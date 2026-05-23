#!/usr/bin/env python3
"""
Forex Carry Trade Strategy
============================
Buy high-yield currencies, sell low-yield currencies.

Edge source: Risk premium — investors compensated for holding volatile currencies.
Academic basis: Lustig, Roussanov, Verdelhan (2011) "Common Risk Factors in Currency Markets"
Expected: 55-60% WR, PF 1.2-1.5, Sharpe 0.8-1.2

Rules:
  - Rank G10 currencies by 3-month interest rate differential
  - LONG top 3 pairs (high yield vs. USD)
  - SHORT bottom 3 pairs (low yield vs. USD)
  - TP/SL based on ATR(14) with trend filter (50-day MA)
  - Monthly rebalance
"""

from __future__ import annotations
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent.parent / "alpha_engine" / "data"
FORWARD_DIR = DATA_DIR / "forward_tests" / "forex"
OUTPUT_FILE = FORWARD_DIR / "carry_trade.json"

# G10 Forex Pairs (vs. USD)
FOREX_PAIRS = {
    "AUDUSD=X": {"base": "AUD", "quote": "USD"},
    "NZDUSD=X": {"base": "NZD", "quote": "USD"},
    "GBPUSD=X": {"base": "GBP", "quote": "USD"},
    "EURUSD=X": {"base": "EUR", "quote": "USD"},
    "USDCHF=X": {"base": "USD", "quote": "CHF"},
    "USDJPY=X": {"base": "USD", "quote": "JPY"},
    "USDCAD=X": {"base": "USD", "quote": "CAD"},
    "USDSEK=X": {"base": "USD", "quote": "SEK"},
}

# Approximate 3-month rates as of 2026-04 (update monthly)
# Source: Central bank policy rates
RATE_MAP = {
    "USD": 4.50,
    "EUR": 2.50,
    "GBP": 4.25,
    "JPY": 0.50,
    "CHF": 1.25,
    "AUD": 3.85,
    "NZD": 3.50,
    "CAD": 3.25,
    "SEK": 2.75,
}

# Strategy parameters
ATR_PERIOD = 14
MA_PERIOD = 50
TP_ATR_MULT = 2.0
SL_ATR_MULT = 1.5
TOP_K = 3  # Long top 3, short bottom 3


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def _fetch_forex_ohlcv(symbol: str, period: str = "6mo") -> pd.DataFrame:
    """Fetch forex OHLCV via yfinance."""
    try:
        import yfinance as yf
        df = yf.download(symbol, period=period, interval="1d", progress=False)
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        df.columns = [c.lower() for c in df.columns]
        return df
    except Exception as exc:
        print(f"[CARRY] Failed to fetch {symbol}: {exc}")
        return pd.DataFrame()


def compute_carry_differential(pair_info: Dict, rates: Dict) -> float:
    """Compute annualized carry (yield differential) for a pair."""
    base_rate = rates.get(pair_info["base"], 0)
    quote_rate = rates.get(pair_info["quote"], 0)
    # Carry = base rate - quote rate
    # Positive carry = you earn by holding the base currency
    return base_rate - quote_rate


def rank_pairs_by_carry() -> List[Tuple[str, float]]:
    """Rank all forex pairs by carry differential."""
    ranked = []
    for symbol, info in FOREX_PAIRS.items():
        carry = compute_carry_differential(info, RATE_MAP)
        ranked.append((symbol, carry))
    ranked.sort(key=lambda x: x[1], reverse=True)
    return ranked


def evaluate_carry_signals() -> List[Dict]:
    """Generate carry trade signals."""
    picks = []
    now_iso = datetime.now(timezone.utc).isoformat()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Rank by carry
    ranked = rank_pairs_by_carry()
    long_candidates = ranked[:TOP_K]   # Highest carry → LONG
    short_candidates = ranked[-TOP_K:]  # Lowest carry → SHORT

    for symbol, carry in long_candidates:
        df = _fetch_forex_ohlcv(symbol)
        if df.empty or len(df) < MA_PERIOD + 5:
            continue

        price = float(df["close"].iloc[-1])
        ma50 = float(df["close"].rolling(MA_PERIOD).mean().iloc[-1])
        atr_val = float(_atr(df["high"], df["low"], df["close"], ATR_PERIOD).iloc[-1])

        if pd.isna(ma50) or pd.isna(atr_val) or atr_val <= 0:
            continue

        # Only go long if price > MA (trend confirmation)
        if price <= ma50:
            continue

        confidence = min(abs(carry) / 5.0, 0.90)  # Scale carry to confidence
        tp = round(price + TP_ATR_MULT * atr_val, 6)
        sl = round(price - SL_ATR_MULT * atr_val, 6)

        picks.append({
            "id": f"carry_trade::{symbol}::{today_str}_LONG",
            "strategy": "carry_trade",
            "symbol": symbol,
            "direction": "LONG",
            "entry_price": price,
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": round(confidence, 3),
            "asset_class": "FOREX",
            "source_system": "carry_trade",
            "timeframe": "1d",
            "timestamp": now_iso,
            "created_at": now_iso,
            "status": "ACTIVE",
            "carry_differential": round(carry, 2),
            "trend_aligned": True,
            "reasoning": [
                f"Carry differential: +{carry:.2f}% (high yield base)",
                f"Trend confirmed: price {price:.5f} > MA50 {ma50:.5f}",
                "Lustig et al. (2011): carry factor = 5-7% annual alpha",
            ],
        })

    for symbol, carry in short_candidates:
        df = _fetch_forex_ohlcv(symbol)
        if df.empty or len(df) < MA_PERIOD + 5:
            continue

        price = float(df["close"].iloc[-1])
        ma50 = float(df["close"].rolling(MA_PERIOD).mean().iloc[-1])
        atr_val = float(_atr(df["high"], df["low"], df["close"], ATR_PERIOD).iloc[-1])

        if pd.isna(ma50) or pd.isna(atr_val) or atr_val <= 0:
            continue

        # Only go short if price < MA (downtrend confirmation)
        if price >= ma50:
            continue

        confidence = min(abs(carry) / 5.0, 0.90)
        tp = round(price - TP_ATR_MULT * atr_val, 6)
        sl = round(price + SL_ATR_MULT * atr_val, 6)

        picks.append({
            "id": f"carry_trade::{symbol}::{today_str}_SHORT",
            "strategy": "carry_trade",
            "symbol": symbol,
            "direction": "SHORT",
            "entry_price": price,
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": round(confidence, 3),
            "asset_class": "FOREX",
            "source_system": "carry_trade",
            "timeframe": "1d",
            "timestamp": now_iso,
            "created_at": now_iso,
            "status": "ACTIVE",
            "carry_differential": round(carry, 2),
            "trend_aligned": True,
            "reasoning": [
                f"Negative carry: {carry:.2f}% (low yield base)",
                f"Downtrend confirmed: price {price:.5f} < MA50 {ma50:.5f}",
            ],
        })

    return picks


def run():
    print("[CARRY] Forex Carry Trade scanner starting...")
    picks = evaluate_carry_signals()
    FORWARD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(picks, indent=2))
    print(f"[CARRY] Wrote {len(picks)} carry signals to {OUTPUT_FILE}")
    return picks


if __name__ == "__main__":
    run()
