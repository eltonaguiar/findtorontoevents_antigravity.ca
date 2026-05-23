#!/usr/bin/env python3
"""
Multi-Source Data Fetcher v2.0
==============================
7-exchange failover chain for maximum data reliability.

Crypto OHLCV priority:
  1. Binance Public API  (no auth, 6000 weight/min)
  2. Bybit Public API    (no auth, 600 req/5s)
  3. OKX Public API      (no auth, 20 req/2s)
  4. KuCoin Public API   (no auth, weight-based)
  5. Kraken Public API   (no auth, ~1 req/s)
  6. CoinCap API         (no auth, 200 req/min, close-only)
  7. yfinance            (scraper, unreliable but wide coverage)

Forex daily rates:
  1. Frankfurter (ECB)   (no auth, unlimited)
  2. ExchangeRate-API    (no auth, daily refresh)
  3. yfinance            (fallback)

Stocks/ETFs:
  1. yfinance            (still best for US equities)

All APIs are free, no credit card, generous rate limits.
Designed for GitHub Actions running every 15 minutes.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Circuit Breaker — skip sources after repeated failures within a scan
# ---------------------------------------------------------------------------

_source_failures: dict[str, int] = {}
_CIRCUIT_BREAKER_THRESHOLD = 3

# CI Geo-Block: detect GitHub Actions and skip always-blocked exchanges
_IN_GITHUB_ACTIONS = bool(os.environ.get("GITHUB_ACTIONS"))
_CI_BLOCKED_SOURCES = {"binance", "bybit"}  # geo-blocked from US runners


def reset_circuit_breakers():
    """Call at the start of each scan cycle to reset failure counts."""
    _source_failures.clear()


def _circuit_open(source: str) -> bool:
    """Return True if circuit breaker is tripped for this source."""
    return _source_failures.get(source, 0) >= _CIRCUIT_BREAKER_THRESHOLD


def _record_failure(source: str):
    """Record a failure for circuit breaker tracking."""
    _source_failures[source] = _source_failures.get(source, 0) + 1
    if _source_failures[source] == _CIRCUIT_BREAKER_THRESHOLD:
        print(f"  [circuit-breaker] {source} tripped after {_CIRCUIT_BREAKER_THRESHOLD} consecutive failures — skipping for rest of scan")


def _ci_blocked(source: str) -> bool:
    """Return True if source is geo-blocked in CI environment."""
    return _IN_GITHUB_ACTIONS and source in _CI_BLOCKED_SOURCES


# ---------------------------------------------------------------------------
# API Base URLs
# ---------------------------------------------------------------------------

BINANCE_SPOT_ENDPOINTS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://data-api.binance.vision",
    "https://api.binance.us",
]
BINANCE_FUTURES_ENDPOINTS = [
    "https://fapi.binance.com",
    "https://fapi1.binance.com",
    "https://fapi2.binance.com",
]
# In CI, prefer non-geo-blocked endpoints
if os.environ.get("GITHUB_ACTIONS"):
    BINANCE_SPOT_ENDPOINTS = [
        "https://data-api.binance.vision", "https://api.binance.us",
        "https://api1.binance.com", "https://api2.binance.com",
        "https://api.binance.com",
    ]
# Legacy single URL (backward compat)
BINANCE_SPOT = BINANCE_SPOT_ENDPOINTS[0]
BINANCE_FUTURES = BINANCE_FUTURES_ENDPOINTS[0]
BYBIT = "https://api.bybit.com"
OKX = "https://www.okx.com"
KUCOIN = "https://api.kucoin.com"
KRAKEN = "https://api.kraken.com"
COINCAP = "https://api.coincap.io/v2"
FRANKFURTER = "https://api.frankfurter.dev/v1"
EXCHANGERATE = "https://open.er-api.com/v6"

# Forex pair mapping: yfinance symbol → (base, quote)
_FOREX_MAP = {
    "EURUSD=X": ("EUR", "USD"), "GBPUSD=X": ("GBP", "USD"),
    "USDJPY=X": ("USD", "JPY"), "USDCHF=X": ("USD", "CHF"),
    "AUDUSD=X": ("AUD", "USD"), "USDCAD=X": ("USD", "CAD"),
    "NZDUSD=X": ("NZD", "USD"), "EURJPY=X": ("EUR", "JPY"),
    "GBPJPY=X": ("GBP", "JPY"), "EURGBP=X": ("EUR", "GBP"),
    "AUDJPY=X": ("AUD", "JPY"), "NZDJPY=X": ("NZD", "JPY"),
    "CADJPY=X": ("CAD", "JPY"), "USDMXN=X": ("USD", "MXN"),
    "USDZAR=X": ("USD", "ZAR"),
}

# Kraken symbol mapping (non-standard naming)
_YF_TO_KRAKEN = {
    "BTC-USD": "XBTUSD", "ETH-USD": "ETHUSD", "SOL-USD": "SOLUSD",
    "XRP-USD": "XRPUSD", "ADA-USD": "ADAUSD", "DOT-USD": "DOTUSD",
    "LINK-USD": "LINKUSD", "AVAX-USD": "AVAXUSD", "ATOM-USD": "ATOMUSD",
    "LTC-USD": "LTCUSD", "BCH-USD": "BCHUSD", "ALGO-USD": "ALGOUSD",
    "DOGE-USD": "DOGEUSD", "SHIB-USD": "SHIBUSD", "NEAR-USD": "NEARUSD",
    "FIL-USD": "FILUSD", "ETC-USD": "ETCUSD", "MANA-USD": "MANAUSD",
    "SAND-USD": "SANDUSD", "GRT-USD": "GRTUSD", "TRX-USD": "TRXUSD",
    "BNB-USD": "BNBUSD",
}

# CoinCap ID mapping
_YF_TO_COINCAP = {
    "BTC-USD": "bitcoin", "ETH-USD": "ethereum", "BNB-USD": "binance-coin",
    "XRP-USD": "xrp", "SOL-USD": "solana", "ADA-USD": "cardano",
    "AVAX-USD": "avalanche", "DOT-USD": "polkadot", "LINK-USD": "chainlink",
    "MATIC-USD": "polygon", "LTC-USD": "litecoin", "TRX-USD": "tron",
    "ETC-USD": "ethereum-classic", "BCH-USD": "bitcoin-cash",
    "ATOM-USD": "cosmos", "NEAR-USD": "near-protocol", "ALGO-USD": "algorand",
    "FIL-USD": "filecoin", "ICP-USD": "internet-computer",
    "VET-USD": "vechain", "HBAR-USD": "hedera-hashgraph",
    "DOGE-USD": "dogecoin", "SHIB-USD": "shiba-inu",
    "PEPE-USD": "pepe", "FLOKI-USD": "floki-inu", "BONK-USD": "bonk",
    "SAND-USD": "the-sandbox", "MANA-USD": "decentraland",
    "ENJ-USD": "enjin-coin", "CHZ-USD": "chiliz", "THETA-USD": "theta-network",
    "GRT-USD": "the-graph", "ZEC-USD": "zcash", "DASH-USD": "dash",
    "APT-USD": "aptos", "OP-USD": "optimism",
}


def _http_get(url: str, timeout: int = 15) -> Optional[bytes]:
    """Simple HTTP GET with timeout, error handling, and one retry on failure."""
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "KIMI-Scanner/11.3"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception:
            if attempt == 0:
                time.sleep(3)
            else:
                return None
    return None


def _http_json(url: str, timeout: int = 15) -> Optional[dict | list]:
    """HTTP GET returning parsed JSON."""
    raw = _http_get(url, timeout)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _klines_to_df(rows: list[dict]) -> Optional[pd.DataFrame]:
    """Convert list of {Date, Open, High, Low, Close, Volume} to DataFrame."""
    if len(rows) < 5:
        return None
    df = pd.DataFrame(rows)
    df.set_index("Date", inplace=True)
    df.index = df.index.tz_localize(None)  # tz-naive to match yfinance
    return df


# ===================================================================
# 1. BINANCE — Primary crypto source (no auth, 6000 weight/min)
# ===================================================================

def _yf_to_binance(yf_sym: str) -> Optional[str]:
    if yf_sym.endswith("-USD"):
        return yf_sym.replace("-USD", "") + "USDT"
    return None


def fetch_binance_klines(symbol: str, interval: str = "1d", limit: int = 365) -> Optional[pd.DataFrame]:
    """Binance spot klines with endpoint failover. Weight: 2 per call."""
    for base in BINANCE_SPOT_ENDPOINTS:
        url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={min(limit, 1000)}"
        data = _http_json(url, timeout=20)
        if data and isinstance(data, list) and len(data) >= 5:
            rows = []
            for k in data:
                try:
                    rows.append({
                        "Date": pd.Timestamp(k[0], unit="ms", tz="UTC"),
                        "Open": float(k[1]), "High": float(k[2]),
                        "Low": float(k[3]), "Close": float(k[4]),
                        "Volume": float(k[5]),
                    })
                except (IndexError, ValueError, TypeError):
                    continue
            return _klines_to_df(rows)
    return None


def fetch_binance_price(symbol: str) -> Optional[float]:
    for base in BINANCE_SPOT_ENDPOINTS:
        url = f"{base}/api/v3/ticker/price?symbol={symbol}"
        data = _http_json(url, timeout=10)
        if data and "price" in data:
            try:
                return float(data["price"])
            except (ValueError, TypeError):
                pass
    return None


def fetch_binance_all_prices() -> dict[str, float]:
    """All prices in one call with endpoint failover. Weight: 4."""
    for base in BINANCE_SPOT_ENDPOINTS:
        url = f"{base}/api/v3/ticker/price"
        data = _http_json(url, timeout=15)
        if data and isinstance(data, list):
            return {item["symbol"]: float(item["price"]) for item in data
                    if "symbol" in item and "price" in item}
    return {}


def fetch_binance_funding_rates() -> list[dict]:
    for base in BINANCE_FUTURES_ENDPOINTS:
        url = f"{base}/fapi/v1/premiumIndex"
        data = _http_json(url, timeout=15)
        if data and isinstance(data, list):
            results = []
            for item in data:
                try:
                    results.append({
                        "symbol": item["symbol"],
                        "mark_price": float(item.get("markPrice", 0)),
                        "funding_rate": float(item.get("lastFundingRate", 0)),
                        "next_funding_time": item.get("nextFundingTime", 0),
                    })
                except (KeyError, ValueError, TypeError):
                    continue
            return results
    return []


def fetch_binance_orderbook(symbol: str, limit: int = 20) -> Optional[dict]:
    for base in BINANCE_SPOT_ENDPOINTS:
        data = _http_json(f"{base}/api/v3/depth?symbol={symbol}&limit={limit}", timeout=10)
        if data:
            return data
    return None


# ===================================================================
# 2. BYBIT — Fast backup (no auth, 600 req/5s)
# ===================================================================

def _yf_to_bybit(yf_sym: str) -> Optional[str]:
    if yf_sym.endswith("-USD"):
        return yf_sym.replace("-USD", "") + "USDT"
    return None


def fetch_bybit_klines(symbol: str, interval: str = "D", limit: int = 365, category: str = "spot") -> Optional[pd.DataFrame]:
    """Bybit v5 kline. No auth. Returns newest-first (we reverse)."""
    url = f"{BYBIT}/v5/market/kline?symbol={symbol}&interval={interval}&limit={min(limit, 1000)}&category={category}"
    data = _http_json(url, timeout=20)
    if not data or data.get("retCode") != 0:
        return None
    klines = data.get("result", {}).get("list", [])
    if not klines or len(klines) < 5:
        return None
    rows = []
    for k in reversed(klines):  # reverse: newest-first → oldest-first
        try:
            rows.append({
                "Date": pd.Timestamp(int(k[0]), unit="ms", tz="UTC"),
                "Open": float(k[1]), "High": float(k[2]),
                "Low": float(k[3]), "Close": float(k[4]),
                "Volume": float(k[5]),
            })
        except (IndexError, ValueError, TypeError):
            continue
    return _klines_to_df(rows)


def fetch_bybit_price(symbol: str) -> Optional[float]:
    url = f"{BYBIT}/v5/market/tickers?symbol={symbol}&category=spot"
    data = _http_json(url, timeout=10)
    if not data or data.get("retCode") != 0:
        return None
    tickers = data.get("result", {}).get("list", [])
    if tickers:
        try:
            return float(tickers[0].get("lastPrice", 0))
        except (ValueError, TypeError):
            pass
    return None


# ===================================================================
# 3. OKX — Strong backup (no auth, 20 req/2s)
# ===================================================================

def _yf_to_okx(yf_sym: str) -> Optional[str]:
    if yf_sym.endswith("-USD"):
        base = yf_sym.replace("-USD", "")
        return f"{base}-USDT"
    return None


def fetch_okx_klines(inst_id: str, bar: str = "1D", limit: int = 300) -> Optional[pd.DataFrame]:
    """OKX candles. No auth. Max 300 per call."""
    url = f"{OKX}/api/v5/market/candles?instId={inst_id}&bar={bar}&limit={min(limit, 300)}"
    data = _http_json(url, timeout=20)
    if not data or data.get("code") != "0":
        return None
    candles = data.get("data", [])
    if not candles or len(candles) < 5:
        return None
    rows = []
    for c in reversed(candles):  # OKX returns newest-first
        try:
            rows.append({
                "Date": pd.Timestamp(int(c[0]), unit="ms", tz="UTC"),
                "Open": float(c[1]), "High": float(c[2]),
                "Low": float(c[3]), "Close": float(c[4]),
                "Volume": float(c[5]),
            })
        except (IndexError, ValueError, TypeError):
            continue
    return _klines_to_df(rows)


def fetch_okx_history_klines(inst_id: str, bar: str = "1D", limit: int = 300) -> Optional[pd.DataFrame]:
    """OKX history candles (older data). No auth."""
    url = f"{OKX}/api/v5/market/history-candles?instId={inst_id}&bar={bar}&limit={min(limit, 100)}"
    data = _http_json(url, timeout=20)
    if not data or data.get("code") != "0":
        return None
    candles = data.get("data", [])
    if not candles or len(candles) < 5:
        return None
    rows = []
    for c in reversed(candles):
        try:
            rows.append({
                "Date": pd.Timestamp(int(c[0]), unit="ms", tz="UTC"),
                "Open": float(c[1]), "High": float(c[2]),
                "Low": float(c[3]), "Close": float(c[4]),
                "Volume": float(c[5]),
            })
        except (IndexError, ValueError, TypeError):
            continue
    return _klines_to_df(rows)


def _fetch_okx_full(inst_id: str, days: int = 365) -> Optional[pd.DataFrame]:
    """Fetch recent + history candles from OKX and merge for longer history."""
    df_recent = fetch_okx_klines(inst_id, bar="1D", limit=300)
    if df_recent is None or len(df_recent) < 20:
        return None
    if days <= 300:
        return df_recent
    # Try to get older data
    df_older = fetch_okx_history_klines(inst_id, bar="1D", limit=100)
    if df_older is not None and len(df_older) > 5:
        combined = pd.concat([df_older, df_recent])
        combined = combined[~combined.index.duplicated(keep="last")]
        combined.sort_index(inplace=True)
        return combined
    return df_recent


# ===================================================================
# 4. KUCOIN — Good coverage (no auth, weight-based)
# ===================================================================

def _yf_to_kucoin(yf_sym: str) -> Optional[str]:
    if yf_sym.endswith("-USD"):
        base = yf_sym.replace("-USD", "")
        return f"{base}-USDT"
    return None


def fetch_kucoin_klines(symbol: str, ktype: str = "1day", days: int = 365) -> Optional[pd.DataFrame]:
    """KuCoin candles. No auth. Max 1500 per response.
    WARNING: KuCoin array order is [time, open, CLOSE, high, low, vol, turnover]
    """
    end_at = int(time.time())
    start_at = end_at - (days * 86400)
    url = f"{KUCOIN}/api/v1/market/candles?type={ktype}&symbol={symbol}&startAt={start_at}&endAt={end_at}"
    data = _http_json(url, timeout=20)
    if not data or data.get("code") != "200000":
        return None
    candles = data.get("data", [])
    if not candles or len(candles) < 5:
        return None
    rows = []
    for c in reversed(candles):  # KuCoin returns newest-first
        try:
            # CRITICAL: KuCoin order is [time, open, CLOSE, high, low, vol, turnover]
            rows.append({
                "Date": pd.Timestamp(int(c[0]), unit="s", tz="UTC"),
                "Open": float(c[1]),
                "Close": float(c[2]),   # index 2 = close (non-standard!)
                "High": float(c[3]),    # index 3 = high
                "Low": float(c[4]),     # index 4 = low
                "Volume": float(c[5]),
            })
        except (IndexError, ValueError, TypeError):
            continue
    return _klines_to_df(rows)


# ===================================================================
# 5. KRAKEN — Reliable legacy exchange (no auth, ~1 req/s)
# ===================================================================

def fetch_kraken_ohlc(pair: str, interval: int = 1440) -> Optional[pd.DataFrame]:
    """Kraken OHLC. No auth. Max 720 candles. interval in minutes."""
    url = f"{KRAKEN}/0/public/OHLC?pair={pair}&interval={interval}"
    data = _http_json(url, timeout=20)
    if not data or data.get("error"):
        return None
    result = data.get("result", {})
    # Kraken returns key as internal canonical name
    ohlc_data = None
    for key, val in result.items():
        if key != "last" and isinstance(val, list):
            ohlc_data = val
            break
    if not ohlc_data or len(ohlc_data) < 5:
        return None
    rows = []
    for c in ohlc_data:
        try:
            rows.append({
                "Date": pd.Timestamp(int(c[0]), unit="s", tz="UTC"),
                "Open": float(c[1]), "High": float(c[2]),
                "Low": float(c[3]), "Close": float(c[4]),
                "Volume": float(c[6]),  # index 6 = volume (5 = vwap)
            })
        except (IndexError, ValueError, TypeError):
            continue
    return _klines_to_df(rows)


# ===================================================================
# 6. COINCAP — Last-resort crypto (200 req/min, close-only)
# ===================================================================

def fetch_coincap_history(yf_sym: str, interval: str = "d1", days: int = 365) -> Optional[pd.DataFrame]:
    asset_id = _YF_TO_COINCAP.get(yf_sym)
    if not asset_id:
        return None
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - (days * 86400 * 1000)
    url = f"{COINCAP}/assets/{asset_id}/history?interval={interval}&start={start_ms}&end={end_ms}"
    data = _http_json(url, timeout=20)
    if not data or "data" not in data:
        return None
    points = data["data"]
    if len(points) < 5:
        return None
    rows = []
    for p in points:
        try:
            price = float(p["priceUsd"])
            rows.append({
                "Date": pd.Timestamp(p["time"], unit="ms"),
                "Close": price,
            })
        except (KeyError, ValueError, TypeError):
            continue
    if len(rows) < 5:
        return None
    df = pd.DataFrame(rows)
    df.set_index("Date", inplace=True)
    df.index = df.index.tz_localize(None)
    # Derive OHLV from close (approximate)
    df["Open"] = df["Close"].shift(1).fillna(df["Close"])
    df["High"] = df[["Open", "Close"]].max(axis=1) * 1.005
    df["Low"] = df[["Open", "Close"]].min(axis=1) * 0.995
    df["Volume"] = 0.0
    return df[["Open", "High", "Low", "Close", "Volume"]]


# ===================================================================
# FOREX: Frankfurter (ECB) + ExchangeRate-API
# ===================================================================

def fetch_frankfurter_history(yf_sym: str, days: int = 365) -> Optional[pd.DataFrame]:
    """Frankfurter (ECB rates). Unlimited, no auth, daily."""
    pair = _FOREX_MAP.get(yf_sym)
    if not pair:
        return None
    base, quote = pair
    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    end = datetime.now().strftime("%Y-%m-%d")
    url = f"{FRANKFURTER}/{start}..{end}?base={base}&symbols={quote}"
    data = _http_json(url, timeout=20)
    if not data or "rates" not in data:
        return None
    rates = data["rates"]
    if len(rates) < 5:
        return None
    rows = []
    prev_price = None
    for date_str, rate_dict in sorted(rates.items()):
        try:
            price = float(rate_dict[quote])
            o = prev_price if prev_price else price
            rows.append({
                "Date": pd.Timestamp(date_str),
                "Open": o, "High": max(o, price) * 1.0002,
                "Low": min(o, price) * 0.9998,
                "Close": price, "Volume": 0.0,
            })
            prev_price = price
        except (KeyError, ValueError, TypeError):
            continue
    if len(rows) < 5:
        return None
    df = pd.DataFrame(rows)
    df.set_index("Date", inplace=True)
    return df


def fetch_frankfurter_latest() -> dict[str, float]:
    url = f"{FRANKFURTER}/latest?base=USD"
    data = _http_json(url, timeout=10)
    if not data or "rates" not in data:
        return {}
    return data["rates"]


def fetch_exchangerate_latest() -> dict[str, float]:
    """ExchangeRate-API open endpoint. No auth, daily refresh."""
    url = f"{EXCHANGERATE}/latest/USD"
    data = _http_json(url, timeout=10)
    if not data or "rates" not in data:
        return {}
    return data["rates"]


# ===================================================================
# Fear & Greed Index — alternative.me (free, no auth)
# ===================================================================

def fetch_fear_greed() -> Optional[dict]:
    url = "https://api.alternative.me/fng/?limit=1"
    data = _http_json(url, timeout=10)
    if not data or "data" not in data or not data["data"]:
        return None
    fg = data["data"][0]
    return {
        "value": int(fg.get("value", 50)),
        "classification": fg.get("value_classification", "Neutral"),
    }


# ===================================================================
# Unified Multi-Source Fetcher — 7-exchange failover
# ===================================================================

_fetch_stats = {
    "binance_ok": 0, "binance_fail": 0,
    "bybit_ok": 0, "bybit_fail": 0,
    "okx_ok": 0, "okx_fail": 0,
    "kucoin_ok": 0, "kucoin_fail": 0,
    "kraken_ok": 0, "kraken_fail": 0,
    "coincap_ok": 0, "coincap_fail": 0,
    "frankfurter_ok": 0, "frankfurter_fail": 0,
    "yfinance_ok": 0, "yfinance_fail": 0,
}


def _is_crypto(symbol: str) -> bool:
    return symbol.endswith("-USD") and not symbol.startswith("^")


def _is_forex(symbol: str) -> bool:
    return symbol.endswith("=X")


def fetch_symbol_data_multi(symbol: str, period: str = "1y") -> Optional[pd.DataFrame]:
    """
    7-exchange failover data fetcher.
    Non-geo-blocked sources prioritized for GitHub Actions.

    Crypto:  KuCoin → Kraken → OKX → CoinCap → Binance → Bybit → yfinance
    Forex:   Frankfurter → yfinance
    Stocks:  yfinance

    Returns DataFrame with columns: Open, High, Low, Close, Volume
    """
    import yfinance as yf

    days = {"1y": 365, "6mo": 180, "3mo": 90, "1mo": 30}.get(period, 365)

    # --- CRYPTO: 7-exchange failover chain ---
    # Non-geo-blocked sources first for GitHub Actions compatibility
    if _is_crypto(symbol):

        # 1. KuCoin (no geo-block, weight-based limits)
        if not _circuit_open("kucoin"):
            kucoin_sym = _yf_to_kucoin(symbol)
            if kucoin_sym:
                df = fetch_kucoin_klines(kucoin_sym, ktype="1day", days=days)
                if df is not None and len(df) >= 20:
                    _fetch_stats["kucoin_ok"] += 1
                    return df
                _fetch_stats["kucoin_fail"] += 1
                _record_failure("kucoin")

        # 2. Kraken (no geo-block, ~1 req/s, max 720 candles)
        if not _circuit_open("kraken"):
            kraken_pair = _YF_TO_KRAKEN.get(symbol)
            if kraken_pair:
                df = fetch_kraken_ohlc(kraken_pair, interval=1440)
                if df is not None and len(df) >= 20:
                    _fetch_stats["kraken_ok"] += 1
                    return df
                _fetch_stats["kraken_fail"] += 1
                _record_failure("kraken")

        # 3. OKX (no geo-block for market data, 20 req/2s)
        if not _circuit_open("okx"):
            okx_sym = _yf_to_okx(symbol)
            if okx_sym:
                df = _fetch_okx_full(okx_sym, days=days)
                if df is not None and len(df) >= 20:
                    _fetch_stats["okx_ok"] += 1
                    return df
                _fetch_stats["okx_fail"] += 1
                _record_failure("okx")

        # 4. CoinCap (no geo-block, close-only, approximate OHLV)
        if not _circuit_open("coincap"):
            df = fetch_coincap_history(symbol, interval="d1", days=days)
            if df is not None and len(df) >= 20:
                _fetch_stats["coincap_ok"] += 1
                return df
            _fetch_stats["coincap_fail"] += 1
            _record_failure("coincap")

        # --- Geo-blocked sources (work locally, fail on GitHub Actions) ---

        # 5. Binance (geo-blocked from US/GitHub Actions)
        if not _ci_blocked("binance") and not _circuit_open("binance"):
            binance_sym = _yf_to_binance(symbol)
            if binance_sym:
                df = fetch_binance_klines(binance_sym, interval="1d", limit=min(days, 1000))
                if df is not None and len(df) >= 20:
                    _fetch_stats["binance_ok"] += 1
                    return df
                _fetch_stats["binance_fail"] += 1
                _record_failure("binance")

        # 6. Bybit (geo-blocked via CloudFront)
        if not _ci_blocked("bybit") and not _circuit_open("bybit"):
            bybit_sym = _yf_to_bybit(symbol)
            if bybit_sym:
                df = fetch_bybit_klines(bybit_sym, interval="D", limit=min(days, 1000))
                if df is not None and len(df) >= 20:
                    _fetch_stats["bybit_ok"] += 1
                    return df
                _fetch_stats["bybit_fail"] += 1
                _record_failure("bybit")

    # --- FOREX: Frankfurter → yfinance ---
    if _is_forex(symbol):
        df = fetch_frankfurter_history(symbol, days=days)
        if df is not None and len(df) >= 20:
            _fetch_stats["frankfurter_ok"] += 1
            return df
        _fetch_stats["frankfurter_fail"] += 1

    # --- FALLBACK: yfinance for everything (2 attempts, 5s delay) ---
    for yf_attempt in range(2):
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, auto_adjust=True)
            if df is not None and not df.empty and len(df) >= 20:
                _fetch_stats["yfinance_ok"] += 1
                return df
            _fetch_stats["yfinance_fail"] += 1
            break
        except Exception:
            if yf_attempt == 0:
                time.sleep(5)
            else:
                _fetch_stats["yfinance_fail"] += 1

    return None


def _fetch_okx_price(inst_id: str) -> Optional[float]:
    """OKX spot ticker price. No auth."""
    url = f"{OKX}/api/v5/market/ticker?instId={inst_id}"
    data = _http_json(url, timeout=10)
    if data and data.get("code") == "0" and data.get("data"):
        try:
            return float(data["data"][0]["last"])
        except (KeyError, ValueError, TypeError, IndexError):
            pass
    return None


def _fetch_kucoin_price(symbol: str) -> Optional[float]:
    """KuCoin spot ticker price. No auth."""
    url = f"{KUCOIN}/api/v1/market/orderbook/level1?symbol={symbol}"
    data = _http_json(url, timeout=10)
    if data and data.get("code") == "200000" and data.get("data"):
        try:
            return float(data["data"]["price"])
        except (KeyError, ValueError, TypeError):
            pass
    return None


def _fetch_kraken_price(pair: str) -> Optional[float]:
    """Kraken spot ticker price. No auth."""
    url = f"{KRAKEN}/0/public/Ticker?pair={pair}"
    data = _http_json(url, timeout=10)
    if not data or data.get("error"):
        return None
    result = data.get("result", {})
    for key, val in result.items():
        if key != "last" and isinstance(val, dict):
            try:
                return float(val["c"][0])  # c = last trade closed [price, lot-volume]
            except (KeyError, ValueError, TypeError, IndexError):
                pass
    return None


def _fetch_coincap_price(yf_sym: str) -> Optional[float]:
    """CoinCap current price. No auth."""
    asset_id = _YF_TO_COINCAP.get(yf_sym)
    if not asset_id:
        return None
    url = f"{COINCAP}/assets/{asset_id}"
    data = _http_json(url, timeout=10)
    if data and "data" in data:
        try:
            return float(data["data"]["priceUsd"])
        except (KeyError, ValueError, TypeError):
            pass
    return None


def fetch_latest_price_multi(symbol: str) -> Optional[float]:
    """
    Get latest price from best available source.
    Non-geo-blocked sources prioritized for GitHub Actions.
    Crypto: KuCoin → Kraken → OKX → CoinCap → Binance → Bybit → yfinance
    Others: yfinance
    """
    import yfinance as yf

    if _is_crypto(symbol):
        # --- Non-geo-blocked sources first (work from GitHub Actions) ---

        # 1. KuCoin (no geo-block, weight-based limits)
        if not _circuit_open("kucoin"):
            kucoin_sym = _yf_to_kucoin(symbol)
            if kucoin_sym:
                price = _fetch_kucoin_price(kucoin_sym)
                if price and price > 0:
                    return price

        # 2. Kraken (no geo-block, ~1 req/s)
        if not _circuit_open("kraken"):
            kraken_pair = _YF_TO_KRAKEN.get(symbol)
            if kraken_pair:
                price = _fetch_kraken_price(kraken_pair)
                if price and price > 0:
                    return price

        # 3. OKX (no geo-block for market data)
        if not _circuit_open("okx"):
            okx_sym = _yf_to_okx(symbol)
            if okx_sym:
                price = _fetch_okx_price(okx_sym)
                if price and price > 0:
                    return price

        # 4. CoinCap (no geo-block, 200 req/min)
        if not _circuit_open("coincap"):
            price = _fetch_coincap_price(symbol)
            if price and price > 0:
                return price

        # --- Geo-blocked sources (work locally, fail on GitHub Actions) ---

        # 5. Binance (geo-blocked from US/GitHub Actions)
        if not _ci_blocked("binance") and not _circuit_open("binance"):
            binance_sym = _yf_to_binance(symbol)
            if binance_sym:
                price = fetch_binance_price(binance_sym)
                if price and price > 0:
                    return price

        # 6. Bybit (geo-blocked via CloudFront)
        if not _ci_blocked("bybit") and not _circuit_open("bybit"):
            bybit_sym = _yf_to_bybit(symbol)
            if bybit_sym:
                price = fetch_bybit_price(bybit_sym)
                if price and price > 0:
                    return price

    # 7. Fallback: yfinance
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="2d", interval="5m", auto_adjust=True)
        if df is not None and not df.empty:
            last = float(df["Close"].dropna().iloc[-1])
            if last > 0:
                return last
    except Exception:
        pass
    return None


def get_fetch_stats() -> dict:
    return dict(_fetch_stats)


def print_fetch_summary():
    s = _fetch_stats
    total_ok = sum(v for k, v in s.items() if k.endswith("_ok"))
    total_fail = sum(v for k, v in s.items() if k.endswith("_fail"))
    if total_ok + total_fail == 0:
        return

    sources = []
    for name in ["binance", "bybit", "okx", "kucoin", "kraken", "coincap", "frankfurter", "yfinance"]:
        ok = s.get(f"{name}_ok", 0)
        fail = s.get(f"{name}_fail", 0)
        if ok + fail > 0:
            label = f"{name.capitalize()} {ok}/{ok+fail}"
            if _circuit_open(name):
                label += " [TRIPPED]"
            sources.append(label)
    print(f"  Data sources: {' | '.join(sources)}")
    print(f"  Total: {total_ok} fetched, {total_fail} fallthrough")
    # Report circuit breaker and CI skip status
    tripped = [name for name in _source_failures if _circuit_open(name)]
    if tripped:
        print(f"  Circuit breakers tripped: {', '.join(tripped)}")
    if _IN_GITHUB_ACTIONS:
        print(f"  CI geo-block skip: {', '.join(sorted(_CI_BLOCKED_SOURCES))}")


# ===================================================================
# Bulk fetch helpers
# ===================================================================

def fetch_all_binance_prices_bulk() -> dict[str, float]:
    """All Binance prices in one call (weight: 4). Returns {yf_symbol: price}."""
    prices = fetch_binance_all_prices()
    if not prices:
        return {}
    yf_prices = {}
    for binance_sym, price in prices.items():
        if binance_sym.endswith("USDT"):
            yf_sym = binance_sym.replace("USDT", "") + "-USD"
            yf_prices[yf_sym] = price
    return yf_prices


def fetch_all_funding_rates_bulk() -> dict[str, dict]:
    """All Binance futures funding rates in one call."""
    rates = fetch_binance_funding_rates()
    if not rates:
        return {}
    result = {}
    for item in rates:
        sym = item["symbol"]
        if sym.endswith("USDT"):
            yf_sym = sym.replace("USDT", "") + "-USD"
            result[yf_sym] = item
    return result
