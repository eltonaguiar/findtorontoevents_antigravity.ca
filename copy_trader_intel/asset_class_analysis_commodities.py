#!/usr/bin/env python3
"""
Commodity Asset Class Pattern Analyzer
========================================
Fetches 2y daily OHLCV for 12 commodities + 4 index futures from yfinance,
computes commodity-specific technical features, identifies per-symbol best
strategies, corrects too-wide TP/SL, generates strategy variations, and
backtests each variation.

Outputs:
  - data/commodity_asset_analysis.json   (per-symbol stats & features)
  - data/commodity_strategy_variations.json (per-symbol variations with proper TP/SL)
  - data/commodity_ml_picks.json         (current picks with corrected TP/SL)

source_system = "ml_commodity_reverser"
"""

import sys
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

import json
import time
import warnings
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Symbol universe
# ---------------------------------------------------------------------------
COMMODITY_SYMBOLS = {
    # Energy
    "CL=F": {"name": "Crude Oil WTI", "sector": "energy", "seasonal_strong": [1, 2, 3, 6, 7], "seasonal_weak": [9, 10, 11]},
    "BZ=F": {"name": "Brent Crude", "sector": "energy", "seasonal_strong": [1, 2, 3, 6, 7], "seasonal_weak": [9, 10, 11]},
    "NG=F": {"name": "Natural Gas", "sector": "energy", "seasonal_strong": [10, 11, 12, 1, 2], "seasonal_weak": [4, 5, 6]},
    "HO=F": {"name": "Heating Oil", "sector": "energy", "seasonal_strong": [10, 11, 12, 1], "seasonal_weak": [5, 6, 7]},
    "RB=F": {"name": "RBOB Gasoline", "sector": "energy", "seasonal_strong": [3, 4, 5, 6], "seasonal_weak": [10, 11, 12]},
    # Precious Metals
    "GC=F": {"name": "Gold", "sector": "precious_metals", "seasonal_strong": [1, 2, 8, 9], "seasonal_weak": [3, 6]},
    "SI=F": {"name": "Silver", "sector": "precious_metals", "seasonal_strong": [1, 2, 7, 8], "seasonal_weak": [3, 6]},
    "PL=F": {"name": "Platinum", "sector": "precious_metals", "seasonal_strong": [1, 4, 7], "seasonal_weak": [9, 10]},
    "PA=F": {"name": "Palladium", "sector": "precious_metals", "seasonal_strong": [1, 4, 7], "seasonal_weak": [9, 10]},
    # Base Metals
    "HG=F": {"name": "Copper", "sector": "base_metals", "seasonal_strong": [1, 2, 3, 4], "seasonal_weak": [6, 10]},
    # Agriculture
    "ZC=F": {"name": "Corn", "sector": "agriculture", "seasonal_strong": [3, 4, 5, 6], "seasonal_weak": [9, 10, 11]},
    "ZW=F": {"name": "Wheat", "sector": "agriculture", "seasonal_strong": [3, 4, 5, 6], "seasonal_weak": [9, 10, 11]},
    "ZS=F": {"name": "Soybeans", "sector": "agriculture", "seasonal_strong": [3, 4, 5, 6, 7], "seasonal_weak": [9, 10]},
    "ZM=F": {"name": "Soybean Meal", "sector": "agriculture", "seasonal_strong": [10, 11, 12, 1, 2], "seasonal_weak": [6, 7]},
    "ZL=F": {"name": "Soybean Oil", "sector": "agriculture", "seasonal_strong": [10, 11, 12, 1, 2], "seasonal_weak": [6, 7]},
    # Softs
    "KC=F": {"name": "Coffee", "sector": "softs", "seasonal_strong": [5, 6, 7], "seasonal_weak": [11, 12]},
    "SB=F": {"name": "Sugar", "sector": "softs", "seasonal_strong": [2, 3, 4], "seasonal_weak": [7, 8]},
    "CC=F": {"name": "Cocoa", "sector": "softs", "seasonal_strong": [10, 11, 12], "seasonal_weak": [5, 6]},
    "OJ=F": {"name": "Orange Juice", "sector": "softs", "seasonal_strong": [11, 12, 1], "seasonal_weak": [5, 6, 7]},
    # Livestock
    "LE=F": {"name": "Live Cattle", "sector": "livestock", "seasonal_strong": [2, 3, 4], "seasonal_weak": [9, 10]},
    "GF=F": {"name": "Feeder Cattle", "sector": "livestock", "seasonal_strong": [2, 3, 4], "seasonal_weak": [9, 10]},
    "HE=F": {"name": "Lean Hogs", "sector": "livestock", "seasonal_strong": [4, 5, 6], "seasonal_weak": [10, 11]},
}

INDEX_FUTURES_SYMBOLS = {
    "ES=F": {"name": "S&P 500 E-mini", "sector": "equity_index"},
    "NQ=F": {"name": "Nasdaq 100 E-mini", "sector": "equity_index"},
    "YM=F": {"name": "Dow Jones E-mini", "sector": "equity_index"},
    "RTY=F": {"name": "Russell 2000 E-mini", "sector": "equity_index"},
}

ALL_SYMBOLS = {**COMMODITY_SYMBOLS, **INDEX_FUTURES_SYMBOLS}

# ---------------------------------------------------------------------------
# TP/SL caps per commodity (max TP % allowed)
# ---------------------------------------------------------------------------
TP_CAPS = {
    "GC=F": 5.0, "SI=F": 8.0, "PL=F": 8.0, "PA=F": 8.0, "HG=F": 8.0,
    "CL=F": 8.0, "BZ=F": 8.0, "NG=F": 12.0, "HO=F": 8.0, "RB=F": 8.0,
    "ZC=F": 6.0, "ZW=F": 6.0, "ZS=F": 6.0, "ZM=F": 6.0, "ZL=F": 6.0,
    "KC=F": 10.0, "SB=F": 8.0, "CC=F": 10.0, "OJ=F": 10.0,
    "LE=F": 6.0, "GF=F": 6.0, "HE=F": 6.0,
    "ES=F": 4.0, "NQ=F": 5.0, "YM=F": 4.0, "RTY=F": 5.0,
}

SL_CAPS = {
    "GC=F": 3.0, "SI=F": 5.0, "PL=F": 5.0, "PA=F": 5.0, "HG=F": 5.0,
    "CL=F": 5.0, "BZ=F": 5.0, "NG=F": 8.0, "HO=F": 5.0, "RB=F": 5.0,
    "ZC=F": 4.0, "ZW=F": 4.0, "ZS=F": 4.0, "ZM=F": 4.0, "ZL=F": 4.0,
    "KC=F": 6.0, "SB=F": 5.0, "CC=F": 6.0, "OJ=F": 6.0,
    "LE=F": 4.0, "GF=F": 4.0, "HE=F": 4.0,
    "ES=F": 2.5, "NQ=F": 3.0, "YM=F": 2.5, "RTY=F": 3.0,
}


# ---------------------------------------------------------------------------
# Data fetching with rate limiting
# ---------------------------------------------------------------------------
def fetch_ohlcv(symbol: str, period: str = "2y") -> pd.DataFrame:
    """Fetch daily OHLCV from yfinance with rate limiting."""
    try:
        import yfinance as yf
        time.sleep(0.5)  # rate limit
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval="1d")
        if df.empty:
            print(f"  [WARN] No data for {symbol}")
            return pd.DataFrame()
        # Standardize columns
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low",
                                "Close": "close", "Volume": "volume"})
        df.index = pd.to_datetime(df.index)
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        return df[["open", "high", "low", "close", "volume"]]
    except Exception as e:
        print(f"  [ERROR] Failed to fetch {symbol}: {e}")
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Technical indicators
# ---------------------------------------------------------------------------
def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def compute_bollinger(close: pd.Series, period: int = 20, num_std: float = 2.0):
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    pct_b = (close - lower) / (upper - lower).replace(0, np.nan)
    return mid, upper, lower, pct_b


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def compute_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1.0 / period, min_periods=period).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1.0 / period, min_periods=period).mean() / atr.replace(0, np.nan))
    minus_di = 100 * (minus_dm.ewm(alpha=1.0 / period, min_periods=period).mean() / atr.replace(0, np.nan))
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    return dx.ewm(alpha=1.0 / period, min_periods=period).mean()


# ---------------------------------------------------------------------------
# Feature computation per symbol
# ---------------------------------------------------------------------------
def compute_features(symbol: str, df: pd.DataFrame) -> dict:
    """Compute all commodity-specific features for the latest bar."""
    if df.empty or len(df) < 252:
        return {}

    close = df["close"]
    latest = close.iloc[-1]

    # RSI
    rsi14 = compute_rsi(close, 14).iloc[-1]
    rsi2 = compute_rsi(close, 2).iloc[-1]

    # Bollinger %B
    _, _, _, pct_b = compute_bollinger(close, 20, 2.0)
    bb_pct_b = pct_b.iloc[-1]

    # ATR as % of price
    atr_series = compute_atr(df, 14)
    atr_val = atr_series.iloc[-1]
    atr_pct = (atr_val / latest) * 100 if latest > 0 else 0.0

    # Momentum
    mom_20d = (latest / close.iloc[-21] - 1) * 100 if len(close) > 21 else 0.0
    mom_60d = (latest / close.iloc[-61] - 1) * 100 if len(close) > 61 else 0.0
    mom_252d = (latest / close.iloc[-253] - 1) * 100 if len(close) > 253 else 0.0

    # Volume ratio
    vol = df["volume"]
    vol_avg_20 = vol.rolling(20).mean().iloc[-1]
    vol_ratio = vol.iloc[-1] / vol_avg_20 if vol_avg_20 > 0 else 1.0

    # Seasonal month
    current_month = df.index[-1].month
    meta = ALL_SYMBOLS.get(symbol, {})
    seasonal_strong = meta.get("seasonal_strong", [])
    seasonal_weak = meta.get("seasonal_weak", [])
    if current_month in seasonal_strong:
        seasonal_signal = "bullish"
    elif current_month in seasonal_weak:
        seasonal_signal = "bearish"
    else:
        seasonal_signal = "neutral"

    # Distance from 52-week high/low
    high_252 = df["high"].rolling(252).max().iloc[-1]
    low_252 = df["low"].rolling(252).min().iloc[-1]
    dist_from_high = ((latest - high_252) / high_252) * 100 if high_252 > 0 else 0.0
    dist_from_low = ((latest - low_252) / low_252) * 100 if low_252 > 0 else 0.0

    # ADX
    adx_val = compute_adx(df, 14).iloc[-1]

    return {
        "symbol": symbol,
        "name": meta.get("name", symbol),
        "sector": meta.get("sector", "unknown"),
        "latest_price": round(float(latest), 4),
        "rsi14": round(float(rsi14), 2) if not np.isnan(rsi14) else None,
        "rsi2": round(float(rsi2), 2) if not np.isnan(rsi2) else None,
        "bb_pct_b": round(float(bb_pct_b), 4) if not np.isnan(bb_pct_b) else None,
        "atr": round(float(atr_val), 4),
        "atr_pct": round(float(atr_pct), 3),
        "momentum_20d": round(float(mom_20d), 3),
        "momentum_60d": round(float(mom_60d), 3),
        "momentum_252d": round(float(mom_252d), 3),
        "volume_ratio": round(float(vol_ratio), 3),
        "current_month": current_month,
        "seasonal_signal": seasonal_signal,
        "dist_from_52w_high_pct": round(float(dist_from_high), 3),
        "dist_from_52w_low_pct": round(float(dist_from_low), 3),
        "adx": round(float(adx_val), 2) if not np.isnan(adx_val) else None,
        "data_bars": len(df),
    }


def compute_cross_ratios(price_data: dict) -> dict:
    """Compute cross-commodity ratios."""
    ratios = {}
    gc = price_data.get("GC=F")
    si = price_data.get("SI=F")
    cl = price_data.get("CL=F")
    zc = price_data.get("ZC=F")
    zw = price_data.get("ZW=F")

    if gc is not None and si is not None and not gc.empty and not si.empty:
        gc_price = gc["close"].iloc[-1]
        si_price = si["close"].iloc[-1]
        if si_price > 0:
            ratios["gold_silver_ratio"] = round(float(gc_price / si_price), 3)
            # Historical mean ~65-70. Above 80 = silver undervalued, below 60 = gold undervalued
            r = gc_price / si_price
            ratios["gold_silver_signal"] = "silver_undervalued" if r > 80 else ("gold_undervalued" if r < 60 else "neutral")

    if cl is not None and gc is not None and not cl.empty and not gc.empty:
        cl_price = cl["close"].iloc[-1]
        gc_price = gc["close"].iloc[-1]
        if gc_price > 0:
            ratios["oil_gold_ratio"] = round(float(cl_price / gc_price) * 100, 4)  # barrels per oz * 100

    if zc is not None and zw is not None and not zc.empty and not zw.empty:
        zc_price = zc["close"].iloc[-1]
        zw_price = zw["close"].iloc[-1]
        if zw_price > 0:
            ratios["corn_wheat_ratio"] = round(float(zc_price / zw_price), 4)
            # Historically corn/wheat ~ 0.7-0.85. Below 0.7 = corn cheap vs wheat
            r = zc_price / zw_price
            ratios["corn_wheat_signal"] = "corn_cheap" if r < 0.70 else ("wheat_cheap" if r > 0.90 else "neutral")

    return ratios


# ---------------------------------------------------------------------------
# Per-symbol strategy affinity
# ---------------------------------------------------------------------------
STRATEGY_AFFINITIES = {
    "GC=F": {
        "best_strategies": ["mean_reversion", "safe_haven_dxy", "seasonal"],
        "notes": "Gold mean-reverts well on RSI extremes; rallies when DXY weakens; strong Jan/Feb/Aug/Sep seasonal",
    },
    "CL=F": {
        "best_strategies": ["momentum_breakout", "volume_confirmation", "seasonal"],
        "notes": "Oil trends strongly; momentum with volume confirmation; seasonal summer driving demand",
    },
    "NG=F": {
        "best_strategies": ["seasonal_winter", "volatility_expansion", "mean_reversion"],
        "notes": "NatGas highly seasonal (winter demand); volatile with mean reversion at extremes; max TP 12%",
    },
    "ZC=F": {
        "best_strategies": ["seasonal_planting", "agricultural_spread", "momentum"],
        "notes": "Corn seasonal around planting (Mar-Jun); spread trades with wheat; CFTC COT signals",
    },
    "ZW=F": {
        "best_strategies": ["seasonal_planting", "agricultural_spread", "momentum"],
        "notes": "Wheat similar to corn; weather premium in spring; spread vs corn",
    },
    "ZS=F": {
        "best_strategies": ["seasonal_planting", "momentum", "mean_reversion"],
        "notes": "Soybeans: planting season rally Mar-Jul; crush spread; China demand driven",
    },
    "SI=F": {
        "best_strategies": ["gold_correlation", "industrial_demand", "mean_reversion"],
        "notes": "Silver correlates with gold but more volatile; industrial demand component; gold/silver ratio trades",
    },
    "HG=F": {
        "best_strategies": ["economic_cycle", "momentum", "mean_reversion"],
        "notes": "Copper as economic bellwether; momentum during expansion; mean reversion at extremes",
    },
    "PL=F": {
        "best_strategies": ["gold_correlation", "automotive_demand", "mean_reversion"],
        "notes": "Platinum: auto catalyst demand; gold/platinum spread; mean reversion",
    },
    "KC=F": {
        "best_strategies": ["seasonal", "supply_shock", "momentum"],
        "notes": "Coffee: Brazilian harvest cycle; frost/drought supply shocks; May-Jul seasonal",
    },
    "SB=F": {
        "best_strategies": ["seasonal", "ethanol_correlation", "mean_reversion"],
        "notes": "Sugar: Feb-Apr seasonal; ethanol blend demand; mean reversion on RSI extremes",
    },
    "HO=F": {
        "best_strategies": ["seasonal_winter", "crack_spread", "momentum"],
        "notes": "Heating oil: winter demand Oct-Jan; crack spread with crude; momentum trends",
    },
    "ES=F": {
        "best_strategies": ["mean_reversion", "bollinger_breakout", "momentum"],
        "notes": "S&P 500: strong mean reversion on RSI(2); BB breakout 87.5% WR; tight TP/SL",
    },
    "NQ=F": {
        "best_strategies": ["momentum", "mean_reversion", "bollinger_breakout"],
        "notes": "Nasdaq: momentum leader; mean reversion at extremes; more volatile than ES",
    },
    "YM=F": {
        "best_strategies": ["mean_reversion", "value_rotation", "bollinger_breakout"],
        "notes": "Dow: value/defensive rotation; mean reversion; lower volatility than NQ",
    },
    "RTY=F": {
        "best_strategies": ["momentum", "risk_on_off", "mean_reversion"],
        "notes": "Russell 2000: risk-on/off barometer; momentum in expansions; mean reversion sharp",
    },
}


# ---------------------------------------------------------------------------
# TP/SL correction
# ---------------------------------------------------------------------------
def correct_tp_sl(picks: list, atr_data: dict) -> list:
    """Fix too-wide TP/SL based on actual ATR and per-commodity caps."""
    corrected = []
    for pick in picks:
        p = dict(pick)
        sym = p.get("symbol", "")
        entry = p.get("entry_price", 0)
        if entry <= 0 or sym not in TP_CAPS:
            corrected.append(p)
            continue

        tp_cap_pct = TP_CAPS.get(sym, 10.0) / 100.0
        sl_cap_pct = SL_CAPS.get(sym, 6.0) / 100.0
        direction = p.get("direction", "LONG").upper()

        # Current TP/SL distance
        tp = p.get("take_profit", entry)
        sl = p.get("stop_loss", entry)
        original_tp_pct = abs(tp - entry) / entry
        original_sl_pct = abs(sl - entry) / entry

        adjustments = []

        # Use ATR-based sizing if available, but cap at max
        atr_info = atr_data.get(sym, {})
        atr_pct = atr_info.get("atr_pct", 2.0) / 100.0

        # TP: cap at min(3 * ATR, commodity cap)
        ideal_tp_pct = min(3.0 * atr_pct, tp_cap_pct)
        # SL: cap at min(2 * ATR, commodity cap)
        ideal_sl_pct = min(2.0 * atr_pct, sl_cap_pct)

        if original_tp_pct > tp_cap_pct:
            if direction == "LONG":
                p["take_profit"] = round(entry * (1 + ideal_tp_pct), 6)
            else:
                p["take_profit"] = round(entry * (1 - ideal_tp_pct), 6)
            adjustments.append(f"TP capped {original_tp_pct*100:.1f}% -> {ideal_tp_pct*100:.1f}%")

        if original_sl_pct > sl_cap_pct:
            if direction == "LONG":
                p["stop_loss"] = round(entry * (1 - ideal_sl_pct), 6)
            else:
                p["stop_loss"] = round(entry * (1 + ideal_sl_pct), 6)
            adjustments.append(f"SL capped {original_sl_pct*100:.1f}% -> {ideal_sl_pct*100:.1f}%")

        if adjustments:
            # Recalculate risk/reward
            new_tp_dist = abs(p["take_profit"] - entry)
            new_sl_dist = abs(p["stop_loss"] - entry)
            p["risk_reward"] = round(new_tp_dist / new_sl_dist, 2) if new_sl_dist > 0 else 1.0
            p["tp_sl_adjusted"] = True
            p["adjustment_notes"] = "; ".join(adjustments)
        else:
            p["tp_sl_adjusted"] = False
            p["adjustment_notes"] = ""

        p["source_system"] = "ml_commodity_reverser"
        corrected.append(p)

    return corrected


# ---------------------------------------------------------------------------
# Strategy variation generation
# ---------------------------------------------------------------------------
COMMODITY_STRATEGY_TEMPLATES = {
    "GC=F": [
        {"name": "gold_safe_haven_mean_reversion", "type": "mean_reversion",
         "description": "Buy gold when RSI(2) < 10 and DXY weakening; TP at BB middle",
         "entry_condition": "rsi2 < 10", "direction": "LONG",
         "tp_atr_mult": 2.5, "sl_atr_mult": 1.5, "hold_days": 5},
        {"name": "gold_seasonal_january", "type": "seasonal",
         "description": "Long gold in Jan-Feb seasonal strength",
         "entry_condition": "month in [1, 2] and rsi14 < 50", "direction": "LONG",
         "tp_atr_mult": 3.0, "sl_atr_mult": 2.0, "hold_days": 20},
        {"name": "gold_momentum_breakout", "type": "trend_following",
         "description": "Long gold on BB upper breakout with ADX > 25",
         "entry_condition": "bb_pct_b > 1.0 and adx > 25", "direction": "LONG",
         "tp_atr_mult": 2.0, "sl_atr_mult": 1.5, "hold_days": 10},
    ],
    "CL=F": [
        {"name": "oil_momentum_breakout", "type": "momentum",
         "description": "Oil momentum with volume confirmation; long when 20d mom > 5% and vol > 1.3x",
         "entry_condition": "momentum_20d > 5 and volume_ratio > 1.3", "direction": "LONG",
         "tp_atr_mult": 2.5, "sl_atr_mult": 2.0, "hold_days": 10},
        {"name": "oil_mean_reversion_oversold", "type": "mean_reversion",
         "description": "Buy oil on RSI(2) < 5 extremes",
         "entry_condition": "rsi2 < 5", "direction": "LONG",
         "tp_atr_mult": 2.0, "sl_atr_mult": 1.5, "hold_days": 5},
        {"name": "oil_seasonal_summer", "type": "seasonal",
         "description": "Long oil Jun-Jul driving season demand",
         "entry_condition": "month in [6, 7] and momentum_20d > 0", "direction": "LONG",
         "tp_atr_mult": 2.5, "sl_atr_mult": 2.0, "hold_days": 15},
    ],
    "NG=F": [
        {"name": "natgas_seasonal_winter", "type": "seasonal",
         "description": "Long natgas Oct-Feb for heating demand; high vol environment",
         "entry_condition": "month in [10, 11, 12, 1, 2]", "direction": "LONG",
         "tp_atr_mult": 3.0, "sl_atr_mult": 2.0, "hold_days": 20},
        {"name": "natgas_volatility_expansion", "type": "volatility",
         "description": "Long natgas on volatility breakout (ATR expanding + momentum)",
         "entry_condition": "atr_expanding and momentum_20d > 0", "direction": "LONG",
         "tp_atr_mult": 2.5, "sl_atr_mult": 2.0, "hold_days": 10},
        {"name": "natgas_mean_reversion_crash", "type": "mean_reversion",
         "description": "Buy natgas after >15% crash in 20d, RSI(2) < 5",
         "entry_condition": "momentum_20d < -15 and rsi2 < 5", "direction": "LONG",
         "tp_atr_mult": 3.0, "sl_atr_mult": 2.5, "hold_days": 10},
    ],
    "ZC=F": [
        {"name": "corn_seasonal_planting", "type": "seasonal",
         "description": "Long corn Mar-Jun planting season premium",
         "entry_condition": "month in [3, 4, 5, 6]", "direction": "LONG",
         "tp_atr_mult": 2.5, "sl_atr_mult": 2.0, "hold_days": 20},
        {"name": "corn_wheat_spread", "type": "spread",
         "description": "Long corn / short wheat when corn/wheat ratio < 0.70",
         "entry_condition": "corn_wheat_ratio < 0.70", "direction": "LONG",
         "tp_atr_mult": 2.0, "sl_atr_mult": 1.5, "hold_days": 15},
        {"name": "corn_momentum_trend", "type": "momentum",
         "description": "Long corn on 60d momentum > 5% with volume",
         "entry_condition": "momentum_60d > 5 and volume_ratio > 1.2", "direction": "LONG",
         "tp_atr_mult": 2.0, "sl_atr_mult": 1.5, "hold_days": 10},
    ],
    "ZW=F": [
        {"name": "wheat_seasonal_planting", "type": "seasonal",
         "description": "Long wheat Mar-Jun planting season; weather premium",
         "entry_condition": "month in [3, 4, 5, 6]", "direction": "LONG",
         "tp_atr_mult": 2.5, "sl_atr_mult": 2.0, "hold_days": 20},
        {"name": "wheat_mean_reversion", "type": "mean_reversion",
         "description": "Buy wheat on RSI(14) < 30 and BB %B < 0",
         "entry_condition": "rsi14 < 30 and bb_pct_b < 0", "direction": "LONG",
         "tp_atr_mult": 2.0, "sl_atr_mult": 1.5, "hold_days": 8},
    ],
    "ZS=F": [
        {"name": "soybean_seasonal_planting", "type": "seasonal",
         "description": "Long soybeans Mar-Jul growing season",
         "entry_condition": "month in [3, 4, 5, 6, 7]", "direction": "LONG",
         "tp_atr_mult": 2.5, "sl_atr_mult": 2.0, "hold_days": 20},
        {"name": "soybean_momentum_china_demand", "type": "momentum",
         "description": "Long soybeans on strong 60d momentum (China import demand)",
         "entry_condition": "momentum_60d > 5 and adx > 20", "direction": "LONG",
         "tp_atr_mult": 2.0, "sl_atr_mult": 1.5, "hold_days": 10},
    ],
    "SI=F": [
        {"name": "silver_gold_ratio_reversion", "type": "ratio_trade",
         "description": "Long silver when gold/silver ratio > 80 (silver undervalued)",
         "entry_condition": "gold_silver_ratio > 80", "direction": "LONG",
         "tp_atr_mult": 3.0, "sl_atr_mult": 2.0, "hold_days": 15},
        {"name": "silver_momentum_breakout", "type": "momentum",
         "description": "Long silver on BB upper breakout with volume surge",
         "entry_condition": "bb_pct_b > 1.0 and volume_ratio > 1.5", "direction": "LONG",
         "tp_atr_mult": 2.5, "sl_atr_mult": 2.0, "hold_days": 10},
    ],
    "HG=F": [
        {"name": "copper_economic_momentum", "type": "momentum",
         "description": "Long copper on rising 60d + 252d momentum (economic expansion signal)",
         "entry_condition": "momentum_60d > 0 and momentum_252d > 0", "direction": "LONG",
         "tp_atr_mult": 2.5, "sl_atr_mult": 2.0, "hold_days": 15},
        {"name": "copper_mean_reversion_oversold", "type": "mean_reversion",
         "description": "Buy copper on RSI(2) < 10 with seasonal support",
         "entry_condition": "rsi2 < 10", "direction": "LONG",
         "tp_atr_mult": 2.0, "sl_atr_mult": 1.5, "hold_days": 5},
    ],
    "PL=F": [
        {"name": "platinum_gold_spread", "type": "ratio_trade",
         "description": "Long platinum when cheap vs gold (historically platinum > gold)",
         "entry_condition": "rsi14 < 40 and momentum_60d < -5", "direction": "LONG",
         "tp_atr_mult": 2.5, "sl_atr_mult": 2.0, "hold_days": 15},
    ],
    "KC=F": [
        {"name": "coffee_seasonal_frost", "type": "seasonal",
         "description": "Long coffee May-Jul (Brazilian frost risk premium)",
         "entry_condition": "month in [5, 6, 7]", "direction": "LONG",
         "tp_atr_mult": 3.0, "sl_atr_mult": 2.0, "hold_days": 20},
    ],
    "SB=F": [
        {"name": "sugar_seasonal_spring", "type": "seasonal",
         "description": "Long sugar Feb-Apr seasonal strength",
         "entry_condition": "month in [2, 3, 4]", "direction": "LONG",
         "tp_atr_mult": 2.5, "sl_atr_mult": 2.0, "hold_days": 15},
    ],
    "HO=F": [
        {"name": "heating_oil_winter_demand", "type": "seasonal",
         "description": "Long heating oil Oct-Jan winter demand",
         "entry_condition": "month in [10, 11, 12, 1]", "direction": "LONG",
         "tp_atr_mult": 2.5, "sl_atr_mult": 2.0, "hold_days": 20},
    ],
    "ES=F": [
        {"name": "sp500_rsi2_mean_reversion", "type": "mean_reversion",
         "description": "Buy S&P on RSI(2) < 5; proven 87.5% WR on BB breakout",
         "entry_condition": "rsi2 < 5", "direction": "LONG",
         "tp_atr_mult": 1.5, "sl_atr_mult": 1.0, "hold_days": 3},
        {"name": "sp500_bb_breakout", "type": "breakout",
         "description": "S&P 500 Bollinger Breakout above upper band with ADX > 25",
         "entry_condition": "bb_pct_b > 1.0 and adx > 25", "direction": "LONG",
         "tp_atr_mult": 1.5, "sl_atr_mult": 1.0, "hold_days": 5},
    ],
    "NQ=F": [
        {"name": "nasdaq_momentum_leader", "type": "momentum",
         "description": "Long Nasdaq on strong 20d momentum with tech leadership",
         "entry_condition": "momentum_20d > 3 and adx > 20", "direction": "LONG",
         "tp_atr_mult": 2.0, "sl_atr_mult": 1.5, "hold_days": 7},
    ],
    "YM=F": [
        {"name": "dow_mean_reversion_value", "type": "mean_reversion",
         "description": "Buy Dow on RSI(2) < 10; value rotation play",
         "entry_condition": "rsi2 < 10", "direction": "LONG",
         "tp_atr_mult": 1.5, "sl_atr_mult": 1.0, "hold_days": 3},
    ],
    "RTY=F": [
        {"name": "russell_risk_on_momentum", "type": "momentum",
         "description": "Long Russell 2000 when risk-on (momentum + volume)",
         "entry_condition": "momentum_20d > 2 and volume_ratio > 1.2", "direction": "LONG",
         "tp_atr_mult": 2.0, "sl_atr_mult": 1.5, "hold_days": 7},
    ],
}


def generate_variations(features: dict, atr_data: dict) -> list:
    """Generate strategy variations per symbol with ATR-scaled TP/SL."""
    variations = []
    for sym, templates in COMMODITY_STRATEGY_TEMPLATES.items():
        feat = features.get(sym, {})
        atr_info = atr_data.get(sym, {})
        atr_val = atr_info.get("atr", 0)
        price = feat.get("latest_price", 0)
        if price <= 0 or atr_val <= 0:
            continue

        tp_cap = TP_CAPS.get(sym, 10.0) / 100.0
        sl_cap = SL_CAPS.get(sym, 6.0) / 100.0
        affinity = STRATEGY_AFFINITIES.get(sym, {})

        for tmpl in templates:
            tp_pct = min((tmpl["tp_atr_mult"] * atr_val / price), tp_cap)
            sl_pct = min((tmpl["sl_atr_mult"] * atr_val / price), sl_cap)

            direction = tmpl["direction"]
            if direction == "LONG":
                tp_price = round(price * (1 + tp_pct), 6)
                sl_price = round(price * (1 - sl_pct), 6)
            else:
                tp_price = round(price * (1 - tp_pct), 6)
                sl_price = round(price * (1 + sl_pct), 6)

            rr = round(tp_pct / sl_pct, 2) if sl_pct > 0 else 1.0

            var = {
                "id": f"ml_commodity_reverser::{sym}::{tmpl['name']}",
                "strategy": tmpl["name"],
                "strategy_type": tmpl["type"],
                "symbol": sym,
                "name": ALL_SYMBOLS[sym]["name"],
                "sector": ALL_SYMBOLS[sym].get("sector", "unknown"),
                "direction": direction,
                "entry_price": round(price, 6),
                "take_profit": tp_price,
                "stop_loss": sl_price,
                "tp_pct": round(tp_pct * 100, 3),
                "sl_pct": round(sl_pct * 100, 3),
                "risk_reward": rr,
                "hold_days": tmpl["hold_days"],
                "entry_condition": tmpl["entry_condition"],
                "description": tmpl["description"],
                "best_strategies": affinity.get("best_strategies", []),
                "notes": affinity.get("notes", ""),
                "source_system": "ml_commodity_reverser",
            }
            variations.append(var)

    return variations


# ---------------------------------------------------------------------------
# Simple backtest per variation
# ---------------------------------------------------------------------------
def backtest_variation(symbol: str, df: pd.DataFrame, variation: dict) -> dict:
    """Run a simple walk-forward backtest for a strategy variation.

    Returns win_rate, profit_factor, trade_count, avg_pnl_pct, sharpe.
    Uses last 252 bars as out-of-sample (most recent year).
    """
    if df.empty or len(df) < 100:
        return {"win_rate": 0, "trade_count": 0, "avg_pnl_pct": 0, "sharpe": 0, "profit_factor": 0}

    close = df["close"].values
    high = df["high"].values
    low = df["low"].values

    # Use last 252 bars (or all if less)
    n = min(252, len(df) - 60)
    start_idx = len(df) - n

    tp_pct = variation.get("tp_pct", 3.0) / 100.0
    sl_pct = variation.get("sl_pct", 2.0) / 100.0
    hold_days = variation.get("hold_days", 10)
    direction = variation.get("direction", "LONG")
    strat_type = variation.get("strategy_type", "")

    # Pre-compute indicators for entry signals
    close_series = df["close"]
    rsi2 = compute_rsi(close_series, 2).values
    rsi14 = compute_rsi(close_series, 14).values
    _, _, _, pct_b_series = compute_bollinger(close_series, 20, 2.0)
    pct_b = pct_b_series.values
    adx_series = compute_adx(df, 14).values
    months = df.index.month.values

    vol_20 = close_series.rolling(20).mean().values
    mom_20 = np.zeros(len(close))
    for i in range(20, len(close)):
        if close[i - 20] > 0:
            mom_20[i] = (close[i] / close[i - 20] - 1) * 100

    trades = []
    i = start_idx

    while i < len(df) - 1:
        # Determine entry signal based on strategy type
        entry_signal = False

        if strat_type == "mean_reversion":
            if not np.isnan(rsi2[i]):
                entry_signal = rsi2[i] < 10
        elif strat_type == "momentum":
            if not np.isnan(adx_series[i]):
                entry_signal = mom_20[i] > 3 and adx_series[i] > 20
        elif strat_type == "seasonal":
            meta = ALL_SYMBOLS.get(symbol, {})
            strong = meta.get("seasonal_strong", [])
            entry_signal = months[i] in strong
        elif strat_type == "breakout":
            if not np.isnan(pct_b[i]) and not np.isnan(adx_series[i]):
                entry_signal = pct_b[i] > 1.0 and adx_series[i] > 25
        elif strat_type in ("ratio_trade", "spread"):
            if not np.isnan(rsi14[i]):
                entry_signal = rsi14[i] < 35
        elif strat_type == "volatility":
            entry_signal = mom_20[i] > 0 and (not np.isnan(adx_series[i]) and adx_series[i] > 20)
        else:
            # Default: RSI-based entry
            if not np.isnan(rsi14[i]):
                entry_signal = rsi14[i] < 35 or rsi14[i] > 65

        if not entry_signal:
            i += 1
            continue

        entry_price = close[i]
        if entry_price <= 0:
            i += 1
            continue

        # Simulate trade over hold period
        pnl = 0.0
        exit_idx = min(i + hold_days, len(df) - 1)
        hit = False

        for j in range(i + 1, exit_idx + 1):
            if direction == "LONG":
                if high[j] >= entry_price * (1 + tp_pct):
                    pnl = tp_pct * 100
                    hit = True
                    break
                if low[j] <= entry_price * (1 - sl_pct):
                    pnl = -sl_pct * 100
                    hit = True
                    break
            else:
                if low[j] <= entry_price * (1 - tp_pct):
                    pnl = tp_pct * 100
                    hit = True
                    break
                if high[j] >= entry_price * (1 + sl_pct):
                    pnl = -sl_pct * 100
                    hit = True
                    break

        if not hit:
            # Exit at end of hold period
            exit_price = close[exit_idx]
            if direction == "LONG":
                pnl = ((exit_price - entry_price) / entry_price) * 100
            else:
                pnl = ((entry_price - exit_price) / entry_price) * 100

        trades.append(pnl)
        i = exit_idx + 1  # skip to after exit

    if not trades:
        return {"win_rate": 0, "trade_count": 0, "avg_pnl_pct": 0, "sharpe": 0, "profit_factor": 0}

    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t <= 0]
    win_rate = len(wins) / len(trades) if trades else 0
    avg_pnl = np.mean(trades)
    std_pnl = np.std(trades) if len(trades) > 1 else 1.0
    sharpe = (avg_pnl / std_pnl) * np.sqrt(252 / max(hold_days, 1)) if std_pnl > 0 else 0

    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 0.001
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 10.0

    return {
        "win_rate": round(win_rate, 4),
        "trade_count": len(trades),
        "avg_pnl_pct": round(avg_pnl, 3),
        "sharpe": round(sharpe, 3),
        "profit_factor": round(profit_factor, 3),
        "total_pnl_pct": round(sum(trades), 3),
    }


# ---------------------------------------------------------------------------
# CFTC COT data fetch
# ---------------------------------------------------------------------------
def fetch_cot_data() -> dict:
    """Fetch latest CFTC Commitments of Traders data."""
    try:
        import urllib.request
        url = "https://publicreporting.cftc.gov/resource/6dca-aqww.json?$limit=50&$order=report_date_as_yyyy_mm_dd DESC"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        print(f"  [COT] Fetched {len(data)} CFTC COT records")
        return {"records": len(data), "sample": data[:3] if data else []}
    except Exception as e:
        print(f"  [COT] Failed to fetch COT data: {e}")
        return {"records": 0, "error": str(e)}


# ---------------------------------------------------------------------------
# Load current picks
# ---------------------------------------------------------------------------
def load_commodity_picks() -> list:
    """Load commodity/futures picks from CTA and multi-asset scanners."""
    picks = []

    # CTA picks
    cta_path = DATA_DIR / "cta_picks.json"
    if cta_path.exists():
        with open(cta_path, "r", encoding="utf-8") as f:
            cta = json.load(f)
        for p in cta.get("picks", []):
            if p.get("asset_class") in ("COMMODITY",):
                picks.append(p)

    # Multi-asset picks (COMMODITY + FUTURES category=commodity)
    ma_path = DATA_DIR / "multi_asset_picks.json"
    if ma_path.exists():
        with open(ma_path, "r", encoding="utf-8") as f:
            ma = json.load(f)
        for p in ma.get("picks", []):
            if p.get("asset_class") in ("COMMODITY", "FUTURES") and p.get("category") in ("commodity", "futures"):
                picks.append(p)

    return picks


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("Commodity Asset Class Pattern Analyzer")
    print("=" * 70)
    ts_start = datetime.now(timezone.utc)

    # 1. Fetch OHLCV for all symbols
    print("\n[1/7] Fetching 2y daily OHLCV for 16 instruments...")
    price_data = {}
    for sym in ALL_SYMBOLS:
        print(f"  Fetching {sym} ({ALL_SYMBOLS[sym]['name']})...")
        df = fetch_ohlcv(sym, "2y")
        if not df.empty:
            price_data[sym] = df
            print(f"    -> {len(df)} bars from {df.index[0].date()} to {df.index[-1].date()}")
        else:
            print(f"    -> FAILED (will skip)")

    print(f"\n  Fetched {len(price_data)}/{len(ALL_SYMBOLS)} symbols successfully")

    # 2. Compute features
    print("\n[2/7] Computing commodity-specific features...")
    features = {}
    atr_data = {}
    for sym, df in price_data.items():
        feat = compute_features(sym, df)
        if feat:
            features[sym] = feat
            atr_data[sym] = {"atr": feat["atr"], "atr_pct": feat["atr_pct"]}
            print(f"  {sym}: RSI14={feat['rsi14']}, ATR%={feat['atr_pct']}, Mom20d={feat['momentum_20d']}%, "
                  f"Seasonal={feat['seasonal_signal']}, ADX={feat['adx']}")

    # Cross-commodity ratios
    cross_ratios = compute_cross_ratios(price_data)
    print(f"\n  Cross ratios: {json.dumps(cross_ratios, indent=2)}")

    # 3. Fetch COT data
    print("\n[3/7] Fetching CFTC COT data...")
    cot_data = fetch_cot_data()

    # 4. Load and correct current picks
    print("\n[4/7] Loading current commodity picks and correcting TP/SL...")
    raw_picks = load_commodity_picks()
    print(f"  Loaded {len(raw_picks)} commodity/futures picks")
    corrected_picks = correct_tp_sl(raw_picks, atr_data)
    adjusted_count = sum(1 for p in corrected_picks if p.get("tp_sl_adjusted"))
    print(f"  Adjusted {adjusted_count}/{len(corrected_picks)} picks with too-wide TP/SL")
    for p in corrected_picks:
        if p.get("tp_sl_adjusted"):
            print(f"    {p['symbol']}: {p['adjustment_notes']}")

    # 5. Generate strategy variations
    print("\n[5/7] Generating per-commodity strategy variations...")
    variations = generate_variations(features, atr_data)
    print(f"  Generated {len(variations)} strategy variations across {len(COMMODITY_STRATEGY_TEMPLATES)} symbols")

    # 6. Backtest each variation
    print("\n[6/7] Backtesting each variation (last 252 bars)...")
    for var in variations:
        sym = var["symbol"]
        df = price_data.get(sym)
        if df is not None and not df.empty:
            bt = backtest_variation(sym, df, var)
            var["backtest"] = bt
            status = "PASS" if bt["win_rate"] >= 0.45 and bt["trade_count"] >= 3 else "LOW"
            print(f"  {var['strategy']:40s} | WR={bt['win_rate']:.1%} | PF={bt['profit_factor']:.2f} | "
                  f"Trades={bt['trade_count']:3d} | PnL={bt['total_pnl_pct']:+.1f}% | [{status}]")
        else:
            var["backtest"] = {"win_rate": 0, "trade_count": 0, "avg_pnl_pct": 0, "sharpe": 0, "profit_factor": 0}

    # 7. Save outputs
    print("\n[7/7] Saving results...")

    # commodity_asset_analysis.json
    analysis_output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_system": "ml_commodity_reverser",
        "symbols_analyzed": len(features),
        "commodity_count": sum(1 for s in features if s in COMMODITY_SYMBOLS),
        "index_futures_count": sum(1 for s in features if s in INDEX_FUTURES_SYMBOLS),
        "cross_ratios": cross_ratios,
        "cot_data_available": cot_data.get("records", 0) > 0,
        "cot_records": cot_data.get("records", 0),
        "per_symbol": features,
        "strategy_affinities": {k: v for k, v in STRATEGY_AFFINITIES.items() if k in features},
    }
    analysis_path = DATA_DIR / "commodity_asset_analysis.json"
    with open(analysis_path, "w", encoding="utf-8") as f:
        json.dump(analysis_output, f, indent=2, default=str)
    print(f"  Saved {analysis_path} ({len(features)} symbols)")

    # commodity_strategy_variations.json
    variations_output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_system": "ml_commodity_reverser",
        "total_variations": len(variations),
        "passing_variations": sum(1 for v in variations
                                  if v.get("backtest", {}).get("win_rate", 0) >= 0.45
                                  and v.get("backtest", {}).get("trade_count", 0) >= 3),
        "variations": variations,
    }
    variations_path = DATA_DIR / "commodity_strategy_variations.json"
    with open(variations_path, "w", encoding="utf-8") as f:
        json.dump(variations_output, f, indent=2, default=str)
    print(f"  Saved {variations_path} ({len(variations)} variations)")

    # commodity_ml_picks.json
    picks_output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_system": "ml_commodity_reverser",
        "total_picks": len(corrected_picks),
        "adjusted_count": adjusted_count,
        "tp_sl_caps": TP_CAPS,
        "picks": corrected_picks,
    }
    picks_path = DATA_DIR / "commodity_ml_picks.json"
    with open(picks_path, "w", encoding="utf-8") as f:
        json.dump(picks_output, f, indent=2, default=str)
    print(f"  Saved {picks_path} ({len(corrected_picks)} picks, {adjusted_count} adjusted)")

    elapsed = (datetime.now(timezone.utc) - ts_start).total_seconds()
    print(f"\nDone in {elapsed:.1f}s")
    print(f"  Analysis: {analysis_path}")
    print(f"  Variations: {variations_path}")
    print(f"  ML Picks: {picks_path}")


if __name__ == "__main__":
    main()
