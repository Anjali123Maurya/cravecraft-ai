from core.knowledge.loader import load_seed_recipes
from core.recommender.ingredients import canonical
from core.recommender.ranker import Preferences, rank_recipes
from core.safety.filter import SafetyProfile, safe_recipes


def test_canonical_handles_plurals_and_hindi():
    assert canonical("Tomatoes") == "tomato"
    assert canonical("tamatar") == "tomato"
    assert canonical("Potatoes") == "potato"
    assert canonical("curd") == "yogurt"
    assert canonical("rajma (red kidney beans)") == "kidney beans"
    assert canonical("") == ""


def test_potato_and_peas_ranks_aloo_matar_first():
    prefs = Preferences(pantry=["potatoes", "peas", "onion", "tomato"])
    top = rank_recipes(load_seed_recipes(), prefs)
    assert top[0].recipe.id == "aloo-matar"
    assert top[0].missing == []


def test_missing_ingredients_are_reported():
    prefs = Preferences(pantry=["spinach", "onion", "tomato"])
    top = rank_recipes(load_seed_recipes(), prefs, top_n=16)
    palak = next(m for m in top if m.recipe.id == "palak-paneer")
    assert "paneer" in palak.missing and "spinach" in palak.have

def test_recent_recipe_is_pushed_down():
    base = Preferences(pantry=["potatoes", "peas", "onion", "tomato"])
    again = Preferences(pantry=base.pantry, recent_ids=["aloo-matar"])
    before = next(m for m in rank_recipes(load_seed_recipes(), base, top_n=16)
                  if m.recipe.id == "aloo-matar")
    after = next(m for m in rank_recipes(load_seed_recipes(), again, top_n=16)
                 if m.recipe.id == "aloo-matar")
    assert after.score == before.score - 30
    assert "shown recently" in after.reasons    


def test_craving_bonus_applies():
    prefs = Preferences(pantry=["rice"], cravings=["tangy"])
    top = rank_recipes(load_seed_recipes(), prefs, top_n=3)
    assert any("craving" in " ".join(m.reasons) for m in top)


def test_vegan_pipeline_never_returns_dairy_recipe():
    safe = safe_recipes(load_seed_recipes(), SafetyProfile(diet="vegan"))
    prefs = Preferences(pantry=["paneer", "capsicum", "onion", "tomato"])
    ids = {m.recipe.id for m in rank_recipes(safe, prefs, top_n=16)}
    assert "paneer-bhurji" not in ids   