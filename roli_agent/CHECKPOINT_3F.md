# Checkpoint 3F: changes after the 3E review

Date: 2026-11-06. Spec: `SPEC_3_mvp.md` 12.10 ("Changes after the Checkpoint 3E review"), build readings in 12.11.

**Stopped here for your review.** Not done, as instructed: no USDA release data approved, Telegram and deployment not started.

## 1. Result in brief

- **The new marinade rule broke the olives. This is the main finding.** Recipes for marinated olives rarely say the olives are lifted out, so the model now tags the marinade oil eaten at its full recipe weight, a whole cup in one case. W57, the clinging-oil row, no longer fires. Zuni's Marinated olives are newly flagged (5.4 g per 100 g against 1.7-2.8 g). The Sicilian Olives lost their estimate. I did not reword the prompt to fix it: you said not to tune, and a rule for olives is yours to approve. Decision 1 in section 10.
- **Pass B matched pass A.** All 4 recommendations, rankings, figures and flags are the same. One page differed with no effect on any figure.
- **The reader still varies when it reads fresh**, and that reaches testers (section 4).
- **The raw-flesh fix worked**: fried squid and whiting plates are 14.5 % lighter. Fried chicken and fish and chips did not change, for two different reasons (section 3).
- **Fish and chips stays flagged**: vegetable oil 6.9-10.1 g against published 2-5.2 g. Chips are still the top contributor, so under 12.10.10 it is "made of: chips" and stays open.
- **The frying-fat sentence is built**, 27 words. Fish and chips is flagged, so a tester sees it in the "Could not be ranked" list, not in the recommendation.
- **The Schnitzel's Parmesan is 20 g** (was 60 g).
- **Pan Fried Seabass is back**, third on The Greyhound at 9.0-23.1 g, with the new-potatoes row.
- **Tag test set:** role 104 of 104 on both runs, 0 harmful after code's checks. Both 3E marinade misses are now tagged eaten, on the test set and on their real pages. The test set also passed the olive line that failed on real menus, so again it overstates quality.
- **Tests:** agent 381 passed (358 at 3E), library 333 passed (333 at 3E), no regressions. `test_report_3f.txt`.

## 2. What changed and where

| spec | change | where |
|---|---|---|
| 12.10.1 | raw share scaled by USDA's moisture change, diagnostics say when a record has none; PR15 recomputed to 99.9-129.2 g raw | `recipes/survey.py`, `recipes/portion_rules.csv` |
| 12.10.2 | tag prompt: marinade, frying oil and poaching rules | `prompts.py`, `recipes/tags.py` |
| 12.10.3 | 12 decided lines added, stock and sausage corrected; guards accept soy sauce, tamari and lemon | `tests/fixtures/line_tag_test_set.json`, `recipes/tags.py`, `scripts/eval_line_tags.py` |
| 12.10.4 | `clean_query`, one rule in the query builder | `recipes/ingest.py` |
| 12.10.5 | saved reading, `MvpConfig.reuse_saved_reading`, `--reuse-saved-reading`, reader check | `mvp/readings.py`, `mvp/menu_run.py`, `scripts/eval_mvp.py`, `scripts/reader_check.py` |
| 12.10.6 | rows W58 and W59 | `recipes/assumed_weights.csv`, `.md` |
| 12.10.7 | `same_food` test, and D25 searches for the variety first | `recipes/equivalence.py`, `recipes/survey.py` |
| 12.10.8 | W27 excludes "cream of tartar" | `recipes/assumed_weights.csv` |
| 12.10.9 | frying-fat sentence on the recommendation and the page | `mvp/ranking.py`, `mvp/menu_run.py`, `mvp/web.py` |
| 12.10.11 | flag file gets a line only on open or close; closed report prints no "None" | `mvp/reference.py`, `scripts/eval_mvp.py` |
| tests | all of the above, including the PR15 round trip and Parmesan against cottage cheese | `tests/test_3f.py`, fixtures added by `capture_fixtures_3d.py` |

**Where the brief, the spec and the build differ:**

1. **Two sections are numbered 12.10** (my 3E notes and your changes). I left both and put my notes in 12.11.
2. **12.10.1 names chicken; chicken is not affected.** USDA's fried chicken record is built from already-cooked chicken, so no raw-flesh rule applies. USDA's serving measures size it at 140-185 g.
3. **Fish and chips does not get 15 % lighter.** PR15 and the conversion changed together, which is what returns the measured 131.4-170 g. It was never overweight.
4. **D25 needed more than a stricter test.** A search for "Cheese" never returns Parmesan, so a stricter test alone would have left those lines empty. D25 now searches the variety first.
5. **Method sentences went from 4 to 8.** The Margherita's "Brush dough with the olive oil" was the fifth sentence, so the model could not have seen it.
6. **The sentence on a flagged dish.** A flagged dish is not ranked, so it has no line in the recommendation. I put the sentence on its line in "Could not be ranked". With two such dishes in the top three, a reply can pass 80 words, because neither the sentence nor the disclaimer may be cut.
7. **"Lemon in a fish cavity":** the set's existing line is a roast chicken. I added a fish recipe and read the chicken the same way.
8. **Cooking spray:** you decided its role, not its kind, so its kind is not scored.
9. **Accents stay in queries.** The spec does not list them, so "aïllade" and "aillade" remain two searches.

## 3. Before and after, top three per menu

Before = 3E pass A. After = 3F pass A. Saturated fat per plate.

| menu | | before | after |
|---|---|---|---|
| Flour + Water | 1 | Heirloom Tomatoes 0.4-2.4 | same |
| | 2 | Bluefin Crudo 0.5-4.3 | same |
| | 3 | Little Gem Lettuces 4.4-11.3 | same |
| The Greyhound | 1 | Sicilian Olives 1.0-3.0 | Padron Peppers 0.6-4.0 |
| | 2 | Padron Peppers 0.6-4.0 | Crispy Squid & Prawns 1.5-3.0 |
| | 3 | Crispy Squid & Prawns 1.8-3.5 | Pan Fried Seabass 9.0-23.1 |
| Zuni Cafe | 1 | Marinated olives 0.7-4.0 | Tomato and eggplant soup 0.7-3.9 |
| | 2 | Tomato and eggplant soup 0.7-3.9 | Garden lettuce salad 0.3-5.4 |
| | 3 | Garden lettuce salad 0.3-5.4 | Zuni Caesar salad 2.0-5.6 |
| Seafood chalkboard | 1 | Ocean Trout / Tuna Poke Salad 2.9-7.0 | same dish, 0.3-7.0 |
| | 2 | Crumbed Whiting 3.2-6.5 | Crumbed Whiting 2.8-5.5 |
| | 3 | Crudo Of Swordfish 2.5-12.9 | same |

**Why they changed:**

| dish | cause |
|---|---|
| Both olive dishes | the marinade rule (section 5). The before/after file says "model variability" for the Sicilian Olives; that automatic reason is wrong |
| Crispy Squid, Crumbed Whiting | the raw-flesh fix: survey figures x 0.855 |
| Pan Fried Seabass | W58 filled "New Potatoes" |
| Poke low, 2.9 to 0.3 g | the cleaned query found different pages, and arcisfoodblog's poke (0.3-0.7 g) is now processed. One recipe sets that low |
| Spaghetti high, 11.9 to 18.4 g | the cleaned query brought in a new page, thechowdownblog |
| Ocean Trout low, 8.8 to 6.2 g | ronniefein's marinade oil now counts as eaten, which gives that recipe an upper bound |

The fried plates you asked about:

| dish | 3E | 3F | ratio |
|---|---|---|---|
| Crispy Squid & Prawns | 1.77-3.54 g | 1.51-3.03 g | 0.857 |
| Crumbed Whiting | 3.22-6.46 g | 2.75-5.52 g | 0.855 |
| Chicken Schnitzel | 12.5-34.4 g | 12.5-34.4 g | 1.00 |
| Fish and chips | 6.90-30.70 g | 6.91-30.74 g | 1.00 |

PR15 round trip: 99.9-129.2 g raw returns 131.4-170.0 g fried, using USDA's raw share of 76.01 g. A test covers it.

Full tables: `eval/mvp_before_after_2026-11-06_3f.md`.

## 4. Repeatability and the reader check

| menu | reading | recommendation | ranking and figures | differences | model $ A / B | USDA requests A / B |
|---|---|---|---|---|---|---|
| Flour + Water | same | same | same | 0 | 0.1016 / 0.0106 | 29 / 3 |
| The Greyhound | same | same | same | 0 | 0.1478 / 0.0094 | 61 / 1 |
| Zuni Cafe | same | same | same | 0 | 0.1792 / 0.0071 | 81 / 0 |
| Seafood chalkboard | same | same | same | 1 | 0.0521 / 0.0050 | 14 / 4 |

**The one difference:** danapointfishcompany.com's poke page returned an HTTP error in pass A and loaded in pass B. It was not used either way. Failed pages are not saved, so a rerun is not fully sealed: a page like this could change a figure if a recipe depended on it.

**Reader check, seafood chalkboard read twice, fresh:** 9 items, then 10. The first reading attaches "WATERMELON, FETTA, MINT ALMOND, SALSA VERDE" to four fish. The second gives those fish no description and lists that line as a dish of its own.

So saved readings make test reruns repeatable; they do not make the reader stable. **A tester's run reads the photo fresh, so this variation still reaches testers.** Cleaned queries remove the punctuation cause only.

Details: `eval/mvp_repeatability_2026-11-06_3f.md`.

## 5. Line tags

**Test set (live, two runs):** 34 recipes, 104 lines. Report: `eval/line_tag_test_2026-11-06_3f_first.md`.

| | run 1 | run 2 |
|---|---|---|
| role correct | 104 of 104 | 104 of 104 |
| kind correct | 103 of 103 | 101 of 103 |
| harmful, after code's checks | 0 | 0 |
| harmful in the model's own answer | 1 | 2 |
| cost | $0.030 | $0.031 |

- The model's own harmful answers were steeped garlic and roasted garlic heads tagged removed. The 3D guards kept them eaten.
- The kind misses in run 2: Parmesan rind and balsamic vinegar tagged prepared_product, the safe direction.
- All 12 decided lines came back as you decided, on both runs.

**The two 3E misses:** the Margherita's oil and the beet carpaccio's oil and vinegar are tagged eaten, in the test set and on the real pages in pass A.

**Real menu lines (pass A):** 2,170 tagged lines: 2,116 eaten, 39 medium (56 in 3E), 15 removed (32 in 3E). I read all 54 medium and removed tags and found no harmful miss. One is borderline: 2 tsp of oil brushed on a griddle (squid), read as grill-grate oil. The search pages also changed, so those falls are not all the prompt's doing. Of the eaten lines I listed only those of 50 g or more that name a fat: 69 lines, a few of them false matches such as butter lettuce. I did not check their methods one by one.

**What "eaten" now costs.** This is the olive finding:

| recipe | line | 3E | 3F |
|---|---|---|---|
| thecozyapron (Sicilian Olives) | 1 cup olive oil | medium | eaten, 216 g |
| foodiecrush | 1 cup olive oil | medium | eaten, 216 g |
| foodnetwork | 2/3 cup olive oil | eaten | eaten, 143 g |
| budgetbytes | 1/2 cup olive oil | medium | eaten, 108 g |
| NYT | 1/4 cup olive oil | medium | eaten, 54 g |

These recipes pack olives in a jar or warm them in the oil and serve them, and none says the olives are lifted out. Under "only when lifted out" plus "when in doubt, eaten", the model's answer is a fair reading. It conflicts with 12.9.3 ("olive oil of a marinade" is a medium) and 12.9.10 (W57 fills that medium).

On the Sicilian recipe the model tagged everything eaten, sprigs and peel too. The peel strips have no weight, so the recipe cannot be portioned, and the dish lost its estimate.

The test-set line passed on both runs because its short method reads differently from a real recipe.

## 6. Flags

| dish | check | Roli's middle | published | allowed | result |
|---|---|---|---|---|---|
| Fish and chips | vegetable oil, 2 independent | 8.49 g | 2-5.2 g | up to 7.8 g | **failed, above: open** |
| | unlabelled, 3 independent | 18.83 g | 10.25-22.8 g | 6.83-34.2 g | passed |
| | beef dripping, 1 figure | 26.36 g | 35.6 g | | shown only |
| Marinated olives (Zuni) | per 100 g, 5 independent | 5.40 g | 1.7-2.8 g | up to 4.2 g | **failed, above: new, open** |
| | per plate, 1 figure | 4.05 g | 1.4 g | | shown only |
| Sicilian Olives | | no range | | | not checked: its 3E closure no longer means much |

**Fish and chips: top contributors**

| line | saturated fat | share of the middle |
|---|---|---|
| chips frying fat | 10.93 g | 58 % |
| fish frying fat | 5.98 g | 32 % |
| mushy peas | 0.85 g | 5 % |

Classified as 12.10.10 says: the chips are still the top contributor, so **"made of: chips"**, and the flag stays open. Nothing was tuned.

| frying fat | saturated fat | cholesterol |
|---|---|---|
| vegetable oil | 6.9-10.1 g | 65-107 mg |
| beef dripping | 22.0-30.7 g | 110-169 mg |

**Marinated olives: top contributors**

| line | saturated fat | share of the middle |
|---|---|---|
| 1 cup DeLallo extra virgin olive oil | 2.80 g | 69 % |
| extra virgin olive oil / Castelvetrano olives | 0.72 g | 18 % |
| imported olives / kosher salt | 0.40 g | 10 % |

Not classified: 12.10.10 covers only fish and chips. My reading is that the check caught a real overstatement caused by the tag rule.

`runs/flags.jsonl` gained one line in these runs, Zuni's new flag. Fish and chips stayed open with no repeat line.

**The frying-fat sentence as a tester sees it, 27 words:**

> Cornish Fish & Chips: about 6.9-10 g saturated fat if fried in vegetable oil, up to about 31 g in beef dripping. Ask what they fry in.

It appears under "Could not be ranked", below the reason "our estimate disagrees with published figures for this kind of dish". It is not in The Greyhound's 78-word recommendation. If the dish were ranked in the top three, the sentence would appear there; a test covers that.

## 7. New rows and figures

| row | USDA record | per 100 g | per plate | sources |
|---|---|---|---|---|
| W58 new or baby potatoes, plain | 2709395 Potato, boiled, from fresh, peel eaten, no added fat | 0.034 g sat, 0 mg chol | 120-180 g | see below |
| W59 buttered, only when the menu says so | 2709397 same, made with butter | 2.2 g sat, 11 mg chol | 120-180 g | see below |

**Sources for the weight, two to three new potatoes:**

- USDA Survey on both records: 1 new potato 60 g, 1 baby potato 60 g, quantity not specified 170 g.
- British Dietetic Association, Food Fact Sheet "Portion sizes": "2 egg sized new potatoes (boiled)" is one portion (wchc.nhs.uk/wp-content/uploads/2026/05/bda-portion-sizes.pdf, read 2026-11-06).
- Check Your Food: "Avg portion (180g)", third-party with no source given (checkyourfood.com/ingredients/ingredient/683/new-potatoes, read 2026-11-06).

**Judging W59, never in a total:** Chef & Brewer buttered minted new potatoes, 2.6 g saturated fat per serving, no weight given (CalorieKing, third-party). W59's low end is 2.64 g.

A search summary also gave a BDA figure of 175 g, but I could not open a page showing it, so it is not cited. No new reference figures were added.

## 8. Coverage, spending, USDA

| menu | evaluated 3E / 3F | ranked | unranked | flagged | model $ 3E A / 3F A / 3F B | Tavily credits A / B | USDA A / B |
|---|---|---|---|---|---|---|---|
| Flour + Water | 12 / 12 | 6 / 6 | 6 / 6 | 0 / 0 | 0.1208 / 0.1016 / 0.0106 | 2 / 0 | 29 / 3 |
| The Greyhound | 13 / 13 | 5 / 5 | 9 / 9 | 1 / 1 | 0.1299 / 0.1478 / 0.0094 | 10 / 0 | 61 / 1 |
| Zuni Cafe | 13 / 12 | 7 / 6 | 6 / 7 | 0 / 1 | 0.1388 / 0.1792 / 0.0071 | 20 / 0 | 81 / 0 |
| Seafood chalkboard | 7 / 7 | 5 / 5 | 2 / 2 | 0 / 0 | 0.0673 / 0.0521 / 0.0050 | 2 / 0 | 14 / 4 |

- **Model cost:** pass A $0.48, pass B $0.03. Tags were all asked afresh, because the prompt changed. Zuni rose most: its long comma-filled names changed, so its searches and pages were new. No menu came near $0.50.
- **The whole day:** $1.26 of the $5 cap, 34 of 300 Tavily credits.
- **Tavily:** 34 credits in pass A, as you expected, 0 in pass B.
- **USDA:** 185 requests in pass A, 8 in pass B. Remaining before each pass: 3,469 and 3,362 of 3,600. No refusal, no halt.

## 9. Questionable or unexpected results

1. **The olive result** (sections 1 and 5).
2. **The D25 list still has class-level lenders.** A record naming no variety may lend, which keeps Kalamata olives on "Olives, NFS" (135 g a cup, the same as USDA's green and black records). It also lets through "Pork, NFS" for pancetta, "Nuts, NFS" for walnuts, "Sausage, NFS" for Italian sausage and "Fish, canned" for anchovies. I kept these rather than leave the lines empty. Decision 4.
3. **D25 fixed more than Parmesan.** Every borrowed cheese weight had come from "cottage cheese, with gelatin dessert": feta was 120 g and is now 75 g per half cup. Greek yogurt had come from almond-milk yogurt. "3 cups baby spinach" was 600 g from creamed spinach and is now 75 g.
4. **The Poke's 0.3 g low rests on one recipe** (arcisfoodblog, 0.3-0.7 g, against 2.9-7.0 g for the others).
5. **Cleaned queries shifted some figures once**, as with the Spaghetti. They should now stay put, but the changes are search effects, not improvements.
6. **A line's stated grams are ignored:** in 3E, "1/3 cup pecorino romano ((33g)" was weighed by cups, and the parser does not read "(33g)". I did not change it and did not check it further.
7. **The compare tool's reasons are only a first reading.** "Model variability" for the Sicilian Olives is wrong, as section 3 says.
8. **The run page does not escape text.** Menu text a model read goes into the page as written. That is harmless on your Mac, but fix it before any deployment.
9. **Timing:** some runs show long gaps between menus, such as Zuni's flag at 15:07 in a run that began at 14:51 and reports 291 s. It looks like the Mac sleeping, but I did not confirm that.

## 10. Not built, and decisions for you

**Everything in 12.10 was built.** 12.10.12, the staged-answers rerun, is deferred by the spec.

**Your decisions:**

1. **Olives.** I recommend one rule on the card: on a `snack_bowl` olive dish, marinade oil is a medium, so W57 fills it as 12.9.10 intended. The alternative is to accept that oil in the bowl is eaten and drop W57. It needs your approval because it is a special case, and the prompt or card change means rerunning the menus.
2. **Sicilian Olives:** this follows from decision 1. If the oil stays eaten, the recipe needs a weight for peel strips or a removed tag.
3. **Reader variation for testers:** the chalkboard's shared description is the clearest case. Does that need work before testers use it?
4. **D25 class-level lenders:** keep them, or leave those lines empty?
5. **Fish and chips:** "made of: chips" is recorded, and USDA has no thick-cut record, per 12.10.10. What closes it?
6. **Failed pages:** should a rerun treat a failed page as failed, so that a test rerun is fully sealed?

**Stopped here.**
