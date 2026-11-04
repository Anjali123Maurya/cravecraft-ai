"""Try the full pipeline from the terminal (needs Ollama running).

Example:
    python -m scripts.demo_adapt --pantry paneer capsicum onion tomato --craving spicy creamy
    python -m scripts.demo_adapt --pantry chickpeas onion tomato --diet vegan --allergen peanuts
"""
import argparse
import logging
import time

from core.ai.adapter import adapt_recipe
from core.knowledge.loader import load_seed_recipes
from core.recommender.ranker import Preferences, rank_recipes
from core.safety.filter import SafetyProfile, safe_recipes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pantry", nargs="+", required=True)
    parser.add_argument("--craving", nargs="*", default=[])
    parser.add_argument("--diet", default="vegetarian")
    parser.add_argument("--allergen", nargs="*", default=[])
    parser.add_argument("--avoid", nargs="*", default=[])
    parser.add_argument("--minutes", type=int, default=None)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    profile = SafetyProfile(diet=args.diet, allergens=args.allergen,
                            custom_avoid=args.avoid)
    prefs = Preferences(pantry=args.pantry, cravings=args.craving,
                        max_total_minutes=args.minutes)

    ranked = rank_recipes(safe_recipes(load_seed_recipes(), profile), prefs)
    if not ranked:
        print("No safe recipes found for this profile.")
        return
    print("\nTop matches:")
    for m in ranked:
        print(f"  {m.score:>6}  {m.recipe.name}  (missing: {m.missing or 'nothing'})")

    start = time.perf_counter()
    result = adapt_recipe(ranked[0], prefs, profile)
    seconds = time.perf_counter() - start

    recipe = result.recipe
    print(f"\n=== {recipe.name} | AI used: {result.used_llm} | "
          f"{result.attempts} attempt(s) | {seconds:.0f}s ===")
    print(recipe.description)
    print(f"Time: {recipe.total_time_min} min | {recipe.difficulty} | serves {recipe.servings}")
    print("\nIngredients:")
    for ing in recipe.ingredients:
        mark = " " if ing.in_pantry else "*"
        print(f" {mark} {ing.quantity or ''} {ing.unit} {ing.name}")
    print("  (* = you need to buy this)")
    print("\nSteps:")
    for i, step in enumerate(recipe.steps, 1):
        print(f"  {i}. {step}")
    print("\nTips:", *recipe.tips, sep="\n  - ")
    print("\nSubstitutions:", *(recipe.substitutions or ["none"]), sep="\n  - ")
    for warning in result.warnings:
        print("\nWarning:", warning)


if __name__ == "__main__":
    main()     