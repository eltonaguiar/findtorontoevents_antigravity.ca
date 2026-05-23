#!/usr/bin/env python3
"""Publish HF audit strict gates + macro/risk/dashboard progress to alpha_engine_bus."""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REDIS_CLI = "C:/Users/zerou/redis-bus/redis-cli.exe"
PORT = 6379
REPO = Path(__file__).resolve().parent.parent
PRIMARY_DOC = "docs/HF_MERGED_EXECUTION_PLAN_2026-04-02.md"


def run_redis_cmd(args: list[str]) -> tuple[str, int]:
    cmd = [REDIS_CLI, "-p", str(PORT)] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    envelope = {
        "bus_topic": "HF_AUDIT_STRICT_GATES_PROGRESS",
        "topic": "HF_AUDIT_STRICT_GATES_PROGRESS",
        "schema_version": 1,
        "from": "cursor-composer",
        "ts": ts,
        "timestamp_utc": ts,
        "summary": (
            "HF action plan §2 implementation (audit path): optional /audit Smart overlay "
            "config/hf_audit_smart_strict.json (default OFF)—elite>=80, R:R>=2.5, 4h freshness, "
            "WATCH+ trust, MTF 2/3, macro when snapshot has series; wired via audit_trail/hf_strict_smart_gate.py "
            "at end of _smart_gate_fail_after_active. Separate from alpha_engine config/hf_quality_gates.json "
            "(engine post-score, also default OFF). Macro: linear overlay from alpha_engine/data/macro_regression_weights.json "
            "when weights populated; by_asset_class still wins. Risk: get_atr_stop_multiplier() in risk_policy_loader. "
            "Dashboard: payload.hf_weekly_audit from hf_weekly_audit_report.json. Tests: test_hf_audit_strict_smart_gate, "
            "test_macro_overlay_score, test_risk_policy_loader ATR."
        ),
        "doc_path_repo_relative": PRIMARY_DOC,
        "related_artifacts": [
            "config/hf_audit_smart_strict.json",
            "audit_trail/hf_strict_smart_gate.py",
            "audit_trail/quality_gates.py",
            "alpha_engine/macro_overlay_score.py",
            "alpha_engine/data/macro_regression_weights.json",
            "alpha_engine/risk_policy_loader.py",
            "audit_trail/dashboard_generator.py",
            "config/hf_quality_gates.json",
            "alpha_engine/hf_quality_gate.py",
            "HEDGE_FUND_QUALITY_ROADMAP.md",
        ],
        "coordination": {
            "similar_prior_bus": [
                "HF_MERGED_EXECUTION_PLAN",
                "GOOGLE_ANTIGRAVITY_HF_FEEDBACK",
                "AUDIT_HIGH_CERTAINTY_ROLLOUT",
                "GOLDEN_STANDARD_ACTION_PLAN_RECONCILIATION",
            ],
            "not_duplicate": (
                "This is additive optional tightening + plumbing; does not replace SMART_PICKS_MIN_RR=1.5 baseline. "
                "Strict R:R 2.5 applies only when hf_audit_smart_strict or hf_quality_gates enabled."
            ),
            "reconcile_with_golden_reconciliation": (
                "GOLDEN_STANDARD_ACTION_PLAN_RECONCILIATION warned elite 71-80 sweet spot vs full removal. "
                "audit strict elite>=80 stays DISABLED by default—enable only after backtest validation; "
                "no conflict with edge-map if left off."
            ),
            "peer_append_topic": "HF_MERGED_PLAN_PEER_APPEND",
        },
    }
    body = json.dumps(envelope, separators=(",", ":"))
    _, code_pub = run_redis_cmd(["PUBLISH", "alpha_engine_bus", body])
    short = "HF_AUDIT_STRICT_GATES_PROGRESS | %s | see envelope on alpha_engine_bus" % ts
    _, code_push = run_redis_cmd(["LPUSH", "bus:broadcast:log", short])
    run_redis_cmd(["LTRIM", "bus:broadcast:log", "0", "99"])
    ok = code_pub == 0 and code_push == 0
    print("[OK]" if ok else "[WARN]", short)
    if code_pub != 0:
        print("PUBLISH stderr: redis may have no subscribers (message still attempted).", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
