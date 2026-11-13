# Held-out set v3: review notes

Scored once on 2026-11-02 (`results_2026-11-02.{json,md}`), labels frozen (hash in `../heldout_CHANGELOG.md`), verdicts not changed afterwards.

Headline: 54 rows; 18 direct, 26 acceptable proxies, 3 label disagreements, 2 false matches, 5 unresolved. High-consequence rows: 41, with 2 false matches (4.9 %); both are the ones Julius decided to keep as false matches ('nduja -> salami, mascarpone -> cream-cheese spread).

| Ingredient | Verdict | Reading |
|---|---|---|
| 'nduja, mascarpone | false_match | retained by decision; no reviewed proxy exists |
| bresaola -> Beef, cured, dried (direct) | mislabelled | label kept as proxy after reviewing the exact description; the model over-claims "direct" |
| gorgonzola -> Cheese, blue (direct) | mislabelled | label kept as proxy by decision; the model over-claims |
| soppressata -> Salami (proxy) | mislabelled | the model under-claims (label expects direct); harmless |
| duck fat, squid ink, bone marrow, coppa | unresolved | declined; no suitable USDA candidates |
| manchego | unresolved | declined this run (v2 run proxied it to romano): model variance |
| ghee | direct | the model chose the record named ghee (171314), accepted in v3 |
| dry vermouth | direct | "wine, dessert, dry", accepted as direct in v3 |

Plain-name retry: see the row list printed in the checkpoint; the retry fires only when the model's query returns no USDA candidates.
