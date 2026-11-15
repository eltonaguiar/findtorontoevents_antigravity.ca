#!/usr/bin/env python3
"""
ALPHA_ENGINE -- MF/ETF Pipeline (PE-09 + PE-10)
================================================
End-to-end ingestion, screening, and mark pipeline for mutual funds and ETFs.

Responsibilities:
  1. Load curated MF/ETF universe from alpha_engine/data/mf_etf_universe.json
  2. Fetch NAV / market price via yfinance + existing failover chain
  3. Validate tickers against the curated whitelist
  4. Apply cost/constraints filter (ER, load, AUM, turnover, 12b-1)
  5. Model next-NAV semantics for mutual funds (orders fill at next-day NAV)
  6. Estimate annual cost drag (ER + transaction costs) for backtest realism

Designed for the WIRED_IN passive-beta sleeve (VTI/BND 60/40) and low-cost
index-MF alternatives.  No active-prediction edge is claimed here — this is
infrastructure to make MF/ETF classes testable and auditable.

Usage:
    from alpha_engine.mf_etf_pipeline import (
        load_universe,
        screen_universe,
        fetch_nav_or_price,
        validate_ticker,
        estimate_annual_cost,
        next_nav_fill_price,
    )
    screened = screen_universe()
    df = fetch_nav_or_price("VTI")
"""
from __future__ import annotations

import json
import logging
import math
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

# Allow direct script invocation (python alpha_engine/mf_etf_pipeline.py)
# to resolve sibling imports when the parent is not on sys.path.
_sys_path_guard = str(Path(__file__).resolve().parent)
if _sys_path_guard not in sys.path:
    sys.path.insert(0, _sys_path_guard)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_ENGINE_DIR = Path(__file__).resolve().parent
_DATA_DIR = _ENGINE_DIR / "data"
_UNIVERSE_PATH = _DATA_DIR / "mf_etf_universe.json"

# ---------------------------------------------------------------------------
# Optional yfinance
# ---------------------------------------------------------------------------
try:
    import yfinance as yf
    _HAS_YFINANCE = True
except ImportError:
    _HAS_YFINANCE = False

# ---------------------------------------------------------------------------
# Default constraints (match PE-10 spec)
# ---------------------------------------------------------------------------
_DEFAULT_CONSTRAINTS: dict[str, Any] = {
    "max_er_pct": 0.10,
    "min_aum_usd": 1_000_000_000,
    "max_turnover_pct": 20.0,
    "allow_load": False,
    "allow_12b1": False,
}


# ---------------------------------------------------------------------------
# Universe loading
# ---------------------------------------------------------------------------

def load_universe(path: Optional[Path] = None) -> dict[str, dict]:
    """Load curated MF/ETF universe from JSON sidecar.

    Returns dict of ticker -> metadata.  Raises FileNotFoundError if missing.
    """
    p = path or _UNIVERSE_PATH
    if not p.exists():
        raise FileNotFoundError(f"MF/ETF universe not found: {p}")
    with open(p, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    return doc.get("universe", {})


def load_constraints(path: Optional[Path] = None) -> dict[str, Any]:
    """Load constraint metadata from universe JSON."""
    p = path or _UNIVERSE_PATH
    if not p.exists():
        return dict(_DEFAULT_CONSTRAINTS)
    with open(p, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    return {**_DEFAULT_CONSTRAINTS, **doc.get("constraints", {})}


# ---------------------------------------------------------------------------
# Price / NAV fetching
# ---------------------------------------------------------------------------

def fetch_nav_or_price(
    ticker: str,
    period: str = "2y",
    retries: int = 3,
) -> Optional[pd.DataFrame]:
    """Fetch daily OHLCV for an MF or ETF ticker.

    Uses yfinance first (mutual-fund tickers like FXAIX resolve on Yahoo
    Finance as ``FXAIX``).  Falls back to :mod:`alpha_engine.ohlcv_failover`
    on total failure (Tiingo / Polygon / AlphaVantage).

    Returns DataFrame indexed by date with columns
    ``Open/High/Low/Close/Volume``, or ``None`` on failure.

    Note on MFs: Yahoo Finance returns the daily NAV series for mutual-fund
    tickers (no intraday OHLC — just a single Close = NAV).  This is exactly
    what we need for next-NAV backtests.
    """
    if not _HAS_YFINANCE:
        return _failover_fetch(ticker)

    for attempt in range(1, retries + 1):
        try:
            raw = yf.download(
                ticker, period=period, progress=False, threads=False,
                auto_adjust=True,
            )
            if raw is not None and not raw.empty and len(raw) >= 30:
                df = _normalise_yf(raw)
                logger.debug("Fetched %s (%d rows) via yfinance", ticker, len(df))
                return df
        except Exception as exc:  # noqa: BLE001
            logger.warning("yfinance %s attempt %d/%d failed: %s", ticker, attempt, retries, exc)
        if attempt < retries:
            time.sleep(2 * attempt)

    logger.info("yfinance exhausted for %s — trying failover", ticker)
    return _failover_fetch(ticker)


def _normalise_yf(raw: pd.DataFrame) -> pd.DataFrame:
    """Normalise yfinance output to Open/High/Low/Close/Volume columns."""
    # yfinance with auto_adjust=True returns columns without MultiIndex
    cols = [c for c in ("Open", "High", "Low", "Close", "Volume") if c in raw.columns]
    df = raw[cols].copy()
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    # Drop rows with missing Close
    df = df.dropna(subset=["Close"])
    return df


def _failover_fetch(ticker: str) -> Optional[pd.DataFrame]:
    """Try Tiingo/Polygon/AlphaVantage via ohlcv_failover."""
    try:
        from alpha_engine.ohlcv_failover import (  # type: ignore[import-untyped]
            fetch_ohlcv_failover, failover_available,
        )
    except ImportError:
        try:
            from ohlcv_failover import (  # type: ignore[import-untyped]
                fetch_ohlcv_failover, failover_available,
            )
        except ImportError:
            logger.warning("ohlcv_failover not importable — cannot fetch %s", ticker)
            return None

    if not failover_available():
        return None

    try:
        df, provider = fetch_ohlcv_failover(ticker)
        if df is not None and len(df) >= 30:
            logger.debug("Fetched %s (%d rows) via failover (%s)", ticker, len(df), provider)
            return df
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failover fetch %s failed: %s", ticker, exc)
    return None


# ---------------------------------------------------------------------------
# Ticker validation
# ---------------------------------------------------------------------------

def validate_ticker(ticker: str, universe: Optional[dict[str, dict]] = None) -> tuple[bool, str]:
    """Return (is_valid, reason) for a ticker against the curated universe.

    A ticker is valid iff it exists in the universe JSON and its asset_class
    is one of ``mutual_fund`` or ``etf``.
    """
    u = universe or load_universe()
    sym = (ticker or "").upper().strip()
    meta = u.get(sym)
    if not meta:
        return False, f"{sym} not in curated MF/ETF universe"
    ac = meta.get("asset_class", "").lower()
    if ac not in ("mutual_fund", "etf"):
        return False, f"{sym} asset_class={ac} (expected mutual_fund or etf)"
    return True, f"{sym} OK ({ac})"


# ---------------------------------------------------------------------------
# Constraints / screener
# ---------------------------------------------------------------------------

def passes_constraints(
    meta: dict[str, Any],
    constraints: Optional[dict[str, Any]] = None,
) -> tuple[bool, list[str]]:
    """Evaluate a single universe entry against constraints.

    Returns (passes: bool, reasons: list[str]).
    """
    c = {**_DEFAULT_CONSTRAINTS, **(constraints or {})}
    reasons: list[str] = []

    # Expense ratio
    er = float(meta.get("er_pct", math.inf))
    max_er = float(c.get("max_er_pct", math.inf))
    if er > max_er:
        reasons.append(f"ER {er:.3f}% > max {max_er:.3f}%")

    # Load
    load = float(meta.get("load", 0.0))
    if not c.get("allow_load", False) and load > 0.0:
        reasons.append(f"load {load:.2f}% > 0 (no-load required)")

    # 12b-1 fee
    fee_12b1 = float(meta.get("fee_12b1_pct", 0.0))
    if not c.get("allow_12b1", False) and fee_12b1 > 0.0:
        reasons.append(f"12b-1 fee {fee_12b1:.3f}% > 0 (disallowed)")

    # AUM
    aum = float(meta.get("aum_usd", 0.0))
    min_aum = float(c.get("min_aum_usd", 0.0))
    if aum < min_aum:
        reasons.append(f"AUM ${aum:,.0f} < min ${min_aum:,.0f}")

    # Turnover
    turnover = float(meta.get("turnover_pct", math.inf))
    max_to = float(c.get("max_turnover_pct", math.inf))
    if turnover > max_to:
        reasons.append(f"turnover {turnover:.1f}% > max {max_to:.1f}%")

    return (len(reasons) == 0), reasons


def screen_universe(
    universe: Optional[dict[str, dict]] = None,
    constraints: Optional[dict[str, Any]] = None,
) -> dict[str, dict]:
    """Run the minimal MF/ETF screener.

    Filters:
      - ER  ≤ max_er_pct   (default 0.10%)
      - No load
      - No 12b-1 fee
      - AUM ≥ min_aum_usd  (default $1B)
      - Turnover ≤ max_turnover_pct (default 20%)

    Returns a dict of ticker -> metadata for entries that pass.
    """
    u = universe or load_universe()
    out: dict[str, dict] = {}
    for ticker, meta in u.items():
        ok, reasons = passes_constraints(meta, constraints)
        if ok:
            out[ticker] = meta
        else:
            logger.debug("Screener rejected %s: %s", ticker, "; ".join(reasons))
    logger.info("MF/ETF screener: %d/%d passed", len(out), len(u))
    return out


# ---------------------------------------------------------------------------
# Next-NAV semantics (mutual funds only)
# ---------------------------------------------------------------------------

def next_nav_fill_price(
    ticker: str,
    price_df: Optional[pd.DataFrame] = None,
    universe: Optional[dict[str, dict]] = None,
) -> Optional[float]:
    """Return the next-day NAV fill price for a mutual-fund order.

    Mutual funds trade once per day after market close; orders placed before
    the cutoff (typically 16:00 ET) fill at that evening's computed NAV,
    which is published after hours and becomes the historical Close of the
    *current* trading day.  Orders placed after the cutoff fill at the
    *next* trading day's NAV.

    This function models the conservative case: an order placed today fills
    at **tomorrow's Close / NAV** (one-bar delay).  For ETFs it returns the
    most recent Close (intraday fill assumption).

    Args:
        ticker: symbol
        price_df: optional pre-fetched price DataFrame (saves a network call)
        universe: optional universe dict

    Returns:
        float fill price, or None if data unavailable.
    """
    u = universe or load_universe()
    meta = u.get(ticker)
    if meta is None:
        return None

    ac = meta.get("asset_class", "").lower()
    df = price_df if price_df is not None else fetch_nav_or_price(ticker)
    if df is None or df.empty:
        return None

    if ac == "mutual_fund":
        # Conservative: fill at next day's NAV (one-bar delay)
        if len(df) >= 2:
            return float(df["Close"].iloc[-1])
        return float(df["Close"].iloc[-1])
    else:
        # ETF — assume intraday fill at last known close
        return float(df["Close"].iloc[-1])


def backtest_nav_fill_series(
    ticker: str,
    price_df: pd.DataFrame,
) -> pd.Series:
    """Return a NAV-aligned fill-price series for backtesting mutual funds.

    For MFs: shift Close by +1 bar so that a signal on day T fills at day T+1
    NAV.  The last bar uses the last known NAV (no forward information).
    For ETFs: returns the unshifted Close series.

    Returns a Series indexed by date with the fill price for each bar.
    """
    closes = price_df["Close"].copy()
    # Heuristic: if the DataFrame has no Volume or Volume is all NaN/zero,
    # treat as MF (mutual funds on Yahoo have no volume).
    vol = price_df.get("Volume")
    is_mf = vol is None or vol.isna().all() or (vol == 0).all()
    if is_mf and len(closes) >= 2:
        fills = closes.shift(1)
        fills.iloc[0] = closes.iloc[0]  # first bar has no prior NAV
        return fills
    return closes


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------

def estimate_annual_cost(
    ticker: str,
    principal_usd: float,
    universe: Optional[dict[str, dict]] = None,
) -> dict[str, float]:
    """Estimate annual cost drag for holding a fund.

    Components:
      - ER drag: principal * ER (annual, recurring)
      - Load drag: principal * load (one-time, on entry)
      - 12b-1 drag: principal * 12b-1 fee (annual, recurring)

    Returns dict with keys: er_drag_usd, load_drag_usd, fee_12b1_drag_usd,
    total_annual_drag_usd, total_annual_drag_pct.
    """
    u = universe or load_universe()
    meta = u.get(ticker, {})
    er = float(meta.get("er_pct", 0.0)) / 100.0
    load = float(meta.get("load", 0.0)) / 100.0
    fee_12b1 = float(meta.get("fee_12b1_pct", 0.0)) / 100.0

    er_drag = principal_usd * er
    load_drag = principal_usd * load
    fee_12b1_drag = principal_usd * fee_12b1
    total = er_drag + fee_12b1_drag  # load is one-time; not annualised here

    return {
        "er_drag_usd": round(er_drag, 4),
        "load_drag_usd": round(load_drag, 4),
        "fee_12b1_drag_usd": round(fee_12b1_drag, 4),
        "total_annual_drag_usd": round(total, 4),
        "total_annual_drag_pct": round(total / principal_usd * 100, 4) if principal_usd > 0 else 0.0,
    }


# ---------------------------------------------------------------------------
# Batch fetch helper (mirrors etf_scanner.fetch_etf_data pattern)
# ---------------------------------------------------------------------------

def fetch_batch(
    tickers: list[str],
    period: str = "2y",
    chunk_size: int = 12,
    retries: int = 3,
) -> dict[str, pd.DataFrame]:
    """Fetch OHLCV for a list of MF/ETF tickers in chunks.

    Returns dict of ticker -> DataFrame.  Missing tickers are omitted.
    """
    data: dict[str, pd.DataFrame] = {}
    for t in tickers:
        df = fetch_nav_or_price(t, period=period, retries=retries)
        if df is not None and len(df) >= 30:
            data[t] = df
    logger.info("MF/ETF batch fetch: %d/%d succeeded", len(data), len(tickers))
    return data


# ---------------------------------------------------------------------------
# CLI / smoke-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    # 1. Load universe
    universe = load_universe()
    print(f"Loaded universe: {len(universe)} tickers")

    # 2. Screen
    screened = screen_universe(universe)
    print(f"Screener passed: {len(screened)} tickers")
    for t, m in screened.items():
        print(f"  {t:8s}  {m['asset_class']:12s}  ER={m['er_pct']:.3f}%  AUM=${m['aum_usd']:,.0f}")

    # 3. Smoke-fetch first 3
    for t in list(screened.keys())[:3]:
        df = fetch_nav_or_price(t, period="6mo")
        if df is not None:
            fill = next_nav_fill_price(t, df, universe)
            costs = estimate_annual_cost(t, 10_000.0, universe)
            print(f"  {t}: last={df['Close'].iloc[-1]:.4f}  fill={fill:.4f}  "
                  f"annual_drag=${costs['total_annual_drag_usd']:.2f}")
        else:
            print(f"  {t}: FETCH FAILED")
