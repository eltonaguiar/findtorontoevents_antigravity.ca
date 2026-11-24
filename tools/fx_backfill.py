#!/usr/bin/env python3
"""Backfill the ``fx_prices`` FOREX daily table and repair the ledger-to-table
symbol mapping.

Why this exists
---------------
The audit (docs/EDGE_IDEAS_BACKLOG_2026-11-19.md E11) measured two defects:

1. Staleness: ``fx_prices`` ends 2026-02-09 (3,855 rows, 15 pairs) while the
   pick ledger runs to 2026-11-19, so 211 forex picks have no computable alpha.
2. Mapping: the audit's ``symbol_candidates()``
   (alpha_engine/audit3_selection_alpha.py:63) only swaps ``.``/``-`` for
   non-crypto, so a ledger symbol like ``AUDJPY=X`` never matches the bare
   ``AUDJPY`` pair stored in ``fx_prices``. ``EURUSDT`` is additionally
   mis-filed as FOREX when its ``USDT`` quote makes it a CRYPTO pair.

This tool normalizes ``XXXYYY=X`` / ``XXX-YYY`` / ``XXX/YYY`` to the bare
``XXXYYY`` form the table uses, classifies USDT-quoted symbols as CRYPTO, and
backfills daily bars for a ``--since``/``--until`` window.

Data source: Yahoo Finance (the same source the existing PHP writer uses at
findforex2/api/fetch_prices.php:49, via query1.finance.yahoo.com). yfinance is
an optional dependency, imported only on ``--apply``.

SAFETY
------
* Not auto-run. No cron, no workflow, no import side effect touches the DB.
* ``--dry-run`` (default) is fully offline: no network, no DB, no credentials.
* ``--apply`` is the only mode that reads credentials or writes. It resolves
  them through ``tools.db_env.get_stocks_creds()`` — the repo's canonical
  convention (DB_PASSWORDS_JSON / MYSQL_PASSWORD / DB_STOCKS_* env vars).
  Nothing is hardcoded and no secret is printed.
* Writes use ``INSERT ... ON DUPLICATE KEY UPDATE`` on the
  ``idx_pair_date (pair, trade_date)`` unique key, so re-runs are idempotent.

Usage
-----
    python3 tools/fx_backfill.py --dry-run
    python3 tools/fx_backfill.py --dry-run --since 2026-02-10 --until 2026-11-19
    python3 tools/fx_backfill.py --apply --since 2026-02-10 --until 2026-11-19
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_PAIRS = [
    "EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD", "NZDUSD", "USDCHF",
    "EURGBP", "EURJPY", "GBPJPY", "EURCHF", "AUDCAD", "CADJPY", "GBPCAD",
    "USDMXN",
]

FOREX_CCYS = frozenset({"EUR", "GBP", "USD", "JPY", "AUD", "CAD", "CHF", "NZD", "MXN"})

CRYPTO_QUOTE_SUFFIXES = ("USDT", "USDC", "BUSD", "USDP", "DAI", "TUSD", "FDUSD")

YAHOO_TICKER_OVERRIDES = {
    "USDJPY": "JPY=X",
    "USDCAD": "CAD=X",
    "USDCHF": "CHF=X",
    "USDMXN": "MXN=X",
}

DEFAULT_SINCE = "2026-02-10"


def _clean(symbol: str) -> str:
    return (
        str(symbol or "").strip().upper()
        .replace(" ", "").replace("/", "").replace("-", "").replace("_", "")
    )


def normalize_fx_symbol(symbol: str) -> str | None:
    """Map a ledger/vendor FX symbol to the bare ``XXXYYY`` pair stored in ``fx_prices``.

    Handles ``AUDJPY=X``, ``AUD-JPY``, ``AUD/JPY``, ``AUDJPY`` and the
    ``=X`` suffix. Returns None for non-FX symbols (crypto, futures, equities)
    and for malformed input.
    """
    s = _clean(symbol)
    if not s:
        return None
    if s.endswith("=F"):
        return None
    if s.endswith("=X"):
        s = s[:-2]
    if len(s) == 6 and s.isalpha() and s[:3] in FOREX_CCYS and s[3:] in FOREX_CCYS:
        return s
    return None


def classify_symbol(symbol: str) -> str:
    """Classify a symbol as FOREX or CRYPTO for backfill purposes.

    A USDT/USDC/BUSD-style quote is CRYPTO regardless of any claimed FOREX
    class (so ``EURUSDT`` is CRYPTO, not FOREX).
    """
    s = _clean(symbol)
    if not s:
        return "UNKNOWN"
    if any(s.endswith(sfx) for sfx in CRYPTO_QUOTE_SUFFIXES):
        return "CRYPTO"
    if s.endswith("=X"):
        return "FOREX"
    if normalize_fx_symbol(s):
        return "FOREX"
    return "OTHER"


def yahoo_ticker(pair: str) -> str:
    """Yahoo ticker for a bare pair, preserving the PHP writer's inverse tickers."""
    return YAHOO_TICKER_OVERRIDES.get(pair, f"{pair}=X")


def business_days(since: date, until: date) -> int:
    if until < since:
        return 0
    n = 0
    d = since
    while d <= until:
        if d.weekday() < 5:
            n += 1
        d += timedelta(days=1)
    return n


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def build_plan(pairs: list[str], since: date, until: date) -> list[dict]:
    plan: list[dict] = []
    for raw in pairs:
        klass = classify_symbol(raw)
        pair = normalize_fx_symbol(raw)
        entry = {
            "input": raw,
            "asset_class": klass,
            "pair": pair,
            "ticker": yahoo_ticker(pair) if pair else None,
            "since": since,
            "until": until,
            "business_days": business_days(since, until) if pair else 0,
            "action": "backfill" if pair else "skip",
        }
        if klass == "CRYPTO":
            entry["reason"] = "USDT-quoted -> CRYPTO, not FOREX"
        elif pair is None:
            entry["reason"] = "not a recognizable FX pair"
        plan.append(entry)
    return plan


def print_plan(plan: list[dict]) -> None:
    print("FX BACKFILL PLAN (dry-run)")
    print(f"  window: {plan[0]['since']} -> {plan[0]['until']}" if plan else "  (no pairs)")
    print()
    print(f"  {'input':<14} {'class':<8} {'pair':<8} {'ticker':<12} {'days':>5}  action")
    print("  " + "-" * 66)
    total_days = 0
    backfills = 0
    for e in plan:
        days = e["business_days"] if e["action"] == "backfill" else 0
        total_days += days
        backfills += 1 if e["action"] == "backfill" else 0
        print(
            f"  {e['input']:<14} {e['asset_class']:<8} {str(e['pair'] or '-'):<8} "
            f"{str(e['ticker'] or '-'):<12} {days:>5}  {e['action']}"
            + (f"  ({e['reason']})" if e.get("reason") else "")
        )
    print("  " + "-" * 66)
    print(f"  pairs to backfill: {backfills}")
    print(f"  estimated rows (business days x pairs): {total_days}")
    print()
    print("  No network and no database were contacted. Re-run with --apply to write.")


def apply_plan(plan: list[dict], limit: int | None) -> int:
    try:
        import pymysql
        from tools.db_env import get_stocks_creds
    except Exception as exc:
        print(f"ERROR: cannot import DB deps ({exc}). Install pymysql and use "
              f"tools.db_env credentials.", file=sys.stderr)
        return 1

    try:
        import yfinance as yf
    except ImportError:
        print("ERROR: yfinance is required for --apply (pip install yfinance).",
              file=sys.stderr)
        return 1

    targets = [e for e in plan if e["action"] == "backfill"]
    if limit:
        targets = targets[:limit]

    try:
        conn = pymysql.connect(**get_stocks_creds(),
                               cursorclass=pymysql.cursors.DictCursor)
    except Exception as exc:
        print(f"ERROR: MySQL connect failed: {exc}", file=sys.stderr)
        return 1

    total_inserted = 0
    try:
        cur = conn.cursor()
        for e in targets:
            pair, ticker = e["pair"], e["ticker"]
            try:
                hist = yf.Ticker(ticker).history(
                    start=e["since"].isoformat(), end=e["until"].isoformat(),
                    interval="1d", auto_adjust=False,
                )
            except Exception as exc:
                print(f"  [FAIL] {pair} ({ticker}): {exc}")
                continue
            if hist is None or hist.empty:
                print(f"  [WARN] {pair} ({ticker}): no bars in window")
                continue
            inserted = 0
            for ts, row in hist.iterrows():
                d = ts.date() if hasattr(ts, "date") else ts
                if d < e["since"] or d > e["until"]:
                    continue
                cur.execute(
                    "INSERT INTO fx_prices "
                    "(pair, trade_date, open_price, high_price, low_price, close_price, volume) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s) "
                    "ON DUPLICATE KEY UPDATE open_price=VALUES(open_price), "
                    "high_price=VALUES(high_price), low_price=VALUES(low_price), "
                    "close_price=VALUES(close_price), volume=VALUES(volume)",
                    (pair, d.isoformat(),
                     float(row["Open"]), float(row["High"]),
                     float(row["Low"]), float(row["Close"]),
                     int(row["Volume"]) if row["Volume"] == row["Volume"] else 0),
                )
                inserted += 1
            conn.commit()
            total_inserted += inserted
            print(f"  [OK] {pair} ({ticker}): {inserted} bars")
    finally:
        conn.close()
    print(f"\n[APPLY] wrote {total_inserted} rows across {len(targets)} pairs.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Backfill fx_prices and fix FX symbol mapping.")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true",
                      help="Offline plan only: no network, no DB (default).")
    mode.add_argument("--apply", action="store_true",
                      help="Fetch Yahoo bars and write fx_prices (needs DB credentials).")
    ap.add_argument("--since", default=DEFAULT_SINCE,
                    help=f"Start date YYYY-MM-DD (default {DEFAULT_SINCE}, day after the "
                         f"known 2026-02-09 stale tail).")
    ap.add_argument("--until", default=None,
                    help="End date YYYY-MM-DD (default: today).")
    ap.add_argument("--pairs", default=None,
                    help="Comma-separated symbols/pairs (default: the 15 seeded pairs).")
    ap.add_argument("--limit", type=int, default=None,
                    help="Apply at most N pairs (useful for a first live smoke test).")
    args = ap.parse_args()

    since = _parse_date(args.since)
    until = _parse_date(args.until) if args.until else date.today()
    if until < since:
        print(f"ERROR: --until {until} is before --since {since}", file=sys.stderr)
        return 2

    pairs = ([p.strip() for p in args.pairs.split(",") if p.strip()]
             if args.pairs else list(DEFAULT_PAIRS))

    plan = build_plan(pairs, since, until)

    if args.apply:
        return apply_plan(plan, args.limit)

    print_plan(plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
