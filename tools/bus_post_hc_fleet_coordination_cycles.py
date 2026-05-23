#!/usr/bin/env python3
"""Publish N Redis bus coordination cycles to alpha_engine_bus (fleet / peer agents)."""

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

REDIS_CLI = "C:/Users/zerou/redis-bus/redis-cli.exe"
PORT = 6379
REPO = Path(__file__).resolve().parent.parent
CHANNEL = "alpha_engine_bus"
TOPIC = "HC_FILTER_FLEET_COORD_CYCLE"


def run_redis_cmd(args: list[str]) -> tuple[str, int]:
    cmd = [REDIS_CLI, "-p", str(PORT)] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode


def publish_cycle(cycle: int, total: int) -> bool:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    envelope = {
        "bus_topic": TOPIC,
        "topic": TOPIC,
        "schema_version": 1,
        "from": "cursor-composer",
        "ts": ts,
        "timestamp_utc": ts,
        "summary": (
            "HC filter v3 fleet coordination: cycle %d/%d — Gate 9 + filterHighConvictionOrdered "
            "shipped on branch fix/high-conviction-filter-v2 (commit area: hc_filter.js, "
            "dashboard_hc_rules.py, corrPairs). Peers: poll validate_dashboard_parity / "
            "node tests/test_hc_filter.js if touching HC paths. Use HF_MERGED_PLAN_PEER_APPEND for claims."
            % (cycle, total)
        ),
        "doc_path_repo_relative": "audit_dashboard/hc_filter.js",
        "related_artifacts": [
            "audit_dashboard/hc_filter.js",
            "tools/dashboard_hc_rules.py",
            "config/hc_gate_params.json",
        ],
        "coordination": {
            "cycle": cycle,
            "total_cycles": total,
            "peer_append_topic": "HF_MERGED_PLAN_PEER_APPEND",
            "redis_log_key": "bus:broadcast:log",
        },
    }
    body = json.dumps(envelope, separators=(",", ":"))
    _, code_pub = run_redis_cmd(["PUBLISH", CHANNEL, body])
    short = "%s | cycle %d/%d | %s" % (TOPIC, cycle, total, ts)
    _, code_push = run_redis_cmd(["LPUSH", "bus:broadcast:log", short])
    run_redis_cmd(["LTRIM", "bus:broadcast:log", "0", "99"])
    ok = code_pub == 0 and code_push == 0
    print("[OK]" if ok else "[WARN]", short)
    return ok


def main() -> int:
    total = 3
    all_ok = True
    for c in range(1, total + 1):
        if not publish_cycle(c, total):
            all_ok = False
        if c < total:
            time.sleep(0.35)
    if not all_ok:
        print("PUBLISH: one or more cycles failed (redis down or redis-cli missing).", flush=True)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
