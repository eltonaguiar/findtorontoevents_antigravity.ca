#!/usr/bin/env python3
"""
Deduplicate ghost cohorts in ejaguiar1_stocks.trading_picks.

Ghost definition (INC OVERALL #9): rows sharing
(category, strategy, symbol, direction, ROUND(pnl_pct,2), ROUND(entry_price,8))
with COUNT(*) >= min_cohort AND COUNT(DISTINCT DATE(created_at)) <= max_distinct_days.

Keeps the row with MIN(id); deletes the rest. Dry-run by default.

Usage:
  python3 tools/dedup_trading_picks_ghosts.py
  python3 tools/dedup_trading_picks_ghosts.py --apply --limit 5000
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

try:
    import pymysql
except ImportError:
    print("pymysql required", file=sys.stderr)
    sys.exit(2)


def _connect():
    pw = os.environ.get("DB_PASS_STOCKS") or os.environ.get("DB_STOCKS_PASSWORD", "")
    if not pw:
        raise RuntimeError("Set DB_PASS_STOCKS")
    return pymysql.connect(
        host=os.environ.get("DB_STOCKS_HOST", "mysql.50webs.com"),
        user=os.environ.get("DB_STOCKS_USER", "ejaguiar1_stocks"),
        password=pw,
        database=os.environ.get("DB_STOCKS_NAME", "ejaguiar1_stocks"),
        port=int(os.environ.get("DB_STOCKS_PORT", "3306")),
        charset="utf8mb4",
        connect_timeout=30,
        autocommit=False,
        cursorclass=pymysql.cursors.DictCursor,
    )


def discover_cohorts(cur, min_cohort: int, max_distinct_days: int, scan_limit: int):
    cur.execute(
        """
        SELECT category, strategy, symbol, direction,
               ROUND(pnl_pct, 2) AS pnl_r,
               ROUND(entry_price, 8) AS entry_r,
               COUNT(*) AS n,
               MIN(id) AS keep_id,
               COUNT(DISTINCT DATE(created_at)) AS distinct_days
        FROM trading_picks
        GROUP BY category, strategy, symbol, direction, ROUND(pnl_pct, 2), ROUND(entry_price, 8)
        HAVING n >= %s AND COUNT(DISTINCT DATE(created_at)) <= %s
        ORDER BY n DESC
        LIMIT %s
        """,
        (min_cohort, max_distinct_days, scan_limit),
    )
    return cur.fetchall()


def delete_cohort(cur, row: dict, batch_limit: int) -> int:
    cur.execute(
        """
        DELETE FROM trading_picks
        WHERE category <=> %s AND strategy <=> %s AND symbol <=> %s
          AND direction <=> %s
          AND ROUND(pnl_pct, 2) <=> %s
          AND ROUND(entry_price, 8) <=> %s
          AND id != %s
        LIMIT %s
        """,
        (
            row["category"],
            row["strategy"],
            row["symbol"],
            row["direction"],
            row["pnl_r"],
            row["entry_r"],
            row["keep_id"],
            batch_limit,
        ),
    )
    return cur.rowcount


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--min-cohort", type=int, default=50)
    ap.add_argument("--max-distinct-days", type=int, default=1,
                    help="Cohorts with at most N distinct created_at days (default 1 = single burst)")
    ap.add_argument("--limit", type=int, default=5000, help="Max rows to delete this run")
    ap.add_argument("--scan-limit", type=int, default=50, help="Max cohorts to inspect")
    args = ap.parse_args()

    conn = _connect()
    cur = conn.cursor()
    cohorts = discover_cohorts(cur, args.min_cohort, args.max_distinct_days, args.scan_limit)
    deletable = sum(max(int(c["n"]) - 1, 0) for c in cohorts)

    print(f"cohorts={len(cohorts)} deletable_rows={deletable} mode={'APPLY' if args.apply else 'DRY_RUN'}")
    for c in cohorts[:10]:
        print(
            f"  {c['strategy']}/{c['symbol']}/{c['direction']} pnl={c['pnl_r']} "
            f"n={c['n']} days={c['distinct_days']} keep_id={c['keep_id']}"
        )

    deleted = 0
    if args.apply and cohorts:
        for c in cohorts:
            while deleted < args.limit:
                chunk = min(1000, args.limit - deleted)
                n = delete_cohort(cur, c, chunk)
                if n == 0:
                    break
                deleted += n
                conn.commit()
            if deleted >= args.limit:
                break

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "APPLY" if args.apply else "DRY_RUN",
        "cohorts": len(cohorts),
        "deletable_est": deletable,
        "deleted": deleted,
        "top_cohorts": cohorts[:20],
    }
    out = "tools/trading_picks_ghost_dedup_report.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"report={out} deleted={deleted}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
