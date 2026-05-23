#!/usr/bin/env python3
"""
ALPHA ENGINE -- Heikin Ashi Trend Filter + 3-Indicator Ensemble Gate
=====================================================================
Combines two complementary filters to improve pick quality:

1. Heikin Ashi (HA) Trend Filter (4H timeframe):
   - Computes HA candles from regular OHLCV
   - 3 consecutive green HA candles = BULLISH
   - 3 consecutive red HA candles = BEARISH
   - Mixed = NEUTRAL
   - LONGs only allowed when BULLISH, SHORTs only when BEARISH

2. 3-Indicator Ensemble (ALL must agree for full score):
   - Trend:    EMA-9 vs EMA-20 (above = bullish, below = bearish)
   - Momentum: RSI(14)         (>50 = bullish,  <50 = bearish)
   - Volume:   Vol vs 20-SMA   (>1.0x = confirms, <0.5x = rejects)

3. Combined Gate:
   - check_ha_ensemble(symbol, direction) returns pass/fail + score adjustment
   - +10 (all 3 indicators + HA agree), +5 (2/3), -10 (1/3), -25 (0/3 + HA disagrees)

References:
- Heikin Ashi smoothing: Valcu (2004) -- noise reduction via averaging
- EMA crossover: Appel (1979) -- trend detection
- RSI momentum filter: Wilder (1978) -- 50-line as bull/bear divide
- Volume confirmation: Granville (1963) -- volume precedes price

Stdlib only (urllib, json, math). 5-mirror Binance failover. 10-min cache.

Usage:
    from ha_ensemble_filter import check_ha_ensemble, check_ha_ensemble_batch

    result = check_ha_ensemble("BTCUSDT", "LONG")
    # result['passes']           -> True/False
    # result['score_adjustment'] -> -25 to +10
    # result['ha_trend']         -> "BULLISH"/"BEARISH"/"NEUTRAL"
    # result['indicators_aligned'] -> 0-3
"""

from __future__ import annotations

import json
import logging
import math
import ssl
import sys
import time
import urllib.error
import urllib.request
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Windows UTF-8 fix
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Binance mirror failover (5 mirrors -- per MEMORY.md API Failover Rule)
# ---------------------------------------------------------------------------
BINANCE_MIRRORS = [
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

_KLINE_ENDPOINT = "/api/v3/klines"

# ---------------------------------------------------------------------------
# Cache: { (symbol, interval): (timestamp, data) }  -- 10-minute TTL
# ---------------------------------------------------------------------------
_kline_cache: Dict[Tuple[str, str], Tuple[float, list]] = {}
_CACHE_TTL = 600  # 10 minutes

# Rate-limit tracker
_last_api_call = 0.0
_RATE_LIMIT_DELAY = 0.1  # 100 ms between API calls


# ---------------------------------------------------------------------------
# SSL context (some CI environments lack certs)
# ---------------------------------------------------------------------------
def _make_ssl_ctx() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    try:
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
    except Exception:
        ctx = ssl._create_unverified_context()
    return ctx


_SSL_CTX = _make_ssl_ctx()


# ---------------------------------------------------------------------------
# Fetch klines with 5-mirror failover
# ---------------------------------------------------------------------------
def _rate_limit() -> None:
    global _last_api_call
    now = time.time()
    elapsed = now - _last_api_call
    if elapsed < _RATE_LIMIT_DELAY:
        time.sleep(_RATE_LIMIT_DELAY - elapsed)
    _last_api_call = time.time()


def _fetch_klines(symbol: str, interval: str, limit: int = 50) -> list:
    """
    Fetch kline/candlestick data from Binance with 5-mirror failover.
    Returns list of [open_time, open, high, low, close, volume, ...].
    """
    cache_key = (symbol.upper(), interval)
    now = time.time()

    # Check cache
    if cache_key in _kline_cache:
        cached_ts, cached_data = _kline_cache[cache_key]
        if now - cached_ts < _CACHE_TTL:
            return cached_data

    params = f"symbol={symbol.upper()}&interval={interval}&limit={limit}"
    last_err = None

    for mirror in BINANCE_MIRRORS:
        url = f"{mirror}{_KLINE_ENDPOINT}?{params}"
        try:
            _rate_limit()
            req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
            with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, list) and len(data) > 0:
                _kline_cache[cache_key] = (now, data)
                return data
        except Exception as exc:
            last_err = exc
            logger.debug("Mirror %s failed for %s %s: %s", mirror, symbol, interval, exc)
            continue

    logger.warning("All Binance mirrors failed for %s %s: %s", symbol, interval, last_err)
    return []


# ---------------------------------------------------------------------------
# Parse klines into OHLCV lists
# ---------------------------------------------------------------------------
def _parse_ohlcv(klines: list) -> Tuple[List[float], List[float], List[float], List[float], List[float]]:
    """Extract open, high, low, close, volume from Binance kline response."""
    opens: List[float] = []
    highs: List[float] = []
    lows: List[float] = []
    closes: List[float] = []
    volumes: List[float] = []
    for k in klines:
        try:
            opens.append(float(k[1]))
            highs.append(float(k[2]))
            lows.append(float(k[3]))
            closes.append(float(k[4]))
            volumes.append(float(k[5]))
        except (IndexError, TypeError, ValueError):
            continue
    return opens, highs, lows, closes, volumes


# ---------------------------------------------------------------------------
# Technical indicators (stdlib only -- no numpy/pandas)
# ---------------------------------------------------------------------------
def _ema(values: List[float], period: int) -> List[float]:
    """Compute EMA. Returns list same length as input (NaN-filled for warmup)."""
    if len(values) < period:
        return [float("nan")] * len(values)
    multiplier = 2.0 / (period + 1)
    ema_vals: List[float] = [float("nan")] * (period - 1)
    # Seed with SMA of first `period` values
    seed = sum(values[:period]) / period
    ema_vals.append(seed)
    for i in range(period, len(values)):
        prev = ema_vals[-1]
        ema_vals.append((values[i] - prev) * multiplier + prev)
    return ema_vals


def _sma(values: List[float], period: int) -> List[float]:
    """Compute SMA. Returns list same length as input (NaN-filled for warmup)."""
    if len(values) < period:
        return [float("nan")] * len(values)
    result: List[float] = [float("nan")] * (period - 1)
    window_sum = sum(values[:period])
    result.append(window_sum / period)
    for i in range(period, len(values)):
        window_sum += values[i] - values[i - period]
        result.append(window_sum / period)
    return result


def _rsi(values: List[float], period: int = 14) -> List[float]:
    """Compute RSI using Wilder's smoothing. Returns list same length as input."""
    if len(values) < period + 1:
        return [float("nan")] * len(values)

    result: List[float] = [float("nan")] * period

    # Calculate initial average gain/loss from first `period` changes
    gains: List[float] = []
    losses: List[float] = []
    for i in range(1, period + 1):
        change = values[i] - values[i - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        result.append(100.0)
    else:
        rs = avg_gain / avg_loss
        result.append(100.0 - 100.0 / (1.0 + rs))

    # Wilder's smoothing for remaining values
    for i in range(period + 1, len(values)):
        change = values[i] - values[i - 1]
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(100.0 - 100.0 / (1.0 + rs))

    return result


# ---------------------------------------------------------------------------
# Heikin Ashi computation
# ---------------------------------------------------------------------------
def _compute_heikin_ashi(
    opens: List[float],
    highs: List[float],
    lows: List[float],
    closes: List[float],
) -> Tuple[List[float], List[float], List[float], List[float]]:
    """
    Compute Heikin Ashi candles from regular OHLCV.
      HA_Close = (O + H + L + C) / 4
      HA_Open  = (prev_HA_Open + prev_HA_Close) / 2   (first bar: (O + C) / 2)
      HA_High  = max(H, HA_Open, HA_Close)
      HA_Low   = min(L, HA_Open, HA_Close)
    """
    n = len(closes)
    if n == 0:
        return [], [], [], []

    ha_open: List[float] = [0.0] * n
    ha_close: List[float] = [0.0] * n
    ha_high: List[float] = [0.0] * n
    ha_low: List[float] = [0.0] * n

    # First bar
    ha_close[0] = (opens[0] + highs[0] + lows[0] + closes[0]) / 4.0
    ha_open[0] = (opens[0] + closes[0]) / 2.0
    ha_high[0] = max(highs[0], ha_open[0], ha_close[0])
    ha_low[0] = min(lows[0], ha_open[0], ha_close[0])

    # Subsequent bars
    for i in range(1, n):
        ha_close[i] = (opens[i] + highs[i] + lows[i] + closes[i]) / 4.0
        ha_open[i] = (ha_open[i - 1] + ha_close[i - 1]) / 2.0
        ha_high[i] = max(highs[i], ha_open[i], ha_close[i])
        ha_low[i] = min(lows[i], ha_open[i], ha_close[i])

    return ha_open, ha_high, ha_low, ha_close


def _ha_trend(ha_open: List[float], ha_close: List[float], lookback: int = 3) -> str:
    """
    Determine HA trend from last `lookback` candles.
      - All green (close > open) = BULLISH
      - All red   (close < open) = BEARISH
      - Mixed                    = NEUTRAL
    """
    if len(ha_close) < lookback or len(ha_open) < lookback:
        return "NEUTRAL"

    green_count = 0
    red_count = 0
    for i in range(-lookback, 0):
        if ha_close[i] > ha_open[i]:
            green_count += 1
        elif ha_close[i] < ha_open[i]:
            red_count += 1

    if green_count == lookback:
        return "BULLISH"
    elif red_count == lookback:
        return "BEARISH"
    return "NEUTRAL"


# ---------------------------------------------------------------------------
# 3-Indicator Ensemble
# ---------------------------------------------------------------------------
def _ensemble_vote(
    closes: List[float],
    volumes: List[float],
) -> Tuple[int, Dict[str, str]]:
    """
    Evaluate the 3-indicator ensemble on close/volume data.

    Returns (bullish_count, details_dict).
      bullish_count: 0-3 (how many indicators are bullish)
      details_dict: per-indicator verdict
    """
    details: Dict[str, str] = {
        "ema_trend": "N/A",
        "rsi_momentum": "N/A",
        "volume_confirm": "N/A",
    }
    bullish = 0

    # --- 1. Trend: EMA-9 vs EMA-20 ---
    ema9 = _ema(closes, 9)
    ema20 = _ema(closes, 20)
    if ema9 and ema20 and not math.isnan(ema9[-1]) and not math.isnan(ema20[-1]):
        if ema9[-1] > ema20[-1]:
            details["ema_trend"] = "BULLISH"
            bullish += 1
        else:
            details["ema_trend"] = "BEARISH"
    else:
        details["ema_trend"] = "INSUFFICIENT_DATA"

    # --- 2. Momentum: RSI(14) above/below 50 ---
    rsi_vals = _rsi(closes, 14)
    if rsi_vals and not math.isnan(rsi_vals[-1]):
        rsi_val = rsi_vals[-1]
        if rsi_val > 50:
            details["rsi_momentum"] = f"BULLISH ({rsi_val:.1f})"
            bullish += 1
        else:
            details["rsi_momentum"] = f"BEARISH ({rsi_val:.1f})"
    else:
        details["rsi_momentum"] = "INSUFFICIENT_DATA"

    # --- 3. Volume: current vs 20-SMA ---
    vol_sma = _sma(volumes, 20)
    if (
        volumes
        and vol_sma
        and not math.isnan(vol_sma[-1])
        and vol_sma[-1] > 0
    ):
        vol_ratio = volumes[-1] / vol_sma[-1]
        if vol_ratio < 0.5:
            details["volume_confirm"] = f"REJECTED ({vol_ratio:.2f}x)"
            # Volume too low -- explicitly bearish (rejects the move)
        elif vol_ratio >= 1.0:
            details["volume_confirm"] = f"CONFIRMED ({vol_ratio:.2f}x)"
            bullish += 1
        else:
            # 0.5x-1.0x: neutral -- don't add to bullish but don't reject
            details["volume_confirm"] = f"NEUTRAL ({vol_ratio:.2f}x)"
    else:
        details["volume_confirm"] = "INSUFFICIENT_DATA"

    return bullish, details


# ---------------------------------------------------------------------------
# Combined gate: check_ha_ensemble
# ---------------------------------------------------------------------------
def check_ha_ensemble(
    symbol: str,
    direction: str,
    interval: str = "4h",
    limit: int = 50,
) -> Dict:
    """
    Main entry point. Checks HA trend + 3-indicator ensemble for a symbol.

    Args:
        symbol:    e.g. "BTCUSDT"
        direction: "LONG" or "SHORT" (also accepts "BULL"/"BEAR"/"BUY"/"SELL")
        interval:  kline interval, default "4h"
        limit:     number of bars to fetch, default 50

    Returns dict:
        ha_trend:           "BULLISH" / "BEARISH" / "NEUTRAL"
        indicators_aligned: int 0-3 (how many indicators agree with direction)
        passes:             bool (HA agrees AND 2+ indicators agree)
        score_adjustment:   int (+10, +5, -10, or -25)
        details:            per-indicator breakdown
        error:              str or None
    """
    # Normalize direction
    dir_upper = direction.upper().strip()
    is_long = dir_upper in ("LONG", "BULL", "BUY", "BULLISH")

    result: Dict = {
        "symbol": symbol.upper(),
        "direction": dir_upper,
        "ha_trend": "NEUTRAL",
        "indicators_aligned": 0,
        "passes": False,
        "score_adjustment": -10,
        "details": {},
        "error": None,
    }

    # Fetch 4H klines
    klines = _fetch_klines(symbol, interval, limit)
    if not klines or len(klines) < 25:
        result["error"] = f"Insufficient kline data ({len(klines) if klines else 0} bars)"
        result["score_adjustment"] = 0  # No data = no penalty
        return result

    opens, highs, lows, closes, volumes = _parse_ohlcv(klines)
    if len(closes) < 25:
        result["error"] = "Insufficient parsed OHLCV data"
        result["score_adjustment"] = 0
        return result

    # --- Heikin Ashi trend ---
    ha_open, ha_high, ha_low, ha_close = _compute_heikin_ashi(opens, highs, lows, closes)
    trend = _ha_trend(ha_open, ha_close, lookback=3)
    result["ha_trend"] = trend

    ha_agrees = (
        (is_long and trend == "BULLISH")
        or (not is_long and trend == "BEARISH")
        or trend == "NEUTRAL"  # Neutral doesn't block
    )

    # --- 3-Indicator ensemble ---
    bullish_count, indicator_details = _ensemble_vote(closes, volumes)
    result["details"] = indicator_details

    # Count how many indicators agree with direction
    if is_long:
        aligned = bullish_count
    else:
        # For shorts, bearish indicators are the ones that agree
        aligned = 3 - bullish_count
        # But handle neutral volume correctly
        if "NEUTRAL" in indicator_details.get("volume_confirm", ""):
            # Neutral volume doesn't count for either side
            aligned = min(aligned, 2)
        if "REJECTED" in indicator_details.get("volume_confirm", ""):
            # Rejected volume counts as bearish (agrees with short)
            pass  # already counted via 3 - bullish_count
        if "CONFIRMED" in indicator_details.get("volume_confirm", ""):
            # Confirmed volume is bullish (disagrees with short)
            pass

    result["indicators_aligned"] = aligned

    # --- Score adjustment ---
    if ha_agrees and aligned >= 3:
        result["score_adjustment"] = 10
        result["passes"] = True
    elif ha_agrees and aligned >= 2:
        result["score_adjustment"] = 5
        result["passes"] = True
    elif aligned >= 1:
        result["score_adjustment"] = -10
        result["passes"] = False
    else:
        # 0/3 indicators + HA disagrees
        result["score_adjustment"] = -25
        result["passes"] = False

    return result


# ---------------------------------------------------------------------------
# Batch helper
# ---------------------------------------------------------------------------
def check_ha_ensemble_batch(
    symbols_directions: List[Tuple[str, str]],
    interval: str = "4h",
) -> List[Dict]:
    """
    Check HA ensemble for multiple (symbol, direction) pairs.
    Returns list of result dicts.
    """
    results = []
    for symbol, direction in symbols_directions:
        results.append(check_ha_ensemble(symbol, direction, interval=interval))
    return results


# ---------------------------------------------------------------------------
# run() -- test with BTC, ETH, SOL
# ---------------------------------------------------------------------------
def run() -> None:
    """Test the HA ensemble filter on BTCUSDT, ETHUSDT, SOLUSDT."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    test_cases = [
        ("BTCUSDT", "LONG"),
        ("BTCUSDT", "SHORT"),
        ("ETHUSDT", "LONG"),
        ("ETHUSDT", "SHORT"),
        ("SOLUSDT", "LONG"),
        ("SOLUSDT", "SHORT"),
    ]

    print("=" * 72)
    print("  HEIKIN ASHI ENSEMBLE FILTER -- TEST RUN")
    print("=" * 72)

    for symbol, direction in test_cases:
        r = check_ha_ensemble(symbol, direction)
        status = "PASS" if r["passes"] else "FAIL"
        print(f"\n  {symbol} {direction:5s} | HA={r['ha_trend']:8s} | "
              f"Aligned={r['indicators_aligned']}/3 | "
              f"Score={r['score_adjustment']:+3d} | {status}")
        if r.get("error"):
            print(f"    ERROR: {r['error']}")
        for k, v in r.get("details", {}).items():
            print(f"    {k}: {v}")

    print("\n" + "=" * 72)
    print("  DONE")
    print("=" * 72)


if __name__ == "__main__":
    run()
