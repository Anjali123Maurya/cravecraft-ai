"""Adapts a retrieved, already-safe seed recipe to the user's pantry and craving.

The LLM writes ONLY: a tailored description, a few tips, and substitutions.
Ingredients and steps come from the seed recipe; in_pantry flags come from the
ranker's match. Every AI sentence is checked by the safety filter.
"""
import logging
from dataclasses import dataclass, field

from pydantic import ValidationError

from core.ai.llm_client import LLMClient, LLMUnavailable
from core.knowledge.loader import SeedRecipe
from core.recommender.ingredients import STAPLES, canonical
from core.recommender.ranker import Match, Preferences
from core.safety.filter import (SafetyProfile, check_recipe, check_text,
                                filter_ingredients, strip_unsafe_optional)
from core.schemas import Adaptation

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a careful Indian home-cooking assistant. Reply ONLY with JSON "
    "matching the schema. Never mention ingredients that are not listed in "
    "the message or common kitchen staples. Keep every sentence short."
)


@dataclass
class AdaptedRecipe:
    recipe: SeedRecipe
    used_llm: bool
    attempts: int
    warnings: list[str] = field(default_factory=list)


def build_prompt(match: Match, prefs: Preferences, kitchen: list[str]) -> str:
    recipe = match.recipe
    lines = [
        f"Dish: {recipe.name} ({recipe.region})",
        f"Original description: {recipe.description}",
        f"Main ingredients the user has: {', '.join(match.have) or 'none'}",
        f"Main ingredients the user is missing: {', '.join(match.missing) or 'none'}",
        f"Other items in the user's kitchen: {', '.join(kitchen) or 'none'}",
        f"Craving: {', '.join(prefs.cravings) or 'no preference'}",
    ]
    if prefs.max_total_minutes:
        lines.append(f"Time available: {prefs.max_total_minutes} minutes")
    lines.append(
        "Write: description = 1-2 sentences tailored to the craving, no new "
        "ingredients. tips = up to 3 short cooking tips for this dish. "
        "substitutions = for each missing ingredient, one short suggestion "
        "using only the user's kitchen items or common staples (empty list if "
        "nothing is missing)."
    )
    return "\n".join(lines)


def _safe_lines(lines: list[str], profile: SafetyProfile) -> list[str]:
    return [line for line in lines if not check_text(line, profile)]


def adapt_recipe(match: Match, prefs: Preferences, profile: SafetyProfile,
                 llm: LLMClient | None = None, max_attempts: int = 2) -> AdaptedRecipe:
    # 1. Start from the original recipe, minus unsafe optional lines.
    base = strip_unsafe_optional(match.recipe, profile)
    if check_recipe(base, profile):
        raise ValueError(f"Recipe '{base.id}' is not safe for this profile; "
                         "filter with safe_recipes() before adapting.")

    # 2. Set the "you have it / you need to buy it" flags in code.
    ingredients = [
        ing.model_copy(update={"in_pantry": (canonical(ing.name) in STAPLES
                                             or canonical(ing.name) in match.have)})
        for ing in base.ingredients
    ]
    base = base.model_copy(update={"ingredients": ingredients,
                                   "missing_ingredients": list(match.missing)})

    # 3. Ask the model, using only safe pantry items in the prompt.
    kitchen, _blocked = filter_ingredients(prefs.pantry, profile)
    prompt = build_prompt(match, prefs, kitchen)
    llm = llm or LLMClient()
    warnings: list[str] = []
    adaptation: Adaptation | None = None
    attempts = 0

    for attempt in range(max_attempts):
        attempts += 1
        try:
            raw = llm.generate_json(SYSTEM_PROMPT, prompt,
                                    Adaptation.model_json_schema(),
                                    temperature=0.3 + 0.2 * attempt)
        except LLMUnavailable as exc:
            logger.error("LLM unavailable: %s", exc)
            warnings.append("The AI assistant is not available, so the recipe "
                            "is shown as written.")
            break
        try:
            candidate = Adaptation.model_validate_json(raw)
        except ValidationError:
            logger.warning("Attempt %d: invalid AI output", attempts)
            continue
        if check_text(candidate.description, profile):
            logger.warning("Attempt %d: AI description failed the safety check",
                           attempts)
            continue
        adaptation = candidate
        break

    if adaptation is None:
        if not warnings:
            warnings.append("The AI text could not be used safely, so the "
                            "recipe is shown as written.")
        return AdaptedRecipe(base, used_llm=False, attempts=attempts,
                             warnings=warnings)

    # 4. Merge, keeping only safe AI lines.
    tips = list(dict.fromkeys(base.tips + _safe_lines(adaptation.tips, profile)))[:5]
    subs = list(dict.fromkeys(base.substitutions
                              + _safe_lines(adaptation.substitutions, profile)))[:6]
    final = base.model_copy(update={"description": adaptation.description,
                                    "tips": tips, "substitutions": subs})

    # 5. Last gate: the finished recipe must pass the safety check.
    if check_recipe(final, profile):
        warnings.append("The AI text was rejected by the safety check.")
        return AdaptedRecipe(base, used_llm=False, attempts=attempts,
                             warnings=warnings)
    return AdaptedRecipe(final, used_llm=True, attempts=attempts, warnings=warnings)    