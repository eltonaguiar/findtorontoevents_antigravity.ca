"""DXY (US Dollar Index) inverse booster for COMMODITY picks.

Empirical basis: USD and commodity prices are negatively correlated
(Gorton & Rouwenhorst 2006; Erb & Harvey 2006; IMF commodity price studies).
When DXY is trending below its 20-day SMA (USD weakening), commodity LONGs
get a +6 score boost. When DXY is trending above 20-day SMA and rising,
LONG picks get a small penalty (-3) and SHORT picks get a boost (+4).

State file: alpha_engine/data/dxy_state.json
Updated by: tools/dxy_state_updater.py (runs daily before market open)

Fail-open: returns 0 on any error (missing file, stale data, import error).
Kill-switch: DXY_BOOSTER_DISABLED=1 env var.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_STATE_FILE = Path(__file__).parent / "data" / "dxy_state.json"
_STALE_HOURS = 96  # treat state as stale after 96h (covers 3-day holiday weekends e.g. Memorial Day)

# Score adjustments (empirically conservative — can be raised after 30d shadow)
_LONG_BONUS_WHEN_WEAK = 6    # DXY below SMA20 → commodity LONGs favored
_LONG_PENALTY_WHEN_STRONG = -3  # DXY above SMA20 → commodity LONGs penalized
_SHORT_BONUS_WHEN_STRONG = 4   # DXY rising above SMA20 → commodity SHORTs favored


def _load_dxy_state() -> dict | None:
    """Load and validate dxy_state.json. Returns None if missing/stale/invalid."""
    if not _STATE_FILE.exists():
        return None
    try:
        state = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        log.warning("dxy_booster: failed to read %s", _STATE_FILE)
        return None
    ts_str = state.get("generated_at", "")
    if not ts_str:
        return None
    try:
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
        if age_hours > _STALE_HOURS:
            log.warning("dxy_booster: state is %.1fh old (>%dh) — returning neutral", age_hours, _STALE_HOURS)
            return None
    except (ValueError, TypeError):
        return None
    return state


def dxy_score_adjustment(pick: dict) -> int:
    """Return score delta for a COMMODITY pick based on DXY trend direction.

    Ordering note: this runs on already-gated active_picks in run_score_booster().
    Picks that were filtered out (score below elite_score floor) before the gate
    cannot be rescued by this adjustment. Full pre-gate wiring would require
    integrating into calculate_smart_score() — deferred (complexity vs marginal gain).

    Returns 0 for non-COMMODITY picks, stale/missing state, or kill-switch.
    """
    if not isinstance(pick, dict):
        return 0
    if os.environ.get("DXY_BOOSTER_DISABLED", "0") in ("1", "true", "True", "TRUE"):
        return 0

    ac = str(pick.get("asset_class", "") or "").upper()
    if ac != "COMMODITY":
        return 0

    state = _load_dxy_state()
    if state is None:
        return 0

    trend = str(state.get("trend", "") or "").upper()  # "WEAK" | "STRONG" | "NEUTRAL"
    direction = str(pick.get("direction", pick.get("signal", "")) or "").upper()
    is_long = direction in ("LONG", "BUY")
    is_short = direction in ("SHORT", "SELL")

    if trend == "WEAK":
        # USD weakening → commodity prices tend to rise → favor LONGs
        if is_long:
            return _LONG_BONUS_WHEN_WEAK
        return 0
    elif trend == "STRONG":
        # USD strengthening → commodity prices tend to fall → penalize LONGs
        if is_long:
            return _LONG_PENALTY_WHEN_STRONG
        elif is_short:
            return _SHORT_BONUS_WHEN_STRONG
        return 0
    return 0  # NEUTRAL


def get_dxy_state_summary() -> dict:
    """Return current DXY state for dashboard/logging use."""
    state = _load_dxy_state()
    if state is None:
        return {"available": False, "trend": "UNKNOWN"}
    return {
        "available": True,
        "trend": state.get("trend", "UNKNOWN"),
        "dxy_close": state.get("dxy_close"),
        "dxy_sma20": state.get("dxy_sma20"),
        "generated_at": state.get("generated_at"),
    }
