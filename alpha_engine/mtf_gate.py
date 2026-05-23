"""
ALPHA ENGINE -- Multi-Timeframe (MTF) Confirmation Gate
=========================================================
The #1 WR-boosting feature.  Before any pick is accepted as a Smart Pick,
this gate checks whether the HIGHER timeframe agrees with the signal
direction.  Research shows MTF confirmation alone can push WR from ~42%
to 55-62%.

Timeframes checked:
  - 1H  (50 bars) -- signal timeframe
  - 4H  (50 bars) -- trend timeframe
  - 1D  (30 bars) -- structure timeframe

Each timeframe's trend is determined by majority vote of:
  1. EMA-9 vs EMA-20
  2. Price vs SMA-50
  3. MACD histogram sign

Agreement scoring:
  3/3 agree with pick direction  -> STRONG   (+10)
  2/3 agree                      -> MODERATE (+5)
  1/3 agree                      -> WEAK     (-10)
  0/3 agree                      -> BLOCKED  (-25, optionally reject pick)

Usage:
    from mtf_gate import check_mtf_alignment, check_mtf_batch

    result = check_mtf_alignment("BTCUSDT", "BULL")
    # result['aligned'] -> True/False
    # result['score_adjustment'] -> -25 to +10

Stdlib only (urllib, json, math).  5-mirror Binance failover.
"""

from __future__ import annotations

import json
import math
import logging
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
# Binance mirror failover (5 mirrors)
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
# Cache: module-level dict  { (symbol, interval): (timestamp, data) }
# ---------------------------------------------------------------------------
_kline_cache: Dict[Tuple[str, str], Tuple[float, list]] = {}
_CACHE_TTL = 600  # 10 minutes

# Rate-limit tracker
_last_api_call = 0.0
_RATE_LIMIT_DELAY = 0.1  # 100 ms between API calls

# Circuit-breaker: if Binance returns HTTP 451 (geo-block), skip all remaining calls
_BINANCE_BLOCKED = False
_binance_consecutive_failures = 0
_BINANCE_FAILURE_THRESHOLD = 3  # Give up after 3 consecutive 451/block failures

# Pre-check: test Binance availability once at module load (saves 50s+ if geo-blocked)
def _ping_binance() -> bool:
    """Quick ping to check if Binance is reachable. Timeout 3s."""
    import urllib.request
    try:
        req = urllib.request.Request("https://data-api.binance.vision/api/v3/ping",
                                     headers={"User-Agent": "AlphaEngine/2.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False

# Run ping at import time — if Binance is down, skip everything immediately
if not _ping_binance():
    _BINANCE_BLOCKED = True
    import logging
    logging.getLogger("mtf_gate").warning("Binance ping failed at startup — MTF gate disabled for this session")


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


def _to_cc_symbol(symbol: str) -> Tuple[str, str]:
    s = symbol.upper().replace("-", "").replace("_", "").replace("/", "")
    if s.endswith("USDT"):
        return s[:-4], "USDT"
    if s.endswith("USDC"):
        return s[:-4], "USDC"
    if s.endswith("USD"):
        return s[:-3], "USD"
    return s[:3], s[3:] if len(s) > 3 else "USD"


def _fetch_klines_bybit(symbol: str, interval: str, limit: int = 50) -> list:
    """Fallback OHLCV from Bybit v5 when Binance is geo-blocked (no auth, no geo-block)."""
    _BYBIT_INTERVAL_MAP = {"1h": "60", "4h": "240", "1d": "D", "5m": "5", "15m": "15"}
    bybit_interval = _BYBIT_INTERVAL_MAP.get(interval, "60")
    url = (
        f"https://api.bybit.com/v5/market/kline"
        f"?category=spot&symbol={symbol.upper()}"
        f"&interval={bybit_interval}&limit={min(limit, 200)}"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
        with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if payload.get("retCode") != 0:
            return []
        rows = []
        for item in payload["result"]["list"]:
            # Bybit format: [startTime, open, high, low, close, volume, turnover]
            rows.append([int(item[0]), item[1], item[2], item[3], item[4], item[5]])
        return rows[-limit:] if rows else []
    except Exception:
        return []


def _fetch_klines_kucoin(symbol: str, interval: str, limit: int = 50) -> list:
    """Fallback OHLCV from KuCoin when Binance + Bybit are unavailable (no auth, no geo-block)."""
    _KC_INTERVAL_MAP = {"1h": "1hour", "4h": "4hour", "1d": "1day"}
    kc_interval = _KC_INTERVAL_MAP.get(interval, "1hour")
    base_sym = symbol.upper().replace("USDT", "-USDT").replace("USDC", "-USDC")
    if "-" not in base_sym:
        base_sym = f"{base_sym}-USDT"
    end_at = int(time.time())
    start_at = end_at - (limit * 3600 * (4 if interval == "4h" else 24 if interval == "1d" else 1))
    url = (
        f"https://api.kucoin.com/api/v1/market/candles"
        f"?type={kc_interval}&symbol={base_sym}"
        f"&startAt={start_at}&endAt={end_at}"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
        with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if payload.get("code") != "200000":
            return []
        rows = []
        for item in payload.get("data", []):
            # KuCoin format: [time, open, close, high, low, volume, turnover]
            rows.append([int(item[0]) * 1000, item[1], item[3], item[4], item[2], item[5]])
        return rows[-limit:] if rows else []
    except Exception:
        return []


def _fetch_klines_fallback(symbol: str, interval: str, limit: int = 50) -> list:
    """Fallback OHLCV: try Bybit → KuCoin → CryptoCompare when Binance is unavailable."""
    # 1. Bybit (fast, no geo-block, no auth)
    data = _fetch_klines_bybit(symbol, interval, limit)
    if data:
        return data

    # 2. KuCoin (good coverage, no geo-block)
    data = _fetch_klines_kucoin(symbol, interval, limit)
    if data:
        return data

    # 3. CryptoCompare (slow, reliable)
    fsym, tsym = _to_cc_symbol(symbol)
    if interval in ("1h", "4h"):
        endpoint = "https://min-api.cryptocompare.com/data/v2/histohour"
        aggregate = 1 if interval == "1h" else 4
    else:
        endpoint = "https://min-api.cryptocompare.com/data/v2/histoday"
        aggregate = 1
    url = (
        f"{endpoint}?fsym={fsym}&tsym={tsym}&limit={max(20, limit)}"
        f"&aggregate={aggregate}&e=CCCAGG"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
        with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        rows = (((payload or {}).get("Data") or {}).get("Data")) or []
        out = []
        for r in rows:
            close = r.get("close")
            if close is None:
                continue
            ts = int(r.get("time", 0)) * 1000
            # Binance-compatible minimal kline shape: close at index 4.
            out.append([ts, 0, 0, 0, str(close), str(r.get("volumefrom", 0))])
        return out[-limit:] if out else []
    except Exception:
        return []


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
    global _BINANCE_BLOCKED, _binance_consecutive_failures

    # Circuit-breaker: if geo-blocked (HTTP 451) or repeated failures, bail immediately
    if _BINANCE_BLOCKED:
        return []

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
                _binance_consecutive_failures = 0  # Reset on success
                return data
        except urllib.error.HTTPError as exc:
            last_err = exc
            if exc.code == 451:
                # Geo-blocked — trip circuit breaker immediately, don't waste time on remaining mirrors
                _BINANCE_BLOCKED = True
                logger.warning("Binance geo-blocked (HTTP 451) — disabling all Binance kline fetches for this session")
                return []
            logger.debug("Mirror %s failed for %s %s: %s", mirror, symbol, interval, exc)
            continue
        except Exception as exc:
            last_err = exc
            logger.debug("Mirror %s failed for %s %s: %s", mirror, symbol, interval, exc)
            continue

    _binance_consecutive_failures += 1
    if _binance_consecutive_failures >= _BINANCE_FAILURE_THRESHOLD:
        _BINANCE_BLOCKED = True
        logger.warning("Binance unreachable after %d consecutive failures — disabling kline fetches", _binance_consecutive_failures)

    logger.warning("All Binance mirrors failed for %s %s: %s", symbol, interval, last_err)
    return []


# ---------------------------------------------------------------------------
# Parse klines into close-price list
# ---------------------------------------------------------------------------
def _parse_closes(klines: list) -> List[float]:
    """Extract close prices from Binance kline response."""
    closes = []
    for k in klines:
        try:
            closes.append(float(k[4]))  # index 4 = close price
        except (IndexError, TypeError, ValueError):
            continue
    return closes


# ---------------------------------------------------------------------------
# Technical indicators (stdlib only -- no numpy/pandas)
# ---------------------------------------------------------------------------
def _ema(values: List[float], period: int) -> List[float]:
    """Compute EMA.  Returns list same length as input (NaN-filled for warmup)."""
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
    """Compute SMA.  Returns list same length as input (NaN-filled for warmup)."""
    if len(values) < period:
        return [float("nan")] * len(values)
    result: List[float] = [float("nan")] * (period - 1)
    window_sum = sum(values[:period])
    result.append(window_sum / period)
    for i in range(period, len(values)):
        window_sum += values[i] - values[i - period]
        result.append(window_sum / period)
    return result


def _macd_histogram(values: List[float]) -> List[float]:
    """MACD histogram = MACD line - signal line.
    MACD line  = EMA12 - EMA26
    Signal line = EMA9 of MACD line
    """
    ema12 = _ema(values, 12)
    ema26 = _ema(values, 26)
    macd_line: List[float] = []
    for a, b in zip(ema12, ema26):
        if math.isnan(a) or math.isnan(b):
            macd_line.append(float("nan"))
        else:
            macd_line.append(a - b)

    # Filter valid values for signal line
    valid_macd = [v for v in macd_line if not math.isnan(v)]
    if len(valid_macd) < 9:
        return [float("nan")] * len(values)

    signal = _ema(valid_macd, 9)
    # Map signal back to full-length list
    histogram: List[float] = [float("nan")] * len(values)
    valid_idx = 0
    for i, m in enumerate(macd_line):
        if not math.isnan(m):
            if valid_idx < len(signal) and not math.isnan(signal[valid_idx]):
                histogram[i] = m - signal[valid_idx]
            valid_idx += 1
    return histogram


# ---------------------------------------------------------------------------
# Determine trend direction for a single timeframe
# ---------------------------------------------------------------------------
def _determine_trend(closes: List[float]) -> Optional[str]:
    """
    Determine trend using 3 indicators (majority vote):
      1. EMA-9 vs EMA-20
      2. Price vs SMA-50
      3. MACD histogram sign

    Returns 'BULL', 'BEAR', or None if insufficient data.
    """
    if len(closes) < 26:  # minimum for MACD
        return None

    ema9 = _ema(closes, 9)
    ema20 = _ema(closes, 20)
    sma50 = _sma(closes, min(50, len(closes)))  # use available data
    macd_hist = _macd_histogram(closes)

    latest_close = closes[-1]
    latest_ema9 = ema9[-1] if ema9 else float("nan")
    latest_ema20 = ema20[-1] if ema20 else float("nan")
    latest_sma50 = sma50[-1] if sma50 else float("nan")
    latest_macd = macd_hist[-1] if macd_hist else float("nan")

    bull_votes = 0
    bear_votes = 0
    total_votes = 0

    # Indicator 1: EMA 9 vs EMA 20
    if not math.isnan(latest_ema9) and not math.isnan(latest_ema20):
        total_votes += 1
        if latest_ema9 > latest_ema20:
            bull_votes += 1
        else:
            bear_votes += 1

    # Indicator 2: Price vs SMA 50
    if not math.isnan(latest_sma50):
        total_votes += 1
        if latest_close > latest_sma50:
            bull_votes += 1
        else:
            bear_votes += 1

    # Indicator 3: MACD histogram
    if not math.isnan(latest_macd):
        total_votes += 1
        if latest_macd > 0:
            bull_votes += 1
        else:
            bear_votes += 1

    if total_votes == 0:
        return None

    # 2/3 majority required
    if bull_votes >= 2:
        return "BULL"
    elif bear_votes >= 2:
        return "BEAR"
    # 1-1 or edge case: side with EMA crossover
    if not math.isnan(latest_ema9) and not math.isnan(latest_ema20):
        return "BULL" if latest_ema9 > latest_ema20 else "BEAR"
    return None


# ---------------------------------------------------------------------------
# Core: check MTF alignment for a single symbol
# ---------------------------------------------------------------------------
_SCORE_MAP = {
    "STRONG": 10,
    "MODERATE": 5,
    "WEAK": -10,
    "BLOCKED": -25,
}


def check_mtf_alignment(symbol: str, direction: str) -> dict:
    """
    Check multi-timeframe alignment for a symbol/direction.

    Args:
        symbol:    Binance symbol (e.g. 'BTCUSDT')
        direction: 'BULL' or 'BEAR' (the pick direction)

    Returns:
        {
            'aligned': True/False,
            'score_adjustment': int (-25 to +10),
            'tf_1h': 'BULL'/'BEAR'/None,
            'tf_4h': 'BULL'/'BEAR'/None,
            'tf_1d': 'BULL'/'BEAR'/None,
            'agreement': '3/3' or '2/3' or '1/3' or '0/3',
            'recommendation': 'STRONG'/'MODERATE'/'WEAK'/'BLOCKED'
        }
    """
    direction = direction.upper()
    if direction not in ("BULL", "BEAR"):
        direction = "BULL"  # default

    result = {
        "aligned": False,
        "score_adjustment": 0,
        "tf_1h": None,
        "tf_4h": None,
        "tf_1d": None,
        "agreement": "0/3",
        "recommendation": "BLOCKED",
        "symbol": symbol,
        "direction": direction,
    }

    # Fetch klines for all 3 timeframes
    klines_1h = _fetch_klines(symbol, "1h", limit=50)
    klines_4h = _fetch_klines(symbol, "4h", limit=50)
    klines_1d = _fetch_klines(symbol, "1d", limit=30)
    # Fallback chain: Bybit → KuCoin → CryptoCompare (when Binance is geo-blocked)
    if not klines_1h:
        klines_1h = _fetch_klines_fallback(symbol, "1h", limit=50)
    if not klines_4h:
        klines_4h = _fetch_klines_fallback(symbol, "4h", limit=50)
    if not klines_1d:
        klines_1d = _fetch_klines_fallback(symbol, "1d", limit=30)

    closes_1h = _parse_closes(klines_1h)
    closes_4h = _parse_closes(klines_4h)
    closes_1d = _parse_closes(klines_1d)

    # Determine trend per timeframe
    trend_1h = _determine_trend(closes_1h)
    trend_4h = _determine_trend(closes_4h)
    trend_1d = _determine_trend(closes_1d)

    result["tf_1h"] = trend_1h
    result["tf_4h"] = trend_4h
    result["tf_1d"] = trend_1d

    # Count agreements
    agree_count = 0
    total_tf = 0
    for tf_trend in [trend_1h, trend_4h, trend_1d]:
        if tf_trend is not None:
            total_tf += 1
            if tf_trend == direction:
                agree_count += 1

    if total_tf == 0:
        # No data available -- pass through with no adjustment
        result["agreement"] = "N/A"
        result["recommendation"] = "NO_DATA"
        result["aligned"] = True  # don't block if we have no data
        result["score_adjustment"] = 0
        return result

    result["agreement"] = f"{agree_count}/{total_tf}"

    # Map to recommendation
    if total_tf == 3:
        if agree_count == 3:
            rec = "STRONG"
        elif agree_count == 2:
            rec = "MODERATE"
        elif agree_count == 1:
            rec = "WEAK"
        else:
            rec = "BLOCKED"
    elif total_tf == 2:
        if agree_count == 2:
            rec = "STRONG"
        elif agree_count == 1:
            rec = "MODERATE"
        else:
            rec = "BLOCKED"
    else:
        # Only 1 timeframe available
        rec = "MODERATE" if agree_count == 1 else "WEAK"

    result["recommendation"] = rec
    result["score_adjustment"] = _SCORE_MAP.get(rec, 0)
    result["aligned"] = rec in ("STRONG", "MODERATE")

    return result


# ---------------------------------------------------------------------------
# Batch: check multiple symbols efficiently (shared cache)
# ---------------------------------------------------------------------------
def check_mtf_batch(symbols_directions: List[Tuple[str, str]]) -> Dict[str, dict]:
    """
    Check MTF alignment for multiple symbols at once.
    Cache is shared, so repeated symbols don't re-fetch.

    Args:
        symbols_directions: list of (symbol, direction) tuples
            e.g. [('BTCUSDT', 'BULL'), ('ETHUSDT', 'BEAR')]

    Returns:
        dict keyed by symbol -> alignment result dict
    """
    results: Dict[str, dict] = {}
    for symbol, direction in symbols_directions:
        try:
            results[symbol] = check_mtf_alignment(symbol, direction)
        except Exception as exc:
            logger.warning("MTF check failed for %s: %s", symbol, exc)
            results[symbol] = {
                "aligned": True,  # don't block on errors
                "score_adjustment": 0,
                "tf_1h": None,
                "tf_4h": None,
                "tf_1d": None,
                "agreement": "ERROR",
                "recommendation": "ERROR",
                "symbol": symbol,
                "direction": direction,
                "error": str(exc),
            }
    return results


# ---------------------------------------------------------------------------
# Clear cache (for testing / forced refresh)
# ---------------------------------------------------------------------------
def clear_cache() -> None:
    """Clear the kline data cache."""
    _kline_cache.clear()


# ---------------------------------------------------------------------------
# run() -- test with BTC, ETH, SOL
# ---------------------------------------------------------------------------
def run() -> None:
    """Test MTF gate with BTC, ETH, SOL."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    print("=" * 70)
    print("  Multi-Timeframe (MTF) Confirmation Gate -- Test Run")
    print("=" * 70)

    test_pairs = [
        ("BTCUSDT", "BULL"),
        ("ETHUSDT", "BULL"),
        ("SOLUSDT", "BULL"),
    ]

    # Single checks
    for symbol, direction in test_pairs:
        print(f"\n--- {symbol} ({direction}) ---")
        result = check_mtf_alignment(symbol, direction)
        print(f"  1H trend : {result['tf_1h']}")
        print(f"  4H trend : {result['tf_4h']}")
        print(f"  1D trend : {result['tf_1d']}")
        print(f"  Agreement: {result['agreement']}")
        print(f"  Verdict  : {result['recommendation']}")
        print(f"  Score adj: {result['score_adjustment']:+d}")
        print(f"  Aligned  : {result['aligned']}")

    # Batch check
    print("\n" + "=" * 70)
    print("  Batch check (same symbols, uses cached data)")
    print("=" * 70)
    batch = check_mtf_batch(test_pairs)
    for sym, res in batch.items():
        print(f"  {sym}: {res['recommendation']} ({res['agreement']}) score={res['score_adjustment']:+d}")

    print("\n[DONE]")


if __name__ == "__main__":
    run()
