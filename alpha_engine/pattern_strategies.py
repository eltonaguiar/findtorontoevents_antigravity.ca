"""
ALPHA_ENGINE -- Pattern Detection & Support/Resistance Strategies (Wave 7)
==========================================================================
10 strategies for chart pattern detection, support/resistance analysis,
volume profile trading, and template-based price forecasting.

Strategies 74-83:
  74. fractal_sr_bounce           -- Williams fractal S/R with touch counting
                                    Window=5, cluster 0.5%, strength scoring
  75. double_top_bottom_detector  -- Double top/bottom with measured move
                                    Bulkowski (2005): 78% success double bottoms
  76. head_shoulders_detector     -- H&S and Inverse H&S pattern detection
                                    Bulkowski (2005): 83% success H&S tops
  77. ascending_triangle_breakout -- Flat resistance + rising lows breakout
                                    Bulkowski (2005): 64% break upward
  78. sr_breakout_retest          -- S/R flip retest: old R→new S and vice versa
                                    Higher-probability entry after confirmed break
  79. price_level_magnetism       -- Round numbers, VWAP, and key levels as magnets
                                    Price memory/attraction with RSI confluence
  80. pattern_repetition_forecast -- Template matching: find similar historical bars
                                    Vectorized Z-score distance, t-test validation
  81. volume_profile_value_area   -- Volume profile: buy below VAL, sell above VAH
                                    70% volume concentration at POC
  82. multi_touch_level_strength  -- Touch-count-based S/R prediction
                                    3-4 touches → bounce, 5+ → breakout (Bulkowski)
  83. failed_breakout_reversal    -- Failed breakout / bull & bear trap detection
                                    Bulkowski (2005): 72% success rate

References:
  - Bulkowski, T. (2005). Encyclopedia of Chart Patterns, 2nd Ed. Wiley.
  - Williams, B. (1995). Trading Chaos. Wiley. (Fractal pivots)
  - Steidlmayer, J.P. (1986). Market Profile. CBOT. (Volume Profile, POC, VA)
  - Lo, Mamaysky & Wang (2000). "Foundations of Technical Analysis."
    Journal of Finance, 55(4), 1705-1765. (Pattern recognition)
  - Caginalp & Laurent (1998). "The Predictive Power of Price Patterns."
    Applied Mathematical Finance, 5(3-4), 181-205. (Template matching)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd
from config import CRYPTO_SYMBOLS, ALL_SYMBOLS
from indicators import (
    sma, ema, rsi, atr, bollinger_bands, volume_ratio, vwap_session, obv,
)


# -- Helpers (same pattern as crypto_strategies) ------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_category(symbol: str) -> str:
    info = ALL_SYMBOLS.get(symbol, {})
    return info.get("cat", "crypto")


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


def _atr_tp_sl(close: pd.Series, high: pd.Series, low: pd.Series,
               tp_mult: float = 3.0, sl_mult: float = 1.5,
               atr_period: int = 14) -> tuple[float, float, float]:
    atr_val = atr(high, low, close, atr_period)
    current_atr = float(atr_val.iloc[-1])
    price = float(close.iloc[-1])
    tp = price + tp_mult * current_atr
    sl = price - sl_mult * current_atr
    return _smart_round(price), _smart_round(tp), _smart_round(sl)


# -- Fractal & S/R Helpers ----------------------------------------------


def _find_fractal_pivots(
    high: pd.Series,
    low: pd.Series,
    window: int = 5,
) -> list[tuple[int, float, str]]:
    """
    Williams fractal pivot detection.

    A fractal high is a bar whose high is the highest within *window* bars
    on each side.  A fractal low is the mirror image.

    Returns list of ``(index_position, price, 'high'|'low')`` sorted by
    index_position ascending.

    Reference: Williams (1995), *Trading Chaos*.
    """
    pivots: list[tuple[int, float, str]] = []
    n = len(high)
    half = window // 2

    high_arr = high.values.astype(float)
    low_arr = low.values.astype(float)

    for i in range(half, n - half):
        # Check fractal high: bar i must be >= all bars in window
        is_high = True
        for j in range(i - half, i + half + 1):
            if j == i:
                continue
            if high_arr[j] > high_arr[i]:
                is_high = False
                break
        if is_high:
            pivots.append((i, float(high_arr[i]), "high"))

        # Check fractal low: bar i must be <= all bars in window
        is_low = True
        for j in range(i - half, i + half + 1):
            if j == i:
                continue
            if low_arr[j] < low_arr[i]:
                is_low = False
                break
        if is_low:
            pivots.append((i, float(low_arr[i]), "low"))

    return sorted(pivots, key=lambda x: x[0])


def _cluster_pivots_to_levels(
    pivots: list[tuple[int, float, str]],
    tolerance_pct: float = 0.005,
    min_touches: int = 3,
    total_bars: int = 200,
) -> list[dict]:
    """
    Cluster fractal pivots within *tolerance_pct* into discrete S/R levels.

    Each returned dict has:
      - ``level``:  average price of the cluster
      - ``touches``: number of pivots in the cluster
      - ``type``:   'support' | 'resistance' | 'both'
      - ``first_idx``: bar index of earliest touch
      - ``last_idx``:  bar index of latest touch
      - ``bar_span``:  last_idx - first_idx
      - ``volumes``:   list of bar indices for volume-weighting
    """
    if not pivots:
        return []

    used = [False] * len(pivots)
    levels: list[dict] = []

    for i, (idx_i, price_i, type_i) in enumerate(pivots):
        if used[i]:
            continue
        cluster_prices: list[float] = [price_i]
        cluster_indices: list[int] = [idx_i]
        cluster_types: set[str] = {type_i}
        used[i] = True

        for j in range(i + 1, len(pivots)):
            if used[j]:
                continue
            _, price_j, type_j = pivots[j]
            if abs(price_j - price_i) / max(price_i, 1e-10) <= tolerance_pct:
                cluster_prices.append(price_j)
                cluster_indices.append(pivots[j][0])
                cluster_types.add(type_j)
                used[j] = True

        if len(cluster_prices) < min_touches:
            continue

        avg_price = float(np.mean(cluster_prices))
        if "high" in cluster_types and "low" in cluster_types:
            level_type = "both"
        elif "high" in cluster_types:
            level_type = "resistance"
        else:
            level_type = "support"

        first_idx = min(cluster_indices)
        last_idx = max(cluster_indices)

        # Recency weight: levels that were touched more recently are stronger
        recency = 1.0 + 0.5 * (last_idx / max(total_bars, 1))

        levels.append({
            "level": avg_price,
            "touches": len(cluster_prices),
            "type": level_type,
            "first_idx": first_idx,
            "last_idx": last_idx,
            "bar_span": last_idx - first_idx,
            "recency_weight": round(recency, 3),
            "indices": cluster_indices,
        })

    # Sort by strength (touches * recency) descending
    levels.sort(key=lambda lv: lv["touches"] * lv["recency_weight"], reverse=True)
    return levels


def _build_volume_profile(
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    volume: pd.Series,
    n_bins: int = 50,
    lookback: int = 30,
) -> dict:
    """
    Build a volume profile from the last *lookback* bars.

    Returns dict with:
      - ``poc``:     Point of Control (price level with max volume)
      - ``val``:     Value Area Low
      - ``vah``:     Value Area High
      - ``poc_vol``: volume at POC bin
      - ``avg_vol``: average volume per bin
      - ``bins``:    array of bin edges
      - ``profile``: array of volume per bin

    Reference: Steidlmayer (1986), Market Profile. CBOT.
    """
    h = high.iloc[-lookback:].values.astype(float)
    l = low.iloc[-lookback:].values.astype(float)
    c = close.iloc[-lookback:].values.astype(float)
    v = volume.iloc[-lookback:].values.astype(float)

    price_min = float(np.nanmin(l))
    price_max = float(np.nanmax(h))

    if price_max <= price_min or price_max == 0:
        return {}

    bin_edges = np.linspace(price_min, price_max, n_bins + 1)
    profile = np.zeros(n_bins)

    for i in range(len(c)):
        bar_low = l[i]
        bar_high = h[i]
        bar_vol = v[i]
        if np.isnan(bar_low) or np.isnan(bar_high) or np.isnan(bar_vol):
            continue
        if bar_high <= bar_low:
            bar_high = bar_low + 1e-10

        # Distribute volume across bins that the bar spans
        for b in range(n_bins):
            bin_lo = bin_edges[b]
            bin_hi = bin_edges[b + 1]
            # Overlap between bar range and bin range
            overlap_lo = max(bar_low, bin_lo)
            overlap_hi = min(bar_high, bin_hi)
            if overlap_hi > overlap_lo:
                frac = (overlap_hi - overlap_lo) / (bar_high - bar_low)
                profile[b] += bar_vol * frac

    if profile.sum() == 0:
        return {}

    poc_idx = int(np.argmax(profile))
    poc_price = float((bin_edges[poc_idx] + bin_edges[poc_idx + 1]) / 2.0)
    poc_vol = float(profile[poc_idx])
    avg_vol = float(profile.mean())

    # Value Area: 70% of total volume, expanding from POC
    total_vol = profile.sum()
    target_vol = total_vol * 0.70
    va_vol = profile[poc_idx]
    lo_idx = poc_idx
    hi_idx = poc_idx

    while va_vol < target_vol:
        expand_lo = profile[lo_idx - 1] if lo_idx > 0 else 0
        expand_hi = profile[hi_idx + 1] if hi_idx < n_bins - 1 else 0

        if expand_lo == 0 and expand_hi == 0:
            break

        if expand_lo >= expand_hi and lo_idx > 0:
            lo_idx -= 1
            va_vol += profile[lo_idx]
        elif hi_idx < n_bins - 1:
            hi_idx += 1
            va_vol += profile[hi_idx]
        elif lo_idx > 0:
            lo_idx -= 1
            va_vol += profile[lo_idx]
        else:
            break

    val_price = float((bin_edges[lo_idx] + bin_edges[lo_idx + 1]) / 2.0)
    vah_price = float((bin_edges[hi_idx] + bin_edges[hi_idx + 1]) / 2.0)

    return {
        "poc": poc_price,
        "val": val_price,
        "vah": vah_price,
        "poc_vol": poc_vol,
        "avg_vol": avg_vol,
        "bins": bin_edges,
        "profile": profile,
    }


# =====================================================================
# STRATEGY 74: Fractal S/R Bounce
# =====================================================================
# Williams fractal pivots (window=5) clustered into S/R levels.
# Trade bounces off well-tested levels (3+ touches).
# Reference: Williams (1995), "Trading Chaos"
# =====================================================================

def fractal_sr_bounce(
    data: dict[str, pd.DataFrame],
    context: Optional[dict] = None,
) -> list[dict]:
    """
    Fractal support/resistance detection with touch counting and bounce trading.

    Finds Williams fractal pivots, clusters them into S/R levels, scores each
    level by (touch_count * recency * volume_weight), and generates BUY/SELL
    when price is within 0.5 ATR of a strong level.

    Reference: Williams (1995), *Trading Chaos*. Wiley.
    """
    signals: list[dict] = []

    for symbol in CRYPTO_SYMBOLS:
        try:
            if symbol not in data:
                continue
            df = data[symbol]
            if len(df) < 60:
                continue

            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]
            price = float(close.iloc[-1])

            # ATR for proximity threshold
            atr_val = atr(high, low, close, 14)
            current_atr = float(atr_val.iloc[-1])
            if current_atr == 0 or np.isnan(current_atr):
                continue

            # Find fractal pivots and cluster into levels
            pivots = _find_fractal_pivots(high, low, window=5)
            if len(pivots) < 6:
                continue

            levels = _cluster_pivots_to_levels(
                pivots,
                tolerance_pct=0.005,
                min_touches=3,
                total_bars=len(df),
            )
            if not levels:
                continue

            # Volume weighting for each level
            vol_arr = volume.values.astype(float)
            avg_volume = float(np.nanmean(vol_arr[-60:]))
            if avg_volume <= 0:
                avg_volume = 1.0

            for lvl in levels:
                level_price = lvl["level"]
                touches = lvl["touches"]
                lvl_type = lvl["type"]
                recency_w = lvl["recency_weight"]
                bar_span = lvl["bar_span"]

                # Volume at touch points
                touch_vols = []
                for idx in lvl["indices"]:
                    if 0 <= idx < len(vol_arr):
                        touch_vols.append(vol_arr[idx])
                vol_at_touch = float(np.mean(touch_vols)) if touch_vols else avg_volume
                vol_weight = min(2.0, vol_at_touch / avg_volume)

                strength = touches * recency_w * vol_weight

                # Check proximity: within 0.5 ATR of level
                distance = abs(price - level_price)
                if distance > 0.5 * current_atr:
                    continue

                # Determine signal type
                if price <= level_price and lvl_type in ("support", "both"):
                    signal_type = "BUY"
                    # TP: next resistance level above, or 2.5*ATR
                    next_r = None
                    for other in levels:
                        if other["level"] > price and other["type"] in (
                            "resistance", "both",
                        ):
                            next_r = other["level"]
                            break
                    tp = next_r if next_r else price + 2.5 * current_atr
                    sl = level_price - 0.005 * level_price  # 0.5% beyond level
                elif price >= level_price and lvl_type in ("resistance", "both"):
                    signal_type = "SELL"
                    # TP: next support level below, or 2.5*ATR down
                    next_s = None
                    for other in levels:
                        if other["level"] < price and other["type"] in (
                            "support", "both",
                        ):
                            next_s = other["level"]
                            break
                    tp = next_s if next_s else price - 2.5 * current_atr
                    sl = level_price + 0.005 * level_price  # 0.5% beyond level
                else:
                    continue

                # Risk/reward
                reward = abs(tp - price)
                risk = abs(price - sl)
                if risk == 0:
                    continue
                rr = reward / risk

                conf = min(0.80, 0.50 + touches * 0.05)

                signals.append({
                    "strategy": "fractal_sr_bounce",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": signal_type,
                    "entry_price": _smart_round(price),
                    "take_profit": _smart_round(tp),
                    "stop_loss": _smart_round(sl),
                    "confidence": round(min(0.85, conf), 2),
                    "risk_reward": round(rr, 2),
                    "reason": (
                        f"Price ${price:.2f} at {lvl_type} ${level_price:.2f} "
                        f"({touches} touches over {bar_span} bars, "
                        f"strength={strength:.2f})"
                    ),
                    "timeframe": "1d",
                    "timestamp": _now_iso(),
                })
                break  # One signal per symbol

        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY 75: Double Top / Bottom Detector
# =====================================================================
# Algorithmic double top/bottom detection with measured move targets.
# Reference: Bulkowski (2005) -- 78% success rate for double bottoms
# =====================================================================

def double_top_bottom_detector(
    data: dict[str, pd.DataFrame],
    context: Optional[dict] = None,
) -> list[dict]:
    """
    Algorithmic double top/bottom detection.

    Finds pairs of swing highs/lows within 2% tolerance separated by at
    least 10 bars.  Confirms on neckline break.  Target = measured move.

    Reference: Bulkowski (2005), *Encyclopedia of Chart Patterns*. 78%
    success rate for double bottoms.
    """
    signals: list[dict] = []

    for symbol in CRYPTO_SYMBOLS:
        try:
            if symbol not in data:
                continue
            df = data[symbol]
            if len(df) < 50:
                continue

            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            price = float(close.iloc[-1])

            close_arr = close.values.astype(float)
            high_arr = high.values.astype(float)
            low_arr = low.values.astype(float)

            pivots = _find_fractal_pivots(high, low, window=5)
            if len(pivots) < 4:
                continue

            swing_lows = [(idx, p) for idx, p, t in pivots if t == "low"]
            swing_highs = [(idx, p) for idx, p, t in pivots if t == "high"]

            best_signal = None

            # --- Double Bottom Detection ---
            for i in range(len(swing_lows)):
                for j in range(i + 1, len(swing_lows)):
                    idx1, p1 = swing_lows[i]
                    idx2, p2 = swing_lows[j]

                    # Minimum 10 bars apart
                    if abs(idx2 - idx1) < 10:
                        continue

                    # Within 2% tolerance
                    if abs(p1 - p2) / max(p1, 1e-10) > 0.02:
                        continue

                    # The second trough must be recent (within last 30 bars)
                    if idx2 < len(close_arr) - 30:
                        continue

                    # Find neckline: highest high between the two troughs
                    between_start = min(idx1, idx2) + 1
                    between_end = max(idx1, idx2)
                    if between_start >= between_end or between_end > len(high_arr):
                        continue

                    neckline = float(np.nanmax(high_arr[between_start:between_end]))
                    pattern_height = neckline - min(p1, p2)
                    pattern_height_pct = pattern_height / max(neckline, 1e-10)

                    # Confirm: price must have broken above neckline
                    if price <= neckline:
                        continue

                    target = neckline + pattern_height
                    sl = min(p1, p2) * 0.995  # Just below the lower trough

                    reward = abs(target - price)
                    risk = abs(price - sl)
                    if risk == 0:
                        continue
                    rr = reward / risk

                    conf = min(0.80, 0.55 + pattern_height_pct * 5.0)
                    if best_signal is None or conf > best_signal["confidence"]:
                        best_signal = {
                            "strategy": "double_top_bottom_detector",
                            "symbol": symbol,
                            "category": _get_category(symbol),
                            "signal_type": "BUY",
                            "entry_price": _smart_round(price),
                            "take_profit": _smart_round(target),
                            "stop_loss": _smart_round(sl),
                            "confidence": round(min(0.85, conf), 2),
                            "risk_reward": round(rr, 2),
                            "reason": (
                                f"Double bottom confirmed: troughs at "
                                f"${p1:.2f}/${p2:.2f}, neckline=${neckline:.2f}, "
                                f"target=${target:.2f}"
                            ),
                            "timeframe": "1d",
                            "timestamp": _now_iso(),
                        }

            # --- Double Top Detection ---
            for i in range(len(swing_highs)):
                for j in range(i + 1, len(swing_highs)):
                    idx1, p1 = swing_highs[i]
                    idx2, p2 = swing_highs[j]

                    if abs(idx2 - idx1) < 10:
                        continue
                    if abs(p1 - p2) / max(p1, 1e-10) > 0.02:
                        continue
                    if idx2 < len(close_arr) - 30:
                        continue

                    between_start = min(idx1, idx2) + 1
                    between_end = max(idx1, idx2)
                    if between_start >= between_end or between_end > len(low_arr):
                        continue

                    neckline = float(np.nanmin(low_arr[between_start:between_end]))
                    pattern_height = max(p1, p2) - neckline
                    pattern_height_pct = pattern_height / max(max(p1, p2), 1e-10)

                    # Confirm: price broke below neckline
                    if price >= neckline:
                        continue

                    target = neckline - pattern_height
                    sl = max(p1, p2) * 1.005  # Just above the higher peak

                    reward = abs(price - target)
                    risk = abs(sl - price)
                    if risk == 0:
                        continue
                    rr = reward / risk

                    conf = min(0.80, 0.55 + pattern_height_pct * 5.0)
                    candidate = {
                        "strategy": "double_top_bottom_detector",
                        "symbol": symbol,
                        "category": _get_category(symbol),
                        "signal_type": "SELL",
                        "entry_price": _smart_round(price),
                        "take_profit": _smart_round(target),
                        "stop_loss": _smart_round(sl),
                        "confidence": round(min(0.85, conf), 2),
                        "risk_reward": round(rr, 2),
                        "reason": (
                            f"Double top confirmed: peaks at "
                            f"${p1:.2f}/${p2:.2f}, neckline=${neckline:.2f}, "
                            f"target=${target:.2f}"
                        ),
                        "timeframe": "1d",
                        "timestamp": _now_iso(),
                    }
                    if best_signal is None or conf > best_signal["confidence"]:
                        best_signal = candidate

            if best_signal is not None:
                signals.append(best_signal)

        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY 76: Head & Shoulders Detector
# =====================================================================
# H&S and inverse H&S pattern recognition using fractal pivots.
# Reference: Bulkowski (2005) -- 83% success rate for H&S tops
# =====================================================================

def head_shoulders_detector(
    data: dict[str, pd.DataFrame],
    context: Optional[dict] = None,
) -> list[dict]:
    """
    Head & Shoulders and Inverse H&S pattern detection.

    Tests all triplets of consecutive swing highs/lows for the classic
    pattern geometry: head is highest/lowest, shoulders within 1.5%.
    Confirms on neckline break.  Target = measured move.

    Reference: Bulkowski (2005), *Encyclopedia of Chart Patterns*. 83%
    success rate for H&S tops.
    """
    signals: list[dict] = []

    for symbol in CRYPTO_SYMBOLS:
        try:
            if symbol not in data:
                continue
            df = data[symbol]
            if len(df) < 60:
                continue

            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            price = float(close.iloc[-1])
            high_arr = high.values.astype(float)
            low_arr = low.values.astype(float)

            pivots = _find_fractal_pivots(high, low, window=5)

            swing_highs = [(idx, p) for idx, p, t in pivots if t == "high"]
            swing_lows = [(idx, p) for idx, p, t in pivots if t == "low"]

            best_signal = None

            # --- H&S Top (bearish) ---
            if len(swing_highs) >= 3:
                for i in range(len(swing_highs) - 2):
                    ls_idx, ls_price = swing_highs[i]
                    h_idx, h_price = swing_highs[i + 1]
                    rs_idx, rs_price = swing_highs[i + 2]

                    # The right shoulder must be recent
                    if rs_idx < len(close) - 25:
                        continue

                    # Head must be the highest
                    if h_price <= ls_price or h_price <= rs_price:
                        continue

                    # Shoulders within 1.5% of each other
                    shoulder_diff = abs(ls_price - rs_price) / max(ls_price, 1e-10)
                    if shoulder_diff > 0.015:
                        continue

                    # Find troughs between LS-Head and Head-RS for neckline
                    troughs_left = [
                        p for idx, p in swing_lows
                        if ls_idx < idx < h_idx
                    ]
                    troughs_right = [
                        p for idx, p in swing_lows
                        if h_idx < idx < rs_idx
                    ]

                    if not troughs_left or not troughs_right:
                        continue

                    neckline = (min(troughs_left) + min(troughs_right)) / 2.0

                    # Confirm: price broke below neckline
                    if price >= neckline:
                        continue

                    pattern_height = h_price - neckline
                    pattern_height_pct = pattern_height / max(h_price, 1e-10)
                    target = neckline - pattern_height
                    sl = h_price * 1.005  # Above head

                    reward = abs(price - target)
                    risk = abs(sl - price)
                    if risk == 0:
                        continue
                    rr = reward / risk

                    conf = min(0.80, 0.60 + pattern_height_pct * 3.0)
                    candidate = {
                        "strategy": "head_shoulders_detector",
                        "symbol": symbol,
                        "category": _get_category(symbol),
                        "signal_type": "SELL",
                        "entry_price": _smart_round(price),
                        "take_profit": _smart_round(target),
                        "stop_loss": _smart_round(sl),
                        "confidence": round(min(0.85, conf), 2),
                        "risk_reward": round(rr, 2),
                        "reason": (
                            f"H&S top: LS=${ls_price:.2f}, "
                            f"Head=${h_price:.2f}, RS=${rs_price:.2f}, "
                            f"neckline=${neckline:.2f}, target=${target:.2f}"
                        ),
                        "timeframe": "1d",
                        "timestamp": _now_iso(),
                    }
                    if best_signal is None or conf > best_signal["confidence"]:
                        best_signal = candidate

            # --- Inverse H&S (bullish) ---
            if len(swing_lows) >= 3:
                for i in range(len(swing_lows) - 2):
                    ls_idx, ls_price = swing_lows[i]
                    h_idx, h_price = swing_lows[i + 1]
                    rs_idx, rs_price = swing_lows[i + 2]

                    if rs_idx < len(close) - 25:
                        continue

                    # Head must be the lowest
                    if h_price >= ls_price or h_price >= rs_price:
                        continue

                    # Shoulders within 1.5%
                    shoulder_diff = abs(ls_price - rs_price) / max(ls_price, 1e-10)
                    if shoulder_diff > 0.015:
                        continue

                    # Peaks between pivots form neckline
                    peaks_left = [
                        p for idx, p in swing_highs
                        if ls_idx < idx < h_idx
                    ]
                    peaks_right = [
                        p for idx, p in swing_highs
                        if h_idx < idx < rs_idx
                    ]

                    if not peaks_left or not peaks_right:
                        continue

                    neckline = (max(peaks_left) + max(peaks_right)) / 2.0

                    # Confirm: price broke above neckline
                    if price <= neckline:
                        continue

                    pattern_height = neckline - h_price
                    pattern_height_pct = pattern_height / max(neckline, 1e-10)
                    target = neckline + pattern_height
                    sl = h_price * 0.995  # Below head

                    reward = abs(target - price)
                    risk = abs(price - sl)
                    if risk == 0:
                        continue
                    rr = reward / risk

                    conf = min(0.80, 0.60 + pattern_height_pct * 3.0)
                    candidate = {
                        "strategy": "head_shoulders_detector",
                        "symbol": symbol,
                        "category": _get_category(symbol),
                        "signal_type": "BUY",
                        "entry_price": _smart_round(price),
                        "take_profit": _smart_round(target),
                        "stop_loss": _smart_round(sl),
                        "confidence": round(min(0.85, conf), 2),
                        "risk_reward": round(rr, 2),
                        "reason": (
                            f"Inverse H&S: LS=${ls_price:.2f}, "
                            f"Head=${h_price:.2f}, RS=${rs_price:.2f}, "
                            f"neckline=${neckline:.2f}, target=${target:.2f}"
                        ),
                        "timeframe": "1d",
                        "timestamp": _now_iso(),
                    }
                    if best_signal is None or conf > best_signal["confidence"]:
                        best_signal = candidate

            if best_signal is not None:
                signals.append(best_signal)

        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY 77: Ascending / Descending Triangle Breakout
# =====================================================================
# Flat resistance + rising lows (ascending) or flat support + falling
# highs (descending).  Linear regression on swing points.
# Reference: Bulkowski (2005) -- 64% breakout upward for ascending
# =====================================================================

def ascending_triangle_breakout(
    data: dict[str, pd.DataFrame],
    context: Optional[dict] = None,
) -> list[dict]:
    """
    Ascending triangle: flat resistance + rising lows → 64% breakout up.
    Descending triangle: flat support + falling highs → breakout down.

    Fits linear regression to last 5 swing highs and 5 swing lows, then
    checks slope conditions for triangle geometry.

    Reference: Bulkowski (2005), *Encyclopedia of Chart Patterns*. 64%
    upward breakout for ascending triangles.
    """
    signals: list[dict] = []

    for symbol in CRYPTO_SYMBOLS:
        try:
            if symbol not in data:
                continue
            df = data[symbol]
            if len(df) < 60:
                continue

            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            price = float(close.iloc[-1])

            pivots = _find_fractal_pivots(high, low, window=5)

            swing_highs = [(idx, p) for idx, p, t in pivots if t == "high"]
            swing_lows = [(idx, p) for idx, p, t in pivots if t == "low"]

            # Need at least 5 of each
            if len(swing_highs) < 5 or len(swing_lows) < 5:
                continue

            # Take last 5
            last_highs = swing_highs[-5:]
            last_lows = swing_lows[-5:]

            # Linear regression on swing highs
            h_x = np.array([idx for idx, _ in last_highs], dtype=float)
            h_y = np.array([p for _, p in last_highs], dtype=float)
            if len(set(h_x)) < 2:
                continue
            slope_h, intercept_h = np.polyfit(h_x, h_y, 1)

            # Linear regression on swing lows
            l_x = np.array([idx for idx, _ in last_lows], dtype=float)
            l_y = np.array([p for _, p in last_lows], dtype=float)
            if len(set(l_x)) < 2:
                continue
            slope_l, intercept_l = np.polyfit(l_x, l_y, 1)

            avg_price = float(np.mean(close.iloc[-60:]))
            if avg_price == 0:
                continue

            slope_h_norm = slope_h / avg_price
            slope_l_norm = slope_l / avg_price

            # ATR for fallback TP/SL
            atr_val = atr(high, low, close, 14)
            current_atr = float(atr_val.iloc[-1])
            if current_atr == 0 or np.isnan(current_atr):
                continue

            signal_type = None
            reason_prefix = ""

            # Ascending: flat highs, rising lows
            if abs(slope_h_norm) < 0.0001 and slope_l_norm > 0.0003:
                resistance = float(np.mean(h_y))
                # Price must be breaking above resistance
                if price > resistance * 0.998:
                    pattern_height = resistance - float(np.min(l_y))
                    tp = resistance + pattern_height
                    sl = float(l_y[-1])  # Last swing low
                    signal_type = "BUY"
                    reason_prefix = (
                        f"Ascending triangle: resistance at ${resistance:.2f}, "
                        f"lows converging, breakout expected up"
                    )

            # Descending: flat lows, falling highs
            elif abs(slope_l_norm) < 0.0001 and slope_h_norm < -0.0003:
                support = float(np.mean(l_y))
                # Price must be breaking below support
                if price < support * 1.002:
                    pattern_height = float(np.max(h_y)) - support
                    tp = support - pattern_height
                    sl = float(h_y[-1])  # Last swing high
                    signal_type = "SELL"
                    reason_prefix = (
                        f"Descending triangle: support at ${support:.2f}, "
                        f"highs converging, breakdown expected down"
                    )

            if signal_type is None:
                continue

            reward = abs(tp - price)
            risk = abs(price - sl)
            if risk == 0:
                continue
            rr = reward / risk

            signals.append({
                "strategy": "ascending_triangle_breakout",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": signal_type,
                "entry_price": _smart_round(price),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": 0.60,  # Bulkowski's 64% rate
                "risk_reward": round(rr, 2),
                "reason": reason_prefix,
                "timeframe": "1d",
                "timestamp": _now_iso(),
            })

        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY 78: S/R Breakout Retest
# =====================================================================
# After a level breaks, wait for price to retest from the other side.
# Old resistance → new support (and vice versa).
# Higher probability entry than chasing breakouts.
# =====================================================================

def sr_breakout_retest(
    data: dict[str, pd.DataFrame],
    context: Optional[dict] = None,
) -> list[dict]:
    """
    S/R flip retest: after a level breaks, trade the retest.

    Old resistance becomes new support (BUY on retest from above).
    Old support becomes new resistance (SELL on retest from below).

    Reference: Bulkowski (2005); Murphy (1999), *Technical Analysis of
    the Financial Markets*.
    """
    signals: list[dict] = []

    for symbol in CRYPTO_SYMBOLS:
        try:
            if symbol not in data:
                continue
            df = data[symbol]
            if len(df) < 60:
                continue

            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            price = float(close.iloc[-1])
            close_arr = close.values.astype(float)

            atr_val = atr(high, low, close, 14)
            current_atr = float(atr_val.iloc[-1])
            if current_atr == 0 or np.isnan(current_atr):
                continue

            pivots = _find_fractal_pivots(high, low, window=5)
            if len(pivots) < 6:
                continue

            levels = _cluster_pivots_to_levels(
                pivots, tolerance_pct=0.005, min_touches=3, total_bars=len(df),
            )
            if not levels:
                continue

            n = len(close_arr)
            best_signal = None

            for lvl in levels:
                level_price = lvl["level"]
                touches = lvl["touches"]

                # Check if price broke through this level in last 10 bars
                broke_above = False
                broke_below = False
                for bar_idx in range(max(0, n - 10), n - 1):
                    prev = close_arr[bar_idx - 1] if bar_idx > 0 else close_arr[bar_idx]
                    curr = close_arr[bar_idx]

                    # Broke above: was below, now above
                    if prev < level_price and curr > level_price:
                        broke_above = True
                    # Broke below: was above, now below
                    if prev > level_price and curr < level_price:
                        broke_below = True

                # Now check if price is retesting (within 0.5% of level)
                retest_distance_pct = abs(price - level_price) / max(level_price, 1e-10)
                if retest_distance_pct > 0.005:
                    continue

                signal_type = None
                reason_suffix = ""

                if broke_above and price >= level_price * 0.995:
                    # Resistance broke → now testing as support from above
                    signal_type = "BUY"
                    reason_suffix = "resistance\u2192support"
                elif broke_below and price <= level_price * 1.005:
                    # Support broke → now testing as resistance from below
                    signal_type = "SELL"
                    reason_suffix = "support\u2192resistance"
                else:
                    continue

                if signal_type == "BUY":
                    tp = price + 3.0 * current_atr
                    sl = level_price - 1.0 * current_atr
                else:
                    tp = price - 3.0 * current_atr
                    sl = level_price + 1.0 * current_atr

                reward = abs(tp - price)
                risk = abs(price - sl)
                if risk == 0:
                    continue
                rr = reward / risk

                conf = min(0.75, 0.55 + touches * 0.04)
                if best_signal is None or conf > best_signal["confidence"]:
                    best_signal = {
                        "strategy": "sr_breakout_retest",
                        "symbol": symbol,
                        "category": _get_category(symbol),
                        "signal_type": signal_type,
                        "entry_price": _smart_round(price),
                        "take_profit": _smart_round(tp),
                        "stop_loss": _smart_round(sl),
                        "confidence": round(min(0.85, conf), 2),
                        "risk_reward": round(rr, 2),
                        "reason": (
                            f"S/R flip retest: ${level_price:.2f} "
                            f"({touches}-touch {reason_suffix}), retesting now"
                        ),
                        "timeframe": "1d",
                        "timestamp": _now_iso(),
                    }

            if best_signal is not None:
                signals.append(best_signal)

        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY 79: Price Level Magnetism
# =====================================================================
# Prices cluster at round numbers, VWAP, and previous key levels.
# Trade attraction toward strongest magnet with RSI confluence.
# Reference: Lo, Mamaysky & Wang (2000), "Foundations of Technical
# Analysis," Journal of Finance 55(4).
# =====================================================================

def price_level_magnetism(
    data: dict[str, pd.DataFrame],
    context: Optional[dict] = None,
) -> list[dict]:
    """
    Price memory / magnetism: round numbers, VWAP, previous day close/high/low
    act as attractors.  Score each magnet and require RSI confluence.

    Reference: Lo, Mamaysky & Wang (2000), Journal of Finance 55(4), 1705-1765.
    """
    signals: list[dict] = []

    for symbol in ALL_SYMBOLS:
        try:
            if symbol not in data:
                continue
            df = data[symbol]
            if len(df) < 30:
                continue

            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]
            price = float(close.iloc[-1])

            if price <= 0 or np.isnan(price):
                continue

            atr_val = atr(high, low, close, 14)
            current_atr = float(atr_val.iloc[-1])
            if current_atr == 0 or np.isnan(current_atr):
                continue

            rsi_val = float(rsi(close, 14).iloc[-1])
            if np.isnan(rsi_val):
                continue

            # Build list of magnet levels with type and base strength
            magnets: list[tuple[float, str, float]] = []

            # Previous day close, high, low
            if len(close) >= 2:
                magnets.append((float(close.iloc[-2]), "prev_close", 1.0))
            if len(high) >= 2:
                magnets.append((float(high.iloc[-2]), "prev_high", 0.8))
            if len(low) >= 2:
                magnets.append((float(low.iloc[-2]), "prev_low", 0.8))

            # VWAP
            try:
                vwap_vals = vwap_session(high, low, close, volume)
                vwap_current = float(vwap_vals.iloc[-1])
                if not np.isnan(vwap_current) and vwap_current > 0:
                    magnets.append((vwap_current, "VWAP", 1.2))
            except Exception:
                pass

            # Round numbers
            cat = _get_category(symbol)
            if cat in ("forex",):
                # Forex: round to nearest 0.01 and 0.005
                for r_func, r_name, r_str in [
                    (0.01, "round_001", 0.7),
                    (0.005, "round_0005", 0.5),
                ]:
                    nearest = round(price / r_func) * r_func
                    magnets.append((nearest, r_name, r_str))
                    if nearest != price:
                        # Also add adjacent round levels
                        magnets.append((nearest + r_func, r_name, r_str * 0.6))
                        magnets.append((nearest - r_func, r_name, r_str * 0.6))
            else:
                # Crypto/stocks: round to nearest 100, 50, 10
                for divisor, r_name, r_str in [
                    (100, "round_100", 0.9),
                    (50, "round_50", 0.7),
                    (10, "round_10", 0.5),
                ]:
                    if price < divisor * 2:
                        continue  # Skip if price is too small for this level
                    nearest = round(price / divisor) * divisor
                    magnets.append((nearest, r_name, r_str))

            if not magnets:
                continue

            # Score each magnet by: strength * inverse_distance
            scored: list[tuple[float, str, float, float]] = []
            for m_price, m_type, m_base_str in magnets:
                if m_price <= 0:
                    continue
                dist_pct = abs(m_price - price) / price
                if dist_pct < 0.0001:
                    continue  # Already at the level
                if dist_pct > 0.05:
                    continue  # Too far away (>5%)
                score = m_base_str * (1.0 / (1.0 + dist_pct * 100.0))
                scored.append((m_price, m_type, score, dist_pct))

            if not scored:
                continue

            # Find strongest magnet
            scored.sort(key=lambda x: x[2], reverse=True)
            magnet_price, magnet_type, magnet_strength, dist_pct = scored[0]

            # RSI confluence check
            signal_type = None
            if magnet_price > price:
                # Magnet is above → expect pull up
                if rsi_val < 45:  # Not overbought -- good for upside
                    signal_type = "BUY"
            elif magnet_price < price:
                # Magnet is below → expect pull down
                if rsi_val > 55:  # Not oversold -- good for downside
                    signal_type = "SELL"

            if signal_type is None:
                continue

            tp = magnet_price
            sl_dist = 1.5 * current_atr
            if signal_type == "BUY":
                sl = price - sl_dist
            else:
                sl = price + sl_dist

            reward = abs(tp - price)
            risk = abs(price - sl)
            if risk == 0:
                continue
            rr = reward / risk

            conf = min(0.70, 0.50 + magnet_strength * 0.30)

            signals.append({
                "strategy": "price_level_magnetism",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": signal_type,
                "entry_price": _smart_round(price),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": round(min(0.85, conf), 2),
                "risk_reward": round(rr, 2),
                "reason": (
                    f"Price magnet: ${magnet_price:.2f} ({magnet_type}) pulling "
                    f"from ${price:.2f} ({dist_pct * 100:.1f}% away), "
                    f"RSI={rsi_val:.0f}"
                ),
                "timeframe": "1d",
                "timestamp": _now_iso(),
            })

        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY 80: Pattern Repetition Forecast
# =====================================================================
# Template matching: Z-score normalize last 10 bars, find similar
# historical windows, forecast from their forward returns.
# Reference: Caginalp & Laurent (1998), Applied Mathematical Finance.
# =====================================================================

def pattern_repetition_forecast(
    data: dict[str, pd.DataFrame],
    context: Optional[dict] = None,
) -> list[dict]:
    """
    Template matching: Z-score normalize last 10 bars, search all
    historical 10-bar windows for similar patterns (Euclidean distance),
    forecast using the distribution of forward 5-bar returns.

    Reference: Caginalp & Laurent (1998), "The Predictive Power of Price
    Patterns," Applied Mathematical Finance 5(3-4), 181-205.
    """
    signals: list[dict] = []
    template_len = 10
    forward_len = 5
    distance_threshold = 0.5
    min_matches = 20

    for symbol in CRYPTO_SYMBOLS:
        try:
            if symbol not in data:
                continue
            df = data[symbol]
            # Need enough history: template + forward + buffer
            if len(df) < template_len + forward_len + 60:
                continue

            close = df["Close"].values.astype(float)
            price = float(close[-1])
            n = len(close)

            # Template: last template_len bars, Z-score normalized
            template = close[-template_len:]
            t_mean = np.mean(template)
            t_std = np.std(template)
            if t_std < 1e-10:
                continue
            template_norm = (template - t_mean) / t_std

            # Build matrix of all historical windows (vectorized)
            # Each row is a template_len window of close prices
            # Stop before the last template_len bars (that's our query)
            end_idx = n - template_len - forward_len
            if end_idx < template_len:
                continue

            # Create sliding windows using stride tricks
            stride = close.strides[0]
            shape = (end_idx - template_len + 1, template_len)
            if shape[0] < min_matches:
                continue

            windows = np.lib.stride_tricks.as_strided(
                close[template_len:],
                shape=(end_idx - template_len + 1, template_len),
                strides=(stride, stride),
            ).copy()

            # Forward returns for each window
            forward_starts = np.arange(template_len, template_len + shape[0])
            forward_ends = forward_starts + template_len + forward_len - 1
            # Ensure forward_ends don't exceed data
            valid_mask = forward_ends < n - template_len
            if valid_mask.sum() < min_matches:
                continue

            windows = windows[valid_mask]
            forward_starts_valid = forward_starts[valid_mask]

            # Z-score normalize each window
            w_means = windows.mean(axis=1, keepdims=True)
            w_stds = windows.std(axis=1, keepdims=True)
            w_stds[w_stds < 1e-10] = 1.0
            windows_norm = (windows - w_means) / w_stds

            # Euclidean distance from template to each window
            diffs = windows_norm - template_norm
            distances = np.sqrt((diffs ** 2).sum(axis=1))

            # Find matches below threshold
            match_mask = distances < distance_threshold
            n_matches = int(match_mask.sum())

            if n_matches < min_matches:
                continue

            # Compute forward returns for matches
            match_indices = np.where(match_mask)[0]
            forward_returns = []
            for m_idx in match_indices:
                # Index into original close array
                window_end = int(forward_starts_valid[m_idx]) + template_len - 1
                fwd_end = window_end + forward_len
                if fwd_end >= n - template_len:
                    continue
                start_price = close[window_end]
                end_price = close[fwd_end]
                if start_price > 0:
                    fwd_ret = (end_price - start_price) / start_price
                    forward_returns.append(fwd_ret)

            if len(forward_returns) < min_matches:
                continue

            fwd_arr = np.array(forward_returns)
            mean_ret = float(np.mean(fwd_arr))
            std_ret = float(np.std(fwd_arr))
            if std_ret < 1e-10:
                continue

            # t-test: is the mean return significantly different from zero?
            t_stat = mean_ret / (std_ret / np.sqrt(len(fwd_arr)))
            # Normal approx for t-dist (valid when df > ~20, which our min_matches guarantees)
            import math
            p_value = float(math.erfc(abs(t_stat) / math.sqrt(2)))

            if p_value >= 0.10:
                continue

            win_rate = float(np.mean(fwd_arr > 0) * 100.0)
            pct_10 = float(np.percentile(fwd_arr, 10))

            signal_type = None
            if mean_ret > 0.005:
                signal_type = "BUY"
                tp = price * (1.0 + mean_ret)
                sl = price * (1.0 + pct_10)
            elif mean_ret < -0.005:
                signal_type = "SELL"
                tp = price * (1.0 + mean_ret)  # mean_ret is negative
                sl = price * (1.0 - pct_10)    # pct_10 is negative, so this goes up
            else:
                continue

            reward = abs(tp - price)
            risk = abs(price - sl)
            if risk == 0:
                continue
            rr = reward / risk

            conf = min(0.75, 0.50 + abs(t_stat) * 0.05)

            signals.append({
                "strategy": "pattern_repetition_forecast",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": signal_type,
                "entry_price": _smart_round(price),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": round(min(0.85, conf), 2),
                "risk_reward": round(rr, 2),
                "reason": (
                    f"Pattern match: {n_matches} similar patterns found "
                    f"(distance<{distance_threshold}), mean forward "
                    f"return={mean_ret * 100:.2f}%, WR={win_rate:.0f}%, "
                    f"t-stat={t_stat:.2f}"
                ),
                "timeframe": "1d",
                "timestamp": _now_iso(),
            })

        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY 81: Volume Profile Value Area
# =====================================================================
# Build volume profile, identify POC and Value Area (70% volume).
# Buy below VAL, sell above VAH -- mean-revert to fair value.
# Reference: Steidlmayer (1986), Market Profile. CBOT.
# =====================================================================

def volume_profile_value_area(
    data: dict[str, pd.DataFrame],
    context: Optional[dict] = None,
) -> list[dict]:
    """
    Volume profile: buy below Value Area Low, sell above Value Area High.
    Target is POC (Point of Control).

    Reference: Steidlmayer (1986), *Market Profile*. CBOT.
    """
    signals: list[dict] = []

    for symbol in CRYPTO_SYMBOLS:
        try:
            if symbol not in data:
                continue
            df = data[symbol]
            if len(df) < 35:
                continue

            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]
            price = float(close.iloc[-1])

            atr_val = atr(high, low, close, 14)
            current_atr = float(atr_val.iloc[-1])
            if current_atr == 0 or np.isnan(current_atr):
                continue

            vp = _build_volume_profile(close, high, low, volume,
                                       n_bins=50, lookback=30)
            if not vp:
                continue

            poc = vp["poc"]
            val = vp["val"]
            vah = vp["vah"]
            poc_vol = vp["poc_vol"]
            avg_vol = vp["avg_vol"]

            if avg_vol <= 0:
                continue

            signal_type = None

            if price < val:
                # Below Value Area → expect reversion up to POC
                signal_type = "BUY"
                tp = poc
                sl = price - 2.0 * current_atr
                # Guard: TP must be above entry for LONG
                if tp <= price:
                    tp = price + 1.5 * current_atr
            elif price > vah:
                # Above Value Area → expect reversion down to POC
                signal_type = "SELL"
                tp = poc
                sl = price + 2.0 * current_atr
                # Guard: TP must be below entry for SHORT, and positive
                if tp >= price or tp <= 0:
                    tp = price - 1.5 * current_atr
                if tp <= 0:
                    continue  # Skip -- price too low for meaningful SHORT TP
            else:
                continue

            reward = abs(tp - price)
            risk = abs(price - sl)
            if risk == 0:
                continue
            rr = reward / risk

            vol_ratio_score = poc_vol / avg_vol
            conf = min(0.75, 0.55 + vol_ratio_score * 0.05)

            side_label = "below VAL" if signal_type == "BUY" else "above VAH"

            signals.append({
                "strategy": "volume_profile_value_area",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": signal_type,
                "entry_price": _smart_round(price),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": round(min(0.85, conf), 2),
                "risk_reward": round(rr, 2),
                "reason": (
                    f"Price ${price:.2f} is {side_label} "
                    f"(VA: ${val:.2f}-${vah:.2f}, POC=${poc:.2f}), "
                    f"vol-confirmed fair value reversion"
                ),
                "timeframe": "1d",
                "timestamp": _now_iso(),
            })

        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY 82: Multi-Touch Level Strength
# =====================================================================
# The more times a level is touched, the more predictable the outcome.
# 3-4 touches → expect bounce (62%).  5+ → weakening, expect breakout.
# Reference: Bulkowski (2005), support/resistance touch statistics.
# =====================================================================

def multi_touch_level_strength(
    data: dict[str, pd.DataFrame],
    context: Optional[dict] = None,
) -> list[dict]:
    """
    Touch-count-based S/R strength prediction.

    3-4 touches: expect bounce (62% historical).
    5+ touches: level weakening, expect breakout (55% bounce → 52% at 7+).

    Reference: Bulkowski (2005), *Encyclopedia of Chart Patterns*.
    """
    signals: list[dict] = []

    # Bounce probability by touch count (Bulkowski approximation)
    bounce_prob = {
        3: 0.62,
        4: 0.60,
        5: 0.55,
        6: 0.53,
    }
    # 7+ touches → 52% bounce → breakout becomes more likely

    for symbol in CRYPTO_SYMBOLS:
        try:
            if symbol not in data:
                continue
            df = data[symbol]
            if len(df) < 60:
                continue

            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]
            price = float(close.iloc[-1])

            atr_val = atr(high, low, close, 14)
            current_atr = float(atr_val.iloc[-1])
            if current_atr == 0 or np.isnan(current_atr):
                continue

            vol_r = volume_ratio(volume, 20)
            current_vol_ratio = float(vol_r.iloc[-1])
            if np.isnan(current_vol_ratio):
                current_vol_ratio = 1.0

            pivots = _find_fractal_pivots(high, low, window=5)
            if len(pivots) < 6:
                continue

            levels = _cluster_pivots_to_levels(
                pivots, tolerance_pct=0.005, min_touches=3, total_bars=len(df),
            )
            if not levels:
                continue

            best_signal = None

            for lvl in levels:
                level_price = lvl["level"]
                touches = lvl["touches"]
                lvl_type = lvl["type"]
                recency_w = lvl["recency_weight"]

                # Is price near this level? (within 0.5 ATR)
                distance = abs(price - level_price)
                if distance > 0.5 * current_atr:
                    continue

                bp = bounce_prob.get(min(touches, 6), 0.52)

                if touches <= 4:
                    # Expect bounce
                    if price <= level_price and lvl_type in ("support", "both"):
                        signal_type = "BUY"
                        tp = price + 2.5 * current_atr
                        sl = level_price - 0.5 * current_atr
                    elif price >= level_price and lvl_type in ("resistance", "both"):
                        signal_type = "SELL"
                        tp = price - 2.5 * current_atr
                        sl = level_price + 0.5 * current_atr
                    else:
                        continue
                    action = f"bounce expected ({bp * 100:.0f}% hist)"
                else:
                    # 5+ touches: expect breakout
                    if price >= level_price and lvl_type in ("resistance", "both"):
                        # Breaking above weakened resistance
                        signal_type = "BUY"
                        tp = price + 3.0 * current_atr
                        sl = level_price - 0.5 * current_atr
                    elif price <= level_price and lvl_type in ("support", "both"):
                        # Breaking below weakened support
                        signal_type = "SELL"
                        tp = price - 3.0 * current_atr
                        sl = level_price + 0.5 * current_atr
                    else:
                        continue
                    action = f"weakening ({bp * 100:.0f}% bounce rate)"

                reward = abs(tp - price)
                risk = abs(price - sl)
                if risk == 0:
                    continue
                rr = reward / risk

                # Confidence: higher for clear bounce cases, volume-confirmed
                conf = min(0.75, 0.50 + touches * 0.03 + current_vol_ratio * 0.02)

                if best_signal is None or conf > best_signal["confidence"]:
                    best_signal = {
                        "strategy": "multi_touch_level_strength",
                        "symbol": symbol,
                        "category": _get_category(symbol),
                        "signal_type": signal_type,
                        "entry_price": _smart_round(price),
                        "take_profit": _smart_round(tp),
                        "stop_loss": _smart_round(sl),
                        "confidence": round(min(0.85, conf), 2),
                        "risk_reward": round(rr, 2),
                        "reason": (
                            f"${level_price:.2f} level touched {touches} times: "
                            f"{action}, vol={current_vol_ratio:.1f}x avg"
                        ),
                        "timeframe": "1d",
                        "timestamp": _now_iso(),
                    }

            if best_signal is not None:
                signals.append(best_signal)

        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY 83: Failed Breakout Reversal
# =====================================================================
# Price breaks through S/R but immediately reverses back -- bull/bear trap.
# One of the highest-probability reversal signals.
# Reference: Bulkowski (2005) -- 72% success rate for failed breakouts.
# =====================================================================

def failed_breakout_reversal(
    data: dict[str, pd.DataFrame],
    context: Optional[dict] = None,
) -> list[dict]:
    """
    Failed breakout / bull & bear trap detection.

    After price breaks through a 3+ touch S/R level but immediately reverses
    back, trade the reversal.  This is one of the highest-probability setups.

    Reference: Bulkowski (2005), *Encyclopedia of Chart Patterns*. ~72%
    success rate for failed breakouts.
    """
    signals: list[dict] = []

    for symbol in CRYPTO_SYMBOLS:
        try:
            if symbol not in data:
                continue
            df = data[symbol]
            if len(df) < 60:
                continue

            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            price = float(close.iloc[-1])
            close_arr = close.values.astype(float)
            high_arr = high.values.astype(float)
            low_arr = low.values.astype(float)
            n = len(close_arr)

            atr_val = atr(high, low, close, 14)
            current_atr = float(atr_val.iloc[-1])
            if current_atr == 0 or np.isnan(current_atr):
                continue

            pivots = _find_fractal_pivots(high, low, window=5)
            if len(pivots) < 6:
                continue

            levels = _cluster_pivots_to_levels(
                pivots, tolerance_pct=0.005, min_touches=3, total_bars=len(df),
            )
            if not levels:
                continue

            best_signal = None

            for lvl in levels:
                level_price = lvl["level"]
                touches = lvl["touches"]
                lvl_type = lvl["type"]

                # Check last 3 bars for breakout + reversal
                recent_close = close_arr[-4:]  # bars [-3], [-2], [-1], [current]
                recent_high = high_arr[-4:]
                recent_low = low_arr[-4:]

                if len(recent_close) < 4:
                    continue

                broke_above = False
                broke_below = False
                breakout_extreme = None

                for bi in range(len(recent_close) - 1):
                    bar_close = recent_close[bi]
                    bar_high = recent_high[bi]
                    bar_low = recent_low[bi]

                    # Broke above resistance by > 0.3%
                    if (bar_close > level_price * 1.003
                            and lvl_type in ("resistance", "both")):
                        broke_above = True
                        breakout_extreme = bar_high if (
                            breakout_extreme is None
                            or bar_high > breakout_extreme
                        ) else breakout_extreme

                    # Broke below support by > 0.3%
                    if (bar_close < level_price * 0.997
                            and lvl_type in ("support", "both")):
                        broke_below = True
                        breakout_extreme = bar_low if (
                            breakout_extreme is None
                            or bar_low < breakout_extreme
                        ) else breakout_extreme

                signal_type = None

                if broke_above and price < level_price:
                    # Bull trap: broke above resistance, now back below
                    signal_type = "SELL"
                    tp = price - 3.0 * current_atr
                    sl = breakout_extreme * 1.002 if breakout_extreme else (
                        level_price + 1.0 * current_atr
                    )
                elif broke_below and price > level_price:
                    # Bear trap: broke below support, now back above
                    signal_type = "BUY"
                    tp = price + 3.0 * current_atr
                    sl = breakout_extreme * 0.998 if breakout_extreme else (
                        level_price - 1.0 * current_atr
                    )
                else:
                    continue

                reward = abs(tp - price)
                risk = abs(price - sl)
                if risk == 0:
                    continue
                rr = reward / risk

                # High base confidence for this pattern
                conf = min(0.80, 0.65 + touches * 0.03)

                trap_type = "bear" if signal_type == "BUY" else "bull"
                break_dir = "below" if signal_type == "BUY" else "above"

                if best_signal is None or conf > best_signal["confidence"]:
                    best_signal = {
                        "strategy": "failed_breakout_reversal",
                        "symbol": symbol,
                        "category": _get_category(symbol),
                        "signal_type": signal_type,
                        "entry_price": _smart_round(price),
                        "take_profit": _smart_round(tp),
                        "stop_loss": _smart_round(sl),
                        "confidence": round(min(0.85, conf), 2),
                        "risk_reward": round(rr, 2),
                        "reason": (
                            f"Failed {'breakdown' if signal_type == 'BUY' else 'breakout'} "
                            f"at ${level_price:.2f}: price broke {break_dir} then "
                            f"reversed \u2014 {trap_type} trap "
                            f"(72% hist success)"
                        ),
                        "timeframe": "1d",
                        "timestamp": _now_iso(),
                    }

            if best_signal is not None:
                signals.append(best_signal)

        except Exception:
            continue

    return signals


# =====================================================================
# Registration dict -- importable by production_scanner.py
# =====================================================================

PATTERN_STRATEGIES = {
    "fractal_sr_bounce": fractal_sr_bounce,
    # DISABLED: -$14,088 loss on 18 trades (5.6% WR). Removed 2026-02-24.
    # "double_top_bottom_detector": double_top_bottom_detector,
    "head_shoulders_detector": head_shoulders_detector,
    "ascending_triangle_breakout": ascending_triangle_breakout,
    "sr_breakout_retest": sr_breakout_retest,
    "price_level_magnetism": price_level_magnetism,
    "pattern_repetition_forecast": pattern_repetition_forecast,
    "volume_profile_value_area": volume_profile_value_area,
    "multi_touch_level_strength": multi_touch_level_strength,
    "failed_breakout_reversal": failed_breakout_reversal,
}
