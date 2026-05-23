#!/usr/bin/env python3
"""
ALPHA_ENGINE -- PCA-Based Multi-Asset Factor Model
=====================================================
Decomposes multi-asset returns into latent factors (market, sector rotation,
idiosyncratic) using manual PCA via power iteration.

STDLIB ONLY -- no numpy, pandas, or sklearn required.
All matrix operations implemented from scratch using math module.

Usage:
    from pca_factor_model import get_pca_signal
    sig = get_pca_signal("ETHUSDT", symbols_closes)
    # sig = {"factor_exposures": {...}, "factor_momentum": {...},
    #        "diversification_score": 0.72, "pca_market_exposure": 0.85}
"""

from __future__ import annotations

import math
from typing import Any, Optional


# ---------------------------------------------------------------------------
# 1. Compute returns matrix from close prices
# ---------------------------------------------------------------------------

def compute_returns_matrix(symbols_closes: dict[str, list[float]]) -> list[list[float]]:
    """Compute log-return matrix from {symbol: [close_prices]} dict.

    Args:
        symbols_closes: mapping of symbol -> list of close prices (newest last)

    Returns:
        Matrix of returns: rows = time steps, cols = symbols (in insertion order).
        Only time steps where ALL symbols have valid returns are included.
    """
    if not symbols_closes:
        return []

    # Compute log returns per symbol
    all_returns: list[list[float]] = []
    for sym, closes in symbols_closes.items():
        if len(closes) < 2:
            all_returns.append([])
            continue
        rets = []
        for i in range(1, len(closes)):
            if closes[i] > 0 and closes[i - 1] > 0:
                rets.append(math.log(closes[i] / closes[i - 1]))
            else:
                rets.append(0.0)
        all_returns.append(rets)

    if not all_returns:
        return []

    # Align to shortest series
    min_len = min(len(r) for r in all_returns)
    if min_len < 2:
        return []

    # Build matrix: rows=time, cols=symbols (take the LAST min_len entries)
    n_symbols = len(all_returns)
    matrix: list[list[float]] = []
    for t in range(min_len):
        row = []
        for s in range(n_symbols):
            offset = len(all_returns[s]) - min_len
            row.append(all_returns[s][offset + t])
        matrix.append(row)

    return matrix


# ---------------------------------------------------------------------------
# Matrix utilities (stdlib only)
# ---------------------------------------------------------------------------

def _mean(vals: list[float]) -> float:
    """Mean of a list."""
    if not vals:
        return 0.0
    return sum(vals) / len(vals)


def _col(matrix: list[list[float]], j: int) -> list[float]:
    """Extract column j from matrix."""
    return [row[j] for row in matrix]


def _dot(a: list[float], b: list[float]) -> float:
    """Dot product of two vectors."""
    return sum(x * y for x, y in zip(a, b))


def _norm(v: list[float]) -> float:
    """Euclidean norm."""
    return math.sqrt(sum(x * x for x in v))


def _scale(v: list[float], s: float) -> list[float]:
    """Scale vector by scalar."""
    return [x * s for x in v]


def _subtract_vec(a: list[float], b: list[float]) -> list[float]:
    """Element-wise subtraction a - b."""
    return [x - y for x, y in zip(a, b)]


def _mat_vec(mat: list[list[float]], v: list[float]) -> list[float]:
    """Matrix-vector multiply: mat @ v."""
    return [_dot(row, v) for row in mat]


def _outer_subtract_matrix(
    mat: list[list[float]], eigenval: float, eigvec: list[float]
) -> list[list[float]]:
    """Deflate matrix: mat - eigenval * outer(eigvec, eigvec)."""
    n = len(mat)
    result = []
    for i in range(n):
        row = []
        for j in range(n):
            row.append(mat[i][j] - eigenval * eigvec[i] * eigvec[j])
        result.append(row)
    return result


# ---------------------------------------------------------------------------
# 2. PCA decomposition via power iteration
# ---------------------------------------------------------------------------

def pca_decompose(
    returns_matrix: list[list[float]], n_components: int = 3
) -> dict[str, Any]:
    """Manual PCA via power iteration on the covariance matrix.

    Args:
        returns_matrix: rows=time, cols=symbols (from compute_returns_matrix)
        n_components: number of principal components to extract

    Returns:
        dict with keys:
            eigenvalues: list[float]
            eigenvectors: list[list[float]]  (each is a column vector)
            explained_variance_ratio: list[float]
            factor_loadings: list[list[float]]  (n_components x n_symbols)
    """
    if not returns_matrix or len(returns_matrix) < 3:
        return {
            "eigenvalues": [],
            "eigenvectors": [],
            "explained_variance_ratio": [],
            "factor_loadings": [],
        }

    n_time = len(returns_matrix)
    n_sym = len(returns_matrix[0])

    # Cap components at n_sym
    n_components = min(n_components, n_sym)

    # Center each column (subtract mean)
    col_means = []
    for j in range(n_sym):
        col_vals = _col(returns_matrix, j)
        col_means.append(_mean(col_vals))

    centered: list[list[float]] = []
    for row in returns_matrix:
        centered.append([row[j] - col_means[j] for j in range(n_sym)])

    # Compute covariance matrix (n_sym x n_sym)
    cov: list[list[float]] = []
    for i in range(n_sym):
        cov_row = []
        col_i = _col(centered, i)
        for j in range(n_sym):
            col_j = _col(centered, j)
            cov_ij = _dot(col_i, col_j) / (n_time - 1)
            cov_row.append(cov_ij)
        cov.append(cov_row)

    # Power iteration to extract top eigenvectors
    eigenvalues: list[float] = []
    eigenvectors: list[list[float]] = []
    work_mat = [row[:] for row in cov]  # deep copy

    for _ in range(n_components):
        eigvec = _power_iteration(work_mat, max_iter=200, tol=1e-8)
        if eigvec is None:
            break
        eigenval = _dot(_mat_vec(work_mat, eigvec), eigvec)
        if eigenval < 1e-12:
            break
        eigenvalues.append(eigenval)
        eigenvectors.append(eigvec)
        # Deflate
        work_mat = _outer_subtract_matrix(work_mat, eigenval, eigvec)

    # Explained variance ratio
    total_var = sum(cov[i][i] for i in range(n_sym))
    if total_var > 0:
        explained = [ev / total_var for ev in eigenvalues]
    else:
        explained = [0.0] * len(eigenvalues)

    # Factor loadings = eigenvectors scaled by sqrt(eigenvalue)
    factor_loadings = []
    for k, evec in enumerate(eigenvectors):
        sqrt_ev = math.sqrt(max(eigenvalues[k], 0))
        factor_loadings.append([v * sqrt_ev for v in evec])

    return {
        "eigenvalues": eigenvalues,
        "eigenvectors": eigenvectors,
        "explained_variance_ratio": explained,
        "factor_loadings": factor_loadings,
    }


def _power_iteration(
    mat: list[list[float]], max_iter: int = 200, tol: float = 1e-8
) -> Optional[list[float]]:
    """Extract dominant eigenvector via power iteration.

    Args:
        mat: square symmetric matrix
        max_iter: max iterations
        tol: convergence tolerance

    Returns:
        Unit eigenvector or None if degenerate.
    """
    n = len(mat)
    if n == 0:
        return None

    # Initialize with [1, 1, ..., 1] normalized
    v = [1.0 / math.sqrt(n)] * n

    for _ in range(max_iter):
        new_v = _mat_vec(mat, v)
        nrm = _norm(new_v)
        if nrm < 1e-15:
            return None
        new_v = _scale(new_v, 1.0 / nrm)

        # Check convergence (change in vector)
        diff = _norm(_subtract_vec(new_v, v))
        v = new_v
        if diff < tol:
            break

    return v


# ---------------------------------------------------------------------------
# 3. Identify / name factors
# ---------------------------------------------------------------------------

def identify_factors(
    eigenvectors: list[list[float]], symbols: list[str]
) -> list[dict[str, Any]]:
    """Name and characterize each principal component.

    Factor naming heuristics:
        - Factor 1: "market" if most loadings share the same sign
        - Factor 2: "sector_rotation" if loadings have mixed signs
        - Factor 3+: "idiosyncratic"

    Args:
        eigenvectors: list of eigenvectors (each a list of floats)
        symbols: symbol names corresponding to vector indices

    Returns:
        List of dicts: [{"name": str, "loadings": {symbol: float}, "type": str}]
    """
    factors = []
    for idx, evec in enumerate(eigenvectors):
        loadings = {sym: round(evec[i], 6) for i, sym in enumerate(symbols)}

        # Heuristic naming
        pos = sum(1 for v in evec if v > 0.01)
        neg = sum(1 for v in evec if v < -0.01)
        total_nonzero = pos + neg

        if idx == 0:
            # First factor: typically market
            if total_nonzero > 0 and min(pos, neg) / max(pos, neg, 1) < 0.3:
                factor_type = "market"
            else:
                factor_type = "mixed_market"
            name = "market"
        elif idx == 1:
            if pos > 0 and neg > 0:
                factor_type = "sector_rotation"
            else:
                factor_type = "secondary"
            name = "sector_rotation"
        else:
            factor_type = "idiosyncratic"
            name = f"idiosyncratic_{idx}"

        factors.append({
            "name": name,
            "type": factor_type,
            "index": idx,
            "loadings": loadings,
        })

    return factors


# ---------------------------------------------------------------------------
# 4. Per-symbol factor exposure
# ---------------------------------------------------------------------------

def get_factor_exposure(
    symbol: str, factor_loadings: list[list[float]], symbols: list[str]
) -> dict[str, float]:
    """Get a symbol's exposure to each PCA factor.

    Args:
        symbol: target symbol
        factor_loadings: from pca_decompose (n_components x n_symbols)
        symbols: symbol names in column order

    Returns:
        {"factor_0": float, "factor_1": float, ...}
        High factor_0 (market) = moves with market; low = independent alpha.
    """
    if symbol not in symbols:
        return {}

    idx = symbols.index(symbol)
    exposures = {}
    for k, loadings in enumerate(factor_loadings):
        if idx < len(loadings):
            exposures[f"factor_{k}"] = round(loadings[idx], 6)

    return exposures


# ---------------------------------------------------------------------------
# 5. Factor momentum
# ---------------------------------------------------------------------------

def compute_factor_momentum(
    symbols_closes: dict[str, list[float]], lookback: int = 20
) -> dict[str, float]:
    """Compute PCA and measure whether each factor is trending.

    Uses the last `lookback` periods of factor scores to determine momentum.

    Args:
        symbols_closes: {symbol: [close_prices]}
        lookback: number of periods for momentum calculation

    Returns:
        {"factor_0_momentum": float, "factor_1_momentum": float, ...}
        Positive = factor trending up, negative = trending down.
    """
    returns_mat = compute_returns_matrix(symbols_closes)
    if len(returns_mat) < lookback + 5:
        return {}

    pca = pca_decompose(returns_mat, n_components=3)
    if not pca["eigenvectors"]:
        return {}

    # Project returns onto factors to get factor time series
    n_time = len(returns_mat)
    n_components = len(pca["eigenvectors"])

    # Center returns
    n_sym = len(returns_mat[0])
    col_means = [_mean(_col(returns_mat, j)) for j in range(n_sym)]
    centered = [[returns_mat[t][j] - col_means[j] for j in range(n_sym)]
                for t in range(n_time)]

    factor_series: dict[str, list[float]] = {}
    for k, evec in enumerate(pca["eigenvectors"]):
        scores = [_dot(centered[t], evec) for t in range(n_time)]
        factor_series[f"factor_{k}"] = scores

    # Compute momentum as slope of cumulative factor score over lookback
    momentum = {}
    for fname, scores in factor_series.items():
        recent = scores[-lookback:]
        if len(recent) < 5:
            momentum[f"{fname}_momentum"] = 0.0
            continue
        # Simple linear regression slope
        n = len(recent)
        x_mean = (n - 1) / 2.0
        y_mean = _mean(recent)
        num = sum((i - x_mean) * (recent[i] - y_mean) for i in range(n))
        den = sum((i - x_mean) ** 2 for i in range(n))
        slope = num / den if den > 1e-15 else 0.0
        # Normalize slope by std of scores for comparability
        std = math.sqrt(max(_mean([(s - y_mean) ** 2 for s in recent]), 1e-15))
        momentum[f"{fname}_momentum"] = round(slope / std, 6) if std > 1e-10 else 0.0

    return momentum


# ---------------------------------------------------------------------------
# 6. Full PCA signal for a symbol
# ---------------------------------------------------------------------------

def get_pca_signal(
    symbol: str, symbols_closes: dict[str, list[float]]
) -> dict[str, Any]:
    """Compute full PCA-based signal for a symbol.

    Args:
        symbol: target symbol (must be a key in symbols_closes)
        symbols_closes: {symbol: [close_prices]} for the universe

    Returns:
        {
            "factor_exposures": {"factor_0": float, ...},
            "factor_momentum": {"factor_0_momentum": float, ...},
            "diversification_score": float,  # 0=identical to market, 1=fully independent
            "pca_market_exposure": float,    # abs loading on factor 0
            "pca_diversification": float,    # alias for diversification_score
        }
    """
    result: dict[str, Any] = {
        "factor_exposures": {},
        "factor_momentum": {},
        "diversification_score": 0.5,
        "pca_market_exposure": 0.5,
        "pca_diversification": 0.5,
    }

    if symbol not in symbols_closes or len(symbols_closes) < 3:
        return result

    returns_mat = compute_returns_matrix(symbols_closes)
    if len(returns_mat) < 10:
        return result

    symbols = list(symbols_closes.keys())
    pca = pca_decompose(returns_mat, n_components=3)

    if not pca["factor_loadings"]:
        return result

    # Factor exposures
    exposures = get_factor_exposure(symbol, pca["factor_loadings"], symbols)
    result["factor_exposures"] = exposures

    # Factor momentum
    result["factor_momentum"] = compute_factor_momentum(symbols_closes)

    # Market exposure = absolute loading on first factor (normalized)
    if pca["eigenvectors"]:
        sym_idx = symbols.index(symbol)
        market_vec = pca["eigenvectors"][0]
        if sym_idx < len(market_vec):
            raw_loading = abs(market_vec[sym_idx])
            # Normalize: max possible loading is 1.0 (unit vector)
            market_exposure = min(raw_loading * math.sqrt(len(symbols)), 1.0)
            result["pca_market_exposure"] = round(market_exposure, 4)

    # Diversification score: how much variance is NOT explained by factor 1
    # For the specific symbol: 1 - (market_loading^2 / sum_of_all_loadings^2)
    if pca["eigenvectors"]:
        sym_idx = symbols.index(symbol)
        total_loading_sq = 0.0
        market_loading_sq = 0.0
        for k, evec in enumerate(pca["eigenvectors"]):
            if sym_idx < len(evec):
                lsq = evec[sym_idx] ** 2
                total_loading_sq += lsq
                if k == 0:
                    market_loading_sq = lsq

        if total_loading_sq > 1e-15:
            div_score = 1.0 - (market_loading_sq / total_loading_sq)
        else:
            div_score = 0.5
        # Clamp to [0, 1]
        div_score = max(0.0, min(1.0, div_score))
        result["diversification_score"] = round(div_score, 4)
        result["pca_diversification"] = round(div_score, 4)

    return result


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Synthetic test data: 3 assets, 50 time steps
    import random
    random.seed(42)

    # Market factor + idiosyncratic noise
    market = [100.0]
    for _ in range(49):
        market.append(market[-1] * (1 + random.gauss(0.001, 0.02)))

    btc = [m * (1 + random.gauss(0, 0.005)) for m in market]
    eth = [m * 0.5 * (1 + random.gauss(0, 0.01)) for m in market]
    # SOL is more independent
    sol = [100.0]
    for _ in range(49):
        sol.append(sol[-1] * (1 + random.gauss(0.002, 0.03)))

    closes = {"BTCUSDT": btc, "ETHUSDT": eth, "SOLUSDT": sol}

    print("=== PCA Factor Model Test ===\n")

    # Test returns matrix
    mat = compute_returns_matrix(closes)
    print(f"Returns matrix: {len(mat)} rows x {len(mat[0])} cols")

    # Test PCA
    pca = pca_decompose(mat, n_components=3)
    print(f"\nEigenvalues: {[round(e, 6) for e in pca['eigenvalues']]}")
    print(f"Explained variance: {[round(e, 4) for e in pca['explained_variance_ratio']]}")

    # Test factor identification
    syms = list(closes.keys())
    factors = identify_factors(pca["eigenvectors"], syms)
    for f in factors:
        print(f"\nFactor '{f['name']}' ({f['type']}):")
        for sym, load in f["loadings"].items():
            print(f"  {sym}: {load:+.4f}")

    # Test full signal
    for sym in syms:
        sig = get_pca_signal(sym, closes)
        print(f"\n{sym}:")
        print(f"  Market exposure: {sig['pca_market_exposure']}")
        print(f"  Diversification: {sig['pca_diversification']}")
        print(f"  Factor exposures: {sig['factor_exposures']}")
