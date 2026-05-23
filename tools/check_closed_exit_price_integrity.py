#!/usr/bin/env python3
"""Check closed-trade exit_price integrity across MySQL tables.

Usage:
  python tools/check_closed_exit_price_integrity.py
"""

from __future__ import annotations

import os
import sys


def _connect():
    try:
        import pymysql  # type: ignore
    except ImportError:
        import subprocess

        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pymysql"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        import pymysql  # type: ignore

    return pymysql.connect(
        host=os.environ.get("AUDIT_DB_HOST", "mysql.50webs.com"),
        port=int(os.environ.get("AUDIT_DB_PORT", "3306")),
        user=os.environ.get("AUDIT_DB_USER", "ejaguiar1_stocks"),
        password=os.environ.get("AUDIT_DB_PASS", "stocks"),
        database=os.environ.get("AUDIT_DB_NAME", "ejaguiar1_stocks"),
        charset="utf8mb4",
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
    )


def main() -> int:
    conn = _connect()
    cur = conn.cursor()

    queries = {
        "trading_picks_closed_missing_exit_non_crypto": """
            SELECT COUNT(*) AS n
            FROM trading_picks
            WHERE category IN ('equity','stock','stocks','forex','commodity','commodities',
                               'futures','etf','bond','penny','pennystock','index')
              AND status IN ('WON','WIN','LOST','LOSS','CLOSED','CLOSED_TP','CLOSED_SL',
                             'tp_hit','sl_hit','EXPIRED','FLAT','time_exit')
              AND (exit_price IS NULL OR exit_price = 0)
        """,
        "at_raw_picks_closed_missing_exit": """
            SELECT COUNT(*) AS n
            FROM at_raw_picks
            WHERE status IN ('WON','LOST','EXPIRED','CLOSED')
              AND (exit_price IS NULL OR exit_price = 0)
        """,
        "at_consensus_picks_closed_missing_exit": """
            SELECT COUNT(*) AS n
            FROM at_consensus_picks
            WHERE status IN ('WON','LOST','EXPIRED','CLOSED')
              AND (exit_price IS NULL OR exit_price = 0)
        """,
    }

    print("=== CLOSED EXIT_PRICE INTEGRITY ===")
    bad_total = 0
    for name, sql in queries.items():
        cur.execute(sql)
        n = int(cur.fetchone()["n"])
        bad_total += n
        print(f"{name}: {n}")

    print(f"TOTAL_BAD_ROWS: {bad_total}")
    cur.close()
    conn.close()
    # Non-zero exit code lets CI/ops alert quickly.
    return 1 if bad_total > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())

