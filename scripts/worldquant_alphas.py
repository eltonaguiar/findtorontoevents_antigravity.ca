#!/usr/bin/env python3
"""
WorldQuant 101 Alphas — Cherry-picked implementations for live-monitor.

Selected 8 alphas from WorldQuant's "101 Formulaic Alphas" paper that:
  1. Have low correlation to existing technical signals
  2. Work on daily/hourly timeframes (0.6-6 day hold)
  3. Don't require expensive data (use OHLCV only)
  4. Have demonstrated alpha in academic backtests

References:
  - Kakushadze, Z. (2016). "101 Formulaic Alphas"
  - https://arxiv.org/abs/1601.00991

Each alpha returns a z-score signal: positive = long, negative = short.
Signals feed into the ML Alpha Bundle.

Requires: pip install numpy pandas yfinance requests
"""
import sys
import os
import json
import logging
import numpy as np
import pandas as pd
import warnings

warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import post_to_api, call_api
from config import TRACKED_TICKERS

logger = logging.getLogger('worldquant_alphas')


# ---------------------------------------------------------------------------
# Helper Functions (matching WorldQuant notation)
# ---------------------------------------------------------------------------

def rank(series):
    """Cross-sectional rank (percentile 0-1)."""
    return series.rank(pct=True)

def delta(series, d=1):
    """Change over d periods."""
    return series.diff(d)

def ts_rank(series, d=10):
    """Time-series rank over d periods."""
    return series.rolling(d).apply(lambda x: pd.Series(x).rank().iloc[-1] / len(x), raw=False)

def ts_min(series, d=10):
    """Rolling min over d periods."""
    return series.rolling(d).min()

def ts_max(series, d=10):
    """Rolling max over d periods."""
    return series.rolling(d).max()

def ts_argmax(series, d=10):
    """Position of max in last d periods (0 to d-1)."""
    return series.rolling(d).apply(lambda x: np.argmax(x), raw=True)

def ts_argmin(series, d=10):
    """Position of min in last d periods."""
    return series.rolling(d).apply(lambda x: np.argmin(x), raw=True)

def stddev(series, d=10):
    """Rolling standard deviation."""
    return series.rolling(d).std()

def correlation(x, y, d=10):
    """Rolling correlation."""
    return x.rolling(d).corr(y)

def covariance(x, y, d=5):
    """Rolling covariance."""
    return x.rolling(d).cov(y)

def decay_linear(series, d=10):
    """Linearly decaying weighted average (newer = higher weight)."""
    weights = np.arange(1, d + 1, dtype=float)
    weights /= weights.sum()
    return series.rolling(d).apply(lambda x: np.dot(x, weights), raw=True)

def sign(series):
    """Sign function: -1, 0, or 1."""
    return np.sign(series)

def adv(volume, d=20):
    """Average daily volume over d periods."""
    return volume.rolling(d).mean()


# ---------------------------------------------------------------------------
# Selected WorldQuant Alphas
# ---------------------------------------------------------------------------

def alpha_001(close, returns):
    """
    Alpha#1: Rank of momentum quality.
    rank(Ts_ArgMax(SignedPower(((returns < 0) ? stddev(returns, 20) : close), 2.), 5))
    Simplified: Reward consistent up-trends, penalize volatile down-trends.
    """
    conditioned = pd.Series(np.where(returns < 0, stddev(returns, 20), close), index=close.index)
    powered = conditioned ** 2
    arg = ts_argmax(powered, 5)
    return -1 * rank(arg)  # Negative because argmax of bad = sell signal


def alpha_006(open_price, volume):
    """
    Alpha#6: Open-volume correlation signal.
    -1 * correlation(open, volume, 10)
    Anti-correlated open and volume = unusual activity.
    """
    return -1 * correlation(open_price, volume, 10)


def alpha_012(close, volume):
    """
    Alpha#12: Volume-price divergence.
    sign(delta(volume, 1)) * (-1 * delta(close, 1))
    Volume increasing + price falling = bearish divergence.
    Volume increasing + price rising = confirmation (but we fade).
    """
    return sign(delta(volume, 1)) * (-1 * delta(close, 1))


def alpha_026(close, high, volume):
    """
    Alpha#26: Extreme reversal.
    -1 * ts_max(correlation(ts_rank(volume, 5), ts_rank(high, 5), 5), 3)
    When volume rank and high rank are highly correlated = exhaustion.
    """
    vol_rank = ts_rank(volume, 5)
    high_rank = ts_rank(high, 5)
    corr = correlation(vol_rank, high_rank, 5)
    return -1 * ts_max(corr, 3)


def alpha_033(close, open_price, returns):
    """
    Alpha#33: Gap reversal.
    rank(-1 + (open / close))
    Gaps tend to fill — simple but effective.
    """
    return rank(-1 + (open_price / close))


def alpha_041(high, low, volume):
    """
    Alpha#41: Volume-weighted range signal.
    power(high * low, 0.5) - vwap approximation
    Simplified: sqrt(high * low) as geometric mean price vs volume signal.
    """
    geo_mean = np.sqrt(high * low)
    vol_ratio = volume / adv(volume, 20)
    return rank(geo_mean * vol_ratio)


def alpha_053(close, high, low):
    """
    Alpha#53: Williams %R momentum.
    -1 * delta((((close - low) - (high - close)) / (close - low)), 9)
    Change in normalized position within range.
    """
    pos = ((close - low) - (high - close)) / (close - low + 1e-10)
    return -1 * delta(pos, 9)


def alpha_101(close, open_price, high, low):
    """
    Alpha#101: The last alpha.
    (close - open) / ((high - low) + 0.001)
    Normalized close-open range — candle body ratio.
    Strong close = bullish (but fade via rank).
    """
    body = (close - open_price) / (high - low + 0.001)
    return rank(body)


# ---------------------------------------------------------------------------
# Compute All Alphas for a Ticker
# ---------------------------------------------------------------------------

def compute_alphas(df):
    """
    Compute all 8 selected WorldQuant alphas for a single ticker's OHLCV data.
    Returns DataFrame with alpha columns.
    """
    close = df['Close'].squeeze() if hasattr(df['Close'], 'squeeze') else df['Close']
    open_p = df['Open'].squeeze() if hasattr(df['Open'], 'squeeze') else df['Open']
    high = df['High'].squeeze() if hasattr(df['High'], 'squeeze') else df['High']
    low = df['Low'].squeeze() if hasattr(df['Low'], 'squeeze') else df['Low']
    volume = df['Volume'].squeeze() if hasattr(df['Volume'], 'squeeze') else df['Volume']
    returns = close.pct_change()

    alphas = pd.DataFrame(index=df.index)

    try:
        alphas['wq_alpha_001'] = alpha_001(close, returns)
    except Exception as e:
        logger.warning("Alpha 001 failed: %s", e)

    try:
        alphas['wq_alpha_006'] = alpha_006(open_p, volume)
    except Exception as e:
        logger.warning("Alpha 006 failed: %s", e)

    try:
        alphas['wq_alpha_012'] = alpha_012(close, volume)
    except Exception as e:
        logger.warning("Alpha 012 failed: %s", e)

    try:
        alphas['wq_alpha_026'] = alpha_026(close, high, volume)
    except Exception as e:
        logger.warning("Alpha 026 failed: %s", e)

    try:
        alphas['wq_alpha_033'] = alpha_033(close, open_p, returns)
    except Exception as e:
        logger.warning("Alpha 033 failed: %s", e)

    try:
        alphas['wq_alpha_041'] = alpha_041(high, low, volume)
    except Exception as e:
        logger.warning("Alpha 041 failed: %s", e)

    try:
        alphas['wq_alpha_053'] = alpha_053(close, high, low)
    except Exception as e:
        logger.warning("Alpha 053 failed: %s", e)

    try:
        alphas['wq_alpha_101'] = alpha_101(close, open_p, high, low)
    except Exception as e:
        logger.warning("Alpha 101 failed: %s", e)

    return alphas


# ---------------------------------------------------------------------------
# Cross-Asset Momentum Spillover
# ---------------------------------------------------------------------------

def cross_asset_spillover():
    """
    Detect momentum spillovers between asset classes.
    Bond rally (TLT up) → equity buy signal (flight from bonds ends)
    Gold rally (GLD up) → risk-off (caution for equities)
    USD strength (UUP up) → pressure on commodities/EM
    """
    import yfinance as yf

    etfs = {
        'TLT': 'bonds_20y',     # 20Y treasury bonds
        'GLD': 'gold',           # Gold
        'UUP': 'usd_index',     # US Dollar
        'HYG': 'high_yield',    # High yield bonds (risk appetite)
        'VIX': '^VIX'           # VIX (direct)
    }

    spillover = {}

    for label, ticker in etfs.items():
        try:
            df = yf.download(ticker, period='30d', interval='1d', progress=False)
            if len(df) < 10:
                continue

            closes = df['Close'].values.flatten()
            ret_5d = (closes[-1] - closes[-5]) / closes[-5] if len(closes) >= 5 else 0
            ret_10d = (closes[-1] - closes[-10]) / closes[-10] if len(closes) >= 10 else 0
            sma20 = np.mean(closes[-20:]) if len(closes) >= 20 else closes[-1]

            spillover[label] = {
                'price': round(float(closes[-1]), 2),
                'return_5d': round(float(ret_5d) * 100, 2),
                'return_10d': round(float(ret_10d) * 100, 2),
                'above_sma20': bool(closes[-1] > sma20),
                'trend': 'up' if ret_5d > 0.005 else ('down' if ret_5d < -0.005 else 'flat')
            }
        except Exception as e:
            logger.warning("Spillover fetch failed for %s: %s", ticker, e)

    # Generate equity signals from cross-asset
    equity_signal = 0  # -100 to +100

    if 'TLT' in spillover:
        if spillover['TLT']['trend'] == 'down':
            equity_signal += 15  # Money rotating out of bonds → equities
        elif spillover['TLT']['trend'] == 'up':
            equity_signal -= 10  # Flight to safety

    if 'GLD' in spillover:
        if spillover['GLD']['trend'] == 'up' and spillover['GLD']['return_5d'] > 2:
            equity_signal -= 15  # Strong gold = fear
        elif spillover['GLD']['trend'] == 'down':
            equity_signal += 5   # Risk-on

    if 'HYG' in spillover:
        if spillover['HYG']['trend'] == 'up':
            equity_signal += 10  # Credit appetite = risk-on
        elif spillover['HYG']['trend'] == 'down':
            equity_signal -= 15  # Credit stress

    if 'UUP' in spillover:
        if spillover['UUP']['trend'] == 'up' and spillover['UUP']['return_5d'] > 1:
            equity_signal -= 10  # Strong dollar hurts multinationals

    spillover['equity_signal'] = max(-100, min(100, equity_signal))
    spillover['equity_bias'] = 'bullish' if equity_signal > 15 else ('bearish' if equity_signal < -15 else 'neutral')

    logger.info("Cross-asset spillover: equity_signal=%d (%s)", equity_signal, spillover['equity_bias'])
    return spillover


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def run_worldquant_alphas():
    """
    Compute WorldQuant alphas for all tracked tickers + cross-asset spillover.
    Post results to PHP API.
    """
    import yfinance as yf

    logger.info("=" * 60)
    logger.info("WORLDQUANT ALPHAS + CROSS-ASSET — Starting")
    logger.info("=" * 60)

    results = {}
    signals = []

    for ticker in TRACKED_TICKERS:
        try:
            df = yf.download(ticker, period='60d', interval='1d', progress=False)
            if len(df) < 30:
                logger.warning("Insufficient data for %s (%d rows)", ticker, len(df))
                continue

            alphas = compute_alphas(df)
            latest = alphas.iloc[-1].to_dict()

            # Filter NaN
            latest = {k: round(float(v), 4) if not np.isnan(v) else 0 for k, v in latest.items()}

            # Composite WQ signal: average of z-scored alphas
            valid_alphas = [v for v in latest.values() if v != 0]
            if valid_alphas:
                composite = np.mean(valid_alphas)
            else:
                composite = 0

            results[ticker] = {
                'alphas': latest,
                'composite_wq': round(composite, 4),
                'signal': 'LONG' if composite > 0.3 else ('SHORT' if composite < -0.3 else 'NEUTRAL')
            }

            if abs(composite) > 0.3:
                signals.append({
                    'ticker': ticker,
                    'signal': results[ticker]['signal'],
                    'strength': min(100, int(abs(composite) * 100)),
                    'source': 'worldquant_101',
                    'alphas': latest
                })

            logger.info("  %s: composite=%.3f (%s) | a001=%.3f a006=%.3f a012=%.3f a053=%.3f",
                         ticker, composite, results[ticker]['signal'],
                         latest.get('wq_alpha_001', 0),
                         latest.get('wq_alpha_006', 0),
                         latest.get('wq_alpha_012', 0),
                         latest.get('wq_alpha_053', 0))

        except Exception as e:
            logger.error("Failed for %s: %s", ticker, e)

    # Cross-asset spillover
    logger.info("Computing cross-asset spillover...")
    spillover = cross_asset_spillover()

    # Compile and post
    output = {
        'worldquant_alphas': results,
        'cross_asset': spillover,
        'signals': signals,
        'signal_count': len(signals)
    }

    logger.info("=" * 60)
    logger.info("WORLDQUANT SUMMARY")
    logger.info("  Tickers analyzed: %d", len(results))
    logger.info("  Signals generated: %d", len(signals))
    logger.info("  Cross-asset equity bias: %s (score=%s)",
                 spillover.get('equity_bias', '?'), spillover.get('equity_signal', '?'))
    logger.info("=" * 60)

    # Post to API
    result = post_to_api('ingest_worldquant', output)
    if result.get('ok'):
        logger.info("WorldQuant data saved")
    else:
        logger.warning("API post: %s", result.get('error', 'unknown'))

    # Print JSON for GitHub Actions
    print("\n--- WORLDQUANT JSON OUTPUT ---")
    print(json.dumps(output, indent=2, default=str))

    return output


if __name__ == '__main__':
    run_worldquant_alphas()
