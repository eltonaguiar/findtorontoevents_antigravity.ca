"""Ledger-backed gate for the PROVEN trust badge.

Why this exists
---------------
The /audit dashboard wrote ``trust_tier`` from *name lookups*:
``cross_aggregation.system_trust_registry.get_tier(source_system)`` in the
generator (dashboard_generator.py) and a hand-written JS map in the frontend.
Neither re-reads the strategy's resolved rows, so a source that had one good
run keeps a PROVEN badge while its live ledger loses money.

2026-11-16 audit evidence (live payload):
  * 97 of 97 PROVEN rows came from ``ml_bg_system_f`` (registry alias
    ``claws_of_doom``), whose own ledger is WR 20.6% / PF 0.31.
  * ``extreme_fear`` alone: 52 rows, WR 9.6%, PF 0.12, -224.0% total.
  * 21 of the 26 frontend registry names have no resolved rows at all.

Rule enforced here — the definition the dashboard itself publishes:
    PROVEN requires n >= 20 resolved rows, WR >= 50%, PF >= 1.5.
Anything that cannot be verified against those numbers is demoted one tier
(PROVEN -> WATCH when n >= 5, else MONITOR) with a machine-readable reason.

The module is intentionally pick-field based: the generator enriches picks
after ``stamp_pick_quality.py`` has computed ``strat_fwd_wr`` /
``strat_fwd_trades`` / ``strat_fwd_pf`` from closed-pick history, so the gate
needs no extra file I/O and no lookahead at generation time.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Tuple

PROVEN_MIN_N = 20
PROVEN_MIN_WR = 50.0
PROVEN_MIN_PF = 1.5

#: Tiers that represent a resolved (settled) outcome.
RESOLVED_STATUSES = frozenset({"WON", "LOST", "CLOSED", "TP_HIT", "SL_HIT"})

_MIN_ABS_PNL = 0.01


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_wr_pct(value: Any) -> Optional[float]:
    """Accept both 0-1 fractions and 0-100 percentages."""
    raw = _float(value, default=float("nan"))
    if raw != raw:  # NaN
        return None
    return raw * 100.0 if abs(raw) <= 1.0 else raw


def ledger_stats(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Return n / WR / PF for resolved rows that carry a non-flat pnl_pct."""
    wins: list[float] = []
    losses: list[float] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("status", "")).upper() not in RESOLVED_STATUSES:
            continue
        pnl = _float(row.get("pnl_pct"), default=0.0)
        if abs(pnl) <= _MIN_ABS_PNL:
            continue
        (wins if pnl > 0 else losses).append(pnl)
    n = len(wins) + len(losses)
    gross_win = sum(wins)
    gross_loss = sum(losses)
    return {
        "n": n,
        "wins": len(wins),
        "losses": len(losses),
        "wr": (len(wins) / n * 100.0) if n else 0.0,
        "pf": (gross_win / abs(gross_loss)) if gross_loss < 0 else None,
        "total_pnl_pct": gross_win + gross_loss,
    }


def stats_from_pick(pick: Dict[str, Any]) -> Dict[str, Any]:
    """Read the strategy-level forward stats stamped onto a pick."""
    n = int(_float(pick.get("strat_fwd_trades"), default=0.0))
    wr = _normalize_wr_pct(pick.get("strat_fwd_wr"))
    pf = _float(pick.get("strat_fwd_pf"), default=float("nan"))
    if pf != pf:  # NaN -> unknown
        pf = None
    return {"n": n, "wr": wr, "pf": pf, "source": "pick.strat_fwd_*"}


def proven_eligibility(stats: Dict[str, Any]) -> Tuple[bool, str]:
    """Apply the published PROVEN rule to ledger stats."""
    n = int(stats.get("n") or 0)
    wr = stats.get("wr")
    pf = stats.get("pf")
    reason_bits = [
        "n=%d/%d" % (n, PROVEN_MIN_N),
        "wr=%s/%s" % ("n/a" if wr is None else "%.1f" % wr, PROVEN_MIN_WR),
        "pf=%s/%s" % ("n/a" if pf is None else "%.2f" % pf, PROVEN_MIN_PF),
    ]
    if n < PROVEN_MIN_N:
        return False, "insufficient_sample:" + ",".join(reason_bits)
    if wr is None:
        return False, "wr_unknown:" + ",".join(reason_bits)
    if wr < PROVEN_MIN_WR:
        return False, "wr_below_floor:" + ",".join(reason_bits)
    if pf is None:
        return False, "pf_unknown:" + ",".join(reason_bits)
    if pf < PROVEN_MIN_PF:
        return False, "pf_below_floor:" + ",".join(reason_bits)
    return True, "ok:" + ",".join(reason_bits)


def check_pick_proven(
    pick: Dict[str, Any], stats: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str, Dict[str, Any]]:
    """Decide whether ``pick`` may keep a PROVEN badge.

    ``stats`` may be supplied by a caller that has already aggregated the
    closed ledger (preferred). Otherwise the stamped ``strat_fwd_*`` fields on
    the pick are used, and a pick with no usable stats is treated as
    unverifiable -> not eligible.
    """
    resolved_stats = stats if stats is not None else stats_from_pick(pick)
    if not resolved_stats or int(resolved_stats.get("n") or 0) == 0:
        return False, "unverifiable:no_strategy_stats", resolved_stats or {}
    eligible, reason = proven_eligibility(resolved_stats)
    return eligible, reason, resolved_stats


def demoted_tier(stats: Dict[str, Any]) -> str:
    """Fallback tier for a PROVEN pick that fails verification."""
    return "WATCH" if int(stats.get("n") or 0) >= 5 else "MONITOR"
