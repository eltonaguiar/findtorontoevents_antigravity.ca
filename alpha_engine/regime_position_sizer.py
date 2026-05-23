#!/usr/bin/env python3
"""
Regime-Aware Position Sizer
============================
Detects BTC market regime from 4H price action and enforces directional
position limits per regime. Prevents the all-LONG-in-choppy-market mistake
that was the root cause of paper-trade losses.

Regimes:
  TRENDING_UP   -> max 6 LONG, 2 SHORT
  TRENDING_DOWN -> max 2 LONG, 6 SHORT
  CHOPPY        -> max 3 LONG, 3 SHORT  (force balance)
  VOLATILE      -> max 2 LONG, 2 SHORT  (reduce exposure)

Uses Binance 4H klines with 3+ mirror failover (API Failover Rule).
"""

from __future__ import annotations

import json
import math
import os
import ssl
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# -- Windows UTF-8 fix --
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent / "data"
REGIME_REPORT_PATH = DATA_DIR / "regime_position_sizing.json"

# 3+ API failover chain (NEVER use single Binance API)
BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]
COINGECKO_BTC_URL = "https://api.coingecko.com/api/v3/coins/bitcoin/ohlc?vs_currency=usd&days=14"
KUCOIN_BTC_URL = "https://api.kucoin.com/api/v1/market/candles?type=4hour&symbol=BTC-USDT"
CRYPTOCOMPARE_BTC_URL = "https://min-api.cryptocompare.com/data/v2/histohour?fsym=BTC&tsym=USD&limit=200&aggregate=4"

SYMBOL = "BTCUSDT"
INTERVAL = "4h"
CANDLE_COUNT = 50

# Regime position limits: (max_long, max_short)
REGIME_LIMITS = {
    "TRENDING_UP":   (6, 2),
    "TRENDING_DOWN": (2, 6),
    "CHOPPY":        (3, 3),
    "VOLATILE":      (2, 2),
}

REGIME_RECOMMENDATIONS = {
    "TRENDING_UP":   "Favor long positions. Ride the trend with trailing stops.",
    "TRENDING_DOWN": "Favor short positions. Tighten long stop-losses.",
    "CHOPPY":        "Balance long/short exposure. Reduce position sizes.",
    "VOLATILE":      "Reduce total exposure. Widen stops or sit out.",
}

# SSL context
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


# ---------------------------------------------------------------------------
# BTC kline fetcher with 3+ failover
# ---------------------------------------------------------------------------

def _http_get_json(url: str, timeout: int = 15) -> list | dict | None:
    """GET JSON from a URL, return parsed data or None on failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=_ssl_ctx, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def fetch_btc_4h_klines(limit: int = CANDLE_COUNT) -> list[dict] | None:
    """
    Fetch BTC 4H klines with Binance mirror failover + CoinGecko + KuCoin
    + CryptoCompare fallback chain.

    Returns list of dicts with keys: open, high, low, close, volume
    or None if all sources fail.
    """

    # --- Attempt 1: Binance mirrors ---
    for mirror in BINANCE_MIRRORS:
        url = f"{mirror}/api/v3/klines?symbol={SYMBOL}&interval={INTERVAL}&limit={limit}"
        data = _http_get_json(url)
        if data and isinstance(data, list) and len(data) >= 20:
            candles = []
            for k in data:
                candles.append({
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                })
            print(f"[regime_sizer] Fetched {len(candles)} candles from {mirror}")
            return candles

    # --- Attempt 2: CoinGecko OHLC (free, no key) ---
    data = _http_get_json(COINGECKO_BTC_URL)
    if data and isinstance(data, list) and len(data) >= 20:
        candles = []
        for row in data:
            # CoinGecko OHLC: [timestamp, open, high, low, close]
            candles.append({
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": 0.0,
            })
        print(f"[regime_sizer] Fetched {len(candles)} candles from CoinGecko")
        return candles[-limit:]

    # --- Attempt 3: KuCoin ---
    data = _http_get_json(KUCOIN_BTC_URL)
    if data and isinstance(data, dict) and data.get("data"):
        raw = data["data"]
        candles = []
        for row in raw:
            # KuCoin: [time, open, close, high, low, volume, turnover]
            candles.append({
                "open": float(row[1]),
                "high": float(row[3]),
                "low": float(row[4]),
                "close": float(row[2]),
                "volume": float(row[5]),
            })
        candles.reverse()  # KuCoin returns newest first
        print(f"[regime_sizer] Fetched {len(candles)} candles from KuCoin")
        return candles[-limit:]

    # --- Attempt 4: CryptoCompare ---
    data = _http_get_json(CRYPTOCOMPARE_BTC_URL)
    if data and isinstance(data, dict):
        raw = data.get("Data", {}).get("Data", [])
        if raw and len(raw) >= 20:
            candles = []
            for row in raw:
                candles.append({
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row.get("volumefrom", 0)),
                })
            print(f"[regime_sizer] Fetched {len(candles)} candles from CryptoCompare")
            return candles[-limit:]

    print("[regime_sizer] ERROR: All API sources failed for BTC 4H klines")
    return None


# ---------------------------------------------------------------------------
# Technical indicators (pure math, no dependencies)
# ---------------------------------------------------------------------------

def _rsi(closes: list[float], period: int = 14) -> float:
    """Calculate RSI from close prices."""
    if len(closes) < period + 1:
        return 50.0  # neutral fallback

    gains = []
    losses = []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))

    # Use exponential moving average (Wilder's smoothing)
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _sma(values: list[float], period: int) -> list[float]:
    """Simple moving average."""
    result = []
    for i in range(len(values)):
        if i < period - 1:
            result.append(None)
        else:
            window = values[i - period + 1: i + 1]
            result.append(sum(window) / period)
    return result


def _atr(candles: list[dict], period: int = 14) -> float:
    """Average True Range."""
    if len(candles) < period + 1:
        return 0.0

    trs = []
    for i in range(1, len(candles)):
        h = candles[i]["high"]
        l = candles[i]["low"]
        pc = candles[i - 1]["close"]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)

    if len(trs) < period:
        return sum(trs) / max(len(trs), 1)

    atr_val = sum(trs[:period]) / period
    for i in range(period, len(trs)):
        atr_val = (atr_val * (period - 1) + trs[i]) / period
    return atr_val


def _sma_slope(sma_values: list[float | None], lookback: int = 5) -> float:
    """
    Calculate slope of SMA over last `lookback` values.
    Returns percentage slope (positive = uptrend, negative = downtrend).
    """
    valid = [v for v in sma_values if v is not None]
    if len(valid) < lookback:
        return 0.0
    recent = valid[-lookback:]
    if recent[0] == 0:
        return 0.0
    return (recent[-1] - recent[0]) / recent[0] * 100.0


# ---------------------------------------------------------------------------
# Regime classification
# ---------------------------------------------------------------------------

def classify_regime(candles: list[dict]) -> dict:
    """
    Classify market regime from BTC 4H candles.

    Returns dict with:
      regime, btc_rsi, btc_trend, sma_slope, volatility_pct,
      max_long, max_short, recommendation
    """
    closes = [c["close"] for c in candles]
    current_price = closes[-1]

    # Indicators
    rsi = _rsi(closes, 14)
    sma20 = _sma(closes, 20)
    slope = _sma_slope(sma20, lookback=5)
    atr_val = _atr(candles, 14)
    volatility_pct = (atr_val / current_price * 100.0) if current_price > 0 else 0.0

    # Trend direction from SMA slope
    if slope > 0.5:
        trend = "UP"
    elif slope < -0.5:
        trend = "DOWN"
    else:
        trend = "FLAT"

    # --- Regime decision logic ---
    # High volatility overrides everything
    if volatility_pct > 3.0:
        regime = "VOLATILE"
    # Strong trend signals
    elif trend == "UP" and rsi > 45:
        regime = "TRENDING_UP"
    elif trend == "DOWN" and rsi < 55:
        regime = "TRENDING_DOWN"
    # RSI extremes can indicate trend even with flat SMA
    elif rsi > 65 and slope > 0.0:
        regime = "TRENDING_UP"
    elif rsi < 35 and slope < 0.0:
        regime = "TRENDING_DOWN"
    # Default: choppy / range-bound
    else:
        regime = "CHOPPY"

    max_long, max_short = REGIME_LIMITS[regime]
    recommendation = REGIME_RECOMMENDATIONS[regime]

    return {
        "regime": regime,
        "btc_rsi": round(rsi, 1),
        "btc_trend": trend,
        "sma_slope": round(slope, 3),
        "volatility_pct": round(volatility_pct, 3),
        "btc_price": round(current_price, 2),
        "atr": round(atr_val, 2),
        "max_long": max_long,
        "max_short": max_short,
        "recommendation": recommendation,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_cached_regime: dict | None = None
_cache_ts: float = 0.0
_CACHE_TTL = 300.0  # 5 minutes


def get_regime() -> str:
    """Return current regime string (e.g. 'CHOPPY'). Loads from cache or report file."""
    global _cached_regime, _cache_ts

    now = time.time()
    if _cached_regime and (now - _cache_ts) < _CACHE_TTL:
        return _cached_regime["regime"]

    # Try loading from report file
    if REGIME_REPORT_PATH.exists():
        try:
            with open(REGIME_REPORT_PATH, "r", encoding="utf-8") as f:
                report = json.load(f)
            _cached_regime = report
            _cache_ts = now
            return report.get("regime", "CHOPPY")
        except Exception:
            pass

    return "CHOPPY"  # safe default


def check_position_allowed(
    direction: str,
    current_longs: int,
    current_shorts: int,
) -> bool:
    """
    Check if a new position in the given direction is allowed under the
    current regime's position limits.

    Args:
        direction: "LONG" or "SHORT" (case-insensitive)
        current_longs: number of currently open long positions
        current_shorts: number of currently open short positions

    Returns:
        True if the position is allowed, False if it would exceed regime limits.
    """
    regime = get_regime()
    max_long, max_short = REGIME_LIMITS.get(regime, (3, 3))

    d = direction.upper().strip()
    if d == "LONG":
        allowed = current_longs < max_long
        if not allowed:
            print(
                f"[regime_sizer] BLOCKED: LONG rejected. "
                f"Regime={regime}, current_longs={current_longs}, max_long={max_long}"
            )
        return allowed
    elif d == "SHORT":
        allowed = current_shorts < max_short
        if not allowed:
            print(
                f"[regime_sizer] BLOCKED: SHORT rejected. "
                f"Regime={regime}, current_shorts={current_shorts}, max_short={max_short}"
            )
        return allowed
    else:
        print(f"[regime_sizer] WARNING: Unknown direction '{direction}', defaulting to blocked")
        return False


def run() -> dict:
    """
    Main entry point: fetch BTC data, classify regime, save report.
    Returns the regime report dict.
    """
    global _cached_regime, _cache_ts

    print("[regime_sizer] Fetching BTC 4H klines...")
    candles = fetch_btc_4h_klines(limit=CANDLE_COUNT)

    if candles is None or len(candles) < 20:
        print("[regime_sizer] Insufficient data, defaulting to CHOPPY regime")
        report = {
            "regime": "CHOPPY",
            "btc_rsi": 50.0,
            "btc_trend": "FLAT",
            "sma_slope": 0.0,
            "volatility_pct": 0.0,
            "btc_price": 0.0,
            "atr": 0.0,
            "max_long": 3,
            "max_short": 3,
            "recommendation": REGIME_RECOMMENDATIONS["CHOPPY"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data_source": "FALLBACK",
        }
    else:
        report = classify_regime(candles)
        report["timestamp"] = datetime.now(timezone.utc).isoformat()
        report["candle_count"] = len(candles)

    # Save report
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(REGIME_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Update cache
    _cached_regime = report
    _cache_ts = time.time()

    print(f"[regime_sizer] Regime: {report['regime']}")
    print(f"  BTC RSI: {report['btc_rsi']}, Trend: {report['btc_trend']}, "
          f"Volatility: {report.get('volatility_pct', 0)}%")
    print(f"  Max LONG: {report['max_long']}, Max SHORT: {report['max_short']}")
    print(f"  -> {report['recommendation']}")
    print(f"  Report saved to {REGIME_REPORT_PATH}")

    return report


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    report = run()
    print(json.dumps(report, indent=2))
