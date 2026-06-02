#!/usr/bin/env python3
"""
One-time (idempotent) ALTER for at_pick_outcomes forward-test isolation columns.

Requires AUDIT_DB_PASS or DB_PASS_STOCKS (same as check_resolver_health).
"""
from __future__ import annotations

import argparse
import os
import sys

COLUMNS = (
    ("forward_test_only", "BOOLEAN DEFAULT FALSE"),
    ("forward_validated", "BOOLEAN DEFAULT FALSE"),
    ("_gated_forward_test_isolated", "BOOLEAN DEFAULT FALSE"),
)


def _password() -> str:
    for key in ("AUDIT_DB_PASS", "DB_PASS_STOCKS", "MYSQL_PASSWORD"):
        v = os.environ.get(key, "").strip()
        if v:
            return v
    try:
        from tools.resolve_stale_open_picks import _read_db_password

        return _read_db_password()
    except Exception:
        return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    pw = _password()
    if not pw:
        print("No DB password — set AUDIT_DB_PASS or DB_PASS_STOCKS", file=sys.stderr)
        return 2

    import pymysql

    host = os.environ.get("AUDIT_DB_HOST", "mysql.50webs.com")
    user = os.environ.get("AUDIT_DB_USER", "ejaguiar1_stocks")
    db = os.environ.get("AUDIT_DB_NAME", "ejaguiar1_stocks")
    port = int(os.environ.get("AUDIT_DB_PORT", "3306"))

    conn = pymysql.connect(host=host, user=user, password=pw, database=db, port=port)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA=%s AND TABLE_NAME='at_pick_outcomes'",
                (db,),
            )
            existing = {row[0] for row in cur.fetchall()}
        missing = [name for name, _ in COLUMNS if name not in existing]
        if not missing:
            print("OK: all forward_test columns present on at_pick_outcomes")
            return 0
        print(f"Missing columns: {missing}")
        for name, typedef in COLUMNS:
            if name not in missing:
                continue
            sql = f"ALTER TABLE at_pick_outcomes ADD COLUMN {name} {typedef}"
            print(f"  {sql}")
            if args.execute:
                with conn.cursor() as cur:
                    cur.execute(sql)
                conn.commit()
                print(f"  applied {name}")
        if not args.execute:
            print("Dry-run — re-run with --execute to apply")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
