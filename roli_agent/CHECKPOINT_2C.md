# Checkpoint 2C: menu-adapted scenarios (internal), held-out v3, D22/D23 outcomes

Date: 2026-11-02. Status: **Phase 2C built and tested; stopped for review. Internal only: no user-facing reply changed. Phase 2D, menu-wide ranking, Telegram and the conversational interface not started.** Specification: `SPEC_2C_menu_adapted_scenarios.md` revision 3; decisions in `SPEC_2B_recipe_scenarios.md` section 15.5; weights table `roli_agent/recipes/assumed_weights.csv` (generated, nothing approved).

## 1. Summary

| Item | Result |
|---|---|
| Built | `roli_agent/recipes/adapt.py` (`adapt_pairs`, `WeightsTable`, computed `display_class` and `materiality`), models `Assumption`, `AdaptedPair`, `AdaptedScenario`, `InternalSummary`; `estimate_dish(..., adapt_mode="off"/"approved"/"experimental")`; `scripts/replay_adapt.py`; `scripts/build_weights_table.py` regenerated (30 rows, W03/W04 split) |
| Tests | agent **186 passed** (9 new for 2C, 1 for the plain-name retry, 1 for density tolerance), 4 skipped live; library 308 passed unchanged (`test_report_2C.txt`). No regressions; three earlier tests had their expectations updated for the retry's extra USDA searches |
| Published scenarios | byte-identical before and after adaptation (asserted inside `adapt_pairs` on every call, and by test); Phase 2A calculator untouched (test: the calculator source does not mention adaptation) |
| Reply | the user-facing reply is byte-identical with adaptation off, approved or experimental (test); no internal number reaches it |
| Five dishes, 19 published scenarios | **approved mode: 8 pairs, 11 lines filled (salt nominal weights and record size labels only), 0 complete. Experimental mode: 18 pairs, 66 lines filled, 99 left unfilled, 0 complete** for the modeled list at either bound |
| Why still nothing complete | every dish has at least one line that no permitted assumption can fill: a USDA record without a cholesterol row (23 lines, 13 of them extra-virgin olive oil; D23), a household measure the record cannot weigh (47 lines), a blocked row (14: bottarga, shishito, shiso, little gem) |
| Held-out v3 | 54 rows, labels frozen before scoring: 18 direct, 26 acceptable proxies, 3 label disagreements, 2 false matches (both retained by your decision), 5 unresolved; high-consequence false-match rate 4.9 % |

## 2. What was built, against your twelve refinements

| # | Refinement | Implementation |
|---|---|---|
| 1 | display impact vs materiality | `display_class` (`zero_nutrient` / `low_impact` / `displayable` / `nutrient_missing`, by the 0.005 g / 0.5 mg floor) and a separate `materiality_at_high` (`negligible` / `minor` / `moderate` / `major`, absolute high-bound contribution against 20 g and 300 mg daily references). "Substantial" is gone |
| 2 | class-count inconsistency | spec section 3 now states the computed counts (1 zero-nutrient, 4 low-impact, 23 displayable, 2 nutrient-missing) and names them |
| 3 | W03/W04 split | W03a mint (USDA spearmint measures), W03b shiso (blocked: no USDA record), W04a parsley, W04b cilantro (its own USDA measures) |
| 4 | blocked rows | W10, W20, W28 and W03b are `blocked_questionable_proxy`; `WeightRow.usable()` refuses them in both modes (tests, and 14 live refusals) |
| 5 | no approvals | `approved_by` is empty on all 30 rows (test) |
| 6 | experimental mode | `mode: "experimental"` on every pair; rows' `review_status` untouched; the measurement script runs it on the same published scenarios as approved mode; nothing from it enters the estimate's `summary`, `comparison` or the reply |
| 7 | deterministic classes, missing stays missing | classes recomputed from the record and the high bound on every build; `nutrient_missing` lines are never filled (D23); the 13 olive-oil lines stay incomplete for cholesterol (section 5) |
| 8 | one pair, not two recipes | `AdaptedPair` with `derived_from`, `pair_id`, `scenario_kind: "menu_adapted_pair"`; pair-level `sensitivity_*`; between-recipe spread reported separately per bound |
| 9 | 30 % warning | `assumption_driven` flag only; `assumed_share` of the **known subtotal** (null when 0, with its own flag); absolute `sensitivity_per_serving` and `sensitivity_total` reported |
| 10 | recipe basis | `servings_basis: "recipe"`; whole-recipe `totals` kept in every calculation; pair note says per-serving values are on the recipe's own count |
| 11 | internal | `adapt_mode` defaults to `off` in the graph; the CLI and reply do not expose adaptation |
| 12 | published byte-for-byte, 2A unchanged | guarded in code and tests |

Also built, from your other decisions: the bounded plain-name retry in the matcher (`retried_with_plain_name`), the D23 measurement fields (`completeness_by_nutrient` on scenarios and adapted scenarios; `n_saturated_fat_only_complete` in summaries), and held-out v3.

## 3. Published versus adapted, all five dishes (experimental mode; approved mode in section 4)

Live pass on the five Flour + Water dishes with the 2B-2.1 page and search caches reused (same recipes where the search cache still held them; the relevance rubric was re-run live and admitted three recipes it had excluded in run 4: two grilled or baked little-gem recipes and a one-serving Food Network margherita). Adaptation was then re-run offline on the saved published scenarios after three row-selection fixes (section 7), so the numbers below are from `roli_agent/eval/2b2_live_2026-11-02_2c_v2.json`.

| Dish | Published calculated / complete | Pairs built | Lines filled | Lines unfilled (main reasons) | Complete low / high | Assumption-driven |
|---|---:|---:|---:|---|---:|---:|
| Bluefin Crudo | 4 / 0 | 4 | 17 | 17: 10 measures, 4 blocked (bottarga), 2 no cholesterol row, 1 no record | 0 / 0 | 1 |
| Little Gem Lettuces | 4 / 0 | 4 | 23 | 23: 12 measures, 7 no cholesterol row, 3 blocked (little gem), 1 no row | 0 / 0 | 2 |
| Heirloom Tomatoes | 3 / 0 | 3 | 11 | 22: 10 measures, 6 no cholesterol row, 3 blocked (shiso), 3 no row | 0 / 0 | 0 |
| Margherita | 4 / 0 | 3 | 4 | 18: 6 no cholesterol row, 6 measures, 1 no row, 1 no record, 4 in the unpaired recipe | 0 / 0 | 0 |
| King Salmon | 4 / 0 | 4 | 11 | 19: 9 measures, 4 blocked (shishito), 2 no record, 2 no cholesterol row, 2 no row | 0 / 0 | 0 |

Per-recipe detail (per serving on the recipe's own count; "at least" = known subtotal of an incomplete list):

| Recipe (servings) | Published sat fat / chol | Adapted low | Adapted high | Sensitivity per serving | Assumed share at high (of known subtotal) | Filled | Still unfilled |
|---|---|---|---|---|---|---|---|
| Spicy Tuna Crudo (2) | ≥ 1.74 g / ≥ 38 mg | ≥ 2.07 g / 38 mg | ≥ 2.72 g / 38 mg | 0.64 g / 0 mg | 35 % / 0 % → **driven** | carrot, scallions, orange (record sizes); olive oil (W09); micro cilantro; muscat grape; chive | mirin, white miso, lemon (measures); bottarga (blocked) |
| Sicilian Tuna Crudo (4) | ≥ 1.86 / ≥ 22 | ≥ 1.87 / 22 | ≥ 1.88 / 22 | 0.02 / 0 | 1 % / 0 % | salt (nominal 0.4 g), red pepper flakes, muscat grape, chive | lemon, olives (measures); EVOO (no cholesterol row); bottarga |
| James Beard Tuna Crudo (4) | ≥ 0.62 / ≥ 22 | ≥ 0.63 / 22 | ≥ 0.64 / 22 | 0.01 / 0 | 2 % / 0 % | salt, black pepper (W15), muscat grape, chive | EVOO (no cholesterol row); jarred chiles (measure); bottarga |
| Tuna Crudo, twopurplefigs (4) | ≥ 2.50 / ≥ 0 | ≥ 2.50 / 0 | ≥ 2.51 / 0 | 0.005 / 0 | 0 % / — | muscat grape, chive | tuna block, capers, vinegar, oil (typo units: measures); garlic (no record); bottarga |
| Little Gem Salad (4) | ≥ 3.20 / ≥ 0 | ≥ 3.72 / 1 | ≥ 4.49 / 3 | 0.76 / 2.2 | 28 % / 100 % → **driven** | salt-and-pepper (W15), tahini vinaigrette (W08), pecorino sardo (W05), toasted sesame (W07) | little gem heads (blocked); champagne vinegar, EVOO (no cholesterol row); honey (measure) |
| Little Gem Wedge Salad (4) | ≥ 7.33 / ≥ 30 | ≥ 7.85 / 31 | ≥ 8.61 / 33 | 0.77 / 2.2 | 14 % / 9 % | pepper, radishes (sizes), tahini, pecorino, sesame | bread, garlic ×2, yogurt, eggs (measures); vinegar, red onion (no cholesterol row); little gem |
| Grilled Little Gems (6) | ≥ 0.01 / ≥ 0 | ≥ 0.56 / 1 | ≥ 1.49 / 2 | 0.92 / 1.4 | 99 % / 100 % → **driven** | zest (W13), salt ×2, oil (W09), chives, pecorino, tahini, sesame | yogurt, tarragon, garlic (measures); canola oil (no row); little gem |
| Baked Goat Cheese With Garden Lettuces (4) | ≥ 18.43 / ≥ 26 | ≥ 18.95 / 27 | ≥ 19.72 / 29 | 0.77 / 2.2 | 6 % / 11 % | salt, pepper, tahini, pecorino, sesame | EVOO, vinegars (no cholesterol row); thyme, rosemary, baguette (measures) |
| Heirloom Tomato Salad (6) | ≥ 1.42 / ≥ 0 | ≥ 1.45 / 0 | ≥ 1.48 / 0 | 0.03 / 0 | 3 % / — | pluot (W21, proxy size), sourdough (W17) | EVOO, vinegar (no cholesterol row); cherry tomatoes, onion, oregano (measures); shiso |
| Pluot-Tomato Salad (6) | ≥ 1.85 / ≥ 0 | ≥ 1.98 / 0 | ≥ 2.22 / 0 | 0.24 / 0 | 16 % / — | pluots, EVOO drizzle (W09), basil-or-mint (W03a), flaky salt, sourdough | sugar, cream, yogurt, honey (measures); EVOO ×2 (no cholesterol row); tomatoes, balsamic (no row); shiso |
| Chamoy Tomato Salad (6) | ≥ 0.41 / ≥ 0 | ≥ 0.44 / 0 | ≥ 0.47 / 0 | 0.03 / 0 | 11 % / — | salt, pluot, basil, sourdough | tamarind, sugar, chips (measures); chipotle (no row); onion, sesame oil (no cholesterol row); shiso |
| Margherita, King Arthur (12) | ≥ 1.83 / ≥ 7 | ≥ 1.83 / 7 | ≥ 1.83 / 7 | 0.0001 / 0 | 0 % / 0 % | basil (W02) | canned tomatoes, EVOO (no cholesterol row); garlic, 00 flour (measures) |
| Best Homemade Margherita (4) | ≥ 8.22 / ≥ 42 | ≥ 8.22 / 42 | ≥ 8.23 / 42 | 0.01 / 0 | 0 % / 0 % | kosher salt (W14), red pepper flakes | EVOO ×2 (no cholesterol row); semolina (no row); garlic (measure) |
| Margherita, Food Network (1) | ≥ 41.37 / ≥ 179 | same | same | 0 / 0 | 0 % / 0 % | salt-and-pepper | EVOO ×2 (no cholesterol row); garlic, oregano, basil (measures); pizza dough sub-recipe (no record) |
| Margherita, Taste of Home (6) | ≥ 4.27 / ≥ 15 | no pair | | | | nothing fillable | oregano, garlic, olive oil (measures); canned tomatoes (no cholesterol row) |
| Baked King Salmon (4) | ≥ 10.66 / ≥ 108 | ≥ 10.75 / 108 | ≥ 10.82 / 108 | 0.08 / 0 | 1 % / 0 % | squash (W19), corn (W18), basil | honey (measure); optional toppings (no row); shishito |
| Best Easy Healthy Baked Salmon (4) | ≥ 6.21 / ≥ 85 | ≥ 6.29 / 85 | ≥ 6.37 / 85 | 0.07 / 0 | 2 % / 0 % | squash, corn | herb blend, lemon (measures); shishito |
| Crispy Skin Salmon (4) | ≥ 4.87 / ≥ 77 | ≥ 4.95 / 77 | ≥ 5.03 / 77 | 0.08 / 0 | 3 % / 0 % | squash, corn, basil | pepper (typo unit), garlic (measures); chicken stock (no record); shishito |
| Pan-Seared King Salmon (6) | ≥ 6.60 / ≥ 82 | ≥ 6.74 / 82 | ≥ 6.99 / 82 | 0.25 / 0 | 5 % / 0 % | olive oil (W09), corn, basil | milk (no record); lemon thyme (no row); squash, shallot, thyme, tomato (measures); EVOO, vinegar (no cholesterol row); shishito |

Reading. The adapted figures move little for most recipes (sensitivity under 0.3 g saturated fat per serving in 14 of 18 pairs) because the lines that can be filled are garnishes; the three assumption-driven pairs are the ones where a proposed `major` row (olive-oil drizzle, tahini, pecorino) lands on a small known subtotal. Nothing becomes complete because the unfillable gaps (section 6) sit in every recipe.

## 4. Approved-only mode versus experimental mode (same published scenarios)

| | Approved (normal) | Experimental (diagnostic) |
|---|---:|---:|
| pairs built / published calculated | 8 / 19 | 18 / 19 |
| lines filled | 11 | 66 |
| by source | 7 zero-nutrient nominal (salt), 4 record size labels | 7 nominal, 4 sizes, 55 table rows |
| by gap | G2 7, G3 4 | G1 menu-only 35, G2 24, G3 4, G4 3 |
| by display class | zero 7, displayable 4 | zero 8, low-impact 12, displayable 46 |
| by materiality | negligible 7, minor 4 | negligible 20, minor 23, moderate 11, major 12 |
| unfilled | 154 (of which 32 `row_unapproved`) | 99 |
| complete (low / high) | 0 / 0 | 0 / 0 |
| assumption-driven | 0 | 3 |
| adaptation cost | no model or search calls; 0.01–0.09 s per dish (USDA records already cached) | same |

Approved mode fills exactly what you allowed: a nominal 0.4 g for salt lines whose record reports 0 and 0, and labelled size ranges for counts on records that list sizes. Everything else waits for a row approval.

## 5. D23 measurement: saturated fat complete, cholesterol unreported

With D23 refused, a line on the Foundation extra-virgin olive-oil record (748608: 15.4 g saturated fat, no cholesterol row) is resolved for saturated fat and unresolved for cholesterol. In this run no scenario reaches "saturated fat complete, cholesterol incomplete" (`n_saturated_fat_only_complete` = 0 everywhere) because every such scenario also has other gaps; the per-nutrient completeness is now recorded on every published and adapted scenario so the next ranking phase can use it. The 13 olive-oil lines are the single largest unfillable group (section 6).

## 6. Where the remaining missing values come from (experimental mode, 99 unfilled lines + 4 in the one unpaired recipe)

| Cause | Lines | Kind | Examples |
|---|---:|---|---|
| household measure the record cannot weigh (D20: ambiguous or absent labels) | 47 | technical | "1 lemon" (the juice record's labels), garlic cloves (two clove labels), honey by the teaspoon (fixed going forward: the record's cup and tablespoon densities differ by 1 %, now tolerated), greek yogurt and bread by the cup, miso and mirin by the spoon, lines with the typo "tabelspoons" |
| USDA record lacks a nutrient (D23 refused) | 23 | record | extra-virgin olive oil ×13, vinegars ×5, red onion ×2, canned tomatoes, sesame oil |
| blocked row | 14 | unsupported assumption, by decision | bottarga ×4, shishito ×4, shiso ×3, little gem ×3 |
| no table row | 7 | unsupported assumption | canola oil, lemon thyme, semolina, chipotle, tamarind, "optional toppings", heirloom tomatoes (a G1 word with no row) |
| no USDA record (matching) | 4 | matching | garlic cloves pan-fried, pizza dough sub-recipe, milk, chicken stock |
| the one recipe with nothing fillable | 4 | mixed | Taste of Home margherita: oregano leaves/ground, garlic, olive oil (measures), canned tomatoes (no cholesterol row) |

So the remaining gaps are primarily technical measure gaps (47) and record gaps (23), then assumptions blocked by decision (14). Unsupported-but-fillable assumptions account for only 7 lines.

## 7. Corrections made during the checkpoint, and what the live run exposed

1. Row keys: "fresh lemon thyme" was taking the lemon-juice row and "canola or safflower oil" the olive-oil row through bare keys; the keys were tightened and the adaptation re-run offline (`replay_adapt.py`, output `_2c_v2.json`; the first adaptation is kept inside `_2c.json`).
2. Compound lines: "kosher salt and freshly ground black pepper" was filled as a zero-nutrient salt weight, hiding the pepper; lines joined by "and"/"or" now go to the table instead (W15 pepper).
3. Derived-volume density tolerance: USDA's cup and tablespoon weights for honey disagree by 1 % through rounding; a 2 % tolerance is now allowed (test). This affects future conversions, not the saved scenarios.
4. Relevance variance: the rubric admitted three recipes this run that it had excluded in run 4 (two grilled/baked little-gem recipes, a one-serving Food Network margherita with 41 g saturated fat per "serving"). Model variance at temperature 0, recorded here as before; it does not affect the 2C logic but it does affect which scenarios exist.
5. Held-out v3 (section 8) and the plain-name retry: the retry fired for one row (beef tallow); prosciutto and speck resolved this run through the model's own query.

## 8. Held-out evaluation v3

v1 and v2 and their results untouched. v3 (`heldout_set_v3.csv`, changelog `heldout_CHANGELOG.md`): ghee accepts the exact record "Butter, Clarified butter (ghee)" (171314, verified live: 60.0 g / 300 mg per 100 g) as direct; bresaola reviewed against "Beef, cured, dried" (170604: 0.95 g / 79 mg) and kept a proxy; dry vermouth reviewed against "Alcoholic beverage, wine, dessert, dry" (175112) and accepted as direct; 'nduja → salami and fresh foie gras → canned pâté kept as false matches. Scored once (`heldout_v3/results_2026-11-02.{json,md}`, notes in `heldout_v3/review_notes.md`): 18 direct, 26 proxy, 3 mislabelled (the model over-claims bresaola and gorgonzola as direct, under-claims soppressata), 2 false matches (the two retained by decision), 5 unresolved (duck fat, squid ink, bone marrow, coppa, and manchego this run). High-consequence rows: 2 false matches of 41 (4.9 %).

## 9. Assumptions that deserve human review first

| Row | Why | Used in |
|---|---|---|
| W09 olive-oil drizzle 4.5–13.5 g (`major`) | the largest single mover; a drizzle range is a guess; 4 pairs, one made assumption-driven by it | crudo, gem, tomato, salmon |
| W05 grated pecorino 5–15 g, W08 tahini 15–30 g (`major`, composition proxies) | together they are 28 % of the Little Gem salads' known saturated fat and 100 % of their cholesterol; the menu says "tahini vinaigrette", the row is plain tahini | all 4 gem pairs |
| W07 sesame 3–9 g (`moderate`) | USDA lists only an ounce; the range is proposed | gem |
| W18 corn 73–145 g, W19 squash 118–196 g (`moderate`/`minor`) | USDA ear and fruit sizes used as a *side-dish* quantity: the usage is the assumption | all salmon pairs |
| W17 sourdough 28–60 g, W21 pluot 33–66 g (proxy size) | pluot uses the plum's size, flagged as a proxy size | tomato pairs |
| W11 grapes 20–49 g, W01 chives 1–3 g | low stakes (`minor`/`negligible`) but on every crudo pair | crudo |
| zero-nutrient nominal for "flaky salt" | 0 contribution by USDA's figures; the nominal 0.4 g is bookkeeping | 7 lines |
| blocked W10 bottarga, W20 shishito, W03b shiso, W28 little gem | each blocks every pair of its dish; a reviewed weight and a reviewed composition proxy are both needed | 14 lines |

## 10. Prioritised shortlist: what would most improve the five test dishes

1. **Extra-virgin olive oil's missing cholesterol row (13 lines, 10 pairs).** Not a weight assumption: a record choice. Options are a narrower D19 wording for this one pair of records (the SR Legacy olive oil reports 0 mg and differs by 1.6 g saturated fat per 100 g), or accepting that these pairs stay cholesterol-incomplete. Your decision; nothing was changed.
2. **The four blocked rows** (bottarga, shishito, shiso, little gem head): one blocked line per dish, and the crudo's is the dish's signature ingredient. Each needs a reviewed weight and a reviewed composition proxy.
3. **Garlic cloves and whole lemons (8 lines):** two USDA label patterns ("1 clove" vs "3 cloves"; the lemon-juice record's "1 lemon yields") that a small, testable label rule would resolve without any assumption.
4. **W09, W05, W08** (the `major` rows): approving or correcting them changes the numbers most.
5. **W18, W19** for the salmon and **W17, W21** for the tomatoes: moderate stakes, all four salmon and three tomato pairs.
6. Everything else is `minor` or `negligible` and can wait.

Even with 1–5 resolved, no pair in this run becomes complete: vinegars and canned tomatoes without a cholesterol row, sub-recipes ("pizza dough"), and typo units remain. The honest next lever is the measure gap (item 3's pattern, generalised), not more weights.

## 11. Files

Created: `roli_agent/recipes/adapt.py`, `roli_agent/scripts/replay_adapt.py`, `roli_agent/tests/test_recipes_adapt.py`, `roli_agent/eval/2b2_live_2026-11-02_2c.json` and `_2c_v2.json`, `nutrition_service/tests/fixtures/usda/food_{173468,169994,172232,170931,169997}.json` (real records, manifest updated), `menu_reader_eval/usda_matching/heldout_set_v3.csv`, `heldout_v3/results_2026-11-02.{json,md}`, `heldout_v3/review_notes.md`, `roli_agent/test_report_2C.txt`, this file.

Modified: `roli_agent/recipes/{models,match,pipeline,convert}.py`, `roli_agent/scripts/{measure_2b2,build_weights_table,score_matching}.py`, `roli_agent/recipes/assumed_weights.{csv,md}`, `SPEC_2C_menu_adapted_scenarios.md` (revision 3), `SPEC_2B_recipe_scenarios.md` (15.5), `heldout_CHANGELOG.md`, the project notes, tests.

Unchanged: the Phase 2A calculator, every missing-data safeguard, the user-facing reply, `code/`, the MCP wrapper, the LangSmith prototype. Secret scan: 0 hits outside `.env`. Live spend for this checkpoint: 0 Tavily credits (caches reused), about $0.17 on OpenRouter (five dishes plus the v3 scoring), roughly 300 USDA requests.

**Stopped here.**
