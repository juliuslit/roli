"""Household-measure weights of one USDA food (``foodPortions[]``), read-only (Phase 2B, decision D4).

This module reads *weights* ("1 tablespoon" = 13.5 g), never nutrient values. Phase 1A's rule that
nutrient values are read only from ``foodNutrients`` of the requested record stands; the calculator
in ``recipe/`` does not import this module and is unchanged. Pure functions: no network, no cache.
"""

from __future__ import annotations

import math
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from .errors import RoliNutritionError
from .schemas import SOURCE

ALLOWED_DATA_TYPES = ("SR Legacy", "Foundation", "Survey (FNDDS)")
MALFORMED = "USDA reply was not in the expected format."


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Portion(_Frozen):
    """One household measure: ``amount`` × ``measure`` (+ ``modifier``) weighs ``gram_weight`` grams.

    SR Legacy records put the measure words in ``modifier`` with measure unit "undetermined"
    ("1 tablespoon" -> amount 1, measure "undetermined", modifier "tablespoon"); Foundation records
    use ``measureUnit.name`` ("cup") plus a modifier ("chopped"). ``label`` joins them for display."""

    amount: float
    measure: str                      # measureUnit.name as USDA gives it ("undetermined", "cup", "RACC")
    modifier: str                     # "" when absent
    gram_weight: float
    label: str                        # "1 tablespoon", "1 cup, chopped", "0.5 fillet"


class PortionsResult(_Frozen):
    status: Literal["complete"] = "complete"
    fdc_id: int
    description: str
    data_type: str
    portions: list[Portion]           # may be empty: many records list no household measures
    source: Literal["USDA FoodData Central"] = SOURCE


class PortionsError(RoliNutritionError):
    pass


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _fmt(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


def extract_portions(requested_fdc_id: int, body: Any) -> PortionsResult:
    """Validate the record identity exactly as ``extract_nutrition`` does, then read ``foodPortions``.

    A portion row is kept only when its gram weight and amount are finite positive numbers; rows that
    fail are skipped (they carry no information we could use), never repaired."""
    if not isinstance(body, dict):
        raise PortionsError("malformed_response", MALFORMED)
    fdc_id = body.get("fdcId")
    if not _is_int(fdc_id):
        raise PortionsError("malformed_response", MALFORMED)
    if fdc_id != requested_fdc_id:
        raise PortionsError("id_mismatch", f"USDA returned FDC ID {fdc_id} for a request for FDC ID {requested_fdc_id}.")
    data_type = body.get("dataType")
    if not isinstance(data_type, str):
        raise PortionsError("malformed_response", MALFORMED)
    if data_type not in ALLOWED_DATA_TYPES:
        raise PortionsError("unsupported_data_type", f"USDA data type '{data_type[:40]}' is not supported. Only SR Legacy, Foundation and Survey (FNDDS) foods are.")
    description = body.get("description")
    if not isinstance(description, str) or not description:
        raise PortionsError("malformed_response", MALFORMED)

    rows = body.get("foodPortions")
    if rows is None:
        rows = []
    if not isinstance(rows, list):
        raise PortionsError("malformed_response", MALFORMED)

    portions: list[Portion] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        grams, amount = row.get("gramWeight"), row.get("amount")
        if not _is_number(grams) or not math.isfinite(grams) or grams <= 0:
            continue
        # Survey (FNDDS) rows (spec v2.2): the words are in ``portionDescription`` ("1 large fillet", "1 cup", "Quantity not specified"), ``modifier`` is
        # a numeric code and ``amount`` is absent; the description's leading number is the amount, else 1.
        survey_text = row.get("portionDescription") if isinstance(row.get("portionDescription"), str) else None
        if survey_text and not _is_number(amount):
            m = re.match(r"^\s*(\d+(?:\.\d+)?|\d+/\d+)\s+(.*)$", survey_text.strip())
            amount = (float(m.group(1)) if "/" not in m.group(1) else float(m.group(1).split("/")[0]) / float(m.group(1).split("/")[1])) if m else 1.0
        if not _is_number(amount) or not math.isfinite(amount) or amount <= 0:
            continue
        unit = row.get("measureUnit") if isinstance(row.get("measureUnit"), dict) else {}
        measure = str(unit.get("name") or "undetermined")
        modifier = str(row.get("modifier") or "").strip()
        if survey_text:
            label = survey_text.strip()
            modifier = label.split(" ", 1)[1] if re.match(r"^\d", label) and " " in label else label
        elif measure == "undetermined":
            label = f"{_fmt(amount)} {modifier}".strip()
        else:
            label = f"{_fmt(amount)} {measure}" + (f", {modifier}" if modifier else "")
        portions.append(Portion(amount=float(amount), measure=measure, modifier=modifier, gram_weight=float(grams), label=label))
    return PortionsResult(fdc_id=fdc_id, description=description, data_type=data_type, portions=portions)
