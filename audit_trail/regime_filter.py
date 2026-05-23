"""
B13 — per-asset-class regime filter sidecar (default-OFF).

Environment flags (all default-OFF):
    REGIME_FILTER_ENABLED         = "0"   master switch
    REGIME_FILTER_CRYPTO_ENABLED  = "0"   CRYPTO sub-gate
    REGIME_FILTER_LOG_ONLY        = "1"   shadow mode: log, don't block

Reads regime from alpha_engine/data/regime_report.json.
Stale (>24h), missing, or unreadable → permissive (None returned).
Any exception → permissive.

Returns None if the pick is allowed, or a reason string if blocked.
All blocking is guarded by REGIME_FILTER_LOG_ONLY; when log-only is on
the function always returns None but logs the would-be rejection.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_REGIME_REPORT_PATH = Path(__file__).parent.parent / "alpha_engine" / "data" / "regime_report.json"
_STALENESS_HOURS = 24

# CRYPTO allow matrix.  Non-CRYPTO classes are permissive stubs pending
# per-class regime enrichment (only CRYPTO has confirmed regime-edge correlation).
_ALLOW_MATRIX: Dict[str, Dict[str, Dict[str, bool]]] = {
    "CRYPTO": {
        "BULL":    {"LONG": True,  "SHORT": False},
        "BEAR":    {"LONG": False, "SHORT": True},
        "CHOPPY":  {"LONG": True,  "SHORT": True},
        "RANGING": {"LONG": True,  "SHORT": True},
        "NEUTRAL": {"LONG": True,  "SHORT": True},
    },
    "FOREX":     {r: {"LONG": True, "SHORT": True} for r in ("BULL", "BEAR", "CHOPPY", "RANGING", "NEUTRAL")},
    "EQUITY":    {r: {"LONG": True, "SHORT": True} for r in ("BULL", "BEAR", "CHOPPY", "RANGING", "NEUTRAL")},
    "COMMODITY": {r: {"LONG": True, "SHORT": True} for r in ("BULL", "BEAR", "CHOPPY", "RANGING", "NEUTRAL")},
    "FUTURES":   {r: {"LONG": True, "SHORT": True} for r in ("BULL", "BEAR", "CHOPPY", "RANGING", "NEUTRAL")},
    "ETF":       {r: {"LONG": True, "SHORT": True} for r in ("BULL", "BEAR", "CHOPPY", "RANGING", "NEUTRAL")},
    "BOND":      {r: {"LONG": True, "SHORT": True} for r in ("BULL", "BEAR", "CHOPPY", "RANGING", "NEUTRAL")},
}


def _load_regime() -> Optional[str]:
    """Return current regime string or None if stale/missing/unreadable."""
    try:
        if not _REGIME_REPORT_PATH.exists():
            logger.debug("regime_report.json not found — permissive")
            return None
        with open(_REGIME_REPORT_PATH) as fh:  # noqa: WPS515
            data: Dict[str, Any] = json.load(fh)
        # Use regime_last_checked if available (updated more frequently than timestamp)
        ts_str = data.get("regime_last_checked") or data.get("timestamp")
        if ts_str:
            ts = datetime.fromisoformat(ts_str)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) - ts > timedelta(hours=_STALENESS_HOURS):
                logger.debug("regime_report.json stale (>%dh) — permissive", _STALENESS_HOURS)
                return None
        regime = str(data.get("regime") or "").upper() or None
        if regime not in ("BULL", "BEAR", "CHOPPY", "RANGING", "NEUTRAL"):
            logger.debug("Unknown regime value %r — permissive", regime)
            return None
        return regime
    except Exception as exc:  # noqa: BLE001
        logger.debug("regime_report.json read error: %s — permissive", exc)
        return None


def _normalize_direction(pick: Dict[str, Any]) -> str:
    """Normalize pick direction to LONG/SHORT."""
    raw = str(pick.get("direction") or pick.get("signal_type") or "").upper()
    if raw in ("BUY",):
        return "LONG"
    if raw in ("SELL",):
        return "SHORT"
    return raw  # LONG / SHORT pass through unchanged


def passes_regime_filter(pick: Dict[str, Any]) -> Optional[str]:
    """
    Return None if pick passes the regime filter, or a reason string if blocked.

    Always returns None when:
    - REGIME_FILTER_ENABLED != "1"
    - REGIME_FILTER_LOG_ONLY == "1" (logs would-be rejections)
    - regime_report.json is missing, stale, or unreadable
    - asset class is not CRYPTO and CRYPTO sub-gate is the only active gate
    """
    if os.environ.get("REGIME_FILTER_ENABLED", "0") != "1":
        return None

    log_only = os.environ.get("REGIME_FILTER_LOG_ONLY", "1") == "1"
    asset_class = str(pick.get("asset_class") or "").upper()

    if asset_class == "CRYPTO":
        if os.environ.get("REGIME_FILTER_CRYPTO_ENABLED", "0") != "1":
            return None
    else:
        # Non-CRYPTO: permissive stubs — all allow-all, no blocking possible
        return None

    regime = _load_regime()
    if regime is None:
        return None  # stale / missing / unreadable → permissive

    direction = _normalize_direction(pick)
    if not direction:
        return None  # unknown direction → permissive

    class_matrix = _ALLOW_MATRIX.get(asset_class, {})
    regime_row = class_matrix.get(regime, {})
    allowed = regime_row.get(direction, True)  # default permissive

    if not allowed:
        reason = f"regime_filter: {asset_class} {direction} blocked in {regime} regime"
        if log_only:
            logger.info("[SHADOW] would-reject pick %s — %s", pick.get("id", "?"), reason)
            return None
        return reason

    return None
