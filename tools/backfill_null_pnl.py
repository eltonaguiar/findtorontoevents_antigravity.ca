#!/usr/bin/env python3
"""
Backfill NULL pnl_pct for resolved picks where entry_price + exit_price are available.

Root cause: resolver marks TP_HIT/SL_HIT but doesn't always compute pnl_pct.
Formula: LONG = (exit - entry) / entry; SHORT = (entry - exit) / entry

Run: python3 tools/backfill_null_pnl.py [--dry-run]
"""
from __future__ import annotations
import os
import sys
import argparse
from decimal import Decimal

REPO = __file__
for _ in range(2):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, REPO)

import pymysql

CLOSED_STATUSES = ("LOST", "SL_HIT", "TIME_EXIT", "TP_HIT", "EXPIRED",
                   "LOSS", "WIN", "FORCE_CLOSED_TOXIC")


def connect():
    from tools.db_env import get_stocks_creds
    return pymysql.connect(
        **get_stocks_creds(),
        connect_timeout=15,
        cursorclass=pymysql.cursors.DictCursor,
    )


def compute_pnl(row: dict) -> float | None:
    entry = row.get("entry_price")
    exit_ = row.get("exit_price")
    direction = str(row.get("direction") or "LONG").upper()
    if not entry or not exit_ or float(entry) <= 0:
        return None
    e = float(entry)
    x = float(exit_)
    if direction == "LONG":
        return (x - e) / e
    else:
        return (e - x) / e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=10000, help="Max rows to fix per run")
    args = ap.parse_args()

    conn = connect()
    cursor = conn.cursor()

    placeholders = ",".join(["%s"] * len(CLOSED_STATUSES))
    cursor.execute(
        f"""SELECT id, direction, entry_price, exit_price, status, source_system
            FROM trading_picks
            WHERE pnl_pct IS NULL
            AND entry_price IS NOT NULL AND exit_price IS NOT NULL
            AND status IN ({placeholders})
            LIMIT %s""",
        (*CLOSED_STATUSES, args.limit),
    )
    rows = cursor.fetchall()
    print(f"Found {len(rows)} rows with NULL pnl_pct and valid entry/exit prices")

    fixed = 0
    skipped = 0
    sign_violations = 0
    for row in rows:
        pnl = compute_pnl(row)
        if pnl is None:
            skipped += 1
            continue
        # Hard cap: pnl > 500% almost always means price-unit mismatch
        # (e.g. SHIB entry in USDT-fraction, exit in whole-number scale).
        # Leave these NULL rather than contaminating metrics.
        if abs(pnl) > 5.0:  # 500% in decimal fraction
            skipped += 1
            continue
        status = str(row.get("status") or "")
        # Respect chk_pnl_sign_coherence constraint
        if status in ("TP_HIT", "WON", "closed_win") and pnl < -0.01:
            sign_violations += 1
            continue
        if status in ("SL_HIT", "LOST", "closed_loss") and pnl > 0.01:
            sign_violations += 1
            continue
        if not args.dry_run:
            cursor.execute(
                "UPDATE trading_picks SET pnl_pct = %s WHERE id = %s",
                (round(pnl, 8), row["id"]),
            )
        fixed += 1

    if not args.dry_run:
        conn.commit()
        print(f"Fixed: {fixed} rows | Skipped (no valid prices): {skipped} | Sign violations: {sign_violations}")
    else:
        print(f"DRY RUN — would fix: {fixed} rows | skip: {skipped} | sign violations: {sign_violations}")
        if rows:
            r = rows[0]
            pnl = compute_pnl(r)
            print(f"  Sample: id={r['id']} {r['direction']} entry={r['entry_price']} exit={r['exit_price']} → pnl={pnl:.4%}")

    conn.close()


if __name__ == "__main__":
    main()
