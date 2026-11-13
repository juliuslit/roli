# Specification: Phase 2D, restaurant portion-size normalisation

Status: **built 2026-11-03 (Julius's go-ahead after Checkpoint 2C.1), internal only; stopped at Checkpoint 2D (`roli_agent/CHECKPOINT_2D.md`).** Sections 0-8 are the specification as written at Checkpoint 2C.1; section 9 records what was built and where it departs from the plan. Builds on `SPEC_2B_recipe_scenarios.md` (published scenarios) and `SPEC_2C_menu_adapted_scenarios.md` (menu-adapted pairs, internal). Every rule row is `proposed_unreviewed`; nothing reaches a user.

## 0. Purpose, in one paragraph

A published recipe says "serves 4" or "makes one 12-inch pizza"; a restaurant plate is neither. Phases 2B and 2C stop at the recipe's own serving count and say so. Phase 2D maps a scenario's **whole-recipe ingredient weights and totals** (which Phase 2A always keeps) onto a **plausible restaurant portion** of the same dish, with the uncertainty stated as a low/high range, the rule that produced it named, and the recipe-basis figures preserved untouched beside it. It does not change any nutrient value, any USDA record choice or the Phase 2A arithmetic: it changes only the *amount of the dish* the per-serving figure refers to.

## 1. What a restaurant portion is, and three ways to model it

For a dish made from a recipe with total ingredient mass `M_total` (grams, as declared to the calculator: raw weights where the recipe gives raw weights, D6) and total nutrients `N_total`, a restaurant serving is a fraction `f` of the recipe: `N_serving = f x N_total`. Everything in 2D is about estimating `f` honestly. Three models, from most to least direct:

| Model | `f` from | Needs | Fits |
|---|---|---|---|
| **P1 unit dish** | the recipe makes `k` units of the thing the restaurant serves one of (one pizza, one fillet, one salad bowl): `f = 1 / k` | the recipe's unit count (D15 yield text: "makes two 12-inch pizzas"), and a reviewed rule that the restaurant serves one unit | pizza, a whole fillet main, a plated starter made per person |
| **P2 plate weight** | a reviewed plate-weight range for the dish type, `W_low..W_high` grams of finished dish: `f = W / M_served`, where `M_served` is the recipe's served mass (raw mass adjusted for the recipe's own stated yield, or raw mass with the limitation stated) | plate-weight evidence per dish type (section 4) and a served-mass estimate per recipe | salads, crudo, pasta, grain bowls |
| **P3 key-ingredient weight** | the restaurant's portion of the dish's main ingredient (120-180 g raw fish per crudo, 170-225 g raw salmon per main) scales the whole recipe: `f = K / K_recipe`, where `K_recipe` is the recipe's weight of that ingredient | a reviewed key-ingredient range per dish type; the recipe's own key-ingredient weight (known when that line is resolved) | fish and meat mains, crudo, anything with one dominant ingredient |

Each model has a basis and a review status exactly like a 2C weights row. P1 is preferred when the yield text states units; P3 when the key ingredient is resolved and the dish has one; P2 otherwise. A dish can carry two models and report both; they are never averaged.

## 2. Interface

Input: a published scenario or a 2C adapted scenario (either bound) with `calculation.totals`, every line's `grams_in_recipe`, the recipe's `servings`, `yield_text`, `yield_source`, and the menu item (name, section, printed ingredients).

Output: a `PortionedScenario` added beside the input, never replacing it:

| Field | Meaning |
|---|---|
| `derived_from`, `input_bound` | the scenario (and, for an adapted pair, which bound) that was portioned |
| `servings_basis: "restaurant_model"` | distinguishes it from `"recipe"` |
| `portion_rule_id`, `model` (`P1`/`P2`/`P3`), `rule_basis`, `review_status` | the rule applied, its evidence and whether Julius approved it |
| `fraction_low`, `fraction_high` | `f` at both bounds, with the arithmetic shown (`W / M_served`, `K / K_recipe`, `1 / k`) |
| `per_portion_low`, `per_portion_high` | the Phase 2A calculator re-run with `servings = 1 / f` (so the calculator's own per-serving arithmetic, display rules and completeness logic apply unchanged), or `totals x f` with the scaling recorded; one method, named |
| `recipe_basis` | the input's per-serving figures and serving count, untouched |
| `limitations[]` | raw-weight basis (no cooking yield), served-mass estimate, model assumptions, anything else that applies |
| `uncertainty` | the ratio `fraction_high / fraction_low` and the absolute per-portion spread for both nutrients |
| `confidence` | `portion_published` (P1 from the page's own unit count), `portion_reviewed` (approved rule), `portion_proposed` (unapproved rule: internal only, never user-facing) |

Rules: `f` is never inferred from the recipe's serving count alone (a 12-serving pizza recipe does not mean a restaurant pizza is a twelfth of it); a `PortionedScenario` is never called a verified restaurant serving; the recipe basis stays reported; the 2C assumption sensitivity and the 2D portion sensitivity are reported side by side so the larger uncertainty is named (section 6).

## 3. Served mass and cooking yield (the honest limitation)

Phase 2A works on raw weights (D6) and never applies a cooking yield. For P2 the plate weight is a *cooked, dressed* weight, so `M_served` needs a yield estimate. Three options, in order of preference, each recorded on the output:

1. **The recipe's own stated finished yield** ("makes about 6 cups", "yield: 900 g") when D15 recovers one: `M_served` = that, with the unit converted only by a USDA measure of the finished food where one exists; otherwise unusable.
2. **No yield adjustment for dishes with no cooking loss** (crudo, salads, dressed raw vegetables): `M_served = M_total`, limitation "raw = served".
3. **A reviewed yield factor per dish type** (pizza dough loses ~10-15 % water in the oven; a roasted vegetable side loses more): a table row with a basis and a review status, used only in experimental mode until approved, exactly as 2C weights.

A missing yield never becomes 1.0 silently: the output says which option applied.

## 4. Evidence plan: real-world portion data

The models need numbers from outside recipe pages. Three evidence sources, collected into a reviewed table `roli_agent/recipes/portion_rules.csv` (same discipline as `assumed_weights.csv`: id, dish type, model, low, high, basis, source URL or weighing record, review status, approved_by):

1. **Own weighings** (strongest for this project): take-out or dine-in portions of the dish types on the test menu, weighed on a kitchen scale, with photos and the restaurant's menu description recorded. Target: 20 dishes across the five test dish types (starter crudo, leaf salad, tomato salad, pizza, fish main), at least 3 restaurants per type. Cost: the meals; no API spend. Each weighing becomes one row of evidence with its date.
2. **Published restaurant nutrition data**: US chains publish per-item nutrition and often serving weights (FDA menu-labelling). Useful for pizza (a 12-inch margherita from several chains: whole-pizza weight and per-slice weight) and salads; weak for crudo and composed plates. Each row cites the publisher and date.
3. **Culinary references for standard portions** (professional portioning guides, culinary-school texts, USDA Food Patterns serving sizes): 4-6 oz of raw fish per main, 2-3 oz for a starter crudo, and so on. Treated as *proposed* until confirmed by 1 or 2.

What counts as evidence for a key-ingredient range (P3) is kept separate from evidence for a plate weight (P2): a weighing of a crudo plate gives the plate weight; the fish weight on it is a separate estimate unless the restaurant states it.

## 5. Evaluation plan

1. **Hold-out by restaurant**: rules are proposed from the evidence of some restaurants and tested on the weighings of others; the error of `f` (predicted plate weight vs weighed) is reported per dish type as median and worst case, with n.
2. **Error budget**: for each test dish, three uncertainty sources are reported side by side on the same scale (grams of saturated fat and milligrams of cholesterol per portion): between-recipe spread (2B), assumption sensitivity (2C low vs high), portion sensitivity (2D low vs high). The largest is named in the output. If the portion uncertainty dominates, the ranking phase must say so.
3. **No user exposure** until, per dish type, the P1/P2/P3 error is characterised on at least 3 weighed portions from different restaurants and Julius has approved the rule rows.
4. **Regression tests**: the recipe-basis figures of every scenario are byte-identical before and after portioning; `f` is never derived from `servings` alone; a missing yield is reported, never 1.0; unapproved rules never reach a user-facing figure; the calculator source is untouched.

## 6. Worked example (numbers from the 2C.1 controlled run, for illustration only)

Taste of Home margherita, 6 recipe servings, complete in the adapted pair under the D24 variant at 15 % tolerance: saturated fat 25.65 g and cholesterol 90 mg for the whole recipe (one 12-inch-class pizza by the page's method). P1: the page's yield is "6 servings" of one pizza; a restaurant margherita is one pizza per person at Flour + Water's pizza section (a rule row that needs evidence: do they serve a 10-, 12- or 14-inch pizza, and is one pizza one portion?). With `k = 1`: `f = 1`, per portion 25.65 g / 90 mg; with `k = 2` (shared): 12.8 g / 45 mg. The 2D range would be stated as that factor-of-two spread until a weighing settles it; the recipe-basis figure (4.27 g / 15 mg per sixth) stays beside it, labelled as the page's own serving.

## 7. Dependencies on data quality (what must be true before 2D is worth building)

- At least some scenarios must be complete (published or adapted, under rules Julius approves); portioning an incomplete subtotal only scales a known subtotal. At Checkpoint 2C.1: 0 published complete; 1 adapted pair complete only under the D24 15 % variant; 4 pairs blocked only by weight rows awaiting review (section 6 of the checkpoint). So 2D's first useful inputs depend on decisions in Checkpoint 2C.1, not on more code.
- The key ingredient of each dish must be resolved for P3 (it is, for every crudo and salmon scenario: the fish lines are weight lines).
- Yield texts that state units (D15) exist for pizzas; for salads and crudo P2 or P3 applies.

## 8. Decisions needed from Julius before implementation

1. Which model is allowed to reach users first (recommendation: P1 for pizzas with a stated unit count, P3 for fish dishes with an approved key-ingredient range; P2 internal until weighings exist).
2. Whether to fund the own-weighing plan (20 dishes) or start with published chain data for pizza only.
3. The uncertainty wording a user sees when the portion range is wider than the recipe range.


## 9. As built (2026-11-03): `roli_agent/recipes/portions.py`, `portion_rules.csv`, `compare_dishes.py`, `blocked_evidence.csv`, `inference.py`

**Decisions from Julius that shaped the build** (his message after Checkpoint 2C.1): D20 revised to the median of comparable USDA whole-item sizes, flagged `assumed_size_median`, range and labels kept, garlic's exact clove weight unchanged, a whole lemon never combined with a wedge; no D24 at 15 %; instead a narrow cholesterol-zero inference for verified pure olive oil (rule I01) that keeps the Foundation saturated-fat value, records the absent field and labels the inferred zero with its evidence; P1 for pizzas, P3 for dishes with a dominant protein, experimental P2 for salads; recipe portions and restaurant portions kept apart; explicit low/high portion assumptions, never a verified serving size; nutrient-specific completeness preserved, a scaled subtotal never a total; Phase 2A arithmetic unchanged.

| Spec item | As built | Departure from the plan |
|---|---|---|
| Interface (section 2) | `PortionedScenario` beside the input, `servings_basis: "restaurant_model"`, `recipe_basis` carries the input's serving count and per-serving figures untouched, `fraction_low/high` with the arithmetic shown, `low`/`high` bounds each a full Phase 2A result re-run with `servings = 1 / f` (so the calculator's own completeness, display and reconciliation apply), `limitations[]`, `uncertainty`, `confidence` | per-portion figures come from the calculator re-run, not from scaled totals: a per-plate assumption (`quantity_basis: per_serving`) then counts once per plate while recipe lines scale with f |
| P1 unit dish | `unit_count_from_text`: k from the yield text ("One 12-inch pizza"), "makes two pizzas", a dough division ("divide the dough in half", "separate the dough into two equal-sized portions", "cut the dough into 2 pieces") or, failing those, a single shaped round ("roll it into a 13-inch circle"); a page that reserves dough "for another use" is refused; the serving count is never used. f = units_per_portion x area_ratio / k, with units_per_portion 0.5-1 (rule PR01) and the area ratio applied only when the page states its pizza's diameter (restaurant pie 12-13 in: 13 in verified for Flour + Water, 2019) | the area adjustment is new; it assumes equal thickness and topping density per square inch and is recorded as a limitation |
| P3 key ingredient | `key_ingredient_grams(head)`: the recipe's own lines whose USDA description starts with the key head ("fish"; "tomatoes" for the tomato starter), summed; menu-only lines (a bottarga proxied to a caviar record) are never key lines; unweighed key line -> not applicable. Rows PR02 fish main 113-227 g raw, PR03 crudo 45-110 g raw, PR06 tomato starter 120-250 g raw tomato | PR06 applies P3 to a vegetable dish with one dominant ingredient; the spec reserved P3 for proteins. Preferred over P2 when the key weight is known |
| P2 plate weight | f = W / M_served with M_served = the recipe's own raw mass (yield option 2, raw = served) and only when every recipe line is weighed; rows PR04 leaf salad 100-250 g, PR05 tomato starter 150-300 g | applies to 1 of 3 gem-salad recipes (the others have an unweighed line); the weakest evidence of the three models, as the spec said |
| Cooking yield (section 3) | option 2 only (salads); no yield table built | pizzas and fish mains use P1/P3, which need no served mass |
| Evidence (section 4) | `portion_rules.csv` rows cite what was read on 2026-11-03 (AVPN Disciplinare 2024 PDF; San Francisco Chronicle 2019 on the 13-inch Flour + Water pie; lacademie.com 8-10 oz; peelwithzeal.com 1-2 oz for crudo) and what was only seen in search summaries (Citarella 6-8 oz; side-salad database weights); no weighings yet | own weighings (the spec's strongest source) not started |
| Evaluation (section 5) | controlled recipes with stated weights first (`tests/test_recipes_2d.py`), then the frozen five-dish inputs (`scripts/replay_2d.py`) against drafted expectations (`eval/expectations_2d_v1.csv`, `scripts/evaluate_2d.py`); recipe-basis figures byte-identical; f never from servings; incomplete stays incomplete | hold-out by restaurant impossible without weighings |
| Comparison prototype (asked for after 2C.1) | `compare_dishes.py`: per scenario an interval per restaurant portion from the best evidence tier (source complete; complete with documented inferences; 2C pair complete at both bounds; pair bounded by external evidence for its missing lines; lower bound only); per dish the lowest low and, when at least one recipe is bounded, the highest bounded high, with the unbounded recipes named; pairwise `clear` / `overlapping` / `insufficient_evidence`, saturated fat first, cholesterol second; a lower bound alone never ranks; margins and assumption drivers reported | the external-evidence tier (`blocked_evidence.csv`) is new: non-USDA composition for bottarga, USDA sibling records for lines whose own record lacks a nutrient or a measure, amounts estimated as ceilings; it only ever raises an upper bound and never enters a total |
| Inference layer | `inference.py`: `assumed_size_median` lines and rule I01 collected per scenario and per pair bound; `InferredTotal` per nutrient = known subtotal + inferred contributions (0) when every remaining exclusion is inferred; `Scenario.basis` tells `source_reported` from `documented_inferences`; a scenario complete only through an inference is not user-facing eligible | rule I02 (vinegar cholesterol) is written, disabled, awaiting approval |
| Weights table | column `amount_basis` (per_plate / per_count_unit); rows W28b little gem per head, W20b shishito per plate, W03c shiso per plate added from the 2C.1 evidence as `proposed_from_evidence_2c1`, experimental only; W03b/W10/W20/W28 still blocked and never used; a usable row wins a key tie over a blocked one | 2C had entered per-plate amounts as whole-recipe amounts (understating them per recipe serving by the serving count); corrected and reported in Checkpoint 2D |

Not built: Telegram, the user interface, menu-wide ranking beyond the five-dish prototype, own weighings, any approval of a rule row.
