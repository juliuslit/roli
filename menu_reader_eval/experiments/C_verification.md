# Experiment C - Verification pass on low-confidence items

Written 2026-10-30, before any run. Round two, workflow experiments. Models: the best closed and the best open model chosen after v5. Not started until Julius chooses them, and after B.

## Question
Prompt v5 tells the model to include faint or blurred lines and mark them confidence "low". That should raise found and may raise invented. Can a cheap second call remove the invented ones without losing the real ones? The second call asks only one thing per item: is this exact name printed on the menu?

## Procedure
1. Take the model's v5 answer for a photo (from its v5 batch, or a fresh read if B's merged answer is used as the input instead; this is decided when the experiment starts and recorded).
2. For every item with confidence "low", one small call: the same photo, and the text "Is this exact name printed on the menu: "<name>"? Answer yes or no and nothing else." Same model, temperature 0, cap 5 tokens, no reasoning.
3. Items answered "no" are dropped; items answered "yes" are kept as they were. Items with confidence "high" or "medium" are not checked.
4. Scored twice: the answer before the pass and the answer after it, so the pass's own effect is visible.

## What is scored and compared
Both versions under the current rules, in `results/expC_<stamp>_<model>_v5_t0/` with `before/` and `after/` score files and the question-answer log per item (`checks.csv`: photo, item name, answer, seconds, cost). Reported: found, invented, garbled and prices before and after; how many items were checked, dropped and wrongly dropped (a dropped item that the key has); cost of the checks per photo.

## Decision
Worth keeping if invented falls by at least half with found falling by less than 1 point. If the model says "no" to real items, the pass is harmful and the result is recorded as such. The number of "low" items per photo in the v5 batches sets the cost: at roughly 5 to 20 checks a photo and a few hundred input tokens each (the photo dominates), expect 1 to 4 c a photo on Gemini and under 1 c on Qwen3.6, plus 1 to 3 s per check in sequence.

## Risks
- The check sends the photo again for every item, so its cost scales with the number of "low" items; v5 may produce many on dense photos. If a photo has more than 25 low items, check only the first 25 and report the rest unchecked.
- A yes/no question to the same model that produced the item may just agree with itself. Running the check on the other chosen model is a variant worth one smoke if the same-model check changes nothing.
- "Exact name" is strict: the model may say "no" to its own misspelling of a real item, which is a garbled item lost rather than an invented one; both counts are reported so this is visible.
