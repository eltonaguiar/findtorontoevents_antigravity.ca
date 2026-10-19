"""Research dataset harness (extended history) for the combined book.

This is a SEPARATE dataset path from the live paper-trade pilot. It uses
spliced mutual-fund proxies, Ken French high-OP/value portfolios, and the CBOE
PUT index to reproduce the reference grokbot backtest on full history (from
~1988) rather than the raw-ETF-only history (which starts ~1993-2013).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from combined_book.fetch import (
    RESEARCH_TREND_UNIVERSE,
    get_put_index_daily_closes,
    get_research_daily_closes,
    load_kfrench_quality_value_monthly,
    monthly_returns,
)
from combined_book.simulator import book_return_series, compute_stats


def _tsmom_sleeve(closes, lbs=(1, 3, 12), tgt=0.10, cost=0.001):
    """Reference TSMOM trend sleeve (matches grokbot/combined-book-edge-proof run.py)."""
    M = pd.DataFrame({s: c.resample("ME").last() for s, c in closes.items()})
    R = M.pct_change(fill_method=None)
    D = pd.DataFrame({s: c.pct_change(fill_method=None) for s, c in closes.items()})
    px = (1 + R.fillna(0)).cumprod().where(R.notna())
    sig = sum(np.sign(px / px.shift(l) - 1) for l in lbs) / len(lbs)
    vol = D.rolling(63).std().resample("ME").last().reindex(R.index) * math.sqrt(252)
    navail = sig.notna().sum(axis=1).replace(0, np.nan)
    w = (sig * tgt / vol).div(np.sqrt(navail), axis=0)
    w = w.clip(-1, 1)
    g = w.abs().sum(axis=1)
    w = w.div(np.maximum(g / 2.0, 1), axis=0)
    w = w.fillna(0)
    ret = (w.shift(1) * R.fillna(0)).sum(axis=1) - cost * w.diff().abs().sum(axis=1)
    return ret[w.shift(1).abs().sum(axis=1) > 0]


def build_research_sleeve_returns(cache_dir=None) -> dict[str, pd.Series]:
    """Build the three sleeve monthly-return series from the research dataset."""
    spliced = get_research_daily_closes(cache_dir=cache_dir)
    trend_closes = {s: c for s, c in spliced.items() if s in RESEARCH_TREND_UNIVERSE}

    trend_ret = _tsmom_sleeve(trend_closes)

    quality_ret = load_kfrench_quality_value_monthly()

    put_closes = get_put_index_daily_closes(cache_dir=cache_dir)
    put_ret = monthly_returns(put_closes)

    return {"trend": trend_ret, "quality": quality_ret, "put": put_ret}


def _rolling_invvol_weights(sleeve: dict[str, pd.Series], window=36):
    """Reference-style rolling inverse-vol weights (36m window, shift 1)."""
    frame = pd.DataFrame(sleeve)
    iv = 1.0 / frame.rolling(window, min_periods=24).std().shift(1)
    w = iv.div(iv.sum(axis=1), axis=0).clip(upper=0.40)
    return w


def _overlay_scale(r: pd.Series, tgt: float, lb=12) -> pd.Series:
    """Scale a return series to a target trailing vol, capped at 1.0 (<=1)."""
    v = r.rolling(lb).std().shift(1) * math.sqrt(12)
    s = (tgt / v).clip(upper=1.0).fillna(1.0)
    return r * s


def run_reference_backtest(vol_target=0.05, start=None, end=None, cache_dir=None):
    """Mirror the reference grokbot run's combined book + 5% overlay.

    Building: rolling inverse-vol weights on the three research sleeves, 40%
    cap per sleeve, then the overlay scales the combined series to a target
    trailing vol (capped at 1.0 so it never increases vol above natural).
    """
    sleeve = build_research_sleeve_returns(cache_dir=cache_dir)
    w = _rolling_invvol_weights(sleeve)
    frame = pd.DataFrame(sleeve)
    comb = (frame * w).sum(axis=1)[w.notna().any(axis=1) & (w.sum(axis=1) > 0)]
    r = _overlay_scale(comb.dropna(), vol_target)
    r = r.loc[~r.index.duplicated(keep="last")].sort_index()
    r.index = pd.to_datetime(r.index)
    if start:
        r = r.loc[pd.Timestamp(start):]
    if end:
        r = r.loc[:pd.Timestamp(end)]
    r = r.dropna()
    return {"returns": r, "weights": w, "stats": compute_stats(r), "sleeves": sleeve}


def run_research_backtest(vol_cap=0.05, start=None, end=None, cache_dir=None):
    """Run the standalone combined-book backtest on the research dataset."""
    return run_reference_backtest(vol_target=vol_cap, start=start, end=end, cache_dir=cache_dir)


def sleeve_stats(sleeve_returns: dict[str, pd.Series]) -> dict[str, dict]:
    """Per-sleeve stats (for side-by-side comparison vs results.csv)."""
    return {k: compute_stats(v) for k, v in sleeve_returns.items() if len(v) > 0}
