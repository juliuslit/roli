# Checkpoint 3I: changes after the 3H review

Date: 2026-11-06 (build) and 2026-11-07 (reruns). Spec: `SPEC_3_mvp.md` 12.16, build readings in 12.17.

**Stopped here for your review.** No table row is approved, no USDA release data is approved, Telegram and deployment are not started.

## 1. Result in brief

**Note added 2026-11-06, late evening:** after your single-source decision and the chain-sheet reading (section 13), fish mains, crudo and tomato salads are ranked again; where sections 1, 4, 5 and 7 say they are not, sections 13 and 14 supersede them. Section 14 adds the FNDDS portions (12.16.8a): twelve rows now take their range from USDA's own portions, four of them marked sources_disagree. The reruns at 00:05 run on the table of section 14.

- **The two safety faults are fixed.** One plate is never more than one whole recipe (12.16.3): a recipe whose plate share would pass 1 is refused, and the diagnostics say so per rule. The empty-menu sentence names the kinds Roli cannot size (12.16.4), and a menu where dishes were tried and none ranked now says why ("2 could not be sized from a recipe (crudo, tomatoes)", "2 had no usable recipe") instead of the 3H claim of a missing upper bound.
- **The plate-size table is rebuilt from measured chain data: 33 rows, 28 with a source, 5 without.** MenuStat (44,936 chain items, 96 chains, 2017-2018) plus one chain sheet (Pizza Express). Every sourced row cites its source, read date and item count; nothing is adjusted by hand. Section 5 is the table for your approval.
- **The unsourced rows cost coverage: fish mains, crudo and tomato salads are no longer ranked.** Only one chain states a fish portion's weight alone, no chain weighs a crudo, one chain weighs a caprese. Under 12.16.8 those dishes are not tried at all now: 44 of the 400 labelled food items on the 13 menus, 8 of the 9 dishes on the seafood chalkboard. Section 10 has the choice this puts to you.
- **Every kind of dish now has a family.** Desserts, sides, children's dishes, burgers, sandwiches, tacos, breakfast plates, soups, dips: the excluded-section rules are gone and the word lists cover 347 of the 400 labelled items (3H's word lists: 164).
- **The dish-kind model call is built but stays off.** It is more accurate overall (378 of 400 against 347) but not on every 3H failure case (shellfish: 14 against 15), so by 12.16.12 the word lists stay live.
- **Coverage before and after:** 51 of 400 food dishes ranked at 3H (13 %) -> 66 of 406 at 3I pass A (16 %); dishes outside what Roli ranks 201 -> 37; dishes not tried for the 14-dish cap 97 -> 220; tried and not ranked 51 -> 83 (section 4).
- **Repeatability:** pass B matched pass A on three of the four test menus with 0 differences; on The Greyhound one dessert's figures moved because the cached search returned the recipes in another order and a different recipe fell inside the scenario cap; recommendations and ranking orders matched on all four (section 8).
- **Tests:** agent 512 passed (493 at 3H), library 337 passed (unchanged), `test_report_3i.txt`.
- **A mistake of mine cost $0.126 and 9 search credits:** the rerun script's wait condition was wrong and two menus ran at 19:15 on pre-final code; the $5.00 daily cap then blocked everything else, as designed (section 9).

## 2. What changed and where

| spec | change | where |
|---|---|---|
| 12.16.1 | count-line reading of 3H pinned by tests | `tests/test_3i.py` |
| 12.16.2 | the 3 g "fatty food" line is `MvpConfig.low_fat_g_per_100g`, plumbed to the nutrient facts | `mvp/models.py`, `recipes/pipeline.py`, `recipes/inference.py`, `recipes/adapt.py` |
| 12.16.3 | plate-share ceiling in `portion_scenario`: a high-bound share above 1 refuses the rule, reason in the diagnostics | `recipes/portions.py` |
| 12.16.4 | empty-menu sentence with kinds; drinks-only sentence; causes named when dishes were tried and none ranked | `mvp/ranking.py` (`recommendation_text`, `unranked_causes`), `mvp/selection.py` (`kind_label`, `unsized_kinds`), `mvp/menu_run.py` |
| 12.16.6 | MenuStat downloaded from NYC Open Data (menustat.org refuses scripts); Pizza Express sheet transcribed | `data/menustat_download/`, `data/chain_sheets/` |
| 12.16.7-10 | `build_cards.py` builds every row and its evidence; `PortionRule` gains `plate_low`, `plate_high`, `n_items`, `read_on`; aggregate reference figures with `n_businesses`; the reference check counts chains | `scripts/build_cards.py`, `recipes/portion_rules.csv`, `recipes/reference_figures.csv`, `recipes/portions.py`, `mvp/reference.py`, `eval/card_evidence_2026-11-06.md` |
| 12.16.8 | unsourced rows never used: `for_dish_type` skips them, the USDA fried-food route refuses them, selection excludes their dishes before any spend | `recipes/portions.py`, `recipes/survey.py`, `mvp/selection.py` |
| 12.16.9 | 18 new families with rows PR16-PR33; word lists rewritten; excluded-section rules removed; courses for the new families in the round-robin | `recipes/portions.py` (`FAMILIES`, `dish_type_for`), `mvp/selection.py` (`COURSE_OF`) |
| 12.16.11 | dish-kind call: prompt, validation, per-item cache, wired into the run behind `MvpConfig.dish_kind_model` (False) | `mvp/dish_kind.py`, `mvp/menu_run.py`, `mvp/models.py` |
| 12.16.12 | labelled set and the evaluation script | `eval/dish_kind_labels_2026-11-06.csv`, `scripts/eval_dish_kind.py`, `eval/dish_kind_eval_2026-11-06.md` |
| 12.16.13 | coverage script reads the new exclusion reasons | `scripts/coverage.py` |

**Removed:** the dessert, side, children's-menu and breakfast exclusions in `dish_type_for`; the fixed rule rows' hand-set figures for PR01, PR02, PR04, PR07, PR09-PR12 (replaced by measured ranges; the 3H figures stay on the unsourced rows for the record).

**Bugs found and fixed on the way (12.14 principle: bugs are always fixed):** a bare "egg" made a scotch egg a breakfast plate (now only named egg dishes, or any egg in a breakfast section); the salad families counted "Chicken Caprese" and caprese sandwiches; the fish row counted "Crab Cake Filet, 6 oz" and "Flo's Filet 8 oz & Lobster Tail", whose ounces are the steak's (an item naming two proteins is left out of both stated-weight sets); the 3H "no defensible upper bound" sentence fired whatever the cause.

## 3. The safety fixes on the cases

**Plate-share ceiling.** The Pizzaface dip is now filed as a dip (PR27, 30-163 g a pot), so the 3H route (a tomato-salad card against 22.5 g of sun-dried tomato) cannot recur. The test replays the ceiling on the dip row: a 60 g recipe against a pot of up to 163 g would be 2.7 recipes a plate; the rule is refused with "PR27: plate share 2.72 would exceed one whole recipe (...); the recipe is not used for portioning (12.16.3)". A recipe larger than the plate still portions. Checked on the rerun output: in the 13 pass A runs no applicable portion has a high-bound plate share above 1; 25 recipe rows were refused by the ceiling and the dish went on to its next recipe (the largest refusals: Crumbed Whiting on PR02 at 3.40 recipes a plate, baked beans on toast on the kids' row at 2.25, Padron peppers at 2.10, a bacon sandwich at 2.05; the full list is in the coverage file).

**Empty-menu sentence.** On The Shed breakfast menu (3H run 20261106-223251-cbe070, with every rule removed in the test), the reply is: "I can't size the dishes on this menu yet: toast, sandwiches, granola, porridge. Modeled from published recipes and typical portions, not this kitchen's numbers." A drinks-only menu reads "I found no food dishes on this menu, only drinks or extras." The breakfast and taco menus as a tester sees them after the rerun (run ids 20261107-052941-380da1 and 20261107-053920-375a65):

> **The Shed breakfast:** "Among the 1 dish I could estimate (8 tried; 7 had no usable estimate), lowest saturated fat first: 1) Scrambled Eggs on Toast, about 1.7-7.2 g saturated fat per plate. It's the only dish I could estimate, so this is one figure, not a ranking. Scrambled Eggs on Toast cholesterol about 169-737 mg, the top end from eggs (an assumed amount). Modeled from published recipes and typical portions, not this kitchen's numbers." Then seven "could not be ranked" lines: poached eggs, the adults' scrambled eggs, a round of toast and porridge each on a line with no weight ("Malted or White Toast" read as an ingredient; "Homemade Berry Compote" with no record), granola on oats whose record has no saturated fat, the bacon sandwich with no portionable recipe, beans on toast with a tin of beans in an unresolved state. The one ranked dish is the children's version. The empty-menu sentence of 12.16.4 was not needed here.

> **Mother's Tacos:** "Among the 3 dishes I could estimate (14 tried; 11 had no usable estimate; 8 not tried), lowest saturated fat first: 1) Tortillas & Salsa, about 0.0-0.0 g saturated fat per plate; 2) Red Rice, 0.3-3.3 g; 3) Quesadilla, 2.6-12 g. Red Rice and Quesadilla overlap, so treat that order as a toss-up. Tortillas & Salsa has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers." Then eleven lines: seven tacos (pastor, carne asada, pollo asado, mushroom, jamaica, purple potato, the taco meal) and the beans with "no recipe of this dish could be portioned", papas fritas with an oil line of no weight. The quesadilla ranked is the children's one; no adult taco ranked (section 4 on why).

## 4. Coverage before and after

`eval/coverage_2026-11-07_3i.md` (before = the 13 3H pass A runs, after = 3I pass A, 2026-11-07 00:05-00:50 local, on the table of sections 13-14).

| | before (3H) | after (3I) |
|---|---|---|
| food dishes on the 13 menus | 400 | 406 (Ren's Kitchen read 41 items, 35 before) |
| ranked | 51 (13 %) | 66 (16 %) |
| tried, not ranked | 51 | 83 |
| not tried (the 14-dish cap) | 97 | 220 |
| outside what Roli ranks (no family) | 201 | 37 |

By menu: Ren's Kitchen 0 -> 5, Dwarf Grill 3 -> 9, Mother's Tacos 0 -> 3, The Shed breakfast 0 -> 1, Greyhound 6 -> 7, chalkboard 6 -> 7, Pizzaface 2 -> 3, Alex's Kitchen 12 -> 13; Flour + Water 6 -> 4 and both Zuni photos 8 -> 7 (recipes whose plate share passed 1 are now refused, and PR03's sashimi range of 82-113 g sent the bluefin crudo and the poke salad through the ceiling on their first recipe). The new families moved 164 dishes from "no family" into "tried", and the cap then left most of them untried: the cap, not the table, is now the first limit on coverage (220 dishes). Causes of "tried, not ranked" after: no recipe could be portioned 30 (10 before), no upper bound from a line with no weight 13, no usable recipe 15, no USDA record 7, raw or cooked state unresolved 5, flagged against published figures 5 (0 before), a nutrient USDA does not report 2.

Tacos: Mother's Tacos' nine tacos are typed `taco` and selected, but none could be portioned ("no scenario could be portioned, 4 without an applicable portion model"): PR19 is a P2 row and the taco recipes found give no served mass to divide by. Not changed; for you.

## 5. The plate-size table, for your approval

All 33 rows are `proposed_unreviewed` or `unsourced`; `approved_by` and `approved_on` are empty. Sources: MenuStat = DOHMH MenuStat (Historical), NYC Open Data qgc5-ecnb, downloaded 2026-11-06 (`data/menustat_download/SOURCE_AND_LICENCE.md`); PE = Pizza Express nutrition sheet, November 2026, weights derived as kcal per portion / kcal per 100 g (`data/chain_sheets/pizzaexpress_2026-11.csv`). Full evidence per row, with the lightest, middle and heaviest item and the chains counted: `eval/card_evidence_2026-11-06.md`.

| row | family | model | plate figure (low-high) | n items (chains) | sat fat / plate p10-p90 g (n) | source | status |
|---|---|---|---|---|---|---|---|
| PR01 | pizza_neapolitan | P1 | 171-385 g dough per pizza = whole pizza 300-675 g x 0.5694 (USDA 2708674 dough share) | 117 (3) | 2.5-20.6 (230) | PE, MenuStat; AVPN ball kept in the notes | proposed_unreviewed |
| PR02 | fish_main | P3 | 113-227 g raw fish (3H figure, record only) | 85 plates (14); 6 stated weights (1 chain) | 1.0-23.0 (522) | MenuStat | **unsourced**: one chain states the fish weight alone |
| PR03 | crudo_starter | P3 | 45-110 g raw fish (3H figure, record only) | 0 | 1.7-7.4 (9, 3H figures) | none | **unsourced**: no measured item |
| PR04 | leaf_salad_starter | P2 | 96-362 g plated salad | 31 (15) | 0.0-10.0 (162) | MenuStat | proposed_unreviewed |
| PR05 | tomato_salad_starter | P2 | 150-300 g (3H figure, record only) | 1 (1) | 3.8-18.0 (10) | MenuStat, PE | **unsourced**: one chain weighs a caprese |
| PR06 | tomato_salad_starter | P3 | 120-250 g raw tomato (3H figure, record only) | 1 (1) | as PR05 | as PR05 | **unsourced** |
| PR07 | meat_main | P3 | 170-454 g raw meat = stated cut weight, 6-16 oz | 303 plates (30); 42 stated cuts (30 chains) | 2.0-33.0 (1009) | MenuStat; USDA Cooking Yields cited | proposed_unreviewed |
| PR08 | pasta_main | P3 | 90-140 g dry pasta (3H figure, record only) | 36 (11) | 2.5-40.0 (311) | MenuStat plates; no USDA share for dry pasta | **unsourced** |
| PR09 | pasta_main | P2 | 97-562 g plated pasta | 36 (11) | 2.5-40.0 (311) | MenuStat | proposed_unreviewed |
| PR10 | vegetable_starter | P2 | 47-297 g plated starter | 387 (31) | 0.0-16.0 (1394) | MenuStat | proposed_unreviewed |
| PR11 | fish_starter | P3 | 31-180 g raw seafood = plate 41-236 g x 0.7601 (USDA 2706334) | 8 (4) | 0.0-14.0 (85) | MenuStat | proposed_unreviewed |
| PR12 | fried_potato_side | P2 | 78-266 g chips (was 200-284) | 132 (25) | 1.5-11.0 (333) | MenuStat | proposed_unreviewed |
| PR13 | snack_bowl (olives) | P2 | 50-100 g, confirmed | 1 (1) | 1.4 (1) | 3D sources, PE | proposed_unreviewed |
| PR14 | snack_bowl (nuts) | P2 | 25-60 g, confirmed | 0 | none | 3D sources | proposed_unreviewed |
| PR15 | fish_and_chips | P3 | 99.9-129.2 g raw fish, confirmed | 2 plates (2) | 7.0-19.0 (21) | Papa's lab weight, Seafish survey; MenuStat figures added | proposed_unreviewed |
| PR16 | burger | P2 | 84-424 g whole item | 260 (16) | 5.0-28.0 (737) | MenuStat | proposed_unreviewed |
| PR17 | sandwich | P2 | 128-539 g whole item | 875 (30) | 3.0-19.0 (2434) | MenuStat | proposed_unreviewed |
| PR18 | wrap | P2 | 288-474 g | 219 (7) | 4.0-18.8 (306) | MenuStat | proposed_unreviewed |
| PR19 | taco | P2 | 83-180 g per order | 53 (8) | 3.0-19.0 (198) | MenuStat | proposed_unreviewed |
| PR20 | burrito | P2 | 196-507 g | 80 (9) | 3.0-17.0 (171) | MenuStat | proposed_unreviewed |
| PR21 | quesadilla | P2 | 60-394 g | 24 (7) | 3.0-37.5 (66) | MenuStat | proposed_unreviewed |
| PR22 | breakfast_eggs | P2 | 113-575 g plated | 139 (12) | 4.5-29.0 (330) | MenuStat | proposed_unreviewed |
| PR23 | breakfast_pancakes | P2 | 82-453 g | 98 (17) | 2.0-19.5 (306) | MenuStat | proposed_unreviewed |
| PR24 | breakfast_cereal | P2 | 27-319 g per bowl | 45 (15) | 0.0-8.0 (88) | MenuStat | proposed_unreviewed |
| PR25 | toast_plate | P2 | 56-151 g | 41 (10) | 1.0-23.6 (135) | MenuStat | proposed_unreviewed |
| PR26 | soup | P2 | 193-372 g per bowl | 209 (14) | 0.0-15.0 (622) | MenuStat | proposed_unreviewed |
| PR27 | dip | P2 | 30-163 g per pot | 94 (25) | 0.0-15.1 (280) | MenuStat | proposed_unreviewed |
| PR28 | side_salad | P2 | 95-257 g | 28 (15) | 0.0-10.0 (159) | MenuStat | proposed_unreviewed |
| PR29 | side_vegetable | P2 | 64-314 g | 108 (21) | 0.0-11.0 (333) | MenuStat | proposed_unreviewed |
| PR30 | side_rice | P2 | 86-408 g | 33 (12) | 0.0-8.0 (91) | MenuStat | proposed_unreviewed |
| PR31 | side_bread | P2 | 55-133 g per order | 58 (18) | 0.0-10.0 (191) | MenuStat | proposed_unreviewed |
| PR32 | dessert | P2 | 34-255 g | 529 (37) | 2.5-30.0 (1346) | MenuStat | proposed_unreviewed |
| PR33 | kids_dish | P2 | 57-240 g | 274 (27) | 0.0-12.0 (998) | MenuStat | proposed_unreviewed |

Cholesterol ranges and per-100 g ranges are in the evidence file; all three ranges are written as reference figures (98 aggregate rows, each carrying its chain count) and used by the 12.1 check with the two-chain minimum.

**Things in this table I would not approve without a look:**
- PR01 counts whole Pizza Express pizzas from the Island Flatbread (62 g) to the Christmas Crackler (780 g) and Large Classics; the dough range 171-385 g sits above the AVPN ball (200-280 g) at the top. MenuStat's pizza items are slices and were not used.
- PR07 reads the chain's stated ounces ("6 oz Classic Sirloin") as the raw cut. US steakhouses state the raw weight by convention, but no chain says so; USDA's cooking yields (sirloin 80 %, ribeye 82-86 %) are cited on the row for the opposite reading.
- PR16 and PR17 run from a 55 g slider to a 1,234 g "burger with a lower-calorie side" and a 539 g sandwich: MenuStat serving weights include the sides on some items and not on others.
- PR15 gained MenuStat's fish and chips figures (Denny's, Perkins: 7-19 g saturated fat per plate) beside the UK lab and survey figures.
- PR11 rests on 8 items from 4 chains; PR13 on one Pizza Express item; PR14 on none (confirmed from its 3D sources).
- MenuStat is 2017-2018 only; 12.16.6 expected 2012-2019. Chain portions have changed since.

## 6. Dish kind: the model against the word lists

`eval/dish_kind_labels_2026-11-06.csv` (400 food items, 13 menus; the labels are my proposal, 92 marked unsure, not yet reviewed by you) and `eval/dish_kind_eval_2026-11-06.md`.

| classifier | correct of 400 | of the 308 not marked unsure |
|---|---|---|
| word lists, 3I | 347 (86.8 %) | 308 (100 %; circular: the labels were drafted from these lists) |
| word lists, 3H | 164 (41.0 %) | 147 |
| model (Gemini 3.8 Flash, one call per menu) | 378 (94.5 %) | 296 (96.1 %) |

3H failure cases (items, word lists 3I / model): dips 9, 9 / 9; invented pizza names 25, 25 / 25; misspelt fish 1, 1 / 1; shellfish 16, 15 / 14; soups 22, 22 / 22; Pizzaface's mixed "starters, salads, sides, dips" section 10, 0 / 9. **The rule of 12.16.12 is not met** (shellfish), so the word lists stay live and `dish_kind_model` is False. The model's misses are mostly defensible readings I did not label its way: Alex's Kitchen chicken appetizers as meat mains (8), Crumbed Whiting and chilled prawns as fish starters, Tortellini in brodo as a soup, a jacket potato as a vegetable starter. The word lists' 53 misses are concentrated on Pizzaface's mixed section (every item read as a dip) and Alex's Kitchen vegetable mains and momos (no family). Per-family accuracy is in the evaluation file. The evaluation ran twice ($0.072 each) because the script does not read the per-item cache.

## 7. Desserts, sides and children's dishes in the rankings

From the rerun (33 ranked dishes of the new families on 9 menus; full list in the coverage file):

- Desserts ranked: Greyhound apple and rhubarb crumble (5th, 6.9-16.9 g), Ren's Kitchen giant cinnamon bun (4th, 6.1-19.1 g) and fruit and nut flapjack (5th, 9.7-29.1 g), Dwarf Grill Half Moon Apple (3rd, 5.3-11.2 g), Doughnuts (5th), Icebox Chocolate (7th, 10.6-22.7 g). None reached a top-three recommendation except the Dwarf Grill's Half Moon Apple, where the only lower dishes were shoestring potatoes and a bacon-tomato sandwich.
- Sides ranked, and often first: Greyhound chilli and garlic green beans (2nd) and mixed leaf salad (3rd); Zuni shoestring potatoes (4th) and the tomato and eggplant soup (3rd); Ren's chunky chips (1st, 0.2-4.1 g) and onion rings (2nd); Alex's Kitchen plain rice (2nd) and three soups; Mother's Tacos tortillas and salsa (1st, 0.0-0.0 g) and red rice (2nd); Dwarf Grill shoestring potatoes (1st). So a side or a soup is now the recommendation on five of nine menus with a ranking.
- Children's dishes ranked: The Shed's kids' scrambled eggs on toast (the only ranked dish on that menu, 1.7-7.2 g) and Mother's Tacos' kids' quesadilla (3rd). The breakfast menu's reply therefore reads as one figure, not a ranking; the empty-menu sentence was not needed there.
- Bug found by the rerun, fixed afterwards and not re-measured: Pizzaface's section heading "STARTERS, SALADS, SIDES, DIPS" made every salad on the page a dip (three salads ranked 1st-3rd as `dip`). A heading that lists several kinds no longer decides the kind; the item's words do (`portions.section_lists_kinds`, test in test_3i). On a rerun those salads would be typed as salads.

## 8. Repeatability: pass A against pass B

`eval/mvp_repeatability_2026-11-07_3i.md`: pass B (saved readings reused, 40 minutes after pass A) against pass A on 03, 08, 01, 23.

| menu | menu read | recommendation | ranking and figures | model $ A / B | USDA requests A / B |
|---|---|---|---|---|---|
| 03 Flour + Water | same | same | same | 0.0160 / 0.0081 | 2 / 2 |
| 08 The Greyhound | same | same | one dessert's figures differ | 0.1425 / 0.0065 | 150 / 2 |
| 01 Zuni Cafe | same | same | same | 0.0727 / 0.0061 | 17 / 1 |
| 23 Seafood chalkboard | same | same | same | 0.0338 / 0.0009 | 6 / 0 |

The one difference: the Greyhound's apple and rhubarb crumble read 6.9-16.9 g in pass A and 5.8-15.2 g in pass B, 5th place in both. In pass A the garnishwithlemon.com crisp was calculated; in pass B the same recipe was "not processed: beyond the scenario cap", because the cached search answer listed the recipes in another order and a different recipe filled the cap. The saved reading removed the 3E reader variation; the recipe order from the search cache is the remaining source of pass-to-pass difference. Not changed.

## 9. Spending

Model spend is read from the ledger (`runs/spend_ledger.jsonl`); caps unchanged ($5.00 and 300 credits a day, $0.50 and 30 credits a menu).

| what | model $ | search credits |
|---|---|---|
| dish-kind evaluation, 13 menus, run twice | 0.145 | 0 |
| **my mistake:** reruns started at 19:15 on 2026-11-06 instead of after midnight; menus 03 and 08 ran on pre-final code before the daily cap stopped the rest | 0.126 | 9 |
| 2026-11-06 total, all work | 5.018 (cap $5.00; the cap blocked the next call) | |
| pass A, 13 menus (2026-11-07, 00:05-00:50) | $1.709 model (676 calls across both passes), 144 Tavily credits, 935 USDA requests | the dearest menus: Ren's Kitchen $0.273, Alex's Kitchen $0.271, Mother's Tacos $0.251; the cheapest with a ranking: Flour + Water $0.016 |
| pass B, 4 menus (00:50-00:52) | $0.022 model, 0 credits, 5 USDA requests | saved readings and cached searches |

USDA requests: 3,599 of 3,600 left when pass A started, 2,663 when pass B started, 2,658 after; the 200 reserve was never approached. The 2026-11-07 ledger: $1.732 model, 144 credits, 17 runs; the day's caps ($5.00, 300 credits) were not reached.

## 10. Questionable or unexpected results

- **Three families lost their ranking entirely.** Fish mains were a third of what Roli ranked in 3H on the fish-heavy menus; the seafood chalkboard goes from 6 ranked of 9 to at most 1. This follows from your rule 8 and from the data, not from a bug: the chains do not state a fish portion's weight alone. The way back is a decision, not a fix (section 12).
- **A tomato salad's reference figures would flag a plain one.** MenuStat's ten caprese items run 3.8-18 g saturated fat a plate (mozzarella); an heirloom tomato salad with oil is 1-2 g. The row is unsourced anyway, so the figures do nothing today.
- **MenuStat serving weights mix the item with its sides** on some chains ("Sirloin & Shrimp Dinner 749 g", "burger w/ lower calorie side 1,234 g"), which widens PR02's plate range, PR07's and PR16's. Only the stated-weight sets (PR02, PR07) escape this.
- **The labelled set is mine.** The word lists' score on the "sure" items is circular, and the 92 unsure items are where the model and I disagree most.
- **The reference check now has figures for almost every family** (98 aggregate rows). More dishes will be flagged than in 3H, including correct estimates that fall below a chain range. From the rerun: 5 dishes flagged and left unranked. Above the published range: Salsiccia Bianca pizza at Flour + Water (middle 42.5 g against 2.5-20.6; caciocavallo and butter), Pizzaface's Margherita (35.5 g against 2.5-21.2), the own-photo pork belly (65.8 g against 2.0-32.0). Below it: Flour + Water's heirloom tomatoes (1.9 g against 4.0-18.0, olive oil the whole figure) and the Dwarf Grill's lettuce and tomato sandwich (2.0 g against 3.0-19.0). The two below-range flags are the case foreseen here: a plain dish failing a chain range built from richer dishes of the same kind. The Salsiccia flag line in `flags.jsonl` carries the time of the mistaken early run (19:16 local), which opened it first; pass A found it open and recorded no new line.
- **Pizza Express weights are derived**, not stated (kcal per portion / kcal per 100 g); the sheet has no gram column.
- **The dish-kind evaluation ran twice**, and the reruns fired early. Both were my errors; both were capped by the budget module.

## 11. Not built, and why

- Other chain sheets (Wetherspoon, Nando's, Chipotle, Panera, Denny's) and retail labels: not read. MenuStat covered every family but crudo and tomato salads, and the brief's order was MenuStat first; Pizza Express was read because it is the only measured whole-pizza source. Reading more sheets is the obvious next step for the unsourced rows.
- The model switch for dish kinds: condition not met.
- A P2 (plate weight) row for fish mains, a side-salad proxy for tomato salads, a serving-measure route for crudo: all would add rows 12.16 does not list, so they are proposals in section 12, not code.
- Telegram, deployment, accounts: not started.

## 12. Decisions for you

1. Approve, change or reject each row in section 5 (`approved_by`, `approved_on` are yours to fill).
2. **Fish mains, crudo, tomato salads.** Options: (a) leave them unranked until a measured source appears; (b) add a P2 row for fish mains from MenuStat's 85 fish plates (72-520 g, 14 chains), knowing the range includes sides; (c) read chain sheets that state fish weights (UK pub chains publish some). Each is a new row or a new source, so I did not do it.
3. The meat reading on PR07 (stated ounces = raw cut) and the egg reading (a bare "egg" outside breakfast is not a breakfast plate).
4. Whether the word lists stay or the model goes live despite one shellfish miss (it is better on 10 Pizzaface items and 14 Alex's Kitchen items, by my labels).
5. Review the 92 unsure labels in `eval/dish_kind_labels_2026-11-06.csv`.
6. MenuStat's vintage (2017-2018) and the Pizza Express derivation: acceptable sources, or not.

## 13. Second table rebuild: your single-source decision and the chain sheets (2026-11-06, evening)

**Decision applied.** Status is now by the number of businesses behind the row's key weight: none `unsourced`, one `single_source` (runs under the reference
check), two or more `proposed_unreviewed` (`build_cards.status_for`; spec 12.17 note 14). The two-figure minimum stays a flagging rule only. Nothing outside the
builder changed, because the loader already treated every status but `unsourced` as sourced. No row ended up `single_source`: every revived row has two or more
businesses.

**Sheets read**, each from the chain's own site and transcribed to `data/chain_sheets/` (README has the table): Bonefish Grill June 2026 (46 rows), Carrabba's
September 2026 (31; the May 2025 URL is 404, the chain's nutrition page links the current sheet), Wasabi v32 June 2026 (17), YO! Sushi To Go July 2024 (3),
Zizzi Autumn 2026 (40; the 2024 and 2025 URLs redirect or 404, zizzi.co.uk/menus links the current guide), Vapiano 2022 (47), Prezzo January (28, per serving
only). Two USDA records were read for the YO! sashimi weights (175167 raw Atlantic salmon 208 kcal, 175159 raw yellowfin tuna 109 kcal per 100 g); USDA's
remaining count stood at 3598 of 3600 afterwards.

**Not read, and why.** Wagamama: the dish page URL is 404 and the menu is built in the browser, so no figures reach a plain fetch. ASK Italian: the May 2023 PDF
URL returns a "Page Not Found" page; the site's menus page links only an allergen guide (autumn 2026), no nutrition guide. Wetherspoon: the menu PDF (MENU_7933,
summer 2026) prints kcal only, says weights are approximate uncooked, and points to the app and customer screen for nutrition; the website links no sheet.
YO! Sushi restaurant menu: 404 (the To Go guide was read). Of the spec's original list, Wetherspoon is above; Nando's, Chipotle, Panera and Denny's were not
attempted in either pass for time (Denny's and Chipotle items are in MenuStat 2017-2018), so those four are reachable gaps, not blocked ones.

**The five rows, before and after**

| row | kind | status before -> after | range before -> after | items before -> after | behind the figure now |
|---|---|---|---|---|---|
| PR02 | fish_main (P3) | unsourced -> proposed_unreviewed | 113-227 -> 211-317 g raw fish | 85 -> 87 plates; stated fish 6 -> 7 items | O'Charley's (6 items, 6 and 9 oz salmon) and Bonefish (Grilled Atlantic Salmon 7.5 oz) state the fish alone; 15 businesses for the whole-plate range; sat fat and cholesterol references from MenuStat, Bonefish, Carrabba's, Zizzi, Prezzo |
| PR03 | crudo_starter (P3) | unsourced -> proposed_unreviewed | 45-110 -> 82-113 g raw fish | 0 -> 3 | Wasabi salmon sashimi 120 g (stated, dressing excluded); YO! salmon 85.0 g and tuna 80.9 g (derived from kcal and USDA) |
| PR05 | tomato_salad_starter (P2) | unsourced -> proposed_unreviewed | 150-300 -> 287.1-301.2 g plated | 1 -> 3 | Pizza Express 284 g, Vapiano 300 g (stated), Zizzi 302 g (derived); Carrabba's caprese adds a reference figure |
| PR06 | tomato_salad_starter (P3) | unsourced -> unsourced | 120-250 g raw tomato, kept for the record | 1 -> 3 plates | no USDA input share for the tomato's share of a caprese; dishes rank through PR05 |
| PR08 | pasta_main (P3) | unsourced -> unsourced | 90-140 g dry pasta, kept for the record | 36 -> 59 plates | no USDA input share for dry pasta; Vapiano's extras put the cooked pasta component at 180 g, a cooked-to-dry conversion would be a new rule (your call); dishes rank through PR09 (117-569 g plated) |

Other rows moved by the sheets: PR01 171-385 -> 175-382 g dough (Vapiano's nine whole pizzas), PR11 31-180 -> 50-243 g raw fish (Zizzi's calamari and prawn
spiedini are heavier plates than MenuStat's), PR09 97-562 -> 117-569 g, and small moves on PR04, PR12, PR17, PR24, PR26-PR28, PR31-PR33 (full diff in spec
12.17 note 16; evidence in `eval/card_evidence_2026-11-06.md`, rebuilt). Reference figures: 126 rows.

**Consequences.** The 44 labelled items excluded under 12.16.8 after the first rebuild (37 fish mains, 6 crudo, 1 tomato salad) are tried again; on the seafood
chalkboard all 9 dishes are selected. The reruns at 00:05 run on this table. Tests: agent 515 passed, 4 skipped (test_3i has 22 tests, three new: the
three-way status, stated weights read from a sheet's item names and sashimi as raw fish, and the chalkboard selected again).

**For your review here:** (1) PR03 reads a sashimi weight as the raw fish of any crudo, ceviche or tartare; a crudo with other things on the plate is sized by
the same fish weight. (2) YO!'s sashimi weights are derived from kcal, not stated; Wasabi's is the only stated sashimi weight. (3) PR02's seven stated items
are all salmon (6, 7.5 and 9 oz); Bonefish's other fish state no weight. (4) PR05's three caprese plates sit within 18 g of each other, so the row's range is
narrow (287-301 g). (5) Vapiano's BBQ Chicken pizza line prints fat figures far below its neighbours; it is taken as printed and noted.

## 14. FNDDS portions as a second source (12.16.8a, built 2026-11-06, evening, before the reruns)

**What was done.** `scripts/fndds_portions.py` looked up one to five Survey (FNDDS) records per family (34 families, pinned FDC ids from a Survey-only search),
read their portions through the nutrition service's portions call, and kept only whole-dish, fillet, steak or restaurant-order gram weights; a cup, spoon,
slice, piece, "Quantity not specified" or an extra-large sharing pizza never qualifies, and size words alone count as a whole item only for item or cut
families (so a small breadstick is not an order of bread). Every record and every portion, qualifying or not, is listed in `eval/fndds_portions_2026-11-06.md`.
USDA requests: 136 for the pass (3600 -> 3464 remaining), the 200 reserve untouched; the reruns later in the night read from the store. `build_cards.py` then
wrote both figures on every row (`fndds_low/high/n/basis/records`, `chain_low/high/n/businesses`) with `range_source` and `sources_status`; the range is FNDDS
where FNDDS gives the key the family needs, the chain figure otherwise; approved_by is empty on all 33.

**The five rows you named**

| row | FNDDS portions found | FNDDS key figure | chain key figure | range used | status |
|---|---|---|---|---|---|
| PR02 fish_main (P3, raw fish) | cod, salmon, bass baked or broiled: small/regular fillet 90-140 g, large fillet 135-210 g, steak 210 g, whole fish 420 g (9 portions) | 156-313 g raw (p10-p90 x 1.2418) | 211-317 g raw (O'Charley's, Bonefish, 7 stated items) | FNDDS | proposed_unreviewed (midpoints 235 vs 264 agree) |
| PR03 crudo_starter (P3, raw fish) | Fish, salmon, raw and Fish, tuna, raw: only "1 cup 135 g" and "Quantity not specified 85 g"; no sashimi record | none | 82-113 g (Wasabi, YO! Sushi) | chain | proposed_unreviewed |
| PR05 tomato_salad (P2, plate) | "Mozzarella cheese, tomato, and basil, with oil and vinegar dressing": only "1 cup 160 g" and the default 80 g | none | 287-301 g (Pizza Express, Vapiano, Zizzi) | chain | proposed_unreviewed |
| PR06 tomato_salad (P3, raw tomato) | same record; a cup of the salad is not the tomato alone | none | none (no USDA input share) | record only | unsourced |
| PR08 pasta_main (P3, dry pasta) | pasta with sauce, restaurant, and lasagna from restaurant: cups, pieces of a pan, the default 250 g | none | none (no USDA input share); PR09 carries pasta on 117-569 g plated | record only | unsourced |
| PR11 fish_starter (P3, raw seafood) | calamari fried, shrimp fried, crab cake: "1 item", "1 prawn", cups, the default | none | 50-243 g raw (13 plates, 5 businesses) | chain | proposed_unreviewed |

**Every other family** (your item 3) is in the same evidence file. Whole-dish or cut portions exist for: steaks, breasts and chops (PR07: FNDDS 139-300 g raw
by the 80 % yield against chain 170-454 g, agree), whole pizzas (PR01: dough 83-448 g from personal to large pizzas against chain 175-382 g, midpoints agree, but
the range is now much wider), fries orders (PR12: 76-166 g against chain 78-266 g, agree), burgers, sandwiches, wraps, tacos, burritos, fast-food side salads
(PR04, PR28) and dessert pieces (PR32: 99-209 g against 35-255 g, agree). Nothing qualifies for quesadillas, eggs, pancakes, cereal, toast, soup (cups only),
dips, vegetable and rice sides, bread orders, snack bowls, children's dishes or fish and chips as a dish (PR15 records the fried-fillet portions 140-420 g and
keeps its cited range).

**sources_disagree, four rows, all running on the FNDDS range as 8a says:**

| row | FNDDS range | chain range | note |
|---|---|---|---|
| PR04 leaf_salad_starter | 90-146 g | 97-356 g (33 items, 16 chains) | FNDDS has fast-food side salads only (McDonald's, Burger King, Wendy's), not a restaurant starter salad |
| PR16 burger | 123-171 g | 84-424 g (260 items, 16 chains) | FNDDS burgers are the one-patty fast-food items; chain burgers run to 424 g |
| PR17 sandwich | 130-240 g | 128-539 g (879 items, 31 chains) | FNDDS deli and fillet sandwiches; chain subs and melts are heavier |
| PR18 wrap | 136-157 g | 288-474 g (219 items, 7 chains) | three FNDDS wraps, half the chain weight; the biggest gap in the table |

**What this does to Roli tonight.** Twelve rows take their range from FNDDS. On the 13 menus the effect falls mostly on fish mains (PR02 a little lower and
wider), meat mains (lower), pizzas (a much wider dough range, so more pizzas hit the plate-share cap of 1), fries, burgers, sandwiches and desserts; nothing
is tuned. The reruns at 00:05 run on this table, so coverage, the plate-share check and repeatability (sections 1, 3, 4, 8) are measured on it.

**For your review here:** (1) whether a fast-food side salad or one-patty burger is the right FNDDS stand-in for a restaurant plate (the four
sources_disagree rows); (2) whether a whole fish (420 g cooked) belongs in the fish-main fillet range; (3) the pizza reading: personal to large pizzas count
as one plate, extra-large does not; (4) the meat conversion: FNDDS cooked cuts to raw by the 80 % sirloin yield; (5) the midpoint reading of "disagree by more
than a third". Tests: agent 518 passed, 4 skipped (three new 12.16.8a tests: the portion rule, the fit and conversion with the disagreement mark, and the
table's columns).

