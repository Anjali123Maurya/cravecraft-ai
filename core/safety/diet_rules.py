"""Diet rules. Each diet lists extra forbidden keywords and which allergen
groups it also excludes (reused from allergens.py, so nothing is duplicated).

Vegetarian follows the Indian convention: no eggs. Use "eggetarian" to allow them.
"""

MEAT_AND_ANIMAL = [
    "chicken", "mutton", "lamb", "goat", "beef", "pork", "bacon", "ham",
    "sausage", "salami", "pepperoni", "turkey", "duck", "venison", "rabbit",
    "meat", "keema", "fish", "prawn", "shrimp", "crab", "lobster", "squid",
    "salmon", "tuna", "sardine", "anchovy", "anchovies", "oyster", "mussel",
    "clam", "bone broth", "gelatin", "gelatine", "lard", "tallow",
]

JAIN_EXTRA = [
    "onion", "pyaz", "garlic", "lahsun", "potato", "aloo", "sweet potato",
    "carrot", "gajar", "radish", "mooli", "beetroot", "beet", "ginger",
    "adrak", "turnip", "yam", "arbi", "mushroom", "shallot", "leek",
]

DIETS: dict[str, dict] = {
    "non_vegetarian": {"label": "Non-vegetarian",
                       "keywords": [], "include_allergens": []},
    "eggetarian": {"label": "Eggetarian",
                   "keywords": MEAT_AND_ANIMAL, "include_allergens": []},
    "vegetarian": {"label": "Vegetarian",
                   "keywords": MEAT_AND_ANIMAL, "include_allergens": ["eggs"]},
    "vegan": {"label": "Vegan",
              "keywords": MEAT_AND_ANIMAL + ["honey", "shahad"],
              "include_allergens": ["dairy", "eggs"]},
    "jain": {"label": "Jain",
             "keywords": MEAT_AND_ANIMAL + JAIN_EXTRA,
             "include_allergens": ["eggs"]},
}