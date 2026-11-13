# Phase 2D controlled run (experimental pairs feed the comparison)

## Published scenarios: completeness basis, inferences

| dish | scenario | 2A status | completeness basis (sat / chol) | inferences | blockers |
|---|---|---|---|---|---|
| bluefin_crudo | foodmymuse.com:spicy-tuna-crudo-with-shoyu-ponzu | incomplete | incomplete / incomplete | median:carrot, median:scallions, median:orange, median:lemon | {'unknown_quantity': 2, 'menu_only': 3} |
| bluefin_crudo | coleycooks.com:sicilian-tuna-crudo-with-olives-a | incomplete | incomplete / incomplete | median:lemon, nutrient:extra virgin olive | {'nutrient_not_reported': 1, 'seasoning_unknown_quantity': 1, 'proxy_portion_refused': 1, 'no_usda_portion': 1, 'menu_only': 3} |
| bluefin_crudo | jamesbeard.org:tuna-crudo-james-beard-foundation | incomplete | incomplete / incomplete | nutrient:extra virgin olive | {'nutrient_not_reported': 1, 'seasoning_unknown_quantity': 2, 'no_usda_portion': 1, 'menu_only': 3} |
| bluefin_crudo | twopurplefigs.com:tuna-crudo | incomplete | incomplete / incomplete | - | {'no_usda_portion': 1, 'nutrient_not_reported': 1, 'unresolved_usda': 1, 'menu_only': 3} |
| little_gem_lettuces | pinchandswirl.com:little-gem-salad | incomplete | incomplete / incomplete | nutrient:extra virgin olive | {'proxy_portion_refused': 1, 'nutrient_not_reported': 2, 'seasoning_unknown_quantity': 1, 'menu_only': 3} |
| little_gem_lettuces | cravingcalifornia.com:little-gem-wedge-salad-wit | incomplete | incomplete / incomplete | median:hard-boiled eggs, median:radishes | {'no_usda_portion': 2, 'nutrient_not_reported': 2, 'seasoning_unknown_quantity': 1, 'proxy_portion_refused': 1, 'menu_only': 3} |
| little_gem_lettuces | cooking.nytimes.com:baked-goat-cheese-with-garde | incomplete | incomplete / incomplete | nutrient:extra-virgin olive | {'nutrient_not_reported': 3, 'no_usda_portion': 3, 'seasoning_unknown_quantity': 2, 'menu_only': 3} |
| heirloom_tomatoes | thesophisticatedcaveman.com:heirloom-tomato-sala | incomplete | incomplete / incomplete | nutrient:extra virgin olive | {'nutrient_not_reported': 2, 'no_usda_portion': 2, 'menu_only': 3} |
| heirloom_tomatoes | cooking.nytimes.com:pluot-tomato-salad-with-suya | incomplete | incomplete / incomplete | nutrient:extra-virgin olive, nutrient:extra-virgin olive | {'no_usda_portion': 3, 'nutrient_not_reported': 2, 'proxy_portion_refused': 2, 'unknown_quantity': 2, 'seasoning_unknown_quantity': 2, 'menu_only': 2} |
| heirloom_tomatoes | cooking.nytimes.com:chamoy-tomato-salad | incomplete | incomplete / incomplete | - | {'seasoning_unknown_quantity': 1, 'no_usda_portion': 2, 'proxy_portion_refused': 1, 'nutrient_not_reported': 1, 'menu_only': 4} |
| margherita | kingarthurbaking.com:margherita-pizza | incomplete | incomplete / incomplete | nutrient:extra-virgin olive | {'nutrient_not_reported': 3, 'unknown_quantity': 1} |
| margherita | abeautifulplate.com:best-homemade-margherita-piz | incomplete | incomplete / incomplete | nutrient:extra virgin olive, nutrient:extra virgin olive | {'nutrient_not_reported': 2, 'unknown_quantity': 1, 'proxy_portion_refused': 1, 'seasoning_unknown_quantity': 1} |
| margherita | foodnetwork.com:margherita-pizza | incomplete | incomplete / incomplete | nutrient:extra-virgin olive, nutrient:extra-virgin olive | {'nutrient_not_reported': 2, 'seasoning_unknown_quantity': 1, 'no_usda_portion': 1} |
| margherita | tasteofhome.com:margherita-pizza | incomplete | incomplete / incomplete | nutrient:extra virgin olive, nutrient:extra virgin olive | {'nutrient_not_reported': 2, 'no_usda_portion': 1} |
| king_salmon | thishealthytable.com:baked-king-salmon | incomplete | incomplete / incomplete | - | {'optional_unknown_quantity': 1, 'menu_only': 4} |
| king_salmon | lecremedelacrumb.com:best-easy-healthy-baked-sal | incomplete | incomplete / incomplete | median:lemon | {'no_usda_portion': 1, 'menu_only': 3} |
| king_salmon | mylatinatable.com:crispy-skin-salmon-with-lemon- | incomplete | incomplete / incomplete | - | {'no_usda_portion': 1, 'menu_only': 4} |
| king_salmon | foodnetwork.com:pan-seared-wild-pacific-king-sal | incomplete | incomplete / incomplete | nutrient:extra-virgin olive | {'unresolved_usda': 1, 'proxy_portion_refused': 1, 'unknown_quantity': 1, 'no_usda_portion': 3, 'nutrient_not_reported': 2, 'menu_only': 3} |

## Adapted pairs (experimental): completeness at both bounds, with inferences

| dish | scenario | low | high | low+inf | high+inf | unfilled (high) |
|---|---|---|---|---|---|---|
| bluefin_crudo | foodmymuse.com:spicy-tuna-crudo-with-shoyu-ponzu | incomplete | incomplete | incomplete | incomplete | bottarga (blocked_row) |
| bluefin_crudo | coleycooks.com:sicilian-tuna-crudo-with-olives-a | incomplete | incomplete | incomplete | incomplete | extra virgin olive o (nutrient_missing_on_record), castelvetrano olives (ambiguous_or_missing_measure), bottarga (blocke |
| bluefin_crudo | jamesbeard.org:tuna-crudo-james-beard-foundation | incomplete | incomplete | incomplete | incomplete | extra virgin olive o (nutrient_missing_on_record), chopped jarred hot i (ambiguous_or_missing_measure), bottarga (blocke |
| bluefin_crudo | twopurplefigs.com:tuna-crudo | incomplete | incomplete | incomplete | incomplete | saku tuna or ahi tun (ambiguous_or_missing_measure), white balsamic vineg (nutrient_missing_on_record), garlic (no_usda_ |
| little_gem_lettuces | pinchandswirl.com:little-gem-salad | incomplete | incomplete | incomplete | incomplete | champagne vinegar (nutrient_missing_on_record), extra virgin olive o (nutrient_missing_on_record) |
| little_gem_lettuces | cravingcalifornia.com:little-gem-wedge-salad-wit | incomplete | incomplete | incomplete | incomplete | whole milk greek yog (ambiguous_or_missing_measure), white wine vinegar (nutrient_missing_on_record), red onion (nutrien |
| little_gem_lettuces | cooking.nytimes.com:baked-goat-cheese-with-garde | incomplete | incomplete | incomplete | incomplete | extra-virgin olive o (nutrient_missing_on_record), fresh thyme (ambiguous_or_missing_measure), sprig rosemary (ambiguous |
| heirloom_tomatoes | thesophisticatedcaveman.com:heirloom-tomato-sala | incomplete | incomplete | incomplete | incomplete | extra virgin olive o (nutrient_missing_on_record), white balsamic vineg (nutrient_missing_on_record), red onion (ambiguo |
| heirloom_tomatoes | cooking.nytimes.com:pluot-tomato-salad-with-suya | incomplete | incomplete | incomplete | incomplete | extra-virgin olive o (nutrient_missing_on_record), plain full-fat greek (ambiguous_or_missing_measure), extra-virgin oli |
| heirloom_tomatoes | cooking.nytimes.com:chamoy-tomato-salad | incomplete | incomplete | incomplete | incomplete | tamarind concentrate (ambiguous_or_missing_measure), chipotle chile in ad (no_table_row), red onion (nutrient_missing_on |
| margherita | kingarthurbaking.com:margherita-pizza | incomplete | incomplete | incomplete | incomplete | whole (nutrient_missing_on_record), extra-virgin olive o (nutrient_missing_on_record), king arthur ‘00’ piz (nutrient_mi |
| margherita | abeautifulplate.com:best-homemade-margherita-piz | incomplete | incomplete | incomplete | incomplete | extra virgin olive o (nutrient_missing_on_record), semolina and all-pur (no_table_row), extra virgin olive o (nutrient_m |
| margherita | foodnetwork.com:margherita-pizza | incomplete | incomplete | incomplete | incomplete | extra-virgin olive o (nutrient_missing_on_record), fresh basil leaves (ambiguous_or_missing_measure), extra-virgin olive |
| margherita | tasteofhome.com:margherita-pizza | incomplete | incomplete | complete | complete | extra virgin olive o (nutrient_missing_on_record), extra virgin olive o (nutrient_missing_on_record) |
| king_salmon | thishealthytable.com:baked-king-salmon | incomplete | incomplete | incomplete | incomplete | optional toppings (no_table_row) |
| king_salmon | lecremedelacrumb.com:best-easy-healthy-baked-sal | complete | complete | complete | complete | - |
| king_salmon | mylatinatable.com:crispy-skin-salmon-with-lemon- | complete | complete | complete | complete | - |
| king_salmon | foodnetwork.com:pan-seared-wild-pacific-king-sal | incomplete | incomplete | incomplete | incomplete | milk (no_usda_record), fresh lemon thyme (no_table_row), yellow pattypan squa (ambiguous_or_missing_measure), extra-virg |

## Portion models (experimental pairs)

| dish | scenario | model / rule | applicable | f low-high | sat fat per portion low-high (+inf) | chol per portion low-high (+inf) | recipe basis per serving (sat known) | reason / limits |
|---|---|---|---|---|---|---|---|---|
| bluefin_crudo | foodmymuse.com:spicy-tuna-crudo-with-sho | P3 PR03 | yes | 0.227-0.554 | 1.45-3.91 (---) | 17-42 (---) | 2.43-3.71 / 2 servings | P3 scales every recipe line by the fish ratio: sauces, dressings and s |
| bluefin_crudo | coleycooks.com:sicilian-tuna-crudo-with- | P3 PR03 | yes | 0.198-0.485 | 1.50-3.68 (---) | 17-42 (---) | 1.88-1.91 / 4 servings | P3 scales every recipe line by the fish ratio: sauces, dressings and s |
| bluefin_crudo | jamesbeard.org:tuna-crudo-james-beard-fo | P3 PR03 | yes | 0.198-0.485 | 0.51-1.27 (---) | 18-43 (---) | 0.64-0.68 / 4 servings | P3 scales every recipe line by the fish ratio: sauces, dressings and s |
| bluefin_crudo | twopurplefigs.com:tuna-crudo | P3 | no | - | - | - | - | PR03: P3 not applicable: the recipe's fish weight is unknown (saku tuna or ahi tuna) |
| little_gem_lettuces | pinchandswirl.com:little-gem-salad | P2 PR04 | yes | 0.197-0.289 | 4.64-8.95 (4.64-8.95) | 4-13 (---) | 5.32-8.44 / 4 servings | served mass = the recipe's raw ingredient mass (yield option 2: no coo |
| little_gem_lettuces | cravingcalifornia.com:little-gem-wedge-s | P2 | no | - | - | - | - | PR04: P2 not applicable: the recipe's served mass is incomplete (1 unweighed: whole milk greek yogurt); a partial mass w |
| little_gem_lettuces | cooking.nytimes.com:baked-goat-cheese-wi | P2 | no | - | - | - | - | PR04: P2 not applicable: the recipe's served mass is incomplete (3 unweighed: fresh thyme, sprig rosemary, of a sour bag |
| heirloom_tomatoes | thesophisticatedcaveman.com:heirloom-tom | P3 PR06 | yes | 0.0996-0.207 | 1.01-2.12 (---) | 0-0 (---) | 1.59-1.77 / 6 servings | P3 scales every recipe line by the tomatoes ratio: sauces, dressings a |
| heirloom_tomatoes | cooking.nytimes.com:pluot-tomato-salad-w | P3 | no | - | - | - | - | PR06: P3 not applicable: the recipe's tomatoes weight is unknown (heirloom tomatoes); PR05: P2 not applicable: the recip |
| heirloom_tomatoes | cooking.nytimes.com:chamoy-tomato-salad | P3 PR06 | yes | 0.176-0.367 | 0.82-1.72 (---) | 0-0 (---) | 0.78-0.96 / 6 servings | P3 scales every recipe line by the tomatoes ratio: sauces, dressings a |
| margherita | kingarthurbaking.com:margherita-pizza | P1 PR01 | yes | 0.25-0.5 | 5.41-10.82 (---) | 22-45 (---) | 1.80-1.81 / 12 servings | recipe pizza size not stated on the page: no size adjustment between t |
| margherita | abeautifulplate.com:best-homemade-marghe | P1 PR01 | yes | 0.360-0.845 | 11.84-27.82 (---) | 60-142 (---) | 8.23-8.27 / 4 servings | recipe pizza 10 in; restaurant pie assumed 12-13 in (rule PR01); scale |
| margherita | foodnetwork.com:margherita-pizza | P1 | no | - | - | - | - | PR01: P1 not applicable: the recipe reserves part of the dough for another use, so the ingredient list does not describe |
| margherita | tasteofhome.com:margherita-pizza | P1 PR01 | yes | 0.426-1 | 11.35-26.65 (11.35-26.65) | 38-90 (38-90) | 4.44-4.44 / 6 servings | recipe pizza 13 in; restaurant pie assumed 12-13 in (rule PR01); scale |
| king_salmon | thishealthytable.com:baked-king-salmon | P3 PR02 | yes | 0.166-0.334 | 7.43-14.88 (---) | 72-144 (---) | 11.01-11.31 / 4 servings | P3 scales every recipe line by the fish ratio: sauces, dressings and s |
| king_salmon | lecremedelacrumb.com:best-easy-healthy-b | P3 PR02 | yes | 0.166-0.334 | 4.47-8.95 (4.47-8.95) | 56-114 (56-114) | 6.56-6.87 / 4 servings | P3 scales every recipe line by the fish ratio: sauces, dressings and s |
| king_salmon | mylatinatable.com:crispy-skin-salmon-wit | P3 PR02 | yes | 0.249-0.500 | 5.21-10.44 (5.21-10.44) | 77-155 (77-155) | 5.23-5.54 / 4 servings | P3 scales every recipe line by the fish ratio: sauces, dressings and s |
| king_salmon | foodnetwork.com:pan-seared-wild-pacific- | P3 PR02 | yes | 0.125-0.250 | 5.79-12.25 (---) | 61-123 (---) | 7.46-8.95 / 6 servings | P3 scales every recipe line by the fish ratio: sauces, dressings and s |

## Dish intervals per restaurant portion: saturated_fat_g

| dish | low | high | bounded | recipes (bounded) | tiers | caveats |
|---|---|---|---|---|---|---|
| bluefin_crudo | 0.51 | 4.29 | True | 3 (3) | {'modeled_range_external_bound': 3} | 1 calculated recipe(s) had no applicable portion model and are not in this interval / the upper bound includes external evidence bounds for lines no USDA record could calculate (labelled per scenario; |
| little_gem_lettuces | 4.64 | 8.95 | True | 1 (1) | {'modeled_range_complete': 1} | 2 calculated recipe(s) had no applicable portion model and are not in this interval / assumption-driven: assumed lines exceed 30 % of a known subtotal in 1 of 1 recipes / no recipe is complete from so |
| heirloom_tomatoes | 0.82 | 2.23 | True | 2 (2) | {'modeled_range_external_bound': 2} | 1 calculated recipe(s) had no applicable portion model and are not in this interval / the upper bound includes external evidence bounds for lines no USDA record could calculate (labelled per scenario; |
| margherita | 5.41 | 27.85 | True | 3 (3) | {'modeled_range_external_bound': 2, 'modeled_range_complete': 1} | 1 calculated recipe(s) had no applicable portion model and are not in this interval / the upper bound includes external evidence bounds for lines no USDA record could calculate (labelled per scenario; |
| king_salmon | 4.47 | 14.89 | True | 4 (4) | {'modeled_range_external_bound': 2, 'modeled_range_complete': 2} | the upper bound includes external evidence bounds for lines no USDA record could calculate (labelled per scenario; never inside a total) / no recipe is complete from source-stated weights alone: every |

## Dish intervals per restaurant portion: cholesterol_mg

| dish | low | high | bounded | recipes (bounded) | tiers | caveats |
|---|---|---|---|---|---|---|
| bluefin_crudo | 17.10 | 115.10 | True | 3 (3) | {'modeled_range_external_bound': 3} | 1 calculated recipe(s) had no applicable portion model and are not in this interval / the upper bound includes external evidence bounds for lines no USDA record could calculate (labelled per scenario; |
| little_gem_lettuces | 4.30 | 12.90 | True | 1 (1) | {'modeled_range_external_bound': 1} | 2 calculated recipe(s) had no applicable portion model and are not in this interval / the upper bound includes external evidence bounds for lines no USDA record could calculate (labelled per scenario; |
| heirloom_tomatoes | 0.00 | 0.00 | True | 2 (2) | {'modeled_range_external_bound': 2} | 1 calculated recipe(s) had no applicable portion model and are not in this interval / the upper bound includes external evidence bounds for lines no USDA record could calculate (labelled per scenario; |
| margherita | 22.40 | 141.56 | True | 3 (3) | {'modeled_range_external_bound': 2, 'modeled_range_complete': 1} | 1 calculated recipe(s) had no applicable portion model and are not in this interval / the upper bound includes external evidence bounds for lines no USDA record could calculate (labelled per scenario; |
| king_salmon | 56.50 | 154.54 | True | 4 (4) | {'modeled_range_external_bound': 2, 'modeled_range_complete': 2} | the upper bound includes external evidence bounds for lines no USDA record could calculate (labelled per scenario; never inside a total) / no recipe is complete from source-stated weights alone: every |

## Pairwise verdicts

| nutrient | A | B | verdict | lower | reason |
|---|---|---|---|---|---|
| saturated_fat_g | bluefin_crudo | heirloom_tomatoes | overlapping | - | bluefin_crudo 0.507-4.29 g overlaps heirloom_tomatoes 0.819-2.23 g |
| saturated_fat_g | bluefin_crudo | king_salmon | clear | bluefin_crudo | bluefin_crudo at most 4.29 g per portion; king_salmon at least 4.47 g |
| saturated_fat_g | bluefin_crudo | little_gem_lettuces | clear | bluefin_crudo | bluefin_crudo at most 4.29 g per portion; little_gem_lettuces at least 4.64 g |
| saturated_fat_g | bluefin_crudo | margherita | clear | bluefin_crudo | bluefin_crudo at most 4.29 g per portion; margherita at least 5.41 g |
| saturated_fat_g | heirloom_tomatoes | king_salmon | clear | heirloom_tomatoes | heirloom_tomatoes at most 2.23 g per portion; king_salmon at least 4.47 g |
| saturated_fat_g | heirloom_tomatoes | little_gem_lettuces | clear | heirloom_tomatoes | heirloom_tomatoes at most 2.23 g per portion; little_gem_lettuces at least 4.64 g |
| saturated_fat_g | heirloom_tomatoes | margherita | clear | heirloom_tomatoes | heirloom_tomatoes at most 2.23 g per portion; margherita at least 5.41 g |
| saturated_fat_g | king_salmon | little_gem_lettuces | overlapping | - | king_salmon 4.47-14.9 g overlaps little_gem_lettuces 4.64-8.95 g |
| saturated_fat_g | king_salmon | margherita | overlapping | - | king_salmon 4.47-14.9 g overlaps margherita 5.41-27.8 g |
| saturated_fat_g | little_gem_lettuces | margherita | overlapping | - | little_gem_lettuces 4.64-8.95 g overlaps margherita 5.41-27.8 g |
| cholesterol_mg | bluefin_crudo | heirloom_tomatoes | clear | heirloom_tomatoes | heirloom_tomatoes at most 0 mg per portion; bluefin_crudo at least 17.1 mg |
| cholesterol_mg | bluefin_crudo | king_salmon | overlapping | - | bluefin_crudo 17.1-115 mg overlaps king_salmon 56.5-155 mg |
| cholesterol_mg | bluefin_crudo | little_gem_lettuces | clear | little_gem_lettuces | little_gem_lettuces at most 12.9 mg per portion; bluefin_crudo at least 17.1 mg |
| cholesterol_mg | bluefin_crudo | margherita | overlapping | - | bluefin_crudo 17.1-115 mg overlaps margherita 22.4-142 mg |
| cholesterol_mg | heirloom_tomatoes | king_salmon | clear | heirloom_tomatoes | heirloom_tomatoes at most 0 mg per portion; king_salmon at least 56.5 mg |
| cholesterol_mg | heirloom_tomatoes | little_gem_lettuces | clear | heirloom_tomatoes | heirloom_tomatoes at most 0 mg per portion; little_gem_lettuces at least 4.3 mg |
| cholesterol_mg | heirloom_tomatoes | margherita | clear | heirloom_tomatoes | heirloom_tomatoes at most 0 mg per portion; margherita at least 22.4 mg |
| cholesterol_mg | king_salmon | little_gem_lettuces | clear | little_gem_lettuces | little_gem_lettuces at most 12.9 mg per portion; king_salmon at least 56.5 mg |
| cholesterol_mg | king_salmon | margherita | overlapping | - | king_salmon 56.5-155 mg overlaps margherita 22.4-142 mg |
| cholesterol_mg | little_gem_lettuces | margherita | clear | little_gem_lettuces | little_gem_lettuces at most 12.9 mg per portion; margherita at least 22.4 mg |

## Drivers (highest bounded recipe per dish, saturated fat)

- **bluefin_crudo**: foodmymuse.com: portion P3 rule PR03: f = 0.227-0.554 (K / K_recipe = 110 g / 198.446661875 g) | foodmymuse.com: assumed olive oil: 13.5 g -> 1.86 per portion at the high bound (G2_unquantified, table_row, W09, high): 13.5 g per ) | foodmymuse.com: assumed muscat grape: 49 g -> 0.0265 per portion at the high bound (G1_menu_only, table_row, W11, high): 49 g per plate) | foodmymuse.com: assumed lemon: 84 g -> 0.0182 per portion at the high bound (G3_size_unspecified, record_size_labels, high): 84 )
- **little_gem_lettuces**: pinchandswirl.com: portion P2 rule PR04: f = 0.197-0.289 (W / M_served = 250 g / 866.383289731 g) | pinchandswirl.com: assumed pecorino sardo: 15 g -> 2.31 per portion at the high bound (G1_menu_only, table_row, W05, high): 15 g per plate) | pinchandswirl.com: assumed tahini vinaigrette: 30 g -> 2.23 per portion at the high bound (G1_menu_only, table_row, W08, high): 30 g per plate) | pinchandswirl.com: assumed toasted sesame: 9 g -> 0.605 per portion at the high bound (G1_menu_only, table_row, W07, high): 9 g per plate;)
- **heirloom_tomatoes**: thesophisticatedcaveman.com: portion P3 rule PR06: f = 0.0996-0.207 (K / K_recipe = 250 g / 1205.18474 g) | thesophisticatedcaveman.com: assumed sourdough: 60 g -> 0.317 per portion at the high bound (G1_menu_only, table_row, W17, high): 60 g per plate) | thesophisticatedcaveman.com: assumed pluot: 66 g -> 0.0112 per portion at the high bound (G1_menu_only, table_row, W21, high): 66 g per plate) | thesophisticatedcaveman.com: assumed shiso: 3 g -> 0.00123 per portion at the high bound (G1_menu_only, table_row, W03c, high): 3 g per plate)
- **margherita**: abeautifulplate.com: portion P1 rule PR01: f = 0.360-0.845 (units_per_portion x area_ratio / k = 1 x 1.69 / 2) | abeautifulplate.com: assumed dried red pepper flakes: 1.8 g -> 0.0587 per portion at the high bound (G2_unquantified, table_row, W16, high): 1.8 g per p) | abeautifulplate.com: external upper bound +0.0262 from 1 line(s) (non-USDA evidence, labelled)
- **king_salmon**: thishealthytable.com: portion P3 rule PR02: f = 0.166-0.334 (K / K_recipe = 227 g / 680.388555 g) | thishealthytable.com: assumed corn: 145 g -> 0.471 per portion at the high bound (G1_menu_only, table_row, W18, high): 145 g per plat) | thishealthytable.com: assumed squash: 196 g -> 0.165 per portion at the high bound (G1_menu_only, table_row, W19, high): 196 g per plat) | thishealthytable.com: assumed shishito: 55 g -> 0.0116 per portion at the high bound (G1_menu_only, table_row, W20b, high): 55 g per plat)

Statement: INTERNAL 2D prototype: saturated fat decides 6 of 10 dish pairs clearly; 5 dishes have an upper bound, 0 do not (none). Dishes without an upper bound are never ranked; cholesterol is reported as the secondary criterion. Modeled restaurant portions from unreviewed rule rows; not verified restaurant values; not for users.

Timing (s): {"bluefin_crudo": {"build_scenarios": 27.41, "adapt_both_modes": 0.03, "portion": 0.02, "intervals": 0.071}, "little_gem_lettuces": {"build_scenarios": 18.2, "adapt_both_modes": 0.49, "portion": 0.0, "intervals": 0.001}, "heirloom_tomatoes": {"build_scenarios": 13.08, "adapt_both_modes": 0.25, "portion": 0.01, "intervals": 0.004}, "margherita": {"build_scenarios": 8.38, "adapt_both_modes": 0.02, "portion": 0.01, "intervals": 0.002}, "king_salmon": {"build_scenarios": 12.07, "adapt_both_modes": 0.03, "portion": 0.01, "intervals": 0.004}, "compare_dishes": 0.001, "total": 80.1}
