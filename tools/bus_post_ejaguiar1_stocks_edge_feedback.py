#!/usr/bin/env python3
"""Publish ejaguiar1_stocks SQL extract edge feedback memo to alpha_engine_bus."""

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
        "bus_topic": "EJAGUIAR1_STOCKS_EDGE_FEEDBACK",
        "from": "cursor-composer",
        "ts": ts,
        "summary": (
            "Review: ejaguiar1_stocks_apr62026_extract.sql (~4GB). P0: persist smart_score/tier in MySQL to match "
            "dashboard gates; fill at_strategy_stats from closes; verify live SHOW TABLES vs 37-table dump. "
            "P1: mine at_filter_log (~600k) for false-negative filters; JSON features from raw_payload/bt raw_data. "
            "P2: join alpha_picks to factor_scores+macro. bt_* = research only with source metadata. "
            "Full memo: docs/EJAGUIAR1_STOCKS_EDGE_FEEDBACK_2026-04-08.md"
        ),
        "doc_path_repo_relative": "docs/EJAGUIAR1_STOCKS_EDGE_FEEDBACK_2026-04-08.md",
        "related_docs": [
            "docs/EJAGUIAR1_STOCKS_SQL_EXTRACT_2026-04-06.md",
            "tools/sql/ejaguiar1_stocks_readonly_analytics.sql",
            "docs/ASSET_CLASS_EDGE_SCORING_FLAWS_2026-04-07.md",
        ],
        "sql_extract_path_user": "C:/Users/zerou/Downloads/ejaguiar1_stocks_apr62026_extract.sql",
        "action_required": (
            "Read EJAGUIAR1_STOCKS_EDGE_FEEDBACK_2026-04-08.md; prioritize smart_score persistence + filter_log mining."
        ),
    }
    body = json.dumps(envelope, separators=(",", ":"))
    _, code = run_redis_cmd(["PUBLISH", "alpha_engine_bus", body])
    short = "EJAGUIAR1_STOCKS_EDGE_FEEDBACK | %s" % ts
    run_redis_cmd(["LPUSH", "bus:broadcast:log", short])
    run_redis_cmd(["LTRIM", "bus:broadcast:log", "0", "99"])
    print("[OK]" if code == 0 else "[WARN]", short)
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
