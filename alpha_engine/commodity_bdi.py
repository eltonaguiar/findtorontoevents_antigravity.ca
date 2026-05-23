"""IDEA-A factor: Baltic Dry Index Momentum for COMMODITY picks.

Swarm research 2026-05-19: BDI (FRED series BDIY) 7-day ROC captures
dry-bulk shipping demand, a leading indicator for base metals and energy
commodities (DBB, USO, UNG). Does NOT apply to soft commodities (CT=F,
DBA) — those are driven by crop conditions, not shipping rates.

Score mapping (BDI 7-day ROC):
  ROC > +5%           → score 75-90 (supply tightening, bullish)
  ROC  0% to +5%      → score 55-75 (mild positive)
  ROC -5% to  0%      → score 40-55 (mild negative)
  ROC < -5%           → score 10-40 (supply glut, bearish)

Fail-open: returns 50.0 on any fetch/parse failure so it never blocks picks.
Cache: in-process 60-minute TTL (module-level dict).

Functions:
  bdi_score(lookback_days=7) -> float   -- 0-100, fail-open 50.0
  stamp_pick(pick: dict) -> dict        -- stamps bdi_momentum_score on
                                           COMMODITY picks only (skips CT=F,DBA)
"""
from __future__ import annotations

import math
import os
import time
from typing import Any

# In-process cache: {"bdi": (timestamp, score)}
_bdi_cache: dict[str, tuple[float, float]] = {}
CACHE_TTL_S = 3600  # 60 minutes

# Soft-commodity symbols that BDI does NOT apply to
_BDI_SKIP_SYMBOLS: frozenset[str] = frozenset({"CT=F", "DBA"})


def _read_fred_key() -> str | None:
    """Read FRED_API_KEY from env, then Windows registry fallback."""
    key = os.environ.get("FRED_API_KEY")
    if key:
        return key
    try:
        import winreg  # type: ignore[import]
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as reg:
            key, _ = winreg.QueryValueEx(reg, "FRED_API_KEY")
            return key if key else None
    except Exception:
        return None


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def _roc_to_score(roc: float) -> float:
    """Map BDI 7-day ROC (as a fraction, e.g. 0.05 = +5%) to [0, 100]."""
    roc_pct = roc * 100.0
    if roc_pct > 5.0:
        # 75-90 range: linear scale within > +5%
        # cap at +20% → 90
        capped = min(roc_pct, 20.0)
        score = 75.0 + (capped - 5.0) / 15.0 * 15.0
        return round(min(90.0, score), 2)
    elif roc_pct >= 0.0:
        # 55-75 range: linear 0% → 55, +5% → 75
        score = 55.0 + roc_pct / 5.0 * 20.0
        return round(score, 2)
    elif roc_pct >= -5.0:
        # 40-55 range: linear -5% → 40, 0% → 55
        score = 40.0 + (roc_pct + 5.0) / 5.0 * 15.0
        return round(score, 2)
    else:
        # 10-40 range: linear -5% → 40, cap at -20% → 10
        capped = max(roc_pct, -20.0)
        score = 40.0 + (capped + 5.0) / 15.0 * 30.0
        return round(max(10.0, score), 2)


def _fetch_bdi_roc(lookback_days: int = 7) -> float:
    """Fetch BDIY from FRED and compute lookback_days ROC. Returns ROC as
    a fraction (0.05 = +5%). Returns None on any failure."""
    fred_key = _read_fred_key()
    if not fred_key:
        return None  # type: ignore[return-value]

    url = (
        f"https://api.stlouisfed.org/fred/series/observations"
        f"?series_id=BDIY&api_key={fred_key}&file_type=json"
        f"&sort_order=desc&limit={lookback_days + 10}"
    )
    try:
        import urllib.request
        import json
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        observations = data.get("observations", [])
        # Filter out missing/non-numeric values, newest first (sort_order=desc)
        values: list[float] = []
        for obs in observations:
            val_str = obs.get("value", ".")
            if val_str == ".":
                continue
            try:
                values.append(float(val_str))
            except (TypeError, ValueError):
                continue
        if len(values) < 2:
            return None  # type: ignore[return-value]
        # values[0] = most recent, values[-1] = oldest in window
        newest = values[0]
        oldest = values[min(lookback_days - 1, len(values) - 1)]
        if oldest == 0.0:
            return None  # type: ignore[return-value]
        return (newest - oldest) / abs(oldest)
    except Exception:
        return None  # type: ignore[return-value]


def bdi_score(lookback_days: int = 7) -> float:
    """Return Baltic Dry Index 7-day ROC score in [0, 100].

    Fail-open: returns 50.0 on any network/parse/key failure.
    Cached in-process for 60 minutes.
    """
    now = time.time()
    cached = _bdi_cache.get("bdi")
    if cached and now - cached[0] < CACHE_TTL_S:
        return cached[1]

    try:
        roc = _fetch_bdi_roc(lookback_days)
        if roc is None:
            return 50.0
        score = _roc_to_score(roc)
        _bdi_cache["bdi"] = (now, score)
        return score
    except Exception:
        return 50.0


def stamp_pick(pick: dict, lookback_days: int = 7) -> dict:
    """Stamp bdi_momentum_score on COMMODITY picks in-place.

    Skips:
      - Non-COMMODITY asset classes
      - CT=F and DBA (soft commodities not driven by BDI)

    Returns the pick dict for chaining. Fail-open: pick unchanged on error.
    """
    try:
        asset_class = str(pick.get("asset_class", "")).upper()
        if asset_class != "COMMODITY":
            return pick
        symbol = str(pick.get("symbol", ""))
        if symbol in _BDI_SKIP_SYMBOLS:
            return pick
        pick["bdi_momentum_score"] = bdi_score(lookback_days)
    except Exception:
        pass
    return pick
