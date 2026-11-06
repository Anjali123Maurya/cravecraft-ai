from core.knowledge.loader import load_seed_recipes
from core.recommender.ranker import Preferences, score_recipe
from core.safety.filter import SafetyProfile, safe_recipes
from core.services.planner import grocery_list, plan_week


def recipe(recipe_id):
    return next(r for r in load_seed_recipes() if r.id == recipe_id)


def test_plan_has_requested_length_and_no_repeats():
    prefs = Preferences(pantry=["potatoes", "peas", "onion", "tomato"])
    plan = plan_week(load_seed_recipes(), prefs, days=7)
    ids = [m.recipe.id for m in plan]
    assert len(ids) == 7 and len(set(ids)) == 7


def test_plan_respects_vegan_profile():
    candidates = safe_recipes(load_seed_recipes(), SafetyProfile(diet="vegan"))
    plan = plan_week(candidates, Preferences(pantry=["paneer", "capsicum"]), 7)
    ids = {m.recipe.id for m in plan}
    assert "paneer-bhurji" not in ids and "palak-paneer" not in ids


def test_short_pool_gives_shorter_plan():
    candidates = safe_recipes(load_seed_recipes(), SafetyProfile(diet="jain"))
    plan = plan_week(candidates, Preferences(pantry=[]), 7)
    assert len(plan) == min(7, len(candidates))


def test_grocery_list_merges_same_unit_quantities():
    prefs = Preferences(pantry=[])
    plan = [score_recipe(recipe("aloo-matar"), prefs),
            score_recipe(recipe("aloo-gobi"), prefs)]
    items, _ = grocery_list(plan)
    by_name = {i.name: i for i in items}
    assert by_name["potato"].quantity == 5      # 3 + 2 pieces
    assert by_name["onion"].quantity == 3       # 2 + 1 pieces
    assert set(by_name["potato"].used_in) == {"Aloo Matar", "Aloo Gobi"}


def test_grocery_list_skips_what_pantry_has():
    plan = [score_recipe(recipe("aloo-matar"), Preferences(pantry=["potatoes"]))]
    items, _ = grocery_list(plan)
    assert "potato" not in {i.name for i in items}


def test_staples_listed_separately():
    plan = [score_recipe(recipe("aloo-matar"), Preferences(pantry=[]))]
    items, staples = grocery_list(plan)
    assert "salt" in staples and "water" not in staples
    assert "salt" not in {i.name for i in items}