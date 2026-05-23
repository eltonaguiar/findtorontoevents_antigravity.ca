"""
Pilot #3: Cross-Asset Momentum ML
-----------------------------------
Detects risk-on/risk-off regime by tracking momentum across gold, bonds,
USD, equities, and crypto simultaneously. Generates cross-asset picks.

Academic: CME Group study - cross-asset momentum Sharpe 0.78, enhanced with ML to 1.0+.
Expected impact: Better regime awareness, avoiding crypto longs during risk-off.

Data: Yahoo Finance (raw HTTP) for traditional assets, Binance for crypto.
"""
import os, json, time, requests
import numpy as np
import pandas as pd
from datetime import datetime, timezone

PILOT_NAME = "cross_asset_momentum"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

YAHOO_ASSETS = {
    "GLD": "Gold ETF",
    "TLT": "20Y Treasury Bond ETF",
    "SPY": "S&P 500 ETF",
    "QQQ": "Nasdaq 100 ETF",
    "IWM": "Russell 2000 ETF",
    "DX-Y.NYB": "USD Index",
}

CRYPTO_ASSETS = {
    "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum",
}

ALL_SYMBOLS = list(YAHOO_ASSETS.keys()) + list(CRYPTO_ASSETS.keys())


def fetch_yahoo(symbol, range_days=90):
    """Fetch daily OHLCV from Yahoo Finance via raw HTTP."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"range": f"{range_days}d", "interval": "1d"}
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        quotes = result["indicators"]["quote"][0]

        df = pd.DataFrame({
            "timestamp": pd.to_datetime(timestamps, unit="s"),
            "Close": quotes["close"],
            "Volume": quotes.get("volume", [0] * len(timestamps)),
        })
        df.set_index("timestamp", inplace=True)
        df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
        df = df.dropna(subset=["Close"])
        return df
    except Exception as e:
        print(f"  [WARN] Yahoo fetch {symbol}: {e}")
        return None


def compute_momentum_features(df):
    """Compute momentum and volatility features for a single asset."""
    closes = df["Close"]
    features = {}

    # Momentum at various lookbacks
    for period in [5, 10, 20, 60]:
        if len(closes) >= period:
            features[f"mom_{period}d"] = float(closes.iloc[-1] / closes.iloc[-period] - 1)
        else:
            features[f"mom_{period}d"] = 0.0

    # 20-day realized volatility (annualized)
    rets = closes.pct_change().dropna()
    if len(rets) >= 20:
        features["vol_20d"] = float(rets.tail(20).std() * np.sqrt(252))
    else:
        features["vol_20d"] = float(rets.std() * np.sqrt(252)) if len(rets) > 1 else 0.5

    # Current price
    features["price"] = float(closes.iloc[-1])

    return features


def compute_cross_correlations(all_data, window=20):
    """Compute rolling cross-asset correlations."""
    corrs = {}

    pairs = [
        ("GLD", "BTC-USD", "gold_btc"),
        ("SPY", "BTC-USD", "spy_btc"),
        ("TLT", "BTC-USD", "tlt_btc"),
        ("DX-Y.NYB", "BTC-USD", "usd_btc"),
        ("GLD", "TLT", "gold_bond"),
        ("SPY", "TLT", "spy_bond"),
    ]

    for sym1, sym2, label in pairs:
        if sym1 in all_data and sym2 in all_data:
            df1 = all_data[sym1]["Close"]
            df2 = all_data[sym2]["Close"]
            # Align on common dates
            combined = pd.DataFrame({"a": df1, "b": df2}).dropna()
            if len(combined) >= window:
                ret_a = combined["a"].pct_change().dropna()
                ret_b = combined["b"].pct_change().dropna()
                common = pd.DataFrame({"a": ret_a, "b": ret_b}).dropna()
                if len(common) >= window:
                    corrs[f"corr_{label}_{window}d"] = float(
                        common["a"].tail(window).corr(common["b"].tail(window))
                    )
                    continue
        corrs[f"corr_{label}_{window}d"] = 0.0

    return corrs


def detect_regime(features_by_asset, correlations):
    """Rule-based cross-asset regime detection."""
    gold = features_by_asset.get("GLD", {})
    tlt = features_by_asset.get("TLT", {})
    spy = features_by_asset.get("SPY", {})
    btc = features_by_asset.get("BTC-USD", {})
    usd = features_by_asset.get("DX-Y.NYB", {})

    gold_up = gold.get("mom_10d", 0) > 0.01
    bond_up = tlt.get("mom_10d", 0) > 0.01
    spy_up = spy.get("mom_10d", 0) > 0.01
    btc_up = btc.get("mom_10d", 0) > 0.02
    usd_down = usd.get("mom_10d", 0) < -0.005

    # Regime classification
    if gold_up and not btc_up and not spy_up:
        regime = "RISK_OFF"
        description = "Gold up, risk assets down - flight to safety"
    elif usd_down and spy_up and btc_up:
        regime = "RISK_ON"
        description = "Weak USD, equities and crypto rising - risk appetite high"
    elif not spy_up and not btc_up and not gold_up:
        regime = "PANIC"
        description = "All assets declining - stay out or hedge"
    elif bond_up and not spy_up:
        regime = "FLIGHT_TO_SAFETY"
        description = "Bonds bid, equities weak - defensive positioning"
    elif btc_up and spy_up:
        regime = "RISK_ON"
        description = "Broad risk-on across equities and crypto"
    else:
        regime = "MIXED"
        description = "No clear cross-asset signal"

    return regime, description


def train_btc_predictor(all_data, features_by_asset, correlations):
    """Train ML model to predict BTC 5-day direction from cross-asset features."""
    try:
        from sklearn.ensemble import GradientBoostingClassifier
        from sklearn.model_selection import cross_val_score
    except ImportError:
        print("  [WARN] scikit-learn not available, using regime heuristic only")
        return None, None

    # Build aligned dataset
    btc_df = all_data.get("BTC-USD")
    if btc_df is None or len(btc_df) < 30:
        return None, None

    # We need all assets aligned
    frames = {}
    for sym, df in all_data.items():
        if df is not None and len(df) > 0:
            frames[sym] = df["Close"].rename(sym)

    if len(frames) < 4:
        print(f"  [WARN] Only {len(frames)} assets available, need at least 4")
        return None, None

    merged = pd.DataFrame(frames).dropna()
    if len(merged) < 30:
        return None, None

    # Compute rolling features
    X_rows, y_rows = [], []
    for i in range(25, len(merged) - 5):
        row = []
        for sym in merged.columns:
            prices = merged[sym].iloc[:i + 1]
            # 5d, 10d, 20d momentum
            row.append(float(prices.iloc[-1] / prices.iloc[-5] - 1) if len(prices) >= 5 else 0)
            row.append(float(prices.iloc[-1] / prices.iloc[-10] - 1) if len(prices) >= 10 else 0)
            row.append(float(prices.iloc[-1] / prices.iloc[-20] - 1) if len(prices) >= 20 else 0)
            # 10d vol
            rets = prices.pct_change().dropna().tail(10)
            row.append(float(rets.std()) if len(rets) > 1 else 0)

        # Cross correlations (BTC vs SPY, BTC vs GLD)
        for other in ["SPY", "GLD", "TLT"]:
            if other in merged.columns and "BTC-USD" in merged.columns:
                window = merged.iloc[max(0, i - 20):i + 1]
                r1 = window.get("BTC-USD", pd.Series()).pct_change().dropna()
                r2 = window.get(other, pd.Series()).pct_change().dropna()
                common = pd.DataFrame({"a": r1, "b": r2}).dropna()
                row.append(float(common["a"].corr(common["b"])) if len(common) > 5 else 0)
            else:
                row.append(0)

        X_rows.append(row)

        # Target: BTC up in next 5 days?
        btc_now = merged["BTC-USD"].iloc[i] if "BTC-USD" in merged.columns else 0
        btc_future = merged["BTC-USD"].iloc[i + 5] if "BTC-USD" in merged.columns else 0
        y_rows.append(1 if btc_future > btc_now else 0)

    if len(X_rows) < 20:
        return None, None

    X, y = np.array(X_rows), np.array(y_rows)

    model = GradientBoostingClassifier(
        n_estimators=80, max_depth=3, learning_rate=0.1, random_state=42
    )
    model.fit(X, y)

    scores = cross_val_score(model, X, y, cv=min(5, len(X) // 5 or 2), scoring="accuracy")
    accuracy = scores.mean()
    print(f"  [ML] BTC 5d predictor: {len(X)} samples, CV accuracy: {accuracy:.1%}")

    # Predict current
    latest_row = X_rows[-1] if X_rows else None
    if latest_row is not None:
        prob = model.predict_proba(np.array(latest_row).reshape(1, -1))[0]
        btc_up_prob = float(prob[1]) if len(prob) > 1 else 0.5
    else:
        btc_up_prob = 0.5

    return model, {"accuracy": round(accuracy, 4), "btc_5d_up_prob": round(btc_up_prob, 4)}


def generate_picks(regime, features_by_asset, ml_result):
    """Generate cross-asset picks based on regime and ML prediction."""
    picks = []

    btc_up_prob = ml_result.get("btc_5d_up_prob", 0.5) if ml_result else 0.5

    if regime == "RISK_ON":
        if btc_up_prob > 0.55:
            picks.append({"asset": "BTC", "direction": "BUY", "reason": "Risk-on + ML bullish",
                          "confidence": round(btc_up_prob, 2)})
            picks.append({"asset": "ETH", "direction": "BUY", "reason": "Risk-on beta play",
                          "confidence": round(btc_up_prob * 0.9, 2)})
        picks.append({"asset": "SPY", "direction": "BUY", "reason": "Risk-on equities",
                      "confidence": 0.6})

    elif regime == "RISK_OFF":
        picks.append({"asset": "GLD", "direction": "BUY", "reason": "Flight to gold",
                      "confidence": 0.65})
        picks.append({"asset": "TLT", "direction": "BUY", "reason": "Safe haven bonds",
                      "confidence": 0.6})
        if btc_up_prob < 0.4:
            picks.append({"asset": "BTC", "direction": "SELL", "reason": "Risk-off + ML bearish",
                          "confidence": round(1 - btc_up_prob, 2)})

    elif regime == "PANIC":
        picks.append({"asset": "TLT", "direction": "BUY", "reason": "Panic flight to bonds",
                      "confidence": 0.55})
        picks.append({"asset": "ALL_RISK", "direction": "REDUCE", "reason": "Panic: reduce exposure",
                      "confidence": 0.7})

    elif regime == "FLIGHT_TO_SAFETY":
        picks.append({"asset": "TLT", "direction": "BUY", "reason": "Bond rally in safety flight",
                      "confidence": 0.65})
        picks.append({"asset": "GLD", "direction": "BUY", "reason": "Gold as safe haven",
                      "confidence": 0.55})

    else:  # MIXED
        picks.append({"asset": "NONE", "direction": "WAIT", "reason": "No clear cross-asset signal",
                      "confidence": 0.5})

    return picks


def scan():
    """Scan cross-asset momentum and generate regime + picks."""
    print(f"\n{'='*50}")
    print(f"[Pilot 3] Cross-Asset Momentum ML")
    print(f"{'='*50}")

    # Fetch all asset data
    all_data = {}
    features_by_asset = {}

    for symbol in ALL_SYMBOLS:
        print(f"  Fetching {symbol}...")
        df = fetch_yahoo(symbol)
        time.sleep(0.3)  # Rate limit Yahoo

        if df is not None and len(df) > 5:
            all_data[symbol] = df
            features_by_asset[symbol] = compute_momentum_features(df)
            print(f"    {len(df)} days | Price: ${features_by_asset[symbol]['price']:,.2f} "
                  f"| 10d mom: {features_by_asset[symbol]['mom_10d']:.2%}")
        else:
            print(f"    [SKIP] No data")

    # Cross-asset correlations
    correlations = compute_cross_correlations(all_data)
    print(f"\n  Cross-correlations (20d):")
    for k, v in correlations.items():
        print(f"    {k}: {v:+.3f}")

    # Detect regime
    regime, description = detect_regime(features_by_asset, correlations)
    print(f"\n  Regime: {regime}")
    print(f"  Detail: {description}")

    # Train ML predictor
    model, ml_result = train_btc_predictor(all_data, features_by_asset, correlations)
    if ml_result:
        print(f"  ML BTC 5d up probability: {ml_result['btc_5d_up_prob']:.1%}")

    # Generate picks
    picks = generate_picks(regime, features_by_asset, ml_result)
    print(f"\n  Picks ({len(picks)}):")
    for p in picks:
        print(f"    {p['direction']:6s} {p['asset']:8s} | Conf: {p['confidence']:.0%} | {p['reason']}")

    # Compile output
    output = {
        "pilot": PILOT_NAME,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "regime": regime,
        "regime_description": description,
        "assets_loaded": len(all_data),
        "model_type": "GradientBoosting" if model else "heuristic",
        "ml_result": ml_result,
        "reference": "CME Group: cross-asset momentum Sharpe 0.78, ML-enhanced to 1.0+",
        "asset_features": {
            sym: {k: round(v, 6) if isinstance(v, float) else v for k, v in feat.items()}
            for sym, feat in features_by_asset.items()
        },
        "correlations": {k: round(v, 4) for k, v in correlations.items()},
        "picks": picks,
    }

    outpath = os.path.join(DATA_DIR, "cross_asset_momentum.json")
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n  Output saved to pilots/data/cross_asset_momentum.json")
    return output


if __name__ == "__main__":
    scan()
