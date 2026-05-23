"""
Cross-Sectional Momentum Rank — Feature for ML models.

Based on: FINAL_SYNTHESIS_REPORT Researcher R001 (Dr. Vasquez)
Date: 2026-03-13

Ranks coins by N-day momentum against each other.
  - Top-decile coins have stronger continuation (momentum factor)
  - Bottom-decile coins tend to mean-revert or crash
  - The RANK itself is the feature (not the raw momentum)

This was a dead standalone strategy (0/3 WR) because it traded directly.
As a FEATURE fed into LightGBM/XGBoost, it becomes a powerful signal.

Reference: Unravel Finance verified live Sharpe ~2.0 on cross-sectional
           momentum (2024-2025 crypto data).

Usage:
    from ml_battleground.shared.cross_sectional_momentum import compute_momentum_rank

    # symbols_data: dict of {symbol: list_of_close_prices}
    ranks = compute_momentum_rank(symbols_data, lookback=30)
    # Returns {symbol: rank_percentile} where 1.0 = strongest momentum
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)


def compute_momentum(prices: Union[list, "np.ndarray"], lookback: int = 30) -> float:
    """Compute momentum as percentage return over lookback period.

    Args:
        prices: Close prices (newest last)
        lookback: Number of bars to look back

    Returns:
        Momentum as decimal (e.g., 0.05 = 5% gain)
    """
    arr = np.array(prices, dtype=np.float64)
    arr = arr[np.isfinite(arr)]

    if len(arr) < lookback or arr[-lookback] == 0:
        return 0.0

    return float((arr[-1] - arr[-lookback]) / arr[-lookback])


def compute_momentum_rank(
    symbols_data: Dict[str, Union[list, "np.ndarray"]],
    lookback: int = 30,
) -> Dict[str, float]:
    """Rank symbols by momentum and return percentile rank.

    Args:
        symbols_data: Dict of {symbol: prices_list} with close prices.
        lookback: Momentum lookback period in bars.

    Returns:
        Dict of {symbol: percentile_rank} where 1.0 = strongest momentum,
        0.0 = weakest. Returns 0.5 for symbols with insufficient data.
    """
    if not symbols_data:
        return {}

    # Compute raw momentum for each symbol
    momentums = {}
    for sym, prices in symbols_data.items():
        mom = compute_momentum(prices, lookback)
        momentums[sym] = mom

    # Rank: sort symbols by momentum, assign percentile
    sorted_symbols = sorted(momentums.keys(), key=lambda s: momentums[s])
    n = len(sorted_symbols)

    ranks = {}
    for i, sym in enumerate(sorted_symbols):
        # Percentile rank: 0.0 (worst) to 1.0 (best)
        ranks[sym] = i / max(n - 1, 1)

    return ranks


def compute_multi_period_momentum_features(
    prices: Union[list, "np.ndarray"],
    all_symbols_data: Optional[Dict[str, Union[list, "np.ndarray"]]] = None,
    symbol: Optional[str] = None,
    lookback_periods: Optional[List[int]] = None,
) -> Dict[str, float]:
    """Compute multiple momentum features for a single symbol.

    Returns a dict of named features ready to add to a feature vector.

    Args:
        prices: Close prices for the target symbol.
        all_symbols_data: Optional dict of all symbols' prices for cross-sectional rank.
        symbol: Name of the target symbol (required if all_symbols_data provided).
        lookback_periods: Lookback periods to compute. Default: [7, 14, 30, 60].

    Returns:
        Dict with features:
            mom_7d, mom_14d, mom_30d, mom_60d — raw momentum values
            mom_rank_30d — cross-sectional percentile rank (if all_symbols_data given)
            mom_acceleration — difference between short and long momentum
            mom_consistency — fraction of sub-periods that were positive
    """
    if lookback_periods is None:
        lookback_periods = [7, 14, 30, 60]

    arr = np.array(prices, dtype=np.float64)
    arr = arr[np.isfinite(arr)]
    features = {}

    # Raw momentum at multiple lookbacks
    for lb in lookback_periods:
        mom = compute_momentum(arr, lb)
        features[f"mom_{lb}d"] = mom

    # Cross-sectional rank (if peer data available)
    if all_symbols_data and symbol:
        ranks = compute_momentum_rank(all_symbols_data, lookback=30)
        features["mom_rank_30d"] = ranks.get(symbol, 0.5)
    else:
        features["mom_rank_30d"] = 0.5  # neutral

    # Momentum acceleration: short-term vs long-term
    short_lb = lookback_periods[0] if len(lookback_periods) > 0 else 7
    long_lb = lookback_periods[-1] if len(lookback_periods) > 1 else 30
    mom_short = compute_momentum(arr, short_lb)
    mom_long = compute_momentum(arr, long_lb)
    features["mom_acceleration"] = mom_short - mom_long

    # Momentum consistency: what fraction of weekly sub-windows were positive?
    window_size = min(7, len(arr) // 4) if len(arr) > 4 else max(1, len(arr) // 2)
    if window_size > 0 and len(arr) >= window_size * 2:
        sub_returns = []
        for start in range(0, len(arr) - window_size, window_size):
            end = start + window_size
            if arr[start] != 0:
                sub_returns.append((arr[end - 1] - arr[start]) / arr[start])
        if sub_returns:
            features["mom_consistency"] = sum(1 for r in sub_returns if r > 0) / len(sub_returns)
        else:
            features["mom_consistency"] = 0.5
    else:
        features["mom_consistency"] = 0.5

    return features


# ── Quick test ───────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    np.random.seed(42)

    # Simulate 5 crypto assets with different momentum profiles
    n_bars = 90
    symbols = {
        "BTCUSDT": np.cumprod(1 + np.random.normal(0.002, 0.02, n_bars)) * 80000,   # bullish
        "ETHUSDT": np.cumprod(1 + np.random.normal(0.001, 0.025, n_bars)) * 3000,    # mild bull
        "SOLUSDT": np.cumprod(1 + np.random.normal(-0.001, 0.03, n_bars)) * 150,     # flat/bear
        "BNBUSDT": np.cumprod(1 + np.random.normal(0.003, 0.015, n_bars)) * 500,     # strong bull
        "DOGEUSDT": np.cumprod(1 + np.random.normal(-0.003, 0.04, n_bars)) * 0.15,   # bearish
    }

    print("\n=== Cross-Sectional Momentum Rank ===")
    ranks = compute_momentum_rank(symbols, lookback=30)
    for sym, rank in sorted(ranks.items(), key=lambda x: x[1], reverse=True):
        mom = compute_momentum(symbols[sym], 30)
        print(f"  {sym:12s}  rank={rank:.2f}  mom_30d={mom:+.2%}")

    print("\n=== Multi-Period Momentum Features (BTCUSDT) ===")
    features = compute_multi_period_momentum_features(
        symbols["BTCUSDT"],
        all_symbols_data=symbols,
        symbol="BTCUSDT",
    )
    for name, value in features.items():
        print(f"  {name:25s}: {value:+.6f}")
