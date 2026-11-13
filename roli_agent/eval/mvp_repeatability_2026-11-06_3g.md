# Repeatability: pass A against pass B

These are the second 3G pair, on the final code. The first pair (runs 20261106-180121-79c840 to 20261106-181046-e2d74b) also showed 0 differences; it was replaced because its lender list showed four bad lenders, and a reader check after it found the two readings identical. Pass B reuses the saved reading, so it cannot show reader variation; the reader check below does.

Pass A: final code, reader v5, fresh reading, saved. Pass B straight after, with reuse_saved_reading on: the same saved reading, and a page that failed in pass A stays failed (12.12.7).

| menu | menu read | recommendation text | ranking and figures | differences | model calls A / B | model $ A / B | USDA requests A / B |
|---|---|---|---|---|---|---|---|
| Flour + Water | same | same | same | 0 | 17 / 16 | 0.0196 / 0.0117 | 3 / 3 |
| The Greyhound | same | same | same | 0 | 11 / 10 | 0.0220 / 0.0056 | 0 / 2 |
| Zuni Cafe | same | same | same | 0 | 13 / 10 | 0.0406 / 0.0079 | 1 / 0 |
| Seafood chalkboard | same | same | same | 0 | 3 / 2 | 0.0057 / 0.0013 | 0 / 0 |

## Flour + Water (20261106-181416-9ff31a vs 20261106-181733-0d09d3)

No differences.

## The Greyhound (20261106-181452-d3868e vs 20261106-181747-8ac031)

No differences.

## Zuni Cafe (20261106-181554-0fb09d vs 20261106-181845-95544a)

No differences.

## Seafood chalkboard (20261106-181718-06b914 vs 20261106-181942-533201)

No differences.

## Reader check: menu_23_en_boardwalk_bistro_chalkboard.jpg, read twice, fresh

9 and 9 items; 8 differences; $0.009578, 2 calls.

- item 6 (OCEAN TROUT), description: 'WATERMELON, FETTA, MINT ALMOND, SALSA VERDE' vs 'WATERMELON, FETTA, MINT ALMOND, SALSA VERDE SALAD'
- item 6 (OCEAN TROUT), section: 'FISH OF THE DAY.' vs 'FISH OF THE DAY'
- item 7 (NORTH QLD BARAMUNDI), description: 'WATERMELON, FETTA, MINT ALMOND, SALSA VERDE' vs 'WATERMELON, FETTA, MINT ALMOND, SALSA VERDE SALAD'
- item 7 (NORTH QLD BARAMUNDI), section: 'FISH OF THE DAY.' vs 'FISH OF THE DAY'
- item 8 (COBIA), description: 'WATERMELON, FETTA, MINT ALMOND, SALSA VERDE' vs 'WATERMELON, FETTA, MINT ALMOND, SALSA VERDE SALAD'
- item 8 (COBIA), section: 'FISH OF THE DAY.' vs 'FISH OF THE DAY'
- item 9 (SNAPPER), description: 'WATERMELON, FETTA, MINT ALMOND, SALSA VERDE' vs 'WATERMELON, FETTA, MINT ALMOND, SALSA VERDE SALAD'
- item 9 (SNAPPER), section: 'FISH OF THE DAY.' vs 'FISH OF THE DAY'
