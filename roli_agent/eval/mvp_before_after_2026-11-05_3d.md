# MVP before/after (Checkpoint 3D, 2026-11-05)

Before = the Checkpoint 3C final runs of 2026-11-05 (Greyhound: the clean rerun after USDA's hour reset). After = Checkpoint 3D on the final code: line tags, near-zero rule I04, dish-family cards, reference check, saved USDA answers; same photos, warm caches. Greyhound and the seafood chalkboard are pass 2 (mvp_eval_2026-11-05_3d_v2.*); Zuni and Flour + Water are pass 3 reruns after two readings of the near-zero rule were corrected (_v3_zuni.*, _v3_fw.*). Pass 1, with a cold saved-answer store, is mvp_eval_2026-11-05_3d.*.

| menu | run | menu items | candidates | selected | evaluated | ranked | unranked | no recipes | errors | skipped | budget-stopped | flagged | USDA-unavailable | search credits | model calls | USDA requests | rate-limit waits | USDA left after | model $ | total s | words |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Flour + Water | before 20261105-195725-71964f | 19 | 17 | 14 | 12 | 6 | 6 | 2 | 0 | 3 | 0 |  |  | 0 | 37 | 450 | 28 |  | 0.0528 | 140.8 | 74 |
| Flour + Water | after 20261105-225651-aa66fa | 19 | 17 | 14 | 12 | 6 | 6 | 2 | 0 | 3 | 0 | 0 | 0 | 0 | 41 | 12 | 32 | 2600 | 0.1452 | 163.2 | 74 |
| The Greyhound (gastropub) | before 20261105-210830-9ab5f4 | 38 | 15 | 14 | 14 | 5 | 9 | 0 | 0 | 1 | 0 |  |  | 0 | 29 | 467 | 9 |  | 0.0540 | 111.8 | 79 |
| The Greyhound (gastropub) | after 20261105-224308-ac4093 | 38 | 15 | 14 | 12 | 5 | 9 | 0 | 0 | 1 | 0 | 2 | 0 | 0 | 43 | 12 | 74 | 2529 | 0.1518 | 174.1 | 78 |
| Zuni Cafe | before 20261105-200148-e09a7c | 71 | 13 | 13 | 13 | 7 | 6 | 0 | 0 | 0 | 0 |  |  | 2 | 24 | 110 | 52 |  | 0.0585 | 110.4 | 65 |
| Zuni Cafe | after 20261105-225157-850782 | 71 | 13 | 13 | 13 | 7 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 39 | 10 | 19 | 2572 | 0.1601 | 182.4 | 72 |
| Seafood chalkboard | before 20261105-200338-7ab1d1 | 9 | 7 | 7 | 7 | 5 | 2 | 0 | 0 | 0 | 0 |  |  | 0 | 16 | 88 | 68 |  | 0.0261 | 58.5 | 74 |
| Seafood chalkboard | after 20261105-224837-9656cc | 9 | 7 | 7 | 7 | 5 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 21 | 5 | 108 | 2552 | 0.0731 | 78.2 | 74 |

## Flour + Water

**Before:** Among the 6 dishes I could estimate (14 tried; 8 had no usable estimate; 3 not tried), lowest saturated fat first: 1) Heirloom Tomatoes, about 0.4-2.4 g saturated fat per plate; 2) Bluefin Crudo, 0.5-4.3 g; 3) Little Gem Lettuces, 4.4-11 g. Heirloom Tomatoes and Bluefin Crudo overlap, so treat that order as a toss-up. Heirloom Tomatoes has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

**After:** Among the 6 dishes I could estimate (14 tried; 8 had no usable estimate; 3 not tried), lowest saturated fat first: 1) Heirloom Tomatoes, about 0.4-2.4 g saturated fat per plate; 2) Bluefin Crudo, 0.5-4.3 g; 3) Little Gem Lettuces, 4.4-11 g. Heirloom Tomatoes and Bluefin Crudo overlap, so treat that order as a toss-up. Heirloom Tomatoes has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | HEIRLOOM TOMATOES: sat 0.4-2.4 g, chol 0-0 mg (close_call) | HEIRLOOM TOMATOES: sat 0.4-2.4 g, chol 0-0 mg (close_call) |
| #2 | BLUEFIN CRUDO: sat 0.5-4.3 g, chol 17-115 mg (close_call, driver bottarga (external evidence)) | BLUEFIN CRUDO: sat 0.5-4.3 g, chol 17-115 mg (close_call, driver bottarga (external evidence)) |
| #3 | LITTLE GEM LETTUCES: sat 4.4-11.3 g, chol 4-126 mg (close_call, driver hard-boiled eggs (assumed amount)) | LITTLE GEM LETTUCES: sat 4.4-11.3 g, chol 4-126 mg (close_call, driver hard-boiled eggs (assumed amount)) |

| dish | before | after | why |
|---|---|---|---|
| POLE BEANS | evaluated unbounded | evaluated unbounded | different recipes calculated (3 before, 6 after, 3 shared): search results or cache, not a code change |
| ORECCHIETTE | evaluated unbounded | evaluated unbounded | lines no longer open: ['milk', 'salt-packed capers']; different recipes calculated (4 before, 4 after, 3 shared): search results or cache, not a code change |
| DUCK TRIANGOLI | evaluated unbounded | skipped | selection: evaluated -> skipped |
| TALEGGIO SCARPINOCC | skipped | evaluated unbounded | selection: skipped -> evaluated |
| PAPPARDELLE | evaluated unbounded | evaluated unbounded | different recipes calculated (2 before, 4 after, 2 shared): search results or cache, not a code change |

Unranked after, with reasons:
- POLE BEANS: the estimate has no upper bound: 2 of 2 recipes have no upper bound (cooking.nytimes.com: miso bagna cauda (missing_grams); thekitchn.com: miso bagna cauda (missing_grams
- PUTTANESCA: the estimate has no upper bound: 1 of 1 recipes have no upper bound (foodnetwork.com: castelvetrano (missing_grams), chili (missing_grams), boquerones (missing_grams))
- SALSICCIA BIANCA: no recipe of this dish could be portioned (no scenario could be portioned (6 without an applicable portion model))
- ORECCHIETTE: the estimate has no upper bound: 4 of 4 recipes have no upper bound (bakedbree.com: chanterelle (missing_grams), wasabi (missing_grams); aboutamom.com: fresh baby spinach
- TALEGGIO SCARPINOCC: the estimate has no upper bound: 1 of 1 recipes have no upper bound (qbcucina.com: aceto balsamico (missing_grams))
- PAPPARDELLE: the estimate has no upper bound: 3 of 3 recipes have no upper bound (aflavorjournal.com: lamb merguez ragu (missing_grams), tomato xo (missing_grams); bigdeliciouslife.co

Reference checks after (card; per plate: Roli's middle vs published; per 100 g):
- TODAY'S RICOTTA: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- POLE BEANS: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- BLUEFIN CRUDO: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- LITTLE GEM LETTUCES: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- HEIRLOOM TOMATOES: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- PUTTANESCA: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- MARGHERITA: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- SALSICCIA BIANCA: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- ORECCHIETTE: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- TALEGGIO SCARPINOCC: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- SAFFRON SOPRESE: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- PAPPARDELLE: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- KING SALMON: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- PORK CHOP: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None

## The Greyhound (gastropub)

**Before:** Among the 5 dishes I could estimate (14 tried; 9 had no usable estimate; 1 not tried), lowest saturated fat first: 1) Padron Peppers, about 0.6-4.0 g saturated fat per plate; 2) Crispy Squid & Prawns, 1.8-3.5 g; 3) Cornish Fish & Chips, 11-22 g. Padron Peppers and Crispy Squid & Prawns overlap, so treat that order as a toss-up. Padron Peppers has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

**After:** Among the 5 dishes I could estimate (14 tried; 9 had no usable estimate; 1 not tried), lowest saturated fat first: 1) Padron Peppers, about 0.6-1.9 g saturated fat per plate; 2) Crispy Squid & Prawns, 1.8-3.5 g; 3) Pan Fried Seabass, 8.7-23 g. Padron Peppers and Crispy Squid & Prawns overlap, so treat that order as a toss-up. Padron Peppers has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | PADRON PEPPERS: sat 0.6-4.0 g, chol 0-0 mg (close_call) | PADRON PEPPERS: sat 0.6-1.9 g, chol 0-0 mg (close_call) |
| #2 | CRISPY SQUID & PRAWNS: sat 1.8-3.5 g, chol 132-263 mg (tentative) | CRISPY SQUID & PRAWNS: sat 1.8-3.5 g, chol 132-263 mg (tentative) |
| #3 | CORNISH FISH & CHIPS: sat 10.8-22.5 g, chol 91-185 mg (close_call) | PAN FRIED SEABASS: sat 8.7-23.2 g, chol 68-158 mg (close_call, driver Seaweed Butter (assumed amount)) |

| dish | before | after | why |
|---|---|---|---|
| PADRON PEPPERS | evaluated bounded | evaluated bounded | different recipes calculated (4 before, 5 after, 4 shared): search results or cache, not a code change |
| SICILIAN OLIVES | evaluated unbounded | flagged bounded | same recipes, same rows: model variability in grading or matching |
| CRISPY SQUID & PRAWNS | evaluated bounded | evaluated bounded | different recipes calculated (1 before, 2 after, 1 shared): search results or cache, not a code change |
| CORNISH FISH & CHIPS | evaluated bounded | flagged bounded | lines no longer open: ['for the chips:'] |
| SIRLOIN STEAK |  | evaluated unbounded | new on the after run (menu read differently or newly selected) |
| SIRLOIN STEAK 10oz | evaluated unbounded |  | absent from the after run (menu read differently) |
| PAN FRIED SEABASS | evaluated unbounded | evaluated bounded | lines no longer open: ['New Potatoes', 'anchovy fillets', 'capers']; different recipes calculated (4 before, 4 after, 3 shared): search results or cache, not a code change |
| TAGLIATELLE CARBONARA | evaluated unbounded | evaluated unbounded | lines no longer open: ['heavy cream']; different recipes calculated (4 before, 4 after, 3 shared): search results or cache, not a code change |

Unranked after, with reasons:
- CRACKLING PIG STICKS: no recipe of this dish could be portioned (no scenario could be portioned (3 without an applicable portion model))
- ROASTED HARISSA AUBERGINE: no recipe of this dish could be portioned (no scenario could be portioned (8 without an applicable portion model))
- THE GREYHOUND SCOTCH EGG: the estimate has no upper bound: 2 of 2 recipes have no upper bound (catwillmadeit.com: canola/vegetable oil (missing_grams), Crackling (missing_grams); greatbritishchefs
- CAMEMBERT & SAGE CROQUETTES: no recipe of this dish could be portioned (no scenario could be portioned (2 without an applicable portion model))
- SIRLOIN STEAK: the estimate has no upper bound: 4 of 4 recipes have no upper bound (cookingwithcurls.com: brown sugar (missing_grams), Koffmann's Hand Cut Chips (missing_grams); food.co
- CONISBEE BUTCHER LAMB & MINT SAUSAGES: the estimate has no upper bound: 1 of 1 recipes have no upper bound (foodnetwork.com: 8-foot hog casing (missing_fdc_id), 8-foot hog casing (missing_fdc_id), frying f)
- TAGLIATELLE CARBONARA: the estimate has no upper bound: 4 of 4 recipes have no upper bound (mandytanner.com: Wild Mushroom & Asparagus (missing_grams), frying fat (the recipe fries but list; th
- SICILIAN OLIVES: our estimate disagrees with published figures for this kind of dish
- CORNISH FISH & CHIPS: our estimate disagrees with published figures for this kind of dish

Flags after:
- open: SICILIAN OLIVES (PR13, per_plate; Roli's middle 2.692 vs published 1.6-1.6; suspected: eaten)
- open: CORNISH FISH & CHIPS (PR15, per_plate; Roli's middle 16.010 vs published 2.0-3.9; suspected: eaten)

Reference checks after (card; per plate: Roli's middle vs published; per 100 g):
- CRACKLING PIG STICKS: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- PADRON PEPPERS: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- SICILIAN OLIVES: PR13; flagged; plate 2.692 vs 1.6-1.6; per 100 g 3.590 vs 1.8-2.8
- PIGS IN BLANKETS: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- ROASTED HARISSA AUBERGINE: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- THE GREYHOUND SCOTCH EGG: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- CRISPY SQUID & PRAWNS: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- CAMEMBERT & SAGE CROQUETTES: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- CORNISH FISH & CHIPS: PR15; flagged; plate 16.010 vs 2.0-3.9; per 100 g n/a vs None-None
- SIRLOIN STEAK: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- CHICKEN SCHNITZEL: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- PAN FRIED SEABASS: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- CONISBEE BUTCHER LAMB & MINT SAUSAGES: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- TAGLIATELLE CARBONARA: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None

## Zuni Cafe

**Before:** Among the 7 dishes I could estimate (13 tried; 6 had no usable estimate), lowest saturated fat first: 1) Wood fire-roasted tomato and eggplant soup, about 0.7-3.9 g saturated fat per plate; 2) Garden lettuce salad, 0.3-5.4 g; 3) Zuni Caesar salad, 2.0-5.6 g. These ranges overlap, so treat the order as a toss-up. Modeled from published recipes and typical portions, not this kitchen's numbers.

**After:** Among the 7 dishes I could estimate (13 tried; 6 had no usable estimate), lowest saturated fat first: 1) Marinated olives, about 1.3-3.3 g saturated fat per plate; 2) Wood fire-roasted tomato and eggplant soup, 0.7-3.9 g; 3) Garden lettuce salad, 0.3-5.4 g. These ranges overlap, so treat the order as a toss-up. Marinated olives has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | Wood fire-roasted tomato and eggplant so: sat 0.7-3.9 g, chol 2-15 mg (close_call, driver parmesan cheese shavings (assumed amount)) | Marinated olives: sat 1.3-3.3 g, chol 0-0 mg (close_call) |
| #2 | Garden lettuce salad with Sungold tomato: sat 0.3-5.4 g, chol 0-17 mg (close_call) | Wood fire-roasted tomato and eggplant so: sat 0.7-3.9 g, chol 2-15 mg (close_call, driver parmesan cheese shavings (assumed amount)) |
| #3 | Zuni Caesar salad: sat 2.0-5.6 g, chol 25-95 mg (close_call, driver very fresh large eggs (assumed amount)) | Garden lettuce salad with Sungold tomato: sat 0.3-5.4 g, chol 0-17 mg (close_call) |

| dish | before | after | why |
|---|---|---|---|
| Marinated olives | evaluated bounded | evaluated bounded | lines no longer open: ['good olive oil']; different recipes calculated (7 before, 4 after, 4 shared): search results or cache, not a code change |
| Shoestring potatoes | evaluated bounded | evaluated bounded | code fix: new weights row(s) ['W31', 'W40'] filled lines that were open; different recipes calculated (6 before, 5 after, 4 shared): search results or cache, not a code change |
| House-cured anchovies with celery, Parmigiano | evaluated unbounded | evaluated unbounded | lines no longer open: ['/ 2.2 lbs fresh anchovies', 'juice of half a large lemon', 'more sliced garlic']; different recipes calculated (4 before, 5 after, 4 shared): search results or cache, not a code change |
| Fuyu persimmon and roasted beet "carpaccio" w | evaluated unbounded |  | absent from the after run (menu read differently) |
| Fuyu persimmon and roasted beet "carpaccio" w |  | evaluated unbounded | new on the after run (menu read differently or newly selected) |
| Garden lettuce salad with Sungold tomatoes, A | evaluated bounded | evaluated bounded | lines no longer open: ['-ounce log goat cheese', 'pear or cherry tomatoes']; different recipes calculated (9 before, 8 after, 8 shared): search results or cache, not a code change |
| Yellowfin tuna grilled rare all'acqua di mare | evaluated unbounded |  | absent from the after run (menu read differently) |
| Yellowfin tuna grilled rare all'acqua di mare |  | evaluated unbounded | new on the after run (menu read differently or newly selected) |
| Chicken for two roasted in the wood-fired bri | evaluated unbounded | evaluated unbounded | lines no longer open: ['arugula', 'champagne vinegar or white wine vinegar', 'few handfuls of arugula', 'generous 8 ounces slightly stale open-crumbed']; different recipes calculated (6 before, 5 after, 5 shared): search results or cache, not a code change |

Unranked after, with reasons:
- House-cured anchovies with celery, Parmigiano-Reggiano, and coquillo olives: the estimate has no upper bound: 1 of 1 recipes have no upper bound (30daysofgreekfood.com: fresh anchovies (as_used_not_accepted_for_flesh), white wine vinegar (missing_
- Fuyu persimmon and roasted beet "carpaccio" with Laychee goat cheese, tender herbs, and Meyer lemon-pistachio aillade: no recipe of this dish could be portioned (no scenario could be portioned (3 without an applicable portion model))
- Pizza with Wagon Wheel cheese, soppressata, wild nettles, red onion, and Boont Corners sheep cheese: the estimate has no upper bound: 1 of 1 recipes have no upper bound (epicurious.com: unbleached all-purpose flour (missing_grams), cornmeal for sprinkling the baking)
- Yellowfin tuna grilled rare all'acqua di mare with Manila clams, mussels, sprouting cauliflower, string beans, a slow-cooked Early Girl tomato, and aïoli: no recipe of this dish could be portioned (no scenario could be portioned (1 without an applicable portion model))
- Steak frites: Stemple Creek Ranch bavette steak with pommes frites, Padrón peppers, avocado, and chimichurri: the estimate has no upper bound: 3 of 3 recipes have no upper bound (cooking.nytimes.com: steak-cut frozen fries (preparation_unresolved); delish.com: canola oil (missing
- Chicken for two roasted in the wood-fired brick oven; warm bread salad with scallions, garlic, bitter greens, dried currants, and pine nuts: the estimate has no upper bound: 3 of 3 recipes have no upper bound (debspots.com: pine nuts (preparation_unresolved), chicken drippings (missing_grams), a mutual ; foste

Reference checks after (card; per plate: Roli's middle vs published; per 100 g):
- Marinated olives: PR13; inside; plate 2.297 vs 1.6-1.6; per 100 g 3.063 vs 1.8-2.8
- Shoestring potatoes: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- House-cured anchovies with celery, Parmigiano: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- Fuyu persimmon and roasted beet "carpaccio" w: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- Zuni Caesar salad: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- Garden lettuce salad with Sungold tomatoes, A: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- Wood fire-roasted tomato and eggplant soup wi: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- Pizza with Wagon Wheel cheese, soppressata, w: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- Spaghetti with Gulf shrimp, heirloom tomatoes: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- Yellowfin tuna grilled rare all'acqua di mare: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- Steak frites: Stemple Creek Ranch bavette ste: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- Stemple Creek Ranch ribeye steak (served with: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- Chicken for two roasted in the wood-fired bri: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None

## Seafood chalkboard

**Before:** Among the 5 dishes I could estimate (7 tried; 2 had no usable estimate), lowest saturated fat first: 1) Ocean Trout / Tuna Poke Salad, about 0.3-7.1 g saturated fat per plate; 2) Crumbed Whiting, 3.2-6.5 g; 3) Crudo Of Swordfish, 2.5-13 g. These ranges overlap, so treat the order as a toss-up. Ocean Trout / Tuna Poke Salad cholesterol about 18-43 mg. Modeled from published recipes and typical portions, not this kitchen's numbers.

**After:** Among the 5 dishes I could estimate (7 tried; 2 had no usable estimate), lowest saturated fat first: 1) Ocean Trout / Tuna Poke Salad, about 2.9-7.0 g saturated fat per plate; 2) Crumbed Whiting, 3.2-6.5 g; 3) Crudo Of Swordfish, 2.5-13 g. These ranges overlap, so treat the order as a toss-up. Ocean Trout / Tuna Poke Salad cholesterol about 18-43 mg. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | OCEAN TROUT / TUNA POKE SALAD: sat 0.3-7.1 g, chol 18-43 mg (close_call) | OCEAN TROUT / TUNA POKE SALAD: sat 2.9-7.0 g, chol 18-43 mg (close_call) |
| #2 | CRUMBED WHITING: sat 3.2-6.5 g, chol 99-199 mg (close_call) | CRUMBED WHITING: sat 3.2-6.5 g, chol 99-199 mg (close_call) |
| #3 | CRUDO OF SWORDFISH: sat 2.5-12.9 g, chol 33-99 mg (close_call) | CRUDO OF SWORDFISH: sat 2.5-12.9 g, chol 33-99 mg (close_call) |

| dish | before | after | why |
|---|---|---|---|
| CRUDO OF SWORDFISH | evaluated bounded | evaluated bounded | lines no longer open: ['baby spinach leaves', 'mustard']; different recipes calculated (4 before, 3 after, 3 shared): search results or cache, not a code change |
| OCEAN TROUT / TUNA POKE SALAD | evaluated bounded | evaluated bounded | lines no longer open: ['/ 4 oz sweet onion', 'carrots', 'corn tortillas', 'cucumber']; different recipes calculated (6 before, 5 after, 5 shared): search results or cache, not a code change |

Unranked after, with reasons:
- CHILLED MOOLOOLABA PRAWNS: no recipe of this dish could be portioned (no scenario could be portioned (2 without an applicable portion model))
- COBIA: the estimate has no upper bound: 1 of 1 recipes have no upper bound (mydeliciousblog.com: toasted pepitas or sunflower seeds (missing_grams))

Reference checks after (card; per plate: Roli's middle vs published; per 100 g):
- CRUDO OF SWORDFISH: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- OCEAN TROUT / TUNA POKE SALAD: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- CRUMBED WHITING: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- CHILLED MOOLOOLABA PRAWNS: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- OCEAN TROUT: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- COBIA: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
- SNAPPER: no card; no reference: no dish-family card for this dish; plate None vs None-None; per 100 g n/a vs None-None
