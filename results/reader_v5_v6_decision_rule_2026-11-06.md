# Reader v5 against v6: how "no worse" is read (written 2026-11-06, before either batch ran)

Spec: `roli_agent/SPEC_3_mvp.md` 12.12.3. Roli switches to v6 only if v6 is no worse than v5 on any pass bar; otherwise report and keep v5.

- Both prompts run now, same day, same model (`google/gemini-3.8-flash`), same harness: `code/full_run.py`, 25 photos, each sent twice, temperature 0. The 2026-10-30 v5 batch is not used as the baseline.
- The verdict uses the `as_written` block of each `verdict.txt`, scored under interpretations 1-18. Photo 17 stays in.
- "No worse" is applied strictly, with no tolerance: on every pass bar the v6 figure, at the precision the harness prints, must be equal to or better than the v5 figure. A bar that both prompts fail still counts.
- Bars compared: dishes found average, no photo below 80 % (the worst photo), invented (each run), cut-off lines listed (each run), prices, descriptions, format, partly photos caught (each run), false alarms (each run), speed.
- The answer key is not changed for this decision.

Known before running: the key lists "Watermelon, fetta, mint, almond, salsa verde salad" on photo 23 as a dish of its own, and a smoke of v6 on photo 23 attached that line to the four fish, so it scored 10 of 11 there. The batches are scored as the key stands.
