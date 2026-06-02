"""ENHANCEMENT #67 — shadow-size promotion ladder tests (pure functions)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verified_strategies"))
import admissibility_pipeline as ap  # noqa: E402


def test_rejected_when_harness_not_cleared():
    p = ap.shadow_size_plan(False)
    assert p["stage"] == "REJECTED"
    assert p["capital_fraction"] == 0.0


def test_cleared_enters_shadow_at_half_percent():
    p = ap.shadow_size_plan(True, forward_weeks=0)
    assert p["stage"] == "SHADOW"
    assert p["capital_fraction"] == ap.SHADOW_SIZE_PCT == 0.005


def test_probation_when_weeks_met_but_criteria_not():
    p = ap.shadow_size_plan(True, forward_weeks=6, backtest_pf=2.0, live_pf=2.0,
                            windows_passed=1)
    assert p["stage"] == "PROBATION"
    assert p["capital_fraction"] == 0.005


def test_promote_only_after_two_windows_within_tolerance():
    p = ap.shadow_size_plan(True, forward_weeks=8, backtest_pf=2.0, live_pf=1.9,
                            windows_passed=2)
    assert p["stage"] == "PROMOTE"
    assert p["pf_within_tolerance"] is True
    assert p["capital_fraction"] is None  # graded scaling, manual sign-off


def test_no_promote_when_pf_out_of_tolerance():
    # live PF 50% below backtest -> out of +-10% band
    p = ap.shadow_size_plan(True, forward_weeks=8, backtest_pf=2.0, live_pf=1.0,
                            windows_passed=3)
    assert p["stage"] == "PROBATION"
    assert p["pf_within_tolerance"] is False
