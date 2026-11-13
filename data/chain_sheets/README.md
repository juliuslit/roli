# Chain nutrition sheets (SPEC_3_mvp.md 12.16.6, source (b))

One CSV per chain and sheet. Every row is read from the chain's own published sheet; `derivation` says how a figure was arrived at when the sheet does not print it directly (a serving weight from energy per portion over energy per 100 g). Nothing here enters a total: these rows feed `roli_agent/scripts/build_cards.py`, which writes the plate-size table and the reference figures.

| file | chain | sheet | read on |
|---|---|---|---|
| `pizzaexpress_2026-11.csv` | Pizza Express (UK) | Nutrition Information, England, Wales & Scotland, November 2026 (PDF) | 2026-11-06 |
| `bonefish_2026-06.csv` | Bonefish Grill (US) | Bonefish Grill Nutrition, created June 2026 (PDF); saturated fat and cholesterol per serving, no weights; fish and cut weights stated in some item names | 2026-11-06 |
| `carrabbas_2026-09.csv` | Carrabba's Italian Grill (US) | Carrabba's Italian Grill Nutrition, created September 2026 (PDF, linked from carrabbas.com/nutrition; the May 2025 PDF is 404); per serving, no weights; steak weights in item names | 2026-11-06 |
| `wasabi_2026-06.csv` | Wasabi (UK) | Nutritional Guide version 32, released 4 June 2026 (PDF); per 100 g with a portion size column | 2026-11-06 |
| `yosushi_2024-07.csv` | YO! Sushi (UK) | To Go allergen and nutrition guide, July 2024 (PDF); per serving, no weights; sashimi weights derived from kcal and USDA raw fish records 175167 and 175159 | 2026-11-06 |
| `zizzi_2026-09.csv` | Zizzi (UK) | UK Nutrition Guide Autumn 2026 V1, 15.09.26 (PDF, linked from zizzi.co.uk/menus; the 2024 and 2025 URLs redirect or 404); per 100 g and per portion, weights derived | 2026-11-06 |
| `vapiano_2022-11.csv` | Vapiano | Nutritionals sheet, 2022 (PDF); portion weights printed, per portion and per 100 g | 2026-11-06 |
| `prezzo_jan.csv` | Prezzo (UK) | Website nutrition sheet, January, V2, year not printed (PDF); per serving only, so reference figures only | 2026-11-06 |

Not read, and why (2026-11-06): Wagamama's per-dish pages are built in the browser and the URL given returned 404, so no figures could be fetched without a browser; ASK Italian's May 2023 PDF URL returns a "Page Not Found" page and the site's menus page links only an allergen guide (autumn 2026), no nutrition guide; Wetherspoon's menu PDF (MENU_7933, summer 2026) prints kcal only and says weights are approximate uncooked, with the full nutrition on the customer screen and app, and the website links no nutrition sheet; the YO! Sushi restaurant menu PDF is 404 (the To Go guide was read instead). Nando's, Chipotle, Panera and Denny's were not attempted in this pass (Denny's and Chipotle items are in MenuStat 2017-2018). Third-party copies were not used.

Columns: `serving_g` is the plate weight as stated or derived; a protein weight stated in the item name ("Grilled Atlantic Salmon 7.5 oz") is read by `build_cards.py` into the P3 key share and never into the plate weight; rows with no weight feed the reference figures only. `family` names a row family of `portion_rules.csv`; `rice_bowl` has no row yet and is recorded for a future family.

Earlier chain figures (Papa's Fish and Chips lab weights, JD Wetherspoon portions, the UK pub fish and chips figures via CalorieKing and Fitatu) stay in `roli_agent/recipes/reference_figures.csv` and `portion_rules.csv` with their own citations.
