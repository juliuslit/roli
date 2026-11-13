# Checkpoint 2B-0: recipe source evaluation and architecture recommendation

Date: 2026-11-02. Scope: `SPEC_2B_recipe_scenarios.md` section 15.1. Status: **evaluation complete, including live Tavily searches (addendum, section 2b, 2026-11-02); stopped for the source-strategy decision. No Phase 2B-1 code written.**

Correction: the first version of this report said no Tavily key existed. `TAVILY_API_KEY` was already in `roli/.env`; I had not re-checked the file since Phase 1B. Section 2b fills the gap that error left, and former decision D13 is withdrawn.

## 1. Recommendation in one paragraph

**Web extraction as the primary source (option c), behind the `RecipeSource` interface, with no structured recipe API in this phase.** The deciding evidence is licensing, not coverage: Spoonacular's terms forbid storing any ingredient data beyond a one-hour cache and require deleting everything on termination; Edamam's terms allow caching only four nutrients plus id, title and image and say response data "can not be stored unless explicitly permitted". Both rule out saved real-response test fixtures, the 30-day match cache, and provenance records that keep the quantities we calculated from, all of which the spec requires. Edamam also no longer has a free plan ($9/month, 10-day trial). Public recipe pages carry no such restriction on recording the factual ingredient lines we extract, and schema.org Recipe data was present on 13 of the 23 pages that could be fetched. The costs are real and measured on Tavily's own results (section 2b): across 10 searches, 71 pages were fetched, 64 answered, 41 yielded an ingredient list (58%), 33 of those stated a serving count (80%); a handful of hosts rate-limited (429) or refused (403) scripted fetches. Structured APIs should stay as an optional, non-cached, online-only comparison source behind the same interface if Julius later supplies a key, not as a tested dependency. TheMealDB is not useful beyond a smoke test: 0 results for crudo, little gem or heirloom tomato, no serving count field, free-text measures like "Drizzle" and "Pinch".

A second finding matters more than the provider choice: **arithmetically complete, representative scenarios will be uncommon for restaurant dishes, and the garnish rule decides how uncommon.** Of 41 recipes extracted from Tavily's results, one contained every menu-listed ingredient (a Margherita). Every tomato-salad recipe lacked pluot; every salmon recipe lacked shishito; three crudo-search results contained the word bottarga and lacked only the grape and chive garnishes (**withdrawn in section 2c: none of the three is a crudo**). Under D8 alone these menu-only ingredients become unknown-quantity lines, so most estimates would be "at least X, missing: …". With the D11 refinement (section 6), the Margheritas and several tomato salads would become complete and representative, while any dish missing a material ingredient (bottarga, a cheese, an oil) stays incomplete.

## 2. What was evaluated and how

| Source | What I could inspect without a key | What needs a key |
|---|---|---|
| **TheMealDB** | live calls with the public test key `1` on 8 queries for the five dishes; one full payload | nothing (free) |
| **Spoonacular** | terms page, pricing page, API docs incl. example JSON for `complexSearch` and `GET /recipes/{id}/information` | live coverage for the five dishes (free plan: sign-up, 50 points/day, no card) |
| **Edamam Recipe Search v2** | plan page, docs page (response fields), terms page (returned empty twice) | live coverage (no free plan; $9/month EnterpriseBasic with a 10-day trial) |
| **Tavily + web extraction** | Tavily pricing and terms pages; extraction measured on 30 URLs from my search tool, then on 71 URLs from 10 live Tavily searches (section 2b), using `recipe-scrapers` 15.13.0 (MIT) in a scratch environment | nothing: the key was already in `.env` |

The first benchmark (section 5) used 30 URLs from my own web search tool. The addendum (section 2b) repeats the measurement on Tavily's actual results for the same five dishes, two search modes each, 10 credits in total.

Evidence files: `roli_agent/source_eval/web_extraction_bench.py` (the script) and `web_extraction_results_2026-11-02.json` (every URL with status, structured-data flag, line counts, yield, menu-ingredient coverage).


## 2b. Addendum: live Tavily searches (10 credits)

Script and raw results: `roli_agent/source_eval/tavily_bench.py`, `tavily_results_2026-11-02.json`. For each dish, one open search and one restricted with `include_domains` to 18 publishers known to carry schema.org Recipe data; up to 8 results fetched per search after dropping video, social, retail and paywalled hosts. "Usable" means an ingredient list was extracted deterministically. "Missing" is a plain substring check against the menu's ingredient words and over-counts: "fior di latte" is missing wherever a recipe says mozzarella, "tomato" where it says passata or San Marzano; the real pipeline's coverage measure uses token matching plus a synonym table.

| Dish | Mode | Search s | Fetched | 200 | Usable | With servings | Menu ingredients missing per usable recipe |
|---|---|---:|---:|---:|---:|---:|---|
| Bluefin Crudo | open | 1.1 | 7 | 7 | 3 | 3 | **grape, chive** (lacucinaitaliana.com, has bottarga); bottarga, grape, chive ×2 |
| Bluefin Crudo | structured hosts | 2.3 | 8 | 8 | 4 | 1 | **grape, chive** ×2 (greatitalianchefs.com, have bottarga); bottarga, grape, chive ×2 |
| Little Gem Lettuces | open | 1.3 | 6 | 4 | 3 | 3 | pecorino (epicurious, bonappetit: tahini + sesame present); tahini, pecorino, sesame |
| Little Gem Lettuces | structured hosts | 2.4 | 8 | 7 | 3 | 3 | pecorino; tahini, sesame; tahini, pecorino, sesame |
| Heirloom Tomatoes | open | 1.7 | 6 | 5 | 3 | 3 | pluot, shiso; pluot, sourdough; pluot, shiso, sourdough |
| Heirloom Tomatoes | structured hosts | 1.8 | 8 | 8 | 7 | 5 | pluot always; shiso and/or sourdough in most |
| Margherita | open | 1.1 | 6 | 6 | 5 | 3 | none ×1 (newidea.com.au); fior di latte ×3; tomato, fior di latte |
| Margherita | structured hosts | 2.6 | 8 | 8 | 7 | 5 | fior di latte ×6 (mozzarella wording); tomato ×1 |
| King Salmon | open | 1.0 | 6 | 5 | 3 | 3 | corn, shishito; squash, basil, shishito; squash, shishito |
| King Salmon | structured hosts | 2.0 | 8 | 6 | 3 | 3 | salmon itself missing in 3 (different fish): relevance filter cases |
| **Total** | | | **71** | **64** | **41** | **33** | |

Against the first sample: usable pages 40% → 58%; usable recipes with a serving count 58% → 80%; crudo recipes containing bottarga 0 → 3. The domain-restricted mode gave more usable recipes (24 vs 17) and more serving counts, but also surfaced epicurious pages without structured data and two hosts that rate-limited (food52.com, 429) the scripted fetch, so the pipeline needs per-host back-off and `robots.txt` checks as specified. Search latency 1.0–2.6 s per call. Both modes are worth running (D12).

What this does not measure: relevance grading (Measure B) and the synonym-aware coverage check, both of which are 2B-2 components; the "salmon" and "fior di latte" misses above are exactly the cases they handle.

## 2c. Correction (2026-11-02, found during 2B-1): the "bottarga crudo" recipes are not crudo recipes

Section 2b counted three crudo-search results that "contain bottarga and lack only grape and chive". That count used a substring check on the ingredient lines; it did not look at what the recipes were. Fetched and read in 2B-1 (item 7 of Julius's requirements), the three are distinct pages and **none is a crudo**:

| URL (host) | Title | Fish line | Bottarga line | Preparation |
|---|---|---|---|---|
| lacucinaitaliana.com | Tuna and Bottarga Toast | 4 1/2 oz water-packed (canned) tuna | fresh bottarga di tonno, no quantity | assembled toast, no method text |
| greatitalianchefs.com | 'Anchovy painting', anchovy with bottarga mayonnaise | 400 g anchovies, filleted; cuttlefish ink | 40 g tuna bottarga | pickled, not raw tuna |
| greatitalianchefs.com | Sea bass with apple, fennel and celery | 320 g sea bass; prawns; scallops | 20 g bottarga, grated | sous-vide at 80 °C |

So the statement in section 1 that "three crudo recipes did contain bottarga" is withdrawn, and with it the suggestion that a garnish rule alone would have made the crudo complete. For the Bluefin Crudo, no published recipe found so far contains bottarga and is a crudo. The relevance grading of 2B-2 (dish type and preparation) is exactly what would have rejected these three, and this episode is the reason menu-ingredient coverage must never be the only relevance signal (D10).

## 3. Comparative table

| Criterion | Spoonacular | Edamam | Tavily + web extraction | TheMealDB |
|---|---|---|---|---|
| Recipes for the five dishes | **not measured** (key needed) | **not measured** (key needed) | Tavily, 10 searches: 41 extractable of 71 fetched; per dish 7 / 6 / 10 / 12 / 6 (crudo, little gem, tomatoes, margherita, salmon) | 0 crudo, 0 little gem, 0 heirloom tomato, 1 margherita, 7 "salmon" (none matching) |
| Match to menu dish | unknown | unknown | 3 crudo recipes with bottarga (missing garnishes only); tahini + sesame little gem salads without pecorino; tomato salads always without pluot; salmon recipes with other vegetables | poor (Tuna Nicoise for a crudo) |
| Quantities | `extendedIngredients[].amount`, `unit`, `measures.metric` (grams for some, e.g. pasta 170.097 g; `Tbsp` for butter) | `ingredients[].quantity`, `measure`, **`weight` in grams** for every ingredient, `foodId` | text lines: 9% weight units, 45% volume, 33% counts, 5% vague, 8% none (116 lines) | free text ("150ml", "Drizzle", "Pinch") |
| Servings | `servings` | `yield` | `recipeYield` with a serving count in 33 of 41 Tavily recipes; blanks, "1 item", "12 slices" otherwise | **none** |
| Instructions | `instructions`, `analyzedInstructions` | **not provided** for web recipes; source URL only | present in 12 of 12 extracted | `strInstructions` |
| Transformations before Phase 2A | parse `unit` → grams via USDA portions (metric grams only sometimes); state from instructions; USDA matching | grams given → skip conversion; state unknown (no instructions) → read source page anyway; USDA matching from `food` | full pipeline: parse lines, convert, state from instructions, USDA matching | parse free text; servings unknown → ineligible |
| LLM calls per recipe (estimate) | 2 (state, USDA query+select batched) | 2–3 (must fetch the source page for preparation) | 3–4 (name normalisation, state, query, select; +1 if no structured data) | 3 |
| Cost | free 50 points/day (≈ 10 dishes/day at ~4–5 points each), then $29/month for 1,500/day | $9/month (10,000 calls), no free tier | 1 credit per basic search; 1,000 free/month ≈ 500 dishes at 2 searches; then $0.008/credit | free |
| Latency | not measured | not measured | search 1.0–2.6 s; median 0.5 s per page fetch, max 1.9 s | ~0.3 s |
| Access limits | 1 request/s free | 10 calls/minute Basic | none stated for Tavily; some recipe hosts answer 403 or 429 to scripted fetches (back-off and robots.txt required) | 100-item list cap |
| **Caching / storing responses** | **max 1 hour with written permission; may not store ingredients; delete all data on termination** | **only 4 nutrients + id, title, image; "can not be stored unless explicitly permitted"; shown only to the requesting user** | terms restrict the *Service*, explicitly exclude *Output*; page facts are public; fetch cache and extracted-line fixtures are not restricted by Tavily | not stated; "free at point of access"; supporter tier required for app-store release |
| **Test fixtures from real responses** | **not permitted** | **not permitted** | permitted (ingredient lines and yields are facts; store URL and date, not full HTML) | unclear |
| Attribution | credit original source; backlink on free plan | mandatory Edamam image with link; missing it is a contract breach | cite the source URL (we do anyway) | none stated |
| Nutrition fields we must ignore | `nutrition` when requested | `totalNutrients` always present | JSON-LD `nutrition` block on many pages | none |

## 4. Schema compatibility with `RecipeInput`

- **Spoonacular** `extendedIngredients[]` → `name`, `grams` from `measures.metric.amount` when `unitShort` is `g`, else `quantity`+`unit` through the 2B parser; `servings` → `servings`; `sourceUrl` → provenance; `instructions` → preparation state. Compatible, but every quantity we keep would be a stored "other data" the terms forbid, so a scenario could be computed and shown once, never saved or tested against a real payload.
- **Edamam** `ingredients[]` → `grams` directly from `weight` (the best quantity data of the four), `yield` → `servings`, `url` → provenance; no instructions, so preparation state would need the source page or an LLM guess, and the storage clause has the same effect as Spoonacular's.
- **Web JSON-LD** `recipeIngredient[]` → the 2B parser; `recipeYield` → servings parser; `recipeInstructions` → state; URL → provenance. Fully compatible with storage and provenance requirements.
- **TheMealDB** `strIngredientN`/`strMeasureN` → parser; no servings → per-serving impossible.

## 5. First web benchmark (my search tool, 30 URLs) and what it says about usable scenarios

| Dish | Pages tried | Fetched (200) | Extracted | All menu ingredients present | Missing only herbs or fruit |
|---|---:|---:|---:|---:|---:|
| Bluefin Crudo | 6 | 4 | 0 | 0 | 0 |
| Little Gem Lettuces | 6 | 5 | 1 | 0 | 0 (missing pecorino, sesame, little gem) |
| Heirloom Tomatoes | 6 | 5 | 4 | 0 | 4 (pluot, shiso) |
| Margherita | 6 | 3 | 2 | 2 | 0 |
| King Salmon | 6 | 6 | 5 | 0 | 1 (basil, shishito); others also miss squash or corn |

Reading (superseded in part by section 2b, which found bottarga crudo recipes): under the approved rules, Margherita would yield two eligible scenarios; Heirloom Tomatoes would yield four recipes that are relevant but incomplete unless pluot and shiso can be treated as modeled-zero garnishes (section 6); King Salmon recipes are variants with different vegetables (coverage below threshold); the crudo and the little gem salad produce nothing complete and representative from this sample. Restaurant dishes are defined by their garnishes, and published home recipes rarely share them. This is a property of the problem, not of the provider, and the honest output for most dishes will be a bounded "at least" figure with a named missing list.

Three practical improvements for 2B-1 follow from the data:
1. **Prefer hosts that publish structured data.** `recipe-scrapers` lists 742 supported hosts. Section 2b confirms that restricting Tavily to such hosts raises usable recipes (24 vs 17 across the five dishes) and serving counts, while the open search finds the niche pages (the bottarga crudo on lacucinaitaliana.com). Proposal: two searches per dish, one domain-restricted, one open.
2. **Read the yield from the page text when `recipeYield` is blank** (8 of 41 Tavily recipes), with the same verbatim check as LLM extraction.
3. **Expect volume and count lines.** 78% of lines need USDA portion weights or counts; D4's ordering (convert after matching) is the right design, and `get_portions()` is on the critical path.

## 6. Proposed refinement to D5 and D8, for your decision (D11)

Herb and fruit garnishes (chive, basil, shiso, pluot, grapes, shishito) appear on the menu and almost never in recipes. D8 makes each an unknown-quantity line, which blocks completeness. D5 permits a narrow modeled-zero list only where both tracked nutrients are effectively zero in USDA. Fresh herbs qualify (USDA basil: 0.041 g saturated fat, 0 mg cholesterol per 100 g; chives 0.146 g, 0 mg); fruit mostly qualifies (plums 0.017 g, 0 mg; grapes 0.054 g, 0 mg). Proposal (note: section 2c removed the crudo example that first motivated this; D11 was not approved as proposed, see the spec's section 15.0): when a menu-only ingredient is on the validated D5 list, append it as `grams_declared: null`, `modeled_zero: true`, with the USDA record cited, so the scenario can still be complete and the reply says "garnish contributions modeled as zero: shiso, pluot". Bottarga, cheeses, oils, nuts, bread and any flesh food can never be on the list, so the crudo stays incomplete, as it should. Alternative: keep D8 strict and accept that most dishes never reach a complete scenario. Recommendation: adopt the refinement, with the list capped at ingredients whose USDA record shows ≤ 0.15 g saturated fat and 0 mg cholesterol per 100 g, each entry cited and tested.

## 7. Unresolved licensing and access questions

1. **Edamam terms page** returned no body text twice; the plan page's footnotes were readable and are quoted above. If you want Edamam considered further, the full terms should be read in a browser before any trial sign-up.
2. **Spoonacular written permission** would be required even for the one-hour cache; the free plan requires a backlink. Not pursued.
3. **TheMealDB terms of use** were not read (link only); irrelevant given coverage.
4. **Site-level permission for web fetching:** 5 of 30 sites refused scripted fetches. The pipeline will honour `robots.txt` and skip such sites; whether a site's terms also forbid programmatic reading of recipe pages would be checked per included domain if the domain-restricted search is adopted.
5. **Tavily key:** present in `.env` (my earlier statement that it was missing was wrong). Ten credits were used for section 2b; the free tier is 1,000 per month.

## 8. Decisions needed from you

| # | Decision | Recommendation |
|---|---|---|
| D1 (final) | Primary source | Web extraction via Tavily search + `recipe-scrapers` + verified LLM fallback; structured APIs not integrated in 2B; interface kept |
| D11 | Menu-only herb and fruit garnishes as cited modeled-zero lines (section 6) | adopt, with the ≤ 0.15 g / 0 mg criterion and a tested list |
| D12 | Domain-restricted plus open search (section 5, item 1) | adopt |
| D14 | Spoonacular free key for an online-only, uncached comparison run during 2B-2 | optional; skip unless you want the coverage number for the record |

If D1, D11 and D12 are approved, 2B-1 starts with the fetch cache, extraction, the line parser, yield parser, weight-unit conversion and the D5 list, on fixtures captured from the 41 extractable Tavily pages (ingredient lines, yields, URLs and dates only), and stops at Checkpoint 2B-1.
