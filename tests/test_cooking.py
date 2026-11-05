import json

from core.ai.llm_client import LLMUnavailable
from core.knowledge.loader import load_seed_recipes
from core.safety.filter import SafetyProfile
from core.services.cooking import (answer_question, quick_answer,
                                   step_ingredients, step_timers)


class FakeLLM:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = 0

    def generate_json(self, system, user, schema, temperature=None):
        item = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        if isinstance(item, Exception):
            raise item
        return item


def recipe(recipe_id):
    return next(r for r in load_seed_recipes() if r.id == recipe_id)


def test_timers_use_upper_end_of_range():
    found = step_timers("Cook for 6-8 minutes. Then fry for 30 seconds.")
    assert found == [("8 min", 480), ("30 sec", 30)]


def test_no_time_means_no_timers():
    assert step_timers("Chop the onion finely.") == []


def test_step_ingredients_does_not_match_oil_inside_boil():
    names = {i.name for i in step_ingredients(recipe("dal-tadka"), 0)}
    assert {"toor dal", "turmeric powder", "salt", "water"} <= names
    assert "oil" not in names and "onion" not in names


def test_step_ingredients_for_onion_step():
    names = {i.name for i in step_ingredients(recipe("aloo-matar"), 2)}
    assert {"onion", "ginger garlic paste"} <= names
    assert "potato" not in names


def test_quick_answer_for_thick_gravy():
    answer = quick_answer("My gravy is too thick. What should I do?",
                          SafetyProfile(diet="vegan"))
    assert answer and "hot water" in answer


def test_quick_answer_blocked_when_it_breaks_the_diet():
    question = "Can I replace cream with milk?"
    assert quick_answer(question, SafetyProfile(diet="vegetarian"))
    assert quick_answer(question, SafetyProfile(diet="vegan")) is None


def test_ai_answer_used_and_safe():
    good = json.dumps({"answer": "Add a pinch of garam masala at the end."})
    reply = answer_question("What gives it more aroma?", recipe("dal-tadka"), 0,
                            SafetyProfile(diet="vegan"), llm=FakeLLM(good))
    assert reply.source == "ai" and "garam masala" in reply.text


def test_unsafe_ai_answer_is_refused_after_retry():
    bad = json.dumps({"answer": "Finish it with a spoon of ghee."})
    llm = FakeLLM(bad)
    reply = answer_question("How can I make it taste richer?", recipe("dal-tadka"),
                            0, SafetyProfile(diet="vegan"), llm=llm)
    assert reply.source == "none" and llm.calls == 2 and "ghee" not in reply.text


def test_llm_unavailable_gives_friendly_message():
    reply = answer_question("What gives it more aroma?", recipe("dal-tadka"), 0,
                            SafetyProfile(), llm=FakeLLM(LLMUnavailable("down")))
    assert reply.source == "none" and "not available" in reply.text


def test_empty_question():
    reply = answer_question("   ", recipe("dal-tadka"), 0, SafetyProfile(),
                            llm=FakeLLM())
    assert reply.text == "Type a question first."