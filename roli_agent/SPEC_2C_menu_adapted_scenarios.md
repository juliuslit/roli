# Specification: Phase 2C, menu-adapted scenarios (revision 4: revision 3 as implemented for Checkpoint 2C, plus the 2C.1 additions in section 13)

Status: **architecture approved 2026-11-03 (Checkpoint 2C review); built as `roli_agent/recipes/adapt.py`; Phase 2C.1 additions in section 13.** Supersedes revisions 1 and 2. Builds on `SPEC_2B_recipe_scenarios.md` (sections 15.2–15.5). Phase 2C is **internal-only** (section 9); the user-facing reply does not read any of it.

## 0. Summary

Phase 2B scenarios are published recipes exactly as published: an unquantified line, a menu ingredient the recipe lacks, or a household measure USDA cannot weigh stays unknown and the scenario stays incomplete. Phase 2C adds a separate object, the **menu-adapted scenario**: a copy of a published scenario whose named gaps are filled with explicit, labelled assumed weights and calculated by the unchanged Phase 2A calculator. Each assumption has a class computed from the USDA record and the assumed upper-bound weight (never typed by hand), a basis (a USDA household measure, or a proposed restaurant-usage range that is unverified until reviewed), and a low and a high value. Published inputs are never altered; adapted figures are never described as verified restaurant totals or as restaurant servings. A restaurant portion model is a separate later phase (2D, section 10).

## 1. Gaps, by kind

| Gap | Example from the live dishes | 2B treatment | 2C treatment |
|---|---|---|---|
| G1 menu-only ingredient (D8) | bottarga, muscat grape, chive on the crudo | appended, unknown, blocks completeness | assumed weight from a table row for that ingredient and role |
| G2 recipe line without a quantity | "olive oil, for drizzling", "salt, to taste", "a handful of mint" | unknown | assumed weight; class computed |
| G3 household measure the record cannot weigh | "1 carrot" (record lists sizes, line names none); "1 tsp dried oregano" (leaves vs ground); "2 tbsp mirin" | unknown (D20) | portion-size assumption from the record's own labels, low = smallest listed size, high = largest; semantically different labels (leaves vs ground, fruit vs wedge) are never averaged and stay unknown |
| G4 count on a composition proxy (D21) | "3 baby gem lettuce" matched to romaine; "3 large heirloom tomatoes" matched to standard tomatoes | unknown | a table row for the *menu food* (little gem head) with a reviewed weight, or unknown. A proxy's whole-item weight is never used, even within the same food family |
| G5 nutrient not reported by the record | grape tomatoes (Foundation, no cholesterol row) | unknown for that nutrient | not an assumption: an equivalent record under D22 if one exists, else unknown; a missing value is never zero |

Two kinds of proxy are kept apart throughout:

- **composition proxy** (2B `match_type: proxy`): another food's nutrient profile stands in; its effect is `proxy_share` of the known subtotal (D18).
- **portion-size proxy** (2C): a weight taken from a table row or from the record's own size labels; always an assumption with a class, a basis and a review status.

## 2. The menu-adapted scenario

`adapt(published: Scenario, table, policy) -> AdaptedPair | None` returns a **low** and a **high** adapted scenario for one published scenario, or nothing if no gap can be filled.

| Field | Meaning |
|---|---|
| `derived_from` | the published `scenario_id`; the published object is byte-identical before and after (test) |
| `scenario_kind` | `"menu_adapted_low"` / `"menu_adapted_high"`; never a published recipe; the two are one pair, not two recipes (section 7) |
| `assumptions[]` | per filled line: `ingredient_id`, `gap` (G1–G4), `grams_declared` (what the recipe said, `null` when nothing), `grams_assumed`, `bound`, `basis` (`usda_measure` with FDC ID and label, or table row ID), `computed_class`, `review_status`, `note` |
| `calculation` | the Phase 2A result of the adapted list; arithmetic unchanged |
| `completeness` | the Phase 2A `status` **for the modeled ingredient list**; the output never calls it a verified restaurant total (section 8) |
| `assumed_contribution`, `assumed_share` | per nutrient: absolute contribution of assumed lines and its share of the known subtotal (section 6) |
| `servings_basis` | always `"recipe"` (section 9) |
| `representativeness` | at most `assumed`; never `high` |

## 3. Display class and materiality, both computed

Two separate diagnostics, both computed from the matched USDA record's per-100 g values and the **upper-bound** weight, never typed by hand (`adapt.display_class`, `adapt.materiality`; the weights table stores them only for reading and the builder recomputes them):

**Display class** (does the contribution show in the Phase 2A display?):

| Class | Rule (mechanical) |
|---|---|
| `zero_nutrient` | both nutrients reported **and** both exactly 0 per 100 g |
| `low_impact` | both reported, and at the high bound the contribution is below the display floor: saturated fat < 0.005 g (displays as 0.00) and cholesterol < 0.5 mg |
| `displayable` | both reported and the contribution shows; this says nothing about how large it is |
| `nutrient_missing` | the record lacks a value; such a line can never be `zero_nutrient` or `low_impact`; the missing nutrient stays missing (D23) |

**Materiality** (how much does the assumed line matter, in absolute terms?): the high-bound contribution against common daily reference amounts (20 g saturated fat, 300 mg cholesterol): `negligible` below the display floor; `minor` under 1 % of either reference (< 0.2 g or < 3 mg); `moderate` under 5 % (< 1 g or < 15 mg); `major` at or above 5 %. The larger tier of the two nutrients wins. A 0.006 g contribution is `displayable` and `minor`; a 20 g contribution is `displayable` and `major`; the word "substantial" is no longer used.

On USDA zeros: a reported 0 is USDA's value at USDA's precision; the output says "USDA record 173468 reports 0 g and 0 mg per 100 g", never "contains none". Applied to the table in section 5: 1 row is `zero_nutrient` (salt), 4 are `low_impact` (chives, basil, cilantro, lemon zest), 23 are `displayable`, 2 are `nutrient_missing` (the blocked little gem and shiso rows). Among the displayable rows the materiality runs from `minor` (black pepper, 0.032 g at a teaspoon) to `major` (mozzarella on a pizza, 23.6 g).

D5, resolved narrowly: "salt, to taste" is filled at a nominal weight (the record's smallest household measure, "1 dash" = 0.4 g) with `grams_declared: null`; its contribution is 0 by USDA's figures; source `zero_nutrient_nominal`, permitted in both modes. Pepper is `displayable` / `minor` by the rule and is filled only from its table row, like any other row.

## 4. Sources of assumed weights, and the two modes

| Source | What it is | approved mode | experimental mode |
|---|---|---|---|
| `zero_nutrient_nominal` | the line's own matched record reports 0 g and 0 mg; nominal weight = its smallest household measure | yes | yes |
| `record_size_labels` (G3) | the recipe gives a count, the record lists sizes, the line names none: low = smallest listed whole item, high = largest, labelled; never a median; unlike labels never averaged (D20) | yes | yes |
| `table_row` with `approved_by` filled | a reviewed row of the weights table | yes | yes |
| `table_row` unapproved (`verified_usda_measure; restaurant usage assumed` or `proposed_unreviewed`) | an unreviewed row | **no** (`row_unapproved`) | yes, without changing the row's status |
| `blocked_questionable_proxy` rows (W03b, W10, W20, W28) | never | never | never |
| nothing | the line stays unknown; the pair stays incomplete | | |

Approved mode is the normal mode. Experimental mode is a clearly labelled diagnostic for testing unreviewed assumptions; its outputs are marked `mode: "experimental"` on every pair and must not enter approved internal ranges, future ranking inputs or any user-facing response. A row's `review_status` is never changed by either mode.

Rows are selected deterministically by `ingredient_keys` (the longest key found as whole words in the singularised ingredient name). Rows marked as composition proxies (notes) propagate `composition_proxy: true` to the assumption. When a line's own matched record differs from the row's record, the row's record is used and the difference is noted on the assumption.

## 5. Weights table

`roli_agent/recipes/assumed_weights.csv`, generated by `roli_agent/scripts/build_weights_table.py` from live USDA portion weights (`roli_agent/eval/garnish_portions_2026-11-02.json`); classes computed, not typed. Columns: id, ingredient/role, FDC ID and description, per-100 g values, low g, high g, basis, measures, computed class, high-bound contributions, review status, approved_by, approved_on, notes.

Columns also include `ingredient_keys` (deterministic row selection), computed `materiality_at_high`, and `approved_by` / `approved_on`, both empty for every row: **nothing has been approved on Julius's behalf.** Review status vocabulary:

- `verified_usda_measure; restaurant usage assumed`: the bounds are USDA household measures of the named record (the weights are verified; that a restaurant uses that much is the assumption).
- `proposed_unreviewed`: a restaurant-usage range the agent drafted with no external reference. **Not a verified culinary standard.** Not usable for any figure, internal or not, until `approved_by` is filled.
- `blocked_questionable_proxy`: a physically or nutritionally doubtful substitution; never a trusted input; kept for investigation.

Table at generation time (2026-11-02):

| ID | Ingredient / role | USDA record | sat fat g/100 g | chol mg/100 g | Low g | High g | High-bound sat fat g | High-bound chol mg | Display class | Materiality | Basis | Review status |
|---|---|---|---:|---:|---:|---:|---:|---:|---|---|---|---|
| W01 | chives, garnish on a starter | Chives, raw (169994) | 0.146 | 0.0 | 1 | 3 | 0.0044 | 0.00 | low_impact | negligible | usda_measure | verified_usda_measure; restaurant usage assumed |
| W02 | basil leaves, garnish | Basil, fresh (172232) | 0.041 | 0.0 | 2.5 | 6 | 0.0025 | 0.00 | low_impact | negligible | usda_measure | verified_usda_measure; restaurant usage assumed |
| W03a | mint leaves, garnish | Spearmint, fresh (173475) | 0.191 | 0.0 | 0.3 | 11.4 | 0.0218 | 0.00 | displayable | minor | usda_measure | verified_usda_measure; restaurant usage assumed |
| W03b | shiso leaves, garnish |  () |  |  |  |  |  |  | nutrient_missing | unknown | blocked | blocked_questionable_proxy |
| W04a | parsley, garnish | Parsley, fresh (170416) | 0.132 | 0.0 | 3.8 | 10 | 0.0132 | 0.00 | displayable | minor | usda_measure | verified_usda_measure; restaurant usage assumed |
| W04b | cilantro, garnish | Coriander (cilantro) leaves, raw (169997) | 0.014 | 0.0 | 4 | 20 | 0.0028 | 0.00 | low_impact | negligible | usda_measure | verified_usda_measure; restaurant usage assumed |
| W05 | grated hard cheese finished over a salad or pasta | Cheese, parmesan, grated (171247) | 15.371 | 86.0 | 5 | 15 | 2.3056 | 12.90 | displayable | major | proposed | proposed_unreviewed |
| W06 | fresh mozzarella / fior di latte on one pizza | Cheese, mozzarella, whole milk (170845) | 13.9 | 79.0 | 85 | 170 | 23.6300 | 134.30 | displayable | major | proposed | proposed_unreviewed |
| W07 | sesame seeds, toasted, garnish | Seeds, sesame seeds, whole, roasted and  (170151) | 6.722 | 0.0 | 3 | 9 | 0.6050 | 0.00 | displayable | moderate | proposed | proposed_unreviewed |
| W08 | tahini in a dressing, per serving | Seeds, sesame butter, tahini, type of ke (168604) | 7.423 | 0.0 | 15 | 30 | 2.2269 | 0.00 | displayable | major | proposed | proposed_unreviewed |
| W09 | olive oil, drizzle to finish | Oil, olive, salad or cooking (171413) | 13.808 | 0.0 | 4.5 | 13.5 | 1.8641 | 0.00 | displayable | major | proposed | proposed_unreviewed |
| W10 | bottarga, shaved or grated over a starter | Fish, roe, mixed species, raw (175132) | 1.456 | 374.0 | 3 | 10 | 0.1456 | 37.40 | displayable | major | blocked | blocked_questionable_proxy |
| W11 | grapes, halved, garnish | Grapes, red or green (European type, suc (174683) | 0.054 | 0.0 | 20 | 49 | 0.0265 | 0.00 | displayable | minor | usda_measure | verified_usda_measure; restaurant usage assumed |
| W12 | lemon juice, finishing | Lemon juice, raw (167747) | 0.04 | 0.0 | 5.9 | 15 | 0.0060 | 0.00 | displayable | minor | usda_measure | verified_usda_measure; restaurant usage assumed |
| W13 | lemon zest | Lemon peel, raw (167749) | 0.039 | 0.0 | 1 | 2 | 0.0008 | 0.00 | low_impact | negligible | usda_measure | verified_usda_measure; restaurant usage assumed |
| W14 | salt, to taste | Salt, table (173468) | 0.0 | 0.0 | 0.4 | 6 | 0.0000 | 0.00 | zero_nutrient | negligible | usda_measure | verified_usda_measure; restaurant usage assumed |
| W15 | black pepper, to taste | Spices, pepper, black (170931) | 1.392 | 0.0 | 0.1 | 2.3 | 0.0320 | 0.00 | displayable | minor | usda_measure | verified_usda_measure; restaurant usage assumed |
| W16 | red pepper flakes, pinch | Spices, pepper, red or cayenne (170932) | 3.26 | 0.0 | 0.5 | 1.8 | 0.0587 | 0.00 | displayable | minor | usda_measure | verified_usda_measure; restaurant usage assumed |
| W17 | sourdough croutons or torn bread on a salad | Bread, french or vienna (includes sourdo (172675) | 0.529 | 0.0 | 28 | 60 | 0.3174 | 0.00 | displayable | moderate | proposed | proposed_unreviewed |
| W18 | corn kernels, side on a main | Corn, sweet, yellow, raw (169998) | 0.325 | 0.0 | 73 | 145 | 0.4712 | 0.00 | displayable | moderate | usda_measure | verified_usda_measure; restaurant usage assumed |
| W19 | summer squash, side on a main | Squash, summer, zucchini, includes skin, (169291) | 0.084 | 0.0 | 118 | 196 | 0.1646 | 0.00 | displayable | minor | usda_measure | verified_usda_measure; restaurant usage assumed |
| W20 | shishito peppers, side | Peppers, hot chili, green, raw (170497) | 0.021 | 0.0 | 45 | 135 | 0.0284 | 0.00 | displayable | minor | blocked | blocked_questionable_proxy |
| W21 | pluot, sliced, in a salad | Plums, raw (169949) | 0.017 | 0.0 | 33 | 66 | 0.0112 | 0.00 | displayable | minor | proposed | proposed_unreviewed |
| W22 | pistachios, garnish | Nuts, pistachio nuts, raw (170184) | 5.907 | 0.0 | 7 | 14 | 0.8270 | 0.00 | displayable | moderate | proposed | proposed_unreviewed |
| W23 | capers, garnish | Capers, canned (172238) | 0.233 | 0.0 | 4.3 | 8.6 | 0.0200 | 0.00 | displayable | minor | usda_measure | verified_usda_measure; restaurant usage assumed |
| W24 | green olives (castelvetrano), garnish | Olives, pickled, canned or bottled, gree (169096) | 2.029 | 0.0 | 8 | 27 | 0.5478 | 0.00 | displayable | moderate | proposed | proposed_unreviewed |
| W25 | egg yolk, one | Egg, yolk, raw, fresh (172184) | 9.551 | 1085.0 | 17 | 17 | 1.6237 | 184.45 | displayable | major | usda_measure | verified_usda_measure; restaurant usage assumed |
| W26 | pancetta or guanciale, cooked, in a pasta serving | Pork, cured, bacon, cooked, baked (167914) | 14.187 | 107.0 | 16 | 32 | 4.5398 | 34.24 | displayable | major | proposed | proposed_unreviewed |
| W27 | heavy cream, finishing | Cream, fluid, heavy whipping (170859) | 23.032 | 113.0 | 15 | 30 | 6.9096 | 33.90 | displayable | major | proposed | proposed_unreviewed |
| W28 | little gem lettuce, one head |  () |  |  |  |  |  |  | nutrient_missing | unknown | blocked | blocked_questionable_proxy |

What remains unverified: every `proposed_unreviewed` row (W05–W09, W17, W21, W22, W24, W26, W27) and every `blocked` row (W03b shiso, W10 bottarga, W20 shishito, W28 little gem). W03 and W04 were split so that a USDA measure for one plant is never presented as verified for another (spearmint ≠ shiso; parsley ≠ cilantro). The `usda_measure` rows (W01, W02, W03a, W04a, W04b, W11–W16, W18, W19, W23, W25) have verified gram weights, but the *usage* (that a garnish is one tablespoon rather than three) is an assumption nobody has approved. The agent may propose revisions with references; Julius approves consequential rows before any use outside experimental mode.

## 6. Assumed share, sensitivity, and the 30 % warning

Per nutrient and per adapted scenario (`AdaptedScenario`):

- `assumed_contribution` = sum of the calculator's contributions of assumed lines (absolute, whole recipe).
- `assumed_share` = `assumed_contribution / known_subtotal`; **the denominator is the known subtotal of that scenario, never the unknown true total**. When the known subtotal is 0 the share is `null` and the flag `no_known_contribution_to_compare_with` is set. When a nutrient is incomplete in the adapted scenario the share is still computed over the known subtotal and `completeness_by_nutrient` is reported beside it.
- `proxy_share` = the share of the known subtotal from composition proxies (published proxy lines plus proxy-based rows).
- Pair-level `sensitivity_per_serving` and `sensitivity_total` = high-bound minus low-bound known subtotal per nutrient, in absolute units.
- `assumed_share > 0.30` on either nutrient sets `assumption_driven` on the scenario and the pair. **It is a warning, never a discard.**

## 7. Low/high pairs and provenance

One published scenario yields one `AdaptedPair` (`pair_id`, `derived_from`, `scenario_kind: "menu_adapted_pair"`): a low scenario (every assumption at its low bound) and a high scenario (every bound high); combinations are not enumerated. Between-recipe variability (the spread across pairs, reported separately at the low and at the high bound in the internal summary) and within-recipe assumption sensitivity (the pair's `sensitivity_*`) are never merged into one range, and a pair is never counted as two recipes in any count or median. Every assumed line records `grams_declared` (always `null`), both bounds, the source, the row ID, the basis, the review status and the computed diagnostics; the calculator's own `assumption` text on the line starts with `ASSUMED (gap, source, row, bound)`.

## 8. Completeness and eligibility

An adapted scenario can be `complete` for its modeled ingredient list; `completeness_by_nutrient` is reported per nutrient (saturated fat may be complete while cholesterol is not, D23). The output calls it "complete for the modeled ingredient list" and never a verified restaurant total; the Phase 2A completeness note is kept and the pair note adds the recipe-serving basis. Internal eligibility and the confidence a future ranking could attach:

| State | Internal range | Confidence label |
|---|---|---|
| published complete, relevant, not proxy-dependent | yes | `published` |
| adapted complete, only `zero_nutrient` / `low_impact` assumptions, all rows approved | yes | `assumed_minor` |
| adapted complete with approved `displayable` rows | yes, sensitivity shown | `assumed_major` if any assumption is `major` or `moderate`, else `assumed_minor` |
| any assumption from an unapproved row (experimental mode) | **no**: diagnostic only | not rankable |
| `assumption_driven` (share > 30 %) | yes, flagged | one step lower; the ranking must show the sensitivity |
| adapted incomplete | no | not rankable |

## 9. Serving size: internal only, recipe basis

Phase 2C keeps `servings_basis: "recipe"` and preserves full-recipe quantities (`totals`) beside the recipe's own per-serving values. Nothing in 2C is presented as an estimate for a restaurant serving; the user-facing reply keeps the 2B wording (known subtotals, named gaps). The four live margherita recipes (4, 6, 8 and 12 servings per dough) are the standing reason.

## 10. Phase 2D: restaurant portion model (separate, later)

**Purpose:** convert a scenario's full-recipe totals into a figure for one restaurant serving, with the same labelling discipline as 2C.

**Interface to 2C:** input = a 2C scenario (published or adapted) with `totals` and `ingredient grams_in_recipe`; a portion rule for the dish type; output = a `portioned` scenario with `servings_basis: "restaurant_model"`, `portion_rule_id`, `portion_low`, `portion_high`, and per-serving values computed by the unchanged calculator (re-run with the model's serving count, or scaled totals with the scaling recorded). Never overwrites the recipe-basis values.

**Portion rules (reviewed table, like section 5):** per dish type (pizza: one pizza = 1 serving low, 2 servings high; pasta primo; starter salad; main protein in grams of raw fish or meat per plate), each with a basis and review status.

**Evaluation plan:** (1) a set of 20 dishes with photographed or published restaurant portion weights (own weighing of take-out dishes, or published restaurant nutrition data where it exists) to compare rule outputs against; (2) report the error distribution per dish type; (3) sensitivity of per-serving saturated fat and cholesterol to the portion rule versus to the 2C assumptions, so the larger uncertainty is named; (4) no user exposure until the error per dish type is characterised.

## 11. Tests (built, `roli_agent/tests/test_recipes_adapt.py`)

1. `derived_from` published scenario byte-identical before and after.
2. display class and materiality recomputed from the record and the high bound; a typed class in the table is ignored; a record missing a nutrient is `nutrient_missing` and stays missing (D23).
3. In approved mode an unapproved row leaves the line unknown (`row_unapproved`); blocked rows are never used in either mode.
4. No whole-item weight from a composition proxy, even within the same food family (D21); no median of unlike labels (D20).
5. Low ≤ high per assumption; the pair is one entity in every count.
6. `assumed_share` denominator is the known subtotal; zero denominator -> `null` and the stated wording; the 30 % flag never removes a scenario.
7. The user-facing reply is byte-identical with and without adaptation; experimental outputs are labelled `mode: "experimental"`.
8. Every adapted figure carries `servings_basis: "recipe"` and the "not a verified restaurant total" wording; reply-number guard.

## 12. Decisions needed from Julius

1. The display floor (0.005 g / 0.5 mg) and the materiality tiers (1 % and 5 % of 20 g / 300 mg).
2. The weights table: approve, change or delete each `proposed_unreviewed` row; decide who owns future rows.
3. The 30 % diagnostic flag and the confidence labels of section 8.
4. Phase 2D as a separate phase with the evaluation plan of section 10.


## 13. Phase 2C.1 additions (2026-11-03, `CHECKPOINT_2C1.md`)

| Change | Where | Rule |
|---|---|---|
| **G5 measure-ambiguous gap** | `adapt._fill_from_measure_options`, source `record_measure_labels` | the line's unit matches several labels of the matched record that weigh differently ("1 tsp, leaves" 1 g vs "1 tsp, ground" 1.8 g; "1 cup, cubes" vs "1 cup, crumbs"; "1 tsp packed/unpacked" sugar). The published line stays unknown (D20: no default); the pair takes the smallest label as low and the largest as high, both labelled, never averaged. The converter records the candidate labels on the line (`ParsedIngredient.portion_options`). Permitted in both modes (record-derived, like size labels); on a composition proxy the labels are the proxy's volume measures and the assumption is marked `composition_proxy` (D21). |
| **G3 from dimension-labelled sizes** | `convert.is_sized_label`, `adapt._fill_from_size_labels` | a whole-item label that states a size by dimension ('1 fruit (2-3/8" dia)') counts as a size label when the record offers more than one whole item, so "1 lemon" on the lemon record (58 g and 84 g fruits) is `portion_size_unspecified` in the published scenario and a 58-84 g G3 assumption in the pair. A lone dimension-labelled fruit is the record's one item weight and converts directly. |
| **G3 with a single sized label** | same | a record whose only whole-item label is sized ("1 large" hard-boiled egg) gives low = high, `note: "single labelled size"`; still a labelled size assumption, never a default. |
| **Reconciled counts** | `InternalSummary.n_blocked_lines`, `n_unfilled_in_pairs`, `n_unfilled_no_pair` | `n_lines_filled + n_unfilled_in_pairs + n_unfilled_no_pair = n_blocked_lines` is asserted on every summary; the statement prints the three terms. |

Nothing in this section changes approved-mode permissions beyond the two record-derived sources above, the weights table, D23, or the user-facing reply.


## 14. Phase 2D additions (2026-11-03, `CHECKPOINT_2D.md`)

| Change | Where | Rule |
|---|---|---|
| **Amount basis of a weights row** | `assumed_weights.csv` column `amount_basis`; `adapt._fill`, `_adapt_one` | `per_plate` (every restaurant-usage row: the range is what one plate carries) enters the calculator as a per-serving amount, so a recipe for N servings gets N times it; `per_count_unit` (W25 egg yolk, W28b little gem head) is one item, multiplied by the line's stated count for a count line (G4). **Correction:** revision 3 had entered per-plate amounts as whole-recipe amounts, understating them per recipe serving by the serving count. The 2C.1 controlled figures were computed under the old reading. |
| **Median-size lines in the pair** | `adapt._spread_for_median_line` | a published line weighed at the assumed median size (D20 revised) gets a G3 assumption from the same labels (low = smallest, high = largest) with `published_grams` = the median, so the pair shows the sensitivity to the size assumption; such lines are counted as `n_median_size_spreads`, not as blocked lines. |
| **Inference layer on the bounds** | `AdaptedScenario.inferences`, `inferred_totals` | rule I01 (olive-oil cholesterol zero) applies to both bounds; `n_complete_low/high_with_inferences` count pairs complete once the inference is accepted. |
| **Calculator input kept** | `AdaptedScenario.calculator_input` | the modeled line list is stored so Phase 2D can re-run the unchanged calculator at `servings = 1 / f`. |
| **Three evidence-backed rows** | W28b, W20b, W03c | `proposed_from_evidence_2c1`, composition proxies flagged, experimental mode only; the blocked rows W03b, W10, W20, W28 are untouched and never used; on a key tie a usable row beats a blocked one. |
