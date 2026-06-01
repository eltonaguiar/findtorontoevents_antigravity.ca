#!/usr/bin/env python3
"""
SAFE DB ARCHIVE — implements Hermes rule #1.

Before any significant table modification, archive the affected slice of the
source table into `ejaguiar1_backups.<source_table>_<purpose>_<utc_ts>`.
Default mode is DRY-RUN; pass --apply to actually copy.

Usage:
  python tools/safe_db_archive.py \\
      --source-table trading_picks \\
      --where "trust_score IS NULL" \\
      --purpose trust_score_backfill
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if sys.platform == "win32":
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            try:
                s.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from tools.db_backup import archive_table_slice  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-db", default="ejaguiar1_stocks")
    ap.add_argument("--backup-db", default="ejaguiar1_backups")
    ap.add_argument("--source-table", required=True)
    ap.add_argument("--where", required=True, help="WHERE clause body (no leading WHERE)")
    ap.add_argument("--purpose", required=True, help="Slug like 'trust_score_backfill'")
    ap.add_argument("--apply", action="store_true", help="Actually copy (default: dry-run)")
    ap.add_argument("--max-rows", type=int, default=500_000)
    args = ap.parse_args()

    result = archive_table_slice(
        source_table=args.source_table,
        where=args.where,
        purpose=args.purpose,
        apply=args.apply,
        source_db=args.source_db,
        backup_db=args.backup_db,
        max_rows=args.max_rows,
    )
    if result.row_count == 0:
        return
    if args.apply and not result.applied:
        sys.exit(1)


if __name__ == "__main__":
    main()
