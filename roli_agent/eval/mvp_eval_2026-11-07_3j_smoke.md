# MVP evaluation (2026-11-07)

| photo | run | status | s | menu items | candidates | selected | evaluated | ranked | unranked | no recipes | errors | skipped | budget-stopped | credits | model calls | model $ (actual+est.) | USDA req | words |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| menu_03_own_IMG_5185.jpg | 1 | done | 188.3 | 19 | 18 | 18 | 14 | 7 | 8 | 3 | 0 | 0 | 0 | 0 | 50 | 0.1207 (0.1207+0.0000) | 91 | 68 |

## menu_03_own_IMG_5185.jpg run 1

> Among the 7 dishes I could estimate (18 tried; 11 had no usable estimate), lowest saturated fat first: 1) Heirloom Tomatoes, about 1.8-2.1 g saturated fat per plate; 2) Bluefin Crudo, 0.8-11 g; 3) Little Gem Lettuces, 4.3-14 g. These ranges overlap, so treat the order as a toss-up. Heirloom Tomatoes has no cholesterol in its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

| # | dish | sat fat g | support |
|---|---|---|---|
| 1 | HEIRLOOM TOMATOES | 1.806–2.070 | close_call |
| 2 | BLUEFIN CRUDO | 0.828–11.30 | close_call |
| 3 | LITTLE GEM LETTUCES | 4.348–14.07 | close_call |
| 4 | KING SALMON | 6.348–20.07 | close_call |
| 5 | CORN CAPPELLETTI | 3.547–23.25 | close_call |
| 6 | KOSHIHIKARI ARANCINI | 1.059–30.39 | close_call |
| 7 | PORK CHOP | 7.864–27.92 | well_supported |

Unranked: POLE BEANS (the estimate has no upper bound: 2 of 2 recipes have no upper bound (notquitenigella.com: miso bagna cauda (missing_gram); PUTTANESCA (the estimate has no upper bound: 4 of 4 recipes have no upper bound (cilantroparsley.com: store bought pizza dough (miss); MARGHERITA (the estimate has no upper bound: 3 of 4 recipes have no upper bound (life-in-the-lofthouse.com: for my best pizza dough ); ORECCHIETTE (the estimate has no upper bound: 3 of 3 recipes have no upper bound (aboutamom.com: chanterelle (missing_grams), wasabi ); DUCK TRIANGOLI (no recipe of this dish could be portioned (no scenario could be portioned (1 without an applicable portion model))); TALEGGIO SCARPINOCC (the estimate has no upper bound: 1 of 1 recipes have no upper bound (qbcucina.com: aceto balsamico (missing_grams))); PAPPARDELLE (no recipe of this dish could be portioned (no scenario could be portioned (4 without an applicable portion model))); SALSICCIA BIANCA (our estimate disagrees with published figures for this kind of dish)

USDA: 91 requests; remaining 3598 -> 3509 of 3600; halted False; flagged 1; USDA-unavailable dishes 0

Flags: closed HEIRLOOM TOMATOES (every check that may flag now passes: per_plate 1.938 vs 4.0-18.0); open SALSICCIA BIANCA (per_plate; Roli 42.826 vs 2.5-21.2; top ['caciocavallo', 'butter', 'cooked italian sausage'])
