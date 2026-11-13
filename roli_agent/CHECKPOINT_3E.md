# Checkpoint 3E: changes after the 3D review

Date: 2026-11-06. Spec: `SPEC_3_mvp.md` 12.9, build readings in 12.10; library `nutrition_service/SPEC.md` section 19 (v2.4).

**Stopped here for your review.** Not done, as instructed: no USDA release data approved, the frying-fat spread not worded for testers, Telegram and deployment not started.

## 1. Result in brief

- **Pass B did not match pass A exactly.** All 4 recommendations, all 4 ranking orders and the open flags matched. 4 of 45 evaluated dishes had different figures, two of them ranked. Every one traces to the menu reader, which is not saved. A full stop after "FISH OF THE DAY" moved Snapper's high from 15.4 g to 24.2 g. Saved grades and tags worked as built: no difference traces to them. Section 4 has the detail and a decision for you.
- **Padron peppers and seared-fish pan oil now count as eaten.** Padron goes from 0.6-1.9 g to 0.6-4.0 g and drops from first to second.
- **The Scotch egg's remoulade is counted**: 20-45 g of mayonnaise-type sauce, 2.3-5.3 g saturated fat. The dish stays unranked, because the apple puree, the crackling and the frying oil have no amount.
- **The Sicilian olives' flag closed.** They rank first of five on The Greyhound at 1.0-3.0 g. That rests on one recipe.
- **Fish and chips is still flagged, for a new reason.** On vegetable oil Roli says 6.9-10.1 g; the published vegetable-oil plates are 2-5.2 g. On beef dripping Roli says 21.9-30.7 g. One fat per plate is in force and the chips now follow the fat.
- **Tag test set: role 81 of 81, 0 harmful misses.** The real menus were harder: reading every medium and removed tag in pass A found 2 harmful misses. Neither reached a published figure.
- **Model cost per menu fell 8-17 %**, to $0.07-0.14. A rerun with saved answers costs $0.02-0.05.
- **Tests:** agent 358 passed (338 at 3D), library 333 passed (332 at 3D), no regressions. `test_report_3e.txt`.

## 2. What changed and where

| spec | change | where |
|---|---|---|
| 12.9.13 | `LANGSMITH_TRACING=false`, no other line changed | `.env` |
| 12.9.2, 12.9.4 | tag prompt: what counts as a medium, "when in doubt, eaten", reasons only for tags that change the calculation. Prompt quoted in section 11 | `prompts.py`, `recipes/tags.py` |
| 12.9.3 | fixed test set: 29 recipes, 81 scored lines, 12 unclear lines | `tests/fixtures/line_tag_test_set.json`, `scripts/eval_line_tags.py` |
| 12.9.5 | saved grades and tags keyed by page, menu item, prompt version and model; "grading changed" reason | `recipes/judgements.py`, `recipes/relevance.py`, `recipes/pipeline.py`, `scripts/compare_mvp_runs.py` |
| 12.9.6-7, 12.9.9 | two-figure minimum, like with like, flag lines name top contributors; 20 % and 35 % limits are config values | `mvp/reference.py`, `mvp/models.py`, `recipes/reference_figures.csv`, `recipes/portions.py` |
| 12.9.8 | one fat per plate; chips rebuilt from USDA 2709458 | `recipes/survey.py`, `recipes/portion_rules.csv` |
| 12.9.8 (found while building) | USDA's input weights are the recipe before cooking. Added USDA's stated moisture change, which reproduces the records exactly | `nutrition_service/roli_nutrition/inputs.py` |
| 12.9.10 | rows W56 tartare sauce and W57 clinging olive oil | `recipes/assumed_weights.csv`, `.md`, `recipes/adapt.py` |
| 12.9.11 | 3D guards kept | `recipes/tags.py` |
| 12.9.12 | provenance labels; 10 dated notes added, nothing rewritten | `reference_figures.csv`, `CHECKPOINT_3D.md` |
| new tools | pass A against pass B comparison | `scripts/repeatability.py`, `tests/test_3e.py` |

**Where the brief and the spec differ, or the build reads the spec a particular way:**

- Oil wiped on a grill grate is a medium. 12.9.3 expects that tag, though 12.9.2's list does not name it.
- W56 uses USDA's own tartar record, not the UK labels, because a nutrient value may only come from a USDA record. The labels judge the record. The record runs high: 3.3 g per 100 g against labels of 1.6-2.1 g, up to about 0.5 g too much per plate.
- The tag prompt also shows up to four method sentences per recipe. A line alone cannot tell a frying bath from a skillet's oil. Without them, role still scored 81 of 81, and kind 76 instead of 77. They stayed in because real recipes are harder than the set.
- The published figures moved out of `portion_rules.csv` into their own file, because the check needs each figure's business, basis and total fat.

## 3. Before and after, top three per menu

Before = the 3D runs. After = pass A on the final code. The Greyhound and seafood "before" runs were made on pass-2 code (12.9.1). Saturated fat per plate.

| menu | | before | after |
|---|---|---|---|
| Flour + Water | 1 | Heirloom Tomatoes 0.4-2.4 | same |
| | 2 | Bluefin Crudo 0.5-4.3 | same |
| | 3 | Little Gem Lettuces 4.4-11.3 | same |
| The Greyhound | 1 | Padron Peppers 0.6-1.9 | Sicilian Olives 1.0-3.0 |
| | 2 | Crispy Squid & Prawns 1.8-3.5 | Padron Peppers 0.6-4.0 |
| | 3 | Pan Fried Seabass 8.7-23.2 | Crispy Squid & Prawns 1.8-3.5 |
| Zuni Cafe | 1 | Marinated olives 1.3-3.3 | Marinated olives 0.7-4.0 |
| | 2 | Tomato and eggplant soup 0.7-3.9 | same |
| | 3 | Garden lettuce salad 0.3-5.4 | same |
| Seafood chalkboard | 1 | Ocean Trout / Tuna Poke Salad 2.9-7.0 | same |
| | 2 | Crumbed Whiting 3.2-6.5 | same |
| | 3 | Crudo Of Swordfish 2.5-12.9 | same |

**Why the changes happened:**

- **Sicilian Olives** entered the ranking because the flag closed.
- **Padron** moved because its oil now counts.
- **Pan Fried Seabass** left the ranking because the pass-2 fault is gone. In 3D the fault zeroed its "New Potatoes" line, which gave it an upper bound. Now that line is open and there is no weights row for it. The before/after file says "grading changed" for this dish; that is true but it is not the main reason.
- **Snapper and Ocean Trout** changed from 4.6-24.2 g and 6.8-26.1 g to 4.7-15.4 g and 8.8-18.1 g. **That is not a 12.9 effect.** The 3D reader wrote "FISH OF THE DAY." and pass A wrote it without the full stop, so the search differed. Pass B's reading matched 3D's and gave back nearly the 3D figures. The other four dishes on that board that I compared kept the same query.

Full tables: `eval/mvp_before_after_2026-11-06_3e.md`.

## 4. Repeatability: pass A against pass B

| menu | menu read | recommendation | ranking order | figures | model $ A / B | USDA requests A / B |
|---|---|---|---|---|---|---|
| Flour + Water | same | same | same | same | 0.1208 / 0.0197 | 3 / 3 |
| The Greyhound | different | same | same | 1 unranked dish differs | 0.1299 / 0.0473 | 8 / 10 |
| Zuni Cafe | different | same | same | 1 unranked dish differs | 0.1388 / 0.0438 | 0 / 4 |
| Seafood chalkboard | different | same | same | 2 ranked dishes differ | 0.0673 / 0.0288 | 23 / 1 |

| dish | pass A | pass B | what the reader changed |
|---|---|---|---|
| Ocean Trout | 8.8-18.1 g | 6.8-26.1 g | section gained a full stop; description lost "SALAD" |
| Snapper | 4.7-15.4 g | 4.6-24.2 g | same |
| Sirloin Steak (unranked) | low 7.8 g | low 9.5 g | "10oz" dropped from the name |
| Yellowfin tuna (unranked) | no figure | low 3.0 g | footnote asterisk copied into the name |

**How a small reading change moves a figure.** The reader's text is copied into the search query, punctuation included, so a full stop or an asterisk is a different search with different pages. A changed description also changes the item key, so saved grades and tags do not apply. The reader runs at temperature 0 and still varies.

**One difference did not come from the reader.** Chicken Schnitzel's tag call returned an invalid answer in pass A, so the dish ran on the older text patterns. Failed answers are not saved, so pass B asked again. The figures were the same. It was the only failed tag call in eight runs.

Every difference is listed in `eval/mvp_repeatability_2026-11-06_3e.md`.

**Decision for you:** I recommend two changes, and built neither because 12.9 asks only for saved grades and tags:

1. Save the reader's answer per photo, prompt and model. The same photo then repeats exactly, and this is the one that meets your "should match exactly".
2. Strip punctuation from search queries. This helps whenever two readings differ, including a new photo of the same menu.

Note that the first hides reader variation rather than fixing it. Snapper at 15 g or 24 g depends on which recipes were found. Saving would fix the number, not make it right.

## 5. Line tags

**Test set (live, two runs, same result both times):** role 81 of 81; kind 77 of 81; harmful-direction misses 0, before and after code's checks; $0.025 per run, 28 calls. Report: `eval/line_tag_test_2026-11-06_first.md`.

**The 4 kind misses**, all in the safe direction, because a prepared product never passes the near-zero rule: fish stock, chicken stock, vegetable stock and "1 sausage" tagged `prepared_product`. I left the expected answers as written rather than edit them to fit the model.

**Caveat:** I wrote the set and the prompt from the same spec wording, so 100 % overstates it. The real lines below are the better test.

**Real menu lines (pass A):** 1,994 tagged lines: 1,906 eaten, 56 cooking medium, 32 removed. I read all 88 medium and removed tags. For the marinade lines I judged most from the line and the model's reason, and opened the method only for the three below. I did not audit the eaten lines, apart from the oil and butter lines of the seared and fried fish dishes.

| line | dish | tagged | what the recipe does | effect |
|---|---|---|---|---|
| 1/4 cup extra virgin olive oil (life-in-the-lofthouse) | Margherita | medium, "marinade for tomatoes" | oil is then brushed on the dough and baked: **eaten, harmful miss** | recipe out of the range, also incomplete on other lines; no published figure changed |
| 1 tbsp olive oil (aline-made) | Fuyu persimmon and beet | medium, "marinade" | dressing stays on the plate: **eaten, harmful miss** | dish could not be portioned anyway |
| olive oil, to cover the carrots (foodmymuse) | Bluefin Crudo | medium | shallow-fried, then drained: unclear | recipe out of the range, also incomplete on other lines |

Both harmful misses have one cause: the rule says a marinade is a medium, and these marinades are eaten. **Decision for you:** should a medium be only a marinade that is drained or discarded?

**Code guards:** in pass A they rejected 30 medium tags and 9 removed tags, all kept as eaten. Example: the model tagged a whole Pork Chop marinade as medium, and the code kept the chiles, garlic, sugar and spices.

**Confirmed on real lines:** all Padron oil lines are eaten; pan oil and butter are eaten on King Salmon, Snapper and Cobia; oil lines that say they are for frying are media. Some larger amounts stay eaten where the method is unclear (for example "200ml of rapeseed oil" on the squid, "1/2 cup vegetable oil" on the snapper). That follows "when in doubt, eaten" and errs high.

**12 unclear lines for you to decide**, with the model's answer. The build decided none of them.

| line | model's answer |
|---|---|
| lemon rind strips in a marinade | removed |
| steeped garlic | eaten |
| soy sauce in a discarded marinade | eaten, prepared |
| poaching milk | medium |
| salt "maybe" for pasta water | medium |
| semolina for the peel | eaten |
| shallow-fry with 1 cup of oil | eaten |
| lemon in a cavity | eaten |
| roasted garlic heads | eaten |
| cooking spray | eaten |
| oil covering carrots | medium |
| couscous boiling water | eaten |

## 6. Flags

| dish | check | Roli's middle | published | allowed | result |
|---|---|---|---|---|---|
| Sicilian Olives | per 100 g, 5 independent | 2.68 g | 1.7-2.8 g | 1.13-4.2 g | passed |
| | per plate, 1 figure | 2.01 g | 1.4 g | | shown only |
| Marinated olives (Zuni) | per 100 g, 5 independent | 3.12 g | 1.7-2.8 g | 1.13-4.2 g | passed |
| | per plate, 1 figure | 2.34 g | 1.4 g | | shown only |
| Fish and chips | unlabelled, 3 independent | 18.8 g | 10.25-22.8 g | 6.83-34.2 g | passed |
| | vegetable oil, 2 independent | 8.48 g | 2-5.2 g | 1.33-7.8 g | **failed, above** |
| | beef dripping, 1 figure | 26.3 g | 35.6 g | | shown only |

**Sicilian olives: closed.** It closed on the two-figure rule (one chain cannot flag) and because the per-100 g check passes. Its plate figure would have been inside the allowance. Top contributors: none recorded, as it is not flagged. Caution: it ranks first on one recipe, thecozyapron, and the W57 oil share drives the range. Zuni's plate middle of 2.34 g would fail if a second plate figure appeared, since the allowance is 2.1 g.

**Fish and chips: open.** Top contributors at the middle of the whole range:

| line | saturated fat | share of the middle |
|---|---|---|
| chips frying fat | 10.93 g | 58 % |
| fish frying fat | 5.95 g | 32 % |
| mushy peas | 0.85 g | 5 % |

My reading, for your review: the chips drive it. USDA's fried-from-fresh record gives 1.76 g saturated fat per 100 g, and Wetherspoon's chips are listed at 1.0 g per 100 g (third-party, Fitatu). Over a 200-284 g plate that is about 3.5-5.0 g against 2.0-2.8 g. I did not tune anything to pass the check.

**The ranges you asked for:**

| frying fat | saturated fat | cholesterol |
|---|---|---|
| vegetable oil | 6.9-10.1 g | 64-107 mg |
| beef dripping | 21.9-30.7 g | 109-168 mg |
| whole range (3D: 9.9-22.2 g) | 6.9-30.7 g | 64-168 mg |

Both the fish and the chips take the same fat at each end. The chips follow it through USDA 2709458, whose inputs name the oil, so the "chips cannot follow" fallback did not fire on this dish.

The unlabelled check passing means little: its middle of 18.8 g is the midpoint of two very different plates, a value no real plate has. Also, the vegetable-oil range includes Wetherspoon's small plate (2 g), and the sides differ across the figures.

`runs/flags.jsonl` now has 7 lines: 4 from 3D, the olives closed, and fish and chips open from each pass.

## 7. New rows and reference figures

**W56 tartare sauce:** USDA 171826, 3.333 g saturated fat and 7 mg cholesterol per 100 g, 15-28 g per plate. Sources: Colman's label serving 15 g; USDA Survey 2710173, one tablespoon 14 g and one dipping container 28 g. Labels that judge the record: Colman's 2.1 g, Duerr's 1.6 g per 100 g.

**W57 clinging olive oil:** USDA 171413, 0.3-10.8 g per 100 g of olives, on `snack_bowl` olives. Worked out as (label fat minus the olives' own fat) divided by (100 minus own fat), with own fat 13.11 g, the mean of USDA green and ripe olives.

| label | total fat per 100 g | oil per 100 g of olives |
|---|---|---|
| Pizza Express | 13.4 g | 0.3 g |
| Sainsbury's Taste the Difference | 14.2 g | 1.3 g |
| Marks & Spencer | 21.6 g | 10.8 g |

The low end depends on the own-fat assumption. On a green-olive basis Pizza Express and Sainsbury's show no oil at all; on a ripe basis they show 2.9-3.8 g.

**Reference figures** (`recipes/reference_figures.csv`, where each row has its URL and notes):

| id | card | business | product | basis | sat fat g | total fat g | how it was read |
|---|---|---|---|---|---|---|---|
| F01 | olives | Woolworths (AU) | Green olive half marinated, from the deli | per_100g | 1.8 |  | retail_label; found by web search, 2026-11-05 |
| F02 | olives | Food Snob | Olives, sold by Woolworths NZ | per_100g | 2.0 |  | retail_label; found by web search, 2026-11-05 |
| F03 | olives | Sainsbury's Taste the Difference | Mixed Marinated Olives | per_100g | 1.9 | 14.2 | third_party; opened by the build |
| F04 | olives | Marks & Spencer Deli | Marinated Olive Selection | per_100g | 2.8 | 21.6 | third_party; opened by the build |
| F05 | olives | Pizza Express | Olives Marinate | per_100g | 1.7 | 13.4 | own; opened by the build |
| F06 | olives | Pizza Express | Olives Marinate, one portion (10.7 g fat at 13.4 g per 100 g = 80 g) | per_plate | 1.4 | 10.7 | own; opened by the build |
| F10 | nuts | Ocado | Roasted & salted almonds | per_100g | 3.8 |  | retail_label; search summary only: the page refused or timed out when opened |
| F10p | nuts | Ocado | Roasted & salted almonds, one 25 g serving | per_plate | 1.0 |  | retail_label; search summary only: the page refused or timed out when opened |
| F11 | nuts | Marks & Spencer | Roasted and salted almonds | per_100g | 4.7 |  | retail_label; search summary only: the page refused or timed out when opened |
| F11p | nuts | Marks & Spencer | Roasted and salted almonds, one 30 g serving | per_plate | 1.4 |  | retail_label; search summary only: the page refused or timed out when opened |
| F12 | nuts | Sainsbury's | Unsalted mixed nuts | per_100g | 7.6 |  | retail_label; search summary only: the page refused or timed out when opened |
| F12p | nuts | Sainsbury's | Unsalted mixed nuts, one 30 g serving | per_plate | 2.3 |  | retail_label; search summary only: the page refused or timed out when opened |
| F13 | nuts | Asda | Roasted and salted almonds | per_100g | 4.5 |  | retail_label; search summary only: the page refused or timed out when opened |
| F20 | chips | JD Wetherspoon | Portion of chips (250 g) | per_100g | 1.0 |  | third_party; opened by the build |
| F30 | fish and chips | JD Wetherspoon | Freshly battered fish & chips, haddock fillet & mushy peas | per_plate | 3.8 | 35.7 | third_party; opened by the build |
| F31 | fish and chips | JD Wetherspoon | Freshly battered fish & chips, cod fillet with mushy peas | per_plate | 3.9 | 35.9 | third_party; opened by the build |
| F32 | fish and chips | JD Wetherspoon | Small freshly battered cod and chips with beans | per_plate | 2 | 15 | third_party; opened by the build |
| F33 | fish and chips | Beefeater | Beer-battered haddock & chips, with mushy peas | per_plate | 5.2 | 48.1 | third_party; opened by the build |
| F34 | fish and chips | Sizzling Pubs | Fish and Chips | per_plate | 12 | 54 | third_party; opened by the build |
| F35 | fish and chips | Sizzling Pubs | Cod & Chips, with peas | per_plate | 12 | 49 | third_party; opened by the build |
| F36 | fish and chips | Yates | Freshly battered cod and chips, without peas | per_plate | 13.1 | 48.1 | third_party; opened by the build |
| F37 | fish and chips | Slug & Lettuce | Hand-battered cod and chips, with peas | per_plate | 22.8 | 82 | third_party; opened by the build |
| F38 | fish and chips | Chef & Brewer | Pub Classics, Cod & Chips | per_plate | 35.6 | 92.8 | third_party; opened by the build |
| F39 | fish and chips | Andy's Fish Bar, Stapleford | Fish & Chips, one 300 g serving | per_plate | 10.249 | 42.14 | own; opened by the build |

Independent-owner counts: Yates and Slug & Lettuce count once (Stonegate, confirmed by search). The Mitchells & Butlers, Whitbread and Greene King ownership is general knowledge that I did not verify. The chain figures come mostly through third-party sites; the table says which. Andy's Fish Bar and Pizza Express are the businesses' own. Every row marked as a search summary or web search is a figure the build did not read on the page itself.

## 8. Coverage, USDA and spending

| menu | evaluated 3D / A | ranked 3D / A | unranked 3D / A | flagged 3D / A | model $ 3D / A / B | model calls 3D / A / B |
|---|---|---|---|---|---|---|
| Flour + Water | 12 / 12 | 6 / 6 | 6 / 6 | 0 / 0 | 0.1452 / 0.1208 / 0.0197 | 41 / 43 / 17 |
| The Greyhound | 12 / 13 | 5 / 5 | 9 / 9 | 2 / 1 | 0.1518 / 0.1299 / 0.0473 | 43 / 41 / 18 |
| Zuni Cafe | 13 / 13 | 7 / 7 | 6 / 6 | 0 / 0 | 0.1601 / 0.1388 / 0.0438 | 39 / 37 / 18 |
| Seafood chalkboard | 7 / 7 | 5 / 5 | 2 / 2 | 0 / 0 | 0.0731 / 0.0673 / 0.0288 | 21 / 23 / 13 |

- **Model cost:** pass A is down 17, 14, 13 and 8 %. Total: pass A $0.46, pass B $0.14. The whole day including the tag tests: $0.67 of the $5 cap. No menu came near $0.50.
- **USDA:** pass A 34 requests, pass B 18. Remaining read before each pass: 3,560 and 3,525 of 3,600. After pass B: 3,507. No refusal, no halt.
- **Tavily:** 0 credits in either pass.
- **Flour + Water:** 3 dishes not tried, because of the cap of 14.

## 9. Questionable or unexpected results

1. **Repeatability fell short** (section 4), and it showed that Snapper and Ocean Trout carry a spread of about 9 g from which recipes the search finds.
2. **3D's seafood before/after was partly a full stop**, as was this one (section 3).
3. **Marinades that are eaten get tagged as media** (section 5).
4. **Sicilian Olives at the top of The Greyhound rests on one recipe.** The order is a stated toss-up.
5. **Pan Fried Seabass left the ranking** for want of a "new potatoes" side row. A weights row would bring it back.
6. **Fish and chips on vegetable oil runs above published plates**, and the range between the two fats is very wide. Your wording call on that spread stays open.
7. **Raw-flesh rules are not moisture-corrected.** PR02, PR07 and PR11 use the raw share of 65 without USDA's moisture change, so fried plates like whiting and squid are overstated by about 17 %. Not in 12.9, and fixing it changes those dishes, so I left it.
8. **A D25 cup weight looks wrong:** "1/4 cup thinly sliced Parmesan" gets 60 g from a cottage cheese Survey record on Chicken Schnitzel. It predates 3E and I did not investigate it.
9. **Small faults left as they are:** "cream of tartar" matches the cream row W27; `flags.jsonl` adds a repeat line each run; the pass A report prints "Roli None vs None-None" on the closed olive flag.
10. **Provenance gaps:** the nut figures (PR14) come from search summaries only, and the build never read the Woolworths pages.

## 10. Not built, and decisions for you

**Everything in 12.9 was built.** Not built:

- The 12.5.4 rerun of the four menus against staged USDA answers, carried over from 3D. Staging and promotion exist; that rerun does not. It is corrected in the 3D notes and is not part of 12.9.
- Saving the menu reader's answer: not asked for, and it is your decision below.

**Your decisions:**

1. Save the reader's answer, strip punctuation from queries, or both (section 4).
2. Should a marinade that stays on the food count as eaten (section 5)?
3. The 12 unclear lines, and whether stock and sausage are `plain_food` (section 5).
4. Classify the fish and chips flag: is it the chips' oil (section 6)?
5. Add a "new potatoes" side row (section 9.5)?
6. Apply the moisture correction to the raw-flesh rules (section 9.7)?
7. Still open from 3D: the frying-fat wording for testers, and any new USDA release.

## 11. The tag prompt as run

Version 2e3a82ed51c6, `prompts.py` `LINE_TAGS_PROMPT`:

```
You tag the ingredient lines of published recipes for one restaurant dish. You do not estimate nutrition and you never write a quantity.

Menu item: "{name}" (section: {section}); printed ingredients: {description}.

Recipes (title, then the method sentences that name a fat or liquid when the page has them, then each line number and the line as printed):
{recipes}

For EVERY line give two tags.

role, one of:
- "cooking_medium": ONLY these: a deep-fry bath (the food is submerged in hot oil: "oil for deep-frying", or cups or litres of oil in a recipe that deep-fries),
  a marinade (oil or liquid the food sits in), a brine, a poaching or boiling liquid (water that boils pasta, a court-bouillon), confit fat,
  or oil wiped on a grill grate.
- "removed": lifted out before serving: bay leaves, whole herb sprigs, rinds, bones, shells, aromatics such as a cinnamon stick or star anise.
- "eaten": everything else. Oil or fat used to blister, saute, sear, pan-fry, stir-fry, baste or roast STAYS WITH THE FOOD and is "eaten", whatever the amount.
  Oil in a dressing, a drizzle or a sauce is "eaten". Water or stock inside a soup, stew or risotto is "eaten".
When in doubt the line is "eaten". A line wrongly left out can put a fatty dish at the top of the ranking, which is the harmful error.

kind, one of:
- "plain_food": a single food: an olive, a fish, salt, flour, an oil.
- "prepared_product": a sauce, paste, dressing, condiment, stock cube, spice blend, pesto, salsa, mayonnaise, a bought dough or batter: something made of
  several ingredients.

Write a "reason" of a few words ONLY for a line tagged cooking_medium, removed or prepared_product. For an eaten plain_food line leave the reason out.

Answer with ONE JSON object and nothing else:
{{"recipes": [{{"index": 1, "lines": [{{"n": 1, "role": "eaten", "kind": "plain_food"}}, {{"n": 2, "role": "cooking_medium", "kind": "plain_food", "reason": "frying bath"}}, ...]}}, ...]}}
Include every recipe index and every line number exactly once. Never add nutrition values, weights or quantities.
```

**Stopped here.**
