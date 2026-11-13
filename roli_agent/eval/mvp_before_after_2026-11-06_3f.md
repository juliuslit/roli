# MVP before/after: 3E pass A against 3F pass A

Before: the 3E pass A runs. After: 3F pass A on the final code, with a fresh reading. Cleaned search queries changed which pages some dishes read, so a change marked 'search results or cache' can come from 12.10.4.

| menu | run | menu items | candidates | selected | evaluated | ranked | unranked | no recipes | errors | skipped | budget-stopped | flagged | USDA-unavailable | search credits | model calls | USDA requests | rate-limit waits | USDA left after | model $ | total s | words |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Flour + Water | before 20261106-134104-7e4cd4 | 19 | 17 | 14 | 12 | 6 | 6 | 2 | 0 | 3 | 0 | 0 | 0 | 0 | 43 | 3 | 28 | 3557 | 0.1208 | 168.2 | 74 |
| Flour + Water | after 20261106-144638-f35cef | 19 | 17 | 14 | 12 | 6 | 6 | 2 | 0 | 3 | 0 | 0 | 0 | 2 | 30 | 29 | 14 | 3444 | 0.1016 | 114.4 | 74 |
| The Greyhound (gastropub) | before 20261106-134352-2c7e93 | 38 | 15 | 14 | 13 | 5 | 9 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 41 | 8 | 49 | 3550 | 0.1299 | 171.9 | 72 |
| The Greyhound (gastropub) | after 20261106-144833-44b2d8 | 38 | 15 | 14 | 13 | 5 | 9 | 0 | 0 | 1 | 0 | 1 | 0 | 10 | 46 | 61 | 32 | 3393 | 0.1478 | 199.6 | 78 |
| Zuni Cafe | before 20261106-134644-b10521 | 71 | 13 | 13 | 13 | 7 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 37 | 0 | 70 | 3550 | 0.1388 | 164.2 | 72 |
| Zuni Cafe | after 20261106-145153-12037e | 71 | 13 | 13 | 12 | 6 | 7 | 0 | 0 | 0 | 0 | 1 | 0 | 20 | 59 | 81 | 67 | 3350 | 0.1792 | 290.9 | 65 |
| Seafood chalkboard | before 20261106-134928-48ec86 | 9 | 7 | 7 | 7 | 5 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 23 | 23 | 90 | 3533 | 0.0673 | 76.8 | 74 |
| Seafood chalkboard | after 20261106-150714-cfc7cb | 9 | 7 | 7 | 7 | 5 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 18 | 14 | 67 | 3356 | 0.0521 | 78.9 | 74 |

## Flour + Water

**Before:** Among the 6 dishes I could estimate (14 tried; 8 had no usable estimate; 3 not tried), lowest saturated fat first: 1) Heirloom Tomatoes, about 0.4-2.4 g saturated fat per plate; 2) Bluefin Crudo, 0.5-4.3 g; 3) Little Gem Lettuces, 4.4-11 g. Heirloom Tomatoes and Bluefin Crudo overlap, so treat that order as a toss-up. Heirloom Tomatoes has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

**After:** Among the 6 dishes I could estimate (14 tried; 8 had no usable estimate; 3 not tried), lowest saturated fat first: 1) Heirloom Tomatoes, about 0.4-2.4 g saturated fat per plate; 2) Bluefin Crudo, 0.5-4.3 g; 3) Little Gem Lettuces, 4.4-11 g. Heirloom Tomatoes and Bluefin Crudo overlap, so treat that order as a toss-up. Heirloom Tomatoes has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | HEIRLOOM TOMATOES: sat 0.4-2.4 g, chol 0-0 mg (close_call) | HEIRLOOM TOMATOES: sat 0.4-2.4 g, chol 0-0 mg (close_call) |
| #2 | BLUEFIN CRUDO: sat 0.5-4.3 g, chol 17-115 mg (close_call, driver bottarga (external evidence)) | BLUEFIN CRUDO: sat 0.5-4.3 g, chol 17-115 mg (close_call, driver bottarga (external evidence)) |
| #3 | LITTLE GEM LETTUCES: sat 4.4-11.3 g, chol 4-126 mg (close_call, driver hard-boiled eggs (assumed amount)) | LITTLE GEM LETTUCES: sat 4.4-11.3 g, chol 4-125 mg (close_call, driver hard-boiled eggs (assumed amount)) |

| dish | before | after | why |
|---|---|---|---|
| DUCK TRIANGOLI | evaluated unbounded | skipped | selection: evaluated -> skipped |
| TALEGGIO SCARPINOCC | skipped | evaluated unbounded | selection: skipped -> evaluated |

Unranked after, with reasons:
- POLE BEANS: the estimate has no upper bound: 1 of 1 recipes have no upper bound (cooking.nytimes.com: miso bagna cauda (missing_grams))
- PUTTANESCA: the estimate has no upper bound: 1 of 1 recipes have no upper bound (foodnetwork.com: castelvetrano (missing_grams), chili (missing_grams), boquerones (missing_grams))
- SALSICCIA BIANCA: no recipe of this dish could be portioned (no scenario could be portioned (6 without an applicable portion model))
- ORECCHIETTE: the estimate has no upper bound: 4 of 4 recipes have no upper bound (bakedbree.com: chanterelle (missing_grams), wasabi (missing_grams); aboutamom.com: fresh baby spinach
- TALEGGIO SCARPINOCC: the estimate has no upper bound: 1 of 1 recipes have no upper bound (qbcucina.com: aceto balsamico (missing_grams))
- PAPPARDELLE: the estimate has no upper bound: 3 of 3 recipes have no upper bound (aflavorjournal.com: lamb merguez ragu (missing_grams), tomato xo (missing_grams); bigdeliciouslife.co

## The Greyhound (gastropub)

**Before:** Among the 5 dishes I could estimate (14 tried; 9 had no usable estimate; 1 not tried), lowest saturated fat first: 1) Sicilian Olives, about 1.0-3.0 g saturated fat per plate; 2) Padron Peppers, 0.6-4.0 g; 3) Crispy Squid & Prawns, 1.8-3.5 g. These ranges overlap, so treat the order as a toss-up. Sicilian Olives has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

**After:** Among the 5 dishes I could estimate (14 tried; 9 had no usable estimate; 1 not tried), lowest saturated fat first: 1) Padron Peppers, about 0.6-4.0 g saturated fat per plate; 2) Crispy Squid & Prawns, 1.5-3.0 g; 3) Pan Fried Seabass, 9.0-23 g. Padron Peppers and Crispy Squid & Prawns overlap, so treat that order as a toss-up. Padron Peppers has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | SICILIAN OLIVES: sat 1.0-3.0 g, chol 0-0 mg (close_call) | PADRON PEPPERS: sat 0.6-4.0 g, chol 0-0 mg (close_call) |
| #2 | PADRON PEPPERS: sat 0.6-4.0 g, chol 0-0 mg (close_call) | CRISPY SQUID & PRAWNS: sat 1.5-3.0 g, chol 112-225 mg (tentative) |
| #3 | CRISPY SQUID & PRAWNS: sat 1.8-3.5 g, chol 132-263 mg (tentative) | PAN FRIED SEABASS: sat 9.0-23.1 g, chol 68-158 mg (close_call, driver Seaweed Butter (assumed amount)) |

| dish | before | after | why |
|---|---|---|---|
| SICILIAN OLIVES | evaluated bounded | evaluated unbounded | same recipes, same rows: model variability in grading or matching |
| CRISPY SQUID & PRAWNS | evaluated bounded | evaluated bounded | different recipes calculated (2 before, 4 after, 2 shared): search results or cache, not a code change |
| CAMEMBERT & SAGE CROQUETTES | evaluated unbounded | evaluated unbounded | different recipes calculated (2 before, 3 after, 1 shared): search results or cache, not a code change |
| CORNISH FISH & CHIPS | flagged bounded | flagged bounded | lines no longer open: ['lager beer', 'sunflower oil', 'sunflower oil for frying', 'vegetable oil or refined peanut oil']; different recipes calculated (4 before, 4 after, 2 shared): search results or cache, not a code change |
| SIRLOIN STEAK 10oz | evaluated unbounded | evaluated unbounded | lines no longer open: ["Koffmann's Hand Cut Chips", 'Vine Tomatoes', 'red wine vinegar']; different recipes calculated (4 before, 4 after, 2 shared): search results or cache, not a code change |
| PAN FRIED SEABASS | evaluated unbounded | evaluated bounded | lines no longer open: ['New Potatoes'] |
| CONISBEE BUTCHER LAMB & MINT SAUSAGES | evaluated unbounded | evaluated unbounded | code fix: an 'unprepared' bacon/pancetta record is now a raw record; lines no longer open: ['8-foot hog casing', 'baguette or crusty rolls', 'frying fat (the recipe fries but lists no oil, butter or fat)']; different recipes calculated (1 before, 2 after, 0 shared): search results or cache, not a code change |

Unranked after, with reasons:
- CRACKLING PIG STICKS: no recipe of this dish could be portioned (no scenario could be portioned (3 without an applicable portion model))
- SICILIAN OLIVES: no recipe of this dish could be portioned (no scenario could be portioned (1 without an applicable portion model))
- ROASTED HARISSA AUBERGINE: no recipe of this dish could be portioned (no scenario could be portioned (8 without an applicable portion model))
- THE GREYHOUND SCOTCH EGG: the estimate has no upper bound: 2 of 2 recipes have no upper bound (catwillmadeit.com: canola/vegetable oil (missing_grams), Burnt Apple Puree (missing_grams), Crackli; 
- CAMEMBERT & SAGE CROQUETTES: no recipe of this dish could be portioned (no scenario could be portioned (3 without an applicable portion model))
- SIRLOIN STEAK 10oz: the estimate has no upper bound: 4 of 4 recipes have no upper bound (cookingwithcurls.com: brown sugar (missing_grams), shallot (missing_grams), roasted garlic-goat chees
- CONISBEE BUTCHER LAMB & MINT SAUSAGES: the estimate has no upper bound: 1 of 1 recipes have no upper bound (cooking.nytimes.com: white beans (preparation_unresolved))
- TAGLIATELLE CARBONARA: the estimate has no upper bound: 4 of 4 recipes have no upper bound (mandytanner.com: Wild Mushroom & Asparagus (missing_grams), frying fat (the recipe fries but list; th
- CORNISH FISH & CHIPS: our estimate disagrees with published figures for this kind of dish

Flags after:
- open: CORNISH FISH & CHIPS (PR15, per_plate (vegetable oil); Roli's middle 8.490 vs published 2-5.2; top contributors: CHIPS: frying fat, Vegetable oil, NFS / CHIPS: fry 10.93 g (0.58); CORNISH FISH: frying fat, Vegetable oil, NFS / COR 5.98 g (0.32); Mushy Peas 0.85 g (0.05))

Reference checks after:
- CORNISH FISH & CHIPS (PR15): flagged
  - per_plate: Roli's middle 18.827 vs published 10.249-22.8, 3 independent; passed
  - per_plate (beef dripping): Roli's middle 26.355 vs published 35.6-35.6, 1 independent; shown only
  - per_plate (vegetable oil): Roli's middle 8.490 vs published 2-5.2, 2 independent; FAILED above

## Zuni Cafe

**Before:** Among the 7 dishes I could estimate (13 tried; 6 had no usable estimate), lowest saturated fat first: 1) Marinated olives, about 0.7-4.0 g saturated fat per plate; 2) Wood fire-roasted tomato and eggplant soup, 0.7-3.9 g; 3) Garden lettuce salad, 0.3-5.4 g. These ranges overlap, so treat the order as a toss-up. Marinated olives has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

**After:** Among the 6 dishes I could estimate (13 tried; 7 had no usable estimate), lowest saturated fat first: 1) Wood fire-roasted tomato and eggplant soup, about 0.7-3.9 g saturated fat per plate; 2) Garden lettuce salad, 0.3-5.4 g; 3) Zuni Caesar salad, 2.0-5.6 g. These ranges overlap, so treat the order as a toss-up. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | Marinated olives: sat 0.7-4.0 g, chol 0-0 mg (close_call) | Wood fire-roasted tomato and eggplant so: sat 0.7-3.9 g, chol 2-15 mg (close_call, driver parmesan cheese shavings (assumed amount)) |
| #2 | Wood fire-roasted tomato and eggplant so: sat 0.7-3.9 g, chol 2-15 mg (close_call, driver parmesan cheese shavings (assumed amount)) | Garden lettuce salad with Sungold tomato: sat 0.3-5.4 g, chol 0-17 mg (close_call) |
| #3 | Garden lettuce salad with Sungold tomato: sat 0.3-5.4 g, chol 0-17 mg (close_call) | Zuni Caesar salad‡: sat 2.0-5.6 g, chol 25-95 mg (close_call, driver very fresh large eggs (assumed amount)) |

| dish | before | after | why |
|---|---|---|---|
| Marinated olives | evaluated bounded | flagged bounded | reference check: evaluated -> flagged; lines no longer open: ['red wine vinegar'] |
| House-cured anchovies with celery, Parmigiano | evaluated unbounded | evaluated unbounded | lines no longer open: ['/ 2.2 lbs fresh anchovies', 'banyuls vinegar', 'champagne vinegar', 'chunk of parmigiano-reggiano or grana padano*']; different recipes calculated (5 before, 3 after, 1 shared): search results or cache, not a code change |
| Fuyu persimmon and roasted beet "carpaccio" w |  | evaluated unbounded | new on the after run (menu read differently or newly selected) |
| Fuyu persimmon and roasted beet "carpaccio" w | evaluated unbounded |  | absent from the after run (menu read differently) |
| Zuni Caesar salad | evaluated bounded |  | absent from the after run (menu read differently) |
| Zuni Caesar salad‡ |  | evaluated bounded | new on the after run (menu read differently or newly selected) |
| Garden lettuce salad with Sungold tomatoes, A | evaluated bounded | evaluated bounded | lines no longer open: ['hot sauce', 'red wine vinegar', 'your favorite lettuce']; different recipes calculated (8 before, 8 after, 7 shared): search results or cache, not a code change |
| Pizza with Wagon Wheel cheese, soppressata, w | evaluated unbounded | evaluated unbounded | code fix: new weights row(s) ['W32'] filled lines that were open; different recipes calculated (3 before, 6 after, 3 shared): search results or cache, not a code change |
| Spaghetti with Gulf shrimp, heirloom tomatoes | evaluated bounded | evaluated bounded | different recipes calculated (4 before, 4 after, 3 shared): search results or cache, not a code change |
| Yellowfin tuna‡ grilled rare all'acqua di mar |  | evaluated unbounded | new on the after run (menu read differently or newly selected) |
| Yellowfin tuna grilled rare all'acqua di mare | evaluated unbounded |  | absent from the after run (menu read differently) |
| Steak frites: Stemple Creek Ranch bavette ste | evaluated unbounded | evaluated unbounded | lines no longer open: ['canola oil', 'red wine vinegar']; different recipes calculated (4 before, 5 after, 1 shared): search results or cache, not a code change |
| Stemple Creek Ranch ribeye steak (served with | evaluated bounded | evaluated bounded | different recipes calculated (3 before, 2 after, 2 shared): search results or cache, not a code change |
| Chicken for two roasted in the wood-fired bri | evaluated unbounded | evaluated unbounded | lines no longer open: ['chicken drippings', 'pine nuts']; different recipes calculated (6 before, 5 after, 4 shared): search results or cache, not a code change |

Unranked after, with reasons:
- House-cured anchovies with celery, Parmigiano-Reggiano, and coquillo olives: no recipe of this dish could be portioned (no scenario could be portioned (3 without an applicable portion model))
- Fuyu persimmon and roasted beet "carpaccio" with Laychee goat cheese, tender herbs, and Meyer lemon-pistachio aillade: no recipe of this dish could be portioned (no scenario could be portioned (6 without an applicable portion model))
- Pizza with Wagon Wheel cheese, soppressata, wild nettles, red onion, and Boont Corners sheep cheese: the estimate has no upper bound: 1 of 1 recipes have no upper bound (epicurious.com: unbleached all-purpose flour (missing_grams), cornmeal for sprinkling the baking)
- Yellowfin tuna‡ grilled rare all'acqua di mare with Manila clams, mussels, sprouting cauliflower, string beans, a slow-cooked Early Girl tomato, and aïoli‡: the estimate has no upper bound: 1 of 1 recipes have no upper bound (cooking.nytimes.com: whole (missing_grams), red onion (nutrient_not_reported:saturated_fat_g))
- Steak frites: Stemple Creek Ranch bavette steak with pommes frites, Padrón peppers, avocado, and chimichurri: the estimate has no upper bound: 1 of 2 recipes have no upper bound (cooking.nytimes.com: steak-cut frozen fries (preparation_unresolved))
- Chicken for two roasted in the wood-fired brick oven; warm bread salad with scallions, garlic, bitter greens, dried currants, and pine nuts: the estimate has no upper bound: 3 of 3 recipes have no upper bound (fostersmarket.com: salad (missing_grams), toasted pine nuts (preparation_unresolved), a mutual aid ; 
- Marinated olives: our estimate disagrees with published figures for this kind of dish

Flags after:
- open: Marinated olives (PR13, per_100g; Roli's middle 5.398 vs published 1.7-2.8; top contributors: delallo extra virgin olive oil 2.80 g (0.69); extra virgin olive oil / delallo castelvetrano oli 0.72 g (0.18); imported olives / kosher salt 0.40 g (0.10))

Reference checks after:
- Marinated olives (PR13): flagged
  - per_plate: Roli's middle 4.049 vs published 1.4-1.4, 1 independent; shown only
  - per_100g: Roli's middle 5.398 vs published 1.7-2.8, 5 independent; FAILED above

## Seafood chalkboard

**Before:** Among the 5 dishes I could estimate (7 tried; 2 had no usable estimate), lowest saturated fat first: 1) Ocean Trout / Tuna Poke Salad, about 2.9-7.0 g saturated fat per plate; 2) Crumbed Whiting, 3.2-6.5 g; 3) Crudo Of Swordfish, 2.5-13 g. These ranges overlap, so treat the order as a toss-up. Ocean Trout / Tuna Poke Salad cholesterol about 18-43 mg. Modeled from published recipes and typical portions, not this kitchen's numbers.

**After:** Among the 5 dishes I could estimate (7 tried; 2 had no usable estimate), lowest saturated fat first: 1) Ocean Trout / Tuna Poke Salad, about 0.3-7.0 g saturated fat per plate; 2) Crumbed Whiting, 2.8-5.5 g; 3) Crudo Of Swordfish, 2.5-13 g. These ranges overlap, so treat the order as a toss-up. Ocean Trout / Tuna Poke Salad cholesterol about 18-43 mg. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | OCEAN TROUT / TUNA POKE SALAD: sat 2.9-7.0 g, chol 18-43 mg (close_call) | OCEAN TROUT / TUNA POKE SALAD: sat 0.3-7.0 g, chol 18-43 mg (close_call) |
| #2 | CRUMBED WHITING: sat 3.2-6.5 g, chol 99-199 mg (close_call) | CRUMBED WHITING: sat 2.8-5.5 g, chol 85-170 mg (close_call) |
| #3 | CRUDO OF SWORDFISH: sat 2.5-12.9 g, chol 33-99 mg (close_call) | CRUDO OF SWORDFISH: sat 2.5-12.9 g, chol 33-99 mg (close_call) |

| dish | before | after | why |
|---|---|---|---|
| OCEAN TROUT / TUNA POKE SALAD | evaluated bounded | evaluated bounded | lines no longer open: ['-cup of honey', '-cup of pickled jalapeno', 'bonito flakes', 'brown rice']; different recipes calculated (5 before, 5 after, 1 shared): search results or cache, not a code change |
| COBIA | evaluated unbounded | evaluated unbounded | lines no longer open: ['bottle dry white wine', 'chowder:', 'cobia:', 'ground lavender']; grading changed on 2 page(s), e.g. doughnutlounge.com: variant/high -> different/low (hard exclusion None -> hard_exclusion:dish_type_different) |

Unranked after, with reasons:
- CHILLED MOOLOOLABA PRAWNS: no recipe of this dish could be portioned (no scenario could be portioned (2 without an applicable portion model))
- COBIA: the estimate has no upper bound: 1 of 1 recipes have no upper bound (mydeliciousblog.com: toasted pepitas or sunflower seeds (missing_grams))

## Note added by hand

The reasons above are the tool's first reading. Two need correcting. SICILIAN OLIVES: the reason says "model variability"; the cause is the 12.10.2 marinade rule, which tagged every line of the recipe eaten, leaving the peel strips with no weight. Marinated olives: the flag comes from the same rule. See `CHECKPOINT_3F.md` sections 3 and 5.
