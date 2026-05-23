"""
Feature Family 5: Mean Reversion

Short-term reversal, z-scores vs bands, overnight vs intraday effects.
Counter-trend signals that work best in range-bound / high-vol regimes.
"""
import numpy as np
import pandas as pd


def compute_mean_reversion_features(
    close: pd.DataFrame,
    high: pd.DataFrame = None,
    low: pd.DataFrame = None,
) -> pd.DataFrame:
    """
    Compute mean reversion features.
    
    Features (stacked):
    - Short-term reversal (1-5 day)
    - Bollinger Band z-scores
    - Distance from VWAP proxy
    - Overnight gap
    - RSI extremes
    - Price oscillator
    - Hurst exponent proxy
    """
    features = {}
    returns = close.pct_change()

    # ── Short-Term Reversal ───────────────────────────────────────────────
    # Stocks that went down recently tend to bounce (at short horizons)
    for w in [1, 3, 5]:
        features[f"reversal_{w}d"] = (-returns.rolling(w).sum()).stack()

    # ── Bollinger Band Z-Score ────────────────────────────────────────────
    for w in [20, 50]:
        ma = close.rolling(w).mean()
        std = close.rolling(w).std()
        zscore = (close - ma) / std.replace(0, np.nan)
        features[f"bb_zscore_{w}d"] = zscore.stack()

        # Bandwidth (vol measure)
        bandwidth = (2 * std) / ma
        features[f"bb_width_{w}d"] = bandwidth.stack()

    # ── Bollinger Band Position ───────────────────────────────────────────
    for w in [20]:
        ma = close.rolling(w).mean()
        std = close.rolling(w).std()
        upper = ma + 2 * std
        lower = ma - 2 * std
        bb_pos = (close - lower) / (upper - lower).replace(0, np.nan)
        features[f"bb_position_{w}d"] = bb_pos.stack()

    # ── Keltner Channel Z-Score ───────────────────────────────────────────
    if high is not None and low is not None:
        ema20 = close.ewm(span=20).mean()
        atr = _simple_atr(close, high, low, 20)
        upper_k = ema20 + 2 * atr
        lower_k = ema20 - 2 * atr
        keltner_pos = (close - lower_k) / (upper_k - lower_k).replace(0, np.nan)
        features["keltner_pos"] = keltner_pos.stack()

        # Squeeze: Bollinger inside Keltner = low vol, about to expand
        bb_upper = close.rolling(20).mean() + 2 * close.rolling(20).std()
        bb_lower = close.rolling(20).mean() - 2 * close.rolling(20).std()
        squeeze = ((bb_upper < upper_k) & (bb_lower > lower_k)).astype(float)
        features["squeeze"] = squeeze.stack()

    # ── Distance from N-day Mean ──────────────────────────────────────────
    for w in [5, 10, 20]:
        mean = close.rolling(w).mean()
        dist = (close - mean) / mean
        features[f"dist_mean_{w}d"] = dist.stack()

    # ── Stochastic Oscillator ─────────────────────────────────────────────
    if high is not None and low is not None:
        for w in [14]:
            lowest_low = low.rolling(w).min()
            highest_high = high.rolling(w).max()
            stoch_k = (close - lowest_low) / (highest_high - lowest_low).replace(0, np.nan) * 100
            stoch_d = stoch_k.rolling(3).mean()
            features[f"stoch_k_{w}"] = stoch_k.stack()
            features[f"stoch_d_{w}"] = stoch_d.stack()

    # ── Overnight Gap (open vs prev close proxy) ──────────────────────────
    # Without open data, approximate with consecutive close returns
    gap = returns - returns.rolling(5).mean()
    features["gap_from_trend"] = gap.stack()

    # ── Hurst Exponent Proxy ──────────────────────────────────────────────
    # H < 0.5 = mean reverting, H > 0.5 = trending, H = 0.5 = random walk
    for w in [63, 126]:
        hurst = _rolling_hurst_proxy(returns, w)
        features[f"hurst_{w}d"] = hurst.stack()

    # ── Mean Reversion Score (composite) ──────────────────────────────────
    # Combine: low BB z-score + high recent vol + short-term reversal
    bb_z = (close - close.rolling(20).mean()) / close.rolling(20).std().replace(0, np.nan)
    rev_5 = -returns.rolling(5).sum()
    mr_composite = bb_z.rank(axis=1, pct=True) * 0.5 + rev_5.rank(axis=1, pct=True) * 0.5
    features["mr_composite_rank"] = mr_composite.stack()

    result = pd.DataFrame(features)
    result.index.names = ["date", "ticker"]
    return result


def _simple_atr(close: pd.DataFrame, high: pd.DataFrame, low: pd.DataFrame, window: int) -> pd.DataFrame:
    """Simplified ATR computation."""
    tr = high - low  # Simplified: just high-low range
    return tr.rolling(window).mean()


def _rolling_hurst_proxy(returns: pd.DataFrame, window: int) -> pd.DataFrame:
    """
    Simplified Hurst exponent estimate using R/S analysis.
    H < 0.5 = mean reverting, H > 0.5 = trending.
    """
    # Use variance ratio as a proxy for Hurst
    # VR = Var(n-period returns) / (n * Var(1-period returns))
    # VR < 1 = mean reverting, VR > 1 = trending
    n = 5
    var_1 = returns.rolling(window).var()
    ret_n = returns.rolling(n).sum()
    var_n = ret_n.rolling(window).var()
    vr = var_n / (n * var_1).replace(0, np.nan)
    # Convert VR to approximate Hurst: H ≈ log(VR) / (2 * log(n)) + 0.5
    hurst = np.log(vr.clip(lower=0.01)) / (2 * np.log(n)) + 0.5
    return hurst.clip(0, 1)
