# Recall check, 2026-11-08b

Does google/gemini-3.8-flash recognise these 50 chain dishes, and can it quote their published figures? Two probes, one call each per typed menu; spend $0.014420; nothing enters Roli. Per dish: `known_answer_recall_2026-11-08b.csv`.

## 1. Naming the restaurant from the menu (no chain name given)

| menu (truth) | the model's answer | confidence | dishes it attributed to the right chain |
|---|---|---|---|
| Pizza Express | PizzaExpress | high | 12 of 12 |
| Bonefish Grill | Moxies | high | 0 of 8 |
| Zizzi | Bella Italia | high | 0 of 8 |
| Vapiano | Vapiano | high | 8 of 8 |
| Carrabba's Italian Grill | Carrabba's Italian Grill | high | 6 of 6 |
| Prezzo | Wildwood | high | 0 of 5 |
| Wasabi | Waitrose | medium | 0 of 3 |

Overall: the right restaurant for 3 of 7 menus; the right chain for 26 of 50 (52 %) dishes.

## 2. Quoting the published figure (chain named, do not estimate)

It claimed to know the published saturated fat for 32 of 50 (64 %) dishes. Of those, the quoted figure was within 10 % of the published one for 3 of 32 (9 %), within 25 % for 9 of 32 (28 %).

Cholesterol quoted for 9 Bonefish or Carrabba's dishes; within 10 % for 4 of 9 (44 %).

## 3. Were the name-only guesses better where it recognised the chain?

| group | dishes | name-only guess within a factor of 2 | within 25 % | typical miss |
|---|---|---|---|---|
| dish attributed to the right chain | 26 | 16 | 7 | 1.62x |
| not attributed | 24 | 15 | 7 | 1.75x |

| chain | dish | published g | attributed to | quoted (known?) | name-only guess |
|---|---|---|---|---|---|
| Pizza Express | The Full Works - scrambled eggs | 33 | PizzaExpress (high) |  (no) | 26 |
| Pizza Express | Tiramisu | 17.8 | PizzaExpress (medium) | 19.3 (yes) | 20 |
| Pizza Express | Smoky BBQ Chicken | 10.4 | PizzaExpress (high) |  (no) | 18 |
| Pizza Express | Garlic & Herbs dip | 0.8 | PizzaExpress (high) | 1.7 (yes) | 5 |
| Pizza Express | Bruschetta Originale | 3.3 | PizzaExpress (high) | 2.1 (yes) | 3 |
| Pizza Express | Pollo Pesto | 26.3 | PizzaExpress (high) | 16.2 (yes) | 28 |
| Pizza Express | Grand Chicken Caesar Salad | 8.8 | PizzaExpress (high) | 8 (yes) | 8 |
| Pizza Express | Garlic Bread | 2.5 | PizzaExpress (medium) | 6.8 (yes) | 9 |
| Pizza Express | Blueberries & Mascarpone Pancakes | 6.3 | PizzaExpress (high) |  (no) | 24 |
| Pizza Express | Cajun Prawns | 9.4 | PizzaExpress (high) |  (no) | 8 |
| Pizza Express | Polenta Chips | 4 | PizzaExpress (high) | 3.7 (yes) | 6 |
| Pizza Express | Fresh Fruit & Yoghurt Bowl | 2 | PizzaExpress (high) |  (no) | 4 |
| Bonefish Grill | Grilled Rainbow Trout | 3.5 | unknown (low) | 8 (yes) | 7 |
| Bonefish Grill | Grilled 9 oz Sirloin | 11 | unknown (low) | 9 (yes) | 13 |
| Bonefish Grill | Creamy Tomato Linguine with Chicke | 33 | unknown (low) |  (no) | 26 |
| Bonefish Grill | Calamari, Appetizer | 11 | Moxies (high) | 4 (yes) | 7 |
| Bonefish Grill | Tomato Bisque Soup cup | 12 | unknown (low) |  (no) | 9 |
| Bonefish Grill | Bourbon Brownie | 63 | Moxies (high) |  (no) | 24 |
| Bonefish Grill | Kids Chicken Bites | 2 | Moxies (high) | 2.5 (yes) | 6 |
| Bonefish Grill | Shaved Brussels Sprouts Side Salad | 2.5 | unknown (low) |  (no) | 4.5 |
| Zizzi | Kids Spaghetti Bolognese | 2 | Bella Italia (high) | 3.7 (yes) | 6 |
| Zizzi | Vanilla Gelato | 1.8 | Bella Italia (medium) | 6.8 (yes) | 10 |
| Zizzi | Bolognese Classico | 4.3 | Bella Italia (high) | 10 (yes) | 12 |
| Zizzi | Hot Honey Glazed Duck | 14 | Bella Italia (high) |  (no) | 16 |
| Zizzi | Garlic Bread | 3.4 | Bella Italia (medium) | 8 (yes) | 9 |
| Zizzi | Mediterranean Sea Bass | 5.2 | Bella Italia (high) |  (no) | 5 |
| Zizzi | Chips | 3.6 | Bella Italia (medium) | 1.9 (yes) | 4 |
| Zizzi | Olives | 1.3 | Bella Italia (medium) | 1.7 (yes) | 2.5 |
| Vapiano | Pesto basilico | 2.6 | Vapiano (high) | 13.9 (yes) | 12 |
| Vapiano | Verdure | 16.1 | Vapiano (high) | 6.8 (yes) | 15 |
| Vapiano | Pistachio Truffle Dolci | 4.8 | Vapiano (high) |  (no) | 22 |
| Vapiano | Pizza prosciutto e funghi | 6.8 | Vapiano (medium) | 18 (yes) | 11 |
| Vapiano | Insalata Mista Della Casa with no  | 2.1 | Vapiano (high) | 0.1 (yes) | 0.2 |
| Vapiano | Pizza Bread Garlic | 1.9 | Vapiano (high) | 2.2 (yes) | 6 |
| Vapiano | Insalata Mista Piccola | 0 | Vapiano (high) | 0.1 (yes) | 1.5 |
| Vapiano | Antipasti Caprese | 20.8 | Vapiano (high) | 13.1 (yes) | 15 |
| Carrabba's Italian Grill | Shrimp and Scallop Linguine Alla V | 13 | Carrabba's Italian Grill (high) | 39 (yes) | 26 |
| Carrabba's Italian Grill | Salmon Caperi | 16 | Carrabba's Italian Grill (high) | 20 (yes) | 10 |
| Carrabba's Italian Grill | Tuscan Grilled Ribeye, 16 oz. | 18 | Carrabba's Italian Grill (high) | 38 (yes) | 42 |
| Carrabba's Italian Grill | Shrimp Scampi | 26 | Carrabba's Italian Grill (high) | 29 (yes) | 18 |
| Carrabba's Italian Grill | Tomato Caprese with Fresh Burrata | 17 | Carrabba's Italian Grill (high) | 19 (yes) | 20 |
| Carrabba's Italian Grill | Filet and Shrimp Pasta Toscana | 83 | Carrabba's Italian Grill (high) |  (no) | 28 |
| Prezzo | Salmon, Tomato & Basil Rigatoni | 12 | Wildwood (high) |  (no) | 8 |
| Prezzo | Truffle Gorgonzola Burger - Chicke | 15 | Wildwood (high) |  (no) | 16 |
| Prezzo | House Fries | 1.4 | Wildwood (medium) |  (no) | 5 |
| Prezzo | Garlic Bread With Mozzarella | 10 | Wildwood (high) |  (no) | 17 |
| Prezzo | Olives | 1.7 | Wildwood (medium) |  (no) | 2 |
| Wasabi | Spicy chicken tom yum | 17.95 | itsu (high) | 6.8 (yes) | 2.5 |
| Wasabi | Korean chicken katsu sando | 1.8 | unknown (low) | 3.7 (yes) | 12 |
| Wasabi | Porridge pot with berry compote | 2.95 | unknown (low) | 1.7 (yes) | 2.5 |
