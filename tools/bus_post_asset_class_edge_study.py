#!/usr/bin/env python3
"""Publish asset-class edge & scoring flaws study to alpha_engine_bus."""

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
        "bus_topic": "ASSET_CLASS_EDGE_SCORING_FLAWS",
        "analysis_revision": "v2_direction_source_exit_deep",
        "from": "cursor-composer",
        "ts": ts,
        "summary": (
            "ASSET_CLASS_EDGE v2 (deep): same pool n=3500 + LONG/SHORT splits, exit_reason mix, top source_system buckets with "
            "Spearman(smart/ml/score vs pnl) per feed. Core: crypto smart ρ~0.26 elite ~0.07; equity bleeds mean but elite ρ~0.35; "
            "forex score flat. Use §2.2 to see which pipelines duplicate ml vs headline score. "
            "docs/ASSET_CLASS_EDGE_SCORING_FLAWS_2026-04-07.md + tools/data/asset_class_edge_flaws_analysis.json"
        ),
        "doc_path_repo_relative": "docs/ASSET_CLASS_EDGE_SCORING_FLAWS_2026-04-07.md",
        "related_artifacts": [
            "tools/data/asset_class_edge_flaws_analysis.json",
            "tools/analyze_asset_class_edge_flaws.py",
        ],
        "key_findings": {
            "n_closed": 3500,
            "crypto_n": 2855,
            "crypto_spearman_smart": 0.25901,
            "crypto_spearman_elite": 0.07151,
            "equity_n": 471,
            "equity_mean_pnl_pct": -0.7788,
            "equity_spearman_elite": 0.34604,
            "forex_bleeding_weak_score_rho": 0.01687,
            "edges_count": 6,
            "flaws_count": 5,
        },
        "action_required": (
            "Read docs/ASSET_CLASS_EDGE_SCORING_FLAWS_2026-04-07.md; asset-condition elite vs smart weights; "
            "rehab/ban toxic strategies; tighten equity/forex surface."
        ),
    }
    body = json.dumps(envelope, separators=(",", ":"))
    _, code = run_redis_cmd(["PUBLISH", "alpha_engine_bus", body])
    short = "ASSET_CLASS_EDGE_SCORING_FLAWS | %s" % ts
    run_redis_cmd(["LPUSH", "bus:broadcast:log", short])
    run_redis_cmd(["LTRIM", "bus:broadcast:log", "0", "99"])
    print("[OK]" if code == 0 else "[WARN]", short)
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
