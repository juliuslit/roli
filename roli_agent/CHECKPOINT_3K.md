# Checkpoint 3K: narrower, honest ranges

Date: 2026-11-08. Spec: `SPEC_3_mvp.md` 12.20 (your decisions of 2026-11-08), build readings in 12.21.

**Stopped here for your review.** No new USDA release data is approved; Telegram and deployment are not started.

## 1. Result in brief

PENDING_BRIEF

## 2. What changed and where

| fix (12.20) | change | where |
|---|---|---|
| A, distribution | `SamplingInputs` on every scenario interval (R, P, f, W, M, K, dough at both bounds, read from the saved calculation); `sampling.sample_band` draws 2,000 plates per dish and nutrient (recipe x position x plate weight) and writes the band on `DishInterval` beside the extremes; seeded from the dish, nutrient and scenario ids | `recipes/models.py`, `recipes/compare_dishes.py`, `recipes/sampling.py`, `recipes/survey.py` |
| A, plate samples | `build_cards.write_plate_weights` writes `recipes/plate_weights.csv` (4,125 rows: chain items, stated protein weights, AVPN balls, FNDDS portions, in each row's unit); `PlateWeights` loads and truncates them to the approved range; under 10 samples a row draws uniformly | `scripts/build_cards.py`, `recipes/plate_weights.py`, `recipes/plate_weights.csv` |
| B, weights and outliers | draw weight = grade x coverage; an outlier recipe (5x from the others' median, with 3+ recipes, never half of them) is set aside and named | `recipes/sampling.py` |
| C, plate model | `scripts/plate_model.py` fits and validates the ridge regression on MenuStat (pure Python), writes `recipes/plate_model.json` with `live` by your switch rule; `recipes/plate_model.py` draws from it at run time when live | `scripts/plate_model.py`, `recipes/plate_model.py`, `recipes/plate_model.json`, `eval/plate_model_2026-11-08.md` |
| D, top-up | `TopUp` in the pipeline: below 3 usable recipes, one "open" search from the menu's words, 6 new pages, graded, tagged, processed; `DishEstimate.topup`; `MenuBudget.topups` | `recipes/pipeline.py`, `recipes/ingest.py` (`topup_query`, `modes`, `skip_urls`), `recipes/tags.py` (`LineTags.merge`), `mvp/budget.py`, `mvp/menu_run.py` |
| E, assumed weights from recipes | `scripts/build_assumed_weights.py` writes `recipes/assumed_weights_data.csv` (265 ranges, 24 live); `WeightsTable.range_for` with the two guards; the assumption's basis and status say so | `scripts/build_assumed_weights.py`, `recipes/adapt.py`, `recipes/assumed_weights_data.csv`, `eval/assumed_weights_data_2026-11-08.md` |
| F, frying-fat prior | `recipes/frying_fat_prior.csv` (NEODA trade estimate, 4 % dripping); the survey draw follows it | `recipes/frying_fat_prior.csv`, `recipes/sampling.py` |
| G, line category | the tag call names a category from a list of twenty; code validates; zero-fat categories fall back to a fixed USDA record when the line matched nothing; a splash of wine is not a served-mass stop; prompt version bumped | `prompts.py`, `recipes/tags.py`, `recipes/match.py`, `recipes/pipeline.py`, `recipes/portions.py`, `recipes/models.py` |
| consumers | ranking by the band's median; "most plates" wording; the reference check compares the band's median; the web page shows band, extremes, plate source, set-aside, top-up | `mvp/ranking.py`, `mvp/reference.py`, `mvp/menu_run.py`, `mvp/web.py`, `mvp/models.py` |
| config | band_draws 2000, band quantiles 0.10/0.90, plate_samples_min 10, recipe_outlier_factor 5, grade_weight_medium 0.5, plate_weight_model None (follows the model file), frying_fat_prior True, min_usable_recipes 3, extra_fetch 6, max_topups_per_menu 8, assumed_weights_from_data True | `mvp/models.py` |
| scripts | `band_report.py` (band against extremes, offline); `repeatability.py` compares the band; `coverage.py` reports band width and top-ups per menu | `scripts/` |
| bug fixed | the card builder prepended the approval note on every rebuild, doubling it; now idempotent (a rebuild leaves the table byte-identical) | `scripts/build_cards.py` |
| verdicts on the bands (agreed 2026-11-08, before the reruns) | the support label and the toss-up sentence now read the bands: bands apart but extremes overlapping is "tentative", worded "Most plates fall in this order; the full ranges still overlap, so it is likely, not certain." Offline on the 3J runs: 3 of 89 close calls change; 9 of 11 menus still read toss-up because the lowest three dishes are close | `recipes/compare_dishes.py` (`_pairwise`), `mvp/ranking.py` |
| outlier guard tightened | one odd recipe is always an outlier; two or more that agree and make up a third of the recipes are a second kind of the dish and stay | `recipes/sampling.py` |
| dish kind reaches the portion step (bug found 2026-11-08 by the known-answer check) | the pipeline's portion and assumed-weights steps re-read the dish kind from the word lists, so the model's kind never decided the plate size ("Pollo Pesto" sized as a pot of dip); fixed and tested before the reruns; the 3J runs and today's preview carried the bug | `recipes/pipeline.py`, `recipes/portions.py`, `mvp/menu_run.py` |
| top-up count made atomic | three dish threads could each pass the "fewer than 8" check at once (the smoke run counted 9); the check and the count are now one step | `mvp/budget.py` (`reserve_topup`) |

Tests: agent 559 passed, 4 skipped (532 at 3J); library 337 unchanged (`test_report_3k.txt`).

## 3. The band against the extremes

PENDING_BAND

## 4. Coverage before and after

PENDING_COVERAGE

## 5. The plate-weight model: built, validated, off

`scripts/plate_model.py` fitted a ridge regression (pure Python; Roli's environment has no numpy) on 7,498 MenuStat items with a measured weight from 75 restaurants: the item's name words (689 in the vocabulary), its Roli family and the kids flag, to the log of its weight. Five folds grouped by restaurant, so no chain is on both sides. The model's error on held-out restaurants is a factor of 1.96 (MAE 0.67 in ln); on the UK chain sheets, which it never saw, a factor of 2.6.

Your switch rule: live when the model's 80 % interval covers held-out items at least as well as the family range and is narrower. On 3,514 held-out items of P2 families with a row:

| | 80 % coverage | median width |
|---|---|---|
| the model (intervals calibrated on cross-fitted held-out residuals) | 73 % | 5.1x |
| the family's approved range | 69 % | 4.2x |

Wider, so **not met: the model stays off**. Before the calibration the intervals were narrower (3.4x) but covered only 61 %, because a training fold's own residuals understate the error on new restaurants; the calibrated version is the honest one. The lesson in the numbers: an item's name words explain little of its weight once the family is known (sandwich 2.4x on the model's own interval but only 57 % covered), so the family range is about as good as a word model gets from this data. `recipes/plate_model.json` is written with `live: false` and the runner follows it; `eval/plate_model_2026-11-08.md` has the per-family table and the largest coefficients. The family samples (fix A) remain the plate source.

## 6. Assumed weights from recipe data

`scripts/build_assumed_weights.py` read the 2,463 stored recipe extractions: 2,040 distinct recipes, 1,738 with a serving count, 20,096 lines, 4,013 with a weight stated in the text, 167 skipped because a saved tag called them a cooking medium or removed, 719 filed under a weights row. The 265 (row, family) ranges are in `recipes/assumed_weights_data.csv`; `eval/assumed_weights_data_2026-11-08.md` shows each beside its hand row.

**24 ranges go live** under your rule (8 recipes of the family, 15 across families) and two guards I added after seeing the first build (12.21.4): a spread wider than 20x (p90 over p10) means the lines were not one role, and a median more than 4x outside the hand row's range means another food or another basis; either keeps the hand row. The guards stopped W14 salt (0.4 to 184 g per serving: lines like a salted can of tomatoes) and W05 hard cheese on vegetable starters (5.5 to 121 g). Live, with the hand row beside:

| row | hand row g | data range g (recipes) |
|---|---|---|
| W12 lemon juice, finishing | 5.9-15 | 1.2-11.1 (116 recipes, any dish); 2.5-11.3 on fish mains (18); 2.5-8.9 on leaf salads (17) |
| W50 lime or lemon wedge | 10-35 | 1.2-13.9 (53); 1.7-14.8 on fish mains (14) |
| W27 heavy cream, finishing | 15-30 | 9.4-70.1 (50); 9.9-100.9 on desserts (10) |
| W05 grated hard cheese | 5-15 | 4.8-25.0 (43); 6.9-21.6 on pasta (10) |
| W06 fresh mozzarella on a pizza | 85-170 | 99.4-272.2 per pizza (13 pizza recipes, divided by the unit count, not the slice count) |
| W31 aged cheese named on a plate | 15-60 | 16.0-45.8 on leaf salads (10); 20.0-64.1 on vegetable starters (13) |
| W26 pancetta or bacon | 16-32 | 9.7-70.9 (26) |
| W17 croutons or torn bread | 28-60 | 21.2-137.1 (23) |
| W18 corn kernels | 73-145 | 28.4-210.0 (19); 36.8-213.3 in soups (8) |
| W35 soft goat cheese | 20-60 | 16.2-95.7 (18) |
| W38 cured sausage | 20-60 | 10.7-56.7 (17) |
| W43 aubergine | 80-200 | 87.8-181.4 (17); 97.7-151.1 on vegetable starters (12) |
| W54 peas | 60-150 | 14.7-118.0 (37) |

The lemon and lime juice rows shrink a lot and the cream, pancetta and crouton rows widen upwards: recipe writers use less citrus and more cream than the hand rows assumed. The reading you accepted stands: a recipe's per-serving amount stands in for a restaurant's per-plate amount, and these are home recipes.

## 7. Top-ups, the category tag, the fat prior

PENDING_TOPUP

## 8. Flags

PENDING_FLAGS

## 9. Repeatability

PENDING_REPEAT

## 10. Spending

PENDING_SPEND

## 11. Questionable or unexpected

PENDING_QUESTIONABLE

## 12. Not built, and why

- The plate-weight model is built, validated and **off** by your own rule (section 5). Nothing else in 12.20 was left out.
- The URL sort of 3J item 10 stays not built (3J section 6).
- Telegram, deployment, accounts: the step after this one.

## 13. Decisions for you

PENDING_DECISIONS
