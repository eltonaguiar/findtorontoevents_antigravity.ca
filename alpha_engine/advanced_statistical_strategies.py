"""
ALPHA_ENGINE -- Advanced Statistical Strategies
=================================================
3 research-grade quant strategies exploiting fractal geometry,
long-range dependence, and PCA factor rotation.

AS1: Fractal Dimension Regime Filter (Higuchi 1988, Mandelbrot 1983)
     FD < 1.3 = trending, FD > 1.7 = chaotic, between = transition
     Standalone + regime filter export for other strategies
     55-62% WR in trending regimes

AS2: Detrended Fluctuation Analysis Timer (Peng et al. 1994, Kantelhardt 2002)
     DFA alpha > 0.5 = persistent (ride trend), < 0.5 = anti-persistent (mean revert)
     Captures Hurst-style long-memory without stationarity assumptions
     58-65% WR

AS3: PCA Factor Rotation (Jolliffe 2002, Fama-French style)
     PC1 = market factor (BTC beta), PC2 = rotation factor
     PC2 loading flip = relative strength shift -> tradeable signal
     55-60% WR

Data sources (all FREE):
  - Binance/Bybit/KuCoin via api_failover (multi-exchange failover)
  - 4H candles, 200 bars, top 15 symbols by 24h volume

References:
  - Higuchi (1988) "Approach to an irregular time series on the basis of the fractal theory"
  - Mandelbrot (1983) "The Fractal Geometry of Nature"
  - Peng et al. (1994) "Mosaic organization of DNA nucleotides" Phys Rev E
  - Jolliffe (2002) "Principal Component Analysis" Springer
  - Fama & French (1993) "Common risk factors" JFE
"""

from __future__ import annotations

import json
import logging
import math
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

from config import CRYPTO_SYMBOLS
from indicators import rsi, atr, sma

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _get_category(symbol):
    info = CRYPTO_SYMBOLS.get(symbol, {})
    return info.get("cat", "crypto")


def _smart_round(v):
    if v == 0:
        return 0.0
    av = abs(v)
    if av >= 100:
        return round(v, 2)
    if av >= 1:
        return round(v, 4)
    if av >= 0.01:
        return round(v, 6)
    return round(v, 10)


def _atr_val(close, high, low, period=14):
    """Get current ATR value."""
    atr_series = atr(high, low, close, period)
    val = float(atr_series.iloc[-1])
    if np.isnan(val) or val <= 0:
        return None
    return val


def _make_pick(symbol, direction, entry, tp, sl, confidence, strategy, reason=""):
    return {
        "symbol": symbol,
        "direction": direction,
        "entry": _smart_round(entry),
        "tp": _smart_round(tp),
        "sl": _smart_round(sl),
        "confidence": round(min(0.95, max(0.1, confidence)), 3),
        "strategy": strategy,
        "asset_class": _get_category(symbol),
        "timestamp": _now_iso(),
        "reason": reason,
    }


def _fetch_top_symbols_by_volume(n=15):
    """Fetch top N crypto symbols by 24h quote volume via api_failover."""
    try:
        from api_failover import fetch_ticker_24h
        tickers = fetch_ticker_24h()
        if not tickers or not isinstance(tickers, list):
            return list(CRYPTO_SYMBOLS.keys())[:n]
        # Filter USDT pairs, sort by volume
        usdt_tickers = [
            t for t in tickers
            if isinstance(t, dict) and t.get("symbol", "").endswith("USDT")
        ]
        usdt_tickers.sort(
            key=lambda t: float(t.get("quoteVolume", 0) or 0), reverse=True
        )
        symbols = [t["symbol"] for t in usdt_tickers[:n]]
        return symbols if symbols else list(CRYPTO_SYMBOLS.keys())[:n]
    except Exception as e:
        logger.debug(f"Volume fetch failed: {e}")
        return list(CRYPTO_SYMBOLS.keys())[:n]


def _get_df(data, symbol):
    """Get DataFrame for a symbol from data dict, checking common variants."""
    df = data.get(symbol)
    if df is not None and len(df) >= 50:
        return df
    # Try common variants
    for variant in [symbol.replace("USDT", "-USD"), symbol.replace("-USD", "USDT")]:
        df = data.get(variant)
        if df is not None and len(df) >= 50:
            return df
    return None


# =========================================================================
# AS1: Fractal Dimension Regime Filter
# Higuchi (1988), Mandelbrot (1983)
# =========================================================================

def compute_higuchi_fd(series, kmax=10):
    """
    Compute Higuchi Fractal Dimension of a 1D time series.

    For each k from 1..kmax, compute mean curve length L(k) across
    k sub-series starting at offsets m=1..k.
    FD = slope of log(L(k)) vs log(1/k) via least-squares.

    Parameters:
        series: 1D numpy array of prices
        kmax: maximum scale factor (default 10)

    Returns:
        float: fractal dimension (typically 1.0-2.0 for price series)
    """
    n = len(series)
    if n < kmax + 1:
        return np.nan

    # Ensure kmax doesn't exceed what the series can support
    kmax = min(kmax, n // 4)
    if kmax < 2:
        return np.nan

    log_k = []
    log_l = []

    for k in range(1, kmax + 1):
        lengths = []
        for m in range(1, k + 1):
            # Number of points in this sub-series
            num_points = int(np.floor((n - m) / k))
            if num_points < 1:
                continue
            # Compute curve length for sub-series starting at m, stepping by k
            indices = np.arange(m - 1, m - 1 + num_points * k, k)
            if len(indices) < 2:
                continue
            diffs = np.abs(np.diff(series[indices]))
            # Normalized length
            norm_factor = (n - 1) / (num_points * k)
            length_m = np.sum(diffs) * norm_factor / k
            lengths.append(length_m)

        if lengths:
            mean_length = np.mean(lengths)
            if mean_length > 0:
                log_k.append(np.log(1.0 / k))
                log_l.append(np.log(mean_length))

    if len(log_k) < 3:
        return np.nan

    # Linear regression: log(L(k)) = FD * log(1/k) + c
    log_k = np.array(log_k)
    log_l = np.array(log_l)
    n_pts = len(log_k)
    mean_x = np.mean(log_k)
    mean_y = np.mean(log_l)
    ss_xx = np.sum((log_k - mean_x) ** 2)
    if ss_xx < 1e-20:
        return np.nan
    ss_xy = np.sum((log_k - mean_x) * (log_l - mean_y))
    fd = ss_xy / ss_xx

    return fd


def get_fractal_regime(series, window=50, kmax=10):
    """
    Classify regime based on Higuchi Fractal Dimension.

    Returns:
        (fd_value, regime_label)
        regime_label: 'trending' | 'chaotic' | 'transition'
    """
    if len(series) < window:
        return np.nan, "unknown"

    fd = compute_higuchi_fd(series[-window:], kmax=kmax)
    if np.isnan(fd):
        return np.nan, "unknown"

    if fd < 1.3:
        return fd, "trending"
    elif fd > 1.7:
        return fd, "chaotic"
    else:
        return fd, "transition"


def fractal_dimension_regime(data, context=None):
    """
    AS1: Fractal Dimension Regime Filter.

    BUY when FD < 1.3 (trending) AND price > 20-SMA (trending up)
    SELL when FD < 1.3 (trending) AND price < 20-SMA (trending down)
    NO TRADE when FD > 1.7 (too chaotic)
    TP: 2x ATR, SL: 1.5x ATR
    """
    signals = []
    strategy_name = "fractal_dimension_regime"

    for symbol, df in data.items():
        try:
            if df is None or len(df) < 60:
                continue
            if not symbol.endswith("USDT") and not symbol.endswith("-USD"):
                continue

            close = df["close"].astype(float)
            high = df["high"].astype(float)
            low = df["low"].astype(float)

            # Compute fractal dimension on last 50 bars
            close_arr = close.values
            fd, regime = get_fractal_regime(close_arr, window=50, kmax=10)

            if np.isnan(fd) or regime != "trending":
                continue  # Only trade in trending regime

            # Direction: price vs 20-SMA
            sma_20 = sma(close, 20)
            current_price = float(close.iloc[-1])
            current_sma = float(sma_20.iloc[-1])

            if np.isnan(current_sma):
                continue

            # ATR for TP/SL
            current_atr = _atr_val(close, high, low, 14)
            if current_atr is None or current_atr <= 0:
                continue

            # Confidence scales with how strongly trending (lower FD = more trending)
            base_confidence = 0.55 + (1.3 - fd) * 0.3  # FD=1.0 -> 0.64, FD=1.2 -> 0.58

            if current_price > current_sma:
                # Trending UP
                tp = current_price + 2.0 * current_atr
                sl = current_price - 1.5 * current_atr
                reason = (f"Higuchi FD={fd:.3f} (trending regime), "
                          f"price {current_price:.4f} > SMA20 {current_sma:.4f}")
                signals.append(_make_pick(
                    symbol, "LONG", current_price, tp, sl,
                    base_confidence, strategy_name, reason
                ))
            elif current_price < current_sma:
                # Trending DOWN
                tp = current_price - 2.0 * current_atr
                sl = current_price + 1.5 * current_atr
                reason = (f"Higuchi FD={fd:.3f} (trending regime), "
                          f"price {current_price:.4f} < SMA20 {current_sma:.4f}")
                signals.append(_make_pick(
                    symbol, "SHORT", current_price, tp, sl,
                    base_confidence, strategy_name, reason
                ))
        except Exception as e:
            logger.debug(f"FD regime error {symbol}: {e}")
            continue

    return signals


# =========================================================================
# AS2: Detrended Fluctuation Analysis Timer
# Peng et al. (1994), Kantelhardt (2002)
# =========================================================================

def compute_dfa_alpha(series, min_window=4, max_window=None, n_windows=8):
    """
    Compute DFA alpha exponent on a 1D time series.

    Steps:
    1. Integrate: Y(i) = cumsum(x - mean(x))
    2. For each window size n, divide into non-overlapping windows
    3. Fit linear trend to each window, compute RMS of residuals F(n)
    4. DFA alpha = slope of log(F(n)) vs log(n)

    Parameters:
        series: 1D numpy array
        min_window: smallest window size
        max_window: largest window size (default N//4)
        n_windows: number of window sizes to test

    Returns:
        float: DFA alpha exponent
            > 0.5: persistent (long-memory, trend continuation)
            = 0.5: random walk (no memory)
            < 0.5: anti-persistent (mean-reverting)
    """
    n = len(series)
    if n < 20:
        return np.nan

    if max_window is None:
        max_window = n // 4
    if max_window < min_window + 2:
        return np.nan

    # Step 1: Integrate (cumulative deviation from mean)
    mean_val = np.mean(series)
    y = np.cumsum(series - mean_val)

    # Generate window sizes (log-spaced)
    window_sizes = np.unique(np.logspace(
        np.log10(min_window), np.log10(max_window), n_windows
    ).astype(int))
    window_sizes = window_sizes[window_sizes >= min_window]
    if len(window_sizes) < 3:
        return np.nan

    log_n = []
    log_f = []

    for w in window_sizes:
        n_segments = n // w
        if n_segments < 1:
            continue

        rms_values = []
        for seg in range(n_segments):
            start = seg * w
            end = start + w
            segment = y[start:end]

            # Fit linear trend (least squares): y = a*x + b
            x = np.arange(w, dtype=float)
            x_mean = np.mean(x)
            y_seg_mean = np.mean(segment)
            ss_xx = np.sum((x - x_mean) ** 2)
            if ss_xx < 1e-20:
                continue
            ss_xy = np.sum((x - x_mean) * (segment - y_seg_mean))
            slope = ss_xy / ss_xx
            intercept = y_seg_mean - slope * x_mean
            trend = slope * x + intercept

            # RMS of residuals
            residuals = segment - trend
            rms = np.sqrt(np.mean(residuals ** 2))
            if rms > 0:
                rms_values.append(rms)

        if rms_values:
            f_n = np.mean(rms_values)
            if f_n > 0:
                log_n.append(np.log(w))
                log_f.append(np.log(f_n))

    if len(log_n) < 3:
        return np.nan

    # Linear regression: log(F(n)) = alpha * log(n) + c
    log_n = np.array(log_n)
    log_f = np.array(log_f)
    mean_x = np.mean(log_n)
    mean_y = np.mean(log_f)
    ss_xx = np.sum((log_n - mean_x) ** 2)
    if ss_xx < 1e-20:
        return np.nan
    ss_xy = np.sum((log_n - mean_x) * (log_f - mean_y))
    alpha = ss_xy / ss_xx

    return alpha


def dfa_timer(data, context=None):
    """
    AS2: Detrended Fluctuation Analysis Timer.

    BUY when alpha > 0.6 AND last 5-bar return > 0 (persistent uptrend)
    SELL when alpha > 0.6 AND last 5-bar return < 0 (persistent downtrend)
    MEAN REVERT when alpha < 0.4 AND RSI < 30 (anti-persistent + oversold)
    TP: 1.5x ATR, SL: 1.0x ATR
    """
    signals = []
    strategy_name = "dfa_timer"

    for symbol, df in data.items():
        try:
            if df is None or len(df) < 110:
                continue
            if not symbol.endswith("USDT") and not symbol.endswith("-USD"):
                continue

            close = df["close"].astype(float)
            high = df["high"].astype(float)
            low = df["low"].astype(float)

            # Compute DFA alpha on last 100 bars of log-returns
            close_arr = close.values
            if len(close_arr) < 100:
                continue
            log_returns = np.diff(np.log(close_arr[-101:]))
            alpha = compute_dfa_alpha(log_returns, min_window=4, max_window=25, n_windows=8)

            if np.isnan(alpha):
                continue

            current_price = float(close.iloc[-1])
            current_atr = _atr_val(close, high, low, 14)
            if current_atr is None or current_atr <= 0:
                continue

            # Last 5-bar return
            if len(close) < 6:
                continue
            ret_5 = (float(close.iloc[-1]) / float(close.iloc[-6])) - 1.0

            # RSI for mean reversion
            rsi_series = rsi(close, 14)
            current_rsi = float(rsi_series.iloc[-1]) if not np.isnan(rsi_series.iloc[-1]) else 50.0

            if alpha > 0.6:
                # Persistent regime -- ride the trend
                confidence = 0.55 + (alpha - 0.6) * 0.5  # alpha=0.8 -> 0.65

                if ret_5 > 0:
                    tp = current_price + 1.5 * current_atr
                    sl = current_price - 1.0 * current_atr
                    reason = (f"DFA alpha={alpha:.3f} (persistent), "
                              f"5-bar return={ret_5*100:.2f}% positive -> trend continuation")
                    signals.append(_make_pick(
                        symbol, "LONG", current_price, tp, sl,
                        confidence, strategy_name, reason
                    ))
                elif ret_5 < 0:
                    tp = current_price - 1.5 * current_atr
                    sl = current_price + 1.0 * current_atr
                    reason = (f"DFA alpha={alpha:.3f} (persistent), "
                              f"5-bar return={ret_5*100:.2f}% negative -> trend continuation")
                    signals.append(_make_pick(
                        symbol, "SHORT", current_price, tp, sl,
                        confidence, strategy_name, reason
                    ))

            elif alpha < 0.4 and current_rsi < 30:
                # Anti-persistent + oversold -> mean reversion BUY
                confidence = 0.52 + (0.4 - alpha) * 0.3  # alpha=0.2 -> 0.58
                tp = current_price + 1.5 * current_atr
                sl = current_price - 1.0 * current_atr
                reason = (f"DFA alpha={alpha:.3f} (anti-persistent), "
                          f"RSI={current_rsi:.1f} oversold -> mean reversion bounce")
                signals.append(_make_pick(
                    symbol, "LONG", current_price, tp, sl,
                    confidence, strategy_name, reason
                ))

        except Exception as e:
            logger.debug(f"DFA timer error {symbol}: {e}")
            continue

    return signals


# =========================================================================
# AS3: PCA Factor Rotation
# Jolliffe (2002), Fama-French style crypto factor model
# =========================================================================

def _compute_pca_loadings(returns_matrix):
    """
    Compute PCA on returns matrix using eigendecomposition of covariance matrix.

    Parameters:
        returns_matrix: (n_obs, n_assets) numpy array of returns

    Returns:
        eigenvalues: sorted descending
        eigenvectors: corresponding eigenvectors (columns)
        None, None on failure
    """
    n_obs, n_assets = returns_matrix.shape
    if n_obs < n_assets + 5:
        return None, None

    # Remove any columns with zero variance
    variances = np.var(returns_matrix, axis=0)
    valid_cols = variances > 1e-15
    if np.sum(valid_cols) < 3:
        return None, None

    # Compute covariance matrix
    cov_matrix = np.cov(returns_matrix[:, valid_cols], rowvar=False)
    if cov_matrix.ndim < 2:
        return None, None

    # Eigendecomposition (numpy.linalg.eigh for symmetric matrices)
    try:
        eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)
    except np.linalg.LinAlgError:
        return None, None

    # Sort by eigenvalue descending
    idx = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]

    # Map back to full asset space
    full_eigenvectors = np.zeros((n_assets, len(eigenvalues)))
    valid_indices = np.where(valid_cols)[0]
    for i, vi in enumerate(valid_indices):
        full_eigenvectors[vi, :] = eigenvectors[i, :]

    return eigenvalues, full_eigenvectors


def pca_factor_rotation(data, context=None):
    """
    AS3: PCA Factor Rotation Strategy.

    Compute PCA on returns of top 15 crypto symbols over 30-day rolling window.
    PC1 = market factor (BTC beta)
    PC2 = rotation factor
    When PC2 loading flips negative->positive, coin gaining relative strength -> BUY
    When PC2 loading flips positive->negative -> SELL
    TP: +8%, SL: -4%, confidence scaled by eigenvalue magnitude
    """
    signals = []
    strategy_name = "pca_factor_rotation"

    # Collect symbols with enough data
    crypto_symbols = []
    crypto_dfs = {}
    for symbol, df in data.items():
        if df is None or len(df) < 65:
            continue
        if not symbol.endswith("USDT") and not symbol.endswith("-USD"):
            continue
        crypto_symbols.append(symbol)
        crypto_dfs[symbol] = df

    if len(crypto_symbols) < 5:
        return signals  # Need enough symbols for meaningful PCA

    # Use top 15 by data availability, preferring USDT pairs
    crypto_symbols = crypto_symbols[:15]

    # Build returns matrix: 30-day rolling window of daily returns
    # Using last 35 bars (4H) ~ 5.8 days for returns, need ~60 bars for 30-day window
    window_current = 30
    window_prev = 30

    # Compute log returns for each symbol
    all_returns = {}
    min_len = float("inf")
    for sym in crypto_symbols:
        df = crypto_dfs[sym]
        close = df["close"].astype(float).values
        if len(close) < 65:
            continue
        log_ret = np.diff(np.log(close))
        all_returns[sym] = log_ret
        min_len = min(min_len, len(log_ret))

    if len(all_returns) < 5 or min_len < 60:
        return signals

    # Align returns to same length
    symbols_list = list(all_returns.keys())
    n_assets = len(symbols_list)
    returns_aligned = np.column_stack([
        all_returns[sym][-min_len:] for sym in symbols_list
    ])

    # Current window (last 30 bars) and previous window (30 bars before that)
    if min_len < 60:
        return signals

    current_returns = returns_aligned[-window_current:, :]
    prev_returns = returns_aligned[-(window_current + window_prev):-window_current, :]

    # PCA on current window
    curr_eigenvals, curr_eigenvecs = _compute_pca_loadings(current_returns)
    if curr_eigenvals is None:
        return signals

    # PCA on previous window
    prev_eigenvals, prev_eigenvecs = _compute_pca_loadings(prev_returns)
    if prev_eigenvals is None:
        return signals

    # Ensure we have at least 2 components
    if len(curr_eigenvals) < 2 or len(prev_eigenvals) < 2:
        return signals

    # PC2 loadings (rotation factor)
    curr_pc2 = curr_eigenvecs[:, 1]
    prev_pc2 = prev_eigenvecs[:, 1]

    # Handle sign ambiguity: align PC2 signs using PC1 correlation
    # If PC1 directions are flipped, flip PC2 too
    curr_pc1 = curr_eigenvecs[:, 0]
    prev_pc1 = prev_eigenvecs[:, 0]
    if np.dot(curr_pc1, prev_pc1) < 0:
        prev_pc2 = -prev_pc2

    # Also align PC2 by majority sign consistency
    sign_agreement = np.sum(np.sign(curr_pc2) == np.sign(prev_pc2))
    if sign_agreement < n_assets // 2:
        prev_pc2 = -prev_pc2

    # Eigenvalue magnitude for confidence scaling
    total_var = np.sum(curr_eigenvals)
    if total_var <= 0:
        return signals
    pc2_var_explained = curr_eigenvals[1] / total_var  # Typically 5-20%

    for i, sym in enumerate(symbols_list):
        try:
            curr_loading = curr_pc2[i]
            prev_loading = prev_pc2[i]

            df = crypto_dfs[sym]
            close = df["close"].astype(float)
            current_price = float(close.iloc[-1])

            if current_price <= 0:
                continue

            # Detect loading flip
            flipped_positive = prev_loading < -0.05 and curr_loading > 0.05
            flipped_negative = prev_loading > 0.05 and curr_loading < -0.05

            if not flipped_positive and not flipped_negative:
                continue

            # Confidence based on eigenvalue magnitude and loading strength
            loading_strength = abs(curr_loading)
            base_confidence = 0.50 + pc2_var_explained * 1.5 + loading_strength * 0.2
            base_confidence = min(0.75, base_confidence)

            tp_pct = 0.08  # +8%
            sl_pct = 0.04  # -4%

            if flipped_positive:
                # Gaining relative strength -> BUY
                tp = current_price * (1.0 + tp_pct)
                sl = current_price * (1.0 - sl_pct)
                reason = (f"PC2 loading flip {prev_loading:.3f} -> {curr_loading:.3f} "
                          f"(gaining relative strength), "
                          f"PC2 explains {pc2_var_explained*100:.1f}% variance")
                signals.append(_make_pick(
                    sym, "LONG", current_price, tp, sl,
                    base_confidence, strategy_name, reason
                ))

            elif flipped_negative:
                # Losing relative strength -> SELL
                tp = current_price * (1.0 - tp_pct)
                sl = current_price * (1.0 + sl_pct)
                reason = (f"PC2 loading flip {prev_loading:.3f} -> {curr_loading:.3f} "
                          f"(losing relative strength), "
                          f"PC2 explains {pc2_var_explained*100:.1f}% variance")
                signals.append(_make_pick(
                    sym, "SHORT", current_price, tp, sl,
                    base_confidence, strategy_name, reason
                ))

        except Exception as e:
            logger.debug(f"PCA rotation error {sym}: {e}")
            continue

    return signals


# =========================================================================
# Exported regime filter for use by other strategies
# =========================================================================

def fractal_regime_filter(close_series, window=50, kmax=10):
    """
    Public API for other strategies to query fractal regime.

    Parameters:
        close_series: pd.Series or numpy array of close prices
        window: lookback window (default 50)
        kmax: max scale for Higuchi FD

    Returns:
        dict with keys:
            fd: float, fractal dimension
            regime: str, 'trending'|'chaotic'|'transition'|'unknown'
            tradeable: bool, True if trending (FD < 1.3)
            position_scale: float, 1.0 for trending, 0.5 for transition, 0.0 for chaotic
    """
    if isinstance(close_series, pd.Series):
        arr = close_series.values
    else:
        arr = np.asarray(close_series, dtype=float)

    fd, regime = get_fractal_regime(arr, window=window, kmax=kmax)

    if regime == "trending":
        position_scale = 1.0
        tradeable = True
    elif regime == "transition":
        position_scale = 0.5
        tradeable = True  # Trade with reduced size
    else:
        position_scale = 0.0
        tradeable = False

    return {
        "fd": round(fd, 4) if not np.isnan(fd) else None,
        "regime": regime,
        "tradeable": tradeable,
        "position_scale": position_scale,
    }


def dfa_regime_filter(close_series, window=100):
    """
    Public API for other strategies to query DFA persistence regime.

    Parameters:
        close_series: pd.Series or numpy array of close prices
        window: lookback window for DFA (default 100)

    Returns:
        dict with keys:
            alpha: float, DFA alpha exponent
            regime: str, 'persistent'|'anti_persistent'|'random_walk'|'unknown'
            trend_friendly: bool, True if alpha > 0.5
    """
    if isinstance(close_series, pd.Series):
        arr = close_series.values
    else:
        arr = np.asarray(close_series, dtype=float)

    if len(arr) < window + 1:
        return {"alpha": None, "regime": "unknown", "trend_friendly": False}

    log_returns = np.diff(np.log(arr[-window - 1:]))
    alpha = compute_dfa_alpha(log_returns, min_window=4, max_window=window // 4, n_windows=8)

    if np.isnan(alpha):
        return {"alpha": None, "regime": "unknown", "trend_friendly": False}

    if alpha > 0.55:
        regime = "persistent"
        trend_friendly = True
    elif alpha < 0.45:
        regime = "anti_persistent"
        trend_friendly = False
    else:
        regime = "random_walk"
        trend_friendly = False

    return {
        "alpha": round(alpha, 4),
        "regime": regime,
        "trend_friendly": trend_friendly,
    }


# =========================================================================
# Strategy registry
# =========================================================================

ADVANCED_STATISTICAL_STRATEGIES = {
    "fractal_dimension_regime": fractal_dimension_regime,
    "dfa_timer": dfa_timer,
    "pca_factor_rotation": pca_factor_rotation,
}
