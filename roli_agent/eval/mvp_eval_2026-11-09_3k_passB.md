# MVP evaluation (2026-11-09)

| photo | run | status | s | menu items | candidates | selected | evaluated | ranked | unranked | no recipes | errors | skipped | budget-stopped | credits | model calls | model $ (actual+est.) | USDA req | words |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| menu_03_own_IMG_5185.jpg | 1 | done | 77.6 | 19 | 18 | 18 | 15 | 8 | 8 | 2 | 0 | 0 | 0 | 0 | 27 | 0.0260 (0.0260+0.0000) | 3 | 73 |
| menu_08_greyhound_pub_uk_printed.jpg | 1 | done | 110.9 | 38 | 33 | 30 | 28 | 17 | 11 | 1 | 1 | 3 | 0 | 0 | 27 | 0.0165 (0.0165+0.0000) | 0 | 86 |
| menu_01_own_zuni_cafe_sf.jpg | 1 | done | 15.4 | 71 | 15 | 15 | 14 | 9 | 5 | 1 | 0 | 0 | 0 | 0 | 8 | 0.0046 (0.0046+0.0000) | 0 | 75 |
| menu_23_en_boardwalk_bistro_chalkboard.jpg | 1 | done | 73.5 | 9 | 9 | 9 | 8 | 7 | 1 | 1 | 0 | 0 | 0 | 0 | 10 | 0.0048 (0.0048+0.0000) | 1 | 80 |

## menu_03_own_IMG_5185.jpg run 1

> Among the 8 dishes I could estimate (18 tried; 10 had no usable estimate), lowest saturated fat first: 1) Heirloom Tomatoes, most plates about 1.9-3.1 g saturated fat per plate; 2) Bluefin Crudo, most plates 1.1-12 g; 3) Today's Ricotta, most plates 3.1-11 g. These ranges overlap, so treat the order as a toss-up. Heirloom Tomatoes has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

| # | dish | sat fat g | support |
|---|---|---|---|
| 1 | HEIRLOOM TOMATOES | 1.770–3.298 | close_call |
| 2 | BLUEFIN CRUDO | 0.828–11.30 | close_call |
| 3 | TODAY'S RICOTTA | 2.095–18.93 | close_call |
| 4 | LITTLE GEM LETTUCES | 4.317–20.89 | close_call |
| 5 | KING SALMON | 6.203–20.28 | close_call |
| 6 | PORK CHOP | 7.512–27.92 | close_call |
| 7 | CORN CAPPELLETTI | 3.547–23.25 | close_call |
| 8 | KOSHIHIKARI ARANCINI | 1.059–30.39 | well_supported |

Unranked: POLE BEANS (the estimate has no upper bound: 2 of 2 recipes have no upper bound (notquitenigella.com: miso bagna cauda (missing_gram); PUTTANESCA (the estimate has no upper bound: 4 of 4 recipes have no upper bound (cilantroparsley.com: store bought pizza dough (miss); MARGHERITA (the estimate has no upper bound: 3 of 4 recipes have no upper bound (life-in-the-lofthouse.com: for my best pizza dough ); ORECCHIETTE (the estimate has no upper bound: 3 of 3 recipes have no upper bound (aboutamom.com: chanterelle (missing_grams), wasabi ); DUCK TRIANGOLI (no recipe of this dish could be portioned (no scenario could be portioned (1 without an applicable portion model))); TALEGGIO SCARPINOCC (the estimate has no upper bound: 1 of 1 recipes have no upper bound (qbcucina.com: aceto balsamico (missing_grams))); PAPPARDELLE (no recipe of this dish could be portioned (no scenario could be portioned (4 without an applicable portion model))); SALSICCIA BIANCA (our estimate disagrees with published figures for this kind of dish)

USDA: 3 requests; remaining 3562 -> 3561 of 3600; halted False; flagged 1; USDA-unavailable dishes 0

Flags: open SALSICCIA BIANCA (per_plate; Roli 42.196 vs 2.5-21.2; top ['caciocavallo', 'butter', 'cooked italian sausage'])

## menu_08_greyhound_pub_uk_printed.jpg run 1

> Among the 17 dishes I could estimate (30 tried; 13 had no usable estimate; 3 not tried), lowest saturated fat first: 1) Padron Peppers, most plates about 0.4-1.9 g saturated fat per plate; 2) Cornish Fish & Chips; 3) Pan Fried Seabass, most plates 5.6-19 g. Cornish Fish & Chips: most plates about 5.1-7.6 g saturated fat if fried in vegetable oil, up to about 21 g in beef dripping. Ask what they fry in. Modeled from published recipes and typical portions, not this kitchen's numbers.

| # | dish | sat fat g | support |
|---|---|---|---|
| 1 | PADRON PEPPERS | 0.217–3.076 | close_call |
| 2 | CORNISH FISH & CHIPS | 4.716–23.07 | close_call |
| 3 | PAN FRIED SEABASS | 4.129–25.65 | close_call |
| 4 | PIGS IN BLANKETS | 4.227–42.71 | close_call |
| 5 | CHICKEN SCHNITZEL | 12.51–34.44 | well_supported |
| 6 | CHILLI & GARLIC GREEN BEANS | 0.466–3.953 | close_call |
| 7 | TENDER STEM BROCOLLI | 0.637–3.122 | close_call |
| 8 | TOMATO & RED ONION SALAD | 0.852–3.315 | close_call |
| 9 | ONION RINGS | 0.317–3.804 | close_call |
| 10 | MIXED LEAF SALAD | 0.039–3.910 | close_call |
| 11 | SICILIAN OLIVES | 1.376–4.034 | close_call |
| 12 | KOFFMANN'S HAND CUT CHIPS | 1.892–4.133 | close_call |
| 13 | SKINNY FRIES | 1.892–4.133 | close_call |
| 14 | SMOKED GARLIC MASH | 1.577–15.08 | close_call |
| 15 | THE GREYHOUND CHEESE SLATE | 6.506–13.73 | close_call |
| 16 | APPLE & CRUMBLE RHUBARB | 5.749–33.23 | close_call |
| 17 | STICKY TOFFEE PUDDING | 5.708–30.47 | close_call |

Unranked: CRACKLING PIG STICKS (no recipe of this dish could be portioned (no scenario could be portioned (4 without an applicable portion model))); ROASTED HARISSA AUBERGINE (the estimate has no upper bound: 1 of 1 recipes have no upper bound (bbcgoodfood.com: Coconut Yoghurt (missing_grams))); HOUSE BAKED BREAD (the estimate has no upper bound: 1 of 1 recipes have no upper bound (tastesbetterfromscratch.com: & Hummus (missing_gram); CAMEMBERT & SAGE CROQUETTES (no recipe of this dish could be portioned (no scenario could be portioned (3 without an applicable portion model))); SIRLOIN STEAK 10oz (the estimate has no upper bound: 4 of 4 recipes have no upper bound (cookingwithcurls.com: Koffmann's Hand Cut Chips (mi); WAGYU BEEF BURGER (the estimate has no upper bound: 1 of 1 recipes have no upper bound (foodnetwork.com: Hand Cut Chips (missing_grams))); THE GREYHOUND VEGAN BURGER (no recipe of this dish could be portioned (no scenario could be portioned (4 without an applicable portion model))); CONISBEE BUTCHER LAMB & MINT SAUSAGES (the estimate has no upper bound: 2 of 2 recipes have no upper bound (cooking.nytimes.com: white beans (preparation_unres); TAGLIATELLE CARBONARA (the estimate has no upper bound: 2 of 2 recipes have no upper bound (pastaevangelists.com: Wild Mushroom & Asparagus (mi); BAKED VANILA CHEESECAKE (the estimate has no upper bound: 2 of 2 recipes have no upper bound (bbcgoodfood.com: Red Wine & Cinnamon Compote (missi); BISCOFF DOUGHNUTS (no recipe of this dish could be portioned (no scenario could be portioned (2 without an applicable portion model)))

Errors: CRISPY SQUID & PRAWNS: ArithmeticError: cholesterol_mg: per-serving value does not reconcile within tolerance

USDA: 0 requests; remaining 3561 -> 3561 of 3600; halted False; flagged 0; USDA-unavailable dishes 0

Frying-fat line: Cornish Fish & Chips: most plates about 5.1-7.6 g saturated fat if fried in vegetable oil, up to about 21 g in beef dripping. Ask what they fry in.

## menu_01_own_zuni_cafe_sf.jpg run 1

> Among the 9 dishes I could estimate (15 tried; 6 had no usable estimate), lowest saturated fat first: 1) Bowl of polenta, most plates about 2.1-7.3 g saturated fat per plate; 2) Zuni Caesar salad, most plates 2.3-5.6 g; 3) Garden lettuce salad, most plates 1.7-12 g. These ranges overlap, so treat the order as a toss-up. Bowl of polenta cholesterol about 9-33 mg. Modeled from published recipes and typical portions, not this kitchen's numbers.

| # | dish | sat fat g | support |
|---|---|---|---|
| 1 | Bowl of polenta with mascarpone or Parmigiano-Reggiano | 1.173–12.54 | close_call |
| 2 | Zuni Caesar salad | 1.952–7.970 | close_call |
| 3 | Garden lettuce salad with Sungold tomatoes, Alpha Tolman cheese, chapons, and passion fruit vinaigrette | 1.278–21.07 | close_call |
| 4 | Spaghetti with Gulf shrimp, heirloom tomatoes, basil, garlic, Espelette pepper, and brandy | 0.776–14.50 | close_call |
| 5 | Yellowfin tuna grilled rare all'acqua di mare with Manila clams, mussels, sprouting cauliflower, string beans, a slow-cooked Early Girl tomato, and aïoli | 3.298–12.75 | tentative |
| 6 | Stemple Creek Ranch ribeye steak (served with the above accompaniments) | 11.22–33.15 | well_supported |
| 7 | Marinated olives | 1.287–3.910 | close_call |
| 8 | Wood fire-roasted tomato and eggplant soup with mint, Urfa pepper, and charmoula | 1.181–5.215 | close_call |
| 9 | Shoestring potatoes | 1.892–4.133 | close_call |

Unranked: House-cured anchovies with celery, Parmigiano-Reggiano, and coquillo olives (the estimate has no upper bound: 2 of 2 recipes have no upper bound (exau.substack.com: fresh anchovies (as_used_not_acc); Fuyu persimmon and roasted beet "carpaccio" with Laychee goat cheese, tender herbs, and Meyer lemon-pistachio aillade (no recipe of this dish could be portioned (no scenario could be portioned (6 without an applicable portion model))); Pizza with Wagon Wheel cheese, soppressata, wild nettles, red onion, and Boont Corners sheep cheese (the estimate has no upper bound: 4 of 4 recipes have no upper bound (epicurious.com: purchased fully baked thin pizza cr); Steak frites: Stemple Creek Ranch bavette steak with pommes frites, Padrón peppers, avocado, and chimichurri (the estimate has no upper bound: 1 of 1 recipes have no upper bound (cooking.nytimes.com: steak-cut frozen fries (prepar); Stemple Creek Ranch grass-fed hamburger on rosemary focaccia with aïoli and Zuni pickles (no recipe of this dish could be portioned (no scenario could be portioned (1 without an applicable portion model)))

USDA: 0 requests; remaining 3561 -> 3561 of 3600; halted False; flagged 0; USDA-unavailable dishes 0

## menu_23_en_boardwalk_bistro_chalkboard.jpg run 1

> Among the 7 dishes I could estimate (9 tried; 2 had no usable estimate), lowest saturated fat first: 1) Ocean Trout / Tuna Poke Salad, most plates about 0.6-3.0 g saturated fat per plate; 2) Crumbed Whiting, most plates 1.7-5.0 g; 3) Chilled Mooloolaba Prawns, most plates 1.4-4.7 g. These ranges overlap, so treat the order as a toss-up. Chilled Mooloolaba Prawns may carry up to 312 mg cholesterol. Modeled from published recipes and typical portions, not this kitchen's numbers.

| # | dish | sat fat g | support |
|---|---|---|---|
| 1 | OCEAN TROUT / TUNA POKE SALAD | 0.509–6.848 | close_call |
| 2 | CRUMBED WHITING | 1.074–5.914 | close_call |
| 3 | CHILLED MOOLOOLABA PRAWNS | 0.921–5.720 | close_call |
| 4 | BATTERED OYSTERS | 1.329–6.457 | close_call |
| 5 | CRUDO OF SWORDFISH | 3.997–13.07 | close_call |
| 6 | SNAPPER | 4.958–17.88 | close_call |
| 7 | OCEAN TROUT | 6.720–21.65 | well_supported |

Unranked: COBIA (the estimate has no upper bound: 1 of 1 recipes have no upper bound (mydeliciousblog.com: toasted pepitas or sunflower s)

USDA: 1 requests; remaining 3561 -> 3560 of 3600; halted False; flagged 0; USDA-unavailable dishes 0
