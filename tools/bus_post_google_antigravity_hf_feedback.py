#!/usr/bin/env python3
"""Publish GOOGLE_ANTIGRAVITY_HF_FEEDBACK to alpha_engine_bus."""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REDIS_CLI = "C:/Users/zerou/redis-bus/redis-cli.exe"
PORT = 6379
REPO = Path(__file__).resolve().parent.parent
DOC = "docs/GOOGLE_ANTIGRAVITY_HF_FEEDBACK_2026-04-02.md"
MERGED = "docs/HF_MERGED_EXECUTION_PLAN_2026-04-02.md"


def run_redis_cmd(args):
    cmd = [REDIS_CLI, "-p", str(PORT)] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    envelope = {
        "bus_topic": "GOOGLE_ANTIGRAVITY_HF_FEEDBACK",
        "topic": "GOOGLE_ANTIGRAVITY_HF_FEEDBACK",
        "schema_version": 1,
        "from": "cursor-composer",
        "ts": ts,
        "timestamp_utc": ts,
        "summary": (
            "Google Antigravity HF guidance merged: alt-data factors, VA 4h+D+W confluence (B6), "
            "VaR risk-parity sizing (B7), regime MR/momentum (B1), MC pre-VA (C5), spread/slippage+D1, "
            "ATR trails A1, walk-forward B2/B5. See docs; canonical phases in HF_MERGED_EXECUTION_PLAN."
        ),
        "doc_path_repo_relative": DOC,
        "related_artifacts": [
            MERGED,
            "HEDGE_FUND_ENHANCEMENT_PLAN.md",
            "audit_trail/dashboard_generator.py",
            "tools/bus_post_hf_merged_execution_plan.py",
        ],
    }
    body = json.dumps(envelope, separators=(",", ":"))
    _, code = run_redis_cmd(["PUBLISH", "alpha_engine_bus", body])
    short = "GOOGLE_ANTIGRAVITY_HF_FEEDBACK | %s" % ts
    run_redis_cmd(["LPUSH", "bus:broadcast:log", short])
    run_redis_cmd(["LTRIM", "bus:broadcast:log", "0", "99"])
    print("[OK]" if code == 0 else "[WARN]", short)
    if code != 0:
        import sys
        print("Envelope:\n", body, file=sys.stderr)
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
