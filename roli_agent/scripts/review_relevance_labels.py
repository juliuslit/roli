"""Independent review of the frozen relevance reference labels (Julius, 2026-11-03: "arrange a small independent review of the reference
labels, prioritizing high-impact preparation mismatches").

A second model, from a different family than the pipeline's grader (default anthropic/claude-sonnet-5.5; the pipeline grades with Gemini),
reads each of the 42 frozen recipes (title, yield, verbatim ingredient lines, method text) against its menu item and gives ITS OWN judgment:
usable as a recipe at all, dish type, preparation, course, and whether the method cooks the main ingredient of a raw dish. It never sees the
reference labels. The script then lists every disagreement with the reference (`relevance_set_v1.csv`), preparation mismatches first, for
Julius to settle. Nothing in the CSV is changed.

    .venv/bin/python -m roli_agent.scripts.review_relevance_labels [--model anthropic/claude-sonnet-5.5] [--tag _2026-11-03]

Writes `menu_reader_eval/relevance/independent_review<tag>.json` and `.md`. Cost: one short call per recipe (42 calls).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

from roli_agent.config import ROOT
from roli_agent.llm import make_chat_model, parse_json_object
from roli_agent.recipes.relevance import combine
from roli_agent.scripts.eval_relevance_2c1 import SET_PATH, load_frozen

PROMPT = """You are an independent reviewer checking whether a published recipe is a fair stand-in for a restaurant menu dish, for the purpose
of estimating that dish's saturated fat and cholesterol from the recipe's ingredients. You do not estimate nutrition.

Menu item: "{name}" (menu section: {section}); the menu prints these ingredients: {description}.

Recipe page:
- title: {title}
- yield text: {yield_text}
- ingredient lines (verbatim):
{lines}
- method text (may be truncated):
{method}

Judge, from the recipe's own words, not its title:
1. usable: true if this is one recipe with quantified ingredient lines (not a collection, a listicle, a product page or a text with ingredient names only).
2. dish_type: "same" (the same dish), "variant" (a close relative), or "different" (another dish).
3. preparation: "same", "similar" or "different" compared with the menu dish. A crudo is raw sliced fish; a lettuce salad is raw leaves; a
   margherita is a baked pizza; a king salmon entree is a cooked fish main. A recipe whose METHOD grills, chars, roasts, sears, bakes, braises or
   fries the main ingredient of a raw dish is "different" even if its title sounds like the dish. A cooked garnish on raw leaves (toasted seeds,
   baked cheese placed on the salad) does not change the preparation.
4. course_portion: "same" (a starter recipe for a starter, a main for a main, a pizza for a pizza) or "different".
5. cooks_main_ingredient: true if the method text cooks the main ingredient of a raw menu dish; false otherwise (false for cooked menu dishes).
6. confidence: "high", "medium" or "low".

Answer with ONE JSON object and nothing else:
{{"usable": true, "dish_type": "same", "preparation": "same", "course_portion": "same", "cooks_main_ingredient": false, "confidence": "high", "reason": "one or two sentences quoting the decisive words"}}
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen", default=str(ROOT / "roli_agent" / "eval" / "frozen_inputs_2c1.json"))
    parser.add_argument("--model", default="anthropic/claude-sonnet-5.5")
    parser.add_argument("--tag", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--pause", type=float, default=3.5, help="seconds between calls (OpenRouter allows 20 requests per minute on this model for new accounts)")
    parser.add_argument("--resume", action="store_true", help="keep the successful reviews of an earlier run with the same tag; redo only the errors")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    frozen = load_frozen(Path(args.frozen))
    rows = list(csv.DictReader(SET_PATH.open(encoding="utf-8")))
    ref = {(r["dish"], r["canonical_url"]): r for r in rows}
    set_hash = hashlib.sha256(SET_PATH.read_bytes()).hexdigest()
    llm = make_chat_model(args.model, max_tokens=600, timeout=90)
    out = {"date": str(date.today()), "reviewer_model": args.model, "set_sha256": set_hash, "reviews": []}
    cost_total, tokens_in, tokens_out, n = 0.0, 0, 0, 0
    previous: dict[str, dict] = {}
    base = ROOT / "menu_reader_eval" / "relevance" / f"independent_review{args.tag}"
    if args.resume and base.with_suffix(".json").exists():
        old = json.loads(base.with_suffix(".json").read_text(encoding="utf-8"))
        previous = {x["canonical_url"]: x for x in old["reviews"] if x.get("reviewer")}
        s_old = old.get("summary", {})
        cost_total, tokens_in, tokens_out = s_old.get("cost_usd_reported", 0.0), s_old.get("tokens_in", 0), s_old.get("tokens_out", 0)
        print(f"resuming: {len(previous)} reviews kept from the earlier run")
    t0 = time.perf_counter()
    for dish, (item, recipes, _) in frozen.items():
        for r in recipes:
            rr = ref.get((dish, r.canonical_url))
            if rr is None:
                continue
            if args.limit and n >= args.limit:
                break
            n += 1
            if r.canonical_url in previous:
                out["reviews"].append(previous[r.canonical_url])
                continue
            if n > 1:
                time.sleep(args.pause)
            prompt = PROMPT.format(name=item.name, section=item.section or "none", description=item.description or "none", title=r.title, yield_text=r.yield_text or "none",
                                   lines="\n".join(f"  - {l}" for l in r.ingredient_lines[:40]) or "  (none)", method=(r.instructions_text or "(none)")[:2500])
            review, error = None, None
            for attempt in range(3):
                try:
                    reply = llm.invoke([HumanMessage(content=prompt)])
                    error = None
                    break
                except Exception as exc:              # noqa: BLE001
                    error = f"{type(exc).__name__}: {exc}"[:200]
                    if "429" in error or "Rate limit" in error:
                        time.sleep(20 * (attempt + 1))
                        continue
                    break
            try:
                if error is not None:
                    raise RuntimeError(error)
                review = parse_json_object(reply.content if isinstance(reply.content, str) else json.dumps(reply.content))
                meta = (getattr(reply, "response_metadata", None) or {}).get("token_usage") or {}
                usage = getattr(reply, "usage_metadata", None) or {}
                tokens_in += int(usage.get("input_tokens") or meta.get("prompt_tokens") or 0)
                tokens_out += int(usage.get("output_tokens") or meta.get("completion_tokens") or 0)
                if isinstance(meta.get("cost"), (int, float)):
                    cost_total += float(meta["cost"])
            except Exception as exc:              # noqa: BLE001
                error = f"{type(exc).__name__}: {exc}"[:200]
            if review is None and error is None:
                error = "no JSON object in the reply"
            # the reviewer's verdict mapped onto the pipeline's gate: usable, the same dish or a variant of it, and no cooked main ingredient
            rev_gate = ("passed" if review.get("usable") and review.get("dish_type") in ("same", "variant") and not review.get("cooks_main_ingredient") else "rejected") if review else ""
            rev_grade, rev_hard = combine(review.get("dish_type", ""), review.get("preparation", ""), review.get("course_portion", "")) if review else ("", None)
            if review and review.get("cooks_main_ingredient"):
                rev_hard = rev_hard or "hard_exclusion:main_ingredient_cooked_in_method"
            disagreements = []
            if review:
                if rev_gate != rr["ref_gate"]:
                    disagreements.append(f"gate: reviewer {rev_gate} vs reference {rr['ref_gate']}")
                for field, key in (("ref_dish_type", "dish_type"), ("ref_preparation", "preparation"), ("ref_course", "course_portion")):
                    if rr[field] and review.get(key) != rr[field]:
                        disagreements.append(f"{key}: reviewer {review.get(key)} vs reference {rr[field]}")
                ref_excl = bool(rr["ref_hard_exclusion"]) or rr["ref_gate"] == "rejected"
                if bool(review.get("cooks_main_ingredient")) != bool("cooked_in_method" in (rr["ref_hard_exclusion"] or "")):
                    disagreements.append(f"cooks_main_ingredient: reviewer {review.get('cooks_main_ingredient')} vs reference exclusion {rr['ref_hard_exclusion'] or 'none'}")
                if rev_grade and rr["ref_grade"] and rev_grade != rr["ref_grade"] and rr["ref_gate"] == "passed":
                    disagreements.append(f"grade (Python combine): reviewer {rev_grade} vs reference {rr['ref_grade']}")
            prep_related = any(d.startswith(("preparation", "cooks_main")) for d in disagreements)
            out["reviews"].append({"dish": dish, "title": r.title, "canonical_url": r.canonical_url, "reference": {k: rr[k] for k in rr if k.startswith("ref_")},
                                   "reviewer": review, "reviewer_gate": rev_gate, "reviewer_grade": rev_grade, "reviewer_hard_exclusion": rev_hard, "error": error,
                                   "disagreements": disagreements, "preparation_related": prep_related})
            print(f"{n:2d} {dish[:12]:12s} {r.title[:48]!r:50s} -> {rev_gate:8s} {review.get('preparation', '?') if review else 'ERR':9s} {'DISAGREE: ' + '; '.join(disagreements) if disagreements else 'agrees'}")
    seconds = round(time.perf_counter() - t0, 1)
    reviewed = [x for x in out["reviews"] if x["reviewer"]]
    agree = [x for x in reviewed if not x["disagreements"]]
    prep = [x for x in reviewed if x["preparation_related"]]
    out["summary"] = {"reviewed": len(reviewed), "errors": len(out["reviews"]) - len(reviewed), "full_agreement": len(agree), "with_disagreements": len(reviewed) - len(agree),
                      "preparation_related_disagreements": len(prep), "tokens_in": tokens_in, "tokens_out": tokens_out, "cost_usd_reported": round(cost_total, 4), "seconds": seconds}
    base.with_suffix(".json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    md = [f"# Independent review of the relevance reference labels ({out['date']})", "",
          f"Reviewer model: `{args.model}` (the pipeline grades with Gemini 3.8 Flash); reference set `relevance_set_v1.csv` sha256 {set_hash[:16]}…; "
          f"the reviewer never saw the reference labels. {len(reviewed)} recipes reviewed, {len(agree)} in full agreement, {len(reviewed) - len(agree)} with at least one "
          f"disagreement, {len(prep)} of them preparation-related. Tokens {tokens_in}+{tokens_out}, cost reported ${cost_total:.3f}, {seconds} s.", "",
          "## Preparation-related disagreements (settle these first)", ""]
    for x in prep:
        md.append(f"- **{x['dish']}** {x['title'][:70]!r}: {'; '.join(x['disagreements'])}. Reviewer: {(x['reviewer'] or {}).get('reason', '')[:260]}")
    md += ["", "## Other disagreements", ""]
    for x in reviewed:
        if x["disagreements"] and not x["preparation_related"]:
            md.append(f"- **{x['dish']}** {x['title'][:70]!r}: {'; '.join(x['disagreements'])}. Reviewer: {(x['reviewer'] or {}).get('reason', '')[:260]}")
    md += ["", "## Full agreement", ""] + [f"- {x['dish']} {x['title'][:70]!r} ({x['reviewer_gate']}, {(x['reviewer'] or {}).get('preparation')})" for x in agree]
    if len(reviewed) < len(out["reviews"]):
        md += ["", "## Errors", ""] + [f"- {x['dish']} {x['title'][:60]!r}: {x['error']}" for x in out["reviews"] if not x["reviewer"]]
    base.with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n", json.dumps(out["summary"]), "\nwritten:", base.with_suffix(".md"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
