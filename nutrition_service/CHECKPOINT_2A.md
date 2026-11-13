# Checkpoint 2A: deterministic recipe nutrition calculator

Date: 2026-11-02. Spec: `SPEC_2A_recipe_calculator.md` (decisions D1–D8 and four corrections applied before coding). Status: **Phase 2A complete; stopped for review. Phase 2B not started.**

## 1. Summary

| Item | Result |
|---|---|
| Standalone calculator | `roli_nutrition.recipe`: models, preparation classifier, calculator, scenario comparison; pure Python, Decimal arithmetic, no LLM |
| Nutrition-service suite | **292 passed**, 4 skipped (live); 85 of them are the new recipe tests (T1–T28 plus extras) |
| LangGraph suite | **31 passed**, 4 skipped (live); 4 new recipe-path tests |
| Acceptance case | 150 g Chinook, one serving → exactly `4.821` g saturated fat and `127.5` mg cholesterol, computed by Python |
| Spec example | the corrected Bluefin Crudo JSON in spec section 8 is reproduced byte for byte by the calculator (test T25) |
| Bottarga guard | declared but unmatched ingredient → `incomplete`, `null` contribution, named in both nutrient displays, no dish total anywhere |
| Live LangGraph run | `run_roli(recipe=...)` through the CLI against the real USDA API: 0.8 s, no LLM call |
| New real fixtures | 8 USDA records captured (olive oil, bluefin, tahini, romano, sesame, green leaf lettuce, tomatoes, bread); manifest now 24 files |
| Unchanged | `code/`, the MCP wrapper, the LangSmith prototype, the Phase 1 USDA client and validation rules |

## 2. Architecture and interfaces

```text
RecipeInput (dict or model) ──► RecipeCalculator(service).calculate()
      │ validate (Pydantic, extra=forbid)          │ invalid ──► RecipeInvalid(problems=[...])
      │ fetch each distinct FDC ID once ───────────┼─ roli_nutrition.NutritionService.get_nutrition()
      │ classify record state from USDA description (preparation.py)
      │ per ingredient: compatibility → contribution = grams × ref / 100 (exact) or null
      │ per nutrient: covers / excludes, known_subtotal (exact), total only when complete
      │ per serving: ÷ servings, quantized to 6 dp; reconciliation asserted
      └─► RecipeResult ──► compare_scenarios([...]) ──► ComparisonResult
```

| Interface | Signature | Notes |
|---|---|---|
| `RecipeCalculator(service)` | `.calculate(recipe) -> RecipeResult \| RecipeInvalid` | never raises on bad input; raises `ArithmeticError` only if its own reconciliation fails (a bug) |
| `compare_scenarios(results, basis="per_serving")` | `-> ComparisonResult` | keeps the originals; `range_meaningful` false below two complete scenarios |
| `record_state(description)`, `compatibility(state, description)` | pure functions | the raw/cooked table of spec section 5 |
| `display_amount(value, nutrient)` | `Decimal -> str` | 2 dp g / whole mg, half-up; `<0.01 g` / `<1 mg` for positive values that would round to zero |
| LangGraph | `run_roli(recipe={...})`; CLI `python -m roli_agent --recipe file.json` | `route_input` → `calculate_recipe` → `compose`; no LLM node on the path |

Decisions as built: D1 subpackage of the library; D2 keyword table, `as_used` refused for flesh foods (first word of the USDA description in Fish, Beef, Pork, Chicken, Turkey, Lamb, Veal, Game meat, Duck, Goose, Crustaceans, Mollusks, Egg); D3 `per_serving` quantities converted and flagged; D4 display rounding as above, exact Decimals as strings in JSON; D5 structured recipes only; D6 fixtures captured; D7 fractional servings; D8 unresolved contributions are `null`. Corrections: contributions and subtotals exact, per-serving quantized to six places with tolerance `0.0000005 × servings`; the section 8 example reconciles (1.06845 + 1.3808 = 2.44925; 32.3 + 0 = 32.3); `complete` is defined as complete for the supplied list; comparisons report `n_complete` and flag insufficient evidence.

## 3. Files

Created: `nutrition_service/roli_nutrition/recipe/__init__.py`, `models.py`, `preparation.py`, `calculator.py`, `compare.py`; `nutrition_service/tests/test_recipe_calculator.py`, `test_recipe_examples.py`, `test_recipe_preparation.py`; `nutrition_service/scripts/capture_recipe_fixtures.py`, `demo_recipe.py`; 9 fixture files under `tests/fixtures/usda/` (8 foods + the olive-oil search); `roli_agent/tests/test_recipe_path.py`; `nutrition_service/test_report_2A.txt`, `roli_agent/test_report_2A.txt`; this file.

Modified: `SPEC_2A_recipe_calculator.md` (decisions and corrections), `nutrition_service/README.md` (section 11), `tests/captured_expectations.py` (`RECIPE_RECORDS`), `tests/fixtures/usda/manifest.json` (merged), `roli_agent/state.py`, `nodes.py`, `graph.py`, `responses.py`, `__main__.py`.

## 4. Tests

Full outputs: `nutrition_service/test_report_2A.txt` and `roli_agent/test_report_2A.txt`.

| Spec test | Where | What it proves |
|---|---|---|
| T1–T5 | `test_recipe_calculator.py` | single and multi-ingredient complete recipes, four servings, oil and tahini `as_used`, totals equal the sum of contributions |
| T4 | same | `4.821` g and `127.5` mg exactly, also as JSON strings |
| T6–T8, T16 | same | missing FDC ID → known subtotal not total; Foundation broccoli → fat complete, cholesterol incomplete, in a mixed recipe too |
| T9–T11 | same | raw-on-cooked and cooked-on-raw mismatches; unknown states; `as_used` on fish refused with the "declare raw or cooked" message |
| T12 | same (16 cases) | servings 0/negative/text, grams negative/NaN/inf/boolean, string or zero FDC ID, bad states, 0 or 101 ingredients, unknown keys, duplicate IDs → `invalid_recipe` naming every problem, no USDA call |
| T13, T20, T21 | same | duplicate records counted twice and fetched once; per-serving basis converted and flagged; explicit zero vs unknown grams |
| T14 | same (5 cases) | 503, 429, 404, malformed body, mismatched ID → `usda_error:*`, `null` contribution, no alternative record searched |
| T15, T24 | same | reconciliation on four recipes incl. servings 1.5, 3 and 7; recurring decimals `0.006667`, `0.002857` within tolerance |
| T18, T25, T26 | `test_recipe_examples.py` | Bluefin Crudo equals the spec JSON exactly; bottarga appears in every exclusion and display; six unresolved cases all carry `null` |
| T19 | same | Little Gem Lettuces complete: 0.016 + 1.88225 + 1.7115 + 0.3361 = 3.94585 g; 10.4 mg |
| T17, T28 | same | three scenarios: min/median/max over the two complete ones, incomplete one named; one complete → `range_meaningful: false`; none complete → empty values; mixed servings on `totals` basis rejected |
| T22 | `test_recipe_preparation.py` | classifier on every fixture description and edge cases ("cooking" ≠ "cooked", "Rawlings" ≠ "raw", both words → unknown); flesh detection; the full compatibility table |
| T23, T27 | calculator tests | JSON round-trip with `extra="forbid"`; display rounding incl. `<0.01 g`, `<1 mg`, half-up |
| LangGraph | `roli_agent/tests/test_recipe_path.py` | complete reply lists every contribution and both totals; incomplete reply never states a dish total and uses the word "known subtotals"; invalid recipe → no numbers, no USDA call; no LLM call on the path; text path unaffected |

## 5–8. Worked examples (live USDA, `scripts/demo_recipe.py`, all weights hypothetical and labelled)

### 1. Complete recipe: Little Gem Lettuces
```json
{
  "status": "complete",
  "recipe_name": "Little Gem Lettuces (hypothetical weights)",
  "servings": "1",
  "calculator_version": "2a.1",
  "source": "USDA FoodData Central",
  "per_serving_precision": "6 decimal places",
  "completeness_note": "complete = every supplied ingredient was calculated from a validated USDA record with the supplied grams; it does not verify that the list or weights match the restaurant's dish",
  "ingredients": [
    {
      "ingredient_id": "ing_01",
      "name": "Little gem lettuce (green leaf lettuce as the nearest USDA record)",
      "grams_declared": "80",
      "quantity_basis": "total_recipe",
      "grams_in_recipe": "80",
      "preparation_state": "raw",
      "assumption": "hypothetical: a starter-sized salad",
      "usda": {
        "fdc_id": 169249,
        "description": "Lettuce, green leaf, raw",
        "data_type": "SR Legacy",
        "saturated_fat_g_per_100g": "0.02",
        "cholesterol_mg_per_100g": "0",
        "record_state": "raw"
      },
      "usda_error": null,
      "compatibility": "compatible",
      "contribution": {
        "saturated_fat_g": "0.016",
        "cholesterol_mg": "0"
      },
      "resolved": {
        "saturated_fat_g": true,
        "cholesterol_mg": true
      },
      "issues": []
    },
    {
      "ingredient_id": "ing_02",
      "name": "Tahini vinaigrette (tahini)",
      "grams_declared": "25",
      "quantity_basis": "total_recipe",
      "grams_in_recipe": "25",
      "preparation_state": "as_used",
      "assumption": "hypothetical: 2 tablespoons",
      "usda": {
        "fdc_id": 170189,
        "description": "Seeds, sesame butter, tahini, from roasted and toasted kernels (most common type)",
        "data_type": "SR Legacy",
        "saturated_fat_g_per_100g": "7.529",
        "cholesterol_mg_per_100g": "0",
        "record_state": "cooked"
      },
      "usda_error": null,
      "compatibility": "compatible",
      "contribution": {
        "saturated_fat_g": "1.88225",
        "cholesterol_mg": "0"
      },
      "resolved": {
        "saturated_fat_g": true,
        "cholesterol_mg": true
      },
      "issues": []
    },
    {
      "ingredient_id": "ing_03",
      "name": "Pecorino sardo (USDA romano as the nearest record)",
      "grams_declared": "10",
      "quantity_basis": "total_recipe",
      "grams_in_recipe": "10",
      "preparation_state": "as_used",
      "assumption": "hypothetical: a light grating",
      "usda": {
        "fdc_id": 171249,
        "description": "Cheese, romano",
        "data_type": "SR Legacy",
        "saturated_fat_g_per_100g": "17.115",
        "cholesterol_mg_per_100g": "104",
        "record_state": "unknown"
      },
      "usda_error": null,
      "compatibility": "compatible",
      "contribution": {
        "saturated_fat_g": "1.7115",
        "cholesterol_mg": "10.4"
      },
      "resolved": {
        "saturated_fat_g": true,
        "cholesterol_mg": true
      },
      "issues": []
    },
    {
      "ingredient_id": "ing_04",
      "name": "Toasted sesame",
      "grams_declared": "5",
      "quantity_basis": "total_recipe",
      "grams_in_recipe": "5",
      "preparation_state": "as_used",
      "assumption": "hypothetical: a sprinkle",
      "usda": {
        "fdc_id": 170151,
        "description": "Seeds, sesame seeds, whole, roasted and toasted",
        "data_type": "SR Legacy",
        "saturated_fat_g_per_100g": "6.722",
        "cholesterol_mg_per_100g": "0",
        "record_state": "cooked"
      },
      "usda_error": null,
      "compatibility": "compatible",
      "contribution": {
        "saturated_fat_g": "0.3361",
        "cholesterol_mg": "0"
      },
      "resolved": {
        "saturated_fat_g": true,
        "cholesterol_mg": true
      },
      "issues": []
    }
  ],
  "totals": {
    "saturated_fat_g": {
      "complete": true,
      "total": "3.94585",
      "known_subtotal": "3.94585",
      "covers": [
        "ing_01",
        "ing_02",
        "ing_03",
        "ing_04"
      ],
      "excludes": []
    },
    "cholesterol_mg": {
      "complete": true,
      "total": "10.4",
      "known_subtotal": "10.4",
      "covers": [
        "ing_01",
        "ing_02",
        "ing_03",
        "ing_04"
      ],
      "excludes": []
    }
  },
  "per_serving": {
    "saturated_fat_g": {
      "complete": true,
      "total": "3.945850",
      "known_subtotal": "3.945850",
      "covers": [
        "ing_01",
        "ing_02",
        "ing_03",
        "ing_04"
      ],
      "excludes": []
    },
    "cholesterol_mg": {
      "complete": true,
      "total": "10.400000",
      "known_subtotal": "10.400000",
      "covers": [
        "ing_01",
        "ing_02",
        "ing_03",
        "ing_04"
      ],
      "excludes": []
    }
  },
  "issues": [],
  "display": {
    "saturated_fat_g": "3.95 g per serving",
    "cholesterol_mg": "10 mg per serving"
  }
}
```

### 2. Incomplete recipe: Bluefin Crudo with bottarga unmatched
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
    {
      "ingredient_id": "ing_01",
      "name": "Bluefin tuna, raw",
      "grams_declared": "85",
      "quantity_basis": "total_recipe",
      "grams_in_recipe": "85",
      "preparation_state": "raw",
      "assumption": "hypothetical: typical crudo portion",
      "usda": {
        "fdc_id": 173706,
        "description": "Fish, tuna, fresh, bluefin, raw",
        "data_type": "SR Legacy",
        "saturated_fat_g_per_100g": "1.257",
        "cholesterol_mg_per_100g": "38",
        "record_state": "raw"
      },
      "usda_error": null,
      "compatibility": "compatible",
      "contribution": {
        "saturated_fat_g": "1.06845",
        "cholesterol_mg": "32.3"
      },
      "resolved": {
        "saturated_fat_g": true,
        "cholesterol_mg": true
      },
      "issues": []
    },
    {
      "ingredient_id": "ing_02",
      "name": "Bottarga",
      "grams_declared": "5",
      "quantity_basis": "total_recipe",
      "grams_in_recipe": "5",
      "preparation_state": "as_used",
      "assumption": "no USDA record selected",
      "usda": null,
      "usda_error": null,
      "compatibility": "not_applicable",
      "contribution": {
        "saturated_fat_g": null,
        "cholesterol_mg": null
      },
      "resolved": {
        "saturated_fat_g": false,
        "cholesterol_mg": false
      },
      "issues": [
        "missing_fdc_id"
      ]
    },
    {
      "ingredient_id": "ing_03",
      "name": "Olive oil",
      "grams_declared": "10",
      "quantity_basis": "total_recipe",
      "grams_in_recipe": "10",
      "preparation_state": "as_used",
      "assumption": "hypothetical: drizzle",
      "usda": {
        "fdc_id": 171413,
        "description": "Oil, olive, salad or cooking",
        "data_type": "SR Legacy",
        "saturated_fat_g_per_100g": "13.808",
        "cholesterol_mg_per_100g": "0",
        "record_state": "unknown"
      },
      "usda_error": null,
      "compatibility": "compatible",
      "contribution": {
        "saturated_fat_g": "1.3808",
        "cholesterol_mg": "0"
      },
      "resolved": {
        "saturated_fat_g": true,
        "cholesterol_mg": true
      },
      "issues": []
    }
  ],
  "totals": {
    "saturated_fat_g": {
      "complete": false,
      "total": null,
      "known_subtotal": "2.44925",
      "covers": [
        "ing_01",
        "ing_03"
      ],
      "excludes": [
        {
          "ingredient_id": "ing_02",
          "name": "Bottarga",
          "reason": "missing_fdc_id"
        }
      ]
    },
    "cholesterol_mg": {
      "complete": false,
      "total": null,
      "known_subtotal": "32.3",
      "covers": [
        "ing_01",
        "ing_03"
      ],
      "excludes": [
        {
          "ingredient_id": "ing_02",
          "name": "Bottarga",
          "reason": "missing_fdc_id"
        }
      ]
    }
  },
  "per_serving": {
    "saturated_fat_g": {
      "complete": false,
      "total": null,
      "known_subtotal": "2.449250",
      "covers": [
        "ing_01",
        "ing_03"
      ],
      "excludes": [
        {
          "ingredient_id": "ing_02",
          "name": "Bottarga",
          "reason": "missing_fdc_id"
        }
      ]
    },
    "cholesterol_mg": {
      "complete": false,
      "total": null,
      "known_subtotal": "32.300000",
      "covers": [
        "ing_01",
        "ing_03"
      ],
      "excludes": [
        {
          "ingredient_id": "ing_02",
          "name": "Bottarga",
          "reason": "missing_fdc_id"
        }
      ]
    }
  },
  "issues": [
    {
      "ingredient_id": "ing_02",
      "code": "missing_fdc_id",
      "message": "Bottarga has no USDA record; its contribution is unknown and not included."
    }
  ],
  "display": {
    "saturated_fat_g": "at least 2.45 g per serving from 2 of 3 ingredients; missing: Bottarga",
    "cholesterol_mg": "at least 32 mg per serving from 2 of 3 ingredients; missing: Bottarga"
  }
}
```

### 3. Four servings
```json
{
  "status": "complete",
  "recipe_name": "Salmon for four (hypothetical weights)",
  "servings": "4",
  "calculator_version": "2a.1",
  "source": "USDA FoodData Central",
  "per_serving_precision": "6 decimal places",
  "completeness_note": "complete = every supplied ingredient was calculated from a validated USDA record with the supplied grams; it does not verify that the list or weights match the restaurant's dish",
  "ingredients": [
    {
      "ingredient_id": "ing_01",
      "name": "Chinook salmon, cooked",
      "grams_declared": "600",
      "quantity_basis": "total_recipe",
      "grams_in_recipe": "600",
      "preparation_state": "cooked",
      "assumption": "hypothetical: 150 g cooked per person",
      "usda": {
        "fdc_id": 171999,
        "description": "Fish, salmon, chinook, cooked, dry heat",
        "data_type": "SR Legacy",
        "saturated_fat_g_per_100g": "3.214",
        "cholesterol_mg_per_100g": "85",
        "record_state": "cooked"
      },
      "usda_error": null,
      "compatibility": "compatible",
      "contribution": {
        "saturated_fat_g": "19.284",
        "cholesterol_mg": "510"
      },
      "resolved": {
        "saturated_fat_g": true,
        "cholesterol_mg": true
      },
      "issues": []
    },
    {
      "ingredient_id": "ing_02",
      "name": "Olive oil",
      "grams_declared": "20",
      "quantity_basis": "total_recipe",
      "grams_in_recipe": "20",
      "preparation_state": "as_used",
      "assumption": "hypothetical: for the pan",
      "usda": {
        "fdc_id": 171413,
        "description": "Oil, olive, salad or cooking",
        "data_type": "SR Legacy",
        "saturated_fat_g_per_100g": "13.808",
        "cholesterol_mg_per_100g": "0",
        "record_state": "unknown"
      },
      "usda_error": null,
      "compatibility": "compatible",
      "contribution": {
        "saturated_fat_g": "2.7616",
        "cholesterol_mg": "0"
      },
      "resolved": {
        "saturated_fat_g": true,
        "cholesterol_mg": true
      },
      "issues": []
    }
  ],
  "totals": {
    "saturated_fat_g": {
      "complete": true,
      "total": "22.0456",
      "known_subtotal": "22.0456",
      "covers": [
        "ing_01",
        "ing_02"
      ],
      "excludes": []
    },
    "cholesterol_mg": {
      "complete": true,
      "total": "510",
      "known_subtotal": "510",
      "covers": [
        "ing_01",
        "ing_02"
      ],
      "excludes": []
    }
  },
  "per_serving": {
    "saturated_fat_g": {
      "complete": true,
      "total": "5.511400",
      "known_subtotal": "5.511400",
      "covers": [
        "ing_01",
        "ing_02"
      ],
      "excludes": []
    },
    "cholesterol_mg": {
      "complete": true,
      "total": "127.500000",
      "known_subtotal": "127.500000",
      "covers": [
        "ing_01",
        "ing_02"
      ],
      "excludes": []
    }
  },
  "issues": [],
  "display": {
    "saturated_fat_g": "5.51 g per serving (22.05 g for the whole recipe, 4 servings)",
    "cholesterol_mg": "128 mg per serving (510 mg for the whole recipe, 4 servings)"
  }
}
```

### 4. Three scenarios compared (per serving)
```json
{
  "basis": "per_serving",
  "nutrients": {
    "saturated_fat_g": {
      "n_scenarios": 3,
      "n_complete": 2,
      "values": {
        "Crudo A, lean": "1.758850",
        "Crudo C, oily": "3.453900"
      },
      "min": "1.758850",
      "median": "2.606375",
      "max": "3.453900",
      "range_meaningful": true,
      "excluded": [
        {
          "recipe_name": "Bluefin crudo, scenario A (hypothetical weights)",
          "reason": "incomplete"
        }
      ],
      "note": "Range across the 2 modeled recipes that were complete for this nutrient. Ranges describe the supplied recipes only: not a statistical confidence interval and not a guaranteed range for the restaurant's dish."
    },
    "cholesterol_mg": {
      "n_scenarios": 3,
      "n_complete": 2,
      "values": {
        "Crudo A, lean": "32.300000",
        "Crudo C, oily": "41.800000"
      },
      "min": "32.300000",
      "median": "37.050000",
      "max": "41.800000",
      "range_meaningful": true,
      "excluded": [
        {
          "recipe_name": "Bluefin crudo, scenario A (hypothetical weights)",
          "reason": "incomplete"
        }
      ],
      "note": "Range across the 2 modeled recipes that were complete for this nutrient. Ranges describe the supplied recipes only: not a statistical confidence interval and not a guaranteed range for the restaurant's dish."
    }
  },
  "note": "Ranges describe the supplied recipes only: not a statistical confidence interval and not a guaranteed range for the restaurant's dish."
}
```

## 9. LangGraph integration test (live USDA, CLI, 0.8 s, no LLM)

```text
$ .venv/bin/python -m roli_agent --recipe crudo_recipe.json --trace
Recipe: Bluefin crudo, scenario A (hypothetical weights) (1 serving(s)); calculation incomplete.
Ingredients:
- Bluefin tuna, raw: 85 g; USDA 173706 "Fish, tuna, fresh, bluefin, raw"; 1.06845 g saturated fat, 32.3 mg cholesterol [hypothetical: typical crudo portion]
- Bottarga: 5 g; no USDA record; not included: missing_fdc_id [no USDA record selected]
- Olive oil: 10 g; USDA 171413 "Oil, olive, salad or cooking"; 1.3808 g saturated fat, 0 mg cholesterol [hypothetical: drizzle]
Per serving:
- Saturated fat: at least 2.45 g per serving from 2 of 3 ingredients; missing: Bottarga
- Cholesterol: at least 32 mg per serving from 2 of 3 ingredients; missing: Bottarga
These are known subtotals from the ingredients that could be calculated, not totals for the dish.
Basis: USDA FoodData Central values per 100 g; complete = every supplied ingredient was calculated from a validated USDA record with the supplied grams; it does not verify that the list or weights match the restaurant's dish.

--- trace ---
route: structured recipe supplied -> calculator path
recipe: incomplete; sat complete=False, chol complete=False
compose: done
```

The four-serving salmon recipe through the same path gave "5.51 g per serving (22.05 g for the whole recipe, 4 servings)" and "128 mg per serving (510 mg for the whole recipe, 4 servings)", status complete.

## 10. Deviations from the spec

1. **Explicit zero grams resolves the line even without a USDA record** (spec section 7 wording left this open): 0 g of anything contributes exactly 0, flagged `explicit_zero`, so a "pinch of salt, 0 g" line never blocks completeness.
2. **Whole-number USDA references are normalised** (`38.0` → `38`, `0.0` → `0`) so JSON shows `"38"` as in the spec example; fractional values keep every digit (`3.214`, `13.808`).
3. **`fdc_id` is strict**: `"171999"` as a string, `171999.0` and `true` are rejected as invalid input rather than coerced. The spec said "the library's rule"; the library's rule is strict, so this matches it, but it is stricter than Pydantic's default.
4. **Issue messages carry record numbers and nutrient names** for readability, e.g. "USDA record 747447 does not report cholesterol_mg"; the spec only required codes.
5. **The LangGraph reply shows each ingredient's exact contribution** (e.g. `1.06845 g`) and the display-rounded per-serving lines; the spec left the reply layout open.
6. **`compare_scenarios` requires distinct recipe names**, since they key the `values` map.

## 11. Remaining limitations

- **The recipe is the caller's.** Weights, ingredient lists and USDA record choices are supplied by hand; the calculator cannot judge them. Every output says so in `completeness_note`, but a plausible-looking complete result still rests entirely on those inputs.
- **Nearest-record substitutions are invisible to the calculator** ("pecorino sardo" → USDA romano, "little gem" → green leaf lettuce). They are correct arithmetic over a proxy. The ingredient name and `assumption` field are the only place this shows.
- **Raw/cooked classification is a keyword table** over USDA descriptions. It is tested on every fixture, but a description that mentions neither word (most cheeses, oils, breads) is `unknown`, which forces `as_used`; a flesh record without either word would be unresolvable until declared.
- **No household units, no cooking yields, no nutrient retention**, by design; a recipe stated in tablespoons cannot be entered yet.
- **Foundation plant records often lack a cholesterol row**, so vegetables make cholesterol incomplete even though biologically plant cholesterol is zero. The calculator correctly refuses to assume zero; the SR Legacy counterpart usually has the row (as with green leaf lettuce 169249).
- **Scenario comparison is only as good as the scenarios**: three hand-written recipes give a range of three guesses, which the note says plainly.

## 12. Recommended specification for Phase 2B

1. **Recipe discovery (LLM + web search, outside the calculator):** for a menu dish and its listed ingredients, find about three published recipes; record title, URL, stated yield, and a similarity note. Store them as provenance; never let search results carry nutrient numbers.
2. **Ingredient extraction (LLM → structured):** produce the Phase 2A `RecipeInput` shape with `assumption` filled per line ("recipe says 2 tbsp olive oil") and `fdc_id` left `null`; the calculator's `invalid_recipe` path is the validator.
3. **Unit conversion (Python table, not LLM):** a small, cited table of household measures to grams per ingredient class (oils 13.5 g/tbsp, etc.), applied deterministically with the factor recorded in `assumption`; anything not in the table stays `grams: null` → incomplete.
4. **Ingredient matching:** reuse the Phase 1E search-and-select path per ingredient (LLM picks from USDA's candidates, code verifies), and add the relevance test set from CHECKPOINT_1D so matching quality is measured.
5. **Cooking yields:** only with a cited USDA yield table (USDA Agricultural Handbook 102) and only as an explicit, flagged conversion step; otherwise keep the mismatch rule.
6. **Reporting:** `compare_scenarios` output rendered by a deterministic template; the LLM may introduce the dish and read out the range, never alter it; a guard rejects any reply number that is not in the comparison result.
7. **Sensitivity:** per-ingredient share of the per-serving total (already computable from `contribution` ÷ `known_subtotal`) to show which assumption drives the estimate.

**Stopped here. Phase 2B starts only after your review.**
