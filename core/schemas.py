"""Pydantic models that define what a valid CraveCraft recipe looks like.

Pydantic checks the LLM's JSON against these rules. If the model returns
bad data (missing fields, wrong types, absurd times), validation fails
and we can retry instead of showing garbage to the user.
"""
from typing import Literal

from pydantic import BaseModel, Field


class RecipeIngredient(BaseModel):
    name: str = Field(min_length=1)
    quantity: float | None = Field(default=None, ge=0)
    unit: str = ""  # g, ml, cup, tsp, tbsp, piece ...
    in_pantry: bool = True  # False means the user must buy it


class Recipe(BaseModel):
    name: str = Field(min_length=1)
    description: str
    cuisine: str
    flavor_profile: list[str]
    prep_time_min: int = Field(ge=0, le=600)
    cook_time_min: int = Field(ge=0, le=600)
    difficulty: Literal["easy", "medium", "hard"]
    servings: int = Field(ge=1, le=20)
    ingredients: list[RecipeIngredient] = Field(min_length=2)
    missing_ingredients: list[str] = Field(default_factory=list)
    steps: list[str] = Field(min_length=3)
    tips: list[str] = Field(default_factory=list)
    substitutions: list[str] = Field(default_factory=list)
    image_prompt: str = ""

    @property
    def total_time_min(self) -> int:
        return self.prep_time_min + self.cook_time_min
    


class Adaptation(BaseModel):
    """The only thing the LLM is allowed to write."""
    description: str = Field(min_length=10, max_length=300)
    tips: list[str] = Field(default_factory=list, max_length=4)
    substitutions: list[str] = Field(default_factory=list, max_length=4)