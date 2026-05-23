# -*- coding: utf-8 -*-
"""Mercury 2 — Data fetcher (Binance REST + multi-source failover)."""

import sys, time, requests, logging, numpy as np, pandas as pd
from pathlib import Path

log = logging.getLogger("mercury2.data")

# Import shared multi-source fetcher for failover
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from shared.multi_source_fetcher import (
        fetch_klines as _shared_fetch_klines,
        fetch_current_price as _shared_fetch_price,
    )
    _HAS_SHARED_FETCHER = True
except ImportError:
    _HAS_SHARED_FETCHER = False
    log.warning("shared.multi_source_fetcher not available — Binance-only mode")

BINANCE_BASES = [
    "https://api.binance.com",       # Primary (blocked from US)
    "https://api.binance.us",        # US fallback (fewer pairs but accessible)
    "https://data-api.binance.vision",  # Public data API (no geo-block)
]
BINANCE_FAPI = "https://fapi.binance.com"

# Map symbols that don't exist on Binance.US
_BINANCE_US_MISSING = {"INJUSDT", "TIAUSDT", "FETUSDT", "ARBUSDT", "OPUSDT",
                       "AAVEUSDT", "SEIUSDT"}


def fetch_ohlcv(symbol: str, interval: str = "1h", limit: int = 300,
                start_ms: int | None = None) -> pd.DataFrame:
    """Fetch OHLCV candles from Binance spot with geo-block fallback."""
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    if start_ms:
        params["startTime"] = start_ms

    all_rows = []
    base_url = None

    # Try each base URL until one works
    for base in BINANCE_BASES:
        if "binance.us" in base and symbol in _BINANCE_US_MISSING:
            continue  # Skip US exchange for unsupported pairs
        try:
            url = f"{base}/api/v3/klines"
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 451:
                log.debug(f"  [fetch] {symbol}: 451 from {base}, trying fallback")
                continue
            resp.raise_for_status()
            data = resp.json()
            if data:
                base_url = base
                all_rows.extend(data)
                break
        except Exception as e:
            log.debug(f"  [fetch] {symbol}: {base} failed: {e}")
            continue

    if not all_rows:
        # All Binance endpoints failed — try shared multi-source failover
        if _HAS_SHARED_FETCHER:
            log.info(f"  [fetch] {symbol}: Binance failed, trying multi-source failover")
            raw = _shared_fetch_klines(symbol, interval, limit)
            if raw:
                df = pd.DataFrame(raw, columns=["ts", "open", "high", "low", "close", "volume"])
                df["ts"] = pd.to_datetime(df["ts"], unit="ms")
                df.set_index("ts", inplace=True)
                for col in ["open", "high", "low", "close", "volume"]:
                    df[col] = df[col].astype(float)
                df = df[~df.index.duplicated(keep="last")]
                log.info(f"  [fetch] {symbol}: got {len(df)} bars from multi-source failover")
                return df
        log.warning(f"  [fetch] {symbol}: all endpoints failed (including failover)")
        return pd.DataFrame()

    # Continue pagination from the working base URL
    while True:
        if start_ms is None:
            break
        if len(all_rows) > 0 and len(data) < limit:
            break
        params["startTime"] = all_rows[-1][0] + 1
        time.sleep(0.1)
        try:
            url = f"{base_url}/api/v3/klines"
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 451:
                break
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            log.warning(f"  [fetch] {symbol} pagination failed: {e}")
            break
        if not data:
            break
        all_rows.extend(data)

        # If we got less than limit, we've reached the end
        if len(data) < limit:
            break

        # Move forward for next batch
        params["startTime"] = data[-1][0] + 1
        time.sleep(0.1)  # Rate limiting

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows, columns=[
        "ts", "open", "high", "low", "close", "volume",
        "close_time", "quote_vol", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore"
    ])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms")
    df.set_index("ts", inplace=True)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    df = df[["open", "high", "low", "close", "volume"]]
    df = df[~df.index.duplicated(keep="last")]
    return df


def fetch_funding_rate(symbol: str, limit: int = 100) -> pd.Series:
    """Fetch recent funding rates from Binance Futures."""
    fapi_urls = [BINANCE_FAPI, "https://fapi.binance.com"]
    data = None
    for base in fapi_urls:
        url = f"{base}/fapi/v1/fundingRate"
        try:
            resp = requests.get(url, params={"symbol": symbol, "limit": limit}, timeout=10)
            if resp.status_code == 451:
                continue
            resp.raise_for_status()
            data = resp.json()
            break
        except Exception as e:
            log.debug(f"  [funding] {symbol} from {base}: {e}")
            continue
    if data is None:
        log.warning(f"  [funding] {symbol}: all endpoints failed")
        return pd.Series(dtype=float)

    if not data:
        return pd.Series(dtype=float)

    ts = [pd.to_datetime(d["fundingTime"], unit="ms") for d in data]
    rates = [float(d["fundingRate"]) for d in data]
    return pd.Series(rates, index=ts, name="funding")


def fetch_fear_greed() -> int:
    """Fetch current Fear & Greed index."""
    try:
        resp = requests.get(
            "https://api.alternative.me/fng/?limit=1&format=json", timeout=5
        )
        return int(resp.json()["data"][0]["value"])
    except Exception:
        return 50


def fetch_btc_dominance() -> float:
    """Fetch BTC dominance from CoinGecko."""
    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/global", timeout=5
        )
        return float(resp.json()["data"]["market_cap_percentage"]["btc"])
    except Exception:
        return 0.0


def fetch_all_symbols(symbols: list[str], interval: str = "1h",
                      limit: int = 300, start_ms: int | None = None) -> dict[str, pd.DataFrame]:
    """Fetch OHLCV for all symbols, return dict."""
    result = {}
    for sym in symbols:
        df = fetch_ohlcv(sym, interval, limit, start_ms)
        if not df.empty:
            result[sym] = df
            log.info(f"  [fetch] {sym}: {len(df)} bars")
        else:
            log.warning(f"  [fetch] {sym}: no data")
        time.sleep(0.05)  # Rate limit
    return result
