"""
Skyrocket Feature Engine
=========================
Computes 15 zero-lookahead features from OHLCV data for the skyrocket detector.

All features use ONLY past data relative to each bar (no future leakage).
Uses numpy/pandas only -- no external TA libraries required.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _sma(series: np.ndarray, period: int) -> np.ndarray:
    """Simple moving average. Returns NaN for first (period-1) values."""
    result = np.full_like(series, np.nan, dtype=float)
    if len(series) < period:
        return result
    cumsum = np.cumsum(series)
    cumsum[period:] = cumsum[period:] - cumsum[:-period]
    result[period - 1:] = cumsum[period - 1:] / period
    return result


def _ema(series: np.ndarray, period: int) -> np.ndarray:
    """Exponential moving average."""
    result = np.full_like(series, np.nan, dtype=float)
    if len(series) < period:
        return result
    alpha = 2.0 / (period + 1)
    result[period - 1] = np.mean(series[:period])
    for i in range(period, len(series)):
        result[i] = alpha * series[i] + (1 - alpha) * result[i - 1]
    return result


def _rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    """Relative Strength Index."""
    result = np.full_like(close, np.nan, dtype=float)
    if len(close) < period + 1:
        return result

    deltas = np.diff(close)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    if avg_loss == 0:
        result[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        result[period] = 100.0 - (100.0 / (1.0 + rs))

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            result[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[i + 1] = 100.0 - (100.0 / (1.0 + rs))

    return result


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """Average True Range."""
    result = np.full_like(close, np.nan, dtype=float)
    if len(close) < period + 1:
        return result

    tr = np.zeros(len(close))
    tr[0] = high[0] - low[0]
    for i in range(1, len(close)):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )

    # Initial ATR is SMA of first `period` TRs
    result[period] = np.mean(tr[1:period + 1])
    for i in range(period + 1, len(close)):
        result[i] = (result[i - 1] * (period - 1) + tr[i]) / period

    return result


def _linreg_slope(arr: np.ndarray, window: int) -> np.ndarray:
    """Rolling linear regression slope."""
    result = np.full_like(arr, np.nan, dtype=float)
    if len(arr) < window:
        return result
    x = np.arange(window, dtype=float)
    x_mean = x.mean()
    x_var = np.sum((x - x_mean) ** 2)
    if x_var == 0:
        return result
    for i in range(window - 1, len(arr)):
        y = arr[i - window + 1:i + 1]
        if np.any(np.isnan(y)):
            continue
        y_mean = np.mean(y)
        result[i] = np.sum((x - x_mean) * (y - y_mean)) / x_var
    return result


def _obv(close: np.ndarray, volume: np.ndarray) -> np.ndarray:
    """On-Balance Volume."""
    obv = np.zeros_like(close, dtype=float)
    for i in range(1, len(close)):
        if close[i] > close[i - 1]:
            obv[i] = obv[i - 1] + volume[i]
        elif close[i] < close[i - 1]:
            obv[i] = obv[i - 1] - volume[i]
        else:
            obv[i] = obv[i - 1]
    return obv


def _rolling_corr(a: np.ndarray, b: np.ndarray, window: int) -> np.ndarray:
    """Rolling Pearson correlation."""
    result = np.full_like(a, np.nan, dtype=float)
    if len(a) < window:
        return result
    for i in range(window - 1, len(a)):
        x = a[i - window + 1:i + 1]
        y = b[i - window + 1:i + 1]
        if np.any(np.isnan(x)) or np.any(np.isnan(y)):
            continue
        x_std = np.std(x)
        y_std = np.std(y)
        if x_std == 0 or y_std == 0:
            result[i] = 0.0
        else:
            result[i] = np.corrcoef(x, y)[0, 1]
    return result


def _percentile_rank(arr: np.ndarray, window: int) -> np.ndarray:
    """Rolling percentile rank of the last value within its window."""
    result = np.full_like(arr, np.nan, dtype=float)
    if len(arr) < window:
        return result
    for i in range(window - 1, len(arr)):
        win = arr[i - window + 1:i + 1]
        valid = win[~np.isnan(win)]
        if len(valid) < 2:
            continue
        result[i] = np.sum(valid < valid[-1]) / (len(valid) - 1)
    return result


# ---------------------------------------------------------------------------
# Main feature computation
# ---------------------------------------------------------------------------

FEATURE_NAMES = [
    "vol_accel_6h",
    "vol_accel_3h",
    "bb_squeeze_pctile",
    "rsi_14",
    "rsi_slope_6h",
    "obv_divergence",
    "ret_24h",
    "ret_6h",
    "ret_1h",
    "price_compress_ratio",
    "vol_trend_direction",
    "rel_vol_spike",
    "macd_hist",
    "atr_pct",
    "consecutive_green",
]


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute 15 zero-lookahead features from OHLCV data.

    Args:
        df: DataFrame with columns [open, high, low, close, volume].
            Must have at least 100 bars for meaningful features.

    Returns:
        DataFrame with 15 feature columns added.
        Early bars may have NaN where lookback is insufficient.
    """
    df = df.copy()
    n = len(df)

    o = df["open"].values.astype(float)
    h = df["high"].values.astype(float)
    l = df["low"].values.astype(float)
    c = df["close"].values.astype(float)
    v = df["volume"].values.astype(float)

    # 1. vol_accel_6h: volume sum of last 6 bars / volume sum of bars 7-30
    vol_accel_6h = np.full(n, np.nan)
    for i in range(29, n):
        recent = np.sum(v[i - 5:i + 1])       # last 6 bars (i-5 to i inclusive)
        baseline = np.sum(v[i - 29:i - 5])     # bars 7 to 30 back (24 bars)
        if baseline > 0:
            vol_accel_6h[i] = recent / baseline * (24 / 6)  # normalize by bar count ratio
        else:
            vol_accel_6h[i] = 0.0
    df["vol_accel_6h"] = vol_accel_6h

    # 2. vol_accel_3h: volume sum of last 3 bars / volume sum of bars 4-30
    vol_accel_3h = np.full(n, np.nan)
    for i in range(29, n):
        recent = np.sum(v[i - 2:i + 1])       # last 3 bars
        baseline = np.sum(v[i - 29:i - 2])     # bars 4 to 30 back (27 bars)
        if baseline > 0:
            vol_accel_3h[i] = recent / baseline * (27 / 3)  # normalize
        else:
            vol_accel_3h[i] = 0.0
    df["vol_accel_3h"] = vol_accel_3h

    # 3. bb_squeeze_pctile: Bollinger Band width percentile rank over 100 bars
    sma_20 = _sma(c, 20)
    bb_width = np.full(n, np.nan)
    for i in range(19, n):
        window = c[i - 19:i + 1]
        std = np.std(window, ddof=1)
        if sma_20[i] > 0 and not np.isnan(sma_20[i]):
            bb_width[i] = (2 * std) / sma_20[i]
    df["bb_squeeze_pctile"] = _percentile_rank(bb_width, 100)

    # 4. rsi_14
    rsi_vals = _rsi(c, 14)
    df["rsi_14"] = rsi_vals

    # 5. rsi_slope_6h: linear regression slope of RSI over last 6 bars
    df["rsi_slope_6h"] = _linreg_slope(rsi_vals, 6)

    # 6. obv_divergence: correlation between OBV and price over 20 bars
    obv_vals = _obv(c, v)
    df["obv_divergence"] = _rolling_corr(obv_vals, c, 20)

    # 7. ret_24h: return over last 24 bars
    ret_24h = np.full(n, np.nan)
    for i in range(24, n):
        if c[i - 24] > 0:
            ret_24h[i] = c[i] / c[i - 24] - 1.0
    df["ret_24h"] = ret_24h

    # 8. ret_6h: return over last 6 bars
    ret_6h = np.full(n, np.nan)
    for i in range(6, n):
        if c[i - 6] > 0:
            ret_6h[i] = c[i] / c[i - 6] - 1.0
    df["ret_6h"] = ret_6h

    # 9. ret_1h: return over last 1 bar
    ret_1h = np.full(n, np.nan)
    for i in range(1, n):
        if c[i - 1] > 0:
            ret_1h[i] = c[i] / c[i - 1] - 1.0
    df["ret_1h"] = ret_1h

    # 10. price_compress_ratio: (high-low range of last 12 bars) / ATR_14
    atr_vals = _atr(h, l, c, 14)
    compress = np.full(n, np.nan)
    for i in range(11, n):
        range_12 = np.max(h[i - 11:i + 1]) - np.min(l[i - 11:i + 1])
        if not np.isnan(atr_vals[i]) and atr_vals[i] > 0:
            compress[i] = range_12 / atr_vals[i]
    df["price_compress_ratio"] = compress

    # 11. vol_trend_direction: sign of linear regression slope of volume over 12 bars
    vol_slope = _linreg_slope(v, 12)
    df["vol_trend_direction"] = np.sign(vol_slope)

    # 12. rel_vol_spike: current bar volume / SMA(volume, 20)
    vol_sma_20 = _sma(v, 20)
    rel_vol = np.full(n, np.nan)
    for i in range(n):
        if not np.isnan(vol_sma_20[i]) and vol_sma_20[i] > 0:
            rel_vol[i] = v[i] / vol_sma_20[i]
    df["rel_vol_spike"] = rel_vol

    # 13. macd_hist: MACD histogram value
    ema_12 = _ema(c, 12)
    ema_26 = _ema(c, 26)
    macd_line = ema_12 - ema_26
    macd_signal = _ema(macd_line[~np.isnan(macd_line)], 9)
    # Align signal line back to original index
    macd_hist = np.full(n, np.nan)
    valid_idx = np.where(~np.isnan(macd_line))[0]
    if len(valid_idx) >= 9:
        for j, idx in enumerate(valid_idx):
            if j < 8:  # signal EMA needs 9 values
                continue
            if j - 8 < len(macd_signal):
                macd_hist[idx] = macd_line[idx] - macd_signal[j - 8]
    df["macd_hist"] = macd_hist

    # 14. atr_pct: ATR(14) / close
    atr_pct = np.full(n, np.nan)
    for i in range(n):
        if not np.isnan(atr_vals[i]) and c[i] > 0:
            atr_pct[i] = atr_vals[i] / c[i]
    df["atr_pct"] = atr_pct

    # 15. consecutive_green: count of consecutive bullish candles (close > open)
    consec = np.zeros(n)
    for i in range(n):
        if c[i] > o[i]:
            consec[i] = (consec[i - 1] + 1) if i > 0 else 1
        else:
            consec[i] = 0
    df["consecutive_green"] = consec

    return df


def compute_features_for_live(df: pd.DataFrame) -> dict:
    """
    Compute features for the LAST bar only (for live inference).

    Args:
        df: DataFrame with at least 100 bars of OHLCV data.
            Recommended: 300 bars for stable feature computation.

    Returns:
        Dict of {feature_name: value} for the last bar.
        Returns None if insufficient data.
    """
    if len(df) < 100:
        print(f"[feature_engine] WARNING: Only {len(df)} bars, need at least 100 for stable features")
        if len(df) < 30:
            return None

    featured = compute_features(df)
    last_row = featured.iloc[-1]

    result = {}
    for name in FEATURE_NAMES:
        val = last_row.get(name, np.nan)
        result[name] = float(val) if not np.isnan(val) else 0.0

    return result
