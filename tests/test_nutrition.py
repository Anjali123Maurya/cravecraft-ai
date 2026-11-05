from core.knowledge.loader import load_seed_recipes
from core.services.nutrition import estimate_nutrition, ingredient_grams, load_table


def recipe(recipe_id):
    return next(r for r in load_seed_recipes() if r.id == recipe_id)


def test_unit_conversion():
    table = load_table()
    assert ingredient_grams(table["oil"], 2, "tbsp") == 27
    assert ingredient_grams(table["paneer"], 200, "g") == 200
    assert ingredient_grams(table["potato"], 3, "piece") == 450
    assert ingredient_grams(table["rice"], 1, "bucket") is None


def test_every_recipe_has_plausible_values_and_reports_gaps():
    for r in load_seed_recipes():
        n = estimate_nutrition(r)
        assert 0 <= n.kcal < 1500, f"{r.id}: {n.kcal} kcal"
        assert n.protein >= 0 and n.fat >= 0 and n.carbs >= 0
        assert 0 <= n.coverage <= 1


def test_aloo_matar_is_in_a_sensible_range():
    n = estimate_nutrition(recipe("aloo-matar"))
    assert 150 < n.kcal < 450
    assert "potato" in n.matched


def test_paneer_dish_has_more_protein_than_a_plain_veg_dish():
    paneer = estimate_nutrition(recipe("paneer-bhurji"))
    veg = estimate_nutrition(recipe("aloo-gobi"))
    assert paneer.protein > veg.protein


def test_unknown_ingredient_is_reported_not_guessed():
    n = estimate_nutrition(recipe("podi-idli"))
    assert n.coverage > 0   # idli batter matches
    # asafoetida / podi are negligible, so nothing should be silently invented
    assert all(name not in n.matched for name in ("idli podi", "asafoetida"))