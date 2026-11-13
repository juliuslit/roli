# Checkpoint 3C: USDA Survey (FNDDS) records, herbs left out, recipe replacement, serving count

Date: 2026-11-05. Status: **built, tested, rerun live on the four menus (several passes, each fixing something the previous one exposed); stopped for review.**
Decisions implemented today, all Julius's: leave herbs and spices out (rule I03); replace a recipe that cannot be portioned; read the serving count beside the
serving word; use USDA Survey records. Specs: `SPEC_3_mvp.md` sections 10-11, `nutrition_service/SPEC.md` section 17. Tests: `test_report_3c.txt`
(agent **318 passed**, library **319 passed**, no regressions; Phase 2A arithmetic untouched). Before/after per dish: `eval/mvp_before_after_2026-11-05_survey.md`
(before = this morning's Checkpoint 3B runs; after = the final pass).

## 1. What changed

| Change | Where | Effect seen live |
|---|---|---|
| Herbs and spices left out of the calculation and the recipe weight, labelled (I03; max 0.066 g saturated fat per serving on 266 weighed lines) | `recipes/inference.py`, `pipeline.py` | unblocked recipes whose only open lines were sprigs or bay leaves (marinated olives, pigs in blankets) |
| A recipe that cannot be portioned gives its place to the next eligible one; capped at one round after the first four | `pipeline.py` | more dishes bounded; a third round on the schnitzel made about 900 USDA requests and hit USDA's hourly limit, hence the cap |
| Serving count = the number beside the serving word ("2 cups / 12 servings" is 12) | `parse.py` | the one misread (NYT olives) fixed; others unchanged |
| Nutrition service accepts Survey (FNDDS) foods; `search_foods(..., data_types=)`; `get_inputs` reads a Survey food's recipe inputs; Survey portion rows parsed | `nutrition_service/roli_nutrition/` | spec v2.2 |
| D25: a Survey record of the SAME food lends its cup or spoon weight when the matched record has none; nutrients stay with the matched record | `recipes/survey.py`, `pipeline.py` | 28 measures lent on Flour + Water alone (olives, bread cubes, yogurt, cream); several recipes became complete |
| Fried dishes: each fried component named by the menu is matched to a USDA Survey finished-food record ("Fish, NS as to type, fried" = 65 g raw fish, 25 g batter, 10 g oil per 100 g), given a plate amount from the existing portion rules (raw-flesh rules converted by USDA's raw share; PR12 120-250 g for chips; the record's own serving sizes for coated chicken), added by the Phase 2A calculator, and reported as one more interval, tier `survey_dish_record`, always assumption-driven | `recipes/survey.py`, `portion_rules.csv` PR12 | fish and chips 10.8-22.5 g, crispy squid and prawns 1.8-3.5 g, crumbed whiting 3.2-6.5 g, shoestring potatoes 3.0-6.2 g: all previously unrankable |
| A recipe's stated frying oil ("for frying", or 100 g or more in a recipe that fries) is left open instead of counted as eaten | `pipeline.py` | shoestring potatoes fell from 12.7-23.3 g (436 g of canola oil "eaten") to the Survey record's 3.0-6.2 g |
| A dish's lower bound comes from its bounded recipes; an incomplete recipe's subtotal is a caveat, never the range's low | `compare_dishes.py` | the midpoint no longer leans on partial figures (whiting: 3.2, not 0.7) |
| Rows W50-W55 (lime wedge, pickles, chilli sauces, flavoured butter, peas, mushy peas) so side words stop blocking fried dishes; W53 is the first butter row (10-30 g, major) | `assumed_weights.csv` | fish and chips with mushy peas and tartare now estimable |
| Word limit never cuts the disclaimer | `mvp/ranking.py` | the 80-word gastropub text had lost "not this kitchen's numbers" |

Roli still never invents a frying-oil amount: the oil in a fried-dish estimate is USDA's figure for a typical US preparation in generic vegetable oil, and the
page says so. Branded and Experimental foods stay out.

## 2. Before (3B, this morning) and after (final pass), warm caches

| Menu | Ranked | Top three before | Top three after | Time s | Model $ | USDA requests |
|---|---|---|---|---|---|---|
| Flour + Water | 6 -> 6 | Tomatoes 0.4-2.4; Crudo 0.5-4.3; Little gem 4.4-8.6 | same order; Little gem 4.4-**11.3** (bread cubes now weighed, D25) | 107 -> 141 | 0.048 -> 0.053 | 421 -> 450 |
| The Greyhound | 1 -> **5** | Padron peppers 1.2-3.0 | Padron peppers 0.6-4.0; **Crispy squid & prawns 1.8-3.5**; **Fish & chips 10.8-22.5**; chicken schnitzel 12.5-34.4; pigs in blankets 18.7-46.7 (rerun after the USDA hour reset, with replacement capped: 467 USDA requests, no refusals) | 105 -> 112 | 0.054 -> 0.054 | 170 -> 467 |
| Zuni Café | 4 -> **7** | Soup 0.7-3.9; Caesar 2.0-5.7; Shrimp spaghetti 1.9-11.9 | Soup 0.7-3.9; **Garden salad 0.3-5.4**; Caesar 2.0-5.6; then shoestring potatoes 3.0-6.2, spaghetti, olives 4.8-19.3, ribeye | 112 -> 110 | 0.062 -> 0.059 | 116 -> 110 |
| Seafood chalkboard | 4 -> **5** | Poke 2.0-7.1; Swordfish crudo 2.5-13.2; Snapper 4.7-15.4 | Poke 0.3-7.1; **Crumbed whiting 3.2-6.5**; Swordfish crudo 2.5-12.9 | 84 -> 59 | 0.042 -> 0.026 | 140 -> 88 |

The two fixed-dish toss-ups (tomatoes/crudo; soup/salads) are unchanged. Every new ranked dish is one of today's changes at work: herbs (olives), D25 cup weights
(garden salad, little gem's bread), Survey fried-food records (squid and prawns, fish and chips, whiting, shoestring potatoes). Nothing moved because of
the midpoint rule itself. Today's spend: 23 runs, $1.26 of model calls, 9 Tavily credits; the key shows $12.34 used of $20.00; Tavily 312 of 1,500.

## 3. Sample recommendations (final pass, as shown)

- **The Greyhound** (79 words): Among the 4 dishes I could estimate (14 tried; 10 had no usable estimate; 1 not tried), lowest saturated fat first: 1) Padron Peppers,
  about 0.6-4.0 g saturated fat per plate; 2) Crispy Squid & Prawns, 1.8-3.5 g; 3) Cornish Fish & Chips, 11-22 g. Padron Peppers and Crispy Squid & Prawns overlap, so
  treat that order as a toss-up. Padron Peppers has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.
- **Zuni Café** (65 words): ... 1) Wood fire-roasted tomato and eggplant soup, about 0.7-3.9 g; 2) Garden lettuce salad, 0.3-5.4 g; 3) Zuni Caesar salad, 2.0-5.6 g.
  These ranges overlap, so treat the order as a toss-up. ...
- **Seafood chalkboard** (74 words): ... 1) Ocean Trout / Tuna Poke Salad, about 0.3-7.1 g; 2) Crumbed Whiting, 3.2-6.5 g; 3) Crudo Of Swordfish, 2.5-13 g. These ranges
  overlap, so treat the order as a toss-up. Ocean Trout / Tuna Poke Salad cholesterol about 18-43 mg. ...
- **Flour + Water** (74 words): unchanged order: Heirloom Tomatoes 0.4-2.4 g; Bluefin Crudo 0.5-4.3 g; Little Gem Lettuces 4.4-11 g; toss-up between the first two.

## 4. Questionable or unexpected results, honestly

1. **USDA's hourly request limit was hit** in the last Greyhound run. The key's limit is 3,600 requests per rolling hour (from USDA's own response headers; I first wrote 1,000); the day's reruns had used most of it and the run itself made 1,000 requests, 897 lookups of them for the schnitzel across 11 replacement recipes. The
   schnitzel's Survey lookup then failed with `rate_limited` and the dish dropped out (it had ranked at 10.6-37.5 g in the pass before). Fixes: replacement is capped at
   one round; a run now prints a visible error when USDA refused requests. The Greyhound was rerun after the hour reset with the cap in place: 467 USDA requests, no refusals, and the schnitzel ranked again at 12.5-34.4 g (run 20261105-210830).
   *Correction (2026-11-05, Checkpoint 3D, SPEC_3_mvp.md 12.7):* "897 lookups for the schnitzel" counts service lookups, mostly answered from the in-memory cache, not HTTP requests. The 20:05 Greyhound run started with about 250 of the hour's 3,600 requests left (13 runs since 19:34 had made 3,353); of its 1,000 requests about 750 were refused, and the refusals made the schnitzel's recipes look incomplete, which fetched more recipes. Since 3D a run stops asking USDA at the first refusal and never fetches replacement recipes because of a USDA error.
2. **Marinated olives 4.8-19.3 g** (Zuni): the plate rule for a vegetable starter (120-300 g) is far too large for a bowl of olives, and the oil marinade comes with it.
   You asked to keep one range per dish type; this is the clearest case for your testing feedback.
3. **Fish and chips 10.8-22.5 g**: the fish rule (113-227 g raw) gives up to 349 g of fried fish; a chip-shop fish is 200-300 g. Chips 120-250 g (PR12, proposed, no
   measured source). The direction is right; the top end is generous.
4. **Crispy squid and prawns 1.8-3.5 g** rests entirely on the Survey record and two shared starter-rule halves; cholesterol 132-263 mg (squid). Labelled tentative.
5. **D25 lends measures by food head**: "Olives, green" for castelvetrano, "Bread, white" for sourdough cubes, "Cream, light" for heavy cream. The weights are close
   (cup of bread 40 g, of cream 240 g) and only the measure is borrowed, never a nutrient, but a reader of the diagnostics should know the head-match is loose.
6. **Little gem 4.4-11.3 g**: the top end rose because a recipe's bread cubes are now weighed; the salad's figure is still 60 % assumptions.
7. The Survey "Fish, NS as to type, fried" record is a US average (cod, salmon, catfish, tilapia); a Cornish cod and a British batter differ from it.

## 5. Remaining blockers to local testing

None. The app runs on the current code (`./roli_local.sh start`). Watch for the USDA limit (3,600 requests per hour on this key; a menu uses 100-1,000) if you run many menus in an hour: the run page will say so.

## 6. Still to do

- Your calls: the vegetable-starter plate for snacks like olives (PR10), the chips side (PR12), W53 flavoured butter, and whether a fried dish's Survey estimate should
  show "USDA's oil amount" in the recommendation text itself (it is in the diagnostics only).

Files: `nutrition_service/roli_nutrition/{schemas,nutrients,portions,usda_client,service,inputs}.py`, `nutrition_service/tests/test_survey.py` and 13 fixtures;
`roli_agent/recipes/{survey,inference,pipeline,parse,adapt,compare_dishes,portions,metrics}.py`, `recipes/{assumed_weights,portion_rules}.csv`, `mvp/{models,menu_run,ranking,web}.py`,
`tests/test_mvp_local.py` (+13 tests), `eval/mvp_eval_2026-11-05_survey*.{json,md}`, `eval/mvp_before_after_2026-11-05_survey.md`, 23 runs under `runs/`.

**Stopped here.**
