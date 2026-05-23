"""
Direction Conflict Resolver
============================

Standalone module that detects and suppresses conflicting LONG+SHORT picks
on the same symbol using trust-weighted voting via system_trust_registry.

Designed to be wired into dashboard_generator.py (or quality_gates.py) after
`final_active_picks` is built and BEFORE the payload is published. Does not
modify any existing file — can be adopted incrementally.

Context
-------
As of 2026-04-04 the audit dashboard payload had 7 symbols with simultaneous
LONG+SHORT picks wasting capital through self-hedging:
  BTCUSDT  10L /  2S
  AVAXUSDT  7L /  2S
  BNBUSDT   7L /  1S
  XRPUSDT   7L /  3S
  DOGEUSDT  5L /  2S
  SOLUSDT   8L /  3S
  ADAUSDT   4L /  2S

The existing `_detect_conflicts()` in dashboard_generator.py only *tags*
these cosmetically (_direction_conflict flag). This module actually filters.

Usage
-----
    from audit_trail.direction_conflict_resolver import (
        detect_pick_conflicts,
        filter_direction_conflicts,
    )

    # Inspect conflicts (no side effects)
    conflicts = detect_pick_conflicts(active_picks)
    for sym, info in conflicts.items():
        log.info("Conflict on %s: %s", sym, info["decision"])

    # Apply filtering (returns new list with minority-direction picks removed)
    filtered = filter_direction_conflicts(active_picks, strategy="trust_weighted")

Strategies
----------
- "trust_weighted" (default): use system_trust_registry.resolve_conflict()
  to pick the winning direction; suppress the losing side. CONTESTED splits
  (within 1.5x trust ratio) keep BOTH sides (no-op).
- "score_weighted": sum `score` field per direction, keep higher side.
- "kill_both": aggressively remove all picks on conflicted symbols.
- "majority": keep direction with more picks.

All strategies return a new list — never mutate input.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable, Literal

try:
    from cross_aggregation.system_trust_registry import resolve_conflict as _trust_resolve_conflict
    _TRUST_AVAILABLE = True
except Exception:
    _TRUST_AVAILABLE = False

    def _trust_resolve_conflict(long_systems, short_systems):
        # Fallback: pick side with more systems
        if len(long_systems) > len(short_systems):
            return ("LONG", "majority fallback (trust_registry unavailable)", 0.0)
        elif len(short_systems) > len(long_systems):
            return ("SHORT", "majority fallback (trust_registry unavailable)", 0.0)
        return ("CONTESTED", "tie fallback", 0.0)


Strategy = Literal["trust_weighted", "score_weighted", "kill_both", "majority"]


def _norm_symbol(sym: Any) -> str:
    """Normalize symbol for comparison (uppercase, strip hyphens -> USDT form)."""
    s = str(sym or "").upper().strip()
    if not s:
        return ""
    # Normalize SOL-USD -> SOLUSDT (same convention as dashboard_generator._normalize_symbol)
    if "-" in s:
        s = s.replace("-", "")
    if s.endswith("USD") and not s.endswith("USDT"):
        s = s + "T"
    return s


def _norm_direction(pick: dict) -> str:
    d = str(pick.get("direction") or "").upper().strip()
    if d in ("LONG", "BUY"):
        return "LONG"
    if d in ("SHORT", "SELL"):
        return "SHORT"
    return ""


def _pick_score(pick: dict) -> float:
    """Best available score for ranking (prefers score, falls back to elite_score)."""
    for k in ("score", "elite_score", "ml_composite_score"):
        v = pick.get(k)
        if v is None:
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return 0.0


def detect_pick_conflicts(picks: Iterable[dict]) -> dict[str, dict]:
    """
    Identify symbols with both LONG and SHORT picks.

    Returns
    -------
    dict mapping normalized_symbol -> {
        "long_picks": list[dict],
        "short_picks": list[dict],
        "long_systems": list[str],
        "short_systems": list[str],
        "long_score_sum": float,
        "short_score_sum": float,
        "decision": str,           # LONG | SHORT | CONTESTED | SKIP
        "decision_reason": str,
        "confidence_delta": float,
    }
    """
    groups: dict[str, dict[str, list[dict]]] = defaultdict(lambda: {"LONG": [], "SHORT": []})
    for p in picks:
        sym = _norm_symbol(p.get("symbol"))
        d = _norm_direction(p)
        if sym and d:
            groups[sym][d].append(p)

    conflicts: dict[str, dict] = {}
    for sym, by_dir in groups.items():
        longs = by_dir["LONG"]
        shorts = by_dir["SHORT"]
        if not longs or not shorts:
            continue  # no conflict — single direction only

        long_systems = [str(p.get("source_system") or p.get("source") or "") for p in longs]
        short_systems = [str(p.get("source_system") or p.get("source") or "") for p in shorts]
        long_score_sum = sum(_pick_score(p) for p in longs)
        short_score_sum = sum(_pick_score(p) for p in shorts)

        decision, reason, conf_delta = _trust_resolve_conflict(long_systems, short_systems)

        conflicts[sym] = {
            "long_picks": longs,
            "short_picks": shorts,
            "long_systems": long_systems,
            "short_systems": short_systems,
            "long_score_sum": long_score_sum,
            "short_score_sum": short_score_sum,
            "decision": decision,
            "decision_reason": reason,
            "confidence_delta": conf_delta,
        }
    return conflicts


def filter_direction_conflicts(
    picks: list[dict],
    strategy: Strategy = "trust_weighted",
    tag_survivors: bool = True,
) -> list[dict]:
    """
    Return a new list with minority-direction picks removed on conflicted symbols.

    Parameters
    ----------
    picks : list[dict]
        Active picks to filter.
    strategy : Strategy
        "trust_weighted" - use trust registry (default, safest)
        "score_weighted" - sum pick scores per direction
        "kill_both"      - remove all picks on conflicted symbols
        "majority"       - keep direction with more picks
    tag_survivors : bool
        If True, add `_conflict_resolved=True` + `_conflict_winner=<direction>`
        to kept picks on conflicted symbols (for audit transparency).

    Returns
    -------
    list[dict] : new list, never mutates input.
    """
    if not picks:
        return list(picks)

    conflicts = detect_pick_conflicts(picks)
    if not conflicts:
        return list(picks)

    # Decide winning direction per conflict symbol based on strategy
    # winners[symbol] = "LONG" | "SHORT" | "BOTH" (keep all) | "NONE" (kill all)
    winners: dict[str, str] = {}
    for sym, info in conflicts.items():
        if strategy == "trust_weighted":
            d = info["decision"]
            if d == "LONG":
                winners[sym] = "LONG"
            elif d == "SHORT":
                winners[sym] = "SHORT"
            else:  # CONTESTED or SKIP — keep both (don't arbitrate low-confidence)
                winners[sym] = "BOTH"
        elif strategy == "score_weighted":
            if info["long_score_sum"] > info["short_score_sum"] * 1.5:
                winners[sym] = "LONG"
            elif info["short_score_sum"] > info["long_score_sum"] * 1.5:
                winners[sym] = "SHORT"
            else:
                winners[sym] = "BOTH"
        elif strategy == "kill_both":
            winners[sym] = "NONE"
        elif strategy == "majority":
            ln, sn = len(info["long_picks"]), len(info["short_picks"])
            if ln > sn:
                winners[sym] = "LONG"
            elif sn > ln:
                winners[sym] = "SHORT"
            else:
                winners[sym] = "BOTH"
        else:
            raise ValueError(f"Unknown strategy: {strategy!r}")

    # Filter
    out: list[dict] = []
    for p in picks:
        sym = _norm_symbol(p.get("symbol"))
        if sym not in winners:
            out.append(p)
            continue
        w = winners[sym]
        if w == "BOTH":
            out.append(p)
            continue
        if w == "NONE":
            continue  # drop
        d = _norm_direction(p)
        if d == w:
            if tag_survivors:
                p = dict(p)  # copy to avoid mutation
                p["_conflict_resolved"] = True
                p["_conflict_winner"] = w
                p["_conflict_reason"] = conflicts[sym]["decision_reason"]
            out.append(p)
        # else: drop (minority direction on conflicted symbol)
    return out


def conflict_summary(picks: Iterable[dict]) -> str:
    """Return a human-readable summary of current conflicts."""
    conflicts = detect_pick_conflicts(picks)
    if not conflicts:
        return "No direction conflicts detected."
    lines = [f"Direction conflicts on {len(conflicts)} symbol(s):"]
    for sym, info in sorted(conflicts.items()):
        nl, ns = len(info["long_picks"]), len(info["short_picks"])
        lines.append(
            f"  {sym}: {nl}L / {ns}S -> {info['decision']} ({info['decision_reason']})"
        )
    return "\n".join(lines)
