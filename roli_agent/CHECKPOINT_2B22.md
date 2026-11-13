# Checkpoint 2B-2.2: D22 as a constrained policy, held-out set v2, Phase 2C specification revision 2

Date: 2026-11-02. Status: **stopped for review. Phase 2C not built.** Decisions recorded in `SPEC_2B_recipe_scenarios.md` section 15.4; the revised Phase 2C specification is `SPEC_2C_menu_adapted_scenarios.md`; the weights table is `roli_agent/recipes/assumed_weights.csv` (generated, classes computed).

## 1. Summary

| Item | Result |
|---|---|
| D22 built | `roli_agent/recipes/equivalence.py`: deterministic, six conditions, applied only when the chosen record cannot weigh the line; 6 tests; **174 agent tests pass**, 308 library tests pass unchanged |
| D22 on the documented olive-oil case | **refused, on USDA's own numbers**: "Oil, olive, extra virgin" (Foundation 748608) reports 15.4 g saturated fat per 100 g and no cholesterol row; "Oil, olive, salad or cooking" (SR Legacy 171413) reports 13.808 g and 0 mg. 11.5 % apart and one value missing. Your caution about grade differences was right for this pair |
| Olive-oil lines nevertheless weighed | the Foundation record carries one measure of its own, "100 milliliter = 90.7 g"; millilitre measures are now read as density sources (D4, the record's own measure). 15 olive-oil lines in the saved run get grams. They stay incomplete for cholesterol, because that record reports none |
| Controlled replay (identical saved inputs, no search, no LLM) | 18 scenarios, 221 lines: baseline 115 resolved; + millilitre density 115 resolved (15 lines gain grams, still blocked on cholesterol); + D22 strict 116 resolved, 1 substitution (mirin); relaxed tolerance adds nothing. 0 complete under every policy |
| Held-out set v2 | v1 preserved; v2 = 54 rows with a changelog (one label change, ghee, after live record verification; foie gras wording made explicit; 14 consequential-proxy rows added; `consequence` column). Scored once: 17 direct, 23 acceptable proxies, 5 label disagreements, 3 false matches, 6 unresolved; high-consequence false-match rate 7.3 % (3 of 41) |
| Phase 2C specification revision 2 | all ten refinements addressed; classes computed, not typed; 28-row table with review status, three rows blocked; 30 % as a diagnostic flag with absolute sensitivity; recipe basis only; Phase 2D defined |
| Weight assumptions still unverified | every `proposed_unreviewed` row (11) and every `blocked` row (3); the 14 `usda_measure` rows have verified gram weights but their restaurant usage is assumed (section 6) |

## 2. D22: the policy as built

`EquivalentRecordPolicy.find(line, decision)` runs only after `convert_with_portions` failed for a volume line. A replacement is accepted only if all of these hold:

1. it is in the candidate list USDA returned for that ingredient's search (decisions now carry `candidates`; nothing from memory);
2. same food: identical first two comma-separated description words ("Oil, olive");
3. same preparation state (Phase 2A classifier) **and** same physical-form words ("with peel", "drained", "canned", "shredded", … must match on both descriptions; added after the replay showed "Oranges, raw, all commercial varieties" turning into "Oranges, raw, with peel");
4. both records report both nutrients and the values are equivalent: |Δ| ≤ max(0.1 g, 5 %) for saturated fat and max(1 mg, 5 %) for cholesterol. Grade and varietal words are judged by this test, never assumed irrelevant;
5. the replacement converts the line (has a measure for that unit);
6. the line is a **volume** (`allow_whole_items=False` by default): otherwise a sibling record with one typical "1 fruit" label resolves a count that D20 left unresolved on the chosen record (the replay showed "1/2 orange" moving to the California valencia record, 121 g per fruit). Whole-item weights remain a D20 / Phase 2C matter.

The substitution is recorded on the decision (`source: "d22"`, `substituted_for`, a reason naming both records) and on the line (`d22_equivalent_record`); the scenario carries `d22_equivalent_record:<name>`; the estimate notes list every substitution.

### 2a. Tests (`test_recipes_equivalence.py`)

| Test | Shows |
|---|---|
| the real olive-oil records are not equivalent | 15.4 vs 13.808 g and a missing cholesterol row -> refused; log says why |
| extra virgin converts from its own millilitre measure | 2 tbsp -> 26.82 g from "100 milliliter = 90.7 g" (0.9070 g/ml), flagged `portion_derived_volume` |
| substitution only when all conditions hold | with the Foundation record made equivalent (values copied) and stripped of measures, the SR Legacy sibling from the same list is used: 27 g, `substituted_for` 748608; the sesame-oil candidate is never considered |
| no substitution across states or unrelated foods | cooked chinook never takes the raw chinook sibling; pink salmon (0.971 g) never replaces chinook (3.214 g) although both are "Fish, salmon"; romano never considered for oil |
| physical form | an orange "with peel" never replaces a peeled-orange record; by default count lines are not eligible at all |
| inert when nothing needs a measure or when disabled | explicit weights, unquantified lines, `enabled=False`: no USDA call |
| candidates carried on decisions | the matcher stores USDA's list on every decision |

### 2b. Controlled comparison on identical saved inputs

`roli_agent/scripts/replay_d22.py` rebuilds the 18 calculated scenarios of the 2B-2.1 run (`2b2_live_2026-11-02.json`: same recipes, same parsed lines, same record choices) and re-runs conversion and the calculator under four policies; USDA live, no search, no model. Output: `roli_agent/eval/d22_replay_2026-11-02.json`.

| Policy | Resolved lines | Complete scenarios | Substitutions | Lines changed vs A | no USDA portion | nutrient not reported |
|---|---:|---:|---:|---:|---:|---:|
| A: 2B-2.1 behaviour | 115 / 221 | 0 | 0 | 0 | 63 | 8 |
| B: + millilitre measures as density (D4) | 115 / 221 | 0 | 0 | 15 | 48 | 23 |
| C: B + D22 strict (**proposed**) | 116 / 221 | 0 | 1 | 16 | 47 | 23 |
| D: B + D22 with 15 % tolerance and a missing nutrient tolerated | 116 / 221 | 0 | 1 | 16 | 47 | 23 |

Reading. (B) The 15 olive-oil lines gain grams from their own record but move from "no USDA portion" to "nutrient not reported": the Foundation extra-virgin record has no cholesterol row, so the line is resolved for saturated fat and unresolved for cholesterol. (C) D22 strict substitutes exactly one line, "2 tbsp mirin": "Alcoholic beverage, wine, dessert, sweet" (173176, no spoon measure) -> "Alcoholic beverage, wine, cooking" (169070, "1 tsp = 4.9 g"), both 0 g / 0 mg. (D) Relaxing the tolerance changes nothing, because D22 is consulted only when the record cannot weigh the line, and after (B) the olive-oil record can. The cholesterol gap on olive oil is therefore outside D22 as you scoped it; closing it would need a different rule ("a same-food sibling may supply a nutrient the chosen record does not report when the reported nutrient is equivalent") and is listed as decision D23 in section 7, not built. No policy makes any scenario complete.

## 3. Held-out evaluation: v1 preserved, v2 created

- `heldout_set.csv` (v1, 40 rows) and `heldout/` (its results, review notes) are untouched.
- `heldout_set_v2.csv` (54 rows) with `heldout_CHANGELOG.md`: mascarpone kept as a false match; gorgonzola kept as a proxy; ghee relabelled direct after the record was verified live through the nutrition service (USDA 173412 "Butter oil, anhydrous": 61.924 g saturated fat, 256 mg cholesterol per 100 g; the same search also returned 171314 "Butter, Clarified butter (ghee)", found after v2 was frozen, so it is noted for v3); foie gras wording made explicit ("seared, fresh") with the label unchanged, plus a separate canned-pâté row; 14 rows added for the stringent review (cured tuna roe, marsala, shaoxing, vermouth, coppa, soppressata, mortadella, lardons, pecorino toscano, asiago, scamorza, robiola, manchego, the pâté); a `consequence` column (41 high, 9 medium, 4 low); the scorer reports the false-match rate among high-consequence rows. The free-text notes cell of the ghee row was corrected after scoring started (values cited only as verified); patterns unchanged; both hashes are in the changelog.
- Scored once (`heldout_v2/results_2026-11-02.{json,md}`; 10 LLM calls, 67 s, $0.029). Verdicts kept; the reading is in `heldout_v2/review_notes.md`:

| Verdict | Count | What they are |
|---|---:|---|
| direct, correct | 17 | incl. mortadella, chorizo, egg yolk, salt cod, octopus, the canned pâté row |
| proxy, acceptable | 23 | bottarga (both kinds) -> roe/caviar; marsala, shaoxing -> cooking wine / sake; guanciale, pancetta, lardons -> cooked bacon; pecorino toscano, manchego -> romano; asiago -> parmesan; scamorza -> low-moisture mozzarella; robiola -> brie; gorgonzola -> blue |
| label disagreement | 5 | ghee -> the ghee record 171314 (model right, label frozen too early); bresaola -> cured dried beef as direct; lardo -> lard as direct (label's "proxy" stands); dry vermouth as direct; soppressata -> salami as proxy (model under-claimed) |
| false match | 3 | mascarpone (retained, a real error); 'nduja -> salami (a label gap: salami is a reasonable proxy the pattern did not list); fresh foie gras -> canned pâté, labelled proxy by the model (preparation-dependent, your call) |
| unresolved | 6 | prosciutto and speck (the model's query returned no USDA candidates this run; v1 resolved both), coppa, duck fat, squid ink, bone marrow |

Model variance between v1 and v2 on identical rows is real and recorded (ghee 173412 vs 171314; prosciutto resolved vs not).

## 4. Phase 2C specification, revision 2

`SPEC_2C_menu_adapted_scenarios.md`. Point by point against your ten refinements:

1. Classes `zero_nutrient` / `low_impact` / `substantial` are computed from the matched record's per-100 g values and the upper-bound weight (`build_weights_table.classify`; the builder recomputes every time); a record missing a nutrient is `nutrient_missing` and can never be zero or low-impact. Typed labels are ignored.
2. All 28 rows regenerated from live USDA portions; `basis` separates verified USDA measures from proposed restaurant usage; `review_status` per row.
3. W01 chives computes to `low_impact` (0.0044 g at 3 g), not zero; W11 grapes computes to `substantial` (0.0265 g) under the floor; W15 black pepper (0.032 g) and W16 red pepper flakes (0.059 g) compute to `substantial`. The same test reclassifies mint, parsley, grapes, lemon juice, capers, corn, squash and pluot as `substantial`: under a 0.005 g / 0.5 mg floor only chives, basil, lemon zest and salt stay below it.
4. W10 (bottarga / raw roe), W20 (shishito / green chili) and W28 (little gem / romaine) are `blocked_questionable_proxy`: never a source, kept for investigation.
5. `proposed_unreviewed` rows stay in the table and cannot reach any figure until `approved_by` is filled; the agent may propose revisions with references.
6. Assumed share above 30 % is the diagnostic flag `assumption_driven`, never a discard; absolute `sensitivity` (high minus low) is printed beside it; a zero known subtotal gives `null` with fixed wording; incomplete nutrients are reported beside the share.
7. One published scenario yields one low/high **pair** with shared provenance; between-recipe spread and within-recipe sensitivity are reported separately and never merged; a pair is never counted as two recipes.
8. "Complete for the modeled ingredient list (N assumed lines)", never a verified restaurant total.
9. Internal only; `servings_basis: "recipe"`; full-recipe totals preserved; nothing presented as a restaurant serving.
10. Phase 2D defined: purpose, interface to 2C (`servings_basis: "restaurant_model"`, portion rule IDs, low/high), a reviewed portion-rule table, and an evaluation plan (20 weighed dishes, error per dish type, sensitivity of portion rule versus 2C assumptions, no user exposure before characterisation).

## 5. Files

Created: `roli_agent/recipes/equivalence.py`, `roli_agent/tests/test_recipes_equivalence.py`, `roli_agent/scripts/replay_d22.py`, `roli_agent/scripts/build_weights_table.py`, `roli_agent/recipes/assumed_weights.{csv,md}`, `roli_agent/eval/d22_replay_2026-11-02.json`, `nutrition_service/tests/fixtures/usda/food_748608.json` and `food_1750351.json` (real records, manifest updated), `menu_reader_eval/usda_matching/heldout_set_v2.csv`, `heldout_CHANGELOG.md`, `heldout_v2/results_2026-11-02.{json,md}`, `heldout_v2/review_notes.md`, `roli_agent/test_report_2B22.txt`, this file.

Modified: `roli_agent/recipes/{models,match,pipeline,convert}.py` (candidates on decisions; policy wiring; millilitre density), `roli_agent/scripts/score_matching.py` (consequence reporting), `roli_agent/SPEC_2C_menu_adapted_scenarios.md` (rewritten), `SPEC_2B_recipe_scenarios.md` (15.4), the project notes, one test's leak check made precise (`"999 kcal"` instead of `"999"`, which an FDC ID now matched).

Unchanged: the Phase 2A calculator and every missing-data safeguard (no scenario became complete anywhere), `code/`, the MCP wrapper, the LangSmith prototype. Secret scan: 0 hits outside `.env`.

## 6. Which weight assumptions remain unverified

| Status | Rows | What is verified / what is not |
|---|---|---|
| `verified_usda_measure; restaurant usage assumed` | W01 chives, W02 basil, W03 mint/shiso, W04 parsley, W11 grapes, W12 lemon juice, W13 zest, W14 salt, W15 pepper, W16 flakes, W18 corn, W19 squash, W23 capers, W25 egg yolk | the gram weight of each measure is USDA's; that a restaurant uses that measure (one tablespoon of chives, not three) is **not** verified |
| `proposed_unreviewed` | W05 grated hard cheese, W06 mozzarella per pizza, W07 sesame, W08 tahini, W09 oil drizzle, W17 bread, W21 pluot size, W22 pistachios, W24 olives, W26 pancetta, W27 cream | the restaurant-usage ranges are the agent's drafts with no external reference; the `substantial` ones among them (all but W21) move the numbers most and need your approval before any use |
| `blocked_questionable_proxy` | W10 bottarga/raw roe, W20 shishito/green chili, W28 little gem/romaine | not usable until evidence or a reviewed weight exists |

## 7. Decisions needed

| # | Question | Recommendation |
|---|---|---|
| D22 | confirm the policy as built (six conditions, volume lines only) and the replay result; confirm the millilitre-density reading (D4) | confirm both |
| D23 (new) | olive oil's missing cholesterol row: allow a same-food sibling (same head, state and form, equivalent on the reported nutrient) to supply a nutrient the chosen record does not report, flagged? Without it the 15 olive-oil lines stay incomplete for cholesterol although every olive oil reports 0 mg | adopt, with the same guards as D22 and a `d23_nutrient_from_sibling` flag; the alternative is the D19 selection preferring the SR Legacy record, which you ruled out when the foods differ |
| held-out v3 | accept the four label readings in `heldout_v2/review_notes.md` ('nduja/salami, ghee 171314, bresaola direct, vermouth direct); decide the foie-gras pâté proxy; decide whether "no candidates" rows get a deterministic plain-name retry | accept the four; reject the pâté proxy for fresh foie gras; add the retry |
| 2C | review the revision-2 spec, the class floor, the 30 % flag, Phase 2D; approve or delete each `proposed_unreviewed` row | per the spec's section 12 |

**Stopped here. Phase 2C, Phase 2D, menu-wide ranking, Telegram and the conversational interface are not started.**
