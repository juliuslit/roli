# MVP before/after (local-testing milestone, 2026-11-04)

Before = the Phase 3 runs of 2026-11-04 (menu order selection, no budget, old wording); after = the same photos through the fixed code.

| menu | run | menu items | candidates | selected | evaluated | ranked | unranked | no recipes | errors | skipped | budget-stopped | search credits | model calls | USDA requests | rate-limit waits | model $ | total s | words |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Flour + Water | before 20261104-010950-f71751 | 19 |  |  | 16 | 5 | 11 | 1 | 0 |  |  | 0 | 135 | 711 | 127 | 0.3341 | 523.2 | 75 |
| Flour + Water | after 20261104-040940-dc2383 | 19 | 17 | 14 | 13 | 5 | 8 | 1 | 0 | 3 | 0 | 0 | 33 | 409 | 4 | 0.0559 | 116.8 | 74 |
| The Greyhound (gastropub) | before 20261104-012103-375d1b | 38 |  |  | 12 | 1 | 11 | 0 | 0 |  |  | 24 | 84 | 447 | 72 | 0.1847 | 339.9 | 49 |
| The Greyhound (gastropub) | after 20261104-041137-b7cf5b | 38 | 14 | 14 | 14 | 1 | 13 | 0 | 0 | 0 | 0 | 0 | 31 | 202 | 36 | 0.0592 | 117.3 | 62 |
| Zuni Cafe | before 20261104-012643-2ef4a1 | 71 |  |  | 9 | 2 | 7 | 1 | 2 |  |  | 20 | 62 | 179 | 123 | 0.1357 | 290.0 | 79 |
| Zuni Cafe | after 20261104-041334-aa2845 | 71 | 13 | 13 | 13 | 4 | 9 | 0 | 0 | 0 | 0 | 5 | 24 | 105 | 41 | 0.0604 | 115.8 | 70 |
| Seafood chalkboard (before = first run today, pass 1) | before 20261104-034931-49e48b | 10 | 8 | 8 | 8 | 2 | 6 | 0 | 0 | 0 | 0 | 8 | 62 | 179 | 132 | 0.1504 | 234.6 | 62 |
| Seafood chalkboard (before = first run today, pass 1) | after 20261104-041530-432689 | 9 | 7 | 7 | 7 | 4 | 3 | 0 | 0 | 0 | 0 | 5 | 20 | 89 | 56 | 0.0364 | 72.6 | 73 |

## Flour + Water

**Before:** Lowest saturated fat on this menu, by our estimate: 1) Bluefin Crudo (about 0.5-1.6 g saturated fat per plate, close call); 2) Heirloom Tomatoes (about 0.4-2.1 g saturated fat per plate, tentative); 3) Little Gem Lettuces (about 4.4-8.6 g saturated fat per plate, close call). Bluefin Crudo carries about 17-115 mg cholesterol. Figures are modeled from published recipes and typical restaurant portions, not this kitchen's own numbers. 12 of 17 dishes could not be estimated.

**After:** Among the 5 dishes I could estimate (14 tried; 9 had no usable estimate; 3 not tried), lowest saturated fat first: 1) Heirloom Tomatoes, about 0.4-2.4 g saturated fat per plate; 2) Bluefin Crudo, 0.5-4.3 g; 3) Little Gem Lettuces, 4.4-8.6 g. Heirloom Tomatoes and Bluefin Crudo overlap, so treat that order as a toss-up. Heirloom Tomatoes has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | BLUEFIN CRUDO: sat 0.5-1.6 g, chol 17-115 mg (close_call) | HEIRLOOM TOMATOES: sat 0.4-2.4 g, chol 0-0 mg (close_call) |
| #2 | HEIRLOOM TOMATOES: sat 0.4-2.1 g, chol 0-0 mg (tentative) | BLUEFIN CRUDO: sat 0.5-4.3 g, chol 17-115 mg (tentative, driver bottarga (external evidence)) |
| #3 | LITTLE GEM LETTUCES: sat 4.4-8.6 g, chol 4-13 mg (close_call) | LITTLE GEM LETTUCES: sat 4.4-8.6 g, chol 4-13 mg (close_call, driver pecorino sardo (assumed amount)) |

| dish | before | after | why |
|---|---|---|---|
| KOSHIHIKARI ARANCINI | evaluated unbounded | skipped | selection: evaluated -> skipped |
| CORN CAPPELLETTI | evaluated unbounded | skipped | selection: evaluated -> skipped |
| SAFFRON SOPRESE | evaluated unbounded | evaluated unbounded | lines no longer open: ['fresh egg pasta ribbons']; different recipes calculated (3 before, 2 after, 2 shared): search results or cache, not a code change |
| ORECCHIETTE | evaluated unbounded | evaluated unbounded | lines no longer open: ['fresh oregano', 'salt-packed capers', 'turnip']; different recipes calculated (4 before, 4 after, 3 shared): search results or cache, not a code change |
| DUCK TRIANGOLI | evaluated unbounded | skipped | selection: evaluated -> skipped |
| PAPPARDELLE | evaluated unbounded | evaluated unbounded | lines no longer open: ['pappardelle pasta', 'peperoncino flakes', 'shallots', 'strips bacon']; different recipes calculated (4 before, 1 after, 1 shared): search results or cache, not a code change |
| KING SALMON | evaluated bounded | evaluated bounded | different recipes calculated (4 before, 4 after, 3 shared): search results or cache, not a code change |
| PORK CHOP | evaluated unbounded | evaluated unbounded | code fix: new weights row(s) ['W39'] filled lines that were open; different recipes calculated (4 before, 4 after, 3 shared): search results or cache, not a code change |

Unranked after, with reasons:
- POLE BEANS: no recipe of this dish could be portioned (no scenario could be portioned (4 without an applicable portion model))
- PUTTANESCA: the estimate has no upper bound: 1 of 1 recipes have no upper bound (foodnetwork.com: pizza dough (missing_fdc_id), castelvetrano (missing_grams), chili (missing_gram)
- SALSICCIA BIANCA: no recipe of this dish could be portioned (no scenario could be portioned (4 without an applicable portion model))
- ORECCHIETTE: the estimate has no upper bound: 4 of 4 recipes have no upper bound (bakedbree.com: chanterelle (missing_grams), wasabi (missing_grams); aboutamom.com: fresh baby spinach
- TALEGGIO SCARPINOCC: no recipe of this dish could be portioned (no scenario could be portioned (4 without an applicable portion model))
- SAFFRON SOPRESE: the estimate has no upper bound: 2 of 2 recipes have no upper bound (figandoliveplatter.com: mussels escabeche (missing_grams); the-pasta-project.com: sachet saffron powd
- PAPPARDELLE: the estimate has no upper bound: 1 of 1 recipes have no upper bound (cooking.nytimes.com: rabbit (missing_grams), anchovy (as_used_not_accepted_for_flesh), tomato paste (
- PORK CHOP: the estimate has no upper bound: 2 of 4 recipes have no upper bound (foodnetwork.com: pomegranate marinade (missing_grams); foodnetwork.com: whole (missing_grams), sautee

## The Greyhound (gastropub)

**Before:** Lowest saturated fat on this menu, by our estimate: 1) Padron Peppers (about 1.2-3.1 g saturated fat per plate). Padron Peppers carries about 0-0 mg cholesterol. Figures are modeled from published recipes and typical restaurant portions, not this kitchen's own numbers. 11 of 12 dishes could not be estimated.

**After:** Among the 1 dish I could estimate (14 tried; 13 had no usable estimate), lowest saturated fat first: 1) Padron Peppers, about 1.2-3.0 g saturated fat per plate. It's the only dish I could estimate, so this is one figure, not a ranking. Padron Peppers has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | PADRON PEPPERS: sat 1.2-3.1 g, chol 0-0 mg (well_supported) | PADRON PEPPERS: sat 1.2-3.0 g, chol 0-0 mg (only_estimate) |
| #2 |  |  |
| #3 |  |  |

| dish | before | after | why |
|---|---|---|---|
| PADRON PEPPERS | evaluated bounded | evaluated bounded | different recipes calculated (4 before, 4 after, 3 shared): search results or cache, not a code change |
| PIGS IN BLANKETS | evaluated unbounded | evaluated unbounded | different recipes calculated (4 before, 4 after, 3 shared): search results or cache, not a code change |
| ROASTED HARISSA AUBERGINE | evaluated unbounded | evaluated unbounded | lines no longer open: ['/30ml raw organic honey', 'Toasted Almonds', 'a bunch of fresh flat-leaf parsley', 'chinese or japanese eggplants']; different recipes calculated (4 before, 4 after, 1 shared): search results or cache, not a code change |
| HOUSE BAKED BREAD | evaluated unbounded | excluded | selection: evaluated -> excluded |
| CRISPY SQUID & PRAWNS | evaluated unbounded | evaluated unbounded | different recipes calculated (1 before, 2 after, 1 shared): search results or cache, not a code change |
| PAN FRIED SEABASS | not_evaluated | evaluated unbounded | selection: not_evaluated -> evaluated |
| CONISBEE BUTCHER LAMB & MINT SAUSAGES | not_evaluated | evaluated unbounded | selection: not_evaluated -> evaluated |
| TAGLIATELLE CARBONARA | not_evaluated | evaluated unbounded | selection: not_evaluated -> evaluated |

Unranked after, with reasons:
- CRACKLING PIG STICKS: no recipe of this dish could be portioned (no scenario could be portioned (2 without an applicable portion model))
- SICILIAN OLIVES: no recipe of this dish could be portioned (no scenario could be portioned (1 without an applicable portion model))
- PIGS IN BLANKETS: the estimate has no upper bound: 1 of 1 recipes have no upper bound (bakingamoment.com: Rosemary (missing_grams))
- ROASTED HARISSA AUBERGINE: no recipe of this dish could be portioned (no scenario could be portioned (4 without an applicable portion model))
- THE GREYHOUND SCOTCH EGG: no recipe of this dish could be portioned (no scenario could be portioned (4 without an applicable portion model))
- CRISPY SQUID & PRAWNS: the estimate has no upper bound: 1 of 1 recipes have no upper bound (greatbritishchefs.com: sparkling water (missing_fdc_id), oil (missing_grams), natural yoghurt (missin
- CAMEMBERT & SAGE CROQUETTES: no recipe of this dish could be portioned (no scenario could be portioned (2 without an applicable portion model))
- CHICKEN & MUSHROOM ARANCINI: no recipe of this dish could be portioned (no scenario could be portioned (4 without an applicable portion model))
- SIRLOIN STEAK 10oz: the estimate has no upper bound: 4 of 4 recipes have no upper bound (cookingwithcurls.com: brown sugar (missing_grams), shallot (missing_grams), roasted garlic-goat chees
- CHICKEN SCHNITZEL: the estimate has no upper bound: 1 of 1 recipes have no upper bound (thepioneerwoman.com: vegetable oil (missing_grams))
- PAN FRIED SEABASS: the estimate has no upper bound: 4 of 4 recipes have no upper bound (carolinescooking.com: anchovy fillets (as_used_not_accepted_for_flesh), capers (missing_grams), Samph
- CONISBEE BUTCHER LAMB & MINT SAUSAGES: the estimate has no upper bound: 1 of 1 recipes have no upper bound (foodnetwork.com: 8-foot hog casing (missing_fdc_id), 8-foot hog casing (missing_fdc_id), frying f)
- TAGLIATELLE CARBONARA: the estimate has no upper bound: 4 of 4 recipes have no upper bound (mandytanner.com: parmigiano reggiano cheese (missing_grams), Wild Mushroom & Asparagus (missing_g; th

## Zuni Cafe

**Before:** Lowest saturated fat on this menu, by our estimate: 1) Wood Fire-Roasted Tomato And Eggplant Soup With Mint, Urfa Pepper, And Charmoula (about 0.6-4.7 g saturated fat per plate); 2) Stemple Creek Ranch Ribeye Steak (Served With The Above Accompaniments) (about 11-28 g saturated fat per plate). Wood Fire-Roasted Tomato And Eggplant Soup With Mint, Urfa Pepper, And Charmoula carries about 0-19 mg cholesterol. Figures are modeled from published recipes and typical restaurant portions, not this kitchen's own numbers.

**After:** Among the 4 dishes I could estimate (13 tried; 9 had no usable estimate), lowest saturated fat first: 1) Wood fire-roasted tomato and eggplant soup, about 0.7-4.7 g saturated fat per plate; 2) Zuni Caesar salad, 2.3-5.7 g; 3) Spaghetti with Gulf shrimp, heirloom tomatoes, basil, garlic,, 1.9-12 g. These ranges overlap, so treat the order as a toss-up. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | Wood fire-roasted tomato and eggplant so: sat 0.6-4.7 g, chol 0-19 mg (well_supported) | Wood fire-roasted tomato and eggplant so: sat 0.7-4.7 g, chol 0-19 mg (close_call, driver parmesan cheese shavings (assumed amount)) |
| #2 | Stemple Creek Ranch ribeye steak (served: sat 11.4-28.2 g, chol 92-204 mg (well_supported) | Zuni Caesar salad‡: sat 2.3-5.7 g, chol 35-95 mg (close_call, driver very fresh large eggs (assumed amount)) |
| #3 |  | Spaghetti with Gulf shrimp, heirloom tom: sat 1.9-11.9 g, chol 4-376 mg (close_call) |

| dish | before | after | why |
|---|---|---|---|
| House-cured anchovies with celery, Parmigiano | evaluated unbounded | evaluated unbounded | lines no longer open: ['fresh anchovies', 'watermelon radish']; different recipes calculated (4 before, 4 after, 3 shared): search results or cache, not a code change |
| Zuni Caesar salad‡ |  | evaluated bounded | new on the after run (menu read differently or newly selected) |
| Zuni Caesar salad | error |  | absent from the after run (menu read differently) |
| Pizza with Wagon Wheel cheese, soppressata, w | error | evaluated unbounded | error path: APIStatusError: Error code: 402 - This request would exceed your available credi |
| Spaghetti with Gulf shrimp, heirloom tomatoes | no_recipes unbounded | evaluated bounded | different recipes calculated (0 before, 4 after, 0 shared): search results or cache, not a code change |
| Yellowfin tuna‡ grilled rare all'acqua di mar |  | evaluated unbounded | new on the after run (menu read differently or newly selected) |
| Yellowfin tuna grilled rare all'acqua di mare | evaluated unbounded |  | absent from the after run (menu read differently) |
| Chicken for two roasted in the wood-fired bri | not_evaluated | evaluated unbounded | selection: not_evaluated -> evaluated |

Unranked after, with reasons:
- Marinated olives: no recipe of this dish could be portioned (no scenario could be portioned (4 without an applicable portion model))
- Shoestring potatoes: no recipe of this dish could be portioned (no scenario could be portioned (4 without an applicable portion model))
- House-cured anchovies with celery, Parmigiano-Reggiano, and coquillo olives: no recipe of this dish could be portioned (no scenario could be portioned (4 without an applicable portion model))
- Fuyu persimmon and roasted beet "carpaccio" with Laychee goat cheese, tender herbs, and Meyer lemon-pistachio aillade: no recipe of this dish could be portioned (no scenario could be portioned (3 without an applicable portion model))
- Garden lettuce salad with Sungold tomatoes, Alpha Tolman cheese, chapons, and passion fruit vinaigrette: no recipe of this dish could be portioned (no scenario could be portioned (4 without an applicable portion model))
- Pizza with Wagon Wheel cheese, soppressata, wild nettles, red onion, and Boont Corners sheep cheese: the estimate has no upper bound: 1 of 1 recipes have no upper bound (epicurious.com: unbleached all-purpose flour (missing_grams), cornmeal for sprinkling the baking)
- Yellowfin tuna‡ grilled rare all'acqua di mare with Manila clams, mussels, sprouting cauliflower, string beans, a slow-cooked Early Girl tomato, and aïoli‡: no recipe of this dish could be portioned (no scenario could be portioned (1 without an applicable portion model))
- Steak frites: Stemple Creek Ranch bavette steak with pommes frites, Padrón peppers, avocado, and chimichurri: the estimate has no upper bound: 3 of 3 recipes have no upper bound (cooking.nytimes.com: steak-cut frozen fries (preparation_unresolved); delish.com: canola oil (missing
- Chicken for two roasted in the wood-fired brick oven; warm bread salad with scallions, garlic, bitter greens, dried currants, and pine nuts: the estimate has no upper bound: 3 of 3 recipes have no upper bound (fostersmarket.com: chunks of rustic sourdough bread (missing_grams), salad (missing_fdc_id), toaste; 

## Seafood chalkboard (before = first run today, pass 1)

**Before:** Among the 2 dishes I could estimate (8 tried; 6 had no usable estimate), lowest saturated fat first: 1) Watermelon, about 1.7-4.2 g saturated fat per plate; 2) Ocean Trout / Tuna Poke Salad, 2.0-7.3 g. These ranges overlap, so treat the order as a toss-up. Watermelon cholesterol about 6-15 mg. Modeled from published recipes and typical portions, not this kitchen's numbers.

**After:** Among the 4 dishes I could estimate (7 tried; 3 had no usable estimate), lowest saturated fat first: 1) Ocean Trout / Tuna Poke Salad, about 2.0-7.3 g saturated fat per plate; 2) Crudo Of Swordfish, 2.5-15 g; 3) Snapper, 4.7-16 g. These ranges overlap, so treat the order as a toss-up. Ocean Trout / Tuna Poke Salad cholesterol about 18-43 mg. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | WATERMELON, FETTA, MINT ALMOND, SALSA VE: sat 1.7-4.2 g, chol 6-15 mg (close_call) | OCEAN TROUT / TUNA POKE SALAD: sat 2.0-7.3 g, chol 18-43 mg (close_call) |
| #2 | OCEAN TROUT / TUNA POKE SALAD: sat 2.0-7.3 g, chol 18-43 mg (well_supported) | CRUDO OF SWORDFISH: sat 2.5-15.2 g, chol 33-113 mg (close_call, driver FETTA LEMON PANGRATTA (assumed amount)) |
| #3 |  | SNAPPER: sat 4.7-15.7 g, chol 55-140 mg (close_call) |

| dish | before | after | why |
|---|---|---|---|
| CRUDO OF SWORDFISH | evaluated unbounded | evaluated bounded | code fix: new weights row(s) ['W34'] filled lines that were open |
| OCEAN TROUT | evaluated unbounded | evaluated bounded | code fix: new weights row(s) ['W34', 'W39'] filled lines that were open; different recipes calculated (4 before, 3 after, 1 shared): search results or cache, not a code change |
| SNAPPER | evaluated unbounded | evaluated bounded | code fix: new weights row(s) ['W34', 'W39'] filled lines that were open; different recipes calculated (4 before, 4 after, 1 shared): search results or cache, not a code change |
| WATERMELON, FETTA, MINT ALMOND, SALSA VERDE S | evaluated bounded |  | absent from the after run (menu read differently) |

Unranked after, with reasons:
- CRUMBED WHITING: the estimate has no upper bound: 2 of 2 recipes have no upper bound (pattysaveurs.com: frying fat (the recipe fries but lists no oil, butter or fat) (missing_fdc_id); sav
- CHILLED MOOLOOLABA PRAWNS: no recipe of this dish could be portioned (no scenario could be portioned (2 without an applicable portion model))
- COBIA: no recipe of this dish could be portioned (no scenario could be portioned (2 without an applicable portion model))

## Notes added after the comparison was generated

- Three passes ran today; this file compares the Phase 3 runs with the FINAL pass. Intermediate passes: `mvp_eval_2026-11-04_local.*` (pass 1) and
  `mvp_eval_2026-11-04_local_v2.*` (pass 2). Pass 2 exposed two material errors that the final code fixes: Flour + Water "Salsiccia bianca" at 47-111 g
  saturated fat (a deep-dish sausage pizza recipe treated as the Neapolitan unit, with a second cheese added per plate) and the seafood chalkboard's
  "Crumbed whiting" first at 0.8-1.8 g (a breaded recipe with no fat line read as complete). Both dishes are now honestly unranked.
- The Zuni run's saved text has a double comma in the spaghetti name and no cholesterol notice; the final wording (re-rendered from the same ranking) is in
  `CHECKPOINT_3A_local.md` section 3.
- Cost and time differences are mostly cache warmth, not code; the ranked-count changes are code (Zuni +2) or structure (Greyhound unchanged).
- The seafood "before" is pass 1 of today (the Phase 3 run never happened: credit), so its before/after is code-only with warm caches on both sides.
