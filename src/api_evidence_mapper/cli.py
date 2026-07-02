from __future__ import annotations

import argparse
import json
import sys

from .config import load_config
from .pipeline import run_all


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a Postman collection and migration mapping from local API evidence.")
    sub = parser.add_subparsers(dest="command", required=True)
    all_parser = sub.add_parser("all", help="Run offline scan, reconciliation, and artifact generation")
    all_parser.add_argument("--config", required=True, help="Path to project TOML configuration")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "all":
        result = run_all(load_config(args.config))
        print(json.dumps(result, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
