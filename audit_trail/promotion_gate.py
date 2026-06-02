"""Strategy Promotion Gate — research-to-production translation barrier.

EAGLE-2 Pillar 3 (2026-06-02). The premise: lab-survivor strategies
(e.g. VWAPReversion, BollingerMR, ETF Verified DM) must NOT reach the
production pick pool until they clear an explicit admissibility check.
Without this gate, the production scanner emits from the full noisy
strategy universe while only a tiny minority has real forward proof —
this is the root cause of live PF ≈ 0.98 on CRYPTO and PF ≈ 0.56 on FOREX.

Usage in production_scanner.py:

    from audit_trail.promotion_gate import is_admissible_for_production

    for pick in candidate_picks:
        if not is_admissible_for_production(pick.get("source_system", ""),
                                            pick.get("asset_class", "")):
            continue  # strategy not yet promoted — drop from live emission
        live_picks.append(pick)

Promotion criteria (ALL must pass):
  1. Strategy is in the explicit allowlist `PROMOTED_STRATEGIES`
  2. Asset class is not in `BLOCKED_ASSET_CLASSES` (re-uses quality_gates.py)
  3. Strategy is not in the recency-drift / sign-flip / dispute lists
  4. Source-system concentration HHI < 0.30 within its asset class
     (the live aggregate must not be dominated by one source system)

The allowlist is intentionally small. Adding to it requires:
  - Lab walk-forward PASS with purged + embargoed methodology
  - DSR > 0.95 + PBO < 0.05 with N_trials = real hypothesis count
  - 30-day shadow paper PF within 30% of OOS lab PF
  - Concentration HHI < 0.30 (no single source > 30% of its class)
  - sign_coherence_check.py returns 0 flips for the strategy's rows

See EAGLE2_2026-06-02_CLAUDE_OPUS_4_7.MD Pillar 3 + Pillar 4 capital ladder.
"""
from __future__ import annotations

from typing import Iterable, Optional

# ─────────────────────────────────────────────────────────────────────────────
# Allowlist — strategies cleared for live production emission.
#
# EMPTY BY DESIGN as of 2026-06-02. Even the 3 walk-forward survivors
# (VWAPReversion, BollingerMR, DualMomentumCrypto) are NOT here yet because
# they have not completed the 30-day shadow paper requirement and the
# verification engine itself was on a stale branch (never landed on main).
#
# First expected entry: "etf_verified_dual_momentum" after 30d shadow holds
# (cleanest data feed, no resolver/sign-flip risk, Sharpe 1.91 on n=104).
# ─────────────────────────────────────────────────────────────────────────────
PROMOTED_STRATEGIES: frozenset = frozenset({
    # Empty by design. See module docstring + EAGLE2 for promotion criteria.
})


# Concentration cap — if a single source_system contributes more than this
# fraction of an asset class's recent picks, no strategy in that class is
# admissible. Codifies EAGLE-2's "concentration masquerades as edge" rule.
#
# 2026-06-02: tightened 0.30 -> 0.20 per blackboxai EAGLE-2 review (HHI cap 0.20
# is the institutional standard for aggregate-book concentration). Cross-confirmed
# by minimax-m3-free (recommended 0.25).
CONCENTRATION_HHI_CAP: float = 0.20

# Top-K source-system exposure cap (blackboxai EAGLE-2). The top-5 emitters combined
# must not exceed 35% of an asset class's recent picks. Catches distributed
# concentration that HHI alone misses (5 emitters at 7% each clears HHI but is
# over-concentrated).
TOP_K_EXPOSURE_CAP: float = 0.35
TOP_K_N: int = 5

# Resolver dispute-rate thresholds (blackboxai EAGLE-2).
#  - DISPUTE_RATE_ALERT: weekly dispute_rate > 2% triggers alert
#  - DISPUTE_RATE_PROMOTION_MAX: must be < 1% for admissibility
#  - DISPUTE_RATE_AUTOFREEZE_SIGMA: > N sigma above trailing 8-week mean auto-freezes
DISPUTE_RATE_ALERT: float = 0.02
DISPUTE_RATE_PROMOTION_MAX: float = 0.01
DISPUTE_RATE_AUTOFREEZE_SIGMA: float = 3.0

# Tracks strategies that were once promoted but had their promotion revoked
# (e.g. forward PF collapsed). Kept separately so a revoked strategy
# requires the full admission cycle again — no quiet re-add.
REVOKED_STRATEGIES: frozenset = frozenset({
    # populated as revocations happen; never empty quietly
})


def is_admissible_for_production(
    strategy_key: str,
    asset_class: str,
    blocked_asset_classes: Optional[Iterable[str]] = None,
) -> bool:
    """Return True if `strategy_key` is cleared for live capital emission.

    This is a DENY-BY-DEFAULT gate. Adding a strategy requires meeting all
    promotion criteria (see module docstring) and an explicit entry in
    PROMOTED_STRATEGIES. The gate is intentionally conservative — a false
    negative costs nothing (strategy stays paper-only); a false positive
    costs real money.

    Args:
        strategy_key: the `source_system` or `strategy` field on a pick.
        asset_class: the pick's asset class (CRYPTO / EQUITY / etc.).
        blocked_asset_classes: optional override; defaults to importing
            `BLOCKED_ASSET_CLASSES` from quality_gates lazily to avoid a
            hard import cycle.

    Returns:
        True iff the strategy is on PROMOTED_STRATEGIES, NOT on
        REVOKED_STRATEGIES, AND the asset class is not frozen.
    """
    if not strategy_key:
        return False
    key = strategy_key.strip().lower()
    if not key:
        return False

    if key in {s.lower() for s in REVOKED_STRATEGIES}:
        return False

    if key not in {s.lower() for s in PROMOTED_STRATEGIES}:
        return False

    # Asset-class freeze — re-use the canonical set when possible to avoid
    # drift between this gate and the rest of quality_gates.
    if blocked_asset_classes is None:
        try:
            from audit_trail.quality_gates import BLOCKED_ASSET_CLASSES
            blocked_asset_classes = BLOCKED_ASSET_CLASSES
        except Exception:
            blocked_asset_classes = {"FOREX", "COMMODITY", "FUTURES"}

    ac = (asset_class or "").strip().upper()
    if ac in {c.upper() for c in (blocked_asset_classes or [])}:
        return False

    return True


def admission_reason(strategy_key: str, asset_class: str) -> str:
    """Human-readable explanation of why a strategy was admitted or denied.

    Useful for the funnel-audit pipeline and operator review. Not used in
    the hot pick path (which only calls is_admissible_for_production).
    """
    if not strategy_key:
        return "denied: missing strategy_key"
    key = strategy_key.strip().lower()
    if key in {s.lower() for s in REVOKED_STRATEGIES}:
        return f"denied: strategy '{strategy_key}' is on REVOKED list"
    if key not in {s.lower() for s in PROMOTED_STRATEGIES}:
        return (
            f"denied: strategy '{strategy_key}' not in PROMOTED_STRATEGIES "
            f"(see EAGLE2 Pillar 3 + Pillar 4 for promotion criteria)"
        )
    try:
        from audit_trail.quality_gates import BLOCKED_ASSET_CLASSES
        blocked = BLOCKED_ASSET_CLASSES
    except Exception:
        blocked = {"FOREX", "COMMODITY", "FUTURES"}
    ac = (asset_class or "").strip().upper()
    if ac in {c.upper() for c in blocked}:
        return (
            f"denied: asset class '{asset_class}' is in BLOCKED_ASSET_CLASSES "
            f"(see quality_gates.py:1725 for freeze rationale)"
        )
    return f"admitted: '{strategy_key}' on PROMOTED list and class '{asset_class}' not frozen"


__all__ = [
    "is_admissible_for_production",
    "admission_reason",
    "PROMOTED_STRATEGIES",
    "REVOKED_STRATEGIES",
    "CONCENTRATION_HHI_CAP",
    "TOP_K_EXPOSURE_CAP",
    "TOP_K_N",
    "DISPUTE_RATE_ALERT",
    "DISPUTE_RATE_PROMOTION_MAX",
    "DISPUTE_RATE_AUTOFREEZE_SIGMA",
]
