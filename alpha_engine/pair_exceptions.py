"""
Pair-level exception carve-out registry (B19).

Allows specific (strategy, symbol, direction) combinations with verified
per-pair edge to bypass the strategy-level Smart Picks gate, which uses
strategy-wide stats that can understate pair-specific performance.

Acceptance criteria for a registry entry:
  - Wilson 95% lower bound on pair WR >= 60%
  - Pair sample size n >= 20 closed picks
  - Operator sign-off via code-change PR (never auto-written by a cron)

Default-OFF: set PAIR_EXCEPTION_CARVE_OUT_ENABLED=1 to enable.

To propose new entries: run `python tools/derive_pair_exceptions.py` weekly
to surface candidates from recent_closed data, then submit a doc-only PR
with the proposed registry addition.

Consensus deltas applied from B19 multi-AI feedback (2026-05-02):
  - Carve-out ONLY bypasses: score-floor, R:R floor, forward-WR floor
  - Carve-out NEVER bypasses: BANNED trust-tier, BLOCKED_SYMBOLS,
    is_strategy_blocked, SCALP-mode gate
"""

from __future__ import annotations

import os
from math import sqrt
from typing import Any, Dict, NamedTuple


class PairExceptionEntry(NamedTuple):
    strategy: str
    symbol: str
    direction: str          # "LONG" | "SHORT" | "BUY" | "SELL"
    n: int
    wr_pct: float           # point-estimate WR %
    wilson_lb_pct: float    # Wilson 95% lower bound %
    verified_date: str      # ISO date string (YYYY-MM-DD)


def _wilson_lower_bound(wins: int, n: int, z: float = 1.96) -> float:
    """Wilson 95% lower bound on a proportion."""
    if n <= 0:
        return 0.0
    p = wins / n
    lb = (p + z * z / (2 * n) - z * sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (
        1 + z * z / n
    )
    return round(lb * 100, 1)


# ── Registry ─────────────────────────────────────────────────────────────────
# Each entry must meet: Wilson lb >= 60% AND n >= 20.
# New entries require a code-change PR (NOT auto-written by cron).
# Format: PairExceptionEntry(strategy, symbol, direction, n, wr_pct, wilson_lb_pct, verified_date)

PAIR_EXCEPTIONS: tuple[PairExceptionEntry, ...] = (
    PairExceptionEntry(
        strategy="atr_percentile_gate",
        symbol="BTCUSDT",
        direction="LONG",
        n=25,
        wr_pct=84.0,
        wilson_lb_pct=65.3,
        verified_date="2026-04-30",
    ),
)

# Internal lookup set for O(1) checks: (strategy_lower, symbol_upper, direction_upper)
_REGISTRY_LOOKUP: frozenset[tuple[str, str, str]] = frozenset(
    (e.strategy.lower(), e.symbol.upper(), e.direction.upper())
    for e in PAIR_EXCEPTIONS
)


def is_pair_exception(pick: Dict[str, Any]) -> bool:
    """Return True if this pick matches a registry entry.

    Does NOT check the PAIR_EXCEPTION_CARVE_OUT_ENABLED flag — callers
    must gate on that before calling.
    """
    strategy = str(pick.get("strategy") or "").lower()
    symbol = str(pick.get("symbol") or "").upper()
    direction = str(pick.get("direction") or pick.get("signal_type") or "").upper()
    return (strategy, symbol, direction) in _REGISTRY_LOOKUP


def should_pair_exception_pass(pick: Dict[str, Any]) -> bool:
    """Return True when this pick should bypass score/R:R/WR gates.

    Conditions:
      1. PAIR_EXCEPTION_CARVE_OUT_ENABLED=1 (default OFF)
      2. pick matches a registry entry
    """
    if os.environ.get("PAIR_EXCEPTION_CARVE_OUT_ENABLED", "0") != "1":
        return False
    return is_pair_exception(pick)
