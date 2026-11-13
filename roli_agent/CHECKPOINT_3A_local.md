# Checkpoint 3A: Roli ready for Julius's local testing

Date: 2026-11-04. Status: **built, tested, evaluated live on four menus (three passes, the last with the final code); stopped for review.** Scope per
Julius's brief of 2026-11-04: one user on his Mac; functionality, recommendation quality, performance; no deployment, authentication, Telegram or
privacy infrastructure. Nothing purchased, no billing settings touched, no top-ups enabled; `.env` untouched. Spec: `SPEC_3_mvp.md` section 8.
Human review: `eval/mvp_review_v2.md`. Before/after: `eval/mvp_before_after_2026-11-04.md`. Tests: `test_report_3a.txt`.

## 1. Test results and regressions

| Suite | Before | After | New |
|---|---|---|---|
| `roli_agent` (root `.venv`) | 248 passed | **266 passed**, 4 live tests skipped | `tests/test_mvp_local.py` (18): budget limits, actual vs estimated cost, thread safety, ledger and daily limits, cached searches never blocked, price loading, a run that hits its budget, lean score, course-balanced selection, wording (toss-up, tentative, bottarga driver, zero cholesterol, high-cholesterol notice, long names), unprepared bacon state and strips-as-slices, match cache state recomputation, fraction-slash and "about" quantities, deep-dish exclusion and cheese substitution, a fried recipe with no fat line, local web mode |
| `nutrition_service` (own `.venv`) | 308 passed | **315 passed**, 4 live skipped | 7 word-table cases ("unprepared", "unheated", cooked bacon) |

Regressions: none. Phase 2A arithmetic untouched (only the raw/cooked word table gained three words, as asked). Five Phase 3 tests were updated for the
new statuses and wording. Secret scan over the changed files: 0 hits.

## 2. Before-and-after menu evaluation

Before = the Phase 3 runs of 2026-11-04 (menu-order selection, no budget, old wording, before the fixes). After = the final pass with all fixes.
Three passes were run today: pass 1 (all fixes except the match-cache state), pass 2 (plus the cache fix), final (plus the deep-dish, cheese-substitution,
frying-fat and vegetable-row fixes that pass 2 exposed). Per-pass files: `eval/mvp_eval_2026-11-04_local{,_v2,_final}.{json,md}`.

| Menu | Items read | Candidates | Tried | Evaluated | Ranked before -> after | Unranked after | Not tried (cap) | Credits before -> after | Model calls | Model $ before -> after | Time s before -> after | Words |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Flour + Water | 19 | 17 | 14 | 13 (+1 no recipes) | 5 -> **5** | 8 | 3 | 0 -> 0 | 135 -> 33 | 0.334 -> **0.056** | 523 -> **117** | 74 |
| The Greyhound (gastropub) | 38 | 14 | 14 | 14 | 1 -> **1** | 13 | 0 | 24 -> 0 | 84 -> 31 | 0.185 -> **0.059** | 340 -> **117** | 62 |
| Zuni Café | 71 | 13 | 13 | 13 | 2 -> **4** | 9 | 0 | 20 -> 5 | 62 -> 24 | 0.136 -> **0.060** | 290 -> **116** | 70 |
| Seafood chalkboard | 9-10 | 7-8 | 7 | 7 | (not run) -> **4** | 3 | 0 | 8 (pass 1) -> 5 | 62 -> 20 | 0.150 (pass 1) -> **0.036** | 235 (pass 1) -> **73** | 73 |

Reading the differences honestly:
- **Cost and time fell 3-5x mainly because the caches were warm** (search, pages, extraction, USDA matches); the first cold pass today cost $0.06-0.15 per
  menu. The limiter waited 4-56 times per menu instead of 72-180 because fewer calls were needed.
- **Zuni 2 -> 4 ranked** is an actual improvement: the Caesar salad no longer errors (credit), and the shrimp spaghetti was reached by the course-balanced
  selection. The Greyhound stays at 1 for structural reasons (section 5). Flour + Water stays at 5; its crudo range widened (1.6 -> 4.3 g) because two more
  recipes are now bounded (the pinch rule and the E22 chile row from Phase 3), which moved the tomatoes to first; the pair is a toss-up either way.
- **The bacon fix did work** (pole beans: bacon resolved) but only after the match cache stopped freezing a record's old state; the pappardelle
  swapped its recipes between runs (relevance grading variability), so its status change is not attributable to code.
- **Recipe and menu-read variability** between passes is real: the seafood chalkboard read 10 items once and 9 the other times; the pappardelle and
  salsiccia recipes changed. The top-three rankings were stable across today's passes for every menu except the two material errors below.

## 3. Sample recommendations (as shown, final pass; Zuni re-rendered with the final wording, see below)

**Flour + Water** (74 words): Among the 5 dishes I could estimate (14 tried; 9 had no usable estimate; 3 not tried), lowest saturated fat first:
1) Heirloom Tomatoes, about 0.4-2.4 g saturated fat per plate; 2) Bluefin Crudo, 0.5-4.3 g; 3) Little Gem Lettuces, 4.4-8.6 g. Heirloom Tomatoes and
Bluefin Crudo overlap, so treat that order as a toss-up. Heirloom Tomatoes has no cholesterol in its ingredients. Modeled from published recipes and
typical portions, not this kitchen's numbers.

**The Greyhound** (62 words): Among the 1 dish I could estimate (14 tried; 13 had no usable estimate), lowest saturated fat first: 1) Padron Peppers,
about 1.2-3.0 g saturated fat per plate. It's the only dish I could estimate, so this is one figure, not a ranking. Padron Peppers has no cholesterol in
its ingredients. Modeled from published recipes and typical portions, not this kitchen's numbers.

**Zuni Café** (77 words, final wording): Among the 4 dishes I could estimate (13 tried; 9 had no usable estimate), lowest saturated fat first: 1) Wood
fire-roasted tomato and eggplant soup, about 0.7-4.7 g saturated fat per plate; 2) Zuni Caesar salad, 2.3-5.7 g; 3) Spaghetti with Gulf shrimp, 1.9-12 g.
These ranges overlap, so treat the order as a toss-up. Spaghetti with Gulf shrimp may carry up to 376 mg cholesterol. Modeled from published recipes and
typical portions, not this kitchen's numbers. *(The saved run's text, written minutes earlier, reads "Spaghetti with Gulf shrimp, heirloom tomatoes,
basil, garlic,," and lacks the cholesterol notice; both wording fixes came from reading it.)*

**Seafood chalkboard** (73 words): Among the 4 dishes I could estimate (7 tried; 3 had no usable estimate), lowest saturated fat first: 1) Ocean Trout /
Tuna Poke Salad, about 2.0-7.3 g saturated fat per plate; 2) Crudo Of Swordfish, 2.5-15 g; 3) Snapper, 4.7-16 g. These ranges overlap, so treat the order
as a toss-up. Ocean Trout / Tuna Poke Salad cholesterol about 18-43 mg. Modeled from published recipes and typical portions, not this kitchen's numbers.

Top three with figures, cholesterol drivers and the reasons dishes stay unranked: `eval/mvp_before_after_2026-11-04.md` and each run's page.

## 4. Spending and latency

- **Per menu (warm caches):** $0.036-0.060 of model calls (menu read included), 0-5 Tavily credits, 73-117 s. **Cold (pass 1 today):** $0.06-0.15, 8 credits,
  146-255 s. Every call was priced by the provider; no estimated or flat-reserve charges were needed. No budget interruption occurred (cap $0.50).
- **Today in total:** 13 runs, $0.94 of model calls, 37 Tavily credits (ledger `runs/spend_ledger.jsonl`). OpenRouter reports $10.78 used of the $20.00 now
  on the key (so about $9.22 left); Tavily 267 of 1,500 monthly credits.
- **Safeguards built** (`mvp/budget.py`): $0.50 per menu, 30 credits per menu, $5.00 and 300 credits per day (env-overridable), enforced before every model
  call and live search across the parallel dish threads; a dish hit mid-way is `budget_stopped`, dishes not started are `skipped`, the run still ranks what it
  has and the page says why. Actual (provider-priced) and estimated (token-priced from the public price list) spending are reported separately.
- **LangSmith:** the free plan's monthly trace limit is exceeded; tracing failures are logged and harmless to results, but noisy. Setting
  `LANGSMITH_TRACING=false` in `.env` silences them (your call; I did not change `.env`).

## 5. Remaining material accuracy and coverage concerns

1. **Per-plate category defaults dominate some ranges.** Feta 15-45 g and salsa verde 20-45 g set the upper ends of all four seafood fish mains; the little
   gem salad is 60 % assumptions. The labels (toss-up, tentative, assumption-driven) are right, but the ranges are wide and a tester may find them vague.
2. **Portion rules are unverified and sometimes mis-sized**: a main-course Caesar at the leaf-salad plate of 100-250 g (PR04) probably undersizes it.
3. **One outlier recipe can withdraw a dish's bound** (Flour + Water pork chop: a double-cut-chop recipe whose chop weight the parser could not read gave
   f = 1.5 and a 150 g lower bound). The withdrawal rule is right; a per-recipe sanity check on f is not built.
4. **Run-to-run variability:** the menu reader and the relevance grader are not deterministic at temperature 0; the top three held across today's passes but
   the recipes behind a dish can change. Consistency across repeated uploads of the same photo was 3 for 3 on Flour + Water and Zuni today, 2 for 3 on the
   seafood chalkboard (one read split the menu differently).
5. **Coverage on pub-style menus stays low** (1 of 14): deep-frying oil (correctly never assumed), side dishes written as menu words, and a Phase 2A rule that
   refuses an as-used state for anchovies in oil (a decision of yours, not changed).
6. Chanterelles stay open because USDA reports no saturated fat for the record (D23: never borrowed).

Nothing in this list prevents local testing; items 1-2 are what your feedback should target.

## 6. Exact commands

```
cd /Users/juliuslitinskas/projects/roli
./roli_local.sh start          # http://127.0.0.1:8008/  (loopback only; log in roli_agent/runs/web.log)
./roli_local.sh status
./roli_local.sh stop
./roli_local.sh restart        # after a code change
```
Then in a browser: open http://127.0.0.1:8008/, choose a menu photo, press "Read this menu", watch the progress page (refreshes every 5 s, shows each dish
as it finishes with the running spend), read the recommendation, open "Internal diagnostics" (recipes, USDA matches, assumptions, portion models,
intervals, pairwise verdicts, the dish-selection table, the spending report), use the feedback form (saved to `roli_agent/runs/feedback.jsonl`), and
"Past runs" for earlier results. Verified today: start, index, past runs, an old run's page and diagnostics, stop (`web.log`); a full upload-to-result
run through the web layer is covered by the test suite (`test_web_app_requires_the_token_and_serves_the_pages`, local mode test) and the live runs went
through the same `MenuRunner`.

Command-line alternatives: `.venv/bin/python -m roli_agent.scripts.eval_mvp --photos <photo> [--repeat 2] [--menu-budget-usd 0.50]`;
`.venv/bin/python -m roli_agent.scripts.compare_mvp_runs --before <run id> --after <run id>`.

## 7. Readiness

**Ready for your hands-on testing.** The end-to-end path works from a photo on your Mac; every number is traceable; spending is capped per menu and per day;
coverage is stated in the first sentence of every recommendation; close calls and assumption-driven orders are labelled; the two material errors found
today (a deep-dish recipe as a Neapolitan unit at 47-111 g; a fried recipe with no fat line at 0.8-1.8 g) are fixed and tested.

What to look for while testing: wide ranges that rest on a single assumed garnish amount (feta, pecorino), a salad or pasta portion that looks too small
or too large for the restaurant, and any dish you know to be rich that ranks near the top. The feedback form has those three categories.

## 8. For your review

1. Keep the category-default rows W30-W49 as experimental (recommended) or narrow them; the feta and salsa-verde amounts are the ones that move rankings.
2. The leaf-salad plate rule PR04 (100-250 g) for main-course salads: raise the high bound or add a "salad main" type.
3. The "may carry up to N mg cholesterol" notice for a pick whose upper bound reaches 300 mg: keep, or lower the threshold.
4. `LANGSMITH_TRACING` in `.env`: leave on (trace quota exceeded this month) or turn off.
5. `eval/mvp_review_v2.md`: correct any verdict you disagree with.

## 9. Files

Created: `mvp/budget.py`, `mvp/selection.py`, `scripts/compare_mvp_runs.py`, `tests/test_mvp_local.py`, `roli_local.sh` (repo root), `eval/mvp_review_v2.md`,
`eval/mvp_before_after_2026-11-04.md`, `eval/mvp_eval_2026-11-04_local{,_v2,_final}.{json,md}`, `test_report_3a.txt`, this file; USDA fixtures `food_168277.json`
(bacon, unprepared) and `food_328637.json` (cheddar) with manifest entries; 13 runs under `runs/` and `runs/spend_ledger.jsonl`.

Modified: `mvp/{menu_run,ranking,models,web}.py`, `mvp/DEPLOY.md`, `recipes/{adapt,compare_dishes,convert,match,models,parse,pipeline,portions,search}.py`,
`recipes/assumed_weights.{csv,md}` (54 rows; new columns `dish_types`, `exclude_pattern`, `substitutes_family`; W26 and W05 keys extended; W15 exclusion),
`scripts/eval_mvp.py`, `SPEC_3_mvp.md` (section 8), the project notes, `.gitignore`, tests; `nutrition_service/roli_nutrition/recipe/preparation.py` (three raw
words) and its test. Unchanged: the Phase 2A arithmetic, D23, every `approved_by`, `code/`, the MCP wrapper, the LangSmith prototype, `.env`.

**Stopped here.**
