# Checkpoint 2D: restaurant portion models and the internal dish-comparison prototype

Date: 2026-11-03. Status: **built and tested; stopped for review. Everything internal: no Telegram, no user interface, no user-facing wording changed (the reply is byte-identical, test). Every portion-rule row and every weights row is unapproved.** Decisions recorded in `SPEC_2B_recipe_scenarios.md` section 15.7; as-built notes in `SPEC_2D_restaurant_portions.md` section 9 and `SPEC_2C_menu_adapted_scenarios.md` section 14; test output in `test_report_2D.txt`.

## 1. Summary

| Item | Result |
|---|---|
| Tests | agent **238 passed** (15 new in `test_recipes_2d.py`; 5 earlier expectations updated to the revised D20 and the per-plate basis, section 8), library 308 passed; Phase 2A calculator source untouched (asserted); the user-facing reply byte-identical with and without portioning (test) |
| Your decisions | D20 median built (`assumed_size_median`, range and labels kept, garlic's 3 g clove unchanged, a wedge never combined with a fruit); olive-oil cholesterol inference built as rule **I01**, outside the calculator, labelled, saturated fat from the Foundation record kept; D24 stays off; relevance labels independently reviewed; shishito, shiso and little gem get evidence-backed experimental rows, bottarga stays blocked and bounded only by labelled external evidence |
| Portion models | P1 (unit count read from the page's own method text, never from servings), P3 (key-ingredient weight: fish for crudo and salmon, tomatoes for the tomato starter), experimental P2 (plate weight; needs the whole recipe mass). Per-portion figures come from the unchanged Phase 2A calculator re-run at `servings = 1 / f`; a per-plate assumption counts once per plate, a recipe line scales with f; completeness inherited (a scaled subtotal stays a subtotal); the recipe-basis figures stay beside every result |
| Controlled validation first | 15 tests on recipes whose every line is a stated weight: f arithmetic for all three models, per-portion = total × f to 6 places, recipe basis untouched, P1 refuses without a unit count or when dough is reserved, P2 refuses an incomplete mass, P3 refuses an unweighed key line, menu-only lines never count as key weight or mass, unapproved rules stay `portion_proposed` |
| Five dishes (frozen inputs, no model or search variance) | 18 scenarios after the gate (the grilled gems recipe is now dropped before grading); **13 of 18 portioned** (3 refused for an unweighed key line or mass, 1 pizza for reserved dough, 1 crudo whose tuna "block" has no weight); every dish gets a per-portion interval for both nutrients |
| Comparison prototype | saturated fat first: **6 of 10 dish pairs decided clearly, 4 overlapping, 0 insufficient**; cholesterol: 7 clear, 3 overlapping. Against the drafted expectations (section 6): 10 of 10 dish-nutrient intervals overlap the expected range; **13 of the 20 pairs decided, 13 agree with the expected order, 0 contradict it**, 7 undecided (6 of those were expected to overlap) |
| Complete evidence | pairs complete at both bounds once I01 is accepted: **3 of 18** (Taste of Home margherita, two salmon recipes); 10 more are bounded only through labelled external evidence (section 5); published scenarios complete: still 0 (menu-only lines) |
| Cost and latency | the live pipeline with caches: 6-15 s per dish, 1-3 model calls, **$0.0016-0.0040 per dish**; the portion stage adds under 15 ms and the comparison under 1 ms per run; the frozen replay takes 80 s, all of it USDA lookups on a cold service cache; the independent review cost $0.19 (42 calls) |
| Corrections found on the way | per-plate assumption amounts were entered as whole-recipe amounts in 2C (understated per recipe serving by the serving count); "chicken stock" was treated as a flesh food and excluded; two crudo pages were rejected as unquantified because a leading bullet glyph hid the numbers; `recipe_scrapers` rewrites "One 12-inch pizza" into "12 servings" (a dimension read as a serving count) |

## 2. Your decisions, as implemented

**D20, revised.** `convert.median_whole_item`: a bare count on a record that lists the same item in several sizes (small/medium/large, or fruits by diameter) is weighed at the **median** per-item weight × the count, flagged `assumed_size_median`, with every label and weight kept in `portion_options` and the range in the reference ("ASSUMED size: median of 2 comparable whole-item sizes of USDA 167746 ('1 fruit (2-1/8" dia)' = 58 g; '1 fruit (2-3/8" dia)' = 84 g) -> 71 g per item"). A record with one sized label ("1 large" egg) takes it, flagged `single_labelled_size`. Unlike labels are never combined: a wedge or slice never enters (`NOT_A_WHOLE_ITEM`), and a sized label beside an unsized one of a different kind ("1 fruit" next to "1 large"; "1 cherry" next to "1 medium whole") leaves the line unknown as before. Garlic is untouched (its two clove labels weigh the same). Source-stated weights never carry the flag. In the five-dish run: 8 lines (carrot, scallions, orange, three lemons, eggs, radishes). The pair still carries the labelled spread around the median (`published_grams` records the median), so the sensitivity to the size assumption stays visible. A scenario complete only through a median is `basis: documented_inferences` and is not user-facing eligible.

**Olive oil, rule I01** (`inference.py`). When a line names olive oil and its USDA record's description starts "Oil, olive" and the record has no cholesterol row, the inference layer records: the field is absent (not zero) on record 748608; saturated fat 15.4 g/100 g is kept from that record; cholesterol inferred 0 mg/100 g; reference: cholesterol is an animal sterol, vegetable oils carry phytosterols, USDA 171413 reports 0 mg. The Phase 2A result is untouched (its exclusion stays); `InferredTotal` = known subtotal + 0 says whether the nutrient is complete *with* the inference; `Scenario.basis` and `completeness_basis` tell `complete_source_reported` from `complete_with_inferences`. Scope excludes sprays, blends, infused oils, dressings; sesame or canola oil would need their own rule. 15 lines in the five-dish run (13 extra-virgin olive oil lines plus 2 in the live run's new recipes). **Rule I02 (vinegar, same reasoning) is written and disabled** pending your approval; its absence keeps three salad recipes open for cholesterol (section 5).

**Relevance.** Frozen evaluation kept. The independent review (`menu_reader_eval/relevance/independent_review_2026-11-03.md`): Claude Sonnet 5.5, a different model family from the Gemini grader, judged all 42 frozen recipes without seeing the labels. Field-level: 16 full agreements, 26 with some disagreement, 12 preparation-related. Outcome-level (admitted as a scenario or excluded, which is what the pipeline acts on): **42 of 42 agree** after two label corrections the review forced (below). The field disagreements are wording: the reviewer calls a crudo whose garnishes differ from the menu's a `variant` with `similar` preparation where I wrote `same`/`same`; Python maps both to the same grade. **Material finding:** the SoPo Seafood and Sea Forager crudo pages do state quantities ("½ lb Bluefin Tuna", "6-8 oz bluefin"); a leading bullet glyph had hidden the numbers from the parser, so the gate rejected them as unquantified. Fixed (`parse.LEADING_BULLET`, the verbatim line is kept with the glyph, flag `leading_bullet_stripped`); labels v1.2 and v1.3 (the roasted-tomato soup now reaches the rubric, which rejects it); gate 42/42 on the re-frozen inputs. No further relevance phase is proposed.

**Specialty ingredients.** Three experimental rows from the 2C.1 evidence, `proposed_from_evidence_2c1`, composition proxies flagged, usable in experimental mode only: W28b little gem 90-180 g per head (romaine composition), W20b shishito 25-55 g per plate (hot green chili composition; count per plate assumed), W03c shiso 0.5-3 g per plate (basil composition; leaf weight estimated). The blocked rows W03b, W10, W20, W28 are unchanged and never used; a usable row wins a key tie over a blocked one. Bottarga stays blocked; in the comparison it only raises the crudo's upper bound through labelled external evidence (section 5), never a total.

## 3. The portion models on the five dishes (frozen inputs, experimental pairs)

| Dish | Recipe | Model, rule | f low-high | Saturated fat per portion, g | Cholesterol per portion, mg | Note |
|---|---|---|---|---|---|---|
| crudo | foodmymuse | P3 PR03 (45-110 g fish / 198 g) | 0.23-0.55 | 1.45-3.91 | 17-42 | bottarga unfilled: bounded externally (+0.38 g / +72 mg) |
| crudo | coleycooks | P3 PR03 | 0.20-0.49 | 1.50-3.68 | 17-42 | olives (tbsp) bounded externally |
| crudo | James Beard | P3 PR03 | 0.20-0.49 | 0.51-1.27 | 18-43 | jarred chiles bounded externally |
| crudo | twopurplefigs | P3 | refused | | | the tuna "block" has no weight: the key line is unweighed |
| gem salad | pinchandswirl | P2 PR04 (100-250 g / 506-866 g) | 0.20-0.29 | 4.64-8.95 | 4-13 | complete at both bounds for saturated fat; champagne vinegar cholesterol bounded at 0 externally |
| gem salad | cravingcalifornia, baked goat cheese | P2 | refused | | | an unweighed line (Greek yogurt; thyme, rosemary, half a baguette): the served mass is incomplete |
| tomatoes | thesophisticatedcaveman | P3 PR06 (120-250 g tomato / 1205 g) | 0.10-0.21 | 1.01-2.12 | 0 | red onion, fresh oregano bounded externally |
| tomatoes | chamoy | P3 PR06 | 0.18-0.37 | 0.82-1.72 | 0 | tamarind, chipotle, chips bounded externally |
| tomatoes | pluot | P3, P2 | refused | | | "3 large heirloom tomatoes" on a proxy: the tomato weight is unknown |
| pizza | King Arthur | P1 PR01 (k = 2, "divide the dough in half") | 0.25-0.50 | 5.41-10.82 | 22-45 | no stated diameter: no size adjustment; canned tomatoes and '00' flour (Foundation records lacking nutrients) bounded by SR Legacy siblings |
| pizza | abeautifulplate | P1 PR01 (k = 2, 10-inch rounds → 12-13 in) | 0.36-0.85 | 11.84-27.82 | 60-142 | dusting flour bounded externally |
| pizza | Taste of Home | P1 PR01 (k = 1, 13-inch circle) | 0.43-1.00 | **11.35-26.65** | **38-90** | **complete at both bounds with I01** |
| pizza | Food Network | P1 | refused | | | "cut the dough into 2 pieces and reserve 1 piece for another use": the list does not describe one unit |
| salmon | thishealthytable | P3 PR02 (113-227 g fish / 680 g) | 0.17-0.33 | 7.43-14.88 | 72-144 | optional herb toppings bounded externally |
| salmon | lecremedelacrumb | P3 PR02 | 0.17-0.33 | **4.47-8.95** | **56-114** | **complete at both bounds with I01** |
| salmon | mylatinatable | P3 PR02 (453 g) | 0.25-0.50 | **5.21-10.44** | **77-155** | **complete** (the chicken-stock fix resolved its last line) |
| salmon | Food Network | P3 PR02 (907 g) | 0.13-0.25 | 5.79-12.25 | 61-123 | milk (no record), lemon thyme, pattypan squash bounded externally |

Every f range spans a factor 2.0-2.4 (fish 113-227 g; a shared or whole pizza; 100-250 g of salad), so the portion uncertainty is the largest term in every error budget: for the three complete pairs the 2C assumption sensitivity is 0.002-0.31 g of saturated fat per serving against a per-portion spread of 4.5-15.3 g from the portion range alone. The ranking phase must say so.

## 4. The comparison prototype

Intervals per restaurant portion (saturated fat primary; experimental pairs; external bounds included and labelled):

| Dish | Sat fat g | Chol mg | Recipes (bounded) | Caveats |
|---|---|---|---|---|
| heirloom tomatoes | 0.82-2.23 | 0 | 2 (2) | external bounds; 1 recipe not portionable |
| bluefin crudo | 0.51-4.29 | 17-115 | 3 (3) | bottarga's bound (+0.38 g, +72 mg) is non-USDA evidence; assumption-driven in 2 recipes |
| little gem lettuces | 4.64-8.95 | 4-13 | 1 (1) | one recipe only; the tahini and pecorino fills are 60 % of the subtotal (assumption-driven) |
| king salmon | 4.47-14.89 | 57-155 | 4 (4) | 2 of 4 recipes bounded only externally |
| margherita | 5.41-27.85 | 22-142 | 3 (3) | 2 of 3 bounded only externally; "shared or whole" doubles the range |

Pairwise, saturated fat: tomatoes clearly below gem, salmon and pizza; crudo clearly below gem, salmon and pizza (margins 0.35, 0.18 and 1.1 g: the first two are flagged **narrow** against ranges several grams wide, and they rest on the bottarga upper bound); tomatoes vs crudo, gem vs salmon, gem vs pizza, salmon vs pizza overlap. Cholesterol: tomatoes clearly lowest; gem clearly below crudo, salmon and pizza; crudo, salmon and pizza overlap. No pair is `insufficient_evidence` once the external bounds are allowed; without them (USDA-only), 4 of 5 dishes would have no upper bound and 16 of 20 pairs would be undecided: that is the honest cost of the blocked and record-gap lines, and the reason the external-evidence tier exists.

Rules the prototype enforces: a dish's upper bound comes only from recipes that have one, the unbounded recipes are named, and an unbounded recipe whose lower bound already exceeds the bounded recipes' maximum withdraws the upper bound; a lower bound alone never ranks (verdict `insufficient_evidence` with the reason); every clear verdict reports its margin and inherits the caveats of both dishes; the main drivers (portion rule and f, the three largest assumed lines, inferences, external bounds) are listed per dish. The statement is internal wording.

## 5. Where the figures come from: assumptions, inferences, external bounds

| Layer | What | Count in the run | Review status |
|---|---|---|---|
| Phase 2A | source-stated weights and USDA values | 141 resolved lines of 272 | as before |
| D20 median (inference) | 8 lines | `assumed_size_median`, spread kept in the pair | your decision, implemented |
| I01 (inference) | 15 olive-oil lines, cholesterol 0 | labelled, outside the calculator | requested by you; wording awaits your sign-off |
| 2C assumptions (experimental) | 68 filled lines: G1 menu-only 40, G2 unquantified 17, G4 proxy count 5, G5 ambiguous measure 6 | per-plate rows now per serving | all rows unapproved |
| 2C unfilled | 54 lines | stay excluded from every total | |
| External bounds (comparison only) | 19 evidence rows: bottarga (INRAN, Foods 2020), vinegar cholesterol (USDA cider vinegar 0), USDA sibling records for lines whose own record lacks a nutrient (canned tomatoes, '00' flour, red onion) or a measure (herbs, yogurt, milk, chips, olives, chiles, flour for dusting, half a baguette, squash), amounts as ceilings | 10 of 13 portioned pairs use at least one | **never in a total; raise an upper bound only; amounts are my estimates, compositions are USDA except bottarga** |
| Portion rules | PR01-PR06 | all 13 portioned pairs | all `proposed_unreviewed`; evidence cited per row, none weighed |

The two material external bounds are bottarga (crudo cholesterol, +72 mg at the ceiling) and whole milk in the Food Network salmon (+2.3 g saturated fat per portion at the ceiling); the rest are under 0.5 g.

## 6. Evaluation against the expectations

`eval/expectations_2d_v1.{csv,md}`: per-portion ranges and an expected order for the five dishes, drafted by me from the dominant ingredients' USDA values and the proposed portion rules, **awaiting your review** (change a row and `scripts/evaluate_2d.py` re-scores in a second). Results (`eval/2d_evaluation_2026-11-03.json`): 10 of 10 modeled intervals overlap the expected ranges (4 are wider than expected, all because the portion range doubles them); 13 of 20 pairs decided, all 13 in the expected direction, 0 contradictions; of the 7 undecided, 6 were expected to overlap and 1 (gem salad vs pizza, saturated fat) was expected to be clear but overlaps because a shared pizza (5.4 g) can sit below a dressed salad (9 g). Plausibility, not just completeness, as you asked; the limits are that the expectations are mine and the live scenario count is small (1 recipe for the gem salad).

## 7. Cost and latency

Live run with warm caches (`eval/2b2_live_2026-11-03_2d.json`, `measure_2b2 --keep-cache --adapt --cold-only --portion`): per dish 6.0-15.1 s, of which relevance 2.8-4.5 s (one model call), matching 0-4.5 s (match cache; one call for new lines), conversion and calculation 1.2-2.8 s (USDA lookups), adaptation 5-15 ms, **portioning 2-12 ms**; 1-3 model calls and $0.0016-0.0040 per dish; 20-69 USDA requests per dish. The frozen replay (`scripts/replay_2d.py`) takes 80 s for five dishes, 78 s of it USDA lookups on a cold service cache; adaptation 0.03-0.5 s per dish, portioning and comparison under 0.1 s. The independent review: 42 calls, 54k + 8k tokens, $0.19, 108 s throttled to 20 requests per minute. Tavily: 0 credits (search cache).

## 8. Changes to earlier behaviour, and the tests that moved

- **Per-plate amounts** (`assumed_weights.csv` column `amount_basis`): 2C had entered restaurant-usage rows as whole-recipe amounts, so per recipe serving they were understated by the serving count (a 13.5 g drizzle over a 4-serving recipe became 3.4 g per serving). They now enter as per-serving amounts; count lines (G4) take the row per counted item × the stated count. Tests updated: `test_experimental_mode_fills_table_rows...` (pepper contribution × 4; oil `grams_in_recipe` 54 g for 13.5 g per plate), `test_the_generated_table_loads...` (33 rows; W03c wins the "shiso" tie).
- **D20 revised**: `test_dimension_labelled_sizes...` (lemon 71 g, eggs 150 g, options kept), `test_adapted_pair_bounds...` (1 blocked line instead of 3; two median spreads), `test_foundation_measure_names...` (orange median 65.5 g for a half; an unsized "1 fruit" beside sizes still blocks).
- **Flesh names**: "chicken stock", "fish sauce", "duck fat" are products, not flesh (`pipeline.is_flesh_name`); the mylatinatable salmon pair became complete.
- **Bullet glyphs** stripped before parsing, verbatim line kept.
- **Yield text under recipe_scrapers**: the JSON-LD `recipeYield` is preferred over the library's rewritten `yields()`; D15 then leaves "One 12-inch pizza" without a serving count as intended. Finding for later: three margherita pages state only a unit yield ("One 12-inch pizza", "8 slices", "12 items") and are therefore never calculated, though P1 would fit them exactly; a rule "a unit yield of k pizzas gives servings = k for the recipe basis" would admit them and is yours to decide.

## 9. Readiness for a first user-facing prototype

**Assessment: ready for an internal or invited-testers prototype that shows ranges and names its assumptions; not ready for public users.** What supports it: the arithmetic is tested and reproducible; every figure carries its provenance (source, inference, assumption, external bound, portion rule); the comparison refuses to rank on lower bounds and reports margins; on the five dishes it produced plausible magnitudes and no contradiction of the expected order; the full pipeline runs in 6-15 s per dish at under half a cent. What blocks public use, in order:

1. **Nothing is approved.** All six portion-rule rows and all 33 weights rows are unreviewed; the three complete pairs and all 13 portioned pairs rest on them. Approving or adjusting PR01-PR03 (pizza, fish main, crudo) and the five weight rows that drive the dishes (W05 pecorino, W08 tahini, W09 oil drizzle, W18 corn, W19 squash) is the shortest path.
2. **Portion ranges are a factor of two wide** and dominate every error budget. A dozen weighings (three pizzas, three salmon mains, three crudos, three salads at Flour + Water or comparable restaurants) would narrow PR01-PR04 more than any further code.
3. **Ten of thirteen portioned pairs are bounded only through external evidence** whose amounts are my ceilings. Users should not see a figure that depends on them without a label; the cleanest fix is the data: approve I02 (vinegar), decide the Foundation-record gaps (canned tomatoes, '00' flour, red onion: D24-style sibling selection or a measure), and resolve Greek yogurt.
4. **The gem salad rests on one recipe** and the tomato starter on two; two more calculable recipes per dish would make the between-recipe spread meaningful.
5. **User-facing wording** for ranges, caveats and the "modeled portion" status does not exist yet; the only user text is the Phase 2B statement.

Not blockers but worth a decision: the unit-yield rule for pizzas (section 8), the I01 wording, and whether the menu-wide ranking should use the pairwise verdicts as built.

## 10. For your review

1. The portion rules `recipes/portion_rules.csv` (six rows, evidence cited per row): approve, change or reject each; decide whether to fund weighings.
2. The weights rows that drive the five dishes (W05, W08, W09, W18, W19, W28b, W20b, W03c) and whether experimental mode may feed an invited-testers prototype.
3. Rule I01's wording and reference; rule I02 (vinegar) yes or no.
4. The expectations file (`eval/expectations_2d_v1.csv`): your numbers replace mine, then the evaluation re-runs.
5. The external-evidence table (`recipes/blocked_evidence.csv`): whether upper bounds from estimated amounts may enter an internal comparison at all, or only USDA-composition rows.
6. The relevance labels at v1.3 (42 rows; the review found no material disagreement left).
7. The unit-yield rule for pizza pages that state no serving count.

## 11. Files

Created: `roli_agent/recipes/{portions,compare_dishes,inference}.py`, `roli_agent/recipes/{portion_rules,blocked_evidence}.csv`, `roli_agent/scripts/{replay_2d,evaluate_2d,review_relevance_labels}.py`, `roli_agent/tests/test_recipes_2d.py`, `roli_agent/eval/{2d_controlled_2026-11-03.json,2d_controlled_2026-11-03.md,2d_evaluation_2026-11-03.json,expectations_2d_v1.csv,expectations_2d_v1.md,frozen_inputs_2d.json,2b2_live_2026-11-03_2d.json}`, `menu_reader_eval/relevance/{independent_review_2026-11-03.json,independent_review_2026-11-03.md,results_2026-11-03_gate_v1_2.json,results_2026-11-03_gate_v1_3.json}`, `roli_agent/test_report_2D.txt`, this file.

Modified: `roli_agent/recipes/{models,convert,adapt,pipeline,parse,extract}.py`, `roli_agent/recipes/assumed_weights.{csv,md}` (column `amount_basis`, rows W28b/W20b/W03c; no `approved_by` touched), `roli_agent/scripts/measure_2b2.py` (`--portion`), `roli_agent/scripts/eval_relevance_2c1.py` (unchanged code; run against the new frozen file), `menu_reader_eval/relevance/{relevance_set_v1.csv (v1.3),README.md}`, `roli_agent/SPEC_2D_restaurant_portions.md` (section 9), `SPEC_2B_recipe_scenarios.md` (15.7), `SPEC_2C_menu_adapted_scenarios.md` (14), the project notes, five tests listed in section 8.

Unchanged: the Phase 2A calculator and its completeness logic, D23, the blocked rows, every `approved_by` field, the user-facing reply, `code/`, the MCP wrapper, the LangSmith prototype. Secret scan: 0 hits.

**Stopped here.**
