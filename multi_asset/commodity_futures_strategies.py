#!/usr/bin/env python3
"""
COMMODITY & FUTURES STRATEGIES v1.0
====================================
Dedicated strategies exploiting commodity/futures-specific edges:

  1. Commodity Seasonality Scanner — seasonal extremes in NG, CL, grains
  2. Gold Safe Haven — LONG gold when VIX spikes + SPY RSI < 30
  3. Crude Oil Mean Reversion — buy WTI after extreme weekly drops
  4. Commodity Momentum (Cross-Commodity) — LONG strongest, SHORT weakest
  5. Dr. Copper Economic Indicator — copper breakout/breakdown signals
  6. Equity Index Gap Reversion — ES/NQ overnight gap mean reversion
  7. Bond-Equity Rotation — rotate between TLT and SPY on risk regime
  8. Contango/Backwardation — futures curve structure signals

All strategies produce picks in the standard scanner.py JSON format.
No fake data. Real yfinance prices. Proven edges only.

Usage:
  # Import into scanner.py and register in STRATEGIES / COMMODITY_STRATEGIES dict
  # Or run standalone for backtesting:
  python multi_asset/commodity_futures_strategies.py --backtest
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# Wire-up: EIA Wednesday proxy from new_equity_commodity_strategies_20
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "alpha_engine"))
    from new_equity_commodity_strategies_20 import energy_eia_inventory_proxy as _eia_proxy
    _EIA_AVAILABLE = True
except Exception:
    _EIA_AVAILABLE = False
    _eia_proxy = None

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance required. pip install yfinance")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = SCRIPT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Symbol universes — commodities & futures
# ---------------------------------------------------------------------------
COMMODITY_SYMBOLS = {
    # Precious metals
    "GC=F":  {"name": "Gold",            "cat": "commodity", "sector": "precious_metals"},
    "SI=F":  {"name": "Silver",          "cat": "commodity", "sector": "precious_metals"},
    # Energy
    "CL=F":  {"name": "WTI Crude Oil",   "cat": "commodity", "sector": "energy"},
    "NG=F":  {"name": "Natural Gas",     "cat": "commodity", "sector": "energy"},
    # Industrial metals
    "HG=F":  {"name": "Copper",          "cat": "commodity", "sector": "industrial_metals"},
    # Agriculture (ETF proxies — futures tickers unreliable on yfinance)
    "CORN":  {"name": "Corn ETF",        "cat": "commodity", "sector": "agriculture"},
    "WEAT":  {"name": "Wheat ETF",       "cat": "commodity", "sector": "agriculture"},
    "SOYB":  {"name": "Soybean ETF",     "cat": "commodity", "sector": "agriculture"},
}

FUTURES_SYMBOLS = {
    "ES=F":  {"name": "S&P 500 E-mini",    "cat": "futures", "sector": "equity_index"},
    "NQ=F":  {"name": "Nasdaq 100 E-mini",  "cat": "futures", "sector": "equity_index"},
    "YM=F":  {"name": "Dow E-mini",         "cat": "futures", "sector": "equity_index"},
    "RTY=F": {"name": "Russell 2000 E-mini", "cat": "futures", "sector": "equity_index"},
    # Bonds
    "ZB=F":  {"name": "30-Year T-Bond",     "cat": "futures", "sector": "bonds"},
    "ZN=F":  {"name": "10-Year T-Note",     "cat": "futures", "sector": "bonds"},
    "ZT=F":  {"name": "2-Year T-Note",      "cat": "futures", "sector": "bonds"},
}

# Combined universe for this module
ALL_CF_SYMBOLS = {**COMMODITY_SYMBOLS, **FUTURES_SYMBOLS}

# Risk parameters: (stop_loss_pct, take_profit_pct, max_hold_days)
RISK_PARAMS = {
    "commodity":      (-0.04, 0.08, 10),
    "futures":        (-0.04, 0.08, 10),
    "commodity_mr":   (-0.03, 0.05, 5),     # Mean reversion: tighter, shorter
    "safe_haven":     (-0.03, 0.10, 15),    # Safe haven: wider TP, longer hold
    "rotation":       (-0.04, 0.10, 20),    # Rotation: longer hold
    "gap_reversion":  (-0.015, 0.025, 3),   # Gap fills: very short hold
}


# ---------------------------------------------------------------------------
# Seasonal patterns — month-based expected direction
# ---------------------------------------------------------------------------
# Source: 30+ year commodity seasonal studies (Moore Research, MRCI)
SEASONAL_PATTERNS = {
    "NG=F": {
        # Nat gas: buy Oct-Nov (pre-winter), sell Mar-Apr (post-winter)
        "buy_months":  [10, 11],
        "sell_months": [3, 4],
        "name": "Natural Gas Winter Demand",
    },
    "CL=F": {
        # Crude: buy Feb-Mar (pre-summer driving), sell Sep-Oct (post-summer)
        "buy_months":  [2, 3],
        "sell_months": [9, 10],
        "name": "Crude Oil Driving Season",
    },
    "CORN": {
        # Corn: buy Sep-Oct (harvest low), sell Jun-Jul (pre-harvest uncertainty)
        "buy_months":  [9, 10],
        "sell_months": [6, 7],
        "name": "Corn Harvest Cycle",
    },
    "WEAT": {
        # Wheat: buy Jun-Jul (harvest pressure low), sell Dec-Jan (storage)
        "buy_months":  [6, 7],
        "sell_months": [12, 1],
        "name": "Wheat Harvest Cycle",
    },
    "SOYB": {
        # Soybeans: buy Oct (harvest), sell May-Jun (planting)
        "buy_months":  [10, 11],
        "sell_months": [5, 6],
        "name": "Soybean Planting Cycle",
    },
    "GC=F": {
        # Gold: buy Jul-Aug (Indian wedding/Diwali demand ahead), sell Jan
        "buy_months":  [7, 8],
        "sell_months": [1],
        "name": "Gold Seasonal Demand",
    },
    "HG=F": {
        # Copper: buy Dec-Jan (Chinese restocking ahead), sell May-Jun
        "buy_months":  [12, 1],
        "sell_months": [5, 6],
        "name": "Copper Restocking Cycle",
    },
}


# ---------------------------------------------------------------------------
# Technical Indicators (self-contained, mirrors scanner.py)
# ---------------------------------------------------------------------------

def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    atr_val = atr(high, low, close, period)
    plus_di = 100 * ema(plus_dm, period) / atr_val.replace(0, np.nan)
    minus_di = 100 * ema(minus_dm, period) / atr_val.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return ema(dx, period)

def bollinger_bands(series: pd.Series, period: int = 20, std_mult: float = 2.0):
    mid = sma(series, period)
    std = series.rolling(period).std()
    return mid, mid + std_mult * std, mid - std_mult * std

def weekly_return(close: pd.Series) -> float:
    """Return percentage change over last 5 trading days."""
    if len(close) < 6:
        return 0.0
    return float((close.iloc[-1] / close.iloc[-6]) - 1)


# ---------------------------------------------------------------------------
# STRATEGY 1: Commodity Seasonality Scanner
# ---------------------------------------------------------------------------

def commodity_seasonality(df: pd.DataFrame, symbol: str, info: dict) -> list[dict]:
    """
    Commodity Seasonality Scanner
    =============================
    Identifies when commodities enter their seasonal buy/sell windows.
    Confirms with RSI and trend alignment (don't fight the trend).

    Edge: 30+ years of seasonal data show commodities follow planting,
    harvest, weather, and demand cycles with 55-65% reliability.
    Adding RSI confirmation improves to estimated 60-70% WR.
    """
    signals = []
    if symbol not in SEASONAL_PATTERNS:
        return signals
    if len(df) < 50:
        return signals

    pattern = SEASONAL_PATTERNS[symbol]
    close = df["Close"]
    price = float(close.iloc[-1])

    # Get current month from the last data point
    last_date = df.index[-1]
    if hasattr(last_date, 'month'):
        current_month = last_date.month
    else:
        current_month = datetime.now().month

    rsi_14 = rsi(close, 14)
    rsi_val = float(rsi_14.iloc[-1])
    sma_50 = sma(close, 50)
    sma_50_val = float(sma_50.iloc[-1]) if len(df) >= 50 else price
    atr_val = float(atr(df["High"], df["Low"], close, 14).iloc[-1])

    if not all(np.isfinite([price, rsi_val, sma_50_val, atr_val])):
        return signals

    sl_pct, tp_pct, max_hold = RISK_PARAMS.get("commodity", (-0.04, 0.08, 10))

    # Seasonal BUY window + RSI not overbought + near support
    if current_month in pattern["buy_months"]:
        # Confirm: RSI < 60 (not already overbought) and price within 5% of SMA50
        if rsi_val < 60 and price < sma_50_val * 1.05:
            confidence = 0.60 + (60 - rsi_val) * 0.003  # Higher confidence if more oversold
            confidence = min(0.80, max(0.55, confidence))
            signals.append({
                "strategy": "commodity_seasonality",
                "symbol": symbol,
                "category": info.get("cat", "commodity"),
                "direction": "LONG",
                "signal_type": "BUY",
                "entry_price": price,
                "take_profit": price * (1 + abs(tp_pct)),
                "stop_loss": price * (1 + sl_pct),
                "confidence": round(confidence, 3),
                "risk_reward": abs(tp_pct) / abs(sl_pct),
                "reason": (f"Seasonal BUY window ({pattern['name']}), "
                           f"month={current_month}, RSI(14)={rsi_val:.1f}"),
                "rsi_at_entry": rsi_val,
                "atr_at_entry": atr_val,
                "max_hold_days": max_hold,
            })

    # Seasonal SELL window + RSI not oversold + near resistance
    if current_month in pattern["sell_months"]:
        if rsi_val > 40 and price > sma_50_val * 0.95:
            confidence = 0.55 + (rsi_val - 40) * 0.003
            confidence = min(0.75, max(0.55, confidence))
            signals.append({
                "strategy": "commodity_seasonality",
                "symbol": symbol,
                "category": info.get("cat", "commodity"),
                "direction": "SHORT",
                "signal_type": "SELL",
                "entry_price": price,
                "take_profit": price * (1 - abs(tp_pct)),
                "stop_loss": price * (1 - sl_pct),
                "confidence": round(confidence, 3),
                "risk_reward": abs(tp_pct) / abs(sl_pct),
                "reason": (f"Seasonal SELL window ({pattern['name']}), "
                           f"month={current_month}, RSI(14)={rsi_val:.1f}"),
                "rsi_at_entry": rsi_val,
                "atr_at_entry": atr_val,
                "max_hold_days": max_hold,
            })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 2: Gold Safe Haven
# ---------------------------------------------------------------------------

def gold_safe_haven(df: pd.DataFrame, symbol: str, info: dict,
                    vix_data: pd.DataFrame | None = None,
                    spy_data: pd.DataFrame | None = None) -> list[dict]:
    """
    Gold Safe Haven Strategy
    ========================
    LONG gold (GC=F, GLD, SI=F) when market fear spikes.
    Trigger: VIX > 25 AND SPY RSI(14) < 30
    Edge: Gold historically rallies 3-8% during fear episodes.
    Estimated WR: 65-70% over 10-15 day hold.
    """
    signals = []
    # Only applies to precious metals
    if symbol not in ("GC=F", "GLD", "SI=F"):
        return signals
    if len(df) < 50:
        return signals
    if vix_data is None or len(vix_data) < 14:
        return signals
    if spy_data is None or len(spy_data) < 14:
        return signals

    close = df["Close"]
    price = float(close.iloc[-1])

    # VIX check
    vix_close = vix_data["Close"]
    try:
        vix_last = vix_close.iloc[-1]
        if hasattr(vix_last, 'values'):
            vix_last = vix_last.values[0]
        vix_val = float(vix_last)
    except (IndexError, TypeError, ValueError):
        return signals

    # SPY RSI check
    spy_close = spy_data["Close"]
    spy_rsi_14 = rsi(spy_close, 14)
    spy_rsi_val = float(spy_rsi_14.iloc[-1])

    if not all(np.isfinite([price, vix_val, spy_rsi_val])):
        return signals

    atr_val = float(atr(df["High"], df["Low"], close, 14).iloc[-1])
    sl_pct, tp_pct, max_hold = RISK_PARAMS["safe_haven"]

    # Primary trigger: VIX > 25 AND SPY RSI < 30
    if vix_val > 25 and spy_rsi_val < 30:
        # Strong fear signal — higher confidence
        confidence = 0.70 + min(0.15, (vix_val - 25) * 0.005 + (30 - spy_rsi_val) * 0.005)
        confidence = min(0.90, confidence)
        signals.append({
            "strategy": "gold_safe_haven",
            "symbol": symbol,
            "category": info.get("cat", "commodity"),
            "direction": "LONG",
            "signal_type": "STRONG_BUY",
            "entry_price": price,
            "take_profit": price * (1 + abs(tp_pct)),
            "stop_loss": price * (1 + sl_pct),
            "confidence": round(confidence, 3),
            "risk_reward": abs(tp_pct) / abs(sl_pct),
            "reason": (f"Safe haven trigger: VIX={vix_val:.1f} > 25, "
                       f"SPY RSI(14)={spy_rsi_val:.1f} < 30"),
            "rsi_at_entry": float(rsi(close, 14).iloc[-1]),
            "atr_at_entry": atr_val,
            "vix_at_entry": vix_val,
            "spy_rsi_at_entry": spy_rsi_val,
            "max_hold_days": max_hold,
        })

    # Secondary trigger: VIX > 20 AND SPY RSI < 35 AND gold RSI < 50 (not overbought)
    elif vix_val > 20 and spy_rsi_val < 35:
        gold_rsi = float(rsi(close, 14).iloc[-1])
        if gold_rsi < 50:
            confidence = 0.60 + min(0.10, (vix_val - 20) * 0.004)
            signals.append({
                "strategy": "gold_safe_haven",
                "symbol": symbol,
                "category": info.get("cat", "commodity"),
                "direction": "LONG",
                "signal_type": "BUY",
                "entry_price": price,
                "take_profit": price * (1 + abs(tp_pct) * 0.7),  # Reduced target
                "stop_loss": price * (1 + sl_pct),
                "confidence": round(confidence, 3),
                "risk_reward": round(abs(tp_pct) * 0.7 / abs(sl_pct), 2),
                "reason": (f"Mild fear: VIX={vix_val:.1f} > 20, "
                           f"SPY RSI={spy_rsi_val:.1f} < 35, Gold RSI={gold_rsi:.1f}"),
                "rsi_at_entry": gold_rsi,
                "atr_at_entry": atr_val,
                "vix_at_entry": vix_val,
                "spy_rsi_at_entry": spy_rsi_val,
                "max_hold_days": max_hold,
            })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 3: Crude Oil Mean Reversion
# ---------------------------------------------------------------------------

def crude_oil_mean_reversion(df: pd.DataFrame, symbol: str, info: dict) -> list[dict]:
    """
    Crude Oil Mean Reversion
    ========================
    Buy WTI crude after extreme weekly drops (> 5%) with RSI confirmation.
    Edge: Crude mean-reverts after panic selling. 3-5 day hold.
    Target symbols: CL=F, USO, XLE (energy sector)
    Estimated WR: 60-65% with 3-5 day mean reversion window.

    NOTE: CL=F was previously removed from scanner (3.8% WR, -29.82% PnL)
    due to generic strategies being applied. This strategy is crude-SPECIFIC
    with tighter stops and shorter holds to capture the mean reversion edge.
    """
    signals = []
    if symbol not in ("CL=F", "USO", "XLE", "NG=F"):
        return signals
    if len(df) < 20:
        return signals

    close = df["Close"]
    price = float(close.iloc[-1])

    # Weekly return
    wk_ret = weekly_return(close)
    rsi_14 = rsi(close, 14)
    rsi_val = float(rsi_14.iloc[-1])
    atr_val = float(atr(df["High"], df["Low"], close, 14).iloc[-1])

    if not all(np.isfinite([price, wk_ret, rsi_val, atr_val])):
        return signals

    sl_pct, tp_pct, max_hold = RISK_PARAMS["commodity_mr"]

    # LONG: Weekly drop > 5% AND RSI < 30 → mean reversion buy
    if wk_ret < -0.05 and rsi_val < 30:
        # More extreme drop = higher confidence
        confidence = 0.62 + min(0.18, abs(wk_ret + 0.05) * 2.0)
        confidence = min(0.85, confidence)
        signals.append({
            "strategy": "crude_oil_mean_reversion",
            "symbol": symbol,
            "category": info.get("cat", "commodity"),
            "direction": "LONG",
            "signal_type": "STRONG_BUY",
            "entry_price": price,
            "take_profit": price * (1 + abs(tp_pct)),
            "stop_loss": price * (1 + sl_pct),
            "confidence": round(confidence, 3),
            "risk_reward": abs(tp_pct) / abs(sl_pct),
            "reason": (f"Mean reversion: weekly return={wk_ret*100:.1f}% < -5%, "
                       f"RSI(14)={rsi_val:.1f} < 30"),
            "rsi_at_entry": rsi_val,
            "atr_at_entry": atr_val,
            "weekly_return": round(wk_ret, 4),
            "max_hold_days": max_hold,
        })

    # Moderate drop: > 3% with RSI < 35 (less extreme but still oversold)
    elif wk_ret < -0.03 and rsi_val < 35:
        confidence = 0.55 + min(0.10, abs(wk_ret + 0.03) * 1.5)
        signals.append({
            "strategy": "crude_oil_mean_reversion",
            "symbol": symbol,
            "category": info.get("cat", "commodity"),
            "direction": "LONG",
            "signal_type": "BUY",
            "entry_price": price,
            "take_profit": price * (1 + abs(tp_pct) * 0.7),
            "stop_loss": price * (1 + sl_pct),
            "confidence": round(confidence, 3),
            "risk_reward": round(abs(tp_pct) * 0.7 / abs(sl_pct), 2),
            "reason": (f"Moderate mean reversion: weekly={wk_ret*100:.1f}%, "
                       f"RSI(14)={rsi_val:.1f}"),
            "rsi_at_entry": rsi_val,
            "atr_at_entry": atr_val,
            "weekly_return": round(wk_ret, 4),
            "max_hold_days": max_hold,
        })

    # SHORT: Weekly spike > 5% AND RSI > 70 → overbought mean reversion
    if wk_ret > 0.05 and rsi_val > 70:
        confidence = 0.58 + min(0.15, (wk_ret - 0.05) * 2.0)
        confidence = min(0.80, confidence)
        signals.append({
            "strategy": "crude_oil_mean_reversion",
            "symbol": symbol,
            "category": info.get("cat", "commodity"),
            "direction": "SHORT",
            "signal_type": "SELL",
            "entry_price": price,
            "take_profit": price * (1 - abs(tp_pct)),
            "stop_loss": price * (1 - sl_pct),
            "confidence": round(confidence, 3),
            "risk_reward": abs(tp_pct) / abs(sl_pct),
            "reason": (f"Overbought reversion: weekly={wk_ret*100:+.1f}%, "
                       f"RSI(14)={rsi_val:.1f} > 70"),
            "rsi_at_entry": rsi_val,
            "atr_at_entry": atr_val,
            "weekly_return": round(wk_ret, 4),
            "max_hold_days": max_hold,
        })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 4: Cross-Commodity Momentum
# ---------------------------------------------------------------------------

def commodity_momentum(all_data: dict[str, pd.DataFrame],
                       symbols: dict | None = None) -> list[dict]:
    """
    Cross-Commodity Momentum
    ========================
    Ranks commodities by momentum (20-day ROC + ADX filter).
    LONG the top 2, SHORT the bottom 2.
    Edge: Commodity trends persist longer than equities (supply constraints).
    Estimated WR: 55-60% with trend filter.

    NOTE: This is a CROSS-ASSET strategy — it compares all commodities at once
    rather than scanning individual symbols. Call once per scan cycle.
    """
    signals = []
    momentum_symbols = ["GC=F", "SI=F", "CL=F", "HG=F", "NG=F", "CORN", "WEAT", "SOYB"]
    if symbols is not None:
        momentum_symbols = [s for s in momentum_symbols if s in symbols]

    # Calculate momentum score for each commodity
    scores = []
    for sym in momentum_symbols:
        df = all_data.get(sym)
        if df is None or len(df) < 50:
            continue

        close = df["Close"]
        price = float(close.iloc[-1])

        # 20-day Rate of Change
        roc_20 = float((close.iloc[-1] / close.iloc[-21]) - 1) if len(close) > 20 else 0.0
        # ADX for trend strength
        adx_val = float(adx(df["High"], df["Low"], close, 14).iloc[-1])
        rsi_val = float(rsi(close, 14).iloc[-1])
        atr_val = float(atr(df["High"], df["Low"], close, 14).iloc[-1])

        if not all(np.isfinite([price, roc_20, adx_val, rsi_val, atr_val])):
            continue

        # Only consider assets with ADX > 20 (trending)
        if adx_val < 20:
            continue

        info = ALL_CF_SYMBOLS.get(sym, {"name": sym, "cat": "commodity"})
        scores.append({
            "symbol": sym,
            "info": info,
            "roc_20": roc_20,
            "adx": adx_val,
            "rsi": rsi_val,
            "price": price,
            "atr": atr_val,
            # Momentum score: ROC weighted by ADX strength
            "momentum_score": roc_20 * (adx_val / 30),
        })

    if len(scores) < 3:
        return signals  # Need enough assets to rank

    # Sort by momentum score
    scores.sort(key=lambda x: x["momentum_score"], reverse=True)

    sl_pct, tp_pct, max_hold = RISK_PARAMS["commodity"]

    # LONG top 2 (strongest momentum)
    for entry in scores[:2]:
        if entry["roc_20"] <= 0:
            continue  # Don't go long negative momentum even if "best"
        if entry["rsi"] > 80:
            continue  # Already extremely overbought

        confidence = 0.58 + min(0.17, entry["roc_20"] * 2.0 + (entry["adx"] - 20) * 0.003)
        confidence = min(0.80, max(0.55, confidence))

        signals.append({
            "strategy": "commodity_momentum",
            "symbol": entry["symbol"],
            "category": entry["info"].get("cat", "commodity"),
            "direction": "LONG",
            "signal_type": "BUY",
            "entry_price": entry["price"],
            "take_profit": entry["price"] * (1 + abs(tp_pct)),
            "stop_loss": entry["price"] * (1 + sl_pct),
            "confidence": round(confidence, 3),
            "risk_reward": abs(tp_pct) / abs(sl_pct),
            "reason": (f"Top momentum: ROC(20)={entry['roc_20']*100:+.1f}%, "
                       f"ADX={entry['adx']:.1f}, RSI={entry['rsi']:.1f}"),
            "rsi_at_entry": entry["rsi"],
            "atr_at_entry": entry["atr"],
            "momentum_score": round(entry["momentum_score"], 4),
            "max_hold_days": max_hold,
        })

    # SHORT bottom 2 (weakest momentum)
    for entry in scores[-2:]:
        if entry["roc_20"] >= 0:
            continue  # Don't short positive momentum even if "worst"
        if entry["rsi"] < 20:
            continue  # Already extremely oversold

        confidence = 0.55 + min(0.15, abs(entry["roc_20"]) * 1.5 + (entry["adx"] - 20) * 0.002)
        confidence = min(0.75, max(0.55, confidence))

        signals.append({
            "strategy": "commodity_momentum",
            "symbol": entry["symbol"],
            "category": entry["info"].get("cat", "commodity"),
            "direction": "SHORT",
            "signal_type": "SELL",
            "entry_price": entry["price"],
            "take_profit": entry["price"] * (1 - abs(tp_pct)),
            "stop_loss": entry["price"] * (1 - sl_pct),
            "confidence": round(confidence, 3),
            "risk_reward": abs(tp_pct) / abs(sl_pct),
            "reason": (f"Bottom momentum: ROC(20)={entry['roc_20']*100:+.1f}%, "
                       f"ADX={entry['adx']:.1f}, RSI={entry['rsi']:.1f}"),
            "rsi_at_entry": entry["rsi"],
            "atr_at_entry": entry["atr"],
            "momentum_score": round(entry["momentum_score"], 4),
            "max_hold_days": max_hold,
        })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 5: Dr. Copper Economic Indicator
# ---------------------------------------------------------------------------

def dr_copper_indicator(df: pd.DataFrame, symbol: str, info: dict,
                        copper_data: pd.DataFrame | None = None) -> list[dict]:
    """
    Dr. Copper Economic Indicator
    =============================
    Copper predicts economic health. Use copper breakouts/breakdowns
    to signal industrial/cyclical commodity trades.

    - Copper breaks above 20d high + ADX > 25 → LONG industrials/cyclicals
    - Copper breaks below 20d low + ADX > 25 → SHORT cyclicals
    Target symbols: HG=F (copper itself), XLE, XLF, and other cyclicals.
    Estimated WR: 55-60%.
    """
    signals = []
    # This strategy reads copper data to generate signals on OTHER symbols
    cyclical_targets = ("HG=F", "XLE", "XLF", "CL=F", "ES=F")
    if symbol not in cyclical_targets:
        return signals

    # If scanning copper itself, use its own data; otherwise need copper_data
    if symbol == "HG=F":
        cu_df = df
    elif copper_data is not None and len(copper_data) > 20:
        cu_df = copper_data
    else:
        return signals

    if len(cu_df) < 50 or len(df) < 20:
        return signals

    cu_close = cu_df["Close"]
    cu_price = float(cu_close.iloc[-1])
    cu_high_20 = float(cu_close.rolling(20).max().iloc[-1])
    cu_low_20 = float(cu_close.rolling(20).min().iloc[-1])
    cu_adx = float(adx(cu_df["High"], cu_df["Low"], cu_close, 14).iloc[-1])

    close = df["Close"]
    price = float(close.iloc[-1])
    rsi_val = float(rsi(close, 14).iloc[-1])
    atr_val = float(atr(df["High"], df["Low"], close, 14).iloc[-1])

    if not all(np.isfinite([cu_price, cu_high_20, cu_low_20, cu_adx, price, rsi_val, atr_val])):
        return signals

    sl_pct, tp_pct, max_hold = RISK_PARAMS["commodity"]

    # Copper breakout → LONG cyclicals
    if cu_price >= cu_high_20 and cu_adx > 25:
        if rsi_val < 70:  # Target not already overbought
            confidence = 0.58 + min(0.12, (cu_adx - 25) * 0.004)
            signals.append({
                "strategy": "dr_copper_indicator",
                "symbol": symbol,
                "category": info.get("cat", "commodity"),
                "direction": "LONG",
                "signal_type": "BUY",
                "entry_price": price,
                "take_profit": price * (1 + abs(tp_pct)),
                "stop_loss": price * (1 + sl_pct),
                "confidence": round(confidence, 3),
                "risk_reward": abs(tp_pct) / abs(sl_pct),
                "reason": (f"Dr. Copper BREAKOUT: Cu=${cu_price:.2f} at 20d high, "
                           f"ADX={cu_adx:.1f}, {symbol} RSI={rsi_val:.1f}"),
                "rsi_at_entry": rsi_val,
                "atr_at_entry": atr_val,
                "copper_price": cu_price,
                "copper_adx": round(cu_adx, 1),
                "max_hold_days": max_hold,
            })

    # Copper breakdown → SHORT cyclicals
    if cu_price <= cu_low_20 and cu_adx > 25:
        if rsi_val > 30:  # Target not already oversold
            confidence = 0.55 + min(0.10, (cu_adx - 25) * 0.003)
            signals.append({
                "strategy": "dr_copper_indicator",
                "symbol": symbol,
                "category": info.get("cat", "commodity"),
                "direction": "SHORT",
                "signal_type": "SELL",
                "entry_price": price,
                "take_profit": price * (1 - abs(tp_pct)),
                "stop_loss": price * (1 - sl_pct),
                "confidence": round(confidence, 3),
                "risk_reward": abs(tp_pct) / abs(sl_pct),
                "reason": (f"Dr. Copper BREAKDOWN: Cu=${cu_price:.2f} at 20d low, "
                           f"ADX={cu_adx:.1f}, {symbol} RSI={rsi_val:.1f}"),
                "rsi_at_entry": rsi_val,
                "atr_at_entry": atr_val,
                "copper_price": cu_price,
                "copper_adx": round(cu_adx, 1),
                "max_hold_days": max_hold,
            })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 6: Equity Index Gap Reversion
# ---------------------------------------------------------------------------

def equity_index_gap_reversion(df: pd.DataFrame, symbol: str, info: dict) -> list[dict]:
    """
    Equity Index Gap Reversion
    ==========================
    ES and NQ mean-revert after overnight gaps.
    - Gap down > 0.5% at open → BUY for intraday/short-term mean reversion
    - Gap up > 0.5% at open → SHORT for mean reversion
    Historical WR: 60-65% on ES/NQ.

    Uses daily bars: gap = today's Open vs yesterday's Close.
    Hold period: 1-3 days.
    """
    signals = []
    if symbol not in ("ES=F", "NQ=F", "YM=F", "RTY=F", "SPY", "QQQ"):
        return signals
    if len(df) < 20:
        return signals

    close = df["Close"]
    open_price = df["Open"]

    # Today's gap: current Open vs previous Close
    today_open = float(open_price.iloc[-1])
    prev_close = float(close.iloc[-2])
    current_price = float(close.iloc[-1])

    if not all(np.isfinite([today_open, prev_close, current_price])):
        return signals

    gap_pct = (today_open / prev_close) - 1
    rsi_val = float(rsi(close, 14).iloc[-1])
    atr_val = float(atr(df["High"], df["Low"], close, 14).iloc[-1])

    if not all(np.isfinite([gap_pct, rsi_val, atr_val])):
        return signals

    sl_pct, tp_pct, max_hold = RISK_PARAMS["gap_reversion"]

    # Gap down > 0.5% → BUY (gap fill)
    if gap_pct < -0.005:
        # Check if gap hasn't already filled (current close still below prev close)
        if current_price < prev_close:
            gap_unfilled_pct = abs((current_price / prev_close) - 1)
            confidence = 0.60 + min(0.15, abs(gap_pct) * 5.0)
            confidence = min(0.80, confidence)
            signals.append({
                "strategy": "equity_index_gap_reversion",
                "symbol": symbol,
                "category": info.get("cat", "futures"),
                "direction": "LONG",
                "signal_type": "BUY",
                "entry_price": current_price,
                "take_profit": prev_close,  # Target: fill the gap
                "stop_loss": current_price * (1 + sl_pct),
                "confidence": round(confidence, 3),
                "risk_reward": round(gap_unfilled_pct / abs(sl_pct), 2) if abs(sl_pct) > 0 else 1.0,
                "reason": (f"Gap down {gap_pct*100:.2f}% (unfilled {gap_unfilled_pct*100:.2f}%), "
                           f"RSI={rsi_val:.1f}"),
                "rsi_at_entry": rsi_val,
                "atr_at_entry": atr_val,
                "gap_pct": round(gap_pct, 4),
                "max_hold_days": max_hold,
            })

    # Gap up > 0.5% → SHORT (gap fill)
    if gap_pct > 0.005:
        if current_price > prev_close:
            gap_unfilled_pct = abs((current_price / prev_close) - 1)
            confidence = 0.58 + min(0.12, gap_pct * 4.0)
            confidence = min(0.75, confidence)
            signals.append({
                "strategy": "equity_index_gap_reversion",
                "symbol": symbol,
                "category": info.get("cat", "futures"),
                "direction": "SHORT",
                "signal_type": "SELL",
                "entry_price": current_price,
                "take_profit": prev_close,  # Target: fill the gap
                "stop_loss": current_price * (1 - sl_pct),
                "confidence": round(confidence, 3),
                "risk_reward": round(gap_unfilled_pct / abs(sl_pct), 2) if abs(sl_pct) > 0 else 1.0,
                "reason": (f"Gap up {gap_pct*100:+.2f}% (unfilled {gap_unfilled_pct*100:.2f}%), "
                           f"RSI={rsi_val:.1f}"),
                "rsi_at_entry": rsi_val,
                "atr_at_entry": atr_val,
                "gap_pct": round(gap_pct, 4),
                "max_hold_days": max_hold,
            })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 7: Bond-Equity Rotation
# ---------------------------------------------------------------------------

def bond_equity_rotation(all_data: dict[str, pd.DataFrame]) -> list[dict]:
    """
    Bond-Equity Rotation
    ====================
    Rotate between bonds (TLT/ZB=F) and equities (SPY/ES=F) based on
    relative momentum and risk regime.

    - Bonds rally + stocks drop = risk-off → LONG bonds, SHORT equities
    - Bonds drop + stocks rally = risk-on → LONG equities, SHORT bonds
    - Confirm with 20-day relative strength

    Estimated WR: 55-60% with 2-3 week rotation windows.
    """
    signals = []

    # Need both bond and equity data
    bond_symbols = ["TLT", "ZB=F", "ZN=F"]
    equity_symbols = ["SPY", "ES=F"]

    bond_df = None
    bond_sym = None
    for sym in bond_symbols:
        if sym in all_data and len(all_data[sym]) >= 50:
            bond_df = all_data[sym]
            bond_sym = sym
            break

    equity_df = None
    equity_sym = None
    for sym in equity_symbols:
        if sym in all_data and len(all_data[sym]) >= 50:
            equity_df = all_data[sym]
            equity_sym = sym
            break

    if bond_df is None or equity_df is None:
        return signals

    # 20-day momentum for both
    bond_close = bond_df["Close"]
    equity_close = equity_df["Close"]

    bond_roc = float((bond_close.iloc[-1] / bond_close.iloc[-21]) - 1) if len(bond_close) > 20 else 0.0
    equity_roc = float((equity_close.iloc[-1] / equity_close.iloc[-21]) - 1) if len(equity_close) > 20 else 0.0

    bond_rsi = float(rsi(bond_close, 14).iloc[-1])
    equity_rsi = float(rsi(equity_close, 14).iloc[-1])

    bond_price = float(bond_close.iloc[-1])
    equity_price = float(equity_close.iloc[-1])

    bond_atr = float(atr(bond_df["High"], bond_df["Low"], bond_close, 14).iloc[-1])
    equity_atr = float(atr(equity_df["High"], equity_df["Low"], equity_close, 14).iloc[-1])

    if not all(np.isfinite([bond_roc, equity_roc, bond_rsi, equity_rsi,
                            bond_price, equity_price, bond_atr, equity_atr])):
        return signals

    sl_pct, tp_pct, max_hold = RISK_PARAMS["rotation"]

    # Relative strength differential
    rel_diff = bond_roc - equity_roc

    # RISK-OFF: Bonds outperforming equities significantly (> 2%)
    if rel_diff > 0.02 and bond_roc > 0 and equity_roc < 0:
        confidence = 0.58 + min(0.15, rel_diff * 3.0)
        confidence = min(0.78, confidence)

        # LONG bonds
        if bond_rsi < 75:  # Not already extreme
            bond_info = ALL_CF_SYMBOLS.get(bond_sym, {"cat": "futures"})
            signals.append({
                "strategy": "bond_equity_rotation",
                "symbol": bond_sym,
                "category": bond_info.get("cat", "futures"),
                "direction": "LONG",
                "signal_type": "BUY",
                "entry_price": bond_price,
                "take_profit": bond_price * (1 + abs(tp_pct)),
                "stop_loss": bond_price * (1 + sl_pct),
                "confidence": round(confidence, 3),
                "risk_reward": abs(tp_pct) / abs(sl_pct),
                "reason": (f"Risk-OFF rotation: bonds ROC(20)={bond_roc*100:+.1f}% vs "
                           f"equities {equity_roc*100:+.1f}%, rel_diff={rel_diff*100:+.1f}%"),
                "rsi_at_entry": bond_rsi,
                "atr_at_entry": bond_atr,
                "max_hold_days": max_hold,
            })

        # SHORT equities
        if equity_rsi > 25:  # Not already extreme
            equity_info = ALL_CF_SYMBOLS.get(equity_sym, {"cat": "futures"})
            signals.append({
                "strategy": "bond_equity_rotation",
                "symbol": equity_sym,
                "category": equity_info.get("cat", "futures"),
                "direction": "SHORT",
                "signal_type": "SELL",
                "entry_price": equity_price,
                "take_profit": equity_price * (1 - abs(tp_pct)),
                "stop_loss": equity_price * (1 - sl_pct),
                "confidence": round(min(0.72, confidence - 0.03), 3),
                "risk_reward": abs(tp_pct) / abs(sl_pct),
                "reason": (f"Risk-OFF rotation: SHORT equities, bonds outperforming by "
                           f"{rel_diff*100:+.1f}%"),
                "rsi_at_entry": equity_rsi,
                "atr_at_entry": equity_atr,
                "max_hold_days": max_hold,
            })

    # RISK-ON: Equities outperforming bonds significantly (> 2%)
    elif rel_diff < -0.02 and equity_roc > 0 and bond_roc < 0:
        confidence = 0.58 + min(0.15, abs(rel_diff) * 3.0)
        confidence = min(0.78, confidence)

        # LONG equities
        if equity_rsi < 75:
            equity_info = ALL_CF_SYMBOLS.get(equity_sym, {"cat": "futures"})
            signals.append({
                "strategy": "bond_equity_rotation",
                "symbol": equity_sym,
                "category": equity_info.get("cat", "futures"),
                "direction": "LONG",
                "signal_type": "BUY",
                "entry_price": equity_price,
                "take_profit": equity_price * (1 + abs(tp_pct)),
                "stop_loss": equity_price * (1 + sl_pct),
                "confidence": round(confidence, 3),
                "risk_reward": abs(tp_pct) / abs(sl_pct),
                "reason": (f"Risk-ON rotation: equities ROC(20)={equity_roc*100:+.1f}% vs "
                           f"bonds {bond_roc*100:+.1f}%, rel_diff={rel_diff*100:+.1f}%"),
                "rsi_at_entry": equity_rsi,
                "atr_at_entry": equity_atr,
                "max_hold_days": max_hold,
            })

        # SHORT bonds
        if bond_rsi > 25:
            bond_info = ALL_CF_SYMBOLS.get(bond_sym, {"cat": "futures"})
            signals.append({
                "strategy": "bond_equity_rotation",
                "symbol": bond_sym,
                "category": bond_info.get("cat", "futures"),
                "direction": "SHORT",
                "signal_type": "SELL",
                "entry_price": bond_price,
                "take_profit": bond_price * (1 - abs(tp_pct)),
                "stop_loss": bond_price * (1 - sl_pct),
                "confidence": round(min(0.72, confidence - 0.03), 3),
                "risk_reward": abs(tp_pct) / abs(sl_pct),
                "reason": (f"Risk-ON rotation: SHORT bonds, equities outperforming by "
                           f"{abs(rel_diff)*100:.1f}%"),
                "rsi_at_entry": bond_rsi,
                "atr_at_entry": bond_atr,
                "max_hold_days": max_hold,
            })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 8: Commodity Bollinger Squeeze
# ---------------------------------------------------------------------------

def commodity_bollinger_squeeze(df: pd.DataFrame, symbol: str, info: dict) -> list[dict]:
    """
    Commodity Bollinger Squeeze
    ===========================
    Commodities exhibit strong breakouts after low-volatility compression.
    When Bollinger Band width < 20-day average AND ADX starts rising,
    enter in the direction of the breakout.

    Edge: Commodity supply shocks cause explosive moves after quiet periods.
    Estimated WR: 55-60% with proper directional confirmation.
    """
    signals = []
    commodity_targets = ("GC=F", "SI=F", "CL=F", "HG=F", "NG=F", "CORN", "WEAT", "SOYB")
    if symbol not in commodity_targets:
        return signals
    if len(df) < 50:
        return signals

    close = df["Close"]
    price = float(close.iloc[-1])

    # Bollinger Bands
    mid, upper, lower = bollinger_bands(close, 20, 2.0)
    bb_width = (upper - lower) / mid
    bb_width_current = float(bb_width.iloc[-1])
    bb_width_avg = float(bb_width.rolling(20).mean().iloc[-1])

    # ADX for trend emergence
    adx_val = float(adx(df["High"], df["Low"], close, 14).iloc[-1])
    adx_prev = float(adx(df["High"], df["Low"], close, 14).iloc[-3])
    rsi_val = float(rsi(close, 14).iloc[-1])
    atr_val = float(atr(df["High"], df["Low"], close, 14).iloc[-1])

    if not all(np.isfinite([price, bb_width_current, bb_width_avg, adx_val, adx_prev, rsi_val, atr_val])):
        return signals

    sl_pct, tp_pct, max_hold = RISK_PARAMS["commodity"]

    # Squeeze detected: BB width < average AND ADX rising
    if bb_width_current < bb_width_avg * 0.8 and adx_val > adx_prev:
        upper_val = float(upper.iloc[-1])
        lower_val = float(lower.iloc[-1])
        mid_val = float(mid.iloc[-1])

        # Breakout direction: price above mid = bullish, below = bearish
        if price > mid_val and rsi_val > 50:
            confidence = 0.58 + min(0.15, (adx_val - adx_prev) * 0.02)
            confidence = min(0.78, confidence)
            signals.append({
                "strategy": "commodity_bollinger_squeeze",
                "symbol": symbol,
                "category": info.get("cat", "commodity"),
                "direction": "LONG",
                "signal_type": "BUY",
                "entry_price": price,
                "take_profit": price + 2.0 * atr_val,  # ATR-based TP
                "stop_loss": price - 1.0 * atr_val,     # ATR-based SL
                "confidence": round(confidence, 3),
                "risk_reward": 2.0,
                "reason": (f"BB Squeeze breakout UP: width={bb_width_current:.4f} < "
                           f"avg={bb_width_avg:.4f}, ADX rising {adx_prev:.1f}→{adx_val:.1f}"),
                "rsi_at_entry": rsi_val,
                "atr_at_entry": atr_val,
                "bb_width": round(bb_width_current, 4),
                "max_hold_days": max_hold,
            })

        elif price < mid_val and rsi_val < 50:
            confidence = 0.55 + min(0.12, (adx_val - adx_prev) * 0.02)
            confidence = min(0.72, confidence)
            signals.append({
                "strategy": "commodity_bollinger_squeeze",
                "symbol": symbol,
                "category": info.get("cat", "commodity"),
                "direction": "SHORT",
                "signal_type": "SELL",
                "entry_price": price,
                "take_profit": price - 2.0 * atr_val,
                "stop_loss": price + 1.0 * atr_val,
                "confidence": round(confidence, 3),
                "risk_reward": 2.0,
                "reason": (f"BB Squeeze breakout DOWN: width={bb_width_current:.4f} < "
                           f"avg={bb_width_avg:.4f}, ADX rising {adx_prev:.1f}→{adx_val:.1f}"),
                "rsi_at_entry": rsi_val,
                "atr_at_entry": atr_val,
                "bb_width": round(bb_width_current, 4),
                "max_hold_days": max_hold,
            })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 9: Treasury Yield Curve (Bond)
# ---------------------------------------------------------------------------

def treasury_yield_curve(all_data: dict[str, pd.DataFrame]) -> list[dict]:
    """
    Treasury Yield Curve Strategy
    ==============================
    Compares short-duration (SHY/ZT=F) vs long-duration (TLT/ZB=F) bonds.
    When the yield curve inverts (short-term bonds outperform long-term),
    it signals recession risk -> go LONG TLT (flight to safety).
    When curve normalizes (long-term outperforms), SHORT TLT (risk-on).

    Proxy: We use price ratio SHY/TLT as a yield curve proxy.
    When SHY outperforms TLT (ratio rising), curve is flattening/inverting.
    When TLT outperforms SHY (ratio falling), curve is steepening.

    Estimated WR: 60-65% with 2-4 week hold periods.
    """
    signals = []

    # Get short-duration data (SHY preferred, ZT=F fallback)
    short_df = None
    short_sym = None
    for sym in ["SHY", "ZT=F"]:
        if sym in all_data and len(all_data[sym]) >= 50:
            short_df = all_data[sym]
            short_sym = sym
            break

    # Get long-duration data (TLT preferred, ZB=F fallback)
    long_df = None
    long_sym = None
    for sym in ["TLT", "ZB=F"]:
        if sym in all_data and len(all_data[sym]) >= 50:
            long_df = all_data[sym]
            long_sym = sym
            break

    if short_df is None or long_df is None:
        return signals

    short_close = short_df["Close"]
    long_close = long_df["Close"]

    # Price ratio: SHY/TLT (rising = curve flattening/inverting)
    # Use aligned data (last 50 bars)
    min_len = min(len(short_close), len(long_close))
    if min_len < 50:
        return signals

    short_prices = short_close.iloc[-min_len:]
    long_prices = long_close.iloc[-min_len:]

    # 20-day rate of change for both
    short_roc = float((short_prices.iloc[-1] / short_prices.iloc[-21]) - 1)
    long_roc = float((long_prices.iloc[-1] / long_prices.iloc[-21]) - 1)

    long_price = float(long_prices.iloc[-1])
    long_rsi = float(rsi(long_prices, 14).iloc[-1])
    long_atr = float(atr(long_df["High"].iloc[-min_len:],
                         long_df["Low"].iloc[-min_len:],
                         long_prices, 14).iloc[-1])

    if not all(np.isfinite([short_roc, long_roc, long_price, long_rsi, long_atr])):
        return signals

    # Curve differential: positive = short outperforming (flattening/inverting)
    curve_diff = short_roc - long_roc
    sl_pct, tp_pct, max_hold = RISK_PARAMS["rotation"]

    # CURVE INVERTING: Short bonds outperforming long bonds -> recession signal
    # LONG TLT (flight to safety, rates will eventually drop)
    if curve_diff > 0.01 and long_rsi < 60:
        confidence = 0.58 + min(0.17, curve_diff * 5.0)
        confidence = min(0.80, confidence)
        tp = long_price * (1 + abs(tp_pct))
        sl = long_price * (1 + sl_pct)
        rr = abs(tp_pct) / abs(sl_pct)
        if rr >= 1.5:
            signals.append({
                "strategy": "treasury_yield_curve",
                "symbol": long_sym,
                "category": "bond",
                "direction": "LONG",
                "signal_type": "BUY",
                "entry_price": long_price,
                "take_profit": round(tp, 2),
                "stop_loss": round(sl, 2),
                "confidence": round(confidence, 3),
                "risk_reward": round(rr, 2),
                "reason": (f"Yield curve flattening: {short_sym} ROC(20)={short_roc*100:+.1f}% "
                           f"vs {long_sym} {long_roc*100:+.1f}%, diff={curve_diff*100:+.1f}%"),
                "rsi_at_entry": round(long_rsi, 1),
                "atr_at_entry": round(long_atr, 4),
                "max_hold_days": max_hold,
            })

    # CURVE STEEPENING: Long bonds outperforming short bonds -> growth signal
    # SHORT TLT (rates rising, bonds falling)
    elif curve_diff < -0.01 and long_rsi > 40:
        confidence = 0.55 + min(0.15, abs(curve_diff) * 4.0)
        confidence = min(0.75, confidence)
        tp = long_price * (1 - abs(tp_pct))
        sl = long_price * (1 - sl_pct)
        rr = abs(tp_pct) / abs(sl_pct)
        if rr >= 1.5:
            signals.append({
                "strategy": "treasury_yield_curve",
                "symbol": long_sym,
                "category": "bond",
                "direction": "SHORT",
                "signal_type": "SELL",
                "entry_price": long_price,
                "take_profit": round(tp, 2),
                "stop_loss": round(sl, 2),
                "confidence": round(confidence, 3),
                "risk_reward": round(rr, 2),
                "reason": (f"Yield curve steepening: {long_sym} ROC(20)={long_roc*100:+.1f}% "
                           f"vs {short_sym} {short_roc*100:+.1f}%, diff={curve_diff*100:+.1f}%"),
                "rsi_at_entry": round(long_rsi, 1),
                "atr_at_entry": round(long_atr, 4),
                "max_hold_days": max_hold,
            })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 10: Credit Spread (Bond)
# ---------------------------------------------------------------------------

def credit_spread_strategy(all_data: dict[str, pd.DataFrame]) -> list[dict]:
    """
    Credit Spread Strategy
    =======================
    Monitors HYG/LQD ratio (high yield vs investment grade corporate bonds).
    When ratio drops (credit stress), go LONG treasuries (TLT/IEF).
    When ratio rises (risk-on), SHORT treasuries.

    Edge: Credit spreads lead equity selloffs by 2-4 weeks.
    When HYG underperforms LQD, smart money is de-risking.
    Estimated WR: 60-65% on 2-3 week holds.
    """
    signals = []

    # Need HYG and LQD
    hyg_df = all_data.get("HYG")
    lqd_df = all_data.get("LQD")

    if hyg_df is None or lqd_df is None:
        return signals
    if len(hyg_df) < 50 or len(lqd_df) < 50:
        return signals

    # Get treasury target
    treas_df = None
    treas_sym = None
    for sym in ["TLT", "IEF", "BND"]:
        if sym in all_data and len(all_data[sym]) >= 50:
            treas_df = all_data[sym]
            treas_sym = sym
            break

    if treas_df is None:
        return signals

    hyg_close = hyg_df["Close"]
    lqd_close = lqd_df["Close"]
    treas_close = treas_df["Close"]

    # HYG/LQD ratio and its momentum
    min_len = min(len(hyg_close), len(lqd_close))
    if min_len < 30:
        return signals

    hyg_prices = hyg_close.iloc[-min_len:]
    lqd_prices = lqd_close.iloc[-min_len:]

    # Compute ratio
    ratio = hyg_prices / lqd_prices.values
    ratio_now = float(ratio.iloc[-1])
    ratio_10d = float(ratio.iloc[-11]) if len(ratio) > 10 else ratio_now
    ratio_20d = float(ratio.iloc[-21]) if len(ratio) > 20 else ratio_now

    ratio_change_10d = (ratio_now / ratio_10d) - 1 if ratio_10d > 0 else 0
    ratio_change_20d = (ratio_now / ratio_20d) - 1 if ratio_20d > 0 else 0

    treas_price = float(treas_close.iloc[-1])
    treas_rsi = float(rsi(treas_close, 14).iloc[-1])
    treas_atr = float(atr(treas_df["High"], treas_df["Low"], treas_close, 14).iloc[-1])

    if not all(np.isfinite([ratio_now, ratio_change_10d, ratio_change_20d,
                            treas_price, treas_rsi, treas_atr])):
        return signals

    sl_pct, tp_pct, max_hold = RISK_PARAMS["rotation"]

    # CREDIT STRESS: HYG/LQD ratio falling (HYG underperforming)
    # -> LONG treasuries (flight to safety)
    if ratio_change_10d < -0.005 and ratio_change_20d < -0.005 and treas_rsi < 65:
        stress_magnitude = abs(ratio_change_10d) + abs(ratio_change_20d)
        confidence = 0.60 + min(0.18, stress_magnitude * 5.0)
        confidence = min(0.82, confidence)
        tp = treas_price * (1 + abs(tp_pct))
        sl = treas_price * (1 + sl_pct)
        rr = abs(tp_pct) / abs(sl_pct)
        if rr >= 1.5:
            signals.append({
                "strategy": "credit_spread",
                "symbol": treas_sym,
                "category": "bond",
                "direction": "LONG",
                "signal_type": "BUY",
                "entry_price": round(treas_price, 2),
                "take_profit": round(tp, 2),
                "stop_loss": round(sl, 2),
                "confidence": round(confidence, 3),
                "risk_reward": round(rr, 2),
                "reason": (f"Credit stress: HYG/LQD ratio falling "
                           f"10d={ratio_change_10d*100:+.2f}%, "
                           f"20d={ratio_change_20d*100:+.2f}%"),
                "rsi_at_entry": round(treas_rsi, 1),
                "atr_at_entry": round(treas_atr, 4),
                "max_hold_days": max_hold,
                "extra": {
                    "hyg_lqd_ratio": round(ratio_now, 4),
                    "ratio_change_10d": round(ratio_change_10d, 4),
                    "ratio_change_20d": round(ratio_change_20d, 4),
                },
            })

    # RISK-ON: HYG/LQD ratio rising (credit appetite improving)
    # -> SHORT treasuries (money rotating out of safety)
    elif ratio_change_10d > 0.005 and ratio_change_20d > 0.005 and treas_rsi > 35:
        confidence = 0.55 + min(0.15, (ratio_change_10d + ratio_change_20d) * 3.0)
        confidence = min(0.75, confidence)
        tp = treas_price * (1 - abs(tp_pct))
        sl = treas_price * (1 - sl_pct)
        rr = abs(tp_pct) / abs(sl_pct)
        if rr >= 1.5:
            signals.append({
                "strategy": "credit_spread",
                "symbol": treas_sym,
                "category": "bond",
                "direction": "SHORT",
                "signal_type": "SELL",
                "entry_price": round(treas_price, 2),
                "take_profit": round(tp, 2),
                "stop_loss": round(sl, 2),
                "confidence": round(confidence, 3),
                "risk_reward": round(rr, 2),
                "reason": (f"Risk-on: HYG/LQD ratio rising "
                           f"10d={ratio_change_10d*100:+.2f}%, "
                           f"20d={ratio_change_20d*100:+.2f}%"),
                "rsi_at_entry": round(treas_rsi, 1),
                "atr_at_entry": round(treas_atr, 4),
                "max_hold_days": max_hold,
                "extra": {
                    "hyg_lqd_ratio": round(ratio_now, 4),
                    "ratio_change_10d": round(ratio_change_10d, 4),
                    "ratio_change_20d": round(ratio_change_20d, 4),
                },
            })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 11: Duration Rotation (Bond)
# ---------------------------------------------------------------------------

def duration_rotation(all_data: dict[str, pd.DataFrame]) -> list[dict]:
    """
    Duration Rotation Strategy
    ===========================
    Rotate between TLT (long duration, 20+ year) and SHY (short duration, 1-3y)
    based on rate expectations inferred from price momentum.

    When TLT momentum is positive and SHY is flat/negative -> LONG TLT
    (rates expected to fall, long duration benefits more).
    When SHY outperforms TLT -> LONG SHY (rates rising, short duration safer).
    Also considers IEF as intermediate duration option.

    Estimated WR: 55-60% with monthly rotation.
    """
    signals = []

    # Check for available bond ETFs
    bond_etfs = {}
    for sym in ["TLT", "IEF", "SHY"]:
        if sym in all_data and len(all_data[sym]) >= 50:
            bond_etfs[sym] = all_data[sym]

    if len(bond_etfs) < 2:
        return signals  # Need at least 2 duration buckets

    # Calculate 20-day and 50-day momentum for each
    momentum = {}
    for sym, df in bond_etfs.items():
        close = df["Close"]
        roc_20 = float((close.iloc[-1] / close.iloc[-21]) - 1) if len(close) > 20 else 0.0
        roc_50 = float((close.iloc[-1] / close.iloc[-51]) - 1) if len(close) > 50 else 0.0
        rsi_val = float(rsi(close, 14).iloc[-1])
        price = float(close.iloc[-1])
        atr_val = float(atr(df["High"], df["Low"], close, 14).iloc[-1])
        sma_50_val = float(sma(close, 50).iloc[-1])

        if all(np.isfinite([roc_20, roc_50, rsi_val, price, atr_val, sma_50_val])):
            momentum[sym] = {
                "roc_20": roc_20, "roc_50": roc_50, "rsi": rsi_val,
                "price": price, "atr": atr_val, "sma_50": sma_50_val,
            }

    if len(momentum) < 2:
        return signals

    # Rank by 20-day momentum
    ranked = sorted(momentum.items(), key=lambda x: x[1]["roc_20"], reverse=True)
    best_sym, best = ranked[0]
    worst_sym, worst = ranked[-1]

    sl_pct, tp_pct, max_hold = RISK_PARAMS["rotation"]

    # LONG the strongest duration bucket if trending
    diff = best["roc_20"] - worst["roc_20"]
    if diff > 0.01 and best["roc_20"] > 0 and best["rsi"] < 70 and best["price"] > best["sma_50"]:
        confidence = 0.58 + min(0.17, diff * 4.0)
        confidence = min(0.78, confidence)
        tp = best["price"] * (1 + abs(tp_pct))
        sl = best["price"] * (1 + sl_pct)
        rr = abs(tp_pct) / abs(sl_pct)
        if rr >= 1.5:
            signals.append({
                "strategy": "duration_rotation",
                "symbol": best_sym,
                "category": "bond",
                "direction": "LONG",
                "signal_type": "BUY",
                "entry_price": round(best["price"], 2),
                "take_profit": round(tp, 2),
                "stop_loss": round(sl, 2),
                "confidence": round(confidence, 3),
                "risk_reward": round(rr, 2),
                "reason": (f"Duration rotation: {best_sym} strongest "
                           f"(ROC20={best['roc_20']*100:+.1f}%) vs "
                           f"{worst_sym} ({worst['roc_20']*100:+.1f}%), "
                           f"RSI={best['rsi']:.0f}"),
                "rsi_at_entry": round(best["rsi"], 1),
                "atr_at_entry": round(best["atr"], 4),
                "max_hold_days": max_hold,
            })

    # SHORT the weakest if it's in a downtrend
    if diff > 0.01 and worst["roc_20"] < 0 and worst["rsi"] > 30 and worst["price"] < worst["sma_50"]:
        confidence = 0.55 + min(0.12, diff * 3.0)
        confidence = min(0.72, confidence)
        tp = worst["price"] * (1 - abs(tp_pct))
        sl = worst["price"] * (1 - sl_pct)
        rr = abs(tp_pct) / abs(sl_pct)
        if rr >= 1.5:
            signals.append({
                "strategy": "duration_rotation",
                "symbol": worst_sym,
                "category": "bond",
                "direction": "SHORT",
                "signal_type": "SELL",
                "entry_price": round(worst["price"], 2),
                "take_profit": round(tp, 2),
                "stop_loss": round(sl, 2),
                "confidence": round(confidence, 3),
                "risk_reward": round(rr, 2),
                "reason": (f"Duration rotation: SHORT {worst_sym} weakest "
                           f"(ROC20={worst['roc_20']*100:+.1f}%), "
                           f"below SMA50, RSI={worst['rsi']:.0f}"),
                "rsi_at_entry": round(worst["rsi"], 1),
                "atr_at_entry": round(worst["atr"], 4),
                "max_hold_days": max_hold,
            })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 12: Futures Momentum
# ---------------------------------------------------------------------------

def futures_momentum(all_data: dict[str, pd.DataFrame]) -> list[dict]:
    """
    Futures Momentum Strategy
    ==========================
    LONG ES/NQ when price is above 20d SMA + volume confirmation (vol > 1.2x avg).
    SHORT when below 20d SMA + volume confirmation.
    Additional filter: ADX > 20 (trending market) and RSI not extreme.

    Edge: Index futures trend strongly in momentum regimes.
    Estimated WR: 55-60% with proper trend/volume filters.
    """
    signals = []
    targets = {
        "ES=F": {"name": "S&P 500 E-mini", "cat": "futures"},
        "NQ=F": {"name": "Nasdaq 100 E-mini", "cat": "futures"},
        "YM=F": {"name": "Dow E-mini", "cat": "futures"},
        "RTY=F": {"name": "Russell 2000 E-mini", "cat": "futures"},
    }

    for sym, info in targets.items():
        df = all_data.get(sym)
        if df is None or len(df) < 50:
            continue

        close = df["Close"]
        volume = df["Volume"]
        price = float(close.iloc[-1])

        sma_20 = float(sma(close, 20).iloc[-1])
        sma_50_val = float(sma(close, 50).iloc[-1])
        rsi_val = float(rsi(close, 14).iloc[-1])
        adx_val = float(adx(df["High"], df["Low"], close, 14).iloc[-1])
        atr_val = float(atr(df["High"], df["Low"], close, 14).iloc[-1])

        # Volume confirmation
        avg_vol = float(volume.iloc[-20:].mean())
        curr_vol = float(volume.iloc[-1])
        vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 0

        if not all(np.isfinite([price, sma_20, sma_50_val, rsi_val,
                                adx_val, atr_val, vol_ratio])):
            continue

        # Need trending market
        if adx_val < 20:
            continue

        sl_pct, tp_pct, max_hold = RISK_PARAMS["futures"]

        # LONG: Price above 20d SMA, volume confirmation, RSI not overbought
        if price > sma_20 and price > sma_50_val and vol_ratio > 1.2 and rsi_val < 70:
            # Stronger signal if well above SMA
            above_pct = (price / sma_20) - 1
            confidence = 0.58 + min(0.17, above_pct * 5.0 + (adx_val - 20) * 0.003)
            confidence = min(0.80, confidence)
            tp = price + 2.5 * atr_val
            sl = price - 1.5 * atr_val
            rr = (tp - price) / (price - sl) if price > sl else 0

            if rr >= 1.5:
                signals.append({
                    "strategy": "futures_momentum",
                    "symbol": sym,
                    "category": "futures",
                    "direction": "LONG",
                    "signal_type": "BUY",
                    "entry_price": round(price, 2),
                    "take_profit": round(tp, 2),
                    "stop_loss": round(sl, 2),
                    "confidence": round(confidence, 3),
                    "risk_reward": round(rr, 2),
                    "reason": (f"Futures momentum: above SMA20 ({sma_20:.0f}) + "
                               f"SMA50 ({sma_50_val:.0f}), vol={vol_ratio:.1f}x, "
                               f"ADX={adx_val:.0f}, RSI={rsi_val:.0f}"),
                    "rsi_at_entry": round(rsi_val, 1),
                    "atr_at_entry": round(atr_val, 2),
                    "max_hold_days": max_hold,
                })

        # SHORT: Price below 20d SMA, volume confirmation, RSI not oversold
        elif price < sma_20 and price < sma_50_val and vol_ratio > 1.2 and rsi_val > 30:
            below_pct = 1 - (price / sma_20)
            confidence = 0.55 + min(0.15, below_pct * 5.0 + (adx_val - 20) * 0.003)
            confidence = min(0.75, confidence)
            tp = price - 2.5 * atr_val
            sl = price + 1.5 * atr_val
            rr = (price - tp) / (sl - price) if sl > price else 0

            if rr >= 1.5:
                signals.append({
                    "strategy": "futures_momentum",
                    "symbol": sym,
                    "category": "futures",
                    "direction": "SHORT",
                    "signal_type": "SELL",
                    "entry_price": round(price, 2),
                    "take_profit": round(tp, 2),
                    "stop_loss": round(sl, 2),
                    "confidence": round(confidence, 3),
                    "risk_reward": round(rr, 2),
                    "reason": (f"Futures momentum: below SMA20 ({sma_20:.0f}) + "
                               f"SMA50 ({sma_50_val:.0f}), vol={vol_ratio:.1f}x, "
                               f"ADX={adx_val:.0f}, RSI={rsi_val:.0f}"),
                    "rsi_at_entry": round(rsi_val, 1),
                    "atr_at_entry": round(atr_val, 2),
                    "max_hold_days": max_hold,
                })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 13: Precious Metals Momentum
# ---------------------------------------------------------------------------

def precious_metals_momentum(all_data: dict[str, pd.DataFrame]) -> list[dict]:
    """
    Precious Metals Momentum
    =========================
    Rank GLD, SLV, PPLT (ETFs -- more liquid than futures) by 20-day momentum.
    LONG the strongest, SHORT the weakest if both trending (ADX > 20).
    Can also use GC=F, SI=F as substitutes.

    Edge: Precious metals trend for extended periods due to macro drivers
    (inflation, USD weakness, geopolitical risk).
    Estimated WR: 55-60%.
    """
    signals = []
    # Prefer ETFs for liquidity; fall back to futures
    pm_map = {
        "GLD": "GC=F", "SLV": "SI=F", "PPLT": None,
    }

    scores = []
    for etf_sym, fut_sym in pm_map.items():
        sym = etf_sym
        df = all_data.get(etf_sym)
        if df is None or len(df) < 50:
            if fut_sym:
                df = all_data.get(fut_sym)
                sym = fut_sym
            if df is None or len(df) < 50:
                continue

        close = df["Close"]
        price = float(close.iloc[-1])
        roc_20 = float((close.iloc[-1] / close.iloc[-21]) - 1)
        rsi_val = float(rsi(close, 14).iloc[-1])
        adx_val = float(adx(df["High"], df["Low"], close, 14).iloc[-1])
        atr_val = float(atr(df["High"], df["Low"], close, 14).iloc[-1])
        sma_50_val = float(sma(close, 50).iloc[-1])

        if not all(np.isfinite([price, roc_20, rsi_val, adx_val, atr_val, sma_50_val])):
            continue

        cat = "commodity" if sym.endswith("=F") else "etf"
        scores.append({
            "symbol": sym, "cat": cat, "price": price,
            "roc_20": roc_20, "rsi": rsi_val, "adx": adx_val,
            "atr": atr_val, "sma_50": sma_50_val,
        })

    if len(scores) < 2:
        return signals

    # Rank by momentum
    scores.sort(key=lambda x: x["roc_20"], reverse=True)
    best = scores[0]
    worst = scores[-1]

    sl_pct, tp_pct, max_hold = RISK_PARAMS.get("commodity", (-0.04, 0.08, 10))

    # LONG strongest if trending up
    if (best["roc_20"] > 0.01 and best["adx"] > 20 and
            best["rsi"] < 72 and best["price"] > best["sma_50"]):
        confidence = 0.58 + min(0.17, best["roc_20"] * 5.0)
        confidence = min(0.80, confidence)
        tp = best["price"] + 2.5 * best["atr"]
        sl = best["price"] - 1.5 * best["atr"]
        rr = (tp - best["price"]) / (best["price"] - sl) if best["price"] > sl else 0
        if rr >= 1.5:
            signals.append({
                "strategy": "precious_metals_momentum",
                "symbol": best["symbol"],
                "category": best["cat"],
                "direction": "LONG",
                "signal_type": "BUY",
                "entry_price": round(best["price"], 2),
                "take_profit": round(tp, 2),
                "stop_loss": round(sl, 2),
                "confidence": round(confidence, 3),
                "risk_reward": round(rr, 2),
                "reason": (f"PM momentum leader: ROC20={best['roc_20']*100:+.1f}%, "
                           f"ADX={best['adx']:.0f}, RSI={best['rsi']:.0f}"),
                "rsi_at_entry": round(best["rsi"], 1),
                "atr_at_entry": round(best["atr"], 4),
                "max_hold_days": max_hold,
            })

    # SHORT weakest if trending down
    if (worst["roc_20"] < -0.01 and worst["adx"] > 20 and
            worst["rsi"] > 28 and worst["price"] < worst["sma_50"]):
        confidence = 0.55 + min(0.12, abs(worst["roc_20"]) * 4.0)
        confidence = min(0.72, confidence)
        tp = worst["price"] - 2.5 * worst["atr"]
        sl = worst["price"] + 1.5 * worst["atr"]
        rr = (worst["price"] - tp) / (sl - worst["price"]) if sl > worst["price"] else 0
        if rr >= 1.5:
            signals.append({
                "strategy": "precious_metals_momentum",
                "symbol": worst["symbol"],
                "category": worst["cat"],
                "direction": "SHORT",
                "signal_type": "SELL",
                "entry_price": round(worst["price"], 2),
                "take_profit": round(tp, 2),
                "stop_loss": round(sl, 2),
                "confidence": round(confidence, 3),
                "risk_reward": round(rr, 2),
                "reason": (f"PM momentum laggard: ROC20={worst['roc_20']*100:+.1f}%, "
                           f"ADX={worst['adx']:.0f}, RSI={worst['rsi']:.0f}"),
                "rsi_at_entry": round(worst["rsi"], 1),
                "atr_at_entry": round(worst["atr"], 4),
                "max_hold_days": max_hold,
            })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 14: Energy Sector Rotation
# ---------------------------------------------------------------------------

def energy_sector_rotation(all_data: dict[str, pd.DataFrame]) -> list[dict]:
    """
    Energy Sector Rotation
    =======================
    Rotate between XLE (energy sector ETF), USO (crude oil ETF), and
    UNG (natural gas ETF) based on relative strength.
    LONG the strongest, SHORT the weakest.

    Edge: Energy sub-sectors diverge significantly due to different
    supply/demand dynamics (oil vs gas vs integrated).
    Estimated WR: 55-60%.
    """
    signals = []
    energy_symbols = {
        "XLE": {"name": "Energy Sector", "cat": "etf"},
        "USO": {"name": "US Oil Fund", "cat": "etf"},
        "UNG": {"name": "US Natural Gas", "cat": "etf"},
        "CL=F": {"name": "WTI Crude", "cat": "commodity"},
        "NG=F": {"name": "Natural Gas", "cat": "commodity"},
    }

    scores = []
    for sym, info in energy_symbols.items():
        df = all_data.get(sym)
        if df is None or len(df) < 50:
            continue

        close = df["Close"]
        price = float(close.iloc[-1])
        roc_20 = float((close.iloc[-1] / close.iloc[-21]) - 1)
        rsi_val = float(rsi(close, 14).iloc[-1])
        adx_val = float(adx(df["High"], df["Low"], close, 14).iloc[-1])
        atr_val = float(atr(df["High"], df["Low"], close, 14).iloc[-1])
        sma_50_val = float(sma(close, 50).iloc[-1])

        if not all(np.isfinite([price, roc_20, rsi_val, adx_val, atr_val, sma_50_val])):
            continue

        scores.append({
            "symbol": sym, "cat": info["cat"], "price": price,
            "roc_20": roc_20, "rsi": rsi_val, "adx": adx_val,
            "atr": atr_val, "sma_50": sma_50_val,
        })

    if len(scores) < 2:
        return signals

    # Rank by 20d momentum
    scores.sort(key=lambda x: x["roc_20"], reverse=True)
    best = scores[0]
    worst = scores[-1]
    diff = best["roc_20"] - worst["roc_20"]

    if diff < 0.02:
        return signals  # Not enough divergence

    sl_pct, tp_pct, max_hold = RISK_PARAMS.get("commodity", (-0.04, 0.08, 10))

    # LONG the strongest energy asset
    if best["roc_20"] > 0 and best["adx"] > 18 and best["rsi"] < 72 and best["price"] > best["sma_50"]:
        confidence = 0.58 + min(0.15, diff * 3.0)
        confidence = min(0.78, confidence)
        tp = best["price"] + 2.5 * best["atr"]
        sl = best["price"] - 1.5 * best["atr"]
        rr = (tp - best["price"]) / (best["price"] - sl) if best["price"] > sl else 0
        if rr >= 1.5:
            signals.append({
                "strategy": "energy_sector_rotation",
                "symbol": best["symbol"],
                "category": best["cat"],
                "direction": "LONG",
                "signal_type": "BUY",
                "entry_price": round(best["price"], 2),
                "take_profit": round(tp, 2),
                "stop_loss": round(sl, 2),
                "confidence": round(confidence, 3),
                "risk_reward": round(rr, 2),
                "reason": (f"Energy rotation leader: {best['symbol']} "
                           f"ROC20={best['roc_20']*100:+.1f}%, "
                           f"ADX={best['adx']:.0f}, spread={diff*100:.1f}%"),
                "rsi_at_entry": round(best["rsi"], 1),
                "atr_at_entry": round(best["atr"], 4),
                "max_hold_days": max_hold,
            })

    # SHORT the weakest energy asset
    if worst["roc_20"] < 0 and worst["adx"] > 18 and worst["rsi"] > 28 and worst["price"] < worst["sma_50"]:
        confidence = 0.55 + min(0.12, diff * 2.5)
        confidence = min(0.72, confidence)
        tp = worst["price"] - 2.5 * worst["atr"]
        sl = worst["price"] + 1.5 * worst["atr"]
        rr = (worst["price"] - tp) / (sl - worst["price"]) if sl > worst["price"] else 0
        if rr >= 1.5:
            signals.append({
                "strategy": "energy_sector_rotation",
                "symbol": worst["symbol"],
                "category": worst["cat"],
                "direction": "SHORT",
                "signal_type": "SELL",
                "entry_price": round(worst["price"], 2),
                "take_profit": round(tp, 2),
                "stop_loss": round(sl, 2),
                "confidence": round(confidence, 3),
                "risk_reward": round(rr, 2),
                "reason": (f"Energy rotation laggard: {worst['symbol']} "
                           f"ROC20={worst['roc_20']*100:+.1f}%, "
                           f"ADX={worst['adx']:.0f}, spread={diff*100:.1f}%"),
                "rsi_at_entry": round(worst["rsi"], 1),
                "atr_at_entry": round(worst["atr"], 4),
                "max_hold_days": max_hold,
            })

    return signals


# ---------------------------------------------------------------------------
# Strategy registry — for integration with scanner.py
# ---------------------------------------------------------------------------
# Per-symbol strategies (called once per symbol)
COMMODITY_STRATEGIES = {
    "commodity_seasonality": commodity_seasonality,
    # KILLED 2026-04-12: crude_oil_mean_reversion — PF 0.94, -30.4% return.
    # XLE worked via etf_relative_strength; raw CL=F/NG=F did not. NG=F toxic.
    # Function retained for backtest use; removed from live registry.
    # See multi_asset/FOCUSED_NONCRYPTO_BACKTEST_REPORT_2026-04-07.md.
    # "crude_oil_mean_reversion": crude_oil_mean_reversion,
    # KILLED 2026-04-12: equity_index_gap_reversion — 53.1% WR but PF 0.87,
    # -55.4% return on 693 trades. Largest negative contributor in non-crypto
    # backtest (payoff shape inverted). Function retained for backtest use.
    # "equity_index_gap_reversion": equity_index_gap_reversion,
    "commodity_bollinger_squeeze": commodity_bollinger_squeeze,
}

# VIX-dependent strategies (need extra data)
COMMODITY_VIX_STRATEGIES = {
    "gold_safe_haven": gold_safe_haven,
}

# Cross-asset strategies (need ALL data, called once per scan cycle)
COMMODITY_CROSS_STRATEGIES = {
    "commodity_momentum": commodity_momentum,
    "bond_equity_rotation": bond_equity_rotation,
    "dr_copper_indicator": dr_copper_indicator,
    "treasury_yield_curve": treasury_yield_curve,
    "credit_spread": credit_spread_strategy,
    "duration_rotation": duration_rotation,
    "futures_momentum": futures_momentum,
    "precious_metals_momentum": precious_metals_momentum,
    "energy_sector_rotation": energy_sector_rotation,
    **( {"energy_eia_inventory_proxy": _eia_proxy} if _EIA_AVAILABLE else {} ),
}


# ---------------------------------------------------------------------------
# Standalone backtest runner
# ---------------------------------------------------------------------------

def _yf_download(tickers: list[str], period: str = "1y") -> dict[str, pd.DataFrame]:
    """Download data for multiple tickers with retry."""
    result = {}
    for ticker in tickers:
        for attempt in range(3):
            try:
                df = yf.download(ticker, period=period, interval="1d",
                                 progress=False, auto_adjust=True)
                if df is not None and not df.empty:
                    # Handle MultiIndex columns from yfinance
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    result[ticker] = df
                    break
            except Exception:
                if attempt == 2:
                    print(f"  WARN: Failed to download {ticker} after 3 attempts")
    return result


def backtest_strategy(strategy_fn, df: pd.DataFrame, symbol: str, info: dict,
                      lookback_days: int = 252) -> list[dict]:
    """
    Walk-forward backtest: simulate strategy over historical bars.
    Returns list of closed trades with PnL.
    """
    trades = []
    if len(df) < lookback_days:
        lookback_days = len(df) - 50  # Use what we have
    if lookback_days < 50:
        return trades

    start_idx = len(df) - lookback_days

    for i in range(start_idx, len(df) - 5):
        # Simulate the strategy seeing only data up to bar i
        window = df.iloc[:i + 1].copy()
        try:
            signals = strategy_fn(window, symbol, info)
        except Exception:
            continue

        for sig in signals:
            entry_price = sig["entry_price"]
            tp = sig.get("take_profit", entry_price * 1.05)
            sl = sig.get("stop_loss", entry_price * 0.97)
            direction = sig["direction"]
            max_hold = sig.get("max_hold_days", 10)

            # Simulate forward from entry
            for j in range(i + 1, min(i + 1 + max_hold, len(df))):
                bar_high = float(df["High"].iloc[j])
                bar_low = float(df["Low"].iloc[j])
                bar_close = float(df["Close"].iloc[j])

                if direction == "LONG":
                    # Check stop loss first (conservative)
                    if bar_low <= sl:
                        pnl = (sl / entry_price) - 1
                        trades.append({**sig, "pnl_pct": pnl, "exit_reason": "STOP_LOSS",
                                       "hold_days": j - i, "status": "LOST"})
                        break
                    # Check take profit
                    if bar_high >= tp:
                        pnl = (tp / entry_price) - 1
                        trades.append({**sig, "pnl_pct": pnl, "exit_reason": "TAKE_PROFIT",
                                       "hold_days": j - i, "status": "WON"})
                        break
                else:  # SHORT
                    if bar_high >= sl:
                        pnl = 1 - (sl / entry_price)
                        trades.append({**sig, "pnl_pct": pnl, "exit_reason": "STOP_LOSS",
                                       "hold_days": j - i, "status": "LOST"})
                        break
                    if bar_low <= tp:
                        pnl = 1 - (tp / entry_price)
                        trades.append({**sig, "pnl_pct": pnl, "exit_reason": "TAKE_PROFIT",
                                       "hold_days": j - i, "status": "WON"})
                        break
            else:
                # Expired: close at last bar
                exit_price = float(df["Close"].iloc[min(i + max_hold, len(df) - 1)])
                if direction == "LONG":
                    pnl = (exit_price / entry_price) - 1
                else:
                    pnl = 1 - (exit_price / entry_price)
                trades.append({**sig, "pnl_pct": pnl, "exit_reason": "EXPIRED",
                               "exit_price": exit_price,
                               "hold_days": max_hold, "status": "WON" if pnl > 0 else "LOST"})

    return trades


def run_backtest():
    """Run backtest on all commodity/futures strategies."""
    print("=" * 70)
    print("COMMODITY & FUTURES STRATEGIES — BACKTEST")
    print("=" * 70)

    # Download data
    all_tickers = list(ALL_CF_SYMBOLS.keys()) + ["SPY", "TLT", "^VIX",
                                                  "XLE", "XLF", "QQQ",
                                                  "CORN", "WEAT", "SOYB", "USO"]
    print(f"\nDownloading data for {len(all_tickers)} tickers...")
    data = _yf_download(all_tickers, period="2y")
    print(f"  Got data for {len(data)} tickers")

    results = {}

    # Test per-symbol strategies
    print("\n--- Per-Symbol Strategies ---")
    for strat_name, strat_fn in COMMODITY_STRATEGIES.items():
        all_trades = []
        for sym, info in {**COMMODITY_SYMBOLS, **FUTURES_SYMBOLS}.items():
            df = data.get(sym)
            if df is None or len(df) < 50:
                continue
            trades = backtest_strategy(strat_fn, df, sym, info)
            all_trades.extend(trades)

        if all_trades:
            wins = sum(1 for t in all_trades if t["status"] == "WON")
            total = len(all_trades)
            wr = wins / total if total > 0 else 0
            avg_pnl = sum(t["pnl_pct"] for t in all_trades) / total if total > 0 else 0
            results[strat_name] = {"wins": wins, "total": total, "wr": wr, "avg_pnl": avg_pnl}
            print(f"  {strat_name}: {wins}/{total} = {wr*100:.1f}% WR, "
                  f"avg PnL = {avg_pnl*100:+.2f}%")
        else:
            print(f"  {strat_name}: No trades generated")

    # Test gold safe haven (needs VIX + SPY)
    print("\n--- VIX-Dependent Strategies ---")
    vix_data = data.get("^VIX")
    spy_data = data.get("SPY")
    for sym in ["GC=F", "GLD", "SI=F"]:
        df = data.get(sym)
        if df is None:
            continue
        info = ALL_CF_SYMBOLS.get(sym, {"name": sym, "cat": "commodity"})
        trades = []
        # Walk forward
        for i in range(100, len(df) - 5):
            window = df.iloc[:i + 1]
            vix_w = vix_data.iloc[:i + 1] if vix_data is not None else None
            spy_w = spy_data.iloc[:i + 1] if spy_data is not None else None
            try:
                sigs = gold_safe_haven(window, sym, info, vix_data=vix_w, spy_data=spy_w)
                for sig in sigs:
                    entry = sig["entry_price"]
                    tp = sig.get("take_profit", entry * 1.10)
                    sl = sig.get("stop_loss", entry * 0.97)
                    mh = sig.get("max_hold_days", 15)
                    for j in range(i + 1, min(i + 1 + mh, len(df))):
                        h = float(df["High"].iloc[j])
                        lo = float(df["Low"].iloc[j])
                        if lo <= sl:
                            trades.append({**sig, "pnl_pct": (sl / entry) - 1,
                                           "status": "LOST", "exit_reason": "STOP_LOSS"})
                            break
                        if h >= tp:
                            trades.append({**sig, "pnl_pct": (tp / entry) - 1,
                                           "status": "WON", "exit_reason": "TAKE_PROFIT"})
                            break
                    else:
                        ep = float(df["Close"].iloc[min(i + mh, len(df) - 1)])
                        pnl = (ep / entry) - 1
                        trades.append({**sig, "pnl_pct": pnl,
                                       "status": "WON" if pnl > 0 else "LOST",
                                       "exit_reason": "EXPIRED"})
            except Exception:
                continue

        if trades:
            wins = sum(1 for t in trades if t["status"] == "WON")
            total = len(trades)
            wr = wins / total if total > 0 else 0
            avg_pnl = sum(t["pnl_pct"] for t in trades) / total
            print(f"  gold_safe_haven ({sym}): {wins}/{total} = {wr*100:.1f}% WR, "
                  f"avg PnL = {avg_pnl*100:+.2f}%")

    # Summary
    print("\n" + "=" * 70)
    print("BACKTEST SUMMARY")
    print("=" * 70)
    for name, r in results.items():
        status = "PASS" if r["wr"] >= 0.50 and r["avg_pnl"] > 0 else "REVIEW"
        print(f"  [{status}] {name}: {r['wr']*100:.1f}% WR, {r['avg_pnl']*100:+.2f}% avg PnL "
              f"({r['total']} trades)")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Commodity & Futures Strategies")
    parser.add_argument("--backtest", action="store_true", help="Run historical backtest")
    parser.add_argument("--scan", action="store_true", help="Run live scan")
    args = parser.parse_args()

    if args.backtest:
        run_backtest()
    elif args.scan:
        print("Scanning commodity/futures strategies...")
        tickers = list(ALL_CF_SYMBOLS.keys()) + ["SPY", "TLT", "^VIX", "USO",
                                                   "XLE", "XLF", "QQQ",
                                                   "CORN", "WEAT", "SOYB"]
        data = _yf_download(tickers, period="1y")
        vix_data = data.get("^VIX")
        spy_data = data.get("SPY")
        copper_data = data.get("HG=F")

        all_signals = []

        # Per-symbol strategies
        for sym, info in ALL_CF_SYMBOLS.items():
            df = data.get(sym)
            if df is None:
                continue
            for strat_name, strat_fn in COMMODITY_STRATEGIES.items():
                try:
                    sigs = strat_fn(df, sym, info)
                    all_signals.extend(sigs)
                except Exception as e:
                    print(f"  ERROR: {strat_name} on {sym}: {e}")

            # Gold safe haven
            try:
                sigs = gold_safe_haven(df, sym, info, vix_data=vix_data, spy_data=spy_data)
                all_signals.extend(sigs)
            except Exception as e:
                print(f"  ERROR: gold_safe_haven on {sym}: {e}")

            # Dr. Copper
            try:
                sigs = dr_copper_indicator(df, sym, info, copper_data=copper_data)
                all_signals.extend(sigs)
            except Exception as e:
                print(f"  ERROR: dr_copper on {sym}: {e}")

        # Cross-asset strategies
        try:
            all_signals.extend(commodity_momentum(data))
        except Exception as e:
            print(f"  ERROR: commodity_momentum: {e}")

        try:
            all_signals.extend(bond_equity_rotation(data))
        except Exception as e:
            print(f"  ERROR: bond_equity_rotation: {e}")

        print(f"\n=== Total signals: {len(all_signals)} ===")
        for sig in all_signals:
            print(f"  {sig['strategy']:30s} {sig['symbol']:8s} {sig['direction']:5s} "
                  f"conf={sig['confidence']:.2f} | {sig['reason']}")
    else:
        parser.print_help()
