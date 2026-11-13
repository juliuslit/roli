# Held-out set: versions

## v1: `heldout_set.csv` (frozen, 40 rows; results in `heldout/`)
Unchanged. Its labels and its scored results are preserved as they were.

## v2: `heldout_set_v2.csv` (54 rows; SHA-256 `aa2019df73f2a61751cd8ee42299dd4f9c5d520862b34e9ff8c7cdea02425f38` at creation, 2026-11-02; results in `heldout_v2/`)

Changes to existing rows (Julius's provisional assessment, 2026-11-02, applied only where he said so):

| Row | Change | Justification |
|---|---|---|
| mascarpone | none | retained as a false match: a cream-cheese *spread* understates fat for mascarpone |
| ghee | label changed to **direct** `^Butter oil, anhydrous` | record verified live on 2026-11-02 through the nutrition service: USDA 173412 "Butter oil, anhydrous" (SR Legacy) reports 61.924 g saturated fat and 256 mg cholesterol per 100 g (the two nutrients the service reads); anhydrous butter oil is clarified, dehydrated butter, i.e. ghee. The same live search also returned USDA 171314 "Butter, Clarified butter (ghee)", a record named ghee outright, which the v2 label does not list because v2 was frozen before this check; it belongs in v3 as the first direct pattern. The old proxy pattern is kept as the accepted proxy |
| gorgonzola | none | "Cheese, blue" stays an accepted proxy, not a direct match; a model that labels it direct scores "mislabelled" |
| foie gras | wording made explicit: "foie gras (seared, fresh)"; label unchanged | preparation-dependent: fresh foie gras and canned pâté are different foods; a new row "pâté de foie gras (canned)" accepts the canned pâté record as direct |

Note on the hash: after scoring had started, the free-text *notes* cell of the ghee row was corrected to cite only the values actually verified (61.924 g saturated fat, 256 mg cholesterol) and to mention USDA 171314; no pattern or label changed. SHA-256 after that edit: `209d854949f7b663791fc8d04ec772569c46c392bea1414d0e61c716905530bb`. The scoring run used the file at creation.

Additions (14 rows): more consequential proxies for the stringent review: cured tuna roe; cooking wines (marsala, shaoxing, dry vermouth); cured meats (coppa, soppressata, mortadella, lardons); specialty cheeses (pecorino toscano, asiago, scamorza, robiola, manchego); the canned pâté row. Every row now carries a `consequence` column (high / medium / low) by its effect on saturated fat and cholesterol; the scorer reports the false-match rate among high-consequence rows separately.

Rule unchanged: labels are written before scoring and not edited afterwards; disagreements go to a review-notes file and, if accepted, into the next version.

## v3: `heldout_set_v3.csv` (54 rows; SHA-256 `de0a00745c0d11bbd5b0c2f6ed722f99b35650cf7f9b9cbb09780dc5d0ca03a1` at creation, 2026-11-02; results in `heldout_v3/`)

v1 and v2 and their results are unchanged. Selective revision per Julius's review of the v2 reading:

| Row | Change | Justification |
|---|---|---|
| ghee | expected (direct) pattern now also accepts `Butter, Clarified butter (ghee)` | USDA 171314 verified live through the nutrition service: 60.0 g saturated fat, 300 mg cholesterol per 100 g; the record is named ghee |
| bresaola | no label change (proxy) | reviewed against the exact description "Beef, cured, dried" (170604: 0.95 g, 79 mg per 100 g): American cured dried beef, the same process class but not the Italian product; an acceptable proxy, not direct |
| dry vermouth | expected (direct) pattern `^Alcoholic beverage, wine, dessert, dry`; other wines stay accepted proxies | reviewed against "Alcoholic beverage, wine, dessert, dry" (175112: 0 g, 0 mg): dry vermouth is a dry fortified wine, which is what the record describes |
| 'nduja | no change | generic salami not approved as an acceptable nutritional proxy; stays a false match until a reviewed proxy exists |
| foie gras (seared, fresh) | no change | canned smoked pâté rejected as a substitute for fresh seared foie gras |

Pipeline change scored with v3 (not a label change): one bounded plain-name retry when the model's query returns no USDA candidates (`retried_with_plain_name` on the decision; the same candidate-ID and preparation guards apply to the retried candidates).
