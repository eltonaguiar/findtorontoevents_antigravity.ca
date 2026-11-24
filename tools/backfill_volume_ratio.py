#!/usr/bin/env python3
"""Backfill `volume_ratio_at_entry` on resolved signal outcomes (dry-run by default).

Definition: the entry bar's volume divided by the median volume of the 20 bars
immediately before it (same symbol + timeframe). A value of 1.0 means normal
participation; 2.0 means twice the recent median. It is recorded at entry, never
reconstructed later from future bars.

Why this exists: the column does not exist on `at_signal_outcomes`, so 0 of 3,500
closed rows carry it and every volume A/B is impossible (buffy, 2026-11-19).
This tool is the backfiller; the resolver should call the same pure function at
write time so new rows never need backfilling.

Safety: default is a DRY RUN that only counts and samples. `--apply` adds the
column (via the SQL migration guard) and updates NULL rows in bounded batches.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

DEFAULT_WINDOW = 20
DEFAULT_TIMEFRAME = "1h"

SIDECAR_DDL = """
CREATE TABLE IF NOT EXISTS at_signal_volume_context (
  outcome_id INT PRIMARY KEY,
  symbol VARCHAR(50) NOT NULL,
  volume_ratio_at_entry DECIMAL(12,4) NOT NULL,
  window_bars TINYINT NOT NULL DEFAULT 20,
  timeframe VARCHAR(10) NOT NULL DEFAULT '1h',
  computed_at DATETIME NOT NULL,
  KEY idx_symbol (symbol)
) ENGINE=InnoDB
"""


def volume_ratio(volumes: list[float], idx: int, window: int = DEFAULT_WINDOW) -> float | None:
    """Vol[idx] / median(prior `window` bars). None when there is not enough history."""
    if idx < window or idx >= len(volumes):
        return None
    prior = [float(v) for v in volumes[idx - window:idx] if v is not None and float(v) > 0]
    if len(prior) < window or not volumes[idx] or float(volumes[idx]) <= 0:
        return None
    med = statistics.median(prior)
    if med <= 0:
        return None
    return round(float(volumes[idx]) / med, 4)


def _conn():
    import pymysql
    from tools.db_env import get_stocks_creds

    keep = ("host", "user", "password", "database", "port", "connect_timeout")
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor,
                           **{k: v for k, v in get_stocks_creds().items() if k in keep})


def _table_for(asset_class: str) -> str:
    return "crypto_ohlcv" if str(asset_class or "").upper() in ("CRYPTO", "MEMECOIN") else "stock_ohlcv"


def _has_column(conn) -> bool:
    cur = conn.cursor()
    cur.execute("SHOW COLUMNS FROM at_signal_outcomes LIKE 'volume_ratio_at_entry'")
    return cur.fetchone() is not None


def _batches(conn, limit: int, has_col: bool = True):
    cur = conn.cursor()
    where = "opened_at IS NOT NULL"
    if has_col:
        where += " AND volume_ratio_at_entry IS NULL"
    cur.execute(
        f"SELECT id, symbol, asset_class, opened_at FROM at_signal_outcomes "
        f"WHERE {where} ORDER BY opened_at DESC LIMIT %s", (limit,))
    return cur.fetchall()


def _ms(dt) -> int:
    """OHLCV.timestamp is epoch milliseconds (bigint), not a DATETIME."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _bars(conn, table: str, symbol: str, start, end, timeframe: str):
    cur = conn.cursor()
    cur.execute(
        f"SELECT timestamp, volume FROM {table} WHERE symbol=%s AND timeframe=%s "
        "AND timestamp BETWEEN %s AND %s ORDER BY timestamp",
        (symbol, timeframe, _ms(start), _ms(end)))
    return cur.fetchall()


def plan(conn, limit: int = 500, timeframe: str = DEFAULT_TIMEFRAME) -> dict:
    """Dry-run: what would be filled, and how often. No writes."""
    has_col = _has_column(conn)
    rows = _batches(conn, limit, has_col)
    filled, skipped, sample = 0, 0, []
    cache: dict[tuple, list] = {}
    for r in rows:
        table = _table_for(r["asset_class"])
        key = (table, r["symbol"])
        if key not in cache:
            start = r["opened_at"] - timedelta(days=10)
            cache[key] = _bars(conn, table, r["symbol"], start, r["opened_at"], timeframe)
        bars = cache[key]
        idx = len(bars) - 1 if bars else -1
        ratio = volume_ratio([b["volume"] for b in bars], idx)
        if ratio is None:
            skipped += 1
        else:
            filled += 1
            if len(sample) < 5:
                sample.append({"id": r["id"], "symbol": r["symbol"], "ratio": ratio})
    return {"column_present": has_col, "candidates": len(rows),
            "would_fill": filled, "skipped": skipped, "sample": sample,
            "applied": False,
            "note": ("dry run only; --apply adds the column and writes"
                     if not has_col else "dry run only")}


def apply(conn, limit: int = 500, timeframe: str = DEFAULT_TIMEFRAME,
          mode: str = "sidecar") -> dict:
    """Write the values. mode='sidecar' (default) never touches at_signal_outcomes."""
    cur = conn.cursor()
    if mode == "sidecar":
        cur.execute(SIDECAR_DDL)
        conn.commit()
        rows = _batches(conn, limit, False)
    else:
        if not _has_column(conn):
            cur.execute("ALTER TABLE at_signal_outcomes ADD COLUMN volume_ratio_at_entry "
                        "DECIMAL(12,4) NULL COMMENT 'entry-bar volume / prior-20-bar median' "
                        "AFTER asset_class")
            conn.commit()
        rows = _batches(conn, limit, True)
    updated, skipped = 0, 0
    cache: dict[tuple, list] = {}
    for r in rows:
        table = _table_for(r["asset_class"])
        key = (table, r["symbol"])
        if key not in cache:
            start = r["opened_at"] - timedelta(days=10)
            cache[key] = _bars(conn, table, r["symbol"], start, r["opened_at"], timeframe)
        bars = cache[key]
        idx = len(bars) - 1 if bars else -1
        ratio = volume_ratio([b["volume"] for b in bars], idx)
        if ratio is None:
            skipped += 1
            continue
        if mode == "sidecar":
            cur.execute(
                "INSERT INTO at_signal_volume_context "
                "(outcome_id, symbol, volume_ratio_at_entry, window_bars, timeframe, computed_at) "
                "VALUES (%s, %s, %s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE volume_ratio_at_entry=VALUES(volume_ratio_at_entry), "
                "computed_at=VALUES(computed_at)",
                (r["id"], r["symbol"], ratio, DEFAULT_WINDOW, timeframe,
                 datetime.now(timezone.utc).replace(tzinfo=None)))
        else:
            cur.execute("UPDATE at_signal_outcomes SET volume_ratio_at_entry=%s WHERE id=%s",
                        (ratio, r["id"]))
        updated += 1
    conn.commit()
    return {"mode": mode, "candidates": len(rows), "updated": updated,
            "skipped": skipped, "applied": True,
            "rolled_back_by": ("DROP TABLE at_signal_volume_context" if mode == "sidecar"
                               else "ALTER TABLE ... DROP COLUMN (backup is forensic only)")}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="backfill volume_ratio_at_entry (dry-run default)")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=500)
    ap.add_argument("--timeframe", default=DEFAULT_TIMEFRAME)
    ap.add_argument("--mode", choices=("sidecar", "column"), default="sidecar",
                    help="sidecar (default, no ALTER) or column (ALTER + backup needed)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    conn = _conn()
    try:
        rep = apply(conn, args.limit, args.timeframe, args.mode) if args.apply \
            else {**plan(conn, args.limit, args.timeframe), "mode": args.mode}
    finally:
        conn.close()
    print(json.dumps(rep, indent=1) if args.json else rep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
