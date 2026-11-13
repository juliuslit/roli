# Phase 2C proposal: restaurant-specific ingredient assumptions (menu-adapted scenarios)

Status: **proposal only (D11, 2026-11-02). Nothing here is implemented.** Written for Julius's review after Checkpoint 2B-2.

## 1. The problem 2B-2 leaves open

Phase 2B-2 builds scenarios from published recipes and appends every menu-listed ingredient the recipe lacks as an unknown-quantity line (D8). That is the honest result, and it has a predictable consequence: a dish whose printed garnish appears in no published recipe never gets a complete scenario. In the live run the crudo's bottarga, muscat grape and chive, the little gem's pecorino sardo and toasted sesame, the salmon's shishito all block completeness. The figures that exist are known subtotals, never totals.

Two different gaps hide behind "incomplete":

| Gap | Example | Effect on saturated fat and cholesterol |
|---|---|---|
| **Low-impact unknown** | chives, shiso, basil leaves, salt, pepper, lemon zest, grape | near zero whatever plausible weight is assumed |
| **Substantial unknown** | bottarga (cured roe, cholesterol-rich), pecorino sardo, burrata, pancetta, an extra egg yolk | large, and strongly weight-dependent |

Treating both the same way (unknown, blocks completeness) is correct but makes the product mute. Treating them the same way in the other direction (modeled zero) would be wrong for the second row. Phase 2C separates them.

## 2. Menu-adapted scenarios

A **menu-adapted scenario** is a copy of a published-recipe scenario in which each menu-only line receives an **explicit assumed weight**, a USDA record (from the same matcher), and the unchanged Phase 2A calculator computes its real contribution. It is a different object from the published recipe: `scenario_kind: "menu_adapted"`, never presented as the recipe's own figures, and always shown next to the unadapted scenario so a reader sees exactly what the assumption added.

Per line, the adapted scenario records: `grams_declared: null` (what the recipe said), `grams_assumed` (what Phase 2C assumed), `assumption_basis` (where the weight comes from), `assumption_class` (below), and the resulting contribution. The calculator receives `grams = grams_assumed` with an `assumption` string; its arithmetic and completeness rules are untouched. A menu-adapted scenario can therefore be *complete*, but its `representativeness` can never be `high`: it is `assumed` at best, and the range statement says "including assumed weights for X and Y".

## 3. Where assumed weights come from (in order of preference)

1. **A USDA portion of the matched record**, when the menu wording implies a count or a household measure: "1 tbsp" grated bottarga, "a few" chives → 1 tbsp chopped chives (USDA portion), basil leaves → "5 leaves" portion. Deterministic, cited to the FDC ID and portion label.
2. **A garnish table** (`roli_agent/recipes/garnish_weights.json`, a reviewed fixture): typical restaurant garnish weights per dish type, each entry with a source note (a culinary reference, a chef's book, or an explicit "estimate by Julius, 2026-xx-xx"). Example entries: shaved bottarga on a crudo 3–6 g; grated hard cheese on a salad 5–10 g; sesame seeds on a salad 2–4 g; fresh herb leaves 1–3 g; a drizzle of oil 5–10 g.
3. **Nothing.** An ingredient with no portion and no table entry stays unknown, and the adapted scenario stays incomplete. Phase 2C never invents a number outside these two sources.

Ranges in the table (3–6 g) produce two adapted scenarios (low and high) rather than a midpoint, so the comparison shows the sensitivity instead of hiding it.

## 4. Assumption classes

| Class | Definition | Rule |
|---|---|---|
| `zero_nutrient` | the matched USDA record reports **0 g saturated fat and 0 mg cholesterol** per 100 g (salt, water, vinegar, most fresh herbs, citrus juice, sugar) | any plausible weight gives exactly 0; the line may be completed with an assumed weight from source 1 or 2 and the scenario stays `complete`; the contribution is 0 **because USDA says 0 per 100 g**, never because the weight was set to 0 |
| `low_impact` | the record reports > 0 but the assumed weight's contribution is below the display floor (< 0.01 g saturated fat and < 1 mg cholesterol) at the high end of the assumed range | completed with the assumed weight; flagged; the statement says "including small assumed garnish weights" |
| `substantial` | anything else (bottarga, cheeses, cured meats, egg, cream, nuts in quantity) | completed only with a garnish-table entry; low and high scenarios; the statement names the ingredient and the assumed grams explicitly |

This is also the narrow answer to D5: "salt, to taste" is `zero_nutrient` (USDA 173468 "Salt, table": 0 g, 0 mg per 100 g), so it can be completed with any assumed weight without changing the arithmetic, and the unknown weight is still recorded as unknown. Black pepper is `low_impact` at garnish weights (USDA reports a small saturated-fat value; 1 g of pepper contributes about 0.01 g). The distinction is made by the USDA record and the display floor, not by a hand-written "negligible" list.

## 5. Omissions in the other direction

Recipes also contain ingredients the restaurant dish may not: a home margherita recipe's dough yields six servings of a size no pizzeria serves; a salad recipe's dressing may be twice the restaurant's. Phase 2C does not try to correct these. It reports them as **portion-size uncertainty**: per-serving figures depend on the recipe's own serving count, which is shown with every scenario. Scaling to a restaurant portion would need a restaurant-portion model (grams of the finished dish per serving), which is a separate decision and not proposed here.

## 6. Output and wording

The dish estimate gains `adapted_scenarios` beside `scenarios`, and the summary gains a second range: "range across published recipes" (2B-2, unchanged) and "range including assumed garnish weights" (2C), each with its own `n_eligible`. Python templates only. Every assumed weight appears in the reply with its basis: "bottarga: 3 g and 6 g assumed (garnish table, cured roe shaved over a starter); USDA 173701".

## 7. Tests the phase must pass before it is wired in

- An adapted scenario never changes `grams_declared` of any recipe line; the published scenario it derives from is byte-identical before and after.
- A `substantial` line without a garnish-table entry stays unknown and the adapted scenario stays incomplete.
- A `zero_nutrient` classification is derived from the USDA record's own 0 values; a record reporting > 0 for either nutrient can never be classed `zero_nutrient`.
- The low/high pair from a range always brackets the midpoint and both appear in the comparison.
- The reply names every assumed weight; a regression test scans the reply for grams that are not in the estimate object.

## 8. Cost

No new LLM calls: matching for menu-only words already happens in 2B-2 (their records are known), and garnish weights are table lookups. One extra calculator run per adapted scenario (no network: the service cache holds the records).

## 9. Decisions needed from Julius before 2C starts

1. Approve the three assumption classes and the "USDA says 0" rule as the resolution of D5.
2. Approve the garnish table approach, and who writes the first entries (proposal: Julius supplies or approves each weight; the agent drafts with references).
3. Decide whether menu-adapted ranges are shown to end users or kept as an internal diagnostic until a restaurant-portion model exists.
