"""Concept-aware scoring modifier for the elite scorer (B5 / Cursor Phase 3).

Shadow mode only — ``CONCEPT_SCORING_SHADOW=0`` (default) means every call
returns ``pts=0`` with no production impact.  Set to ``1`` after ≥7 days of
shadow evidence to activate modifiers.

Usage::

    from alpha_engine.concept_scorer import compute_concept_modifier
    result = compute_concept_modifier(pick, strategy_perf)
    score += result["pts"]          # always 0 when shadow is OFF
    breakdown["concept_modifier"] = result["pts"]

Modifier table (shadow ON):

    Family           pts   Gate condition
    -------          ---   --------------
    skyrocket        +3    n_closed ≥ 30 AND fwd_wr ≥ 0.50
    tradingagents    +2    n_closed ≥ 30 AND fwd_wr ≥ 0.55
    long_term_value  +1    unconditional
    penny_stock      -1    unconditional
    reverse_engineer -1    unconditional
    meme_coin        -2    unconditional
    standard          0    n/a
    mercury2          0    n/a

All modifiers are bounded to [-3, +3].

References
----------
* `reports/REMAINING_ACTION_ITEMS_2026_04_30.md` §4 B5 (Cursor Phase 3)
* `alpha_engine/concept_registry.py` — concept-family derivation (B4)
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

__all__ = ["compute_concept_modifier"]

_SHADOW_ON: bool = bool(int(os.getenv("CONCEPT_SCORING_SHADOW", "0")))

# Gated families: require sufficient forward-test evidence before awarding pts.
_GATED_FAMILIES: Dict[str, Dict[str, Any]] = {
    "skyrocket": {
        "pts": 3,
        "min_n": 30,
        "min_wr": 0.50,
    },
    "tradingagents": {
        "pts": 2,
        "min_n": 30,
        "min_wr": 0.55,
    },
}

# Ungated families: apply pts regardless of evidence (positive or negative signals
# baked into the concept itself rather than requiring empirical validation).
_UNGATED_FAMILIES: Dict[str, int] = {
    "long_term_value": 1,
    "penny_stock": -1,
    "reverse_engineer": -1,
    "meme_coin": -2,
    "standard": 0,
    "mercury2": 0,
}

_PTS_FLOOR = -3
_PTS_CAP = 3


def compute_concept_modifier(
    pick: Dict[str, Any],
    strategy_perf: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Return the concept-family scoring modifier for *pick*.

    Args:
        pick: Normalised pick dict (must include ``concept_family``).
        strategy_perf: Optional mapping with ``n_closed`` (int) and
            ``fwd_wr`` (float 0–1).  May be ``None`` — gated families
            will be treated as evidence-insufficient.

    Returns:
        dict with keys:
            pts (int): Score delta.  Always 0 when shadow is OFF.
            family (str): Resolved concept family.
            shadow_on (bool): Whether CONCEPT_SCORING_SHADOW is active.
            gated (bool): True if gate criterion was NOT met (pts clamped to 0).
            reason (str): Human-readable explanation.
    """
    family: str = str(pick.get("concept_family") or "standard").strip() or "standard"

    if not _SHADOW_ON:
        return {
            "pts": 0,
            "family": family,
            "shadow_on": False,
            "gated": False,
            "reason": "CONCEPT_SCORING_SHADOW=0 (default-off)",
        }

    # --- gated families ---
    if family in _GATED_FAMILIES:
        cfg = _GATED_FAMILIES[family]
        n_closed: int = 0
        fwd_wr: float = 0.0
        if strategy_perf is not None:
            raw_n = strategy_perf.get("n_closed")
            raw_wr = strategy_perf.get("fwd_wr")
            n_closed = int(raw_n) if raw_n is not None else 0
            fwd_wr = float(raw_wr) if raw_wr is not None else 0.0
        gate_met = n_closed >= cfg["min_n"] and fwd_wr >= cfg["min_wr"]
        if gate_met:
            pts = max(_PTS_FLOOR, min(_PTS_CAP, cfg["pts"]))
            return {
                "pts": pts,
                "family": family,
                "shadow_on": True,
                "gated": False,
                "reason": (
                    f"{family}: +{pts} (n={n_closed}≥{cfg['min_n']}, "
                    f"wr={fwd_wr:.1%}≥{cfg['min_wr']:.0%})"
                ),
            }
        else:
            return {
                "pts": 0,
                "family": family,
                "shadow_on": True,
                "gated": True,
                "reason": (
                    f"{family}: gated (n={n_closed}<{cfg['min_n']} "
                    f"OR wr={fwd_wr:.1%}<{cfg['min_wr']:.0%})"
                ),
            }

    # --- ungated families ---
    raw_pts = _UNGATED_FAMILIES.get(family, 0)
    pts = max(_PTS_FLOOR, min(_PTS_CAP, raw_pts))
    verb = f"+{pts}" if pts >= 0 else str(pts)
    return {
        "pts": pts,
        "family": family,
        "shadow_on": True,
        "gated": False,
        "reason": f"{family}: {verb} (unconditional)",
    }
