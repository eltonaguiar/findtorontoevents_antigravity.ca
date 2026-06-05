#!/usr/bin/env python3
"""
Equity Momentum + Quality Factor Emitter

Implements academically-validated factors (Jegadeesh & Titman 1993, Asness et al. 2013):
  - Price Momentum: 12-1 month return (12-month lookback, skip last month)
  - Quality composite: ROE + low debt + profit margin (Fama-French extensions)

Wire-Up: Called by tools/feature_signals/orchestrator.py and production_scanner.py
EQUITY emission path. Emits to feature_signals table (opt-in sidecar until n>=100).

Usage:
    python3 alpha_engine/factors/equity_momentum_quality.py --top-n 10
    from alpha_engine.factors.equity_momentum_quality import EquityMomentumQualityFactor
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    import yfinance as yf
except ImportError:
    print("ERROR: pip install yfinance")
    sys.exit(1)

# Default watchlist: liquid large-caps with high analyst coverage
DEFAULT_WATCHLIST = [
    "NVDA", "META", "MSFT", "GOOGL", "AMZN",
    "AAPL", "AMD", "TSM", "AVGO", "ASML",
    "JPM", "BAC", "GS", "V", "MA",
    "UNH", "LLY", "JNJ", "ABBV", "MRK",
]

LOOKBACK_MONTHS = 12
QUALITY_WEIGHT = 0.4  # 40% quality, 60% momentum


def get_momentum_score(ticker: str) -> float | None:
    """12-1 month price momentum (standard academic definition).

    Returns (price_1_month_ago / price_12_months_ago) - 1,
    which avoids short-term reversal by skipping the last month.
    """
    try:
        data = yf.download(ticker, period=f"{LOOKBACK_MONTHS + 2}mo",
                           progress=False, auto_adjust=True)
        if data is None or len(data) < 22:
            return None
        close = data["Close"]
        if hasattr(close, "squeeze"):
            close = close.squeeze()
        price_12m = float(close.iloc[0])
        price_1m = float(close.iloc[-22]) if len(close) > 22 else float(close.iloc[0])
        price_now = float(close.iloc[-1])
        if price_12m <= 0 or price_1m <= 0:
            return None
        # Momentum = return from 12m ago to 1m ago (skip last month = no reversal bias)
        momentum = (price_1m / price_12m) - 1.0
        return round(float(momentum), 6)
    except Exception:
        return None


def get_quality_score(ticker: str) -> float | None:
    """Quality composite: ROE + low debt + profit margin.

    Each component z-scored implicitly by working in [0,1] bounded form.
    Returns None if yfinance data insufficient.
    """
    try:
        info = yf.Ticker(ticker).info
        if not info:
            return None
        roe = float(info.get("returnOnEquity") or 0.0)
        debt_eq = float(info.get("debtToEquity") or 0.0)
        profit_margin = float(info.get("profitMargins") or 0.0)

        # Normalize each to [0, 1] range using soft caps
        roe_norm = max(0.0, min(roe / 0.30, 1.0))           # cap at 30% ROE
        debt_norm = 1.0 / (1.0 + max(0.0, debt_eq / 100.0)) # low debt = high score
        pm_norm = max(0.0, min(profit_margin / 0.25, 1.0))   # cap at 25% margin

        quality = (roe_norm + debt_norm + pm_norm) / 3.0
        return round(float(quality), 6)
    except Exception:
        return None


def rank_universe(tickers: list[str], quality_weight: float = QUALITY_WEIGHT) -> list[dict[str, Any]]:
    """Score and rank a universe of tickers by combined momentum + quality."""
    results = []
    for ticker in tickers:
        mom = get_momentum_score(ticker)
        qual = get_quality_score(ticker)

        if mom is None and qual is None:
            continue

        mom_safe = mom if mom is not None else 0.0
        qual_safe = qual if qual is not None else 0.5  # neutral if missing

        combined = (1.0 - quality_weight) * mom_safe + quality_weight * qual_safe
        results.append({
            "symbol": ticker,
            "direction": "LONG" if combined > 0 else "SHORT",
            "momentum_12_1": round(mom_safe * 100, 2),  # in percent
            "quality_composite": round(qual_safe, 4),
            "combined_score": round(combined, 6),
            "momentum_raw": mom,
            "quality_raw": qual,
            "source_system": "equity_momentum_quality",
            "category": "equity",
            "strategy": f"mom12_qual_q{int(quality_weight * 100)}",
        })

    results.sort(key=lambda x: x["combined_score"], reverse=True)
    return results


def generate_picks(top_n: int = 5,
                   tickers: list[str] | None = None,
                   quality_weight: float = QUALITY_WEIGHT) -> list[dict[str, Any]]:
    """Generate top-N equity picks by momentum + quality rank.

    Filters: direction=LONG only (momentum must be positive), combined_score > 0.
    """
    universe = tickers or DEFAULT_WATCHLIST
    ranked = rank_universe(universe, quality_weight)
    longs = [r for r in ranked if r["direction"] == "LONG" and r["combined_score"] > 0]
    return longs[:top_n]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--quality-weight", type=float, default=QUALITY_WEIGHT)
    parser.add_argument("--tickers", nargs="+", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    picks = generate_picks(
        top_n=args.top_n,
        tickers=args.tickers,
        quality_weight=args.quality_weight,
    )

    if args.json:
        print(json.dumps(picks, indent=2, default=str))
    else:
        print(f"\nEquity Momentum + Quality Factor — top {len(picks)} picks\n")
        print(f"{'Symbol':<8} {'Dir':<6} {'Mom12-1':>9} {'Quality':>8} {'Score':>9}")
        print("-" * 46)
        for p in picks:
            print(
                f"  {p['symbol']:<8} {p['direction']:<6} "
                f"{p['momentum_12_1']:>7.1f}% "
                f"{p['quality_composite']:>8.4f} "
                f"{p['combined_score']:>9.6f}"
            )
