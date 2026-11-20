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
    peer_matrix: np.ndarray | list[list[float]] | None = None,
) -> float:
    """PBO for a candidate set. Returns nan unless ``peer_matrix`` is supplied.

    .. deprecated:: 2026-11-20
        Calling this with a single return series is DEPRECATED and returns
        ``nan``. PBO (Bailey & Lopez de Prado 2014) is the probability that the
        in-sample-best configuration underperforms out-of-sample, computed
        across a set of genuinely competing candidate configurations. It is not
        a property of one return series.

        This function used to embed the series as column 0 of a ``(T, 2)``
        matrix and fill column 1 with ``1e-6``-scale noise. That second column
        is not a candidate configuration -- it is an almost-constant zero line,
        so the strategy dominated in-sample by construction and the "PBO" that
        came out measured only the out-of-sample SIGN of the strategy. That is
        roughly a coin flip, reported to the caller as a robustness statistic
        and consumed by a kill switch.

    Args:
        returns: Unused for real PBO. Accepted for backward compatibility.
        n_splits: Number of contiguous time-buckets for CSCV (even, >= 4).
        peer_matrix: ``(T, N)`` array of per-period returns for N genuinely
            competing candidates. When supplied, real PBO is computed.

    Returns:
        PBO in [0, 1] when ``peer_matrix`` is given; otherwise ``nan``.
    """
    if peer_matrix is None:
        warnings.warn(
            "probability_of_backtest_overfitting() called with a single "
            "return series: PBO is not estimable from one series and nan is "
            "returned. Pass peer_matrix=(T, N) of competing candidates, or "
            "call tools.pbo_cscv.compute_pbo directly.",
            DeprecationWarning,
            stacklevel=2,
        )
        return float("nan")

    mat = np.asarray(peer_matrix, dtype=float)
    if mat.ndim != 2 or mat.shape[1] < 2:
        raise ValueError(
            f"peer_matrix must be (T, N) with N >= 2 competing candidates, "
            f"got shape {mat.shape}"
        )
    if mat.shape[0] < n_splits:
        return 1.0  # insufficient data -> assume overfit

    result = _compute_pbo(mat, S=n_splits)
    pbo_val = result.get("pbo")
    return float(pbo_val) if pbo_val is not None else float("nan")