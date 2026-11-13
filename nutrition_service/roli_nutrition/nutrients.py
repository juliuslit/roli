"""Turn one USDA reply into a result. Pure functions: no network, no cache.

``extract_nutrition`` applies the validation rules of spec section 10 in order.
Its only input is the one reply for the one requested food, so a value can
never be taken from another record (rule V15).
"""

from __future__ import annotations

import logging
import math
from typing import Any

from .errors import RoliNutritionError
from .schemas import NUTRIENT_IDS, Candidate, NutritionResult, SearchResult

logger = logging.getLogger("roli_nutrition")

ALLOWED_DATA_TYPES = ("SR Legacy", "Foundation", "Survey (FNDDS)")   # spec v2.2 (2026-11-05): FNDDS values are per 100 g of food as consumed

SATURATED_FAT_ID = NUTRIENT_IDS["saturated_fat_g"]  # 1258
CHOLESTEROL_ID = NUTRIENT_IDS["cholesterol_mg"]  # 1253

# nutrient ID -> (output field, USDA nutrient number, expected unit)
TARGETS: dict[int, tuple[str, str, str]] = {
    SATURATED_FAT_ID: ("saturated_fat_g", "606", "g"),
    CHOLESTEROL_ID: ("cholesterol_mg", "601", "mg"),
}
NUMBER_TO_ID = {number: nid for nid, (_, number, _) in TARGETS.items()}
TOTAL_FAT_ID, TOTAL_FAT_NUMBER = 1004, "204"      # spec v2.5: read like a tracked nutrient, but its absence is not a missing nutrient

MALFORMED = "USDA reply was not in the expected format."


class ExtractionError(RoliNutritionError):
    """The reply failed one of the rules in spec section 10."""


def _is_int(value: Any) -> bool:
    """True for a real integer. ``bool`` is a subclass of ``int`` in Python, so it is excluded."""
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: Any) -> bool:
    return (isinstance(value, (int, float))) and not isinstance(value, bool)


def _validation_failed(rule: str) -> ExtractionError:
    return ExtractionError("validation_failed", f"USDA record failed validation rule {rule}.")


# ---------------------------------------------------------------------------
# Tool 2: one food record -> NutritionResult
# ---------------------------------------------------------------------------


def extract_nutrition(requested_fdc_id: int, body: Any) -> NutritionResult:
    # V1: the body is a JSON object.
    if not isinstance(body, dict):
        raise ExtractionError("malformed_response", MALFORMED)

    # V2: fdcId is an integer and not a boolean.
    fdc_id = body.get("fdcId")
    if not _is_int(fdc_id):
        raise ExtractionError("malformed_response", MALFORMED)

    # V3: it is the food we asked for.
    if fdc_id != requested_fdc_id:
        raise ExtractionError(
            "id_mismatch",
            f"USDA returned FDC ID {fdc_id} for a request for FDC ID {requested_fdc_id}.",
        )

    # V4: SR Legacy, Foundation and Survey (FNDDS) are per-100 g tables; Branded and Experimental are not accepted.
    data_type = body.get("dataType")
    if not isinstance(data_type, str):
        raise ExtractionError("malformed_response", MALFORMED)
    if data_type not in ALLOWED_DATA_TYPES:
        raise ExtractionError(
            "unsupported_data_type",
            f"USDA data type '{data_type[:40]}' is not supported. "
            "Only SR Legacy, Foundation and Survey (FNDDS) foods are.",
        )

    # V5: description is a non-empty string, returned unchanged.
    description = body.get("description")
    if not isinstance(description, str) or description == "":
        raise ExtractionError("malformed_response", MALFORMED)

    # V6: foodNutrients is a list (an empty list means both values are missing).
    rows = body.get("foodNutrients")
    if not isinstance(rows, list):
        raise ExtractionError("malformed_response", MALFORMED)

    # V7 + V8: select rows by nutrient.id, and cross-check id against number both ways.
    selected: dict[int, dict] = {}
    counts: dict[int, int] = {nid: 0 for nid in TARGETS}
    total_fat_rows: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        nutrient = row.get("nutrient")
        if not isinstance(nutrient, dict):
            continue  # V7: rows with no nutrient object are skipped
        nutrient_id = nutrient.get("id")  # never row["id"]: that is a row ID
        number = nutrient.get("number")
        number_str = None if number is None else str(number)

        if nutrient_id == TOTAL_FAT_ID or number_str == TOTAL_FAT_NUMBER:
            if nutrient_id != TOTAL_FAT_ID or number_str != TOTAL_FAT_NUMBER:
                raise _validation_failed("id_number_mismatch")
            total_fat_rows.append(row)
        elif nutrient_id in TARGETS:
            if number_str != TARGETS[nutrient_id][1]:
                raise _validation_failed("id_number_mismatch")
            counts[nutrient_id] += 1
            selected[nutrient_id] = row
        elif number_str in NUMBER_TO_ID:
            # Number says saturated fat or cholesterol, but the ID does not agree.
            raise _validation_failed("id_number_mismatch")

    # V9: at most one row per target nutrient.
    if any(count > 1 for count in counts.values()):
        raise _validation_failed("duplicate_nutrient")

    values: dict[str, float | None] = {}
    missing: list[str] = []
    for nutrient_id, (field, _number, expected_unit) in TARGETS.items():
        row = selected.get(nutrient_id)
        if row is None:
            values[field] = None
            missing.append(field)
            continue

        # V10: the unit is the one we expect, ignoring case.
        unit = row["nutrient"].get("unitName")
        if not isinstance(unit, str) or unit.lower() != expected_unit:
            raise _validation_failed("unit_mismatch")

        # V11: a row without an amount is a missing value, not zero.
        amount = row.get("amount")
        if amount is None:
            values[field] = None
            missing.append(field)
            continue

        # V12: the amount is a real, finite, non-negative number.
        if not _is_number(amount) or not math.isfinite(amount) or amount < 0:
            raise _validation_failed("invalid_amount")

        # V13 + V14: zero only when USDA says zero; float, no rounding.
        values[field] = float(amount)

    # Spec v2.5: total fat passes V9-V12 like the tracked nutrients; a row without an amount is simply unknown.
    if len(total_fat_rows) > 1:
        raise _validation_failed("duplicate_nutrient")
    total_fat: float | None = None
    if total_fat_rows:
        row = total_fat_rows[0]
        unit = row["nutrient"].get("unitName")
        if not isinstance(unit, str) or unit.lower() != "g":
            raise _validation_failed("unit_mismatch")
        amount = row.get("amount")
        if amount is not None:
            if not _is_number(amount) or not math.isfinite(amount) or amount < 0:
                raise _validation_failed("invalid_amount")
            total_fat = float(amount)
    category = body.get("foodCategory") or {}
    survey_category = body.get("wweiaFoodCategory") or {}
    food_category = (category.get("description") if isinstance(category, dict) else category if isinstance(category, str) else None) or (
        survey_category.get("wweiaFoodCategoryDescription") if isinstance(survey_category, dict) else None)

    # V15: every field below comes from `body` alone.
    return NutritionResult(
        status="complete" if not missing else "partial",
        fdc_id=fdc_id,
        description=description,
        data_type=data_type,
        saturated_fat_g=values["saturated_fat_g"],
        cholesterol_mg=values["cholesterol_mg"],
        missing_nutrients=missing,
        total_fat_g=total_fat,
        food_category=food_category if isinstance(food_category, str) else None,
    )


# ---------------------------------------------------------------------------
# Tool 1: search reply -> SearchResult
# ---------------------------------------------------------------------------


def parse_search(query: str, body: Any, limit: int | None = None) -> SearchResult:
    """Read ``foods[]`` into candidates. ``limit`` caps the list after unsupported types are dropped,
    so a reply longer than the requested ``pageSize`` can never pass through uncut."""
    if not isinstance(body, dict):
        raise ExtractionError("malformed_response", MALFORMED)
    foods = body.get("foods")
    if not isinstance(foods, list):
        raise ExtractionError("malformed_response", MALFORMED)

    candidates: list[Candidate] = []
    for entry in foods:
        if not isinstance(entry, dict):
            raise ExtractionError("malformed_response", MALFORMED)
        fdc_id = entry.get("fdcId")
        description = entry.get("description")
        data_type = entry.get("dataType")
        if not _is_int(fdc_id) or not isinstance(description, str) or not isinstance(data_type, str):
            raise ExtractionError("malformed_response", MALFORMED)
        if data_type not in ALLOWED_DATA_TYPES:
            logger.warning(
                '{"call": "search_foods", "dropped_fdc_id": %d, "dropped_data_type": "%s"}',
                fdc_id,
                data_type[:40],
            )
            continue
        # Only these three fields; USDA's rounded nutrient values and score are ignored.
        candidates.append(Candidate(fdc_id=fdc_id, description=description, data_type=data_type))

    if limit is not None:
        candidates = candidates[:limit]
    return SearchResult(query=query, candidates=candidates)
