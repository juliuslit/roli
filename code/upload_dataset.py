"""Upload the 25 test examples to a LangSmith dataset.

One example per photo:
  inputs      = which photo (number and file name)
  attachment  = the Telegram-size photo itself (the model will see this)
  reference_outputs = the "expected" block of menu_reader_eval/expected/menu_NN.json
  metadata    = the "scoring_hints" block, plus readable and item count for filtering

Run:   .venv/bin/python code/upload_dataset.py            # uploads (stops if the dataset exists)
       .venv/bin/python code/upload_dataset.py --replace  # deletes the old dataset first
       .venv/bin/python code/upload_dataset.py --dry-run  # builds and checks the 25 examples, no upload
"""
import argparse
import json
import sys

from config import DATASET_NAME, EXPECTED, TEST_SET, keys_look_real


def build_examples() -> list:
    examples = []
    for path in sorted(EXPECTED.glob("menu_*.json")):
        record = json.loads(path.read_text())
        photo_id = path.stem.split("_")[1]                       # "menu_06" -> "06"
        photo_path = TEST_SET / record["telegram_file"]
        if not photo_path.exists():
            sys.exit(f"photo missing: {photo_path}")
        expected = record["expected"]
        examples.append({
            "inputs": {"photo_id": photo_id, "telegram_file": record["telegram_file"]},
            "reference_outputs": expected,
            "metadata": {
                "photo_id": photo_id,
                "expected_readable": expected["readable"],
                "expected_items": len(expected["items"]),
                "scoring_hints": record["scoring_hints"],
            },
            "attachments": {"photo": ("image/jpeg", photo_path.read_bytes())},
        })
    return examples


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--update", action="store_true", help="refresh the examples in place; keeps the dataset id and its experiments")
    parser.add_argument("--replace", action="store_true", help="delete the dataset (and every experiment attached to it) and rebuild")
    parser.add_argument("--dry-run", action="store_true", help="build and validate, do not upload")
    args = parser.parse_args()

    examples = build_examples()
    total_mb = sum(len(e["attachments"]["photo"][1]) for e in examples) / 1e6
    print(f"{len(examples)} examples built, photos total {total_mb:.1f} MB")

    from langsmith import Client
    from langsmith.schemas import ExampleCreate
    for e in examples:                                           # schema check, no network
        ExampleCreate(**e)
    if args.dry_run:
        print("dry run: all 25 examples pass the LangSmith schema check. Nothing uploaded.")
        return

    problems = keys_look_real()
    if any("LANGSMITH" in p for p in problems):
        sys.exit("\n".join(p for p in problems if "LANGSMITH" in p))

    client = Client()
    if client.has_dataset(dataset_name=DATASET_NAME):
        if args.update:
            # Update the 25 examples in place. The dataset keeps its id, so the experiments already
            # attached to it stay visible. (--replace deletes the dataset AND its experiments: the first
            # Haiku batch of 2026-10-29 was lost from LangSmith that way. Prefer --update.)
            existing = {e.inputs["photo_id"]: e for e in client.list_examples(dataset_name=DATASET_NAME)}
            updates = [{"id": existing[e["inputs"]["photo_id"]].id, "inputs": e["inputs"], "outputs": e["reference_outputs"],
                        "metadata": e["metadata"], "attachments": e["attachments"]} for e in examples if e["inputs"]["photo_id"] in existing]
            client.update_examples(dataset_id=existing[next(iter(existing))].dataset_id, updates=updates)
            print(f"updated {len(updates)} of {len(examples)} examples in place in dataset '{DATASET_NAME}' (id kept)")
            return
        if not args.replace:
            sys.exit(f"dataset '{DATASET_NAME}' already exists in LangSmith. Re-run with --update to refresh the examples in place "
                     f"(keeps experiments), or --replace to delete and rebuild it (DELETES every experiment attached to it).")
        client.delete_dataset(dataset_name=DATASET_NAME)
        print(f"deleted old dataset '{DATASET_NAME}' and every experiment attached to it")
    dataset = client.create_dataset(
        DATASET_NAME,
        description="roli menu reader test: 25 Telegram-size menu photos with expected answers and scoring hints.",
    )
    client.create_examples(dataset_id=dataset.id, examples=examples)
    print(f"uploaded {len(examples)} examples to dataset '{DATASET_NAME}' (id {dataset.id})")


if __name__ == "__main__":
    main()
