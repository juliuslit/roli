# Checkpoint 2C.1: input completeness and relevance hardening

Date: 2026-11-03. Status: **built and tested; stopped for review. Nothing user-facing changed. Phase 2D is specified (`SPEC_2D_restaurant_portions.md`), not built. Menu-wide ranking, Telegram and the conversational interface not started.** Decisions recorded in `SPEC_2B_recipe_scenarios.md` section 15.6; 2C spec at revision 4 (section 13); test output in `test_report_2C1.txt`.

## 1. Summary

| Item | Result |
|---|---|
| Tests | agent **223 passed** (37 new in `test_recipes_2c1.py`; 3 earlier expectations updated, listed in section 7), library 308 passed; Phase 2A calculator untouched; published scenarios and the reply byte-identical guards unchanged |
| Controlled evaluation (section F) | same 19 published scenarios, same recipes (re-ingested offline from the caches), same frozen USDA decisions per verbatim line; no Tavily, no LLM. **Resolved lines 120 -> 141 of 286; household-measure gaps 62 -> 40** (31 unweighable + 9 proxy counts refused by D21); no previously resolved line lost; 3 lines changed grams, all to a weight the page itself states |
| Complete scenarios | published: **0 of 19** before and after, for both nutrients. Adapted pairs (experimental, all rows): **0 of 19** at either bound; 1 pair saturated-fat-complete at the high bound (Taste of Home margherita). Under the proposed D24 at a 15 % tolerance: that pair becomes complete for both nutrients (4.27 g / 15 mg per recipe serving); still 0 published complete |
| Record selection (B) | the 13 extra-virgin olive-oil lines can be resolved only by a same-food record whose saturated fat differs by 1.592 g/100 g (10.3 %); built as policy **D24, off by default**; your decision on the tolerance (section B) |
| Relevance (C) | frozen set of 42 real recipes with reference labels (`menu_reader_eval/relevance/relevance_set_v1.csv`, v1.1, labels drafted by me, awaiting your review); Python gate 42/42; rubric grade accuracy **99.4 %** over 5 live runs; the two grilled little-gem recipes are now rejected by a deterministic method-text rule before any model call |
| Blocked ingredients (D) | evidence gathered for bottarga, shishito, shiso, little gem (section D); **no row approved**; proposed treatment per ingredient for your decision |
| Counts (E) | the 2C checkpoint's "99 unfilled + 4 unpaired" double-counted: the 99 already included the 4. Reconciled denominator: 165 blocked lines = 66 filled + 95 unfilled in pairs + 4 in the unpaired recipe. The summary now carries the three terms and asserts they add up |
| Spend | 25 model calls (relevance runs, about $0.05); a few hundred USDA requests (deterministic data, no credits); 0 Tavily credits; 13 USDA records captured as fixtures |

## 2. Requirement A: household-measure conversion

### What the 47 unresolved measure lines actually were

Read against the live USDA portion labels of their records (all 40 records probed), the "47 measures" of Checkpoint 2C fell into seven causes, four of which are deterministic parsing or label-reading defects rather than missing data:

| Cause | Lines | Fix | Example |
|---|---:|---|---|
| two labels, one weight per unit, treated as ambiguous | 8 garlic + 1 thyme | labels whose per-unit weights agree within 0.5 % are one measure (`same_weight`); "N garlic cloves" and "1 small garlic clove" now parse `cloves` as the unit (`unit_from_name`), the size word kept as a note and flagged `portion_size_word_unmatched` when the record has no such size | "2 cloves garlic": '1 clove' = 3 g and '3 cloves' = 9 g -> 6 g |
| density derivable from another measure, but blocked by a label spelling or a modifier | 9 | "fl oz" labels read as fluid ounces; a label whose extra words the line itself uses may serve as the density source ('1 cup cherry tomatoes' for "1 pint cherry tomatoes"); the 2 % tolerance from 2C applies | mirin by the tablespoon from '1 fl oz' = 29.5 g; honey, miso, sugar by the spoon |
| misspelt unit | 3 | a typo table (`tabelspoons`, `tabespoons`, `teaspon`, ...) flagged `unit_typo_corrected`; a unit written twice ("2 tsp tsp pepper") flagged `unit_repeated` | "1-2 tabespoons olive oil" -> 20.25 g |
| a weight the page states beside the measure, ignored | 3 (previously converted by volume, now by the page's own gram figure) | "(232g)", "(38g)", "(300 g)" on a volume line are the line's total, flagged `embedded_weight_after_measure`; "(about 6 oz)" also, flagged approximate; a note with other words is ignored | "2 cups (232g) '00' flour" -> 232 g (was 2 cups of a proxy flour: unweighable) |
| a cooking word inside a product name | 1 | a name ending in "oil" is `as_used` whatever precedes it | "toasted sesame oil" was declared cooked and excluded as `preparation_unresolved` (mis-reported as a nutrient gap) |
| a sub-recipe reference line | 1 | "1 recipe pizza dough, recipe follows" is excluded from the calculator as `not_an_ingredient` when the page says the components follow; a reference to a recipe elsewhere stays an unresolved gap | Food Network margherita: the dough's own lines were already in the list |
| genuinely no usable label (whole lemons, sized counts, two differing labels, records without measures) | the rest | not converted in the published scenario (D20); handled in the pair where the record's own labels bound the answer (below) | "1 lemon" (58 g and 84 g fruits), "1 tsp dried oregano" (leaves 1 g, ground 1.8 g) |

Also built: a "plus" compound split ("Grated zest of 1 small lemon, plus 1 tablespoon lemon juice" becomes two lines, both keeping the verbatim text); the blocker category is now decided from the calculator's own exclusion codes, so a preparation problem is never reported as a nutrient gap.

### Garlic cloves and whole lemons, as asked

- Garlic: 8 lines resolved, all from the record's own '1 clove' = 3 g, no assumption. "1 small garlic clove" takes the same 3 g with the size word recorded as unmatched (the record has one clove size).
- Lemons: the lemon record lists two fruits by diameter (2-1/8" = 58 g, 2-3/8" = 84 g) and no size word. A dimension now counts as a size label when the record offers more than one whole item, so "1 lemon" stays `portion_size_unspecified` in the published scenario (D20) and the pair carries 58-84 g (G3). "1 medium lemon" stays unspecified too: the line's word matches no label. Zested-only lemons are weighed as whole fruit (0 g / 0 mg either way).

### Two new pair-level sources, both from the record's own labels (spec 2C section 13)

- **G5 measure-ambiguous**: the line's unit matches several labels that weigh differently (oregano leaves vs ground, bread cubes vs crumbs, brown sugar packed vs unpacked, pepper ground vs whole, cream whipped vs fluid). The converter records the candidate labels; the pair takes the smallest as low and the largest as high; never averaged; the published line stays unknown. 6 lines in the run.
- **G3 from dimension sizes and single sized labels**: lemons (above); "3 hard-boiled eggs" on a record whose only whole item is '1 large' = 50 g gives low = high = 150 g, noted as a single labelled size. 8 G3 fills in the run (4 before).

### What remains unweighable (40 lines), by kind

| Kind | Lines | Why no code change can weigh them |
|---|---:|---|
| sized count, line names no size (G3 in the pair) | 8 | carrot, scallions, orange, lemon x3, eggs, radishes: D20 |
| two differing labels (G5 in the pair) | 6 | oregano x2, pepper, bread, brown sugar, heavy cream |
| the record has no measure for the unit | 17 | Greek yogurt x3 (USDA lists no household measure for 171304, and the Foundation twin lists only RACC), olives by the spoon (record lists olives), jarred chiles (only "cup drained"), thyme and rosemary sprigs, half a baguette, a tuna "block", a bunch of basil, pattypan squash by count (only "cup slices"), a shallot (only "tbsp chopped"), tamarind paste on the raw-fruit record, fresh oregano on the dried record, tomato concasse, a handful of chips, red onion by the cup on the Foundation record |
| count on a composition proxy, refused (D21) | 9 | little gem heads x3, heirloom tomatoes, pluots, chipotle, a pinch of flakes, pinches of salt, a bunch of lemon thyme |

The 17 "no measure" lines are where USDA has nothing for the unit; only a reviewed weight row or a different record could help, and for Greek yogurt not even that (no record carries a cup).

## 3. Requirement B: record selection and per-nutrient completeness

### The 23 (now 26) nutrient-gap lines, by record

| Record | Lines | What is missing | Same-food candidate in USDA's own list for the saved query |
|---|---:|---|---|
| 748608 Oil, olive, extra virgin (Foundation) | 13 | cholesterol row | 171413 Oil, olive, salad or cooking (SR Legacy): 13.808 g / 0 mg; **saturated fat 1.592 g/100 g lower (10.3 %)** |
| 172240 Vinegar, red wine; 172241 Vinegar, balsamic (SR Legacy) | 6 (+1: the typo'd balsamic line now converts and lands here) | cholesterol row (saturated fat is 0.0) | cider and distilled vinegar report both (0 / 0) but are different foods by name; no same-head candidate |
| 790577 Onions, red, raw (Foundation) | 2 | both nutrients | 170000 Onions, raw (SR Legacy) reports both (0.042 g / 0 mg) and has cup measures, but "Onions, red" ≠ "Onions, raw" by the two-word rule |
| 2685578 Tomatoes, whole, canned (Foundation) | 1 | both | 170051 Tomatoes, red, ripe, canned, packed in tomato juice (SR Legacy) reports both; different head words |
| 790018 Flour, wheat, all-purpose, unenriched, unbleached (Foundation, proxy for '00' flour) | 1 (new: the 232 g line now converts) | a nutrient row | none with the same head |
| 171016 Oil, sesame (SR Legacy) | 0 now | it reports both; the line was mis-attributed (section A) | |

### D24, built and evaluated, off by default

`roli_agent/recipes/completeness.py`, `CompleteRecordPolicy`: when the chosen record lacks a tracked nutrient, choose instead, **at selection**, a record from the same USDA candidate list that names the same food (first two description words), the same state and physical form (the D22 word rules), reports both nutrients, and whose saturated fat is within a tolerance of the original's (|Δ| ≤ max(0.1 g, tolerance × the larger value)). The whole line then uses that one record: a household measure is re-weighed on it (grams and nutrients always from the same record; a test asserts the EVOO line's reference no longer mentions 748608). Nothing is borrowed between records (D23 intact). The Δ is recorded on the decision (`saturated_fat_delta_per_100g`), the decision says `source: "d24"` and `substituted_for`.

| Tolerance | Lines resolved | Effect on the figures |
|---|---:|---|
| 5 % (the D22 value; the default when enabled) | **0**: EVOO refused (10.3 %), every other gap has no same-food candidate | none |
| 15 % | **13** (all EVOO lines, 10 scenarios) | each tablespoon of EVOO carries 0.215 g less saturated fat (1.86 g instead of 2.08 g); per recipe serving the change runs from 0.01 g (1 tsp over 4) to 0.4 g (1 cup over 4); cholesterol becomes 0 mg reported instead of unreported |

Observed only, the policy costs one nutrient lookup per matched line; switched off it costs nothing (test). It is **not enabled**. The question for you: is a 10 % difference in saturated fat between USDA's EVOO analysis (2019 Foundation samples) and its older generic olive-oil record "sacrificing saturated-fat accuracy"? Nothing resolves the vinegar, red-onion and canned-tomato cases without a looser food-identity rule, which I do not recommend.

### Per-nutrient completeness

Tracked separately on every scenario and pair. Published: 19/19 incomplete for both nutrients before and after. Pairs (experimental): 1 saturated-fat-complete at the high bound (Taste of Home margherita: 4.44 g per serving with cholesterol unreported for its EVOO); under D24 at 15 % it is complete for both (4.27 g / 15 mg per sixth of the recipe) and no pair is saturated-fat-only.

## 4. Requirement C: relevance

- **Frozen set**: `menu_reader_eval/relevance/relevance_set_v1.csv` (42 recipes, the ones actually read for the five dishes; recipes themselves frozen in `roli_agent/eval/frozen_inputs_2c1.json`, re-ingested offline from the caches, sha256 ec5410…). Reference columns: gate, dish type, preparation, course, grade, hard exclusion, rationale. **The labels are my draft and need your review**; one label was changed after the first gate scoring and is recorded with both hashes in the README.
- **Deterministic exclusion**: `relevance.cooked_main_ingredient`: for a raw-type menu dish (crudo family, or a leaf-salad head word with no cooking word in the menu's own text) a method sentence that contains a base-form cooking verb (grill, char, roast, bake, sear, fry, cook, …) and the main ingredient word (lettuce, gems, romaine; tuna, fish, …) is a hard exclusion before any model call. Base forms only, so "top the lettuce with the toasted seeds" is not cooking the lettuce; "Baked Goat Cheese With Garden Lettuces" passes (the cheese is baked, the leaves are not). On the real cached pages exactly the two grilled little-gem recipes and the braised-lettuce "cookies" page trip it. The rubric prompt now receives the method sentence as evidence and is told that the method, not the title, decides.
- **Results** (5 live runs, temperature 0): gate 42/42 against the reference; rubric grade accuracy 164/165 run-recipe pairs (the miss: "King Salmon en Papillote" graded low once); 21 of 33 recipes gave the identical three answers in all 5 runs; the rest alternate same/variant or same/similar on salmon and salad recipes, which Python maps to the same grade. The admission of the grilled recipes can no longer vary with the model.

## 5. Requirement D: the four blocked ingredients (evidence, limits, proposed treatment; nothing approved)

Composition (per 100 g) and portion weight are kept apart. "Verified" means I read the number on the source page today; the search-engine summaries I could not open are not cited.

| Ingredient | Composition evidence | Portion-weight evidence | Limits | Proposed treatment (for your decision) |
|---|---|---|---|---|
| **Bottarga** (salted, dried mullet roe) | INRAN table via my-personaltrainer.it, "Cefalo muggine, uova (bottarga)": lipids 25.7 g, cholesterol 440 mg, saturated fat *not given* (verified). Foods 2020 (PMC7600528, Mugil cephalus bottarga, Sardinia): lipid 7.5 g, cholesterol 722 mg/100 g, saturated 14.58 % of fatty acids (verified, Tables 1 and 6). Sources disagree threefold on fat and nearly twofold on cholesterol | none for a shaved garnish; the 2C row proposes 3-10 g | no source gives saturated fat in g/100 g; the published values span 7.5-25.7 g lipid and 440-722 mg cholesterol; USDA's raw mixed roe (1.456 g / 374 mg) is a different product | keep blocked. If you want a modeled range: a cholesterol band of 440-722 mg/100 g from the two sources with saturated fat from the Foods 2020 share (14.6 % of 7.5 g ≈ 1.1 g) as an explicitly experimental composition row, never approved-mode; weight stays a separate row |
| **Shishito** | MEXT Standard Tables (八訂 増補2023), item 06093 ししとう 果実 生: fat 0.3 g, cholesterol "(0)" (estimated zero), refuse 10 % (verified on fooddb.mext.go.jp); saturated fatty acids on a separate tab I could not open | 4.4 g edible per pepper, from a Japanese nutrition site citing the same tables (verified on the page, not on MEXT) | the saturated-fat figure is unverified (third-party sites give ≈ 0.03 g); the USDA proxy "Peppers, hot chili, green, raw" is a different pepper but reports 0.021 g / 0 mg | composition: either the MEXT record as a *non-USDA* source (new source kind, needs a decision: the nutrition service is USDA-only by design) or keep the USDA green-chili proxy as a declared composition proxy; weight: 4-5 g per pepper, count unknown on the plate (6-12 peppers is a guess) |
| **Shiso** | MEXT item 06095 しそ 葉 生: fat 0.1 g, cholesterol "(0)", refuse 0 % (verified) | no per-leaf weight found in a primary source; typical leaves are small (under 1 g) but that is an estimate | saturated fat unverified; no USDA record at all | composition negligible by any source; the blocker is the weight. A garnish row of 1-3 leaves at ~0.5-1 g each would be `negligible` by the class rule; still needs your approval |
| **Little gem** | no national table entry found (CoFID, AUSNUT, NEVO); retail labels 0.02-0.1 g saturated fat, cholesterol 0 or not determined; romaine (USDA 169247) is the natural composition proxy | retail packs: 180 g per 2-pack (≈ 90 g per head), 190-229 g per 2-pack, single heads listed at 136-180 g; so one head ≈ 90-180 g | labels, not analyses; head weight varies twofold | composition: romaine as a declared proxy (saturated fat 0.03 g / 0 mg, `low_impact`); weight: 90-180 g per head as a proposed row, experimental only; heads per plate unknown |

## 6. Requirement E: the counts

Old run (`2b2_live_2026-11-02_2c_v2.json`, experimental): 165 blocked lines in the 19 calculated published scenarios = 66 filled + 95 unfilled inside pairs + 4 unfilled in the one scenario without a pair. The checkpoint sentence "99 unfilled lines + 4 in the unpaired recipe" counted the 4 twice; 99 was already the sum. The 47 "measure" lines were the `no_usda_portion` lines unfilled inside pairs (of 53 such published lines: 4 filled by G3, 2 in the unpaired scenario). `InternalSummary` now carries `n_blocked_lines`, `n_unfilled_in_pairs`, `n_unfilled_no_pair`, asserts `filled + in_pairs + no_pair = blocked`, and prints the three terms.

## 7. Requirement F: controlled evaluation

Inputs frozen by `scripts/freeze_inputs_2c1.py` (offline: search cache, page cache, extraction cache; a page-cache miss answers 404, as the page failed before); replayed by `scripts/replay_2c1.py` (frozen decision per verbatim line; candidate lists re-read from USDA for the saved query because the older match cache stored none; USDA records live). Output `roli_agent/eval/2c1_controlled_2026-11-03.json`.

**Line states, 19 published scenarios** (before = the saved 2C run; after = current code; D24 column = after with the policy applied at 15 %):

| State | Before | After | After + D24 15 % |
|---|---:|---:|---:|
| resolved | 120 | **141** | 156 |
| household measure unweighable | 53 | 31 | 31 |
| count on a proxy refused (D21) | 9 | 9 | 9 |
| record lacks a nutrient | 25 | 26 | 11 |
| no quantity (seasoning / unknown / optional) | 28 | 28 | 28 |
| menu-only (D8) | 46 | 46 | 46 |
| no record / state problem | 4 | 4 | 4 |
| sub-recipe reference, not an ingredient | 0 | 1 | 1 |
| total | 285 | 286 | 286 |

Per dish (resolved / measure-blocked / record-gap, before → after → after + D24): crudo 22/14/2 → 26/9/3 → 28/9/1; little gem 14/16/7 → 19/11/7 → 21/11/5; tomatoes 20/13/6 → 24/10/5 → 27/10/2; margherita 35/9/8 → 40/3/9 → 47/3/2; salmon 29/10/2 → 32/7/2 → 33/7/1.

**Resolved by cause** (the 21 new resolutions and the 3 cause moves): derived volume 9; garlic cloves 8; typo units 2; equal-weight thyme labels 1; oil name 1; sub-recipe reference 1. Cause moved, not resolved: the typo'd balsamic line and the 232 g flour line now convert and land on records lacking a nutrient (measure gap → record gap); the lemon-juice half of the split line has no frozen decision (a live run would match it).

**Quantity errors / new substitutions**: no line lost its weight (one regression, a basil-leaves line, was caught by this check during development and fixed before this run). Three lines changed grams, all from a volume conversion to the page's own stated weight: 40.2 → 38 g EVOO, 7.5 → 8 g salt, 312.5 → 300 g flour. Substitutions: none in the default configuration; 13 under the D24 variant, all 748608 → 171413, Δ −1.592 g/100 g, each listed in the JSON notes. Relevance: one previously calculated scenario (NYT grilled little gems) is now rejected by the gate; it is kept in this comparison so the 19 scenarios match.

**Adaptation, experimental mode, after** (reconciled): 144 blocked lines = 76 filled (G1 35, G2 24, G3 8, G4 3, G5 6) + 68 unfilled in pairs + 0 without a pair; 19 pairs (the Taste of Home margherita now gets one through G5); **complete 0 / 0**; saturated-fat-only complete at high 1; assumption-driven 5 (3 before: the two new are the wedge salad, where the 150 g egg fill carries 560 mg cholesterol, and the pluot salad, where a ¼ cup of cream spans 30-59.5 g because USDA labels both a whipped and a fluid cup). Approved mode: 21 filled (G2 nominal salt 7, G3 8, G5 6), 0 complete.

**What still blocks the 19 pairs at the high bound** (after; D24 at 15 % in brackets):

| Remaining cause set | Pairs |
|---|---:|
| complete | 0 [1] |
| only weight assumptions missing (blocked or missing table rows: bottarga, shishito, lemon thyme, semolina) | 3 [4] |
| weight rows plus a record lacking a nutrient | 4 [2] |
| a measure, matching or record gap that no weight row touches | 12 [12] |

So: **approving every proposed and blocked weight row would complete 3 pairs (4 with D24) out of 19**; the other 12 need USDA measures that do not exist (Greek yogurt, sprigs, a bunch of basil), records that lack a nutrient (vinegars, red onion, canned tomatoes, the flour proxy), or a matching decision (milk, chicken stock, the lemon-juice split). Those are data gaps, not assumption gaps, and they are the honest ceiling of this recipe set.

## 8. Phase 2D and readiness

`SPEC_2D_restaurant_portions.md`: three portion models (unit dish, plate weight, key-ingredient weight), the interface (a `PortionedScenario` beside the recipe-basis figures, never replacing them), the cooking-yield limitation, an evidence plan (own weighings of 20 dishes, published chain data, culinary portion standards), an evaluation plan (hold-out by restaurant, an error budget naming the largest of the three uncertainties), and the decisions it needs.

**Recommendation: not yet.** 2D scales whole-recipe totals to a plate; with 0 published and 0 adapted scenarios complete under the rules you have approved, it would scale known subtotals. The blockers are decisions, not code: (1) D24's tolerance (13 lines, 10 scenarios, one pair complete at 15 %); (2) the weight rows that would complete 3-4 pairs (W09 olive-oil drizzle, W05/W08 for the gem salads, the four blocked rows, egg size); (3) whether a non-USDA composition source (MEXT, INRAN) may ever enter the service, which is an architecture change. Once any dish has two complete scenarios, 2D's P1 model for the pizza (the page states one pizza per recipe) is the cheapest first implementation.

## 9. For your review, in priority order

1. **D24 tolerance**: 5 % (nothing changes), 15 % (13 EVOO lines; −0.215 g saturated fat per tablespoon against the Foundation analysis), or refuse. The policy stays off until you say.
2. **Egg size**: "3 hard-boiled eggs" on a record whose only size is '1 large' = 50 g. D20 keeps the published line unknown; the pair uses 150 g. If you consider USDA's "large" the standard egg, that is a one-line approval with a big effect (560 mg cholesterol on the wedge salad).
3. **Transformed-state labels** (whipped vs fluid cream, packed vs unpacked sugar, ground vs whole pepper): the G5 range is honest but wide for cream (30-59.5 g for ¼ cup). A rule "a label naming a transformation the line does not mention loses to the plain label" would be deterministic and would pick "fluid" for "heavy cream"; it is a default and I have not built it.
4. **Blocked rows** (section 5): per-ingredient proposals; the non-USDA-source question for shishito and shiso.
5. **The relevance reference labels** (42 rows): correct any you disagree with; the eval re-runs in minutes.
6. **Greek yogurt** (3 lines, three recipes): USDA has no household measure on any Greek-yogurt record; the only ways out are a reviewed density assumption or a weight row. I recommend leaving it unresolved.

## 10. Files

Created: `roli_agent/recipes/completeness.py`, `roli_agent/scripts/{freeze_inputs_2c1,replay_2c1,eval_relevance_2c1}.py`, `roli_agent/tests/test_recipes_2c1.py`, `roli_agent/eval/{frozen_inputs_2c1,2c1_controlled_2026-11-03}.json`, `menu_reader_eval/relevance/{relevance_set_v1.csv,README.md,results_2026-11-03_run5.json,results_2026-11-03_gate_v1_1.json}`, `roli_agent/SPEC_2D_restaurant_portions.md`, 13 USDA fixtures (`nutrition_service/tests/fixtures/usda/food_{169230,167746,169640,173176,171328,174924,173424,168833,170000,790577,173470,172442,169655}.json`, manifest updated), `roli_agent/test_report_2C1.txt`, this file.

Modified: `roli_agent/recipes/{parse,convert,adapt,pipeline,relevance,models,ingest}.py`, `roli_agent/prompts.py` (rubric: method text decides), `SPEC_2B_recipe_scenarios.md` (15.6), `SPEC_2C_menu_adapted_scenarios.md` (revision 4, section 13), the project notes, three tests whose expectations the new parser makes obsolete ("2 garlic cloves" is a clove count; a dimension-labelled lone fruit converts; a pint of cherry tomatoes derives from the cup label that names them).

Unchanged: the Phase 2A calculator and its completeness logic, every missing-data safeguard, D23, the weights table (`approved_by` empty on all rows), the user-facing reply, `code/`, the MCP wrapper, the LangSmith prototype. Secret scan: 0 hits.

**Stopped here.**
