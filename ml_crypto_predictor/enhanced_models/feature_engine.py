"""
Feature Engineering Pipeline
=============================
70+ features across 6 groups: Momentum, Volume, Volatility, Trend, 
Price Structure, Market Context.

Fixes critical gap: old models used only 5 raw OHLCV features.
New approach: derived indicators + cross-asset context + regime signals.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple


# ─── Technical Indicator Helpers ──────────────────────────────────────────────

def _ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()

def _sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(period).mean()

def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    return 100 - (100 / (1 + rs))

def _macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """MACD line, signal line, histogram."""
    ema_fast = _ema(close, fast)
    ema_slow = _ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range."""
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def _adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14):
    """Average Directional Index with +DI and -DI."""
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0), index=high.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0), index=high.index)
    atr_val = _atr(high, low, close, period)
    plus_di = 100 * _ema(plus_dm, period) / (atr_val + 1e-10)
    minus_di = 100 * _ema(minus_dm, period) / (atr_val + 1e-10)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10)
    adx_val = _ema(dx, period)
    return adx_val, plus_di, minus_di

def _bollinger(close: pd.Series, period: int = 20, num_std: float = 2.0):
    """Bollinger Bands: width, %B, squeeze flag."""
    sma = _sma(close, period)
    std = close.rolling(period).std()
    upper = sma + num_std * std
    lower = sma - num_std * std
    width = (upper - lower) / (sma + 1e-10)
    percentb = (close - lower) / (upper - lower + 1e-10)
    # Squeeze: BB width below 20th percentile of its 60-bar history
    width_pctile = width.rolling(60).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False)
    squeeze = (width_pctile < 0.2).astype(float)
    return width, percentb, squeeze

def _obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On-Balance Volume."""
    direction = np.sign(close.diff())
    direction.iloc[0] = 0
    return (direction * volume).cumsum()

def _stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
                k_period: int = 14, d_period: int = 3):
    """Stochastic Oscillator %K and %D."""
    lowest_low = low.rolling(k_period).min()
    highest_high = high.rolling(k_period).max()
    k = 100 * (close - lowest_low) / (highest_high - lowest_low + 1e-10)
    d = _sma(k, d_period)
    return k, d

def _williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Williams %R."""
    highest_high = high.rolling(period).max()
    lowest_low = low.rolling(period).min()
    return -100 * (highest_high - close) / (highest_high - lowest_low + 1e-10)

def _cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
    """Commodity Channel Index."""
    tp = (high + low + close) / 3
    tp_sma = _sma(tp, period)
    mad = tp.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    return (tp - tp_sma) / (0.015 * mad + 1e-10)

def _aroon(high: pd.Series, low: pd.Series, period: int = 25):
    """Aroon Up and Down indicators."""
    aroon_up = high.rolling(period + 1).apply(lambda x: x.argmax() / period * 100, raw=True)
    aroon_down = low.rolling(period + 1).apply(lambda x: x.argmin() / period * 100, raw=True)
    return aroon_up, aroon_down

def _supertrend(high: pd.Series, low: pd.Series, close: pd.Series,
                period: int = 10, multiplier: float = 3.0) -> pd.Series:
    """Supertrend direction signal (1=bullish, -1=bearish)."""
    atr_val = _atr(high, low, close, period)
    hl2 = (high + low) / 2
    upper_band = hl2 + multiplier * atr_val
    lower_band = hl2 - multiplier * atr_val
    
    direction = pd.Series(1, index=close.index)
    for i in range(1, len(close)):
        if close.iloc[i] > upper_band.iloc[i-1]:
            direction.iloc[i] = 1
        elif close.iloc[i] < lower_band.iloc[i-1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i-1]
    return direction


# ─── Main Feature Builder ────────────────────────────────────────────────────

def build_features(df: pd.DataFrame, btc_df: Optional[pd.DataFrame] = None,
                   fear_greed: Optional[float] = None,
                   funding_rate: Optional[float] = None) -> pd.DataFrame:
    """
    Build 70+ features from OHLCV data.
    
    Args:
        df: DataFrame with columns [open, high, low, close, volume] and timestamp index
        btc_df: BTC OHLCV for cross-correlation features (optional)
        fear_greed: Current fear & greed index 0-100 (optional)
        funding_rate: Current Binance funding rate (optional)
    
    Returns:
        DataFrame with all features computed, NaN rows dropped
    """
    o, h, l, c, v = df["open"], df["high"], df["low"], df["close"], df["volume"]
    features = pd.DataFrame(index=df.index)
    
    # ═══ 1. MOMENTUM (15 features) ═══════════════════════════════════════════
    features["rsi_14"] = _rsi(c, 14)
    features["rsi_7"] = _rsi(c, 7)
    features["rsi_slope_5"] = features["rsi_14"].diff(5)
    features["rsi_slope_10"] = features["rsi_14"].diff(10)
    
    macd_line, macd_sig, macd_hist = _macd(c)
    features["macd_hist"] = macd_hist
    features["macd_signal_cross"] = np.sign(macd_line - macd_sig).diff().fillna(0)
    # MACD divergence: price makes new low but MACD makes higher low
    # Detect over rolling 20-bar windows
    price_new_low = (c == c.rolling(20).min())
    macd_higher_low = (macd_hist > macd_hist.rolling(20).min())
    features["macd_divergence"] = (price_new_low & macd_higher_low).astype(float)
    
    features["roc_5"] = c.pct_change(5) * 100
    features["roc_10"] = c.pct_change(10) * 100
    features["roc_20"] = c.pct_change(20) * 100
    
    features["williams_r_14"] = _williams_r(h, l, c, 14)
    features["cci_20"] = _cci(h, l, c, 20)
    
    stoch_k, stoch_d = _stochastic(h, l, c)
    features["stoch_k"] = stoch_k
    features["stoch_d"] = stoch_d
    features["stoch_cross"] = np.sign(stoch_k - stoch_d).diff().fillna(0)
    
    # ═══ 2. VOLUME (9 features) ══════════════════════════════════════════════
    vol_ma_20 = _sma(v, 20)
    vol_ma_5 = _sma(v, 5)
    features["vol_ratio_20"] = v / (vol_ma_20 + 1e-10)
    features["vol_ratio_5"] = v / (vol_ma_5 + 1e-10)
    features["vol_spike_3x"] = (features["vol_ratio_20"] > 3.0).astype(float)
    
    obv = _obv(c, v)
    features["obv_slope"] = obv.diff(5) / (obv.rolling(20).std() + 1e-10)
    # OBV divergence: OBV trending up while price trending down (or vice versa)
    price_trend = np.sign(c.diff(10))
    obv_trend = np.sign(obv.diff(10))
    features["obv_divergence"] = (price_trend != obv_trend).astype(float)
    
    # VWAP proxy (cumulative avg price weighted by volume)
    cumvol = v.cumsum()
    cumvp = (c * v).cumsum()
    vwap = cumvp / (cumvol + 1e-10)
    features["vwap_distance"] = (c - vwap) / (vwap + 1e-10)
    
    features["volume_ma_ratio"] = vol_ma_5 / (vol_ma_20 + 1e-10)
    features["relative_volume_1h"] = v / (v.shift(1) + 1e-10)
    # Cumulative delta proxy: volume * sign(close - open)
    features["cumulative_delta_proxy"] = (v * np.sign(c - o)).rolling(10).sum()
    features["cumulative_delta_proxy"] = features["cumulative_delta_proxy"] / (features["cumulative_delta_proxy"].rolling(50).std() + 1e-10)
    
    # ═══ 3. VOLATILITY (10 features) ═════════════════════════════════════════
    atr_val = _atr(h, l, c, 14)
    features["atr_14"] = atr_val / (c + 1e-10)  # Normalized ATR
    atr_20 = _atr(h, l, c, 20)
    features["atr_ratio"] = atr_val / (atr_20 + 1e-10)
    features["atr_percentile_60"] = atr_val.rolling(60).apply(
        lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False
    )
    
    bb_width, bb_pctb, bb_squeeze = _bollinger(c)
    features["bb_width"] = bb_width
    features["bb_percentb"] = bb_pctb
    features["bb_squeeze"] = bb_squeeze
    
    # Keltner squeeze: BB inside Keltner = extreme compression
    kelt_upper = _ema(c, 20) + 1.5 * atr_val
    kelt_lower = _ema(c, 20) - 1.5 * atr_val
    bb_upper = _sma(c, 20) + 2 * c.rolling(20).std()
    bb_lower = _sma(c, 20) - 2 * c.rolling(20).std()
    features["keltner_squeeze"] = ((bb_lower > kelt_lower) & (bb_upper < kelt_upper)).astype(float)
    
    # Realized volatility 
    log_returns = np.log(c / c.shift(1))
    features["realized_vol_20"] = log_returns.rolling(20).std() * np.sqrt(252)
    
    features["high_low_range_pct"] = (h - l) / (c + 1e-10)
    features["close_to_high_pct"] = (c - l) / (h - l + 1e-10)
    
    # ═══ 4. TREND (12 features) ══════════════════════════════════════════════
    ema5 = _ema(c, 5)
    ema20 = _ema(c, 20)
    ema50 = _ema(c, 50)
    ema200 = _ema(c, 200)
    
    features["ema_5_20_cross"] = np.sign(ema5 - ema20)
    features["ema_20_50_cross"] = np.sign(ema20 - ema50)
    features["ema_50_200_cross"] = np.sign(ema50 - ema200)
    
    features["price_vs_ema20"] = (c - ema20) / (ema20 + 1e-10)
    features["price_vs_ema50"] = (c - ema50) / (ema50 + 1e-10)
    features["price_vs_ema200"] = (c - ema200) / (ema200 + 1e-10)
    
    adx_val, di_plus, di_minus = _adx(h, l, c, 14)
    features["adx_14"] = adx_val
    features["di_plus"] = di_plus
    features["di_minus"] = di_minus
    
    aroon_up, aroon_down = _aroon(h, l, 25)
    features["aroon_up"] = aroon_up
    features["aroon_down"] = aroon_down
    
    features["supertrend_signal"] = _supertrend(h, l, c, 10, 3.0)
    
    # ═══ 5. PRICE STRUCTURE (10 features) ════════════════════════════════════
    # Higher highs / lower lows (3-bar lookback)
    features["higher_highs_3"] = ((h > h.shift(1)) & (h.shift(1) > h.shift(2)) & (h.shift(2) > h.shift(3))).astype(float)
    features["lower_lows_3"] = ((l < l.shift(1)) & (l.shift(1) < l.shift(2)) & (l.shift(2) < l.shift(3))).astype(float)
    
    # Candlestick patterns
    body = (c - o).abs()
    total_range = h - l + 1e-10
    features["inside_bar"] = ((h < h.shift(1)) & (l > l.shift(1))).astype(float)
    features["outside_bar"] = ((h > h.shift(1)) & (l < l.shift(1))).astype(float)
    features["doji_pattern"] = (body / total_range < 0.1).astype(float)
    features["engulfing_pattern"] = (
        (body > body.shift(1) * 1.5) &
        (np.sign(c - o) != np.sign(c.shift(1) - o.shift(1)))
    ).astype(float)
    
    # Consolidation
    rolling_high = h.rolling(20).max()
    rolling_low = l.rolling(20).min()
    features["consolidation_range_20"] = (rolling_high - rolling_low) / (c + 1e-10)
    features["price_compression"] = c.rolling(10).std() / (c.rolling(50).std() + 1e-10)
    
    # Distance from extremes
    high_52w = h.rolling(min(252, len(h))).max()
    low_52w = l.rolling(min(252, len(l))).min()
    features["distance_from_52w_high"] = (c - high_52w) / (high_52w + 1e-10)
    features["distance_from_52w_low"] = (c - low_52w) / (low_52w + 1e-10)
    
    # ═══ 6. MARKET CONTEXT (8 features) ══════════════════════════════════════
    if btc_df is not None and len(btc_df) > 20:
        btc_close = btc_df["close"]
        # Cross-correlation with BTC
        btc_returns = btc_close.pct_change()
        crypto_returns = c.pct_change()
        # Align indexes
        common_idx = btc_returns.index.intersection(crypto_returns.index)
        if len(common_idx) > 20:
            features.loc[common_idx, "btc_correlation_20"] = crypto_returns.loc[common_idx].rolling(20).corr(btc_returns.loc[common_idx])
        else:
            features["btc_correlation_20"] = 0.5
        features["btc_return_1h"] = btc_close.pct_change(1).reindex(features.index).fillna(0)
        features["btc_return_24h"] = btc_close.pct_change(24).reindex(features.index).fillna(0)
    else:
        features["btc_correlation_20"] = 0.5
        features["btc_return_1h"] = 0.0
        features["btc_return_24h"] = 0.0
    
    # Fear & Greed (static for the batch, will be updated per scan)
    features["fear_greed_index"] = fear_greed if fear_greed is not None else 50.0
    # Funding rate
    features["funding_rate"] = funding_rate if funding_rate is not None else 0.0
    
    # Time encoding (cyclical)
    if hasattr(df.index, 'hour'):
        hour = df.index.hour
    elif 'timestamp' in df.columns:
        hour = pd.to_datetime(df['timestamp']).dt.hour
    else:
        hour = pd.Series(12, index=df.index)  # Default to noon
    
    if hasattr(df.index, 'dayofweek'):
        dow = df.index.dayofweek
    elif 'timestamp' in df.columns:
        dow = pd.to_datetime(df['timestamp']).dt.dayofweek
    else:
        dow = pd.Series(3, index=df.index)  # Default to Wednesday
    
    features["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    features["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    features["day_sin"] = np.sin(2 * np.pi * dow / 7)
    features["day_cos"] = np.cos(2 * np.pi * dow / 7)
    
    # ═══ 7. FRACTIONAL DIFFERENTIATION — Lopez de Prado AFML Ch.5 ════════════
    # Fractional differentiation d=0.4: makes price series stationary while
    # preserving memory (~60% correlation with original). Standard returns (d=1)
    # destroy all memory; raw prices are non-stationary. d=0.4 is the sweet spot.
    try:
        from crypto_ml_edge.features.fracdiff import frac_diff_ffd
        features["close_ffd"] = frac_diff_ffd(c, d=0.4)
        features["high_ffd"] = frac_diff_ffd(h, d=0.4)
        features["low_ffd"] = frac_diff_ffd(l, d=0.4)
        features["volume_ffd"] = frac_diff_ffd(v, d=0.4)
    except ImportError:
        # Inline fallback: FFD weights (pure numpy, no external dependency)
        _weights = [1.0]
        _k = 1
        while True:
            _w = -_weights[-1] * (0.4 - _k + 1) / _k
            if abs(_w) < 1e-5:
                break
            _weights.append(_w)
            _k += 1
        _w_arr = np.array(_weights[::-1])
        _width = len(_w_arr)
        for col_name, series in [("close_ffd", c), ("high_ffd", h),
                                  ("low_ffd", l), ("volume_ffd", v)]:
            ffd = pd.Series(index=series.index, dtype=float)
            vals = series.values.astype(float)
            for _i in range(_width - 1, len(vals)):
                ffd.iloc[_i] = np.dot(_w_arr, vals[_i - _width + 1: _i + 1])
            features[col_name] = ffd

    # ─── Clean up NaN from lookback periods ──────────────────────────────────
    # Don't drop NaN rows here — let the caller decide the warmup period
    return features


def build_target(close: pd.Series, horizon: int, tp_pct: float = 0.02, sl_pct: float = -0.01,
                  high: Optional[pd.Series] = None, low: Optional[pd.Series] = None,
                  atr: Optional[pd.Series] = None,
                  tp_atr_mult: float = 2.5, sl_atr_mult: float = 2.0) -> pd.Series:
    """
    Triple Barrier labeling (v1.5 — Lopez de Prado 2018):
    Uses HIGH/LOW for realistic intra-bar TP/SL detection.
    When ATR is provided, uses ATR-based dynamic TP/SL (preferred).
    tp_atr_mult/sl_atr_mult control ATR multipliers per timeframe style.
    Falls back to fixed tp_pct/sl_pct when ATR unavailable.
    """
    target = pd.Series(0, index=close.index, dtype=int)
    h = high if high is not None else close
    l = low if low is not None else close

    for i in range(len(close) - horizon):
        entry_price = close.iloc[i]

        if atr is not None and not np.isnan(atr.iloc[i]) and atr.iloc[i] > 0:
            atr_val = atr.iloc[i]
            tp_level = entry_price + tp_atr_mult * atr_val
            sl_level = entry_price - sl_atr_mult * atr_val
        else:
            tp_level = entry_price * (1 + tp_pct)
            sl_level = entry_price * (1 + sl_pct)

        tp_hit = None
        sl_hit = None

        for j in range(1, min(horizon + 1, len(close) - i)):
            if tp_hit is None and h.iloc[i + j] >= tp_level:
                tp_hit = j
            if sl_hit is None and l.iloc[i + j] <= sl_level:
                sl_hit = j
            if tp_hit is not None and sl_hit is not None:
                break

        if tp_hit is not None and (sl_hit is None or tp_hit <= sl_hit):
            target.iloc[i] = 1
        elif tp_hit is None and sl_hit is None:
            end_idx = min(i + horizon, len(close) - 1)
            if close.iloc[end_idx] > entry_price:
                target.iloc[i] = 1

    return target


def build_regression_target(close: pd.Series, horizon: int) -> pd.Series:
    """Build regression target: forward return over horizon bars."""
    return close.pct_change(horizon).shift(-horizon) * 100
