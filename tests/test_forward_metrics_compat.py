"""Tests for forward_metrics_compat.forward_win_rate_percent."""

from forward_metrics_compat import forward_win_rate_percent


def test_legacy_percent():
    assert forward_win_rate_percent({"forward_win_rate": 62.5}) == 62.5


def test_ratio_strat_fwd_wr():
    assert forward_win_rate_percent({"strat_fwd_wr": 0.52}) == 52.0


def test_nested_forward_metrics():
    assert forward_win_rate_percent(
        {"forward_metrics": {"win_rate": 83.33}}
    ) == 83.33


def test_strat_fwd_wr_priority_over_nested():
    assert forward_win_rate_percent(
        {"strat_fwd_wr": 0.6, "forward_metrics": {"win_rate": 50.0}}
    ) == 60.0


def test_empty():
    assert forward_win_rate_percent({}) == 0.0
