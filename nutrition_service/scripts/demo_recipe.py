"""Print the Phase 2A worked examples against the real USDA API (about 7 USDA calls, cached after the first).

    nutrition_service/.venv/bin/python scripts/demo_recipe.py

All ingredient weights are HYPOTHETICAL and labelled as such; they illustrate the calculator,
they do not measure the restaurant's dishes.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from roli_nutrition import NutritionService, Settings  # noqa: E402
from roli_nutrition.recipe import RecipeCalculator, compare_scenarios  # noqa: E402

BLUEFIN, OLIVE, CHINOOK, LETTUCE, TAHINI, ROMANO, SESAME = 173706, 171413, 171999, 169249, 170189, 171249, 170151


def ing(name, fdc_id, grams, state="as_used", assumption="hypothetical weight"):
    return {"name": name, "fdc_id": fdc_id, "grams": grams, "preparation_state": state, "assumption": assumption}


def show(title, obj):
    print(f"\n### {title}\n```json")
    print(json.dumps(obj.model_dump(mode="json"), indent=2, ensure_ascii=False))
    print("```")


def main() -> int:
    logging.disable(logging.CRITICAL)
    load_dotenv(SERVICE_DIR.parent / ".env")
    calc = RecipeCalculator(NutritionService(Settings.from_env()))

    complete = calc.calculate({"recipe_name": "Little Gem Lettuces (hypothetical weights)", "servings": 1, "ingredients": [
        ing("Little gem lettuce (green leaf lettuce as the nearest USDA record)", LETTUCE, "80", "raw", "hypothetical: a starter-sized salad"),
        ing("Tahini vinaigrette (tahini)", TAHINI, "25", assumption="hypothetical: 2 tablespoons"),
        ing("Pecorino sardo (USDA romano as the nearest record)", ROMANO, "10", assumption="hypothetical: a light grating"),
        ing("Toasted sesame", SESAME, "5", assumption="hypothetical: a sprinkle"),
    ]})
    show("1. Complete recipe: Little Gem Lettuces", complete)

    crudo = calc.calculate({"recipe_name": "Bluefin crudo, scenario A (hypothetical weights)", "servings": 1, "ingredients": [
        ing("Bluefin tuna, raw", BLUEFIN, "85", "raw", "hypothetical: typical crudo portion"),
        ing("Bottarga", None, "5", "as_used", "no USDA record selected"),
        ing("Olive oil", OLIVE, "10", assumption="hypothetical: drizzle"),
    ]})
    show("2. Incomplete recipe: Bluefin Crudo with bottarga unmatched", crudo)

    family = calc.calculate({"recipe_name": "Salmon for four (hypothetical weights)", "servings": 4, "ingredients": [
        ing("Chinook salmon, cooked", CHINOOK, "600", "cooked", "hypothetical: 150 g cooked per person"),
        ing("Olive oil", OLIVE, "20", assumption="hypothetical: for the pan"),
    ]})
    show("3. Four servings", family)

    lean = calc.calculate({"recipe_name": "Crudo A, lean", "servings": 1, "ingredients": [
        ing("Bluefin tuna, raw", BLUEFIN, "85", "raw"), ing("Olive oil", OLIVE, "5")]})
    oily = calc.calculate({"recipe_name": "Crudo C, oily", "servings": 1, "ingredients": [
        ing("Bluefin tuna, raw", BLUEFIN, "110", "raw"), ing("Olive oil", OLIVE, "15")]})
    comparison = compare_scenarios([lean, crudo, oily])
    print("\n### 4. Three scenarios compared (per serving)\n```json")
    print(json.dumps({k: v for k, v in comparison.model_dump(mode="json").items() if k != "scenarios"}, indent=2))
    print("```")
    return 0


if __name__ == "__main__":
    sys.exit(main())
