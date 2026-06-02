"""Regression: mutation_framework.compute_pf must be dollar PF, not win/loss count ratio."""
from verified_strategies.mutation_framework import compute_pf


def test_compute_pf_mixed_trades():
    assert compute_pf([2.0, -1.0, 3.0, -2.0, 1.0]) == 2.0


def test_compute_pf_all_wins_not_inflated():
    assert compute_pf([1.0] * 10) == 0.0


def test_compute_pf_all_losses():
    assert compute_pf([-1.0, -2.0]) == 0.0


def test_compute_pf_capped():
    assert compute_pf([100.0, -0.01]) == 99.0
