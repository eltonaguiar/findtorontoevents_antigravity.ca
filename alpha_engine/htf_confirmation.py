#!/usr/bin/env python3
"""Higher Timeframe (HTF) Confirmation Filter for Alpha Engine.

Fetches daily (1d) candles from Binance (4-mirror failover) and computes:
  - Daily EMA 9/21/50/200 alignment
  - Daily RSI(14)
  - Daily Bollinger %B (20,2)
  - Daily MACD histogram direction
  - Daily Williams %R(14)
  - Weekly trend proxy (last 5 daily closes direction)

Exports:
  get_htf_confirmation(symbol) -> dict
  should_take_trade(symbol, direction) -> bool
  apply_htf_filter(picks) -> list[dict]

Pure Python + numpy.  No pandas/scipy.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
import urllib.error

# Windows UTF-8 fix
if sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Shared API failover (Binance -> Bybit -> CoinGecko -> KuCoin -> CryptoCompare)
# ---------------------------------------------------------------------------
try:
    from api_failover import fetch_klines as _failover_fetch_klines
except ImportError:
    from alpha_engine.api_failover import fetch_klines as _failover_fetch_klines

# ---------------------------------------------------------------------------
# 1-hour in-memory cache
# ---------------------------------------------------------------------------
_htf_cache: dict[str, tuple[float, dict]] = {}  # symbol -> (timestamp, result)
CACHE_TTL = 3600  # 1 hour


def _cache_get(symbol: str) -> dict | None:
    if symbol in _htf_cache:
        ts, result = _htf_cache[symbol]
        if time.time() - ts < CACHE_TTL:
            return result
        del _htf_cache[symbol]
    return None


def _cache_set(symbol: str, result: dict) -> None:
    _htf_cache[symbol] = (time.time(), result)


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _rate_limit() -> None:
    global _last_api_call
    now = time.time()
    elapsed = now - _last_api_call
    if elapsed < RATE_LIMIT_SECONDS:
        time.sleep(RATE_LIMIT_SECONDS - elapsed)
    _last_api_call = time.time()


def _fetch_daily_klines(symbol: str, limit: int = 100) -> list[list]:
    """Fetch daily klines with 3-tier failover: Binance -> CoinGecko -> Bybit.

    Returns list of [open_time, open, high, low, close, volume, ...] or [].
    """
    _rate_limit()
    binance_sym = _to_binance_symbol(symbol)
    if binance_sym is None:
        return []

    # --- Tier 1: Binance 4-mirror failover ---
    params = f"symbol={binance_sym}&interval=1d&limit={limit}"
    last_err = None
    for mirror in BINANCE_MIRRORS:
        url = f"{mirror}/api/v3/klines?{params}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine-HTF/1.0"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode())
                if isinstance(data, list) and len(data) > 0:
                    return data
        except (urllib.error.URLError, urllib.error.HTTPError,
                json.JSONDecodeError, OSError, TimeoutError) as exc:
            last_err = exc
            continue

    if last_err:
        print(f"  [htf_confirmation] All Binance mirrors failed for {symbol}: {last_err}")

    # --- Tier 2: CoinGecko OHLC fallback ---
    cg_data = _fetch_coingecko_ohlc(binance_sym)
    if cg_data:
        return cg_data

    # --- Tier 3: Bybit kline fallback ---
    bybit_data = _fetch_bybit_klines(binance_sym, limit)
    if bybit_data:
        return bybit_data

    return []


def _fetch_coingecko_ohlc(binance_sym: str) -> list[list]:
    """CoinGecko OHLC fallback. Returns Binance-compatible kline format or []."""
    cg_id = _COINGECKO_IDS.get(binance_sym)
    if not cg_id:
        return []
    url = f"https://api.coingecko.com/api/v3/coins/{cg_id}/ohlc?vs_currency=usd&days=30"
    try:
        _rate_limit()
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine-HTF/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            if not isinstance(data, list) or len(data) == 0:
                return []
            # CoinGecko OHLC format: [timestamp, open, high, low, close]
            # Convert to Binance kline format: [time, open, high, low, close, volume, ...]
            klines = []
            for candle in data:
                if len(candle) >= 5:
                    klines.append([
                        candle[0],       # open_time (ms)
                        str(candle[1]),  # open
                        str(candle[2]),  # high
                        str(candle[3]),  # low
                        str(candle[4]),  # close
                        "0",             # volume (not available from CoinGecko OHLC)
                    ])
            if klines:
                print(f"  [htf_confirmation] CoinGecko fallback OK for {binance_sym}: {len(klines)} candles")
            return klines
    except (urllib.error.URLError, urllib.error.HTTPError,
            json.JSONDecodeError, OSError, TimeoutError) as exc:
        print(f"  [htf_confirmation] CoinGecko fallback failed for {binance_sym}: {exc}")
        return []


def _fetch_bybit_klines(binance_sym: str, limit: int = 100) -> list[list]:
    """Bybit V5 kline fallback. Returns Binance-compatible kline format or []."""
    url = (f"https://api.bybit.com/v5/market/kline"
           f"?category=spot&symbol={binance_sym}&interval=D&limit={min(limit, 200)}")
    try:
        _rate_limit()
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine-HTF/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = json.loads(resp.read().decode())
            result = raw.get("result", {})
            candles = result.get("list", [])
            if not candles:
                return []
            # Bybit V5 kline: [startTime, open, high, low, close, volume, turnover]
            klines = []
            for c in candles:
                if len(c) >= 5:
                    klines.append([
                        int(c[0]),  # open_time (ms)
                        str(c[1]),  # open
                        str(c[2]),  # high
                        str(c[3]),  # low
                        str(c[4]),  # close
                        str(c[5]) if len(c) > 5 else "0",  # volume
                    ])
            # Bybit returns newest first; reverse to oldest-first like Binance
            klines.reverse()
            if klines:
                print(f"  [htf_confirmation] Bybit fallback OK for {binance_sym}: {len(klines)} candles")
            return klines
    except (urllib.error.URLError, urllib.error.HTTPError,
            json.JSONDecodeError, OSError, TimeoutError) as exc:
        print(f"  [htf_confirmation] Bybit fallback failed for {binance_sym}: {exc}")
        return []


def _to_binance_symbol(symbol: str) -> str | None:
    """Convert pick symbol to Binance spot pair, or None if not convertible."""
    if not symbol:
        return None
    # Skip forex / equity symbols
    if "=" in symbol or symbol in ("SPY", "QQQ", "NVDA", "AAPL", "MSFT",
                                     "TSLA", "AMZN", "META", "GOOGL"):
        return None
    s = symbol.upper().replace("-", "")
    # Already has USDT suffix
    if s.endswith("USDT"):
        return s
    # Has USD suffix (CoinGecko style) -> USDT
    if s.endswith("USD"):
        return s + "T"
    # Bare symbol (BTC, ETH) -> add USDT
    if s.isalpha() and len(s) <= 10:
        return s + "USDT"
    return s


# ---------------------------------------------------------------------------
# Technical indicator computation (pure numpy)
# ---------------------------------------------------------------------------

def _ema(data: "np.ndarray", period: int) -> "np.ndarray":
    """Exponential Moving Average."""
    alpha = 2.0 / (period + 1)
    result = np.empty_like(data)
    result[0] = data[0]
    for i in range(1, len(data)):
        result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
    return result


def _sma(data: "np.ndarray", period: int) -> "np.ndarray":
    """Simple Moving Average (NaN for first period-1 bars)."""
    result = np.full_like(data, np.nan)
    if len(data) < period:
        return result
    cumsum = np.cumsum(data)
    result[period - 1:] = (cumsum[period - 1:] - np.concatenate(([0], cumsum[:-period]))) / period
    return result


def _rsi(closes: "np.ndarray", period: int = 14) -> float:
    """RSI(period) of most recent bar."""
    if len(closes) < period + 1:
        return 50.0
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100.0 - 100.0 / (1.0 + rs))


def _bollinger_pct_b(closes: "np.ndarray", period: int = 20, mult: float = 2.0) -> float:
    """Bollinger %B: (price - lower) / (upper - lower). 0=lower band, 1=upper band."""
    if len(closes) < period:
        return 0.5
    window = closes[-period:]
    sma_val = float(np.mean(window))
    std_val = float(np.std(window, ddof=0))
    if std_val == 0:
        return 0.5
    upper = sma_val + mult * std_val
    lower = sma_val - mult * std_val
    band_width = upper - lower
    if band_width == 0:
        return 0.5
    return float((closes[-1] - lower) / band_width)


def _macd_histogram(closes: "np.ndarray") -> tuple[float, bool]:
    """MACD histogram (12,26,9). Returns (histogram_value, is_rising)."""
    if len(closes) < 35:
        return 0.0, False
    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    macd_line = ema12 - ema26
    signal_line = _ema(macd_line, 9)
    hist = macd_line - signal_line
    current = float(hist[-1])
    prev = float(hist[-2]) if len(hist) >= 2 else 0.0
    return current, current > prev


def _williams_r(highs: "np.ndarray", lows: "np.ndarray", closes: "np.ndarray",
                period: int = 14) -> float:
    """Williams %R. Range: -100 to 0."""
    if len(closes) < period:
        return -50.0
    hh = float(np.max(highs[-period:]))
    ll = float(np.min(lows[-period:]))
    if hh == ll:
        return -50.0
    return float(-100.0 * (hh - closes[-1]) / (hh - ll))


def _weekly_trend(closes: "np.ndarray") -> str:
    """Proxy weekly trend from last 5 daily closes."""
    if len(closes) < 5:
        return "FLAT"
    last5 = closes[-5:]
    rising = sum(1 for i in range(1, len(last5)) if last5[i] > last5[i - 1])
    if rising >= 4:
        return "UP"
    elif rising <= 1:
        return "DOWN"
    return "FLAT"


# ---------------------------------------------------------------------------
# Core HTF analysis
# ---------------------------------------------------------------------------

def get_htf_confirmation(symbol: str) -> dict:
    """Compute HTF confirmation data for a symbol.

    Returns dict with:
        htf_bias: "BULLISH" / "BEARISH" / "NEUTRAL"
        htf_score: 0-5 (number of bullish indicators)
        daily_ema_aligned: bool (EMA 9>21>50 for bull, 9<21<50 for bear)
        daily_rsi: float
        daily_bb_position: float (0-1 Bollinger %B)
        daily_macd_rising: bool
        daily_williams_r: float (-100 to 0)
        weekly_trend: "UP" / "DOWN" / "FLAT"
    """
    if np is None:
        return _neutral_result()

    # Check cache first
    cached = _cache_get(symbol)
    if cached is not None:
        return cached

    klines = _fetch_daily_klines(symbol, limit=100)
    if not klines or len(klines) < 30:
        result = _neutral_result()
        _cache_set(symbol, result)
        return result

    # Parse OHLCV
    opens = np.array([float(k[1]) for k in klines])
    highs = np.array([float(k[2]) for k in klines])
    lows = np.array([float(k[3]) for k in klines])
    closes = np.array([float(k[4]) for k in klines])

    # --- Indicators ---
    # 1. Daily EMA alignment
    ema9 = _ema(closes, 9)
    ema21 = _ema(closes, 21)
    ema50 = _ema(closes, 50)

    ema9_now = float(ema9[-1])
    ema21_now = float(ema21[-1])
    ema50_now = float(ema50[-1])

    bullish_ema = ema9_now > ema21_now > ema50_now
    bearish_ema = ema9_now < ema21_now < ema50_now
    daily_ema_aligned = bullish_ema or bearish_ema

    # Also compute EMA 200 for context (if enough bars)
    ema200_now = None
    if len(closes) >= 200:
        ema200 = _ema(closes, 200)
        ema200_now = float(ema200[-1])

    # 2. Daily RSI
    daily_rsi = _rsi(closes, 14)

    # 3. Daily Bollinger %B
    daily_bb = _bollinger_pct_b(closes, 20, 2.0)

    # 4. Daily MACD histogram
    macd_val, macd_rising = _macd_histogram(closes)

    # 5. Williams %R
    williams = _williams_r(highs, lows, closes, 14)

    # 6. Weekly trend proxy
    wk_trend = _weekly_trend(closes)

    # --- Score: count bullish signals (0-5) ---
    bull_score = 0

    # EMA alignment: +1 if bullish
    if bullish_ema:
        bull_score += 1

    # RSI: +1 if above 50 (bullish), 0 if below (bearish)
    if daily_rsi > 50:
        bull_score += 1

    # BB position: +1 if in upper half
    if daily_bb > 0.5:
        bull_score += 1

    # MACD: +1 if histogram positive and rising
    if macd_val > 0 and macd_rising:
        bull_score += 1

    # Weekly trend: +1 if UP
    if wk_trend == "UP":
        bull_score += 1

    # --- Determine bias ---
    bear_score = 0
    if bearish_ema:
        bear_score += 1
    if daily_rsi < 50:
        bear_score += 1
    if daily_bb < 0.5:
        bear_score += 1
    if macd_val < 0 and not macd_rising:
        bear_score += 1
    if wk_trend == "DOWN":
        bear_score += 1

    if bull_score >= 4:
        htf_bias = "BULLISH"
    elif bear_score >= 4:
        htf_bias = "BEARISH"
    else:
        htf_bias = "NEUTRAL"

    result = {
        "htf_bias": htf_bias,
        "htf_score": bull_score,
        "htf_bear_score": bear_score,
        "daily_ema_aligned": daily_ema_aligned,
        "daily_ema_bullish": bullish_ema,
        "daily_ema_bearish": bearish_ema,
        "daily_rsi": round(daily_rsi, 2),
        "daily_bb_position": round(daily_bb, 4),
        "daily_macd_rising": macd_rising,
        "daily_macd_value": round(macd_val, 6),
        "daily_williams_r": round(williams, 2),
        "weekly_trend": wk_trend,
    }

    _cache_set(symbol, result)
    return result


def _neutral_result() -> dict:
    return {
        "htf_bias": "NEUTRAL",
        "htf_score": 0,
        "htf_bear_score": 0,
        "daily_ema_aligned": False,
        "daily_ema_bullish": False,
        "daily_ema_bearish": False,
        "daily_rsi": 50.0,
        "daily_bb_position": 0.5,
        "daily_macd_rising": False,
        "daily_macd_value": 0.0,
        "daily_williams_r": -50.0,
        "weekly_trend": "FLAT",
    }


# ---------------------------------------------------------------------------
# Trade direction filter
# ---------------------------------------------------------------------------

def should_take_trade(symbol: str, direction: str) -> bool:
    """Check if HTF confirms the trade direction.

    direction: "BUY" / "SELL" / "LONG" / "SHORT"
    Returns True if HTF is aligned or neutral, False if HTF disagrees.
    """
    htf = get_htf_confirmation(symbol)
    bias = htf["htf_bias"]
    is_long = direction.upper() in ("BUY", "LONG")

    # Neutral never blocks
    if bias == "NEUTRAL":
        return True

    # Strong disagreement blocks
    if is_long and bias == "BEARISH" and htf["htf_bear_score"] >= 4:
        return False
    if not is_long and bias == "BULLISH" and htf["htf_score"] >= 4:
        return False

    return True


# ---------------------------------------------------------------------------
# Batch filter for pick lists
# ---------------------------------------------------------------------------

def apply_htf_filter(picks: list[dict]) -> list[dict]:
    """Annotate picks with HTF confirmation data and adjust confidence.

    - Fetches HTF data for each unique symbol (with rate limiting)
    - Annotates each pick with htf_bias, htf_score, htf_aligned
    - Picks where HTF disagrees: confidence -= 0.10
    - Picks where HTF strongly agrees (score >= 4): confidence += 0.05
    - Returns the annotated picks list
    """
    if not picks:
        return picks

    # Collect unique crypto symbols
    symbols = set()
    for p in picks:
        cat = p.get("category", "crypto")
        if cat in ("forex", "stock", "etf", "futures"):
            continue
        sym = p.get("symbol", "")
        if sym and "=" not in sym:
            symbols.add(sym)

    # Pre-fetch HTF data for all symbols (rate-limited)
    htf_data: dict[str, dict] = {}
    fetched = 0
    for sym in sorted(symbols):
        try:
            htf_data[sym] = get_htf_confirmation(sym)
            fetched += 1
        except Exception as exc:
            htf_data[sym] = _neutral_result()

    htf_adjusted = 0
    htf_boosted = 0

    for p in picks:
        sym = p.get("symbol", "")
        if sym not in htf_data:
            p.setdefault("extra", {})["htf_bias"] = "N/A"
            p.setdefault("extra", {})["htf_score"] = 0
            p.setdefault("extra", {})["htf_aligned"] = True
            continue

        htf = htf_data[sym]
        direction = p.get("signal_type", "BUY").upper()
        is_long = direction in ("BUY", "LONG")
        bias = htf["htf_bias"]

        # Determine alignment
        aligned = True
        if is_long and bias == "BEARISH":
            aligned = False
        elif not is_long and bias == "BULLISH":
            aligned = False

        # Annotate (both top-level for dashboard and extra for detail)
        extra = p.setdefault("extra", {})
        extra["htf_bias"] = bias
        extra["htf_score"] = htf["htf_score"]
        extra["htf_bear_score"] = htf["htf_bear_score"]
        extra["htf_aligned"] = aligned
        extra["daily_rsi"] = htf["daily_rsi"]
        extra["daily_bb_position"] = htf["daily_bb_position"]
        extra["daily_macd_rising"] = htf["daily_macd_rising"]
        extra["daily_williams_r"] = htf["daily_williams_r"]
        extra["weekly_trend"] = htf["weekly_trend"]
        extra["daily_ema_aligned"] = htf["daily_ema_aligned"]
        # Promote to top-level so dashboard HTF/STRONG columns can read it
        p["htf_confirmation"] = bias.lower()
        p["htf_bias"] = bias
        p["htf_aligned"] = aligned

        # Confidence adjustment
        conf = p.get("confidence", 0.5)
        if not aligned:
            conf = max(0.05, conf - 0.10)
            htf_adjusted += 1
        elif (is_long and htf["htf_score"] >= 4) or \
             (not is_long and htf["htf_bear_score"] >= 4):
            conf = min(0.99, conf + 0.05)
            htf_boosted += 1
        p["confidence"] = round(conf, 4)

    print(f"  [htf_confirmation] Fetched HTF for {fetched} symbols | "
          f"penalized={htf_adjusted}, boosted={htf_boosted} out of {len(picks)} picks")

    return picks


# ---------------------------------------------------------------------------
# Standalone CLI mode
# ---------------------------------------------------------------------------

def _cli_test():
    """Test HTF confirmation on BTC, ETH, SOL."""
    test_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    print("=" * 70)
    print("HTF Confirmation Module - Standalone Test")
    print("=" * 70)

    for sym in test_symbols:
        print(f"\n--- {sym} ---")
        result = get_htf_confirmation(sym)
        for k, v in result.items():
            print(f"  {k:25s}: {v}")

        # Test should_take_trade
        for direction in ("BUY", "SELL"):
            ok = should_take_trade(sym, direction)
            print(f"  should_take_trade({direction:4s}): {'YES' if ok else 'NO'}")

    # Test batch filter
    print(f"\n{'=' * 70}")
    print("Batch filter test:")
    test_picks = [
        {"symbol": "BTCUSDT", "signal_type": "BUY", "confidence": 0.7, "category": "crypto"},
        {"symbol": "ETHUSDT", "signal_type": "SELL", "confidence": 0.65, "category": "crypto"},
        {"symbol": "SOLUSDT", "signal_type": "BUY", "confidence": 0.8, "category": "crypto"},
    ]
    annotated = apply_htf_filter(test_picks)
    for p in annotated:
        extra = p.get("extra", {})
        print(f"  {p['symbol']} {p['signal_type']} conf={p['confidence']:.4f} "
              f"htf_bias={extra.get('htf_bias')} aligned={extra.get('htf_aligned')}")

    print(f"\n{'=' * 70}")
    print("All tests completed.")


if __name__ == "__main__":
    _cli_test()
