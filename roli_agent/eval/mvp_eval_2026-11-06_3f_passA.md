# MVP evaluation (2026-11-06)

| photo | run | status | s | menu items | candidates | selected | evaluated | ranked | unranked | no recipes | errors | skipped | budget-stopped | credits | model calls | model $ (actual+est.) | USDA req | words |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| menu_03_own_IMG_5185.jpg | 1 | done | 114.4 | 19 | 17 | 14 | 12 | 6 | 6 | 2 | 0 | 3 | 0 | 2 | 30 | 0.1016 (0.1016+0.0000) | 29 | 74 |
| menu_08_greyhound_pub_uk_printed.jpg | 1 | done | 199.7 | 38 | 15 | 14 | 13 | 5 | 9 | 0 | 0 | 1 | 0 | 10 | 46 | 0.1478 (0.1478+0.0000) | 61 | 78 |
| menu_01_own_zuni_cafe_sf.jpg | 1 | done | 291.0 | 71 | 13 | 13 | 12 | 6 | 7 | 0 | 0 | 0 | 0 | 20 | 59 | 0.1792 (0.1792+0.0000) | 81 | 65 |
| menu_23_en_boardwalk_bistro_chalkboard.jpg | 1 | done | 79.1 | 9 | 7 | 7 | 7 | 5 | 2 | 0 | 0 | 0 | 0 | 2 | 18 | 0.0521 (0.0521+0.0000) | 14 | 74 |

## menu_03_own_IMG_5185.jpg run 1

> Among the 6 dishes I could estimate (14 tried; 8 had no usable estimate; 3 not tried), lowest saturated fat first: 1) Heirloom Tomatoes, about 0.4-2.4 g saturated fat per plate; 2) Bluefin Crudo, 0.5-4.3 g; 3) Little Gem Lettuces, 4.4-11 g. Heirloom Tomatoes and Bluefin Crudo overlap, so treat that order as a toss-up. Heirloom Tomatoes has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

| # | dish | sat fat g | support |
|---|---|---|---|
| 1 | HEIRLOOM TOMATOES | 0.435–2.390 | close_call |
| 2 | BLUEFIN CRUDO | 0.465–4.298 | close_call |
| 3 | LITTLE GEM LETTUCES | 4.427–11.28 | close_call |
| 4 | KING SALMON | 4.109–15.11 | close_call |
| 5 | PORK CHOP | 7.920–26.37 | close_call |
| 6 | MARGHERITA | 11.56–27.55 | well_supported |

Unranked: POLE BEANS (the estimate has no upper bound: 1 of 1 recipes have no upper bound (cooking.nytimes.com: miso bagna cauda (missing_gram); PUTTANESCA (the estimate has no upper bound: 1 of 1 recipes have no upper bound (foodnetwork.com: castelvetrano (missing_grams), chi); SALSICCIA BIANCA (no recipe of this dish could be portioned (no scenario could be portioned (6 without an applicable portion model))); ORECCHIETTE (the estimate has no upper bound: 4 of 4 recipes have no upper bound (bakedbree.com: chanterelle (missing_grams), wasabi ); TALEGGIO SCARPINOCC (the estimate has no upper bound: 1 of 1 recipes have no upper bound (qbcucina.com: aceto balsamico (missing_grams))); PAPPARDELLE (the estimate has no upper bound: 3 of 3 recipes have no upper bound (aflavorjournal.com: lamb merguez ragu (missing_gram)

USDA: 29 requests; remaining 3469 -> 3444 of 3600; halted False; flagged 0; USDA-unavailable dishes 0

## menu_08_greyhound_pub_uk_printed.jpg run 1

> Among the 5 dishes I could estimate (14 tried; 9 had no usable estimate; 1 not tried), lowest saturated fat first: 1) Padron Peppers, about 0.6-4.0 g saturated fat per plate; 2) Crispy Squid & Prawns, 1.5-3.0 g; 3) Pan Fried Seabass, 9.0-23 g. Padron Peppers and Crispy Squid & Prawns overlap, so treat that order as a toss-up. Padron Peppers has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

| # | dish | sat fat g | support |
|---|---|---|---|
| 1 | PADRON PEPPERS | 0.559–4.007 | close_call |
| 2 | CRISPY SQUID & PRAWNS | 1.507–3.033 | tentative |
| 3 | PAN FRIED SEABASS | 8.962–23.11 | close_call |
| 4 | CHICKEN SCHNITZEL | 12.51–34.44 | close_call |
| 5 | PIGS IN BLANKETS | 18.68–46.70 | well_supported |

Unranked: CRACKLING PIG STICKS (no recipe of this dish could be portioned (no scenario could be portioned (3 without an applicable portion model))); SICILIAN OLIVES (no recipe of this dish could be portioned (no scenario could be portioned (1 without an applicable portion model))); ROASTED HARISSA AUBERGINE (no recipe of this dish could be portioned (no scenario could be portioned (8 without an applicable portion model))); THE GREYHOUND SCOTCH EGG (the estimate has no upper bound: 2 of 2 recipes have no upper bound (catwillmadeit.com: canola/vegetable oil (missing_gr); CAMEMBERT & SAGE CROQUETTES (no recipe of this dish could be portioned (no scenario could be portioned (3 without an applicable portion model))); SIRLOIN STEAK 10oz (the estimate has no upper bound: 4 of 4 recipes have no upper bound (cookingwithcurls.com: brown sugar (missing_grams), ); CONISBEE BUTCHER LAMB & MINT SAUSAGES (the estimate has no upper bound: 1 of 1 recipes have no upper bound (cooking.nytimes.com: white beans (preparation_unres); TAGLIATELLE CARBONARA (the estimate has no upper bound: 4 of 4 recipes have no upper bound (mandytanner.com: Wild Mushroom & Asparagus (missing); CORNISH FISH & CHIPS (our estimate disagrees with published figures for this kind of dish)

USDA: 61 requests; remaining 3444 -> 3393 of 3600; halted False; flagged 1; USDA-unavailable dishes 0

Flags: open CORNISH FISH & CHIPS (per_plate (vegetable oil); Roli 8.490 vs 2-5.2; top ['CHIPS: frying fat, Vegetable oil, NFS / CHIPS: frying fat, Fat, beef tallow', 'CORNISH FISH: frying fat, Vegetable oil, NFS / CORNISH FISH: frying fat, Fat, beef tallow', 'Mushy Peas'])

Frying-fat line: Cornish Fish & Chips: about 6.9-10 g saturated fat if fried in vegetable oil, up to about 31 g in beef dripping. Ask what they fry in.

## menu_01_own_zuni_cafe_sf.jpg run 1

> Among the 6 dishes I could estimate (13 tried; 7 had no usable estimate), lowest saturated fat first: 1) Wood fire-roasted tomato and eggplant soup, about 0.7-3.9 g saturated fat per plate; 2) Garden lettuce salad, 0.3-5.4 g; 3) Zuni Caesar salad, 2.0-5.6 g. These ranges overlap, so treat the order as a toss-up. Modeled from published recipes and typical portions, not this kitchen's numbers.

| # | dish | sat fat g | support |
|---|---|---|---|
| 1 | Wood fire-roasted tomato and eggplant soup with mint, Urfa pepper, and charmoula | 0.714–3.896 | close_call |
| 2 | Garden lettuce salad with Sungold tomatoes, Alpha Tolman cheese, chapons, and passion fruit vinaigrette | 0.282–5.401 | close_call |
| 3 | Zuni Caesar salad‡ | 1.956–5.627 | close_call |
| 4 | Shoestring potatoes | 4.98–7.071 | close_call |
| 5 | Spaghetti with Gulf shrimp, heirloom tomatoes, basil, garlic, Espelette pepper, and brandy | 3.983–18.43 | close_call |
| 6 | Stemple Creek Ranch ribeye steak (served with the above accompaniments) | 11.30–27.63 | well_supported |

Unranked: House-cured anchovies with celery, Parmigiano-Reggiano, and coquillo olives (no recipe of this dish could be portioned (no scenario could be portioned (3 without an applicable portion model))); Fuyu persimmon and roasted beet "carpaccio" with Laychee goat cheese, tender herbs, and Meyer lemon-pistachio aillade (no recipe of this dish could be portioned (no scenario could be portioned (6 without an applicable portion model))); Pizza with Wagon Wheel cheese, soppressata, wild nettles, red onion, and Boont Corners sheep cheese (the estimate has no upper bound: 1 of 1 recipes have no upper bound (epicurious.com: unbleached all-purpose flour (missi); Yellowfin tuna‡ grilled rare all'acqua di mare with Manila clams, mussels, sprouting cauliflower, string beans, a slow-cooked Early Girl tomato, and aïoli‡ (the estimate has no upper bound: 1 of 1 recipes have no upper bound (cooking.nytimes.com: whole (missing_grams), red oni); Steak frites: Stemple Creek Ranch bavette steak with pommes frites, Padrón peppers, avocado, and chimichurri (the estimate has no upper bound: 1 of 2 recipes have no upper bound (cooking.nytimes.com: steak-cut frozen fries (prepar); Chicken for two roasted in the wood-fired brick oven; warm bread salad with scallions, garlic, bitter greens, dried currants, and pine nuts (the estimate has no upper bound: 3 of 3 recipes have no upper bound (fostersmarket.com: salad (missing_grams), toasted p); Marinated olives (our estimate disagrees with published figures for this kind of dish)

USDA: 81 requests; remaining 3393 -> 3350 of 3600; halted False; flagged 1; USDA-unavailable dishes 0

Flags: open Marinated olives (per_100g; Roli 5.398 vs 1.7-2.8; top ['delallo extra virgin olive oil', 'extra virgin olive oil / delallo castelvetrano olives', 'imported olives / kosher salt'])

## menu_23_en_boardwalk_bistro_chalkboard.jpg run 1

> Among the 5 dishes I could estimate (7 tried; 2 had no usable estimate), lowest saturated fat first: 1) Ocean Trout / Tuna Poke Salad, about 0.3-7.0 g saturated fat per plate; 2) Crumbed Whiting, 2.8-5.5 g; 3) Crudo Of Swordfish, 2.5-13 g. These ranges overlap, so treat the order as a toss-up. Ocean Trout / Tuna Poke Salad cholesterol about 18-43 mg. Modeled from published recipes and typical portions, not this kitchen's numbers.

| # | dish | sat fat g | support |
|---|---|---|---|
| 1 | OCEAN TROUT / TUNA POKE SALAD | 0.291–6.969 | close_call |
| 2 | CRUMBED WHITING | 2.750–5.524 | close_call |
| 3 | CRUDO OF SWORDFISH | 2.450–12.85 | close_call |
| 4 | SNAPPER | 4.729–15.36 | close_call |
| 5 | OCEAN TROUT | 6.180–18.10 | well_supported |

Unranked: CHILLED MOOLOOLABA PRAWNS (no recipe of this dish could be portioned (no scenario could be portioned (2 without an applicable portion model))); COBIA (the estimate has no upper bound: 1 of 1 recipes have no upper bound (mydeliciousblog.com: toasted pepitas or sunflower s)

USDA: 14 requests; remaining 3350 -> 3356 of 3600; halted False; flagged 0; USDA-unavailable dishes 0
