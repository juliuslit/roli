# Technical Specification: Phase 2A, Deterministic Recipe Nutrition Calculator

Status: **approved by Julius 2026-11-02 with decisions D1–D8 and four corrections (sections 5, 6, 8, 9, 12); implementation follows this text.** Companion to `SPEC.md` (the USDA library, Phases 1A–1D) and `roli_agent/CHECKPOINT_1E.md` (the LangGraph application).

## 0. One-paragraph summary

A pure-Python calculator takes a recipe (ingredients with grams and USDA FDC IDs, a serving count), fetches each ingredient's validated per-100 g saturated fat and cholesterol through the existing `roli_nutrition` library, multiplies grams/100 by the reference value with exact decimal arithmetic, and returns every intermediate number: per ingredient, per recipe, per serving. Completeness is tracked separately for each nutrient. Anything that cannot be computed (no FDC ID, no grams, USDA error, nutrient not reported, raw/cooked mismatch) makes that nutrient's total **incomplete**: the calculator returns a *known subtotal* clearly labelled as such, lists what is missing and why, and never presents the subtotal as the dish total. A small helper compares three manually supplied recipes and reports the min, median and max of the complete per-serving results as "the range across modeled recipes". The LLM does no arithmetic anywhere. LangGraph gets a node that runs the calculator on a structured recipe already in state and a deterministic reply template.

## 1. Objective and non-goals

**Goal.** Reliable, inspectable dish-level estimates from explicit inputs, so a reader can reconstruct every reported number from the output alone.

**Out of scope (Phase 2B):** finding recipes, extracting ingredients from text or web pages, converting cups and tablespoons to grams, cooking-yield or nutrient-retention factors, matching ingredient names to USDA records automatically, sensitivity analysis.

## 2. Where it lives (decision D1)

**Proposal:** a subpackage of the existing library, `nutrition_service/roli_nutrition/recipe/`, with modules `models.py` (input and output schemas), `calculator.py` (retrieval and arithmetic), `compare.py` (scenario comparison), `preparation.py` (raw/cooked classification of USDA descriptions). Tests go in `nutrition_service/tests/test_recipe_*.py`, run in the nutrition service's own venv with its saved USDA fixtures.

Why there and not a new package: the calculator consumes `NutritionResult` objects and nothing else from outside; the library already carries the per-100 g basis guarantee; LangGraph already installs the library in editable mode, so one `pip install -e nutrition_service` delivers both; the fixture and mock-transport infrastructure already exists. The MCP wrapper is not extended; the calculator is for LangGraph.

Alternative if you prefer separation: a top-level `roli_recipe/` package depending on `roli-nutrition`. Same code, one more package to install and version.

## 3. Input contract

Pydantic models, `extra="forbid"`, so a misspelled field is an error, not a silent drop.

```json
{
  "recipe_name": "Bluefin crudo, scenario A",
  "servings": 1,
  "ingredients": [
    {"name": "Bluefin tuna, raw", "fdc_id": 173706, "grams": "85", "preparation_state": "raw",
     "quantity_basis": "total_recipe", "assumption": "hypothetical: typical crudo portion"},
    {"name": "Bottarga", "fdc_id": null, "grams": "5", "preparation_state": "as_used",
     "quantity_basis": "total_recipe", "assumption": "no USDA record selected"},
    {"name": "Olive oil", "fdc_id": 171413, "grams": "10", "preparation_state": "as_used",
     "quantity_basis": "total_recipe", "assumption": "hypothetical: drizzle"}
  ]
}
```

| Field | Type and rule | If broken |
|---|---|---|
| `recipe_name` | string, 1–200 characters | input error |
| `servings` | positive number (integer or decimal, e.g. `1`, `4`, `1.5`); given as number or numeric string | input error |
| `ingredients` | list, 1–100 items | input error |
| `ingredients[].name` | string, 1–200 characters | input error |
| `ingredients[].fdc_id` | integer ≥ 1 (the library's rule), or `null` meaning *no USDA record chosen* | input error if present but invalid |
| `ingredients[].grams` | decimal ≥ 0 and finite, given as a numeric string or number; `null` means *unknown quantity* | input error if negative, infinite or not numeric |
| `ingredients[].preparation_state` | `raw`, `cooked`, `as_used`, `unknown` | input error |
| `ingredients[].quantity_basis` | `total_recipe` (default) or `per_serving` | input error |
| `ingredients[].assumption` | free text or `null`: where the grams came from | none |
| `ingredients[].ingredient_id` | optional string the caller may use to tell duplicates apart; generated as `ing_01`, `ing_02`, … when absent | none |

Rules behind the table:
- **Grams as strings.** JSON numbers are floats; `"85"` or `"0.5"` keeps the exact decimal. Plain numbers are accepted and converted through `str()`, which preserves what was typed.
- **Explicit zero is not unknown.** `grams: "0"` contributes zero and is marked `explicit_zero`; `grams: null` is `missing_grams` and makes the nutrient totals incomplete.
- **`per_serving` quantities** are multiplied by `servings` to get the recipe quantity before any arithmetic, and the conversion is recorded in the output (decision D3).
- **Input errors** (a negative quantity, zero servings, an unknown state) stop the calculation and return a single `invalid_recipe` result naming every problem; nothing is computed from a partly invalid recipe.

## 4. USDA retrieval

For every distinct `fdc_id` in the recipe, once: `NutritionService.get_nutrition(fdc_id)` from the existing library (its cache also dedupes across recipes in the same process). The result is stored verbatim with the ingredient: FDC ID, USDA description, data type, per-100 g values, `missing_nutrients`, or the library's `ErrorResult`. Nothing is substituted: if 173706 fails, the bluefin line is unresolved, and no other tuna record is tried.

The calculator takes the service as a constructor argument (`RecipeCalculator(service)`), so tests inject the fixture-backed service exactly as Phase 1E tests do.

## 5. Preparation-state compatibility (decision D2)

The USDA record's own state is read **deterministically from its description** by `preparation.py`:

| Description contains (case-insensitive, whole words) | Record state |
|---|---|
| `raw` | `raw` |
| `cooked`, `dry heat`, `moist heat`, `roasted`, `baked`, `boiled`, `grilled`, `broiled`, `fried`, `braised`, `steamed`, `toasted` (for seeds/bread) | `cooked` |
| neither, or both | `unknown` |

Compatibility of ingredient state × record state:

| Ingredient says | Record is `raw` | Record is `cooked` | Record `unknown` |
|---|---|---|---|
| `raw` | compatible | **mismatch** | unresolved_state |
| `cooked` | **mismatch** | compatible | unresolved_state |
| `as_used` (oils, cheeses, condiments: the weight is the weight) | compatible | compatible | compatible |
| `unknown` | unresolved_state | unresolved_state | unresolved_state |

`mismatch` and `unresolved_state` both make the ingredient **unresolved**: it is listed with its name, grams, the USDA record that was fetched (if any) and the reason, its `contribution` is `null` (D8: a number for an incompatible pairing would read as a valid contribution, so none is shown), and it is excluded from known subtotals, making both nutrient totals incomplete. Issue codes: `preparation_mismatch`, `preparation_unresolved`. No yield factor is ever applied.

**`as_used` is not a blanket workaround (D2).** It is for ingredients whose weight is their weight regardless of cooking: oils, cheeses, condiments, seeds, bread. For flesh foods it is refused: when the USDA description's first word is one of `Fish`, `Beef`, `Pork`, `Chicken`, `Turkey`, `Lamb`, `Veal`, `Game meat`, `Duck`, `Goose`, `Crustaceans`, `Mollusks`, `Egg`, an `as_used` ingredient is treated as `unresolved` with issue `as_used_not_accepted_for_flesh`, and the message says to declare `raw` or `cooked`.

The keyword table is the weak point of this rule and is listed as D2 because a wrong classification silently changes compatibility. Each keyword decision is unit-tested against the real descriptions in our fixtures (e.g. "Fish, salmon, chinook, cooked, dry heat" → cooked; "Fish, tuna, fresh, bluefin, raw" → raw; "Cheese, romano" → unknown, which is why cheeses are declared `as_used`; "Oil, olive, salad or cooking" → unknown, since "cooking" is not the whole word "cooked").

## 6. Arithmetic

All arithmetic in `decimal.Decimal` with a context of 28 significant digits (Python's default), no float anywhere after input parsing:

```text
reference = Decimal(str(usda_value_per_100g))          # 3.214 -> Decimal("3.214"), exact
contribution = grams * reference / Decimal(100)         # Decimal("150") * Decimal("3.214") / 100 = Decimal("4.821")
recipe_total = sum(contributions of resolved ingredients)
per_serving = recipe_total / servings
```

Acceptance example (section 9, test T4): 150 g of 171999, one serving → saturated fat `4.821` g exactly, cholesterol `127.5` mg exactly.

Values are serialised as **strings of the exact Decimal** (`"4.821"`, `"127.5"`) in the JSON output, plus a `display` block rounded for people (D4). Internal precision is never rounded.

**Two levels of exactness (correction 1).** Contributions and recipe subtotals are exact: multiplying by a decimal reference and dividing by 100 cannot produce a recurring decimal, so `sum(contributions of resolved ingredients) == known_subtotal` is asserted with exact equality. Per-serving values can recur (1 ÷ 3), so they are **quantized to six decimal places, round-half-even**, the output states `per_serving_precision: "6 decimal places"`, and the reconciliation rule is `|per_serving × servings − recipe_total| ≤ 0.0000005 × servings`. Both checks run inside the calculator before it returns; a violation is a bug and raises.

**Display rounding (D4):** saturated fat to 2 decimal places, cholesterol to whole milligrams, round-half-up. A value that is greater than zero but would round to zero is shown as `<0.01 g` or `<1 mg`, never as `0`. An exact zero is shown as `0`.

## 7. Completeness, per nutrient

Tracked separately for saturated fat and cholesterol, because USDA often reports one and not the other (Foundation plant records in Phase 1D had fat but no cholesterol row).

**What `complete` means (correction 3):** every ingredient *in the supplied list* was calculated from a validated USDA record with the supplied grams. It is completeness of the arithmetic over the caller's recipe, not verification that the list or the weights match the restaurant's actual dish. Every estimate is conditional on the supplied ingredients and quantities, and the output says so in `completeness_note`.

A nutrient's recipe total is **complete** when every ingredient is *resolved for that nutrient*: it has an FDC ID whose lookup succeeded, non-null grams, a compatible preparation state, and a non-null USDA value for that nutrient. Ingredients with `grams: "0"` count as resolved for both nutrients with a contribution of exactly zero, flagged `explicit_zero`, whatever their USDA status (zero grams of anything contributes nothing).

Otherwise the nutrient is **incomplete**:
- `total` is `null`;
- `known_subtotal` holds the sum over resolved ingredients, with `covers` listing which ingredients it includes and `excludes` listing which it does not, each with a reason code;
- the display text says "at least X from N of M ingredients; missing: …", never "X".

Reason codes: `missing_fdc_id`, `missing_grams`, `usda_error:<library error_code>`, `nutrient_not_reported`, `preparation_mismatch`, `preparation_unresolved`. Informational flags that do not affect completeness: `explicit_zero`, `per_serving_quantity_converted`, `duplicate_fdc_id` (two ingredient lines share a record; both counted, as declared).

## 8. Output contract

Bluefin Crudo, hypothetical weights, one serving. Real USDA references: 173706 bluefin raw 1.257 g / 38 mg per 100 g; 171413 olive oil 13.808 g / 0 mg per 100 g. Contributions: tuna 85 g → 1.06845 g and 32.3 mg; olive oil 10 g → 1.3808 g and 0 mg; bottarga has no record. Known subtotals: 1.06845 + 1.3808 = **2.44925 g**; 32.3 + 0 = **32.3 mg**. Both reconcile with `covers`.

```json
{
  "status": "incomplete",
  "recipe_name": "Bluefin crudo, scenario A (hypothetical weights)",
  "servings": "1",
  "calculator_version": "2a.1",
  "source": "USDA FoodData Central",
  "per_serving_precision": "6 decimal places",
  "completeness_note": "complete = every supplied ingredient was calculated from a validated USDA record with the supplied grams; it does not verify that the list or weights match the restaurant's dish",
  "ingredients": [
    {"ingredient_id": "ing_01", "name": "Bluefin tuna, raw", "grams_declared": "85", "quantity_basis": "total_recipe",
     "grams_in_recipe": "85", "preparation_state": "raw", "assumption": "hypothetical: typical crudo portion",
     "usda": {"fdc_id": 173706, "description": "Fish, tuna, fresh, bluefin, raw", "data_type": "SR Legacy",
              "saturated_fat_g_per_100g": "1.257", "cholesterol_mg_per_100g": "38", "record_state": "raw"},
     "usda_error": null, "compatibility": "compatible",
     "contribution": {"saturated_fat_g": "1.06845", "cholesterol_mg": "32.3"},
     "resolved": {"saturated_fat_g": true, "cholesterol_mg": true}, "issues": []},
    {"ingredient_id": "ing_02", "name": "Bottarga", "grams_declared": "5", "quantity_basis": "total_recipe",
     "grams_in_recipe": "5", "preparation_state": "as_used", "assumption": "no USDA record selected",
     "usda": null, "usda_error": null, "compatibility": "not_applicable",
     "contribution": {"saturated_fat_g": null, "cholesterol_mg": null},
     "resolved": {"saturated_fat_g": false, "cholesterol_mg": false}, "issues": ["missing_fdc_id"]},
    {"ingredient_id": "ing_03", "name": "Olive oil", "grams_declared": "10", "quantity_basis": "total_recipe",
     "grams_in_recipe": "10", "preparation_state": "as_used", "assumption": "hypothetical: drizzle",
     "usda": {"fdc_id": 171413, "description": "Oil, olive, salad or cooking", "data_type": "SR Legacy",
              "saturated_fat_g_per_100g": "13.808", "cholesterol_mg_per_100g": "0", "record_state": "unknown"},
     "usda_error": null, "compatibility": "compatible",
     "contribution": {"saturated_fat_g": "1.3808", "cholesterol_mg": "0"},
     "resolved": {"saturated_fat_g": true, "cholesterol_mg": true}, "issues": []}
  ],
  "totals": {
    "saturated_fat_g": {"complete": false, "total": null, "known_subtotal": "2.44925",
                        "covers": ["ing_01", "ing_03"], "excludes": [{"ingredient_id": "ing_02", "name": "Bottarga", "reason": "missing_fdc_id"}]},
    "cholesterol_mg":  {"complete": false, "total": null, "known_subtotal": "32.3",
                        "covers": ["ing_01", "ing_03"], "excludes": [{"ingredient_id": "ing_02", "name": "Bottarga", "reason": "missing_fdc_id"}]}
  },
  "per_serving": {
    "saturated_fat_g": {"complete": false, "total": null, "known_subtotal": "2.449250", "covers": ["ing_01", "ing_03"],
                        "excludes": [{"ingredient_id": "ing_02", "name": "Bottarga", "reason": "missing_fdc_id"}]},
    "cholesterol_mg":  {"complete": false, "total": null, "known_subtotal": "32.300000", "covers": ["ing_01", "ing_03"],
                        "excludes": [{"ingredient_id": "ing_02", "name": "Bottarga", "reason": "missing_fdc_id"}]}
  },
  "issues": [{"ingredient_id": "ing_02", "code": "missing_fdc_id", "message": "Bottarga has no USDA record; its contribution is unknown and not included."}],
  "display": {"saturated_fat_g": "at least 2.45 g per serving from 2 of 3 ingredients; missing: Bottarga",
              "cholesterol_mg": "at least 32 mg per serving from 2 of 3 ingredients; missing: Bottarga"}
}
```

Everything needed to recompute any number is present: declared grams, basis conversion, the per-100 g reference, the contribution, which contributions were summed, and the serving count. This exact example is test T18b: the calculator's output for these inputs must equal this JSON.

## 9. Scenario comparison

`compare_scenarios([result_a, result_b, result_c], basis="per_serving")` keeps the individual results unchanged and adds, per nutrient:

```json
{"saturated_fat_g": {"n_scenarios": 3, "n_complete": 2, "values": {"A": "4.1", "C": "5.1"},
                     "min": "4.1", "median": "4.6", "max": "5.1", "range_meaningful": true,
                     "excluded": [{"recipe_name": "B", "reason": "incomplete"}],
                     "note": "Range across the 2 modeled recipes that were complete for this nutrient. It describes the supplied recipes only: not a statistical confidence interval and not a guaranteed range for the restaurant's dish."}}
```

Rules (correction 4): only scenarios complete for that nutrient enter `values`, `min`, `median`, `max`; `n_complete` is reported; invalid or incomplete scenarios are listed under `excluded` with the reason. **Fewer than two complete scenarios → `range_meaningful: false`** and the note says the evidence is insufficient for a range (the single value, if any, is still listed). All scenarios must share the serving basis (`per_serving`, or `totals` only when every recipe has the same `servings`), otherwise an input error. Median is the exact Decimal median (mean of the two middle values for an even count). The words "confidence interval" never appear in any output.

## 10. LangGraph integration (after the standalone tests pass)

- **Input.** `run_roli(text="", photo_path=None, recipe=<dict or RecipeInput>)` and the state gains `recipe`, `recipe_result`, `recipe_error`. Phase 2A does **not** extract recipes from text or menus; the recipe is supplied programmatically (decision D5).
- **Graph.** `route_input` sends a request with `recipe` to a new `calculate_recipe` node (Python: validate, run the calculator) and then to `compose`. No LLM call on this path.
- **Reply.** Deterministic template: the ingredient table (grams, USDA record, contribution), then totals **or** known subtotals with the missing list, then per serving, then the assumptions line by line. The complete/incomplete status is the first line. `numbers_allowed` is set true only by this node or by `fetch_nutrition`.
- **Tests.** Graph-level tests mirror the calculator tests through `run_roli`, including the bottarga case: the reply must contain "missing: Bottarga" and must not contain a sentence of the form "contains X g".

## 11. Tests (standalone, in `nutrition_service/tests/`)

| # | Test | Fixtures |
|---|---|---|
| T1 | single ingredient, complete | 171999 |
| T2 | multiple ingredients, complete, totals reconcile to the sum of contributions | 171999, 170457, 172675 |
| T3 | four servings: recipe total ÷ 4, both totals present | 171999 |
| T4 | **150 g Chinook, one serving → exactly `4.821` g and `127.5` mg** | 171999 |
| T5 | oil and dressing contributions (`as_used` with an `unknown`-state record) | olive oil 171413, tahini 170189 |
| T6 | ingredient without FDC ID → incomplete, known subtotal, listed as missing | any |
| T7 | nutrient not reported → that nutrient incomplete, the other complete | broccoli 747447 (Foundation, no cholesterol row), green leaf lettuce 169249 |
| T8 | Foundation plant record with partial coverage inside a mixed recipe | 747447 + 171999 |
| T9 | raw grams on a cooked record → `preparation_mismatch`, excluded, both totals incomplete | 171999 declared `raw` |
| T10 | cooked grams on a raw record → mismatch | 173706 declared `cooked` |
| T11 | `unknown` ingredient state, and a record whose description has no state keyword with a `raw` claim → `preparation_unresolved` | 171249 romano |
| T12 | invalid amounts and servings: negative grams, `NaN`, `inf`, servings 0 or negative, 101 ingredients → `invalid_recipe` with every problem named | none |
| T13 | duplicate FDC IDs in two lines → both counted, one USDA request | 171999 ×2 |
| T14 | USDA failures: 503 ×3, 429, 404, mismatched ID, malformed body → `usda_error:*`, excluded, no substitution | library's error fixtures |
| T15 | reconciliation: sum(contributions) == known_subtotal; per_serving × servings == total, for every test recipe | all |
| T16 | distinct completeness: a recipe complete for fat and incomplete for cholesterol | 747447 + 171999 |
| T17 | three manually supplied scenarios with different per-serving results → min, median, max over the complete ones; the incomplete one excluded and named | 173706, 171413, 170189, 171249 |
| T18 | **Bluefin Crudo (hypothetical weights, labelled):** 85 g bluefin raw (173706), 5 g bottarga (no USDA record), 10 g olive oil (171413) → incomplete; known subtotals; "Bottarga" in the missing list; reply never states a dish total | as listed |
| T19 | **Little Gem Lettuces (hypothetical weights):** 80 g green leaf lettuce (169249), 25 g tahini (170189), 10 g romano (171249, `as_used`), 5 g toasted sesame (170151) → complete; per-ingredient contributions shown | as listed |
| T20 | `per_serving` quantity basis converted and flagged | 171999 |
| T21 | explicit zero grams counted as resolved and flagged `explicit_zero`; `null` grams → `missing_grams` | 171999 |
| T22 | preparation classifier against every fixture description | all food fixtures |
| T23 | output JSON round-trips through the Pydantic models with `extra="forbid"` | any |
| T24 | recurring decimals: 1 g total over 3 servings → per serving `0.333333`, reconciliation within tolerance; a 1 ÷ 7 case | 171999 scaled |
| T25 | the section 8 Bluefin Crudo JSON is reproduced exactly by the calculator | 173706, 171413 |
| T26 | unresolved ingredients carry `contribution: null` for both nutrients in every unresolved case (no ID, no grams, USDA error, mismatch, unresolved state, `as_used` on fish) | several |
| T27 | display rounding: `0.004` g shows `<0.01 g`, `0.4` mg shows `<1 mg`, exact `0` shows `0` | synthetic via scaled grams |
| T28 | comparison with one complete scenario → `range_meaningful: false`; with none → values empty, note says insufficient | any |

**Fixtures captured 2026-11-02** by `scripts/capture_recipe_fixtures.py` (9 USDA calls, D6; manifest now 24 files): 173706 bluefin raw, 170189 tahini, 171249 romano, 170151 sesame toasted, 169249 green leaf lettuce, 170457 tomatoes, 172675 bread, and olive oil (171413 "Oil, olive, salad or cooking", to be verified by search before capture). Expected values are typed into `captured_expectations.py` after reading the files once, as in Phase 1A.

## 12. Decisions (all taken 2026-11-02)

| # | Decision | Proposal |
|---|---|---|
| D1 | Location: subpackage `roli_nutrition.recipe` vs new top-level package | subpackage (section 2) |
| D2 | Preparation state of a USDA record read from its description with a keyword table; mismatched or unresolved ingredients excluded from subtotals | **decided**: yes; `as_used` only for oils, cheeses, condiments, seeds, bread; refused for flesh foods (section 5) |
| D3 | Accept `quantity_basis: per_serving` and convert, or require `total_recipe` only | accept both, record the conversion |
| D4 | Display rounding | **decided**: 2 decimals (g), whole mg, half-up; a positive value that would round to zero shows as `<0.01 g` / `<1 mg` |
| D5 | LangGraph integration takes a structured recipe supplied by the caller; no LLM extraction in 2A | yes |
| D6 | Capture about 8 more real USDA fixtures for the recipe tests | yes |
| D7 | Non-integer servings allowed (e.g. 1.5) | yes, any positive number |
| D8 | Per-ingredient contributions of *unresolved* ingredients | **decided: `null`**; show name, grams, the USDA record if fetched, and the reason; never a number that could read as a valid contribution |

## 13. Implementation plan

1. Extend `capture_fixtures.py` for the recipe records; run once; type expected values (D6).
2. `recipe/models.py` and `recipe/preparation.py` with their tests (T12, T22, T23).
3. `recipe/calculator.py`: retrieval, arithmetic, completeness, reconciliation; tests T1–T16, T18–T21.
4. `recipe/compare.py`; T17.
5. Full nutrition-service suite green; update its README with a calculator section and an example.
6. LangGraph: state fields, `calculate_recipe` node, reply template, graph tests incl. the bottarga reply; full agent suite green.
7. `CHECKPOINT_2A.md` with the ten items you listed, then stop.

Nothing in `code/`, the MCP wrapper, or the LangSmith prototype changes. No deployment.
