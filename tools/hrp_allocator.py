"""Hierarchical Risk Parity (HRP) allocator — Lopez de Prado (2016).

Extends PR #301's naive inverse-volatility allocator to account for
correlations between asset classes via hierarchical clustering.

Algorithm (Lopez de Prado 2016, "Building Diversified Portfolios That
Outperform Out-of-Sample"):
  1. Compute correlation matrix of asset-class returns
  2. Convert to distance matrix: d_ij = sqrt(0.5 * (1 - corr_ij))
  3. Hierarchical clustering (single-linkage) to produce a dendrogram
  4. Quasi-diagonalize: reorder the cov matrix by dendrogram leaves
  5. Recursive bisection: split into two halves, allocate inverse-variance
     weights, descend recursively

Why HRP over naive inverse-vol:
  Naive inverse-vol treats all classes independently. When CRYPTO and EQUITY
  are correlated (e.g., risk-off sells both), naive gives them too much weight.
  HRP clusters correlated classes together and assigns them a shared allocation
  budget, then splits within the cluster.

Implementation is pure-Python + no scipy (uses single-linkage clustering
manually). Runs in O(n^3) which is fine for n <= ~100 asset classes/strategies.

Reference: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2708678
"""
from __future__ import annotations

import math
import statistics
from collections import defaultdict


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = min(len(xs), len(ys))
    if n < 2:
        return 0.0
    mx = sum(xs[:n]) / n
    my = sum(ys[:n]) / n
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    dx = math.sqrt(sum((xs[i] - mx) ** 2 for i in range(n)))
    dy = math.sqrt(sum((ys[i] - my) ** 2 for i in range(n)))
    if dx == 0 or dy == 0:
        return 0.0
    return num / (dx * dy)


def correlation_matrix(returns_by_asset: dict[str, list[float]]) -> tuple[list[str], list[list[float]]]:
    """Pearson correlation matrix. Returns (asset_order, matrix)."""
    assets = sorted(returns_by_asset.keys())
    m = [[0.0] * len(assets) for _ in assets]
    for i, a in enumerate(assets):
        for j, b in enumerate(assets):
            m[i][j] = 1.0 if i == j else _pearson(returns_by_asset[a], returns_by_asset[b])
    return assets, m


def _distance_matrix(corr: list[list[float]]) -> list[list[float]]:
    n = len(corr)
    d = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            d[i][j] = math.sqrt(0.5 * max(0.0, 1.0 - corr[i][j]))
    return d


def _single_linkage_order(dist: list[list[float]]) -> list[int]:
    """Return leaf order from single-linkage hierarchical clustering.

    Simple agglomerative clustering; merges closest pairs iteratively.
    Quasi-diagonalization step from LdP paper.
    """
    n = len(dist)
    # Initialize each element as its own cluster
    clusters = [[i] for i in range(n)]
    cluster_dist = [row[:] for row in dist]  # copy

    while len(clusters) > 1:
        # Find closest pair
        best = (None, None, float("inf"))
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                if cluster_dist[i][j] < best[2]:
                    best = (i, j, cluster_dist[i][j])
        i, j, _ = best
        # Merge j into i
        clusters[i] = clusters[i] + clusters[j]
        clusters.pop(j)
        # Update distances: single linkage = min over pair
        new_dist = [[0.0] * len(clusters) for _ in clusters]
        for a in range(len(clusters)):
            for b in range(len(clusters)):
                if a == b:
                    new_dist[a][b] = 0.0
                    continue
                ca = clusters[a]
                cb = clusters[b]
                min_d = min(dist[x][y] for x in ca for y in cb)
                new_dist[a][b] = min_d
        cluster_dist = new_dist

    return clusters[0]


def _inverse_variance_weights(variances: list[float]) -> list[float]:
    inv = [1.0 / v if v > 0 else 0.0 for v in variances]
    total = sum(inv)
    if total == 0:
        return [1.0 / len(variances)] * len(variances)
    return [x / total for x in inv]


def _recursive_bisection(variances: list[float]) -> list[float]:
    """Recursive bisection of the (already quasi-diagonalized) variance list.

    At each step: split list in half, allocate inverse-variance weights to
    each half, scale children by parent weight. Recurse.
    """
    n = len(variances)
    weights = [1.0] * n

    def _recurse(idx_start: int, idx_end: int, parent_weight: float):
        if idx_end - idx_start <= 1:
            weights[idx_start] = parent_weight
            return
        mid = (idx_start + idx_end) // 2
        left = variances[idx_start:mid]
        right = variances[mid:idx_end]
        v_left = sum(_inverse_variance_weights(left)[k] * left[k]
                     for k in range(len(left)))
        v_right = sum(_inverse_variance_weights(right)[k] * right[k]
                      for k in range(len(right)))
        total_v = v_left + v_right
        if total_v == 0:
            w_left = w_right = 0.5
        else:
            w_left = 1.0 - v_left / total_v
            w_right = 1.0 - v_right / total_v
            # LdP eq. 5: weight proportional to inverse-variance ratio
            s = w_left + w_right
            w_left, w_right = w_left / s, w_right / s
        _recurse(idx_start, mid, parent_weight * w_left)
        _recurse(mid, idx_end, parent_weight * w_right)

    _recurse(0, n, 1.0)
    return weights


def compute_hrp_weights(returns_by_asset: dict[str, list[float]]) -> dict[str, float]:
    """End-to-end HRP. Returns dict[asset -> weight], weights sum to 1.0."""
    if len(returns_by_asset) == 0:
        return {}
    if len(returns_by_asset) == 1:
        only = next(iter(returns_by_asset))
        return {only: 1.0}

    # Filter to assets with at least 2 returns (needed for variance)
    filtered = {k: v for k, v in returns_by_asset.items() if len(v) >= 2}
    if len(filtered) <= 1:
        # fall back to equal weights
        return {k: 1.0 / len(returns_by_asset) for k in returns_by_asset}

    assets, corr = correlation_matrix(filtered)
    dist = _distance_matrix(corr)
    order = _single_linkage_order(dist)
    ordered_assets = [assets[i] for i in order]
    variances = [statistics.variance(filtered[a]) if len(filtered[a]) >= 2 else 1.0
                 for a in ordered_assets]
    weights = _recursive_bisection(variances)

    return {ordered_assets[i]: round(weights[i], 4) for i in range(len(ordered_assets))}


def compare_to_naive_inverse_vol(returns_by_asset: dict[str, list[float]]) -> dict:
    """Side-by-side HRP vs naive inverse-vol for the same input."""
    # Naive inverse-vol
    assets = list(returns_by_asset.keys())
    variances = [statistics.variance(returns_by_asset[a]) if len(returns_by_asset[a]) >= 2 else 1.0
                 for a in assets]
    iv_weights = _inverse_variance_weights(variances)
    naive = {assets[i]: round(iv_weights[i], 4) for i in range(len(assets))}
    hrp = compute_hrp_weights(returns_by_asset)
    return {"naive_inverse_vol": naive, "hrp": hrp,
            "delta": {a: round(hrp.get(a, 0) - naive.get(a, 0), 4) for a in assets}}


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description="HRP vs naive inverse-vol on asset-class returns.")
    ap.add_argument("--dashboard", default="audit_trail/data/dashboard_payload.json")
    ap.add_argument("--min-n", type=int, default=20)
    args = ap.parse_args()

    dp = json.load(open(args.dashboard, "r", encoding="utf-8"))
    closed = [p for p in dp["picks"]["recent_closed"] if p.get("pnl_pct") is not None]
    by_class = defaultdict(list)
    for p in closed:
        ac = (p.get("asset_class") or "UNKNOWN").upper()
        by_class[ac].append(float(p["pnl_pct"]))
    # Drop sparse classes
    by_class = {k: v for k, v in by_class.items() if len(v) >= args.min_n}
    print(json.dumps(compare_to_naive_inverse_vol(dict(by_class)), indent=2))
