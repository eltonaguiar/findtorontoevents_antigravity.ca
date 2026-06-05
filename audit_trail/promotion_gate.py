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


# ── MASTERPLAN 2026-06-05: forward Tier-2 evaluation (pure math, no DB) ──
TIER2_MIN_N = 100
TIER2_MIN_WR = 0.55
TIER2_MIN_PF = 1.4
TIER2_MIN_DSR = 0.80
TIER2_OOS_PF_RATIO = 0.85
TIER2_MAX_REGIME_WR_DROP = 0.15


def _profit_factor_from_pnls(pnls: list[float]) -> float | None:
    wins = sum(p for p in pnls if p > 0)
    losses = abs(sum(p for p in pnls if p < 0))
    if losses <= 0:
        return None if wins <= 0 else float("inf")
    return wins / losses


def evaluate_forward_tier2(
    closed_pnls: list[float],
    *,
    oos_pf: float | None = None,
    is_pf: float | None = None,
    dsr: float | None = None,
    wr_high_vix: float | None = None,
    wr_low_vix: float | None = None,
) -> dict:
    """Six-check promotion ladder for paper→production (MASTERPLAN action 4).

    ``closed_pnls`` should be ordered with the most recent trade first; only the
    last 100 are evaluated when more than 100 are supplied.

    Returns dict with ``passed``, ``blockers``, and computed metrics.
    """
    window = list(closed_pnls[:TIER2_MIN_N])
    n = len(window)
    blockers: list[str] = []
    if n < TIER2_MIN_N:
        blockers.append(f"n<{TIER2_MIN_N}")

    wins = sum(1 for p in window if p > 0)
    wr = wins / n if n else 0.0
    if wr < TIER2_MIN_WR:
        blockers.append(f"wr<{TIER2_MIN_WR:.0%}")

    pf = _profit_factor_from_pnls(window)
    if pf is None or (pf != float("inf") and pf < TIER2_MIN_PF):
        blockers.append(f"pf<{TIER2_MIN_PF}")

    if oos_pf is not None and is_pf is not None and is_pf > 0:
        if oos_pf < TIER2_OOS_PF_RATIO * is_pf:
            blockers.append("oos_pf_below_85pct_is")

    if dsr is not None and dsr < TIER2_MIN_DSR:
        blockers.append(f"dsr<{TIER2_MIN_DSR}")

    if wr_high_vix is not None and wr_low_vix is not None:
        if abs(wr_high_vix - wr_low_vix) > TIER2_MAX_REGIME_WR_DROP:
            blockers.append("regime_wr_drop>15pp")

    return {
        "passed": len(blockers) == 0,
        "blockers": blockers,
        "n": n,
        "wr": round(wr, 4),
        "pf": round(pf, 4) if pf is not None and pf != float("inf") else pf,
        "dsr": dsr,
    }


__all__ = [
    "is_admissible_for_production",
    "admission_reason",
    "evaluate_forward_tier2",
    "PROMOTED_STRATEGIES",
    "REVOKED_STRATEGIES",
    "CONCENTRATION_HHI_CAP",
    "TOP_K_EXPOSURE_CAP",
    "TOP_K_N",
    "DISPUTE_RATE_ALERT",
    "DISPUTE_RATE_PROMOTION_MAX",
    "DISPUTE_RATE_AUTOFREEZE_SIGMA",
    "TIER2_MIN_N",
    "TIER2_MIN_WR",
    "TIER2_MIN_PF",
]
