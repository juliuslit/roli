"""2B-1 end to end on a fake web: search both modes -> dedup -> fetch -> extract -> parse -> stats. No network."""

from __future__ import annotations

import json
from decimal import Decimal

import httpx

from roli_agent.recipes import ingest_dish
from roli_agent.recipes.fetch import PoliteFetcher
from roli_agent.recipes.models import MenuItem

from test_recipes_fetch_search import Site


def page(name, lines, yield_text="4 servings", steps="Slice the tuna. Dress and serve.", nutrition=True):
    ld = {"@context": "https://schema.org", "@type": "Recipe", "name": name, "recipeIngredient": lines, "recipeYield": yield_text,
          "recipeInstructions": [{"@type": "HowToStep", "text": steps}]}
    if nutrition:
        ld["nutrition"] = {"@type": "NutritionInformation", "calories": "123 kcal", "saturatedFatContent": "45 g"}
    return f"<html><head><script type='application/ld+json'>{json.dumps(ld)}</script></head><body>{name}</body></html>"


class FakeSource:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def search(self, query, mode, max_results=10):
        self.calls.append((query, mode))
        return self.results[mode]


CRUDO_LINES = ["85 g sushi-grade bluefin tuna, thinly sliced", "1 tbsp extra-virgin olive oil", "1 tsp bottarga, grated", "Flaky salt, to taste"]
PAGES = {
    "https://a.test/crudo": page("Tuna crudo with bottarga", CRUDO_LINES),
    "https://a.test/crudo/print/9": page("Tuna crudo with bottarga", CRUDO_LINES),        # same content, print view
    "https://b.test/crudo-copy": page("Crudo (syndicated)", CRUDO_LINES, nutrition=False),  # same content, other host
    "https://c.test/seared": page("Seared tuna", ["2 tuna steaks", "1 tbsp oil"], yield_text="2 servings", steps="Sear the tuna 2 minutes per side."),
    "https://d.test/blog": "<html><body><p>No recipe here.</p></body></html>",
}
RESULTS = {
    "open": [{"url": "https://a.test/crudo", "title": "Crudo"}, {"url": "https://youtube.com/w", "title": "v"},
             {"url": "https://c.test/seared", "title": "Seared"}, {"url": "https://d.test/blog", "title": "Blog"}],
    "structured_hosts": [{"url": "https://www.a.test/crudo/?utm_source=t", "title": "Crudo"}, {"url": "https://a.test/crudo/print/9", "title": "Print"},
                         {"url": "https://b.test/crudo-copy", "title": "Copy"}],
}


def run_ingest(pages=PAGES, results=RESULTS, robots=None):
    site = Site(robots=robots or {}, pages=pages)
    fetcher = PoliteFetcher(transport=httpx.MockTransport(site), sleep=lambda s: None)
    source = FakeSource(results)
    item = MenuItem(name="BLUEFIN CRUDO", description="bottarga, muscat grape, chive", section="TO START")
    return ingest_dish(item, source=source, fetcher=fetcher), source, site


def test_both_modes_searched_and_queries_recorded():
    result, source, _ = run_ingest()
    assert [m for _, m in source.calls] == ["open", "structured_hosts"]
    assert result.queries == {"open": "bluefin crudo recipe", "structured_hosts": "bluefin crudo recipe bottarga"}


def test_specific_section_word_joins_the_query_generic_ones_do_not():
    from roli_agent.recipes.ingest import default_queries
    assert default_queries(MenuItem(name="MARGHERITA", description="tomato, fior di latte, basil", section="PIZZA")) == {
        "open": "margherita pizza recipe", "structured_hosts": "margherita pizza recipe tomato"}
    assert default_queries(MenuItem(name="KING SALMON", description="squash, corn", section="ENTREE"))["open"] == "king salmon recipe"
    assert default_queries(MenuItem(name="PUTTANESCA", description="", section="PIZZA"))["structured_hosts"] == "puttanesca pizza recipe"
    assert default_queries(MenuItem(name="DUCK TRIANGOLI", description="pistachio", section="PASTA"))["open"] == "duck triangoli pasta recipe"


def test_url_dedup_and_found_by():
    result, _, _ = run_ingest()
    by_host_path = {h.canonical_url: h for h in result.hits}
    crudo = by_host_path["https://a.test/crudo"]
    assert crudo.found_by == ["open", "structured_hosts"]
    assert result.stats.hits_in_both_modes == 1 and result.stats.blocked_hosts_skipped == 1
    assert result.stats.hits_after_url_dedup == 5          # a/crudo, c/seared, d/blog, a/crudo/print/9 -> folds to a/crudo/9 (distinct path), b/crudo-copy


def test_content_dedup_marks_equivalent_recipes_but_keeps_them():
    result, _, _ = run_ingest()
    extracted = result.recipes
    dupes = [r for r in extracted if r.duplicate_of]
    assert result.stats.extracted == 4 and result.stats.content_duplicates == 2 and result.stats.distinct_recipes == 2
    assert all(d.duplicate_of == "https://a.test/crudo" for d in dupes)
    assert all("content_duplicate" in d.flags for d in dupes)


def test_provenance_and_parsing_preserved():
    result, _, _ = run_ingest()
    crudo = next(r for r in result.recipes if r.canonical_url == "https://a.test/crudo")
    assert crudo.ingredient_lines == CRUDO_LINES                       # verbatim lines kept beside parsed values
    assert crudo.yield_text == "4 servings" and crudo.servings == Decimal(4)
    assert crudo.found_by == ["open", "structured_hosts"] and crudo.extraction in ("recipe_scrapers", "json_ld")
    tuna, oil, bottarga, salt = crudo.ingredients
    assert tuna.grams == Decimal(85) and tuna.preparation_hint == "raw"      # 'sushi-grade' is a raw-fish cue
    assert oil.grams is None and "conversion_pending_usda_portion" in oil.flags
    assert bottarga.quantity == Decimal(1) and bottarga.unit == "tsp" and bottarga.grams is None
    assert salt.quantity is None and "vague_quantity" in salt.flags and salt.grams is None
    assert "sear" not in crudo.cooking_verbs
    seared = next(r for r in result.recipes if r.canonical_url == "https://c.test/seared")
    assert "sear" in seared.cooking_verbs


def test_stats_measure_usable_quantities_not_only_extraction():
    result, _, _ = run_ingest()
    s = result.stats
    assert s.fetched == 5 and s.fetch_ok == 5
    assert s.distinct_recipes == 2 and s.with_servings == 2
    # crudo: 3 of 4 lines quantified, 1 of 4 with grams; seared: 2 of 2 quantified, 0 grams -> 5/6 and 1/6
    assert s.pct_lines_quantified == 83.3 and s.pct_lines_grams_known == 16.7
    assert s.recipes_with_all_lines_quantified == 1


def test_page_nutrition_never_reaches_the_result():
    result, _, _ = run_ingest()
    blob = result.model_dump_json()
    assert "123 kcal" not in blob and "45 g" not in blob and "saturatedFatContent" not in blob


def test_robots_and_search_failures_are_recorded_not_fatal():
    class Failing(FakeSource):
        def search(self, query, mode, max_results=10):
            if mode == "structured_hosts":
                raise httpx.ConnectError("down")
            return super().search(query, mode, max_results)
    site = Site(robots={"a.test": "User-agent: *\nDisallow: /"}, pages=PAGES)
    fetcher = PoliteFetcher(transport=httpx.MockTransport(site), sleep=lambda s: None)
    item = MenuItem(name="BLUEFIN CRUDO", description="bottarga")
    result = ingest_dish(item, source=Failing(RESULTS), fetcher=fetcher)
    assert any("structured_hosts" in n for n in result.notes)
    assert result.stats.robots_disallowed >= 1 and result.stats.search_credits == 1
    assert all(r.host != "a.test" for r in result.recipes)


def test_listicle_without_quantities_is_flagged():
    pages = dict(PAGES)
    pages["https://l.test/list"] = page("21 Tomato Recipes", ["Tomato salad", "Tomato soup", "Panzanella", "Caprese", "Gazpacho", "Bruschetta"], yield_text="")
    results = {"open": [{"url": "https://l.test/list", "title": "List"}], "structured_hosts": []}
    result, _, _ = run_ingest(pages, results)
    (r,) = result.recipes
    assert "no_quantities_listicle_suspect" in r.flags and r.n_quantified == 0 and r.servings is None
