"""
Hedge-fund policy thresholds (approved 2026-04-04).

Centralizes numeric constants and pure helpers so quality_gates and tests can
share one definition. See docs/HEDGE_FUND_QUALITY_NEXT_STEPS.md.

This module must not import quality_gates (avoid cycles).
"""

from __future__ import annotations

# --- Threshold A: backtest vs forward decay hard gate ---
DECAY_HARD_GAP_PERCENTAGE_POINTS = 15.0
DECAY_HARD_MIN_CLOSED_TRADES = 20

# --- Other approved letters (for future wiring; documented in HF_NEXT_STEPS) ---
# B: concentration — implemented in score_booster / gates elsewhere
# C: agreeing_systems >= 2 for tier-1 — display/scoring
# D: strategy retirement fwd_WR < 45% after 30 trades
# E: portfolio DD > 15% pause 24h
# F: ml_composite fallback conf * 0.5 — smart_picks_engine
# G: consensus conflict hard-reject — quality_gates


def normalize_wr_percent(value: object) -> float | None:
    """
    Normalize a win-rate field to 0..100 percentage points.

    Accepts ratio form (0..1) or already-percent form (e.g. 62.5).
    Returns None if missing or non-numeric.
    """
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if 0.0 <= f <= 1.0:
        return f * 100.0
    return f


def decay_hard_gate_triggers(
    bt_wr: object,
    fwd_wr: object,
    n_closed: int,
    gap_pp: float = DECAY_HARD_GAP_PERCENTAGE_POINTS,
    min_closed: int = DECAY_HARD_MIN_CLOSED_TRADES,
) -> bool:
    """
    Threshold A: True when forward WR is materially below backtest WR with
    enough closed trades (policy: reject / exclude from smart tier).

    Policy (user-approved): reject if fwd_WR < BT_WR - 15pp AND n_closed >= 20.

    If bt_wr or fwd_wr cannot be normalized, returns False (no gate — missing
    data should not silently punish).
    """
    if n_closed < min_closed:
        return False
    bt = normalize_wr_percent(bt_wr)
    fwd = normalize_wr_percent(fwd_wr)
    if bt is None or fwd is None:
        return False
    return bool(fwd < (bt - gap_pp))
