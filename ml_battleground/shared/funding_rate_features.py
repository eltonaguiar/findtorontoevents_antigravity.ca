"""
Funding Rate Feature Decomposition — 5 orthogonal features from raw funding rate.

Based on: FINAL_SYNTHESIS_REPORT Researchers R001 (Dr. Vasquez) and R009 (Dr. Patel)
Date: 2026-03-13

Instead of feeding raw funding rate as 1 feature, decompose into 5 features
that capture different market dynamics:
  1. current_rate — raw normalized funding rate
  2. rate_roc_8h — rate of change over 8 hours (acceleration)
  3. rate_zscore_30d — how extreme is current rate vs 30-day distribution
  4. rate_vs_basis — funding rate vs spot-perp basis (convergence signal)
  5. rate_momentum — directional momentum of funding rate changes

Expected Impact: +5-15% accuracy boost as LightGBM/XGBoost features
Effort: Minimal — pure feature engineering, no model changes needed

Usage:
    from ml_battleground.shared.funding_rate_features import decompose_funding_rate

    # From a pandas Series/DataFrame of raw funding rates
    features = decompose_funding_rate(funding_rates, spot_prices, perp_prices)
    # Returns dict with 5 named features for each timestamp
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)


def decompose_funding_rate(
    funding_rates: Union[list, "np.ndarray"],
    spot_prices: Optional[Union[list, "np.ndarray"]] = None,
    perp_prices: Optional[Union[list, "np.ndarray"]] = None,
    interval_hours: int = 8,
) -> Dict[str, float]:
    """Decompose a series of funding rates into 5 orthogonal features.

    Args:
        funding_rates: Array of recent funding rates (newest last).
                       At least 90 values (30 days × 3 per day @ 8h) recommended.
        spot_prices: Optional spot prices aligned with funding_rates.
        perp_prices: Optional perpetual futures prices aligned with funding_rates.
        interval_hours: Hours between funding rate updates (default 8h for most exchanges).

    Returns:
        Dict with 5 features:
            current_rate, rate_roc_8h, rate_zscore_30d,
            rate_vs_basis, rate_momentum
    """
    rates = np.array(funding_rates, dtype=np.float64)
    rates = rates[np.isfinite(rates)]

    if len(rates) == 0:
        return _empty_features()

    # Feature 1: Current normalized funding rate
    current_rate = float(rates[-1])

    # Feature 2: Rate of change over 8h (1 funding interval = acceleration)
    if len(rates) >= 2:
        rate_roc_8h = float(rates[-1] - rates[-2])
    else:
        rate_roc_8h = 0.0

    # Feature 3: Z-score over 30-day window (how extreme is the current rate?)
    window_30d = 30 * (24 // interval_hours)  # e.g., 90 for 8h intervals
    lookback = min(window_30d, len(rates))
    window = rates[-lookback:]
    mean_30d = float(np.mean(window))
    std_30d = float(np.std(window))
    if std_30d > 1e-10:
        rate_zscore_30d = float((current_rate - mean_30d) / std_30d)
    else:
        rate_zscore_30d = 0.0

    # Feature 4: Rate vs spot-perp basis (convergence/divergence signal)
    if (
        spot_prices is not None
        and perp_prices is not None
        and len(spot_prices) > 0
        and len(perp_prices) > 0
    ):
        spot = np.array(spot_prices, dtype=np.float64)
        perp = np.array(perp_prices, dtype=np.float64)
        basis_pct = float((perp[-1] - spot[-1]) / spot[-1]) * 100 if spot[-1] != 0 else 0.0
        # Positive basis + positive funding = consistent (contango)
        # Negative basis + positive funding = divergence (potential reversal)
        rate_vs_basis = float(current_rate * 10000 - basis_pct)  # Rate in bps minus basis
    else:
        rate_vs_basis = 0.0

    # Feature 5: Funding rate momentum (EMA-based directional trend)
    if len(rates) >= 5:
        # Simple momentum: mean of last 3 changes
        recent_changes = np.diff(rates[-4:])  # last 3 changes
        rate_momentum = float(np.mean(recent_changes))
    elif len(rates) >= 2:
        rate_momentum = float(rates[-1] - rates[-2])
    else:
        rate_momentum = 0.0

    features = {
        "funding_current_rate": current_rate,
        "funding_roc_8h": rate_roc_8h,
        "funding_zscore_30d": rate_zscore_30d,
        "funding_vs_basis": rate_vs_basis,
        "funding_momentum": rate_momentum,
    }

    logger.debug(
        "Funding rate decomposition: current=%.6f, roc=%.6f, zscore=%.2f, basis=%.4f, momentum=%.6f",
        current_rate, rate_roc_8h, rate_zscore_30d, rate_vs_basis, rate_momentum,
    )

    return features


def decompose_funding_rate_series(
    funding_rates: Union[list, "np.ndarray"],
    spot_prices: Optional[Union[list, "np.ndarray"]] = None,
    perp_prices: Optional[Union[list, "np.ndarray"]] = None,
    interval_hours: int = 8,
) -> Dict[str, List[float]]:
    """Decompose funding rates into 5 features for each timestamp in the series.

    Returns dict of feature_name → list of values, aligned with input indices.
    Useful for building training DataFrames.
    """
    rates = np.array(funding_rates, dtype=np.float64)
    n = len(rates)

    result = {
        "funding_current_rate": [],
        "funding_roc_8h": [],
        "funding_zscore_30d": [],
        "funding_vs_basis": [],
        "funding_momentum": [],
    }

    window_30d = 30 * (24 // interval_hours)

    for i in range(n):
        current = float(rates[i]) if np.isfinite(rates[i]) else 0.0
        result["funding_current_rate"].append(current)

        # ROC
        if i >= 1 and np.isfinite(rates[i - 1]):
            result["funding_roc_8h"].append(float(rates[i] - rates[i - 1]))
        else:
            result["funding_roc_8h"].append(0.0)

        # Z-score
        lookback = min(window_30d, i + 1)
        window = rates[max(0, i + 1 - lookback):i + 1]
        window = window[np.isfinite(window)]
        if len(window) > 1:
            m, s = float(np.mean(window)), float(np.std(window))
            result["funding_zscore_30d"].append(float((current - m) / s) if s > 1e-10 else 0.0)
        else:
            result["funding_zscore_30d"].append(0.0)

        # Basis
        if spot_prices is not None and perp_prices is not None and i < len(spot_prices):
            sp = float(spot_prices[i]) if np.isfinite(spot_prices[i]) else 0
            pp = float(perp_prices[i]) if np.isfinite(perp_prices[i]) else 0
            basis = ((pp - sp) / sp * 100) if sp != 0 else 0.0
            result["funding_vs_basis"].append(float(current * 10000 - basis))
        else:
            result["funding_vs_basis"].append(0.0)

        # Momentum
        if i >= 4:
            changes = np.diff(rates[i - 3:i + 1])
            changes = changes[np.isfinite(changes)]
            result["funding_momentum"].append(float(np.mean(changes)) if len(changes) > 0 else 0.0)
        elif i >= 1:
            result["funding_momentum"].append(float(rates[i] - rates[i - 1]))
        else:
            result["funding_momentum"].append(0.0)

    return result


def _empty_features() -> Dict[str, float]:
    """Return zeroed features when no data is available."""
    return {
        "funding_current_rate": 0.0,
        "funding_roc_8h": 0.0,
        "funding_zscore_30d": 0.0,
        "funding_vs_basis": 0.0,
        "funding_momentum": 0.0,
    }


# ── Quick test ───────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    # Simulate 90 funding rate observations (30 days × 3 per day)
    np.random.seed(42)
    mock_rates = np.cumsum(np.random.normal(0.0001, 0.0005, 90))  # Trending slightly positive
    mock_spot = np.linspace(80000, 82000, 90)
    mock_perp = mock_spot * (1 + mock_rates * 100)  # Perp premium correlated with funding

    features = decompose_funding_rate(mock_rates, mock_spot, mock_perp)
    print("\n=== Funding Rate Decomposition (Latest Point) ===")
    for name, value in features.items():
        print(f"  {name:30s}: {value:+.8f}")

    series = decompose_funding_rate_series(mock_rates, mock_spot, mock_perp)
    print(f"\n=== Series (last 5 of {len(series['funding_current_rate'])} points) ===")
    for name, values in series.items():
        print(f"  {name:30s}: {[f'{v:+.6f}' for v in values[-5:]]}")
