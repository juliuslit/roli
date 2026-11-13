# Experiment A - Tiling, and "send as file"

Written 2026-10-30, before any run. Round two, workflow experiments. Models: the best closed and the best open model chosen after v5 (to be filled in). Not started until Julius chooses them.

## Question
Dense menus (photos 10 and 17) and small-print menus (13, 19) are where every model stops early or reads unevenly. Does the model read more when it sees less at a time, at higher effective resolution? And does the 1280-pixel Telegram copy itself cost items, compared with the original photo?

## Two variants, run separately
**A1 Tiling.** Each photo is cut into four overlapping quarters (top-left, top-right, bottom-left, bottom-right), each quarter covering 60 % of the width and 60 % of the height, so every line near the middle appears in two tiles. Each tile is sent with prompt v5 as its own call. The four answers are merged into one list by name, using the scorer's own pairing rules (interpretations 1-16: clean names, 90 % similarity, joined text, tie-break by section then price). An item seen in two tiles is kept once; where the two copies differ, the copy with the fuller description wins and the price is kept only if the copies agree, otherwise left blank with confidence "low". `readable` is "partly" if any tile said so; `problems` is the tiles' problems joined. Only the merged JSON goes to the scorer.

**A2 Send as file.** The original full-size photo from `menu_test_set/` (not the `telegram_1280/` copy), one call with prompt v5, no tiling. Same scoring. This tells us whether the Telegram downscale is the limit; if it is, a "send as file" instruction to users is a cheaper fix than tiling.

## Procedure
1. Smoke on photos 10, 13 and 17, once each, both variants, both models: compare items found with the single-read v5 result for the same photo.
2. If a variant gains on at least two of the three photos without adding invented items, run it on all 25 photos, twice, as a normal 50-answer batch (200 tile calls for A1).
3. If it does not help on the three photos, stop and record that.

## What is scored
The merged (or single full-size) answer, under the current rules, in its own results folder: `results/expA1_<stamp>_<model>_v5_t0/` and `results/expA2_...`, with the per-tile raw answers kept under `tiles/` for inspection. The comparison is against that model's v5 single-read batch on the same photos.

## Decision
A variant is worth keeping if dishes found rises by 3 points or more on average, or lifts the worst photo above 80 %, with invented not rising by more than 2 per run and cost per photo under four times the single read. Report found, invented, garbled, cut-off, prices, descriptions, speed and cost beside the single read.

## Cost and time, estimated
A1: four calls per photo, each with a smaller image and a shorter answer; about 2.5 times the single-read cost (Gemini about 3 c a photo, Qwen3.6 about 0.9 c) and 2 to 3 times the time. A2: about 1.3 times the single-read input tokens for the larger image; same output.

## Risks
- Tiling splits sections: an item's section heading may sit in another tile, so `section` will often be wrong or empty. Sections are not scored this round, but the cholesterol step may want them.
- Prices in a right-hand column can be cut from their names by the tile edge; the 60 % overlap is meant to catch that, and the smoke on photo 10 will show whether it does.
- Merging by name can pair two different items with the same name across tiles (photo 12 has two "Tuna Mayo"); the section-then-price tie-break handles this when sections survive.
- A2 depends on the host's own image limits: Anthropic downsizes above about 1.15 megapixels, Google tiles at 768 pixels, so "full size" may be rescaled anyway. Input token counts per call will show what arrived.
