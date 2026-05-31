#!/usr/bin/env python3
"""
Backfill NULL/UNKNOWN/empty trading_picks.category using detect_asset_class().

Addresses INC P2 OVERALL: UNKNOWN asset_class on active + closed picks.

Usage:
  python3 tools/backfill_unknown_category.py           # dry-run counts
  python3 tools/backfill_unknown_category.py --apply   # UPDATE rows
"""

from __future__ import annotations

import argparse
import os
import sys

import pymysql

# Repo root on path for alpha_engine imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from alpha_engine.config import detect_asset_class  # noqa: E402

_DB = dict(
    host=os.getenv("DB_HOST_STOCKS", "mysql.50webs.com"),
    user=os.getenv("DB_USER_STOCKS", "ejaguiar1_stocks"),
    password=os.getenv("DB_PASS_STOCKS", ""),
    database=os.getenv("DB_NAME_STOCKS", "ejaguiar1_stocks"),
    charset="utf8mb4",
    connect_timeout=20,
)

_CATEGORY_MAP = {
    "crypto": "CRYPTO",
    "bond": "BOND",
    "commodity": "COMMODITY",
    "futures": "FUTURES",
    "etf": "ETF",
    "forex": "FOREX",
    "equity": "EQUITY",
}


def _normalize_db_category(detected: str) -> str | None:
    key = (detected or "").strip().lower()
    if key == "unknown" or not key:
        return None
    return _CATEGORY_MAP.get(key, key.upper())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=5000)
    args = ap.parse_args()

    if not _DB["password"]:
        print("DB_PASS_STOCKS not set", file=sys.stderr)
        return 1

    conn = pymysql.connect(**_DB, cursorclass=pymysql.cursors.DictCursor)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, symbol, category
        FROM trading_picks
        WHERE category IS NULL OR category = '' OR UPPER(category) = 'UNKNOWN'
        LIMIT %s
        """,
        (args.limit,),
    )
    rows = cur.fetchall()
    updates: list[tuple[str, int]] = []
    skipped = 0
    for row in rows:
        new_cat = _normalize_db_category(detect_asset_class(str(row.get("symbol") or "")))
        if not new_cat:
            skipped += 1
            continue
        updates.append((new_cat, row["id"]))

    print(f"scanned={len(rows)} updatable={len(updates)} skipped_unknown_symbol={skipped}")
    if args.apply and updates:
        for cat, pk in updates:
            cur.execute(
                "UPDATE trading_picks SET category=%s, updated_at=NOW() WHERE id=%s",
                (cat, pk),
            )
        conn.commit()
        print(f"applied={len(updates)}")
    elif not args.apply and updates:
        print("dry-run only — pass --apply to write")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
