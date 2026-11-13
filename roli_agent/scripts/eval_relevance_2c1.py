"""Phase 2C.1 requirement C: a frozen relevance evaluation on the real recipes of the five test dishes.

Reference judgments live in `menu_reader_eval/relevance/relevance_set_v1.csv` (one row per distinct recipe seen for a dish; columns
`ref_*` are the human-reviewable reference; `reviewer` says who wrote them). The recipes themselves are the frozen inputs
(`roli_agent/eval/frozen_inputs_2c1.json`), so the LLM sees exactly the same titles, yields, method sentences and ingredient names each run.

    --write-skeleton   create the CSV with the saved outcomes filled in and empty reference columns (does not overwrite an existing file)
    --runs N           run the Python gate and the LLM rubric N times (live model calls: N per dish) and report accuracy and consistency

Writes `menu_reader_eval/relevance/results_<date>.json` and prints the tables.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from roli_agent.config import BATCH_ANSWER_TOKENS, BATCH_TIMEOUT_SECONDS, ROOT
from roli_agent.llm import make_chat_model, parse_json_object
from roli_agent.recipes.models import MenuItem, Relevance, SourceRecipe
from roli_agent.recipes.relevance import combine, gate, grade_batch, menu_coverage

SET_PATH = ROOT / "menu_reader_eval" / "relevance" / "relevance_set_v1.csv"
FIELDS = ["dish", "canonical_url", "title", "host", "yield_text", "saved_gate", "saved_grade", "saved_hard_exclusion", "saved_status",
          "ref_gate", "ref_dish_type", "ref_preparation", "ref_course", "ref_grade", "ref_hard_exclusion", "rationale", "reviewer", "review_status"]


def load_frozen(path: Path) -> dict[str, tuple[MenuItem, list[SourceRecipe], dict[str, dict]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for dish, d in data["dishes"].items():
        recipes = [SourceRecipe(**{k: v for k, v in r.items() if not k.startswith("saved_")}) for r in d["recipes"] if r["duplicate_of"] is None]
        meta = {r["canonical_url"]: r for r in d["recipes"]}
        out[dish] = (MenuItem(**d["menu_item"]), recipes, meta)
    return out


def write_skeleton(frozen) -> None:
    if SET_PATH.exists():
        print("exists, not overwritten:", SET_PATH)
        return
    with SET_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for dish, (item, recipes, meta) in frozen.items():
            for r in recipes:
                m = meta[r.canonical_url]
                rel = m.get("saved_relevance") or {}
                st = m.get("saved_status") or ["not_in_saved_run", None]
                w.writerow({"dish": dish, "canonical_url": r.canonical_url, "title": r.title, "host": r.host, "yield_text": r.yield_text,
                            "saved_gate": rel.get("gate", ""), "saved_grade": rel.get("grade", ""), "saved_hard_exclusion": rel.get("hard_exclusion") or "",
                            "saved_status": f"{st[0]}:{st[1] or ''}", "ref_gate": "", "ref_dish_type": "", "ref_preparation": "", "ref_course": "", "ref_grade": "",
                            "ref_hard_exclusion": "", "rationale": "", "reviewer": "", "review_status": "draft"})
    print("skeleton written:", SET_PATH)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen", default=str(ROOT / "roli_agent" / "eval" / "frozen_inputs_2c1.json"))
    parser.add_argument("--write-skeleton", action="store_true")
    parser.add_argument("--runs", type=int, default=0)
    parser.add_argument("--tag", default="")
    args = parser.parse_args()
    frozen = load_frozen(Path(args.frozen))
    if args.write_skeleton:
        write_skeleton(frozen)
        return 0
    rows = list(csv.DictReader(SET_PATH.open(encoding="utf-8")))
    ref = {(r["dish"], r["canonical_url"]): r for r in rows}
    set_hash = hashlib.sha256(SET_PATH.read_bytes()).hexdigest()
    print("reference set:", SET_PATH, "sha256:", set_hash, "rows:", len(rows))

    # 1. the Python gate (deterministic): once
    gate_rows = []
    for dish, (item, recipes, _) in frozen.items():
        for r in recipes:
            passed, reason = gate(item, r)
            rr = ref.get((dish, r.canonical_url))
            if rr is None:
                continue
            gate_rows.append({"dish": dish, "title": r.title, "gate": "passed" if passed else "rejected", "reason": reason or "", "ref_gate": rr["ref_gate"],
                              "ref_hard_exclusion": rr["ref_hard_exclusion"]})
    agree = sum(1 for g in gate_rows if g["gate"] == g["ref_gate"])
    print(f"\n=== PYTHON GATE vs reference: {agree}/{len(gate_rows)} agree ===")
    for g in gate_rows:
        if g["gate"] != g["ref_gate"]:
            print(f"  DISAGREE {g['dish'][:12]:12s} {g['title'][:50]!r}: gate {g['gate']} ({g['reason']}) vs ref {g['ref_gate']}")
    out = {"date": str(date.today()), "set_sha256": set_hash, "gate": gate_rows, "runs": []}
    if args.runs <= 0:
        (ROOT / "menu_reader_eval" / "relevance" / f"results_{date.today()}{args.tag}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
        return 0

    # 2. the LLM rubric, N times, on the gate-passed recipes (as the pipeline does)
    load_dotenv(ROOT / ".env")
    llm = make_chat_model(max_tokens=BATCH_ANSWER_TOKENS, timeout=BATCH_TIMEOUT_SECONDS)
    out["model"] = llm.model_name
    per_recipe: dict[tuple[str, str], list[tuple[str, str, str, str, str]]] = {}
    for run in range(args.runs):
        for dish, (item, recipes, _) in frozen.items():
            passed_recipes, rels = [], []
            for r in recipes:
                ok, _reason = gate(item, r)
                if ok and (dish, r.canonical_url) in ref:
                    cov, matched, missing = menu_coverage(item, r)
                    passed_recipes.append(r)
                    rels.append(Relevance(menu_coverage=cov, menu_matched=matched, menu_missing=missing, gate="passed"))
            log = grade_batch(item, passed_recipes, rels, llm, parse_json_object)
            for r, rel in zip(passed_recipes, rels):
                per_recipe.setdefault((dish, r.canonical_url), []).append((rel.dish_type or "", rel.preparation or "", rel.course_portion or "", rel.grade, rel.hard_exclusion or ""))
            out["runs"].append({"run": run + 1, "dish": dish, "log": log})
        print(f"run {run + 1}/{args.runs} done")

    # 3. accuracy and consistency
    print(f"\n=== RUBRIC, {args.runs} runs on the gate-passed recipes (reference grade / hard exclusion; Python combines) ===")
    exact, grade_ok, consistent, n = 0, 0, 0, 0
    detail = []
    for (dish, url), answers in per_recipe.items():
        rr = ref[(dish, url)]
        n += 1
        modal = Counter(answers).most_common(1)[0]
        agreement = modal[1] / len(answers)
        if agreement == 1.0:
            consistent += 1
        grades = [a[3] for a in answers]
        ref_grade = rr["ref_grade"]
        ok_runs = sum(1 for a in answers if a[3] == ref_grade and (a[4].split(":")[0] == rr["ref_hard_exclusion"].split(":")[0] if rr["ref_hard_exclusion"] else a[4] == ""))
        grade_ok += ok_runs / len(answers)
        exact += sum(1 for a in answers if (a[0], a[1], a[2]) == (rr["ref_dish_type"], rr["ref_preparation"], rr["ref_course"])) / len(answers)
        title = next(r.title for r in frozen[dish][1] if r.canonical_url == url)
        detail.append({"dish": dish, "title": title, "ref": (rr["ref_dish_type"], rr["ref_preparation"], rr["ref_course"], ref_grade, rr["ref_hard_exclusion"]),
                       "answers": answers, "agreement": agreement, "grade_accuracy": ok_runs / len(answers)})
        flag = "" if ok_runs == len(answers) and agreement == 1.0 else "  <-- "
        print(f"  {dish[:12]:12s} {title[:48]!r:50s} ref {ref_grade:6s} | runs {Counter(grades)} | all-three agreement {agreement:.0%} | grade accuracy {ok_runs}/{len(answers)}{flag}")
    print(f"\n  recipes graded: {n}; fully consistent across runs: {consistent}/{n}; mean grade accuracy vs reference: {grade_ok / n:.1%}; "
          f"mean exact-triple accuracy: {exact / n:.1%}")
    out["detail"] = detail
    out["summary"] = {"graded": n, "consistent": consistent, "mean_grade_accuracy": grade_ok / n if n else None, "mean_triple_accuracy": exact / n if n else None,
                      "gate_agreement": f"{agree}/{len(gate_rows)}"}
    path = ROOT / "menu_reader_eval" / "relevance" / f"results_{date.today()}{args.tag}.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print("written:", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
