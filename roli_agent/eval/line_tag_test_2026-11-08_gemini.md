# Line-tag test set_2026-11-08_gemini

Model google/gemini-3.8-flash; prompt version 4e6b3af61ba0; set `roli_agent/tests/fixtures/line_tag_test_set.json`.

## Run 1

- Role correct: 148 of 149
- Real pages (12.12.9): role correct 44 of 45, harmful 0
- Made-up cases: role correct 104 of 104
- Kind correct: 145 of 148
- Different answers on lines that cannot move a figure, passed (12.14.5): 5
- Harmful direction (an eaten line tagged medium or removed, moving a figure), after code's checks: 0
- Harmful direction in the model's own answer, before code's checks: 2
- Failed calls: 0
- Cost: $0.048950, 34 calls

Role misses:

| dish | recipe | real page | line | expected | got | model said | harmful | rule |
|---|---|---|---|---|---|---|---|---|
| Marinated olives | Warm Marinated Olives | yes | 2/3 cup good olive oil | cooking_medium | eaten | eaten | no | 12.12.1 oil a food is stored in or served out of (3F: tagged eaten at full recipe weight) |

Kind misses:

| dish | line | expected | got | rule |
|---|---|---|---|---|
| GARDEN SALAD | 1 tablespoon red wine vinegar | plain_food | prepared_product | dressing |
| Marinated olives | 1 ½ cups Mediterranean olive mix*, drained ($2.40) | plain_food | prepared_product | main ingredient |
| Marinated olives | 2 tablespoons red wine vinegar | plain_food | prepared_product | 12.10.2 a marinade left in the jar: every liquid of it is a medium |

