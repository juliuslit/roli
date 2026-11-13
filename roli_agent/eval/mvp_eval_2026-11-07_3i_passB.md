# MVP evaluation (2026-11-07)

| photo | run | status | s | menu items | candidates | selected | evaluated | ranked | unranked | no recipes | errors | skipped | budget-stopped | credits | model calls | model $ (actual+est.) | USDA req | words |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| menu_03_own_IMG_5185.jpg | 1 | done | 10.5 | 19 | 18 | 14 | 9 | 4 | 7 | 3 | 0 | 4 | 0 | 0 | 10 | 0.0081 (0.0081+0.0000) | 2 | 76 |
| menu_08_greyhound_pub_uk_printed.jpg | 1 | done | 58.2 | 38 | 33 | 14 | 14 | 7 | 7 | 0 | 0 | 19 | 0 | 0 | 12 | 0.0065 (0.0065+0.0000) | 2 | 80 |
| menu_01_own_zuni_cafe_sf.jpg | 1 | done | 11.2 | 71 | 15 | 14 | 13 | 7 | 6 | 1 | 0 | 1 | 0 | 0 | 8 | 0.0061 (0.0061+0.0000) | 1 | 75 |
| menu_23_en_boardwalk_bistro_chalkboard.jpg | 1 | done | 3.6 | 9 | 9 | 9 | 8 | 7 | 1 | 1 | 0 | 0 | 0 | 0 | 2 | 0.0009 (0.0009+0.0000) | 0 | 74 |

## menu_03_own_IMG_5185.jpg run 1

> Among the 4 dishes I could estimate (14 tried; 10 had no usable estimate; 4 not tried), lowest saturated fat first: 1) Bluefin Crudo, about 0.8-11 g saturated fat per plate; 2) Little Gem Lettuces, 4.2-8.7 g; 3) King Salmon, 6.3-20 g. These ranges overlap, so treat the order as a toss-up. Bluefin Crudo cholesterol about 31-116 mg, the top end from bottarga (an estimate). Modeled from published recipes and typical portions, not this kitchen's numbers.

| # | dish | sat fat g | support |
|---|---|---|---|
| 1 | BLUEFIN CRUDO | 0.828–11.30 | close_call |
| 2 | LITTLE GEM LETTUCES | 4.188–8.728 | close_call |
| 3 | KING SALMON | 6.348–20.24 | close_call |
| 4 | PORK CHOP | 7.864–27.92 | well_supported |

Unranked: POLE BEANS (the estimate has no upper bound: 2 of 2 recipes have no upper bound (notquitenigella.com: miso bagna cauda (missing_gram); PUTTANESCA (the estimate has no upper bound: 4 of 4 recipes have no upper bound (cilantroparsley.com: store bought pizza dough (miss); MARGHERITA (the estimate has no upper bound: 3 of 4 recipes have no upper bound (life-in-the-lofthouse.com: for my best pizza dough ); ORECCHIETTE (the estimate has no upper bound: 4 of 4 recipes have no upper bound (aboutamom.com: chanterelle (missing_grams), wasabi ); PAPPARDELLE (no recipe of this dish could be portioned (no scenario could be portioned (4 without an applicable portion model))); HEIRLOOM TOMATOES (our estimate disagrees with published figures for this kind of dish); SALSICCIA BIANCA (our estimate disagrees with published figures for this kind of dish)

USDA: 2 requests; remaining 2661 -> 2661 of 3600; halted False; flagged 2; USDA-unavailable dishes 0

Flags: open HEIRLOOM TOMATOES (per_plate; Roli 1.938 vs 4.0-18.0; top ['extra virgin olive oil', 'sourdough', 'heirloom tomatoes']); open SALSICCIA BIANCA (per_plate; Roli 41.154 vs 2.5-21.2; top ['caciocavallo', 'butter', 'cooked italian sausage'])

## menu_08_greyhound_pub_uk_printed.jpg run 1

> Among the 7 dishes I could estimate (14 tried; 7 had no usable estimate; 19 not tried), lowest saturated fat first: 1) Padron Peppers, about 0.2-3.1 g saturated fat per plate; 2) Chilli & Garlic Green Beans, 0.4-3.0 g; 3) Mixed Leaf Salad, 0.0-3.8 g. These ranges overlap, so treat the order as a toss-up. Padron Peppers has no cholesterol in its ingredients. Light snack: Sicilian Olives, 1.6-3.8 g. Modeled from published recipes and typical portions, not this kitchen's numbers.

| # | dish | sat fat g | support |
|---|---|---|---|
| 1 | PADRON PEPPERS | 0.217–3.076 | close_call |
| 2 | CHILLI & GARLIC GREEN BEANS | 0.433–3.014 | close_call |
| 3 | MIXED LEAF SALAD | 0.039–3.826 | close_call |
| 4 | TOMATO & RED ONION SALAD | 0.967–4.406 | tentative |
| 5 | APPLE & CRUMBLE RHUBARB | 5.818–15.19 | close_call |
| 6 | CORNISH FISH & CHIPS | 4.716–23.07 | well_supported |
| 7 | SICILIAN OLIVES | 1.587–3.796 | close_call |

Unranked: ROASTED HARISSA AUBERGINE (the estimate has no upper bound: 1 of 1 recipes have no upper bound (bbcgoodfood.com: Coconut Yoghurt (missing_fdc_id))); HOUSE BAKED BREAD (the estimate has no upper bound: 1 of 1 recipes have no upper bound (tastesbetterfromscratch.com: & Hummus (missing_gram); WAGYU BEEF BURGER (the estimate has no upper bound: 1 of 1 recipes have no upper bound (foodnetwork.com: ground sirloin (nutrient_not_repor); THE GREYHOUND VEGAN BURGER (no recipe of this dish could be portioned (no scenario could be portioned (3 without an applicable portion model))); CONISBEE BUTCHER LAMB & MINT SAUSAGES (the estimate has no upper bound: 1 of 1 recipes have no upper bound (cooking.nytimes.com: white beans (preparation_unres); TAGLIATELLE CARBONARA (the estimate has no upper bound: 2 of 2 recipes have no upper bound (pastaevangelists.com: Wild Mushroom & Asparagus (mi); BAKED VANILA CHEESECAKE (the estimate has no upper bound: 2 of 2 recipes have no upper bound (bbcgoodfood.com: Red Wine & Cinnamon Compote (missi)

USDA: 2 requests; remaining 2661 -> 2659 of 3600; halted False; flagged 0; USDA-unavailable dishes 0

Frying-fat line: Cornish Fish & Chips: about 4.7-8.0 g saturated fat if fried in vegetable oil, up to about 23 g in beef dripping. Ask what they fry in.

## menu_01_own_zuni_cafe_sf.jpg run 1

> Among the 7 dishes I could estimate (14 tried; 7 had no usable estimate; 1 not tried), lowest saturated fat first: 1) Garden lettuce salad, about 1.2-3.2 g saturated fat per plate; 2) Zuni Caesar salad, 1.8-3.3 g; 3) Wood fire-roasted tomato and eggplant soup, 1.2-4.5 g. These ranges overlap, so treat the order as a toss-up. Garden lettuce salad cholesterol about 1-10 mg. Modeled from published recipes and typical portions, not this kitchen's numbers.

| # | dish | sat fat g | support |
|---|---|---|---|
| 1 | Garden lettuce salad with Sungold tomatoes, Alpha Tolman cheese, chapons, and passion fruit vinaigrette | 1.153–3.154 | close_call |
| 2 | Zuni Caesar salad | 1.756–3.272 | close_call |
| 3 | Wood fire-roasted tomato and eggplant soup with mint, Urfa pepper, and charmoula | 1.212–4.462 | close_call |
| 4 | Shoestring potatoes | 1.892–4.133 | close_call |
| 5 | Yellowfin tuna grilled rare all'acqua di mare with Manila clams, mussels, sprouting cauliflower, string beans, a slow-cooked Early Girl tomato, and aïoli | 3.299–7.313 | close_call |
| 6 | Spaghetti with Gulf shrimp, heirloom tomatoes, basil, garlic, Espelette pepper, and brandy | 0.288–14.50 | well_supported |
| 7 | Marinated olives | 1.287–4.006 | close_call |

Unranked: House-cured anchovies with celery, Parmigiano-Reggiano, and coquillo olives (no recipe of this dish could be portioned (no scenario could be portioned (3 without an applicable portion model))); Fuyu persimmon and roasted beet "carpaccio" with Laychee goat cheese, tender herbs, and Meyer lemon-pistachio aillade (no recipe of this dish could be portioned (no scenario could be portioned (6 without an applicable portion model))); Pizza with Wagon Wheel cheese, soppressata, wild nettles, red onion, and Boont Corners sheep cheese (the estimate has no upper bound: 4 of 4 recipes have no upper bound (epicurious.com: purchased fully baked thin pizza cr); Steak frites: Stemple Creek Ranch bavette steak with pommes frites, Padrón peppers, avocado, and chimichurri (the estimate has no upper bound: 1 of 1 recipes have no upper bound (cooking.nytimes.com: steak-cut frozen fries (prepar); Chicken for two roasted in the wood-fired brick oven; warm bread salad with scallions, garlic, bitter greens, dried currants, and pine nuts (the estimate has no upper bound: 4 of 4 recipes have no upper bound (fostersmarket.com: salad (missing_grams), toasted p); Stemple Creek Ranch grass-fed hamburger on rosemary focaccia with aïoli and Zuni pickles (no recipe of this dish could be portioned (no scenario could be portioned (1 without an applicable portion model)))

USDA: 1 requests; remaining 2659 -> 2658 of 3600; halted False; flagged 0; USDA-unavailable dishes 0

## menu_23_en_boardwalk_bistro_chalkboard.jpg run 1

> Among the 7 dishes I could estimate (9 tried; 2 had no usable estimate), lowest saturated fat first: 1) Ocean Trout / Tuna Poke Salad, about 0.5-6.8 g saturated fat per plate; 2) Chilled Mooloolaba Prawns, 2.9-7.5 g; 3) Crumbed Whiting, 3.8-7.6 g. These ranges overlap, so treat the order as a toss-up. Chilled Mooloolaba Prawns is high in cholesterol, about 217-436 mg. Modeled from published recipes and typical portions, not this kitchen's numbers.

| # | dish | sat fat g | support |
|---|---|---|---|
| 1 | OCEAN TROUT / TUNA POKE SALAD | 0.507–6.848 | close_call |
| 2 | CHILLED MOOLOOLABA PRAWNS | 2.869–7.465 | close_call |
| 3 | CRUMBED WHITING | 3.796–7.618 | close_call |
| 4 | BATTERED OYSTERS | 4.145–8.318 | close_call |
| 5 | CRUDO OF SWORDFISH | 2.805–13.07 | close_call |
| 6 | SNAPPER | 4.958–17.88 | close_call |
| 7 | OCEAN TROUT | 6.720–21.65 | well_supported |

Unranked: COBIA (the estimate has no upper bound: 1 of 1 recipes have no upper bound (mydeliciousblog.com: toasted pepitas or sunflower s)

USDA: 0 requests; remaining 2658 -> 2658 of 3600; halted False; flagged 0; USDA-unavailable dishes 0
