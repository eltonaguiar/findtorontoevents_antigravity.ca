"""Fetch historical daily closes/returns for the combined-book ETF universe."""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

UNIVERSE = {
    "SPY": "trend_stock", "EFA": "trend_stock", "EEM": "trend_stock",
    "IWM": "trend_stock",
    "TLT": "trend_bond", "IEF": "trend_bond", "SHY": "trend_bond",
    "LQD": "trend_bond", "HYG": "trend_bond", "TIP": "trend_bond",
    "GLD": "trend_comm", "DBC": "trend_comm", "USO": "trend_comm",
    "SLV": "trend_comm",
    "VNQ": "trend_re",
    "QUAL": "quality", "VLUE": "quality", "MTUM": "quality", "USMV": "quality",
    "XYLD": "put_proxy", "PUT": "put_index",
}


def _default_cache_dir() -> Path:
    return Path(os.environ.get("COMBINED_BOOK_CACHE", "combined_book/data"))


def _write_cache(closes: dict, cache_dir: Path) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    for sym, series in closes.items():
        series.to_frame(name="close").to_csv(cache_dir / f"{sym}.csv")


def _read_cache(sym: str, cache_dir: Path) -> pd.Series | None:
    path = cache_dir / f"{sym}.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    return df["close"].dropna()


def _download(symbol: str) -> pd.Series:
    try:
        import yfinance as yf
    except ImportError as exc:  # pragma: no cover - env dependent
        raise RuntimeError("yfinance is required to download missing data") from exc
    df = yf.download(symbol, auto_adjust=True, progress=False)
    close = df["Close"].squeeze()
    close.index = pd.to_datetime(close.index)
    return close.dropna()


def get_daily_closes(
    symbols: list[str], cache_dir: Path | None = None
) -> dict[str, pd.Series]:
    cache_dir = cache_dir or _default_cache_dir()
    out: dict[str, pd.Series] = {}
    missing: list[str] = []
    for sym in symbols:
        cached = _read_cache(sym, cache_dir)
        if cached is not None and not cached.empty:
            out[sym] = cached
        else:
            missing.append(sym)
    if missing:
        fetched = {sym: _download(sym) for sym in missing}
        _write_cache(fetched, cache_dir)
        out.update(fetched)
    return out


def monthly_returns(series: pd.Series) -> pd.Series:
    monthly = series.resample("ME").last().dropna()
    if len(monthly) < 2:
        return pd.Series(dtype=float)
    # First month's return is measured against the first available close so
    # the series includes the opening month rather than dropping it.
    first_close = float(series.dropna().iloc[0])
    rets = monthly.pct_change(fill_method=None)
    if first_close > 0:
        rets.iloc[0] = monthly.iloc[0] / first_close - 1.0
    return rets.dropna()
