"""
Hierarchical Risk Parity (HRP) Allocator over Source-Systems
==============================================================

Implements López de Prado's HRP algorithm (2016) at the *source-system*
level, not the symbol level. The plan (Theme D) calls this out
explicitly:

    > Hierarchical Risk Parity over the source-systems, not the symbols
    > — so capital flows to ``kimi_riseoftheclaw`` and ``stocks_competition``
    > automatically and starves ``goldmine_stocks`` /
    > ``fast_stocks_competition``.

Why HRP and not mean-variance:
    * Mean-variance is famously unstable on noisy covariance matrices
      (Michaud's "error maximization"). HRP uses *only* hierarchical
      clustering of the correlation matrix and recursive bisection;
      it never inverts the covariance matrix.
    * Pro shops (AQR, Two Sigma, Bridgewater All-Weather) all use
      risk-parity-flavoured allocators for the top-of-stack risk
      budget — HRP is the academic state-of-the-art for that class.
    * The audit currently allocates picks "equally" across source-
      systems; HRP makes capital flow *automatically* to the systems
      with the best Sharpe-adjusted return contribution, no manual
      re-tuning required.

References
----------
* López de Prado, M. (2016) "Building Diversified Portfolios that
  Outperform Out-of-Sample", Journal of Portfolio Management 42(4).
* López de Prado, M. (2018) "Advances in Financial Machine Learning",
  ch. 16 (HRP).

Wiring plan
-----------
This module is an **opt-in sidecar** today. Target production caller
is ``alpha_engine/regime_position_sizer.py`` (Week 3 of the plan):
the regime sizer will call :func:`hrp_allocate` once per resolution
window with a per-source-system return matrix to derive the source-
level capital weights, then multiply through with the per-symbol vol-
target weight already produced by ``vol_targeted_sizer.py``.
"""

from __future__ import annotations

import math
from typing import Dict, List, Sequence

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:  # pragma: no cover
    np = None  # type: ignore
    _HAS_NUMPY = False


# ---------------------------------------------------------------------------
# Correlation / distance helpers (numpy-optional)
# ---------------------------------------------------------------------------
def _corr_to_distance(corr: "np.ndarray") -> "np.ndarray":
    """Convert correlation to the López de Prado distance metric.

    d_ij = sqrt(0.5 · (1 - rho_ij)). This is a proper metric
    (triangle inequality) suitable for hierarchical clustering.
    """
    return np.sqrt(0.5 * (1.0 - corr))


def _quasi_diag(link: "np.ndarray") -> List[int]:
    """Recursively unfold a SciPy-format linkage matrix into a leaf order.

    Implements López de Prado's ``getQuasiDiag``. We do not depend on
    scipy.cluster.hierarchy; this works with any (n-1, 4) array where
    the first two columns are cluster ids.
    """
    link = link.astype(int)
    n_items = link[-1, 3]
    sort_ix = [link[-1, 0], link[-1, 1]]
    while max(sort_ix) >= n_items:
        new_ix = []
        for i in sort_ix:
            if i < n_items:
                new_ix.append(i)
            else:
                row = link[i - n_items]
                new_ix.append(int(row[0]))
                new_ix.append(int(row[1]))
        sort_ix = new_ix
    return sort_ix


def _ivp_weights(cov_slice: "np.ndarray") -> "np.ndarray":
    """Inverse-variance portfolio weights for one cluster."""
    ivp = 1.0 / np.diag(cov_slice)
    return ivp / ivp.sum()


def _cluster_var(cov: "np.ndarray", items: List[int]) -> float:
    """Cluster variance under inverse-variance weighting."""
    cov_slice = cov[np.ix_(items, items)]
    w = _ivp_weights(cov_slice).reshape(-1, 1)
    return float((w.T @ cov_slice @ w).item())


def _bisect(
    cov: "np.ndarray", sort_ix: List[int]
) -> Dict[int, float]:
    """López de Prado's recursive bisection.

    Returns a dict ``{leaf_index: weight}`` summing to 1.0.
    """
    weights = {i: 1.0 for i in sort_ix}
    clusters = [sort_ix]
    while clusters:
        next_clusters: List[List[int]] = []
        for cluster in clusters:
            if len(cluster) <= 1:
                continue
            mid = len(cluster) // 2
            left = cluster[:mid]
            right = cluster[mid:]
            v_left = _cluster_var(cov, left)
            v_right = _cluster_var(cov, right)
            # Allocate inversely to cluster variance
            total = v_left + v_right
            if total <= 0:
                alpha = 0.5
            else:
                alpha = 1.0 - v_left / total
            for i in left:
                weights[i] *= alpha
            for i in right:
                weights[i] *= 1.0 - alpha
            next_clusters.append(left)
            next_clusters.append(right)
        clusters = next_clusters
    return weights


def _single_linkage(distance: "np.ndarray") -> "np.ndarray":
    """Pure-numpy single-linkage agglomerative clustering.

    Returns a SciPy-shaped linkage matrix ``(n-1, 4)`` where row k is
    ``[child_a, child_b, dist, n_items]``.
    """
    n = distance.shape[0]
    # Working copy with diagonal masked
    d = distance.astype(float).copy()
    np.fill_diagonal(d, np.inf)
    cluster_ids = list(range(n))
    sizes = {i: 1 for i in range(n)}
    next_id = n
    link_rows = []
    active = set(cluster_ids)
    # Map cluster_id -> row index in the working matrix
    while len(active) > 1:
        # Restrict to active rows/cols
        idxs = sorted(active)
        sub = d[np.ix_(idxs, idxs)]
        # Find argmin
        flat = sub.argmin()
        i_local, j_local = divmod(int(flat), len(idxs))
        ci = idxs[i_local]
        cj = idxs[j_local]
        if ci == cj:
            # Should not happen with diagonal=inf, but guard anyway
            d[ci, cj] = np.inf
            continue
        dist = float(sub[i_local, j_local])
        new_size = sizes[ci] + sizes[cj]
        link_rows.append([ci, cj, dist, new_size])
        # Merge: create new row/col by single-linkage min
        new_row = np.minimum(d[ci, :], d[cj, :])
        new_row[ci] = np.inf
        new_row[cj] = np.inf
        # Expand matrix to hold new cluster id
        d = np.pad(d, ((0, 1), (0, 1)), constant_values=np.inf)
        d[next_id, :len(new_row)] = new_row
        d[:len(new_row), next_id] = new_row
        # Deactivate merged clusters
        d[ci, :] = np.inf
        d[:, ci] = np.inf
        d[cj, :] = np.inf
        d[:, cj] = np.inf
        active.discard(ci)
        active.discard(cj)
        active.add(next_id)
        sizes[next_id] = new_size
        next_id += 1
    return np.array(link_rows, dtype=float)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def hrp_allocate(
    returns_by_source: Dict[str, Sequence[float]],
    *,
    min_observations: int = 20,
    floor_weight: float = 0.0,
) -> Dict[str, float]:
    """Compute HRP weights over a dict of {source_system: per-trade-returns}.

    Args:
        returns_by_source: dict mapping source-system name to a list of
            *aligned* per-period returns (e.g. daily PnL%). Sources with
            fewer than ``min_observations`` are dropped — their HRP
            weight returns 0.0.
        min_observations: minimum aligned return count to include a
            source. Default 20 keeps thin sources out of the allocator.
        floor_weight: optional minimum weight (e.g. 0.01) to keep tiny
            but non-zero exposure for monitoring; renormalised after
            flooring.

    Returns:
        ``{source_system: weight}`` with weights summing to 1.0 over
        included sources. Excluded (thin) sources receive weight 0.

    Edge cases:
        * If only one source qualifies, it gets weight 1.0.
        * If no sources qualify, returns ``{}``.
        * Numpy is required for clustering; without numpy this returns
          equal-weights over qualifying sources as a safe fallback
          (logged via the calling layer).
    """
    qualifying = {
        s: list(rs)
        for s, rs in returns_by_source.items()
        if len(rs) >= min_observations
    }
    excluded = {s: 0.0 for s in returns_by_source if s not in qualifying}

    if not qualifying:
        return excluded
    if len(qualifying) == 1:
        only = next(iter(qualifying))
        return {**excluded, only: 1.0}

    # All series must be the same length for a valid covariance matrix.
    # Truncate to the *shortest* series — the dashboard's resolution
    # window is rolling so this is the standard alignment.
    min_len = min(len(rs) for rs in qualifying.values())
    names = list(qualifying.keys())

    if not _HAS_NUMPY:  # pragma: no cover - safety fallback
        eq = 1.0 / len(names)
        return {**excluded, **{n: eq for n in names}}

    matrix = np.array(
        [qualifying[n][-min_len:] for n in names], dtype=float
    )
    # Variance along each series — guard against zero-variance sources
    variances = matrix.var(axis=1)
    if np.any(variances == 0):
        # Drop zero-variance sources (constant-PnL series are degenerate)
        keep = variances > 0
        if keep.sum() == 0:
            eq = 1.0 / len(names)
            return {**excluded, **{n: eq for n in names}}
        matrix = matrix[keep]
        names = [n for n, k in zip(names, keep) if k]
        for n, k in zip(qualifying, keep):
            if not k:
                excluded[n] = 0.0
        if len(names) == 1:
            return {**excluded, names[0]: 1.0}

    # Correlation -> distance -> linkage -> quasi-diag -> bisection
    corr = np.corrcoef(matrix)
    # Numerical safety
    corr = np.clip(corr, -1.0, 1.0)
    dist = _corr_to_distance(corr)
    link = _single_linkage(dist)
    sort_ix = _quasi_diag(link)
    cov = np.cov(matrix)
    weights_idx = _bisect(cov, sort_ix)

    raw = {names[i]: w for i, w in weights_idx.items()}
    # Apply floor and renormalise
    if floor_weight > 0:
        raw = {n: max(w, floor_weight) for n, w in raw.items()}
    total = sum(raw.values())
    if total <= 0:
        eq = 1.0 / len(names)
        return {**excluded, **{n: eq for n in names}}
    final = {n: w / total for n, w in raw.items()}
    return {**excluded, **final}


__all__ = ["hrp_allocate"]
