"""FRED macro overlay for FOREX + cross-asset regime context.

Top-7 swarm queue item #2 (2026-05-08). Sibling to alpha_engine/bond_data_fred.py
which fills the BOND series desert. This module focuses on the FOREX-facing
macro context: USD strength, rate path, and curve shape.

Backend: re-uses bond_data_fred.fetch_fred_series so cache + key handling are
shared. No new HTTP code path.

Series tracked:
    DTWEXBGS    Trade-weighted USD broad index (FOREX direction)
    DGS10       10Y Treasury yield (rate path)
    DGS2        2Y Treasury yield (front-end)
    T10Y2Y      10Y - 2Y curve spread (recession proxy)
    FEDFUNDS    Fed funds target rate
    VIXCLS      VIX (cross-asset risk-off proxy)

Public API:
    get_macro_context(refresh=False) -> dict
        Returns a snapshot dict with the latest values and computed regime
        labels. Cached for 1 hour by default to reduce FRED API hits.
    summarize_for_dashboard() -> dict
        Same data shaped for /audit display (top-level "macro_context" key).

Regime labels (heuristic, NOT a model):
    usd_regime in {"strong", "weak", "neutral"}      -- DTWEXBGS 30d delta
    curve_regime in {"inverted", "flat", "steep"}    -- T10Y2Y latest
    vol_regime in {"low", "normal", "elevated"}      -- VIXCLS latest

Wiring plan (Wire-Up Rule compliance):
    1. Dashboard surface (this PR): audit_trail/dashboard_generator.py adds a
       `macro_context` payload key calling summarize_for_dashboard(). Caller
       in production pick-generation path -> contributes to /audit display.
    2. FOREX confidence overlay (next PR): alpha_engine/feed_hygiene.py adds
       a soft-multiplier on FOREX pick confidence from get_macro_context().
       Off by default behind FRED_FX_OVERLAY_ENABLED=1. Acceptance criteria:
       no n drop > 10% on FOREX after 7d; macro_dampened picks observable.
    3. BOND scoring overlay: alpha_engine/bond_scanner.py adds curve_regime
       to bt_pf shrinkage when curve is inverted (avoid overconfidence on
       backtest-period strong-curve setups).

Rollback:
    FRED_MACRO_DISABLED=1  -> get_macro_context returns {} (no-op).
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

_CACHE: dict[str, Any] = {"ts": 0.0, "data": None}
_CACHE_TTL_SEC = 3600  # 1 hour

_SERIES = ("DTWEXBGS", "DGS10", "DGS2", "T10Y2Y", "FEDFUNDS", "VIXCLS")


def _disabled() -> bool:
    return os.environ.get("FRED_MACRO_DISABLED", "0") == "1"


def _safe_fetch(series_id: str, days: int = 60) -> list[dict]:
    try:
        from alpha_engine.bond_data_fred import fetch_fred_series
    except Exception as exc:
        logger.debug("bond_data_fred import failed: %s", exc)
        return []
    end = datetime.now(timezone.utc).date().isoformat()
    start = (datetime.now(timezone.utc).date() - timedelta(days=days)).isoformat()
    try:
        return fetch_fred_series(series_id, start, end) or []
    except Exception as exc:
        logger.warning("FRED fetch %s failed: %s", series_id, exc)
        return []


def _last_value(rows: list[dict]) -> tuple[float | None, str | None]:
    for r in reversed(rows or []):
        v = r.get("value")
        if v is None:
            continue
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        return fv, str(r.get("date") or "")
    return None, None


def _delta_pct(rows: list[dict], lookback: int = 30) -> float | None:
    if not rows or len(rows) < 2:
        return None
    last_v, _ = _last_value(rows)
    earlier = rows[max(0, len(rows) - lookback - 1)] if rows else None
    try:
        prev = float(earlier.get("value")) if earlier else None
    except Exception:
        prev = None
    if last_v is None or not prev:
        return None
    return round(((last_v - prev) / prev) * 100.0, 2)


def _classify_usd(d30: float | None) -> str:
    if d30 is None:
        return "unknown"
    if d30 >= 1.5:
        return "strong"
    if d30 <= -1.5:
        return "weak"
    return "neutral"


def _classify_curve(t10y2y: float | None) -> str:
    if t10y2y is None:
        return "unknown"
    if t10y2y < -0.05:
        return "inverted"
    if t10y2y < 0.5:
        return "flat"
    return "steep"


def _classify_vol(vix: float | None) -> str:
    if vix is None:
        return "unknown"
    if vix < 15:
        return "low"
    if vix < 25:
        return "normal"
    return "elevated"


def get_macro_context(refresh: bool = False) -> dict:
    """Return snapshot of FRED macro indicators + regime labels.

    Cached for _CACHE_TTL_SEC. Returns {} if FRED_MACRO_DISABLED=1.
    """
    if _disabled():
        return {}
    now = time.time()
    if not refresh and _CACHE["data"] and now - _CACHE["ts"] < _CACHE_TTL_SEC:
        return _CACHE["data"]

    raw: dict[str, list[dict]] = {sid: _safe_fetch(sid) for sid in _SERIES}
    last: dict[str, tuple[float | None, str | None]] = {sid: _last_value(rows) for sid, rows in raw.items()}

    dtwx_30d = _delta_pct(raw.get("DTWEXBGS") or [], 30)
    t10y2y_v = last["T10Y2Y"][0]
    vix_v = last["VIXCLS"][0]

    snapshot: dict[str, Any] = {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "indicators": {
            sid: {"value": last[sid][0], "date": last[sid][1]}
            for sid in _SERIES
        },
        "deltas": {
            "DTWEXBGS_30d_pct": dtwx_30d,
        },
        "regime": {
            "usd": _classify_usd(dtwx_30d),
            "curve": _classify_curve(t10y2y_v),
            "vol": _classify_vol(vix_v),
        },
        "disclaimer": "Macro indicators sourced from FRED. NOT FINANCIAL ADVICE.",
    }
    _CACHE["data"] = snapshot
    _CACHE["ts"] = now
    return snapshot


def summarize_for_dashboard() -> dict:
    """Shape the snapshot for /audit consumption.

    Returns {} if FRED_MACRO_DISABLED=1 or if all fetches failed (so the
    dashboard renderer can guard with a single truthy check).
    """
    snap = get_macro_context()
    if not snap:
        return {}
    inds = snap.get("indicators") or {}
    if not any(d.get("value") is not None for d in inds.values()):
        return {}
    return snap


__all__ = ["get_macro_context", "summarize_for_dashboard"]
