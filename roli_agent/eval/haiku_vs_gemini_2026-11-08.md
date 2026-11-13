# Claude Haiku 5.5 against Gemini 3.8 Flash on Roli's model tasks, 2026-11-08

Question (Julius, 2026-11-08): can a cheaper model do Roli's tasks other than reading the menu photo, as well as Gemini? Answer: not as it stands. Haiku is about
four times cheaper for the same work but worse on three of the four tasks, in the direction that matters, and it is not faster.

## Prices (OpenRouter, 2026-11-08, per million tokens)

| model | in | out |
|---|---|---|
| google/gemini-3.8-flash (Roli today) | $0.825 | $4.125 |
| anthropic/claude-haiku-5.5 | $0.10 | $0.50 |

## 1. The four test sets (same prompts, same day)

| task | test set | Gemini 3.8 Flash | Claude Haiku 5.5 |
|---|---|---|---|
| line tags | 149 decided lines (`tests/fixtures/line_tag_test_set.json`) | role 148 of 149; **0 harmful errors** after code's checks; kind 145 of 148 | answered only 136 lines; role 127 of 136; **2 harmful errors** after code's checks (5 before); kind 134 of 135 |
| dish kind | 400 labelled menu items | 387 of 400 (96.8 %); shellfish 13 of 16 | 384 of 400 (96.0 %); shellfish 10 of 16 |
| USDA matching | 44-line set | 40 usable (28 direct, 12 proxy), **0 false matches**, 2 unresolved | 32 usable (26 direct, 6 proxy), **5 false matches**, 3 unresolved |
| USDA matching | 54-line held-out set | 44 usable, 5 false matches, 3 unresolved | 30 usable, **9 false matches**, 9 unresolved |
| recipe grading | 33 recipes of 5 dishes | grade right 33 of 33 | one dish's reply failed the format check (8 recipes lost); of the other 25, grade right 19; 6 good recipes wrongly excluded as "preparation different" |

Cost of the test sets: Gemini $0.10, Haiku $0.02 (the grading runs were too small for the account counter to register).

## 2. The four menus

Same saved photo readings (read by Gemini), same cache state at the start (rewound to before the Gemini preview of 19:48 UTC), same code. Haiku did every model
task after the reading. Not quite like for like: Gemini reused recipe grades saved on earlier days (12 grading calls against Haiku's 89), so Haiku did more work.

| menu | model | time | model cost | model calls | dishes ranked |
|---|---|---|---|---|---|
| Flour + Water | Gemini | 82 s | $0.027 | 25 | 8 |
| | Haiku | 310 s | $0.045 | 83 | 7 |
| The Greyhound | Gemini | 361 s | $0.369 | 96 | 17 |
| | Haiku | 476 s | $0.078 | 127 | 13 |
| Zuni | Gemini | 85 s | $0.119 | 22 | 8 |
| | Haiku | 160 s | $0.029 | 44 | 4 |
| Chalkboard | Gemini | 152 s | $0.105 | 38 | 7 |
| | Haiku | 161 s | $0.020 | 41 | 5 |
| **all four** | Gemini | 680 s | **$0.62** | 181 | **40** |
| | Haiku | 1,106 s | **$0.17** | 295 | **29** |

Per call, by task (seconds): tagging Gemini 13.5, Haiku 10.9; matching 7.1 against 8.5; grading 12.3 against 10.0; copying recipes from pages 13.5 against 18.2.
Haiku wrote more text for the same answers (223,000 output tokens against 118,000; part of it is a different way of counting tokens, part more calls).

Why Haiku ranked 11 fewer dishes: its grading rejected 194 recipes as not the dish against Gemini's 124, so 250 recipes were calculated against 309; two grading
replies failed the format check and lost the dish (Koffmann's chips, Zuni's garden lettuce salad); its dish sorting left Padron peppers and pigs in blankets without a
sourced plate row; and on Zuni's marinated olives its tags led to a flagged estimate. On the 2,408 recipe lines both models tagged, they disagreed on 57 (2.4 %),
several of them oil read as a frying bath ("1/4 cup neutral oil", "Olive oil, as needed"), which leaves the oil out of the count.

## 3. Reading

- **Cost:** for this workload Haiku is about 3.6x cheaper (and it did more work); the eightfold price gap shrinks because it writes more tokens.
- **Speed:** no gain. Time is set by the number of model calls and Roli's limit of 16 calls a minute; per call Haiku is about as fast.
- **Quality:** tagging fails the rule used before (no more harmful errors than Gemini); matching makes more false matches, the error that matters most; grading is
  clearly worse and its replies break the format; dish sorting is close to a tie.
- Only the dish-kind call is a near-tie, and it is one call per menu, so switching it saves under a cent a menu.

Runs: Gemini preview `eval/mvp_eval_2026-11-08_3k_preview.*` (runs 20261108-194828-fbf41c, -194950-c973df, -195551-4228dc, -195716-6c1e7a); Haiku runs
20261108-204202-4920d5, 20261108-204712-848419, 20261108-205508-0cb9cc, 20261108-205748-4cbf18. Test-set outputs: `eval/line_tag_test_2026-11-08_gemini|haiku.*`,
`menu_reader_eval/relevance/results_2026-11-08_2026-11-08_gemini|haiku.json`; dish-kind and matching outputs in the session scratchpad.
