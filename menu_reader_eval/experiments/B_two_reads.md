# Experiment B - Two reads, merged

Written 2026-10-30, before any run. Round two, workflow experiments. Runs first, on Gemini 3.8 Flash; then on the chosen open model. Not started until Julius chooses the two models.

## Question
Gemini's two v2 batches showed that on the hard photos the variation between identical calls is in how far the model reads, not in what it invents: photo 13 ranged 50 to 96 % found and photo 17 57 to 98 % across four runs, with nothing invented on 13 and one to three invented items on 17. If two reads of the same photo miss different items, merging them should recover most of the gap at twice the cost. Does it, and what does it do to invented?

## Procedure
1. Each photo is sent twice with prompt v5, same settings as the model's v5 batch (temperature 0, cap 24,000, same host and reasoning setting). The two calls are sequential.
2. The two answers are merged by name with the scorer's pairing rules (clean names, 90 % similarity, joined text, tie-break by section then price):
   - An item present in both reads is kept once, as read, with the fuller description. If the two prices agree it is kept; if they differ, the price is left blank and confidence set to "low". Confidence is the lower of the two when they agree on price.
   - An item present in one read only is kept, with confidence set to "low".
   - `readable` is the more cautious of the two ("no" over "partly" over "yes"); `problems` joins both texts.
3. Only the merged JSON is scored. The merged answer counts as one "answer" per photo; to keep the two-runs rule, the whole procedure is done twice per photo, so 100 model calls make 50 scored answers.

## What is scored and compared
The merged answers, under the current rules, in `results/expB_<stamp>_<model>_v5_t0/`, with both raw reads kept under `reads/`. Compared with the model's v5 single-read batch: dishes found (average and worst photo), invented, garbled, cut-off listed, prices, descriptions, partly caught, false alarms, and cost per scored answer. Also reported: how many items came from one read only, and how many prices were blanked by disagreement, per photo.

## Decision
Worth keeping if found rises and the worst photo improves without invented rising by more than the single read's own run-to-run spread. The expected cost is exactly two reads per photo plus nothing (the merge is local), so about 2.5 c a photo on Gemini and 0.7 c on Qwen3.6 at Parasail; time is two calls in sequence, about 35 s on Gemini. The "one read only -> low" rule also feeds the app's design: those are the items it would ask the user to confirm.

## Risks
- Invented items from either read survive the merge (as "low"), so invented can only rise. The question is by how much, and whether the confidence flag is enough for the app to handle them.
- Two reads that garble the same name differently produce two items; the 90 % rule catches small spelling differences, not large ones.
- On Google, temperature 0 is not repeatable, which is what makes this experiment useful; on a host where it is repeatable, two reads would be identical and the merge would change nothing. Check the two reads differ before drawing conclusions.
