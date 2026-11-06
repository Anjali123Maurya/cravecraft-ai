"""Ingredient name normalization and the staples list.

canonical("Tomatoes") -> "tomato"; canonical("tamatar") -> "tomato".
Names are reduced to a canonical form so user input can be compared with
recipe ingredients.
"""
import re

ALIASES: dict[str, str] = {
    "tamatar": "tomato", "aloo": "potato", "pyaz": "onion", "pyaaz": "onion",
    "matar": "green peas", "peas": "green peas", "green pea": "green peas",
    "gobi": "cauliflower", "phool gobi": "cauliflower",
    "palak": "spinach", "bhindi": "okra", "lady finger": "okra",
    "baingan": "brinjal", "eggplant": "brinjal", "aubergine": "brinjal",
    "shimla mirch": "capsicum", "bell pepper": "capsicum",
    "curd": "yogurt", "dahi": "yogurt",
    "chawal": "rice", "basmati rice": "rice", "cooked rice": "rice",
    "arhar dal": "toor dal", "tur dal": "toor dal",
    "chole": "chickpeas", "kabuli chana": "chickpeas", "chana": "chickpeas",
    "rajma": "kidney beans", "red kidney beans": "kidney beans",
    "besan": "gram flour", "poha": "flattened rice",
    "thick poha": "flattened rice", "sooji": "semolina", "rava": "semolina",
    "suji": "semolina", "hara dhania": "coriander leaves",
    "cilantro": "coriander leaves", "dhania": "coriander leaves",
    "adrak": "ginger", "lahsun": "garlic", "nimbu": "lemon",
    "lemon juice": "lemon", "jeera": "cumin seeds", "cumin": "cumin seeds",
    "haldi": "turmeric powder", "turmeric": "turmeric powder",
    "hari mirch": "green chilli", "green chili": "green chilli",
    "lal mirch": "red chilli powder", "red chili powder": "red chilli powder",
    "moongfali": "peanuts", "peanut": "peanuts", "groundnut": "peanuts",
    "mungfali": "peanuts", "yellow moong dal": "moong dal",
        "atta": "wheat flour", "wheat flour atta": "wheat flour",
    "whole wheat flour": "wheat flour", "sabudana": "sago",
    "sabudana sago pearls": "sago", "tapioca pearls": "sago",
    "masoor dal red lentils": "masoor dal", "red lentils": "masoor dal",
    "bean": "french beans", "green beans": "french beans",
        "bottle gourd lauki": "bottle gourd", "lauki": "bottle gourd",
    "doodhi": "bottle gourd", "tindora ivy gourd": "tindora",
    "ivy gourd": "tindora", "kovakkai": "tindora",
    "ragi flour finger millet": "ragi flour", "sev gram flour noodles": "sev",
    "nylon sev": "sev",
}

# Assumed to be in every kitchen: not counted as "missing" and not scored.
STAPLES = {
    "salt", "oil", "water", "sugar", "cumin seeds", "turmeric powder",
    "red chilli powder", "coriander powder", "garam masala", "mustard seeds",
    "asafoetida", "black pepper", "bay leaf", "cloves", "cinnamon stick",
    "curry leaves", "dried red chilli", "amchur powder", "chana masala powder",
    "sambar powder", "ginger garlic paste",
        "pav bhaji masala", "kasuri methi", "biryani masala", "chaat masala",
    "bisi bele bath powder", "idli podi", "ajwain", "coriander seeds",
    "cardamom", "mint leaves", "fruit salt eno",
}

_PAREN = re.compile(r"\(.*?\)")


def _clean(text: str) -> str:
    text = _PAREN.sub(" ", text.lower())
    return re.sub(r"[^a-z\s]", " ", text).split() and " ".join(
        re.sub(r"[^a-z\s]", " ", text).split())


def _singular(word: str) -> str:
    if word.endswith("oes"):
        return word[:-2]
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return word


def canonical(name: str) -> str:
    """Return the canonical form of an ingredient name ('' if empty)."""
    cleaned = _clean(name or "")
    if not cleaned:
        return ""
    singular = " ".join(_singular(w) for w in cleaned.split())
    for candidate in (cleaned, singular):
        if candidate in ALIASES:
            return ALIASES[candidate]
    # Staples are stored in their natural (plural) form, e.g. "cumin seeds".
    if cleaned in STAPLES:
        return cleaned
    return singular 


def canonical_all(names) -> set[str]:
    return {c for c in (canonical(n) for n in names) if c}  