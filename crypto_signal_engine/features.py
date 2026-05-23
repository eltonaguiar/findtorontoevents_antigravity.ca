"""Feature engineering and binary labeling.

15 causal features — all use past data only (no look-ahead bias):
  ret_1h       — 1-hour percentage return
  ret_4h       — 4-hour percentage return
  ret_24h      — 24-hour percentage return
  rsi_14       — Relative Strength Index (14-period)
  macd         — Moving Average Convergence Divergence (EMA12 - EMA26)
  atr          — Average True Range (14-period volatility measure)
  bb_width     — Bollinger Band width (measures squeeze/expansion)
  vol_ratio    — Volume vs 24h average (detects unusual activity)
  above_200    — Binary: 1 if price > 200-period SMA (trend regime)
  rsi_slope    — RSI rate of change over 4 bars (momentum acceleration)
  close_ema9   — (close - EMA9) / EMA9 (short-term mean reversion)
  atr_ratio    — ATR / 50-period ATR average (volatility regime: expanding/contracting)
  candle_body  — |close - open| / (high - low) (candle conviction strength)
  high_low_pos — (close - low) / (high - low) (where price closed within range)
  ret_vol_corr — Rolling 12-bar correlation of returns and volume (smart money detection)
"""
import numpy as np
import pandas as pd
from . import config


def rsi(series, period=14):
    """RSI (Relative Strength Index) using exponential moving average.
    RSI > 70 = overbought, RSI < 30 = oversold."""
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ma_up = up.ewm(alpha=1 / period, adjust=False).mean()
    ma_down = down.ewm(alpha=1 / period, adjust=False).mean()
    rs = ma_up / ma_down
    return 100 - (100 / (1 + rs))


def macd(series, fast=12, slow=26):
    """MACD (Moving Average Convergence Divergence).
    Positive = bullish momentum, negative = bearish."""
    return (series.ewm(span=fast, adjust=False).mean()
            - series.ewm(span=slow, adjust=False).mean())


def atr(df, period=14):
    """ATR (Average True Range) — measures price volatility.
    Used for setting TP/SL distances and position sizing."""
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift()).abs(),
        (df["low"] - df["close"].shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def bb_width(prices, period=20):
    """Bollinger Band width as % of SMA.
    Narrow = squeeze (breakout incoming), wide = expansion."""
    sma = prices.rolling(period).mean()
    std = prices.rolling(period).std()
    return (4 * std) / sma


def add_features(df, fng_value=50, btc_dom_value=0.0, funding_rate=0.0):
    """Add all 15 causal features to a DataFrame of OHLCV data.

    Args:
        df: DataFrame with columns [open, high, low, close, vol]
        fng_value: Fear & Greed Index (0-100) — stored for context, not a model feature
        btc_dom_value: BTC dominance percentage — stored for context, not a model feature
        funding_rate: Funding rate — stored for context, not a model feature
    """
    df = df.copy()

    # Returns (momentum)
    df["ret_1h"] = df["close"].pct_change(1)
    df["ret_4h"] = df["close"].pct_change(4)
    df["ret_24h"] = df["close"].pct_change(24)

    # Technical indicators
    df["rsi_14"] = rsi(df["close"], 14)
    df["macd"] = macd(df["close"])

    # Volatility
    df["atr"] = atr(df, config.ATR_PERIOD)
    df["bb_width"] = bb_width(df["close"], 20)

    # Volume anomaly
    vol_ma = df["vol"].rolling(24).mean()
    df["vol_ratio"] = np.where(vol_ma > 0, df["vol"] / vol_ma, 1.0)

    # Trend regime
    df["sma_200"] = df["close"].rolling(200).mean()
    df["above_200"] = (df["close"] > df["sma_200"]).astype(int)

    # RSI momentum acceleration (replaces scalar fng)
    df["rsi_slope"] = df["rsi_14"].diff(4)

    # Mean reversion: distance from 9-period EMA (replaces scalar btc_dom)
    ema9 = df["close"].ewm(span=9, adjust=False).mean()
    df["close_ema9"] = (df["close"] - ema9) / ema9

    # Volatility regime: current ATR vs longer average (replaces scalar funding_z)
    atr_ma50 = df["atr"].rolling(50).mean()
    df["atr_ratio"] = np.where(atr_ma50 > 0, df["atr"] / atr_ma50, 1.0)

    # Candle body strength: how much of the bar is body vs wick
    bar_range = df["high"] - df["low"]
    df["candle_body"] = np.where(
        bar_range > 0,
        (df["close"] - df["open"]).abs() / bar_range,
        0.0,
    )

    # Close position within bar range (0=closed at low, 1=closed at high)
    df["high_low_pos"] = np.where(
        bar_range > 0,
        (df["close"] - df["low"]) / bar_range,
        0.5,
    )

    # Return-volume correlation (smart money indicator)
    df["ret_vol_corr"] = df["ret_1h"].rolling(12).corr(
        df["vol"].pct_change(1)
    )

    # Store sentiment values for context (not model features — they're scalars)
    df["fng"] = float(fng_value)
    df["btc_dom"] = float(btc_dom_value)
    df["funding_z"] = float(funding_rate)

    # Ensure all feature columns are numeric (fixes XGBoost dtype errors)
    for col in config.FEATURES:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.dropna()


def create_labels(df, horizon=None):
    """Binary labels: 1 = price UP after `horizon` bars, 0 = down/flat.

    This gives ~50/50 class balance — unlike cost-gated triple-barrier
    which creates 95%+ class imbalance and makes models learn 'never trade'.
    """
    if horizon is None:
        horizon = config.LABEL_HORIZON
    df = df.copy()
    df["future_ret"] = df["close"].shift(-horizon) / df["close"] - 1
    df["label"] = (df["future_ret"] > 0).astype(int)
    return df.dropna()
