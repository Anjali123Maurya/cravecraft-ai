"""Loads and validates the hand-written seed recipes.

Every recipe is checked against the same Recipe schema the LLM output uses,
so a typo in the JSON fails loudly at startup instead of later in the UI.
"""
import json
from functools import lru_cache
from pathlib import Path

from core.schemas import Recipe

SEED_PATH = Path(__file__).with_name("recipes_seed.json")


class SeedRecipe(Recipe):
    id: str
    region: str


@lru_cache
def load_seed_recipes() -> tuple[SeedRecipe, ...]:
    data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    return tuple(SeedRecipe.model_validate(item) for item in data)