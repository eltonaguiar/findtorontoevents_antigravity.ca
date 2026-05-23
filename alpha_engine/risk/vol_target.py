"""Volatility-targeted position sizing (Moreira-Muir 2017 inspired).

Per Phase 2-A CRYPTO panel + 5-stream consensus 2026-04-29:
MDD is the binding constraint on CRYPTO (177% peak-to-trough vs cap 35%).
This module reduces position size when realized volatility is high so that
realized portfolio MDD can drop into Tier-2 range (15-20%) without
sacrificing strategy edge.

Default-off: operator must set CRYPTO_VOL_TARGET_ENABLED=1 to activate.
Rollback: unset or set to "0" to disable.

References:
- Moreira-Muir 2017 "Volatility-Managed Portfolios"
- Phase 2-A CRYPTO panel 7/8 vote
- minimax-m2.5: Kelly% x RegimeConfidenceFactor x EdgeMagnitudeFactor

Note: this module is a NEW opt-in sidecar; it does NOT modify the existing
`alpha_engine/kelly_position_sizer.py` (which is already wired into
`production_scanner.py` with always-on Kelly + vol scaling at target_vol=0.15
and clamp [0.25, 2.0]). This sidecar is scoped to CRYPTO only with a clamp
of [0.25, 1.0] (no leverage) and is gated by an env flag for operator-runway
shadow validation per CLAUDE.md Wire-Up Rule.
"""
from __future__ import annotations

import os
from typing import Optional

DEFAULT_VOL_TARGET_PCT = 30.0  # annualized — operator-tunable via env
DEFAULT_MIN_SCALE = 0.25
DEFAULT_MAX_SCALE = 1.0


def crypto_vol_target_enabled() -> bool:
    """Return True iff the CRYPTO_VOL_TARGET_ENABLED env flag is set to '1'."""
    return os.environ.get("CRYPTO_VOL_TARGET_ENABLED", "0") == "1"


def get_vol_target_pct() -> float:
    """Return the configured annualized vol target (default 30.0%)."""
    try:
        return float(os.environ.get("CRYPTO_VOL_TARGET_PCT", DEFAULT_VOL_TARGET_PCT))
    except (TypeError, ValueError):
        return DEFAULT_VOL_TARGET_PCT


def compute_size_scale(realized_vol_pct: Optional[float]) -> float:
    """Return position-size multiplier in [0.25, 1.0].

    If realized vol unavailable, return 1.0 (no scaling — preserves current behavior).
    If realized vol > vol target, scale DOWN (target / realized).
    If realized vol < vol target, scale UP but cap at 1.0 (no leverage).
    """
    if realized_vol_pct is None or realized_vol_pct <= 0:
        return 1.0
    target = get_vol_target_pct()
    raw_scale = target / realized_vol_pct
    return max(DEFAULT_MIN_SCALE, min(DEFAULT_MAX_SCALE, raw_scale))


def apply_to_pick(pick: dict, realized_vol_pct: Optional[float] = None) -> dict:
    """Mutate pick dict to apply vol-target scaling to its position size.

    Reads pick.realized_vol_pct or accepts override. Writes:
    - pick['_vol_target_scale']: float (the multiplier applied)
    - pick['position_size_pct']: scaled (existing field, multiplied by scale)

    No-op if asset_class != CRYPTO or flag is off.
    """
    if not crypto_vol_target_enabled():
        return pick
    if str(pick.get("asset_class", "")).upper() != "CRYPTO":
        return pick
    rv = realized_vol_pct
    if rv is None:
        rv = pick.get("realized_vol_pct") or pick.get("atr_pct_annualized")
    scale = compute_size_scale(rv)
    pick["_vol_target_scale"] = scale
    if "position_size_pct" in pick:
        pick["position_size_pct"] = float(pick["position_size_pct"]) * scale
    return pick
