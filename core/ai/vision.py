"""Ingredient detection from a photo using CLIP (local, CPU, optional).

torch and transformers are imported only when detection is first used, so the
rest of the app and the tests work without them installed.
"""
import logging
from dataclasses import dataclass
from functools import lru_cache

logger = logging.getLogger(__name__)

MODEL_NAME = "openai/clip-vit-base-patch32"

VOCAB = [
    "tomato", "onion", "potato", "green peas", "cauliflower", "spinach",
    "okra", "brinjal", "carrot", "french beans", "capsicum", "garlic",
    "ginger", "green chilli", "coriander leaves", "mint leaves", "lemon",
    "cabbage", "cucumber", "beetroot", "radish", "pumpkin", "sweet potato",
    "mushroom", "corn", "coconut", "curry leaves", "paneer", "yogurt",
    "milk", "butter", "eggs", "rice", "wheat flour", "toor dal", "moong dal",
    "masoor dal", "chickpeas", "kidney beans", "peanuts", "cashew",
    "tamarind", "bread", "banana", "apple",
]
PROMPTS = [f"a photo of {name}, a food ingredient" for name in VOCAB]


class VisionUnavailable(Exception):
    """Raised when torch/transformers or the model are not available."""


@dataclass(frozen=True)
class Detection:
    name: str
    score: float


def make_crops(image) -> list:
    """The full image plus a 3x3 grid, so small items in a pile get seen."""
    image = image.convert("RGB")
    image.thumbnail((640, 640))
    w, h = image.size
    crops = [image.copy()]
    for row in range(3):
        for col in range(3):
            crops.append(image.crop((col * w // 3, row * h // 3,
                                     (col + 1) * w // 3, (row + 1) * h // 3)))
    return crops


def aggregate(crop_probs: list[list[float]], labels: list[str], top_k: int = 3,
              min_prob: float = 0.08, max_items: int = 15) -> list[Detection]:
    """Keep each crop's top_k labels above min_prob; best score per label."""
    best: dict[str, float] = {}
    for probs in crop_probs:
        order = sorted(range(len(labels)), key=lambda i: probs[i], reverse=True)
        for i in order[:top_k]:
            if probs[i] >= min_prob:
                best[labels[i]] = max(best.get(labels[i], 0.0), probs[i])
    ranked = sorted(best.items(), key=lambda kv: kv[1], reverse=True)[:max_items]
    return [Detection(name, round(score, 2)) for name, score in ranked]


class CLIPDetector:
    def __init__(self):
        self._model = None
        self._processor = None
        self._torch = None

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            import torch
            from transformers import CLIPModel, CLIPProcessor
        except ImportError as exc:
            raise VisionUnavailable(
                "Photo detection needs extra packages: "
                "pip install -r requirements-vision.txt") from exc
        try:
            self._torch = torch
            self._processor = CLIPProcessor.from_pretrained(MODEL_NAME)
            self._model = CLIPModel.from_pretrained(MODEL_NAME).eval()
        except Exception as exc:  # download or load failure
            logger.error("Could not load CLIP: %s", exc)
            raise VisionUnavailable(f"Could not load the vision model: {exc}") from exc

    def detect(self, image) -> list[Detection]:
        self._load()
        crops = make_crops(image)
        inputs = self._processor(text=PROMPTS, images=crops,
                                 return_tensors="pt", padding=True)
        with self._torch.no_grad():
            logits = self._model(**inputs).logits_per_image
        return aggregate(logits.softmax(dim=1).tolist(), VOCAB)


@lru_cache
def get_detector() -> CLIPDetector:
    return CLIPDetector()


def detect_ingredients(image) -> list[Detection]:
    return get_detector().detect(image)