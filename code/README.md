# code/ - the scripts that run the menu reader test

Read the approved documents in `../menu_reader_eval/` first; nothing here changes them.

| file | what it does |
|---|---|
| `config.py` | Folder paths, dataset name, and the keys from `../.env`. |
| `scorers.py` | One function per score in `scoring_rules.md`, the name-matching test, and the human check list. `score_answer()` runs all of them on one answer. |
| `menu_reader.py` | The target function: photo + prompt file -> model via OpenRouter -> raw answer, with time, tokens, cost. |
| `upload_dataset.py` | Sends the 25 examples (photo, expected answer, scoring hints) to the LangSmith dataset `roli-menu-reader`. |
| `smoke_test.py` | A few photos through one model, once each. Prints raw answers and scores; saves them under `../results/`. |
| `full_run.py` | The real test: one model x one prompt over the LangSmith dataset, every photo twice, one call at a time. One bundled scorer sends all scores to LangSmith as one feedback set per call. Saves raw answers, scores, check list, summary and a verdict (rules as written, and with photo 17 set aside) under `../results/full_*`. |
| `compare_runs.py` | One table over every `results/smoke_*` run. |
| `rescore.py` | Re-scores saved raw answers under the current rules into a sibling `*_rescored_<date>_<rules tag>/` folder; no model calls. |
| `splice_rerun.py` | Folds a re-run of a few photos (e.g. photo 17 at a higher cap) into an existing results folder and records it under `reruns` in its summary.json. |

## Running

```
cd <this repo>
.venv/bin/python code/upload_dataset.py --dry-run        # check the 25 examples, no upload
.venv/bin/python code/upload_dataset.py                  # upload to LangSmith (first time)
.venv/bin/python code/upload_dataset.py --update         # after a key change: refresh examples in place, experiments kept
.venv/bin/python code/smoke_test.py --model qwen/qwen3.6-35b-a3b
.venv/bin/python code/full_run.py --model anthropic/claude-haiku-5.5 --prompt v2     # 25 photos x 2, ~90 min for Haiku
caffeinate -i -s .venv/bin/python code/full_run.py ...                                # keeps the Mac awake for the run
```

The scorers can be exercised with no keys and no network: see the self-test commands in the
session notes, or run `score_answer(expected, hints, raw_text)` on any saved raw answer.

## Settings that are not in the approved documents (decisions to confirm)

- Temperature 0 (`TEMPERATURE`), set 2026-10-28. Until then it was the host default of 1.0, and
  Haiku found 81 dishes on photo 06 in one run and 38 in the next with the same prompt. Runs in
  `results/` stamped 2026-10-28_0824 and _2045 were made at 1.0; later ones at 0.
- The answer is capped at 24,000 tokens (`MAX_ANSWER_TOKENS`; 32,000 until 2026-10-29 morning, 16,000 during
  that day's runs, 24,000 from the evening after Qwen3.6 ran out of room on photo 17 while writing sensible items).
  `finish_reason = "length"` in the results means the cap was hit. Each summary.json records the cap it ran under.
  The cap is enforced by every host, and OpenRouter skips hosts whose own limit is below it (DeepInfra's 16,384
  for Qwen3-VL), so it also steers routing.
- Each call has a 300 s deadline (`DEADLINE_SECONDS`). The answer is streamed; at the deadline the
  connection is closed, what arrived is saved with `finish_reason = "deadline"` and scored as it is.
  Closing the connection stops generation and billing at hosts that support cancellation (DeepInfra,
  Anthropic), not at Google. The older `timeout=180` is only the longest allowed silence on the line:
  OpenRouter sends keep-alive bytes every 3 s, so it never stopped a long call (found 2026-10-29).
- Provider order per model (`PROVIDER_ORDER_BY_MODEL`), with fallback to any no-training provider
  (`data_collection: deny`): Claude models to Anthropic's own endpoint; Qwen3.6 to Parasail then DeepInfra
  (DeepInfra ran it at 20-30 output tokens/s on 2026-10-29, Parasail at ~100, same price); Qwen3-VL to Novita
  then SiliconFlow (Parasail does not serve it; DeepInfra's output limit is below our cap). `full_run.py
  --pause-on-host siliconflow:5` stops a run once a sixth call lands there. Default for anything else: DeepInfra then Parasail. Every
  summary.json records the serving host per call and the median output tokens/s per host.
- Hidden reasoning is off (`THINKING = False`) except where the endpoint refuses that: Sonnet 5.5 at Anthropic
  answers "Reasoning is mandatory for this endpoint", so it runs at the lowest allowed effort, `minimal`, with the
  reasoning text excluded (`REASONING_BY_MODEL`). Reasoning tokens are billed as output and are logged per call
  (`reasoning_tokens`) and totalled in each summary. Found 2026-10-30.
