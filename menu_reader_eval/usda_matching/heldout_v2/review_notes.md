# Held-out set v2: review notes (evaluation-set development log)

Scored once on 2026-11-02 (`results_2026-11-02.{json,md}`), labels frozen before scoring (changelog has the hash). Verdicts are not changed after the fact. Reading of the disagreements, for Julius; accepted items would go into a v3 file.

Headline: 54 rows; 17 direct, 23 acceptable proxies, 5 label disagreements, 3 false matches, 6 unresolved. High-consequence rows: 41, with 3 false matches (7.3 %).

| Ingredient | Verdict as scored | Chosen record | Reading | For v3 (not applied) |
|---|---|---|---|---|
| mascarpone | false_match | Cheese spread, cream cheese base (169081), proxy | retained as a false match per Julius: a spread understates mascarpone's fat | none |
| 'nduja | false_match | Salami, Italian, pork (174603), proxy | a label gap, not a model error: the accepted-proxy pattern listed sausage and cured pork but not salami; spreadable cured pork sausage -> salami is a reasonable composition proxy | add `Salami` to the accepted proxies |
| foie gras (seared, fresh) | false_match | Pate de foie gras, canned (171100), proxy | the model chose the pâté as a *proxy* for fresh foie gras and said so; the label pattern's wording ("Pate, goose liver") does not match USDA's "Pate de foie gras". Preparation-dependent, as Julius said; whether canned smoked pâté is an acceptable proxy for seared fresh liver is his call | decide; at minimum fix the pattern wording |
| ghee | mislabelled | Butter, Clarified butter (ghee) (171314), direct | the model found the record named ghee; v2's label named 173412 only (frozen before the live check that revealed 171314). The model is right | add `^Butter, Clarified butter \(ghee\)` as direct |
| bresaola | mislabelled | Beef, cured, dried (170604), direct | air-dried cured beef; direct is defensible | accept direct |
| lardo | mislabelled | Lard (171401), direct | cured back fat vs rendered pork fat: nutritionally close, physically different; the label's "proxy" stands | none |
| dry vermouth | mislabelled | Alcoholic beverage, wine, dessert, dry (175112), direct | either label is fine for these nutrients | accept direct |
| soppressata | mislabelled | Salami, Italian, pork (174603), proxy | the model under-claimed (label said direct); harmless | none |
| prosciutto, speck | unresolved, `no_candidates` | — | the model's query returned no USDA candidates at all; v1 resolved both to cured ham with a different query. Query wording variance between runs | none; query writing could get a retry with the plain name (deterministic fallback exists only when the model's query is unusable, not when it returns nothing) |
| coppa, duck fat, squid ink, bone marrow | unresolved, declined | — | honest declines; USDA has no coppa or squid ink; duck fat and bone marrow were not among the candidates returned | none |

Model variance between v1 and v2 on identical rows: ghee 173412 -> 171314 (both ghee), bottarga di muggine caviar both times, pancetta and guanciale bacon both times; prosciutto and speck resolved in v1 and not in v2.

With the v3 label changes above applied, the same predictions would read 20 direct, 25 proxy, 2 mislabelled, 1 false match (mascarpone; 2 if the foie gras pâté proxy is rejected), 6 unresolved. Those are projections, not the scored result.
