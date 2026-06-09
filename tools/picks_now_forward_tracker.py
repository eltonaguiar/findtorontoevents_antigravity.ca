#!/usr/bin/env python3
"""
PICKS NOW FORWARD TRACKER (Phase C, 2026-06-09)
================================================
Snapshots every emit of picks_now.json into a `picks_now_emits` history table,
joins against at_pick_outcomes to compute per-emit forward WR/PF/avg_pnl, and
publishes a `forward_perf_panel` block back to picks_now.json so the page
shows bucketed forward performance (1h/4h/24h/7d/30d).

Methodology
-----------
1. **Emit snapshot**: every row in picks_now.json's `picks` (top BUY list) and
   the per-class `all` slices is inserted into `picks_now_emits` with the
   (emit_ts, symbol, direction, suggested_tp_pct, suggested_sl_pct) tuple as
   the natural key. Idempotent (INSERT IGNORE on the unique key).

2. **Resolution join**: each emit row is matched to at_pick_outcomes by
   (symbol, asset_class, direction, entry_price within ±2% of stored TP price
   proxy). The most-recent matching resolved_at is used. Emits that haven't
   been resolved yet are flagged as `pending`.

3. **Bucketed stats**: emits are bucketed by `age = NOW - emit_ts`:
       1h, 4h, 24h, 7d, 30d
   For each bucket: n, wins, losses, expired, flat, WR (denom = WON+LOST,
   EXPIRED honest), PF, avg_pnl, n_pending.

4. **Publish**: writes the bucketed stats + a `picks_now_emits_total` row
   count to picks_now.json under the `forward_perf_panel` key. The page
   reads this on load and renders a single line per bucket, plus a small
   "tracker status" footer.

5. **Backfill on first run**: if the table is empty, the script will also
   back-insert the last 7 days of `picks_now_tracker` rows so we have
   something to evaluate immediately. This is gated by a flag and is one-shot.

Usage
-----
    python3 tools/picks_now_forward_tracker.py            # full run
    python3 tools/picks_now_forward_tracker.py --no-insert  # read-only (rebuild panel)
    python3 tools/picks_now_forward_tracker.py --backfill   # force backfill

Output
------
    audit_dashboard/data/picks_now.json  (mutated: adds forward_perf_panel)
    MySQL table `picks_now_emits`        (appended)

Safety
------
- INSERT IGNORE on the unique key — safe to re-run.
- All DB writes are best-effort. If the DB is unreachable, the script still
  reads picks_now.json, computes the panel from at_pick_outcomes alone (with
  a degraded match), and writes the panel.
- No destructive operations; no DROP/TRUNCATE.
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# Import the project-standard DB resolver
DB_CREDS = None
try:
    from tools.db_env import get_stocks_creds
    DB_CREDS = get_stocks_creds(raise_on_missing=False)
except Exception:
    DB_CREDS = None

JSON_PATH = REPO / "audit_dashboard" / "data" / "picks_now.json"
REPORT_PATH = REPO / "reports" / f"picks_now_forward_perf_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"

# Emit age buckets (in hours)
BUCKETS_HOURS = [
    ("1h",  1),
    ("4h",  4),
    ("24h", 24),
    ("7d",  24 * 7),
    ("30d", 24 * 30),
]

# Sane-pnl caps per asset class (mirror build_pf_registry / picks_now_professional)
SANE_PNL_CAP = {
    "FOREX": 20.0, "COMMODITY": 30.0, "BOND": 25.0,
    "CRYPTO": 95.0, "EQUITY": 50.0, "ETF": 50.0,
}

# Direction normalization
DIR_NORM = {
    "STRONG_BUY": "LONG", "BUY": "LONG", "LONG": "LONG",
    "STRONG_SELL": "SHORT", "SELL": "SHORT", "SHORT": "SHORT",
    "WATCH": "LONG", "HOLD": "LONG", "WEAK": "LONG", "AVOID": "LONG",
    None: "LONG", "": "LONG",
}


def _get_conn():
    """Return a pymysql connection or None if creds are missing."""
    if not DB_CREDS or not DB_CREDS.get("password"):
        return None
    import pymysql
    return pymysql.connect(**DB_CREDS, cursorclass=pymysql.cursors.DictCursor)


def ensure_table(conn):
    """Create picks_now_emits if it doesn't exist (idempotent)."""
    if conn is None:
        return False
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS picks_now_emits (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            emit_ts DATETIME NOT NULL,
            symbol VARCHAR(20) NOT NULL,
            asset_class VARCHAR(20) NOT NULL,
            direction VARCHAR(10) NOT NULL,
            strategy VARCHAR(50) DEFAULT NULL,
            entry_price DECIMAL(12,4) DEFAULT NULL,
            suggested_tp_pct DECIMAL(6,2) DEFAULT NULL,
            suggested_sl_pct DECIMAL(6,2) DEFAULT NULL,
            score DECIMAL(6,1) DEFAULT NULL,
            dbf_active TINYINT(1) DEFAULT 0,
            dbf_wr DECIMAL(5,1) DEFAULT NULL,
            dbf_n_weighted DECIMAL(8,2) DEFAULT NULL,
            tp_sl_quality_score DECIMAL(5,1) DEFAULT NULL,
            emi