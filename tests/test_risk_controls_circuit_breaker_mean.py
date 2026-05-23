"""
Regression tests for the circuit-breaker drawdown computation in
``alpha_engine/risk_controls.check_circuit_breaker``.

Pin the Issue #623 fix: drawdown is computed as the **mean** per-pick
``pnl_pct`` (* 100), not the **sum**. Mixed-unit pnl_pct outliers (where
the field was stored as a percentage like -2.5 instead of a fraction
-0.025) are clipped to [-1.0, 1.0] before averaging.

Without these guards, 966 closed picks with average pnl_pct of -0.186
produced a "drawdown" of -17,950% to -25,465% on Issue #623 — wildly
inflated, no portfolio meaning, and the breaker stayed locked in
EMERGENCY for 8+ days, taking the scanner offline.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from alpha_engine import risk_controls


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pick(pnl_pct: float | None, days_ago: int = 0,
               unrealized_pnl_pct: float | None = None) -> dict:
    """Build a closed-pick dict with ``exit_date`` ``days_ago`` from today."""
    exit_date = (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%d")
    pick = {"exit_date": exit_date}
    if pnl_pct is not None:
        pick["pnl_pct"] = pnl_pct
    if unrealized_pnl_pct is not None:
        pick["unrealized_pnl_pct"] = unrealized_pnl_pct
    return pick


@pytest.fixture(autouse=True)
def _isolate_state(tmp_path, monkeypatch):
    """Redirect risk_controls state files so tests don't touch production data."""
    monkeypatch.setattr(risk_controls, "CIRCUIT_BREAKER_PATH", tmp_path / "cb.json")
    monkeypatch.setattr(risk_controls, "DAILY_PNL_PATH", tmp_path / "daily.json")
    monkeypatch.setattr(risk_controls, "CONSECUTIVE_LOSS_PATH", tmp_path / "consec.json")
    yield


# ---------------------------------------------------------------------------
# The fix: mean, not sum
# ---------------------------------------------------------------------------


def test_drawdown_is_mean_not_sum_of_pnl_pct():
    """100 picks each at -2% (-0.02 fractional) should produce -2% drawdown,
    not -200% (the old sum*100 bug)."""
    closed = [_make_pick(-0.02, days_ago=2) for _ in range(100)]
    status = risk_controls.check_circuit_breaker(active_picks=[], closed_picks=closed)

    cb = json.loads(risk_controls.CIRCUIT_BREAKER_PATH.read_text())
    assert cb["realized_7d_pct"] == pytest.approx(-2.0, abs=0.01)
    # -2% is above WARNING (-5%), so status is NORMAL
    assert status == "NORMAL"
    assert cb["recent_closed_count"] == 100


def test_drawdown_with_966_picks_at_minus_6pct_yields_minus_6pct_not_minus_5796pct():
    """Issue #623 scenario: many closed picks. Old code would have produced
    966 * -6 = -5796%. New code reports -6% (the actual mean), which is
    comfortably in WARNING territory (below -5% threshold).

    Note: avoid -0.05 exactly because floating-point sum/N math lands on
    -4.99999... which is technically > -5.0 (NORMAL, not WARNING). -0.06
    is unambiguous and the same Issue #623 scenario."""
    closed = [_make_pick(-0.06, days_ago=3) for _ in range(966)]
    status = risk_controls.check_circuit_breaker(active_picks=[], closed_picks=closed)

    cb = json.loads(risk_controls.CIRCUIT_BREAKER_PATH.read_text())
    assert cb["realized_7d_pct"] == pytest.approx(-6.0, abs=0.01)
    assert status == "WARNING"


def test_mixed_unit_pnl_pct_is_clipped_before_averaging():
    """58 picks with pnl_pct stored as percentage (-2.5) instead of fraction
    (-0.025) must NOT drag the average to -2.5%; they get clipped to -1.0
    (-100% per pick is the floor) before averaging."""
    # 50 picks at sane -1% (-0.01) + 50 picks with -2.5 (percentage-form bug)
    closed = []
    for _ in range(50):
        closed.append(_make_pick(-0.01, days_ago=2))
    for _ in range(50):
        closed.append(_make_pick(-2.5, days_ago=2))  # Bug: stored as %, not fraction

    risk_controls.check_circuit_breaker(active_picks=[], closed_picks=closed)
    cb = json.loads(risk_controls.CIRCUIT_BREAKER_PATH.read_text())

    # After clipping the 50 outliers to -1.0:
    #   mean = (50 * -0.01 + 50 * -1.0) / 100 = (-0.5 + -50.0) / 100 = -0.505
    #   * 100 = -50.5%
    # Without clip:
    #   mean = (50 * -0.01 + 50 * -2.5) / 100 = -1.255
    #   * 100 = -125.5% — clearly nonsensical
    assert cb["realized_7d_pct"] == pytest.approx(-50.5, abs=0.1)


def test_emergency_threshold_still_fires_on_real_loss():
    """Confirm the fix doesn't accidentally unlock EMERGENCY on real losses.
    100 picks each at -16% (worse than -15% emergency threshold) should
    still trip EMERGENCY."""
    closed = [_make_pick(-0.16, days_ago=2) for _ in range(100)]
    status = risk_controls.check_circuit_breaker(active_picks=[], closed_picks=closed)

    cb = json.loads(risk_controls.CIRCUIT_BREAKER_PATH.read_text())
    assert cb["realized_7d_pct"] == pytest.approx(-16.0, abs=0.01)
    assert status == "EMERGENCY"


def test_normal_status_on_winning_picks():
    """Sanity: 100 picks each at +1% should be NORMAL."""
    closed = [_make_pick(0.01, days_ago=2) for _ in range(100)]
    status = risk_controls.check_circuit_breaker(active_picks=[], closed_picks=closed)

    cb = json.loads(risk_controls.CIRCUIT_BREAKER_PATH.read_text())
    assert cb["realized_7d_pct"] == pytest.approx(1.0, abs=0.01)
    assert status == "NORMAL"


def test_picks_outside_7d_window_excluded():
    """Picks older than 7 days must NOT count toward the drawdown."""
    closed = (
        [_make_pick(-0.20, days_ago=2) for _ in range(10)]   # 10 in window @ -20%
        + [_make_pick(-0.50, days_ago=30) for _ in range(100)]  # 100 OUT of window
    )
    risk_controls.check_circuit_breaker(active_picks=[], closed_picks=closed)
    cb = json.loads(risk_controls.CIRCUIT_BREAKER_PATH.read_text())

    # Only the 10 in-window picks count: mean = -20%
    assert cb["recent_closed_count"] == 10
    assert cb["realized_7d_pct"] == pytest.approx(-20.0, abs=0.01)


def test_unrealized_also_uses_mean_not_sum():
    """The same fix applies to unrealized PnL on active picks."""
    active = [
        {"unrealized_pnl_pct": -0.03},  # -3% per pick
        {"unrealized_pnl_pct": -0.03},
        {"unrealized_pnl_pct": -0.03},
    ]
    risk_controls.check_circuit_breaker(active_picks=active, closed_picks=[])
    cb = json.loads(risk_controls.CIRCUIT_BREAKER_PATH.read_text())

    # Old code: sum * 100 = -9%
    # New code: mean * 100 = -3%
    assert cb["unrealized_pct"] == pytest.approx(-3.0, abs=0.01)


def test_empty_inputs_produce_normal_status():
    """No picks → no drawdown → NORMAL."""
    status = risk_controls.check_circuit_breaker(active_picks=[], closed_picks=[])
    cb = json.loads(risk_controls.CIRCUIT_BREAKER_PATH.read_text())

    assert status == "NORMAL"
    assert cb["realized_7d_pct"] == 0.0
    assert cb["unrealized_pct"] == 0.0
    assert cb["recent_closed_count"] == 0


def test_picks_with_none_pnl_pct_skipped():
    """Picks where pnl_pct is None must be excluded from the mean."""
    closed = [
        _make_pick(-0.05, days_ago=1),
        _make_pick(None, days_ago=1),       # excluded
        _make_pick(-0.05, days_ago=1),
    ]
    risk_controls.check_circuit_breaker(active_picks=[], closed_picks=closed)
    cb = json.loads(risk_controls.CIRCUIT_BREAKER_PATH.read_text())

    # Mean of -0.05 and -0.05 (None excluded) = -5%
    assert cb["realized_7d_pct"] == pytest.approx(-5.0, abs=0.01)
    assert cb["recent_closed_count"] == 3  # count includes None-pnl rows


def test_none_exit_date_does_not_crash():
    """Picks where exit_date key exists but has value None must not crash.

    Issue #638: p.get("exit_date", "") returns None (not "") when the key is
    present with value None; None >= "2026-xx-xx" raises TypeError. The fix
    uses (p.get("exit_date") or "") to coerce None → "".
    """
    recent_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    closed = [
        {"exit_date": None, "closed_at": None, "pnl_pct": -0.05},   # None dates — must not crash
        {"exit_date": recent_date, "pnl_pct": -0.05},                # valid pick in window
    ]
    # Must not raise TypeError
    status = risk_controls.check_circuit_breaker(active_picks=[], closed_picks=closed)
    cb = json.loads(risk_controls.CIRCUIT_BREAKER_PATH.read_text())

    # Only the pick with a valid recent date should be counted
    assert cb["recent_closed_count"] == 1
    assert status in ("NORMAL", "WARNING", "EMERGENCY")
