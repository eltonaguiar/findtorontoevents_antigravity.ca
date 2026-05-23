"""
ALPHA ENGINE — Hold Duration Optimizer
=======================================
Dynamically adjusts SL, TP, and trailing stop parameters based on how long
a pick has been held.

Empirical evidence from 500 closed picks:
  0-24h hold:  41% WR, -0.54% avg PnL  (worst — early SL kills winners)
  1-2d hold:   35% WR, +0.44% avg PnL  (below avg but positive)
  2-3d hold:   71% WR, +7.32% avg PnL  (sweet spot)
  3-7d hold:   67% WR, +11.90% avg PnL (massive returns)
  7d+ hold:    52% WR, +1.20% avg PnL  (diminishing)

Strategy: widen SL in the first 24h (let trades breathe past the worst
bucket), keep normal SL during the sweet spot, then tighten to lock in
gains once returns start diminishing.

Integration: forward_validator.py calls adjust_risk_for_duration() before
checking SL/TP/trailing stop exit conditions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Duration phase thresholds (hours)
# ---------------------------------------------------------------------------
GRACE_END_H = 4.0       # Existing SL grace period (no SL check at all)
BREATHING_END_H = 24.0  # Widened SL phase ends
SWEET_SPOT_END_H = 72.0 # Normal SL phase ends; then tighten

# ---------------------------------------------------------------------------
# SL multipliers per phase
# ---------------------------------------------------------------------------
SL_MULTIPLIER_BREATHING = 1.5   # 0-24h: widen SL by 50% (give room)
SL_MULTIPLIER_NORMAL = 1.0      # 24-72h: standard SL (sweet spot)
SL_MULTIPLIER_TIGHTEN = 0.75    # 72h+: tighten SL by 25% (lock gains)

# ---------------------------------------------------------------------------
# Trailing stop overrides by duration
# ---------------------------------------------------------------------------
TRAIL_ACTIVATE_48H = 0.02  # After 48h: activate trail at 2% profit (was 4%)
TRAIL_ACTIVATE_72H = 0.02  # After 72h: keep 2% activation
TRAIL_PCT_72H = 0.05       # After 72h: 5% trail (was 10% for crypto)


def get_pick_age_hours(pick: dict[str, Any]) -> float | None:
    """Return pick age in hours from created_at timestamp, or None if unknown."""
    created_at_str = pick.get("created_at", "")
    if not created_at_str:
        return None
    try:
        created_dt = datetime.fromisoformat(
            created_at_str.replace("Z", "+00:00")
        )
        # Ensure timezone-aware
        if created_dt.tzinfo is None:
            created_dt = created_dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - created_dt
        return max(delta.total_seconds() / 3600.0, 0.0)
    except (ValueError, TypeError, OSError):
        return None


def _get_duration_phase(hours_held: float) -> str:
    """Classify hold duration into a named phase."""
    if hours_held < GRACE_END_H:
        return "grace"
    elif hours_held < BREATHING_END_H:
        return "breathing"
    elif hours_held < SWEET_SPOT_END_H:
        return "sweet_spot"
    else:
        return "tighten"


def adjust_risk_for_duration(
    pick: dict[str, Any],
    hours_held: float | None = None,
    *,
    base_sl_pct: float | None = None,
    base_tp_pct: float | None = None,
    base_trail_pct: float | None = None,
    base_trail_activate_pct: float = 0.04,
) -> dict[str, Any]:
    """
    Compute duration-adjusted risk parameters for a pick.

    Parameters
    ----------
    pick : dict
        The pick dict (needs at minimum 'created_at' if hours_held not given).
    hours_held : float, optional
        Override for pick age in hours.  If None, computed from pick['created_at'].
    base_sl_pct : float, optional
        Base stop-loss percentage (negative, e.g. -0.08).  If None, read from
        pick['sl_pct'] or defaults to -0.08.
    base_tp_pct : float, optional
        Base take-profit percentage (positive, e.g. 0.15).  If None, read from
        pick['tp_pct'] or defaults to 0.15.
    base_trail_pct : float, optional
        Base trailing stop percentage (e.g. 0.10).  If None, defaults to 0.10.
    base_trail_activate_pct : float
        Base trailing stop activation threshold (e.g. 0.04).

    Returns
    -------
    dict with keys:
        sl_pct          - adjusted stop-loss percentage (negative)
        tp_pct          - adjusted take-profit percentage (positive)
        trail_pct       - adjusted trailing stop percentage
        trail_activate  - adjusted trailing stop activation threshold
        phase           - duration phase name (grace/breathing/sweet_spot/tighten)
        hours_held      - actual hours held used for the calculation
        sl_multiplier   - SL multiplier applied
    """
    # Resolve hours held
    if hours_held is None:
        hours_held = get_pick_age_hours(pick)
    if hours_held is None:
        hours_held = 0.0

    # Resolve base values
    if base_sl_pct is None:
        base_sl_pct = pick.get("sl_pct", -0.08)
        if base_sl_pct is None:
            base_sl_pct = -0.08
    if base_tp_pct is None:
        base_tp_pct = pick.get("tp_pct", 0.15)
        if base_tp_pct is None:
            base_tp_pct = 0.15
    if base_trail_pct is None:
        base_trail_pct = pick.get("trail_pct", 0.10)
        if base_trail_pct is None:
            base_trail_pct = 0.10

    # Ensure types are float
    try:
        base_sl_pct = float(base_sl_pct)
        base_tp_pct = float(base_tp_pct)
        base_trail_pct = float(base_trail_pct)
        base_trail_activate_pct = float(base_trail_activate_pct)
        hours_held = float(hours_held)
    except (TypeError, ValueError):
        # If conversion fails, return unchanged defaults
        return {
            "sl_pct": -0.08,
            "tp_pct": 0.15,
            "trail_pct": 0.10,
            "trail_activate": 0.04,
            "phase": "unknown",
            "hours_held": 0.0,
            "sl_multiplier": 1.0,
        }

    phase = _get_duration_phase(hours_held)

    # --- SL adjustment ---
    if phase == "grace":
        # During grace period the SL is not checked at all (handled by
        # forward_validator's existing _in_sl_grace logic).  We still return
        # the widened SL in case caller wants to display it.
        sl_mult = SL_MULTIPLIER_BREATHING
    elif phase == "breathing":
        sl_mult = SL_MULTIPLIER_BREATHING
    elif phase == "sweet_spot":
        sl_mult = SL_MULTIPLIER_NORMAL
    else:  # tighten
        sl_mult = SL_MULTIPLIER_TIGHTEN

    # SL is negative, so multiplying by >1 makes it *more* negative (wider).
    # e.g. -0.08 * 1.5 = -0.12 (wider stop)
    adjusted_sl = base_sl_pct * sl_mult

    # --- TP stays unchanged ---
    # We don't shrink TP — let winners run to full target.
    adjusted_tp = base_tp_pct

    # --- Trailing stop adjustment ---
    adjusted_trail = base_trail_pct
    adjusted_trail_activate = base_trail_activate_pct

    if hours_held >= 72.0:
        # After 72h: tighten trail to 5% and activate at 2%
        adjusted_trail = min(base_trail_pct, TRAIL_PCT_72H)
        adjusted_trail_activate = min(base_trail_activate_pct, TRAIL_ACTIVATE_72H)
    elif hours_held >= 48.0:
        # After 48h: lower activation threshold to 2%
        adjusted_trail_activate = min(base_trail_activate_pct, TRAIL_ACTIVATE_48H)

    return {
        "sl_pct": round(adjusted_sl, 6),
        "tp_pct": round(adjusted_tp, 6),
        "trail_pct": round(adjusted_trail, 6),
        "trail_activate": round(adjusted_trail_activate, 6),
        "phase": phase,
        "hours_held": round(hours_held, 2),
        "sl_multiplier": sl_mult,
    }


def apply_adjusted_sl_tp(
    pick: dict[str, Any],
    entry_price: float,
    signal_type: str = "BUY",
    hours_held: float | None = None,
    category: str = "crypto",
) -> dict[str, float | None]:
    """
    Convenience: compute adjusted absolute SL and TP prices for a pick.

    Parameters
    ----------
    pick : dict
        The pick dict.
    entry_price : float
        Entry price of the position.
    signal_type : str
        'BUY' or 'SELL'.
    hours_held : float, optional
        Override pick age.
    category : str
        Asset category for looking up base risk params.

    Returns
    -------
    dict with 'sl_price', 'tp_price', 'trail_pct', 'trail_activate', 'phase'.
    """
    # Import here to avoid circular imports at module level
    try:
        from alpha_engine.config import CATEGORY_RISK, TRAILING_STOP, TRAIL_ACTIVATE_PCT
    except ImportError:
        # Fallback defaults if config unavailable
        CATEGORY_RISK = {"crypto": (-0.08, 0.15, 7)}
        TRAILING_STOP = {"crypto": 0.10}
        TRAIL_ACTIVATE_PCT = 0.04

    sl_pct, tp_pct, _ = CATEGORY_RISK.get(category, (-0.08, 0.15, 7))
    trail_pct = TRAILING_STOP.get(category, 0.10)

    adj = adjust_risk_for_duration(
        pick,
        hours_held=hours_held,
        base_sl_pct=sl_pct,
        base_tp_pct=tp_pct,
        base_trail_pct=trail_pct,
        base_trail_activate_pct=TRAIL_ACTIVATE_PCT,
    )

    try:
        entry_price = float(entry_price)
    except (TypeError, ValueError):
        return {
            "sl_price": None,
            "tp_price": None,
            "trail_pct": adj["trail_pct"],
            "trail_activate": adj["trail_activate"],
            "phase": adj["phase"],
        }

    if signal_type == "BUY":
        sl_price = entry_price * (1 + adj["sl_pct"])   # sl_pct is negative
        tp_price = entry_price * (1 + adj["tp_pct"])
    else:  # SELL / SHORT
        sl_price = entry_price * (1 - adj["sl_pct"])   # For shorts, SL is above entry
        tp_price = entry_price * (1 - adj["tp_pct"])

    return {
        "sl_price": round(sl_price, 8),
        "tp_price": round(tp_price, 8),
        "trail_pct": adj["trail_pct"],
        "trail_activate": adj["trail_activate"],
        "phase": adj["phase"],
    }
