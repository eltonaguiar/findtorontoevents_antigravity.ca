"""
Pilot #4: Ornstein-Uhlenbeck Pairs Trading
--------------------------------------------
Statistical arbitrage on crypto pairs using cointegration testing and
OU process calibration. Trades mean-reverting spreads between correlated assets.

Academic: Huang (2016) - OU optimal pairs trading, Sharpe 0.8-2.4.
Expected impact: Market-neutral returns, uncorrelated to BTC direction.

Data: Binance 1h candles (free API, no key needed).
"""
import os, json, time, requests
import numpy as np
import pandas as pd
from datetime import datetime, timezone

PILOT_NAME = "ou_pairs_trading"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Candidate pairs (high likelihood of cointegration based on sector/correlation)
PAIR_CANDIDATES = [
    ("BTCUSDT", "ETHUSDT"),
    ("ETHUSDT", "BNBUSDT"),
    ("SOLUSDT", "AVAXUSDT"),
    ("LINKUSDT", "TAOUSDT"),  # Rotated Feb 26 2026: DOT → TAO
    ("XRPUSDT", "ADAUSDT"),
]

# Trading parameters
ENTRY_ZSCORE = 2.0       # Enter when spread deviates 2 sigma
EXIT_ZSCORE = 0.0        # Exit when spread reverts to mean
STOP_ZSCORE = 3.5        # Stop loss if spread diverges further
LOOKBACK_HOURS = 500     # ~21 days of hourly data


def fetch_hourly_candles(symbol, limit=500):
    """Fetch 1h candles with Binance → Yahoo fallback."""
    try:
        from pilots.data_fetch import fetch_crypto_hourly
        df = fetch_crypto_hourly(symbol, limit)
        if df is not None:
            return df[["Close"]]
    except ImportError:
        pass

    # Direct Binance fallback
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": "1h", "limit": min(limit, 1000)}
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        df = pd.DataFrame(data, columns=[
            "timestamp", "Open", "High", "Low", "Close", "Volume",
            "close_time", "qav", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore"
        ])
        df["Close"] = df["Close"].astype(float)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        return df[["Close"]]
    except Exception as e:
        print(f"  [WARN] Candles for {symbol}: {e}")
        return None


def ols_hedge_ratio(y, x):
    """Compute OLS hedge ratio (beta): y = alpha + beta * x + epsilon."""
    x_arr = np.array(x, dtype=float)
    y_arr = np.array(y, dtype=float)
    # Add intercept
    X = np.column_stack([np.ones(len(x_arr)), x_arr])
    try:
        beta = np.linalg.lstsq(X, y_arr, rcond=None)[0]
        return beta[1], beta[0]  # hedge_ratio, intercept
    except np.linalg.LinAlgError:
        return 1.0, 0.0


def compute_spread(prices_a, prices_b, hedge_ratio, intercept):
    """Compute the spread: A - hedge_ratio * B - intercept."""
    return np.array(prices_a) - hedge_ratio * np.array(prices_b) - intercept


def adf_test(series):
    """
    Augmented Dickey-Fuller test for stationarity.
    Uses statsmodels if available, otherwise a simple ADF approximation.
    Returns (adf_stat, p_value, is_stationary).
    """
    try:
        from statsmodels.tsa.stattools import adfuller
        result = adfuller(series, autolag="AIC")
        return result[0], result[1], result[1] < 0.05
    except ImportError:
        # Fallback: simple unit root test approximation
        # Regress delta_y on y_{t-1}
        y = np.array(series, dtype=float)
        dy = np.diff(y)
        y_lag = y[:-1]
        if len(dy) < 10:
            return 0, 1.0, False

        X = np.column_stack([np.ones(len(y_lag)), y_lag])
        try:
            beta = np.linalg.lstsq(X, dy, rcond=None)[0]
            residuals = dy - X @ beta
            se = np.sqrt(np.sum(residuals ** 2) / (len(dy) - 2))
            se_beta = se / np.sqrt(np.sum((y_lag - y_lag.mean()) ** 2))
            adf_stat = beta[1] / se_beta if se_beta > 1e-10 else 0

            # Approximate p-value using MacKinnon critical values (rough)
            # -3.43 (1%), -2.86 (5%), -2.57 (10%) for n~500
            if adf_stat < -3.43:
                p_val = 0.005
            elif adf_stat < -2.86:
                p_val = 0.03
            elif adf_stat < -2.57:
                p_val = 0.07
            else:
                p_val = 0.5

            return round(float(adf_stat), 4), round(p_val, 4), p_val < 0.05
        except Exception:
            return 0, 1.0, False


def estimate_ou_halflife(spread):
    """
    Estimate OU process half-life of mean reversion.
    OU: dS = theta * (mu - S) * dt + sigma * dW
    Half-life = ln(2) / theta
    """
    spread = np.array(spread, dtype=float)
    if len(spread) < 10:
        return float("inf")

    # Regress delta_spread on spread_{t-1}
    ds = np.diff(spread)
    s_lag = spread[:-1]

    X = np.column_stack([np.ones(len(s_lag)), s_lag])
    try:
        beta = np.linalg.lstsq(X, ds, rcond=None)[0]
        theta = -beta[1]  # Mean reversion speed

        if theta <= 0:
            return float("inf")  # Not mean-reverting

        half_life = np.log(2) / theta
        return max(1.0, float(half_life))  # In periods (hours)
    except Exception:
        return float("inf")


def analyze_pair(sym_a, sym_b):
    """Analyze a single pair for cointegration and trading signals."""
    print(f"\n  Analyzing {sym_a} / {sym_b}...")

    # Fetch data
    df_a = fetch_hourly_candles(sym_a, LOOKBACK_HOURS)
    time.sleep(0.2)
    df_b = fetch_hourly_candles(sym_b, LOOKBACK_HOURS)
    time.sleep(0.2)

    if df_a is None or df_b is None:
        return None

    # Align timestamps
    merged = pd.DataFrame({
        "A": df_a["Close"],
        "B": df_b["Close"],
    }).dropna()

    if len(merged) < 50:
        print(f"    [SKIP] Only {len(merged)} aligned candles (need 50+)")
        return None

    prices_a = merged["A"].values
    prices_b = merged["B"].values

    # Log prices for cointegration (more stable)
    log_a = np.log(prices_a)
    log_b = np.log(prices_b)

    # OLS hedge ratio
    hedge_ratio, intercept = ols_hedge_ratio(log_a, log_b)

    # Compute spread
    spread = compute_spread(log_a, log_b, hedge_ratio, intercept)

    # Test cointegration (ADF on spread)
    adf_stat, p_value, is_stationary = adf_test(spread)
    print(f"    Hedge ratio: {hedge_ratio:.4f} | ADF stat: {adf_stat:.3f} | p-value: {p_value:.4f}")

    if not is_stationary:
        print(f"    [SKIP] Not cointegrated (p={p_value:.3f} > 0.05)")
        # Still return info but mark as non-cointegrated
        return {
            "pair": f"{sym_a}/{sym_b}",
            "sym_a": sym_a,
            "sym_b": sym_b,
            "cointegrated": False,
            "adf_stat": round(adf_stat, 4),
            "cointegration_pvalue": round(p_value, 4),
            "hedge_ratio": round(hedge_ratio, 4),
            "signal": "NO_SIGNAL",
            "reason": f"Not cointegrated (p={p_value:.3f})",
        }

    # OU half-life estimation
    half_life = estimate_ou_halflife(spread)
    print(f"    Half-life: {half_life:.1f} hours ({half_life / 24:.1f} days)")

    # Current z-score
    spread_mean = np.mean(spread)
    spread_std = np.std(spread)
    if spread_std < 1e-10:
        z_score = 0.0
    else:
        z_score = (spread[-1] - spread_mean) / spread_std

    # Rolling z-score (for trend)
    window = min(50, len(spread) // 4)
    rolling_mean = np.mean(spread[-window:])
    rolling_std = np.std(spread[-window:])
    z_rolling = (spread[-1] - rolling_mean) / rolling_std if rolling_std > 1e-10 else 0

    print(f"    Z-score: {z_score:.3f} (rolling: {z_rolling:.3f})")

    # Signal generation
    signal = "NO_SIGNAL"
    direction_a = ""
    direction_b = ""
    reason = ""

    if z_score > ENTRY_ZSCORE:
        # Spread too high: short A, long B (expect reversion down)
        signal = "ENTER_SHORT_SPREAD"
        direction_a = "SELL"
        direction_b = "BUY"
        reason = f"Spread z={z_score:.2f} > {ENTRY_ZSCORE}: short {sym_a}, long {sym_b}"
    elif z_score < -ENTRY_ZSCORE:
        # Spread too low: long A, short B (expect reversion up)
        signal = "ENTER_LONG_SPREAD"
        direction_a = "BUY"
        direction_b = "SELL"
        reason = f"Spread z={z_score:.2f} < -{ENTRY_ZSCORE}: long {sym_a}, short {sym_b}"
    elif abs(z_score) < abs(EXIT_ZSCORE) + 0.3:
        signal = "EXIT"
        reason = f"Spread z={z_score:.2f} near mean: close positions"
    elif abs(z_score) > STOP_ZSCORE:
        signal = "STOP_LOSS"
        reason = f"Spread z={z_score:.2f} exceeds {STOP_ZSCORE}: relationship breaking"

    if signal == "NO_SIGNAL":
        reason = f"Spread z={z_score:.2f} within normal range ({-ENTRY_ZSCORE} to {ENTRY_ZSCORE})"

    # Spread statistics
    spread_stats = {
        "mean": round(float(spread_mean), 6),
        "std": round(float(spread_std), 6),
        "current": round(float(spread[-1]), 6),
        "min_30d": round(float(np.min(spread[-720:])), 6) if len(spread) >= 720 else round(float(np.min(spread)), 6),
        "max_30d": round(float(np.max(spread[-720:])), 6) if len(spread) >= 720 else round(float(np.max(spread)), 6),
    }

    # Current prices
    price_a = float(prices_a[-1])
    price_b = float(prices_b[-1])

    result = {
        "pair": f"{sym_a}/{sym_b}",
        "sym_a": sym_a,
        "sym_b": sym_b,
        "price_a": round(price_a, 4),
        "price_b": round(price_b, 4),
        "cointegrated": True,
        "adf_stat": round(adf_stat, 4),
        "cointegration_pvalue": round(p_value, 4),
        "hedge_ratio": round(hedge_ratio, 4),
        "half_life_hours": round(half_life, 1),
        "half_life_days": round(half_life / 24, 2),
        "z_score": round(z_score, 4),
        "z_score_rolling": round(z_rolling, 4),
        "signal": signal,
        "direction_a": direction_a,
        "direction_b": direction_b,
        "reason": reason,
        "spread_stats": spread_stats,
    }

    indicator = ">>>" if signal.startswith("ENTER") else "   "
    print(f"    {indicator} Signal: {signal}")

    return result


def scan():
    """Scan all pair candidates for OU pairs trading opportunities."""
    print(f"\n{'='*50}")
    print(f"[Pilot 4] Ornstein-Uhlenbeck Pairs Trading")
    print(f"{'='*50}")
    print(f"  Parameters: entry z={ENTRY_ZSCORE}, exit z={EXIT_ZSCORE}, stop z={STOP_ZSCORE}")
    print(f"  Lookback: {LOOKBACK_HOURS}h (~{LOOKBACK_HOURS // 24}d)")

    results = []
    for sym_a, sym_b in PAIR_CANDIDATES:
        result = analyze_pair(sym_a, sym_b)
        if result:
            results.append(result)

    # Summary
    cointegrated = [r for r in results if r.get("cointegrated")]
    active_signals = [r for r in results if r.get("signal", "").startswith("ENTER")]

    print(f"\n  {'='*40}")
    print(f"  Summary:")
    print(f"    Pairs analyzed: {len(results)}")
    print(f"    Cointegrated: {len(cointegrated)}")
    print(f"    Active signals: {len(active_signals)}")

    for r in cointegrated:
        hl = r.get("half_life_days", 0)
        z = r.get("z_score", 0)
        sig = r.get("signal", "")
        print(f"    {r['pair']:20s} | HL: {hl:.1f}d | z: {z:+.2f} | {sig}")

    # Sort: cointegrated first, then by abs(z_score) descending
    results.sort(key=lambda r: (not r.get("cointegrated", False), -abs(r.get("z_score", 0))))

    # Save output
    output = {
        "pilot": PILOT_NAME,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "parameters": {
            "entry_zscore": ENTRY_ZSCORE,
            "exit_zscore": EXIT_ZSCORE,
            "stop_zscore": STOP_ZSCORE,
            "lookback_hours": LOOKBACK_HOURS,
        },
        "pairs_analyzed": len(results),
        "cointegrated_count": len(cointegrated),
        "active_signals": len(active_signals),
        "model_type": "OLS_cointegration_OU",
        "reference": "Huang (2016): OU optimal pairs Sharpe 0.8-2.4",
        "pairs": results,
    }

    outpath = os.path.join(DATA_DIR, "ou_pairs.json")
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n  Output saved to pilots/data/ou_pairs.json")
    return output


if __name__ == "__main__":
    scan()
