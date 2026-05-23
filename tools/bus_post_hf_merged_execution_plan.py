#!/usr/bin/env python3
"""Publish HF_MERGED_EXECUTION_PLAN to alpha_engine_bus (canonical merged HF roadmap)."""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REDIS_CLI = "C:/Users/zerou/redis-bus/redis-cli.exe"
PORT = 6379
REPO = Path(__file__).resolve().parent.parent
DOC = "docs/HF_MERGED_EXECUTION_PLAN_2026-04-02.md"


def run_redis_cmd(args):
    cmd = [REDIS_CLI, "-p", str(PORT)] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    envelope = {
        "bus_topic": "HF_MERGED_EXECUTION_PLAN",
        "topic": "HF_MERGED_EXECUTION_PLAN",
        "schema_version": 1,
        "from": "cursor-composer",
        "ts": ts,
        "timestamp_utc": ts,
        "summary": (
            "Merged HF execution plan: external audit + AUDIT_HF_MULTICLASS + HEDGE_FUND_ENHANCEMENT_PLAN + "
            "Google Antigravity (B6–B7 VA/MTF/VaR, C4–C5 alt-data/MC, D1 TCA). Phases A–D. "
            "Peers: §8 or HF_MERGED_PLAN_PEER_APPEND. See also GOOGLE_ANTIGRAVITY_HF_FEEDBACK."
        ),
        "doc_path_repo_relative": DOC,
        "related_artifacts": [
            "docs/AUDIT_HF_MULTICLASS_FLEET_REVIEW_2026-04-07.md",
            "HEDGE_FUND_ENHANCEMENT_PLAN.md",
            "EDGE_ADDENDUM.md",
            "docs/AUDIT_CRYPTO_PREDICTION_TP_SL_QUALITY_2026-04-02.md",
            "audit_trail/quality_gates.py",
            "audit_trail/dashboard_generator.py",
            "tools/bus_post_audit_hf_multiclass_review.py",
            "docs/GOOGLE_ANTIGRAVITY_HF_FEEDBACK_2026-04-02.md",
            "tools/bus_post_google_antigravity_hf_feedback.py",
        ],
        "coordination": {
            "peer_append_topic": "HF_MERGED_PLAN_PEER_APPEND",
            "canonical_doc": DOC,
            "claude_handoff_section": "## 6. Claude Code agent checklist",
        },
    }
    body = json.dumps(envelope, separators=(",", ":"))
    _, code = run_redis_cmd(["PUBLISH", "alpha_engine_bus", body])
    short = "HF_MERGED_EXECUTION_PLAN | %s" % ts
    run_redis_cmd(["LPUSH", "bus:broadcast:log", short])
    run_redis_cmd(["LTRIM", "bus:broadcast:log", "0", "99"])
    print("[OK]" if code == 0 else "[WARN]", short)
    if code != 0:
        import sys
        print("Envelope:\n", body, file=sys.stderr)
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
