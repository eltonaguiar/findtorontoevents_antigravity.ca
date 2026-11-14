"""Tests for tools.cot_contrarian_backtest — pure logic only, no network/DB."""
from datetime import date

import pytest

from tools import cot_contrarian_backtest as cot


# --- trailing z-score must not look ahead ---------------------------------
def test_zscores_are_computed_from_prior_values_only():
    # A flat history then one huge jump: the jump's own z must use the flat
    # history (huge), not a mean polluted by itself.
    values = [10.0 + (i % 2) * 0.1 for i in range(40)] + [1000.0]
    zs = cot.trailing_zscores(values, window=156)
    assert all(z is None for z in zs[:30])
    assert zs[40] > 50, "the outlier is scored against prior data, so it is extreme"


def test_zscores_none_when_history_too_short():
    zs = cot.trailing_zscores([1.0, 2.0, 3.0], window=156)
    assert zs == [None, None, None]


def test_zscores_none_on_zero_variance():
    assert cot.trailing_zscores([5.0] * 40, window=156)[-1] is None


def test_zscores_ignore_missing_values():
    values = [1.0, None] + [2.0] * 40
    zs = cot.trailing_zscores(values, window=156)
    assert zs[1] is None
    assert zs[-1] is not None


# --- profit factor ---------------------------------------------------------
def test_profit_factor_basic():
    assert cot.profit_factor([0.02, -0.01, 0.03, -0.01]) == pytest.approx(2.5)


def test_profit_factor_no_losses_is_inf():
    assert cot.profit_factor([0.01, 0.02]) == float("inf")


def test_profit_factor_all_losses_is_zero():
    assert cot.profit_factor([-0.01, -0.02]) == 0.0


def test_profit_factor_empty_is_none():
    assert cot.profit_factor([]) is None


# --- entry timing guard ----------------------------------------------------
def test_entry_is_after_friday_publication():
    # COT as-of Tuesday 2026-01-06 -> published Fri 2026-01-09 -> Monday 01-12
    bars = [date(2026, 1, 5), date(2026, 1, 9), date(2026, 1, 12), date(2026, 1, 13)]
    i = cot.entry_index_for(bars, date(2026, 1, 6))
    assert bars[i] == date(2026, 1, 12)
    assert bars[i] > date(2026, 1, 6) + (date(2026, 1, 9) - date(2026, 1, 6))


def test_entry_skips_bars_before_publication():
    bars = [date(2026, 1, 5), date(2026, 1, 6), date(2026, 1, 7)]
    # No bar at/after the Monday following publication -> no trade, never a
    # pre-publication bar.
    assert cot.entry_index_for(bars, date(2026, 1, 6)) is None


def test_entry_none_when_no_later_bar():
    assert cot.entry_index_for([date(2026, 1, 5)], date(2026, 1, 6)) is None


# --- gate ------------------------------------------------------------------
def test_gate_passes_on_strong_oos():
    rets = [0.02] * 60 + [-0.01] * 40  # PF 3.0, n=100, mean +0.008
    g = cot.evaluate_gate(rets, oos_benchmark_mean=0.001)
    assert g["n"] == 100
    assert g["checks"]["n_ge_100"] is True
    assert g["checks"]["pf_ge_1.15"] is True
    assert g["checks"]["beats_benchmark"] is True
    assert g["passes_gate"] is True


def test_gate_fails_below_100_trades_even_when_profitable():
    rets = [0.02] * 30 + [-0.01] * 30  # PF 2.0 but n=60
    g = cot.evaluate_gate(rets, oos_benchmark_mean=0.0)
    assert g["checks"]["n_ge_100"] is False
    assert g["passes_gate"] is False


def test_gate_fails_when_pf_below_threshold():
    rets = [0.011] * 50 + [-0.010] * 50  # PF 1.10
    g = cot.evaluate_gate(rets, oos_benchmark_mean=0.0)
    assert g["checks"]["pf_ge_1.15"] is False
    assert g["passes_gate"] is False


def test_gate_requires_beating_benchmark_not_zero():
    rets = [0.02] * 60 + [-0.01] * 40  # beats zero
    g = cot.evaluate_gate(rets, oos_benchmark_mean=0.05)  # but not the benchmark
    assert g["checks"]["beats_benchmark"] is False
    assert g["passes_gate"] is False


def test_gate_fails_when_costs_exceed_quarter_of_gross():
    # tiny edge: gross 0.0012 vs 0.0010 cost -> slippage share ~0.83
    rets = [0.0012] * 60 + [0.0012] * 40
    g = cot.evaluate_gate(rets, oos_benchmark_mean=0.0)
    assert g["slippage_share_of_gross"] > 0.25
    assert g["checks"]["slippage_lt_25pct"] is False


def test_gate_none_benchmark_cannot_pass():
    g = cot.evaluate_gate([0.02] * 60 + [-0.01] * 40, oos_benchmark_mean=None)
    assert g["checks"]["beats_benchmark"] is False


# --- split ----------------------------------------------------------------
def test_split_uses_first_60_percent_of_report_dates():
    cot_map = {"HG": [{"report_date": date(2021, 1, 1) + __import__("datetime").timedelta(weeks=i),
                       "comm_net_pct_oi": 1.0} for i in range(200)]}
    cut = cot.split_dates(cot_map, 0.60)
    assert cut is not None
    assert cut == cot_map["HG"][119]["report_date"] or cut == cot_map["HG"][120]["report_date"]


def test_split_returns_none_for_short_history():
    cot_map = {"HG": [{"report_date": date(2021, 1, 1), "comm_net_pct_oi": 1.0}] * 10}
    assert cot.split_dates(cot_map) is None
