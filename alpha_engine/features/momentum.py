"""
Feature Family 1: Trend / Momentum

Multi-horizon returns, moving average slopes, trend strength, breakout distance.
These are the classic "price follows price" signals.
"""
import numpy as np
import pandas as pd
from typing import List


def compute_momentum_features(
    close: pd.DataFrame,
    windows: List[int] = None,
    ma_windows: List[int] = None,
) -> pd.DataFrame:
    """
    Compute trend and momentum features for all tickers.
    
    Features:
    - Multi-horizon returns (1w, 2w, 1m, 3m, 6m, 1y)
    - Moving average slopes (10, 20, 50, 100, 200)
    - Price vs MA distances
    - Trend strength (ADX proxy)
    - Breakout distance (% above N-day high)
    - Momentum acceleration (change in momentum)
    - RSI (multiple windows)
    - MACD and signal
    """
    if windows is None:
        windows = [5, 10, 21, 63, 126, 252]
    if ma_windows is None:
        ma_windows = [10, 20, 50, 100, 200]

    features = pd.DataFrame(index=close.index)

    # ── Multi-Horizon Returns ─────────────────────────────────────────────
    for w in windows:
        ret = close.pct_change(w)
        # Stack tickers: create one column per ticker per feature
        # For efficiency, we'll keep it as wide format and flatten later
        for ticker in close.columns:
            if ticker in ret.columns:
                features[f"ret_{w}d_{ticker}"] = ret[ticker]

    # ── Log Returns (for statistical properties) ──────────────────────────
    for w in [5, 21, 63]:
        log_ret = np.log(close / close.shift(w))
        for ticker in close.columns:
            if ticker in log_ret.columns:
                features[f"logret_{w}d_{ticker}"] = log_ret[ticker]

    # ── Moving Average Slopes ─────────────────────────────────────────────
    for w in ma_windows:
        ma = close.rolling(w).mean()
        slope = ma.pct_change(5)  # 5-day slope of the MA
        for ticker in close.columns:
            features[f"ma{w}_slope_{ticker}"] = slope.get(ticker, np.nan)

    # ── Price vs MA Distance ──────────────────────────────────────────────
    for w in ma_windows:
        ma = close.rolling(w).mean()
        dist = (close - ma) / ma
        for ticker in close.columns:
            features[f"price_vs_ma{w}_{ticker}"] = dist.get(ticker, np.nan)

    # ── MA Crossover Signals ──────────────────────────────────────────────
    for ticker in close.columns:
        if ticker in close.columns:
            ma50 = close[ticker].rolling(50).mean()
            ma200 = close[ticker].rolling(200).mean()
            features[f"golden_cross_{ticker}"] = (ma50 > ma200).astype(float)
            features[f"ma50_200_spread_{ticker}"] = (ma50 - ma200) / ma200

    # ── Trend Strength (ADX proxy via directional movement) ───────────────
    for ticker in close.columns:
        price = close[ticker]
        # Simplified trend strength: consistency of returns
        for w in [21, 63]:
            daily_ret = price.pct_change()
            up_days = (daily_ret > 0).rolling(w).mean()
            features[f"trend_consistency_{w}d_{ticker}"] = up_days
            # Trend strength: magnitude of return / volatility
            ret_w = price.pct_change(w)
            vol_w = daily_ret.rolling(w).std() * np.sqrt(w)
            features[f"trend_strength_{w}d_{ticker}"] = ret_w / vol_w.replace(0, np.nan)

    # ── Breakout Distance ─────────────────────────────────────────────────
    for w in [20, 50, 252]:
        high_w = close.rolling(w).max()
        low_w = close.rolling(w).min()
        for ticker in close.columns:
            features[f"dist_from_{w}d_high_{ticker}"] = (close[ticker] - high_w[ticker]) / high_w[ticker]
            features[f"dist_from_{w}d_low_{ticker}"] = (close[ticker] - low_w[ticker]) / low_w[ticker]

    # ── RSI ───────────────────────────────────────────────────────────────
    for w in [14, 21]:
        for ticker in close.columns:
            features[f"rsi_{w}d_{ticker}"] = _compute_rsi(close[ticker], w)

    # ── MACD ──────────────────────────────────────────────────────────────
    for ticker in close.columns:
        price = close[ticker]
        ema12 = price.ewm(span=12).mean()
        ema26 = price.ewm(span=26).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9).mean()
        features[f"macd_{ticker}"] = macd / price  # Normalize
        features[f"macd_signal_{ticker}"] = signal / price
        features[f"macd_hist_{ticker}"] = (macd - signal) / price

    # ── Momentum Acceleration ─────────────────────────────────────────────
    for ticker in close.columns:
        mom_21 = close[ticker].pct_change(21)
        mom_63 = close[ticker].pct_change(63)
        features[f"mom_accel_{ticker}"] = mom_21 - mom_21.shift(21)
        features[f"mom_ratio_{ticker}"] = mom_21 / mom_63.replace(0, np.nan)

    return features


def compute_momentum_features_stacked(
    close: pd.DataFrame,
    windows: List[int] = None,
) -> pd.DataFrame:
    """
    Compute momentum features in stacked (date, ticker) format.
    More memory efficient for large universes.
    """
    if windows is None:
        windows = [5, 10, 21, 63, 126, 252]

    features = {}

    # Returns
    for w in windows:
        features[f"ret_{w}d"] = close.pct_change(w).stack()

    # Price vs MAs
    for w in [20, 50, 200]:
        ma = close.rolling(w).mean()
        features[f"price_vs_ma{w}"] = ((close - ma) / ma).stack()

    # RSI
    rsi_df = close.apply(lambda x: _compute_rsi(x, 14))
    features["rsi_14"] = rsi_df.stack()

    # Trend strength
    daily_ret = close.pct_change()
    for w in [21, 63]:
        ret_w = close.pct_change(w)
        vol_w = daily_ret.rolling(w).std() * np.sqrt(w)
        features[f"trend_strength_{w}d"] = (ret_w / vol_w.replace(0, np.nan)).stack()

    # Breakout
    for w in [20, 50, 252]:
        high_w = close.rolling(w).max()
        features[f"dist_{w}d_high"] = ((close - high_w) / high_w).stack()

    # MACD (normalized)
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd = (ema12 - ema26) / close
    features["macd_norm"] = macd.stack()

    result = pd.DataFrame(features)
    result.index.names = ["date", "ticker"]
    return result


def _compute_rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """Compute RSI for a price series."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/window, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1/window, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))
