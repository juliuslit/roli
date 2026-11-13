# Line-tag test set_2026-11-06_3g

Model google/gemini-3.8-flash; prompt version 36aae65c6b66; set `roli_agent/tests/fixtures/line_tag_test_set.json`.

## Run 1

- Role correct: 145 of 149
- Real pages (12.12.9): role correct 41 of 45, harmful 2
- Made-up cases: role correct 104 of 104
- Kind correct: 146 of 148
- Harmful direction (an eaten line tagged medium or removed), after code's checks: 2
- Harmful direction in the model's own answer, before code's checks: 4
- Failed calls: 0
- Cost: $0.037922, 34 calls

Role misses:

| dish | recipe | real page | line | expected | got | model said | harmful | rule |
|---|---|---|---|---|---|---|---|---|
| SICILIAN OLIVES | Marinated Olives | yes | 4 (2 inch) thin strips lemon peel | removed | eaten | eaten | no | strips of peel or rind stay in the jar and are not eaten (3F: tagged eaten) |
| Marinated olives | Marinated Olives Recipe | yes | 6-8 black peppercorns | eaten | removed | removed | yes | stays with the food |
| Marinated olives | Marinated Olives Recipe | yes | 1 tsp black peppercorns, whole ($0.08) | eaten | removed | removed | yes | stays with the food |
| Marinated olives | Warm Marinated Olives | yes | 2/3 cup good olive oil | cooking_medium | eaten | eaten | no | 12.12.1 oil a food is stored in or served out of (3F: tagged eaten at full recipe weight) |

Kind misses:

| dish | line | expected | got | rule |
|---|---|---|---|---|
| FISH AND CHIPS | 1 cup dark lager beer | plain_food | prepared_product | batter liquid stays in the batter (tagged medium in 3D) |
| BEET CARPACCIO | 1 tbsp balsamic vinegar | plain_food | prepared_product | 12.10.2 a marinade served on the plate |

## Run 2

- Role correct: 143 of 149
- Real pages (12.12.9): role correct 39 of 45, harmful 2
- Made-up cases: role correct 104 of 104
- Kind correct: 145 of 148
- Harmful direction (an eaten line tagged medium or removed), after code's checks: 2
- Harmful direction in the model's own answer, before code's checks: 4
- Failed calls: 0
- Cost: $0.036805, 34 calls

Role misses:

| dish | recipe | real page | line | expected | got | model said | harmful | rule |
|---|---|---|---|---|---|---|---|---|
| SICILIAN OLIVES | Marinated Olives | yes | 2 medium sprigs fresh rosemary | removed | eaten | eaten | no | whole herb sprigs stay in the jar and are not eaten (3F: tagged eaten) |
| SICILIAN OLIVES | Marinated Olives | yes | 4 medium sprigs fresh thyme | removed | eaten | eaten | no | whole herb sprigs stay in the jar and are not eaten (3F: tagged eaten) |
| SICILIAN OLIVES | Marinated Olives | yes | 4 (2 inch) thin strips lemon peel | removed | eaten | eaten | no | strips of peel or rind stay in the jar and are not eaten (3F: tagged eaten) |
| Marinated olives | Marinated Olives Recipe | yes | 6-8 black peppercorns | eaten | removed | removed | yes | stays with the food |
| Marinated olives | Marinated Olives Recipe | yes | 1 tsp black peppercorns, whole ($0.08) | eaten | removed | removed | yes | stays with the food |
| Marinated olives | Warm Marinated Olives | yes | 2/3 cup good olive oil | cooking_medium | eaten | eaten | no | 12.12.1 oil a food is stored in or served out of (3F: tagged eaten at full recipe weight) |

Kind misses:

| dish | line | expected | got | rule |
|---|---|---|---|---|
| FISH AND CHIPS | 1 cup dark lager beer | plain_food | prepared_product | batter liquid stays in the batter (tagged medium in 3D) |
| Marinated olives | 1 ½ cups Mediterranean olive mix*, drained ($2.40) | plain_food | prepared_product | main ingredient |
| Marinated olives | 2 tablespoons red wine vinegar | plain_food | prepared_product | 12.10.2 a marinade left in the jar: every liquid of it is a medium |

