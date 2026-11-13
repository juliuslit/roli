"""Pure extraction and validation (spec section 10), on real saved replies and edited copies."""

from __future__ import annotations

import pytest

from roli_nutrition.nutrients import ExtractionError, extract_nutrition, parse_search
from roli_nutrition.schemas import NutritionResult, SearchResult

from captured_expectations import BRANDED, CHINOOK, FOUNDATION_ANIMAL, FOUNDATION_PLANT, PINK
from conftest import FOOD_171999, FOOD_172001, load, mutate


def expect_error(requested_id, body, code, rule: str | None = None) -> ExtractionError:
    with pytest.raises(ExtractionError) as info:
        extract_nutrition(requested_id, body)
    assert info.value.code == code
    if rule is not None:
        assert rule in info.value.message
    return info.value


def row_for(body: dict, nutrient_id: int) -> dict:
    rows = [r for r in body["foodNutrients"] if r.get("nutrient", {}).get("id") == nutrient_id]
    assert len(rows) == 1
    return rows[0]


# -- A and B: the two salmon records ----------------------------------------


def test_a_chinook_complete(chinook_body):
    result = extract_nutrition(FOOD_171999, chinook_body)
    assert isinstance(result, NutritionResult)
    assert result.status == "complete"
    assert result.fdc_id == CHINOOK["fdc_id"]
    assert result.description == CHINOOK["description"]
    assert result.data_type == "SR Legacy"
    assert result.saturated_fat_g == 3.214
    assert result.cholesterol_mg == 85.0
    assert result.missing_nutrients == []
    assert result.nutrient_ids == {"saturated_fat_g": 1258, "cholesterol_mg": 1253}
    assert result.basis == "per_100g"


def test_b_pink_complete(pink_body):
    result = extract_nutrition(FOOD_172001, pink_body)
    assert result.status == "complete"
    assert result.description == PINK["description"]
    assert result.saturated_fat_g == 0.971
    assert result.cholesterol_mg == 55.0


def test_b_chinook_never_carries_pink_values(chinook_body):
    result = extract_nutrition(FOOD_171999, chinook_body)
    assert result.saturated_fat_g != 0.971
    assert result.cholesterol_mg != 55.0


# -- I: unfiltered replies give the same output ----------------------------


@pytest.mark.parametrize("fdc_id, filtered, unfiltered", [
    (FOOD_171999, "food_171999", "food_171999_unfiltered"),
    (FOOD_172001, "food_172001", "food_172001_unfiltered"),
])
def test_i_unfiltered_equivalence(fdc_id, filtered, unfiltered):
    # the filtered fixtures were captured before total fat was requested (spec v2.5); everything else must agree
    assert extract_nutrition(fdc_id, load(filtered)) == extract_nutrition(fdc_id, load(unfiltered)).model_copy(update={"total_fat_g": None})


def total_fat_row(amount):
    return {"nutrient": {"id": 1004, "number": "204", "name": "Total lipid (fat)", "unitName": "g"}, "amount": amount}


def test_v25_total_fat_is_read_and_is_not_a_tracked_nutrient(chinook_body):
    body = mutate(chinook_body, lambda b: b["foodNutrients"].append(total_fat_row(13.38)))
    result = extract_nutrition(171999, body)
    assert result.total_fat_g == 13.38 and result.status == "complete" and result.missing_nutrients == []
    assert result.food_category == "Finfish and Shellfish Products"
    assert extract_nutrition(171999, chinook_body).total_fat_g is None and extract_nutrition(171999, chinook_body).status == "complete"     # absent is unknown, never zero


def test_v25_total_fat_passes_the_same_checks(chinook_body):
    from roli_nutrition.nutrients import ExtractionError
    for row in (total_fat_row(-1), {**total_fat_row(1), "nutrient": {"id": 1004, "number": "204", "unitName": "mg"}}, {**total_fat_row(1), "nutrient": {"id": 1005, "number": "204", "unitName": "g"}}):
        with pytest.raises(ExtractionError):
            extract_nutrition(171999, mutate(chinook_body, lambda b: b["foodNutrients"].append(row)))
    with pytest.raises(ExtractionError):
        extract_nutrition(171999, mutate(chinook_body, lambda b: b["foodNutrients"].extend([total_fat_row(1), total_fat_row(2)])))


def test_v25_a_survey_record_names_its_category(chinook_body):
    body = mutate(chinook_body, lambda b: (b.pop("foodCategory"), b.update(wweiaFoodCategory={"wweiaFoodCategoryDescription": "Fish"})))
    assert extract_nutrition(171999, body).food_category == "Fish"


def test_i_unfiltered_has_heading_rows_without_amount():
    body = load("food_171999_unfiltered")
    headings = [r for r in body["foodNutrients"] if "amount" not in r]
    assert len(headings) >= 1  # spec 5.6 saw 6; the exact count is USDA's, not ours


# -- D: missing values -------------------------------------------------------


def test_d_cholesterol_row_removed(chinook_body):
    body = mutate(chinook_body, lambda b: b["foodNutrients"].remove(row_for(b, 1253)))
    result = extract_nutrition(FOOD_171999, body)
    assert result.status == "partial"
    assert result.cholesterol_mg is None
    assert result.saturated_fat_g == 3.214
    assert result.missing_nutrients == ["cholesterol_mg"]


def test_d_row_present_without_amount(chinook_body):
    body = mutate(chinook_body, lambda b: row_for(b, 1253).pop("amount"))
    result = extract_nutrition(FOOD_171999, body)
    assert result.status == "partial"
    assert result.cholesterol_mg is None
    assert result.missing_nutrients == ["cholesterol_mg"]


def test_d_amount_null(chinook_body):
    body = mutate(chinook_body, lambda b: row_for(b, 1253).update(amount=None))
    result = extract_nutrition(FOOD_171999, body)
    assert result.cholesterol_mg is None
    assert result.missing_nutrients == ["cholesterol_mg"]


def test_d_empty_food_nutrients(chinook_body):
    body = mutate(chinook_body, lambda b: b.update(foodNutrients=[]))
    result = extract_nutrition(FOOD_171999, body)
    assert result.status == "partial"
    assert result.saturated_fat_g is None
    assert result.cholesterol_mg is None
    assert result.missing_nutrients == ["saturated_fat_g", "cholesterol_mg"]


def test_d_missing_never_becomes_zero(chinook_body):
    body = mutate(chinook_body, lambda b: b.update(foodNutrients=[]))
    result = extract_nutrition(FOOD_171999, body)
    assert result.saturated_fat_g is not 0 and result.saturated_fat_g is None  # noqa: F632


def test_d_real_foundation_plant_food():
    if FOUNDATION_PLANT is None:
        pytest.fail("Fill FOUNDATION_PLANT in captured_expectations.py after running capture_fixtures.py")
    result = extract_nutrition(FOUNDATION_PLANT["fdc_id"], load(FOUNDATION_PLANT["file"]))
    assert result.data_type == "Foundation"
    assert result.description == FOUNDATION_PLANT["description"]
    assert result.status == FOUNDATION_PLANT["status"]
    assert result.saturated_fat_g == FOUNDATION_PLANT["saturated_fat_g"]
    assert result.cholesterol_mg == FOUNDATION_PLANT["cholesterol_mg"]
    expected_missing = [k for k in ("saturated_fat_g", "cholesterol_mg") if FOUNDATION_PLANT[k] is None]
    assert result.missing_nutrients == expected_missing


def test_real_foundation_animal_food():
    if FOUNDATION_ANIMAL is None:
        pytest.fail("Fill FOUNDATION_ANIMAL in captured_expectations.py after running capture_fixtures.py")
    result = extract_nutrition(FOUNDATION_ANIMAL["fdc_id"], load(FOUNDATION_ANIMAL["file"]))
    assert result.data_type == "Foundation"
    assert result.description == FOUNDATION_ANIMAL["description"]
    assert result.status == FOUNDATION_ANIMAL["status"]
    assert result.saturated_fat_g == FOUNDATION_ANIMAL["saturated_fat_g"]
    assert result.cholesterol_mg == FOUNDATION_ANIMAL["cholesterol_mg"]


# -- E: ID mismatch -----------------------------------------------------------


def test_e_id_mismatch(chinook_body):
    body = mutate(chinook_body, lambda b: b.update(fdcId=FOOD_172001))
    err = expect_error(FOOD_171999, body, "id_mismatch")
    assert "172001" in err.message and "171999" in err.message


# -- F: structural failures and validation rules ------------------------------


@pytest.mark.parametrize("body", ["not an object", 42, None, [1, 2]])
def test_f_body_not_object(body):
    expect_error(FOOD_171999, body, "malformed_response")


@pytest.mark.parametrize("bad_id", [None, "171999", 171999.0, True])
def test_f_fdcid_wrong_type(chinook_body, bad_id):
    body = mutate(chinook_body, lambda b: b.update(fdcId=bad_id))
    expect_error(FOOD_171999, body, "malformed_response")


def test_f_fdcid_missing(chinook_body):
    body = mutate(chinook_body, lambda b: b.pop("fdcId"))
    expect_error(FOOD_171999, body, "malformed_response")


@pytest.mark.parametrize("field", ["description", "dataType", "foodNutrients"])
def test_f_required_field_missing(chinook_body, field):
    body = mutate(chinook_body, lambda b: b.pop(field))
    expect_error(FOOD_171999, body, "malformed_response")


@pytest.mark.parametrize("bad", ["", None, 5])
def test_f_description_wrong(chinook_body, bad):
    body = mutate(chinook_body, lambda b: b.update(description=bad))
    expect_error(FOOD_171999, body, "malformed_response")


@pytest.mark.parametrize("data_type", ["Branded", "Experimental", "sr legacy"])
def test_f_unsupported_data_type(chinook_body, data_type):
    body = mutate(chinook_body, lambda b: b.update(dataType=data_type))
    err = expect_error(FOOD_171999, body, "unsupported_data_type")
    assert data_type in err.message


def test_f_real_branded_detail():
    if BRANDED is None:
        pytest.fail("Fill BRANDED in captured_expectations.py after running capture_fixtures.py")
    err = expect_error(BRANDED["fdc_id"], load(BRANDED["file"]), "unsupported_data_type")
    assert "Branded" in err.message


def test_f_v8_id_number_mismatch_on_selected_row(chinook_body):
    body = mutate(chinook_body, lambda b: row_for(b, 1258)["nutrient"].update(number="601"))
    expect_error(FOOD_171999, body, "validation_failed", "id_number_mismatch")


def test_f_v8_number_claims_target_but_id_differs(chinook_body):
    # A row numbered "601" (cholesterol) that carries a foreign nutrient ID.
    body = mutate(chinook_body, lambda b: row_for(b, 1253)["nutrient"].update(id=9999))
    expect_error(FOOD_171999, body, "validation_failed", "id_number_mismatch")


def test_f_v9_duplicate_row_same_amount(chinook_body):
    import copy
    body = mutate(chinook_body, lambda b: b["foodNutrients"].append(copy.deepcopy(row_for(b, 1253))))
    expect_error(FOOD_171999, body, "validation_failed", "duplicate_nutrient")


@pytest.mark.parametrize("unit", ["mg", "MG", "kcal", None])
def test_f_v10_unit_mismatch_on_saturated_fat(chinook_body, unit):
    body = mutate(chinook_body, lambda b: row_for(b, 1258)["nutrient"].update(unitName=unit))
    expect_error(FOOD_171999, body, "validation_failed", "unit_mismatch")


def test_f_v10_unit_case_is_ignored(chinook_body):
    body = mutate(chinook_body, lambda b: row_for(b, 1258)["nutrient"].update(unitName="G"))
    assert extract_nutrition(FOOD_171999, body).saturated_fat_g == 3.214


@pytest.mark.parametrize("amount", [-1, "3.2", True, float("nan"), float("inf")])
def test_f_v12_invalid_amount(chinook_body, amount):
    body = mutate(chinook_body, lambda b: row_for(b, 1258).update(amount=amount))
    expect_error(FOOD_171999, body, "validation_failed", "invalid_amount")


def test_v13_zero_is_returned_as_zero(chinook_body):
    body = mutate(chinook_body, lambda b: row_for(b, 1253).update(amount=0))
    result = extract_nutrition(FOOD_171999, body)
    assert result.cholesterol_mg == 0.0
    assert result.status == "complete"
    assert result.missing_nutrients == []


def test_v14_no_rounding(chinook_body):
    body = mutate(chinook_body, lambda b: row_for(b, 1258).update(amount=3.2145678))
    assert extract_nutrition(FOOD_171999, body).saturated_fat_g == 3.2145678


def test_v7_row_id_is_never_used(chinook_body):
    # Make the row IDs look like nutrient IDs; the selection must not be fooled.
    def edit(b):
        for row in b["foodNutrients"]:
            row["id"] = 1258
        b["foodNutrients"].remove(row_for(b, 1253))
    body = mutate(chinook_body, edit)
    result = extract_nutrition(FOOD_171999, body)
    assert result.cholesterol_mg is None and result.saturated_fat_g == 3.214


def test_v7_rows_without_nutrient_object_are_skipped(chinook_body):
    body = mutate(chinook_body, lambda b: b["foodNutrients"].extend([{"id": 1, "amount": 99}, "junk", None]))
    assert extract_nutrition(FOOD_171999, body).cholesterol_mg == 85.0


# -- C: search parsing -----------------------------------------------------------


def test_c_search_candidates_match_usda_order():
    body = load("search_king_salmon")
    result = parse_search("king salmon cooked dry heat", body)
    assert isinstance(result, SearchResult)
    expected = [
        {"fdc_id": f["fdcId"], "description": f["description"], "data_type": f["dataType"]}
        for f in body["foods"]
        if f["dataType"] in ("SR Legacy", "Foundation")
    ]
    assert [c.model_dump() for c in result.candidates] == expected
    assert result.query == "king salmon cooked dry heat"
    assert result.source == "USDA FoodData Central"


def test_c_candidates_carry_no_nutrient_fields():
    result = parse_search("king salmon cooked dry heat", load("search_king_salmon"))
    assert result.candidates, "the king salmon search returned nothing; check the fixture"
    for candidate in result.candidates:
        assert set(candidate.model_dump()) == {"fdc_id", "description", "data_type"}


def test_c_records_whether_171999_appears(record_property, capsys):
    result = parse_search("king salmon cooked dry heat", load("search_king_salmon"))
    ids = [c.fdc_id for c in result.candidates]
    record_property("king_salmon_contains_171999", FOOD_171999 in ids)
    with capsys.disabled():
        print(f"\n[recorded] 'king salmon cooked dry heat' candidates: {ids}; contains 171999: {FOOD_171999 in ids}")


def test_c_other_data_types_are_dropped_and_logged(caplog):
    body = mutate(load("search_king_salmon"), lambda b: b["foods"].insert(0, {
        "fdcId": 1, "description": "Some branded thing", "dataType": "Branded"}))
    result = parse_search("x", body)
    assert all(c.fdc_id != 1 for c in result.candidates)
    assert "dropped_fdc_id" in caplog.text


def test_c_zero_results_is_not_an_error():
    result = parse_search("zzzz", {"foods": []})
    assert result.candidates == [] and result.status == "complete"


@pytest.mark.parametrize("body", ["text", None, {"nope": []}, {"foods": "x"}, {"foods": [{"fdcId": "1"}]}])
def test_c_malformed_search(body):
    with pytest.raises(ExtractionError) as info:
        parse_search("x", body)
    assert info.value.code == "malformed_response"


def test_c_parse_search_limit_applies_after_dropping_unsupported_types():
    body = mutate(load("search_king_salmon"), lambda b: b["foods"].insert(0, {
        "fdcId": 1, "description": "Branded first", "dataType": "Branded"}))
    result = parse_search("x", body, limit=2)
    original = load("search_king_salmon")["foods"]
    assert [c.fdc_id for c in result.candidates] == [original[0]["fdcId"], original[1]["fdcId"]]
