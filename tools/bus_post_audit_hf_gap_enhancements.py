#!/usr/bin/env python3
"""Publish AUDIT_HF_GAP_AND_ENHANCEMENTS to alpha_engine_bus."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REDIS_CLI = "C:/Users/zerou/redis-bus/redis-cli.exe"
PORT = 6379
REPO = Path(__file__).resolve().parents[1]


def run_redis_cmd(args: list[str]) -> tuple[str, int]:
    cmd = [REDIS_CLI, "-p", str(PORT)] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    envelope = {
        "bus_topic": "AUDIT_HF_GAP_AND_ENHANCEMENTS",
        "topic": "AUDIT_HF_GAP_AND_ENHANCEMENTS",
        "from": "cursor-composer",
        "ts": ts,
        "schema_version": 1,
        "timestamp_utc": ts,
        "summary": (
            "PR docs: audit /audit tabs vs HF-grade pick quality — gaps (Smart funnel anti_overfit, "
            "open-book score~PnL, truth-layer deploy, non-crypto lanes, TCA). P0 observability + CI HTML; "
            "P1 registry/conviction/double-count guard; P2 WF calibration + portfolio + TCA. "
            "Acceptance: pytest quality_gates+hf_gate, smart_gate_funnel on fresh JSON. "
            "See docs/AUDIT_HF_GAP_AND_ENHANCEMENTS_2026-04-08.md"
        ),
        "doc_path_repo_relative": "docs/AUDIT_HF_GAP_AND_ENHANCEMENTS_2026-04-08.md",
        "related_artifacts": [
            "DEFINITIVE_HEDGE_FUND_PIPELINE.md",
            "tools/audit_smart_gate_funnel.py",
            "tools/fetch_audit_dashboard_snapshot.py",
            "tools/bus_post_smart_gate_funnel.py",
        ],
        "public_urls": {
            "audit": "https://findtorontoevents.ca/audit/",
            "updates": "https://findtorontoevents.ca/updates/",
        },
    }
    body = json.dumps(envelope, separators=(",", ":"))
    _, code = run_redis_cmd(["PUBLISH", "alpha_engine_bus", body])
    short = "AUDIT_HF_GAP_AND_ENHANCEMENTS | gap doc + PR | %s" % ts
    run_redis_cmd(["LPUSH", "bus:broadcast:log", short])
    run_redis_cmd(["LTRIM", "bus:broadcast:log", "0", "99"])
    run_redis_cmd(["LPUSH", "bus:alpha_engine_bus:log", body])
    run_redis_cmd(["LTRIM", "bus:alpha_engine_bus:log", "0", "199"])
    print("[OK]" if code == 0 else "[FAIL]", short, flush=True)
    if code != 0:
        print("redis PUBLISH failed — check redis-cli and server", file=sys.stderr)
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
