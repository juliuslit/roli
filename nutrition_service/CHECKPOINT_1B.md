# Checkpoint 1B: MCP wrapper

Date: 2026-11-01. Spec: `SPEC.md` v2.1, section 14, Phase 1B, plus Julius's additional Phase 1B requirements (token, latency and size, Inspector). Status: **Phase 1B complete; stopped. Phase 1C not started, nothing deployed, neither Roli implementation touched.**

## 1. Summary

| Item | Result |
|---|---|
| Pre-1B changes (limit enforcement, httpx log off in scripts, fixture override removed) | done; Phase 1A suite re-run green before any MCP work |
| Full suite, offline (`pytest -v`, 1A + 1B) | **156 passed, 4 skipped** (live tests), 0 failed |
| Live tests (`ROLI_LIVE_TESTS=1`) | **4 passed** |
| MCP tests L, M, N | 25 tests, all passing |
| Tool discovery (Inspector CLI) | exactly 2 tools, spec names and descriptions, schemas as expected |
| Tool execution (Inspector CLI, live USDA) | both tools return the service's JSON unchanged |
| Authentication | missing, wrong, malformed and non-Bearer headers all 401 before any tool or USDA call; verified by tests, curl and the server log |
| MCP latency over direct Python, warmed cache, local | median +1.3 ms in-process, +2.0 ms over HTTP on 127.0.0.1 |
| Nutrition payload | 300 bytes compact JSON (limit 2 KB); full HTTP body 814 bytes |
| `ROLI_MCP_TOKEN` | 64 characters from `secrets.token_urlsafe(48)`, appended to `roli/.env` (git-ignored), never printed or written elsewhere |
| USDA calls made in this phase | 4 (live tests) + 2 (Inspector calls) + 1 (curl) = 7; tests and benchmark use saved replies |

## 2. What was built, in plain language

`roli_nutrition/mcp_server.py` is the only new library file. It does three things and nothing else:

1. **Two tools.** Each tool calls the existing service in a worker thread and hands back `result.model_dump()`, the same dict a LangGraph node gets from the direct Python call. The MCP SDK then puts that dict into the reply twice: as `structuredContent` (machine-readable) and as a pretty-printed text block (for clients that only read text). Test M checks both views equal the direct call.
2. **A door check.** A small piece of ASGI middleware sits in front of the SDK's endpoint. Every HTTP request must carry `Authorization: Bearer <ROLI_MCP_TOKEN>`. Anything else gets a 401 before routing happens, so no tool code and no USDA request can run. The comparison uses `hmac.compare_digest`, which takes the same time whether the first or the last character is wrong.
3. **A `main()`** that loads `roli/.env`, refuses to start if the token is missing or shorter than 32 characters, and serves `/mcp` with uvicorn (`HOST`, `PORT`, defaults 127.0.0.1:8000).

The core package did not change for MCP. `mcp_server.py` is never imported by `roli_nutrition/__init__.py`, and test O (fresh interpreter) still proves that importing the core loads none of `mcp`, `uvicorn`, `dotenv`, `langgraph` or `langchain`.

Run it locally:

```text
nutrition_service/.venv/bin/python -m roli_nutrition.mcp_server        # serves http://127.0.0.1:8000/mcp
PORT=8765 nutrition_service/.venv/bin/python -m roli_nutrition.mcp_server
```

## 3. Pre-1B changes requested at Checkpoint 1A

| Request | Done |
|---|---|
| 1. Enforce `limit` on returned candidates, add a test | `parse_search(query, body, limit)` cuts the list after unsupported types are dropped; `test_limit_caps_candidates_even_if_usda_returns_more` (service) and `test_c_parse_search_limit_applies_after_dropping_unsupported_types` (pure function) |
| 2. Keep the real fixtures unchanged | unchanged; SHA-256 values in `manifest.json` still match |
| 4. httpx INFO logging off in scripts and MCP server, not in the library | `logging.getLogger("httpx").setLevel(WARNING)` in `demo.py`, `capture_fixtures.py`, `mcp_server.main()`; nothing in `roli_nutrition/` touches logger levels |
| 5. Remove `ROLI_FIXTURES_DIR` | removed from `tests/conftest.py` |

## 4. Test results

Offline: 156 passed, 4 skipped (the live tests). Live: 4 passed. Exactly as saved in `test_report_1B.txt`:

```text
============================= test session starts ==============================
platform darwin -- Python 3.13.5, pytest-8.4.2, pluggy-1.7.0 -- .venv/bin/python
cachedir: .pytest_cache
rootdir: /Users/juliuslitinskas/projects/roli/nutrition_service
configfile: pytest.ini
plugins: anyio-4.16.0
collecting ... collected 160 items

tests/test_isolation.py::test_o_core_imports_no_forbidden_modules PASSED [  0%]
tests/test_live.py::test_live_a_chinook SKIPPED (set ROLI_LIVE_TESTS...) [  1%]
tests/test_live.py::test_live_b_pink SKIPPED (set ROLI_LIVE_TESTS=1 ...) [  1%]
tests/test_live.py::test_live_search_king_salmon SKIPPED (set ROLI_L...) [  2%]
tests/test_live.py::test_live_not_found SKIPPED (set ROLI_LIVE_TESTS...) [  3%]
tests/test_mcp_server.py::test_l_exactly_two_tools_with_spec_names_and_descriptions PASSED [  3%]
tests/test_mcp_server.py::test_l_input_schemas PASSED                    [  4%]
tests/test_mcp_server.py::test_m_nutrition_tool_equals_service_output PASSED [  5%]
tests/test_mcp_server.py::test_m_search_tool_equals_service_output PASSED [  5%]
tests/test_mcp_server.py::test_m_search_default_limit_through_mcp PASSED [  6%]
tests/test_mcp_server.py::test_m_service_error_is_a_normal_tool_result PASSED [  6%]
tests/test_mcp_server.py::test_m_value_rules_come_back_in_our_error_shape PASSED [  7%]
tests/test_mcp_server.py::test_m_json_type_errors_are_rejected_by_the_mcp_layer[True] PASSED [  8%]
tests/test_mcp_server.py::test_m_json_type_errors_are_rejected_by_the_mcp_layer[171999] PASSED [  8%]
tests/test_mcp_server.py::test_m_json_type_errors_are_rejected_by_the_mcp_layer[2.0] PASSED [  9%]
tests/test_mcp_server.py::test_m_json_type_errors_are_rejected_by_the_mcp_layer[None] PASSED [ 10%]
tests/test_mcp_server.py::test_m_calls_run_in_a_worker_thread_and_do_not_block_the_loop PASSED [ 10%]
tests/test_mcp_server.py::test_n_unauthorised_requests_get_401_before_any_tool_runs[None] PASSED [ 11%]
tests/test_mcp_server.py::test_n_unauthorised_requests_get_401_before_any_tool_runs[Bearer wrong-token-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx] PASSED [ 11%]
tests/test_mcp_server.py::test_n_unauthorised_requests_get_401_before_any_tool_runs[Token test-only-token-0123456789abcdef0123456789abcdef0123456789abcdef] PASSED [ 12%]
tests/test_mcp_server.py::test_n_unauthorised_requests_get_401_before_any_tool_runs[Bearer] PASSED [ 13%]
tests/test_mcp_server.py::test_n_unauthorised_requests_get_401_before_any_tool_runs[Bearer test-only-token-0123456789abcdef0123456789abcdef0123456789abcdef extra] PASSED [ 13%]
tests/test_mcp_server.py::test_n_unauthorised_requests_get_401_before_any_tool_runs[Bearertest-only-token-0123456789abcdef0123456789abcdef0123456789abcdef] PASSED [ 14%]
tests/test_mcp_server.py::test_n_unauthorised_requests_get_401_before_any_tool_runs[test-only-token-0123456789abcdef0123456789abcdef0123456789abcdef] PASSED [ 15%]
tests/test_mcp_server.py::test_n_unauthorised_requests_get_401_before_any_tool_runs[] PASSED [ 15%]
tests/test_mcp_server.py::test_n_right_token_works_and_scheme_is_case_insensitive PASSED [ 16%]
tests/test_mcp_server.py::test_n_other_methods_and_paths_are_also_protected PASSED [ 16%]
tests/test_mcp_server.py::test_n_wrong_token_through_official_client_fails_and_never_reaches_usda PASSED [ 17%]
tests/test_mcp_server.py::test_n_server_refuses_to_start_without_a_usable_token PASSED [ 18%]
tests/test_mcp_server.py::test_n_token_never_appears_in_logs PASSED      [ 18%]
tests/test_nutrients.py::test_a_chinook_complete PASSED                  [ 19%]
tests/test_nutrients.py::test_b_pink_complete PASSED                     [ 20%]
tests/test_nutrients.py::test_b_chinook_never_carries_pink_values PASSED [ 20%]
tests/test_nutrients.py::test_i_unfiltered_equivalence[171999-food_171999-food_171999_unfiltered] PASSED [ 21%]
tests/test_nutrients.py::test_i_unfiltered_equivalence[172001-food_172001-food_172001_unfiltered] PASSED [ 21%]
tests/test_nutrients.py::test_i_unfiltered_has_heading_rows_without_amount PASSED [ 22%]
tests/test_nutrients.py::test_d_cholesterol_row_removed PASSED           [ 23%]
tests/test_nutrients.py::test_d_row_present_without_amount PASSED        [ 23%]
tests/test_nutrients.py::test_d_amount_null PASSED                       [ 24%]
tests/test_nutrients.py::test_d_empty_food_nutrients PASSED              [ 25%]
tests/test_nutrients.py::test_d_missing_never_becomes_zero PASSED        [ 25%]
tests/test_nutrients.py::test_d_real_foundation_plant_food PASSED        [ 26%]
tests/test_nutrients.py::test_real_foundation_animal_food PASSED         [ 26%]
tests/test_nutrients.py::test_e_id_mismatch PASSED                       [ 27%]
tests/test_nutrients.py::test_f_body_not_object[not an object] PASSED    [ 28%]
tests/test_nutrients.py::test_f_body_not_object[42] PASSED               [ 28%]
tests/test_nutrients.py::test_f_body_not_object[None] PASSED             [ 29%]
tests/test_nutrients.py::test_f_body_not_object[body3] PASSED            [ 30%]
tests/test_nutrients.py::test_f_fdcid_wrong_type[None] PASSED            [ 30%]
tests/test_nutrients.py::test_f_fdcid_wrong_type[171999] PASSED          [ 31%]
tests/test_nutrients.py::test_f_fdcid_wrong_type[171999.0] PASSED        [ 31%]
tests/test_nutrients.py::test_f_fdcid_wrong_type[True] PASSED            [ 32%]
tests/test_nutrients.py::test_f_fdcid_missing PASSED                     [ 33%]
tests/test_nutrients.py::test_f_required_field_missing[description] PASSED [ 33%]
tests/test_nutrients.py::test_f_required_field_missing[dataType] PASSED  [ 34%]
tests/test_nutrients.py::test_f_required_field_missing[foodNutrients] PASSED [ 35%]
tests/test_nutrients.py::test_f_description_wrong[] PASSED               [ 35%]
tests/test_nutrients.py::test_f_description_wrong[None] PASSED           [ 36%]
tests/test_nutrients.py::test_f_description_wrong[5] PASSED              [ 36%]
tests/test_nutrients.py::test_f_unsupported_data_type[Branded] PASSED    [ 37%]
tests/test_nutrients.py::test_f_unsupported_data_type[Survey (FNDDS)] PASSED [ 38%]
tests/test_nutrients.py::test_f_unsupported_data_type[Experimental] PASSED [ 38%]
tests/test_nutrients.py::test_f_unsupported_data_type[sr legacy] PASSED  [ 39%]
tests/test_nutrients.py::test_f_real_branded_detail PASSED               [ 40%]
tests/test_nutrients.py::test_f_v8_id_number_mismatch_on_selected_row PASSED [ 40%]
tests/test_nutrients.py::test_f_v8_number_claims_target_but_id_differs PASSED [ 41%]
tests/test_nutrients.py::test_f_v9_duplicate_row_same_amount PASSED      [ 41%]
tests/test_nutrients.py::test_f_v10_unit_mismatch_on_saturated_fat[mg] PASSED [ 42%]
tests/test_nutrients.py::test_f_v10_unit_mismatch_on_saturated_fat[MG] PASSED [ 43%]
tests/test_nutrients.py::test_f_v10_unit_mismatch_on_saturated_fat[kcal] PASSED [ 43%]
tests/test_nutrients.py::test_f_v10_unit_mismatch_on_saturated_fat[None] PASSED [ 44%]
tests/test_nutrients.py::test_f_v10_unit_case_is_ignored PASSED          [ 45%]
tests/test_nutrients.py::test_f_v12_invalid_amount[-1] PASSED            [ 45%]
tests/test_nutrients.py::test_f_v12_invalid_amount[3.2] PASSED           [ 46%]
tests/test_nutrients.py::test_f_v12_invalid_amount[True] PASSED          [ 46%]
tests/test_nutrients.py::test_f_v12_invalid_amount[nan] PASSED           [ 47%]
tests/test_nutrients.py::test_f_v12_invalid_amount[inf] PASSED           [ 48%]
tests/test_nutrients.py::test_v13_zero_is_returned_as_zero PASSED        [ 48%]
tests/test_nutrients.py::test_v14_no_rounding PASSED                     [ 49%]
tests/test_nutrients.py::test_v7_row_id_is_never_used PASSED             [ 50%]
tests/test_nutrients.py::test_v7_rows_without_nutrient_object_are_skipped PASSED [ 50%]
tests/test_nutrients.py::test_c_search_candidates_match_usda_order PASSED [ 51%]
tests/test_nutrients.py::test_c_candidates_carry_no_nutrient_fields PASSED [ 51%]
tests/test_nutrients.py::test_c_records_whether_171999_appears 
[recorded] 'king salmon cooked dry heat' candidates: [174236, 171999, 172000, 172001, 173692, 175168, 171998, 173716, 173719, 174229]; contains 171999: True
PASSED    [ 52%]
tests/test_nutrients.py::test_c_other_data_types_are_dropped_and_logged PASSED [ 53%]
tests/test_nutrients.py::test_c_zero_results_is_not_an_error PASSED      [ 53%]
tests/test_nutrients.py::test_c_malformed_search[text] PASSED            [ 54%]
tests/test_nutrients.py::test_c_malformed_search[None] PASSED            [ 55%]
tests/test_nutrients.py::test_c_malformed_search[body2] PASSED           [ 55%]
tests/test_nutrients.py::test_c_malformed_search[body3] PASSED           [ 56%]
tests/test_nutrients.py::test_c_malformed_search[body4] PASSED           [ 56%]
tests/test_nutrients.py::test_c_parse_search_limit_applies_after_dropping_unsupported_types PASSED [ 57%]
tests/test_service.py::test_a_chinook_through_service PASSED             [ 58%]
tests/test_service.py::test_b_pink_through_service PASSED                [ 58%]
tests/test_service.py::test_b_isolation_with_cache[order0] PASSED        [ 59%]
tests/test_service.py::test_b_isolation_with_cache[order1] PASSED        [ 60%]
tests/test_service.py::test_b_isolation_without_cache[order0] PASSED     [ 60%]
tests/test_service.py::test_b_isolation_without_cache[order1] PASSED     [ 61%]
tests/test_service.py::test_c_search_through_service PASSED              [ 61%]
tests/test_service.py::test_c_search_default_limit_is_five PASSED        [ 62%]
tests/test_service.py::test_c_chinook_search_fixture_parses PASSED       [ 63%]
tests/test_service.py::test_f_invalid_fdc_id[0] PASSED                   [ 63%]
tests/test_service.py::test_f_invalid_fdc_id[-1] PASSED                  [ 64%]
tests/test_service.py::test_f_invalid_fdc_id[True] PASSED                [ 65%]
tests/test_service.py::test_f_invalid_fdc_id[1.5] PASSED                 [ 65%]
tests/test_service.py::test_f_invalid_fdc_id[171999] PASSED              [ 66%]
tests/test_service.py::test_f_invalid_fdc_id[None] PASSED                [ 66%]
tests/test_service.py::test_f_invalid_search_input[-5] PASSED            [ 67%]
tests/test_service.py::test_f_invalid_search_input[   -5] PASSED         [ 68%]
tests/test_service.py::test_f_invalid_search_input[xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-5] PASSED [ 68%]
tests/test_service.py::test_f_invalid_search_input[None-5] PASSED        [ 69%]
tests/test_service.py::test_f_invalid_search_input[5-5] PASSED           [ 70%]
tests/test_service.py::test_f_invalid_search_input[salmon-0] PASSED      [ 70%]
tests/test_service.py::test_f_invalid_search_input[salmon-11] PASSED     [ 71%]
tests/test_service.py::test_f_invalid_search_input[salmon-True] PASSED   [ 71%]
tests/test_service.py::test_f_invalid_search_input[salmon-2.0] PASSED    [ 72%]
tests/test_service.py::test_f_invalid_search_input[salmon-5] PASSED      [ 73%]
tests/test_service.py::test_f_limit_is_rejected_not_capped PASSED        [ 73%]
tests/test_service.py::test_f_saved_404_not_found PASSED                 [ 74%]
tests/test_service.py::test_f_saved_403_auth_failed PASSED               [ 75%]
tests/test_service.py::test_f_429_rate_limited_one_request PASSED        [ 75%]
tests/test_service.py::test_f_503_three_times_unavailable PASSED         [ 76%]
tests/test_service.py::test_f_timeout_then_200 PASSED                    [ 76%]
tests/test_service.py::test_f_non_json_body_malformed PASSED             [ 77%]
tests/test_service.py::test_f_id_mismatch_returns_no_values PASSED       [ 78%]
tests/test_service.py::test_f_validation_failed_names_rule PASSED        [ 78%]
tests/test_service.py::test_search_usda_failure_carries_query PASSED     [ 79%]
tests/test_service.py::test_g_nutrition_shape_and_size PASSED            [ 80%]
tests/test_service.py::test_g_partial_shape PASSED                       [ 80%]
tests/test_service.py::test_g_search_shape_and_size PASSED               [ 81%]
tests/test_service.py::test_g_error_shape PASSED                         [ 81%]
tests/test_service.py::test_j_second_call_makes_no_request PASSED        [ 82%]
tests/test_service.py::test_j_search_is_cached_case_insensitively PASSED [ 83%]
tests/test_service.py::test_j_errors_are_not_cached PASSED               [ 83%]
tests/test_service.py::test_j_ttl_expiry_refetches PASSED                [ 84%]
tests/test_service.py::test_j_lru_eviction PASSED                        [ 85%]
tests/test_service.py::test_j_entry_with_wrong_fdc_id_is_dropped PASSED  [ 85%]
tests/test_service.py::test_k_log_lines_are_json_with_documented_fields PASSED [ 86%]
tests/test_service.py::test_k_failures_never_leak_key PASSED             [ 86%]
tests/test_service.py::test_p_twenty_threads_get_their_own_food PASSED   [ 87%]
tests/test_service.py::test_limit_caps_candidates_even_if_usda_returns_more PASSED [ 88%]
tests/test_usda_client.py::test_h_detail_request_shape PASSED            [ 88%]
tests/test_usda_client.py::test_h_search_request_shape PASSED            [ 89%]
tests/test_usda_client.py::test_f_saved_404_is_not_found PASSED          [ 90%]
tests/test_usda_client.py::test_f_saved_403_is_auth_failed PASSED        [ 90%]
tests/test_usda_client.py::test_f_saved_400_is_unavailable PASSED        [ 91%]
tests/test_usda_client.py::test_f_429_rate_limited_after_exactly_one_request PASSED [ 91%]
tests/test_usda_client.py::test_f_503_three_times_is_unavailable_after_three_requests PASSED [ 92%]
tests/test_usda_client.py::test_f_other_5xx_retry_then_fail[500] PASSED  [ 93%]
tests/test_usda_client.py::test_f_other_5xx_retry_then_fail[502] PASSED  [ 93%]
tests/test_usda_client.py::test_f_other_5xx_retry_then_fail[504] PASSED  [ 94%]
tests/test_usda_client.py::test_f_timeout_then_200_succeeds_after_two_requests PASSED [ 95%]
tests/test_usda_client.py::test_f_connection_error_three_times PASSED    [ 95%]
tests/test_usda_client.py::test_f_non_json_body_is_malformed PASSED      [ 96%]
tests/test_usda_client.py::test_f_unexpected_status_is_unavailable[201] PASSED [ 96%]
tests/test_usda_client.py::test_f_unexpected_status_is_unavailable[301] PASSED [ 97%]
tests/test_usda_client.py::test_f_unexpected_status_is_unavailable[401] PASSED [ 98%]
tests/test_usda_client.py::test_f_unexpected_status_is_unavailable[418] PASSED [ 98%]
tests/test_usda_client.py::test_search_404_is_unavailable_not_not_found PASSED [ 99%]
tests/test_usda_client.py::test_k_error_messages_never_contain_usda_text_or_key PASSED [100%]

=========================== short test summary info ============================
SKIPPED [1] tests/test_live.py:25: set ROLI_LIVE_TESTS=1 to call USDA
SKIPPED [1] tests/test_live.py:33: set ROLI_LIVE_TESTS=1 to call USDA
SKIPPED [1] tests/test_live.py:40: set ROLI_LIVE_TESTS=1 to call USDA
SKIPPED [1] tests/test_live.py:46: set ROLI_LIVE_TESTS=1 to call USDA
======================== 156 passed, 4 skipped in 1.53s ========================
============================= test session starts ==============================
platform darwin -- Python 3.13.5, pytest-8.4.2, pluggy-1.7.0 -- .venv/bin/python
cachedir: .pytest_cache
rootdir: /Users/juliuslitinskas/projects/roli/nutrition_service
configfile: pytest.ini
plugins: anyio-4.16.0
collecting ... collected 4 items

tests/test_live.py::test_live_a_chinook PASSED                           [ 25%]
tests/test_live.py::test_live_b_pink PASSED                              [ 50%]
tests/test_live.py::test_live_search_king_salmon PASSED                  [ 75%]
tests/test_live.py::test_live_not_found PASSED                           [100%]

============================== 4 passed in 1.48s ===============================
```

Where the Phase 1B tests live (`tests/test_mcp_server.py`, skipped automatically if the `[mcp]` extra is absent):

| Spec | Tests |
|---|---|
| L Discovery | `test_l_exactly_two_tools_with_spec_names_and_descriptions`, `test_l_input_schemas` |
| M Calls | `test_m_nutrition_tool_equals_service_output`, `test_m_search_tool_equals_service_output`, `test_m_search_default_limit_through_mcp`, `test_m_service_error_is_a_normal_tool_result`, `test_m_value_rules_come_back_in_our_error_shape`, `test_m_json_type_errors_are_rejected_by_the_mcp_layer` (4 cases), `test_m_calls_run_in_a_worker_thread_and_do_not_block_the_loop` |
| N Auth | `test_n_unauthorised_requests_get_401_before_any_tool_runs` (8 header variants), `test_n_right_token_works_and_scheme_is_case_insensitive`, `test_n_other_methods_and_paths_are_also_protected`, `test_n_wrong_token_through_official_client_fails_and_never_reaches_usda`, `test_n_server_refuses_to_start_without_a_usable_token`, `test_n_token_never_appears_in_logs` |

How the tests run without a network: the official MCP client (`ClientSession` over `streamable_http_client`) talks to the ASGI app through an in-process transport, and USDA is the same recording mock transport as in Phase 1A. The tests use a separate 64-character test token; the real token is never read by any test.

## 5. Authentication results

Against the live server on 127.0.0.1:8765 with `curl`, request body a `tools/call` for 171999:

| Authorization header | HTTP status | Tool ran? | USDA called? |
|---|---:|---|---|
| none | 401 | no | no |
| `Bearer <wrong token>` | 401 | no | no |
| `Basic abc` | 401 | no | no |
| `GET /mcp`, no header | 401 | no | no |
| `GET /health`, no header | 401 | no | no |
| `Bearer <ROLI_MCP_TOKEN>` | 200, 814 bytes, 1.8 ms (warm cache) | yes | no (cached) |

401 body: `{"error": "unauthorized", "message": "Missing or invalid bearer token."}` with `WWW-Authenticate: Bearer`. The test suite adds: `Bearer` alone, `Bearer <token> extra`, `Bearer<token>` (no space), the bare token, an empty header, and two `Authorization` headers; all 401 with zero USDA requests. The server log records each rejection as `{"event": "auth_rejected", "reason": "missing|malformed|wrong", "path": ...}` and never the header value; a search of the log for the token value found 0 occurrences.

Start-up refusal: `read_mcp_token` raises `ConfigError` for a missing, blank or shorter-than-32-character token, and `create_app_from_env` raises before any server object exists (`test_n_server_refuses_to_start_without_a_usable_token`).

The Inspector CLI with a wrong token stopped with `auth_required` (it read the 401 as "this server wants OAuth"), which is the correct outcome from its side; the 401 itself is covered above.

## 6. Latency and response size (`scripts/benchmark_mcp.py --calls 50`)

Fully local: USDA replaced by the saved real reply for 171999 through a mock transport, so network variance is out. Cache warmed with one call before timing. Mac, 2026-11-01.

| Path | Mean | Median | p95 | Extra vs direct (median) |
|---|---:|---:|---:|---:|
| direct Python `service.get_nutrition(171999)` | 0.007 ms | 0.007 ms | 0.008 ms | +0.000 ms |
| MCP in-process (official client, no sockets) | 1.385 ms | 1.341 ms | 1.569 ms | +1.335 ms |
| MCP over HTTP to uvicorn on 127.0.0.1 | 2.058 ms | 2.033 ms | 2.156 ms | +2.026 ms |

So the MCP layer costs about 2 ms per call on this machine. A cache miss costs 200 to 650 ms at USDA, so MCP adds under 1% to a cold call and dominates only a cached one, where 2 ms is still far below anything a user notices.

| Tool | App payload (compact JSON) | Text block (pretty JSON) | Full HTTP body | Protocol overhead |
|---|---:|---:|---:|---:|
| `roli_get_usda_nutrition` | 300 B | 356 B | 814 B | 514 B |
| `roli_search_usda_foods`, 10 candidates | 1,097 B | 1,457 B | 2,834 B | 1,737 B |

"App payload" is what the service returns, serialised compactly; that is the figure the 2 KB limit applies to, and it is 300 bytes. "Full HTTP body" is the JSON-RPC envelope containing the payload twice (text block and `structuredContent`); the difference is protocol overhead. The benchmark also asserts, for both tools, that `structuredContent` equals the direct call's dict.

## 7. MCP Inspector verification (CLI mode)

Tool: `@modelcontextprotocol/inspector` via `npx`, CLI mode, against the real server on 127.0.0.1:8765 with the real key and token loaded from `roli/.env`. The token was passed in the header from a shell variable and never printed; outputs below were filtered for it before saving.

Command shape (token redacted):

```text
npx -y @modelcontextprotocol/inspector@latest --cli http://127.0.0.1:8765/mcp --transport http \
    --header "Authorization: Bearer <ROLI_MCP_TOKEN>" --method tools/list
npx -y @modelcontextprotocol/inspector@latest --cli http://127.0.0.1:8765/mcp --transport http \
    --header "Authorization: Bearer <ROLI_MCP_TOKEN>" --method tools/call \
    --tool-name roli_get_usda_nutrition --tool-arg fdc_id=171999
npx -y @modelcontextprotocol/inspector@latest --cli http://127.0.0.1:8765/mcp --transport http \
    --header "Authorization: Bearer <ROLI_MCP_TOKEN>" --method tools/call \
    --tool-name roli_search_usda_foods --tool-arg "query=salmon chinook cooked dry heat" limit=3
```

**Result: verification complete.** Both tools are discovered and both return the expected structured output.

`tools/list`:

```json
{
  "tools": [
    {
      "name": "roli_search_usda_foods",
      "description": "Search USDA FoodData Central for one ingredient. Returns candidate foods with FDC ID, USDA's exact description and data type, and no nutrient values; call roli_get_usda_nutrition with the chosen FDC ID to get those. Searches SR Legacy and Foundation foods only. USDA matches words, not synonyms: use USDA wording (food, then species or variety, then preparation), e.g. \"salmon chinook cooked dry heat\", not \"king salmon\". Results are in USDA's order, and the first is not necessarily right. Pick the candidate whose description names the same food and preparation. If none does, search again with different words or say that no match was found. Never invent an FDC ID. Inputs: query (1–200 characters), limit (1–10, default 5).",
      "inputSchema": {
        "type": "object",
        "properties": {
          "query": {
            "title": "Query",
            "type": "string"
          },
          "limit": {
            "default": 5,
            "title": "Limit",
            "type": "integer"
          }
        },
        "required": [
          "query"
        ],
        "title": "roli_search_usda_foodsArguments"
      },
      "outputSchema": {
        "type": "object",
        "additionalProperties": true,
        "title": "roli_search_usda_foodsDictOutput"
      },
      "annotations": {
        "readOnlyHint": true,
        "idempotentHint": true,
        "openWorldHint": true
      }
    },
    {
      "name": "roli_get_usda_nutrition",
      "description": "Returns saturated fat (g) and cholesterol (mg) per 100 g for exactly one USDA food, identified by FDC ID. The values belong only to the food named in \"description\" and the \"fdc_id\" in the same response; never pair them with another food or ID. null means USDA reports no value for that nutrient: never replace it with zero or an estimate. status is \"complete\", \"partial\" (one or both values missing) or \"error\" (no values; see error_code). SR Legacy and Foundation foods only.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "fdc_id": {
            "title": "Fdc Id",
            "type": "integer"
          }
        },
        "required": [
          "fdc_id"
        ],
        "title": "roli_get_usda_nutritionArguments"
      },
      "outputSchema": {
        "type": "object",
        "additionalProperties": true,
        "title": "roli_get_usda_nutritionDictOutput"
      },
      "annotations": {
        "readOnlyHint": true,
        "idempotentHint": true,
        "openWorldHint": true
      }
    }
  ]
}
```

`tools/call roli_get_usda_nutrition fdc_id=171999` (live USDA):

```json
{
  "content": [
    {
      "type": "text",
      "text": "{\n  \"status\": \"complete\",\n  \"fdc_id\": 171999,\n  \"description\": \"Fish, salmon, chinook, cooked, dry heat\",\n  \"data_type\": \"SR Legacy\",\n  \"basis\": \"per_100g\",\n  \"saturated_fat_g\": 3.214,\n  \"cholesterol_mg\": 85.0,\n  \"missing_nutrients\": [],\n  \"nutrient_ids\": {\n    \"saturated_fat_g\": 1258,\n    \"cholesterol_mg\": 1253\n  },\n  \"source\": \"USDA FoodData Central\"\n}"
    }
  ],
  "structuredContent": {
    "status": "complete",
    "fdc_id": 171999,
    "description": "Fish, salmon, chinook, cooked, dry heat",
    "data_type": "SR Legacy",
    "basis": "per_100g",
    "saturated_fat_g": 3.214,
    "cholesterol_mg": 85,
    "missing_nutrients": [],
    "nutrient_ids": {
      "saturated_fat_g": 1258,
      "cholesterol_mg": 1253
    },
    "source": "USDA FoodData Central"
  },
  "isError": false
}
```

One display note: the Inspector prints `"cholesterol_mg": 85` inside `structuredContent` and `85.0` inside the text block. Both are the same JSON number; JavaScript drops the `.0` when printing. Test M compares parsed values, and 85 equals 85.0.

`tools/call roli_search_usda_foods query="salmon chinook cooked dry heat" limit=3` (live USDA):

```json
{
  "content": [
    {
      "type": "text",
      "text": "{\n  \"status\": \"complete\",\n  \"query\": \"salmon chinook cooked dry heat\",\n  \"candidates\": [\n    {\n      \"fdc_id\": 171999,\n      \"description\": \"Fish, salmon, chinook, cooked, dry heat\",\n      \"data_type\": \"SR Legacy\"\n    },\n    {\n      \"fdc_id\": 172000,\n      \"description\": \"Fish, salmon, chum, cooked, dry heat\",\n      \"data_type\": \"SR Legacy\"\n    },\n    {\n      \"fdc_id\": 172001,\n      \"description\": \"Fish, salmon, pink, cooked, dry heat\",\n      \"data_type\": \"SR Legacy\"\n    }\n  ],\n  \"source\": \"USDA FoodData Central\"\n}"
    }
  ],
  "structuredContent": {
    "status": "complete",
    "query": "salmon chinook cooked dry heat",
    "candidates": [
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
      }
    ],
    "source": "USDA FoodData Central"
  },
  "isError": false
}
```

To repeat the check by hand:

1. `PORT=8765 nutrition_service/.venv/bin/python -m roli_nutrition.mcp_server`
2. In another terminal, run the three commands above with the real token in place of `<ROLI_MCP_TOKEN>` (read it from `roli/.env`; do not paste it anywhere that is saved).
3. Expect two tools in the list and `"isError": false` on both calls. For the visual Inspector instead, run `npx -y @modelcontextprotocol/inspector@latest`, choose transport "Streamable HTTP", URL `http://127.0.0.1:8765/mcp`, and add the `Authorization` header under the connection's header settings.

## 8. Deviations from the spec and Julius's requirements

1. **Strict integer arguments.** Spec 7.1 says the MCP layer checks JSON types. The SDK's default is lax: it turned `true` into `1`, `"171999"` into `171999` and `2.0` into `2` in a probe, so `fdc_id: true` would have fetched food 1. The tools therefore declare `Annotated[int, Field(strict=True)]`; non-integers are rejected by the SDK with `isError: true` before the service runs. The value rules (≥ 1, 1..10) stay in the service as the spec says.
2. **Every path is protected, not only `/mcp`.** The spec names `/mcp`. Nothing else is served, so the middleware rejects every unauthenticated HTTP request. A health endpoint for hosting, if wanted in 1C, would need an explicit exemption.
3. **`Bearer` scheme compared case-insensitively** (`bearer`, `BEARER` accepted, as RFC 7235 allows); the token itself is compared byte for byte. Everything else about the header is strict: exactly two parts, one header.
4. **Return type is `dict[str, Any]` with `structured_output=True`, not the Pydantic models.** The SDK wraps a union return type (`NutritionResult | ErrorResult`) under a `result` key, which would have made the MCP JSON differ from the service JSON. A plain dict is passed through unchanged.
5. **Tool annotations and an `instructions` string were added** (`readOnlyHint`, `idempotentHint`, `openWorldHint`, and two sentences of server instructions). Metadata only; no behaviour.
6. **`create_app` attaches `.inner`** so tests and the benchmark can run the SDK's lifespan by hand. The SDK's session manager can be started only once per app, which also shaped the benchmark (one app per phase).
7. **`HOST` environment variable** added next to `PORT`, default 127.0.0.1.
8. **The MCP SDK v2 depends on `httpx2`**, a separate package from the `httpx` 0.28 the core uses. Both are installed side by side; the core's dependency list is unchanged.
9. **DNS-rebinding protection is left at the SDK default**, which accepts only `Host: 127.0.0.1:<port>` or `localhost:<port>` and answers 421 to anything else. A Cloudflare Tunnel or ngrok hostname will be rejected until `transport_security` is configured; the spec already lists this for the 1C README.
10. **The Inspector's wrong-token case** could not be shown as a plain 401 from the Inspector itself (it switches to an OAuth flow and stops). The 401 is verified by curl, the tests and the server log instead.
11. **Benchmarks are overhead-only** (mock USDA). Real cold calls add 200 to 650 ms of USDA time on top, as measured in Checkpoint 1A.
12. **`requirements.txt` with exact pins is still deferred to 1C**, as agreed at Checkpoint 1A.

## 9. Open questions

1. Should a token-free `GET /health` exist for the hosting platform in 1C (deviation 2)? Recommendation: yes, returning only `{"status": "ok"}` and never touching USDA.
2. Hosts to allow for the tunnel in 1C (deviation 9): recommendation is an `ROLI_MCP_ALLOWED_HOSTS` variable read by `main()` only, so the core stays untouched.

## 10. Not done, by design

- No Dockerfile, README or pinned `requirements.txt` (Phase 1C).
- Nothing deployed. No tunnel opened. The server ran only on 127.0.0.1 and was stopped.
- `code/`, `menu_reader_eval/`, `menu_test_set/`, `results/`, the root `.venv` and `requirements.txt`, the LangGraph implementation and the Agent Builder agent are unchanged. One pytest run was started from the wrong folder by mistake; the three cache artefacts it created in the repo root and in `code/__pycache__/` were removed, and nothing else there was touched.
- Neither the USDA key nor the MCP token appears in any file under `nutrition_service/`, in this report, or in the test report.

**Stopped here. Phase 1C starts only after your review.**
