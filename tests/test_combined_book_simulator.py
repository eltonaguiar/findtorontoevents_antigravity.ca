"""Tests for the month-end simulator + backtest stats."""
import pandas as pd

from combined_book import simulator


def _series(months, vals):
    return pd.Series(vals, index=pd.to_datetime([f"{m}-01" for m in months]))


def test_combine_sleeves_dot_product():
    sleeve = {
        "trend": _series(["2026-01", "2026-02"], [0.01, 0.02]),
        "quality": _series(["2026-01", "2026-02"], [0.03, -0.01]),
        "put": _series(["2026-01", "2026-02"], [0.00, 0.01]),
    }
    weights = {"trend": 0.35, "quality": 0.40, "put": 0.25}
    r = simulator.combine_sleeves(sleeve, weights)
    assert abs(r["2026-01-01"] - (0.35 * 0.01 + 0.40 * 0.03 + 0.25 * 0.00)) < 1e-9


def test_equity_curve_compounds():
    r = _series(["2026-01", "2026-02"], [0.10, -0.05])
    eq = simulator.equity_curve(r)
    assert abs(eq.iloc[0] - 1.10) < 1e-9
    assert abs(eq.iloc[1] - 1.10 * 0.95) < 1e-9


def test_max_drawdown_from_returns():
    r = _series(["2026-01", "2026-02", "2026-03"], [0.20, -0.25, 0.10])
    assert simulator.max_drawdown_from_returns(r) < 0.0


def test_compute_stats_includes_required_keys():
    r = _series(["2026-01", "2026-02", "2026-03"], [0.01, 0.02, -0.01])
    stats = simulator.compute_stats(r)
    for key in ("n_months", "cagr", "sharpe", "annualized_sharpe", "max_dd",
                "pf", "win_rate", "bootstrap_p_over_1"):
        assert key in stats
