"""Ledger-backed `forward_validated` decision.

Why this exists
---------------
`forward_validated` was set by individual emitters: some compute it from their
own closed history, several hardcode ``False`` (inverse mutations, DNA mutator,
academic emitters, ...), and the dashboard only fills it in a narrow branch
(``n>=5 and WR>=45``). On the 2026-11-16 payload only 11 of 789 active picks
carried the flag, while 38 active picks had a strategy with 20+ resolved rows —
the evidence existed but was never consulted.

This module separates two ideas that were being conflated:

* **forward-validated** — the strategy has a real forward sample that is not a
  loser: ``n >= 20``, ``WR >= 45%``, ``PF >= 1.0``. This is the gate Smart
  Picks uses.
* **PROVEN** — stricter (``n >= 20``, ``WR >= 50%``, ``PF >= 1.5``), handled by
  ``audit_trail/proven_gate.py``.

A strategy that clears forward validation but not PROVEN keeps its PROVEN
demotion; the two are deliberately different bars.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

FV_MIN_N = 20
FV_MIN_WR = 45.0
FV_MIN_PF = 1.0

_MIN_ABS_PNL = 0.01


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def evaluate(n: Any, wr_pct: Any, pf: Any) -> Tuple[bool, str]:
    """Decide forward validation from ledger stats.

    ``wr_pct`` is a percentage (45.0 = 45%). ``pf`` may be None (unknown), in
    which case validation cannot be granted.
    """
    n_i = int(_float(n, 0.0))
    wr = _float(wr_pct, 0.0) if wr_pct is not None else None
    pf_f: Optional[float] = None if pf is None else _float(pf)
    bits = "n=%d/%d,wr=%s/%s,pf=%s/%s" % (
        n_i,
        FV_MIN_N,
        "n/a" if wr is None else "%.1f" % wr,
        FV_MIN_WR,
        "n/a" if pf_f is None else "%.2f" % pf_f,
        FV_MIN_PF,
    )
    if n_i < FV_MIN_N:
        return False, "insufficient_sample:" + bits
    if wr is None or wr < FV_MIN_WR:
        return False, "wr_below_floor:" + bits
    if pf_f is None:
        return False, "pf_unknown:" + bits
    if pf_f < FV_MIN_PF:
        return False, "pf_below_floor:" + bits
    return True, "ok:" + bits


def ledger_stats(pnls) -> Dict[str, Any]:
    """Aggregate resolved per-trade percentages into n / WR% / PF."""
    wins, losses = [], []
    for value in pnls or []:
        v = _float(value, 0.0)
        if abs(v) <= _MIN_ABS_PNL:
            continue
        (wins if v > 0 else losses).append(v)
    n = len(wins) + len(losses)
    gross_loss = sum(losses)
    return {
        "n": n,
        "wins": len(wins),
        "losses": len(losses),
        "wr": (len(wins) / n * 100.0) if n else 0.0,
        "pf": (sum(wins) / abs(gross_loss)) if gross_loss < 0 else None,
    }


def apply_ledger_validation(
    pick: Dict[str, Any], stats: Dict[str, Any]
) -> Optional[str]:
    """Promote/demote ``pick['forward_validated']`` from ledger stats in place.

    Returns ``"promoted"``, ``"demoted"`` or ``None`` (no change). An emitter's
    ``True`` is only revoked when the ledger has enough rows to overrule it.
    """
    ok, reason = evaluate(stats.get("n"), stats.get("wr"), stats.get("pf"))
    current = pick.get("forward_validated")
    if ok and current is not True:
        pick["forward_validated"] = True
        pick["forward_validated_basis"] = "strategy_ledger"
        pick["forward_validation_reason"] = reason
        return "promoted"
    if not ok and current is True and int(_float(stats.get("n"), 0.0)) >= FV_MIN_N:
        pick["forward_validated"] = False
        pick["forward_validated_basis"] = "strategy_ledger"
        pick["forward_validation_reason"] = reason
        return "demoted"
    return None
