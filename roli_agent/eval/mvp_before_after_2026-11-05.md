# MVP before/after (local-testing milestone, 2026-11-04)

Before = the Phase 3 runs of 2026-11-04 (menu order selection, no budget, old wording); after = the same photos through the fixed code.

| menu | run | menu items | candidates | selected | evaluated | ranked | unranked | no recipes | errors | skipped | budget-stopped | search credits | model calls | USDA requests | rate-limit waits | model $ | total s | words |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Flour + Water | before 20261104-040940-dc2383 | 19 | 17 | 14 | 13 | 5 | 8 | 1 | 0 | 3 | 0 | 0 | 33 | 409 | 4 | 0.0559 | 116.8 | 74 |
| Flour + Water | after 20261105-134002-24bb5a | 19 | 17 | 14 | 13 | 6 | 7 | 1 | 0 | 3 | 0 | 0 | 29 | 421 | 9 | 0.0478 | 107.4 | 74 |
| The Greyhound (gastropub) | before 20261104-041137-b7cf5b | 38 | 14 | 14 | 14 | 1 | 13 | 0 | 0 | 0 | 0 | 0 | 31 | 202 | 36 | 0.0592 | 117.3 | 62 |
| The Greyhound (gastropub) | after 20261105-134150-bdd566 | 38 | 14 | 14 | 14 | 1 | 13 | 0 | 0 | 0 | 0 | 0 | 27 | 170 | 28 | 0.0535 | 105.2 | 62 |
| Zuni Cafe | before 20261104-041334-aa2845 | 71 | 13 | 13 | 13 | 4 | 9 | 0 | 0 | 0 | 0 | 5 | 24 | 105 | 41 | 0.0604 | 115.8 | 70 |
| Zuni Cafe | after 20261105-134335-3be1f4 | 71 | 13 | 13 | 13 | 4 | 9 | 0 | 0 | 0 | 0 | 0 | 22 | 116 | 36 | 0.0621 | 111.5 | 77 |
| Seafood chalkboard | before 20261104-041530-432689 | 9 | 7 | 7 | 7 | 4 | 3 | 0 | 0 | 0 | 0 | 5 | 20 | 89 | 56 | 0.0364 | 72.6 | 73 |
| Seafood chalkboard | after 20261105-134526-cbaf68 | 9 | 7 | 7 | 7 | 4 | 3 | 0 | 0 | 0 | 0 | 0 | 20 | 140 | 46 | 0.0419 | 84.4 | 73 |

## Flour + Water

**Before:** Among the 5 dishes I could estimate (14 tried; 9 had no usable estimate; 3 not tried), lowest saturated fat first: 1) Heirloom Tomatoes, about 0.4-2.4 g saturated fat per plate; 2) Bluefin Crudo, 0.5-4.3 g; 3) Little Gem Lettuces, 4.4-8.6 g. Heirloom Tomatoes and Bluefin Crudo overlap, so treat that order as a toss-up. Heirloom Tomatoes has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

**After:** Among the 6 dishes I could estimate (14 tried; 8 had no usable estimate; 3 not tried), lowest saturated fat first: 1) Heirloom Tomatoes, about 0.4-2.4 g saturated fat per plate; 2) Bluefin Crudo, 0.5-4.3 g; 3) Little Gem Lettuces, 4.4-8.6 g. Heirloom Tomatoes and Bluefin Crudo overlap, so treat that order as a toss-up. Heirloom Tomatoes has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | HEIRLOOM TOMATOES: sat 0.4-2.4 g, chol 0-0 mg (close_call) | HEIRLOOM TOMATOES: sat 0.4-2.4 g, chol 0-0 mg (close_call) |
| #2 | BLUEFIN CRUDO: sat 0.5-4.3 g, chol 17-115 mg (tentative, driver bottarga (external evidence)) | BLUEFIN CRUDO: sat 0.5-4.3 g, chol 17-115 mg (close_call, driver bottarga (external evidence)) |
| #3 | LITTLE GEM LETTUCES: sat 4.4-8.6 g, chol 4-13 mg (close_call, driver pecorino sardo (assumed amount)) | LITTLE GEM LETTUCES: sat 4.4-8.6 g, chol 4-13 mg (close_call, driver pecorino sardo (assumed amount)) |

| dish | before | after | why |
|---|---|---|---|
| POLE BEANS | evaluated unbounded | evaluated unbounded | lines no longer open: ['lemon zested', 'lovage']; different recipes calculated (4 before, 3 after, 3 shared): search results or cache, not a code change |
| ORECCHIETTE | evaluated unbounded | evaluated unbounded | lines no longer open: ['fresh rosemary branches', 'mixed wild or cultivated mushrooms']; different recipes calculated (4 before, 4 after, 3 shared): search results or cache, not a code change |
| PAPPARDELLE | evaluated unbounded | evaluated unbounded | code fix: an 'unprepared' bacon/pancetta record is now a raw record; different recipes calculated (1 before, 4 after, 1 shared): search results or cache, not a code change |
| KING SALMON | evaluated bounded | evaluated bounded | different recipes calculated (4 before, 4 after, 3 shared): search results or cache, not a code change |
| PORK CHOP | evaluated unbounded | evaluated bounded | lines no longer open: ['springs fresh thyme']; different recipes calculated (4 before, 4 after, 3 shared): search results or cache, not a code change |

Unranked after, with reasons:
- POLE BEANS: no recipe of this dish could be portioned (no scenario could be portioned (3 without an applicable portion model))
- PUTTANESCA: the estimate has no upper bound: 1 of 1 recipes have no upper bound (foodnetwork.com: pizza dough (missing_fdc_id), castelvetrano (missing_grams), chili (missing_gram)
- SALSICCIA BIANCA: no recipe of this dish could be portioned (no scenario could be portioned (4 without an applicable portion model))
- ORECCHIETTE: the estimate has no upper bound: 4 of 4 recipes have no upper bound (bakedbree.com: chanterelle (missing_grams), wasabi (missing_grams); aboutamom.com: fresh baby spinach
- TALEGGIO SCARPINOCC: no recipe of this dish could be portioned (no scenario could be portioned (4 without an applicable portion model))
- SAFFRON SOPRESE: the estimate has no upper bound: 2 of 2 recipes have no upper bound (figandoliveplatter.com: mussels escabeche (missing_grams); the-pasta-project.com: sachet saffron powd
- PAPPARDELLE: the estimate has no upper bound: 3 of 3 recipes have no upper bound (aflavorjournal.com: lamb merguez ragu (missing_grams), tomato xo (missing_grams); bigdeliciouslife.co

## The Greyhound (gastropub)

**Before:** Among the 1 dish I could estimate (14 tried; 13 had no usable estimate), lowest saturated fat first: 1) Padron Peppers, about 1.2-3.0 g saturated fat per plate. It's the only dish I could estimate, so this is one figure, not a ranking. Padron Peppers has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

**After:** Among the 1 dish I could estimate (14 tried; 13 had no usable estimate), lowest saturated fat first: 1) Padron Peppers, about 1.2-3.0 g saturated fat per plate. It's the only dish I could estimate, so this is one figure, not a ranking. Padron Peppers has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | PADRON PEPPERS: sat 1.2-3.0 g, chol 0-0 mg (only_estimate) | PADRON PEPPERS: sat 1.2-3.0 g, chol 0-0 mg (only_estimate) |
| #2 |  |  |
| #3 |  |  |

| dish | before | after | why |
|---|---|---|---|
| CRACKLING PIG STICKS | evaluated unbounded | evaluated unbounded | different recipes calculated (2 before, 3 after, 2 shared): search results or cache, not a code change |
| ROASTED HARISSA AUBERGINE | evaluated unbounded | evaluated unbounded | lines no longer open: ['aubergine', 'greek yogurt']; different recipes calculated (4 before, 4 after, 2 shared): search results or cache, not a code change |
| CRISPY SQUID & PRAWNS | evaluated unbounded | evaluated unbounded | lines no longer open: ['Charred Lime & Homemade Sweet Chilli Sauce', 'mixed salad', 'natural yoghurt', 'oil']; different recipes calculated (2 before, 1 after, 1 shared): search results or cache, not a code change |

Unranked after, with reasons:
- CRACKLING PIG STICKS: no recipe of this dish could be portioned (no scenario could be portioned (3 without an applicable portion model))
- SICILIAN OLIVES: no recipe of this dish could be portioned (no scenario could be portioned (1 without an applicable portion model))
- PIGS IN BLANKETS: the estimate has no upper bound: 1 of 1 recipes have no upper bound (bakingamoment.com: Rosemary (missing_grams))
- ROASTED HARISSA AUBERGINE: no recipe of this dish could be portioned (no scenario could be portioned (4 without an applicable portion model))
- THE GREYHOUND SCOTCH EGG: no recipe of this dish could be portioned (no scenario could be portioned (4 without an applicable portion model))
- CRISPY SQUID & PRAWNS: no recipe of this dish could be portioned (no scenario could be portioned (1 without an applicable portion model))
- CAMEMBERT & SAGE CROQUETTES: no recipe of this dish could be portioned (no scenario could be portioned (2 without an applicable portion model))
- CHICKEN & MUSHROOM ARANCINI: no recipe of this dish could be portioned (no scenario could be portioned (4 without an applicable portion model))
- SIRLOIN STEAK 10oz: the estimate has no upper bound: 4 of 4 recipes have no upper bound (cookingwithcurls.com: brown sugar (missing_grams), shallot (missing_grams), roasted garlic-goat chees
- CHICKEN SCHNITZEL: the estimate has no upper bound: 1 of 1 recipes have no upper bound (thepioneerwoman.com: vegetable oil (missing_grams))
- PAN FRIED SEABASS: the estimate has no upper bound: 4 of 4 recipes have no upper bound (carolinescooking.com: anchovy fillets (as_used_not_accepted_for_flesh), capers (missing_grams), Samph
- CONISBEE BUTCHER LAMB & MINT SAUSAGES: the estimate has no upper bound: 1 of 1 recipes have no upper bound (foodnetwork.com: 8-foot hog casing (missing_fdc_id), 8-foot hog casing (missing_fdc_id), frying f)
- TAGLIATELLE CARBONARA: the estimate has no upper bound: 4 of 4 recipes have no upper bound (mandytanner.com: parmigiano reggiano cheese (missing_grams), Wild Mushroom & Asparagus (missing_g; th

## Zuni Cafe

**Before:** Among the 4 dishes I could estimate (13 tried; 9 had no usable estimate), lowest saturated fat first: 1) Wood fire-roasted tomato and eggplant soup, about 0.7-4.7 g saturated fat per plate; 2) Zuni Caesar salad, 2.3-5.7 g; 3) Spaghetti with Gulf shrimp, heirloom tomatoes, basil, garlic,, 1.9-12 g. These ranges overlap, so treat the order as a toss-up. Modeled from published recipes and typical portions, not this kitchen's numbers.

**After:** Among the 4 dishes I could estimate (13 tried; 9 had no usable estimate), lowest saturated fat first: 1) Wood fire-roasted tomato and eggplant soup, about 0.7-3.9 g saturated fat per plate; 2) Zuni Caesar salad, 2.0-5.7 g; 3) Spaghetti with Gulf shrimp, 1.9-12 g. These ranges overlap, so treat the order as a toss-up. Spaghetti with Gulf shrimp may carry up to 376 mg cholesterol. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | Wood fire-roasted tomato and eggplant so: sat 0.7-4.7 g, chol 0-19 mg (close_call, driver parmesan cheese shavings (assumed amount)) | Wood fire-roasted tomato and eggplant so: sat 0.7-3.9 g, chol 0-15 mg (close_call, driver parmesan cheese shavings (assumed amount)) |
| #2 | Zuni Caesar salad‡: sat 2.3-5.7 g, chol 35-95 mg (close_call, driver very fresh large eggs (assumed amount)) | Zuni Caesar salad: sat 2.0-5.7 g, chol 25-95 mg (close_call, driver very fresh large eggs (assumed amount)) |
| #3 | Spaghetti with Gulf shrimp, heirloom tom: sat 1.9-11.9 g, chol 4-376 mg (close_call) | Spaghetti with Gulf shrimp, heirloom tom: sat 1.9-11.9 g, chol 4-376 mg (close_call) |

| dish | before | after | why |
|---|---|---|---|
| House-cured anchovies with celery, Parmigiano | evaluated unbounded | evaluated unbounded | lines no longer open: ['anchovy filets', 'celery']; different recipes calculated (4 before, 4 after, 3 shared): search results or cache, not a code change |
| Zuni Caesar salad‡ | evaluated bounded |  | absent from the after run (menu read differently) |
| Zuni Caesar salad |  | evaluated bounded | new on the after run (menu read differently or newly selected) |
| Yellowfin tuna grilled rare all'acqua di mare |  | evaluated unbounded | new on the after run (menu read differently or newly selected) |
| Yellowfin tuna‡ grilled rare all'acqua di mar | evaluated unbounded |  | absent from the after run (menu read differently) |

Unranked after, with reasons:
- Marinated olives: no recipe of this dish could be portioned (no scenario could be portioned (4 without an applicable portion model))
- Shoestring potatoes: no recipe of this dish could be portioned (no scenario could be portioned (4 without an applicable portion model))
- House-cured anchovies with celery, Parmigiano-Reggiano, and coquillo olives: no recipe of this dish could be portioned (no scenario could be portioned (4 without an applicable portion model))
- Fuyu persimmon and roasted beet "carpaccio" with Laychee goat cheese, tender herbs, and Meyer lemon-pistachio aillade: no recipe of this dish could be portioned (no scenario could be portioned (3 without an applicable portion model))
- Garden lettuce salad with Sungold tomatoes, Alpha Tolman cheese, chapons, and passion fruit vinaigrette: no recipe of this dish could be portioned (no scenario could be portioned (4 without an applicable portion model))
- Pizza with Wagon Wheel cheese, soppressata, wild nettles, red onion, and Boont Corners sheep cheese: the estimate has no upper bound: 1 of 1 recipes have no upper bound (epicurious.com: unbleached all-purpose flour (missing_grams), cornmeal for sprinkling the baking)
- Yellowfin tuna grilled rare all'acqua di mare with Manila clams, mussels, sprouting cauliflower, string beans, a slow-cooked Early Girl tomato, and aïoli: no recipe of this dish could be portioned (no scenario could be portioned (2 without an applicable portion model))
- Steak frites: Stemple Creek Ranch bavette steak with pommes frites, Padrón peppers, avocado, and chimichurri: the estimate has no upper bound: 3 of 3 recipes have no upper bound (cooking.nytimes.com: steak-cut frozen fries (preparation_unresolved); delish.com: canola oil (missing
- Chicken for two roasted in the wood-fired brick oven; warm bread salad with scallions, garlic, bitter greens, dried currants, and pine nuts: the estimate has no upper bound: 2 of 2 recipes have no upper bound (fostersmarket.com: chunks of rustic sourdough bread (missing_grams), salad (missing_grams), toasted; 

## Seafood chalkboard

**Before:** Among the 4 dishes I could estimate (7 tried; 3 had no usable estimate), lowest saturated fat first: 1) Ocean Trout / Tuna Poke Salad, about 2.0-7.3 g saturated fat per plate; 2) Crudo Of Swordfish, 2.5-15 g; 3) Snapper, 4.7-16 g. These ranges overlap, so treat the order as a toss-up. Ocean Trout / Tuna Poke Salad cholesterol about 18-43 mg. Modeled from published recipes and typical portions, not this kitchen's numbers.

**After:** Among the 4 dishes I could estimate (7 tried; 3 had no usable estimate), lowest saturated fat first: 1) Ocean Trout / Tuna Poke Salad, about 2.0-7.1 g saturated fat per plate; 2) Crudo Of Swordfish, 2.5-13 g; 3) Snapper, 4.7-15 g. These ranges overlap, so treat the order as a toss-up. Ocean Trout / Tuna Poke Salad cholesterol about 18-43 mg. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | OCEAN TROUT / TUNA POKE SALAD: sat 2.0-7.3 g, chol 18-43 mg (close_call) | OCEAN TROUT / TUNA POKE SALAD: sat 2.0-7.1 g, chol 18-43 mg (close_call) |
| #2 | CRUDO OF SWORDFISH: sat 2.5-15.2 g, chol 33-113 mg (close_call, driver FETTA LEMON PANGRATTA (assumed amount)) | CRUDO OF SWORDFISH: sat 2.5-13.2 g, chol 33-99 mg (close_call) |
| #3 | SNAPPER: sat 4.7-15.7 g, chol 55-140 mg (close_call) | SNAPPER: sat 4.7-15.4 g, chol 55-132 mg (close_call) |

| dish | before | after | why |
|---|---|---|---|
| OCEAN TROUT | evaluated bounded | evaluated bounded | code fix: an 'unprepared' bacon/pancetta record is now a raw record; lines no longer open: ['trout roe']; different recipes calculated (3 before, 4 after, 1 shared): search results or cache, not a code change |
| COBIA | evaluated unbounded | evaluated unbounded | lines no longer open: ['cobia fillets']; different recipes calculated (2 before, 4 after, 2 shared): search results or cache, not a code change |
| SNAPPER | evaluated bounded | evaluated bounded | lines no longer open: ['dry bay', 'red wine vinegar', 'scotch bonnet chile', 'yellow onion']; different recipes calculated (4 before, 4 after, 1 shared): search results or cache, not a code change |

Unranked after, with reasons:
- CRUMBED WHITING: the estimate has no upper bound: 2 of 2 recipes have no upper bound (pattysaveurs.com: frying fat (the recipe fries but lists no oil, butter or fat) (missing_fdc_id); sav
- CHILLED MOOLOOLABA PRAWNS: no recipe of this dish could be portioned (no scenario could be portioned (2 without an applicable portion model))
- COBIA: the estimate has no upper bound: 2 of 2 recipes have no upper bound (mydeliciousblog.com: toasted pepitas or sunflower seeds (missing_grams), fresh lemon or lime wedges f
