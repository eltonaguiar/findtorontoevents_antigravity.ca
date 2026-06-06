#!/usr/bin/env python3
"""Materialize the local SQLite ``crypto_data.db`` from the MySQL source of truth.

Why this exists
---------------
``incubator/backtest_team/real_data_sweep_runner.py`` reads OHLCV from a local
SQLite file ``crypto_data.db`` (table ``klines(pair, timestamp, open, high,
low, close, volume)``). That file is **gitignored** to keep the repo small, so
it is absent on GitHub Actions runners — which is why the
"Battleground Mass Backtest (Part 2 - Babies)" workflow died in ~22s with
``ERROR: crypto_data.db not found`` (run 27055166676), trapping every baby
strategy: they could never be backtested in CI.

The OHLCV is already stored canonically in MySQL ``ejaguiar1_stocks``:
  - ``crypto_ohlcv``  (312 symbols, 1h, ~223k rows)  symbol e.g. ``BTCUSDT``
  - ``stock_ohlcv``   (equities/ETFs)                 symbol e.g. ``AAPL``
  - ``fx_prices``     (forex daily)                   pair   e.g. ``EURUSD``

This script projects those tables into the ``klines`` schema the runner
expects, writing a fresh SQLite each run. No git bloat (still gitignored);
MySQL stays the single source of truth.

Key conversions (correctness-critical)
--------------------------------------
1. **timestamp**: MySQL stores bigint epoch. The runner calls
   ``pd.to_datetime(timestamp, utc=True)`` with NO ``unit=``, so an integer
   would be misread as *nanoseconds*. We therefore write ISO-8601 strings,
   which ``pd.to_datetime`` parses unambiguously.
2. **pair format**: the runner queries ``WHERE pair = 'BTC/USDT'`` (with a
   slash). MySQL crypto symbols are ``BTCUSDT`` (no slash). We insert a slash
   before the quote currency so ``BTCUSDT`` -> ``BTC/USDT``. We ALSO insert a
   no-slash alias row-set so callers using either format resolve. (Cheap;
   storage is tiny.)

Usage
-----
    python tools/build_crypto_data_db_from_mysql.py            # -> ./crypto_data.db
    python tools/build_crypto_data_db_from_mysql.py --out /tmp/x.db --crypto-only
    python tools/build_crypto_data_db_from_mysql.py --min-bars 80   # skip thin symbols

Exit code 0 on success (BTC/USDT present + non-empty), 1 otherwise — so CI can
fail fast with a clear message instead of dying deep in the backtester.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Known quote currencies, longest-first so e.g. "USDT" matches before "USD".
_QUOTES = ["USDT", "USDC", "BUSD", "FDUSD", "TUSD", "USD", "EUR", "GBP",
           "BTC", "ETH", "BNB", "JPY", "AUD", "CAD", "CHF", "NZD"]


def _epoch_to_iso(ts) -> str | None:
    """Convert a MySQL timestamp (epoch s or ms, or already a datetime/str)
    into an ISO-8601 UTC string that pd.to_datetime parses correctly."""
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts.replace(tzinfo=ts.tzinfo or timezone.utc).isoformat()
    # datetime.date (not datetime) — e.g. fx_prices.trade_date
    import datetime as _dt
    if isinstance(ts, _dt.date):
        return _dt.datetime(ts.year, ts.month, ts.day, tzinfo=timezone.utc).isoformat()
    if isinstance(ts, str):
        # already a date/datetime string — trust it
        return ts
    try:
        v = int(ts)
    except (TypeError, ValueError):
        return None
    # Heuristic: > 1e12 means milliseconds; ~1e9 means seconds.
    if v > 1_000_000_000_000:      # ms
        v = v / 1000.0
    elif v > 100_000_000_000:      # likely ms without quite hitting 1e12
        v = v / 1000.0
    try:
        return datetime.fromtimestamp(v, tz=timezone.utc).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def _slashify(symbol: str) -> str:
    """BTCUSDT -> BTC/USDT (insert slash before the quote currency)."""
    s = (symbol or "").upper().replace("/", "")
    for q in _QUOTES:
        if s.endswith(q) and len(s) > len(q):
            return f"{s[:-len(q)]}/{q}"
    return s


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS klines")
    conn.execute(
        """
        CREATE TABLE klines (
            pair      TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            open      REAL,
            high      REAL,
            low       REAL,
            close     REAL,
            volume    REAL
        )
        """
    )


def _bulk_insert(conn: sqlite3.Connection, rows: list[tuple]) -> int:
    if not rows:
        return 0
    conn.executemany(
        "INSERT INTO klines (pair, timestamp, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    return len(rows)


def _load_crypto(cur, out_rows: list, alias_noslash: bool) -> int:
    cur.execute(
        "SELECT symbol, timestamp, open, high, low, close, volume FROM crypto_ohlcv"
    )
    n = 0
    for sym, ts, o, h, lo, c, v in cur.fetchall():
        iso = _epoch_to_iso(ts)
        if iso is None:
            continue
        pair = _slashify(sym)
        row = (pair, iso, float(o), float(h), float(lo), float(c), float(v))
        out_rows.append(row)
        n += 1
        if alias_noslash and "/" in pair:
            out_rows.append((sym.upper(), iso, float(o), float(h), float(lo), float(c), float(v)))
            n += 1
    return n


def _load_stock(cur, out_rows: list) -> int:
    cur.execute(
        "SELECT symbol, timestamp, open, high, low, close, volume FROM stock_ohlcv"
    )
    n = 0
    for sym, ts, o, h, lo, c, v in cur.fetchall():
        iso = _epoch_to_iso(ts)
        if iso is None:
            continue
        out_rows.append((sym.upper(), iso, float(o), float(h), float(lo), float(c), float(v)))
        n += 1
    return n


def _load_fx(cur, out_rows: list) -> int:
    cur.execute(
        "SELECT pair, trade_date, open_price, high_price, low_price, close_price, volume FROM fx_prices"
    )
    n = 0
    for pair, td, o, h, lo, c, v in cur.fetchall():
        iso = _epoch_to_iso(td)
        if iso is None:
            continue
        slashed = _slashify(pair)
        out_rows.append((slashed, iso, float(o), float(h), float(lo), float(c), float(v or 0)))
        n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(ROOT / "crypto_data.db"))
    ap.add_argument("--crypto-only", action="store_true",
                    help="Skip stock_ohlcv and fx_prices (crypto babies only)")
    ap.add_argument("--no-alias", action="store_true",
                    help="Do not also emit no-slash symbol aliases (BTCUSDT)")
    ap.add_argument("--require-pair", default="BTC/USDT",
                    help="Fail if this pair has no rows (sanity gate for CI)")
    args = ap.parse_args()

    try:
        import pymysql  # noqa: F401
        from tools.db_env import get_stocks_creds
    except Exception as exc:  # pragma: no cover
        print(f"ERROR: cannot import deps: {exc}", file=sys.stderr)
        return 1

    import pymysql
    try:
        conn_my = pymysql.connect(**get_stocks_creds())
    except Exception as exc:
        print(f"ERROR: MySQL connect failed: {exc}", file=sys.stderr)
        return 1
    cur = conn_my.cursor()

    rows: list[tuple] = []
    print("[build] loading crypto_ohlcv ...")
    nc = _load_crypto(cur, rows, alias_noslash=not args.no_alias)
    print(f"[build]   crypto rows: {nc:,}")

    if not args.crypto_only:
        try:
            print("[build] loading stock_ohlcv ...")
            ns = _load_stock(cur, rows)
            print(f"[build]   stock rows: {ns:,}")
        except Exception as exc:
            print(f"[build]   stock_ohlcv skipped: {exc}")
        try:
            print("[build] loading fx_prices ...")
            nf = _load_fx(cur, rows)
            print(f"[build]   fx rows: {nf:,}")
        except Exception as exc:
            print(f"[build]   fx_prices skipped: {exc}")

    conn_my.close()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    conn = sqlite3.connect(str(out_path))
    try:
        _create_schema(conn)
        _bulk_insert(conn, rows)
        conn.execute("CREATE INDEX idx_klines_pair_ts ON klines (pair, timestamp)")
        conn.commit()

        # Sanity gate
        cur2 = conn.execute("SELECT COUNT(*) FROM klines WHERE pair = ?", [args.require_pair])
        n_btc = cur2.fetchone()[0]
        cur3 = conn.execute("SELECT COUNT(DISTINCT pair) FROM klines")
        n_pairs = cur3.fetchone()[0]
        cur4 = conn.execute("SELECT COUNT(*) FROM klines")
        n_total = cur4.fetchone()[0]
    finally:
        conn.close()

    size_mb = out_path.stat().st_size / 1024 / 1024
    print(f"[build] wrote {out_path} — {n_total:,} rows, {n_pairs:,} pairs, {size_mb:.1f} MB")
    print(f"[build] sanity: '{args.require_pair}' has {n_btc:,} bars")

    if n_btc == 0:
        print(f"ERROR: required pair '{args.require_pair}' has no rows — backtester would fail.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
