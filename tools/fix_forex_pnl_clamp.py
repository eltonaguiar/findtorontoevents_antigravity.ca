#!/usr/bin/env python3
"""Clamp FOREX pnl_pct values below -100% to -100%.

Incident: 5 FOREX rows have pnl_pct < -100% (one at -106,700%).
Distorts FOREX avg to -8% and rounds PF to 0.00.
Fix: UPDATE trading_picks SET pnl_pct = -100 WHERE pnl_pct < -100 AND category='FOREX'.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    try:
        import pymysql
    except ImportError:
        print("pymysql not available")
        return 1

    password = os.environ.get("DB_STOCKS_PASSWORD") or os.environ.get("DB_PASS_STOCKS") or ""
    if not password:
        print("DB_PASS_STOCKS env var not set")
        return 1

    conn = pymysql.connect(
        host=os.environ.get("DB_STOCKS_HOST", "mysql.50webs.com"),
        port=int(os.environ.get("DB_STOCKS_PORT", "3306")),
        user=os.environ.get("DB_STOCKS_USER", "ejaguiar1_stocks"),
        password=password,
        database=os.environ.get("DB_STOCKS_NAME", "ejaguiar1_stocks"),
        charset="utf8mb4",
    )
    try:
        cur = conn.cursor()

        cur.execute(
            "SELECT COUNT(*) FROM trading_picks WHERE category='FOREX' AND pnl_pct < -100"
        )
        affected = cur.fetchone()[0]
        print(f"Rows with pnl_pct < -100 in FOREX: {affected}")

        if affected == 0:
            print("No rows to fix. Exiting.")
            return 0

        cur.execute(
            "UPDATE trading_picks SET pnl_pct = -100 WHERE category='FOREX' AND pnl_pct < -100"
        )
        conn.commit()
        print(f"Updated {cur.rowcount} rows")

        cur.execute(
            "SELECT COUNT(*) FROM trading_picks WHERE category='FOREX' AND pnl_pct < -100"
        )
        remaining = cur.fetchone()[0]
        print(f"Remaining under-clamped rows: {remaining}")
        print("FOREX pnl_pct clamp complete.")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
