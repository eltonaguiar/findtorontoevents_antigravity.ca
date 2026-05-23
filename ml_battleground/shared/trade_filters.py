"""
Research-backed pre-trade filters for ML Battleground.

References:
  - Adaptive threshold: Kissell (2020) "Science of Algorithmic Trading"
    → breakeven probability = (SL + cost) / (TP + SL) where cost is round-trip
  - ATR percentile filter: Wilder (1978) "New Concepts in Technical Trading"
    → avoid ultra-low (no edge) and ultra-high (stops blown) volatility
  - Volume confirmation: standard microstructure literature
    → thin volume = worse fills + more noise
  - Reversal confirmation: Elder (1993) "Trading for a Living"
    → wait for price action to confirm signal direction before entry
"""
import numpy as np
from typing import Optional


def adaptive_threshold(
    tp_distance: float,
    sl_distance: float,
    cost_pct: float,
    regime: str = "normal",
    recent_win_rate: Optional[float] = None,
) -> float:
    """
    Calculate minimum confidence threshold based on cost-aware breakeven.

    Instead of a fixed 0.55 or 0.65 threshold, compute the probability
    needed to break even given TP, SL, and costs. Then add a buffer.

    Args:
        tp_distance: distance to take profit (price units or %)
        sl_distance: distance to stop loss (price units or %)
        cost_pct: round-trip cost as decimal (e.g., 0.0025)
        regime: market regime string
        recent_win_rate: recent empirical win rate (if available)

    Returns:
        minimum confidence threshold (0.0 - 1.0)
    """
    if sl_distance <= 0 or tp_distance <= 0:
        return 0.85  # refuse trade with invalid TP/SL

    # Breakeven probability: P(win) = (SL + cost) / (TP + SL)
    # At this probability, expected value = 0
    breakeven = (sl_distance + cost_pct) / (tp_distance + sl_distance)

    # Add buffer above breakeven (need edge, not just breakeven)
    buffer = 0.05  # 5% above breakeven

    # Regime adjustments — reduced from v1.0 (was blocking all trades in bear markets)
    if regime in ("high_volatility", "volatile"):
        buffer += 0.05  # was 0.10 — too aggressive, blocked D+E entirely
    elif regime in ("trending_down",):
        buffer += 0.02  # was 0.05

    # If recent performance is bad, raise the bar (only with enough data)
    if recent_win_rate is not None and recent_win_rate < 0.3:
        buffer += 0.03  # was 0.05

    threshold = min(breakeven + buffer, 0.85)
    return round(max(threshold, 0.40), 3)  # floor lowered from 0.50 to 0.40


def atr_percentile_filter(
    atr_values: np.ndarray,
    low_pct: float = 40.0,
    high_pct: float = 95.0,
) -> bool:
    """
    Check if current ATR is in the "goldilocks zone" for trading.

    Too low: no movement to profit from, costs eat the edge.
    Too high: stops get blown by noise, adverse selection risk.

    Args:
        atr_values: array of recent ATR values (at least 50 bars)
        low_pct: lower percentile bound (default 40th)
        high_pct: upper percentile bound (default 95th)

    Returns:
        True if current ATR is in acceptable range
    """
    if len(atr_values) < 50:
        return True  # not enough data, allow

    current = float(atr_values[-1])
    low_bound = float(np.percentile(atr_values[:-1], low_pct))
    high_bound = float(np.percentile(atr_values[:-1], high_pct))

    return low_bound <= current <= high_bound


def volume_confirmation(
    volumes: np.ndarray,
    min_ratio: float = 0.7,
    lookback: int = 20,
) -> tuple[bool, float]:
    """
    Check if current volume confirms the trade.

    Thin volume = worse fills, more noise, higher effective costs.
    Require volume to be at least min_ratio × average.

    Args:
        volumes: array of volume values
        min_ratio: minimum volume/average ratio (default 0.7)
        lookback: number of bars for average (default 20)

    Returns:
        (passes, ratio) tuple
    """
    if len(volumes) < lookback + 1:
        return True, 1.0  # not enough data

    current = float(volumes[-1])
    avg = float(np.mean(volumes[-lookback - 1:-1]))

    if avg <= 0:
        return True, 1.0

    ratio = current / avg
    return ratio >= min_ratio, round(ratio, 2)


def reversal_confirmation(
    closes: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    signal_type: str = "BUY",
    lookback: int = 3,
) -> tuple[bool, str]:
    """
    Confirm that recent price action supports the signal direction.

    Problem solved: All 15 losing trades had Max Favorable Excursion near 0% —
    price never moved in the right direction after entry. This filter requires
    at least 1 of the last `lookback` candles to confirm direction.

    For BUY signals, confirmation means:
      - At least 1 green candle (close > open) in last `lookback` bars, AND
      - Last close > lowest close in the lookback window (not making new lows)

    For SELL signals, confirmation means:
      - At least 1 red candle (close < open) in last `lookback` bars, AND
      - Last close < highest close in the lookback window (not making new highs)

    Args:
        closes: array of close prices (at least lookback+1 bars)
        highs: array of high prices
        lows: array of low prices
        signal_type: "BUY" or "SELL"
        lookback: number of bars to check (default 3)

    Returns:
        (confirmed, reason) tuple
    """
    if len(closes) < lookback + 1:
        return True, "insufficient_data"

    recent_closes = closes[-lookback:]
    prev_closes = closes[-(lookback + 1):-1]  # opens approximated by prior close

    if signal_type == "BUY":
        # Check 1: at least 1 green candle (close > prior close)
        green_count = sum(1 for i in range(lookback) if recent_closes[i] > prev_closes[i])
        if green_count == 0:
            return False, "no_green_candles"

        # Check 2: not making new lows (last close above lowest recent close)
        if float(recent_closes[-1]) <= float(np.min(lows[-lookback:])):
            return False, "making_new_lows"

        # Check 3: last candle should be green or at least not a large red
        last_change = (float(recent_closes[-1]) - float(prev_closes[-1])) / float(prev_closes[-1])
        if last_change < -0.01:  # last candle dropped > 1%
            return False, "last_candle_bearish"

        return True, f"confirmed_{green_count}_green"

    else:  # SELL
        # Check 1: at least 1 red candle
        red_count = sum(1 for i in range(lookback) if recent_closes[i] < prev_closes[i])
        if red_count == 0:
            return False, "no_red_candles"

        # Check 2: not making new highs
        if float(recent_closes[-1]) >= float(np.max(highs[-lookback:])):
            return False, "making_new_highs"

        # Check 3: last candle should be red or at least not a large green
        last_change = (float(recent_closes[-1]) - float(prev_closes[-1])) / float(prev_closes[-1])
        if last_change > 0.01:  # last candle rose > 1%
            return False, "last_candle_bullish"

        return True, f"confirmed_{red_count}_red"
