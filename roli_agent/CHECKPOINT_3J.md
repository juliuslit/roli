# Checkpoint 3J: your decisions on 3I, built and rerun

Date: 2026-11-07 (build) and 2026-11-08 (reruns). Spec: `SPEC_3_mvp.md` 12.18 (your decisions), build readings in 12.19.

**Stopped here for your review.** No new USDA release data is approved; Telegram and deployment are not started.

## 1. Result in brief

**How the reruns went.** The passes were queued for 00:05 on 2026-11-08, but the Mac slept through the night (the power log shows a dark wake every 15 minutes and a real wake at 07:48, when you opened it). The clock check only cleared at 01:17 in one of those wakes; the first two menus failed in the menu reader with a connection error, and the rest ran only after 07:48. **Round 1** (07:48-08:55) then exposed a wiring bug of mine (section 6a): the dish-kind call decided which dishes to try, but the evaluation step took the family from the word lists again, so 30 dishes ran under the wrong family and 15 with no portion rule at all. Fixed with a test, and **round 2** (09:01-09:39, all 13 menus fresh, then the four test menus on saved readings) is the 3J result below. Round 1 is kept for the record (`eval/coverage_2026-11-08_3j_round1.md`). Both rounds ran one pass at a time, within the caps; the day's ledger closed at $3.23 and 215 credits (the caps are $5.00 and 300).

- **Coverage: 66 of 406 food dishes at 3I (16 %) -> 101 of 402 at 3J (25 %).** Every menu with mains gained or held except Dwarf Grill (9 -> 8, reader variation). Alex's Kitchen 13 -> 26, The Greyhound 7 -> 16, Ren's Kitchen 5 -> 8, Pizzaface 3 -> 7, Flour + Water 4 -> 7.
- **The cap now cuts 145 dishes, not 220**, and 120 of those are Alex's Kitchen's 150 dishes against a cap of 30. No other menu loses more than 16. No menu hit a spending cap in round 2 (round 1 had two: Ren's Kitchen on 30 credits, Alex's Kitchen on $0.50; both were cold, round 2 ran warm on their caches).
- **Sides, soups, dips, desserts and kids' dishes are out of the top three** on every menu and get their own line: Alex's Kitchen reads "Lightest side: Plain Rice, 0.1-2.1 g. Lightest soup: Vegetable Canton Soup, 0.5-0.8 g."; Mother's Tacos "Lightest side: Tortillas & Salsa, 0.0-0.0 g. Kids: Quesadilla, 2.7-12 g."; The Shed "I couldn't estimate a main dish on this menu (8 tried). Kids: Scrambled Eggs on Toast, 1.7-7.2 g." Pizzaface's Marinara sauce, first on the menu in round 1 under the word lists' pizza family, is a dip under the model's family and sits in the dip line.
- **Flags: 8 open, all above the range** (section 7). The heirloom tomatoes rank first on Flour + Water and the lettuce-and-tomato sandwich ranks on Dwarf Grill; both carry the "below the published range; plain recipe" note and their flags are closed.
- **Repeatability:** pass B matched pass A on two of the four menus; on the other two one dish moved because the USDA matching model declined a line in pass A and matched it in pass B (section 8). Recommendations and orders were the same on all four. The Greyhound dessert that differed at 3I was identical in both passes of both rounds.
- **Dish-kind call:** on in every run, 0 fallbacks to the word lists across 13 menus; 9 items read as "not a dish" or "add-on" (sharing platters, a chicken for two, side orders of bacon, sausage and ham), all defensible.
- **Tests:** agent 532 passed, 4 skipped (519 at 3I); library 337; `test_report_3j.txt`.

## 2. What changed and where

| decision (12.18) | change | where |
|---|---|---|
| 1-4 approvals | your decisions per row live in `recipes/portion_approvals.csv`; the builder copies them onto the table last, so a rebuild keeps them; PR01 171-385 g dough, PR04/PR16/PR17/PR18 on the chain figures with the FNDDS figure kept as a note and `sources_disagree` dropped; PR07 as is; every row `approved` (PR06, PR08 stay `unsourced`) | `recipes/portion_approvals.csv`, `scripts/build_cards.py` (`load_approvals`, `apply_approvals`), `recipes/portion_rules.csv`, `eval/card_evidence_2026-11-06.md` |
| 5 egg reading | nothing changed; pinned by the 3I tests | `tests/test_3i.py` |
| 6 dish kind | `MvpConfig.dish_kind_model` True; every fallback to the word lists logged with the item and the reason (`log["fallbacks"]`), kept in `MenuRun.dish_kind_log` | `mvp/models.py`, `mvp/dish_kind.py` |
| 7 non-main families apart | `APART_GROUPS` (sides, soups, dips, desserts, snacks, kids) after the mains, never in the top three; one "Lightest side/soup/dip/dessert/snack: name, range" or "Kids: ..." line per group present; kids only with a children's section; dropped first under the word limit | `mvp/ranking.py` (`APART_GROUPS`, `apart_lines`, `recommendation_text`), `mvp/menu_run.py`, `mvp/models.py` (`RankedDish.listed_apart`), `mvp/web.py` |
| 8 flag above only | a middle below the published range is not flagged: the dish ranks, the comparison carries the note "below the published range for this kind of dish; plain recipe", `ReferenceCheck.below_published` shows on the diagnostics page | `mvp/reference.py`, `mvp/web.py` |
| 9 the cap | `MvpConfig.max_dishes` 30; `eval_mvp --max-dishes` defaults to the config; the coverage script tells "the dish cap" from "a spending limit" | `mvp/models.py`, `scripts/eval_mvp.py`, `scripts/coverage.py` |
| 10 search order | **not added**; the real cause of the Greyhound difference was found and fixed instead (section 6) | `recipes/match.py` |
| 11 dish-kind evaluation | reads the per-item cache before calling the model and reports how many items it answered | `scripts/eval_dish_kind.py` |
| bug fix (6a) | the family the dish-kind call chose now reaches the portion rules, not only the selection | `mvp/menu_run.py` (`evaluate_dish(..., dish_type=)`) |
| tests | 13 new tests in `tests/test_3j.py`; 7 older tests updated to the new statuses, the "Lightest snack" wording and the below-range note | `tests/` |

Tests: agent 532 passed, 4 skipped (519 at 3I); library 337 passed, unchanged (`test_report_3j.txt`). The table rebuild with the approvals moved only the five rows you named; `reference_figures.csv` is byte-identical to 3I.

## 3. The table as approved

| row | family | range now | range before | status |
|---|---|---|---|---|
| PR01 pizza | dough per pizza | **171-385 g** (Pizza Express plus AVPN) | 83-448 g (FNDDS whole pizzas), kept as a note | approved |
| PR04 leaf salad | plated salad | **96.6-355.6 g** (chain, 33 items) | 89.8-146.0 g (FNDDS fast-food side salads), kept as a note | approved |
| PR16 burger | whole item | **83.7-424.1 g** (chain, 260 items) | 123.0-171.0 g (FNDDS), kept as a note | approved |
| PR17 sandwich | whole item | **128.0-538.7 g** (chain, 879 items) | 130.0-240.0 g (FNDDS), kept as a note | approved |
| PR18 wrap | whole item | **288.0-474.0 g** (chain, 219 items) | 136.0-156.8 g (FNDDS), kept as a note | approved |
| PR07 meat | raw meat | 139-300 g (FNDDS cuts; chain 170-454 beside it) | same | approved as is, stated ounces = raw cut, yield note kept |
| 25 other sourced rows | | as they stood | same | approved |
| PR06 raw tomato, PR08 dry pasta | | 120-250 g, 90-140 g for the record only | same | unsourced, approved as such; never used |

**Reading to check (12.19.1):** "every row" includes PR06 and PR08, so they carry your name too; their status stays `unsourced` and they never run. If you meant to leave those two columns empty, delete the two rows from `portion_approvals.csv` and rebuild.

## 4. Coverage before and after

`eval/coverage_2026-11-08_3j.md` (before = the 3I pass A runs of 2026-11-07; after = round 2 pass A, 2026-11-08 09:01-09:35).

| | before (3I) | after (3J, round 2) | round 1, for the record |
|---|---|---|---|
| food dishes on the 13 menus | 406 | 402 (the reader read Ren's Kitchen as 37 items, 41 before) | 405 |
| ranked | 66 (16 %) | **101 (25 %)** | 91 (22 %) |
| tried, not ranked | 83 | 147 | 144 |
| not tried, the dish cap | 220 | 145 | 150 |
| not tried, a spending limit | 0 | 0 | 11 |
| outside what Roli ranks | 37 | 9 (all by the dish-kind call: platters, a chicken for two, side orders) | 9 |

Causes of "tried, not ranked" after: no recipe could be portioned 61 (30 before), no usable recipe 32 (15), no upper bound from a line with no weight 24 (13), flagged 8 (5), raw or cooked state unresolved 7, no USDA record 6. The rise in "no recipe could be portioned" and "no usable recipe" is the cap: dishes 15-30 in each menu's selection order are the ones the lean-word score liked least, and they portion less often (tacos, loaded fries, pastries).

## 5. The cap, the top three, the tester replies

**The cap.** 145 dishes cut by the cap of 30 (220 at 14): Alex's Kitchen 120 (150 candidates), Pizzaface 16 (46), Ren's Kitchen 7 (37), The Greyhound 2 (32); every other menu now tries every candidate. **Spending against both caps (round 2):** no menu reached $0.50 or 30 credits; the dearest was Ren's Kitchen at $0.291 and 24 credits, Alex's Kitchen $0.111 and 2 credits (warm caches). In round 1, cold, Ren's Kitchen reached the 30-credit menu cap (7 dishes skipped before they started) and Alex's Kitchen the $0.50 model cap (4 skipped, and three "next call blocked" interruptions). So a 30-dish menu with no cache behind it can hit the spending caps before the dish cap; the table in the coverage file has the per-menu figures for both rounds.

**Top three per menu, sides and desserts out of it** (full list with the apart dishes in the coverage file): Flour + Water: heirloom tomatoes 1.8-2.1 g, bluefin crudo 0.8-11 g, little gem lettuces 4.3-14 g. The Greyhound: Padron peppers 0.2-3.1 g, Cornish fish and chips (4.7-8.0 g in vegetable oil, up to 23 g in beef dripping), pan fried seabass 4.1-26 g; twelve dishes listed apart (broccoli, green beans, mixed leaf salad, onion rings, olives, two chips, mash, three desserts). Zuni (both photos): Caesar salad 2.2-8.0 g, yellowfin tuna 3.3-12 g, spaghetti with Gulf shrimp 0.8-15 g; olives, the tomato soup and shoestring potatoes apart. Chalkboard: poke salad 0.5-6.8 g, crumbed whiting 1.2-5.9 g, battered oysters 1.3-6.5 g. Ren's Kitchen: shakshuka 1.1-9.9 g, the only main; four sides and three desserts apart. Pizzaface: Greek salad 2.9-14 g, garden salad 2.5-16 g; five dips apart (chilli oil 1.0-5.3 g the lightest). Alex's Kitchen: boiled noodle with hot chicken 0.8-3.9 g, boiled noodle with hot veg 1.0-5.0 g, Sichuan veg soft noodles 0.6-6.0 g; six soups and seven rice sides apart. Mother's Tacos: chilorio mulita 1.2-8.2 g, the only main; tortillas and salsa, beans, red rice and the kids' quesadilla apart. Dwarf Grill: chicken salad 1.4-5.8 g, bacon tomato 3.5-9.7 g, lettuce and tomato 1.4-21 g. Own photo: nothing ranked (5 with no upper bound, 1 flagged). The Shed: no main; the kids' scrambled eggs apart.

**Tacos.** Mother's Tacos' tacos are typed `taco` by the model, nine were evaluated, none ranked: as at 3I, the taco recipes found give no served mass for the P2 row. Not changed.

**The taco and breakfast menus as a tester sees them:**

> **Mother's Tacos (run 20261108-142931-fd41cc):** "Among the 5 dishes I could estimate (28 tried; 23 had no usable estimate), lowest saturated fat first: 1) Chilorio, about 1.2-8.2 g saturated fat per plate. It's the only dish I could estimate, so this is one figure, not a ranking. Chilorio cholesterol about 18-116 mg. Lightest side: Tortillas & Salsa, 0.0-0.0 g. Kids: Quesadilla, 2.7-12 g. Modeled from published recipes and typical portions, not this kitchen's numbers." The Chilorio is the mulita (quesadilla family), not a taco; red rice and beans are in the ranking table as sides but the word limit dropped their lines after the first side; the kids line appears because the menu has a NIÑOS section.

> **The Shed breakfast (run 20261108-142413-5f3687):** "I couldn't estimate a main dish on this menu (8 tried). Kids: Scrambled Eggs on Toast, 1.7-7.2 g. Modeled from published recipes and typical portions, not this kitchen's numbers." Seven adult dishes could not be ranked (lines with no weight, no portionable recipe); the only estimate is the children's one, now said so.

## 6. The Greyhound dessert: the real cause, and what was built instead of the URL sort

Your item 10 asked for cached search results sorted by URL. I did not add it, for two reasons found when the two 3I runs were compared line by line:

- The scenario cap already sorts its candidates by relevance grade, then quantified lines, then URL, and a cached search answer is one saved list read in the same order by every pass. A URL sort would change nothing between pass A and pass B; it would only reorder which pages a fresh search fetches first, losing the search engine's relevance order.
- The difference had another cause. In pass A the greatbritishchefs recipe's line "350ml of whole milk" matched no USDA record (the model declined: no fluid whole milk among the candidates), so the recipe's served mass was incomplete, it could not be portioned, and the backfill brought in the garnishwithlemon crisp as a fifth recipe. In pass B the same line was answered from the USDA match cache with a **proxy chosen for another dish**: "Soymilk, original and vanilla, unfortified", reason "the dish context is vegan". The crumble then portioned on four recipes and the crisp stayed beyond the cap. The cache keyed decisions by ingredient name and preparation hint only, so a proxy that rests on one dish's context reached every dish naming that ingredient. Soy milk for whole milk in a crumble also moved the figures the wrong way.

**Fixed (12.14: bugs are always fixed):** `MatchCache` now saves a proxy under the dish's context and reuses it only for that dish; a direct match of the same food is reused everywhere as before; proxies saved by the earlier code under the bare key are not reused (they are matched again). Cost: proxy lines are matched once per dish instead of once overall; direct matches, the large majority, are unchanged. Test: `test_3j.py::test_a_proxy_match_is_reused_only_for_the_dish_it_was_chosen_for_and_a_direct_match_everywhere`.

**The Greyhound dessert repeat (pass A against pass B):** the apple and rhubarb crumble read 6.9-16.9 g in pass A and pass B of round 1 and in pass A and pass B of round 2, 0 differences on the dish. In round 2 the Greyhound's one A/B difference was the cheese slate (section 8).

### 6a. The dish-kind wiring bug (found by round 1, fixed before round 2)

`MenuRunner.evaluate_dish` recomputed the family with `dish_type_for(item)`, the word lists, although selection had already taken the family from the dish-kind call. In round 1, 30 selected dishes had a model family different from the word lists' and ran under the word lists' family; 15 of them had no word-list family at all and were tried with no portion rule (Mother's Tacos' loaded fries, Ren's quiche and pastries, Zuni's bowl of polenta, Pizzaface's coleslaw and BBQ sauce). Pizzaface's Marinara sauce ranked first as a pizza. Fixed: the runner passes the candidate's family into `evaluate_dish(..., dish_type=c.dish_type)`; without the argument the word lists decide as before, so the older callers and tests are unchanged. Test: `test_3j.py::test_the_evaluation_uses_the_family_selection_decided_not_the_word_lists`. Round 2 ranked 101 dishes against round 1's 91 on the same code otherwise.

## 7. Flags

Open after round 2: **8 dishes, all above the published range** (`runs/flags.jsonl`; the two below-range flags of 3I are closed: heirloom tomatoes on 2026-11-07 in the smoke test of the final code, lettuce and tomato at 08:38 today).

| menu | dish | family | Roli's middle | published range (per plate unless said) | top contributors |
|---|---|---|---|---|---|
| Flour + Water | Salsiccia Bianca | pizza | 42.8 g | 2.5-21.2 | caciocavallo, butter, Italian sausage |
| own photo | Pork belly | meat main | 65.8 g | 2.0-32.0 | pork belly, butter, clarified butter |
| Pizzaface | Margherita | pizza | 36.9 g | 2.5-21.2 | mozzarella, canola oil, flour |
| Pizzaface | Garlic bread | side bread | 15.8 g | 0.0-10.0 | mozzarella / butter, parmesan |
| Pizzaface | Garlic bread with cheese | side bread | 19.9 g | 0.0-10.0 | butter, mozzarella, parmigiano |
| Pizzaface | Goats cheese salad | leaf salad | 23.2 g | 0.0-10.0 | a log of goat cheese |
| Pizzaface | Parma salad | leaf salad | 17.3 g | 0.0-10.0 | mozzarella, dressing, Parmesan |
| The Greyhound | Pigs in blankets | vegetable starter | 24.7 g (per 100 g 13.7 against 0-7) | 0.0-16.0 | butter, cocktail sausages, mayonnaise |

Five of the eight are new since 3I and come from the chain ranges of the new families (side bread 0-10 g, leaf salad 0-10 g, vegetable starter 0-16 g): a garlic bread with cheese or a salad built on a log of goat cheese sits above a range made of chain side salads and bread orders. Whether those are wrong estimates or right estimates of rich dishes against lean ranges is for you (section 12). Nothing below the range is flagged any more; the two below-range notes in round 2 are the heirloom tomatoes (1.9 g against 4.0-18.0, a plain tomato salad against caprese figures) and the Chilorio mulita per 100 g (2.1 against 4.2-11.0).

## 8. Repeatability: pass A against pass B

`eval/mvp_repeatability_2026-11-08_3j.md` (round 2; round 1's comparison is in the file's history only through the checkpoint: 3 of 4 identical, Zuni two dishes).

| menu | menu read | recommendation | ranking and figures | model $ A / B |
|---|---|---|---|---|
| 03 Flour + Water | same | same | same | 0.026 / 0.013 |
| 08 The Greyhound | same | 16 against 17 dishes estimated | the cheese slate: no upper bound in A, 6.7-14.1 g in B | 0.121 / 0.022 |
| 01 Zuni Cafe | same | 2.2-8.0 against 2.0-8.0 on the Caesar salad | Caesar salad low end 2.18 against 1.95 g | 0.043 / 0.006 |
| 23 Seafood chalkboard | same | same | same | 0.009 / 0.003 |

Both differences are the same mechanism: the USDA matching model declined a line in pass A ("1/4 pound chewy, rustic French or Italian bread": "an adjective with no identifiable food item"; a cheese on the cheese board) and matched it in pass B (a proxy, "rustic chewy bread croutons"). An unresolved decision is never cached (by design, D7), so pass B asked again, with a batch of lines that was smaller because the rest came from the cache, and the model answered differently. The top three and their order were the same on all four menus. The search-cache and proxy-leak causes of 3I are gone (section 6); what remains is the matcher's own variation between calls. Not tuned.

## 9. Spending

From the ledger (`runs/spend_ledger.jsonl`), 2026-11-08, caps $5.00 and 300 credits a day, $0.50 and 30 a menu, unchanged.

| what | model $ | credits | USDA requests |
|---|---|---|---|
| round 1 pass A, 11 menus (07:48-08:50) + 2 failed reader attempts ($0) | 1.78 | 139 | 690 |
| round 1 pass B, 4 menus; repeat of menus 03 and 08 (A2, B2) | 0.19 | 2 | 36 |
| round 2 pass A, 13 menus (09:01-09:35) | 1.01 | 60 | 222 |
| round 2 pass B, 4 menus (09:35-09:39) | 0.05 | 0 | 11 |
| 2026-11-07 smoke test of the final code, menu 03 | 0.12 | 0 | 91 |
| **day total 2026-11-08** | **3.23** | **215** | |

USDA: 3,599 of 3,600 left before round 1 pass A, 3,021 before its pass B, 2,925 and 2,919 before the repeat passes, 2,943 before round 2 pass A, 3,102 before its pass B; the 200 reserve was never approached. The dish-kind call cost $0.005-0.02 a menu; in round 2 most items came from the per-item cache (Alex's Kitchen: 157 of 157).

## 10. Questionable or unexpected

- **The Mac slept.** `caffeinate -i -s` holds off idle and system sleep but not a closed lid; the queued reruns need the laptop open and on power, or a machine that stays up. The two failed menus cost nothing (the reader never answered) and were repeated.
- **The wiring bug (6a)** meant your decision 6 was half applied for one round. Round 1's numbers are kept apart; round 2 is the result.
- **The remaining pass-to-pass difference is the USDA matcher**, which may decline a line once and match it the next time when its batch differs. It changes a low end by a few tenths of a gram; it never changed a recommendation in these runs.
- **New flags from the new families' chain ranges**: garlic breads, a goats cheese salad and a Parma salad at Pizzaface, pigs in blankets at the Greyhound. The ranges (side bread 0-10 g, leaf salad 0-10 g per plate) come from chain sides and may be too lean for a pub or pizzeria portion with cheese; or the estimates are high. Not decided here.
- **Alex's Kitchen** has 150 food dishes; the cap of 30 leaves 120 untried, and the reply says "120 not tried". Any cap leaves most of that menu unseen.
- **Mother's Tacos**: nine tacos evaluated, none portioned (no served mass in taco recipes); the only ranked main is the mulita. The reply calls it "the only dish I could estimate" while four sides and the kids' quesadilla are estimated and listed apart; the wording counts mains only, by design.
- **The word limit** drops the second and later "Lightest ..." lines before anything else; on Mother's Tacos the beans and red rice lines were dropped and only the tortillas line stayed. Fine by 12.18.7, but a tester sees one side when three were estimated.
- **Chilorio** sits below the quesadilla family's per-100 g range (2.1 against 4.2-11.0) and ranks with the note; that family's figures are MenuStat quesadillas with cheese, the mulita recipe found has little.
- **Reader variation** changed the food-dish count (406 -> 402) and Dwarf Grill lost one ranked dish for it; the saved-reading pass B exists for that reason.

## 11. Not built, and why

- The URL sort of item 10 (section 6).
- The dish-kind evaluation was not rerun: nothing in 12.18 asked for it, and the labels are unchanged (the 92 unsure stay unsure). The live runs now fill the per-item cache, so a later evaluation costs little.
- Nothing for the tacos: Mother's Tacos' tacos still need a recipe with a served mass for the P2 row (3I section 4); no decision was taken on it.
- Telegram, deployment, accounts: the step after this one.

## 12. Decisions for you

1. **PR06 and PR08 approvals (section 3):** keep your name on the two unsourced rows (approving that they stay unsourced), or clear it.
2. **The five new flags** (section 7): wrong estimates, or right estimates against chain ranges that are too lean for these dishes? If the latter, the reference figures for side_bread, leaf_salad_starter and vegetable_starter need a decision (a wider range, a like-with-like rule for cheese, or leave flagged).
3. **Alex's Kitchen and the cap**: 120 of 150 dishes untried at 30. Leave it, raise the cap for dense menus, or let a tester choose a section.
4. **Tacos**: a P2 row needs a served mass; taco recipes give counts. Options as at 3I: a per-taco weight row from FNDDS (103-160 g per order is already on PR19), or leave unranked.
5. **The matcher's pass-to-pass variation** (section 8): accept, or cache a "declined" decision per dish so pass B repeats pass A.
6. **The sleep problem**: how the overnight reruns should run (lid open on power; or run them in the day).
7. Telegram and deployment: the step after this one, untouched.
