#!/usr/bin/env python3
"""
Shared API Failover Module for Alpha Engine
=============================================
Provides resilient data fetching with automatic failover across multiple
exchange APIs. Created because Binance returns HTTP 451 (geo-blocked) on
GitHub Actions US runners.

Failover chain (per source type):
  Spot OHLCV / Price:
    1. Binance mirrors (api, api1, api2, api3, data-api, binance.us)
    2. Bybit v5 market kline / tickers
    3. CoinGecko simple/price + coins/{id}/ohlc
    4. KuCoin v1 market candles
    5. CryptoCompare histohour / histoday

  Futures (funding rate, OI):
    1. Binance fapi mirrors
    2. Bybit v5 linear tickers / fundingRate
    3. CoinGlass (if key available)

Exports:
    fetch_price(symbol) -> float | None
    fetch_klines(symbol, interval, limit) -> list[list] | None
    fetch_ticker_24h(symbol) -> dict | None
    fetch_funding_rate(symbol) -> dict | None
    fetch_orderbook(symbol, limit) -> dict | None

Each function returns None on total failure (all sources exhausted).
Results are cached in-memory for 60s (configurable).
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import urllib.request
import urllib.error
from typing import Optional
from urllib.parse import urlparse

_log = logging.getLogger("alpha_engine.api_failover")

# ---------------------------------------------------------------------------
# Windows UTF-8 fix
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            # try:
            #     _stream.reconfigure(encoding="utf-8", errors="replace")
            # except Exception:
            #     pass
            pass

# ---------------------------------------------------------------------------
# Exchange base URLs
# ---------------------------------------------------------------------------
BINANCE_SPOT_BASES = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
    "https://api.binance.us",
]

BINANCE_FAPI_BASES = [
    "https://fapi.binance.com",
    "https://fapi1.binance.com",
    "https://fapi2.binance.com",
]

BYBIT_BASE = "https://api.bybit.com"
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
KUCOIN_BASE = "https://api.kucoin.com"
CRYPTOCOMPARE_BASE = "https://min-api.cryptocompare.com/data"

# In CI, prefer non-geo-blocked endpoints first
if os.environ.get("GITHUB_ACTIONS"):
    _preferred_spot = ["https://data-api.binance.vision", "https://api.binance.us"]
    BINANCE_SPOT_BASES = _preferred_spot + [
        u for u in BINANCE_SPOT_BASES if u not in _preferred_spot
    ]

# ---------------------------------------------------------------------------
# Symbol mapping helpers
# ---------------------------------------------------------------------------
_COINGECKO_IDS = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
    "BNB": "binancecoin", "XRP": "ripple", "ADA": "cardano",
    "AVAX": "avalanche-2", "LINK": "chainlink", "DOT": "polkadot",
    "ATOM": "cosmos", "NEAR": "near", "MATIC": "matic-network",
    "DOGE": "dogecoin", "SHIB": "shiba-inu", "LTC": "litecoin",
    "UNI": "uniswap", "AAVE": "aave", "ARB": "arbitrum",
    "OP": "optimism", "SUI": "sui", "FIL": "filecoin",
    "APT": "aptos", "INJ": "injective-protocol", "FET": "fetch-ai",
    "PEPE": "pepe", "WIF": "dogwifcoin", "RENDER": "render-token",
    "TON": "the-open-network", "TRX": "tron", "XLM": "stellar",
    "BCH": "bitcoin-cash", "ETC": "ethereum-classic", "HBAR": "hedera-hashgraph",
    "SEI": "sei-network", "TIA": "celestia", "BONK": "bonk",
    "FLOKI": "floki", "STX": "blockstack", "CAKE": "pancakeswap-token",
    "TAO": "bittensor", "KAS": "kaspa", "ONDO": "ondo-finance",
    "ICP": "internet-computer", "HYPE": "hyperliquid",
    "POL": "polygon-ecosystem-token",
}

_SYMBOL_ALIASES = {
    "MATICUSDT": "POLUSDT",
    "MATICUSD": "POLUSDT",
}

# Interval mapping: Binance interval -> Bybit interval (minutes)
_BYBIT_INTERVAL_MAP = {
    "1m": "1", "3m": "3", "5m": "5", "15m": "15", "30m": "30",
    "1h": "60", "2h": "120", "4h": "240", "6h": "360", "12h": "720",
    "1d": "D", "1w": "W", "1M": "M",
}

# Interval -> seconds (for CryptoCompare endpoint selection)
_INTERVAL_SECONDS = {
    "1m": 60, "3m": 180, "5m": 300, "15m": 900, "30m": 1800,
    "1h": 3600, "2h": 7200, "4h": 14400, "6h": 21600, "12h": 43200,
    "1d": 86400, "1w": 604800,
}


def _normalize_symbol(symbol: str) -> str:
    """Normalize to BTCUSDT format."""
    if not symbol:
        return ""
    s = symbol.upper().replace("-", "").replace("/", "")
    if s.endswith("USD") and not s.endswith("USDT"):
        s = s + "T"
    return _SYMBOL_ALIASES.get(s, s)


def _base_coin(symbol: str) -> str:
    """Extract base coin from BTCUSDT -> BTC."""
    s = _normalize_symbol(symbol)
    for suffix in ("USDT", "BUSD", "USD"):
        if s.endswith(suffix):
            return s[:-len(suffix)]
    return s


def _to_coingecko_id(symbol: str) -> Optional[str]:
    """Map symbol to CoinGecko ID."""
    base = _base_coin(symbol)
    return _COINGECKO_IDS.get(base)


def _to_kucoin_symbol(symbol: str) -> str:
    """BTCUSDT -> BTC-USDT."""
    s = _normalize_symbol(symbol)
    if s.endswith("USDT"):
        return s[:-4] + "-USDT"
    return s


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------
_HTTP_TIMEOUT = 5  # 5 seconds per source
_USER_AGENT = "AlphaEngine-Failover/1.0"
_GEOBLOCK_WARNED = set()


def _http_get_json(url: str, timeout: int = _HTTP_TIMEOUT, _retries: int = 2) -> Optional[dict | list]:
    """Fetch JSON from URL. Retries on 429 with exponential backoff. Returns None on any failure."""
    for attempt in range(_retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                code = resp.getcode()
                if code == 451:
                    parsed = urlparse(url)
                    key = (parsed.netloc, parsed.path)
                    if key not in _GEOBLOCK_WARNED:
                        _log.warning("Geo-blocked (451) on %s%s; suppressing repeated warnings for this endpoint", parsed.netloc, parsed.path)
                        _GEOBLOCK_WARNED.add(key)
                    else:
                        _log.debug("Geo-blocked (451): %s", url)
                    return None
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            if exc.code == 451:
                parsed = urlparse(url)
                key = (parsed.netloc, parsed.path)
                if key not in _GEOBLOCK_WARNED:
                    _log.warning("Geo-blocked (451) on %s%s; suppressing repeated warnings for this endpoint", parsed.netloc, parsed.path)
                    _GEOBLOCK_WARNED.add(key)
                else:
                    _log.debug("Geo-blocked (451): %s", url)
                return None
            if exc.code == 429 and attempt < _retries:
                wait = (attempt + 1) * 2  # 2s, 4s backoff
                _log.info("Rate-limited (429) on %s, retrying in %ds...", url, wait)
                time.sleep(wait)
                continue
            _log.debug("HTTP %d %s: %s", exc.code, url, exc)
            return None
        except Exception as exc:
            _log.debug("HTTP failed %s: %s", url, exc)
            return None
    return None


# ---------------------------------------------------------------------------
# In-memory cache (60s TTL)
# ---------------------------------------------------------------------------
_CACHE_TTL = 60  # seconds
_cache: dict[str, tuple[float, object]] = {}


def _cache_get(key: str):
    """Return cached value or None if expired/missing."""
    entry = _cache.get(key)
    if entry and (time.time() - entry[0]) < _CACHE_TTL:
        return entry[1]
    return None


def _cache_set(key: str, value):
    """Store value in cache."""
    _cache[key] = (time.time(), value)


# ---------------------------------------------------------------------------
# fetch_price(symbol) -> float | None
# ---------------------------------------------------------------------------
def fetch_price(symbol: str) -> Optional[float]:
    """Fetch current price from best available source.

    Tries: Binance spot -> Bybit -> CoinGecko -> KuCoin
    Returns float price or None.
    """
    sym = _normalize_symbol(symbol)
    if not sym:
        return None

    cache_key = f"price:{sym}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    price = None
    source = None

    # 1. Binance spot mirrors
    for base in BINANCE_SPOT_BASES:
        data = _http_get_json(f"{base}/api/v3/ticker/price?symbol={sym}")
        if data and "price" in data:
            try:
                price = float(data["price"])
                source = f"binance({base.split('//')[1].split('.')[0]})"
                break
            except (ValueError, TypeError):
                continue

    # 2. Bybit
    if price is None:
        data = _http_get_json(
            f"{BYBIT_BASE}/v5/market/tickers?category=spot&symbol={sym}"
        )
        if data and data.get("retCode") == 0:
            tickers = data.get("result", {}).get("list", [])
            if tickers:
                try:
                    price = float(tickers[0].get("lastPrice", 0))
                    source = "bybit"
                except (ValueError, TypeError):
                    pass
        # Try linear (perpetual) if spot failed
        if price is None:
            data = _http_get_json(
                f"{BYBIT_BASE}/v5/market/tickers?category=linear&symbol={sym}"
            )
            if data and data.get("retCode") == 0:
                tickers = data.get("result", {}).get("list", [])
                if tickers:
                    try:
                        price = float(tickers[0].get("lastPrice", 0))
                        source = "bybit_linear"
                    except (ValueError, TypeError):
                        pass

    # 3. CoinGecko
    if price is None:
        cg_id = _to_coingecko_id(sym)
        if cg_id:
            data = _http_get_json(
                f"{COINGECKO_BASE}/simple/price?ids={cg_id}&vs_currencies=usd"
            )
            if data and cg_id in data:
                try:
                    price = float(data[cg_id].get("usd", 0))
                    source = "coingecko"
                except (ValueError, TypeError):
                    pass

    # 4. KuCoin
    if price is None:
        kc_sym = _to_kucoin_symbol(sym)
        data = _http_get_json(
            f"{KUCOIN_BASE}/api/v1/market/orderbook/level1?symbol={kc_sym}"
        )
        if data and data.get("code") == "200000":
            kc_data = data.get("data")
            if isinstance(kc_data, dict):
                try:
                    price = float(kc_data.get("price", 0) or 0)
                    source = "kucoin"
                except (ValueError, TypeError):
                    pass

    if price and price > 0:
        _log.debug("fetch_price(%s) = %.8f [%s]", sym, price, source)
        _cache_set(cache_key, price)
        return price

    _log.warning("fetch_price(%s): ALL sources failed", sym)
    return None


# ---------------------------------------------------------------------------
# fetch_klines(symbol, interval, limit) -> list[list] | None
# ---------------------------------------------------------------------------
def fetch_klines(symbol: str, interval: str = "1h",
                 limit: int = 100) -> Optional[list]:
    """Fetch OHLCV klines from best available source.

    Returns Binance-compatible format: [[open_time, open, high, low, close, volume, ...], ...]
    All numeric values are strings (Binance format) for compatibility.

    Tries: Binance -> Bybit -> KuCoin -> CoinGecko -> CryptoCompare
    """
    sym = _normalize_symbol(symbol)
    if not sym:
        return None

    cache_key = f"klines:{sym}:{interval}:{limit}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    result = None
    source = None

    # 1. Binance spot mirrors
    for base in BINANCE_SPOT_BASES:
        data = _http_get_json(
            f"{base}/api/v3/klines?symbol={sym}&interval={interval}&limit={limit}"
        )
        if data and isinstance(data, list) and len(data) > 0:
            result = data
            source = f"binance({base.split('//')[1].split('.')[0]})"
            break

    # 2. Bybit
    if result is None:
        bybit_interval = _BYBIT_INTERVAL_MAP.get(interval)
        if bybit_interval:
            data = _http_get_json(
                f"{BYBIT_BASE}/v5/market/kline?category=linear&symbol={sym}"
                f"&interval={bybit_interval}&limit={limit}"
            )
            if data and data.get("retCode") == 0:
                raw_list = data.get("result", {}).get("list", [])
                if raw_list:
                    # Bybit returns newest first; reverse to match Binance order
                    # Format: [startTime, open, high, low, close, volume, turnover]
                    result = [
                        [int(k[0]), k[1], k[2], k[3], k[4], k[5]]
                        for k in reversed(raw_list)
                    ]
                    source = "bybit"

    # 3. KuCoin
    if result is None:
        kc_sym = _to_kucoin_symbol(sym)
        # KuCoin interval format: 1min, 5min, 15min, 30min, 1hour, 4hour, 1day, 1week
        _kc_interval_map = {
            "1m": "1min", "3m": "3min", "5m": "5min", "15m": "15min",
            "30m": "30min", "1h": "1hour", "2h": "2hour", "4h": "4hour",
            "6h": "6hour", "8h": "8hour", "12h": "12hour",
            "1d": "1day", "1w": "1week",
        }
        kc_interval = _kc_interval_map.get(interval)
        if kc_interval:
            end_at = int(time.time())
            interval_secs = _INTERVAL_SECONDS.get(interval, 3600)
            start_at = end_at - (limit + 5) * interval_secs
            data = _http_get_json(
                f"{KUCOIN_BASE}/api/v1/market/candles"
                f"?type={kc_interval}&symbol={kc_sym}"
                f"&startAt={start_at}&endAt={end_at}"
            )
            if data and data.get("code") == "200000" and data.get("data"):
                # KuCoin: [time, open, close, high, low, volume, turnover] -- newest first
                raw = data["data"]
                result = [
                    [int(k[0]) * 1000, k[1], k[3], k[4], k[2], k[5]]
                    for k in reversed(raw)
                ][-limit:]
                source = "kucoin"

    # 4. CoinGecko (daily only, limited resolution)
    if result is None:
        cg_id = _to_coingecko_id(sym)
        if cg_id:
            # CoinGecko /ohlc only supports days=1,7,14,30,90,180,365,max
            interval_secs = _INTERVAL_SECONDS.get(interval, 3600)
            days = max(1, (limit * interval_secs) // 86400 + 1)
            if days > 365:
                days = 365
            data = _http_get_json(
                f"{COINGECKO_BASE}/coins/{cg_id}/ohlc?vs_currency=usd&days={days}"
            )
            if data and isinstance(data, list) and len(data) > 0:
                # CoinGecko OHLC: [timestamp, open, high, low, close]
                result = [
                    [d[0], str(d[1]), str(d[2]), str(d[3]), str(d[4]), "0"]
                    for d in data
                ][-limit:]
                source = "coingecko"

    # 5. CryptoCompare
    if result is None:
        fsym = _base_coin(sym)
        interval_secs = _INTERVAL_SECONDS.get(interval, 3600)
        if interval_secs >= 86400:
            cc_endpoint = "v2/histoday"
        elif interval_secs >= 3600:
            cc_endpoint = "v2/histohour"
        else:
            cc_endpoint = "v2/histominute"
        data = _http_get_json(
            f"{CRYPTOCOMPARE_BASE}/{cc_endpoint}"
            f"?fsym={fsym}&tsym=USD&limit={limit}"
        )
        if data and isinstance(data, dict):
            hist = data.get("Data", {}).get("Data", [])
            if hist:
                result = [
                    [
                        d["time"] * 1000,
                        str(d["open"]),
                        str(d["high"]),
                        str(d["low"]),
                        str(d["close"]),
                        str(d.get("volumeto", 0)),
                    ]
                    for d in hist
                    if d.get("close", 0) > 0
                ]
                source = "cryptocompare"

    if result:
        _log.debug("fetch_klines(%s, %s, %d) -> %d bars [%s]",
                    sym, interval, limit, len(result), source)
        _cache_set(cache_key, result)
        return result

    _log.warning("fetch_klines(%s, %s, %d): ALL sources failed",
                 sym, interval, limit)
    return None


# ---------------------------------------------------------------------------
# fetch_ticker_24h(symbol) -> dict | None
# ---------------------------------------------------------------------------
def fetch_ticker_24h(symbol: str = "") -> Optional[dict | list]:
    """Fetch 24h ticker statistics.

    If symbol is empty, returns all tickers (list).
    If symbol is provided, returns single ticker dict.

    Returns Binance-compatible format with keys:
        symbol, priceChange, priceChangePercent, lastPrice, volume, quoteVolume
    """
    sym = _normalize_symbol(symbol) if symbol else ""

    cache_key = f"ticker24h:{sym or 'ALL'}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    result = None
    source = None

    # 1. Binance spot mirrors
    for base in BINANCE_SPOT_BASES:
        path = f"{base}/api/v3/ticker/24hr"
        if sym:
            path += f"?symbol={sym}"
        data = _http_get_json(path)
        if data is not None:
            result = data
            source = "binance"
            break

    # 2. Bybit
    if result is None:
        path = f"{BYBIT_BASE}/v5/market/tickers?category=spot"
        if sym:
            path += f"&symbol={sym}"
        data = _http_get_json(path)
        if data and data.get("retCode") == 0:
            tickers = data.get("result", {}).get("list", [])
            if tickers:
                if sym:
                    t = tickers[0]
                    result = {
                        "symbol": t.get("symbol", sym),
                        "priceChange": str(float(t.get("lastPrice", 0)) - float(t.get("prevPrice24h", 0))),
                        "priceChangePercent": t.get("price24hPcnt", "0"),
                        "lastPrice": t.get("lastPrice", "0"),
                        "volume": t.get("volume24h", "0"),
                        "quoteVolume": t.get("turnover24h", "0"),
                    }
                else:
                    result = [
                        {
                            "symbol": t.get("symbol", ""),
                            "priceChange": str(float(t.get("lastPrice", 0)) - float(t.get("prevPrice24h", 0))),
                            "priceChangePercent": t.get("price24hPcnt", "0"),
                            "lastPrice": t.get("lastPrice", "0"),
                            "volume": t.get("volume24h", "0"),
                            "quoteVolume": t.get("turnover24h", "0"),
                        }
                        for t in tickers
                    ]
                source = "bybit"

    # 3. CoinGecko (single symbol only)
    if result is None and sym:
        cg_id = _to_coingecko_id(sym)
        if cg_id:
            data = _http_get_json(
                f"{COINGECKO_BASE}/simple/price?ids={cg_id}"
                f"&vs_currencies=usd&include_24hr_vol=true&include_24hr_change=true"
            )
            if data and cg_id in data:
                info = data[cg_id]
                price = info.get("usd", 0)
                change_pct = info.get("usd_24h_change", 0)
                result = {
                    "symbol": sym,
                    "lastPrice": str(price),
                    "priceChangePercent": str(round(change_pct, 4)),
                    "priceChange": str(round(price * change_pct / 100, 8)),
                    "volume": "0",
                    "quoteVolume": str(info.get("usd_24h_vol", 0)),
                }
                source = "coingecko"

    if result is not None:
        _log.debug("fetch_ticker_24h(%s) [%s]", sym or "ALL", source)
        _cache_set(cache_key, result)
        return result

    _log.warning("fetch_ticker_24h(%s): ALL sources failed", sym or "ALL")
    return None


# ---------------------------------------------------------------------------
# fetch_funding_rate(symbol) -> dict | None
# ---------------------------------------------------------------------------
def fetch_funding_rate(symbol: str = "BTCUSDT") -> Optional[dict]:
    """Fetch current funding rate.

    Returns: {rate: float, source: str} or None.
    Rate is the raw decimal value (e.g., 0.0001 = 0.01%).

    Tries: Binance fapi -> Bybit v5 -> None
    """
    sym = _normalize_symbol(symbol)
    if not sym:
        return None

    cache_key = f"funding:{sym}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    result = None

    # 1. Binance fapi mirrors
    for base in BINANCE_FAPI_BASES:
        data = _http_get_json(f"{base}/fapi/v1/premiumIndex?symbol={sym}")
        if data and isinstance(data, dict) and "lastFundingRate" in data:
            try:
                result = {
                    "rate": float(data["lastFundingRate"]),
                    "markPrice": float(data.get("markPrice", 0)),
                    "indexPrice": float(data.get("indexPrice", 0)),
                    "source": "binance_fapi",
                }
                break
            except (ValueError, TypeError):
                continue

    # 2. Bybit
    if result is None:
        data = _http_get_json(
            f"{BYBIT_BASE}/v5/market/tickers?category=linear&symbol={sym}"
        )
        if data and data.get("retCode") == 0:
            tickers = data.get("result", {}).get("list", [])
            if tickers:
                try:
                    t = tickers[0]
                    result = {
                        "rate": float(t.get("fundingRate", 0)),
                        "markPrice": float(t.get("markPrice", 0)),
                        "indexPrice": float(t.get("indexPrice", 0)),
                        "source": "bybit",
                    }
                except (ValueError, TypeError):
                    pass

    if result:
        _log.debug("fetch_funding_rate(%s) = %.6f [%s]",
                    sym, result["rate"], result["source"])
        _cache_set(cache_key, result)
        return result

    _log.warning("fetch_funding_rate(%s): ALL sources failed", sym)
    return None


# ---------------------------------------------------------------------------
# fetch_orderbook(symbol, limit) -> dict | None
# ---------------------------------------------------------------------------
def fetch_orderbook(symbol: str, limit: int = 20) -> Optional[dict]:
    """Fetch order book depth.

    Returns: {bids: [[price, qty], ...], asks: [[price, qty], ...], source: str}
    Prices and quantities are strings.

    Tries: Binance -> Bybit -> KuCoin
    """
    sym = _normalize_symbol(symbol)
    if not sym:
        return None

    cache_key = f"orderbook:{sym}:{limit}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    result = None

    # 1. Binance spot mirrors
    for base in BINANCE_SPOT_BASES:
        data = _http_get_json(
            f"{base}/api/v3/depth?symbol={sym}&limit={limit}"
        )
        if data and "bids" in data and "asks" in data:
            result = {
                "bids": data["bids"],
                "asks": data["asks"],
                "source": "binance",
            }
            break

    # 2. Bybit
    if result is None:
        data = _http_get_json(
            f"{BYBIT_BASE}/v5/market/orderbook?category=spot&symbol={sym}&limit={limit}"
        )
        if data and data.get("retCode") == 0:
            book = data.get("result", {})
            if book.get("b") and book.get("a"):
                result = {
                    "bids": book["b"],
                    "asks": book["a"],
                    "source": "bybit",
                }

    # 3. KuCoin
    if result is None:
        kc_sym = _to_kucoin_symbol(sym)
        kc_limit = "20" if limit <= 20 else "100"
        data = _http_get_json(
            f"{KUCOIN_BASE}/api/v1/market/orderbook/level2_{kc_limit}?symbol={kc_sym}"
        )
        if data and data.get("code") == "200000" and data.get("data"):
            book = data["data"]
            result = {
                "bids": book.get("bids", []),
                "asks": book.get("asks", []),
                "source": "kucoin",
            }

    if result:
        _log.debug("fetch_orderbook(%s, %d) [%s]", sym, limit, result["source"])
        _cache_set(cache_key, result)
        return result

    _log.warning("fetch_orderbook(%s, %d): ALL sources failed", sym, limit)
    return None


# ---------------------------------------------------------------------------
# Resilient price fetch alias — imported by signal generators with fallback
# ---------------------------------------------------------------------------

# Alias so signal generators can do:
#   try: from alpha_engine.api_failover import fetch_price_resilient
#   except: from api_failover import fetch_price_resilient
# When the import fails entirely (module run directly, alpha_engine not on
# sys.path), callers fall back to a minimal inline Binance spot fetch.
# The inline code does NOT need Bybit/CoinGecko/KuCoin because those are
# already covered by fetch_price() when it IS importable.
fetch_price_resilient = fetch_price


# ---------------------------------------------------------------------------
# Convenience: symbol validation
# ---------------------------------------------------------------------------
def is_crypto_symbol(symbol: str) -> bool:
    """Return True if symbol looks like a crypto pair (not forex/equity)."""
    if not symbol:
        return False
    s = symbol.upper()
    # Forex pairs
    if "=" in s or s.endswith("JPY") and not s.startswith("0"):
        return False
    # Common equities
    equities = {"SPY", "QQQ", "NVDA", "AAPL", "MSFT", "TSLA", "AMZN", "META", "GOOGL"}
    if s in equities:
        return False
    return True


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print("=== API Failover Module Test ===\n")

    # Test price
    for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
        p = fetch_price(sym)
        print(f"  Price {sym}: {p}")

    # Test klines
    klines = fetch_klines("BTCUSDT", "1h", 5)
    if klines:
        print(f"\n  Klines BTCUSDT 1h: {len(klines)} bars")
        print(f"  Last bar: {klines[-1][:6]}")
    else:
        print("\n  Klines: FAILED")

    # Test ticker
    ticker = fetch_ticker_24h("BTCUSDT")
    if ticker:
        print(f"\n  Ticker 24h: {ticker.get('lastPrice')} ({ticker.get('priceChangePercent')}%)")
    else:
        print("\n  Ticker: FAILED")

    # Test funding
    fr = fetch_funding_rate("BTCUSDT")
    if fr:
        print(f"\n  Funding rate: {fr['rate']} [{fr['source']}]")
    else:
        print("\n  Funding: FAILED")

    print("\n=== Done ===")
