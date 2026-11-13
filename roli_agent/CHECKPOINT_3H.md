# Checkpoint 3H: changes after the 3G review

Date: 2026-11-06. Spec: `SPEC_3_mvp.md` 12.14, build readings in 12.15.

**Stopped here for your review.** Nothing the wider run found was fixed. No USDA release data approved, and Telegram and deployment not started.

## 1. Result in brief

- **The fixes helped less than they were aimed at.** On the four menus, ranked dishes went from 23 to 26 of 46 evaluated. Dishes with no upper bound stayed at 14; the gain came from portioning (8 failures down to 5).
- **The wider run shows a bigger problem than those causes: 13 % of food dishes are ranked** (51 of 400; 11 % without the second Zuni photo). Most never reach an estimate, because Roli has no portion rule for them.
- **Roli shows a tester an impossible figure.** On Pizzaface, a sun-dried tomato dip ranks second at 513-1076 g saturated fat. The same mechanism gives Crispy Squid 1.5-42 g on The Greyhound. It recurs on three menus (section 6).
- **Five of the 13 menus rank nothing.** On 04 and 05 every tried dish failed. On 07, 09 and 11 nothing was tried, and the sentence a tester reads gives a false reason.
- **Olives are on W09 with no flag.** Zuni's are 3.5 g per 100 g and the Sicilian 3.6 g, against an allowed 4.2 g.
- **Pass B matched pass A exactly:** 0 differences on all four menus.
- **Measure audit:** unweighed lines fell from 108 to 19.
- **Missing nutrients:** 72 of 87 lines resolved by the two facts.
- **Two of my readings need your check:** count lines and the "fatty food" line (section 9).
- **Tests:** agent 493 passed (419 at 3G), library 337 passed (333 at 3G), no regressions. `test_report_3h.txt`.

## 2. What changed and where

| spec | change | where |
|---|---|---|
| 12.14.1 | photo 23 key: shared line now on the four fish; key backed up, expected files rebuilt; Roli stays on v5 | `menu_test_set/answer_key.csv`, `menu_reader_eval/expected/` |
| 12.14.2 | every cooking medium gets W09's amount on its own record; a USDA fried record still covers deep-fried dishes | `recipes/adapt.py`, `recipes/survey.py` |
| 12.14.3 | external bounds work with no adapted pair | `recipes/compare_dishes.py` |
| 12.14.4 | snack bowls listed apart, with a "Light snack" line dropped first | `mvp/ranking.py`, `mvp/menu_run.py`, `mvp/web.py` |
| 12.14.5 | either tag passes when it cannot move a figure | `scripts/eval_line_tags.py` |
| 12.14.6 | a weight on a count line is the total | `recipes/convert.py` |
| 12.14.7 | two nutrient facts; library requests total fat and returns the category (v2.5) | `recipes/inference.py`, `nutrition_service/` |
| 12.14.8 | reading fixes, same-food whole items, slices and spoons, the audit | `recipes/parse.py`, `recipes/convert.py`, `recipes/survey.py`, `recipes/equivalence.py`, `scripts/measure_audit.py` |
| 12.14.9 | millilitres through the record's spoon or cup | `recipes/convert.py` |
| 12.14.10 | pizza rule with the AVPN dough ball, 200-280 g | `recipes/portions.py`, `recipes/portion_rules.csv` |
| 12.14.11 | shellfish count as seafood on PR02, PR03, PR11 | `recipes/portion_rules.csv` |
| 12.14.12 | one near-zero rule, menu-only lines in the tag call | `recipes/pipeline.py`, `recipes/tags.py`, `recipes/adapt.py` |
| 12.14.13 | wider run and coverage report | `scripts/wider_run.py`, `scripts/coverage.py` |

**Removed:** W57; the `snack_bowl` olive setting; rules I01 and I02; the old near-zero tests of 12.4(b), 12.8 and 12.12.2; the `gaps` and `key_record_head` columns of the weights table; the `per_100g_key` amount; the pizza area ratio and its diameter columns.

## 3. Before and after: top three per menu

Grams of saturated fat per plate. Before is 3G pass A, after is 3H pass A.

| menu | | before | after |
|---|---|---|---|
| Flour + Water | 1 | Heirloom Tomatoes 0.8-2.2 | Heirloom Tomatoes 0.8-2.2 |
| | 2 | Bluefin Crudo 0.5-4.3 | Bluefin Crudo 0.5-11.0 |
| | 3 | Little Gem Lettuces 4.4-11.3 | Little Gem Lettuces 4.4-11.3 |
| The Greyhound | 1 | Sicilian Olives 1.0-3.0 | Padron Peppers 0.6-4.0 |
| | 2 | Padron Peppers 0.6-4.0 | Pan Fried Seabass 8.9-23.0 |
| | 3 | Crispy Squid & Prawns 1.5-3.0 | Crispy Squid & Prawns 1.5-42.3 |
| Zuni Cafe | 1 | Marinated olives 0.7-2.6 | Garden lettuce salad 1.3-5.4 |
| | 2 | Tomato and eggplant soup 0.7-3.9 | Tomato and eggplant soup 1.5-5.6 |
| | 3 | Garden lettuce salad 0.3-5.4 | Zuni Caesar salad 2.0-5.6 |
| Seafood chalkboard | 1 | Poke Salad 0.3-7.0 | Poke Salad 0.3-7.0 |
| | 2 | Crumbed Whiting 2.8-5.5 | Chilled Mooloolaba Prawns 2.1-5.4 |
| | 3 | Crudo Of Swordfish 2.5-12.9 | Crumbed Whiting 2.8-5.5 |

- **Light-snack line, exactly as a tester sees it on Zuni:** "Light snack: Marinated olives, 1.3-4.0 g." On The Greyhound the word limit dropped it, as specified; Sicilian Olives (1.6-3.8 g) appear only in the ranked table, marked as a light snack.
- **Olives:** 1.3-4.0 g and 1.6-3.8 g on W09, up from 0.7-2.6 g and 1.0-3.0 g on W57. One Zuni recipe, Ina Garten's, was tagged eaten in the live run, so its oil counts in full; the olive setting that used to catch it is gone.
- **Newly ranked:** Salsiccia Bianca (20.9-56.1 g), Yellowfin tuna, Chilled Mooloolaba Prawns.
- **Bluefin Crudo's 11 g:** "1 saku tuna" now has a weight, which brings in a recipe with 92 g of olive oil on 112.5 g of tuna.
- **Snapper's high went from 13.4 g to 36.4 g.** "2 + 2 tbsp butter" and "2 + 2 tbsp olive oil" are now read in full, so a rich piccata recipe sets the high. That is correct.

**The four pizzas:**

| pizza | result | why |
|---|---|---|
| Salsiccia Bianca | ranked, 20.9-56.1 g | one recipe of four is bounded |
| Margherita | no upper bound | one recipe gives 16.1 g, but a dough line with no USDA record leaves others open, and one already passes it at 58 g |
| Puttanesca | no upper bound | dough lines with no record, and castelvetrano and boquerones have no weight |
| Wagon Wheel | no upper bound | dough or crust lines with no record, and a state not resolved |

The pizza rule works: recipes that were refused now portion. What now holds pizzas back is the dough line itself.

## 4. Coverage

**Four menus, the dishes evaluated:**

| | 3G | 3H |
|---|---|---|
| Ranked | 23 | 26 |
| No upper bound | 14 | 14 |
| Could not be portioned | 8 | 5 |
| Known limit | 1 | 1 |

**Wider run.** You stopped it after menu_10 and added 11 and 19. Food dishes per menu:

| menu | food dishes | ranked | share | tried, not ranked | not tried (cap) | outside what Roli ranks |
|---|---|---|---|---|---|---|
| 03 Flour + Water | 18 | 6 | 33 % | 8 | 3 | 1 |
| 08 The Greyhound | 35 | 6 | 17 % | 8 | 1 | 20 |
| 01 Zuni Cafe | 16 | 8 | 50 % | 5 | 0 | 3 |
| 23 Seafood chalkboard | 9 | 6 | 67 % | 1 | 0 | 2 |
| 02 Zuni, second photo | 16 | 8 | 50 % | 5 | 0 | 3 |
| 04 own photo | 6 | 0 | 0 % | 4 | 0 | 2 |
| 05 Ren's Kitchen | 35 | 0 | 0 % | 4 | 0 | 31 |
| 06 Pizzaface | 48 | 2 | 4 % | 12 | 14 | 20 |
| 07 Cafe Rust | 0 | 0 | | 0 | 0 | 0 |
| 09 The Shed breakfast | 8 | 0 | 0 % | 0 | 0 | 8 |
| 10 Alex's Kitchen | 150 | 12 | 8 % | 2 | 79 | 57 |
| 11 Mother's Tacos | 28 | 0 | 0 % | 0 | 0 | 28 |
| 19 Dwarf Grill | 31 | 3 | 10 % | 2 | 0 | 26 |
| **all** | **400** | **51** | **13 %** | **51** | **97** | **201** |

02 is a second photo of Zuni and 07 has no food, so neither counts toward cuisine variety. Without 02: 384 dishes, 43 ranked, 11 %.

**Not run, by your decision:** 12, 13, 14, 15, 16, 17, 18, 20, 21, 22, 24, 25. Your note said "20-25"; 23 is one of the four test menus, so it did run.

**Causes, by dishes affected:**

| cause | dishes | menus |
|---|---|---|
| No portion rule for this kind of item | 108 | 12 |
| The 14-dish cap | 97 | 4 |
| Sandwich, burger, wrap or taco | 30 | 5 |
| Side or extra | 28 | 4 |
| No upper bound, all kinds | 30 | 10 |
| Dessert | 18 | 4 |
| Breakfast section | 14 | 2 |
| No usable recipe found | 10 | 2 |
| No recipe could be portioned | 10 | 5 |
| Children's menu | 3 | 2 |
| Known limit | 1 | 1 |

The first, third and breakfast rows recur on most menus, and together they are the main gap: dishes Roli has no way to size. Side dishes, desserts and children's dishes are outside on purpose.

**Menu_09: the reader did not fail.** It read 14 items with "readable: yes". All 8 food dishes were excluded before any search: toast and sandwich dishes have no portion rule, Granola and Porridge match no dish family, and the two Kids Menu dishes sit in an excluded section. The other 6 items are add-ons. That is why it took 8 seconds and $0.006. Menu 11 is the same story for tacos.

**The watch list:**
- **Burgers and sandwiches:** 33 of 36 excluded.
- **Shellfish starters:** 6 of 22 shellfish dishes ranked, and 14 were cut by the cap. Battered Oysters is excluded.
- **Inconsistent classification:** the board's "BARAMUNDI" (one R) is not in the fish word list, so it is excluded while the fish beside it are mains. Soups read as meat mains, and dips as salads or pizzas.
- **The 14-dish cap:** 97 dishes, 79 of them on one menu.
- **Fatty menu-only ingredients:** salsa verde, fetta (the spelling misses the feta row), toasted almonds, smoked garlic butter, caciocavallo and crackling come up most.

Full detail, including what a tester sees on each menu: `eval/coverage_wider_run_2026-11-06_3h.md`.

## 5. The audit, nutrients, flags, repeatability, tag tests

**Measure audit** (`eval/measure_audit_2026-11-06_3h.md`). The 108 `no_usda_portion` lines of 3G:

| result | lines |
|---|---|
| Real gap, but near-zero: holds nothing up | 37 |
| Reading bug: the line or the record had it | 30 |
| Real gap | 20 |
| Measure in a same-food record | 15 |
| Recipe not processed in 3H | 6 |

Shallots are the largest real gap: no USDA table has a whole shallot. Two "real gap" flour lines do have a measure in USDA, but under a name the same-food test cannot see ("Flour, wheat" against "Wheat flour").

**Missing nutrients.** 87 line occurrences were held up in 3H's calculations. The two facts resolved 72 (the plant-cholesterol fact 70 times, the fat ceiling 38 times; a line can use both). 15 are still missing: mainly vinegars and canned tomatoes the model called prepared products, plus pork belly, which stays missing as you specified.

**Flags.** No open flags.

| dish | status | figures | top contributors |
|---|---|---|---|
| Cornish Fish & Chips | known limit | vegetable oil middle 8.49 g against 2-5.2 g | chips 9.19 g (51 %), fish 4.95 g (27 %), vegetable oil 2.27 g (12 %) |
| Zuni Marinated olives | closed, stays closed | 3.53 g per 100 g against 1.7-2.8 g, allowed 4.2 g | |
| Sicilian Olives | closed, stays closed | 3.59 g per 100 g, same allowance | |

None of the wider-run menus raised a flag, but the check runs only on the three cards with published figures, so "Sundried tomato" had nothing to fail against.

**Repeatability.** Pass A against pass B: 0 differences on all four menus, in reading, recommendation, ranking, figures and pages. `eval/mvp_repeatability_2026-11-06_3h.md`.

**Tag tests.** Two live runs, prompt version d93a4db04c35, $0.04 each.

| | run 1 | run 2 |
|---|---|---|
| Made-up cases | 104 of 104 | 104 of 104 |
| Real pages | 8 of 8 scored | 45 of 45 |
| Different answers that move no figure, passed | 3 | 5 |
| Harmful after code's checks | 0 | 0 |
| Failed calls | 1 | 0 |

The failed call matters: the model's reply for the four olive recipes broke the format, so run 1 lost those 37 real-page lines. In a live run that dish falls back to the text patterns, and the two nutrient facts need tags, so it loses more than it did in 3G. It was 1 call of 68. Ina Garten's oil tagged correctly in the test run and eaten in the live run, so that line is not stable.

## 6. Questionable or unexpected results

1. **Impossible figures reach the tester.** The key-ingredient method has no ceiling. If the recipe holds little of the key ingredient, one plate becomes many whole recipes.
   - Pizzaface: Sundried tomato dip, 513-1076 g, read as a tomato salad, up to 18.5 recipes.
   - The Greyhound: Crispy Squid & Prawns, 1.5-42 g, 6.9 recipes. A same-food size gave "2-3 large squids or 8 large sea prawns" 17.5 g.
   - Alex's Kitchen: chicken soups read as meat mains, up to 3.3 recipes.

   This recurs on different menus, so it meets your test for a rule. Decision 3.
2. **The tester's sentence is false on 07, 09 and 11.** It says no estimate had an upper bound, when nothing was tried. On 07, a drinks-only menu, the sentence reads oddly too.
3. **Coverage measures two things.** The 13 % counts every food dish. Of the 102 dishes Roli tried, half ranked. The bigger loss comes before any estimate.
4. **Wider-run costs ran above the four test menus'.** Menu_10 cost $0.37 and used 28 credits, close to the $0.50 and 30-credit menu limits.
5. **Wine pairings became ingredients on 04.** Carricante, Etna and Sicily were read into dish descriptions, and they stopped all 4 tried dishes from ranking.
6. **Pizza recipes with an unknown dough weight count as a whole pizza,** as specified, which gives high figures: Margherita's 67 g on Pizzaface and 58 g on Flour + Water.
7. **The first same-food lender bugs of 3G stayed fixed,** but two more turned up in this build and I fixed them: "Quantity not specified" was read as an item, and "without skin" counted as the word "skin".

## 7. Spending

| menu | model $ | credits | USDA requests |
|---|---|---|---|
| Flour + Water (pass A / B) | 0.10 / 0.01 | 0 / 0 | 13 / 2 |
| The Greyhound | 0.11 / 0.00 | 0 / 0 | 9 / 0 |
| Zuni Cafe | 0.12 / 0.01 | 1 / 0 | 5 / 1 |
| Seafood chalkboard | 0.05 / 0.00 | 0 / 0 | 5 / 0 |
| 02 Zuni, second photo | 0.04 | 4 | 3 |
| 04 own photo | 0.12 | 6 | 121 |
| 05 Ren's Kitchen | 0.19 | 8 | 171 |
| 06 Pizzaface | 0.18 | 28 | 93 |
| 07 Cafe Rust | 0.01 | 0 | 0 |
| 09 The Shed | 0.01 | 0 | 0 |
| 10 Alex's Kitchen | 0.37 | 28 | 244 |
| 11 Mother's Tacos | 0.01 | 0 | 2 |
| 19 Dwarf Grill | 0.16 | 10 | 130 |

- **3H totals:** model $1.56 (four-menu passes $0.40, wider run $1.08, tag tests $0.08), 85 credits, 799 USDA requests.
- **Day total, with 3G's work:** $4.75 of the cap, 120 of 300 credits.
- **USDA's remaining count, of 3,600:** 3,485 before pass A, 3,468 before pass B, 3,469 early in the wider run, 2,880 before menus 11 and 19, 2,756 at the end.
- **Daily cap change, by your decision:** raised to $6.50 for menus 11 and 19 only, 17:40-17:44 EST, through `--daily-budget-usd 6.50` on that one command, then back to $5.00 when it ended. The default in the code was never edited, and two run records show the $6.50. The day never passed $5, so the raise was not used. The search-credit cap stayed at 300.
- **The saved USDA answers** with saturated fat missing were read once more to get total fat. That is the same record, not a new release.

## 8. Not built, and why

- **Everything in 12.14 is built.** The wider run covers 13 of 25 photos, by your decision.
- `scripts/wider_run.py` stays in the repo for the remaining 12 if you want them; its state file records what has run.
- The LangSmith dataset was not refreshed for the photo 23 key, because the harness scores from the expected files.

## 9. Decisions for you

1. **Count lines (my reading):** I kept "4 (6-ounce) fillets" and "2 (400 g) cans" per item, although your rule says only "each" or "per". Read literally, four fillets become 170 g and the sauce comes out four times too large. Keep this reading? I recommend yes.
2. **"A fatty food stays missing" (my reading):** the spec gives no line, so I used the EU "low fat" limit, 3 g of fat per 100 g. Every plant record seen is under 2 g and pork belly is 35.8 g. Keep it?
3. **A ceiling on the plate share:** should one plate never exceed the whole recipe, as the pizza rule already says? I recommend yes: it recurs on three menus and it is what puts impossible figures in front of a tester.
4. **What to size next:** burgers and sandwiches, breakfast plates and tacos are the largest group of dishes Roli cannot size. Which come first?
5. **The 14-dish cap:** keep it, or raise it for long menus? It cost 97 dishes, and raising it raises spending per menu.
6. **The empty-menu sentence:** should it say what happened, for example that no dish on the menu is one Roli can estimate yet? That is a wording fix.
7. **Store-bought dough:** does it need a row or a USDA record? It is the main thing stopping pizzas.
