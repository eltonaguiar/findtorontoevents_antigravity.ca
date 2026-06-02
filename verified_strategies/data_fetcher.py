#!/usr/bin/env python3
"""
Real OHLCV data fetcher for strategy verification.

Failover chain (per asset class):
  Equities/ETF/FX/Commodity: yfinance -> Tiingo/Polygon/AlphaVantage (ohlcv_failover)
  Crypto: shared.multi_source_fetcher (OKX -> CoinGecko -> Kraken -> ...)

Carry rate differentials: FRED CSV (free, no key) -> config fallback (documented).
"""

from __future__ import annotations

import json
import logging
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger(__name__)

_FRED_CSV_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"
_FRED_CACHE_DIR = REPO_ROOT / "tools" / "cache"
_FRED_CACHE_FILE = _FRED_CACHE_DIR / "fred_carry_rates.json"
_FRED_CACHE_TTL_SEC = 7 * 24 * 3600

# FRED 3-month interbank rates for carry differential (base - quote, annualized %)
# Series IDs from FRED: IR3TIB01<CCY>M156N
CARRY_RATE_SERIES = {
    "AUDJPY=X": ("IR3TIB01AUM156N", "IR3TIB01JPM156N"),
    "EURJPY=X": ("IR3TIB01EZM156N", "IR3TIB01JPM156N"),
    "GBPJPY=X": ("IR3TIB01GBM156N", "IR3TIB01JPM156N"),
    "NZDJPY=X": ("IR3TIB01NZM156N", "IR3TIB01JPM156N"),
    "AUDUSD=X": ("IR3TIB01AUM156N", "IR3TIB01USM156N"),
}

# Config fallback when FRED is unreachable (approximate differentials, annualized)
CARRY_RATE_FALLBACK = {
    "AUDJPY=X": 0.036,
    "EURJPY=X": 0.029,
    "GBPJPY=X": 0.044,
    "NZDJPY=X": 0.049,
    "AUDUSD=X": -0.010,  # Negative: USD yields > AUD currently
}


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase OHLCV columns and ensure DatetimeIndex."""
    if df is None or df.empty:
        return df
    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = out.columns.get_level_values(0)
    col_map = {c: c.lower() for c in out.columns}
    out = out.rename(columns=col_map)
    out.index = pd.to_datetime(out.index)
    out = out.sort_index()
    required = ("close", "high", "low")
    if not all(c in out.columns for c in required):
        return pd.DataFrame()
    if "open" not in out.columns:
        out["open"] = out["close"]
    if "volume" not in out.columns:
        out["volume"] = 0.0
    return out[["open", "high", "low", "close", "volume"]].dropna(subset=["close"])


def fetch_yfinance_ohlcv(symbol: str, period_days: int = 1260) -> Tuple[Optional[pd.DataFrame], str]:
    """Fetch daily OHLCV via yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        logger.warning("yfinance not installed")
        return None, "none"

    period = "5y" if period_days >= 1000 else "2y" if period_days >= 500 else "1y"
    try:
        df = yf.download(
            symbol,
            period=period,
            interval="1d",
            progress=False,
            auto_adjust=True,
        )
    except Exception as exc:
        logger.warning("yfinance %s failed: %s", symbol, exc)
        return None, "none"

    out = normalize_ohlcv(df)
    if out is None or out.empty or len(out) < 60:
        return None, "none"
    return out, "yfinance"


def fetch_failover_ohlcv(symbol: str, period_days: int = 760) -> Tuple[Optional[pd.DataFrame], str]:
    """Tiingo -> Polygon -> AlphaVantage chain (equity tickers only)."""
    try:
        from alpha_engine.ohlcv_failover import fetch_ohlcv_failover
    except ImportError:
        return None, "none"

    # Strip yfinance suffixes for API providers
    api_symbol = symbol.replace("=X", "").replace("-USD", "").replace("=F", "")
    df, provider = fetch_ohlcv_failover(api_symbol, period_days)
    if df is None:
        return None, provider
    out = normalize_ohlcv(df)
    if out.empty or len(out) < 60:
        return None, "none"
    return out, provider


def fetch_ohlcv(symbol: str, period_days: int = 1260) -> Tuple[Optional[pd.DataFrame], str]:
    """
    Fetch daily OHLCV with failover.

    Returns (dataframe, provider_name). DataFrame has lowercase columns.
    """
    df, provider = fetch_yfinance_ohlcv(symbol, period_days)
    if df is not None:
        logger.info("OHLCV %s: %d bars via %s", symbol, len(df), provider)
        return df, provider

    df, provider = fetch_failover_ohlcv(symbol, period_days)
    if df is not None:
        logger.info("OHLCV %s: %d bars via %s (failover)", symbol, len(df), provider)
        return df, provider

    logger.error("OHLCV %s: all providers failed", symbol)
    return None, "none"


def _fred_cache_get(series_id: str, ignore_ttl: bool = False) -> Optional[pd.Series]:
    try:
        if not _FRED_CACHE_FILE.exists():
            return None
        blob = json.loads(_FRED_CACHE_FILE.read_text(encoding="utf-8"))
        entry = blob.get("series", {}).get(series_id)
        if not entry:
            return None
        if not ignore_ttl:
            age = datetime.now(timezone.utc).timestamp() - float(entry.get("saved_at", 0))
            if age > _FRED_CACHE_TTL_SEC:
                return None
        idx = pd.to_datetime(entry["dates"])
        return pd.Series(entry["values"], index=idx, name=series_id)
    except Exception:
        return None


def _fred_cache_put(series_id: str, series: pd.Series) -> None:
    try:
        _FRED_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        blob: dict = {}
        if _FRED_CACHE_FILE.exists():
            blob = json.loads(_FRED_CACHE_FILE.read_text(encoding="utf-8"))
        blob.setdefault("series", {})[series_id] = {
            "saved_at": datetime.now(timezone.utc).timestamp(),
            "dates": [d.isoformat() for d in series.index],
            "values": [float(v) for v in series.values],
        }
        _FRED_CACHE_FILE.write_text(json.dumps(blob), encoding="utf-8")
    except Exception as exc:
        logger.warning("FRED cache write failed: %s", exc)


def fetch_fred_series(series_id: str, days_back: int = 2000) -> Optional[pd.Series]:
    """Fetch a FRED time series via public CSV export (no API key)."""
    if os.environ.get("VERIFY_SKIP_FRED", "").strip() in ("1", "true", "yes"):
        return None

    cached = _fred_cache_get(series_id)
    if cached is not None and len(cached) > 30:
        logger.info("FRED %s: %d points (cache)", series_id, len(cached))
        return cached

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days_back)
    url = (
        f"{_FRED_CSV_BASE}?id={series_id}"
        f"&cosd={start.strftime('%Y-%m-%d')}"
        f"&coed={end.strftime('%Y-%m-%d')}"
    )
    timeout = int(os.environ.get("VERIFY_FRED_TIMEOUT", "8"))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "verified_strategies/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8")
        lines = text.strip().split("\n")
        if len(lines) < 2:
            return None
        dates, vals = [], []
        for line in lines[1:]:
            parts = line.split(",")
            if len(parts) != 2 or parts[1] == ".":
                continue
            try:
                dates.append(pd.to_datetime(parts[0]))
                vals.append(float(parts[1]))
            except (ValueError, IndexError):
                continue
        if not dates:
            return None
        out = pd.Series(vals, index=pd.DatetimeIndex(dates), name=series_id)
        _fred_cache_put(series_id, out)
        return out
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as exc:
        logger.warning("FRED %s failed: %s", series_id, exc)
        # gx10 hosts: urllib often times out; curl usually works
        try:
            import subprocess
            curl_url = f"{_FRED_CSV_BASE}?id={series_id}&cosd={start.strftime('%Y-%m-%d')}"
            proc = subprocess.run(
                ["curl", "-sS", "--max-time", "90", curl_url],
                capture_output=True, text=True, check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip().startswith("observation_date"):
                dates, vals = [], []
                for line in proc.stdout.strip().split("\n")[1:]:
                    parts = line.split(",")
                    if len(parts) != 2 or parts[1] in (".", ""):
                        continue
                    try:
                        dates.append(pd.to_datetime(parts[0]))
                        vals.append(float(parts[1]))
                    except (ValueError, IndexError):
                        continue
                if dates:
                    out = pd.Series(vals, index=pd.DatetimeIndex(dates), name=series_id)
                    _fred_cache_put(series_id, out)
                    logger.info("FRED %s: %d points (curl fallback)", series_id, len(out))
                    return out
        except Exception as curl_exc:
            logger.warning("FRED %s curl fallback failed: %s", series_id, curl_exc)
        stale = _fred_cache_get(series_id, ignore_ttl=True)
        if stale is not None:
            logger.info("FRED %s: stale cache fallback", series_id)
            return stale
        return None


def fetch_carry_rate_diff(symbol: str, price_index: pd.DatetimeIndex) -> Tuple[pd.Series, str]:
    """
    Build daily rate differential series aligned to price_index.

    Returns (rate_diff_series, source_label).
    rate_diff is in decimal form (e.g. 0.036 = 3.6% annualized).
    """
    pair = CARRY_RATE_SERIES.get(symbol)
    if pair is None:
        fallback = CARRY_RATE_FALLBACK.get(symbol, 0.02)
        logger.warning(
            "No FRED mapping for %s; using config fallback %.1f%%",
            symbol, fallback * 100,
        )
        return pd.Series(fallback, index=price_index, name="rate_diff"), "config_fallback"

    base_id, quote_id = pair
    base_rates = fetch_fred_series(base_id)
    quote_rates = fetch_fred_series(quote_id)

    if base_rates is not None and quote_rates is not None:
        combined = pd.DataFrame({"base": base_rates, "quote": quote_rates})
        combined = combined.sort_index().ffill()
        diff_pct = (combined["base"] - combined["quote"]) / 100.0  # FRED is in percent
        aligned = diff_pct.reindex(price_index, method="ffill").bfill()
        if aligned.notna().sum() > len(price_index) * 0.5:
            logger.info(
                "Carry rate diff for %s via FRED (%s - %s), mean=%.2f%%",
                symbol, base_id, quote_id, aligned.mean() * 100,
            )
            return aligned.rename("rate_diff"), "fred"

    fallback = CARRY_RATE_FALLBACK.get(symbol, 0.02)
    logger.warning(
        "FRED unavailable for %s; using config fallback %.1f%%",
        symbol, fallback * 100,
    )
    return pd.Series(fallback, index=price_index, name="rate_diff"), "config_fallback"


def load_carry_data(
    symbol: str = "AUDJPY=X", period_days: int = 1260
) -> Tuple[Optional[pd.DataFrame], str]:
    """Load FX OHLCV + rate differential for carry trade verification."""
    df, provider = fetch_ohlcv(symbol, period_days)
    if df is None:
        return None, provider

    rate_diff, rate_source = fetch_carry_rate_diff(symbol, df.index)
    df = df.copy()
    df["rate_diff"] = rate_diff
    return df, f"{provider}+{rate_source}"


def klines_to_dataframe(klines: list) -> pd.DataFrame:
    """Convert multi_source_fetcher klines to normalized DataFrame."""
    if not klines:
        return pd.DataFrame()
    index = pd.DatetimeIndex([pd.to_datetime(k[0], unit="ms") for k in klines])
    rows = [{
        "open": float(k[1]),
        "high": float(k[2]),
        "low": float(k[3]),
        "close": float(k[4]),
        "volume": float(k[5]),
    } for k in klines]
    df = pd.DataFrame(rows, index=index)
    return normalize_ohlcv(df)


def fetch_crypto_ohlcv(symbol: str = "BTCUSDT", limit: int = 1000) -> Tuple[Optional[pd.DataFrame], str]:
    """Fetch crypto daily OHLCV via multi-source failover."""
    try:
        from shared.multi_source_fetcher import fetch_klines
    except ImportError:
        return None, "none"

    klines = fetch_klines(symbol, interval="1d", limit=limit)
    df = klines_to_dataframe(klines)
    if df.empty or len(df) < 60:
        return None, "none"
    logger.info("Crypto OHLCV %s: %d bars via multi_source_fetcher", symbol, len(df))
    return df, "multi_source_fetcher"


def fetch_crypto_ohlcv_paginated(
    symbol: str = "BTCUSDT",
    interval: str = "1d",
    target_bars: int = 2500,
) -> Tuple[Optional[pd.DataFrame], str]:
    """
    Paginate Binance klines (3+ mirror failover) for deeper crypto history.
    Falls back to multi_source_fetcher single-shot if pagination fails.
    """
    import time

    try:
        from alpha_engine.api_failover import BINANCE_SPOT_BASES
    except ImportError:
        return fetch_crypto_ohlcv(symbol, limit=min(target_bars, 1000))

    interval_ms = {
        "1d": 86_400_000,
        "4h": 14_400_000,
        "1h": 3_600_000,
    }.get(interval, 86_400_000)

    page_limit = 1000
    all_rows: list = []
    end_ms: Optional[int] = None
    max_pages = (target_bars // page_limit) + 2

    for base in BINANCE_SPOT_BASES:
        all_rows = []
        end_ms = None
        for _ in range(max_pages):
            params = f"symbol={symbol}&interval={interval}&limit={page_limit}"
            if end_ms is not None:
                params += f"&endTime={end_ms - 1}"
            url = f"{base}/api/v3/klines?{params}"
            try:
                import urllib.request
                import json as _json

                req = urllib.request.Request(url, headers={"User-Agent": "verified_strategies/1.0"})
                with urllib.request.urlopen(req, timeout=20) as resp:
                    batch = _json.loads(resp.read().decode())
            except Exception:
                batch = None
            if not batch:
                break
            all_rows = batch + all_rows
            end_ms = int(batch[0][0])
            if len(batch) < page_limit:
                break
            time.sleep(0.08)
        if len(all_rows) >= 200:
            break

    if not all_rows:
        return fetch_crypto_ohlcv(symbol, limit=min(target_bars, 1000))

    seen = set()
    unique = []
    for k in all_rows:
        ts = int(k[0])
        if ts in seen:
            continue
        seen.add(ts)
        unique.append(k)
    unique.sort(key=lambda k: int(k[0]))

    df = klines_to_dataframe(unique[-target_bars:])
    if df.empty or len(df) < 60:
        return fetch_crypto_ohlcv(symbol, limit=min(target_bars, 1000))
    logger.info(
        "Crypto OHLCV %s: %d bars via binance_paginated",
        symbol, len(df),
    )
    return df, "binance_paginated"
