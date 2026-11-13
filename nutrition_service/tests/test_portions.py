"""Phase 2B D4: ``get_portions`` reads household-measure gram weights from the saved real replies.

Read-only, separate from nutrient extraction; the calculator does not use it (checked here too).
"""

from __future__ import annotations

import inspect
import json

import httpx
import pytest

from roli_nutrition import ErrorResult, Portion, PortionsResult
from roli_nutrition.portions import PortionsError, extract_portions

from conftest import SENTINEL_KEY, FakeClock, Recorder, error_response, load, make_service, mutate


@pytest.mark.parametrize("fixture, fdc_id, expected", [
    ("food_171413", 171413, [("1 tablespoon", 13.5), ("1 tsp", 4.5), ("1 cup", 216.0)]),
    ("food_170457", 170457, [("1 medium whole (2-3/5\" dia)", 123.0), ("1 slice, medium (1/4\" thick)", 20.0), ("1 large whole (3\" dia)", 182.0),
                             ("1 cherry", 17.0), ("1 Italian tomato", 62.0), ("1 slice, thin/small", 15.0), ("1 cup, chopped or sliced", 180.0),
                             ("1 small whole (2-2/5\" dia)", 91.0), ("1 slice, thick/large (1/2\" thick)", 27.0), ("1 cup cherry tomatoes", 149.0),
                             ("1 wedge (1/4 of medium tomato)", 31.0), ("1 NLEA serving", 148.0), ("1 plum tomato", 62.0)]),
    ("food_169249", 169249, [("1 head", 360.0), ("1 leaf inner", 4.8), ("1 leaf outer", 24.0), ("1 cup shredded", 36.0)]),
    ("food_171999", 171999, [("0.5 fillet", 154.0), ("3 oz", 85.0)]),
    ("food_173706", 173706, [("3 oz", 85.0)]),
])
def test_sr_legacy_portions_read_from_real_replies(fixture, fdc_id, expected):
    result = extract_portions(fdc_id, load(fixture))
    assert isinstance(result, PortionsResult) and result.fdc_id == fdc_id
    assert [(p.label, p.gram_weight) for p in result.portions] == expected
    assert all(p.measure == "undetermined" for p in result.portions)


def test_foundation_portions_use_measure_unit_and_modifier():
    result = extract_portions(747447, load("food_foundation_747447"))
    labels = [(p.label, p.measure, p.modifier, p.gram_weight) for p in result.portions]
    assert labels == [("1 cup, chopped", "cup", "chopped", 76.0), ("1 RACC", "RACC", "", 85.0)]


def test_record_without_portions_gives_empty_list_not_error():
    body = mutate(load("food_171413"), lambda b: b.pop("foodPortions"))
    assert extract_portions(171413, body).portions == []
    body2 = mutate(load("food_171413"), lambda b: b.__setitem__("foodPortions", []))
    assert extract_portions(171413, body2).portions == []


def test_bad_rows_are_skipped_never_repaired():
    def edit(b):
        b["foodPortions"][0]["gramWeight"] = -1          # negative
        b["foodPortions"][1]["amount"] = 0               # zero amount
        b["foodPortions"].append("not a row")
        b["foodPortions"].append({"gramWeight": "13.5", "amount": 1})   # string weight
    result = extract_portions(171413, mutate(load("food_171413"), edit))
    assert [p.label for p in result.portions] == ["1 cup"]


@pytest.mark.parametrize("edit, code", [
    (lambda b: b.__setitem__("fdcId", 172001), "id_mismatch"),
    (lambda b: b.__setitem__("dataType", "Branded"), "unsupported_data_type"),
    (lambda b: b.__setitem__("foodPortions", "x"), "malformed_response"),
    (lambda b: b.__setitem__("description", ""), "malformed_response"),
])
def test_identity_rules_match_nutrient_extraction(edit, code):
    with pytest.raises(PortionsError) as info:
        extract_portions(171413, mutate(load("food_171413"), edit))
    assert info.value.code == code


def test_portions_never_carry_nutrient_values():
    result = extract_portions(171413, load("food_171413"))
    blob = json.dumps(result.model_dump())
    assert "13.808" not in blob and "saturated" not in blob.lower() and "cholesterol" not in blob.lower()
    assert set(Portion.model_fields) == {"amount", "measure", "modifier", "gram_weight", "label"}


# -- through the service ----------------------------------------------------------


def _router(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/food/171413"):
        return httpx.Response(200, json=load("food_171413"))
    if request.url.path.endswith("/food/999"):
        return error_response("error_404")
    return httpx.Response(500, content=b"")


def test_service_get_portions_caches_separately_from_nutrition():
    clock = FakeClock()
    service, rec = make_service(_router, clock=clock)
    first = service.get_portions(171413)
    assert isinstance(first, PortionsResult) and first.portions[0].gram_weight == 13.5
    second = service.get_portions(171413)
    assert second is first and len(rec.requests) == 1                      # cache hit
    nutrition = service.get_nutrition(171413)
    assert nutrition.saturated_fat_g == 13.808 and len(rec.requests) == 2   # a different cache entry, its own fetch


def test_service_get_portions_errors_have_the_usual_shape():
    service, _ = make_service(_router)
    missing = service.get_portions(999)
    assert isinstance(missing, ErrorResult) and missing.error_code == "not_found" and missing.fdc_id == 999
    assert service.get_portions("171413").error_code == "invalid_input"
    assert service.get_portions(True).error_code == "invalid_input"
    down = service.get_portions(5)
    assert down.error_code == "usda_unavailable"
    assert SENTINEL_KEY not in json.dumps(down.model_dump())


def test_calculator_does_not_import_portions():
    import roli_nutrition.recipe.calculator as calc
    import roli_nutrition.recipe.compare as cmp
    src = inspect.getsource(calc) + inspect.getsource(cmp)
    assert "portions" not in src.lower()
