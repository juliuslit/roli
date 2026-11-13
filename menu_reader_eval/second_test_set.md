# Second test set - notes for a held-out set

Started 2026-10-30. Notes only; no photos collected, no action yet.

## Why
Every prompt change, scoring interpretation and answer-key ruling in round one was made after looking at how the models did on the 25 photos in `menu_test_set/`. The prompts (v4, v5) carry examples taken from those photos (the broccoli line from 17, the pizza slices from 21, the dips from 06), and 16 scoring interpretations plus about 70 key edits were made with the models' answers in view. The results on this set therefore overstate how the winner will do on a photo it has never influenced. A second set that no decision has touched is the only honest check before the reader goes into the bot.

## What it needs
- **20 to 30 new photos**, none of them used for any prompt, scorer or key decision, and not looked at while any of those were being made. Once collected, the set is sealed: no edits to prompts or rules in response to its results until a third set exists.
- **The same mix as the first set**, roughly: a third clean printed menus, a third dense or long menus (100+ items, two columns, placemats), a third hard photos (glare, shadow, angle, chalk or handwriting, objects in the way, an edge cut off). The first set has 7 "partly" photos of 25; keep that share.
- **Same preparation**: own photos plus Wikimedia Commons with licences in a manifest; a 1280-pixel Telegram copy of each; an answer key typed as printed with the 13 columns of `answer_key.csv`, following every convention settled in round one (one row per orderable option, add-ons as rows, tiers in price and portion, headings as `other`, cut-off lines left out and listed in the photo notes); `photo_level.csv` with readable and problems; medium/low confidence marks on uncertain items.
- **Key written before any model sees the photos**, by a person, and reviewed once by a second person if possible. Model answers must not be used to draft it.
- **English menus only**, as in round one. Foreign-language menus stay in `_not_used_foreign_language/` for a later round.
- **At least five photos of the kind the first set lacks**: handwritten specials boards, photos taken in restaurant lighting at night, menus photographed from a seated position at an angle, a menu on a phone or tablet screen, and one or two non-menu photos (a receipt, a shop sign) to test `readable: no`.

## How it is used
- Run the chosen closed and open model once, with the final prompt and workflow from round two, 25 to 30 photos twice each, under the final scoring rules, with no re-scoring after rule changes.
- Report the same table as round one. The gap between first-set and second-set numbers is the overfitting estimate and goes in the portfolio write-up as such.
- Items where the model disagrees with the key go to the check list as before; key errors found this way are corrected, but prompts and rules are not.

## Open points
- Who photographs: Julius's own photos are the closest to real Telegram use; Commons photos widen the variety but tend to be well lit and straight on.
- Whether to keep one or two photos of the same restaurant as the first set (different menu page) to test memorisation of layout; probably not needed.
- Timing: after round two's workflow choice, before any hosting work.
