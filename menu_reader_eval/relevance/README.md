# Frozen relevance evaluation (Phase 2C.1, requirement C)

`relevance_set_v1.csv`: one row per distinct recipe actually read for the five Flour + Water test dishes (42 recipes), with the saved
outcome of the 2C live run and a **human-reviewable reference judgment** per recipe: `ref_gate` (should the Python gate pass it),
`ref_dish_type` / `ref_preparation` / `ref_course` (the rubric's three answers), `ref_grade` and `ref_hard_exclusion` (what Python's
`combine` should produce), and a rationale. The recipes themselves (titles, yields, verbatim ingredient lines, method text) are the frozen
inputs in `roli_agent/eval/frozen_inputs_2c1.json` (sha256 ec5410078f81...), re-ingested offline from the 2B-2 caches, so every run of the
rubric sees the same text.

Reviewer: the reference labels were drafted on 2026-11-03 and are **awaiting Julius's review** (`review_status: draft_unreviewed`).
Label changes are recorded here with hashes, never silently.

| Version | sha256 | Change |
|---|---|---|
| v1.0 | d982b540f50aabbe8f75c748435ea06947881abf9fea3c428dc743902c2cdbb9 | first draft, 42 rows, 34 pass the reference gate |
| v1.1 | f9b7b6fc3ec257abe243235b2275c15485e03f8afd6f3c504c864db5020ba422 | after the first gate scoring (41/42): "Little Gem Cookies Food" (cooking-guide.com) relabelled `ref_gate: rejected` with the method rule, since its method braises the lettuces ("cook" and "lettuce" in one sentence); v1.0 had it passing the gate and relying on the rubric, which also rejected it 5/5 |
| v1.2 | 2c3b47a65f933945482d2ea9c2ab036f634f56059fd3545ec0e90ca81b15b2d3 | after the independent review (2026-11-03): the SoPo Seafood and Sea Forager crudo rows relabelled `ref_gate: passed`; their pages do state quantities ("½ lb Bluefin Tuna", "6-8 oz bluefin") behind a leading list glyph that hid the numbers from the parser (parser fixed: `parse.LEADING_BULLET`) |
| v1.3 | dd6f96553d4774ba23b1f6360841305727b143455d12df8b93d8069bbfc1e74f | "Roasted Heirloom Tomato Soup" relabelled `ref_gate: passed` (same glyph fix; the rubric, not the gate, excludes it as a different dish); gate 42/42 against `roli_agent/eval/frozen_inputs_2d.json` (sha256 efd79fd18d77…, re-frozen offline with the current parser; the 2C.1 file is kept unchanged for its record) |

Runner: `roli_agent/scripts/eval_relevance_2c1.py` (`--write-skeleton` builds the CSV skeleton; `--runs N` runs the Python gate once and the
LLM rubric N times on the gate-passed recipes, reporting per-recipe agreement across runs and accuracy against the reference). Results:
`results_<date>_<tag>.json`.

Results on 2026-11-03 (model `google/gemini-3.8-flash` via OpenRouter, temperature 0, 5 runs, prompt with the method-sentence evidence):
gate 42/42 against v1.1 (41/42 against v1.0); rubric on the 33 gate-passed recipes: grade accuracy 99.4 % (164/165 run-recipe pairs;
the one miss is "Simple King Salmon en Papillote" graded low in 1 of 5 runs), fully consistent three-answer triple in 21 of 33 recipes,
exact-triple accuracy 77.6 % (the inconsistency is same/variant and same/similar wording on salmon and salad recipes, which Python maps to
the same grade). The two grilled little-gem recipes that the rubric admitted in the 2C live run are now rejected by the Python gate before
grading (`hard_exclusion:main_ingredient_cooked_in_method:grill`), so their admission can no longer vary with the model.

**Independent review (Phase 2D, 2026-11-03):** `roli_agent/scripts/review_relevance_labels.py` had a second model from a different family
(`anthropic/claude-sonnet-5.5` via OpenRouter; the pipeline grades with Gemini 3.8 Flash) judge all 42 frozen recipes without seeing the
reference labels: usable, dish type, preparation, course, and whether the method cooks the main ingredient of a raw dish. Results in
`independent_review_2026-11-03.{json,md}`: 42 reviewed, 16 in full field-level agreement, 26 with some disagreement, 12 preparation-related;
on the outcome that matters (admitted as a scenario or excluded) the reviewer agrees with the reference on **42 of 42** after the v1.2/v1.3 corrections
(no material disagreement remains; the review file lists the check). The field-level disagreements are wording
(`variant`/`similar` for a recipe whose garnishes differ from the menu's, where the reference says `same`/`same`; both map to the same grade).
Two of the first run's disagreements were material and right: the bullet-glyph parsing defect above. Cost: 42 calls, $0.19, 108 s (throttled to the
model's 20 requests per minute).
