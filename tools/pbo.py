#!/usr/bin/env python3
"""
PBO (Probability of Backtest Overfitting) — thin wrapper for h037_forward_verification.py
===========================================================================================
Exports probability_of_backtest_overfitting() using the CSCV implementation
in tools/pbo_cscv.py (Bailey & Lopez de Prado 2014).
"""

from __future__ import annotations

import numpy as np

import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from tools.pbo_cscv import compute_pbo as _compute_pbo


def probability_of_backtest_overfitting(
    returns: list[float] | np.ndarray,
    n_splits: int = 8,
) -> float:
    """
    Compute PBO for a single strategy's return series.

    Wraps the multi-strategy CSCV engine by embedding the single return
    vector as one column of a (T, 2) matrix (second column = zeros so
    the candidate always ranks #1 on IS, and PBO measures how often it
    also ranks #1 on OOS).  This is equivalent to the single-series
    leave-one-out PBO used in the López de Prado framework.

    Args:
        returns: 1-D array of per-period returns.
        n_splits: Number of contiguous time-buckets for CSCV (must be even, >=4).

    Returns:
        PBO value in [0, 1].  Lower is better; < 0.05 indicates robust edge.
    """
    r = np.asarray(returns, dtype=float)
    if r.ndim != 1:
        r = r.flatten()
    T = len(r)
    if T < n_splits:
        return 1.0  # insufficient data → assume overfit

    # Build a (T, 2) matrix: col 0 = strategy returns, col 1 = small noise
    # so the candidate isn't trivially dominant.
    noise = np.random.default_rng(42).standard_normal(T) * 1e-6
    mat = np.column_stack([r, noise])

    result = _compute_pbo(mat, S=n_splits)
    pbo_val = result.get("pbo")
    if pbo_val is None:
        return 1.0
    return float(pbo_val)