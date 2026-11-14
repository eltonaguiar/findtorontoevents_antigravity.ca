#!/usr/bin/env python3
"""
Backfill missing exit_price on closed picks in MySQL trading_picks.

Problem: ~33% of closed picks have exit_price=None despite status=CLOSED,
breaking PnL calculation and downstream analytics.

Strategy:
  1. Find rows where status is terminal AND (exit_price IS NULL OR exit_price=0)
     AND entry_price > 0.
  2. If a last-known current_price exists in the row, use it (rare but best).
  3. Otherwise fallback to entry_price as breakeven (pnl_pct=0.0).
  4. Tag exit_reason with BACKFILL_BREAKEVEN so analytics can filter.

Usage:
    python3 tools/backfill_missing_exit_prices.py        # dry-run (print summary)
    python3 tools/backfill_missing_exit_prices.py --apply # write to DB
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

try:
    import pymysql
except ImportError as e:
    print(f"Missing dependency: {e}", file=sys.stderr)
    sys.exit(1)

from tools.db_env import get_stocks_creds  # noqa: E402

_KEEP = ("host", "user", "password", "database", "port", "connect_timeout")
TERMINAL_STATUSES = (
    "CLOSED", "WON", "LOST", "EXPIRED", "TIME_EXIT",
    "TP_HIT", "SL_HIT", "RESOLVED", "FLAT",
)


def _connect():
    creds = {k: v for k, v in get_stocks_creds().items() if k in _KEEP}
    return pymysql.connect(**creds, cursorclass=pymysql.cursors.DictCursor)


def backfill(dry_run: bool = True) -> dict:
    conn = _connect()
    cur = conn.cursor()

    # Count eligible rows
    cur.execute(
        """
        SELECT COUNT(*) AS n
        FROM trading_picks
        WHERE status IN %(statuses)s
          AND (exit_price IS NULL OR exit_price = 0)
          AND entry_price > 0
        """,
        {"statuses": TERMINAL_STATUSES},
    )
    total_eligible = cur.fetchone()["n"]

    if total_eligible == 0:
        print("[backfill] No rows need backfilling.")
        conn.close()
        return {"eligible": 0, "updated": 0, "skipped": 0}

    print(f"[backfill] Eligible rows: {total_eligible}")

    # Pull IDs + data needed for fallback decision
    cur.execute(
        """
        SELECT id, symbol, status, entry_price, current_price, exit_reason, closed_at
        FROM trading_picks
        WHERE status IN %(statuses)s
          AND (exit_price IS NULL OR exit_price = 0)
          AND entry_price > 0
        """,
        {"statuses": TERMINAL_STATUSES},
    )
    rows = cur.fetchall()

    updated = 0
    skipped = 0
    for row in rows:
        entry = float(row["entry_price"])
        current = row["current_price"]
        fallback = None
        reason_tag = "BACKFILL_BREAKEVEN"

        # Prefer last-known current_price if it differs from entry
        if current is not None:
            try:
                cur_p = float(current)
                if cur_p > 0 and abs(cur_p - entry) / entry > 0.00001:
                    fallback = cur_p
                    reason_tag = "BACKFILL_FALLBACK_CURRENT"
            except (TypeError, ValueError):
                pass

        if fallback is None:
            fallback = entry

        new_reason = row["exit_reason"] or ""
        if reason_tag not in new_reason:
            new_reason = f"{new_reason}|{reason_tag}".lstrip("|")

        if not dry_run:
            cur.execute(
                """
                UPDATE trading_picks
                SET exit_price = %s,
                    pnl_pct = %s,
                    exit_reason = %s,
                    closed_at = COALESCE(closed_at, NOW())
                WHERE id = %s
                """,
                (fallback, 0.0, new_reason, row["id"]),
            )
            if cur.rowcount > 0:
                updated += 1
            else:
                skipped += 1
        else:
            # In dry-run, count as would-update
            updated += 1

    if not dry_run:
        conn.commit()
        print(f"[backfill] Committed {updated} updates, {skipped} skipped.")
    else:
        print(f"[backfill] DRY-RUN: would update {updated} rows, skip {skipped}.")

    conn.close()
    return {"eligible": total_eligible, "updated": updated, "skipped": skipped}


def main() -> int:
    ap = argparse.ArgumentParser(description="Backfill missing exit_price on closed picks")
    ap.add_argument("--apply", action="store_true", help="write to DB")
    args = ap.parse_args()

    result = backfill(dry_run=not args.apply)
    if result["eligible"]:
        print(f"\nSummary: eligible={result['eligible']} updated={result['updated']} skipped={result['skipped']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
