#!/usr/bin/env python3
"""
Time-Series Momentum (TSMOM) — For Futures & Bonds
====================================================
The most documented factor in futures markets.

Academic basis: Moskowitz, Ooi, Pedersen (2012) "Time-Series Momentum"
  - Validated on 58 liquid futures across 25+ years
  - Average Sharpe 1.5-2.0 across all asset classes
  - Works because: herding, slow information diffusion, institutional mandates

Rules:
  LONG  when excess_return(lookback) > 0 AND volatility not extreme
  SHORT when excess_return(lookback) < 0 AND volatility not extreme
  Position sizing: Volatility-targeted (target 10% annualized vol)
  TP/SL: ATR-based with trailing stop

Covers: FUTURES (ES, NQ, GC, CL, ZN, ZB) and BONDS (TLT, IEF, BND)
"""

from __future__ import annotations
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent.parent / "alpha_engine" / "data"

# Futures universe
FUTURES_SYMBOLS = {
    "ES=F": {"name": "S&P 500 E-mini", "asset_class": "FUTURES", "sector": "equity_index"},
    "NQ=F": {"name": "Nasdaq E-mini", "asset_class": "FUTURES", "sector": "equity_index"},
    "YM=F": {"name": "Dow E-mini", "asset_class": "FUTURES", "sector": "equity_index"},
    "RTY=F": {"name": "Russell 2000 E-mini", "asset_class": "FUTURES", "sector": "equity_index"},
    "GC=F": {"name": "Gold", "asset_class": "FUTURES", "sector": "precious_metals"},
    "SI=F": {"name": "Silver", "asset_class": "FUTURES", "sector": "precious_metals"},
    "CL=F": {"name": "Crude Oil", "asset_class": "FUTURES", "sector": "energy"},
    "NG=F": {"name": "Natural Gas", "asset_class": "FUTURES", "sector": "energy"},
}

# Bond ETFs (proxies for bond futures)
BOND_SYMBOLS = {
    "TLT": {"name": "20+ Year Treasury", "asset_class": "BONDS", "sector": "government"},
    "IEF": {"name": "7-10 Year Treasury", "asset_class": "BONDS", "sector": "government"},
    "BND": {"name": "Total Bond Market", "asset_class": "BONDS", "sector": "aggregate"},
    "SHY": {"name": "1-3 Year Treasury", "asset_class": "BONDS", "sector": "short_term"},
}

ALL_SYMBOLS = {**FUTURES_SYMBOLS, **BOND_SYMBOLS}

# TSMOM Parameters
LOOKBACK_DAYS = 60      # 3-month lookback for trend signal
VOL_LOOKBACK = 20       # 20-day realized volatility
VOL_TARGET = 0.10       # 10% annualized target volatility
ATR_PERIOD = 14
TP_ATR_MULT = 3.0       # Wider for trend-following (let winners run)
SL_ATR_MULT = 2.0       # Wider stops for trend strategies
EXTREME_VOL_PERCENTILE = 95  # Don't trade when vol is extreme


def _fetch_ohlcv(symbol: str, period: str = "1y") -> pd.DataFrame:
    """Fetch OHLCV via yfinance."""
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
        print(f"[TSMOM] Failed to fetch {symbol}: {exc}")
        return pd.DataFrame()


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def compute_tsmom_signal(df: pd.DataFrame, lookback: int = LOOKBACK_DAYS) -> Optional[str]:
    """
    Core TSMOM signal: sign of excess return over lookback period.
    
    Returns "LONG", "SHORT", or None (if volatility is extreme).
    """
    if len(df) < lookback + 10:
        return None

    close = df["close"]
    
    # Excess return over lookback
    excess_return = (close.iloc[-1] / close.iloc[-lookback]) - 1

    # Realized volatility check
    daily_returns = close.pct_change().dropna()
    if len(daily_returns) < VOL_LOOKBACK:
        return None
    
    realized_vol = daily_returns.tail(VOL_LOOKBACK).std() * math.sqrt(252)
    
    # Historical vol distribution for percentile check
    rolling_vol = daily_returns.rolling(VOL_LOOKBACK).std() * math.sqrt(252)
    vol_percentile = (rolling_vol < realized_vol).mean() * 100

    # Don't trade in extreme volatility (circuit breaker)
    if vol_percentile > EXTREME_VOL_PERCENTILE:
        return None

    if excess_return > 0:
        return "LONG"
    elif excess_return < 0:
        return "SHORT"
    return None


def compute_vol_scaled_size(df: pd.DataFrame, target_vol: float = VOL_TARGET) -> float:
    """
    Volatility-targeted position sizing.
    
    Position size = target_vol / realized_vol
    Capped at 2x to prevent excessive leverage.
    """
    daily_returns = df["close"].pct_change().dropna()
    if len(daily_returns) < VOL_LOOKBACK:
        return 1.0

    realized_vol = daily_returns.tail(VOL_LOOKBACK).std() * math.sqrt(252)
    if realized_vol <= 0:
        return 1.0

    size = target_vol / realized_vol
    return min(size, 2.0)  # Cap at 2x


def evaluate_tsmom_signals(asset_class_filter: str = "") -> List[Dict]:
    """Generate TSMOM signals for all symbols."""
    picks = []
    now_iso = datetime.now(timezone.utc).isoformat()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    symbols = ALL_SYMBOLS
    if asset_class_filter:
        symbols = {k: v for k, v in ALL_SYMBOLS.items() if v["asset_class"] == asset_class_filter.upper()}

    for symbol, info in symbols.items():
        df = _fetch_ohlcv(symbol)
        if df.empty or len(df) < LOOKBACK_DAYS + 20:
            print(f"[TSMOM] Skipping {symbol}: insufficient data ({len(df)} bars)")
            continue

        signal = compute_tsmom_signal(df, LOOKBACK_DAYS)
        if signal is None:
            print(f"[TSMOM] {symbol}: No signal (extreme vol or insufficient trend)")
            continue

        price = float(df["close"].iloc[-1])
        atr_val = float(_atr(df["high"], df["low"], df["close"], ATR_PERIOD).iloc[-1])
        vol_size = compute_vol_scaled_size(df)

        if pd.isna(atr_val) or atr_val <= 0:
            continue

        # Compute lookback return for reasoning
        lookback_return = (price / float(df["close"].iloc[-LOOKBACK_DAYS]) - 1) * 100
        realized_vol = float(df["close"].pct_change().tail(VOL_LOOKBACK).std() * math.sqrt(252) * 100)

        if signal == "LONG":
            tp = round(price + TP_ATR_MULT * atr_val, 4)
            sl = round(price - SL_ATR_MULT * atr_val, 4)
        else:
            tp = round(price - TP_ATR_MULT * atr_val, 4)
            sl = round(price + SL_ATR_MULT * atr_val, 4)

        # Confidence: stronger trends get higher confidence
        trend_strength = min(abs(lookback_return) / 20, 1.0)
        confidence = round(0.55 + trend_strength * 0.30, 3)

        picks.append({
            "id": f"tsmom::{symbol}::{today_str}_{signal}",
            "strategy": "tsmom",
            "symbol": symbol,
            "direction": signal,
            "entry_price": price,
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": confidence,
            "asset_class": info["asset_class"],
            "source_system": "tsmom",
            "timeframe": "1d",
            "timestamp": now_iso,
            "created_at": now_iso,
            "status": "ACTIVE",
            "vol_scaled_size": round(vol_size, 2),
            "sector": info["sector"],
            "reasoning": [
                f"TSMOM {signal}: {LOOKBACK_DAYS}d return = {lookback_return:+.1f}%",
                f"Realized vol: {realized_vol:.1f}% annualized",
                f"Vol-scaled size: {vol_size:.2f}x",
                "Moskowitz et al. (2012): TSMOM Sharpe 1.5-2.0 across 58 futures",
            ],
        })

        print(f"[TSMOM] {symbol} ({info['name']}): {signal} @ {price:.4f}, "
              f"ret={lookback_return:+.1f}%, vol={realized_vol:.1f}%, size={vol_size:.2f}x")

    return picks


def run(asset_class: str = ""):
    print("[TSMOM] Time-Series Momentum scanner starting...")
    picks = evaluate_tsmom_signals(asset_class)

    # Write to appropriate forward test directories
    futures_picks = [p for p in picks if p["asset_class"] == "FUTURES"]
    bond_picks = [p for p in picks if p["asset_class"] == "BONDS"]

    futures_dir = DATA_DIR / "forward_tests" / "futures"
    bonds_dir = DATA_DIR / "forward_tests" / "bonds"
    futures_dir.mkdir(parents=True, exist_ok=True)
    bonds_dir.mkdir(parents=True, exist_ok=True)

    if futures_picks:
        (futures_dir / "tsmom.json").write_text(json.dumps(futures_picks, indent=2))
        print(f"[TSMOM] Wrote {len(futures_picks)} futures signals")

    if bond_picks:
        (bonds_dir / "tsmom.json").write_text(json.dumps(bond_picks, indent=2))
        print(f"[TSMOM] Wrote {len(bond_picks)} bond signals")

    print(f"[TSMOM] Total: {len(picks)} signals across {len(set(p['asset_class'] for p in picks))} asset classes")
    return picks


if __name__ == "__main__":
    import sys
    ac = sys.argv[1] if len(sys.argv) > 1 else ""
    run(ac)
