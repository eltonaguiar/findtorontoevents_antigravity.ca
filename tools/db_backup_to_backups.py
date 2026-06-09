#!/usr/bin/env python3
"""db_backup_to_backups.py — back up prod tables into ejaguiar1_backups.

2026-06-09 FIX: the original used a single connection as the parent `ejaguiar1`
user on host `fdb1027.50webs.com` and did `CREATE TABLE ejaguiar1_backups.x AS
SELECT * FROM <db>.x`. BOTH were broken in this env:
  - `fdb1027.50webs.com` is unreachable from the agent IPs (connection refused).
  - 50webs uses per-DATABASE users (ejaguiar1_stocks -> ejaguiar1_stocks only;
    ejaguiar1_backups -> ejaguiar1_backups only), so a single connection cannot
    do a cross-DB CREATE-AS-SELECT, and the parent `ejaguiar1` user is
    access-denied from the agent IPs.

Now it uses the canonical tools/db_env resolver (env-first + verified defaults +
~/dbpasses.txt) and a TWO-CONNECTION copy: read rows from the source DB
(get_stocks_creds / get_backtests_creds) and write them to ejaguiar1_backups
(get_backups_creds) via SHOW CREATE TABLE -> CREATE -> batched INSERT.

Usage: python3 tools/db_backup_to_backups.py --source-db ejaguiar1_stocks --tables trading_picks,at_raw_picks
Behavior per table: row-count guard (abort if > --row-limit), idempotent skip if
the dated backup already exists, batched copy, row-count verify, audit log to
ejaguiar1_backups.db_audit_log. Exit: 0 OK, 1 partial, 2 hard failure.
"""
from __future__ import annotations
import argparse
import datetime as dt
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import pymysql  # noqa: E402
from tools.db_env import get_stocks_creds, get_backtests_creds, get_backups_creds  # noqa: E402

BACKUP_DB = "ejaguiar1_backups"
AUDIT_TABLE = "db_audit_log"
_KEEP = ("host", "user", "password", "database", "port", "connect_timeout")
_BATCH = 2000


def _conn(creds: dict):
    return pymysql.connect(**{k: v for k, v in creds.items() if k in _KEEP}, autocommit=False)


def _source_creds(source_db: str) -> dict:
    if source_db == "ejaguiar1_backtests":
        return get_backtests_creds()
    return get_stocks_creds()


def _utc_suffix() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _exists(cur, db: str, table: str) -> bool:
    cur.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_schema=%s AND table_name=%s LIMIT 1",
        (db, table),
    )
    return cur.fetchone() is not None


def _audit(bcur, source_db, source_table, backup_table, row_count, status, message) -> None:
    try:
        if not _exists(bcur, BACKUP_DB, AUDIT_TABLE):
            bcur.execute(
                f"CREATE TABLE IF NOT EXISTS `{AUDIT_TABLE}` (ts_utc DATETIME, source_db VARCHAR(64), "
                "source_table VARCHAR(128), backup_table VARCHAR(160), row_count INT, "
                "status VARCHAR(24), message VARCHAR(1024))"
            )
        bcur.execute(
            f"INSERT INTO `{AUDIT_TABLE}` (ts_utc, source_db, source_table, backup_table, row_count, status, message) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (dt.datetime.now(dt.timezone.utc), source_db, source_table, backup_table, row_count, status, str(message)[:1000]),
        )
    except Exception as e:
        print(f"WARN: audit log write failed ({e}); continuing", file=sys.stderr)


def backup_table(scon, bcon, source_db: str, table: str, row_limit: int, suffix: str, dry_run: bool) -> str:
    """Two-connection copy. Returns OK / SKIP_EXISTS / SKIP_TOO_BIG / SKIP_MISSING / FAIL."""
    scur = scon.cursor()
    bcur = bcon.cursor()
    if not _exists(scur, source_db, table):
        print(f"  [{table}] SKIP_MISSING: source table not found", file=sys.stderr)
        return "SKIP_MISSING"
    backup_name = f"{table}_{suffix}"
    if _exists(bcur, BACKUP_DB, backup_name):
        print(f"  [{table}] SKIP_EXISTS: {BACKUP_DB}.{backup_name} already there")
        return "SKIP_EXISTS"
    scur.execute(f"SELECT COUNT(*) FROM `{table}`")
    rows = int(scur.fetchone()[0])
    if rows > row_limit:
        msg = f"row_count={rows} exceeds --row-limit={row_limit}"
        print(f"  [{table}] SKIP_TOO_BIG: {msg} — surface to operator")
        _audit(bcur, source_db, table, backup_name, rows, "SKIP_TOO_BIG", msg)
        bcon.commit()
        return "SKIP_TOO_BIG"
    if dry_run:
        print(f"  [{table}] DRY_RUN: would copy {rows} rows -> {BACKUP_DB}.{backup_name}")
        return "OK"
    try:
        scur.execute(f"SHOW CREATE TABLE `{table}`")
        ddl = scur.fetchone()[1].replace(f"CREATE TABLE `{table}`", f"CREATE TABLE `{backup_name}`", 1)
        # Named constraints (CHECK / FK) must be unique PER SCHEMA in MySQL-8, so a
        # verbatim DDL collides across backup snapshots (e.g. chk_pnl_sign_coherence).
        # Rename every named constraint with the backup suffix so the snapshot DDL is
        # always unique. (A snapshot doesn't need enforced constraints anyway.)
        ddl = re.sub(r"CONSTRAINT `([^`]+)`", lambda m: "CONSTRAINT `" + (m.group(1) + "_b" + suffix)[:60] + "`", ddl)
        bcur.execute(f"DROP TABLE IF EXISTS `{backup_name}`")
        bcur.execute(ddl)
        scur.execute(f"SELECT * FROM `{table}`")
        cols = [d[0] for d in scur.description]
        ins = (f"INSERT INTO `{backup_name}` (" + ",".join("`" + c + "`" for c in cols) + ") VALUES (" +
               ",".join(["%s"] * len(cols)) + ")")
        copied = 0
        while True:
            batch = scur.fetchmany(_BATCH)
            if not batch:
                break
            bcur.executemany(ins, batch)
            copied += len(batch)
        bcon.commit()
    except Exception as e:
        print(f"  [{table}] FAIL: {e}", file=sys.stderr)
        try:
            _audit(bcur, source_db, table, backup_name, rows, "FAIL", str(e))
            bcon.commit()
        except Exception:
            pass
        return "FAIL"
    bcur.execute(f"SELECT COUNT(*) FROM `{backup_name}`")
    dst = int(bcur.fetchone()[0])
    status = "OK" if dst == rows else "FAIL_VERIFY"
    print(f"  [{table}] {status}: {BACKUP_DB}.{backup_name} src={rows} dst={dst}")
    _audit(bcur, source_db, table, backup_name, dst, status, f"src_rows={rows}")
    bcon.commit()
    return status if status == "OK" else "FAIL"


def main() -> int:
    ap = argparse.ArgumentParser(description="Back up prod tables into ejaguiar1_backups (two-connection copy via db_env).")
    ap.add_argument("--source-db", required=True, help="ejaguiar1_stocks or ejaguiar1_backtests")
    ap.add_argument("--tables", required=True, help="comma-separated table names")
    ap.add_argument("--row-limit", type=int, default=1_000_000, help="abort a table if rows > this (default 1M)")
    ap.add_argument("--dry-run", action="store_true", help="report only; no writes")
    args = ap.parse_args()

    tables = [t.strip() for t in args.tables.split(",") if t.strip()]
    suffix = _utc_suffix()
    print(f"db_backup_to_backups.py  source_db={args.source_db}  tables={tables}  row_limit={args.row_limit}  suffix={suffix}  dry_run={args.dry_run}")

    try:
        scon = _conn(_source_creds(args.source_db))
    except Exception as e:
        print(f"FATAL: source connect failed: {e}", file=sys.stderr)
        return 2
    try:
        bcon = _conn(get_backups_creds())
    except Exception as e:
        print(f"FATAL: ejaguiar1_backups connect failed: {e}", file=sys.stderr)
        scon.close()
        return 2

    results: dict[str, list[str]] = {}
    try:
        for t in tables:
            r = backup_table(scon, bcon, args.source_db, t, args.row_limit, suffix, args.dry_run)
            results.setdefault(r, []).append(t)
    finally:
        scon.close()
        bcon.close()

    print("\nSummary:")
    for status, ts in sorted(results.items()):
        print(f"  {status}: {', '.join(ts)}")
    if any(s in results for s in ("FAIL",)):
        return 2
    if any(s.startswith("SKIP") for s in results):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
