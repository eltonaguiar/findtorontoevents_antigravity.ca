#!/usr/bin/env python3
"""Publish AUDIT_PICKS_EDGE_ANALYSIS to alpha_engine_bus."""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REDIS_CLI = "C:/Users/zerou/redis-bus/redis-cli.exe"
PORT = 6379
REPO = Path(__file__).resolve().parent.parent
ARTIFACT = REPO / "tools" / "data" / "audit_active_book_analysis.json"


def run_redis_cmd(args):
    cmd = [REDIS_CLI, "-p", str(PORT)] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    key_stats = {}
    if ARTIFACT.is_file():
        with open(ARTIFACT, "r", encoding="utf-8") as f:
            data = json.load(f)
        agg = data.get("aggregate_active_unrealized") or {}
        key_stats = {
            "active_count": data.get("active_count"),
            "unrealized_sum_pct": agg.get("unrealized_sum_pct"),
            "unrealized_mean_pct": agg.get("unrealized_mean_pct"),
            "smart_picks_count": data.get("smart_picks_count"),
            "va_active_count": (data.get("verified_alpha_summary_counts") or {}).get(
                "active_count"
            ),
        }
    envelope = {
        "bus_topic": "AUDIT_PICKS_EDGE_ANALYSIS",
        "from": "cursor-composer",
        "ts": ts,
        "summary": (
            "Active book n=110: pick unrealized sum +92pct; payload systems unrealized sum +110pct (rollup cross-check). "
            "Open-book score vs PnL Spearman ~0; closed n=3500 score IC ~0.24. "
            "smart_picks=0; strategy rows now include n_closed_30d/90d. "
            "Doc: docs/AUDIT_PICKS_EDGE_ANALYSIS_2026-04-06.md; fetch: tools/fetch_audit_dashboard_snapshot.py"
        ),
        "doc_path_repo_relative": "docs/AUDIT_PICKS_EDGE_ANALYSIS_2026-04-06.md",
        "related_artifacts": [
            "tools/data/audit_active_book_analysis.json",
            "tools/data/score_pnl_analysis.json",
            "tools/analyze_audit_active_book.py",
        ],
        "key_stats": key_stats,
        "action_required": (
            "Read the MD; use closed-book IC for scoring calibration; tighten non-crypto or reduce surface; "
            "investigate smart_picks=0 and strategy label alignment for history lookup."
        ),
    }
    body = json.dumps(envelope, separators=(",", ":"))
    _, code = run_redis_cmd(["PUBLISH", "alpha_engine_bus", body])
    short = "AUDIT_PICKS_EDGE_ANALYSIS | %s" % ts
    run_redis_cmd(["LPUSH", "bus:broadcast:log", short])
    run_redis_cmd(["LTRIM", "bus:broadcast:log", "0", "99"])
    print("[OK]" if code == 0 else "[WARN]", short)
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
