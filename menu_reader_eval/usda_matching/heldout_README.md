# Held-out USDA matching set

- File: `heldout_set.csv` (41 rows). Focus: consequential proxies (bottarga, mirin, cured meats, cheeses, fats, offal) plus direct records that look like proxies.
- Labels written by the developer on 2026-11-02 **before** any model prediction on these rows, as expected-description and accepted-proxy regular expressions over USDA descriptions. Independent review by Julius: **pending** (the labels are the agent's judgement of USDA naming and nutritional closeness; uncertainties are stated in the notes column).
- Frozen: SHA-256 `cc594a614aef2a7e77a8b40ca865ebeff38de54fdea2279b35dd9a95216a2965` at the time of the first and only scoring run. The labels are not edited after predictions. Any disagreement found while reading the results is recorded under "evaluation-set development" in `heldout/review_notes.md`, with the original verdict kept.
- Scoring: `.venv/bin/python -m roli_agent.scripts.score_matching --set menu_reader_eval/usda_matching/heldout_set.csv --out menu_reader_eval/usda_matching/heldout`, a fresh empty match cache, so every row is decided live.
