"""
test_stat_tests.py — Comprehensive tests for stat_tests module.
"""

import sys
import math
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from alpha_engine.stat_tests import (
    wilson_score_interval,
    two_proportion_z_test,
    welch_t_test,
    chi_square_independence,
    bonferroni_correction,
    bootstrap_ci,
    sharpe_ratio,
    sortino_ratio,
    profit_factor,
    max_consecutive,
    kelly_criterion,
    var_cvar,
    herfindahl_hirschman,
)

PASS = 0
FAIL = 0


def assert_near(a, b, tol=1e-6, msg=""):
    global PASS, FAIL
    if abs(a - b) <= tol:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {msg} — expected {b}, got {a} (tol={tol})")


def assert_true(cond, msg=""):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {msg}")


def assert_tuple_near(a, b, tol=1e-6, msg=""):
    global PASS, FAIL
    if len(a) != len(b):
        FAIL += 1
        print(f"FAIL: {msg} — length mismatch {len(a)} vs {len(b)}")
        return
    ok = all(abs(x - y) <= tol for x, y in zip(a, b))
    if ok:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {msg} — expected {b}, got {a}")


# ======================= Wilson Score Interval =======================

def test_wilson():
    print("--- Wilson Score Interval ---")
    # Standard case: 50/100
    lo, hi = wilson_score_interval(50, 100)
    assert_true(lo < 0.5 < hi, "50/100 should contain 0.5")
    assert_near(lo, 0.4038, tol=0.01, msg="wilson lower")
    assert_near(hi, 0.5962, tol=0.01, msg="wilson upper")

    # Perfect success
    lo, hi = wilson_score_interval(100, 100)
    assert_true(lo > 0.95, "all successes lower bound > 0.95")
    assert_true(hi == 1.0 or hi > 0.99, "all successes upper ~1.0")

    # Zero trials
    lo, hi = wilson_score_interval(0, 0)
    assert_tuple_near((lo, hi), (0.0, 0.0), msg="zero trials")

    # Zero successes
    lo, hi = wilson_score_interval(0, 100)
    assert_true(lo == 0.0, "zero successes lower = 0")
    assert_true(hi < 0.05, "zero successes upper < 0.05")


# ======================= Two-Proportion Z-Test =======================

def test_two_prop_z():
    print("--- Two-Proportion Z-Test ---")
    # Clear difference
    z, p, sig = two_proportion_z_test(100, 80, 100, 50)
    assert_true(sig, "80% vs 50% should be significant")
    assert_true(p < 0.001, "p should be very small")

    # Same proportions
    z, p, sig = two_proportion_z_test(100, 50, 100, 50)
    assert_near(z, 0.0, tol=1e-9, msg="same props z=0")
    assert_true(not sig, "same props not significant")

    # Zero samples
    z, p, sig = two_proportion_z_test(0, 0, 100, 50)
    assert_true(p == 1.0, "zero sample p=1")
    assert_true(not sig, "zero sample not sig")

    # All zeros
    z, p, sig = two_proportion_z_test(0, 0, 0, 0)
    assert_true(not sig, "all zero not sig")


# ======================= Welch's t-Test =======================

def test_welch():
    print("--- Welch's t-Test ---")
    # Clear difference
    t, p, df, sig = welch_t_test(10.0, 2.0, 30, 5.0, 2.0, 30)
    assert_true(sig, "10 vs 5 should be significant")
    assert_true(p < 0.001, "p should be very small")
    assert_true(df > 0, "df should be positive")

    # Same means
    t, p, df, sig = welch_t_test(5.0, 1.0, 30, 5.0, 1.0, 30)
    assert_near(t, 0.0, tol=1e-9, msg="same means t=0")
    assert_true(not sig, "same means not significant")

    # Too few samples
    t, p, df, sig = welch_t_test(5.0, 1.0, 1, 5.0, 1.0, 30)
    assert_true(p == 1.0, "n1<2 returns p=1")

    # Zero variance
    t, p, df, sig = welch_t_test(5.0, 0.0, 30, 5.0, 0.0, 30)
    assert_near(t, 0.0, tol=1e-9, msg="zero var same mean")

    t, p, df, sig = welch_t_test(5.0, 0.0, 30, 3.0, 0.0, 30)
    assert_true(sig, "zero var diff mean significant")


# ======================= Chi-Square Independence =======================

def test_chi_square():
    print("--- Chi-Square Independence ---")
    # Independent table
    observed = [[25, 25], [25, 25]]
    chi2, p, dof, sig = chi_square_independence(observed)
    assert_near(chi2, 0.0, tol=1e-9, msg="uniform table chi2=0")
    assert_true(not sig, "uniform table not sig")

    # Strong association
    observed = [[50, 0], [0, 50]]
    chi2, p, dof, sig = chi_square_independence(observed)
    assert_true(chi2 > 50, "strong association chi2 large")
    assert_true(sig, "strong association significant")
    assert_true(dof == 1, "2x2 dof=1")

    # Empty table
    chi2, p, dof, sig = chi_square_independence([])
    assert_true(p == 1.0, "empty table p=1")

    # Zero totals
    observed = [[0, 0], [0, 0]]
    chi2, p, dof, sig = chi_square_independence(observed)
    assert_true(not sig, "zero table not sig")

    # 3x2 table
    observed = [[10, 20], [30, 40], [50, 60]]
    chi2, p, dof, sig = chi_square_independence(observed)
    assert_true(dof == 2, "3x2 dof=2")


# ======================= Bonferroni Correction =======================

def test_bonferroni():
    print("--- Bonferroni Correction ---")
    assert_near(bonferroni_correction(0.05, 10), 0.005, msg="0.05/10")
    assert_near(bonferroni_correction(0.01, 5), 0.002, msg="0.01/5")
    assert_near(bonferroni_correction(0.05, 0), 0.05, msg="zero tests")
    assert_near(bonferroni_correction(0.05, 1), 0.05, msg="one test")


# ======================= Bootstrap CI =======================

def test_bootstrap():
    print("--- Bootstrap CI ---")
    data = [1.0, 2.0, 3.0, 4.0, 5.0]
    lo, hi = bootstrap_ci(data, lambda x: sum(x) / len(x), n_boot=5000, seed=42)
    assert_true(lo < 3.0 < hi, "mean CI contains 3")
    assert_true(lo > 1.5, "lo > 1.5")
    assert_true(hi < 4.5, "hi < 4.5")

    # Empty data
    lo, hi = bootstrap_ci([], lambda x: sum(x) / max(len(x), 1))
    assert_tuple_near((lo, hi), (0.0, 0.0), msg="empty data")

    # Single element
    lo, hi = bootstrap_ci([42.0], lambda x: x[0], n_boot=100)
    assert_tuple_near((lo, hi), (42.0, 42.0), tol=1e-9, msg="single element")


# ======================= Sharpe Ratio =======================

def test_sharpe():
    print("--- Sharpe Ratio ---")
    # Positive returns with variation
    returns = [0.001 + 0.0005 * (i % 3) for i in range(252)]
    sr = sharpe_ratio(returns)
    assert_true(sr > 0, "positive returns sharpe > 0")

    # Single return → std undefined → sharpe=0
    sr = sharpe_ratio([0.001])
    assert_near(sr, 0.0, msg="single return")

    sr = sharpe_ratio([])
    assert_near(sr, 0.0, msg="empty returns")

    # Negative returns with variation
    returns = [-0.001 - 0.0005 * (i % 3) for i in range(252)]
    sr = sharpe_ratio(returns)
    assert_true(sr < 0, "negative returns sharpe < 0")

    # With risk-free
    returns = [0.002 + 0.0005 * (i % 3) for i in range(252)]
    sr = sharpe_ratio(returns, risk_free=0.001)
    assert_true(sr > 0, "excess positive sharpe > 0")


# ======================= Sortino Ratio =======================

def test_sortino():
    print("--- Sortino Ratio ---")
    returns = [0.001] * 252
    sr = sortino_ratio(returns)
    # All positive → downside var = 0 → sortino = 0 (no downside)
    assert_near(sr, 0.0, tol=1e-6, msg="all positive sortino=0")

    returns = [-0.001] * 252
    sr = sortino_ratio(returns)
    assert_true(sr < 0, "all negative sortino < 0")

    sr = sortino_ratio([])
    assert_near(sr, 0.0, msg="empty sortino")

    # Mixed
    returns = [0.01] * 100 + [-0.005] * 100
    sr = sortino_ratio(returns)
    assert_true(sr > 0, "mixed positive sortino")


# ======================= Profit Factor =======================

def test_profit_factor():
    print("--- Profit Factor ---")
    pf = profit_factor([100, 200], [50, 50])
    assert_near(pf, 3.0, tol=1e-9, msg="300/100 = 3")

    pf = profit_factor([], [50])
    assert_near(pf, 0.0, tol=1e-9, msg="no gains")

    pf = profit_factor([100], [])
    assert_true(pf == float('inf') or pf == 0.0, "no losses inf")

    pf = profit_factor([], [])
    assert_near(pf, 0.0, tol=1e-9, msg="empty")

    # Bootstrap
    pf, lo, hi = profit_factor([100, 200], [50, 50], bootstrap=True, n_boot=1000, seed=42)
    assert_true(lo <= pf <= hi, "bootstrap CI contains pf")


# ======================= Max Consecutive =======================

def test_max_consecutive():
    print("--- Max Consecutive ---")
    t, f = max_consecutive([True, True, False, True, True, True, False])
    assert_true(t == 3, "max true = 3")
    assert_true(f == 1, "max false = 1")

    t, f = max_consecutive([])
    assert_true(t == 0 and f == 0, "empty = (0,0)")

    t, f = max_consecutive([True])
    assert_true(t == 1 and f == 0, "single true")

    t, f = max_consecutive([False])
    assert_true(t == 0 and f == 1, "single false")

    t, f = max_consecutive([True, True, True])
    assert_true(t == 3 and f == 0, "all true")

    t, f = max_consecutive([False, False, False, False])
    assert_true(t == 0 and f == 4, "all false")


# ======================= Kelly Criterion =======================

def test_kelly():
    print("--- Kelly Criterion ---")
    # 60% win, avg_win=2, avg_loss=1 → b=2, kelly = (0.6*2 - 0.4)/2 = 0.4
    k = kelly_criterion(0.6, 2.0, 1.0)
    assert_near(k, 0.4, msg="classic kelly")

    # 50% win, 1:1 odds → kelly = 0
    k = kelly_criterion(0.5, 1.0, 1.0)
    assert_near(k, 0.0, msg="breakeven kelly")

    # Edge: zero loss
    k = kelly_criterion(0.6, 2.0, 0.0)
    assert_near(k, 0.0, msg="zero loss kelly=0")

    # Negative kelly clamps to 0
    k = kelly_criterion(0.1, 1.0, 2.0)
    assert_near(k, 0.0, msg="negative kelly clamped")

    # Edge: zero avg_win
    k = kelly_criterion(0.6, 0.0, 1.0)
    assert_near(k, 0.0, msg="zero avg_win")


# ======================= VaR and CVaR =======================

def test_var_cvar():
    print("--- VaR and CVaR ---")
    returns = [-0.05, -0.03, -0.01, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07]
    var, cvar = var_cvar(returns, confidence=0.95)
    assert_true(var > 0, "VaR is positive (loss)")
    assert_true(cvar >= var, "CVaR >= VaR")

    # All positive returns
    returns = [0.01, 0.02, 0.03]
    var, cvar = var_cvar(returns)
    assert_true(var <= 0 or abs(var) < 0.02, "all positive VaR small")

    # Empty
    var, cvar = var_cvar([])
    assert_tuple_near((var, cvar), (0.0, 0.0), msg="empty VaR")

    # Single element
    var, cvar = var_cvar([-0.1])
    assert_near(var, 0.1, msg="single var")
    assert_near(cvar, 0.1, msg="single cvar")


# ======================= Herfindahl-Hirschman =======================

def test_hhi():
    print("--- Herfindahl-Hirschman Index ---")
    # Equal shares (fractions)
    hhi = herfindahl_hirschman([0.25, 0.25, 0.25, 0.25])
    assert_near(hhi, 0.25, tol=1e-9, msg="4 equal shares")

    # Monopoly
    hhi = herfindahl_hirschman([1.0])
    assert_near(hhi, 1.0, tol=1e-9, msg="monopoly")

    # Percentage format
    hhi = herfindahl_hirschman([25, 25, 25, 25])
    assert_near(hhi, 0.25, tol=1e-9, msg="percentages normalised")

    # Empty
    hhi = herfindahl_hirschman([])
    assert_near(hhi, 0.0, msg="empty HHI")

    # All zeros
    hhi = herfindahl_hirschman([0, 0, 0])
    assert_near(hhi, 0.0, msg="all zero HHI")

    # Two unequal shares
    hhi = herfindahl_hirschman([0.7, 0.3])
    assert_near(hhi, 0.58, tol=1e-9, msg="70/30 split")


# ======================= Run All =======================

if __name__ == "__main__":
    test_wilson()
    test_two_prop_z()
    test_welch()
    test_chi_square()
    test_bonferroni()
    test_bootstrap()
    test_sharpe()
    test_sortino()
    test_profit_factor()
    test_max_consecutive()
    test_kelly()
    test_var_cvar()
    test_hhi()

    print(f"\n{'='*50}")
    print(f"PASSED: {PASS}  FAILED: {FAIL}  TOTAL: {PASS+FAIL}")
    if FAIL == 0:
        print("All tests passed ✓")
    else:
        print(f"{FAIL} test(s) failed ✗")
        sys.exit(1)
