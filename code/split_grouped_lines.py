"""One-off key edit, 2026-10-28: on photo 06, split each grouped add-on line into one item per topping.

The menu prints the toppings one per line with a single price for the group. answer_format.md says a
price printed once for a group is repeated on each item, so the key now follows its own rule.
A backup of the key was taken first (answer_key_backup_before_split_2026-10-28.csv).
"""
import csv

from config import TEST_SET

KEY = TEST_SET / "answer_key.csv"
PHOTO = "menu_06_pizzaface_uk_printed_spread.jpg"
NOTE = "split from a grouped line, 2026-10-28"

rows = list(csv.DictReader(open(KEY, encoding="utf-8", newline="")))
fields = list(rows[0].keys())
out, split_count, new_items = [], 0, 0
for r in rows:
    grouped = r["file"] == PHOTO and r["category"] == "add-on" and ", " in r["name"]
    if not grouped:
        out.append(r)
        continue
    split_count += 1
    text = r["name"].split(":", 1)[1] if r["name"].startswith("DIPS:") else r["name"]
    for part in [p.strip() for p in text.split(", ") if p.strip()]:
        new = dict(r)
        new["name"] = part
        low = part.lower()
        new["tags"] = "VEGAN" if ("vgn" in low or "vegan" in low) else ""
        new["notes"] = NOTE
        out.append(new)
        new_items += 1
# renumber item_no within each photo
counter = {}
for r in out:
    counter[r["file"]] = counter.get(r["file"], 0) + 1
    r["item_no"] = str(counter[r["file"]])
with open(KEY, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(out)
print(f"{split_count} grouped lines replaced by {new_items} items; key now has {len(out)} rows")
