"""Weekly meal planner and grocery list (rule-based, no AI)."""
from dataclasses import dataclass, field

from core.knowledge.loader import SeedRecipe
from core.recommender.ingredients import STAPLES, canonical
from core.recommender.ranker import Match, Preferences, rank_recipes

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
SAME_REGION_PENALTY = 5
SHARED_BONUS = 3
MAX_SHARED_BONUS = 9


@dataclass
class GroceryItem:
    name: str
    quantity: float | None
    unit: str
    used_in: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        qty = f"{self.quantity:g} " if self.quantity else ""
        unit = f"{self.unit} " if self.unit else ""
        return f"{qty}{unit}{self.name}"


def plan_week(recipes, prefs: Preferences, days: int = 7) -> list[Match]:
    """Pick up to `days` different recipes from already-safe `recipes`."""
    pool = rank_recipes(recipes, prefs, top_n=max(len(recipes), 1))
    target = max(1, min(days, len(DAY_NAMES)))
    chosen: list[Match] = []
    chosen_missing: set[str] = set()

    def adjusted(m: Match) -> float:
        score = m.score
        if chosen and m.recipe.region == chosen[-1].recipe.region:
            score -= SAME_REGION_PENALTY
        shared = len(set(m.missing) & chosen_missing)
        return score + min(SHARED_BONUS * shared, MAX_SHARED_BONUS)

    while len(chosen) < target and pool:
        best = max(pool, key=adjusted)
        pool.remove(best)
        chosen.append(best)
        chosen_missing |= set(best.missing)
    return chosen


def grocery_list(plan: list[Match]) -> tuple[list[GroceryItem], list[str]]:
    """Return (items to buy, staples to check)."""
    totals: dict[tuple[str, str], GroceryItem] = {}
    staples: set[str] = set()
    for match in plan:
        missing = set(match.missing)
        for ing in match.recipe.ingredients:
            canon = canonical(ing.name)
            if not canon:
                continue
            if canon in STAPLES:
                staples.add(canon)
                continue
            if canon not in missing:
                continue  # the user's pantry covers it
            key = (canon, ing.unit)
            item = totals.get(key)
            if item is None:
                item = totals[key] = GroceryItem(ing.name, None, ing.unit)
            if ing.quantity is not None:
                item.quantity = (item.quantity or 0) + ing.quantity
            if match.recipe.name not in item.used_in:
                item.used_in.append(match.recipe.name)
    items = sorted(totals.values(), key=lambda i: i.name.lower())
    return items, sorted(staples - {"water"})