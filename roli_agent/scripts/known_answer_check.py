"""Known-answer check: Roli against dishes whose saturated fat per plate the chain itself publishes (Julius, 2026-11-08).

    .venv/bin/python -m roli_agent.scripts.known_answer_check build  --n 50 --date 2026-11-08      # choose the dishes, write the typed menus
    .venv/bin/python -m roli_agent.scripts.known_answer_check run    --date 2026-11-08 [--daily-usd 7.00 --daily-credits 450]
    .venv/bin/python -m roli_agent.scripts.known_answer_check report --date 2026-11-08

build: a spread sample of dishes from data/chain_sheets/*.csv (one version per dish: no gluten-free, vegan, large/small or dine-out duplicates; Pizza Express pizzas
from its Classic size only; no family without a sourced plate row), typed as menus of at most 12 dishes per chain, dish NAME and SECTION only, as the sheet prints
them, with the sheet's own notes in brackets removed ("Salmon sashimi (excl. dressing)" -> "Salmon sashimi"). Julius's choice of 2026-11-08: names only, no
descriptions from the chains' websites. Written to data/known_answer_menus/<date>.json with the published figures kept apart from the menus Roli sees.

run: each typed menu goes through the normal MenuRunner in place of a photo reading; nothing else changes. While a chain is tested, that chain's own items are
removed from the plate-weight samples Roli draws from (leave one chain out). Spending goes through the budget and the ledger; the daily caps can be raised for
this run only by the options above (Julius's permission of 2026-11-08); the per-menu caps stay.

report: per dish, the published figure against Roli's band (10th-90th percentile of simulated plates) and full range; how far the middle is off and in which
direction; per chain, whether Roli's order agrees with the published order (Spearman rank correlation) and where Roli's lightest pick stands. Flagged dishes are
scored too. Families whose plate size rests mostly on these same sheets are reported apart. Writes eval/known_answer_check_<date>.md and .csv.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
import statistics
import sys
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

from roli_agent.config import ROOT
from roli_agent.recipes.portions import PortionRules

SHEETS = ROOT / "data" / "chain_sheets"
MENUS = ROOT / "data" / "known_answer_menus"
EVAL = ROOT / "roli_agent" / "eval"
RUNS = ROOT / "roli_agent" / "runs"
ALLOCATION = {"Pizza Express": 12, "Bonefish Grill": 8, "Zizzi": 8, "Vapiano": 8, "Carrabba's Italian Grill": 6, "Prezzo": 5, "Wasabi": 3}
MAX_PER_MENU = 12
SKIP_NAME = re.compile(r"\b(GF|gluten[- ]free|vegan|dine out|large|small|piccolo|1 portion|regional)\b", re.I)
NOTE = re.compile(r"\s*\([^)]*\)")
# families whose plate size rests mostly on these same chain sheets: reported apart, not in the headline
DEPENDENT = {"crudo_starter": "PR03 is built from Wasabi and YO! Sushi sashimi weights", "tomato_salad_starter": "PR05 is built from Pizza Express, Vapiano and Zizzi caprese weights"}
DEPENDENT_BY_CHAIN = {("Pizza Express", "pizza_neapolitan"): "PR01's approved range is Pizza Express pizzas plus the AVPN dough ball",
                      ("Bonefish Grill", "fish_main"): "PR02's chain figure rests on Bonefish's stated fish weights"}


def sheet_rows() -> list[dict]:
    rows = []
    for f in sorted(SHEETS.glob("*.csv")):
        for r in csv.DictReader(f.open(encoding="utf-8")):
            r["_file"] = f.name
            rows.append(r)
    return rows


def dependent_reason(chain: str, family: str) -> str:
    return DEPENDENT.get(family) or DEPENDENT_BY_CHAIN.get((chain, family), "")


def build(n: int, date: str, seed: int = 0) -> Path:
    rules = PortionRules.load()
    sourced = {r.dish_type for r in rules.rows if not r.review_status.startswith("unsourced")}
    by_chain: dict[str, list[dict]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    for r in sheet_rows():
        chain, fam = r["business"], r["family"]
        if chain not in ALLOCATION or not (r.get("sat_fat_g_per_plate") or "").strip() or fam not in sourced:
            continue
        if SKIP_NAME.search(r["item"]) or SKIP_NAME.search(r.get("section") or ""):
            continue
        if chain == "Pizza Express" and fam == "pizza_neapolitan" and r["section"] != "Pizza Classic":
            continue
        name = NOTE.sub("", r["item"]).strip(" ,-")
        if (chain, name.lower()) in seen:
            continue
        seen.add((chain, name.lower()))
        by_chain[chain].append(dict(r, _name=name))
    rng = random.Random(seed)
    chosen: list[dict] = []
    scale = n / sum(ALLOCATION.values())
    for chain, k in ALLOCATION.items():
        want = max(1, round(k * scale))
        fams: dict[str, list[dict]] = defaultdict(list)
        for r in by_chain[chain]:
            fams[r["family"]].append(r)
        for v in fams.values():
            rng.shuffle(v)
        order = sorted(fams, key=lambda f: (-len(fams[f]), f))
        picked: list[dict] = []
        while len(picked) < want and any(fams.values()):                 # round-robin across the chain's families, so the sample spreads over kinds of dish
            for f in order:
                if fams[f] and len(picked) < want:
                    picked.append(fams[f].pop())
        chosen += picked
    menus = []
    for chain in ALLOCATION:
        items = [r for r in chosen if r["business"] == chain]
        for m in range(0, len(items), MAX_PER_MENU):
            part = items[m:m + MAX_PER_MENU]
            menus.append({"menu_id": f"{re.sub(r'[^a-z]+', '_', chain.lower()).strip('_')}_{m // MAX_PER_MENU + 1}", "chain": chain,
                          "menu": {"readable": "yes", "problems": "", "items": [{"section": r.get("section") or "", "category": "food", "name": r["_name"], "description": "",
                                                                                  "price": "", "tags": [], "belongs_to": ""} for r in part]},
                          "answers": [{"index": i, "sheet_item": r["item"], "family": r["family"], "sat_fat_g_per_plate": r["sat_fat_g_per_plate"],
                                       "cholesterol_mg_per_plate": r.get("cholesterol_mg_per_plate") or "", "serving_g": r.get("serving_g") or "", "source_file": r["_file"],
                                       "url": r.get("url") or "", "read_on": r.get("read_on") or "", "dependent": dependent_reason(chain, r["family"])} for i, r in enumerate(part)]})
    MENUS.mkdir(parents=True, exist_ok=True)
    out = MENUS / f"{date}.json"
    out.write_text(json.dumps({"date": date, "seed": seed, "n": len(chosen), "rule": "dish name and section only, as the chain's nutrition sheet prints them; the sheet's bracketed notes removed; "
                                                                                      "no descriptions (Julius, 2026-11-08)", "menus": menus}, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(chosen)} dishes in {len(menus)} menus -> {out}")
    for m in menus:
        print(" ", m["menu_id"], [(i["name"], a["family"], a["sat_fat_g_per_plate"]) for i, a in zip(m["menu"]["items"], m["answers"])])
    return out


def run(date: str, daily_usd: str | None, daily_credits: int | None) -> None:
    load_dotenv(ROOT / ".env")
    from roli_agent.mvp.menu_run import MenuRunner
    from roli_agent.mvp.models import MvpConfig
    from roli_agent.recipes.plate_weights import PlateWeights
    data = json.loads((MENUS / f"{date}.json").read_text(encoding="utf-8"))
    cfg = dict(max_dishes=30)
    if daily_usd:
        cfg["daily_budget_usd"] = Decimal(daily_usd)
    if daily_credits:
        cfg["daily_search_credits"] = daily_credits
    menus = {m["menu_id"]: m["menu"] for m in data["menus"]}
    runner = MenuRunner(MvpConfig(**cfg), read_menu=lambda path: menus[Path(path).stem])
    all_weights = PlateWeights.load()
    ids = {}
    for m in data["menus"]:
        runner.plate_weights = PlateWeights([r for r in all_weights.rows if r.get("business") != m["chain"]])      # leave the tested chain out of the plate samples
        st = runner.usda_status()
        print(f"{m['menu_id']}: USDA remaining {st.get('remaining')}", flush=True)
        r = runner.run(f"known_answer/{m['menu_id']}.menu")
        ids[m["menu_id"]] = r.run_id
        print(f"  {r.run_id} {r.status} {r.timings.get('total')} s ${r.spend.get('model_usd_total')} {r.spend.get('search_credits')} credits; interruptions {r.spend.get('interruptions')}", flush=True)
    data["runs"] = ids
    data["run_settings"] = {"daily_budget_usd": daily_usd, "daily_search_credits": daily_credits, "per_menu": "unchanged ($0.50, 30 credits)", "leave_one_chain_out": True}
    (MENUS / f"{date}.json").write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")


def spearman(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3:
        return None
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    rx, ry = ranks(xs), ranks(ys)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else None


def report(date: str) -> None:
    data = json.loads((MENUS / f"{date}.json").read_text(encoding="utf-8"))
    rows = []
    for m in data["menus"]:
        run = json.loads((RUNS / data["runs"][m["menu_id"]] / "run.json").read_text(encoding="utf-8"))
        dishes = {d["menu_index"]: d for d in run["dishes"]}
        ranked = {x["key"] for x in run["ranking"]}
        for item, ans in zip(m["menu"]["items"], m["answers"]):
            d = dishes.get(ans["index"]) or {}
            iv = (d.get("intervals") or {}).get("saturated_fat_g") or {}
            ch = (d.get("intervals") or {}).get("cholesterol_mg") or {}
            pub = float(ans["sat_fat_g_per_plate"])
            f = lambda v: float(v) if v not in (None, "") else None
            lo, hi, blo, bmid, bhi = f(iv.get("low")), f(iv.get("high")), f(iv.get("band_low")), f(iv.get("band_mid")), f(iv.get("band_high"))
            estimated = hi is not None and lo is not None
            row = {"chain": m["chain"], "menu": m["menu_id"], "dish": item["name"], "family": ans["family"], "roli_family": d.get("dish_type") or "", "status": d.get("status") or "not read",
                   "reason": (d.get("reason") or "")[:120], "ranked": d.get("key") in ranked, "published": pub, "estimated": estimated, "low": lo, "high": hi, "band_low": blo,
                   "band_mid": bmid, "band_high": bhi, "dependent": ans["dependent"], "flagged": d.get("status") == "flagged",
                   "in_band": estimated and blo is not None and blo <= pub <= bhi, "in_range": estimated and lo <= pub <= hi,
                   "ratio": (bmid / pub) if estimated and bmid is not None and pub > 0 else None, "published_chol": f(ans.get("cholesterol_mg_per_plate")),
                   "chol_low": f(ch.get("low")), "chol_high": f(ch.get("high")), "chol_band_low": f(ch.get("band_low")), "chol_band_high": f(ch.get("band_high")), "run": data["runs"][m["menu_id"]]}
            if row["published_chol"] is not None and row["chol_high"] is not None:
                row["chol_in_band"] = row["chol_band_low"] is not None and row["chol_band_low"] <= row["published_chol"] <= row["chol_band_high"]
                row["chol_in_range"] = row["chol_low"] <= row["published_chol"] <= row["chol_high"]
            rows.append(row)
    EVAL.mkdir(exist_ok=True)
    fields = list(rows[0].keys()) + [k for k in ("chol_in_band", "chol_in_range") if k not in rows[0]]
    with (EVAL / f"known_answer_check_{date}.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    est = [r for r in rows if r["estimated"]]
    head = [r for r in est if not r["dependent"]]
    dep = [r for r in est if r["dependent"]]
    pct = lambda a, b: f"{a} of {b} ({100 * a / b:.0f} %)" if b else "none"
    def block(rs):
        ratios = [r["ratio"] for r in rs if r["ratio"]]
        logs = [math.log(x) for x in ratios]
        over = sum(1 for x in ratios if x > 1)
        return {"n": len(rs), "in_band": sum(r["in_band"] for r in rs), "in_range": sum(r["in_range"] for r in rs),
                "median_ratio": math.exp(statistics.median(logs)) if logs else None, "typical_miss": math.exp(statistics.median(abs(x) for x in logs)) if logs else None,
                "over": over, "under": len(ratios) - over, "within_2x": sum(1 for x in ratios if 0.5 <= x <= 2)}
    L = [f"# Known-answer check, {date}", "", f"{len(rows)} dishes from {len(set(r['chain'] for r in rows))} chains, typed as menus of dish names and sections only (no descriptions), run through the normal "
         f"pipeline with the tested chain's own items left out of the plate-weight samples. Published figure = the chain's own saturated fat per plate (`data/chain_sheets/`). "
         f"Run settings: {data.get('run_settings')}.", "",
         f"Roli gave an estimate for {pct(len(est), len(rows))} of the dishes. Of the {len(head)} independent estimates (families whose plate size does not rest on these sheets):", ""]
    b = block(head)
    L += ["| measure | result |", "|---|---|", f"| published figure inside Roli's band (\"most plates\", meant to hold 8 in 10) | {pct(b['in_band'], b['n'])} |",
          f"| inside Roli's full range | {pct(b['in_range'], b['n'])} |", f"| Roli's middle within a factor of 2 of the published figure | {pct(b['within_2x'], b['n'])} |",
          f"| typical size of the miss (median, as a factor) | {b['typical_miss']:.2f}x |" if b["typical_miss"] else "| typical miss | none |",
          f"| direction: Roli's middle above / below the published figure | {b['over']} above, {b['under']} below; median ratio {b['median_ratio']:.2f} |" if b["median_ratio"] else "| direction | none |", ""]
    bd = block(dep)
    L += [f"Dependent families, reported apart ({len(dep)} dishes): band {pct(bd['in_band'], bd['n'])}, full range {pct(bd['in_range'], bd['n'])}, within 2x {pct(bd['within_2x'], bd['n'])}.", ""]
    L += ["## By chain", "", "| chain | dishes | estimated | in band | in range | within 2x | order agreement (Spearman) | Roli's lightest pick: published rank |", "|---|---|---|---|---|---|---|---|"]
    for chain in dict.fromkeys(r["chain"] for r in rows):
        rs = [r for r in rows if r["chain"] == chain]
        es = [r for r in rs if r["estimated"] and r["band_mid"] is not None]
        rho = spearman([r["band_mid"] for r in es], [r["published"] for r in es])
        pick = ""
        if es:
            top = min(es, key=lambda r: r["band_mid"])
            rank = 1 + sum(1 for r in es if r["published"] < top["published"])
            pick = f"{top['dish']} ({top['published']} g): {rank} of {len(es)}"
        bb = block([r for r in rs if r["estimated"]])
        L.append(f"| {chain} | {len(rs)} | {len([r for r in rs if r['estimated']])} | {bb['in_band']} | {bb['in_range']} | {bb['within_2x']} | {f'{rho:.2f}' if rho is not None else 'n/a'} | {pick} |")
    L += ["", "## By kind of dish (independent estimates)", "", "| family | dishes | in band | in range | median ratio Roli / published |", "|---|---|---|---|---|"]
    for fam in sorted({r["family"] for r in head}):
        rs = [r for r in head if r["family"] == fam]
        bb = block(rs)
        L.append(f"| {fam} | {len(rs)} | {bb['in_band']} | {bb['in_range']} | {bb['median_ratio']:.2f} |" if bb["median_ratio"] else f"| {fam} | {len(rs)} | {bb['in_band']} | {bb['in_range']} | |")
    chol = [r for r in rows if r.get("chol_in_range") is not None]
    if chol:
        L += ["", f"Cholesterol (Bonefish and Carrabba's publish it): inside the band {pct(sum(r['chol_in_band'] for r in chol), len(chol))}, inside the full range {pct(sum(r['chol_in_range'] for r in chol), len(chol))}."]
    L += ["", "## Every dish", "", "| chain | dish | family | published g | Roli band g (middle) | full range g | in band | in range | Roli / published | status |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if r["estimated"]:
            L.append(f"| {r['chain']} | {r['dish'][:34]} | {r['family']}{' (dependent)' if r['dependent'] else ''} | {r['published']:g} | {r['band_low']:.1f}-{r['band_high']:.1f} ({r['band_mid']:.1f}) | "
                     f"{r['low']:.1f}-{r['high']:.1f} | {'yes' if r['in_band'] else 'no'} | {'yes' if r['in_range'] else 'no'} | {f'{r['ratio']:.2f}' if r['ratio'] else ''} | {r['status']} |")
        else:
            L.append(f"| {r['chain']} | {r['dish'][:34]} | {r['family']} | {r['published']:g} | no estimate | | | | | {r['status']}: {r['reason'][:60]} |")
    out = EVAL / f"known_answer_check_{date}.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:40]))
    print("written", out)


LLM_ONLY_PROMPT = """You estimate nutrition for restaurant dishes from their names alone. You have no recipes, no database and no tools: use what you know.

For each dish below (section, then name, as a restaurant menu prints them), estimate per plate AS SERVED in a restaurant:
- saturated fat in grams: a best guess, and a low and a high such that you are 80 % sure the restaurant's true figure lies between them;
- cholesterol in milligrams: the same three numbers.

Dishes:
{items}

Answer with ONE JSON object and nothing else:
{{"dishes": [{{"index": 0, "sat_fat_g": {{"low": 0, "best": 0, "high": 0}}, "cholesterol_mg": {{"low": 0, "best": 0, "high": 0}}}}, ...]}}
Include every index exactly once."""


def llm_only(date: str) -> None:
    """Experiment (Julius, 2026-11-08): the same dishes, names and sections only, to the same model with no tools or data; one call per typed menu, through the budget
    and the ledger. The answers are kept beside Roli's in the menus file; they never enter Roli."""
    load_dotenv(ROOT / ".env")
    from langchain_core.messages import HumanMessage
    from roli_agent.config import BATCH_ANSWER_TOKENS, BATCH_TIMEOUT_SECONDS, MODEL_ID
    from roli_agent.llm import RateLimitedLLM, make_chat_model, parse_json_object
    from roli_agent.mvp.budget import BudgetedLLM, Limits, MenuBudget, Prices, SpendLedger
    path = MENUS / f"{date}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    llm = RateLimitedLLM(make_chat_model(max_tokens=BATCH_ANSWER_TOKENS, timeout=BATCH_TIMEOUT_SECONDS))
    prices = Prices.load(MODEL_ID, ROOT / ".cache" / "roli_mvp" / "openrouter_prices.json")
    budget = MenuBudget(Limits.from_env(), SpendLedger(RUNS / "spend_ledger.jsonl"), prices, run_id=f"known-answer-llm-only-{date}")
    out = {}
    try:
        for m in data["menus"]:
            items = "\n".join(f"{i}. [{it['section'] or 'no section'}] {it['name']}" for i, it in enumerate(m["menu"]["items"]))
            reply = BudgetedLLM(llm, budget).invoke([HumanMessage(content=LLM_ONLY_PROMPT.format(items=items))])
            content = getattr(reply, "content", reply)
            parsed = parse_json_object(content if isinstance(content, str) else str(content)) or {}
            out[m["menu_id"]] = {str(d.get("index")): d for d in parsed.get("dishes", []) if isinstance(d, dict)}
            print(m["menu_id"], len(out[m["menu_id"]]), "answers", flush=True)
    finally:
        budget.close()
    data["llm_only"] = {"model": MODEL_ID, "prompt": LLM_ONLY_PROMPT, "answers": out, "spend": budget.report()}
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    print("spend", budget.report()["model_usd_total"])


def compare_llm_only(date: str) -> None:
    """The model alone against the published figures and against Roli, on the same dishes; appended to eval/known_answer_check_<date>.md."""
    data = json.loads((MENUS / f"{date}.json").read_text(encoding="utf-8"))
    roli = {(r["menu"], r["dish"]): r for r in csv.DictReader((EVAL / f"known_answer_check_{date}.csv").open(encoding="utf-8"))}
    rows = []
    for m in data["menus"]:
        ans = data["llm_only"]["answers"].get(m["menu_id"], {})
        for i, (item, a) in enumerate(zip(m["menu"]["items"], m["answers"])):
            g = ans.get(str(i)) or {}
            s, c = g.get("sat_fat_g") or {}, g.get("cholesterol_mg") or {}
            num = lambda v: float(v) if isinstance(v, (int, float)) else None
            r = roli.get((m["menu_id"], item["name"]), {})
            pub = float(a["sat_fat_g_per_plate"])
            pchol = float(a["cholesterol_mg_per_plate"]) if a.get("cholesterol_mg_per_plate") else None
            rows.append({"chain": m["chain"], "dish": item["name"], "family": a["family"], "dependent": bool(a["dependent"]), "published": pub, "published_chol": pchol,
                         "llm_low": num(s.get("low")), "llm_best": num(s.get("best")), "llm_high": num(s.get("high")),
                         "llm_chol_low": num(c.get("low")), "llm_chol_best": num(c.get("best")), "llm_chol_high": num(c.get("high")),
                         "roli_estimated": r.get("estimated") == "True", "roli_mid": float(r["band_mid"]) if r.get("band_mid") else None,
                         "roli_low": float(r["band_low"]) if r.get("band_low") else None, "roli_high": float(r["band_high"]) if r.get("band_high") else None})
    with (EVAL / f"known_answer_llm_only_{date}.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    def stats(rs, key_lo, key_mid, key_hi):
        ok = [r for r in rs if r[key_mid] is not None and r["published"] > 0 and r[key_mid] > 0]
        logs = [math.log(r[key_mid] / r["published"]) for r in ok]
        inside = sum(1 for r in rs if r[key_lo] is not None and r[key_lo] <= r["published"] <= r[key_hi])
        n = sum(1 for r in rs if r[key_mid] is not None)
        return {"n": n, "inside": inside, "within2": sum(1 for x in logs if abs(x) <= math.log(2)), "typical": math.exp(statistics.median(abs(x) for x in logs)) if logs else None,
                "median_ratio": math.exp(statistics.median(logs)) if logs else None, "over": sum(1 for x in logs if x > 0), "under": sum(1 for x in logs if x < 0)}
    indep = [r for r in rows if not r["dependent"]]
    both = [r for r in indep if r["roli_estimated"] and r["llm_best"] is not None]
    L = ["", "## The model alone, names only (experiment, 2026-11-08)", "",
         f"The same {len(rows)} dishes, names and sections only, to {data['llm_only']['model']} with no tools, recipes or data; one call per typed menu; it gave a best guess and an "
         f"80 % range per dish. Spend ${data['llm_only']['spend']['model_usd_total']}. The answers never enter Roli. Per dish: `known_answer_llm_only_{date}.csv`.", "",
         f"On the {len(both)} independent dishes both answered:", "",
         "| measure | the model alone | Roli |", "|---|---|---|"]
    a, b = stats(both, "llm_low", "llm_best", "llm_high"), stats(both, "roli_low", "roli_mid", "roli_high")
    pc = lambda x, n: f"{x} of {n} ({100 * x / n:.0f} %)" if n else "none"
    L += [f"| published figure inside its own range (each claims 8 in 10) | {pc(a['inside'], a['n'])} | {pc(b['inside'], b['n'])} |",
          f"| best guess / middle within a factor of 2 | {pc(a['within2'], a['n'])} | {pc(b['within2'], b['n'])} |",
          f"| typical miss | {a['typical']:.2f}x | {b['typical']:.2f}x |", f"| median ratio to published (1 = no lean) | {a['median_ratio']:.2f} | {b['median_ratio']:.2f} |",
          f"| too high / too low | {a['over']} / {a['under']} | {b['over']} / {b['under']} |"]
    closer_llm = sum(1 for r in both if r["published"] > 0 and r["llm_best"] > 0 and r["roli_mid"] > 0 and abs(math.log(r["llm_best"] / r["published"])) < abs(math.log(r["roli_mid"] / r["published"])))
    L += ["", f"Head to head, dish by dish: the model alone was closer on {closer_llm} of {len(both)}, Roli on {len(both) - closer_llm}.",
          f"On all {len(indep)} independent dishes the model alone answered every one; its range held the published figure {pc(stats(indep, 'llm_low', 'llm_best', 'llm_high')['inside'], len(indep))}."]
    chol = [r for r in rows if r["published_chol"] is not None and r["llm_chol_best"] is not None]
    if chol:
        ins = sum(1 for r in chol if r["llm_chol_low"] <= r["published_chol"] <= r["llm_chol_high"])
        w2 = sum(1 for r in chol if r["published_chol"] > 0 and r["llm_chol_best"] > 0 and abs(math.log(r["llm_chol_best"] / r["published_chol"])) <= math.log(2))
        L.append(f"Cholesterol (Bonefish and Carrabba's): the model alone's range held the published figure {pc(ins, len(chol))}; best guess within 2x {pc(w2, len(chol))}.")
    L += ["", "| chain | order agreement, model alone (Spearman) | order agreement, Roli | model alone's lightest pick: published rank |", "|---|---|---|---|"]
    for chain in dict.fromkeys(r["chain"] for r in rows):
        rs = [r for r in rows if r["chain"] == chain and r["llm_best"] is not None]
        rr = [r for r in rs if r["roli_mid"] is not None]
        top = min(rs, key=lambda r: r["llm_best"]) if rs else None
        rank = f"{top['dish']} ({top['published']:g} g): {1 + sum(1 for r in rs if r['published'] < top['published'])} of {len(rs)}" if top else ""
        s1, s2 = spearman([r["llm_best"] for r in rs], [r["published"] for r in rs]), spearman([r["roli_mid"] for r in rr], [r["published"] for r in rr])
        L.append(f"| {chain} | {f'{s1:.2f}' if s1 is not None else 'n/a'} | {f'{s2:.2f}' if s2 is not None else 'n/a'} | {rank} |")
    L += ["", "| chain | dish | published g | model alone: best (80 % range) | Roli: middle (band) | closer |", "|---|---|---|---|---|---|"]
    for r in rows:
        lo = f"{r['llm_best']:g} ({r['llm_low']:g}-{r['llm_high']:g})" if r["llm_best"] is not None else "no answer"
        ro = f"{r['roli_mid']:.1f} ({r['roli_low']:.1f}-{r['roli_high']:.1f})" if r["roli_mid"] is not None else "no estimate"
        closer = ""
        if r["llm_best"] and r["roli_mid"] and r["published"] > 0:
            closer = "model alone" if abs(math.log(r["llm_best"] / r["published"])) < abs(math.log(r["roli_mid"] / r["published"])) else "Roli"
        L.append(f"| {r['chain']} | {r['dish'][:34]}{' (dependent)' if r['dependent'] else ''} | {r['published']:g} | {lo} | {ro} | {closer} |")
    md = EVAL / f"known_answer_check_{date}.md"
    text = md.read_text(encoding="utf-8")
    cut = text.find("\n## The model alone")
    md.write_text((text if cut < 0 else text[:cut]) + "\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:24]))


RECALL_MENU_PROMPT = """Below is a list of dishes from one restaurant menu (section, then name, as printed). No restaurant name is given.

{items}

1. Which restaurant or restaurant chain do you think this menu comes from? Give your best answer, or "unknown" if you cannot tell.
2. For each dish, which restaurant chain serves a dish by exactly this name? "unknown" when you do not recognise it.

Answer with ONE JSON object and nothing else:
{{"menu_restaurant": "...", "menu_confidence": "high|medium|low", "dishes": [{{"index": 0, "chain": "...", "confidence": "high|medium|low"}}, ...]}}"""

RECALL_FIGURE_PROMPT = """For each dish below, the restaurant chain that serves it is named. If you know the chain's own PUBLISHED nutrition figures for the dish (from its nutrition
information), give saturated fat in grams and cholesterol in milligrams per serving as published. If you do not know the published figure, write null; do not estimate.

{items}

Answer with ONE JSON object and nothing else:
{{"dishes": [{{"index": 0, "known": true, "sat_fat_g": 0, "cholesterol_mg": 0}}, ...]}}"""


def recall_check(date: str) -> None:
    """Experiment (Julius, 2026-11-08): does the model recall these chain dishes? (1) name the restaurant from the menu as the model-alone experiment saw it; (2) quote the
    chain's published figure when told the chain. Through the budget and the ledger; nothing enters Roli. Writes eval/known_answer_recall_<date>.md and .csv."""
    load_dotenv(ROOT / ".env")
    from langchain_core.messages import HumanMessage
    from roli_agent.config import BATCH_ANSWER_TOKENS, BATCH_TIMEOUT_SECONDS, MODEL_ID
    from roli_agent.llm import RateLimitedLLM, make_chat_model, parse_json_object
    from roli_agent.mvp.budget import BudgetedLLM, Limits, MenuBudget, Prices, SpendLedger
    path = MENUS / f"{date}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    llm = RateLimitedLLM(make_chat_model(max_tokens=BATCH_ANSWER_TOKENS, timeout=BATCH_TIMEOUT_SECONDS))
    budget = MenuBudget(Limits.from_env(), SpendLedger(RUNS / "spend_ledger.jsonl"), Prices.load(MODEL_ID, ROOT / ".cache" / "roli_mvp" / "openrouter_prices.json"), run_id=f"known-answer-recall-{date}")
    ask = lambda prompt: parse_json_object((lambda c: c if isinstance(c, str) else str(c))(getattr(BudgetedLLM(llm, budget).invoke([HumanMessage(content=prompt)]), "content", ""))) or {}
    menus_out, figs_out = {}, {}
    try:
        for m in data["menus"]:
            items = "\n".join(f"{i}. [{it['section'] or 'no section'}] {it['name']}" for i, it in enumerate(m["menu"]["items"]))
            menus_out[m["menu_id"]] = ask(RECALL_MENU_PROMPT.format(items=items))
            items2 = "\n".join(f"{i}. {m['chain']}: {it['name']}" for i, it in enumerate(m["menu"]["items"]))
            figs_out[m["menu_id"]] = {str(d.get("index")): d for d in (ask(RECALL_FIGURE_PROMPT.format(items=items2)).get("dishes") or []) if isinstance(d, dict)}
            print(m["menu_id"], "->", menus_out[m["menu_id"]].get("menu_restaurant"), flush=True)
    finally:
        budget.close()
    data["recall"] = {"model": MODEL_ID, "menus": menus_out, "figures": figs_out, "spend": budget.report()}
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    norm = lambda s: re.sub(r"[^a-z]", "", (s or "").lower())
    short = {"Pizza Express": "pizzaexpress", "Bonefish Grill": "bonefish", "Zizzi": "zizzi", "Vapiano": "vapiano", "Carrabba's Italian Grill": "carrabba", "Prezzo": "prezzo", "Wasabi": "wasabi"}
    rows = []
    for m in data["menus"]:
        rec = menus_out[m["menu_id"]]
        by_i = {str(d.get("index")): d for d in (rec.get("dishes") or []) if isinstance(d, dict)}
        guess = data.get("llm_only", {}).get("answers", {}).get(m["menu_id"], {})
        for i, (it, a) in enumerate(zip(m["menu"]["items"], m["answers"])):
            d, f, g = by_i.get(str(i)) or {}, figs_out[m["menu_id"]].get(str(i)) or {}, guess.get(str(i)) or {}
            pub, pchol = float(a["sat_fat_g_per_plate"]), (float(a["cholesterol_mg_per_plate"]) if a.get("cholesterol_mg_per_plate") else None)
            best = (g.get("sat_fat_g") or {}).get("best")
            num = lambda v: float(v) if isinstance(v, (int, float)) else None
            rows.append({"chain": m["chain"], "dish": it["name"], "published": pub, "published_chol": pchol, "menu_named": rec.get("menu_restaurant", ""), "menu_right": short[m["chain"]] in norm(rec.get("menu_restaurant")),
                         "dish_chain": d.get("chain", ""), "dish_confidence": d.get("confidence", ""), "dish_right": short[m["chain"]] in norm(d.get("chain")),
                         "quoted_known": bool(f.get("known")), "quoted_sat": num(f.get("sat_fat_g")), "quoted_chol": num(f.get("cholesterol_mg")), "name_only_guess": num(best)})
    with (EVAL / f"known_answer_recall_{date}.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    def err(x, p):
        return abs(math.log(x / p)) if x and p and x > 0 and p > 0 else None
    def close(x, p, tol):
        e = err(x, p)
        return e is not None and e <= math.log(1 + tol)
    pc = lambda a, b: f"{a} of {b} ({100 * a / b:.0f} %)" if b else "none"
    quoted = [r for r in rows if r["quoted_known"] and r["quoted_sat"] is not None]
    L = [f"# Recall check, {date}", "", f"Does {MODEL_ID} recognise these 50 chain dishes, and can it quote their published figures? Two probes, one call each per typed menu; spend "
         f"${budget.report()['model_usd_total']}; nothing enters Roli. Per dish: `known_answer_recall_{date}.csv`.", "", "## 1. Naming the restaurant from the menu (no chain name given)", "",
         "| menu (truth) | the model's answer | confidence | dishes it attributed to the right chain |", "|---|---|---|---|"]
    for m in data["menus"]:
        rs = [r for r in rows if r["chain"] == m["chain"]]
        L.append(f"| {m['chain']} | {menus_out[m['menu_id']].get('menu_restaurant', '')} | {menus_out[m['menu_id']].get('menu_confidence', '')} | {sum(r['dish_right'] for r in rs)} of {len(rs)} |")
    L += ["", f"Overall: the right restaurant for {sum(1 for m in data['menus'] if short[m['chain']] in norm(menus_out[m['menu_id']].get('menu_restaurant')))} of {len(data['menus'])} menus; "
          f"the right chain for {pc(sum(r['dish_right'] for r in rows), len(rows))} dishes.", "", "## 2. Quoting the published figure (chain named, do not estimate)", "",
          f"It claimed to know the published saturated fat for {pc(len(quoted), len(rows))} dishes. Of those, the quoted figure was within 10 % of the published one for "
          f"{pc(sum(close(r['quoted_sat'], r['published'], 0.10) for r in quoted), len(quoted))}, within 25 % for {pc(sum(close(r['quoted_sat'], r['published'], 0.25) for r in quoted), len(quoted))}.", ""]
    qc = [r for r in rows if r["quoted_known"] and r["quoted_chol"] is not None and r["published_chol"]]
    if qc:
        L.append(f"Cholesterol quoted for {len(qc)} Bonefish or Carrabba's dishes; within 10 % for {pc(sum(close(r['quoted_chol'], r['published_chol'], 0.10) for r in qc), len(qc))}.")
    L += ["", "## 3. Were the name-only guesses better where it recognised the chain?", "", "| group | dishes | name-only guess within a factor of 2 | within 25 % | typical miss |", "|---|---|---|---|---|"]
    for label, grp in (("dish attributed to the right chain", [r for r in rows if r["dish_right"]]), ("not attributed", [r for r in rows if not r["dish_right"]])):
        es = [err(r["name_only_guess"], r["published"]) for r in grp]
        es = [e for e in es if e is not None]
        L.append(f"| {label} | {len(grp)} | {sum(1 for e in es if e <= math.log(2))} | {sum(1 for e in es if e <= math.log(1.25))} | {math.exp(statistics.median(es)):.2f}x |" if es else f"| {label} | {len(grp)} | | | |")
    L += ["", "| chain | dish | published g | attributed to | quoted (known?) | name-only guess |", "|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['chain']} | {r['dish'][:34]} | {r['published']:g} | {r['dish_chain'] or ''} ({r['dish_confidence']}) | {'' if r['quoted_sat'] is None else format(r['quoted_sat'], 'g')} ({'yes' if r['quoted_known'] else 'no'}) | {'' if r['name_only_guess'] is None else format(r['name_only_guess'], 'g')} |")
    out = EVAL / f"known_answer_recall_{date}.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:40]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("build", "run", "report", "llm-only", "compare-llm-only", "recall-check"))
    ap.add_argument("--date", required=True)
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--daily-usd", default=None)
    ap.add_argument("--daily-credits", type=int, default=None)
    args = ap.parse_args()
    if args.step == "build":
        build(args.n, args.date)
    elif args.step == "run":
        run(args.date, args.daily_usd, args.daily_credits)
    elif args.step == "llm-only":
        llm_only(args.date)
    elif args.step == "compare-llm-only":
        compare_llm_only(args.date)
    elif args.step == "recall-check":
        recall_check(args.date)
    else:
        report(args.date)
    return 0


if __name__ == "__main__":
    sys.exit(main())
