"""Scores and ranks safe recipes for a user's pantry and preferences."""
from dataclasses import dataclass, field

from core.knowledge.loader import SeedRecipe
from core.recommender.ingredients import STAPLES, canonical, canonical_all

# Words in a craving -> flavor words in recipes that match them.
CRAVING_MAP: dict[str, set[str]] = {
    "spicy": {"spicy", "mildly spicy"},
    "sweet": {"sweet"},
    "tangy": {"tangy"},
    "creamy": {"creamy"},
    "savory": {"savory"},
    "smoky": {"smoky"},
    "crunchy": {"crunchy"},
    "comforting": {"comforting", "mild"},
    "light": {"light", "fresh", "mild"},
    "fresh": {"fresh", "light"},
}


@dataclass
class Preferences:
    pantry: list[str]
    cravings: list[str] = field(default_factory=list)
    max_total_minutes: int | None = None
    difficulty: str | None = None  # "easy" | "medium" | "hard" | None
    recent_ids: list[str] = field(default_factory=list)
    use_first: list[str] = field(default_factory=list)  # items expiring soon


@dataclass
class Match:
    recipe: SeedRecipe
    score: float
    coverage: float            # share of main ingredients the user has (0..1)
    have: list[str]
    missing: list[str]
    reasons: list[str]


def _main_ingredients(recipe: SeedRecipe) -> list[str]:
    """Canonical non-staple ingredients: the ones the user must have."""
    seen: list[str] = []
    for ing in recipe.ingredients:
        name = canonical(ing.name)
        if name and name not in STAPLES and name not in seen:
            seen.append(name)
    return seen


def _have(main_name: str, pantry: set[str]) -> bool:
    if main_name in pantry:
        return True
    # "toor dal" vs pantry "dal"; "green peas" vs "peas": match on whole words.
    words = set(main_name.split())
    return any(p in words or set(p.split()) <= words and len(p.split()) > 1
               for p in pantry)


def score_recipe(recipe: SeedRecipe, prefs: Preferences) -> Match | None:
    pantry = canonical_all(prefs.pantry)
    main = _main_ingredients(recipe)
    if not main:
        return None

    have = [m for m in main if _have(m, pantry)]
    missing = [m for m in main if m not in have]
    coverage = len(have) / len(main)

    score = coverage * 100
    reasons = [f"you have {len(have)} of {len(main)} main ingredients"]

    wanted: set[str] = set()
    for craving in prefs.cravings:
        wanted |= CRAVING_MAP.get(craving.lower().strip(), {craving.lower().strip()})
    if wanted and wanted & {f.lower() for f in recipe.flavor_profile}:
        score += 15
        reasons.append("matches your craving")

    if prefs.max_total_minutes is not None:
        if recipe.total_time_min <= prefs.max_total_minutes:
            score += 8
            reasons.append("fits your time")
        else:
            score -= 20
            reasons.append("takes longer than you wanted")

    if prefs.difficulty and recipe.difficulty == prefs.difficulty:
        score += 5

    # Bonus for recipes that use up ingredients that expire soon.
    urgent = canonical_all(prefs.use_first)
    uses_up = [m for m in have if m in urgent]
    if uses_up:
        score += min(10 * len(uses_up), 20)
        reasons.append("uses up " + ", ".join(uses_up))

    if recipe.id in prefs.recent_ids:
        score -= 30
        reasons.append("shown recently")

    return Match(recipe, round(score, 1), round(coverage, 2), have, missing, reasons)


def rank_recipes(recipes, prefs: Preferences, top_n: int = 5,
                 min_coverage: float = 0.0) -> list[Match]:
    matches = [m for r in recipes if (m := score_recipe(r, prefs))
               and m.coverage >= min_coverage]
    matches.sort(key=lambda m: m.score, reverse=True)
    return matches[:top_n]