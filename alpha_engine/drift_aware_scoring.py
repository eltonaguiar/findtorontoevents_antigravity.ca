"""
Drift-aware scoring multiplier.

Auto-halve (or scale 0.5..1.0) Smart Scores when a source_system's recent
forward win-rate has drifted below its longer-horizon baseline. Idea: if a
source was a 55% winner over 100+ trades but the last 30 days are 35%, we
should down-weight its picks until the forward window recovers, even if the
underlying components in calculate_smart_score still look healthy.

Public API
----------
- ``compute_drift_factor(source_system: str, *, force_refresh=False) -> float``
    Return a multiplier in [0.5, 1.0]. 1.0 = no drift; 0.5 = max conservatism.
- ``apply_drift_aware_multiplier(raw_score: float, source_system: str) -> float``
    Convenience wrapper around ``compute_drift_factor``. Multiplies and clamps.
- ``detect_simple_drift(source_history) -> dict``
    Stateless helper: given a list of closed picks for ONE source, computes
    baseline_wr (older window) and recent_wr (recent window) and returns
    drift severity. Used by tests and by the cache loader.
- ``apply_drift_conservatism(payload, severity) -> dict``
    Back-compat shim referenced by reports/HEDGE_LIBS_LEVERAGE_AUDIT_2026_04_22.md.
    Scales ``payload['confidence']`` by the drift factor for the given severity.

Caching
-------
``compute_drift_factor`` reads ``audit_dashboard/data/dashboard_data.json`` ONCE
per process and memoizes the per-source factor. This avoids the N^2 disk-read
risk noted in the wiring task. Use ``force_refresh=True`` from tests to reset.

Edge cases (documented in module docstring intentionally)
----------------------------------------------------------
- Cold start / file missing / parse error -> empty cache; every source gets 1.0.
- Source has no history at all -> 1.0 (innocent until proven drifting).
- Source has < ``MIN_RECENT_TRADES`` recent closed picks -> 1.0 (signal too noisy).
- Recent WR >= baseline WR or drop < ``DRIFT_THRESHOLD_PP`` -> 1.0.
- Drop >= ``HARD_DRIFT_THRESHOLD_PP`` -> 0.5 (halve, per the audit recommendation).
- Drop in (DRIFT_THRESHOLD_PP, HARD_DRIFT_THRESHOLD_PP) -> linear scale 1.0 -> 0.5.
"""

from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

# -- Tunables (conservative defaults; see PR body for rationale) --------------
DRIFT_THRESHOLD_PP = 15.0  # pp drop below baseline that starts the haircut
HARD_DRIFT_THRESHOLD_PP = 30.0  # pp drop at which we apply the full 0.5 floor
MIN_RECENT_TRADES = 10  # below this many recent closes we skip (too noisy)
MIN_BASELINE_TRADES = 30  # below this many baseline closes we skip
RECENT_WINDOW_DAYS = 30
BASELINE_WINDOW_DAYS = 180  # baseline = trades older than recent window, capped here
MIN_FACTOR = 0.5
MAX_FACTOR = 1.0

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
_DEFAULT_DASHBOARD_DATA = os.path.join(
    _REPO_ROOT, "audit_dashboard", "data", "dashboard_data.json"
)

# Memoized snapshot: maps lowercased source_system -> factor in [0.5, 1.0]
_DRIFT_FACTOR_CACHE: Optional[Dict[str, float]] = None


def _winning(pick: Dict[str, Any]) -> Optional[bool]:
    """Best-effort 'did this closed pick win?' classifier matching dashboard semantics."""
    status = str(pick.get("status", "") or "").upper()
    if status in {"WON", "WIN", "PROFIT", "TP_HIT", "TARGET", "TARGET_HIT"}:
        return True
    if status in {"LOST", "LOSS", "SL_HIT", "STOP", "STOPPED_OUT", "FAILED"}:
        return False
    # Fall back to pnl_pct if status is ambiguous (e.g. EXPIRED/CLOSED).
    pnl = pick.get("pnl_pct")
    if pnl is None:
        pnl = pick.get("pnl")
    try:
        pnl_f = float(pnl)
    except (TypeError, ValueError):
        return None
    if pnl_f > 0:
        return True
    if pnl_f < 0:
        return False
    return None  # exactly zero -> ambiguous (FLAT_CLOSE_BUG territory; skip)


def _parse_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    s = str(value).strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def detect_simple_drift(
    source_history: Iterable[Dict[str, Any]],
    *,
    now: Optional[datetime] = None,
    recent_days: int = RECENT_WINDOW_DAYS,
    baseline_days: int = BASELINE_WINDOW_DAYS,
    min_recent: int = MIN_RECENT_TRADES,
    min_baseline: int = MIN_BASELINE_TRADES,
) -> Dict[str, Any]:
    """Compute baseline vs recent WR for a single source's closed picks.

    Returns a dict ``{baseline_wr, recent_wr, drop_pp, recent_n, baseline_n,
    severity}`` where severity is in [0.0, 1.0]: 0.0 means 'no drift signal',
    1.0 means 'fully drifted, halve the score'. Linear ramp between
    ``DRIFT_THRESHOLD_PP`` and ``HARD_DRIFT_THRESHOLD_PP``.
    """
    now = now or datetime.now(timezone.utc)
    recent_cutoff = now - timedelta(days=recent_days)
    baseline_cutoff = now - timedelta(days=baseline_days)

    recent_outcomes: List[bool] = []
    baseline_outcomes: List[bool] = []
    for pick in source_history:
        won = _winning(pick)
        if won is None:
            continue
        ts = _parse_dt(pick.get("closed_at") or pick.get("timestamp"))
        if ts is None:
            continue
        if ts >= recent_cutoff:
            recent_outcomes.append(won)
        elif ts >= baseline_cutoff:
            baseline_outcomes.append(won)

    out: Dict[str, Any] = {
        "baseline_wr": None,
        "recent_wr": None,
        "drop_pp": 0.0,
        "recent_n": len(recent_outcomes),
        "baseline_n": len(baseline_outcomes),
        "severity": 0.0,
    }
    if len(recent_outcomes) < min_recent or len(baseline_outcomes) < min_baseline:
        return out

    base_wr = sum(baseline_outcomes) / len(baseline_outcomes)
    recent_wr = sum(recent_outcomes) / len(recent_outcomes)
    drop_pp = (base_wr - recent_wr) * 100.0
    out["baseline_wr"] = base_wr
    out["recent_wr"] = recent_wr
    out["drop_pp"] = drop_pp

    if drop_pp <= DRIFT_THRESHOLD_PP:
        out["severity"] = 0.0
    elif drop_pp >= HARD_DRIFT_THRESHOLD_PP:
        out["severity"] = 1.0
    else:
        span = HARD_DRIFT_THRESHOLD_PP - DRIFT_THRESHOLD_PP
        out["severity"] = max(0.0, min(1.0, (drop_pp - DRIFT_THRESHOLD_PP) / span))
    return out


def _severity_to_factor(severity: float) -> float:
    severity = max(0.0, min(1.0, float(severity)))
    return MAX_FACTOR - (MAX_FACTOR - MIN_FACTOR) * severity


def apply_drift_conservatism(
    payload: Dict[str, Any], severity: float
) -> Dict[str, Any]:
    """Back-compat shim: scale ``payload['confidence']`` by the drift factor.

    Referenced by reports/HEDGE_LIBS_LEVERAGE_AUDIT_2026_04_22.md. Returns a new
    dict (does not mutate input).
    """
    factor = _severity_to_factor(severity)
    out = dict(payload)
    if "confidence" in out:
        try:
            out["confidence"] = float(out["confidence"]) * factor
        except (TypeError, ValueError):
            pass
    out["_drift_factor"] = factor
    return out


def _build_factor_cache(
    dashboard_data_path: str = _DEFAULT_DASHBOARD_DATA,
) -> Dict[str, float]:
    """One-shot snapshot: per-source drift factor in [0.5, 1.0]."""
    factors: Dict[str, float] = {}
    if not os.path.isfile(dashboard_data_path):
        logger.debug("drift_aware_scoring: %s missing; cache empty", dashboard_data_path)
        return factors
    try:
        with open(dashboard_data_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("drift_aware_scoring: cannot load dashboard data (%s)", exc)
        return factors

    recent_closed = (data.get("picks") or {}).get("recent_closed") or []
    if not isinstance(recent_closed, list):
        return factors

    by_source: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for pick in recent_closed:
        if not isinstance(pick, dict):
            continue
        src = str(pick.get("source_system") or pick.get("source") or "").strip().lower()
        if not src:
            continue
        by_source[src].append(pick)

    for src, hist in by_source.items():
        snap = detect_simple_drift(hist)
        factor = _severity_to_factor(snap["severity"])
        if factor < MAX_FACTOR:
            factors[src] = factor
    return factors


def _ensure_cache(force_refresh: bool = False) -> Dict[str, float]:
    global _DRIFT_FACTOR_CACHE
    if _DRIFT_FACTOR_CACHE is None or force_refresh:
        _DRIFT_FACTOR_CACHE = _build_factor_cache()
    return _DRIFT_FACTOR_CACHE


def reset_cache() -> None:
    """Test hook: clear the memoized snapshot."""
    global _DRIFT_FACTOR_CACHE
    _DRIFT_FACTOR_CACHE = None


def set_cache_for_testing(factors: Dict[str, float]) -> None:
    """Test hook: install a synthetic per-source factor map."""
    global _DRIFT_FACTOR_CACHE
    _DRIFT_FACTOR_CACHE = {k.lower(): float(v) for k, v in factors.items()}


def compute_drift_factor(source_system: Optional[str], *, force_refresh: bool = False) -> float:
    """Return the multiplier in [0.5, 1.0] for ``source_system``.

    No source / unknown source -> 1.0. The cache is built on first call.
    """
    if not source_system:
        return MAX_FACTOR
    cache = _ensure_cache(force_refresh=force_refresh)
    src = str(source_system).strip().lower()
    if not src:
        return MAX_FACTOR
    return float(cache.get(src, MAX_FACTOR))


def apply_drift_aware_multiplier(raw_score: float, source_system: Optional[str]) -> float:
    """Multiply ``raw_score`` by the drift factor for ``source_system`` and clamp."""
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        return 0.0
    factor = compute_drift_factor(source_system)
    out = score * factor
    # Match calculate_smart_score's clamp range
    return round(max(0.0, min(out, 100.0)), 1)


__all__ = [
    "DRIFT_THRESHOLD_PP",
    "HARD_DRIFT_THRESHOLD_PP",
    "MIN_RECENT_TRADES",
    "MIN_BASELINE_TRADES",
    "MIN_FACTOR",
    "MAX_FACTOR",
    "detect_simple_drift",
    "apply_drift_conservatism",
    "compute_drift_factor",
    "apply_drift_aware_multiplier",
    "reset_cache",
    "set_cache_for_testing",
]
