#!/usr/bin/env python3
"""Daily-OHLCV failover fetcher for the ETF + Bond scanners.

yfinance is hard-blocked from GitHub Actions runner IPs — Yahoo rate-limits
the Azure shared ranges, so the ETF and Bond scanners fetch 0 data in CI
(they work fine locally). Tiingo, Polygon, and AlphaVantage are served from
normal APIs that work from cloud IPs.

The scanners try yfinance first (fast, no key). For any symbol still missing
they call :func:`fetch_ohlcv_failover`, which tries a 3-provider chain:

    1. Tiingo        — key in ``TIINGO_API_KEY`` (free tier, no tight rate cap)
    2. Polygon       — key in ``MASSIVE_API_KEY`` / ``POLYGON_API_KEY``
                       (free tier ~5 req/min — caller should space requests)
    3. AlphaVantage  — key in ``ALPHAVANTAGE_API_KEY``
                       (free tier 25 req/day; last-resort fallback)

With no key configured the module is a transparent no-op (returns ``None``),
so it is always safe to import and call.

All fetchers return a DataFrame indexed by date with capitalised columns
``Open/High/Low/Close/Volume`` (split/dividend-adjusted) — the shape the
ETF/Bond strategies expect — or ``None`` on any failure.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) alpha-engine/1.0"

# Polygon free tier ≈ 5 req/min ⇒ ~13s courtesy delay between calls. The
# per-symbol loop lives in the caller, so the sleep value is exposed here.
POLYGON_RATE_SLEEP = float(os.environ.get("POLYGON_RATE_SLEEP", "13"))


def _tiingo_key() -> Optional[str]:
    return os.environ.get("TIINGO_API_KEY") or os.environ.get("TIINGO_API")


def _polygon_key() -> Optional[str]:
    return os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY")


def _alphavantage_key() -> Optional[str]:
    return os.environ.get("ALPHAVANTAGE_API_KEY") or os.environ.get("ALPHA_VANTAGE_KEY")


def failover_available() -> bool:
    """True when at least one failover provider has a key configured."""
    return bool(_tiingo_key() or _polygon_key() or _alphavantage_key())


def _http_get_json(url: str, timeout: int = 30):
    req = urllib.request.Request(
        url, method="GET",
        headers={"Content-Type": "application/json", "User-Agent": _UA},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _frame(records: list, col_map: dict, date_key: str,
           date_unit: Optional[str] = None) -> Optional[pd.DataFrame]:
    """Build a normalised OHLCV DataFrame from raw provider records."""
    df = pd.DataFrame(records)
    if not all(c in df.columns for c in col_map) or date_key not in df.columns:
        return None
    out = df[list(col_map)].rename(columns=col_map)
    out.index = pd.to_datetime(df[date_key], unit=date_unit) if date_unit \
        else pd.to_datetime(df[date_key])
    out = out.sort_index()
    return out if len(out) >= 60 else None


def fetch_tiingo_ohlcv(symbol: str, period_days: int = 760) -> Optional[pd.DataFrame]:
    """Daily OHLCV from Tiingo. ``None`` on no key / failure."""
    key = _tiingo_key()
    if not key:
        return None
    start = (datetime.now(timezone.utc) - timedelta(days=period_days)).strftime("%Y-%m-%d")
    url = (f"https://api.tiingo.com/tiingo/daily/{symbol.upper()}/prices"
           f"?startDate={start}&format=json&token={key}")
    try:
        rows = _http_get_json(url)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError,
            json.JSONDecodeError) as exc:
        logger.warning("Tiingo %s: fetch failed — %s", symbol, exc)
        return None
    if not isinstance(rows, list) or not rows:
        return None
    # Prefer split/dividend-adjusted columns; fall back to raw.
    adj = {"adjOpen": "Open", "adjHigh": "High", "adjLow": "Low",
           "adjClose": "Close", "adjVolume": "Volume"}
    raw = {"open": "Open", "high": "High", "low": "Low",
           "close": "Close", "volume": "Volume"}
    col_map = adj if all(c in rows[0] for c in adj) else raw
    try:
        return _frame(rows, col_map, "date")
    except (KeyError, ValueError, TypeError) as exc:
        logger.warning("Tiingo %s: parse failed — %s", symbol, exc)
        return None


def fetch_polygon_ohlcv(symbol: str, period_days: int = 760) -> Optional[pd.DataFrame]:
    """Daily OHLCV from Polygon. ``None`` on no key / failure."""
    key = _polygon_key()
    if not key:
        return None
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=period_days)
    url = (f"https://api.polygon.io/v2/aggs/ticker/{symbol.upper()}"
           f"/range/1/day/{start.isoformat()}/{end.isoformat()}"
           f"?adjusted=true&sort=asc&limit=50000&apiKey={key}")
    try:
        payload = _http_get_json(url)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError,
            json.JSONDecodeError) as exc:
        logger.warning("Polygon %s: fetch failed — %s", symbol, exc)
        return None
    results = payload.get("results") if isinstance(payload, dict) else None
    if not results:
        return None
    col_map = {"o": "Open", "h": "High", "l": "Low", "c": "Close", "v": "Volume"}
    try:
        return _frame(results, col_map, "t", date_unit="ms")
    except (KeyError, ValueError, TypeError) as exc:
        logger.warning("Polygon %s: parse failed — %s", symbol, exc)
        return None


def fetch_alphavantage_ohlcv(symbol: str, period_days: int = 760) -> Optional[pd.DataFrame]:
    """Daily OHLCV from AlphaVantage TIME_SERIES_DAILY_ADJUSTED. ``None`` on no key / failure.

    Free tier: 25 req/day. Use as last-resort fallback — not for high-volume loops.
    """
    key = _alphavantage_key()
    if not key:
        return None
    outputsize = "full" if period_days > 100 else "compact"
    url = (f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED"
           f"&symbol={symbol.upper()}&outputsize={outputsize}&apikey={key}")
    try:
        payload = _http_get_json(url)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError,
            json.JSONDecodeError) as exc:
        logger.warning("AlphaVantage %s: fetch failed — %s", symbol, exc)
        return None
    if not isinstance(payload, dict):
        return None
    ts = payload.get("Time Series (Daily)") or payload.get("Time Series (Daily Adjusted)")
    if not ts:
        logger.warning("AlphaVantage %s: empty time series (note: 25 req/day limit)", symbol)
        return None
    cutoff = datetime.now(timezone.utc).date() - timedelta(days=period_days)
    records = []
    for date_str, vals in ts.items():
        if date_str < cutoff.isoformat():
            continue
        try:
            records.append({
                "date": date_str,
                "Open": float(vals.get("1. open", 0)),
                "High": float(vals.get("2. high", 0)),
                "Low": float(vals.get("3. low", 0)),
                "Close": float(vals.get("5. adjusted close", vals.get("4. close", 0))),
                "Volume": float(vals.get("6. volume", vals.get("5. volume", 0))),
            })
        except (ValueError, TypeError):
            continue
    if not records:
        return None
    col_map = {"Open": "Open", "High": "High", "Low": "Low", "Close": "Close", "Volume": "Volume"}
    try:
        return _frame(records, col_map, "date")
    except (KeyError, ValueError, TypeError) as exc:
        logger.warning("AlphaVantage %s: parse failed — %s", symbol, exc)
        return None


def fetch_ohlcv_failover(
    symbol: str, period_days: int = 760
) -> tuple[Optional[pd.DataFrame], str]:
    """Try Tiingo → Polygon → AlphaVantage (3-provider chain).

    Returns ``(dataframe, provider)`` where *provider* is ``"tiingo"``,
    ``"polygon"``, ``"alphavantage"``, or ``"none"``. The provider name lets
    the caller pace requests — Polygon's free tier needs ~13s between calls;
    Tiingo and AlphaVantage do not (AlphaVantage is capped at 25 req/day).
    """
    df = fetch_tiingo_ohlcv(symbol, period_days)
    if df is not None:
        logger.info("OHLCV failover: %s via Tiingo (%d bars)", symbol, len(df))
        return df, "tiingo"
    df = fetch_polygon_ohlcv(symbol, period_days)
    if df is not None:
        logger.info("OHLCV failover: %s via Polygon (%d bars)", symbol, len(df))
        return df, "polygon"
    df = fetch_alphavantage_ohlcv(symbol, period_days)
    if df is not None:
        logger.info("OHLCV failover: %s via AlphaVantage (%d bars)", symbol, len(df))
        return df, "alphavantage"
    return None, "none"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if not failover_available():
        print("No TIINGO_API_KEY / MASSIVE_API_KEY / ALPHAVANTAGE_API_KEY — module is a no-op fallback.")
        raise SystemExit(0)
    for sym in ("SPY", "XLK", "TLT"):
        d, provider = fetch_ohlcv_failover(sym)
        print(f"{sym}: {len(d) if d is not None else 'None'} bars via {provider}")
