"""
ALPHA_ENGINE -- Technical Indicators
====================================
Pure functions for technical analysis. No side effects, no data fetching.
Each function takes pandas Series/DataFrame and returns computed values.

References:
  - Wilder (1978): RSI, ATR, ADX
  - Bollinger (2001): Bollinger Bands
  - Hosoda (1969): Ichimoku Cloud
  - Appel (1979): MACD
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Trend indicators
# ---------------------------------------------------------------------------

def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def vwma(close: pd.Series, volume: pd.Series, period: int) -> pd.Series:
    """Volume-Weighted Moving Average."""
    vol = volume.replace(0, np.nan).fillna(1)
    return (close * vol).rolling(period).sum() / vol.rolling(period).sum()


def hma(series: pd.Series, period: int = 21) -> pd.Series:
    """Hull Moving Average (Alan Hull 2005) -- lag-reduced trend direction."""
    half = max(1, period // 2)
    sqrt_n = max(1, int(period ** 0.5))
    wma_half = series.ewm(span=half, adjust=False).mean()
    wma_full = series.ewm(span=period, adjust=False).mean()
    raw = 2 * wma_half - wma_full
    return raw.ewm(span=sqrt_n, adjust=False).mean()


def hma_slope(series: pd.Series, period: int = 21) -> pd.Series:
    """HMA trend direction: +1 uptrend, -1 downtrend, 0 flat."""
    h = hma(series, period)
    return np.sign(h.diff())


def ichimoku(high: pd.Series, low: pd.Series, close: pd.Series,
             tenkan: int = 9, kijun: int = 26,
             senkou_b: int = 52, displacement: int = 26) -> dict[str, pd.Series]:
    """
    Ichimoku Cloud -- all 5 lines.
    Reference: Hosoda (1969), adapted for crypto with longer periods.

    Returns dict with keys: tenkan_sen, kijun_sen, senkou_a, senkou_b, chikou_span
    """
    # Tenkan-sen (conversion line): (highest high + lowest low) / 2 over tenkan period
    tenkan_sen = (high.rolling(tenkan).max() + low.rolling(tenkan).min()) / 2

    # Kijun-sen (base line): (highest high + lowest low) / 2 over kijun period
    kijun_sen = (high.rolling(kijun).max() + low.rolling(kijun).min()) / 2

    # Senkou Span A (leading span A): (tenkan + kijun) / 2, shifted forward
    senkou_a = ((tenkan_sen + kijun_sen) / 2).shift(displacement)

    # Senkou Span B (leading span B): (highest high + lowest low) / 2 over senkou_b, shifted forward
    senkou_b_line = ((high.rolling(senkou_b).max() + low.rolling(senkou_b).min()) / 2).shift(displacement)

    # Chikou Span (lagging span): close shifted back
    chikou_span = close.shift(-displacement)

    return {
        "tenkan_sen": tenkan_sen,
        "kijun_sen": kijun_sen,
        "senkou_a": senkou_a,
        "senkou_b": senkou_b_line,
        "chikou_span": chikou_span,
    }


# ---------------------------------------------------------------------------
# Momentum indicators
# ---------------------------------------------------------------------------

def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """
    Relative Strength Index -- Wilder smoothing.
    Reference: Wilder (1978), "New Concepts in Technical Trading Systems"
    """
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def stoch_rsi(close: pd.Series, rsi_period: int = 14, stoch_period: int = 14,
              k_smooth: int = 3, d_smooth: int = 3) -> dict[str, pd.Series]:
    """Stochastic RSI -- RSI applied to RSI."""
    rsi_vals = rsi(close, rsi_period)
    rsi_min = rsi_vals.rolling(stoch_period).min()
    rsi_max = rsi_vals.rolling(stoch_period).max()
    stoch = (rsi_vals - rsi_min) / (rsi_max - rsi_min).replace(0, np.nan)
    k = stoch.rolling(k_smooth).mean() * 100
    d = k.rolling(d_smooth).mean()
    return {"k": k, "d": d}


def macd(close: pd.Series, fast: int = 12, slow: int = 26,
         signal: int = 9) -> dict[str, pd.Series]:
    """MACD -- Moving Average Convergence Divergence. Reference: Appel (1979)."""
    fast_ema = ema(close, fast)
    slow_ema = ema(close, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}


def adx(high: pd.Series, low: pd.Series, close: pd.Series,
        period: int = 14) -> pd.Series:
    """
    Average Directional Index -- trend strength.
    Reference: Wilder (1978). ADX > 25 = trending, < 20 = ranging.
    """
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    tr = atr(high, low, close, period) * period  # True range sum
    plus_di = 100 * ema(plus_dm, period) / tr.replace(0, np.nan)
    minus_di = 100 * ema(minus_dm, period) / tr.replace(0, np.nan)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return ema(dx, period)


# ---------------------------------------------------------------------------
# Volatility indicators
# ---------------------------------------------------------------------------

def atr(high: pd.Series, low: pd.Series, close: pd.Series,
        period: int = 14) -> pd.Series:
    """Average True Range -- Wilder (1978)."""
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return true_range.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()


def bollinger_bands(close: pd.Series, period: int = 20,
                    num_std: float = 2.0) -> dict[str, pd.Series]:
    """
    Bollinger Bands -- Reference: Bollinger (2001).
    Returns upper, middle, lower bands + bandwidth + %B.
    """
    middle = sma(close, period)
    std = close.rolling(period).std()
    upper = middle + num_std * std
    lower = middle - num_std * std
    bandwidth = (upper - lower) / middle
    pct_b = (close - lower) / (upper - lower).replace(0, np.nan)
    return {
        "upper": upper, "middle": middle, "lower": lower,
        "bandwidth": bandwidth, "pct_b": pct_b,
    }


def keltner_channels(high: pd.Series, low: pd.Series, close: pd.Series,
                     ema_period: int = 20, atr_period: int = 10,
                     atr_mult: float = 1.5) -> dict[str, pd.Series]:
    """Keltner Channels -- EMA ± ATR multiple."""
    mid = ema(close, ema_period)
    atr_val = atr(high, low, close, atr_period)
    return {
        "upper": mid + atr_mult * atr_val,
        "middle": mid,
        "lower": mid - atr_mult * atr_val,
    }


def bollinger_squeeze(close: pd.Series, high: pd.Series, low: pd.Series,
                      bb_period: int = 20, kc_period: int = 20) -> pd.Series:
    """
    Squeeze detection: BB inside Keltner = compression.
    Returns boolean Series: True when squeezed.
    """
    bb = bollinger_bands(close, bb_period)
    kc = keltner_channels(high, low, close, kc_period)
    return (bb["lower"] > kc["lower"]) & (bb["upper"] < kc["upper"])


# ---------------------------------------------------------------------------
# Volume indicators
# ---------------------------------------------------------------------------

def volume_ratio(volume: pd.Series, period: int = 20) -> pd.Series:
    """Current volume / average volume over period."""
    avg = volume.rolling(period).mean()
    ratio = volume / avg.replace(0, np.nan)
    return ratio.fillna(0.0)


def volume_expansion(volume: pd.Series, period: int = 20, threshold: float = 1.2) -> pd.Series:
    """Boolean: True when current volume exceeds threshold × average."""
    avg = volume.rolling(period).mean()
    return volume > (threshold * avg)


def mfi(high: pd.Series, low: pd.Series, close: pd.Series,
        volume: pd.Series, period: int = 14) -> pd.Series:
    """
    Money Flow Index -- volume-weighted RSI.
    Reference: Quong & Soudack (1989). MFI > 80 = overbought, < 20 = oversold.
    """
    typical = (high + low + close) / 3.0
    raw_mf = typical * volume
    delta = typical.diff()
    pos_mf = raw_mf.where(delta > 0, 0.0)
    neg_mf = raw_mf.where(delta < 0, 0.0)
    pos_sum = pos_mf.rolling(window=period, min_periods=period).sum()
    neg_sum = neg_mf.rolling(window=period, min_periods=period).sum()
    mf_ratio = pos_sum / neg_sum.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + mf_ratio))


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On-Balance Volume."""
    direction = np.sign(close.diff()).fillna(0)
    return (direction * volume).cumsum()


def vwap_session(high: pd.Series, low: pd.Series, close: pd.Series,
                 volume: pd.Series) -> pd.Series:
    """VWAP -- cumulative (session-level approximation for daily data)."""
    typical = (high + low + close) / 3.0
    cum_tp_vol = (typical * volume).cumsum()
    cum_vol = volume.cumsum()
    return cum_tp_vol / cum_vol.replace(0, np.nan)


# ---------------------------------------------------------------------------
# Statistical
# ---------------------------------------------------------------------------

def zscore(series: pd.Series, lookback: int) -> pd.Series:
    """Rolling z-score."""
    m = series.rolling(lookback).mean()
    s = series.rolling(lookback).std().replace(0, np.nan)
    return (series - m) / s


def rolling_beta(returns: pd.Series, bench_returns: pd.Series,
                 lookback: int = 60) -> pd.Series:
    """Rolling beta vs benchmark."""
    cov = returns.rolling(lookback).cov(bench_returns)
    var = bench_returns.rolling(lookback).var().replace(0, np.nan)
    return cov / var


def rolling_correlation(a: pd.Series, b: pd.Series, lookback: int = 30) -> pd.Series:
    """Rolling Pearson correlation."""
    return a.rolling(lookback).corr(b)


def hurst_exponent(series: pd.Series, max_lag: int = 20) -> float:
    """
    Hurst exponent -- measures persistence/mean-reversion.
    H > 0.5 = trending, H < 0.5 = mean-reverting, H ≈ 0.5 = random walk.
    """
    lags = range(2, min(max_lag + 1, len(series) // 2))
    tau = []
    for lag in lags:
        diffs = (series.iloc[lag:].values - series.iloc[:-lag].values)
        tau.append(np.sqrt(np.nanstd(diffs)))
    if len(tau) < 2 or any(t == 0 for t in tau):
        return 0.5
    log_lags = np.log(list(lags))
    log_tau = np.log(tau)
    poly = np.polyfit(log_lags, log_tau, 1)
    return poly[0]


def shannon_entropy(returns: pd.Series, bins: int = 20) -> float:
    """
    Shannon entropy of return distribution.
    High entropy = uniform/chaotic, low entropy = concentrated/predictable.
    Reference: Adaptive entropy thresholds -- KIMI research notes.
    """
    clean = returns.dropna()
    if len(clean) < bins:
        return 0.5
    hist, _ = np.histogram(clean, bins=bins, density=True)
    hist = hist[hist > 0]
    hist = hist / hist.sum()
    return float(-np.sum(hist * np.log2(hist)) / np.log2(bins))


# ---------------------------------------------------------------------------
# Pattern detection
# ---------------------------------------------------------------------------

def detect_divergence(price: pd.Series, indicator: pd.Series,
                      lookback: int = 14) -> pd.Series:
    """
    Detect bullish divergence: price makes lower low, indicator makes higher low.
    Returns boolean Series.
    """
    result = pd.Series(False, index=price.index)
    for i in range(lookback * 2, len(price)):
        window_p = price.iloc[i - lookback:i + 1]
        window_i = indicator.iloc[i - lookback:i + 1]
        p_min_idx = window_p.idxmin()
        p_prev_min = price.iloc[i - lookback * 2:i - lookback + 1].min()
        i_at_min = indicator.loc[p_min_idx] if p_min_idx in indicator.index else np.nan
        i_prev_min = indicator.iloc[i - lookback * 2:i - lookback + 1].min()
        if (not np.isnan(i_at_min) and not np.isnan(i_prev_min) and
                not np.isnan(p_prev_min)):
            if window_p.min() < p_prev_min and i_at_min > i_prev_min:
                result.iloc[i] = True
    return result


def detect_support_resistance(close: pd.Series,
                              lookback: int = 60,
                              num_levels: int = 3) -> dict[str, list[float]]:
    """
    Detect key support/resistance levels using price clustering.
    Returns dict with 'support' and 'resistance' lists.
    """
    window = close.iloc[-lookback:]
    current = close.iloc[-1]

    # Find local minima and maxima
    mins = []
    maxs = []
    for i in range(2, len(window) - 2):
        if window.iloc[i] <= window.iloc[i - 1] and window.iloc[i] <= window.iloc[i + 1]:
            mins.append(window.iloc[i])
        if window.iloc[i] >= window.iloc[i - 1] and window.iloc[i] >= window.iloc[i + 1]:
            maxs.append(window.iloc[i])

    supports = sorted([m for m in mins if m < current], reverse=True)[:num_levels]
    resistances = sorted([m for m in maxs if m > current])[:num_levels]
    return {"support": supports, "resistance": resistances}


def detect_accumulation_phase(close: pd.Series, volume: pd.Series,
                              lookback: int = 30) -> dict[str, float]:
    """
    Wyckoff accumulation detection.
    Returns dict with 'is_accumulating' bool and 'phase_score' 0-1.
    Reference: Wyckoff Method (1930s), adapted for modern markets.
    """
    if len(close) < lookback:
        return {"is_accumulating": False, "phase_score": 0.0}

    window_c = close.iloc[-lookback:]
    window_v = volume.iloc[-lookback:]

    # Check range contraction (price consolidation)
    price_range = (window_c.max() - window_c.min()) / window_c.mean()
    range_score = max(0, 1.0 - price_range / 0.15)

    # Check volume decline (smart money accumulating quietly)
    vol_first_half = window_v.iloc[:lookback // 2].mean()
    vol_second_half = window_v.iloc[lookback // 2:].mean()
    vol_decline = (vol_first_half - vol_second_half) / max(vol_first_half, 1)
    vol_score = min(1.0, max(0, vol_decline / 0.40))

    # Check for spring (brief dip below support then recovery)
    support = window_c.iloc[:lookback // 2].min()
    recent_low = window_c.iloc[-5:].min()
    current_price = close.iloc[-1]
    spring_score = 0.0
    if recent_low < support and current_price > support:
        spring_score = 0.5

    phase_score = (range_score * 0.35 + vol_score * 0.35 + spring_score * 0.30)
    return {
        "is_accumulating": phase_score > 0.50,
        "phase_score": round(phase_score, 3),
    }

# ---------------------------------------------------------------------------
# Additional missing indicators
# ---------------------------------------------------------------------------

_FNG_CACHE = {"value": 50.0, "fetched_at": 0}

def fear_and_greed_index() -> float:
    """Fetch Fear & Greed Index from alternative.me (free, no API key).
    Caches for 10 minutes to avoid rate limiting.
    Falls back to 50.0 if API is unreachable.
    """
    import time
    now = time.time()
    if now - _FNG_CACHE["fetched_at"] < 600:  # 10-min cache
        return _FNG_CACHE["value"]
    import requests
    for _attempt in range(3):
        try:
            r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5)
            if r.ok:
                data = r.json()
                if data and data.get("data"):
                    val = float(data["data"][0]["value"])
                    _FNG_CACHE["value"] = val
                    _FNG_CACHE["fetched_at"] = now
                    return val
        except Exception:
            pass
        if _attempt < 2:
            time.sleep(2 * (_attempt + 1))
    return _FNG_CACHE["value"]


def stochastic_rsi(close: pd.Series, period: int = 14, smooth_k: int = 3, smooth_d: int = 3) -> pd.DataFrame:
    """Stochastic RSI – combines RSI and Stochastic oscillator.
    Returns DataFrame with columns 'k' and 'd'.
    """
    rsi = ta.rsi(close, period)
    min_rsi = rsi.rolling(period).min()
    max_rsi = rsi.rolling(period).max()
    k = 100 * (rsi - min_rsi) / (max_rsi - min_rsi).replace(0, np.nan)
    k = k.ewm(alpha=1/ smooth_k, adjust=False).mean()
    d = k.ewm(alpha=1/ smooth_d, adjust=False).mean()
    return pd.DataFrame({"k": k, "d": d})



def fair_value_gap(high: pd.Series, low: pd.Series,
                   min_gap_pct: float = 0.005) -> pd.DataFrame:
    """
    Fair Value Gap (FVG) detection -- Smart Money Concepts.
    A gap between candle N-2 high and candle N low (bullish FVG).
    Returns DataFrame with gap info.
    """
    gaps = []
    for i in range(2, len(high)):
        # Bullish FVG: current low > 2-candles-ago high
        gap = low.iloc[i] - high.iloc[i - 2]
        if gap > 0:
            gap_pct = gap / high.iloc[i - 2]
            if gap_pct >= min_gap_pct:
                gaps.append({
                    "index": high.index[i],
                    "type": "bullish",
                    "gap_low": high.iloc[i - 2],
                    "gap_high": low.iloc[i],
                    "gap_pct": gap_pct,
                })
        # Bearish FVG: current high < 2-candles-ago low
        gap_bear = low.iloc[i - 2] - high.iloc[i]
        if gap_bear > 0:
            gap_pct = gap_bear / low.iloc[i - 2]
            if gap_pct >= min_gap_pct:
                gaps.append({
                    "index": high.index[i],
                    "type": "bearish",
                    "gap_low": high.iloc[i],
                    "gap_high": low.iloc[i - 2],
                    "gap_pct": gap_pct,
                })
    return pd.DataFrame(gaps) if gaps else pd.DataFrame(
        columns=["index", "type", "gap_low", "gap_high", "gap_pct"])
