"""The calculator: validate, fetch USDA references once per record, multiply, sum, divide, reconcile.

Everything is Decimal. Contributions and recipe subtotals are exact; per-serving values are
quantized to six decimal places (spec 2A, section 6). Unresolved ingredients get `null`
contributions and are excluded from subtotals (D8); completeness is per nutrient (section 7).
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from typing import Any

from pydantic import ValidationError

from ..schemas import ErrorResult, NutritionResult
from ..service import NutritionService
from .models import (
    NUTRIENTS,
    Contribution,
    Exclusion,
    IngredientInput,
    IngredientResult,
    Issue,
    NutrientTotal,
    RecipeInput,
    RecipeInvalid,
    RecipeResult,
    UsdaReference,
)
from .preparation import compatibility, record_state

CALCULATOR_VERSION = "2a.1"
HUNDRED = Decimal(100)
PER_SERVING_PLACES = Decimal("0.000001")
PER_SERVING_PRECISION = "6 decimal places"
PER_SERVING_HALF_UNIT = Decimal("0.0000005")
COMPLETENESS_NOTE = (
    "complete = every supplied ingredient was calculated from a validated USDA record with the supplied grams; "
    "it does not verify that the list or weights match the restaurant's dish"
)
UNITS = {"saturated_fat_g": "g", "cholesterol_mg": "mg"}
DISPLAY_PLACES = {"saturated_fat_g": Decimal("0.01"), "cholesterol_mg": Decimal("1")}
DISPLAY_FLOOR = {"saturated_fat_g": "<0.01 g", "cholesterol_mg": "<1 mg"}

MESSAGES = {
    "missing_fdc_id": "{name} has no USDA record; its contribution is unknown and not included.",
    "missing_grams": "{name} has no quantity; its contribution is unknown and not included.",
    "usda_error": "{name}: the USDA lookup for record {fdc_id} failed ({code}); its contribution is unknown and not included.",
    "nutrient_not_reported": "{name}: USDA record {fdc_id} does not report {nutrient}; that nutrient is unknown for this ingredient.",
    "preparation_mismatch": "{name} is declared {state} but USDA record {fdc_id} is a {record_state} food; the weights are not interchangeable, so it is not included.",
    "preparation_unresolved": "{name}: preparation state could not be matched to USDA record {fdc_id} (ingredient {state}, record {record_state}); not included.",
    "as_used_not_accepted_for_flesh": "{name}: 'as_used' is not accepted for meat, fish, poultry or egg (USDA record {fdc_id}); declare raw or cooked. Not included.",
}
INFO_CODES = {"explicit_zero", "per_serving_quantity_converted", "duplicate_fdc_id"}


def display_amount(value: Decimal, nutrient: str) -> str:
    """Round for people (half-up); a positive value that would show as zero becomes '<0.01 g' / '<1 mg'."""
    unit = UNITS[nutrient]
    if value == 0:
        return f"0 {unit}"
    rounded = value.quantize(DISPLAY_PLACES[nutrient], rounding=ROUND_HALF_UP)
    if rounded == 0:
        return DISPLAY_FLOOR[nutrient]
    text = format(rounded, "f")
    return f"{text} {unit}"


class RecipeCalculator:
    def __init__(self, service: NutritionService) -> None:
        self._service = service

    # -- entry point ------------------------------------------------------------

    def calculate(self, recipe: RecipeInput | dict[str, Any]) -> RecipeResult | RecipeInvalid:
        try:
            parsed = recipe if isinstance(recipe, RecipeInput) else RecipeInput.model_validate(recipe)
        except ValidationError as exc:
            problems = [f"{'.'.join(str(p) for p in e['loc']) or 'recipe'}: {e['msg']}" for e in exc.errors()]
            name = recipe.get("recipe_name") if isinstance(recipe, dict) else None
            return RecipeInvalid(recipe_name=name if isinstance(name, str) else None, problems=problems)

        references = self._fetch_references(parsed)
        duplicates = self._duplicate_ids(parsed)
        ingredients = [self._ingredient_result(ing, parsed.servings, references, duplicates) for ing in parsed.ingredients]

        totals = {n: self._total(ingredients, n) for n in NUTRIENTS}
        per_serving = {n: self._per_serving(totals[n], parsed.servings) for n in NUTRIENTS}
        self._reconcile(ingredients, totals, per_serving, parsed.servings)

        issues = self._issues(ingredients)
        status = "complete" if all(t.complete for t in totals.values()) else "incomplete"
        display = {n: self._display(per_serving[n], totals[n], parsed.servings, ingredients, n) for n in NUTRIENTS}
        return RecipeResult(
            status=status, recipe_name=parsed.recipe_name, servings=parsed.servings,
            calculator_version=CALCULATOR_VERSION, per_serving_precision=PER_SERVING_PRECISION,
            completeness_note=COMPLETENESS_NOTE, ingredients=ingredients, totals=totals,
            per_serving=per_serving, issues=issues, display=display,
        )

    # -- references ---------------------------------------------------------------

    def _fetch_references(self, recipe: RecipeInput) -> dict[int, NutritionResult | ErrorResult]:
        """One lookup per distinct FDC ID (the service's cache makes repeats free anyway)."""
        ids = sorted({ing.fdc_id for ing in recipe.ingredients if ing.fdc_id is not None})
        return {fid: self._service.get_nutrition(fid) for fid in ids}

    @staticmethod
    def _duplicate_ids(recipe: RecipeInput) -> set[int]:
        counts: dict[int, int] = {}
        for ing in recipe.ingredients:
            if ing.fdc_id is not None:
                counts[ing.fdc_id] = counts.get(ing.fdc_id, 0) + 1
        return {fid for fid, count in counts.items() if count > 1}

    # -- one ingredient ------------------------------------------------------------

    def _ingredient_result(self, ing: IngredientInput, servings: Decimal, references, duplicates) -> IngredientResult:
        issues: list[str] = []
        grams_in_recipe = ing.grams
        if ing.grams is not None and ing.quantity_basis == "per_serving":
            grams_in_recipe = ing.grams * servings
            issues.append("per_serving_quantity_converted")
        if ing.fdc_id is not None and ing.fdc_id in duplicates:
            issues.append("duplicate_fdc_id")

        usda: UsdaReference | None = None
        usda_error: dict | None = None
        compat = "not_applicable"
        if ing.fdc_id is not None:
            ref = references[ing.fdc_id]
            if isinstance(ref, NutritionResult):
                usda = UsdaReference(
                    fdc_id=ref.fdc_id, description=ref.description, data_type=ref.data_type,
                    saturated_fat_g_per_100g=_dec(ref.saturated_fat_g), cholesterol_mg_per_100g=_dec(ref.cholesterol_mg),
                    record_state=record_state(ref.description),
                )
                compat, compat_issue = compatibility(ing.preparation_state, ref.description)
                if compat_issue:
                    issues.append(compat_issue)
            else:
                usda_error = ref.model_dump()
                issues.append(f"usda_error:{ref.error_code}")
        else:
            issues.append("missing_fdc_id")
        if ing.grams is None:
            issues.append("missing_grams")

        # Explicit zero: contributes exactly nothing, whatever USDA said (0 x anything = 0).
        if grams_in_recipe is not None and grams_in_recipe == 0:
            issues = [i for i in issues if i in INFO_CODES or i == "missing_fdc_id"] + ["explicit_zero"]
            contribution = Contribution(saturated_fat_g=Decimal(0), cholesterol_mg=Decimal(0))
            resolved = {n: True for n in NUTRIENTS}
            return IngredientResult(
                ingredient_id=ing.ingredient_id, name=ing.name, grams_declared=ing.grams, quantity_basis=ing.quantity_basis,
                grams_in_recipe=grams_in_recipe, preparation_state=ing.preparation_state, assumption=ing.assumption,
                usda=usda, usda_error=usda_error, compatibility=compat, contribution=contribution, resolved=resolved,
                issues=issues,
            )

        blocked = ing.fdc_id is None or usda is None or grams_in_recipe is None or compat != "compatible"
        values: dict[str, Decimal | None] = {}
        resolved = {}
        for nutrient in NUTRIENTS:
            reference = getattr(usda, f"{nutrient}_per_100g", None) if usda is not None else None
            if blocked or reference is None:
                values[nutrient] = None          # D8: never a number for an unresolved line
                resolved[nutrient] = False
                if not blocked and reference is None:
                    issues.append(f"nutrient_not_reported:{nutrient}")
            else:
                values[nutrient] = grams_in_recipe * reference / HUNDRED   # exact
                resolved[nutrient] = True
        return IngredientResult(
            ingredient_id=ing.ingredient_id, name=ing.name, grams_declared=ing.grams, quantity_basis=ing.quantity_basis,
            grams_in_recipe=grams_in_recipe, preparation_state=ing.preparation_state, assumption=ing.assumption,
            usda=usda, usda_error=usda_error, compatibility=compat,
            contribution=Contribution(saturated_fat_g=values["saturated_fat_g"], cholesterol_mg=values["cholesterol_mg"]),
            resolved=resolved, issues=issues,
        )

    # -- totals ------------------------------------------------------------------------

    @staticmethod
    def _total(ingredients: list[IngredientResult], nutrient: str) -> NutrientTotal:
        covers, excludes = [], []
        subtotal = Decimal(0)
        for ing in ingredients:
            if ing.resolved[nutrient]:
                covers.append(ing.ingredient_id)
                subtotal += getattr(ing.contribution, nutrient)
            else:
                excludes.append(Exclusion(ingredient_id=ing.ingredient_id, name=ing.name, reason=_exclusion_reason(ing, nutrient)))
        complete = not excludes
        return NutrientTotal(complete=complete, total=subtotal if complete else None, known_subtotal=subtotal,
                             covers=covers, excludes=excludes)

    @staticmethod
    def _per_serving(total: NutrientTotal, servings: Decimal) -> NutrientTotal:
        def q(value: Decimal) -> Decimal:
            return (value / servings).quantize(PER_SERVING_PLACES, rounding=ROUND_HALF_EVEN)
        return NutrientTotal(complete=total.complete, total=q(total.total) if total.total is not None else None,
                             known_subtotal=q(total.known_subtotal), covers=list(total.covers), excludes=list(total.excludes))

    @staticmethod
    def _reconcile(ingredients, totals, per_serving, servings: Decimal) -> None:
        """Internal invariants (spec 2A, section 6). A failure here is a bug, so it raises."""
        for nutrient in NUTRIENTS:
            exact = sum((getattr(i.contribution, nutrient) for i in ingredients if i.resolved[nutrient]), Decimal(0))
            if exact != totals[nutrient].known_subtotal:
                raise ArithmeticError(f"{nutrient}: contributions do not sum to the subtotal")
            back = per_serving[nutrient].known_subtotal * servings
            if abs(back - totals[nutrient].known_subtotal) > PER_SERVING_HALF_UNIT * servings:
                raise ArithmeticError(f"{nutrient}: per-serving value does not reconcile within tolerance")

    @staticmethod
    def _issues(ingredients: list[IngredientResult]) -> list[Issue]:
        out: list[Issue] = []
        for ing in ingredients:
            for code in ing.issues:
                if code in INFO_CODES:
                    continue
                base, _, detail = code.partition(":")
                fdc_id = ing.usda.fdc_id if ing.usda else (ing.usda_error or {}).get("fdc_id")
                template = MESSAGES.get(base, "{name}: {code}.")
                message = template.format(name=ing.name, fdc_id=fdc_id, code=detail or code, nutrient=detail,
                                          state=ing.preparation_state, record_state=ing.usda.record_state if ing.usda else "unknown")
                out.append(Issue(ingredient_id=ing.ingredient_id, code=code, message=message))
        return out

    @staticmethod
    def _display(ps: NutrientTotal, total: NutrientTotal, servings: Decimal, ingredients, nutrient: str) -> str:
        if ps.complete:
            whole = f" ({display_amount(total.total, nutrient)} for the whole recipe, {format(servings, 'f')} servings)" if servings != 1 else ""
            return f"{display_amount(ps.total, nutrient)} per serving{whole}"
        covered, total_n = len(ps.covers), len(ingredients)
        missing = ", ".join(e.name for e in ps.excludes)
        if covered == 0:
            return f"unknown: no ingredient could be calculated for this nutrient; missing: {missing}"
        return f"at least {display_amount(ps.known_subtotal, nutrient)} per serving from {covered} of {total_n} ingredients; missing: {missing}"


def _dec(value: float | None) -> Decimal | None:
    """USDA's float 38.0 becomes Decimal('38'), 3.214 becomes Decimal('3.214'): exact, and whole numbers stay whole."""
    if value is None:
        return None
    d = Decimal(str(value))
    return d.quantize(Decimal(1)) if d == d.to_integral_value() else d


def _exclusion_reason(ing: IngredientResult, nutrient: str) -> str:
    for code in ing.issues:
        base = code.split(":")[0]
        if base in ("missing_fdc_id", "missing_grams", "usda_error", "preparation_mismatch",
                    "preparation_unresolved", "as_used_not_accepted_for_flesh"):
            return code
    if f"nutrient_not_reported:{nutrient}" in ing.issues:
        return f"nutrient_not_reported:{nutrient}"
    return "unresolved"
