"""Cross-asset regime features (SPX / VIX / DXY) — Task L feature source.

Purpose
-------
Provide a single, cheap entry point for the rest of the pipeline to ask
"what is the cross-asset risk regime right now?" without every caller
having to know how to reach yfinance or where caches live.

This module is a FEATURE SOURCE ONLY. It does NOT wire itself into
``audit_trail/quality_gates.py``, ``alpha_engine/scanner.py``, or the
dashboard. Gate thresholds / policy decisions are intentionally left
outside so they can be tuned (with user sign-off) in a follow-up PR.

Design notes
------------
- Reuses ``MACRO_TICKERS`` from ``alpha_engine.config`` so tickers stay
  in one place. SPY is used as the SPX proxy (it is what is already
  wired in ``alpha_engine/data/macro.py`` — adding ``^GSPC`` would be
  redundant and adds another yfinance call).
- Disk cache: ``alpha_engine/data/cross_asset_cache.json``. Default TTL
  is 1 hour — SPX/VIX/DXY are daily-to-intraday indicators, hitting
  yfinance on every scanner pass is wasteful.
- All errors are swallowed and the function falls back to the last
  known cache (even if stale) or an empty snapshot. Callers therefore
  never need a try/except around ``get_cross_asset_regime``.
- Stdlib + yfinance only. yfinance is already pinned in
  ``alpha_engine/requirements.txt``.

Public API
----------
- ``fetch_cross_asset_snapshot(force_refresh=False)`` -> dict
- ``compute_regime_flags(snapshot)`` -> dict
- ``get_cross_asset_regime(force_refresh=False)`` -> dict  (one-stop call)
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CACHE_PATH = os.path.join(_REPO_ROOT, "alpha_engine", "data", "cross_asset_cache.json")
_DEFAULT_TTL_SECONDS = 3600  # 1 hour

# VIX / DXY / SPX thresholds. These are regime-tag thresholds, NOT gate
# thresholds — they describe what the market is doing, not what we should
# do about it. Keep policy decisions in a separate wiring PR.
_VIX_ELEVATED = 25.0
_DXY_STRONG = 105.0
_SPX_TREND_FLAT_PCT = 0.5  # |5d pct change| < 0.5% -> flat


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_cache() -> dict[str, Any]:
    if not os.path.exists(_CACHE_PATH):
        return {}
    try:
        with open(_CACHE_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return raw if isinstance(raw, dict) else {}
    except (json.JSONDecodeError, OSError) as e:
        logger.debug("cross_asset_cache read failed: %s", e)
        return {}


def _write_cache(snapshot: dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
        with open(_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, sort_keys=True)
    except OSError as e:
        logger.debug("cross_asset_cache write failed: %s", e)


def _cache_is_fresh(snapshot: dict[str, Any], ttl_seconds: int) -> bool:
    ts = snapshot.get("fetched_at")
    if not ts:
        return False
    try:
        fetched = datetime.fromisoformat(ts)
        if fetched.tzinfo is None:
            fetched = fetched.replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    age = (datetime.now(timezone.utc) - fetched).total_seconds()
    return age < ttl_seconds


def _fetch_live_snapshot() -> dict[str, Any]:
    """Hit yfinance for SPY/VIX/DXY. Returns empty dict on any failure."""
    try:
        import yfinance as yf  # type: ignore
    except ImportError:
        logger.warning("yfinance not installed; cross_asset snapshot unavailable")
        return {}

    # Reuse existing ticker map where possible; fall back to literals.
    try:
        from alpha_engine import config as _cfg
        tickers_cfg = getattr(_cfg, "MACRO_TICKERS", {}) or {}
    except Exception:
        tickers_cfg = {}

    tickers = {
        "SPX": tickers_cfg.get("SPY", "SPY"),   # SPY as SPX proxy
        "VIX": tickers_cfg.get("VIX", "^VIX"),
        "DXY": tickers_cfg.get("DXY", "DX-Y.NYB"),
    }

    levels: dict[str, Optional[float]] = {}
    spx_5d_pct: Optional[float] = None

    for name, tk in tickers.items():
        try:
            hist = yf.download(
                tk,
                period="10d",
                interval="1d",
                progress=False,
                auto_adjust=False,
            )
            if hist is None or hist.empty:
                levels[name] = None
                continue
            closes = hist["Adj Close"] if "Adj Close" in hist.columns else hist["Close"]
            # closes may be a DataFrame if yfinance returned MultiIndex — flatten.
            try:
                closes = closes.squeeze()
            except Exception:
                pass
            last = float(closes.iloc[-1])
            levels[name] = last
            if name == "SPX" and len(closes) >= 6:
                prev = float(closes.iloc[-6])  # ~5 trading days back
                if prev:
                    spx_5d_pct = (last - prev) / prev * 100.0
        except Exception as e:
            logger.debug("yfinance fetch failed for %s (%s): %s", name, tk, e)
            levels[name] = None

    return {
        "fetched_at": _utc_now_iso(),
        "source": "yfinance",
        "tickers": tickers,
        "levels": levels,
        "spx_5d_pct": spx_5d_pct,
    }


def fetch_cross_asset_snapshot(
    force_refresh: bool = False,
    ttl_seconds: int = _DEFAULT_TTL_SECONDS,
) -> dict[str, Any]:
    """Return a cross-asset snapshot dict, hitting cache when possible.

    Shape::

        {
          "fetched_at": "2026-04-11T18:05:00+00:00",
          "source": "yfinance" | "cache" | "stale_cache",
          "tickers": {"SPX": "SPY", "VIX": "^VIX", "DXY": "DX-Y.NYB"},
          "levels":  {"SPX": 512.34, "VIX": 17.2, "DXY": 104.8},
          "spx_5d_pct": 1.25
        }

    Never raises. On any failure returns an empty dict (or stale cache
    if one exists) so callers can rely on a dict shape.
    """
    if not force_refresh:
        cached = _read_cache()
        if cached and _cache_is_fresh(cached, ttl_seconds):
            cached["source"] = "cache"
            return cached

    live = _fetch_live_snapshot()
    if live and any(v is not None for v in (live.get("levels") or {}).values()):
        _write_cache(live)
        return live

    # Live fetch empty/failed: fall back to stale cache if present.
    stale = _read_cache()
    if stale:
        stale["source"] = "stale_cache"
        return stale
    return {}


def compute_regime_flags(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Derive coarse regime flags from a snapshot.

    Returned dict keys (all optional — missing input data means key is
    omitted or set to ``None``):

    - ``risk_on`` (bool): VIX below elevated AND SPX 5d trend up
    - ``vix_elevated`` (bool): VIX > 25
    - ``dxy_strong`` (bool): DXY > 105
    - ``spx_trend_5d`` (str): "up" | "down" | "flat"
    - ``vix`` / ``dxy`` / ``spx`` (float|None): raw levels for convenience
    - ``as_of`` (str): snapshot fetched_at
    - ``source`` (str): snapshot source
    """
    out: dict[str, Any] = {
        "as_of": snapshot.get("fetched_at"),
        "source": snapshot.get("source"),
        "risk_on": None,
        "vix_elevated": None,
        "dxy_strong": None,
        "spx_trend_5d": None,
        "vix": None,
        "dxy": None,
        "spx": None,
    }
    levels = snapshot.get("levels") or {}
    vix = levels.get("VIX")
    dxy = levels.get("DXY")
    spx = levels.get("SPX")
    spx_5d_pct = snapshot.get("spx_5d_pct")

    out["vix"] = vix
    out["dxy"] = dxy
    out["spx"] = spx

    if isinstance(vix, (int, float)):
        out["vix_elevated"] = bool(vix > _VIX_ELEVATED)
    if isinstance(dxy, (int, float)):
        out["dxy_strong"] = bool(dxy > _DXY_STRONG)
    if isinstance(spx_5d_pct, (int, float)):
        if spx_5d_pct > _SPX_TREND_FLAT_PCT:
            out["spx_trend_5d"] = "up"
        elif spx_5d_pct < -_SPX_TREND_FLAT_PCT:
            out["spx_trend_5d"] = "down"
        else:
            out["spx_trend_5d"] = "flat"

    # risk_on: need both VIX and SPX trend to decide; otherwise leave None
    if out["vix_elevated"] is not None and out["spx_trend_5d"] is not None:
        out["risk_on"] = (not out["vix_elevated"]) and out["spx_trend_5d"] == "up"

    return out


def get_cross_asset_regime(force_refresh: bool = False) -> dict[str, Any]:
    """One-stop call: fetch (cached) snapshot + compute regime flags.

    Example::

        from alpha_engine.cross_asset_features import get_cross_asset_regime
        regime = get_cross_asset_regime()
        if regime.get("vix_elevated"):
            ...  # caller decides policy
    """
    snap = fetch_cross_asset_snapshot(force_refresh=force_refresh)
    return compute_regime_flags(snap)


# ---------------------------------------------------------------------------
# Self-test — run with: python -m alpha_engine.cross_asset_features
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import pprint

    print("=== compute_regime_flags on synthetic snapshots ===")
    synthetic_cases = [
        {
            "name": "calm risk-on",
            "snap": {
                "fetched_at": _utc_now_iso(),
                "source": "synthetic",
                "levels": {"SPX": 520.0, "VIX": 14.0, "DXY": 103.5},
                "spx_5d_pct": 1.8,
            },
        },
        {
            "name": "stormy risk-off",
            "snap": {
                "fetched_at": _utc_now_iso(),
                "source": "synthetic",
                "levels": {"SPX": 480.0, "VIX": 32.0, "DXY": 107.2},
                "spx_5d_pct": -3.1,
            },
        },
        {
            "name": "flat / missing VIX",
            "snap": {
                "fetched_at": _utc_now_iso(),
                "source": "synthetic",
                "levels": {"SPX": 500.0, "VIX": None, "DXY": 104.0},
                "spx_5d_pct": 0.1,
            },
        },
    ]
    for case in synthetic_cases:
        print(f"\n-- {case['name']} --")
        pprint.pp(compute_regime_flags(case["snap"]))

    print("\n=== live fetch (yfinance; may be slow / offline-tolerant) ===")
    try:
        live_regime = get_cross_asset_regime()
        pprint.pp(live_regime)
    except Exception as exc:
        print(f"live fetch raised (unexpected; should fail-open): {exc}")
