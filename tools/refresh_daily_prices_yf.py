#!/usr/bin/env python3
"""refresh_daily_prices_yf.py — yfinance ingest for daily_prices (replaces the DEAD
fetch_prices.php endpoint that returns HTTP 404, which froze daily_prices at
2026-04-29 and broke the equity feed).

Mirrors the proven etf_daily_ohlcv / equity_daily_ohlcv yfinance pattern. Refreshes
the EXISTING daily_prices ticker universe (153 US equities). Insert-only for missing
(ticker, trade_date) rows — additive, idempotent, no schema change, no deletes, so no
backup needed. Uses auto_adjust=False to store raw OHLC + adj_close separately.

    python3 tools/refresh_daily_prices_yf.py            # refresh all tickers (gap-fill)
    python3 tools/refresh_daily_prices_yf.py --days 400 # wider lookback
    python3 tools/refresh_daily_prices_yf.py --dry-run  # report only, no write
"""
from __future__ import annotations

import argparse
import sys

sys.path.insert(0, "/home/eaguiar2015/findtorontoevents_antigravity.ca")
from tools.db_env import get_stocks_creds  # noqa: E402
import pymysql  # noqa: E402


def _db():
    keep = ("host", "user", "password", "database", "port", "connect_timeout")
    return pymysql.connect(**{k: v for k, v in get_stocks_creds().items() if k in keep})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=120, help="yfinance lookback window (period=Nd)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--tickers", default="", help="comma list override (default = existing daily_prices universe)")
    args = ap.parse_args()

    import yfinance as yf

    conn = _db()
    cur = conn.cursor()
    if args.tickers:
        universe = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    else:
        cur.execute("SELECT DISTINCT ticker FROM daily_prices WHERE ticker IS NOT NULL AND ticker<>'' ORDER BY ticker")
        universe = [r[0] for r in cur.fetchall()]
    print(f"refresh_daily_prices_yf | {len(universe)} tickers | window={args.days}d | dry_run={args.dry_run}")

    ins_sql = """INSERT INTO daily_prices (ticker, trade_date, open_price, high_price, low_price, close_price, adj_close, volume)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"""
    total_new = 0
    ok = fail = 0
    for t in universe:
        try:
            df = yf.download(t, period=f"{args.days}d", progress=False, auto_adjust=False)
            if df is None or len(df) == 0:
                fail += 1
                continue
            cur.execute("SELECT trade_date FROM daily_prices WHERE ticker=%s AND trade_date>=%s",
                        (t, str(df.index[0].date())))
            have = {r[0] for r in cur.fetchall()}
            rows = []
            for idx, r in df.iterrows():
                d = idx.date()
                if d in have:
                    continue

                def g(col):
                    v = r[col]
                    try:
                        return float(v.iloc[0]) if hasattr(v, "iloc") else float(v)
                    except Exception:
                        return None

                cl = g("Close")
                if cl and cl > 0:
                    rows.append((t, d, g("Open"), g("High"), g("Low"), cl, g("Adj Close") or cl, int(g("Volume") or 0)))
            if rows and not args.dry_run:
                cur.executemany(ins_sql, rows)
                conn.commit()
            total_new += len(rows)
            ok += 1
        except Exception as exc:
            print(f"  {t}: {str(exc)[:60]}")
            fail += 1
    cur.execute("SELECT MAX(trade_date), COUNT(DISTINCT ticker) FROM daily_prices")
    mx, nt = cur.fetchone()
    conn.close()
    print(f"Done | ok={ok} fail={fail} | new rows {'(would insert)' if args.dry_run else 'inserted'}={total_new} | daily_prices now {mx} / {nt} tickers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
