# Line-tag test set_2026-11-06_3h

Model google/gemini-3.8-flash; prompt version d93a4db04c35; set `roli_agent/tests/fixtures/line_tag_test_set.json`.

## Run 1

- Role correct: 112 of 112
- Real pages (12.12.9): role correct 8 of 8, harmful 0
- Made-up cases: role correct 104 of 104
- Kind correct: 110 of 111
- Different answers on lines that cannot move a figure, passed (12.14.5): 3
- Harmful direction (an eaten line tagged medium or removed, moving a figure), after code's checks: 0
- Harmful direction in the model's own answer, before code's checks: 1
- Failed calls: 1
- Cost: $0.040051, 34 calls

Kind misses:

| dish | line | expected | got | rule |
|---|---|---|---|---|
| FISH AND CHIPS | 1 cup dark lager beer | plain_food | prepared_product | batter liquid stays in the batter (tagged medium in 3D) |

## Run 2

- Role correct: 149 of 149
- Real pages (12.12.9): role correct 45 of 45, harmful 0
- Made-up cases: role correct 104 of 104
- Kind correct: 146 of 148
- Different answers on lines that cannot move a figure, passed (12.14.5): 5
- Harmful direction (an eaten line tagged medium or removed, moving a figure), after code's checks: 0
- Harmful direction in the model's own answer, before code's checks: 2
- Failed calls: 0
- Cost: $0.039383, 34 calls

Kind misses:

| dish | line | expected | got | rule |
|---|---|---|---|---|
| FISH AND CHIPS | 1 cup dark lager beer | plain_food | prepared_product | batter liquid stays in the batter (tagged medium in 3D) |
| BEET CARPACCIO | 1 tbsp balsamic vinegar | plain_food | prepared_product | 12.10.2 a marinade served on the plate |

