"""
feed_membership.py — Per-pick feed-membership evaluators
=========================================================

Phase 1 of the /audit remaining roadmap (see
docs/REMAINING_ENHANCEMENT_PROPOSALS_V3_2026_04_20.md).

Provides helpers to compute, per-pick, whether it is a:
  * Smart Pick            (delegates to audit_trail.quality_gates.passes_smart_gate)
  * Verified Alpha pick   (trust_tier=PROVEN AND source_system in allow-list)
  * High-Conviction tier  (minimal inline rule; Phase 3 parity-test vs
                           audit_dashboard/hc_filter.js and tools/hc_gates_python.py)

These helpers are consumed by audit_trail.stamp_pick_quality.stamp_picks,
which both stamps the live (overwriting) flags AND snapshots immutable
`at_issue_*` twins at the ACTIVE->CLOSED transition.

Design notes
------------
- Reuse of `tools/hc_gates_python.py` was deliberately avoided here. That
  module is Cursor-authored and its parity test against hc_filter.js is
  scheduled for Phase 3. Inlining a conservative rule keeps the stamp
  pipeline decoupled from the parity effort.
- VERIFIED_ALPHA_SOURCES is intentionally narrow and operator-maintained.
  Derived from the current cross_aggregation/system_trust_registry.py
  PROVEN entries. Items without a current PROVEN tag have been excluded.
"""

from __future__ import annotations

from typing import Optional

# ---------------------------------------------------------------------------
# Verified-Alpha allow-list
# ---------------------------------------------------------------------------
# Operator-maintained. A source belongs here ONLY when:
#   1. Its registry entry is TIER_PROVEN in cross_aggregation/system_trust_registry.py
#   2. The cohort has enough forward trades to justify labelling each pick
#      "Verified Alpha" at issue time
#   3. It is NOT in the human-override force-demotion set (see blocklist.py)
#
# Derived 2026-04-20 from the live registry. `claude_gainer_st` was initially
# listed but was force-demoted the same day (commit 534269141) after an
# effectiveness audit showed 790 of 790 PROVEN-tagged closes were from that
# single strategy with realized WR 26.7% / PF 0.52. Leaving it in this list
# would contradict the force-demote; cross-check the blocklist at evaluation
# time (see is_verified_alpha_per_pick) to auto-propagate any future demotion.
VERIFIED_ALPHA_SOURCES = frozenset({
    # claws_of_doom — 59 trades, 52.5% WR, +41% PnL (TIER_PROVEN)
    "claws_of_doom",
    # claude_gainer_st deliberately REMOVED 2026-04-20: see commit 534269141
    # force-demote rationale. Add back only after S4 rehabilitation and a
    # fresh effectiveness-audit pass.
})


# ---------------------------------------------------------------------------
# Smart-pick (per-pick)
# ---------------------------------------------------------------------------
def is_smart_pick_per_pick(pick: dict) -> Optional[bool]:
    """Return True/False if pick qualifies as a Smart Pick at issue time,
    or None if the required inputs (notably strategy) are missing.

    Mirrors `audit_trail.quality_gates.classify_pick_quality_v2` in that it
    clones status="ACTIVE" before delegating, so the gate evaluates at-issue
    quality irrespective of current resolved state.
    """
    if not isinstance(pick, dict):
        return None
    if not str(pick.get("strategy") or "").strip():
        return None
    if not pick.get("symbol"):
        return None

    try:
        from audit_trail.quality_gates import passes_smart_gate
    except Exception:
        return None

    clone = dict(pick)
    clone["status"] = "ACTIVE"
    try:
        return bool(passes_smart_gate(clone))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Verified Alpha (per-pick)
# ---------------------------------------------------------------------------
def is_verified_alpha_per_pick(pick: dict) -> bool:
    """Return True iff trust_tier == PROVEN AND source_system is in the
    operator-maintained VERIFIED_ALPHA_SOURCES allow-list AND the pick's
    strategy is NOT in the human-override force-demotion set.

    The force-demote cross-check (v1.1 governance reviewer) auto-propagates
    any strategy kicked out of PROVEN via `_FORCE_DEMOTED_STRATEGIES` into
    is_verified_alpha=False, even if the source_system is otherwise in the
    allow-list.
    """
    if not isinstance(pick, dict):
        return False
    trust = str(pick.get("trust_tier") or "").upper().strip()
    if trust != "PROVEN":
        return False
    source = str(pick.get("source_system") or "").strip()
    if source not in VERIFIED_ALPHA_SOURCES:
        return False
    # v1.1 override: if the strategy has been human-force-demoted, its
    # picks lose Verified-Alpha status regardless of registry tier.
    try:
        from audit_trail.stamp_pick_quality import _FORCE_DEMOTED_STRATEGIES
        strategy = str(pick.get("strategy") or "").strip()
        if strategy in _FORCE_DEMOTED_STRATEGIES:
            return False
    except Exception:
        pass
    return True


# ---------------------------------------------------------------------------
# HC tier (per-pick)
# ---------------------------------------------------------------------------
# PLACEHOLDER thresholds — empirical derivation deferred to Phase 3.
# These values (score 60/70, confidence 0.70/0.80) are NOT cited from any
# in-repo empirical analysis; they are conservative round numbers aligned
# loosely with `audit_dashboard/hc_filter.js` display thresholds and
# `audit_trail/quality_gates.py::SMART_PICKS_MIN_SCORE_*` per-asset floors.
# Phase 3 (tools/hc_parity_test.py) will run this evaluator against the JS
# source of truth on the full 3,500-row closed window; any divergence will
# shift these thresholds to match JS. Until then, treat as placeholder.
#
# Minimal criteria:
#   * score >= 60
#   * trust_tier in {PROVEN, RELIABLE}
#   * confidence >= 0.70
#
# Grade split:
#   grade-a : score >= 70 AND trust_tier == PROVEN AND confidence >= 0.80
#   grade-b : otherwise meets the minimal criteria
#   None    : does not meet the minimal criteria
def evaluate_hc_tier(pick: dict) -> Optional[str]:
    if not isinstance(pick, dict):
        return None
    try:
        score = float(pick.get("score") or 0)
    except (TypeError, ValueError):
        score = 0.0
    try:
        conf = float(pick.get("confidence") or 0)
    except (TypeError, ValueError):
        conf = 0.0
    trust = str(pick.get("trust_tier") or "").upper().strip()

    if score < 60 or conf < 0.70 or trust not in {"PROVEN", "RELIABLE"}:
        return None

    if score >= 70 and trust == "PROVEN" and conf >= 0.80:
        return "grade-a"
    return "grade-b"
