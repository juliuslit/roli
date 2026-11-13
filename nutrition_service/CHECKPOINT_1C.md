# Checkpoint 1C: package, deployment configuration, README

Date: 2026-11-01. Spec: `SPEC.md` v2.1, section 14, Phase 1C, plus Julius's Phase 1C requirements (health endpoint, allowlists, factory, Docker image security). Status: **Phase 1C complete; stopped. Nothing deployed, no tunnel opened, no LangSmith connection changed, neither Roli implementation touched.**

## 1. Summary

| Item | Result |
|---|---|
| Full suite, offline (1A + 1B + 1C) | **202 passed, 4 skipped** (live), 0 failed |
| Live tests | **4 passed** |
| New in 1C | 46 tests: health (7), Host allowlist (12), Origin (6), allowlist parsing (19), factory (2) |
| `GET /health` | public, any Host, `{"status": "ok"}`, touches nothing; every other path still 401 |
| Host allowlist | `ROLI_MCP_ALLOWED_HOSTS`, validated at app construction, passed to the SDK's `TransportSecuritySettings`; unlisted Host → 421 |
| Origin | absent → accepted; present → checked against `ROLI_MCP_ALLOWED_ORIGINS`, mismatch → 403 |
| Factory | `create_app()` works with no arguments for `uvicorn --factory`; import needs no secrets and starts nothing |
| Container startup path | verified locally with the exact `uvicorn ... --factory` command and environment variables only: refusals, health, 401, 421, 403, live call |
| Docker build | **not run: no Docker or other container runtime on this Mac.** Build steps simulated in a clean venv from a `.dockerignore`-filtered context (section 6) |
| Image secret check | could not be run on a real image; the filtered build context contains no `.env` and no credential, and both startup logs were scanned (0 occurrences) |
| `requirements.txt` | 32 exact pins (core + `[mcp]`, no dev packages), generated from a clean Python 3.13 venv |
| README | written: setup, tests, LangGraph import, local server, tunnel, hosting, Docker, LangSmith connection, security, troubleshooting |

## 2. What changed, in plain language

**`mcp_server.py`** gained a front door and a factory.

- The front door (`FrontDoor`, replacing `BearerTokenMiddleware`) now has two steps: `GET /health` is answered immediately with `{"status": "ok"}`, with no token and whatever the `Host` header says, so a hosting platform's probe (which uses an internal hostname) can see the container is alive. Everything else needs the bearer token, exactly as before. After the token, the SDK checks the `Host` header against the allowlist and, if a browser sent an `Origin` header, checks that too.
- `create_app()` can now be called with no arguments. It reads and validates `USDA_FDC_API_KEY`, `ROLI_MCP_TOKEN`, `ROLI_MCP_ALLOWED_HOSTS` and `ROLI_MCP_ALLOWED_ORIGINS` at that moment and raises `ConfigError` if any is unusable. This is what `uvicorn roli_nutrition.mcp_server:create_app --factory` calls in the container. `main()` still loads `roli/.env` first for local runs. Tests pass `service`, `token` or `security` directly to skip the environment.
- Allowlist rules: comma-separated; exact value or trailing `:*` for any port; `*`, `*.example.com`, empty entries, whitespace and URLs-as-hosts are rejected before the server starts. DNS-rebinding protection is always on. Defaults allow only `127.0.0.1:*` and `localhost:*` (hosts) and `http://127.0.0.1:*`, `http://localhost:*` (origins).

**New files:** `Dockerfile` (`python:3.13-slim`, pinned install, unprivileged user `roli`, `PORT`, factory command), `.dockerignore` (excludes `.env*`, `.venv`, tests, fixtures, scripts, reports, markdown), `requirements.txt`, `README.md`. `.env.example` lists the two new variables.

**Unchanged:** the core library. `mcp_server.py` is still not imported by `roli_nutrition/__init__.py`, and test O (fresh interpreter) still passes.

## 3. Test results

Offline 202 passed, 4 skipped (live tests); live 4 passed. Exactly as saved in `test_report_1C.txt`:

```text
============================= test session starts ==============================
platform darwin -- Python 3.13.5, pytest-8.4.2, pluggy-1.7.0 -- .venv/bin/python
cachedir: .pytest_cache
rootdir: /Users/juliuslitinskas/projects/roli/nutrition_service
configfile: pytest.ini
plugins: anyio-4.16.0
collecting ... collected 206 items

tests/test_isolation.py::test_o_core_imports_no_forbidden_modules PASSED [  0%]
tests/test_live.py::test_live_a_chinook SKIPPED (set ROLI_LIVE_TESTS...) [  0%]
tests/test_live.py::test_live_b_pink SKIPPED (set ROLI_LIVE_TESTS=1 ...) [  1%]
tests/test_live.py::test_live_search_king_salmon SKIPPED (set ROLI_L...) [  1%]
tests/test_live.py::test_live_not_found SKIPPED (set ROLI_LIVE_TESTS...) [  2%]
tests/test_mcp_server.py::test_l_exactly_two_tools_with_spec_names_and_descriptions PASSED [  2%]
tests/test_mcp_server.py::test_l_input_schemas PASSED                    [  3%]
tests/test_mcp_server.py::test_m_nutrition_tool_equals_service_output PASSED [  3%]
tests/test_mcp_server.py::test_m_search_tool_equals_service_output PASSED [  4%]
tests/test_mcp_server.py::test_m_search_default_limit_through_mcp PASSED [  4%]
tests/test_mcp_server.py::test_m_service_error_is_a_normal_tool_result PASSED [  5%]
tests/test_mcp_server.py::test_m_value_rules_come_back_in_our_error_shape PASSED [  5%]
tests/test_mcp_server.py::test_m_json_type_errors_are_rejected_by_the_mcp_layer[True] PASSED [  6%]
tests/test_mcp_server.py::test_m_json_type_errors_are_rejected_by_the_mcp_layer[171999] PASSED [  6%]
tests/test_mcp_server.py::test_m_json_type_errors_are_rejected_by_the_mcp_layer[2.0] PASSED [  7%]
tests/test_mcp_server.py::test_m_json_type_errors_are_rejected_by_the_mcp_layer[None] PASSED [  7%]
tests/test_mcp_server.py::test_m_calls_run_in_a_worker_thread_and_do_not_block_the_loop PASSED [  8%]
tests/test_mcp_server.py::test_n_unauthorised_requests_get_401_before_any_tool_runs[None] PASSED [  8%]
tests/test_mcp_server.py::test_n_unauthorised_requests_get_401_before_any_tool_runs[Bearer wrong-token-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx] PASSED [  9%]
tests/test_mcp_server.py::test_n_unauthorised_requests_get_401_before_any_tool_runs[Token test-only-token-0123456789abcdef0123456789abcdef0123456789abcdef] PASSED [  9%]
tests/test_mcp_server.py::test_n_unauthorised_requests_get_401_before_any_tool_runs[Bearer] PASSED [ 10%]
tests/test_mcp_server.py::test_n_unauthorised_requests_get_401_before_any_tool_runs[Bearer test-only-token-0123456789abcdef0123456789abcdef0123456789abcdef extra] PASSED [ 10%]
tests/test_mcp_server.py::test_n_unauthorised_requests_get_401_before_any_tool_runs[Bearertest-only-token-0123456789abcdef0123456789abcdef0123456789abcdef] PASSED [ 11%]
tests/test_mcp_server.py::test_n_unauthorised_requests_get_401_before_any_tool_runs[test-only-token-0123456789abcdef0123456789abcdef0123456789abcdef] PASSED [ 11%]
tests/test_mcp_server.py::test_n_unauthorised_requests_get_401_before_any_tool_runs[] PASSED [ 12%]
tests/test_mcp_server.py::test_n_right_token_works_and_scheme_is_case_insensitive PASSED [ 12%]
tests/test_mcp_server.py::test_n_other_methods_and_paths_are_also_protected PASSED [ 13%]
tests/test_mcp_server.py::test_n_wrong_token_through_official_client_fails_and_never_reaches_usda PASSED [ 13%]
tests/test_mcp_server.py::test_n_server_refuses_to_start_without_a_usable_token PASSED [ 14%]
tests/test_mcp_server.py::test_n_token_never_appears_in_logs PASSED      [ 14%]
tests/test_mcp_server.py::test_health_is_public_under_any_host[127.0.0.1:8000] PASSED [ 15%]
tests/test_mcp_server.py::test_health_is_public_under_any_host[localhost:8000] PASSED [ 15%]
tests/test_mcp_server.py::test_health_is_public_under_any_host[10.0.0.7:8080] PASSED [ 16%]
tests/test_mcp_server.py::test_health_is_public_under_any_host[internal.platform.local] PASSED [ 16%]
tests/test_mcp_server.py::test_health_is_public_under_any_host[evil.example] PASSED [ 16%]
tests/test_mcp_server.py::test_health_with_a_token_also_works_and_reveals_nothing PASSED [ 17%]
tests/test_mcp_server.py::test_health_exception_is_limited_to_get_health PASSED [ 17%]
tests/test_mcp_server.py::test_hosts_listed_are_accepted[mcp.example.com] PASSED [ 18%]
tests/test_mcp_server.py::test_hosts_listed_are_accepted[localhost:8000] PASSED [ 18%]
tests/test_mcp_server.py::test_hosts_listed_are_accepted[localhost:65000] PASSED [ 19%]
tests/test_mcp_server.py::test_hosts_listed_are_accepted[tunnel.trycloudflare.com:443] PASSED [ 19%]
tests/test_mcp_server.py::test_hosts_unlisted_get_421_even_with_a_valid_token[evil.example] PASSED [ 20%]
tests/test_mcp_server.py::test_hosts_unlisted_get_421_even_with_a_valid_token[mcp.example.com:8443] PASSED [ 20%]
tests/test_mcp_server.py::test_hosts_unlisted_get_421_even_with_a_valid_token[127.0.0.1:8000] PASSED [ 21%]
tests/test_mcp_server.py::test_hosts_unlisted_get_421_even_with_a_valid_token[localhost] PASSED [ 21%]
tests/test_mcp_server.py::test_hosts_unlisted_get_421_even_with_a_valid_token[notlocalhost:8000] PASSED [ 22%]
tests/test_mcp_server.py::test_hosts_unlisted_get_421_even_with_a_valid_token[mcp.example.com.evil.net] PASSED [ 22%]
tests/test_mcp_server.py::test_hosts_unauthenticated_request_to_bad_host_gets_401_not_421 PASSED [ 23%]
tests/test_mcp_server.py::test_health_works_where_mcp_rejects_the_host PASSED [ 23%]
tests/test_mcp_server.py::test_origin_absent_is_accepted_for_server_to_server_clients PASSED [ 24%]
tests/test_mcp_server.py::test_origin_present_is_checked_against_the_allowlist[https://agent.example.com-200] PASSED [ 24%]
tests/test_mcp_server.py::test_origin_present_is_checked_against_the_allowlist[http://localhost:5173-200] PASSED [ 25%]
tests/test_mcp_server.py::test_origin_present_is_checked_against_the_allowlist[http://localhost-403] PASSED [ 25%]
tests/test_mcp_server.py::test_origin_present_is_checked_against_the_allowlist[https://evil.example-403] PASSED [ 26%]
tests/test_mcp_server.py::test_origin_present_is_checked_against_the_allowlist[http://agent.example.com-403] PASSED [ 26%]
tests/test_mcp_server.py::test_allowlist_defaults_when_unset_or_blank PASSED [ 27%]
tests/test_mcp_server.py::test_allowlist_parsing_trims_and_keeps_order PASSED [ 27%]
tests/test_mcp_server.py::test_allowlist_rejects_unrestricted_wildcards_and_junk_hosts[*] PASSED [ 28%]
tests/test_mcp_server.py::test_allowlist_rejects_unrestricted_wildcards_and_junk_hosts[*:*] PASSED [ 28%]
tests/test_mcp_server.py::test_allowlist_rejects_unrestricted_wildcards_and_junk_hosts[*.example.com] PASSED [ 29%]
tests/test_mcp_server.py::test_allowlist_rejects_unrestricted_wildcards_and_junk_hosts[localhost:*,*] PASSED [ 29%]
tests/test_mcp_server.py::test_allowlist_rejects_unrestricted_wildcards_and_junk_hosts[a.com,] PASSED [ 30%]
tests/test_mcp_server.py::test_allowlist_rejects_unrestricted_wildcards_and_junk_hosts[,a.com] PASSED [ 30%]
tests/test_mcp_server.py::test_allowlist_rejects_unrestricted_wildcards_and_junk_hosts[a.com,,b.com] PASSED [ 31%]
tests/test_mcp_server.py::test_allowlist_rejects_unrestricted_wildcards_and_junk_hosts[a com] PASSED [ 31%]
tests/test_mcp_server.py::test_allowlist_rejects_unrestricted_wildcards_and_junk_hosts[https://a.com] PASSED [ 32%]
tests/test_mcp_server.py::test_allowlist_rejects_unrestricted_wildcards_and_junk_hosts[:*] PASSED [ 32%]
tests/test_mcp_server.py::test_allowlist_rejects_bad_origins[*] PASSED   [ 33%]
tests/test_mcp_server.py::test_allowlist_rejects_bad_origins[https://*] PASSED [ 33%]
tests/test_mcp_server.py::test_allowlist_rejects_bad_origins[agent.example.com] PASSED [ 33%]
tests/test_mcp_server.py::test_allowlist_rejects_bad_origins[ftp://a.com] PASSED [ 34%]
tests/test_mcp_server.py::test_allowlist_rejects_bad_origins[https://a.com,] PASSED [ 34%]
tests/test_mcp_server.py::test_allowlist_from_env_reaches_the_sdk_settings PASSED [ 35%]
tests/test_mcp_server.py::test_bad_allowlist_stops_app_construction PASSED [ 35%]
tests/test_mcp_server.py::test_factory_module_imports_without_any_secrets PASSED [ 36%]
tests/test_mcp_server.py::test_factory_with_no_arguments_reads_the_environment PASSED [ 36%]
tests/test_nutrients.py::test_a_chinook_complete PASSED                  [ 37%]
tests/test_nutrients.py::test_b_pink_complete PASSED                     [ 37%]
tests/test_nutrients.py::test_b_chinook_never_carries_pink_values PASSED [ 38%]
tests/test_nutrients.py::test_i_unfiltered_equivalence[171999-food_171999-food_171999_unfiltered] PASSED [ 38%]
tests/test_nutrients.py::test_i_unfiltered_equivalence[172001-food_172001-food_172001_unfiltered] PASSED [ 39%]
tests/test_nutrients.py::test_i_unfiltered_has_heading_rows_without_amount PASSED [ 39%]
tests/test_nutrients.py::test_d_cholesterol_row_removed PASSED           [ 40%]
tests/test_nutrients.py::test_d_row_present_without_amount PASSED        [ 40%]
tests/test_nutrients.py::test_d_amount_null PASSED                       [ 41%]
tests/test_nutrients.py::test_d_empty_food_nutrients PASSED              [ 41%]
tests/test_nutrients.py::test_d_missing_never_becomes_zero PASSED        [ 42%]
tests/test_nutrients.py::test_d_real_foundation_plant_food PASSED        [ 42%]
tests/test_nutrients.py::test_real_foundation_animal_food PASSED         [ 43%]
tests/test_nutrients.py::test_e_id_mismatch PASSED                       [ 43%]
tests/test_nutrients.py::test_f_body_not_object[not an object] PASSED    [ 44%]
tests/test_nutrients.py::test_f_body_not_object[42] PASSED               [ 44%]
tests/test_nutrients.py::test_f_body_not_object[None] PASSED             [ 45%]
tests/test_nutrients.py::test_f_body_not_object[body3] PASSED            [ 45%]
tests/test_nutrients.py::test_f_fdcid_wrong_type[None] PASSED            [ 46%]
tests/test_nutrients.py::test_f_fdcid_wrong_type[171999] PASSED          [ 46%]
tests/test_nutrients.py::test_f_fdcid_wrong_type[171999.0] PASSED        [ 47%]
tests/test_nutrients.py::test_f_fdcid_wrong_type[True] PASSED            [ 47%]
tests/test_nutrients.py::test_f_fdcid_missing PASSED                     [ 48%]
tests/test_nutrients.py::test_f_required_field_missing[description] PASSED [ 48%]
tests/test_nutrients.py::test_f_required_field_missing[dataType] PASSED  [ 49%]
tests/test_nutrients.py::test_f_required_field_missing[foodNutrients] PASSED [ 49%]
tests/test_nutrients.py::test_f_description_wrong[] PASSED               [ 50%]
tests/test_nutrients.py::test_f_description_wrong[None] PASSED           [ 50%]
tests/test_nutrients.py::test_f_description_wrong[5] PASSED              [ 50%]
tests/test_nutrients.py::test_f_unsupported_data_type[Branded] PASSED    [ 51%]
tests/test_nutrients.py::test_f_unsupported_data_type[Survey (FNDDS)] PASSED [ 51%]
tests/test_nutrients.py::test_f_unsupported_data_type[Experimental] PASSED [ 52%]
tests/test_nutrients.py::test_f_unsupported_data_type[sr legacy] PASSED  [ 52%]
tests/test_nutrients.py::test_f_real_branded_detail PASSED               [ 53%]
tests/test_nutrients.py::test_f_v8_id_number_mismatch_on_selected_row PASSED [ 53%]
tests/test_nutrients.py::test_f_v8_number_claims_target_but_id_differs PASSED [ 54%]
tests/test_nutrients.py::test_f_v9_duplicate_row_same_amount PASSED      [ 54%]
tests/test_nutrients.py::test_f_v10_unit_mismatch_on_saturated_fat[mg] PASSED [ 55%]
tests/test_nutrients.py::test_f_v10_unit_mismatch_on_saturated_fat[MG] PASSED [ 55%]
tests/test_nutrients.py::test_f_v10_unit_mismatch_on_saturated_fat[kcal] PASSED [ 56%]
tests/test_nutrients.py::test_f_v10_unit_mismatch_on_saturated_fat[None] PASSED [ 56%]
tests/test_nutrients.py::test_f_v10_unit_case_is_ignored PASSED          [ 57%]
tests/test_nutrients.py::test_f_v12_invalid_amount[-1] PASSED            [ 57%]
tests/test_nutrients.py::test_f_v12_invalid_amount[3.2] PASSED           [ 58%]
tests/test_nutrients.py::test_f_v12_invalid_amount[True] PASSED          [ 58%]
tests/test_nutrients.py::test_f_v12_invalid_amount[nan] PASSED           [ 59%]
tests/test_nutrients.py::test_f_v12_invalid_amount[inf] PASSED           [ 59%]
tests/test_nutrients.py::test_v13_zero_is_returned_as_zero PASSED        [ 60%]
tests/test_nutrients.py::test_v14_no_rounding PASSED                     [ 60%]
tests/test_nutrients.py::test_v7_row_id_is_never_used PASSED             [ 61%]
tests/test_nutrients.py::test_v7_rows_without_nutrient_object_are_skipped PASSED [ 61%]
tests/test_nutrients.py::test_c_search_candidates_match_usda_order PASSED [ 62%]
tests/test_nutrients.py::test_c_candidates_carry_no_nutrient_fields PASSED [ 62%]
tests/test_nutrients.py::test_c_records_whether_171999_appears 
[recorded] 'king salmon cooked dry heat' candidates: [174236, 171999, 172000, 172001, 173692, 175168, 171998, 173716, 173719, 174229]; contains 171999: True
PASSED    [ 63%]
tests/test_nutrients.py::test_c_other_data_types_are_dropped_and_logged PASSED [ 63%]
tests/test_nutrients.py::test_c_zero_results_is_not_an_error PASSED      [ 64%]
tests/test_nutrients.py::test_c_malformed_search[text] PASSED            [ 64%]
tests/test_nutrients.py::test_c_malformed_search[None] PASSED            [ 65%]
tests/test_nutrients.py::test_c_malformed_search[body2] PASSED           [ 65%]
tests/test_nutrients.py::test_c_malformed_search[body3] PASSED           [ 66%]
tests/test_nutrients.py::test_c_malformed_search[body4] PASSED           [ 66%]
tests/test_nutrients.py::test_c_parse_search_limit_applies_after_dropping_unsupported_types PASSED [ 66%]
tests/test_service.py::test_a_chinook_through_service PASSED             [ 67%]
tests/test_service.py::test_b_pink_through_service PASSED                [ 67%]
tests/test_service.py::test_b_isolation_with_cache[order0] PASSED        [ 68%]
tests/test_service.py::test_b_isolation_with_cache[order1] PASSED        [ 68%]
tests/test_service.py::test_b_isolation_without_cache[order0] PASSED     [ 69%]
tests/test_service.py::test_b_isolation_without_cache[order1] PASSED     [ 69%]
tests/test_service.py::test_c_search_through_service PASSED              [ 70%]
tests/test_service.py::test_c_search_default_limit_is_five PASSED        [ 70%]
tests/test_service.py::test_c_chinook_search_fixture_parses PASSED       [ 71%]
tests/test_service.py::test_f_invalid_fdc_id[0] PASSED                   [ 71%]
tests/test_service.py::test_f_invalid_fdc_id[-1] PASSED                  [ 72%]
tests/test_service.py::test_f_invalid_fdc_id[True] PASSED                [ 72%]
tests/test_service.py::test_f_invalid_fdc_id[1.5] PASSED                 [ 73%]
tests/test_service.py::test_f_invalid_fdc_id[171999] PASSED              [ 73%]
tests/test_service.py::test_f_invalid_fdc_id[None] PASSED                [ 74%]
tests/test_service.py::test_f_invalid_search_input[-5] PASSED            [ 74%]
tests/test_service.py::test_f_invalid_search_input[   -5] PASSED         [ 75%]
tests/test_service.py::test_f_invalid_search_input[xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-5] PASSED [ 75%]
tests/test_service.py::test_f_invalid_search_input[None-5] PASSED        [ 76%]
tests/test_service.py::test_f_invalid_search_input[5-5] PASSED           [ 76%]
tests/test_service.py::test_f_invalid_search_input[salmon-0] PASSED      [ 77%]
tests/test_service.py::test_f_invalid_search_input[salmon-11] PASSED     [ 77%]
tests/test_service.py::test_f_invalid_search_input[salmon-True] PASSED   [ 78%]
tests/test_service.py::test_f_invalid_search_input[salmon-2.0] PASSED    [ 78%]
tests/test_service.py::test_f_invalid_search_input[salmon-5] PASSED      [ 79%]
tests/test_service.py::test_f_limit_is_rejected_not_capped PASSED        [ 79%]
tests/test_service.py::test_f_saved_404_not_found PASSED                 [ 80%]
tests/test_service.py::test_f_saved_403_auth_failed PASSED               [ 80%]
tests/test_service.py::test_f_429_rate_limited_one_request PASSED        [ 81%]
tests/test_service.py::test_f_503_three_times_unavailable PASSED         [ 81%]
tests/test_service.py::test_f_timeout_then_200 PASSED                    [ 82%]
tests/test_service.py::test_f_non_json_body_malformed PASSED             [ 82%]
tests/test_service.py::test_f_id_mismatch_returns_no_values PASSED       [ 83%]
tests/test_service.py::test_f_validation_failed_names_rule PASSED        [ 83%]
tests/test_service.py::test_search_usda_failure_carries_query PASSED     [ 83%]
tests/test_service.py::test_g_nutrition_shape_and_size PASSED            [ 84%]
tests/test_service.py::test_g_partial_shape PASSED                       [ 84%]
tests/test_service.py::test_g_search_shape_and_size PASSED               [ 85%]
tests/test_service.py::test_g_error_shape PASSED                         [ 85%]
tests/test_service.py::test_j_second_call_makes_no_request PASSED        [ 86%]
tests/test_service.py::test_j_search_is_cached_case_insensitively PASSED [ 86%]
tests/test_service.py::test_j_errors_are_not_cached PASSED               [ 87%]
tests/test_service.py::test_j_ttl_expiry_refetches PASSED                [ 87%]
tests/test_service.py::test_j_lru_eviction PASSED                        [ 88%]
tests/test_service.py::test_j_entry_with_wrong_fdc_id_is_dropped PASSED  [ 88%]
tests/test_service.py::test_k_log_lines_are_json_with_documented_fields PASSED [ 89%]
tests/test_service.py::test_k_failures_never_leak_key PASSED             [ 89%]
tests/test_service.py::test_p_twenty_threads_get_their_own_food PASSED   [ 90%]
tests/test_service.py::test_limit_caps_candidates_even_if_usda_returns_more PASSED [ 90%]
tests/test_usda_client.py::test_h_detail_request_shape PASSED            [ 91%]
tests/test_usda_client.py::test_h_search_request_shape PASSED            [ 91%]
tests/test_usda_client.py::test_f_saved_404_is_not_found PASSED          [ 92%]
tests/test_usda_client.py::test_f_saved_403_is_auth_failed PASSED        [ 92%]
tests/test_usda_client.py::test_f_saved_400_is_unavailable PASSED        [ 93%]
tests/test_usda_client.py::test_f_429_rate_limited_after_exactly_one_request PASSED [ 93%]
tests/test_usda_client.py::test_f_503_three_times_is_unavailable_after_three_requests PASSED [ 94%]
tests/test_usda_client.py::test_f_other_5xx_retry_then_fail[500] PASSED  [ 94%]
tests/test_usda_client.py::test_f_other_5xx_retry_then_fail[502] PASSED  [ 95%]
tests/test_usda_client.py::test_f_other_5xx_retry_then_fail[504] PASSED  [ 95%]
tests/test_usda_client.py::test_f_timeout_then_200_succeeds_after_two_requests PASSED [ 96%]
tests/test_usda_client.py::test_f_connection_error_three_times PASSED    [ 96%]
tests/test_usda_client.py::test_f_non_json_body_is_malformed PASSED      [ 97%]
tests/test_usda_client.py::test_f_unexpected_status_is_unavailable[201] PASSED [ 97%]
tests/test_usda_client.py::test_f_unexpected_status_is_unavailable[301] PASSED [ 98%]
tests/test_usda_client.py::test_f_unexpected_status_is_unavailable[401] PASSED [ 98%]
tests/test_usda_client.py::test_f_unexpected_status_is_unavailable[418] PASSED [ 99%]
tests/test_usda_client.py::test_search_404_is_unavailable_not_not_found PASSED [ 99%]
tests/test_usda_client.py::test_k_error_messages_never_contain_usda_text_or_key PASSED [100%]

=========================== short test summary info ============================
SKIPPED [1] tests/test_live.py:25: set ROLI_LIVE_TESTS=1 to call USDA
SKIPPED [1] tests/test_live.py:33: set ROLI_LIVE_TESTS=1 to call USDA
SKIPPED [1] tests/test_live.py:40: set ROLI_LIVE_TESTS=1 to call USDA
SKIPPED [1] tests/test_live.py:46: set ROLI_LIVE_TESTS=1 to call USDA
======================== 202 passed, 4 skipped in 2.55s ========================
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

============================== 4 passed in 1.92s ===============================
```

Phase 1C tests, all in `tests/test_mcp_server.py`:

| Requirement | Tests |
|---|---|
| Health public under any Host, reveals nothing, no USDA | `test_health_is_public_under_any_host` (5 hosts incl. `internal.platform.local`, `evil.example`), `test_health_with_a_token_also_works_and_reveals_nothing` |
| Exception limited to `GET /health` | `test_health_exception_is_limited_to_get_health`: `POST /health`, `/healthz`, `/health/`, `/health/x`, `GET /mcp`, `/` all 401 |
| Listed hosts accepted, incl. `name:*` | `test_hosts_listed_are_accepted` (4 cases) |
| Unlisted hosts 421 even with a valid token, no USDA | `test_hosts_unlisted_get_421_even_with_a_valid_token` (6 cases incl. `mcp.example.com.evil.net`, bare `localhost`) |
| Auth before host check | `test_hosts_unauthenticated_request_to_bad_host_gets_401_not_421` |
| `/health` works where `/mcp` rejects the Host | `test_health_works_where_mcp_rejects_the_host` |
| No Origin accepted | `test_origin_absent_is_accepted_for_server_to_server_clients` |
| Origin present checked, port wildcard, scheme matters | `test_origin_present_is_checked_against_the_allowlist` (5 cases) |
| Parsing: defaults, trimming, order | `test_allowlist_defaults_when_unset_or_blank`, `test_allowlist_parsing_trims_and_keeps_order` |
| Wildcards and junk rejected | `test_allowlist_rejects_unrestricted_wildcards_and_junk_hosts` (10), `test_allowlist_rejects_bad_origins` (5) |
| Allowlist reaches the SDK; bad list stops construction | `test_allowlist_from_env_reaches_the_sdk_settings`, `test_bad_allowlist_stops_app_construction` |
| Import without secrets; factory with no args | `test_factory_module_imports_without_any_secrets` (fresh interpreter, empty environment, no new threads, nothing listening), `test_factory_with_no_arguments_reads_the_environment` |

## 4. Health endpoint behaviour (live server, exact container command, env vars only)

| Request | Result |
|---|---|
| `GET /health`, `Host: evil.example`, no token | 200 `{"status": "ok"}` |
| `GET /health`, `Host: 10.9.8.7:1234`, no token | 200 `{"status": "ok"}` |
| `POST /health` | 401 |
| `GET /healthz`, `GET /health/`, `GET /` | 401 |

The handler sends a fixed 16-byte body and returns. It does not read configuration, touch the service, the cache or USDA. In the simulated image run, the server log contained no secret and the health response contained nothing but the fixed body.

## 5. Hostname and Origin validation (live server, `ROLI_MCP_ALLOWED_HOSTS="localhost:*,mcp.example.com"`)

| Request to `/mcp` | Result |
|---|---|
| no token, `Host: localhost:8766` | 401 (auth first) |
| token, `Host: evil.example` | 421 `Invalid Host header` |
| token, `Host: 127.0.0.1:8766` (not listed this time) | 421 |
| token, `Host: mcp.example.com` | 200 |
| token, `Host: localhost:8766`, `Origin: https://evil.example` | 403 `Invalid Origin header` |
| token, `Host: localhost:8766`, no Origin | 200, two tools listed |
| token, `tools/call` 171999, live USDA | `complete`, 3.214 g, 85.0 mg |

Start-up refusals with the same command: no `ROLI_MCP_TOKEN` → exit 1, `ConfigError: ROLI_MCP_TOKEN is missing or blank`; `ROLI_MCP_ALLOWED_HOSTS="*"` → exit 1, `ConfigError: ROLI_MCP_ALLOWED_HOSTS: '*' is not allowed`. The `app_created` log line shows the parsed lists and nothing else.

## 6. Docker: what was and was not verified

**Not verified:** `docker build`, `docker run`, and the image-layer secret scan. There is no `docker`, `podman`, `colima`, `nerdctl` or Docker Desktop on this Mac. The README (section 7) gives the build, run and pass/fail secret-check commands to run on a machine that has Docker.

**Verified instead**, as close to the Dockerfile as possible without a daemon:

1. The build context was reproduced as `.dockerignore` leaves it: exactly `requirements.txt`, `pyproject.toml` and the nine files under `roli_nutrition/`. Zero `.env*` files, no tests, fixtures, scripts, reports or venv.
2. In a fresh Python 3.13 venv, `pip install -r requirements.txt` then `pip install --no-deps .` from that context installed cleanly; `pip check` found no broken requirements; no pytest, dotenv-for-tests or other dev packages were present (python-dotenv is in the `[mcp]` extra for local runs and is harmless in the image).
3. From that environment, with an empty process environment, `import roli_nutrition.mcp_server` succeeded and started nothing.
4. The container's command, `uvicorn roli_nutrition.mcp_server:create_app --factory --host ... --port $PORT`, was run from that environment with smoke-test credentials: `/health` answered 200 under a foreign Host, `/mcp` answered 401 without a token and 200 with it. The server log contained the smoke credentials zero times.
5. The same command was run from the development venv with the real key and token from environment variables (no `.env` load) for the live checks in sections 4 and 5.

What a real Docker run would add: confirmation that `python:3.13-slim` resolves, that the `useradd` step and non-root execution work, and the three secret checks (`docker history`, `docker inspect`, filesystem grep). The Dockerfile has no `ARG`, no `COPY .env`, and no `ENV` carrying a credential, so the only way a secret could enter the image is through the build context, which excludes it.

## 7. Deployment readiness

Ready to build and deploy on any container host once Docker is available somewhere:

1. `docker build -t roli-nutrition nutrition_service/`
2. Run the three secret checks from README section 7 (pass/fail only).
3. Set `USDA_FDC_API_KEY`, `ROLI_MCP_TOKEN`, `ROLI_MCP_ALLOWED_HOSTS=<public hostname>,localhost:*` and `PORT` as platform secrets/variables.
4. Point the platform's health check at `GET /health`.
5. In LangSmith: remote MCP server, `https://<host>/mcp`, header `Authorization: Bearer <ROLI_MCP_TOKEN>`.

For a first test without hosting, the README's tunnel section (cloudflared or ngrok) applies; the tunnel hostname must be added to `ROLI_MCP_ALLOWED_HOSTS` or every request gets 421. Cold-start caveat for scale-to-zero platforms is documented.

Measured overhead did not change with the factory: MCP adds a median 1.4 ms in-process and 2.0 ms over loopback HTTP; nutrition payload 300 B, full HTTP body 814 B (`scripts/benchmark_mcp.py`, re-run after the change).

## 8. Deviations from the spec and from the 1C requirements

1. **Docker build and image scan not executed** (no runtime available). Simulated as described in section 6; documented in the README.
2. **`ROLI_MCP_ALLOWED_ORIGINS` added.** The requirement says "continue enforcing the configured Origin allowlist"; the SDK has one, so it is exposed as a variable with the same syntax as the host list. Default allows localhost origins only.
3. **`/health` answers `GET` only.** `HEAD` and other methods fall through to the token check and get 401. Hosting platforms probe with `GET`.
4. **Auth runs before the Host check.** An unauthenticated request to a bad host gets 401, not 421, so a caller without the token learns nothing about allowed hosts. The requirement lists both checks; the order is a choice.
5. **The SDK matches `name:*` by prefix**, so `localhost:*` matches any `localhost:<anything>` string. The parser forbids wildcards anywhere else, and the test with `mcp.example.com.evil.net` confirms a listed exact host does not match a longer hostname.
6. **The `app_created` log line lists the allowed hosts and origins.** Not secrets, and useful when a 421 appears in production; mention in case Julius prefers quieter logs.
7. **`python-dotenv` is in the image** because the Dockerfile installs the `[mcp]` extra pins and `main()` uses it for local runs. The container command does not call `main()` and never reads a `.env` file.
8. **Spec 4 listed `test_mcp_server.py` only for 1B**; the 1C tests were added to the same file rather than a new one, since they test the same module.

## 9. Open questions

1. Where will Docker run? If Julius installs Docker Desktop or OrbStack on the Mac, the build and the three secret checks take about two minutes with the README commands; I can run them on request.
2. Keep or quiet the `app_created` log line (deviation 6)?

## 10. Not done, by design

- No tunnel opened, nothing deployed, LangSmith not touched.
- `code/`, `menu_reader_eval/`, `menu_test_set/`, `results/`, the root `.venv` and `requirements.txt`, the LangGraph implementation and the Agent Builder agent are unchanged. The repo root holds no pytest cache or report.
- Neither the USDA key nor the MCP token appears in any file under `nutrition_service/`, in this report, in the test report, or in any server log written during verification (all scanned: 0 occurrences).

**Stopped here. Phase 2 (LangGraph import, Agent Builder connection) starts only after your review.**
