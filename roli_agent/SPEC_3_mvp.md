# Specification: Phase 3, Roli MVP for invited testers

Status: **written 2026-11-03 before implementation; built 2026-11-03/04 as specified (`roli_agent/mvp/`), evaluated and stopped at `CHECKPOINT_3.md`.** Departures: `max_dishes` 14 (not 12); sharing platters excluded; a process-wide model rate limiter (16 per minute) was needed; a lone ranked dish is labelled `only_estimate`. Builds on Phases 1E, 2A, 2B, 2C and 2D; changes none of their arithmetic or safeguards. Everything a tester sees is produced by Python templates from the pipeline's own objects.

## 1. Objective

A tester uploads a restaurant menu photo and gets **up to three recommendations**, lowest saturated fat first, cholesterol as the second criterion, in 80 words or fewer, with an internal diagnostic view behind every recommendation. Private, access-controlled, experimental configuration clearly marked.

## 2. Flow (one menu run)

1. **Read the menu** with the existing reader (`nodes.make_read_menu`, prompt v5, Gemini 3.8 Flash): items with name, description, section, category.
2. **Choose the dishes to evaluate**: food items only (not drinks, add-ons, "other"); sections that are desserts or bread are skipped (no portion rule; outside the comparison's purpose); items with a `has_choice` list are kept but evaluated by name; at most `max_dishes` (default 12) in menu order, so a run has a known cost ceiling.
3. **Estimate each dish** with the existing `estimate_dish` (recipe search, fetch, extraction, relevance, USDA matching, conversion, Phase 2A calculation, 2C adaptation, 2D portioning), **in parallel threads** (default 4). A dish that fails for any reason (search down, no recipe, model error) is recorded as `error` or `no_recipes` with the reason; the run continues.
4. **Intervals and comparison**: per dish and nutrient the 2D `scenario_interval` and `dish_interval`; `compare_dishes` with the four verdicts (`well_supported`, `tentative`, `overlapping`, `insufficient_evidence`).
5. **Rank**: dishes with a saturated-fat upper bound, ordered by that upper bound, then by the cholesterol upper bound; a dish without an upper bound is never recommended (it is listed as "could not be ranked" with the reason). Each recommended dish carries its support: how many of the other ranked dishes it beats well-supported, tentatively, or overlaps.
6. **Recommendation text** (Python template, ≤ 80 words): the top one to three dishes, their saturated-fat range per plate, the support word, one sentence on what the figures are (modeled from published recipes and typical restaurant portions, not the restaurant's numbers), and how many dishes could not be estimated.
7. **Persist** the run as JSON under `roli_agent/runs/` (menu, dishes, intervals, comparison, recommendation, costs, timings, errors), identified by a run id; the photo is kept beside it.
8. **Diagnostics view** per run: every evaluated dish with its scenarios (source recipes, URLs, relevance grade), USDA matches (record, data type, proxy or not), assumptions (gap, row, grams low/high, review status), inferences, portion model (rule, f, evidence), intervals per nutrient with tier and caveats, the pairwise verdicts and the ranking reasons, errors, costs and timings.
9. **Feedback** per run: a form that lets a tester mark a dish as inaccurate, a ranking as unexpected, or an uncertainty explanation as unhelpful, plus free text; stored as one JSON line per submission (`roli_agent/runs/feedback.jsonl`) with the run id and dish.

## 3. Experimental configuration

`MvpConfig(experimental=True)` (the only configuration that produces rankings today): adaptation mode `experimental` (proposed and evidence-based weights rows), the proposed portion rules, inference rules I01 and I02, and the external-evidence bounds in the comparison. Every page shows a banner "Experimental: modeled from published recipes with unapproved portion rules and assumed weights; not the restaurant's figures." `experimental=False` uses approved mode only and today ranks nothing (every row is unapproved), which is the honest state. Nothing in either mode writes `approved_by`.

## 4. Interface

FastAPI + Jinja2, served by uvicorn on Julius's Mac. Routes: `GET /` upload form; `POST /menu` starts a run in a background thread and redirects to `GET /run/{id}` (status, progress per dish, the recommendation when done); `GET /run/{id}/diagnostics`; `POST /run/{id}/feedback`; `GET /runs` list. **Access control:** one shared token (`ROLI_WEB_TOKEN` in `.env`) required as a cookie or query parameter on every route; wrong or missing token gets 401. No accounts, no public listing. Uploads limited to 12 MB images; the photo is resized the way Telegram would (1280 px) before reading, as the menu reader was tested.

## 5. Generalising the dish types

`portions.dish_type_for` grows deterministic categories from the menu's own words: pizza; crudo starter; fish main / fish starter; **meat main** (beef, steak, pork, chop, lamb, chicken, duck, veal, burger); **pasta** (pasta words or a PASTA section); leaf salad; tomato salad; **vegetable starter / side**. New proposed rule rows (evidence cited, all `proposed_unreviewed`): PR07 meat main P3 (key records beef/pork/lamb/veal/chicken/turkey/duck, 140-280 g raw), PR08 pasta P3 (key record "Pasta", 90-140 g dry), PR09 vegetable starter or side P2 (120-300 g plated). P3 accepts several key record heads per row. Desserts, drinks, bread and sandwiches have no rule and are not ranked (listed as not evaluated).

## 6. Evaluation

1. **End to end on the Flour + Water menu photo** (`menu_test_set/telegram_1280/menu_03_own_IMG_5185.jpg`, 18 food items): the five known dishes must come out as in Checkpoint 2D; the other 13 are new.
2. **Unseen menus**: three photos from the test set the recipe pipeline has never seen (a British gastropub, an American bistro, a seafood chalkboard), capped at 12 dishes each.
3. **Measured per menu**: wall time (and per stage), Tavily credits, model calls and dollars, USDA requests, dishes evaluated / ranked / unranked / errored, and **consistency**: the same photo run twice, rankings and verdicts compared.
4. **Error handling tests** (no network): search down, no recipes, model failure in grading, USDA outage, unreadable photo, bad token, oversize upload: the run completes with the dish marked and the page rendered.
5. **Human-reviewed evaluation**: a review file of the actual recommendations drafted for Julius, emphasising close pairs and specialty ingredients; the agent's expected ranges are not treated as proof.

## 7. Out of scope

Telegram; accounts; hosting beyond a recommendation; approving any row; changing Phase 2A; menu-wide ranking of dishes without a portion rule.

## 8. Local-testing milestone (added 2026-11-04, Julius's brief of 2026-11-04)

Scope: Julius as the only user, on his Mac; functionality, recommendation quality and performance; no deployment, authentication or privacy work.

1. **Wording** (`mvp/ranking.py`): "Among the N dishes I could estimate (M tried; K had no usable estimate; S not tried)" whenever coverage is
   incomplete; "Lowest saturated fat on this menu, by my estimate" only when every candidate was tried and ranked. Overlapping picks read
   "X and Y overlap, so treat that order as a toss-up"; a tentative order reads "The order is tentative: it leans on assumed amounts and modeled
   portions". The top pick's cholesterol names the one ingredient that supplies at least 30 % of its upper end, from the interval's own labels
   ("the top end from bottarga (an estimate)" for an external-evidence bound; "(an assumed amount)" for a weights row). 80 words or fewer.
2. **Dish selection** (`mvp/selection.py`): every food item with a portion rule is a candidate with a course (starters, salads, mains, pasta,
   pizza) and a lean score from menu words (raw fish, salad, vegetables, grilled, fish, soup up; cream, cheese, cured or fatty meat, fried, red
   meat, egg, pizza, pastry down). The cap is filled round-robin across courses, best score first; menu order plays no part. Every item keeps
   `selected` / `skipped` / `excluded` with the reason and the scoring words; the diagnostics show the table. The score never ranks.
3. **Comparison**: a disjoint pair whose lower dish's upper bound comes from an assumption-driven recipe (assumed lines above 30 % of the known
   subtotal) is `tentative` (`compare_dishes.py`, `DishInterval.bound_assumption_driven`).
4. **Nutrition and parsing**: the Phase 2A word table now reads USDA's "unprepared", "uncooked" and "unheated" as raw
   (`roli_nutrition/recipe/preparation.py`; arithmetic untouched); "2 strips bacon" and "4 rashers" convert through the record's slice weight
   (`convert.py`); category-default weights rows W30-W40 (cheeses by family, cured whole-muscle pork, cured sausage, vinaigrette, egg- or
   mayonnaise-based dressing) with a `dish_types` column (W31 cheese on a plate vs W32 cheese on a pizza), all `proposed_unreviewed`, experimental
   mode only, composition proxies flagged; W26 keys extended to bacon and lardons; W29 and PR07-PR11 kept. Deep-frying oil and butter sauces
   have no default on purpose. Two dish-type fixes: bread named in a starters section is not ranked; "chicken for two ...; warm bread salad" is a
   meat main.
5. **Spending safeguards** (`mvp/budget.py`): one `MenuBudget` per run shared by every thread; `BudgetedLLM` checks before and charges after
   every model call including the menu read; `BudgetedSource` blocks a live search over the credit limit and never a cached one; limits per menu
   ($0.50, 30 credits) and per day ($5.00, 300 credits, from the append-only ledger); provider-reported cost is "actual", a call without a price
   is "estimated" from tokens and the model's public per-token prices (fetched once without a key, cached a week), a call with neither gets a flat
   $0.01 reserve; the report separates the three and lists every interruption. A dish stopped mid-way is `budget_stopped`; a dish that could not
   start is `skipped`; the run still ranks what it has.
6. **Local mode** (`mvp/web.py`, `roli_local.sh`): no token means local mode, bound to 127.0.0.1 by the script; the experimental banner stays.
7. **Evaluation**: `scripts/eval_mvp.py` reports spend; `scripts/compare_mvp_runs.py` pairs old and new runs and attributes each dish change to a
   code fix, selection, budget or recipe variability. Results and the readiness assessment: `CHECKPOINT_3A_local.md`.

## 9. Ingredient role and midpoint ranking (added 2026-11-05, Julius's brief of 2026-11-05)

1. **Ingredient role** (`recipes/adapt.py`, `ingredient_role`, CSV column `role_sensitive`): for cheese, cured-meat, nut, seed and olive rows, when the
   ingredient's role on the plate is clear, a garnish takes the lower half of the row's range and a substantial ingredient the upper half; an ambiguous
   role keeps the whole range. Clear means: a garnish or substantial word beside the ingredient on the menu or in the recipe line ("shaved parmesan",
   "to finish", "baked goat cheese"); the ingredient named in a salad's or pizza's own name (substantial); a cheese, cured meat or nut listed beside a
   fish or meat main (garnish: the protein is the dish). No model call, no new rows, no change to review status; the assumption's basis records the
   role and the reason.
2. **Midpoint ranking** (`mvp/ranking.py`): dishes with a credible interval are ordered by (low + high) / 2 of saturated fat, lowest first; two
   centres within 0.25 g or 5 % are an effective tie and the central cholesterol decides. The ranges stay on display and the page says the order is
   by the middle of the range. A dish without an upper bound gets no midpoint and is never ranked; the pairwise verdicts (toss-up, tentative,
   well supported) are unchanged.
3. **Outlier recipes**: the Phase 2D aggregation (min low, max high; an incomplete recipe whose lower bound exceeds the bounded maximum withdraws the
   bound) was checked against the one demonstrated case, the Flour + Water pork chop: a "1 (8-rib) pork rack" read as one 133 g chop. The targeted
   correction is in `convert.py`: a rack, crown roast, N-rib or whole-bird line never takes a single-piece label, so that recipe is not portioned
   and no longer withdraws the dish's bound. No other aggregation change.

## 10. Herbs and spices, recipe backfill, serving count (added 2026-11-05, Julius's follow-up)

1. **Rule I03, herbs and spices left out** (`recipes/inference.py`, `is_herb_or_spice`; `MvpConfig.exclude_herbs_spices`, on by default in the MVP, off in the Phase 2B reply path).
   A directly matched USDA spice or fresh-herb record decides; otherwise the whole name must be herb or spice words plus descriptors, so "mint almond", "bay scallops" and
   "mustard greens" stay in. Mixtures (butter, oil, pesto, sauce and similar), poppy seeds, garlic, fresh ginger, fresh chiles, prepared mustard and plain salt are not covered. A
   left-out line is never sent to the Phase 2A calculator, published or adapted, and is not part of the recipe weight. It is labelled: `excluded_from_calculation`, an `excluded_negligible`
   inference with rule I03, basis `documented_inferences`, and a total that relied on it is `complete_with_inferences`, never `source_complete`. Checked on 266 weighed lines in the
   saved runs: maximum 0.066 g saturated fat per recipe serving, median 0.003 g, cholesterol 0. Weights rows for herbs (W01, W02, W03a, W03c, W04a, W04b, W15, W16, W29) stay in the
   table and are no longer reached in the MVP.
2. **Recipe backfill** (`pipeline.py`; `MvpConfig.backfill_recipes`). The cap of 4 already applied after relevance and serving-count drops. Now a recipe that no portion model
   can use gives its place to the next eligible one, until 4 are portioned or none remain. The failed recipe stays visible in the diagnostics. More recipes mean more model calls;
   the existing per-menu budget still applies.
3. **Serving count** (`parse.py`). The number beside the serving word wins ("2 cups / 12 servings" is 12; "Serves 8 (4 breakfasts for 2 people)" is 8); a yield with no such number
   falls back to the old reading.

## 11. USDA Survey (FNDDS) records (added 2026-11-05, Julius: "Use survey records")

Library: spec v2.2 (`nutrition_service/SPEC.md` section 17). Two uses in Roli, both deterministic Python (`recipes/survey.py`):

1. **D25, same-food measure.** A volume line ("1 1/2 cups olives") whose matched SR Legacy or Foundation record has no usable measure may take the cup,
   tablespoon or teaspoon weight of a Survey record of the SAME food (first word of the description equal). Nutrients stay with the matched record;
   the line's reference names both records; whole-item counts are never borrowed (D21). `MvpConfig.survey_measures`, default on.
2. **Fried-dish record.** For a menu dish whose name or description says it is fried (crumbed, battered, crispy, chips, calamari, schnitzel, ...), each
   fried component named in the dish name is matched by a fixed table to one Survey finished-food record ("Fish, NS as to type, fried", "Fish, cod, fried",
   "Calamari, fried", "Shrimp, fried", "Chicken breast, fried, coated, ...", "Potato, french fries, restaurant", "Fried onion rings", ...). The plate amount
   comes from the existing portion rules: a raw-flesh rule (PR02, PR07, PR11) converted by USDA's own raw share from the record's inputs (65 g raw fish per
   100 g fried fish), the new proposed row PR12 for a side of chips (120-250 g cooked), PR10 for a fried vegetable starter, else the record's own serving
   measures. Description words go through the weights table (tartare sauce -> W40) or stop the estimate when nothing covers them; herbs are left out (I03).
   The Phase 2A calculator adds the components for one plate at each bound. The result is one more scenario interval beside the recipe-based ones,
   tier `survey_dish_record`, always assumption-driven, so any ranking resting on it is tentative. The diagnostics show the record, USDA's frying-fat
   grams per 100 g, the inputs, the rule and the choice. `MvpConfig.survey_fried_dishes`, default on. "Fish & chips" is now a fish main.

Roli still never invents a frying-oil quantity: the oil amount is USDA's, for a typical US preparation in generic vegetable oil, and the limitations say so.

Refinements made while rerunning the four menus (2026-11-05, same day):
- A fried recipe's stated frying oil is not eaten: an oil or fat line that says "for frying" (or lists 100 g or more in a recipe whose method fries) is left
  open rather than counted; the Survey fried-food record bounds the dish instead (`pipeline.py`, `FRYING_FAT_LINE`, `FRYING_BATH_MIN_G`). Oil that is eaten
  (a dressing, a confit) still counts as the recipe states.
- Two fried components of the same family on one plate (squid and prawns) share the family's plate rule equally instead of each taking all of it.
- A dish's lower bound is the lowest low of its BOUNDED recipes when there are any; an incomplete recipe's known subtotal is reported as a caveat, not used
  as the range's low, so the midpoint never leans on a partial figure (`compare_dishes.dish_interval`).
- Rows W50-W55 (lime wedge, pickles, chilli sauces, flavoured butter, peas, mushy peas on a Survey fat-added-peas record) so side words on pub menus stop
  blocking the fried-dish estimate; description words that restate the fried component are skipped.
- The Survey search asks for 10 results (the service's maximum) with queries written so the wanted record ranks first; the first live pass had asked for 25
  and every fried-dish lookup failed silently, which the test fake now reproduces.
- The recommendation's word limit drops optional sentences (top pick's cholesterol, the certainty sentence, the cholesterol notice) and never cuts the
  closing disclaimer.

## 12. Check the result; fix by class, as data (added 2026-11-05, Julius's decisions of 2026-11-05)

Why. Every recent fix answered one of three questions: is a line eaten (frying oil, the 100 g bath, herbs, marinade oil), how much is on the plate
(PR rows, weights rows, the role rule, the pork rack, the olive bowl), and what is it made of (stand-ins, D25 head match, the US fish mix). Each was
built as its own code path after a person spotted a bad number. From here: one check on every finished number (12.1), and one general mechanism per
question whose knowledge lives in sourced tables (12.2-12.4). USDA access is fixed in 12.5. Reading bugs stay with tests.

### 12.1 Reference check and flags

1. Each dish-family card (12.2) carries published saturated fat **per 100 g served** and **per plate**, each with its sources (retail labels, chain
   nutrition disclosures, USDA Survey whole-dish records). Published figures are used only in this check, never in a total (the `blocked_evidence.csv` policy).
2. After a dish's interval is built and before ranking, Roli compares the **middle** of its range with the card's published range, per 100 g served
   (when the served mass is known) and per plate. The dish is **flagged** when the middle is above 1.5 x the published high or below the published low / 1.5
   on either comparison (`MvpConfig.reference_check_factor`, default 1.5). No card or no reference: no check; the diagnostics say "no reference".
3. A flagged dish is left out of the ranking and the recommendation (Julius, 2026-11-05). The result page lists it with the dishes not estimated, reason
   "our estimate disagrees with published figures for this kind of dish". The diagnostics show both numbers and which comparison failed. One line goes to
   `runs/flags.jsonl`: run, menu, dish, comparison, Roli's middle, published range, suspected question (eaten / how much / made of).
4. **A flag is temporary.** The aim is to fix the cause of the over- or under-estimate, not to exclude the dish. Each flag stays open in the review file
   until its cause is fixed in 12.2-12.4; the dish then returns to the ranking. Every checkpoint reports open flags and what closed them.

### 12.2 Dish-family cards (extends `portion_rules.csv`)

1. One row per dish family; the PR rows become cards. New columns: `ref_sat_fat_per_100g_low/high`, `ref_sat_fat_per_plate_low/high`, `ref_sources`,
   `typical_choices` (for example fish and chips: species cod | haddock | pollock; frying fat: vegetable oil | beef dripping).
2. **Evidence rule.** No card or weights row runs live without at least one measured figure in its sources. Rows whose basis says "no source" (today PR10
   and PR12, among others) run only with the reference check on and are listed in every checkpoint until sourced.
3. **Unnamed choices become the range, not an average.** When the menu does not name the species, fat or cut, Roli rebuilds the USDA Survey record from its
   inputs (`get_inputs`) with the card's low and high choice swapped in, and the spread is the dish's range. A menu that names the choice uses it ("cod and
   chips" -> cod only). This replaces fixed defaults such as "Fish, NS as to type, fried" (US mix: 27 g salmon and 16 g catfish of 65 g fish per 100 g).
   How the frying-fat spread is worded for testers stays Julius's open call.
4. New cards from today's review: `snack_bowl` (olives, nuts; replaces PR10 for these, plate weight and references from published figures) and
   `fish_and_chips` (white-fish species, frying-fat choices, references from UK pub disclosures).

### 12.3 One model call per dish: line tags (Julius, 2026-11-05)

1. One call per dish, all its recipes together, returns for every line: `role` = eaten | cooking_medium | removed, and `kind` = plain_food |
   prepared_product, each with a short reason. Code checks the answer: only fats, oils, liquids (brine, stock, water, wine, vinegar) and salt may be a
   cooking medium; anything else tagged medium is treated as eaten and logged. Tags and reasons appear in the diagnostics.
2. `cooking_medium`: never counted at its recipe weight and not part of the served mass. The eaten amount comes from USDA (the fried-food record) or a
   per-plate row (W09 for oil that clings to olives or vegetables). This replaces `FRYING_FAT_LINE` and `FRYING_BATH_MIN_G`, and supersedes section 11's
   "a confit still counts as the recipe states": confit oil, marinade, brine and poaching liquid are cooking media.
3. `removed`: left out of the calculation and the served mass (bay leaf, sprigs, rind, bones, aromatics lifted out).
4. If the call fails, the dish falls back to the current patterns and 12.4(b) is not applied; the diagnostics say so.

### 12.4 Lines that cannot move the result (I03 widened)

1. A line with a missing amount does not hold up a recipe when either test passes:
   (a) **amount**: an herb or spice, as I03 is built (dried spices can be fatty per 100 g but are used in pinches);
   (b) **composition**: `kind` = plain_food (12.3) and the matched USDA record, direct or stand-in, reports at most 0.1 g saturated fat per 100 g and
   0 mg cholesterol. At 0.1 g, even 400 g in a 4-serving recipe adds 0.1 g per serving, under the 0.25 g ranking tie.
2. Guards: USDA must report both nutrients, since a missing value is not zero (D23 stands). A prepared product (sauce, paste, condiment) never passes (b),
   whatever the match: the Flour + Water pork chop's "salsa verde" matched USDA's ready-to-serve (tomatillo) salsa verde at 0 g, while an Italian salsa
   verde is about half olive oil.
3. Such a line counts as zero for both nutrients, labelled `excluded_negligible` with the test used; a total that relies on it is
   `complete_with_inferences`, never `source_complete`.
4. Plate-weight method (P2): salt, zest, peel and citrus juice count as zero weight. Any other plain food with no weight (whole vegetables, heads,
   bunches) still stops P2, because leaving its mass out makes each plate's share too big. P3 is unaffected.
5. Measured on the four final runs of 2026-11-05: 347 of 913 holding lines are near-zero, but most recipes they hold up are also held by a fatty or
   unreported line; (b) with these guards frees 13 recipes in 8 dishes (The Greyhound's Sicilian olives becomes estimable).

### 12.5 USDA access

1. **Saved answers.** USDA answers (records, searches, portions) are saved on disk and reused across runs and restarts; the in-memory cache (1,000
   entries, empty in every new process) stays only as the fast layer. Refused or failed answers are never saved.
2. **Refusal.** At the first `rate_limited`, the run stops asking USDA; affected dishes are marked "USDA unavailable" and not ranked. Replacement recipes
   are fetched only for a recipe's own failure, never because of a USDA error.
3. **Allowance.** Read USDA's remaining-requests count from each response, show it on the run page, and pause before a reserve (proposal: 200).
4. **Refresh by USDA release, not by timer.** Each saved answer stores its data type and the FoodData Central version it came from.
   - SR Legacy answers are never refreshed (final release, April 2018).
   - Foundation answers (USDA updates April and October), Survey answers (every two years) and saved searches are refreshed when a new release is
     detected: new releases add records that can change which record a search picks.
   - Detection: one request at app start and once a day while it runs.
   - On a new release: keep the old answers as a snapshot, refresh paced under the allowance, rerun the four test menus and write a before/after file;
     the new data is used live only after Julius approves. Each run records the FoodData Central version it used.
   - Safety net: Foundation and Survey answers older than 7 months are refreshed even if detection fails.

### 12.6 Today's two cases in these terms

- Marinated olives: marinade oil is a cooking medium (12.3) with W09 for clinging oil; the `snack_bowl` card (12.2) sets the plate.
- Fish and chips: the `fish_and_chips` card's species and frying-fat choices (12.2); W40 stays for tartar sauce.
- Noted, not changed here: W39 prices salsa verde as a 3:1 oil-and-vinegar dressing (9.1 g/100 g); at about half oil it likely overstates by 15-35 %.

### 12.7 Tests and checkpoint

- Tests: reference-check boundaries (middle, 1.5 x, both comparisons) and the flag file; tag validation and the fallback; 12.4 with salsa verde held
  (prepared) and Maldon salt passing (stand-in); the P2 weight rule; saved answers surviving a restart; no replacement recipes after `rate_limited`;
  release detection with a fake.
- Rerun the four menus: before/after, open flags, coverage, USDA requests per run (a rerun of the same menus should make almost none).
- Correction to `CHECKPOINT_3C_survey.md` section 4.1: "897 lookups for the schnitzel" counts lookups, mostly answered from the in-memory cache, not HTTP
  requests. The 20:05 Greyhound run started with about 250 of the hour's 3,600 left (13 runs since 19:34 had made 3,353); of its 1,000 requests about 750
  were refused, and the refusals made the schnitzel's recipes look incomplete, which fetched more recipes.

### 12.8 Built at Checkpoint 3D (2026-11-05); where the build reads the section a particular way

- 12.1: `mvp/reference.py`. The dish's middle is (low + high) / 2 of its saturated-fat interval. The served mass for the per-100 g comparison is known
  only when every bounded recipe states one: P2 gives the rule's plate weight, P3 the fraction times the recipe's own mass when that mass is complete,
  the Survey estimate the sum of its components and additions; otherwise the per-100 g comparison is skipped and says so. The suspected question is a
  heuristic: a dish with a cooking-medium line -> "eaten"; a failed per-100 g comparison without one -> "made of"; a failure on the plate comparison
  alone -> "how much". Flags live in `runs/flags.jsonl`, identified by (photo file name, dish name); a run that finds the dish inside the range appends
  a `closed` line. Flagged dishes are listed with the unranked ones on the run page with the reason of 12.1.3.
- 12.2: cards are rows of `portion_rules.csv` (new columns `menu_words`, `ref_sat_fat_per_100g_low/high`, `ref_sat_fat_per_plate_low/high`, `ref_sources`,
  `typical_choices`). `snack_bowl` has two rows chosen by `menu_words` (PR13 olives, PR14 nuts) because olives and nuts have different published
  figures; `fish_and_chips` is PR15 (white fish, raw grams from measured served portions) with the chips side on PR12, which is now sourced (200-284 g)
  instead of "no measured source" (120-250 g). The rebuild (12.2.3) keeps every input of the Survey record at USDA's grams per 100 g, resolves each kept
  input to a USDA record by exact description in USDA's own search results, and swaps the choice groups (fish: the raw-fish inputs; oil: the fat inputs)
  for the card's lowest- and highest-fat choice; a choice the menu names is used alone. When an input cannot be resolved the record's own values stay
  in use and the diagnostics say why. The evidence rule: `for_dish_type(..., allow_unsourced=False)` when the reference check is off (PR05, PR09, PR10,
  PR11 are the unsourced rows today); weights rows carry the same `sourced` flag (none says "no source" today).
- 12.3: `recipes/tags.py`, prompt `LINE_TAGS_PROMPT`. One call per dish covers the chosen recipes and the ones a backfill round could still bring in (at
  most two times the cap), so a backfill never needs a second call. Beyond the spec's validation of `cooking_medium`, code also refuses `removed` on
  anything that is not an aromatic, rind, bone, shell or herb (a wrong "removed" on a main ingredient would empty the plate) and reads `kind` as
  `prepared_product` whenever the line's USDA record is a sauce, dressing, soup or gravy. A medium whose record is near zero (brine, water, stock) is left
  out entirely; a fatty medium stays an open line (`cooking_medium_unknown_amount`) that the adapted pair fills from a per-plate row (gap
  `G6_cooking_medium`; W09 for olive oil; no row for other oils, so the recipe stays open and the Survey record bounds a fried dish). Confit oil is
  therefore a medium too, superseding section 11.
- 12.4: rule I04 (`negligible_composition`), threshold `MvpConfig.negligible_sat_fat_per_100g`; applied to recipe lines with NO stated quantity (a counted
  but unweighed line stays with the weights table; a menu-only line stays with D8 and the weights table: both readings were corrected on the live reruns); needs the tags (off in the fallback). P2: `ZERO_WEIGHT_WORDS` (salt, zest, peel, rind, citrus juice); any other composition-excluded
  plain food still stops the plate-weight model; media and removed lines are not part of the served mass.
- 12.5: nutrition service v2.3 (`nutrition_service/SPEC.md` section 18). The agent's store is `roli/.cache/usda_store` (`MvpConfig.usda_store_dir`). The
  release check runs at the first run after start and once a day (`maybe_check_release`), never when USDA is refusing or the reserve is reached. A dish
  during which USDA refused is `usda_unavailable`; a dish is not started under the reserve (`skipped`, "USDA allowance reserve reached").

### 12.9 Changes after the Checkpoint 3D review (2026-11-06, Julius's decisions of 2026-11-06)

1. **Rerun on the final code.** The 3D "after" runs for The Greyhound and the seafood chalkboard are pass 2: they still zeroed 33 and 11 menu-only
   lines that had no tag (among them the Scotch egg's "Celeriac & Cranberry Remoulade", a mayonnaise sauce, matched to raw celeriac). Every
   before/after from here uses runs made on the code being reported.
2. **What a cooking medium is (tag prompt).** Only a deep-fry bath, a marinade, a brine, a poaching or boiling liquid, and confit fat are media. Oil or
   fat used to blister, sauté, sear, pan-fry or roast stays with the food and is `eaten`. When in doubt the line is `eaten`: an underestimate is the
   harmful error, because it can put a fatty dish at the top. Seen in 3D: all five Padron recipes (1-3 tablespoons in a skillet for 4-6 servings) and
   the searing oil for fish were tagged media.
3. **A fixed tag test set.** A list of recipe lines with their expected tags, run against the live tag call: the cases in 12.9.2, plus pasta water
   (medium), water in a soup (eaten), bay leaf and herb sprigs (removed), dressing and drizzle oil (eaten), oil on a grill grate (medium), olive oil of a
   marinade (medium), confit fat (medium), brine (medium). Lines whose expected tag is unclear are listed for Julius, not decided by the build. The
   report counts errors in the harmful direction (an eaten line tagged medium or removed) separately.
4. **Shorter tag answers.** The `reason` is written only for tags that change the calculation (cooking_medium, removed, prepared_product); about 81%
   of lines in the 3D runs were eaten plain foods. Still one call per dish.
5. **Repeatable reruns.** Relevance grades and line tags are saved like pages, keyed by the page, the menu item, the prompt version and the model, and
   reused on a rerun. Seen in 3D: with the same 12 saved pages, the grader called arcisfoodblog's poke "same dish" before and "variant" after, so the
   recipe that set the poke's 0.3 g low was not processed and the top dish's low moved from 0.3 to 2.9 g. `compare_mvp_runs.py` gains a "grading
   changed" reason, separate from "search results or cache".
6. **Reference check: two figures minimum.** A published range (per plate or per 100 g) can flag a dish only when it rests on at least two independent
   figures: different businesses, or different brands for retail labels; several dishes from one chain count as one. A single figure is shown in the
   diagnostics but does not flag. (Consequences today: the Sicilian olives' plate check, Pizza Express only, stops flagging; the fish and chips plate
   check, Wetherspoon only, stops until a second business's figure is found.)
7. **Reference check: compare like with like.** A reference figure may carry the choice it represents (for example frying fat = vegetable oil), recorded
   with its basis: stated by the business, or shown by the figure itself (for a fried dish, a saturated share of total fat below 20 % means a liquid
   vegetable oil, above 35 % means beef dripping or palm; `MvpConfig` values). A labelled figure is compared with the middle of Roli's range for that
   choice only; an unlabelled one with the middle of the whole range, as now. A choice with no reference is not checked.
8. **One frying fat per plate.** All fried components of one plate take the same fat choice at each end of the range (the fish and chips come out of the
   same fryer). For the chips: if USDA's Survey data has a fried-from-fresh potato record whose inputs include the oil, it is rebuilt like the fish;
   otherwise the restaurant fries record stays and the diagnostics say the chips cannot follow the fat choice.
9. **Flag lines name the top contributors** (the components or lines with the largest share of the middle) instead of a guessed question; the review
   classifies each flag.
10. **Two sourced rows.** (a) Clinging marinade oil for olives, in grams per 100 g of olives so it grows with the bowl, from published labels (the
    Pizza Express olives label: total fat minus the olives' own fat; retail marinated-olive labels); it fills a marinade medium on `snack_bowl` olives
    instead of W09, which stays the drizzle row. (b) Tartare sauce, from measured figures (bottled UK tartare labels; a pub-made or home-recipe figure if
    one is published); W40 stays for mayonnaise. Every figure cited; none invented; if a range cannot be sourced, say so and leave the row unbuilt.
11. **Kept from 3D:** the guards refusing `removed` on anything that is not an aromatic, rind, bone, shell or herb, and reading a sauce, dressing, soup
    or gravy record as a prepared product.
12. **Provenance and text corrections.** The two olive pages the build could not reach are labelled "found by web search, 2026-11-05", not
    "read by Julius". Dated notes in `CHECKPOINT_3D.md` correct: the poke change (12.9.5, not search variability); the Sicilian olives became
    estimable because the lemon peel was tagged removed, not through rule I04; the Greyhound and seafood "after" runs were pass 2 (12.9.1).
13. **Tracing.** `LANGSMITH_TRACING=false` in `.env` until LangSmith's monthly quota resets; no other line of `.env` changes.

### 12.9a Built at Checkpoint 3E (2026-11-06); where the build reads 12.9 a particular way (numbered 12.10 until 2026-11-06, renamed because 12.10 below took that number)

- 12.9.2-4: the tag prompt also shows, per recipe, up to four method sentences that name a fat, a liquid or how the food is cooked (`tags.method_sentences`): the words of a line alone cannot tell a
  frying bath from a skillet's oil. Oil wiped on a grill grate is listed as a medium because 12.9.3 expects that tag, though 12.9.2's list does not name it. The test set is
  `tests/fixtures/line_tag_test_set.json`, its runner `scripts/eval_line_tags.py`, charged to the spend ledger.
- 12.9.5: `recipes/judgements.py`, files under `.cache/roli_mvp/judgements/`. The page key is its canonical URL plus the hash of its ingredient lines; the prompt version is the hash of the prompt text; the menu item key ignores case and punctuation. Saved tags are the model's answers and are validated again on every load. Thirty days, like a saved page.
- 12.9.6-7: the published figures left `portion_rules.csv` for `recipes/reference_figures.csv`, one row per figure, because the check needs each figure's business, basis and total fat; this replaces the `ref_*` columns of 12.2.1. `group` is the owner, so Yates and Slug & Lettuce (both Stonegate) count once. One basis can give several comparisons, one per fat label.
- 12.9.8: `typical_choices` gains a `potato` group that names the record to use for chips when the plate has a fat choice. USDA has one: 2709458 "Potato, french fries, from fresh, fried", with Vegetable oil, NFS among its inputs.
- 12.9.8 and USDA's inputs: section 11 and 12.2.3 read `ingredientWeight` as grams per 100 g of the finished food. It is the recipe before cooking; `nutrition_service/SPEC.md` section 19.
- 12.9.10(a): row W57, `amount_basis` `per_100g_key`; 12.9.10(b): row W56 on USDA's own tartar record, because a nutrient value may only come from a USDA record: the labels judge the record, they do not enter a total.
- 12.9.5, result: grades and tags are saved, the menu reader's answer is not, and the reader's text reaches the search query with its punctuation. Pass B therefore did not match pass A exactly (`CHECKPOINT_3E.md` section 4; `scripts/repeatability.py`). Saving the reading and stripping punctuation from queries are left for Julius's decision.

### 12.10 Changes after the Checkpoint 3E review (2026-11-06, Julius's decisions of 2026-11-06)

1. **Raw-flesh conversion on the finished-food basis (bug).** USDA's input weights are weights before cooking; the rebuild already scales them by
   `grams_per_100g_scale`, but `survey._amount` divides the raw-flesh rules by the unscaled raw share (65), so fried fish, squid and chicken plates are
   about 15-17 % too heavy and too fatty. The raw share is the scaled one (raw-flesh input grams x `grams_per_100g_scale`); when a record gives no
   moisture change, the unscaled share stays and the diagnostics say so. PR15's raw grams were derived from measured fried weights with the same
   unscaled 65 g: recompute them with the scaled share, so the round trip returns the measured fried weights (131.4-170 g).
2. **What a cooking medium is (tag prompt, adds to 12.9.2).** A marinade is a medium only when the food is lifted out and the liquid is drained, thrown
   away or left in the jar; a marinade brushed on, cooked with the food or served on the plate is eaten. A cup or more of oil used to fry, deep or
   shallow, is a medium. A poaching liquid is a medium unless the recipe turns it into a sauce or serves it.
3. **The 12 unclear lines, decided** (add them to the tag test set): shallow-fry with 1 cup of oil = cooking_medium; poaching milk = cooking_medium
   unless made into a sauce; soy sauce in a discarded marinade = cooking_medium; lemon in a fish cavity = removed; lemon rind strips in a marinade =
   removed; steeped garlic, semolina for the peel, roasted garlic heads, cooking spray and couscous water = eaten; salt for pasta water and oil covering
   carrots that are then drained = cooking_medium. Stock and sausage are `prepared_product` (several ingredients, composition varies by maker): correct
   the test set's expected answers.
4. **Search queries are cleaned** before searching: lower case; punctuation, asterisks and footnote marks removed; sizes, weights and prices dropped
   ("10oz", "£14"). One rule in the query builder, for every dish.
5. **Saved reading for test reruns.** The menu reader's answer is saved per photo (keyed by the image's hash, the reader prompt version and the model)
   and reused when `MvpConfig.reuse_saved_reading` is on (on for evaluation reruns, off by default). The reader is measured on its own: each checkpoint
   reads one photo twice, fresh, and reports what changed.
6. **New potatoes side row**, sourced like every row; butter is added only when the menu says buttered.
7. **D25 same-food test.** A borrowed cup weight needs the same food, not the same first word: "Cheese, parmesan" and "Cheese, cottage" are different
   foods. Seen in 3E: "1/4 cup thinly sliced Parmesan" took 60 g from a cottage cheese record (about 20-25 g expected), overstating a fatty cheese about
   2.5 times.
8. **W27 (cream)** gets an exclude pattern for "cream of tartar".
9. **Frying-fat wording for testers (Julius, 2026-11-06).** When a dish's range spans the card's frying-fat choices, its line reads:
   "{dish}: about {low}-{high} g saturated fat if fried in {lower-fat choice}, up to about {top} g in {higher-fat choice}. Ask what they fry in."
   Figures and choice names come from the computed ranges and the card, never written by hand. The dish still ranks on the middle of its full range.
   The sentence is never dropped by the word limit; optional sentences go first.
10. **Fish and chips flag:** classify only after item 1 is applied and the menus are rerun. If the chips are still the top contributor, it is "made of:
    chips" (USDA has no thick-cut chips record), and the flag stays open. Nothing is tuned to pass.
11. **Small faults:** `runs/flags.jsonl` gets a line only when a flag opens or closes; the closed-flag report stops printing "None".
12. **Deferred:** the rerun against staged USDA answers (12.5.4) waits for the next release; Foundation Foods was last published 2026-10-29 and is
   updated in April and October.

### 12.11 Built at Checkpoint 3F (2026-11-06); where the build reads 12.10 a particular way

- Numbering: two sections carry the number 12.10, "Built at Checkpoint 3E" and "Changes after the Checkpoint 3E review". References to 12.10.n mean the second.
- 12.10.1: `survey._amount` takes `grams_per_100g_scale`. Every fried seafood record has 65 g of raw flesh in a 100.6 g recipe with a -15% moisture change: raw share 76.01 g, plates 14.5% lighter. The fried chicken record is not affected, though the spec names it: its flesh input is already-cooked chicken, so no raw-flesh rule applies and USDA's own serving measures size it. PR15 is now 99.9-129.2 g raw. Because PR15's raw grams and the conversion both changed, its plate stays the measured 131.4-170 g: fish and chips does not get 15% lighter.
- 12.10.2: the tag prompt shows up to eight method sentences (was four), and the sentence filter also picks brush, drain, discard, lift, reserve, spoon, pour, sauce and serve: what happens to a marinade comes late in a method.
- 12.10.3: the guards gain "soy sauce" and "tamari" as liquids and "lemon" as removable, which the decided lines need; 12.9.11's guards otherwise stay. "Lemon in a fish cavity" is scored on a new fish recipe; the set's existing roast-chicken lemon is read the same way. Cooking spray's role is decided, its kind is not, so that line's kind is not scored. Added beyond the 12 lines: the two real 3E misses, a poaching milk made into a sauce, a marinade cooked with the food.
- 12.10.4: `ingest.clean_query`, applied to the name, the section and the first description word separately, before the generic-section test, so "DESSERTS 8" is the generic "desserts". A bare number is dropped only at the end of the text ("7 layer dip" keeps its 7). Accents are kept: the spec does not list them, so "aïllade" and "aillade" stay two searches.
- 12.10.5: `mvp/readings.py`, files under `.cache/roli_mvp/readings/`, no expiry. Every fresh reading is saved; `eval_mvp --reuse-saved-reading` turns reuse on. `scripts/reader_check.py` reads twice without saving.
- 12.10.6: W58 plain and W59 buttered. Two to three new potatoes at USDA's 60 g each, 120-180 g. Butter is not a separate line: W59 is USDA's "made with butter" record, as W55 is for peas.
- 12.10.7: `equivalence.same_food`. The lender's first segment must match and every word naming its variety must be in the record; a lender naming no variety ("Onions, raw", "Olives, NFS") is the plain food and may lend. D25 also searches the first two segments before the head, because a head search for "Cheese" never returns Parmesan: a stricter test alone would leave those lines without a weight.
- 12.10.9: `ranking.frying_fat_line`, on `RankedDish` and `Unranked`. A ranked dish among the top three carries it in the recommendation, in place of its range. A flagged dish is not ranked, so it is not in the recommendation; its line in "Could not be ranked" on the page carries the sentence. With two such dishes the reply may pass 80 words, because neither the sentence nor the disclaimer may be cut.

### 12.12 Changes after the Checkpoint 3F review (2026-11-06, Julius's decisions of 2026-11-06)

1. **Food stored or served in oil (corrects 12.10.2).** Where the oil ends up decides. Oil a food is stored in or served out of (a jar or bowl of olives,
   feta or vegetables in oil, a confit) is a cooking medium; the eaten part is the oil that clings. The tag prompt gets this as one general sentence.
   The `snack_bowl` card gets a setting for olives: their oil lines are cooking media and W57 supplies the clinging oil (card data, not a code branch).
   A food in oil with no clinging-oil row stays open and unranked; its eaten oil is never guessed. The rest of 12.10.2 stands: a marinade brushed on,
   cooked with the food or served on the plate is eaten. Seen in 3F: five olive recipes had 54-216 g of oil tagged eaten, Zuni's olives were flagged
   at 5.4 g per 100 g against published 1.7-2.8 g, and W57 no longer fired.
2. **Near-zero rule for small items (amends 12.8).** Rule I04's composition test also covers counted lines of zest, peel, citrus juice and salt
   ("4 strips of lemon peel"), which 12.4.4 already counts as zero weight on P2. Whole vegetables, heads and bunches with no weight stay excluded (the
   little gem case behind 12.8).
3. **Reader: lines shared by several dishes.** Reader prompt v6 = v5 plus one rule: a line that describes several dishes is not a dish; attach it to
   each dish it describes. Run the existing reader evaluation (`roli/code/full_run.py`, scored per `menu_reader_eval/scoring_rules.md`, 25 photos, each
   sent twice) for v5 and v6 on Roli's current reader model. Report every pass bar, "invented 0 on both runs" first. Roli switches to v6 only if v6 is
   no worse than v5 on any pass bar; otherwise report and keep v5. Photo 23 is the seafood chalkboard. Seen in 3F: on a second fresh reading, the
   chalkboard's shared garnish line became a dish of its own.
4. **D25 lenders: same food first.** A cup weight is borrowed first from the same food in any USDA data type (for example SR Legacy's walnut record
   before "Nuts, NFS"). A class-level record (NFS, a whole category) lends only when no same-food record has the measure, and the line is labelled
   `class_level_cup_weight` (`complete_with_inferences`).
5. **The recipe's own grams win.** A weight stated on the line ("1/3 cup pecorino romano (33g)", "4 oz / 113 g") is used before any cup conversion.
6. **Flag status "known limit of the data".** A flag whose cause cannot be fixed within USDA is recorded with this status and its reason in
   `recipes/known_limits.csv` (card, top contributor, reason, date, decided by). The dish stays out of the ranking and keeps its line under "Could not
   be ranked", but the flag no longer counts as an open to-do. Only Julius adds a row; the build never sets this status on its own. First row:
   `fish_and_chips`, chips, "USDA has no thick-cut chips record", 2026-11-06, Julius.
7. **Failed pages in test reruns.** With `reuse_saved_reading` on, a page that failed in the saved pass stays failed; live runs retry failed pages.
8. **Escape text on every page.** Text from the reader, a model or a fetched page is HTML-escaped wherever a page shows it. Test with a menu name that
   contains markup.
9. **Tag tests from real pages.** Every tag miss found on a real page becomes a test case built from the saved page, whole recipe, as the tag call sees
   it. First cases: the five olive recipes of 3F (thecozyapron, foodiecrush, foodnetwork, budgetbytes, NYT) and the Sicilian olives' sprigs and peel.
   The made-up cases stay.
10. **Correction to 12.10.1:** it named chicken; USDA's fried chicken record starts from cooked chicken, so the fix does not apply there (as built in 3F).

### 12.13 Built at Checkpoint 3G (2026-11-06); where the build reads 12.12 a particular way

- 12.12.1: the sentence sits in the prompt's list of cooking media. The card setting is a new column, `medium_record_head`, in `portion_rules.csv`: `oil` on PR13, empty elsewhere. On that card a line matched to a record with that first segment becomes a medium even when the model says eaten, and the note says so. It runs only when tags are available. W09 still answers olive oil on any dish, so "stays open" holds for oils with no row, and a food stored in olive oil outside the olive card gets W09 (seen on the house-cured anchovies, no portion, no effect on a ranking): the tags cannot tell stored oil from grill oil. Open for Julius.
- 12.12.2: `ZERO_WEIGHT_WORDS` moved to `recipes/inference.py` and is used for both P2 and the composition test. It keeps "rind" and "juice of", as 12.4.4 does.
- 12.12.3: "no worse" is read strictly at the precision the harness prints, over 14 lines (each run separately where the bar says both runs), using the `as_written` verdict with photo 17 in. Written down before the batches ran: `results/reader_v5_v6_decision_rule_2026-11-06.md`. Result: not met, v5 kept. `ROLI_MENU_PROMPT` still defaults to v5. The harness's model calls are outside the budget code, so their cost was added to the ledger by hand. LangSmith answered 429 on trace upload; local results are complete.
- 12.12.4: `equivalence.same_food` has three cases, and refuses raw against cooked and a colour the record lacks. Case 2 (same first two segments) needs the second segment to name the food, not a state (`STATE_SEGMENTS`). Case 3 (a lender filed under the food's own name) applies only to `OWN_NAME_HEADS`: nuts, seeds, sausage. Class-level means a record naming no variety that is NFS or sits under `CLASS_HEADS`; "Onions, raw" and "Tomatoes, raw" are the plain food and not class-level. Both lists are judgement calls. `class_level_cup_weight` is a new inference kind and keeps a scenario out of `source_complete`.
- 12.12.5: a note counts only when a piece of it is a weight and nothing else, so "from a 14 oz can" stays ignored. Prices are dropped first. Two systems: the metric one wins, also over a weight line's own ounces ("4 oz / 113 g"). A stated range on a volume line is read at its midpoint with `range_midpoint`. A page's weight also beats the 1 g/ml assumption for water-like liquids. Brackets are now matched in pairs, which also cleans food names ("shallots )" is "shallots", and "$1.78)" no longer lands in a name), and a measure after a slash leaves the name. Weights in count lines keep the 2B per-item rule.
- 12.12.6: the table's `card` column holds the dish family (`fish_and_chips`); flags carry the row id. A row applies while its contributor is, as a whole word, in the dish's top contributor line, so a different top contributor reopens the flag. Status `known_limit` replaces `open` in `flags.jsonl` and leaves `open_flags()`; a later pass of every check closes it. `totals.dishes_flagged` now excludes known limits, which `totals.dishes_known_limit` counts.
- 12.12.7: `fetch.FailedPages`, file `.cache/roli_mvp/failed_pages.json`, all failure kinds. A live success clears a page. Sealed mode reads only. The check comes before the page cache.
- 12.12.8: `autoescape=True`. `select_autoescape(["html"])` matched nothing, because the template names have no extension.
- 12.12.9: `scripts/build_real_tag_cases.py` builds the cases from the saved pages; the roles are hand-written there. Set version 3: 39 recipes, 149 lines, 45 of them real. Whole peppercorns are labelled eaten and the model says removed, which is scored as 2 harmful misses with no effect on a figure. The tag set does not use the card setting, so Ina Garten's oil stays a miss in the set while the card catches it live.

### 12.14 Changes after the Checkpoint 3G review (2026-11-06, Julius's decisions of 2026-11-06)

**How changes are chosen from here (Julius, 2026-11-06).**
1. A rule is about a kind of ingredient, cooking step or dish family, never a named dish or food.
2. One wrong dish is a reason to look, not a reason to add a rule. A rule is added when the same cause shows up in several dishes, preferably on
   different menus, or when the issue is material (it stops many dishes being assessed), and then as a rule that works broadly. Otherwise the dish
   stays unranked or keeps its wider range.
3. Bugs (code doing something different from its own stated rule) are always fixed.
4. When results are similar, removing or merging rules beats adding them.

**Decisions on Checkpoint 3G.**
1. **Reader:** Roli stays on v5; v6 is not adopted and not rerun. The answer key for photo 23 attaches the shared garnish line to each fish it
   describes instead of listing it as a dish (back up the key first, as its history does; rebuild the expected files with `code/build_expected.py`).
2. **Cooking media, one rule:** every cooking medium (a marinade, oil a food is stored or served in, frying oil that no USDA fried-food record covers)
   gets W09's clinging amount; a USDA fried-food record covers deep-fried dishes as now. W57 and the `snack_bowl` olive setting of 12.12.1 are removed;
   12.12.1's "never guessed" is withdrawn; no "stored in oil" tag. The tag prompt's general sentence on oil a food is stored or served in stays.
3. **External bounds attach to the line they bound**, whether or not an adapted pair is built (the Margherita in 3G, the crudo's bottarga in 3D).
4. **Snack bowls are listed apart:** dishes on the `snack_bowl` card do not enter the top three; they get one line, "Light snack: {name}, {range}",
   which is the first line dropped under the word limit.
5. **Tag tests:** when a line's tag cannot move any figure, either answer passes; "harmful" counts only misses that would move a figure.
6. **Count lines:** "3 large (560 grams)" means 560 g in total; only "each" or "per" makes a weight per item.

**Coverage fixes.** On the four 3G menus, 23 of the 46 evaluated dishes were not ranked: 14 had no upper bound (an unweighed or unreported line in every
recipe), 8 could not be portioned, 1 is a known limit. These fixes target the broad causes.

7. **Missing nutrients: two facts** (they replace rules I01 and I02; D24 stays off; D23 stands). USDA lists a nutrient only when it was measured, so an
   absent value means "not measured", not zero.
   (a) **A plain plant food has no cholesterol** (only animals make it): the line's kind is `plain_food` and its USDA record is in a plant category
   (vegetables, fruits, cereal grains and pasta, legumes, nuts and seeds, spices and herbs, plant oils). Not animal fats, not prepared products (pesto,
   dressings). Labelled as an inference, like I01.
   (b) **Saturated fat cannot exceed total fat:** when a record reports total fat but not saturated fat, saturated fat is the range 0 to total fat. The
   nutrition service also requests total fat (nutrient 204); library spec update. A fatty food whose saturated fat is unreported (pork belly) stays
   missing.
   Seen: 86 line occurrences held up by a missing nutrient: 45 plant foods missing only cholesterol (vinegars, plant oils), 37 plant foods missing
   both (onions, tomatoes, rocket, spinach, flour, beans, mushrooms, apples), 4 others.
8. **Measures.**
   (a) Reading fixes: a weight written in the line, hyphenated or in brackets ("17-ounce log", "5-ounce package"; 12.12.5); a size word anywhere in
   the line, brackets included, whatever brand names or extra words surround it ("2 Eggland's Best eggs (large)", "2 cold large eggs"); a record's
   whole-item measure named in its own words ("eggplant, unpeeled (approx 1-1/4 lb)") is one item when the line names no size.
   (b) Same-food measures: when the chosen record lacks the measure a line uses, take it from another USDA record of the same food (D25's same-food
   test, any data type): whole-item sizes, slices, spoons (also from a cup weight: 1 cup = 16 tbsp = 48 tsp). A size no record has ("small",
   "Japanese") is never stretched from another size.
   (c) Audit: sort every `no_usda_portion` line on the four menus into reading bug, measure in a same-food record, or real gap, before and after.
9. **Millilitres for any liquid:** ml and l convert to US spoons and cups (the NIST factors in `convert.py`) and are weighed through the record's spoon
   or cup measure, or a same-food record's (8b). Seen: 11 lines ("200ml rapeseed oil", "125ml double cream").
10. **Pizza:** a pizza recipe makes one pizza unless the page says otherwise. When the dough weight is known (stated, a crust's weight, or the sum of
    the recipe's own dough lines when all are weighed), one plate is one restaurant pizza: plate share = a published restaurant dough-ball weight
    (a cited range) / the recipe's dough weight, capped at the whole recipe. When it is not known, one plate is the recipe's pizza. Seen: 12 of 15 pizza
    recipes make one pizza but were refused because the page does not say so; all four pizzas were unranked.
11. **Shellfish count as seafood:** the fish cards' key record includes shellfish (shrimp and prawns, scallops, crab, lobster, mussels, clams,
    oysters). Seen: 9 portion failures, "no 'fish' line".
12. **One near-zero rule** (replaces test (b) of 12.4, the narrowing in 12.8 and 12.12.2): a line whose kind is `plain_food` and whose USDA record shows
    at most 0.1 g saturated fat per 100 g and 0 mg cholesterol (reported, or by 7a and 7b) never holds up a recipe, whether it comes from the recipe or
    the menu and whether or not it has a quantity. The rule sets that line's nutrients only; its weight is still found by the weighing steps, and the
    plate-weight method (P2) still needs it (salt, zest, peel and citrus juice count as zero weight, 12.4.4). Menu-only lines join the per-dish tag
    call so they get a role and a kind. I03's amount test for herbs and spices stays.

**Wider menu run.**
13. Run Roli on the other 21 photos of the 25-photo test set (`menu_test_set/telegram_1280/`), plus the four, on the final code. Review only what a
    tester sees: the top three, the light-snack line and the "Could not be ranked" list. The main measure is coverage: the share of food dishes ranked,
    and the dishes not ranked or excluded by cause, per menu and overall. List causes by how many dishes they affect and say which recur across menus.
    Watch in particular: burgers and sandwiches (no portion rule; a burger with a bun is read as a sandwich), shellfish starters, inconsistent
    classification (3G's barramundi), the 14-dish cap, fatty menu-only ingredients without a weights row. Nothing found in the wider run is fixed in this
    checkpoint; it is reported for Julius to decide under the principles above.

### 12.15 Built at Checkpoint 3H (2026-11-06); where the build reads 12.14 a particular way

- 12.14.1: key backed up as `menu_test_set/answer_key_backup_before_23_garnish_edit_2026-11-06.csv`; the line is now the description of the four fish and no longer a row; `code/build_expected.py` rebuilt the files. The LangSmith dataset was not updated: `code/full_run.py` scores from `expected/`.
- 12.14.2: `adapt._fill_medium`: every medium takes W09's amount per plate on the line's own record (W09's record only when the line has none). A dish `survey.fried_record_covers` answers for keeps its recipes' oil open. W57, the `gaps` and `key_record_head` columns of the weights table, `medium_record_head` on the cards and the `per_100g_key` amount basis are removed.
- 12.14.3: `compare_dishes.scenario_interval` reads the published scenario the same way as a pair when no pair exists; the separate lower-bound branch is gone.
- 12.14.4: `RankedDish.snack`. Snack bowls are moved after the plates and renumbered; the line is optional text 3, dropped first. Several snacks share the one line. A menu with only snacks says so. The word count of "Among the N dishes" still includes them.
- 12.14.5: `eval_line_tags.moves_a_figure`: herbs and spices (I03), salt, zest, peel, citrus juice, sprigs, whole peppercorns and bay. Other near-zero foods such as garlic still count, because their weight reaches the plate weight.
- 12.14.6: **a reading to check.** A plain bracket after a count is the line's total, as decided. Two forms stay per item although they do not say "each": a hyphenated weight ("4 (6-ounce) fillets", "2 (6- to 8-oz.) steaks") and a bracket straight after the count ("2 (400 g) cans"). Read literally, four 6-ounce fillets would be 170 g in total and the sauce would come out four times too large on the plate. A weight with no bracket ("2 400g tins") also stays per item, as before.
- 12.14.7: `inference.NutrientFacts`. (a) plant means USDA's own category: vegetables, fruits, cereal grains and pasta, legumes, nut and seed products, spices and herbs, and "Fats and Oils" records named "Oil, ...". (b) **a reading to check:** "a fatty food stays missing" needed a line, and the spec gives none, so the fact applies at or under 3 g of total fat per 100 g, the EU "low fat" condition (Regulation (EC) 1924/2006, Annex). On the four menus every record it answers has under 2 g, and pork belly has 35.8 g. Saved USDA answers with saturated fat missing are read again once for total fat; library v2.5 (`nutrition_service/SPEC.md` section 20). Without line tags 7a does not apply, so a dish whose tag call fails has lost what I01 and I02 gave it.
- 12.14.8: `ONLY_DESCRIBES` moves a first comma piece that only describes the food out of the name ("crisp, fresh romaine lettuce"). A label in the record's own word is one item unless it is a yield. `SIZED_VARIETIES` (Japanese, Chinese, Thai, Indian) count as named sizes. A lent whole item must name a word of the line or a size, "Quantity not specified" is never an item, and class-level records lend cups only. Spoon and cup measures that disagree by 2-5 % answer by the nearest in size; over 5 % still refuses.
- 12.14.9: `ml` and `l` go through `_derive_volume`.
- 12.14.10: PR01 is now the dough ball, 200-280 g (AVPN). Its diameter columns and the area ratio are removed. A page that reserves dough is still refused, and pan, deep-dish and sheet pizzas still are. `portions.dough_weight`: a line naming dough or crust with grams, else flour, water, yeast and salt when each line with a quantity is weighed; flour and water are both required, and dusting lines are skipped.
- 12.14.11: PR02, PR03 and PR11 list USDA's shellfish heads, both the grouped ones (Crustaceans, Mollusks) and the Foundation names (Shrimp, Scallops, Crab, Lobster, Mussels, Clams, Oysters). PR15 stays fish.
- 12.14.12: a near-zero line with a stated amount and no USDA weight keeps `mass_gap`; `_adapt_one` still looks for its weight (`Assumption.mass_only`), and only a weighed line leaves the plate-weight stops. Menu-only words are one more block in the tag call, saved like a recipe's tags. A cooking medium uses the same `near_zero` test.
- 12.14.13: `scripts/wider_run.py` starts a photo only when a whole menu's limits fit under today's caps, and otherwise waits for the next local day; `scripts/coverage.py` reports it. Julius cut the run short on 2026-11-06: it stopped after menu_10, menus 11 and 19 ran by `eval_mvp --daily-budget-usd 6.50` (his decision, for those two only, and not reached), and 12-18, 20-22, 24 and 25 were not run.


### 12.16 Changes after the Checkpoint 3H review (2026-11-06, Julius's decisions of 2026-11-06)

The wider run (13 menus, 400 food dishes) ranked 51 dishes, 13 %. 185 dishes had no portion rule for their kind of dish, 97 were cut by the dish
cap, 51 were tried and failed. Three menus showed an impossible figure. This pass fixes the two safety faults, rebuilds the plate-size table from
measured restaurant data, and replaces the dish-kind word lists with a checked model call. The principles of 12.14 apply.

**Decisions on Checkpoint 3H.**
1. Count lines: a weight between the count and the item is per item ("4 (6-ounce) fillets", "2 (400 g) cans"); a weight after the item is the
   total unless the line says "each" or "per". The 3H reading stands.
2. The "fatty food" line for 12.14.7(b) is 3 g of total fat per 100 g, the EU "low fat" claim limit (Regulation (EC) 1924/2006, annex). Config value.
3. **Plate-share ceiling:** one plate is never more than one whole recipe, in every portion model. A recipe whose plate share would exceed 1 is not
   used for portioning, and the diagnostics say so. (Seen: a dip at 513-1076 g saturated fat, 18.5 recipes; squid 6.9; soups 3.3.)
4. **The empty-menu sentence:** when no dish was tried, the reply says Roli cannot size the dishes on this menu yet and names them with their
   kind ("sandwiches, toast, granola"); "no estimate had an upper bound" is used only when estimates were tried.
5. The 14-dish cap stays. No cheaper models. Store-bought dough, wine pairings read as ingredients and the unstable olive tag are recorded in the
   checkpoint, not fixed.

**Plate-size table rebuilt from measured restaurant data.**
6. **Sources, in order:** (a) MenuStat (NYC Department of Health; the 100 largest US chains, 2012-2019; serving size, saturated fat, cholesterol
   per item; free download at menustat.org); (b) current chain nutrition sheets published by the chains themselves (for example Pizza Express,
   Wetherspoon, Nando's, Chipotle, Panera, Denny's); (c) retail labels only where (a) and (b) have nothing. Nutritionix is not used (paid; its terms
   forbid storing its data). Every figure cites its source and read date; third-party listings are labelled third-party.
7. **Method, one pass for every family:** group the chain items by dish family; take the serving weight range as the plate weight (the 10th-90th
   percentile, with the count of items behind it); take the saturated-fat and cholesterol ranges as the card's reference figures for the 12.1
   check (the two-figure minimum of 12.9.6 and the like-with-like rule of 12.9.7 still apply); keep the key-ingredient share for P3 families
   (meat, fish, pasta, dough) by converting the plate weight with USDA's own input shares, as the fish and chips card does. Each row records
   `n_items`, `sources`, `read_on`. Where chain data describes a bigger or richer plate than independent restaurants serve, the row says so; nothing
   is adjusted by hand.
8. **Existing rows (PR01-PR15):** every row is rebuilt or confirmed from 6-7. A row with no measured source after the pass is marked `unsourced` and
   its dishes are not ranked.
   **8a. What makes a plate-size row sourced (Julius, 2026-11-06, evening).** A row's key weight is the protein weight for a P3 family and the plate weight
   for a P2 or P1 family. The row is "sourced" when a measured figure for that key weight exists in either: (a) USDA FNDDS portions: the portions USDA
   attaches to a Survey (FNDDS) food record, read through the nutrition service's existing portions call (the same foodPortions data Roli already uses for
   cup and item weights); use a gram weight for a restaurant, fillet or whole-dish portion, never a spoon, cup or slice; (b) chain figures: MenuStat items or
   chain sheets, from at least two businesses. A chain figure from one business alone makes the row "single_source". No figure from either makes it
   "unsourced", and dishes of that kind are not ranked. Record both on the row; never drop one because the other exists. How the two figures are used: every
   row shows the FNDDS figure and the chain figures side by side, each with n_items and sources; until Julius approves a row, its range is the FNDDS figure
   when FNDDS gives the key the family needs (fish alone for a fish main, whole plate for pizza), otherwise the chain figure; when FNDDS and the chain figures
   disagree by more than a third, the row is marked "sources_disagree" in the table and the checkpoint, and still runs; Julius chooses the final range when he
   approves the row, and approved_by stays empty on every row. Code checks that a proposed FNDDS portion exists on the record and is a whole-dish, fillet or
   restaurant portion. Built: `scripts/fndds_portions.py` (the lookup and `eval/fndds_portions_<date>.md|json`), `scripts/build_cards.py` (`fndds_figure`,
   `apply_fndds`, columns fndds_low/high/n/basis/records, chain_low/high/n/businesses, range_source, sources_status).

9. **New families:** burgers and sandwiches (one plate = the whole item, bun included; wraps and tacos with them, as their own rows if the data
   separates them), breakfast plates (eggs, pancakes, toast plates, granola and porridge), soups, dips and spreads, sides (fried potatoes stays PR12;
   add salads, vegetables, rice, bread), desserts, children's dishes. The excluded-section rules for desserts, sides and children's menus are
   removed; those dishes are ranked and listed like any other, and remain subject to the lean-word selection under the cap.
10. **Approval:** every row, new or rebuilt, is `proposed_unreviewed` until Julius approves it. The checkpoint presents the whole table (family, plate
    weight, key share, reference ranges, n_items, sources) for review; `approved_by` and `approved_on` are filled only by Julius. Until approval the
    rows run under the reference check as now.

**Dish kind by model.**
11. One model call per menu classifies every food item into one of the card families (or "not a dish", "drink", "add-on"), with a one-line reason.
    Code checks the family exists and that add-on rules of the reader are respected; an unknown answer falls back to the current word lists and is
    logged. The call uses the same model as the line tags. Answers are saved like tags (12.9.5), so reruns repeat.
12. **Labelled set first:** from the 13 run menus, label every food item with its family by hand (the agent proposes, Julius reviews the disagreements),
    then measure the model and the word lists against it. The model goes live only if it is at least as accurate overall and on the cases that
    failed in 3H (misspelt fish, shellfish, soups, dips, invented pizza names). Report accuracy per family.

**Measure.**
13. The same coverage table on the same 13 menus (3H pass A runs as "before"): ranked share overall and per menu; the "no portion rule" and
    "misclassified" counts; no plate share above 1 anywhere; every card row with a source; spending per menu. The wider run's other photos are not run.

### 12.17 Built at Checkpoint 3I (2026-11-06 and 2026-11-07); where the build reads 12.16 a particular way

Numbered as 12.16. Readings that Julius should check are marked **reading**.

1. **Count lines.** Nothing changed; the 3H reading is pinned by tests (`tests/test_3i.py`): a weight between the count and the item is per item, a
   weight after the item is the total unless the line says each or per.
2. **The 3 g line** is `MvpConfig.low_fat_g_per_100g` (default `Decimal("3")`) and reaches `recipes/inference.py` through `estimate_dish(...,
   low_fat_g_per_100g=)`; the constant `LOW_FAT_G_PER_100G` stays only as the default.
3. **Plate-share ceiling.** In `portions.portion_scenario`, after a rule's two fractions are formed and before anything is calculated: a high-bound
   share above 1 refuses that rule with the reason "plate share X would exceed one whole recipe (arithmetic); the recipe is not used for portioning
   (12.16.3)". The refusal is listed per rule in the scenario's `not_applicable_reason`, so the diagnostics page shows it. **Reading:** P1 (pizza)
   already caps its share at 1 under 12.14.10 and is left so; P2 and P3 refuse. The 3H case (the Pizzaface dip, 18.5 recipes a plate) cannot recur by
   its 3H route, because the dip is now filed as a dip (PR27); the test replays the ceiling on that row with a small recipe.
4. **The empty-menu sentence** fires only when no candidate was tried (`n_dishes_considered == 0`), names the kinds from `selection.kind_label`
   ("toast, sandwiches, granola, porridge"), and says "I found no food dishes on this menu, only drinks or extras" when there was no food at all.
   **Addition, a bug fix:** when dishes were tried and none ranked, the reply names the causes counted from the unranked list (`ranking.unranked_causes`:
   "2 could not be sized from a recipe (crudo, tomatoes)", "1 had no defensible upper bound", "1 disagrees with published figures for that kind of
   dish", "N had no usable recipe", "N failed with an error") instead of the 3H sentence, which claimed a missing upper bound whatever the
   cause. The 3H wording remains only when no cause list is given.
5. Nothing built. Store-bought dough, wine pairings and the olive tag are in the checkpoint.
6. **Sources.** menustat.org answers scripted downloads with 403 (Cloudflare), with and without a browser user agent, so MenuStat was taken from its
   publisher's own open-data copy: NYC Open Data dataset qgc5-ecnb, "DOHMH MenuStat (Historical)", downloaded 2026-11-06 to
   `data/menustat_download/` with `SOURCE_AND_LICENCE.md` (NYC Administrative Code 23-502(d) and 23-504(a) quoted; the terms page itself returned
   404). **Reading:** the file holds 2017 and 2018 only (65,219 rows, 44,936 distinct items, 96 chains), not 2012-2019 as 12.16.6 expected; the
   latest year of each item is used. Chain sheets: one, Pizza Express (England, Wales and Scotland, November 2026; `data/chain_sheets/pizzaexpress_2026-11.csv`,
   276 rows). **Reading:** that sheet gives kcal per portion and per 100 g but no weight, so the serving weight is kcal per portion / kcal per 100 g x 100,
   recorded in the row's `derivation`. No other chain sheet and no retail label was read; YO! Sushi's guides carry no weights. Nutritionix not used.
7. **Method as built** (`scripts/build_cards.py`, evidence in `eval/card_evidence_2026-11-06.md`). Items are grouped into families by MenuStat
   category and name words (kids' meals and shareable items are left out of every family but the children's; meals, combos and platters are left out;
   salads naming a protein or a sandwich are left out of the salad families; an item naming two proteins, "Crab Cake Filet, 6 oz", is left out of
   the stated-weight sets because the ounces belong to one of them). Plate weight = the 10th-90th percentile of serving weights, needing two chains;
   reference figures = p10 and p90 of saturated fat and cholesterol per plate and per 100 g, needing ten values and two chains, written as aggregate
   rows `MS-<row>-<basis>-p10/p90` whose `n_businesses` is the chain count; `reference.independent_figures` now sums the businesses behind the figures,
   so the two-figure minimum of 12.9.6 reads "two chains". P3 key shares: pizza dough = whole-pizza weight x 0.5694 (USDA 2708674's dough share;
   MenuStat's pizza items are slices and are not used); fish starter = plate weight x 0.7601 raw per g fried (USDA 2706334, as PR15); fish main =
   the chain's stated fish portion x 1.2418 raw per g cooked (USDA 2706241) where the serving weight is the stated fish alone; meat main = the chain's
   stated cut weight ("6 oz Classic Sirloin", 42 items, 30 chains) taken as the raw weight, **reading:** US steakhouses state the raw cut by
   convention, and USDA's Table of Cooking Yields (ARS, December 2012: sirloin 80 %, ribeye 82-86 %, pork chop 82 %) is cited on the row for the
   reader who disagrees; dry pasta has no USDA input share for a plated pasta, so PR08 is unsourced and the P2 row PR09 carries pasta. Bigger chain
   plates are noted in the evidence file (Pizza Express Large Classics in PR01; "High Calorie" dinners in PR02 and PR07), not adjusted.
8. **Unsourced after the pass:** PR02 (fish main: one chain, O'Charley's, states the fish weight alone), PR03 (crudo: no items), PR05 and PR06
   (tomato salad: one chain weighs a caprese), PR08 (dry pasta share). Their earlier figures stay on the row for the record only; `for_dish_type`
   never returns them, and the USDA fried-food route (`survey._amount`) refuses them too, so fish mains, crudo and tomato salads are not portioned
   or ranked by any route. On the 13 menus that is 44 of the 400 labelled food items (37 fish mains, 6 crudo, 1 tomato salad), 8 of the 9 dishes on
   the seafood chalkboard. Earlier figures kept: PR02 113-227 g, PR03 45-110 g, PR05 150-300 g, PR06 120-250 g, PR08 90-140 g.
   **Reading:** these dishes are excluded at selection (`selection.RULES.for_dish_type` finds no sourced row; reason "excluded: no plate-size row with a
   measured source applies to this kind of item (12.16.8)"), so no model call or search credit is spent on a dish that cannot rank, and the reply
   counts them among the kinds Roli cannot size yet. The pipeline tests keep a toy table in which PR02, PR03 and PR05 are treated as sourced
   (`tests/test_mvp.py::toy_rules`); the real table's behaviour is tested in `tests/test_3i.py`.
9. **New rows PR16-PR33:** burger, sandwich, wrap, taco, burrito, quesadilla, breakfast_eggs, breakfast_pancakes, breakfast_cereal, toast_plate, soup,
   dip, side_salad, side_vegetable, side_rice, side_bread, dessert, kids_dish; fried potatoes stays PR12 (now 78-266 g from 132 items). The
   excluded-section rules for desserts, sides and children's menus are gone from `portions.dish_type_for`; every food item gets a family, and
   `selection.COURSE_OF` gives the new families their courses (handheld, breakfast, sides, desserts, kids) in the round-robin. **Reading:** a bare
   "egg" outside a breakfast section is not a breakfast plate (scotch egg, egg fried rice); the named egg dishes (omelette, benedict, shakshuka,
   frittata, fry-up) are, in any section.
10. Every row is `proposed_unreviewed` or `unsourced`; `approved_by` and `approved_on` are empty on all 33.
11. **Dish-kind call** built in `mvp/dish_kind.py` (`DISH_KIND_PROMPT`, `classify_menu`, `validate_kind`, `DishKindCache` under
    `.cache/roli_mvp/judgements/dish_kind/`). Code keeps the reader's add-on filing (an add-on or an item that belongs to another is never a dish, whatever
    the model says), accepts only names in `portions.FAMILIES` plus "not a dish", "drink", "add-on", and falls back to the word lists on an unknown name,
    a failed call or a missing item, logging each. `MvpConfig.dish_kind_model` is False: the call is wired into `menu_run` but off (12).
12. **Labelled set:** `eval/dish_kind_labels_2026-11-06.csv`, 400 food items from the 13 3H runs. **Reading:** the labels are my proposal, built from the
    3I word lists and corrected by hand; 92 are marked unsure, and Julius has not reviewed them, so the word lists' 100 % on the "sure" items is partly
    circular. Result (`eval/dish_kind_eval_2026-11-06.md`): word lists 347 of 400 (86.8 %), 3H word lists 164 (41.0 %), model 378 (94.5 %). On the
    3H failure cases the model is behind on shellfish (14 of 16 against 15) and ahead on the mixed Pizzaface section (9 of 10 against 0); equal on dips,
    soups, misspelt fish and invented pizza names. The condition "at least as accurate overall and on every 3H failure case" is not met, so the word
    lists stay live. The evaluation was run twice ($0.072 each, 13 calls each) because `scripts/eval_dish_kind.py` does not read the cache.
13. **Coverage** is measured on the 13 menus after local midnight on 2026-11-07, because the 2026-11-06 model budget stood at $4.89 of $5.00 after
    the evaluations; results in `CHECKPOINT_3I.md` and `eval/coverage_2026-11-07_3i.md`.
14. **Statuses, by Julius's decision of 2026-11-06 (evening):** a row with one business stating a measured figure for its key weight is `single_source`, not
    `unsourced`. A `single_source` row runs and its dishes are ranked under the reference check; the two-figure minimum of 12.9.6 governs flagging only, never
    whether a row may run. No business at all is `unsourced` (the row is never used, 12.16.8). `scripts/build_cards.py` (`status_for`) writes the three statuses;
    `PortionRule.sourced` and `for_dish_type` already treated every status but `unsourced` as sourced, so no code outside the builder changed. After the
    chain sheets below no row carries `single_source`: every revived row has two or more businesses behind it.
15. **Chain sheets read on 2026-11-06 (12.16.6 source b)**, each from the chain's own URL and transcribed to `data/chain_sheets/` (README there): Bonefish Grill
    June 2026, Carrabba's September 2026 (the May 2025 URL is 404; the chain's nutrition page links the current sheet), Wasabi v32 (4 June 2026), YO! Sushi To
    Go guide July 2024, Zizzi Autumn 2026 V1 (the 2024 and 2025 URLs redirect or 404; zizzi.co.uk/menus links the current guide), Vapiano 2022, Prezzo January
    (V2, year not printed). Not read: Wagamama (browser-rendered pages, URL 404), ASK Italian (PDF URL 404, no nutrition guide linked), Wetherspoon (menu PDF has
    kcal only; nutrition is on the app and customer screen), the YO! restaurant menu (404). **Readings:** (i) a protein weight printed in a sheet's item name is
    the chain's stated portion and feeds the P3 key share (as for MenuStat's O'Charley's items); a sheet with no weight column feeds the reference figures only;
    (ii) a sashimi portion weight, dressing excluded, is the raw fish, so PR03's key share is the sashimi weight itself (Wasabi states it; YO!'s is derived as
    kcal per serving over USDA 175167 or 175159 kcal per 100 g, the USDA records read on 2026-11-06); (iii) Zizzi's weights derive as Pizza Express's do
    (energy per portion over energy per 100 g); Vapiano prints its weights, and its extras list the pasta component alone at 180 g cooked, so its 220-600 g
    pasta portions are whole plated dishes, which sources PR09, not PR08 (dry pasta still has no USDA input share; a cooked-to-dry conversion from a USDA pasta
    record would be a new rule and is left for Julius); (iv) Wasabi's donburi are recorded under `rice_bowl`, a family with no row.
16. **Rows changed by the sheets:** PR02 fish_main 113-227 (unsourced) -> 211-317 g raw fish, proposed_unreviewed (O'Charley's and Bonefish state the fish
    alone, 7 items); PR03 crudo 45-110 (unsourced) -> 82-113 g, proposed_unreviewed (3 sashimi items, 2 businesses); PR05 tomato salad 150-300 (unsourced) ->
    287.1-301.2 g plated, proposed_unreviewed (Pizza Express, Vapiano, Zizzi); PR06 and PR08 stay unsourced (no USDA input share); PR09 97-562 -> 117-569 g;
    PR11 31-180 -> 50-243 g raw fish (Zizzi calamari and prawns); PR01 171-385 -> 175-382 g dough (Vapiano whole pizzas); small moves on PR04, PR12, PR17,
    PR24, PR26-PR28, PR31-PR33. The 44 labelled items excluded under 12.16.8 after the first rebuild are tried again. Tests: agent 515 passed, 4 skipped.
17. **12.16.8a built the same evening.** `scripts/fndds_portions.py` searches Survey (FNDDS) records per family (pinned FDC ids, found by a Survey-only search),
    reads their portions through `NutritionService.get_portions`, and keeps a portion only when its words name a whole dish, a fillet or steak, or a restaurant
    order (`qualifies`): a cup, spoon, slice, piece, "Quantity not specified" or an extra-large (16-18") pizza never qualifies; size words alone ("1 small",
    "1 thick") count as a whole item only for item or cut families (burgers, sandwiches, wraps, tacos, burritos, quesadillas, pizzas, fish and meat), so a small
    breadstick is not an order of bread; desserts allow "1 piece". **Readings:** (i) the FNDDS range is the 10th-90th percentile of the qualifying gram weights
    (min-max under three portions), converted to the row's unit by the same USDA shares the chain figure uses (cooked fillet x 1.2418; cooked cut / 0.80 by
    the USDA yield table; whole pizza x 0.5694 dough share); (ii) "disagree by more than a third" is read on the midpoints: |FNDDS mid - chain mid| > a third
    of the larger; (iii) a `keep` row (PR13-PR15) records the FNDDS figure and keeps its cited range; (iv) `sources_disagree` is a `review_status` value, and
    every status but `unsourced` runs. USDA requests for the pass: 136 (3600 -> 3464), the reserve untouched.
18. **What FNDDS gave.** Whole-dish, fillet or restaurant portions exist for fish fillets (cod, salmon, bass: 90-420 g cooked, the whole fish included), steaks,
    breasts and chops, whole pizzas (110-1112 g, extra-large left out), fries orders (70-180 g), burgers (115-175 g), sandwiches (130-240 g), wraps (135-161 g),
    tacos (100-160 g), burritos (220-330 g), fast-food side salads (87-168 g) and dessert pieces (75-260 g). Nothing qualifies for raw fish (cups and the
    default only), caprese, plated pasta (cups), fried seafood (pieces), quesadillas, eggs, pancakes, cereal, toast, soup (cups), dips, vegetable and rice
    sides, bread orders or children's dishes. The range comes from FNDDS on 12 rows (PR01, PR02, PR04, PR07, PR12, PR16-PR20, PR28, PR32) and from the chain
    figures on the rest. **sources_disagree on four rows:** PR04 leaf salad (FNDDS 90-146 g against chain 97-356 g), PR16 burger (123-171 against 84-424),
    PR17 sandwich (130-240 against 128-539), PR18 wrap (136-157 against 288-474); all four run on the FNDDS range per 8a. PR01's dough range widened to 83-448 g
    (FNDDS whole pizzas from personal to large), midpoints agreeing with the chain figure. PR02 fish main: FNDDS 156-313 g raw against chain 211-317 g (agree);
    PR07 meat: 139-300 against 170-454 (agree). PR03, PR05 keep their chain ranges; PR06 and PR08 stay unsourced. Tests: agent 518 passed, 4 skipped.
19. **Order of the evening against the reruns:** the queued reruns (00:05) run on the table as it stands after notes 14-18, so pass A and pass B see one table;
    no further table change is made before they finish.
20. **Reruns (2026-11-07, 00:05-00:52 local), on the table of notes 14-18.** Pass A on 13 menus: 66 of 406 food dishes ranked (16 %; 51 of 400 at 3H), no plate
    share above 1, 25 recipe rows refused by the ceiling (12.16.3), 5 dishes flagged, $1.709 model, 144 credits, 935 USDA requests, the reserve untouched. Pass B on
    the four test menus with saved readings: 0 differences on three, one dessert's figures on The Greyhound (a cached search listed recipes in another order,
    so a different recipe filled the scenario cap); recommendations and orders matched on all four. **Bug found and fixed after the reruns, not re-measured:**
    a section heading that lists several kinds ("STARTERS, SALADS, SIDES, DIPS") decided the kind, so Pizzaface's salads ranked as dips; `section_lists_kinds`
    now sets such a heading aside and the item's words decide. Full results: `CHECKPOINT_3I.md` sections 1, 3, 4, 7-10, `eval/coverage_2026-11-07_3i.md`,
    `eval/mvp_repeatability_2026-11-07_3i.md`. Tests: agent 519 passed, 4 skipped.

### 12.18 Changes after the Checkpoint 3I review (2026-11-07, Julius's decisions of 2026-11-07)

The 3I reruns ranked 66 of 406 food dishes (16 %); the 14-dish cap left 220 untried, sides and soups took the recommendation on five of nine menus, and two plain dishes
were flagged for falling below a chain range. These decisions approve the plate-size table, switch the dish kind to the model, keep the non-main families out of the
top three, flag above the range only and raise the cap. The principles of 12.14 apply.

**Plate-size table: approvals.**
1. `approved_by` = "Julius", `approved_on` = 2026-11-07 on every row, with the ranges as they stand (FNDDS where it gives the family's key, otherwise chain), except the
   five rows changed in 2-4, which are changed and then approved. MenuStat's 2017-2018 vintage and Pizza Express's derived weights (kcal per portion over kcal per 100 g)
   are accepted as sources.
2. **PR01 pizza:** range 171-385 g dough per pizza (Pizza Express plus the AVPN standard); the FNDDS figure stays on the row as a note, not the range.
3. **PR04 leaf_salad_starter, PR16 burger, PR17 sandwich, PR18 wrap:** range = the chain figures; the FNDDS items are fast-food portions, not restaurant plates. The FNDDS
   figure stays as a note; the `sources_disagree` mark is dropped on these four.
4. **PR07 meat:** approved as is; stated ounces read as the raw cut (US steakhouse convention), with the USDA cooking-yield note kept.
5. The egg reading of 3H stands: a bare "egg" outside a breakfast section is not a breakfast plate.

**Dish kind: switch to the model.**
6. `dish_kind_model` is True. The word lists stay as the fallback when the call fails or returns a family not on the list, and that fallback is logged. The 12.16.12 rule
   (no worse on any failure case) was too strict for one shellfish miss against 24 items the model gets right. The 92 unsure labels stay marked unsure; Julius reviews them separately.

**Non-main families listed apart.**
7. Generalising the snack-bowl rule of 12.14.4: sides (PR12, PR28-PR31), soups (PR26), dips (PR27), desserts (PR32), snack bowls (PR13-PR14) and children's dishes (PR33) never
   enter the top three. Mains, starters, salads, pizza, pasta, burgers, sandwiches, wraps, tacos, burritos, quesadillas and breakfast plates do. Each non-main family present
   gets one line after the ranking: "Lightest side: {name}, {range}" (and "Lightest soup", "Lightest dessert", "Kids: ..."), dropped first under the word limit. Children's
   dishes are listed only when the menu has a children's section. The checkpoint shows the taco and breakfast menus' replies as a tester sees them.

**Reference check: flag above the range only.**
8. A dish whose middle is above the published range is flagged as now. A dish below the range is not flagged: it ranks, and its diagnostics carry the note "below the
   published range for this kind of dish; plain recipe". The heirloom tomatoes and the lettuce-and-tomato sandwich are reopened on that basis. The two-figure minimum and
   the like-with-like rules are unchanged.

**The cap.**
9. The dish cap goes from 14 to 30 (config). The per-menu spending cap of $0.50 stays, so the checkpoint reports any menu that hits the spending cap before the dish cap.

**Small fixes.**
10. Sort cached search results by URL before the scenario cap is applied, so pass B cannot pick a different recipe from the same cache. Rerun the Greyhound dessert case.
11. The dish-kind evaluation script reads the per-item cache before calling the model.

**Reruns and measure.**
12. Before = the 3I pass A runs. Pass A on the final code, fresh readings saved; pass B on the four test menus with `reuse_saved_reading` on. The same coverage table, by
    cause, plus: how many dishes the cap now cuts; the top three per menu with sides and desserts out of it; flags open, above-range only; spending per menu against both caps.

**Rules, unchanged.** Phase 2A arithmetic untouched; no nutrient value or weight from a model; no one-off rules for single dishes; every figure sourced; spending caps as
above ($5.00 and 300 credits a day, $0.50 and 30 credits a menu). Check the USDA remaining count before each pass. Stop at Checkpoint 3J; no new USDA release data approved;
Telegram and deployment are the step after this one.

### 12.19 Built at Checkpoint 3J (2026-11-07 and 2026-11-08); where the build reads 12.18 a particular way

Numbered as 12.18. Readings that Julius should check are marked **reading**.

1. **Approvals live in `recipes/portion_approvals.csv`** (id, approved_by, approved_on, low, high, range_source, spec, decision), one row per PR row, written from Julius's
   message of 2026-11-07, and `scripts/build_cards.py` copies them onto the table last (`load_approvals`, `apply_approvals`), so a rebuild keeps them. The table was rebuilt
   with `--date 2026-11-06` (the data's read date; `read_on` stays 2026-11-06) and only the five changed rows moved; `reference_figures.csv` is byte-identical to 3I. An
   approved row's `review_status` is `approved` (every status but `unsourced` runs, as before); `PortionRule.confidence` reads `portion_reviewed` for an approved, sourced row.
   **Reading:** "every row" includes PR06 and PR08, so they carry `approved_by` = Julius too, but their status stays `unsourced` and they are never used: the approval is of
   the fact that they stay unsourced. Where Julius chose another range, the row's `basis` starts with "APPROVED RANGE (12.18, Julius, 2026-11-07): ..." and names the build's
   figure it replaced; the FNDDS columns stay filled as the note he asked for; `sources_status` on the four former `sources_disagree` rows reads "approved: chain range; FNDDS
   figure kept as a note (...)".
2. PR01: 171-385 g as instructed (`range_source` "pizza express and avpn"); the build's own chain figure was 175-382 (Vapiano included) and FNDDS 83-448, both on the row.
3. PR04 96.6-355.6, PR16 83.7-424.1, PR17 128.0-538.7, PR18 288.0-474.0 g: the chain figures as the table carried them.
4. PR07 unchanged (139-300 g raw, FNDDS range, chain 170-454 beside it); the yield note stays in the basis.
5. Nothing changed; the 3H egg reading is pinned by `tests/test_3i.py`.
6. `MvpConfig.dish_kind_model` defaults to True. `dish_kind.classify_menu` logs every fallback in `log["fallbacks"]` (index, item name, why, what the word lists said) and
   counts them in `log["fallback"]`: a failed call, a missing answer, or a kind not on the list. **Reading:** an item the reader filed as a drink, an add-on or an option of
   another item needs no model answer and is not a fallback (source `reader`). The run keeps the log in `MenuRun.dish_kind_log`.
7. `ranking.APART_GROUPS` maps the ten non-main families to six groups (side, soup, dip, dessert, snack, kids); `menu_run` moves their dishes after the mains and sets
   `RankedDish.listed_apart` (the `snack` field stays for the saved runs and equals `listed_apart == "snack"`). `ranking.apart_lines` writes one line per group present,
   naming the group's lightest dish (the ranking is by midpoint, so its first row), "Lightest side/soup/dip/dessert/snack: {name}, {range} g." and "Kids: {name}, {range} g.";
   the kids line only when a menu section matches `portions.KIDS_SECTIONS` ("Kids Menu", "NIÑOS"). Under the word limit the apart lines go first, the last group first (kids,
   then dessert, snack, dip, soup, side), then the cholesterol sentence, the certainty sentence and the notice as before. **Reading:** the 3H snack line "Light snack: ..."
   became "Lightest snack: ...", one dish not all; a menu whose only ranked dishes are apart reads "I couldn't estimate a main dish on this menu (N tried). Lightest side: ...".
   The web page marks these rows "(side, listed apart: never in the top three)" with no rank number.
8. `reference._compare`: `failed` is True only for direction "above"; a "below" comparison keeps its direction, is not failed, and carries the note `BELOW_NOTE`
   ("below the published range for this kind of dish; plain recipe"); `ReferenceCheck.below_published` is set and the diagnostics page says so. A dish below the range is
   `evaluated` and ranks. The two flags reopen by the ordinary route: a rerun of their menus finds every check that may flag passing and appends a `closed` line.
9. `MvpConfig.max_dishes` = 30; `eval_mvp --max-dishes` defaults to the config; `coverage.cause_of` now reads the reason, "the dish cap" against "a spending limit" (a dish
   skipped "before it started" by the budget).
10. **Not added, and why.** The scenario cap already sorts its candidates by (relevance grade, quantified lines, URL), and the cached search answer is one saved list read in
    the same order by every pass, so a sort by URL would change nothing between passes and would only reorder which pages a fresh search fetches first. The Greyhound dessert
    difference had another cause, found when the two runs were compared line by line: in pass A the greatbritishchefs recipe's "350ml of whole milk" matched no USDA record
    (the model declined), so that recipe could not be portioned and the backfill of 10.2 brought in the garnishwithlemon crisp; in pass B the same line was answered from the
    USDA match cache with a PROXY chosen for another dish ("the dish is vegan, so soy milk stands in for whole milk"), the recipe portioned, and no backfill ran. The match
    cache keyed decisions by ingredient name and preparation hint only, so a proxy that rests on one dish's context reached every dish naming that ingredient. **Fixed
    (12.14: bugs are always fixed):** `match.MatchCache` saves a proxy under the dish's context (`context_key`) and reuses it only for that dish; a direct match is reused
    everywhere as before; proxies saved by the earlier code under the bare key are not reused. Cost: proxy lines are matched again per dish (one batched model call and a USDA
    search per new line); direct matches, the large majority, are unchanged. The Greyhound dessert is rerun in pass A and pass B as asked.
11. `scripts/eval_dish_kind.py` reads `DishKindCache` under `.cache/roli_mvp/judgements/dish_kind/` first and reports how many items came from it.
12. Reruns are scheduled for 2026-11-08, 00:05 local, because the 2026-11-07 ledger already carries the 3I reruns ($1.73, 144 credits) and a 30-dish pass A on 13 menus
    needs more than the day's remaining 156 credits. **What happened:** the Mac slept through the night (lid closed; `caffeinate -i -s` does not prevent that), the clock check
    cleared at 01:17 in a dark wake, two menus failed in the menu reader with a connection error, and the rest ran only after 07:48 (round 1, 07:48-08:55, the two menus
    repeated at 08:49-08:55). Round 1 found the bug of note 13; round 2 (09:01-09:39, all 13 menus fresh, then the four test menus on saved readings) is the 3J result:
    101 of 402 food dishes ranked (25 %; 66 of 406 at 3I), the cap cuts 145 dishes (220 at 14), 120 of them on Alex's Kitchen, no menu at a spending cap in round 2 (two
    in cold round 1: Ren's Kitchen on 30 credits, Alex's Kitchen on $0.50), 8 flags open, all above the range, 0 fallbacks of the dish-kind call on 13 menus, pass B matched pass
    A on two of four menus with the USDA matcher's own variation on the other two; day's spending $3.23 and 215 credits. `CHECKPOINT_3J.md`, `eval/coverage_2026-11-08_3j.md`,
    `eval/coverage_2026-11-08_3j_round1.md`, `eval/mvp_repeatability_2026-11-08_3j.md`.
13. **Bug found by round 1, fixed before round 2 (12.14: bugs are always fixed).** `MenuRunner.evaluate_dish` recomputed the family from the word lists, so the dish-kind
    call's family reached selection but not the portion rules: 30 dishes ran under the word lists' family, 15 with no rule at all. The runner now passes the candidate's family
    (`evaluate_dish(..., dish_type=c.dish_type)`); without the argument the word lists decide, as before. Test in `tests/test_3j.py`. Round 1 ranked 91 dishes, round 2 101.
14. **Reading:** the repeatability check now sees only the USDA matcher's variation (a line declined once and matched the next time, because an unresolved decision is never
    cached and the model sees a different batch); it moved a low end by tenths of a gram and never a recommendation. Not tuned; a decision for Julius (checkpoint section 12).

### 12.20 Changes after the Checkpoint 3J review (2026-11-08, Julius's decisions of 2026-11-08)

Round two of the 3J reruns ranked 101 of 402 food dishes, 89 of them "close call": the typical saturated-fat range was 5x wide (top over bottom), a quarter over 10x,
and 45 dishes were unranked for an open top. On the saved runs the width came 56 % from the plate size (one weight range per family applied to the same recipe), 35 %
from recipes for the same dish disagreeing (one outlier at an end), 8 % from assumed amounts, 1 % from the frying fat; and the dish range paired the smallest plate with
the leanest recipe and the largest with the richest, so the causes multiplied. 39 of 101 dishes rested on one recipe. Julius asked for all seven fixes proposed on
2026-11-08 and decided the open points. The principles of 12.14 apply.

**Decisions.**
1. **The headline range is the middle 80 % band** of simulated plates (10th-90th percentile); the extremes stay on the diagnostics page; the wording says "most plates".
2. **A plate-weight regression on MenuStat's measured items is allowed** ("statistics on measured data"); it goes live automatically when, on held-out chains, its 80 %
   intervals cover at least as well as the family ranges and are narrower; the report states the figures either way.
3. **More recipes only when needed:** fewer than 3 usable recipes after the first round -> one extra search phrased from the menu's own ingredients and more pages, within
   the per-menu caps.
4. **Assumed-weight ranges built from stored recipes are used live** when 8+ recipes of the dish family (15+ across families) state the amount; the hand row is the fallback
   and is shown beside the data in the diagnostics.
5. **The NEODA trade estimate is the frying-fat prior**: beef dripping about 4 % of UK shops, vegetable oils the rest (The Telegraph, 18 September 2026, quoting NEODA's
   secretary-general and the Chippy Tour map), labelled a trade estimate; the fat line still shows both fats.

**The seven fixes.**
6. **Distribution combination (A).** Per dish and nutrient: draw a recipe (weighted, 7), a position between the adapted pair's two bounds (where the assumed amounts sit)
   and a plate weight from the measured samples behind the row, and re-form the per-plate value from the saved Phase 2A totals, V = f x R + P (R the whole-recipe
   total of stated lines, P the per-plate total, which the calculator counts once per plate); P3 draws the key weight, P1 the dough ball capped at one recipe; the external
   bound enters scaled by the position; a Survey fried-food interval draws its fat by the prior (5) and a position inside that fat's range. 2,000 draws, seeded from the
   dish, the nutrient and the scenario ids; p10/p50/p90 are the band; min and max over bounded recipes stay the extremes. The plate samples are written by the card builder
   (`recipes/plate_weights.csv`: every chain item, stated protein weight, AVPN ball and qualifying FNDDS portion in the row's unit), truncated to the approved range; fewer
   than 10 samples -> a uniform draw over the approved range.
7. **Recipe weighting and outliers (B).** Draw weight = relevance grade (high 1.0, medium 0.5) x (0.5 + 0.5 x the share of menu ingredients the recipe lists); with three or
   more bounded recipes, one whose midpoint is more than 5x from the others' median (log scale) is set aside, named in the caveats, kept in the extremes; when the set-aside
   would be half the recipes or more, they disagree in groups and none is set aside.
8. **Plate-weight model (C).** `scripts/plate_model.py`: ridge regression (pure Python) on item-name words, family and the kids flag -> ln(grams), grouped 5-fold by
   restaurant, intervals calibrated on cross-fitted held-out residuals, baseline = the family's approved range on the same items; `recipes/plate_model.json` carries the
   coefficients, the per-family residual quantiles and `live` by the switch rule of decision 2; the runner follows `live` unless the config says otherwise.
9. **Recipe top-up (D).** After the first round and its backfill, fewer than `min_usable_recipes` (3) portionable recipes -> one "open" search (`ingest.topup_query`: the
   name plus the first two printed ingredients) fetching `extra_fetch` (6) new pages, graded and tagged like the first ones, processed up to the scenario cap; never after
   a USDA refusal (12.5.2); only when the menu's spending room and its top-up count (`max_topups_per_menu`, 8) allow.
10. **Assumed weights built from recipe data (E).** `scripts/build_assumed_weights.py` reads every stored recipe extraction, keeps lines whose weight the text itself states
    (explicit grams, an embedded weight, a water-like liquid at 1 g per ml), skips lines a saved tag calls a cooking medium or removed, divides by the recipe's serving count
    (pizza: by its unit count), files each under its weights row and the recipe's dish family, and writes p10/p50/p90 per (row, family) and (row, any) to
    `recipes/assumed_weights_data.csv` with the recipe count and sources. `adapt.WeightsTable.range_for` uses a data range when it rests on 8 recipes of the family (15 across
    families, hand row not limited to dish types), its spread is under 20x and its median within 4x of the hand row's range; otherwise the hand row stands.
11. **Frying-fat prior (F).** `recipes/frying_fat_prior.csv` (region, fat label, share, source, read date, status trade_estimate) read by `sampling.load_frying_fat_prior`;
    the Survey interval's fat is drawn by those shares; no file -> equal draws.
12. **Line category (G).** The tag call names each line's food category from a fixed list of twenty (`tags.CATEGORIES`); code validates (salt, beer and water need a word of
    their own; an unknown name reads other). A line in a zero-fat category (wine or spirit, beer, salt, water or stock) that matched no USDA record takes the category's
    fixed record by one code-run search accepting only the exact description (`match.CATEGORY_FALLBACK`), so the near-zero rule can bound it; a composition category never
    does. A zero-fat line with no quantity is not a served-mass stop for P2. The tag prompt version changed, so saved tags are asked again.

**Measure.** Pass A on the 13 menus with fresh readings, pass B on 01/03/08/23 with saved readings; the coverage table by cause; the band against the extremes
(`scripts/band_report.py`), before (3J round 2) and after; flags opened and closed by the new middle; top-ups per menu; spending per menu against both caps.

**Rules, unchanged.** Phase 2A arithmetic untouched; no nutrient value or weight from a model; no one-off rules per dish; no new parsing regexes; every figure sourced;
spending caps as before. Stop at Checkpoint 3K; no new USDA release data; Telegram and deployment are the step after.

### 12.21 Built at Checkpoint 3K (2026-11-08); where the build reads 12.20 a particular way

Numbered as 12.20. Readings that Julius should check are marked **Reading**.

1. Band fields on `DishInterval` (band_low/mid/high, band_draws, band_method, plate_source, recipe_weights, set_aside, fat_bands), all defaulted so saved runs load;
   `ScenarioInterval.sampling` (`SamplingInputs`) holds R, P, f, W, M, K and dough at both bounds, read from the saved calculation; a test checks f x R + P reproduces every
   saved bound of the 3J runs (976 bounds, worst difference 5e-7). `_mid` = the band's median when present; the reply, the apart lines and the fat line read the band
   ("most plates"); the reference check compares the band's median per plate and per fat (**Reading:** the served-mass middle is unchanged, so only one thing moved).
2. The model stays **off**: on 3,514 held-out items of P2 families the model's 80 % interval covered 73 % against the family ranges' 69 %, but its median width was 5.1x
   against 4.2x, so the rule (narrower AND at least as covering) is not met; before the cross-fitted calibration the intervals covered 61 % at 3.4x. Held-out error a factor
   of 1.96; on the UK chain sheets a factor of 2.6 with 53 % coverage. `recipes/plate_model.json` is written with `live: false`; `eval/plate_model_2026-11-08.md`.
   **Reading:** the family samples (6) remain the plate source; the model file is kept for the record and the runner reads `live` when `MvpConfig.plate_weight_model` is None.
3. As decided; `TopUp` in `recipes/pipeline.py`, the "open" mode only, `skip_urls` for pages already read, new recipes deduplicated by URL and content hash; `DishEstimate.topup`
   records query, hits, new recipes, usable before and after; `MenuBudget.topups` counts them.
4. As decided, with the two guards of 12.20.10 (**Reading:** spread under 20x, median within 4x of the hand row; W14 salt and W05 cheese on vegetable starters were kept to the
   hand row by them). The 2026-11-08 build: 265 (row, family) ranges, 24 live, among them W12 lemon juice (116 recipes: 1.2-11.1 g against the hand row's 5.9-15), W27 cream,
   W50 lime, W05 hard cheese on pasta, W06 mozzarella on pizza (per pizza, 99-272 g against 85-170), W31 cheese on salads and starters, W43 aubergine, W54 peas, W17 croutons,
   W18 corn, W26 pancetta, W35 goat cheese, W38 cured sausage. `eval/assumed_weights_data_2026-11-08.md` shows every row.
5. As decided; the prior file names the article, the quote and the date and carries status trade_estimate.
6. **Readings:** chain and FNDDS samples are pooled per row; the approved range truncates them; PR03, PR05, PR13-PR15 and the unsourced rows have no or too few samples and draw
   uniformly; the Survey interval's draw weight is 1.0 like a high-grade recipe; the external bound enters as position x bound.
7. **Reading:** the outlier rule needs three bounded recipes and never sets aside half or more of them (the tomato soup with two lean and two rich recipes keeps all four).
8. See 2.
9. **Reading:** 8 top-ups a menu, one credit and two model calls each, keep a cold 30-dish menu inside the 30-credit cap.
10. See 4.
11. See 5.
12. **Readings:** only the four zero-fat categories get a code-chosen record; the fixed records are 173185 wine, 168746 beer, 173468 salt, 173647 tap water (confirmed against
    USDA on 2026-11-08); a zero-fat line with a quantity and no weight still stops P2.
13. Results of the reruns: PENDING_3K_RESULTS.
14. **Added the same afternoon, by Julius's agreement of 2026-11-08, before the reruns.** (a) The pairwise verdicts read the bands when both dishes have one: bands apart
    and extremes apart -> well supported, as before; bands apart but extremes overlapping -> tentative, with the reason "most plates apart ... but the full ranges overlap";
    bands overlapping -> close call. Without bands (runs saved before 3K) the extremes decide, as before. The certainty sentence for that case reads "Most plates fall in
    this order; the full ranges still overlap, so it is likely, not certain." Before this the headline read the band while the support label and the toss-up sentence
    read the extremes, so the reply could call two dishes apart and a toss-up in consecutive sentences. Replayed offline on the 3J round-2 runs: 3 of 89 close calls become
    tentative; 9 of 11 menus with a ranking still say toss-up, because the three lowest dishes on a menu are usually close and their bands overlap too. (b) **Reading:** the
    outlier guard: a single odd recipe is always an outlier (with three or more recipes); two or more that would be set aside together and make up a third or more of the
    recipes are a second kind of the dish, and none is set aside (two lean against three rich keeps all five).
15. **Bug found by the known-answer check of 2026-11-08 and fixed before the reruns.** The 3J fix (12.19.13) passed the dish-kind call's family to the runner, but
    `estimate_dish` still recomputed it from the word lists for the adapted pairs (`adapt_pairs(dish_type=...)`) and the portion step (`portion_scenario`), so the
    plate rule and the assumed-weight rows followed the word lists: Pizza Express's "Pollo Pesto" (pasta) was sized as a 30-156 g pot of dip (PR27). `estimate_dish`
    and `portion_scenario` now take `dish_type`; the runner passes the candidate's family. Test in `tests/test_3k.py`. The 3J and 3K-preview runs were affected.
