# Line-tag test set_2026-11-06_3f_first

Model google/gemini-3.8-flash; prompt version 48024cfadff9; set `roli_agent/tests/fixtures/line_tag_test_set.json`.

## Run 1

- Role correct: 104 of 104
- Kind correct: 103 of 103
- Harmful direction (an eaten line tagged medium or removed), after code's checks: 0
- Harmful direction in the model's own answer, before code's checks: 1
- Failed calls: 0
- Cost: $0.030165, 32 calls

## Run 2

- Role correct: 104 of 104
- Kind correct: 101 of 103
- Harmful direction (an eaten line tagged medium or removed), after code's checks: 0
- Harmful direction in the model's own answer, before code's checks: 2
- Failed calls: 0
- Cost: $0.030570, 32 calls

Kind misses:

| dish | line | expected | got | rule |
|---|---|---|---|---|
| LENTIL SOUP | 1 Parmesan rind | plain_food | prepared_product | 12.3 rind lifted out |
| BEET CARPACCIO | 1 tbsp balsamic vinegar | plain_food | prepared_product | 12.10.2 a marinade served on the plate |

