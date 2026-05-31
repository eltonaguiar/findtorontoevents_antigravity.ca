#!/usr/bin/env python3
"""
db_backup_to_backups.py — Python fallback for mysqldump-unavailable env.

Zoo's swarm tried mysqldump on 2026-05-31 to back up tables into
ejaguiar1_backups before any destructive remediation; mysqldump is NOT
installed on this server. This script does the same job purely via
pymysql + SQL `CREATE TABLE ... AS SELECT *`.

Usage:
    python3 tools/db_backup_to_backups.py \
        --source-db ejaguiar1_stocks \
        --tables trading_picks,at_raw_picks \
        --row-limit 1000000

Behavior:
  - For each table:
      1) row-count guard (abort table if rows > --row-limit; surface to operator).
      2) CREATE TABLE ejaguiar1_backups.<table>_<UTC_ISO> AS SELECT * FROM <db>.<table>
      3) log to ejaguiar1_backups.db_audit_log (table created by zoo swarm).
  - Idempotent: if backup with same UTC suffix already exists, WARN + skip.
  - Exit codes: 0 OK, 1 partial (some skipped), 2 hard failure.

Operator action: this is a destructive op surface (writes new tables);
per CLAUDE.md, requires explicit operator greenlight before running on
prod DBs.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys

try:
    import pymysql
except ImportError:
    print("FATAL: pymysql not installed. pip install pymysql", file=sys.stderr)
    sys.exit(2)


BACKUP_DB = "ejaguiar1_backups"
AUDIT_TABLE = "db_audit_log"


def _load_creds() -> tuple[str, str, str]:
    """Load DB host/user/pass. Convention: 50webs pw = <user>1234560."""
    host = os.environ.get("DB_HOST", "fdb1027.50webs.com")
    user = os.environ.get("DB_USER", "ejaguiar1")
    pw = os.environ.get("DB_PASS")
    if not pw:
        pw = f"{user}1234560"
    return host, user, pw


def _utc_suffix() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _table_exists(cur, db: str, table: str) -> bool:
    cur.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema=%s AND table_name=%s LIMIT 1",
        (db, table),
    )
    return cur.fetchone() is not None


def _row_count(cur, db: str, table: str) -> int:
    cur.execute(f"SELECT COUNT(*) FROM `{db}`.`{table}`")
    return int(cur.fetchone()[0])


def _audit(cur, source_db: str, source_table: str, backup_table: str,
           row_count: int, status: str, message: str) -> None:
    try:
        cur.execute(
            f"INSERT INTO `{BACKUP_DB}`.`{AUDIT_TABLE}` "
            "(ts_utc, source_db, source_table, backup_table, row_count, status, message) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (dt.datetime.now(dt.timezone.utc), source_db, source_table,
             backup_table, row_count, status, message[:1000]),
        )
    except Exception as e:
        print(f"WARN: audit log write failed ({e}); continuing", file=sys.stderr)


def backup_table(conn, source_db: str, table: str, row_limit: int,
                 suffix: str, dry_run: bool) -> str:
    """Returns one of: OK, SKIP_EXISTS, SKIP_TOO_BIG, SKIP_MISSING, FAIL."""
    with conn.cursor() as cur:
        if not _table_exists(cur, source_db, table):
            print(f"  [{table}] SKIP_MISSING: source table not found", file=sys.stderr)
            return "SKIP_MISSING"

        backup_name = f"{table}_{suffix}"
        if _table_exists(cur, BACKUP_DB, backup_name):
            print(f"  [{table}] SKIP_EXISTS: {BACKUP_DB}.{backup_name} already there")
            _audit(cur, source_db, table, backup_name, -1, "SKIP_EXISTS",
                   "idempotent skip")
            conn.commit()
            return "SKIP_EXISTS"

        rows = _row_count(cur, source_db, table)
        if rows > row_limit:
            msg = f"row_count={rows} exceeds --row-limit={row_limit}"
            print(f"  [{table}] SKIP_TOO_BIG: {msg} — surface to operator")
            _audit(cur, source_db, table, backup_name, rows, "SKIP_TOO_BIG", msg)
            conn.commit()
            return "SKIP_TOO_BIG"

        if dry_run:
            print(f"  [{table}] DRY_RUN: would CREATE {BACKUP_DB}.{backup_name} "
                  f"({rows} rows)")
            return "OK"

        sql = (f"CREATE TABLE `{BACKUP_DB}`.`{backup_name}` AS "
               f"SELECT * FROM `{source_db}`.`{table}`")
        try:
            cur.execute(sql)
            conn.commit()
        except Exception as e:
            print(f"  [{table}] FAIL: {e}", file=sys.stderr)
            _audit(cur, source_db, table, backup_name, rows, "FAIL", str(e))
            conn.commit()
            return "FAIL"

        backup_rows = _row_count(cur, BACKUP_DB, backup_name)
        status = "OK" if backup_rows == rows else "FAIL_VERIFY"
        print(f"  [{table}] {status}: {BACKUP_DB}.{backup_name} "
              f"src={rows} dst={backup_rows}")
        _audit(cur, source_db, table, backup_name, backup_rows, status,
               f"src_rows={rows}")
        conn.commit()
        return status if status == "OK" else "FAIL"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-db", required=True, help="e.g. ejaguiar1_stocks")
    ap.add_argument("--tables", required=True, help="comma-separated table names")
    ap.add_argument("--row-limit", type=int, default=1_000_000,
                    help="abort a table if rows > this (default 1M)")
    ap.add_argument("--dry-run", action="store_true",
                    help="do not create backup tables; just report")
    args = ap.parse_args()

    host, user, pw = _load_creds()
    tables = [t.strip() for t in args.tables.split(",") if t.strip()]
    suffix = _utc_suffix()

    print(f"db_backup_to_backups.py")
    print(f"  source_db = {args.source_db}")
    print(f"  tables    = {tables}")
    print(f"  row_limit = {args.row_limit}")
    print(f"  suffix    = {suffix}")
    print(f"  dry_run   = {args.dry_run}")

    try:
        conn = pymysql.connect(host=host, user=user, password=pw,
                               database=args.source_db,
                               autocommit=False, connect_timeout=10)
    except Exception as e:
        print(f"FATAL: connect failed: {e}", file=sys.stderr)
        return 2

    results: dict[str, list[str]] = {}
    try:
        for t in tables:
            r = backup_table(conn, args.source_db, t, args.row_limit,
                             suffix, args.dry_run)
            results.setdefault(r, []).append(t)
    finally:
        conn.close()

    print("\n=== SUMMARY ===")
    for status, ts in results.items():
        print(f"  {status}: {len(ts)} ({', '.join(ts)})")

    if results.get("FAIL") or results.get("FAIL_VERIFY"):
        return 2
    if any(k.startswith("SKIP") for k in results):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
