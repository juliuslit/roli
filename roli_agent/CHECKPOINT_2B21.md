# Checkpoint 2B-2.1: corrections, re-evaluation, held-out matching set, revised Phase 2C specification

Date: 2026-11-02. Status: **Phase 2B-2.1 complete; stopped for review. Phase 2C not built.** Decisions D18–D21 and D5 are recorded in `SPEC_2B_recipe_scenarios.md` section 15.3; the revised Phase 2C specification is `SPEC_2C_menu_adapted_scenarios.md`.

## 1. Summary

| Item | Result |
|---|---|
| Corrections 1–3 (inline weights, proxy portions, ambiguous portions) | built, tested; the two wrong live conversions of 2B-2 are gone (section 3) |
| Correction 6 (extraction cache) | built; warm run 87.8 s -> 46.5 s for five dishes, LLM calls 30 -> 13, cost $0.046 -> $0.017 |
| Correction 7 (Phase 2A and safeguards) | unchanged: 308 library tests pass unchanged; no scenario became complete by assumption |
| Automated tests | agent **167 passed** (160 + 7 new), 4 skipped live; `test_report_2B21.txt` |
| Held-out matching set (correction 5) | 40 rows, labels frozen before scoring (hash in `heldout_README.md`): 15 direct, 18 acceptable proxies, 2 label disagreements, 2 "false matches" (one real: mascarpone), 3 unresolved. Verdicts not retuned; the reading is in `heldout/review_notes.md` |
| Five-dish re-run (correction 4) | still **0 complete, 0 eligible** of 18 calculated scenarios. On the 15 recipes both runs calculated: 142 lines unchanged, 1 wrong weight fixed, 1 newly resolved, 11 correctly withdrawn under D20/D21, 27 changed by a different model choice, of which 8 olive-oil lines lost their weight to the D19 qualification (section 4) |
| Revised Phase 2C | `SPEC_2C_menu_adapted_scenarios.md`: gaps by kind, assumption classes, composition vs portion-size proxies, low/high scenarios, serving-size uncertainty, a 28-row reviewable weights table from live USDA portions, and the recommendation to keep modeled ranges internal |

## 2. What changed in the code

| Correction | Change | Where |
|---|---|---|
| 1. inline weights | "One 8-ounce loin …", "two 6 oz fillets", "1 8-oz block": the weight after the count becomes a per-item note that the weight converter reads; the count stays; flag `inline_weight`. "2% milk" is not a weight. | `parse.py` (`INLINE_WEIGHT`), tests `test_inline_weight_after_the_count_wins_over_the_count` |
| 1. bare counts | cubic-inch, slice, strip, stick, section, floret, ring and similar labels never serve a bare count | `convert.py` (`NOT_A_WHOLE_ITEM`), test `test_cubic_inch_and_slice_labels_never_serve_a_bare_count` |
| 2. proxy portions (D21) | whole-item weights of a proxy record are refused (`proxy_count_portion_refused`, blocker `proxy_portion_refused`); volume measures of a proxy are allowed for volume lines only, flagged `proxy_volume_portion`, reference says "approximation" | `convert.py` (`proxy=` argument), `pipeline.py`, test `test_proxy_records_lend_volume_measures_only` |
| 3. ambiguous portions (D20) | no median, no default size: a record that lists sizes while the line names none -> `portion_size_unspecified`, unresolved; a stated size ("1 large orange") picks that size; a record whose only whole-item label is unsized ("1 fruit", "1 clove", "1 pepper") matches a bare count (`portion_whole_item`). Semantically different labels are never averaged (ambiguity stays `portion_ambiguous`). The former `portion_default_medium` / `portion_default_whole` paths are deleted. | `convert.py`, tests updated and extended |
| D18 reporting | `proxy_contribution` (absolute, per nutrient), `proxy_share` and `proxy_share_percent` with `proxy_share_basis: "known_subtotal"`, `largest_contributor_is_proxy` per nutrient, flags `proxy_largest_contributor` and `proxy_share_of_known_subtotal`; the reply prints "their share of the known subtotal" for incomplete scenarios | `models.py`, `pipeline.py`, `responses.py`, pipeline test |
| D19 qualification | prompt: prefer SR Legacy only for the same food in the same state; "never trade away the specific food or the right state" | `prompts.py` |
| 6. extraction cache | `ExtractionCache` keyed by URL + page content, beside the page cache, 30 days; stats `extracted_from_cache`; wired into the graph default, the pipeline and the measurement script | `extract.py`, `ingest.py`, `graph.py`, test `test_extraction_cache_skips_the_llm_fallback_for_an_unchanged_page` |

Nothing changed in `nutrition_service/roli_nutrition/recipe/`, `code/`, the MCP wrapper or the LangSmith prototype.

## 3. The two 2B-2 errors, before and after (same recipes, live)

| Line | 2B-2 (run 3) | 2B-2.1 (run 4) |
|---|---|---|
| One 8-ounce loin sushi-grade yellowfin tuna, cut into 1-inch cubes | 16 g from the '1 cubic inch, boneless' portion | **226.796 g** = 8 oz x 28.349523125 (inline weight; flags `inline_weight`, `embedded_weight`) |
| 3 baby gem lettuce (aka little gem lettuce), leaves separated | 1878 g from romaine's '1 head' = 626 g | **unresolved**, `proxy_count_portion_refused` (the romaine head is not a little gem head) |
| 4 heads little gem lettuce / 4 medium heads Little Gem Lettuce | 2504 g | unresolved, `proxy_count_portion_refused` |
| one 14.5-oz. can whole, peeled tomatoes | unresolved (the weight sat inside the line) | **411.068 g** (inline weight x 1) |

## 4. Five-dish re-run: before (run 3) and after (run 4)

Both runs cold (empty page, search, extraction and match caches), same model (`google/gemini-3.8-flash`, temperature 0), same script. Search results and model choices are **not** identical between runs: Tavily returned partly different pages (Little Gem and Margherita sets changed; 15 of the 18 calculated recipes are common) and the model's record choices moved on 27 common lines. Two comparisons are therefore given: the whole run, and the common recipes line by line.

### 4a. Whole run

| Measure | 2B-2 (run 3) | 2B-2.1 (run 4) |
|---|---:|---:|
| distinct recipes read / relevant / calculated | 38 / 29 / 19 | 42 / 30 / 18 |
| complete / eligible for a range | 0 / 0 | 0 / 0 |
| recipe lines in calculated scenarios | 229 | 221 |
| lines fully resolved (record, grams, state) | 139 (61 %) | 115 (52 %) |
| lines converted by a USDA portion | 120 | 90 |
| lines with an explicit or embedded weight | 15 | 19 |
| blockers: no USDA portion | 46 | 63 |
| blockers: proxy whole-item refused (new, D21) | — | 9 |
| blockers: menu-only (D8) | 44 | 44 |
| blockers: unknown quantity (incl. seasonings, optional) | 30 | 19 |
| blockers: nutrient not reported | 8 | 8 |
| blockers: unresolved USDA | 6 | 6 |
| errors (LLM failures, exceptions) | 0 | 0 |
| cold: seconds / LLM calls / cost | 282 s / 54 / $0.132 | 303 s / 52 / $0.132 |
| warm: seconds / LLM calls / cost / USDA HTTP | 87.8 s / 30 / $0.046 / 4 | **46.5 s / 13 / $0.017 / 6** |
| warm ingest stage per dish | 3.8–17.0 s | 0.3–6.6 s |

### 4b. Common recipes, line by line (15 scenarios, 182 lines)

| Outcome | Lines | What happened |
|---|---:|---|
| unchanged | 142 | same record, same grams |
| wrong weight corrected | 1 | the tuna loin (section 3) |
| newly resolved | 1 | the 14.5-oz can (inline weight) |
| withdrawn under D20 | 4 | "3 hard-boiled eggs" (the record lists sizes, the line names none), "2 scallions", "4 radishes", "1/2 orange" |
| withdrawn under D21 | 7 | the three little-gem lines, "2 large pluots" on the plum proxy, "3 large heirloom tomatoes" on a record the model labelled proxy, "2-3 large pinches of kosher salt" on a proxy-labelled salt |
| different record chosen by the model | 27 | 8 olive-oil lines went from "Oil, olive, salad or cooking" (SR Legacy, 13.5 g per tbsp) to "Oil, olive, extra virgin" (Foundation, no measures) and lost their weight; the rest are equivalent swaps (tap water records, spearmint vs peppermint, grape vs red tomatoes, a flour record that gained a weight) |

Reading: corrections 1–3 behaved as specified. Every one of the 11 withdrawals is a weight that was an assumption; three of them ("3 large heirloom tomatoes", the salt pinches, the pluots) are casualties of the model labelling a composition-equivalent record "proxy", which D21 then treats as a different-sized food. The resolved-line share fell from 61 % to 52 % mainly through the olive-oil change, which is the D19 qualification working as written: "extra virgin" reads as more specific, so the model keeps the Foundation record, which USDA cannot weigh. For saturated fat and cholesterol the two olive-oil records are equivalent (13.808 g and 0 mg per 100 g for both grades in USDA's tables), so the specificity gained is nil and the weight lost is real. I did not add a rule for this; it is decision D22 below.

### 4c. The five statements (run 4)

All five say "none could be calculated completely" and name the causes; the crudo's now also says "some counted items are matched to substitute records whose item sizes do not apply". Margherita coverage is 1.0 on all four calculated recipes; its blockers are oregano (leaves vs ground), garlic (two clove labels), olive oil (D22) and a dough sub-recipe. Known subtotals remain visible per scenario with the "known subtotals" wording.

### 4d. Run-to-run variation

Temperature 0 does not make the model deterministic across OpenRouter calls, and Tavily's results drift within the day. Between runs 3 and 4: 3 of 18 calculated recipes are new, 2 Little Gem recipes moved from relevant to hard-excluded (grilled or baked preparations), and 27 of 182 common lines got a different record. Any before/after claim on this pipeline must be read on common lines, as in 4b; whole-run totals carry this noise.

## 5. Held-out USDA matching evaluation (correction 5)

`menu_reader_eval/usda_matching/heldout_set.csv` (40 rows: cured meats, Italian cheeses, fats, offal, roe, plus direct records that look like proxies), `heldout_README.md` (labelling date, frozen SHA-256, scoring command), results `heldout/results_2026-11-02.{json,md}`, reading `heldout/review_notes.md`. Labels are the agent's, written before any prediction; Julius's independent review is pending and is recorded as such.

| Verdict | Count | Notes |
|---|---:|---|
| direct, correct | 15 | fontina, egg yolk, chicken livers, salt cod, octopus, anchovy, shrimp, scallops, lamb loin, ricotta, heavy cream, coconut milk, chorizo, beef tallow, pecorino romano |
| proxy, acceptable | 18 | bottarga -> caviar; mirin -> cooking wine; guanciale and pancetta -> bacon, cooked; prosciutto and speck -> cured ham; 'nduja -> pork sausage; bresaola -> beef, cured, dried; lardo -> lard; pecorino sardo -> romano; grana padano -> parmesan; caciocavallo -> provolone; burrata and stracciatella -> mozzarella; taleggio -> fontina; ricotta salata -> ricotta; crème fraîche -> sour cream; colatura -> fish sauce |
| label disagreement | 2 | gorgonzola -> blue cheese and ghee -> anhydrous butter oil, both labelled direct by the model and proxy by my labels; the model is right |
| false match | 2 | **mascarpone -> "Cheese spread, cream cheese base"**: a real proxy error that understates fat; foie gras -> "Pate de foie gras, canned": a label-wording error on my side |
| unresolved | 3 | duck fat (the model found no rendered fat among USDA's ten candidates), squid ink, bone marrow |

Scored once, 8 LLM calls, 48 s, $0.023. The verdicts stand as scored; `review_notes.md` says what a corrected v2 set would give (1 false match, 2.5 %) without applying it.

## 6. Files

Created: `roli_agent/SPEC_2C_menu_adapted_scenarios.md`, `roli_agent/test_report_2B21.txt`, `roli_agent/eval/2b2_live_2026-11-02.json` (run 4), `roli_agent/eval/2b2_live_2026-11-02_run3.json` (run 3, renamed), `roli_agent/eval/garnish_portions_2026-11-02.json` (USDA portions for the 2C weights table), `menu_reader_eval/usda_matching/heldout_set.csv`, `heldout_README.md`, `heldout/results_2026-11-02.{json,md}`, `heldout/review_notes.md`, this file.

Modified: `roli_agent/recipes/{parse,convert,models,pipeline,extract,ingest}.py`, `roli_agent/{prompts,responses,nodes,graph}.py`, `roli_agent/scripts/measure_2b2.py`, tests `test_recipes_convert_portions.py`, `test_recipes_pipeline.py`, `test_recipes_extract.py`, `SPEC_2B_recipe_scenarios.md` (section 15.3), the project notes. `PHASE_2C_proposal.md` is superseded by the new specification and kept for history.

Unchanged: `nutrition_service/` except nothing (308 tests, same as 2B-2), `code/`, MCP wrapper, LangSmith prototype. No deployment; secret scan 0 hits for all five keys outside `.env`.

## 7. Decisions needed

| # | Question | Recommendation |
|---|---|---|
| D22 | olive oil and similar: the D19 qualification keeps "Oil, olive, extra virgin" (Foundation, no household measures) over "Oil, olive, salad or cooking" (SR Legacy), equivalent for both tracked nutrients, and 8 common lines lost their weight. Options: (a) tell the model that grade and varietal qualifiers (extra virgin, year-round average) do not count as food specificity for these two nutrients when the records are otherwise the same food and state; (b) let a Foundation record without measures borrow the *volume* measures of the same-food SR Legacy sibling among the candidates, flagged as a same-food density approximation; (c) accept the loss as honest | (a) first; it is a wording of D19, not a new assumption. (b) only if (a) proves insufficient |
| D21 edge | the model labels "Tomatoes, red, ripe, raw" a proxy for heirloom tomatoes, so D21 refuses the tomato's own sizes | accept for now; revisit when the composition-proxy label carries a "same food family, size comparable" sub-type (2C section 6) |
| held-out set | approve or amend the labels (`review_notes.md` lists the four disagreements); approve that a v2 set is a new frozen file scored again | approve v2 with the four label corrections |
| 2C | review `SPEC_2C_menu_adapted_scenarios.md`: classes, the weights table (every `proposed` row), the 30 % assumed-share limit, and "internal only" | internal only, as you prefer; the `substantial` rows need your review before any figure is shown |

**Stopped here. Phase 2C, menu-wide ranking, Telegram and the conversational interface are not started.**
