# Checkpoint 2B-2: recipe scenarios for a menu item (relevance, USDA matching, conversion, calculation, comparison)

Date: 2026-11-02. Status: **Phase 2B-2 complete; stopped for review. Phase 2C not started (proposal only).** Spec: `SPEC_2B_recipe_scenarios.md`, section 15.2.

## 1. Summary

| Item | Result |
|---|---|
| Built | `roli_agent/recipes/{relevance,match,pipeline,metrics}.py`, conversion extensions, the `estimate_dish` graph node, `run_roli(menu_item=...)`, `responses.dish_reply`; library: read-only `get_portions()` |
| Offline tests | agent **160 passed**, 4 skipped (live); library **308 passed** (292 unchanged + 16 for portions). `test_report_2B2.txt` |
| Phase 2A arithmetic | unchanged; its 292 tests pass unchanged; a test asserts the calculator does not import the portions module |
| USDA matching evaluation (44 ingredients, live) | 31 direct correct, 11 acceptable proxies, 1 label disagreement, **0 false matches**, 1 unresolved; 8 LLM calls, 54 s, $0.023 |
| Live run, five Flour + Water dishes | 38 distinct recipes read, 29 relevant, 19 calculated, **0 arithmetically complete, 0 eligible for a range**. Every statement says so and names why |
| Cost per dish, cold | 47–74 s, $0.023–0.032, 8–14 LLM calls, 31–42 USDA searches, 43–98 USDA HTTP requests, 2 Tavily credits |
| Cost per dish, warm | 12–24 s, $0.005–0.013, 4–8 LLM calls, 0–3 USDA HTTP requests, 0 credits |
| Numbers in replies | only Phase 2A display strings and comparison values; a test checks every digit in the reply exists in the estimate |
| Decisions applied | D5 measured, not modeled; D11 documented (`PHASE_2C_proposal.md`); D15, D16, D17 built; D18 and D19 proposed below |

The headline result is honest and unwelcome: **no published recipe produced a complete per-serving figure for any of the five dishes.** Section 6 shows exactly which lines block each scenario. Three causes account for almost everything: menu ingredients the recipes lack (44 lines, D8, by design), household measures USDA cannot weigh for that record (46 lines), and unstated quantities (30 lines, 16 of them seasonings). The pipeline is doing what the spec asks; the remaining gap is a product decision about assumptions (Phase 2C), not a correctness problem.

## 2. Architecture, in plain language

```text
MenuItem -> ingest (2B-1) -> gate (Python) -> coverage (Python) -> rubric (1 LLM call per dish) -> choose up to 4 scenarios
        -> USDA matching (batched: 1 LLM query call + searches + 1 LLM selection call per 12 ingredients; guard; state check; disk cache)
        -> preparation state (Python, from the recipe's words and the record's state) -> grams (USDA portions of the matched record)
        -> menu-only lines appended (D8) -> Phase 2A calculator, unchanged -> blockers, proxy share, representativeness, eligibility
        -> Phase 2A comparison over eligible scenarios -> statement (Python template) -> DishEstimate
```

| Step | Who | What the LLM may do | Numbers produced |
|---|---|---|---|
| gate | Python | nothing | none |
| rubric | LLM, then Python | categorical grades per recipe; Python combines them and applies D10 hard exclusions | none |
| matching | LLM, then Python | write USDA search words; pick one FDC ID from each ingredient's own candidate list | FDC IDs only, each verified to be in the list (`roli_agent/selection.py`, shared with the food path) |
| conversion | Python | nothing | grams, each with factor and reference |
| calculator | Python (Phase 2A) | nothing | every nutrient number |
| statement | Python | nothing | counts and Phase 2A values |

Relevance and completeness stay separate fields: `Relevance.grade` and `representativeness` say how well the recipe matches the restaurant's dish; `calculation_status` says whether the arithmetic covers every line. A scenario enters the range only if it is complete, graded high or medium with no hard exclusion, and not proxy-dependent (D18).

## 3. Decisions applied and taken

| # | Decision | How it was applied |
|---|---|---|
| D5 | deferred | No modeled zero anywhere. Each excluded line gets a `blocker` category; `complete_except_seasonings` and the summary counter measure the effect (section 6). The narrow proposal is in section 9. |
| D11 | documentation only | `roli_agent/PHASE_2C_proposal.md`. Nothing implemented. |
| D15 | yield from page text | `recover_yield_from_text`: serving words only, verbatim regex; used for 5 of 19 calculated scenarios (James Beard "serves 4", Pike Place "serves 2-3" -> 2.5 flagged range). "Makes 2 pizzas" and "8 slices" never become servings (tests). |
| D16 | listicles out, reason kept | Gate rejects `no_quantities_listicle_suspect` pages and titles like "6 Tasty Recipes Using Heirloom Tomatoes"; live: 3 rejections. A recipe with some unquantified lines is calculated and comes out incomplete, never rejected. |
| D17 | refusing hosts | `RefusalMemory`: 401/403/451 twice in a week -> skipped that week, persisted next to the page cache. robots.txt and 429 handling unchanged. Live: 0 refusals this run. |
| **D18 (proposed)** | proxy dependence | representativeness `proxy_dependent` when a substitute record is the largest contributor or supplies > 50 % of a nutrient's known subtotal; above 50 % the scenario leaves the range. Live: 0 scenarios crossed 50 % in the final run (the Little Gem salad whose only resolved contributor was a proxy did in run 2). **Needs your yes or a different threshold.** |
| **D19 (taken during 2B-2, needs confirmation)** | prefer SR Legacy records | Run 2 showed the model choosing Foundation records ("Oil, olive, extra virgin" 748608) that carry no household measures and often no cholesterol value: 56 of 92 unconvertible lines and 6 of 10 "nutrient not reported" lines. The selection prompt now says: when an SR Legacy and a Foundation candidate name the same food in the same state, take SR Legacy. Final run: 257 of 264 matched records are SR Legacy. The guard is unchanged; the model still only picks from USDA's list. |

Requirements 1–10 of your message map to code and evidence in `SPEC_2B_recipe_scenarios.md` section 15.2.

## 4. Automated tests (offline, no network)

| File | Tests | Covers |
|---|---|---|
| `nutrition_service/tests/test_portions.py` | 16 | portions read from the saved real replies (olive oil tbsp 13.5 g, 13 tomato measures, Foundation "1 cup, chopped"); identity rules identical to nutrient extraction; bad rows skipped not repaired; separate cache key; error shapes; no nutrient value in a portions result; calculator does not import portions |
| `test_recipes_convert_portions.py` | 15 | embedded weights ("1 (14 oz) can", "2 (6-ounce) fillets", "about 1.5 pounds" as total); portions by unit words, modifiers ("cup, chopped" vs "cup cherry tomatoes"), plum/Italian synonym, medium default, size units, ambiguity -> unknown, Foundation measure names, derived volumes from another measure's density; D15 yield recovery; D17 refusal memory |
| `test_recipes_match.py` | 8 | batched direct/proxy/unresolved in two LLM calls; guard rejects a foreign ID and never looks it up; raw hint vs cooked record -> `state_conflict`; cache hit skips LLM and USDA, proxies stay proxies, expiry; malformed rows dropped singly; USDA outage recorded |
| `test_recipes_relevance.py` | 20 | gate cases (crudo vs bottarga pasta, seared tuna, listicles, margarita cocktail); coverage with synonyms and `menu_missing`; `combine` truth table; batch grading in one call; unparsable or off-vocabulary rubric -> ungraded |
| `test_recipes_pipeline.py` | 12 | crudo: bottarga, grape and chive appended and the statement names them, no total stated, page nutrition never leaks, rejected pages cost no USDA call; tomato salad: complete vs seasoning-blocked vs proxy-dependent scenarios, range over the 2 eligible ones only, single eligible -> not a range, scenario cap; reliability: all rejected -> no numbers and no USDA calls, rubric failure, USDA outage, guard rejection; graph path and reply-number guard; setup failure (no Tavily key) reported, not invented |

Earlier suites (food path, failures, menu path, recipe path, 2B-1 ingestion) are unchanged and pass.

## 5. USDA matching evaluation (requirement 2)

Set: `menu_reader_eval/usda_matching/matching_set.csv`, 44 ingredients from the five dishes plus common ones, each with an expected-description pattern and, where USDA has no exact food, an accepted-proxy pattern. Scorer: `roli_agent/scripts/score_matching.py`; results `menu_reader_eval/usda_matching/results_2026-11-02.{json,md}`.

| Verdict | Count | Examples |
|---|---:|---|
| direct, correct | 31 | bluefin tuna raw 173706, chinook raw 173688, tahini 170189, fior di latte -> mozzarella whole milk 170845, canned tomatoes 2685578, scallions 2727585 |
| proxy, acceptable | 11 | bottarga -> Fish, roe, mixed species, raw; pecorino sardo -> Cheese, romano; little gem -> Lettuce, cos or romaine; pluot -> Plums, raw; mirin -> sake; caciocavallo -> provolone; pancetta -> bacon, cooked |
| label disagreement | 1 | castelvetrano olives -> green olives labelled direct (a proxy by my pattern) |
| false match | **0** | |
| unresolved | 1 | shiso: the model declined every candidate (correct: USDA has no perilla) |

Two things to know. First, the first evaluation run lost 20 of 44 rows because one batched selection reply failed a strict whole-envelope validation; the matcher now validates each row on its own and records the reason, so a malformed row costs one ingredient, not a batch. Second, 7 of my 44 oracle patterns were written in SR Legacy wording and were wrong for USDA Foundation names ("Green onion, (scallion)…", "Anchovies, canned in olive oil…", "Cream, heavy"); I corrected the patterns after inspecting the chosen descriptions and re-scored the saved decisions without new calls (`--rescore`; the markdown shows the verdict before and after for every row). No matcher output was changed by that step.

## 6. Live evaluation: the five dishes (requirements 7 and 8)

Script `roli_agent/scripts/measure_2b2.py`; raw output `roli_agent/eval/2b2_live_2026-11-02.json` (final run) and `2b2_live_2026-11-02_run1.json` (first run, kept for comparison). Model `google/gemini-3.8-flash`, temperature 0. Cold = empty page, search and match caches and a cold USDA cache; warm = the same caches after the cold run, same process.

### 6a. Funnel (final run)

| Dish | hits | fetched | extracted | distinct | gate passed | relevant | calculated | complete | eligible | exclusion reasons |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Bluefin Crudo | 18 | 12 | 9 | 9 | 6 | 6 | 4 | 0 | 0 | 2 dish word absent (bottarga pastas), 1 listicle, 1 servings unknown, 1 beyond cap, 4 incomplete |
| Little Gem Lettuces | 17 | 12 | 8 | 8 | 7 | 5 | 4 | 0 | 0 | 2 hard exclusions (a "Baby Gem Lettuce" essay: different dish; grilled salad: different preparation), 1 dish word absent (a dressing), 1 beyond cap, 4 incomplete |
| Heirloom Tomatoes | 16 | 12 | 5 | 5 | 3 | 3 | 3 | 0 | 0 | 2 listicles, 3 incomplete |
| Margherita | 17 | 12 | 10 | 9 | 9 | 9 | 4 | 0 | 0 | 2 servings unknown, 3 beyond cap, 4 incomplete |
| King Salmon | 17 | 12 | 7 | 7 | 7 | 6 | 4 | 0 | 0 | 1 hard exclusion (salmon laksa), 1 servings unknown, 1 beyond cap, 4 incomplete |

The gate and rubric did their job: no bottarga pasta, cocktail, soup or laksa was calculated, and every rejection carries its reason. Relevance grading cost one LLM call per dish.

### 6b. Why the 19 calculated scenarios are incomplete (requirement 5 and the D5 measurement)

Over the 19 scenarios, 229 recipe lines: 139 resolved (USDA record, grams and a compatible state), 90 excluded, plus 44 menu-only lines appended under D8.

| Blocker category | Lines | What it is |
|---|---:|---|
| menu_only | 44 | printed menu ingredients absent from the recipe (bottarga, muscat grape, chive; tahini vinaigrette, pecorino sardo, toasted sesame; pluot, shiso, sourdough; squash, corn, basil, shishito). By design never omitted |
| no_usda_portion | 46 | a count or volume the matched record cannot weigh: 19 ambiguous ("1 carrot" between large/medium/small with no medium label; "1 lemon" between "fruit" and "wedge" labels; "2 cloves garlic" between "1 clove" and "3 cloves"), 27 with no measure of that kind (miso and honey by the teaspoon, mirin and olives by the tablespoon, a bunch of thyme, lines with the typo "tabelspoons") |
| seasoning_unknown_quantity | 16 | "salt, to taste", "freshly ground black pepper", "flaky salt" |
| unknown_quantity | 13 | "olive oil, for drizzling", "a handful of mint", "fresh shaved Parmesan", "cooking oil" |
| nutrient_not_reported | 8 | the record lacks one nutrient (grape tomatoes 321360, red onion 790577, red wine and balsamic vinegar) |
| unresolved_usda | 6 | the model declined every candidate (salsa macha, demi-glace, "garlic cloves pan fried in olive oil") |
| optional_unknown_quantity | 1 | "optional toppings" |

D5 measurement, as you asked: 11 of the 19 scenarios contain at least one seasoning line with no quantity; **0 scenarios are blocked solely by seasonings**, 0 solely by menu-only lines, 0 by the two together; 5 are blocked only by the three categories seasonings + menu-only + portions. One scenario (Taste of Home's Margherita, menu coverage 1.0, 12 of 14 lines resolved) is blocked by portions alone: "1 teaspoon dried oregano" (USDA lists "1 tsp, leaves" and "1 tsp, ground", which weigh differently) and "1 garlic clove" (two clove labels). Fixing portion ambiguity would make that one complete; a seasoning rule alone would complete nothing today.

### 6c. The five statements, verbatim (Python templates)

- **Bluefin Crudo:** "6 comparable recipes were found for BLUEFIN CRUDO, but none could be calculated completely: the published recipes do not include bottarga, muscat grape, chive, which the menu lists; some seasonings have no stated quantity ("to taste"); some ingredients have no stated quantity; some household measures have no USDA weight; some ingredients could not be matched to a USDA record. Known subtotals cover the other ingredients only and are not totals for the dish. Not a verified value for the restaurant's dish."
- **Little Gem Lettuces:** same shape; names tahini vinaigrette, pecorino sardo, toasted sesame.
- **Heirloom Tomatoes:** names pluot, shiso, sourdough.
- **Margherita:** "9 comparable recipes were found for MARGHERITA, but none could be calculated completely: some seasonings have no stated quantity ("to taste"); some ingredients have no stated quantity; some household measures have no USDA weight; some ingredients could not be matched to a USDA record. …" (menu coverage 1.0 on all four calculated recipes)
- **King Salmon:** names squash, corn, basil, shishito.

Known subtotals shown per scenario (from the Phase 2A display strings), for example the four margheritas: saturated fat at least 1.84 g (King Arthur, 12 servings), 8.03 g (A Beautiful Plate, 4), 6.52 g (Belly Full, 8), 4.27 g (Taste of Home, 6) per serving from 9–12 of 9–16 ingredients. These are subtotals and the reply says so; the spread across them is itself a finding: per-serving figures depend heavily on each recipe's own serving count (section 5 of the 2C proposal).

### 6d. Conversions (requirement 3), examples from the live run

| Line | Grams | Method and reference |
|---|---:|---|
| 2 tablespoons extra virgin olive oil | 27 | USDA 171413 portion '1 tablespoon' = 13.5 g |
| 1/3 cup olive oil | 72 | USDA 171413 portion '1 cup' = 216 g |
| 1/4 cup tamari | 72.0 | derived: USDA 174278 portion '1 tsp' = 6 g, i.e. 1.2173 g/ml x 236.588 ml (flag `portion_derived_volume`) |
| 1 tablespoon pistachios | 7.69 | derived: USDA 170184 '1 cup' = 123 g, 0.5199 g/ml |
| 1/2 orange (juiced) | 65.5 | USDA 169097 portion '1 fruit (2-5/8" dia)' = 131 g (flag `portion_default_whole`) |
| 2 scallions (chopped) | 30 | USDA 170005 portion '1 medium (4-1/8" long)' = 15 g |
| 1 cup cucumbers (sliced) | 104 | USDA 168409 portion '0.5 cup slices' = 52 g |
| 1 tablespoon fresh basil (finely minced) | 2.65 | USDA 172232 portion '2 tbsp, chopped' = 5.3 g |
| 1/8 teaspoon lemon zest | 0.25 | USDA 167749 portion '1 tsp' = 2 g |
| One 8-ounce loin sushi-grade yellowfin tuna, cut into 1-inch cubes | 16 | **wrong**: the count "1" took the portion '1 cubic inch, boneless' = 16 g; the 8 oz is inside the line, not in parentheses. Flagged in section 8 |
| 3 baby gem lettuce, leaves separated | 1878 | **doubtful**: the proxy record's '1 head' (romaine, 626 g) applied to little gem heads. A proxy's portions are a different-sized food. Flagged in section 8 |
| 1 (14 oz) can … (tests) | 396.9 | embedded weight x 1, NIST ounce |
| 1 carrot; 1 lemon (zested); 2 cloves garlic | unknown | `portion_ambiguous`: several whole-item labels, nothing in the line to choose by |
| Salt, to taste | unknown | never zero |

Methods over the 229 recipe lines: USDA portion 120 (5 derived), explicit weight 13, embedded weight 2, water-like density 13, none 81.

### 6e. Cost and latency by stage (requirement 7)

| Dish | Cold s (ingest / relevance / match / convert+calc) | Cold LLM calls, tokens, cost | Cold USDA searches / lookups / portions / HTTP | Warm s | Warm LLM calls, cost | Warm USDA HTTP |
|---|---|---|---|---|---|---|
| Bluefin Crudo | 73.5 (21.1 / 2.9 / 46.6 / 2.9) | 14, 22.9K+4.0K, $0.032 | 42 / 85 / 56 / 98 | 20.5 | 8, $0.012 | 0 |
| Little Gem Lettuces | 53.3 (8.5 / 4.5 / 38.1 / 2.2) | 10, 16.0K+3.2K, $0.024 | 37 / 78 / 49 / 66 | 11.5 | 4, $0.005 | 3 |
| Heirloom Tomatoes | 60.4 (26.0 / 3.0 / 30.0 / 1.4) | 12, 25.0K+2.7K, $0.029 | 34 / 72 / 53 / 43 | 24.4 | 8, $0.013 | 1 |
| Margherita | 47.2 (9.6 / 4.0 / 31.5 / 2.1) | 8, 14.6K+3.2K, $0.023 | 32 / 65 / 37 / 45 | 13.9 | 4, $0.007 | 0 |
| King Salmon | 48.0 (12.8 / 3.6 / 30.2 / 1.5) | 10, 16.1K+3.3K, $0.024 | 31 / 87 / 58 / 45 | 17.5 | 6, $0.009 | 0 |
| **Total** | 282 s | 54 calls, 94.5K+16.4K tokens, **$0.132** | 176 / 387 / 253 / 297 HTTP; 10 Tavily credits | 88 s | 30 calls, $0.046 | 4 HTTP, 0 credits |

Where the time goes: matching (30–47 s cold) is the model writing queries and choosing records plus one USDA search per ingredient, serial; ingestion (9–26 s) is page fetching plus the LLM extraction fallback for pages without structured data (5 pages for the crudo and the tomatoes, 1 for the others); conversion and calculation is 1–3 s after the parallel prefetch of USDA records (it was 60–95 s in run 2, sequential). Warm runs spend nothing on Tavily or USDA HTTP and skip the LLM for 179 cached ingredient decisions; what remains is the relevance call and the extraction fallbacks (pages without structured data are re-read by the LLM every time; caching the extraction result per page is a cheap next step). Costs are OpenRouter's own figures (`token_usage.cost`), not estimates. Targets from spec section 12 (under 60 s and $0.10 cold, under 20 s warm): cost met, cold time met for 3 of 5, warm time met for 3 of 5.

### 6f. Run history (for transparency)

1. **Run 1** (same day): a batched selection reply failed the whole-envelope validation; 2 of the crudo's 4 scenarios had every ingredient unresolved. Fixed (row-level validation, reasons recorded). Cost $0.130. File kept as `_run1.json`.
2. **Run 2**: 0 complete; 92 lines without a USDA weight, 56 of them because the model chose Foundation records without household measures. Fixed by D19, Foundation portion names, derived volumes, parallel prefetch. Output not kept (superseded within the hour).
3. **Run 3 (final)**: the numbers above. Unconvertible lines 92 -> 46; "nutrient not reported" 10 -> 8; matched records 97 % SR Legacy.

Total live spend for 2B-2: about $0.33 on OpenRouter, 30 Tavily credits, roughly 900 USDA requests.

## 7. Files

Created: `roli_agent/recipes/relevance.py`, `match.py`, `pipeline.py`, `metrics.py`; `roli_agent/selection.py`; `roli_agent/scripts/measure_2b2.py`, `score_matching.py`; `roli_agent/eval/2b2_live_2026-11-02.json`, `2b2_live_2026-11-02_run1.json`; `menu_reader_eval/usda_matching/matching_set.csv`, `results_2026-11-02.json`, `results_2026-11-02.md`; `nutrition_service/roli_nutrition/portions.py`, `nutrition_service/tests/test_portions.py`; tests `test_recipes_convert_portions.py`, `test_recipes_match.py`, `test_recipes_relevance.py`, `test_recipes_pipeline.py`, helper `recipe_test_helpers.py`; `roli_agent/PHASE_2C_proposal.md`; `roli_agent/test_report_2B2.txt`; this file.

Modified: `roli_agent/recipes/{models,convert,extract,fetch,search,ingest,__init__}.py` (2B-2 models; embedded weights and portions; D15; D17; search cache; wiring), `roli_agent/{prompts,nodes,graph,state,responses,config,__main__}.py` (dish path), `nutrition_service/roli_nutrition/{service,__init__}.py` (`get_portions`, exports), `nutrition_service/README.md` (section 12), `SPEC_2B_recipe_scenarios.md` (status, section 15.2), the project notes (current stage).

Unchanged: `nutrition_service/roli_nutrition/recipe/` (the calculator and comparison), `code/`, the MCP wrapper, the LangSmith prototype, `menu_test_set/`, `results/`. No deployment, no tunnel, no key in any file (scan: 0 hits for all five secrets outside `.env`).

## 8. Deviations, known weaknesses, and what I would fix next

1. **Portions of a proxy record** are a different food's sizes ("1 head" of romaine for little gem). Proposed rule: when the match is a proxy, accept only *volume* and *weight-like* portions (cups, tablespoons), never whole-item counts; count lines on proxies stay unknown.
2. **Weights inside the line** ("One 8-ounce loin … cut into 1-inch cubes") are not read; the parser only reads parenthetical weights. The count "1" then took a cubic-inch portion. Proposed: read "N-ounce/pound" anywhere in the line when the count is 1, and never apply a "cubic inch" or "slice" portion to a bare count.
3. **Ambiguous whole-item portions** (19 lines): choose by equal weight already works; for different weights I propose the SR Legacy "medium" or the label without a size word, else the median of the candidates, flagged `portion_median_of_labels`. Needs your yes: it is a documented assumption, not a measurement.
4. **Teaspoon lines on records that list only "1 tsp, leaves" and "1 tsp, ground"** (dried oregano) and tablespoon lines on records with only ounces (olives, pickled peppers): unknown today. Weight-only records could use a density table *per record*, but that is a new assumption class; left for review.
5. **Relevance rubric is one call per dish**, not per recipe (spec 3.3); matching batches 12 ingredients per call across recipes. Fewer calls, same guards.
6. **Up to four scenarios per dish** are calculated (`MAX_SCENARIOS`); 7 relevant recipes were left as `beyond_scenario_cap`. Raising the cap costs about 10 USDA searches and 2 LLM calls per extra recipe.
7. **Extraction fallback results are not cached**, so pages without structured data are re-read by the LLM on warm runs (5 calls for the crudo). Cheap to cache beside the page.
8. **`Baby Gem Lettuce` by Rachel Phipps** passed the gate (dish word present) and was correctly rejected by the rubric as a different dish type: the gate is a coarse filter by design and the rubric is still needed.

## 9. D5: the narrow proposal you asked for

Distinguish by the USDA record, not by a hand-written list:

- **zero-nutrient**: the matched record reports **0 g saturated fat and 0 mg cholesterol per 100 g** (table salt 173468, water, vinegars where reported, citrus juice, sugar). Any plausible weight contributes exactly 0, so the line can be marked resolved with `grams_declared: null`, an assumed weight from the record's own smallest portion (for the audit trail only) and `assumption: "zero_nutrient: USDA <id> reports 0 g / 0 mg per 100 g; weight unstated"`. The contribution is 0 because USDA says 0 per 100 g, never because the weight was set to 0.
- **low but nonzero**: the record reports > 0 for either nutrient (black pepper, dried herbs, chili flakes). Stays unknown in 2B. In 2C it may receive an explicit assumed garnish weight whose contribution is shown, not hidden.
- Phase 2A's completeness rule is untouched: the line enters the calculator with a real `grams` value and a real record; the calculator does its ordinary arithmetic. The change is confined to the pipeline's line-building step and is fully visible in the assumption text.

Measured effect today: of the 16 seasoning lines, those matched to salt (≥ 10) would resolve; pepper and chili flakes would not. No scenario becomes complete from this alone (section 6b), so I recommend deciding it together with the portion fixes in section 8.

## 10. Decisions needed before Phase 2C

| # | Question | My recommendation |
|---|---|---|
| D18 | proxy-dependence threshold for leaving the range | keep 50 % of a nutrient's known subtotal; always print the share |
| D19 | prefer SR Legacy over Foundation for the same food | confirm; it gives household measures and both nutrients |
| D20 | portion ambiguity: medium / unsized label / median of labels, flagged | adopt; the alternative is leaving most counts unknown forever |
| D21 | proxies get volume portions only, never whole-item counts | adopt |
| D5 | the zero-nutrient rule above | adopt in 2C together with D20 |
| 2C | the menu-adapted scenario approach in `PHASE_2C_proposal.md` (assumption classes, garnish table, low/high pairs) | review the proposal; decide who writes the first garnish weights |
| — | show known subtotals to end users, or only the "no complete recipe" statement until 2C exists | show them with the current wording; they are honest and auditable |

**Stopped here. Phase 2C, the menu-wide ranking, Telegram and the conversational interface are not started.**
