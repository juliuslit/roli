"""Add real-page tag cases to the line-tag test set (SPEC_3_mvp.md 12.12.9): every tag miss found on a real page becomes a test case built from the saved page, whole recipe, as the tag call sees it.

    .venv/bin/python -m roli_agent.scripts.build_real_tag_cases

The recipe's title, method and lines come from the saved page (`.cache/roli_mvp/pages`), through the same extraction as a menu run; no model call, no network. The roles below are the review's
answers, one per line, written by hand. A case already in the set (same URL) is replaced. The made-up cases stay.
"""

from __future__ import annotations

import json
import sys

from roli_agent.config import ROOT
from roli_agent.recipes.extract import ExtractionCache, extract_recipe
from roli_agent.recipes.fetch import FetchCache
from roli_agent.scripts.eval_line_tags import SET

E, M, R = "eaten", "cooking_medium", "removed"
OIL = "12.12.1 oil a food is stored in or served out of (3F: tagged eaten at full recipe weight)"
SPRIG = "whole herb sprigs stay in the jar and are not eaten (3F: tagged eaten)"
PEEL = "strips of peel or rind stay in the jar and are not eaten (3F: tagged eaten)"
JAR = "12.10.2 a marinade left in the jar: every liquid of it is a medium"
STAYS = "stays with the food"
# url, menu item, section, then (role, why) per line in page order. Every line here is a plain food.
CASES = [
    ("https://thecozyapron.com/marinated-olives", "SICILIAN OLIVES", "BAR SNACKS",
     [(E, "main ingredient"), (M, OIL), (R, SPRIG), (R, SPRIG), (E, STAYS), (R, PEEL), (E, STAYS), (E, STAYS)]),
    ("https://www.foodiecrush.com/marinated-olives", "Marinated olives", "",
     [(E, "main ingredient"), (E, "main ingredient"), (M, OIL), (E, STAYS), (R, SPRIG), (R, SPRIG), (E, STAYS), (E, STAYS), (E, STAYS), (E, "grated zest stays with the food")]),
    ("https://www.budgetbytes.com/marinated-olives", "Marinated olives", "",
     [(E, "a whole fruit; the line is not a liquid"), (E, "main ingredient"), (E, STAYS), (R, SPRIG), (R, SPRIG), (E, STAYS), (E, STAYS), (M, OIL)]),
    ("https://cooking.nytimes.com/recipes/1014416-marinated-olives", "Marinated olives", "",
     [(M, OIL), (M, JAR), (R, "bay leaves"), (E, STAYS), (R, PEEL), (E, STAYS), (E, STAYS), (E, STAYS), (E, "main ingredient")]),
    ("https://www.foodnetwork.com/recipes/ina-garten/warm-marinated-olives-1-7088521", "Marinated olives", "",
     [(E, "main ingredient"), (E, "main ingredient"), (R, PEEL), (E, STAYS), (E, STAYS), (E, STAYS), (E, STAYS), (E, STAYS), (M, OIL), (R, SPRIG)]),
]


def main() -> int:
    cache = ROOT / ".cache" / "roli_mvp"
    pages, extractions = FetchCache(cache / "pages"), ExtractionCache(cache / "extractions")
    doc = json.loads(SET.read_text(encoding="utf-8"))
    built = []
    for url, dish, section, roles in CASES:
        page = pages.get(url)
        if page is None:
            print(f"no saved page for {url}")
            return 1
        ex = extract_recipe(page["text"], url, cache=extractions)
        if len(ex.ingredient_lines) != len(roles):
            print(f"{url}: {len(ex.ingredient_lines)} lines on the page, {len(roles)} roles written")
            return 1
        built.append({"dish": dish, "section": section, "title": ex.title, "source": "real_page", "url": url, "seen_in": "3F", "method": ex.instructions_text,
                      "lines": [{"line": line, "role": role, "kind": "plain_food", "rule": why} for line, (role, why) in zip(ex.ingredient_lines, roles)]})
    urls = {b["url"] for b in built}
    doc["recipes"] = [r for r in doc["recipes"] if r.get("url") not in urls] + built
    doc["version"] = 3
    SET.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(built)} real-page recipes, {sum(len(b['lines']) for b in built)} lines; the set now has {len(doc['recipes'])} recipes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
