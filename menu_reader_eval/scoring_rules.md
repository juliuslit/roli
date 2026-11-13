# Scoring rules for the menu reader test (plain English, for approval before any code)

## How a run works

Each model gets the same prompt and the same 25 Telegram-size photos. Every photo is sent **twice**, with the same prompt, because models do not always give the same answer to the same input; running twice shows whether a model is steady or lucky. So one model = 50 answers. Each answer is compared with the expected answer for that photo (the file in `expected/`) and gets the scores below. A model's score on a measure is the average over its 50 answers, except where a rule says "on both runs", which means each of the two runs must clear the bar on its own.

## Where the side information lives

Several rules below refer to **scoring hints**. They exist in two places with the same content: as a block called `scoring_hints` inside each `expected/menu_NN.json` file (that is what the scoring code reads), and as a table, `scoring_hints.csv`, one row per photo (that is what you read). They hold: which photos must be flagged `partly`, which cut-off lines are set aside, and which answer-key items are medium or low confidence.

## 0. What is compared, and what is set aside

**Items that are compared.** Items whose `category` is food, drink or add-on, on both sides.

**Items marked `other` are set aside.** The key has 8 of them: a set-menu price line ("4000 baht + service"), a wine-pairing line, a "coming soon... milkshakes" note, an "other breads available" line, a "make it vegan" note. Why they are not scored: (1) none of them is a dish a person eats, so the cholesterol step never needs them; (2) whether such a line is "an item" is a judgment call - two careful humans would disagree - so scoring it would measure agreement with my judgment, not reading ability; (3) with 8 lines out of 930, scoring them could not change a pass or fail anyway. Setting them aside means: if the model lists one, nothing happens; if it skips one, nothing happens. They stay in the key because the recommender may later want the set-menu price line.

**Cut-off lines.** On four photos (13, 16, 17, 24), some lines are cut off mid-word by the edge of the photo. We agreed these are left out: they are not in the expected answer, and rule 3 of the prompt tells the model not to list them either. So a model that follows the rules never produces them. This paragraph only covers what the scorer does when a model lists one anyway. It is not counted as "found" (nothing in the expected answer matches it) and it is not counted as "invented" either, because "invented" is reserved for things that are not on the menu at all, and this line is on the menu, just unreadable. Instead it is counted under its own measure, score 2b below, as a rule break. The scorer recognises these lines from the fragments listed in the scoring hints (column `cut_off_lines_left_out`). Example: photo 17 shows "...occoli w/ Garlic Sauce". A model that returns "Broccoli w/ Garlic Sauce" gets no credit for it, is not marked as inventing, and gets one point on score 2b for listing a line it was told to leave out.

**Sections are not compared** this round (agreed earlier). Keeping them in the answer costs nothing and the cholesterol step may use them.

**When two names count as the same.** The scorer compares names in three steps:
1. Clean both names the same way: make everything lower-case, remove punctuation (commas, dots, apostrophes, brackets, hyphens, slashes), collapse repeated spaces, and strip dietary marks that sit at the end or in brackets (GF, VE, V, N, "(vegetarian)", "(vegan)"). So "Chicken Tikka (Vegetarian)" and "chicken tikka" clean to the same thing.
2. If the cleaned names are identical, they match.
3. If not, measure how similar the two cleaned strings are, letter by letter (the standard "edit distance" measure, expressed as a percentage). At 90 % or more they match: "chilli chicken" vs "chilly chicken" is 93 % similar, match. "chicken" vs "chicken wings" is 54 %, no match. "beef burger & fries" vs "beef burger and fries" cleans to the same string in step 1 before this step is reached.

**Each item can be used once.** The scorer pairs items up: one expected item with one model item. Once paired, both are taken off the table. Example: the expected answer has "Egg Fried Rice" once; the model lists "Egg Fried Rice" twice. The first copy is paired and counted as found; the second has nothing left to pair with, so it counts as invented. When one expected item could pair with several model items (say the expected "Chicken Tikka" and the model's "Chicken Tikka" and "Chicken Tikka Masala"), the closest one by the similarity test is used ("Chicken Tikka"), and the other stays on the table for other pairings.

## 1. Dishes found - pass bar: 95 % on average, and no photo below 80 %

Share of expected items that have a matching model item. Example: the expected answer has 40 items and 38 of them are matched, so the score is 95 %.

## 2. Invented dishes - pass bar: 0 per photo, on both runs

Number of model items that match no expected item and are not on the cut-off list. A heading, slogan, opening-hours line or address returned as an item counts as invented. A description line returned as its own item counts as invented.

## 2b. Cut-off lines listed anyway - pass bar: 0 on both runs (bar added 2026-10-29; was reported only)

Number of model items that match a fragment in the scoring hints' `cut_off_lines_left_out` list. These were not invented, but the prompt said not to list them. Reported per model and, from 2026-10-29, a pass bar like score 2: a model that lists a line it was told to leave out breaks the rule, and the bar is 0 on both runs.

## 3. Prices right - pass bar: 95 % of matched items

For every matched item: the model's price is right when, after removing currency symbols, spaces and dashes, the digits are the same ("12.95" = "$12.95" = "12,95"; "310-00" = "310.00"). For two-size prices, both numbers must be present ("4.50 regular / 8.00 grande" needs 4.50 and 8.00). When the expected price is blank, the model's price must also be blank: a number there is a guess and is wrong. Pence and cents count as the same amount as their decimal form: "50p" = "0.5" = "0.50", "20c" = "0.20" (added 2026-10-28, interpretation 4 below).

## 4. Descriptions right - pass bar: 90 % of matched items that have a description

For matched items whose expected description is not empty: the model's description is right when its name and description together contain **every** ingredient word from the expected description (joined test since 2026-10-29, interpretation 15; before that the description field alone). Filler words (with, and, &, a, the, of, on, in, our, served) and punctuation are ignored; so is case. Words must otherwise match exactly: "eggs" and "egg" are different words (changed 2026-10-28, see Interpretations below). A dropped ingredient is a miss, because the cholesterol estimate depends on the ingredients ("fried egg" dropped from a description changes the answer). Extra words in the model's description do not hurt.

## 5. Tags, portion, has_choice, belongs_to - reported, no pass bar this round

- `tags`: right when the same set of marks is present, in any order, ignoring case.
- `portion`: right when the numbers in the model's text equal the numbers in the expected text ("two eggs" vs "2 eggs" is right).
- `has_choice`: right when yes/no agrees.
- `belongs_to`: for matched add-ons, right when it names the same dish (same name test as in section 0) or the same section.

These four are new and we have no idea yet how models handle them; the first run tells us where to set bars.

## 6. Format right - pass bar: 98 % of answers

An answer is right when it is valid JSON, has the three top-level fields, every item has all ten fields, and every value is one of the allowed ones (`readable` is yes/partly/no, `category` is one of the four, `has_choice` is yes/no, `confidence` is high/medium/low). An answer preceded by a sentence is wrong even if the JSON inside is fine; the bot would break on it. An answer wrapped in a code fence passes once the fence is removed, but is counted and reported as "fenced" (interpretation 18, 2026-10-30; before that it was wrong).

## 7. Bad photos caught - pass bar: all 7 flagged photos caught, on both runs

Seven photos have something missing or hidden - an edge cut off, glare over text, objects in the way - so the expected answer for them says `readable: partly` (photos 02, 10, 13, 15, 16, 17, 24; the list is in the scoring hints, column `expected_readable`). A model catches one when it returns `partly` or `no` for it. For the other 18 photos, returning `partly` is a false alarm: counted and reported, and held against the model only if it happens on more than 3 photos in a run.

## 8. Speed - pass bar: under 60 seconds per photo, averaged

Wall-clock time from sending the photo to receiving the full answer, as recorded by LangSmith. Raised from 10 seconds on 2026-10-28: the smoke test showed the time is almost entirely the model writing the JSON (about 85 tokens per item at 70-90 tokens per second on DeepInfra), so a 37-item menu, the test-set average, takes about 40 seconds whatever the model.

## 9. Cost - reported

Cents per photo from OpenRouter's usage figures. Among the models that pass bars 1, 2, 2b, 3, 4, 6, 7 and 8, the cheapest wins; scores 5 and 10 break ties.

## 10. Does the model know when it is unsure - reported, no pass bar this round

Each item in the model's answer carries the model's own `confidence` (high / medium / low). The scorer reports, per model: the share of items marked `high` that turned out wrong (name unmatched or price wrong), and the share of items marked `low` or `medium` that turned out wrong. A model that knows itself has a low first number and a high second number. This matters for the app: it will ask the user to confirm low-confidence items, which only helps if "low" really means "likely wrong". A model whose "high" items are wrong as often as its "low" ones is giving us no information, and that counts against it when two models are otherwise close.

## Decision rule

A model passes when it clears every pass bar above on both runs. If no open-weight model passes, the closest one is compared with the closed benchmark model and we decide whether the gap is worth the price difference. If a model's two runs differ by more than 5 points on "dishes found", it is flagged as unstable regardless of its average.

## Where the answer key itself may be wrong

54 of the 930 items in the answer key are marked `medium` (33) or `low` (21) confidence: my own reading of them was uncertain (small print, glare, a skewed price column). They are listed per photo in the scoring hints (columns `medium_confidence_items` and `low_confidence_items`). This is a different thing from the model's `confidence` field in score 10: that one is the model's opinion of its own reading; this one is about the key. The rule for them: when a model's answer **disagrees** with the key on one of these items (different name, different price), the scorer does not count it right or wrong straight away. It puts the item on a short "check" list. You look at the photo, decide who is right, and either the key is corrected or the model's point is counted as wrong. When the model **agrees** with the key, the point is counted as right with no check. Since these 54 items are under 6 % of the key, they can shift a score a little but cannot turn a fail into a pass on their own.

## Interpretations made during coding (agreed 2026-10-28)

Three points the rules above left open, settled when the scoring code was written:

1. **Plurals (score 4).** No plural handling. After lower-casing and removing punctuation, a word in the expected description must appear exactly in the model's description. "eggs" and "egg" are different words. This replaced the earlier "plural 's' is ignored" wording in score 4.
2. **Cut-off recognition (score 2b).** Pairing runs first, as in section 0. Only model items left unpaired are then tested against the `cut_off_lines_left_out` fragments. A model item matches a fragment when, after cleaning both the same way as names, one contains the other or they are 90 % similar. Matches count under 2b; the rest are invented.
3. **Confidence calibration (score 10).** A model item counts as wrong unless it paired with an expected item and its price is right. No exceptions: invented items, cut-off lines listed anyway, and price disagreements on medium/low key items (which go to the check list for the price score) all count as wrong here.
4. **Pence and cents (score 3).** When the digit test fails, the amounts are compared as numbers with "p" and "c" meaning hundredths: "50p each" and "0.5" are the same price. A side effect: "18.1" and "18.10" also count as the same. Clarified 2026-10-30: a hyphen between a number and two digits is a decimal point in this amount test ("105-00" is 105.00), so a model that writes "105" for a key price of "105-00" is right, as rule 3's own example intends. Found when Sonnet 5.5 wrote whole numbers for all 157 prices on photo 10.

Five more, agreed 2026-10-29 after the first Haiku batch (150 answers). They change what "found" and "invented" mean, so results before and after are not comparable; every results folder records which rules it was scored under.

5. **Joined text (score 1).** When the strict name test fails, the expected name is tested against the model's name and description joined into one string, cleaned the same way, with the same 90 % rule. A match counts as found. Reason: photo 02 prints dish and ingredients as one sentence and the key kept the whole sentence as the name; the model split it into name + description, which is the more useful reading.
6. **Grouped items (score 1 and 2).** A model item still unpaired after 5 whose name or description contains, as whole words, two or more expected names that are still unfound counts each of them as found, and is not invented. The number of such groupings is reported per model. Grouped expected items are found only: they have no partner for scores 3, 4, 5 and 10. Reason: "Pizza By The Slice: Vegetarian, Combo, Pepperoni" against three key items.
7. **Three outcomes for a model item (score 2).** After 5 and 6, a model item still unpaired is one of: *found* (handled above), *garbled* (its name is 50-89 % similar to a still-unfound expected name: counts as not found, not invented, reported separately), *invented* (under 50 % to everything). "Invented" now means genuinely new items only.
8. **Cut-off recognition last (score 2b).** Interpretation 2 is applied only to model items still unpaired after 5 and 6, before the garbled/invented split of 7, so a cut-off line is never labelled garbled.
9. **Check list (section "Where the answer key itself may be wrong").** Only items the model returned with a different name (a garbled match to a medium/low key item) or a different price (a pair on a medium/low key item) go on the check list, and those items stay out of the score until checked. A medium/low key item the model simply did not list is a plain miss and is not listed.

Two more, agreed 2026-10-29 after the Qwen3.6 batch on DeepInfra. Every batch on disk (Haiku morning, Haiku fresh, Qwen3.6 DeepInfra) was re-scored under interpretations 1-11 before any further run, so all models are scored the same way.

10. **Menu shorthand (section 0 cleaning, and score 4).** Before punctuation is removed, "w/" becomes "with", "w/o" becomes "without" and "&" becomes "and", in names and in descriptions. Nothing further. Reason: photo 17 prints "w/" throughout; "Broccoli w/ Garlic Sauce" against "Broccoli with Garlic Sauce" was 89 % similar and fell to garbled.
11. **Grouping stays within a category (interpretation 6).** A model item's text can only group expected items of the same category as itself. Reason: on photo 05 the sandwich's description named "sausage" and "smoked bacon", which counted the add-ons of those names as found and left the sandwich rows looking invented.

Three more, agreed 2026-10-29 after the Haiku v2 invented list was reviewed. All batches on disk were re-scored again under 1-14.

12. **"Other" is set aside after matching, not before (section 0).** Items of every category, including `other`, go through the name matching (steps 1 and 2). Then three kinds of item are set aside: pairs whose expected item is `other`, unmatched expected `other` lines, and unmatched model items the model itself marked `other`. Reason: on photo 15 the key's "Make it Vegan" note is `other`; the model returned it as food and, with `other` removed before matching, it counted as invented.
13. **Joined text by words (interpretation 5).** Besides the 90 % test, an expected name and a model item match when every word of the expected name (2 or more words) appears in the model's cleaned name + description, or every word of the model's name (2 or more words) appears in the expected cleaned name + description. One-word names use the 90 % test only. A model item whose text holds two or more unfound expected names of its own category is not paired by this word test; it is left for interpretation 6, so the EXTRAS line still finds all seven add-ons rather than one (ordering decided during coding, 2026-10-29). Reason: "Jacket Potatoes" with "Tuna Mayonnaise" as the description, against the key item "Tuna Mayonnaise"; "Oysters" + "Humboldt Bay" against "Oysters - Humboldt Bay"; "Yuzu Lime" against "Badger Sparkling Yuzu Lime".
14. **Cut-off recognition by whole words (score 2b).** A fragment's partial word (the one next to the "...", last or first) and any bracketed note at its end are dropped; a model item is the cut-off line when the remaining words appear in its cleaned name in order and next to each other. "...occoli w/ Garlic Sauce" becomes "with garlic sauce" and recognises "Broccoli with Garlic Sauce". A fragment with no whole word left ("...oy") recognises nothing. This only classifies the item; it is never credit, and score 2b now has a pass bar of 0 on both runs.
15. **Description words anywhere in the item (score 4).** The expected ingredient words are looked for in the model's name and description joined, not in the description field alone. Reason: interpretations 5 and 13 pair items where the model put the dish name and the ingredients in different fields from the key, and those pairs were then failing the description test for words that sat in the model's name. Agreed 2026-10-29.
16. **Tie-break in pairing (section 0).** When an expected item has two equally similar model candidates (or a model item two equally similar expected items), the pair in the same section is preferred, then the pair whose prices agree, then the earlier item. Applies to the strict pairing and to the joined-text pairing. Reason: photo 12 now has "Tuna Mayo" twice (a 7.50 sandwich and a 6.50 jacket potato); without the tie-break the two could cross-pair and show a wrong price. Agreed 2026-10-29.

Two more, from the round-one review on 2026-10-30. All batches re-scored under 1-18.

17. **Parent line with its children (score 1).** When a model item pairs with a key line of category `other` that is a heading over options (such as "Childs Half Sandwich" or "FRESHLY BAKED JACKETS"), and that model item's description names two or more of the parent's children, those children count as found (found only, like interpretation 6). Children are the key rows directly under the parent with the same section and price. A child's name is matched after dropping any word that also appears in the parent's name ("Cheese & Ham Sandwich" under "Childs Half Sandwich" is looked for as "cheese and ham"). Reason: Haiku, Sonnet and Gemini keep such option lists as one item with the options in the description, which is a complete reading, not a miss.
18. **Code fence (score 6).** Format passes when the JSON parses after a surrounding code fence is removed; fenced answers are counted and reported per batch. Reason: Gemini wrapped two of fifty answers on one photo; the bot can strip a fence, and the count still shows which models do it.
