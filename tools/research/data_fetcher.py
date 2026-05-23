"""Fetch historical OHLC for an ETF universe via yfinance with parquet cache.

Cache location: `alpha_engine/data/bt_cache_<TICKER>.parquet` — same
convention as existing backtest cache. .gitignored already.

Usage:
  prices = fetch_universe(["IEF", "TLT"], period="5y")
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = REPO_ROOT / "alpha_engine" / "data"

_CACHE_TTL_DAYS = 1  # parquet stale after 1 day -> refetch


def _cache_path(ticker: str) -> Path:
    return CACHE_DIR / f"bt_cache_{ticker.upper()}.parquet"


def _is_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    age = dt.datetime.now() - dt.datetime.fromtimestamp(path.stat().st_mtime)
    return age.total_seconds() < _CACHE_TTL_DAYS * 86400


def fetch_one(ticker: str, period: str = "5y") -> pd.Series:
    """Return Close-price Series for ticker. Cached parquet path."""
    cache = _cache_path(ticker)
    if _is_fresh(cache):
        try:
            df = pd.read_parquet(cache)
            return df["Close"]
        except Exception:
            pass

    import yfinance as yf

    df = yf.download(
        ticker, period=period, progress=False, auto_adjust=True, threads=False
    )
    if df is None or df.empty:
        return pd.Series(dtype=float)

    # yfinance newer versions return MultiIndex columns; flatten
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]

    try:
        df.to_parquet(cache)
    except Exception:
        pass

    return df["Close"]


def fetch_universe(tickers: list[str], period: str = "5y") -> pd.DataFrame:
    """Return DataFrame indexed by date, one column per ticker (Close).

    Missing tickers (delisted, fetch error) are silently dropped from output.
    """
    series_map = {}
    for t in tickers:
        s = fetch_one(t, period=period)
        if s is None or s.empty:
            continue
        series_map[t.upper()] = s
    if not series_map:
        return pd.DataFrame()
    df = pd.DataFrame(series_map)
    df = df.dropna(how="all")
    return df
