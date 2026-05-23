"""
ALPHA_ENGINE -- Quantified Divergence Detection + Trading System
================================================================
Proven approach from r/algotrading: combines market structure (trend/BOS context),
regular + hidden divergence, RSI/MFI/TSI multi-indicator momentum, ATR quality
filters, and trailing entry logic. Claims 90%+ directional accuracy on regular
divergence with walk-forward testing on 15+ years of data.

Strategy A: regular_divergence_reversal
  - Regular divergence + Break of Structure + 2/3 momentum agree + ATR filter
  - Regular Bullish: price lower low, indicator higher low -> reversal up
  - Regular Bearish: price higher high, indicator lower high -> reversal down

Strategy B: hidden_divergence_continuation
  - Hidden divergence + trend alignment + momentum + ATR filter
  - Hidden Bullish: price higher low, indicator lower low -> continuation up
  - Hidden Bearish: price lower high, indicator higher high -> continuation down

Strategy C: multi_divergence_confluence
  - Both regular and hidden divergence detected on different indicators simultaneously
  - Highest conviction: multiple independent confirmation

Risk management:
  - TP: 1.5x ATR trailing stop from entry
  - SL: Below divergence swing low (regular) or 1.0x ATR (hidden)
  - Max hold: 7 days

References:
  - Wilder (1978) -- RSI
  - Quong & Soudack (1989) -- Money Flow Index
  - Blau (1991) -- True Strength Index
  - r/algotrading divergence thread -- walk-forward validated approach
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _smart_round(value: float) -> float:
    """Round to sensible precision based on magnitude."""
    if value == 0:
        return 0.0
    abs_val = abs(value)
    if abs_val >= 100:
        return round(value, 2)
    elif abs_val >= 1:
        return round(value, 4)
    elif abs_val >= 0.01:
        return round(value, 6)
    return round(value, 10)


def _detect_category(symbol: str) -> str:
    """Detect asset category from symbol name."""
    s = symbol.upper()
    if "=X" in s:
        return "forex"
    forex_codes = [
        "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF", "SEK", "NOK",
        "DKK", "HKD", "SGD", "ZAR", "MXN", "TRY", "PLN", "HUF", "CZK",
    ]
    for code in forex_codes:
        if s.startswith(code) or s.endswith(code):
            return "forex"
    return "crypto"


def _ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def _sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period, min_periods=period).mean()


def _atr(high: pd.Series, low: pd.Series, close: pd.Series,
         period: int = 14) -> pd.Series:
    """Average True Range -- Wilder (1978)."""
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False).mean()


# ---------------------------------------------------------------------------
# Momentum Indicators (pure Python + numpy/pandas, no ta-lib)
# ---------------------------------------------------------------------------

def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index -- Wilder (1978)."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def _mfi(high: pd.Series, low: pd.Series, close: pd.Series,
         volume: pd.Series, period: int = 14) -> pd.Series:
    """Money Flow Index -- Quong & Soudack (1989). Volume-weighted RSI."""
    typical_price = (high + low + close) / 3.0
    raw_money_flow = typical_price * volume
    direction = typical_price.diff()

    positive_flow = pd.Series(0.0, index=close.index)
    negative_flow = pd.Series(0.0, index=close.index)
    positive_flow[direction > 0] = raw_money_flow[direction > 0]
    negative_flow[direction < 0] = raw_money_flow[direction < 0]

    pos_sum = positive_flow.rolling(window=period, min_periods=period).sum()
    neg_sum = negative_flow.rolling(window=period, min_periods=period).sum()

    mfi = 100.0 - (100.0 / (1.0 + pos_sum / neg_sum.replace(0, np.nan)))
    return mfi


def _tsi(close: pd.Series, long_period: int = 25, short_period: int = 13) -> pd.Series:
    """True Strength Index -- Blau (1991).

    TSI = 100 * EMA(EMA(momentum, long), short) / EMA(EMA(abs(momentum), long), short)
    """
    momentum = close.diff()
    abs_momentum = momentum.abs()

    # Double smooth momentum
    ema_mom_long = momentum.ewm(span=long_period, adjust=False).mean()
    ema_mom_double = ema_mom_long.ewm(span=short_period, adjust=False).mean()

    # Double smooth absolute momentum
    ema_abs_long = abs_momentum.ewm(span=long_period, adjust=False).mean()
    ema_abs_double = ema_abs_long.ewm(span=short_period, adjust=False).mean()

    tsi = 100.0 * ema_mom_double / ema_abs_double.replace(0, np.nan)
    return tsi


# ---------------------------------------------------------------------------
# Swing High/Low Detection
# ---------------------------------------------------------------------------

def _find_swing_highs(high: pd.Series, window: int = 5) -> List[Tuple[int, float]]:
    """Find swing high points: bars where high is the max within +/- window bars."""
    swings = []
    half = window // 2
    values = high.values
    n = len(values)
    for i in range(half, n - half):
        segment = values[max(0, i - half): i + half + 1]
        if not np.isnan(values[i]) and values[i] == np.nanmax(segment):
            # Ensure it's truly a peak (not a plateau)
            left_lower = any(values[j] < values[i] for j in range(max(0, i - half), i))
            right_lower = any(values[j] < values[i] for j in range(i + 1, min(n, i + half + 1)))
            if left_lower and right_lower:
                swings.append((i, float(values[i])))
    return swings


def _find_swing_lows(low: pd.Series, window: int = 5) -> List[Tuple[int, float]]:
    """Find swing low points: bars where low is the min within +/- window bars."""
    swings = []
    half = window // 2
    values = low.values
    n = len(values)
    for i in range(half, n - half):
        segment = values[max(0, i - half): i + half + 1]
        if not np.isnan(values[i]) and values[i] == np.nanmin(segment):
            left_higher = any(values[j] > values[i] for j in range(max(0, i - half), i))
            right_higher = any(values[j] > values[i] for j in range(i + 1, min(n, i + half + 1)))
            if left_higher and right_higher:
                swings.append((i, float(values[i])))
    return swings


# ---------------------------------------------------------------------------
# Divergence Detection Engine
# ---------------------------------------------------------------------------

def detect_divergence(
    close: pd.Series,
    indicator_values: pd.Series,
    high: pd.Series,
    low: pd.Series,
    lookback: int = 14,
    swing_window: int = 5,
) -> List[Dict]:
    """Detect regular and hidden divergences between price and an indicator.

    Regular Bullish: price makes lower low, indicator makes higher low -> reversal up
    Regular Bearish: price makes higher high, indicator makes lower high -> reversal down
    Hidden Bullish: price makes higher low, indicator makes lower low -> continuation up
    Hidden Bearish: price makes lower high, indicator makes higher high -> continuation down

    Returns: list of {bar_index, type, direction, strength, price_swing, indicator_swing}
    """
    divergences: List[Dict] = []

    swing_highs_price = _find_swing_highs(high, swing_window)
    swing_lows_price = _find_swing_lows(low, swing_window)
    swing_highs_ind = _find_swing_highs(indicator_values, swing_window)
    swing_lows_ind = _find_swing_lows(
        indicator_values * -1, swing_window  # invert to find lows
    )
    # Re-extract actual indicator lows (not inverted)
    swing_lows_ind = _find_swing_lows(indicator_values, swing_window)

    n = len(close)
    min_bar = n - lookback * 3  # look back up to 3x lookback

    # --- Check for bullish divergences (at lows) ---
    # Need at least 2 recent swing lows in both price and indicator
    recent_price_lows = [(i, v) for i, v in swing_lows_price if i >= min_bar]
    recent_ind_lows = [(i, v) for i, v in swing_lows_ind if i >= min_bar]

    if len(recent_price_lows) >= 2 and len(recent_ind_lows) >= 2:
        # Use the two most recent lows
        pl_prev, pl_curr = recent_price_lows[-2], recent_price_lows[-1]
        il_prev, il_curr = recent_ind_lows[-2], recent_ind_lows[-1]

        # Ensure swings are roughly aligned in time (within lookback bars)
        if abs(pl_curr[0] - il_curr[0]) <= lookback and abs(pl_prev[0] - il_prev[0]) <= lookback:
            price_lower_low = pl_curr[1] < pl_prev[1]
            ind_higher_low = il_curr[1] > il_prev[1]
            price_higher_low = pl_curr[1] > pl_prev[1]
            ind_lower_low = il_curr[1] < il_prev[1]

            # Regular Bullish: price LL, indicator HL
            if price_lower_low and ind_higher_low:
                price_diff = abs(pl_prev[1] - pl_curr[1]) / max(abs(pl_prev[1]), 1e-10)
                ind_diff = abs(il_curr[1] - il_prev[1]) / max(abs(il_prev[1]), 1e-10)
                strength = min(1.0, (price_diff + ind_diff) * 5.0)
                divergences.append({
                    "bar_index": pl_curr[0],
                    "type": "regular",
                    "direction": "bullish",
                    "strength": round(strength, 3),
                    "price_swing": (pl_prev, pl_curr),
                    "indicator_swing": (il_prev, il_curr),
                })

            # Hidden Bullish: price HL, indicator LL
            if price_higher_low and ind_lower_low:
                price_diff = abs(pl_curr[1] - pl_prev[1]) / max(abs(pl_prev[1]), 1e-10)
                ind_diff = abs(il_prev[1] - il_curr[1]) / max(abs(il_prev[1]), 1e-10)
                strength = min(1.0, (price_diff + ind_diff) * 5.0)
                divergences.append({
                    "bar_index": pl_curr[0],
                    "type": "hidden",
                    "direction": "bullish",
                    "strength": round(strength, 3),
                    "price_swing": (pl_prev, pl_curr),
                    "indicator_swing": (il_prev, il_curr),
                })

    # --- Check for bearish divergences (at highs) ---
    recent_price_highs = [(i, v) for i, v in swing_highs_price if i >= min_bar]
    recent_ind_highs = [(i, v) for i, v in swing_highs_ind if i >= min_bar]

    if len(recent_price_highs) >= 2 and len(recent_ind_highs) >= 2:
        ph_prev, ph_curr = recent_price_highs[-2], recent_price_highs[-1]
        ih_prev, ih_curr = recent_ind_highs[-2], recent_ind_highs[-1]

        if abs(ph_curr[0] - ih_curr[0]) <= lookback and abs(ph_prev[0] - ih_prev[0]) <= lookback:
            price_higher_high = ph_curr[1] > ph_prev[1]
            ind_lower_high = ih_curr[1] < ih_prev[1]
            price_lower_high = ph_curr[1] < ph_prev[1]
            ind_higher_high = ih_curr[1] > ih_prev[1]

            # Regular Bearish: price HH, indicator LH
            if price_higher_high and ind_lower_high:
                price_diff = abs(ph_curr[1] - ph_prev[1]) / max(abs(ph_prev[1]), 1e-10)
                ind_diff = abs(ih_prev[1] - ih_curr[1]) / max(abs(ih_prev[1]), 1e-10)
                strength = min(1.0, (price_diff + ind_diff) * 5.0)
                divergences.append({
                    "bar_index": ph_curr[0],
                    "type": "regular",
                    "direction": "bearish",
                    "strength": round(strength, 3),
                    "price_swing": (ph_prev, ph_curr),
                    "indicator_swing": (ih_prev, ih_curr),
                })

            # Hidden Bearish: price LH, indicator HH
            if price_lower_high and ind_higher_high:
                price_diff = abs(ph_prev[1] - ph_curr[1]) / max(abs(ph_prev[1]), 1e-10)
                ind_diff = abs(ih_curr[1] - ih_prev[1]) / max(abs(ih_prev[1]), 1e-10)
                strength = min(1.0, (price_diff + ind_diff) * 5.0)
                divergences.append({
                    "bar_index": ph_curr[0],
                    "type": "hidden",
                    "direction": "bearish",
                    "strength": round(strength, 3),
                    "price_swing": (ph_prev, ph_curr),
                    "indicator_swing": (ih_prev, ih_curr),
                })

    return divergences


# ---------------------------------------------------------------------------
# Market Structure Detection
# ---------------------------------------------------------------------------

def detect_market_structure(
    close: pd.Series, high: pd.Series, low: pd.Series, swing_window: int = 5,
) -> Dict:
    """Identify market structure: UPTREND, DOWNTREND, RANGING, or BOS.

    UPTREND: higher highs + higher lows
    DOWNTREND: lower highs + lower lows
    RANGING: mixed
    BOS (Break of Structure): swing high/low broken -- potential reversal

    Returns: {trend, bos_bull, bos_bear, last_swing_high, last_swing_low}
    """
    swing_highs = _find_swing_highs(high, swing_window)
    swing_lows = _find_swing_lows(low, swing_window)

    result = {
        "trend": "RANGING",
        "bos_bull": False,
        "bos_bear": False,
        "last_swing_high": None,
        "last_swing_low": None,
    }

    if len(swing_highs) < 3 or len(swing_lows) < 3:
        return result

    # Use last 3 swing highs/lows for structure
    sh = swing_highs[-3:]
    sl = swing_lows[-3:]

    result["last_swing_high"] = sh[-1]
    result["last_swing_low"] = sl[-1]

    # Higher highs and higher lows?
    hh = sh[-1][1] > sh[-2][1] and sh[-2][1] > sh[-3][1]
    hl = sl[-1][1] > sl[-2][1] and sl[-2][1] > sl[-3][1]

    # Lower highs and lower lows?
    lh = sh[-1][1] < sh[-2][1] and sh[-2][1] < sh[-3][1]
    ll = sl[-1][1] < sl[-2][1] and sl[-2][1] < sl[-3][1]

    if hh and hl:
        result["trend"] = "UPTREND"
    elif lh and ll:
        result["trend"] = "DOWNTREND"
    else:
        result["trend"] = "RANGING"

    # Break of Structure detection
    # BOS Bull: current close breaks above the previous swing high
    last_close = float(close.iloc[-1])
    if len(swing_highs) >= 2:
        prev_sh = swing_highs[-2][1]
        if last_close > prev_sh:
            result["bos_bull"] = True

    if len(swing_lows) >= 2:
        prev_sl = swing_lows[-2][1]
        if last_close < prev_sl:
            result["bos_bear"] = True

    return result


# ---------------------------------------------------------------------------
# ATR Quality Filter
# ---------------------------------------------------------------------------

def atr_quality_filter(atr_series: pd.Series, lookback: int = 100) -> bool:
    """ATR must be between 20th and 90th percentile of last N bars.

    Filters out garbage setups in dead markets (too little volatility)
    and extreme chop (too much volatility).
    """
    if len(atr_series) < lookback:
        recent = atr_series.dropna()
    else:
        recent = atr_series.iloc[-lookback:].dropna()

    if len(recent) < 20:
        return False

    current_atr = float(atr_series.iloc[-1])
    if np.isnan(current_atr) or current_atr <= 0:
        return False

    p20 = float(np.nanpercentile(recent.values, 20))
    p90 = float(np.nanpercentile(recent.values, 90))

    return p20 <= current_atr <= p90


# ---------------------------------------------------------------------------
# Multi-Indicator Momentum Agreement (2-of-3)
# ---------------------------------------------------------------------------

def _momentum_agreement(
    rsi_val: float, mfi_val: float, tsi_val: float, direction: str,
) -> Tuple[bool, int, str]:
    """Check if 2-of-3 momentum indicators agree on direction.

    For bullish: RSI < 40 (oversold zone), MFI < 40, TSI < -10
    For bearish: RSI > 60 (overbought zone), MFI > 60, TSI > 10

    Returns: (agreement_met, count, details_string)
    """
    if direction == "bullish":
        rsi_ok = rsi_val < 40
        mfi_ok = mfi_val < 40
        tsi_ok = tsi_val < -10
        label = "oversold"
    else:
        rsi_ok = rsi_val > 60
        mfi_ok = mfi_val > 60
        tsi_ok = tsi_val > 10
        label = "overbought"

    count = sum([rsi_ok, mfi_ok, tsi_ok])
    details = []
    if rsi_ok:
        details.append(f"RSI={rsi_val:.1f}")
    if mfi_ok:
        details.append(f"MFI={mfi_val:.1f}")
    if tsi_ok:
        details.append(f"TSI={tsi_val:.1f}")

    detail_str = f"{count}/3 {label} ({', '.join(details)})" if details else f"0/3 {label}"
    return count >= 2, count, detail_str


# ---------------------------------------------------------------------------
# Trailing Entry Logic
# ---------------------------------------------------------------------------

def _trailing_entry_check(
    close: pd.Series, low: pd.Series, high: pd.Series,
    divergence_bar: int, direction: str, lookback: int = 5,
) -> Tuple[bool, Optional[float]]:
    """Trailing entry: wait for confirmation after divergence.

    Bullish: Wait for price to make a new higher low after divergence,
             then enter on break above the confirmation bar's high.
    Bearish: Wait for price to make a new lower high after divergence,
             then enter on break below the confirmation bar's low.

    Returns: (confirmed, entry_price)
    """
    n = len(close)
    start = divergence_bar + 1
    end = min(n, divergence_bar + lookback + 1)

    if start >= n:
        return False, None

    if direction == "bullish":
        # Find the lowest low after divergence
        post_lows = low.iloc[start:end]
        if len(post_lows) < 2:
            # Not enough bars; check if current bar is higher than div bar
            if n > start and float(low.iloc[-1]) > float(low.iloc[divergence_bar]):
                return True, _smart_round(float(high.iloc[-1]))
            return False, None

        min_idx = post_lows.idxmin()
        min_pos = post_lows.index.get_loc(min_idx) if hasattr(post_lows.index, 'get_loc') else 0
        # Check if a subsequent bar made a higher low
        if min_pos < len(post_lows) - 1:
            for j in range(min_pos + 1, len(post_lows)):
                if float(post_lows.iloc[j]) > float(post_lows.iloc[min_pos]):
                    # Higher low found -> entry is break above that bar's high
                    actual_idx = post_lows.index[j]
                    entry = float(high.loc[actual_idx])
                    return True, _smart_round(entry)
        # Fallback: if last bar's low > divergence bar's low, use it
        if float(low.iloc[-1]) > float(low.iloc[divergence_bar]):
            return True, _smart_round(float(high.iloc[-1]))
    else:
        # Bearish: find the highest high after divergence
        post_highs = high.iloc[start:end]
        if len(post_highs) < 2:
            if n > start and float(high.iloc[-1]) < float(high.iloc[divergence_bar]):
                return True, _smart_round(float(low.iloc[-1]))
            return False, None

        max_idx = post_highs.idxmax()
        max_pos = post_highs.index.get_loc(max_idx) if hasattr(post_highs.index, 'get_loc') else 0
        if max_pos < len(post_highs) - 1:
            for j in range(max_pos + 1, len(post_highs)):
                if float(post_highs.iloc[j]) < float(post_highs.iloc[max_pos]):
                    actual_idx = post_highs.index[j]
                    entry = float(low.loc[actual_idx])
                    return True, _smart_round(entry)
        if float(high.iloc[-1]) < float(high.iloc[divergence_bar]):
            return True, _smart_round(float(low.iloc[-1]))

    return False, None


# ---------------------------------------------------------------------------
# Strategy A: Regular Divergence Reversal
# ---------------------------------------------------------------------------

def regular_divergence_reversal(
    symbol: str, df: pd.DataFrame, market_data: Optional[dict] = None,
) -> List[Dict]:
    """Regular divergence + Break of Structure + 2/3 momentum agree + ATR filter.

    Regular Bullish divergence in DOWNTREND/BOS -> reversal long
    Regular Bearish divergence in UPTREND/BOS -> reversal short
    """
    picks: List[Dict] = []

    if df is None or len(df) < 60:
        return picks

    try:
        close = df["Close"].astype(float)
        high = df["High"].astype(float)
        low = df["Low"].astype(float)
        volume = df["Volume"].astype(float) if "Volume" in df.columns else pd.Series(
            1.0, index=close.index)
    except (KeyError, TypeError):
        return picks

    # Compute indicators
    rsi = _rsi(close, 14)
    mfi = _mfi(high, low, close, volume, 14)
    tsi = _tsi(close, 25, 13)
    atr_vals = _atr(high, low, close, 14)

    # ATR quality gate
    if not atr_quality_filter(atr_vals):
        return picks

    # Market structure
    structure = detect_market_structure(close, high, low)

    # Current indicator values
    i = len(df) - 1
    rsi_now = float(rsi.iloc[i]) if not np.isnan(rsi.iloc[i]) else 50.0
    mfi_now = float(mfi.iloc[i]) if not np.isnan(mfi.iloc[i]) else 50.0
    tsi_now = float(tsi.iloc[i]) if not np.isnan(tsi.iloc[i]) else 0.0
    atr_now = float(atr_vals.iloc[i])
    c = float(close.iloc[i])

    if np.isnan(atr_now) or atr_now <= 0:
        return picks

    category = _detect_category(symbol)

    # Detect divergences on all 3 indicators
    for ind_name, ind_vals in [("RSI", rsi), ("MFI", mfi), ("TSI", tsi)]:
        divs = detect_divergence(close, ind_vals, high, low, lookback=14)

        for div in divs:
            if div["type"] != "regular":
                continue

            bar_idx = div["bar_index"]

            # Only recent divergences (within last 10 bars)
            if i - bar_idx > 10:
                continue

            if div["direction"] == "bullish":
                # Regular bullish -> only in DOWNTREND or BOS_bear (reversal)
                if structure["trend"] not in ("DOWNTREND", "RANGING") and not structure["bos_bear"]:
                    continue

                # 2/3 momentum agreement
                agree, count, detail = _momentum_agreement(rsi_now, mfi_now, tsi_now, "bullish")
                if not agree:
                    continue

                # Trailing entry confirmation
                confirmed, entry_price = _trailing_entry_check(
                    close, low, high, bar_idx, "bullish"
                )
                if not confirmed or entry_price is None:
                    # Fallback: use current close if divergence is very recent
                    if i - bar_idx <= 3:
                        entry_price = _smart_round(c)
                    else:
                        continue

                # SL below the divergence swing low
                div_swing_low = div["price_swing"][1][1]  # current swing low price
                sl = _smart_round(div_swing_low - 0.3 * atr_now)
                risk = entry_price - sl
                if risk <= 0:
                    continue

                # TP: 1.5x ATR trailing from entry
                tp = _smart_round(entry_price + 1.5 * atr_now)
                rr = (tp - entry_price) / risk

                if rr < 1.0:
                    continue

                conf = min(0.90, 0.55
                           + div["strength"] * 0.15
                           + (0.05 if structure["bos_bear"] else 0)
                           + min((count - 2) * 0.05, 0.05)
                           + (0.05 if ind_name == "RSI" else 0))

                picks.append({
                    "symbol": symbol,
                    "direction": "long",
                    "confidence": round(conf, 2),
                    "entry_price": entry_price,
                    "take_profit": tp,
                    "stop_loss": sl,
                    "reason": (
                        f"Regular bullish divergence ({ind_name}): price LL + {ind_name} HL "
                        f"in {structure['trend']}, {detail}, "
                        f"ATR={atr_now:.2f}, strength={div['strength']:.2f}"
                    ),
                    "strategy": "regular_divergence_reversal",
                    "category": category,
                    "risk_reward": round(rr, 2),
                    "timestamp": _now_iso(),
                    "extra": {
                        "divergence_type": "regular_bullish",
                        "indicator": ind_name,
                        "strength": div["strength"],
                        "market_structure": structure["trend"],
                        "bos": structure["bos_bear"],
                        "rsi": round(rsi_now, 1),
                        "mfi": round(mfi_now, 1),
                        "tsi": round(tsi_now, 1),
                        "atr": _smart_round(atr_now),
                        "momentum_agreement": f"{count}/3",
                    },
                })
                break  # One pick per direction per symbol

            elif div["direction"] == "bearish":
                # Regular bearish -> only in UPTREND or BOS_bull (reversal)
                if structure["trend"] not in ("UPTREND", "RANGING") and not structure["bos_bull"]:
                    continue

                agree, count, detail = _momentum_agreement(rsi_now, mfi_now, tsi_now, "bearish")
                if not agree:
                    continue

                confirmed, entry_price = _trailing_entry_check(
                    close, low, high, bar_idx, "bearish"
                )
                if not confirmed or entry_price is None:
                    if i - bar_idx <= 3:
                        entry_price = _smart_round(c)
                    else:
                        continue

                # SL above the divergence swing high
                div_swing_high = div["price_swing"][1][1]
                sl = _smart_round(div_swing_high + 0.3 * atr_now)
                risk = sl - entry_price
                if risk <= 0:
                    continue

                tp = _smart_round(entry_price - 1.5 * atr_now)
                rr = (entry_price - tp) / risk

                if rr < 1.0:
                    continue

                conf = min(0.90, 0.55
                           + div["strength"] * 0.15
                           + (0.05 if structure["bos_bull"] else 0)
                           + min((count - 2) * 0.05, 0.05)
                           + (0.05 if ind_name == "RSI" else 0))

                picks.append({
                    "symbol": symbol,
                    "direction": "short",
                    "confidence": round(conf, 2),
                    "entry_price": entry_price,
                    "take_profit": tp,
                    "stop_loss": sl,
                    "reason": (
                        f"Regular bearish divergence ({ind_name}): price HH + {ind_name} LH "
                        f"in {structure['trend']}, {detail}, "
                        f"ATR={atr_now:.2f}, strength={div['strength']:.2f}"
                    ),
                    "strategy": "regular_divergence_reversal",
                    "category": category,
                    "risk_reward": round(rr, 2),
                    "timestamp": _now_iso(),
                    "extra": {
                        "divergence_type": "regular_bearish",
                        "indicator": ind_name,
                        "strength": div["strength"],
                        "market_structure": structure["trend"],
                        "bos": structure["bos_bull"],
                        "rsi": round(rsi_now, 1),
                        "mfi": round(mfi_now, 1),
                        "tsi": round(tsi_now, 1),
                        "atr": _smart_round(atr_now),
                        "momentum_agreement": f"{count}/3",
                    },
                })
                break

    return picks


# ---------------------------------------------------------------------------
# Strategy B: Hidden Divergence Continuation
# ---------------------------------------------------------------------------

def hidden_divergence_continuation(
    symbol: str, df: pd.DataFrame, market_data: Optional[dict] = None,
) -> List[Dict]:
    """Hidden divergence + trend alignment + 2/3 momentum + ATR filter.

    Hidden Bullish in UPTREND -> continuation long
    Hidden Bearish in DOWNTREND -> continuation short
    """
    picks: List[Dict] = []

    if df is None or len(df) < 60:
        return picks

    try:
        close = df["Close"].astype(float)
        high = df["High"].astype(float)
        low = df["Low"].astype(float)
        volume = df["Volume"].astype(float) if "Volume" in df.columns else pd.Series(
            1.0, index=close.index)
    except (KeyError, TypeError):
        return picks

    rsi = _rsi(close, 14)
    mfi = _mfi(high, low, close, volume, 14)
    tsi = _tsi(close, 25, 13)
    atr_vals = _atr(high, low, close, 14)

    if not atr_quality_filter(atr_vals):
        return picks

    structure = detect_market_structure(close, high, low)

    i = len(df) - 1
    rsi_now = float(rsi.iloc[i]) if not np.isnan(rsi.iloc[i]) else 50.0
    mfi_now = float(mfi.iloc[i]) if not np.isnan(mfi.iloc[i]) else 50.0
    tsi_now = float(tsi.iloc[i]) if not np.isnan(tsi.iloc[i]) else 0.0
    atr_now = float(atr_vals.iloc[i])
    c = float(close.iloc[i])

    if np.isnan(atr_now) or atr_now <= 0:
        return picks

    category = _detect_category(symbol)

    for ind_name, ind_vals in [("RSI", rsi), ("MFI", mfi), ("TSI", tsi)]:
        divs = detect_divergence(close, ind_vals, high, low, lookback=14)

        for div in divs:
            if div["type"] != "hidden":
                continue

            bar_idx = div["bar_index"]
            if i - bar_idx > 10:
                continue

            if div["direction"] == "bullish":
                # Hidden bullish -> only in UPTREND (continuation)
                if structure["trend"] != "UPTREND":
                    continue

                agree, count, detail = _momentum_agreement(rsi_now, mfi_now, tsi_now, "bullish")
                if not agree:
                    continue

                confirmed, entry_price = _trailing_entry_check(
                    close, low, high, bar_idx, "bullish"
                )
                if not confirmed or entry_price is None:
                    if i - bar_idx <= 3:
                        entry_price = _smart_round(c)
                    else:
                        continue

                # SL: 1.0x ATR below entry (hidden div uses tighter stop)
                sl = _smart_round(entry_price - 1.0 * atr_now)
                risk = entry_price - sl
                if risk <= 0:
                    continue

                tp = _smart_round(entry_price + 1.5 * atr_now)
                rr = (tp - entry_price) / risk

                if rr < 1.0:
                    continue

                conf = min(0.88, 0.55
                           + div["strength"] * 0.12
                           + (0.08 if structure["trend"] == "UPTREND" else 0)
                           + min((count - 2) * 0.05, 0.05))

                picks.append({
                    "symbol": symbol,
                    "direction": "long",
                    "confidence": round(conf, 2),
                    "entry_price": entry_price,
                    "take_profit": tp,
                    "stop_loss": sl,
                    "reason": (
                        f"Hidden bullish divergence ({ind_name}): price HL + {ind_name} LL "
                        f"in {structure['trend']} (continuation), {detail}, "
                        f"ATR={atr_now:.2f}"
                    ),
                    "strategy": "hidden_divergence_continuation",
                    "category": category,
                    "risk_reward": round(rr, 2),
                    "timestamp": _now_iso(),
                    "extra": {
                        "divergence_type": "hidden_bullish",
                        "indicator": ind_name,
                        "strength": div["strength"],
                        "market_structure": structure["trend"],
                        "rsi": round(rsi_now, 1),
                        "mfi": round(mfi_now, 1),
                        "tsi": round(tsi_now, 1),
                        "atr": _smart_round(atr_now),
                        "momentum_agreement": f"{count}/3",
                    },
                })
                break

            elif div["direction"] == "bearish":
                # Hidden bearish -> only in DOWNTREND (continuation)
                if structure["trend"] != "DOWNTREND":
                    continue

                agree, count, detail = _momentum_agreement(rsi_now, mfi_now, tsi_now, "bearish")
                if not agree:
                    continue

                confirmed, entry_price = _trailing_entry_check(
                    close, low, high, bar_idx, "bearish"
                )
                if not confirmed or entry_price is None:
                    if i - bar_idx <= 3:
                        entry_price = _smart_round(c)
                    else:
                        continue

                sl = _smart_round(entry_price + 1.0 * atr_now)
                risk = sl - entry_price
                if risk <= 0:
                    continue

                tp = _smart_round(entry_price - 1.5 * atr_now)
                rr = (entry_price - tp) / risk

                if rr < 1.0:
                    continue

                conf = min(0.88, 0.55
                           + div["strength"] * 0.12
                           + (0.08 if structure["trend"] == "DOWNTREND" else 0)
                           + min((count - 2) * 0.05, 0.05))

                picks.append({
                    "symbol": symbol,
                    "direction": "short",
                    "confidence": round(conf, 2),
                    "entry_price": entry_price,
                    "take_profit": tp,
                    "stop_loss": sl,
                    "reason": (
                        f"Hidden bearish divergence ({ind_name}): price LH + {ind_name} HH "
                        f"in {structure['trend']} (continuation), {detail}, "
                        f"ATR={atr_now:.2f}"
                    ),
                    "strategy": "hidden_divergence_continuation",
                    "category": category,
                    "risk_reward": round(rr, 2),
                    "timestamp": _now_iso(),
                    "extra": {
                        "divergence_type": "hidden_bearish",
                        "indicator": ind_name,
                        "strength": div["strength"],
                        "market_structure": structure["trend"],
                        "rsi": round(rsi_now, 1),
                        "mfi": round(mfi_now, 1),
                        "tsi": round(tsi_now, 1),
                        "atr": _smart_round(atr_now),
                        "momentum_agreement": f"{count}/3",
                    },
                })
                break

    return picks


# ---------------------------------------------------------------------------
# Strategy C: Multi-Divergence Confluence
# ---------------------------------------------------------------------------

def multi_divergence_confluence(
    symbol: str, df: pd.DataFrame, market_data: Optional[dict] = None,
) -> List[Dict]:
    """Both regular AND hidden divergence on different indicators simultaneously.

    Highest conviction: multiple independent divergence confirmations.
    """
    picks: List[Dict] = []

    if df is None or len(df) < 60:
        return picks

    try:
        close = df["Close"].astype(float)
        high = df["High"].astype(float)
        low = df["Low"].astype(float)
        volume = df["Volume"].astype(float) if "Volume" in df.columns else pd.Series(
            1.0, index=close.index)
    except (KeyError, TypeError):
        return picks

    rsi = _rsi(close, 14)
    mfi = _mfi(high, low, close, volume, 14)
    tsi = _tsi(close, 25, 13)
    atr_vals = _atr(high, low, close, 14)

    if not atr_quality_filter(atr_vals):
        return picks

    structure = detect_market_structure(close, high, low)

    i = len(df) - 1
    rsi_now = float(rsi.iloc[i]) if not np.isnan(rsi.iloc[i]) else 50.0
    mfi_now = float(mfi.iloc[i]) if not np.isnan(mfi.iloc[i]) else 50.0
    tsi_now = float(tsi.iloc[i]) if not np.isnan(tsi.iloc[i]) else 0.0
    atr_now = float(atr_vals.iloc[i])
    c = float(close.iloc[i])

    if np.isnan(atr_now) or atr_now <= 0:
        return picks

    category = _detect_category(symbol)

    # Collect all divergences across indicators
    all_divs: Dict[str, List[Dict]] = {}
    for ind_name, ind_vals in [("RSI", rsi), ("MFI", mfi), ("TSI", tsi)]:
        divs = detect_divergence(close, ind_vals, high, low, lookback=14)
        for div in divs:
            if i - div["bar_index"] > 10:
                continue
            key = f"{div['direction']}"
            if key not in all_divs:
                all_divs[key] = []
            all_divs[key].append({**div, "indicator": ind_name})

    # Need divergences on 2+ different indicators in the same direction
    for direction in ("bullish", "bearish"):
        divs_in_dir = all_divs.get(direction, [])
        if len(divs_in_dir) < 2:
            continue

        # Check that at least 2 different indicators are involved
        indicators_involved = set(d["indicator"] for d in divs_in_dir)
        if len(indicators_involved) < 2:
            continue

        # Check for mix of regular + hidden (bonus) or at least 2 of same type
        types_found = set(d["type"] for d in divs_in_dir)
        has_both_types = len(types_found) >= 2

        # Momentum agreement
        agree, count, detail = _momentum_agreement(
            rsi_now, mfi_now, tsi_now, direction
        )
        if not agree:
            continue

        # Best divergence for entry timing
        best_div = max(divs_in_dir, key=lambda d: d["strength"])
        bar_idx = best_div["bar_index"]

        if direction == "bullish":
            confirmed, entry_price = _trailing_entry_check(
                close, low, high, bar_idx, "bullish"
            )
            if not confirmed or entry_price is None:
                entry_price = _smart_round(c)

            # Tightest SL for high-conviction: swing low - 0.2 ATR
            swing_low = min(d["price_swing"][1][1] for d in divs_in_dir
                            if d["direction"] == "bullish")
            sl = _smart_round(swing_low - 0.2 * atr_now)
            risk = entry_price - sl
            if risk <= 0:
                continue

            tp = _smart_round(entry_price + 1.5 * atr_now)
            rr = (tp - entry_price) / risk

            if rr < 1.0:
                continue

            conf = min(0.92, 0.60
                       + best_div["strength"] * 0.10
                       + (0.05 if has_both_types else 0)
                       + len(indicators_involved) * 0.03
                       + min((count - 2) * 0.05, 0.05))

            ind_list = ", ".join(sorted(indicators_involved))
            type_list = "+".join(sorted(types_found))

            picks.append({
                "symbol": symbol,
                "direction": "long",
                "confidence": round(conf, 2),
                "entry_price": entry_price,
                "take_profit": tp,
                "stop_loss": sl,
                "reason": (
                    f"Multi-divergence confluence LONG: {type_list} bullish on "
                    f"{ind_list}, {detail}, {structure['trend']}, "
                    f"strength={best_div['strength']:.2f}"
                ),
                "strategy": "multi_divergence_confluence",
                "category": category,
                "risk_reward": round(rr, 2),
                "timestamp": _now_iso(),
                "extra": {
                    "divergence_types": type_list,
                    "indicators": ind_list,
                    "num_divergences": len(divs_in_dir),
                    "has_both_types": has_both_types,
                    "best_strength": best_div["strength"],
                    "market_structure": structure["trend"],
                    "rsi": round(rsi_now, 1),
                    "mfi": round(mfi_now, 1),
                    "tsi": round(tsi_now, 1),
                    "atr": _smart_round(atr_now),
                    "momentum_agreement": f"{count}/3",
                },
            })

        elif direction == "bearish":
            confirmed, entry_price = _trailing_entry_check(
                close, low, high, bar_idx, "bearish"
            )
            if not confirmed or entry_price is None:
                entry_price = _smart_round(c)

            swing_high = max(d["price_swing"][1][1] for d in divs_in_dir
                             if d["direction"] == "bearish")
            sl = _smart_round(swing_high + 0.2 * atr_now)
            risk = sl - entry_price
            if risk <= 0:
                continue

            tp = _smart_round(entry_price - 1.5 * atr_now)
            rr = (entry_price - tp) / risk

            if rr < 1.0:
                continue

            conf = min(0.92, 0.60
                       + best_div["strength"] * 0.10
                       + (0.05 if has_both_types else 0)
                       + len(indicators_involved) * 0.03
                       + min((count - 2) * 0.05, 0.05))

            ind_list = ", ".join(sorted(indicators_involved))
            type_list = "+".join(sorted(types_found))

            picks.append({
                "symbol": symbol,
                "direction": "short",
                "confidence": round(conf, 2),
                "entry_price": entry_price,
                "take_profit": tp,
                "stop_loss": sl,
                "reason": (
                    f"Multi-divergence confluence SHORT: {type_list} bearish on "
                    f"{ind_list}, {detail}, {structure['trend']}, "
                    f"strength={best_div['strength']:.2f}"
                ),
                "strategy": "multi_divergence_confluence",
                "category": category,
                "risk_reward": round(rr, 2),
                "timestamp": _now_iso(),
                "extra": {
                    "divergence_types": type_list,
                    "indicators": ind_list,
                    "num_divergences": len(divs_in_dir),
                    "has_both_types": has_both_types,
                    "best_strength": best_div["strength"],
                    "market_structure": structure["trend"],
                    "rsi": round(rsi_now, 1),
                    "mfi": round(mfi_now, 1),
                    "tsi": round(tsi_now, 1),
                    "atr": _smart_round(atr_now),
                    "momentum_agreement": f"{count}/3",
                },
            })

    return picks


# ---------------------------------------------------------------------------
# Backtest Engine (90 days, 4H, via api_failover)
# ---------------------------------------------------------------------------

BACKTEST_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT",
    "DOGEUSDT", "AVAXUSDT", "RENDERUSDT", "FETUSDT",
]


def _fetch_4h_data(symbol: str, limit: int = 540) -> Optional[pd.DataFrame]:
    """Fetch 4H OHLCV data via api_failover (90 days ~ 540 bars at 4H).

    Uses 3+ fallback chain: Binance mirrors -> Bybit -> KuCoin -> CoinGecko -> CryptoCompare
    """
    try:
        from api_failover import fetch_klines
    except ImportError:
        logger.warning("api_failover not available for backtest data fetch")
        return None

    klines = fetch_klines(symbol, interval="4h", limit=limit)
    if not klines or len(klines) < 60:
        return None

    rows = []
    for k in klines:
        try:
            rows.append({
                "Open": float(k[1]),
                "High": float(k[2]),
                "Low": float(k[3]),
                "Close": float(k[4]),
                "Volume": float(k[5]),
                "Timestamp": int(k[0]),
            })
        except (IndexError, ValueError, TypeError):
            continue

    if len(rows) < 60:
        return None

    df = pd.DataFrame(rows)
    df.sort_values("Timestamp", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def run_backtest(symbols: Optional[List[str]] = None) -> Dict:
    """Run walk-forward backtest on 90 days of 4H data.

    TP: 1.5x ATR trailing stop from entry
    SL: Below divergence swing low (regular) or 1.0x ATR (hidden)
    Max hold: 7 days (42 bars at 4H)

    Returns: {symbol: {strategy: {trades, wins, losses, win_rate, avg_rr, pnl_pct}}}
    """
    if symbols is None:
        symbols = BACKTEST_SYMBOLS

    results: Dict = {}
    max_hold_bars = 42  # 7 days at 4H

    for sym in symbols:
        df = _fetch_4h_data(sym)
        if df is None:
            logger.warning("Backtest: no data for %s", sym)
            continue

        close = df["Close"].astype(float)
        high = df["High"].astype(float)
        low = df["Low"].astype(float)
        volume = df["Volume"].astype(float)

        rsi = _rsi(close, 14)
        mfi = _mfi(high, low, close, volume, 14)
        tsi = _tsi(close, 25, 13)
        atr_vals = _atr(high, low, close, 14)

        sym_results: Dict = {}

        for strategy_name in ["regular_divergence_reversal", "hidden_divergence_continuation",
                              "multi_divergence_confluence"]:
            trades = []
            # Walk forward: start at bar 60, step through
            window = 60
            step = 1

            for start in range(0, len(df) - window, step):
                end = start + window
                if end >= len(df):
                    break

                sub_df = df.iloc[start:end].copy()
                sub_df.reset_index(drop=True, inplace=True)

                if strategy_name == "regular_divergence_reversal":
                    picks = regular_divergence_reversal(sym, sub_df)
                elif strategy_name == "hidden_divergence_continuation":
                    picks = hidden_divergence_continuation(sym, sub_df)
                else:
                    picks = multi_divergence_confluence(sym, sub_df)

                for pick in picks:
                    entry = pick["entry_price"]
                    tp = pick["take_profit"]
                    sl = pick["stop_loss"]
                    direction = pick["direction"]

                    # Simulate forward from entry
                    outcome = "timeout"
                    exit_price = entry
                    bars_held = 0

                    for j in range(end, min(end + max_hold_bars, len(df))):
                        bars_held += 1
                        h = float(high.iloc[j])
                        l = float(low.iloc[j])
                        c_j = float(close.iloc[j])

                        if direction == "long":
                            if l <= sl:
                                outcome = "loss"
                                exit_price = sl
                                break
                            if h >= tp:
                                outcome = "win"
                                exit_price = tp
                                break
                        else:  # short
                            if h >= sl:
                                outcome = "loss"
                                exit_price = sl
                                break
                            if l <= tp:
                                outcome = "win"
                                exit_price = tp
                                break

                    if outcome == "timeout":
                        # Exit at last bar's close
                        last_idx = min(end + max_hold_bars - 1, len(df) - 1)
                        exit_price = float(close.iloc[last_idx])
                        if direction == "long":
                            outcome = "win" if exit_price > entry else "loss"
                        else:
                            outcome = "win" if exit_price < entry else "loss"

                    if direction == "long":
                        pnl_pct = (exit_price - entry) / entry * 100
                    else:
                        pnl_pct = (entry - exit_price) / entry * 100

                    trades.append({
                        "outcome": outcome,
                        "pnl_pct": round(pnl_pct, 2),
                        "bars_held": bars_held,
                        "direction": direction,
                        "entry": entry,
                        "exit": _smart_round(exit_price),
                    })

            if trades:
                wins = sum(1 for t in trades if t["outcome"] == "win")
                losses = sum(1 for t in trades if t["outcome"] == "loss")
                total = len(trades)
                avg_pnl = sum(t["pnl_pct"] for t in trades) / total
                win_pnls = [t["pnl_pct"] for t in trades if t["outcome"] == "win"]
                loss_pnls = [t["pnl_pct"] for t in trades if t["outcome"] == "loss"]
                avg_win = sum(win_pnls) / len(win_pnls) if win_pnls else 0
                avg_loss = sum(loss_pnls) / len(loss_pnls) if loss_pnls else 0

                sym_results[strategy_name] = {
                    "trades": total,
                    "wins": wins,
                    "losses": losses,
                    "win_rate": round(wins / total * 100, 1) if total > 0 else 0,
                    "avg_pnl_pct": round(avg_pnl, 2),
                    "avg_win_pct": round(avg_win, 2),
                    "avg_loss_pct": round(avg_loss, 2),
                    "total_pnl_pct": round(sum(t["pnl_pct"] for t in trades), 2),
                }

        if sym_results:
            results[sym] = sym_results

    return results


# ---------------------------------------------------------------------------
# Export: DIVERGENCE_STRATEGIES dict for scanner.py
# ---------------------------------------------------------------------------

TECHNICAL_DIVERGENCE_STRATEGIES = {
    "regular_divergence_reversal": regular_divergence_reversal,
    "hidden_divergence_continuation": hidden_divergence_continuation,
    "multi_divergence_confluence": multi_divergence_confluence,
}


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    print("=" * 70)
    print("Divergence Strategy Backtest -- 90 days, 4H, 8 symbols")
    print("=" * 70)
    results = run_backtest()
    if results:
        print(json.dumps(results, indent=2))
        print("\n--- Summary ---")
        for sym, strats in results.items():
            for sname, stats in strats.items():
                print(f"  {sym} | {sname}: {stats['trades']} trades, "
                      f"WR={stats['win_rate']}%, PnL={stats['total_pnl_pct']:.1f}%")
    else:
        print("No backtest results (check api_failover availability)")
