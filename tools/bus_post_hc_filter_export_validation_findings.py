#!/usr/bin/env python3
"""Publish HC filter empirical CSV validation summary to alpha_engine_bus."""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REDIS_CLI = "C:/Users/zerou/redis-bus/redis-cli.exe"
PORT = 6379
REPO = Path(__file__).resolve().parent.parent
TOPIC = "HC_FILTER_EXPORT_VALIDATION_FINDINGS"
PRIMARY_DOC = "docs/HC_FILTER_POST_PLAN_E2E.md"


def run_redis_cmd(args: list[str]) -> tuple[str, int]:
    cmd = [REDIS_CLI, "-p", str(PORT)] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    envelope = {
        "bus_topic": TOPIC,
        "topic": TOPIC,
        "schema_version": 1,
        "from": "cursor-composer",
        "ts": ts,
        "timestamp_utc": ts,
        "summary": (
            "HC_FILTER_EXPORT_VALIDATION_FINDINGS: Plan doc enhanced (HC_FILTER_POST_PLAN_E2E.md §5.1) with "
            "2026-04-09 antigravity CSV snapshot. CLOSED n=3430: ~47% WR book (coin-toss); PROVEN ~69% WR +0.96% avg "
            "vs SANDBOX ~27% -1.26% vs PROBATION ~42%; Grade A ~83% WR; CRYPTO bulk ~50% WR, EQUITY/FOREX weaker in window. "
            "ACTIVE n=90 vs dashboard_hc_rules: 7/90 (~8%) pass HC funnel; 0 HC for SANDBOX/PROBATION/WATCH sample; 6/7 PROVEN pass. "
            "Tool: tools/analyze_antigravity_picks_export.py (--closed/--active/--all-picks). "
            "Limits: closed CSV lacks full consensus/regime for Gate 8 replay; ensure forward fields in live payloads."
        ),
        "doc_path_repo_relative": PRIMARY_DOC,
        "related_artifacts": [
            PRIMARY_DOC,
            "tools/analyze_antigravity_picks_export.py",
            "tools/dashboard_hc_rules.py",
            "audit_dashboard/hc_filter.js",
            "config/hc_gate_params.json",
        ],
        "coordination": {
            "peer_append_topic": "HF_MERGED_PLAN_PEER_APPEND",
            "snapshot_date": "2026-04-09",
        },
    }
    body = json.dumps(envelope, separators=(",", ":"))
    _, code_pub = run_redis_cmd(["PUBLISH", "alpha_engine_bus", body])
    short = "%s | %s | see %s" % (TOPIC, ts, PRIMARY_DOC)
    _, code_push = run_redis_cmd(["LPUSH", "bus:broadcast:log", short])
    run_redis_cmd(["LTRIM", "bus:broadcast:log", "0", "99"])
    ok = code_pub == 0 and code_push == 0
    print("[OK]" if ok else "[WARN]", short)
    if code_pub != 0:
        print("PUBLISH: redis may be down or redis-cli missing.", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
