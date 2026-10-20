#!/usr/bin/env python3
"""Nightly UNCAPPED export of resolved closed picks from at_pick_outcomes.

Why (2026-10-20): the dashboard payload caps the published closed list at
MAX_CLOSED_PICKS=3500 (audit_trail/dashboard_generator.py), so the live
``recent_closed`` cannot reproduce full history and class PF/WR on the dashboard
disagree with the DB. This tool exports EVERY resolved row (no cap) so the row
count can be reconciled against the DB.

Read-only: SELECT only, never mutates. Creds resolve from env (same convention as
tools/mysql_resolve_at_pick_outcomes.py) — never hard-coded, never printed.

Validation: logs ``db_count`` and ``exported_count`` and FAILS (exit 1) if they
differ, so "exported row count == DB count" is machine-checked every run.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone

try:
    import pymysql
except ImportError:
    sys.exit("pymysql not installed — run: pip install pymysql")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger("closed_picks_full_export")

DB_HOST = os.getenv("AUDIT_DB_HOST", os.getenv("DB_HOST", "mysql.50webs.com"))
DB_PORT = int(os.getenv("AUDIT_DB_PORT", os.getenv("DB_PORT", "3306")))
DB_USER = os.getenv("AUDIT_DB_USER", os.getenv("DB_USER", "ejaguiar1_stocks"))
DB_PASS = (
    os.getenv("AUDIT_DB_PASS")
    or os.getenv("DB_PASS_STOCKS")
    or os.getenv("MYSQL_PASSWORD")
    or ""
)
DB_NAME = os.getenv("AUDIT_DB_NAME", os.getenv("DB_NAME", "ejaguiar1_stocks"))

DEFAULT_OUT = "audit_dashboard/data/closed_picks_full.json"


def _connect():
    if not DB_PASS:
        log.error("No DB password — set AUDIT_DB_PASS, DB_PASS_STOCKS, or MYSQL_PASSWORD")
        sys.exit(1)
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        connect_timeout=15,
    )


def export(out_path: str) -> int:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            # db_count: total resolved rows (the reconciliation anchor).
            cur.execute(
                "SELECT COUNT(*) AS c FROM at_pick_outcomes "
                "WHERE status IS NOT NULL AND status <> 'OPEN'"
            )
            db_count = int(cur.fetchone()["c"])

            # Full, uncapped export of resolved rows.
            cur.execute(
                "SELECT * FROM at_pick_outcomes "
                "WHERE status IS NOT NULL AND status <> 'OPEN' "
                "ORDER BY resolved_at DESC"
            )
            rows = list(cur.fetchall())
    finally:
        conn.close()

    exported_count = len(rows)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    payload = {
        "generated_at": generated_at,
        "source": f"mysql://{DB_HOST}/{DB_NAME}/at_pick_outcomes",
        "db_count": db_count,
        "exported_count": exported_count,
        "uncapped": True,
        "rows": rows,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, default=str, separators=(",", ":"))

    log.info("db_count=%d exported_count=%d -> %s", db_count, exported_count, out_path)
    if exported_count != db_count:
        log.error(
            "COUNT MISMATCH: exported %d != DB %d — do not trust this export",
            exported_count, db_count,
        )
        return 1
    log.info("OK: exported_count == db_count (%d)", db_count)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=DEFAULT_OUT, help="output JSON path")
    args = ap.parse_args()
    sys.exit(export(args.out))


if __name__ == "__main__":
    main()
