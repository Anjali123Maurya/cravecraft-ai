"""Rule-based recipe remixes (no AI involved).

Each remix returns a modified COPY of the recipe. The result is re-checked by
the safety filter; if it still breaks the user's rules, the original recipe is
returned together with an explanation.
"""
import math
import re
from dataclasses import dataclass, field

from core.knowledge.loader import SeedRecipe
from core.recommender.ingredients import STAPLES, canonical
from core.safety.filter import (SafetyProfile, check_recipe, check_text,
                                strip_unsafe_optional)

REMIXES = {
    "vegan": "Make it vegan",
    "spicier": "Make it spicier",
    "milder": "Make it milder",
    "healthier": "Make it lighter",
    "protein": "Boost the protein",
    "beginner": "Beginner-friendly",
}
SHORT = {"vegan": "Vegan", "spicier": "Spicier", "milder": "Milder",
         "healthier": "Lighter", "protein": "High-protein",
         "beginner": "Beginner"}


@dataclass
class RemixResult:
    recipe: SeedRecipe
    ok: bool
    changes: list[str] = field(default_factory=list)
    message: str = ""


# ---------------- helpers ----------------
def _pattern(swaps: dict[str, str]) -> re.Pattern:
    keys = sorted(swaps, key=len, reverse=True)
    body = "|".join(re.escape(k) for k in keys)
    # whole words only; never touch "coconut milk" / "coconut cream" again
    return re.compile(rf"(?<!\w)(?<!coconut )({body})(?!\w)", re.IGNORECASE)


def _swap(text: str, swaps: dict[str, str]) -> str:
    lookup = {k.lower(): v for k, v in swaps.items()}

    def repl(match: re.Match) -> str:
        new = lookup[match.group(1).lower()]
        if new and match.group(1)[0].isupper():
            return new[0].upper() + new[1:]
        return new

    return _pattern(swaps).sub(repl, text)


def _mentions(text: str, swaps: dict[str, str]) -> bool:
    return bool(_pattern(swaps).search(text))


def _merge(ingredients: list) -> list:
    """Combine duplicate ingredients (same name and unit) by adding quantities."""
    out: list = []
    index: dict[tuple[str, str], int] = {}
    for ing in ingredients:
        key = (ing.name.lower(), ing.unit)
        if key in index and ing.quantity is not None \
                and out[index[key]].quantity is not None:
            prev = out[index[key]]
            out[index[key]] = prev.model_copy(
                update={"quantity": prev.quantity + ing.quantity})
        else:
            index[key] = len(out)
            out.append(ing)
    return out


def _finish(original: SeedRecipe, new: SeedRecipe, kind: str,
            profile: SafetyProfile, changes: list[str],
            check_profile: SafetyProfile | None = None) -> RemixResult:
    check_profile = check_profile or profile
    new = new.model_copy(update={
        "id": f"{original.id}--{kind}",
        "name": f"{new.name} ({SHORT[kind]})",
    })
    new = strip_unsafe_optional(new, check_profile)  # drop unsafe added tips
    probe = new.model_copy(update={"id": "remix"})   # ids are not food words
    violations = check_recipe(probe, check_profile)
    if violations:
        terms = ", ".join(sorted({v.term for v in violations}))
        return RemixResult(original, False, [],
                           f"I couldn't do that safely for your food rules "
                           f"(still contains: {terms}).")
    return RemixResult(new, True, changes)


def _no_change(recipe: SeedRecipe, message: str) -> RemixResult:
    return RemixResult(recipe, False, [], message)


# ---------------- vegan ----------------
VEGAN_SWAPS = {
    "yogurt (curd)": "thick coconut milk with a squeeze of lemon",
    "yogurt": "thick coconut milk", "curd": "thick coconut milk",
    "paneer": "firm tofu", "ghee": "oil", "butter": "oil",
    "cream": "coconut cream", "milk": "coconut milk", "honey": "jaggery",
}
VEGAN_NAME_SWAPS = {"paneer": "Tofu", "curd": "Coconut", "yogurt": "Coconut"}


def _vegan(recipe: SeedRecipe, profile: SafetyProfile) -> RemixResult:
    changes: list[str] = []
    ingredients = []
    for ing in recipe.ingredients:
        new_name = _swap(ing.name, VEGAN_SWAPS)
        if new_name != ing.name:
            changes.append(f"{ing.name} → {new_name}")
            ing = ing.model_copy(update={
                "name": new_name, "in_pantry": canonical(new_name) in STAPLES})
        ingredients.append(ing)

    tips = [t for t in recipe.tips if not _mentions(t, VEGAN_SWAPS)]
    subs = [s for s in recipe.substitutions if not _mentions(s, VEGAN_SWAPS)]
    new = recipe.model_copy(update={
        "name": _swap(recipe.name, VEGAN_NAME_SWAPS),
        "description": _swap(recipe.description, VEGAN_SWAPS),
        "ingredients": _merge(ingredients),
        "steps": [_swap(s, VEGAN_SWAPS) for s in recipe.steps],
        "missing_ingredients": [_swap(m, VEGAN_SWAPS)
                                for m in recipe.missing_ingredients],
        "tips": tips, "substitutions": subs,
        "image_prompt": _swap(recipe.image_prompt, VEGAN_SWAPS),
    })
    if not changes:
        changes.append("Already free of dairy and honey")
    check = SafetyProfile(diet="vegan", allergens=profile.allergens,
                          custom_avoid=profile.custom_avoid)
    return _finish(recipe, new, "vegan", profile, changes, check)


# ---------------- spice level ----------------
def _scale_chilli(recipe: SeedRecipe, factor: float, changes: list[str]) -> list:
    out = []
    for ing in recipe.ingredients:
        if "chilli" in ing.name.lower() and ing.quantity:
            q = ing.quantity * factor
            if ing.unit == "piece":
                q = math.ceil(q) if factor > 1 else max(1, math.floor(q))
            else:
                q = max(0.25, round(q * 4) / 4)
            q = float(q)
            if q != ing.quantity:
                changes.append(f"{ing.name}: {ing.quantity:g} → {q:g} {ing.unit}".strip())
                ing = ing.model_copy(update={"quantity": q})
        out.append(ing)
    return out


def _has_chilli(recipe: SeedRecipe) -> bool:
    return any("chilli" in i.name.lower() for i in recipe.ingredients)


def _spicier(recipe: SeedRecipe, profile: SafetyProfile) -> RemixResult:
    changes: list[str] = []
    ingredients = _scale_chilli(recipe, 1.5, changes)
    tips = list(recipe.tips)
    if not _has_chilli(recipe):
        extra = recipe.ingredients[0].model_copy(update={
            "name": "red chilli powder", "quantity": 0.5, "unit": "tsp",
            "in_pantry": True})
        ingredients.append(extra)
        tips.insert(0, "Add the extra chilli powder together with the other spices.")
        changes.append("added red chilli powder: 0.5 tsp")
    tips.insert(0, "For a different kind of heat, add a pinch of black pepper "
                   "with the last spices.")
    changes.append("added a heat tip")
    new = recipe.model_copy(update={"ingredients": ingredients, "tips": tips})
    return _finish(recipe, new, "spicier", profile, changes)


def _milder(recipe: SeedRecipe, profile: SafetyProfile) -> RemixResult:
    if not _has_chilli(recipe):
        return _no_change(recipe, "This dish has no chilli, so it is already mild.")
    changes: list[str] = []
    ingredients = _scale_chilli(recipe, 0.5, changes)
    tips = list(recipe.tips)
    if any("green chilli" in i.name.lower() for i in recipe.ingredients):
        tips.insert(0, "Remove the seeds from the green chillies to cut the heat further.")
    tips.insert(0, "Serve with a cooling side such as cucumber or plain rice.")
    changes.append("added cooling tips")
    new = recipe.model_copy(update={"ingredients": ingredients, "tips": tips})
    return _finish(recipe, new, "milder", profile, changes)


# ---------------- lighter ----------------
EXPLICIT_FAT = re.compile(r"\d(?:\.\d+)?\s*(?:tbsp|tsp)\s+(?:oil|butter|ghee|cream)",
                          re.IGNORECASE)
FAT_FACTOR = {"oil": 0.75, "butter": 0.5, "ghee": 0.5, "cream": 0.5}


def _healthier(recipe: SeedRecipe, profile: SafetyProfile) -> RemixResult:
    changes: list[str] = []
    ingredients = list(recipe.ingredients)
    steps_state_amounts = any(EXPLICIT_FAT.search(s) for s in recipe.steps)
    if steps_state_amounts:
        changes.append("The steps state exact fat amounts, so quantities were "
                       "left unchanged (tips added instead)")
    else:
        ingredients = []
        for ing in recipe.ingredients:
            factor = FAT_FACTOR.get(canonical(ing.name))
            if factor and ing.quantity:
                q = max(0.25, round(ing.quantity * factor * 4) / 4)
                changes.append(f"{ing.name}: {ing.quantity:g} → {q:g} {ing.unit}".strip())
                ing = ing.model_copy(update={"quantity": q})
            ingredients.append(ing)
    tips = ["Use a non-stick pan so you need less oil.",
            "Add an extra handful of vegetables, or a salad on the side, for fibre."
            ] + list(recipe.tips)
    changes.append("added lighter-cooking tips")
    new = recipe.model_copy(update={"ingredients": ingredients, "tips": tips})
    return _finish(recipe, new, "healthier", profile, changes)


# ---------------- protein ----------------
PROTEIN_ADDONS = [("boiled chickpeas", 0.5, "cup"), ("firm tofu", 100, "g"),
                  ("paneer", 100, "g"), ("roasted peanuts", 2, "tbsp")]
NO_ADDIN = {"dosa", "podi-idli", "dhokla", "aloo-paratha", "methi-thepla",
            "jeera-rice", "curd-rice", "poha", "upma", "gujarati-kadhi"}


def _protein(recipe: SeedRecipe, profile: SafetyProfile) -> RemixResult:
    if recipe.id in NO_ADDIN:
        tips = ["Serve with a bowl of dal, sprouts or a chickpea salad to "
                "raise the protein."] + list(recipe.tips)
        new = recipe.model_copy(update={"tips": tips})
        return _finish(recipe, new, "protein", profile,
                       ["added a high-protein side suggestion"])

    names = " ".join(i.name.lower() for i in recipe.ingredients)
    for name, qty, unit in PROTEIN_ADDONS:
        if name.split()[-1] in names:      # already in the dish
            continue
        if check_text(name, profile):      # breaks diet, allergy or avoid list
            continue
        ingredient = recipe.ingredients[0].model_copy(update={
            "name": name, "quantity": float(qty), "unit": unit,
            "in_pantry": False})
        steps = list(recipe.steps) + [
            f"Stir in the {name} during the last 5 minutes of cooking and heat through."]
        new = recipe.model_copy(update={
            "ingredients": list(recipe.ingredients) + [ingredient],
            "steps": steps})
        return _finish(recipe, new, "protein", profile,
                       [f"added {name}: {qty:g} {unit}"])
    return _no_change(recipe, "I couldn't find a protein add-on that fits your food rules.")


# ---------------- beginner ----------------
def _beginner(recipe: SeedRecipe, profile: SafetyProfile) -> RemixResult:
    tips = ["Read all the steps once, then chop and measure everything before "
            "you turn on the stove.",
            "Keep the heat on medium. If anything smells burnt, switch the heat "
            "off first, then fix it.",
            "Use the timers in cooking mode so you do not have to watch the clock."]
    if recipe.difficulty == "hard":
        tips.insert(0, "This is an advanced dish. Allow extra time and do not rush.")
    new = recipe.model_copy(update={"tips": tips + list(recipe.tips)})
    return _finish(recipe, new, "beginner", profile,
                   ["added preparation and heat-control tips"])


_HANDLERS = {"vegan": _vegan, "spicier": _spicier, "milder": _milder,
             "healthier": _healthier, "protein": _protein, "beginner": _beginner}


def remix(recipe: SeedRecipe, kind: str, profile: SafetyProfile) -> RemixResult:
    handler = _HANDLERS.get(kind)
    if handler is None:
        raise ValueError(f"Unknown remix '{kind}'. Choose from {list(_HANDLERS)}")
    return handler(recipe, profile)