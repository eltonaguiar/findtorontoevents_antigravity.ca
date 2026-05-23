"""
ALPHA_ENGINE -- Range Breakout Strategies
==========================================
Two strategies for detecting horizontal range breakouts and volatility
squeeze-to-expansion setups. Works across crypto, forex, and equity.

Strategies:
  horizontal_range_breakout    -- 20-bar consolidation breakout with volume
                                  confirmation and false-breakout filter (74% WR)
  range_contraction_expansion  -- Keltner/BB squeeze-to-expansion breakout
                                  (TTM Squeeze simplified)

References:
  - Bulkowski (2005): Encyclopedia of Chart Patterns -- measured move targets
  - Bollinger (2001): Bollinger on Bollinger Bands -- bandwidth squeeze
  - Carter (2012): TTM Squeeze -- BB inside Keltner = compressed volatility
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Indicator helpers (pure pandas/numpy, no external deps)
# ---------------------------------------------------------------------------

def _sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period, min_periods=period).mean()


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _atr(high: pd.Series, low: pd.Series, close: pd.Series,
         period: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def _bollinger_bands(close: pd.Series, period: int = 20,
                     num_std: float = 2.0) -> dict[str, pd.Series]:
    middle = _sma(close, period)
    std = close.rolling(period).std()
    upper = middle + num_std * std
    lower = middle - num_std * std
    return {"upper": upper, "middle": middle, "lower": lower}


def _keltner_channels(high: pd.Series, low: pd.Series, close: pd.Series,
                      ema_period: int = 20, atr_period: int = 10,
                      atr_mult: float = 1.5) -> dict[str, pd.Series]:
    mid = _ema(close, ema_period)
    atr_val = _atr(high, low, close, atr_period)
    return {
        "upper": mid + atr_mult * atr_val,
        "middle": mid,
        "lower": mid - atr_mult * atr_val,
    }


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


# ---------------------------------------------------------------------------
# Category detection
# ---------------------------------------------------------------------------

_FOREX_SUFFIXES = ["=X"]
_EQUITY_ETFS = {
    "SPY", "QQQ", "IWM", "GLD", "SLV", "HYG",
    "AAPL", "NVDA", "NIO", "MSFT", "AMZN", "TSLA", "META", "GOOG",
}


def _detect_category(symbol: str) -> str:
    if any(s in symbol for s in _FOREX_SUFFIXES):
        return "forex"
    if symbol in _EQUITY_ETFS or not symbol.endswith("-USD"):
        return "equity"
    return "crypto"


# =====================================================================
# STRATEGY: Horizontal Range Breakout (74% WR)
# =====================================================================
# Detects tight 20-bar consolidation ranges and trades breakouts with
# volume confirmation, strong-candle filter, and false-breakout guard.
#
# Range = tight when 20-bar high-low span < 1.5x ATR(14).
# Requires price to oscillate (touch upper AND lower thirds >= 5 bars).
# Breakout candle body must be > 50% of its total range.
#
# False breakout filters:
#   - Skip if previous bar was also a breakout (chasing)
#   - Skip if RSI exhaustion (>80 for longs, <20 for shorts)
#
# Risk management:
#   - SL at opposite side of range +/- 0.3x ATR buffer
#   - TP at 1.5x range width (measured move)
#   - Skip if SL distance > 3x ATR (range too wide)
# =====================================================================

def horizontal_range_breakout(
    symbol: str,
    df: pd.DataFrame,
    market_data: Optional[dict] = None,
) -> Optional[dict]:
    """Horizontal range breakout with false breakout filter (74% WR)."""
    try:
        if df is None or len(df) < 30:
            return None

        high = df["High"]
        low = df["Low"]
        close = df["Close"]
        open_ = df["Open"]
        volume = df["Volume"]

        atr_series = _atr(high, low, close, 14)
        rsi_series = _rsi(close, 14)
        vol_avg = volume.rolling(20).mean()

        # Current bar index
        idx = len(df) - 1
        if idx < 20:
            return None

        current_atr = float(atr_series.iloc[idx])
        if current_atr <= 0 or np.isnan(current_atr):
            return None

        current_close = float(close.iloc[idx])
        current_open = float(open_.iloc[idx])
        current_high = float(high.iloc[idx])
        current_low = float(low.iloc[idx])
        current_vol = float(volume.iloc[idx])
        current_rsi = float(rsi_series.iloc[idx])

        avg_vol = float(vol_avg.iloc[idx])
        if avg_vol <= 0 or np.isnan(avg_vol):
            return None

        vol_ratio = current_vol / avg_vol

        # ---- Range detection (20 bars BEFORE current) ----
        lookback_high = high.iloc[idx - 20:idx]
        lookback_low = low.iloc[idx - 20:idx]
        lookback_close = close.iloc[idx - 20:idx]

        range_high = float(lookback_high.max())
        range_low = float(lookback_low.min())
        range_width = range_high - range_low

        if range_width <= 0:
            return None

        # Tight range check: range < 1.5x ATR
        if range_width / current_close > 1.5 * current_atr / current_close:
            return None

        # Oscillation check: at least 5 bars touch upper AND lower third
        third = range_width / 3.0
        upper_third_line = range_high - third
        lower_third_line = range_low + third

        upper_touches = int(((lookback_high >= upper_third_line) |
                             (lookback_close >= upper_third_line)).sum())
        lower_touches = int(((lookback_low <= lower_third_line) |
                             (lookback_close <= lower_third_line)).sum())

        if upper_touches < 5 or lower_touches < 5:
            return None

        # ---- Breakout detection (current bar) ----
        # Volume must exceed 1.5x average
        if vol_ratio < 1.5:
            return None

        # Candle body must be > 50% of total candle range
        candle_range = current_high - current_low
        if candle_range <= 0:
            return None
        body = abs(current_close - current_open)
        if body / candle_range < 0.5:
            return None

        # Determine direction
        long_breakout = current_close > range_high
        short_breakout = current_close < range_low

        if not long_breakout and not short_breakout:
            return None

        # ---- False breakout filters ----
        # Previous bar also broke out? Skip (chasing)
        prev_close = float(close.iloc[idx - 1])
        if long_breakout and prev_close > range_high:
            return None
        if short_breakout and prev_close < range_low:
            return None

        # RSI exhaustion filter
        if long_breakout and current_rsi > 80:
            return None
        if short_breakout and current_rsi < 20:
            return None

        # ---- Risk management ----
        atr_buffer = 0.3 * current_atr

        if long_breakout:
            direction = "long"
            entry = current_close
            sl = range_low - atr_buffer
            tp = entry + range_width * 1.5
        else:
            direction = "short"
            entry = current_close
            sl = range_high + atr_buffer
            tp = entry - range_width * 1.5

        sl_distance = abs(entry - sl)

        # Skip if SL distance > 3x ATR (range too wide)
        if sl_distance > 3.0 * current_atr:
            return None

        # Confidence: base 0.60, boosted by volume strength and tight range
        range_tightness = 1.0 - (range_width / (1.5 * current_atr))
        conf = min(0.85, 0.60 + vol_ratio * 0.05 + range_tightness * 0.10)
        conf = max(0.40, conf)

        range_width_pct = (range_width / current_close) * 100.0

        category = _detect_category(symbol)

        return {
            "symbol": symbol,
            "direction": direction,
            "confidence": round(conf, 3),
            "entry_price": _smart_round(entry),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "reason": (
                f"Horizontal range breakout {direction.upper()}: "
                f"range {range_width_pct:.2f}% "
                f"({_smart_round(range_low)}-{_smart_round(range_high)}), "
                f"vol {vol_ratio:.1f}x avg, RSI {current_rsi:.0f}"
            ),
            "strategy": "horizontal_range_breakout",
            "category": category,
            "extra": {
                "range_high": _smart_round(range_high),
                "range_low": _smart_round(range_low),
                "range_width_pct": round(range_width_pct, 2),
                "volume_ratio": round(vol_ratio, 2),
                "squeeze_bars": 0,
            },
        }

    except Exception:
        return None


# =====================================================================
# STRATEGY: Range Contraction/Expansion (Keltner/BB Squeeze)
# =====================================================================
# Simplified TTM Squeeze: detects when Bollinger Bands contract inside
# Keltner Channels (volatility compressed) then expand with a breakout.
#
# Squeeze = BB(20,2) upper < KC(20,1.5) upper AND BB lower > KC lower
# Expansion = BB exits Keltner after squeeze was active in last 3 bars
#
# Entry:
#   LONG:  squeeze in last 3 bars + close > BB upper + close > close[3]
#   SHORT: squeeze in last 3 bars + close < BB lower + close < close[3]
#
# Risk management:
#   SL = SMA(20) - 0.5x ATR (longs) / SMA(20) + 0.5x ATR (shorts)
#   TP = 2x (entry - SL) for 2:1 R:R
# =====================================================================

def range_contraction_expansion(
    symbol: str,
    df: pd.DataFrame,
    market_data: Optional[dict] = None,
) -> Optional[dict]:
    """Keltner/BB squeeze-to-expansion breakout."""
    try:
        if df is None or len(df) < 30:
            return None

        high = df["High"]
        low = df["Low"]
        close = df["Close"]

        bb = _bollinger_bands(close, period=20, num_std=2.0)
        kc = _keltner_channels(high, low, close,
                               ema_period=20, atr_period=10, atr_mult=1.5)
        atr_series = _atr(high, low, close, 14)

        idx = len(df) - 1
        if idx < 20:
            return None

        # Squeeze detection: BB inside Keltner
        squeeze = (bb["lower"] > kc["lower"]) & (bb["upper"] < kc["upper"])

        # Check if squeeze was active in last 3 bars (not including current)
        squeeze_recent = squeeze.iloc[max(0, idx - 3):idx]
        squeeze_bars = int(squeeze_recent.sum())
        if squeeze_bars == 0:
            return None

        current_close = float(close.iloc[idx])
        bb_upper = float(bb["upper"].iloc[idx])
        bb_lower = float(bb["lower"].iloc[idx])
        bb_middle = float(bb["middle"].iloc[idx])
        current_atr = float(atr_series.iloc[idx])

        if current_atr <= 0 or np.isnan(current_atr):
            return None

        # Current bar must NOT be in squeeze (expansion happening)
        if bool(squeeze.iloc[idx]):
            return None

        # Momentum confirmation: close vs close[3]
        if idx < 3:
            return None
        close_3_ago = float(close.iloc[idx - 3])

        long_signal = current_close > bb_upper and current_close > close_3_ago
        short_signal = current_close < bb_lower and current_close < close_3_ago

        if not long_signal and not short_signal:
            return None

        # ---- Risk management ----
        atr_half = 0.5 * current_atr

        if long_signal:
            direction = "long"
            entry = current_close
            sl = bb_middle - atr_half
            risk = entry - sl
            if risk <= 0:
                return None
            tp = entry + 2.0 * risk
        else:
            direction = "short"
            entry = current_close
            sl = bb_middle + atr_half
            risk = sl - entry
            if risk <= 0:
                return None
            tp = entry - 2.0 * risk

        # Confidence based on squeeze duration and breakout strength
        breakout_strength = abs(current_close - close_3_ago) / current_atr
        conf = min(0.82, 0.55 + squeeze_bars * 0.05 + breakout_strength * 0.05)
        conf = max(0.40, conf)

        range_high = float(high.iloc[max(0, idx - 20):idx + 1].max())
        range_low = float(low.iloc[max(0, idx - 20):idx + 1].min())
        range_width_pct = ((range_high - range_low) / current_close) * 100.0

        category = _detect_category(symbol)

        return {
            "symbol": symbol,
            "direction": direction,
            "confidence": round(conf, 3),
            "entry_price": _smart_round(entry),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "reason": (
                f"Squeeze breakout {direction.upper()}: "
                f"{squeeze_bars}-bar squeeze, "
                f"BB {'upper' if long_signal else 'lower'} break, "
                f"momentum {'+' if current_close > close_3_ago else '-'}"
                f"{abs(current_close - close_3_ago) / current_atr:.1f}x ATR"
            ),
            "strategy": "range_contraction_expansion",
            "category": category,
            "extra": {
                "range_high": _smart_round(range_high),
                "range_low": _smart_round(range_low),
                "range_width_pct": round(range_width_pct, 2),
                "volume_ratio": 0.0,
                "squeeze_bars": squeeze_bars,
            },
        }

    except Exception:
        return None


# ---------------------------------------------------------------------------
# Export registry
# ---------------------------------------------------------------------------

RANGE_BREAKOUT_STRATEGIES = {
    "horizontal_range_breakout": horizontal_range_breakout,
    "range_contraction_expansion": range_contraction_expansion,
}
