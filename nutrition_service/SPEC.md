# Technical Specification: Roli USDA Nutrition Service (v2.4)

Status: approved by Julius, 2026-11-01. Replaces v1 and v2.
USDA details were checked against the official FDC API guide, the official OpenAPI spec, the api.data.gov developer manual, and live API calls on 2026-11-01 (section 5.6). A copy of the official OpenAPI spec is saved at `roli/fdc_api.json`.

## A. Instructions for the build

1. Read the project notes, then this spec. Explain your choices in plain language: Julius is learning the engineering side.
2. Work only inside `roli/nutrition_service/`. Do not change:
   - `code/`, `menu_reader_eval/`, `menu_test_set/`, `results/`, the root `requirements.txt` or the root `.venv`
   - the LangGraph implementation
   - the LangSmith Agent Builder agent
3. The USDA key is `USDA_FDC_API_KEY` in `roli/.env`. Check that it exists without printing it. Never print, log, copy or commit the key, and never open `.env` in output you show.
4. You have terminal and network access. Run `capture_fixtures.py` and the tests yourself, read the failures, and fix them.
5. If live USDA behavior differs from section 5.6, stop and report. Examples: the `X-Api-Key` header is rejected, or 171999 does not return 3.214 g and 85 mg. Never change expected values or validation rules just to make tests pass.
6. Use only the dependencies in section 3. Ask before adding any other.
7. **Stop at Checkpoint 1A (section 14).** Do not start Phase 1B until Julius approves.

## 0. What changed

| Area | v1 | v2.1 |
|---|---|---|
| Consumers | Agent Builder only | One shared Python library. LangGraph imports it directly; Agent Builder reaches it through a thin MCP wrapper |
| Problem split | One goal | Record integrity (this build) kept separate from record relevance (later) |
| Detail request | Format unclear | `GET /food/{id}?format=full&nutrients=606,601` only. Abridged format rounds values and has no nutrient IDs |
| Expected value, FDC 171999 | 3.21 g saturated fat | **3.214 g**. 3.21 is the abridged format's rounded figure |
| Nutrient matching | "IDs 1258 and 1253" | `foodNutrients[].nutrient.id`, cross-checked with `nutrient.number`. `foodNutrients[].id` is a row ID and is never read |
| Per-100 g basis | "validate" | Follows from data type; USDA documents SR Legacy and Foundation as per 100 g |
| Errors | Not defined | One error shape, 9 codes |
| 429 handling | Retry with backoff | No retry. USDA blocks the key for an hour |
| Fixtures | Mocked responses | Real saved USDA replies; failure cases are edited copies |
| Key transport | Unspecified | `X-Api-Key` header only |
| Core style | Unspecified | Synchronous core, no MCP or LangGraph imports. The MCP wrapper is added in Phase 1B |
| Who builds | Unspecified | Built locally (VS Code), stopping at Checkpoint 1A |

## 1. Objective

Provide one reusable Python library that returns saturated fat and cholesterol for one USDA food. The values are retrieved and checked by plain code, so a value can never be attached to the wrong food record.

Two consumers, one copy of the logic:
- **LangGraph** (the existing code-based Roli implementation) imports and calls the Python functions directly. It does not use MCP.
- **LangSmith Agent Builder** (a separate experimental prototype) calls the same functions through a thin MCP wrapper.

Two problems, kept separate:
- **Record integrity: solved here.** The values returned belong to the FDC ID returned, and come from one USDA record. Code enforces this, not a prompt. It fixes the failure where Chinook salmon's FDC ID (171999) was paired with Pink salmon's values (172001).
- **Record relevance: not solved here.** Picking the right USDA food for a menu item stays with the LLM, which chooses among a few candidates shown with USDA's exact descriptions. It gets measured separately later.

Second goal: efficiency. Small, fixed-shape replies, and as few USDA calls as possible.

## 2. Scope

Phase 1 delivers:
1. A standalone Python package `roli_nutrition` containing the USDA client, nutrient extraction and validation, and a service layer with a cache.
2. Two MCP tools wrapping that package (Phase 1B): `roli_search_usda_foods` and `roli_get_usda_nutrition`.
3. Tests built on saved real USDA replies.
4. A ready-to-deploy package plus instructions for connecting it to the LangSmith agent (Phase 1C).

Out of scope for Phase 1:
- Any change to the LangGraph implementation or the Agent Builder agent. Integrating with either is Phase 2, after the standalone tests pass and Julius approves.
- Survey (FNDDS), Branded and Experimental foods
- Looking up several FDC IDs in one call
- Dish calculation
- Any LLM call, menu reading or Telegram code
- Deployment
- Databases, Redis, or any outside cache

## 3. Environment and stack

- **Python 3.11 or later.** `requires-python = ">=3.11"`, so the package also installs in the LangGraph environment if that runs 3.11. Do not use 3.12-only syntax. The Mac has `/opt/anaconda3/bin/python3.13`; the Docker image uses `python:3.13-slim`.
- **Core (`roli_nutrition`):** `httpx` (sync `httpx.Client`) and Pydantic v2. Nothing else. The core never imports `mcp`, `langgraph`, `langchain`, `dotenv` or `uvicorn`.
- **Synchronous core, chosen so that:**
  - LangGraph sync nodes can call it directly, and async nodes through `asyncio.to_thread`
  - scripts can call it without any setup
  - the MCP wrapper can run each call in a worker thread
  - tests need no async plugin
- **Extra `[mcp]` (Phase 1B):**
  - MCP Python SDK **v2 line**, `mcp>=2,<3`. In v2, `FastMCP` was renamed `MCPServer` (`from mcp.server.mcpserver import MCPServer`), and `stateless_http`/`json_response` are arguments to `streamable_http_app()`/`run()`, not to the constructor. Do not use v1 tutorial code. Reference: https://py.sdk.modelcontextprotocol.io/
  - `uvicorn`, and `python-dotenv` for local runs.
- **Extra `[dev]`:** `pytest`, `python-dotenv`. Tests use `httpx.MockTransport`; no other mocking library.
- **Packaging:** `nutrition_service/pyproject.toml` declares package `roli_nutrition`, core dependencies with version ranges, and the two extras. `nutrition_service/requirements.txt` holds exact pins for Docker, generated after the tests pass.
- **Local environment:** `nutrition_service/.venv`, created with `/opt/anaconda3/bin/python3.13 -m venv nutrition_service/.venv`, then `pip install -e "nutrition_service[dev]"`. It is kept separate from the menu reader's root `.venv`.
- **Settings:** the core reads environment variables only and never opens files. Entry points (scripts, tests, the MCP server) load `roli/.env` with `python-dotenv` before building the service.

## 4. Project layout

```
roli/
  .env                          existing; has USDA_FDC_API_KEY (ROLI_MCP_TOKEN added in 1B)
  fdc_api.json                  official FDC OpenAPI spec (reference only)
  nutrition_service/
    SPEC.md                     this file
    CHECKPOINT_1A.md            written at Checkpoint 1A
    README.md                   1C
    pyproject.toml
    requirements.txt            exact pins, generated
    pytest.ini
    .env.example
    Dockerfile, .dockerignore   1C
    roli_nutrition/
      __init__.py               exports get_nutrition, search_foods, NutritionService, result models
      config.py                 Settings.from_env()
      usda_client.py            USDA communication only: requests, retries, status mapping
      nutrients.py              extraction + validation; pure functions, no network
      schemas.py                Pydantic models for outputs and errors
      service.py                NutritionService: client + validation + cache
      mcp_server.py             1B: thin MCP wrapper + bearer-token check (needs the [mcp] extra)
    scripts/
      capture_fixtures.py       saves real USDA replies
      demo.py                   prints outputs for the checkpoint
    tests/
      conftest.py               fixture loader, mutate() helper, mock transport, fake clock
      fixtures/usda/*.json      real saved replies
      fixtures/usda/manifest.json
      test_nutrients.py
      test_usda_client.py
      test_service.py
      test_isolation.py         no MCP or LangGraph imports in the core
      test_mcp_server.py        1B
      test_live.py              runs only with ROLI_LIVE_TESTS=1
```

## 5. USDA FoodData Central API

### 5.1 Base and authentication

- Base URL: `https://api.nal.usda.gov/fdc/v1`. A constant in code, not configurable. No request may go to any other host.
- Key: `USDA_FDC_API_KEY` from the environment. Never `DEMO_KEY`.
- Send the key only as the `X-Api-Key` request header, never in the URL.
  - The api.data.gov gateway in front of FDC documents this header. FDC's own OpenAPI spec (`fdc_api.json`) lists only the `api_key` query parameter.
  - The first call in `capture_fixtures.py` confirms the header works. If USDA answers 403, stop and report (section A.5). Do not switch to the query parameter.
- Rate limit: 1,000 requests per hour. Going over returns 429 and blocks the key for one hour.

### 5.2 Data types and basis

Allowed `dataType` values, spelled exactly: `"SR Legacy"`, `"Foundation"`.

Basis is per 100 g, and follows from the data type:
- FDC data dictionary, `food_nutrient.amount`: "Amount of the nutrient per 100g of food."
- Foundation Foods documentation: values are on a 100-gram basis of the edible portion.

Never read `foodPortions`, serving sizes or label nutrients. Any other `dataType` returns `unsupported_data_type`.

### 5.3 Detail request (Tool 2)

```
GET /food/{fdcId}?format=full&nutrients=606,601
Header: X-Api-Key: <key>
```

- `nutrients` takes nutrient **numbers**, not IDs: 606 is saturated fat (ID 1258) and 601 is cholesterol (ID 1253). The filter cuts the 171999 reply from 13.8 KB to 1.3 KB.
- If the food has neither nutrient, USDA returns the food with an empty `foodNutrients` list.
- Never use `format=abridged`. It returns `3.21` where the full record has `3.214`, gives units in capitals (`"G"`, `"MG"`) and carries no nutrient IDs.

Response paths, verified on 171999 and 172001:

| What | Path | Type |
|---|---|---|
| FDC ID | `fdcId` | integer |
| Description | `description` | string |
| Data type | `dataType` | string |
| Nutrient ID | `foodNutrients[].nutrient.id` | integer |
| Nutrient number | `foodNutrients[].nutrient.number` | **string** (`"606"`) |
| Unit | `foodNutrients[].nutrient.unitName` | string, lower case in full format (`"g"`, `"mg"`) |
| Amount | `foodNutrients[].amount` | number; may be absent |
| Row ID (never use) | `foodNutrients[].id` | integer, e.g. 1656908 |

In unfiltered full replies, heading rows ("Proximates", "Lipids", and so on) have no `amount`.

### 5.4 Search request (Tool 1)

```
POST /foods/search
Header: X-Api-Key: <key>; Content-Type: application/json
Body: {"query": "<query>", "dataType": ["Foundation", "SR Legacy"], "pageSize": <limit>}
```

- Do not set `sortBy`. Keep USDA's relevance order.
- Pass the query exactly as given, after trimming spaces at the ends. USDA supports search operators.
- From each `foods[]` entry, read only `fdcId`, `description` and `dataType`. Ignore the rest, including the rounded `foodNutrients` and `score`.
- Drop any result whose `dataType` is not allowed, and log it.
- Zero results is a normal result (`candidates: []`), not an error.

### 5.5 USDA status codes

| USDA reply | Service result |
|---|---|
| 200 | parse and validate |
| 400 (body `{"error":"Bad Request",...}`) | `usda_unavailable` (input is validated first, so this is unexpected) |
| 403 (`API_KEY_MISSING`, `API_KEY_INVALID`, ...) | `usda_auth_failed` |
| 404 (empty body) | `not_found` |
| 429 (`{"error":{"code":"OVER_RATE_LIMIT",...}}`) | `rate_limited`, no retry |
| 500, 502, 503, 504, timeout, connection error | retry, then `usda_unavailable` |
| anything else | `usda_unavailable` |

### 5.6 Verified on 2026-11-01 (live calls with DEMO_KEY)

| Check | Result |
|---|---|
| 171999 full | SR Legacy, "Fish, salmon, chinook, cooked, dry heat"; saturated fat 3.214 g, cholesterol 85 mg; 74 rows; 13.8 KB |
| 172001 full | SR Legacy, "Fish, salmon, pink, cooked, dry heat"; saturated fat 0.971 g, cholesterol 55 mg; 116 rows; 43.5 KB |
| One row per target nutrient | true for both foods |
| Rows without `amount` | 6 heading rows in each food |
| `full` + `nutrients=606,601` | 2 rows, same values as unfiltered, 1.3 KB |
| `abridged` + `nutrients=606,601` | 3.21 (rounded), `"G"`/`"MG"`, no nutrient ID |
| `/food/99999999`, `/food/0` | 404, empty body |
| `/food/abc` | 400, JSON body |
| Over the limit | 429, `OVER_RATE_LIMIT` |
| `X-Api-Key` header | not yet confirmed; confirmed by the first capture call |
| Search "king salmon cooked dry heat" | not yet run; captured by `capture_fixtures.py` |

## 6. Module contracts

**`config.py`**
- `Settings.from_env()` reads `USDA_FDC_API_KEY` (required), `ROLI_CACHE_TTL_SECONDS` (default 86400) and `ROLI_CACHE_MAX_ENTRIES` (default 1000).
- Raises `ConfigError` if the key is missing or blank. The message names the variable and never shows a value.

**`usda_client.py`**: talks to USDA only.
- `UsdaClient(api_key, *, transport=None, sleep=time.sleep)` wraps one shared `httpx.Client`: base URL constant, `X-Api-Key` header, timeouts of connect 5 s and read 10 s. `transport` and `sleep` are injected by tests.
- `get_food(fdc_id: int) -> dict`: the request in 5.3. `search(query: str, page_size: int) -> dict`: the request in 5.4.
- Raises `UsdaError(code, message)` using the 5.5 mapping. Messages never include the key, request headers or USDA's raw text.
- Retries: at most 2, after 0.5 s and 1.0 s, only on timeouts, connection errors and 500/502/503/504.
- Reports how many USDA requests each call made, for logging.

**`nutrients.py`**: pure functions with no network and no cache.
- `extract_nutrition(requested_fdc_id: int, body: Any) -> NutritionResult` applies section 10 in order. Its only input is one USDA reply.
- `parse_search(query: str, body: Any) -> SearchResult`.

**`schemas.py`**: Pydantic models `NutritionResult`, `SearchResult`, `Candidate` and `ErrorResult`, all with `extra="forbid"`.

**`service.py`**
- `NutritionService(settings, *, client=None, clock=time.monotonic)` provides `get_nutrition(fdc_id) -> NutritionResult | ErrorResult` and `search_foods(query, limit=5) -> SearchResult | ErrorResult`.
- Checks inputs (7.1, 8.1), calls the client, validates, caches (section 11), and logs one line per call.
- After construction, it never raises to its caller: every failure becomes an `ErrorResult`.
- Safe to call from several threads at once: one shared client, and the cache protected by a `threading.Lock`.
- Module-level `get_nutrition()` and `search_foods()` use a default service built from `Settings.from_env()` on first use.

**How LangGraph will call it (Phase 2; for reference only, do not implement now):**
```python
from roli_nutrition import get_nutrition, search_foods
r = get_nutrition(171999)                              # sync node
r = await asyncio.to_thread(get_nutrition, 171999)     # async node
state_update = r.model_dump()                          # plain dict
```
LangGraph's environment installs the core only (`pip install -e <roli>/nutrition_service`), so MCP is never installed there.

## 7. Tool 1: search foods

### 7.1 Input

| Field | Rule | If broken |
|---|---|---|
| `query` | string; trimmed; 1–200 characters | `invalid_input` |
| `limit` | integer 1–10; default 5; booleans rejected | `invalid_input` (rejected, not capped) |

In Phase 1B the MCP layer checks JSON types. The service checks the value rules, so range errors come back in our error shape.

### 7.2 Output

```json
{
  "status": "complete",
  "query": "salmon chinook cooked dry heat",
  "candidates": [
    {"fdc_id": 171999, "description": "Fish, salmon, chinook, cooked, dry heat", "data_type": "SR Legacy"}
  ],
  "source": "USDA FoodData Central"
}
```

(Illustrative; the real list comes from the captured fixture.) Descriptions and data types are copied character for character, in USDA's order. No nutrient values, scores or other fields.

### 7.3 MCP tool description (Phase 1B)

> Search USDA FoodData Central for one ingredient. Returns candidate foods with FDC ID, USDA's exact description and data type, and no nutrient values; call roli_get_usda_nutrition with the chosen FDC ID to get those. Searches SR Legacy and Foundation foods only. USDA matches words, not synonyms: use USDA wording (food, then species or variety, then preparation), e.g. "salmon chinook cooked dry heat", not "king salmon". Results are in USDA's order, and the first is not necessarily right. Pick the candidate whose description names the same food and preparation. If none does, search again with different words or say that no match was found. Never invent an FDC ID. Inputs: query (1–200 characters), limit (1–10, default 5).

## 8. Tool 2: get nutrition

### 8.1 Input

| Field | Rule | If broken |
|---|---|---|
| `fdc_id` | integer ≥ 1; booleans rejected | `invalid_input` |

### 8.2 Output: complete

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
  "nutrient_ids": {"saturated_fat_g": 1258, "cholesterol_mg": 1253},
  "source": "USDA FoodData Central"
}
```

### 8.3 Output: partial

Same fields. Each missing value is `null` and is listed in `missing_nutrients`, e.g. `"cholesterol_mg": null, "missing_nutrients": ["cholesterol_mg"]`.

`partial` means one **or both** values are missing; both missing is still `partial`. `nutrient_ids` is always the fixed mapping.

### 8.4 MCP tool description (Phase 1B)

> Returns saturated fat (g) and cholesterol (mg) per 100 g for exactly one USDA food, identified by FDC ID. The values belong only to the food named in "description" and the "fdc_id" in the same response; never pair them with another food or ID. null means USDA reports no value for that nutrient: never replace it with zero or an estimate. status is "complete", "partial" (one or both values missing) or "error" (no values; see error_code). SR Legacy and Foundation foods only.

## 9. Error output

One shape for every failure, returned as a normal result (and in Phase 1B as a normal tool result, not raised):

```json
{"status": "error", "fdc_id": 171999, "error_code": "not_found", "message": "USDA has no food with this FDC ID."}
```

Search errors carry `"query"` in place of `"fdc_id"`. Messages are fixed text owned by the service. They never contain USDA's raw text, a stack trace, a URL or the key.

| error_code | Trigger | Applies to |
|---|---|---|
| `invalid_input` | input breaks 7.1 or 8.1 | both |
| `not_found` | USDA 404 | get nutrition |
| `unsupported_data_type` | `dataType` not SR Legacy or Foundation (message names the type) | get nutrition |
| `id_mismatch` | reply `fdcId` ≠ requested ID | get nutrition |
| `validation_failed` | rules V8–V12; message names the rule (`id_number_mismatch`, `duplicate_nutrient`, `unit_mismatch`, `invalid_amount`) | get nutrition |
| `malformed_response` | not JSON, not an object, or missing or wrong-typed `fdcId`, `description`, `dataType`, `foodNutrients`/`foods` | both |
| `rate_limited` | USDA 429 | both |
| `usda_auth_failed` | USDA 403 | both |
| `usda_unavailable` | timeouts, connection errors, 5xx after retries, any other unexpected status | both |

## 10. Validation rules for get nutrition, applied in order

- V1. The body is a JSON object. Otherwise `malformed_response`.
- V2. `fdcId` is an integer and not a boolean. Otherwise `malformed_response`.
- V3. `fdcId` equals the requested ID. Otherwise `id_mismatch`.
- V4. `dataType` is `"SR Legacy"` or `"Foundation"`. Otherwise `unsupported_data_type`.
- V5. `description` is a non-empty string. It is returned unchanged. Otherwise `malformed_response`.
- V6. `foodNutrients` is a list. A missing key is `malformed_response`; an empty list means both values are missing.
- V7. Select rows by `row["nutrient"]["id"]` in {1258, 1253}. Skip rows with no `nutrient` object. Never read `row["id"]`.
- V8. A selected row's `nutrient.number`, compared as a string, must be `"606"` for 1258 and `"601"` for 1253. In the other direction, any row whose number is `"606"` or `"601"` must carry the matching ID. A mismatch either way is `validation_failed` (`id_number_mismatch`).
- V9. At most one row per target nutrient, even if two rows have the same amount. Otherwise `validation_failed` (`duplicate_nutrient`).
- V10. `unitName`, ignoring case, is `"g"` for 1258 and `"mg"` for 1253. Otherwise `validation_failed` (`unit_mismatch`).
- V11. A selected row with no `amount`, or `amount: null`, counts as missing: the value is `null` and the nutrient is listed in `missing_nutrients`.
- V12. `amount` is an int or float, not a boolean or string, finite and ≥ 0. Otherwise `validation_failed` (`invalid_amount`).
- V13. Zero is returned only when USDA's number is 0. A missing value never becomes 0.
- V14. The output value is `float(amount)`, with no rounding.
- V15. Every output field comes from this one reply. The function has no access to any other record.

## 11. Reliability and performance

- **Cache:** in memory, per process.
  - Get-nutrition key: `fdc_id`. Search key: (lower-cased trimmed query, limit).
  - TTL from `ROLI_CACHE_TTL_SECONDS`. At most `ROLI_CACHE_MAX_ENTRIES` entries; the least recently used is dropped first.
  - Store only `complete`, `partial` and search results. Never store errors.
  - On read, check the cached `fdc_id` equals the key. If not, drop the entry and fetch again.
- **Logs:** use Python `logging` with logger name `roli_nutrition`, one JSON line per call. Fields: `call`, `fdc_id` or `query`, `status`, `error_code`, `duration_ms`, `cache_hit`, `usda_requests`. Never log headers, keys or USDA bodies. Log fields never appear in results.
- **Targets** (measured, not guaranteed): get-nutrition result under 2 KB; cache hit under 50 ms; cache miss usually under 3 s.

## 12. Security

- Read `USDA_FDC_API_KEY` from the environment: loaded from `roli/.env` by entry points locally, host secrets in deployment.
- Phase 1B: the server requires `ROLI_MCP_TOKEN` and refuses to start if it is missing or shorter than 32 characters.
  - Every request to `/mcp` must carry `Authorization: Bearer <token>`. Compare with `hmac.compare_digest`.
  - Otherwise HTTP 401 before any tool code runs.
  - Use a small ASGI middleware, not the SDK's OAuth setup.
- USDA host fixed in code. Send USDA only food names and FDC IDs; never user images or health data.
- `.env.example` lists variable names with placeholder values. `.env` stays git-ignored (already true).

## 13. Fixtures and tests

### 13.1 Capturing real replies

The developer runs `scripts/capture_fixtures.py` once with the real key. It loads `roli/.env`, writes JSON bodies to `tests/fixtures/usda/` and a `manifest.json` recording, for each file: method and path with parameters (never the key), status, capture time, byte size and SHA-256. It does not save response headers. Captures:

1. `food_171999.json`: 5.3 request. This first call also confirms the `X-Api-Key` header; on 403 the script stops.
2. `food_172001.json`: 5.3 request.
3. `food_171999_unfiltered.json`, `food_172001_unfiltered.json`: `format=full` without `nutrients`.
4. `search_king_salmon.json`: 5.4 request, "king salmon cooked dry heat", pageSize 10.
5. `search_salmon_chinook.json`: "salmon chinook cooked dry heat", pageSize 10.
6. A Foundation animal food: search "salmon" (Foundation only, pageSize 5); save the search, then fetch the first result's detail (5.3) as `food_foundation_<id>.json`.
7. A Foundation plant food, expected to have no cholesterol row: the same steps with "broccoli raw".
8. A Branded food: search "salmon" (Branded only, pageSize 1); fetch its detail with `format=full&nutrients=606,601`.
9. Error replies, saved as `{status, body}`: 404 (`/food/99999999`), 400 (`/food/abc`), 403 (request without key).

About 15 calls in total. The script never prints the key and never writes it to disk.

After capture, the expected values for items 6–7 are read once from the files and typed into the tests, with a comment naming the file. Tests never compute expected values from the fixture under test. For 171999 and 172001, the expected values are fixed now: 3.214 g / 85.0 mg and 0.971 g / 55.0 mg.

### 13.2 Edited copies

Failure cases use `mutate(load("food_171999"), edit)` in `conftest.py`, which edits a deep copy of a real reply. No fixture is typed by hand.

### 13.3 Required tests, Phase 1A

- **A. Chinook.** `get_nutrition(171999)` returns `complete`, 3.214 g, 85.0 mg, exact description, `"SR Legacy"`, `nutrient_ids` {1258, 1253}.
- **B. Pink.** `get_nutrition(172001)` returns 0.971 g, 55.0 mg. Isolation:
  - 171999 never returns 0.971 or 55.
  - Calling 172001 then 171999, and the reverse, gives identical results, with or without the cache.
- **C. Search.**
  - Candidates equal USDA's `foods[]` (`fdc_id`, `description`, `data_type`) in the same order, with no nutrient fields.
  - The request body is exactly as in 5.4.
  - Whether 171999 appears for "king salmon cooked dry heat" is recorded, not asserted.
- **D. Missing.**
  - Cholesterol row removed: `partial`, `cholesterol_mg: null`, listed in `missing_nutrients`.
  - Row present with no `amount`: same result.
  - `foodNutrients: []`: both null, `partial`.
  - The real Foundation plant food checked against its actual rows.
- **E. ID mismatch.** `fdcId` edited to 172001 in the 171999 reply returns `id_mismatch` and no values.
- **F. Failures.**
  - `invalid_input` for 0, −1, True, 1.5 and "171999".
  - Saved 404 → `not_found`. 403 → `usda_auth_failed`.
  - 429 → `rate_limited` after exactly 1 request.
  - 503 three times → `usda_unavailable` after exactly 3 requests.
  - Timeout then 200 → success after 2 requests.
  - Non-JSON body → `malformed_response`.
  - The real Branded detail → `unsupported_data_type`.
  - V8, V9 (duplicate row), V10 (`"mg"` on saturated fat) and V12 (−1, `"3.2"`, True) → `validation_failed` naming the rule.
- **G. Shape and size.** Every result type has exactly the documented keys. Get-nutrition output is ≤ 2 KB as JSON. Search output with 10 candidates is ≤ 3 KB.
- **H. Request shape.**
  - Detail calls use exactly `format=full` and `nutrients=606,601`.
  - Search calls use POST with the 5.4 body.
  - The `X-Api-Key` header is present.
  - No URL contains `api_key`.
  - The only host contacted is `api.nal.usda.gov`.
- **I. Unfiltered equivalence.** The unfiltered 74-row and 116-row replies give the same outputs as the filtered ones (heading rows without `amount` are ignored).
- **J. Cache.**
  - A second call for the same ID makes 0 USDA requests.
  - Errors are not cached.
  - After the TTL passes (fake clock), USDA is called again.
  - A cache entry whose `fdc_id` differs from its key is dropped.
- **K. Secrets.** With a fake key such as `SENTINEL_KEY_123`, the key never appears in any log line (`caplog`), error message or result, in every failure test.
- **O. Core isolation.** In a fresh interpreter (subprocess), `import roli_nutrition; roli_nutrition.get_nutrition` leaves none of `mcp`, `langgraph`, `langchain`, `uvicorn` or `dotenv` in `sys.modules`.
- **P. Threads.** 20 threads calling `get_nutrition(171999)` and `get_nutrition(172001)` at once against the mock transport: every result is correct for its own ID.
- **Live, optional.** `ROLI_LIVE_TESTS=1` runs A and B against the real API.

### 13.4 Tests in Phase 1B

- **L. Discovery.** An MCP client over Streamable HTTP lists exactly two tools with the names, descriptions and input schemas above.
- **M. Calls.** Both tools called through MCP, with USDA replaced by the mock transport, return JSON equal to the service output. Calls do not block the event loop: each runs in a worker thread.
- **N. Auth.**
  - No token, a wrong token, or a token without `Bearer` returns 401, with no USDA request.
  - The right token works.
  - The server will not start without `ROLI_MCP_TOKEN`.

## 14. Phases and checkpoints

**Phase 0: done.** Julius has added `USDA_FDC_API_KEY` to `roli/.env`. The agent checks it exists without printing it.

**Phase 1A: core package and tests.**
1. `pyproject.toml`, `.venv`, `config.py`, `schemas.py`.
2. `usda_client.py`.
3. `nutrients.py`.
4. `service.py` with the cache and module-level functions.
5. `capture_fixtures.py`; run it.
6. Tests A–K, O, P, plus the live tests run once with `ROLI_LIVE_TESTS=1`.
7. `scripts/demo.py`: prints real results for 171999, 172001, the king salmon search, and three error cases (`not_found`, `id_mismatch`, `invalid_input`).

**Checkpoint 1A: stop and wait for Julius.** Write `nutrition_service/CHECKPOINT_1A.md` with:
- pass/fail counts and the full `pytest -v` output (also saved to `nutrition_service/test_report_1A.txt`)
- `demo.py` output, as the exact JSON
- the fixture manifest summary
- the observed king salmon and chinook candidate lists
- measured sizes and timings (cache miss, cache hit)
- every deviation from this spec, and open questions

**Phase 1B (after approval): MCP wrapper.**
- `mcp_server.py`: MCP SDK v2 `MCPServer` with two tools that call `NutritionService` in a worker thread; `streamable_http_app(stateless_http=True, json_response=True)` at `/mcp`; the bearer-token middleware.
- Tests L–N.
- Manual check with the MCP Inspector.

**Phase 1C: package.**
- Dockerfile (`python:3.13-slim`, non-root user, `PORT` env); pinned `requirements.txt`.
- README covering:
  - install, test and run locally
  - using the core from LangGraph (section 6)
  - a temporary public HTTPS link through Cloudflare Tunnel or ngrok for the first Agent Builder test
  - hosting options and their cold-start caveat
  - connecting in LangSmith: remote MCP server, URL `https://<host>/mcp`, header `Authorization: Bearer <ROLI_MCP_TOKEN>`
  - the SDK's DNS-rebinding protection when serving on localhost behind a tunnel
- No deployment, no change to either agent.

**Phase 2 (separate approval):**
- LangGraph imports `roli_nutrition` directly.
- The Agent Builder prototype connects to the MCP endpoint.

## 15. Later (not in this build)

- ~~Survey (FNDDS) foods, including foods cooked with added fat.~~ Done in v2.2 (section 17).
- Several FDC IDs per call (USDA `POST /foods` takes up to 20).
- `calculate_dish_nutrition`: ingredient FDC IDs plus assumed grams → per-ingredient values and a dish total, with source IDs and assumptions.
- A test set pairing menu wording with the correct FDC IDs, to measure record relevance.

## 16. Known limitations

- `null` means USDA reports no value. Foundation plant foods often have no cholesterol row, so a plant food can come back `partial`. Agents must not treat that `null` as zero.
- SR Legacy is a frozen 2018 dataset. Some values are calculated rather than measured: USDA marks 172001's values "Calculated or imputed".
- SR Legacy "cooked, dry heat" means cooked without added fat. Restaurant dishes cooked in butter or oil will contain more.
- The library checks that values belong to the food returned. It cannot check that the agent picked the right food.
- The cache is per process. LangGraph and the MCP server each keep their own.

## Definition of done

**Phase 1A:**
- Tests A–K, O and P pass, and the live tests pass once.
- `get_nutrition(171999)` returns exactly 3.214 g and 85.0 mg, and `get_nutrition(172001)` returns 0.971 g and 55.0 mg, each taken from its own record alone.
- `CHECKPOINT_1A.md` is written, and the agent stops.

**Phase 1 overall:**
- Phase 1A done, plus tests L–N.
- A local MCP client discovers and calls both tools through the token-protected `/mcp` endpoint.
- The package builds, and the README explains both the LangGraph import and the LangSmith connection.
- Nothing deployed; neither agent changed.

## 17. Revision 2.2 (2026-11-05, decided by Julius: "Use survey records")

- `dataType` "Survey (FNDDS)" is accepted by `get_nutrition`, `get_portions` and the new `get_inputs`. FNDDS nutrient values are per 100 g of the
  food as consumed (USDA FNDDS documentation), so the per-100 g basis holds. Branded and Experimental foods stay refused.
- `search_foods(query, limit, data_types=None)`: the default search is unchanged (Foundation + SR Legacy), so ingredient matching is unchanged;
  a caller may pass `["Survey (FNDDS)"]`. The cache key includes the table set. Only the three per-100 g tables are accepted.
- Survey `foodPortions` rows carry their words in `portionDescription` and no `amount`; the parser reads the description's leading number as the amount
  (else 1) and keeps the description as the label ("1 cup" = 135 g for olives; "1 small/regular fillet" = 140 g for fried cod).
- `get_inputs(fdc_id)` (`roli_nutrition/inputs.py`) returns a Survey food's `inputFoods` (description, USDA ingredient code, grams per 100 g of the
  finished food). SR Legacy and Foundation foods return an empty list. Read-only; no nutrient is touched.
- The filtered detail request (`nutrients=606,601`) is not honoured for Survey foods: USDA returns all rows. The parser already selects by nutrient id,
  so the values are the same; the reply is about 12 KB instead of 1.3 KB.
- Fixtures: `food_survey_*.json` (olives, fried fish, fries, calamari, chicken, onion rings), `search_survey_*.json`; tests in `tests/test_survey.py`.
- Why: Roli (Phase 3) needs cup weights SR Legacy lacks and the finished-food values of fried dishes, whose frying oil is never quantified by a recipe
  and never invented by Roli. The uses are in `roli_agent/recipes/survey.py`.


## 18. Revision 2.3 (2026-11-05, decided by Julius: "USDA access", SPEC_3_mvp.md section 12.5)

Why: on 2026-11-05 the day's reruns used most of the key's hourly allowance (3,600 requests per rolling hour, from USDA's own `x-ratelimit-limit`
header; the README's 1,000 was wrong), one run then made about 750 refused requests, and the refusals were read as incomplete recipes, which fetched
more recipes. Each new process also started with an empty cache and fetched every record again.

1. **Saved answers on disk** (`roli_nutrition/store.py`, `AnswerStore`). The raw JSON body of every successful food and search reply is saved under
   `Settings.store_dir` (`ROLI_USDA_STORE_DIR`; `None` keeps the in-memory-only behaviour of v2.2) with the time saved, the food's `dataType` and
   `publicationDate` as USDA states them, and the release label the store knew. Read order: memory cache, disk, USDA. A saved body is parsed by the same
   functions as a fresh one, so no number can come from anywhere but one USDA reply. Refused and failed replies are never saved (the service saves only
   after a successful parse). The three food calls (`get_nutrition`, `get_portions`, `get_inputs`) share one saved body, so a record costs one request
   instead of two. Writes are atomic and locked; a corrupt file reads as absent.
2. **Refusal.** After the first 429 the client refuses to send anything for `Settings.halt_seconds` (`ROLI_USDA_HALT_SECONDS`, default 3600; 0 disables):
   every uncached call returns `rate_limited` with `usda_requests` 0. `UsdaClient.reset_halt()` lifts it early (a person's decision). `requests_sent`
   counts the HTTP requests a client actually made.
3. **Allowance.** `x-ratelimit-limit` and `x-ratelimit-remaining` are read from every reply into `UsdaClient.allowance`; `NutritionService.usda_status()`
   reports limit, remaining, when observed, halted, requests sent, store hits and misses and the known release. `allowance_ok(reserve)` is False when
   halted or when the remaining count is at or under `Settings.reserve_requests` (`ROLI_USDA_RESERVE_REQUESTS`, default 200, the proposal of 12.5).
4. **Refresh by release.** `UsdaClient.list_foods(data_types, page_size=1, sort_by="publishedDate", sort_order="desc")` is `POST /foods/list`
   (`fdc_api.json`: `postFoodsList`, body `FoodListCriteria`, reply a list of `AbridgedFoodItem` with `publicationDate`). `NutritionService.check_release()`
   makes one such request per refreshable table (Foundation, Survey (FNDDS); SR Legacy is final, April 2019 publication, never refreshed) and compares
   the newest publication date with `release.json` in the store: first sight records it; a newer date is recorded as `pending_publication_date` and the
   live label is left as it was. Read live 2026-11-05: Foundation 2026-10-29, Survey 2024-10-31, SR Legacy 2019-04-01 (fixtures `list_*_newest.json`).
   Each saved answer records the release labels it was fetched under. `scripts/refresh_usda.py --stage` re-fetches the refreshable answers (or, with
   `--stale-only`, those older than `Settings.stale_months`, default 7, the safety net) into `staging/`, stopping at the reserve or the first refusal;
   `--promote --yes` snapshots the live answers to `snapshots/<time>/` and makes the staged ones live. The service never promotes on its own: new release
   data goes live only after Julius approves. Roli (the agent) calls `check_release()` at app start and once a day while it runs.
5. Unchanged: the core imports no MCP, LangGraph or LangChain; the MCP wrapper is untouched; Branded and Experimental foods stay refused.

Tests: `tests/test_store.py` (saved answers across a restart, search keys, nothing saved on failure, corrupt files, the halt, the headers and reserve,
release detection with fakes and the saved replies, staging and promotion, settings). Fixtures added by `scripts/capture_fixtures_3d.py`.

## 19. Revision 2.4 (2026-11-06, found at Checkpoint 3E)

`get_inputs` also returns `moisture_change_pct`, read from USDA's `foodAttributes` ("Moisture change: -15%"), and `InputsResult.grams_per_100g_scale`. USDA's `ingredientWeight`
is the recipe weight BEFORE cooking, not grams in 100 g of the finished food as section 17 said: finished mass = sum of inputs x (1 + moisture change / 100). Checked on the saved
records: "Fish, NS as to type, fried" (100.6 g of inputs, -15 %) gives its own 2.83 g saturated fat and 46 mg cholesterol; "Potato, french fries, from fresh, fried" (115.4 g, 0 %)
gives its own 1.76 g. The field `InputFood.grams_per_100g` keeps its name and now says so in its comment. Nothing else changes; read-only; no nutrient value is touched.

## 20. Revision 2.5 (2026-11-06, decided by Julius: SPEC_3_mvp.md 12.14.7)

1. `GET /food/{fdcId}` now asks for `nutrients=606,601,204`. Total fat (nutrient id 1004, number 204) is read with the same checks as the two tracked nutrients (V8-V12) and returned as `total_fat_g`. It is not a tracked nutrient: its absence never makes a result partial and it is never in `missing_nutrients`. A row with no amount is unknown, not zero.
2. `food_category` returns USDA's own category as the record states it: `foodCategory.description` (SR Legacy, Foundation) or `wweiaFoodCategory.wweiaFoodCategoryDescription` (Survey). The library does not interpret it.
3. Saved answers fetched before this revision hold no total fat. One is asked for again only when its saturated fat is missing, the one case that reads total fat; new entries record `request.nutrients`. This is the same record, not a refresh, so it needs no promotion. It stays subject to the allowance and to the stop at the first refusal.
4. What the two values are used for (saturated fat lies between 0 and total fat; a plant food has no cholesterol) belongs to the agent's inference layer. The library still returns only what one USDA record says.

