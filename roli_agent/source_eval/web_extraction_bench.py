"""Phase 2B-0: can real recipe pages for the five dishes be extracted deterministically? (scratch script)"""
import json, re, sys, time
import httpx
from recipe_scrapers import scrape_html

DISHES = {
 "Bluefin Crudo (bottarga, muscat grape, chive)": {"menu": ["bottarga", "grape", "chive"], "urls": [
   "https://sitkaseafoodmarket.com/blogs/culinary/recipes/tuna-crudo",
   "https://sitkaseafoodmarket.com/blogs/recipes/tuna-crudo-with-pickled-shallots-and-smoked-salt",
   "https://www.lcbo.com/en/recipe/yellowfin-tuna-crudo-with-radish-cucumber-capers/F202302005",
   "https://archive.jamesbeard.org/recipes/tuna-crudo",
   "https://www.russh.com/?p=306898",
   "https://www.cubitthouse.co.uk/dish-with-tish-sea-bass-crudo-yellow-peach-bottarga-and-marjoram"]},
 "Little Gem Lettuces (tahini vinaigrette, pecorino sardo, toasted sesame)": {"menu": ["tahini", "pecorino", "sesame", "little gem"], "urls": [
   "https://andybaraghani.com/recipes/little-gem-wedge-salad-with-tahini-ranch",
   "https://thedevilwearssalad.com/little-gem-salad/",
   "https://patient.info/recipes/vegetarian-recipes/little-gem-wedge-salad-with-tahini-ranch",
   "https://clearspring.co.uk/blogs/recipes/grilled-little-gem-salad-with-white-tahini-dressing",
   "https://more.ctv.ca/food/recipes/gem-lettuce-with-fridge-raid-dressing.html",
   "https://modernrustic.substack.com/p/a-siren-song-at-trader-joes"]},
 "Heirloom Tomatoes (pluot, shiso, genovese basil, sourdough)": {"menu": ["pluot", "shiso", "basil", "sourdough", "tomato"], "urls": [
   "https://www.purewow.com/recipes/heirloom-tomato-basil-olive-croutons",
   "https://www.saveur.com/recipes/heirloom-tomato-stone-fruit-salad-garlicky-croutons/",
   "https://www.lifeisbutadish.com/heirloom-tomato-salad-w-basil-vinaigrette-homemade-croutons/",
   "https://www.aberdeenskitchen.com/2016/08/heirloom-tomato-panzanella-salad/",
   "https://stacylynharris.com/panzanella-recipe-tomato-salad/",
   "https://www.pardonyourfrench.com/heirloom-tomato-bread-salad-with-fresh-herbs/"]},
 "Margherita (tomato, fior di latte, basil)": {"menu": ["tomato", "fior di latte", "basil"], "urls": [
   "https://www.ciaoitalia.com/recipes/pizza-margherita",
   "https://filippoberio.com/recipes/pizza-margherita/",
   "https://www.finedininglovers.com/recipes/pizza-margherita-ciro-salvo",
   "https://www.tastemade.com/recipes/pizza-margherita",
   "https://www.newidea.com.au/recipe/food/margherita-pizza-with-fior-di-latte/",
   "https://saputofoodservice.ca/en/recipes/classic-margherita-pizza"]},
 "King Salmon (squash, corn, basil, shishito)": {"menu": ["salmon", "squash", "corn", "basil", "shishito"], "urls": [
   "https://www.landolakes.com/recipe/9679/salmon-summer-squash-with-basil",
   "https://www.alaskaseafood.org/recipe/alaska-slow-roasted-king-salmon-with-mexican-street-corn-salad/",
   "https://hogislandoysters.com/recipes/salmon-grilled-corn-sauce/",
   "https://sunset.com/recipe/slow-roasted-curried-salmon-corn-tomato",
   "https://30seconds.com/food/tip/83087/Roasted-Salmon-Recipe-With-Corn-Tomatoes-Tastes-Like-Summer-8-Ingredients-25-Minutes",
   "https://www.goodtaste.tv/?p=68231"]},
}
WEIGHT = re.compile(r"\b(\d+(?:[.,]\d+)?)\s*(g|gram|grams|kg|oz|ounce|ounces|lb|lbs|pound|pounds)\b", re.I)
VOLUME = re.compile(r"\b(\d+(?:[.,]\d+)?|\d+/\d+|[½¼¾⅓⅔⅛])\s*(tsp|teaspoon|teaspoons|tbsp|tablespoon|tablespoons|cup|cups|ml|l|fl oz|litre|liter)s?\b", re.I)
COUNT = re.compile(r"^\s*(\d+(?:[.,]\d+)?|\d+/\d+|[½¼¾⅓⅔⅛]|an?|one|two|three|four)\s", re.I)
VAGUE = re.compile(r"to taste|pinch|handful|drizzle|as needed|some|a few|sprinkle|dash", re.I)

def classify(line):
    if WEIGHT.search(line): return "weight"
    if VOLUME.search(line): return "volume"
    if VAGUE.search(line) and not COUNT.search(line): return "vague"
    if COUNT.search(line): return "count"
    return "none"

def ldjson_recipe(html):
    for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.S | re.I):
        try: data = json.loads(m.group(1).strip())
        except Exception: continue
        stack = [data]
        while stack:
            x = stack.pop()
            if isinstance(x, dict):
                t = x.get("@type"); t = t if isinstance(t, list) else [t]
                if "Recipe" in t: return x
                stack.extend(x.values())
            elif isinstance(x, list): stack.extend(x)
    return None

rows = []
client = httpx.Client(headers={"User-Agent": "Mozilla/5.0 (compatible; RoliRecipeEval/0.1; +research)"}, follow_redirects=True, timeout=15)
for dish, spec in DISHES.items():
    for url in spec["urls"]:
        row = {"dish": dish, "url": url, "http": None, "sec": None, "jsonld": False, "scraper": False, "n_ing": 0, "yield": "", "instr": False,
               "weight": 0, "volume": 0, "count": 0, "vague": 0, "none": 0, "coverage": [], "missing": [], "title": "", "err": ""}
        t0 = time.perf_counter()
        try:
            r = client.get(url); row["http"] = r.status_code; html = r.text
        except Exception as e:
            row["err"] = type(e).__name__; rows.append(row); continue
        row["sec"] = round(time.perf_counter() - t0, 1)
        if r.status_code != 200: rows.append(row); continue
        ld = ldjson_recipe(html); row["jsonld"] = ld is not None
        ings, yld, instr, title = [], "", "", ""
        try:
            s = scrape_html(html, org_url=url, supported_only=False)
            ings = s.ingredients() or []; row["scraper"] = bool(ings)
            try: yld = s.yields() or ""
            except Exception: pass
            try: instr = s.instructions() or ""
            except Exception: pass
            try: title = s.title() or ""
            except Exception: pass
        except Exception as e:
            row["err"] = f"scraper:{type(e).__name__}"
        if not ings and ld:
            ings = ld.get("recipeIngredient") or []; yld = yld or str(ld.get("recipeYield") or ""); title = title or ld.get("name", "")
            instr = instr or json.dumps(ld.get("recipeInstructions") or "")
        row.update(n_ing=len(ings), **{"yield": str(yld)[:30]}, instr=bool(instr), title=title[:60])
        for line in ings: row[classify(line)] += 1
        text = " ".join(ings).lower()
        row["coverage"] = [m for m in spec["menu"] if m in text]; row["missing"] = [m for m in spec["menu"] if m not in text]
        row["lines_sample"] = ings[:4]
        rows.append(row)
json.dump(rows, open(sys.argv[1], "w"), indent=1)
print(f"{'dish':28} {'http':>4} {'ld':>3} {'scr':>3} {'ing':>3} {'yield':>10} {'ins':>3} {'wt':>2} {'vol':>3} {'cnt':>3} {'vag':>3} {'non':>3}  missing-menu-ingredients | url")
for r in rows:
    print(f"{r['dish'][:28]:28} {str(r['http']):>4} {str(r['jsonld'])[0]:>3} {str(r['scraper'])[0]:>3} {r['n_ing']:>3} {r['yield'][:10]:>10} {str(r['instr'])[0]:>3} {r['weight']:>2} {r['volume']:>3} {r['count']:>3} {r['vague']:>3} {r['none']:>3}  {','.join(r['missing']) or '-':28} | {r['url'][:70]} {r['err']}")
