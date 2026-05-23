"""Multi-source kline/price fetcher with automatic fallback.

Supports: Binance → CryptoCompare → CoinGecko
All sources normalize to Binance kline format:
  [timestamp_ms, open, high, low, close, volume, close_time, ...]

Includes a shared in-memory cache so multiple strategies scanning
the same symbols don't duplicate API calls.
"""
import logging
import os
import time
from typing import Dict, List, Optional, Tuple

from paper_trading.helpers import fetch_json, rate_limited

logger = logging.getLogger("paper_trading")

# ── Symbol mapping ────────────────────────────────────────────────────
# Binance uses e.g. BTCUSDT, CryptoCompare uses BTC, CoinGecko uses "bitcoin"
_SYMBOL_MAP: Dict[str, Tuple[str, str]] = {
    "BTCUSDT":  ("BTC",  "bitcoin"),
    "ETHUSDT":  ("ETH",  "ethereum"),
    "SOLUSDT":  ("SOL",  "solana"),
    "BNBUSDT":  ("BNB",  "binancecoin"),
    "XRPUSDT":  ("XRP",  "ripple"),
    "ADAUSDT":  ("ADA",  "cardano"),
    "AVAXUSDT": ("AVAX", "avalanche-2"),
    "DOTUSDT":  ("DOT",  "polkadot"),
    "LINKUSDT": ("LINK", "chainlink"),
    "DOGEUSDT": ("DOGE", "dogecoin"),
    "MATICUSDT": ("MATIC", "matic-network"),
    "ATOMUSDT": ("ATOM", "cosmos"),
    "NEARUSDT": ("NEAR", "near"),
    "APTUSDT":  ("APT",  "aptos"),
    "ARBUSDT":  ("ARB",  "arbitrum"),
    "OPUSDT":   ("OP",   "optimism"),
    "SUIUSDT":  ("SUI",  "sui"),
    "LTCUSDT":  ("LTC",  "litecoin"),
    "UNIUSDT":  ("UNI",  "uniswap"),
    "AAVEUSDT": ("AAVE", "aave"),
}

# Interval mapping: Binance → CryptoCompare histoX endpoint
_INTERVAL_MAP = {
    "1m":  ("histominute", 1),
    "5m":  ("histominute", 5),
    "15m": ("histominute", 15),
    "1h":  ("histohour",   1),
    "4h":  ("histohour",   4),
    "1d":  ("histoday",    1),
}

# CoinGecko interval → days param
_CG_DAYS_MAP = {
    "1h": "14",     # CoinGecko returns hourly for 1-90 days
    "4h": "30",
    "1d": "180",
}

# ── In-memory cache ──────────────────────────────────────────────────
_kline_cache: Dict[str, dict] = {}  # key → {"ts": float, "data": list}
_price_cache: Dict[str, dict] = {}  # symbol → {"ts": float, "price": float, "source": str}
KLINE_CACHE_TTL = 600   # 10 minutes
PRICE_CACHE_TTL = 120   # 2 minutes


def _cache_key(symbol: str, interval: str, limit: int) -> str:
    return f"{symbol}_{interval}_{limit}"


# ── Source 1: Binance ────────────────────────────────────────────────

_BINANCE_SPOT_BASES = [
    "https://api.binance.com", "https://api1.binance.com",
    "https://data-api.binance.vision", "https://api.binance.us",
]

@rate_limited("binance", 0.15)
def _fetch_binance_klines(symbol: str, interval: str = "1h", limit: int = 250) -> list:
    """Fetch klines from Binance (with endpoint failover). Returns native format."""
    for base in _BINANCE_SPOT_BASES:
        try:
            result = fetch_json(
                f"{base}/api/v3/klines",
                params={"symbol": symbol, "interval": interval, "limit": limit},
            )
            if result:
                return result
        except Exception:
            continue
    return []


@rate_limited("binance", 0.1)
def _fetch_binance_price(symbol: str) -> dict:
    for base in _BINANCE_SPOT_BASES:
        try:
            result = fetch_json(
                f"{base}/api/v3/ticker/price",
                params={"symbol": symbol},
            )
            if result:
                return result
        except Exception:
            continue
    return {}


# ── Source 2: CryptoCompare ─────────────────────────────────────────

@rate_limited("cryptocompare", 0.25)
def _fetch_cryptocompare_klines(symbol: str, interval: str = "1h", limit: int = 250) -> list:
    """Fetch OHLCV from CryptoCompare, normalize to Binance kline format."""
    cc_sym = _SYMBOL_MAP.get(symbol, (symbol.replace("USDT", ""),))[0]
    endpoint_info = _INTERVAL_MAP.get(interval)
    if not endpoint_info:
        raise ValueError(f"Unsupported interval {interval} for CryptoCompare")

    endpoint, aggregate = endpoint_info
    # CryptoCompare limits to 2000 per call
    cc_limit = min(limit * aggregate if aggregate > 1 else limit, 2000)

    api_key = os.environ.get("CRYPTOCOMPARE_API_KEY", "")
    headers = {"Authorization": f"Apikey {api_key}"} if api_key else {}

    data = fetch_json(
        f"https://min-api.cryptocompare.com/data/v2/{endpoint}",
        params={"fsym": cc_sym, "tsym": "USDT", "limit": cc_limit},
        headers=headers,
    )

    raw = data.get("Data", {}).get("Data", [])
    if not raw:
        raise ValueError(f"CryptoCompare returned no data for {cc_sym}")

    # If aggregate > 1, we need to resample (e.g., 4h from 1h bars)
    if aggregate > 1:
        raw = _aggregate_bars(raw, aggregate)

    # Normalize to Binance kline format: [time_ms, O, H, L, C, V, close_time_ms, ...]
    klines = []
    for bar in raw:
        ts_ms = int(bar["time"]) * 1000
        klines.append([
            ts_ms,
            str(bar["open"]),
            str(bar["high"]),
            str(bar["low"]),
            str(bar["close"]),
            str(bar.get("volumeto", bar.get("volumefrom", 0))),
            ts_ms + 3599999,  # close time approx
            "0", "0", "0", "0", "0",  # padding to match Binance format
        ])
    return klines


def _aggregate_bars(bars: list, factor: int) -> list:
    """Aggregate N bars into 1 (e.g., 4 × 1h → 1 × 4h)."""
    result = []
    for i in range(0, len(bars) - factor + 1, factor):
        chunk = bars[i:i + factor]
        result.append({
            "time": chunk[0]["time"],
            "open": chunk[0]["open"],
            "high": max(b["high"] for b in chunk),
            "low": min(b["low"] for b in chunk),
            "close": chunk[-1]["close"],
            "volumeto": sum(b.get("volumeto", 0) for b in chunk),
        })
    return result


@rate_limited("cryptocompare", 0.25)
def _fetch_cryptocompare_price(symbol: str) -> dict:
    cc_sym = _SYMBOL_MAP.get(symbol, (symbol.replace("USDT", ""),))[0]
    data = fetch_json(
        "https://min-api.cryptocompare.com/data/price",
        params={"fsym": cc_sym, "tsyms": "USDT"},
    )
    price = data.get("USDT", 0)
    if price:
        return {"symbol": symbol, "price": str(price)}
    raise ValueError(f"CryptoCompare price unavailable for {cc_sym}")


# ── Source 3: CoinGecko ──────────────────────────────────────────────

@rate_limited("coingecko", 1.5)
def _fetch_coingecko_klines(symbol: str, interval: str = "1h", limit: int = 250) -> list:
    """Fetch OHLC from CoinGecko, normalize to Binance format.

    CoinGecko OHLC has limited granularity:
    - 1-2 days → 30min candles
    - 3-30 days → 4h candles
    - 31+ days → daily candles
    For hourly data, we use the market_chart endpoint (has close price + volume).
    """
    sym_info = _SYMBOL_MAP.get(symbol)
    if not sym_info:
        raise ValueError(f"No CoinGecko mapping for {symbol}")
    cg_id = sym_info[1]

    days = _CG_DAYS_MAP.get(interval, "30")
    api_key = os.environ.get("COINGECKO_API_KEY", "")
    headers = {"x-cg-demo-api-key": api_key} if api_key else {}

    # Use OHLC endpoint for daily/4h, market_chart for hourly
    if interval in ("1d", "4h"):
        data = fetch_json(
            f"https://api.coingecko.com/api/v3/coins/{cg_id}/ohlc",
            params={"vs_currency": "usd", "days": days},
            headers=headers,
        )
        if not data or not isinstance(data, list):
            raise ValueError(f"CoinGecko OHLC empty for {cg_id}")

        klines = []
        for candle in data[-limit:]:
            # CoinGecko OHLC format: [timestamp_ms, O, H, L, C]
            ts_ms = int(candle[0])
            klines.append([
                ts_ms,
                str(candle[1]), str(candle[2]), str(candle[3]), str(candle[4]),
                "0",  # CoinGecko OHLC doesn't include volume
                ts_ms + 3599999, "0", "0", "0", "0", "0",
            ])
        return klines
    else:
        # For hourly: use market_chart (prices + volumes, no OHLC)
        data = fetch_json(
            f"https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart",
            params={"vs_currency": "usd", "days": days},
            headers=headers,
        )
        prices = data.get("prices", [])
        volumes = data.get("total_volumes", [])
        if not prices:
            raise ValueError(f"CoinGecko market_chart empty for {cg_id}")

        # Synthesize pseudo-OHLCV from close prices (not ideal but functional)
        klines = []
        vol_map = {int(v[0]): v[1] for v in volumes} if volumes else {}
        for i, (ts_ms, price) in enumerate(prices[-limit:]):
            ts_ms = int(ts_ms)
            p = str(price)
            vol = str(vol_map.get(ts_ms, 0))
            # Use price as O/H/L/C (CoinGecko market_chart only gives close)
            # For strategies that rely on H/L, CryptoCompare is preferred
            klines.append([ts_ms, p, p, p, p, vol, ts_ms + 3599999,
                           "0", "0", "0", "0", "0"])
        return klines


@rate_limited("coingecko", 1.5)
def _fetch_coingecko_price(symbol: str) -> dict:
    sym_info = _SYMBOL_MAP.get(symbol)
    if not sym_info:
        raise ValueError(f"No CoinGecko mapping for {symbol}")
    cg_id = sym_info[1]
    api_key = os.environ.get("COINGECKO_API_KEY", "")
    headers = {"x-cg-demo-api-key": api_key} if api_key else {}

    data = fetch_json(
        "https://api.coingecko.com/api/v3/simple/price",
        params={"ids": cg_id, "vs_currencies": "usd"},
        headers=headers,
    )
    price = data.get(cg_id, {}).get("usd")
    if price:
        return {"symbol": symbol, "price": str(price)}
    raise ValueError(f"CoinGecko price unavailable for {cg_id}")


# ── Public API ───────────────────────────────────────────────────────

def fetch_klines(symbol: str, interval: str = "1h", limit: int = 250,
                 sources: Optional[List[str]] = None) -> list:
    """Fetch klines with automatic fallback across multiple sources.

    Args:
        symbol: Binance-style symbol (e.g., "BTCUSDT")
        interval: Candle interval ("1m", "5m", "15m", "1h", "4h", "1d")
        limit: Number of candles
        sources: Override source priority (default: ["binance", "cryptocompare", "coingecko"])

    Returns:
        List of klines in Binance format: [ts_ms, O, H, L, C, V, ...]
    """
    # Check cache — exact match first, then check if a larger cached set exists
    key = _cache_key(symbol, interval, limit)
    cached = _kline_cache.get(key)
    if cached and (time.time() - cached["ts"]) < KLINE_CACHE_TTL:
        return cached["data"]

    # Check for a superset in cache (e.g., we have 300 bars cached, request is for 10)
    for cached_key, cached_entry in _kline_cache.items():
        if (cached_key.startswith(f"{symbol}_{interval}_")
                and (time.time() - cached_entry["ts"]) < KLINE_CACHE_TTL
                and len(cached_entry["data"]) >= limit):
            return cached_entry["data"][-limit:]

    if sources is None:
        sources = ["binance", "cryptocompare", "coingecko"]

    fetchers = {
        "binance": lambda: _fetch_binance_klines(symbol, interval, limit),
        "cryptocompare": lambda: _fetch_cryptocompare_klines(symbol, interval, limit),
        "coingecko": lambda: _fetch_coingecko_klines(symbol, interval, limit),
    }

    last_error = None
    for src in sources:
        fetcher = fetchers.get(src)
        if not fetcher:
            continue
        try:
            klines = fetcher()
            if klines and len(klines) >= 1:
                _kline_cache[key] = {"ts": time.time(), "data": klines}
                if src != "binance":
                    logger.info(f"Klines for {symbol} ({interval}) served from {src}")
                return klines
        except Exception as e:
            last_error = e
            logger.debug(f"Kline fetch failed for {symbol} from {src}: {e}")
            continue

    logger.warning(f"All sources failed for klines {symbol} ({interval}): {last_error}")
    return []


def fetch_price(symbol: str, sources: Optional[List[str]] = None) -> dict:
    """Fetch current price with automatic fallback.

    Returns: {"symbol": "BTCUSDT", "price": "12345.67"}
    """
    cached = _price_cache.get(symbol)
    if cached and (time.time() - cached["ts"]) < PRICE_CACHE_TTL:
        return {"symbol": symbol, "price": str(cached["price"]),
                "source": cached["source"]}

    if sources is None:
        sources = ["binance", "cryptocompare", "coingecko"]

    fetchers = {
        "binance": lambda: _fetch_binance_price(symbol),
        "cryptocompare": lambda: _fetch_cryptocompare_price(symbol),
        "coingecko": lambda: _fetch_coingecko_price(symbol),
    }

    last_error = None
    for src in sources:
        fetcher = fetchers.get(src)
        if not fetcher:
            continue
        try:
            result = fetcher()
            price = float(result.get("price", 0))
            if price > 0:
                _price_cache[symbol] = {"ts": time.time(), "price": price, "source": src}
                result["source"] = src
                return result
        except Exception as e:
            last_error = e
            logger.debug(f"Price fetch failed for {symbol} from {src}: {e}")
            continue

    logger.warning(f"All sources failed for price {symbol}: {last_error}")
    return {"symbol": symbol, "price": "0"}


def clear_cache():
    """Clear all in-memory caches (useful between scan cycles)."""
    _kline_cache.clear()
    _price_cache.clear()


def get_cache_stats() -> dict:
    """Return cache hit statistics."""
    now = time.time()
    kline_valid = sum(1 for v in _kline_cache.values()
                      if now - v["ts"] < KLINE_CACHE_TTL)
    price_valid = sum(1 for v in _price_cache.values()
                      if now - v["ts"] < PRICE_CACHE_TTL)
    return {
        "kline_entries": len(_kline_cache),
        "kline_valid": kline_valid,
        "price_entries": len(_price_cache),
        "price_valid": price_valid,
    }
