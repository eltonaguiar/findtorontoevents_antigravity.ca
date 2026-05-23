"""M-012: DSR score + verdict wired into per-strategy breakdown rows.

Pins three contracts:
1. Known strategy in anti_overfit_audit.json gets dsr_score + dsr_verdict stamped.
2. Unknown strategy fails open: dsr_score=None, dsr_verdict=None.
3. _load_dsr_audit() returns a dict with at least one strategy (file exists in repo).
"""
from __future__ import annotations

import pytest

from audit_trail.dashboard_generator import _build_strategy_breakdown, _load_dsr_audit


def _strat_bucket(*, wins=5, losses=5, flat=0, active=0, pnl=0.0):
    return {
        "active": active,
        "wins": wins,
        "losses": losses,
        "flat": flat,
        "total_pnl": pnl,
        "long_wins": wins,
        "long_losses": losses,
        "long_flat": flat,
        "short_wins": 0,
        "short_losses": 0,
        "short_flat": 0,
        "symbols": {},
        "last_ts": "",
        "pnl_series": [],
    }


def test_load_dsr_audit_nonempty():
    """anti_overfit_audit.json must be present and parseable."""
    audit = _load_dsr_audit()
    assert isinstance(audit, dict), "Expected dict from _load_dsr_audit()"
    assert len(audit) > 0, "DSR audit is empty — anti_overfit_audit.json missing or empty"


def test_known_strategy_stamped():
    """cot_positioning is in anti_overfit_audit.json; must get real dsr_score."""
    audit = _load_dsr_audit()
    if "cot_positioning" not in audit:
        pytest.skip("cot_positioning not in anti_overfit_audit.json — skip")
    strat_dict = {"cot_positioning": _strat_bucket(wins=90, losses=10, pnl=30.0)}
    rows = _build_strategy_breakdown(strat_dict)
    assert len(rows) == 1
    row = rows[0]
    assert row["dsr_score"] is not None, "Expected dsr_score for known strategy"
    assert row["dsr_verdict"] is not None, "Expected dsr_verdict for known strategy"
    assert isinstance(row["dsr_score"], (int, float)), "dsr_score must be numeric"
    assert 0.0 <= row["dsr_score"] <= 1.0, f"dsr_score out of [0,1]: {row['dsr_score']}"


def test_unknown_strategy_fails_open():
    """Strategy not in audit file → dsr_score=None, dsr_verdict=None (fail-open)."""
    strat_dict = {"__no_such_strategy_xyzzy__": _strat_bucket(wins=5, losses=5, pnl=0.0)}
    rows = _build_strategy_breakdown(strat_dict)
    assert len(rows) == 1
    row = rows[0]
    assert row["dsr_score"] is None, "Unknown strategy should fail open with None"
    assert row["dsr_verdict"] is None, "Unknown strategy should fail open with None"


def test_dsr_fields_present_on_all_rows():
    """Every strategy row must have dsr_score and dsr_verdict keys (even if None)."""
    strat_dict = {
        "strategy_a": _strat_bucket(wins=3, losses=7, pnl=-2.0),
        "strategy_b": _strat_bucket(wins=8, losses=2, pnl=5.0),
    }
    rows = _build_strategy_breakdown(strat_dict)
    for row in rows:
        assert "dsr_score" in row, f"dsr_score missing from row: {row['name']}"
        assert "dsr_verdict" in row, f"dsr_verdict missing from row: {row['name']}"
