"""Per-asset-class smart-score predictor using only verified-IC features.

Replaces the legacy 35%-elite_score weighting (elite_score Spearman
ρ≈+0.02 = NOISE per ``tools/predictor_ic_reproducer.py``) with a
trust_score-led blend. Tracks the corrected mimo proposal of 2026-05-13
after the original was scrapped for citing IC values from fields that
don't exist in production data (``regime_bonus``,
``ml_replacement_score``, ``source_system_tier``).

Verified IC values (Spearman ρ vs ``pnl_pct``, ghost-filtered):

==================  ============  =========================================
feature             ρ (closed)    note
==================  ============  =========================================
trust_score         +0.154        recent_closed dataset (n=3500). STRONGEST.
elite_score         +0.023        closed_picks ghost-filtered (n=7178). NOISE.
confidence          -0.048        recent_closed (n=3500). INVERTS — penalty.
==================  ============  =========================================

Unquantified-but-plausible features are kept as minority weights:
``direction_x_regime`` (regime gate), ``freshness``, ``tp_upside_remaining``,
``htf_alignment``. None of these have measured IC in the production
dataset — encoded weights reflect design intent only, NOT empirical
edge. If you need to justify them empirically, run
``tools/predictor_ic_reproducer.py`` against a dataset that records
those fields.

Confidence is **not a positive gate**. ``min_confidence_smart = 0.0``
for every class. Higher confidence DEDUCTS from the score (penalty
coefficient encoded in ``CONFIDENCE_PENALTY``).

Pure function. No global state. Single entry point::

    adjusted = per_asset_class_smart_score(pick, base_smart_score=None)
        -> float    # 0..100

Designed for opt-in wire-up behind an env flag.

Wiring Plan (per CLAUDE.md Wire-Up Rule):
    Target caller: ``audit_trail/quality_gates.py::calculate_smart_score``.
    Wired and active in shadow mode (stamps ``smart_score_v2_shadow``,
    returns legacy score). Shadow mode default-ON; flip
    ``PER_ASSET_CLASS_SCORING_SHADOW=0`` to activate live scoring.
    trust_score is now enriched on-demand inside calculate_smart_score
    if not pre-populated by production_scanner (2026-05-19 fix).

NFA. Read-only. No side-effects.
"""
from __future__ import annotations
import math
import os
from typing import Any

# Per-class weight maps. Positive weights MUST sum to 1.0.
# confidence_penalty is applied separately (subtracted from final score).
# trust_score weight is the largest positive weight for every class —
# tested in tests/test_audit_enhancements_2026_05_13.py.
WEIGHTS_DEFAULT: dict[str, float] = {
    "trust_score":          0.35,
    "elite_score":          0.15,
    "direction_x_regime":   0.20,
    "freshness":            0.10,
    "tp_upside_remaining":  0.10,
    "htf_alignment":        0.10,
}

WEIGHTS_BY_CLASS: dict[str, dict[str, float]] = {
    "CRYPTO": {
        "trust_score":          0.40,
        "elite_score":          0.10,
        "direction_x_regime":   0.25,
        "freshness":            0.10,
        "tp_upside_remaining":  0.10,
        "htf_alignment":        0.05,
    },
    "EQUITY": {
        "trust_score":          0.35,
        "elite_score":          0.15,
        "direction_x_regime":   0.20,
        "freshness":            0.10,
        "tp_upside_remaining":  0.10,
        "htf_alignment":        0.05,
        "sector_rs_score":      0.05,  # IDEA-A: sector ETF RS (Moskowitz & Grinblatt 1999)
    },
    "COMMODITY": {
        "trust_score":          0.35,
        "elite_score":          0.10,  # reduced from 0.15 (elite_score IC ≈ noise; room for fundamentals)
        "direction_x_regime":   0.20,
        "freshness":            0.10,
        "tp_upside_remaining":  0.10,
        "htf_alignment":        0.05,  # reduced from 0.10 to make room for new factors
        "bdi_momentum_score":   0.05,  # IDEA-A: Baltic Dry Index momentum (bulk commodities)
        "crop_condition_score": 0.05,  # IDEA-A: USDA NASS crop condition z-score (CT=F)
    },
    "FOREX": {
        "trust_score":          0.40,
        "elite_score":          0.10,
        "direction_x_regime":   0.20,
        "freshness":            0.10,
        "tp_upside_remaining":  0.10,
        "htf_alignment":        0.10,
    },
    "ETF": {
        "trust_score":          0.35,
        "elite_score":          0.15,
        "direction_x_regime":   0.20,
        "freshness":            0.10,
        "tp_upside_remaining":  0.10,
        "htf_alignment":        0.10,
    },
    "BOND": {
        "trust_score":          0.40,
        "elite_score":          0.10,
        "direction_x_regime":   0.20,
        "freshness":            0.10,
        "tp_upside_remaining":  0.10,
        "htf_alignment":        0.10,
    },
    "FUTURES": {
        "trust_score":          0.40,
        "elite_score":          0.10,
        "direction_x_regime":   0.20,
        "freshness":            0.10,
        "tp_upside_remaining":  0.10,
        "htf_alignment":        0.10,
    },
}

# Confidence is anti-predictive on recent_closed (ρ=-0.048). Higher
# confidence → larger deduction. CRYPTO + FOREX show the strongest
# inversion in the IC reproducer; equity / commodity less so.
CONFIDENCE_PENALTY: dict[str, float] = {
    "CRYPTO":    0.08,
    "FOREX":     0.08,
    "ETF":       0.06,
    "EQUITY":    0.04,
    "COMMODITY": 0.04,
    "BOND":      0.04,
    "FUTURES":   0.04,
}
CONFIDENCE_PENALTY_DEFAULT = 0.04

# Per-class minimum confidence to enter the smart-gate. ALL ZERO —
# confidence is no longer a positive gate. Use trust_tier for trust gating.
MIN_CONFIDENCE_SMART: dict[str, float] = {
    "CRYPTO":    0.0,
    "FOREX":     0.0,
    "ETF":       0.0,
    "EQUITY":    0.0,
    "COMMODITY": 0.0,
    "BOND":      0.0,
    "FUTURES":   0.0,
}

# Hard-blocked classes — score forced to 0 regardless of inputs.
# FUTURES: 157 closed picks, 2.5% WR — confirmed drag per AA-6 audit.
HARD_BLOCKED_CLASSES: dict[str, str] = {
    "FUTURES": "AA-6: FUTURES 157 picks @ 2.5% WR — confirmed drag, scoring suppressed",
}

# Trust-tier fallback: when numeric trust_score is missing but
# trust_tier is set, map to a numeric proxy. Values calibrated so the
# tier-derived score reflects the IC observed for trust_score (+0.154
# verified). PROVEN/RELIABLE come from the canonical tier set
# (project_strategy_state_2026_05_03).
TRUST_TIER_FALLBACK: dict[str, float] = {
    "PROVEN":     90.0,
    "RELIABLE":   70.0,
    "DEVELOPING": 40.0,
    "WATCH":      30.0,
    "UNVERIFIED": 20.0,
    "UNTRUSTED":  10.0,
}


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def _class_of(pick: dict) -> str:
    return (pick.get("asset_class") or "").upper()


def get_weights(asset_class: str) -> dict[str, float]:
    """Return per-class weight map (default if class unknown)."""
    return dict(WEIGHTS_BY_CLASS.get((asset_class or "").upper(), WEIGHTS_DEFAULT))


def min_confidence_smart(asset_class: str) -> float:
    return MIN_CONFIDENCE_SMART.get((asset_class or "").upper(), 0.0)


def is_hard_blocked(asset_class: str) -> tuple[bool, str]:
    """Return (blocked, reason). Reason empty when not blocked."""
    reason = HARD_BLOCKED_CLASSES.get((asset_class or "").upper())
    if reason:
        return True, reason
    return False, ""


def _feature_value(pick: dict, name: str) -> float:
    """Extract a single feature in 0..100 scale. Missing → 0.0 (for
    real-signal features) or 50.0 (for design-intent neutral features).
    """
    if name == "trust_score":
        v = pick.get("trust_score")
        if v is not None:
            raw = _safe_float(v)
            # trust_score is 0-10; scale to 0-100 for weighted-sum consistency.
            # Values already in 0-100 range (>10) are passed through unchanged to
            # tolerate any future re-scaling of the trust model.
            if raw <= 10.0:
                raw = raw * 10.0
            return max(0.0, min(100.0, raw))
        # Fallback to tier string (mimo design suggestion incorporated)
        tier = (pick.get("trust_tier") or "").upper()
        if tier in TRUST_TIER_FALLBACK:
            return TRUST_TIER_FALLBACK[tier]
        return 0.0
    if name == "elite_score":
        return _safe_float(pick.get("elite_score"))
    if name == "direction_x_regime":
        # Composite: use regime_bonus if present, else fall back to
        # explicit direction_x_regime field, else neutral 50.
        v = pick.get("direction_x_regime")
        if v is None:
            v = pick.get("regime_bonus")
        return _safe_float(v, 50.0) if v is not None else 50.0
    if name == "freshness":
        # Repo convention: freshness ∈ [0, 100]. Missing → 50 (neutral).
        v = pick.get("freshness_score")
        if v is None:
            v = pick.get("freshness")
        return _safe_float(v, 50.0) if v is not None else 50.0
    if name == "tp_upside_remaining":
        v = pick.get("tp_upside_remaining_pct")
        if v is None:
            v = pick.get("tp_upside_remaining")
        # Clamp 0..100
        f = _safe_float(v, 50.0) if v is not None else 50.0
        return max(0.0, min(100.0, f))
    if name == "htf_alignment":
        v = pick.get("htf_alignment_score")
        if v is None:
            v = pick.get("htf_alignment")
        return _safe_float(v, 50.0) if v is not None else 50.0
    if name == "sector_rs_score":
        # IDEA-A: sector ETF relative-strength score in [0, 100]. Missing → 50 (neutral).
        v = pick.get("sector_rs_score")
        return _safe_float(v, 50.0) if v is not None else 50.0
    if name == "bdi_momentum_score":
        # IDEA-A: Baltic Dry Index 7-day ROC score in [0, 100]. Missing → 50 (neutral).
        v = pick.get("bdi_momentum_score")
        return _safe_float(v, 50.0) if v is not None else 50.0
    if name == "crop_condition_score":
        # IDEA-A: USDA NASS cotton crop condition z-score in [0, 100]. Missing → 50 (neutral).
        v = pick.get("crop_condition_score")
        return _safe_float(v, 50.0) if v is not None else 50.0
    return 0.0


def per_asset_class_smart_score(pick: dict,
                                base_smart_score: float | None = None,
                                blend_with_base: float = 0.0) -> float:
    """Compute a per-asset-class adjusted smart score.

    Args:
      pick: pick dict with at minimum ``asset_class`` and the feature
        fields used in the weight map. Missing features default to
        50.0 (neutral, except trust_score / elite_score which default
        to 0.0 — being absent is a real negative signal for those).
      base_smart_score: optional legacy smart score (0..100). When
        provided AND ``blend_with_base > 0``, the return value is a
        convex combination: ``(1-blend) * new + blend * base``. Use
        ``blend_with_base=0.4`` for a 60/40 gradual rollout.
      blend_with_base: 0..1.

    Returns:
      Adjusted score in [0, 100]. Confidence penalty is applied AFTER
      the weighted sum.
    """
    ac = _class_of(pick)
    blocked, _reason = is_hard_blocked(ac)
    if blocked:
        return 0.0
    weights = get_weights(ac)
    raw = 0.0
    for feat, w in weights.items():
        raw += w * _feature_value(pick, feat)
    # Confidence is a PENALTY, not a gate. Pick's confidence is
    # typically in [0, 1] in this repo, but tolerate either scale.
    conf = _safe_float(pick.get("confidence"), 0.0)
    if conf > 1.5:
        conf = conf / 100.0
    conf = max(0.0, min(1.0, conf))
    penalty_coef = CONFIDENCE_PENALTY.get(ac, CONFIDENCE_PENALTY_DEFAULT)
    # Max penalty applied at conf=1.0 is penalty_coef * 100 points.
    raw_after_penalty = raw - (penalty_coef * 100.0 * conf)
    # Clamp 0..100
    new_score = max(0.0, min(100.0, raw_after_penalty))
    if base_smart_score is not None and blend_with_base > 0.0:
        b = max(0.0, min(1.0, blend_with_base))
        base = max(0.0, min(100.0, _safe_float(base_smart_score, new_score)))
        return (1.0 - b) * new_score + b * base
    return new_score


def is_enabled() -> bool:
    """Default ON as of 2026-05-13 (shadow-only by default — see is_shadow_mode).
    Override: ``PER_ASSET_CLASS_SCORING_ENABLED=0`` fully disables the overlay."""
    return os.environ.get("PER_ASSET_CLASS_SCORING_ENABLED", "1") == "1"


def is_shadow_mode() -> bool:
    """Default ON as of 2026-05-13: stamps ``smart_score_v2_shadow`` on pick
    dicts but returns the legacy clamped score (no live behavior change).
    Starts the 14d data-collection soak required by the activation playbook
    in reports/audit_enhancements_2026-05-13/SYNTHESIS.md. Override to flip
    to live blending: ``PER_ASSET_CLASS_SCORING_SHADOW=0``."""
    return os.environ.get("PER_ASSET_CLASS_SCORING_SHADOW", "1") == "1"
