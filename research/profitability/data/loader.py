"""Cached public-market data loaders for the profitability research program.

Sources:
  - Binance Vision monthly klines (primary history) + Binance spot API (fallback/current)
  - Stooq daily CSV for ETFs/equities
  - Frankfurter (ECB) daily FX

Raw files are cached under data/cache/ (gitignored). A manifest with SHA-256 and
date coverage is written next to the run.
"""
from __future__ import annotations

import hashlib
import io
import json
import time
import urllib.error
import urllib.request
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
CACHE.mkdir(parents=True, exist_ok=True)
MANIFEST = HERE / "manifest.json"

UA = {"User-Agent": "Mozilla/5.0 (profitability-research; contact: repo owner)"}


def _fetch(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _cache_path(name: str) -> Path:
    return CACHE / name


def _record(entry: dict) -> None:
    data = []
    if MANIFEST.exists():
        try:
            data = json.loads(MANIFEST.read_text())
        except Exception:
            data = []
    data = [d for d in data if d.get("key") != entry.get("key")]
    data.append(entry)
    MANIFEST.write_text(json.dumps(sorted(data, key=lambda d: d["key"]), indent=2))


def _binance_api_daily(symbol: str, start: str, end: str) -> pd.DataFrame:
    """Paginate Binance spot API. Returns UTC-date indexed OHLCV."""
    start_ms = int(datetime.fromisoformat(start).replace(tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime.fromisoformat(end).replace(tzinfo=timezone.utc).timestamp() * 1000)
    rows = []
    cursor = start_ms
    while cursor < end_ms:
        url = (
            "https://api.binance.com/api/v3/klines"
            f"?symbol={symbol}&interval=1d&startTime={cursor}&endTime={end_ms}&limit=1000"
        )
        raw = _fetch(url)
        batch = json.loads(raw)
        if not batch:
            break
        rows.extend(batch)
        last = batch[-1][0]
        if last <= cursor:
            break
        cursor = last + 86_400_000
        time.sleep(0.15)
    if not rows:
        raise RuntimeError(f"no Binance API rows for {symbol}")
    df = pd.DataFrame(rows, columns=[
        "open_time", "open", "high", "low", "close", "volume", "close_time",
        "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore",
    ])
    df["date"] = pd.to_datetime(df["open_time"], unit="ms", utc=True).dt.tz_convert(None).dt.normalize()
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[["date", "open", "high", "low", "close", "volume"]].drop_duplicates("date").sort_values("date")
    return df.set_index("date")


def _binance_vision_monthly(symbol: str, start: str, end: str) -> pd.DataFrame:
    """Download monthly ZIPs from data.binance.vision and concatenate."""
    s = pd.Timestamp(start)
    e = pd.Timestamp(end)
    frames = []
    cur = pd.Timestamp(year=s.year, month=s.month, day=1)
    while cur <= e:
        ym = cur.strftime("%Y-%m")
        name = f"{symbol}-1d-{ym}.zip"
        url = f"https://data.binance.vision/data/spot/monthly/klines/{symbol}/1d/{name}"
        try:
            blob = _fetch(url)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                cur = (cur + pd.offsets.MonthBegin(1)).normalize()
                continue
            raise
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            inner = zf.namelist()[0]
            text = zf.read(inner).decode("utf-8")
        # Some archives have a header, some do not.
        first = text.splitlines()[0]
        has_header = "open_time" in first or "Open time" in first
        df = pd.read_csv(io.StringIO(text), header=0 if has_header else None)
        df = df.iloc[:, :12]
        df.columns = [
            "open_time", "open", "high", "low", "close", "volume", "close_time",
            "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore",
        ]
        df["date"] = pd.to_datetime(df["open_time"], unit="ms", utc=True).dt.tz_convert(None).dt.normalize()
        for c in ["open", "high", "low", "close", "volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        frames.append(df[["date", "open", "high", "low", "close", "volume"]])
        cur = (cur + pd.offsets.MonthBegin(1)).normalize()
    if not frames:
        raise RuntimeError(f"no Binance Vision rows for {symbol}")
    out = pd.concat(frames).drop_duplicates("date").sort_values("date").set_index("date")
    return out


def binance_daily(symbol: str, start: str = "2018-01-01", end: str | None = None) -> pd.DataFrame:
    end = end or date.today().isoformat()
    key = f"binance:{symbol}:1d:{start}:{end}"
    path = _cache_path(f"binance_{symbol}_1d.csv")
    if path.exists():
        df = pd.read_csv(path, parse_dates=["date"]).set_index("date")
        if len(df) and df.index.min() <= pd.Timestamp(start) + pd.Timedelta(days=5) and df.index.max() >= pd.Timestamp(end) - pd.Timedelta(days=5):
            _record({"key": key, "symbol": symbol, "source": "cache", "rows": len(df),
                     "first": str(df.index.min().date()), "last": str(df.index.max().date()),
                     "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
            return df
    last_err = None
    for source, fn in (("binance_api", _binance_api_daily), ("binance_vision", _binance_vision_monthly)):
        try:
            df = fn(symbol, start, end)
            df.to_csv(path)
            _record({"key": key, "symbol": symbol, "source": source, "rows": len(df),
                     "first": str(df.index.min().date()), "last": str(df.index.max().date()),
                     "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
            return df
        except Exception as exc:  # noqa: BLE001
            last_err = exc
    raise RuntimeError(f"binance load failed for {symbol}: {last_err}")


def stooq_daily(symbol: str, start: str = "2007-01-01", end: str | None = None) -> pd.DataFrame:
    end = end or date.today().isoformat()
    key = f"stooq:{symbol}:{start}:{end}"
    path = _cache_path(f"stooq_{symbol}_1d.csv")
    if path.exists():
        df = pd.read_csv(path, parse_dates=["date"]).set_index("date")
        if len(df) and df.index.max() >= pd.Timestamp(end) - pd.Timedelta(days=7):
            _record({"key": key, "symbol": symbol, "source": "cache", "rows": len(df),
                     "first": str(df.index.min().date()), "last": str(df.index.max().date()),
                     "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
            return df
    url = f"https://stooq.com/q/d/l/?s={symbol.lower()}.us&i=d"
    text = _fetch(url).decode("utf-8", errors="replace")
    if "Date,Open" not in text[:200]:
        raise RuntimeError(f"stooq unexpected response for {symbol}: {text[:120]!r}")
    df = pd.read_csv(io.StringIO(text))
    df["date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df["close"] = pd.to_numeric(df["Close"], errors="coerce")
    df = df.dropna(subset=["close"])[["date", "close"]].drop_duplicates("date").sort_values("date")
    df = df.set_index("date")
    df.to_csv(path)
    _record({"key": key, "symbol": symbol, "source": "stooq", "rows": len(df),
             "first": str(df.index.min().date()), "last": str(df.index.max().date()),
             "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return df


def nasdaq_daily(symbol: str, start: str = "2016-01-01", end: str | None = None,
                 assetclass: str = "etf") -> pd.DataFrame:
    """Nasdaq public quote API (keyless). ~10 years of daily closes, price-only."""
    end = end or date.today().isoformat()
    key = f"nasdaq:{symbol}:{start}:{end}"
    path = _cache_path(f"nasdaq_{symbol}_1d.csv")
    if path.exists():
        df = pd.read_csv(path, parse_dates=["date"]).set_index("date")
        if len(df) and df.index.max() >= pd.Timestamp(end) - pd.Timedelta(days=7):
            _record({"key": key, "symbol": symbol, "source": "cache", "rows": len(df),
                     "first": str(df.index.min().date()), "last": str(df.index.max().date()),
                     "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
            return df
    url = (f"https://api.nasdaq.com/api/quote/{symbol}/historical"
           f"?assetclass={assetclass}&fromdate={start}&todate={end}&limit=10000")
    data = json.loads(_fetch(url))
    time.sleep(0.2)
    rows = (data.get("data") or {}).get("tradesTable", {}).get("rows", [])
    if not rows:
        raise RuntimeError(f"nasdaq no rows for {symbol}")
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y", errors="coerce")
    df["close"] = (df["close"].astype(str)
                   .str.replace("$", "", regex=False)
                   .str.replace(",", "", regex=False))
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["date", "close"])[["date", "close"]].drop_duplicates("date").sort_values("date")
    df = df.set_index("date")
    df.to_csv(path)
    _record({"key": key, "symbol": symbol, "source": "nasdaq", "rows": len(df),
             "first": str(df.index.min().date()), "last": str(df.index.max().date()),
             "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return df


def treasury_bill_daily(start_year: int = 2018, end_year: int | None = None) -> pd.DataFrame:
    """13-week T-bill coupon-equivalent yield from Treasury.gov (keyless)."""
    end_year = end_year or date.today().year
    key = f"treasury:13w:{start_year}:{end_year}"
    path = _cache_path("treasury_13w.csv")
    if path.exists():
        df = pd.read_csv(path, parse_dates=["date"]).set_index("date")
        if len(df) and df.index.max().year >= end_year and df.index.min().year <= start_year:
            _record({"key": key, "symbol": "13W_TBILL", "source": "cache", "rows": len(df),
                     "first": str(df.index.min().date()), "last": str(df.index.max().date()),
                     "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
            return df
    frames = []
    for year in range(start_year, end_year + 1):
        url = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
               f"daily-treasury-rates.csv/{year}/all?type=daily_treasury_bill_rates"
               f"&field_tdr_date_value={year}&page&_format=csv")
        try:
            text = _fetch(url).decode("utf-8", errors="replace")
        except Exception:
            continue
        if "Date" not in text[:200]:
            continue
        df = pd.read_csv(io.StringIO(text))
        col = next((c for c in df.columns if "13 WEEKS COUPON" in c.upper()), None)
        if col is None:
            continue
        df["date"] = pd.to_datetime(df["Date"], format="%m/%d/%Y", errors="coerce")
        df["rate"] = pd.to_numeric(df[col], errors="coerce")
        frames.append(df.dropna(subset=["date", "rate"])[["date", "rate"]])
        time.sleep(0.2)
    if not frames:
        raise RuntimeError("no Treasury bill rows")
    out = pd.concat(frames).drop_duplicates("date").sort_values("date").set_index("date")
    out.to_csv(path)
    _record({"key": key, "symbol": "13W_TBILL", "source": "treasury.gov", "rows": len(out),
             "first": str(out.index.min().date()), "last": str(out.index.max().date()),
             "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return out


def frankfurter_daily(base: str, quote: str, start: str = "2018-01-01", end: str | None = None) -> pd.DataFrame:
    end = end or date.today().isoformat()
    key = f"frankfurter:{base}{quote}:{start}:{end}"
    path = _cache_path(f"fx_{base}{quote}_1d.csv")
    if path.exists():
        df = pd.read_csv(path, parse_dates=["date"]).set_index("date")
        _record({"key": key, "symbol": f"{base}{quote}", "source": "cache", "rows": len(df),
                 "first": str(df.index.min().date()), "last": str(df.index.max().date()),
                 "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        return df
    url = f"https://api.frankfurter.app/{start}..{end}?from={base}&to={quote}"
    raw = _fetch(url)
    data = json.loads(raw)
    rows = [{"date": pd.Timestamp(d), "close": float(v[quote])} for d, v in data.get("rates", {}).items()]
    if not rows:
        raise RuntimeError(f"no FX rows for {base}{quote}")
    df = pd.DataFrame(rows).sort_values("date").set_index("date")
    df.to_csv(path)
    _record({"key": key, "symbol": f"{base}{quote}", "source": "frankfurter", "rows": len(df),
             "first": str(df.index.min().date()), "last": str(df.index.max().date()),
             "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return df


def panel(loader, symbols: list[str], **kwargs) -> pd.DataFrame:
    """Wide close-price panel, outer-joined on date. Missing symbols stay NaN."""
    frames = {}
    for sym in symbols:
        try:
            df = loader(sym, **kwargs)
            frames[sym] = df["close"]
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] {sym}: {exc}")
    if not frames:
        raise RuntimeError("no symbols loaded")
    return pd.concat(frames, axis=1).sort_index()
