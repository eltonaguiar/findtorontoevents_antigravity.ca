#!/usr/bin/env python3
"""
ALPHA_ENGINE -- Feature Populator (Phase 16 -- Kill Dead Features)
===================================================================
Fetches real OHLCV data from Binance (5-mirror failover) and computes
ALL ML features at pick-creation time, so the ML model trains on real
values instead of mostly-zero defaults.

INTEGRATION POINT (scanner.py):
  Insert AFTER cross-sectional injection (~line 3608) and BEFORE ML scoring (~line 2431):

    from feature_populator import populate_batch
    if signals:
        populate_batch(signals)

  This populates every feature that ml_ranker.py's _signal_to_features() reads
  from the signal dict, including: rsi_at_entry, volume_ratio, atr_at_entry,
  regime_encoded, close_to_vwap, garman_klass_vol, fear_greed_norm, funding_rate_raw,
  mom30, rsi30, macd_hist_norm, stoch_k30, stoch_d30, cci20_norm, williams_r,
  cs_momentum_rank, orderbook_imbalance, btc_correlation, btc_24h_change, and more.

Stdlib only (math, urllib, json) -- NO numpy/pandas.
Windows UTF-8 safe.
10-minute in-memory kline cache.
100ms rate limiting between API calls.
Graceful fallback: if any feature fails, existing default is preserved.
"""

from __future__ import annotations

import io
import json
import logging
import math
import os
import ssl
import sys
import time
import urllib.request
from datetime import datetime, timezone
from typing import Any, Optional

# Windows UTF-8 fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Binance mirror failover chain (5 mirrors as required by API failover rule)
# ---------------------------------------------------------------------------
BINANCE_KLINE_MIRRORS = [
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

BINANCE_FAPI_MIRRORS = [
    "https://fapi.binance.com",
    "https://api.binance.com",
    "https://api1.binance.com",
]

FEAR_GREED_URL = "https://api.alternative.me/fng/?limit=1"
BINANCE_DEPTH_URL = "https://api.binance.com/api/v3/depth"

# ---------------------------------------------------------------------------
# In-memory cache (10-minute TTL)
# ---------------------------------------------------------------------------
_CACHE: dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 600  # 10 minutes in seconds
_LAST_API_CALL = 0.0
_RATE_LIMIT_MS = 100  # 100ms between API calls


def _rate_limit():
    """Enforce 100ms minimum between API calls."""
    global _LAST_API_CALL
    now = time.monotonic()
    elapsed_ms = (now - _LAST_API_CALL) * 1000
    if elapsed_ms < _RATE_LIMIT_MS:
        time.sleep((_RATE_LIMIT_MS - elapsed_ms) / 1000.0)
    _LAST_API_CALL = time.monotonic()


def _get_cached(key: str) -> Optional[Any]:
    """Get value from cache if not expired."""
    if key in _CACHE:
        ts, val = _CACHE[key]
        if time.time() - ts < _CACHE_TTL:
            return val
        del _CACHE[key]
    return None


def _set_cached(key: str, val: Any):
    """Store value in cache with current timestamp."""
    _CACHE[key] = (time.time(), val)


def _create_ssl_ctx():
    """Create a permissive SSL context for urllib."""
    ctx = ssl.create_default_context()
    try:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    except Exception:
        pass
    return ctx


def _fetch_json(url: str, timeout: int = 10) -> Optional[Any]:
    """Fetch JSON from URL with timeout. Returns None on failure."""
    _rate_limit()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
        ctx = _create_ssl_ctx()
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read()
            return json.loads(raw.decode("utf-8", errors="replace"))
    except Exception as e:
        logger.debug("Fetch failed %s: %s", url, e)
        return None


# ---------------------------------------------------------------------------
# Data fetching with failover
# ---------------------------------------------------------------------------

def _normalize_symbol(symbol: str) -> str:
    """Normalize symbol to Binance format: BTCUSDT, ETHUSDT, etc."""
    s = symbol.upper().replace("-", "").replace("/", "").replace(" ", "")
    # BTC-USD -> BTCUSD -> BTCUSDT
    if s.endswith("USD") and not s.endswith("USDT") and not s.endswith("USDC"):
        s = s + "T"
    return s


def fetch_klines(symbol: str, interval: str = "1h", limit: int = 200) -> Optional[list]:
    """Fetch klines from Binance with 5-mirror failover.

    Each kline: [open_time, open, high, low, close, volume, close_time, ...]
    Returns list of klines or None on total failure.
    """
    binance_sym = _normalize_symbol(symbol)
    cache_key = f"klines:{binance_sym}:{interval}:{limit}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    for mirror in BINANCE_KLINE_MIRRORS:
        url = f"{mirror}/api/v3/klines?symbol={binance_sym}&interval={interval}&limit={limit}"
        data = _fetch_json(url)
        if data and isinstance(data, list) and len(data) > 10:
            _set_cached(cache_key, data)
            return data

    # If standard symbol fails, try without trailing T
    if binance_sym.endswith("USDT"):
        alt = binance_sym[:-1]  # Try BTCUSD
        for mirror in BINANCE_KLINE_MIRRORS[:2]:
            url = f"{mirror}/api/v3/klines?symbol={alt}&interval={interval}&limit={limit}"
            data = _fetch_json(url)
            if data and isinstance(data, list) and len(data) > 10:
                _set_cached(cache_key, data)
                return data

    logger.debug("All kline mirrors failed for %s", binance_sym)
    return None


def _extract_ohlcv(klines: list) -> tuple[list, list, list, list, list]:
    """Extract opens, highs, lows, closes, volumes from Binance klines."""
    opens, highs, lows, closes, volumes = [], [], [], [], []
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
# Technical indicator computations (stdlib only, no numpy/pandas)
# ---------------------------------------------------------------------------

def _wilder_smooth(values: list[float], period: int) -> list[float]:
    """Wilder smoothing (used by RSI). First value is SMA, then EMA with alpha=1/period."""
    if len(values) < period:
        return [float("nan")] * len(values)
    result = [float("nan")] * len(values)
    result[period - 1] = sum(values[:period]) / period
    alpha = 1.0 / period
    for i in range(period, len(values)):
        result[i] = alpha * values[i] + (1 - alpha) * result[i - 1]
    return result


def _ema(values: list[float], span: int) -> list[float]:
    """Exponential moving average."""
    if not values:
        return []
    alpha = 2.0 / (span + 1)
    result = [values[0]]
    for i in range(1, len(values)):
        result.append(alpha * values[i] + (1 - alpha) * result[-1])
    return result


def _sma_last(values: list[float], period: int) -> float:
    """Simple moving average of last `period` values."""
    if len(values) < period:
        return float("nan")
    return sum(values[-period:]) / period


def compute_rsi(closes: list[float], period: int = 14) -> float:
    """RSI with Wilder smoothing, returns 0-100."""
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]
    avg_gain = _wilder_smooth(gains, period)
    avg_loss = _wilder_smooth(losses, period)
    g = avg_gain[-1]
    l_val = avg_loss[-1]
    if math.isnan(g) or math.isnan(l_val):
        return 50.0
    if l_val == 0:
        return 100.0 if g > 0 else 50.0
    rs = g / l_val
    return 100.0 - (100.0 / (1.0 + rs))


def compute_atr(highs: list[float], lows: list[float], closes: list[float],
                period: int = 14) -> float:
    """Average True Range as percentage of current price."""
    if len(closes) < period + 1 or len(highs) < period + 1 or len(lows) < period + 1:
        return 0.0
    trs = []
    for i in range(1, len(closes)):
        h = highs[i]
        l = lows[i]
        pc = closes[i - 1]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
    if len(trs) < period:
        return 0.0
    smoothed = _wilder_smooth(trs, period)
    atr_val = smoothed[-1]
    if math.isnan(atr_val):
        return 0.0
    price = closes[-1]
    if price == 0:
        return 0.0
    return atr_val / price


def compute_volume_ratio(volumes: list[float], period: int = 20) -> float:
    """Current volume / SMA(period) volume."""
    if len(volumes) < period:
        return 1.0
    avg = sum(volumes[-period:]) / period
    if avg == 0:
        return 1.0
    return volumes[-1] / avg


def compute_regime(closes: list[float], sma_period: int = 50) -> int:
    """1 if price > SMA50, -1 if below, 0 if within 0.5%."""
    if len(closes) < sma_period:
        return 0
    sma = sum(closes[-sma_period:]) / sma_period
    if sma == 0:
        return 0
    ratio = closes[-1] / sma
    if ratio > 1.005:
        return 1
    elif ratio < 0.995:
        return -1
    return 0


def compute_vwap_deviation(highs: list[float], lows: list[float],
                            closes: list[float], volumes: list[float]) -> float:
    """(price - VWAP) / price as decimal. Uses intraday approximation."""
    if len(closes) < 20 or len(volumes) < 20:
        return 0.0
    # Use last 20 bars for VWAP approximation
    n = min(len(closes), 20)
    cum_vol = 0.0
    cum_pv = 0.0
    for i in range(-n, 0):
        tp = (highs[i] + lows[i] + closes[i]) / 3.0
        v = volumes[i]
        cum_vol += v
        cum_pv += tp * v
    if cum_vol == 0:
        return 0.0
    vwap = cum_pv / cum_vol
    price = closes[-1]
    if price == 0:
        return 0.0
    return (price - vwap) / price


def compute_garman_klass(opens: list[float], highs: list[float],
                         lows: list[float], closes: list[float],
                         period: int = 20) -> float:
    """Garman-Klass volatility: 0.5*ln(H/L)^2 - (2ln2-1)*ln(C/O)^2, averaged over period."""
    if len(opens) < period or len(highs) < period or len(lows) < period or len(closes) < period:
        return 0.0
    gk_sum = 0.0
    count = 0
    for i in range(-period, 0):
        o = opens[i]
        h = highs[i]
        l = lows[i]
        c = closes[i]
        if o <= 0 or h <= 0 or l <= 0 or c <= 0 or l >= h:
            continue
        ln_hl = math.log(h / l)
        ln_co = math.log(c / o)
        gk = 0.5 * ln_hl * ln_hl - (2.0 * math.log(2.0) - 1.0) * ln_co * ln_co
        gk_sum += gk
        count += 1
    if count == 0:
        return 0.0
    avg_gk = gk_sum / count
    # Take sqrt and normalize to [0, 1] range (typical crypto GK vol is 0.01-0.10)
    vol = math.sqrt(max(avg_gk, 0.0))
    return max(0.0, min(1.0, vol / 0.15))


def compute_mom30(closes: list[float]) -> float:
    """30-period momentum: (close[-1] / close[-31]) - 1, clipped to [-0.5, 0.5]."""
    if len(closes) < 31:
        return 0.0
    if closes[-31] == 0:
        return 0.0
    mom = (closes[-1] / closes[-31]) - 1.0
    return max(-0.5, min(0.5, mom))


def compute_rsi30(closes: list[float]) -> float:
    """30-period RSI with Wilder smoothing, normalized to [0, 1]."""
    return compute_rsi(closes, 30) / 100.0


def compute_macd_hist_norm(closes: list[float]) -> float:
    """MACD histogram normalized by price, clipped [-0.05, 0.05]."""
    if len(closes) < 35:
        return 0.0
    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    macd_line = [e12 - e26 for e12, e26 in zip(ema12, ema26)]
    signal_line = _ema(macd_line, 9)
    histogram = macd_line[-1] - signal_line[-1]
    price = closes[-1]
    if price == 0:
        return 0.0
    normalized = histogram / price
    return max(-0.05, min(0.05, normalized))


def compute_stoch_k30(closes: list[float], highs: list[float], lows: list[float]) -> float:
    """30-period Stochastic %K."""
    period = 30
    if len(closes) < period or len(highs) < period or len(lows) < period:
        return 0.5
    highest = max(highs[-period:])
    lowest = min(lows[-period:])
    rng = highest - lowest
    if rng == 0:
        return 0.5
    k = (closes[-1] - lowest) / rng
    return max(0.0, min(1.0, k))


def compute_stoch_d30(closes: list[float], highs: list[float], lows: list[float]) -> float:
    """3-period SMA of %K30 (Stochastic %D)."""
    period_k = 30
    period_d = 3
    needed = period_k + period_d - 1
    if len(closes) < needed or len(highs) < needed or len(lows) < needed:
        return 0.5
    k_values = []
    for offset in range(period_d):
        idx = len(closes) - period_d + offset + 1
        start = idx - period_k
        if start < 0:
            k_values.append(0.5)
            continue
        highest = max(highs[start:idx])
        lowest = min(lows[start:idx])
        rng = highest - lowest
        if rng == 0:
            k_values.append(0.5)
        else:
            k = (closes[idx - 1] - lowest) / rng
            k_values.append(max(0.0, min(1.0, k)))
    return max(0.0, min(1.0, sum(k_values) / len(k_values)))


def compute_cci20_norm(closes: list[float], highs: list[float], lows: list[float]) -> float:
    """CCI(20) normalized to [-1, 1]."""
    period = 20
    if len(closes) < period or len(highs) < period or len(lows) < period:
        return 0.0
    tp_values = [(highs[-(period - i)] + lows[-(period - i)] + closes[-(period - i)]) / 3.0
                 for i in range(period)]
    tp_current = tp_values[-1]
    tp_mean = sum(tp_values) / period
    mean_dev = sum(abs(tp - tp_mean) for tp in tp_values) / period
    if mean_dev == 0:
        return 0.0
    cci = (tp_current - tp_mean) / (0.015 * mean_dev)
    return max(-1.0, min(1.0, max(-3.0, min(3.0, cci)) / 3.0))


def compute_williams_r(closes: list[float], highs: list[float], lows: list[float]) -> float:
    """Williams %R(14), range [-1, 0]."""
    period = 14
    if len(closes) < period or len(highs) < period or len(lows) < period:
        return -0.5
    highest = max(highs[-period:])
    lowest = min(lows[-period:])
    rng = highest - lowest
    if rng == 0:
        return -0.5
    wr = -1.0 * (highest - closes[-1]) / rng
    return max(-1.0, min(0.0, wr))


# ---------------------------------------------------------------------------
# External data fetching
# ---------------------------------------------------------------------------

def fetch_fear_greed() -> float:
    """Fetch Fear & Greed index from alternative.me, normalized 0-1."""
    cache_key = "fear_greed"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    data = _fetch_json(FEAR_GREED_URL)
    if data and isinstance(data, dict):
        try:
            val = float(data["data"][0]["value"])
            result = max(0.0, min(1.0, val / 100.0))
            _set_cached(cache_key, result)
            return result
        except (KeyError, IndexError, TypeError, ValueError):
            pass
    return 0.5  # neutral default


def fetch_funding_rate(symbol: str) -> float:
    """Fetch funding rate from Binance futures API."""
    binance_sym = _normalize_symbol(symbol)
    cache_key = f"funding:{binance_sym}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    for mirror in BINANCE_FAPI_MIRRORS:
        url = f"{mirror}/fapi/v1/premiumIndex?symbol={binance_sym}"
        data = _fetch_json(url)
        if data and isinstance(data, dict):
            try:
                rate = float(data.get("lastFundingRate", 0))
                _set_cached(cache_key, rate)
                return rate
            except (TypeError, ValueError):
                pass

    return 0.0  # default


def fetch_orderbook_imbalance(symbol: str, limit: int = 20) -> float:
    """Fetch orderbook imbalance from Binance depth API.

    Returns bid_volume / (bid_volume + ask_volume) mapped to [-1, 1].
    > 0 means more bids (bullish), < 0 means more asks (bearish).
    """
    binance_sym = _normalize_symbol(symbol)
    cache_key = f"obi:{binance_sym}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    for mirror in BINANCE_KLINE_MIRRORS[:3]:
        url = f"{mirror}/api/v3/depth?symbol={binance_sym}&limit={limit}"
        data = _fetch_json(url)
        if data and isinstance(data, dict) and "bids" in data and "asks" in data:
            try:
                bid_vol = sum(float(b[1]) for b in data["bids"])
                ask_vol = sum(float(a[1]) for a in data["asks"])
                total = bid_vol + ask_vol
                if total == 0:
                    break
                # Map from [0, 1] ratio to [-1, 1] imbalance
                imbalance = 2.0 * (bid_vol / total) - 1.0
                result = max(-1.0, min(1.0, imbalance))
                _set_cached(cache_key, result)
                return result
            except (TypeError, ValueError, IndexError):
                pass

    return 0.0  # default


def _compute_cs_momentum_rank(symbol: str, closes_map: dict[str, list[float]]) -> float:
    """Rank this symbol's 7d return among all symbols (0-1).

    Uses last 168 bars of 1H data (7 days).
    """
    if symbol not in closes_map:
        return 0.5

    # Compute 7d returns for all symbols
    returns = {}
    for sym, cls in closes_map.items():
        if len(cls) < 168:
            if len(cls) >= 24:
                # Fallback: use available data
                ret = (cls[-1] / cls[0] - 1.0) if cls[0] != 0 else 0.0
            else:
                continue
        else:
            ret = (cls[-1] / cls[-168] - 1.0) if cls[-168] != 0 else 0.0
        returns[sym] = ret

    if symbol not in returns or len(returns) < 2:
        return 0.5

    target_ret = returns[symbol]
    all_rets = list(returns.values())
    n_below = sum(1 for r in all_rets if r <= target_ret)
    return max(0.0, min(1.0, n_below / len(all_rets)))


# ---------------------------------------------------------------------------
# BTC correlation & change features (Phase 17 -- strongest missing predictor)
# ---------------------------------------------------------------------------

def compute_btc_correlation(closes: list[float], btc_closes: Optional[list[float]],
                            period: int = 30) -> float:
    """Compute Pearson correlation between symbol's returns and BTC returns.

    Uses last `period` hourly returns from 1H closes.
    Returns correlation in [-1.0, 1.0]. Default 0.8 if insufficient data.
    Most alts have 0.6-0.9 correlation with BTC; this is the strongest
    missing predictor per ML_BLUEPRINT Section 9.
    """
    if not btc_closes or len(btc_closes) < period + 1 or len(closes) < period + 1:
        return 0.8  # typical alt-BTC correlation

    # Use last (period+1) closes to get `period` returns
    n = min(len(closes), len(btc_closes), period + 1)
    sym_returns = []
    btc_returns = []
    for i in range(1, n):
        if closes[-(n - i) - 1] != 0 and btc_closes[-(n - i) - 1] != 0:
            sym_returns.append((closes[-(n - i)] / closes[-(n - i) - 1]) - 1.0)
            btc_returns.append((btc_closes[-(n - i)] / btc_closes[-(n - i) - 1]) - 1.0)

    if len(sym_returns) < 10:
        return 0.8

    k = len(sym_returns)
    mean_s = sum(sym_returns) / k
    mean_b = sum(btc_returns) / k
    cov = sum((s - mean_s) * (b - mean_b) for s, b in zip(sym_returns, btc_returns)) / k
    std_s = math.sqrt(sum((s - mean_s) ** 2 for s in sym_returns) / k)
    std_b = math.sqrt(sum((b - mean_b) ** 2 for b in btc_returns) / k)

    if std_s == 0 or std_b == 0:
        return 0.8

    corr = cov / (std_s * std_b)
    return max(-1.0, min(1.0, corr))


def _compute_btc_24h_change(btc_closes: Optional[list[float]]) -> Optional[float]:
    """Compute BTC 24h percentage change from hourly closes.

    Uses close[-1] vs close[-25] (24 bars back on 1H data).
    Returns percentage change or None if data unavailable.
    """
    if not btc_closes or len(btc_closes) < 25:
        return None
    if btc_closes[-25] == 0:
        return None
    return ((btc_closes[-1] / btc_closes[-25]) - 1.0) * 100.0


# ---------------------------------------------------------------------------
# Main feature population functions
# ---------------------------------------------------------------------------

def populate_features(pick: dict, closes_map: Optional[dict[str, list[float]]] = None,
                      btc_closes: Optional[list[float]] = None) -> dict:
    """Populate all ML features on a pick dict.

    Args:
        pick: signal/pick dict with at least 'symbol' key
        closes_map: optional {symbol: closes_list} for cross-sectional features
        btc_closes: optional BTC close prices for correlation computation

    Returns:
        The same pick dict with features added/updated.
    """
    symbol = pick.get("symbol", "")
    if not symbol:
        return pick

    # Fetch klines
    klines = fetch_klines(symbol)
    if not klines:
        logger.debug("No klines for %s, using defaults", symbol)
        return pick

    opens, highs, lows, closes, volumes = _extract_ohlcv(klines)
    if len(closes) < 15:
        return pick

    price = closes[-1]

    # --- RSI at entry (0-100 scale for ml_ranker fallback chain) ---
    try:
        pick["rsi_at_entry"] = round(compute_rsi(closes, 14), 2)
    except Exception:
        pass

    # --- Volume ratio ---
    try:
        pick["volume_ratio"] = round(compute_volume_ratio(volumes, 20), 4)
    except Exception:
        pass

    # --- ATR at entry (as % of price) ---
    try:
        pick["atr_at_entry"] = round(compute_atr(highs, lows, closes, 14), 6)
    except Exception:
        pass

    # --- Regime encoded ---
    try:
        pick["regime_encoded"] = compute_regime(closes, 50)
        # Also set regime_at_entry for the ml_ranker fallback chain
        regime_val = pick["regime_encoded"]
        if regime_val == 1:
            pick["regime_at_entry"] = "bullish"
        elif regime_val == -1:
            pick["regime_at_entry"] = "bearish"
        else:
            pick["regime_at_entry"] = "neutral"
    except Exception:
        pass

    # --- Close to VWAP ---
    try:
        vwap_dev = compute_vwap_deviation(highs, lows, closes, volumes)
        pick["vwap_deviation"] = round(max(-1.0, min(1.0, vwap_dev)), 6)
        pick["close_to_vwap"] = pick["vwap_deviation"]
    except Exception:
        pass

    # --- Garman-Klass volatility ---
    try:
        gk = compute_garman_klass(opens, highs, lows, closes, 20)
        pick["gk_vol"] = round(gk, 6)
        pick["garman_klass_vol"] = pick["gk_vol"]
    except Exception:
        pass

    # --- Fear & Greed index (shared across all picks) ---
    try:
        fng = fetch_fear_greed()
        pick["fear_greed"] = round(fng * 100, 1)  # Store as 0-100 for ml_ranker normalization
        pick["fear_greed_norm"] = round(fng, 4)
    except Exception:
        pass

    # --- Funding rate ---
    try:
        fr = fetch_funding_rate(symbol)
        pick["funding_rate"] = fr
        pick["funding_rate_raw"] = fr
    except Exception:
        pass

    # --- 30-period momentum ---
    try:
        pick["mom30"] = round(compute_mom30(closes), 6)
    except Exception:
        pass

    # --- RSI(30) normalized 0-1 ---
    try:
        pick["rsi30"] = round(compute_rsi30(closes), 4)
    except Exception:
        pass

    # --- MACD histogram normalized ---
    try:
        pick["macd_hist_norm"] = round(compute_macd_hist_norm(closes), 6)
    except Exception:
        pass

    # --- Stochastic K/D (30-period) ---
    try:
        pick["stoch_k30"] = round(compute_stoch_k30(closes, highs, lows), 4)
    except Exception:
        pass
    try:
        pick["stoch_d30"] = round(compute_stoch_d30(closes, highs, lows), 4)
    except Exception:
        pass

    # --- CCI(20) normalized ---
    try:
        pick["cci20_norm"] = round(compute_cci20_norm(closes, highs, lows), 4)
    except Exception:
        pass

    # --- Williams %R ---
    try:
        pick["williams_r"] = round(compute_williams_r(closes, highs, lows), 4)
    except Exception:
        pass

    # --- Cross-sectional momentum rank ---
    try:
        if closes_map:
            pick["cs_momentum_rank"] = round(
                _compute_cs_momentum_rank(symbol, closes_map), 4
            )
    except Exception:
        pass

    # --- Orderbook imbalance ---
    try:
        obi = fetch_orderbook_imbalance(symbol)
        pick["orderbook_imbalance"] = round(obi, 4)
    except Exception:
        pass

    # --- BTC correlation (30-period rolling Pearson with BTCUSDT returns) ---
    try:
        btc_corr = compute_btc_correlation(closes, btc_closes)
        pick["btc_correlation"] = round(btc_corr, 4)
    except Exception:
        # Default 0.8: most alts are highly correlated with BTC
        if "btc_correlation" not in pick:
            pick["btc_correlation"] = 0.8

    # --- Hurst exponent (long-range dependence / regime detection) ---
    try:
        from hurst_exponent import compute_hurst
        if len(closes) >= 20:
            h_val = compute_hurst(closes)
            pick["hurst_exponent"] = round(h_val, 4)
    except Exception:
        pass

    # --- Wavelet trend strength + momentum ---
    try:
        from wavelet_trend import detect_trend_wavelet, wavelet_momentum as _wm
        if len(closes) >= 8:
            _wt = detect_trend_wavelet(closes, timeframe="4h")
            pick["wavelet_trend_strength"] = round(_wt.get("trend_strength", 0.0), 4)
            pick["wavelet_momentum"] = round(_wm(closes), 4)
    except Exception:
        pass

    # --- BTC 24h change (injected by scanner from market_ctx, or computed here) ---
    try:
        if "btc_24h_change" not in pick or pick["btc_24h_change"] is None:
            btc_chg = _compute_btc_24h_change(btc_closes)
            if btc_chg is not None:
                pick["btc_24h_change"] = round(btc_chg, 4)
    except Exception:
        pass

    # --- PCA factor model (multi-asset factor exposure + diversification) ---
    try:
        from pca_factor_model import get_pca_signal
        if closes_map and len(closes_map) >= 3:
            pca_sig = get_pca_signal(sym, closes_map)
            if pca_sig:
                pick["pca_market_exposure"] = pca_sig.get("pca_market_exposure", 0.5)
                pick["pca_diversification"] = pca_sig.get("pca_diversification", 0.5)
    except Exception:
        pass

    # --- Also populate ml_features_at_entry for the preferred fallback path ---
    mf = pick.get("ml_features_at_entry") or {}
    mf["rsi_14"] = pick.get("rsi_at_entry", mf.get("rsi_14"))
    mf["volume_ratio"] = pick.get("volume_ratio", mf.get("volume_ratio"))
    mf["atr_pct"] = pick.get("atr_at_entry", mf.get("atr_pct"))
    mf["mom30"] = pick.get("mom30", mf.get("mom30"))
    mf["rsi30"] = pick.get("rsi30", mf.get("rsi30"))
    mf["macd_hist_norm"] = pick.get("macd_hist_norm", mf.get("macd_hist_norm"))
    mf["stoch_k30"] = pick.get("stoch_k30", mf.get("stoch_k30"))
    mf["stoch_d30"] = pick.get("stoch_d30", mf.get("stoch_d30"))
    mf["cci20_norm"] = pick.get("cci20_norm", mf.get("cci20_norm"))
    mf["williams_r"] = pick.get("williams_r", mf.get("williams_r"))
    mf["funding_rate_raw"] = pick.get("funding_rate_raw", mf.get("funding_rate_raw"))
    mf["orderbook_imbalance"] = pick.get("orderbook_imbalance", mf.get("orderbook_imbalance"))
    mf["btc_correlation"] = pick.get("btc_correlation", mf.get("btc_correlation"))
    mf["btc_24h_change"] = pick.get("btc_24h_change", mf.get("btc_24h_change"))
    mf["hurst_exponent"] = pick.get("hurst_exponent", mf.get("hurst_exponent"))
    mf["wavelet_trend_strength"] = pick.get("wavelet_trend_strength", mf.get("wavelet_trend_strength"))
    mf["wavelet_momentum"] = pick.get("wavelet_momentum", mf.get("wavelet_momentum"))
    mf["pca_market_exposure"] = pick.get("pca_market_exposure", mf.get("pca_market_exposure"))
    mf["pca_diversification"] = pick.get("pca_diversification", mf.get("pca_diversification"))
    pick["ml_features_at_entry"] = mf

    return pick


def populate_batch(picks: list[dict]) -> list[dict]:
    """Populate features for a batch of picks efficiently.

    Shares kline cache across picks and builds a cross-sectional
    closes map for momentum ranking.

    Args:
        picks: list of signal/pick dicts

    Returns:
        Same list with features populated on each pick.
    """
    if not picks:
        return picks

    t0 = time.time()

    # Collect unique symbols
    symbols = list({p.get("symbol", "") for p in picks if p.get("symbol")})

    # Pre-fetch all klines (cache will prevent redundant calls)
    closes_map: dict[str, list[float]] = {}
    fetched = 0
    for sym in symbols:
        klines = fetch_klines(sym)
        if klines:
            _, _, _, closes, _ = _extract_ohlcv(klines)
            if closes:
                closes_map[sym] = closes
                fetched += 1

    # Also fetch top 20 symbols for cross-sectional ranking context
    top20 = [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
        "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT",
        "LINKUSDT", "UNIUSDT", "LTCUSDT", "ATOMUSDT", "NEARUSDT",
        "APTUSDT", "ARBUSDT", "OPUSDT", "SUIUSDT", "SEIUSDT",
    ]
    for sym in top20:
        if sym not in closes_map:
            klines = fetch_klines(sym)
            if klines:
                _, _, _, closes, _ = _extract_ohlcv(klines)
                if closes:
                    closes_map[sym] = closes

    # Pre-fetch BTC closes for correlation computation (shared across all picks)
    btc_closes = closes_map.get("BTCUSDT")
    if btc_closes is None:
        btc_klines = fetch_klines("BTCUSDT")
        if btc_klines:
            _, _, _, btc_closes, _ = _extract_ohlcv(btc_klines)
            if btc_closes:
                closes_map["BTCUSDT"] = btc_closes

    # Populate each pick
    populated = 0
    for pick in picks:
        try:
            populate_features(pick, closes_map, btc_closes=btc_closes)
            populated += 1
        except Exception as e:
            logger.debug("Feature population failed for %s: %s", pick.get("symbol"), e)

    elapsed = time.time() - t0
    print(f"  [FEATURE POPULATOR] {populated}/{len(picks)} picks enriched "
          f"({fetched}/{len(symbols)} symbols fetched, "
          f"{len(closes_map)} in cross-sectional universe, "
          f"{elapsed:.1f}s)")

    return picks


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    test_pick = {"symbol": "BTCUSDT", "strategy": "test", "confidence": 0.7}
    print("Before:", {k: v for k, v in test_pick.items() if k != "ml_features_at_entry"})
    populate_features(test_pick)
    print("\nAfter:")
    for k, v in sorted(test_pick.items()):
        if k == "ml_features_at_entry":
            print(f"  {k}:")
            for mk, mv in sorted(v.items()):
                print(f"    {mk}: {mv}")
        else:
            print(f"  {k}: {v}")
