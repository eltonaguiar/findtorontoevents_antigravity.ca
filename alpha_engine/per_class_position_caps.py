"""
Per-asset-class position caps + concurrent limits.

OPT-IN SIDECAR (Wire-Up Rule compliant): defines per-class config + helpers
but ships ZERO production callers. Caller wire-up follows in PR-B.

Rationale (CLAUDE.md Goal #1 charter):
- Universal 5% per-position cap + 30 concurrent limit applies regardless of
  asset class. Per the 2026-05-03 reviewer findings on PR #730:
    * BOND has 336h hold window (PR #730) — without per-class concurrent cap,
      stuck BOND picks tie up portfolio for 14 days each.
    * EQUITY meets T2 thresholds (PF 1.41, WR 52.7%, n=421); charter says
      "size up" — needs per-class max_position_pct uplift to act on the data.
    * MEME has 24h hold window — high turnover; needs lower per-class
      concurrent cap to prevent tail-risk concentration.

Defaults derived from per-asset volatility, hold window, and current Tier
status per `audit_dashboard/data/dashboard_data.json::asset_class_health`
(2026-05-03T00:06Z snapshot).

Usage (consumer):
    from alpha_engine.per_class_position_caps import (
        get_max_position_pct,
        get_max_concurrent,
        is_concurrent_cap_breached,
    )

    # In production_scanner / portfolio sizer:
    cap_pct = get_max_position_pct(pick.get("asset_class"))
    max_n = get_max_concurrent(pick.get("asset_class"))
    if is_concurrent_cap_breached(active_picks, pick.get("asset_class")):
        # reject new pick — class-cap reached
        return None

Rollback (each is independently env-toggleable):
    PER_CLASS_POSITION_PCT_DISABLED=1   → all classes use UNIVERSAL_POSITION_PCT
    PER_CLASS_CONCURRENT_DISABLED=1     → all classes use UNIVERSAL_MAX_CONCURRENT

References:
- PR #730 reviewer follow-up (BOND position cap)
- reports/ASSET_CLASS_RESCUE_STATE_2026_05_03_0510Z.md item #5
"""
from __future__ import annotations

import os
from typing import Iterable

# ---------------------------------------------------------------------------
# Defaults (universal fallback when per-class disabled or class unknown)
# ---------------------------------------------------------------------------
UNIVERSAL_POSITION_PCT: float = 0.05      # 5% — matches alpha_engine/backtest/portfolio.py default
UNIVERSAL_MAX_CONCURRENT: int = 30         # matches alpha_engine/backtest/engine.py default

# ---------------------------------------------------------------------------
# Per-class position size caps (% of portfolio per single position)
# ---------------------------------------------------------------------------
# Calibrated to per-asset-class Tier status + volatility profile:
#   - EQUITY: T2 candidate (PF 1.41 / WR 52.7%) → uplift to 8% per charter "size up"
#   - COMMODITY: meets T2 PF (1.78) → uplift to 7%
#   - BOND: T2 thresholds met but n<100 → conservative 4% pending more samples
#   - ETF: borderline T3 → 5% (universal)
#   - CRYPTO: sub-T2 system PF 1.25 → 5% (universal) until drag-cut completes
#   - MEME: high vol, fast decay → 2% (downsized)
#   - FOREX: sub-floor PF 0.27 → 3% (downsized while pip-as-percent fix pending)
#   - FUTURES: thin sample, leverage built-in → 3%
PER_CLASS_POSITION_PCT: dict[str, float] = {
    "CRYPTO":    0.05,
    "MEME":      0.02,    # high vol + fast decay
    "EQUITY":    0.08,    # T2 candidate — charter size-up
    "ETF":       0.05,    # borderline T3
    "COMMODITY": 0.07,    # meets T2 PF
    "FUTURES":   0.03,    # thin sample + leverage
    "FOREX":     0.03,    # sub-floor pending pip fix
    "BOND":      0.04,    # T2 thresholds met but n<100
}

# ---------------------------------------------------------------------------
# Per-class max concurrent live picks
# ---------------------------------------------------------------------------
# Calibrated to per-asset-class hold window (PR #730 MAX_HOLD_HOURS_BY_CLASS):
# Volume × duration must fit the universal 30-pick portfolio capacity. Longer
# hold windows demand smaller concurrent caps to prevent stuck-pick lock-up.
#   CRYPTO    48h hold  → 15 concurrent (high churn, big universe)
#   MEME      24h hold  → 5 concurrent (fast decay, tail-risk)
#   EQUITY    72h hold  → 8 concurrent
#   ETF      120h hold  → 6 concurrent
#   COMMODITY 168h hold → 5 concurrent
#   FUTURES  168h hold  → 4 concurrent (thin sample)
#   FOREX    120h hold  → 8 concurrent (16 majors universe)
#   BOND     336h hold  → 5 concurrent (14d hold = tie-up risk)
PER_CLASS_MAX_CONCURRENT: dict[str, int] = {
    "CRYPTO":    15,
    "MEME":      5,
    "EQUITY":    8,
    "ETF":       6,
    "COMMODITY": 5,
    "FUTURES":   4,
    "FOREX":     8,
    "BOND":      5,
}


def _normalize_class(asset_class: str | None) -> str:
    if not asset_class:
        return ""
    return str(asset_class).upper().strip()


def get_max_position_pct(asset_class: str | None) -> float:
    """Return the max position size (as fraction of portfolio) for an asset class.

    Falls back to UNIVERSAL_POSITION_PCT when the class is unknown or when
    PER_CLASS_POSITION_PCT_DISABLED env var is set.
    """
    if os.environ.get("PER_CLASS_POSITION_PCT_DISABLED", "0") == "1":
        return UNIVERSAL_POSITION_PCT
    ac = _normalize_class(asset_class)
    if not ac:
        return UNIVERSAL_POSITION_PCT
    return PER_CLASS_POSITION_PCT.get(ac, UNIVERSAL_POSITION_PCT)


def get_max_concurrent(asset_class: str | None) -> int:
    """Return the max simultaneous live picks for an asset class.

    Falls back to UNIVERSAL_MAX_CONCURRENT when the class is unknown or
    when PER_CLASS_CONCURRENT_DISABLED env var is set.
    """
    if os.environ.get("PER_CLASS_CONCURRENT_DISABLED", "0") == "1":
        return UNIVERSAL_MAX_CONCURRENT
    ac = _normalize_class(asset_class)
    if not ac:
        return UNIVERSAL_MAX_CONCURRENT
    return PER_CLASS_MAX_CONCURRENT.get(ac, UNIVERSAL_MAX_CONCURRENT)


def count_class_active(active_picks: Iterable[dict], asset_class: str | None) -> int:
    """Count current live picks for a given asset class (case-insensitive match)."""
    ac = _normalize_class(asset_class)
    if not ac:
        return 0
    n = 0
    for p in active_picks:
        p_ac = _normalize_class(p.get("asset_class") or p.get("category"))
        if p_ac == ac:
            n += 1
    return n


def is_concurrent_cap_breached(
    active_picks: Iterable[dict],
    asset_class: str | None,
) -> bool:
    """Return True if accepting a NEW pick of this class would breach the cap.

    Caller pattern:
        if is_concurrent_cap_breached(current_active, new_pick.asset_class):
            log.debug("Class cap breached for %s — pick rejected", asset_class)
            return None  # reject pick
    """
    ac = _normalize_class(asset_class)
    if not ac:
        return False  # no cap on unknown class — defer to universal limit upstream
    cap = get_max_concurrent(ac)
    current = count_class_active(active_picks, ac)
    return current >= cap
