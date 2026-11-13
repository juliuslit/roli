# MVP before/after (local-testing milestone, 2026-11-04)

Before = the Phase 3 runs of 2026-11-04 (menu order selection, no budget, old wording); after = the same photos through the fixed code.

| menu | run | menu items | candidates | selected | evaluated | ranked | unranked | no recipes | errors | skipped | budget-stopped | search credits | model calls | USDA requests | rate-limit waits | model $ | total s | words |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Flour + Water | before 20261105-134002-24bb5a | 19 | 17 | 14 | 13 | 6 | 7 | 1 | 0 | 3 | 0 | 0 | 29 | 421 | 9 | 0.0478 | 107.4 | 74 |
| Flour + Water | after 20261105-195725-71964f | 19 | 17 | 14 | 12 | 6 | 6 | 2 | 0 | 3 | 0 | 0 | 37 | 450 | 28 | 0.0528 | 140.8 | 74 |
| The Greyhound (gastropub) | before 20261105-134150-bdd566 | 38 | 14 | 14 | 14 | 1 | 13 | 0 | 0 | 0 | 0 | 0 | 27 | 170 | 28 | 0.0535 | 105.2 | 62 |
| The Greyhound (gastropub) | after 20261105-210830-9ab5f4 | 38 | 15 | 14 | 14 | 5 | 9 | 0 | 0 | 1 | 0 | 0 | 29 | 467 | 9 | 0.0540 | 111.8 | 79 |
| Zuni Cafe | before 20261105-134335-3be1f4 | 71 | 13 | 13 | 13 | 4 | 9 | 0 | 0 | 0 | 0 | 0 | 22 | 116 | 36 | 0.0621 | 111.5 | 77 |
| Zuni Cafe | after 20261105-200148-e09a7c | 71 | 13 | 13 | 13 | 7 | 6 | 0 | 0 | 0 | 0 | 2 | 24 | 110 | 52 | 0.0585 | 110.4 | 65 |
| Seafood chalkboard | before 20261105-134526-cbaf68 | 9 | 7 | 7 | 7 | 4 | 3 | 0 | 0 | 0 | 0 | 0 | 20 | 140 | 46 | 0.0419 | 84.4 | 73 |
| Seafood chalkboard | after 20261105-200338-7ab1d1 | 9 | 7 | 7 | 7 | 5 | 2 | 0 | 0 | 0 | 0 | 0 | 16 | 88 | 68 | 0.0261 | 58.5 | 74 |

## Flour + Water

**Before:** Among the 6 dishes I could estimate (14 tried; 8 had no usable estimate; 3 not tried), lowest saturated fat first: 1) Heirloom Tomatoes, about 0.4-2.4 g saturated fat per plate; 2) Bluefin Crudo, 0.5-4.3 g; 3) Little Gem Lettuces, 4.4-8.6 g. Heirloom Tomatoes and Bluefin Crudo overlap, so treat that order as a toss-up. Heirloom Tomatoes has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

**After:** Among the 6 dishes I could estimate (14 tried; 8 had no usable estimate; 3 not tried), lowest saturated fat first: 1) Heirloom Tomatoes, about 0.4-2.4 g saturated fat per plate; 2) Bluefin Crudo, 0.5-4.3 g; 3) Little Gem Lettuces, 4.4-11 g. Heirloom Tomatoes and Bluefin Crudo overlap, so treat that order as a toss-up. Heirloom Tomatoes has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | HEIRLOOM TOMATOES: sat 0.4-2.4 g, chol 0-0 mg (close_call) | HEIRLOOM TOMATOES: sat 0.4-2.4 g, chol 0-0 mg (close_call) |
| #2 | BLUEFIN CRUDO: sat 0.5-4.3 g, chol 17-115 mg (close_call, driver bottarga (external evidence)) | BLUEFIN CRUDO: sat 0.5-4.3 g, chol 17-115 mg (close_call, driver bottarga (external evidence)) |
| #3 | LITTLE GEM LETTUCES: sat 4.4-8.6 g, chol 4-13 mg (close_call, driver pecorino sardo (assumed amount)) | LITTLE GEM LETTUCES: sat 4.4-11.3 g, chol 4-126 mg (close_call, driver hard-boiled eggs (assumed amount)) |

| dish | before | after | why |
|---|---|---|---|
| BLUEFIN CRUDO | evaluated bounded | evaluated bounded | lines no longer open: ['castelvetrano olives', 'chopped jarred hot italian chiles']; different recipes calculated (4 before, 5 after, 4 shared): search results or cache, not a code change |
| PUTTANESCA | evaluated unbounded | evaluated unbounded | lines no longer open: ['anchovy filets in olive oil', 'kalamata olives', 'pitted kalamata olives', 'pkg. jus-rol round & thin pizza crust']; different recipes calculated (4 before, 5 after, 4 shared): search results or cache, not a code change |
| MARGHERITA | evaluated bounded | evaluated bounded | lines no longer open: ['for my best pizza dough', 'roma tomatoes']; different recipes calculated (4 before, 5 after, 4 shared): search results or cache, not a code change |
| SALSICCIA BIANCA | evaluated unbounded | evaluated unbounded | lines no longer open: ['cooked italian sausage', 'hot italian sausage', 'nutmeg']; different recipes calculated (4 before, 6 after, 4 shared): search results or cache, not a code change |
| TALEGGIO SCARPINOCC | evaluated unbounded | skipped | selection: evaluated -> skipped |
| SAFFRON SOPRESE | evaluated unbounded | no_recipes unbounded | lines no longer open: ['calabrian chili', 'garlic scapes', 'mussels escabeche', 'sachet saffron powder']; different recipes calculated (2 before, 0 after, 0 shared): search results or cache, not a code change |
| DUCK TRIANGOLI | skipped | evaluated unbounded | selection: skipped -> evaluated |
| PAPPARDELLE | evaluated unbounded | evaluated unbounded | lines no longer open: ['bay', 'pappardelle pasta', 'peperoncino flakes', 'shallots']; different recipes calculated (4 before, 2 after, 2 shared): search results or cache, not a code change |
| PORK CHOP | evaluated bounded | evaluated bounded | lines no longer open: ['whole star anise']; different recipes calculated (4 before, 6 after, 4 shared): search results or cache, not a code change |

Unranked after, with reasons:
- POLE BEANS: the estimate has no upper bound: 1 of 1 recipes have no upper bound (cooking.nytimes.com: miso bagna cauda (missing_grams))
- PUTTANESCA: the estimate has no upper bound: 1 of 1 recipes have no upper bound (foodnetwork.com: castelvetrano (missing_grams), chili (missing_grams), boquerones (missing_grams))
- SALSICCIA BIANCA: no recipe of this dish could be portioned (no scenario could be portioned (6 without an applicable portion model))
- ORECCHIETTE: the estimate has no upper bound: 4 of 4 recipes have no upper bound (bakedbree.com: chanterelle (missing_grams), wasabi (missing_grams); aboutamom.com: fresh baby spinach
- DUCK TRIANGOLI: no recipe of this dish could be portioned (no scenario could be portioned (1 without an applicable portion model))
- PAPPARDELLE: the estimate has no upper bound: 2 of 2 recipes have no upper bound (aflavorjournal.com: lamb merguez ragu (missing_grams), tomato xo (missing_grams); cooking.nytimes.com

## The Greyhound (gastropub)

**Before:** Among the 1 dish I could estimate (14 tried; 13 had no usable estimate), lowest saturated fat first: 1) Padron Peppers, about 1.2-3.0 g saturated fat per plate. It's the only dish I could estimate, so this is one figure, not a ranking. Padron Peppers has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

**After:** Among the 5 dishes I could estimate (14 tried; 9 had no usable estimate; 1 not tried), lowest saturated fat first: 1) Padron Peppers, about 0.6-4.0 g saturated fat per plate; 2) Crispy Squid & Prawns, 1.8-3.5 g; 3) Cornish Fish & Chips, 11-22 g. Padron Peppers and Crispy Squid & Prawns overlap, so treat that order as a toss-up. Padron Peppers has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | PADRON PEPPERS: sat 1.2-3.0 g, chol 0-0 mg (only_estimate) | PADRON PEPPERS: sat 0.6-4.0 g, chol 0-0 mg (close_call) |
| #2 |  | CRISPY SQUID & PRAWNS: sat 1.8-3.5 g, chol 132-263 mg (tentative) |
| #3 |  | CORNISH FISH & CHIPS: sat 10.8-22.5 g, chol 91-185 mg (close_call) |

| dish | before | after | why |
|---|---|---|---|
| PADRON PEPPERS | evaluated bounded | evaluated bounded | lines no longer open: ['sherry vinegar', 'smoked paprika']; different recipes calculated (4 before, 4 after, 3 shared): search results or cache, not a code change |
| PIGS IN BLANKETS | evaluated unbounded | evaluated bounded | lines no longer open: ['Rosemary', 'lil’ smokies', 'milk', 'pizza dough']; different recipes calculated (4 before, 6 after, 4 shared): search results or cache, not a code change |
| ROASTED HARISSA AUBERGINE | evaluated unbounded | evaluated unbounded | lines no longer open: ['/30ml raw organic honey', 'a bunch of fresh flat-leaf parsley', 'chinese or japanese eggplants']; different recipes calculated (4 before, 8 after, 3 shared): search results or cache, not a code change |
| THE GREYHOUND SCOTCH EGG | evaluated unbounded | evaluated unbounded | lines no longer open: ['allspice berries', 'bay', 'nutmeg', 'pickled onions']; different recipes calculated (4 before, 5 after, 4 shared): search results or cache, not a code change |
| CRISPY SQUID & PRAWNS | evaluated unbounded | evaluated bounded | lines no longer open: ['few sprigs of fresh flat-leaf parsley'] |
| CHICKEN & MUSHROOM ARANCINI | evaluated unbounded | skipped | selection: evaluated -> skipped |
| CORNISH FISH & CHIPS | excluded | evaluated bounded | selection: excluded -> evaluated |
| CHICKEN SCHNITZEL | evaluated unbounded | evaluated bounded | lines no longer open: ['Smoked Garlic Butter & Pickles', 'fresh dill', 'picked fresh oregano', 'thinly sliced parmesan']; different recipes calculated (4 before, 7 after, 4 shared): search results or cache, not a code change |
| TAGLIATELLE CARBONARA | evaluated unbounded | evaluated unbounded | lines no longer open: ['parmigiano reggiano cheese', 'rosemary']; different recipes calculated (4 before, 4 after, 3 shared): search results or cache, not a code change |

Unranked after, with reasons:
- CRACKLING PIG STICKS: no recipe of this dish could be portioned (no scenario could be portioned (3 without an applicable portion model))
- SICILIAN OLIVES: no recipe of this dish could be portioned (no scenario could be portioned (1 without an applicable portion model))
- ROASTED HARISSA AUBERGINE: no recipe of this dish could be portioned (no scenario could be portioned (8 without an applicable portion model))
- THE GREYHOUND SCOTCH EGG: no recipe of this dish could be portioned (no scenario could be portioned (5 without an applicable portion model))
- CAMEMBERT & SAGE CROQUETTES: no recipe of this dish could be portioned (no scenario could be portioned (2 without an applicable portion model))
- SIRLOIN STEAK 10oz: the estimate has no upper bound: 4 of 4 recipes have no upper bound (cookingwithcurls.com: brown sugar (missing_grams), shallot (missing_grams), Koffmann's Hand Cut Chips
- PAN FRIED SEABASS: the estimate has no upper bound: 4 of 4 recipes have no upper bound (carolinescooking.com: anchovy fillets (as_used_not_accepted_for_flesh), capers (missing_grams), Samph
- CONISBEE BUTCHER LAMB & MINT SAUSAGES: the estimate has no upper bound: 1 of 1 recipes have no upper bound (foodnetwork.com: 8-foot hog casing (missing_fdc_id), 8-foot hog casing (missing_fdc_id), frying f)
- TAGLIATELLE CARBONARA: the estimate has no upper bound: 4 of 4 recipes have no upper bound (mandytanner.com: Wild Mushroom & Asparagus (missing_grams), frying fat (the recipe fries but list; th

## Zuni Cafe

**Before:** Among the 4 dishes I could estimate (13 tried; 9 had no usable estimate), lowest saturated fat first: 1) Wood fire-roasted tomato and eggplant soup, about 0.7-3.9 g saturated fat per plate; 2) Zuni Caesar salad, 2.0-5.7 g; 3) Spaghetti with Gulf shrimp, 1.9-12 g. These ranges overlap, so treat the order as a toss-up. Spaghetti with Gulf shrimp may carry up to 376 mg cholesterol. Modeled from published recipes and typical portions, not this kitchen's numbers.

**After:** Among the 7 dishes I could estimate (13 tried; 6 had no usable estimate), lowest saturated fat first: 1) Wood fire-roasted tomato and eggplant soup, about 0.7-3.9 g saturated fat per plate; 2) Garden lettuce salad, 0.3-5.4 g; 3) Zuni Caesar salad, 2.0-5.6 g. These ranges overlap, so treat the order as a toss-up. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | Wood fire-roasted tomato and eggplant so: sat 0.7-3.9 g, chol 0-15 mg (close_call, driver parmesan cheese shavings (assumed amount)) | Wood fire-roasted tomato and eggplant so: sat 0.7-3.9 g, chol 2-15 mg (close_call, driver parmesan cheese shavings (assumed amount)) |
| #2 | Zuni Caesar salad: sat 2.0-5.7 g, chol 25-95 mg (close_call, driver very fresh large eggs (assumed amount)) | Garden lettuce salad with Sungold tomato: sat 0.3-5.4 g, chol 0-17 mg (close_call) |
| #3 | Spaghetti with Gulf shrimp, heirloom tom: sat 1.9-11.9 g, chol 4-376 mg (close_call) | Zuni Caesar salad: sat 2.0-5.6 g, chol 25-95 mg (close_call, driver very fresh large eggs (assumed amount)) |

| dish | before | after | why |
|---|---|---|---|
| Marinated olives | evaluated unbounded | evaluated bounded | lines no longer open: ['fresh rosemary', 'fresh thyme', 'mediterranean olive mix*']; different recipes calculated (4 before, 7 after, 4 shared): search results or cache, not a code change |
| Shoestring potatoes | evaluated unbounded | evaluated bounded | lines no longer open: ['peanut oil']; different recipes calculated (4 before, 6 after, 4 shared): search results or cache, not a code change |
| House-cured anchovies with celery, Parmigiano | evaluated unbounded | evaluated unbounded | lines no longer open: ['anchovy fillets', 'chunk of parmigiano-reggiano or grana padano*', 'fresh basil', 'heads frisée']; different recipes calculated (4 before, 4 after, 2 shared): search results or cache, not a code change |
| Fuyu persimmon and roasted beet "carpaccio" w |  | evaluated unbounded | new on the after run (menu read differently or newly selected) |
| Fuyu persimmon and roasted beet "carpaccio" w | evaluated unbounded |  | absent from the after run (menu read differently) |
| Garden lettuce salad with Sungold tomatoes, A | evaluated unbounded | evaluated bounded | lines no longer open: ['chopped habanero pepper']; different recipes calculated (4 before, 9 after, 4 shared): search results or cache, not a code change |
| Spaghetti with Gulf shrimp, heirloom tomatoes | evaluated bounded | evaluated bounded | code fix: an 'unprepared' bacon/pancetta record is now a raw record; lines no longer open: ['-size bunch black kale', 'shallots', 'shrimp']; different recipes calculated (4 before, 4 after, 3 shared): search results or cache, not a code change |
| Yellowfin tuna grilled rare all'acqua di mare | evaluated unbounded |  | absent from the after run (menu read differently) |
| Yellowfin tuna grilled rare all'acqua di mare |  | evaluated unbounded | new on the after run (menu read differently or newly selected) |
| Chicken for two roasted in the wood-fired bri | evaluated unbounded | evaluated unbounded | lines no longer open: ['chunks of rustic sourdough bread', 'fresh thyme', 'tender sprigs fresh thyme']; different recipes calculated (4 before, 6 after, 4 shared): search results or cache, not a code change |

Unranked after, with reasons:
- House-cured anchovies with celery, Parmigiano-Reggiano, and coquillo olives: no recipe of this dish could be portioned (no scenario could be portioned (4 without an applicable portion model))
- Fuyu persimmon and roasted beet "carpaccio" with Laychee goat cheese, tender herbs, and Meyer lemon-pistachio aïllade: no recipe of this dish could be portioned (no scenario could be portioned (4 without an applicable portion model))
- Pizza with Wagon Wheel cheese, soppressata, wild nettles, red onion, and Boont Corners sheep cheese: the estimate has no upper bound: 1 of 1 recipes have no upper bound (epicurious.com: unbleached all-purpose flour (missing_grams), cornmeal for sprinkling the baking)
- Yellowfin tuna grilled rare all'acqua di mare with Manila clams, mussels, sprouting cauliflower, string beans, a slow-cooked Early Girl tomato, and aioli: no recipe of this dish could be portioned (no scenario could be portioned (1 without an applicable portion model))
- Steak frites: Stemple Creek Ranch bavette steak with pommes frites, Padrón peppers, avocado, and chimichurri: the estimate has no upper bound: 3 of 3 recipes have no upper bound (cooking.nytimes.com: steak-cut frozen fries (preparation_unresolved); delish.com: canola oil (missing
- Chicken for two roasted in the wood-fired brick oven; warm bread salad with scallions, garlic, bitter greens, dried currants, and pine nuts: the estimate has no upper bound: 3 of 3 recipes have no upper bound (debspots.com: pine nuts (preparation_unresolved), chicken drippings (missing_grams), a mutual ; foste

## Seafood chalkboard

**Before:** Among the 4 dishes I could estimate (7 tried; 3 had no usable estimate), lowest saturated fat first: 1) Ocean Trout / Tuna Poke Salad, about 2.0-7.1 g saturated fat per plate; 2) Crudo Of Swordfish, 2.5-13 g; 3) Snapper, 4.7-15 g. These ranges overlap, so treat the order as a toss-up. Ocean Trout / Tuna Poke Salad cholesterol about 18-43 mg. Modeled from published recipes and typical portions, not this kitchen's numbers.

**After:** Among the 5 dishes I could estimate (7 tried; 2 had no usable estimate), lowest saturated fat first: 1) Ocean Trout / Tuna Poke Salad, about 0.3-7.1 g saturated fat per plate; 2) Crumbed Whiting, 3.2-6.5 g; 3) Crudo Of Swordfish, 2.5-13 g. These ranges overlap, so treat the order as a toss-up. Ocean Trout / Tuna Poke Salad cholesterol about 18-43 mg. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | OCEAN TROUT / TUNA POKE SALAD: sat 2.0-7.1 g, chol 18-43 mg (close_call) | OCEAN TROUT / TUNA POKE SALAD: sat 0.3-7.1 g, chol 18-43 mg (close_call) |
| #2 | CRUDO OF SWORDFISH: sat 2.5-13.2 g, chol 33-99 mg (close_call) | CRUMBED WHITING: sat 3.2-6.5 g, chol 99-199 mg (close_call) |
| #3 | SNAPPER: sat 4.7-15.4 g, chol 55-132 mg (close_call) | CRUDO OF SWORDFISH: sat 2.5-12.9 g, chol 33-99 mg (close_call) |

| dish | before | after | why |
|---|---|---|---|
| OCEAN TROUT / TUNA POKE SALAD | evaluated bounded | evaluated bounded | lines no longer open: ['chilli powder', 'coriander', 'sugar snap peas']; different recipes calculated (4 before, 6 after, 4 shared): search results or cache, not a code change |
| CRUMBED WHITING | evaluated unbounded | evaluated bounded | lines no longer open: ['gluten-free all-purpose flour', 'vegetable oil for frying'] |
| COBIA | evaluated unbounded | evaluated unbounded | lines no longer open: ['bottle dry white wine', 'cardamom pods', 'champagne vinegar', 'chile oil']; different recipes calculated (4 before, 2 after, 2 shared): search results or cache, not a code change |
| SNAPPER | evaluated bounded | evaluated bounded | lines no longer open: ['cajun or old bay seasoning*']; different recipes calculated (4 before, 5 after, 4 shared): search results or cache, not a code change |

Unranked after, with reasons:
- CHILLED MOOLOOLABA PRAWNS: no recipe of this dish could be portioned (no scenario could be portioned (2 without an applicable portion model))
- COBIA: the estimate has no upper bound: 1 of 1 recipes have no upper bound (mydeliciousblog.com: toasted pepitas or sunflower seeds (missing_grams))
