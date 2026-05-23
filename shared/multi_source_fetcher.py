"""
Multi-Source Crypto Data Fetcher — Shared Failover Module
==========================================================
5-source failover chain for all ML scanners (mercury2, ml_crypto_predictor,
claude_gainer_ml, crypto_ml_edge).

Failover order (non-geo-blocked first for GitHub Actions):
  1. OKX          (no geo-block, 20 req/2s)
  2. CoinGecko    (no geo-block, 30 req/min free tier)
  3. Kraken       (no geo-block, public API, good liquidity)
  4. CryptoCompare(no geo-block, 100K calls/month free)
  5. Binance      (geo-blocked from US GitHub Actions runners — 451)
  6. yfinance     (scraper fallback, unreliable but wide coverage)

Interface:
  fetch_klines(symbol, interval, limit) -> list[list]   # raw OHLCV arrays
  fetch_current_price(symbol) -> float                   # latest price
  fetch_current_prices_bulk(symbols) -> dict[str, float] # batch prices

Symbols use Binance format (BTCUSDT) since that's what all scanners use.
The module handles conversion to each exchange's format internally.

Cache: 5-minute in-memory TTL cache to avoid hammering APIs.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# In-memory TTL cache (5 minutes)
# ---------------------------------------------------------------------------

_cache: dict[str, tuple[float, object]] = {}
_CACHE_TTL = 300  # 5 minutes


def _cache_get(key: str):
    """Return cached value if still valid, else None."""
    entry = _cache.get(key)
    if entry and (time.time() - entry[0]) < _CACHE_TTL:
        return entry[1]
    return None


def _cache_set(key: str, value):
    """Store value in cache with current timestamp."""
    _cache[key] = (time.time(), value)


def clear_cache():
    """Clear the entire cache (call between scan cycles if needed)."""
    _cache.clear()


# ---------------------------------------------------------------------------
# Circuit breaker — skip sources after repeated failures
# ---------------------------------------------------------------------------

_source_failures: dict[str, int] = {}
_CIRCUIT_BREAKER_THRESHOLD = 3

# CI geo-block detection
_IN_GITHUB_ACTIONS = bool(os.environ.get("GITHUB_ACTIONS"))
_CI_BLOCKED_SOURCES = {"binance"}


def reset_circuit_breakers():
    """Reset failure counts — call at the start of each scan cycle."""
    _source_failures.clear()


def _circuit_open(source: str) -> bool:
    return _source_failures.get(source, 0) >= _CIRCUIT_BREAKER_THRESHOLD


def _record_failure(source: str):
    _source_failures[source] = _source_failures.get(source, 0) + 1
    if _source_failures[source] == _CIRCUIT_BREAKER_THRESHOLD:
        print(f"  [multi-source] {source} circuit breaker tripped after {_CIRCUIT_BREAKER_THRESHOLD} failures")


def _ci_blocked(source: str) -> bool:
    return _IN_GITHUB_ACTIONS and source in _CI_BLOCKED_SOURCES


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _http_get(url: str, timeout: int = 15, headers: dict | None = None) -> Optional[bytes]:
    """HTTP GET with retry."""
    hdrs = {"User-Agent": "MultiSourceFetcher/1.0"}
    if headers:
        hdrs.update(headers)
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code in (451, 403, 429):
                return None  # Don't retry geo-blocks or rate limits
            if attempt == 0:
                time.sleep(2)
        except Exception:
            if attempt == 0:
                time.sleep(2)
    return None


def _http_json(url: str, timeout: int = 15, headers: dict | None = None):
    """HTTP GET returning parsed JSON."""
    raw = _http_get(url, timeout, headers)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Symbol mapping
# ---------------------------------------------------------------------------

def _binance_to_okx(symbol: str) -> Optional[str]:
    """BTCUSDT -> BTC-USDT"""
    if symbol.endswith("USDT"):
        return symbol[:-4] + "-USDT"
    if symbol.endswith("BUSD"):
        return symbol[:-4] + "-USDT"
    return None


def _binance_to_coingecko(symbol: str) -> Optional[str]:
    """BTCUSDT -> bitcoin (CoinGecko ID)"""
    _MAP = {
        "BTC": "bitcoin", "ETH": "ethereum", "BNB": "binancecoin",
        "XRP": "ripple", "SOL": "solana", "ADA": "cardano",
        "AVAX": "avalanche-2", "DOT": "polkadot", "LINK": "chainlink",
        "MATIC": "matic-network", "LTC": "litecoin", "TRX": "tron",
        "ETC": "ethereum-classic", "BCH": "bitcoin-cash",
        "ATOM": "cosmos", "NEAR": "near", "ALGO": "algorand",
        "FIL": "filecoin", "ICP": "internet-computer",
        "VET": "vechain", "HBAR": "hedera-hashgraph",
        "DOGE": "dogecoin", "SHIB": "shiba-inu",
        "PEPE": "pepe", "FLOKI": "floki", "BONK": "bonk",
        "SAND": "the-sandbox", "MANA": "decentraland",
        "ENJ": "enjin-coin", "CHZ": "chiliz", "THETA": "theta-token",
        "GRT": "the-graph", "ZEC": "zcash", "DASH": "dash",
        "APT": "aptos", "OP": "optimism", "ARB": "arbitrum",
        "UNI": "uniswap", "AAVE": "aave", "MKR": "maker",
        "CRV": "curve-dao-token", "LDO": "lido-dao",
        "RNDR": "render-token", "INJ": "injective-protocol",
        "TIA": "celestia", "SEI": "sei-network", "SUI": "sui",
        "FET": "fetch-ai", "WIF": "dogwifcoin",
        "STX": "blockstack", "IMX": "immutable-x",
        "RUNE": "thorchain", "FTM": "fantom",
    }
    base = symbol.replace("USDT", "").replace("BUSD", "")
    return _MAP.get(base)


def _binance_to_cryptocompare(symbol: str) -> Optional[str]:
    """BTCUSDT -> BTC (CryptoCompare uses plain ticker)"""
    if symbol.endswith("USDT"):
        return symbol[:-4]
    if symbol.endswith("BUSD"):
        return symbol[:-4]
    return None


# Delisted / rebranded yfinance tickers -- map old ticker to working one
_YF_TICKER_REMAP = {
    "RNDR-USD": "RENDER-USD", "FTM-USD": "S-USD", "COMP-USD": "COMP1-USD",
    "ZK-USD": "ZKSYNC-USD", "THE-USD": "THE1-USD", "TAO-USD": "TAO22974-USD",
    "HIFI-USD": "HIFI1-USD", "IMX-USD": "IMX1-USD", "MEW-USD": "MEW1-USD",
    "ZRO-USD": "ZRO1-USD", "SUI-USD": "SUI20947-USD", "POPCAT-USD": "POPCAT1-USD",
    "ROBO-USD": "ROBO1-USD", "PEPE-USD": "PEPE24478-USD", "HYPE-USD": "HYPE32196-USD",
    "PIXEL-USD": "PORTAL-USD", "TON-USD": "TON11419-USD",
}


def _binance_to_yfinance(symbol: str) -> Optional[str]:
    """BTCUSDT -> BTC-USD (with delisted ticker remap)"""
    if symbol.endswith("USDT") or symbol.endswith("BUSD"):
        base = symbol.replace("USDT", "").replace("BUSD", "")
        yf_sym = f"{base}-USD"
        return _YF_TICKER_REMAP.get(yf_sym, yf_sym)
    return None


def _binance_to_kraken(symbol: str) -> Optional[str]:
    """BTCUSDT -> XBTUSD, ETHUSDT -> XETHZUSD, others -> {base}USD"""
    _KRAKEN_MAP = {
        "BTC": "XBTUSD",
        "ETH": "XETHZUSD",
    }
    if symbol.endswith("USDT") or symbol.endswith("BUSD"):
        base = symbol.replace("USDT", "").replace("BUSD", "")
        return _KRAKEN_MAP.get(base, f"{base}USD")
    return None


# ---------------------------------------------------------------------------
# OKX interval mapping (Binance -> OKX)
# ---------------------------------------------------------------------------

_OKX_INTERVAL_MAP = {
    "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1H", "2h": "2H", "4h": "4H", "6h": "6H", "12h": "12H",
    "1d": "1D", "1w": "1W",
}

# CryptoCompare interval mapping
_CC_INTERVAL_MAP = {
    "1m": ("histominute", 1), "5m": ("histominute", 5),
    "15m": ("histominute", 15), "30m": ("histominute", 30),
    "1h": ("histohour", 1), "2h": ("histohour", 2),
    "4h": ("histohour", 4), "1d": ("histoday", 1), "1w": ("histoday", 7),
}

# Kraken interval mapping (Binance interval -> Kraken minutes)
_KRAKEN_INTERVAL_MAP = {
    "1m": 1, "5m": 5, "15m": 15, "30m": 30,
    "1h": 60, "4h": 240, "1d": 1440, "1w": 10080,
}


# ===================================================================
# Source 1: OKX — No geo-block, 20 req/2s
# ===================================================================

def _fetch_okx_klines(symbol: str, interval: str, limit: int) -> list[list]:
    """Fetch klines from OKX. Returns list of [ts_ms, o, h, l, c, vol]."""
    inst_id = _binance_to_okx(symbol)
    if not inst_id:
        return []
    okx_bar = _OKX_INTERVAL_MAP.get(interval, interval)
    url = f"https://www.okx.com/api/v5/market/candles?instId={inst_id}&bar={okx_bar}&limit={min(limit, 300)}"
    data = _http_json(url, timeout=15)
    if not data or data.get("code") != "0":
        return []
    candles = data.get("data", [])
    if not candles:
        return []
    # OKX returns newest first — reverse to oldest first
    result = []
    for c in reversed(candles):
        try:
            result.append([
                int(c[0]), float(c[1]), float(c[2]),
                float(c[3]), float(c[4]), float(c[5]),
            ])
        except (IndexError, ValueError, TypeError):
            continue
    return result


def _fetch_okx_price(symbol: str) -> Optional[float]:
    """Get current price from OKX."""
    inst_id = _binance_to_okx(symbol)
    if not inst_id:
        return None
    url = f"https://www.okx.com/api/v5/market/ticker?instId={inst_id}"
    data = _http_json(url, timeout=10)
    if data and data.get("code") == "0" and data.get("data"):
        try:
            return float(data["data"][0]["last"])
        except (KeyError, ValueError, TypeError, IndexError):
            pass
    return None


# ===================================================================
# Source 2: CoinGecko — No geo-block, 30 req/min free
# ===================================================================

def _fetch_coingecko_klines(symbol: str, interval: str, limit: int) -> list[list]:
    """Fetch OHLC from CoinGecko. Limited intervals: 1d, 4h (via days param)."""
    cg_id = _binance_to_coingecko(symbol)
    if not cg_id:
        return []

    # CoinGecko OHLC endpoint: /coins/{id}/ohlc?vs_currency=usd&days=N
    # days=1 → 30min candles, days=7-30 → 4h, days=90-365 → 4day
    # For 1h/4h we use market_chart and derive OHLCV from price data
    if interval in ("1d", "1D"):
        days = min(limit, 365)
    elif interval in ("4h", "4H"):
        days = min(limit // 6 + 1, 90)
    elif interval in ("1h", "1H"):
        days = min(limit // 24 + 1, 90)
    else:
        days = min(limit // 24 + 1, 30)

    # Use OHLC endpoint for daily data
    url = f"https://api.coingecko.com/api/v3/coins/{cg_id}/ohlc?vs_currency=usd&days={days}"
    headers = {}
    cg_key = os.environ.get("COINGECKO_API_KEY", "")
    if cg_key:
        headers["x-cg-demo-api-key"] = cg_key

    data = _http_json(url, timeout=20, headers=headers if headers else None)
    if not data or not isinstance(data, list) or len(data) < 3:
        return []

    result = []
    for candle in data:
        try:
            # CoinGecko OHLC: [timestamp_ms, open, high, low, close]
            result.append([
                int(candle[0]), float(candle[1]), float(candle[2]),
                float(candle[3]), float(candle[4]), 0.0,  # no volume from OHLC
            ])
        except (IndexError, ValueError, TypeError):
            continue
    return result[-limit:]  # trim to requested limit


def _fetch_coingecko_price(symbol: str) -> Optional[float]:
    """Get current price from CoinGecko."""
    cg_id = _binance_to_coingecko(symbol)
    if not cg_id:
        return None
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd"
    headers = {}
    cg_key = os.environ.get("COINGECKO_API_KEY", "")
    if cg_key:
        headers["x-cg-demo-api-key"] = cg_key
    data = _http_json(url, timeout=10, headers=headers if headers else None)
    if data and cg_id in data:
        try:
            return float(data[cg_id]["usd"])
        except (KeyError, ValueError, TypeError):
            pass
    return None


# ===================================================================
# Source 3: Kraken — No geo-block, public API, good liquidity
# ===================================================================

def _fetch_kraken_klines(symbol: str, interval: str, limit: int) -> list[list]:
    """Fetch OHLC from Kraken. Returns list of [ts_ms, o, h, l, c, vol]."""
    kraken_pair = _binance_to_kraken(symbol)
    if not kraken_pair:
        return []
    kraken_interval = _KRAKEN_INTERVAL_MAP.get(interval)
    if kraken_interval is None:
        kraken_interval = 60  # default to 1h
    url = f"https://api.kraken.com/0/public/OHLC?pair={kraken_pair}&interval={kraken_interval}"
    data = _http_json(url, timeout=15)
    if not data or data.get("error"):
        # Kraken returns {"error": [...]} on failure
        errors = data.get("error", []) if data else []
        if errors:
            return []
        return []
    result_data = data.get("result", {})
    if not result_data:
        return []
    # Result keys vary (e.g. "XXBTZUSD" or "XETHZUSD") — pick first non-"last" key
    candles = None
    for key, val in result_data.items():
        if key != "last" and isinstance(val, list):
            candles = val
            break
    if not candles:
        return []
    # Kraken OHLC: [timestamp, open, high, low, close, vwap, volume, count]
    result = []
    for c in candles:
        try:
            result.append([
                int(c[0]) * 1000,  # convert unix seconds to ms
                float(c[1]), float(c[2]),
                float(c[3]), float(c[4]), float(c[6]),
            ])
        except (IndexError, ValueError, TypeError):
            continue
    return result[-limit:]  # trim to requested limit


def _fetch_kraken_price(symbol: str) -> Optional[float]:
    """Get current price from Kraken."""
    kraken_pair = _binance_to_kraken(symbol)
    if not kraken_pair:
        return None
    url = f"https://api.kraken.com/0/public/Ticker?pair={kraken_pair}"
    data = _http_json(url, timeout=10)
    if not data or data.get("error"):
        return None
    result_data = data.get("result", {})
    for key, val in result_data.items():
        try:
            # Kraken ticker: "c" = [price, lot_volume]
            return float(val["c"][0])
        except (KeyError, ValueError, TypeError, IndexError):
            continue
    return None


# ===================================================================
# Source 4: CryptoCompare — No geo-block, 100K calls/month free
# ===================================================================

def _fetch_cryptocompare_klines(symbol: str, interval: str, limit: int) -> list[list]:
    """Fetch klines from CryptoCompare."""
    cc_sym = _binance_to_cryptocompare(symbol)
    if not cc_sym:
        return []
    mapping = _CC_INTERVAL_MAP.get(interval)
    if not mapping:
        # Default to hourly
        mapping = ("histohour", 1)
    endpoint, aggregate = mapping

    api_key = os.environ.get("CRYPTOCOMPARE_API_KEY", "")
    url = (
        f"https://min-api.cryptocompare.com/data/v2/{endpoint}"
        f"?fsym={cc_sym}&tsym=USD&limit={min(limit, 2000)}&aggregate={aggregate}"
    )
    headers = {}
    if api_key:
        headers["authorization"] = f"Apikey {api_key}"
    data = _http_json(url, timeout=15, headers=headers if headers else None)
    if not data or data.get("Response") == "Error":
        return []
    hist = data.get("Data", {}).get("Data", [])
    if not hist:
        return []

    result = []
    for bar in hist:
        try:
            if bar.get("close", 0) == 0:
                continue  # skip empty bars
            result.append([
                int(bar["time"]) * 1000,  # convert to ms for consistency
                float(bar["open"]), float(bar["high"]),
                float(bar["low"]), float(bar["close"]),
                float(bar.get("volumefrom", 0)),
            ])
        except (KeyError, ValueError, TypeError):
            continue
    return result


def _fetch_cryptocompare_price(symbol: str) -> Optional[float]:
    """Get current price from CryptoCompare."""
    cc_sym = _binance_to_cryptocompare(symbol)
    if not cc_sym:
        return None
    url = f"https://min-api.cryptocompare.com/data/price?fsym={cc_sym}&tsyms=USD"
    data = _http_json(url, timeout=10)
    if data and "USD" in data:
        try:
            return float(data["USD"])
        except (ValueError, TypeError):
            pass
    return None


# ===================================================================
# Source 5: Binance — Primary but geo-blocked from US (451)
# ===================================================================

_BINANCE_BASE = "https://api.binance.com"


def _fetch_binance_klines(symbol: str, interval: str, limit: int) -> list[list]:
    """Fetch klines from Binance. Returns list of [ts_ms, o, h, l, c, vol]."""
    url = f"{_BINANCE_BASE}/api/v3/klines?symbol={symbol}&interval={interval}&limit={min(limit, 1000)}"
    data = _http_json(url, timeout=15)
    if not data or not isinstance(data, list):
        return []
    result = []
    for k in data:
        try:
            result.append([
                int(k[0]), float(k[1]), float(k[2]),
                float(k[3]), float(k[4]), float(k[5]),
            ])
        except (IndexError, ValueError, TypeError):
            continue
    return result


def _fetch_binance_price(symbol: str) -> Optional[float]:
    """Get current price from Binance."""
    url = f"{_BINANCE_BASE}/api/v3/ticker/price?symbol={symbol}"
    data = _http_json(url, timeout=10)
    if data and "price" in data:
        try:
            return float(data["price"])
        except (ValueError, TypeError):
            pass
    return None


# ===================================================================
# Source 6: yfinance — Scraper fallback
# ===================================================================

def _fetch_yfinance_klines(symbol: str, interval: str, limit: int) -> list[list]:
    """Fetch klines via yfinance. Slow but reliable."""
    try:
        import yfinance as yf
    except ImportError:
        return []

    yf_sym = _binance_to_yfinance(symbol)
    if not yf_sym:
        return []

    # Map interval to yfinance period
    period_map = {
        "1m": "7d", "5m": "60d", "15m": "60d", "30m": "60d",
        "1h": "730d", "4h": "730d", "1d": "max",
    }
    yf_interval = interval.replace("h", "h").replace("d", "d")
    # yfinance intervals: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk
    if yf_interval == "4h":
        yf_interval = "1h"  # fetch 1h and we'll just return more data
    if yf_interval == "2h":
        yf_interval = "1h"

    period = period_map.get(interval, "730d")

    try:
        ticker = yf.Ticker(yf_sym)
        df = ticker.history(period=period, interval=yf_interval, auto_adjust=True)
        if df is None or df.empty:
            return []
        result = []
        for idx, row in df.iterrows():
            ts_ms = int(idx.timestamp() * 1000) if hasattr(idx, 'timestamp') else 0
            result.append([
                ts_ms, float(row["Open"]), float(row["High"]),
                float(row["Low"]), float(row["Close"]),
                float(row.get("Volume", 0)),
            ])
        return result[-limit:]
    except Exception:
        return []


def _fetch_yfinance_price(symbol: str) -> Optional[float]:
    """Get current price via yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        return None

    yf_sym = _binance_to_yfinance(symbol)
    if not yf_sym:
        return None
    try:
        ticker = yf.Ticker(yf_sym)
        df = ticker.history(period="2d", interval="5m", auto_adjust=True)
        if df is not None and not df.empty:
            return float(df["Close"].dropna().iloc[-1])
    except Exception:
        pass
    return None


# ===================================================================
# Unified Public API
# ===================================================================

# Source registry: (name, klines_fn, price_fn)
_SOURCES = [
    ("okx",           _fetch_okx_klines,           _fetch_okx_price),
    ("coingecko",     _fetch_coingecko_klines,      _fetch_coingecko_price),
    ("kraken",        _fetch_kraken_klines,          _fetch_kraken_price),
    ("cryptocompare", _fetch_cryptocompare_klines,   _fetch_cryptocompare_price),
    ("binance",       _fetch_binance_klines,         _fetch_binance_price),
    ("yfinance",      _fetch_yfinance_klines,        _fetch_yfinance_price),
]

# Stats tracking
_fetch_stats: dict[str, int] = {}


def fetch_klines(symbol: str, interval: str = "1h", limit: int = 100) -> list[list]:
    """
    Fetch OHLCV klines with 5-source failover.

    Args:
        symbol: Binance-format symbol (e.g. "BTCUSDT")
        interval: Candle interval (e.g. "1h", "4h", "1d")
        limit: Number of candles to fetch

    Returns:
        List of [timestamp_ms, open, high, low, close, volume] arrays.
        Empty list if all sources fail.
    """
    cache_key = f"klines:{symbol}:{interval}:{limit}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    for name, klines_fn, _ in _SOURCES:
        if _ci_blocked(name) or _circuit_open(name):
            continue
        try:
            result = klines_fn(symbol, interval, limit)
            if result and len(result) >= 3:
                _fetch_stats[f"{name}_ok"] = _fetch_stats.get(f"{name}_ok", 0) + 1
                _cache_set(cache_key, result)
                return result
        except Exception:
            pass
        _fetch_stats[f"{name}_fail"] = _fetch_stats.get(f"{name}_fail", 0) + 1
        _record_failure(name)

    return []


def fetch_current_price(symbol: str) -> Optional[float]:
    """
    Get the latest price for a symbol with 5-source failover.

    Args:
        symbol: Binance-format symbol (e.g. "BTCUSDT")

    Returns:
        Current price as float, or None if all sources fail.
    """
    cache_key = f"price:{symbol}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    for name, _, price_fn in _SOURCES:
        if _ci_blocked(name) or _circuit_open(name):
            continue
        try:
            price = price_fn(symbol)
            if price and price > 0:
                _cache_set(cache_key, price)
                return price
        except Exception:
            pass
        _record_failure(name)

    return None


def fetch_current_prices_bulk(symbols: list[str]) -> dict[str, float]:
    """
    Get current prices for multiple symbols.
    Uses per-symbol failover (not bulk endpoint) for maximum reliability.

    Args:
        symbols: List of Binance-format symbols

    Returns:
        Dict of {symbol: price}
    """
    prices = {}
    for sym in symbols:
        price = fetch_current_price(sym)
        if price is not None:
            prices[sym] = price
    return prices


def get_fetch_stats() -> dict:
    """Return fetch success/failure counts per source."""
    return dict(_fetch_stats)


def print_fetch_summary():
    """Print a summary of which sources were used and their success rates."""
    if not _fetch_stats:
        return
    total_ok = sum(v for k, v in _fetch_stats.items() if k.endswith("_ok"))
    total_fail = sum(v for k, v in _fetch_stats.items() if k.endswith("_fail"))
    sources = []
    for name in ["okx", "coingecko", "kraken", "cryptocompare", "binance", "yfinance"]:
        ok = _fetch_stats.get(f"{name}_ok", 0)
        fail = _fetch_stats.get(f"{name}_fail", 0)
        if ok + fail > 0:
            label = f"{name} {ok}/{ok+fail}"
            if _circuit_open(name):
                label += " [TRIPPED]"
            sources.append(label)
    if sources:
        print(f"  [multi-source] Sources: {' | '.join(sources)} "
              f"(total: {total_ok} ok, {total_fail} fail)")
    if _IN_GITHUB_ACTIONS:
        print(f"  [multi-source] CI geo-block skip: {', '.join(sorted(_CI_BLOCKED_SOURCES))}")
