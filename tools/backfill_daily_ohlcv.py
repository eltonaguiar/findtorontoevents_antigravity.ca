#!/usr/bin/env python3
"""backfill_daily_ohlcv.py — gap-fill daily bars for equity / ETF / futures tables.

Why
---
The G8 selection-alpha gate needs a bar at or after each pick's exit timestamp.
On 2026-11-19 three tables had stopped well before the picks did, so whole asset
classes could not be measured at all:

    equity_daily_ohlcv    last bar 2026-06-18   (486 of 765 equity picks closed after)
    fx_prices             last bar 2026-02-09   (handled by tools/fx_backfill.py)
    futures_daily_ohlcv   last bar 2026-06-21   (51 of 51 commodity picks closed after)
    etf_daily_ohlcv       last bar 2026-10-30, only 36 symbols tracked

That is a data gap, not a code bug. This tool closes it from yfinance, which is
already the source the repo uses for these tables.

Safety
------
* **Dry run by default** — prints the universe and window, touches no network and
  no database. ``--apply`` is the deliberate act.
* Upsert only: ``INSERT ... ON DUPLICATE KEY UPDATE`` against the existing unique
  keys (``uk_eq``/``uk``/``uk_fut`` on ``(symbol, trade_date)``). Re-running is
  idempotent; no row is deleted and no schema is changed.
* ``--since`` bounds what is written, so a wide yfinance window cannot rewrite
  history that is already stored.
* Credentials come from ``tools/db_env`` and are never printed.

Usage
-----
    python3 tools/backfill_daily_ohlcv.py --since 2026-06-18
    python3 tools/backfill_daily_ohlcv.py --since 2026-06-18 --apply

    # only the ETF table, widening its universe
    python3 tools/backfill_daily_ohlcv.py --tables etf --since 2026-10-30 --apply
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import date, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

TABLE_ALIASES = {
    "equity": "equity_daily_ohlcv",
    "etf": "etf_daily_ohlcv",
    "futures": "futures_daily_ohlcv",
}

UPSERT = (
    "INSERT INTO `{table}` (symbol, trade_date, open, high, low, close, volume) "
    "VALUES (%s,%s,%s,%s,%s,%s,%s) "
    "ON DUPLICATE KEY UPDATE open=VALUES(open), high=VALUES(high), low=VALUES(low), "
    "close=VALUES(close), volume=VALUES(volume)"
)


def _db():
    from tools.db_env import get_stocks_creds
    import pymysql

    keep = ("host", "user", "password", "database", "port", "connect_timeout")
    return pymysql.connect(read_timeout=120, write_timeout=120,
                           **{k: v for k, v in get_stocks_creds().items() if k in keep})


def _extra_symbols(table: str) -> list[str]:
    """Symbols the class universe should include even if the table lacks them.

    ETF was tracked on 36 symbols while the product ships picks on many more, so
    widening the universe is as important as advancing the last date.
    """
    try:
        from alpha_engine.asset_class import (COMMODITY_SYMBOLS, EQUITY_SYMBOLS,
                                              ETF_SYMBOLS, BOND_SYMBOLS)
    except Exception:  # pragma: no cover - defensive
        return []
    if table == "etf_daily_ohlcv":
        return sorted(ETF_SYMBOLS | BOND_SYMBOLS)
    if table == "equity_daily_ohlcv":
        return sorted(EQUITY_SYMBOLS)
    if table == "futures_daily_ohlcv":
        return sorted(f"{c}=F" if "=" not in c else c for c in COMMODITY_SYMBOLS)
    return []


def universe(table: str, cur, extra: bool = True) -> list[str]:
    cur.execute(f"SELECT DISTINCT symbol FROM `{table}` WHERE symbol IS NOT NULL AND symbol <> ''")
    stored = {str(r[0]).upper().strip() for r in cur.fetchall()}
    if extra:
        stored |= {str(s).upper().strip() for s in _extra_symbols(table)}
    return sorted(s for s in stored if s)


def _batches(items: list[str], size: int):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _frame_for(df, ticker: str):
    """Return a per-ticker OHLCV frame for both single- and multi-ticker results."""
    import pandas as pd

    if df is None or len(df) == 0:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        if ticker not in df.columns.get_level_values(0):
            return None
        sub = df[ticker].dropna(how="all")
        return sub if len(sub) else None
    return df.dropna(how="all")


def backfill(table: str, since: date, batch_size: int, pause: float,
             apply: bool, limit: int) -> dict:
    import pandas as pd
    import yfinance as yf

    conn = _db()
    cur = conn.cursor()
    syms = universe(table, cur)
    if limit:
        syms = syms[:limit]
    print(f"\n[{table}] universe={len(syms)} since={since} apply={apply}")

    days = max((date.today() - since).days + 5, 30)
    sql = UPSERT.format(table=table)
    written = fetched = failed = 0
    errors: list[str] = []

    for batch in _batches(syms, batch_size):
        try:
            df = yf.download(" ".join(batch), period=f"{days}d", interval="1d",
                             group_by="ticker", progress=False, threads=True,
                             auto_adjust=False)
        except Exception as exc:  # network / parse
            errors.append(f"batch {batch[:2]}… {type(exc).__name__}: {exc}")
            continue
        for ticker in batch:
            frame = _frame_for(df, ticker)
            if frame is None:
                failed += 1
                continue
            rows = []
            for idx, row in frame.iterrows():
                try:
                    trade_date = idx.date() if hasattr(idx, "date") else datetime.fromisoformat(str(idx)).date()
                except Exception:
                    continue
                if trade_date < since:
                    continue
                close = row.get("Close")
                if close is None or pd.isna(close):
                    continue
                rows.append((
                    ticker, trade_date,
                    float(row.get("Open", 0) or 0), float(row.get("High", 0) or 0),
                    float(row.get("Low", 0) or 0), float(close),
                    int(row.get("Volume", 0) or 0),
                ))
            if not rows:
                failed += 1
                continue
            fetched += len(rows)
            if apply:
                try:
                    cur.executemany(sql, rows)
                    conn.commit()
                    written += len(rows)
                except Exception as exc:
                    conn.rollback()
                    errors.append(f"{ticker} insert {type(exc).__name__}: {exc}")
        time.sleep(pause)

    if apply:
        conn.close()
    return {"table": table, "symbols": len(syms), "rows_fetched": fetched,
            "rows_written": written, "symbols_without_data": failed,
            "errors": errors[:10]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Backfill daily OHLCV tables from yfinance.")
    ap.add_argument("--tables", default="equity,etf,futures",
                    help="comma list of equity|etf|futures (default all three)")
    ap.add_argument("--since", default="2026-06-18", help="ISO date; nothing earlier is written")
    ap.add_argument("--apply", action="store_true", help="fetch and write (default: plan only)")
    ap.add_argument("--batch-size", type=int, default=20)
    ap.add_argument("--pause", type=float, default=1.0, help="seconds between yfinance batches")
    ap.add_argument("--limit", type=int, default=0, help="cap symbols per table (debug)")
    args = ap.parse_args(argv)

    since = date.fromisoformat(args.since)
    tables = [TABLE_ALIASES.get(t.strip().lower(), t.strip()) for t in args.tables.split(",") if t.strip()]

    if not args.apply:
        conn = _db()
        cur = conn.cursor()
        for table in tables:
            syms = universe(table, cur)
            if args.limit:
                syms = syms[:args.limit]
            cur.execute(f"SELECT MAX(trade_date), COUNT(DISTINCT symbol) FROM `{table}`")
            last, distinct = cur.fetchone()
            print(f"  {table:22s} symbols={len(syms):4d} stored={int(distinct or 0):4d} "
                  f"last_bar={last} -> since {since}")
        conn.close()
        print("\ndry run: no network fetch, no database write (pass --apply)")
        return 0

    results = [backfill(t, since, args.batch_size, args.pause, True, args.limit) for t in tables]
    print("\n" + "=" * 68)
    for r in results:
        print(f"  {r['table']:22s} symbols={r['symbols']:4d} fetched={r['rows_fetched']:6d} "
              f"written={r['rows_written']:6d} no_data={r['symbols_without_data']:3d}")
        for e in r["errors"]:
            print(f"     ! {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
