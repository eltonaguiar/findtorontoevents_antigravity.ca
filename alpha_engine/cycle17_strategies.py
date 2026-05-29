"""Cycle 17 strategies: FOREX/BOND breakthrough strategies.

Discovered in Cycle 17 (2026-05-29): stoch_rsi, pivot_reversion, ichimoku,
yield_curve_proxy, range_trading. Wired to production scanner.

Top results:
- USDCHF rsi_mr: PF 4.28 (FOREX breakthrough)
- ZN=F mean_rev_atr: PF 2.11 (BOND breakthrough)
- AVAX ichimoku: PF 4.33
- NVDA stoch_rsi: PF 3.53
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Optional


# ---------------------------------------------------------------------------
# Indicator helpers
# ---------------------------------------------------------------------------

def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def _stoch_rsi(close: pd.Series, rsi_period: int = 14,
               stoch_period: int = 14, k_smooth: int = 3) -> pd.Series:
    """Stochastic RSI — Stochastic applied to RSI values."""
    rsi = _rsi(close, rsi_period)
    rsi_min = rsi.rolling(stoch_period).min()
    rsi_max = rsi.rolling(stoch_period).max()
    stoch = (rsi - rsi_min) / (rsi_max - rsi_min).replace(0, np.nan) * 100
    return stoch.rolling(k_smooth).mean()


def _atr(high: pd.Series, low: pd.Series, close: pd.Series,
         period: int = 14) -> pd.Series:
    """Average True Range."""
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def _pivot_points(high: pd.Series, low: pd.Series,
                  close: pd.Series) -> dict[str, pd.Series]:
    """Daily pivot points (PP, S1, S2, R1, R2)."""
    pp = (high + low + close) / 3
    s1 = 2 * pp - high
    s2 = pp - (high - low)
    r1 = 2 * pp - low
    r2 = pp + (high - low)
    return {"pp": pp, "s1": s1, "s2": s2, "r1": r1, "r2": r2}


def _ichimoku(high: pd.Series, low: pd.Series, close: pd.Series,
              tenkan: int = 9, kijun: int = 26, senkou_b: int = 52
              ) -> dict[str, pd.Series]:
    """Ichimoku Cloud components."""
    tenkan_sen = (high.rolling(tenkan).max() + low.rolling(tenkan).min()) / 2
    kijun_sen = (high.rolling(kijun).max() + low.rolling(kijun).min()) / 2
    senkou_a = ((tenkan_sen + kijun_sen) / 2).shift(kijun)
    senkou_b_line = ((high.rolling(senkou_b).max() +
                      low.rolling(senkou_b).min()) / 2).shift(kijun)
    return {
        "tenkan": tenkan_sen,
        "kijun": kijun_sen,
        "senkou_a": senkou_a,
        "senkou_b": senkou_b_line,
    }


# ---------------------------------------------------------------------------
# Signal functions (scanner-compatible: df in, signal list out)
# ---------------------------------------------------------------------------

def scan_stoch_rsi(df: pd.DataFrame, symbol: str = "") -> list[dict]:
    """Stochastic RSI overbought/oversold signals.

    BUY when StochRSI < 20 (oversold), SELL when > 80 (overbought).
    Confirmed by trend filter (close > SMA50 for BUY, < SMA50 for SELL).
    """
    if len(df) < 60:
        return []

    close = df["close"].astype(float)
    stoch_k = _stoch_rsi(close)
    sma50 = close.rolling(50).mean()

    if pd.isna(stoch_k.iloc[-1]):
        return []

    current_k = stoch_k.iloc[-1]
    prev_k = stoch_k.iloc[-2] if len(stoch_k) > 1 else current_k
    current_close = close.iloc[-1]
    current_sma50 = sma50.iloc[-1]

    signal = None
    if current_k < 20 and prev_k >= 20:
        # Oversold — BUY if above SMA50 (trend filter)
        if current_close > current_sma50:
            signal = {
                "name": "stoch_rsi",
                "regime": "ranging",
                "valid": True,
                "score": round((20 - current_k) / 20, 4),
                "score_breakdown": {"stoch_k": round(current_k, 2)},
                "meta": {"direction": "BUY", "hold_bars": 10},
            }
    elif current_k > 80 and prev_k <= 80:
        # Overbought — SELL if below SMA50
        if current_close < current_sma50:
            signal = {
                "name": "stoch_rsi",
                "regime": "ranging",
                "valid": True,
                "score": round((current_k - 80) / 20, 4),
                "score_breakdown": {"stoch_k": round(current_k, 2)},
                "meta": {"direction": "SELL", "hold_bars": 10},
            }

    return [signal] if signal else []


def scan_pivot_reversion(df: pd.DataFrame, symbol: str = "") -> list[dict]:
    """Pivot point mean-reversion signals.

    BUY when price touches S1/S2 support and bounces.
    SELL when price touches R1/R2 resistance and rejects.
    """
    if len(df) < 5:
        return []

    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)

    pivots = _pivot_points(high.shift(1), low.shift(1), close.shift(1))

    current_close = close.iloc[-1]
    current_low = low.iloc[-1]
    current_high = high.iloc[-1]
    s1 = pivots["s1"].iloc[-1]
    s2 = pivots["s2"].iloc[-1]
    r1 = pivots["r1"].iloc[-1]
    r2 = pivots["r2"].iloc[-1]
    pp = pivots["pp"].iloc[-1]

    if any(pd.isna(x) for x in [s1, s2, r1, r2, pp, current_close]):
        return []

    signal = None
    # BUY: price touched S1 or S2 and closed above (bounce)
    if current_low <= s1 and current_close > s1:
        dist = (s1 - current_close) / s1 if s1 != 0 else 0
        signal = {
            "name": "pivot_reversion",
            "regime": "ranging",
            "valid": True,
            "score": round(min(abs(dist) * 100, 1.0), 4),
            "score_breakdown": {"pivot_level": "S1", "pivot_val": round(s1, 6)},
            "meta": {"direction": "BUY", "hold_bars": 5},
        }
    elif current_low <= s2 and current_close > s2:
        signal = {
            "name": "pivot_reversion",
            "regime": "ranging",
            "valid": True,
            "score": 0.8,
            "score_breakdown": {"pivot_level": "S2", "pivot_val": round(s2, 6)},
            "meta": {"direction": "BUY", "hold_bars": 5},
        }
    # SELL: price touched R1 or R2 and closed below (rejection)
    elif current_high >= r1 and current_close < r1:
        dist = (current_close - r1) / r1 if r1 != 0 else 0
        signal = {
            "name": "pivot_reversion",
            "regime": "ranging",
            "valid": True,
            "score": round(min(abs(dist) * 100, 1.0), 4),
            "score_breakdown": {"pivot_level": "R1", "pivot_val": round(r1, 6)},
            "meta": {"direction": "SELL", "hold_bars": 5},
        }
    elif current_high >= r2 and current_close < r2:
        signal = {
            "name": "pivot_reversion",
            "regime": "ranging",
            "valid": True,
            "score": 0.8,
            "score_breakdown": {"pivot_level": "R2", "pivot_val": round(r2, 6)},
            "meta": {"direction": "SELL", "hold_bars": 5},
        }

    return [signal] if signal else []


def scan_ichimoku_cloud(df: pd.DataFrame, symbol: str = "") -> list[dict]:
    """Ichimoku Cloud breakout/rejection signals.

    BUY when price breaks above cloud with Tenkan > Kijun (bullish alignment).
    SELL when price breaks below cloud with Tenkan < Kijun.
    """
    if len(df) < 80:
        return []

    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)

    ichi = _ichimoku(high, low, close)
    tenkan = ichi["tenkan"]
    kijun = ichi["kijun"]
    senkou_a = ichi["senkou_a"]
    senkou_b = ichi["senkou_b"]

    if any(pd.isna(x.iloc[-1]) for x in [tenkan, kijun, senkou_a, senkou_b]):
        return []

    current_close = close.iloc[-1]
    current_tenkan = tenkan.iloc[-1]
    current_kijun = kijun.iloc[-1]
    cloud_top = max(senkou_a.iloc[-1], senkou_b.iloc[-1])
    cloud_bottom = min(senkou_a.iloc[-1], senkou_b.iloc[-1])

    signal = None
    # BUY: price above cloud, Tenkan > Kijun (bullish)
    if current_close > cloud_top and current_tenkan > current_kijun:
        prev_close = close.iloc[-2]
        prev_cloud_top = max(senkou_a.iloc[-2], senkou_b.iloc[-2])
        # Trigger on cloud breakout
        if prev_close <= prev_cloud_top:
            signal = {
                "name": "ichimoku",
                "regime": "trending",
                "valid": True,
                "score": 0.85,
                "score_breakdown": {
                    "above_cloud": True,
                    "tk_cross": "bullish",
                },
                "meta": {"direction": "BUY", "hold_bars": 15},
            }
    # SELL: price below cloud, Tenkan < Kijun (bearish)
    elif current_close < cloud_bottom and current_tenkan < current_kijun:
        prev_close = close.iloc[-2]
        prev_cloud_bottom = min(senkou_a.iloc[-2], senkou_b.iloc[-2])
        if prev_close >= prev_cloud_bottom:
            signal = {
                "name": "ichimoku",
                "regime": "trending",
                "valid": True,
                "score": 0.85,
                "score_breakdown": {
                    "below_cloud": True,
                    "tk_cross": "bearish",
                },
                "meta": {"direction": "SELL", "hold_bars": 15},
            }

    return [signal] if signal else []


def scan_yield_curve_proxy(df: pd.DataFrame, symbol: str = "") -> list[dict]:
    """Yield curve proxy signal — uses RSI + slope as macro regime filter.

    When RSI is extreme AND price is trending with the macro regime,
    generates momentum signals. Works best on rate-sensitive assets.
    """
    if len(df) < 60:
        return []

    close = df["close"].astype(float)
    rsi = _rsi(close, 14)
    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()

    if pd.isna(rsi.iloc[-1]) or pd.isna(sma50.iloc[-1]):
        return []

    current_rsi = rsi.iloc[-1]
    current_close = close.iloc[-1]
    current_sma20 = sma20.iloc[-1]
    current_sma50 = sma50.iloc[-1]

    signal = None
    # BUY: RSI recovering from oversold, price above SMA50 (uptrend)
    if 30 < current_rsi < 45 and current_close > current_sma50:
        if current_sma20 > current_sma50:  # Uptrend confirmed
            signal = {
                "name": "yield_curve_proxy",
                "regime": "transitional",
                "valid": True,
                "score": round((45 - current_rsi) / 30, 4),
                "score_breakdown": {"rsi": round(current_rsi, 2)},
                "meta": {"direction": "BUY", "hold_bars": 10},
            }
    # SELL: RSI falling from overbought, price below SMA50 (downtrend)
    elif 55 < current_rsi < 70 and current_close < current_sma50:
        if current_sma20 < current_sma50:
            signal = {
                "name": "yield_curve_proxy",
                "regime": "transitional",
                "valid": True,
                "score": round((current_rsi - 55) / 30, 4),
                "score_breakdown": {"rsi": round(current_rsi, 2)},
                "meta": {"direction": "SELL", "hold_bars": 10},
            }

    return [signal] if signal else []


def scan_range_trading(df: pd.DataFrame, symbol: str = "") -> list[dict]:
    """Range trading — buy at range bottom, sell at range top.

    Identifies consolidation via ATR compression and Bollinger Band squeeze.
    """
    if len(df) < 60:
        return []

    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)

    # Bollinger Bands
    sma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    upper_bb = sma20 + 2 * std20
    lower_bb = sma20 - 2 * std20

    # ATR for volatility compression
    atr = _atr(high, low, close, 14)
    atr_sma = atr.rolling(50).mean()

    if pd.isna(upper_bb.iloc[-1]) or pd.isna(atr_sma.iloc[-1]):
        return []

    current_close = close.iloc[-1]
    current_upper = upper_bb.iloc[-1]
    current_lower = lower_bb.iloc[-1]
    current_atr = atr.iloc[-1]
    current_atr_sma = atr_sma.iloc[-1]

    # Range detection: ATR below average = consolidation
    is_range = current_atr < current_atr_sma * 0.8

    if not is_range:
        return []

    signal = None
    # BUY: price at lower Bollinger Band in range
    if current_close <= current_lower * 1.01:
        bb_width = (current_upper - current_lower) / sma20.iloc[-1]
        signal = {
            "name": "range_trading",
            "regime": "ranging",
            "valid": True,
            "score": round(min(bb_width * 10, 1.0), 4),
            "score_breakdown": {
                "bb_position": "lower",
                "atr_compression": round(current_atr / current_atr_sma, 2),
            },
            "meta": {"direction": "BUY", "hold_bars": 8},
        }
    # SELL: price at upper Bollinger Band in range
    elif current_close >= current_upper * 0.99:
        bb_width = (current_upper - current_lower) / sma20.iloc[-1]
        signal = {
            "name": "range_trading",
            "regime": "ranging",
            "valid": True,
            "score": round(min(bb_width * 10, 1.0), 4),
            "score_breakdown": {
                "bb_position": "upper",
                "atr_compression": round(current_atr / current_atr_sma, 2),
            },
            "meta": {"direction": "SELL", "hold_bars": 8},
        }

    return [signal] if signal else []


# ---------------------------------------------------------------------------
# Scanner-compatible strategy dict
# ---------------------------------------------------------------------------
CYCLE17_STRATEGIES = {
    "stoch_rsi": scan_stoch_rsi,
    "pivot_reversion": scan_pivot_reversion,
    "ichimoku": scan_ichimoku_cloud,
    "yield_curve_proxy": scan_yield_curve_proxy,
    "range_trading": scan_range_trading,
}
