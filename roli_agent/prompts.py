"""The two short LLM instructions of the food path. The menu prompt is the harness's v5 file."""

INTERPRET_PROMPT = """You help a nutrition assistant look up foods in USDA FoodData Central.
Read the user's message and answer with ONE JSON object and nothing else:

{
  "intent": "food_lookup" or "other",
  "food": "the food the user named, in their words",
  "usda_query": "search words in USDA's style: food, then species or variety, then preparation",
  "preparation": "cooked", "raw", or "unknown"
}

Rules:
- "food_lookup" only when the user asks about the nutrition of one specific food or ingredient.
  Anything else (greetings, several foods at once, whole dishes, questions about the assistant) is "other".
- USDA wording: "salmon chinook cooked dry heat", "lettuce romaine raw", "cheese romano".
  Use the species or variety name USDA uses: king salmon is chinook salmon; baked, grilled or broiled fish is "cooked dry heat".
- Never include nutrition values, FDC IDs or estimates in your answer.

User message:
"""

SELECT_PROMPT = """You are choosing a USDA FoodData Central record for the food "{food}" (preparation: {preparation}).
USDA returned these candidates, in USDA's own order (the first is not necessarily right):

{candidates}

Pick the candidate whose description names the same food AND the same preparation.
Answer with ONE JSON object and nothing else:

{{"fdc_id": <one of the fdc_id numbers above, or null if none matches>, "reason": "one short sentence"}}

Never invent an fdc_id. If no candidate matches, use null.
"""


# -- Phase 2B-2: recipe scenarios. Every prompt returns JSON that Python validates; no numbers are asked for. --

RELEVANCE_PROMPT = """You grade how well published recipes match one restaurant menu item. You do not estimate nutrition.

Menu item: "{name}" (section: {section}); printed ingredients: {description}.

Recipes (title, source, yield, cooking methods seen in the method text, ingredient names):
{recipes}

For EACH recipe index, judge three things:
- dish_type: "same" (the same dish, e.g. a tuna crudo for a crudo), "variant" (a close relative, e.g. tuna carpaccio for a crudo,
  a pizza with the same base for a margherita), or "different" (another dish: seared tuna steak for a crudo, pasta with bottarga for a crudo,
  a soup for a salad, a cocktail for a pizza).
- preparation: "same" (same cooking state and technique), "similar" (minor differences, e.g. sliced vs cubed raw fish, baked vs grilled pizza),
  or "different" (e.g. cooked vs raw, deep-fried vs roasted, a laksa soup for a roasted fish). Judge the method text, not the title: a recipe
  whose method grills, chars, roasts or sears the main ingredient of a raw dish (lettuce in a lettuce salad, fish in a crudo) is "different"
  even when its title sounds like the dish; a cooked garnish (toasted seeds, baked cheese on raw leaves) does not make the preparation different.
- course_portion: "same" (a starter recipe for a starter, a main for a main) or "different".

Answer with ONE JSON object and nothing else:
{{"recipes": [{{"index": 1, "dish_type": "same", "preparation": "same", "course_portion": "same", "reason": "one short sentence"}}, ...]}}
Include every index exactly once. Never add nutrition values or quantities.
"""

QUERY_BATCH_PROMPT = """You write search queries for USDA FoodData Central (SR Legacy and Foundation foods) for recipe ingredients.
Dish context: {context}.

Ingredients (id, name as written in the recipe, preparation hint):
{items}

For each id write the USDA-style query: the food, then species or variety, then form or preparation, in USDA's wording.
Examples: "sushi-grade bluefin tuna" (raw) -> "tuna bluefin raw"; "extra-virgin olive oil" -> "oil olive"; "king salmon fillet" (raw) ->
"salmon chinook raw"; "pecorino sardo" -> "cheese romano"; "little gem lettuce" -> "lettuce romaine raw"; "flaky sea salt" -> "salt table";
"shishito peppers" -> "peppers hot chili green raw"; "fior di latte" -> "cheese mozzarella whole milk".
Answer with ONE JSON object and nothing else: {{"queries": [{{"id": 1, "usda_query": "..."}}, ...]}}
Never include numbers, FDC IDs or nutrition values.
"""

SELECT_BATCH_PROMPT = """You choose USDA FoodData Central records for recipe ingredients. Dish context: {context}.
For each ingredient, USDA returned the candidates listed under it (USDA's own order; the first is not necessarily right).

{blocks}

For each ingredient id, pick the candidate whose description names the same food in the same state (raw/cooked) as the hint, and say whether it is:
- "direct": the same food and form (bluefin tuna, raw -> "Fish, tuna, fresh, bluefin, raw"), or
- "proxy": a stand-in you declare as such because USDA has no record for the exact food (pecorino sardo -> "Cheese, romano";
  little gem -> "Lettuce, cos or romaine, raw"). Choose a proxy only when the foods are nutritionally close for saturated fat and cholesterol.
If nothing fits, use null. Never pick a cooked record for a raw hint or a raw record for a cooked hint.
When an [SR Legacy] and a [Foundation] candidate name the SAME food in the SAME preparation state, pick the [SR Legacy] one: it carries household
measures (cups, tablespoons, pieces) and both nutrients, which Foundation records often lack. Never trade away the specific food or the
right state for an [SR Legacy] record: a more specific or correctly prepared [Foundation] record beats a vaguer [SR Legacy] one.
Answer with ONE JSON object and nothing else:
{{"selections": [{{"id": 1, "fdc_id": <one of that ingredient's fdc_id numbers or null>, "match_type": "direct" or "proxy", "reason": "one short sentence"}}, ...]}}
Never invent an fdc_id.
"""


# -- Checkpoint 3D (SPEC_3_mvp.md 12.3, Julius 2026-11-05): one call per dish tags every recipe line. The model never writes a number. --

LINE_TAGS_PROMPT = """You tag the ingredient lines of published recipes for one restaurant dish. You do not estimate nutrition and you never write a quantity.

Menu item: "{name}" (section: {section}); printed ingredients: {description}.

Recipes (title, then the method sentences that name a fat or liquid when the page has them, then each line number and the line as printed):
{recipes}

A block titled "Menu words no recipe lists" names foods the menu prints and no recipe has. Tag them like any line.

For EVERY line give two tags.

role, one of:
- "cooking_medium": ONLY these:
  frying oil: a cup or more of oil used to fry, deep or shallow, or oil the food is covered with and then drained from;
  a marinade, but ONLY when the food is lifted out and the liquid is drained, thrown away or left in the jar: then every liquid of it is a medium (oil, vinegar, juice, soy sauce).
  A marinade that is brushed on, cooked with the food or served on the plate is "eaten";
  oil a food is stored in or served out of (a jar or bowl of olives, feta or vegetables in oil, a confit): only the oil that clings to the food is eaten;
  a brine; a poaching or boiling liquid (water that boils pasta and the salt for that water, a court-bouillon), unless the recipe turns it into a sauce or serves it, when it is "eaten";
  confit fat; or oil wiped on a grill grate.
- "removed": lifted out before serving: bay leaves, whole herb sprigs, rinds, bones, shells, a lemon stuffed in a cavity, aromatics such as a cinnamon stick or star anise.
- "eaten": everything else. Under a cup of oil or fat used to pan-fry, and any oil or fat used to blister, saute, sear, stir-fry, baste or roast, STAYS WITH THE FOOD and is "eaten".
  Oil in a dressing, a drizzle or a sauce is "eaten". Water or stock inside a soup, stew or risotto, or absorbed by a grain, is "eaten".
When in doubt the line is "eaten". A line wrongly left out can put a fatty dish at the top of the ranking, which is the harmful error.

kind, one of:
- "plain_food": a single food: an olive, a fish, salt, flour, an oil.
- "prepared_product": a sauce, paste, dressing, condiment, stock, sausage, spice blend, pesto, salsa, mayonnaise, a bought dough or batter: something made of
  several ingredients.

category, one of: "wine_or_spirit", "beer", "herb", "spice", "salt", "water_or_stock", "cheese", "oil_or_fat", "meat", "poultry", "fish_or_seafood", "egg", "dairy",
"vegetable", "fruit", "grain_or_bread", "legume_or_nut", "sauce_or_condiment", "sweetener", "other". The kind of food the line names, so that a line no database
record matches can still be placed: "Carricante" and "Schiava" are wines ("wine_or_spirit"), "Maldon" is salt, "chanterelles" are a vegetable. "other" when none fits.

Write a "reason" of a few words ONLY for a line tagged cooking_medium, removed or prepared_product. For an eaten plain_food line leave the reason out.

Answer with ONE JSON object and nothing else:
{{"recipes": [{{"index": 1, "lines": [{{"n": 1, "role": "eaten", "kind": "plain_food", "category": "vegetable"}}, {{"n": 2, "role": "cooking_medium", "kind": "plain_food", "category": "oil_or_fat", "reason": "frying bath"}}, ...]}}, ...]}}
Include every recipe index and every line number exactly once. Never add nutrition values, weights or quantities.
"""
