"""Re-score saved answers from disk under the current scoring rules. No model calls.

Run:  .venv/bin/python code/rescore.py results/full_2026-10-29_1015_anthropic_claude-haiku-5.5_v1_t0 [more folders]

For each folder it reads run*/menu_NN_raw.txt, scores them with scorers.score_answer() as it is today, and
writes a sibling folder <folder>_rescored_<date>_<rules tag>/ with the same layout (run*/menu_NN_scores.json, summary.json,
verdict.txt, check_list.csv). The original scores are left untouched, so old and new rules can be compared.
Call stats (seconds, cost, host, tokens) are copied from the original summary.json where present.
"""
import csv
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import expected_path
from full_run import RULES_TAG, RULES_VERSION, SET_ASIDE, host_speeds, verdict
from scorers import score_answer


def rescore(folder: Path) -> Path:
    original = json.loads((folder / "summary.json").read_text()) if (folder / "summary.json").exists() else {}
    calls = {(c.get("photo"), c.get("rep", 1)): c for c in original.get("calls", [])}
    out_dir = folder.parent / f"{folder.name}_rescored_{date.today().isoformat()}_{RULES_TAG}"
    scores, check_list = [], []
    for raw_file in sorted(folder.glob("run*/menu_*_raw.txt")):
        rep = int(raw_file.parent.name[3:])
        photo = raw_file.stem[5:7]
        record = json.loads(expected_path(photo).read_text())
        s = score_answer(record["expected"], record["scoring_hints"], raw_file.read_text(), photo=photo)
        c = calls.get((photo, rep), {})
        for k in ("seconds", "cost_usd", "finish_reason", "provider", "error", "prompt_tokens", "completion_tokens", "reasoning_tokens", "generation_id"):
            s[k] = c.get(k)
        s["rep"] = rep
        (out_dir / f"run{rep}").mkdir(parents=True, exist_ok=True)
        (out_dir / f"run{rep}" / f"menu_{photo}_scores.json").write_text(json.dumps(s, indent=1, ensure_ascii=False))
        scores.append(s)
        check_list.extend(s["check_list"])
    meta = {k: original.get(k) for k in ("model", "prompt_version", "temperature", "max_answer_tokens", "deadline_seconds", "repetitions")}
    summary = {**meta, "rules": RULES_VERSION, "rescored_from": str(folder), "run_dir": str(out_dir),
               "calls": original.get("calls", []), "hosts": host_speeds(original.get("calls", [])),
               "reruns": original.get("reruns", []),
               "as_written": verdict(scores, []), "photo_17_set_aside": verdict(scores, SET_ASIDE)}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1))
    with (out_dir / "check_list.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["photo", "key_confidence", "key_name", "key_price", "model_name", "model_price", "reason"])
        w.writeheader()
        for row in check_list:
            w.writerow({k: row.get(k, "") for k in w.fieldnames})
    v = summary["as_written"]
    (out_dir / "verdict.txt").write_text(json.dumps({"as_written": v, "photo_17_set_aside": summary["photo_17_set_aside"]}, indent=1))
    return out_dir


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        out = rescore(Path(arg))
        print("rescored ->", out)
