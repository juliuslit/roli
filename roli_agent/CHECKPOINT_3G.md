# Checkpoint 3G: changes after the 3F review

Date: 2026-11-06. Spec: `SPEC_3_mvp.md` 12.12 ("Changes after the Checkpoint 3F review"), build readings in 12.13.

**Stopped here for your review.** Not done, as instructed: no USDA release data approved, no known-limit rows beyond yours, Telegram and deployment not started.

## 1. Result in brief

- **The olives are fixed.** Zuni's Marinated olives use W57 on all four recipes, and their flag closed: 2.2 g per 100 g against published 1.7-2.8 g. The Sicilian Olives have their estimate back, 1.0-3.0 g.
- **Olive bowls now rank first on two menus.** That follows from the rules, but you should look at it (section 9).
- **Roli stays on reader v5.** v6 was worse on 5 of the 14 pass-bar lines, so the rule was not met. It also changed nothing on the chalkboard: both prompts attached the shared line to the four fish on all four runs.
- **Pass B matched pass A exactly**: 0 differences on all four menus, failed pages included.
- **Cornish Fish & Chips is now a known limit**, not an open flag. No open flags remain.
- **D25:** 15 lines moved to a different same-food record, and 4 lines stay class-level, labelled. Walnuts, Italian sausage and Kalamata olives left their class records.
- **My first version of the same-food rule was wrong.** It let goat meat lend to goat cheese, and three more bad lenders got through. The lender list showed this after the first live pass. I fixed it and redid both passes. Everything below comes from the second pair (section 9).
- **Margherita lost its upper bound** as a side effect of the near-zero change (section 9).
- **The stored-oil rule is only partly met for olive oil.** W09 still fills olive oil on foods other than olives (section 10).
- **Tests:** agent 419 passed (381 at 3F), library 333 passed (333 at 3F), no regressions. `test_report_3g.txt`.

## 2. What changed and where

| spec | change | where |
|---|---|---|
| 12.12.1 | one tag-prompt sentence; card setting `medium_record_head` on PR13 (oil); a food in oil with no row stays open | `prompts.py`, `recipes/portion_rules.csv`, `recipes/portions.py`, `recipes/pipeline.py` |
| 12.12.2 | I04 also tests counted zest, peel, citrus juice and salt | `recipes/inference.py`, `recipes/pipeline.py` |
| 12.12.3 | prompt v6; both batches run; Roli stays on v5 | `menu_reader_eval/prompts/menu_reader_v6.md`, `results/`, `scripts/reader_compare.py` |
| 12.12.4 | same food first in every USDA table, class-level records last and labelled | `recipes/equivalence.py`, `recipes/survey.py`, `recipes/inference.py`, `recipes/compare_dishes.py`, `scripts/d25_lenders.py` |
| 12.12.5 | stated weights read through nested brackets, prices, a second system, slashes and ranges | `recipes/parse.py`, `recipes/convert.py` |
| 12.12.6 | status `known_limit`; the table with your one row | `recipes/known_limits.csv`, `mvp/reference.py`, `mvp/menu_run.py`, `mvp/web.py` |
| 12.12.7 | failed pages noted live, kept failed with `reuse_saved_reading` on | `recipes/fetch.py`, `mvp/menu_run.py` |
| 12.12.8 | escaping on every page; before this, none of them escaped anything | `mvp/web.py` |
| 12.12.9 | five olive recipes from the saved pages, 45 lines; report splits real from made-up | `tests/fixtures/line_tag_test_set.json`, `scripts/build_real_tag_cases.py`, `scripts/eval_line_tags.py` |
| 12.12.10 | a correction to the spec, nothing to build | |

## 3. Before and after: top three per menu

Before is 3F pass A. After is 3G pass A on the final code. Figures are grams of saturated fat per plate.

| menu | | before | after |
|---|---|---|---|
| Flour + Water | 1 | Heirloom Tomatoes 0.4-2.4 | Heirloom Tomatoes 0.8-2.2 |
| | 2 | Bluefin Crudo 0.5-4.3 | Bluefin Crudo 0.5-4.3 |
| | 3 | Little Gem Lettuces 4.4-11.3 | Little Gem Lettuces 4.4-11.3 |
| The Greyhound | 1 | Padron Peppers 0.6-4.0 | **Sicilian Olives 1.0-3.0** |
| | 2 | Crispy Squid & Prawns 1.5-3.0 | Padron Peppers 0.6-4.0 |
| | 3 | Pan Fried Seabass 9.0-23.1 | Crispy Squid & Prawns 1.5-3.0 |
| Zuni Cafe | 1 | Tomato and eggplant soup 0.7-3.9 | **Marinated olives 0.7-2.6** |
| | 2 | Garden lettuce salad 0.3-5.4 | Tomato and eggplant soup 0.7-3.9 |
| | 3 | Zuni Caesar salad 2.0-5.6 | Garden lettuce salad 0.3-5.4 |
| Seafood chalkboard | 1 | Poke Salad 0.3-7.0 | Poke Salad 0.3-7.0 |
| | 2 | Crumbed Whiting 2.8-5.5 | Crumbed Whiting 2.8-5.5 |
| | 3 | Crudo Of Swordfish 2.5-12.9 | Crudo Of Swordfish 2.5-12.9 |

The things you said you would look for:

- **Zuni's olives:** all four calculated recipes now take their oil from W57, with the amount set by each recipe's olive weight. One of the four, Ina Garten's warm olives, was still tagged eaten by the model; the card caught it. The flag closed.
- **Sicilian Olives:** one recipe, 1.0-3.0 g, passes the check at 2.68 g per 100 g. The peel strips now pass the near-zero rule.
- **Pecorino line:** "1/3 cup freshly grated pecorino romano ((33g), or parmesan cheese)" reads 33 g. It was unweighed. Salsiccia Bianca still has no portion, so this does not reach a ranking yet.
- **Other stated weights that now win:** the Schnitzel recipe's flour 80 g (was 62.5), panko 100 g (was 135) and Parmesan 65 g (was 50). The Schnitzel's range did not move, because other recipes set both ends. A ribeye recipe's "about 2 lbs." is now read, which lifts that dish's high from 27.6 g to 31.0 g.
- **Heirloom Tomatoes:** "¼ cup toasted white sesame seeds" now has a same-food cup weight, so the NYT chamoy recipe's range narrowed from 0.4-2.4 g to 0.8-2.2 g.
- **Snapper:** one recipe's fillets now have their stated weight, so it can be portioned and the replacement recipe it needed in 3F is no longer brought in. That replacement set the 15.4 g high, which is now 13.4 g.

Full detail: `eval/mvp_before_after_2026-11-06_3g.md`.

## 4. Reader evaluation

Both prompts ran on `google/gemini-3.8-flash`, 25 photos, each sent twice, temperature 0, scored under interpretations 1-18. I wrote down how "no worse" would be read before running: strict, no tolerance, at the precision the harness prints (`results/reader_v5_v6_decision_rule_2026-11-06.md`).

| pass bar | bar | v5 | v6 | v6 is |
|---|---|---|---|---|
| Invented, run 1 | 0 | 8 | 12 | worse |
| Invented, run 2 | 0 | 7 | 6 | better |
| Dishes found, average | 95 % | 96.4 % | 96.4 % | same |
| Worst photo found | 80 % | 62 % | 50 % | worse |
| Cut-off lines listed, run 1 | 0 | 13 | 6 | better |
| Cut-off lines listed, run 2 | 0 | 14 | 8 | better |
| Prices | 95 % | 98.7 % | 98.2 % | worse |
| Descriptions | 90 % | 94.3 % | 95.8 % | better |
| Format | 98 % | 98.0 % | 96.0 % | worse |
| Partly photos caught, run 1 | 7 of 7 | 6 | 4 | worse |
| Partly photos caught, run 2 | 7 of 7 | 6 | 6 | same |
| False alarms, run 1 | at most 3 | 2 | 0 | better |
| False alarms, run 2 | at most 3 | 1 | 0 | better |
| Speed per photo | under 60 s | 19 s | 18 s | better |

**Roli stays on v5.** Neither prompt passes every bar, and v5 did not in round one either.

- **The shared line:** both prompts attached it to all four fish, on every run. The key lists it as a dish, so both score 9 of 10 on photo 23. The dispute over that key line did not decide anything.
- **How much of the gap is real:** most of it looks like chance in single answers, but two runs cannot prove that. Format is one extra answer that dropped a field; the partly gap is one run. The one loss that repeated is photo 21, the handwritten whiteboard, where v6 missed "Meatballs (3)" on both runs.
- **Cost:** $0.66 and $0.66, plus $0.005 for a one-photo smoke test, $1.33 in all.
- **LangSmith:** it refused the traces (429, the monthly quota), so the local folders are the record. The harness finished normally.

Files: `results/full_2026-11-06_1229_google_gemini-3.8-flash_v5_t0`, `results/full_2026-11-06_1245_google_gemini-3.8-flash_v6_t0`, summary `results/reader_v5_v6_2026-11-06.md`.

## 5. Repeatability and the reader check

| menu | menu read | recommendation | ranking and figures | differences |
|---|---|---|---|---|
| Flour + Water | same | same | same | 0 |
| The Greyhound | same | same | same | 0 |
| Zuni Cafe | same | same | same | 0 |
| Seafood chalkboard | same | same | same | 0 |

The page that broke 3F's match can no longer differ: 108 failed pages are on the list, and pass B loaded the same pages as pass A.

**Reader check.** The chalkboard was read twice fresh, twice: once after the first pair of passes, once after the final pair. All four readings gave 9 items, with the shared line attached to the four fish.

- First check: identical.
- Final check: 8 differences, in two strings. One reading wrote "SALSA VERDE", the other "SALSA VERDE SALAD", and one wrote the section "FISH OF THE DAY." with a full stop.

The separate dish seen in 3F did not come back in any reading today. That does not show it is gone: nothing changed in the reader, so it can recur, and testers still get fresh readings. Details: `eval/mvp_repeatability_2026-11-06_3g.md`.

## 6. Tag test results

Two live runs, prompt version 36aae65c6b66, $0.04 each.

| | run 1 | run 2 |
|---|---|---|
| Made-up cases, role | 104 of 104 | 104 of 104 |
| **Real pages, role** | **41 of 45** | **39 of 45** |
| Kind | 146 of 148 | 145 of 148 |
| Harmful after code's checks | 2 | 2 |
| Harmful in the model's own answer | 4 | 4 |

What the real-page misses are:

- **Oil:** four of the five olive oils are tagged medium by the prompt sentence alone. The fifth, Ina Garten's warm olives, is sautéed before serving, so the model keeps saying eaten. The card setting catches it on a live run; the test set does not use the card, so it stays a miss here.
- **The 2 "harmful" misses are whole peppercorns**, tagged removed where I labelled them eaten. Pepper is left out by I03 either way, so no figure moves. I kept my labels and did not change them to improve the score.
- **Sicilian sprigs and peel:** the peel was tagged eaten on both runs, the sprigs on one. No figure moves: herbs fall under I03 and the peel under the near-zero rule.
- **Before code's checks**, the model also marked garlic removed and the whole orange a medium; the code turned both back to eaten.

Real lines on the four menus, from the first pass A, where every tag was fresh: 2,126 tagged, 2,054 eaten, 51 medium, 21 removed. I read every distinct one. Two are borderline: the griddle's 2 tsp of olive oil, again, and a Snapper recipe's ½ cup of vegetable oil tagged a frying bath though it is under a cup. Files: `eval/line_tag_test_2026-11-06_3g.md`.

## 7. Flags

| dish | status | figures | top contributors |
|---|---|---|---|
| Cornish Fish & Chips | **known limit**: USDA has no thick-cut chips record | vegetable oil middle 8.49 g against 2-5.2 g, allowed 7.8 | chips 10.93 g (58 %), fish 5.98 g (32 %), mushy peas 0.85 g (5 %) |
| Zuni Marinated olives | **closed** | 2.20 g per 100 g against 1.7-2.8 g | |
| Greyhound Sicilian Olives | closed in 3E, stays closed | 2.68 g per 100 g against 1.7-2.8 g | |

**Open flags: none.** Fish and chips stays out of the ranking. A tester sees it under "Could not be ranked" as "known limit of the data: USDA has no thick-cut chips record", with the frying-fat sentence below. The row applies only while chips are the top contributor, so if something else takes over, the flag opens again.

## 8. D25 lender list, spending and USDA requests

**D25:** 55 lines use a lent measure. 51 are same-food and 4 are class-level.

| still class-level | lines | why |
|---|---|---|
| Fish, canned | 3 anchovy lines (Puttanesca, Zuni Caesar, Steak frites) | USDA's "Fish, anchovy" has no cup or spoon measure |
| Seaweed, raw | 1 wakame line (Poke Salad) | no wakame record has one |

| moved to a same-food record | before | now |
|---|---|---|
| walnuts, 1 cup (Garden lettuce salad) | Nuts, NFS 142 g | Walnuts, excluding honey roasted 120 g |
| toasted walnuts, ½ cup (Fuyu persimmon) | Nuts, NFS 71 g | Nuts, walnuts, english 58.5 g |
| Italian sausage, 2 lines | Sausage, NFS 69 and 138 g | Italian sausage, same weights |
| Kalamata olives, 4 lines | Olives, NFS | Olives, ripe, canned (small-extra large), 134.4 g a cup against 135 g |
| red onion ½ cup, thinly sliced (Heirloom Tomatoes) | Onions, raw (Survey) 80 g | Onions, raw (SR Legacy) 57.5 g |
| broccoli florets, 2 lines | Broccoli, raw (Survey) 90 g | Broccoli, raw (Foundation) 76 g |

Four more moved tables at the same weight (three onion lines, one feta). "Pork, NFS" and "Mushrooms, raw" no longer appear because the dish that needed them, Taleggio Scarpinocc, was not tried this time (section 9, point 7). Both remain class-level if used, so pancetta would still get "Pork, NFS". Full list: `eval/d25_lenders_2026-11-06_3g.md`.

**Spending.** The first pass A is the honest cost of a menu, because its tags were new. The final pass A reused those saved tags.

| menu | model $ first pass A | final pass A | final pass B | Tavily (first / final A / B) | USDA requests (first / final A / B) |
|---|---|---|---|---|---|
| Flour + Water | 0.10 | 0.02 | 0.01 | 0 / 0 / 0 | 28 / 3 / 3 |
| The Greyhound | 0.11 | 0.02 | 0.01 | 0 / 0 / 0 | 11 / 0 / 2 |
| Zuni Cafe | 0.11 | 0.04 | 0.01 | 0 / 1 / 0 | 10 / 1 / 0 |
| Seafood chalkboard | 0.04 | 0.01 | 0.00 | 0 / 0 / 0 | 4 / 0 / 0 |

- USDA's remaining count before each pass: 3,577 and 3,526 (first pair), 3,521 and 3,517 (final pair), of 3,600.
- Reader evaluation: $1.33. Tag tests: $0.07. Both pairs of passes: $0.50. Reader checks: $0.02.
- Day total $3.19 of the $5 cap, including $1.26 from 3F. The evaluation does not pass through the budget code, so I added its cost to the ledger by hand.

## 9. Questionable or unexpected results

1. **A bowl of olives now tops two menus.** The figures are in range, but the comparison is a 50-100 g bar snack against full plates. A tester asking what to eat may not read "olives" as an answer. W57's range is also wide, 0.3-10.8 g of oil per 100 g of olives, so these estimates rest on three labels. Decision 4.
2. **My same-food rule let bad lenders through on the first pass.** Goat meat lent to goat cheese on two lines, which moved the Sirloin's low. Half and half lent to heavy cream, cooked tomatoes to raw (240 g against 180 g a cup), and white pepper to black. I caught this reading the lender list, fixed the rule, added tests, and redid both passes. The first pair stays in `eval/mvp_eval_2026-11-06_3g_first_pass*`. The rule still rests on word tests and two short lists (`CLASS_HEADS`, `OWN_NAME_HEADS`), so read the list each time it changes.
3. **Margherita lost its upper bound** (11.6-27.6 g to no bound), so Flour + Water ranks 5 dishes, not 6. The 12.12.2 change is correct for the salt line, but that line was the recipe's only filled gap. Without a filled gap no adapted pair forms, and the pair is what let external evidence bound the flour. The same trap appeared on 2026-11-05. I did not fix it, because the fix changes when pairs form. Decision 3.
4. **The tag prompt changed some tags with no connection to oil.** The Garden lettuce salad's vinegar and salt became media for a beet's cooking liquid, and some sprigs swapped between removed and eaten. None of these moved a figure.
5. **Weights inside count lines still read per item.** "3 large (560 grams) Russet potatoes" gives 1,680 g, and "4 slices bread (8 ounces)" gives 907 g, though both are probably totals. This is the 2B rule and 12.12.5 does not cover it, so I left it. "2 large chicken breasts (boneless, skinless (780g) $4.59*)" is not read at all.
6. **A wrong match is still there:** "3/4C. peeled, chopped tomatoes" reads the food as "peeled" and matches red onion. It predates this checkpoint.
7. **The reader's order can change which dishes are tried.** The fresh Flour + Water reading listed the pasta section in a different order. Taleggio Scarpinocc and Duck Triangoli tie on lean score, so the cap of 14 now drops Taleggio and keeps the Duck. That is why "Pork, NFS" and "Mushrooms, raw" left the lender list. Pass B cannot show this, because it reuses the saved reading.

## 10. Not built, and why

- **"Its eaten oil is never guessed" holds only for oils with no row.** W09 still answers olive oil on any dish, so the house-cured anchovies' stored olive oil got 4.5-13.5 g per plate from a drizzle row. That dish has no portion, so nothing reached a ranking. I left it because the tags cannot tell a stored-in oil from grill or griddle oil, and narrowing W09 would make those dishes unranked. Decision 2.
- **Everything else in 12.12 is built.** 12.12.3 was run and did not qualify. 12.12.10 needs no code.

Differences from your brief: none that change the work. The spec's first known-limit row names the card `fish_and_chips`, which is the dish family; flags carry the row id PR15, so the table is read against the family.

## 11. Decisions for you

1. **Reader:** keep v5, or re-run v5 and v6 to separate chance from a real loss? I recommend keeping v5: v6 fixed nothing on the chalkboard. Separately, should the key's photo 23 line stay a dish? It costs both prompts a point.
2. **W09 on stored olive oil:** accept it as the clinging row, or add a tag value for "stored in oil" so those dishes stay open? I recommend the tag value, because your rule says never guessed.
3. **Margherita:** should a recipe with no filled gap still get its external bound? I recommend yes.
4. **Olive bowls ranking first:** keep them in the ranking, or list bar snacks apart from plates?
5. **Whole peppercorns:** eaten or removed in the test set? This only changes the score.
6. **Weights in count lines:** treat "(560 grams)" after a count as the total? I recommend yes, unless the note says "each".
