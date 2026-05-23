"""
ALPHA_ENGINE -- Commodities Strategies
======================================
8 commodity strategies with academic backing.
Commodities exhibit strong seasonal patterns, mean-reversion in spreads,
and inverse correlation with the US dollar. Strategies span precious metals,
energy, and agricultural futures.

Key insight: Commodity returns are driven by inventory cycles, weather,
and USD strength -- providing diversification from equity/crypto alpha.

March 2026: Initial implementation covering seasonal, macro, mean-reversion,
spread, momentum, and divergence strategies across 12 commodity futures.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

from config import COMMODITY_SYMBOLS, CATEGORY_RISK
from indicators import (
    sma, ema, rsi, atr, adx, bollinger_bands,
    zscore, macd, volume_ratio,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atr_tp_sl_commodity(close: pd.Series, high: pd.Series, low: pd.Series,
                         tp_mult: float = 2.0, sl_mult: float = 1.5,
                         direction: str = "BUY") -> tuple[float, float, float]:
    """ATR-based TP/SL for commodities -- wider than forex, narrower than crypto.

    Commodities typically move 0.5-2.5% daily (vs forex 0.3-0.8%, crypto 2-8%).
    Default: TP=2.0x ATR, SL=1.5x ATR.  Hard cap: 5% TP, 3% SL.
    """
    atr_val = atr(high, low, close, 14)
    current_atr = float(atr_val.iloc[-1])
    price = float(close.iloc[-1])
    # ATR-based targets
    tp_distance = tp_mult * current_atr
    sl_distance = sl_mult * current_atr
    # Hard percentage caps for commodities (5% TP, 3% SL)
    tp_distance = min(tp_distance, price * 0.05)
    sl_distance = min(sl_distance, price * 0.03)
    if direction == "BUY":
        tp = price + tp_distance
        sl = price - sl_distance
    else:
        tp = price - tp_distance
        sl = price + sl_distance
    return price, tp, sl


# Forward-testing confidence cap: unvalidated commodity strategies get capped
_COMMODITY_FORWARD_TESTED: set[str] = set()  # Add strategy names here once validated


def _commodity_confidence_cap(confidence: float, strategy_name: str) -> float:
    """Cap confidence for unvalidated commodity strategies.

    2026-04-18: Cap raised from 0.72 -> 0.76 per Antigravity P2 diagnosis.
    All commodity strategies have academic backing (seasonal, COT, ATR-based)
    documented in module headers. The 0.72 cap was overly restrictive; 0.76
    gives meaningful headroom above the 0.70 gate while staying conservative
    until live forward-test data populates _COMMODITY_FORWARD_TESTED.
    """
    if strategy_name not in _COMMODITY_FORWARD_TESTED:
        return min(confidence, 0.76)
    return confidence


# =========================================================================
# STRATEGY 1: Seasonal Momentum
# =========================================================================
# Commodities have well-documented seasonal patterns driven by weather,
# planting/harvest cycles, and heating/cooling demand.
# Reference: Bodie & Rosansky (1980), "Risk and Return in Commodity Futures".
# =========================================================================

def seasonal_momentum(data: dict[str, pd.DataFrame]) -> list[dict]:
    """BUY commodities in their historically bullish months with momentum confirmation.

    Seasonal filter + 20d SMA momentum + RSI band (30-70) to avoid
    overbought/oversold entries. Each commodity has its own bullish months.
    """
    signals = []
    current_month = datetime.now(timezone.utc).month

    for symbol, info in COMMODITY_SYMBOLS.items():
        seasonal_months = info.get("seasonal_bullish", [])
        if current_month not in seasonal_months:
            continue

        df = data.get(symbol)
        if df is None or len(df) < 50:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        price = float(close.iloc[-1])

        # Momentum confirmation: price above 20d SMA
        sma_20 = float(sma(close, 20).iloc[-1])
        if price < sma_20:
            continue

        # RSI filter: avoid overbought/oversold
        rsi_val = float(rsi(close, 14).iloc[-1])
        if rsi_val < 30 or rsi_val > 70:
            continue

        tp_mult = info.get("atr_mult_tp", 2.0)
        sl_mult = info.get("atr_mult_sl", 1.5)
        entry, tp, sl = _atr_tp_sl_commodity(close, high, low,
                                             tp_mult=tp_mult, sl_mult=sl_mult,
                                             direction="BUY")
        rr = (tp - entry) / (entry - sl) if entry > sl else 0
        if rr < 1.0:
            continue

        # Momentum strength
        mom_20d = (price / float(close.iloc[-20]) - 1) if len(close) >= 20 else 0
        conf = round(min(0.78, 0.55 + mom_20d * 3 + (0.03 if rsi_val < 50 else 0)), 2)
        conf = _commodity_confidence_cap(conf, "seasonal_momentum")

        signals.append({
            "strategy": "seasonal_momentum",
            "symbol": symbol, "category": "commodity",
            "signal_type": "BUY",
            "entry_price": round(entry, 4),
            "take_profit": round(tp, 4),
            "stop_loss": round(sl, 4),
            "confidence": conf,
            "risk_reward": round(rr, 2),
            "reason": (f"Seasonal bullish month ({current_month}) for {info['name']}, "
                       f"price above 20d SMA ({sma_20:.4f}), RSI={rsi_val:.1f}"),
            "timeframe": "1d",
            "max_hold_bars": 14,
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {
                "seasonal_months": seasonal_months,
                "current_month": current_month,
                "momentum_20d": round(mom_20d, 4),
                "sma_20": round(sma_20, 4),
                "reference": "Bodie & Rosansky (1980)",
            },
            "timestamp": _now_iso(),
        })
    return signals


# =========================================================================
# STRATEGY 2: Gold Safe Haven
# =========================================================================
# Gold as risk-off hedge: rallies when USD weakens and volatility rises.
# Reference: Baur & Lucey (2010), "Is Gold a Hedge or a Safe Haven?"
# =========================================================================

def gold_safe_haven(data: dict[str, pd.DataFrame]) -> list[dict]:
    """BUY gold when DXY weakens below 20d SMA AND VIX is elevated (>20).

    Gold has historically rallied during risk-off events when the dollar
    weakens simultaneously. Requires gold above 50d SMA for trend confirmation.
    """
    signals = []

    # Need DXY data
    dxy_df = data.get("DX-Y.N") or data.get("DXY")
    if dxy_df is None or len(dxy_df) < 50:
        return signals

    # Need VIX data
    vix_df = data.get("^VIX") or data.get("VIX")
    if vix_df is None or len(vix_df) < 20:
        return signals

    dxy_close = dxy_df["Close"]
    dxy_current = float(dxy_close.iloc[-1])
    dxy_sma_20 = float(sma(dxy_close, 20).iloc[-1])

    # DXY must be below 20d SMA (weakening dollar)
    if dxy_current >= dxy_sma_20:
        return signals

    # VIX must be above 20 (elevated volatility / risk-off)
    vix_current = float(vix_df["Close"].iloc[-1])
    if vix_current < 20:
        return signals

    # Trade gold
    symbol = "GC=F"
    info = COMMODITY_SYMBOLS.get(symbol)
    if info is None:
        return signals

    df = data.get(symbol)
    if df is None or len(df) < 50:
        return signals

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    price = float(close.iloc[-1])

    # Gold must be above 50d SMA (uptrend confirmation)
    sma_50 = float(sma(close, 50).iloc[-1])
    if price < sma_50:
        return signals

    rsi_val = float(rsi(close, 14).iloc[-1])
    if rsi_val > 80:
        return signals  # Already overbought

    entry, tp, sl = _atr_tp_sl_commodity(close, high, low,
                                         tp_mult=2.0, sl_mult=1.5,
                                         direction="BUY")
    rr = (tp - entry) / (entry - sl) if entry > sl else 0
    if rr < 1.0:
        return signals

    dxy_weakness = (dxy_sma_20 - dxy_current) / dxy_sma_20
    conf = round(min(0.80, 0.58 + dxy_weakness * 5 + (vix_current - 20) * 0.005), 2)
    conf = _commodity_confidence_cap(conf, "gold_safe_haven")

    signals.append({
        "strategy": "gold_safe_haven",
        "symbol": symbol, "category": "commodity",
        "signal_type": "BUY",
        "entry_price": round(entry, 4),
        "take_profit": round(tp, 4),
        "stop_loss": round(sl, 4),
        "confidence": conf,
        "risk_reward": round(rr, 2),
        "reason": (f"Safe haven: DXY={dxy_current:.2f} below 20d SMA ({dxy_sma_20:.2f}), "
                   f"VIX={vix_current:.1f}>20, gold above 50d SMA ({sma_50:.2f})"),
        "timeframe": "1d",
        "max_hold_bars": 14,
        "rsi_at_entry": round(rsi_val, 1),
        "extra": {
            "dxy_current": round(dxy_current, 2),
            "dxy_sma_20": round(dxy_sma_20, 2),
            "dxy_weakness_pct": round(dxy_weakness * 100, 2),
            "vix_current": round(vix_current, 1),
            "gold_sma_50": round(sma_50, 2),
            "reference": "Baur & Lucey (2010)",
        },
        "timestamp": _now_iso(),
    })
    return signals


# =========================================================================
# STRATEGY 3: Oil Inventory Momentum
# =========================================================================
# Crude oil momentum with volatility filter and Bollinger Band extremes.
# Reference: Gorton & Rouwenhorst (2006), "Facts and Fantasies about
# Commodity Futures".
# =========================================================================

def oil_inventory_momentum(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Trade crude oil oversold bounces and overbought fades using RSI + Bollinger Bands.

    BUY when RSI < 35 and price below lower Bollinger Band (oversold bounce).
    SELL when RSI > 65 and price above upper Bollinger Band (overbought fade).
    Requires ADX > 20 (trending market) to filter out choppy periods.
    """
    signals = []
    symbol = "CL=F"
    info = COMMODITY_SYMBOLS.get(symbol)
    if info is None:
        return signals

    df = data.get(symbol)
    if df is None or len(df) < 50:
        return signals

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    price = float(close.iloc[-1])

    # ADX trend strength filter
    adx_val = float(adx(high, low, close, 14).iloc[-1])
    if adx_val < 20:
        return signals

    rsi_val = float(rsi(close, 14).iloc[-1])
    bb = bollinger_bands(close, 20, 2.0)
    bb_upper = float(bb["upper"].iloc[-1])
    bb_lower = float(bb["lower"].iloc[-1])
    bb_mid = float(bb["middle"].iloc[-1])

    direction = None
    if rsi_val < 35 and price < bb_lower:
        direction = "BUY"
    elif rsi_val > 65 and price > bb_upper:
        direction = "SELL"

    if direction is None:
        return signals

    tp_mult = info.get("atr_mult_tp", 2.0)
    sl_mult = info.get("atr_mult_sl", 1.5)
    entry, tp, sl = _atr_tp_sl_commodity(close, high, low,
                                         tp_mult=tp_mult, sl_mult=sl_mult,
                                         direction=direction)
    if direction == "BUY":
        rr = (tp - entry) / (entry - sl) if entry > sl else 0
    else:
        rr = (entry - tp) / (sl - entry) if sl > entry else 0
    if rr < 1.0:
        return signals

    # Confidence based on extremity of RSI and BB deviation
    bb_deviation = abs(price - bb_mid) / (bb_upper - bb_lower) if (bb_upper - bb_lower) > 0 else 0
    conf = round(min(0.78, 0.55 + bb_deviation * 0.15 + adx_val * 0.002), 2)
    conf = _commodity_confidence_cap(conf, "oil_inventory_momentum")

    signals.append({
        "strategy": "oil_inventory_momentum",
        "symbol": symbol, "category": "commodity",
        "signal_type": direction,
        "entry_price": round(entry, 4),
        "take_profit": round(tp, 4),
        "stop_loss": round(sl, 4),
        "confidence": conf,
        "risk_reward": round(rr, 2),
        "reason": (f"Oil {'oversold bounce' if direction == 'BUY' else 'overbought fade'}: "
                   f"RSI={rsi_val:.1f}, price {'below' if direction == 'BUY' else 'above'} "
                   f"BB {'lower' if direction == 'BUY' else 'upper'} ({bb_lower:.2f}/{bb_upper:.2f}), "
                   f"ADX={adx_val:.1f}"),
        "timeframe": "1d",
        "max_hold_bars": 10,
        "rsi_at_entry": round(rsi_val, 1),
        "extra": {
            "adx": round(adx_val, 1),
            "bb_upper": round(bb_upper, 2),
            "bb_lower": round(bb_lower, 2),
            "bb_mid": round(bb_mid, 2),
            "bb_deviation": round(bb_deviation, 3),
            "reference": "Gorton & Rouwenhorst (2006)",
        },
        "timestamp": _now_iso(),
    })
    return signals


# =========================================================================
# STRATEGY 4: Metals Mean Reversion
# =========================================================================
# Gold, Silver, Platinum, Copper mean reversion to 100d SMA using z-scores.
# Reference: Erb & Harvey (2006), "The Strategic and Tactical Value of
# Commodity Futures".
# =========================================================================

_METALS = {"GC=F", "SI=F", "PL=F", "HG=F"}

def metals_mean_reversion(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Trade metals mean reversion to 100d SMA using z-score extremes.

    BUY when z-score < -1.5 (price far below 100d SMA).
    SELL when z-score > 1.5 (price far above 100d SMA).
    Confirmation: RSI divergence from price direction.
    """
    signals = []

    for symbol in _METALS:
        info = COMMODITY_SYMBOLS.get(symbol)
        if info is None:
            continue

        df = data.get(symbol)
        if df is None or len(df) < 120:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        price = float(close.iloc[-1])

        # Z-score of distance from 100d SMA
        sma_100 = sma(close, 100)
        z = zscore(close, 100)
        z_val = float(z.iloc[-1])

        rsi_val = float(rsi(close, 14).iloc[-1])
        sma_100_current = float(sma_100.iloc[-1])

        direction = None
        # Bullish: z < -1.5 and RSI shows some recovery (divergence)
        if z_val < -1.5 and rsi_val > 30:
            direction = "BUY"
        # Bearish: z > 1.5 and RSI shows weakening
        elif z_val > 1.5 and rsi_val < 70:
            direction = "SELL"

        if direction is None:
            continue

        tp_mult = info.get("atr_mult_tp", 2.0)
        sl_mult = info.get("atr_mult_sl", 1.5)
        entry, tp, sl = _atr_tp_sl_commodity(close, high, low,
                                             tp_mult=tp_mult, sl_mult=sl_mult,
                                             direction=direction)
        if direction == "BUY":
            rr = (tp - entry) / (entry - sl) if entry > sl else 0
        else:
            rr = (entry - tp) / (sl - entry) if sl > entry else 0
        if rr < 1.0:
            continue

        conf = round(min(0.78, 0.55 + abs(z_val) * 0.08), 2)
        conf = _commodity_confidence_cap(conf, "metals_mean_reversion")

        signals.append({
            "strategy": "metals_mean_reversion",
            "symbol": symbol, "category": "commodity",
            "signal_type": direction,
            "entry_price": round(entry, 4),
            "take_profit": round(tp, 4),
            "stop_loss": round(sl, 4),
            "confidence": conf,
            "risk_reward": round(rr, 2),
            "reason": (f"{info['name']} mean reversion: z-score={z_val:.2f}, "
                       f"100d SMA={sma_100_current:.2f}, RSI={rsi_val:.1f}"),
            "timeframe": "1d",
            "max_hold_bars": 14,
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {
                "z_score": round(z_val, 3),
                "sma_100": round(sma_100_current, 4),
                "distance_pct": round((price - sma_100_current) / sma_100_current * 100, 2),
                "reference": "Erb & Harvey (2006)",
            },
            "timestamp": _now_iso(),
        })
    return signals


# =========================================================================
# STRATEGY 5: Agricultural Spread
# =========================================================================
# Corn/Wheat/Soybean spread relationships. Agricultural spreads are
# well-documented as mean-reverting due to substitution effects.
# Reference: Fama & French (1987), "Commodity Futures Prices".
# =========================================================================

_AG_SPREADS = [
    ("ZC=F", "ZW=F", "corn_wheat"),      # Corn/Wheat ratio
    ("ZS=F", "ZC=F", "soybean_corn"),     # Soybean/Corn ratio
]

def agricultural_spread(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Trade mean-reverting agricultural commodity spreads.

    When corn/wheat ratio or soybean/corn ratio deviates >1.5 std
    from the 60d rolling mean, trade the reversion.
    """
    signals = []

    for sym_a, sym_b, spread_name in _AG_SPREADS:
        info_a = COMMODITY_SYMBOLS.get(sym_a)
        info_b = COMMODITY_SYMBOLS.get(sym_b)
        if info_a is None or info_b is None:
            continue

        df_a = data.get(sym_a)
        df_b = data.get(sym_b)
        if df_a is None or df_b is None:
            continue
        if len(df_a) < 80 or len(df_b) < 80:
            continue

        close_a = df_a["Close"]
        close_b = df_b["Close"]

        # Align lengths
        min_len = min(len(close_a), len(close_b))
        close_a = close_a.iloc[-min_len:]
        close_b = close_b.iloc[-min_len:]

        # Compute spread ratio
        ratio = close_a / close_b
        ratio = ratio.dropna()
        if len(ratio) < 80:
            continue

        # Z-score of ratio vs 60d rolling mean
        z_val_series = zscore(ratio, 60)
        z_val = float(z_val_series.iloc[-1])

        price_a = float(close_a.iloc[-1])
        price_b = float(close_b.iloc[-1])
        current_ratio = price_a / price_b if price_b != 0 else 0
        ratio_mean = float(ratio.iloc[-60:].mean())

        # Determine trade direction
        # z > 1.5: ratio is high -> sell A, buy B (ratio reverts down)
        # z < -1.5: ratio is low -> buy A, sell B (ratio reverts up)
        if abs(z_val) < 1.5:
            continue

        if z_val > 1.5:
            # Ratio too high -- sell the numerator (A), or BUY the denominator (B)
            trade_symbol = sym_b
            trade_info = info_b
            trade_df = df_b
            direction = "BUY"
            reason_detail = f"{spread_name} ratio={current_ratio:.3f} HIGH (z={z_val:.2f}), mean={ratio_mean:.3f}"
        else:
            # Ratio too low -- buy the numerator (A)
            trade_symbol = sym_a
            trade_info = info_a
            trade_df = df_a
            direction = "BUY"
            reason_detail = f"{spread_name} ratio={current_ratio:.3f} LOW (z={z_val:.2f}), mean={ratio_mean:.3f}"

        trade_close = trade_df["Close"]
        trade_high = trade_df["High"]
        trade_low = trade_df["Low"]

        rsi_val = float(rsi(trade_close, 14).iloc[-1])

        tp_mult = trade_info.get("atr_mult_tp", 2.0)
        sl_mult = trade_info.get("atr_mult_sl", 1.5)
        entry, tp, sl = _atr_tp_sl_commodity(trade_close, trade_high, trade_low,
                                             tp_mult=tp_mult, sl_mult=sl_mult,
                                             direction=direction)
        rr = (tp - entry) / (entry - sl) if entry > sl else 0
        if rr < 1.0:
            continue

        conf = round(min(0.76, 0.52 + abs(z_val) * 0.08), 2)
        conf = _commodity_confidence_cap(conf, "agricultural_spread")

        signals.append({
            "strategy": "agricultural_spread",
            "symbol": trade_symbol, "category": "commodity",
            "signal_type": direction,
            "entry_price": round(entry, 4),
            "take_profit": round(tp, 4),
            "stop_loss": round(sl, 4),
            "confidence": conf,
            "risk_reward": round(rr, 2),
            "reason": f"Ag spread reversion: {reason_detail}",
            "timeframe": "1d",
            "max_hold_bars": 14,
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {
                "spread_name": spread_name,
                "z_score": round(z_val, 3),
                "current_ratio": round(current_ratio, 4),
                "ratio_60d_mean": round(ratio_mean, 4),
                "sym_a": sym_a,
                "sym_b": sym_b,
                "reference": "Fama & French (1987)",
            },
            "timestamp": _now_iso(),
        })
    return signals


# =========================================================================
# STRATEGY 6: Energy Momentum Breakout
# =========================================================================
# Oil, Natural Gas, Copper breakout above/below 20-day extremes.
# Volume confirmation + ADX trend strength filter.
# =========================================================================

_ENERGY_SYMBOLS = {"CL=F", "NG=F", "HG=F"}

def energy_momentum_breakout(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Trade 20-day high/low breakouts on energy commodities with volume confirmation.

    BUY on breakout above 20d high with volume > 1.5x average.
    SELL on breakdown below 20d low with volume > 1.5x average.
    ADX > 25 confirms trend strength. Wider stops for natural gas.
    """
    signals = []

    for symbol in _ENERGY_SYMBOLS:
        info = COMMODITY_SYMBOLS.get(symbol)
        if info is None:
            continue

        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        vol = df.get("Volume")
        price = float(close.iloc[-1])

        # ADX trend strength
        adx_val = float(adx(high, low, close, 14).iloc[-1])
        if adx_val < 25:
            continue

        # Volume confirmation
        if vol is not None and len(vol) > 20:
            vr = float(volume_ratio(vol, 20).iloc[-1])
            if vr < 1.5:
                continue
        else:
            vr = 1.5  # No volume data, skip filter

        # 20-day high/low breakout
        high_20d = float(high.iloc[-21:-1].max())
        low_20d = float(low.iloc[-21:-1].min())

        direction = None
        if price > high_20d:
            direction = "BUY"
        elif price < low_20d:
            direction = "SELL"

        if direction is None:
            continue

        rsi_val = float(rsi(close, 14).iloc[-1])

        tp_mult = info.get("atr_mult_tp", 2.0)
        sl_mult = info.get("atr_mult_sl", 1.5)
        # Wider stops for natgas (more volatile)
        if symbol == "NG=F":
            tp_mult = max(tp_mult, 3.0)
            sl_mult = max(sl_mult, 2.0)

        entry, tp, sl = _atr_tp_sl_commodity(close, high, low,
                                             tp_mult=tp_mult, sl_mult=sl_mult,
                                             direction=direction)
        if direction == "BUY":
            rr = (tp - entry) / (entry - sl) if entry > sl else 0
        else:
            rr = (entry - tp) / (sl - entry) if sl > entry else 0
        if rr < 1.0:
            continue

        conf = round(min(0.76, 0.55 + adx_val * 0.003 + (vr - 1.5) * 0.05), 2)
        conf = _commodity_confidence_cap(conf, "energy_momentum_breakout")

        signals.append({
            "strategy": "energy_momentum_breakout",
            "symbol": symbol, "category": "commodity",
            "signal_type": direction,
            "entry_price": round(entry, 4),
            "take_profit": round(tp, 4),
            "stop_loss": round(sl, 4),
            "confidence": conf,
            "risk_reward": round(rr, 2),
            "reason": (f"{info['name']} {direction} breakout: price {'above 20d high' if direction == 'BUY' else 'below 20d low'} "
                       f"({high_20d:.2f}/{low_20d:.2f}), ADX={adx_val:.1f}, vol_ratio={vr:.2f}"),
            "timeframe": "1d",
            "max_hold_bars": 10,
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {
                "adx": round(adx_val, 1),
                "volume_ratio": round(vr, 2),
                "high_20d": round(high_20d, 4),
                "low_20d": round(low_20d, 4),
            },
            "timestamp": _now_iso(),
        })
    return signals


# =========================================================================
# STRATEGY 7: Commodity RSI Divergence
# =========================================================================
# RSI divergence on all commodities. Works well due to strong trend-reversal
# patterns in commodity markets driven by inventory/supply cycles.
# =========================================================================

def commodity_rsi_divergence(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Trade RSI divergences on all commodities.

    Bullish divergence: price makes lower low but RSI makes higher low.
    Bearish divergence: price makes higher high but RSI makes lower high.
    Uses 14-period RSI on daily timeframe with 20-bar lookback for pivots.
    """
    signals = []
    lookback = 20

    for symbol, info in COMMODITY_SYMBOLS.items():
        df = data.get(symbol)
        if df is None or len(df) < 50:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        price = float(close.iloc[-1])

        rsi_series = rsi(close, 14)
        rsi_val = float(rsi_series.iloc[-1])

        # Recent price and RSI pivots (last lookback bars)
        recent_close = close.iloc[-lookback:]
        recent_rsi = rsi_series.iloc[-lookback:]

        if len(recent_close) < lookback or len(recent_rsi) < lookback:
            continue

        # Split into two halves to find divergence
        half = lookback // 2
        first_half_close = recent_close.iloc[:half]
        second_half_close = recent_close.iloc[half:]
        first_half_rsi = recent_rsi.iloc[:half]
        second_half_rsi = recent_rsi.iloc[half:]

        price_low_1 = float(first_half_close.min())
        price_low_2 = float(second_half_close.min())
        rsi_low_1 = float(first_half_rsi.min())
        rsi_low_2 = float(second_half_rsi.min())

        price_high_1 = float(first_half_close.max())
        price_high_2 = float(second_half_close.max())
        rsi_high_1 = float(first_half_rsi.max())
        rsi_high_2 = float(second_half_rsi.max())

        direction = None
        div_type = ""

        # Bullish divergence: lower low in price, higher low in RSI
        if price_low_2 < price_low_1 and rsi_low_2 > rsi_low_1 and rsi_val < 45:
            direction = "BUY"
            div_type = "bullish"
        # Bearish divergence: higher high in price, lower high in RSI
        elif price_high_2 > price_high_1 and rsi_high_2 < rsi_high_1 and rsi_val > 55:
            direction = "SELL"
            div_type = "bearish"

        if direction is None:
            continue

        tp_mult = info.get("atr_mult_tp", 2.0)
        sl_mult = info.get("atr_mult_sl", 1.5)
        entry, tp, sl = _atr_tp_sl_commodity(close, high, low,
                                             tp_mult=tp_mult, sl_mult=sl_mult,
                                             direction=direction)
        if direction == "BUY":
            rr = (tp - entry) / (entry - sl) if entry > sl else 0
        else:
            rr = (entry - tp) / (sl - entry) if sl > entry else 0
        if rr < 1.0:
            continue

        # Stronger divergence = higher confidence
        if direction == "BUY":
            div_strength = (rsi_low_2 - rsi_low_1) / max(abs(rsi_low_1), 1)
        else:
            div_strength = (rsi_high_1 - rsi_high_2) / max(abs(rsi_high_1), 1)
        conf = round(min(0.76, 0.54 + div_strength * 0.5), 2)
        conf = _commodity_confidence_cap(conf, "commodity_rsi_divergence")

        signals.append({
            "strategy": "commodity_rsi_divergence",
            "symbol": symbol, "category": "commodity",
            "signal_type": direction,
            "entry_price": round(entry, 4),
            "take_profit": round(tp, 4),
            "stop_loss": round(sl, 4),
            "confidence": conf,
            "risk_reward": round(rr, 2),
            "reason": (f"{info['name']} {div_type} RSI divergence: "
                       f"price {'lower low' if direction == 'BUY' else 'higher high'} "
                       f"but RSI {'higher low' if direction == 'BUY' else 'lower high'}, "
                       f"RSI={rsi_val:.1f}"),
            "timeframe": "1d",
            "max_hold_bars": 10,
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {
                "divergence_type": div_type,
                "div_strength": round(div_strength, 3),
                "price_pivot_1": round(price_low_1 if direction == "BUY" else price_high_1, 4),
                "price_pivot_2": round(price_low_2 if direction == "BUY" else price_high_2, 4),
                "rsi_pivot_1": round(rsi_low_1 if direction == "BUY" else rsi_high_1, 1),
                "rsi_pivot_2": round(rsi_low_2 if direction == "BUY" else rsi_high_2, 1),
            },
            "timestamp": _now_iso(),
        })
    return signals


# =========================================================================
# STRATEGY 8: DXY Inverse Commodities
# =========================================================================
# Dollar-denominated commodities have inverse correlation with USD.
# When DXY breaks support, commodities tend to rally and vice versa.
# Reference: Akram (2009), "Commodity Prices, Interest Rates and the Dollar".
# =========================================================================

_DXY_INVERSE_SYMBOLS = {"GC=F", "SI=F", "CL=F", "HG=F"}

def dxy_inverse_commodities(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Trade commodities based on DXY breakdowns/breakouts.

    When DXY breaks below 20d low (support break), BUY commodities.
    When DXY breaks above 20d high (resistance break), SELL commodities.
    Applies to Gold, Silver, Oil, Copper (strongest inverse correlation).
    """
    signals = []

    # Need DXY data
    dxy_df = data.get("DX-Y.N") or data.get("DXY")
    if dxy_df is None or len(dxy_df) < 30:
        return signals

    dxy_close = dxy_df["Close"]
    dxy_price = float(dxy_close.iloc[-1])

    # DXY 20-day high/low
    dxy_high_20d = float(dxy_close.iloc[-21:-1].max())
    dxy_low_20d = float(dxy_close.iloc[-21:-1].min())

    # Determine commodity direction based on DXY
    commodity_direction = None
    dxy_signal = ""
    if dxy_price < dxy_low_20d:
        commodity_direction = "BUY"
        dxy_signal = f"DXY broke below 20d low ({dxy_low_20d:.2f})"
    elif dxy_price > dxy_high_20d:
        commodity_direction = "SELL"
        dxy_signal = f"DXY broke above 20d high ({dxy_high_20d:.2f})"

    if commodity_direction is None:
        return signals

    for symbol in _DXY_INVERSE_SYMBOLS:
        info = COMMODITY_SYMBOLS.get(symbol)
        if info is None:
            continue

        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        rsi_val = float(rsi(close, 14).iloc[-1])

        # Don't fight extreme RSI
        if commodity_direction == "BUY" and rsi_val > 75:
            continue
        if commodity_direction == "SELL" and rsi_val < 25:
            continue

        tp_mult = info.get("atr_mult_tp", 2.0)
        sl_mult = info.get("atr_mult_sl", 1.5)
        entry, tp, sl = _atr_tp_sl_commodity(close, high, low,
                                             tp_mult=tp_mult, sl_mult=sl_mult,
                                             direction=commodity_direction)
        if commodity_direction == "BUY":
            rr = (tp - entry) / (entry - sl) if entry > sl else 0
        else:
            rr = (entry - tp) / (sl - entry) if sl > entry else 0
        if rr < 1.0:
            continue

        dxy_deviation = abs(dxy_price - (dxy_high_20d if commodity_direction == "SELL" else dxy_low_20d))
        dxy_deviation_pct = dxy_deviation / dxy_price if dxy_price > 0 else 0
        conf = round(min(0.76, 0.54 + dxy_deviation_pct * 20), 2)
        conf = _commodity_confidence_cap(conf, "dxy_inverse_commodities")

        signals.append({
            "strategy": "dxy_inverse_commodities",
            "symbol": symbol, "category": "commodity",
            "signal_type": commodity_direction,
            "entry_price": round(entry, 4),
            "take_profit": round(tp, 4),
            "stop_loss": round(sl, 4),
            "confidence": conf,
            "risk_reward": round(rr, 2),
            "reason": (f"{info['name']} {commodity_direction} on USD weakness: "
                       f"{dxy_signal}, DXY={dxy_price:.2f}, RSI={rsi_val:.1f}"),
            "timeframe": "1d",
            "max_hold_bars": 14,
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {
                "dxy_price": round(dxy_price, 2),
                "dxy_high_20d": round(dxy_high_20d, 2),
                "dxy_low_20d": round(dxy_low_20d, 2),
                "dxy_deviation_pct": round(dxy_deviation_pct * 100, 2),
                "reference": "Akram (2009)",
            },
            "timestamp": _now_iso(),
        })
    return signals


# =========================================================================
# STRATEGY 9: Time-Series Momentum (12-month)
# =========================================================================
# Cross-sectional time-series momentum (TSMOM) on commodity futures.
# Long if trailing 12-month return > 0, short if < 0.  Vol-targeted sizing
# (40% annualized vol target) scales confidence by realized 60d vol.
# Hold ~1 month (21 bars) or until r12 sign flips.
# Reference: Moskowitz, Ooi & Pedersen (2012), "Time Series Momentum",
# Journal of Financial Economics 104(2):228-250.  Diversified TSMOM
# Sharpe ~1.4; commodity sleeve standalone Sharpe ~0.5-0.7.
# =========================================================================

# Symbols where 12m momentum is most persistent per Moskowitz et al. (2012).
_TSMOM_BEST_SYMBOLS = {"CL=F", "GC=F", "HG=F", "ZC=F"}


def commodity_tsmom_12m(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Time-Series Momentum (12-month) on commodity futures.

    Entry: r12 = close.pct_change(252).  r12 > 0 -> BUY, r12 < 0 -> SELL.
    Sizing: vol-targeted to 40% annualized using realized 60d vol.
    Exit: 21 trading days hold (~1 month) or until r12 sign flips.
    TP/SL: 2.5x ATR(14) / 1.5x ATR(14) (capped by commodity TP/SL caps).
    """
    signals = []

    for symbol, info in COMMODITY_SYMBOLS.items():
        if info is None:
            info = {"name": symbol}

        df = data.get(symbol)
        if df is None or len(df) < 252:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        price = float(close.iloc[-1])

        # 12-month (252 trading day) return
        r12_series = close.pct_change(252)
        r12 = float(r12_series.iloc[-1])
        if not np.isfinite(r12) or r12 == 0.0:
            continue

        # Realized 60d vol (annualized)
        daily_returns = close.pct_change()
        if len(daily_returns.dropna()) < 60:
            continue
        realized_vol_60d = float(daily_returns.rolling(60).std().iloc[-1] * np.sqrt(252))
        if not np.isfinite(realized_vol_60d) or realized_vol_60d <= 0:
            continue

        direction = "BUY" if r12 > 0 else "SELL"

        # Vol-targeted size (40% target).  Used to scale confidence only --
        # actual position sizing is handled downstream.
        target_vol = 0.40
        size_scalar = min(target_vol / realized_vol_60d, 1.0)

        entry, tp, sl = _atr_tp_sl_commodity(
            close, high, low,
            tp_mult=2.5, sl_mult=1.5,
            direction=direction,
        )
        if direction == "BUY":
            rr = (tp - entry) / (entry - sl) if entry > sl else 0
        else:
            rr = (entry - tp) / (sl - entry) if sl > entry else 0
        if rr < 1.0:
            continue

        rsi_val = float(rsi(close, 14).iloc[-1])

        # Confidence: base + momentum strength + vol component
        vol_score = min(target_vol / realized_vol_60d, 1.0)
        mom_score = min(abs(r12) * 5, 1.0)
        confidence = 0.55 + (mom_score * 0.15) + (vol_score * 0.10)
        # Bonus for the 4 most persistent commodities per Moskowitz
        if symbol in _TSMOM_BEST_SYMBOLS:
            confidence += 0.02
        conf = round(min(0.80, confidence), 2)
        conf = _commodity_confidence_cap(conf, "commodity_tsmom_12m")

        commodity_name = info.get("name", symbol)

        signals.append({
            "strategy": "commodity_tsmom_12m",
            "symbol": symbol, "category": "commodity",
            "signal_type": direction,
            "entry_price": round(entry, 4),
            "take_profit": round(tp, 4),
            "stop_loss": round(sl, 4),
            "confidence": conf,
            "risk_reward": round(rr, 2),
            "reason": (
                f"TSMOM 12m {direction} on {commodity_name}: r12={r12*100:.2f}%, "
                f"realized_vol_60d={realized_vol_60d*100:.1f}% (target 40%), "
                f"size_scalar={size_scalar:.2f}, RSI={rsi_val:.1f}"
            ),
            "timeframe": "1d",
            # ~1 month hold per Moskowitz et al.; signal also exits if r12 flips.
            "max_hold_bars": 21,
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {
                "r12": round(r12, 4),
                "realized_vol_60d": round(realized_vol_60d, 4),
                "vol_target": target_vol,
                "size_scalar": round(size_scalar, 3),
                "mom_score": round(mom_score, 3),
                "vol_score": round(vol_score, 3),
                "is_best_symbol": symbol in _TSMOM_BEST_SYMBOLS,
                "reference": "Moskowitz, Ooi & Pedersen (2012), JFE 104(2):228-250",
            },
            "timestamp": _now_iso(),
        })
    return signals


# =========================================================================
# Collector -- all commodity strategies
# =========================================================================

def collect_commodity_signals(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Run all commodity strategies and return combined signals."""
    # Defensive import of pre-emission policy gates. Fail-open if broken.
    try:
        from alpha_engine.non_crypto_policy import passes_non_crypto_policy
        _policy_available = True
    except Exception:
        _policy_available = False

    all_signals: list[dict] = []
    strategies = [
        seasonal_momentum, gold_safe_haven, oil_inventory_momentum,
        metals_mean_reversion, agricultural_spread, energy_momentum_breakout,
        commodity_rsi_divergence, dxy_inverse_commodities,
        commodity_tsmom_12m,
    ]
    for func in strategies:
        try:
            signals = func(data)
        except Exception as e:
            print(f"  [WARN] {func.__name__} failed: {e}")
            continue

        for sig in signals:
            # Emissions here only carry `category='commodity'`; inject the
            # uppercase `asset_class` the policy gate expects.
            if not sig.get("asset_class"):
                sig["asset_class"] = "COMMODITY"

            if _policy_available:
                try:
                    ok, reason = passes_non_crypto_policy(sig)
                    if not ok:
                        print(f"  [POLICY] Blocked {sig.get('symbol')} "
                              f"via {func.__name__}: {reason}")
                        continue
                except Exception:
                    # Fail-open on unexpected gate errors.
                    pass

            all_signals.append(sig)
    return all_signals


# =========================================================================
# Registry -- all commodity strategies
# =========================================================================

COMMODITY_STRATEGIES = {
    "seasonal_momentum":         seasonal_momentum,
    "gold_safe_haven":           gold_safe_haven,
    "oil_inventory_momentum":    oil_inventory_momentum,
    "metals_mean_reversion":     metals_mean_reversion,
    "agricultural_spread":       agricultural_spread,
    "energy_momentum_breakout":  energy_momentum_breakout,
    "commodity_rsi_divergence":  commodity_rsi_divergence,
    "dxy_inverse_commodities":   dxy_inverse_commodities,
    "commodity_tsmom_12m":       commodity_tsmom_12m,
}
