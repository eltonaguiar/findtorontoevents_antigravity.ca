#!/usr/bin/env python3
"""BOND data-feed scaffold (INCIDENT/ENHANCEMENT BONDS#7) — OPT-IN SIDECAR.

The BOND asset class has n=0 live samples (money_ready_verdict 2026-06-02), so
nothing can be backtested or promoted for it. This module stands up the missing
data feed: bond ETFs (price) + the US Treasury yield curve (FRED), reusing the
project's existing failover fetchers in `data_fetcher`.

OPT-IN / SIDECAR: this module is NOT yet wired into pick generation or scoring.
See the Wiring Plan in the PR. It adds no production behavior; it only provides
the data primitives a future bond sleeve (e.g. duration-timing / yield-curve)
will consume.

API failover follows the repo rule: price via data_fetcher.fetch_ohlcv
(yfinance -> Tiingo/Polygon/AlphaVantage), yields via FRED (free, no key) with
config/cache fallback already handled inside data_fetcher.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import data_fetcher

logger = logging.getLogger(__name__)

# Core liquid bond ETFs spanning the duration spectrum.
BOND_ETFS = ["SHY", "IEF", "TLT", "AGG", "BND", "LQD"]

# US Treasury yield-curve series on FRED (free, no API key).
YIELD_SERIES = {
    "UST3M": "DGS3MO",
    "UST2Y": "DGS2",
    "UST10Y": "DGS10",
    "T10Y2Y": "T10Y2Y",   # 10y-2y spread (recession/curve-inversion signal)
}


def fetch_bond_etfs(period_days: int = 1260) -> Dict[str, Dict[str, Any]]:
    """Return {symbol: {ok, provider, rows, last_close}} for each bond ETF.
    Never raises on a single-symbol failure — degrades per-symbol."""
    out: Dict[str, Dict[str, Any]] = {}
    for sym in BOND_ETFS:
        try:
            df, provider = data_fetcher.fetch_ohlcv(sym, period_days=period_days)
        except Exception as exc:  # noqa: BLE001 — feed must degrade, not crash
            logger.warning("bond ETF %s fetch failed: %s", sym, exc)
            df, provider = None, "error"
        if df is not None and len(df) > 0:
            last_close = float(df["close"].iloc[-1]) if "close" in df else None
            out[sym] = {"ok": True, "provider": provider,
                        "rows": int(len(df)), "last_close": last_close}
        else:
            out[sym] = {"ok": False, "provider": provider,
                        "rows": 0, "last_close": None}
    return out


def fetch_yield_curve(days_back: int = 2000) -> Dict[str, Dict[str, Any]]:
    """Return {name: {ok, latest, n}} for each Treasury yield series."""
    out: Dict[str, Dict[str, Any]] = {}
    for name, series_id in YIELD_SERIES.items():
        try:
            s = data_fetcher.fetch_fred_series(series_id, days_back=days_back)
        except Exception as exc:  # noqa: BLE001
            logger.warning("FRED %s (%s) failed: %s", name, series_id, exc)
            s = None
        if s is not None and len(s) > 0:
            out[name] = {"ok": True, "series_id": series_id,
                         "latest": float(s.iloc[-1]), "n": int(len(s))}
        else:
            out[name] = {"ok": False, "series_id": series_id,
                         "latest": None, "n": 0}
    return out


def curve_is_inverted(yield_curve: Optional[Dict[str, Dict[str, Any]]] = None) -> Optional[bool]:
    """True if 10y-2y spread < 0 (inverted). None if unavailable."""
    yc = yield_curve if yield_curve is not None else fetch_yield_curve()
    spread = yc.get("T10Y2Y", {})
    if spread.get("ok") and spread.get("latest") is not None:
        return spread["latest"] < 0
    return None


def bond_universe_snapshot() -> Dict[str, Any]:
    """One-call summary a future bond sleeve / dashboard tile can read."""
    etfs = fetch_bond_etfs()
    yc = fetch_yield_curve()
    return {
        "etfs": etfs,
        "yield_curve": yc,
        "n_etfs_ok": sum(1 for v in etfs.values() if v["ok"]),
        "n_yields_ok": sum(1 for v in yc.values() if v["ok"]),
        "curve_inverted": curve_is_inverted(yc),
    }


if __name__ == "__main__":  # pragma: no cover — manual probe (hits network)
    import json
    print(json.dumps(bond_universe_snapshot(), indent=2, default=str))
