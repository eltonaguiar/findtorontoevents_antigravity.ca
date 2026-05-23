#!/usr/bin/env python3
"""
Yield Curve + Fed Policy Macro Data Pipeline
=============================================
Fetches Treasury yield spreads (10Y-2Y, 10Y-3M) and the Effective Federal
Funds Rate, computes a macro risk score, and writes a version-2 snapshot.

Dual-source failover:
  1. FRED API (requires FRED_API_KEY env var)
  2. Yahoo Finance fallback (yfinance if available, else raw Yahoo v8 chart API)

Circuit breaker:
  If BOTH sources fail for 3 consecutive attempts within 1 hour, the pipeline
  trips OPEN and returns a safe neutral/default signal. The breaker state is
  persisted to alpha_engine/data/macro_circuit_breaker.json.

Usage:
    from macro_data_pipeline import run_macro_pipeline, get_macro_snapshot
    snap = run_macro_pipeline()
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

logger = __import__("logging").getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
SNAPSHOT_PATH = DATA_DIR / "macro_factors_snapshot.json"
CB_PATH = DATA_DIR / "macro_circuit_breaker.json"

CACHE_TTL = 3600  # 1 hour
_cache: dict[str, tuple[float, Any]] = {}

FRED_BASE = "https://api.stlouisfed.org/fred"
YAHOO_CHART_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"

# Yahoo tickers for fallback reconstruction
YAHOO_10Y = "^TNX"      # CBOE 10-Year Treasury Note Yield
YAHOO_2Y_FUT = "ZT=F"   # 2-Year T-Note futures (yield ≈ 100 - price)
YAHOO_3M = "^IRX"       # CBOE 13-Week T-Bill (proxy for short end)
YAHOO_SOFR = "SR1=F"    # 1-Month SOFR futures (rate ≈ 100 - price)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict:
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_json(path: Path, data: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        logger.warning("Could not write %s: %s", path, e)


# ---------------------------------------------------------------------------
# FRED API
# ---------------------------------------------------------------------------

def _get_fred_api_key() -> str:
    return os.environ.get("FRED_API_KEY", "")


def _fred_get(series_id: str, limit: int = 90) -> list[dict]:
    """Fetch recent observations for a FRED series."""
    cache_key = f"fred:{series_id}:{limit}"
    if cache_key in _cache:
        ts, val = _cache[cache_key]
        if time.time() - ts < CACHE_TTL:
            return val

    key = _get_fred_api_key()
    if not key:
        return []

    try:
        params = {
            "series_id": series_id,
            "api_key": key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": str(limit),
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{FRED_BASE}/series/observations?{query}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())

        observations = []
        for obs in data.get("observations", []):
            try:
                val = float(obs["value"])
                observations.append({"date": obs["date"], "value": val})
            except (ValueError, KeyError):
                continue

        _cache[cache_key] = (time.time(), observations)
        return observations
    except Exception as e:
        logger.warning("FRED API error for %s: %s", series_id, e)
        return []


# ---------------------------------------------------------------------------
# Yahoo Finance fallback
# ---------------------------------------------------------------------------

def _fetch_yahoo_raw(symbol: str) -> Optional[list[dict]]:
    """
    Fetch daily historical closes from Yahoo v8 chart API.
    Returns list of {"date": str, "close": float} sorted newest first.
    """
    url = (
        f"{YAHOO_CHART_BASE}/{symbol}?"
        f"interval=1d&range=6mo&events=history"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())

        result = data.get("chart", {}).get("result", [None])[0]
        if not result:
            return None

        timestamps = result.get("timestamp", [])
        closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
        if not timestamps or not closes or len(timestamps) != len(closes):
            return None

        observations = []
        for ts, close in zip(timestamps, closes):
            if close is None:
                continue
            dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            observations.append({"date": dt, "close": float(close)})
        observations.sort(key=lambda x: x["date"], reverse=True)
        return observations
    except Exception as e:
        logger.debug("Yahoo raw fetch error for %s: %s", symbol, e)
        return None


def _fetch_yahoo_via_yfinance(symbol: str) -> Optional[list[dict]]:
    """Try yfinance if available."""
    try:
        import yfinance as yf  # type: ignore
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="6mo", interval="1d")
        if hist.empty:
            return None
        observations = []
        for idx, row in hist.iterrows():
            dt = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]
            close = row.get("Close")
            if close is not None:
                observations.append({"date": dt, "close": float(close)})
        observations.sort(key=lambda x: x["date"], reverse=True)
        return observations
    except Exception as e:
        logger.debug("yfinance fetch error for %s: %s", symbol, e)
        return None


def _fetch_yahoo(symbol: str) -> Optional[list[dict]]:
    """Fetch from Yahoo: tries yfinance first, then raw API."""
    cache_key = f"yahoo:{symbol}"
    if cache_key in _cache:
        ts, val = _cache[cache_key]
        if time.time() - ts < CACHE_TTL:
            return val

    result = _fetch_yahoo_via_yfinance(symbol)
    if result is None:
        result = _fetch_yahoo_raw(symbol)

    if result is not None:
        _cache[cache_key] = (time.time(), result)
    return result


def _yahoo_last_close(symbol: str) -> Optional[float]:
    """Return the most recent close for a Yahoo symbol."""
    obs = _fetch_yahoo(symbol)
    if obs:
        return obs[0]["close"]
    return None


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------

def _load_cb_state() -> dict:
    return _load_json(CB_PATH)


def _save_cb_state(state: dict) -> None:
    _save_json(CB_PATH, state)


def _record_failure(source: str) -> dict:
    """Record a failure timestamp. Returns updated state."""
    state = _load_cb_state()
    now = datetime.now(timezone.utc)
    failures = state.get("failures", [])
    failures.append({"source": source, "timestamp": now.isoformat()})
    # Keep only last 1 hour
    cutoff = now - timedelta(hours=1)
    failures = [
        f for f in failures
        if datetime.fromisoformat(f["timestamp"].replace("Z", "+00:00")) >= cutoff
    ]
    state["failures"] = failures
    _save_cb_state(state)
    return state


def _check_trip_circuit_breaker() -> bool:
    """Return True if we should trip the breaker (3 failures within 1h)."""
    state = _load_cb_state()
    if state.get("status") == "OPEN":
        return True
    failures = state.get("failures", [])
    if len(failures) >= 3:
        now = _now_iso()
        state["status"] = "OPEN"
        state["reason"] = "dual_source_failure"
        state["opened_at"] = now
        # circuit_breaker_aggregator.py compatible fields
        state["active"] = True
        state["level"] = "RED"
        state["timestamp"] = now
        _save_cb_state(state)
        logger.warning("Macro circuit breaker OPENED after %d failures", len(failures))
        return True
    return False


def clear_macro_circuit_breaker() -> dict:
    """Clear the macro circuit breaker and return the reset state."""
    now = _now_iso()
    state = {
        "status": "CLOSED",
        "failures": [],
        "cleared_at": now,
        # circuit_breaker_aggregator.py compatible fields
        "active": False,
        "level": "GREEN",
        "reason": None,
        "timestamp": now,
    }
    _save_cb_state(state)
    logger.info("Macro circuit breaker cleared")
    return state


# ---------------------------------------------------------------------------
# Data fetching with failover
# ---------------------------------------------------------------------------

def _fetch_yield_curve_10y2y() -> tuple[Optional[float], str]:
    """Return (value, source) for 10Y-2Y spread."""
    # Primary: FRED T10Y2Y
    fred_obs = _fred_get("T10Y2Y", limit=10)
    if fred_obs:
        return round(fred_obs[0]["value"], 3), "FRED"

    # Fallback: Yahoo reconstruction (10Y - 2Y futures implied yield)
    y_10y = _yahoo_last_close(YAHOO_10Y)
    y_2y_fut = _yahoo_last_close(YAHOO_2Y_FUT)
    if y_10y is not None and y_2y_fut is not None:
        y_2y = 100.0 - y_2y_fut  # treasury futures price -> yield
        spread = round(y_10y - y_2y, 3)
        return spread, "YAHOO_FALLBACK"

    return None, ""


def _fetch_yield_curve_10y3m() -> tuple[Optional[float], str]:
    """Return (value, source) for 10Y-3M spread."""
    # Primary: FRED T10Y3M
    fred_obs = _fred_get("T10Y3M", limit=10)
    if fred_obs:
        return round(fred_obs[0]["value"], 3), "FRED"

    # Fallback: Yahoo reconstruction (10Y - 3M bill)
    y_10y = _yahoo_last_close(YAHOO_10Y)
    y_3m = _yahoo_last_close(YAHOO_3M)
    if y_10y is not None and y_3m is not None:
        spread = round(y_10y - y_3m, 3)
        return spread, "YAHOO_FALLBACK"

    return None, ""


def _fetch_fed_funds_rate() -> tuple[Optional[float], Optional[float], str]:
    """Return (current_rate, rate_90d_change, source)."""
    # Primary: FRED DFF
    fred_obs = _fred_get("DFF", limit=120)
    if fred_obs:
        current = fred_obs[0]["value"]
        # Look back ~90 days (FRED DFF is daily)
        idx_90 = min(90, len(fred_obs) - 1)
        prior = fred_obs[idx_90]["value"] if idx_90 < len(fred_obs) else current
        change = round(current - prior, 3)
        return round(current, 3), change, "FRED"

    # Fallback: Yahoo SOFR futures or 3M bill
    sofr = _yahoo_last_close(YAHOO_SOFR)
    if sofr is not None:
        rate = round(100.0 - sofr, 3)
        # We don't have 90-day history easily without another fetch;
        # approximate change from 3M bill as a proxy for recent trend
        y_3m = _yahoo_last_close(YAHOO_3M)
        change = round(rate - (y_3m if y_3m is not None else rate), 3)
        return rate, change, "YAHOO_FALLBACK"

    y_3m = _yahoo_last_close(YAHOO_3M)
    if y_3m is not None:
        # No 90d change available from single point
        return round(y_3m, 3), 0.0, "YAHOO_FALLBACK"

    return None, None, ""


# ---------------------------------------------------------------------------
# Macro risk score computation
# ---------------------------------------------------------------------------

def _compute_macro_risk_score(
    t10y2y: Optional[float],
    t10y3m: Optional[float],
    dff: Optional[float],
    dff_change_90d: Optional[float],
) -> tuple[float, str]:
    """
    Compute macro_risk_score from -1.0 (very risk-off) to +1.0 (very risk-on)
    and a regime label.
    """
    score = 0.0
    factors = 0

    # Yield curve inversion signal
    spread = t10y2y if t10y2y is not None else t10y3m
    if spread is not None:
        if spread < 0:
            score -= 0.6
            factors += 1
        elif spread < 0.5:
            score -= 0.3
            factors += 1
        elif spread > 1.5:
            score += 0.3
            factors += 1

    # Fed funds tightening signal
    if dff_change_90d is not None:
        if dff_change_90d > 0.75:  # > 75bps hike over 90d
            score -= 0.4
            factors += 1
        elif dff_change_90d < -0.50:  # > 50bps cut over 90d
            score += 0.3
            factors += 1

    # Absolute rate level (very high = restrictive)
    if dff is not None and dff > 5.5:
        score -= 0.2
        factors += 1
    elif dff is not None and dff < 2.0:
        score += 0.2
        factors += 1

    # Normalize to [-1, 1]
    if factors > 0:
        score = max(-1.0, min(1.0, score))
    else:
        score = 0.0

    if score <= -0.6:
        label = "RISK_OFF"
    elif score <= -0.3:
        label = "NEUTRAL"
    elif t10y2y is not None and t10y2y < 0:
        label = "INVERSION"
    elif score >= 0.5:
        label = "RISK_ON"
    else:
        label = "NEUTRAL"

    return round(score, 3), label


def _build_by_asset_class(score: float, regime_label: str) -> dict[str, dict]:
    """Build per-asset-class overlay recommendations."""
    asset_classes = ["CRYPTO", "EQUITY", "FOREX", "COMMODITY", "ETF", "BOND"]
    result: dict[str, dict] = {}

    for ac in asset_classes:
        if regime_label == "RISK_OFF":
            if ac in ("BOND", "FOREX"):
                rec = "INCREASE"
                os_score = 0.15
            elif ac == "EQUITY":
                rec = "REDUCE"
                os_score = -0.30
            else:
                rec = "REDUCE"
                os_score = -0.20
        elif regime_label == "RISK_ON":
            if ac in ("CRYPTO", "EQUITY", "ETF"):
                rec = "INCREASE"
                os_score = 0.20
            elif ac == "COMMODITY":
                rec = "INCREASE"
                os_score = 0.10
            else:
                rec = "NEUTRAL"
                os_score = 0.0
        elif regime_label == "INVERSION":
            if ac in ("BOND", "FOREX"):
                rec = "INCREASE"
                os_score = 0.10
            elif ac == "EQUITY":
                rec = "REDUCE"
                os_score = -0.25
            else:
                rec = "NEUTRAL"
                os_score = -0.05
        else:  # NEUTRAL
            rec = "NEUTRAL"
            os_score = 0.0

        result[ac] = {
            "overlay_score": round(os_score, 3),
            "recommendation": rec,
            "macro_score": round(score, 3),
        }

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_macro_pipeline() -> dict:
    """
    Run the full macro data pipeline with dual-source failover and circuit breaker.

    Returns:
        The written snapshot dict (version 2 schema).
    """
    # Check circuit breaker first
    cb_state = _load_cb_state()
    if cb_state.get("status") == "OPEN":
        logger.warning("Macro circuit breaker is OPEN; returning default signal")
        default = _build_default_snapshot()
        _save_json(SNAPSHOT_PATH, default)
        return default

    t10y2y, src_10y2y = _fetch_yield_curve_10y2y()
    t10y3m, src_10y3m = _fetch_yield_curve_10y3m()
    dff, dff_change, src_dff = _fetch_fed_funds_rate()

    sources = {src_10y2y, src_10y3m, src_dff}
    sources.discard("")

    # Determine overall source label
    if not sources:
        _record_failure("FRED")
        _record_failure("YAHOO")
        if _check_trip_circuit_breaker():
            default = _build_default_snapshot()
            _save_json(SNAPSHOT_PATH, default)
            return default
        # Not yet tripped — write a degraded snapshot
        degraded = _build_default_snapshot(reason="partial_failure")
        _save_json(SNAPSHOT_PATH, degraded)
        return degraded

    if "FRED" in sources:
        source_label = "FRED"
    else:
        source_label = "YAHOO_FALLBACK"

    score, regime_label = _compute_macro_risk_score(t10y2y, t10y3m, dff, dff_change)
    by_ac = _build_by_asset_class(score, regime_label)

    snapshot = {
        "version": 2,
        "as_of": _now_iso(),
        "source": source_label,
        "series": {
            "yield_curve_10y2y": t10y2y,
            "yield_curve_10y3m": t10y3m,
            "fed_funds_rate": dff,
            "fed_funds_rate_90d_change": dff_change,
            "macro_risk_score": score,
            "regime_label": regime_label,
        },
        "by_asset_class": by_ac,
    }

    _save_json(SNAPSHOT_PATH, snapshot)
    logger.info("Macro snapshot written: source=%s regime=%s score=%.2f", source_label, regime_label, score)
    return snapshot


def _build_default_snapshot(reason: str = "circuit_breaker_default") -> dict:
    """Build a safe neutral snapshot when circuit breaker is open."""
    return {
        "version": 2,
        "as_of": _now_iso(),
        "source": "CIRCUIT_BREAKER_DEFAULT",
        "series": {
            "yield_curve_10y2y": None,
            "yield_curve_10y3m": None,
            "fed_funds_rate": None,
            "fed_funds_rate_90d_change": None,
            "macro_risk_score": 0.0,
            "regime_label": "NEUTRAL",
        },
        "by_asset_class": _build_by_asset_class(0.0, "NEUTRAL"),
        "circuit_breaker_reason": reason,
    }


def get_macro_snapshot() -> dict:
    """Read the latest macro snapshot from disk."""
    return _load_json(SNAPSHOT_PATH)


if __name__ == "__main__":
    snap = run_macro_pipeline()
    print(json.dumps(snap, indent=2))
