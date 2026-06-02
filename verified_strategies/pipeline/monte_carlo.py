"""Block bootstrap for temporally dependent returns (EAGLE2 §3.4)."""

from __future__ import annotations

from typing import Tuple

import numpy as np


def block_bootstrap_pvalue(
    returns: np.ndarray,
    observed_stat: float,
    block_size: int,
    n_iter: int = 1000,
    seed: int = 42,
) -> Tuple[float, float, float]:
    """Right-tail p-value under block resampling; returns (p, mean, std)."""
    returns = np.asarray(returns, dtype=float)
    n = len(returns)
    if n < block_size + 2:
        return 1.0, 0.0, 0.0

    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n / block_size))
    stats = []

    for _ in range(n_iter):
        starts = rng.integers(0, n - block_size + 1, size=n_blocks)
        sample = np.concatenate([returns[s : s + block_size] for s in starts])[:n]
        stat = sample.mean() / (sample.std() + 1e-12)
        stats.append(stat)

    stats_arr = np.array(stats)
    p = float((stats_arr >= observed_stat).mean())
    return p, float(stats_arr.mean()), float(stats_arr.std())
