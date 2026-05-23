#!/usr/bin/env python3
"""Publish SQL extract findings to alpha_engine_bus."""

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
        "bus_topic": "edge_findings_sql_extract",
        "from": "kilo-sql-analysis",
        "ts": ts,
        "summary": "ejaguiar1_stocks SQL extract analyzed: 37 tables, 85349 rows. bt_backtest_trades = 80712 (94.6% of data) — enormous backtest noise. at_raw_picks: 1551 rows (CRYPTO 23, EQUITY 4, FOREX 2). at_filter_log: 1923 blocked picks (wr_suppressed, demoted_system). algorithm_performance: 22 strategies ALL showing negative avg_return_pct (-0.35% to -8.93%). Worst: Alpha Factor Composite -8.93%, Safe Bets -8.07%, Low Vol -7.87%. CONFIRMS equity algorithm disaster from dashboard data. Schema gap: win_rate column uses non-standard cumulative scores, not actual WR%. EDGE_FINDINGS_2026-04-06.md updated with SQL analysis.",
        "doc_path_repo_relative": "EDGE_FINDINGS_2026-04-06.md",
        "sql_extract": "C:/Users/zerou/Downloads/ejaguiar1_stocks_apr62026_extract.sql",
        "key_finding": "94.6% of DB is backtest trades. All 22 algorithms show negative live returns. The backtest-to-live pipeline is generating noise, not edge.",
        "action_required": "Schema needs: (1) standardize win_rate to 0-100%, (2) add smart_score/ml_composite columns, (3) add regime/ATR columns, (4) separate backtest from live data.",
    }
    body = json.dumps(envelope, separators=(",", ":"))
    _, code = run_redis_cmd(["PUBLISH", "alpha_engine_bus", body])
    short = f"edge_findings_sql_extract | ejaguiar1_stocks 85349 rows | 94.6% backtest noise | {ts}"
    run_redis_cmd(["LPUSH", "bus:broadcast:log", short])
    run_redis_cmd(["LTRIM", "bus:broadcast:log", "0", "99"])
    print("[OK]" if code == 0 else "[WARN]", short)
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
