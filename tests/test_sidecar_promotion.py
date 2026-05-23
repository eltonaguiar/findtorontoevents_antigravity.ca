"""Tests for `_compute_sidecar_promotion_status` (sidecar promotion tracker).

Covers the 4-state ladder (INCUBATING / BELOW_GATE / READY_TO_PROMOTE /
PROMOTED), ETA extrapolation, schema, and the empty-input contract.

Surfaced under /audit -> BtVsFwd tab.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from audit_trail.dashboard_generator import (
    _compute_sidecar_promotion_status,
    _SIDECAR_PROMOTION_GATES,
    _PROMOTED_SIDECARS,
)


_NOW = datetime.now(timezone.utc)
_EXPECTED_KEYS = {
    "n", "wr", "pf", "gate_n", "gate_wr", "gate_pf",
    "status", "days_since_first_trade", "eta_to_promotion_days",
}


def _pick(strategy: str, pnl_pct: float, days_ago: float = 1.0) -> dict:
    """Build a minimal closed-pick dict matching the function's expected shape."""
    ts = _NOW - timedelta(days=days_ago)
    return {
        "strategy": strategy,
        "pnl_pct": pnl_pct,
        "closed_at": ts.isoformat(),
    }


# ---------------------------------------------------------------------------
# 1. INCUBATING — n < gate_n; ETA must be a finite positive number.
# ---------------------------------------------------------------------------
def test_incubating_below_gate_n_with_eta():
    """commodity_cot_contrarian: gate_n=20. 5 trades over 5 days -> INCUBATING."""
    name = "commodity_cot_contrarian"
    closed = [_pick(name, 1.0, days_ago=5 - i) for i in range(5)]  # 1 trade/day, 5 days

    out = _compute_sidecar_promotion_status(closed)
    entry = out[name]

    assert entry["status"] == "INCUBATING"
    assert entry["n"] == 5
    assert entry["gate_n"] == 20
    # 5 trades / 5d pace = 1/day -> ETA = (20-5)/1 = 15 days
    assert entry["eta_to_promotion_days"] is not None
    assert entry["eta_to_promotion_days"] > 0
    assert entry["eta_to_promotion_days"] == pytest.approx(15.0, abs=2.0)


# ---------------------------------------------------------------------------
# 2. BELOW_GATE — n >= gate_n but WR / PF failing.
# ---------------------------------------------------------------------------
def test_below_gate_when_wr_fails():
    """commodity_cot_contrarian: gate_n=20, gate_wr=55. n=40 with WR 47.5% -> BELOW_GATE."""
    name = "commodity_cot_contrarian"
    # 40 picks: 19 wins (+1.0), 21 losses (-0.5) -> WR 47.5%, PF=(19/(21*0.5))=1.81
    # Fails wr gate (47.5 < 55) so should still be BELOW_GATE despite passing pf.
    closed = []
    for i in range(19):
        closed.append(_pick(name, 1.0, days_ago=10 - (i / 4.0)))
    for i in range(21):
        closed.append(_pick(name, -0.5, days_ago=10 - (i / 4.0)))

    out = _compute_sidecar_promotion_status(closed)
    entry = out[name]

    assert entry["n"] == 40
    assert entry["wr"] < 55.0
    assert entry["status"] == "BELOW_GATE"
    # ETA only set for INCUBATING.
    assert entry["eta_to_promotion_days"] is None


# ---------------------------------------------------------------------------
# 3. READY_TO_PROMOTE — passing all 3 gates.
# ---------------------------------------------------------------------------
def test_ready_to_promote_passing_all_gates():
    """commodity_cot_contrarian: gate (20, 55%, 1.5). 35 picks, 21 wins, PF~2.1."""
    name = "commodity_cot_contrarian"
    # 21 wins (+2.0), 14 losses (-1.0) -> WR=60%, PF=(21*2)/(14*1)=3.0
    closed = []
    for i in range(21):
        closed.append(_pick(name, 2.0, days_ago=10 - (i / 4.0)))
    for i in range(14):
        closed.append(_pick(name, -1.0, days_ago=10 - (i / 4.0)))

    out = _compute_sidecar_promotion_status(closed)
    entry = out[name]

    assert entry["n"] == 35
    assert entry["wr"] >= 55.0
    assert entry["pf"] >= 1.5
    assert entry["status"] == "READY_TO_PROMOTE"
    assert entry["eta_to_promotion_days"] is None  # already eligible


# ---------------------------------------------------------------------------
# 4. PROMOTED — strategy in hardcoded promoted-list overrides stats.
# ---------------------------------------------------------------------------
def test_promoted_status_sticky_regardless_of_stats():
    """sentiment_macro_contrarian is in _PROMOTED_SIDECARS; 1 awful trade -> still PROMOTED."""
    name = "sentiment_macro_contrarian"
    assert name in _PROMOTED_SIDECARS  # invariant guard

    closed = [_pick(name, -10.0, days_ago=1)]  # 1 catastrophic loss
    out = _compute_sidecar_promotion_status(closed)
    entry = out[name]

    assert entry["status"] == "PROMOTED"
    assert entry["n"] == 1
    # Even with empty closed_picks the status is still PROMOTED.
    out_empty = _compute_sidecar_promotion_status([])
    assert out_empty[name]["status"] == "PROMOTED"


# ---------------------------------------------------------------------------
# 5. Empty closed_picks — every sidecar present, n=0, status INCUBATING
#    unless in the promoted list.
# ---------------------------------------------------------------------------
def test_empty_input_returns_all_sidecars_in_baseline_state():
    out = _compute_sidecar_promotion_status([])

    # Every registered sidecar must appear.
    assert set(out.keys()) == set(_SIDECAR_PROMOTION_GATES.keys())

    for name, entry in out.items():
        assert entry["n"] == 0
        assert entry["wr"] == 0.0
        assert entry["pf"] == 0.0
        assert entry["days_since_first_trade"] == 0
        assert entry["eta_to_promotion_days"] is None  # no pace yet
        if name in _PROMOTED_SIDECARS:
            assert entry["status"] == "PROMOTED"
        else:
            assert entry["status"] == "INCUBATING"


# ---------------------------------------------------------------------------
# 6. Schema — every entry must contain all 9 expected keys.
# ---------------------------------------------------------------------------
def test_every_entry_has_full_schema():
    closed = [_pick("crypto_pairs_arb", 1.0, days_ago=1)]
    out = _compute_sidecar_promotion_status(closed)

    assert len(out) == len(_SIDECAR_PROMOTION_GATES)
    for name, entry in out.items():
        missing = _EXPECTED_KEYS - set(entry.keys())
        assert not missing, f"{name} missing keys: {missing}"
        # Type sanity.
        assert isinstance(entry["n"], int)
        assert isinstance(entry["wr"], float)
        assert isinstance(entry["pf"], float)
        assert isinstance(entry["status"], str)
        assert entry["status"] in {
            "INCUBATING", "BELOW_GATE", "READY_TO_PROMOTE", "PROMOTED",
        }
