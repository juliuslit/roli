# Human review of the MVP's actual recommendations, v1 (drafted 2026-11-04 for Julius)

Drafted from the saved runs under `roli_agent/runs/` (run ids below); **awaiting Julius's review**. The agent's own expected ranges
(`expectations_2d_v1.csv`) are not used as proof here; each judgment is argued from the ingredients the recipes name, the USDA values of the
dominant ingredients, and what the kitchen's menu says. Close pairs and specialty ingredients first, as asked.

## Flour + Water (menu_03; runs 20261104-010950 cold, 20261104-011834 warm; identical rankings and text)

Recommendation shown: *1) Bluefin Crudo (0.5-1.6 g, close call); 2) Heirloom Tomatoes (0.4-2.1 g, tentative); 3) Little Gem Lettuces (4.4-8.6 g, close call); crudo cholesterol 17-115 mg; 12 of 17 dishes could not be estimated.*

| Case | What the prototype did | Review | Verdict |
|---|---|---|---|
| **Crudo vs tomatoes (close pair)** | ranked the crudo first because its upper bound (1.6 g) sits below the tomatoes' (2.1 g); called it a close call because the two ranges overlap | The crudo's upper bound comes from **one** recipe (James Beard) and rests on the external bounds for bottarga and jarred chiles; the other two crudo recipes have no upper bound (an unquantified chile and a pinch of flakes). The tomato salad's bound rests on one recipe plus bounds for red onion and oregano. Both are lean plant-or-raw-fish plates; the order between them is not knowable from this evidence. The "close call" label is right; a stricter reading would call the pair a tie. | plausible, correctly hedged |
| **Crudo cholesterol 17-115 mg (specialty ingredient)** | the upper end is the bottarga bound (10 g at 722 mg/100 g) added to the tuna | This is the single most material specialty-ingredient effect on the menu: without bottarga the crudo would read 17-42 mg. The wording shows the range but not that bottarga is the reason; the diagnostics do. A tester who avoids cholesterol needs that sentence in the recommendation. | accurate; wording should name bottarga |
| **Little gem third (close call)** | 4.4-8.6 g from one recipe; overlaps the salmon (4.1-14.9 g) | The gem salad's figure is 60 % assumptions (pecorino 5-15 g, tahini dressing 15-30 g); a lighter dressing would put it near the tomatoes, a heavier one near the salmon. Ranking it third over the salmon is defensible only as "probably lower, overlapping", which is what close call says. | plausible, assumption-driven |
| **King salmon fourth, margherita fifth** | salmon 4.1-14.9 g (4 recipes, 2 complete), pizza 8.9-27.6 g (3 recipes, 1 bounded) | A whole 12-13-inch margherita with fior di latte is the richest plate on the menu for saturated fat; a shared half overlaps a salmon main. Both the order and the overlap match what the ingredients say. | plausible |
| **12 of 17 not estimated** | pasta courses, the pork chop, the two other pizzas, arancini, pole beans | Honest: the menu lists ingredients (burrata, caciocavallo, mussels escabeche, lamb merguez ragu) that no recipe quantifies and no weights row covers, so the totals stay open. Not an error, a coverage gap. | correct refusal |

## The Greyhound, a British gastropub (menu_08; run 20261104-012103)

Shown: *1) Padron Peppers (1.2-3.1 g).* 11 of 12 evaluated dishes could not be ranked; 26 items were outside the rules (sides, desserts, sharing platters, burgers).

| Case | What the prototype did | Review | Verdict |
|---|---|---|---|
| **Padron peppers as the only pick** | ranked alone, so labelled "the only dish we could estimate" | Blistered peppers in oil are indeed low in saturated fat; the number is believable. But recommending it as "lowest" when the fish, the sea bass or the chicken were never bounded would mislead; the new label says so. | right figure; the label matters |
| **Sirloin steak 10 oz unbounded** | "mesquite seasoning (missing grams)" and similar lines left every steak recipe open | A 10 oz sirloin is 280 g of beef at 4-6 g saturated fat per 100 g: the steak itself would bound at 11-17 g and the seasoning could not change that. The seasoning row (W29) added after this run should bound it; **re-run to confirm**. | defect found, fix untested live |
| **Fish and chips, schnitzel** | unbounded because of "vegetable oil for frying" | Correct refusal: deep-frying absorbs an unknown amount of oil; no row should bound it. | correct refusal |
| **Cap reached at 12 dishes** | the first 12 items in menu order were snacks and starters; the pub classics were beyond the cap | The cap is a cost control, but menu order is the wrong priority. Raised to 14 and sharing platters excluded; a mains-first order is worth a decision. | process defect |

## Zuni Café (menu_01; run 20261104-012643)

Shown: *1) Wood fire-roasted tomato and eggplant soup (0.6-4.7 g); 2) Ribeye steak (11-28 g).* 7 evaluated dishes unranked; 2 errored on the provider's credit limit; 59 items were drinks or outside the rules.

| Case | What the prototype did | Review | Verdict |
|---|---|---|---|
| **Soup first, ribeye second, well supported** | the ribeye's lower bound (11 g) sits far above the soup's upper bound (4.7 g) | A ribeye at 140-280 g against a vegetable soup: the direction is certain whatever the recipes. Well supported is right. | plausible |
| **Steak frites unbounded** | "steak-cut frozen fries" line | Fries fried in unknown oil: correct refusal, same family as the schnitzel. | correct refusal |
| **Caesar salad and the pizza errored** | 402 from OpenRouter: the account's credit was exhausted mid-run | Not a pipeline fault; the run continued and reported the two dishes as errors, as designed. | handled |

## What this review says about the prototype

1. Where the dominant ingredient decides (steak vs soup, pizza vs salad), the ranking is right and says "well supported".
2. Where two lean plates compete (crudo vs tomatoes), the prototype correctly refuses to call a winner, but the wording should say which specialty ingredient drives the only number a tester would act on (bottarga's cholesterol).
3. Coverage, not accuracy, is the limit on unseen menus: 1 of 12 and 2 of 9 dishes ranked, because menu-only ingredients have no weights rows and frying oil is rightly unbounded.
4. Two defects were found and fixed in code but **not re-measured live** (seasoning rows; the dish cap order and sharing platters), because the OpenRouter credit ran out.
