# Repeatability: pass A against pass B

Round 2 of the 3J reruns (2026-11-08, after the dish-kind wiring fix): the same photos, the same code and the approved table; pass A 09:01-09:35 local with fresh readings, pass B 09:35-09:39 with reuse_saved_reading on.

| menu | menu read | recommendation text | ranking and figures | differences | model calls A / B | model $ A / B | USDA requests A / B |
|---|---|---|---|---|---|---|---|
| 03 Flour + Water | same | same | same | 0 | 21 / 20 | 0.0255 / 0.0134 | 2 / 2 |
| 08 The Greyhound | same | different | different | 1 | 52 / 30 | 0.1211 / 0.0218 | 19 / 7 |
| 01 Zuni Cafe | same | different | different | 1 | 14 / 10 | 0.0426 / 0.0063 | 7 / 2 |
| 23 Seafood chalkboard | same | same | same | 0 | 7 / 6 | 0.0085 / 0.0032 | 0 / 0 |

## 03 Flour + Water (20261108-140127-abbf34 vs 20261108-143531-910df2)

No differences.

## 08 The Greyhound (20261108-140247-e7468c vs 20261108-143636-d86a24)

- the greyhound cheese slate: ('evaluated', '7.914038', None) vs ('evaluated', '6.659633', '14.059225'): USDA match differed on ('https://lifemadesweeter.com/cheese-board', 'ing_07'): None vs 746952

A: Among the 16 dishes I could estimate (30 tried; 14 had no usable estimate; 2 not tried), lowest saturated fat first: 1) Padron Peppers, about 0.2-3.1 g saturated fat per plate; 2) Cornish Fish & Chips; 3) Pan Fried Seabass, 4.1-26 g. Cornish Fish & Chips: about 4.7-8.0 g saturated fat if fried in vegetable oil, up to about 23 g in beef dripping. Ask what they fry in. Modeled from published recipes and typical portions, not this kitchen's numbers.

B: Among the 17 dishes I could estimate (30 tried; 13 had no usable estimate; 2 not tried), lowest saturated fat first: 1) Padron Peppers, about 0.2-3.1 g saturated fat per plate; 2) Cornish Fish & Chips; 3) Pan Fried Seabass, 4.1-26 g. Cornish Fish & Chips: about 4.7-8.0 g saturated fat if fried in vegetable oil, up to about 23 g in beef dripping. Ask what they fry in. Modeled from published recipes and typical portions, not this kitchen's numbers.

## 01 Zuni Cafe (20261108-140617-8a7d6a vs 20261108-143838-db4c83)

- zuni caesar salad: ('evaluated', '2.176233', '7.970537') vs ('evaluated', '1.952675', '7.970537'): USDA match differed on ('https://sfgate.com/cooking/article/zuni-recipe-correction-5063087.php', 'ing_07'): None vs 172751

A: Among the 8 dishes I could estimate (15 tried; 7 had no usable estimate), lowest saturated fat first: 1) Zuni Caesar salad, about 2.2-8.0 g saturated fat per plate; 2) Yellowfin tuna grilled rare all'acqua di, 3.3-12 g; 3) Spaghetti with Gulf shrimp, 0.8-15 g. These ranges overlap, so treat the order as a toss-up. Spaghetti with Gulf shrimp may carry up to 414 mg cholesterol. Modeled from published recipes and typical portions, not this kitchen's numbers.

B: Among the 8 dishes I could estimate (15 tried; 7 had no usable estimate), lowest saturated fat first: 1) Zuni Caesar salad, about 2.0-8.0 g saturated fat per plate; 2) Yellowfin tuna grilled rare all'acqua di, 3.3-12 g; 3) Spaghetti with Gulf shrimp, 0.8-15 g. These ranges overlap, so treat the order as a toss-up. Spaghetti with Gulf shrimp may carry up to 414 mg cholesterol. Modeled from published recipes and typical portions, not this kitchen's numbers.

## 23 Seafood chalkboard (20261108-140737-78c112 vs 20261108-143846-69fabe)

No differences.
