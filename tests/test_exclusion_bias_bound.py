"""Deterministic tests for exclusion_bias_bound (no DB, no network)."""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from alpha_engine.audit3_tribunal import exclusion_bias_bound  # noqa: E402


def _rows(pnls):
    return [{"pnl_pct": p, "asset_class": "CRYPTO"} for p in pnls]


def test_returns_none_when_nothing_is_unscored():
    assert exclusion_bias_bound(_rows([1.0, 2.0]), 0) is None
    assert exclusion_bias_bound(_rows([1.0, 2.0]), None) is None


def test_returns_none_for_an_empty_scored_book():
    # Unscored rows with no scored distribution to anchor against: no bound
    # is computable, and inventing one would be worse than saying nothing.
    assert exclusion_bias_bound([], 100) is None


def test_sign_is_stable_when_the_scored_book_is_clearly_profitable():
    b = exclusion_bias_bound(_rows([5.0, 6.0, 7.0, 8.0]), 4)
    assert b is not None
    assert b["sign_stable"] is True
    assert b["straddles_zero"] is False


def test_sign_is_stable_when_the_scored_book_is_clearly_losing():
    b = exclusion_bias_bound(_rows([-5.0, -6.0, -7.0, -8.0]), 4)
    assert b is not None
    assert b["sign_stable"] is True
    assert b["straddles_zero"] is False


def test_a_thin_book_straddles_zero():
    # Mean +0.1 with a wide spread: a tail-quantile assumption for the missing
    # rows flips the sign, so the headline is not robust.
    b = exclusion_bias_bound(_rows([-10.0, -2.0, 3.0, 9.5]), 50)
    assert b is not None
    assert b["straddles_zero"] is True
    assert b["sign_stable"] is False


def test_range_brackets_the_scored_mean_only_when_scenarios_differ():
    b = exclusion_bias_bound(_rows([-4.0, 0.0, 4.0]), 3)
    lo, hi = b["combined_mean_range_pct"]
    assert lo <= hi
    # Each scenario is the pooled mean of scored + assumed unscored rows, so
    # every one sits between the scored mean and the assumed value.
    for s in b["scenarios"]:
        assert min(0.0, s["assumed_unscored_net_pct"]) - 1e-9 <= \
            s["combined_mean_net_pct"] <= max(0.0, s["assumed_unscored_net_pct"]) + 1e-9


def test_more_unscored_rows_pull_the_range_toward_the_assumption():
    rows = _rows([-4.0, 0.0, 4.0])
    small = exclusion_bias_bound(rows, 1)
    large = exclusion_bias_bound(rows, 100)
    # With more missing mass, the combined mean moves further from the scored
    # mean (+0.0 here) toward the assumed quantile value.
    assert abs(large["scenarios"][-1]["delta_pct"]) > \
        abs(small["scenarios"][-1]["delta_pct"])


def test_rows_without_numeric_pnl_are_ignored():
    rows = _rows([1.0, 3.0]) + [{"pnl_pct": None}, {"pnl_pct": "n/a"}]
    b = exclusion_bias_bound(rows, 2)
    assert b["scored_n"] == 2
    assert b["scored_mean_net_pct"] != 0
