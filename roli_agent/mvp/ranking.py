"""Phase 3: rank the evaluated dishes of one menu and write the recommendation (Python templates; the only words a tester reads).

Rank (since 2026-11-05, Julius) = the central estimate (low + high) / 2 of the saturated-fat interval per modeled portion, lowest first; the central
cholesterol estimate breaks an effective tie. The low/high ranges stay on display; the midpoint is a practical ranking value, never a verified one.
A dish without an upper bound is never recommended and never gets a midpoint. Each pick carries its support against the other ranked dishes below it in the list: `well_supported` when every pairwise
verdict against them is well supported, `tentative` when at least one is tentative and none overlap, `close_call` when it overlaps at least one.

Wording (Julius, 2026-11-04): when coverage is incomplete the text says "Among the dishes I could estimate", never "lowest on the menu"; an
overlapping or assumption-dependent order is called a toss-up or tentative; a specialty ingredient that supplies most of the top pick's
cholesterol upper end (bottarga) is named; at most 80 words, texting style.
"""

from __future__ import annotations

import re
from decimal import Decimal

from ..recipes.models import DishComparison, DishInterval
from .models import RankedDish, Unranked

WORD_LIMIT = 80
# 12.18 (Julius, 2026-11-07), generalising the snack-bowl rule of 12.14.4: these families never enter the top three. Each group present gets one line after the ranking,
# "Lightest side: ..." (soup, dip, dessert, snack alike) or "Kids: ..."; children's dishes are listed only when the menu has a children's section. The lines are the first to go
# under the word limit, the last group first. Mains, starters, salads, pizza, pasta, burgers, sandwiches, wraps, tacos, burritos, quesadillas and breakfast plates stay in the ranking.
APART_GROUPS = {"fried_potato_side": "side", "side_salad": "side", "side_vegetable": "side", "side_rice": "side", "side_bread": "side", "soup": "soup", "dip": "dip",
                "dessert": "dessert", "snack_bowl": "snack", "kids_dish": "kids"}
APART_ORDER = ("side", "soup", "dip", "dessert", "snack", "kids")
NOT_RESTAURANT = "Modeled from published recipes and typical portions, not this kitchen's numbers."
DRIVER_SHARE = Decimal("0.30")                  # one ingredient must supply at least this share of the upper end to be named
HIGH_CHOLESTEROL_MG = Decimal("150")            # a pick whose cholesterol LOWER bound is at least this per plate is called high in cholesterol
VERY_HIGH_CHOLESTEROL_MG = Decimal("300")       # a pick whose UPPER bound reaches this is said to "carry up to" it (a daily reference amount)


def _dec(v) -> Decimal | None:
    return None if v is None else Decimal(str(v))


# -- the cholesterol driver --------------------------------------------------------------------------------------------------

_EXTERNAL = re.compile(r"^(?P<name>[^:]+): \+(?P<amt>[\d.]+(?:e[+-]?\d+)?) (?:g|mg):", re.I)
_ASSUMED = re.compile(r"^(?:[^:]+: )?assumed (?P<name>.+?): [\d.]+ g -> (?P<amt>[\d.]+(?:e[+-]?\d+)?) per portion", re.I)


def cholesterol_driver(iv: DishInterval | None) -> tuple[str | None, Decimal | None]:
    """The single named line that adds most to the dish's cholesterol upper end, when it is at least DRIVER_SHARE of the upper bound
    (or of the range width): external-evidence bounds (bottarga) and assumed weights rows are read from the interval's own labels."""
    if iv is None or iv.high is None or iv.high <= 0:
        return None, None
    top = sorted((s for s in iv.scenarios if s.high is not None), key=lambda s: -s.high)[:1]
    if not top:
        return None, None
    s = top[0]
    found: list[tuple[Decimal, str, str]] = []
    for src in s.external_bound_sources:
        m = _EXTERNAL.match(src)
        if m:
            found.append((Decimal(m.group("amt")), m.group("name").strip(), "external evidence"))
    for d in s.drivers:
        m = _ASSUMED.match(d)
        if m:
            found.append((Decimal(m.group("amt")), m.group("name").strip(), "assumed amount"))
    if not found:
        return None, None
    amt, name, kind = max(found, key=lambda t: t[0])
    width = iv.high - iv.low if iv.low is not None else iv.high
    base = max(width, Decimal(0)) or iv.high
    share = amt / iv.high
    if share >= DRIVER_SHARE or (base > 0 and amt / base >= Decimal("0.5")):
        return f"{name} ({kind})", share.quantize(Decimal("0.01"))
    return None, None


# -- ranking --------------------------------------------------------------------------------------------------------------------


def rank_dishes(comparison: DishComparison, names: dict[str, str]) -> tuple[list[RankedDish], list[Unranked]]:
    sat = comparison.intervals.get("saturated_fat_g", {})
    chol = comparison.intervals.get("cholesterol_mg", {})
    bounded = [d for d, iv in sat.items() if iv.bounded and iv.high is not None]
    unranked = [Unranked(key=d, name=names.get(d, d), reason=_unranked_reason(iv)) for d, iv in sat.items() if not (iv.bounded and iv.high is not None)]
    order, tie_broken = _midpoint_order(bounded, sat, chol)
    verdict = {}
    for p in comparison.pairwise:
        if p.nutrient == "saturated_fat_g":
            verdict[(p.dish_a, p.dish_b)] = p
            verdict[(p.dish_b, p.dish_a)] = p
    ranked: list[RankedDish] = []
    for i, d in enumerate(order):
        below = order[i + 1:]
        well = tent = over = 0
        reasons, caveats, overlaps_with, tentative_vs = [], list(sat[d].caveats), [], []
        for other in below:
            p = verdict.get((d, other))
            if p is None:
                continue
            if p.verdict == "well_supported" and p.lower == d:
                well += 1
            elif p.verdict == "tentative" and p.lower == d:
                tent += 1
                tentative_vs.append(names.get(other, other))
                reasons.append(f"tentative vs {names.get(other, other)}: {'; '.join(p.tentative_because)[:200]}")
            elif p.verdict == "overlapping":
                over += 1
                overlaps_with.append(names.get(other, other))
                reasons.append(f"overlaps {names.get(other, other)}: {p.reason[:120]}")
            else:
                reasons.append(f"vs {names.get(other, other)}: {p.verdict} ({p.reason[:100]})")
        support = "close_call" if over else ("tentative" if tent else "well_supported")
        if len(order) == 1:
            support = "only_estimate"                       # nothing to compare with: not a supported ranking, just the one estimate
        c = chol.get(d)
        driver, share = cholesterol_driver(c)
        ranked.append(RankedDish(rank=i + 1, key=d, name=names.get(d, d), saturated_fat_low=sat[d].low, saturated_fat_high=sat[d].high,
                                 saturated_fat_mid=_mid(sat[d]), cholesterol_mid=_mid(c) if c else None, tie_broken_by_cholesterol=d in tie_broken,
                                 cholesterol_low=c.low if c else None, cholesterol_high=c.high if c else None, support=support,
                                 band_low=sat[d].band_low, band_high=sat[d].band_high, cholesterol_band_low=c.band_low if c else None, cholesterol_band_high=c.band_high if c else None,
                                 plate_source=sat[d].plate_source, set_aside=list(sat[d].set_aside),
                                 beats_well_supported=well, beats_tentative=tent, overlaps=over, overlaps_with=overlaps_with, tentative_vs=tentative_vs,
                                 cholesterol_driver=driver, cholesterol_driver_share=share, reasons=reasons, caveats=caveats, drivers=list(sat[d].drivers)[:6]))
    return ranked, unranked


def _mid(iv: DishInterval | None) -> Decimal | None:
    """The practical central estimate: since 3K the band's median when the interval carries one, else (low + high) / 2 of a bounded interval; None when the
    interval has no upper bound. Never a verified value and never computed for an incomplete subtotal (an unbounded dish is not ranked at all)."""
    if iv is None or iv.low is None or iv.high is None:
        return None
    if iv.band_mid is not None:
        return iv.band_mid
    return (iv.low + iv.high) / 2


TIE_ABS_G = Decimal("0.25")                     # two central saturated-fat estimates within this many grams, or within TIE_REL of the larger, are "effectively tied"
TIE_REL = Decimal("0.05")


def _tied(a: Decimal, b: Decimal) -> bool:
    return abs(a - b) <= max(TIE_ABS_G, TIE_REL * max(a, b))


def _midpoint_order(bounded: list[str], sat: dict[str, DishInterval], chol: dict[str, DishInterval]) -> tuple[list[str], set[str]]:
    """Lowest central saturated fat first (Julius, 2026-11-05); where two neighbours are effectively tied on saturated fat, the lower central
    cholesterol goes first. Dishes without an upper bound never enter (they are listed unranked with the reason)."""
    big = Decimal("1e9")
    order = sorted(bounded, key=lambda d: (_mid(sat[d]), sat[d].high, _mid(chol[d]) if d in chol and _mid(chol[d]) is not None else big))
    tie_broken: set[str] = set()
    changed = True
    while changed:                                # a few adjacent swaps at most: the lists are short
        changed = False
        for i in range(len(order) - 1):
            a, b = order[i], order[i + 1]
            ca, cb = (_mid(chol[x]) if x in chol and _mid(chol[x]) is not None else big for x in (a, b))
            if _tied(_mid(sat[a]), _mid(sat[b])) and cb < ca:
                order[i], order[i + 1] = b, a
                tie_broken |= {a, b}
                changed = True
    return order, tie_broken


def _unranked_reason(iv: DishInterval) -> str:
    if iv.low is None:
        return "no recipe of this dish could be portioned" + (f" ({iv.caveats[0]})" if iv.caveats else "")
    opens = [c for c in iv.caveats if "no upper bound" in c]
    return "the estimate has no upper bound: " + (opens[0][:160] if opens else "an ingredient could not be bounded")


# -- the words ------------------------------------------------------------------------------------------------------------------


def _g(v: Decimal) -> str:
    v = Decimal(v)
    return f"{v:.1f}" if v < 10 else f"{v:.0f}"


def _mg(v: Decimal) -> str:
    return f"{Decimal(v):.0f}"


def _title(name: str) -> str:
    name = re.sub(r"\s+", " ", name.strip())
    if not name.isupper():
        return name
    return re.sub(r"[A-Za-z]+(?:['’][A-Za-z]+)*", lambda m: m.group(0)[0] + m.group(0)[1:].lower(), name)      # "TODAY'S RICOTTA" -> "Today's Ricotta", never "Today'S"


def _short(name: str, limit: int = 6) -> str:
    """A long menu name ("Wood fire-roasted tomato and eggplant soup with mint, urfa pepper, and charmoula") cut at the first comma, colon,
    semicolon or 'with', then to `limit` words."""
    name = re.sub(r"[*†‡]+", "", name)                                   # menu footnote marks ("Zuni Caesar salad*")
    head = re.split(r",|;|:|\bwith\b|\(", name, maxsplit=1)[0].strip()
    if len(head.split()) < 2 and len(name.split()) > 1:
        head = " ".join(name.split()[:4])                                 # "Spaghetti with Gulf shrimp, ...", "Watermelon, fetta, mint almond, ...": a one-word head says too little
        return head.rstrip(",;: ")
    words = head.split()
    return (" ".join(words[:limit]) if len(words) > limit else head).rstrip(",;: ")


def _sat_range(p: RankedDish) -> tuple[Decimal, Decimal, bool]:
    """(low, high, banded): the band when the dish carries one (3K: "most plates"), else the extremes."""
    if p.band_low is not None and p.band_high is not None:
        return p.band_low, p.band_high, True
    return p.saturated_fat_low, p.saturated_fat_high, False


def _chol_range(p: RankedDish) -> tuple[Decimal | None, Decimal | None]:
    if p.cholesterol_band_low is not None and p.cholesterol_band_high is not None:
        return p.cholesterol_band_low, p.cholesterol_band_high
    return p.cholesterol_low, p.cholesterol_high


def _driver_words(driver: str) -> str:
    name = driver.rsplit(" (", 1)[0]
    name = name.lower() if name.isupper() else name                         # a menu word in capitals ("FETTA LEMON PANGRATTA") reads as text
    kind = "an estimate" if "external" in driver else "an assumed amount"
    return f"{name} ({kind})"


def frying_fat_line(name: str, choice_ranges: dict[str, dict], fat_bands: dict[str, dict] | None = None) -> str | None:
    """12.10.9: the line of a dish whose range spans the card's frying-fat choices. Every figure and choice name comes from the computed ranges; None when one choice
    applies. 3K: when the band sampler gives a per-fat band (`fat_bands`, {label: {"low", "mid", "high"}}) the line reads it ("most plates")."""
    sat = sorted(((Decimal(r["saturated_fat_g"]["high"]), Decimal(r["saturated_fat_g"]["low"]), label) for label, r in choice_ranges.items()))
    if len(sat) < 2:
        return None
    (lean_high, lean_low, lean), (top, _, fat) = sat[0], sat[-1]
    if fat_bands and lean in fat_bands and fat in fat_bands:
        b_lean, b_fat = fat_bands[lean], fat_bands[fat]
        return (f"{_title(_short(name))}: most plates about {_g(Decimal(str(b_lean['low'])))}-{_g(Decimal(str(b_lean['high'])))} g saturated fat if fried in {lean}, "
                f"up to about {_g(Decimal(str(b_fat['high'])))} g in {fat}. Ask what they fry in.")
    return f"{_title(_short(name))}: about {_g(lean_low)}-{_g(lean_high)} g saturated fat if fried in {lean}, up to about {_g(top)} g in {fat}. Ask what they fry in."


def apart_lines(ranked: list[RankedDish], *, kids_section: bool) -> list[str]:
    """12.18: one line per non-main group present, naming its lightest dish (the ranking is by midpoint, so the group's first row is the lightest). Kids only with a children's section."""
    lines = []
    for group in APART_ORDER:
        rows = [r for r in ranked if (r.listed_apart or ("snack" if r.snack else None)) == group]
        if not rows or (group == "kids" and not kids_section):
            continue
        best = rows[0]
        label = "Kids" if group == "kids" else f"Lightest {group}"
        lo, hi, banded = _sat_range(best)
        lines.append(f"{label}: {_title(_short(best.name))}, {'most plates ' if banded else ''}{_g(lo)}-{_g(hi)} g. ")
    return lines


def unranked_causes(unranked: list[Unranked], kinds: dict[str, str]) -> list[str]:
    """3I: why nothing ranked, counted from the unranked reasons: dishes no recipe could be sized for (with their kinds, from `kinds` by dish key),
    estimates without an upper bound, estimates that disagree with published figures, dishes USDA could not be asked about."""
    unsized = [u for u in unranked if u.reason.startswith("no recipe of this dish could be portioned")]
    open_top = [u for u in unranked if u.reason.startswith("the estimate has no upper bound")]
    disagree = [u for u in unranked if "disagrees with published figures" in u.reason]
    rest = [u for u in unranked if u not in unsized and u not in open_top and u not in disagree]
    out = []
    if unsized:
        names = sorted({kinds.get(u.key, "") for u in unsized} - {""})
        out.append(f"{len(unsized)} could not be sized from a recipe" + (f" ({', '.join(names)})" if names else ""))
    if open_top:
        out.append(f"{len(open_top)} had no defensible upper bound")
    if disagree:
        out.append(f"{len(disagree)} disagree{'s' if len(disagree) == 1 else ''} with published figures for that kind of dish")
    if rest:
        out.append(f"{len(rest)} could not be looked up")
    return out


def recommendation_text(ranked: list[RankedDish], n_evaluated: int, n_dishes_considered: int, n_unestimated: int, *, n_skipped: int = 0,
                        n_stopped: int = 0, unsized_kinds: list[str] | None = None, n_food: int | None = None, causes: list[str] | None = None,
                        kids_section: bool = False) -> tuple[str, int]:
    """At most WORD_LIMIT words. Lowest saturated fat first; how certain the order is; cholesterol for the top pick with its driver when one
    ingredient supplies it; what the figures are; what could not be estimated or was not tried. 12.16.4: when nothing was tried, the reply says
    Roli cannot size the dishes on this menu yet and names their kinds (`unsized_kinds`). When dishes were tried and none ranked, `causes` (from
    `unranked_causes`) says why; without it the older "no defensible upper bound" wording stands. 12.18: dishes of the non-main families (`listed_apart`) never enter
    the top three; each group present gets one "Lightest ..." line after the ranking (`apart_lines`), children's dishes only when `kids_section` is True."""
    if not ranked:
        tried = n_dishes_considered - n_skipped
        if n_dishes_considered == 0:                 # no dish had a portion rule: nothing was tried, and nothing was held back by the cap or a reserve
            if n_food == 0:
                return _cap(f"I found no food dishes on this menu, only drinks or extras. {NOT_RESTAURANT}")
            kinds = ", ".join(unsized_kinds or [])
            return _cap(f"I can't size the dishes on this menu yet{': ' + kinds if kinds else ''}. {NOT_RESTAURANT}")
        text = (f"I couldn't estimate any of the {tried} dishes I tried on this menu: {'; '.join(causes) if causes else 'no estimate had a defensible upper bound'}"
                + (f", and {n_skipped} dishes were not tried" if n_skipped else "") + f". {NOT_RESTAURANT}")
        return _cap(text)
    plates = [r for r in ranked if not r.snack and not r.listed_apart]
    apart = apart_lines(ranked, kids_section=kids_section)
    if not plates:
        text = f"I couldn't estimate a main dish on this menu ({n_dishes_considered - n_skipped} tried). " + "".join(apart) + NOT_RESTAURANT
        while len(text.split()) > WORD_LIMIT and apart:
            apart.pop()
            text = f"I couldn't estimate a main dish on this menu ({n_dishes_considered - n_skipped} tried). " + "".join(apart) + NOT_RESTAURANT
        return _cap(text)
    picks = plates[:3]
    complete = n_unestimated == 0 and n_skipped == 0 and n_stopped == 0
    n_tried = n_dishes_considered - n_skipped
    if complete:
        lead = "Lowest saturated fat on this menu, by my estimate: "
    else:
        detail = []
        if n_unestimated:
            detail.append(f"{n_unestimated} had no usable estimate")
        if n_skipped:
            detail.append(f"{n_skipped} not tried")
        n_r = len(ranked)
        lead = f"Among the {n_r} dish{'es' if n_r != 1 else ''} I could estimate ({n_tried} tried; {'; '.join(detail)}), lowest saturated fat first: "
    parts = []
    for k, p in enumerate(picks):
        lo, hi, banded = _sat_range(p)
        most = "most plates " if banded else ""                    # 3K (12.20): the band is what a tester reads; the extremes stay on the diagnostics page
        rng = f"{most}about {_g(lo)}-{_g(hi)} g saturated fat per plate" if k == 0 else f"{most}{_g(lo)}-{_g(hi)} g"
        parts.append(f"{k + 1}) {_title(_short(p.name))}" if p.fat_line else f"{k + 1}) {_title(_short(p.name))}, {rng}")     # 12.10.9: its own line says the figures
    fat_lines = " ".join(p.fat_line for p in picks if p.fat_line)
    core = lead + "; ".join(parts) + ". " + (fat_lines + " " if fat_lines else "")
    certainty = _certainty_sentence(picks, plates)
    top = picks[0]
    chol_sentence = ""
    c_lo, c_hi = _chol_range(top)
    if c_hi is not None:
        lo, hi = _mg(c_lo), _mg(c_hi)
        if hi == "0":
            chol_sentence = f"{_title(_short(top.name))} has no cholesterol in its ingredients. "
        else:
            chol_sentence = f"{_title(_short(top.name))} cholesterol about {hi if lo == hi else f'{lo}-{hi}'} mg"
            chol_sentence += f", the top end from {_driver_words(top.cholesterol_driver)}. " if top.cholesterol_driver else ". "
    # a pick that is low in saturated fat but high in cholesterol (shrimp, egg yolk, roe) is said so: cholesterol is the secondary criterion, never hidden
    notice = ""
    for p in picks[1:]:
        p_lo, p_hi = _chol_range(p)
        if p_lo is not None and p_lo >= HIGH_CHOLESTEROL_MG:
            notice = f"{_title(_short(p.name))} is high in cholesterol, about {_mg(p_lo)}-{_mg(p_hi)} mg. "
            break
        if p_hi is not None and p_hi >= VERY_HIGH_CHOLESTEROL_MG:
            notice = f"{_title(_short(p.name))} may carry up to {_mg(p_hi)} mg cholesterol. "
            break
    # the word limit never cuts the disclaimer: the optional sentences go first (12.18: the listed-apart lines, the last group first; then the top pick's cholesterol,
    # the certainty sentence, the notice)
    optional = [chol_sentence, certainty, notice]
    while len((core + "".join(optional) + "".join(apart) + NOT_RESTAURANT).split()) > WORD_LIMIT and (apart or any(optional)):
        if apart:
            apart.pop()
            continue
        for i in (0, 1, 2):
            if optional[i]:
                optional[i] = ""
                break
    text = core + optional[1] + optional[0] + optional[2] + "".join(apart) + NOT_RESTAURANT
    if fat_lines:                                                       # 12.10.9: never cut, and neither is the disclaimer after it; only the optional sentences give way
        text = re.sub(r"\s+", " ", text).strip()
        return text, len(text.split())
    return _cap(text)


def _certainty_sentence(picks: list[RankedDish], ranked: list[RankedDish]) -> str:
    names = {p.name for p in picks}
    pick_titles = {p.name: _title(_short(p.name)) for p in picks}
    if len(ranked) == 1:
        return "It's the only dish I could estimate, so this is one figure, not a ranking. "
    overlapping = [(p, o) for p in picks for o in p.overlaps_with if o in names]
    if overlapping:
        p, o = overlapping[0]
        if len(overlapping) > 1 or len(picks) == 2:
            return "These ranges overlap, so treat the order as a toss-up. "
        return f"{pick_titles[p.name]} and {pick_titles.get(o, _title(_short(o)))} overlap, so treat that order as a toss-up. "
    if any(p.overlaps_with for p in picks):
        return "Each overlaps a dish further down the list, so the order below these is less certain. "
    if any(p.support == "tentative" for p in picks):
        band_only = [r for p in picks for r in p.reasons if r.startswith("tentative vs")]
        if band_only and all("most plates apart" in r for r in band_only):
            return "Most plates fall in this order; the full ranges still overlap, so it is likely, not certain. "     # 3K (12.20): bands apart, extremes overlapping
        return "The order is tentative: it leans on assumed amounts and modeled portions. "
    return ""


def _cap(text: str, drop_first: str = "") -> tuple[str, int]:
    words = text.split()
    if len(words) > WORD_LIMIT and drop_first:
        text = text.replace(drop_first, "", 1)
        words = text.split()
    if len(words) > WORD_LIMIT:
        words = words[:WORD_LIMIT - 1] + ["..."]
        text = " ".join(words)
    text = re.sub(r"\s+", " ", text).strip()
    return text, len(text.split())
