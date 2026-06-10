#!/usr/bin/env python3
"""
reverse_pillar_migration.py
===========================

Reverse migration for the 4 pillar columns added by
`tools/migrate_add_pillar_columns.py` on 2026-06-09.

Drops these columns from BOTH `at_pick_outcomes` and `trading_picks`:
  - market_regime_id
  - sector
  - volatility_atr
  - execution_slippage_pct

Idempotent: pre-checks INFORMATION_SCHEMA and skips any column that doesn't
exist, so re-running is a no-op.

SAFE BY DEFAULT: must pass `--apply` to actually drop columns. Without it,
runs in dry-run mode and prints the exact `ALTER TABLE ... DROP COLUMN` it
would execute.

⚠️  Data loss warning
---------------------
The 4 columns contain backfilled data from `tools/backfill_pillar_columns.py`
(sector, market_regime_id, volatility_atr). Dropping the columns is
destructive and cannot be undone. The companion backup tables
`at_pick_outcomes_pre_pillar_migration_2026_06_09` and
`trading_picks_pre_pillar_migration_2026_06_09` (created 2026-06-09) preserve
a full snapshot for recovery, but the column DATA is lost from the live
tables on drop.

Usage
-----
  python3 tools/reverse_pillar_migration.py                # dry-run
  python3 tools/reverse_pillar_migration.py --apply        # execute

To recover after running --apply:
  - Schema can be re-added by re-running tools/migrate_add_pillar_columns.py --apply
  - Backfilled data would need to be re-run via tools/backfill_pillar_columns.py --apply

Co-Authored-By: Claude <noreply@anthropic.com>
"""
import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pymysql  # noqa: E402
from tools.db_env import get_stocks_creds  # noqa: E402

TARGET_TABLES = ("at_pick_outcomes", "trading_picks")
COLUMNS_TO_DROP = (
    "market_regime_id",
    "sector",
    "volatility_atr",
    "execution_slippage_pct",
)


def get_existing_columns(cur, table: str) -> set:
    cur.execute(
        "SELECT COLUMN_NAME FROM information_schema.columns "
        "WHERE table_schema = DATABASE() AND table_name = %s",
        (table,),
    )
    return {r["COLUMN_NAME"] for r in cur.fetchall()}


def drop_column(cur, table: str, col_name: str, apply: bool) -> str:
    sql = f"ALTER TABLE `{table}` DROP COLUMN `{col_name}`"
    if not apply:
        return f"[DRY-RUN] would: {sql}"
    cur.execute(sql)
    return f"[APPLIED]  {sql}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Actually execute ALTER TABLE DROP COLUMN. Without this flag, runs in dry-run mode.",
    )
    args = ap.parse_args()

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"=== reverse_pillar_migration.py [{mode}] ===\n")

    if args.apply:
        print("⚠️  WARNING: this will drop 4 columns from 2 tables.")
        print("   Pre-backup tables exist (created 2026-06-09) for snapshot recovery:")
        for tbl in TARGET_TABLES:
            print(f"     - {tbl}_pre_pillar_migration_2026_06_09")
        print()

    conn = pymysql.connect(
        **get_stocks_creds(), cursorclass=pymysql.cursors.DictCursor
    )
    cur = conn.cursor()

    try:
        summary = {"dropped": 0, "skipped_not_present": 0}

        for tbl in TARGET_TABLES:
            cur.execute(f"SELECT COUNT(*) c FROM `{tbl}`")
            n_rows = cur.fetchone()["c"]

            existing = get_existing_columns(cur, tbl)
            to_drop = [c for c in COLUMNS_TO_DROP if c in existing]
            already = [c for c in COLUMNS_TO_DROP if c not in existing]

            print(f"--- {tbl} ({n_rows} rows) ---")
            print(f"  columns to drop:     {COLUMNS_TO_DROP}")
            print(f"  already absent:     {already}")
            print(f"  need drop:          {to_drop}")
            print()

            for col_name in COLUMNS_TO_DROP:
                if col_name not in existing:
                    summary["skipped_not_present"] += 1
                    print(f"  SKIP  {col_name} (not present)")
                    continue
                try:
                    msg = drop_column(cur, tbl, col_name, apply=args.apply)
                    summary["dropped"] += 1
                    print(f"  {msg}")
                except pymysql.err.OperationalError as e:
                    # MySQL 1091 = can't DROP ... check that column/key exists
                    if e.args and e.args[0] == 1091:
                        summary["skipped_not_present"] += 1
                        print(f"  SKIP  {col_name} (race: column gone)")
                    else:
                        raise

        if args.apply:
            conn.commit()
            print("\n[COMMITTED]")
        else:
            conn.rollback()
            print("\n[ROLLED BACK — dry-run, no changes]")

        print(
            f"\nSummary: dropped={summary['dropped']}, "
            f"skipped_not_present={summary['skipped_not_present']}"
        )
        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
