#!/usr/bin/env python3
"""Publish DOW closed-trades study summary to alpha_engine_bus."""

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
        "bus_topic": "DOW_CLOSED_TRADES_STUDY",
        "from": "cursor-composer",
        "ts": ts,
        "summary": (
            "UTC DOW on closed_at: n=3500. Chi-square win/loss vs weekday p~6e-21 (all), "
            "Cramer V~0.18; Kruskal-Wallis pnl p~4e-36. Crypto n=2855: chi2 p~4e-25, V~0.21, KW p~2e-40. "
            "Pattern: Thu worst (WR~27%, mean~-1.2% all; crypto Thu similar). Mon best mean pnl; crypto Fri highest WR~63%. "
            "Caveats: observational, close-time not entry, UTC label, confounds possible — use as research + monitor not sole signal."
        ),
        "doc_path_repo_relative": "docs/DOW_CLOSED_TRADES_STUDY_2026-04-07.md",
        "related_artifacts": [
            "tools/data/dow_closed_trades_analysis.json",
            "tools/analyze_dow_closed_trades.py",
        ],
        "key_findings": {
            "n_closed": 3500,
            "n_crypto": 2855,
            "timezone": "UTC_weekday_from_closed_at",
            "chi2_all_chi2": 107.5975,
            "chi2_all_p": 6.488743700019784e-21,
            "cramers_v_all": 0.1753,
            "kw_all_H": 179.8491,
            "kw_all_p": 3.652948641320895e-36,
            "chi2_crypto_chi2": 127.8323,
            "chi2_crypto_p": 3.675754167428154e-25,
            "cramers_v_crypto": 0.2116,
            "kw_crypto_H": 200.0173,
            "kw_crypto_p": 1.881559987357917e-40,
            "thu_all_win_rate_pct": 26.96,
            "thu_all_mean_pnl_pct": -1.2465,
            "mon_all_mean_pnl_pct": 0.8631,
            "fri_crypto_win_rate_pct": 62.66,
        },
        "action_required": (
            "Read docs/DOW_CLOSED_TRADES_STUDY_2026-04-07.md; decompose Thu by strategy; optional DOW risk overlay only if walk-forward stable."
        ),
    }
    body = json.dumps(envelope, separators=(",", ":"))
    _, code = run_redis_cmd(["PUBLISH", "alpha_engine_bus", body])
    short = "DOW_CLOSED_TRADES_STUDY | Thu trough UTC | %s" % ts
    run_redis_cmd(["LPUSH", "bus:broadcast:log", short])
    run_redis_cmd(["LTRIM", "bus:broadcast:log", "0", "99"])
    print("[OK]" if code == 0 else "[WARN]", short)
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
