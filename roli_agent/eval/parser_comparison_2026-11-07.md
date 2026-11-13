# Roli's ingredient-line parser against ingredient-parser-nlp 2.9.2

Date: 2026-11-07. Side task to Checkpoint 3J; no Roli code changed, no model, search or USDA call made. Per-line results: `parser_comparison_2026-11-07_lines.csv`
(2783 lines, both parsers' fields and the agreement flags); the 150 hand-judged lines: `parser_comparison_2026-11-07_judgements.csv`.

## 1. Safety steps

1. **Download and hashes.** `pip download ingredient-parser-nlp==2.9.2 --no-deps` for the wheel and, with `--no-binary :all:`, the sdist, into a directory of their own in the session scratchpad.
   SHA-256: wheel `0ada9331ef1bc6966930d0924048a9b739924b2ab32411dcb8fdca7aa00c6415` (4,262,601 bytes), sdist `96f4c9bfe119ffdb3ee6ae1d500088ad56c407c0bfbf3d47c869e4e58c0aabc7` (4,255,928 bytes).
   **Both match the expected values**, so the work went on.
2. **Read before installing.** The wheel holds 24 Python files under `ingredient_parser/`, the model `en/data/model.en.json.gz` (586 KB, a JSON of CRF feature weights, loaded with `gzip` and `json.loads`, no pickle),
   `ingredient_tagdict.json.gz`, GloVe embeddings `ingredient_embeddings.35d.glove.txt.gz` (3.4 MB), `fdc_ingredients.csv.gz` (for its optional USDA foundation-food matching, off by default), a model card and `pint_extensions.txt`.
   Dependencies declared: `nltk>=3.9.1`, `pint>=0.25.0`, `numpy`; Python 3.11 or newer. Grep over every `.py` for socket, urllib, requests, http, subprocess, os.system, os.environ, getenv, pickle, eval, exec, download and writing opens:
   - **No** socket, urllib, requests, os.environ, getenv, pickle, eval or exec. The only `open(` is `open(path, "rb")` reading the model file. The only http strings are documentation URLs and the FDC URL the dataclass builds for display.
   - **One subprocess:** `_common.show_model_card()` runs `open <model card path>` on macOS (`xdg-open` on Linux, `os.startfile` on Windows). It opens a file in a viewer and runs only when called; nothing here calls it.
   - **One network path, at import time:** `en/_utils.py` calls `download_nltk_resources()` when imported, which looks for NLTK's `averaged_perceptron_tagger_eng` data and, if it is missing, calls `nltk.downloader.download(...)`,
     fetching it from NLTK's servers. A parser needs the tagger, but the package does not ship it. I fetched that NLTK data myself, in a separate step with the network on, into a folder inside the throwaway environment
     (`NLTK_DATA` pointed there, 6.9 MB), so the library's own import found it and never reached for the network.
3. **Install and run.** Fresh venv `roli_agent/.venv_parser_test` created from Roli's own Python 3.13 interpreter (the system `python3` is 3.9, below the library's floor). Installed from the downloaded wheel; pip pulled
   `nltk 3.10.4, Pint 0.26.2, numpy 2.5.4` and their dependencies (click, joblib, regex, tqdm, flexcache, flexparser, platformdirs, typing_extensions, cloudpickle, defusedxml). The comparison ran under macOS
   `sandbox-exec -p '(version 1)(allow default)(deny network*)'` with `python -I`; a control `curl` under the same profile could not resolve pypi.org, so the network was off for the process. Both parser runs finished with
   0 library errors and 0 Roli errors.
4. **Deleted:** the venv `roli_agent/.venv_parser_test` was removed after the runs (see the end of this file). Roli's own `.venv` was not touched; nothing was installed into it.

## 2. The lines

Measured on the 3I pass A runs (2026-11-07): for each menu, the recipe lines (origin `recipe`) that ended **unparsed** (the line carries a number or a number word but Roli read no quantity), **unweighed** (no grams: the
conversion waited for a USDA portion that never came, or the blocker was `no_usda_portion`) or with a **parsing blocker** (`unknown_quantity`, `optional_unknown_quantity`, `seasoning_unknown_quantity`, `no_usda_portion`,
`cooking_medium_unknown_amount`). A line is counted once per recipe it appears in.

| menu | troubled recipe lines | unparsed | unweighed | blocker | |
|---|---|---|---|---|---|
| 05 Ren's Kitchen | 113 | 5 | 54 | 87 | chosen |
| 19 Dwarf Grill | 69 | 1 | 22 | 52 | chosen |
| 11 Mother's Tacos | 64 | 5 | 30 | 43 | chosen |
| 08 The Greyhound | 55 | 1 | 18 | 45 | chosen |
| 01 Zuni Cafe | 48 | 5 | 13 | 41 | chosen |
| 10 Alex's Kitchen | 48 | 2 | 29 | 31 | |
| 02 Zuni second photo | 47 | 5 | 12 | 40 | |
| 09 The Shed breakfast | 42 | 1 | 28 | 26 | |
| 03 Flour + Water | 37 | 3 | 15 | 28 | |
| 04 own photo | 25 | 0 | 11 | 18 | |
| 06 Pizzaface | 23 | 2 | 9 | 19 | |
| 23 Seafood chalkboard | 16 | 1 | 6 | 13 | |
| 07 Cafe Rust (drinks) | 0 | 0 | 0 | 0 | |

The five chosen: Ren's Kitchen, Dwarf Grill, Mother's Tacos, The Greyhound, Zuni Cafe (Alex's Kitchen ties Zuni at 48 occurrences; Zuni has more distinct troubled lines after de-duplication, and Alex's Kitchen's recipes
overlap Zuni's less, so the tie was broken towards the menu whose lines were already in the set). Every distinct recipe line from those five menus' runs: **2783 lines**, of which 318
were troubled in Roli's runs.

## 3. Agreement

Fair comparison rules: the library writes fractions ("3/2", "1/4") and Roli decimals, so quantities are compared as numbers; a range is agreed when Roli's low and high equal the library's quantity and maximum;
the library's units are pint names or free text ("large cloves", "tablespoons sprigs"), brought to Roli's spelling by singularising, folding plurals and removing size words; a bare count is Roli's `each` and the
library's empty unit; names are compared lower-cased without punctuation, "lenient" when one contains the other or the library's "X | Y" alternatives match Roli's "X or Y".

| field | agree | disagree |
|---|---|---|
| quantity | 2676 | 107 |
| unit | 2614 | 169 |
| food name, strict | 2083 | 700 |
| food name, lenient | 2759 | 24 |
| all three (lenient name) | 2550 | 233 |
| all three (strict name) | 2041 | 742 |
| produced any quantity | Roli 2394, library 2448 | |

Where the names differ strictly but not leniently it is mostly the library stripping the preparation ("chopped green onions" against "green onions", prep "chopped") or splitting alternatives. The library returns
several amounts on 288 lines (221 of them with a weight or volume as a later amount: "1 package" + "5 ounces", "3" + "560 grams"); Roli keeps such a weight as a note its converter reads.

## 4. Hand judgement, 150 lines

100 drawn at random (seed 0) from the 233 lines where the two disagree on quantity, unit or name, plus the 50 lines that caused the most trouble in Roli's runs (unparsed first, then unweighed, by
occurrences; 9 of the 50 also fell in the random 100 and are judged in both sets). Verdicts: **library** (its reading is right, Roli's is not), **roli**, **both** (both usable), **neither**.

| set | library | roli | both | neither |
|---|---|---|---|---|
| random 100 (disagreements) | 57 | 15 | 19 | 9 |
| 50 most troubled | 18 | 0 | 27 | 5 |
| all 150 | 75 | 15 | 46 | 14 |

**What the library does better (57 of the 100 disagreements):** a bare "pinch", "handful", "small bunch" or "generous grind" is one of that unit (Roli reads no quantity, so the line blocks the recipe); "Juice of 1 lemon",
"Zest 1/2 lemon" (Roli has no quantity); "optional: 1/2 cup ..." and "(1) tsp." and "(2) ... steaks" (a prefix or bracket stops Roli); "1 and 1/2 cups", "2 and 3/4 cups" (Roli reads 1 or 2 each); container and
count units ("package", "box", "tin", "cube", "loaf", "sheet", "rashers", "ribs", "cloves", "sprigs") with a clean food name, where Roli writes `each` and leaves the unit word in the name ("package vegan bacon"); size
words as size, not as the unit ("1 small head garlic": unit "small head", name "garlic"; Roli: unit "small", name "head garlic").

**What Roli does better (15):** a weight before a container is the amount ("14 ounce can", "400g can", "100g bag", "200g pack", "9 ounce box": Roli 14 oz / 400 g / 100 g / 200 g / 9 oz; the library's first amount
is "1 can" or "1 bag", though the weight sits in its later amounts on all five); "Tbl." as tablespoon (the library leaves "Tbl." in the name on three lines); a checkbox glyph "▢" (the library reads it as the unit);
"1 handfull" (typo); "sliced into 8 (1/2-inch) slices" (the library takes "slice" as the unit, Roli keeps the apple); "4 cups (1-inch) chunks" (the library's unit "cups chunks").

**Neither (14):** every "X plus Y" line ("1/2 cup plus 2 tablespoons olive oil", 9 lines): Roli reads the first amount with a polluted name, the library reads no quantity; a compound line of three ingredients;
"3 - 1/2 cup heavy cream" (ambiguous on the page); "Scant 1/2 cup" (the library's unit is "Scant", Roli reads nothing); "(2) Tbl." (quantity to one, unit to the other); "vegan scrambled eggs for 4" (the
library's name "eggs" drops the point).

**The 50 most troubled lines** are mostly not parsing failures: 27 are "both" (1 can baked beans, 1 cup whole milk, 1 bunch kale, 1 vanilla bean) where both parsers read the line and the trouble was the weighing
step (no USDA portion for a can, a cup of this food, a bunch) or the USDA match. The library would help on 18 of the 50: the "optional:" and bracketed-count lines, "1 recipe ..." read literally, "Generous 8 ounces",
"One-half of a 3 1/2-ounce package", "1 heaping tablespoon" (Roli: 1 each), and the container units.

The judged lines with both parses and the reason are in the judgements CSV; the full tables follow.

### Random 100

| line | Roli: quantity unit / name / size / prep | library: quantity unit / name / size / prep | verdict | why |
|---|---|---|---|---|
| 4 Tbl. prepared garlic butter | 4 tbsp | prepared garlic butter | size - | prep  | 4 - | Tbl. prepared garlic butter | size - | prep  | **roli** | library leaves 'Tbl.' in the name and no unit |
| 1 large sprig of Fresh Rosemary | 1 large | sprig of fresh rosemary | size large | prep  | 1 large sprig | Fresh Rosemary | size - | prep  | **library** | unit 'large sprig', name rosemary; Roli puts 'sprig' in the name and 'large' as the unit |
| 1 ea Romaine Lettuce, head, cleaned, cored and chiffonaded | 1 each | romaine lettuce | size - | prep head; cleaned; cored and chif | 1 head | ea Romaine Lettuce | size - | prep cleaned, cored and chiffon | **roli** | library keeps 'ea' in the name |
| A little water | 1 each | little water | size - | prep  | - - | A little water | size - | prep  | **library** | Roli invents a quantity of 1 for 'a little' |
| Handful chopped fresh parsley leaves | - handful | chopped fresh parsley leaves | size - | prep  | 1 Handful | fresh parsley leaves | size - | prep chopped | **library** | a bare 'handful' is one handful; Roli has no quantity |
| pinch of salt | - pinch | salt | size - | prep  | 1 pinch | salt | size - | prep  | **library** | a bare 'pinch' is one pinch; Roli has no quantity |
| 1 (1/4-ounce) packet active dry yeast active dry yeast (2 1/4 teaspoons) | 1 each | packet active dry yeast active dry yeast | size - | prep 1/4- | 1 packet | active dry yeast active dry yeast | size - | prep  | **both** | Roli keeps the 1/4-ounce note its converter reads; the library gives the unit 'packet' |
| ▢ ¼ cup fresh cilantro | 0.25 cup | fresh cilantro | size - | prep  | 1 ▢ | fresh cilantro | size - | prep  | **roli** | library takes the checkbox glyph as the unit and quantity 1 |
| 2 tablespoons plus 2 tablespoons avocado or olive oil | 2 tbsp | plus 2 tablespoons avocado or olive oil | size - | prep  | - - | avocado oil | olive oil | size - | prep  | **neither** | '2 tablespoons plus 2 tablespoons': Roli reads 2 with a polluted name, the library gives no quantity; 4 tbsp is right |
| 6 Little Gem leaves | 6 leaf | little gem | size - | prep  | 6 - | Little Gem leaves | size - | prep  | **both** | 6 leaves either way |
| optional: 1/2 cup light cream or half and half | - - | optional: 1/2 cup light cream or half and half | size - | prep  | 1/2 cup | light cream | half and half | size - | prep  | **library** | 'optional:' prefix stops Roli reading 1/2 cup |
| 1 small head garlic, halved horizontally | 1 small | head garlic | size small | prep halved horizontally | 1 small head | garlic | size - | prep halved horizontally | **library** | unit 'small head', name garlic |
| 3 - 1/2 cup heavy cream | 3 cup | heavy cream | size - | prep  | 1/2/3 cup | heavy cream | size - | prep  | **neither** | '3 - 1/2 cup' is ambiguous on the page itself |
| 1 (8-oz) tub Beans for Beings Southwest Black Bean Dip | 1 each | tub beans for beings southwest black bean dip | size - | prep | 1 tub | Beans for Beings Southwest Black Bean Dip | size - | prep  | **both** | Roli keeps the 8-oz note, the library the unit tub |
| 4 medium to large tomatoes (about 2 pounds), cored | 4 medium | to large tomatoes | size medium | prep about 2 pounds; core | 4 - | tomatoes | size medium to large | prep cored | **library** | size 'medium to large', name tomatoes; Roli's name is 'to large tomatoes' |
| Cheese slices (of choice) | - - | cheese slices | size - | prep of choice | - slices | Cheese (of choice) | size - | prep  | **both** | no quantity on the line; both say so |
| 1 recipe caramel sauce (, or one 16oz jar caramel topping) | - - | caramel sauce | size - | prep , or one 16oz jar caramel topping | 1 recipe | caramel sauce | size - | prep  | **library** | '1 recipe' read literally; Roli treats it as a sub-recipe reference (by design) |
| Vegetable or peanut oil, for frying (about 6 cups, enough for 3–4 inches in the  | - - | vegetable or peanut oil | size - | prep about 6 cups, enough for | 6 cup | Vegetable oil | peanut oil | size - | prep  | **library** | 'about 6 cups' read from the note; Roli leaves frying oil unquantified by its medium rule |
| 2 tablespoons sprigs fresh parsley, chopped | 2 tbsp | sprigs fresh parsley | size - | prep chopped | 2 tablespoons sprigs | fresh parsley | size - | prep chopped | **roli** | 2 tbsp; the library's unit is 'tablespoons sprigs' |
| For the glaze: | - - | for the glaze: | size - | prep  | - - |  | size - | prep  | **library** | a heading, not an ingredient; Roli names it |
| ½ cup plus 2 tablespoons extra-virgin olive oil | 0.5 cup | plus 2 tablespoons extra-virgin olive oil | size - | prep  | - - | extra-virgin olive oil | size - | prep  | **neither** | 'plus' line: Roli 1/2 cup with a polluted name, the library nothing |
| Handful of torn mint leaves | - handful | torn mint leaves | size - | prep  | 1 Handful | torn mint leaves | size - | prep  | **library** | one handful |
| 2 sheets of ready-rolled puff pastry (640g) (we used Jus Rol) | 2 each | sheets of ready-rolled puff pastry | size - | prep 640g; we u | 2 sheets | ready-rolled puff pastry | size - | prep  | **both** | Roli keeps the 640g note, the library the unit sheets |
| 9 ounce box of Jovial Gluten Free Tagliatelle pasta | 9 oz | box of jovial gluten free tagliatelle pasta | size - | prep  | 1 box | Jovial Gluten Free Tagliatelle pasta | size - | prep  | **roli** | 9 oz is the usable amount; the library's first amount is 1 box |
| 1 (1 pound) ball store bought dough | 1 each | ball store bought dough | size - | prep 1 pound | 1 ball | store bought dough | size - | prep  | **both** | Roli keeps the 1 pound note; the library the unit ball |
| 2 Tbsp. plus 3 cups (391 g) bread flour, plus more for surface | 2 tbsp | plus 3 cups bread flour | size - | prep 391 g; plus more for  | - - | bread flour | size - | prep  | **neither** | '2 Tbsp. plus 3 cups': neither gives the total |
| Juice of 1 lemon | - - | juice of 1 lemon | size - | prep  | 1 - | lemon | size - | prep Juice of | **library** | 1 lemon, preparation 'juice of'; Roli has no quantity |
| 1 handfull arugula | 1 handful | arugula | size - | prep  | 1 - | handfull arugula | size - | prep  | **roli** | typo 'handfull' read as a handful; the library leaves it in the name |
| handful of kale leaves | - handful | kale leaves | size - | prep  | 1 handful | kale leaves | size - | prep  | **library** | one handful |
| 2 Tins (800g) Baked Beans (choose reduced salt & sugar whenever possible) | 2 each | tins baked beans | size - | prep 800g; choose reduced salt &  | 2 Tins | Baked Beans | size - | prep  | **both** | 2 tins, 800g note kept by Roli |
| 2 (9-ounce) packages Nabisco Famous Chocolate Wafers (see Recipe Notes) | - - | packages nabisco famous chocolate wafers | size - | prep 9-ounce | 2 packages | Nabisco Famous Chocolate Wafers | size - | prep  | **library** | Roli reads no quantity at all from '2 (9-ounce) packages' |
| Pinch of cayenne | - pinch | cayenne | size - | prep  | 1 Pinch | cayenne | size - | prep  | **library** | one pinch |
| 2 hearts of romaine lettuce, cored, leaves left whole, chilled | 2 each | hearts of romaine lettuce | size - | prep cored; leaves left  | 2 hearts | romaine lettuce | size - | prep cored, leaves left whole, c | **both** | 2 hearts either way |
| 2 celery sticks, roughly diced | 2 each | celery sticks | size - | prep roughly diced | 2 sticks | celery | size - | prep roughly diced | **library** | unit sticks, name celery |
| 5 bay leaves | 5 leaf | bay | size - | prep  | 5 - | bay leaves | size - | prep  | **both** | 5 bay leaves either way |
| rosemary sprig (to garnish) | - - | rosemary sprig | size - | prep to garnish | 1 sprig | rosemary | size - | prep  | **library** | 1 sprig; Roli has no quantity |
| 1/2 medium bunch fresh thyme, plus more for garnish | 0.5 medium | bunch fresh thyme | size medium | prep plus more for garn | 1/2 medium bunches | fresh thyme | size - | prep  | **library** | unit 'medium bunches', name thyme |
| 1 small garlic clove crushed | 1 small | garlic clove crushed | size small | prep  | 1 small clove | garlic | size - | prep crushed | **library** | unit 'small clove', name garlic, preparation crushed |
| optional: 1/4 cup cheddar cheese | - - | optional: 1/4 cup cheddar cheese | size - | prep  | 1/4 cup | cheddar cheese | size - | prep  | **library** | 'optional:' prefix stops Roli |
| 4 large leaves of Bibb lettuce | 4 large | leaves of bibb lettuce | size large | prep  | 4 large leaves | Bibb lettuce | size - | prep  | **library** | unit 'large leaves', name Bibb lettuce |
| 2 celery ribs, finely chopped | 2 each | celery ribs | size - | prep finely chopped | 2 ribs | celery | size - | prep finely chopped | **library** | unit ribs, name celery |
| 1 small Granny Smith apple, cored and sliced into 8 (1/2-inch) slices | 1 small | granny smith apple | size small | prep 1/2-inch; cored and s | 1 slice | Granny Smith apple | size small | prep cored and sliced into | **roli** | the library takes 'slices' from the cutting instruction as the unit |
| 1 cube vegetable stock | 1 each | cube vegetable stock | size - | prep  | 1 cube | vegetable stock | size - | prep  | **library** | unit cube |
| 3 packages cream cheese, (room temperature (8oz or 250g each)) | 3 each | packages cream cheese | size - | prep room temperature (8oz o | 3 packages | cream cheese | size - | prep room temperature | **both** | 3 packages; Roli keeps the '8oz or 250g each' note |
| 1 box panko bread crumbs | 1 each | box panko bread crumbs | size - | prep  | 1 box | panko bread crumbs | size - | prep  | **library** | unit box |
| Small bunch of fresh coriander | - small | bunch of fresh coriander | size small | prep  | 1 Small bunch | fresh coriander | size - | prep  | **library** | one small bunch; Roli has no quantity |
| (1) tsp. herb salt of choice (we added some smoked paprika to ours) | - tsp | herb salt of choice | size - | prep 1; we added some smoked pa | 1 teaspoon | herb salt of choice | size - | prep  | **library** | a bracketed count '(1)' stops Roli |
| 8 garlic, cloves, unpeeled | 8 each | garlic | size - | prep cloves; unpeeled | 8 cloves | garlic | size - | prep unpeeled | **library** | 8 cloves of garlic |
| 1/2 tbsp+ lime juice | 0.5 tbsp | + lime juice | size - | prep  | 1/2 - | tbsp+ lime juice | size - | prep  | **roli** | 1/2 tbsp; the library leaves 'tbsp+' in the name |
| 4 tender sprigs fresh thyme, marjoram, rosemary or sage, about 1/2 inch long | 4 each | tender sprigs fresh thyme | size - | prep marjoram; rosemary  | 4 tender sprigs | fresh thyme | fresh marjoram | fresh rosemary | fres | **library** | unit 'tender sprigs', four herb alternatives |
| 8 fresh sage leaves, finely chopped | 8 leaf | fresh sage | size - | prep finely chopped | 8 - | fresh sage leaves | size - | prep finely chopped | **both** | 8 sage leaves either way |
| Pinch red pepper flakes | - pinch | red pepper flakes | size - | prep  | 1 Pinch | red pepper flakes | size - | prep  | **library** | one pinch |
| 3/4 cup raw sunflower or pumpkin seeds (or mix of both!) | 0.75 cup | raw sunflower or pumpkin seeds | size - | prep or mix of bo | 3/4 cup | raw sunflower seeds | raw pumpkin seeds | size - | prep  | **both** | 3/4 cup either way |
| 2 sheets puff pastry from 1 (17- or 18-ounce) package, thawed in fridge for 24 h | 2 each | sheets puff pastry from 1 package | size - | prep 17- or 18-o | 2 sheets | puff pastry from | size - | prep thawed in fridge for 24 ho | **both** | 2 sheets; the library's name is cut short, Roli's carries 'from 1 package' |
| 1 red onion cut into 6 thick slices | 1 slice | red onion cut into 6 thick | size - | prep  | 1 - | red onion | size - | prep cut into 6 thick slices | **library** | Roli takes 'slices' from the cutting instruction as the unit |
| 1 and 1/2 cups (180g) graham cracker crumbs (about 12 full-sheet graham crackers | 1 each | and 1/2 cups graham cracker crumbs | size - | prep 180g; abou | 3/2 cup | graham cracker crumbs | size - | prep  | **library** | '1 and 1/2 cups' read as 3/2 cup; Roli reads 1 each |
| 100g bag mixed rocket , spinach and watercress salad | 100 g | mixed rocket | size - | prep spinach and watercress salad | 1 bag | mixed rocket | size - | prep spinach and watercress salad | **roli** | 100 g is the usable amount; the library's first amount is 1 bag |
| 1 package vegan bacon (I like to use the King's Vegetarian Bacon or my Rice Pape | 1 each | package vegan bacon | size - | prep I like to use the King's  | 1 package | vegan bacon | size - | prep  | **library** | unit package |
| A 4 – 5 ounce chunk or slice of day-old levain or sourdough bread or other chewy | 1 each | 4 | size - | prep 5 ounce chunk or slice of day-old levain or | 4/5 ounces chunks | day-old levain other chewy | day-old sourdough bre | **library** | 4-5 ounces; Roli names the ingredient '4' |
| 1 dried avocado leaf | 1 leaf | dried avocado | size - | prep  | 1 - | dried avocado leaf | size - | prep  | **both** | 1 leaf either way |
| Leaves of 3 to 4 sprigs fresh thyme | - leaf | 3 to 4 sprigs fresh thyme | size - | prep  | 3/4 sprigs | Leaves of fresh thyme | size - | prep  | **library** | 3-4 sprigs; Roli has no quantity |
| 2 and 1/4 teaspoons Platinum Yeast from Red Star (1 standard packet)* | 2 each | and 1/4 teaspoons platinum yeast from red star * | size - | p | 9/4 teaspoon | Platinum Yeast from Red Star | size - | prep  | **library** | '2 and 1/4 teaspoons' read as 9/4 tsp; Roli 2 each |
| Pinch salt | - pinch | salt | size - | prep  | 1 Pinch | salt | size - | prep  | **library** | one pinch |
| generous grind of black pepper | - - | generous grind of black pepper | size - | prep  | 1 generous grind | black pepper | size - | prep  | **library** | one generous grind; Roli nothing |
| 1/4 cup chopped green onions (scallions), white and green parts | 0.25 cup | chopped green onions | size - | prep scallions; white and g | 1/4 cup | green onions (scallions) | size - | prep chopped | **both** | 1/4 cup either way |
| 2 small-medium aubergine (or one extra large) | 2 small | -medium aubergine | size small | prep or one extra large | 2 - | small-medium aubergine | size - | prep  | **library** | Roli's name is '-medium aubergine' |
| 14 ounce can sweetened condensed milk | 14 oz | can sweetened condensed milk | size - | prep  | 1 can | sweetened condensed milk | size - | prep  | **roli** | 14 oz is the usable amount; the library's first amount is 1 can |
| 2 and 3/4 cups (344g) all-purpose flour (spooned & leveled), plus more as needed | 2 each | and 3/4 cups all-purpose flour | size - | prep 344g; spooned  | 11/4 cup | all-purpose flour | size - | prep (spooned & leveled) | **library** | '2 and 3/4 cups' read as 11/4 cup; Roli 2 each |
| 1x 415g/14oz tin of Baked Beans | 1 each | x 415g/14oz tin of baked beans | size - | prep  | 1 tin | Baked Beans | size - | prep  | **library** | name 'Baked Beans', unit tin; Roli's name starts 'x 415g/14oz tin' |
| 3 large cloves garlic, smashed | 3 large | cloves garlic | size large | prep smashed | 3 large cloves | garlic | size - | prep smashed | **library** | unit 'large cloves', name garlic |
| One-half of a 3 ½-ounce package achiote paste (available to Mexican groceries; r | - - | one-half of a 3 ½-ounce package achiote paste | size - | prep av | 1/2 packages | achiote paste | size - | prep  | **library** | 'one-half of a ... package' read as 1/2 package; Roli nothing |
| pinch of all-purpose flour | - pinch | all-purpose flour | size - | prep  | 1 pinch | all-purpose flour | size - | prep  | **library** | one pinch |
| 1 fresh or dried bay leaf | 1 leaf | fresh or dried bay | size - | prep  | 1 - | fresh bay leaf | dried bay leaf | size - | prep  | **both** | 1 bay leaf either way |
| 1 (8 ounce) tube Pillsbury Original crescent rolls | 1 each | tube pillsbury original crescent rolls | size - | prep 8 ounc | 1 tube | Pillsbury Original crescent rolls | size - | prep  | **both** | Roli keeps the 8 ounce note, the library the unit tube |
| 4 cups (1-inch) chunks of rustic sourdough bread | 4 cup | chunks of rustic sourdough bread | size - | prep 1-inch | 4 cups chunks | rustic sourdough bread | size (1 inch) | prep  | **roli** | 4 cups; the library's unit is 'cups chunks' |
| 2 bay leaves | 2 leaf | bay | size - | prep  | 2 - | bay leaves | size - | prep  | **both** | 2 bay leaves either way |
| 1 small head green cabbage, outer leaves removed, shredded (about 1 ½ pounds) | 1 small | head green cabbage | size small | prep about 1 1/2 pounds; o | 1 small head | green cabbage | size - | prep outer leaves removed, shr | **library** | unit 'small head', name green cabbage |
| 2 Tbl. fresh chopped Italian parsley | 2 tbsp | fresh chopped italian parsley | size - | prep  | 2 - | Tbl. | Italian parsley | size - | prep fresh chopped | **roli** | 2 tbsp; the library leaves 'Tbl.' as a name |
| 1/3 cup plus 1 Tbs. mild olive oil | 0.3333333333333333333333333333 cup | plus 1 tbs. mild olive oil | size | - - | mild olive oil | size - | prep  | **neither** | 'plus' line |
| 3 (8-ounce) packages chocolate chip cookies, such as Tate's Bake Shop | 3 each | packages chocolate chip cookies | size - | prep 8-ounce; such | 3 packages | chocolate chip cookies | size - | prep  | **both** | 3 packages; Roli keeps the 8-ounce note |
| 1 recipe Spicy Slaw, recipe follows | - - | spicy slaw | size - | prep  | 1 recipe | Spicy Slaw | size - | prep  | **library** | '1 recipe' literal; Roli's sub-recipe reading |
| Pinch of salt and pepper | - pinch | salt and pepper | size - | prep  | 1 Pinch | salt | pepper | size - | prep  | **library** | one pinch |
| 200g pack shortbread biscuits | 200 g | shortbread biscuits | size - | prep  | 200 g packs | shortbread biscuits | size - | prep  | **roli** | 200 g; the library's unit is 'g packs' |
| 4 medium sprigs fresh thyme | 4 medium | sprigs fresh thyme | size medium | prep  | 4 medium sprigs | fresh thyme | size - | prep  | **library** | unit 'medium sprigs' |
| 2 small cloves garlic, minced | 2 small | cloves garlic | size small | prep minced | 2 small cloves | garlic | size - | prep minced | **library** | unit 'small cloves' |
| 1 stick of celery or ¼ red pepper, chopped | 1 each | stick of celery or 1/4 red pepper | size - | prep chopped | 1 stick | celery | size - | prep chopped | **library** | unit stick, name celery; the alternative is dropped by both in effect |
| Pinch of salt | - pinch | salt | size - | prep  | 1 Pinch | salt | size - | prep  | **library** | one pinch |
| -- Juice of 1 lemon (about 2 tablespoons), or to taste | - - | juice of 1 lemon | size - | prep about 2 tablespoons; or to tast | 1 - | lemon | size - | prep Juice of | **library** | 1 lemon, 'juice of' |
| Handful green beans | - handful | green beans | size - | prep  | 1 Handful | green beans | size - | prep  | **library** | one handful |
| 6 tablespoons plus 2 teaspoons extra-virgin olive oil | 6 tbsp | plus 2 teaspoons extra-virgin olive oil | size - | prep  | - - | extra-virgin olive oil | size - | prep  | **neither** | 'plus' line |
| 2 rashers of smoked streaky higher-welfare bacon | 2 each | rashers of smoked streaky higher-welfare bacon | size - | pre | 2 rashers | smoked streaky higher-welfare bacon | size - | prep  | **library** | unit rashers, name bacon |
| Zest 1/2 Lemon | - - | zest 1/2 lemon | size - | prep  | 1/2 - | Lemon | size - | prep Zest | **library** | 1/2 lemon, zest |
| 400g can chickpeas drained and left to dry a little | 400 g | can chickpeas drained and left to dry a little | size - | prep | 1 can | chickpeas drained and left to dry a little | size - | prep  | **roli** | 400 g; the library's first amount is 1 can |
| 1/2 cup plus 4 teaspoons shredded sharp cheddar cheese | 0.5 cup | plus 4 teaspoons shredded sharp cheddar cheese | size - | pr | - - | sharp cheddar cheese | size - | prep shredded | **neither** | 'plus' line |
| finely grated zest of 1 lemon (about 2 tsp) | - - | finely grated zest of 1 lemon | size - | prep about 2 tsp | 1 - | lemon | size - | prep finely grated zest of | **library** | 1 lemon, zest |
| 1/4 cup plus 2 Tbs. freshly grated Parmigiano-Reggiano cheese | 0.25 cup | plus 2 tbs. freshly grated parmigiano-reggiano cheese | siz | - - | Parmigiano-Reggiano cheese | size - | prep freshly grated | **neither** | 'plus' line |
| 290g can pitted prunes in natural juice, drained | 290 g | can pitted prunes in natural juice | size - | prep drained | 1 can | pitted prunes in natural juice | size - | prep drained | **roli** | 290 g; the library's first amount is 1 can |
| 2/3 cup + 1 tablespoon olive oil | 0.6666666666666666666666666667 cup | + 1 tablespoon olive oil | size - | - - | olive oil | size - | prep  | **neither** | '+' line |
| Juice of 1 Lime, about 2 tablespoons | - - | juice of 1 lime | size - | prep about 2 tablespoons | 1 - | Lime | size - | prep Juice of | **library** | 1 lime, juice |
| 1 sheet vegan puff pastry | 1 each | sheet vegan puff pastry | size - | prep  | 1 sheet | vegan puff pastry | size - | prep  | **library** | unit sheet |

### 50 most troubled

| line | Roli | library | verdict | why |
|---|---|---|---|---|
| (2) Tbl. olive oil | - tbsp | olive oil | size - | prep 2 | 2 - | Tbl. olive oil | size - | prep  | **neither** | '(2) Tbl.': the library reads 2 with no unit, Roli the unit with no quantity |
| (2) Stemple Creek Beef Bavette Steaks | - - | stemple creek beef bavette steaks | size - | prep 2 | 2 - | Stemple Creek Beef Bavette Steaks | size - | prep  | **library** | bracketed count read as 2 |
| 1 recipe caramel sauce (, or one 16oz jar caramel topping) | - - | caramel sauce | size - | prep , or one 16oz jar caramel topping | 1 recipe | caramel sauce | size - | prep  | **library** | '1 recipe' literal |
| 1 recipe carne asada | - - | carne asada | size - | prep  | 1 recipe | carne asada | size - | prep  | **library** | '1 recipe' literal |
| BBQ Sauce (see note 2) | - - | bbq sauce | size - | prep see note 2 | - - | BBQ Sauce | size - | prep  | **both** | no quantity on the line |
| Coleslaw (see note 3) | - - | coleslaw | size - | prep see note 3 | - - | Coleslaw | size - | prep  | **both** | no quantity on the line |
| Cooked bacon slices (2 slices per burger) | - - | cooked bacon slices | size - | prep 2 slices per burger | 2 slices | bacon slices | size - | prep Cooked | **library** | 2 slices per burger read from the note |
| Generous 8 ounces slightly stale open-crumbed, chewy, peasant-style bread (not s | - - | generous 8 ounces slightly stale open-crumbed | size - | prep no | 8 ounce | slightly stale open-crumbed, chewy, peasant-style bread | si | **library** | 8 ounces; Roli reads no quantity after 'Generous' |
| One-half of a 3 ½-ounce package achiote paste (available to Mexican groceries; r | - - | one-half of a 3 ½-ounce package achiote paste | size - | prep av | 1/2 packages | achiote paste | size - | prep  | **library** | 1/2 package |
| Scant ½ cup grated Cheddar or Mexican cheese blend (scant 2 ounces) | - - | scant ½ cup grated cheddar or mexican cheese blend | size - | pr | 1 Scant | Cheddar cheese blend | Mexican cheese blend | size - | prep  | **neither** | 'Scant 1/2 cup': the library reads unit 'Scant', Roli nothing |
| Spicy salsa (there are 2 recipes of spicy salsa in my blog) | - - | spicy salsa | size - | prep there are 2 recipes of spicy salsa i | - - | Spicy salsa | size - | prep  | **both** | no quantity on the line |
| Turkish bread (, about 60cm / 2 feet long (or 4 rolls / buns of choice)) | - - | turkish bread | size - | prep , about 60cm / 2 feet long (or 4 r | - - | Turkish bread | size - | prep 2 feet long | **both** | no quantity on the line |
| Vegetable or peanut oil, for frying (about 6 cups, enough for 3–4 inches in the  | - - | vegetable or peanut oil | size - | prep about 6 cups, enough for | 6 cup | Vegetable oil | peanut oil | size - | prep  | **library** | about 6 cups |
| optional: 1/2 cup light cream or half and half | - - | optional: 1/2 cup light cream or half and half | size - | prep  | 1/2 cup | light cream | half and half | size - | prep  | **library** | 'optional:' prefix |
| optional: 1/4 cup cheddar cheese | - - | optional: 1/4 cup cheddar cheese | size - | prep  | 1/4 cup | cheddar cheese | size - | prep  | **library** | 'optional:' prefix |
| vegan egg wash: 2 tsp plant milk, 1 tsp olive oil + 1 tsp maple syrup or sugar | - - | vegan egg wash: 2 tsp plant milk | size - | prep 1 tsp olive oil | - - | vegan egg wash | size - | prep  | **neither** | a compound line of three ingredients |
| vegan scrambled eggs for 4 (I used JUST egg, but my favourite is my Tofu Scrambl | - - | vegan scrambled eggs for 4 | size - | prep I used JUST egg, but  | - - | eggs | size - | prep vegan scrambled | **neither** | 'vegan scrambled eggs for 4': the library's name 'eggs' is wrong, Roli's keeps 'for 4' |
| 1 chipotle chile in adobo, plus 1 Tbsp. adobo sauce | 1 each | chipotle chile in adobo | size - | prep plus 1 Tbsp. adobo sa | 1 - | chipotle chile in adobo | size - | prep  | **both** | 1 chile; the 'plus 1 Tbsp. adobo sauce' is lost by both |
| 1 cup whole milk | 1 cup | whole milk | size - | prep  | 1 cup | whole milk | size - | prep  | **both** | 1 cup whole milk (the trouble was the USDA match, not the parse) |
| 2 Rodelle Vanilla Beans, split and scraped | 2 each | rodelle vanilla beans | size - | prep split and scraped | 2 - | Rodelle Vanilla Beans | size - | prep split and scraped | **both** | 2 beans |
| 2 Tbsp. plus 3 cups (391 g) bread flour, plus more for surface | 2 tbsp | plus 3 cups bread flour | size - | prep 391 g; plus more for  | - - | bread flour | size - | prep  | **neither** | 'plus' line |
| 2 chipotles in adobo plus 2 tablespoons of the adobo sauce (well mashed together | 2 each | chipotles in adobo plus 2 tablespoons of the adobo sauce | si | 2 - | chipotles | size - | prep  | **library** | name 'chipotles'; Roli's name carries 'plus 2 tablespoons of the adobo sauce' |
| 8 slices country bread | 8 slice | country bread | size - | prep  | 8 slices | country bread | size - | prep  | **both** | 8 slices |
| 1 4 1/2-foot hog casing, soaked in water 30 minutes and then flushed with water | 1 each | 4 1/2-foot hog casing | size - | prep soaked in water 30 minu | 1 - | hog casing | size - | prep soaked in water 30 minutes and then f | **library** | name 'hog casing'; Roli names it '4 1/2-foot hog casing' |
| 1 American Wagyu Black® bavette | 1 each | american wagyu black® bavette | size - | prep  | 1 - | American Wagyu Black® bavette | size - | prep  | **both** | 1 bavette |
| 1 Bunch Kale, stemmed and chopped into pieces | 1 bunch | kale | size - | prep stemmed and chopped into pieces | 1 Bunch | Kale | size - | prep stemmed and chopped into pieces | **both** | 1 bunch |
| 1 Teaspoon Liquid Smoke (optional) | 1 tsp | liquid smoke | size - | prep optional | 1 Teaspoon | Liquid Smoke | size - | prep  | **both** | 1 tsp |
| 1 Vanilla Bean | 1 each | vanilla bean | size - | prep  | 1 - | Vanilla Bean | size - | prep  | **both** | 1 bean |
| 1 box panko bread crumbs | 1 each | box panko bread crumbs | size - | prep  | 1 box | panko bread crumbs | size - | prep  | **library** | unit box |
| 1 can baked beans (in England they use Heinz, so it's what I used) | 1 can | baked beans | size - | prep in England they use Heinz, so it's | 1 can | baked beans | size - | prep  | **both** | 1 can |
| 1 can chilli beans | 1 can | chilli beans | size - | prep  | 1 can | chilli beans | size - | prep  | **both** | 1 can |
| 1 can of Heinz Baked Beans in Tomato Sauce | 1 can | heinz baked beans in tomato sauce | size - | prep  | 1 can | Heinz Baked Beans in Tomato Sauce | size - | prep  | **both** | 1 can |
| 1 can whole kernel corn | 1 can | whole kernel corn | size - | prep  | 1 can | whole kernel corn | size - | prep  | **both** | 1 can |
| 1 chocolate cake (, baked in a 9x13'' pan) | 1 each | chocolate cake | size - | prep , baked in a 9x13'' pan | 1 - | chocolate cake | size - | prep (, baked in a 9x 13'' pan) | **both** | 1 cake |
| 1 cube vegetable stock | 1 each | cube vegetable stock | size - | prep  | 1 cube | vegetable stock | size - | prep  | **library** | unit cube |
| 1 cup Chocolate Chips | 1 cup | chocolate chips | size - | prep  | 1 cup | Chocolate Chips | size - | prep  | **both** | 1 cup |
| 1 cup Meathead's Kansas City-Style BBQ sauce | 1 cup | meathead's kansas city-style bbq sauce | size - | prep  | 1 cup | Meathead's Kansas City-Style BBQ sauce | size - | prep  | **both** | 1 cup |
| 1 cup apple juice ( or chicken broth works) | 1 cup | apple juice | size - | prep or chicken broth works | 1 cup | apple juice | chicken broth works | size - | prep  | **both** | 1 cup |
| 1 cup barbecue sauce (optional) | 1 cup | barbecue sauce | size - | prep optional | 1 cup | barbecue sauce | size - | prep  | **both** | 1 cup |
| 1 cup grated cheese | 1 cup | grated cheese | size - | prep  | 1 cup | cheese | size - | prep grated | **both** | 1 cup |
| 1 cup old-fashioned rolled oats | 1 cup | old-fashioned rolled oats | size - | prep  | 1 cup | old-fashioned rolled oats | size - | prep  | **both** | 1 cup |
| 1 disk sweet tart crust, chilled | 1 each | disk sweet tart crust | size - | prep chilled | 1 - | disk sweet tart crust | size - | prep chilled | **both** | 1 disk |
| 1 dried avocado leaf | 1 leaf | dried avocado | size - | prep  | 1 - | dried avocado leaf | size - | prep  | **both** | 1 leaf |
| 1 heaping tablespoon malt powder (optional) | 1 each | heaping tablespoon malt powder | size - | prep optional | 1 heaping tablespoon | malt powder | size - | prep  | **library** | 'heaping tablespoon' read as the unit; Roli reads 1 each |
| 1 large ciabatta halved | 1 large | ciabatta halved | size large | prep  | 1 - | ciabatta | size large | prep halved | **library** | name ciabatta, size large, preparation halved |
| 1 large shallot, finely diced | 1 large | shallot | size large | prep finely diced | 1 - | shallot | size large | prep finely diced | **both** | 1 large shallot |
| 1 loaf ciabatta bread, sliced | 1 each | loaf ciabatta bread | size - | prep sliced | 1 loaf | ciabatta bread | size - | prep sliced | **library** | unit loaf |
| 1 long French baguette (sliced into 4 equal size pieces) | 1 each | long french baguette | size - | prep sliced into 4 equal size | 1 - | long French baguette | size - | prep (sliced into 4 equal size p | **both** | 1 baguette |
| 1 package instant yeast (not rapid rise) | 1 each | package instant yeast | size - | prep not rapid rise | 1 package | instant yeast | size - | prep  | **library** | unit package |
| 1 package pear or cherry tomatoes | 1 each | package pear or cherry tomatoes | size - | prep  | 1 package | pear tomatoes | cherry tomatoes | size - | prep  | **library** | unit package |

## 5. The 15 named lines

Roli: quantity [range] / unit / name / size / preparation / flags. Library: quantity[/max] / unit / name / size / preparation / comment / purpose / all amounts when more than one / confidence amount/name.

| line | Roli | ingredient-parser-nlp |
|---|---|---|
| 17-ounce log goat cheese, cut into 12 slices | 17 / oz / goat cheese / size - / prep cut into 12 slices | 17 / ounce / log goat cheese / size - / prep cut into 12 slices / conf 0.99/0.99 |
| 5-ounce package soft fresh goat cheese, coarsely crumbled | 5 / oz / soft fresh goat cheese / size - / prep coarsely crumbled | 1 / package / soft fresh goat cheese / size - / prep coarsely crumbled / amounts [1 package; 5 ounces] / conf 0.99/0.99 |
| 2 Eggland's Best eggs (large) | 2 / each / eggland's best eggs / size large / prep large / conversion_pending_usda_portion | 2 / - / Eggland's Best eggs / size (large) / prep - / conf 0.99/0.99 |
| 2 cold large eggs, well beaten | 2 / each / cold large eggs / size - / prep well beaten / conversion_pending_usda_portion | 2 / - / eggs / size cold large / prep well beaten / conf 0.99/0.88 |
| 4 (6-ounce) fillets | 4 / fillet / 4 (6-ounce) fillets / size - / prep 6-ounce / note_follows_count;note_follows_measure;conversion_pending_usda_portion | 4 / - / fillets / size - / prep - / amounts [4; 6 ounces] / conf 0.99/0.86 |
| 3 large potatoes (560 grams) | 3 / large / potatoes / size large / prep 560 grams / conversion_pending_usda_portion | 3 / - / potatoes / size large / prep - / amounts [3; 560 grams] / conf 0.99/0.99 |
| squids or 8 large sea prawns | - / - / squids or 8 large sea prawns / size - / prep - | 8 / - / squids | sea prawns / size large / prep - / conf 0.70/0.68 |
| 1/3 cup pecorino romano (33g) | 0.3333333333333333333333333333 / cup / pecorino romano / size - / prep 33g / conversion_pending_usda_portion | 1/3 / cup / pecorino romano / size - / prep - / amounts [⅓ cups; 33 g] / conf 0.99/0.99 |
| 200ml rapeseed oil | 200 / ml / rapeseed oil / size - / prep - / conversion_pending_usda_portion | 200 / milliliter / rapeseed oil / size - / prep - / conf 0.99/0.99 |
| 4 strips lemon peel | 4 / each / strips lemon peel / size - / prep - / conversion_pending_usda_portion | 4 / strips / lemon peel / size - / prep - / conf 0.99/0.99 |
| 1 cup olive oil | 1 / cup / olive oil / size - / prep - / conversion_pending_usda_portion | 1 / cup / olive oil / size - / prep - / conf 0.99/0.99 |
| Semolina flour, for dusting | - / - / semolina flour / size - / prep for dusting | - / - / Semolina flour / size - / prep - / purpose for dusting / conf -/0.98 |
| 2 shallots, sliced | 2 / each / shallots / size - / prep sliced / conversion_pending_usda_portion | 2 / - / shallots / size - / prep sliced / conf 0.99/0.99 |
| 1 (28-ounce) can fire roasted diced tomatoes | 1 / can / fire roasted diced tomatoes / size - / prep 28-ounce / note_follows_count;note_follows_measure;conversion_pending_usda_portion | 1 / can / fire roasted diced tomatoes / size - / prep - / amounts [1 can; 28 ounces] / conf 0.99/0.99 |
| Extra-virgin olive oil, as needed | - / - / extra-virgin olive oil / size - / prep as needed / vague_quantity | - / - / Extra-virgin olive oil / size - / prep - / comment as needed / conf -/0.99 |

Readings: the library separates the weight of a labelled item into a second amount ("1 package" + "5 ounces", "4" + "6 ounces", "3" + "560 grams", "1/3 cups" + "33 g", "1 can" + "28 ounces"), which is what Roli's
converter does with its notes; both read "17-ounce log" as 17 oz; the library finds the 8 in "squids or 8 large sea prawns" (Roli reads nothing) at confidence 0.71; "4 strips lemon peel" gets the unit "strips" from
the library and `each` with "strips" in the name from Roli; "Semolina flour, for dusting" and "Extra-virgin olive oil, as needed" have no amount in either, the library files the tail as purpose or comment, Roli as a
preparation note with its `vague_quantity` flag; "2 cold large eggs" gets size "cold large" from the library (cold is not a size) and the name "eggs"; Roli keeps "cold large eggs" as the name.

## 6. Confidence on the lines the library got wrong

The library gives a confidence per field; I take the lower of the amount and the name confidence. On the 150 judged lines the library was wrong (verdict roli or neither) on 29 and right on 121.

| threshold | wrong lines caught (of 29) | right lines discarded (of 121) | of all 2783 lines under it |
|---|---|---|---|
| 0.80 | 6 | 9 | 171 |
| 0.90 | 8 | 17 | 276 |
| 0.95 | 11 | 27 | 385 |
| 0.99 | 16 | 55 | 842 |

A 0.9 threshold catches 8 of the 29 wrong lines and discards 17 of 121 right ones; the "plus" lines and the container-before-weight lines are wrong at 0.99 or above,
because the model is sure of what it tagged and the error is in what it did not do (sum two amounts, prefer the weight). The low-confidence wrong lines are the odd ones: the checkbox glyph (0.51), "A little water"
(0.45 on the name), "1 ea Romaine" (0.67), "400g can chickpeas drained and left to dry a little" (0.65). Confidence is a weak guard here: it flags unusual text, not the systematic misses.
Wrong lines by confidence: 0.45 '2 tablespoons plus 2 tablespoons avocado or olive oil' (neither); 0.51 '▢ ¼ cup fresh cilantro' (roli); 0.52 'vegan scrambled eggs for 4 (I used JUST egg, but my favourit' (neither); 0.65 '400g can chickpeas drained and left to dry a little' (roli); 0.67 '1 ea Romaine Lettuce, head, cleaned, cored and chiffonaded' (roli); 0.74 '2 Tbl. fresh chopped Italian parsley' (roli); 0.84 '1 small Granny Smith apple, cored and sliced into 8 (1/2-inc' (roli); 0.86 '(2) Tbl. olive oil' (neither); 0.94 '4 Tbl. prepared garlic butter' (roli); 0.94 'vegan egg wash: 2 tsp plant milk, 1 tsp olive oil + 1 tsp ma' (neither); 0.94 '100g bag mixed rocket , spinach and watercress salad' (roli); 0.95 'Scant ½ cup grated Cheddar or Mexican cheese blend (scant 2 ' (neither); 0.97 '1/2 cup plus 4 teaspoons shredded sharp cheddar cheese' (neither); 0.97 '1/2 tbsp+ lime juice' (roli); 0.98 '1 handfull arugula' (roli); 0.98 '2 tablespoons sprigs fresh parsley, chopped' (roli); 0.99 '4 cups (1-inch) chunks of rustic sourdough bread' (roli); 0.99 '14 ounce can sweetened condensed milk' (roli); 0.99 '1/4 cup plus 2 Tbs. freshly grated Parmigiano-Reggiano chees' (neither); 0.99 '2 Tbsp. plus 3 cups (391 g) bread flour, plus more for surfa' (neither); 0.99 '2 Tbsp. plus 3 cups (391 g) bread flour, plus more for surfa' (neither); 1.00 '9 ounce box of Jovial Gluten Free Tagliatelle pasta' (roli); 1.00 '290g can pitted prunes in natural juice, drained' (roli); 1.00 '200g pack shortbread biscuits' (roli); 1.00 '1/3 cup plus 1 Tbs. mild olive oil' (neither); 1.00 '2/3 cup + 1 tablespoon olive oil' (neither); 1.00 '½ cup plus 2 tablespoons extra-virgin olive oil' (neither); 1.00 '6 tablespoons plus 2 teaspoons extra-virgin olive oil' (neither); 1.00 '3 - 1/2 cup heavy cream' (neither).

## 7. Speed and what the library needs

| | Roli's parser | ingredient-parser-nlp 2.9.2 |
|---|---|---|
| per line, warm | 0.048 ms | 1.52 ms |
| start-up | none | import 0.47 s, first call 0.27 s (model and embeddings load) |
| 2783 lines | 0.13 s | 4.23 s |
| installed size | part of Roli | wheel 4.3 MB (model 0.6 MB, embeddings 3.4 MB) plus numpy, nltk, pint and their 10 dependencies; plus NLTK's tagger data (6.9 MB) fetched from NLTK's servers on first import unless pre-installed |
| Python | 3.13 | 3.11 or newer |
| network | none | none once the NLTK data is present; otherwise one download at import |

Thirty times slower per line, but a dish's 100-200 lines still parse in well under a second; the cost that matters is the start-up and the dependency surface, not the per-line time.

## 8. Recommendation

**Use the library only for lines Roli's parser cannot read, and not yet.** Reasons:

- On the lines where the two disagree the library is right more often (57 against 15 of 100), and its wins are exactly the shapes that block Roli's recipes today: "pinch of", "handful", "juice of 1 lemon",
  "optional: ...", "(1) tsp.", "1 and 1/2 cups", "1 heaping tablespoon", container units with a clean name. Those are fixable one by one in Roli's parser too, and they are the kind of fix the parser has had at every
  checkpoint; the library would fix them in one step but bring its own misses.
- Where Roli is right the cases matter for weighing: it takes the printed weight over the container ("400g can" is 400 g). The library has the weight too, as a second amount, so an adapter that prefers a mass or
  volume amount from the list would close that gap; but "plus" lines fail in both and need a rule either way.
- The 50 most troubled lines show the limit of any parser swap: 27 of 50 were read correctly by both and failed at the weighing step (no USDA portion for a can, a cup of that food, a bunch, a package). A better parser
  moves perhaps 18 of those 50 lines forward; the rest need portion data, not parsing.
- Cost of adoption: three dependencies (numpy, nltk, pint) plus NLTK data that the package downloads at import unless it is shipped, a 0.7 s start-up, and a model whose errors are not caught by its confidence.
  Roli's rule "a model never writes a nutrient value or a weight" is not touched (the library writes neither), but a trained tagger deciding quantities and units would be a new kind of component in the number path,
  and the spec would need to say so.

**What would have to change in Roli to adopt it, even as a fallback.** Roli's weighing step (`recipes/convert.py`, `recipes/adapt.py`, the portion rules) reads from `ParsedIngredient`: `quantity` (Decimal),
`quantity_low` / `quantity_high` for a range, `unit` in Roli's normalised spelling with `unit_kind` (mass, volume, count, none), `name` (lower-cased food words, the USDA query starts from it), `preparation_words` (the
notes the embedded-weight step reads, such as "(8-oz)" or "(560 grams)", and the words the preparation hint and the line tags read), `preparation_hint`, `optional`, and `flags` (`vague_quantity`,
`note_follows_count`, `conversion_pending_usda_portion`). An adapter would: turn the library's fraction strings into Decimals and its `quantity`/`quantity_max` into the range fields; map pint unit names and free-text
units ("large cloves", "heaping tablespoon") onto Roli's unit table and kinds; choose among several amounts (prefer a mass, then a volume, then the count, keeping the others as notes so "4 (6-ounce) fillets" stays
4 fillets of 6 oz each by Roli's 12.16.1 reading); join the name alternatives back to "X or Y" or pick the first; move `size` into the preparation words where Roli's portion chooser looks for "large"; carry
`comment` and `purpose` as notes so the "for dusting" and "as needed" lines keep their `vague_quantity` reading; and decide what to do with "1 recipe X" (Roli's sub-recipe reference) and the frying-oil lines
Roli leaves unquantified on purpose. As a fallback it would run only when Roli's parse has no quantity on a line that carries a number or an amount word, and the run would record which parser answered.

**Not done:** Roli's parser was not changed; the library is not installed anywhere in Roli; the venv was deleted.
