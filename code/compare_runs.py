"""Print one table over every smoke run in results/: model x prompt, with the scores and cost.

Run:  .venv/bin/python code/compare_runs.py
"""
import json

from config import RESULTS


def pct(x):
    return "-" if x is None else f"{100 * x:.0f}%"


def main():
    rows = []
    for d in sorted(RESULTS.glob("smoke_*")):
        f = d / "summary.json"
        if not f.exists() or "ABORTED" in d.name:
            continue
        s = json.loads(f.read_text())
        per_photo = {c["photo"]: c for c in s["calls"]}
        found = {}
        for n in s["photos"]:
            sc = json.loads((d / f"menu_{n}_scores.json").read_text())
            found[n] = pct(sc["dishes_found"])
        costs = [c["cost_usd"] for c in s["calls"] if c.get("cost_usd") is not None]
        secs = [c["seconds"] for c in s["calls"] if c.get("seconds") is not None]
        s.setdefault("cost_total_usd", sum(costs) if costs else None)
        s.setdefault("cost_avg_usd", sum(costs) / len(costs) if costs else None)
        s.setdefault("seconds_avg", sum(secs) / len(secs) if secs else None)
        rows.append((s["model"].split("/")[1], s["prompt"], d.name[6:22], found, s))   # temperature: see 'temp' column
    print(f"{'model':28s} {'prompt':6s} {'temp':4s} {'run':17s} {'06':>5s} {'17':>5s} {'13':>5s} {'invent':>6s} {'prices':>6s} {'desc':>5s} {'format':>6s} {'partly':>6s} {'s/photo':>7s} {'c/photo':>7s} {'total $':>8s}")
    for model, prompt, run, found, s in rows:
        temp = str(s.get("temperature", "1.0"))   # runs before 2026-10-28 22:00 had no setting: host default 1.0
        print(f"{model:28s} {prompt:6s} {temp:4s} {run:17s} {found.get('06','-'):>5s} {found.get('17','-'):>5s} {found.get('13','-'):>5s} "
              f"{s['invented_total']:>6d} {pct(s['prices_right_avg']):>6s} {pct(s['descriptions_right_avg']):>5s} {pct(s['format_right_avg']):>6s} "
              f"{s['bad_photos_caught']}/{s['bad_photos_total']:<4d} {s.get('seconds_avg') or 0:>7.0f} {100*(s.get('cost_avg_usd') or 0):>7.2f} {s.get('cost_total_usd') or 0:>8.4f}")
    total = sum(s.get("cost_total_usd") or 0 for *_, s in rows)
    print(f"\nspend across these runs: ${total:.4f}")


if __name__ == "__main__":
    main()
