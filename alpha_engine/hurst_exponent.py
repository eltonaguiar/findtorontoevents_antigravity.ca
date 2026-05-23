#!/usr/bin/env python3
"""
ALPHA_ENGINE -- Hurst Exponent Module
======================================
Detects long-range dependence in price series using Rescaled Range (R/S) analysis.

The Hurst exponent H characterises the memory of a time series:
  H > 0.5  =>  trending / persistent (momentum strategies favoured)
  H < 0.5  =>  mean-reverting / anti-persistent (reversion strategies favoured)
  H ~ 0.5  =>  random walk (reduce exposure, favour neutral strategies)

Stdlib only -- no numpy/pandas.
"""

from __future__ import annotations

import math
from typing import Any


# ---------------------------------------------------------------------------
# Core R/S analysis
# ---------------------------------------------------------------------------

def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def _std(xs: list[float], mu: float) -> float:
    """Population standard deviation."""
    if len(xs) < 2:
        return 0.0
    var = sum((x - mu) ** 2 for x in xs) / len(xs)
    return math.sqrt(var)


def _rescaled_range(series: list[float]) -> float:
    """Compute R/S for a single sub-series.

    R = max(cumulative deviations) - min(cumulative deviations)
    S = standard deviation
    Returns R/S, or 0.0 if S is near zero.
    """
    n = len(series)
    if n < 2:
        return 0.0

    mu = _mean(series)
    s = _std(series, mu)
    if s < 1e-15:
        return 0.0

    # Cumulative deviations from mean
    cum = 0.0
    cum_min = 0.0
    cum_max = 0.0
    for x in series:
        cum += (x - mu)
        if cum < cum_min:
            cum_min = cum
        if cum > cum_max:
            cum_max = cum

    r = cum_max - cum_min
    return r / s


def compute_hurst(prices: list[float], max_lag: int = 100) -> float:
    """Compute the Hurst exponent via R/S analysis.

    Args:
        prices: list of close prices (at least 20 values recommended).
        max_lag: maximum sub-series length to test (capped at len(prices)//2).

    Returns:
        H clamped to [0.0, 1.0].  Returns 0.5 (random walk) on error.
    """
    if len(prices) < 20:
        return 0.5  # Not enough data -- assume random walk

    # Compute log returns
    returns: list[float] = []
    for i in range(1, len(prices)):
        if prices[i - 1] > 0 and prices[i] > 0:
            returns.append(math.log(prices[i] / prices[i - 1]))
        else:
            returns.append(0.0)

    if len(returns) < 20:
        return 0.5

    # Cap max_lag at half the returns length
    effective_max_lag = min(max_lag, len(returns) // 2)
    if effective_max_lag < 10:
        return 0.5

    # Compute average R/S for each lag (sub-series length)
    log_n_list: list[float] = []
    log_rs_list: list[float] = []

    for lag in range(10, effective_max_lag + 1):
        # Divide returns into non-overlapping sub-series of length `lag`
        num_subseries = len(returns) // lag
        if num_subseries < 1:
            continue

        rs_values: list[float] = []
        for k in range(num_subseries):
            start = k * lag
            end = start + lag
            sub = returns[start:end]
            rs = _rescaled_range(sub)
            if rs > 0:
                rs_values.append(rs)

        if not rs_values:
            continue

        avg_rs = _mean(rs_values)
        if avg_rs > 0:
            log_n_list.append(math.log(lag))
            log_rs_list.append(math.log(avg_rs))

    if len(log_n_list) < 3:
        return 0.5

    # Ordinary least squares: log(R/S) = H * log(n) + c
    # H = slope of the regression
    n = len(log_n_list)
    mean_x = _mean(log_n_list)
    mean_y = _mean(log_rs_list)

    num = 0.0
    den = 0.0
    for i in range(n):
        dx = log_n_list[i] - mean_x
        num += dx * (log_rs_list[i] - mean_y)
        den += dx * dx

    if abs(den) < 1e-15:
        return 0.5

    h = num / den

    # Clamp to [0, 1]
    return max(0.0, min(1.0, h))


# ---------------------------------------------------------------------------
# Regime classification
# ---------------------------------------------------------------------------

def get_regime_from_hurst(h: float) -> str:
    """Classify the market regime based on Hurst exponent.

    Args:
        h: Hurst exponent value in [0, 1].

    Returns:
        "trending", "mean_reverting", or "random_walk".
    """
    if h > 0.65:
        return "trending"
    elif h < 0.35:
        return "mean_reverting"
    else:
        return "random_walk"


# ---------------------------------------------------------------------------
# Strategy selector
# ---------------------------------------------------------------------------

def hurst_strategy_selector(h: float) -> list[str]:
    """Recommend strategy families based on the Hurst exponent.

    Args:
        h: Hurst exponent value in [0, 1].

    Returns:
        List of recommended strategy family names.
    """
    regime = get_regime_from_hurst(h)

    if regime == "trending":
        return [
            "momentum",
            "trend_following",
            "breakout",
            "moving_average_crossover",
            "acceleration",
        ]
    elif regime == "mean_reverting":
        return [
            "mean_reversion",
            "bollinger_reversion",
            "rsi_oversold_bounce",
            "pairs_trading",
            "grid_trading",
        ]
    else:
        # Random walk -- reduce risk, favour neutral / hedged approaches
        return [
            "market_neutral",
            "reduced_position",
            "range_bound",
            "volatility_selling",
        ]


# ---------------------------------------------------------------------------
# Signal generator (integration entry point)
# ---------------------------------------------------------------------------

def get_hurst_signal(symbol: str, closes: list[float]) -> dict[str, Any]:
    """Compute Hurst-based regime signal for a symbol.

    Args:
        symbol: Trading pair identifier (e.g. "BTCUSDT").
        closes: List of close prices.

    Returns:
        dict with keys:
            hurst_exponent   -- float in [0, 1]
            regime           -- "trending" | "mean_reverting" | "random_walk"
            recommended_families -- list[str]
            confidence       -- float in [0, 1], higher when H is far from 0.5
    """
    h = compute_hurst(closes)
    regime = get_regime_from_hurst(h)
    families = hurst_strategy_selector(h)

    # Confidence: how far H is from the ambiguous 0.5 zone
    # Max confidence (1.0) at H=0 or H=1, min (0.0) at H=0.5
    confidence = min(1.0, abs(h - 0.5) * 2.0)

    return {
        "symbol": symbol,
        "hurst_exponent": round(h, 4),
        "regime": regime,
        "recommended_families": families,
        "confidence": round(confidence, 4),
    }


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Quick sanity test with synthetic data
    import random
    random.seed(42)

    # Generate trending (persistent) series
    trending = [100.0]
    for _ in range(200):
        trending.append(trending[-1] + random.gauss(0.5, 1.0))

    # Generate mean-reverting series (Ornstein-Uhlenbeck-like)
    mr = [100.0]
    for _ in range(200):
        mr.append(mr[-1] + 0.3 * (100.0 - mr[-1]) + random.gauss(0, 0.5))

    # Random walk
    rw = [100.0]
    for _ in range(200):
        rw.append(rw[-1] + random.gauss(0, 1.0))

    for label, series in [("Trending", trending), ("Mean-reverting", mr), ("Random walk", rw)]:
        sig = get_hurst_signal("TEST", series)
        print(f"{label:15s}  H={sig['hurst_exponent']:.4f}  regime={sig['regime']:15s}  "
              f"confidence={sig['confidence']:.4f}  families={sig['recommended_families']}")
