# Answer format (the "output contract")

Every model must return **one JSON object** and nothing else - no greeting, no explanation, no code fences.
JSON is a plain-text way of writing structured data that code can read without a human. The shape is:

```json
{
  "readable": "yes",
  "problems": "",
  "items": [
    {
      "section": "STARTERS",
      "category": "food",
      "name": "Marinated olives",
      "description": "",
      "price": "7.00",
      "tags": "",
      "portion": "",
      "has_choice": "no",
      "belongs_to": "",
      "confidence": "high"
    }
  ]
}
```

## Photo-level fields

| field | allowed values | meaning |
|---|---|---|
| `readable` | `yes` / `partly` / `no` | `yes` = every item on the photo can be read. `partly` = some items or prices are cut off, hidden, blurred or out of focus. `no` = it is not a readable menu (not a menu, too blurry, too dark). |
| `problems` | short free text, or empty | What is wrong, if anything: "right edge cut off, prices missing", "glare over the lower half", "salt shakers hide the centre". Empty when `readable` is `yes`. |

## Item fields (one object per dish, drink or add-on; ten fields, all required)

| field | allowed values | rule |
|---|---|---|
| `section` | text | The heading the item sits under, as printed. Empty if the menu has no headings. |
| `category` | `food` / `drink` / `add-on` / `other` | `add-on` = an extra you add to a dish ("add cheese .75"). `other` = a printed line that is not something you order on its own (a set-menu price line, a "coming soon" note). |
| `name` | text | Exactly as printed: same spelling, same capitals, including misspellings. Never translated, never "corrected". |
| `description` | text | The ingredient or description line(s) printed under or beside the name. Empty if none. Options printed in smaller type under an item belong here. |
| `price` | text | Digits as printed, no currency symbol ("7.00", "12.95", "530", "20c"). Two sizes: "4.50 regular / 8.00 grande". **Blank if no price is printed or the price cannot be read. Never guess a price.** If one price is printed once for a group of items, repeat it on each item. |
| `tags` | text | Dietary or allergen marks printed next to the item or its section, exactly as printed and comma-separated: "GF", "VE", "V", "N", "VEGAN", "VEGETARIAN", "VEG", "NON-VEG", "PLANT BASED". Empty if none. |
| `portion` | text | Counts and sizes as printed: "two eggs", "(8)", "3 strips", "S / L", "half / full", "for two". Empty if none. |
| `has_choice` | `yes` / `no` | `yes` when the item is made with a choice the customer picks: "mascarpone or Parmigiano", "choice of chicken, steak or combo", "Veg / Chicken", "eggs any style". Size choices do not count (they go in `portion`). |
| `belongs_to` | text | Add-ons only: the name of the dish the extra is printed under or next to ("add cheese" under "Steak sandwich" → `Steak sandwich`), or `section: X` when the menu offers it for every item in a section (pizza toppings → `section: all pizzas`). Empty for everything else, and empty for a standalone extra such as a side of hot sauce. |
| `confidence` | `high` / `medium` / `low` | The model's own judgement of its reading of this item. `high` = name and price read clearly. `medium` = print was small, faint, skewed or partly hidden. `low` = the name is readable but the price or description is doubtful. The app uses this to decide which items to confirm with the user; the test uses it to check whether a model knows when it is unsure (see `scoring_rules.md`, score 10). Not to be confused with the `confidence` column of the answer key, which is about the human reading. |

## Rules the model must follow

These are the same six rules, word for word, as in the prompt; `prompts/menu_reader_v1.md` is the source of truth and this copy is for readers of this document.

1. Never invent an item. If you are not sure something is an item, leave it out.
2. Never guess a price. A blank price is correct when nothing readable is printed.
3. If an item's name is cut off at the edge of the photo or hidden, do not list it; mention it in "problems".
4. Options printed in smaller type under an item, without their own price, belong in that item's description, not as separate items.
5. Ignore headings, slogans, opening hours, addresses, legal notes, and any other menu or sign visible at the edge of the photo.
6. If part of the menu is cut off, hidden, blurred, in shadow or covered by glare, set "readable" to "partly" and describe the problem in "problems". If the photo is not a menu or cannot be read at all, set "readable" to "no", explain in "problems", and return an empty items list.
