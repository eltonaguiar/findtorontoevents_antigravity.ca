"""Hurst exponent regime classifier.

Classical quant regime detector: computes the Hurst exponent H from a
stationary series (log-returns, not price levels) using rescaled-range (R/S)
analysis.

**Input expectation:** log-returns or differences, NOT raw price levels.
A non-stationary price series will give spurious H ~ 1.0. Use
`tools.cusum_filter.log_returns(prices)` first if you only have prices.

Interpretation:
  H > 0.55    : TRENDING     (momentum strategies favored)
  0.45 <= H <= 0.55 : RANDOM_WALK (efficient / no edge)
  H < 0.45    : MEAN_REVERTING (mean-reversion strategies favored)

References:
  - Hurst H.E. (1951), "Long-term storage capacity of reservoirs"
  - Peters E.E. (1994), "Fractal Market Analysis"
  - mlfinlab Hurst exponent module (Hudson-Thames)

Why we need this
----------------
Our cycles 3-9 perf-reviews show consistent pattern: trend-following strategies
(e.g. `futures_momentum`, `cta_cross_asset_tsmom`) are profitable despite low WR,
while mean-reversion strategies on the same symbols are unprofitable. This hints
at regime mismatch — we don't know whether a symbol is in a trending or
mean-reverting regime when emitting. Hurst gives that answer.

Integration hook: use `classify_regime()` in the AutoHedge sentiment agent
(PR #298) or in `quality_gates.py` to reject picks whose strategy style
mismatches the symbol's current regime (mean-rev picks on trending symbols,
trend picks on mean-reverting symbols).
"""
from __future__ import annotations

import math
import statistics


def _rescaled_range(series: list[float]) -> float:
    """R/S statistic for a single series: max cumulative deviation / stdev."""
    n = len(series)
    if n < 2:
        return 0.0
    mean = sum(series) / n
    devs = [x - mean for x in series]
    cum = []
    running = 0.0
    for d in devs:
        running += d
        cum.append(running)
    R = max(cum) - min(cum)
    S = statistics.stdev(series) if n >= 2 else 0.0
    if S == 0.0:
        return 0.0
    return R / S


def hurst_exponent(series: list[float], min_chunk: int = 8) -> float:
    """Estimate Hurst H via R/S analysis.

    Splits the series into progressively larger non-overlapping chunks, computes
    R/S for each, and fits log(R/S) vs log(chunk_size). The slope is H.

    Returns H in approximately (0, 1). H=0.5 is a random walk.

    Requires len(series) >= ~32 for a stable estimate.
    """
    n = len(series)
    if n < max(min_chunk * 2, 16):
        return 0.5  # not enough data; assume random walk

    chunk_sizes = []
    log_rs = []
    c = min_chunk
    while c <= n // 2:
        rs_list = []
        n_chunks = n // c
        for i in range(n_chunks):
            chunk = series[i * c: (i + 1) * c]
            rs = _rescaled_range(chunk)
            if rs > 0:
                rs_list.append(rs)
        if rs_list:
            avg_rs = sum(rs_list) / len(rs_list)
            if avg_rs > 0:
                chunk_sizes.append(math.log(c))
                log_rs.append(math.log(avg_rs))
        c *= 2

    if len(chunk_sizes) < 2:
        return 0.5

    # Simple least-squares slope
    mean_x = sum(chunk_sizes) / len(chunk_sizes)
    mean_y = sum(log_rs) / len(log_rs)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(chunk_sizes, log_rs))
    den = sum((x - mean_x) ** 2 for x in chunk_sizes)
    if den == 0:
        return 0.5
    return num / den


def classify_regime(series: list[float]) -> dict:
    """Classify a price/return series by regime.

    Returns {
      "hurst": float,
      "regime": "TRENDING" | "RANDOM_WALK" | "MEAN_REVERTING",
      "confidence": float in [0, 1],
    }
    """
    H = hurst_exponent(series)
    if H > 0.55:
        regime = "TRENDING"
        confidence = min(1.0, (H - 0.55) / 0.35)
    elif H < 0.45:
        regime = "MEAN_REVERTING"
        confidence = min(1.0, (0.45 - H) / 0.35)
    else:
        regime = "RANDOM_WALK"
        confidence = 1.0 - abs(H - 0.5) / 0.05
    return {"hurst": round(H, 4), "regime": regime, "confidence": round(confidence, 3)}


def strategy_regime_match(strategy_name: str, regime: str) -> bool:
    """Is this strategy style compatible with the current regime?

    Mean-reversion strategies should NOT trade in TRENDING regimes.
    Trend strategies should NOT trade in MEAN_REVERTING regimes.
    Both can trade in RANDOM_WALK (with reduced confidence).
    """
    s = strategy_name.lower()
    # Mean-reversion fingerprint
    mean_rev_markers = ("mean_reversion", "rsi2", "bollinger_mr", "reversion",
                        "fear_greed_contrarian", "vwap_deviation", "rsi_extreme",
                        "bb_mean_reversion", "connors_rsi")
    # Trend-following fingerprint
    trend_markers = ("momentum", "breakout", "trend", "tsmom", "macd_crossover",
                     "golden_cross", "donchian", "ema_stack", "keltner_compression")
    is_mean_rev = any(m in s for m in mean_rev_markers)
    is_trend = any(m in s for m in trend_markers)

    if is_mean_rev and regime == "TRENDING":
        return False
    if is_trend and regime == "MEAN_REVERTING":
        return False
    return True


if __name__ == "__main__":
    import argparse
    import json
    import random

    ap = argparse.ArgumentParser(description="Hurst regime demo.")
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--type", choices=["trending", "mean_rev", "random"], default="random")
    args = ap.parse_args()

    rng = random.Random(42)
    if args.type == "trending":
        # Strong positive drift
        series = [100.0]
        for _ in range(args.n):
            series.append(series[-1] + 0.5 + rng.gauss(0, 0.3))
    elif args.type == "mean_rev":
        # Ornstein-Uhlenbeck-like
        series = [100.0]
        for _ in range(args.n):
            pull = (100.0 - series[-1]) * 0.1
            series.append(series[-1] + pull + rng.gauss(0, 0.5))
    else:
        # Geometric random walk
        series = [100.0]
        for _ in range(args.n):
            series.append(series[-1] + rng.gauss(0, 0.5))

    print(json.dumps(classify_regime(series), indent=2))
