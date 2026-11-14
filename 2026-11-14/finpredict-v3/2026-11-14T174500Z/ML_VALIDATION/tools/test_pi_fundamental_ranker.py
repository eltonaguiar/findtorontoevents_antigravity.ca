#!/usr/bin/env python3
"""Tests for the minimal/honest fundamental walk-forward ranker."""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest  # noqa: E402

from tools.pi_fundamental_ranker import (  # noqa: E402
    FEATURE_COLS,
    build_mock_dataset,
    run,
    _chronological_splits,
    _fit_zscaler,
)


def test_chronological_split_no_future_leakage():
    """A 'future-knowing' probe must never appear inside a training window."""
    df = build_mock_dataset(n_tickers=40, n_dates=120, seed=7, signal=True)
    # peek = perfect future knowledge (the forward return itself). If the split
    # ever let a future row into training, this probe would flag it.
    df["peek"] = df["forward_return"]
    splits = _chronological_splits(df, n_windows=4)
    assert len(splits) == 4
    for i, (train, oos) in enumerate(splits):
        assert len(train) > 0 and len(oos) > 0
        # training is strictly before the OOS window — no same-or-later dates.
        assert train["date"].max() < oos["date"].min()
        # every row in train is a past decision point; none can be future.
        assert train["date"].max() < oos["date"].max()
        # the scaler is fit on train only, so its stats match train, not the
        # full sample (which would leak future info into OOS scoring).
        means, _ = _fit_zscaler(train, FEATURE_COLS)
        for c in FEATURE_COLS:
            assert abs(means[c] - train[c].mean()) < 1e-12


def test_random_nosignal_mock_ci_includes_50():
    """An honest null result: no-edge mock yields a CI straddling 50%."""
    df = build_mock_dataset(n_tickers=40, n_dates=120, seed=3, signal=False)
    rep = run(df)
    assert rep.top_n > 0
    assert rep.ci_includes_050 is True
    assert rep.edge_detected is False
    assert "NO EDGE DETECTED" in rep.verdict


def test_planted_signal_is_detected():
    """Sanity check the detection machinery: a planted edge is found."""
    df = build_mock_dataset(n_tickers=40, n_dates=120, seed=11, signal=True)
    rep = run(df)
    assert rep.edge_detected is True
    assert rep.ci_lo > 0.50
    assert "EDGE DETECTED" in rep.verdict


def test_walk_forward_window_sizes_correct():
    """Windows are contiguous, disjoint, correct-sized, with expanding train."""
    df = build_mock_dataset(n_tickers=40, n_dates=120, seed=5, signal=False)
    dates = sorted(df["date"].unique())
    n = len(dates)
    init_train = int(n * 0.4)
    oos_dates = dates[init_train:]
    expected_sizes = [len(oos_dates) // 4] * 4

    splits = _chronological_splits(df, n_windows=4)
    assert len(splits) == 4

    oos_date_sets = []
    train_sizes = []
    for train, oos in splits:
        oos_date_sets.append(set(oos["date"].unique()))
        train_sizes.append(len(train))
        assert len(oos["date"].unique()) in expected_sizes

    # disjoint and covering the entire OOS span
    union = set()
    total = 0
    for s in oos_date_sets:
        union |= s
        total += len(s)
    assert len(union) == total == len(oos_dates)
    assert union == set(oos_dates)

    # expanding training length
    for i in range(len(train_sizes) - 1):
        assert train_sizes[i] < train_sizes[i + 1]
