# MVP before/after

Hand notes, 2026-11-06. Before is 3F pass A; after is 3G pass A on the final code, reader v5. These are the second 3G pair: the first (`mvp_eval_2026-11-06_3g_first_pass*`) was replaced after its lender list showed four bad lenders. The tags were saved by the first pair, so the "after" cost here is lower than a cold run; `CHECKPOINT_3G.md` section 8 has both.

- Margherita's "why" below is incomplete. The flour lines did not close: a counted salt line passed the near-zero rule, which removed the recipe's only filled gap, so no adapted pair formed and the flour lost its external bound.
- Zuni Caesar salad and Yellowfin tuna appear as "absent" and "new" only because the reader dropped the ‡ mark. They are the same dishes with the same figures.
- Taleggio Scarpinocc and Duck Triangoli swapped because the reader listed the pasta section in a different order, and they tie on lean score at the cap of 14.

Before and after: the same photos through the code of each checkpoint.

| menu | run | menu items | candidates | selected | evaluated | ranked | unranked | no recipes | errors | skipped | budget-stopped | flagged | known limit | USDA-unavailable | search credits | model calls | USDA requests | rate-limit waits | USDA left after | model $ | total s | words |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Flour + Water | before 20261106-144638-f35cef | 19 | 17 | 14 | 12 | 6 | 6 | 2 | 0 | 3 | 0 | 0 |  | 0 | 2 | 30 | 29 | 14 | 3444 | 0.1016 | 114.4 | 74 |
| Flour + Water | after 20261106-181416-9ff31a | 19 | 17 | 14 | 12 | 5 | 7 | 2 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 17 | 3 | 0 | 3518 | 0.0196 | 35.4 | 74 |
| The Greyhound | before 20261106-144833-44b2d8 | 38 | 15 | 14 | 13 | 5 | 9 | 0 | 0 | 1 | 0 | 1 |  | 0 | 10 | 46 | 61 | 32 | 3393 | 0.1478 | 199.6 | 78 |
| The Greyhound | after 20261106-181452-d3868e | 38 | 15 | 14 | 13 | 6 | 8 | 0 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 11 | 0 | 13 | 3518 | 0.0220 | 61.6 | 72 |
| Zuni Cafe | before 20261106-145153-12037e | 71 | 13 | 13 | 12 | 6 | 7 | 0 | 0 | 0 | 0 | 1 |  | 0 | 20 | 59 | 81 | 67 | 3350 | 0.1792 | 290.9 | 65 |
| Zuni Cafe | after 20261106-181554-0fb09d | 71 | 13 | 13 | 13 | 7 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 13 | 1 | 13 | 3518 | 0.0406 | 83.9 | 72 |
| Seafood chalkboard | before 20261106-150714-cfc7cb | 9 | 7 | 7 | 7 | 5 | 2 | 0 | 0 | 0 | 0 | 0 |  | 0 | 2 | 18 | 14 | 67 | 3356 | 0.0521 | 78.9 | 74 |
| Seafood chalkboard | after 20261106-181718-06b914 | 9 | 7 | 7 | 7 | 5 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 13 | 3518 | 0.0057 | 12.8 | 74 |

## Flour + Water

**Before:** Among the 6 dishes I could estimate (14 tried; 8 had no usable estimate; 3 not tried), lowest saturated fat first: 1) Heirloom Tomatoes, about 0.4-2.4 g saturated fat per plate; 2) Bluefin Crudo, 0.5-4.3 g; 3) Little Gem Lettuces, 4.4-11 g. Heirloom Tomatoes and Bluefin Crudo overlap, so treat that order as a toss-up. Heirloom Tomatoes has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

**After:** Among the 5 dishes I could estimate (14 tried; 9 had no usable estimate; 3 not tried), lowest saturated fat first: 1) Heirloom Tomatoes, about 0.8-2.2 g saturated fat per plate; 2) Bluefin Crudo, 0.5-4.3 g; 3) Little Gem Lettuces, 4.4-11 g. Heirloom Tomatoes and Bluefin Crudo overlap, so treat that order as a toss-up. Heirloom Tomatoes has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | HEIRLOOM TOMATOES: sat 0.4-2.4 g, chol 0-0 mg (close_call) | HEIRLOOM TOMATOES: sat 0.8-2.2 g, chol 0-0 mg (close_call) |
| #2 | BLUEFIN CRUDO: sat 0.5-4.3 g, chol 17-115 mg (close_call, driver bottarga (external evidence)) | BLUEFIN CRUDO: sat 0.5-4.3 g, chol 17-115 mg (close_call, driver bottarga (external evidence)) |
| #3 | LITTLE GEM LETTUCES: sat 4.4-11.3 g, chol 4-125 mg (close_call, driver hard-boiled eggs (assumed amount)) | LITTLE GEM LETTUCES: sat 4.4-11.3 g, chol 4-125 mg (close_call, driver hard-boiled eggs (assumed amount)) |

| dish | before | after | why |
|---|---|---|---|
| MARGHERITA | evaluated bounded | evaluated unbounded | lines no longer open: ['semolina and all-purpose flour', 'unbleached all-purpose flour'] |
| TALEGGIO SCARPINOCC | evaluated unbounded | skipped | selection: evaluated -> skipped |
| DUCK TRIANGOLI | skipped | evaluated unbounded | selection: skipped -> evaluated |

Unranked after, with reasons:
- POLE BEANS: the estimate has no upper bound: 1 of 1 recipes have no upper bound (cooking.nytimes.com: miso bagna cauda (missing_grams))
- PUTTANESCA: the estimate has no upper bound: 1 of 1 recipes have no upper bound (foodnetwork.com: castelvetrano (missing_grams), chili (missing_grams), boquerones (missing_grams))
- SALSICCIA BIANCA: no recipe of this dish could be portioned (no scenario could be portioned (6 without an applicable portion model))
- MARGHERITA: the estimate has no upper bound: 4 of 4 recipes have no upper bound (abeautifulplate.com: unbleached all-purpose flour (nutrient_not_reported:saturated_fat_g), semolina a
- ORECCHIETTE: the estimate has no upper bound: 4 of 4 recipes have no upper bound (bakedbree.com: chanterelle (missing_grams), wasabi (missing_grams); aboutamom.com: fresh baby spinach
- DUCK TRIANGOLI: no recipe of this dish could be portioned (no scenario could be portioned (1 without an applicable portion model))
- PAPPARDELLE: the estimate has no upper bound: 3 of 3 recipes have no upper bound (aflavorjournal.com: lamb merguez ragu (missing_grams), tomato xo (missing_grams); bigdeliciouslife.co

## The Greyhound

**Before:** Among the 5 dishes I could estimate (14 tried; 9 had no usable estimate; 1 not tried), lowest saturated fat first: 1) Padron Peppers, about 0.6-4.0 g saturated fat per plate; 2) Crispy Squid & Prawns, 1.5-3.0 g; 3) Pan Fried Seabass, 9.0-23 g. Padron Peppers and Crispy Squid & Prawns overlap, so treat that order as a toss-up. Padron Peppers has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

**After:** Among the 6 dishes I could estimate (14 tried; 8 had no usable estimate; 1 not tried), lowest saturated fat first: 1) Sicilian Olives, about 1.0-3.0 g saturated fat per plate; 2) Padron Peppers, 0.6-4.0 g; 3) Crispy Squid & Prawns, 1.5-3.0 g. These ranges overlap, so treat the order as a toss-up. Sicilian Olives has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | PADRON PEPPERS: sat 0.6-4.0 g, chol 0-0 mg (close_call) | SICILIAN OLIVES: sat 1.0-3.0 g, chol 0-0 mg (close_call) |
| #2 | CRISPY SQUID & PRAWNS: sat 1.5-3.0 g, chol 112-225 mg (tentative) | PADRON PEPPERS: sat 0.6-4.0 g, chol 0-0 mg (close_call) |
| #3 | PAN FRIED SEABASS: sat 9.0-23.1 g, chol 68-158 mg (close_call, driver Seaweed Butter (assumed amount)) | CRISPY SQUID & PRAWNS: sat 1.5-3.0 g, chol 112-225 mg (tentative) |

| dish | before | after | why |
|---|---|---|---|
| SICILIAN OLIVES | evaluated unbounded | evaluated bounded | code fix: new weights row(s) ['W57'] filled lines that were open |

Unranked after, with reasons:
- CRACKLING PIG STICKS: no recipe of this dish could be portioned (no scenario could be portioned (3 without an applicable portion model))
- ROASTED HARISSA AUBERGINE: no recipe of this dish could be portioned (no scenario could be portioned (8 without an applicable portion model))
- THE GREYHOUND SCOTCH EGG: the estimate has no upper bound: 2 of 2 recipes have no upper bound (catwillmadeit.com: canola/vegetable oil (missing_grams), Burnt Apple Puree (missing_grams), Crackli; 
- CAMEMBERT & SAGE CROQUETTES: no recipe of this dish could be portioned (no scenario could be portioned (3 without an applicable portion model))
- SIRLOIN STEAK 10oz: the estimate has no upper bound: 4 of 4 recipes have no upper bound (cookingwithcurls.com: brown sugar (missing_grams), shallot (missing_grams), roasted garlic-goat chees
- CONISBEE BUTCHER LAMB & MINT SAUSAGES: the estimate has no upper bound: 1 of 1 recipes have no upper bound (cooking.nytimes.com: white beans (preparation_unresolved))
- TAGLIATELLE CARBONARA: the estimate has no upper bound: 4 of 4 recipes have no upper bound (mandytanner.com: Wild Mushroom & Asparagus (missing_grams), frying fat (the recipe fries but list; th
- CORNISH FISH & CHIPS: known limit of the data: USDA has no thick-cut chips record

Flags after:
- known limit: CORNISH FISH & CHIPS (PR15, per_plate (vegetable oil); Roli's middle 8.490 vs published 2-5.2; top contributors: CHIPS: frying fat, Vegetable oil, NFS / CHIPS: fry 10.93 g (0.58); CORNISH FISH: frying fat, Vegetable oil, NFS / COR 5.98 g (0.32); Mushy Peas 0.85 g (0.05))

Reference checks after:
- SICILIAN OLIVES (PR13): no failing check
  - per_plate: Roli's middle 2.011 vs published 1.4-1.4, 1 independent; shown only
  - per_100g: Roli's middle 2.681 vs published 1.7-2.8, 5 independent; passed
- CORNISH FISH & CHIPS (PR15): flagged
  - per_plate: Roli's middle 18.827 vs published 10.249-22.8, 3 independent; passed
  - per_plate (beef dripping): Roli's middle 26.355 vs published 35.6-35.6, 1 independent; shown only
  - per_plate (vegetable oil): Roli's middle 8.490 vs published 2-5.2, 2 independent; FAILED above

## Zuni Cafe

**Before:** Among the 6 dishes I could estimate (13 tried; 7 had no usable estimate), lowest saturated fat first: 1) Wood fire-roasted tomato and eggplant soup, about 0.7-3.9 g saturated fat per plate; 2) Garden lettuce salad, 0.3-5.4 g; 3) Zuni Caesar salad, 2.0-5.6 g. These ranges overlap, so treat the order as a toss-up. Modeled from published recipes and typical portions, not this kitchen's numbers.

**After:** Among the 7 dishes I could estimate (13 tried; 6 had no usable estimate), lowest saturated fat first: 1) Marinated olives, about 0.7-2.6 g saturated fat per plate; 2) Wood fire-roasted tomato and eggplant soup, 0.7-3.9 g; 3) Garden lettuce salad, 0.3-5.4 g. These ranges overlap, so treat the order as a toss-up. Marinated olives has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | Wood fire-roasted tomato and eggplant so: sat 0.7-3.9 g, chol 2-15 mg (close_call, driver parmesan cheese shavings (assumed amount)) | Marinated olives: sat 0.7-2.6 g, chol 0-0 mg (close_call) |
| #2 | Garden lettuce salad with Sungold tomato: sat 0.3-5.4 g, chol 0-17 mg (close_call) | Wood fire-roasted tomato and eggplant so: sat 0.7-3.9 g, chol 2-15 mg (close_call, driver parmesan cheese shavings (assumed amount)) |
| #3 | Zuni Caesar salad‡: sat 2.0-5.6 g, chol 25-95 mg (close_call, driver very fresh large eggs (assumed amount)) | Garden lettuce salad with Sungold tomato: sat 0.3-5.4 g, chol 0-17 mg (close_call) |

| dish | before | after | why |
|---|---|---|---|
| Marinated olives | flagged bounded | evaluated bounded | reference check: flagged -> evaluated; code fix: new weights row(s) ['W57'] filled lines that were open |
| Zuni Caesar salad |  | evaluated bounded | new on the after run (menu read differently or newly selected) |
| Zuni Caesar salad‡ | evaluated bounded |  | absent from the after run (menu read differently) |
| Yellowfin tuna‡ grilled rare all'acqua di mar | evaluated unbounded |  | absent from the after run (menu read differently) |
| Yellowfin tuna grilled rare all'acqua di mare |  | evaluated unbounded | new on the after run (menu read differently or newly selected) |

Unranked after, with reasons:
- House-cured anchovies with celery, Parmigiano-Reggiano, and coquillo olives: no recipe of this dish could be portioned (no scenario could be portioned (3 without an applicable portion model))
- Fuyu persimmon and roasted beet "carpaccio" with Laychee goat cheese, tender herbs, and Meyer lemon-pistachio aillade: no recipe of this dish could be portioned (no scenario could be portioned (6 without an applicable portion model))
- Pizza with Wagon Wheel cheese, soppressata, wild nettles, red onion, and Boont Corners sheep cheese: the estimate has no upper bound: 1 of 1 recipes have no upper bound (epicurious.com: unbleached all-purpose flour (missing_grams), cornmeal for sprinkling the baking)
- Yellowfin tuna grilled rare all'acqua di mare with Manila clams, mussels, sprouting cauliflower, string beans, a slow-cooked Early Girl tomato, and aïoli: the estimate has no upper bound: 1 of 1 recipes have no upper bound (cooking.nytimes.com: whole (missing_grams), red onion (nutrient_not_reported:saturated_fat_g))
- Steak frites: Stemple Creek Ranch bavette steak with pommes frites, Padrón peppers, avocado, and chimichurri: the estimate has no upper bound: 1 of 2 recipes have no upper bound (cooking.nytimes.com: steak-cut frozen fries (preparation_unresolved))
- Chicken for two roasted in the wood-fired brick oven; warm bread salad with scallions, garlic, bitter greens, dried currants, and pine nuts: the estimate has no upper bound: 3 of 3 recipes have no upper bound (fostersmarket.com: salad (missing_grams), toasted pine nuts (preparation_unresolved), a mutual aid ; 

Reference checks after:
- Marinated olives (PR13): no failing check
  - per_plate: Roli's middle 1.653 vs published 1.4-1.4, 1 independent; shown only
  - per_100g: Roli's middle 2.204 vs published 1.7-2.8, 5 independent; passed

## Seafood chalkboard

**Before:** Among the 5 dishes I could estimate (7 tried; 2 had no usable estimate), lowest saturated fat first: 1) Ocean Trout / Tuna Poke Salad, about 0.3-7.0 g saturated fat per plate; 2) Crumbed Whiting, 2.8-5.5 g; 3) Crudo Of Swordfish, 2.5-13 g. These ranges overlap, so treat the order as a toss-up. Ocean Trout / Tuna Poke Salad cholesterol about 18-43 mg. Modeled from published recipes and typical portions, not this kitchen's numbers.

**After:** Among the 5 dishes I could estimate (7 tried; 2 had no usable estimate), lowest saturated fat first: 1) Ocean Trout / Tuna Poke Salad, about 0.3-7.0 g saturated fat per plate; 2) Crumbed Whiting, 2.8-5.5 g; 3) Crudo Of Swordfish, 2.5-13 g. These ranges overlap, so treat the order as a toss-up. Ocean Trout / Tuna Poke Salad cholesterol about 18-43 mg. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | OCEAN TROUT / TUNA POKE SALAD: sat 0.3-7.0 g, chol 18-43 mg (close_call) | OCEAN TROUT / TUNA POKE SALAD: sat 0.3-7.0 g, chol 18-43 mg (close_call) |
| #2 | CRUMBED WHITING: sat 2.8-5.5 g, chol 85-170 mg (close_call) | CRUMBED WHITING: sat 2.8-5.5 g, chol 85-170 mg (close_call) |
| #3 | CRUDO OF SWORDFISH: sat 2.5-12.9 g, chol 33-99 mg (close_call) | CRUDO OF SWORDFISH: sat 2.5-12.9 g, chol 33-99 mg (close_call) |

| dish | before | after | why |
|---|---|---|---|
| SNAPPER | evaluated bounded | evaluated bounded | lines no longer open: ['yellow tail snapper filets )']; different recipes calculated from the same pages (5 before, 4 after, 4 shared): a code change decided which were processed |

Unranked after, with reasons:
- CHILLED MOOLOOLABA PRAWNS: no recipe of this dish could be portioned (no scenario could be portioned (2 without an applicable portion model))
- COBIA: the estimate has no upper bound: 1 of 1 recipes have no upper bound (mydeliciousblog.com: toasted pepitas or sunflower seeds (missing_grams))
