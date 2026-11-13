# MVP evaluation (2026-11-06)

| photo | run | status | s | menu items | candidates | selected | evaluated | ranked | unranked | no recipes | errors | skipped | budget-stopped | credits | model calls | model $ (actual+est.) | USDA req | words |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| menu_03_own_IMG_5185.jpg | 1 | done | 102.3 | 19 | 17 | 14 | 12 | 6 | 6 | 2 | 0 | 3 | 0 | 0 | 27 | 0.0967 (0.0967+0.0000) | 13 | 71 |
| menu_08_greyhound_pub_uk_printed.jpg | 1 | done | 111.5 | 38 | 15 | 14 | 13 | 6 | 8 | 0 | 0 | 1 | 0 | 0 | 25 | 0.1141 (0.1141+0.0000) | 9 | 76 |
| menu_01_own_zuni_cafe_sf.jpg | 1 | done | 141.6 | 71 | 13 | 13 | 13 | 8 | 5 | 0 | 0 | 0 | 0 | 1 | 28 | 0.1219 (0.1219+0.0000) | 5 | 78 |
| menu_23_en_boardwalk_bistro_chalkboard.jpg | 1 | done | 57.6 | 9 | 7 | 7 | 7 | 6 | 1 | 0 | 0 | 0 | 0 | 0 | 16 | 0.0490 (0.0490+0.0000) | 5 | 74 |

## menu_03_own_IMG_5185.jpg run 1

> Among the 6 dishes I could estimate (14 tried; 8 had no usable estimate; 3 not tried), lowest saturated fat first: 1) Heirloom Tomatoes, about 0.8-2.2 g saturated fat per plate; 2) Bluefin Crudo, 0.5-11 g; 3) Little Gem Lettuces, 4.4-11 g. These ranges overlap, so treat the order as a toss-up. Heirloom Tomatoes has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

| # | dish | sat fat g | support |
|---|---|---|---|
| 1 | HEIRLOOM TOMATOES | 0.809–2.166 | close_call |
| 2 | BLUEFIN CRUDO | 0.454–11.01 | close_call |
| 3 | LITTLE GEM LETTUCES | 4.427–11.28 | close_call |
| 4 | KING SALMON | 4.664–15.32 | close_call |
| 5 | PORK CHOP | 7.908–26.33 | close_call |
| 6 | SALSICCIA BIANCA | 20.87–56.10 | well_supported |

Unranked: POLE BEANS (the estimate has no upper bound: 2 of 2 recipes have no upper bound (notquitenigella.com: miso bagna cauda (missing_gram); PUTTANESCA (the estimate has no upper bound: 4 of 4 recipes have no upper bound (cilantroparsley.com: store bought pizza dough (miss); MARGHERITA (the estimate has no upper bound: 3 of 4 recipes have no upper bound (life-in-the-lofthouse.com: for my best pizza dough ); ORECCHIETTE (the estimate has no upper bound: 4 of 4 recipes have no upper bound (bakedbree.com: chanterelle (missing_grams), wasabi ); DUCK TRIANGOLI (no recipe of this dish could be portioned (no scenario could be portioned (1 without an applicable portion model))); PAPPARDELLE (the estimate has no upper bound: 3 of 3 recipes have no upper bound (aflavorjournal.com: lamb merguez ragu (missing_gram)

USDA: 13 requests; remaining 3485 -> 3478 of 3600; halted False; flagged 0; USDA-unavailable dishes 0

## menu_08_greyhound_pub_uk_printed.jpg run 1

> Among the 6 dishes I could estimate (14 tried; 8 had no usable estimate; 1 not tried), lowest saturated fat first: 1) Padron Peppers, about 0.6-4.0 g saturated fat per plate; 2) Pan Fried Seabass, 8.9-23 g; 3) Crispy Squid & Prawns, 1.5-42 g. These ranges overlap, so treat the order as a toss-up. Crispy Squid & Prawns may carry up to 386 mg cholesterol. Modeled from published recipes and typical portions, not this kitchen's numbers.

| # | dish | sat fat g | support |
|---|---|---|---|
| 1 | PADRON PEPPERS | 0.559–4.007 | close_call |
| 2 | PAN FRIED SEABASS | 8.898–22.96 | close_call |
| 3 | CRISPY SQUID & PRAWNS | 1.507–42.26 | close_call |
| 4 | CHICKEN SCHNITZEL | 12.51–34.44 | close_call |
| 5 | PIGS IN BLANKETS | 7.583–46.70 | well_supported |
| 6 | SICILIAN OLIVES | 1.587–3.796 | close_call |

Unranked: CRACKLING PIG STICKS (no recipe of this dish could be portioned (no scenario could be portioned (3 without an applicable portion model))); ROASTED HARISSA AUBERGINE (the estimate has no upper bound: 1 of 1 recipes have no upper bound (bbcgoodfood.com: Coconut Yoghurt (missing_fdc_id))); THE GREYHOUND SCOTCH EGG (the estimate has no upper bound: 2 of 2 recipes have no upper bound (catwillmadeit.com: Burnt Apple Puree (missing_grams); CAMEMBERT & SAGE CROQUETTES (no recipe of this dish could be portioned (no scenario could be portioned (3 without an applicable portion model))); SIRLOIN STEAK 10oz (the estimate has no upper bound: 4 of 4 recipes have no upper bound (cookingwithcurls.com: Koffmann's Hand Cut Chips (mi); CONISBEE BUTCHER LAMB & MINT SAUSAGES (the estimate has no upper bound: 1 of 1 recipes have no upper bound (cooking.nytimes.com: white beans (preparation_unres); TAGLIATELLE CARBONARA (the estimate has no upper bound: 4 of 4 recipes have no upper bound (mandytanner.com: Wild Mushroom & Asparagus (missing); CORNISH FISH & CHIPS (known limit of the data: USDA has no thick-cut chips record)

USDA: 9 requests; remaining 3478 -> 3470 of 3600; halted False; flagged 0; USDA-unavailable dishes 0

Flags: known_limit CORNISH FISH & CHIPS (per_plate (vegetable oil); Roli 8.490 vs 2-5.2; top ['CHIPS: frying fat, Fat, beef tallow', 'CORNISH FISH: frying fat, Fat, beef tallow', 'vegetable oil'])

Frying-fat line: Cornish Fish & Chips: about 6.9-10 g saturated fat if fried in vegetable oil, up to about 31 g in beef dripping. Ask what they fry in.

## menu_01_own_zuni_cafe_sf.jpg run 1

> Among the 8 dishes I could estimate (13 tried; 5 had no usable estimate), lowest saturated fat first: 1) Garden lettuce salad, about 1.3-5.4 g saturated fat per plate; 2) Wood fire-roasted tomato and eggplant soup, 1.5-5.6 g; 3) Zuni Caesar salad, 2.0-5.6 g. These ranges overlap, so treat the order as a toss-up. Garden lettuce salad cholesterol about 1-17 mg. Light snack: Marinated olives, 1.3-4.0 g. Modeled from published recipes and typical portions, not this kitchen's numbers.

| # | dish | sat fat g | support |
|---|---|---|---|
| 1 | Garden lettuce salad with Sungold tomatoes, Alpha Tolman cheese, chapons, and passion fruit vinaigrette | 1.284–5.401 | close_call |
| 2 | Wood fire-roasted tomato and eggplant soup with mint, Urfa pepper, and charmoula | 1.546–5.597 | close_call |
| 3 | Zuni Caesar salad | 1.956–5.603 | close_call |
| 4 | Yellowfin tuna grilled rare all'acqua di mare with Manila clams, mussels, sprouting cauliflower, string beans, a slow-cooked Early Girl tomato, and aïoli | 2.579–5.871 | close_call |
| 5 | Shoestring potatoes | 4.98–7.071 | close_call |
| 6 | Spaghetti with Gulf shrimp, heirloom tomatoes, basil, garlic, Espelette pepper, and brandy | 1.866–18.43 | close_call |
| 7 | Stemple Creek Ranch ribeye steak | 11.30–30.94 | well_supported |
| 8 | Marinated olives | 1.287–4.006 | close_call |

Unranked: House-cured anchovies with celery, Parmigiano-Reggiano, and coquillo olives (no recipe of this dish could be portioned (no scenario could be portioned (3 without an applicable portion model))); Fuyu persimmon and roasted beet "carpaccio" with Laychee goat cheese, tender herbs, and Meyer lemon-pistachio aillade (no recipe of this dish could be portioned (no scenario could be portioned (6 without an applicable portion model))); Pizza with Wagon Wheel cheese, soppressata, wild nettles, red onion, and Boont Corners sheep cheese (the estimate has no upper bound: 4 of 4 recipes have no upper bound (epicurious.com: purchased fully baked thin pizza cr); Steak frites: Stemple Creek Ranch bavette steak with pommes frites, Padrón peppers, avocado, and chimichurri (the estimate has no upper bound: 1 of 2 recipes have no upper bound (cooking.nytimes.com: steak-cut frozen fries (prepar); Chicken for two roasted in the wood-fired brick oven; warm bread salad with scallions, garlic, bitter greens, dried currants, and pine nuts (the estimate has no upper bound: 4 of 4 recipes have no upper bound (fostersmarket.com: salad (missing_grams), toasted p)

USDA: 5 requests; remaining 3470 -> 3472 of 3600; halted False; flagged 0; USDA-unavailable dishes 0

## menu_23_en_boardwalk_bistro_chalkboard.jpg run 1

> Among the 6 dishes I could estimate (7 tried; 1 had no usable estimate), lowest saturated fat first: 1) Ocean Trout / Tuna Poke Salad, about 0.3-7.0 g saturated fat per plate; 2) Chilled Mooloolaba Prawns, 2.1-5.4 g; 3) Crumbed Whiting, 2.8-5.5 g. These ranges overlap, so treat the order as a toss-up. Chilled Mooloolaba Prawns is high in cholesterol, about 157-316 mg. Modeled from published recipes and typical portions, not this kitchen's numbers.

| # | dish | sat fat g | support |
|---|---|---|---|
| 1 | OCEAN TROUT / TUNA POKE SALAD | 0.292–6.969 | close_call |
| 2 | CHILLED MOOLOOLABA PRAWNS | 2.078–5.414 | close_call |
| 3 | CRUMBED WHITING | 2.750–5.524 | close_call |
| 4 | CRUDO OF SWORDFISH | 2.450–12.82 | close_call |
| 5 | OCEAN TROUT | 5.992–18.06 | close_call |
| 6 | SNAPPER | 4.716–36.42 | well_supported |

Unranked: COBIA (the estimate has no upper bound: 1 of 1 recipes have no upper bound (mydeliciousblog.com: toasted pepitas or sunflower s)

USDA: 5 requests; remaining 3472 -> 3469 of 3600; halted False; flagged 0; USDA-unavailable dishes 0
