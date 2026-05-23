"""Hierarchical Risk Parity (HRP) allocator -- Lopez de Prado (2016).

Allocates capital across source-systems (not individual symbols) based on
their realized risk characteristics, using hierarchical clustering on a
robust correlation matrix and recursive top-down inverse-variance bisection.

Key advantages over classical Markowitz:
1. No matrix inversion (stable with collinear assets).
2. Respects the hierarchical structure of source-systems (e.g. crypto
   momentum and crypto mean-reversion cluster together before competing
   with forex trend).
3. Out-of-sample stability is dramatically higher (Lopez de Prado 2016
   shows turnover ~1/3 of CLA and Sharpe within noise).

Also includes ``sharpe_equalized_sizing`` for AQR-style volatility-targeting
position construction: size = (target_vol / forecast_vol) * (edge / vol).

This module is OPT-IN.  Nothing in the production pick-generation path
imports it yet.  A follow-up PR will wire ``hrp_allocate_by_sharpe`` into
the daily portfolio-rebalance cron and ``sharpe_equalized_sizing`` into
``regime_position_sizer.py``.

Public API
----------
hrp_allocate(returns_df, asset_names=None) -> dict[str, float]
hrp_allocate_by_sharpe(source_systems, lookback_days=90) -> dict[str, float]
sharpe_equalized_sizing(expected_edge, forecast_vol, target_vol=0.10) -> float

Example
-------
>>> import numpy as np
>>> import pandas as pd
>>> dates = pd.date_range('2024-01-01', periods=252)
>>> returns = pd.DataFrame({
...     'crypto_momentum': np.random.randn(252) * 0.02,
...     'crypto_mr': np.random.randn(252) * 0.015,
...     'forex_trend': np.random.randn(252) * 0.01,
... }, index=dates)
>>> weights = hrp_allocate(returns)
>>> print({k: f"{v:.3f}" for k, v in weights.items()})
"""

from __future__ import annotations

import json
import logging
import math
import os
from typing import Any

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage
from scipy.spatial.distance import squareform

logger = logging.getLogger(__name__)

__all__ = [
    "hrp_allocate",
    "hrp_allocate_by_sharpe",
    "sharpe_equalized_sizing",
    "_get_correlation_matrix",
    "_get_distance_matrix",
    "_quasi_diagonal",
    "_get_cluster_var",
    "_recursive_bisection",
]

# ---------------------------------------------------------------------------
# 1. Correlation Matrix (robust)
# ---------------------------------------------------------------------------


def _get_correlation_matrix(returns_matrix: np.ndarray) -> np.ndarray:
    """Compute a robust correlation matrix from a returns matrix.

    Uses the Pearson correlation with pairwise-complete observations.
    Any NaN columns (assets with no overlapping data) are filled with
    zeros -- these assets will cluster neutrally and receive small weights
    via the recursive bisection.

    Parameters
    ----------
    returns_matrix : np.ndarray, shape (T, N)
        Periodic returns for N assets over T observations.

    Returns
    -------
    np.ndarray, shape (N, N)
        Symmetric correlation matrix with ones on the diagonal.
    """
    M = np.asarray(returns_matrix, dtype=np.float64)
    if M.ndim != 2:
        raise ValueError(f"Expected 2-D returns matrix, got shape {M.shape}")

    # pandas handles NaN gracefully with pairwise-complete
    df = pd.DataFrame(M)
    corr = df.corr(method="pearson").values

    # Fill NaN (no overlapping observations) with 0 => neutral correlation
    corr = np.nan_to_num(corr, nan=0.0, posinf=0.0, neginf=0.0)

    # Ensure exact diagonal = 1.0
    np.fill_diagonal(corr, 1.0)
    return corr


# ---------------------------------------------------------------------------
# 2. Distance Matrix
# ---------------------------------------------------------------------------


def _get_distance_matrix(corr_matrix: np.ndarray) -> np.ndarray:
    """Convert correlation matrix to distance matrix.

    Distance = sqrt(0.5 * (1 - rho))

    This is the standard metric used in Lopez de Prado HRP so that:
    * rho =  1  => distance = 0   (identical assets)
    * rho =  0  => distance = sqrt(0.5) ~ 0.707 (orthogonal)
    * rho = -1  => distance = 1    (perfect anti-correlated)

    Parameters
    ----------
    corr_matrix : np.ndarray, shape (N, N)
        Symmetric correlation matrix.

    Returns
    -------
    np.ndarray, shape (N, N)
        Symmetric distance matrix with zeros on the diagonal.
    """
    corr = np.asarray(corr_matrix, dtype=np.float64)
    # Clip correlation to [-1, 1] to avoid numerical issues
    corr = np.clip(corr, -1.0, 1.0)
    dist = np.sqrt(0.5 * (1.0 - corr))
    np.fill_diagonal(dist, 0.0)
    return dist


# ---------------------------------------------------------------------------
# 3. Quasi-Diagonalization (cluster ordering)
# ---------------------------------------------------------------------------


def _quasi_diagonal(linkage_matrix: np.ndarray) -> list[int]:
    """Sort assets by hierarchical clustering for HRP.

    Recursively descends the linkage tree and returns the leaf order
    such that similar assets are adjacent.  This ordering is the
    "quasi-diagonal" reordering that makes the covariance matrix
    approximately block-diagonal.

    Parameters
    ----------
    linkage_matrix : np.ndarray
        SciPy linkage matrix from ``scipy.cluster.hierarchy.linkage``.

    Returns
    -------
    list[int]
        Ordered list of original asset indices.

    References
    ----------
    * Lopez de Prado, M. (2016). Building Diversified Portfolios that
      Outperform Out-of-Sample. *Journal of Portfolio Management*.
    """
    # The linkage matrix encodes merges as [idx1, idx2, dist, count]
    # Leaf nodes are 0..n-1; internal nodes are n..2n-2
    n_obs = linkage_matrix.shape[0] + 1

    def _get_leaves(node: int) -> list[int]:
        if node < n_obs:
            return [int(node)]
        left = int(linkage_matrix[node - n_obs, 0])
        right = int(linkage_matrix[node - n_obs, 1])
        return _get_leaves(left) + _get_leaves(right)

    root = 2 * n_obs - 2
    return _get_leaves(root)


# ---------------------------------------------------------------------------
# 4. Cluster Variance
# ---------------------------------------------------------------------------


def _get_cluster_var(cov_matrix: np.ndarray, cluster_items: list[int]) -> float:
    """Compute the variance of a cluster (inverse-variance weight).

    Given a covariance sub-matrix for the assets in *cluster_items*,
    computes the variance of the minimum-variance portfolio formed by
    equal-RP weighting within the cluster.

    Parameters
    ----------
    cov_matrix : np.ndarray, shape (N, N)
        Full covariance matrix.
    cluster_items : list[int]
        Indices of assets in the cluster.

    Returns
    -------
    float
        Cluster variance.  Higher variance => lower allocation.
    """
    if not cluster_items:
        return 0.0
    sub_cov = cov_matrix[np.ix_(cluster_items, cluster_items)]
    # Inverse-variance weights within the cluster
    ivp = 1.0 / np.diag(sub_cov)
    ivp = ivp / np.sum(ivp)
    # Portfolio variance = w' C w
    return float(np.dot(ivp, np.dot(sub_cov, ivp)))


# ---------------------------------------------------------------------------
# 5. Recursive Bisection (HRP weight allocation)
# ---------------------------------------------------------------------------


def _recursive_bisection(
    cov_matrix: np.ndarray,
    sorted_items: list[int],
) -> dict[int, float]:
    """Allocate weights via recursive bisection along the cluster tree.

    At each split, compute the cluster variance of the left and right
    halves, then allocate capital in inverse proportion to variance:
    alpha = V_right / (V_left + V_right).

    This is the core of HRP -- it never inverts the covariance matrix,
    making it numerically stable even with >100 correlated assets.

    Parameters
    ----------
    cov_matrix : np.ndarray, shape (N, N)
        Full covariance matrix.
    sorted_items : list[int]
        Quasi-diagonal ordering from ``_quasi_diagonal``.

    Returns
    -------
    dict[int, float]
        Map from original asset index to HRP weight (sums to 1.0).
    """
    weights = np.ones(len(sorted_items), dtype=np.float64)

    # Working list of (start, end) slices that need bisection
    clusters: list[tuple[int, int]] = [(0, len(sorted_items))]

    while clusters:
        start, end = clusters.pop()
        if end - start <= 1:
            continue  # leaf node

        mid = (start + end) // 2
        left_items = sorted_items[start:mid]
        right_items = sorted_items[mid:end]

        v_left = _get_cluster_var(cov_matrix, left_items)
        v_right = _get_cluster_var(cov_matrix, right_items)

        denom = v_left + v_right
        if denom < 1e-12:
            alpha = 0.5
        else:
            alpha = v_right / denom  # allocation to left branch

        weights[start:mid] *= alpha
        weights[mid:end] *= (1.0 - alpha)

        clusters.append((start, mid))
        clusters.append((mid, end))

    return {sorted_items[i]: float(weights[i]) for i in range(len(sorted_items))}


# ---------------------------------------------------------------------------
# 6. Main Entry Point: HRP Allocate
# ---------------------------------------------------------------------------


def hrp_allocate(
    returns_df: pd.DataFrame,
    asset_names: list[str] | None = None,
) -> dict[str, float]:
    """Compute HRP weights from a DataFrame of asset returns.

    Parameters
    ----------
    returns_df : pd.DataFrame, shape (T, N)
        Periodic returns for N assets over T observations.  Column names
        are used as asset identifiers unless *asset_names* is provided.
        NaN values are handled via pairwise-complete correlation.
    asset_names : list[str] or None, default None
        Optional override for the asset names in the output dict.  Must
        match the number of columns in *returns_df*.

    Returns
    -------
    dict[str, float]
        Map from asset name to HRP weight.  Weights sum to 1.0 and are
        all non-negative.

    Raises
    ------
    ValueError
        If *returns_df* has fewer than 2 columns or 2 rows.
    """
    if returns_df.shape[1] < 2:
        raise ValueError(f"HRP needs >= 2 assets, got {returns_df.shape[1]}")
    if len(returns_df) < 2:
        raise ValueError(f"HRP needs >= 2 observations, got {len(returns_df)}")

    names = asset_names if asset_names is not None else list(returns_df.columns)
    if len(names) != returns_df.shape[1]:
        raise ValueError(
            f"asset_names length {len(names)} != columns {returns_df.shape[1]}"
        )

    returns_matrix = returns_df.values.astype(np.float64)

    # 1. Correlation -> Distance -> Linkage
    corr = _get_correlation_matrix(returns_matrix)
    dist = _get_distance_matrix(corr)

    # Convert square distance matrix to condensed form for linkage
    dist_condensed = squareform(dist, checks=False)
    link = linkage(dist_condensed, method="single")

    # 2. Quasi-diagonal ordering
    sorted_items = _quasi_diagonal(link)

    # 3. Covariance matrix
    cov = pd.DataFrame(returns_matrix).cov().values
    cov = np.nan_to_num(cov, nan=0.0, posinf=0.0, neginf=0.0)
    np.fill_diagonal(cov, np.diag(cov).clip(min=1e-12))  # ensure positive variance

    # 4. Recursive bisection
    raw_weights = _recursive_bisection(cov, sorted_items)

    # 5. Normalize and return
    w = np.array([raw_weights[i] for i in range(len(names))], dtype=np.float64)
    w_sum = w.sum()
    if w_sum > 0:
        w = w / w_sum
    else:
        w = np.ones(len(names)) / len(names)

    return {names[i]: float(w[i]) for i in range(len(names))}


# ---------------------------------------------------------------------------
# 7. Convenience: HRP by realized Sharpe from dashboard_data.json
# ---------------------------------------------------------------------------


def hrp_allocate_by_sharpe(
    source_systems: list[str] | None = None,
    lookback_days: int = 90,
    dashboard_path: str | None = None,
) -> dict[str, float]:
    """Fetch returns from dashboard_data.json and allocate by realized Sharpe.

    This is the production convenience function.  It reads the daily
    P&L snapshot from the audit dashboard JSON, builds a returns matrix
    for the requested source-systems, and runs HRP allocation.

    Parameters
    ----------
    source_systems : list[str] or None, default None
        Source-system names to include (e.g. ``['openclaw', 'mimo',
        'uesp', 'consensus']``).  None => use all systems found in the
        dashboard data.
    lookback_days : int, default 90
        Number of trailing days to use for the returns history.
    dashboard_path : str or None, default None
        Path to ``dashboard_data.json``.  None => ``DASHBOARD_DATA_PATH``
        env var, then ``./dashboard_data.json``.

    Returns
    -------
    dict[str, float]
        HRP weights for each source-system.  Falls back to equal weights
        if the dashboard file is missing or data is insufficient.
    """
    if dashboard_path is None:
        dashboard_path = os.environ.get("DASHBOARD_DATA_PATH", "./dashboard_data.json")

    try:
        with open(dashboard_path, "r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("hrp_by_sharpe: cannot read dashboard: %s", exc)
        systems = source_systems or ["openclaw", "mimo", "uesp", "consensus"]
        n = len(systems)
        return {s: 1.0 / n for s in systems}

    # Extract daily returns per source-system from dashboard
    history = data.get("source_system_returns", {})
    systems = source_systems or list(history.keys())

    if not systems:
        logger.warning("hrp_by_sharpe: no source systems found")
        return {}

    # Build returns DataFrame
    max_len = lookback_days
    returns_dict: dict[str, list[float]] = {}
    for sys in systems:
        series = history.get(sys, [])
        if isinstance(series, list) and len(series) > 0:
            returns_dict[sys] = [float(x) for x in series[-max_len:]]
        else:
            returns_dict[sys] = [0.0] * max_len  # neutral placeholder

    # Normalize lengths
    min_len = min(len(v) for v in returns_dict.values()) if returns_dict else 0
    if min_len < 2:
        logger.warning("hrp_by_sharpe: insufficient history, using equal weights")
        n = len(systems)
        return {s: 1.0 / n for s in systems}

    returns_df = pd.DataFrame({k: v[:min_len] for k, v in returns_dict.items()})

    try:
        return hrp_allocate(returns_df, asset_names=systems)
    except Exception as exc:
        logger.warning("hrp_by_sharpe: allocation failed: %s; using equal weights", exc)
        n = len(systems)
        return {s: 1.0 / n for s in systems}


# ---------------------------------------------------------------------------
# 8. Sharpe-Equalized Sizing (AQR-style vol targeting)
# ---------------------------------------------------------------------------


def sharpe_equalized_sizing(
    expected_edge: float,
    forecast_vol: float,
    target_vol: float = 0.10,
) -> float:
    """AQR-style volatility-targeted position sizing.

    position_size = (target_vol / forecast_vol) * (expected_edge / vol)

    This is the standard institutional formula for converting an alpha
    forecast into a dollar position.  It scales the position so that:
    1. The portfolio volatility matches the target (e.g. 10% annual).
    2. Positions are proportional to the expected Sharpe (edge / vol).

    Parameters
    ----------
    expected_edge : float
        Expected return (alpha) for the trade, in the same units as
        *forecast_vol* (typically annualized decimal, e.g. 0.05 for 5%).
    forecast_vol : float
        Predicted volatility of the trade, same units as *expected_edge*.
        Must be strictly positive.
    target_vol : float, default 0.10
        Portfolio-level target volatility (annualized decimal).
        Typical institutional values: 0.05 (conservative), 0.10 (standard),
        0.15 (aggressive).

    Returns
    -------
    float
        Position size as a fraction of capital.  Returns 0.0 if inputs
        are degenerate (non-positive volatility or non-finite edge).

    References
    ----------
    * Asness, C. S., et al. (2013). The Volatility Targeting Effect.
      *AQR Working Paper*.
    * Lopez de Prado, M. (2018). *Advances in Financial Machine Learning*.
      Wiley.  Chapter 10.
    """
    if not np.isfinite(expected_edge) or not np.isfinite(forecast_vol):
        logger.debug("sharpe_equalized_sizing: non-finite input, returning 0.0")
        return 0.0
    if forecast_vol <= 1e-12:
        logger.debug("sharpe_equalized_sizing: vol too small, returning 0.0")
        return 0.0
    if target_vol <= 0.0:
        logger.debug("sharpe_equalized_sizing: target_vol <= 0, returning 0.0")
        return 0.0

    vol_scalar = target_vol / forecast_vol
    edge_scalar = expected_edge / forecast_vol
    return float(vol_scalar * edge_scalar)
