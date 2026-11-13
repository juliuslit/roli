# Repeatability: pass A against pass B

The same four photos, the same code, pass B straight after pass A. Both on the final 3E code, with grades and tags saved by pass A.

| menu | menu read | recommendation text | ranking and figures | differences | model calls A / B | model $ A / B | USDA requests A / B |
|---|---|---|---|---|---|---|---|
| Flour + Water | same | same | same | 0 | 43 / 17 | 0.1208 / 0.0197 | 3 / 3 |
| The Greyhound (gastropub) | different | same | same | 11 | 41 / 18 | 0.1299 / 0.0473 | 8 / 10 |
| Zuni Cafe | different | same | same | 5 | 37 / 18 | 0.1388 / 0.0438 | 0 / 4 |
| Seafood chalkboard | different | same | different | 5 | 23 / 13 | 0.0673 / 0.0288 | 23 / 1 |

## Flour + Water (20261106-134104-7e4cd4 vs 20261106-135206-1daace)

No differences.

## The Greyhound (gastropub) (20261106-134352-2c7e93 vs 20261106-135240-35e7db)

- menu read differently: 9 item(s) only in A, 9 only in B; e.g. A [('DESSERTS', 'APPLE & CRUMBLE RHUBARB', 'Vanilla Custard & Ice Cream')], B [('DESSERTS 8', 'APPLE & CRUMBLE RHUBARB', 'Vanilla Custard & Ice Cream')]
- apple crumble rhubarb: same figures; the menu reader wrote the item differently (section: 'DESSERTS' vs 'DESSERTS 8')
- baked vanila cheesecake: same figures; the menu reader wrote the item differently (section: 'DESSERTS' vs 'DESSERTS 8')
- biscoff doughnuts: same figures; the menu reader wrote the item differently (section: 'DESSERTS' vs 'DESSERTS 8')
- chicken schnitzel: same figures; tag differed on ('https://bbcgoodfood.com/premium/crispy-chicken-schnitzel-with-miso-mushroom-sauce', 'ing_01'): None vs ('eaten', 'plain_food')
- chocolate brownie: same figures; the menu reader wrote the item differently (section: 'DESSERTS' vs 'DESSERTS 8')
- sirloin steak: only in B (evaluated): the menu reader wrote it differently
- sirloin steak 10oz: only in A (evaluated): the menu reader wrote it differently
- sticky toffee pudding: same figures; the menu reader wrote the item differently (section: 'DESSERTS' vs 'DESSERTS 8')
- the greyhound cheese slate: same figures; the menu reader wrote the item differently (section: 'DESSERTS' vs 'DESSERTS 8')
- trio of doughnuts to share: same figures; the menu reader wrote the item differently (section: 'DESSERTS' vs 'DESSERTS 8')

## Zuni Cafe (20261106-134644-b10521 vs 20261106-135421-5a4885)

- menu read differently: 4 item(s) only in A, 4 only in B; e.g. A [('', 'Chicken for two roasted in the wood-fired brick oven; warm bread salad with scallions, garlic, bitter greens, dried currants, and pine nuts', '(approximately 75 minutes)\n$1 from each chicken sold is donated to UR Blessings, a mutual aid organization working to end food injustice.')], B [('', 'Chicken for two roasted in the wood-fired brick oven; warm bread salad with scallions, garlic, bitter greens, dried currants, and pine nuts', '(approximately 75 minutes) $1 from each chicken sold is donated to UR Blessings, a mutual aid organization working to end food injustice.')]
- chicken for two roasted in the wood fired brick ov: same figures; the menu reader wrote the item differently (description: 'anization working to end food injustice.' vs 'anization working to end food injustice.')
- fuyu persimmon and roasted beet carpaccio with lay: same figures; the menu reader wrote the item differently (name: 'herbs, and Meyer lemon-pistachio aïllade' vs 'herbs, and Meyer lemon-pistachio aillade')
- yellowfin tuna grilled rare all acqua di mare with: ('evaluated', None, None) vs ('evaluated', '2.997865', None): the menu reader wrote the item differently (name: 'slow-cooked Early Girl tomato, and aïoli' vs 'low-cooked Early Girl tomato, and aïoli*')
- zuni caesar salad: same figures; the menu reader wrote the item differently (name: 'Zuni Caesar salad' vs 'Zuni Caesar salad*')

## Seafood chalkboard (20261106-134928-48ec86 vs 20261106-135554-71cdb5)

- menu read differently: 4 item(s) only in A, 4 only in B; e.g. A [('FISH OF THE DAY', 'COBIA', 'WATERMELON, FETTA, MINT ALMOND, SALSA VERDE SALAD')], B [('FISH OF THE DAY.', 'COBIA', 'WATERMELON, FETTA, MINT ALMOND, SALSA VERDE')]
- cobia: same figures; the menu reader wrote the item differently (description: 'N, FETTA, MINT ALMOND, SALSA VERDE SALAD' vs 'ERMELON, FETTA, MINT ALMOND, SALSA VERDE'; section: 'FISH OF THE DAY' vs 'FISH OF THE DAY.')
- north qld baramundi: same figures; the menu reader wrote the item differently (description: 'N, FETTA, MINT ALMOND, SALSA VERDE SALAD' vs 'ERMELON, FETTA, MINT ALMOND, SALSA VERDE'; section: 'FISH OF THE DAY' vs 'FISH OF THE DAY.')
- ocean trout: ('evaluated', '8.808116', '18.100340') vs ('evaluated', '6.825322', '26.08564936708860759493670886'): the menu reader wrote the item differently (description: 'N, FETTA, MINT ALMOND, SALSA VERDE SALAD' vs 'ERMELON, FETTA, MINT ALMOND, SALSA VERDE'; section: 'FISH OF THE DAY' vs 'FISH OF THE DAY.')
- snapper: ('evaluated', '4.729336', '15.362953') vs ('evaluated', '4.641040', '24.245989'): the menu reader wrote the item differently (description: 'N, FETTA, MINT ALMOND, SALSA VERDE SALAD' vs 'ERMELON, FETTA, MINT ALMOND, SALSA VERDE'; section: 'FISH OF THE DAY' vs 'FISH OF THE DAY.')

## Causes, traced by hand from the two run.json files

Pass B did not match pass A exactly. All four recommendations, all four ranking orders and the open flags matched. Four dishes of the 45 evaluated had different figures, and every one traces back to the menu reader, which is not saved. No difference traces to a saved grade or a saved tag.

| dish | pass A | pass B | what the reader changed | how that reached the figure |
|---|---|---|---|---|
| Ocean Trout (seafood, ranked 5th both times) | 8.8-18.1 g | 6.8-26.1 g | section "FISH OF THE DAY" became "FISH OF THE DAY."; description lost "SALAD" | the full stop is copied into the search query, so a different saved search came back: 4 of 7 pages shared. The lost word changed the item key, so saved grades and tags did not apply: 0 from saved tags |
| Snapper (seafood, ranked 4th both times) | 4.7-15.4 g | 4.6-24.2 g | same | same: 4 pages shared of 7 and 6 |
| Sirloin Steak (Greyhound, unranked both times) | low 7.8 g | low 9.5 g | name "SIRLOIN STEAK 10oz" became "SIRLOIN STEAK" | new query and new item key: 0 from saved tags |
| Yellowfin tuna (Zuni, unranked both times) | no figure | low 3.0 g | name gained a footnote asterisk, "aïoli*" | the asterisk is copied into the search query: different pages, 1 of 3 recipes from saved tags |

Differences that changed no figure: the Greyhound section "DESSERTS" against "DESSERTS 8" and "ADD EMMENTAL CHEESE" against "EMMENTAL CHEESE"; Zuni "Zuni Caesar salad" against "Zuni Caesar salad*", "aïllade" against "aillade", and a line break in the chicken description; Cobia and Barramundi on the seafood board, with the same description and section change as above.

One difference does not come from the reader. Chicken Schnitzel's tag call returned an invalid answer in pass A, so that dish ran on the older text patterns; a failed answer is not saved, so pass B asked again and got valid tags. Its figures were the same. That was the only failed tag call in the eight runs.

Model calls left in pass B: the reader, fresh grades and tags for dishes whose key changed, and calls from the only other model call sites in the dish pipeline, USDA matching and page extraction. Flour + Water still made 16 dish-level calls with every tag saved, and its result was identical. Those calls were not split further.

After pass B, `compare_mvp_runs.py`, `repeatability.py`, `assumed_weights.md` and `tests/test_3e.py` changed. None of them is loaded by a menu run.
