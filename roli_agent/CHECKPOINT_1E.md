# Checkpoint 1E: LangGraph integration and failure handling

Date: 2026-11-02. Status: **Phase 1E complete; stopped for review. Phase 2A not started.**

## 1. Summary

| Item | Result |
|---|---|
| Starting point | no LangGraph application existed; `code/` is the menu-reader evaluation harness |
| Built | `roli_agent/`, the first LangGraph application: a 7-node graph with two input paths |
| Offline tests | **27 passed**, 4 skipped (live), 0 failed; no network, saved real USDA replies, scripted LLM |
| Live tests (Gemini 3.8 Flash via OpenRouter + real USDA) | **4 passed**: Chinook 5.3 s, Pink 4.0 s, King salmon → Chinook 3.5 s, menu photo 10.4 s |
| Nutrition numbers in replies | written only by Python from a validated `roli_nutrition` result; the LLM has no path to them |
| USDA failure handling | every failure class tested; replies state unavailability and contain no nutrition number |
| Infrastructure needed to run | none beyond the root `.venv`: no MCP server, no tunnel, no LangSmith Agent Builder; LangSmith tracing optional |
| Changes outside `roli_agent/` | root `requirements.txt`, new root `pytest.ini`, the project notes current-stage text; `code/` and `nutrition_service/` unchanged |

## 2. Architecture, in plain language

```text
START → route_input ─┬─ text ──→ interpret ─┬─ food_lookup → search_usda ─┬─ ok → select_record ─┬─ resolved → fetch_nutrition → compose → END
                     │                      └─ other / unclear ──────────┐ └─ error ─────────────┘└─ unresolved ─────────────────┘
                     └─ photo → read_menu ───────────────────────────────┴──────────────────────────────────────────────→ compose
```

Who does what:

| Node | Who | Does |
|---|---|---|
| `route_input` | Python | photo → menu path; text → interpretation. Sets every nutrition slot to empty and `numbers_allowed = False` |
| `interpret` | LLM | turns the message into `{intent, food, usda_query, preparation}` as JSON. Unparsable → intent `unclear` |
| `search_usda` | Python | `service.search_foods(usda_query, 10)` from `roli_nutrition`; an `ErrorResult` goes to `search_error` |
| `select_record` | LLM, then Python | the LLM picks one FDC ID from USDA's candidate list; Python accepts it **only if it is in that list**. Anything else (an ID from memory, a string, `true`) is rejected and the request ends unresolved |
| `fetch_nutrition` | Python | `service.get_nutrition(fdc_id)`; a `NutritionResult` sets `numbers_allowed = True`; an `ErrorResult` goes to `nutrition_error` |
| `read_menu` | LLM | the harness's v5 menu prompt plus the photo → the answer-format JSON (readable, problems, items) |
| `compose` | Python | the one place a reply is built; failures first, numbers last, from templates in `responses.py` |

State (`state.py`) keeps the search result, the selected ID, the validated nutrition result, the missing-nutrient list, the error objects and the `numbers_allowed` flag in separate slots. An error is never a result: `nutrition` is `None` whenever `nutrition_error` is set, and a failed request can never look like a zero-nutrient food.

Why this prevents the Phase 1D failure: in Agent Builder the model wrote the final text and chose its sources, so when the tools failed it went to the web and labelled the numbers USDA. Here the model never writes the reply. The only numbers `compose` can print are fields of a `NutritionResult` that the library validated against the record with the requested FDC ID. There is no web-search node, no "general knowledge" branch, and no string from the LLM reaches the reply except the food name it extracted and its one-sentence selection reason.

Reuse from the harness (`harness.py`): OpenRouter URL and key, temperature 0, per-model provider order, no-training providers only, reasoning setting, the token cap and long timeout for menu reading, and the v5 menu prompt file. `code/` is imported, not copied, and not modified. Interpretation and selection calls use a 60 s timeout and a 1,000-token cap (`config.py`), since a person is waiting.

## 3. Files

Created: `roli_agent/__init__.py`, `__main__.py` (CLI), `config.py`, `harness.py`, `llm.py`, `state.py`, `prompts.py`, `nodes.py`, `responses.py`, `graph.py`, `tests/conftest.py`, `tests/test_food_path.py`, `tests/test_failures.py`, `tests/test_menu_path.py`, `tests/test_live.py`, `test_report_1E.txt`, this file; root `pytest.ini`.

Modified: root `requirements.txt` (added `langgraph`, `pytest`, `-e ./nutrition_service`), the project notes (current stage and next steps). Installed into the root `.venv`: langgraph 1.2.19, pytest 9.2.0, roli-nutrition (editable).

Unchanged: everything under `code/`, `nutrition_service/`, `menu_reader_eval/`, `menu_test_set/`, `results/`.

## 4. Test results

Offline, from the repo root (`.venv/bin/python -m pytest -v`; full output in `test_report_1E.txt`): 27 passed, 4 skipped.

| File | Covers |
|---|---|
| `test_food_path.py` (6) | Chinook 171999 → 3.214 g / 85 mg with the exact reply text; Pink 172001 → 0.971 g / 55 mg, no rounding; King salmon query whose USDA list puts king mackerel first → Chinook chosen, mackerel absent from the reply; two lookups on one graph keep their values with their own IDs; a partial record says "not reported by USDA", never 0; intent `other` makes no USDA call |
| `test_failures.py` (17) | timeout ×3, 429, 404, mismatched ID, duplicate-row validation failure, unreadable USDA body; search itself failing (503 ×3, connection refused, 429, 403) with no selection attempt; LLM declines all candidates; LLM proposes an ID outside the list (rejected, never looked up); LLM proposes `true` or a string; no candidates; unparsable interpretation containing the LLM's own figure, which never reaches the user; 201-character query → `invalid_input`; a failed run followed by a good one on the same graph |
| `test_menu_path.py` (4) | photo 03 through the reader (answer key as the scripted output): 18 dishes listed with ingredients and prices, cookbook line excluded, no USDA call, no nutrition-looking number; `partly` readability carried into the reply; unreadable reader output reported, not invented; missing photo file reported before any LLM call |
| `test_live.py` (4, `ROLI_LIVE_TESTS=1`) | the three salmon questions and the menu photo against the real model and USDA |

Every failure test asserts: `numbers_allowed` is not true, `nutrition` is `None`, the reply has no digit except FDC IDs, no "g" or "mg" wording, and the sentence "Roli does not estimate them from other sources". USDA is the saved real replies from Phase 1A through an httpx mock transport; the LLM is a queue of scripted JSON answers, so every path is deterministic.

## 5. Example: successful lookup (live, CLI, 4.3 s)

```text
$ .venv/bin/python -m roli_agent "What are the saturated fat and cholesterol of cooked chinook salmon?" --trace
Food: Fish, salmon, chinook, cooked, dry heat
USDA FoodData Central record 171999 (SR Legacy), values per 100 g:
- Saturated fat: 3.214 g
- Cholesterol: 85 mg
Source: USDA FoodData Central.

--- trace ---
route: text only -> interpret
interpret: food='cooked chinook salmon' query='salmon chinook cooked dry heat'
search: 10 candidates for 'salmon chinook cooked dry heat'
select: 171999 (Matches the specific species of chinook salmon and the specified cooked preparation state.)
fetch: complete for 171999
compose: done
```

Live King salmon (3.5 s): Gemini wrote the query as `fish salmon chinook cooked dry heat` and chose 171999 with the reason "Chinook salmon is another common name for King salmon". Pink (4.0 s): 172001, 0.971 g, 55 mg.

## 6. Example: USDA failure (live, CLI, 2.0 s)

Produced by running the same question with an invalid USDA key in that process only, so USDA answered 403:

```text
Verified nutrition information for cooked chinook salmon is unavailable: USDA rejected Roli's access key. No nutrition values are given; Roli does not estimate them from other sources.

--- trace ---
route: text only -> interpret
interpret: food='cooked chinook salmon' query='fish salmon chinook cooked dry heat'
search: error usda_auth_failed
compose: done
```

The selection step never ran, the LLM was called once, and the reply carries no number. The same template serves timeouts ("USDA FoodData Central could not be reached"), 429 ("USDA's hourly request limit was reached"), mismatched IDs ("USDA returned a different record than the one requested, so its values were discarded") and the other codes, each tested offline.

Partial record (offline test): "- Cholesterol: not reported by USDA for this record" followed by "A value USDA does not report is unknown, not zero."

## 7. Example: menu photo (live, 10.4 s)

Photo 03 (Flour + Water), "Hey, what should I order?": the reader returned 19 items, `readable: yes`; the reply lists 18 dishes by section with their printed ingredients and prices (the cookbook line is category `other` and is left out), then: "Nutrition for whole dishes is not available yet: Roli does not estimate ingredient weights, and USDA values describe single foods, not restaurant dishes. Ask about one food for verified USDA values." No USDA call is made on this path and no number other than prices appears. The structured items stay in `state["menu"]` for Phase 2A.

## 8. Confirmation of independence

Running `roli_agent` needs: the root `.venv`, `OPENROUTER_API_KEY` and `USDA_FDC_API_KEY` in `roli/.env`. It does not start or call the MCP server, does not need a public hostname, and does not use the LangSmith Agent Builder connection. LangSmith tracing happens only if `LANGSMITH_TRACING` is set in the environment; nothing in the graph imports or requires it.

## 9. Deviations and decisions to confirm

1. **Interpretation and selection calls use a 60 s timeout and a 1,000-token cap**, not the harness's 180 s and 24,000. Menu reading keeps the harness values. Both are in `config.py`.
2. **The interpretation prompt tells the model USDA's naming conventions**, including "king salmon is chinook salmon" and "baked, grilled or broiled fish is cooked dry heat". This is guidance for forming the query; the record selection is still checked against USDA's list.
3. **Whole dishes count as intent `other`.** "Dragon fruit tacos with unicorn cheese" live → the model classified it as a dish, and Roli explained what it can do. Single-food questions only, per the scope decision.
4. **`numbers_allowed` is set by code, not by the LLM**, and only in `fetch_nutrition`. A partial record sets it to true as well; the template prints "not reported" for the missing nutrient.
5. **Menu replies show prices.** They are printed digits from the menu, not nutrition values; the tests check for nutrition-shaped numbers (`<number> g|mg`) only.
6. **`harness.py` adds `code/` to `sys.path`** so the harness's `config` and `menu_reader` modules can be imported by their bare names. It is the one slightly unusual piece of plumbing; the alternative was copying about 40 lines of settings.
7. **Selection reasons are kept in the trace only** (adjusted 2026-11-02 on Julius's review). User-facing wording for an unresolved selection is fixed Python text: "none matches it (no candidate names the same food and preparation)" or "(the proposed record was not among USDA's results)". The LLM's one-sentence reason is recorded in `state["trace"]` for debugging and never shown to the user. The only LLM text that reaches a reply is the food name it extracted.

## 10. Limitations and risks

- **One record per question.** Several foods in one message, or a dish, get the "name one food" reply. Multi-ingredient handling is Phase 2A.
- **Record relevance still rests on the LLM's choice** among USDA's candidates. Integrity is enforced; relevance is not measured yet. The relevance test set from CHECKPOINT_1D remains the way to measure it.
- **Menu reading quality is the harness's**: the same v5 prompt and model, about 96% of dishes found in round one. A misread dish name is passed through as read.
- **Latency 3.5 to 5.3 s** for a food question (two model calls plus USDA), 10 s for a menu photo. The nutrition service's cache makes repeat lookups free within a process.
- **No conversation memory.** Each call is independent; follow-up questions ("and raw?") are not understood.
- **`ROLI_MODEL` is honoured, but only Gemini 3.8 Flash has been tested** in this graph.

**Stopped here. Phase 2A (deterministic recipe calculator) starts only after your approval, with its own specification first, as agreed.**
