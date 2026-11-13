# Line-tag test set_2026-11-08_haiku

Model anthropic/claude-haiku-5.5; prompt version 4e6b3af61ba0; set `roli_agent/tests/fixtures/line_tag_test_set.json`.

## Run 1

- Role correct: 127 of 136
- Real pages (12.12.9): role correct 35 of 37, harmful 0
- Made-up cases: role correct 92 of 99
- Kind correct: 134 of 135
- Different answers on lines that cannot move a figure, passed (12.14.5): 3
- Harmful direction (an eaten line tagged medium or removed, moving a figure), after code's checks: 2
- Harmful direction in the model's own answer, before code's checks: 5
- Failed calls: 3
- Cost: $0.008562, 34 calls

Role misses:

| dish | recipe | real page | line | expected | got | model said | harmful | rule |
|---|---|---|---|---|---|---|---|---|
| PORK SCHNITZEL | Pan-Fried Pork Cutlets | no | 3 tablespoons vegetable oil | eaten | cooking_medium | cooking_medium | yes | 12.9.2 pan-frying oil |
| MARINATED OLIVES | Marinated Olives | no | 1 cup olive oil | cooking_medium | eaten | eaten | no | 12.9.3 olive oil of a marinade |
| POACHED SALMON | Poached Salmon | no | 1 cup dry white wine | cooking_medium | eaten | eaten | no | 12.9.2 poaching liquid |
| POACHED SALMON | Poached Salmon | no | 4 cups fish stock | cooking_medium | eaten | eaten | no | 12.9.2 poaching liquid; 12.10.3 stock and sausage are prepared_product |
| POACHED SALMON | Poached Salmon | no | 2 cups whole milk | cooking_medium | eaten | eaten | no | 12.10.3 decided 2026-11-06 |
| ROAST CHICKEN | Roast Chicken with Lemon and Garlic | no | 1 lemon, quartered | removed | eaten | eaten | no | 12.10.3 decided 2026-11-06 |
| SMOKED HADDOCK | Haddock in Parsley Sauce | no | 2 cups whole milk | eaten | cooking_medium | cooking_medium | yes | 12.10.2 a poaching liquid made into a sauce |
| Marinated olives | Marinated Olives Recipe | yes | 1 cup DeLallo extra virgin olive oil | cooking_medium | eaten | eaten | no | 12.12.1 oil a food is stored in or served out of (3F: tagged eaten at full recipe weight) |
| Marinated olives | Warm Marinated Olives | yes | 2/3 cup good olive oil | cooking_medium | eaten | eaten | no | 12.12.1 oil a food is stored in or served out of (3F: tagged eaten at full recipe weight) |

Kind misses:

| dish | line | expected | got | rule |
|---|---|---|---|---|
| MUSHROOM RISOTTO | 6 cups vegetable stock | prepared_product | plain_food | absorbed by the rice; 12.10.3 stock and sausage are prepared_product |

