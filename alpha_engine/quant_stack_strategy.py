#!/usr/bin/env python3
"""
ALPHA_ENGINE -- KAMA + ATR Trailing Stop + Regime Switch (Quant Stack)
======================================================================
Mercury 2 quant stack blueprint implementation.

Strategies:
  - kama_atr_trend       : KAMA slope + ATR trailing + VR filter (trend)
  - kama_regime_adaptive : Regime-adaptive KAMA (bull/bear/choppy params)
  - kama_mean_reversion  : RSI-2 mean reversion in choppy regimes

Components:
  1. KAMA (Kaufman Adaptive Moving Average) -- adapts speed to market noise
  2. ATR Trailing Stop -- ratcheting stop that only moves in trade direction
  3. Volatility Ratio (short ATR / long ATR) -- breakout vs squeeze detector
  4. Regime Switch via fast_regime_detector -- BULL/BEAR/CHOPPY routing

Pure Python + numpy. No external TA libraries required.
All data via api_failover (3+ exchange failover chain).
"""

from __future__ import annotations

import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Local imports
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import CRYPTO_SYMBOLS
from indicators import rsi as compute_rsi, atr as compute_atr, volume_ratio as compute_volume_ratio

try:
    from api_failover import fetch_klines
except ImportError:
    from alpha_engine.api_failover import fetch_klines

try:
    from fast_regime_detector import get_regime_for_symbol
except ImportError:
    def get_regime_for_symbol(symbol: str = "BTCUSDT") -> str:
        return "CHOPPY"

_log = logging.getLogger("alpha_engine.quant_stack")


# =========================================================================
# Component 1: KAMA (Kaufman Adaptive Moving Average)
# =========================================================================
def compute_kama(close: np.ndarray, window: int = 10,
                 fast_period: int = 2, slow_period: int = 30) -> np.ndarray:
    """Compute Kaufman Adaptive Moving Average.

    KAMA adapts its smoothing speed based on the Efficiency Ratio (ER):
      ER = abs(close - close[window]) / sum(abs(close[i] - close[i-1]))
    High ER (trending) -> fast response. Low ER (noisy) -> slow response.

    Args:
        close: 1D array of close prices.
        window: ER lookback period (default 10).
        fast_period: fast EMA period for trending markets (default 2).
        slow_period: slow EMA period for noisy markets (default 30).

    Returns:
        1D array of KAMA values (NaN-padded for initial window).
    """
    n = len(close)
    kama = np.full(n, np.nan)
    if n < window + 1:
        return kama

    fast_sc = 2.0 / (fast_period + 1.0)
    slow_sc = 2.0 / (slow_period + 1.0)

    # Initialize KAMA at the end of the first window
    kama[window] = close[window]

    for i in range(window + 1, n):
        # Direction: net price change over window
        direction = abs(close[i] - close[i - window])

        # Volatility: sum of absolute bar-to-bar changes over window
        volatility = 0.0
        for j in range(i - window + 1, i + 1):
            volatility += abs(close[j] - close[j - 1])

        # Efficiency Ratio
        if volatility > 0:
            er = direction / volatility
        else:
            er = 0.0

        # Smoothing Constant (SC) = (ER * (fast_sc - slow_sc) + slow_sc)^2
        sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2

        # KAMA update
        kama[i] = kama[i - 1] + sc * (close[i] - kama[i - 1])

    return kama


def kama_slope(kama_values: np.ndarray, lookback: int = 3) -> np.ndarray:
    """Compute normalized KAMA slope over lookback periods.

    Returns slope as percentage change per bar (positive = uptrend).
    """
    n = len(kama_values)
    slope = np.full(n, np.nan)
    for i in range(lookback, n):
        if not np.isnan(kama_values[i]) and not np.isnan(kama_values[i - lookback]):
            prev = kama_values[i - lookback]
            if prev > 0:
                slope[i] = (kama_values[i] - prev) / prev * 100.0
    return slope


# =========================================================================
# Component 2: ATR Trailing Stop
# =========================================================================
def compute_atr_trailing_stop(close: np.ndarray, high: np.ndarray,
                              low: np.ndarray, atr_period: int = 14,
                              multiplier: float = 3.0) -> np.ndarray:
    """Compute ATR-based trailing stop that ratchets up only (for longs).

    For long positions: stop = close - multiplier * ATR.
    The stop only moves UP -- it never decreases.

    Args:
        close, high, low: 1D arrays of OHLC data.
        atr_period: ATR calculation period.
        multiplier: ATR multiplier for stop distance.

    Returns:
        1D array of trailing stop values (NaN-padded for ATR warmup).
    """
    n = len(close)
    trail_stop = np.full(n, np.nan)
    if n < atr_period + 1:
        return trail_stop

    # Compute ATR manually with numpy
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i - 1])
        lc = abs(low[i] - close[i - 1])
        tr[i] = max(hl, hc, lc)

    # Wilder's smoothed ATR
    atr_vals = np.full(n, np.nan)
    atr_vals[atr_period] = np.mean(tr[1:atr_period + 1])
    for i in range(atr_period + 1, n):
        atr_vals[i] = (atr_vals[i - 1] * (atr_period - 1) + tr[i]) / atr_period

    # Ratcheting trailing stop (long side: only moves UP)
    for i in range(atr_period, n):
        if np.isnan(atr_vals[i]):
            continue
        raw_stop = close[i] - multiplier * atr_vals[i]
        if np.isnan(trail_stop[i - 1]) if i > atr_period else True:
            trail_stop[i] = raw_stop
        else:
            trail_stop[i] = max(trail_stop[i - 1], raw_stop)

    return trail_stop


def compute_atr_trailing_stop_short(close: np.ndarray, high: np.ndarray,
                                    low: np.ndarray, atr_period: int = 14,
                                    multiplier: float = 3.0) -> np.ndarray:
    """ATR trailing stop for shorts -- ratchets DOWN only."""
    n = len(close)
    trail_stop = np.full(n, np.nan)
    if n < atr_period + 1:
        return trail_stop

    tr = np.zeros(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i - 1])
        lc = abs(low[i] - close[i - 1])
        tr[i] = max(hl, hc, lc)

    atr_vals = np.full(n, np.nan)
    atr_vals[atr_period] = np.mean(tr[1:atr_period + 1])
    for i in range(atr_period + 1, n):
        atr_vals[i] = (atr_vals[i - 1] * (atr_period - 1) + tr[i]) / atr_period

    for i in range(atr_period, n):
        if np.isnan(atr_vals[i]):
            continue
        raw_stop = close[i] + multiplier * atr_vals[i]
        if np.isnan(trail_stop[i - 1]) if i > atr_period else True:
            trail_stop[i] = raw_stop
        else:
            trail_stop[i] = min(trail_stop[i - 1], raw_stop)

    return trail_stop


# =========================================================================
# Component 3: Volatility Ratio (Short ATR / Long ATR)
# =========================================================================
def compute_volatility_ratio(high: np.ndarray, low: np.ndarray,
                             close: np.ndarray,
                             short_period: int = 7,
                             long_period: int = 28) -> np.ndarray:
    """Compute Volatility Ratio = ATR(short) / ATR(long).

    VR > 1.0 = expanding volatility (breakout precursor).
    VR < 0.8 = contracting volatility (squeeze, consolidation).
    VR ~ 1.0 = stable volatility.

    Args:
        high, low, close: 1D arrays.
        short_period: short ATR window (default 7).
        long_period: long ATR window (default 28).

    Returns:
        1D array of VR values.
    """
    n = len(close)
    vr = np.full(n, np.nan)
    if n < long_period + 2:
        return vr

    # True Range
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i - 1])
        lc = abs(low[i] - close[i - 1])
        tr[i] = max(hl, hc, lc)

    # Short ATR (SMA-based for simplicity)
    atr_short = np.full(n, np.nan)
    for i in range(short_period, n):
        atr_short[i] = np.mean(tr[i - short_period + 1:i + 1])

    # Long ATR
    atr_long = np.full(n, np.nan)
    for i in range(long_period, n):
        atr_long[i] = np.mean(tr[i - long_period + 1:i + 1])

    # Ratio
    for i in range(long_period, n):
        if not np.isnan(atr_short[i]) and not np.isnan(atr_long[i]) and atr_long[i] > 0:
            vr[i] = atr_short[i] / atr_long[i]

    return vr


# =========================================================================
# Component 4: Regime-Adaptive Parameters
# =========================================================================
_REGIME_PARAMS = {
    # BULL: aggressive -- fast KAMA, tight ATR stop
    "STRONG_BULL": {"kama_fast": 2, "kama_slow": 30, "atr_mult": 2.0, "direction": "LONG", "mode": "trend"},
    "BULL":        {"kama_fast": 2, "kama_slow": 30, "atr_mult": 2.0, "direction": "LONG", "mode": "trend"},
    # BEAR: defensive -- slow KAMA, wide ATR stop, SHORT only
    "BEAR":        {"kama_fast": 10, "kama_slow": 30, "atr_mult": 4.0, "direction": "SHORT", "mode": "trend"},
    "STRONG_BEAR": {"kama_fast": 10, "kama_slow": 30, "atr_mult": 4.0, "direction": "SHORT", "mode": "trend"},
    # CHOPPY / RANGING: mean reversion -- RSI-2 entries only
    "CHOPPY":      {"kama_fast": 5, "kama_slow": 30, "atr_mult": 3.0, "direction": "BOTH", "mode": "mean_reversion"},
    "RANGING":     {"kama_fast": 5, "kama_slow": 30, "atr_mult": 3.0, "direction": "BOTH", "mode": "mean_reversion"},
}


def get_regime_params(regime: str) -> dict:
    """Get regime-adaptive strategy parameters."""
    return _REGIME_PARAMS.get(regime, _REGIME_PARAMS["CHOPPY"])


# =========================================================================
# Helper: smart rounding + signal construction
# =========================================================================
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _smart_round(value: float) -> float:
    if value == 0:
        return 0.0
    abs_val = abs(value)
    if abs_val >= 100:
        return round(value, 2)
    elif abs_val >= 1:
        return round(value, 4)
    elif abs_val >= 0.01:
        return round(value, 6)
    else:
        return round(value, 10)


def _get_category(symbol: str) -> str:
    info = CRYPTO_SYMBOLS.get(symbol, {})
    return info.get("cat", "crypto")


def _parse_klines_to_arrays(klines: list) -> tuple:
    """Convert Binance-format klines to numpy arrays (open, high, low, close, volume)."""
    opens, highs, lows, closes, volumes = [], [], [], [], []
    for k in klines:
        try:
            opens.append(float(k[1]))
            highs.append(float(k[2]))
            lows.append(float(k[3]))
            closes.append(float(k[4]))
            volumes.append(float(k[5]))
        except (IndexError, ValueError, TypeError):
            continue
    return (np.array(opens), np.array(highs), np.array(lows),
            np.array(closes), np.array(volumes))


# =========================================================================
# Strategy 1: KAMA + ATR Trend Following
# =========================================================================
def kama_atr_trend(data: dict) -> list[dict]:
    """KAMA slope + Volatility Ratio + ATR trailing stop.

    Entry (LONG): KAMA slope positive AND VR > 0.9 AND price > KAMA.
    Exit: price < ATR trailing stop OR KAMA slope turns negative.
    TP: 1.5x ATR from entry. SL: ATR trailing stop level.
    Confidence: 0.70-0.85 based on KAMA slope strength + VR magnitude.
    """
    signals: list[dict] = []

    for symbol in CRYPTO_SYMBOLS:
        if symbol not in data:
            continue
        df = data[symbol]
        if len(df) < 50:
            continue

        try:
            close = df["Close"].values.astype(float)
            high = df["High"].values.astype(float)
            low = df["Low"].values.astype(float)
            vol = df["Volume"].values.astype(float)
            n = len(close)

            # Compute indicators
            kama_vals = compute_kama(close, window=10, fast_period=2, slow_period=30)
            slope_vals = kama_slope(kama_vals, lookback=3)
            trail_stop = compute_atr_trailing_stop(close, high, low, atr_period=14, multiplier=3.0)
            vr = compute_volatility_ratio(high, low, close, short_period=7, long_period=28)

            # Current values
            if np.isnan(kama_vals[-1]) or np.isnan(slope_vals[-1]) or np.isnan(vr[-1]):
                continue
            if np.isnan(trail_stop[-1]):
                continue

            cur_price = close[-1]
            cur_kama = kama_vals[-1]
            cur_slope = slope_vals[-1]
            cur_vr = vr[-1]
            cur_trail = trail_stop[-1]

            # RSI filter
            rsi_series = compute_rsi(pd.Series(close), 14)
            rsi_val = float(rsi_series.iloc[-1]) if len(rsi_series) > 0 else 50.0

            # Volume ratio
            vol_r = compute_volume_ratio(pd.Series(vol), 20)
            vr_vol = float(vol_r.iloc[-1]) if len(vol_r) > 0 else 1.0

            # === LONG Entry ===
            # KAMA slope positive + VR > 0.9 (expanding) + price > KAMA
            if (cur_slope > 0.05 and cur_vr > 0.9 and cur_price > cur_kama
                    and rsi_val < 75 and vr_vol > 0.7):

                # ATR for TP/SL
                atr_series = compute_atr(pd.Series(high), pd.Series(low), pd.Series(close), 14)
                cur_atr = float(atr_series.iloc[-1])
                if cur_atr <= 0:
                    continue

                tp = _smart_round(cur_price + 1.5 * cur_atr)
                sl = _smart_round(cur_trail)
                entry = _smart_round(cur_price)

                rr = abs(tp - entry) / max(abs(entry - sl), cur_price * 0.001)
                if rr < 1.2:
                    continue

                # Confidence: 0.70-0.85 based on slope + VR + volume
                conf = 0.70
                conf += min(0.05, cur_slope * 0.5)       # slope strength bonus
                conf += min(0.05, (cur_vr - 0.9) * 0.5)  # VR expansion bonus
                conf += min(0.03, (vr_vol - 1.0) * 0.03) # volume bonus
                conf = round(min(0.85, max(0.70, conf)), 2)

                signals.append({
                    "strategy": "kama_atr_trend",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": entry,
                    "take_profit": tp,
                    "stop_loss": sl,
                    "confidence": conf,
                    "risk_reward": round(rr, 2),
                    "reason": (
                        f"KAMA trend: slope={cur_slope:+.3f}%, VR={cur_vr:.2f} "
                        f"(expanding), price>{cur_kama:.2f} KAMA, "
                        f"trail stop={cur_trail:.2f}, RSI={rsi_val:.0f}, "
                        f"vol={vr_vol:.1f}x"
                    ),
                    "timeframe": "4h",
                    "rsi_at_entry": round(rsi_val, 1),
                    "extra": {
                        "kama_slope_pct": round(cur_slope, 4),
                        "volatility_ratio": round(cur_vr, 3),
                        "atr_trail_stop": round(cur_trail, 4),
                        "kama_value": round(cur_kama, 4),
                        "volume_ratio": round(vr_vol, 2),
                        "component": "mercury2_quant_stack",
                    },
                    "timestamp": _now_iso(),
                })

        except Exception as e:
            _log.debug("kama_atr_trend error for %s: %s", symbol, e)
            continue

    return signals


# =========================================================================
# Strategy 2: Regime-Adaptive KAMA
# =========================================================================
def kama_regime_adaptive(data: dict) -> list[dict]:
    """Regime-adaptive KAMA with parameters tuned per market state.

    BULL:  aggressive KAMA(fast=2) + tight ATR(2x) -- LONG only
    BEAR:  defensive KAMA(fast=10) + wide ATR(4x) -- SHORT only
    CHOPPY: skip (handled by kama_mean_reversion)

    Uses fast_regime_detector for real-time regime classification.
    """
    signals: list[dict] = []

    for symbol in CRYPTO_SYMBOLS:
        if symbol not in data:
            continue
        df = data[symbol]
        if len(df) < 50:
            continue

        try:
            # Get regime
            regime_sym = symbol.replace("-USD", "USDT").replace("/", "")
            if not regime_sym.endswith("USDT"):
                regime_sym = regime_sym + "USDT" if not regime_sym.endswith("USD") else regime_sym.replace("USD", "USDT")

            regime = get_regime_for_symbol(regime_sym)
            params = get_regime_params(regime)

            # Skip mean-reversion regimes (handled by strategy 3)
            if params["mode"] == "mean_reversion":
                continue

            close = df["Close"].values.astype(float)
            high = df["High"].values.astype(float)
            low = df["Low"].values.astype(float)
            n = len(close)

            # Compute KAMA with regime-adaptive parameters
            kama_vals = compute_kama(close, window=10,
                                     fast_period=params["kama_fast"],
                                     slow_period=params["kama_slow"])
            slope_vals = kama_slope(kama_vals, lookback=3)
            vr = compute_volatility_ratio(high, low, close)

            if np.isnan(kama_vals[-1]) or np.isnan(slope_vals[-1]) or np.isnan(vr[-1]):
                continue

            cur_price = close[-1]
            cur_kama = kama_vals[-1]
            cur_slope = slope_vals[-1]
            cur_vr = vr[-1]

            rsi_series = compute_rsi(pd.Series(close), 14)
            rsi_val = float(rsi_series.iloc[-1]) if len(rsi_series) > 0 else 50.0

            atr_series = compute_atr(pd.Series(high), pd.Series(low), pd.Series(close), 14)
            cur_atr = float(atr_series.iloc[-1])
            if cur_atr <= 0:
                continue

            direction = params["direction"]

            # === LONG signals in BULL regimes ===
            if direction == "LONG" and cur_slope > 0.03 and cur_price > cur_kama and cur_vr > 0.85:
                trail = compute_atr_trailing_stop(close, high, low, 14, params["atr_mult"])
                cur_trail = trail[-1] if not np.isnan(trail[-1]) else cur_price - params["atr_mult"] * cur_atr

                tp = _smart_round(cur_price + 1.5 * cur_atr)
                sl = _smart_round(cur_trail)
                entry = _smart_round(cur_price)

                rr = abs(tp - entry) / max(abs(entry - sl), cur_price * 0.001)
                if rr < 1.0:
                    continue
                if rsi_val > 80:
                    continue

                conf = 0.72
                conf += min(0.05, cur_slope * 0.4)
                conf += min(0.04, (cur_vr - 0.85) * 0.3)
                # Bull regime bonus
                if regime in ("STRONG_BULL",):
                    conf += 0.04
                conf = round(min(0.85, max(0.70, conf)), 2)

                signals.append({
                    "strategy": "kama_regime_adaptive",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": entry,
                    "take_profit": tp,
                    "stop_loss": sl,
                    "confidence": conf,
                    "risk_reward": round(rr, 2),
                    "reason": (
                        f"Regime-KAMA [{regime}]: slope={cur_slope:+.3f}%, "
                        f"VR={cur_vr:.2f}, KAMA_fast={params['kama_fast']}, "
                        f"ATR_mult={params['atr_mult']}, RSI={rsi_val:.0f}"
                    ),
                    "timeframe": "4h",
                    "rsi_at_entry": round(rsi_val, 1),
                    "extra": {
                        "regime": regime,
                        "kama_fast": params["kama_fast"],
                        "atr_multiplier": params["atr_mult"],
                        "kama_slope_pct": round(cur_slope, 4),
                        "volatility_ratio": round(cur_vr, 3),
                        "component": "mercury2_quant_stack",
                    },
                    "timestamp": _now_iso(),
                })

            # === SHORT signals in BEAR regimes ===
            elif direction == "SHORT" and cur_slope < -0.03 and cur_price < cur_kama and cur_vr > 0.85:
                trail = compute_atr_trailing_stop_short(close, high, low, 14, params["atr_mult"])
                cur_trail = trail[-1] if not np.isnan(trail[-1]) else cur_price + params["atr_mult"] * cur_atr

                tp = _smart_round(cur_price - 1.5 * cur_atr)
                sl = _smart_round(cur_trail)
                entry = _smart_round(cur_price)

                rr = abs(entry - tp) / max(abs(sl - entry), cur_price * 0.001)
                if rr < 1.0:
                    continue
                if rsi_val < 20:
                    continue

                conf = 0.72
                conf += min(0.05, abs(cur_slope) * 0.4)
                conf += min(0.04, (cur_vr - 0.85) * 0.3)
                if regime == "STRONG_BEAR":
                    conf += 0.04
                conf = round(min(0.85, max(0.70, conf)), 2)

                signals.append({
                    "strategy": "kama_regime_adaptive",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "SELL",
                    "entry_price": entry,
                    "take_profit": tp,
                    "stop_loss": sl,
                    "confidence": conf,
                    "risk_reward": round(rr, 2),
                    "reason": (
                        f"Regime-KAMA [{regime}] SHORT: slope={cur_slope:+.3f}%, "
                        f"VR={cur_vr:.2f}, KAMA_fast={params['kama_fast']}, "
                        f"ATR_mult={params['atr_mult']}, RSI={rsi_val:.0f}"
                    ),
                    "timeframe": "4h",
                    "rsi_at_entry": round(rsi_val, 1),
                    "extra": {
                        "regime": regime,
                        "kama_fast": params["kama_fast"],
                        "atr_multiplier": params["atr_mult"],
                        "kama_slope_pct": round(cur_slope, 4),
                        "volatility_ratio": round(cur_vr, 3),
                        "component": "mercury2_quant_stack",
                    },
                    "timestamp": _now_iso(),
                })

        except Exception as e:
            _log.debug("kama_regime_adaptive error for %s: %s", symbol, e)
            continue

    return signals


# =========================================================================
# Strategy 3: KAMA Mean Reversion (Choppy/Ranging Regimes)
# =========================================================================
def kama_mean_reversion(data: dict) -> list[dict]:
    """RSI-2 mean reversion in choppy/ranging regimes.

    Only activates when fast_regime_detector returns CHOPPY or RANGING.
    Entry: RSI(2) < 10 => BUY, RSI(2) > 90 => SELL.
    KAMA used as mean-reversion target (TP = KAMA level).
    ATR trailing stop for risk management.
    """
    signals: list[dict] = []

    for symbol in CRYPTO_SYMBOLS:
        if symbol not in data:
            continue
        df = data[symbol]
        if len(df) < 50:
            continue

        try:
            # Check regime -- only fire in choppy/ranging
            regime_sym = symbol.replace("-USD", "USDT").replace("/", "")
            if not regime_sym.endswith("USDT"):
                regime_sym = regime_sym + "USDT" if not regime_sym.endswith("USD") else regime_sym.replace("USD", "USDT")

            regime = get_regime_for_symbol(regime_sym)
            if regime not in ("CHOPPY", "RANGING"):
                continue

            close = df["Close"].values.astype(float)
            high = df["High"].values.astype(float)
            low = df["Low"].values.astype(float)
            n = len(close)

            # RSI(2) for mean reversion timing
            rsi2_series = compute_rsi(pd.Series(close), 2)
            if len(rsi2_series) < 3:
                continue
            rsi2_val = float(rsi2_series.iloc[-1])

            # KAMA as mean-reversion target
            kama_vals = compute_kama(close, window=10, fast_period=5, slow_period=30)
            if np.isnan(kama_vals[-1]):
                continue

            cur_price = close[-1]
            cur_kama = kama_vals[-1]

            # ATR for stops
            atr_series = compute_atr(pd.Series(high), pd.Series(low), pd.Series(close), 14)
            cur_atr = float(atr_series.iloc[-1])
            if cur_atr <= 0:
                continue

            vr = compute_volatility_ratio(high, low, close)
            cur_vr = vr[-1] if not np.isnan(vr[-1]) else 1.0

            # === BUY: RSI(2) oversold in ranging market ===
            if rsi2_val < 10 and cur_price < cur_kama:
                tp = _smart_round(cur_kama)  # Revert to KAMA mean
                sl = _smart_round(cur_price - 3.0 * cur_atr)
                entry = _smart_round(cur_price)

                rr = abs(tp - entry) / max(abs(entry - sl), cur_price * 0.001)
                if rr < 1.0:
                    continue

                conf = 0.70 + min(0.10, (10 - rsi2_val) * 0.01)
                if cur_vr < 0.8:  # squeeze bonus (good for MR)
                    conf += 0.03
                conf = round(min(0.82, max(0.70, conf)), 2)

                signals.append({
                    "strategy": "kama_mean_reversion",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": entry,
                    "take_profit": tp,
                    "stop_loss": sl,
                    "confidence": conf,
                    "risk_reward": round(rr, 2),
                    "reason": (
                        f"KAMA MR [{regime}]: RSI(2)={rsi2_val:.1f} oversold, "
                        f"target KAMA={cur_kama:.2f}, VR={cur_vr:.2f}"
                    ),
                    "timeframe": "4h",
                    "rsi_at_entry": round(rsi2_val, 1),
                    "extra": {
                        "regime": regime,
                        "rsi2": round(rsi2_val, 2),
                        "kama_target": round(cur_kama, 4),
                        "volatility_ratio": round(cur_vr, 3),
                        "mode": "mean_reversion",
                        "component": "mercury2_quant_stack",
                    },
                    "timestamp": _now_iso(),
                })

            # === SELL: RSI(2) overbought in ranging market ===
            elif rsi2_val > 90 and cur_price > cur_kama:
                tp = _smart_round(cur_kama)  # Revert to KAMA mean
                sl = _smart_round(cur_price + 3.0 * cur_atr)
                entry = _smart_round(cur_price)

                rr = abs(entry - tp) / max(abs(sl - entry), cur_price * 0.001)
                if rr < 1.0:
                    continue

                conf = 0.70 + min(0.10, (rsi2_val - 90) * 0.01)
                if cur_vr < 0.8:
                    conf += 0.03
                conf = round(min(0.82, max(0.70, conf)), 2)

                signals.append({
                    "strategy": "kama_mean_reversion",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "SELL",
                    "entry_price": entry,
                    "take_profit": tp,
                    "stop_loss": sl,
                    "confidence": conf,
                    "risk_reward": round(rr, 2),
                    "reason": (
                        f"KAMA MR [{regime}] SHORT: RSI(2)={rsi2_val:.1f} overbought, "
                        f"target KAMA={cur_kama:.2f}, VR={cur_vr:.2f}"
                    ),
                    "timeframe": "4h",
                    "rsi_at_entry": round(rsi2_val, 1),
                    "extra": {
                        "regime": regime,
                        "rsi2": round(rsi2_val, 2),
                        "kama_target": round(cur_kama, 4),
                        "volatility_ratio": round(cur_vr, 3),
                        "mode": "mean_reversion",
                        "component": "mercury2_quant_stack",
                    },
                    "timestamp": _now_iso(),
                })

        except Exception as e:
            _log.debug("kama_mean_reversion error for %s: %s", symbol, e)
            continue

    return signals


# =========================================================================
# Backtest: 90-day 4H data for BTC, ETH, SOL
# =========================================================================
def run_backtest(symbols: list[str] | None = None, days: int = 90,
                 verbose: bool = True) -> dict:
    """Backtest the quant stack strategies on historical 4H data.

    Fetches data via api_failover (Binance -> Bybit -> KuCoin -> CryptoCompare).
    Tests KAMA trend + regime-adaptive + mean-reversion strategies.

    Returns dict with per-strategy and per-symbol results.
    """
    if symbols is None:
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    # 90 days of 4H data = 90 * 6 = 540 candles
    candles_needed = days * 6

    results = {
        "strategies": {},
        "symbols": {},
        "summary": {},
        "timestamp": _now_iso(),
    }

    all_trades: list[dict] = []

    for sym in symbols:
        if verbose:
            print(f"  [BACKTEST] Fetching {sym} 4H x {candles_needed} candles...")

        klines = fetch_klines(sym, interval="4h", limit=candles_needed)
        if not klines or len(klines) < 100:
            if verbose:
                print(f"  [BACKTEST] {sym}: insufficient data ({len(klines) if klines else 0} bars)")
            continue

        o, h, l, c, v = _parse_klines_to_arrays(klines)
        n = len(c)
        if verbose:
            print(f"  [BACKTEST] {sym}: {n} bars loaded")

        # Run KAMA trend following backtest
        kama_vals = compute_kama(c, window=10, fast_period=2, slow_period=30)
        slope_vals = kama_slope(kama_vals, lookback=3)
        trail_stop = compute_atr_trailing_stop(c, h, l, atr_period=14, multiplier=3.0)
        vr = compute_volatility_ratio(h, l, c, short_period=7, long_period=28)

        # True Range + ATR for TP/SL
        tr = np.zeros(n)
        tr[0] = h[0] - l[0]
        for i in range(1, n):
            tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        atr_vals = np.full(n, np.nan)
        if n > 14:
            atr_vals[14] = np.mean(tr[1:15])
            for i in range(15, n):
                atr_vals[i] = (atr_vals[i - 1] * 13 + tr[i]) / 14

        # Simple backtest: walk forward, check entry/exit conditions
        in_trade = False
        entry_price = 0.0
        tp_price = 0.0
        sl_price = 0.0
        entry_bar = 0

        sym_trades = []

        warmup = max(30, 28 + 3)  # VR long_period + slope lookback
        for i in range(warmup, n):
            if np.isnan(kama_vals[i]) or np.isnan(slope_vals[i]) or np.isnan(vr[i]):
                continue
            if np.isnan(trail_stop[i]) or np.isnan(atr_vals[i]):
                continue

            if not in_trade:
                # Entry: KAMA slope positive + VR > 0.9 + price > KAMA
                if (slope_vals[i] > 0.05 and vr[i] > 0.9
                        and c[i] > kama_vals[i] and atr_vals[i] > 0):
                    in_trade = True
                    entry_price = c[i]
                    tp_price = c[i] + 1.5 * atr_vals[i]
                    sl_price = trail_stop[i]
                    entry_bar = i
            else:
                # Exit: price < trailing stop OR KAMA slope negative
                # Update trailing stop (ratchet up)
                sl_price = max(sl_price, trail_stop[i])

                hit_tp = h[i] >= tp_price
                hit_sl = l[i] <= sl_price
                slope_exit = slope_vals[i] < -0.02

                if hit_tp:
                    pnl_pct = (tp_price - entry_price) / entry_price * 100
                    sym_trades.append({
                        "symbol": sym, "strategy": "kama_atr_trend",
                        "entry": entry_price, "exit": tp_price,
                        "pnl_pct": round(pnl_pct, 2), "result": "TP",
                        "bars_held": i - entry_bar,
                    })
                    in_trade = False
                elif hit_sl:
                    pnl_pct = (sl_price - entry_price) / entry_price * 100
                    sym_trades.append({
                        "symbol": sym, "strategy": "kama_atr_trend",
                        "entry": entry_price, "exit": sl_price,
                        "pnl_pct": round(pnl_pct, 2), "result": "SL",
                        "bars_held": i - entry_bar,
                    })
                    in_trade = False
                elif slope_exit:
                    pnl_pct = (c[i] - entry_price) / entry_price * 100
                    sym_trades.append({
                        "symbol": sym, "strategy": "kama_atr_trend",
                        "entry": entry_price, "exit": c[i],
                        "pnl_pct": round(pnl_pct, 2), "result": "SLOPE_EXIT",
                        "bars_held": i - entry_bar,
                    })
                    in_trade = False

        all_trades.extend(sym_trades)

        # Per-symbol summary
        wins = sum(1 for t in sym_trades if t["pnl_pct"] > 0)
        total = len(sym_trades)
        total_pnl = sum(t["pnl_pct"] for t in sym_trades)
        avg_bars = np.mean([t["bars_held"] for t in sym_trades]) if sym_trades else 0

        results["symbols"][sym] = {
            "trades": total,
            "wins": wins,
            "losses": total - wins,
            "win_rate": round(wins / total, 3) if total > 0 else 0,
            "total_pnl_pct": round(total_pnl, 2),
            "avg_pnl_pct": round(total_pnl / total, 2) if total > 0 else 0,
            "avg_bars_held": round(avg_bars, 1),
        }

        if verbose and total > 0:
            wr = wins / total * 100
            print(f"  [BACKTEST] {sym}: {total} trades, WR={wr:.0f}%, "
                  f"PnL={total_pnl:+.2f}%, avg hold={avg_bars:.0f} bars")

    # Aggregate results
    total_trades = len(all_trades)
    total_wins = sum(1 for t in all_trades if t["pnl_pct"] > 0)
    total_pnl = sum(t["pnl_pct"] for t in all_trades)

    results["summary"] = {
        "total_trades": total_trades,
        "total_wins": total_wins,
        "total_losses": total_trades - total_wins,
        "win_rate": round(total_wins / total_trades, 3) if total_trades > 0 else 0,
        "total_pnl_pct": round(total_pnl, 2),
        "avg_pnl_pct": round(total_pnl / total_trades, 2) if total_trades > 0 else 0,
        "symbols_tested": len(results["symbols"]),
    }

    if verbose:
        wr = results["summary"]["win_rate"] * 100
        print(f"\n  [BACKTEST SUMMARY] {total_trades} trades, WR={wr:.0f}%, "
              f"Total PnL={total_pnl:+.2f}%")

    return results


# =========================================================================
# Registry -- export for scanner.py integration
# =========================================================================
QUANT_STACK_STRATEGIES = {
    "kama_atr_trend":       kama_atr_trend,
    "kama_regime_adaptive": kama_regime_adaptive,
    "kama_mean_reversion":  kama_mean_reversion,
}


# =========================================================================
# CLI: standalone backtest + signal generation
# =========================================================================
if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Quant Stack: KAMA + ATR + Regime")
    parser.add_argument("--backtest", action="store_true", help="Run 90-day backtest")
    parser.add_argument("--symbols", nargs="+", default=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
                        help="Symbols to backtest")
    parser.add_argument("--days", type=int, default=90, help="Backtest days")
    args = parser.parse_args()

    if args.backtest:
        print("=" * 60)
        print("QUANT STACK BACKTEST -- KAMA + ATR Trailing + Regime Switch")
        print("=" * 60)
        results = run_backtest(symbols=args.symbols, days=args.days)
        import json
        print("\n" + json.dumps(results["summary"], indent=2))
    else:
        print("Use --backtest to run the 90-day historical backtest.")
        print("In production, strategies run via scanner.py integration.")
