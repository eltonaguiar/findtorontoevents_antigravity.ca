#!/usr/bin/env python3
"""
HMM Regime Detection — Hidden Markov Model for market regime classification
Science: Ang & Bekaert (2004), QuantStart research
Replaces simple SMA-cross regime gate with 3-state HMM (bull/bear/sideways)

Runs via GitHub Actions daily. Stores regime state in DB via PHP API.
"""

import sys
import json
import warnings
import requests
import numpy as np

warnings.filterwarnings("ignore")

try:
    import yfinance as yf
    from hmmlearn.hmm import GaussianHMM
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("pip install yfinance hmmlearn")
    sys.exit(1)

from config import INTEL_API, ADMIN_KEY, BENCHMARKS, API_HEADERS


def fetch_returns(ticker, period="1y", interval="1d"):
    """Fetch daily returns and realized volatility for a ticker."""
    try:
        data = yf.download(ticker, period=period, interval=interval, progress=False)
        if data.empty or len(data) < 60:
            print(f"  Warning: insufficient data for {ticker} ({len(data)} rows)")
            return None, None

        closes = data["Close"].values.flatten()
        returns = np.diff(np.log(closes))  # Log returns

        # 20-day realized volatility
        vol = np.array([
            np.std(returns[max(0, i-20):i]) if i >= 20 else np.std(returns[:i+1])
            for i in range(len(returns))
        ])

        return returns, vol
    except Exception as e:
        print(f"  Error fetching {ticker}: {e}")
        return None, None


def fit_hmm(returns, vol, n_states=3):
    """Fit a 3-state Gaussian HMM on returns + volatility features."""
    if returns is None or vol is None:
        return None, None, None

    # Feature matrix: [returns, volatility]
    X = np.column_stack([returns, vol])

    # Remove any NaN/inf
    mask = np.isfinite(X).all(axis=1)
    X = X[mask]

    if len(X) < 60:
        return None, None, None

    best_model = None
    best_score = -np.inf

    # Try multiple random seeds for stability
    for seed in [42, 123, 456, 789]:
        try:
            model = GaussianHMM(
                n_components=n_states,
                covariance_type="full",
                n_iter=200,
                random_state=seed,
                tol=0.01
            )
            model.fit(X)
            score = model.score(X)
            if score > best_score:
                best_score = score
                best_model = model
        except Exception:
            continue

    if best_model is None:
        return None, None, None

    # Predict states
    states = best_model.predict(X)
    current_state = int(states[-1])

    # Map states to regime labels by mean return
    state_means = {}
    for s in range(n_states):
        mask = states == s
        if mask.sum() > 0:
            state_means[s] = np.mean(X[mask, 0])  # Mean return
        else:
            state_means[s] = 0

    # Sort by mean return: lowest = bear, middle = sideways, highest = bull
    sorted_states = sorted(state_means.keys(), key=lambda s: state_means[s])
    state_map = {}
    labels = ["bear", "sideways", "bull"]
    for i, s in enumerate(sorted_states):
        state_map[s] = labels[i]

    regime_label = state_map[current_state]

    # State probabilities for current observation
    try:
        posteriors = best_model.predict_proba(X[-1:].reshape(1, -1))
        probs = {state_map[i]: float(posteriors[0][i]) for i in range(n_states)}
    except Exception:
        probs = {regime_label: 1.0}

    return regime_label, probs, state_map


def calculate_hurst(prices, max_lag=100):
    """
    Calculate Hurst exponent using R/S analysis.
    H > 0.5: trending (persistent), H < 0.5: mean-reverting, H = 0.5: random walk
    Science: Mandelbrot (1963), Macrosynergy Research
    """
    if prices is None or len(prices) < max_lag:
        return 0.5  # Default to random walk if insufficient data

    lags = range(2, min(max_lag, len(prices) // 2))
    rs_values = []
    lag_values = []

    for lag in lags:
        # Divide series into subseries of length 'lag'
        n_subseries = len(prices) // lag
        if n_subseries < 1:
            continue

        rs_sum = 0
        valid = 0
        for i in range(n_subseries):
            subseries = prices[i * lag:(i + 1) * lag]
            if len(subseries) < 2:
                continue

            mean = np.mean(subseries)
            deviations = subseries - mean
            cumsum = np.cumsum(deviations)
            R = np.max(cumsum) - np.min(cumsum)
            S = np.std(subseries, ddof=1)

            if S > 0:
                rs_sum += R / S
                valid += 1

        if valid > 0:
            rs_values.append(np.log(rs_sum / valid))
            lag_values.append(np.log(lag))

    if len(rs_values) < 3:
        return 0.5

    # Linear regression: log(R/S) = H * log(n) + c
    try:
        coeffs = np.polyfit(lag_values, rs_values, 1)
        H = coeffs[0]
        return max(0.0, min(1.0, float(H)))
    except Exception:
        return 0.5


def store_metric(metric_name, asset_class, value, label, metadata=None):
    """Store a metric via the PHP intelligence API."""
    try:
        data = {
            "action": "store",
            "key": ADMIN_KEY,
            "metric_name": metric_name,
            "asset_class": asset_class,
            "metric_value": str(value),
            "metric_label": label,
        }
        if metadata:
            data["metadata"] = json.dumps(metadata)

        resp = requests.post(INTEL_API, data=data, headers=API_HEADERS, timeout=15)
        result = resp.json()
        if result.get("ok"):
            return True
        else:
            print(f"  API error: {result.get('error', 'unknown')}")
            return False
    except Exception as e:
        print(f"  Store error: {e}")
        return False


def main():
    print("=" * 60)
    print("WORLD-CLASS INTELLIGENCE: HMM Regime + Hurst Exponent")
    print("=" * 60)

    results = {}

    for asset_class, ticker in BENCHMARKS.items():
        print(f"\n--- {asset_class} ({ticker}) ---")

        # Fetch data
        print(f"  Fetching price data...")
        returns, vol = fetch_returns(ticker)

        if returns is None:
            print(f"  SKIP: No data available for {ticker}")
            continue

        # ──── HMM Regime Detection ────
        print(f"  Fitting 3-state HMM...")
        regime, probs, state_map = fit_hmm(returns, vol)

        if regime:
            print(f"  HMM Regime: {regime.upper()} (probs: {probs})")
            store_metric("hmm_regime", asset_class, list(probs.values())[0] if probs else 0,
                        regime, {"probabilities": probs, "ticker": ticker})
        else:
            print(f"  HMM failed, defaulting to neutral")
            store_metric("hmm_regime", asset_class, 0.5, "sideways",
                        {"error": "HMM fit failed", "ticker": ticker})

        # ──── Hurst Exponent ────
        try:
            data = yf.download(ticker, period="6mo", interval="1h", progress=False)
            if not data.empty and len(data) > 100:
                hourly_prices = data["Close"].values.flatten()
                hurst = calculate_hurst(hourly_prices, max_lag=200)
            else:
                # Fallback to daily
                data = yf.download(ticker, period="1y", interval="1d", progress=False)
                daily_prices = data["Close"].values.flatten()
                hurst = calculate_hurst(daily_prices, max_lag=100)
        except Exception as e:
            print(f"  Hurst data error: {e}")
            hurst = 0.5

        # Classify Hurst regime
        if hurst > 0.55:
            hurst_label = "trending"
        elif hurst < 0.45:
            hurst_label = "mean_reverting"
        else:
            hurst_label = "random_walk"

        print(f"  Hurst Exponent: {hurst:.4f} ({hurst_label})")
        store_metric("hurst_exponent", asset_class, hurst, hurst_label,
                    {"ticker": ticker})

        results[asset_class] = {
            "regime": regime or "sideways",
            "hurst": round(hurst, 4),
            "hurst_label": hurst_label
        }

    # ──── Summary ────
    print(f"\n{'=' * 60}")
    print("SUMMARY:")
    for ac, r in results.items():
        print(f"  {ac:8s}: regime={r['regime']:10s} hurst={r['hurst']:.4f} ({r['hurst_label']})")
    print(f"{'=' * 60}")

    return results


if __name__ == "__main__":
    main()
