#!/usr/bin/env python3
"""Clamp impossible FOREX pnl_pct values — EAGLE QW-07."""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone


def get_db_connection():
    import pymysql
    password = os.environ.get("DB_STOCKS_PASSWORD") or os.environ.get("DB_PASS_STOCKS") or ""
    if not password:
        raise RuntimeError("DB_STOCKS_PASSWORD or DB_PASS_STOCKS required")
    return pymysql.connect(
        host=os.environ.get("DB_STOCKS_HOST", "mysql.50webs.com"),
        port=int(os.environ.get("DB_STOCKS_PORT", "3306")),
        user=os.environ.get("DB_STOCKS_USER", "ejaguiar1_stocks"),
        password=password,
        database=os.environ.get("DB_STOCKS_NAME", "ejaguiar1_stocks"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--floor", type=float, default=-100.0)
    ap.add_argument("--ceiling", type=float, default=1000.0)
    args = ap.parse_args()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) AS n FROM trading_picks WHERE category='FOREX' AND pnl_pct IS NOT NULL AND (pnl_pct < %s OR pnl_pct > %s)",
        (args.floor, args.ceiling),
    )
    n = int(cur.fetchone()["n"])
    print(f"FOREX rows outside [{args.floor}, {args.ceiling}]: {n}")
    if n == 0:
        conn.close()
        return 0
    if not args.apply:
        print("DRY-RUN — use --apply")
        conn.close()
        return n
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        """
        UPDATE trading_picks SET pnl_pct = CASE WHEN pnl_pct < %s THEN %s WHEN pnl_pct > %s THEN %s ELSE pnl_pct END,
        updated_at = %s
        WHERE category='FOREX' AND pnl_pct IS NOT NULL AND (pnl_pct < %s OR pnl_pct > %s)
        """,
        (args.floor, args.floor, args.ceiling, args.ceiling, now, args.floor, args.ceiling),
    )
    print(f"Clamped {cur.rowcount} rows")
    conn.commit()
    conn.close()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
