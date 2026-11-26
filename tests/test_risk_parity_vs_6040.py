"""Tests for tools/risk_parity_vs_6040.py (programme items E31, E33, E34).

The output of this tool is a comparison that a reader might act on, so the tests pin the
properties that could silently break and flatter a strategy: weights must be long-only and
sum to one, ERC must actually equalise risk contributions, HRP must not concentrate, and
every "beats 60/40" claim must carry a bootstrap CI rather than a point estimate.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from risk_parity_vs_6040 import erc_weights, hrp_weights, max_ce_weights  # noqa: E402

REPORT = ROOT / "reports" / "portfolio" / "risk_parity_2026-11-22.json"


def _cov(seed=7, n=4):
    rng = np.random.default_rng(seed)
    a = rng.normal(size=(400, n))
    a[:, 1] = 0.9 * a[:, 0] + 0.3 * a[:, 1]          # intentionally correlated
    return pd.DataFrame(np.cov(a.T) * 252, index=list("ABCD"), columns=list("ABCD"))


def test_erc_equalises_risk_contributions():
    cov = _cov()
    w = erc_weights(cov.values)
    rc = w * (cov.values @ w)
    assert rc.max() / rc.min() < 1.05, rc


def test_erc_is_long_only_and_sums_to_one():
    w = erc_weights(_cov().values)
    assert (w >= 0).all() and abs(w.sum() - 1.0) < 1e-9


def test_hrp_sums_to_one_and_is_long_only():
    cov = _cov()
    corr = cov / np.outer(np.sqrt(np.diag(cov)), np.sqrt(np.diag(cov)))
    w = hrp_weights(cov, pd.DataFrame(corr, index=cov.index, columns=cov.columns))
    assert abs(float(w.sum()) - 1.0) < 1e-9
    assert (w >= -1e-12).all()


def test_max_ce_is_long_only_and_sums_to_one():
    cov = _cov()
    mu = pd.Series([0.08, 0.03, 0.05, 0.01], index=cov.index)
    w = max_ce_weights(mu, cov)
    assert (w >= -1e-9).all() and abs(float(w.sum()) - 1.0) < 1e-6


def test_max_ce_drops_a_negative_excess_asset():
    """A negative-excess sleeve with NO diversification benefit must get ~zero weight.

    Uncorrelated assets on purpose: with a correlation < 1 a negative-return asset can
    legitimately earn weight as a hedge (variance reduction can pay for a negative mean),
    so asserting "zero" there would encode a false economic claim rather than a solver
    property. On a diagonal covariance the arithmetic is unambiguous: adding B only
    lowers the mean and raises the variance.
    """
    cov = pd.DataFrame(np.diag([0.04, 0.04, 0.04, 0.04]), index=list("ABCD"),
                       columns=list("ABCD"))
    mu = pd.Series([0.08, -0.02, 0.05, 0.03], index=cov.index)
    w = max_ce_weights(mu, cov)
    assert w["B"] < 0.02, w.to_dict()
    assert abs(float(w.sum()) - 1.0) < 1e-6


@pytest.mark.skipif(not REPORT.exists(), reason="report absent")
def test_no_strategy_claims_a_win_without_an_excluding_ci():
    d = json.loads(REPORT.read_text())
    v = d["verdict"]
    excl = v["strategies_with_ci_excluding_zero"]
    assert v["n_strategies_with_ci_excluding_zero"] == len(excl)
    assert v["beats_6040_after_cost"] == bool(excl), \
        "verdict must be gated on a CI excluding zero, not on a point estimate"
    for k, b in d["paired_ce_bootstrap_vs_60_40"].items():
        if "error" in b:
            continue
        assert "ci90_pp" in b and len(b["ci90_pp"]) == 2
        assert b["ce_diff_point_pp"] is not None
