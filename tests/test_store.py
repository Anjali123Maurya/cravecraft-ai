from datetime import date

import pytest

from core.knowledge.loader import load_seed_recipes
from core.recommender.ranker import Preferences, score_recipe
from db.repositories import expiry_status
from db.session import make_store


@pytest.fixture
def store():
    return make_store("sqlite://")  # fresh in-memory database per test


def test_pantry_add_list_remove(store):
    item = store.add_pantry_item("  Tomato ", 4, "piece", notes="fridge")
    assert [i.name for i in store.list_pantry()] == ["Tomato"]
    assert store.remove_pantry_item(item.id) is True
    assert store.remove_pantry_item(item.id) is False
    assert store.list_pantry() == []


def test_pantry_validation(store):
    with pytest.raises(ValueError):
        store.add_pantry_item("   ")
    with pytest.raises(ValueError):
        store.add_pantry_item("rice", -1)
    with pytest.raises(ValueError):
        store.add_pantry_item("milk", purchase_date=date(2026, 11, 5),
                              expiry_date=date(2026, 11, 1))


def test_expiring_soon_includes_expired_and_sorts(store):
    store.add_pantry_item("dal", expiry_date=date(2026, 12, 30))
    store.add_pantry_item("rice")
    store.add_pantry_item("spinach", expiry_date=date(2026, 11, 7))
    store.add_pantry_item("milk", expiry_date=date(2026, 11, 4))
    names = [i.name for i in store.expiring_soon(today=date(2026, 11, 5), days=3)]
    assert names == ["milk", "spinach"]


def test_expiry_status(store):
    today = date(2026, 11, 5)
    mk = lambda d: store.add_pantry_item("x", expiry_date=d)
    assert expiry_status(mk(None), today) == "none"
    assert expiry_status(mk(date(2026, 11, 4)), today) == "expired"
    assert expiry_status(mk(date(2026, 11, 8)), today) == "soon"
    assert expiry_status(mk(date(2026, 11, 9)), today) == "ok"


def test_favorites_save_is_idempotent_and_removable(store):
    store.save_favorite("aloo-matar", "Aloo Matar")
    store.save_favorite("aloo-matar", "Aloo Matar")
    assert len(store.list_favorites()) == 1
    assert store.is_favorite("aloo-matar")
    assert store.remove_favorite("aloo-matar") is True
    assert store.remove_favorite("aloo-matar") is False


def test_rating_rules(store):
    assert store.set_rating("poha", 4) is False  # not a favorite yet
    store.save_favorite("poha", "Kanda Poha")
    assert store.set_rating("poha", 4) is True
    assert store.list_favorites()[0].rating == 4
    store.set_rating("poha", 0)
    assert store.list_favorites()[0].rating is None
    with pytest.raises(ValueError):
        store.set_rating("poha", 6)


def test_history_recent_ids_distinct_newest_first(store):
    store.add_history("a", "A")
    store.add_history("b", "B")
    store.add_history("a", "A")
    assert store.recent_recipe_ids() == ["a", "b"]
    assert store.recent_recipe_ids(limit=1) == ["a"]


def test_use_first_bonus_in_ranker():
    recipe = next(r for r in load_seed_recipes() if r.id == "aloo-matar")
    base = Preferences(pantry=["potatoes", "peas", "onion", "tomato"])
    urgent = Preferences(pantry=base.pantry, use_first=["peas"])
    assert score_recipe(recipe, urgent).score == score_recipe(recipe, base).score + 10