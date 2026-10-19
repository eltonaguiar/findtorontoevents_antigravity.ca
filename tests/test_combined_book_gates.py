"""Tests for the statistical go-live + kill gates."""
from combined_book import gates


def test_wilson_ci_bounds():
    lo, hi = gates.wilson_ci(60, 100)
    assert 0.0 <= lo < 0.60 < hi <= 1.0


def test_binomial_pvalue_matches_known_case():
    # 60/100 against p0=0.5 is ~2 sigma -> p ~ 0.045
    p = gates.binomial_pvalue(60, 100)
    assert 0.01 < p < 0.10


def test_profit_factor():
    assert abs(gates.profit_factor([1.0, 2.0, -1.0, -0.5]) - (3.0 / 1.5)) < 1e-9
    assert gates.profit_factor([1.0, 2.0]) == float("inf")


def test_bootstrapped_pf_reproducible():
    a = gates.bootstrapped_pf([0.01, -0.02, 0.03, -0.01], seed=1, n_sims=200)
    b = gates.bootstrapped_pf([0.01, -0.02, 0.03, -0.01], seed=1, n_sims=200)
    assert a == b


def test_sharpe_zero_vol_is_zero():
    assert gates.sharpe([0.01, 0.01, 0.01]) == 0.0


def test_annualized_sharpe_scales():
    assert abs(gates.annualized_sharpe([0.01, 0.02, -0.01]) - gates.sharpe([0.01, 0.02, -0.01]) * (12 ** 0.5)) < 1e-9


def test_deflated_sharpe_lower_than_raw():
    raw = gates.sharpe([0.01, 0.02, -0.01, 0.02, 0.01])
    df = gates.deflated_sharpe(raw, n_variants=50, n_samples=60)
    assert df < raw


def test_gate_sanity_no_edge_fails():
    """A coin-flip-ish series must NOT pass the go-live gate."""
    import numpy as np
    import pandas as pd
    from combined_book.simulator import compute_stats
    rng = np.random.default_rng(4)
    returns = rng.choice([0.03, -0.03], size=200)
    stats = compute_stats(pd.Series(returns))
    go, checks = gates.evaluate_go_live(stats)
    assert not go
    assert checks["pf"] is False  # PF ~ 1 < 1.5


def test_gate_sanity_known_edge_passes():
    """A stable positive-drift series must pass the go-live gate."""
    import numpy as np
    import pandas as pd
    from combined_book.simulator import compute_stats
    rng = np.random.default_rng(4)
    returns = rng.normal(0.02, 0.004, size=120)
    stats = compute_stats(pd.Series(returns))
    go, _ = gates.evaluate_go_live(stats)
    assert go
    killed, _ = gates.evaluate_kill(stats)
    assert not killed


def test_random_entry_percentile_in_range():
    pct = gates.random_entry_percentile([0.01, 0.02, -0.01], [0.02, 0.01, -0.02], seed=3, n_sims=200)
    assert 0.0 <= pct <= 1.0


def test_evaluate_go_live():
    ok, checks = gates.evaluate_go_live(
        {"n_months": 120, "pf": 1.8, "win_rate": 0.55, "max_dd": -0.10}
    )
    assert ok is True
    assert all(checks.values())


def test_evaluate_kill_requires_24_months():
    killed, _ = gates.evaluate_kill(
        {"n_months": 12, "max_dd": -0.30, "pf": 0.5, "win_rate": 0.4,
         "annualized_sharpe": -0.5, "bootstrap_p_over_1": 0.9}
    )
    assert killed is False  # still too few months


def test_evaluate_kill_fires_after_24_months():
    killed, kills = gates.evaluate_kill(
        {"n_months": 30, "max_dd": -0.30, "pf": 0.5, "win_rate": 0.4,
         "annualized_sharpe": -0.5, "bootstrap_p_over_1": 0.9}
    )
    assert killed is True
    assert kills["drawdown"] is True
    assert kills["pf"] is True
