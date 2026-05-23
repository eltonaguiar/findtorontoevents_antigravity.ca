# -*- coding: utf-8 -*-
"""Mercury 2 — 12-feature causal engine."""

import numpy as np, pandas as pd
from .data_fetcher import fetch_fear_greed, fetch_btc_dominance
from .config import ATR_PERIOD


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ma_up = up.ewm(alpha=1 / period, adjust=False).mean()
    ma_down = down.ewm(alpha=1 / period, adjust=False).mean()
    rs = ma_up / ma_down
    return 100 - (100 / (1 + rs))


def compute_macd(series: pd.Series, fast: int = 12, slow: int = 26) -> pd.Series:
    return series.ewm(span=fast, adjust=False).mean() - series.ewm(span=slow, adjust=False).mean()


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift()).abs(),
        (df["low"] - df["close"].shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def compute_bb_width(prices: pd.Series, period: int = 20) -> pd.Series:
    sma = prices.rolling(period).mean()
    std = prices.rolling(period).std()
    return (2 * std * 2) / sma  # (upper - lower) / sma


def add_features(df: pd.DataFrame, fng: int | None = None,
                 btc_dom: float | None = None,
                 daily_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Add all causal features to a single-symbol DataFrame.

    Args:
        df: OHLCV DataFrame (must have open/high/low/close/volume columns)
        fng: Fear & Greed value (fetched once, reused for all symbols)
        btc_dom: BTC dominance (fetched once, reused)
        daily_df: Optional daily OHLCV for multi-timeframe trend filter

    Returns:
        df with feature columns added, NaN rows dropped.
    """
    # Ensure OHLCV columns are float (some API endpoints return strings)
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Momentum returns
    df["ret_1h"] = df["close"].pct_change(1)
    df["ret_4h"] = df["close"].pct_change(4)
    df["ret_24h"] = df["close"].pct_change(24)

    # Oscillators
    df["rsi_14"] = compute_rsi(df["close"], 14)
    df["macd"] = compute_macd(df["close"])

    # Volatility
    df["atr"] = compute_atr(df, ATR_PERIOD)
    df["bb_width"] = compute_bb_width(df["close"], 20)

    # Volume
    vol_ma = df["volume"].rolling(24).mean()
    df["vol_ratio"] = df["volume"] / vol_ma.replace(0, np.nan)

    # Trend
    df["sma_200"] = df["close"].rolling(200).mean()
    df["above_200"] = (df["close"] > df["sma_200"]).astype(int)

    # Sentiment (scalar, broadcast to all rows)
    if fng is None:
        fng = fetch_fear_greed()
    df["fng"] = fng

    # Macro
    if btc_dom is None:
        btc_dom = fetch_btc_dominance()
    df["btc_dom"] = btc_dom

    # Fractional differentiation — Lopez de Prado, AFML Ch.5
    # Preserves memory while achieving stationarity (d=0.4)
    try:
        from cross_aggregation.frac_diff import frac_diff_ffd
        df["close_ffd"] = frac_diff_ffd(df["close"], d=0.4)
    except Exception:
        pass  # graceful fallback — feature simply absent

    # ── Multi-timeframe features (daily trend filter) ──
    # KIMI research: adding daily 50-MA trend filter improves Sharpe 0.33→0.80 (+142%)
    if daily_df is not None and len(daily_df) >= 50:
        from .config import DAILY_MA_PERIOD
        d_close = daily_df["close"].astype(float)
        d_ma50 = d_close.rolling(DAILY_MA_PERIOD).mean()
        d_macd = compute_macd(d_close)
        d_macd_signal = d_macd.ewm(span=9, adjust=False).mean()
        d_macd_hist = d_macd - d_macd_signal

        # Latest daily values — broadcast to all hourly rows
        df["daily_ma50"] = float(d_ma50.iloc[-1]) if pd.notna(d_ma50.iloc[-1]) else 0.0
        df["daily_macd_hist"] = float(d_macd_hist.iloc[-1]) if pd.notna(d_macd_hist.iloc[-1]) else 0.0
        latest_daily_close = float(d_close.iloc[-1])
        df["daily_trend_up"] = int(latest_daily_close > df["daily_ma50"].iloc[-1]) if df["daily_ma50"].iloc[-1] > 0 else 0
    else:
        df["daily_ma50"] = 0.0
        df["daily_macd_hist"] = 0.0
        df["daily_trend_up"] = -1  # -1 = no daily data (skips MTF filter in risk engine)

    return df


def add_labels_classification(df: pd.DataFrame, horizon: int = 4) -> pd.DataFrame:
    """ATR-based triple-barrier label: 1 if TP hit before SL within horizon.

    Uses ATR(14) to set dynamic TP/SL thresholds per bar, eliminating
    train-serve skew between fixed-% training labels and ATR-based live TP.
    """
    from .config import TP_ATR_MULT, SL_ATR_MULT

    # Ensure ATR column exists
    if "atr" not in df.columns:
        df["atr"] = compute_atr(df, 14)

    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    atr_vals = df["atr"].values
    n = len(df)

    labels = np.full(n, np.nan)

    for i in range(n - horizon):
        entry = close[i]
        atr_now = atr_vals[i]
        if np.isnan(atr_now) or atr_now <= 0 or entry <= 0:
            continue

        tp_price = entry + TP_ATR_MULT * atr_now
        sl_price = entry - SL_ATR_MULT * atr_now

        label = 0  # default: neither hit or SL hit first
        for j in range(i + 1, min(i + horizon + 1, n)):
            if low[j] <= sl_price:
                label = 0
                break
            if high[j] >= tp_price:
                label = 1
                break

        labels[i] = label

    df["label"] = labels
    return df


def add_labels_regression(df: pd.DataFrame, horizon: int = 24) -> pd.DataFrame:
    """Regression label: next-day % return."""
    df["next_ret"] = df["close"].shift(-horizon) / df["close"] - 1
    return df
