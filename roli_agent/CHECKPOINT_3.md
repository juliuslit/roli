# Checkpoint 3: Roli MVP for invited testers

Date: 2026-11-04. Status: **working prototype built and tested; evaluated live on the Flour + Water menu (twice) and two unseen menus; stopped for review. Not deployed; no tunnel opened; nothing approved on your behalf. Your OpenRouter credit is exhausted ($0.23 of $10 left), which cut the evaluation short: see section 7.** Specification: `SPEC_3_mvp.md`; decisions in `SPEC_2B_recipe_scenarios.md` section 15.8; deployment recommendation in `roli_agent/mvp/DEPLOY.md`; test output in `test_report_3.txt`.

## 1. Summary

| Item | Result |
|---|---|
| Your decisions | I01 marked approved; I02 enabled for plain vinegar with the evidence documented in the rule (USDA cider and distilled vinegar report 0 mg; the wine and balsamic records omit the row), mixtures excluded by pattern; pizza unit yields give the recipe basis one serving per unit and the P1 count ("One 12-inch pizza" pages are now calculated); a disjoint pair that rests on external-evidence bounds is `tentative`, never `well_supported`; experimental mode is the only mode that ranks, and says so on every page |
| What was built | `roli_agent/mvp/`: `menu_run.py` (photo -> menu reader -> dish selection -> parallel `estimate_dish` -> 2D intervals -> comparison -> ranking -> 80-word recommendation -> saved run), `ranking.py`, `web.py` (FastAPI: upload, progress page, recommendation, diagnostics, feedback, past runs; shared-token access), `models.py`; rules for meat mains, pasta, generic starters (PR07-PR11) and a seasoning-blend weights row (W29), all `proposed_unreviewed`; a process-wide model rate limiter with 429 retries |
| Tests | agent **248 passed** (10 new in `test_mvp.py`: run orchestration with a failing search, unreadable photo, approved mode, ranking and support labels, the 80-word cap, the web routes with token, upload limits, feedback storage, dish types for unseen menus, the rate limiter), library 308; Phase 2A untouched; the Phase 2B reply byte-identical |
| Flour + Water, end to end from the photo | 19 items read, 17 evaluated, **5 ranked** (the five known dishes), 12 could not be estimated; cold 523 s / warm 148 s; identical ranking and identical recommendation text across the two runs |
| Unseen menus | gastropub: 12 evaluated, 1 ranked; Zuni Café: 9 evaluated, 2 ranked, 2 errored on the credit limit; third menu not run (credit) |
| Cost per menu | model calls for the dishes $0.06 (warm) to $0.33 (cold, 17 dishes); 20-24 search credits per unseen menu (0 when cached); 10-711 USDA requests |
| Human review of the recommendations | `eval/mvp_review_v1.md`: rankings right where a dominant ingredient decides, correctly hedged where two lean plates compete, coverage the limit on unseen menus; two defects fixed after the runs but not re-measured live |

## 2. The experience, as built

A tester opens the link with the shared token, uploads a menu photo (resized to the 1280 px Telegram size the reader was tested at), and lands on a progress page that refreshes until the run ends (2-9 minutes). The result page shows the recommendation (at most 80 words, Python template), the full ranked table with saturated fat and cholesterol per modeled plate and a support label per dish (`well_supported`, `tentative`, `close_call`, `only_estimate`), the dishes that could not be ranked with the reason, the menu items not evaluated, a link to the diagnostics, and a feedback form (dish inaccurate / ranking unexpected / uncertainty wording unhelpful / other, plus text) stored as JSON lines. The diagnostics page shows, per dish, every recipe read with its URL, yield, relevance grade and basis, every ingredient line with its USDA record (data type, proxy or not), grams, state and blocker, the inferences, every assumption with gap, row, grams low/high, basis and review status, every portion model with rule, fraction arithmetic and limitations, the intervals per nutrient with tier and caveats, the pairwise verdicts with their tentative reasons, errors, timings and costs. An "Experimental" banner tops every page.

Recommendation shown for Flour + Water (both runs): *Lowest saturated fat on this menu, by our estimate: 1) Bluefin Crudo (about 0.5-1.6 g saturated fat per plate, close call); 2) Heirloom Tomatoes (about 0.4-2.1 g saturated fat per plate, tentative); 3) Little Gem Lettuces (about 4.4-8.6 g saturated fat per plate, close call). Bluefin Crudo carries about 17-115 mg cholesterol. Figures are modeled from published recipes and typical restaurant portions, not this kitchen's own numbers. 12 of 17 dishes could not be estimated.* (75 words.)

## 3. Ranking: the four kinds of comparison

`compare_dishes` now returns `well_supported` (disjoint intervals, margin not narrow, holds without any external-evidence bound), `tentative` (disjoint but narrow, or the lower dish's upper bound exists only through, or depends on, external bounds), `overlapping`, `insufficient_evidence` (a side has no upper bound). `rank_dishes` orders the dishes with an upper bound by that bound (cholesterol upper bound breaks ties) and labels each pick by its verdicts against the dishes below it; a dish without an upper bound is never recommended and is listed with the reason; a lone ranked dish is `only_estimate`, not "well supported".

## 4. Live results

| Menu | Run | Items | Evaluated | Ranked | Unranked | No recipes | Errors | Not evaluated | Total s | Search credits | Model calls | Model $ (dishes) | USDA requests |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Flour + Water (cold caches) | 20261104-010950 | 19 | 16 | 5 | 11 | 1 | 0 | 2 | 523 | 0 (cached) | 135 | 0.33 | 711 |
| Flour + Water (warm) | 20261104-011834 | 19 | 16 | 5 | 11 | 1 | 0 | 2 | 148 | 0 | 40 | 0.06 | 10 |
| The Greyhound (gastropub, unseen) | 20261104-012103 | 38 | 12 | 1 | 11 | 0 | 0 | 26 | 340 | 24 | 84 | 0.18 | 447 |
| Zuni Café (unseen) | 20261104-012643 | 71 | 9 | 2 | 7 | 1 | 2 | 59 | 290 | 20 | 62 | 0.14 | 179 |

Details and every recommendation: `eval/mvp_eval_2026-11-03.md`; raw runs under `roli_agent/runs/`. Per dish the pipeline took 15-60 s cold; menu reading 9-29 s; comparison and ranking under 10 ms. The model-call cost excludes the menu-reading call (not metered through the runner; about $0.01-0.03 per photo at this model's prices).

**Consistency:** the Flour + Water menu run twice gave the same five ranked dishes in the same order with identical text and the same unranked set; the second run reused the caches (search, pages, extraction, USDA matches), so what varied was the model's relevance grading and the new-line matching, and neither changed a verdict.

**Error handling:** a search outage, an unreadable photo, a model failure in grading and a provider credit refusal (402) were all exercised, the first two in tests and the last two live; each is recorded on the dish or the run and the page still renders. The first live attempt failed on the provider's 20-requests-per-minute limit across parallel dishes (8 of 17 dishes errored, the second run's menu read failed); the shared limiter fixed it: 0 retries and 0 errors on the rerun, at the cost of 72-180 waits per menu.

## 5. Coverage: why most dishes could not be ranked

Of the 37 dishes evaluated across the three menus, 8 were ranked. The reasons, from the diagnostics:

| Cause | Dishes | Example | Honest? | Fixable? |
|---|---|---|---|---|
| a menu-only ingredient with no weights row leaves the pair unfilled | 9 | burrata, caciocavallo, mussels escabeche, lamb merguez ragu | yes: an unknown amount of cheese or meat is material | only with more rows or a generic per-category default, which is an assumption for you to allow |
| no recipe can be portioned: unweighed lines make P2 impossible, or the pasta recipe gives flour not pasta | 10 | pole beans, arancini, croquettes, scotch egg, filled pastas | yes | a P3 key for "cheese" or "egg" starters would help some |
| frying or cooking oil without a quantity | 4 | fish and chips, schnitzel, steak frites | yes: deep-frying oil is unknowable from a recipe | no, by design |
| unquantified seasoning or spice blend | 3 | sirloin steak "mesquite seasoning" | no: a dry rub cannot move a 280 g steak | W29 added after the run (not re-measured) |
| a product with a cooking word in its name treated as a cooking step, or egg pasta treated as flesh | 3 | smoked paprika, toasted coriander, fresh egg pasta | no | fixed after the run (not re-measured) |
| USDA "unprepared" bacon/pancetta records classified as unknown state | 2 | pole beans, taleggio scarpinocc | no | a Phase 2A word-table gap (`preparation.py` does not know "unprepared"); not changed, yours to decide |
| provider credit refusal | 2 | Zuni Caesar, Zuni pizza | n/a | credits |

## 6. Cost, latency, consistency, in one place

- **Latency:** 2.5 minutes (warm) to 9 minutes (cold, 17 dishes) per menu with 3 parallel dishes under the 16-per-minute model limit; the limiter, not the work, sets the pace (127-180 waits per cold menu). Two testers uploading at once would halve each other's speed.
- **Cost:** dish calls $0.06-0.33 per menu plus the menu read; 0-24 search credits (Tavily plan at 143 + about 44 of 1500 after these runs; the usage endpoint lags); USDA free.
- **Consistency:** same ranking and text on the repeated menu.
- **Model budget:** OpenRouter shows $9.77 of $10.00 spent on this key across all phases; the last run hit 402. Nothing was purchased; adding credit is your decision.

## 7. What was not done, and why

- The third unseen menu (seafood chalkboard) was not run and the post-fix re-measurement of all four menus was not run: the credit ran out. The seasoning row, the product-name rule, the egg-pasta rule, the sharing-platter exclusion and the raised cap are tested but their live effect is not measured.
- Not deployed: `DEPLOY.md` recommends running on your Mac behind a Cloudflare Tunnel with Cloudflare Access (e-mail one-time codes) plus the app's shared token; needs your Cloudflare account and a domain, so it waits for you.
- Telegram, accounts, menu-wide ranking of dishes without a portion rule: out of scope, as agreed.

## 8. Readiness for broader testing

**Ready for a handful of invited testers, with three conditions; not ready for broader testing.**

Supports it: the end-to-end path works from a photo; every figure is traceable in the diagnostics; the recommendation never ranks on a lower bound, labels close calls and tentative calls, and says plainly what could not be estimated; the Flour + Water result is stable across runs; errors degrade to a labelled dish, not a crash.

Conditions before even invited testers: (1) model credit and a per-menu budget cap (a cold menu costs up to $0.35 in dish calls; the limiter also means a tester waits minutes); (2) the two cheap wording fixes from the review: name the specialty ingredient that drives a cholesterol range (bottarga), and prefer mains and starters over snacks when the dish cap bites; (3) one re-measurement pass over the four menus with the fixed code.

Blocks broader testing: coverage. On unseen menus 1 of 12 and 2 of 9 dishes were ranked. The misses are honest (unknown cheese or meat amounts, frying oil) but a tester who gets "11 of 12 could not be estimated" learns little. The levers are yours: allow generic per-category defaults for menu-only ingredients (a new class of assumption), fund the weighings that would narrow the portion rules, and approve the rows the five dishes already rest on.

## 9. For your review

1. Model credit: whether to add OpenRouter credit, and a per-menu cap (suggested: 14 dishes, $0.50).
2. The two wording changes above, and whether the cap should prefer mains and starters.
3. W29 and PR07-PR11 (seasoning blends; meat, pasta, generic starters, fish starters): keep as experimental rows or remove.
4. Whether a generic default for menu-only ingredients by category (cheese garnish, cured meat, dressing) may exist as an experimental assumption.
5. The Phase 2A word-table gap ("unprepared" bacon): change the calculator's classifier or leave it.
6. `eval/mvp_review_v1.md`: correct any verdict you disagree with.
7. Deployment: Cloudflare Tunnel + Access as recommended, or a small VPS.

## 10. Files

Created: `roli_agent/SPEC_3_mvp.md`, `roli_agent/mvp/{__init__,models,menu_run,ranking,web}.py`, `roli_agent/mvp/DEPLOY.md`, `roli_agent/scripts/eval_mvp.py`, `roli_agent/tests/test_mvp.py`, `roli_agent/eval/{mvp_eval_fw.json,mvp_eval_fw.md,mvp_eval_2026-11-03.md,mvp_review_v1.md}`, `roli_agent/runs/<4 runs>/`, `roli_agent/test_report_3.txt`, this file.

Modified: `roli_agent/llm.py` (`RateLimitedLLM`), `roli_agent/recipes/{inference,ingest,parse,pipeline,portions,compare_dishes,adapt,match,models}.py`, `roli_agent/recipes/{portion_rules,blocked_evidence,assumed_weights}.csv` (+ `.md`), `roli_agent/scripts/evaluate_2d.py`, `roli_agent/SPEC_2B_recipe_scenarios.md` (15.8), `roli_agent/tests/{test_recipes_2d,test_recipes_adapt}.py`, the project notes. Unchanged: the Phase 2A calculator, D23, every `approved_by`, the Phase 2B reply, `code/`, the MCP wrapper, the LangSmith prototype. Secret scan: 0 hits.

**Stopped here.**
