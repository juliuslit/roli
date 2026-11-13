# MVP before/after

Hand notes, 2026-11-06. Before is 3G pass A; after is 3H pass A on the final code, reader v5.

- Crispy Squid & Prawns' high of 42 g comes from one recipe. "2-3 large squids or 8 large sea prawns" matched shrimp, a same-food record gave 2.5 large shrimp 17.5 g, and that became the recipe's key seafood weight, so one plate is 6.9 whole recipes.
- Bluefin Crudo's high of 11 g comes from one recipe newly bounded: "1 saku tuna" now has a weight of 112.5 g from a same-food record, so a plate takes most of the recipe's 92 g of olive oil.
- Sicilian Olives and Marinated olives left the top three because they are listed apart (12.14.4).
- Zuni Caesar salad and Yellowfin tuna may appear as "absent" and "new" where the reader wrote the footnote mark differently; they are the same dishes.

Before and after: the same photos through the code of each checkpoint.

| menu | run | menu items | candidates | selected | evaluated | ranked | unranked | no recipes | errors | skipped | budget-stopped | flagged | known limit | USDA-unavailable | search credits | model calls | USDA requests | rate-limit waits | USDA left after | model $ | total s | words |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Flour + Water | before 20261106-181416-9ff31a | 19 | 17 | 14 | 12 | 5 | 7 | 2 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 17 | 3 | 0 | 3518 | 0.0196 | 35.4 | 74 |
| Flour + Water | after 20261106-221052-90e28f | 19 | 17 | 14 | 12 | 6 | 6 | 2 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 27 | 13 | 11 | 3478 | 0.0967 | 102.3 | 71 |
| The Greyhound | before 20261106-181452-d3868e | 38 | 15 | 14 | 13 | 6 | 8 | 0 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 11 | 0 | 13 | 3518 | 0.0220 | 61.6 | 72 |
| The Greyhound | after 20261106-221235-39f92e | 38 | 15 | 14 | 13 | 6 | 8 | 0 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 25 | 9 | 23 | 3470 | 0.1141 | 111.4 | 76 |
| Zuni Cafe | before 20261106-181554-0fb09d | 71 | 13 | 13 | 13 | 7 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 13 | 1 | 13 | 3518 | 0.0406 | 83.9 | 72 |
| Zuni Cafe | after 20261106-221426-4145ed | 71 | 13 | 13 | 13 | 8 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 28 | 5 | 30 | 3472 | 0.1219 | 141.5 | 78 |
| Seafood chalkboard | before 20261106-181718-06b914 | 9 | 7 | 7 | 7 | 5 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 13 | 3518 | 0.0057 | 12.8 | 74 |
| Seafood chalkboard | after 20261106-221648-2160ad | 9 | 7 | 7 | 7 | 6 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 16 | 5 | 39 | 3469 | 0.0490 | 57.6 | 74 |

## Flour + Water

**Before:** Among the 5 dishes I could estimate (14 tried; 9 had no usable estimate; 3 not tried), lowest saturated fat first: 1) Heirloom Tomatoes, about 0.8-2.2 g saturated fat per plate; 2) Bluefin Crudo, 0.5-4.3 g; 3) Little Gem Lettuces, 4.4-11 g. Heirloom Tomatoes and Bluefin Crudo overlap, so treat that order as a toss-up. Heirloom Tomatoes has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

**After:** Among the 6 dishes I could estimate (14 tried; 8 had no usable estimate; 3 not tried), lowest saturated fat first: 1) Heirloom Tomatoes, about 0.8-2.2 g saturated fat per plate; 2) Bluefin Crudo, 0.5-11 g; 3) Little Gem Lettuces, 4.4-11 g. These ranges overlap, so treat the order as a toss-up. Heirloom Tomatoes has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | HEIRLOOM TOMATOES: sat 0.8-2.2 g, chol 0-0 mg (close_call) | HEIRLOOM TOMATOES: sat 0.8-2.2 g, chol 0-0 mg (close_call) |
| #2 | BLUEFIN CRUDO: sat 0.5-4.3 g, chol 17-115 mg (close_call, driver bottarga (external evidence)) | BLUEFIN CRUDO: sat 0.5-11.0 g, chol 17-115 mg (close_call, driver bottarga (external evidence)) |
| #3 | LITTLE GEM LETTUCES: sat 4.4-11.3 g, chol 4-125 mg (close_call, driver hard-boiled eggs (assumed amount)) | LITTLE GEM LETTUCES: sat 4.4-11.3 g, chol 4-125 mg (close_call, driver hard-boiled eggs (assumed amount)) |

| dish | before | after | why |
|---|---|---|---|
| BLUEFIN CRUDO | evaluated bounded | evaluated bounded | lines no longer open: ['fresno chile', 'persian cucumber', 'saku tuna or ahi tuna']; different recipes calculated from the same pages (5 before, 4 after, 4 shared): a code change decided which were processed |
| PUTTANESCA | evaluated unbounded | evaluated unbounded | lines no longer open: ['anchovy paste or 6 fillets flat anchovies', 'chili', 'fire roasted diced tomatoes', 'prepared thin crust pizza shell']; different recipes calculated from the same pages (5 before, 4 after, 4 shared): a code change decided which were processed |
| SALSICCIA BIANCA | evaluated unbounded | evaluated bounded | lines no longer open: ['guindilla peppers', 'to 2 cups all-purpose flour']; different recipes calculated from the same pages (6 before, 5 after, 5 shared): a code change decided which were processed |
| MARGHERITA | evaluated unbounded | evaluated unbounded | lines no longer open: ['pizza dough ball', 'semolina flour for the peel']; different recipes calculated from the same pages (5 before, 4 after, 4 shared): a code change decided which were processed |

Unranked after, with reasons:
- POLE BEANS: the estimate has no upper bound: 2 of 2 recipes have no upper bound (notquitenigella.com: miso bagna cauda (missing_grams); cooking.nytimes.com: miso bagna cauda (missing
- PUTTANESCA: the estimate has no upper bound: 4 of 4 recipes have no upper bound (cilantroparsley.com: store bought pizza dough (missing_fdc_id), castelvetrano (missing_grams), boquer
- MARGHERITA: the estimate has no upper bound: 3 of 4 recipes have no upper bound (life-in-the-lofthouse.com: for my best pizza dough (missing_fdc_id); cherrybombe.com: ball neapolitan
- ORECCHIETTE: the estimate has no upper bound: 4 of 4 recipes have no upper bound (bakedbree.com: chanterelle (missing_grams), wasabi (missing_grams); aboutamom.com: chanterelle (missi
- DUCK TRIANGOLI: no recipe of this dish could be portioned (no scenario could be portioned (1 without an applicable portion model))
- PAPPARDELLE: the estimate has no upper bound: 3 of 3 recipes have no upper bound (aflavorjournal.com: lamb merguez ragu (missing_grams), tomato xo (missing_grams); bigdeliciouslife.co

## The Greyhound

**Before:** Among the 6 dishes I could estimate (14 tried; 8 had no usable estimate; 1 not tried), lowest saturated fat first: 1) Sicilian Olives, about 1.0-3.0 g saturated fat per plate; 2) Padron Peppers, 0.6-4.0 g; 3) Crispy Squid & Prawns, 1.5-3.0 g. These ranges overlap, so treat the order as a toss-up. Sicilian Olives has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

**After:** Among the 6 dishes I could estimate (14 tried; 8 had no usable estimate; 1 not tried), lowest saturated fat first: 1) Padron Peppers, about 0.6-4.0 g saturated fat per plate; 2) Pan Fried Seabass, 8.9-23 g; 3) Crispy Squid & Prawns, 1.5-42 g. These ranges overlap, so treat the order as a toss-up. Crispy Squid & Prawns may carry up to 386 mg cholesterol. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | SICILIAN OLIVES: sat 1.0-3.0 g, chol 0-0 mg (close_call) | PADRON PEPPERS: sat 0.6-4.0 g, chol 0-0 mg (close_call) |
| #2 | PADRON PEPPERS: sat 0.6-4.0 g, chol 0-0 mg (close_call) | PAN FRIED SEABASS: sat 8.9-23.0 g, chol 68-158 mg (close_call, driver Seaweed Butter (assumed amount)) |
| #3 | CRISPY SQUID & PRAWNS: sat 1.5-3.0 g, chol 112-225 mg (tentative) | CRISPY SQUID & PRAWNS: sat 1.5-42.3 g, chol 112-386 mg (close_call) |

| dish | before | after | why |
|---|---|---|---|
| ROASTED HARISSA AUBERGINE | evaluated unbounded | evaluated unbounded | lines no longer open: ['-medium aubergine', 'aubergine', 'aubergines', 'chinese or japanese eggplants']; different recipes calculated from the same pages (8 before, 7 after, 7 shared): a code change decided which were processed |
| CHICKEN SCHNITZEL | evaluated bounded | evaluated bounded | lines no longer open: ['boneless skinless chicken breasts', 'double cream', 'fl. oz. heavy whipping cream', 'or two smaller chicken breasts']; different recipes calculated from the same pages (7 before, 6 after, 6 shared): a code change decided which were processed |

Unranked after, with reasons:
- CRACKLING PIG STICKS: no recipe of this dish could be portioned (no scenario could be portioned (3 without an applicable portion model))
- ROASTED HARISSA AUBERGINE: the estimate has no upper bound: 1 of 1 recipes have no upper bound (bbcgoodfood.com: Coconut Yoghurt (missing_fdc_id))
- THE GREYHOUND SCOTCH EGG: the estimate has no upper bound: 2 of 2 recipes have no upper bound (catwillmadeit.com: Burnt Apple Puree (missing_grams), Crackling (missing_grams); greatbritishchefs.co
- CAMEMBERT & SAGE CROQUETTES: no recipe of this dish could be portioned (no scenario could be portioned (3 without an applicable portion model))
- SIRLOIN STEAK 10oz: the estimate has no upper bound: 4 of 4 recipes have no upper bound (cookingwithcurls.com: Koffmann's Hand Cut Chips (missing_grams); lecremedelacrumb.com: Koffmann's Han
- CONISBEE BUTCHER LAMB & MINT SAUSAGES: the estimate has no upper bound: 1 of 1 recipes have no upper bound (cooking.nytimes.com: white beans (preparation_unresolved))
- TAGLIATELLE CARBONARA: the estimate has no upper bound: 4 of 4 recipes have no upper bound (mandytanner.com: Wild Mushroom & Asparagus (missing_grams), frying fat (the recipe fries but list; th
- CORNISH FISH & CHIPS: known limit of the data: USDA has no thick-cut chips record

Flags after:
- known limit: CORNISH FISH & CHIPS (PR15, per_plate (vegetable oil); Roli's middle 8.490 vs published 2-5.2; top contributors: CHIPS: frying fat, Fat, beef tallow 9.19 g (0.51); CORNISH FISH: frying fat, Fat, beef tallow 4.95 g (0.27); vegetable oil 2.27 g (0.12))

Reference checks after:
- SICILIAN OLIVES (PR13): no failing check
  - per_plate: Roli's middle 2.692 vs published 1.4-1.4, 1 independent; shown only
  - per_100g: Roli's middle 3.590 vs published 1.7-2.8, 5 independent; passed
- CORNISH FISH & CHIPS (PR15): flagged
  - per_plate: Roli's middle 18.183 vs published 10.249-22.8, 3 independent; passed
  - per_plate (beef dripping): Roli's middle 26.355 vs published 35.6-35.6, 1 independent; shown only
  - per_plate (vegetable oil): Roli's middle 8.490 vs published 2-5.2, 2 independent; FAILED above

## Zuni Cafe

**Before:** Among the 7 dishes I could estimate (13 tried; 6 had no usable estimate), lowest saturated fat first: 1) Marinated olives, about 0.7-2.6 g saturated fat per plate; 2) Wood fire-roasted tomato and eggplant soup, 0.7-3.9 g; 3) Garden lettuce salad, 0.3-5.4 g. These ranges overlap, so treat the order as a toss-up. Marinated olives has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

**After:** Among the 8 dishes I could estimate (13 tried; 5 had no usable estimate), lowest saturated fat first: 1) Garden lettuce salad, about 1.3-5.4 g saturated fat per plate; 2) Wood fire-roasted tomato and eggplant soup, 1.5-5.6 g; 3) Zuni Caesar salad, 2.0-5.6 g. These ranges overlap, so treat the order as a toss-up. Garden lettuce salad cholesterol about 1-17 mg. Light snack: Marinated olives, 1.3-4.0 g. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | Marinated olives: sat 0.7-2.6 g, chol 0-0 mg (close_call) | Garden lettuce salad with Sungold tomato: sat 1.3-5.4 g, chol 1-17 mg (close_call) |
| #2 | Wood fire-roasted tomato and eggplant so: sat 0.7-3.9 g, chol 2-15 mg (close_call, driver parmesan cheese shavings (assumed amount)) | Wood fire-roasted tomato and eggplant so: sat 1.5-5.6 g, chol 0-19 mg (close_call) |
| #3 | Garden lettuce salad with Sungold tomato: sat 0.3-5.4 g, chol 0-17 mg (close_call) | Zuni Caesar salad: sat 2.0-5.6 g, chol 25-86 mg (close_call) |

| dish | before | after | why |
|---|---|---|---|
| Garden lettuce salad with Sungold tomatoes, A | evaluated bounded | evaluated bounded | lines no longer open: ['-ounce log goat cheese', 'arugula', 'ea yellow squash', 'persian cucumbers']; different recipes calculated from the same pages (8 before, 7 after, 7 shared): a code change decided which were processed |
| Pizza with Wagon Wheel cheese, soppressata, w | evaluated unbounded | evaluated unbounded | lines no longer open: ['calabrian chiles', 'peeled', 'pizza dough ball', 'red onion finely sliced']; different recipes calculated from the same pages (6 before, 5 after, 5 shared): a code change decided which were processed |
| Yellowfin tuna grilled rare all'acqua di mare | evaluated unbounded | evaluated bounded | lines no longer open: ['ahi tuna steaks', 'vegetable oil'] |
| Stemple Creek Ranch ribeye steak (served with | evaluated bounded |  | absent from the after run (menu read differently) |
| Stemple Creek Ranch ribeye steak |  | evaluated bounded | new on the after run (menu read differently or newly selected) |
| Chicken for two roasted in the wood-fired bri | evaluated unbounded | evaluated unbounded | lines no longer open: ['fresh baguette', 'red wine vinegar', 'roasted chicken', 'whole chicken']; grading changed on 6 page(s), e.g. barefootcontessa.com: same/high -> same/high (preparation similar -> same); different recipes calculated (5 before, 4 after, 4 shared): search results or cache, not a code change |

Unranked after, with reasons:
- House-cured anchovies with celery, Parmigiano-Reggiano, and coquillo olives: no recipe of this dish could be portioned (no scenario could be portioned (3 without an applicable portion model))
- Fuyu persimmon and roasted beet "carpaccio" with Laychee goat cheese, tender herbs, and Meyer lemon-pistachio aillade: no recipe of this dish could be portioned (no scenario could be portioned (6 without an applicable portion model))
- Pizza with Wagon Wheel cheese, soppressata, wild nettles, red onion, and Boont Corners sheep cheese: the estimate has no upper bound: 4 of 4 recipes have no upper bound (epicurious.com: purchased fully baked thin pizza crust (missing_fdc_id), drained roasted red pep; lac
- Steak frites: Stemple Creek Ranch bavette steak with pommes frites, Padrón peppers, avocado, and chimichurri: the estimate has no upper bound: 1 of 2 recipes have no upper bound (cooking.nytimes.com: steak-cut frozen fries (preparation_unresolved))
- Chicken for two roasted in the wood-fired brick oven; warm bread salad with scallions, garlic, bitter greens, dried currants, and pine nuts: the estimate has no upper bound: 4 of 4 recipes have no upper bound (fostersmarket.com: salad (missing_grams), toasted pine nuts (preparation_unresolved), a mutual aid ; 

Reference checks after:
- Marinated olives (PR13): no failing check
  - per_plate: Roli's middle 2.647 vs published 1.4-1.4, 1 independent; shown only
  - per_100g: Roli's middle 3.529 vs published 1.7-2.8, 5 independent; passed

## Seafood chalkboard

**Before:** Among the 5 dishes I could estimate (7 tried; 2 had no usable estimate), lowest saturated fat first: 1) Ocean Trout / Tuna Poke Salad, about 0.3-7.0 g saturated fat per plate; 2) Crumbed Whiting, 2.8-5.5 g; 3) Crudo Of Swordfish, 2.5-13 g. These ranges overlap, so treat the order as a toss-up. Ocean Trout / Tuna Poke Salad cholesterol about 18-43 mg. Modeled from published recipes and typical portions, not this kitchen's numbers.

**After:** Among the 6 dishes I could estimate (7 tried; 1 had no usable estimate), lowest saturated fat first: 1) Ocean Trout / Tuna Poke Salad, about 0.3-7.0 g saturated fat per plate; 2) Chilled Mooloolaba Prawns, 2.1-5.4 g; 3) Crumbed Whiting, 2.8-5.5 g. These ranges overlap, so treat the order as a toss-up. Chilled Mooloolaba Prawns is high in cholesterol, about 157-316 mg. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | OCEAN TROUT / TUNA POKE SALAD: sat 0.3-7.0 g, chol 18-43 mg (close_call) | OCEAN TROUT / TUNA POKE SALAD: sat 0.3-7.0 g, chol 18-43 mg (close_call) |
| #2 | CRUMBED WHITING: sat 2.8-5.5 g, chol 85-170 mg (close_call) | CHILLED MOOLOOLABA PRAWNS: sat 2.1-5.4 g, chol 157-316 mg (close_call) |
| #3 | CRUDO OF SWORDFISH: sat 2.5-12.9 g, chol 33-99 mg (close_call) | CRUMBED WHITING: sat 2.8-5.5 g, chol 85-170 mg (close_call) |

| dish | before | after | why |
|---|---|---|---|
| CHILLED MOOLOOLABA PRAWNS | evaluated unbounded | evaluated bounded | lines no longer open: ['kilo cooked tiger prawns', 'purple shallot'] |

Unranked after, with reasons:
- COBIA: the estimate has no upper bound: 1 of 1 recipes have no upper bound (mydeliciousblog.com: toasted pepitas or sunflower seeds (missing_grams))
