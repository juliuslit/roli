# Checkpoint 2B-1: recipe ingestion, extraction, parsing and conversions

Date: 2026-11-02. Spec: `SPEC_2B_recipe_scenarios.md`, sections 3–5 and 15.0. Status: **2B-1 complete; stopped for review. 2B-2 (USDA matching, relevance, calculation, LangGraph) not started. No modeled assumptions implemented (D5, D11 deferred as instructed).**

## 1. Summary

| Item | Result |
|---|---|
| Automated tests (agent suite) | **96 passed**, 4 skipped (live); 65 of them are the new recipe tests. Nutrition-service suite unchanged at 292 |
| Built | `roli_agent/recipes/`: search (Tavily behind a `RecipeSource` interface), fetch (robots, bounded 429 back-off, cache), extract (structured data first, verified LLM fallback), parse (lines and yields), convert (weight units only), ingest (orchestration, dedup, statistics) |
| Live ingestion, five Flour + Water dishes | 10 Tavily credits; 87 hits after URL dedup; 60 pages fetched, 49 answered; **33 recipes extracted, 32 distinct; 27 with a serving count; 6 with every line quantified** |
| Query rule | found by experiment (15 searches): dish name plus a specific menu section word for the open search; the first menu ingredient added on the structured-host search |
| Item 7, bottarga recipes | the three 2B-0 hits are distinct pages but **none is a crudo** (toast, anchovy dish, sous-vide sea bass); CHECKPOINT_2B0 corrected in its section 2c |
| Provenance | every recipe keeps URL, canonical URL, host, search mode(s) that found it, fetch time, extraction method, verbatim lines, verbatim yield text, cooking verbs from the method; every parsed line keeps the original text beside the parsed values |
| Calculator | untouched; nothing in this phase calls it |
| Secrets | none in code, fixtures, reports or logs (scan: 0 for all four keys) |

## 2. What was built

```text
MenuItem ─► search (open + structured_hosts) ─► merge_hits: canonical-URL dedup, found_by, blocked hosts skipped
         ─► PoliteFetcher: cache → cool-down → robots.txt → GET (429: back off 2 s, 4 s, then cool the host down) → size/type checks
         ─► extract_recipe: recipe-scrapers → schema.org JSON-LD (nutrition keys stripped) → LLM fallback with verbatim check
         ─► parse_line per ingredient line; parse_servings for the yield
         ─► convert_weight: g/kg/mg/oz/lb exact; water-like liquids by volume at density 1 (flagged); everything else pending USDA portions
         ─► content-hash dedup (same normalised lines under different URLs) ─► IngestionStats ─► IngestionResult
```

| Module | Responsibility | Key rules |
|---|---|---|
| `search.py` | `RecipeSource` protocol; `TavilySource` (basic depth, 1 credit per call); `canonical_url` (https, no `www.`, no tracking params, no fragment, print paths folded); `merge_hits` | one entry per canonical URL; `found_by` lists every mode that returned it with its rank; video, social, retail, paywalled hosts skipped |
| `fetch.py` | `PoliteFetcher`, `FetchCache` | robots.txt per host via `urllib.robotparser`; 429 → sleep 2 s, retry, sleep 4 s, retry, then the host is skipped for 10 minutes; 1 MB cap; HTML only; 30-day disk cache under `.cache/roli_recipes` (git-ignored) |
| `extract.py` | three extraction paths producing one shape | JSON-LD `nutrition` and all nutrient keys are removed before anything is read; LLM fallback keeps only lines that appear verbatim in the page text and drops an unverifiable yield |
| `parse.py` | ingredient-line grammar; yield parser | unicode and mixed fractions; ranges → midpoint with both bounds and `range_midpoint`; unit table (weight, volume, count); parenthetical and comma clauses → preparation words; line-level `raw` / `cooked` / `as_used` / `unknown` hint; "to taste" → unknown with `vague_quantity`; "Makes 2 pizzas", "12 slices", "1 item" → servings unknown |
| `convert.py` | pre-USDA conversions only | NIST factors recorded as `grams_reference`; water-like liquids (water, stock, broth, vinegar, lemon/lime juice, wine, coffee, tea) at 1.0 g/ml flagged `density_assumed_1`; milk, oil, flour, counts → `grams: None`, `conversion_pending_usda_portion` |
| `ingest.py` | `ingest_dish`, `default_queries`, statistics | search failures and fetch failures recorded, never fatal; listicle pages (≥ 5 lines, no quantities) flagged `no_quantities_listicle_suspect` |

Unknown never becomes zero anywhere: `grams` is `None` for every unquantified or unconverted line, and the tests assert it.

## 3. The query rule, with evidence

The first live run used "dish name + every menu ingredient" and returned bottarga pasta and toast for the crudo. An experiment on the five dishes (open search, 15 credits; "on-dish" = extracted recipe whose title names the dish):

| Dish | name only | name + first ingredient | name + all ingredients |
|---|---:|---:|---:|
| bluefin crudo | **4** on-dish of 4 extracted | 1 of 2 | 0 of 0 |
| little gem lettuces | **6** of 6 | 1 of 1 | 2 of 2 |
| heirloom tomatoes | 2 of 2 (one a listicle) | **1** of 1 (pluot-tomato salad) | 0 of 0 |
| margherita | 1 of 5 (**4 cocktails**) | **5** of 5 | 5 of 5 |
| king salmon | 4 of 4 | **6** of 6 | 5 of 5 |

Rule adopted: open search = dish name, plus the menu section word when it is specific ("margherita pizza recipe"; generic headings such as TO START or ENTREE are skipped); structured-host search = the same plus the first menu ingredient. Tested in `test_specific_section_word_joins_the_query_generic_ones_do_not`. An LLM query writer remains an option for 2B-2 and is not used.

## 4. Live ingestion of the five dishes (final run, exact script output)

```text
## BLUEFIN CRUDO (bottarga, muscat grape, chive)  queries: 'bluefin crudo recipe'
hits: open 10, structured 10, after URL dedup 18 (in both modes 0; blocked skipped 2)
fetched 12: ok 11 (cache 11), robots 0, 429 0, other errors 1
extracted 6 by {'none': 5, 'recipe_scrapers': 6}; content duplicates 0; distinct 6; with servings 5
lines quantified 83.1%, grams known now 27.7%, recipes fully quantified 1; 1.1s
  - [open] foodmymuse.com | 'Spicy Tuna Crudo with Shoyu Ponzu Sauce' | recipe_scrapers | yield='2 servings' -> servings=2 | lines=15 quantified=13 grams=2 | verbs=['fried', 'fry']
  - [open] coleycooks.com | 'Sicilian Tuna Crudo with Olives and Pistachios' | recipe_scrapers | yield='4 servings' -> servings=4 | lines=8 quantified=7 grams=1 | verbs=[]
  - [open] twopurplefigs.com | 'Tuna Crudo' | recipe_scrapers | yield='4 servings' -> servings=4 | lines=13 quantified=13 grams=1 | verbs=['fried']
  - [open] lindseyeatsla.com | 'Tuna Crudo with Citrus Caper Vinaigrette' | recipe_scrapers | yield='4 servings' -> servings=4 | lines=9 quantified=5 grams=1 | verbs=['toasted']
  - [structured_hosts] cooking.nytimes.com | 'Spaghettini With Bottarga and Colatura' | recipe_scrapers | yield='1 serving' -> servings=1 | lines=9 quantified=6 grams=2 | verbs=['boil']
  - [structured_hosts] greatitalianchefs.com | 'Spaghetti with bottarga sauce' | recipe_scrapers | yield='' -> servings=None | lines=29 quantified=25 grams=16 | verbs=[]

## LITTLE GEM LETTUCES (tahini vinaigrette, pecorino sardo, toasted sesame)  queries: 'little gem lettuces recipe'
hits: open 10, structured 10, after URL dedup 17 (in both modes 0; blocked skipped 3)
fetched 12: ok 7 (cache 7), robots 0, 429 0, other errors 5
extracted 6 by {'recipe_scrapers': 6, 'none': 1}; content duplicates 0; distinct 6; with servings 6
lines quantified 83.6%, grams known now 6.0%, recipes fully quantified 1; 1.0s
  - [open] recipetineats.com | 'Baby Gem Lettuce Salad' | recipe_scrapers | yield='4 servings' -> servings=4 | lines=8 quantified=7 grams=0 | verbs=['bake']
  - [open] pinchandswirl.com | 'Little Gem Salad' | recipe_scrapers | yield='4 servings' -> servings=4 | lines=8 quantified=7 grams=1 | verbs=[]
  - [open] somethingnewfordinner.com | 'Grilled Little Gem salad' | recipe_scrapers | yield='4 servings' -> servings=4 | lines=7 quantified=7 grams=1 | verbs=['charred', 'grill']
  - [open] cravingcalifornia.com | 'Little Gem Wedge Salad with Bacon, Blue Cheese, an' | recipe_scrapers | yield='4 servings' -> servings=4 | lines=15 quantified=14 grams=1 | verbs=['boiled', 'saute']
  - [open] alisoneroman.com | 'Little Gems with Garlicky Lemon and Pistachio' | recipe_scrapers | yield='4 servings' -> servings=4 | lines=10 quantified=8 grams=0 | verbs=['toast']
  - [open] laboiteny.com | 'Little Gem Salad with Herbed Breadcrumbs' | recipe_scrapers | yield='4 servings' -> servings=4 | lines=19 quantified=13 grams=1 | verbs=['sauté', 'toast']

## HEIRLOOM TOMATOES (pluot, shiso, genovese basil, sourdough)  queries: 'heirloom tomatoes recipe'
hits: open 10, structured 10, after URL dedup 18 (in both modes 0; blocked skipped 2)
fetched 12: ok 10 (cache 10), robots 0, 429 0, other errors 2
extracted 4 by {'none': 6, 'recipe_scrapers': 4}; content duplicates 0; distinct 4; with servings 3
lines quantified 47.5%, grams known now 5.1%, recipes fully quantified 1; 0.8s
  - [open] cookingchew.com | '21 Heirloom Tomato Recipes' | recipe_scrapers | yield='' -> servings=None | lines=20 quantified=0 grams=0 | verbs=[]
  - [open] thesophisticatedcaveman.com | 'Heirloom Tomato Salad' | recipe_scrapers | yield='6 servings' -> servings=6 | lines=10 quantified=10 grams=2 | verbs=[]
  - [open] holcombfarm.org | 'Roasted Heirloom Tomato Soup with Smoked Paprika' | recipe_scrapers | yield='4 servings' -> servings=4 | lines=7 quantified=0 grams=0 | verbs=['bake', 'smoked']
  - [structured_hosts] cooking.nytimes.com | 'Pluot-Tomato Salad With Suya Pistachio Crunch' | recipe_scrapers | yield='6 servings' -> servings=6 | lines=22 quantified=18 grams=1 | verbs=['bake']

## MARGHERITA (tomato, fior di latte, basil)  queries: 'margherita pizza recipe'
hits: open 10, structured 10, after URL dedup 17 (in both modes 1; blocked skipped 2)
fetched 12: ok 10 (cache 1), robots 0, 429 0, other errors 2
extracted 9 by {'recipe_scrapers': 9, 'none': 1}; content duplicates 1; distinct 8; with servings 7
lines quantified 85.1%, grams known now 16.2%, recipes fully quantified 2; 10.1s
  - [open,structured_hosts] tasteofhome.com | 'Margherita Pizza' | recipe_scrapers | yield='6 servings' -> servings=6 | lines=14 quantified=14 grams=2 | verbs=['bake']
  - [open] kingarthurbaking.com | 'Margherita Pizza' | recipe_scrapers | yield='12 servings' -> servings=12 | lines=12 quantified=11 grams=2 | verbs=['bake', 'charred', 'uncooked']
  - [open] easyanddelish.com | 'Margherita Pizza Recipe' | recipe_scrapers | yield='8 slices' -> servings=None | lines=5 quantified=5 grams=0 | verbs=['bake']
  - [open] abeautifulplate.com | 'Best Homemade Margherita Pizza' | recipe_scrapers | yield='4 servings' -> servings=4 | lines=16 quantified=14 grams=2 | verbs=['bake', 'broil']
  - [open] bellyfull.net | 'Easy Margherita Pizza' | recipe_scrapers | yield='8 servings' -> servings=8 | lines=9 quantified=7 grams=2 | verbs=['bake']
  - [open] bakingsteel.com | 'The Perfect Margherita Pizza' | recipe_scrapers | yield='1 serving' -> servings=1 | lines=6 quantified=3 grams=2 | verbs=['bake', 'broil']
  - [structured_hosts] cooking.nytimes.com | 'Pizza Margherita' | recipe_scrapers | yield='2 servings' -> servings=2 | lines=5 quantified=4 grams=1 | verbs=['bake']
  - [structured_hosts] cooking.nytimes.com | 'Pizza Margherita' | recipe_scrapers | yield='2 servings' -> servings=2 | lines=5 quantified=4 grams=1 | verbs=['bake'] DUPLICATE of https://cooking.nytimes.com/recipes/1016231-pizza-margherita?eafs_enabled=false
  - [structured_hosts] lacucinaitaliana.com | 'Margherita Pizza' | recipe_scrapers | yield='2 servings' -> servings=2 | lines=7 quantified=5 grams=1 | verbs=['bake']

## KING SALMON (squash, corn, basil, shishito)  queries: 'king salmon recipe'
hits: open 10, structured 10, after URL dedup 17 (in both modes 0; blocked skipped 3)
fetched 12: ok 11 (cache 11), robots 0, 429 0, other errors 1
extracted 8 by {'none': 3, 'recipe_scrapers': 7, 'json_ld': 1}; content duplicates 0; distinct 8; with servings 6
lines quantified 81.4%, grams known now 18.6%, recipes fully quantified 1; 0.7s
  - [open] thishealthytable.com | 'Baked King Salmon' | recipe_scrapers | yield='4 servings' -> servings=4 | lines=10 quantified=9 grams=2 | verbs=['bake']
  - [open] wagyushop.com | 'Pan-Seared Buttery Ora King Salmon Fillets' | json_ld | yield='' -> servings=None | lines=5 quantified=4 grams=2 | verbs=[]
  - [open] premiercatch.com | 'Simple King Salmon en Papillote' | recipe_scrapers | yield='1 serving' -> servings=1 | lines=9 quantified=5 grams=0 | verbs=['bake']
  - [open] lecremedelacrumb.com | 'Best Easy Healthy Baked Salmon' | recipe_scrapers | yield='4 servings' -> servings=4 | lines=7 quantified=7 grams=0 | verbs=['bake', 'broil']
  - [structured_hosts] foodnetwork.com | 'Pan-Seared Wild Pacific King Salmon with Lemon and' | recipe_scrapers | yield='6 servings' -> servings=6 | lines=18 quantified=17 grams=3 | verbs=['boil', 'saute', 'sear']
  - [structured_hosts] bbcgoodfood.com | 'Salmon, squash & prawn laksa' | recipe_scrapers | yield='6 servings' -> servings=6 | lines=11 quantified=8 grams=7 | verbs=['boil', 'fry', 'simmer']
  - [structured_hosts] cooking.nytimes.com | 'Oven-Seared Salmon With Corn and Tomatoes' | recipe_scrapers | yield='4 servings' -> servings=4 | lines=9 quantified=8 grams=0 | verbs=['broil']
  - [structured_hosts] epicurious.com | 'Crispy-Skin King Salmon with Roasted Asparagus, Fi' | recipe_scrapers | yield='4 items' -> servings=None | lines=17 quantified=12 grams=2 | verbs=['roast', 'sauté', 'sear', 'simmer']

## Totals
{'hits_after_url_dedup': 87, 'hits_in_both_modes': 1, 'fetched': 60, 'fetch_ok': 49, 'robots_disallowed': 0, 'rate_limited': 0, 'http_errors': 11, 'extracted': 33, 'content_duplicates': 1, 'distinct_recipes': 32, 'with_servings': 27, 'recipes_with_all_lines_quantified': 6, 'search_credits': 10}
tavily credits used: 10
```

Reading the per-dish results:
- **Bluefin Crudo:** four genuine tuna crudo recipes (spicy ponzu, Sicilian, plain, citrus-caper) plus two bottarga pasta recipes from the structured-host search; none contains bottarga *and* is a crudo. 2B-2's relevance grading will reject the pastas; D8 will append bottarga as an unknown-quantity line to the crudos.
- **Little Gem Lettuces:** six little-gem salads, all with servings; none has the tahini-pecorino-sesame dressing. Relevance is medium at best; coverage will flag the missing dressing components.
- **Heirloom Tomatoes:** one listicle (flagged), one soup, one plain salad, and a pluot-tomato salad from the structured search, the first recipe found with a menu-specific fruit.
- **Margherita:** eight distinct pizza recipes with servings on seven; the earlier cocktail drift is gone.
- **King Salmon:** eight salmon recipes, several king-salmon specific; vegetables differ from the menu's squash, corn and shishito.

Deduplication: 87 URL-level hits from 100 raw results (blocked hosts skipped: 12 across dishes; same page in both modes: 1); one content duplicate (a New York Times page reached with and without an `eafs_enabled=false` parameter the canonical rule does not strip, caught by the content hash). Fetching: 49 of 60 answered, 0 robots refusals, 0 rate-limit failures in the final run (one 429 was absorbed by back-off in an earlier run), 11 other HTTP errors (403s from sites that refuse scripted clients).

Usability (requirement 6), over the 32 distinct recipes: 27 state a serving count (84%); 6 have every line quantified; the share of lines with a parsed quantity and unit ranges from 47% (tomatoes, dragged down by the listicle) to 85% (margherita); the share with grams known *now*, before USDA portions, is 5–28%, because recipes are written in cups, tablespoons and counts. That gap is exactly what `get_portions()` in 2B-2 addresses.

## 5. Parsing and conversion examples

| Line (verbatim) | Quantity | Unit | Kind | Name | Preparation words | Hint | Grams now | Reference / flags |
|---|---:|---|---|---|---|---|---:|---|
| 1 pound (1-inch thick) salmon fillets, skin removed | 1 | lb | weight | salmon fillets | 1-inch thick, skin removed | unknown | 453.59237 | 1 lb = 453.59237 g (NIST SP 811)  |
| 85 g sushi-grade bluefin tuna, thinly sliced | 85 | g | weight | sushi-grade bluefin tuna | thinly sliced | raw | 85 | 1 g  |
| 3 oz bottarga, grated | 3 | oz | weight | bottarga | grated | as_used | 85.048569375 | 1 oz = 28.349523125 g (NIST SP 811)  |
| 2 tablespoons extra-virgin olive oil | 2 | tbsp | volume | extra-virgin olive oil |  | as_used | unknown |  conversion_pending_usda_portion |
| 1½ cups diced fresh fior di latte mozzarella cheese | 1 1/2 | cup | volume | diced fresh fior di latte mozzarella cheese |  | as_used | unknown |  conversion_pending_usda_portion |
| 1-2 tbsp chives (chopped) | 1-2 (→ 1.5, bounds 1–2) | tbsp | volume | chives | chopped | unknown | unknown |  range_midpoint conversion_pending_usda_portion |
| 4 ripe plum tomatoes, cut into thin rounds | 4 | each | count | ripe plum tomatoes | cut into thin rounds | unknown | unknown |  conversion_pending_usda_portion |
| 2 large eggs | 2 | large | count | eggs |  | unknown | unknown |  conversion_pending_usda_portion |
| 1 (14 oz) can San Marzano tomatoes | 1 | can | count | san marzano tomatoes | 14 oz | unknown | unknown |  conversion_pending_usda_portion |
| 1/2 cup water | 1/2 | cup | volume | water |  | unknown | 118.29411825 | 1 US cup = 236.5882365 ml (NIST HB 44); density 1.0 g/ml assumed (water-like liquid) density_assumed_1 |
| 500 ml chicken stock | 500 | ml | volume | chicken stock |  | unknown | 500 | 1 ml; density 1.0 g/ml assumed (water-like liquid) density_assumed_1 |
| Salt, to taste | to taste |  | none | salt | to taste | as_used | unknown |  vague_quantity |
| A handful of basil leaves | 1 | handful | count | basil leaves |  | unknown | unknown |  conversion_pending_usda_portion |
| 50 g pecorino romano, finely grated | 50 | g | weight | pecorino romano | finely grated | as_used | 50 | 1 g  |

| Yield text | Servings | Note |
|---|---:|---|
| '4 servings' | 4 | parsed from '4 servings' |
| 'Serves 4' | 4 | parsed from 'Serves 4' |
| '4 to 6 servings' | 5 | range '4 to 6 servings' -> midpoint (range_midpoint) |
| 'serves 4-6 people' | 5 | range 'serves 4-6 people' -> midpoint (range_midpoint) |
| '6' | 6 | parsed from '6' |
| '12 slices' | unknown | yield '12 slices' is not a serving count |
| 'Makes 2 pizzas' | unknown | yield 'Makes 2 pizzas' is not a serving count |
| '1 item' | unknown | yield '1 item' is not a serving count |
| '8 slices' | unknown | yield '8 slices' is not a serving count |
| '' | unknown | no yield stated |

## 6. Representative extracted recipes (facts only, from the saved fixtures)

Fixtures: `roli_agent/tests/fixtures/recipes/*.json` (five files, 33 recipes), each recipe with URL, canonical URL, host, `found_by`, fetch time, extraction method, verbatim `ingredient_lines`, verbatim `yield_text`, parsed servings with note, cooking verbs, and the parsed lines. Instructions prose is not stored. Examples:

- **Tuna Crudo** (twopurplefigs.com, open search, `recipe_scrapers`, "4 servings" → 4): 13 lines, all 13 quantified, 1 with grams now. A clean raw-fish scenario for 2B-2 once the tuna line is matched to USDA 173706 and its portion converted.
- **Pluot-Tomato Salad With Suya Pistachio Crunch** (cooking.nytimes.com, structured search, "6 servings" → 6): 22 lines, 18 quantified. The one recipe that shares the menu's pluot.
- **Margherita Pizza** (tasteofhome.com, found by **both** modes, "6 servings" → 6): 14 lines, all quantified, 2 with grams now.
- **Spaghetti with bottarga sauce** (greatitalianchefs.com, structured search, no yield): 29 lines, 25 quantified, 16 with grams now, servings unknown → ineligible for per-serving until 2B-2's text-yield fallback, and in any case not a crudo.
- **21 Heirloom Tomato Recipes** (cookingchew.com): 20 "lines", 0 quantified → `no_quantities_listicle_suspect`.

## 7. Item 7: the bottarga recipes

The three 2B-0 search results that contained the word bottarga and lacked only grape and chive were fetched and read:

| Page | Title | Fish | Bottarga line | What it is |
|---|---|---|---|---|
| lacucinaitaliana.com | Tuna and Bottarga Toast | 4½ oz water-packed tuna (canned) | "Fresh bottarga di tonno" (no amount) | a toast, not a crudo |
| greatitalianchefs.com | 'Anchovy painting', anchovy with bottarga mayonnaise | 400 g anchovies, cuttlefish ink | 40 g tuna bottarga | pickled anchovies |
| greatitalianchefs.com | Sea bass with apple, fennel and celery | 320 g sea bass, prawns, scallops | 20 g bottarga, grated | sous-vide sea bass |

Distinct: 3 of 3 (different content hashes). Credible crudo matches: 0 of 3. The 2B-0 report has been corrected (section 2c). The lesson is recorded in the spec: menu-ingredient coverage is one relevance signal among several and can never qualify a recipe on its own; 2B-2's dish-type and preparation grading, with D10's hard exclusions, is what rejects these.

## 8. Files

Created: `roli_agent/recipes/__init__.py`, `models.py`, `search.py`, `fetch.py`, `extract.py`, `parse.py`, `convert.py`, `ingest.py`; `roli_agent/scripts/__init__.py` (none needed; run as a module) and `roli_agent/scripts/ingest_report_2b1.py`; tests `test_recipes_parse.py`, `test_recipes_extract.py`, `test_recipes_fetch_search.py`, `test_recipes_ingest.py`; fixtures `roli_agent/tests/fixtures/recipes/` (5 files); evidence `roli_agent/source_eval/tavily_bench.py` and results; `roli_agent/test_report_2B1.txt`; this file.

Modified: `SPEC_2B_recipe_scenarios.md` (15.0 decisions, D1 final, D5 deferral note), `CHECKPOINT_2B0.md` (section 2c correction), root `requirements.txt` (`recipe-scrapers`), root `.gitignore` (`.cache/`). Installed: `recipe-scrapers` 15.13.0 (MIT) in the root `.venv`.

Unchanged: the Phase 2A calculator and its tests, `nutrition_service/` entirely, `code/`, the MCP wrapper, the LangSmith prototype.

## 9. Deviations and decisions taken

1. **Deterministic queries instead of an LLM query writer** (spec 3.1 allowed one LLM call). The experiment showed a simple rule works; it costs nothing and is testable. An LLM writer can be added in 2B-2 if relevance results call for it.
2. **Section word in the query** (not in the spec): the only way found to separate "margherita" the pizza from the cocktail without an LLM.
3. **Instructions text is kept in memory for cooking-verb hints but not written to fixtures**, out of copyright caution; fixtures hold ingredient lines, yields, titles and URLs, which are facts.
4. **Canonical URL folds `/print/`, `/wprm_print/` and `/easyrecipe-print/` paths** but does not strip arbitrary query parameters (only tracking ones); content hashing catches the rest, as the NYT duplicate showed.
5. **Listicle flag** added as a deterministic non-recipe signal.
6. **D5 negligible seasonings not implemented**, per your D11 instruction to keep unknown-quantity handling unchanged until this review. "Salt, to taste" is parsed as unknown and will make scenarios incomplete in 2B-2 unless D5 is approved.

## 10. Remaining decisions for you

| # | Decision | Recommendation |
|---|---|---|
| D5 | Implement the narrow modeled-zero seasoning list in 2B-2 (unknown grams preserved, explicit flag, USDA-cited)? Without it, almost every scenario is incomplete because of "salt to taste" | implement in 2B-2, list capped to items with 0 mg cholesterol and ≤ 0.05 g saturated fat per 100 g |
| D11 | The menu-adapted scenario approach (explicit assumed weights for missing menu ingredients, calculated with the real calculator): specify in 2B-2's checkpoint, build later? | document in 2B-2, build in 2C |
| D15 | Yield fallback: when `recipeYield` is blank (5 of 32 here), read "Serves N" from the page text with the verbatim check, else leave unknown | adopt in 2B-2 |
| D16 | Listicle and non-recipe pages: drop flagged pages before 2B-2 processing, or keep and let relevance grading reject them | drop when flagged `no_quantities_listicle_suspect`; everything else goes to grading |
| D17 | Hosts that refuse scripted clients (403): maintain a short skip list to save fetch attempts, or keep trying each time | keep trying (no cost beyond one request) but exclude them from the structured-host list if they recur |

**Stopped here. 2B-2 starts only after your review.**
