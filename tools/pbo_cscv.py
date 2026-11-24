"""Probability of Backtest Overfitting (PBO) via Combinatorial Symmetric
Cross-Validation (CSCV), per Bailey & Lopez de Prado (2014).

Usage:
    from tools.pbo_cscv import compute_pbo
    pbo = compute_pbo(returns_matrix, S=16)

Inputs:
    returns_matrix: np.ndarray shape (T, N) -- T time observations x N strategies.
    S: even number of time-buckets to split into (default 16).

Algorithm:
    1. Split rows into S equal-sized contiguous buckets.
    2. Enumerate every combination of S/2 buckets as IS; remaining S/2 as OOS.
    3. For each split:
         - Compute IS Sharpe per strategy, pick n* = argmax.
         - Compute OOS Sharpe per strategy, find rank of n* relative to median.
         - Define logit = log(w / (1 - w)) where w = rank_pct in (0,1).
    4. PBO = P(n* has OOS rank strictly below median) = fraction where w < 0.5.

For small N (strategies) the metric is noisy; we still return it with a
`note` in the result dict.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any

import numpy as np


def _sharpe_cols(mat: np.ndarray) -> np.ndarray:
    """Per-column Sharpe; columns with std==0 get -inf so they cannot be argmax."""
    if mat.size == 0:
        return np.full(mat.shape[1] if mat.ndim == 2 else 0, -np.inf)
    mu = mat.mean(axis=0)
    sd = mat.std(axis=0, ddof=1) if mat.shape[0] > 1 else np.zeros_like(mu)
    out = np.where(sd > 0, mu / np.where(sd > 0, sd, 1.0), -np.inf)
    return out


def compute_pbo(returns_matrix: np.ndarray, S: int = 16) -> dict[str, Any]:
    """Return PBO + logits distribution for a (T, N) strategy-return matrix."""
    R = np.asarray(returns_matrix, dtype=float)
    if R.ndim != 2:
        return {"pbo": None, "note": "returns_matrix must be 2-D (T, N)"}
    T, N = R.shape
    if N < 2:
        return {"pbo": None, "note": f"need >=2 strategies, got N={N}", "n_strategies": N, "T": T}
    if T < S:
        # Fall back to largest even S <= T
        S = max(2, (T // 2) * 2)
        if S < 2:
            return {"pbo": None, "note": f"T={T} too small for CSCV", "n_strategies": N, "T": T}
    if S % 2 == 1:
        S -= 1

    # Trim to a multiple of S rows
    usable = (T // S) * S
    R = R[:usable, :]
    # Split into S contiguous buckets (each of size usable/S)
    buckets = np.array_split(R, S, axis=0)

    half = S // 2
    splits = list(combinations(range(S), half))
    logits: list[float] = []
    below_median = 0
    total = 0

    for is_idx in splits:
        is_set = set(is_idx)
        oos_idx = tuple(i for i in range(S) if i not in is_set)
        IS = np.vstack([buckets[i] for i in is_idx])
        OOS = np.vstack([buckets[i] for i in oos_idx])

        is_sr = _sharpe_cols(IS)
        oos_sr = _sharpe_cols(OOS)
        if not np.any(np.isfinite(is_sr)):
            continue
        n_star = int(np.argmax(is_sr))
        # Rank of n* among OOS sharpes (fraction strictly less than)
        finite = np.isfinite(oos_sr)
        if finite.sum() < 2:
            continue
        oos_vals = oos_sr[finite]
        w = float((oos_vals < oos_sr[n_star]).sum()) / float(len(oos_vals))
        # clip to avoid log(0)
        w_c = min(max(w, 1e-6), 1.0 - 1e-6)
        logits.append(float(np.log(w_c / (1.0 - w_c))))
        if w < 0.5:
            below_median += 1
        total += 1

    if total == 0:
        return {"pbo": None, "note": "no valid splits", "n_strategies": N, "T": T, "S": S}

    pbo = below_median / total
    return {
        "pbo": float(pbo),
        "n_splits": total,
        "n_strategies": int(N),
        "T": int(T),
        "S": int(S),
        "logits_mean": float(np.mean(logits)) if logits else None,
        "logits_median": float(np.median(logits)) if logits else None,
    }


if __name__ == "__main__":
    # Self-test on random data: expect PBO ~ 0.5 for pure noise.
    rng = np.random.default_rng(42)
    R = rng.standard_normal((520, 20))
    print(compute_pbo(R, S=16))
