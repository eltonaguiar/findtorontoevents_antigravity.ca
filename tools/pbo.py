#!/usr/bin/env python3
"""
PBO (Probability of Backtest Overfitting) — thin wrapper for h037_forward_verification.py
===========================================================================================
Exports probability_of_backtest_overfitting() using the CSCV implementation
in tools/pbo_cscv.py (Bailey & Lopez de Prado 2014).
"""

from __future__ import annotations

import warnings

import numpy as np

import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from tools.pbo_cscv import compute_pbo as _compute_pbo


def probability_of_backtest_overfitting(
    returns: list[float] | np.ndarray | None = None,
    n_splits: int = 8,
    peer_matrix: np.ndarray | None = None,
) -> float:
    """
    Compute PBO (probability of backtest overfitting).

    A single return series CANNOT yield PBO: PBO is the probability that the
    in-sample-best candidate is out-of-sample-mediocre, which requires a set of
    competing candidates. Formerly this function fabricated a number by pairing
    the series with 1e-6-scale noise, and that fabricated PBO fed a kill switch.

    Args:
        returns: Legacy single series. Deprecated - returns nan.
        n_splits: Number of contiguous time-buckets for CSCV (even, >= 4).
        peer_matrix: (T, N) matrix of competing candidates. With N >= 2 and
            T >= n_splits this is the only path that produces a real value.

    Returns:
        PBO in [0, 1] (lower is better), nan when only a single series was
        supplied, or 1.0 when there is too little data (assume overfit, which
        is the safe direction).

    Raises:
        ValueError: if peer_matrix is not 2-D, or has fewer than 2 candidates.
    """
    if peer_matrix is not None:
        m = np.asarray(peer_matrix, dtype=float)
        if m.ndim != 2:
            raise ValueError(
                f"peer_matrix must be a 2-D (T, N) array of competing candidates, "
                f"got shape {m.shape}"
            )
        T, N = m.shape
        if N < 2:
            raise ValueError(f"peer_matrix needs N >= 2 candidate columns, got N={N}")

        if T < n_splits:
            return 1.0  # insufficient data -> assume overfit

        result = _compute_pbo(m, S=n_splits)
        pbo_val = result.get("pbo")
        if pbo_val is None:
            return 1.0
        return float(pbo_val)

    warnings.warn(
        "probability_of_backtest_overfitting() called with a single return series; "
        "PBO needs a peer_matrix of competing candidates. Returning nan.",
        DeprecationWarning,
        stacklevel=2,
    )
    return float("nan")