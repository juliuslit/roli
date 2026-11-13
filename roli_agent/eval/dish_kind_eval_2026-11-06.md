# Dish kind: the model against the word lists, dish_kind_labels_2026-11-06.csv

Model google/gemini-3.8-flash, prompt version b42cb8a17fd8. 400 food items on 13 menus, labelled by hand (proposal); 92 marked unsure.

Spend: $0.072409, 13 calls. Fallbacks to the word lists: 0; failed calls: [].

## Overall

| classifier | correct | of | accuracy |
|---|---|---|---|
| word lists (3I) | 347 | 400 | 86.8 % |
| word lists (3H) | 164 | 400 | 41.0 % |
| model | 378 | 400 | 94.5 % |

On the items not marked unsure:

| classifier | correct | of | accuracy |
|---|---|---|---|
| word lists (3I) | 308 | 308 | 100.0 % |
| word lists (3H) | 147 | 308 | 47.7 % |
| model | 296 | 308 | 96.1 % |

## The 3H failure cases

| case | items | word lists (3I) | word lists (3H) | model |
|---|---|---|---|---|
| dip | 9 | 9 | 0 | 9 |
| invented pizza name | 25 | 25 | 25 | 25 |
| misspelt fish | 1 | 1 | 0 | 1 |
| mixed section (starters, salads, sides, dips) | 10 | 0 | 0 | 9 |
| shellfish | 16 | 15 | 15 | 14 |
| soup | 22 | 22 | 0 | 22 |

## Per family (the label's family)

| family | items | word lists (3I) | word lists (3H) | model |
|---|---|---|---|---|
| vegetable_starter | 55 | 29 | 29 | 43 |
| fish_main | 37 | 37 | 36 | 34 |
| pasta_main | 32 | 32 | 11 | 31 |
| pizza_neapolitan | 31 | 31 | 31 | 31 |
| meat_main | 30 | 29 | 29 | 30 |
| soup | 22 | 22 | 0 | 22 |
| side_rice | 21 | 20 | 0 | 21 |
| dessert | 17 | 17 | 0 | 17 |
| fried_potato_side | 16 | 10 | 0 | 16 |
| sandwich | 16 | 16 | 0 | 16 |
| breakfast_eggs | 13 | 12 | 0 | 12 |
| dip | 13 | 13 | 0 | 13 |
| leaf_salad_starter | 12 | 7 | 7 | 10 |
| burger | 11 | 11 | 0 | 11 |
| taco | 10 | 10 | 0 | 10 |
| (none) | 9 | 6 | 8 | 7 |
| side_bread | 8 | 4 | 0 | 7 |
| side_vegetable | 7 | 6 | 0 | 7 |
| crudo_starter | 6 | 6 | 6 | 6 |
| quesadilla | 6 | 6 | 0 | 6 |
| fish_starter | 5 | 2 | 2 | 5 |
| kids_dish | 5 | 5 | 0 | 5 |
| snack_bowl | 4 | 3 | 3 | 4 |
| breakfast_cereal | 4 | 4 | 0 | 4 |
| toast_plate | 3 | 3 | 0 | 3 |
| breakfast_pancakes | 3 | 2 | 0 | 3 |
| side_salad | 2 | 2 | 0 | 2 |
| tomato_salad_starter | 1 | 1 | 1 | 1 |
| fish_and_chips | 1 | 1 | 1 | 1 |

**12.16.12: the model goes live only if it is at least as accurate overall (378 vs 347) and on every 3H failure case (no): not met.**

## Where the model and the label disagree

| menu | item | section | label | model | model said | unsure |
|---|---|---|---|---|---|---|
| 23 | CRUMBED WHITING | TASTE OF THE SEA | fish_main | fish_starter | fish_starter |  |
| 23 | CHILLED MOOLOOLABA PRAWNS | TASTE OF THE SEA | fish_main | fish_starter | fish_starter | yes |
| 04 | TORTELLINI IN BRODO |  | pasta_main | soup | soup |  |
| 05 | PORK & ONION CHUTNEY SAUSAGE ROLLS | ON THE COUNTER | vegetable_starter | meat_main | meat_main | yes |
| 05 | GIANT SCOTCH EGGS | ON THE COUNTER | vegetable_starter | meat_main | meat_main | yes |
| 05 | QUICHE OF THE DAY | ON THE COUNTER | breakfast_eggs | vegetable_starter | vegetable_starter | yes |
| 05 | SAVOURY PASTRIES FROM | ON THE COUNTER | (none) | vegetable_starter | vegetable_starter | yes |
| 05 | FRESHLY MADE SALAD | FRESH SALADS | leaf_salad_starter | side_salad | side_salad |  |
| 05 | FRESHLY BAKED JACKETS | JACKET POTATOES | (none) | vegetable_starter | vegetable_starter | yes |
| 06 | STICKS & DIP | STARTERS, SALADS, SI | side_bread | vegetable_starter | vegetable_starter | yes |
| 10 | Chicken Fooyong | APPETIZERS | vegetable_starter | meat_main | meat_main |  |
| 10 | Chicken Spring Rolls | APPETIZERS | vegetable_starter | meat_main | meat_main |  |
| 10 | Mixed Spring Rolls | APPETIZERS | vegetable_starter | meat_main | meat_main |  |
| 10 | Fried Chicken Wanton | APPETIZERS | vegetable_starter | meat_main | meat_main |  |
| 10 | Spring Chicken | APPETIZERS | vegetable_starter | meat_main | meat_main |  |
| 10 | Chicken Drumsticks | APPETIZERS | vegetable_starter | meat_main | meat_main | yes |
| 10 | Pepper Chicken | APPETIZERS | vegetable_starter | meat_main | meat_main |  |
| 10 | Chicken Pakoda | APPETIZERS | vegetable_starter | meat_main | meat_main |  |
| 10 | Chicken Steam Momo | MOMO | vegetable_starter | meat_main | meat_main | yes |
| 10 | Chicken Fried Momo | MOMO | vegetable_starter | meat_main | meat_main | yes |
| 10 | Green Salad | VEGETARIAN DISHES | leaf_salad_starter | side_salad | side_salad |  |
| 10 | Prawn Chips | PRAWN | fish_main | fish_starter | fish_starter |  |

## Where the word lists and the label disagree

| menu | item | section | label | word lists | unsure |
|---|---|---|---|---|---|
| 01 | House-cured anchovies with celery, Parmi |  | fish_starter | vegetable_starter | yes |
| 01 | Bowl of polenta with mascarpone or Parmi |  | vegetable_starter | (none) | yes |
| 23 | BATTERED OYSTERS | TASTE OF THE SEA | fish_starter | fish_main | yes |
| 02 | House-cured anchovies with celery, Parmi |  | fish_starter | vegetable_starter | yes |
| 02 | Bowl of polenta with mascarpone or Parmi |  | vegetable_starter | (none) | yes |
| 05 | PORK & ONION CHUTNEY SAUSAGE ROLLS | ON THE COUNTER | vegetable_starter | meat_main | yes |
| 05 | VEGAN SAUSAGE ROLLS | ON THE COUNTER | vegetable_starter | meat_main | yes |
| 05 | GIANT SCOTCH EGGS | ON THE COUNTER | vegetable_starter | (none) | yes |
| 05 | QUICHE OF THE DAY | ON THE COUNTER | breakfast_eggs | (none) | yes |
| 06 | COLESLAW | STARTERS, SALADS, SI | side_vegetable | dip | yes |
| 06 | STICKS & DIP | STARTERS, SALADS, SI | side_bread | dip | yes |
| 06 | OLIVES | STARTERS, SALADS, SI | snack_bowl | dip | yes |
| 06 | GARLIC BREAD | STARTERS, SALADS, SI | side_bread | dip | yes |
| 06 | GARLIC BREAD WITH CHEESE | STARTERS, SALADS, SI | side_bread | dip | yes |
| 06 | GARDEN SALAD | STARTERS, SALADS, SI | leaf_salad_starter | dip | yes |
| 06 | GREEK SALAD | STARTERS, SALADS, SI | leaf_salad_starter | dip | yes |
| 06 | 'N'DUJA SALAD | STARTERS, SALADS, SI | leaf_salad_starter | dip | yes |
| 06 | GOATS CHEESE SALAD | STARTERS, SALADS, SI | leaf_salad_starter | dip | yes |
| 06 | PARMA SALAD | STARTERS, SALADS, SI | leaf_salad_starter | dip | yes |
| 06 | CHARCUTERIE PLATTER | STARTERS, SALADS, SI | (none) | dip | yes |
| 06 | CHARCUTERIE & CHEESE PLATTER | STARTERS, SALADS, SI | (none) | dip | yes |
| 10 | Veg Steam Momo | MOMO | vegetable_starter | (none) | yes |
| 10 | Veg Fried Momo | MOMO | vegetable_starter | (none) | yes |
| 10 | Chicken Steam Momo | MOMO | vegetable_starter | meat_main | yes |
| 10 | Chicken Fried Momo | MOMO | vegetable_starter | meat_main | yes |
| 10 | Vegetable Chow Chow | VEGETARIAN DISHES | vegetable_starter | (none) | yes |
| 10 | Vegetable Sweet & Sour | VEGETARIAN DISHES | vegetable_starter | (none) | yes |
| 10 | Chilli Vegetable | VEGETARIAN DISHES | vegetable_starter | (none) | yes |
| 10 | Hot Garlic Vegetable | VEGETARIAN DISHES | vegetable_starter | (none) | yes |
| 10 | Vegetable Manchuria | VEGETARIAN DISHES | vegetable_starter | (none) | yes |
| 10 | Vegetable 65 | VEGETARIAN DISHES | vegetable_starter | (none) | yes |
| 10 | Ginger Vegetable | VEGETARIAN DISHES | vegetable_starter | (none) | yes |
| 10 | Sichuan Vegetable | VEGETARIAN DISHES | vegetable_starter | (none) | yes |
| 10 | Fried Crispy Veg. In Pickle Sauce | VEGETARIAN DISHES | vegetable_starter | (none) | yes |
| 10 | Baby Corn Manchuria | VEGETARIAN DISHES | vegetable_starter | (none) | yes |
| 10 | Chilli Baby Corn | VEGETARIAN DISHES | vegetable_starter | (none) | yes |
| 10 | Vegetable with Cashewnut | VEGETARIAN DISHES | vegetable_starter | (none) | yes |
| 10 | Tofu manchuria (Chinese Paneer) | VEGETARIAN DISHES | vegetable_starter | (none) | yes |
| 10 | Stir Fry Tofu With Mix Vegetable | VEGETARIAN DISHES | vegetable_starter | (none) | yes |
| 10 | Chilli Paneer | VEGETARIAN DISHES | vegetable_starter | (none) | yes |
| 10 | Diced Paneer | VEGETARIAN DISHES | vegetable_starter | (none) | yes |
| 10 | Paneer 65 | VEGETARIAN DISHES | vegetable_starter | (none) | yes |
| 10 | Prawn Fried Rice | RICE | side_rice | fish_main | yes |
| 11 | TORTILLAS & SALSA | SIDES | side_bread | dip | yes |
| 11 | AL PASTOR O.G. | mothers FRIES | fried_potato_side | (none) | yes |
| 11 | CHILORIO DIRTY | mothers FRIES | fried_potato_side | (none) | yes |
| 11 | SUADERO DIRTY | mothers FRIES | fried_potato_side | (none) | yes |
| 11 | CARNE ASADA | mothers FRIES | fried_potato_side | (none) | yes |
| 11 | VEGETARIAN | mothers FRIES | fried_potato_side | (none) | yes |
| 11 | POLLO ASADO | mothers FRIES | fried_potato_side | (none) | yes |
| 19 | Sausage |  | (none) | meat_main | yes |
| 19 | HAMBURGER STEAK PLATE |  | meat_main | burger | yes |
| 19 | No. 5 | BREAKFAST SUGGESTION | breakfast_pancakes | (none) | yes |
