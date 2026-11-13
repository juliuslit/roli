# Known-answer check, 2026-11-08 (first run)

**Superseded by `known_answer_check_2026-11-08b.md`.** This run found a bug: the recipe pipeline's portion and weights steps took the dish kind from the word lists, not from the dish-kind call, so "Pollo Pesto" was sized as a pot of dip. Fixed the same afternoon and rerun as 2026-11-08b.

50 dishes from 7 chains, typed as menus of dish names and sections only (no descriptions), run through the normal pipeline with the tested chain's own items left out of the plate-weight samples. Published figure = the chain's own saturated fat per plate (`data/chain_sheets/`). Run settings: {'daily_budget_usd': '7.50', 'daily_search_credits': 500, 'per_menu': 'unchanged ($0.50, 30 credits)', 'leave_one_chain_out': True}.

Roli gave an estimate for 37 of 50 (74 %) of the dishes. Of the 34 independent estimates (families whose plate size does not rest on these sheets):

| measure | result |
|---|---|
| published figure inside Roli's band ("most plates", meant to hold 8 in 10) | 15 of 34 (44 %) |
| inside Roli's full range | 19 of 34 (56 %) |
| Roli's middle within a factor of 2 of the published figure | 17 of 34 (50 %) |
| typical size of the miss (median, as a factor) | 1.77x |
| direction: Roli's middle above / below the published figure | 14 above, 19 below; median ratio 0.80 |

Dependent families, reported apart (3 dishes): band 1 of 3 (33 %), full range 2 of 3 (67 %), within 2x 1 of 3 (33 %).

## By chain

| chain | dishes | estimated | in band | in range | within 2x | order agreement (Spearman) | Roli's lightest pick: published rank |
|---|---|---|---|---|---|---|---|
| Pizza Express | 12 | 9 | 3 | 4 | 3 | 0.17 | Fresh Fruit & Yoghurt Bowl (2.0 g): 2 of 9 |
| Bonefish Grill | 8 | 7 | 4 | 5 | 4 | 0.86 | Kids Chicken Bites (2.0 g): 1 of 7 |
| Zizzi | 8 | 5 | 2 | 3 | 1 | -0.10 | Chips (3.6 g): 4 of 5 |
| Vapiano | 8 | 5 | 2 | 4 | 3 | 0.90 | Insalata Mista Piccola (0.0 g): 1 of 5 |
| Carrabba's Italian Grill | 6 | 6 | 2 | 2 | 4 | 0.37 | Shrimp Scampi (26.0 g): 5 of 6 |
| Prezzo | 5 | 5 | 3 | 3 | 3 | 0.70 | House Fries (1.4 g): 1 of 5 |
| Wasabi | 3 | 0 | 0 | 0 | 0 | n/a |  |

## By kind of dish (independent estimates)

| family | dishes | in band | in range | median ratio Roli / published |
|---|---|---|---|---|
| breakfast_cereal | 1 | 0 | 0 | 0.03 |
| breakfast_eggs | 1 | 0 | 0 | 0.26 |
| burger | 1 | 1 | 1 | 0.80 |
| dessert | 2 | 1 | 1 | 0.38 |
| dip | 1 | 0 | 0 | 9.08 |
| fish_main | 1 | 1 | 1 | 0.94 |
| fish_starter | 2 | 1 | 1 | 0.24 |
| fried_potato_side | 2 | 1 | 1 | 0.50 |
| kids_dish | 3 | 1 | 3 | 2.11 |
| leaf_salad_starter | 1 | 1 | 1 | 1.06 |
| meat_main | 2 | 2 | 2 | 1.09 |
| pasta_main | 7 | 3 | 3 | 0.69 |
| side_bread | 3 | 1 | 1 | 3.32 |
| side_salad | 2 | 0 | 1 | 1.75 |
| side_vegetable | 1 | 1 | 1 | 1.52 |
| snack_bowl | 2 | 0 | 0 | 2.62 |
| soup | 1 | 1 | 1 | 0.79 |
| vegetable_starter | 1 | 0 | 1 | 0.64 |

Cholesterol (Bonefish and Carrabba's publish it): inside the band 9 of 13 (69 %), inside the full range 10 of 13 (77 %).

## Every dish

| chain | dish | family | published g | Roli band g (middle) | full range g | in band | in range | Roli / published | status |
|---|---|---|---|---|---|---|---|---|---|
| Pizza Express | The Full Works - scrambled eggs | breakfast_eggs | 33 | 3.8-16.3 (8.4) | 2.0-19.6 | no | no | 0.26 | evaluated |
| Pizza Express | Tiramisu | dessert | 17.8 | 10.9-19.6 (11.2) | 9.8-20.7 | yes | yes | 0.63 | evaluated |
| Pizza Express | Smoky BBQ Chicken | pizza_neapolitan | 10.4 | no estimate | | | | | evaluated:  |
| Pizza Express | Garlic & Herbs dip | dip | 0.8 | 4.1-13.8 (7.3) | 3.0-28.4 | no | no | 9.08 | evaluated |
| Pizza Express | Bruschetta Originale | vegetable_starter | 3.3 | 1.5-2.8 (2.1) | 1.0-4.0 | no | yes | 0.64 | evaluated |
| Pizza Express | Pollo Pesto | pasta_main | 26.3 | 1.4-4.3 (1.9) | 1.0-6.0 | no | no | 0.07 | evaluated |
| Pizza Express | Grand Chicken Caesar Salad | leaf_salad_starter | 8.8 | no estimate | | | | | evaluated:  |
| Pizza Express | Garlic Bread | side_bread | 2.5 | 6.6-16.4 (10.8) | 5.9-25.0 | no | no | 4.34 | evaluated |
| Pizza Express | Blueberries & Mascarpone Pancakes | breakfast_pancakes | 6.3 | no estimate | | | | | evaluated:  |
| Pizza Express | Cajun Prawns | fish_starter | 9.4 | 0.1-14.9 (2.5) | 0.1-21.2 | yes | yes | 0.26 | evaluated |
| Pizza Express | Polenta Chips | side_vegetable | 4 | 2.7-14.2 (6.1) | 1.9-18.4 | yes | yes | 1.52 | evaluated |
| Pizza Express | Fresh Fruit & Yoghurt Bowl | breakfast_cereal | 2 | 0.0-0.2 (0.1) | 0.0-0.3 | no | no | 0.03 | evaluated |
| Bonefish Grill | Grilled Rainbow Trout | fish_main (dependent) | 3.5 | 2.4-15.5 (11.1) | 2.2-19.4 | yes | yes | 3.16 | evaluated |
| Bonefish Grill | Grilled 9 oz Sirloin | meat_main | 11 | 8.7-16.4 (11.8) | 7.1-19.8 | yes | yes | 1.07 | evaluated |
| Bonefish Grill | Creamy Tomato Linguine with Chicke | pasta_main | 33 | 7.1-30.3 (22.7) | 6.6-32.2 | no | no | 0.69 | evaluated |
| Bonefish Grill | Calamari, Appetizer | fish_starter | 11 | no estimate | | | | | evaluated:  |
| Bonefish Grill | Tomato Bisque Soup cup | soup | 12 | 3.9-17.6 (9.5) | 3.2-20.1 | yes | yes | 0.79 | evaluated |
| Bonefish Grill | Bourbon Brownie | dessert | 63 | 6.8-25.0 (14.7) | 6.0-30.1 | no | no | 0.23 | evaluated |
| Bonefish Grill | Kids Chicken Bites | kids_dish | 2 | 1.5-8.5 (4.2) | 0.7-11.6 | yes | yes | 2.11 | evaluated |
| Bonefish Grill | Shaved Brussels Sprouts Side Salad | side_salad | 2.5 | 2.7-9.0 (4.4) | 2.3-9.8 | no | yes | 1.75 | evaluated |
| Zizzi | Kids Spaghetti Bolognese | kids_dish | 2 | 2.3-11.2 (5.3) | 1.4-14.9 | no | yes | 2.63 | evaluated |
| Zizzi | Vanilla Gelato | dessert | 1.8 | no estimate | | | | | evaluated:  |
| Zizzi | Bolognese Classico | pasta_main | 4.3 | 1.4-5.9 (4.3) | 1.4-6.6 | yes | yes | 1.00 | evaluated |
| Zizzi | Hot Honey Glazed Duck | meat_main | 14 | no estimate | | | | | evaluated:  |
| Zizzi | Garlic Bread | side_bread | 3.4 | 6.7-16.6 (11.3) | 5.9-25.0 | no | no | 3.32 | evaluated |
| Zizzi | Mediterranean Sea Bass | fish_main | 5.2 | no estimate | | | | | evaluated:  |
| Zizzi | Chips | fried_potato_side | 3.6 | 0.3-3.6 (0.4) | 0.2-4.1 | yes | yes | 0.12 | evaluated |
| Zizzi | Olives | snack_bowl | 1.3 | 2.2-7.8 (3.0) | 1.6-10.2 | no | no | 2.30 | evaluated |
| Vapiano | Pesto basilico | pasta_main | 2.6 | 1.3-4.7 (1.9) | 0.8-7.4 | yes | yes | 0.73 | evaluated |
| Vapiano | Verdure | pizza_neapolitan | 16.1 | no estimate | | | | | evaluated:  |
| Vapiano | Pistachio Truffle Dolci | dessert | 4.8 | no estimate | | | | | evaluated:  |
| Vapiano | Pizza prosciutto e funghi | kids_dish | 6.8 | 2.6-5.6 (3.8) | 1.8-7.1 | no | yes | 0.57 | evaluated |
| Vapiano | Insalata Mista Della Casa with no  | leaf_salad_starter | 2.1 | 1.0-7.1 (2.2) | 0.5-12.8 | yes | yes | 1.06 | evaluated |
| Vapiano | Pizza Bread Garlic | side_bread | 1.9 | no estimate | | | | | evaluated:  |
| Vapiano | Insalata Mista Piccola | side_salad | 0 | 0.9-3.8 (1.7) | 0.5-7.5 | no | no |  | evaluated |
| Vapiano | Antipasti Caprese | tomato_salad_starter (dependent) | 20.8 | 2.1-13.1 (6.0) | 0.9-22.5 | no | yes | 0.29 | evaluated |
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
| Wasabi | Korean chicken katsu sando | sandwich | 1.8 | no estimate | | | | | evaluated:  |
| Wasabi | Porridge pot with berry compote | breakfast_cereal | 2.95 | no estimate | | | | | evaluated:  |
