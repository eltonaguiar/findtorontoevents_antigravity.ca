"""Gainer Scoring Service — CLI tool for ranking crypto "about to pump" predictions.

Lightweight scoring service that runs in CI (GitHub Actions) without FastAPI.
Fetches live Binance data, computes the VelocityGainer composite score for
top-volume USDT pairs, and outputs the top 10 predictions.

Usage:
    python gainer_scoring_service.py              # scan and print top 10
    python gainer_scoring_service.py --top 20     # top 20
    python gainer_scoring_service.py --save       # save to data/gainer_scores_latest.json
    python gainer_scoring_service.py --verbose    # show all sub-scores

Dependencies: stdlib only (json, urllib, math). No pandas/numpy required.
"""

import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"


# ===================================================================== #
#  HTTP helpers                                                         #
# ===================================================================== #

def fetch_json(url, retries=2):
    """Fetch JSON from URL with retries."""
    req = Request(url, headers={"User-Agent": "GainerScoringService/1.0"})
    for attempt in range(retries + 1):
        try:
            with urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except (HTTPError, URLError, Exception) as e:
            if attempt < retries:
                time.sleep(1)
                continue
            print(f"  [WARN] Fetch failed after {retries + 1} attempts: {url} - {e}")
            return None


# ===================================================================== #
#  Binance API                                                          #
# ===================================================================== #

def fetch_all_usdt_tickers():
    """Get 24hr ticker for all USDT pairs, return top 50 by quoteVolume.
    Falls back to alternate Binance endpoints if primary is geo-blocked (HTTP 451).
    """
    # Try multiple Binance API endpoints (some regions block api.binance.com)
    endpoints = [
        "https://api.binance.com/api/v3/ticker/24hr",
        "https://api1.binance.com/api/v3/ticker/24hr",
        "https://api2.binance.com/api/v3/ticker/24hr",
        "https://api3.binance.com/api/v3/ticker/24hr",
        "https://api4.binance.com/api/v3/ticker/24hr",
        "https://data-api.binance.vision/api/v3/ticker/24hr",
    ]
    data = None
    for ep in endpoints:
        data = fetch_json(ep)
        if data:
            break
    if not data:
        # Last resort: try CoinGecko for top coins
        print("  [WARN] All Binance endpoints failed, trying CoinGecko fallback...")
        cg = fetch_json("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=volume_desc&per_page=50&page=1&sparkline=false&price_change_percentage=24h")
        if cg:
            return [{
                "symbol": (c.get("symbol", "").upper() + "USDT"),
                "price": float(c.get("current_price", 0)),
                "change_pct": float(c.get("price_change_percentage_24h", 0) or 0),
                "quote_volume": float(c.get("total_volume", 0)),
            } for c in cg if c.get("current_price")]
        return []
    usdt = []
    for d in data:
        sym = d.get("symbol", "")
        if not sym.endswith("USDT"):
            continue
        qvol = float(d.get("quoteVolume", 0))
        if qvol < 500_000:  # filter dust
            continue
        usdt.append({
            "symbol": sym,
            "price": float(d.get("lastPrice", 0)),
            "change_pct": float(d.get("priceChangePercent", 0)),
            "quote_volume": qvol,
        })
    usdt.sort(key=lambda x: x["quote_volume"], reverse=True)
    return usdt[:50]


# Track whether Binance is geo-blocked so we skip it for subsequent calls
_binance_klines_blocked = False

# CoinGecko ID cache: maps symbol like "BTCUSDT" to CoinGecko coin ID
_coingecko_id_cache = None


def _get_coingecko_id_map():
    """Build a mapping from uppercase symbol to CoinGecko coin ID.
    Uses the /coins/markets endpoint (already fetched for tickers) to avoid
    hitting the /coins/list endpoint which is rate-limited.
    """
    global _coingecko_id_cache
    if _coingecko_id_cache is not None:
        return _coingecko_id_cache

    _coingecko_id_cache = {}
    # Fetch top 250 coins by market cap
    for page in (1, 2, 3):
        url = (
            f"https://api.coingecko.com/api/v3/coins/markets"
            f"?vs_currency=usd&order=market_cap_desc&per_page=100&page={page}"
            f"&sparkline=false"
        )
        data = fetch_json(url)
        if data:
            for c in data:
                sym = (c.get("symbol") or "").upper() + "USDT"
                cg_id = c.get("id")
                if cg_id:
                    _coingecko_id_cache[sym] = cg_id
        time.sleep(1.2)  # CoinGecko free tier: ~30 req/min
    return _coingecko_id_cache


def fetch_klines(symbol, interval="1h", limit=100):
    """Fetch hourly klines from Binance. Falls back to CoinGecko OHLC if geo-blocked.
    Returns list of OHLCV dicts.
    """
    global _binance_klines_blocked

    # Try Binance endpoints first (unless already known to be blocked)
    if not _binance_klines_blocked:
        bases = [
            "https://api.binance.com", "https://api1.binance.com",
            "https://api2.binance.com", "https://api3.binance.com",
            "https://data-api.binance.vision",
        ]
        for base in bases:
            url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
            data = fetch_json(url)
            if data and len(data) >= 2:
                candles = []
                for k in data:
                    candles.append({
                        "ts": int(k[0]),
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[5]),
                    })
                return candles

        # If we get here, all Binance endpoints failed
        print(f"  [WARN] All Binance kline endpoints failed for {symbol}, trying CoinGecko OHLC...")
        _binance_klines_blocked = True

    # --- CoinGecko OHLC fallback ---
    id_map = _get_coingecko_id_map()
    cg_id = id_map.get(symbol)
    if not cg_id:
        return None

    # CoinGecko /ohlc: days=1 gives ~6 candles (4h), days=7 gives ~42 candles (4h),
    # days=14 gives ~84 candles (4h). Use days=14 for ~84 data points.
    days = 14
    url = f"https://api.coingecko.com/api/v3/coins/{cg_id}/ohlc?vs_currency=usd&days={days}"
    data = fetch_json(url)
    if not data or len(data) < 2:
        return None

    candles = []
    for k in data:
        # CoinGecko OHLC format: [timestamp, open, high, low, close]
        # No volume data from CoinGecko OHLC, so we estimate with 0
        candles.append({
            "ts": int(k[0]),
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": 1.0,  # Placeholder — CoinGecko OHLC doesn't include volume
        })

    # CoinGecko OHLC with days=14 returns 4h candles. We keep them as-is since
    # the scoring logic works with any timeframe (indicators adapt to bar count).
    if len(candles) >= 2:
        return candles
    return None


# ===================================================================== #
#  Pure-Python indicators (no numpy/pandas)                             #
# ===================================================================== #

def compute_rsi(closes, period):
    """RSI using Wilder smoothing. Returns list same length as closes."""
    n = len(closes)
    if n < period + 1:
        return [50.0] * n

    rsi = [50.0] * n
    gains = [0.0] * n
    losses = [0.0] * n
    for i in range(1, n):
        delta = closes[i] - closes[i - 1]
        gains[i] = delta if delta > 0 else 0.0
        losses[i] = -delta if delta < 0 else 0.0

    avg_gain = sum(gains[1:period + 1]) / period
    avg_loss = sum(losses[1:period + 1]) / period
    alpha = 1.0 / period

    for i in range(period, n):
        if i > period:
            avg_gain = avg_gain * (1 - alpha) + gains[i] * alpha
            avg_loss = avg_loss * (1 - alpha) + losses[i] * alpha
        if avg_loss > 0:
            rs = avg_gain / avg_loss
            rsi[i] = 100.0 - (100.0 / (1.0 + rs))
        else:
            rsi[i] = 100.0

    return rsi


def compute_ema(values, span):
    """EMA. Returns list same length as values."""
    alpha = 2.0 / (span + 1)
    out = [values[0]]
    for i in range(1, len(values)):
        out.append(alpha * values[i] + (1 - alpha) * out[-1])
    return out


def compute_atr(highs, lows, closes, period):
    """ATR using Wilder smoothing. Returns list same length as input."""
    n = len(closes)
    tr = [highs[0] - lows[0]]
    for i in range(1, n):
        tr.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        ))

    atr = [0.0] * n
    if n <= period:
        return atr

    atr[period - 1] = sum(tr[:period]) / period
    for i in range(period, n):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period

    return atr


def compute_obv(closes, volumes):
    """On-Balance Volume."""
    obv = [0.0]
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            obv.append(obv[-1] + volumes[i])
        elif closes[i] < closes[i - 1]:
            obv.append(obv[-1] - volumes[i])
        else:
            obv.append(obv[-1])
    return obv


def compute_macd_histogram(closes, fast=12, slow=26, signal=9):
    """MACD histogram = MACD line - signal line."""
    ema_fast = compute_ema(closes, fast)
    ema_slow = compute_ema(closes, slow)
    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    signal_line = compute_ema(macd_line, signal)
    return [m - s for m, s in zip(macd_line, signal_line)]


def compute_hma(closes, period):
    """Hull Moving Average using WMA. Returns list same length as closes."""
    def wma(arr, n):
        out = [None] * len(arr)
        weights = list(range(1, n + 1))
        wsum = sum(weights)
        for i in range(n - 1, len(arr)):
            s = sum(arr[i - n + 1 + j] * weights[j] for j in range(n))
            out[i] = s / wsum
        return out

    half = max(period // 2, 1)
    sqrt_p = max(int(math.sqrt(period)), 1)

    wma_half = wma(closes, half)
    wma_full = wma(closes, period)

    diff = []
    for i in range(len(closes)):
        if wma_half[i] is not None and wma_full[i] is not None:
            diff.append(2.0 * wma_half[i] - wma_full[i])
        else:
            diff.append(closes[i])

    return wma(diff, sqrt_p)


# ===================================================================== #
#  Composite scoring (mirrors VelocityGainerStrategy logic)             #
# ===================================================================== #

# Weights (sum = 1.0)
W = {
    'rsi14_above50':      0.15,
    'rsi7_above50':       0.12,
    'volume_ratio':       0.12,
    'price_velocity':     0.15,
    'volume_acceleration': 0.12,
    'rsi14_rising':       0.08,
    'hma_slope':          0.06,
    'macd_hist':          0.06,
    'obv_slope':          0.06,
    'ema_stack':          0.08,
}

COMPOSITE_THRESHOLD = 0.55
VOLUME_RATIO_MIN = 1.5
VOLUME_AVG_PERIOD = 20
VELOCITY_1H_BARS = 1
VELOCITY_4H_BARS = 4
VOL_ACCEL_THRESHOLD = 0.5
ATR_EXPANSION_MULT = 1.3
DIST_FROM_LOW_ATR_MIN = 2.0
INSTITUTIONAL_VOL_MULT = 2.0


def score_symbol(candles):
    """Score a single symbol from its hourly candles.

    Args:
        candles: list of dicts with open/high/low/close/volume keys.

    Returns:
        dict with composite score, velocity metrics, sub-signals, etc.
        Returns None if insufficient data.
    """
    if not candles or len(candles) < 50:
        return None

    closes = [c['close'] for c in candles]
    highs = [c['high'] for c in candles]
    lows = [c['low'] for c in candles]
    volumes = [c['volume'] for c in candles]

    n = len(closes)
    i = n - 1  # current bar

    # Indicators
    rsi14 = compute_rsi(closes, 14)
    rsi7 = compute_rsi(closes, 7)
    hma9 = compute_hma(closes, 9)
    macd_hist = compute_macd_histogram(closes)
    obv = compute_obv(closes, volumes)
    atr = compute_atr(highs, lows, closes, 14)

    if atr[i] <= 0:
        return None

    ema9 = compute_ema(closes, 9)
    ema21 = compute_ema(closes, 21)
    ema50 = compute_ema(closes, 50)

    # --- Price Velocity ---
    v1h_bars = min(VELOCITY_1H_BARS, i)
    v4h_bars = min(VELOCITY_4H_BARS, i)

    if v1h_bars > 0 and closes[i - v1h_bars] > 0:
        velocity_1h = (closes[i] - closes[i - v1h_bars]) / closes[i - v1h_bars] * 100.0
    else:
        velocity_1h = 0.0

    if v4h_bars > 0 and closes[i - v4h_bars] > 0:
        velocity_4h = (closes[i] - closes[i - v4h_bars]) / closes[i - v4h_bars] * 100.0
    else:
        velocity_4h = velocity_1h

    normalized_4h = velocity_4h / max(v4h_bars / max(v1h_bars, 1), 1.0)
    acceleration = velocity_1h - normalized_4h

    # --- Volume Acceleration ---
    vol_avg_period = min(VOLUME_AVG_PERIOD, i)
    if vol_avg_period > 0 and i > 0:
        vol_avg = sum(volumes[i - vol_avg_period:i]) / vol_avg_period
    else:
        vol_avg = volumes[i]
    vol_velocity = volumes[i] / vol_avg if vol_avg > 0 else 1.0

    lookback_va = min(3, i)
    if lookback_va > 0 and i - lookback_va > vol_avg_period:
        prev_slice = volumes[i - lookback_va - vol_avg_period:i - lookback_va]
        vol_avg_prev = sum(prev_slice) / len(prev_slice) if prev_slice else vol_avg
        vol_velocity_prev = volumes[i - lookback_va] / vol_avg_prev if vol_avg_prev > 0 else 1.0
    else:
        vol_velocity_prev = vol_velocity
    vol_acceleration = vol_velocity - vol_velocity_prev

    # Volume ratio (same as vol_velocity but explicit)
    vol_ratio = vol_velocity

    # --- Composite score ---
    composite = 0.0
    signals_fired = []

    # 1. RSI(14) > 50
    if rsi14[i] > 50:
        composite += W['rsi14_above50']
        signals_fired.append("RSI14>50")

    # 2. RSI(7) > 50
    if rsi7[i] > 50:
        composite += W['rsi7_above50']
        signals_fired.append("RSI7>50")

    # 3. Volume ratio > 1.5
    if vol_ratio > VOLUME_RATIO_MIN:
        composite += W['volume_ratio']
        signals_fired.append(f"VolRatio={vol_ratio:.2f}")

    # 4. Price velocity > 0 AND acceleration > 0
    if velocity_1h > 0 and acceleration > 0:
        composite += W['price_velocity']
        signals_fired.append(f"Vel={velocity_1h:.2f}%")

    # 5. Volume acceleration > threshold
    if vol_acceleration > VOL_ACCEL_THRESHOLD:
        composite += W['volume_acceleration']
        signals_fired.append(f"VolAccel={vol_acceleration:.2f}")

    # 6. RSI(14) rising vs 3 bars ago
    lookback = min(3, i)
    if lookback > 0 and rsi14[i] > rsi14[i - lookback]:
        composite += W['rsi14_rising']
        signals_fired.append("RSI14_rising")

    # 7. HMA(9) slope positive
    if hma9[i] is not None and i > 0 and hma9[i - 1] is not None:
        if hma9[i] > hma9[i - 1]:
            composite += W['hma_slope']
            signals_fired.append("HMA9_up")

    # 8. MACD histogram positive
    if macd_hist[i] > 0:
        composite += W['macd_hist']
        signals_fired.append("MACD+")

    # 9. OBV slope positive
    obv_lb = min(3, i)
    if obv_lb > 0 and obv[i] > obv[i - obv_lb]:
        composite += W['obv_slope']
        signals_fired.append("OBV_up")

    # 10. EMA stack aligned: 9 > 21 > 50
    if ema9[i] > ema21[i] > ema50[i]:
        composite += W['ema_stack']
        signals_fired.append("EMA_stack")

    # --- Narrative rotation ---
    narrative = []
    # ATR expansion
    atr_lookback = min(20, i)
    if atr_lookback > 0:
        valid_atrs = [a for a in atr[i - atr_lookback:i] if a > 0]
        if valid_atrs:
            atr_avg = sum(valid_atrs) / len(valid_atrs)
            if atr_avg > 0 and atr[i] > atr_avg * ATR_EXPANSION_MULT:
                narrative.append("ATR_breakout")

    # Recovering from low
    low_lb = min(20, i)
    if low_lb > 0:
        recent_low = min(lows[i - low_lb:i + 1])
        dist_from_low = closes[i] - recent_low
        if atr[i] > 0 and dist_from_low / atr[i] > DIST_FROM_LOW_ATR_MIN:
            narrative.append("recovering")

    # Institutional volume
    if vol_ratio > INSTITUTIONAL_VOL_MULT:
        narrative.append("institutional_vol")

    # --- Confidence with acceleration boost ---
    accel_boost = min(max(acceleration, 0.0), 0.3)
    confidence = min(composite * (1.0 + accel_boost), 1.0)

    # --- TP/SL ---
    entry = closes[i]
    velocity_factor = min(abs(velocity_1h) / 5.0, 0.5)
    tp = entry + atr[i] * 2.5 * (1.0 + velocity_factor)
    sl = entry - atr[i] * 1.0

    return {
        'composite': round(composite, 4),
        'confidence': round(confidence, 4),
        'is_buy': composite >= COMPOSITE_THRESHOLD,
        'price': round(entry, 8),
        'velocity_1h': round(velocity_1h, 4),
        'velocity_4h': round(velocity_4h, 4),
        'acceleration': round(acceleration, 4),
        'vol_velocity': round(vol_velocity, 4),
        'vol_acceleration': round(vol_acceleration, 4),
        'vol_ratio': round(vol_ratio, 4),
        'rsi14': round(rsi14[i], 2),
        'rsi7': round(rsi7[i], 2),
        'atr': round(atr[i], 8),
        'signals_fired': signals_fired,
        'signals_count': len(signals_fired),
        'narrative': narrative,
        'tp': round(tp, 8),
        'sl': round(sl, 8),
        'rr_ratio': round((tp - entry) / (entry - sl), 2) if entry > sl else 0.0,
    }


# ===================================================================== #
#  Main CLI                                                             #
# ===================================================================== #

def run_scan(top_n=10, save=False, verbose=False):
    """Scan top Binance USDT pairs and rank by gainer prediction score."""
    print("=" * 70)
    print("  GAINER SCORING SERVICE — Velocity-Based Pump Predictor")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 70)

    # Step 1: Fetch all USDT tickers, pick top 50 by volume
    print("\n[1/3] Fetching Binance USDT tickers...")
    tickers = fetch_all_usdt_tickers()
    if not tickers:
        print("  ERROR: Could not fetch tickers from Binance or CoinGecko fallback.")
        sys.exit(1)
    print(f"  Found {len(tickers)} high-volume USDT pairs.")

    # Step 2: Fetch hourly klines and score each
    print(f"\n[2/3] Fetching 1h klines and scoring {len(tickers)} pairs...")
    results = []
    for idx, t in enumerate(tickers):
        sym = t['symbol']
        if verbose:
            print(f"  [{idx + 1}/{len(tickers)}] {sym}...", end=" ")

        candles = fetch_klines(sym, interval="1h", limit=100)
        if not candles:
            if verbose:
                print("SKIP (no data)")
            continue

        score = score_symbol(candles)
        if score is None:
            if verbose:
                print("SKIP (insufficient)")
            continue

        score['symbol'] = sym
        score['change_24h'] = t['change_pct']
        score['quote_volume_24h'] = t['quote_volume']
        results.append(score)

        if verbose:
            status = "BUY" if score['is_buy'] else "---"
            print(f"composite={score['composite']:.3f} vel={score['velocity_1h']:+.2f}% [{status}]")

        # Rate limit: Binance allows 1200 req/min; CoinGecko free ~30 req/min
        if _binance_klines_blocked:
            time.sleep(2.0)  # CoinGecko rate limit
        elif (idx + 1) % 10 == 0:
            time.sleep(0.5)

    print(f"  Scored {len(results)} pairs successfully.")

    # Step 3: Rank by composite score (descending)
    results.sort(key=lambda x: x['composite'], reverse=True)
    top = results[:top_n]

    # Display results
    print(f"\n[3/3] TOP {min(top_n, len(top))} — About to Pump Predictions")
    print("-" * 70)
    print(f"{'#':>2}  {'Symbol':<12} {'Score':>6} {'Conf':>6} {'Vel1h':>7} "
          f"{'Accel':>7} {'RSI14':>6} {'Sigs':>4}  {'Status':<5}  Signals")
    print("-" * 70)

    for rank, r in enumerate(top, 1):
        status = "BUY" if r['is_buy'] else "WAIT"
        sigs_str = ", ".join(r['signals_fired'][:5])
        if len(r['signals_fired']) > 5:
            sigs_str += f" +{len(r['signals_fired']) - 5}"
        print(
            f"{rank:>2}  {r['symbol']:<12} {r['composite']:>6.3f} {r['confidence']:>6.3f} "
            f"{r['velocity_1h']:>+7.2f}% {r['acceleration']:>+7.3f} "
            f"{r['rsi14']:>6.1f} {r['signals_count']:>4}  {status:<5}  {sigs_str}"
        )

    # Show buy signals specifically
    buys = [r for r in top if r['is_buy']]
    if buys:
        print(f"\n  ACTIVE BUY SIGNALS: {len(buys)}")
        for r in buys:
            narr = f" | Narrative: {', '.join(r['narrative'])}" if r['narrative'] else ""
            print(
                f"    {r['symbol']}: entry={r['price']:.8g} "
                f"TP={r['tp']:.8g} SL={r['sl']:.8g} "
                f"R:R={r['rr_ratio']:.1f}{narr}"
            )
    else:
        print("\n  No active BUY signals at this time.")

    # Save to JSON
    if save:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        output_path = DATA_DIR / "gainer_scores_latest.json"
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "threshold": COMPOSITE_THRESHOLD,
            "total_scanned": len(results),
            "buy_signals": len(buys),
            "top": top,
            "all_scores": results,
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        print(f"\n  Saved to {output_path}")

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Gainer Scoring Service - Velocity-Based Pump Predictor"
    )
    parser.add_argument("--top", type=int, default=10,
                        help="Number of top results to show (default: 10)")
    parser.add_argument("--save", action="store_true",
                        help="Save results to data/gainer_scores_latest.json")
    parser.add_argument("--verbose", action="store_true",
                        help="Show progress and sub-scores for each symbol")
    args = parser.parse_args()

    run_scan(top_n=args.top, save=args.save, verbose=args.verbose)


if __name__ == "__main__":
    main()
