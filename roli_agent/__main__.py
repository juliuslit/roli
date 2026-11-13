"""Command line: .venv/bin/python -m roli_agent "cooked chinook salmon"  [--photo menu.jpg] [--recipe recipe.json] [--trace]"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time

from .graph import run_roli


def main() -> int:
    parser = argparse.ArgumentParser(prog="roli_agent")
    parser.add_argument("text", nargs="?", default="", help="the user's message")
    parser.add_argument("--photo", help="path to a menu photo")
    parser.add_argument("--recipe", help="path to a JSON recipe (spec 2A, section 3); takes the calculator path, no LLM")
    parser.add_argument("--dish", help='a menu item as JSON, e.g. \'{"name": "BLUEFIN CRUDO", "description": "bottarga, muscat grape, chive", "section": "TO START"}\'')
    parser.add_argument("--trace", action="store_true", help="print the step trace and state summary")
    parser.add_argument("--json", action="store_true", help="print the full final state as JSON")
    args = parser.parse_args()
    if not args.text and not args.photo and not args.recipe and not args.dish:
        parser.error("give a message, a --photo, a --recipe, a --dish, or a combination")
    recipe = json.loads(open(args.recipe, encoding="utf-8").read()) if args.recipe else None
    menu_item = json.loads(args.dish) if args.dish else None

    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    started = time.perf_counter()
    out = run_roli(args.text, args.photo, recipe=recipe, menu_item=menu_item)
    seconds = time.perf_counter() - started

    print(out["response"])
    if args.trace:
        print("\n--- trace ---")
        for line in out["state"].get("trace", []):
            print(line)
        print(f"--- {seconds:.1f} s ---")
    if args.json:
        print(json.dumps(out["state"], indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
