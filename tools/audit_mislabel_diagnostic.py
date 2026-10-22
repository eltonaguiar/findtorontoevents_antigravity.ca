#!/usr/bin/env python3
"""Asset-class mislabel diagnostic for recent closed picks.

Detects rows in the recent_closed cohort whose recorded asset_class disagrees
with the symbol (e.g. a crypto symbol tagged EQUITY, a forex pair tagged
CRYPTO, a stock tagged FOREX). Such mislabels can drag WR/PF aggregates for the
wrong class.

Task QA-T3 of docs/superpowers/plans/2026-10-22-audit-dashboard-quality.md.

Usage:
    python3 tools/audit_mislabel_diagnostic.py [--payload path] [--window-days 3]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

CRYPTO_SUFFIXES = (
    "USDT", "USDC", "BUSD", "ETH", "BTC", "SOL", "DOGE", "ADA", "AVAX",
    "LINK", "MATIC", "DOT", "LTC", "XRP", "BNB", "NEAR", "ICP", "ATOM",
    "UNI", "AAVE", "SUSHI", "FIL", "ALGO", "VET", "XTZ", "EOS", "TRX",
    "SHIB", "APE", "ARB", "OP", "SUI", "APT", "SEI", "INJ", "TIA", "JUP",
    "WIF", "ENA", "PEPE", "FLOKI", "BONK",
)
CRYPTO_INFIX = ("USDT-", "USDC-", "USDT_", "USD-")
FOREX_PAIR_RE = re.compile(r'^[A-Z]{6}=?X?$')
EQUITY_SUFFIX_RE = re.compile(r'^(NYSE|NASDAQ|AMEX|TSX|LSE|BSE|NSE):')
KNOWN_CRYPTO_SYMBOLS = {"BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE",
                        "AVAX", "DOT", "LINK", "LTC", "MATIC", "TRX",
                        "SHIB", "NEAR", "UNI", "APT", "SUI", "ARB",
                        "PEPE", "WIF", "ENA", "INJ"}
KNOWN_EQUITY = {"AAPL", "MSFT", "TSLA", "AMZN", "GOOGL", "GOOG", "META",
                "NFLX", "NVDA", "AMD", "INTC", "MSTR", "COIN", "PLTR",
                "SQ", "HOOD", "KO", "JNJ", "JPM", "BAC", "XOM", "CVX",
                "DIS", "F", "GM", "GE", "SHOP"}
# Tickers that are actual ETFs (their asset_class=ETF is correct, not a mislabel)
KNOWN_ETFS = {"SPY", "QQQ", "IWM", "VTI", "VOO", "DIA", "XLF", "XLE",
              "XLK", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE",
              "EFA", "EEM", "IWM", "ARKK", "GDX", "GLD", "SLV", "USO",
              "TLT", "IEF", "SHY", "LQD", "HYG", "VNQ", "EWJ", "FXI",
              "INDA", "SMH", "SOXX", "IBB", "KRE", "XHB", "ITB", "TAN",
              "BOTZ", "AIQ"}


def _normalize_sym(raw):
    if not raw:
        return ""
    return str(raw).strip().upper()


def _classify_symbol(sym: str) -> str:
    s = _normalize_sym(sym)
    if not s:
        return "UNKNOWN"
    if s in KNOWN_ETFS:
        return "ETF"
    if EQUITY_SUFFIX_RE.match(s):
        return "EQUITY"
    if s in KNOWN_EQUITY:
        return "EQUITY"
    # Forex pairs: 6 letters (e.g. EURUSD) optionally with =X
    if FOREX_PAIR_RE.match(s) and s not in KNOWN_CRYPTO_SYMBOLS:
        if s[:3] in ("EUR", "GBP", "USD", "JPY", "AUD", "CAD", "CHF",
                     "NZD", "MXN", "TRY", "ZAR", "SEK", "NOK", "DKK",
                     "SGD", "HKD", "PLN", "CZK", "HUF", "BRL", "RUB"):
            return "FOREX"
        if s.endswith("=X"):
            return "FOREX"
    if any(s.endswith(sfx) for sfx in CRYPTO_SUFFIXES):
        return "CRYPTO"
    if any(infx in s for infx in CRYPTO_INFIX):
        return "CRYPTO"
    if s in KNOWN_CRYPTO_SYMBOLS:
        return "CRYPTO"
    return "UNKNOWN"


def _iter_closed(payload: dict):
    picks = payload.get("picks", {})
    if isinstance(picks, dict):
        for cohort in ("recent_closed", "closed_picks"):
            rows = picks.get(cohort)
            if isinstance(rows, list):
                yield from rows
    elif isinstance(picks, list):
        yield from picks
    # some payloads nest under performance.closed
    perf = payload.get("performance", {})
    if isinstance(perf, dict):
        for key in ("closed_picks", "recent_closed"):
            rows = perf.get(key)
            if isinstance(rows, list):
                yield from rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--payload", default=str(REPO_ROOT / "audit_dashboard/data/dashboard_data.json"))
    ap.add_argument("--window-days", type=int, default=3)
    args = ap.parse_args()

    p = Path(args.payload)
    if not p.exists():
        print(f"payload not found: {p}", file=sys.stderr)
        return 2
    data = json.loads(p.read_text(encoding="utf-8", errors="replace"))

    rows = list(_iter_closed(data))
    if not rows:
        print("no closed pick rows found in payload")
        return 1

    mismatches = Counter()
    examples = {}
    total = 0
    expected_by_symbol = Counter()
    actual_by_symbol = Counter()

    for row in rows:
        if not isinstance(row, dict):
            continue
        sym = row.get("symbol")
        ac = str(row.get("asset_class", "") or "").upper().strip()
        if not sym or not ac:
            continue
        # skip obvious placeholder rows
        exit_price = row.get("exit_price")
        if exit_price is not None:
            try:
                if float(exit_price) <= 0:
                    continue
            except (TypeError, ValueError):
                continue
        total += 1
        expected = _classify_symbol(sym)
        if expected != "UNKNOWN" and expected != ac:
            key = (ac, expected, str(sym))
            mismatches[key] += 1
            if key not in examples:
                examples[key] = row
        expected_by_symbol[sym] = expected
        actual_by_symbol[sym] = ac

    print(f"scanned {total} closed rows (window filter not applied beyond payload)")
    print(f"asset-class mismatches found: {sum(mismatches.values())}\n")
    for (ac, expected, sym), n in mismatches.most_common():
        ex = examples.get((ac, expected, sym), {})
        strat = ex.get("strategy") or ex.get("source_system") or "?"
        print(f"  {n:4d} row(s): symbol={sym} asset_class={ac} expected={expected} "
              f"(strategy={strat})")

    if sum(mismatches.values()) == 0:
        print("\nNo mislabels detected — asset-class assignments are consistent "
              "with symbols.")
    else:
        print("\nRecommendation: fix at the source (_coerce_asset_class / "
              "nc_asset_category_for_pick) or document as known caveat.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
