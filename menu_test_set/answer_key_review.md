# Answer key – items to double-check

`answer_key.csv` has 1002 items across 25 photos, typed as printed (930 until 2026-10-28; see the change log at the end). 948 are marked `high` confidence. The 54 items below are `medium` or `low` – the only ones worth a look.

Legend: **medium** = fairly sure, but the print was small, skewed, glared or faint. **low** = the name is readable but the price (or description) is cut off or hidden, so it is left blank on purpose.

Rules applied after the first review round:

- A price that is partly hidden or cut off is left **blank** (never guessed) and the row is marked `low`.
- A line whose *name* is cut off mid-word is **left out of the key** and listed in `answer_key_photo_notes.csv` (column `cut_off_lines_left_out`). When scoring, a model that lists one of those is neither right nor wrong – ignore it.
- Smaller-type lines without a price under an item are options or ingredients of that item and go into its `description`.
- Three extra columns: `tags` (dietary marks exactly as printed: GF, VE, V, N, VEGAN, VEGETARIAN, VEG/NON-VEG, PLANT BASED), `portion` (counts and sizes as printed) and `has_choice` (yes when the dish is made with a choice of main ingredient, filling or preparation), `belongs_to` (for add-ons: the dish or section the extra is attached to). All four are copied from the photo, never inferred.

## Flagged items by photo

### menu_10_alexs_kitchen_indochinese_dense.jpg (5 flagged)

| # | section | item | price | conf. | why |
|---|---|---|---|---|---|
| 94 | FISH | Diced Fish (Spicy) | — | low | price hidden by glare |
| 95 | FISH | Mandarin Fish | — | low | price hidden by glare |
| 96 | FISH | Sichuan Fish | — | low | price hidden by glare |
| 97 | FISH | Apollo Fish | — | low | price hidden by glare |
| 98 | FISH | Pepper Fish | — | low | price hidden by glare |

### menu_13_hard_obstructed_cafe_mondegar.jpg (12 flagged)

| # | section | item | price | conf. | why |
|---|---|---|---|---|---|
| 8 | LITE BITES | Wafer / Masala Papad / Boiled Eggs | — | medium | small blurred text; prices cut off at right edge |
| 9 | LITE BITES | Garlic Toast / Green Salad | — | medium | prices cut off |
| 10 | LITE BITES | French Fries / Hash Brown (6 pcs) | — | medium | prices cut off |
| 11 | LITE BITES | Cheese Cherry Pineapple Stick | — | medium | prices cut off |
| 12 | LITE BITES | Onion Rings / Cheese Balls (Schezwan) | — | medium | prices cut off |
| 13 | LITE BITES | Chilly Cheese Toast | — | medium | prices cut off |
| 14 | LITE BITES | Cutlet & Fries (Veg / Chicken) | — | medium | prices cut off |
| 15 | LITE BITES | Koliwada (Paneer / Prawns) | — | medium | prices cut off |
| 16 | LITE BITES | Mondy's Steak Boti | — | medium | prices cut off |
| 17 | LITE BITES | Masala Omelette with French Fries | — | medium | prices cut off |
| 18 | LITE BITES | Kheema Pao / Kheema Gotala | — | medium | prices cut off |
| 19 | LITE BITES | Extra Sauce | — | medium | list of sauces cut off at the right edge; prices cut off |

### menu_15_hard_glare_peg_house_chalkboard.jpg (4 flagged)

| # | section | item | price | conf. | why |
|---|---|---|---|---|---|
| 6 | Burgers - Humboldt Grass fed Beef | Ortega Burger | 12.50 | medium | second line of the description read through the glare band |
| 7 | Burgers - Humboldt Grass fed Beef | Aloha Burger | 15.50 | medium | description under heavy glare |
| 13 | grilled Chicken sandwiches | Aloha | 17 | low | description unreadable under glare; price legible |
| 14 | grilled Chicken sandwiches | Brie | 17 | medium | description faint under glare |

### menu_16_mi_pueblo_us_printed_dense.jpg (2 flagged)

| # | section | item | price | conf. | why |
|---|---|---|---|---|---|
| 12 | ENTREES | POLLO FUNDIDO | — | low | price cut off at right edge; glare on 'guacamole' |
| 14 | ENTREES | TACOS AL CARBON | — | low | price cut off at right edge; description also cut off mid-sentence |

### menu_17_duck_house_takeout_printed_wall.jpg (29 flagged)

| # | section | item | price | conf. | why |
|---|---|---|---|---|---|
| 15 | SOUP | Hot & Sour Soup | (S) 1.95 (L) 7.95 | medium | small price reads 1.95 but may be 2.95; tiny print |
| 16 | SOUP | Egg Flower Soup | (S) 1.95 (L) 7.95 | medium | small price reads 1.95 but may be 2.95; tiny print |
| 68 | BEEF & LAMB | Sliced Beef in Hot & Spicy Gravy | 15.95 | medium | price column is skewed half a line lower than the names (wrinkled paper); prices matched by order |
| 69 | BEEF & LAMB | Soft Tofu Beef | 14.95 | medium | price column is skewed half a line lower than the names (wrinkled paper); prices matched by order |
| 70 | BEEF & LAMB | Stir-fried Beef w/ Cilantro | 14.95 | medium | price column is skewed half a line lower than the names (wrinkled paper); prices matched by order |
| 71 | BEEF & LAMB | Stir-fried Beef w/ Green Onion | 14.95 | medium | price column is skewed half a line lower than the names (wrinkled paper); prices matched by order |
| 72 | BEEF & LAMB | Mongolian Beef | 14.95 | medium | price column is skewed half a line lower than the names (wrinkled paper); prices matched by order |
| 73 | BEEF & LAMB | Cumin Beef | 14.95 | medium | price column is skewed half a line lower than the names (wrinkled paper); prices matched by order |
| 74 | BEEF & LAMB | Beef w/ Broccoli | 13.95 | medium | price column is skewed half a line lower than the names (wrinkled paper); prices matched by order |
| 75 | BEEF & LAMB | Beef w/ Pickled Chili | 13.95 | medium | price column is skewed half a line lower than the names (wrinkled paper); prices matched by order |
| 76 | BEEF & LAMB | Beef w/ Mixed Mushroom | 15.95 | medium | price column is skewed half a line lower than the names (wrinkled paper); prices matched by order |
| 77 | BEEF & LAMB | Beef w/ Black Pepper Sauce | 14.95 | medium | price column is skewed half a line lower than the names (wrinkled paper); prices matched by order |
| 78 | BEEF & LAMB | Beef w/ Green Bean | 14.95 | medium | price column is skewed half a line lower than the names (wrinkled paper); prices matched by order |
| 79 | BEEF & LAMB | Beef w/ Snow Peas | 15.95 | medium | price column is skewed half a line lower than the names (wrinkled paper); prices matched by order |
| 80 | BEEF & LAMB | Stir-fried Lamb w/ Cilantro | 15.95 | medium | price column is skewed half a line lower than the names (wrinkled paper); prices matched by order |
| 81 | BEEF & LAMB | Stir-fried Lamb w/ Green Onion | 15.95 | medium | price column is skewed half a line lower than the names (wrinkled paper); prices matched by order |
| 82 | BEEF & LAMB | Cumin Lamb | 15.95 | medium | price column is skewed half a line lower than the names (wrinkled paper); prices matched by order |
| 83 | BEEF & LAMB | Lamb w/ Pickled Chili | 15.95 | medium | price column is skewed half a line lower than the names (wrinkled paper); prices matched by order |
| 90 | PORK | Pork w/ Bamboo Shoots | — | low | price cut off or blurred at the right edge of the photo |
| 92 | PORK | Shredded Pork w/ Hot Garlic Sauce | — | low | price cut off or blurred at the right edge of the photo |
| 93 | PORK | Smoked Pork Belly w/ Leek | — | low | price cut off or blurred at the right edge of the photo |
| 94 | PORK | Smoked Pork Belly w/ Wood Ear Fungus and Leek | — | low | price cut off or blurred at the right edge of the photo |
| 95 | PORK | Pork Belly w/ Preserved Vegetables | — | low | price cut off or blurred at the right edge of the photo |
| 96 | PORK | Pan Fried Intestines | — | low | price cut off or blurred at the right edge of the photo |
| 97 | PORK | Intestines in Hot & Spicy Gravy | — | low | price cut off or blurred at the right edge of the photo |
| 98 | PORK | Intestines w/ Preserved Vegetable | — | low | price cut off or blurred at the right edge of the photo |
| 99 | PORK | Szechuan Style Pig Feet | — | low | price cut off or blurred at the right edge of the photo |
| 100 | PORK | House Special Garlic Pork Spareribs | — | low | price cut off or blurred at the right edge of the photo |
| 101 | PORK | Sweet & Sour Pork Spareribs | — | low | price cut off or blurred at the right edge of the photo |

### menu_24_hard_partial_mr_bs_menu_board.jpg (2 flagged)

| # | section | item | price | conf. | why |
|---|---|---|---|---|---|
| 5 | HOT SANDWICHES | Beef, Bac. & Cheddar | — | low | last digit cut off at right edge; price not usable |
| 7 | HOT SANDWICHES | French Dip w/Cheddar | — | low | last digit cut off at right edge; price not usable |

## Lines left out because the name is cut off

| file | left out |
|---|---|
| menu_13_hard_obstructed_cafe_mondegar.jpg | Pollo Alla Pepe / Fr...; Achari Gobi Tikka / Baby Corn Ti...; Paneer Tikka / Malai / Achari / S...; Chicken Tikka / Malai / Reshm...; Chicken Sheek / Achari / Tang...; Fish Tikka / Achari / Kalami...; King Prawns Tikka / Harya...; Tandoor Naan / Butter N...; Butter Naan / Garlic N... |
| menu_16_mi_pueblo_us_printed_dense.jpg | ...HILE COLORADO (Chile Colorado); ...ROZ CON POLLO (Arroz con Pollo) |
| menu_17_duck_house_takeout_printed_wall.jpg | ...occoli w/ Garlic Sauce; ...uliflower w/ Black Bean Sauce; ...r-fried Shredded Potato; ...ceed A Choy w/ Dried Fish & Black Bean Sauce; ...oy (A Choy); ...Pea with Garlic Sauce; ...Pea Leaf with Garlic Sauce |

## Photo-level notes (what makes each photo tricky)

Also in `answer_key_photo_notes.csv`. A model that says "part of this menu is cut off" on photos 13, 16, 17 or 24 is doing the right thing.

| file | items | high / med / low | note |
|---|---|---|---|
| menu_01_own_zuni_cafe_sf.JPG | 71 | 71 / 0 / 0 | section|category|name|description|price|confidence|notes |
| menu_02_own_IMG_5181.jpg | 22 | 22 / 0 / 0 | same menu as photo 01, but the photo is cut off just below the drinks headers (APERITIF / JUICE & SODA / WATER / COFFEE, TEA & COCOA); drink items are not readable and must not be listed |
| menu_03_own_IMG_5185.jpg | 19 | 19 / 0 / 0 | Flour + Water (SF). Other menus are partly visible at the left and right edges (a wine list and a beverage page with BEER); only the main white menu counts. Names are printed in capitals. |
| menu_04_own_IMG_5186.jpg | 8 | 8 / 0 / 0 | SF Restaurant Week set menu (Flour + Water). Fixed price 90 per person, 45 optional wine pairing; dishes have no individual prices. Wine pairings are printed in italics under each course. |
| menu_05_ren_kitchen_uk_printed_long.jpg | 68 | 68 / 0 / 0 | Ren's Kitchen, Worthing. Four-column printed menu. Names printed in capitals. Prices in GBP without symbol. |
| menu_06_pizzaface_uk_printed_spread.jpg | 91 | 91 / 0 / 0 | Pizzaface, Worthing. Two-page spread. Names printed in capitals; V = vegetarian, vgn = vegan, (N) = contains nuts. Prices in GBP. |
| menu_07_cafe_rust_uk_printed_kraft.jpg | 46 | 46 / 0 / 0 | Cafe Rust, Brighton: drinks menu only, no food. Laminated brown card, prices without currency symbol. |
| menu_08_greyhound_pub_uk_printed.jpg | 38 | 38 / 0 / 0 | The Greyhound, Kew. Printed pub menu; names in capitals with price and diet tags (V, VG, GF) on the same line. Prices in GBP. |
| menu_09_the_shed_breakfast_uk_printed.jpg | 15 | 15 / 0 / 0 | The Shed: breakfast menu, 9AM - 11:30AM. Prices in GBP without symbol. |
| menu_10_alexs_kitchen_indochinese_dense.jpg | 157 | 152 / 0 / 5 | Alex's Kitchen (Indo-Chinese). Dense printed board; prices printed like 105-00 (INR). A further column is cut off at the LEFT edge of the photo (only its prices are visible) and must not be guessed. Glare hides the last five FISH prices. |
| menu_11_mothers_tacos_us_printed_dense.jpg | 31 | 31 / 0 / 0 | Mothers Tacos (US). Laminated printed sheet, dense; mild glare on lamination. Prices in dollars with no $ sign. |
| menu_12_hard_shadow_dyke_road_cafe.jpg | 46 | 46 / 0 / 0 | Dyke Road Cafe (UK) lunch menu. Laminated printed sheet with a hard diagonal shadow across it. Prices in pounds, no symbol. Dietary tags (GF, VE) printed in italics after names. |
| menu_13_hard_obstructed_cafe_mondegar.jpg | 24 | 12 / 12 / 0 | Cafe Mondegar (Mumbai) table-top menu, HARD: two salt/pepper shakers block the centre, most of the sheet is out of focus, the CONTINENTAL MENU column is printed sideways (rotated 90 degrees), and the right edge is cut off so Lite Bites / Tandoor prices are missing. Only the rows below are legible; the yellow wine list at top is blurred and should NOT be required. A good model should say the photo is partly obstructed. NINE lines whose text is cut off mid-word at the right or bottom edge (Pollo Alla Pepe, Achari Gobi Tikka, Paneer Tikka, Chicken Tikka, Chicken Sheek, Fish Tikka, King Prawns Tikka, two naan lines) are LEFT OUT of the key: do not count them as found or as invented. |
| menu_14_hard_dim_gaggan_tasting.jpg | 17 | 17 / 0 / 0 | Gaggan (Bangkok) tasting menu "Best of Gaggan". Small, dim, low-resolution photo (1248x1856) with a faint watermark image behind the text. One fixed price for the whole menu; courses have no individual prices. |
| menu_15_hard_glare_peg_house_chalkboard.jpg | 44 | 40 / 3 / 1 | The Peg House Grill (US). Handwritten chalk/marker board behind glass, HARD: strong glare and reflections (the photographer is reflected in the lower half), several descriptions under the glare are only partly legible. Prices handwritten with $ and superscript cents; written here as plain numbers. |
| menu_16_mi_pueblo_us_printed_dense.jpg | 14 | 12 / 0 / 2 | Mi Pueblo Traditional Mexican Food (US). Printed laminated page, photographed at an angle; LEFT edge of the left column and RIGHT edge of the right column are cut off, with a small glare spot on Pollo Fundido. All entrees "served with beans and rice". Prices printed as "/ 19". TWO entree lines at the left edge (Chile Colorado, Arroz con Pollo) have their first letters cut off and are LEFT OUT of the key: do not count them as found or as invented. |
| menu_17_duck_house_takeout_printed_wall.jpg | 183 | 154 / 18 / 11 | Duck House Chinese Restaurant (US) takeout menu, two printed sheets taped to a wall, VERY dense (about 230 items), bilingual Chinese/English, chili icons and GF marks. Photo cuts the RIGHT edge of the top sheet (Pork prices) and the LEFT edge of the bottom sheet (first letters of Tofu & Vegetable names). Right-hand info panel (hours, phone, address) is cut off and not required. Chinese names are not transcribed. SEVEN Tofu & Vegetable lines at the left edge of the bottom sheet (broccoli, cauliflower, shredded potato, two A Choy lines, two pea lines) have their first letters cut off and are LEFT OUT of the key: do not count them as found or as invented. |
| menu_18_little_saint_printed_stand_dim.jpg | 17 | 17 / 0 / 0 | Little Saint (Healdsburg, US) Summer 2022 printed menu on a wooden stand, indoor light, slight angle. Plant-based menu. Prices printed after a bullet; salads share one "7/13" price (two sizes) printed at the section header. |
| menu_19_dwarf_grill_printed_card.jpg | 41 | 41 / 0 / 0 | The Dwarf Grill (Hapeville, GA) 1940s reproduction menu card set into a table top, photographed at a steep angle; small print but sharp. Prices in cents ("20c"). Left panel is restaurant info only (name, address, motto, owners) and is not required. |
| menu_20_little_lous_handwritten_kraft.jpg | 7 | 7 / 0 / 0 | Little Lou's (Sonoma County, US). Handwritten marker on kraft paper taped to a shop window; reflections and a Cheetos bag behind the glass. Short menu. "Coming soon... milkshakes" and "Hours" notes are not items. |
| menu_21_the_block_handwritten_whiteboard.jpg | 8 | 8 / 0 / 0 | The Block (US) "Happy Hour Specials" handwritten whiteboard; a different printed menu is partly visible at the LEFT edge (prices $24, $14, $3.50 and a gyro photo) and a mirror image of the board shows at the right - neither should be transcribed. "Riblets" has a taped-over correction. |
| menu_22_woodford_store_chalkboard.jpg | 7 | 7 / 0 / 0 | Woodford General Store (US). Chalk A-frame board listing categories only - NO prices and no individual dishes. One bullet is empty (erased item). A good model should return these 7 items with empty prices and not invent any. |
| menu_23_en_boardwalk_bistro_chalkboard.jpg | 11 | 11 / 0 / 0 | Boardwalk Bistro (Australia) specials chalkboard, handwritten capitals, some glare. "Taste of the Sea" is one shared plate made of four parts; only the Fish of the Day items have prices. The watermelon salad is written without a heading. |
| menu_24_hard_partial_mr_bs_menu_board.jpg | 7 | 5 / 0 / 2 | Mr. B's (US) letter-board menu behind glass, HARD/PARTIAL: close-up of one section only ("HOT SANDWICHES" header half cut at the top), the RIGHT edge is cut so prices lose their last digit on two rows and a second size column (after "REG") is missing entirely; strong reflections. Prices are letter-board digits without a decimal point (6 74 = 6.74). A good model should flag the photo as partial. |
| menu_25_hot_dougs_specials_board_printed.jpg | 10 | 10 / 0 / 0 | Hot Doug's (Chicago) "Today's Specials" printed cards on a wall board, clean and well lit. Ten sausages in two columns; small "$9.00"-style prices under each card. Read left column top to bottom, then right column. |

## Change log

**2026-10-28** - 48 grouped topping lines on photo 06 and 3 grouped milk lines on photo 07 split into one item per topping or milk (rule: one orderable extra = one key item). 930 -> 973 items. Backup: `answer_key_backup_before_split_2026-10-28.csv`.

**2026-10-29** - Julius's rulings after the first Haiku batch. 973 -> 986 items. Backup: `answer_key_backup_before_23_05_edits_2026-10-29.csv`. Photos 02, 14 and 21 were reviewed and left unchanged.

- 05: three ULTIMATE BREAKFAST SANDWICH rows merged into one (price '1 filling 5.50 / 2 fillings 6.50 / 3 fillings 7.50', portion '1 / 2 / 3 fillings', has_choice yes)
- 05: 'Add chorizo 1.50' taken out of the SHAKSHUKA description and added as an add-on (belongs_to SHAKSHUKA)
- 05: 'Add smoked streaky bacon or poached eggs 1.25' taken out of the AVOCADO ON TOAST description and added as an add-on (belongs_to AVOCADO ON TOAST, has_choice yes)
- 05: EXTRAS line at 2.00 split into 7 add-ons (Smoked bacon, Sausage, Chorizo, Black pudding, Halloumi, Avocado, 2 Eggs), price '2.00 each', belongs_to 'section: BREAKFAST'
- 05: EXTRAS line at 1.50 split into 4 add-ons (Field mushroom, Tomato, Hash Brown, Beans), price '1.50 each', belongs_to 'section: BREAKFAST'
- 05: 'SAVOURY PASTRIES' renamed 'SAVOURY PASTRIES FROM'
- 23: 'Taste of the Sea' -> category other
- 23: added 'Ocean trout / tuna poke salad' (food, no price)
- 23: added 'Crumbed whiting' (food, no price)
- 23: added 'Battered oysters' (food, no price)
- 23: added 'Chilled Mooloolaba prawns' (food, no price)

**2026-10-29 (evening)** - Julius's rulings after the Haiku v2 invented list. 986 -> 988 items. Backup: `answer_key_backup_before_06_08_09_edits_2026-10-29.csv`.

- 08: 'add: Emmental Cheese 2.5 / Bacon 2.5 / Blue Cheese 2.5' split into three add-ons (Emmental Cheese, Bacon, Blue Cheese), price 2.5, belongs_to WAGYU BEEF BURGER
- 09: 'Bacon - 1 slice 3, 2 slices 3' -> name 'Bacon', price '1 slice 3 / 2 slices 3', portion '1 slice / 2 slices'
- 06: the nine dips (already one row each since the 2026-10-28 split) moved from section 'STARTERS, SALADS, SIDES, DIPS', category add-on, to section 'DIPS', category food; price '£2 each' unchanged

**2026-10-29 (late)** - Julius's ruling after the Qwen3.6 Parasail v1 invented list. 988 -> 995 items. Backup: `answer_key_backup_before_12_edits_2026-10-29.csv`.

- 12: 'Childs Half Sandwich' -> category other; its four fillings added as items (Ham sandwich; Cheese Sandwich; Cheese & Ham Sandwich; Cucumber & Hummus Sandwich (VE)), price 3.50, section CHILDREN'S
- 12: 'Half Jacket Potato' -> category other; its three toppings added as items (Mozarella Pesto; Cheese & Beans; Tuna Mayo), price 6.50, section CHILDREN'S

**2026-10-30** - Julius's rulings after the Qwen3.6 Parasail invented list. 995 -> 1000 items. Backup: `answer_key_backup_before_05_09_edits_2026-10-30.csv`.

- 05: 'FRESHLY BAKED JACKETS' -> category other (description 'Served with Home made slaw and salad', price 7.95); its four toppings added as food items at 7.95, section JACKET POTATOES: Ham and Cheese; Beans and Cheese; Barbecue Pulled Pork; Mediterranean roast vegetables (vegan) (tags VEGAN)
- 09: the single 'Bacon' add-on replaced by two add-on rows named 'Bacon', price 3, portion '1 slice' and '2 slices', belongs_to 'section: Breakfast'

**2026-10-30 (round-one review)** - Julius's decisions. 1000 -> 1002 items. Backup: `answer_key_backup_before_05_round2_edits_2026-10-30.csv`. The option splits on photos 05, 12 and 21 stay.

- 05: ULTIMATE BREAKFAST SANDWICH price '5.50 / 6.50 / 7.50', portion '1 filling / 2 fillings / 3 fillings' (the filling labels were in the price field and failed any model that wrote the three amounts)
- 05: '(add shot of spirulina £1)' and '(add scoop of vegan protein £1)' taken out of the FRESH JUICES and FRESH SMOOTHIES descriptions and added as add-on rows, price 1, belongs_to the drink
