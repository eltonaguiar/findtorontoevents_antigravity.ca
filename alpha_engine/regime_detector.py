"""Market Regime Detector -- classifies current market into regimes.

Regimes:
  TRENDING_UP    -- Strong uptrend (20d ROC > 5%, ADX > 25)
  TRENDING_DOWN  -- Strong downtrend (20d ROC < -5%, ADX > 25)
  MEAN_REVERTING -- Range-bound (ADX < 20, Bollinger %B between 0.2-0.8)
  HIGH_VOLATILITY -- Volatile (ATR/price > 2x 60d avg)
  LOW_VOLATILITY  -- Compressed (ATR/price < 0.5x 60d avg)
  CRISIS          -- Crash mode (drawdown > 15% in 7d, VIX > 30 or F&G < 15)
"""
import json
import os
from datetime import datetime


def detect_regime(btc_prices: list, fear_greed: int = 50) -> dict:
    """Detect current market regime from BTC price series.

    Args:
        btc_prices: List of closing prices (most recent last), minimum 60 values
        fear_greed: Current Fear & Greed index (0-100)

    Returns:
        dict with keys: regime, confidence, sub_regimes, metrics
    """
    if len(btc_prices) < 60:
        return {"regime": "UNKNOWN", "confidence": 0.0, "sub_regimes": [], "metrics": {}}

    prices = btc_prices[-60:]
    current = prices[-1]

    roc_7d = (current - prices[-7]) / prices[-7] if prices[-7] else 0
    roc_20d = (current - prices[-20]) / prices[-20] if prices[-20] else 0

    high_30d = max(prices[-30:])
    drawdown_30d = (current - high_30d) / high_30d

    high_7d = max(prices[-7:])
    drawdown_7d = (current - high_7d) / high_7d

    returns = [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices))]
    recent_vol = _std(returns[-14:]) if len(returns) >= 14 else 0
    longer_vol = _std(returns[-60:]) if len(returns) >= 60 else recent_vol
    vol_ratio = recent_vol / longer_vol if longer_vol > 0 else 1.0

    pos_moves = [max(returns[i], 0) for i in range(-14, 0)]
    neg_moves = [abs(min(returns[i], 0)) for i in range(-14, 0)]
    adx_proxy = abs(sum(pos_moves) - sum(neg_moves)) / (sum(pos_moves) + sum(neg_moves) + 1e-10) * 100

    # Hurst exponent for trend persistence / mean-reversion detection
    hurst = _hurst_exponent(prices)

    metrics = {
        "roc_7d": round(roc_7d, 4),
        "roc_20d": round(roc_20d, 4),
        "drawdown_30d": round(drawdown_30d, 4),
        "drawdown_7d": round(drawdown_7d, 4),
        "vol_ratio": round(vol_ratio, 2),
        "adx_proxy": round(adx_proxy, 1),
        "fear_greed": fear_greed,
        "hurst": round(hurst, 3),
    }

    sub_regimes = []

    if drawdown_7d < -0.15 or (drawdown_30d < -0.20 and fear_greed < 15):
        sub_regimes.append("CRISIS")

    if vol_ratio > 2.0:
        sub_regimes.append("HIGH_VOLATILITY")
    elif vol_ratio < 0.5:
        sub_regimes.append("LOW_VOLATILITY")

    # Phase 2 fix: check BOTH 20d and 7d ROC to avoid misclassifying reversals.
    # If 20d is up but 7d is sharply down, the trend has reversed -- call it TRENDING_DOWN.
    # This prevents the Phase 1 bug where market was called TRENDING_UP during a selloff.
    if roc_20d > 0.05 and roc_7d > 0.0 and adx_proxy > 25:
        sub_regimes.append("TRENDING_UP")
    elif roc_20d < -0.05 and adx_proxy > 25:
        sub_regimes.append("TRENDING_DOWN")
    elif roc_20d > 0.05 and roc_7d < -0.02 and adx_proxy > 25:
        # 20d up but 7d reversing -- trend reversal, not continuation
        sub_regimes.append("TRENDING_DOWN")
    elif adx_proxy < 20:
        # CHOPPY split: distinguish tight vs wide ranges so downstream
        # direction scoring can stay discriminative in range regimes.
        if vol_ratio < 0.85:
            sub_regimes.append("CHOPPY_TIGHT")
        elif vol_ratio > 1.15:
            sub_regimes.append("CHOPPY_WIDE")
        else:
            sub_regimes.append("MEAN_REVERTING")

    # Hurst-based regime refinement: catch trends/MR the ADX proxy misses
    has_trending = any("TRENDING" in s for s in sub_regimes)
    has_mr = "MEAN_REVERTING" in sub_regimes

    if hurst > 0.65 and not has_trending:
        sub_regimes.append("TRENDING_UP" if roc_20d > 0 else "TRENDING_DOWN")
    if hurst < 0.35 and not has_mr:
        sub_regimes.append("MEAN_REVERTING")

    regime = sub_regimes[0] if sub_regimes else "NEUTRAL"
    if "CHOPPY_TIGHT" in sub_regimes:
        regime = "CHOPPY_TIGHT"
    elif "CHOPPY_WIDE" in sub_regimes:
        regime = "CHOPPY_WIDE"
    confidence = min(adx_proxy / 50, 1.0) if "TRENDING" in regime else 0.5
    if regime == "CRISIS":
        confidence = min(abs(drawdown_7d) * 5, 1.0)
    elif regime == "CHOPPY_TIGHT":
        confidence = 0.35
    elif regime == "CHOPPY_WIDE":
        confidence = 0.45

    # Hurst confirmation boost: if Hurst agrees with detected regime, increase confidence
    if "TRENDING" in regime and hurst > 0.6:
        confidence = min(confidence + 0.15, 1.0)
    elif regime == "MEAN_REVERTING" and hurst < 0.4:
        confidence = min(confidence + 0.15, 1.0)

    # Direction suggestion based on regime + short-term momentum
    if regime == "TRENDING_DOWN" or regime == "CRISIS":
        direction_suggested = "SHORT"
    elif regime == "TRENDING_UP":
        direction_suggested = "LONG"
    elif regime in ("CHOPPY_TIGHT", "CHOPPY_WIDE", "MEAN_REVERTING"):
        direction_suggested = "BOTH"
    elif roc_7d < -0.01:
        direction_suggested = "SHORT"  # Short-term bearish even if regime is neutral
    elif roc_7d > 0.01:
        direction_suggested = "LONG"
    else:
        direction_suggested = "BOTH"

    return {
        "regime": regime,
        "confidence": round(confidence, 2),
        "sub_regimes": sub_regimes,
        "metrics": metrics,
        "direction_suggested": direction_suggested,
        "timestamp": datetime.utcnow().isoformat(),
    }


# Hurst exponent guidance:
#   H > 0.6 favors trend-following strategies (momentum, breakout, trend_following)
#   H < 0.4 favors mean-reversion strategies (mean_reversion, multi_sigma_reversal, autocorrelation_exploiter)
#   0.4 <= H <= 0.6 is random walk territory -- regime-agnostic strategies preferred
STRATEGY_REGIME_COMPATIBILITY = {
    "mean_reversion": ["MEAN_REVERTING", "CHOPPY_TIGHT", "CHOPPY_WIDE", "HIGH_VOLATILITY", "CRISIS"],
    "multi_sigma_reversal": ["MEAN_REVERTING", "CHOPPY_TIGHT", "CHOPPY_WIDE", "HIGH_VOLATILITY", "CRISIS"],
    "fear_greed_extreme_dca": ["CRISIS", "HIGH_VOLATILITY"],
    "cryptopanic_news_sentiment": ["CRISIS", "HIGH_VOLATILITY", "MEAN_REVERTING"],
    "volume_profile_value_area": ["MEAN_REVERTING", "CHOPPY_TIGHT", "LOW_VOLATILITY"],
    "autocorrelation_exploiter": ["MEAN_REVERTING", "CHOPPY_TIGHT", "LOW_VOLATILITY"],
    "momentum": ["TRENDING_UP", "TRENDING_DOWN"],
    "breakout": ["TRENDING_UP", "LOW_VOLATILITY"],
    "trend_following": ["TRENDING_UP", "TRENDING_DOWN"],
    "arbitrage": ["TRENDING_UP", "TRENDING_DOWN", "MEAN_REVERTING", "HIGH_VOLATILITY", "LOW_VOLATILITY", "CRISIS", "NEUTRAL"],
    "funding_rate": ["TRENDING_UP", "TRENDING_DOWN", "MEAN_REVERTING", "HIGH_VOLATILITY", "LOW_VOLATILITY", "CRISIS", "NEUTRAL"],
    "volatility_selling": ["LOW_VOLATILITY", "MEAN_REVERTING"],
    "volatility_buying": ["HIGH_VOLATILITY", "CRISIS"],
}


def is_strategy_compatible(strategy_name: str, regime: str, compatibility_map: dict = None) -> bool:
    """Check if a strategy should run in the current regime."""
    if compatibility_map is None:
        compatibility_map = STRATEGY_REGIME_COMPATIBILITY

    if strategy_name in compatibility_map:
        return regime in compatibility_map[strategy_name]

    for category, regimes in compatibility_map.items():
        if category in strategy_name:
            return regime in regimes

    return True


def _std(values):
    """Standard deviation without numpy."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return variance ** 0.5


def _hurst_exponent(prices: list, min_chunk: int = 8) -> float:
    """Estimate Hurst exponent via Rescaled Range (R/S) analysis.

    H < 0.4  -> mean-reverting
    0.4 <= H <= 0.6 -> random walk
    H > 0.6  -> trending/persistent

    Uses log-log regression of R/S vs chunk size.
    Returns 0.5 (random walk) on insufficient data.
    """
    import math

    if len(prices) < min_chunk * 2:
        return 0.5

    returns = [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices))]
    n = len(returns)

    # Test multiple chunk sizes (powers of 2 that fit)
    chunk_sizes = []
    rs_values = []
    size = min_chunk
    while size <= n // 2:
        chunk_sizes.append(size)
        rs_list = []
        for start in range(0, n - size + 1, size):
            chunk = returns[start:start + size]
            mean_c = sum(chunk) / len(chunk)
            deviations = [sum(chunk[:k + 1]) - (k + 1) * mean_c for k in range(len(chunk))]
            R = max(deviations) - min(deviations)
            S = _std(chunk)
            if S > 0:
                rs_list.append(R / S)
        if rs_list:
            rs_values.append(sum(rs_list) / len(rs_list))
        size *= 2

    if len(chunk_sizes) < 2:
        return 0.5

    # Log-log regression: log(R/S) = H * log(n) + c
    log_sizes = [math.log(s) for s in chunk_sizes]
    log_rs = [math.log(max(r, 1e-10)) for r in rs_values]

    # Simple OLS: H = cov(x,y) / var(x)
    n_pts = len(log_sizes)
    mean_x = sum(log_sizes) / n_pts
    mean_y = sum(log_rs) / n_pts
    cov_xy = sum((log_sizes[i] - mean_x) * (log_rs[i] - mean_y) for i in range(n_pts))
    var_x = sum((x - mean_x) ** 2 for x in log_sizes)

    if var_x == 0:
        return 0.5

    H = cov_xy / var_x
    return max(0.0, min(1.0, H))  # Clamp to [0, 1]
