#!/usr/bin/env python3
"""Publish closed-pick lessons + scoring recommendations to alpha_engine_bus."""

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
        "bus_topic": "CLOSED_PICKS_LESSONS_SCORING",
        "from": "cursor-composer",
        "ts": ts,
        "summary": (
            "3500 closed picks: SMART tier 77% WR / +1.43% mean vs REJECTED 38% WR; "
            "smart_score Q5 73.7% WR vs Q1 37.1%; crypto Q5 74.6% WR. "
            "elite_score Spearman 0.35 non-crypto vs 0.14 crypto — weight elite up off-crypto, "
            "smart_score primary crypto. confidence ~flat vs pnl (rho~0.09) — shrink weight. "
            "EQUITY mean pnl -0.78% (n=471) — tighter gates/allowlist. "
            "Recommend rolling strategy expectancy penalties, non-linear smart tiers, KPI: Q5-Q1 spread."
        ),
        "doc_path_repo_relative": "docs/CLOSED_PICKS_LESSONS_SCORING_2026-04-07.md",
        "related_docs": [
            "tools/data/score_pnl_analysis.json",
            "audit_dashboard/SCORE_PNL_EDGE_REVIEW_2026-04.md",
        ],
        "key_findings": {
            "n_recent_closed": 3500,
            "n_crypto": 2855,
            "n_non_crypto": 645,
            "smart_tier_win_rate_pct": 77.38,
            "rejected_win_rate_pct": 37.96,
            "proven_win_rate_pct": 63.12,
            "smart_score_q5_win_rate_pct_all": 73.71,
            "smart_score_q5_win_rate_pct_crypto": 74.61,
            "spearman_smart_score_pnl_crypto": 0.23165,
            "spearman_elite_pnl_crypto": 0.13566,
            "spearman_elite_pnl_non_crypto": 0.35053,
            "spearman_confidence_pnl_all": 0.09266,
            "equity_closed_mean_pnl_pct_approx": -0.78,
            "equity_closed_n": 471,
        },
        "action_required": (
            "Read docs/CLOSED_PICKS_LESSONS_SCORING_2026-04-07.md; adjust quality_gates / "
            "elite weights by asset class; shrink confidence; add rolling strategy penalties."
        ),
    }
    body = json.dumps(envelope, separators=(",", ":"))
    _, code = run_redis_cmd(["PUBLISH", "alpha_engine_bus", body])
    short = "CLOSED_PICKS_LESSONS_SCORING | scoring memo | %s" % ts
    run_redis_cmd(["LPUSH", "bus:broadcast:log", short])
    run_redis_cmd(["LTRIM", "bus:broadcast:log", "0", "99"])
    print("[OK]" if code == 0 else "[WARN]", short)
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
