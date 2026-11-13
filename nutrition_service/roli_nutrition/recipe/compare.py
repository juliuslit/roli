"""Compare manually supplied recipe scenarios (spec 2A, section 9). Deterministic; no inference."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from .models import NUTRIENTS, ComparisonResult, ExcludedScenario, NutrientComparison, RecipeInvalid, RecipeResult

NOTE = (
    "Ranges describe the supplied recipes only: not a statistical confidence interval and "
    "not a guaranteed range for the restaurant's dish."
)


def _median(values: list[Decimal]) -> Decimal:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def compare_scenarios(results: list[RecipeResult | RecipeInvalid], basis: Literal["per_serving", "totals"] = "per_serving") -> ComparisonResult:
    if len(results) < 1:
        raise ValueError("at least one scenario is required")
    names = [r.recipe_name or f"scenario_{i + 1}" for i, r in enumerate(results)]
    if len(set(names)) != len(names):
        raise ValueError("scenario recipe names must be distinct")
    valid = [r for r in results if isinstance(r, RecipeResult)]
    if basis == "totals" and len({r.servings for r in valid}) > 1:
        raise ValueError("basis 'totals' needs every scenario to have the same servings; use 'per_serving'")

    nutrients = {}
    for nutrient in NUTRIENTS:
        values: dict[str, Decimal] = {}
        excluded: list[ExcludedScenario] = []
        for name, r in zip(names, results):
            if isinstance(r, RecipeInvalid):
                excluded.append(ExcludedScenario(recipe_name=name, reason="invalid_recipe"))
                continue
            block = r.per_serving[nutrient] if basis == "per_serving" else r.totals[nutrient]
            if block.complete and block.total is not None:
                values[name] = block.total
            else:
                excluded.append(ExcludedScenario(recipe_name=name, reason="incomplete"))
        n_complete = len(values)
        meaningful = n_complete >= 2
        if n_complete == 0:
            note = f"No scenario was complete for this nutrient; evidence is insufficient for a range. {NOTE}"
        elif n_complete == 1:
            note = f"Only 1 of {len(results)} scenarios was complete for this nutrient; evidence is insufficient for a meaningful range. {NOTE}"
        else:
            note = f"Range across the {n_complete} modeled recipes that were complete for this nutrient. {NOTE}"
        vals = list(values.values())
        nutrients[nutrient] = NutrientComparison(
            n_scenarios=len(results), n_complete=n_complete, values=values,
            min=min(vals) if vals else None, median=_median(vals) if vals else None, max=max(vals) if vals else None,
            range_meaningful=meaningful, excluded=excluded, note=note,
        )
    return ComparisonResult(basis=basis, nutrients=nutrients, scenarios=list(results), note=NOTE)
