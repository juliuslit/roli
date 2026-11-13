# Checkpoint 3B: ingredient role and midpoint ranking

Date: 2026-11-05. Status: **both changes built and tested; four menus rerun twice (the second time with one small follow-up fix); stopped for
review.** Scope per Julius's brief of 2026-11-05: two targeted improvements, no new architecture. Spec: `SPEC_3_mvp.md` section 9.
Before/after per dish: `eval/mvp_before_after_2026-11-05.md` (before = the Checkpoint 3A final runs). Run files: `eval/mvp_eval_2026-11-05_midpoint{,_final}.*`.

## 1. The two changes

1. **Ingredient role** (`recipes/adapt.py`, `ingredient_role`; CSV column `role_sensitive` on the cheese, cured-meat, nut, seed and olive rows W05, W07, W22,
   W24, W26, W30-W38, W41). When the role is clear, a garnish takes the lower half of the row's existing range and a substantial ingredient the upper half;
   otherwise the whole range stays. Clear means a garnish or substantial word beside the ingredient on the menu or in the recipe line ("shaved parmesan",
   "to finish", "baked goat cheese"), the ingredient named in a salad's or pizza's own name (substantial), or a cheese, cured meat or nut listed beside a
   fish or meat main (garnish). No model call, no new rows, no review-status change; the assumption's basis records the role and why.
2. **Midpoint ranking** (`mvp/ranking.py`). Dishes with a credible interval are ordered by (low + high) / 2 of saturated fat; two centres within 0.25 g or 5 %
   are an effective tie and the central cholesterol decides (the page says so). Ranges stay on display, with the middle beside them and a line explaining
   the order. A dish without an upper bound gets no midpoint and is never ranked; toss-up, tentative and well-supported labels come from the unchanged
   pairwise verdicts.

Two targeted corrections found while rerunning, both tested: a "1 (8-rib) pork rack" no longer counts as one 133 g chop (`convert.py`), which is the one
demonstrated outlier-recipe case and had withdrawn the Flour + Water pork chop's bound; a service note the menu reader puts in a description
("(served with the above accompaniments)") is no longer a menu-only ingredient (`relevance.py`), which had left the Zuni ribeye unbounded in the first rerun.
The Phase 2D aggregation itself (min low, max high, withdrawal by an incomplete recipe's lower bound) is unchanged.

## 2. Tests

`roli_agent`: **271 passed** (was 266), 4 live skipped; `nutrition_service`: 315 passed. New: garnish vs substantial vs ambiguous role (feta on a fish main
15-30 g, in a salad's name 30-45 g, on a pasta 15-45 g; garnish words on the menu and in a recipe line; dressing rows never role-adjusted); midpoint order
among overlapping ranges with the toss-up wording; saturated-fat tie broken by central cholesterol, a non-tie decided by saturated fat; unbounded dishes
never ranked and never given a midpoint; a rack is not a chop; service notes are not ingredients. No regressions; Phase 2A arithmetic untouched.

## 3. Before (3A) and after (now): top three, warm caches

| Menu | Ranked 3A -> now | Top three 3A | Top three now | Time s | Model $ | Credits |
|---|---|---|---|---|---|---|
| Flour + Water | 5 -> **6** | Tomatoes 0.4-2.4; Crudo 0.5-4.3; Little gem 4.4-8.6 | same ranges, same order (mids 1.4, 2.4, 6.5); pork chop now 5th at 6.7-16.4 | 117 -> 107 | 0.056 -> 0.048 | 0 -> 0 |
| The Greyhound | 1 -> 1 | Padron peppers 1.2-3.0 | same | 117 -> 105 | 0.059 -> 0.054 | 0 -> 0 |
| Zuni Café | 4 -> 4 | Soup 0.7-4.7; Caesar 2.3-5.7; Shrimp spaghetti 1.9-11.9; Ribeye 11.4-28.2 | Soup **0.7-3.9**; Caesar **2.0**-5.7; Spaghetti 1.9-11.9; Ribeye 11.4-28.2 (mids 2.3, 3.8, 6.9, 19.8) | 116 -> 112 | 0.060 -> 0.062 | 5 -> 0 |
| Seafood chalkboard | 4 -> 4 | Poke 2.0-7.3; Swordfish crudo 2.5-15.2; Snapper 4.7-15.7; Ocean trout 6.2-20.4 | Poke 2.0-**7.1**; Crudo 2.5-**13.2**; Snapper 4.7-**15.4**; Ocean trout 6.4-**26.2** (mids 4.6, 7.8, 10.0, 16.3) | 73 -> 84 | 0.036 -> 0.042 | 5 -> 0 |

**The order of every top three is unchanged.** On these menus the midpoint and the upper bound agree because the intervals that overlap are nested or
offset in the same direction; the two labelled toss-ups (tomatoes/crudo; soup/Caesar/spaghetti) remain toss-ups. What changed, and why:
- Narrower upper ends on the soup (parmesan shavings read as a garnish), the Caesar's lower end, the swordfish crudo and the snapper (feta beside a fish
  main at 15-30 g instead of 15-45 g), and the poke salad: **the ingredient-role rule**, as intended.
- Flour + Water 5 -> 6 ranked: **the rack correction** (the pork chop keeps its 6.7-16.4 g bound).
- Ocean trout 20.4 -> 26.2 g at the high end: a different fourth recipe was graded relevant this time: **model variability**, not a code change.
- Zuni credits 5 -> 0 and the small time differences: cache warmth.
- Across the two reruns today the top three were identical on all four menus; the only run-to-run difference was the Zuni ribeye dropping out once
  because of the service-note parse, which is now fixed.

Spend today: 8 runs, $0.41 of model calls, 2 Tavily credits (ledger); no budget interruption.

## 4. Unexpected or questionable ranking changes

None in the order. Two things to watch: the midpoint of a wide range (shrimp spaghetti 1.9-11.9 g, centre 6.9) now ranks it under the ribeye's 19.8 and
above the Caesar's 3.8, the same place as before, but a wide range's centre is only as good as its two recipes; and the role rule treats any cheese,
cured meat or nut beside a fish or meat main as a garnish, which is right for a sprinkle of feta and would understate a dish where the cheese is a real
component (none on these menus).

## 5. Blockers to local testing

None. `./roli_local.sh start` runs the current code; the ranked table shows range, middle and a tie note; the diagnostics show each assumption's role.
Open items for later testing feedback remain those of Checkpoint 3A section 8 (portion ranges, category defaults); nothing new.

Files: `recipes/{adapt,convert,relevance}.py`, `recipes/assumed_weights.{csv,md}` (column `role_sensitive`), `mvp/{ranking,models,web}.py`, `tests/test_mvp_local.py`
(+6 tests), `SPEC_3_mvp.md` (section 9), `eval/mvp_before_after_2026-11-05.md`, `eval/mvp_eval_2026-11-05_midpoint{,_final}.*`, 8 runs under `runs/`, this file.
Unchanged: Phase 2A, D23, every `approved_by`, portion rules, menu reading, spending limits, `.env`.

**Stopped here.**
