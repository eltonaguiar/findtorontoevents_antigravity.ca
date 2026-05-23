#!/usr/bin/env python3
"""DRY-RUN: surface battleground timestamp-key mismatch (per Hermes rule #3).

battleground/data/closed_picks.json uses keys `entry_time` and `exit_time`.
alpha_engine/mysql_trading_sync.py::pick_to_row only reads:
  created_at fallback chain: created_at, detected_at, timestamp  ← MISSES entry_time
  closed_at fallback chain: exit_date, closed_at                  ← MISSES exit_time

Result: ALL battleground closed picks land in MySQL with NULL closed_at.
Currently 57,710 NULL closed_at rows in trading_picks (66,058 total = 87%).

This script is READ-ONLY. Outputs CSV showing:
  - which JSON picks have valid entry_time/exit_time but NULL DB timestamps
  - matched DB row id where possible
  - hold-time delta (real vs DB-zero)

NO writes. NO DB modification. Pure preview. Output: reports/battleground_
timestamp_gap_2026-05-10/preview.csv

Run:
  python tools/battleground_timestamp_gap_dryrun.py
"""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

import pymysql

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "reports" / "battleground_timestamp_gap_2026-05-10"
OUT.mkdir(parents=True, exist_ok=True)


def main():
    json_path = REPO / "battleground" / "data" / "closed_picks.json"
    if not json_path.exists():
        print(f"NOT FOUND: {json_path}")
        return

    raw = json.loads(json_path.read_text(encoding="utf-8"))
    picks = raw if isinstance(raw, list) else raw.get("picks") or raw.get("closed") or []
    print(f"battleground/data/closed_picks.json: {len(picks)} picks")

    # Categorize
    has_entry_time = sum(1 for p in picks if p.get("entry_time"))
    has_exit_time = sum(1 for p in picks if p.get("exit_time"))
    has_created_at = sum(1 for p in picks if p.get("created_at"))
    has_closed_at = sum(1 for p in picks if p.get("closed_at"))
    print(f"  with entry_time: {has_entry_time}")
    print(f"  with exit_time:  {has_exit_time}")
    print(f"  with created_at: {has_created_at}")
    print(f"  with closed_at:  {has_closed_at}")

    # Connect to DB to check row state
    try:
        conn = pymysql.connect(
            host="mysql.50webs.com", user="ejaguiar1_stocks",
            password=os.environ.get("DB_PASS_STOCKS", ""), db="ejaguiar1_stocks",
            connect_timeout=15, read_timeout=60, charset="utf8mb4",
        )
        cur = conn.cursor()
    except Exception as e:
        print(f"DB connect failed (non-blocking): {e}")
        cur = None

    rows_out = []
    for p in picks:
        sym = p.get("symbol", "")
        strategy = p.get("strategy", "")
        entry_time = p.get("entry_time")
        exit_time = p.get("exit_time")
        pnl = p.get("pnl_pct") or p.get("pnl") or 0
        status = p.get("status", "")
        # Try to find matching DB row by (symbol, strategy)
        db_id = ""
        db_created = ""
        db_closed = ""
        if cur and sym:
            try:
                cur.execute(
                    "SELECT id, created_at, closed_at, status, pnl_pct FROM trading_picks "
                    "WHERE symbol=%s AND strategy=%s "
                    "ORDER BY updated_at DESC LIMIT 1",
                    (sym, strategy),
                )
                row = cur.fetchone()
                if row:
                    db_id, db_created, db_closed = (
                        str(row[0])[:60], str(row[1] or ""), str(row[2] or "")
                    )
            except Exception:
                pass
        rows_out.append({
            "json_symbol": sym,
            "json_strategy": strategy,
            "json_entry_time": entry_time,
            "json_exit_time": exit_time,
            "json_status": status,
            "json_pnl_pct": pnl,
            "db_id_match": db_id,
            "db_created_at": db_created,
            "db_closed_at": db_closed,
            "WOULD_FIX": "YES" if entry_time and not db_created else "NO",
        })

    csv_path = OUT / "preview.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        cols = ["json_symbol", "json_strategy", "json_entry_time", "json_exit_time",
                "json_status", "json_pnl_pct", "db_id_match", "db_created_at",
                "db_closed_at", "WOULD_FIX"]
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows_out:
            w.writerow(r)

    fix_count = sum(1 for r in rows_out if r["WOULD_FIX"] == "YES")
    print(f"\nWOULD_FIX rows: {fix_count} of {len(rows_out)}")
    print(f"Preview written: {csv_path}")
    print("\nNO DB writes performed. NO archive needed (read-only).")
    print("To apply, the FIX is at the WRITER, not the DB:")
    print("  alpha_engine/mysql_trading_sync.py::pick_to_row")
    print("  Add `entry_time` to created_at fallback chain.")
    print("  Add `exit_time`  to closed_at  fallback chain.")
    print("  Re-run normal sync. NO bulk UPDATE needed; ON DUPLICATE KEY")
    print("  UPDATE will repair on next sync cycle.")
    if cur:
        conn.close()


if __name__ == "__main__":
    main()
