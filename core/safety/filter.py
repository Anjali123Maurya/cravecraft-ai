"""The safety filter: checks text, recipes and ingredient lists against a
user's diet, allergens and free-text "avoid" items.

It is deterministic (no LLM). Use it BEFORE generation to drop forbidden
pantry items, and AFTER generation to re-check every field of the recipe.
"""
import logging
import re
from dataclasses import dataclass

from pydantic import BaseModel, Field, field_validator

from core.safety.allergens import ALLERGENS
from core.safety.diet_rules import DIETS
from core.schemas import Recipe

logger = logging.getLogger(__name__)


def normalize(text: str) -> str:
    """Lowercase and turn every non-alphanumeric run into one space."""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _singular(word: str) -> str:
    word = normalize(word)
    if word.endswith("oes"):
        return word[:-2]
    if word.endswith("s") and len(word) > 3:
        return word[:-1]
    return word


class SafetyProfile(BaseModel):
    diet: str = "vegetarian"
    allergens: list[str] = Field(default_factory=list)
    custom_avoid: list[str] = Field(default_factory=list)

    @field_validator("diet")
    @classmethod
    def _check_diet(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in DIETS:
            raise ValueError(f"Unknown diet '{value}'. Choose from {list(DIETS)}")
        return value

    @field_validator("allergens")
    @classmethod
    def _check_allergens(cls, values: list[str]) -> list[str]:
        for value in values:
            if value not in ALLERGENS:
                raise ValueError(f"Unknown allergen '{value}'. Choose from {list(ALLERGENS)}")
        return list(dict.fromkeys(values))

    @field_validator("custom_avoid")
    @classmethod
    def _clean_custom(cls, values: list[str]) -> list[str]:
        cleaned = [_singular(v) for v in values if normalize(v)]
        return list(dict.fromkeys(cleaned))


@dataclass(frozen=True)
class Violation:
    rule: str  # e.g. "allergen:dairy", "diet:vegan", "avoid:brinjal"
    term: str  # the forbidden keyword that was found


@dataclass(frozen=True)
class _Rule:
    name: str
    keywords: tuple[str, ...]
    safe_phrases: tuple[str, ...] = ()


def _pattern(phrase: str) -> re.Pattern:
    return re.compile(rf"\b{re.escape(normalize(phrase))}(?:s|es)?\b")


def _build_rules(profile: SafetyProfile) -> list[_Rule]:
    rules: list[_Rule] = []
    for key in profile.allergens:
        data = ALLERGENS[key]
        rules.append(_Rule(f"allergen:{key}", tuple(data["keywords"]),
                           tuple(data["safe_phrases"])))

    diet = DIETS[profile.diet]
    keywords = list(diet["keywords"])
    safe: list[str] = []
    for key in diet["include_allergens"]:
        keywords += ALLERGENS[key]["keywords"]
        safe += ALLERGENS[key]["safe_phrases"]
    if keywords:
        rules.append(_Rule(f"diet:{profile.diet}", tuple(keywords), tuple(safe)))

    for item in profile.custom_avoid:
        rules.append(_Rule(f"avoid:{item}", (item,)))
    return rules


def check_text(text: str, profile: SafetyProfile) -> list[Violation]:
    """Return every rule violation found in a piece of text."""
    base = normalize(text)
    found: list[Violation] = []
    for rule in _build_rules(profile):
        scrubbed = base
        for phrase in rule.safe_phrases:
            scrubbed = _pattern(phrase).sub(" ", scrubbed)
        for keyword in rule.keywords:
            if _pattern(keyword).search(scrubbed):
                found.append(Violation(rule.name, normalize(keyword)))
    return found


def _strings(value):
    """Yield every string inside nested dicts/lists."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _strings(item)


def check_recipe(recipe: Recipe, profile: SafetyProfile) -> list[Violation]:
    """Scan EVERY text field of a recipe (ingredients, steps, substitutions,
    missing_ingredients, description, image_prompt...)."""
    text = " . ".join(_strings(recipe.model_dump()))
    violations = check_text(text, profile)
    if violations:
        logger.warning("Recipe '%s' blocked: %s", recipe.name, violations)
    return violations


def filter_ingredients(names: list[str], profile: SafetyProfile):
    """Split a pantry list into (allowed, blocked).

    blocked is a list of (ingredient_name, [Violation, ...]) so the UI can
    explain why an item was left out.
    """
    allowed: list[str] = []
    blocked: list[tuple[str, list[Violation]]] = []
    for name in names:
        violations = check_text(name, profile)
        if violations:
            blocked.append((name, violations))
        else:
            allowed.append(name)
    return allowed, blocked