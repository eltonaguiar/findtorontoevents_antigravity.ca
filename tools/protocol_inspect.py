#!/usr/bin/env python3
"""Debug inspector for cross-PC protocol gateway and event log."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cross_pc_protocol.storage import EventStore


def _print_json(payload: Dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect cross-PC protocol state")
    parser.add_argument("--http-base", default="http://127.0.0.1:8788")
    parser.add_argument("--event-log", default="logs/cross_pc_protocol/events.jsonl")
    sub = parser.add_subparsers(dest="mode", required=True)

    tail_p = sub.add_parser("tail")
    tail_p.add_argument("--limit", type=int, default=20)
    tail_p.add_argument("--topic", default="")

    trace_p = sub.add_parser("trace")
    trace_p.add_argument("--trace-id", required=True)
    trace_p.add_argument("--limit", type=int, default=500)
    trace_p.add_argument("--source", choices=["http", "log"], default="http")

    replay_p = sub.add_parser("replay")
    replay_p.add_argument("--trace-id", required=True)
    replay_p.add_argument("--limit", type=int, default=500)

    health_p = sub.add_parser("health")
    _ = health_p

    args = parser.parse_args()
    store = EventStore(Path(args.event_log))

    if args.mode == "tail":
        _print_json({"ok": True, "events": store.tail(limit=args.limit, topic=args.topic)})
        return 0

    if args.mode == "trace":
        if args.source == "log":
            _print_json({"ok": True, "events": store.by_trace_id(args.trace_id, limit=args.limit)})
            return 0
        response = requests.get(
            f"{args.http_base}/replay",
            params={"trace_id": args.trace_id, "limit": args.limit},
            timeout=10,
        )
        response.raise_for_status()
        _print_json(response.json())
        return 0

    if args.mode == "replay":
        response = requests.get(
            f"{args.http_base}/replay",
            params={"trace_id": args.trace_id, "limit": args.limit},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        events = data.get("events", [])
        _print_json({"ok": True, "trace_id": args.trace_id, "replayed_events": len(events), "events": events})
        return 0

    response = requests.get(f"{args.http_base}/health", timeout=10)
    response.raise_for_status()
    _print_json(response.json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
