"""Approximate per-serving nutrition for a recipe.

Values come from a small reference table (core/knowledge/nutrition_table.json).
They are estimates: unit weights are typical averages and the table is not
exhaustive. Ingredients that are not found are reported, never guessed.
"""
import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from core.knowledge.loader import SeedRecipe
from core.recommender.ingredients import canonical

TABLE_PATH = Path(__file__).resolve().parent.parent / "knowledge" / "nutrition_table.json"

# Spices and small flavourings: under ~2 g per recipe, so ignored on purpose.
NEGLIGIBLE_WORDS = {"powder", "seeds", "masala", "leaf", "leaves", "asafoetida",
                    "cardamom", "cinnamon", "cloves", "pepper", "ajwain",
                    "podi", "salt", "bay", "chilli", "turmeric"}
# Canonical names that look negligible but are not (they have table entries).
KEEP = {"green chilli", "curry leaves", "coriander leaves", "mint leaves"}

# Extra aliases for nutrition lookups only.
NUTRITION_ALIASES = {
    "yogurt": "yogurt", "lemon": "lemon", "cooked rice": "rice",
    "mixed vegetable": "mixed vegetables", "mixed vegetables": "mixed vegetables",
    "pav": "pav", "pav bread roll": "pav", "sago": "sago",
    "kidney bean": "kidney beans", "chickpea": "chickpeas",
    "french bean": "french beans", "green pea": "green peas",
    "wheat flour": "wheat flour", "gram flour": "gram flour",
    "masoor dal": "masoor dal", "moong dal": "moong dal",
}


@dataclass
class Nutrition:
    kcal: float = 0.0
    protein: float = 0.0
    carbs: float = 0.0
    fat: float = 0.0
    fiber: float = 0.0
    matched: list[str] = field(default_factory=list)
    unmatched: list[str] = field(default_factory=list)
    coverage: float = 0.0   # share of counted ingredients that were matched

    @property
    def is_rough(self) -> bool:
        return self.coverage < 0.8


@lru_cache
def load_table() -> dict:
    return json.loads(TABLE_PATH.read_text(encoding="utf-8"))


def _lookup(name: str, table: dict) -> str | None:
    key = canonical(name)
    key = NUTRITION_ALIASES.get(key, key)
    if key in table:
        return key
    # "mixed vegetables carrot beans peas" etc.: try the first words.
    words = re.sub(r"\(.*?\)", " ", name.lower()).split()
    for size in (2, 1):
        candidate = canonical(" ".join(words[:size]))
        candidate = NUTRITION_ALIASES.get(candidate, candidate)
        if candidate in table:
            return candidate
    return None


def _is_negligible(name: str, key: str | None) -> bool:
    if key is not None:
        return False
    canon = canonical(name)
    if canon in KEEP:
        return False
    return any(w in NEGLIGIBLE_WORDS for w in canon.split())


def ingredient_grams(entry: dict, quantity: float | None, unit: str) -> float | None:
    if quantity is None:
        return None
    unit = (unit or "").strip().lower()
    if unit in ("g", "gram", "grams"):
        return quantity
    if unit in ("ml",):
        return quantity  # close enough for water-like liquids
    grams = entry.get("g_per_unit", {}).get(unit)
    return quantity * grams if grams else None


def estimate_nutrition(recipe: SeedRecipe) -> Nutrition:
    table = load_table()
    totals = [0.0] * 5
    result = Nutrition()
    counted = 0

    for ing in recipe.ingredients:
        key = _lookup(ing.name, table)
        if _is_negligible(ing.name, key):
            continue
        counted += 1
        grams = ingredient_grams(table[key], ing.quantity, ing.unit) if key else None
        if key is None or grams is None:
            result.unmatched.append(ing.name)
            continue
        factor = grams / 100
        for i, value in enumerate(table[key]["per100"]):
            totals[i] += value * factor
        result.matched.append(ing.name)

    servings = max(recipe.servings, 1)
    result.kcal, result.protein, result.carbs, result.fat, result.fiber = (
        round(t / servings, 1) for t in totals)
    result.coverage = len(result.matched) / counted if counted else 0.0
    return result