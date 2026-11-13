# MVP before/after: Checkpoint 3D runs against 3E pass A

Before: the Checkpoint 3D runs. The Greyhound and seafood chalkboard ones were made on pass-2 code, which still zeroed menu-only lines with no tag (SPEC 12.9.1). After: pass A on the final 3E code.

| menu | run | menu items | candidates | selected | evaluated | ranked | unranked | no recipes | errors | skipped | budget-stopped | flagged | USDA-unavailable | search credits | model calls | USDA requests | rate-limit waits | USDA left after | model $ | total s | words |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Flour + Water | before 20261105-225651-aa66fa | 19 | 17 | 14 | 12 | 6 | 6 | 2 | 0 | 3 | 0 | 0 | 0 | 0 | 41 | 12 | 32 | 2600 | 0.1452 | 163.2 | 74 |
| Flour + Water | after 20261106-134104-7e4cd4 | 19 | 17 | 14 | 12 | 6 | 6 | 2 | 0 | 3 | 0 | 0 | 0 | 0 | 43 | 3 | 28 | 3557 | 0.1208 | 168.2 | 74 |
| The Greyhound (gastropub) | before 20261105-224308-ac4093 | 38 | 15 | 14 | 12 | 5 | 9 | 0 | 0 | 1 | 0 | 2 | 0 | 0 | 43 | 12 | 74 | 2529 | 0.1518 | 174.1 | 78 |
| The Greyhound (gastropub) | after 20261106-134352-2c7e93 | 38 | 15 | 14 | 13 | 5 | 9 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 41 | 8 | 49 | 3550 | 0.1299 | 171.9 | 72 |
| Zuni Cafe | before 20261105-225157-850782 | 71 | 13 | 13 | 13 | 7 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 39 | 10 | 19 | 2572 | 0.1601 | 182.4 | 72 |
| Zuni Cafe | after 20261106-134644-b10521 | 71 | 13 | 13 | 13 | 7 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 37 | 0 | 70 | 3550 | 0.1388 | 164.2 | 72 |
| Seafood chalkboard | before 20261105-224837-9656cc | 9 | 7 | 7 | 7 | 5 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 21 | 5 | 108 | 2552 | 0.0731 | 78.2 | 74 |
| Seafood chalkboard | after 20261106-134928-48ec86 | 9 | 7 | 7 | 7 | 5 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 23 | 23 | 90 | 3533 | 0.0673 | 76.8 | 74 |

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
| POLE BEANS | evaluated unbounded | evaluated unbounded | lines no longer open: ['frying fat (the recipe fries but lists no oil, butter or fat)', 'lemon zested']; grading changed on 4 page(s), e.g. bbcgoodfood.com: variant/high -> different/low (preparation similar -> different; hard exclusion None -> hard_exclusion:dish_type_different) |
| TALEGGIO SCARPINOCC | evaluated unbounded | skipped | selection: evaluated -> skipped |
| DUCK TRIANGOLI | skipped | evaluated unbounded | selection: skipped -> evaluated |
| PORK CHOP | evaluated bounded | evaluated bounded | lines no longer open: ['brown sugar']; grading changed on 1 page(s), e.g. recipetineats.com: variant/high -> variant/low (preparation similar -> different; hard exclusion None -> hard_exclusion:preparation_different) |

Unranked after, with reasons:
- POLE BEANS: the estimate has no upper bound: 1 of 1 recipes have no upper bound (cooking.nytimes.com: miso bagna cauda (missing_grams))
- PUTTANESCA: the estimate has no upper bound: 1 of 1 recipes have no upper bound (foodnetwork.com: castelvetrano (missing_grams), chili (missing_grams), boquerones (missing_grams))
- SALSICCIA BIANCA: no recipe of this dish could be portioned (no scenario could be portioned (6 without an applicable portion model))
- ORECCHIETTE: the estimate has no upper bound: 4 of 4 recipes have no upper bound (bakedbree.com: chanterelle (missing_grams), wasabi (missing_grams); aboutamom.com: fresh baby spinach
- DUCK TRIANGOLI: no recipe of this dish could be portioned (no scenario could be portioned (1 without an applicable portion model))
- PAPPARDELLE: the estimate has no upper bound: 3 of 3 recipes have no upper bound (aflavorjournal.com: lamb merguez ragu (missing_grams), tomato xo (missing_grams); bigdeliciouslife.co

## The Greyhound (gastropub)

**Before:** Among the 5 dishes I could estimate (14 tried; 9 had no usable estimate; 1 not tried), lowest saturated fat first: 1) Padron Peppers, about 0.6-1.9 g saturated fat per plate; 2) Crispy Squid & Prawns, 1.8-3.5 g; 3) Pan Fried Seabass, 8.7-23 g. Padron Peppers and Crispy Squid & Prawns overlap, so treat that order as a toss-up. Padron Peppers has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

**After:** Among the 5 dishes I could estimate (14 tried; 9 had no usable estimate; 1 not tried), lowest saturated fat first: 1) Sicilian Olives, about 1.0-3.0 g saturated fat per plate; 2) Padron Peppers, 0.6-4.0 g; 3) Crispy Squid & Prawns, 1.8-3.5 g. These ranges overlap, so treat the order as a toss-up. Sicilian Olives has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | PADRON PEPPERS: sat 0.6-1.9 g, chol 0-0 mg (close_call) | SICILIAN OLIVES: sat 1.0-3.0 g, chol 0-0 mg (close_call) |
| #2 | CRISPY SQUID & PRAWNS: sat 1.8-3.5 g, chol 132-263 mg (tentative) | PADRON PEPPERS: sat 0.6-4.0 g, chol 0-0 mg (close_call) |
| #3 | PAN FRIED SEABASS: sat 8.7-23.2 g, chol 68-158 mg (close_call, driver Seaweed Butter (assumed amount)) | CRISPY SQUID & PRAWNS: sat 1.8-3.5 g, chol 132-263 mg (tentative) |

| dish | before | after | why |
|---|---|---|---|
| SICILIAN OLIVES | flagged bounded | evaluated bounded | reference check: flagged -> evaluated; code fix: new weights row(s) ['W57'] filled lines that were open |
| PIGS IN BLANKETS | evaluated bounded | evaluated bounded | grading changed on 1 page(s), e.g. thekitchn.com: variant/high -> variant/low (preparation similar -> different; hard exclusion None -> hard_exclusion:preparation_different) |
| ROASTED HARISSA AUBERGINE | evaluated unbounded | evaluated unbounded | lines no longer open: ['harissa paste', 'thick natural yoghurt or greek yoghurt', 'tin chopped tomatoes']; grading changed on 4 page(s), e.g. anotherfoodblogger.com: same/high -> same/medium (course portion same -> different) |
| SIRLOIN STEAK | evaluated unbounded |  | absent from the after run (menu read differently) |
| SIRLOIN STEAK 10oz |  | evaluated unbounded | new on the after run (menu read differently or newly selected) |
| PAN FRIED SEABASS | evaluated bounded | evaluated unbounded | lines no longer open: ['unsalted butter']; grading changed on 4 page(s), e.g. carolinescooking.com: variant/low -> variant/high (preparation different -> similar; hard exclusion hard_exclusion:preparation_different -> None) |

Unranked after, with reasons:
- CRACKLING PIG STICKS: no recipe of this dish could be portioned (no scenario could be portioned (3 without an applicable portion model))
- ROASTED HARISSA AUBERGINE: no recipe of this dish could be portioned (no scenario could be portioned (8 without an applicable portion model))
- THE GREYHOUND SCOTCH EGG: the estimate has no upper bound: 2 of 2 recipes have no upper bound (catwillmadeit.com: canola/vegetable oil (missing_grams), Burnt Apple Puree (missing_grams), Crackli; 
- CAMEMBERT & SAGE CROQUETTES: no recipe of this dish could be portioned (no scenario could be portioned (2 without an applicable portion model))
- SIRLOIN STEAK 10oz: the estimate has no upper bound: 4 of 4 recipes have no upper bound (cookingwithcurls.com: brown sugar (missing_grams), shallot (missing_grams), Koffmann's Hand Cut Chips
- PAN FRIED SEABASS: the estimate has no upper bound: 4 of 4 recipes have no upper bound (carolinescooking.com: anchovy fillets (as_used_not_accepted_for_flesh), capers (missing_grams), Samph
- CONISBEE BUTCHER LAMB & MINT SAUSAGES: the estimate has no upper bound: 1 of 1 recipes have no upper bound (foodnetwork.com: 8-foot hog casing (missing_fdc_id), 8-foot hog casing (missing_fdc_id), frying f)
- TAGLIATELLE CARBONARA: the estimate has no upper bound: 4 of 4 recipes have no upper bound (mandytanner.com: Wild Mushroom & Asparagus (missing_grams), frying fat (the recipe fries but list; th
- CORNISH FISH & CHIPS: our estimate disagrees with published figures for this kind of dish

Flags after:
- closed: SICILIAN OLIVES (PR13): every check that may flag now passes: per_100g 2.681 vs 1.7-2.8
- open: CORNISH FISH & CHIPS (PR15, per_plate (vegetable oil); Roli's middle 8.477 vs published 2-5.2; top contributors: CHIPS: frying fat, Vegetable oil, NFS / CHIPS: fry 10.93 g (0.58); CORNISH FISH: frying fat, Vegetable oil, NFS / COR 5.95 g (0.32); Mushy Peas 0.85 g (0.05))

Reference checks after:
- SICILIAN OLIVES (PR13): no failing check
  - per_plate: Roli's middle 2.011 vs published 1.4-1.4, 1 independent; shown only
  - per_100g: Roli's middle 2.681 vs published 1.7-2.8, 5 independent; passed
- CORNISH FISH & CHIPS (PR15): flagged
  - per_plate: Roli's middle 18.797 vs published 10.249-22.8, 3 independent; passed
  - per_plate (beef dripping): Roli's middle 26.312 vs published 35.6-35.6, 1 independent; shown only
  - per_plate (vegetable oil): Roli's middle 8.477 vs published 2-5.2, 2 independent; FAILED above

## Zuni Cafe

**Before:** Among the 7 dishes I could estimate (13 tried; 6 had no usable estimate), lowest saturated fat first: 1) Marinated olives, about 1.3-3.3 g saturated fat per plate; 2) Wood fire-roasted tomato and eggplant soup, 0.7-3.9 g; 3) Garden lettuce salad, 0.3-5.4 g. These ranges overlap, so treat the order as a toss-up. Marinated olives has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

**After:** Among the 7 dishes I could estimate (13 tried; 6 had no usable estimate), lowest saturated fat first: 1) Marinated olives, about 0.7-4.0 g saturated fat per plate; 2) Wood fire-roasted tomato and eggplant soup, 0.7-3.9 g; 3) Garden lettuce salad, 0.3-5.4 g. These ranges overlap, so treat the order as a toss-up. Marinated olives has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | Marinated olives: sat 1.3-3.3 g, chol 0-0 mg (close_call) | Marinated olives: sat 0.7-4.0 g, chol 0-0 mg (close_call) |
| #2 | Wood fire-roasted tomato and eggplant so: sat 0.7-3.9 g, chol 2-15 mg (close_call, driver parmesan cheese shavings (assumed amount)) | Wood fire-roasted tomato and eggplant so: sat 0.7-3.9 g, chol 2-15 mg (close_call, driver parmesan cheese shavings (assumed amount)) |
| #3 | Garden lettuce salad with Sungold tomato: sat 0.3-5.4 g, chol 0-17 mg (close_call) | Garden lettuce salad with Sungold tomato: sat 0.3-5.4 g, chol 0-17 mg (close_call) |

| dish | before | after | why |
|---|---|---|---|
| Shoestring potatoes | evaluated bounded | evaluated bounded | lines no longer open: ['avocado oil', 'ketchup']; grading changed on 2 page(s), e.g. foodnetwork.com: same/high -> variant/high |
| House-cured anchovies with celery, Parmigiano | evaluated unbounded | evaluated unbounded | grading changed on 2 page(s), e.g. epicurious.com: different/low -> variant/high (preparation different -> similar; hard exclusion hard_exclusion:dish_type_different -> None) |
| Fuyu persimmon and roasted beet "carpaccio" w |  | evaluated unbounded | new on the after run (menu read differently or newly selected) |
| Fuyu persimmon and roasted beet "carpaccio" w | evaluated unbounded |  | absent from the after run (menu read differently) |
| Garden lettuce salad with Sungold tomatoes, A | evaluated bounded | evaluated bounded | grading changed on 3 page(s), e.g. cooking.nytimes.com: variant/low -> variant/high (preparation different -> similar; hard exclusion hard_exclusion:preparation_different -> None) |
| Chicken for two roasted in the wood-fired bri | evaluated unbounded | evaluated unbounded | grading changed on 5 page(s), e.g. barefootcontessa.com: same/high -> same/high (preparation similar -> same) |

Unranked after, with reasons:
- House-cured anchovies with celery, Parmigiano-Reggiano, and coquillo olives: the estimate has no upper bound: 1 of 1 recipes have no upper bound (30daysofgreekfood.com: fresh anchovies (as_used_not_accepted_for_flesh), white wine vinegar (missing_
- Fuyu persimmon and roasted beet "carpaccio" with Laychee goat cheese, tender herbs, and Meyer lemon-pistachio aïllade: no recipe of this dish could be portioned (no scenario could be portioned (2 without an applicable portion model))
- Pizza with Wagon Wheel cheese, soppressata, wild nettles, red onion, and Boont Corners sheep cheese: the estimate has no upper bound: 1 of 1 recipes have no upper bound (epicurious.com: unbleached all-purpose flour (missing_grams), cornmeal for sprinkling the baking)
- Yellowfin tuna grilled rare all'acqua di mare with Manila clams, mussels, sprouting cauliflower, string beans, a slow-cooked Early Girl tomato, and aïoli: no recipe of this dish could be portioned (no scenario could be portioned (1 without an applicable portion model))
- Steak frites: Stemple Creek Ranch bavette steak with pommes frites, Padrón peppers, avocado, and chimichurri: the estimate has no upper bound: 3 of 3 recipes have no upper bound (cooking.nytimes.com: steak-cut frozen fries (preparation_unresolved); delish.com: canola oil (missing
- Chicken for two roasted in the wood-fired brick oven; warm bread salad with scallions, garlic, bitter greens, dried currants, and pine nuts: the estimate has no upper bound: 3 of 3 recipes have no upper bound (debspots.com: pine nuts (preparation_unresolved), chicken drippings (missing_grams), a mutual ; foste

Reference checks after:
- Marinated olives (PR13): no failing check
  - per_plate: Roli's middle 2.342 vs published 1.4-1.4, 1 independent; shown only
  - per_100g: Roli's middle 3.123 vs published 1.7-2.8, 5 independent; passed

## Seafood chalkboard

**Before:** Among the 5 dishes I could estimate (7 tried; 2 had no usable estimate), lowest saturated fat first: 1) Ocean Trout / Tuna Poke Salad, about 2.9-7.0 g saturated fat per plate; 2) Crumbed Whiting, 3.2-6.5 g; 3) Crudo Of Swordfish, 2.5-13 g. These ranges overlap, so treat the order as a toss-up. Ocean Trout / Tuna Poke Salad cholesterol about 18-43 mg. Modeled from published recipes and typical portions, not this kitchen's numbers.

**After:** Among the 5 dishes I could estimate (7 tried; 2 had no usable estimate), lowest saturated fat first: 1) Ocean Trout / Tuna Poke Salad, about 2.9-7.0 g saturated fat per plate; 2) Crumbed Whiting, 3.2-6.5 g; 3) Crudo Of Swordfish, 2.5-13 g. These ranges overlap, so treat the order as a toss-up. Ocean Trout / Tuna Poke Salad cholesterol about 18-43 mg. Modeled from published recipes and typical portions, not this kitchen's numbers.

| | before | after |
|---|---|---|
| #1 | OCEAN TROUT / TUNA POKE SALAD: sat 2.9-7.0 g, chol 18-43 mg (close_call) | OCEAN TROUT / TUNA POKE SALAD: sat 2.9-7.0 g, chol 18-43 mg (close_call) |
| #2 | CRUMBED WHITING: sat 3.2-6.5 g, chol 99-199 mg (close_call) | CRUMBED WHITING: sat 3.2-6.5 g, chol 99-199 mg (close_call) |
| #3 | CRUDO OF SWORDFISH: sat 2.5-12.9 g, chol 33-99 mg (close_call) | CRUDO OF SWORDFISH: sat 2.5-12.9 g, chol 33-99 mg (close_call) |

| dish | before | after | why |
|---|---|---|---|
| CRUDO OF SWORDFISH | evaluated bounded | evaluated bounded | grading changed on 1 page(s), e.g. lacucinaitaliana.com: variant/low -> variant/high (preparation different -> similar; hard exclusion hard_exclusion:preparation_different -> None) |
| OCEAN TROUT | evaluated bounded | evaluated bounded | lines no longer open: ['heaped tablespoons natural yoghurt', 'shallots', 'yellow onion']; grading changed on 1 page(s), e.g. epicurious.com: variant/low -> different/low (hard exclusion hard_exclusion:preparation_different -> hard_exclusion:dish_type_different); different recipes calculated (4 before, 3 after, 1 shared): search results or cache, not a code change |
| COBIA | evaluated unbounded | evaluated unbounded | grading changed on 1 page(s), e.g. foodnetwork.com: different/low -> variant/high (preparation different -> similar; hard exclusion hard_exclusion:dish_type_different -> None); different recipes calculated (2 before, 3 after, 2 shared): search results or cache, not a code change |
| SNAPPER | evaluated bounded | evaluated bounded | lines no longer open: ['vegetable oil']; different recipes calculated (5 before, 5 after, 1 shared): search results or cache, not a code change |

Unranked after, with reasons:
- CHILLED MOOLOOLABA PRAWNS: no recipe of this dish could be portioned (no scenario could be portioned (2 without an applicable portion model))
- COBIA: the estimate has no upper bound: 1 of 1 recipes have no upper bound (mydeliciousblog.com: toasted pepitas or sunflower seeds (missing_grams))
