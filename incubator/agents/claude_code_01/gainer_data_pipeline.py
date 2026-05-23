"""
Gainer Data Pipeline — Crypto Pump Early Warning System
=======================================================
Fetches top gainers from Binance, screens for early-warning signals,
outputs potential pump candidates.

Designed to run every 30 minutes via GitHub Actions.
"""

import json
import sys
import os
import math
import time
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Binance endpoints to try (primary + mirrors + data-api)
BINANCE_ENDPOINTS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://api4.binance.com",
    "https://data-api.binance.vision",
]

# Track whether Binance is geo-blocked so we skip it for subsequent calls
_binance_blocked = False


def fetch_json(url, retries=2):
    """Fetch JSON from URL with retries."""
    req = Request(url, headers={"User-Agent": "GainerDataPipeline/1.0"})
    for attempt in range(retries + 1):
        try:
            with urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except HTTPError as e:
            if e.code in (451, 403):
                print(f"  [WARN] Geo-blocked (HTTP {e.code}): {url}")
                return None
            if attempt < retries:
                time.sleep(1)
                continue
            print(f"  [WARN] HTTP {e.code} after {retries + 1} attempts: {url}")
            return None
        except (URLError, Exception) as e:
            if attempt < retries:
                time.sleep(1)
                continue
            print(f"  [WARN] Fetch failed after {retries + 1} attempts: {url} - {e}")
            return None


def fetch_binance_json(path):
    """Try fetching a Binance API path across all mirror endpoints.
    Returns data on success, None if all endpoints fail (sets _binance_blocked).
    """
    global _binance_blocked
    if _binance_blocked:
        return None
    for base in BINANCE_ENDPOINTS:
        url = f"{base}{path}"
        data = fetch_json(url, retries=1)
        if data is not None:
            return data
    print("  [WARN] All Binance endpoints failed — marking as geo-blocked for this run.")
    _binance_blocked = True
    return None


def get_binance_gainers(top_n=30):
    """Get top N USDT gainers by 24h price change.
    Falls back to CoinGecko if Binance is geo-blocked (HTTP 451/403).
    """
    data = fetch_binance_json("/api/v3/ticker/24hr")
    if data:
        usdt = [d for d in data if d["symbol"].endswith("USDT")
                and float(d.get("quoteVolume", 0)) > 50000
                and not d["symbol"].startswith("USD")]
        usdt.sort(key=lambda x: float(x["priceChangePercent"]), reverse=True)
        return [{
            "symbol": d["symbol"],
            "change_24h": float(d["priceChangePercent"]),
            "volume": float(d["quoteVolume"]),
            "price": float(d["lastPrice"]),
            "high_24h": float(d["highPrice"]),
            "low_24h": float(d["lowPrice"]),
            "trades": int(d["count"]),
        } for d in usdt[:top_n]]

    # --- CoinGecko fallback ---
    print("  [INFO] Using CoinGecko fallback for gainers...")
    cg = fetch_json(
        "https://api.coingecko.com/api/v3/coins/markets"
        "?vs_currency=usd&order=market_cap_desc&per_page=100&page=1"
        "&sparkline=false&price_change_percentage=24h",
        retries=2,
    )
    if not cg:
        print("  [ERROR] CoinGecko fallback also failed.")
        return []
    # Sort by 24h change descending to mimic "gainers"
    cg.sort(key=lambda c: float(c.get("price_change_percentage_24h_in_currency", 0) or
                                 c.get("price_change_percentage_24h", 0) or 0), reverse=True)
    results = []
    for c in cg[:top_n]:
        sym_raw = (c.get("symbol") or "").upper()
        change = float(c.get("price_change_percentage_24h", 0) or 0)
        price = float(c.get("current_price", 0) or 0)
        high = float(c.get("high_24h", 0) or 0)
        low = float(c.get("low_24h", 0) or 0)
        vol = float(c.get("total_volume", 0) or 0)
        if price <= 0:
            continue
        results.append({
            "symbol": sym_raw + "USDT",
            "change_24h": change,
            "volume": vol,
            "price": price,
            "high_24h": high,
            "low_24h": low,
            "trades": 0,  # CoinGecko doesn't provide trade count
        })
    print(f"  [INFO] CoinGecko returned {len(results)} gainers.")
    return results


def get_1h_movers(top_n=20):
    """Approximate 1h movers using Binance klines.
    Falls back to CoinGecko 1h price change if Binance is geo-blocked.
    """
    # Try Binance first
    tickers = fetch_binance_json("/api/v3/ticker/price")
    if tickers:
        usdt_tickers = {t["symbol"]: float(t["price"]) for t in tickers
                        if t["symbol"].endswith("USDT") and not t["symbol"].startswith("USD")}

        movers = []
        symbols = list(usdt_tickers.keys())[:200]

        for sym in symbols:
            klines = fetch_binance_json(f"/api/v3/klines?symbol={sym}&interval=1h&limit=2")
            if klines and len(klines) >= 2:
                open_1h = float(klines[-1][1])
                close_1h = float(klines[-1][4])
                vol_1h = float(klines[-1][5])
                if open_1h > 0:
                    change = (close_1h - open_1h) / open_1h * 100
                    movers.append({
                        "symbol": sym,
                        "change_1h": round(change, 2),
                        "volume_1h": vol_1h,
                        "price": close_1h,
                    })
            # If Binance got blocked mid-loop, break out
            if _binance_blocked:
                break

        if movers:
            movers.sort(key=lambda x: x["change_1h"], reverse=True)
            return movers[:top_n]

    # --- CoinGecko fallback for 1h movers ---
    print("  [INFO] Using CoinGecko fallback for 1h movers...")
    cg = fetch_json(
        "https://api.coingecko.com/api/v3/coins/markets"
        "?vs_currency=usd&order=volume_desc&per_page=50&page=1"
        "&sparkline=false&price_change_percentage=1h",
        retries=2,
    )
    if not cg:
        print("  [WARN] CoinGecko 1h movers fallback failed.")
        return []
    movers = []
    for c in cg:
        change_1h = float(c.get("price_change_percentage_1h_in_currency", 0) or 0)
        price = float(c.get("current_price", 0) or 0)
        vol = float(c.get("total_volume", 0) or 0)
        sym = (c.get("symbol") or "").upper()
        if price > 0:
            movers.append({
                "symbol": sym + "USDT",
                "change_1h": round(change_1h, 2),
                "volume_1h": vol,
                "price": price,
            })
    movers.sort(key=lambda x: x["change_1h"], reverse=True)
    return movers[:top_n]


def compute_rsi(closes, period=14):
    """Simple RSI calculation without numpy."""
    if len(closes) < period + 1:
        return 50.0
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))

    if len(gains) < period:
        return 50.0

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def compute_volume_ratio(volumes, period=20):
    """Current volume vs average."""
    if len(volumes) < period:
        return 1.0
    avg = sum(volumes[-period:]) / period
    return volumes[-1] / avg if avg > 0 else 1.0


def screen_for_early_signals(symbol):
    """Screen a symbol for proven early-warning signals.

    Returns a score 0-1 based on:
    - RSI(14) > 50: weight 0.20
    - RSI(7) > 50: weight 0.18
    - Volume ratio > 1.5: weight 0.17
    - RSI(2) > 50: weight 0.12
    - RSI(14) rising: weight 0.10
    - Volume > 2x avg: weight 0.08 (bonus)
    - Price above 20-period avg: weight 0.15
    """
    klines = fetch_binance_json(f"/api/v3/klines?symbol={symbol}&interval=1h&limit=50")
    if not klines or len(klines) < 30:
        return None  # Will be None when Binance is geo-blocked; caller handles this

    closes = [float(k[4]) for k in klines]
    volumes = [float(k[5]) for k in klines]

    score = 0.0
    reasons = []

    # RSI(14) > 50
    rsi14 = compute_rsi(closes, 14)
    if rsi14 > 50:
        score += 0.20
        reasons.append(f"RSI14={rsi14:.0f}>50")

    # RSI(7) > 50
    rsi7 = compute_rsi(closes, 7)
    if rsi7 > 50:
        score += 0.18
        reasons.append(f"RSI7={rsi7:.0f}>50")

    # Volume ratio > 1.5
    vol_ratio = compute_volume_ratio(volumes, 20)
    if vol_ratio > 1.5:
        score += 0.17
        reasons.append(f"VolRatio={vol_ratio:.1f}")

    # RSI(2) > 50
    rsi2 = compute_rsi(closes, 2)
    if rsi2 > 50:
        score += 0.12
        reasons.append(f"RSI2={rsi2:.0f}>50")

    # RSI(14) rising
    closes_3ago = closes[:-3] if len(closes) > 3 else closes
    rsi14_prev = compute_rsi(closes_3ago, 14)
    if rsi14 > rsi14_prev:
        score += 0.10
        reasons.append("RSI14_rising")

    # Volume > 2x avg (bonus)
    if vol_ratio > 2.0:
        score += 0.08
        reasons.append(f"VolSpike={vol_ratio:.1f}x")

    # Price above 20-bar avg
    if len(closes) >= 20:
        avg_20 = sum(closes[-20:]) / 20
        if closes[-1] > avg_20:
            score += 0.15
            reasons.append("Above_SMA20")

    return {
        "symbol": symbol,
        "score": round(score, 3),
        "rsi14": round(rsi14, 1),
        "rsi7": round(rsi7, 1),
        "rsi2": round(rsi2, 1),
        "vol_ratio": round(vol_ratio, 2),
        "price": closes[-1],
        "reasons": reasons,
    }


def main():
    print(f"\n{'='*60}")
    print(f"GAINER DATA PIPELINE — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")

    # 1. Fetch 24h gainers
    print("\n[1] Top 24h Gainers from Binance...")
    gainers_24h = get_binance_gainers(30)
    print(f"   Found {len(gainers_24h)} gainers")
    for g in gainers_24h[:5]:
        print(f"   {g['symbol']}: +{g['change_24h']:.1f}%")

    # 2. Screen each for early signals
    print("\n[2] Screening for early-warning signals...")
    screened = []
    for g in gainers_24h:
        result = screen_for_early_signals(g["symbol"])
        if result:
            result["change_24h"] = g["change_24h"]
            result["volume_24h"] = g["volume"]
            screened.append(result)
            if result["score"] >= 0.6:
                print(f"   HIGH SCORE {g['symbol']}: {result['score']:.2f} — {', '.join(result['reasons'])}")

    # If Binance klines were geo-blocked, build basic scores from CoinGecko gainer data
    if not screened and gainers_24h:
        print("  [INFO] Binance klines unavailable — building basic scores from gainer data...")
        for g in gainers_24h:
            # Simple heuristic score based on 24h change and volume
            change = g.get("change_24h", 0)
            vol = g.get("volume", 0)
            price = g.get("price", 0)
            high = g.get("high_24h", 0)
            low = g.get("low_24h", 0)

            score = 0.0
            reasons = []
            if change > 5:
                score += 0.25
                reasons.append(f"24h_gain={change:.1f}%")
            elif change > 0:
                score += 0.10
                reasons.append(f"24h_positive={change:.1f}%")
            if vol > 1_000_000:
                score += 0.20
                reasons.append("high_volume")
            if high > 0 and low > 0 and price > 0:
                # Price near high = bullish
                range_pos = (price - low) / (high - low) if high != low else 0.5
                if range_pos > 0.7:
                    score += 0.15
                    reasons.append(f"near_high={range_pos:.0%}")

            screened.append({
                "symbol": g["symbol"],
                "score": round(score, 3),
                "rsi14": 0.0,
                "rsi7": 0.0,
                "rsi2": 0.0,
                "vol_ratio": 0.0,
                "price": price,
                "reasons": reasons,
                "change_24h": change,
                "volume_24h": vol,
                "source": "coingecko_fallback",
            })
        print(f"  [INFO] Built {len(screened)} basic-scored entries from CoinGecko data.")

    # 3. Rank by predictive score
    screened.sort(key=lambda x: x["score"], reverse=True)

    print(f"\n[3] Top scored symbols (score >= 0.5):")
    for s in screened:
        if s["score"] >= 0.5:
            print(f"   {s['symbol']:<12} Score:{s['score']:.2f}  RSI14:{s['rsi14']:>5.1f}  RSI7:{s['rsi7']:>5.1f}  Vol:{s['vol_ratio']:>5.1f}x  24h:{s['change_24h']:>+6.1f}%")

    # 4. Save results
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gainers_24h": gainers_24h,
        "screened_signals": screened,
        "high_score_candidates": [s for s in screened if s["score"] >= 0.6],
    }

    output_file = DATA_DIR / "gainer_pipeline_latest.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    # Also save to a timestamped file for history
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    history_file = DATA_DIR / f"gainer_scan_{ts}.json"
    with open(history_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n   Saved to: {output_file}")
    print(f"   History: {history_file}")
    print(f"   High-score candidates: {len([s for s in screened if s['score'] >= 0.6])}")

    print(f"\n{'='*60}")
    print("PIPELINE COMPLETE")
    print(f"{'='*60}")

    return output


if __name__ == "__main__":
    main()
