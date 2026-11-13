# Menu reader test set (English only)

25 photos for testing how well each AI model reads restaurant menus.

## What is here

- `menu_01` to `menu_04`: your own phone photos (two shots of the Zuni Cafe lunch menu, an Italian-style menu in dim light, an SF Restaurant Week set menu in dim light).
- `menu_05` to `menu_25`: 21 openly licensed photos from Wikimedia Commons, chosen to cover:
  - clean printed menus (05, 06, 08, 09, 25)
  - dense or long menus (05, 10, 11, 16, 17)
  - low contrast or dim (07, 14, 18)
  - hard shots: shadow (12), partly covered (13), glare (15), cut off at the edge (24), angled (19)
  - handwritten and chalkboard menus (15, 20, 21, 22, 23)
- `manifest.csv`: one row per photo (25 rows) with type, difficulty, original title, author, license and source link.
- `telegram_1280/`: every photo shrunk to 1280 px on the long side, the size Telegram delivers to a bot.
  Run the accuracy test on these, not on the originals, so results match what real users get.
- `_not_used_foreign_language/`: 10 non-English photos from the first pass, kept in case you add other languages later.
- `_broken_placeholders/`: three tiny files that were never real photos; safe to delete.

## Licenses

All Commons photos are CC0, CC BY or CC BY-SA. If you publish the set, keep `manifest.csv` with it: CC BY and CC BY-SA
require naming the author and license.

## Answer key

- `answer_key.csv`: 930 items, one row per dish, drink or add-on, typed exactly as printed (same spelling and capitals).
  Columns: `file`, `item_no`, `section`, `category` (food / drink / add-on / other), `name`, `description`, `price`
  (as printed, no currency symbol; blank when nothing is printed), `tags` (dietary marks exactly as printed, e.g. GF,
  VE, V, N, VEGAN, VEGETARIAN, VEG / NON-VEG, PLANT BASED), `portion` (counts and sizes as printed, e.g. "two eggs",
  "(8)", "S / L"), `has_choice` (yes when the dish comes with a choice of main ingredient, filling or preparation, so
  the bot should ask before estimating), `belongs_to` (add-ons only: the dish, or "section: X", the extra is printed
  for), `confidence` (high / medium / low), `notes`.
  `tags`, `portion`, `has_choice` and `belongs_to` are copied from the photo, never inferred; empty means nothing is printed.
- `answer_key_photo_notes.csv`: one row per photo with the item count, the lines left out because their name is
  cut off mid-word (`cut_off_lines_left_out` – neither right nor wrong if a model lists them), and what makes the
  photo tricky (cut-off edges, glare, obstruction, sideways text). Use it when scoring: on photos 13, 16, 17 and 24 a model
  *should* say that part of the menu is missing.
- `answer_key_review.md`: the 54 items marked medium or low confidence, grouped by photo, so you only need to check
  those, plus the photo notes in a table.

How to score against it: compare the model's list of names to `name` (ignore case and punctuation);
`description` and `price` are there for the cholesterol estimator later and for stricter tests.
A blank `price` means nothing readable is printed; a model that guesses one there is wrong.
Items with `category = other` (a price line for a whole tasting menu, a "coming soon" note) are context, not dishes.

## Next step

Load the 25 Telegram-size photos and `answer_key.csv` into a LangSmith dataset and run the first model comparison.
