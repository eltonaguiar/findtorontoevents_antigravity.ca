"""Charter §7 cross-class risk-budget allocator (P0.5-6).

Companion to charter_position_sizer.py. The sizer caps INDIVIDUAL picks
(5% / 1% per Charter §7); this module caps TOTAL EXPOSURE per asset class so
the portfolio doesn't end up 90% CRYPTO when CRYPTO is the only class
generating high-confidence signals.

Pure functions, no I/O at import. Opt-in sidecar — see ## Wiring Plan in
the merge PR. Production wire-up planned after a 2-week observation window
validates the default caps don't over-reject in practice.

Spec: identified by external swarm (GPT-OSS-120B) as P0.5-6 — the missing
piece in the Charter §7 sizing stack:
  - charter_position_sizer.py: per-pick caps (PR #976)
  - charter_slippage.py: cost discounting (PR #975)
  - charter_drift_circuit_breaker.py: WR-collapse kill-switch (PR #977)
  - charter_risk_budget.py: cross-class exposure caps (THIS MODULE)

Defaults are conservative and informed by Charter §5 current standing:
- CRYPTO 25% (Below-Tier-3 today, do not over-allocate)
- EQUITY 40% (Tier-2 candidate, best WR currently)
- ETF 30%, BOND 25%, COMMODITY 20%, FUTURES 20%, FOREX 15%
Sum is 175% intentionally — class caps are independent ceilings, not a
budget allocation. Total portfolio exposure is still bounded by sum of
approved pick notionals.
"""

from __future__ import annotations

from typing import Any


DEFAULT_CLASS_CAPS: dict[str, float] = {
    "CRYPTO": 0.25,
    "EQUITY": 0.40,
    "ETF": 0.30,
    "BOND": 0.25,
    "COMMODITY": 0.20,
    "FUTURES": 0.20,
    "FOREX": 0.15,
}

# Fallback cap for any asset class not in DEFAULT_CLASS_CAPS.
UNKNOWN_CLASS_CAP: float = 0.10


def _pick_notional_pct(pick: dict) -> float:
    """Read the per-pick notional fraction stamped by charter_position_sizer.
    Returns 0.0 if missing so unstamped picks don't consume budget."""
    v = pick.get("_charter_notional_pct")
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _pick_class(pick: dict) -> str:
    return str(pick.get("asset_class", "") or "").upper()


def _pick_sort_key(pick: dict) -> float:
    """Greedy ordering: accept highest-confidence picks first within each
    class budget. Falls back to notional_pct if confidence missing."""
    try:
        c = float(pick.get("confidence", 0) or 0)
    except (TypeError, ValueError):
        c = 0.0
    return c


def allocate_picks(
    candidates: list[dict],
    *,
    class_caps: dict[str, float] | None = None,
    unknown_class_cap: float = UNKNOWN_CLASS_CAP,
) -> tuple[list[dict], list[tuple[dict, str]]]:
    """Approve picks greedily within per-class notional caps.

    Args:
        candidates: list of pick dicts. Each should have `_charter_notional_pct`
            (stamped by charter_position_sizer) and `asset_class`. Picks
            without `_charter_notional_pct` are passed through with reason
            "no_size_stamp" (caller decides whether to drop or default).
        class_caps: mapping of uppercase class -> max fraction of equity.
            Defaults to DEFAULT_CLASS_CAPS.
        unknown_class_cap: cap applied to classes not in class_caps.

    Returns:
        (approved, rejected) where rejected is a list of (pick, reason) tuples.
    """
    caps = dict(DEFAULT_CLASS_CAPS) if class_caps is None else dict(class_caps)
    # Sort high-confidence first so the cap is filled by the strongest signals.
    ranked = sorted(candidates, key=_pick_sort_key, reverse=True)
    consumed: dict[str, float] = {}
    approved: list[dict] = []
    rejected: list[tuple[dict, str]] = []
    for p in ranked:
        notional = _pick_notional_pct(p)
        if notional <= 0:
            rejected.append((p, "no_size_stamp"))
            continue
        cls = _pick_class(p)
        cap = caps.get(cls, unknown_class_cap)
        used = consumed.get(cls, 0.0)
        if used + notional > cap + 1e-9:
            rejected.append((
                p,
                f"class_cap_exceeded {cls} used={used:.3f}+{notional:.3f}>{cap:.3f}",
            ))
            continue
        consumed[cls] = used + notional
        approved.append(p)
    return approved, rejected


def summarize_allocation(
    approved: list[dict],
    rejected: list[tuple[dict, str]],
) -> dict[str, Any]:
    """Build a compact summary for /audit dashboard consumption."""
    by_class: dict[str, dict[str, float]] = {}
    for p in approved:
        cls = _pick_class(p)
        slot = by_class.setdefault(cls, {"approved_n": 0, "approved_notional": 0.0})
        slot["approved_n"] += 1
        slot["approved_notional"] += _pick_notional_pct(p)
    return {
        "approved_n": len(approved),
        "rejected_n": len(rejected),
        "by_class": by_class,
    }
