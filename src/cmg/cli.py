"""Command-line interface: ``build``, ``stats`` and ``ask``.

Results print as JSON — agent-ready output a coding agent can parse directly.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, List, Optional

from . import config, queries
from .indexer import build


def _emit(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cmg",
        description="Codebase Memory Graph — relationship-aware agent memory on Relate",
    )
    parser.add_argument("--store", default=config.DEFAULT_STORE,
                        help="Path to the Relate store (default: %(default)s)")
    sub = parser.add_subparsers(dest="command", required=True)

    build_cmd = sub.add_parser("build", help="Index a Python repo into the graph")
    build_cmd.add_argument("repo", help="Path to the repository to index")

    sub.add_parser("stats", help="Show node and edge counts")

    ask = sub.add_parser("ask", help="Query the graph")
    ask_sub = ask.add_subparsers(dest="query", required=True)
    for q in ("callers", "callees"):
        p = ask_sub.add_parser(q, help=f"{q} of a function")
        p.add_argument("name")
    sim = ask_sub.add_parser("similar", help="Functions similar to a given one")
    sim.add_argument("name")
    sim.add_argument("-k", type=int, default=5, help="Max results (default: 5)")
    srch = ask_sub.add_parser("search", help="Hybrid semantic + graph search")
    srch.add_argument("text")
    srch.add_argument("-k", type=int, default=5, help="Max results (default: 5)")

    return parser


def _run_ask(args: argparse.Namespace) -> int:
    if args.query == "callers":
        _emit(queries.callers(args.name, store_path=args.store))
    elif args.query == "callees":
        _emit(queries.callees(args.name, store_path=args.store))
    elif args.query == "similar":
        result = queries.similar(args.name, k=args.k, store_path=args.store)
        if result is None:
            print(f"No function named {args.name!r} in the graph.", file=sys.stderr)
            return 1
        _emit(result)
    elif args.query == "search":
        _emit(queries.search(args.text, k=args.k, store_path=args.store))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "build":
        stats = build(args.repo, store_path=args.store)
        _emit({"status": "ok", "store": args.store, **stats})
        return 0
    if args.command == "stats":
        with queries._open(args.store) as store:  # noqa: SLF001 - internal helper
            _emit(store.stats())
        return 0
    if args.command == "ask":
        return _run_ask(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
