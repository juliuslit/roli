"""Fold a re-run of a few photos into an existing results folder.

Run:  .venv/bin/python code/splice_rerun.py <original folder> <re-run folder> "<why>"

Copies run*/menu_NN_raw.txt and menu_NN_scores.json for every photo present in the re-run folder over the
originals, replaces those photos' entries in the original summary.json "calls" list, and records the splice
under summary["reruns"] (photo, rep, source folder, reason, old and new call stats). The replaced raw answers
are kept next to the originals as menu_NN_raw_before_rerun.txt. Scores are re-derived by rescore.py afterwards.
"""
import json
import shutil
import sys
from pathlib import Path


def splice(original: Path, rerun: Path, why: str) -> list:
    summary = json.loads((original / "summary.json").read_text())
    rerun_summary = json.loads((rerun / "summary.json").read_text())
    new_calls = {(c["photo"], c["rep"]): c for c in rerun_summary["calls"]}
    done = []
    for raw in sorted(rerun.glob("run*/menu_*_raw.txt")):
        rep_dir, photo = raw.parent.name, raw.stem[5:7]
        rep = int(rep_dir[3:])
        target = original / rep_dir / raw.name
        if target.exists():
            shutil.copy(target, target.with_name(f"menu_{photo}_raw_before_rerun.txt"))
        shutil.copy(raw, target)
        scores = raw.with_name(f"menu_{photo}_scores.json")
        if scores.exists():
            shutil.copy(scores, original / rep_dir / scores.name)
        old = next((c for c in summary["calls"] if c["photo"] == photo and c["rep"] == rep), None)
        new = new_calls.get((photo, rep))
        summary["calls"] = [c for c in summary["calls"] if not (c["photo"] == photo and c["rep"] == rep)] + ([new] if new else [])
        summary.setdefault("reruns", []).append({"photo": photo, "rep": rep, "source": str(rerun), "reason": why,
                                                 "old_call": old, "new_call": new,
                                                 "max_answer_tokens": rerun_summary.get("max_answer_tokens")})
        done.append((photo, rep))
    summary["calls"].sort(key=lambda c: (c["rep"], c["photo"]))
    (original / "summary.json").write_text(json.dumps(summary, indent=1))
    return done


if __name__ == "__main__":
    print("spliced", splice(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]))
