"""Deterministic recipe nutrition calculator (spec: nutrition_service/SPEC_2A_recipe_calculator.md).

    from roli_nutrition.recipe import RecipeCalculator, compare_scenarios
    calc = RecipeCalculator(NutritionService(Settings.from_env()))
    result = calc.calculate({"recipe_name": "...", "servings": 1, "ingredients": [...]})

Pure Python arithmetic in Decimal over validated USDA records. No LLM anywhere.
"""

from .calculator import CALCULATOR_VERSION, RecipeCalculator
from .compare import compare_scenarios
from .models import (
    ComparisonResult,
    IngredientInput,
    IngredientResult,
    NutrientTotal,
    RecipeInput,
    RecipeInvalid,
    RecipeResult,
)

__all__ = [
    "CALCULATOR_VERSION",
    "ComparisonResult",
    "IngredientInput",
    "IngredientResult",
    "NutrientTotal",
    "RecipeCalculator",
    "RecipeInput",
    "RecipeInvalid",
    "RecipeResult",
    "compare_scenarios",
]
