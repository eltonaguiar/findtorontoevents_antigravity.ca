"""DSR must be a probability in [0,1], never a raw z-score (Grok quick-fix #2/#4).

Main's compute_deflated_sharpe returned (SR - E[max]*se)/se — a z-score — and compared
an ANNUALIZED Sharpe against a per-observation std error. That produced impossible values
like 14.71 (and DSR 7.69 in strategy_funnel_data.json). The Bailey-Lopez de Prado DSR is
a PROBABILITY bounded in [0,1].
"""
from __future__ import annotations

import math

from alpha_engine.rigorous_backtest_harness import compute_deflated_sharpe


def test_dsr_is_bounded_probability_not_zscore() -> None:
    # Repro from Grok's note: a strong Sharpe over 100 trials must NOT yield a z-score of ~14.
    dsr = compute_deflated_sharpe(2.0, n_trials=100, n_observations=200)
    assert 0.0 <= dsr <= 1.0, f"DSR must be a probability in [0,1], got {dsr}"


def test_dsr_single_trial_is_bounded() -> None:
    # Old code returned the raw annualized Sharpe when n_trials<=1 -> 1.8 (not a probability).
    dsr = compute_deflated_sharpe(1.8, n_trials=1, n_observations=40)
    assert 0.0 <= dsr <= 1.0, f"single-trial DSR must still be bounded, got {dsr}"


def test_dsr_high_signal_with_many_trials_not_certain() -> None:
    # A good-but-not-miraculous Sharpe deflated by 500 trials should land well below 1.0.
    dsr = compute_deflated_sharpe(1.8, n_trials=500, n_observations=400)
    assert 0.0 <= dsr <= 1.0
    assert dsr < 0.95, f"1.8 Sharpe over 500 trials should not be near-certain, got {dsr}"


def test_dsr_zero_observations_safe() -> None:
    dsr = compute_deflated_sharpe(1.5, n_trials=10, n_observations=0)
    assert 0.0 <= dsr <= 1.0


def test_dsr_monotonic_in_trials() -> None:
    # More trials (same Sharpe) => lower or equal DSR (harder to beat the expected max).
    a = compute_deflated_sharpe(2.0, n_trials=5, n_observations=300)
    b = compute_deflated_sharpe(2.0, n_trials=200, n_observations=300)
    assert 0.0 <= a <= 1.0 and 0.0 <= b <= 1.0
    assert b <= a + 1e-9, f"DSR should not rise with more trials: {a} -> {b}"


def test_dsr_monotonic_in_sharpe() -> None:
    lo = compute_deflated_sharpe(1.0, n_trials=50, n_observations=300)
    hi = compute_deflated_sharpe(3.0, n_trials=50, n_observations=300)
    assert 0.0 <= lo <= 1.0 and 0.0 <= hi <= 1.0
    assert hi >= lo - 1e-9, f"DSR should rise with Sharpe: {lo} -> {hi}"
