"""
Book-Level Direction-Conflict Reconciler
========================================

Pure-function reconciler that removes *delta-cancelling* opposing-direction
pick pairs from the active book.

Context
-------
Verified finding ``reports/opposing_legs_finding_2026-05-18.md``: 5/30 distinct
active crypto symbols carried BOTH a long-side and a short-side pick at
near-identical entry prices, emitted independently by different strategies
with no book-level arbiter. Holding both sides of the same instrument is not a
hedge — it is two strategies disagreeing while the book pays fees + half-spread
on both legs for ~0 net directional alpha.

This module is the missing book-level arbiter. It is a HYGIENE fix, NOT an
edge claim: it does not change the EDGE_HUNT_CONCLUSION no-edge verdict, it
only stops the book from paying costs to hold both sides of a non-edge.

Distinction from existing logic
-------------------------------
- ``audit_trail/quality_gates.py`` ``opposing`` logic (~line 3006) is
  TIMEFRAME-level — within a single pick's multi-timeframe analysis. It does
  NOT look across the book.
- ``audit_trail/direction_conflict_resolver.py`` is the trust-registry-weighted
  resolver; it depends on ``cross_aggregation.system_trust_registry`` and uses
  a different (trust-ratio) decision rule. This module is intentionally
  standalone, dependency-free, and uses a pure conviction-sum rule with an
  explicit tie band, matching the spec in the finding's "Recommended fix".

Design
------
- Pure function: no I/O, no env reads, no logging at import time.
- Never mutates the input list or its dicts.
- Conservative: when a side wins, only the *losing* side is dropped; when the
  two sides are within the tie band the conflict is treated as no-edge and
  BOTH sides are dropped.
- Non-conflicted symbols pass through untouched.

The env-gated wiring (shadow-first, default OFF) lives in the caller; see
``alpha_engine/scanner.py`` active-book export block.
"""
from __future__ import annotations

import os
from collections import defaultdict
from typing import Any, Dict, List, Tuple

__all__ = ["reconcile_direction_conflicts", "DEFAULT_TIE_BAND"]

# Default absolute conviction-gap below which a conflict is treated as a tie
# (= no edge) and BOTH sides are dropped. Override via env CONFLICT_TIE_BAND.
DEFAULT_TIE_BAND: float = 0.10

# Score fields tried, in priority order, when computing per-pick conviction.
_CONVICTION_FIELDS: Tuple[str, ...] = (
    "confidence",
    "elite_score",
    "method_a_score",
)

_LONG_DIRECTIONS = {"LONG", "BUY"}
_SHORT_DIRECTIONS = {"SHORT", "SELL"}


def _tie_band() -> float:
    """Return the tie band, honoring the CONFLICT_TIE_BAND env override.

    Falls back to :data:`DEFAULT_TIE_BAND` on any parse error or non-positive
    value. Reading the env *inside* the function (not at import) keeps the
    module import-time side-effect free.
    """
    raw = os.environ.get("CONFLICT_TIE_BAND")
    if raw is None or str(raw).strip() == "":
        return DEFAULT_TIE_BAND
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return DEFAULT_TIE_BAND
    if val < 0:
        return DEFAULT_TIE_BAND
    return val


def _norm_symbol(sym: Any) -> str:
    """Normalize a symbol for grouping (uppercase, strip hyphens, USD->USDT)."""
    s = str(sym or "").upper().strip()
    if not s:
        return ""
    if "-" in s:
        s = s.replace("-", "")
    if s.endswith("USD") and not s.endswith("USDT"):
        s = s + "T"
    return s


def _side(pick: Dict[str, Any]) -> str:
    """Return 'LONG', 'SHORT', or '' for a pick based on its direction field."""
    d = str(pick.get("direction") or "").upper().strip()
    if d in _LONG_DIRECTIONS:
        return "LONG"
    if d in _SHORT_DIRECTIONS:
        return "SHORT"
    # Fall back to signal_type when direction is absent/ambiguous.
    st = str(pick.get("signal_type") or "").upper().strip()
    if st in _LONG_DIRECTIONS:
        return "LONG"
    if st in _SHORT_DIRECTIONS:
        return "SHORT"
    return ""


def _conviction(pick: Dict[str, Any]) -> float:
    """Best-available conviction for a single pick.

    Tries ``confidence``, then ``elite_score``, then ``method_a_score``.
    Returns 0.0 when none are present or parseable. Note that ``confidence``
    is typically 0..1 while ``elite_score`` is 0..100 — the reconciler only
    ever *compares* sums of the same instrument's picks, so as long as the
    field choice is consistent within a symbol the comparison is meaningful.
    The tie band default (0.10) is calibrated to the ``confidence`` scale.
    """
    for field in _CONVICTION_FIELDS:
        v = pick.get(field)
        if v is None:
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return 0.0


def reconcile_direction_conflicts(
    picks: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Reconcile book-level opposing-direction conflicts.

    A symbol is *conflicted* when the active book holds at least one long-side
    pick (direction/​signal_type in LONG/BUY) AND at least one short-side pick
    (SHORT/SELL) for that symbol.

    For each conflicted symbol:

    * Compute an aggregate conviction per side as the **sum** of each pick's
      conviction (``confidence``, falling back to ``elite_score`` then
      ``method_a_score``).
    * If the absolute gap between the two side-sums is **<= the tie band**
      (default 0.10, env ``CONFLICT_TIE_BAND``), the conflict is treated as
      *no edge* and **both** sides are dropped.
    * Otherwise, the **higher-conviction** side is kept and the lower side is
      dropped.

    Non-conflicted symbols (single direction, or picks with no resolvable
    direction) pass through into ``kept`` untouched.

    This function is pure: it never mutates ``picks`` or any contained dict,
    and performs no I/O beyond reading the ``CONFLICT_TIE_BAND`` env var.

    Parameters
    ----------
    picks:
        The active book — a list of pick dicts.

    Returns
    -------
    (kept, dropped):
        Two new lists. ``kept`` + ``dropped`` is a partition of ``picks``
        (every input pick appears in exactly one). Order within ``kept``
        follows the input order.
    """
    if not picks:
        return [], []

    band = _tie_band()

    # Group picks by normalized symbol, tracking side sums and membership.
    by_symbol: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "LONG": [],  # list of input-list indices
            "SHORT": [],
            "long_sum": 0.0,
            "short_sum": 0.0,
        }
    )
    for idx, pick in enumerate(picks):
        if not isinstance(pick, dict):
            # Unparseable row — treat as non-conflicting passthrough.
            continue
        sym = _norm_symbol(pick.get("symbol"))
        side = _side(pick)
        if not sym or not side:
            continue
        bucket = by_symbol[sym]
        bucket[side].append(idx)
        if side == "LONG":
            bucket["long_sum"] += _conviction(pick)
        else:
            bucket["short_sum"] += _conviction(pick)

    # Determine which indices to drop.
    drop_indices: set[int] = set()
    for sym, bucket in by_symbol.items():
        longs: List[int] = bucket["LONG"]
        shorts: List[int] = bucket["SHORT"]
        if not longs or not shorts:
            continue  # not conflicted
        gap = abs(bucket["long_sum"] - bucket["short_sum"])
        if gap <= band:
            # Tie -> conflict is no-edge -> drop BOTH sides.
            drop_indices.update(longs)
            drop_indices.update(shorts)
        elif bucket["long_sum"] > bucket["short_sum"]:
            drop_indices.update(shorts)
        else:
            drop_indices.update(longs)

    if not drop_indices:
        return list(picks), []

    kept: List[Dict[str, Any]] = []
    dropped: List[Dict[str, Any]] = []
    for idx, pick in enumerate(picks):
        if idx in drop_indices:
            dropped.append(pick)
        else:
            kept.append(pick)
    return kept, dropped


def summarize(dropped: List[Dict[str, Any]]) -> str:
    """Human-readable one-line summary of a ``dropped`` list (for shadow logs)."""
    if not dropped:
        return "0 picks dropped (no direction conflicts)"
    by_sym: Dict[str, int] = defaultdict(int)
    for p in dropped:
        if isinstance(p, dict):
            by_sym[_norm_symbol(p.get("symbol")) or "?"] += 1
    parts = ", ".join(f"{s}x{n}" for s, n in sorted(by_sym.items()))
    return f"{len(dropped)} picks dropped across {len(by_sym)} symbol(s): {parts}"
