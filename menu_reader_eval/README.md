# Menu reader evaluation - what is in this folder

| file | what it is | who reads it |
|---|---|---|
| `prompts/menu_reader_v1.md` | The instructions sent to every model with each photo. Version 1: no example. | the model (and you) |
| `prompts/menu_reader_v2.md` | Version 1 plus a worked example (a made-up cafe menu and its correct answer). | the model |
| `prompts/menu_reader_v3.md` | Version 2 plus a step-by-step reading procedure. Run only if v1/v2 miss items on dense menus. | the model |
| `prompts/menu_reader_v4.md` | v2 plus guidance on small print and blurred lines. | the model |
| `prompts/menu_reader_v5.md` | v2 with rules 1 and 3 merged into "What to include" (read small print, leave out only incomplete names, never complete or add a line), examples for headings, cut-off lines, shared prices, option lists and tiers, a per-section line count, and a flavour-list line in the worked example. Approved 2026-10-30; the last hand-written prompt of round one. | the model |
| `prompts/menu_reader_v6.md` | v5 plus one rule (rule 10): a line that describes several dishes is not a dish; attach it to each dish it describes. Added 2026-11-06 (`roli_agent/SPEC_3_mvp.md` 12.12.3). | the model |
| `answer_format.md` | The exact shape of the answer and what each field means. The prompt carries the same rules; this is the readable spec. | you, and whoever writes the scoring code |
| `expected/menu_01.json` ... `menu_25.json` | One file per photo, with two blocks: `expected` (the correct answer, in the answer format) and `scoring_hints` (side information for the scorer - see below). Built from `../menu_test_set/answer_key.csv`. | the scoring code |
| `expected_outputs.jsonl` | The same 25 records in one file, one per line - the form LangSmith's dataset upload takes. | LangSmith |
| `scoring_hints.csv` | The same `scoring_hints` blocks as a table, one row per photo, so you can read them without opening JSON: which photos must be flagged `partly`, which cut-off lines are set aside, which answer-key items are medium or low confidence. | you |
| `photo_level.csv` | One row per photo: `readable` and `problems` of the expected answer. Lives here because the answer key has no photo-level columns. Read by `code/build_expected.py`, which rebuilds `expected/`, `expected_outputs.jsonl` and `scoring_hints.csv` from the key. | the build script |
| `scoring_rules.md` | The nine scores, their pass bars and the decision rule, in plain English. Approved before any scoring code is written. | you, then the scoring code |

**Where are the scoring hints?** In two places with identical content: inside each `expected/menu_NN.json` (a block named `scoring_hints`, below the `expected` block) for the code, and in `scoring_hints.csv` for people. They are not a score. They are side information the scorer needs: which photos must be flagged `partly`, the fragments of cut-off lines to set aside, and the answer-key items whose reading was uncertain, so a disagreement on those goes to a human check instead of being counted straight away.
