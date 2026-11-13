# Checkpoint 1A: core package and tests

Date: 2026-11-01. Spec: `SPEC.md` v2.1, section 14. Status: **Phase 1A complete; stopped, waiting for approval to start Phase 1B.**

## 1. Summary

| Item | Result |
|---|---|
| Offline tests (`pytest -v`) | **129 passed, 4 skipped** (the 4 live tests skip unless `ROLI_LIVE_TESTS=1`), 0 failed |
| Live tests (`ROLI_LIVE_TESTS=1`) | **4 passed** against the real USDA API |
| `get_nutrition(171999)` | complete, 3.214 g saturated fat, 85.0 mg cholesterol, "Fish, salmon, chinook, cooked, dry heat", SR Legacy |
| `get_nutrition(172001)` | complete, 0.971 g, 55.0 mg, "Fish, salmon, pink, cooked, dry heat", SR Legacy |
| `X-Api-Key` header | accepted (first capture call returned 200; the same request without the key returned 403 `API_KEY_MISSING`) |
| USDA calls made in this phase | 15 (capture) + 4 (live tests) + 4 x 2 (demo, run twice) + 3 (timing sample) = 30 |
| Fixtures | 15 real saved replies, 1,062,456 bytes on disk, SHA-256 in `tests/fixtures/usda/manifest.json` |

Everything in spec 13.3 (tests A to K, O, P) is implemented and green. Full output is in section 3 and in `test_report_1A.txt`.

## 2. What was built, in plain language

`roli_nutrition/` is a small Python library with one job: given a USDA food ID, fetch that one record, check it, and return saturated fat and cholesterol per 100 g, or a clear error. It is split so each file has one responsibility:

| File | Responsibility |
|---|---|
| `config.py` | Reads the key and two cache settings from environment variables. Never opens files, never prints values. |
| `usda_client.py` | The only code that talks to the network. Builds the two requests exactly as spec 5.3 and 5.4 say, sends the key in the `X-Api-Key` header, retries twice on transient failures (after 0.5 s and 1.0 s), and turns HTTP status codes into our nine error codes. Never retries a 429. |
| `nutrients.py` | Pure functions. Takes one USDA reply and applies validation rules V1 to V15 in order. Has no network and no cache, so a value can only ever come from the one reply it was given. |
| `schemas.py` | The output shapes (Pydantic models). `extra="forbid"` means the shape cannot silently grow; `frozen=True` means a result cannot be edited after it is built. |
| `service.py` | Ties it together: checks inputs, calls the client, validates, caches good results (never errors), writes one JSON log line per call, and never raises to its caller. One lock protects the cache, so many threads can call it at once. |
| `errors.py` | One tiny exception type (code + fixed message) that the service turns into an `ErrorResult`. Added for clarity; not in the spec's file list. |

Two scripts: `scripts/capture_fixtures.py` saved the real USDA replies; `scripts/demo.py` prints the results below.

## 3. Test results

Counts: offline run 129 passed, 4 skipped; live run 4 passed. The four "skipped" lines in the offline run are the live tests, which only run when `ROLI_LIVE_TESTS=1` is set. Both runs are reproduced here exactly as saved in `test_report_1A.txt`.

```text
============================= test session starts ==============================
platform darwin -- Python 3.13.5, pytest-8.4.2, pluggy-1.7.0 -- /Users/juliuslitinskas/projects/roli/nutrition_service/.venv/bin/python
cachedir: .pytest_cache
rootdir: /Users/juliuslitinskas/projects/roli/nutrition_service
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.16.0
collecting ... collected 133 items

tests/test_isolation.py::test_o_core_imports_no_forbidden_modules PASSED [  0%]
tests/test_live.py::test_live_a_chinook SKIPPED (set ROLI_LIVE_TESTS...) [  1%]
tests/test_live.py::test_live_b_pink SKIPPED (set ROLI_LIVE_TESTS=1 ...) [  2%]
tests/test_live.py::test_live_search_king_salmon SKIPPED (set ROLI_L...) [  3%]
tests/test_live.py::test_live_not_found SKIPPED (set ROLI_LIVE_TESTS...) [  3%]
tests/test_nutrients.py::test_a_chinook_complete PASSED                  [  4%]
tests/test_nutrients.py::test_b_pink_complete PASSED                     [  5%]
tests/test_nutrients.py::test_b_chinook_never_carries_pink_values PASSED [  6%]
tests/test_nutrients.py::test_i_unfiltered_equivalence[171999-food_171999-food_171999_unfiltered] PASSED [  6%]
tests/test_nutrients.py::test_i_unfiltered_equivalence[172001-food_172001-food_172001_unfiltered] PASSED [  7%]
tests/test_nutrients.py::test_i_unfiltered_has_heading_rows_without_amount PASSED [  8%]
tests/test_nutrients.py::test_d_cholesterol_row_removed PASSED           [  9%]
tests/test_nutrients.py::test_d_row_present_without_amount PASSED        [  9%]
tests/test_nutrients.py::test_d_amount_null PASSED                       [ 10%]
tests/test_nutrients.py::test_d_empty_food_nutrients PASSED              [ 11%]
tests/test_nutrients.py::test_d_missing_never_becomes_zero PASSED        [ 12%]
tests/test_nutrients.py::test_d_real_foundation_plant_food PASSED        [ 12%]
tests/test_nutrients.py::test_real_foundation_animal_food PASSED         [ 13%]
tests/test_nutrients.py::test_e_id_mismatch PASSED                       [ 14%]
tests/test_nutrients.py::test_f_body_not_object[not an object] PASSED    [ 15%]
tests/test_nutrients.py::test_f_body_not_object[42] PASSED               [ 15%]
tests/test_nutrients.py::test_f_body_not_object[None] PASSED             [ 16%]
tests/test_nutrients.py::test_f_body_not_object[body3] PASSED            [ 17%]
tests/test_nutrients.py::test_f_fdcid_wrong_type[None] PASSED            [ 18%]
tests/test_nutrients.py::test_f_fdcid_wrong_type[171999] PASSED          [ 18%]
tests/test_nutrients.py::test_f_fdcid_wrong_type[171999.0] PASSED        [ 19%]
tests/test_nutrients.py::test_f_fdcid_wrong_type[True] PASSED            [ 20%]
tests/test_nutrients.py::test_f_fdcid_missing PASSED                     [ 21%]
tests/test_nutrients.py::test_f_required_field_missing[description] PASSED [ 21%]
tests/test_nutrients.py::test_f_required_field_missing[dataType] PASSED  [ 22%]
tests/test_nutrients.py::test_f_required_field_missing[foodNutrients] PASSED [ 23%]
tests/test_nutrients.py::test_f_description_wrong[] PASSED               [ 24%]
tests/test_nutrients.py::test_f_description_wrong[None] PASSED           [ 24%]
tests/test_nutrients.py::test_f_description_wrong[5] PASSED              [ 25%]
tests/test_nutrients.py::test_f_unsupported_data_type[Branded] PASSED    [ 26%]
tests/test_nutrients.py::test_f_unsupported_data_type[Survey (FNDDS)] PASSED [ 27%]
tests/test_nutrients.py::test_f_unsupported_data_type[Experimental] PASSED [ 27%]
tests/test_nutrients.py::test_f_unsupported_data_type[sr legacy] PASSED  [ 28%]
tests/test_nutrients.py::test_f_real_branded_detail PASSED               [ 29%]
tests/test_nutrients.py::test_f_v8_id_number_mismatch_on_selected_row PASSED [ 30%]
tests/test_nutrients.py::test_f_v8_number_claims_target_but_id_differs PASSED [ 30%]
tests/test_nutrients.py::test_f_v9_duplicate_row_same_amount PASSED      [ 31%]
tests/test_nutrients.py::test_f_v10_unit_mismatch_on_saturated_fat[mg] PASSED [ 32%]
tests/test_nutrients.py::test_f_v10_unit_mismatch_on_saturated_fat[MG] PASSED [ 33%]
tests/test_nutrients.py::test_f_v10_unit_mismatch_on_saturated_fat[kcal] PASSED [ 33%]
tests/test_nutrients.py::test_f_v10_unit_mismatch_on_saturated_fat[None] PASSED [ 34%]
tests/test_nutrients.py::test_f_v10_unit_case_is_ignored PASSED          [ 35%]
tests/test_nutrients.py::test_f_v12_invalid_amount[-1] PASSED            [ 36%]
tests/test_nutrients.py::test_f_v12_invalid_amount[3.2] PASSED           [ 36%]
tests/test_nutrients.py::test_f_v12_invalid_amount[True] PASSED          [ 37%]
tests/test_nutrients.py::test_f_v12_invalid_amount[nan] PASSED           [ 38%]
tests/test_nutrients.py::test_f_v12_invalid_amount[inf] PASSED           [ 39%]
tests/test_nutrients.py::test_v13_zero_is_returned_as_zero PASSED        [ 39%]
tests/test_nutrients.py::test_v14_no_rounding PASSED                     [ 40%]
tests/test_nutrients.py::test_v7_row_id_is_never_used PASSED             [ 41%]
tests/test_nutrients.py::test_v7_rows_without_nutrient_object_are_skipped PASSED [ 42%]
tests/test_nutrients.py::test_c_search_candidates_match_usda_order PASSED [ 42%]
tests/test_nutrients.py::test_c_candidates_carry_no_nutrient_fields PASSED [ 43%]
tests/test_nutrients.py::test_c_records_whether_171999_appears 
[recorded] 'king salmon cooked dry heat' candidates: [174236, 171999, 172000, 172001, 173692, 175168, 171998, 173716, 173719, 174229]; contains 171999: True
PASSED    [ 44%]
tests/test_nutrients.py::test_c_other_data_types_are_dropped_and_logged PASSED [ 45%]
tests/test_nutrients.py::test_c_zero_results_is_not_an_error PASSED      [ 45%]
tests/test_nutrients.py::test_c_malformed_search[text] PASSED            [ 46%]
tests/test_nutrients.py::test_c_malformed_search[None] PASSED            [ 47%]
tests/test_nutrients.py::test_c_malformed_search[body2] PASSED           [ 48%]
tests/test_nutrients.py::test_c_malformed_search[body3] PASSED           [ 48%]
tests/test_nutrients.py::test_c_malformed_search[body4] PASSED           [ 49%]
tests/test_service.py::test_a_chinook_through_service PASSED             [ 50%]
tests/test_service.py::test_b_pink_through_service PASSED                [ 51%]
tests/test_service.py::test_b_isolation_with_cache[order0] PASSED        [ 51%]
tests/test_service.py::test_b_isolation_with_cache[order1] PASSED        [ 52%]
tests/test_service.py::test_b_isolation_without_cache[order0] PASSED     [ 53%]
tests/test_service.py::test_b_isolation_without_cache[order1] PASSED     [ 54%]
tests/test_service.py::test_c_search_through_service PASSED              [ 54%]
tests/test_service.py::test_c_search_default_limit_is_five PASSED        [ 55%]
tests/test_service.py::test_c_chinook_search_fixture_parses PASSED       [ 56%]
tests/test_service.py::test_f_invalid_fdc_id[0] PASSED                   [ 57%]
tests/test_service.py::test_f_invalid_fdc_id[-1] PASSED                  [ 57%]
tests/test_service.py::test_f_invalid_fdc_id[True] PASSED                [ 58%]
tests/test_service.py::test_f_invalid_fdc_id[1.5] PASSED                 [ 59%]
tests/test_service.py::test_f_invalid_fdc_id[171999] PASSED              [ 60%]
tests/test_service.py::test_f_invalid_fdc_id[None] PASSED                [ 60%]
tests/test_service.py::test_f_invalid_search_input[-5] PASSED            [ 61%]
tests/test_service.py::test_f_invalid_search_input[   -5] PASSED         [ 62%]
tests/test_service.py::test_f_invalid_search_input[xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-5] PASSED [ 63%]
tests/test_service.py::test_f_invalid_search_input[None-5] PASSED        [ 63%]
tests/test_service.py::test_f_invalid_search_input[5-5] PASSED           [ 64%]
tests/test_service.py::test_f_invalid_search_input[salmon-0] PASSED      [ 65%]
tests/test_service.py::test_f_invalid_search_input[salmon-11] PASSED     [ 66%]
tests/test_service.py::test_f_invalid_search_input[salmon-True] PASSED   [ 66%]
tests/test_service.py::test_f_invalid_search_input[salmon-2.0] PASSED    [ 67%]
tests/test_service.py::test_f_invalid_search_input[salmon-5] PASSED      [ 68%]
tests/test_service.py::test_f_limit_is_rejected_not_capped PASSED        [ 69%]
tests/test_service.py::test_f_saved_404_not_found PASSED                 [ 69%]
tests/test_service.py::test_f_saved_403_auth_failed PASSED               [ 70%]
tests/test_service.py::test_f_429_rate_limited_one_request PASSED        [ 71%]
tests/test_service.py::test_f_503_three_times_unavailable PASSED         [ 72%]
tests/test_service.py::test_f_timeout_then_200 PASSED                    [ 72%]
tests/test_service.py::test_f_non_json_body_malformed PASSED             [ 73%]
tests/test_service.py::test_f_id_mismatch_returns_no_values PASSED       [ 74%]
tests/test_service.py::test_f_validation_failed_names_rule PASSED        [ 75%]
tests/test_service.py::test_search_usda_failure_carries_query PASSED     [ 75%]
tests/test_service.py::test_g_nutrition_shape_and_size PASSED            [ 76%]
tests/test_service.py::test_g_partial_shape PASSED                       [ 77%]
tests/test_service.py::test_g_search_shape_and_size PASSED               [ 78%]
tests/test_service.py::test_g_error_shape PASSED                         [ 78%]
tests/test_service.py::test_j_second_call_makes_no_request PASSED        [ 79%]
tests/test_service.py::test_j_search_is_cached_case_insensitively PASSED [ 80%]
tests/test_service.py::test_j_errors_are_not_cached PASSED               [ 81%]
tests/test_service.py::test_j_ttl_expiry_refetches PASSED                [ 81%]
tests/test_service.py::test_j_lru_eviction PASSED                        [ 82%]
tests/test_service.py::test_j_entry_with_wrong_fdc_id_is_dropped PASSED  [ 83%]
tests/test_service.py::test_k_log_lines_are_json_with_documented_fields PASSED [ 84%]
tests/test_service.py::test_k_failures_never_leak_key PASSED             [ 84%]
tests/test_service.py::test_p_twenty_threads_get_their_own_food PASSED   [ 85%]
tests/test_usda_client.py::test_h_detail_request_shape PASSED            [ 86%]
tests/test_usda_client.py::test_h_search_request_shape PASSED            [ 87%]
tests/test_usda_client.py::test_f_saved_404_is_not_found PASSED          [ 87%]
tests/test_usda_client.py::test_f_saved_403_is_auth_failed PASSED        [ 88%]
tests/test_usda_client.py::test_f_saved_400_is_unavailable PASSED        [ 89%]
tests/test_usda_client.py::test_f_429_rate_limited_after_exactly_one_request PASSED [ 90%]
tests/test_usda_client.py::test_f_503_three_times_is_unavailable_after_three_requests PASSED [ 90%]
tests/test_usda_client.py::test_f_other_5xx_retry_then_fail[500] PASSED  [ 91%]
tests/test_usda_client.py::test_f_other_5xx_retry_then_fail[502] PASSED  [ 92%]
tests/test_usda_client.py::test_f_other_5xx_retry_then_fail[504] PASSED  [ 93%]
tests/test_usda_client.py::test_f_timeout_then_200_succeeds_after_two_requests PASSED [ 93%]
tests/test_usda_client.py::test_f_connection_error_three_times PASSED    [ 94%]
tests/test_usda_client.py::test_f_non_json_body_is_malformed PASSED      [ 95%]
tests/test_usda_client.py::test_f_unexpected_status_is_unavailable[201] PASSED [ 96%]
tests/test_usda_client.py::test_f_unexpected_status_is_unavailable[301] PASSED [ 96%]
tests/test_usda_client.py::test_f_unexpected_status_is_unavailable[401] PASSED [ 97%]
tests/test_usda_client.py::test_f_unexpected_status_is_unavailable[418] PASSED [ 98%]
tests/test_usda_client.py::test_search_404_is_unavailable_not_not_found PASSED [ 99%]
tests/test_usda_client.py::test_k_error_messages_never_contain_usda_text_or_key PASSED [100%]

=========================== short test summary info ============================
SKIPPED [1] tests/test_live.py:25: set ROLI_LIVE_TESTS=1 to call USDA
SKIPPED [1] tests/test_live.py:33: set ROLI_LIVE_TESTS=1 to call USDA
SKIPPED [1] tests/test_live.py:40: set ROLI_LIVE_TESTS=1 to call USDA
SKIPPED [1] tests/test_live.py:46: set ROLI_LIVE_TESTS=1 to call USDA
======================== 129 passed, 4 skipped in 0.56s ========================
============================= test session starts ==============================
platform darwin -- Python 3.13.5, pytest-8.4.2, pluggy-1.7.0 -- /Users/juliuslitinskas/projects/roli/nutrition_service/.venv/bin/python
cachedir: .pytest_cache
rootdir: /Users/juliuslitinskas/projects/roli/nutrition_service
configfile: pytest.ini
plugins: anyio-4.16.0
collecting ... collected 4 items

tests/test_live.py::test_live_a_chinook PASSED                           [ 25%]
tests/test_live.py::test_live_b_pink PASSED                              [ 50%]
tests/test_live.py::test_live_search_king_salmon PASSED                  [ 75%]
tests/test_live.py::test_live_not_found PASSED                           [100%]

============================== 4 passed in 1.74s ===============================
```

Mapping from spec 13.3 to test functions:

| Spec | Where |
|---|---|
| A Chinook | `test_nutrients.py::test_a_chinook_complete`, `test_service.py::test_a_chinook_through_service` |
| B Pink + isolation | `test_b_*` in both files; cache and no-cache orderings both ways |
| C Search | `test_c_*` in both files; the 171999 observation is printed, not asserted (section 5 below) |
| D Missing | `test_d_*` incl. the real Foundation broccoli record |
| E ID mismatch | `test_e_id_mismatch`, `test_f_id_mismatch_returns_no_values` |
| F Failures | `test_f_*` across all three files (status codes, retries, V8 to V12, real Branded record) |
| G Shape and size | `test_g_*` |
| H Request shape | `test_h_*` in `test_usda_client.py` |
| I Unfiltered equivalence | `test_i_*` |
| J Cache | `test_j_*` |
| K Secrets | `test_k_*` plus an autouse check in `conftest.py` that fails any test whose log output contains the fake key |
| O Core isolation | `test_isolation.py` (fresh interpreter via subprocess) |
| P Threads | `test_p_twenty_threads_get_their_own_food` |
| Live | `test_live.py` |

## 4. `demo.py` output (exact JSON)

Live USDA calls, except the `id_mismatch` case, which the real API cannot produce (USDA always returns the ID asked for); that one feeds the saved 171999 reply with `fdcId` edited to 172001 through the mock transport, and says so in its note.

### get_nutrition(171999), cache miss
_542 ms, 300 bytes_
```json
{
  "status": "complete",
  "fdc_id": 171999,
  "description": "Fish, salmon, chinook, cooked, dry heat",
  "data_type": "SR Legacy",
  "basis": "per_100g",
  "saturated_fat_g": 3.214,
  "cholesterol_mg": 85.0,
  "missing_nutrients": [],
  "nutrient_ids": {
    "saturated_fat_g": 1258,
    "cholesterol_mg": 1253
  },
  "source": "USDA FoodData Central"
}
```

### get_nutrition(171999), cache hit
_0.18 ms_
```json
{
  "status": "complete",
  "fdc_id": 171999,
  "description": "Fish, salmon, chinook, cooked, dry heat",
  "data_type": "SR Legacy",
  "basis": "per_100g",
  "saturated_fat_g": 3.214,
  "cholesterol_mg": 85.0,
  "missing_nutrients": [],
  "nutrient_ids": {
    "saturated_fat_g": 1258,
    "cholesterol_mg": 1253
  },
  "source": "USDA FoodData Central"
}
```

### get_nutrition(172001)
_258 ms, 297 bytes_
```json
{
  "status": "complete",
  "fdc_id": 172001,
  "description": "Fish, salmon, pink, cooked, dry heat",
  "data_type": "SR Legacy",
  "basis": "per_100g",
  "saturated_fat_g": 0.971,
  "cholesterol_mg": 55.0,
  "missing_nutrients": [],
  "nutrient_ids": {
    "saturated_fat_g": 1258,
    "cholesterol_mg": 1253
  },
  "source": "USDA FoodData Central"
}
```

### search_foods('king salmon cooked dry heat', 10)
_539 ms, 1097 bytes_
```json
{
  "status": "complete",
  "query": "king salmon cooked dry heat",
  "candidates": [
    {
      "fdc_id": 174236,
      "description": "Fish, mackerel, king, cooked, dry heat",
      "data_type": "SR Legacy"
    },
    {
      "fdc_id": 171999,
      "description": "Fish, salmon, chinook, cooked, dry heat",
      "data_type": "SR Legacy"
    },
    {
      "fdc_id": 172000,
      "description": "Fish, salmon, chum, cooked, dry heat",
      "data_type": "SR Legacy"
    },
    {
      "fdc_id": 172001,
      "description": "Fish, salmon, pink, cooked, dry heat",
      "data_type": "SR Legacy"
    },
    {
      "fdc_id": 173692,
      "description": "Fish, salmon, sockeye, cooked, dry heat",
      "data_type": "SR Legacy"
    },
    {
      "fdc_id": 175168,
      "description": "Fish, salmon, Atlantic, farmed, cooked, dry heat",
      "data_type": "SR Legacy"
    },
    {
      "fdc_id": 171998,
      "description": "Fish, salmon, Atlantic, wild, cooked, dry heat",
      "data_type": "SR Legacy"
    },
    {
      "fdc_id": 173716,
      "description": "Fish, salmon, coho, farmed, cooked, dry heat",
      "data_type": "SR Legacy"
    },
    {
      "fdc_id": 173719,
      "description": "Fish, salmon, coho, wild, cooked, dry heat",
      "data_type": "SR Legacy"
    },
    {
      "fdc_id": 174229,
      "description": "Fish, bluefish, cooked, dry heat",
      "data_type": "SR Legacy"
    }
  ],
  "source": "USDA FoodData Central"
}
```

### get_nutrition(99999999) -> not_found
```json
{
  "status": "error",
  "fdc_id": 99999999,
  "error_code": "not_found",
  "message": "USDA has no food with this FDC ID."
}
```

### get_nutrition(0) -> invalid_input
```json
{
  "status": "error",
  "fdc_id": 0,
  "error_code": "invalid_input",
  "message": "fdc_id must be a whole number of 1 or more."
}
```

### get_nutrition(171999) -> id_mismatch
_saved food_171999.json with fdcId edited to 172001, served through the mock transport_
```json
{
  "status": "error",
  "fdc_id": 171999,
  "error_code": "id_mismatch",
  "message": "USDA returned FDC ID 172001 for a request for FDC ID 171999."
}
```

Log lines written by the same run (logger `roli_nutrition`, one JSON line per call; the `HTTP Request:` lines come from httpx's own logger, see deviation 7):

```text
HTTP Request: GET https://api.nal.usda.gov/fdc/v1/food/171999?format=full&nutrients=606,601 "HTTP/1.1 200 OK"
{"call": "get_nutrition", "fdc_id": 171999, "status": "complete", "error_code": null, "duration_ms": 541.5, "cache_hit": false, "usda_requests": 1}
{"call": "get_nutrition", "fdc_id": 171999, "status": "complete", "error_code": null, "duration_ms": 0.0, "cache_hit": true, "usda_requests": 0}
HTTP Request: GET https://api.nal.usda.gov/fdc/v1/food/172001?format=full&nutrients=606,601 "HTTP/1.1 200 OK"
{"call": "get_nutrition", "fdc_id": 172001, "status": "complete", "error_code": null, "duration_ms": 258.0, "cache_hit": false, "usda_requests": 1}
HTTP Request: POST https://api.nal.usda.gov/fdc/v1/foods/search "HTTP/1.1 200 OK"
{"call": "search_foods", "query": "king salmon cooked dry heat", "status": "complete", "error_code": null, "duration_ms": 538.4, "cache_hit": false, "usda_requests": 1}
HTTP Request: GET https://api.nal.usda.gov/fdc/v1/food/99999999?format=full&nutrients=606,601 "HTTP/1.1 404 Not Found"
{"call": "get_nutrition", "fdc_id": 99999999, "status": "error", "error_code": "not_found", "duration_ms": 213.3, "cache_hit": false, "usda_requests": 1}
{"call": "get_nutrition", "fdc_id": 0, "status": "error", "error_code": "invalid_input", "duration_ms": 0.1, "cache_hit": false, "usda_requests": 0}
HTTP Request: GET https://api.nal.usda.gov/fdc/v1/food/171999?format=full&nutrients=606,601 "HTTP/1.1 200 OK"
{"call": "get_nutrition", "fdc_id": 171999, "status": "error", "error_code": "id_mismatch", "duration_ms": 0.8, "cache_hit": false, "usda_requests": 1}

Timings: cache miss 542 ms, cache hit 0.18 ms
```

## 5. Observed candidate lists

**"king salmon cooked dry heat"**, pageSize 10, totalHits 2278. 171999 is present, in **second** place. USDA matched the word "king" to king mackerel first.

| # | FDC ID | Data type | Description |
|---:|---:|---|---|
| 1 | 174236 | SR Legacy | Fish, mackerel, king, cooked, dry heat |
| 2 | 171999 | SR Legacy | Fish, salmon, chinook, cooked, dry heat |
| 3 | 172000 | SR Legacy | Fish, salmon, chum, cooked, dry heat |
| 4 | 172001 | SR Legacy | Fish, salmon, pink, cooked, dry heat |
| 5 | 173692 | SR Legacy | Fish, salmon, sockeye, cooked, dry heat |
| 6 | 175168 | SR Legacy | Fish, salmon, Atlantic, farmed, cooked, dry heat |
| 7 | 171998 | SR Legacy | Fish, salmon, Atlantic, wild, cooked, dry heat |
| 8 | 173716 | SR Legacy | Fish, salmon, coho, farmed, cooked, dry heat |
| 9 | 173719 | SR Legacy | Fish, salmon, coho, wild, cooked, dry heat |
| 10 | 174229 | SR Legacy | Fish, bluefish, cooked, dry heat |

**"salmon chinook cooked dry heat"**, pageSize 10, totalHits 2255. 171999 is **first**.

| # | FDC ID | Data type | Description |
|---:|---:|---|---|
| 1 | 171999 | SR Legacy | Fish, salmon, chinook, cooked, dry heat |
| 2 | 172000 | SR Legacy | Fish, salmon, chum, cooked, dry heat |
| 3 | 172001 | SR Legacy | Fish, salmon, pink, cooked, dry heat |
| 4 | 173692 | SR Legacy | Fish, salmon, sockeye, cooked, dry heat |
| 5 | 175168 | SR Legacy | Fish, salmon, Atlantic, farmed, cooked, dry heat |
| 6 | 171998 | SR Legacy | Fish, salmon, Atlantic, wild, cooked, dry heat |
| 7 | 173716 | SR Legacy | Fish, salmon, coho, farmed, cooked, dry heat |
| 8 | 173719 | SR Legacy | Fish, salmon, coho, wild, cooked, dry heat |
| 9 | 173688 | SR Legacy | Fish, salmon, chinook, raw |
| 10 | 173687 | SR Legacy | Fish, salmon, chinook, smoked |

This supports the wording already in the Phase 1B tool description (spec 7.3): USDA matches words, not meaning, and the first result is not necessarily right. No Foundation food appeared in either top 10.

## 6. Fixture manifest

Captured 2026-11-01T17:04:30+00:00. "Raw body" is what USDA sent; "Saved file" is the pretty-printed JSON on disk (indent 2), which is what the manifest's `bytes` and `sha256` describe.

| File | Status | Raw body (bytes) | Saved file (bytes) | Request |
|---|---:|---:|---:|---|
| `food_171999.json` | 200 | 1,342 | 1,869 | `GET /food/171999?format=full&nutrients=606,601` |
| `food_172001.json` | 200 | 1,783 | 2,510 | `GET /food/172001?format=full&nutrients=606,601` |
| `food_171999_unfiltered.json` | 200 | 14,329 | 22,896 | `GET /food/171999?format=full` |
| `food_172001_unfiltered.json` | 200 | 44,049 | 67,384 | `GET /food/172001?format=full` |
| `search_king_salmon.json` | 200 | 226,292 | 353,930 | `POST /foods/search {"query":"king salmon cooked dry heat","dataType":["Foundation","SR Legacy"],"pageSize":10}` |
| `search_salmon_chinook.json` | 200 | 246,926 | 383,986 | `POST /foods/search {"query":"salmon chinook cooked dry heat","dataType":["Foundation","SR Legacy"],"pageSize":10}` |
| `search_foundation_salmon.json` | 200 | 33,137 | 51,778 | `POST /foods/search {"query":"salmon","dataType":["Foundation"],"pageSize":5}` |
| `food_foundation_2684441.json` | 200 | 12,038 | 18,026 | `GET /food/2684441?format=full&nutrients=606,601` |
| `search_foundation_broccoli_raw.json` | 200 | 82,936 | 129,617 | `POST /foods/search {"query":"broccoli raw","dataType":["Foundation"],"pageSize":5}` |
| `food_foundation_747447.json` | 200 | 5,964 | 8,518 | `GET /food/747447?format=full&nutrients=606,601` |
| `search_branded_salmon.json` | 200 | 7,530 | 10,719 | `POST /foods/search {"query":"salmon","dataType":["Branded"],"pageSize":1}` |
| `food_branded_2016166.json` | 200 | 8,815 | 10,900 | `GET /food/2016166?format=full&nutrients=606,601` |
| `error_404.json` | 404 | 0 | 33 | `GET /food/99999999` |
| `error_400.json` | 400 | 70 | 116 | `GET /food/abc` |
| `error_403.json` | 403 | 133 | 174 | `GET /food/171999?format=full&nutrients=606,601 (no key)` |

Values typed into `tests/captured_expectations.py` after reading the files once:

| Fixture | FDC ID | Data type | Description | Saturated fat | Cholesterol | Status |
|---|---:|---|---|---:|---:|---|
| `food_foundation_2684441` | 2684441 | Foundation | Fish, salmon, Atlantic, farm raised, raw | 2.277 g | 62.11 mg | complete |
| `food_foundation_747447` | 747447 | Foundation | Broccoli, raw | 0.039 g | no row | partial |
| `food_branded_2016166` | 2016166 | Branded | SALMON | (has rows: 1.32 g, 46 mg) | | refused: `unsupported_data_type` |

## 7. Measured sizes and timings

Mac, home network, 2026-11-01. Two separate processes; USDA was warm from the capture run.

| Measurement | Run 1 (demo) | Run 2 (timing sample) | Target (spec 11) |
|---|---:|---:|---|
| `get_nutrition(171999)` cache miss | 530 ms | 509 ms | usually under 3 s |
| `get_nutrition(171999)` cache hit | 0.11 ms | 0.049 ms | under 50 ms |
| `get_nutrition(172001)` cache miss | 256 ms | 200 ms | |
| `get_nutrition(172001)` cache hit | | 0.059 ms | |
| search, 10 candidates, cache miss | 548 ms | 519 ms | |
| `get_nutrition` result as JSON | 300 bytes (171999), 297 bytes (172001) | | under 2 KB |
| search result, 10 candidates, as JSON | 1,097 bytes | | test G bound 3 KB |

The filtered detail request cuts USDA's reply from 14,329 to 1,342 bytes for 171999 and from 44,049 to 1,783 bytes for 172001. The search endpoint ignores the nutrient filter and sends every food's full nutrient list: 226 KB for 10 results. The library reads three fields per food from it and throws the rest away; the result is 1.1 KB.

## 8. Deviations from the spec

1. **`UsdaClient.get_food()` and `search()` return `UsdaReply(body, requests)`**, not a bare `dict`. The spec wants the number of USDA requests per call logged. A counter on the client would be wrong when 20 threads share it (test P), so the count travels with the reply, and with the `UsdaError` on failure.
2. **`ErrorResult` keeps both `fdc_id` and `query` as fields** and remembers privately which tool produced it; serialization drops the unused key. This keeps one `ErrorResult` class (spec 6) while every error has exactly the documented keys (test G). Built through `ErrorResult.for_food(...)` and `ErrorResult.for_search(...)`.
3. **httpx timeouts:** the spec names connect 5 s and read 10 s. httpx also needs write and pool timeouts; set to 10 s and 5 s.
4. **`errors.py` added** (one exception class). Not in the spec's layout; it avoids `nutrients.py` importing from `usda_client.py` or the reverse.
5. **`tests/captured_expectations.py` added** to hold the hand-typed expected values (spec 13.1 last paragraph) in one place with the file names and the date they were read.
6. **`ROLI_FIXTURES_DIR` override in `tests/conftest.py`.** Used once, before the key existed, to dry-run the suite on throwaway synthetic replies in a folder outside the repo. Real runs ignore it. No synthetic file was ever written inside the repo. Can be removed if you prefer.
7. **httpx logs its own `HTTP Request: GET <url> "HTTP/1.1 200 OK"` line at INFO level** (logger `httpx`), visible in section 4. It never includes headers or the key. Spec 11 covers our logger, `roli_nutrition`, which stays as specified. Silencing httpx's logger is a one-line option if wanted.
8. **`demo.py` `id_mismatch` case is not live** (see section 4). The real API cannot return a different ID than requested.
9. **Manifest `bytes`/`sha256` describe the saved pretty-printed file**, not the raw body. Raw sizes are in section 6.
10. **Non-string `dataType` is `malformed_response`, not `unsupported_data_type`.** Spec 9 lists a wrong-typed `dataType` under `malformed_response`; V4's text does not mention the non-string case. The stricter reading was taken.
11. **`requirements.txt` with exact pins is not yet generated.** Spec 3 says "after the tests pass", spec 14 lists it under Phase 1C. Generating it now would pin only the core; the Docker image also needs the `[mcp]` extra from 1B. Deferred to 1C.
12. **Python 3.11 compatibility is by construction, not by test.** The code avoids 3.12-only syntax, but only Python 3.13.5 is on this Mac.

## 9. Open questions

1. **The search tool returns the trimmed query as given, with no truncation of the candidate list** beyond what USDA returns for `pageSize`. If USDA ever returned more than `limit`, all would be passed through. Should the service cut to `limit` as a belt-and-braces rule? Not in the spec; not done.
2. **Fixture size.** The two main search fixtures are 354 KB and 384 KB on disk because USDA sends full nutrient lists per food. They are real, unedited replies, as the spec requires. Total fixtures: 1.06 MB. Acceptable for the repo, or should the search fixtures be captured with a smaller `pageSize` for everyday tests and the 10-result ones kept only for test G?
3. **The Foundation "salmon" record is raw, farm-raised Atlantic salmon** (the only Foundation salmon USDA has). It does not change anything here, but it means Foundation data will rarely cover cooked restaurant preparations; SR Legacy will carry most lookups.
4. **httpx request log line** (deviation 7): keep or silence?
5. **`ROLI_FIXTURES_DIR`** (deviation 6): keep or remove?

## 10. Not done, by design

- No MCP wrapper, no `mcp_server.py`, no tests L to N (Phase 1B).
- No Dockerfile, README or pinned `requirements.txt` (Phase 1C).
- No change to `code/`, `menu_reader_eval/`, `menu_test_set/`, `results/`, the root `.venv` or `requirements.txt`, the LangGraph implementation or the Agent Builder agent.
- The key was never printed, logged or written anywhere; `.env` was read only by `python-dotenv` inside the scripts and the live tests.

**Stopped here. Phase 1B starts only after your approval.**
