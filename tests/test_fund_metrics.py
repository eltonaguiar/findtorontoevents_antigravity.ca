"""Unit tests for tools/fund_deep_dive.py metrics (plan item I1).

These lock the 2026-11-23 corrections so a later refactor cannot silently
restore the old behaviour:
  A1/A2  Sharpe/Sortino are (R - R_f)/risk, not a fee-adjusted return/vol ratio
  A4     the cash vehicle emits null, not a finite ratio
  A5     Sortino uses the all-N target downside deviation, not the negative-day
         count (the legacy denominator is retained for the delta)
  A6     net_cagr is compounded, not additive
  A7     vol uses the sample stdev, not the population stdev

Fixtures are hand-computable so the expected values are derived arithmetically,
not copied from whatever the code happens to print.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import fund_deep_dive as fd  # noqa: E402


# --------------------------------------------------------------------------
# A6 / A7 / CAGR / MDD — exact arithmetic on a two-point series
# --------------------------------------------------------------------------
# r = [+10%, -10%], ann = 2 (so the CAGR exponent is 252/2 -> wait: ann/n with
# n=2 gives factor 1, i.e. the whole series is one "year").
# product = 1.10 * 0.90 = 0.99  ->  CAGR = 0.99**1 - 1 = -1.00%
TWO_POINT = [0.10, -0.10]


def test_cagr_is_geometric_on_the_series():
    m = fd.metrics(TWO_POINT, mer=0.0, ann=2)
    assert m["cagr_pct"] == pytest.approx(-1.00, abs=1e-9)


def test_net_cagr_is_compounded_not_additive():
    """A6: (1+cagr)(1-mer)-1, NOT cagr-mer.

    cagr=-0.01, mer=0.01 -> 0.99*0.99-1 = -0.0199 (-1.99%).
    The old additive form gave -0.02 (-2.00%) -> a 1bp overstatement.
    """
    m = fd.metrics(TWO_POINT, mer=0.01, ann=2)
    assert m["net_cagr_pct"] == pytest.approx(-1.99, abs=1e-9)
    additive = m["cagr_pct"] - 1.0  # what the old code effectively reported
    assert m["net_cagr_pct"] != pytest.approx(additive, abs=1e-12)


def test_vol_uses_sample_stdev():
    """A7: sample stdev of [0.1,-0.1] is 0.14142136; * sqrt(2) = 0.20 exactly.

    The population stdev is 0.1 -> *sqrt(2) = 14.14%. The difference is large
    enough that this test distinguishes them without ambiguity.
    """
    m = fd.metrics(TWO_POINT, mer=0.0, ann=2)
    assert m["vol_pct"] == pytest.approx(20.0, abs=1e-6)


def test_max_drawdown_two_point():
    """equity 1 -> 1.1 -> 0.99; mdd = 0.99/1.1 - 1 = -10%."""
    m = fd.metrics(TWO_POINT, mer=0.0, ann=2)
    assert m["max_dd_pct"] == pytest.approx(-10.0, abs=1e-9)


def test_flat_series_is_all_zero():
    m = fd.metrics([0.0] * 252, mer=0.0, ann=252)
    assert m["cagr_pct"] == pytest.approx(0.0, abs=1e-12)
    assert m["vol_pct"] == pytest.approx(0.0, abs=1e-12)
    assert m["max_dd_pct"] == pytest.approx(0.0, abs=1e-12)


# --------------------------------------------------------------------------
# A1 / A2 / A5 — ratios
# --------------------------------------------------------------------------
def test_sharpe_subtracts_the_risk_free_rate():
    """A1: (net_cagr - rf)/vol. With rf=0 the old and new forms coincide, so
    the test only bites once rf != 0 — which is the whole point."""
    m = fd.add_ratios(fd.metrics(TWO_POINT, mer=0.01, ann=2), rf=0.01)
    expected = (-0.0199 - 0.01) / 0.20
    assert m["sharpe"] == pytest.approx(expected, abs=1e-3)


def test_ret_vol_is_retained_and_differs_from_sharpe():
    """The legacy ratio must survive under its own (honest) name."""
    m = fd.add_ratios(fd.metrics(TWO_POINT, mer=0.01, ann=2), rf=0.01)
    assert "ret_vol" in m and "sharpe" in m
    assert m["ret_vol"] != pytest.approx(m["sharpe"], abs=1e-9)


def test_sharpe_is_none_without_a_cash_hurdle():
    m = fd.add_ratios(fd.metrics(TWO_POINT, mer=0.0, ann=2), rf=None)
    assert m["sharpe"] is None
    assert m["sortino"] is None


def test_sortino_all_n_denominator_exceeds_legacy():
    """A5: dividing by ALL n gives a SMALLER sigma_down, hence a LARGER ratio.

    The old code divided by the count of negative days only, which inflates
    sigma_down and understates Sortino. This was missed by the peer review.
    """
    r = [0.02, -0.01, 0.03, -0.02, 0.01, -0.005]
    m = fd.add_ratios(fd.metrics(r, mer=0.0, ann=len(r)), rf=0.0)
    assert m["sortino"] is not None and m["sortino_legacy"] is not None
    assert abs(m["sortino"]) >= abs(m["sortino_legacy"])


def test_add_ratios_strips_internal_keys():
    m = fd.add_ratios(fd.metrics(TWO_POINT, mer=0.01, ann=2), rf=0.01)
    assert not [k for k in m if k.startswith("_")]


# --------------------------------------------------------------------------
# A4 — the cash vehicle must not carry a finite ratio, end to end
# --------------------------------------------------------------------------
def test_cash_vehicle_emits_null_ratio(tmp_path, monkeypatch):
    """Run the real pipeline on the real CSV and assert SGOV is null in the JSON.

    This is the A4 acceptance criterion: a stored number (e.g. -0.006, which is
    a float-rounding artefact of 0/0) would be read as a real Sharpe by any
    consumer of the JSON.
    """
    src = REPO_ROOT / fd.SRC
    if not src.exists():
        pytest.skip("market_prices.csv not present in this checkout")

    monkeypatch.setattr(fd, "SRC", str(src))
    monkeypatch.chdir(tmp_path)
    fd.main()

    payload = json.loads((tmp_path / "reports" / "fund_deep_dive.json").read_text())
    sgov = payload["funds"]["SGOV_adj"]
    assert sgov["sharpe"] is None
    assert sgov["sortino"] is None
    assert "cash hurdle" in sgov["ratio_note"]

    cash_port = payload["portfolios"]["100% SGOV (T-bill)"]
    assert cash_port["sharpe"] is None

    # And a real fund must still carry a finite ratio.
    assert payload["funds"]["FXAIX_adj"]["sharpe"] is not None


def test_payload_declares_rebalancing_assumption(tmp_path, monkeypatch):
    """The JSON must state that portfolios are daily-rebalanced (plan D1 open)."""
    src = REPO_ROOT / fd.SRC
    if not src.exists():
        pytest.skip("market_prices.csv not present in this checkout")

    monkeypatch.setattr(fd, "SRC", str(src))
    monkeypatch.chdir(tmp_path)
    fd.main()

    payload = json.loads((tmp_path / "reports" / "fund_deep_dive.json").read_text())
    assert payload["schema_version"] >= 2
    # D1: standard portfolios are monthly-rebalanced; before the fix the JSON
    # said "daily" while the docstring claimed monthly -- the opposite of true.
    assert "monthly" in payload["rebalancing"].lower()
    assert "rebalance_sensitivity" in payload


# --------------------------------------------------------------------------
# D1 / D2 / D3 — rebalancing must be real, and its cost must be charged
# --------------------------------------------------------------------------
def test_single_sleeve_reproduces_the_fund_series():
    """weight=1.0 must return the underlying series exactly (no rebalancing)."""
    r = {"A": [0.01, -0.02, 0.03, 0.004]}
    out, stats = fd.portfolio(r, {"A": 1.0})
    assert out == pytest.approx(r["A"], abs=1e-12)
    assert stats["turnover"] == 0.0
    assert stats["rebalances"] == 0


def test_buy_and_hold_never_trades():
    r = {"A": [0.10, -0.05, 0.02], "B": [0.00, 0.01, -0.01]}
    _, stats = fd.portfolio(r, {"A": 0.6, "B": 0.4}, rebal=None)
    assert stats["rebalances"] == 0
    assert stats["turnover"] == 0.0


def test_rebalancing_trades_and_buy_and_hold_does_not():
    """D1: the two schedules must be genuinely different paths.

    The old implementation ignored `rebal`, so both calls returned the same
    series -- the test that would have caught it.
    """
    r = {"A": [0.10, -0.05, 0.08, -0.03, 0.06],
         "B": [0.00, 0.01, -0.01, 0.02, 0.00]}
    bh, bh_stats = fd.portfolio(r, {"A": 0.6, "B": 0.4}, rebal=None)
    rb, rb_stats = fd.portfolio(r, {"A": 0.6, "B": 0.4}, rebal=2)
    assert bh != pytest.approx(rb, abs=1e-12)
    assert rb_stats["rebalances"] > 0
    assert rb_stats["turnover"] > 0.0
    assert bh_stats["turnover"] == 0.0


def test_rebalance_cost_reduces_return():
    """D3: a wider spread must not increase the compounded return."""
    r = {"A": [0.10, -0.09, 0.11, -0.10, 0.07, -0.06],
         "B": [0.01, 0.00, -0.02, 0.03, 0.00, 0.01]}
    free, _ = fd.portfolio(r, {"A": 0.6, "B": 0.4}, rebal=1, spread_bp=0.0)
    costly, _ = fd.portfolio(r, {"A": 0.6, "B": 0.4}, rebal=1, spread_bp=50.0)
    nav_free = 1.0
    for x in free:
        nav_free *= (1 + x)
    nav_cost = 1.0
    for x in costly:
        nav_cost *= (1 + x)
    assert nav_cost < nav_free


def test_portfolio_nav_conserves_weights():
    """With zero returns everywhere the NAV must stay flat at 1.0."""
    r = {"A": [0.0] * 10, "B": [0.0] * 10}
    out, _ = fd.portfolio(r, {"A": 0.6, "B": 0.4}, rebal=3)
    assert all(abs(x) < 1e-12 for x in out)
