# Technical Specification: Phase 2B, Automated Recipe Discovery, Extraction and USDA Matching

Status: **architecture approved by Julius 2026-11-02 with revised decisions D1–D10 (section 15), Phase 2B-0 source evaluation done, Phase 2B-1 approved 2026-11-02, and the Phase 2B-2 decisions D5/D11/D15/D16/D17 plus ten requirements recorded in section 15.2. Sections 15, 15.0 and 15.2 are authoritative where they differ from the body text.** Builds on `nutrition_service/SPEC_2A_recipe_calculator.md` (the calculator, unchanged in this phase) and `roli_agent/CHECKPOINT_1E.md` (the graph's search-and-select path and failure rules).

## 0. One-paragraph summary

Given one menu item (name and printed ingredient list, from the menu reader), Roli finds up to three published recipes for that dish, records each one's URL and yield, extracts its ingredient lines into validated data, converts household measures to grams with deterministic rules whose references are recorded, matches each ingredient to a USDA record through the existing search-and-select path while labelling every match *direct*, *proxy* or *unresolved*, appends every menu-listed ingredient that a recipe lacks as an unknown-quantity line so nothing like bottarga can vanish, runs each recipe through the Phase 2A calculator untouched, and compares the complete scenarios as "the range across modeled recipes". Two separate judgements are reported for every scenario: whether its arithmetic is complete, and how representative it is of the restaurant's dish (ingredient coverage plus a graded preparation match). The LLM reads pages and names things; Python fetches, parses, converts, matches, computes and decides what may be said. No nutrient number ever comes from a web page or from the LLM.

## 1. Objective and non-goals

**Goal.** Credible, auditable recipe scenarios for a restaurant dish from real-world sources, feeding the existing calculator and comparison.

**Non-goals (later phases):** Telegram or web front end, ranking dishes across a menu, the conversational experience, daily and weekly totals, cooking-yield or nutrient-retention adjustments beyond what section 6 allows, any change to the calculator's arithmetic.

**Input:** one `MenuItem` from the menu reader's answer format: `name`, `description` (the printed ingredient words), `section`, optional restaurant name and cuisine. **Output:** one `DishEstimate` (section 9).

## 2. Pipeline and ownership

```text
MenuItem ─► 1 discover ─► 2 fetch ─► 3 extract ─► 4 parse lines ─► 5 convert to grams ─► 6 match USDA
         (search API)   (HTTP)    (JSON-LD, else LLM)  (Python)       (Python + USDA portions)  (1E path)
         ─► 7 inject menu-only ingredients ─► 8 calculate (Phase 2A, unchanged) ─► 9 grade relevance ─► 10 compare ─► DishEstimate
                 (Python)                            (Python)                    (Python + LLM rubric)   (Phase 2A compare)
```

| Step | Who | May the LLM be used? | Numbers produced |
|---|---|---|---|
| 1 discover | search API client | to write the search query (one call per dish) | none |
| 2 fetch | httpx | no | none |
| 3 extract | JSON-LD parser; LLM fallback for pages without structured data | yes, output validated by Pydantic | quantities as *text* only, copied from the page |
| 4 parse lines | Python regex grammar | no (an LLM pass may only *normalise ingredient names*, never quantities) | quantity and unit as text → Decimal |
| 5 convert | Python rules + USDA `foodPortions` | no | grams, each with a recorded factor and reference |
| 6 match | Phase 1E search-and-select | yes, bounded by USDA's candidate list (existing guard) | FDC IDs only |
| 7 inject | Python set difference | no | none |
| 8 calculate | Phase 2A | no | all nutrient numbers |
| 9 grade | Python coverage + LLM rubric | yes, categorical output only | coverage fraction (Python) |
| 10 compare | Phase 2A | no | min, median, max |

Rule carried from Phase 1E: every LLM output is parsed into a Pydantic model with `extra="forbid"`; a parse failure is a recorded failure of that step for that scenario, never a retry with a looser prompt and never a guessed value.

## 3. Recipe discovery and relevance (requirement 1)

### 3.1 Search

- **Provider (decision D1, deferred):** chosen in Phase 2B-0. Candidates: a structured recipe API (Spoonacular, Edamam), web search plus extraction (Tavily + `recipe-scrapers`), TheMealDB as a free baseline. Every source implements one `RecipeSource` interface (`find(menu_item) -> list[RecipeSource records]`) so the pipeline never depends on a provider. Any key goes in `roli/.env`; the usual secrecy rules apply.
- **Query:** one LLM call turns the menu item into one to two search strings ("bluefin crudo bottarga recipe", "tuna crudo recipe"), returned as JSON; the LLM never sees search results. Default: 1 query, a second only if the first yields fewer than 3 usable pages.
- **Result filtering (Python):** keep pages whose URL host is not in a block list (video platforms, social media, forums, retail), at most one page per host, at most 8 fetched per dish.
- **Budget:** ≤ 2 search calls and ≤ 8 page fetches per dish.

### 3.2 Fetch and extract

- **Fetch:** httpx, 10 s timeout, 1 MB cap, a plain `User-Agent` naming Roli, `robots.txt` respected (a page whose robots rules disallow fetching is skipped and recorded as `robots_disallowed`), results cached on disk for 30 days keyed by URL hash so re-runs and tests do not re-fetch.
- **Extract, deterministic first (decision D2):** parse schema.org `Recipe` JSON-LD (or microdata) for `name`, `recipeIngredient[]`, `recipeYield`, `recipeInstructions`, `url`. Most recipe sites publish it. Library: `recipe-scrapers` (handles hundreds of sites and the generic JSON-LD case), pinned, verified at implementation time; fallback to `extruct` if the former proves too site-specific.
- **Extract, LLM fallback:** only when no structured data exists. The page's visible text (capped at 12,000 characters) goes to the LLM with the instruction to return the ingredient lines *verbatim*, the yield text verbatim, and the preparation steps summarised, as JSON. Verbatim means the test can check every returned ingredient line is a substring of the page text; a line that is not is dropped and the scenario flagged `extraction_unverifiable`.
- **Nutrition blocks on recipe pages are ignored entirely.** Structured recipes often carry a `nutrition` object; the parser never reads it, and a test asserts no field named calories, fat, saturated, cholesterol or sodium from a page ever appears in state. Requirement 8 depends on this.

### 3.3 Relevance to the menu dish (two separate measures)

**Measure A, menu ingredient coverage (Python, deterministic).** The menu's printed ingredient words (e.g. "bottarga, muscat grape, chive") are split on commas and matched against the recipe's parsed ingredient names by normalised token overlap, with a small synonym table (muscat grape → grapes, chive → chives). Output: `menu_coverage = matched / listed`, `menu_missing = [...]`. Bottarga absent from a recipe → listed in `menu_missing`, always.

**Measure B, preparation and serving match (LLM rubric, categorical).** One LLM call per recipe receives the menu item (name, description, section) and the recipe's title, yield and a short instruction summary, and returns JSON with three graded fields and one sentence each:

| Field | Values | Meaning |
|---|---|---|
| `dish_type` | `same`, `variant`, `different` | crudo vs crudo = same; seared tuna for a crudo = different |
| `preparation` | `same`, `similar`, `different` | raw sliced vs raw cubed = similar |
| `course_portion` | `same`, `different` | a starter recipe for a starter; a main-course salad for a side = different |

Python combines them: `relevance_grade = high` if all three are `same`/`similar`, `medium` if `dish_type` is `same` or `variant` with at most one `different`, else `low`. The LLM's sentences are kept in the trace and in the scenario's provenance, never in the user reply.

**Do not force three.** Recipes graded `low` are kept in the output as *rejected* with their grade and reasons, and are not calculated. If fewer than two recipes are `medium` or better, the dish estimate says so: "only N comparable recipes were found".

## 4. Structured extraction and parsing (requirement 3)

Intermediate model `RecipeSource` (Pydantic, `extra="forbid"`):

```json
{"url": "...", "title": "...", "fetched_at": "...", "extraction": "json_ld" | "llm_text",
 "yield_text": "Serves 4", "servings": "4" | null, "servings_note": "parsed from 'Serves 4'" | "yield is '12 pieces', not servings",
 "ingredient_lines": ["85 g sushi-grade tuna, thinly sliced", "2 tbsp extra-virgin olive oil", "flaky salt, to taste"],
 "instructions_summary": "slice raw tuna, dress with oil and lemon, top with bottarga"}
```

Each line is parsed by a Python grammar into `ParsedIngredient`:

| Field | From | Rule |
|---|---|---|
| `quantity_text` | the line | as written: `2`, `1/2`, `1½`, `1-2`, `to taste` |
| `quantity` | parsed Decimal or `null` | unicode and ASCII fractions handled; **a range becomes its midpoint, flagged `range_midpoint` with both bounds recorded** (decision D3); `to taste`, `a pinch`, `as needed`, `some` → `null` |
| `unit` | normalised token | `g`, `kg`, `oz`, `lb`, `ml`, `l`, `tsp`, `tbsp`, `cup`, `fl oz`, `piece`, `clove`, `slice`, `large`, `medium`, `small`, or `null` |
| `name` | the rest, lower-cased, trimmed of preparation words | "sushi-grade tuna" |
| `preparation_words` | detached modifiers | "thinly sliced", "cooked", "raw", "toasted" |
| `preparation_state` | derived | `cooked` if the line or the recipe step for it says cooked/roasted/toasted…, `raw` if it says raw or the dish is uncooked (crudo, salad) and no cooking step mentions the ingredient, else `as_used` for oils, cheeses, condiments, seeds, bread, else `unknown` |
| `optional` | `optional`, `for serving`, `garnish` present | informational |

The LLM may be used once per recipe to **normalise names only** ("EVOO" → "extra-virgin olive oil"), returning the same number of lines; quantities and units are copied by Python from the parse, and the test checks they are unchanged.

**Servings:** `recipeYield` like "4", "Serves 4", "4 servings", "4 to 6" (→ midpoint 5, flagged) is parsed; "12 cookies", "2 cups" is not a serving count → `servings: null`, and the scenario cannot produce per-serving numbers (it stays in the output as `ineligible: servings_unknown`).

## 5. Unit normalisation (requirement 4)

Deterministic, with the factor and its reference stored on the ingredient's `assumption`:

1. **Weight units:** exact constants: 1 oz = 28.349523125 g, 1 lb = 453.59237 g, kg and g trivially. Reference: SI/NIST definitions.
2. **Volume and count units, primary source (decision D4): the matched USDA record's own `foodPortions`.** SR Legacy records list household measures with gram weights ("1 tbsp" = 13.5 g for olive oil 171413, "1 cup, chopped" for tomatoes, "1 large" for eggs). The library gains one read-only function, `get_portions(fdc_id) -> list[Portion(description, gram_weight, modifier)]`, reading `foodPortions[]` from the same detail reply the service already fetches (Phase 1A's rule "never read foodPortions *for nutrient values*" stands; this reads them for weights, in a separate function, with its own tests, and the calculator does not change). Matching a parsed unit to a USDA portion is a fixed table of unit synonyms (`tbsp` ↔ "tbsp", "tablespoon"; `cup` ↔ "cup"; `large` ↔ "large") plus modifier words when present ("chopped"). The chosen portion's description and FDC ID are recorded as the reference.
3. **Volume fallback for water-like liquids only** (water, stock, vinegar, lemon or lime juice, wine, milk): 1 tsp = 4.93 ml, 1 tbsp = 14.79 ml, 1 cup = 236.6 ml (US customary, NIST), density 1.0 g/ml, flagged `density_assumed_1`. Any other ingredient with a volume unit and no USDA portion → **grams unknown** → calculator marks it `missing_grams`.
4. **Counts without a USDA portion** ("2 chives", "1 handful") → unknown.
5. **Unknown never becomes zero.** The only zeros are explicit `0` on the page or the negligible-seasoning rule below.

**Negligible seasonings (decision D5).** "Salt, to taste" would make every recipe incomplete. A curated list (`roli_agent/recipes/negligible.json`) of ingredients whose USDA record shows saturated fat < 0.05 g and cholesterol 0 mg per 100 g (salt, black pepper, dried herbs and spices, water, vinegar, lemon and lime juice, citrus zest) may be entered as `grams: "0"` with `assumption: "negligible seasoning: USDA <id> reports <x> g saturated fat and 0 mg cholesterol per 100 g"`. Each entry cites its FDC record and the list is a test fixture. Anything not on the list with an unknown quantity stays unknown. Default: on. Trade-off: it is an assumption, but a documented one with USDA evidence, and without it no real recipe is ever complete.

## 6. Preparation state and the calculator's compatibility rule

Phase 2A's rule stands: a `raw` ingredient needs a raw USDA record, `cooked` needs cooked, `as_used` is for oils, cheeses, condiments, seeds, bread, and is refused for flesh foods. Phase 2B's job is to *declare the state honestly*, from the recipe's own words: fish in a crudo is `raw`; salmon that the steps say to roast is `cooked`, and then the matcher must prefer a cooked USDA record. When a recipe gives raw weight for something that is cooked ("600 g salmon fillet, roast 12 minutes"), the honest state is `raw` with a *cooked* preparation; Phase 2A would then flag a mismatch against a cooked record. **Decision D6:** in 2B, such lines are matched to the **raw** record and declared `raw`, so the arithmetic is on raw weight with raw values and complete; the scenario carries the flag `raw_weight_of_cooked_dish` and the user reply says "based on raw ingredient weights". No yield factor is applied. Alternative: leave them unresolved (more honest about the eaten dish, but almost every cooked recipe becomes incomplete). A cited USDA yield table (Agricultural Handbook 102) is the Phase 2C way to do better.

## 7. USDA ingredient matching (requirement 5)

Reuses the Phase 1E nodes, batched:

- **Query generation:** one LLM call per recipe takes all parsed ingredient names and returns a USDA-style query per name, plus the state hint (raw/cooked). Fewer calls than one per ingredient.
- **Search:** `service.search_foods(query, 10)` per ingredient; the service cache dedupes identical queries across recipes and dishes in a process; an on-disk JSON cache of `normalised name → (fdc_id, match_type)` persists accepted matches across runs for 30 days (decision D7, default on).
- **Selection:** one LLM call per recipe receives every ingredient's candidate list and returns, per ingredient, `{fdc_id or null, match_type: "direct" | "proxy", reason}`. Python applies the Phase 1E guard (an ID not in that ingredient's candidate list is rejected → unresolved) and a state check (a `raw` ingredient may not be matched to a record the classifier calls `cooked`, and vice versa; such a selection is rejected as `state_conflict` and the ingredient is unresolved).
- **Match types, tracked per ingredient and surfaced in the output:**
  - `direct`: the USDA description names the same food and form (bluefin tuna raw → "Fish, tuna, fresh, bluefin, raw").
  - `proxy`: a stand-in the LLM declares as such (pecorino sardo → "Cheese, romano"; little gem → "Lettuce, cos or romaine, raw"; bottarga → "Fish, roe, mixed species, raw" if chosen). Proxies count in the arithmetic but every scenario's output lists them, and a scenario whose *largest* contribution comes from a proxy is graded `representativeness: proxy_dependent`.
  - `unresolved`: no candidate, LLM declined, guard rejected, or USDA failed. Counts as `missing_fdc_id` in the calculator.
- **Relevance test set (deliverable):** `menu_reader_eval/usda_matching/` with about 40 rows: `ingredient_text, menu_context, expected_fdc_id, accepted_proxies[], notes`, built from the Flour + Water menu (bottarga, pecorino sardo, little gem, burrata, boquerones, castelvetrano olives, fior di latte, caciocavallo…), the salmon cases, and 15 common ingredients. Metrics: direct-match accuracy, proxy-acceptable rate, **false-match rate** (a confidently wrong food, the error that matters most), unresolved rate. Target to report, not to pass: false-match rate under 5%.

## 8. Menu-only ingredients and the "nothing vanishes" rule (requirement 2)

After extraction, Python compares the menu's listed ingredients (Measure A) with each recipe's parsed names. Every menu ingredient absent from a recipe is **appended to that recipe as a line** `{name, grams: null, fdc_id: matched or null, preparation_state: as declared or unknown, assumption: "listed on the menu, not in this recipe; quantity unknown"}`. The calculator then marks the scenario incomplete with `missing_grams` for that line, and the reply names it (decision D8, default on). Consequence: a dish whose signature ingredient appears in no published recipe (bottarga on the crudo) never gets a "complete" scenario; the estimate shows known subtotals and says what is missing. That is the intended behaviour: Phase 2A's rule that a partial subtotal is never a total applies to scenarios built by machine exactly as to ones typed by hand.

## 9. Output: `DishEstimate`

```json
{
  "menu_item": {"name": "BLUEFIN CRUDO", "description": "bottarga, muscat grape, chive", "section": "TO START"},
  "scenarios": [
    {"source": {"url": "https://…", "title": "Tuna Crudo with Bottarga", "extraction": "json_ld", "yield_text": "Serves 4", "servings": "4"},
     "relevance": {"menu_coverage": "1.0", "menu_missing": [], "dish_type": "same", "preparation": "same", "course_portion": "same", "grade": "high"},
     "matches": {"direct": ["tuna", "olive oil", "chives"], "proxy": [{"ingredient": "bottarga", "fdc_id": 173701, "description": "Fish, roe, mixed species, raw"}], "unresolved": []},
     "conversions": [{"ingredient": "olive oil", "from": "2 tbsp", "grams": "27", "reference": "USDA 171413 portion '1 tbsp' = 13.5 g"}],
     "flags": ["range_midpoint:grapes"],
     "calculation": { "…the Phase 2A RecipeResult, unchanged…" },
     "eligible_for_range": true,
     "representativeness": "high" | "medium" | "proxy_dependent" | "low"},
    {"source": {"url": "…"}, "relevance": {"menu_coverage": "0.67", "menu_missing": ["bottarga"], "grade": "medium"},
     "calculation": {"status": "incomplete", "…"}, "eligible_for_range": false, "ineligible_reason": "incomplete: bottarga quantity unknown"},
    {"source": {"url": "…"}, "relevance": {"grade": "low", "dish_type": "different"}, "rejected": true, "rejected_reason": "seared tuna, not crudo"}
  ],
  "comparison": { "…Phase 2A ComparisonResult over the eligible scenarios…" },
  "summary": {"n_found": 6, "n_fetched": 5, "n_relevant": 2, "n_complete": 1, "range_meaningful": false,
              "statement": "Only 1 comparable recipe could be calculated completely; evidence is insufficient for a range. Based on raw ingredient weights. Not a verified restaurant value."},
  "cost": {"search_calls": 1, "pages_fetched": 5, "llm_calls": 9, "llm_tokens": 41000, "usda_searches": 11, "usda_lookups": 9, "seconds": 38.2}
}
```

Every number in `calculation` and `comparison` is the Phase 2A object; the LLM's text appears only inside `relevance` sentences in the trace and provenance, never in the user-facing `statement`, which Python assembles from templates.

## 10. Complete versus representative

These are different questions and the output keeps them apart:

- **Arithmetically complete** (Phase 2A `status`): every line in *this recipe* has grams, a USDA record, a compatible state and reported nutrients. A recipe for a plain seared tuna steak can be complete and useless for a crudo.
- **Representative of the menu dish** (Phase 2B `relevance` and `representativeness`): the recipe names the same dish type and preparation (Measure B), covers the menu's listed ingredients (Measure A), and does not lean on proxies for its biggest contributor.

A scenario enters the range only if it is complete **and** graded `medium` or better. The summary reports both counts separately ("5 recipes fetched, 2 relevant, 1 complete") so a reader can see which filter removed what. When relevance is high but completeness fails because of a menu-only ingredient, the reply says exactly that: "the published recipes do not include bottarga, so the figures cover the other ingredients only". When completeness is fine but relevance is low across the board, the reply says no comparable recipe was found and gives no numbers. Neither case is ever smoothed into a single figure.

## 11. Reliability (requirement 8)

Phase 1E rules apply to every step: an LLM parse failure, a fetch error, a USDA error or a guard rejection is recorded on the scenario and the pipeline continues with the others; a dish with zero eligible scenarios produces a `DishEstimate` whose `comparison` is empty and whose statement says so; no step may fall back to another nutrition source; web pages' nutrition blocks are never read; the reply template prints only numbers that exist in the comparison object, and a test scans every reply for numbers and checks each against that object.

## 12. Efficiency and measurement (requirement 9)

**Calls per dish, default budget:** 1–2 search calls; ≤ 8 fetches (cached on disk); LLM calls: 1 query writer, 0–3 extraction fallbacks, ≤ 3 name normalisations, ≤ 3 relevance gradings, ≤ 3 USDA query batches, ≤ 3 selection batches → about 8 to 16, each small (no images, short JSON); USDA: one search per *distinct* ingredient name across the three recipes (typically 10–15) and one lookup per distinct FDC ID, both deduplicated by the service cache and the on-disk match cache.

**Reductions built in:** batching per recipe instead of per ingredient (≈ 3× fewer LLM calls than Phase 1D's agent), the match cache across dishes (olive oil, salt, garlic, lemon recur everywhere), fetch cache, and no LLM call on the arithmetic or reply.

**Measurement plan:** every stage writes one JSON log line `{dish, stage, seconds, llm_tokens_in/out, llm_cost_usd (from OpenRouter usage), usda_requests, cache_hit}`; `scripts/measure_2b.py` runs the pipeline on five Flour + Water dishes, twice (cold and warm cache), one at a time, and reports per-stage p50/p95 seconds and cost per dish. Targets to report, not gates: under 60 s and under $0.10 per dish cold; under 20 s warm.

## 13. Evaluation plan (requirement 10)

Offline tests use **saved recipe pages**: for each test dish, three real pages fetched once by `scripts/capture_recipe_pages.py`, stored as the extracted JSON-LD (or the text extract) plus URL and fetch date in `roli_agent/tests/fixtures/recipes/`. Ingredient lists are facts, not creative text, so storing them is fine; full HTML is not stored. LLM steps are scripted as in Phase 1E tests; USDA is the saved fixtures plus the new portions data.

| Area | Tests |
|---|---|
| Omission | Bluefin Crudo: a recipe without bottarga gets a `menu_missing` entry and an appended unknown-quantity line; the calculation is incomplete; the statement names bottarga. No code path can drop a menu-listed ingredient (property test over random menu lists). |
| Proxy matching | pecorino sardo → romano flagged `proxy`; little gem → romaine `proxy`; a scenario whose largest contribution is a proxy is `proxy_dependent`; the false-match test set runs as a scored evaluation with a report. |
| Quantities | "1½ cups", "1-2 tbsp" (midpoint flagged), "to taste" (unknown), "2 large eggs" (USDA portion), "a handful" (unknown); the LLM name-normalisation step cannot change a quantity. |
| Conversion accuracy | tbsp olive oil → 13.5 g from USDA portion; oz → g exact; cup of water → 236.6 g flagged; cup of flour with no portion → unknown; negligible seasonings → `0` with citation. |
| Incomplete estimates | one complete scenario → `range_meaningful: false`; all incomplete → empty comparison and a no-numbers statement; mixed → range over eligible only, incomplete named. |
| Extraction | JSON-LD page parsed without the LLM; a page without JSON-LD uses the scripted LLM and every returned line is a substring of the text; a page with a `nutrition` block never leaks those fields into state. |
| Relevance | a seared-tuna recipe for the crudo is graded `low` and rejected; "do not force three" when only two pass. |
| Reliability | fetch timeout, robots disallow, search API error, USDA 503, LLM garbage: each recorded, pipeline continues, no numbers invented; reply numbers all exist in the comparison object. |
| End to end | five Flour + Water dishes (Bluefin Crudo, Little Gem Lettuces, Heirloom Tomatoes, Margherita, King Salmon) through the whole pipeline on fixtures; plus one live run per dish for the checkpoint with latency and cost. |

## 14. Where the code lives

`roli_agent/recipes/`: `search.py` (SearchClient, Tavily implementation), `fetch.py` (cache, robots), `extract.py` (JSON-LD, LLM fallback), `parse.py` (line grammar), `convert.py` (units, USDA portions, negligible list), `match.py` (batched 1E path, match cache), `relevance.py` (coverage, rubric), `pipeline.py` (orchestration → `DishEstimate`), `models.py`. In `nutrition_service/roli_nutrition/`: `portions.py` with `get_portions()` and its tests (the only library change; the calculator is untouched). Graph: a `estimate_dish` node reachable with `run_roli(menu_item={...})`, plus the deterministic reply template; menu-wide ranking stays out of scope.

## 15. Decisions (Julius, 2026-11-02)

| # | Decision | Outcome |
|---|---|---|
| D1 | Search / recipe source | **Decided after 2B-0 (2026-11-02): Tavily search + public recipe-page extraction** behind the `RecipeSource` interface; no structured recipe API in this phase; site-level access and content-use restrictions respected (robots.txt, bounded back-off, no bypassing). |
| D2 | Extraction | Native structured fields from an API where available; for web pages schema.org JSON-LD / `recipe-scrapers` first, then validated LLM extraction only when necessary. **Both paths produce the same normalised recipe format.** |
| D3 | Quantity ranges | Midpoint with both bounds recorded and an explicit assumption flag. Unknown quantities never become zero. |
| D4 | Volume to grams | Prefer the matched USDA record's portion weights; deterministic, documented factors with source recorded. **Pipeline order fixed: explicit weight units are parsed immediately; USDA-dependent volume and count conversions run only after USDA matching.** Density fallbacks restricted to liquids with defensible assumptions, each recorded as an approximation. |
| D5 | Negligible seasonings | Narrow, validated list, preferably where both tracked nutrients are actually zero in the USDA record. **The original unknown quantity is preserved** (`grams_declared: null`) and the line carries an explicit `modeled_zero` assumption; it is never presented as a measured zero. Documented in results and tests. **Not implemented in 2B-1** (kept with D11 for review after the first extraction checkpoint); 2B-1 leaves every unknown quantity unknown. |
| D6 | Raw weights of cooked dishes | Allowed with the raw USDA record when the recipe gives raw weights. Scenario flagged "based on raw ingredient inputs, not a verified cooked-dish composition". **No implication that cooking losses, fat absorption or added cooking fat are accounted for; uncertainty about how much cooking fat is consumed is recorded.** |
| D7 | Match cache | Keyed by normalised name **plus preparation state, food form and material context**; only validated decisions are cached; a cached proxy is never reused as a direct match; cache behaviour must respect the provider's terms. |
| D8 | Menu-only ingredients | Appended as unresolved lines with unknown quantities; never omitted. |
| D9 | Checkpoints | **Three:** 2B-0 source evaluation and architecture choice; 2B-1 ingestion, extraction, parsing, conversions; 2B-2 USDA matching, relevance, calculation integration, LangGraph, end-to-end evaluation. Stop for approval after each. |
| D10 | Eligibility | Arithmetic completeness **and** sufficient representativeness, **with hard exclusions for major preparation mismatches** (seared tuna for a crudo is out regardless of other grades). **Menu ingredient coverage affects eligibility directly**; similar dish type and course alone never qualify a recipe. Proxy substitutions are weighted by their effect on saturated fat and cholesterol, not treated as equally reliable. |

Additional standing requirements: the Phase 2A arithmetic is unchanged; nutritional values returned by recipe APIs or websites are never accepted as USDA-verified and never enter the calculation; provenance is preserved for every recipe and quantity (source URL, stated yield, transformations, approximations, USDA record selection); the benchmark measures how often each source yields **usable, complete scenarios**, not merely how many recipes it returns.

### 15.0 Decisions after Phase 2B-0 (Julius, 2026-11-02)

| # | Decision | Outcome |
|---|---|---|
| D11 | Menu-only garnishes | **Not approved as proposed.** No modeled-zero for unknown grams and no completeness bypass in Phase 2A. Future approach to document, not build in 2B-1: *menu-adapted scenarios* that assign explicit, plausible assumed weights to eligible missing ingredients, retrieve their USDA records and calculate real contributions with the unchanged calculator; such scenarios must separate source-reported quantities from modeled assumptions, must not be presented as published recipes, and must treat low-impact herbs differently from substantial fruit or vegetable components. Until reviewed, unknown quantities stay unknown. |
| D12 | Search modes | **Approved:** open and domain-restricted Tavily searches; results deduplicated by canonical URL and, where practical, equivalent recipe content; each source records which mode(s) found it. |
| D14 | Spoonacular comparison | **Skipped.** |

Additional requirements for 2B-1: canonical-URL and content deduplication; bounded per-host back-off on 429, robots rules respected, no bypassing; original ingredient lines, yields and URLs preserved beside parsed values; extracted quantities kept separate from any future modeled assumptions; the Phase 2A calculator and its completeness rules unchanged; statistics on the share of recipes with usable quantities and serving yields, not only extraction success; for recipes containing bottarga, verify distinctness and credibility as matches for the menu crudo.

### 15.2 Decisions for Phase 2B-2 (Julius, 2026-11-02, after Checkpoint 2B-1)

| # | Decision | Outcome |
|---|---|---|
| D5 | Negligible seasonings | **Deferred.** No modeled zero: an unknown weight is never represented as 0 g to make a recipe complete, because a low-but-nonzero concentration is not zero. 2B-2 **measures** how many otherwise complete scenarios are blocked solely by low-impact seasonings ("salt, to taste") and reports it separately (`Scenario.complete_except_seasonings`, `DishSummary.blocked_only_by_seasonings`; the seasoning list in `pipeline.py` is measurement-only). The 2B-2 checkpoint proposes a narrow solution that distinguishes genuinely zero-nutrient ingredients from low-but-nonzero ones; Phase 2A completeness rules are not modified without review. Section 5's "negligible seasonings" paragraph is superseded. |
| D11 | Menu-adapted scenarios | **Documentation only** (`roli_agent/PHASE_2C_proposal.md`): a future Phase 2C adds missing menu ingredients with explicit, plausible assumed weights and calculates them with the unchanged Phase 2A calculator. Not implemented in 2B-2. |
| D15 | Yield fallback | **Approved.** When structured `recipeYield` is missing, an explicit serving count is recovered from the page's own visible text (`recover_yield_from_text`: a regex match is verbatim by construction; only serving words count). Never inferred from pizzas, slices or items; `yield_source` records where the yield came from. |
| D16 | Listicles | **Approved with refinement.** Clearly identified listicles and non-recipe collections are excluded by the Python gate before any USDA or LLM work, with the reason preserved (`listicle_or_collection:no_quantities`, `listicle_or_collection:title`). A genuine recipe with some unquantified lines is never rejected for that; it is calculated and comes out incomplete. |
| D17 | Refusing hosts | **Approved.** robots.txt and access restrictions respected; bounded 429 retries kept; a host that refuses scripted access (401/403/451) twice within a week is not asked again that week (`RefusalMemory`, persisted beside the page cache). No bypassing. |
| D19 (taken in 2B-2, to confirm) | Record preference | When an SR Legacy and a Foundation candidate name the same food in the same state, the selection prompt asks for the SR Legacy record: it carries household measures and both tracked nutrients. The guard is unchanged. Evidence in `CHECKPOINT_2B2.md` section 6f. |
| D18 (proposed) | Proxy dependence | A scenario whose substitute (proxy) records supply more than 50% of a nutrient's known subtotal is `proxy_dependent` and **does not enter the range**; one whose largest single contributor is a proxy but stays at or under 50% is marked `proxy_dependent` and stays eligible. Proxy shares are reported per nutrient. Awaiting Julius's confirmation of the threshold. |

Requirements for 2B-2 and where each is met:

1. **Relevance filtering before expensive operations.** `relevance.gate` (Python, free) rejects listicles, recipes that do not name the dish (pasta with bottarga for a crudo, a margarita cocktail for a margherita pizza) and cooked titles for raw dish types; only gated-in recipes reach the one LLM rubric call per dish, and only graded-in recipes reach USDA matching.
2. **USDA matching.** `match.UsdaMatcher` reuses the validated search-and-select path (`service.search_foods`, the shared guard `roli_agent/selection.py`, the state check) in batches; every ingredient is `direct`, `proxy` or `unresolved`; `menu_reader_eval/usda_matching/matching_set.csv` (44 rows) and `scripts/score_matching.py` measure direct accuracy, proxy acceptability, false-match rate and unresolved rate.
3. **Unit conversion.** Weight units exact (2B-1); embedded weights ("1 (14 oz) can", "2 (6-ounce) fillets") read explicitly with the per-item/total rule recorded; volumes and counts from the matched record's `foodPortions` through the library's new read-only `get_portions()`; every conversion keeps the source text, factor and reference (`Conversion`).
4. **Preparation.** The state declared to the calculator comes from the recipe's words and the chosen record's state (`preparation_state_for`); raw weights of ingredients the recipe cooks are calculated raw with the raw record and flagged `raw_weight_of_cooked_dish` (D6); no cooking yield or retention factor anywhere.
5. **Menu coverage.** Missing menu ingredients are appended as unresolved lines (D8); `Relevance` (representativeness) and `calculation_status` (arithmetic completeness) are separate fields, and the summary counts them separately.
6. **Scenario comparison.** Only complete, relevant (grade high/medium, no hard exclusion) and not proxy-dependent scenarios enter the Phase 2A comparison; fewer than two gives `range_meaningful: false` and the statement says the evidence is insufficient.
7. **Efficiency.** `metrics.Meter` records seconds per stage, LLM calls by stage, tokens, provider-reported cost, USDA service calls, HTTP requests and cache hits; `scripts/measure_2b2.py` reports cold and warm runs separately.
8. **Evaluation.** The same script runs the five Flour + Water dishes and prints discovered / relevant / calculable / eligible counts with exclusion reasons.
9. **Quality safeguards.** USDA-only numbers (the page `nutrition` block is never read; test), the Phase 2A arithmetic untouched (its 292 tests unchanged; `test_calculator_does_not_import_portions`), explicit error handling at every step (tests for USDA outage, LLM garbage, guard rejection, missing key), deterministic replies (`responses.dish_reply`; the reply-number guard test).
10. **Future development.** `roli_agent/PHASE_2C_proposal.md`.

Deviations from the body text, decided during 2B-2: the relevance rubric is one batched LLM call per dish (section 3.3 said one per recipe); query writing and record selection are batched across all chosen recipes of a dish (up to 20 ingredients per call) rather than per recipe; up to four scenarios are calculated per dish (`MAX_SCENARIOS`), the rest recorded as `beyond_scenario_cap`; menu-only words are also sent through matching so their USDA record is known for Phase 2C.

### 15.3 Decisions for Phase 2B-2.1 (Julius, 2026-11-02, after Checkpoint 2B-2)

| # | Decision | Outcome and implementation |
|---|---|---|
| D18 | proxy dependence | **Provisionally approved** at 50 % of a nutrient's *known subtotal*; an initial threshold to validate, not evidence that smaller proxy shares are accurate. Scenarios now carry `proxy_contribution` (absolute, per nutrient), `proxy_share` and `proxy_share_percent` with `proxy_share_basis: "known_subtotal"`, `largest_contributor_is_proxy` per nutrient and the flag `proxy_largest_contributor`; the reply says "of the known subtotal" for incomplete scenarios. |
| D19 | SR Legacy preference | **Approved with qualification:** only when the two records name a genuinely equivalent food and state; never at the cost of food specificity or preparation accuracy. The selection prompt says so. |
| D20 | ambiguous portions | **Modified:** no median, no default size. A portion is used when unit, food form and modifier match unambiguously; a stated size ("1 large orange") picks that size; a record that lists sizes while the line names none leaves the weight unresolved (`portion_size_unspecified`). A record whose only whole-item label is unsized ("1 fruit", "1 clove", "1 pepper") matches a bare count (`portion_whole_item`). Semantically different labels (fruit vs wedge, leaves vs ground) are never averaged. Explicit size assumptions belong to a separate modeled scenario (Phase 2C). |
| D21 | proxy portions | **Approved with qualification:** whole-item weights of a proxy record are never used (`proxy_count_portion_refused`); a proxy's volume measures are accepted only for volume lines, flagged `proxy_volume_portion` and marked an approximation in the reference. |
| D5 | zero-nutrient assumption | **Approved in principle for Phase 2C, not now:** only where a validated record reports 0 for both nutrients; the unknown weight is preserved and any calculation weight recorded separately; a missing value is never 0; USDA zeros are reported values at USDA's precision. Specified in `SPEC_2C_menu_adapted_scenarios.md` section 3. |
| 2C | direction approved, implementation deferred | revised specification `SPEC_2C_menu_adapted_scenarios.md`; modeled ranges to stay internal (recommendation agreed). |

Corrections built in 2B-2.1: inline weights after a count ("One 8-ounce loin") take precedence over the count (`inline_weight`); cubic-inch, slice, strip and similar labels never serve a bare count; proxy portion rules above; extraction results cached per page and content (`ExtractionCache`, beside the page cache, same 30-day life) so the LLM fallback runs once per unchanged page; a held-out matching set with frozen labels (`menu_reader_eval/usda_matching/heldout_set.csv`, README with hash). Phase 2A arithmetic and every missing-data safeguard unchanged.

### 15.4 Decisions after Checkpoint 2B-2.1 (Julius, 2026-11-02)

| # | Decision | Outcome and implementation |
|---|---|---|
| D22 | equivalent record with usable measures | **Approved with safeguards; built as a deterministic policy** (`roli_agent/recipes/equivalence.py`), applied only when the chosen record cannot weigh the line: the replacement must come from the same search's candidate list, name the same food (first two description words), be in the same preparation state, both records must report both nutrients with equivalent values (|Δ| ≤ max(0.1 g / 1 mg, 5 %)), and the replacement must actually convert the line. Grade or varietal differences are judged on the numbers, not assumed irrelevant. Result on the documented case: the real "Oil, olive, extra virgin" (748608) reports 15.4 g saturated fat and no cholesterol row against 13.808 g / 0 mg for 171413, so the policy **refuses** the substitution (test). The olive-oil lines are instead converted from the Foundation record's own "100 milliliter = 90.7 g" measure (D4: the matched record's own measure; millilitre measures are now read as density sources). |
| D21 edge | same-family proxies | **Conservative rule retained:** a composition proxy's whole-item weight is never used, same family or not; such quantities stay unresolved until a validated, context-appropriate portion reference or an explicitly reviewed weight exists (Phase 2C table). |
| held-out set | versioning | v1 and its results preserved untouched; v2 (`heldout_set_v2.csv`, 54 rows, changelog `heldout_CHANGELOG.md`) applies only the ghee change (after live verification of USDA 173412), makes the foie gras wording explicit without relabelling, keeps mascarpone a false match and gorgonzola a proxy, adds 14 consequential-proxy rows and a `consequence` column; the scorer reports the false-match rate among high-consequence rows. |
| 2C | specification revision 2 | `SPEC_2C_menu_adapted_scenarios.md`: classes computed from the record and the upper bound, weights table with review status per row and the questionable proxies blocked, 30 % as a diagnostic flag with absolute sensitivity, low/high pairs as one entity, recipe-basis only, Phase 2D defined. |

### 15.5 Decisions after Checkpoint 2B-2.2 (Julius, 2026-11-02)

| # | Decision | Outcome |
|---|---|---|
| D22 | equivalent-record policy | **Approved** as built (six safeguards, volume lines only); a record's own millilitre measure approved as a density reference with the conversion recorded. |
| D23 | nutrient from a sibling record | **Not approved.** A missing USDA nutrient is never filled from another record (same-record provenance). Completeness is tracked per nutrient (`completeness_by_nutrient` on scenarios and adapted scenarios; `n_saturated_fat_only_complete` in the summary) so a future ranking can treat "saturated fat complete, cholesterol unreported" differently from "neither". The calculator's completeness logic is unchanged. |
| held-out | v3 | v1 and v2 preserved; v3 applies only ghee (exact record 171314 verified, direct), reviews bresaola (stays proxy) and dry vermouth (direct) against their exact descriptions, keeps 'nduja -> salami and fresh foie gras -> canned pâté as false matches; one bounded plain-name retry when the model's query returns no USDA candidates, under the same guards (`retried_with_plain_name`). |
| 2C | internal implementation | Approved with twelve refinements; built (`roli_agent/recipes/adapt.py`, `SPEC_2C_menu_adapted_scenarios.md` revision 3). Phase 2D (restaurant portion model) stays a separate future phase. |

### 15.6 Decisions after Checkpoint 2C (Julius, 2026-11-03): Phase 2C.1

| # | Decision | Outcome |
|---|---|---|
| 1 | 2C architecture | **Approved.** Safeguards kept; adaptation off by default; Phase 2A arithmetic unchanged. |
| 2 | assumption classes | **Approved for internal diagnostics.** Display and materiality classes kept; the materiality tiers are not validated clinical significance or verified nutritional uncertainty. |
| 3 | 30 % share rule | **Approved as a warning only**, with absolute sensitivity and the known-subtotal basis reported. |
| 4 | weights table | **Stays unapproved.** No `approved_by` changed; experimental diagnostics may use proposed rows; trusted ranges and user-facing figures may not. |
| 5 | D23 | **Unchanged.** A missing nutrient is never borrowed from another record; prefer accurate source selection and per-nutrient completeness reporting. 2C.1 adds **D24 (proposed, off by default)**: completeness-aware *selection* among same-food candidates, see `roli_agent/recipes/completeness.py` and Checkpoint 2C.1 section B. |
| 6 | Phase 2D | **Stays separate.** Specification written (`SPEC_2D_restaurant_portions.md`), nothing implemented. |

Phase 2C.1 work (requirements A-F) and its measurements: `roli_agent/CHECKPOINT_2C1.md`.

### 15.7 Decisions after Checkpoint 2C.1 (Julius, 2026-11-03): Phase 2D

| # | Decision | Outcome |
|---|---|---|
| 1 | Phase 2C.1 | **Approved as complete.** Guiding principle: first the most complete, source-grounded total possible; when inputs stay unknown, explicit, defensible assumptions, and a judgment whether the evidence still supports a credible comparison. |
| 2 | D20 (ambiguous whole-item sizes) | **Revised.** A bare count on a record that lists the same item in several sizes takes the **median** of those comparable whole-item weights, flagged `assumed_size_median`, with the range and the labels preserved (`convert.median_whole_item`). Garlic keeps its exact 3 g clove. Unlike labels (a whole lemon and a wedge; a sized item beside an unsized one) are never combined. Source-stated weights and modeled assumptions stay distinguishable (`Scenario.basis`, `Inference`). |
| 3 | Olive oil / D24 | **D24 at 15 % not enabled.** Instead a narrow, evidence-backed cholesterol-zero **inference** for verified pure olive oil (`inference.py` rule I01): the Foundation saturated-fat value stays, the absent cholesterol field is recorded, the inferred zero is labelled with its reference, outside the calculator; source-reported totals and totals with documented inferences are told apart. Not extended to other foods (rule I02 for vinegar written, disabled). |
| 4 | Relevance | **Sufficient to proceed.** Frozen evaluation preserved; an independent review of the reference labels by a second model arranged (`menu_reader_eval/relevance/independent_review_2026-11-03.md`), preparation mismatches first; no new relevance phase unless it finds material problems. |
| 5 | Specialty ingredients | **Flagged proxies, supported approximations, uncertainty allowed.** Rows W28b, W20b, W03c added from the 2C.1 evidence as `proposed_from_evidence_2c1` (experimental only); bottarga stays blocked and is bounded only by labelled external evidence in the comparison; nothing forced complete. |
| 6 | Phase 2D | **Build it** on the specification: P1 (pizzas), P3 (dominant protein), experimental P2 (salads); recipe and restaurant portions separate; explicit low/high; completeness preserved; arithmetic validated on controlled recipes first, then the five dishes; Phase 2A untouched. Then a minimal internal dish-comparison prototype for the five dishes, evaluated against human-reviewed expectations. Estimates internal; no Telegram or user interface. Stop at Checkpoint 2D. |

Phase 2D work and its measurements: `roli_agent/CHECKPOINT_2D.md`; the specification's as-built section: `SPEC_2D_restaurant_portions.md` section 9.

### 15.8 Decisions after Checkpoint 2D (Julius, 2026-11-03): Phase 3

| # | Decision | Outcome |
|---|---|---|
| 1 | Phase 2D | **Approved as complete.** Principle: a complete, source-grounded total where possible; otherwise a useful comparison on explicit, credible assumptions, uncertainty never disguised as certainty. |
| 2 | Rule I01 (olive-oil cholesterol zero) | **Approved.** The record's absent field stays recorded (`inference.py`). |
| 3 | Rule I02 (plain vinegar) | **Conditionally approved**, enabled with the evidence documented in the rule (USDA 173469 cider and 172237 distilled vinegar report 0 mg; the wine and balsamic records omit the row): bare `Vinegar, <kind>` records and lines naming vinegar only; dressings, sauces, glazes and mixtures excluded by pattern; flagged as an inference. |
| 4 | Pizza unit yields | **Approved.** "One 12-inch pizza" / "makes two pizzas" give the recipe basis one serving per unit (`ingest`, flag `servings_from_unit_yield`) and the P1 unit count; a diameter or a slice count is never a unit or serving count. |
| 5 | Portion rules and weights rows | **Permitted in an explicitly experimental, invited-testing mode.** No `approved_by` filled; never presented as verified restaurant quantities (banner on every page). |
| 6 | External evidence bounds | **Retained as modeled upper estimates with provenance, not guaranteed limits.** A disjoint pair that rests materially on them is `tentative`, not `well_supported` (`compare_dishes`). |
| 7 | Phase 3 | **Build the MVP for invited testers** (`SPEC_3_mvp.md`): menu photo in, up to three recommendations out (saturated fat first, cholesterol second, 80 words or fewer), web interface, diagnostics, feedback, evaluation on the five dishes and unseen menus, cost/latency/consistency, deployment recommendation; Telegram later. Stop at Checkpoint 3. |

Phase 3 work and its measurements: `roli_agent/CHECKPOINT_3.md`.

### 15.1 Phase 2B-0: source evaluation (new)

Before 2B-1, compare on the five dishes (Bluefin Crudo, Little Gem Lettuces, Heirloom Tomatoes, Margherita, King Salmon): relevant recipes returned; closeness to the menu dish in ingredients, preparation and serving type; availability of usable quantities, gram weights and servings; access to preparation steps; transformations and LLM calls needed before a recipe can enter Phase 2A; cost per query, latency, access limits, licensing; whether caching, storing responses and building test fixtures are permitted. Inspect real responses or permitted sample payloads and show their mapping to `RecipeInput`; no purchases without approval; no fabricated measurements. Outcome: one of (a) structured API primary with web fallback, (b) several structured APIs with web fallback, (c) web extraction primary.

**Result (2026-11-02, `roli_agent/CHECKPOINT_2B0.md`):** recommendation (c). Spoonacular and Edamam terms forbid storing ingredient data (no real-response fixtures, no match cache, no provenance of quantities); Edamam has no free plan; TheMealDB has no coverage and no serving counts. Live Tavily benchmark (10 searches, key already in `.env`): 41 of 71 fetched pages extractable, 33 of 41 state servings, three crudo recipes contain bottarga; first sample: 78% of ingredient lines are volume or count units. Proposed refinements D11 (menu-only herb and fruit garnishes as cited modeled-zero lines) and D12 (domain-restricted plus open search) await Julius's decision.

## 16. Implementation plan

0. **Phase 2B-0:** source evaluation and architecture recommendation (`roli_agent/CHECKPOINT_2B0.md`). **Stop.**
1. Keys and clients: `TAVILY_API_KEY` in `.env`; `SearchClient`, fetch cache, robots check; capture three pages for each of five test dishes (fixtures).
2. `extract.py`, `parse.py`, `convert.py` with `get_portions()` in the library and the negligible list; tests from section 13 rows Quantities, Conversion, Extraction. **Checkpoint 2B-1.**
3. `match.py` on the batched 1E path with the guard and state check; the relevance test set and its scorer; `relevance.py`.
4. `pipeline.py`, menu-only injection, calculator call, comparison, `DishEstimate`; graph node and reply template; reliability tests; reply-number guard.
5. `scripts/measure_2b.py`; five live dish runs; **Checkpoint 2B-2** with the cost table, the relevance test-set scores, and the five estimates.

Nothing in `code/`, the MCP wrapper, the LangSmith prototype or the Phase 2A arithmetic changes. No deployment.
