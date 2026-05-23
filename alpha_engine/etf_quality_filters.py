"""ETF quality filters — opt-in PF-lift layer for the ETF asset class.

Two filters that collectively target PF 1.32 → 1.50+ while preserving WR:

Filter 1 — Relative Strength vs SPY (20-day outperformance gate)
    An ETF pick must show >= ETF_RS_THRESHOLD (default 2%) 20-day price
    outperformance vs SPY to qualify.  The threshold is configurable via
    ETF_RS_THRESHOLD env var.  Kill-switch: ETF_RS_FILTER_ENABLED=0 (default 1).
    Fail-open: if the pick's 20d_return field is missing, or SPY return cannot
    be read from the cached sidecar, the pick passes (True).

Filter 2 — Volume-Surge Confirmation
    An ETF pick must carry a volume_ratio field >= ETF_VOLUME_SURGE_MIN
    (default 1.3 — current volume / 20-day average volume).  Kill-switch:
    ETF_VOLUME_SURGE_ENABLED=0 (default 1).  Fail-open: if volume_ratio is
    absent the pick passes.

Wire-up (production caller):
    alpha_engine/smart_picks_engine.py :: score_pick()
    Applied after asset_class is resolved to "etf", before the scored dict
    is returned.  A failed filter sets score=0 and tags
    _etf_quality_filtered=True rather than raising an exception.

## Wiring Plan
Target file  : alpha_engine/smart_picks_engine.py
Target fn    : score_pick() — at the end, just before the final `return` dict
               that assembles the scored pick dict.
Mechanism    : try/except import; on filter rejection, zero the score and add
               tag rather than hard-blocking (fail-open), consistent with the
               volume_cap and per_class_trainer patterns already in the file.
Expected PR  : this PR (2026-05-16); wire-up committed in the same changeset.
"""

from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger("etf_quality_filters")

# ---------------------------------------------------------------------------
# Tuneable constants (override via env vars for A/B testing)
# ---------------------------------------------------------------------------
_DEFAULT_RS_THRESHOLD: float = 2.0   # percent: pick's 20d return must beat SPY by 2%+
_DEFAULT_VOLUME_SURGE: float = 1.3   # volume_ratio floor (current vol / 20d avg)


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


def _env_enabled(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if raw in ("0", "false", "off", "no"):
        return False
    if raw in ("1", "true", "on", "yes"):
        return True
    return default


# ---------------------------------------------------------------------------
# Public helpers — called from the wire-up in smart_picks_engine.score_pick()
# ---------------------------------------------------------------------------

def check_rs_filter(pick: dict[str, Any]) -> tuple[bool, str]:
    """Filter 1: 20-day outperformance vs SPY.

    Returns (passes: bool, reason: str).
    Fail-open on missing / unreadable data.

    Kill-switch: ETF_RS_FILTER_ENABLED=0   (default: enabled)
    Threshold  : ETF_RS_THRESHOLD (default: 2.0 — percentage points)

    The pick dict is expected to carry a ``return_20d`` or ``ret_20d`` field
    (float, fractional or percentage).  A cached SPY return is read from
    ``alpha_engine/data/spy_20d_return.json`` if present; otherwise the
    filter pass-through is triggered.
    """
    if not _env_enabled("ETF_RS_FILTER_ENABLED", default=True):
        return True, "etf_rs_filter disabled (kill-switch)"

    threshold = _env_float("ETF_RS_THRESHOLD", _DEFAULT_RS_THRESHOLD)

    # --- Extract the pick's 20-day return ---
    pick_ret = _coerce_return(
        pick.get("return_20d") or pick.get("ret_20d") or pick.get("20d_return")
    )
    if pick_ret is None:
        return True, "etf_rs_filter pass-through: pick 20d return unavailable"

    # --- Fetch cached SPY return ---
    spy_ret = _read_spy_return()
    if spy_ret is None:
        return True, "etf_rs_filter pass-through: SPY 20d return unavailable"

    outperformance = pick_ret - spy_ret  # both in pct-point space now
    if outperformance >= threshold:
        return True, (
            f"etf_rs_filter PASS: +{outperformance:.2f}pp vs SPY "
            f"(pick {pick_ret:.2f}% / SPY {spy_ret:.2f}%)"
        )
    return False, (
        f"etf_rs_filter FAIL: {outperformance:.2f}pp vs SPY "
        f"(pick {pick_ret:.2f}% / SPY {spy_ret:.2f}%, need >={threshold:.1f}pp)"
    )


def check_volume_surge(pick: dict[str, Any]) -> tuple[bool, str]:
    """Filter 2: Volume-surge confirmation.

    Returns (passes: bool, reason: str).
    Fail-open if ``volume_ratio`` (or ``vol_ratio``) is absent.

    Kill-switch: ETF_VOLUME_SURGE_ENABLED=0  (default: enabled)
    Floor      : ETF_VOLUME_SURGE_MIN         (default: 1.3)
    """
    if not _env_enabled("ETF_VOLUME_SURGE_ENABLED", default=True):
        return True, "etf_volume_surge disabled (kill-switch)"

    floor = _env_float("ETF_VOLUME_SURGE_MIN", _DEFAULT_VOLUME_SURGE)

    raw = pick.get("volume_ratio") or pick.get("vol_ratio") or pick.get("volume_surge")
    if raw is None:
        return True, "etf_volume_surge pass-through: volume_ratio field absent"

    try:
        ratio = float(raw)
    except (TypeError, ValueError):
        return True, "etf_volume_surge pass-through: volume_ratio not numeric"

    if ratio >= floor:
        return True, f"etf_volume_surge PASS: ratio {ratio:.2f} >= {floor:.2f}"
    return False, f"etf_volume_surge FAIL: ratio {ratio:.2f} < {floor:.2f}"


def apply_etf_quality_filters(pick: dict[str, Any], score: int) -> tuple[int, bool, list[str]]:
    """Apply both ETF quality filters; return (new_score, was_filtered, reasons).

    ``was_filtered=True`` means at least one filter rejected the pick.
    Score is zeroed on any rejection; all reasons are collected for logging.
    Never raises — wraps everything in try/except so a bug here cannot break
    production pick flow.
    """
    reasons: list[str] = []
    was_filtered = False
    new_score = score

    try:
        rs_pass, rs_reason = check_rs_filter(pick)
        reasons.append(rs_reason)
        if not rs_pass:
            was_filtered = True
            log.info("[etf_quality_filters] RS filter rejected %s: %s",
                     pick.get("symbol", "?"), rs_reason)
    except Exception as exc:
        reasons.append(f"etf_rs_filter error (pass-through): {exc}")
        log.warning("[etf_quality_filters] check_rs_filter exception: %s", exc)

    try:
        vol_pass, vol_reason = check_volume_surge(pick)
        reasons.append(vol_reason)
        if not vol_pass:
            was_filtered = True
            log.info("[etf_quality_filters] Volume-surge filter rejected %s: %s",
                     pick.get("symbol", "?"), vol_reason)
    except Exception as exc:
        reasons.append(f"etf_volume_surge error (pass-through): {exc}")
        log.warning("[etf_quality_filters] check_volume_surge exception: %s", exc)

    if was_filtered:
        new_score = 0

    return new_score, was_filtered, reasons


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _coerce_return(raw: Any) -> float | None:
    """Convert raw return value to percentage-point float, or None."""
    if raw is None:
        return None
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    # Fractional returns (abs < 2.0 and not obviously pct) → convert to pct
    if -2.0 < v < 2.0 and v != 0.0:
        v = v * 100.0
    return v


def _read_spy_return() -> float | None:
    """Read the cached SPY 20-day return (pct) from data sidecar, if present.

    Sidecar path: alpha_engine/data/spy_20d_return.json
    Expected schema: {"spy_20d_return_pct": <float>}

    Returns None on any error (triggers fail-open in caller).
    """
    import json
    import pathlib

    sidecar = (
        pathlib.Path(__file__).resolve().parent / "data" / "spy_20d_return.json"
    )
    if not sidecar.exists():
        return None
    try:
        with open(sidecar, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
        val = doc.get("spy_20d_return_pct")
        if val is None:
            return None
        return float(val)
    except Exception as exc:
        log.debug("[etf_quality_filters] _read_spy_return failed: %s", exc)
        return None
