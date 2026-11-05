from core.knowledge.loader import load_seed_recipes
from core.safety.filter import SafetyProfile, check_recipe

SPICE_WORDS = ["turmeric", "cumin", "coriander", "garam masala", "chilli",
               "chili", "pepper", "mustard", "asafoetida", "cardamom",
               "cinnamon", "clove", "masala", "fenugreek", "kasuri",
               "sambar powder"]


def test_seed_loads_and_has_enough_recipes():
    assert len(load_seed_recipes()) >= 15


def test_ids_are_unique():
    ids = [r.id for r in load_seed_recipes()]
    assert len(ids) == len(set(ids))


def test_every_recipe_uses_at_least_two_spices():
    for recipe in load_seed_recipes():
        names = " ".join(i.name.lower() for i in recipe.ingredients)
        spices = [s for s in SPICE_WORDS if s in names]
        assert len(spices) >= 2, f"{recipe.id} has too few spices: {spices}"


def test_every_recipe_is_vegetarian():
    profile = SafetyProfile(diet="vegetarian")
    for recipe in load_seed_recipes():
        assert check_recipe(recipe, profile) == [], recipe.id
        
def test_second_file_loaded_and_total_is_32():
    ids = {r.id for r in load_seed_recipes()}
    assert len(ids) == 32
    assert {"dosa", "pav-bhaji", "veg-biryani", "sabudana-khichdi"} <= ids