"""
Frequentist helpers for HF closed-book validation (stdlib + math only).

- Two-proportion z-test vs baseline win rate (normal approximation)
- Bootstrap percentile CI for win rate
- Profit factor and Sortino-style ratio on per-trade PnL%
"""
from __future__ import annotations

import math
import random
from typing import Iterable, Sequence


def two_proportion_z_score(w_t: int, n_t: int, w_b: int, n_b: int) -> float | None:
    """
    Pooled z for difference (p_tier - p_baseline). Returns None if denominators invalid.
    """
    if n_t <= 0 or n_b <= 0:
        return None
    p_t = w_t / n_t
    p_b = w_b / n_b
    p_pool = (w_t + w_b) / (n_t + n_b)
    denom_sq = p_pool * (1.0 - p_pool) * (1.0 / n_t + 1.0 / n_b)
    if denom_sq <= 0:
        return None
    return (p_t - p_b) / math.sqrt(denom_sq)


def two_sided_normal_pvalue(z: float) -> float:
    """Two-sided p-value from standard normal, using erf."""
    if z < 0:
        z = -z
    # P(|Z| > z) = 2 * (1 - Phi(z))
    phi = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    return max(0.0, min(1.0, 2.0 * (1.0 - phi)))


def bootstrap_wr_ci(
    wins: Sequence[bool],
    n_bootstrap: int = 2000,
    seed: int = 42,
    alpha: float = 0.05,
) -> tuple[float | None, float | None]:
    """
    Percentile bootstrap CI for win rate given list of boolean outcomes.
    Returns (low, high) on [0,1] or (None, None) if empty.
    """
    if not wins:
        return None, None
    rng = random.Random(seed)
    n = len(wins)
    lows: list[float] = []
    for _ in range(n_bootstrap):
        s = sum(1 for i in range(n) if wins[rng.randrange(n)])
        lows.append(s / n)
    lows.sort()
    lo_i = int((alpha / 2) * n_bootstrap)
    hi_i = int((1 - alpha / 2) * n_bootstrap) - 1
    lo_i = max(0, min(lo_i, n_bootstrap - 1))
    hi_i = max(0, min(hi_i, n_bootstrap - 1))
    return lows[lo_i], lows[hi_i]


def profit_factor(pnl_pct: Iterable[float]) -> float | None:
    """Sum wins / abs(sum losses); None if no losses."""
    gains = 0.0
    losses = 0.0
    for x in pnl_pct:
        try:
            v = float(x)
        except (TypeError, ValueError):
            continue
        if v > 0:
            gains += v
        elif v < 0:
            losses += v
    if losses >= 0:
        return None
    return gains / abs(losses)


def sortino_like(pnl_pct: Sequence[float], target: float = 0.0) -> float | None:
    """
    Mean excess return / downside deviation (only negative deviations from target).
    """
    xs = []
    for x in pnl_pct:
        try:
            xs.append(float(x))
        except (TypeError, ValueError):
            continue
    if len(xs) < 2:
        return None
    mu = sum(xs) / len(xs)
    downs = [target - x for x in xs if x < target]
    if not downs:
        return None
    var = sum(d * d for d in downs) / len(downs)
    sd = math.sqrt(var) if var > 0 else None
    if not sd or sd <= 0:
        return None
    return (mu - target) / sd


def summarize_pnl_metrics(pnl_list: list[float]) -> dict:
    """Aggregate PF + Sortino for JSON report."""
    pf = profit_factor(pnl_list)
    so = sortino_like(pnl_list)
    return {
        "profit_factor": round(pf, 4) if pf is not None else None,
        "sortino_like": round(so, 4) if so is not None else None,
        "n_pnl": len(pnl_list),
    }
