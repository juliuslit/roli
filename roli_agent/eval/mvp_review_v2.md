# Human review of the final recommendations, v2 (local-testing milestone, 2026-11-04; drafted for Julius)

Drafted from the final runs (`20261104-040940` Flour + Water, `-041137` Greyhound, `-041334` Zuni Café, `-041530` seafood chalkboard).
Argued from the ingredients the recipes name, the USDA values of the dominant ingredients and the menu's own words; the agent's expected ranges
are not used as proof. **Awaiting Julius's review.** Close pairs and specialty ingredients first.

## Flour + Water (19 items, 17 candidates, 14 tried, 5 ranked)

Shown: *1) Heirloom Tomatoes 0.4-2.4 g; 2) Bluefin Crudo 0.5-4.3 g; 3) Little Gem Lettuces 4.4-8.6 g; tomatoes and crudo a toss-up; tomatoes have no cholesterol.*

| Case | What the prototype did | Review | Verdict |
|---|---|---|---|
| Tomatoes vs crudo (close pair) | tomatoes first by upper bound (2.4 vs 4.3 g), called a toss-up | Both are lean plates; the crudo's new upper end (4.3 g, up from 1.6 g in Phase 3) comes from a recipe with an olive-oil drizzle (W09, 13.5 g per plate) that is now bounded instead of open; the order is not knowable from this evidence and the text says so | plausible, correctly hedged |
| Crudo cholesterol 17-115 mg | bottarga (external evidence, 10 g at 722 mg/100 g) named as the driver when the crudo is the top pick; this run it is second, so only the table shows it | The bottarga sentence appears when the crudo leads (verified on the final Zuni-style render and in tests); when it is second the table still shows 17-115 mg and the diagnostics the source | accurate; wording rule works |
| Little gem third (4.4-8.6 g) | 60 % assumptions (pecorino 5-15 g, tahini 15-30 g); close call against the salmon (4.5-14.9 g) | A lighter dressing puts it near the tomatoes, a heavier one near the salmon; "probably lower, overlapping" is right | plausible, assumption-driven |
| King salmon fourth (4.5-14.9 g) | 4 recipes bounded, f 0.12-0.50 against 227 g raw fish | Raw king salmon is about 2.5 g saturated fat per 100 g: 227 g gives 5-6 g before oil; the range brackets that | plausible |
| Margherita fifth (8.9-27.6 g) | one whole 12-13 in pizza with 85-170 g mozzarella (W06) | 12-24 g from the cheese alone; well supported against everything above it | plausible |
| Salsiccia bianca | Phase 3: unbounded; pass 2 today: **47-111 g per plate (wrong)**; final: unranked, "no scenario could be portioned" | The 47-111 g came from a deep-dish sausage pizza recipe the relevance gate let through, with a second cheese added per plate (W32). Fixed in code: deep-dish, pan, sheet and stuffed pizzas are not the thin round unit (P1 refuses them); a menu cheese on a recipe that already has a cheese line may replace it (low 0 g). The other three recipes state no unit count, so the dish stays unranked | **material error caught and fixed; now an honest refusal** |
| 9 of 14 not estimated | pasta courses, pork chop, two pizzas, pole beans | Pole beans: bacon now resolves (the "unprepared" fix) but "miso bagna cauda" has no row. Pork chop: one recipe is bounded (7.9-16.4 g) but a double-cut-chop recipe's lower bound (150 g per portion, a recipe whose chop weight the parser could not read, so f = 1.5) exceeds it and the rule withdraws the bound; the rule is right, the recipe is an outlier. Pastas: filled pasta, mussels escabeche, lamb merguez ragu, chanterelles (USDA reports no saturated fat) stay open | honest refusals; one outlier-recipe effect worth a later look |

## The Greyhound (38 items, 14 candidates, 14 tried, 1 ranked)

Shown: *Padron Peppers 1.2-3.0 g, "the only dish I could estimate, so this is one figure, not a ranking"; no cholesterol.*

| Case | Review | Verdict |
|---|---|---|
| Padron peppers 1.2-3.0 g | Blistered peppers in oil; believable | plausible |
| 13 of 14 unranked | Structural: deep-frying oil (fish and chips, schnitzel, squid, croquettes, arancini, scotch egg, crackling), side dishes written as menu words with no row ("Koffmann's hand cut chips", "vine tomatoes", "Bramley apple sauce"), anchovy-in-oil refused by the Phase 2A rule that an as-used state is never accepted for a flesh food, and recipes with no portionable mass. The course-balanced selection now reaches the mains (sea bass, lamb sausages, carbonara, sirloin) that menu order left out in Phase 3; they are open for the same structural reasons, not for the seasoning gap W29 closed | correct refusals; coverage is the limit on pub menus |

## Zuni Café (71 items, 13 candidates, 13 tried, 4 ranked)

Shown (final wording): *1) Wood fire-roasted tomato and eggplant soup 0.7-4.7 g; 2) Zuni Caesar salad 2.3-5.7 g; 3) Spaghetti with Gulf shrimp 1.9-12 g; ranges overlap, toss-up; the spaghetti may carry up to 376 mg cholesterol.*

| Case | Review | Verdict |
|---|---|---|
| Soup first (0.7-4.7 g) | A vegetable soup; the upper end is parmesan shavings (assumed 5-15 g). Right direction | plausible |
| Caesar second (2.3-5.7 g, 60 % assumptions) | Zuni's Caesar is egg, anchovy, parmesan, oil; the range rests on the egg count (G5: 1 or 2 eggs) and a P2 plate of 100-250 g over a recipe of about 1.1 kg (f 0.09-0.22). A main-sized Caesar at 300 g would sit above 5.7 g; the leaf-salad plate rule is the lever | plausible but the portion rule may undersize a main-course salad |
| Spaghetti third (1.9-12 g; 4-376 mg cholesterol) | Three recipes: a garlic-butter shrimp pasta (7.7-11.9 g) and two lighter ones; the Zuni dish names brandy and Espelette, no butter. The wide range is recipe choice. Cholesterol 181-376 mg from the shrimp at the bounded recipes (one recipe leaves it at 4 mg because its shrimp line could not be weighed) is the single most important fact for a cholesterol-watcher on this menu; the final wording now says "may carry up to 376 mg" (added after this run; the saved run text lacks it) | plausible; cholesterol notice needed and added |
| Ribeye fourth (11-28 g), well supported | 140-280 g of ribeye; direction certain | plausible |
| Pizza with soppressata unbounded | flour by the cup without a usable measure on the matched record; the new W32/W38 rows did not get a chance | honest; a flour measure gap, not a rule gap |
| Chicken for two unbounded | now typed as a meat main (fixed), but the bread salad's bread and salad lines are open | honest |

## Seafood chalkboard (9 items read, 7 candidates, 7 tried, 4 ranked)

Shown: *1) Ocean Trout / Tuna Poke Salad 2.0-7.3 g; 2) Crudo of Swordfish 2.5-15 g; 3) Snapper 4.7-16 g; toss-up; poke cholesterol 18-43 mg.*

| Case | Review | Verdict |
|---|---|---|
| Crumbed whiting | pass 2 today: **first at 0.8-1.8 g (wrong)**: the breaded-whiting recipe listed fish, flour, egg and crumbs and fried them in oil named only in the method, so the list was "complete". Fixed: a recipe whose method or menu says fried/crumbed/battered/crispy and whose list has no oil, butter or fat gets an open "frying fat" line that nothing may fill; final: unranked | **material error caught and fixed** |
| Poke salad first (2.0-7.3 g) | Raw tuna, sesame, soy; the James Beard recipe with f 0.45-1.10 (a 100-250 g plate against a 227 g recipe). Lean, plausible | plausible |
| Swordfish crudo second (2.5-15 g) | The upper end is "fetta lemon pangrattato" read as 45 g of feta (6 g saturated fat) plus a whole-lemon size spread; a crumb topping with feta probably carries less cheese than that. Flagged assumption-driven, so a toss-up | plausible direction, high end generous |
| Snapper third, ocean trout fourth | Four fish mains share the menu's "watermelon, fetta, mint almond, salsa verde": feta 15-45 g and salsa verde 20-45 g dominate the upper ends (about 10 g together); the fish themselves add 2-6 g | plausible; the shared side decides, as it should |
| Menu read differed between passes | pass 1 read 10 items including the watermelon salad as a dish of its own and ranked it first; later reads gave 9 items without it. Temperature 0 does not make the reader deterministic on a chalkboard photo | variability to expect |

## What this review says about the prototype

1. Where the dominant ingredient decides (soup vs ribeye, salad vs margherita) the order is right and labelled well supported.
2. Where lean plates compete, the text now says toss-up or tentative and names the assumption or evidence that drives the number (bottarga, pecorino, eggs, feta).
3. Two material errors surfaced only because the live runs were read critically, not from test success: a deep-dish recipe treated as a Neapolitan unit, and a fried recipe with no fat line treated as complete. Both are fixed with tests and the final runs reflect the fixes.
4. The levers that still distort: per-plate category defaults (feta 45 g) dominate fish mains and pastas; the leaf-salad plate rule may undersize main-course salads; one outlier recipe can withdraw a dish's bound (pork chop); the menu reader and the relevance grader vary between runs, so a repeated menu can change which recipes feed a dish even when the ranking holds.
5. Coverage on unseen menus is structural (frying oil, side dishes as menu words, a Phase 2A rule on anchovies in oil), not a bug list.
