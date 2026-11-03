import pytest
from pydantic import ValidationError

from core.safety.filter import (SafetyProfile, check_recipe, check_text,
                                filter_ingredients)
from core.schemas import Recipe


def terms(text, **profile):
    return {v.term for v in check_text(text, SafetyProfile(**profile))}


def make_recipe(ingredients=("potato", "peas"), missing=(), subs=()):
    return Recipe(
        name="Test curry", description="A test.", cuisine="Indian",
        flavor_profile=["spicy"], prep_time_min=5, cook_time_min=20,
        difficulty="easy", servings=2,
        ingredients=[{"name": n} for n in ingredients],
        missing_ingredients=list(missing),
        steps=["Chop.", "Cook.", "Serve."],
        substitutions=list(subs),
    )


def test_vegan_blocks_dairy_and_honey():
    assert {"paneer", "honey"} <= terms("paneer and honey", diet="vegan")


def test_vegetarian_blocks_meat_and_eggs_but_not_chickpeas():
    assert "chicken" in terms("chicken curry", diet="vegetarian")
    assert "egg" in terms("2 eggs", diet="vegetarian")
    assert terms("chickpeas and eggplant", diet="vegetarian") == set()


def test_eggetarian_allows_eggs_blocks_meat():
    assert terms("2 eggs", diet="eggetarian") == set()
    assert "mutton" in terms("mutton", diet="eggetarian")


def test_coconut_milk_ok_for_dairy_allergy_but_not_almond_milk_for_nuts():
    assert terms("1 cup coconut milk", allergens=["dairy"]) == set()
    assert "almond" in terms("almond milk", allergens=["tree_nuts"])


def test_butter_beans_not_dairy():
    assert terms("butter beans", allergens=["dairy"]) == set()


def test_peanut_butter_flagged_for_peanut_allergy():
    assert "peanut" in terms("peanut butter", allergens=["peanuts"])


def test_gluten_flours():
    assert terms("2 cups rice flour", allergens=["gluten"]) == set()
    assert "maida" in terms("maida", allergens=["gluten"])
    assert "flour" in terms("plain flour", allergens=["gluten"])


def test_jain_blocks_onion_not_tomato():
    assert "onion" in terms("1 onion", diet="jain")
    assert "potato" in terms("2 potatoes", diet="jain")
    assert terms("2 tomatoes", diet="jain") == set()


def test_custom_avoid_handles_plural():
    assert "brinjal" in terms("brinjal masala", custom_avoid=["Brinjals"])


def test_recipe_scans_missing_ingredients_and_substitutions():
    profile = SafetyProfile(diet="vegan")
    assert check_recipe(make_recipe(missing=["paneer"]), profile)
    assert check_recipe(make_recipe(subs=["use ghee instead"]), profile)
    assert check_recipe(make_recipe(), profile) == []


def test_filter_ingredients_splits_pantry():
    profile = SafetyProfile(diet="vegan")
    allowed, blocked = filter_ingredients(["paneer", "tomato", "milk"], profile)
    assert allowed == ["tomato"]
    assert [name for name, _ in blocked] == ["paneer", "milk"]


def test_invalid_profile_values_rejected():
    with pytest.raises(ValidationError):
        SafetyProfile(diet="carnivore")
    with pytest.raises(ValidationError):
        SafetyProfile(allergens=["pollen"])