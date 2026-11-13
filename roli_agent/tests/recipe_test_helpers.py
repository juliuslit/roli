"""Helpers for the 2B-2 tests: a rule-driven fake LLM that answers from lookup tables (so prompt order does not
matter), a USDA router over the saved real food records with synthetic candidate lists, and a fake web."""

from __future__ import annotations

import glob
import json
import os
import re
from typing import Any

import httpx
from langchain_core.messages import AIMessage

from conftest import FIXTURES, make_service

BLUEFIN, OLIVE, ROMANO, TOMATO, LETTUCE, SESAME, TAHINI, BREAD, CHINOOK, PINK = 173706, 171413, 171249, 170457, 169249, 170151, 170189, 172675, 171999, 172001


def all_foods() -> dict[int, dict]:
    foods = {}
    for path in glob.glob(str(FIXTURES / "food_*.json")):
        name = os.path.basename(path)
        if "unfiltered" in name or "branded" in name:
            continue
        body = json.loads(open(path, encoding="utf-8").read())
        foods[body["fdcId"]] = body
    return foods


FOODS = all_foods()


def candidates(*fdc_ids: int) -> dict:
    """A USDA search reply listing the given saved records (description and data type copied from the real files)."""
    return {"totalHits": len(fdc_ids), "foods": [{"fdcId": f, "description": FOODS[f]["description"], "dataType": FOODS[f]["dataType"]} for f in fdc_ids]}


# query text -> candidate FDC IDs. Queries are what the RuleLLM writes (see QUERIES below).
SEARCHES = {
    "tuna bluefin raw": [BLUEFIN, CHINOOK],
    "oil olive": [OLIVE],
    "cheese romano": [ROMANO],
    "tomatoes red ripe raw": [TOMATO],
    "lettuce green leaf raw": [LETTUCE],
    "seeds sesame roasted": [SESAME],
    "tahini": [TAHINI],
    "bread sourdough": [BREAD],
    "salmon chinook cooked dry heat": [CHINOOK, PINK],
    "salmon chinook raw": [CHINOOK],              # only a cooked record exists in the fixtures: a state conflict for a raw hint
    "salt table": [],
    "chives raw": [],
    "grapes raw": [],
    "fish roe": [],
}
# ingredient name (as parsed) -> (usda query, chosen fdc_id or None, match_type)
QUERIES = {
    "sushi-grade bluefin tuna": ("tuna bluefin raw", BLUEFIN, "direct"),
    "bluefin tuna": ("tuna bluefin raw", BLUEFIN, "direct"),
    "extra-virgin olive oil": ("oil olive", OLIVE, "direct"),
    "olive oil": ("oil olive", OLIVE, "direct"),
    "pecorino romano": ("cheese romano", ROMANO, "direct"),
    "pecorino sardo": ("cheese romano", ROMANO, "proxy"),
    "burrata": ("cheese romano", ROMANO, "proxy"),
    "ripe plum tomatoes": ("tomatoes red ripe raw", TOMATO, "direct"),
    "heirloom tomatoes": ("tomatoes red ripe raw", TOMATO, "direct"),
    "tomatoes": ("tomatoes red ripe raw", TOMATO, "direct"),
    "little gem lettuce": ("lettuce green leaf raw", LETTUCE, "proxy"),
    "toasted sesame seeds": ("seeds sesame roasted", SESAME, "direct"),
    "tahini": ("tahini", TAHINI, "direct"),
    "sourdough bread": ("bread sourdough", BREAD, "direct"),
    "king salmon fillets": ("salmon chinook raw", CHINOOK, "direct"),
    "cooked chinook salmon": ("salmon chinook cooked dry heat", CHINOOK, "direct"),
    "flaky salt": ("salt table", None, "direct"),
    "salt": ("salt table", None, "direct"),
    "chives": ("chives raw", None, "direct"),
    "bottarga": ("fish roe", None, "direct"),
    "muscat grape": ("grapes raw", None, "direct"),
    "chive": ("chives raw", None, "direct"),
}


class RuleLLM:
    """Answers the three 2B-2 prompts from tables; records prompts. `grades` maps a recipe title to
    (dish_type, preparation, course_portion). Unknown titles get ("same", "same", "same")."""

    def __init__(self, grades: dict[str, tuple[str, str, str]] | None = None, queries: dict | None = None, *, break_relevance: bool = False,
                 foreign_id: int | None = None):
        self.grades = grades or {}
        self.queries = queries or QUERIES
        self.prompts: list[str] = []
        self.break_relevance = break_relevance
        self.foreign_id = foreign_id            # when set, every selection proposes this ID (the guard must reject it)

    def invoke(self, messages) -> AIMessage:
        text = messages[-1].content
        text = text if isinstance(text, str) else json.dumps(text)
        self.prompts.append(text)
        if text.startswith("You grade how well published recipes"):
            if self.break_relevance:
                return AIMessage(content="I cannot answer in JSON, sorry")
            rows = []
            for m in re.finditer(r'^(\d+)\. "([^"]*)"', text, re.M):
                g = self.grades.get(m.group(2), ("same", "same", "same"))
                rows.append({"index": int(m.group(1)), "dish_type": g[0], "preparation": g[1], "course_portion": g[2], "reason": f"test grade for {m.group(2)}"})
            return AIMessage(content=json.dumps({"recipes": rows}))
        if text.startswith("You write search queries"):
            rows = []
            for m in re.finditer(r'^- id (\d+): "([^"]*)"', text, re.M):
                q = self.queries.get(m.group(2), (m.group(2), None, "direct"))[0]
                rows.append({"id": int(m.group(1)), "usda_query": q})
            return AIMessage(content=json.dumps({"queries": rows}))
        if text.startswith("You choose USDA FoodData Central records"):
            rows = []
            for block in re.split(r"\n(?=Ingredient id \d+:)", text):
                m = re.match(r'Ingredient id (\d+): "([^"]*)"', block)
                if not m:
                    continue
                listed = [int(x) for x in re.findall(r"fdc_id (\d+):", block)]
                _, wanted, kind = self.queries.get(m.group(2), ("", None, "direct"))
                if self.foreign_id is not None:
                    wanted = self.foreign_id
                rows.append({"id": int(m.group(1)), "fdc_id": wanted if (wanted in listed or self.foreign_id) else None, "match_type": kind,
                             "reason": f"test selection for {m.group(2)}"})
            return AIMessage(content=json.dumps({"selections": rows}))
        if text.startswith("Below is the visible text of a web page"):
            return AIMessage(content=json.dumps({"ingredient_lines": [], "yield_text": "", "instructions_text": ""}))
        raise AssertionError(f"RuleLLM got an unexpected prompt: {text[:80]!r}")


def usda_router_2b2(searches: dict | None = None):
    table = dict(SEARCHES)
    table.update(searches or {})

    def respond(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path.endswith("/foods/search"):
            query = json.loads(request.content)["query"]
            return httpx.Response(200, json=candidates(*table.get(query, [])))
        m = re.search(r"/food/(\d+)$", request.url.path)
        fid = int(m.group(1)) if m else None
        if fid in FOODS:
            return httpx.Response(200, json=FOODS[fid])
        return httpx.Response(404, content=b"")
    return respond


def make_usda(searches: dict | None = None):
    return make_service(usda_router_2b2(searches))


def recipe_page(name: str, lines: list[str], yield_text: str = "4 servings", steps: str = "Slice and dress. Serve.") -> str:
    ld = {"@context": "https://schema.org", "@type": "Recipe", "name": name, "recipeIngredient": lines, "recipeInstructions": [{"@type": "HowToStep", "text": steps}],
          "nutrition": {"@type": "NutritionInformation", "calories": "999 kcal", "cholesterolContent": "777 mg"}}
    if yield_text:
        ld["recipeYield"] = yield_text
    return f"<html><head><title>{name}</title><script type='application/ld+json'>{json.dumps(ld)}</script></head><body><h1>{name}</h1></body></html>"


class FakeSource:
    def __init__(self, results: dict[str, list[dict]]):
        self.results = results
        self.calls: list[tuple[str, str]] = []

    def search(self, query: str, mode: str, max_results: int = 10) -> list[dict]:
        self.calls.append((query, mode))
        return self.results.get(mode, [])


def numbers_in(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?", text))


def numbers_in_json(obj: Any) -> set[str]:
    return numbers_in(json.dumps(obj, default=str))
