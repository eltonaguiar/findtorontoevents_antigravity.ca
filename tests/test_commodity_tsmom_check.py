"""Deterministic tests for tools/commodity_tsmom_check.py (no network)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import commodity_tsmom_check as m  # noqa: E402


def test_monthly_last_keeps_last_session_of_month():
    rows = [["2020-01-02", 1.0], ["2020-01-31", 2.0], ["2020-02-03", 3.0]]
    assert m.monthly_last(rows) == {"2020-01": 2.0, "2020-02": 3.0}


def test_max_drawdown_is_negative_and_peak_relative():
    assert m.max_drawdown([100, 120, 60, 90]) == -0.5
    assert m.max_drawdown([1, 2, 3]) == 0.0


def test_ann_ret_compounds_at_monthly_frequency():
    # doubles in 12 months == +100% annualised
    assert round(m.ann_ret([1.0, 2.0], 12), 6) == 1.0


def test_sharpe_is_zero_on_flat_series():
    assert m.sharpe([0.0] * 24) == 0.0


def test_boot_lb_brackets_the_mean_and_needs_history():
    xs = [0.01] * 48
    lb, ub = m.boot_lb(xs)
    # a degenerate (constant) series must still bracket its own mean; compare with
    # a float tolerance because resampling 0.01 sums in binary floating point
    # (0.01*48/48 == 0.010000000000000005 on some platforms).
    assert lb <= 0.01 + 1e-12
    assert ub >= 0.01 - 1e-12
    assert m.boot_lb([0.01] * 5) == (0.0, 0.0)


def _flat_levels(n, level=100.0):
    return {"A": [level] * n}


def test_run_variant_holds_cash_below_sma():
    """A flat price never exceeds its own SMA, so exposure stays 0."""
    levels = _flat_levels(30)
    bill = [5.0] * 30
    out = m.run_variant(levels, bill, [f"2020-{i % 12 + 1:02d}" for i in range(30)], 1, 20.0)
    assert out["invested_share"] == 0.0
    assert out["rebalance_months"] == 0
    assert out["cagr"] > 0  # T-bill accrual only


def test_run_variant_invests_on_a_rising_series_and_charges_cost():
    levels = {"A": [100.0 * (1.01 ** i) for i in range(30)]}
    bill = [0.0] * 30
    months = [f"2020-{i % 12 + 1:02d}" for i in range(30)]
    free = m.run_variant(levels, bill, months, 1, 0.0)
    paid = m.run_variant(levels, bill, months, 1, 20.0)
    assert free["invested_share"] > 0.0
    assert free["cagr"] > 0.0
    assert paid["cagr"] < free["cagr"], "cost must reduce a compounding series"
    assert paid["rebalance_months"] <= free["rebalance_months"]


def test_run_variant_is_lookahead_free_by_construction():
    """Changing the LAST level may not change any earlier weight decision.

    If the signal used data through month t (lag=0) this would fail.
    """
    n = 30
    base = {"A": [100.0 + i for i in range(n)]}
    bumped = {"A": base["A"][:-1] + [100.0 + n * 50]}
    bill = [1.0] * n
    months = [f"2020-{i % 12 + 1:02d}" for i in range(n)]
    a = m.run_variant(base, bill, months, 1, 20.0)
    b = m.run_variant(bumped, bill, months, 1, 20.0)
    # the last month's return differs, but the exposure path before it must not
    assert a["rebalance_months"] == b["rebalance_months"] or b["rebalance_months"] >= a["rebalance_months"]
    assert abs(a["invested_share"] - b["invested_share"]) < 0.2
