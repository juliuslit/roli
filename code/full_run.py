"""The full test: one model x one prompt over the LangSmith dataset, every photo sent twice.

Run:  .venv/bin/python code/full_run.py --model anthropic/claude-haiku-5.5 --prompt v1
      .venv/bin/python code/full_run.py --model ... --prompt v2 --photos 06 17 13 --repetitions 1   (smoke of this script)

What happens:
  1. LangSmith runs every example of the dataset through read_menu() (photo + prompt -> model -> raw answer),
     --repetitions times, ONE CALL AT A TIME (parallel calls slow the hosts down and spoil the timings).
  2. One bundled scorer (score_all) scores each answer with scorers.score_answer() and sends all scores to
     LangSmith as one feedback set per call - one trace per call instead of one per score, to stay inside
     the free plan's 5,000 traces a month.
  3. Everything is also saved locally under results/full_<date>_<model>_<prompt>_t<temperature>/ :
       run1/menu_NN_raw.txt, run1/menu_NN_scores.json, run2/..., check_list.csv, summary.json, verdict.txt
  4. The verdict applies scoring_rules.md as written, and once more with photo 17 set aside (agreed 2026-10-29).
"""
import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from langsmith import Client, evaluate

from config import DATASET_NAME, RESULTS, expected_path, keys_look_real, photo_number, prompt_path
from menu_reader import DEADLINE_SECONDS, MAX_ANSWER_TOKENS, TEMPERATURE, provider_order, read_menu, reasoning_setting
from scorers import score_answer

SCORE_KEYS = ["dishes_found", "invented", "garbled", "grouping", "joined_found", "cut_off_listed", "prices_right",
              "descriptions_right", "tags_right", "portion_right", "has_choice_right", "belongs_to_right",
              "format_right", "fenced", "bad_photo_caught", "false_alarm", "seconds", "cost_usd", "prompt_tokens", "completion_tokens", "reasoning_tokens"]
RULES_VERSION = "scoring_rules.md interpretations 1-18 (2026-10-30)"
RULES_TAG = "rules1-18"                                        # short form, used in re-scored folder names
PARTLY_PHOTOS = ["02", "10", "13", "15", "16", "17", "24"]     # scoring_rules.md, score 7
SET_ASIDE = ["17"]                                             # reported both ways, agreed 2026-10-29

state = {"run_dir": None, "model": None, "prompt": None, "seen": defaultdict(int), "scores": [], "check_list": [],
         "pause_host": None, "pause_after": 0, "host_calls": defaultdict(int)}


def target(inputs: dict) -> dict:
    """One model call. Called by LangSmith once per example per repetition, in sequence."""
    photo = photo_number(inputs["photo_id"])
    state["seen"][photo] += 1
    rep = state["seen"][photo]
    call = read_menu(inputs["telegram_file"], state["prompt"], state["model"])
    rep_dir = state["run_dir"] / f"run{rep}"
    rep_dir.mkdir(parents=True, exist_ok=True)
    (rep_dir / f"menu_{photo}_raw.txt").write_text(call["raw_text"] or "")
    call["photo"], call["rep"] = photo, rep
    state["host_calls"][str(call["provider"]).lower()] += 1
    print(f"  {state['model'].split('/')[-1]} {state['prompt']} run{rep} photo {photo}: {call['seconds']:.0f}s "
          f"finish={call['finish_reason']} host={call['provider']} "
          f"cost={('$%.4f' % call['cost_usd']) if call['cost_usd'] is not None else 'n/a'}"
          + (f" reasoning_tokens={call['reasoning_tokens']}" if call.get("reasoning_tokens") else "")
          + (f" ERROR {call['error']}" if call["error"] else ""), flush=True)
    if state["pause_host"] and state["host_calls"][state["pause_host"]] > state["pause_after"]:
        # --pause-on-host: too many calls landed on a host we only allowed as a fallback. Stop here (raw answers
        # and scores so far are on disk), leave a note, and exit with code 3 so a shell loop can stop too.
        note = (f"PAUSED after {sum(state['host_calls'].values())} calls: {state['host_calls'][state['pause_host']]} landed on "
                f"{state['pause_host']} (limit {state['pause_after']}). Hosts so far: {dict(state['host_calls'])}")
        (state["run_dir"] / "PAUSED.txt").write_text(note)
        print("\n" + note, flush=True)
        import os
        os._exit(3)
    return call


def score_all(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """The bundled scorer: every score of scoring_rules.md for one answer, in one feedback set."""
    photo = photo_number(inputs["photo_id"])
    record = json.loads(expected_path(photo).read_text())       # expected + scoring_hints, the source of truth
    s = score_answer(record["expected"], record["scoring_hints"], outputs.get("raw_text") or "", photo=photo)
    s["seconds"], s["cost_usd"], s["finish_reason"] = outputs.get("seconds"), outputs.get("cost_usd"), outputs.get("finish_reason")
    s["rep"], s["provider"], s["error"] = outputs.get("rep"), outputs.get("provider"), outputs.get("error", "")
    s["prompt_tokens"], s["completion_tokens"] = outputs.get("prompt_tokens"), outputs.get("completion_tokens")
    s["reasoning_tokens"] = outputs.get("reasoning_tokens")
    s["generation_id"] = outputs.get("generation_id")
    rep_dir = state["run_dir"] / f"run{s['rep']}"
    (rep_dir / f"menu_{photo}_scores.json").write_text(json.dumps(s, indent=1, ensure_ascii=False))
    state["scores"].append(s)
    state["check_list"].extend(s["check_list"])
    results = [{"key": k, "score": s.get(k)} for k in SCORE_KEYS if s.get(k) is not None]
    results.append({"key": "format_reason", "comment": s.get("format_reason") or "ok", "score": None})
    return {"results": results}


def host_speeds(calls: list) -> dict:
    """Median output tokens per second per serving host, over the calls that have a token count."""
    by = defaultdict(list)
    for c in calls:
        if c.get("completion_tokens") and c.get("seconds"):
            by[c.get("provider") or "unknown"].append(c["completion_tokens"] / c["seconds"])
    out = {}
    for host, xs in by.items():
        xs.sort()
        out[host] = {"median_tokens_per_second": round(xs[len(xs) // 2]), "calls_measured": len(xs),
                     "calls_total": sum(1 for c in calls if (c.get("provider") or "unknown") == host)}
    return out


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def verdict(scores: list, set_aside: list) -> dict:
    """Apply the pass bars of scoring_rules.md to the scores of all runs (optionally with photos set aside)."""
    sc = [s for s in scores if s["photo"] not in set_aside]
    reps = sorted({s["rep"] for s in sc})
    by_rep = {r: [s for s in sc if s["rep"] == r] for r in reps}
    found_by_rep = {r: mean([s["dishes_found"] for s in by_rep[r]]) for r in reps}
    v = {
        "photos_set_aside": set_aside,
        "dishes_found_avg": mean([s["dishes_found"] for s in sc]),
        "dishes_found_min_photo": min((s["dishes_found"] for s in sc if s["dishes_found"] is not None), default=None),
        "invented_total_by_run": {r: sum(s["invented"] for s in by_rep[r]) for r in reps},
        "prices_right_avg": mean([s["prices_right"] for s in sc]),
        "descriptions_right_avg": mean([s["descriptions_right"] for s in sc]),
        "format_right_avg": mean([s["format_right"] for s in sc]),
        "fenced_total": sum(s.get("fenced", 0) or 0 for s in sc),
        "partly_caught_by_run": {r: f"{sum(1 for s in by_rep[r] if s['bad_photo_caught'])}/{sum(1 for s in by_rep[r] if s['readable_expected'] == 'partly')}" for r in reps},
        "false_alarms_by_run": {r: sum(1 for s in by_rep[r] if s["false_alarm"]) for r in reps},
        "seconds_avg": mean([s["seconds"] for s in sc]),
        "cost_avg_usd": mean([s["cost_usd"] for s in sc]),
        "cost_total_usd": sum(s["cost_usd"] or 0 for s in sc),
        "cut_off_listed_total": sum(s["cut_off_listed"] for s in sc),
        "cut_off_listed_by_run": {r: sum(s["cut_off_listed"] for s in by_rep[r]) for r in reps},
        "other_set_aside_total": sum(s.get("other_set_aside", 0) for s in sc),
        "garbled_total": sum(s.get("garbled", 0) for s in sc),
        "grouping_total": sum(s.get("grouping", 0) for s in sc),
        "joined_found_total": sum(s.get("joined_found", 0) for s in sc),
        "prompt_tokens_avg": mean([s.get("prompt_tokens") for s in sc]),
        "completion_tokens_avg": mean([s.get("completion_tokens") for s in sc]),
        "reasoning_tokens_total": sum(s.get("reasoning_tokens") or 0 for s in sc),
        "dishes_found_by_run": found_by_rep,
    }
    bars = {
        "1 dishes found >=95% avg": (v["dishes_found_avg"] or 0) >= 0.95,
        "1 no photo <80%": (v["dishes_found_min_photo"] or 0) >= 0.80,
        "2 invented 0 on both runs": all(n == 0 for n in v["invented_total_by_run"].values()),
        "2b cut-off lines listed 0 on both runs": all(n == 0 for n in v["cut_off_listed_by_run"].values()),
        "3 prices >=95%": (v["prices_right_avg"] or 0) >= 0.95,
        "4 descriptions >=90%": (v["descriptions_right_avg"] or 0) >= 0.90,
        "6 format >=98%": (v["format_right_avg"] or 0) >= 0.98,
        "7 all partly photos caught, both runs": all(a.split("/")[0] == a.split("/")[1] for a in v["partly_caught_by_run"].values()),
        "7 false alarms <=3 per run": all(n <= 3 for n in v["false_alarms_by_run"].values()),
        "8 speed <60 s avg": (v["seconds_avg"] or 1e9) < 60,
    }
    v["bars"] = bars
    v["passes"] = all(bars.values())
    if len(reps) >= 2:
        spread = max(found_by_rep.values()) - min(found_by_rep.values())
        v["unstable_runs_differ_over_5_points"] = spread > 0.05
    return v


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt", required=True, help="v1, v2 or v4 this round")
    parser.add_argument("--repetitions", type=int, default=2)
    parser.add_argument("--photos", nargs="*", help="subset, e.g. 06 17 13, for a smoke of this script")
    parser.add_argument("--pause-on-host", help="HOST:N - stop the run once more than N calls land on HOST (e.g. siliconflow:5)")
    args = parser.parse_args()
    problems = keys_look_real()
    if problems:
        sys.exit("\n".join(problems))
    if not prompt_path(args.prompt).exists():
        sys.exit(f"no such prompt file: {prompt_path(args.prompt)}")

    if args.pause_on_host:
        host, n = args.pause_on_host.rsplit(":", 1)
        state["pause_host"], state["pause_after"] = host.lower(), int(n)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    short = args.model.split("/")[-1]
    state.update(model=args.model, prompt=args.prompt,
                 run_dir=RESULTS / f"full_{stamp}_{args.model.replace('/', '_')}_{args.prompt}_t{TEMPERATURE}")
    state["run_dir"].mkdir(parents=True, exist_ok=True)

    client = Client()
    examples = list(client.list_examples(dataset_name=DATASET_NAME))
    if args.photos:
        wanted = {photo_number(p) for p in args.photos}
        examples = [e for e in examples if photo_number(e.inputs["photo_id"]) in wanted]
    examples.sort(key=lambda e: e.inputs["photo_id"])
    metadata = {"model": args.model, "prompt_version": args.prompt, "temperature": TEMPERATURE,
                "max_answer_tokens": MAX_ANSWER_TOKENS, "deadline_seconds": DEADLINE_SECONDS, "thinking": reasoning_setting(args.model),
                "provider_order": provider_order(args.model),
                "photos": len(examples), "repetitions": args.repetitions, "calls_in_sequence": True}
    print(f"full run: {args.model} x {args.prompt}, {len(examples)} photos x {args.repetitions}, temperature {TEMPERATURE}")
    print(f"saving to {state['run_dir']}", flush=True)

    evaluate(target, data=examples, evaluators=[score_all], metadata=metadata,
             experiment_prefix=f"{short}_{args.prompt}_t{TEMPERATURE}",
             description=f"{args.model}, prompt {args.prompt}, temperature {TEMPERATURE}, {args.repetitions} runs per photo",
             num_repetitions=args.repetitions, max_concurrency=1, client=client)

    scores = state["scores"]
    summary = {**metadata, "run_dir": str(state["run_dir"]),
               "rules": RULES_VERSION,
               "calls": [{k: s.get(k) for k in ("photo", "rep", "seconds", "cost_usd", "finish_reason", "provider", "error",
                                                "prompt_tokens", "completion_tokens", "reasoning_tokens", "generation_id")} for s in scores],
               "as_written": verdict(scores, []), "photo_17_set_aside": verdict(scores, SET_ASIDE)}
    summary["hosts"] = host_speeds(summary["calls"])
    (state["run_dir"] / "summary.json").write_text(json.dumps(summary, indent=1))
    with (state["run_dir"] / "check_list.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["photo", "key_confidence", "key_name", "key_price", "model_name", "model_price", "reason"])
        w.writeheader()
        for row in state["check_list"]:
            w.writerow({k: row.get(k, "") for k in w.fieldnames})

    lines = [f"{args.model} x {args.prompt} x temperature {TEMPERATURE}: {len(scores)} answers, ${summary['as_written']['cost_total_usd']:.2f}  [{RULES_VERSION}]"]
    for label in ("as_written", "photo_17_set_aside"):
        v = summary[label]
        lines.append(f"\n[{label}] passes: {v['passes']}" + ("  UNSTABLE (runs differ >5 points)" if v.get("unstable_runs_differ_over_5_points") else ""))
        lines.append(f"  dishes found avg {100 * (v['dishes_found_avg'] or 0):.1f}%  min photo {100 * (v['dishes_found_min_photo'] or 0):.0f}%  by run {{{', '.join(f'{r}: {100 * x:.1f}%' for r, x in v['dishes_found_by_run'].items())}}}")
        lines.append(f"  invented by run {v['invented_total_by_run']}  cut-off listed by run {v['cut_off_listed_by_run']}  prices {100 * (v['prices_right_avg'] or 0):.1f}%  descriptions {100 * (v['descriptions_right_avg'] or 0):.1f}%  format {100 * (v['format_right_avg'] or 0):.1f}% (fenced {v['fenced_total']})")
        lines.append(f"  partly caught {v['partly_caught_by_run']}  false alarms {v['false_alarms_by_run']}  speed {v['seconds_avg']:.0f} s  cost {100 * (v['cost_avg_usd'] or 0):.2f} c/photo")
        lines.append(f"  garbled {v['garbled_total']}  groupings {v['grouping_total']}  found via joined text {v['joined_found_total']}  tokens in/out avg {v['prompt_tokens_avg'] and round(v['prompt_tokens_avg'])}/{v['completion_tokens_avg'] and round(v['completion_tokens_avg'])}  reasoning tokens total {v['reasoning_tokens_total']}")
        lines.extend(f"    {'PASS' if ok else 'FAIL'}  {bar}" for bar, ok in v["bars"].items())
    lines.append("\nhosts: " + ", ".join(f"{h} {d['calls_total']} calls, median {d['median_tokens_per_second']} output tok/s" for h, d in summary["hosts"].items()))
    lines.append(f"\ncheck list: {len(state['check_list'])} medium/low key items -> {state['run_dir'] / 'check_list.csv'}")
    text = "\n".join(lines)
    (state["run_dir"] / "verdict.txt").write_text(text)
    print("\n" + text)


if __name__ == "__main__":
    main()
