"""
Pilot #2: Funding Rate Carry ML
--------------------------------
Predicts when crypto perpetual funding rates will be elevated, then enters
delta-neutral carry trades (long spot, short perp to collect funding).

Academic: Gate.io (2025) documented 19-115% annual returns on funding rate carry.
Expected impact: Sharpe 1.5-3.0 on delta-neutral carry, near-zero directional risk.

Data: Binance Futures API (funding rates, open interest, long/short ratio).
"""
import os, json, time, requests
import numpy as np
import pandas as pd
from datetime import datetime, timezone

PILOT_NAME = "funding_rate_carry"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Rotated Feb 26 2026: DOT → TAO (AI narrative momentum)
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "TAOUSDT",
]

# Threshold: funding rate > 0.01% per 8h = profitable carry
FUNDING_THRESHOLD = 0.0001
CONFIDENCE_THRESHOLD = 0.60


def fetch_funding_rates(symbol, limit=100):
    """Fetch historical funding rates with Binance → synthetic fallback."""
    try:
        from pilots.data_fetch import fetch_funding_rates as _fetch_fr
        rates = _fetch_fr(symbol, limit)
        if rates:
            return rates
    except ImportError:
        pass

    # Direct Binance fallback
    url = "https://fapi.binance.com/fapi/v1/fundingRate"
    params = {"symbol": symbol, "limit": limit}
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return [
            {"time": r["fundingTime"], "rate": float(r["fundingRate"])}
            for r in data
        ]
    except Exception as e:
        print(f"  [WARN] Funding rates for {symbol}: {e}")
        return []


def fetch_open_interest(symbol):
    """Fetch current open interest from Binance Futures."""
    url = "https://fapi.binance.com/fapi/v1/openInterest"
    params = {"symbol": symbol}
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return float(data.get("openInterest", 0))
    except Exception as e:
        print(f"  [WARN] Open interest for {symbol}: {e}")
        return 0.0


def fetch_long_short_ratio(symbol, period="1h", limit=30):
    """Fetch global long/short account ratio from Binance Futures."""
    url = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio"
    params = {"symbol": symbol, "period": period, "limit": limit}
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return [
            {"time": r["timestamp"], "ratio": float(r["longShortRatio"])}
            for r in data
        ]
    except Exception as e:
        print(f"  [WARN] L/S ratio for {symbol}: {e}")
        return []


def fetch_price_history(symbol, interval="1d", limit=30):
    """Fetch recent price candles with Binance → CoinGecko → Yahoo fallback."""
    try:
        from pilots.data_fetch import fetch_crypto_daily
        df = fetch_crypto_daily(symbol, limit)
        if df is not None and len(df) >= 5:
            return df["Close"].tolist()
    except ImportError:
        pass

    # Direct Binance fallback
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        closes = [float(c[4]) for c in data]
        return closes
    except Exception as e:
        print(f"  [WARN] Price history for {symbol}: {e}")
        return []


def build_features(funding_rates, oi, ls_ratios, prices):
    """Build feature vector for funding rate prediction."""
    features = {}

    # Last 5 funding rates
    rates = [r["rate"] for r in funding_rates[-5:]] if len(funding_rates) >= 5 else []
    for i in range(5):
        features[f"funding_{i}"] = rates[i] if i < len(rates) else 0.0

    # Funding rate trend (slope of last 10)
    recent_rates = [r["rate"] for r in funding_rates[-10:]]
    if len(recent_rates) >= 3:
        x = np.arange(len(recent_rates))
        slope = np.polyfit(x, recent_rates, 1)[0]
        features["funding_slope"] = slope
    else:
        features["funding_slope"] = 0.0

    # Average funding (20 period)
    all_rates = [r["rate"] for r in funding_rates[-20:]]
    features["funding_mean_20"] = np.mean(all_rates) if all_rates else 0.0

    # Open interest (raw value, will be relative across symbols)
    features["open_interest"] = oi

    # Long/short ratio (latest and trend)
    if ls_ratios:
        features["ls_ratio_latest"] = ls_ratios[-1]["ratio"]
        ls_vals = [r["ratio"] for r in ls_ratios[-10:]]
        features["ls_ratio_mean"] = np.mean(ls_vals)
    else:
        features["ls_ratio_latest"] = 1.0
        features["ls_ratio_mean"] = 1.0

    # Price momentum
    if len(prices) >= 10:
        features["momentum_5d"] = (prices[-1] / prices[-5] - 1) if prices[-5] != 0 else 0
        features["momentum_10d"] = (prices[-1] / prices[-10] - 1) if prices[-10] != 0 else 0
    else:
        features["momentum_5d"] = 0.0
        features["momentum_10d"] = 0.0

    # Realized volatility (annualized from daily returns)
    if len(prices) >= 5:
        rets = np.diff(np.log(np.array(prices[-20:]) + 1e-10))
        features["realized_vol"] = float(np.std(rets) * np.sqrt(365)) if len(rets) > 1 else 0.5
    else:
        features["realized_vol"] = 0.5

    return features


def train_model(all_funding_data):
    """Train GradientBoosting on historical funding rate features."""
    try:
        from sklearn.ensemble import GradientBoostingClassifier
        from sklearn.model_selection import cross_val_score
    except ImportError:
        print("  [WARN] scikit-learn not available, using heuristic fallback")
        return None

    # Build training dataset from historical funding sequences
    X, y = [], []
    for symbol, rates in all_funding_data.items():
        if len(rates) < 20:
            continue
        for i in range(15, len(rates) - 1):
            window = rates[max(0, i - 5):i]
            feats = [r["rate"] for r in window]
            # Pad to 5 features if needed
            while len(feats) < 5:
                feats.insert(0, 0.0)
            # Slope of last 10
            long_window = [r["rate"] for r in rates[max(0, i - 10):i]]
            if len(long_window) >= 3:
                slope = np.polyfit(np.arange(len(long_window)), long_window, 1)[0]
            else:
                slope = 0.0
            feats.append(slope)
            feats.append(np.mean([r["rate"] for r in rates[max(0, i - 20):i]]))

            X.append(feats)
            y.append(1 if rates[i]["rate"] > FUNDING_THRESHOLD else 0)

    if len(X) < 30:
        print(f"  [WARN] Only {len(X)} training samples, need at least 30")
        return None

    X, y = np.array(X), np.array(y)
    model = GradientBoostingClassifier(
        n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42
    )
    model.fit(X, y)

    # Quick cross-val
    scores = cross_val_score(model, X, y, cv=min(5, len(X) // 5 or 2), scoring="accuracy")
    print(f"  Model trained: {len(X)} samples, CV accuracy: {scores.mean():.1%}")
    return model


def heuristic_predict(features):
    """Fallback: rule-based funding rate prediction."""
    recent_avg = np.mean([features.get(f"funding_{i}", 0) for i in range(5)])
    slope = features.get("funding_slope", 0)
    ls = features.get("ls_ratio_latest", 1.0)

    # High recent funding + positive slope + longs dominating = likely high next
    score = 0.5
    if recent_avg > FUNDING_THRESHOLD:
        score += 0.15
    if slope > 0:
        score += 0.1
    if ls > 1.5:  # More longs than shorts = higher funding
        score += 0.1
    if features.get("momentum_5d", 0) > 0.05:  # Strong uptrend
        score += 0.05

    predicted_high = score > CONFIDENCE_THRESHOLD
    return predicted_high, round(score, 4)


def scan():
    """Scan all symbols for funding rate carry opportunities."""
    print(f"\n{'='*50}")
    print(f"[Pilot 2] Funding Rate Carry ML")
    print(f"{'='*50}")

    all_funding = {}
    results = []

    for symbol in SYMBOLS:
        print(f"\n  Scanning {symbol}...")
        time.sleep(0.2)  # Rate limiting

        # Fetch data
        funding = fetch_funding_rates(symbol, limit=100)
        oi = fetch_open_interest(symbol)
        ls_ratios = fetch_long_short_ratio(symbol)
        prices = fetch_price_history(symbol)

        all_funding[symbol] = funding

        if not funding:
            print(f"    Skipped (no funding data)")
            continue

        # Build features
        features = build_features(funding, oi, ls_ratios, prices)

        # Current funding rate
        current_rate = funding[-1]["rate"] if funding else 0
        annualized = current_rate * 3 * 365 * 100  # 3x per day, as percentage

        # Predict
        predicted_high, confidence = heuristic_predict(features)

        # Signal
        if predicted_high and confidence >= CONFIDENCE_THRESHOLD:
            signal = "ENTER_CARRY"
        elif current_rate > FUNDING_THRESHOLD * 2:
            signal = "ACTIVE_CARRY"  # Already very high
        else:
            signal = "WAIT"

        result = {
            "pair": symbol,
            "current_funding_rate": round(current_rate * 100, 4),  # As percentage
            "annualized_rate": round(annualized, 2),
            "predicted_high_next": predicted_high,
            "confidence": confidence,
            "signal": signal,
            "current_oi": oi,
            "ls_ratio": round(features.get("ls_ratio_latest", 1.0), 4),
            "momentum_5d": round(features.get("momentum_5d", 0) * 100, 2),
            "realized_vol": round(features.get("realized_vol", 0) * 100, 1),
        }
        results.append(result)

        emoji = ">>>" if signal != "WAIT" else "   "
        print(f"    {emoji} Funding: {result['current_funding_rate']:.4f}% "
              f"(~{annualized:.1f}% ann.) | Conf: {confidence:.1%} | {signal}")

    # Try ML model training on collected data
    model = train_model(all_funding)
    if model is not None:
        print(f"\n  [ML] Re-scoring with trained model...")
        for r in results:
            symbol = r["pair"]
            funding = all_funding.get(symbol, [])
            if len(funding) >= 15:
                rates = [f["rate"] for f in funding[-5:]]
                while len(rates) < 5:
                    rates.insert(0, 0.0)
                long_w = [f["rate"] for f in funding[-10:]]
                slope = np.polyfit(np.arange(len(long_w)), long_w, 1)[0] if len(long_w) >= 3 else 0
                mean_20 = np.mean([f["rate"] for f in funding[-20:]])
                feats = np.array(rates + [slope, mean_20]).reshape(1, -1)
                prob = model.predict_proba(feats)[0]
                high_prob = float(prob[1]) if len(prob) > 1 else 0.5
                r["ml_confidence"] = round(high_prob, 4)
                if high_prob >= CONFIDENCE_THRESHOLD:
                    r["signal"] = "ENTER_CARRY"
                    r["confidence"] = high_prob

    # Sort by confidence descending
    results.sort(key=lambda x: x["confidence"], reverse=True)

    # Summary
    carry_count = sum(1 for r in results if r["signal"] in ("ENTER_CARRY", "ACTIVE_CARRY"))
    print(f"\n  Summary: {carry_count}/{len(results)} pairs have carry signals")

    # Save output
    output = {
        "pilot": PILOT_NAME,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbols_scanned": len(results),
        "carry_signals": carry_count,
        "funding_threshold": f"{FUNDING_THRESHOLD * 100:.2f}%",
        "confidence_threshold": f"{CONFIDENCE_THRESHOLD:.0%}",
        "model_type": "GradientBoosting" if model else "heuristic",
        "reference": "Gate.io 2025 study: 19-115% annual on delta-neutral carry",
        "picks": results,
    }

    outpath = os.path.join(DATA_DIR, "funding_carry.json")
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2)

    print(f"  Output saved to pilots/data/funding_carry.json")
    return output


if __name__ == "__main__":
    scan()
