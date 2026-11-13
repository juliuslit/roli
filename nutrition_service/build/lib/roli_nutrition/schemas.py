"""Output models. Every result the library hands back is one of these.

``extra="forbid"`` means a model refuses unknown keys, so the output shape can
never silently grow. ``frozen=True`` means a result cannot be edited after it is
built, which matters because the same object is kept in the cache.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, PrivateAttr, model_serializer

SOURCE = "USDA FoodData Central"

DataType = Literal["SR Legacy", "Foundation"]

ErrorCode = Literal[
    "invalid_input",
    "not_found",
    "unsupported_data_type",
    "id_mismatch",
    "validation_failed",
    "malformed_response",
    "rate_limited",
    "usda_auth_failed",
    "usda_unavailable",
]

# Fixed mapping, returned in every nutrition result so a reader can see which
# USDA nutrient each number came from.
NUTRIENT_IDS: dict[str, int] = {"saturated_fat_g": 1258, "cholesterol_mg": 1253}


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Candidate(_Frozen):
    fdc_id: int
    description: str
    data_type: DataType


class SearchResult(_Frozen):
    status: Literal["complete"] = "complete"
    query: str
    candidates: list[Candidate]
    source: Literal["USDA FoodData Central"] = SOURCE


class NutritionResult(_Frozen):
    status: Literal["complete", "partial"]
    fdc_id: int
    description: str
    data_type: DataType
    basis: Literal["per_100g"] = "per_100g"
    saturated_fat_g: float | None
    cholesterol_mg: float | None
    missing_nutrients: list[str]
    nutrient_ids: dict[str, int] = NUTRIENT_IDS
    source: Literal["USDA FoodData Central"] = SOURCE


class ErrorResult(_Frozen):
    """One shape for every failure.

    A get-nutrition error carries ``fdc_id``; a search error carries ``query``
    instead. The model remembers which tool produced it (``_tool``) and drops the
    other key when turned into a dict or JSON, so each error has exactly the
    documented keys.
    """

    status: Literal["error"] = "error"
    fdc_id: int | None = None
    query: str | None = None
    error_code: ErrorCode
    message: str

    _tool: Literal["food", "search"] = PrivateAttr(default="food")

    @classmethod
    def for_food(cls, fdc_id: int | None, error_code: ErrorCode, message: str) -> "ErrorResult":
        result = cls(fdc_id=fdc_id, error_code=error_code, message=message)
        result._tool = "food"
        return result

    @classmethod
    def for_search(cls, query: str | None, error_code: ErrorCode, message: str) -> "ErrorResult":
        result = cls(query=query, error_code=error_code, message=message)
        result._tool = "search"
        return result

    @model_serializer(mode="wrap")
    def _keep_one_subject_key(self, handler) -> dict[str, Any]:
        data = handler(self)
        data.pop("query" if self._tool == "food" else "fdc_id", None)
        return data


Result = NutritionResult | SearchResult | ErrorResult
