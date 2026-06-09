#!/usr/bin/env python3
"""
migrate_add_pillar_columns.py
=============================

Idempotent schema migration: adds 4 new columns to `at_pick_outcomes` and
`trading_picks` to support the 5-pillar reliability framework (P2 regime,
P3 execution, P5 sector/concentration).

Columns added to BOTH tables:
  - market_regime_id        ENUM('BULL','BEAR','SIDEWAYS','HIGH_VOL','RISK_OFF','UNKNOWN') DEFAULT 'UNKNOWN'
  - sector                  VARCHAR(64)  NULL
  - volatility_atr          DECIMAL(10,4) NULL
  - execution_slippage_pct  DECIMAL(8,4)  NULL

ALL columns are added as NULLABLE (no DEFAULT enforced for the NUMERIC cols,
sensible DEFAULT for the ENUM) so this migration is a pure schema-only
change: it does not touch existing rows, it does not backfill, it does not
block. A follow-up tool/session does the backfill.

Idempotency: pre-checks INFORMATION_SCHEMA and skips any column that already
exists, so re-running this script is a no-op.

Usage:
  python3 tools/migrate_add_pillar_columns.py            # dry-run
  python3 tools/migrate_add_pillar_columns.py --apply    # execute ALTER TABLE

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

# ---------------------------------------------------------------------------
# Migration definition
# ---------------------------------------------------------------------------

TARGET_TABLES = ("at_pick_outcomes", "trading_picks")

COLUMNS = (
    # (name, ddl_clause_for_add_column)
    (
        "market_regime_id",
        "ENUM('BULL','BEAR','SIDEWAYS','HIGH_VOL','RISK_OFF','UNKNOWN') NOT NULL DEFAULT 'UNKNOWN'",
    ),
    (
        "sector",
        "VARCHAR(64) NULL",
    ),
    (
        "volatility_atr",
        "DECIMAL(10,4) NULL",
    ),
    (
        "execution_slippage_pct",
        "DECIMAL(8,4) NULL",
    ),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_existing_columns(cur, table: str) -> set:
    cur.execute(
        "SELECT COLUMN_NAME FROM information_schema.columns "
        "WHERE table_schema = DATABASE() AND table_name = %s",
        (table,),
    )
    return {r["COLUMN_NAME"] for r in cur.fetchall()}


def add_column(cur, table: str, col_name: str, ddl: str, apply: bool) -> str:
    sql = f"ALTER TABLE `{table}` ADD COLUMN `{col_name}` {ddl}"
    if not apply:
        return f"[DRY-RUN] would: {sql}"
    cur.execute(sql)
    return f"[APPLIED]  {sql}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Actually execute ALTER TABLE. Without this flag, runs in dry-run mode.",
    )
    args = ap.parse_args()

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"=== migrate_add_pillar_columns.py [{mode}] ===\n")

    conn = pymysql.connect(
        **get_stocks_creds(), cursorclass=pymysql.cursors.DictCursor
    )
    cur = conn.cursor()

    try:
        summary = {"added": 0, "skipped_existing": 0}

        for tbl in TARGET_TABLES:
            # Row count for the record
            cur.execute(f"SELECT COUNT(*) c FROM `{tbl}`")
            n_rows = cur.fetchone()["c"]

            existing = get_existing_columns(cur, tbl)
            new_cols = [c for c, _ in COLUMNS]
            missing = [c for c in new_cols if c not in existing]
            already = [c for c in new_cols if c in existing]

            print(f"--- {tbl} ({n_rows} rows) ---")
            print(f"  columns to add:    {new_cols}")
            print(f"  already present:   {already}")
            print(f"  need migration:    {missing}")
            print()

            for col_name, ddl in COLUMNS:
                if col_name in existing:
                    summary["skipped_existing"] += 1
                    print(f"  SKIP  {col_name} (already exists)")
                    continue
                try:
                    msg = add_column(cur, tbl, col_name, ddl, apply=args.apply)
                    summary["added"] += 1
                    print(f"  {msg}")
                except pymysql.err.OperationalError as e:
                    # MySQL 1060 = duplicate column (race with another migrator)
                    if e.args and e.args[0] == 1060:
                        summary["skipped_existing"] += 1
                        print(f"  SKIP  {col_name} (race: duplicate column)")
                    else:
                        raise

        if args.apply:
            conn.commit()
            print("\n[COMMITTED]")
        else:
            conn.rollback()
            print("\n[ROLLED BACK — dry-run, no changes]")

        print(
            f"\nSummary: added={summary['added']}, "
            f"skipped_existing={summary['skipped_existing']}"
        )
        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
