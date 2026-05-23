"""
Data Fetcher — Binance OHLCV for 30 pairs x 5 timeframes
==========================================================
Uses public Binance API (no auth required) with multi-source failover
(OKX, CoinGecko, CryptoCompare, yfinance) when Binance is geo-blocked.
Caches data locally to avoid re-fetching during training.
"""

import json
import sys
import time
import requests
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict

from .config import (
    CRYPTO_PAIRS, TIMEFRAMES, BINANCE_SPOT_BASE,
    BINANCE_FUTURES_BASE, FEAR_GREED_URL, DATA_DIR,
)

# Import shared multi-source fetcher for failover
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from shared.multi_source_fetcher import (
        fetch_klines as _shared_fetch_klines,
    )
    _HAS_SHARED_FETCHER = True
except ImportError:
    _HAS_SHARED_FETCHER = False


def fetch_klines(symbol: str, interval: str, limit: int = 1000,
                 cache: bool = True) -> pd.DataFrame:
    """
    Fetch OHLCV klines from Binance public API.

    Args:
        symbol: e.g. "BTCUSDT"
        interval: e.g. "1h", "4h", "1d"
        limit: number of candles (auto-batches if > 1000)
        cache: whether to cache to disk

    Returns:
        DataFrame with columns: [open, high, low, close, volume]
    """
    cache_dir = DATA_DIR / "klines"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{symbol}_{interval}_{limit}.parquet"

    # Use cached data if the last candle is less than 2 hours old
    # (os.path.getmtime is unreliable in CI -- git checkout resets mtime)
    if cache and cache_file.exists():
        try:
            cached_df = pd.read_parquet(cache_file)
            if not cached_df.empty and hasattr(cached_df.index, 'tz'):
                last_candle_ts = cached_df.index[-1]
                if last_candle_ts.tzinfo is None:
                    last_candle_ts = last_candle_ts.tz_localize('UTC')
                now_utc = pd.Timestamp.now(tz='UTC')
                data_age_hours = (now_utc - last_candle_ts).total_seconds() / 3600
                if data_age_hours < 2.0:
                    return cached_df
        except Exception:
            pass

    # For limits > 1000 we need to batch fetch
    if limit > 1000:
        df = _batch_fetch_klines(symbol, interval, limit)
    else:
        df = _single_fetch_klines(symbol, interval, limit)

    if df.empty:
        # Try cached data even if stale
        if cache and cache_file.exists():
            try:
                return pd.read_parquet(cache_file)
            except Exception:
                pass
        return pd.DataFrame()

    if cache:
        try:
            df.to_parquet(cache_file)
        except Exception:
            pass

    return df


def _single_fetch_klines(symbol: str, interval: str, limit: int) -> pd.DataFrame:
    """Fetch up to 1000 candles. Tries Binance first, falls back to OKX, then shared multi-source."""
    url = f"{BINANCE_SPOT_BASE}/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": min(limit, 1000)}

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data:
            return _parse_klines(data)
    except Exception as e:
        err_str = str(e)
        # 451 = geo-blocked (US GitHub Actions runners), try OKX fallback
        if "451" in err_str or "403" in err_str:
            df = _fetch_okx_klines(symbol, interval, limit)
            if not df.empty:
                return df
            # OKX also failed -- try full shared multi-source failover
            if _HAS_SHARED_FETCHER:
                return _shared_failover_fetch(symbol, interval, limit)
            return pd.DataFrame()
        print(f"[WARN] Failed to fetch {symbol} {interval}: {e}")

    # Binance returned empty or failed without geo-block -- try shared failover
    if _HAS_SHARED_FETCHER:
        return _shared_failover_fetch(symbol, interval, limit)
    return pd.DataFrame()


def _shared_failover_fetch(symbol: str, interval: str, limit: int) -> pd.DataFrame:
    """Use shared multi-source fetcher and convert raw arrays to DataFrame."""
    raw = _shared_fetch_klines(symbol, interval, limit)
    if not raw:
        return pd.DataFrame()
    # Convert raw [ts_ms, o, h, l, c, vol] to Binance-format rows for _parse_klines
    rows = []
    for r in raw:
        rows.append(r + [0, 0, 0, 0, 0, 0])  # pad to 12 columns like Binance
    return _parse_klines(rows)


# OKX interval mapping: Binance -> OKX
_OKX_INTERVAL_MAP = {
    "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1H", "2h": "2H", "4h": "4H", "6h": "6H", "12h": "12H",
    "1d": "1D", "1w": "1W",
}


def _fetch_okx_klines(symbol: str, interval: str, limit: int) -> pd.DataFrame:
    """Fallback: fetch klines from OKX when Binance is geo-blocked (451)."""
    # Convert BTCUSDT -> BTC-USDT for OKX
    if symbol.endswith("USDT"):
        okx_inst = symbol[:-4] + "-USDT"
    elif symbol.endswith("BUSD"):
        okx_inst = symbol[:-4] + "-USDT"
    else:
        return pd.DataFrame()

    okx_interval = _OKX_INTERVAL_MAP.get(interval, interval)
    url = "https://www.okx.com/api/v5/market/candles"
    params = {"instId": okx_inst, "bar": okx_interval, "limit": str(min(limit, 300))}

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        result = resp.json()
        candles = result.get("data", [])
        if not candles:
            return pd.DataFrame()

        # OKX returns: [ts, open, high, low, close, vol, volCcy, volCcyQuote, confirm]
        # Reverse because OKX returns newest first
        candles = list(reversed(candles))
        rows = []
        for c in candles:
            rows.append([
                int(c[0]),          # timestamp ms
                float(c[1]),        # open
                float(c[2]),        # high
                float(c[3]),        # low
                float(c[4]),        # close
                float(c[5]),        # volume
                0, 0, 0, 0, 0, 0   # pad to match Binance format
            ])
        return _parse_klines(rows)
    except Exception as e:
        print(f"[WARN] OKX fallback failed for {symbol} {interval}: {e}")
        return pd.DataFrame()


def _batch_fetch_klines(symbol: str, interval: str, total_candles: int) -> pd.DataFrame:
    """Fetch > 1000 candles using multiple API calls (paginated backward)."""
    all_dfs = []
    end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
    remaining = total_candles
    batch_num = 0

    while remaining > 0:
        batch_size = min(remaining, 1000)
        url = f"{BINANCE_SPOT_BASE}/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": batch_size,
            "endTime": end_time,
        }

        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            if "451" in str(e) or "403" in str(e):
                # Geo-blocked: fall back to OKX for what we can get (max 300)
                print(f"[WARN] Binance geo-blocked, using OKX fallback for {symbol}")
                df = _fetch_okx_klines(symbol, interval, min(total_candles, 300))
                if not df.empty:
                    return df
                # OKX also failed -- try shared multi-source failover
                if _HAS_SHARED_FETCHER:
                    print(f"[WARN] OKX also failed, trying shared multi-source for {symbol}")
                    return _shared_failover_fetch(symbol, interval, min(total_candles, 300))
                return pd.DataFrame()
            print(f"[WARN] Batch {batch_num} failed for {symbol}: {e}")
            break

        if not data:
            break

        df_batch = _parse_klines(data)
        all_dfs.append(df_batch)

        # Move end_time to before earliest candle in this batch
        end_time = int(data[0][0]) - 1
        remaining -= len(data)
        batch_num += 1
        time.sleep(0.15)  # Rate limiting

    if not all_dfs:
        return pd.DataFrame()

    df = pd.concat(all_dfs)
    df.sort_index(inplace=True)
    df = df[~df.index.duplicated(keep='first')]
    return df


def _parse_klines(data: list) -> pd.DataFrame:
    """Parse raw Binance klines API response into DataFrame."""
    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore"
    ])

    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    df = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()
    df.set_index("timestamp", inplace=True)
    return df


def fetch_all_pairs_timeframe(pairs: Optional[List[str]] = None,
                               timeframe: str = "1h",
                               limit: Optional[int] = None) -> Dict[str, pd.DataFrame]:
    """
    Fetch OHLCV data for all pairs for a given timeframe.

    Returns: {symbol: DataFrame}
    """
    if pairs is None:
        pairs = CRYPTO_PAIRS

    tf_config = TIMEFRAMES.get(timeframe, TIMEFRAMES["1h"])
    if limit is None:
        limit = tf_config["limit"]

    data = {}
    for i, symbol in enumerate(pairs):
        df = fetch_klines(symbol, tf_config["interval"], limit)
        if not df.empty:
            data[symbol] = df

        # Rate limiting: 1200 requests/min for Binance
        if (i + 1) % 10 == 0:
            time.sleep(0.5)

    print(f"  Fetched {len(data)}/{len(pairs)} pairs for {timeframe}")
    return data


def fetch_all_data() -> Dict[str, Dict[str, pd.DataFrame]]:
    """
    Fetch all 30 pairs x 5 timeframes.

    Returns: {timeframe: {symbol: DataFrame}}
    """
    all_data = {}
    for tf_name in TIMEFRAMES:
        print(f"[{tf_name}] Fetching {len(CRYPTO_PAIRS)} pairs...")
        all_data[tf_name] = fetch_all_pairs_timeframe(timeframe=tf_name)
        time.sleep(1)  # Courtesy delay between timeframes

    return all_data


def fetch_fear_greed() -> float:
    """Fetch current Fear & Greed index (0-100) with retry."""
    import time as _time
    for attempt in range(3):
        try:
            resp = requests.get(FEAR_GREED_URL, timeout=5)
            data = resp.json()
            return float(data["data"][0]["value"])
        except Exception:
            if attempt < 2:
                _time.sleep(2 * (attempt + 1))
    return 50.0  # Neutral fallback


def fetch_funding_rates(symbols: Optional[List[str]] = None) -> Dict[str, float]:
    """
    Fetch Binance Futures funding rates for all symbols.
    Returns: {symbol: funding_rate}
    """
    if symbols is None:
        symbols = CRYPTO_PAIRS

    rates = {}
    try:
        # Batch endpoint: get all funding rates at once
        url = f"{BINANCE_FUTURES_BASE}/fapi/v1/premiumIndex"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        for item in data:
            sym = item.get("symbol", "")
            if sym in symbols:
                rates[sym] = float(item.get("lastFundingRate", 0))
    except Exception as e:
        print(f"[WARN] Binance funding rates failed ({e}), trying OKX...")
        # OKX fallback for funding rates
        try:
            for sym in symbols:
                okx_inst = sym[:-4] + "-USDT-SWAP" if sym.endswith("USDT") else sym
                url = "https://www.okx.com/api/v5/public/funding-rate"
                resp = requests.get(url, params={"instId": okx_inst}, timeout=10)
                if resp.ok:
                    okx_data = resp.json().get("data", [])
                    if okx_data:
                        rates[sym] = float(okx_data[0].get("fundingRate", 0))
        except Exception as e2:
            print(f"[WARN] OKX funding rates also failed: {e2}")

    return rates


def fetch_training_data(symbol: str, timeframe: str, days: int = 365) -> pd.DataFrame:
    """
    Fetch extended historical data for training.
    Uses multiple API calls to get more than 1000 candles.
    """
    tf_config = TIMEFRAMES.get(timeframe, TIMEFRAMES["1h"])
    interval = tf_config["interval"]

    # Calculate how many candles we need
    candle_minutes = {
        "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440,
    }
    minutes_per_candle = candle_minutes.get(interval, 60)
    total_candles = int(days * 24 * 60 / minutes_per_candle)

    if total_candles <= 1000:
        return fetch_klines(symbol, interval, total_candles, cache=True)

    # Fetch in batches of 1000
    all_dfs = []
    end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
    remaining = total_candles

    while remaining > 0:
        batch_size = min(remaining, 1000)
        url = f"{BINANCE_SPOT_BASE}/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": batch_size,
            "endTime": end_time,
        }

        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[WARN] Batch fetch failed for {symbol}: {e}")
            break

        if not data:
            break

        df_batch = pd.DataFrame(data, columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore"
        ])

        df_batch["timestamp"] = pd.to_datetime(df_batch["timestamp"], unit="ms", utc=True)
        for col in ["open", "high", "low", "close", "volume"]:
            df_batch[col] = df_batch[col].astype(float)

        df_batch = df_batch[["timestamp", "open", "high", "low", "close", "volume"]]
        all_dfs.append(df_batch)

        # Move end_time to before the earliest candle in this batch
        end_time = int(data[0][0]) - 1
        remaining -= batch_size
        time.sleep(0.2)  # Rate limiting

    if not all_dfs:
        return pd.DataFrame()

    df = pd.concat(all_dfs, ignore_index=True)
    df.sort_values("timestamp", inplace=True)
    df.drop_duplicates(subset="timestamp", inplace=True)
    df.set_index("timestamp", inplace=True)

    return df
