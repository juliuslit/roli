# Expected comparisons for the five Flour + Water dishes (per restaurant portion), v1

Drafted on 2026-11-03 from first principles (USDA per-100 g values of the dominant ingredients and the proposed portion rules), **awaiting
Julius's review**. These are the "human-reviewed expectations" the prototype is measured against; if Julius changes a row, the evaluation is re-run
by `scripts/evaluate_2d.py`. Numbers are ranges per restaurant plate, not verified values.

| Dish | Sat fat g | Chol mg | Expected order (sat fat, 1 = lowest) | Why |
|---|---|---|---|---|
| heirloom tomatoes | 0.3-3 | 0 | 1 | plant plate; only the oil dressing carries saturated fat |
| bluefin crudo | 0.2-2.5 | 20-120 | 2 | lean raw fish plus a drizzle; bottarga swings cholesterol |
| little gem lettuces | 2-7 | 3-15 | 3 | tahini and pecorino carry it |
| king salmon | 4-10 | 55-160 | 4 | the fish itself plus butter |
| margherita | 10-25 | 40-140 | 5 | fior di latte; shared halves it |

Expected pairwise picture for saturated fat: tomatoes and crudo clearly below salmon and pizza; tomatoes vs crudo overlapping; gem salad overlapping
with crudo and salmon; pizza above everything except that a shared pizza overlaps a salmon main. Cholesterol: tomatoes lowest and clearly so; gem
salad clearly below crudo, salmon and pizza; crudo, salmon and pizza overlap because bottarga, fish size and cheese amount all swing.
