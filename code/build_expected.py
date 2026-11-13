"""Rebuild menu_reader_eval/expected/, expected_outputs.jsonl and scoring_hints.csv from the key.

Sources (the answer key is the source of truth; never edit the JSON by hand):
  menu_test_set/answer_key.csv              one row per item
  menu_test_set/answer_key_photo_notes.csv  cut_off_lines_left_out per photo
  menu_reader_eval/photo_level.csv          readable + problems per photo

Run:  .venv/bin/python code/build_expected.py --check   # compare with the files on disk, write nothing
      .venv/bin/python code/build_expected.py           # write the files
"""
import argparse
import csv
import json

from config import EVAL, EXPECTED, TEST_SET

ITEM_FIELDS = ["section", "category", "name", "description", "price", "tags", "portion", "has_choice", "belongs_to"]


def split_list(text: str) -> list:
    return [x.strip() for x in (text or "").split(";") if x.strip()]


def build_records() -> list:
    key = list(csv.DictReader(open(TEST_SET / "answer_key.csv", encoding="utf-8")))
    notes = {r["file"]: r for r in csv.DictReader(open(TEST_SET / "answer_key_photo_notes.csv", encoding="utf-8"))}
    level = {r["file"]: r for r in csv.DictReader(open(EVAL / "photo_level.csv", encoding="utf-8"))}
    files = []
    for r in key:
        if r["file"] not in files:
            files.append(r["file"])
    records = []
    for file in files:
        rows = [r for r in key if r["file"] == file]
        records.append({
            "file": file,
            "telegram_file": f"telegram_1280/{file}",
            "expected": {
                "readable": level[file]["readable"],
                "problems": level[file]["problems"],
                "items": [{f: r[f] for f in ITEM_FIELDS} for r in rows],
            },
            "scoring_hints": {
                "cut_off_lines_left_out": split_list(notes[file]["cut_off_lines_left_out"]),
                "low_confidence_items": [r["name"] for r in rows if r["confidence"] == "low"],
                "medium_confidence_items": [r["name"] for r in rows if r["confidence"] == "medium"],
            },
        })
    return records


def render(records: list) -> dict:
    """{relative path: text} for every file this script owns."""
    out = {}
    for n, rec in enumerate(records, 1):
        out[f"expected/menu_{n:02d}.json"] = json.dumps(rec, indent=1, ensure_ascii=False)
    out["expected_outputs.jsonl"] = "".join(json.dumps(rec, ensure_ascii=False) + "\n" for rec in records)
    lines = ["file,expected_readable,items,cut_off_lines_left_out,medium_confidence_items,low_confidence_items"]
    import io
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["file", "expected_readable", "items", "cut_off_lines_left_out", "medium_confidence_items", "low_confidence_items"])
    for rec in records:
        h = rec["scoring_hints"]
        w.writerow([rec["file"], rec["expected"]["readable"], len(rec["expected"]["items"]),
                    "; ".join(h["cut_off_lines_left_out"]), "; ".join(h["medium_confidence_items"]),
                    "; ".join(h["low_confidence_items"])])
    out["scoring_hints.csv"] = buf.getvalue()
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="compare with the files on disk, write nothing")
    args = parser.parse_args()
    files = render(build_records())
    changed = []
    for rel, text in files.items():
        path = EVAL / rel
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current != text:
            changed.append(rel)
            if not args.check:
                path.write_text(text, encoding="utf-8")
    total = sum(len(r["expected"]["items"]) for r in build_records())
    if args.check:
        print(f"{len(files)} files rendered, {total} items; differ from disk: {changed or 'none'}")
    else:
        print(f"{len(files)} files rendered, {total} items; written: {changed or 'none (all identical)'}")


if __name__ == "__main__":
    main()
