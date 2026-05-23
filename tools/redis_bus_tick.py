#!/usr/bin/env python3
"""Redis agent bus: status heartbeat, drain inbox, append broadcast.

Single tick (default): run once from Cursor or CI.
Repeating: ``python tools/redis_bus_tick.py --interval-sec 900`` (~15 min traction loop).

Requires Redis on localhost:6379 (same as redis_agent_handshake / peer scripts).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone

import redis

DEFAULT_AGENT_ID = "cursor-audit-quant"
DEFAULT_SUMMARY = (
    "Audit/quant: PnL sum vs EW compound (dashboard + purged clean_metrics); "
    "poll inbox/broadcast; see PEER_WORK_AUDIT_DASHBOARD_QUANT.md"
)


def _txt(blob: str | bytes | None) -> str:
    if blob is None:
        return ""
    if isinstance(blob, str):
        return blob
    return blob.decode("utf-8", errors="replace")


def tick(client: redis.Redis, agent_id: str, summary: str, print_peers: bool) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    client.hset(
        f"agent:{agent_id}:status",
        mapping={
            "summary": summary,
            "cwd": "E:/findtorontoevents_antigravity.ca",
            "last_seen": now,
            "tool": "cursor",
        },
    )
    client.expire(f"agent:{agent_id}:status", 3600)

    if print_peers:
        print("=== PEERS (agent:*:status) ===", flush=True)
        for k in sorted(client.keys("agent:*:status")):
            kh = _txt(k)
            row = client.hgetall(k)
            decoded = {_txt(a): _txt(b) for a, b in row.items()}
            print(kh, json.dumps(decoded, indent=2), flush=True)

    inbox_key = f"agent:{agent_id}:inbox"
    inbox = client.lrange(inbox_key, 0, -1)
    if inbox:
        print("=== INBOX (cleared) ===", flush=True)
        for m in inbox:
            print(_txt(m), flush=True)
        client.ltrim(inbox_key, 1, 0)

    print("=== BROADCAST (latest 6) ===", flush=True)
    for m in client.lrange("bus:broadcast:log", 0, 5):
        print(_txt(m), flush=True)

    msg = json.dumps(
        {
            "from": agent_id,
            "timestamp": now,
            "body": summary[:1400],
        }
    )
    client.lpush("bus:broadcast:log", msg)
    client.ltrim("bus:broadcast:log", 0, 99)
    print("=== Tick OK ===", flush=True)


def main() -> int:
    p = argparse.ArgumentParser(description="Redis bus heartbeat / inbox drain")
    p.add_argument(
        "--agent-id",
        default=DEFAULT_AGENT_ID,
        dest="agent_id",
        help="Redis key agent:<id>:status / inbox",
    )
    p.add_argument("--summary", default=DEFAULT_SUMMARY, help="Status + broadcast body")
    p.add_argument(
        "--interval-sec",
        type=int,
        default=0,
        help="If >0, repeat every N seconds (900 = 15 minutes)",
    )
    p.add_argument(
        "--peers",
        action="store_true",
        help="List all agent:*:status hashes",
    )
    args = p.parse_args()

    try:
        # decode_responses=False: bus log may contain legacy non-UTF8 bytes
        r = redis.Redis(host="localhost", port=6379, decode_responses=False)
        r.ping()
    except redis.ConnectionError as e:
        print(f"Redis unavailable: {e}", file=sys.stderr)
        return 2

    if args.interval_sec <= 0:
        tick(r, args.agent_id, args.summary, args.peers)
        return 0

    print(
        f"Polling bus every {args.interval_sec}s (Ctrl+C to stop)",
        file=sys.stderr,
        flush=True,
    )
    while True:
        tick(r, args.agent_id, args.summary, args.peers)
        time.sleep(args.interval_sec)


if __name__ == "__main__":
    raise SystemExit(main())
