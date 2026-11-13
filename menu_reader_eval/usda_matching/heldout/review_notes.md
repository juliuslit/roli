# Held-out set: review notes (evaluation-set development log)

Scored once on 2026-11-02 with the labels frozen beforehand (hash in `../heldout_README.md`). The verdicts in
`results_2026-11-02.{json,md}` are **not** changed after seeing the predictions. What follows is the agent's reading
of the disagreements, for Julius's review; any label change would be a new version of the set, scored again.

| Ingredient | Verdict as scored | Chosen record | Reading | Suggested label change (not applied) |
|---|---|---|---|---|
| mascarpone | false_match | Cheese spread, cream cheese base (169081), labelled proxy | A cream-cheese *spread* is a weaker stand-in than cream cheese or heavy cream (lower fat than mascarpone, which is about 44 % fat). A real proxy error worth keeping as a false match: the model chose a less fatty food for a very fatty one, which understates saturated fat. | none; keep as false match |
| foie gras | false_match | Pate de foie gras, canned (goose liver pate), smoked (171100), labelled direct | The label pattern was written as "Pate, goose liver" and USDA's wording differs. The record is foie gras pâté, not fresh foie gras; "direct" is defensible for a pâté dish, a proxy for seared foie gras. A label-wording error on my side. | accept `^Pate de foie gras` as direct; counts as evaluation-set development |
| gorgonzola | mislabelled | Cheese, blue (172175), labelled direct | USDA's blue cheese covers gorgonzola; calling it direct is reasonable. The label said proxy. | accept as direct |
| ghee | mislabelled | Butter oil, anhydrous (173412), labelled direct | Anhydrous butter oil is ghee; direct is right. The label said proxy. | accept as direct |
| duck fat | unresolved | model declined | The model's query was "fat duck"; USDA returned 10 candidates and the model found no rendered duck fat among them (its reason is in the JSON). Honest unresolved rather than a wrong fat. Whether an SR Legacy "Fat, duck" record exists and why the search did not return it is open. | none |
| squid ink, bone marrow | unresolved | model declined | no suitable USDA record; the honest answer | none |

Net reading: 2 of the 2 "false matches" are one real proxy error (mascarpone) and one label-wording error (foie gras);
both "mislabelled" rows are correct direct matches that my labels called proxies. With the label corrections above
the set would read 18 direct, 18 proxy, 1 false match (2.5 %), 3 unresolved; **those corrected figures are not the
scored result and are shown only as what a re-scored v2 set would give.**
