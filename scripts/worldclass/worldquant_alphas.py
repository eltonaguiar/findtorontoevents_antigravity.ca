#!/usr/bin/env python3
"""
WorldQuant 101 Formulaic Alphas — Implementation of select alphas
Source: Kakushadze (2016), arXiv:1601.00991
Average correlation between alphas: 15.9% — excellent diversification

Implements 15 of the simplest, most orthogonal alphas using only OHLCV data.
Computes alpha scores for the stock universe and stores as trading signals.

Runs via GitHub Actions daily.
"""

import sys
import json
import warnings
import requests
import numpy as np
from datetime import datetime

warnings.filterwarnings("ignore")

try:
    import yfinance as yf
    import pandas as pd
except ImportError as e:
    print(f"Missing: {e}")
    sys.exit(1)

from config import INTEL_API, ADMIN_KEY, STOCK_SYMBOLS, CRYPTO_SYMBOLS


def store_metric(metric_name, asset_class, symbol, value, label, metadata=None):
    """Store a metric via PHP API."""
    try:
        data = {
            "action": "store",
            "key": ADMIN_KEY,
            "metric_name": metric_name,
            "asset_class": asset_class,
            "symbol": symbol,
            "metric_value": str(value),
            "metric_label": label,
        }
        if metadata:
            data["metadata"] = json.dumps(metadata)
        requests.post(INTEL_API, data=data, timeout=10)
    except Exception:
        pass


# ════════════════════════════════════════════════════════════════
#  Helper functions (from WorldQuant alpha notation)
# ════════════════════════════════════════════════════════════════

def ts_rank(series, window):
    """Time-series rank: percentile rank of current value in window."""
    if len(series) < window:
        return 0.5
    subset = series[-window:]
    rank = np.sum(subset <= subset[-1]) / len(subset)
    return rank


def ts_argmax(series, window):
    """Position of max value in window (0-indexed from end)."""
    if len(series) < window:
        return 0
    subset = series[-window:]
    return float(np.argmax(subset)) / window


def ts_argmin(series, window):
    """Position of min value in window (0-indexed from end)."""
    if len(series) < window:
        return 0
    subset = series[-window:]
    return float(np.argmin(subset)) / window


def delta(series, period):
    """Change over period."""
    if len(series) <= period:
        return 0
    return series[-1] - series[-1 - period]


def ts_corr(x, y, window):
    """Rolling correlation."""
    if len(x) < window or len(y) < window:
        return 0
    x_w = x[-window:]
    y_w = y[-window:]
    if np.std(x_w) == 0 or np.std(y_w) == 0:
        return 0
    return float(np.corrcoef(x_w, y_w)[0, 1])


def ts_cov(x, y, window):
    """Rolling covariance."""
    if len(x) < window or len(y) < window:
        return 0
    return float(np.cov(x[-window:], y[-window:])[0, 1])


def sma(series, window):
    """Simple moving average."""
    if len(series) < window:
        return np.mean(series) if len(series) > 0 else 0
    return np.mean(series[-window:])


def stddev(series, window):
    """Rolling standard deviation."""
    if len(series) < window:
        return np.std(series) if len(series) > 1 else 0
    return np.std(series[-window:])


def decay_linear(series, window):
    """Linearly-weighted moving average (more recent = higher weight)."""
    if len(series) < window:
        window = len(series)
    if window == 0:
        return 0
    weights = np.arange(1, window + 1, dtype=float)
    weights /= weights.sum()
    return float(np.dot(series[-window:], weights))


# ════════════════════════════════════════════════════════════════
#  Alpha Implementations (15 selected for orthogonality + simplicity)
# ════════════════════════════════════════════════════════════════

def alpha_001(closes, returns):
    """rank(Ts_ArgMax(SignedPower(returns, 2), 20)) - 0.5
    Momentum quality: when did the biggest squared return happen?"""
    if len(returns) < 20:
        return 0
    signed_power = np.sign(returns) * (returns ** 2)
    return ts_argmax(signed_power, 20) - 0.5


def alpha_006(opens, volumes):
    """-correlation(open, volume, 10)
    Open-volume relationship: negative correlation = signal."""
    return -ts_corr(opens, volumes, 10)


def alpha_012(volumes, closes):
    """sign(delta(volume, 1)) * (-delta(close, 1))
    Volume-price divergence: volume up + price down = accumulation."""
    vol_delta = delta(volumes, 1)
    price_delta = delta(closes, 1)
    return float(np.sign(vol_delta) * (-price_delta))


def alpha_026(highs, volumes):
    """-ts_max(correlation(ts_rank(volume, 5), ts_rank(high, 5), 5), 3)
    High-volume divergence reversal."""
    if len(highs) < 10 or len(volumes) < 10:
        return 0
    # Simplified: negative of correlation between volume rank and high rank
    vol_ranks = [ts_rank(volumes[:i+1], 5) for i in range(max(0, len(volumes)-5), len(volumes))]
    high_ranks = [ts_rank(highs[:i+1], 5) for i in range(max(0, len(highs)-5), len(highs))]
    if len(vol_ranks) < 3 or len(high_ranks) < 3:
        return 0
    return -ts_corr(np.array(vol_ranks), np.array(high_ranks), min(5, len(vol_ranks)))


def alpha_028(closes, highs, lows, volumes):
    """scale(correlation(adv20, low, 5) + (high+low)/2 - close)
    Mean-reversion signal from volume-low correlation."""
    adv20 = sma(volumes, 20)
    if len(lows) < 5:
        return 0
    corr = ts_corr(np.full(5, adv20), lows[-5:], 5)
    midpoint = (highs[-1] + lows[-1]) / 2
    return float(corr + midpoint - closes[-1])


def alpha_033(closes, opens):
    """rank((-1 * ((1 - (open / close))^1)))
    Open-close relationship: measures intraday direction strength."""
    if closes[-1] == 0:
        return 0
    return float(-(1 - opens[-1] / closes[-1]))


def alpha_038(closes, highs):
    """(-ts_rank(close, 10)) * rank(close / open) * ...
    Simplified: negative rank reversal on recent highs."""
    if len(closes) < 10:
        return 0
    cr = ts_rank(closes, 10)
    # If close is at top of range, signal bearish (mean-revert)
    return float(-(cr - 0.5) * 2)


def alpha_041(highs, lows):
    """power(high * low, 0.5) - vwap (simplified without vwap)
    Price structure: geometric mean vs current close."""
    geo_mean = np.sqrt(highs[-1] * lows[-1])
    avg_hl = (highs[-1] + lows[-1]) / 2
    if avg_hl == 0:
        return 0
    return float((geo_mean - avg_hl) / avg_hl * 100)


def alpha_044(closes, volumes):
    """-correlation(high, rank(volume), 5)
    Simplified to close-volume relationship."""
    return -ts_corr(closes, volumes, 5)


def alpha_049(closes):
    """Conditional momentum: if recent change is small, predict reversal."""
    if len(closes) < 20:
        return 0
    change_1d = delta(closes, 1)
    change_20d = delta(closes, 20)
    close_val = closes[-1]
    if close_val == 0:
        return 0
    # If 1-day change < 20-day change / 20 (slow momentum), signal reversal
    avg_daily = change_20d / 20
    if abs(change_1d) < abs(avg_daily) * 0.5:
        return float(-np.sign(change_1d) * abs(change_20d) / close_val * 100)
    return 0


def alpha_053(closes, highs, lows):
    """Intraday range ratio change.
    Measures if the daily range is expanding (breakout) or contracting (squeeze)."""
    if len(closes) < 10:
        return 0
    ranges = np.array(highs[-10:]) - np.array(lows[-10:])
    if np.mean(ranges[:-1]) == 0:
        return 0
    range_ratio = ranges[-1] / np.mean(ranges[:-1])
    price_direction = np.sign(delta(closes, 1))
    return float(price_direction * (range_ratio - 1) * 50)


def alpha_054(opens, closes, highs, lows):
    """(-((low - close) * (open^5)) / ((low - high) * (close^5)))
    Simplified price structure signal."""
    if closes[-1] == 0 or (lows[-1] - highs[-1]) == 0:
        return 0
    numerator = -(lows[-1] - closes[-1])
    denominator = (lows[-1] - highs[-1])
    return float(numerator / denominator) if denominator != 0 else 0


def alpha_060(closes, highs, lows, volumes):
    """Volume-weighted price momentum decay."""
    if len(closes) < 10:
        return 0
    # Linear decay-weighted close momentum
    close_changes = np.diff(closes[-11:])
    if len(close_changes) < 10:
        return 0
    decayed = decay_linear(close_changes, 10)
    vol_ratio = volumes[-1] / sma(volumes, 20) if sma(volumes, 20) > 0 else 1
    return float(decayed * vol_ratio)


def alpha_101(opens, closes, highs, lows):
    """(close - open) / ((high - low) + 0.001)
    Directional strength: how much of the bar is real body vs wick."""
    hl_range = highs[-1] - lows[-1] + 0.001
    body = closes[-1] - opens[-1]
    return float(body / hl_range)


# ════════════════════════════════════════════════════════════════
#  Main Computation
# ════════════════════════════════════════════════════════════════

ALL_ALPHAS = {
    "WQ_Alpha001": alpha_001,
    "WQ_Alpha006": alpha_006,
    "WQ_Alpha012": alpha_012,
    "WQ_Alpha026": alpha_026,
    "WQ_Alpha033": alpha_033,
    "WQ_Alpha038": alpha_038,
    "WQ_Alpha041": alpha_041,
    "WQ_Alpha044": alpha_044,
    "WQ_Alpha049": alpha_049,
    "WQ_Alpha053": alpha_053,
    "WQ_Alpha054": alpha_054,
    "WQ_Alpha060": alpha_060,
    "WQ_Alpha101": alpha_101,
}


def compute_alphas_for_symbol(ticker, asset_class):
    """Compute all WorldQuant alphas for a single symbol."""
    try:
        data = yf.download(ticker, period="1mo", interval="1d", progress=False)
        if data.empty or len(data) < 21:
            return {}

        opens = data["Open"].values.flatten()
        closes = data["Close"].values.flatten()
        highs = data["High"].values.flatten()
        lows = data["Low"].values.flatten()
        volumes = data["Volume"].values.flatten().astype(float)
        returns = np.diff(np.log(closes))

        alphas = {}

        # Alpha 001 (needs returns)
        alphas["WQ_Alpha001"] = alpha_001(closes, returns)

        # Alpha 006 (opens, volumes)
        alphas["WQ_Alpha006"] = alpha_006(opens, volumes)

        # Alpha 012 (volumes, closes)
        alphas["WQ_Alpha012"] = alpha_012(volumes, closes)

        # Alpha 026 (highs, volumes)
        alphas["WQ_Alpha026"] = alpha_026(highs, volumes)

        # Alpha 033 (closes, opens)
        alphas["WQ_Alpha033"] = alpha_033(closes, opens)

        # Alpha 038 (closes, highs)
        alphas["WQ_Alpha038"] = alpha_038(closes, highs)

        # Alpha 041 (highs, lows)
        alphas["WQ_Alpha041"] = alpha_041(highs, lows)

        # Alpha 044 (closes, volumes)
        alphas["WQ_Alpha044"] = alpha_044(closes, volumes)

        # Alpha 049 (closes)
        alphas["WQ_Alpha049"] = alpha_049(closes)

        # Alpha 053 (closes, highs, lows)
        alphas["WQ_Alpha053"] = alpha_053(closes, highs, lows)

        # Alpha 054 (opens, closes, highs, lows)
        alphas["WQ_Alpha054"] = alpha_054(opens, closes, highs, lows)

        # Alpha 060 (closes, highs, lows, volumes)
        alphas["WQ_Alpha060"] = alpha_060(closes, highs, lows, volumes)

        # Alpha 101 (opens, closes, highs, lows)
        alphas["WQ_Alpha101"] = alpha_101(opens, closes, highs, lows)

        return alphas

    except Exception as e:
        print(f"    Error computing alphas for {ticker}: {e}")
        return {}


def main():
    print("=" * 60)
    print("WORLD-CLASS INTELLIGENCE: WorldQuant 101 Alphas")
    print("=" * 60)

    all_results = {}

    # Process stocks
    print("\n--- Stock Universe ---")
    for ticker in STOCK_SYMBOLS:
        print(f"  {ticker}...", end=" ")
        alphas = compute_alphas_for_symbol(ticker, "STOCK")
        if alphas:
            # Composite score: average of normalized alphas
            values = [v for v in alphas.values() if abs(v) < 100]
            if values:
                composite = np.mean(values)
                label = "bullish" if composite > 0.1 else ("bearish" if composite < -0.1 else "neutral")
                print(f"composite={composite:.4f} ({label})")

                # Store composite
                store_metric("wq_alpha_composite", "STOCK", ticker,
                           composite, label, alphas)

                # Store individual alphas that have strong signals
                for alpha_name, value in alphas.items():
                    if abs(value) > 0.3:  # Only store significant signals
                        store_metric(alpha_name, "STOCK", ticker,
                                   value, "bullish" if value > 0 else "bearish")
            else:
                print("no signal")
        else:
            print("no data")

        all_results[ticker] = alphas

    # Process top crypto
    print("\n--- Crypto Universe ---")
    for ticker in CRYPTO_SYMBOLS[:5]:
        print(f"  {ticker}...", end=" ")
        alphas = compute_alphas_for_symbol(ticker, "CRYPTO")
        if alphas:
            values = [v for v in alphas.values() if abs(v) < 100]
            if values:
                composite = np.mean(values)
                label = "bullish" if composite > 0.1 else ("bearish" if composite < -0.1 else "neutral")
                print(f"composite={composite:.4f} ({label})")

                store_metric("wq_alpha_composite", "CRYPTO", ticker.replace("-USD", "USD"),
                           composite, label, alphas)
            else:
                print("no signal")
        else:
            print("no data")

    # Summary: rank stocks by composite alpha
    print(f"\n{'=' * 60}")
    print("WORLDQUANT ALPHA RANKINGS:")
    rankings = []
    for ticker, alphas in all_results.items():
        if alphas:
            values = [v for v in alphas.values() if abs(v) < 100]
            if values:
                rankings.append((ticker, np.mean(values)))

    rankings.sort(key=lambda x: x[1], reverse=True)
    for i, (ticker, score) in enumerate(rankings):
        direction = "BULLISH" if score > 0.1 else ("BEARISH" if score < -0.1 else "NEUTRAL")
        print(f"  {i+1}. {ticker:6s}: {score:+.4f} ({direction})")

    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
