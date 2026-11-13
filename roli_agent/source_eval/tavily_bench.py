"""Phase 2B-0 addendum: Tavily search quality for the five dishes, then the same extraction benchmark on its URLs."""
import json, os, re, sys, time
import httpx
from dotenv import load_dotenv
from recipe_scrapers import scrape_html
sys.path.insert(0, os.path.dirname(__file__))
from bench import classify, ldjson_recipe  # reuse the deterministic parts

load_dotenv("/Users/juliuslitinskas/projects/roli/.env")
KEY = os.environ["TAVILY_API_KEY"]
DISHES = {
 "Bluefin Crudo": {"menu": ["bottarga", "grape", "chive"], "q": "bluefin tuna crudo recipe with bottarga"},
 "Little Gem Lettuces": {"menu": ["tahini", "pecorino", "sesame", "little gem"], "q": "little gem lettuce salad tahini vinaigrette pecorino sesame recipe"},
 "Heirloom Tomatoes": {"menu": ["pluot", "shiso", "basil", "sourdough", "tomato"], "q": "heirloom tomato salad pluot shiso basil sourdough recipe"},
 "Margherita": {"menu": ["tomato", "fior di latte", "basil"], "q": "pizza margherita recipe fior di latte basil"},
 "King Salmon": {"menu": ["salmon", "squash", "corn", "basil", "shishito"], "q": "roasted king salmon summer squash corn basil shishito recipe"},
}
# Hosts known to publish schema.org Recipe data (all in recipe-scrapers' supported list).
STRUCTURED_HOSTS = ["seriouseats.com", "bonappetit.com", "epicurious.com", "foodandwine.com", "food52.com", "thekitchn.com",
                    "simplyrecipes.com", "allrecipes.com", "bbcgoodfood.com", "foodnetwork.com", "delish.com", "myrecipes.com",
                    "tasteofhome.com", "eatingwell.com", "cooking.nytimes.com", "jamieoliver.com", "greatbritishchefs.com", "greatitalianchefs.com"]
BLOCK = ("youtube.", "tiktok.", "instagram.", "pinterest.", "facebook.", "reddit.", "amazon.", "ckbk.com", "pressreader.")

def tavily(query, include_domains=None):
    body = {"query": query, "max_results": 10, "search_depth": "basic", "include_answer": False}
    if include_domains: body["include_domains"] = include_domains
    t0 = time.perf_counter()
    r = httpx.post("https://api.tavily.com/search", json=body, headers={"Authorization": f"Bearer {KEY}"}, timeout=30)
    sec = time.perf_counter() - t0
    r.raise_for_status()
    return r.json().get("results", []), sec

client = httpx.Client(headers={"User-Agent": "Mozilla/5.0 (compatible; RoliRecipeEval/0.1; +research)"}, follow_redirects=True, timeout=15)
def extract(url, menu):
    row = {"url": url, "http": None, "jsonld": False, "n_ing": 0, "yield": "", "instr": False, "missing": list(menu), "err": ""}
    try:
        r = client.get(url); row["http"] = r.status_code
    except Exception as e:
        row["err"] = type(e).__name__; return row
    if r.status_code != 200: return row
    html = r.text; ld = ldjson_recipe(html); row["jsonld"] = ld is not None
    ings, yld, instr = [], "", ""
    try:
        s = scrape_html(html, org_url=url, supported_only=False); ings = s.ingredients() or []
        try: yld = s.yields() or ""
        except Exception: pass
        try: instr = s.instructions() or ""
        except Exception: pass
    except Exception as e:
        row["err"] = f"scraper:{type(e).__name__}"
    if not ings and ld:
        ings = ld.get("recipeIngredient") or []; yld = yld or str(ld.get("recipeYield") or ""); instr = instr or "x" if ld.get("recipeInstructions") else instr
    text = " ".join(ings).lower()
    row.update(n_ing=len(ings), instr=bool(instr), missing=[m for m in menu if m not in text]); row["yield"] = str(yld)[:20]
    return row

out = {"searches": [], "credits_used": 0}
for dish, spec in DISHES.items():
    for mode, domains in (("open", None), ("structured_hosts", STRUCTURED_HOSTS)):
        results, sec = tavily(spec["q"], domains); out["credits_used"] += 1
        kept = [x for x in results if not any(b in x["url"] for b in BLOCK)]
        rows = [extract(x["url"], spec["menu"]) for x in kept[:8]]
        usable = [r for r in rows if r["n_ing"] > 0]
        out["searches"].append({"dish": dish, "mode": mode, "query": spec["q"], "search_sec": round(sec, 2), "n_results": len(results),
                                "n_kept": len(kept), "n_fetched": len(rows), "n_200": sum(1 for r in rows if r["http"] == 200),
                                "n_usable": len(usable), "n_full_coverage": sum(1 for r in usable if not r["missing"]),
                                "n_with_servings": sum(1 for r in usable if "serv" in r["yield"].lower()),
                                "usable_missing": [r["missing"] for r in usable], "rows": rows})
        print(f"{dish:20} {mode:16} search {sec:4.1f}s results={len(results):2} kept={len(kept):2} fetched={len(rows)} 200={sum(1 for r in rows if r['http']==200)} usable={len(usable)} full-coverage={sum(1 for r in usable if not r['missing'])} servings={sum(1 for r in usable if 'serv' in r['yield'].lower())}  missing={[r['missing'] for r in usable]}")
json.dump(out, open(sys.argv[1], "w"), indent=1)
print("credits used:", out["credits_used"])
