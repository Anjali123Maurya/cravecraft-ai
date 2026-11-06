from PIL import Image

from core.ai.vision import PROMPTS, VOCAB, aggregate, make_crops


def test_vocab_is_unique_and_matches_prompts():
    assert len(VOCAB) == len(set(VOCAB)) == len(PROMPTS)


def test_make_crops_gives_full_image_plus_grid():
    crops = make_crops(Image.new("RGB", (100, 80)))
    assert len(crops) == 10
    assert crops[0].size == (100, 80) and crops[1].size == (33, 26)


def test_aggregate_merges_crops_and_keeps_best_score():
    probs = [[0.6, 0.3, 0.1], [0.1, 0.2, 0.7], [0.8, 0.1, 0.1]]
    found = aggregate(probs, ["a", "b", "c"], top_k=1)
    assert [(d.name, d.score) for d in found] == [("a", 0.8), ("c", 0.7)]


def test_aggregate_drops_low_confidence():
    found = aggregate([[0.2, 0.2, 0.6]], ["a", "b", "c"], top_k=3, min_prob=0.25)
    assert [d.name for d in found] == ["c"]