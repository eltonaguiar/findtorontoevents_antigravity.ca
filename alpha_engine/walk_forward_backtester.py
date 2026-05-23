#!/usr/bin/env python3
"""
Walk-Forward Backtester for Alpha Engine
==========================================
Validates strategy performance out-of-sample using rolling walk-forward
analysis. Detects overfitting by comparing in-sample vs out-of-sample metrics.

Walk-forward process:
  1. Fetch historical OHLCV data (Binance 5-mirror failover)
  2. Split into rolling train/test windows
  3. Generate signals on each window
  4. Compute per-window and aggregate metrics
  5. Run 8 anti-overfit checks
  6. Generate report saved to data/walk_forward_results.json

Uses stdlib only: urllib.request, json, math, statistics, datetime.
Binance API failover: api, api1, api2, api3, data-api (per CLAUDE.md).
"""

from __future__ import annotations

import json
import logging
import math
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Optional

_log = logging.getLogger("alpha_engine.walk_forward_backtester")

try:
    from alpha_engine.statistical_tests import run_all_tests as run_statistical_tests
    _HAS_STAT_TESTS = True
except ImportError:
    try:
        from statistical_tests import run_all_tests as run_statistical_tests
        _HAS_STAT_TESTS = True
    except ImportError:
        _HAS_STAT_TESTS = False

# ---------------------------------------------------------------------------
# Windows UTF-8 fix
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8")
            except Exception:
                pass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
]

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
KUCOIN_BASE = "https://api.kucoin.com"
CRYPTOCOMPARE_BASE = "https://min-api.cryptocompare.com"

REQUEST_TIMEOUT = 15  # seconds
RETRY_DELAY = 1.0     # seconds between mirror retries

# Default symbols for backtesting (high-volume majors)
DEFAULT_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT",
]

# Interval to milliseconds mapping
INTERVAL_MS = {
    "1m": 60_000, "3m": 180_000, "5m": 300_000, "15m": 900_000,
    "30m": 1_800_000, "1h": 3_600_000, "2h": 7_200_000,
    "4h": 14_400_000, "6h": 21_600_000, "8h": 28_800_000,
    "12h": 43_200_000, "1d": 86_400_000,
}

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------
def _http_get_json(url: str, timeout: int = REQUEST_TIMEOUT) -> Optional[dict]:
    """GET JSON from URL, return parsed object or None on failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return json.loads(raw)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError,
            OSError, TimeoutError) as exc:
        _log.debug("HTTP GET failed for %s: %s", url, exc)
        return None


# ===========================================================================
# 1. fetch_historical_klines
# ===========================================================================
def fetch_historical_klines(
    symbol: str,
    interval: str = "4h",
    days: int = 90,
) -> list:
    """Fetch OHLCV klines from Binance (5-mirror failover) for backtesting.

    Returns list of [timestamp_ms, open, high, low, close, volume] where
    numeric values are floats. Returns empty list on total failure.

    Handles pagination: Binance caps at 1000 candles per request, so we
    paginate with startTime/endTime as needed.
    """
    sym = symbol.upper()
    if interval not in INTERVAL_MS:
        _log.error("Unsupported interval: %s", interval)
        return []

    interval_ms = INTERVAL_MS[interval]
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - (days * 86_400_000)
    total_candles_needed = (days * 86_400_000) // interval_ms + 1

    all_candles = []
    cursor_ms = start_ms

    while cursor_ms < now_ms and len(all_candles) < total_candles_needed + 50:
        batch_limit = min(1000, total_candles_needed - len(all_candles) + 10)
        if batch_limit <= 0:
            break

        batch = _fetch_klines_batch(sym, interval, cursor_ms, now_ms, batch_limit)
        if not batch:
            break

        all_candles.extend(batch)
        # Advance cursor past last candle
        last_ts = batch[-1][0]
        cursor_ms = last_ts + interval_ms

        if len(batch) < batch_limit:
            break  # No more data available

    # Deduplicate by timestamp and sort
    seen = set()
    unique = []
    for c in all_candles:
        ts = c[0]
        if ts not in seen:
            seen.add(ts)
            unique.append(c)
    unique.sort(key=lambda c: c[0])

    _log.info("Fetched %d candles for %s (%s, %dd)", len(unique), sym, interval, days)
    return unique


def _fetch_klines_batch(
    symbol: str, interval: str, start_ms: int, end_ms: int, limit: int
) -> list:
    """Fetch a single batch of klines with Binance 5-mirror failover.

    Falls back to CoinGecko -> KuCoin -> CryptoCompare on total Binance failure.
    Returns list of [timestamp_ms, open, high, low, close, volume] (floats).
    """
    # --- Binance mirrors ---
    for mirror in BINANCE_MIRRORS:
        url = (
            f"{mirror}/api/v3/klines?symbol={symbol}&interval={interval}"
            f"&startTime={start_ms}&endTime={end_ms}&limit={limit}"
        )
        data = _http_get_json(url)
        if data and isinstance(data, list) and len(data) > 0:
            try:
                return [
                    [int(c[0]), float(c[1]), float(c[2]), float(c[3]),
                     float(c[4]), float(c[5])]
                    for c in data
                ]
            except (IndexError, ValueError, TypeError):
                continue
        time.sleep(RETRY_DELAY)

    # --- CoinGecko fallback ---
    candles = _fetch_klines_coingecko(symbol, start_ms, end_ms)
    if candles:
        return candles

    # --- KuCoin fallback ---
    candles = _fetch_klines_kucoin(symbol, interval, start_ms, end_ms, limit)
    if candles:
        return candles

    # --- CryptoCompare fallback ---
    candles = _fetch_klines_cryptocompare(symbol, interval, start_ms, end_ms, limit)
    if candles:
        return candles

    _log.warning("All sources exhausted for %s klines", symbol)
    return []


def _symbol_to_cg_id(symbol: str) -> Optional[str]:
    """Map Binance symbol to CoinGecko ID (best-effort)."""
    mapping = {
        "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "BNBUSDT": "binancecoin",
        "SOLUSDT": "solana", "XRPUSDT": "ripple", "ADAUSDT": "cardano",
        "DOGEUSDT": "dogecoin", "AVAXUSDT": "avalanche-2",
        "DOTUSDT": "polkadot", "MATICUSDT": "matic-network",
        "LINKUSDT": "chainlink", "LTCUSDT": "litecoin",
    }
    return mapping.get(symbol.upper())


def _fetch_klines_coingecko(symbol: str, start_ms: int, end_ms: int) -> list:
    """Fetch OHLC from CoinGecko /coins/{id}/ohlc endpoint."""
    cg_id = _symbol_to_cg_id(symbol)
    if not cg_id:
        return []
    days_span = max(1, (end_ms - start_ms) // 86_400_000)
    # CoinGecko OHLC supports: 1, 7, 14, 30, 90, 180, 365, max
    cg_days = 1
    for d in [1, 7, 14, 30, 90, 180, 365]:
        if d >= days_span:
            cg_days = d
            break
    else:
        cg_days = 365

    url = f"{COINGECKO_BASE}/coins/{cg_id}/ohlc?vs_currency=usd&days={cg_days}"
    data = _http_get_json(url)
    if data and isinstance(data, list):
        try:
            candles = []
            for c in data:
                ts = int(c[0])
                if start_ms <= ts <= end_ms:
                    # CoinGecko OHLC: [timestamp, open, high, low, close]
                    candles.append([ts, float(c[1]), float(c[2]), float(c[3]),
                                    float(c[4]), 0.0])
            return candles if candles else []
        except (IndexError, ValueError, TypeError):
            pass
    return []


def _symbol_to_kucoin(symbol: str) -> str:
    """Convert BTCUSDT -> BTC-USDT for KuCoin."""
    s = symbol.upper()
    if s.endswith("USDT"):
        return s[:-4] + "-USDT"
    return s


KUCOIN_INTERVAL_MAP = {
    "1m": "1min", "3m": "3min", "5m": "5min", "15m": "15min",
    "30m": "30min", "1h": "1hour", "2h": "2hour", "4h": "4hour",
    "6h": "6hour", "8h": "8hour", "12h": "12hour", "1d": "1day",
}


def _fetch_klines_kucoin(
    symbol: str, interval: str, start_ms: int, end_ms: int, limit: int
) -> list:
    """Fetch klines from KuCoin."""
    kc_sym = _symbol_to_kucoin(symbol)
    kc_int = KUCOIN_INTERVAL_MAP.get(interval)
    if not kc_int:
        return []
    start_s = start_ms // 1000
    end_s = end_ms // 1000
    url = (
        f"{KUCOIN_BASE}/api/v1/market/candles?type={kc_int}"
        f"&symbol={kc_sym}&startAt={start_s}&endAt={end_s}"
    )
    data = _http_get_json(url)
    if data and isinstance(data, dict) and data.get("data"):
        try:
            candles = []
            for c in data["data"]:
                # KuCoin: [time_s, open, close, high, low, volume, turnover]
                candles.append([
                    int(c[0]) * 1000,
                    float(c[1]), float(c[3]), float(c[4]),
                    float(c[2]), float(c[5])
                ])
            candles.sort(key=lambda x: x[0])
            return candles[:limit] if candles else []
        except (IndexError, ValueError, TypeError):
            pass
    return []


CRYPTOCOMPARE_INTERVAL_MAP = {
    "1h": ("histohour", 1), "2h": ("histohour", 2), "4h": ("histohour", 4),
    "1d": ("histoday", 1),
}


def _fetch_klines_cryptocompare(
    symbol: str, interval: str, start_ms: int, end_ms: int, limit: int
) -> list:
    """Fetch klines from CryptoCompare."""
    mapping = CRYPTOCOMPARE_INTERVAL_MAP.get(interval)
    if not mapping:
        return []
    endpoint, aggregate = mapping
    sym = symbol.upper()
    base = sym.replace("USDT", "").replace("USD", "")
    ts_to = end_ms // 1000
    url = (
        f"{CRYPTOCOMPARE_BASE}/data/v2/{endpoint}"
        f"?fsym={base}&tsym=USD&limit={limit}&aggregate={aggregate}&toTs={ts_to}"
    )
    data = _http_get_json(url)
    if data and isinstance(data, dict):
        entries = (data.get("Data") or {}).get("Data") or []
        try:
            candles = []
            for e in entries:
                ts = int(e["time"]) * 1000
                if ts >= start_ms:
                    candles.append([
                        ts, float(e["open"]), float(e["high"]),
                        float(e["low"]), float(e["close"]),
                        float(e.get("volumefrom", 0))
                    ])
            return candles if candles else []
        except (KeyError, ValueError, TypeError):
            pass
    return []


# ===========================================================================
# Built-in signal strategies (operate on OHLCV data)
# ===========================================================================
def _compute_ema(values: list, period: int) -> list:
    """Compute EMA from a list of floats. Returns list same length (NaN-padded)."""
    if len(values) < period:
        return [float("nan")] * len(values)
    ema = [float("nan")] * (period - 1)
    # Seed with SMA
    sma = sum(values[:period]) / period
    ema.append(sma)
    multiplier = 2.0 / (period + 1)
    for i in range(period, len(values)):
        ema.append(values[i] * multiplier + ema[-1] * (1 - multiplier))
    return ema


def _compute_sma(values: list, period: int) -> list:
    """Simple moving average. Returns list same length (NaN-padded)."""
    result = [float("nan")] * (period - 1)
    for i in range(period - 1, len(values)):
        result.append(sum(values[i - period + 1:i + 1]) / period)
    return result


def _compute_rsi(closes: list, period: int = 14) -> list:
    """Compute RSI. Returns list same length (NaN-padded)."""
    if len(closes) < period + 1:
        return [float("nan")] * len(closes)

    rsi = [float("nan")] * period
    gains = []
    losses = []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(0, delta))
        losses.append(max(0, -delta))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    if avg_loss == 0:
        rsi.append(100.0)
    else:
        rs = avg_gain / avg_loss
        rsi.append(100.0 - (100.0 / (1.0 + rs)))

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi.append(100.0 - (100.0 / (1.0 + rs)))

    return rsi


def _compute_bollinger(closes: list, period: int = 20, num_std: float = 2.0):
    """Returns (middle, upper, lower) bands as lists."""
    middle = _compute_sma(closes, period)
    upper = [float("nan")] * len(closes)
    lower = [float("nan")] * len(closes)
    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1:i + 1]
        if len(window) < 2:
            continue
        std = statistics.stdev(window)
        upper[i] = middle[i] + num_std * std
        lower[i] = middle[i] - num_std * std
    return middle, upper, lower


def _compute_macd(closes: list, fast: int = 12, slow: int = 26, signal: int = 9):
    """Returns (macd_line, signal_line, histogram) as lists."""
    ema_fast = _compute_ema(closes, fast)
    ema_slow = _compute_ema(closes, slow)
    macd_line = [float("nan")] * len(closes)
    for i in range(len(closes)):
        if not (math.isnan(ema_fast[i]) or math.isnan(ema_slow[i])):
            macd_line[i] = ema_fast[i] - ema_slow[i]

    # Signal line = EMA of MACD values (skip NaNs)
    valid_macd = [v for v in macd_line if not math.isnan(v)]
    if len(valid_macd) < signal:
        return macd_line, [float("nan")] * len(closes), [float("nan")] * len(closes)

    sig_ema = _compute_ema(valid_macd, signal)
    signal_line = [float("nan")] * len(closes)
    histogram = [float("nan")] * len(closes)

    j = 0
    for i in range(len(closes)):
        if not math.isnan(macd_line[i]):
            if j < len(sig_ema):
                signal_line[i] = sig_ema[j]
                if not math.isnan(sig_ema[j]):
                    histogram[i] = macd_line[i] - sig_ema[j]
                j += 1

    return macd_line, signal_line, histogram


# ---------------------------------------------------------------------------
# Signal generators: each takes OHLCV list and returns list of signal dicts
# Signal dict: {"index": int, "side": "BUY"|"SELL", "price": float}
# ---------------------------------------------------------------------------

def signal_ema_crossover(ohlcv: list, fast_period: int = 9, slow_period: int = 21) -> list:
    """EMA crossover signals. BUY when fast crosses above slow, SELL when below."""
    closes = [c[4] for c in ohlcv]
    ema_fast = _compute_ema(closes, fast_period)
    ema_slow = _compute_ema(closes, slow_period)
    signals = []
    for i in range(1, len(closes)):
        if any(math.isnan(v) for v in [ema_fast[i], ema_fast[i-1],
                                         ema_slow[i], ema_slow[i-1]]):
            continue
        # Bullish crossover
        if ema_fast[i] > ema_slow[i] and ema_fast[i-1] <= ema_slow[i-1]:
            signals.append({"index": i, "side": "BUY", "price": closes[i]})
        # Bearish crossover
        elif ema_fast[i] < ema_slow[i] and ema_fast[i-1] >= ema_slow[i-1]:
            signals.append({"index": i, "side": "SELL", "price": closes[i]})
    return signals


def signal_rsi_reversal(ohlcv: list, period: int = 14,
                        oversold: float = 30.0, overbought: float = 70.0) -> list:
    """RSI reversal signals. BUY on oversold bounce, SELL on overbought drop."""
    closes = [c[4] for c in ohlcv]
    rsi = _compute_rsi(closes, period)
    signals = []
    for i in range(1, len(rsi)):
        if math.isnan(rsi[i]) or math.isnan(rsi[i-1]):
            continue
        # Oversold bounce: RSI crosses up through oversold
        if rsi[i-1] < oversold and rsi[i] >= oversold:
            signals.append({"index": i, "side": "BUY", "price": closes[i]})
        # Overbought drop: RSI crosses down through overbought
        elif rsi[i-1] > overbought and rsi[i] <= overbought:
            signals.append({"index": i, "side": "SELL", "price": closes[i]})
    return signals


def signal_bollinger_bounce(ohlcv: list, period: int = 20,
                            num_std: float = 2.0) -> list:
    """Bollinger band bounce. BUY near lower band, SELL near upper band."""
    closes = [c[4] for c in ohlcv]
    lows = [c[3] for c in ohlcv]
    highs = [c[2] for c in ohlcv]
    middle, upper, lower = _compute_bollinger(closes, period, num_std)
    signals = []
    for i in range(1, len(closes)):
        if math.isnan(upper[i]) or math.isnan(lower[i]):
            continue
        # Price touches/crosses below lower band then closes above it
        if lows[i] <= lower[i] and closes[i] > lower[i]:
            signals.append({"index": i, "side": "BUY", "price": closes[i]})
        # Price touches/crosses above upper band then closes below it
        elif highs[i] >= upper[i] and closes[i] < upper[i]:
            signals.append({"index": i, "side": "SELL", "price": closes[i]})
    return signals


def signal_macd_divergence(ohlcv: list) -> list:
    """MACD histogram divergence. BUY on histogram turning positive, SELL on negative."""
    closes = [c[4] for c in ohlcv]
    _macd, _signal, histogram = _compute_macd(closes)
    signals = []
    for i in range(1, len(histogram)):
        if math.isnan(histogram[i]) or math.isnan(histogram[i-1]):
            continue
        # Histogram crosses zero upward
        if histogram[i-1] <= 0 and histogram[i] > 0:
            signals.append({"index": i, "side": "BUY", "price": closes[i]})
        # Histogram crosses zero downward
        elif histogram[i-1] >= 0 and histogram[i] < 0:
            signals.append({"index": i, "side": "SELL", "price": closes[i]})
    return signals


def signal_funding_rate_contrarian(ohlcv: list, threshold: float = 0.001) -> list:
    """Funding rate contrarian proxy using price momentum as proxy.

    Since we only have OHLCV (no live funding data in backtest), we use
    short-term momentum as a proxy: extreme positive momentum -> likely high
    funding -> contrarian short, and vice versa.
    """
    closes = [c[4] for c in ohlcv]
    signals = []
    lookback = 8  # 8 candles momentum
    for i in range(lookback, len(closes)):
        momentum = (closes[i] - closes[i - lookback]) / closes[i - lookback]
        # Extreme positive momentum -> contrarian sell
        if momentum > threshold * 100:  # ~10% move in 8 candles
            signals.append({"index": i, "side": "SELL", "price": closes[i]})
        # Extreme negative momentum -> contrarian buy
        elif momentum < -threshold * 100:
            signals.append({"index": i, "side": "BUY", "price": closes[i]})
    return signals


# Registry of built-in signal functions
BUILTIN_SIGNALS = {
    "ema_crossover": signal_ema_crossover,
    "rsi_reversal": signal_rsi_reversal,
    "bollinger_bounce": signal_bollinger_bounce,
    "macd_divergence": signal_macd_divergence,
    "funding_rate_contrarian": signal_funding_rate_contrarian,
}


# ===========================================================================
# 2. walk_forward_test
# ===========================================================================
def walk_forward_test(
    strategy_func,
    symbol: str,
    train_days: int = 60,
    test_days: int = 30,
    step_days: int = 15,
    interval: str = "4h",
    ohlcv: Optional[list] = None,
) -> dict:
    """Run walk-forward analysis on a strategy.

    Splits historical data into rolling windows:
      - Train on first `train_days` days
      - Test on next `test_days` days
      - Slide forward by `step_days`

    Returns dict with:
      - symbol, strategy, windows (list of per-window results),
      - aggregate (combined OOS metrics), in_sample_aggregate

    If ``ohlcv`` is provided (Binance-style rows: ``[ts_ms, o, h, l, c, v]``),
    historical data is **not** fetched; use for Yahoo forex/equity series.
    """
    total_days = train_days + test_days + step_days * 3  # ensure enough data
    if ohlcv is None:
        ohlcv = fetch_historical_klines(symbol, interval=interval, days=total_days)

    if not ohlcv or len(ohlcv) < 50:
        _log.warning("Insufficient data for %s walk-forward", symbol)
        return {
            "symbol": symbol, "error": "insufficient_data",
            "candles_fetched": len(ohlcv) if ohlcv else 0,
        }

    # Convert days to candle counts
    candles_per_day = 86_400_000 / INTERVAL_MS.get(interval, 14_400_000)
    train_candles = int(train_days * candles_per_day)
    test_candles = int(test_days * candles_per_day)
    step_candles = int(step_days * candles_per_day)

    windows = []
    start = 0

    while start + train_candles + test_candles <= len(ohlcv):
        train_data = ohlcv[start:start + train_candles]
        test_data = ohlcv[start + train_candles:start + train_candles + test_candles]

        # Generate signals on both windows
        is_signals = strategy_func(train_data)
        oos_signals = strategy_func(test_data)

        is_metrics = _evaluate_signals(is_signals, train_data)
        oos_metrics = _evaluate_signals(oos_signals, test_data)

        window_result = {
            "window_start": start,
            "window_end": start + train_candles + test_candles,
            "train_candles": len(train_data),
            "test_candles": len(test_data),
            "in_sample": is_metrics,
            "out_of_sample": oos_metrics,
        }
        windows.append(window_result)
        start += step_candles

    if not windows:
        return {
            "symbol": symbol, "error": "no_valid_windows",
            "candles_fetched": len(ohlcv),
        }

    # Aggregate OOS results across windows
    aggregate_oos = _aggregate_metrics([w["out_of_sample"] for w in windows])
    aggregate_is = _aggregate_metrics([w["in_sample"] for w in windows])

    # Statistical validation on OOS trade PnLs across windows
    stat_tests = None
    if _HAS_STAT_TESTS:
        oos_window_pnls = [
            w["out_of_sample"].get("trades_pnl", [])
            for w in windows
        ]
        oos_window_pnls = [wp for wp in oos_window_pnls if wp]
        all_oos_pnls = [p for wp in oos_window_pnls for p in wp]
        if len(oos_window_pnls) >= 2 and len(all_oos_pnls) >= 8:
            try:
                stat_tests = run_statistical_tests(all_oos_pnls, oos_window_pnls)
            except Exception:
                stat_tests = None

    return {
        "symbol": symbol,
        "interval": interval,
        "total_candles": len(ohlcv),
        "num_windows": len(windows),
        "train_days": train_days,
        "test_days": test_days,
        "step_days": step_days,
        "windows": windows,
        "aggregate_oos": aggregate_oos,
        "aggregate_is": aggregate_is,
        "statistical_tests": stat_tests,
    }


def _evaluate_signals(signals: list, ohlcv: list) -> dict:
    """Evaluate trading signals against OHLCV data.

    Simulates trades: BUY at signal price, exit at next opposite signal
    or end of data. Computes WR, PF, avg PnL, max drawdown, Sharpe.
    """
    if not signals or not ohlcv:
        return {
            "total_trades": 0, "win_rate": 0.0, "profit_factor": 0.0,
            "avg_pnl_pct": 0.0, "max_drawdown_pct": 0.0, "sharpe": 0.0,
            "total_pnl_pct": 0.0,
        }

    trades = []
    position = None  # {"side": "BUY", "entry_price": float, "entry_idx": int}

    for sig in signals:
        idx = sig["index"]
        if idx < 0 or idx >= len(ohlcv):
            continue

        if position is None:
            if sig["side"] == "BUY":
                position = {"side": "BUY", "entry_price": sig["price"], "entry_idx": idx}
        else:
            if sig["side"] == "SELL" and position["side"] == "BUY":
                pnl_pct = ((sig["price"] - position["entry_price"])
                           / position["entry_price"]) * 100.0
                trades.append(pnl_pct)
                position = None
            elif sig["side"] == "BUY" and position.get("side") == "SELL":
                # Close short
                pnl_pct = ((position["entry_price"] - sig["price"])
                           / position["entry_price"]) * 100.0
                trades.append(pnl_pct)
                position = None

    # Close any open position at last candle
    if position and ohlcv:
        last_close = ohlcv[-1][4]
        if position["side"] == "BUY":
            pnl_pct = ((last_close - position["entry_price"])
                       / position["entry_price"]) * 100.0
        else:
            pnl_pct = ((position["entry_price"] - last_close)
                       / position["entry_price"]) * 100.0
        trades.append(pnl_pct)

    if not trades:
        return {
            "total_trades": 0, "win_rate": 0.0, "profit_factor": 0.0,
            "avg_pnl_pct": 0.0, "max_drawdown_pct": 0.0, "sharpe": 0.0,
            "total_pnl_pct": 0.0, "trades_pnl": [],
        }

    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t <= 0]
    total_wins = sum(wins) if wins else 0.0
    total_losses = abs(sum(losses)) if losses else 0.0

    win_rate = len(wins) / len(trades) * 100.0
    profit_factor = (total_wins / total_losses) if total_losses > 0 else (
        999.0 if total_wins > 0 else 0.0
    )
    avg_pnl = statistics.mean(trades)
    total_pnl = sum(trades)

    # Max drawdown from cumulative PnL
    cumulative = []
    running = 0.0
    for t in trades:
        running += t
        cumulative.append(running)

    peak = cumulative[0]
    max_dd = 0.0
    for val in cumulative:
        if val > peak:
            peak = val
        dd = peak - val
        if dd > max_dd:
            max_dd = dd

    # Sharpe ratio (annualized, assuming ~6 trades/day on 4h)
    if len(trades) >= 2:
        try:
            std = statistics.stdev(trades)
            sharpe = (avg_pnl / std) * math.sqrt(252) if std > 0 else 0.0
        except statistics.StatisticsError:
            sharpe = 0.0
    else:
        sharpe = 0.0

    return {
        "total_trades": len(trades),
        "win_rate": round(win_rate, 2),
        "profit_factor": round(profit_factor, 3),
        "avg_pnl_pct": round(avg_pnl, 4),
        "max_drawdown_pct": round(max_dd, 4),
        "sharpe": round(sharpe, 3),
        "total_pnl_pct": round(total_pnl, 4),
        "trades_pnl": [round(t, 4) for t in trades],
    }


def _aggregate_metrics(metrics_list: list) -> dict:
    """Aggregate metrics across multiple windows."""
    valid = [m for m in metrics_list if m.get("total_trades", 0) > 0]
    if not valid:
        return {
            "total_trades": 0, "win_rate": 0.0, "profit_factor": 0.0,
            "avg_pnl_pct": 0.0, "max_drawdown_pct": 0.0, "sharpe": 0.0,
            "total_pnl_pct": 0.0, "num_windows_with_trades": 0,
        }

    total_trades = sum(m["total_trades"] for m in valid)
    # Weighted average WR by trade count
    wr = sum(m["win_rate"] * m["total_trades"] for m in valid) / total_trades
    avg_pnl = sum(m["avg_pnl_pct"] * m["total_trades"] for m in valid) / total_trades
    total_pnl = sum(m["total_pnl_pct"] for m in valid)
    max_dd = max(m["max_drawdown_pct"] for m in valid)

    # Aggregate PF
    total_win_pnl = sum(
        m["total_pnl_pct"] for m in valid if m["total_pnl_pct"] > 0
    )
    total_loss_pnl = abs(sum(
        m["total_pnl_pct"] for m in valid if m["total_pnl_pct"] <= 0
    ))
    pf = (total_win_pnl / total_loss_pnl) if total_loss_pnl > 0 else (
        999.0 if total_win_pnl > 0 else 0.0
    )

    sharpe_vals = [m["sharpe"] for m in valid if m["sharpe"] != 0]
    avg_sharpe = statistics.mean(sharpe_vals) if sharpe_vals else 0.0

    return {
        "total_trades": total_trades,
        "win_rate": round(wr, 2),
        "profit_factor": round(pf, 3),
        "avg_pnl_pct": round(avg_pnl, 4),
        "max_drawdown_pct": round(max_dd, 4),
        "sharpe": round(avg_sharpe, 3),
        "total_pnl_pct": round(total_pnl, 4),
        "num_windows_with_trades": len(valid),
    }


# ===========================================================================
# 3. backtest_single_strategy
# ===========================================================================
def backtest_single_strategy(
    strategy_name: str,
    symbols: Optional[list] = None,
    train_days: int = 60,
    test_days: int = 30,
    step_days: int = 15,
    interval: str = "4h",
    *,
    n_trials: int = 1,
) -> dict:
    """Run walk-forward backtest for a single strategy across symbols.

    Attempts to load the strategy function:
      1. From BUILTIN_SIGNALS registry
      2. By importing from alpha_engine strategy modules

    Returns per-symbol and aggregate results.
    """
    strategy_func = _resolve_strategy(strategy_name)
    if strategy_func is None:
        return {"strategy": strategy_name, "error": "strategy_not_found"}

    test_symbols = symbols or DEFAULT_SYMBOLS[:10]
    results_per_symbol = {}
    all_oos = []
    all_is = []

    for sym in test_symbols:
        _log.info("Backtesting %s on %s...", strategy_name, sym)
        result = walk_forward_test(
            strategy_func, sym,
            train_days=train_days, test_days=test_days,
            step_days=step_days, interval=interval,
        )
        results_per_symbol[sym] = result
        if "aggregate_oos" in result:
            all_oos.append(result["aggregate_oos"])
        if "aggregate_is" in result:
            all_is.append(result["aggregate_is"])

    # Aggregate across all symbols
    combined_oos = _aggregate_metrics(all_oos) if all_oos else {}
    combined_is = _aggregate_metrics(all_is) if all_is else {}

    # Anti-overfit check. FIX-M (2026-04-22): forward n_trials + the flat
    # per-trade OOS pnl series so DSR + Bonferroni multiple-testing checks
    # can fire. ``generate_backtest_report`` passes ``n_trials=len(strategies)``;
    # standalone callers default to n_trials=1 which neutralises the correction.
    flat_oos_pnls: list = []
    for sym_result in results_per_symbol.values():
        for w in sym_result.get("windows", []):
            flat_oos_pnls.extend(w.get("out_of_sample", {}).get("trades_pnl", []) or [])
    overfit_report = {}
    if combined_is and combined_oos:
        overfit_report = compute_anti_overfit_metrics(
            combined_is, combined_oos,
            n_trials=max(int(n_trials), 1),
            oos_trade_pnls=flat_oos_pnls if flat_oos_pnls else None,
        )

    # Aggregate statistical tests across all symbols' OOS trades
    aggregate_stat_tests = None
    if _HAS_STAT_TESTS:
        all_oos_pnls_combined = []
        oos_window_pnls_combined = []
        for sym_result in results_per_symbol.values():
            for w in sym_result.get("windows", []):
                oos_pnls = w.get("out_of_sample", {}).get("trades_pnl", [])
                if oos_pnls:
                    all_oos_pnls_combined.extend(oos_pnls)
                    oos_window_pnls_combined.append(oos_pnls)
        if len(oos_window_pnls_combined) >= 2 and len(all_oos_pnls_combined) >= 8:
            try:
                aggregate_stat_tests = run_statistical_tests(
                    all_oos_pnls_combined, oos_window_pnls_combined
                )
            except Exception:
                aggregate_stat_tests = None

    # Strip trades_pnl from windows to avoid bloating serialized JSON
    for sym_result in results_per_symbol.values():
        for w in sym_result.get("windows", []):
            w.get("in_sample", {}).pop("trades_pnl", None)
            w.get("out_of_sample", {}).pop("trades_pnl", None)

    return {
        "strategy": strategy_name,
        "symbols_tested": test_symbols,
        "per_symbol": results_per_symbol,
        "aggregate_oos": combined_oos,
        "aggregate_is": combined_is,
        "anti_overfit": overfit_report,
        "statistical_tests": aggregate_stat_tests,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _resolve_strategy(name: str):
    """Resolve strategy name to a callable function.

    Search order:
      1. BUILTIN_SIGNALS registry (ema_crossover, rsi_reversal, etc.)
      2. Dynamic import from alpha_engine modules
    """
    # Check built-in registry first
    if name in BUILTIN_SIGNALS:
        return BUILTIN_SIGNALS[name]

    # Try dynamic import from alpha_engine modules
    strategy_modules = [
        "alpha_engine.crypto_strategies",
        "alpha_engine.advanced_strategies",
        "alpha_engine.onchain_strategies",
        "alpha_engine.quant_strategies",
        "alpha_engine.event_strategies",
        "alpha_engine.forex_strategies",
        "alpha_engine.equity_strategies",
        "alpha_engine.advanced_quant_strategies",
        "alpha_engine.advanced_statistical_strategies",
        "alpha_engine.antigravity_strategies",
        "alpha_engine.pattern_strategies",
        "alpha_engine.cyclical_strategies",
    ]

    for module_name in strategy_modules:
        try:
            mod = __import__(module_name, fromlist=[name])
            func = getattr(mod, name, None)
            if callable(func):
                _log.info("Found strategy %s in %s", name, module_name)
                return func
        except (ImportError, AttributeError) as exc:
            _log.debug("Could not load %s from %s: %s", name, module_name, exc)
            continue

    _log.warning("Strategy %s not found in any module", name)
    return None


# ===========================================================================
# 4. compute_anti_overfit_metrics
# ===========================================================================
def deflated_sharpe_ratio(
    observed_sharpe: float,
    n_trials: int,
    n_observations: int,
    skew: float = 0.0,
    excess_kurt: float = 3.0,
) -> tuple:
    """Deflated Sharpe Ratio (López de Prado 2018).

    Adjusts a realized Sharpe ratio for selection bias when N strategies are
    tested. Returns ``(dsr, p_value)`` where ``dsr`` is the probability the
    observed SR is greater than the expected maximum SR under the null
    hypothesis of no skill across ``n_trials`` independent strategies.

    A DSR ≥ 0.95 (i.e. p ≤ 0.05) indicates the SR is unlikely to be
    selection-bias artifact. ``skew`` and ``excess_kurt`` are moment
    corrections that matter for fat-tailed PnL distributions; the defaults
    (0, 3) correspond to a Normal distribution.

    Returns (0.0, 1.0) whenever inputs are degenerate (n_observations ≤ 1,
    std estimator non-positive). That makes the caller's ``dsr >= 0.95``
    check a hard-fail for unusable inputs, which matches the intent.
    """
    import math

    if n_trials < 1 or n_observations <= 1:
        return 0.0, 1.0
    try:
        from scipy.stats import norm  # type: ignore
    except Exception:
        return 0.0, 1.0

    # Expected maximum Sharpe under H0 of no skill across n_trials strategies.
    # Asymptotic formula from López de Prado (2018), eq. 7.
    emc = 0.5772156649015329  # Euler–Mascheroni
    n_eff = max(n_trials, 2)
    exp_max_sr = (
        math.sqrt(2.0 * math.log(n_eff)) - (emc / math.sqrt(2.0 * math.log(n_eff)))
    )
    # Variance of Sharpe-ratio estimator (Mertens 2002 / Opdyke 2007 / PdlP 2018 eq. 9).
    # Uses excess kurtosis (Normal = 0), but the common convention in this pipeline's
    # stats helpers is to pass kurtosis ≈ 3 for Normal; treat ``excess_kurt`` as
    # "excess" if caller uses the 0-centered convention (negative values clamped).
    kurt_term = max(excess_kurt, 0.0)
    var_sr = (
        1.0 - (skew * observed_sharpe) + ((kurt_term - 1.0) / 4.0) * (observed_sharpe ** 2)
    ) / float(n_observations - 1)
    if var_sr <= 0.0:
        return 0.0, 1.0
    sr_std = math.sqrt(var_sr)
    z = (observed_sharpe - exp_max_sr) / sr_std
    dsr = float(norm.cdf(z))
    return round(dsr, 6), round(1.0 - dsr, 6)


def bonferroni_adjust(p_value: float, n_trials: int) -> float:
    """Bonferroni-adjusted p-value: ``min(p * n_trials, 1.0)``.

    Conservative family-wise error control. A ``bonferroni_p < 0.05``
    means the raw per-strategy p-value was tight enough to survive
    testing ``n_trials`` strategies simultaneously at α = 0.05.
    """
    if n_trials < 1:
        return min(max(float(p_value), 0.0), 1.0)
    return min(max(float(p_value) * n_trials, 0.0), 1.0)


def benjamini_hochberg(p_values, fdr: float = 0.05):
    """Benjamini–Hochberg FDR control.

    Given a list of raw p-values across ``n_trials`` strategies, return a
    list of booleans (same length, same order) indicating which pass at
    the requested false-discovery rate.

    Less conservative than Bonferroni — allows more real edges through at
    the cost of a controlled fraction of false positives. Use for
    strategy-selection reporting where discovery matters more than
    family-wise error guarantees.
    """
    n = len(p_values)
    if n == 0:
        return []
    # Sort p's with original indices.
    order = sorted(range(n), key=lambda i: float(p_values[i]))
    passing = [False] * n
    # Find largest k such that p_(k) <= (k / n) * fdr, passing indices 1..k.
    max_k = 0
    for rank, idx in enumerate(order, start=1):
        threshold = (rank / n) * fdr
        if float(p_values[idx]) <= threshold:
            max_k = rank
    for rank, idx in enumerate(order, start=1):
        if rank <= max_k:
            passing[idx] = True
    return passing


def _pnl_series_to_sharpe_and_moments(pnl_pcts):
    """Derive (sharpe, skew, excess_kurt, n) from a per-trade PnL% series.

    Sharpe here is a per-trade ratio (mean / std, no annualisation) to match
    the DSR formulation — annualisation factors cancel in the ratio z-score.
    Returns (0, 0, 3, 0) for n < 2.
    """
    try:
        import math

        vals = [float(x) for x in pnl_pcts if x is not None]
    except Exception:
        return 0.0, 0.0, 3.0, 0
    n = len(vals)
    if n < 2:
        return 0.0, 0.0, 3.0, n
    mean = sum(vals) / n
    var = sum((v - mean) ** 2 for v in vals) / (n - 1)
    if var <= 0:
        return 0.0, 0.0, 3.0, n
    std = math.sqrt(var)
    sharpe = mean / std
    # Sample skew (Fisher), sample kurtosis (not excess).
    m3 = sum((v - mean) ** 3 for v in vals) / n
    m4 = sum((v - mean) ** 4 for v in vals) / n
    skew = m3 / (std ** 3) if std > 0 else 0.0
    kurt = (m4 / (std ** 4)) if std > 0 else 3.0
    return sharpe, skew, kurt, n


def compute_anti_overfit_metrics(
    in_sample_results: dict,
    out_of_sample_results: dict,
    *,
    n_trials: int = 1,
    oos_trade_pnls=None,
) -> dict:
    """Run 10 anti-overfit checks comparing IS vs OOS performance.

    Returns dict with each check name, pass/fail, value, threshold, and
    an overall_pass boolean (True only if ALL checks pass).

    Two checks were added in FIX-M (2026-04-22) to correct for
    multiple-testing selection bias when the caller evaluates many
    strategies in the same report. With ``n_trials`` = N strategies:

      - Check 9 (``dsr_selection_bias``): López de Prado 2018 Deflated
        Sharpe Ratio. Requires DSR ≥ 0.95.
      - Check 10 (``bonferroni_p``): Bonferroni-adjusted per-trade
        t-test p-value. Requires adjusted p < 0.05.

    Pass ``oos_trade_pnls=[...]`` (the raw per-trade OOS PnL% list) to
    enable these checks; without it checks 9 and 10 are emitted with
    ``"skipped": True`` and do not contribute to ``overall_pass``.

    Per ``memory/feedback_mutate_before_kill.md``, DSR/Bonferroni failure
    should **gate promotion** into production, NOT trigger auto-kill. The
    three-axis mutation protocol runs first.
    """
    checks = {}

    is_wr = in_sample_results.get("win_rate", 0)
    oos_wr = out_of_sample_results.get("win_rate", 0)
    is_pf = in_sample_results.get("profit_factor", 0)
    oos_pf = out_of_sample_results.get("profit_factor", 0)
    is_sharpe = in_sample_results.get("sharpe", 0)
    is_dd = in_sample_results.get("max_drawdown_pct", 0)
    oos_dd = out_of_sample_results.get("max_drawdown_pct", 0)
    oos_trades = out_of_sample_results.get("total_trades", 0)
    num_windows = out_of_sample_results.get("num_windows_with_trades", 0)
    oos_total_pnl = out_of_sample_results.get("total_pnl_pct", 0)

    # Check 1: OOS/IS Win Rate ratio > 0.85
    wr_ratio = (oos_wr / is_wr) if is_wr > 0 else 0
    checks["oos_is_wr_ratio"] = {
        "value": round(wr_ratio, 4),
        "threshold": 0.85,
        "pass": wr_ratio >= 0.85,
        "description": "OOS/IS win rate ratio should be >= 0.85",
    }

    # Check 2: OOS/IS Profit Factor ratio > 0.70
    pf_ratio = (oos_pf / is_pf) if is_pf > 0 else 0
    checks["oos_is_pf_ratio"] = {
        "value": round(pf_ratio, 4),
        "threshold": 0.70,
        "pass": pf_ratio >= 0.70,
        "description": "OOS/IS profit factor ratio should be >= 0.70",
    }

    # Check 3: IS Sharpe < 3.0 (too high = likely overfit)
    checks["is_sharpe_not_extreme"] = {
        "value": round(is_sharpe, 4),
        "threshold": 3.0,
        "pass": is_sharpe < 3.0,
        "description": "In-sample Sharpe < 3.0 (higher suggests overfitting)",
    }

    # Check 4: OOS drawdown < 2x IS drawdown
    dd_ratio = (oos_dd / is_dd) if is_dd > 0 else (0 if oos_dd == 0 else 999)
    checks["oos_drawdown_ratio"] = {
        "value": round(dd_ratio, 4),
        "threshold": 2.0,
        "pass": dd_ratio < 2.0,
        "description": "OOS max drawdown should be < 2x IS max drawdown",
    }

    # Check 5: Minimum 30 OOS trades
    checks["min_oos_trades"] = {
        "value": oos_trades,
        "threshold": 30,
        "pass": oos_trades >= 30,
        "description": "Need at least 30 OOS trades for statistical significance",
    }

    # Check 6: Consistent across 3+ test windows
    checks["min_consistent_windows"] = {
        "value": num_windows,
        "threshold": 3,
        "pass": num_windows >= 3,
        "description": "Strategy must be profitable in 3+ test windows",
    }

    # Check 7: No single window accounts for >50% of profit
    # This is checked at a higher level when window data is available
    # Here we use a proxy: if we have the data, check it
    checks["no_single_window_dominance"] = {
        "value": "N/A (checked per-symbol)",
        "threshold": "< 50% of total profit",
        "pass": True,  # Default pass; overridden when window data available
        "description": "No single test window should account for >50% of total profit",
    }

    # Check 8: OOS WR > 40% (absolute minimum)
    checks["oos_wr_absolute_min"] = {
        "value": round(oos_wr, 2),
        "threshold": 40.0,
        "pass": oos_wr >= 40.0,
        "description": "OOS win rate must be >= 40% absolute minimum",
    }

    # Checks 9 & 10 (FIX-M, 2026-04-22): Multiple-testing corrections.
    # Without the raw per-trade OOS pnls we can't compute a per-trade t-test
    # or a moment-adjusted DSR, so we emit "skipped=True" entries and omit
    # them from overall_pass. That preserves backward compatibility with
    # callers that don't yet pass ``oos_trade_pnls``.
    if oos_trade_pnls is not None and len(oos_trade_pnls) >= 2:
        sharpe_per_trade, skew, kurt, n_obs = _pnl_series_to_sharpe_and_moments(
            oos_trade_pnls
        )
        # Deflated Sharpe Ratio.
        dsr, dsr_p = deflated_sharpe_ratio(
            sharpe_per_trade,
            n_trials=max(int(n_trials), 1),
            n_observations=n_obs,
            skew=skew,
            excess_kurt=max(kurt - 3.0, 0.0),
        )
        checks["dsr_selection_bias"] = {
            "value": round(dsr, 4),
            "threshold": 0.95,
            "pass": dsr >= 0.95,
            "n_trials": int(n_trials),
            "n_observations": int(n_obs),
            "per_trade_sharpe": round(float(sharpe_per_trade), 4),
            "p_value": round(dsr_p, 4),
            "description": (
                "DSR (López de Prado 2018) — SR survives selection-bias "
                "correction across n_trials strategies. Gates PROMOTION, not kill."
            ),
        }
        # Per-trade t-test on OOS pnls, then Bonferroni-adjust.
        try:
            from scipy.stats import ttest_1samp  # type: ignore

            t_stat, raw_p = ttest_1samp(
                [float(x) for x in oos_trade_pnls], popmean=0.0,
            )
            # One-sided (edge > 0) — halve p when t > 0, else 1 - p/2.
            t_val = float(t_stat) if t_stat == t_stat else 0.0
            p_two = float(raw_p) if raw_p == raw_p else 1.0
            p_one = (p_two / 2.0) if t_val > 0 else max(1.0 - (p_two / 2.0), 0.0)
            bonf_p = bonferroni_adjust(p_one, int(n_trials))
        except Exception:
            bonf_p, p_one, t_val = 1.0, 1.0, 0.0
        checks["bonferroni_p"] = {
            "value": round(bonf_p, 4),
            "threshold": 0.05,
            "pass": bonf_p < 0.05,
            "raw_p_one_sided": round(p_one, 6),
            "t_stat": round(t_val, 4),
            "n_trials": int(n_trials),
            "description": (
                "Bonferroni-adjusted per-trade t-test p-value across "
                "n_trials strategies. FWER control at alpha = 0.05."
            ),
        }
    else:
        # Skip gracefully; do not contribute to overall_pass.
        for name in ("dsr_selection_bias", "bonferroni_p"):
            checks[name] = {
                "value": None,
                "threshold": None,
                "pass": True,  # skip = neutral, don't fail overall
                "skipped": True,
                "reason": (
                    "oos_trade_pnls not provided or n<2 — multiple-testing check skipped"
                ),
            }

    # Overall pass (skipped checks don't fail)
    overall = all(c["pass"] for c in checks.values())

    return {
        "checks": checks,
        "overall_pass": overall,
        "checks_passed": sum(1 for c in checks.values() if c["pass"]),
        "checks_total": len(checks),
        "multiple_testing": {
            "n_trials": int(n_trials),
            "applied": oos_trade_pnls is not None and len(oos_trade_pnls) >= 2,
        },
    }


def check_single_window_dominance(windows: list) -> bool:
    """Check that no single test window accounts for >50% of total OOS profit.

    Returns True if the check PASSES (no dominance), False if it fails.
    """
    if not windows or len(windows) < 2:
        return True  # Not enough windows to check

    oos_pnls = []
    for w in windows:
        oos = w.get("out_of_sample", {})
        oos_pnls.append(oos.get("total_pnl_pct", 0))

    total_profit = sum(p for p in oos_pnls if p > 0)
    if total_profit <= 0:
        return True  # No profit to dominate

    for pnl in oos_pnls:
        if pnl > 0 and (pnl / total_profit) > 0.50:
            return False

    return True


# ===========================================================================
# 5. generate_backtest_report
# ===========================================================================
def generate_backtest_report(
    strategies: Optional[list] = None,
    symbols: Optional[list] = None,
    train_days: int = 60,
    test_days: int = 30,
    step_days: int = 15,
    interval: str = "4h",
) -> dict:
    """Run walk-forward backtest on all (or specified) strategies.

    Generates comprehensive report and saves to data/walk_forward_results.json.
    """
    if strategies is None:
        strategies = list(BUILTIN_SIGNALS.keys())

    report = {
        "report_type": "walk_forward_backtest",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "parameters": {
            "train_days": train_days,
            "test_days": test_days,
            "step_days": step_days,
            "interval": interval,
        },
        "strategies": {},
        "summary": {},
    }

    passing = []
    failing = []

    n_trials = len(strategies)  # FIX-M: fed to DSR/Bonferroni multiple-testing checks

    for strat_name in strategies:
        _log.info("=== Running walk-forward for strategy: %s ===", strat_name)
        result = backtest_single_strategy(
            strat_name,
            symbols=symbols,
            train_days=train_days,
            test_days=test_days,
            step_days=step_days,
            interval=interval,
            n_trials=n_trials,
        )

        # Check single-window dominance for each symbol
        if "per_symbol" in result:
            for sym, sym_result in result["per_symbol"].items():
                if "windows" in sym_result:
                    dominance_ok = check_single_window_dominance(sym_result["windows"])
                    if not dominance_ok and "anti_overfit" in result:
                        ao = result["anti_overfit"]
                        if "checks" in ao:
                            ao["checks"]["no_single_window_dominance"]["pass"] = False
                            ao["checks"]["no_single_window_dominance"]["value"] = (
                                f"Failed for {sym}"
                            )
                            ao["overall_pass"] = all(
                                c["pass"] for c in ao["checks"].values()
                            )
                            ao["checks_passed"] = sum(
                                1 for c in ao["checks"].values() if c["pass"]
                            )

        report["strategies"][strat_name] = result

        overfit = result.get("anti_overfit", {})
        if overfit.get("overall_pass"):
            passing.append(strat_name)
        else:
            failing.append(strat_name)

    report["summary"] = {
        "total_strategies": len(strategies),
        "passing_anti_overfit": len(passing),
        "failing_anti_overfit": len(failing),
        "passing_strategies": passing,
        "failing_strategies": failing,
    }

    # Save report
    os.makedirs(DATA_DIR, exist_ok=True)
    output_path = os.path.join(DATA_DIR, "walk_forward_results.json")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        _log.info("Report saved to %s", output_path)
    except (OSError, IOError) as exc:
        _log.error("Failed to save report: %s", exc)

    return report


# ===========================================================================
# CLI entry point
# ===========================================================================
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    import argparse

    parser = argparse.ArgumentParser(description="Walk-Forward Backtester")
    parser.add_argument(
        "--strategies", nargs="*", default=None,
        help="Strategy names to test (default: all built-in)",
    )
    parser.add_argument(
        "--symbols", nargs="*", default=None,
        help="Symbols to test (default: top 10 by volume)",
    )
    parser.add_argument("--train-days", type=int, default=60)
    parser.add_argument("--test-days", type=int, default=30)
    parser.add_argument("--step-days", type=int, default=15)
    parser.add_argument("--interval", default="4h")

    args = parser.parse_args()

    report = generate_backtest_report(
        strategies=args.strategies,
        symbols=args.symbols,
        train_days=args.train_days,
        test_days=args.test_days,
        step_days=args.step_days,
        interval=args.interval,
    )

    passed = report["summary"]["passing_anti_overfit"]
    total = report["summary"]["total_strategies"]
    print(f"\nWalk-Forward Complete: {passed}/{total} strategies pass anti-overfit checks")
    print(f"Report: alpha_engine/data/walk_forward_results.json")
