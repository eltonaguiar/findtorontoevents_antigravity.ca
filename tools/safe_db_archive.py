#!/usr/bin/env python3
"""
SAFE DB ARCHIVE — implements Hermes rule #1.

Before any significant table modification, archive the affected slice of the
source table into `ejaguiar1_backups.<source_table>_<purpose>_<utc_ts>`.
Default mode is DRY-RUN; pass --apply to actually copy.

Usage:
  python tools/safe_db_archive.py \\
      --source-table trading_picks \\
      --where "closed_at IS NULL AND status IN ('WON','LOST',...)" \\
      --purpose orphan_resolver
  # → counts matching rows + prints the CREATE/INSERT statements that
  #   would execute. NO writes performed.

  python tools/safe_db_archive.py ... --apply
  # → CREATE TABLE LIKE source schema in ejaguiar1_backups, INSERT in
  #   1000-row batches (Hermes rule #3), verify count parity, append
  #   archive entry to reports/db_archives_log.md.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import pymysql

if sys.platform == "win32":
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            try:
                s.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

REPO = Path(__file__).resolve().parent.parent
LOG_PATH = REPO / "reports" / "db_archives_log.md"


def conn(db_name, user, password):
    return pymysql.connect(
        host="mysql.50webs.com", user=user, password=password,
        db=db_name, connect_timeout=15, read_timeout=120,
        charset="utf8mb4", autocommit=False,
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-db", default="ejaguiar1_stocks")
    ap.add_argument("--source-user", default="ejaguiar1_stocks")
    ap.add_argument("--source-pass", default="stocks")
    ap.add_argument("--backup-db", default="ejaguiar1_backups")
    ap.add_argument("--backup-user", default="ejaguiar1_backups")
    ap.add_argument("--backup-pass", default="backups")
    ap.add_argument("--source-table", required=True)
    ap.add_argument("--where", required=True, help="WHERE clause body (no leading WHERE)")
    ap.add_argument("--purpose", required=True, help="Slug like 'orphan_resolver'")
    ap.add_argument("--apply", action="store_true", help="Actually copy (default: dry-run)")
    ap.add_argument("--max-rows", type=int, default=100_000)
    args = ap.parse_args()

    ts_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive_name = f"{args.source_table}_{args.purpose}_{ts_utc}"[:64]

    print(f"=== SAFE DB ARCHIVE ===")
    print(f"  source: {args.source_db}.{args.source_table}")
    print(f"  where:  {args.where}")
    print(f"  archive: {args.backup_db}.{archive_name}")
    print(f"  mode:   {'APPLY' if args.apply else 'DRY-RUN'}")

    src = conn(args.source_db, args.source_user, args.source_pass)
    cur = src.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {args.source_table} WHERE {args.where}")
    n = cur.fetchone()[0]
    print(f"  matching rows: {n:,}")
    if n == 0:
        print("  no rows to archive. done.")
        src.close(); return
    if n > args.max_rows:
        print(f"  ABORT: {n:,} > max-rows ceiling {args.max_rows:,}.")
        src.close(); sys.exit(2)

    cur.execute(f"SHOW CREATE TABLE {args.source_table}")
    create_sql = cur.fetchone()[1].replace(
        f"CREATE TABLE `{args.source_table}`",
        f"CREATE TABLE `{archive_name}`",
    )

    if not args.apply:
        print("\n  [DRY-RUN] Would execute:")
        print(f"    1. {create_sql[:80]}...")
        print(f"    2. INSERT INTO {args.backup_db}.{archive_name} "
              f"SELECT * FROM {args.source_db}.{args.source_table} "
              f"WHERE {args.where}")
        print(f"    3. Append entry to {LOG_PATH}")
        print("\n  No writes performed. Re-run with --apply to execute.")
        src.close(); return

    bak = conn(args.backup_db, args.backup_user, args.backup_pass)
    bcur = bak.cursor()
    print("\n  [APPLY] creating archive table...")
    bcur.execute(create_sql)
    bak.commit()

    print(f"  [APPLY] copying {n:,} rows in batches of 1,000...")
    BATCH = 1000
    cur.execute(f"SELECT * FROM {args.source_table} WHERE {args.where}")
    cols = [d[0] for d in cur.description]
    placeholders = ",".join(["%s"] * len(cols))
    insert_sql = f"INSERT INTO `{archive_name}` (`" + "`,`".join(cols) + f"`) VALUES ({placeholders})"
    moved = 0
    while True:
        batch = cur.fetchmany(BATCH)
        if not batch:
            break
        bcur.executemany(insert_sql, batch)
        bak.commit()
        moved += len(batch)
        print(f"    {moved:,}/{n:,}")

    bcur.execute(f"SELECT COUNT(*) FROM `{archive_name}`")
    archived_n = bcur.fetchone()[0]
    if archived_n == n:
        print(f"  OK: {archived_n:,} rows archived. Parity confirmed.")
    else:
        print(f"  WARN: source matched {n:,} but archive has {archived_n:,}")

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(
            f"\n## {ts_utc}  {args.purpose}\n"
            f"- source: `{args.source_db}.{args.source_table}`\n"
            f"- where: `{args.where}`\n"
            f"- archive: `{args.backup_db}.{archive_name}`\n"
            f"- rows: {archived_n:,}\n"
        )
    print(f"  archive logged: {LOG_PATH}")
    src.close(); bak.close()


if __name__ == "__main__":
    main()
