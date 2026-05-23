#!/usr/bin/env python3
"""Publish EXTERNAL_QUANT_FEEDBACK_COLLECTED to alpha_engine_bus."""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REDIS_CLI = "C:/Users/zerou/redis-bus/redis-cli.exe"
PORT = 6379
REPO = Path(__file__).resolve().parent.parent
DOC = "docs/EXTERNAL_QUANT_FEEDBACK_COLLECTED_2026-04-07.md"


def run_redis_cmd(args):
    cmd = [REDIS_CLI, "-p", str(PORT)] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    envelope = {
        "bus_topic": "EXTERNAL_QUANT_FEEDBACK_COLLECTED",
        "topic": "EXTERNAL_QUANT_FEEDBACK_COLLECTED",
        "schema_version": 1,
        "from": "cursor-composer",
        "ts": ts,
        "timestamp_utc": ts,
        "summary": (
            "Collected external quant feedback: Xiaomi Mimo dashboard_data.json audit (goldmine/sports leak, "
            "score/PnL inversion actives, suspicious consensus stats, ml_bg+mega_mutation kill list, "
            "regime_validation 0 actives w regime_alignment, decay alerts no auto-action, closed deciles, "
            "TRX/rapid_fire). Index links Google Antigravity + HF_MERGED + multiclass + score reviews."
        ),
        "doc_path_repo_relative": DOC,
        "related_artifacts": [
            "docs/GOOGLE_ANTIGRAVITY_HF_FEEDBACK_2026-04-02.md",
            "docs/HF_MERGED_EXECUTION_PLAN_2026-04-02.md",
            "audit_trail/dashboard_generator.py",
            "audit_trail/quality_gates.py",
            "alpha_engine/smart_picks_engine.py",
        ],
        "reviewer_label": "xiaomi_mimo",
    }
    body = json.dumps(envelope, separators=(",", ":"))
    _, code = run_redis_cmd(["PUBLISH", "alpha_engine_bus", body])
    short = "EXTERNAL_QUANT_FEEDBACK_COLLECTED | %s" % ts
    run_redis_cmd(["LPUSH", "bus:broadcast:log", short])
    run_redis_cmd(["LTRIM", "bus:broadcast:log", "0", "99"])
    print("[OK]" if code == 0 else "[WARN]", short)
    if code != 0:
        import sys
        print("Envelope:\n", body, file=sys.stderr)
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
