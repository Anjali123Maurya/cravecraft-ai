import json

import pytest

from core.ai.adapter import adapt_recipe
from core.ai.llm_client import LLMClient, LLMUnavailable
from core.knowledge.loader import load_seed_recipes
from core.recommender.ranker import Preferences, score_recipe
from core.safety.filter import SafetyProfile, safe_recipes

GOOD = json.dumps({
    "description": "A spicy, comforting potato and pea curry that suits your craving.",
    "tips": ["Brown the onions well."],
    "substitutions": ["No tomato? Add a squeeze of lemon at the end."],
})


class FakeLLM:
    """Returns canned responses in order (the last one repeats)."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = 0

    def generate_json(self, system, user, schema, temperature=None):
        item = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        if isinstance(item, Exception):
            raise item
        return item


def setup(recipe_id, pantry, profile):
    recipes = safe_recipes(load_seed_recipes(), profile)
    recipe = next(r for r in recipes if r.id == recipe_id)
    prefs = Preferences(pantry=pantry, cravings=["spicy"])
    return score_recipe(recipe, prefs), prefs


def test_success_sets_description_and_pantry_flags():
    profile = SafetyProfile(diet="vegetarian")
    match, prefs = setup("aloo-matar", ["potatoes", "peas", "onion"], profile)
    result = adapt_recipe(match, prefs, profile, llm=FakeLLM(GOOD))
    assert result.used_llm and result.attempts == 1
    assert "comforting" in result.recipe.description
    flags = {i.name: i.in_pantry for i in result.recipe.ingredients}
    assert flags["tomato"] is False and flags["potato"] is True
    assert flags["cumin seeds"] is True  # staple
    assert "tomato" in result.recipe.missing_ingredients


def test_unsafe_description_retried_then_falls_back():
    profile = SafetyProfile(diet="vegan")
    match, prefs = setup("dal-tadka", ["toor dal", "onion", "tomato"], profile)
    bad = json.dumps({"description": "Creamy dal finished with ghee.", "tips": [],
                      "substitutions": []})
    llm = FakeLLM(bad)
    result = adapt_recipe(match, prefs, profile, llm=llm)
    assert not result.used_llm and result.attempts == 2 and llm.calls == 2
    assert result.recipe.description == match.recipe.description


def test_second_attempt_can_succeed():
    profile = SafetyProfile(diet="vegan")
    match, prefs = setup("dal-tadka", ["toor dal", "onion", "tomato"], profile)
    bad = json.dumps({"description": "Creamy dal finished with ghee.", "tips": [],
                      "substitutions": []})
    good = json.dumps({"description": "A simple, savory dal with a sizzling tempering.",
                       "tips": [], "substitutions": []})
    result = adapt_recipe(match, prefs, profile, llm=FakeLLM(bad, good))
    assert result.used_llm and result.attempts == 2


def test_unsafe_tip_line_is_dropped_but_rest_kept():
    profile = SafetyProfile(diet="vegan")
    match, prefs = setup("chana-masala", ["chickpeas", "onion", "tomato"], profile)
    raw = json.dumps({"description": "A tangy, robust chickpea masala for you.",
                      "tips": ["Finish with a spoon of ghee.", "Add lemon at the end."],
                      "substitutions": []})
    result = adapt_recipe(match, prefs, profile, llm=FakeLLM(raw))
    joined = " ".join(result.recipe.tips).lower()
    assert result.used_llm and "ghee" not in joined and "lemon" in joined


def test_invalid_json_falls_back_to_original():
    profile = SafetyProfile(diet="vegetarian")
    match, prefs = setup("aloo-matar", ["potatoes", "peas"], profile)
    result = adapt_recipe(match, prefs, profile, llm=FakeLLM("not json at all"))
    assert not result.used_llm and result.warnings
    assert result.recipe.steps == match.recipe.steps


def test_llm_unavailable_still_returns_a_recipe():
    profile = SafetyProfile(diet="vegetarian")
    match, prefs = setup("aloo-matar", ["potatoes", "peas"], profile)
    result = adapt_recipe(match, prefs, profile,
                          llm=FakeLLM(LLMUnavailable("server down")))
    assert not result.used_llm
    assert any("not available" in w for w in result.warnings)


def test_llm_client_wraps_connection_errors():
    class Broken:
        def chat(self, **kwargs):
            raise ConnectionError("refused")

    with pytest.raises(LLMUnavailable):
        LLMClient(client=Broken()).generate_json("s", "u", {})  