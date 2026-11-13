# Known-answer check, 2026-11-08b

50 dishes from 7 chains, typed as menus of dish names and sections only (no descriptions), run through the normal pipeline with the tested chain's own items left out of the plate-weight samples. Published figure = the chain's own saturated fat per plate (`data/chain_sheets/`). Run settings: {'daily_budget_usd': '7.50', 'daily_search_credits': 500, 'per_menu': 'unchanged ($0.50, 30 credits)', 'leave_one_chain_out': True}.

Roli gave an estimate for 41 of 50 (82 %) of the dishes. Of the 38 independent estimates (families whose plate size does not rest on these sheets):

| measure | result |
|---|---|
| published figure inside Roli's band ("most plates", meant to hold 8 in 10) | 17 of 38 (45 %) |
| inside Roli's full range | 19 of 38 (50 %) |
| Roli's middle within a factor of 2 of the published figure | 17 of 38 (45 %) |
| typical size of the miss (median, as a factor) | 2.10x |
| direction: Roli's middle above / below the published figure | 18 above, 19 below; median ratio 1.00 |

Dependent families, reported apart (3 dishes): band 2 of 3 (67 %), full range 2 of 3 (67 %), within 2x 2 of 3 (67 %).

## By chain

| chain | dishes | estimated | in band | in range | within 2x | order agreement (Spearman) | Roli's lightest pick: published rank |
|---|---|---|---|---|---|---|---|
| Pizza Express | 12 | 9 | 3 | 4 | 3 | 0.52 | Fresh Fruit & Yoghurt Bowl (2.0 g): 2 of 9 |
| Bonefish Grill | 8 | 7 | 5 | 5 | 4 | 0.82 | Shaved Brussels Sprouts Side Salad (2.5 g): 2 of 7 |
| Zizzi | 8 | 6 | 4 | 4 | 2 | 0.49 | Chips (3.6 g): 4 of 6 |
| Vapiano | 8 | 7 | 2 | 3 | 2 | 0.54 | Insalata Mista Piccola (0.0 g): 1 of 7 |
| Carrabba's Italian Grill | 6 | 6 | 2 | 2 | 4 | 0.37 | Shrimp Scampi (26.0 g): 5 of 6 |
| Prezzo | 5 | 5 | 3 | 3 | 3 | 0.70 | House Fries (1.4 g): 1 of 5 |
| Wasabi | 3 | 1 | 0 | 0 | 1 | n/a | Korean chicken katsu sando (1.8 g): 1 of 1 |

## By kind of dish (independent estimates)

| family | dishes | in band | in range | median ratio Roli / published |
|---|---|---|---|---|
| breakfast_cereal | 1 | 0 | 0 | 0.03 |
| breakfast_eggs | 1 | 0 | 0 | 0.26 |
| burger | 1 | 1 | 1 | 0.80 |
| dessert | 3 | 1 | 1 | 0.63 |
| dip | 1 | 0 | 0 | 9.08 |
| fish_main | 2 | 2 | 2 | 2.12 |
| fish_starter | 2 | 1 | 1 | 0.24 |
| fried_potato_side | 2 | 1 | 1 | 0.50 |
| kids_dish | 3 | 2 | 3 | 1.11 |
| leaf_salad_starter | 1 | 1 | 1 | 2.04 |
| meat_main | 2 | 2 | 2 | 1.09 |
| pasta_main | 7 | 2 | 2 | 0.69 |
| sandwich | 1 | 0 | 0 | 1.43 |
| side_bread | 4 | 1 | 1 | 3.28 |
| side_salad | 2 | 1 | 1 | 0.81 |
| side_vegetable | 1 | 1 | 1 | 1.52 |
| snack_bowl | 2 | 0 | 0 | 2.62 |
| soup | 1 | 1 | 1 | 0.79 |
| vegetable_starter | 1 | 0 | 1 | 0.64 |

Cholesterol (Bonefish and Carrabba's publish it): inside the band 8 of 13 (62 %), inside the full range 9 of 13 (69 %).

## Every dish

| chain | dish | family | published g | Roli band g (middle) | full range g | in band | in range | Roli / published | status |
|---|---|---|---|---|---|---|---|---|---|
| Pizza Express | The Full Works - scrambled eggs | breakfast_eggs | 33 | 3.8-16.3 (8.4) | 2.0-19.6 | no | no | 0.26 | evaluated |
| Pizza Express | Tiramisu | dessert | 17.8 | 10.9-19.6 (11.2) | 9.8-20.7 | yes | yes | 0.63 | evaluated |
| Pizza Express | Smoky BBQ Chicken | pizza_neapolitan | 10.4 | no estimate | | | | | evaluated:  |
| Pizza Express | Garlic & Herbs dip | dip | 0.8 | 4.1-13.8 (7.3) | 3.0-28.4 | no | no | 9.08 | evaluated |
| Pizza Express | Bruschetta Originale | vegetable_starter | 3.3 | 1.5-2.8 (2.1) | 1.0-4.0 | no | yes | 0.64 | evaluated |
| Pizza Express | Pollo Pesto | pasta_main | 26.3 | 4.7-17.5 (12.5) | 3.9-21.7 | no | no | 0.48 | evaluated |
| Pizza Express | Grand Chicken Caesar Salad | leaf_salad_starter | 8.8 | no estimate | | | | | evaluated:  |
| Pizza Express | Garlic Bread | side_bread | 2.5 | 6.6-16.4 (10.8) | 5.9-25.0 | no | no | 4.34 | evaluated |
| Pizza Express | Blueberries & Mascarpone Pancakes | breakfast_pancakes | 6.3 | no estimate | | | | | evaluated:  |
| Pizza Express | Cajun Prawns | fish_starter | 9.4 | 0.1-14.9 (2.5) | 0.1-21.2 | yes | yes | 0.26 | evaluated |
| Pizza Express | Polenta Chips | side_vegetable | 4 | 2.7-14.2 (6.1) | 1.9-18.4 | yes | yes | 1.52 | evaluated |
| Pizza Express | Fresh Fruit & Yoghurt Bowl | breakfast_cereal | 2 | 0.0-0.2 (0.1) | 0.0-0.3 | no | no | 0.03 | evaluated |
| Bonefish Grill | Grilled Rainbow Trout | fish_main (dependent) | 3.5 | 2.9-15.5 (10.9) | 2.2-19.4 | yes | yes | 3.13 | evaluated |
| Bonefish Grill | Grilled 9 oz Sirloin | meat_main | 11 | 8.7-16.4 (11.8) | 7.1-19.8 | yes | yes | 1.07 | evaluated |
| Bonefish Grill | Creamy Tomato Linguine with Chicke | pasta_main | 33 | 7.1-30.3 (22.7) | 6.6-32.2 | no | no | 0.69 | evaluated |
| Bonefish Grill | Calamari, Appetizer | fish_starter | 11 | no estimate | | | | | evaluated:  |
| Bonefish Grill | Tomato Bisque Soup cup | soup | 12 | 3.9-17.6 (9.5) | 3.2-20.1 | yes | yes | 0.79 | evaluated |
| Bonefish Grill | Bourbon Brownie | dessert | 63 | 6.8-25.0 (14.7) | 6.0-30.1 | no | no | 0.23 | evaluated |
| Bonefish Grill | Kids Chicken Bites | kids_dish | 2 | 1.5-8.5 (4.2) | 0.7-11.6 | yes | yes | 2.11 | evaluated |
| Bonefish Grill | Shaved Brussels Sprouts Side Salad | side_salad | 2.5 | 1.2-3.3 (2.0) | 1.0-3.9 | yes | yes | 0.81 | evaluated |
| Zizzi | Kids Spaghetti Bolognese | kids_dish | 2 | 1.1-4.1 (2.2) | 0.7-6.5 | yes | yes | 1.11 | evaluated |
| Zizzi | Vanilla Gelato | dessert | 1.8 | no estimate | | | | | evaluated:  |
| Zizzi | Bolognese Classico | pasta_main | 4.3 | 1.4-5.9 (4.3) | 1.4-6.6 | yes | yes | 1.00 | evaluated |
| Zizzi | Hot Honey Glazed Duck | meat_main | 14 | no estimate | | | | | evaluated:  |
| Zizzi | Garlic Bread | side_bread | 3.4 | 6.7-16.6 (11.3) | 5.9-25.0 | no | no | 3.32 | evaluated |
| Zizzi | Mediterranean Sea Bass | fish_main | 5.2 | 2.3-38.8 (24.9) | 1.6-46.7 | yes | yes | 4.79 | evaluated |
| Zizzi | Chips | fried_potato_side | 3.6 | 0.3-3.6 (0.4) | 0.2-4.1 | yes | yes | 0.12 | evaluated |
| Zizzi | Olives | snack_bowl | 1.3 | 2.2-7.8 (3.0) | 1.6-10.2 | no | no | 2.30 | evaluated |
| Vapiano | Pesto basilico | pasta_main | 2.6 | 5.3-23.9 (9.8) | 5.0-24.4 | no | no | 3.77 | evaluated |
| Vapiano | Verdure | pizza_neapolitan | 16.1 | no estimate | | | | | evaluated:  |
| Vapiano | Pistachio Truffle Dolci | dessert | 4.8 | 13.4-28.8 (20.0) | 11.8-38.9 | no | no | 4.16 | evaluated |
| Vapiano | Pizza prosciutto e funghi | kids_dish | 6.8 | 2.6-5.6 (3.8) | 1.8-7.1 | no | yes | 0.57 | evaluated |
| Vapiano | Insalata Mista Della Casa with no  | leaf_salad_starter | 2.1 | 1.7-8.9 (4.3) | 1.0-15.4 | yes | yes | 2.04 | evaluated |
| Vapiano | Pizza Bread Garlic | side_bread | 1.9 | 3.6-10.3 (6.1) | 2.9-14.4 | no | no | 3.24 | evaluated |
| Vapiano | Insalata Mista Piccola | side_salad | 0 | 1.2-4.9 (2.2) | 1.0-9.0 | no | no |  | evaluated |
| Vapiano | Antipasti Caprese | tomato_salad_starter (dependent) | 20.8 | 5.4-25.4 (14.8) | 5.3-22.8 | yes | yes | 0.71 | evaluated |
| Carrabba's Italian Grill | Shrimp and Scallop Linguine Alla V | pasta_main | 13 | 2.6-11.3 (8.4) | 2.5-11.9 | no | no | 0.65 | evaluated |
| Carrabba's Italian Grill | Salmon Caperi | fish_main | 16 | 7.6-49.9 (15.1) | 5.6-59.9 | yes | yes | 0.94 | evaluated |
| Carrabba's Italian Grill | Tuscan Grilled Ribeye, 16 oz. | meat_main | 18 | 13.6-27.0 (19.9) | 12.2-33.2 | yes | yes | 1.11 | evaluated |
| Carrabba's Italian Grill | Shrimp Scampi | fish_starter | 26 | 2.4-14.5 (5.8) | 1.2-20.0 | no | no | 0.22 | evaluated |
| Carrabba's Italian Grill | Tomato Caprese with Fresh Burrata | tomato_salad_starter (dependent) | 17 | 7.5-11.0 (9.4) | 5.8-13.3 | no | no | 0.55 | evaluated |
| Carrabba's Italian Grill | Filet and Shrimp Pasta Toscana | pasta_main | 83 | 8.5-40.2 (24.2) | 6.7-50.2 | no | no | 0.29 | evaluated |
| Prezzo | Salmon, Tomato & Basil Rigatoni | pasta_main | 12 | 3.0-29.6 (8.7) | 1.8-39.2 | yes | yes | 0.72 | evaluated |
| Prezzo | Truffle Gorgonzola Burger - Chicke | burger | 15 | 5.1-18.5 (12.0) | 4.3-19.7 | yes | yes | 0.80 | evaluated |
| Prezzo | House Fries | fried_potato_side | 1.4 | 2.1-3.9 (3.0) | 1.9-4.1 | no | no | 2.15 | evaluated |
| Prezzo | Garlic Bread With Mozzarella | side_bread | 10 | 8.9-32.5 (15.2) | 6.7-56.9 | yes | yes | 1.52 | flagged |
| Prezzo | Olives | snack_bowl | 1.7 | 2.8-7.5 (5.1) | 1.7-9.5 | no | no | 2.99 | flagged |
| Wasabi | Spicy chicken tom yum | soup | 17.95 | no estimate | | | | | evaluated:  |
| Wasabi | Korean chicken katsu sando | sandwich | 1.8 | 2.3-2.9 (2.6) | 2.2-2.9 | no | no | 1.43 | evaluated |
| Wasabi | Porridge pot with berry compote | breakfast_cereal | 2.95 | no estimate | | | | | evaluated:  |

## The model alone, names only (experiment, 2026-11-08)

The same 50 dishes, names and sections only, to google/gemini-3.8-flash with no tools, recipes or data; one call per typed menu; it gave a best guess and an 80 % range per dish. Spend $0.014188. The answers never enter Roli. Per dish: `known_answer_llm_only_2026-11-08b.csv`.

On the 38 independent dishes both answered:

| measure | the model alone | Roli |
|---|---|---|
| published figure inside its own range (each claims 8 in 10) | 21 of 38 (55 %) | 17 of 38 (45 %) |
| best guess / middle within a factor of 2 | 22 of 38 (58 %) | 17 of 38 (45 %) |
| typical miss | 1.80x | 2.10x |
| median ratio to published (1 = no lean) | 1.50 | 1.00 |
| too high / too low | 25 / 12 | 18 / 19 |

Head to head, dish by dish: the model alone was closer on 21 of 38, Roli on 17.
On all 46 independent dishes the model alone answered every one; its range held the published figure 26 of 46 (57 %).
Cholesterol (Bonefish and Carrabba's): the model alone's range held the published figure 9 of 14 (64 %); best guess within 2x 13 of 14 (93 %).

| chain | order agreement, model alone (Spearman) | order agreement, Roli | model alone's lightest pick: published rank |
|---|---|---|---|
| Pizza Express | 0.80 | 0.52 | Bruschetta Originale (3.3 g): 4 of 12 |
| Bonefish Grill | 0.90 | 0.82 | Shaved Brussels Sprouts Side Salad (2.5 g): 2 of 8 |
| Zizzi | 0.48 | 0.49 | Olives (1.3 g): 1 of 8 |
| Vapiano | 0.73 | 0.54 | Insalata Mista Della Casa with no dressing (2.1 g): 3 of 8 |
| Carrabba's Italian Grill | 0.31 | 0.37 | Salmon Caperi (16 g): 2 of 6 |
| Prezzo | 0.60 | 0.70 | Olives (1.7 g): 2 of 5 |
| Wasabi | -0.87 | n/a | Spicy chicken tom yum (17.95 g): 3 of 3 |

| chain | dish | published g | model alone: best (80 % range) | Roli: middle (band) | closer |
|---|---|---|---|---|---|
| Pizza Express | The Full Works - scrambled eggs | 33 | 26 (15-40) | 8.4 (3.8-16.3) | model alone |
| Pizza Express | Tiramisu | 17.8 | 20 (12-32) | 11.2 (10.9-19.6) | model alone |
| Pizza Express | Smoky BBQ Chicken (dependent) | 10.4 | 18 (10-30) | no estimate |  |
| Pizza Express | Garlic & Herbs dip | 0.8 | 5 (2-12) | 7.3 (4.1-13.8) | model alone |
| Pizza Express | Bruschetta Originale | 3.3 | 3 (1-7) | 2.1 (1.5-2.8) | model alone |
| Pizza Express | Pollo Pesto | 26.3 | 28 (18-45) | 12.5 (4.7-17.5) | model alone |
| Pizza Express | Grand Chicken Caesar Salad | 8.8 | 8 (4-15) | no estimate |  |
| Pizza Express | Garlic Bread | 2.5 | 9 (4-18) | 10.8 (6.6-16.4) | model alone |
| Pizza Express | Blueberries & Mascarpone Pancakes | 6.3 | 24 (14-38) | no estimate |  |
| Pizza Express | Cajun Prawns | 9.4 | 8 (3-16) | 2.5 (0.1-14.9) | model alone |
| Pizza Express | Polenta Chips | 4 | 6 (2-14) | 6.1 (2.7-14.2) | model alone |
| Pizza Express | Fresh Fruit & Yoghurt Bowl | 2 | 4 (1-9) | 0.1 (0.0-0.2) | model alone |
| Bonefish Grill | Grilled Rainbow Trout (dependent) | 3.5 | 7 (3-14) | 10.9 (2.9-15.5) | model alone |
| Bonefish Grill | Grilled 9 oz Sirloin | 11 | 13 (7-22) | 11.8 (8.7-16.4) | Roli |
| Bonefish Grill | Creamy Tomato Linguine with Chicke | 33 | 26 (14-45) | 22.7 (7.1-30.3) | model alone |
| Bonefish Grill | Calamari, Appetizer | 11 | 7 (3-15) | no estimate |  |
| Bonefish Grill | Tomato Bisque Soup cup | 12 | 9 (4-18) | 9.5 (3.9-17.6) | Roli |
| Bonefish Grill | Bourbon Brownie | 63 | 24 (12-40) | 14.7 (6.8-25.0) | model alone |
| Bonefish Grill | Kids Chicken Bites | 2 | 6 (3-12) | 4.2 (1.5-8.5) | Roli |
| Bonefish Grill | Shaved Brussels Sprouts Side Salad | 2.5 | 4.5 (1.5-10) | 2.0 (1.2-3.3) | Roli |
| Zizzi | Kids Spaghetti Bolognese | 2 | 6 (3-12) | 2.2 (1.1-4.1) | Roli |
| Zizzi | Vanilla Gelato | 1.8 | 10 (5-16) | no estimate |  |
| Zizzi | Bolognese Classico | 4.3 | 12 (6-22) | 4.3 (1.4-5.9) | Roli |
| Zizzi | Hot Honey Glazed Duck | 14 | 16 (8-28) | no estimate |  |
| Zizzi | Garlic Bread | 3.4 | 9 (4-18) | 11.3 (6.7-16.6) | model alone |
| Zizzi | Mediterranean Sea Bass | 5.2 | 5 (2-10) | 24.9 (2.3-38.8) | model alone |
| Zizzi | Chips | 3.6 | 4 (2-9) | 0.4 (0.3-3.6) | model alone |
| Zizzi | Olives | 1.3 | 2.5 (1-5) | 3.0 (2.2-7.8) | model alone |
| Vapiano | Pesto basilico | 2.6 | 12 (6-20) | 9.8 (5.3-23.9) | Roli |
| Vapiano | Verdure | 16.1 | 15 (8-24) | no estimate |  |
| Vapiano | Pistachio Truffle Dolci | 4.8 | 22 (12-35) | 20.0 (13.4-28.8) | Roli |
| Vapiano | Pizza prosciutto e funghi | 6.8 | 11 (6-18) | 3.8 (2.6-5.6) | model alone |
| Vapiano | Insalata Mista Della Casa with no  | 2.1 | 0.2 (0-1) | 4.3 (1.7-8.9) | Roli |
| Vapiano | Pizza Bread Garlic | 1.9 | 6 (2-14) | 6.1 (3.6-10.3) | model alone |
| Vapiano | Insalata Mista Piccola | 0 | 1.5 (0.5-4) | 2.2 (1.2-4.9) |  |
| Vapiano | Antipasti Caprese (dependent) | 20.8 | 15 (8-24) | 14.8 (5.4-25.4) | model alone |
| Carrabba's Italian Grill | Shrimp and Scallop Linguine Alla V | 13 | 26 (14-42) | 8.4 (2.6-11.3) | Roli |
| Carrabba's Italian Grill | Salmon Caperi | 16 | 10 (4-18) | 15.1 (7.6-49.9) | Roli |
| Carrabba's Italian Grill | Tuscan Grilled Ribeye, 16 oz. | 18 | 42 (28-62) | 19.9 (13.6-27.0) | Roli |
| Carrabba's Italian Grill | Shrimp Scampi | 26 | 18 (10-30) | 5.8 (2.4-14.5) | model alone |
| Carrabba's Italian Grill | Tomato Caprese with Fresh Burrata (dependent) | 17 | 20 (12-32) | 9.4 (7.5-11.0) | model alone |
| Carrabba's Italian Grill | Filet and Shrimp Pasta Toscana | 83 | 28 (16-45) | 24.2 (8.5-40.2) | model alone |
| Prezzo | Salmon, Tomato & Basil Rigatoni | 12 | 8 (3-16) | 8.7 (3.0-29.6) | Roli |
| Prezzo | Truffle Gorgonzola Burger - Chicke | 15 | 16 (8-28) | 12.0 (5.1-18.5) | model alone |
| Prezzo | House Fries | 1.4 | 5 (2-10) | 3.0 (2.1-3.9) | Roli |
| Prezzo | Garlic Bread With Mozzarella | 10 | 17 (8-30) | 15.2 (8.9-32.5) | Roli |
| Prezzo | Olives | 1.7 | 2 (1-4) | 5.1 (2.8-7.5) | model alone |
| Wasabi | Spicy chicken tom yum | 17.95 | 2.5 (1-6) | no estimate |  |
| Wasabi | Korean chicken katsu sando | 1.8 | 12 (6-22) | 2.6 (2.3-2.9) | Roli |
| Wasabi | Porridge pot with berry compote | 2.95 | 2.5 (0.5-6) | no estimate |  |
