#!/usr/bin/env python3
"""First-observation point-in-time universe builder.

The approximation removes *left-censoring* (a symbol is excluded before its first
available close) and *right-censoring* (excluded after its last available close),
so a symbol only counts on dates it was actually trading -- but it does NOT
remove delisting-with-poor-returns bias, because a delisted name's final
observations are still whatever the vendor froze them at.
"""
from __future__ import annotations

import csv
import glob
import os
from datetime import date as _date
from typing import Dict, Iterable, Optional

import pandas as pd


def _load_close_series(path: str) -> pd.Series:
    """Read one Date,Close CSV -> sorted Series of positive closes indexed by date."""
    df = pd.read_csv(path, parse_dates=["Date"]).set_index("Date")
    df = df[~df.index.duplicated(keep="last")].sort_index()
    close = pd.to_numeric(df["Close"], errors="coerce").dropna()
    return close[close > 0]


def build_pit_universe(
    date,
    cache_dir: str,
    symbols: Optional[Iterable[str]] = None,
) -> list:
    """Return the symbols trading on ``date`` (first close <= date <= last close).

    Parameters
    ----------
    date : str | datetime.date | pd.Timestamp
        The as-of date. Only the calendar date is compared.
    cache_dir : str
        Directory of ``<SYMBOL>_5y.csv`` files (Date,Open,High,Low,Close,Volume).
    symbols : iterable[str] | None
        Restrict to these symbols; default = every ``*_5y.csv`` in ``cache_dir``.

    Returns
    -------
    list[str]
        Sorted symbols whose first available close is on or before ``date`` and
        whose last available close is on or after ``date``.
    """
    asof = pd.Timestamp(date).normalize()
    if symbols is None:
        paths = sorted(glob.glob(os.path.join(cache_dir, "*_5y.csv")))
        wanted = [os.path.basename(p)[: -len("_5y.csv")] for p in paths]
    else:
        wanted = list(symbols)

    out = []
    for sym in wanted:
        path = os.path.join(cache_dir, f"{sym}_5y.csv")
        if not os.path.exists(path):
            continue
        close = _load_close_series(path)
        if close.empty:
            continue
        first, last = close.index[0], close.index[-1]
        if first <= asof <= last:
            out.append(sym)
    return sorted(out)


def pit_universe_panel(
    dates,
    cache_dir: str,
    symbols: Optional[Iterable[str]] = None,
) -> Dict[str, set]:
    """Return ``{date_str: set(symbols_trading)}`` for every date in ``dates``."""
    return {str(d)[:10]: set(build_pit_universe(d, cache_dir, symbols)) for d in dates}
