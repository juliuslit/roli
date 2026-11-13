"""Input and output schemas for the recipe calculator. All Pydantic, all `extra="forbid"`.

Quantities are `Decimal`. A JSON number such as 0.1 is a float in Python; converting through
`str()` keeps what was typed, and strings like "85" are accepted directly. `None` means unknown.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator, model_validator

NUTRIENTS = ("saturated_fat_g", "cholesterol_mg")
Nutrient = Literal["saturated_fat_g", "cholesterol_mg"]
PreparationState = Literal["raw", "cooked", "as_used", "unknown"]
RecordState = Literal["raw", "cooked", "unknown"]
QuantityBasis = Literal["total_recipe", "per_serving"]
Compatibility = Literal["compatible", "mismatch", "unresolved", "not_applicable"]

MAX_INGREDIENTS = 100


def to_decimal(value: Any) -> Any:
    """Accept Decimal, int, str or float (never bool); reject NaN and infinities. None passes through."""
    if value is None or isinstance(value, Decimal):
        if isinstance(value, Decimal) and not value.is_finite():
            raise ValueError("must be a finite number")
        return value
    if isinstance(value, bool):
        raise ValueError("must be a number, not a boolean")
    if isinstance(value, (int, float, str)):
        try:
            result = Decimal(str(value).strip())
        except InvalidOperation:
            raise ValueError(f"'{value}' is not a number") from None
        if not result.is_finite():
            raise ValueError("must be a finite number")
        return result
    raise ValueError("must be a number")


DecimalField = Annotated[Decimal, BeforeValidator(to_decimal)]
OptionalDecimalField = Annotated[Decimal | None, BeforeValidator(to_decimal)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class IngredientInput(_Strict):
    name: str = Field(min_length=1, max_length=200)
    fdc_id: int | None = None                      # None = no USDA record chosen (unresolved)
    grams: OptionalDecimalField = None             # None = unknown quantity; "0" = explicit zero
    preparation_state: PreparationState = "unknown"
    quantity_basis: QuantityBasis = "total_recipe"
    assumption: str | None = Field(default=None, max_length=500)
    ingredient_id: str | None = Field(default=None, min_length=1, max_length=40)

    @field_validator("fdc_id", mode="before")
    @classmethod
    def _fdc_id_rule(cls, value):
        """Strict: a real JSON integer or null. "171999", 171999.0 and true are rejected, not coerced."""
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError("fdc_id must be a whole number of 1 or more, or null")
        return value

    @field_validator("grams")
    @classmethod
    def _grams_rule(cls, value):
        if value is not None and value < 0:
            raise ValueError("grams must be 0 or more")
        return value


class RecipeInput(_Strict):
    recipe_name: str = Field(min_length=1, max_length=200)
    servings: DecimalField
    ingredients: list[IngredientInput] = Field(min_length=1, max_length=MAX_INGREDIENTS)

    @field_validator("servings")
    @classmethod
    def _servings_rule(cls, value: Decimal):
        if value <= 0:
            raise ValueError("servings must be greater than 0")
        return value

    @model_validator(mode="after")
    def _assign_ids(self):
        seen: set[str] = set()
        for index, ingredient in enumerate(self.ingredients, start=1):
            if ingredient.ingredient_id is None:
                ingredient.ingredient_id = f"ing_{index:02d}"
            if ingredient.ingredient_id in seen:
                raise ValueError(f"duplicate ingredient_id '{ingredient.ingredient_id}'")
            seen.add(ingredient.ingredient_id)
        return self


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class UsdaReference(_Strict):
    fdc_id: int
    description: str
    data_type: str
    saturated_fat_g_per_100g: Decimal | None
    cholesterol_mg_per_100g: Decimal | None
    record_state: RecordState


class Contribution(_Strict):
    saturated_fat_g: Decimal | None
    cholesterol_mg: Decimal | None


class IngredientResult(_Strict):
    ingredient_id: str
    name: str
    grams_declared: Decimal | None
    quantity_basis: QuantityBasis
    grams_in_recipe: Decimal | None
    preparation_state: PreparationState
    assumption: str | None
    usda: UsdaReference | None
    usda_error: dict[str, Any] | None
    compatibility: Compatibility
    contribution: Contribution
    resolved: dict[Nutrient, bool]
    issues: list[str]


class Exclusion(_Strict):
    ingredient_id: str
    name: str
    reason: str


class NutrientTotal(_Strict):
    complete: bool
    total: Decimal | None
    known_subtotal: Decimal
    covers: list[str]
    excludes: list[Exclusion]


class Issue(_Strict):
    ingredient_id: str | None
    code: str
    message: str


class RecipeResult(_Strict):
    status: Literal["complete", "incomplete"]
    recipe_name: str
    servings: Decimal
    calculator_version: str
    source: Literal["USDA FoodData Central"] = "USDA FoodData Central"
    per_serving_precision: str
    completeness_note: str
    ingredients: list[IngredientResult]
    totals: dict[Nutrient, NutrientTotal]
    per_serving: dict[Nutrient, NutrientTotal]
    issues: list[Issue]
    display: dict[Nutrient, str]


class RecipeInvalid(_Strict):
    status: Literal["invalid_recipe"] = "invalid_recipe"
    recipe_name: str | None
    problems: list[str]


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------


class ExcludedScenario(_Strict):
    recipe_name: str
    reason: str


class NutrientComparison(_Strict):
    n_scenarios: int
    n_complete: int
    values: dict[str, Decimal]
    min: Decimal | None
    median: Decimal | None
    max: Decimal | None
    range_meaningful: bool
    excluded: list[ExcludedScenario]
    note: str


class ComparisonResult(_Strict):
    basis: Literal["per_serving", "totals"]
    nutrients: dict[Nutrient, NutrientComparison]
    scenarios: list[RecipeResult | RecipeInvalid]
    note: str
