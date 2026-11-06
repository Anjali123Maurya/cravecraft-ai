from core.knowledge.loader import load_seed_recipes
from core.safety.filter import SafetyProfile, check_recipe
from core.services.remix import remix


def recipe(recipe_id):
    return next(r for r in load_seed_recipes() if r.id == recipe_id)


def qty(r, name):
    return next(i.quantity for i in r.ingredients if i.name == name)


def names(r):
    return [i.name for i in r.ingredients]


def test_vegan_palak_paneer_becomes_tofu():
    result = remix(recipe("palak-paneer"), "vegan", SafetyProfile())
    assert result.ok
    assert "firm tofu" in names(result.recipe)
    assert "coconut cream" in names(result.recipe)
    assert result.recipe.name == "Palak Tofu (Vegan)"
    assert result.recipe.id == "palak-paneer--vegan"
    probe = result.recipe.model_copy(update={"id": "x"})
    assert check_recipe(probe, SafetyProfile(diet="vegan")) == []


def test_vegan_is_refused_for_soy_allergy():
    original = recipe("palak-paneer")
    profile = SafetyProfile(diet="vegetarian", allergens=["soy"])
    result = remix(original, "vegan", profile)
    assert not result.ok and "tofu" in result.message
    assert result.recipe is original


def test_vegan_drops_ghee_tip():
    result = remix(recipe("dal-tadka"), "vegan", SafetyProfile())
    assert result.ok and "ghee" not in " ".join(result.recipe.tips).lower()


def test_spicier_raises_chilli_and_leaves_original_untouched():
    original = recipe("aloo-matar")
    result = remix(original, "spicier", SafetyProfile())
    assert qty(result.recipe, "red chilli powder") == 1.5
    assert qty(original, "red chilli powder") == 1.0


def test_milder_halves_chilli():
    result = remix(recipe("aloo-matar"), "milder", SafetyProfile())
    assert qty(result.recipe, "red chilli powder") == 0.5


def test_milder_on_dish_without_chilli_says_so():
    result = remix(recipe("jeera-rice"), "milder", SafetyProfile())
    assert not result.ok and "already mild" in result.message


def test_healthier_cuts_oil_when_steps_do_not_state_amounts():
    result = remix(recipe("aloo-matar"), "healthier", SafetyProfile())
    assert qty(result.recipe, "oil") == 2.25


def test_healthier_keeps_quantities_when_steps_state_amounts():
    result = remix(recipe("pav-bhaji"), "healthier", SafetyProfile())
    assert result.ok and qty(result.recipe, "butter") == 3


def test_protein_adds_chickpeas():
    result = remix(recipe("aloo-matar"), "protein", SafetyProfile())
    assert "boiled chickpeas" in names(result.recipe)
    assert "boiled chickpeas" in result.recipe.steps[-1]


def test_protein_respects_avoid_list():
    profile = SafetyProfile(custom_avoid=["chickpeas"])
    result = remix(recipe("aloo-matar"), "protein", profile)
    assert "firm tofu" in names(result.recipe)
    assert "boiled chickpeas" not in names(result.recipe)


def test_protein_on_dosa_only_adds_a_tip():
    original = recipe("dosa")
    result = remix(original, "protein", SafetyProfile())
    assert result.ok and len(result.recipe.ingredients) == len(original.ingredients)
    assert "dal" in result.recipe.tips[0]


def test_beginner_adds_tips_first():
    result = remix(recipe("veg-biryani"), "beginner", SafetyProfile())
    assert result.ok and "advanced" in result.recipe.tips[0]


def test_unknown_remix_raises():
    import pytest
    with pytest.raises(ValueError):
        remix(recipe("dosa"), "nonsense", SafetyProfile())