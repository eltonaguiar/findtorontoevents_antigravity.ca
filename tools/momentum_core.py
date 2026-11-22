#!/usr/bin/env python3
"""Shared, asset-agnostic primitives for the momentum tests (items 33 and 34).

Why this module exists: the monthly-return alignment is the one place where a
silent one-month lookahead can creep in (it did, during item 33's development --
a backward `pct_change()` labelled by end date paired each weight with the very
return it was formed from). Keeping exactly ONE implementation, imported by both
commodity_momentum.py and bond_momentum.py, means that bug can only be fixed or
reintroduced once. Everything here is unit-tested in
tests/test_commodity_momentum.py and tests/test_bond_momentum.py.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "cache" / "asset_class_review"
RF_ANNUAL = 0.0432  # US 3-mo T-bill, docs/edge_research/07_HURDLE_RATES_2026-11-22.md
COST_SWEEP_BP = [2.0, 5.0, 10.0, 20.0]
BASE_COST_BP = 5.0
N_NULL = 1000
N_BOOT = 10_000
SEED = 20261122


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def load_close_series(symbol: str, data_dir: Path = DATA_DIR) -> pd.Series:
    """Daily close series for one symbol, indexed by date. Raises if unreadable.

    NOTE: the cached `Close` column behaves as a dividend-adjusted series (proven
    for SHY in doc 16); the exact adjustment method is UNMEASURED.
    """
    path = data_dir / f"{symbol}_5y.csv"
    df = pd.read_csv(path, parse_dates=["Date"])
    df = df.dropna(subset=["Close"]).drop_duplicates(subset=["Date"]).sort_values("Date")
    return df.set_index("Date")["Close"].astype(float)


def load_panel(symbols: Sequence[str], data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Aligned daily close panel; inner-joined on common dates so no row is imputed."""
    return pd.DataFrame({s: load_close_series(s, data_dir) for s in symbols}).dropna(how="any")


# --------------------------------------------------------------------------- #
# Monthly grid and returns
# --------------------------------------------------------------------------- #
def month_end_index(prices: pd.DataFrame) -> List[pd.Timestamp]:
    """Last available trading date of each calendar month."""
    idx = prices.index
    s = pd.Series(idx, index=idx)
    return list(s.groupby([idx.year, idx.month]).last())


def monthly_returns(prices: pd.DataFrame, me: Sequence[pd.Timestamp]) -> pd.DataFrame:
    """FORWARD return, labelled by period START: row me[k] = px[me[k+1]]/px[me[k]] - 1.

    Labelling by start is what makes a backtest lookahead-free: a weight formed from
    data up to me[k] is multiplied by the return that *follows* me[k].
    """
    px = prices.loc[list(me)]
    fwd = px.shift(-1) / px - 1.0
    fwd = fwd.iloc[:-1]                  # last month-end has no forward return
    fwd.index = pd.Index(list(me)[:-1])  # label by period start
    return fwd


def formation_return(prices: pd.DataFrame, t: pd.Timestamp,
                     lookback: int = 252) -> Dict[str, float]:
    """Trailing `lookback`-trading-day return ending at t, per symbol.

    Uses only rows at or before t, so there is no lookahead. Symbols with
    insufficient history are omitted (never imputed).
    """
    hist = prices.loc[:t]
    if len(hist) <= lookback:
        return {}
    start, end = hist.iloc[-lookback - 1], hist.iloc[-1]
    out = {}
    for sym in prices.columns:
        s, e = start[sym], end[sym]
        if pd.notna(s) and pd.notna(e) and s > 0:
            out[sym] = float(e / s - 1.0)
    return out


def mom_12_1(monthly_px: pd.DataFrame, t: pd.Timestamp) -> Dict[str, float]:
    """12-1 month formation at month-end t: months t-12..t-2, skipping t-1.

    `monthly_px` MUST already be resampled to month-ends -- iloc[-13] means twelve
    MONTHS back only on a monthly grid. Passing daily data would silently turn
    this into a ~13-day rule, so that misuse raises instead of returning a number.
    """
    hist = monthly_px.loc[:t]
    # Median gap, not the last gap: the final month may be partial (data ends
    # mid-month) and would false-positive a strict last-gap check. Daily data has a
    # median gap of 1 day; month-end data ~30.
    if len(hist) >= 5 and float(np.median(np.diff(hist.index).astype("timedelta64[D]").astype(int))) < 20:
        raise ValueError("mom_12_1 expects month-end data; got a sub-monthly index")
    if len(hist) < 12:
        return {}           # need t-12 .. t-1 inclusive = 12 month-end prices
    p_end = hist.iloc[-2]    # skip the most recent month (t-1 -> t) to dodge reversal
    p_start = hist.iloc[-12]  # exactly 12 months before p_end
    out = {}
    for sym in monthly_px.columns:
        s, e = p_start[sym], p_end[sym]
        if pd.notna(s) and pd.notna(e) and s > 0:
            out[sym] = float(e / s - 1.0)
    return out


def mom_12_1_by_period(monthly_px: pd.DataFrame,
                      periods: Sequence[pd.Timestamp]) -> Dict[pd.Timestamp, Dict[str, float]]:
    """mom_12_1 evaluated at the month-end that closes each return period.

    `periods` are the START dates returned by monthly_returns(); the decision for the
    period starting at t is made at the month-end ending that period, i.e. after
    monthly_px.index[k+1] where periods[k] == monthly_px.index[k]. Periods whose
    formation window is incomplete map to {} (held as cash, never imputed).
    """
    pos = {d: i for i, d in enumerate(monthly_px.index)}
    out: Dict[pd.Timestamp, Dict[str, float]] = {}
    for p in periods:
        i = pos.get(p)
        out[p] = {} if i is None or i + 1 >= len(monthly_px.index) else mom_12_1(
            monthly_px, monthly_px.index[i + 1])
    return out


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
def max_drawdown(monthly: np.ndarray) -> float:
    eq = np.cumprod(1.0 + monthly)
    peak = np.maximum.accumulate(np.concatenate([[1.0], eq]))[1:]
    return float(np.min(eq / peak - 1.0))


def skewness(x: np.ndarray) -> float:
    m = x.mean()
    s = x.std(ddof=0)
    return float(0.0 if s == 0 else np.mean((x - m) ** 3) / s ** 3)


def cagr_from_monthly(monthly: np.ndarray) -> float:
    n = len(monthly)
    if n == 0:
        return float("nan")
    total = float(np.prod(1.0 + monthly))
    if total <= 0:
        return -1.0
    return total ** (12.0 / n) - 1.0


def summarize(monthly: np.ndarray, rf_annual: float = RF_ANNUAL) -> Dict[str, float]:
    monthly = np.asarray(monthly, dtype=float)
    n = len(monthly)
    nan_keys = ["cagr", "vol", "sharpe_vs_rf", "maxdd", "skew", "worst_month",
                "pct_positive", "mean_month", "median_month"]
    if n < 2:
        return {"n": n, **{k: float("nan") for k in nan_keys}}
    sd = monthly.std(ddof=1)
    rf_m = rf_annual / 12.0
    # A constant series has std ~1e-18 from float noise, not exactly 0; without a
    # tolerance the Sharpe would print as ~1e16 -- a fabricated-looking number.
    sharpe = float((monthly.mean() - rf_m) / sd * np.sqrt(12)) if sd > 1e-12 else float("nan")
    return {
        "n": n, "cagr": cagr_from_monthly(monthly),
        "vol": float(sd * np.sqrt(12)), "sharpe_vs_rf": sharpe,
        "maxdd": max_drawdown(monthly), "skew": skewness(monthly),
        "worst_month": float(monthly.min()), "pct_positive": float((monthly > 0).mean()),
        "mean_month": float(monthly.mean()), "median_month": float(np.median(monthly)),
    }


def profit_factor(monthly: np.ndarray) -> Optional[float]:
    """Gross profit / gross loss over monthly periods. Callers MUST label the cost basis."""
    gains = monthly[monthly > 0].sum()
    losses = -monthly[monthly < 0].sum()
    return float(gains / losses) if losses > 0 else None


# --------------------------------------------------------------------------- #
# Bootstrap
# --------------------------------------------------------------------------- #
def bootstrap_excess_cagr(strategy_monthly: np.ndarray, spy_monthly: np.ndarray,
                          n_boot: int = N_BOOT, seed: int = SEED) -> Dict:
    """Paired bootstrap of CAGR(strategy) - CAGR(SPY) on aligned monthly returns."""
    s = np.asarray(strategy_monthly, dtype=float)
    b = np.asarray(spy_monthly, dtype=float)
    n = min(len(s), len(b))
    s, b = s[:n], b[:n]
    if n < 12:
        return {"excess_cagr": float("nan"), "ci95": [float("nan"), float("nan")],
                "n_boot": n_boot, "n_obs": n, "note": "INSUFFICIENT overlap"}
    point = cagr_from_monthly(s) - cagr_from_monthly(b)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    ts = np.prod(1.0 + s[idx], axis=1)
    tb = np.prod(1.0 + b[idx], axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        ex = np.where((ts > 0) & (tb > 0), ts ** (12.0 / n) - tb ** (12.0 / n), np.nan)
    ex = ex[np.isfinite(ex)]
    lo, hi = np.percentile(ex, [2.5, 97.5])
    return {"excess_cagr": float(point), "ci95": [float(lo), float(hi)],
            "ci_excludes_zero": bool(lo > 0 or hi < 0), "n_boot": n_boot, "n_obs": n}


# --------------------------------------------------------------------------- #
# JSON hygiene
# --------------------------------------------------------------------------- #
def sanitize(obj):
    """Replace non-finite floats with None so the JSON is valid and honest."""
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize(v) for v in obj]
    if isinstance(obj, (np.floating, float)):
        return None if not np.isfinite(float(obj)) else float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return [sanitize(x) for x in obj.tolist()]
    return obj
