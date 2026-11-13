# Roli

A chatbot for people who watch their cholesterol and saturated-fat intake. The user sends a photo of a restaurant menu; Roli reads the menu, estimates saturated fat and cholesterol per dish, and recommends the lightest options. Every number comes from code that reads measured data (USDA FoodData Central, published chain figures); the language model reads the photo and sorts dishes, it never writes a nutrient value.

This repository holds the first build and everything it rests on. A second build, the look-alike estimator, lives in its own repository: [roli2](https://github.com/juliuslit/roli2). The two were built side by side and compared on the same menus.

## What is here

| folder | what |
|---|---|
| `code/` | the menu-reader evaluation harness: photo + prompt -> one model through OpenRouter -> scored answer (round one compared six models over five prompts) |
| `menu_reader_eval/` | the test design: prompts v1-v6, the answer format, expected answers per photo, scoring rules, relevance and USDA-matching test sets |
| `menu_test_set/` | 25 menu photos (own photos and Wikimedia Commons; licences in `manifest.csv`), the 1,001-item answer key, Telegram-size copies |
| `nutrition_service/` | the USDA nutrition library `roli_nutrition`: one USDA record in, validated saturated fat and cholesterol out; its own tests on saved real replies; a thin MCP wrapper |
| `roli_agent/` | the first application: a LangGraph pipeline that finds recipes for each dish, parses ingredient lines, matches them to USDA records, sizes the plate and ranks the dishes; the local web prototype; the checkpoint write-ups 1E through 3K |
| `data/` | chain nutrition sheets transcribed by hand (with sources), MenuStat (NYC Open Data), USDA FNDDS 2021-2023 |
| `results/` | round one of the menu-reader comparison: raw model answers and scores per photo, per model, per prompt |

## How the work is recorded

Each stage has a specification (`SPEC*.md`) written before the build and a checkpoint (`CHECKPOINT_*.md`) written after it, with the pass bars set in advance, what was measured, what missed, and the open decisions. Evaluation reports sit in `roli_agent/eval/` and `menu_reader_eval/`. Nothing in a checkpoint is tuned after the fact: a bar that was missed is reported as missed.

## Running

```
/opt/anaconda3/bin/python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env            # OPENROUTER_API_KEY, USDA_FDC_API_KEY, TAVILY_API_KEY (create the file; it is never committed)
.venv/bin/python -m pytest                                  # the agent's tests (offline)
cd nutrition_service && /opt/anaconda3/bin/python3.13 -m venv .venv && .venv/bin/pip install -e ".[dev,mcp]" && .venv/bin/python -m pytest
./roli_local.sh start                                       # the local web prototype at http://127.0.0.1:8008/
```

The saved runs, caches and virtual environments are not committed; the spend ledger (`roli_agent/runs/spend_ledger.jsonl`) is, as the record of what each experiment cost.

## Data and licences

Menu photos: own photos and Wikimedia Commons files under the licences listed in `menu_test_set/manifest.csv` (CC BY and CC BY-SA require attribution). MenuStat: NYC Open Data. USDA FoodData Central and FNDDS: public domain. Chain nutrition sheets: the chains' own published figures, transcribed with the source URL on every row.
