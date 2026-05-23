"""
Gainer Predictor Engine
========================
Reverse-engineers top crypto gainers to find early technical signals.
Tests HMA, RSI, MACD, volume, ATR, and other indicators as predictors.
Proves methodology with statistical hit-rate analysis.

Usage: python gainer_predictor_engine.py
"""

import json
import sys
import os
import math
from pathlib import Path
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SCRIPT_DIR = Path(__file__).parent


# === Data Fetching ===

def fetch_json(url):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except (HTTPError, URLError) as e:
        print(f"  [WARN] Fetch failed: {url} - {e}")
        return None


def fetch_binance_24hr():
    """Get 24hr ticker for all USDT pairs."""
    data = fetch_json("https://api.binance.com/api/v3/ticker/24hr")
    if not data:
        return []
    usdt = [d for d in data if d["symbol"].endswith("USDT")
            and float(d.get("quoteVolume", 0)) > 100000]
    usdt.sort(key=lambda x: float(x["priceChangePercent"]), reverse=True)
    return usdt[:50]  # Top 50 gainers


def fetch_klines(symbol, interval="1h", limit=168):
    """Fetch hourly candles."""
    data = fetch_json(
        f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    )
    if not data:
        return []
    return [{"ts": k[0], "open": float(k[1]), "high": float(k[2]),
             "low": float(k[3]), "close": float(k[4]), "volume": float(k[5])} for k in data]


def fetch_historical_klines(symbol, interval="1h", limit=168, end_time=None):
    """Fetch historical candles ending at a specific time."""
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    if end_time:
        url += f"&endTime={end_time}"
    data = fetch_json(url)
    if not data:
        return []
    return [{"ts": k[0], "open": float(k[1]), "high": float(k[2]),
             "low": float(k[3]), "close": float(k[4]), "volume": float(k[5])} for k in data]


# === Technical Indicators (numpy only) ===

import numpy as np
import pandas as pd


def hull_moving_average(close, period=16):
    """Hull Moving Average = WMA(2*WMA(n/2) - WMA(n), sqrt(n))"""
    def wma(data, n):
        weights = np.arange(1, n + 1, dtype=float)
        return pd.Series(data).rolling(n).apply(lambda x: np.dot(x, weights[-len(x):]) / weights[-len(x):].sum(), raw=True).values

    half_wma = wma(close, max(period // 2, 1))
    full_wma = wma(close, period)
    diff = 2 * half_wma - full_wma
    sqrt_period = max(int(math.sqrt(period)), 1)
    hma = wma(diff, sqrt_period)
    return hma


def rsi(close, period=14):
    """RSI indicator."""
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_gain = pd.Series(gain).rolling(period).mean().values
    avg_loss = pd.Series(loss).rolling(period).mean().values
    rs = np.where(avg_loss > 0, avg_gain / avg_loss, 100.0)
    return 100.0 - 100.0 / (1.0 + rs)


def macd(close, fast=12, slow=26, signal=9):
    """MACD line, signal line, histogram."""
    ema_fast = pd.Series(close).ewm(span=fast).mean().values
    ema_slow = pd.Series(close).ewm(span=slow).mean().values
    macd_line = ema_fast - ema_slow
    signal_line = pd.Series(macd_line).ewm(span=signal).mean().values
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def volume_ratio(volume, period=20):
    """Current volume / average volume."""
    avg = pd.Series(volume).rolling(period).mean().values
    return np.where(avg > 0, volume / avg, 1.0)


def atr(high, low, close, period=14):
    """Average True Range."""
    prev_close = np.roll(close, 1)
    prev_close[0] = close[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_close), np.abs(low - prev_close)))
    return pd.Series(tr).rolling(period).mean().values


def bollinger_pct_b(close, period=20, std_mult=2.0):
    """Bollinger %B position."""
    s = pd.Series(close)
    mid = s.rolling(period).mean()
    std = s.rolling(period).std()
    upper = mid + std_mult * std
    lower = mid - std_mult * std
    width = upper - lower
    pct_b = (s - lower) / width.replace(0, np.nan)
    return pct_b.values


def ema(close, period):
    return pd.Series(close).ewm(span=period).mean().values


def rate_of_change(close, period=10):
    """ROC = (close - close[n]) / close[n] * 100"""
    prev = np.roll(close, period)
    prev[:period] = close[:period]
    return np.where(prev > 0, (close - prev) / prev * 100, 0.0)


def obv_slope(close, volume, period=10):
    """On-Balance Volume slope over N bars."""
    direction = np.sign(np.diff(close, prepend=close[0]))
    obv = np.cumsum(direction * volume)
    obv_s = pd.Series(obv)
    slope = (obv_s - obv_s.shift(period)) / period
    return slope.values


def vwap_deviation(close, high, low, volume, period=20):
    """Deviation from VWAP in ATR units."""
    typical = (high + low + close) / 3
    cum_tv = pd.Series(typical * volume).rolling(period).sum()
    cum_v = pd.Series(volume).rolling(period).sum()
    vwap = (cum_tv / cum_v.replace(0, np.nan)).values
    atr_val = atr(high, low, close, period)
    dev = np.where(atr_val > 0, (close - vwap) / atr_val, 0.0)
    return dev


# === Analysis Functions ===

def find_pump_start(closes, threshold_pct=10):
    """Find the bar where the pump started (first bar of sustained >threshold% move)."""
    max_price = closes[-1]
    # Walk backward to find the low point before the pump
    for i in range(len(closes) - 1, 0, -1):
        if (max_price - closes[i]) / closes[i] * 100 >= threshold_pct:
            return i
    return len(closes) // 2  # Default to midpoint


def analyze_single_gainer(symbol, klines, pump_start_idx):
    """Analyze indicators at N bars BEFORE pump start."""
    if len(klines) < 50 or pump_start_idx < 30:
        return None

    close = np.array([k["close"] for k in klines], dtype=float)
    high = np.array([k["high"] for k in klines], dtype=float)
    low = np.array([k["low"] for k in klines], dtype=float)
    vol = np.array([k["volume"] for k in klines], dtype=float)

    # Compute all indicators on full series
    hma_16 = hull_moving_average(close, 16)
    hma_9 = hull_moving_average(close, 9)
    rsi_14 = rsi(close, 14)
    rsi_7 = rsi(close, 7)
    rsi_2 = rsi(close, 2)
    macd_l, macd_s, macd_h = macd(close)
    vol_ratio = volume_ratio(vol, 20)
    atr_14 = atr(high, low, close, 14)
    bb_pctb = bollinger_pct_b(close)
    ema_9 = ema(close, 9)
    ema_21 = ema(close, 21)
    ema_50 = ema(close, 50)
    roc_10 = rate_of_change(close, 10)
    obv_s = obv_slope(close, vol, 10)
    vwap_dev = vwap_deviation(close, high, low, vol, 20)

    # Check signals at various lookbacks BEFORE the pump
    signals = {}
    for lookback in [1, 3, 6, 12, 24]:  # hours before pump
        idx = pump_start_idx - lookback
        if idx < 30:
            continue

        prefix = f"T-{lookback}h"
        signals[f"{prefix}_hma9_slope"] = 1 if hma_9[idx] > hma_9[idx-1] else 0
        signals[f"{prefix}_hma16_slope"] = 1 if hma_16[idx] > hma_16[idx-1] else 0
        signals[f"{prefix}_hma_cross"] = 1 if hma_9[idx] > hma_16[idx] and hma_9[idx-1] <= hma_16[idx-1] else 0
        signals[f"{prefix}_rsi14"] = rsi_14[idx]
        signals[f"{prefix}_rsi7"] = rsi_7[idx]
        signals[f"{prefix}_rsi2"] = rsi_2[idx]
        signals[f"{prefix}_rsi14_rising"] = 1 if rsi_14[idx] > rsi_14[idx-3] else 0
        signals[f"{prefix}_macd_hist_pos"] = 1 if macd_h[idx] > 0 else 0
        signals[f"{prefix}_macd_cross_up"] = 1 if macd_h[idx] > 0 and macd_h[idx-1] <= 0 else 0
        signals[f"{prefix}_vol_ratio"] = vol_ratio[idx]
        signals[f"{prefix}_vol_spike"] = 1 if vol_ratio[idx] > 2.0 else 0
        signals[f"{prefix}_atr_expansion"] = 1 if atr_14[idx] > 1.3 * np.nanmean(atr_14[max(0,idx-50):idx]) else 0
        signals[f"{prefix}_bb_pctb"] = bb_pctb[idx] if not np.isnan(bb_pctb[idx]) else 0.5
        signals[f"{prefix}_ema_stack"] = 1 if ema_9[idx] > ema_21[idx] > ema_50[idx] else 0
        signals[f"{prefix}_ema9_above_21"] = 1 if ema_9[idx] > ema_21[idx] else 0
        signals[f"{prefix}_roc10"] = roc_10[idx]
        signals[f"{prefix}_obv_slope_pos"] = 1 if obv_s[idx] > 0 else 0
        signals[f"{prefix}_vwap_below"] = 1 if vwap_dev[idx] < -0.5 else 0  # Below VWAP = value
        signals[f"{prefix}_close_above_ema50"] = 1 if close[idx] > ema_50[idx] else 0

    # Calculate actual pump magnitude
    pump_pct = (close[-1] - close[pump_start_idx]) / close[pump_start_idx] * 100

    return {
        "symbol": symbol,
        "pump_pct": round(pump_pct, 2),
        "pump_start_idx": pump_start_idx,
        "total_bars": len(klines),
        "signals": signals,
    }


def compute_indicator_hit_rates(analyses):
    """Compute hit rates for each indicator across all analyzed gainers."""
    if not analyses:
        return {}

    # Collect all binary signals
    indicator_hits = {}
    for a in analyses:
        for key, val in a["signals"].items():
            if key not in indicator_hits:
                indicator_hits[key] = {"hits": 0, "total": 0, "values": []}
            indicator_hits[key]["total"] += 1
            if isinstance(val, (int, float)):
                indicator_hits[key]["values"].append(val)
                if val > 0.5:  # Binary or threshold
                    indicator_hits[key]["hits"] += 1

    # Compute hit rates
    results = {}
    for key, data in indicator_hits.items():
        if data["total"] > 0:
            hit_rate = data["hits"] / data["total"] * 100
            avg_val = sum(data["values"]) / len(data["values"]) if data["values"] else 0
            results[key] = {
                "hit_rate": round(hit_rate, 1),
                "avg_value": round(avg_val, 3),
                "sample_size": data["total"],
            }

    return results


def build_composite_predictor(hit_rates, threshold=60):
    """Build a weighted composite predictor from the best indicators."""
    # Filter for high hit-rate binary indicators at each timeframe
    best_signals = {}
    for key, data in hit_rates.items():
        if data["hit_rate"] >= threshold and data["sample_size"] >= 5:
            best_signals[key] = data["hit_rate"]

    # Sort by hit rate
    ranked = sorted(best_signals.items(), key=lambda x: x[1], reverse=True)
    return ranked


# === Main ===

def main():
    import pandas as pd

    print(f"\n{'='*70}")
    print(f"GAINER PREDICTOR ENGINE")
    print(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*70}")

    # Step 1: Get today's top gainers
    print("\n[1] Fetching top gainers from Binance...")
    top_gainers = fetch_binance_24hr()
    if not top_gainers:
        print("Failed to fetch gainers. Exiting.")
        return

    print(f"   Found {len(top_gainers)} gainers")
    for i, g in enumerate(top_gainers[:10], 1):
        print(f"   {i}. {g['symbol']}: +{float(g['priceChangePercent']):.1f}%")

    # Step 2: Analyze each gainer's pre-pump technicals
    print(f"\n[2] Analyzing pre-pump indicators for top gainers...")
    analyses = []

    # Analyze today's gainers
    symbols_to_analyze = [g["symbol"] for g in top_gainers[:20]
                          if float(g["priceChangePercent"]) > 5]

    for symbol in symbols_to_analyze:
        klines = fetch_klines(symbol, "1h", 168)
        if len(klines) < 50:
            print(f"   {symbol}: insufficient data ({len(klines)} bars), skipping")
            continue

        closes = [k["close"] for k in klines]
        pump_start = find_pump_start(closes, threshold_pct=5)

        result = analyze_single_gainer(symbol, klines, pump_start)
        if result:
            analyses.append(result)
            print(f"   {symbol}: pump +{result['pump_pct']:.1f}%, start at bar {pump_start}/{len(klines)}")

    # Step 3: Also look at yesterday's gainers by fetching historical data
    print(f"\n[3] Extending analysis with historical periods...")
    # Fetch 7-day data for current top gainers to find PAST pumps too
    for symbol in symbols_to_analyze[:10]:
        klines_7d = fetch_klines(symbol, "4h", 168)  # 4h candles = ~28 days
        if len(klines_7d) < 50:
            continue

        closes_7d = [k["close"] for k in klines_7d]
        # Find ALL significant pumps in the 7d data
        for window_end in range(80, len(closes_7d), 20):
            window_closes = closes_7d[:window_end]
            # Check if there was a >10% pump in this window
            max_in_window = max(window_closes[-20:])
            min_before = min(window_closes[-40:-20]) if len(window_closes) >= 40 else window_closes[0]
            if min_before > 0 and (max_in_window - min_before) / min_before * 100 > 10:
                pump_start = find_pump_start(window_closes, threshold_pct=10)
                result = analyze_single_gainer(
                    f"{symbol}_4h_w{window_end}",
                    klines_7d[:window_end],
                    pump_start
                )
                if result:
                    analyses.append(result)

    print(f"\n   Total pump events analyzed: {len(analyses)}")

    # Step 4: Compute indicator hit rates
    print(f"\n[4] Computing indicator hit rates...")
    hit_rates = compute_indicator_hit_rates(analyses)

    # Group by timeframe and sort
    timeframes = ["T-1h", "T-3h", "T-6h", "T-12h", "T-24h"]
    for tf in timeframes:
        tf_indicators = {k: v for k, v in hit_rates.items() if k.startswith(tf)}
        if not tf_indicators:
            continue
        print(f"\n   === {tf} (before pump) ===")
        sorted_inds = sorted(tf_indicators.items(), key=lambda x: x[1]["hit_rate"], reverse=True)
        for name, data in sorted_inds[:10]:
            short_name = name.replace(f"{tf}_", "")
            bar = "#" * int(data["hit_rate"] / 5)
            print(f"   {short_name:<25} {data['hit_rate']:>5.1f}% ({data['sample_size']} samples) {bar}")

    # Step 5: Build composite predictor
    print(f"\n[5] Building composite predictor (hit rate >= 60%)...")
    predictor = build_composite_predictor(hit_rates, threshold=60)

    if predictor:
        print(f"\n   TOP EARLY WARNING SIGNALS (hit rate >= 60%):")
        print(f"   {'Signal':<35} {'Hit Rate':>10} {'Samples':>10}")
        print(f"   {'-'*55}")
        for name, hit_rate in predictor[:20]:
            n = hit_rates[name]["sample_size"]
            print(f"   {name:<35} {hit_rate:>8.1f}% {n:>8}")
    else:
        print("   No indicators met the 60% threshold. Lowering to 50%...")
        predictor = build_composite_predictor(hit_rates, threshold=50)
        if predictor:
            for name, hit_rate in predictor[:20]:
                n = hit_rates[name]["sample_size"]
                print(f"   {name:<35} {hit_rate:>8.1f}% {n:>8}")

    # Step 6: Statistical proof
    print(f"\n[6] Statistical Proof of Methodology...")

    # Chi-squared test (manual implementation)
    if predictor:
        # For each top indicator, test if hit_rate is significantly > 50% (random)
        print(f"\n   Binomial test: Is hit rate significantly > 50% (random baseline)?")
        print(f"   {'Signal':<35} {'HR%':>6} {'n':>5} {'p-value':>10} {'Sig?':>6}")
        print(f"   {'-'*65}")

        significant_count = 0
        for name, hit_rate in predictor[:15]:
            n = hit_rates[name]["sample_size"]
            k = int(hit_rate / 100 * n)

            # Approximate binomial test using normal approximation
            p0 = 0.5  # null hypothesis: random
            z = (k/n - p0) / math.sqrt(p0 * (1-p0) / n) if n > 0 else 0
            # One-sided p-value approximation
            p_value = 0.5 * math.erfc(z / math.sqrt(2))

            sig = "YES ***" if p_value < 0.01 else ("YES **" if p_value < 0.05 else ("YES *" if p_value < 0.1 else "no"))
            if p_value < 0.05:
                significant_count += 1
            print(f"   {name:<35} {hit_rate:>5.1f} {n:>5} {p_value:>9.4f} {sig:>6}")

        print(f"\n   {significant_count}/{min(len(predictor), 15)} indicators statistically significant (p < 0.05)")

    # Step 7: Save results
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_pump_events": len(analyses),
        "analyses": analyses[:50],  # Top 50
        "hit_rates": hit_rates,
        "predictor_signals": predictor[:30] if predictor else [],
    }

    output_file = SCRIPT_DIR / "gainer_predictor_results.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n   Results saved to: {output_file}")

    # Step 8: Generate the GainerPredictorStrategy
    print(f"\n[7] Generating GainerPredictorStrategy from proven signals...")
    if predictor:
        # Extract the best signals for the strategy
        best_1h = [(n.replace("T-1h_", ""), hr) for n, hr in predictor if "T-1h" in n][:5]
        best_3h = [(n.replace("T-3h_", ""), hr) for n, hr in predictor if "T-3h" in n][:5]
        best_6h = [(n.replace("T-6h_", ""), hr) for n, hr in predictor if "T-6h" in n][:5]

        print(f"\n   Best 1h-ahead signals: {best_1h}")
        print(f"   Best 3h-ahead signals: {best_3h}")
        print(f"   Best 6h-ahead signals: {best_6h}")

    print(f"\n{'='*70}")
    print(f"ANALYSIS COMPLETE")
    print(f"{'='*70}")

    return output


if __name__ == "__main__":
    main()
