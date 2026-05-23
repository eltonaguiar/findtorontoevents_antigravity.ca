#!/usr/bin/env python3
"""
CTA Strategy Replicator -- Academically Verified Multi-Asset Strategies
========================================================================
Implements the most proven systematic trading strategies from academic literature.
All strategies have 20+ years of out-of-sample evidence and published rules.

Strategies:
1. TSMOM Blended (1/3/12 month) -- Sharpe 1.31, Hurst/Ooi/Pedersen (2017)
2. Donchian 55-day Breakout -- Original Turtle Trading, Sharpe 0.8-1.0
3. MA 50/200 Golden Cross -- Simple but robust trend signal
4. FX Carry + Momentum + Value -- Sharpe 0.95, 200+ years evidence
5. Commodity Momentum + Term Structure -- Sharpe 0.96, Moskowitz et al.
6. Cross-Asset TSMOM -- Sharpe 1.84, Pitkajarvi & Suominen (2020)
7. Volatility-Targeted Position Sizing -- Normalize risk across assets

Usage:
    python copy_trader_intel/cta_strategy_replicator.py
"""

import sys
import os
import json
import math
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

if sys.platform == "win32":
    try:
        sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
        sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    except (ValueError, OSError):
        pass

try:
    import numpy as np
    import pandas as pd
except ImportError:
    print("[ERROR] numpy and pandas required: pip install numpy pandas")
    sys.exit(1)

try:
    import yfinance as yf
except ImportError:
    print("[ERROR] yfinance required: pip install yfinance")
    sys.exit(1)

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Universe
# ---------------------------------------------------------------------------
CTA_UNIVERSE = {
    # Equity indices
    "SPY": {"name": "S&P 500", "class": "equity", "vol_target": 0.15},
    "QQQ": {"name": "Nasdaq 100", "class": "equity", "vol_target": 0.20},
    "IWM": {"name": "Russell 2000", "class": "equity", "vol_target": 0.20},
    "EFA": {"name": "EAFE", "class": "equity", "vol_target": 0.15},
    "EEM": {"name": "Emerging Markets", "class": "equity", "vol_target": 0.20},
    # Bonds
    "TLT": {"name": "20Y Treasury", "class": "bond", "vol_target": 0.15},
    "IEF": {"name": "7-10Y Treasury", "class": "bond", "vol_target": 0.08},
    # Commodities
    "GC=F": {"name": "Gold", "class": "commodity", "vol_target": 0.15},
    "SI=F": {"name": "Silver", "class": "commodity", "vol_target": 0.25},
    "CL=F": {"name": "Crude Oil", "class": "commodity", "vol_target": 0.30},
    "NG=F": {"name": "Natural Gas", "class": "commodity", "vol_target": 0.40},
    "HG=F": {"name": "Copper", "class": "commodity", "vol_target": 0.20},
    "ZC=F": {"name": "Corn", "class": "commodity", "vol_target": 0.20},
    "ZW=F": {"name": "Wheat", "class": "commodity", "vol_target": 0.25},
    "ZS=F": {"name": "Soybeans", "class": "commodity", "vol_target": 0.20},
    # Forex
    "EURUSD=X": {"name": "EUR/USD", "class": "forex", "vol_target": 0.08},
    "GBPUSD=X": {"name": "GBP/USD", "class": "forex", "vol_target": 0.09},
    "USDJPY=X": {"name": "USD/JPY", "class": "forex", "vol_target": 0.08},
    "AUDUSD=X": {"name": "AUD/USD", "class": "forex", "vol_target": 0.10},
    "USDCAD=X": {"name": "USD/CAD", "class": "forex", "vol_target": 0.07},
    "NZDUSD=X": {"name": "NZD/USD", "class": "forex", "vol_target": 0.10},
}

# Central bank rates (approx Q1 2026) for carry calc
CB_RATES = {
    "USD": 4.50, "EUR": 3.00, "GBP": 4.25, "JPY": 0.25,
    "AUD": 3.85, "NZD": 3.50, "CAD": 3.25, "CHF": 1.25,
}

# Map forex symbols to base/quote currencies
FX_CURRENCY_MAP = {
    "EURUSD=X": ("EUR", "USD"),
    "GBPUSD=X": ("GBP", "USD"),
    "USDJPY=X": ("USD", "JPY"),
    "AUDUSD=X": ("AUD", "USD"),
    "USDCAD=X": ("USD", "CAD"),
    "NZDUSD=X": ("NZD", "USD"),
}

# Commodity symbols for ranking strategies
COMMODITY_SYMBOLS = [s for s, m in CTA_UNIVERSE.items() if m["class"] == "commodity"]
FOREX_SYMBOLS = [s for s, m in CTA_UNIVERSE.items() if m["class"] == "forex"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range."""
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def _sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()


def _realized_vol(df: pd.DataFrame, lookback: int = 20) -> float:
    """Annualized realized volatility from daily returns."""
    rets = df["Close"].pct_change().dropna().tail(lookback)
    if len(rets) < max(5, lookback // 2):
        return None
    return float(rets.std() * math.sqrt(252))


def _adx(df: pd.DataFrame, period: int = 14) -> float:
    """Average Directional Index (last value)."""
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    atr_vals = _atr(df, period)
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr_vals)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr_vals)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1)
    adx_val = dx.rolling(period).mean()
    last = adx_val.dropna()
    return float(last.iloc[-1]) if len(last) > 0 else 0.0


def _vol_position_size(symbol: str, realized_vol: float) -> float:
    """
    Volatility-targeted position sizing.
    position_size = target_vol / realized_vol, capped at 2.0x
    """
    meta = CTA_UNIVERSE.get(symbol, {})
    target = meta.get("vol_target", 0.15)
    if realized_vol is None or realized_vol <= 0:
        return 1.0
    raw = target / realized_vol
    return min(raw, 2.0)


def _make_pick(
    strategy: str,
    symbol: str,
    direction: str,
    entry_price: float,
    take_profit: float,
    stop_loss: float,
    confidence: float,
    reason: str,
    academic_ref: str,
    sharpe_expected: float,
    lookback_months: int,
    vol_target: float,
    position_size_pct: float,
    extra_fields: dict = None,
) -> dict:
    """Build a pick dict matching the standard multi_asset_picks format."""
    meta = CTA_UNIVERSE.get(symbol, {})
    asset_class = meta.get("class", "unknown").upper()
    category = meta.get("class", "unknown")
    rr = 0.0
    risk = abs(entry_price - stop_loss)
    if risk > 0:
        rr = round(abs(take_profit - entry_price) / risk, 2)

    pick_id = f"cta_{strategy}::{symbol}::{datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%M')}"

    extra = {
        "academic_reference": academic_ref,
        "sharpe_expected": sharpe_expected,
        "lookback_months": lookback_months,
        "vol_target": vol_target,
        "position_size_pct": round(position_size_pct * 100, 2),
    }
    if extra_fields:
        extra.update(extra_fields)

    return {
        "id": pick_id,
        "strategy": f"cta_{strategy}",
        "symbol": symbol,
        "category": category,
        "asset_class": asset_class,
        "signal_type": "BUY" if direction == "LONG" else "SELL",
        "direction": direction,
        "entry_price": round(entry_price, 6),
        "entry_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "take_profit": round(take_profit, 6),
        "stop_loss": round(stop_loss, 6),
        "confidence": round(confidence, 3),
        "ml_score": round(confidence, 3),
        "risk_reward": rr,
        "reason": reason,
        "status": "OPEN",
        "exit_price": None,
        "exit_date": None,
        "pnl_pct": None,
        "pnl_dollar": None,
        "hold_days": None,
        "forward_trades": 0,
        "forward_wr": 0.0,
        "forward_validated": False,
        "forward_test_only": True,
        "source_system": "cta_replicator",
        "source_strategy_type": "academic_cta_replication",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "extra": extra,
    }


# ---------------------------------------------------------------------------
# Strategy 1: TSMOM Blended (1/3/12 month)
# ---------------------------------------------------------------------------

def tsmom_blended(data: pd.DataFrame, symbol: str) -> Optional[dict]:
    """
    Time-Series Momentum blended across 1, 3, and 12 month lookbacks.
    Source: Moskowitz, Ooi, Pedersen (2012); Hurst, Ooi, Pedersen (2017)
    Sharpe ~1.31 across 58 futures, every decade since 1880.
    """
    if len(data) < 260:
        return None

    close = data["Close"]
    # Calculate returns for each lookback
    ret_21 = float((close.iloc[-1] / close.iloc[-22]) - 1) if len(close) > 22 else 0
    ret_63 = float((close.iloc[-1] / close.iloc[-64]) - 1) if len(close) > 64 else 0
    ret_252 = float((close.iloc[-1] / close.iloc[-253]) - 1) if len(close) > 253 else 0

    # Blended signal: equal-weight average of sign of each return
    signals = [np.sign(ret_21), np.sign(ret_63), np.sign(ret_252)]
    blend = sum(signals) / 3.0

    # Threshold per research: >0.33 = LONG, <-0.33 = SHORT, else FLAT
    if abs(blend) < 0.33:
        return None

    direction = "LONG" if blend > 0 else "SHORT"
    entry = float(close.iloc[-1])
    atr_val = float(_atr(data, 14).iloc[-1])
    if atr_val <= 0 or np.isnan(atr_val):
        return None

    meta = CTA_UNIVERSE.get(symbol, {})
    asset_cls = meta.get("class", "equity")

    # TP/SL based on asset class with percentage caps
    if asset_cls == "forex":
        tp_mult, sl_mult = 1.2, 1.0
        max_tp_pct, max_sl_pct = 0.003, 0.002  # 0.3% / 0.2% for forex
    elif asset_cls == "equity":
        tp_mult, sl_mult = 2.0, 1.5
        max_tp_pct, max_sl_pct = 0.05, 0.03  # 5% / 3% for equity/ETFs
    elif asset_cls == "commodity":
        tp_mult, sl_mult = 2.0, 1.5
        max_tp_pct, max_sl_pct = 0.05, 0.03  # 5% / 3% for commodities
    elif asset_cls == "bond":
        tp_mult, sl_mult = 1.5, 1.2
        max_tp_pct, max_sl_pct = 0.03, 0.02  # 3% / 2% for bonds
    else:
        tp_mult, sl_mult = 2.0, 1.5
        max_tp_pct, max_sl_pct = 0.05, 0.03  # default

    tp_dist = min(tp_mult * atr_val, entry * max_tp_pct)
    sl_dist = min(sl_mult * atr_val, entry * max_sl_pct)
    if direction == "LONG":
        tp = entry + tp_dist
        sl = entry - sl_dist
    else:
        tp = entry - tp_dist
        sl = entry + sl_dist

    # Volatility-targeted position sizing
    rvol = _realized_vol(data, 20)
    pos_size = _vol_position_size(symbol, rvol)

    # Confidence: based on signal strength and agreement
    agreement = sum(1 for s in signals if s == np.sign(blend)) / 3.0
    confidence = 0.55 + 0.2 * agreement  # 0.55-0.75

    reason = (
        f"TSMOM blended: 1m={ret_21:+.1%}, 3m={ret_63:+.1%}, 12m={ret_252:+.1%}. "
        f"Signal={blend:+.2f} ({direction}). Vol-sized: {pos_size:.2f}x. "
        f"Hurst/Ooi/Pedersen (2017): Sharpe 1.31, every decade since 1880."
    )

    return _make_pick(
        strategy="tsmom_blend",
        symbol=symbol,
        direction=direction,
        entry_price=entry,
        take_profit=tp,
        stop_loss=sl,
        confidence=confidence,
        reason=reason,
        academic_ref="Hurst, Ooi, Pedersen (2017) - A Century of Evidence on Trend-Following",
        sharpe_expected=1.31,
        lookback_months=12,
        vol_target=meta.get("vol_target", 0.15),
        position_size_pct=pos_size,
        extra_fields={
            "ret_1m": round(ret_21, 4),
            "ret_3m": round(ret_63, 4),
            "ret_12m": round(ret_252, 4),
            "blend_signal": round(blend, 4),
            "realized_vol_20d": round(rvol, 4) if rvol else None,
        },
    )


# ---------------------------------------------------------------------------
# Strategy 2: Donchian 55-Day Breakout (Turtle Trading System 2)
# ---------------------------------------------------------------------------

def donchian_breakout_55(data: pd.DataFrame, symbol: str) -> Optional[dict]:
    """
    55-day Donchian channel breakout (Turtle Trading System 2).
    Source: Richard Dennis / Curtis Faith (1983).
    Entry on 55-day high/low break, exit on 20-day trailing stop.
    """
    if len(data) < 60:
        return None

    close = data["Close"]
    high = data["High"]
    low = data["Low"]
    current = float(close.iloc[-1])

    # 55-day channel
    high_55 = float(high.iloc[-56:-1].max())
    low_55 = float(low.iloc[-56:-1].min())

    # 20-day channel (for exit / trailing stop reference)
    low_20 = float(low.iloc[-21:-1].min())
    high_20 = float(high.iloc[-21:-1].max())

    direction = None
    if current > high_55:
        direction = "LONG"
    elif current < low_55:
        direction = "SHORT"
    else:
        return None

    atr_val = float(_atr(data, 30).iloc[-1])
    if atr_val <= 0 or np.isnan(atr_val):
        return None

    # TP: 3x ATR, SL: 2x ATR (per Turtle rules)
    if direction == "LONG":
        tp = current + 3.0 * atr_val
        sl = current - 2.0 * atr_val
    else:
        tp = current - 3.0 * atr_val
        sl = current + 2.0 * atr_val

    rvol = _realized_vol(data, 20)
    pos_size = _vol_position_size(symbol, rvol)

    # Confidence: breakout strength relative to channel width
    channel_width = high_55 - low_55
    if channel_width > 0:
        breakout_pct = abs(current - (high_55 if direction == "LONG" else low_55)) / channel_width
    else:
        breakout_pct = 0
    confidence = min(0.75, 0.60 + 0.15 * breakout_pct)

    reason = (
        f"Donchian 55-day breakout: price {current:.4f} {'>' if direction == 'LONG' else '<'} "
        f"{'55d high' if direction == 'LONG' else '55d low'} "
        f"{high_55 if direction == 'LONG' else low_55:.4f}. "
        f"20d trailing stop: {low_20 if direction == 'LONG' else high_20:.4f}. "
        f"Turtle Trading System 2, Richard Dennis (1983)."
    )

    return _make_pick(
        strategy="donchian_55",
        symbol=symbol,
        direction=direction,
        entry_price=current,
        take_profit=tp,
        stop_loss=sl,
        confidence=confidence,
        reason=reason,
        academic_ref="Turtle Trading System 2 - Richard Dennis / Curtis Faith (1983)",
        sharpe_expected=0.8,
        lookback_months=3,
        vol_target=CTA_UNIVERSE.get(symbol, {}).get("vol_target", 0.15),
        position_size_pct=pos_size,
        extra_fields={
            "high_55d": round(high_55, 6),
            "low_55d": round(low_55, 6),
            "trailing_stop_20d": round(low_20 if direction == "LONG" else high_20, 6),
            "atr_30": round(atr_val, 6),
        },
    )


# ---------------------------------------------------------------------------
# Strategy 3: Golden Cross 50/200 SMA
# ---------------------------------------------------------------------------

def golden_cross_200(data: pd.DataFrame, symbol: str) -> Optional[dict]:
    """
    50/200 SMA crossover with ADX trending filter.
    BUY: 50 SMA crosses above 200 SMA and price > 200 SMA.
    SELL: 50 SMA crosses below 200 SMA and price < 200 SMA.
    Confirmation: ADX > 20.
    """
    if len(data) < 210:
        return None

    close = data["Close"]
    sma50 = _sma(close, 50)
    sma200 = _sma(close, 200)

    if sma50.iloc[-1] is None or sma200.iloc[-1] is None:
        return None
    if np.isnan(sma50.iloc[-1]) or np.isnan(sma200.iloc[-1]):
        return None

    current = float(close.iloc[-1])
    sma50_now = float(sma50.iloc[-1])
    sma50_prev = float(sma50.iloc[-2])
    sma200_now = float(sma200.iloc[-1])
    sma200_prev = float(sma200.iloc[-2])

    # Check for crossover
    direction = None
    if sma50_prev <= sma200_prev and sma50_now > sma200_now and current > sma200_now:
        direction = "LONG"  # Golden cross
    elif sma50_prev >= sma200_prev and sma50_now < sma200_now and current < sma200_now:
        direction = "SHORT"  # Death cross
    else:
        # Also allow existing trend (not just fresh cross) if strongly positioned
        if sma50_now > sma200_now and current > sma200_now and (sma50_now - sma200_now) / sma200_now > 0.02:
            direction = "LONG"
        elif sma50_now < sma200_now and current < sma200_now and (sma200_now - sma50_now) / sma200_now > 0.02:
            direction = "SHORT"
        else:
            return None

    # ADX filter: require trending market
    adx_val = _adx(data, 14)
    if adx_val < 20:
        return None

    atr_val = float(_atr(data, 14).iloc[-1])
    if atr_val <= 0 or np.isnan(atr_val):
        return None

    # TP: 2.5x ATR, SL: 1.5x ATR
    if direction == "LONG":
        tp = current + 2.5 * atr_val
        sl = current - 1.5 * atr_val
    else:
        tp = current - 2.5 * atr_val
        sl = current + 1.5 * atr_val

    rvol = _realized_vol(data, 20)
    pos_size = _vol_position_size(symbol, rvol)

    # Fresh cross gets higher confidence
    is_fresh_cross = (sma50_prev <= sma200_prev and sma50_now > sma200_now) or \
                     (sma50_prev >= sma200_prev and sma50_now < sma200_now)
    confidence = 0.70 if is_fresh_cross else 0.60

    reason = (
        f"{'Golden' if direction == 'LONG' else 'Death'} Cross: "
        f"SMA50={sma50_now:.2f} {'>' if direction == 'LONG' else '<'} SMA200={sma200_now:.2f}. "
        f"ADX={adx_val:.1f} (trending). Price={current:.4f}. "
        f"{'Fresh crossover' if is_fresh_cross else 'Established trend'}. "
        f"Duke study: 90% of DMAC combos profitable OOS."
    )

    return _make_pick(
        strategy="golden_cross_200",
        symbol=symbol,
        direction=direction,
        entry_price=current,
        take_profit=tp,
        stop_loss=sl,
        confidence=confidence,
        reason=reason,
        academic_ref="Dual MA Crossover 50/200 - widely validated, Duke University study",
        sharpe_expected=0.55,
        lookback_months=10,
        vol_target=CTA_UNIVERSE.get(symbol, {}).get("vol_target", 0.15),
        position_size_pct=pos_size,
        extra_fields={
            "sma50": round(sma50_now, 6),
            "sma200": round(sma200_now, 6),
            "adx": round(adx_val, 2),
            "fresh_cross": is_fresh_cross,
        },
    )


# ---------------------------------------------------------------------------
# Strategy 4: FX Multifactor (Carry + Momentum + Value)
# ---------------------------------------------------------------------------

def fx_multifactor(data: pd.DataFrame, symbol: str) -> Optional[dict]:
    """
    Combined carry + momentum + value for forex.
    Source: Brunnermeier/Nagel/Pedersen (2009), Menkhoff et al. (2012), AQR.
    Signal: avg of 3 z-scores. >0.5 -> LONG, <-0.5 -> SHORT.
    """
    if symbol not in FX_CURRENCY_MAP:
        return None
    if len(data) < 260:
        return None

    close = data["Close"]
    current = float(close.iloc[-1])
    base, quote = FX_CURRENCY_MAP[symbol]

    # --- Carry factor: yield differential ---
    base_rate = CB_RATES.get(base, 0)
    quote_rate = CB_RATES.get(quote, 0)
    carry_diff = base_rate - quote_rate  # positive = long base currency is positive carry
    # Normalize carry to roughly [-2, 2] range
    carry_z = carry_diff / 2.0

    # --- Momentum factor: 12-month return ---
    ret_252 = float((close.iloc[-1] / close.iloc[-253]) - 1) if len(close) > 253 else 0
    # Normalize: typical FX 12m return is ~5-10%
    mom_z = ret_252 / 0.08 if abs(ret_252) < 0.5 else np.sign(ret_252) * 2.0

    # --- Value factor: deviation from 5-year average (PPP proxy) ---
    if len(close) >= 252 * 5:
        avg_5y = float(close.iloc[-252*5:].mean())
    elif len(close) >= 252:
        avg_5y = float(close.mean())  # use available data
    else:
        avg_5y = current

    if avg_5y > 0:
        value_dev = (avg_5y - current) / avg_5y  # positive = undervalued (bullish)
    else:
        value_dev = 0
    value_z = value_dev / 0.05  # normalize

    # Combined signal: average of z-scores
    combined = (carry_z + mom_z + value_z) / 3.0

    if abs(combined) < 0.5:
        return None

    direction = "LONG" if combined > 0 else "SHORT"

    atr_val = float(_atr(data, 14).iloc[-1])
    if atr_val <= 0 or np.isnan(atr_val):
        return None

    # FX TP/SL: 1.2x ATR / 1.0x ATR
    if direction == "LONG":
        tp = current + 1.2 * atr_val
        sl = current - 1.0 * atr_val
    else:
        tp = current - 1.2 * atr_val
        sl = current + 1.0 * atr_val

    rvol = _realized_vol(data, 20)
    pos_size = _vol_position_size(symbol, rvol)

    # Confidence: based on factor agreement
    factor_signs = [np.sign(carry_z), np.sign(mom_z), np.sign(value_z)]
    agreement = sum(1 for s in factor_signs if s == np.sign(combined)) / 3.0
    confidence = 0.55 + 0.2 * agreement

    reason = (
        f"FX Multifactor: carry_z={carry_z:+.2f} ({base}:{base_rate}% vs {quote}:{quote_rate}%), "
        f"mom_z={mom_z:+.2f} (12m={ret_252:+.1%}), value_z={value_z:+.2f}. "
        f"Combined={combined:+.2f}. Brunnermeier et al. (2009), AQR: Sharpe ~0.95."
    )

    return _make_pick(
        strategy="fx_multifactor",
        symbol=symbol,
        direction=direction,
        entry_price=current,
        take_profit=tp,
        stop_loss=sl,
        confidence=confidence,
        reason=reason,
        academic_ref="Brunnermeier/Nagel/Pedersen (2009) + Menkhoff et al. (2012)",
        sharpe_expected=0.95,
        lookback_months=12,
        vol_target=CTA_UNIVERSE.get(symbol, {}).get("vol_target", 0.08),
        position_size_pct=pos_size,
        extra_fields={
            "carry_z": round(carry_z, 4),
            "momentum_z": round(mom_z, 4),
            "value_z": round(value_z, 4),
            "combined_signal": round(combined, 4),
            "carry_diff_pct": carry_diff,
            "ret_12m": round(ret_252, 4),
        },
    )


# ---------------------------------------------------------------------------
# Strategy 5: Commodity Momentum + Term Structure
# ---------------------------------------------------------------------------

def commodity_momentum_term(
    all_data: dict, symbol: str
) -> Optional[dict]:
    """
    Commodity momentum + term structure signal.
    Source: Moskowitz et al. (2012), Gorton & Rouwenhorst (2006).
    LONG top 3, SHORT bottom 3 commodities by combined rank.
    """
    if symbol not in COMMODITY_SYMBOLS:
        return None

    data = all_data.get(symbol)
    if data is None or len(data) < 260:
        return None

    close = data["Close"]
    current = float(close.iloc[-1])

    # --- Momentum rank across all commodities ---
    momentum_scores = {}
    for sym in COMMODITY_SYMBOLS:
        d = all_data.get(sym)
        if d is None or len(d) < 260:
            continue
        c = d["Close"]
        ret_12m = float((c.iloc[-1] / c.iloc[-253]) - 1)
        momentum_scores[sym] = ret_12m

    if len(momentum_scores) < 4:
        return None

    # Rank momentum (higher = better)
    sorted_mom = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)
    mom_rank = {s: i for i, (s, _) in enumerate(sorted_mom)}

    # --- Term structure proxy: (front - price_252d_ago) / price_252d_ago ---
    # Backwardation (positive) = bullish, Contango (negative) = bearish
    term_scores = {}
    for sym in COMMODITY_SYMBOLS:
        d = all_data.get(sym)
        if d is None or len(d) < 260:
            continue
        c = d["Close"]
        price_now = float(c.iloc[-1])
        price_252 = float(c.iloc[-253])
        if price_252 > 0:
            term = (price_now - price_252) / price_252
        else:
            term = 0
        term_scores[sym] = term

    # Rank term structure (higher = more backwardation/bullish)
    sorted_term = sorted(term_scores.items(), key=lambda x: x[1], reverse=True)
    term_rank = {s: i for i, (s, _) in enumerate(sorted_term)}

    # Combined rank (lower combined rank = stronger signal for LONG)
    if symbol not in mom_rank or symbol not in term_rank:
        return None

    combined_rank = mom_rank[symbol] + term_rank[symbol]
    n = len(momentum_scores)

    # LONG top 3 commodities, SHORT bottom 3
    all_combined = {}
    for sym in momentum_scores:
        if sym in term_rank:
            all_combined[sym] = mom_rank[sym] + term_rank[sym]

    sorted_combined = sorted(all_combined.items(), key=lambda x: x[1])
    top_3 = [s for s, _ in sorted_combined[:3]]
    bottom_3 = [s for s, _ in sorted_combined[-3:]]

    direction = None
    if symbol in top_3:
        direction = "LONG"
    elif symbol in bottom_3:
        direction = "SHORT"
    else:
        return None

    atr_val = float(_atr(data, 14).iloc[-1])
    if atr_val <= 0 or np.isnan(atr_val):
        return None

    # TP: 2.5x ATR, SL: 2.0x ATR
    if direction == "LONG":
        tp = current + 2.5 * atr_val
        sl = current - 2.0 * atr_val
    else:
        tp = current - 2.5 * atr_val
        sl = current + 2.0 * atr_val

    rvol = _realized_vol(data, 20)
    pos_size = _vol_position_size(symbol, rvol)

    # Confidence: based on rank position
    rank_position = combined_rank / max(1, 2 * (n - 1))  # 0 = best, 1 = worst
    if direction == "LONG":
        confidence = 0.70 - 0.1 * rank_position
    else:
        confidence = 0.60 + 0.1 * rank_position

    mom_ret = momentum_scores.get(symbol, 0)
    term_val = term_scores.get(symbol, 0)

    reason = (
        f"Commodity Mom+Term: 12m return={mom_ret:+.1%} (rank {mom_rank[symbol]+1}/{n}), "
        f"term structure={term_val:+.1%} (rank {term_rank[symbol]+1}/{n}). "
        f"Combined rank {combined_rank+1}/{2*n} -> {direction}. "
        f"Moskowitz et al. (2012), Gorton & Rouwenhorst (2006): Sharpe ~0.96."
    )

    return _make_pick(
        strategy="commodity_momentum_term",
        symbol=symbol,
        direction=direction,
        entry_price=current,
        take_profit=tp,
        stop_loss=sl,
        confidence=confidence,
        reason=reason,
        academic_ref="Moskowitz et al. (2012) + Gorton & Rouwenhorst (2006)",
        sharpe_expected=0.96,
        lookback_months=12,
        vol_target=CTA_UNIVERSE.get(symbol, {}).get("vol_target", 0.20),
        position_size_pct=pos_size,
        extra_fields={
            "momentum_12m": round(mom_ret, 4),
            "term_structure": round(term_val, 4),
            "momentum_rank": mom_rank[symbol] + 1,
            "term_rank": term_rank[symbol] + 1,
            "combined_rank": combined_rank + 1,
            "total_commodities": n,
        },
    )


# ---------------------------------------------------------------------------
# Strategy 6: Cross-Asset TSMOM
# ---------------------------------------------------------------------------

def cross_asset_tsmom(all_data: dict) -> list:
    """
    Cross-asset time-series momentum.
    Source: Pitkajarvi & Suominen (2020), Sharpe ~1.84.

    Cross-asset signals:
    - Bond returns predict equity (flight-to-safety ending)
    - Equity returns inversely predict bonds
    - Commodity momentum predicts commodity
    Each blended with own-asset TSMOM.
    """
    picks = []

    # Get reference asset 1-month returns
    def _ret_1m(sym):
        d = all_data.get(sym)
        if d is None or len(d) < 25:
            return None
        c = d["Close"]
        return float((c.iloc[-1] / c.iloc[-22]) - 1)

    tlt_ret = _ret_1m("TLT")
    spy_ret = _ret_1m("SPY")

    for symbol, meta in CTA_UNIVERSE.items():
        data = all_data.get(symbol)
        if data is None or len(data) < 260:
            continue

        close = data["Close"]
        current = float(close.iloc[-1])
        asset_cls = meta["class"]

        # Own-asset TSMOM (1-month)
        own_ret = float((close.iloc[-1] / close.iloc[-22]) - 1) if len(close) > 22 else 0
        own_signal = np.sign(own_ret)

        # Cross-asset signal
        cross_signal = 0.0
        cross_reason = ""

        if asset_cls == "equity" and tlt_ret is not None:
            # Bond returns predict equity: positive TLT = flight to safety ending = equity bullish
            cross_signal = np.sign(tlt_ret) * 0.5
            cross_reason = f"TLT 1m={tlt_ret:+.1%} -> equity {'bullish' if tlt_ret > 0 else 'bearish'}"

        elif asset_cls == "bond" and spy_ret is not None:
            # Equity returns inversely predict bonds: negative SPY = bonds bullish
            cross_signal = -np.sign(spy_ret) * 0.5
            cross_reason = f"SPY 1m={spy_ret:+.1%} -> bonds {'bullish' if spy_ret < 0 else 'bearish'}"

        elif asset_cls == "commodity":
            # Commodity momentum predicts commodity (same-class momentum)
            commodity_rets = []
            for cs in COMMODITY_SYMBOLS:
                r = _ret_1m(cs)
                if r is not None:
                    commodity_rets.append(r)
            if commodity_rets:
                avg_comm_ret = sum(commodity_rets) / len(commodity_rets)
                cross_signal = np.sign(avg_comm_ret) * 0.3
                cross_reason = f"Commodity avg 1m={avg_comm_ret:+.1%}"

        elif asset_cls == "forex":
            # For FX, use equity risk sentiment
            if spy_ret is not None:
                # Risk-on (positive SPY) = bullish for high-yield FX
                cross_signal = np.sign(spy_ret) * 0.3
                cross_reason = f"Risk sentiment SPY 1m={spy_ret:+.1%}"

        # Blend: 60% own TSMOM + 40% cross-asset
        blended = 0.6 * own_signal + 0.4 * cross_signal

        if abs(blended) < 0.3:
            continue

        direction = "LONG" if blended > 0 else "SHORT"

        atr_val = float(_atr(data, 14).iloc[-1])
        if atr_val <= 0 or np.isnan(atr_val):
            continue

        # TP/SL scaled by asset class with percentage caps
        if asset_cls == "forex":
            tp_mult, sl_mult = 1.2, 1.0
            max_tp_pct, max_sl_pct = 0.003, 0.002  # 0.3% / 0.2%
        elif asset_cls == "bond":
            tp_mult, sl_mult = 1.5, 1.2
            max_tp_pct, max_sl_pct = 0.03, 0.02  # 3% / 2%
        elif asset_cls == "equity":
            tp_mult, sl_mult = 2.0, 1.5
            max_tp_pct, max_sl_pct = 0.05, 0.03  # 5% / 3% for equity/ETFs
        elif asset_cls == "commodity":
            tp_mult, sl_mult = 2.0, 1.5
            max_tp_pct, max_sl_pct = 0.05, 0.03  # 5% / 3%
        else:
            tp_mult, sl_mult = 2.0, 1.5
            max_tp_pct, max_sl_pct = 0.05, 0.03

        tp_dist = min(tp_mult * atr_val, current * max_tp_pct)
        sl_dist = min(sl_mult * atr_val, current * max_sl_pct)
        if direction == "LONG":
            tp = current + tp_dist
            sl = current - sl_dist
        else:
            tp = current - tp_dist
            sl = current + sl_dist

        rvol = _realized_vol(data, 20)
        pos_size = _vol_position_size(symbol, rvol)

        confidence = 0.55 + 0.15 * abs(blended)
        confidence = min(confidence, 0.80)

        reason = (
            f"Cross-Asset TSMOM: own 1m={own_ret:+.1%} (signal={own_signal:+.0f}), "
            f"cross={cross_reason}. Blended={blended:+.2f} -> {direction}. "
            f"Pitkajarvi & Suominen (2020): Sharpe 1.84."
        )

        pick = _make_pick(
            strategy="cross_asset_tsmom",
            symbol=symbol,
            direction=direction,
            entry_price=current,
            take_profit=tp,
            stop_loss=sl,
            confidence=confidence,
            reason=reason,
            academic_ref="Pitkajarvi & Suominen (2020) - Cross-Asset TSMOM",
            sharpe_expected=1.84,
            lookback_months=1,
            vol_target=meta.get("vol_target", 0.15),
            position_size_pct=pos_size,
            extra_fields={
                "own_ret_1m": round(own_ret, 4),
                "own_signal": own_signal,
                "cross_signal": round(cross_signal, 4),
                "blended_signal": round(blended, 4),
                "cross_reason": cross_reason,
            },
        )
        picks.append(pick)

    return picks


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

def load_universe_data(period: str = "2y") -> dict:
    """
    Load daily OHLCV data for entire CTA universe via yfinance.
    Returns dict of symbol -> DataFrame.
    """
    all_data = {}
    symbols = list(CTA_UNIVERSE.keys())
    print(f"[CTA] Loading {len(symbols)} instruments from yfinance ({period})...")

    # Batch download to reduce API calls
    try:
        tickers_str = " ".join(symbols)
        raw = yf.download(tickers_str, period=period, auto_adjust=True, progress=False, threads=True)
        if raw is not None and not raw.empty:
            for symbol in symbols:
                try:
                    if len(symbols) > 1 and isinstance(raw.columns, pd.MultiIndex):
                        df = raw.xs(symbol, level=1, axis=1).dropna(how="all")
                    else:
                        df = raw.copy()
                    if len(df) >= 50:
                        all_data[symbol] = df
                    else:
                        print(f"  [SKIP] {symbol}: only {len(df)} rows")
                except (KeyError, Exception):
                    pass
    except Exception as e:
        print(f"  [WARN] Batch download failed: {e}. Falling back to individual downloads.")

    # Fallback: download individually for any missing symbols
    missing = [s for s in symbols if s not in all_data]
    for symbol in missing:
        try:
            time.sleep(0.3)  # rate limit
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, auto_adjust=True)
            if df is not None and len(df) >= 50:
                all_data[symbol] = df
            else:
                print(f"  [SKIP] {symbol}: insufficient data")
        except Exception as e:
            print(f"  [FAIL] {symbol}: {e}")

    print(f"[CTA] Loaded {len(all_data)}/{len(symbols)} instruments successfully.")
    return all_data


# ---------------------------------------------------------------------------
# Main Scanner
# ---------------------------------------------------------------------------

def run_cta_scan() -> dict:
    """
    Execute full CTA strategy scan.
    1. Load 2 years daily data for universe
    2. Run all 6 strategies on applicable symbols
    3. Apply vol-targeted sizing
    4. Save cta_picks.json
    """
    print("=" * 70)
    print("CTA Strategy Replicator -- Academic Multi-Asset Scan")
    print("=" * 70)

    all_data = load_universe_data("2y")
    if not all_data:
        print("[ERROR] No data loaded. Exiting.")
        return {"picks": [], "error": "No data loaded"}

    all_picks = []
    strategy_counts = {
        "tsmom_blend": 0,
        "donchian_55": 0,
        "golden_cross_200": 0,
        "fx_multifactor": 0,
        "commodity_momentum_term": 0,
        "cross_asset_tsmom": 0,
    }

    # --- Strategy 1: TSMOM Blended ---
    print("\n[1/6] Running TSMOM Blended (1/3/12 month)...")
    for symbol in CTA_UNIVERSE:
        if symbol in all_data:
            try:
                pick = tsmom_blended(all_data[symbol], symbol)
                if pick:
                    all_picks.append(pick)
                    strategy_counts["tsmom_blend"] += 1
            except Exception as e:
                print(f"  [ERR] tsmom_blend {symbol}: {e}")

    # --- Strategy 2: Donchian 55 Breakout ---
    print("[2/6] Running Donchian 55-day Breakout...")
    for symbol in CTA_UNIVERSE:
        if symbol in all_data:
            try:
                pick = donchian_breakout_55(all_data[symbol], symbol)
                if pick:
                    all_picks.append(pick)
                    strategy_counts["donchian_55"] += 1
            except Exception as e:
                print(f"  [ERR] donchian_55 {symbol}: {e}")

    # --- Strategy 3: Golden Cross 50/200 ---
    print("[3/6] Running Golden Cross 50/200 SMA...")
    for symbol in CTA_UNIVERSE:
        if symbol in all_data:
            try:
                pick = golden_cross_200(all_data[symbol], symbol)
                if pick:
                    all_picks.append(pick)
                    strategy_counts["golden_cross_200"] += 1
            except Exception as e:
                print(f"  [ERR] golden_cross_200 {symbol}: {e}")

    # --- Strategy 4: FX Multifactor ---
    print("[4/6] Running FX Multifactor (Carry + Momentum + Value)...")
    for symbol in FOREX_SYMBOLS:
        if symbol in all_data:
            try:
                pick = fx_multifactor(all_data[symbol], symbol)
                if pick:
                    all_picks.append(pick)
                    strategy_counts["fx_multifactor"] += 1
            except Exception as e:
                print(f"  [ERR] fx_multifactor {symbol}: {e}")

    # --- Strategy 5: Commodity Momentum + Term Structure ---
    print("[5/6] Running Commodity Momentum + Term Structure...")
    for symbol in COMMODITY_SYMBOLS:
        try:
            pick = commodity_momentum_term(all_data, symbol)
            if pick:
                all_picks.append(pick)
                strategy_counts["commodity_momentum_term"] += 1
        except Exception as e:
            print(f"  [ERR] commodity_mom {symbol}: {e}")

    # --- Strategy 6: Cross-Asset TSMOM ---
    print("[6/6] Running Cross-Asset TSMOM...")
    try:
        cross_picks = cross_asset_tsmom(all_data)
        all_picks.extend(cross_picks)
        strategy_counts["cross_asset_tsmom"] = len(cross_picks)
    except Exception as e:
        print(f"  [ERR] cross_asset_tsmom: {e}")
        traceback.print_exc()

    # De-duplicate: if same symbol+direction appears from multiple strategies,
    # keep the one with highest confidence
    seen = {}
    deduped = []
    for pick in all_picks:
        key = (pick["symbol"], pick["direction"])
        if key not in seen or pick["confidence"] > seen[key]["confidence"]:
            seen[key] = pick

    # Collect all unique picks
    deduped = list(seen.values())

    # Hard-block strategies that have already been permanently killed upstream.
    try:
        import sys
        from pathlib import Path

        _alpha_dir = Path(__file__).resolve().parent.parent / "alpha_engine"
        sys.path.insert(0, str(_alpha_dir))
        from auto_tuner import PERMANENTLY_KILLED as _PERMANENTLY_KILLED
        sys.path.pop(0)
    except Exception:
        _PERMANENTLY_KILLED = set()

    if _PERMANENTLY_KILLED:
        deduped = [p for p in deduped if p.get("strategy") not in _PERMANENTLY_KILLED]

    # Sort by confidence descending
    deduped.sort(key=lambda p: p["confidence"], reverse=True)

    # Asset class summary
    by_class = {}
    by_strategy = {}
    for p in deduped:
        cls = p["asset_class"]
        by_class[cls] = by_class.get(cls, 0) + 1
        strat = p["strategy"]
        by_strategy[strat] = by_strategy.get(strat, 0) + 1

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "cta_replicator",
        "total_picks": len(deduped),
        "total_before_dedup": len(all_picks),
        "by_asset_class": by_class,
        "by_strategy": by_strategy,
        "strategy_scan_counts": strategy_counts,
        "picks": deduped,
    }

    # Save
    out_path = DATA_DIR / "cta_picks.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n[CTA] Saved {len(deduped)} picks to {out_path}")

    return result


# ---------------------------------------------------------------------------
# Summary Display
# ---------------------------------------------------------------------------

def print_summary(result: dict):
    """Print a formatted summary table."""
    picks = result.get("picks", [])
    if not picks:
        print("\nNo picks generated.")
        return

    print("\n" + "=" * 100)
    print(f"CTA PICKS SUMMARY  |  {result['total_picks']} picks  |  {result['generated_at']}")
    print("=" * 100)
    print(f"{'Symbol':<14} {'Strategy':<28} {'Dir':<6} {'Entry':>12} {'TP':>12} {'SL':>12} {'R:R':>6} {'Conf':>6}")
    print("-" * 100)

    for p in picks:
        print(
            f"{p['symbol']:<14} {p['strategy']:<28} {p['direction']:<6} "
            f"{p['entry_price']:>12.4f} {p['take_profit']:>12.4f} {p['stop_loss']:>12.4f} "
            f"{p['risk_reward']:>6.2f} {p['confidence']:>6.3f}"
        )

    print("-" * 100)
    print("\nBy strategy:")
    for strat, count in result.get("by_strategy", {}).items():
        print(f"  {strat}: {count}")
    print(f"\nBy asset class:")
    for cls, count in result.get("by_asset_class", {}).items():
        print(f"  {cls}: {count}")

    scan_counts = result.get("strategy_scan_counts", {})
    if scan_counts:
        print(f"\nRaw signal counts (before dedup):")
        for strat, count in scan_counts.items():
            print(f"  {strat}: {count}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        result = run_cta_scan()
        print_summary(result)
    except Exception as e:
        print(f"\n[FATAL] {e}")
        traceback.print_exc()
        sys.exit(1)
