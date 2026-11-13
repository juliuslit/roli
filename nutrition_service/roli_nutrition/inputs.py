"""Survey (FNDDS) recipe inputs, read-only (spec v2.2, 2026-11-05). A Survey food such as "Fish, cod, fried" lists the foods it was built from
(``inputFoods``: the raw fish, the batter, the frying oil, the salt), each with its weight per 100 g of the finished food. Roli reads them to show
USDA's own frying-oil amount and to find the raw-flesh share a portion rule needs. Nothing here changes a nutrient value."""

from __future__ import annotations

import math
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from .errors import RoliNutritionError
from .nutrients import ALLOWED_DATA_TYPES

SOURCE = "USDA FoodData Central"
MALFORMED = "USDA returned a reply that is not the expected food object."


class InputsError(RoliNutritionError):
    pass


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class InputFood(_Frozen):
    code: int | None                  # USDA's ingredient code (an FNDDS or SR code, not an FDC ID)
    description: str
    grams_per_100g: float             # USDA's ingredientWeight: the recipe weight BEFORE cooking, not grams in 100 g of finished food (corrected 2026-11-06; see `grams_per_100g_scale`)


class InputsResult(_Frozen):
    status: Literal["complete"] = "complete"
    fdc_id: int
    description: str
    data_type: str
    inputs: list[InputFood]           # empty for SR Legacy and Foundation foods, which are not built from inputs
    # spec v2.4 (2026-11-06): USDA's "Moisture change: -15%" attribute. The input weights are the recipe BEFORE cooking, so they do not add up to 100 g of
    # finished food: finished mass = sum of inputs x (1 + moisture change / 100). None when USDA states no such attribute.
    moisture_change_pct: float | None = None
    source: Literal["USDA FoodData Central"] = SOURCE

    @property
    def grams_per_100g_scale(self) -> float | None:
        """Multiply an input's weight by this to get its grams in 100 g of the finished food; None without inputs or a stated moisture change."""
        total = sum(i.grams_per_100g for i in self.inputs)
        if not total or self.moisture_change_pct is None:
            return None
        return 100.0 / (total * (1.0 + self.moisture_change_pct / 100.0))


def _is_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def extract_inputs(requested_fdc_id: int, body: Any) -> InputsResult:
    if not isinstance(body, dict):
        raise InputsError("malformed_response", MALFORMED)
    fdc_id = body.get("fdcId")
    if not _is_int(fdc_id):
        raise InputsError("malformed_response", MALFORMED)
    if fdc_id != requested_fdc_id:
        raise InputsError("id_mismatch", f"USDA returned FDC ID {fdc_id} for a request for FDC ID {requested_fdc_id}.")
    data_type = body.get("dataType")
    if not isinstance(data_type, str):
        raise InputsError("malformed_response", MALFORMED)
    if data_type not in ALLOWED_DATA_TYPES:
        raise InputsError("unsupported_data_type", f"USDA data type '{data_type[:40]}' is not supported.")
    description = body.get("description")
    if not isinstance(description, str) or not description:
        raise InputsError("malformed_response", MALFORMED)
    rows = body.get("inputFoods") or []
    if not isinstance(rows, list):
        raise InputsError("malformed_response", MALFORMED)
    inputs: list[InputFood] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        grams = row.get("ingredientWeight")
        desc = row.get("ingredientDescription") or row.get("foodDescription")
        if not _is_number(grams) or not math.isfinite(grams) or grams <= 0 or not isinstance(desc, str) or not desc:
            continue
        code = row.get("ingredientCode")
        inputs.append(InputFood(code=code if _is_int(code) else None, description=desc, grams_per_100g=float(grams)))
    return InputsResult(fdc_id=fdc_id, description=description, data_type=data_type, inputs=inputs, moisture_change_pct=_moisture_change(body))


def _moisture_change(body: dict) -> float | None:
    for attr in body.get("foodAttributes") or []:
        value = attr.get("value") if isinstance(attr, dict) else None
        m = re.match(r"\s*moisture change:\s*(-?\d+(?:\.\d+)?)\s*%", value, re.I) if isinstance(value, str) else None
        if m:
            return float(m.group(1))
    return None
