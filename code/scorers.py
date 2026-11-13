"""The scorers, one function per score in menu_reader_eval/scoring_rules.md.

Vocabulary used below
  expected  = the correct answer for a photo (the "expected" block of expected/menu_NN.json)
  answer    = the model's parsed answer (a dict), or None when the answer was not JSON
  hints     = the "scoring_hints" block of the same file
  raw_text  = the exact text the model returned, used only by the format score

All functions are plain Python with no LangSmith inside, so they can be tested
on their own and wrapped for LangSmith later.
"""
import json
import re

# ---------------------------------------------------------------------------
# Section 0 of the rules: what is compared, and when two names are the same
# ---------------------------------------------------------------------------

COMPARED_CATEGORIES = {"food", "drink", "add-on"}
DIETARY_MARKS = {"gf", "ve", "v", "n", "vg", "vgn", "vegan", "vegetarian", "veg", "nonveg", "plantbased"}
FILLER_WORDS = {"with", "and", "a", "the", "of", "on", "in", "our", "served"}
NAME_MATCH_THRESHOLD = 0.90

NUMBER_WORDS = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
    "seven": "7", "eight": "8", "nine": "9", "ten": "10", "eleven": "11", "twelve": "12",
}


def normalise_abbreviations(s: str) -> str:
    """Interpretation 10 (2026-10-29): the menu shorthand "w/" means "with", "w/o" means "without",
    "&" means "and". Applied to names and descriptions before punctuation is removed, so
    "Broccoli w/ Garlic Sauce" and "Broccoli with Garlic Sauce" clean to the same string. Nothing further."""
    s = re.sub(r"(?<![a-z])w/o(?![a-z])", " without ", s)
    s = re.sub(r"(?<![a-z])w/", " with ", s)
    return s.replace("&", " and ")


def clean_name(name: str) -> str:
    """Step 1 of the name test: lower-case, no punctuation, no dietary marks at the end."""
    s = normalise_abbreviations((name or "").lower())
    # marks in brackets anywhere: "(v)", "(vegan)", "(gf)"
    s = re.sub(r"\((?:\s*(?:gf|ve|v|n|vg|vgn|vegan|vegetarian|veg|non-veg|plant based)\s*,?)+\)", " ", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)       # punctuation out
    words = s.split()
    while words and words[-1] in DIETARY_MARKS:   # marks at the end: "coleslaw v", "matto vgn"
        words.pop()
    return " ".join(words)


def similarity(a: str, b: str) -> float:
    """Step 3 of the name test: 1 - (edit distance / length of the longer string).

    "chilli chicken" vs "chilly chicken" -> 0.93; "chicken" vs "chicken wings" -> 0.54.
    """
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return 1.0 - prev[-1] / max(len(a), len(b))


def names_match(a: str, b: str) -> bool:
    return similarity(clean_name(a), clean_name(b)) >= NAME_MATCH_THRESHOLD


def is_other(item: dict) -> bool:
    return str(item.get("category", "")).strip().lower() == "other"


def compared_items(items: list) -> list:
    """Keep food / drink / add-on. 'other' is set aside. Anything else (a bad category) stays
    in, so a heading returned as an item still counts as invented."""
    return [it for it in items if isinstance(it, dict) and str(it.get("category", "")).strip().lower() != "other"]


def tie_break(exp_item: dict, mod_item: dict) -> tuple:
    """Interpretation 16: among equally good name matches, prefer the model item in the same section,
    then the one whose price agrees. Returns a sort key where smaller is better (0 = same, 1 = different)."""
    same_section = names_match(str(exp_item.get("section", "")), str(mod_item.get("section", "")))
    same_price = price_right(exp_item.get("price"), mod_item.get("price"))
    return (0 if same_section else 1, 0 if same_price else 1)


def pair_items(expected_items: list, model_items: list) -> dict:
    """Pair each expected item with at most one model item, closest name first.

    Returns {"pairs": [(exp_index, model_index, similarity)], "unmatched_expected": [...], "unmatched_model": [...]}
    """
    exp_clean = [clean_name(it.get("name", "")) for it in expected_items]
    mod_clean = [clean_name(it.get("name", "")) for it in model_items]
    candidates = []
    for i, e in enumerate(exp_clean):
        for j, m in enumerate(mod_clean):
            s = similarity(e, m)
            if s >= NAME_MATCH_THRESHOLD:
                candidates.append((s, i, j))
    # best similarity first; ties broken by same section, then same price (interpretation 16), then position
    candidates.sort(key=lambda t: (-t[0], *tie_break(expected_items[t[1]], model_items[t[2]]), t[1], t[2]))
    used_e, used_m, pairs = set(), set(), []
    for s, i, j in candidates:
        if i in used_e or j in used_m:
            continue
        used_e.add(i); used_m.add(j); pairs.append((i, j, s))
    return {
        "pairs": pairs,
        "unmatched_expected": [i for i in range(len(expected_items)) if i not in used_e],
        "unmatched_model": [j for j in range(len(model_items)) if j not in used_m],
    }


def fragment_words(fragment: str) -> list:
    """Interpretation 14: the whole words of a cut-off fragment. A note in brackets at the end
    ("...HILE COLORADO (Chile Colorado)") is the key author's full reading and is dropped; so is the
    partial word next to the "..." (the last word when the dots are at the end, the first when they
    are at the start). What remains is cleaned like a name: "...occoli w/ Garlic Sauce" -> [with, garlic, sauce]."""
    f = re.sub(r"\([^)]*\)\s*$", "", fragment.strip()).strip()
    leading, trailing = f.startswith("..."), f.endswith("...")
    words = clean_name(f.replace("...", " ")).split()
    if trailing and words:
        words = words[:-1]
    elif leading and words:
        words = words[1:]
    return words


def matches_cut_off_fragment(model_name: str, fragments: list) -> bool:
    """Score 2b: is this unpaired model item one of the cut-off lines in the hints?
    Called only for model items left over after pairing and grouping (interpretations 2 and 8).
    Interpretation 14: it is, when the fragment's remaining whole words appear in the model's cleaned
    name, in order and next to each other. This classifies the item; it is not credit."""
    m = clean_name(model_name).split()
    for frag in fragments:
        w = fragment_words(frag)
        if w and any(m[k:k + len(w)] == w for k in range(len(m) - len(w) + 1)):
            return True
    return False


def uncertain_key_items(hints: dict) -> dict:
    """{cleaned name: 'medium' | 'low'} for the answer-key items whose reading was uncertain."""
    out = {}
    for level in ("medium", "low"):
        for name in hints.get(f"{level}_confidence_items", []) or []:
            out[clean_name(name)] = level
    return out


GARBLED_THRESHOLD = 0.50


def joined_text(item: dict) -> str:
    """Interpretation 5: the model's name and description as one cleaned string."""
    return clean_name(f"{item.get('name', '')} {item.get('description', '')}")


def pair_by_joined_text(exp_items: list, mod_items: list, unmatched_e: list, unmatched_m: list) -> list:
    """Interpretation 5 (joined text): an expected name that is 90 %+ similar to a model item's
    name + description counts as found; interpretation 13 adds the word-containment test (see below).
    Greedy, most similar first, each item used once.
    Returns [(exp_index, model_index, similarity)]."""
    cands = []
    for i in unmatched_e:
        e = clean_name(exp_items[i].get("name", ""))
        if not e:
            continue
        e_words, e_joined_words = e.split(), set(joined_text(exp_items[i]).split())
        for j in unmatched_m:
            jt = joined_text(mod_items[j])
            sim = similarity(e, jt)
            m_words = clean_name(mod_items[j].get("name", "")).split()
            # Interpretation 13: besides the 90 % test, every word of a 2+ word expected name inside the model's
            # name + description, or every word of a 2+ word model name inside the expected name + description.
            contained = ((len(e_words) >= 2 and set(e_words) <= set(jt.split()))
                         or (len(m_words) >= 2 and set(m_words) <= e_joined_words))
            # A model item that holds two or more unfound expected names of its category is a grouping
            # (interpretation 6) and is left for that step, or one dip would pair and the other eight stay unfound.
            if contained and sim < NAME_MATCH_THRESHOLD and len(contained_expected_names(mod_items[j], exp_items, unmatched_e)) >= 2:
                contained = False
            if sim >= NAME_MATCH_THRESHOLD or contained:
                cands.append((sim, i, j))
    cands.sort(key=lambda t: (-t[0], *tie_break(exp_items[t[1]], mod_items[t[2]]), t[1], t[2]))   # interpretation 16
    used_e, used_m, pairs = set(), set(), []
    for sim, i, j in cands:
        if i in used_e or j in used_m:
            continue
        used_e.add(i); used_m.add(j); pairs.append((i, j, sim))
    return pairs


def contained_expected_names(model_item: dict, exp_items: list, unmatched_e: list) -> list:
    """Interpretation 6 (grouped items): which still-unfound expected names appear whole, as words,
    inside this model item's name + description. Cleaned names shorter than 3 characters are ignored.
    Interpretation 11 (2026-10-29): only expected items in the same category as the model item count,
    so a sandwich's description naming "sausage" and "bacon" no longer finds the add-ons of that name."""
    text = joined_text(model_item)
    category = str(model_item.get("category", "")).strip().lower()
    hits = []
    for i in unmatched_e:
        if str(exp_items[i].get("category", "")).strip().lower() != category:
            continue
        e = clean_name(exp_items[i].get("name", ""))
        if len(e) >= 3 and re.search(rf"(?<![a-z0-9]){re.escape(e)}(?![a-z0-9])", text):
            hits.append(i)
    return hits


def closest_expected(model_item: dict, exp_items: list, unmatched_e: list) -> tuple:
    """Interpretation 7 (three outcomes): the most similar still-unfound expected name.
    Returns (exp_index or None, similarity)."""
    m = clean_name(model_item.get("name", ""))
    best, best_sim = None, 0.0
    for i in unmatched_e:
        sim = similarity(clean_name(exp_items[i].get("name", "")), m)
        if sim > best_sim:
            best, best_sim = i, sim
    return best, best_sim


# ---------------------------------------------------------------------------
# Field comparisons used by scores 3, 4 and 5
# ---------------------------------------------------------------------------

def price_digits(price: str) -> str:
    """'$12.95' -> '1295', '310-00' -> '31000', '£2.75 each' -> '275', '' -> ''."""
    return re.sub(r"\D", "", str(price or ""))


def price_numbers(price: str) -> list:
    """The numbers in a price as decimals, pence and cents converted: '50p each' -> [0.5],
    '(S) 1.95 (L) 7.95' -> [1.95, 7.95], '12,95' -> [12.95]. Used only when the digit test fails."""
    s = str(price or "").lower()
    s = re.sub(r"(\d),(\d\d)\b", r"\1.\2", s)                  # 12,95 -> 12.95
    s = re.sub(r"(\d)-(\d\d)\b", r"\1.\2", s)                  # 310-00 -> 310.00 (rule 3's own example; clarified 2026-10-30)
    out = []
    for num, unit in re.findall(r"(\d+(?:\.\d+)?)\s*(p|c)?\b", s):
        value = float(num)
        out.append(value / 100 if unit else value)
    return out


def price_right(expected_price: str, model_price: str) -> bool:
    """Score 3. Blank expected means the model must also be blank (a number is a guess).
    Right when the digits agree, or (interpretation 4) when the amounts agree after
    converting pence/cents: '50p each' = '0.5' = '0.50'."""
    if price_digits(expected_price) == price_digits(model_price):
        return True
    e, m = price_numbers(expected_price), price_numbers(model_price)
    return bool(e) and e == m


def description_words(text: str) -> set:
    """Lower-case words, punctuation and filler words removed. No plural handling:
    "eggs" and "egg" are different words (interpretation 1 in scoring_rules.md)."""
    s = normalise_abbreviations((text or "").lower())
    return {w for w in re.findall(r"[a-z0-9]+", s) if w not in FILLER_WORDS}


def description_right(expected_desc: str, model_desc: str) -> bool:
    """Score 4: every ingredient word of the expected description appears in the model's."""
    return description_words(expected_desc) <= description_words(model_desc)


def tags_right(expected_tags: str, model_tags: str) -> bool:
    def tagset(t):
        return {x.strip().lower() for x in str(t or "").split(",") if x.strip()}
    return tagset(expected_tags) == tagset(model_tags)


def portion_numbers(text: str) -> list:
    s = (text or "").lower()
    for word, digit in NUMBER_WORDS.items():
        s = re.sub(rf"\b{word}\b", digit, s)
    return sorted(re.findall(r"\d+(?:\.\d+)?", s))


def portion_right(expected_portion: str, model_portion: str) -> bool:
    return portion_numbers(expected_portion) == portion_numbers(model_portion)


def has_choice_right(expected: str, model: str) -> bool:
    return str(expected or "").strip().lower() == str(model or "").strip().lower()


def belongs_to_right(expected: str, model: str) -> bool:
    e, m = str(expected or "").strip(), str(model or "").strip()
    if not e and not m:
        return True
    e_sec, m_sec = e.lower().startswith("section:"), m.lower().startswith("section:")
    if e_sec or m_sec:
        return e_sec and m_sec and names_match(e.split(":", 1)[1], m.split(":", 1)[1])
    return names_match(e, m)


# ---------------------------------------------------------------------------
# Score 6: format
# ---------------------------------------------------------------------------

ITEM_FIELDS = ["section", "category", "name", "description", "price", "tags",
               "portion", "has_choice", "belongs_to", "confidence"]
ALLOWED = {
    "readable": {"yes", "partly", "no"},
    "category": {"food", "drink", "add-on", "other"},
    "has_choice": {"yes", "no"},
    "confidence": {"high", "medium", "low"},
}


FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE)


def format_right(raw_text: str) -> dict:
    """The raw text must be JSON. Interpretation 18 (2026-10-30): a surrounding code fence is removed first and
    the answer still passes, but it is counted as "fenced" and reported per batch. A sentence in front = wrong."""
    fenced = 0
    try:
        data = json.loads(raw_text)
    except (TypeError, ValueError) as e:
        m = FENCE.match(raw_text or "")
        try:
            data = json.loads(m.group(1)) if m else None
        except ValueError:
            data = None
        if data is None:
            return {"score": 0, "reason": f"not valid JSON as returned: {e}", "fenced": 1 if m else 0}
        fenced = 1
    if not isinstance(data, dict):
        return {"score": 0, "reason": "top level is not an object", "fenced": fenced}
    for f in ("readable", "problems", "items"):
        if f not in data:
            return {"score": 0, "reason": f"missing top-level field '{f}'", "fenced": fenced}
    if data["readable"] not in ALLOWED["readable"]:
        return {"score": 0, "reason": f"readable = {data['readable']!r} not allowed", "fenced": fenced}
    if not isinstance(data["items"], list):
        return {"score": 0, "reason": "items is not a list", "fenced": fenced}
    for k, it in enumerate(data["items"]):
        if not isinstance(it, dict):
            return {"score": 0, "reason": f"item {k} is not an object", "fenced": fenced}
        missing = [f for f in ITEM_FIELDS if f not in it]
        if missing:
            return {"score": 0, "reason": f"item {k} ({it.get('name', '?')!r}) missing {missing}", "fenced": fenced}
        for f in ("category", "has_choice", "confidence"):
            if it[f] not in ALLOWED[f]:
                return {"score": 0, "reason": f"item {k} ({it.get('name', '?')!r}) has {f} = {it[f]!r}", "fenced": fenced}
    return {"score": 1, "reason": "code fence removed (interpretation 18)" if fenced else "", "fenced": fenced}


def parse_leniently(raw_text: str):
    """For every score except format: accept code fences or a sentence in front, take the
    outermost {...}. Returns a dict or None."""
    if raw_text is None:
        return None
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except ValueError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(text[start:end + 1])
        return data if isinstance(data, dict) else None
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# The whole scorecard for one answer to one photo
# ---------------------------------------------------------------------------

def score_answer(expected: dict, hints: dict, raw_text: str, photo: str = "") -> dict:
    """Run every score on one answer. Returns a dict of scores plus the check list."""
    answer = parse_leniently(raw_text)
    fmt = format_right(raw_text if raw_text is not None else "")
    result = {
        "photo": photo,
        "format_right": fmt["score"],          # score 6
        "format_reason": fmt["reason"],
        "fenced": fmt.get("fenced", 0),        # interpretation 18: answer wrapped in a code fence
        "check_list": [],                      # medium/low key items the model disagrees with
    }
    if answer is None:
        # Nothing to compare: every expected item is missing, nothing invented.
        n_exp = len(compared_items(expected.get("items", [])))
        result.update({
            "dishes_found": 0.0, "expected_items": n_exp, "found_items": 0,
            "invented": 0, "cut_off_listed": 0, "garbled": 0, "grouping": 0, "joined_found": 0,
            "prices_right": None, "descriptions_right": None,
            "readable_expected": expected.get("readable"), "readable_model": None,
            "bad_photo_caught": 0 if expected.get("readable") == "partly" else None,
            "false_alarm": 0,
            "tags_right": None, "portion_right": None, "has_choice_right": None, "belongs_to_right": None,
            "confidence_calibration": {},
            "unmatched_expected_names": [it.get("name") for it in compared_items(expected.get("items", []))],
            "invented_names": [], "cut_off_names": [], "garbled_names": [], "grouping_names": [],
        })
        return result

    # Interpretation 12: every item of every category takes part in the name matching (steps 1 and 2);
    # "other" is set aside afterwards, so a note the model called food still pairs with the key's "other" line
    # instead of counting as invented.
    exp_items = [it for it in expected.get("items", []) if isinstance(it, dict)]
    mod_items = [it for it in (answer.get("items", []) if isinstance(answer.get("items"), list) else []) if isinstance(it, dict)]
    uncertain = uncertain_key_items(hints or {})
    fragments = (hints or {}).get("cut_off_lines_left_out", []) or []

    # Step 1: strict name pairing (section 0 of the rules).
    pairing = pair_items(exp_items, mod_items)
    pairs = list(pairing["pairs"])
    unmatched_e, unmatched_m = list(pairing["unmatched_expected"]), list(pairing["unmatched_model"])
    # Step 2 (interpretations 5 and 13): expected name vs the model's name + description.
    joined = pair_by_joined_text(exp_items, mod_items, unmatched_e, unmatched_m)
    pairs += joined
    unmatched_e = [i for i in unmatched_e if i not in {i for i, _, _ in joined}]
    unmatched_m = [j for j in unmatched_m if j not in {j for _, j, _ in joined}]
    # Set "other" aside (interpretation 12): pairs whose expected item is "other", unmatched expected "other"
    # lines, and unmatched model items the model itself marked "other".
    other_pairs = [(i, j, sim) for i, j, sim in pairs if is_other(exp_items[i])]
    pairs = [t for t in pairs if not is_other(exp_items[t[0]])]
    joined = [t for t in joined if not is_other(exp_items[t[0]])]
    set_aside_model = {j for _, j, _ in other_pairs} | {j for j in unmatched_m if is_other(mod_items[j])}
    unmatched_e = [i for i in unmatched_e if not is_other(exp_items[i])]
    unmatched_m = [j for j in unmatched_m if j not in set_aside_model]
    n_exp = sum(1 for it in exp_items if not is_other(it))
    # Interpretation 17: a model item paired with an "other" parent line (a heading such as "Childs Half Sandwich")
    # whose description names two or more of the parent's children counts those children as found. Children are
    # the rows directly under the parent with the same section and price; their names are matched after dropping
    # any word that also appears in the parent's name.
    grouped_found, grouping_names = set(), []
    for i, j, _ in other_pairs:
        parent = exp_items[i]
        pwords = set(clean_name(parent.get("name", "")).split())
        children, k = [], i + 1
        while (k < len(exp_items) and not is_other(exp_items[k]) and exp_items[k].get("section") == parent.get("section")
               and str(exp_items[k].get("price", "")).strip() == str(parent.get("price", "")).strip()):
            children.append(k); k += 1
        if len(children) < 2:
            continue
        desc = clean_name(mod_items[j].get("description", ""))
        hits = []
        for k in children:
            if k not in unmatched_e:
                continue
            phrase = " ".join(w for w in clean_name(exp_items[k].get("name", "")).split() if w not in pwords)
            if phrase and re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", desc):
                hits.append(k)
        if len(hits) >= 2:
            grouped_found.update(hits)
            grouping_names.append(f"parent {parent.get('name')} -> {[exp_items[k].get('name') for k in hits]}")
    unmatched_e = [i for i in unmatched_e if i not in grouped_found]
    # Step 3 (interpretation 6): one model item that holds two or more expected names = a grouping.
    leftovers = []
    for j in unmatched_m:
        hits = [i for i in contained_expected_names(mod_items[j], exp_items, unmatched_e) if i not in grouped_found]
        if len(hits) >= 2:
            grouped_found.update(hits)
            grouping_names.append(f"{mod_items[j].get('name')} -> {[exp_items[i].get('name') for i in hits]}")
        else:
            leftovers.append(j)
    unmatched_e = [i for i in unmatched_e if i not in grouped_found]
    # Step 4 (interpretation 2, applied last): cut-off lines among the leftovers.
    cut_off_names, still_unpaired = [], []
    for j in leftovers:
        name = mod_items[j].get("name", "")
        (cut_off_names if matches_cut_off_fragment(name, fragments) else still_unpaired).append(j)
    # Step 5 (interpretation 7): garbled (50-89 % similar to an unfound expected item) or invented (< 50 %).
    garbled_names, invented_names = [], []
    for j in still_unpaired:
        i, sim = closest_expected(mod_items[j], exp_items, unmatched_e)
        if i is not None and sim >= GARBLED_THRESHOLD:
            level = uncertain.get(clean_name(exp_items[i].get("name", "")))
            garbled_names.append(f"{mod_items[j].get('name')} ~ {exp_items[i].get('name')} ({sim:.0%})")
            if level:   # the model returned this uncertain key item under a different name: for Julius to check
                result["check_list"].append({
                    "photo": photo, "key_confidence": level, "key_name": exp_items[i].get("name"),
                    "key_price": exp_items[i].get("price"), "model_name": mod_items[j].get("name"),
                    "model_price": mod_items[j].get("price"), "reason": f"name differs ({sim:.0%} similar)",
                })
        else:
            invented_names.append(mod_items[j].get("name", ""))

    # --- score 1: dishes found. Plain misses count as misses (interpretation 9). An uncertain key item
    # that the model returned under a different name is pending Julius's check: out of the denominator.
    pending = {row["key_name"] for row in result["check_list"] if row["reason"].startswith("name differs")}
    found = len(pairs) + len(grouped_found)
    unmatched_expected_names = [exp_items[i].get("name") for i in unmatched_e if exp_items[i].get("name") not in pending]
    denominator = n_exp - len(pending)
    result["dishes_found"] = (found / denominator) if denominator else None
    result["expected_items"] = n_exp
    result["other_set_aside"] = len(other_pairs) + sum(1 for j in set_aside_model if j not in {j for _, j, _ in other_pairs})
    result["found_items"] = found
    result["joined_found"] = len(joined)
    result["unmatched_expected_names"] = unmatched_expected_names

    # --- scores 2, 2b and the two new reported counts
    result["invented"] = len(invented_names)
    result["invented_names"] = invented_names
    result["cut_off_listed"] = len(cut_off_names)
    result["cut_off_names"] = [mod_items[j].get("name", "") for j in cut_off_names]
    result["garbled"] = len(garbled_names)
    result["garbled_names"] = garbled_names
    result["grouping"] = len(grouping_names)
    result["grouping_names"] = grouping_names
    pairing = {"pairs": pairs, "unmatched_model": [j for j in leftovers]}   # for scores 3-5 and 10 below

    # --- scores 3, 4, 5 and 10 on the matched pairs
    price_ok = price_n = desc_ok = desc_n = 0
    tags_ok = portion_ok = choice_ok = belongs_ok = belongs_n = 0
    wrong_names = []
    calib = {"high": [0, 0], "medium": [0, 0], "low": [0, 0], "other": [0, 0]}   # [wrong, total]
    for i, j, _ in pairing["pairs"]:
        e, m = exp_items[i], mod_items[j]
        level = uncertain.get(clean_name(e.get("name", "")))
        p_right = price_right(e.get("price"), m.get("price"))
        if not p_right and level:
            result["check_list"].append({
                "photo": photo, "key_confidence": level, "key_name": e.get("name"),
                "key_price": e.get("price"), "model_name": m.get("name"), "model_price": m.get("price"),
                "reason": "price differs",
            })
        else:
            price_n += 1
            price_ok += int(p_right)
            if not p_right:
                wrong_names.append(f"{m.get('name')}: price {m.get('price')!r} vs key {e.get('price')!r}")
        if (e.get("description") or "").strip():
            desc_n += 1
            # Interpretation 15: the ingredient words may sit in the model's name or its description.
            desc_ok += int(description_right(e.get("description"), f"{m.get('name', '')} {m.get('description', '')}"))
        tags_ok += int(tags_right(e.get("tags"), m.get("tags")))
        portion_ok += int(portion_right(e.get("portion"), m.get("portion")))
        choice_ok += int(has_choice_right(e.get("has_choice"), m.get("has_choice")))
        if e.get("category") == "add-on":
            belongs_n += 1
            belongs_ok += int(belongs_to_right(e.get("belongs_to"), m.get("belongs_to")))
        # score 10: wrong unless paired and price right, no exceptions (interpretation 3)
        bucket = m.get("confidence") if m.get("confidence") in calib else "other"
        calib[bucket][1] += 1
        calib[bucket][0] += int(not p_right)
    # unpaired model items (garbled, invented or cut-off) are wrong for score 10 too; grouped items as well (no exceptions)
    for j in [j for j in range(len(mod_items)) if j not in {j for _, j, _ in pairs} and j not in set_aside_model]:
        bucket = mod_items[j].get("confidence") if mod_items[j].get("confidence") in calib else "other"
        calib[bucket][1] += 1
        calib[bucket][0] += 1

    n_pairs = len(pairing["pairs"])
    result["prices_right"] = (price_ok / price_n) if price_n else None
    result["price_wrong_names"] = wrong_names
    result["descriptions_right"] = (desc_ok / desc_n) if desc_n else None
    result["descriptions_checked"] = desc_n
    result["tags_right"] = (tags_ok / n_pairs) if n_pairs else None
    result["portion_right"] = (portion_ok / n_pairs) if n_pairs else None
    result["has_choice_right"] = (choice_ok / n_pairs) if n_pairs else None
    result["belongs_to_right"] = (belongs_ok / belongs_n) if belongs_n else None
    result["confidence_calibration"] = {
        k: {"wrong": v[0], "total": v[1], "share_wrong": (v[0] / v[1]) if v[1] else None}
        for k, v in calib.items() if v[1]
    }

    # --- score 7: bad photos caught / false alarms
    exp_r, mod_r = expected.get("readable"), str(answer.get("readable", "")).lower()
    result["readable_expected"], result["readable_model"] = exp_r, mod_r
    result["problems_model"] = answer.get("problems", "")
    if exp_r == "partly":
        result["bad_photo_caught"] = int(mod_r in ("partly", "no"))
        result["false_alarm"] = 0
    else:
        result["bad_photo_caught"] = None
        result["false_alarm"] = int(mod_r in ("partly", "no"))
    return result


def summarise(scores: list) -> dict:
    """Average the per-answer scores of one run into the model-level numbers of the rules."""
    def avg(key):
        vals = [s[key] for s in scores if s.get(key) is not None]
        return (sum(vals) / len(vals)) if vals else None
    found = [s["dishes_found"] for s in scores if s.get("dishes_found") is not None]
    return {
        "answers": len(scores),
        "dishes_found_avg": avg("dishes_found"),
        "dishes_found_min": min(found) if found else None,
        "invented_total": sum(s.get("invented", 0) for s in scores),
        "cut_off_listed_total": sum(s.get("cut_off_listed", 0) for s in scores),
        "garbled_total": sum(s.get("garbled", 0) for s in scores),
        "grouping_total": sum(s.get("grouping", 0) for s in scores),
        "joined_found_total": sum(s.get("joined_found", 0) for s in scores),
        "prices_right_avg": avg("prices_right"),
        "descriptions_right_avg": avg("descriptions_right"),
        "tags_right_avg": avg("tags_right"),
        "portion_right_avg": avg("portion_right"),
        "has_choice_right_avg": avg("has_choice_right"),
        "belongs_to_right_avg": avg("belongs_to_right"),
        "format_right_avg": avg("format_right"),
        "bad_photos_caught": sum(s["bad_photo_caught"] for s in scores if s.get("bad_photo_caught") is not None),
        "bad_photos_total": sum(1 for s in scores if s.get("bad_photo_caught") is not None),
        "false_alarms": sum(s.get("false_alarm", 0) for s in scores),
        "check_list_items": sum(len(s.get("check_list", [])) for s in scores),
    }
