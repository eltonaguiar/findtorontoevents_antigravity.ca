#!/usr/bin/env python3
"""Publish HC filter v3 Gate 9 (correlation) + ordered filter completion to alpha_engine_bus."""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REDIS_CLI = "C:/Users/zerou/redis-bus/redis-cli.exe"
PORT = 6379
REPO = Path(__file__).resolve().parent.parent


def run_redis_cmd(args: list[str]) -> tuple[str, int]:
    cmd = [REDIS_CLI, "-p", str(PORT)] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    envelope = {
        "bus_topic": "HC_FILTER_V3_GATE9_ORDERED_FILTER",
        "topic": "HC_FILTER_V3_GATE9_ORDERED_FILTER",
        "schema_version": 1,
        "from": "cursor-composer",
        "ts": ts,
        "timestamp_utc": ts,
        "summary": (
            "HC filter v3: Gate 9 (correlated crypto pairs, same-direction dedup) wired in "
            "audit_dashboard/hc_filter.js + tools/dashboard_hc_rules.py; "
            "filterHighConvictionOrdered / filter_high_conviction_ordered replaces raw .filter() "
            "so batch order registers globalThis._hcPassedSyms. config/hc_gate_params.json has corrPairs. "
            "audit_dashboard/index.html aligned with template. Parity: passes_high_conviction_pick(..., passed_registry=) for ordered Python."
        ),
        "doc_path_repo_relative": "audit_dashboard/hc_filter.js",
        "related_artifacts": [
            "audit_dashboard/hc_filter.js",
            "tools/dashboard_hc_rules.py",
            "config/hc_gate_params.json",
            "audit_dashboard/template.html",
            "audit_dashboard/index.html",
            "tests/test_hc_filter.js",
            "tests/test_dashboard_hc_rules.py",
        ],
        "coordination": {
            "peer_append_topic": "HF_MERGED_PLAN_PEER_APPEND",
            "plan_hint": "hc_filter_rewrite_v2 — Gate 9 + index parity closed",
        },
    }
    body = json.dumps(envelope, separators=(",", ":"))
    _, code_pub = run_redis_cmd(["PUBLISH", "alpha_engine_bus", body])
    short = "HC_FILTER_V3_GATE9_ORDERED_FILTER | %s | see envelope" % ts
    _, code_push = run_redis_cmd(["LPUSH", "bus:broadcast:log", short])
    run_redis_cmd(["LTRIM", "bus:broadcast:log", "0", "99"])
    ok = code_pub == 0 and code_push == 0
    print("[OK]" if ok else "[WARN]", short)
    if code_pub != 0:
        print("PUBLISH: redis may be down or redis-cli missing.", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
