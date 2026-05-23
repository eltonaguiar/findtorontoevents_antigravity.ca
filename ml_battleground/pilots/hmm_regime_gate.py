"""
Pilot #1: HMM Regime Gate
--------------------------
Uses Hidden Markov Model to detect market regime (bull/bear/range).
Only allows trades aligned with the detected regime.

Academic: Hamilton (1989) regime-switching, enhanced with Ang & Timmermann (2012).
Expected impact: +0.2 to +0.4 Sharpe improvement, max drawdown reduction 20-30%.

Data: Binance BTC 1d candles (free API, no key needed).
"""
import os, json, requests
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta

PILOT_NAME = "hmm_regime_gate"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_btc_daily(days=365):
    """Fetch BTC/USDT daily candles with Binance → CoinGecko → Yahoo fallback."""
    try:
        from pilots.data_fetch import fetch_crypto_daily
        df = fetch_crypto_daily("BTCUSDT", days)
        if df is not None:
            return df
    except ImportError:
        pass

    # Direct Binance fallback
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": "BTCUSDT", "interval": "1d", "limit": min(days, 1000)}
    resp = requests.get(url, params=params, timeout=15)
    data = resp.json()
    df = pd.DataFrame(data, columns=["timestamp","Open","High","Low","Close","Volume",
                                      "close_time","qav","trades","taker_buy_base",
                                      "taker_buy_quote","ignore"])
    for col in ["Open","High","Low","Close","Volume"]:
        df[col] = df[col].astype(float)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df

def compute_features(df):
    """Compute HMM input features: daily returns and realized volatility."""
    df["returns"] = df["Close"].pct_change()
    df["vol_20d"] = df["returns"].rolling(20).std() * np.sqrt(365)  # annualized
    df["vol_5d"] = df["returns"].rolling(5).std() * np.sqrt(365)
    df["momentum_10d"] = df["Close"].pct_change(10)
    df = df.dropna()
    return df

def train_hmm(df, n_states=3):
    """Train a 3-state Gaussian HMM on returns + volatility."""
    try:
        from hmmlearn.hmm import GaussianHMM
    except ImportError:
        # Fallback: simple rule-based regime detection
        print("[HMM] hmmlearn not available, using rule-based fallback")
        return None

    features = df[["returns", "vol_20d", "momentum_10d"]].values

    model = GaussianHMM(
        n_components=n_states,
        covariance_type="full",
        n_iter=200,
        random_state=42,
    )
    model.fit(features)

    # Predict hidden states
    states = model.predict(features)
    df["regime"] = states

    # Label states by average return (bull = highest mean return, bear = lowest)
    state_returns = {}
    for s in range(n_states):
        mask = states == s
        state_returns[s] = df["returns"].values[mask].mean()

    sorted_states = sorted(state_returns, key=state_returns.get)
    # Map: lowest return = bear(0), middle = range(1), highest = bull(2)
    label_map = {sorted_states[0]: "bear", sorted_states[1]: "range", sorted_states[2]: "bull"}

    df["regime_label"] = df["regime"].map(label_map)

    return model, label_map

def rule_based_regime(df):
    """Fallback regime detection without hmmlearn."""
    df["sma50"] = df["Close"].rolling(50).mean()
    df["sma200"] = df["Close"].rolling(200).mean()

    conditions = []
    for i in range(len(df)):
        price = df["Close"].iloc[i]
        sma50 = df["sma50"].iloc[i] if not pd.isna(df["sma50"].iloc[i]) else price
        sma200 = df["sma200"].iloc[i] if not pd.isna(df["sma200"].iloc[i]) else price
        vol = df["vol_20d"].iloc[i] if "vol_20d" in df.columns and not pd.isna(df["vol_20d"].iloc[i]) else 0.5

        if price > sma50 and price > sma200:
            conditions.append("bull")
        elif price < sma200 * 0.9:  # 10% below 200 SMA
            conditions.append("bear")
        else:
            conditions.append("range")

    df["regime_label"] = conditions
    return df

def detect_current_regime():
    """Main function: detect current market regime and return gate decision."""
    print(f"\n{'='*50}")
    print(f"[Pilot 1] HMM Regime Gate")
    print(f"{'='*50}")

    # Fetch data
    df = fetch_btc_daily(365)
    if df is None or len(df) < 30:
        print("  [ERROR] Could not fetch BTC daily data from any source")
        output = {
            "pilot": PILOT_NAME, "method": "no_data",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "current_regime": "unknown", "error": "No data available",
        }
        with open(os.path.join(DATA_DIR, "hmm_regime_gate.json"), "w") as f:
            json.dump(output, f, indent=2)
        return output

    df = compute_features(df)
    print(f"  Loaded {len(df)} daily BTC candles")

    if len(df) < 30:
        print("  [WARN] Insufficient data after feature computation, using rule-based")
        df = fetch_btc_daily(365)
        df["returns"] = df["Close"].pct_change().fillna(0)
        df["vol_20d"] = 0.5
        result = None
    else:
        # Try HMM, fall back to rules
        result = train_hmm(df)
    if result is None:
        df = rule_based_regime(df)
        method = "rule_based"
    else:
        model, label_map = result
        method = "hmm_3state"

    # Current regime
    current_regime = df["regime_label"].iloc[-1]
    current_price = float(df["Close"].iloc[-1])
    current_vol = float(df["vol_20d"].iloc[-1]) if "vol_20d" in df.columns else 0

    # Regime history (last 30 days)
    recent = df["regime_label"].tail(30).value_counts().to_dict()

    # Gate decision
    if current_regime == "bull":
        allowed_signals = ["BUY"]
        gate_reason = "Bull regime: only BUY signals allowed"
    elif current_regime == "bear":
        allowed_signals = ["SELL"]
        gate_reason = "Bear regime: only SELL signals allowed"
    else:
        allowed_signals = ["BUY", "SELL"]
        gate_reason = "Range regime: both BUY and SELL allowed (mean reversion)"

    print(f"  Current regime: {current_regime.upper()}")
    print(f"  BTC price: ${current_price:,.0f}")
    print(f"  20d annualized vol: {current_vol:.1%}")
    print(f"  Gate decision: {gate_reason}")
    print(f"  Recent 30d regimes: {recent}")

    # Calculate regime statistics
    regime_stats = {}
    for regime in ["bull", "bear", "range"]:
        mask = df["regime_label"] == regime
        if mask.sum() > 0:
            regime_stats[regime] = {
                "days": int(mask.sum()),
                "pct_of_history": round(mask.sum() / len(df) * 100, 1),
                "avg_daily_return": round(float(df.loc[mask, "returns"].mean() * 100), 3),
                "avg_vol": round(float(df.loc[mask, "vol_20d"].mean() * 100), 1) if "vol_20d" in df.columns else 0,
            }

    # Save output
    output = {
        "pilot": PILOT_NAME,
        "method": method,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "current_regime": current_regime,
        "btc_price": current_price,
        "annualized_vol": round(current_vol * 100, 1),
        "allowed_signals": allowed_signals,
        "gate_reason": gate_reason,
        "recent_30d": recent,
        "regime_stats": regime_stats,
        "recommendation": f"Only trade {'/'.join(allowed_signals)} signals in {current_regime} regime",
    }

    with open(os.path.join(DATA_DIR, "hmm_regime_gate.json"), "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n  Output saved to pilots/data/hmm_regime_gate.json")
    return output

if __name__ == "__main__":
    detect_current_regime()
