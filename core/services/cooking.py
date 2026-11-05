"""Logic for cooking mode: step timers, step ingredients and Q&A.

Questions are answered in this order:
1. a small built-in list of common kitchen problems (no AI, fast, reliable)
2. the local AI, with the current recipe and step in the prompt
Every answer is checked by the safety filter before it is shown.
"""
import logging
import re
from dataclasses import dataclass

from pydantic import ValidationError

from core.ai.llm_client import LLMClient, LLMUnavailable
from core.knowledge.loader import SeedRecipe
from core.safety.filter import SafetyProfile, check_text
from core.schemas import Answer

logger = logging.getLogger(__name__)

# ---------------- timers ----------------
_TIME = re.compile(r"(\d+)(?:\s*-\s*(\d+))?\s*(minutes?|mins?|seconds?|secs?|hours?)\b",
                   re.IGNORECASE)
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600}
_UNIT_LABEL = {"s": "sec", "m": "min", "h": "hr"}


def step_timers(step: str) -> list[tuple[str, int]]:
    """Find durations in a step. A range like '6-8 minutes' uses the upper end.

    Returns [(label, seconds), ...], e.g. [("8 min", 480)].
    """
    found: list[tuple[str, int]] = []
    for match in _TIME.finditer(step):
        low, high, unit = match.group(1), match.group(2), match.group(3)
        amount = int(high or low)
        key = unit[0].lower()
        item = (f"{amount} {_UNIT_LABEL[key]}", amount * _UNIT_SECONDS[key])
        if item not in found:
            found.append(item)
    return found


# ---------------- ingredients used in a step ----------------
_GENERIC = {"powder", "seed", "seeds", "leaf", "leaves", "paste", "fresh", "red",
            "green", "dried", "large", "small", "whole", "cooked", "yellow",
            "thick", "mixed", "stick", "piece", "black"}


def _stem(word: str) -> str:
    return word[:-1] if word.endswith("s") and len(word) > 3 and not word.endswith("ss") else word


def _tokens(name: str) -> list[str]:
    name = re.sub(r"\(.*?\)", " ", name.lower())
    return [_stem(w) for w in re.findall(r"[a-z]+", name) if w not in _GENERIC]


def step_ingredients(recipe: SeedRecipe, step_index: int) -> list:
    """Ingredients whose name appears in the step text (approximate)."""
    text = recipe.steps[step_index].lower()
    used = []
    for ing in recipe.ingredients:
        for token in _tokens(ing.name):
            if re.search(rf"\b{re.escape(token)}(?:s|es)?\b", text):
                used.append(ing)
                break
    return used


# ---------------- quick answers ----------------
# First matching rule wins, so symptoms come before ingredient questions.
HELP: list[tuple[tuple[str, ...], str]] = [
    (("thicken", "watery", "runny", "too thin"),
     "Simmer uncovered on medium heat so the extra water evaporates. You can also "
     "mash a few pieces of the cooked vegetables or lentils into the gravy to "
     "thicken it naturally."),
    (("too thick", "thick", "dry", "too dense"),
     "Add a few spoonfuls of hot water, stir, and simmer for 2-3 minutes. Add a "
     "little at a time until it looks right. Hot water keeps the flavor from "
     "turning flat."),
    (("salty", "too much salt"),
     "Dilute with a little hot water and add more of the main ingredient to "
     "balance it. A squeeze of lemon or a pinch of sugar also softens the "
     "saltiness. Next time add salt in small amounts and taste at the end."),
    (("too spicy", "too hot", "less spicy"),
     "Add a pinch of sugar and a squeeze of lemon, and dilute with a little hot "
     "water. Adding more of the main vegetables or lentils also spreads the heat."),
    (("sour", "too tangy"),
     "Balance it with a pinch of sugar and a little hot water, then simmer for a "
     "couple of minutes."),
    (("bitter",),
     "Bitterness usually comes from burnt garlic or spices, or too much "
     "fenugreek. A pinch of sugar and a squeeze of lemon can soften it. If it "
     "tastes burnt, it can't be fully fixed. Next time lower the heat while "
     "frying spices."),
    (("burnt", "burned", "stuck to", "sticking"),
     "Switch off the heat at once and do not scrape the burnt layer. Move the "
     "unburnt food into a clean pot, add a little hot water and continue on low "
     "heat."),
    (("raw smell", "raw taste", "oil separate", "oil leave", "oil not"),
     "Keep cooking the masala on medium heat, stirring often, until the oil "
     "visibly leaves the sides. A splash of water stops it from sticking while "
     "you wait."),
    (("lump",),
     "Whisk vigorously or use a hand blender. Next time, add the batter or grain "
     "slowly while stirring constantly."),
    (("not soft", "undercooked", "still hard", "not cooking", "not cooked"),
     "Cover and cook longer, adding hot water if it is drying out. Check by "
     "pressing a piece between your fingers. Add salt only after beans or "
     "lentils are soft."),
    (("cream",),
     "Yes, milk works for a lighter gravy. Add it with the heat turned off so it "
     "does not curdle, and expect a thinner result. A spoon of cashew paste "
     "brings the richness back."),
    (("paneer",),
     "Paneer only needs warming through, about 2-3 minutes in the gravy. It is "
     "ready when it is hot and soft. Longer cooking makes it rubbery. If it has "
     "gone hard, soak the pieces in warm water for 10 minutes."),
]


def quick_answer(question: str, profile: SafetyProfile) -> str | None:
    q = question.lower()
    for keywords, answer in HELP:
        if any(k in q for k in keywords):
            # Matched, but if the tip breaks the user's rules, don't show it.
            return None if check_text(answer, profile) else answer
    return None


# ---------------- AI answers ----------------
SYSTEM_PROMPT = (
    "You are a careful Indian home-cooking assistant. Reply ONLY with JSON "
    "matching the schema. Answer in 2-4 short sentences. Only suggest "
    "ingredients from the recipe or common staples such as salt, oil, water, "
    "lemon and sugar. If you are not sure, say so."
)


@dataclass
class Reply:
    text: str
    source: str  # "tips" | "ai" | "none"


def build_question_prompt(recipe: SeedRecipe, step_index: int, question: str) -> str:
    names = ", ".join(i.name for i in recipe.ingredients)
    return (f"Dish: {recipe.name}\nIngredients: {names}\n"
            f"Current step ({step_index + 1} of {len(recipe.steps)}): "
            f"{recipe.steps[step_index]}\nQuestion: {question}")


def answer_question(question: str, recipe: SeedRecipe, step_index: int,
                    profile: SafetyProfile, llm=None, max_attempts: int = 2) -> Reply:
    question = question.strip()[:300]
    if not question:
        return Reply("Type a question first.", "none")

    tip = quick_answer(question, profile)
    if tip:
        return Reply(tip, "tips")

    llm = llm or LLMClient()
    prompt = build_question_prompt(recipe, step_index, question)
    for attempt in range(max_attempts):
        try:
            raw = llm.generate_json(SYSTEM_PROMPT, prompt, Answer.model_json_schema(),
                                    temperature=0.2 + 0.2 * attempt)
        except LLMUnavailable as exc:
            logger.error("LLM unavailable: %s", exc)
            return Reply("The AI assistant is not available right now. Common "
                         "kitchen problems (too thick, too salty, too spicy...) "
                         "still work without it.", "none")
        try:
            answer = Answer.model_validate_json(raw)
        except ValidationError:
            continue
        if check_text(answer.answer, profile):
            logger.warning("AI answer failed the safety check")
            continue
        return Reply(answer.answer, "ai")
    return Reply("I couldn't find a safe answer to that. Try rephrasing the "
                 "question.", "none")