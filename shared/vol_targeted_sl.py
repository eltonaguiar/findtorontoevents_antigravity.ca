"""
Volatility-Targeted Stop-Loss / Take-Profit Helper.

Replaces hardcoded ATR multipliers with a configurable, reusable helper.
All functions handle both LONG and SHORT directions and return descriptive dicts.

Usage:
    from shared.vol_targeted_sl import compute_atr, vol_targeted_levels

    atr = compute_atr(highs, lows, closes, period=14)
    levels = vol_targeted_levels(entry=100_000, direction="LONG", atr=2500)
    # => {'stop_loss': 96250.0, 'take_profit': 106250.0, ...}

Dependencies: numpy only.
"""

from typing import Dict, List, Union

import numpy as np

# ---------------------------------------------------------------------------
# Direction helpers
# ---------------------------------------------------------------------------
_LONG_DIRS = {"LONG", "long", "BUY", "buy", "L", "l"}
_SHORT_DIRS = {"SHORT", "short", "SELL", "sell", "S", "s"}


def _is_long(direction: str) -> bool:
    if direction in _LONG_DIRS:
        return True
    if direction in _SHORT_DIRS:
        return False
    raise ValueError(f"Unknown direction '{direction}'. Use LONG/SHORT (or BUY/SELL).")


# ---------------------------------------------------------------------------
# ATR calculation — Wilder smoothing (exponential with alpha = 1/period)
# ---------------------------------------------------------------------------

def compute_atr(
    highs: Union[List[float], np.ndarray],
    lows: Union[List[float], np.ndarray],
    closes: Union[List[float], np.ndarray],
    period: int = 14,
) -> float:
    """Return the latest ATR value using Wilder smoothing.

    Parameters
    ----------
    highs, lows, closes : array-like
        OHLC price arrays of equal length (oldest-first).
    period : int
        Smoothing period (default 14).

    Returns
    -------
    float
        Most recent ATR value.

    Raises
    ------
    ValueError
        If arrays are too short (need at least ``period + 1`` bars).
    """
    highs = np.asarray(highs, dtype=float)
    lows = np.asarray(lows, dtype=float)
    closes = np.asarray(closes, dtype=float)

    n = len(highs)
    if n < period + 1:
        raise ValueError(
            f"Need at least {period + 1} bars for ATR({period}), got {n}."
        )

    # True Range: max(H-L, |H-prevC|, |L-prevC|)
    prev_close = closes[:-1]
    h = highs[1:]
    lo = lows[1:]

    tr = np.maximum(h - lo, np.maximum(np.abs(h - prev_close), np.abs(lo - prev_close)))

    # Wilder smoothing: first ATR = SMA of first `period` TRs, then EMA
    atr = np.mean(tr[:period])
    alpha = 1.0 / period
    for i in range(period, len(tr)):
        atr = atr * (1 - alpha) + tr[i] * alpha

    return float(atr)


# ---------------------------------------------------------------------------
# Core SL / TP levels
# ---------------------------------------------------------------------------

def vol_targeted_levels(
    entry: float,
    direction: str,
    atr: float,
    sl_mult: float = 1.5,
    tp_mult: float = 2.5,
) -> Dict[str, float]:
    """Compute stop-loss and take-profit levels from ATR.

    Parameters
    ----------
    entry : float
        Entry price.
    direction : str
        "LONG" or "SHORT" (also accepts BUY/SELL).
    atr : float
        Current ATR value.
    sl_mult : float
        ATR multiplier for stop-loss distance (default 1.5).
    tp_mult : float
        ATR multiplier for take-profit distance (default 2.5).

    Returns
    -------
    dict
        stop_loss, take_profit, risk_reward_ratio, sl_distance_pct,
        tp_distance_pct, direction, atr, sl_mult, tp_mult.
    """
    long = _is_long(direction)
    sl_dist = atr * sl_mult
    tp_dist = atr * tp_mult

    if long:
        stop_loss = entry - sl_dist
        take_profit = entry + tp_dist
    else:
        stop_loss = entry + sl_dist
        take_profit = entry - tp_dist

    rr = tp_dist / sl_dist if sl_dist > 0 else float("inf")

    return {
        "stop_loss": round(stop_loss, 8),
        "take_profit": round(take_profit, 8),
        "risk_reward_ratio": round(rr, 4),
        "sl_distance_pct": round(sl_dist / entry * 100, 4),
        "tp_distance_pct": round(tp_dist / entry * 100, 4),
        "direction": "LONG" if long else "SHORT",
        "atr": atr,
        "sl_mult": sl_mult,
        "tp_mult": tp_mult,
    }


# ---------------------------------------------------------------------------
# Trailing stop
# ---------------------------------------------------------------------------

def trailing_stop(
    entry: float,
    current_price: float,
    direction: str,
    atr: float,
    trail_mult: float = 1.5,
) -> Dict[str, Union[float, bool]]:
    """Compute a trailing stop and check whether to exit.

    The trail stop follows price by ``trail_mult * atr`` behind the
    current price (below for LONG, above for SHORT).

    Parameters
    ----------
    entry : float
        Original entry price.
    current_price : float
        Current market price.
    direction : str
        "LONG" or "SHORT".
    atr : float
        Current ATR value.
    trail_mult : float
        ATR multiplier for trail distance (default 1.5).

    Returns
    -------
    dict
        trail_stop, should_exit (bool), unrealized_pnl_pct.
    """
    long = _is_long(direction)
    trail_dist = atr * trail_mult

    if long:
        trail_level = current_price - trail_dist
        should_exit = current_price <= trail_level  # never True here by definition
        # But the real check: has price pulled back to the trail?
        # Trail stop is meaningful when comparing against the *highest* price seen.
        # For a single-call helper, we compare entry to current.
        should_exit = current_price <= entry - trail_dist
        pnl_pct = (current_price - entry) / entry * 100
    else:
        trail_level = current_price + trail_dist
        should_exit = current_price >= entry + trail_dist
        pnl_pct = (entry - current_price) / entry * 100

    return {
        "trail_stop": round(trail_level, 8),
        "should_exit": bool(should_exit),
        "unrealized_pnl_pct": round(pnl_pct, 4),
    }


# ---------------------------------------------------------------------------
# Breakeven stop
# ---------------------------------------------------------------------------

def breakeven_stop(
    entry: float,
    current_price: float,
    direction: str,
    atr: float,
    trigger_mult: float = 1.0,
) -> Dict[str, Union[float, bool, str]]:
    """Move stop to breakeven once price moves ``trigger_mult * atr`` in favour.

    Parameters
    ----------
    entry : float
        Original entry price.
    current_price : float
        Current market price.
    direction : str
        "LONG" or "SHORT".
    atr : float
        Current ATR value.
    trigger_mult : float
        How many ATRs of favourable move before triggering (default 1.0).

    Returns
    -------
    dict
        new_sl (breakeven price or None), triggered (bool), reason.
    """
    long = _is_long(direction)
    threshold = atr * trigger_mult

    if long:
        move = current_price - entry
        triggered = move >= threshold
    else:
        move = entry - current_price
        triggered = move >= threshold

    if triggered:
        # Move SL to entry (breakeven), plus a tiny buffer of 0.1 * ATR
        buffer = atr * 0.1
        new_sl = (entry + buffer) if long else (entry - buffer)
        reason = (
            f"Price moved {move:.2f} ({move / entry * 100:.2f}%) in favour "
            f"(>= {trigger_mult}x ATR = {threshold:.2f}). SL moved to breakeven + buffer."
        )
    else:
        new_sl = None
        reason = (
            f"Price move {move:.2f} not yet >= {trigger_mult}x ATR ({threshold:.2f}). "
            "Breakeven not triggered."
        )

    return {
        "new_sl": round(new_sl, 8) if new_sl is not None else None,
        "triggered": triggered,
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# Adaptive levels (confidence + regime)
# ---------------------------------------------------------------------------

# Regime presets: (sl_mult_adj, tp_mult_adj)
#   - trending: wider TP (let winners run), normal SL
#   - ranging:  tighter TP (take profit quickly), tighter SL
#   - volatile: wider SL (avoid whipsaws), wider TP
_REGIME_ADJUSTMENTS = {
    "normal":   (1.0, 1.0),
    "trending": (1.0, 1.4),
    "ranging":  (0.8, 0.7),
    "volatile": (1.5, 1.3),
}


def adaptive_levels(
    entry: float,
    direction: str,
    atr: float,
    confidence: float,
    regime: str = "normal",
    base_sl_mult: float = 1.5,
    base_tp_mult: float = 2.5,
) -> Dict[str, Union[float, str]]:
    """Compute SL/TP adjusted by signal confidence and market regime.

    Higher confidence (0-1) produces tighter stops and wider take-profit
    (more conviction = expect the move to happen, tighter risk).
    Lower confidence widens stops and tightens TP (less conviction = protect more).

    Parameters
    ----------
    entry : float
        Entry price.
    direction : str
        "LONG" or "SHORT".
    atr : float
        Current ATR value.
    confidence : float
        Signal confidence in [0, 1]. Higher = more conviction.
    regime : str
        Market regime: "normal", "trending", "ranging", "volatile".
    base_sl_mult : float
        Base SL ATR multiplier before adjustments (default 1.5).
    base_tp_mult : float
        Base TP ATR multiplier before adjustments (default 2.5).

    Returns
    -------
    dict
        stop_loss, take_profit, risk_reward_ratio, sl_distance_pct,
        tp_distance_pct, direction, regime, confidence, effective_sl_mult,
        effective_tp_mult.
    """
    confidence = float(np.clip(confidence, 0.0, 1.0))

    if regime not in _REGIME_ADJUSTMENTS:
        raise ValueError(
            f"Unknown regime '{regime}'. Choose from: {list(_REGIME_ADJUSTMENTS.keys())}"
        )

    regime_sl_adj, regime_tp_adj = _REGIME_ADJUSTMENTS[regime]

    # Confidence adjustment:
    #   SL: high confidence -> tighter (multiply by 1.2 - 0.4*conf => 0.8 at conf=1, 1.2 at conf=0)
    #   TP: high confidence -> wider  (multiply by 0.7 + 0.6*conf => 1.3 at conf=1, 0.7 at conf=0)
    conf_sl_adj = 1.2 - 0.4 * confidence  # range [0.8, 1.2]
    conf_tp_adj = 0.7 + 0.6 * confidence  # range [0.7, 1.3]

    effective_sl_mult = base_sl_mult * regime_sl_adj * conf_sl_adj
    effective_tp_mult = base_tp_mult * regime_tp_adj * conf_tp_adj

    levels = vol_targeted_levels(
        entry=entry,
        direction=direction,
        atr=atr,
        sl_mult=effective_sl_mult,
        tp_mult=effective_tp_mult,
    )

    # Enrich with adaptive metadata
    levels["regime"] = regime
    levels["confidence"] = confidence
    levels["effective_sl_mult"] = round(effective_sl_mult, 4)
    levels["effective_tp_mult"] = round(effective_tp_mult, 4)

    return levels
