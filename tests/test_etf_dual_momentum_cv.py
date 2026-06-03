"""Purged-embargoed CV metrics — offline tests."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verified_strategies"))
import etf_dual_momentum_cv as cv  # noqa: E402


def test_stable_series_holds_oos():
    # consistent positive-skew returns both halves -> HOLDS
    rets = ([0.03, -0.01] * 15)  # PF identical in train and test
    r = cv.purged_split_metrics(rets, train_frac=0.6, embargo=1)
    assert r["verdict"] == "HOLDS_OOS"
    assert abs(r["decay_pct"]) < 20


def test_decaying_series_flagged():
    # train profitable, test losing -> DECAYS
    rets = [0.04, 0.03, 0.05, 0.02, 0.04, 0.03, 0.05, 0.02, 0.04, 0.03,  # train wins
            0.05, 0.02, 0.04, 0.03,
            -0.05, -0.04, -0.06, -0.03, -0.05, -0.04, -0.06, -0.03]      # test losses
    r = cv.purged_split_metrics(rets, train_frac=0.6, embargo=1)
    assert r["verdict"] == "DECAYS"


def test_insufficient_data():
    r = cv.purged_split_metrics([0.01, -0.01, 0.02], train_frac=0.6)
    assert r["verdict"] == "INSUFFICIENT"


def test_embargo_drops_boundary():
    rets = [0.02] * 20 + [-0.01] * 20
    r = cv.purged_split_metrics(rets, train_frac=0.5, embargo=2)
    # n_train=20, embargo 2 -> test starts at index 22 -> 18 test obs
    assert r["n_train"] == 20 and r["n_test"] == 18
