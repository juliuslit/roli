# Line-tag test set_2026-11-06_no_method

Model google/gemini-3.8-flash; prompt version 2e3a82ed51c6; set `roli_agent/tests/fixtures/line_tag_test_set.json`.

## Run 1

- Role correct: 81 of 81
- Kind correct: 76 of 81
- Harmful direction (an eaten line tagged medium or removed), after code's checks: 0
- Harmful direction in the model's own answer, before code's checks: 0
- Failed calls: 0
- Cost: $0.025362, 28 calls

Kind misses:

| dish | line | expected | got | rule |
|---|---|---|---|---|
| FISH AND CHIPS | 1 cup dark lager beer | plain_food | prepared_product | batter liquid stays in the batter (tagged medium in 3D) |
| POACHED SALMON | 4 cups fish stock | plain_food | prepared_product | 12.9.2 poaching liquid |
| LENTIL SOUP | 4 cups chicken stock | plain_food | prepared_product | 12.9.2 liquid of a soup |
| MUSHROOM RISOTTO | 6 cups vegetable stock | plain_food | prepared_product | absorbed by the rice |
| SCOTCH EGG | 1 sausage | plain_food | prepared_product | main ingredient |

## Unclear lines for Julius (not scored)

| dish | line | model's tag | question |
|---|---|---|---|
| MARINATED OLIVES | Strips of rind from 1 lemon (preferably organic) | removed / plain_food | Steeped in the marinade: lifted out, or served in the bowl? The 3D tag 'removed' made the Sicilian olives estimable. |
| MARINATED OLIVES | 3 large cloves garlic, smashed | eaten / plain_food | Steeped in the marinade: lifted out, eaten or medium? |
| GRILLED CHICKEN | 2 tablespoons soy sauce | eaten / prepared_product | A sauce in a marinade that is discarded: medium (validator refuses soy sauce today) or eaten? |
| POACHED SALMON | 2 cups whole milk | cooking_medium / plain_food | Poaching milk that often becomes the sauce: medium or eaten? |
| SPAGHETTI WITH CLAMS | 2 tsp kosher salt (or more for cooking the pasta) | eaten / plain_food | Salt that may go into the pasta water: medium or eaten? Near zero either way. |
| MARGHERITA | Semolina, for the peel | eaten / plain_food | Dusting the peel: mostly left behind. Eaten, removed or medium? The validator allows neither medium nor removed today. |
| SCHNITZEL | 1 cup vegetable oil | cooking_medium / plain_food | Shallow fry in half an inch of oil: a deep-fry bath (medium) or pan-frying (eaten)? 12.9.2 names both ends, not this middle. |
| ROAST CHICKEN | 1 lemon, quartered | eaten / plain_food | Stuffed in the cavity: removed (validator refuses it in 3D) or eaten? |
| ROAST CHICKEN | 2 whole, unpeeled heads garlic, split in half horizontally | eaten / plain_food | Roasted beside the bird: eaten or removed? |
| SHEET PAN VEGETABLES | Cooking spray | eaten / plain_food | Greasing a tray: like a grill grate (medium), or eaten? |
| TUNA CRUDO | olive oil (to cover the carrots) | cooking_medium / plain_food | A slow oil bath for a garnish: confit (medium) or eaten? |
| COUSCOUS | 3 cup boiling water (see notes) | eaten / plain_food | Absorbed by the grain, seen in 3D as medium. Spec 12.9.3 says water in a soup is eaten; is absorbed water the same? |
