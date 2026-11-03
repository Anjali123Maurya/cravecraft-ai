"""Benchmark local Ollama models for recipe generation.

Run from the project root:
    python -m scripts.benchmark_llm --models qwen2.5:1.5b --runs 1

Measures: speed, valid JSON, valid schema, use of the user's ingredients,
and forbidden-ingredient violations (allergy/diet).
"""
import argparse
import json
import re
import time
from pathlib import Path

import ollama
from pydantic import ValidationError

from core.schemas import Recipe

PEANUTS = ["peanut", "groundnut", "moongfali"]
DAIRY = ["paneer", "ghee", "butter", "milk", "cream", "yogurt", "curd",
         "cheese", "honey"]

TEST_CASES = [
    {
        "name": "aloo_matar",
        "ingredients": ["potatoes", "peas", "onion", "tomato"],
        "craving": "spicy and comforting",
        "diet": "vegetarian",
        "forbidden": [],
    },
    {
        "name": "paneer_creamy",
        "ingredients": ["paneer", "capsicum", "onion", "tomato", "milk"],
        "craving": "creamy, restaurant-style",
        "diet": "vegetarian",
        "forbidden": [],
    },
    {
        "name": "vegan_peanut_allergy",
        "ingredients": ["chickpeas", "spinach", "onion", "tomato", "rice"],
        "craving": "crunchy and savory",
        "diet": "vegan",
        "forbidden": PEANUTS + DAIRY,  # peanut allergy + vegan
    },
]

SYSTEM_PROMPT = (
    "You are a careful home-cooking assistant. Reply ONLY with JSON matching "
    "the schema. Use the user's ingredients. You may also use basic staples "
    "(salt, oil, water, common spices). Any other ingredient must go in "
    "missing_ingredients and be marked in_pantry=false. Respect the diet and "
    "never include forbidden ingredients. Write short, clear steps."
)


def build_user_prompt(case: dict) -> str:
    return (
        f"Ingredients I have: {', '.join(case['ingredients'])}\n"
        f"Craving: {case['craving']}\n"
        f"Cuisine: Indian\nDiet: {case['diet']}\n"
        f"Forbidden: {', '.join(case['forbidden']) or 'none'}\n"
        "Serves 2. Give me one recipe."
    )


def stem(word: str) -> str:
    """Very rough singularizer: potatoes -> potato, peas -> pea."""
    word = word.lower().strip()
    if word.endswith("oes"):
        return word[:-2]
    if word.endswith("s") and len(word) > 3:
        return word[:-1]
    return word


def run_case(client, model: str, case: dict, num_ctx: int, num_predict: int) -> dict:
    result = {"case": case["name"], "json_ok": False, "schema_ok": False,
              "pantry_use": 0.0, "violations": [], "tok_s": 0.0,
              "seconds": 0.0, "error": ""}
    start = time.perf_counter()
    try:
        resp = client.chat(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(case)},
            ],
            format=Recipe.model_json_schema(),  # forces JSON shaped like Recipe
            options={"temperature": 0.3, "num_ctx": num_ctx,
                     "num_predict": num_predict},
        )
    except Exception as exc:  # connection errors, missing model, etc.
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result

    result["seconds"] = time.perf_counter() - start
    if resp.eval_count and resp.eval_duration:
        result["tok_s"] = resp.eval_count / (resp.eval_duration / 1e9)

    raw = resp.message.content or ""
    out_dir = Path("data/raw/benchmarks")  # gitignored
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_model = re.sub(r"[^A-Za-z0-9.]+", "_", model)
    (out_dir / f"{safe_model}__{case['name']}.json").write_text(raw, encoding="utf-8")

    try:
        data = json.loads(raw)
        result["json_ok"] = True
    except json.JSONDecodeError:
        result["error"] = "invalid JSON (possibly cut off by num_predict)"
        return result

    try:
        recipe = Recipe.model_validate(data)
        result["schema_ok"] = True
    except ValidationError as exc:
        result["error"] = f"schema: {exc.error_count()} validation error(s)"
        return result

    text = " ".join(i.name.lower() for i in recipe.ingredients)
    used = sum(stem(i) in text for i in case["ingredients"])
    result["pantry_use"] = used / len(case["ingredients"])

    full_text = (text + " " + " ".join(recipe.steps)).lower()
    result["violations"] = [w for w in case["forbidden"] if w in full_text]
    return result


def summarize(model: str, results: list[dict]) -> None:
    n = len(results)
    ok = [r for r in results if r["schema_ok"]]
    avg = lambda key: sum(r[key] for r in ok) / len(ok) if ok else 0.0
    violations = sum(len(r["violations"]) for r in results)
    print(f"\n=== {model}: {n} runs ===")
    print(f"JSON valid:           {sum(r['json_ok'] for r in results)}/{n}")
    print(f"Schema valid:         {len(ok)}/{n}")
    print(f"Avg speed:            {avg('tok_s'):.1f} tokens/s")
    print(f"Avg time per recipe:  {avg('seconds'):.1f} s")
    print(f"Uses your ingredients: {avg('pantry_use') * 100:.0f}%")
    print(f"Forbidden-ingredient hits: {violations}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", default=["qwen2.5:1.5b"])
    parser.add_argument("--runs", type=int, default=1, help="repeats per test case")
    parser.add_argument("--num-ctx", type=int, default=4096)
    parser.add_argument("--num-predict", type=int, default=1200)
    args = parser.parse_args()

    client = ollama.Client()
    for model in args.models:
        print(f"\nTesting {model} ...")
        results = []
        for case in TEST_CASES:
            for run in range(args.runs):
                r = run_case(client, model, case, args.num_ctx, args.num_predict)
                results.append(r)
                status = "OK" if r["schema_ok"] else f"FAIL ({r['error']})"
                print(f"  {case['name']} run {run + 1}: {status} | "
                      f"{r['seconds']:.0f}s | {r['tok_s']:.1f} tok/s | "
                      f"violations: {r['violations'] or 'none'}")
        summarize(model, results)


if __name__ == "__main__":
    main()