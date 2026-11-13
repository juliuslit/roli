"""Smoke test: a few photos, one prompt, one model, once each. Prints raw answers and scores.

Run:  .venv/bin/python code/smoke_test.py --model qwen/qwen3.6-35b-a3b
      .venv/bin/python code/smoke_test.py --model google/gemma-4-26b-a4b-it --prompt v1 --photos 06 17 13

Everything is saved under results/smoke_<date>_<model>_<prompt>/ :
  menu_NN_raw.txt     the exact text the model returned
  menu_NN_scores.json the scores for that answer
  check_list.csv      medium/low answer-key items the model disagreed with (for a human to look at)
  summary.json        the run-level numbers
"""
import argparse
import csv
import json
import sys
import time
from datetime import datetime

from config import RESULTS, expected_path, keys_look_real, photo_number, prompt_path
from menu_reader import DEADLINE_SECONDS, MAX_ANSWER_TOKENS, TEMPERATURE, read_menu
from scorers import score_answer, summarise


def pct(x):
    return "-" if x is None else f"{100 * x:5.1f}%"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="exact OpenRouter model id, e.g. qwen/qwen3.6-35b-a3b")
    parser.add_argument("--prompt", default="v1", help="prompt version: v1, v2 or v3")
    parser.add_argument("--photos", nargs="+", default=["06", "17", "13"])
    parser.add_argument("--quiet", action="store_true", help="do not print the raw answers")
    args = parser.parse_args()

    problems = keys_look_real()
    if problems:
        sys.exit("\n".join(problems))
    if not prompt_path(args.prompt).exists():
        sys.exit(f"no such prompt file: {prompt_path(args.prompt)}")

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    run_dir = RESULTS / f"smoke_{stamp}_{args.model.replace('/', '_')}_{args.prompt}_t{TEMPERATURE}"   # _t0 = temperature 0
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"model {args.model}, prompt {args.prompt}, photos {args.photos}\nsaving to {run_dir}\n")

    scores, check_list, calls = [], [], []
    for n in args.photos:
        n = photo_number(n)
        record = json.loads(expected_path(n).read_text())
        print(f"=== photo {n}: {record['file']} ({len(record['expected']['items'])} expected items) ===")
        call = read_menu(record["telegram_file"], args.prompt, args.model)
        calls.append({"photo": n, **{k: v for k, v in call.items() if k != "raw_text"}})
        (run_dir / f"menu_{n}_raw.txt").write_text(call["raw_text"] or "")
        if call["error"]:
            print(f"ERROR from the model call: {call['error']}")
        if not args.quiet:
            print("--- raw answer ---")
            print(call["raw_text"])
            print("--- end raw answer ---")
        s = score_answer(record["expected"], record["scoring_hints"], call["raw_text"], photo=n)
        s["seconds"] = call["seconds"]
        s["cost_usd"] = call["cost_usd"]
        s["finish_reason"] = call["finish_reason"]
        scores.append(s)
        check_list.extend(s["check_list"])
        (run_dir / f"menu_{n}_scores.json").write_text(json.dumps(s, indent=1, ensure_ascii=False))
        print(f"time {call['seconds']:.1f}s | tokens in {call['prompt_tokens']} out {call['completion_tokens']} "
              f"| cost {('$%.4f' % call['cost_usd']) if call['cost_usd'] is not None else 'n/a'} | finish {call['finish_reason']}")
        print(f"dishes found {pct(s['dishes_found'])} ({s['found_items']}/{s['expected_items']}) | invented {s['invented']} "
              f"| cut-off listed {s['cut_off_listed']} | prices {pct(s['prices_right'])} | descriptions {pct(s['descriptions_right'])} "
              f"| format {'ok' if s['format_right'] else 'WRONG: ' + s['format_reason']} "
              f"| readable key={s['readable_expected']} model={s['readable_model']}")
        if s["unmatched_expected_names"]:
            print(f"  missing ({len(s['unmatched_expected_names'])}): {s['unmatched_expected_names']}")
        if s["invented_names"]:
            print(f"  invented: {s['invented_names']}")
        if s["cut_off_names"]:
            print(f"  cut-off lines listed anyway: {s['cut_off_names']}")
        if s.get("price_wrong_names"):
            print(f"  wrong prices ({len(s['price_wrong_names'])}): {s['price_wrong_names'][:15]}")
        if s["check_list"]:
            print(f"  check list: {len(s['check_list'])} medium/low key items to look at")
        print()

    summary = {"model": args.model, "prompt": args.prompt, "photos": args.photos, "temperature": TEMPERATURE,
               "max_answer_tokens": MAX_ANSWER_TOKENS, "deadline_seconds": DEADLINE_SECONDS,
               "calls": calls, **summarise(scores)}
    secs = [c["seconds"] for c in calls if c["seconds"] is not None]
    costs = [c["cost_usd"] for c in calls if c["cost_usd"] is not None]
    summary["seconds_avg"] = sum(secs) / len(secs) if secs else None
    summary["cost_total_usd"] = sum(costs) if costs else None
    summary["cost_avg_usd"] = sum(costs) / len(costs) if costs else None
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=1))
    with (run_dir / "check_list.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["photo", "key_confidence", "key_name", "key_price", "model_name", "model_price", "reason"])
        w.writeheader()
        w.writerows(check_list)

    print("=== summary ===")
    print(f"dishes found avg {pct(summary['dishes_found_avg'])}, lowest photo {pct(summary['dishes_found_min'])}")
    print(f"invented total {summary['invented_total']} | cut-off listed {summary['cut_off_listed_total']}")
    print(f"prices {pct(summary['prices_right_avg'])} | descriptions {pct(summary['descriptions_right_avg'])} | format {pct(summary['format_right_avg'])}")
    print(f"bad photos caught {summary['bad_photos_caught']}/{summary['bad_photos_total']} | false alarms {summary['false_alarms']}")
    print(f"tags {pct(summary['tags_right_avg'])} | portion {pct(summary['portion_right_avg'])} | has_choice {pct(summary['has_choice_right_avg'])} | belongs_to {pct(summary['belongs_to_right_avg'])}")
    print(f"speed avg {sum(secs)/len(secs):.1f}s/photo | cost avg {('%.2f cents/photo' % (100*sum(costs)/len(costs))) if costs else 'n/a'} | cost total ${sum(costs):.4f}")
    print(f"check list: {len(check_list)} items -> {run_dir / 'check_list.csv'}")


if __name__ == "__main__":
    main()
