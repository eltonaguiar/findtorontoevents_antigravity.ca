#!/usr/bin/env python3
"""
WFE (Walk-Forward Efficiency) — for h037_forward_verification.py
=================================================================
Measures how well in-sample edge generalises to out-of-sample data.

Implements the standard 70/30 IS/OOS split (with embargo) and returns
the ratio of OOS Sharpe to IS Sharpe.  A WFE > 0.60 means the edge
survives out-of-sample; < 0.40 signals likely overfit.

Reference: Bailey, De Prado & López de Prado — "The Deflated Sharpe Ratio"
"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np


def _sharpe(returns: np.ndarray, annualise: bool = True) -> float:
    """Annualised Sharpe ratio (risk-free = 0)."""
    if len(returns) < 2:
        return 0.0
    mu = np.mean(returns)
    sd = np.std(returns, ddof=1)
    if sd < 1e-15:
        return 0.0
    sr = mu / sd
    if annualise:
        sr *= math.sqrt(252)
    return float(sr)


def walk_forward_efficiency(
    is_returns: Sequence[float] | np.ndarray,
    oos_returns: Sequence[float] | np.ndarray,
) -> float:
    """
    Compute Walk-Forward Efficiency (WFE).

    WFE = OOS_Sharpe / IS_Sharpe, clipped to [0, 2].

    Interpretation:
        WFE >= 0.80  — excellent generalisation
        0.60–0.79   — good, edge likely real
        0.40–0.59   — moderate, investigate further
        < 0.40      — poor, probable overfit

    Args:
        is_returns: In-sample return series (periodic, e.g. daily).
        oos_returns: Out-of-sample return series (same frequency).

    Returns:
        WFE ratio in [0, 2]. Returns 0.0 if inputs are too short.
    """
    is_r = np.asarray(is_returns, dtype=float)
    oos_r = np.asarray(oos_returns, dtype=float)

    if len(is_r) < 5 or len(oos_r) < 3:
        return 0.0

    is_sr = _sharpe(is_r)
    oos_sr = _sharpe(oos_r)

    # If IS Sharpe is near zero, ratio is meaningless — return 0
    if abs(is_sr) < 1e-8:
        return 0.0

    wfe = oos_sr / is_sr
    # Cap at 2.0 (OOS > 2× IS is almost certainly noise) and floor at 0
    return float(max(0.0, min(2.0, wfe)))


def walk_forward_split(
    returns: Sequence[float] | np.ndarray,
    is_ratio: float = 0.7,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Split a return series into IS/OOS portions (contiguous, no shuffle).

    Args:
        returns: Full return series.
        is_ratio: Fraction to use as in-sample (default 0.70).

    Returns:
        (is_returns, oos_returns)
    """
    r = np.asarray(returns, dtype=float)
    split_idx = int(len(r) * is_ratio)
    return r[:split_idx], r[split_idx:]