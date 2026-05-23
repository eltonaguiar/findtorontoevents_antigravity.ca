#!/usr/bin/env python3
"""Publish TRACE_LOG.MD findings to alpha_engine_bus."""

import json
import subprocess
from datetime import datetime, timezone

REDIS_CLI = "C:/Users/zerou/redis-bus/redis-cli.exe"
PORT = 6379


def run_redis_cmd(args):
    cmd = [REDIS_CLI, "-p", str(PORT)] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    envelope = {
        "bus_topic": "trace_log_active_smart_verified",
        "from": "kilo-trace-analysis",
        "ts": ts,
        "summary": "TRACE_LOG.MD — pipeline trace (active vs active_raw, smart_picks vs feed, VA rules) + snapshot stats; see repo root file. (Legacy v2 run also noted: 113 active, 0 smart, 47 VA; solo_battleground edge; quan_engine conflicts — confirm against current JSON.)",
        "doc_path_repo_relative": "TRACE_LOG.MD",
        "biggest_missed_edge": "solo_battleground — 60.2% WR, 669 trades, +3101% PnL, Sharpe 1.61, trust_tier=Highly Trusted, but NOT promoted to live picks",
        "action_required": "Review TRACE_LOG.MD; align actions with current dashboard_data.json and REDIS_BUS_CHANGELOG.",
    }
    body = json.dumps(envelope, separators=(",", ":"))
    _, code = run_redis_cmd(["PUBLISH", "alpha_engine_bus", body])
    short = (
        f"trace_log | Smart=0 | solo_battleground 60.2%WR 669 trades NOT live | {ts}"
    )
    run_redis_cmd(["LPUSH", "bus:broadcast:log", short])
    run_redis_cmd(["LTRIM", "bus:broadcast:log", "0", "99"])
    print("[OK]" if code == 0 else "[WARN]", short)
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
