"""Allergen keyword map (plain data, easy to extend).

keywords:     words that mean the allergen is present.
safe_phrases: phrases that CONTAIN a keyword but do not contain the allergen
              (e.g. "coconut milk" is not dairy). They are removed before
              matching. Matching is on whole words, with simple plurals.

This is keyword matching, not a guarantee. The UI must tell users to check
packaged-food labels themselves.
"""

ALLERGENS: dict[str, dict[str, list[str]]] = {
    "peanuts": {
        "keywords": ["peanut", "groundnut", "moongfali", "mungfali", "monkey nut"],
        "safe_phrases": [],
    },
    "tree_nuts": {
        "keywords": ["almond", "badam", "cashew", "kaju", "walnut", "akhrot",
                     "pistachio", "pista", "hazelnut", "pecan", "macadamia",
                     "brazil nut", "pine nut", "chilgoza", "mixed nut",
                     "praline", "marzipan"],
        "safe_phrases": [],
    },
    "dairy": {
        "keywords": ["milk", "paneer", "ghee", "butter", "buttermilk", "cream",
                     "yogurt", "yoghurt", "curd", "dahi", "cheese", "khoya",
                     "khoa", "mawa", "malai", "chaas", "lassi", "whey",
                     "casein", "kulfi"],
        "safe_phrases": ["coconut milk", "coconut cream", "almond milk",
                         "soy milk", "soya milk", "oat milk", "cashew milk",
                         "cashew cream", "rice milk", "plant based milk",
                         "cocoa butter", "shea butter", "peanut butter",
                         "almond butter", "cashew butter", "butter bean",
                         "vegan butter", "vegan cheese", "vegan cream"],
    },
    "gluten": {
        "keywords": ["wheat", "atta", "maida", "flour", "semolina", "sooji",
                     "suji", "rava", "rawa", "barley", "rye", "bread",
                     "breadcrumb", "panko", "pasta", "spaghetti", "macaroni",
                     "noodle", "vermicelli", "seviyan", "roti", "chapati",
                     "chapatti", "naan", "paratha", "kulcha", "pav", "bun",
                     "couscous", "seitan", "bulgur", "dalia", "soy sauce",
                     "biscuit", "cracker", "tortilla"],
        "safe_phrases": ["rice flour", "gram flour", "besan", "chickpea flour",
                         "corn flour", "cornflour", "almond flour",
                         "coconut flour", "ragi flour", "jowar flour",
                         "bajra flour", "buckwheat flour", "potato flour",
                         "tapioca flour", "millet flour", "rice noodle"],
    },
    "soy": {
        "keywords": ["soy", "soya", "soybean", "soyabean", "tofu", "tempeh",
                     "edamame", "miso", "nutrela"],
        "safe_phrases": [],
    },
    "sesame": {
        "keywords": ["sesame", "til", "tahini", "gingelly"],
        "safe_phrases": [],
    },
    "mustard": {
        "keywords": ["mustard", "rai", "sarson", "kasundi"],
        "safe_phrases": [],
    },
    "eggs": {
        "keywords": ["egg", "omelette", "omelet", "mayonnaise", "mayo",
                     "meringue", "albumen"],
        "safe_phrases": ["eggless mayonnaise", "eggless mayo",
                         "vegan mayonnaise", "vegan mayo"],
    },
}

# Labels for the UI tick-boxes.
ALLERGEN_LABELS: dict[str, str] = {
    "peanuts": "Peanuts",
    "tree_nuts": "Tree nuts (almond, cashew, walnut...)",
    "dairy": "Dairy",
    "gluten": "Gluten (wheat, maida...)",
    "soy": "Soy",
    "sesame": "Sesame",
    "mustard": "Mustard",
    "eggs": "Eggs",
}