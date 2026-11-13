# Repeatability: pass A against pass B

The same four photos, the same 3F code, pass B straight after pass A. Pass A read each photo fresh and saved the reading; pass B reused it (reuse_saved_reading on), with grades and tags saved by pass A.

| menu | menu read | recommendation text | ranking and figures | differences | model calls A / B | model $ A / B | USDA requests A / B |
|---|---|---|---|---|---|---|---|
| Flour + Water | same | same | same | 0 | 30 / 14 | 0.1016 / 0.0106 | 29 / 3 |
| The Greyhound (gastropub) | same | same | same | 0 | 46 / 16 | 0.1478 / 0.0094 | 61 / 1 |
| Zuni Cafe | same | same | same | 0 | 59 / 10 | 0.1792 / 0.0071 | 81 / 0 |
| Seafood chalkboard | same | same | same | 1 | 18 / 8 | 0.0521 / 0.0050 | 14 / 4 |

## Flour + Water (20261106-144638-f35cef vs 20261106-151323-8a5886)

No differences.

## The Greyhound (gastropub) (20261106-144833-44b2d8 vs 20261106-151344-411755)

No differences.

## Zuni Cafe (20261106-145153-12037e vs 20261106-151451-5dddcc)

No differences.

## Seafood chalkboard (20261106-150714-cfc7cb vs 20261106-153358-1bafce)

- ocean trout tuna poke salad: same figures; different pages read: ['https://danapointfishcompany.com/poke-hawaiian-fish-salad']

## Reader check: menu_23_en_boardwalk_bistro_chalkboard.jpg, read twice, fresh

9 and 10 items; 6 differences; $0.009559, 2 calls.

- item count: 9 vs 10
- item 6 (OCEAN TROUT), description: 'WATERMELON, FETTA, MINT ALMOND, SALSA VERDE' vs ''
- item 7 (NORTH QLD BARAMUNDI), description: 'WATERMELON, FETTA, MINT ALMOND, SALSA VERDE' vs ''
- item 8 (COBIA), description: 'WATERMELON, FETTA, MINT ALMOND, SALSA VERDE' vs ''
- item 9 (SNAPPER), description: 'WATERMELON, FETTA, MINT ALMOND, SALSA VERDE' vs ''
- only in the second reading: 'WATERMELON, FETTA, MINT ALMOND, SALSA VERDE'

## Causes, traced by hand

**Pass A against pass B:** all four recommendations, rankings, figures and flags matched. The one difference moved no figure: danapointfishcompany.com's poke page returned an HTTP error in pass A and loaded in pass B. Pages that fail are not saved, so it was tried again. It was graded high and not processed, because enough recipes came before it. A page that fails in one pass and loads in the next could change a figure if it were needed, so saved readings, grades and tags do not rule out every difference.

**Reader check:** the two fresh readings differ in how they treat the chalkboard's shared line. The first attaches "WATERMELON, FETTA, MINT ALMOND, SALSA VERDE" to four fish as their description. The second leaves those four with no description and lists the line as a tenth item, a dish of its own. The saved reading hides this in test reruns only. A tester's run reads the photo fresh, so this variation still reaches testers.
