#!/usr/bin/env python3
"""Append-only price refresh for the R4b ETF forward clock.

Pre-registration: docs/preregistration/ETF_TREND_FORWARD_2026-11-23.md

WHY THIS EXISTS
    `tools/etf_trend_forward_clock.py` reads
    data/cache/asset_class_review/<SYM>_5y.csv. Those files are committed, and nothing
    in the repo kept them current -- so the clock would have sat at whatever date the
    cache was last touched and silently never recorded another month. A month-end
    trigger that never sees a new bar is not a trigger.

WHAT IT WILL NOT DO
    * It will not rewrite history. Rows already in the cache are left byte-identical;
      only dates strictly later than the cache's last date are appended. Backfilling or
      revising an earlier bar could change a signal that has already been recorded in
      the hash-chained ledger, which would make the ledger unverifiable by design.
    * It will not change the universe. The 20 tickers come from the clock module, so
      there is exactly one list. Adding a name is a new trial, not a refresh.
    * It will not paper over a failure. If any ticker cannot be refreshed it exits
      non-zero rather than appending a partial universe silently.

Usage
    python3 tools/etf_trend_price_refresh.py --dry-run
    python3 tools/etf_trend_price_refresh.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import etf_trend_forward_clock as clock  # noqa: E402  (single source of the frozen list)

CACHE = clock.CACHE
PERIOD = "5y"
HEADER = ["Date", "Open", "High", "Low", "Close", "Volume"]
PRICE_ROUND = 6


def cache_path(sym: str) -> Path:
    return CACHE / f"{sym}_5y.csv"


def last_cached_date(sym: str) -> str | None:
    p = cache_path(sym)
    if not p.exists():
        return None
    last = None
    for line in p.read_text().splitlines()[1:]:
        d = line.split(",", 1)[0].strip()
        if d:
            last = d if last is None else max(last, d)
    return last


def download_bars(sym: str, period: str = PERIOD) -> list[list[str]]:
    """Daily OHLCV for `sym`, oldest first, as CSV-ready string rows."""
    import yfinance as yf  # imported lazily so tests run offline

    df = yf.download(sym, period=period, interval="1d", auto_adjust=False,
                     progress=False, threads=False)
    if df is None or len(df) == 0:
        raise RuntimeError(f"yfinance returned no rows for {sym}")
    # yfinance returns ('Close','SPY')-style tuples for a single ticker in recent versions
    if getattr(df.columns, "nlevels", 1) > 1:
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    rows = []
    for idx, r in df.iterrows():
        try:
            o, h, low, c = (float(r["Open"]), float(r["High"]),
                            float(r["Low"]), float(r["Close"]))
            v = float(r["Volume"]) if r.get("Volume") is not None else 0.0
        except (KeyError, TypeError, ValueError):
            continue
        if not (c > 0):
            continue
        d = str(idx)[:10]
        rows.append([d, f"{o:.{PRICE_ROUND}f}", f"{h:.{PRICE_ROUND}f}",
                     f"{low:.{PRICE_ROUND}f}", f"{c:.{PRICE_ROUND}f}", str(int(v))])
    return rows


def new_rows_only(fresh: list[list[str]], last: str | None) -> list[list[str]]:
    """Strictly-later rows, deduplicated and sorted. Never an earlier date."""
    if last is None:
        out = fresh
    else:
        out = [r for r in fresh if r[0] > last]
    seen, uniq = set(), []
    for r in sorted(out, key=lambda x: x[0]):
        if r[0] in seen:
            continue
        seen.add(r[0])
        uniq.append(r)
    return uniq


def refresh(sym: str, dry_run: bool = False, downloader=None) -> int:
    """Append new bars for one symbol. Returns the number of rows appended."""
    dl = downloader or download_bars
    fresh = dl(sym)
    last = last_cached_date(sym)
    rows = new_rows_only(fresh, last)
    if not rows:
        print(f"  {sym}: up to date (last {last})")
        return 0
    if dry_run:
        print(f"  {sym}: would append {len(rows)} row(s) {rows[0][0]}..{rows[-1][0]}")
        return len(rows)
    p = cache_path(sym)
    p.parent.mkdir(parents=True, exist_ok=True)
    write_header = not p.exists() or p.stat().st_size == 0
    with p.open("a") as fh:
        if write_header:
            fh.write(",".join(HEADER) + "\n")
        for r in rows:
            fh.write(",".join(r) + "\n")
    print(f"  {sym}: appended {len(rows)} row(s) {rows[0][0]}..{rows[-1][0]}")
    return len(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--period", default=PERIOD)
    a = ap.parse_args()

    print(f"etf_trend_price_refresh | {len(clock.UNIVERSE)} frozen tickers | period={a.period} "
          f"| dry_run={a.dry_run}")
    total, failed = 0, []
    for sym in clock.UNIVERSE:
        try:
            total += refresh(sym, dry_run=a.dry_run)
        except Exception as exc:                      # noqa: BLE001 - report, do not swallow
            failed.append(sym)
            print(f"  {sym}: FAILED -- {exc}")
    print(f"rows appended: {total}  failed: {len(failed)}")
    if failed:
        print(f"::error::refresh failed for {', '.join(failed)} -- the frozen universe "
              f"must be complete before the clock may record")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
