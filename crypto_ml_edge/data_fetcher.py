"""
Data Fetcher — Zero-lookahead Binance OHLCV + Funding Rates
============================================================
Proven pattern from ml_crypto_predictor/enhanced_models/data_fetcher.py.
Parquet cache, batch pagination, funding rate history.
Multi-source failover: Binance -> OKX -> CoinGecko -> CryptoCompare -> yfinance.

CRITICAL: Every function returns data indexed by timestamp.
No future data is ever exposed — the caller sees only data available at bar T.
"""

import sys
import time
import json
import requests
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Tuple

from .config import (
    BINANCE_SPOT_BASE, BINANCE_FUTURES_BASE, FEAR_GREED_URL,
    COINGECKO_BASE, DATA_DIR, CACHE_TTL_HOURS, CANDIDATE_PAIRS,
    DEFAULT_PAIRS, TIMEFRAMES, MIN_24H_VOLUME_USD,
)

# Import shared multi-source fetcher for failover
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from shared.multi_source_fetcher import (
        fetch_klines as _shared_fetch_klines,
    )
    _HAS_SHARED_FETCHER = True
except ImportError:
    _HAS_SHARED_FETCHER = False

# Centralized failover (Binance mirrors -> CoinGecko -> KuCoin -> CryptoCompare).
# REQUIRED by project rule (CLAUDE.md / feedback_api_failover): never single
# Binance endpoint. Used for tickers, klines, and funding rates.
try:
    from alpha_engine.failover_imports import (
        fetch_tickers_24h as _ae_fetch_tickers_24h,
        fetch_klines as _ae_fetch_klines,
        fetch_funding_rate as _ae_fetch_funding_rate,
        HAS_SHARED_FAILOVER as _HAS_AE_FAILOVER,
    )
except ImportError:
    _HAS_AE_FAILOVER = False
    _ae_fetch_tickers_24h = None  # type: ignore[assignment]
    _ae_fetch_klines = None  # type: ignore[assignment]
    _ae_fetch_funding_rate = None  # type: ignore[assignment]


# ─── OHLCV Fetching ─────────────────────────────────────────────────────────

def fetch_klines(symbol: str, interval: str, limit: int = 1000,
                 cache: bool = True) -> pd.DataFrame:
    """
    Fetch OHLCV from Binance. Auto-paginates for limit > 1000.
    Returns DataFrame with columns [open, high, low, close, volume],
    indexed by UTC timestamp.
    """
    cache_dir = DATA_DIR / "klines"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{symbol}_{interval}_{limit}.parquet"

    if cache and cache_file.exists():
        age_hours = (time.time() - cache_file.stat().st_mtime) / 3600
        if age_hours < CACHE_TTL_HOURS:
            try:
                return pd.read_parquet(cache_file)
            except Exception:
                pass

    if limit > 1000:
        df = _batch_fetch_klines(symbol, interval, limit)
    else:
        df = _single_fetch_klines(symbol, interval, limit)

    if df.empty:
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
    """Fetch up to 1000 candles via centralized failover.

    Order: alpha_engine.failover_imports.fetch_klines (Binance mirrors -> CoinGecko
    -> KuCoin -> CryptoCompare) first, then direct Binance, then shared/multi_source.
    Returns Binance-shape DataFrame regardless of which source served the data.
    """
    # Primary: centralized alpha_engine failover (covers all 4 sources)
    if _HAS_AE_FAILOVER and _ae_fetch_klines is not None:
        try:
            raw = _ae_fetch_klines(symbol, interval, min(limit, 1000))
            if isinstance(raw, list) and raw:
                # Pad each row to 12 cols (Binance shape) for _parse_klines
                rows = [r + [0, 0, 0, 0, 0, 0] if len(r) < 12 else r for r in raw]
                return _parse_klines(rows)
        except Exception as e:
            print(f"[WARN] failover_imports klines {symbol} {interval}: {e}")

    # Secondary: direct Binance
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
        if ("451" in err_str or "403" in err_str) and _HAS_SHARED_FETCHER:
            print(f"[WARN] Binance geo-blocked for {symbol}, using multi-source failover")
            return _shared_failover_fetch(symbol, interval, limit)
        print(f"[WARN] fetch {symbol} {interval}: {e}")

    # Tertiary: legacy shared.multi_source_fetcher
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


def _batch_fetch_klines(symbol: str, interval: str, total: int) -> pd.DataFrame:
    """Fetch > 1000 candles via backward pagination."""
    all_dfs = []
    end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
    remaining = total

    while remaining > 0:
        batch = min(remaining, 1000)
        url = f"{BINANCE_SPOT_BASE}/api/v3/klines"
        params = {"symbol": symbol, "interval": interval,
                  "limit": batch, "endTime": end_time}
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            if ("451" in str(e) or "403" in str(e)) and _HAS_SHARED_FETCHER:
                print(f"[WARN] Binance geo-blocked in batch, using multi-source for {symbol}")
                return _shared_failover_fetch(symbol, interval, min(total, 300))
            print(f"[WARN] batch fetch {symbol}: {e}")
            break

        if not data:
            break

        all_dfs.append(_parse_klines(data))
        end_time = int(data[0][0]) - 1
        remaining -= len(data)
        time.sleep(0.15)

    if not all_dfs:
        return pd.DataFrame()

    df = pd.concat(all_dfs)
    df.sort_index(inplace=True)
    df = df[~df.index.duplicated(keep='first')]
    return df


def _parse_klines(data: list) -> pd.DataFrame:
    """Parse raw Binance klines response."""
    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    for col in ["open", "high", "low", "close", "volume", "quote_volume"]:
        df[col] = df[col].astype(float)
    df.set_index("timestamp", inplace=True)
    return df[["open", "high", "low", "close", "volume", "quote_volume"]]


# ─── Funding Rates ──────────────────────────────────────────────────────────

def fetch_funding_rate_history(symbol: str, days: int = 365,
                                cache: bool = True) -> pd.DataFrame:
    """
    Fetch historical funding rates from Binance Futures.
    Returns DataFrame with columns [funding_rate, funding_time].
    Funding rates are published every 8 hours.
    """
    cache_dir = DATA_DIR / "funding"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{symbol}_funding_{days}d.parquet"

    if cache and cache_file.exists():
        age_hours = (time.time() - cache_file.stat().st_mtime) / 3600
        if age_hours < CACHE_TTL_HOURS:
            try:
                return pd.read_parquet(cache_file)
            except Exception:
                pass

    all_data = []
    end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_time = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)

    while end_time > start_time:
        url = f"{BINANCE_FUTURES_BASE}/fapi/v1/fundingRate"
        params = {"symbol": symbol, "limit": 1000, "endTime": end_time}
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[WARN] funding rate {symbol}: {e}")
            break

        if not data:
            break

        all_data.extend(data)
        end_time = data[0]["fundingTime"] - 1
        time.sleep(0.15)

    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data)
    df["timestamp"] = pd.to_datetime(df["fundingTime"], unit="ms", utc=True)
    df["funding_rate"] = df["fundingRate"].astype(float)
    df.set_index("timestamp", inplace=True)
    df.sort_index(inplace=True)
    df = df[~df.index.duplicated(keep='first')]

    if cache:
        try:
            df[["funding_rate"]].to_parquet(cache_file)
        except Exception:
            pass

    return df[["funding_rate"]]


def fetch_current_funding_rates(symbols: Optional[List[str]] = None) -> Dict[str, float]:
    """Fetch current funding rates for all symbols.

    Tries direct Binance batch endpoint first (cheapest). On failure, falls back
    to per-symbol queries via centralized failover (alpha_engine.failover_imports).
    Returns {symbol: rate_float}.
    """
    if symbols is None:
        symbols = DEFAULT_PAIRS
    rates: Dict[str, float] = {}
    try:
        url = f"{BINANCE_FUTURES_BASE}/fapi/v1/premiumIndex"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        for item in resp.json():
            sym = item.get("symbol", "")
            if sym in symbols:
                rates[sym] = float(item.get("lastFundingRate", 0))
        if rates:
            return rates
    except Exception as e:
        print(f"[WARN] current funding rates: {e}")

    # Failover: per-symbol via alpha_engine.failover_imports.fetch_funding_rate
    if _HAS_AE_FAILOVER and _ae_fetch_funding_rate is not None:
        for sym in symbols:
            try:
                r = _ae_fetch_funding_rate(sym)
                if r is not None:
                    rates[sym] = float(r)
            except Exception:
                continue
    return rates


# ─── Fear & Greed ───────────────────────────────────────────────────────────

def fetch_fear_greed(days: int = 365) -> pd.DataFrame:
    """Fetch Fear & Greed Index history. Returns DataFrame with 'fg_value' column."""
    cache_file = DATA_DIR / f"fear_greed_{days}d.parquet"

    if cache_file.exists():
        age_hours = (time.time() - cache_file.stat().st_mtime) / 3600
        if age_hours < CACHE_TTL_HOURS:
            try:
                return pd.read_parquet(cache_file)
            except Exception:
                pass

    import time as _time
    data = []
    for _attempt in range(3):
        try:
            resp = requests.get(f"{FEAR_GREED_URL}?limit={days}", timeout=10)
            data = resp.json().get("data", [])
            break
        except Exception:
            if _attempt == 2:
                return pd.DataFrame()
            _time.sleep(2 * (_attempt + 1))

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="s", utc=True)
    df["fg_value"] = df["value"].astype(float)
    df.set_index("timestamp", inplace=True)
    df.sort_index(inplace=True)

    try:
        df[["fg_value"]].to_parquet(cache_file)
    except Exception:
        pass

    return df[["fg_value"]]


# ─── Dynamic Universe Selection ─────────────────────────────────────────────

def get_top_pairs_by_volume(n: int = 10,
                            candidates: Optional[List[str]] = None) -> List[str]:
    """
    Select top N pairs by 24h USD volume from Binance.
    Only considers CANDIDATE_PAIRS to avoid illiquid garbage.
    """
    if candidates is None:
        candidates = CANDIDATE_PAIRS

    tickers = None

    # Primary: centralized failover (Binance mirrors -> CoinGecko -> KuCoin -> CryptoCompare)
    if _HAS_AE_FAILOVER and _ae_fetch_tickers_24h is not None:
        try:
            shared_tickers, _src = _ae_fetch_tickers_24h()
            if shared_tickers:
                tickers = shared_tickers
        except Exception:
            tickers = None

    # Secondary: direct Binance
    if tickers is None:
        try:
            url = f"{BINANCE_SPOT_BASE}/api/v3/ticker/24hr"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            tickers = resp.json()
        except Exception:
            return DEFAULT_PAIRS[:n]

    volumes = {}
    for t in tickers:
        sym = t.get("symbol", "")
        if sym in candidates:
            vol = float(t.get("quoteVolume", 0))
            if vol >= MIN_24H_VOLUME_USD:
                volumes[sym] = vol

    sorted_pairs = sorted(volumes.keys(), key=lambda s: volumes[s], reverse=True)
    return sorted_pairs[:n] if len(sorted_pairs) >= n else DEFAULT_PAIRS[:n]


# ─── Bulk Data Loading ──────────────────────────────────────────────────────

def load_pair_data(symbol: str, timeframe: str = "1h") -> Dict[str, pd.DataFrame]:
    """
    Load all data for a pair: OHLCV + funding rates + fear/greed.
    Returns dict of DataFrames that can be joined on timestamp.
    """
    tf_config = TIMEFRAMES[timeframe]
    ohlcv = fetch_klines(symbol, tf_config["interval"], tf_config["candles"])
    funding = fetch_funding_rate_history(symbol, days=365 * 5)
    fg = fetch_fear_greed(days=365 * 5)

    return {
        "ohlcv": ohlcv,
        "funding": funding,
        "fear_greed": fg,
    }


def load_all_pairs(pairs: Optional[List[str]] = None,
                   timeframe: str = "1h") -> Dict[str, Dict[str, pd.DataFrame]]:
    """Load data for all pairs. Returns {symbol: {ohlcv, funding, fear_greed}}."""
    if pairs is None:
        pairs = get_top_pairs_by_volume()

    all_data = {}
    for i, symbol in enumerate(pairs):
        print(f"  [{i+1}/{len(pairs)}] Loading {symbol} {timeframe}...")
        all_data[symbol] = load_pair_data(symbol, timeframe)
        if (i + 1) % 5 == 0:
            time.sleep(0.5)

    print(f"  Loaded {len(all_data)}/{len(pairs)} pairs for {timeframe}")
    return all_data
