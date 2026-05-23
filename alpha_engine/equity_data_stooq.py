"""
Stooq equity data helper.

Status (2026-04-20): Stooq's historical bulk CSV endpoint
(https://stooq.com/q/d/l/?s=...) now requires a per-user API key obtained
via captcha on the Stooq website. The anonymous endpoint returns an
"apikey required" notice and `pandas_datareader`'s Stooq reader is
broken on Python 3.12 (distutils + deprecate_kwarg compat).

What still works anonymously:
  - The intraday/EOD quote snapshot endpoint:
    https://stooq.com/q/l/?s=<sym>&f=sd2t2ohlcv&h&e=csv
    Returns one row (latest close) with no key required.

This helper exposes:
  - fetch_stooq_quote(ticker)            -> dict of last-quote fields
  - fetch_stooq_ohlcv(ticker, start, end) -> DataFrame, uses API key if
    STOOQ_API_KEY env var is set; otherwise raises StooqKeyRequired.

Retry/backoff + on-disk cache (24h) are applied to both paths.
"""
from __future__ import annotations

import csv
import io
import json
import os
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

UA = "Mozilla/5.0 (compatible; FTE-AuditBot/1.0)"
CACHE_DIR = Path(os.environ.get("STOOQ_CACHE_DIR",
                                Path(__file__).parent.parent / ".cache" / "stooq"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_TTL_SEC = 24 * 3600


class StooqKeyRequired(RuntimeError):
    """Raised when Stooq historical CSV requires an API key we don't have."""


def _http_get(url: str, timeout: int = 20, retries: int = 3) -> bytes:
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return urllib.request.urlopen(req, timeout=timeout).read()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"stooq GET failed after {retries}: {last}")


def _cache_path(key: str) -> Path:
    safe = key.replace("/", "_").replace("?", "_").replace("&", "_").replace("=", "_")
    return CACHE_DIR / f"{safe}.json"


def _cache_read(key: str) -> Optional[dict]:
    p = _cache_path(key)
    if not p.exists():
        return None
    if time.time() - p.stat().st_mtime > CACHE_TTL_SEC:
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _cache_write(key: str, payload: dict) -> None:
    _cache_path(key).write_text(json.dumps(payload))


def fetch_stooq_quote(ticker: str) -> dict:
    """Return latest-quote dict for a Stooq symbol (e.g. 'spy.us', '7203.jp')."""
    t = ticker.lower()
    cache_key = f"quote_{t}"
    cached = _cache_read(cache_key)
    if cached is not None:
        return cached
    url = f"https://stooq.com/q/l/?s={t}&f=sd2t2ohlcv&h&e=csv"
    body = _http_get(url).decode("utf-8", errors="replace")
    rows = list(csv.DictReader(io.StringIO(body)))
    if not rows:
        raise RuntimeError(f"stooq: empty response for {ticker}")
    row = rows[0]
    if row.get("Date") in (None, "", "N/D"):
        raise RuntimeError(f"stooq: no data (N/D) for {ticker} — symbol may be gated or wrong suffix")
    out = {
        "symbol": row.get("Symbol"),
        "date": row.get("Date"),
        "time": row.get("Time"),
        "open": float(row["Open"]),
        "high": float(row["High"]),
        "low": float(row["Low"]),
        "close": float(row["Close"]),
        "volume": float(row["Volume"]),
    }
    _cache_write(cache_key, out)
    return out


def fetch_stooq_ohlcv(ticker: str, start, end) -> pd.DataFrame:
    """Daily OHLCV history. Requires STOOQ_API_KEY env var (Stooq now gates
    the bulk CSV behind a captcha-issued key). Raises StooqKeyRequired if
    the key is missing or the endpoint responds with the "Get your apikey"
    notice.
    """
    if isinstance(start, str):
        start = datetime.fromisoformat(start)
    if isinstance(end, str):
        end = datetime.fromisoformat(end)
    api_key = os.environ.get("STOOQ_API_KEY")
    t = ticker.lower()
    d1 = start.strftime("%Y%m%d")
    d2 = end.strftime("%Y%m%d")
    key_param = f"&k={api_key}" if api_key else ""
    url = f"https://stooq.com/q/d/l/?s={t}&d1={d1}&d2={d2}&i=d{key_param}"
    cache_key = f"hist_{t}_{d1}_{d2}"
    cached = _cache_read(cache_key)
    if cached is not None:
        return pd.read_json(io.StringIO(cached["json"]), orient="split")
    body = _http_get(url)
    head = body[:80].lower()
    if b"apikey" in head or b"get your" in head:
        raise StooqKeyRequired(
            "Stooq historical CSV requires an API key. Obtain one at "
            "https://stooq.com/q/d/?s=<sym>&get_apikey and set STOOQ_API_KEY."
        )
    df = pd.read_csv(io.BytesIO(body))
    if "Date" not in df.columns:
        raise RuntimeError(f"stooq: unexpected payload for {ticker}: {body[:120]!r}")
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    _cache_write(cache_key, {"json": df.reset_index().to_json(orient="split")})
    return df


if __name__ == "__main__":
    import sys
    for sym in sys.argv[1:] or ["spy.us", "aapl.us", "7203.jp"]:
        try:
            print(sym, fetch_stooq_quote(sym))
        except Exception as e:  # noqa: BLE001
            print(sym, "ERR", e)
