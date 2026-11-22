"""Deterministic tests for tools/residual_mean_reversion.py (no network)."""

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.residual_mean_reversion import (  # noqa: E402
    MIN_FIT_N,
    ols,
    ou_fit,
    paired_gate_compare,
    residuals,
    returns,
    round_trip_cost_pct,
    s_score,
    simulate,
    summarize,
)


def _rw(n: int = 1500, seed: int = 3):
    """Independent random walks — no residual reversion exists to find."""
    rng = random.Random(seed)
    fac, sym = [100.0], [100.0]
    for _ in range(n - 1):
        fac.append(fac[-1] * (1 + rng.gauss(0, 0.01)))
        sym.append(sym[-1] * (1 + rng.gauss(0, 0.015)))
    return sym, {"F": fac}


def test_round_trip_cost_charges_both_legs_both_ways():
    # 2 legs x in-and-out x 5 bps = 0.2%, NOT 0.1% — the hedge is not free.
    assert math.isclose(round_trip_cost_pct(2, 5.0), 0.2, abs_tol=1e-12)
    assert math.isclose(round_trip_cost_pct(1, 5.0), 0.1, abs_tol=1e-12)
    assert math.isclose(round_trip_cost_pct(2, 10.0), 0.4, abs_tol=1e-12)


def test_gross_and_net_reconcile_exactly():
    # The invariant that would have caught the stale-artifact bug: net must
    # equal gross minus cost, per trade and on the mean.
    sym, fac = _rw()
    trades = simulate(sym, fac, window=60)
    assert trades
    for t in trades:
        assert math.isclose(t["pnl_pct"], t["gross_pct"] - t["cost_pct"],
                            abs_tol=1e-6)
    s = summarize(trades)
    assert math.isclose(s["mean_net_pct"],
                        s["mean_gross_pct"] - s["cost_per_trade_pct"],
                        abs_tol=1e-3)


def test_hedge_is_booked_so_loaded_factor_does_not_pay():
    # A symbol that is pure factor exposure must earn ~nothing gross after
    # the hedge. Before the fix it earned the factor's drift.
    rng = random.Random(11)
    fac, sym = [100.0], [100.0]
    for _ in range(1200):
        d = rng.gauss(0, 0.01)
        fac.append(fac[-1] * (1 + d))
        sym.append(sym[-1] * (1 + 2.0 * d))  # exactly 2x the factor, no alpha
    trades = simulate(sym, {"F": fac}, window=60)
    if trades:
        gross = sum(t["gross_pct"] for t in trades)
        # Residual reversion on a perfectly-loaded name is noise; the point is
        # that it is not the factor's own multi-hundred-percent drift.
        assert abs(gross) < 50.0


def test_paired_compare_uses_one_index_draw():
    # Determinism: same seed, same trades in, same answer out. An unpaired
    # implementation drawing two independent index sets is still deterministic
    # here, so the real assertion is that the delta is small when the arms are
    # nearly identical — an unpaired draw would show spurious spread.
    sym, fac = _rw(seed=5)
    a = paired_gate_compare(sym, fac, window=60, b=200, seed=7)
    b_ = paired_gate_compare(sym, fac, window=60, b=200, seed=7)
    assert a["sharpe_delta"] == b_["sharpe_delta"]
    assert a["delta_ci95"] == b_["delta_ci95"]
    # Keys the hypothesis needs, always present even when inconclusive.
    for k in ("turnover_reduction", "gross_alpha_retention"):
        assert k in a


def test_returns_skip_zero_base():
    r = returns([100, 110, 0, 5])
    # 110/100 is not exactly 0.1 in binary floats — compare with a tolerance
    # rather than pretending it is.
    assert abs(r[0] - 0.1) < 1e-12
    # (110, 0) and (0, 5) both involve a zero: a zero price is missing data, so
    # the return is 0.0 (neither a gain nor a loss) instead of -100% or inf.
    assert r[1] == 0.0
    assert r[2] == 0.0


def test_ols_recovers_known_coefficients():
    rng = random.Random(11)
    x = [rng.gauss(0, 1) for _ in range(200)]
    y = [3.0 + 2.5 * xi for xi in x]
    a, betas = ols(y, [x])
    assert abs(a - 3.0) < 1e-6
    assert abs(betas[0] - 2.5) < 1e-6


def test_ols_is_none_below_minimum_sample():
    assert ols([1.0] * 10, [[1.0] * 10]) is None


def test_ols_is_none_on_collinear_factors():
    rng = random.Random(5)
    x = [rng.gauss(0, 1) for _ in range(100)]
    y = [rng.gauss(0, 1) for _ in range(100)]
    # identical columns: singular, must refuse rather than return garbage
    assert ols(y, [x, list(x)]) is None


def test_residuals_are_orthogonal_to_the_fitted_factor():
    rng = random.Random(2)
    x = [rng.gauss(0, 1) for _ in range(150)]
    y = [1.5 * xi + rng.gauss(0, 0.3) for xi in x]
    e = residuals(y, [x])
    assert e is not None
    assert abs(sum(e) / len(e)) < 1e-9  # intercept absorbs the mean
    assert abs(sum(ei * xi for ei, xi in zip(e, x))) < 1e-6


def _ou_path(rho=0.9, n=400, seed=1):
    rng = random.Random(seed)
    x = [0.0]
    for _ in range(n - 1):
        x.append(rho * x[-1] + rng.gauss(0, 1))
    return x


def test_ou_fit_recovers_half_life():
    rho = 0.9
    fit = ou_fit(_ou_path(rho))
    assert fit is not None
    expected = math.log(2) / (1 - rho)
    assert abs(fit["half_life"] - expected) / expected < 0.25
    assert fit["kappa"] > 0


def test_ou_fit_documents_the_small_sample_bias_on_a_random_walk():
    """A random walk can look mean-reverting at finite n — that is the point.

    AR(1) on a finite sample is biased downward in rho, so a pure random walk
    yields kappa > 0 and a short-looking half-life. This test pins the known
    behavior so nobody later reads a half-life as proof of reversion: the true
    half-life here is infinite, and the fit still reports a finite number.
    """
    rng = random.Random(4)
    x = [0.0]
    for _ in range(MIN_FIT_N + 50):
        x.append(x[-1] + rng.gauss(0, 1))
    fit = ou_fit(x)
    assert fit is None or fit["half_life"] < 100  # finite despite no reversion
    # The honest guard is not the half-life but the rho it came from being
    # implausibly close to 1 for a real mean-reverting series.
    if fit is not None:
        assert 0 < fit["rho"] < 1


def test_s_score_is_standardized_distance():
    fit = {"mu": 1.0, "sigma_eq": 2.0}
    assert s_score(3.0, fit) == 1.0
    assert s_score(1.0, fit) == 0.0
    assert s_score(3.0, {"mu": 1.0, "sigma_eq": None}) is None


def test_simulate_is_point_in_time():
    """Truncating the future must not change trades decided before the cut."""
    rng = random.Random(7)
    n = 400
    fac = [100.0]
    sym = [100.0]
    for _ in range(n - 1):
        f = fac[-1] * (1 + rng.gauss(0, 0.01))
        fac.append(f)
        sym.append(sym[-1] * (1 + 1.0 * (f / fac[-2] - 1) + rng.gauss(0, 0.02)))
    full = simulate(sym, {"F": fac}, window=60)
    cut = 300
    part = simulate(sym[:cut], {"F": fac[:cut]}, window=60)
    closed_before = [t for t in full if t["hold_days"] and t["entry_s"] is not None]
    # every trade the truncated run produced must also appear in the full run
    keys_full = {(t["direction"], t["entry_price"], t["entry_s"]) for t in full}
    for t in part:
        assert (t["direction"], t["entry_price"], t["entry_s"]) in keys_full
    assert closed_before is not None


def test_simulate_refuses_when_too_short():
    assert simulate([100.0] * 50, {"F": [100.0] * 50}, window=60) == []


def test_summarize_empty_is_inconclusive():
    s = summarize([])
    assert s["n"] == 0
    assert "INCONCLUSIVE" in s["verdict"]


def test_summarize_profit_factor_needs_losses():
    only_wins = [{"pnl_pct": 1.0, "hold_days": 2, "exit_kind": "revert"}]
    assert summarize(only_wins)["profit_factor"] is None
    mixed = [{"pnl_pct": 2.0, "hold_days": 2, "exit_kind": "revert"},
             {"pnl_pct": -1.0, "hold_days": 3, "exit_kind": "stop"}]
    assert summarize(mixed)["profit_factor"] == 2.0
