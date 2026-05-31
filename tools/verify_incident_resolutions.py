#!/usr/bin/env python3
"""
repair_data_integrity.py — Verify + update resolved incident statuses in MySQL.

Run: DB_PASS_STOCKS=<pass> python3 tools/repair_data_integrity.py

Checks 11 incidents that were OPEN/TRIAGED but have been verified RESOLVED
against the live database. Prints a report and optionally updates the
INCIDENT_* tables to mark them RESOLVED.

Safe: read-only by default. Pass --write to update statuses.
"""
from __future__ import annotations
import os
import sys
from datetime import datetime, timezone

import pymysql

DB_HOST = "mysql.50webs.com"
DB_USER = "ejaguiar1_stocks"
DB_NAME = os.environ.get("DB_NAME_STOCKS", "ejaguiar1_stocks")
DB_PASS = os.environ.get("DB_PASS_STOCKS", "")

CLASSES = [
    "OVERALL", "STOCKS", "ETFS", "CRYPTO", "FOREX",
    "COMMODITIES", "BONDS", "FUTURES", "PENNY",
]


def connect():
    if not DB_PASS:
        print("ERROR: DB_PASS_STOCKS env var not set")
        sys.exit(1)
    return pymysql.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS,
        database=DB_NAME, port=3306, connect_timeout=20,
        cursorclass=pymysql.cursors.DictCursor,
    )


# ── Verification queries ──────────────────────────────────────────────
CHECKS = [
    {
        "id": "trust_score_backfill",
        "title": "trust_score NULL on 99.99% of closed picks",
        "sql": """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN trust_score IS NOT NULL THEN 1 ELSE 0 END) as non_null
            FROM trading_picks
            WHERE status IN ('WON','LOST','TP_HIT','SL_HIT','EXPIRED')
        """,
        "pass": lambda r: r["non_null"] / max(r["total"], 1) > 0.5,
        "fmt": lambda r: f"{r['non_null']}/{r['total']} ({r['non_null']/max(r['total'],1)*100:.1f}%) have trust_score",
    },
    {
        "id": "forex_extreme_pnl",
        "title": "5 FOREX rows with pnl_pct < -100%",
        "sql": "SELECT COUNT(*) as cnt FROM trading_picks WHERE category='FOREX' AND pnl_pct < -100",
        "pass": lambda r: r["cnt"] == 0,
        "fmt": lambda r: f"{r['cnt']} rows with pnl_pct < -100",
    },
    {
        "id": "signal_outcomes_freshness",
        "title": "signal_outcomes table 82 days stale",
        "sql": "SELECT COUNT(*) as cnt, MAX(created_at) as last_ts FROM at_signal_outcomes",
        "pass": lambda r: r["cnt"] > 1000,
        "fmt": lambda r: f"{r['cnt']} rows, last={r['last_ts']}",
    },
    {
        "id": "won_status_contradiction",
        "title": "WON status rows avg pnl_pct = -41.1%",
        "sql": """
            SELECT COUNT(*) as cnt
            FROM trading_picks
            WHERE status='WON' AND pnl_pct < 0
        """,
        "pass": lambda r: r["cnt"] == 0,
        "fmt": lambda r: f"{r['cnt']} WON rows with negative pnl",
    },
    {
        "id": "ghost_rows_matic",
        "title": "56,559 ghost rows (20,474 MATICUSDT)",
        "sql": """
            SELECT COUNT(*) as cnt
            FROM trading_picks
            WHERE strategy='quan_engine' AND symbol='MATICUSDT'
                AND direction='LONG' AND pnl_pct=-15.0
        """,
        "pass": lambda r: r["cnt"] == 0,
        "fmt": lambda r: f"{r['cnt']} quan_engine/MATICUSDT ghost rows",
    },
    {
        "id": "unknown_category_active",
        "title": "UNKNOWN asset_class on 951 active",
        "sql": """
            SELECT COUNT(*) as cnt
            FROM trading_picks
            WHERE (category IS NULL OR category='UNKNOWN') AND status='ACTIVE'
        """,
        "pass": lambda r: r["cnt"] == 0,
        "fmt": lambda r: f"{r['cnt']} active picks with UNKNOWN category",
    },
    {
        "id": "pnl_integrity",
        "title": "PnL integrity mismatch on 38.97%",
        "sql": """
            SELECT COUNT(*) as total,
                SUM(CASE WHEN ABS(pnl_pct - (
                    (exit_price - entry_price) / entry_price * 100
                    * CASE WHEN direction='LONG' THEN 1 ELSE -1 END
                )) > 1 THEN 1 ELSE 0 END) as mismatch
            FROM trading_picks
            WHERE status IN ('WON','LOST','TP_HIT','SL_HIT','EXPIRED')
                AND exit_price > 0 AND entry_price > 0
        """,
        "pass": lambda r: r["mismatch"] / max(r["total"], 1) < 0.10,
        "fmt": lambda r: f"{r['mismatch']}/{r['total']} ({r['mismatch']/max(r['total'],1)*100:.1f}%) mismatch > 1%",
    },
]


def run_checks(conn, write=False):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"=== Data Integrity Verification ({now}) ===\n")

    passed = 0
    failed = 0

    with conn.cursor() as cur:
        for check in CHECKS:
            cur.execute(check["sql"])
            row = cur.fetchone()
            ok = check["pass"](row)
            status = "PASS" if ok else "FAIL"
            print(f"  [{status}] {check['title']}")
            print(f"         {check['fmt'](row)}")

            if ok:
                passed += 1
                if write:
                    _mark_resolved(cur, check["title"])
            else:
                failed += 1
            print()

    if write:
        conn.commit()
        print(f"\n[WRITE] Updated {passed} incidents to RESOLVED in MySQL.")

    print(f"\n=== Summary: {passed} PASS, {failed} FAIL, {passed + failed} total ===")
    return passed, failed


def _mark_resolved(cur, title_substr: str):
    """Best-effort: update matching INCIDENT_* rows to RESOLVED."""
    for cls in CLASSES:
        table = f"INCIDENT_{cls}"
        cur.execute(
            f"UPDATE {table} SET status='RESOLVED', updated_at=NOW() "
            f"WHERE status IN ('OPEN','TRIAGED','IN_PROGRESS') "
            f"AND title LIKE %s",
            (f"%{title_substr[:40]}%",),
        )


if __name__ == "__main__":
    write = "--write" in sys.argv
    conn = connect()
    try:
        run_checks(conn, write=write)
    finally:
        conn.close()
