#!/usr/bin/env python3
"""
refresh_insider_trades.py — DB-landing collector for SEC Form 4 insider trades.

Revives the dead `gm_sec_insider_trades` feed (was 929 rows / 26 tickers, run once
~Feb 2026) by broadening the universe to the backtestable equity set (daily_prices
tickers, default) and landing DIRECTLY into ejaguiar1_stocks via idempotent upsert.

Reuses the tested SEC EDGAR fetch + Form-4 parse from scripts/insider_tracker.py
(get_ticker_cik_map, fetch_insider_trades_for_ticker) — no new EDGAR/parse logic.
Unlike insider_tracker.py it writes to the DB (not the PHP API) so it is
backup-able + schedulable as a standalone collector.

The money-ready value: open-market PURCHASES (transaction_type='P') are the
academically-robust insider signal (Cohen-Malloy-Pomorski 2012 "Decoding Inside
Information"; Lakonishok-Lee 2001). The current table has only ~17 P rows — too
few to backtest. This broadens the feed so the anomaly can accrue.

Usage:
    python3 tools/refresh_insider_trades.py --dry-run                 # no write
    python3 tools/refresh_insider_trades.py --execute                 # land to DB
    python3 tools/refresh_insider_trades.py --execute --limit-tickers 20 --lookback-days 400
    python3 tools/refresh_insider_trades.py --execute --tickers AAPL,MSFT,NVDA

BACKUP FIRST (CLAUDE.md): before the first --execute, snapshot the table:
    python3 tools/db_backup_to_backups.py --table gm_sec_insider_trades
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import pymysql

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

from tools.db_env import get_stocks_creds
import insider_tracker as it  # reuse get_ticker_cik_map + fetch_insider_trades_for_ticker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger("refresh_insider_trades")

UPSERT_SQL = """
INSERT INTO gm_sec_insider_trades
  (cik, ticker, filer_name, filer_title, transaction_date, transaction_type,
   shares, price_per_share, total_value, shares_owned_after, filing_date,
   accession_number, is_director, is_officer, is_ten_pct_owner)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
ON DUPLICATE KEY UPDATE
  shares=VALUES(shares), price_per_share=VALUES(price_per_share),
  total_value=VALUES(total_value), shares_owned_after=VALUES(shares_owned_after),
  filer_name=VALUES(filer_name), filer_title=VALUES(filer_title)
"""


def get_db():
    keep = ("host", "user", "password", "database", "port", "connect_timeout")
    return pymysql.connect(**{k: v for k, v in get_stocks_creds().items() if k in keep})


def get_universe(conn, args):
    if args.tickers:
        return [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT ticker FROM daily_prices WHERE ticker IS NOT NULL AND ticker<>'' ORDER BY ticker")
        return [r[0] for r in cur.fetchall()]


def to_row(t):
    """Map a parsed Form-4 trade dict to the DB column tuple. Defensive .get()."""
    def f(x):
        try:
            return float(x or 0)
        except (TypeError, ValueError):
            return 0.0
    td = t.get("transaction_date") or None
    fd = t.get("filing_date") or td
    if not td:
        return None  # transaction_date is NOT NULL
    return (
        str(t.get("cik", ""))[:20], str(t.get("ticker", ""))[:10],
        str(t.get("filer_name", ""))[:200], str(t.get("filer_title", ""))[:100],
        td, str(t.get("transaction_type", ""))[:10],
        f(t.get("shares")), f(t.get("price_per_share")), f(t.get("total_value")),
        f(t.get("shares_owned_after")), fd, str(t.get("accession", ""))[:40],
        int(bool(t.get("is_director"))), int(bool(t.get("is_officer"))),
        int(bool(t.get("is_ten_pct_owner"))),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Land SEC Form 4 insider trades into gm_sec_insider_trades")
    ap.add_argument("--dry-run", action="store_true", help="Preview only; no write")
    ap.add_argument("--execute", action="store_true", help="Write to DB")
    ap.add_argument("--tickers", default="", help="Comma list (overrides daily_prices universe)")
    ap.add_argument("--limit-tickers", type=int, default=0, help="Cap universe to first N")
    ap.add_argument("--lookback-days", type=int, default=400, help="Form-4 lookback window")
    ap.add_argument("--max-filings", type=int, default=40, help="Max Form-4 filings per ticker")
    args = ap.parse_args()
    dry = not args.execute or args.dry_run

    conn = get_db()
    universe = get_universe(conn, args)
    if args.limit_tickers > 0:
        universe = universe[: args.limit_tickers]
    logger.info("refresh_insider_trades | dry_run=%s | %d tickers | lookback=%dd max_filings=%d",
                dry, len(universe), args.lookback_days, args.max_filings)

    cikmap = it.get_ticker_cik_map()
    total_rows = 0
    p_buys = 0
    ok = fail = 0
    for tk in universe:
        cik = cikmap.get(tk)
        if not cik:
            logger.warning("%s: no CIK", tk); fail += 1; continue
        try:
            trades = it.fetch_insider_trades_for_ticker(
                tk, cik, lookback_days=args.lookback_days, max_filings=args.max_filings)
        except Exception as exc:
            logger.warning("%s: fetch error %s", tk, str(exc)[:80]); fail += 1; continue
        rows = [r for r in (to_row(t) for t in trades) if r]
        p_buys += sum(1 for t in trades if str(t.get("transaction_type", "")).upper() == "P")
        if rows and not dry:
            with conn.cursor() as cur:
                cur.executemany(UPSERT_SQL, rows)
                conn.commit()
        total_rows += len(rows)
        ok += 1
        time.sleep(0.05)
    logger.info("Done | tickers ok=%d fail=%d | rows %s=%d | open-market BUYS (P)=%d",
                ok, fail, "(would upsert)" if dry else "upserted", total_rows, p_buys)
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
