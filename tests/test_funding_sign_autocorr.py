"""Offline invariants for tools/funding_carry_sign_autocorr.py (no network, no cache file).

These cover the three helpers where a silent bug would change a verdict rather than
crash: the autocorrelation, the streak counter (which is what "clustering" means), and
the block bootstrap interval (which decides pass/fail).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.funding_carry_sign_autocorr import (acf, block_bootstrap_ci,  # noqa: E402
                                               max_drawdown_bp, runs)


def test_acf_of_a_constant_series_is_zero_not_a_division_error():
    assert acf([0.5] * 24, 1) == 0.0


def test_acf_detects_alternating_sign():
    xs = [1.0, -1.0] * 12
    assert acf(xs, 1) < -0.9          # perfectly anti-persistent at lag 1
    assert acf(xs, 2) > 0.9           # and persistent at lag 2


def test_runs_counts_only_negative_streaks():
    signs = [1, -1, -1, -1, 1, -1, 1, 1, -1]
    out = runs(signs)
    assert out["n_negative_streaks"] == 3
    assert out["longest_streak_days"] == 3
    assert out["median_streak_days"] == 1


def test_block_bootstrap_brackets_the_mean():
    xs = [0.001 * ((i % 7) - 3) for i in range(600)]
    lo, hi = block_bootstrap_ci(xs, block=10, n=400, seed=3)
    m = sum(xs) / len(xs)
    assert lo < m < hi


def test_max_drawdown_is_peak_relative_and_zero_when_monotone():
    assert max_drawdown_bp([1.0, -2.0, -3.0, 4.0]) == -5.0
    assert max_drawdown_bp([1.0, 2.0, 3.0]) == 0.0
