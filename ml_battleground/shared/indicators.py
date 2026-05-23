"""
Shared technical indicators for ML Battleground.
All functions take pd.Series and return pd.Series (or float for single values).
"""
import numpy as np
import pandas as pd
from typing import Optional


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """Returns (macd_line, signal_line, histogram)."""
    fast_ema = ema(close, fast)
    slow_ema = ema(close, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, min_periods=period).mean()


def bollinger_bands(close: pd.Series, period: int = 20, std_mult: float = 2.0):
    """Returns (upper, middle, lower, width, pctb)."""
    middle = sma(close, period)
    std = close.rolling(period).std()
    upper = middle + std_mult * std
    lower = middle - std_mult * std
    width = (upper - lower) / middle
    pctb = (close - lower) / (upper - lower).replace(0, np.nan)
    return upper, middle, lower, width, pctb


def keltner_channels(high: pd.Series, low: pd.Series, close: pd.Series,
                     ema_period: int = 20, atr_period: int = 14, atr_mult: float = 1.5):
    """Returns (upper, middle, lower)."""
    middle = ema(close, ema_period)
    atr_val = atr(high, low, close, atr_period)
    upper = middle + atr_mult * atr_val
    lower = middle - atr_mult * atr_val
    return upper, middle, lower


def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    mask = plus_dm < minus_dm
    plus_dm[mask] = 0
    minus_dm[~mask] = 0
    atr_val = atr(high, low, close, period)
    plus_di = 100 * ema(plus_dm, period) / atr_val.replace(0, np.nan)
    minus_di = 100 * ema(minus_dm, period) / atr_val.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return ema(dx, period), plus_di, minus_di


def supertrend(high: pd.Series, low: pd.Series, close: pd.Series,
               period: int = 10, multiplier: float = 3.0) -> pd.Series:
    """Returns pd.Series of 1 (bullish) or -1 (bearish)."""
    hl2 = (high + low) / 2
    atr_val = atr(high, low, close, period)
    upper_band = hl2 + multiplier * atr_val
    lower_band = hl2 - multiplier * atr_val

    direction = pd.Series(1, index=close.index)
    final_upper = upper_band.copy()
    final_lower = lower_band.copy()

    for i in range(1, len(close)):
        if lower_band.iloc[i] > final_lower.iloc[i - 1]:
            final_lower.iloc[i] = lower_band.iloc[i]
        else:
            final_lower.iloc[i] = final_lower.iloc[i - 1]
        if upper_band.iloc[i] < final_upper.iloc[i - 1]:
            final_upper.iloc[i] = upper_band.iloc[i]
        else:
            final_upper.iloc[i] = final_upper.iloc[i - 1]

        if direction.iloc[i - 1] == 1:
            if close.iloc[i] < final_lower.iloc[i]:
                direction.iloc[i] = -1
            else:
                direction.iloc[i] = 1
        else:
            if close.iloc[i] > final_upper.iloc[i]:
                direction.iloc[i] = 1
            else:
                direction.iloc[i] = -1

    return direction


def stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
               k_period: int = 14, d_period: int = 3):
    """Returns (%K, %D)."""
    lowest_low = low.rolling(k_period).min()
    highest_high = high.rolling(k_period).max()
    k = 100 * (close - lowest_low) / (highest_high - lowest_low).replace(0, np.nan)
    d = sma(k, d_period)
    return k, d


def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    highest_high = high.rolling(period).max()
    lowest_low = low.rolling(period).min()
    return -100 * (highest_high - close) / (highest_high - lowest_low).replace(0, np.nan)


def cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
    tp = (high + low + close) / 3
    sma_tp = sma(tp, period)
    mad = tp.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    return (tp - sma_tp) / (0.015 * mad).replace(0, np.nan)


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff()).fillna(0)
    return (volume * direction).cumsum()


def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    tp = (high + low + close) / 3
    return (tp * volume).cumsum() / volume.cumsum().replace(0, np.nan)


def hurst_exponent(series: pd.Series, max_lag: int = 50) -> float:
    """Estimate Hurst exponent. H > 0.5 = trending, H < 0.5 = mean-reverting."""
    if len(series) < max_lag * 2:
        return 0.5
    lags = range(2, max_lag)
    tau = []
    for lag in lags:
        diff = series.diff(lag).dropna()
        if len(diff) > 0:
            tau.append(np.sqrt(np.abs(diff).mean()))
        else:
            tau.append(np.nan)
    tau = np.array(tau)
    valid = ~np.isnan(tau) & (tau > 0)
    if valid.sum() < 5:
        return 0.5
    log_lags = np.log(np.array(list(lags))[valid])
    log_tau = np.log(tau[valid])
    poly = np.polyfit(log_lags, log_tau, 1)
    return max(0.0, min(1.0, poly[0]))


def realized_volatility(close: pd.Series, period: int = 20) -> pd.Series:
    """Annualized realized volatility from log returns."""
    log_ret = np.log(close / close.shift(1))
    return log_ret.rolling(period).std() * np.sqrt(365 * 24)  # hourly assumption


def rate_of_change(close: pd.Series, period: int = 7) -> pd.Series:
    """Price momentum: (close / close[n]) - 1. Strong alpha in 1-7 day horizons."""
    return close / close.shift(period) - 1


def mfi(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 14) -> pd.Series:
    """Money Flow Index — volume-weighted RSI. Overbought >80, oversold <20."""
    tp = (high + low + close) / 3
    raw_mf = tp * volume
    delta = tp.diff()
    pos_mf = raw_mf.where(delta > 0, 0).rolling(period).sum()
    neg_mf = raw_mf.where(delta <= 0, 0).rolling(period).sum()
    mfi_ratio = pos_mf / neg_mf.replace(0, np.nan)
    return 100 - (100 / (1 + mfi_ratio))


def chaikin_money_flow(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 20) -> pd.Series:
    """CMF: accumulation/distribution pressure. >0 = buying, <0 = selling."""
    hl_range = (high - low).replace(0, np.nan)
    clv = ((close - low) - (high - close)) / hl_range
    return (clv * volume).rolling(period).sum() / volume.rolling(period).sum().replace(0, np.nan)


def ichimoku_cloud(high: pd.Series, low: pd.Series, tenkan_period: int = 9, kijun_period: int = 26, senkou_b_period: int = 52):
    """Returns (tenkan_sen, kijun_sen, senkou_a, senkou_b, chikou_span).
    Tenkan = (highest high + lowest low) / 2 over period."""
    tenkan = (high.rolling(tenkan_period).max() + low.rolling(tenkan_period).min()) / 2
    kijun = (high.rolling(kijun_period).max() + low.rolling(kijun_period).min()) / 2
    senkou_a = ((tenkan + kijun) / 2).shift(kijun_period)
    senkou_b = ((high.rolling(senkou_b_period).max() + low.rolling(senkou_b_period).min()) / 2).shift(kijun_period)
    chikou = low.shift(-kijun_period)  # simplified
    return tenkan, kijun, senkou_a, senkou_b, chikou


def volume_profile_poc(close: pd.Series, volume: pd.Series, n_bins: int = 20, lookback: int = 100) -> float:
    """Point of Control: price level with highest volume in recent history.
    Returns the POC price level."""
    c = close.iloc[-lookback:].values
    v = volume.iloc[-lookback:].values
    bins = np.linspace(c.min(), c.max(), n_bins + 1)
    vol_profile = np.zeros(n_bins)
    for i in range(len(c)):
        idx = min(int((c[i] - c.min()) / (c.max() - c.min() + 1e-10) * n_bins), n_bins - 1)
        vol_profile[idx] += v[i]
    poc_idx = int(np.argmax(vol_profile))
    return float((bins[poc_idx] + bins[poc_idx + 1]) / 2)


def linear_regression_slope(series: pd.Series, period: int = 20) -> pd.Series:
    """Slope of linear regression over rolling window. Normalized by price."""
    def _slope(arr):
        if len(arr) < 2 or arr[-1] == 0:
            return 0.0
        x = np.arange(len(arr))
        try:
            m = np.polyfit(x, arr, 1)[0]
            return m / arr[-1]  # normalize by current value
        except Exception:
            return 0.0
    return series.rolling(period).apply(_slope, raw=True)


def btc_correlation(close: pd.Series, btc_close: pd.Series, period: int = 30) -> pd.Series:
    """Rolling correlation with BTC. High correlation = move with market, low = independent alpha."""
    return close.pct_change().rolling(period).corr(btc_close.pct_change())


def atr_gate(current_atr: float, atr_series: pd.Series, lookback: int = 30) -> float:
    """ATR crash-protection gate for Keltner strategies.

    Returns position multiplier:
      1.0 — normal conditions
      0.5 — high volatility (ATR > 2x 30-day mean) — reduce size 50%
      0.0 — extreme volatility (ATR > 3x 30-day mean) — skip trade

    Rationale: Keltner WR drops 72.9% -> 42.1% during crashes (v93/v95 stress test).
    """
    if len(atr_series) < lookback + 1 or current_atr <= 0:
        return 1.0

    mean_atr = float(atr_series.iloc[-lookback:].mean())
    if mean_atr <= 0:
        return 1.0

    ratio = current_atr / mean_atr
    if ratio > 3.0:
        return 0.0
    elif ratio > 2.0:
        return 0.5
    return 1.0


def atr_volatility_regime(high: pd.Series, low: pd.Series, close: pd.Series,
                          atr_period: int = 14, mean_period: int = 30) -> dict:
    """
    ATR-based volatility regime detector for crash-stress resilience.

    Computes current ATR(14) and its 30-bar simple moving average.
    Returns a dict with regime flags and position scaling.

    Rationale: Keltner WR drops 72.9% -> 42.1% during crashes (v93/v95 stress test).
    Reduce size 50% when ATR > 2x mean; skip entirely when > 3x.
    """
    atr_series = atr(high, low, close, atr_period)

    if len(atr_series) < mean_period + 1:
        return {
            "atr_current": float(atr_series.iloc[-1]) if len(atr_series) > 0 else 0.0,
            "atr_mean": 0.0,
            "atr_ratio": 1.0,
            "high_volatility_regime": False,
            "extreme_volatility": False,
            "position_scale": 1.0,
        }

    atr_current = float(atr_series.iloc[-1])
    atr_mean = float(atr_series.rolling(mean_period).mean().iloc[-1])

    if atr_mean <= 0:
        atr_ratio = 1.0
    else:
        atr_ratio = atr_current / atr_mean

    extreme = atr_ratio > 3.0
    high_vol = atr_ratio > 2.0

    if extreme:
        position_scale = 0.0
    elif high_vol:
        position_scale = 0.5
    else:
        position_scale = 1.0

    return {
        "atr_current": round(atr_current, 8),
        "atr_mean": round(atr_mean, 8),
        "atr_ratio": round(atr_ratio, 3),
        "high_volatility_regime": high_vol,
        "extreme_volatility": extreme,
        "position_scale": position_scale,
    }
