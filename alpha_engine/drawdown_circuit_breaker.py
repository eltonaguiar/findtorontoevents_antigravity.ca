#!/usr/bin/env python3
"""
Drawdown Circuit Breaker — Real Money Portfolio Protection
============================================================
Per BACKTEST_4MONTH_ANALYSIS.md Q10 recommendation:
  "Add real-time drawdown circuit breaker: pause system if DD > 5% in 24h"

This module monitors the real money portfolio's equity history and
computes time-windowed drawdowns from peak equity. When thresholds are
breached, it writes a state file that scanners/trackers check before
opening new positions.

Thresholds:
  24h drawdown > 5%  -> CIRCUIT_BREAKER_ACTIVE   (pause new entries)
  48h drawdown > 10% -> CIRCUIT_BREAKER_CRITICAL  (pause + flag for review)

State file: alpha_engine/data/drawdown_circuit_breaker.json
Public API:  is_drawdown_breaker_active() -> bool

Stdlib only. Windows UTF-8 safe.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
PORTFOLIO_FILE = DATA / "real_money_portfolio.json"
PORTFOLIO_HISTORY = DATA / "real_money_history.json"
STATE_FILE = DATA / "drawdown_circuit_breaker.json"

# Thresholds (percentage drawdown from peak equity in window)
THRESHOLD_24H_PCT = 5.0    # 24h DD > 5% => ACTIVE
THRESHOLD_48H_PCT = 10.0   # 48h DD > 10% => CRITICAL

# Auto-recovery: breaker clears when equity recovers to within this % of peak
RECOVERY_BUFFER_PCT = 2.0  # Must recover to within 2% of peak to auto-clear


def _load_json(path: Path) -> Optional[dict | list]:
    """Load JSON file, return None on any error."""
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


def _save_json(path: Path, data: dict) -> None:
    """Save JSON file safely."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    except Exception as e:
        print(f"  [DRAWDOWN CB] Could not write {path.name}: {e}")


def _get_current_equity(portfolio: dict) -> float:
    """Extract current equity from portfolio state."""
    stats = portfolio.get("stats", {})
    return float(stats.get("current_equity", 10000.0))


def _get_peak_equity(portfolio: dict) -> float:
    """Extract peak equity from portfolio state."""
    stats = portfolio.get("stats", {})
    return float(stats.get("peak_equity", 10000.0))


def _compute_windowed_peak(history: list, hours: int) -> Optional[float]:
    """Find peak equity within the last N hours from history snapshots."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours)
    peak = None

    for snap in history:
        ts_str = snap.get("timestamp", "")
        if not ts_str:
            continue
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if ts >= cutoff:
                eq = float(snap.get("equity", 0))
                if eq > 0 and (peak is None or eq > peak):
                    peak = eq
        except (ValueError, TypeError):
            continue

    return peak


def check_drawdown_breaker(portfolio: Optional[dict] = None) -> dict:
    """
    Check real money portfolio drawdown against time-windowed thresholds.

    Args:
        portfolio: Optional pre-loaded portfolio dict. If None, loads from file.

    Returns:
        State dict with level, drawdowns, and metadata.
    """
    now = datetime.now(timezone.utc)

    # Load portfolio if not provided
    if portfolio is None:
        portfolio = _load_json(PORTFOLIO_FILE)
    if not portfolio:
        return _make_state("CLEAR", 0.0, 0.0, now, "No portfolio data")

    # Load history for windowed peak computation
    history = _load_json(PORTFOLIO_HISTORY) or []

    current_equity = _get_current_equity(portfolio)
    overall_peak = _get_peak_equity(portfolio)

    # Compute windowed peaks (fall back to overall peak if insufficient history)
    peak_24h = _compute_windowed_peak(history, 24) or overall_peak
    peak_48h = _compute_windowed_peak(history, 48) or overall_peak

    # Ensure peaks are at least the overall peak (history may be incomplete)
    peak_24h = max(peak_24h, current_equity)  # Can't have DD from below current
    peak_48h = max(peak_48h, current_equity)

    # Actually use the portfolio's tracked peak if it's higher
    peak_24h = max(peak_24h, overall_peak)
    peak_48h = max(peak_48h, overall_peak)

    # Compute drawdowns
    dd_24h = _compute_dd_pct(peak_24h, current_equity)
    dd_48h = _compute_dd_pct(peak_48h, current_equity)

    # Determine level
    triggers = []
    level = "CLEAR"

    if dd_48h >= THRESHOLD_48H_PCT:
        level = "CIRCUIT_BREAKER_CRITICAL"
        triggers.append(
            f"48h DD = {dd_48h:.2f}% exceeds {THRESHOLD_48H_PCT}% threshold"
        )

    if dd_24h >= THRESHOLD_24H_PCT:
        if level != "CIRCUIT_BREAKER_CRITICAL":
            level = "CIRCUIT_BREAKER_ACTIVE"
        triggers.append(
            f"24h DD = {dd_24h:.2f}% exceeds {THRESHOLD_24H_PCT}% threshold"
        )

    # Check for auto-recovery from previous breaker state
    existing_state = _load_json(STATE_FILE) or {}
    was_active = existing_state.get("level", "CLEAR") != "CLEAR"

    if was_active and level == "CLEAR":
        # Verify genuine recovery (within buffer of peak)
        dd_from_peak = _compute_dd_pct(overall_peak, current_equity)
        if dd_from_peak <= RECOVERY_BUFFER_PCT:
            triggers.append(
                f"Auto-recovered: DD from peak = {dd_from_peak:.2f}% "
                f"(within {RECOVERY_BUFFER_PCT}% buffer)"
            )
        else:
            # Still in drawdown but below threshold windows -- keep monitoring
            pass

    state = _make_state(level, dd_24h, dd_48h, now, ", ".join(triggers) if triggers else "All clear")
    state["peak_24h"] = round(peak_24h, 2)
    state["peak_48h"] = round(peak_48h, 2)
    state["current_equity"] = round(current_equity, 2)
    state["overall_peak"] = round(overall_peak, 2)
    state["history_snapshots_used"] = len(history)

    # Preserve activation timestamp from previous state
    if level != "CLEAR" and was_active:
        state["activated_at"] = existing_state.get("activated_at", now.isoformat())
    elif level != "CLEAR":
        state["activated_at"] = now.isoformat()

    # Save state
    _save_json(STATE_FILE, state)

    # Log
    if level == "CIRCUIT_BREAKER_CRITICAL":
        print(f"  [CIRCUIT BREAKER] 48h DD = {dd_48h:.2f}% exceeds "
              f"{THRESHOLD_48H_PCT}% threshold -- CRITICAL: new entries PAUSED, "
              f"manual review required")
    elif level == "CIRCUIT_BREAKER_ACTIVE":
        print(f"  [CIRCUIT BREAKER] 24h DD = {dd_24h:.2f}% exceeds "
              f"{THRESHOLD_24H_PCT}% threshold -- new entries PAUSED")
    else:
        print(f"  [CIRCUIT BREAKER] Drawdown OK: 24h={dd_24h:.2f}%, "
              f"48h={dd_48h:.2f}% (thresholds: {THRESHOLD_24H_PCT}%/{THRESHOLD_48H_PCT}%)")

    return state


def _compute_dd_pct(peak: float, current: float) -> float:
    """Compute drawdown percentage from peak. Returns 0+ (positive = drawdown)."""
    if peak <= 0:
        return 0.0
    dd = (peak - current) / peak * 100.0
    return max(0.0, round(dd, 4))


def _make_state(level: str, dd_24h: float, dd_48h: float,
                timestamp: datetime, reason: str) -> dict:
    """Create a state dict."""
    return {
        "level": level,
        "drawdown_24h_pct": round(dd_24h, 4),
        "drawdown_48h_pct": round(dd_48h, 4),
        "threshold_24h_pct": THRESHOLD_24H_PCT,
        "threshold_48h_pct": THRESHOLD_48H_PCT,
        "reason": reason,
        "timestamp": timestamp.isoformat(),
    }


def is_drawdown_breaker_active() -> bool:
    """
    Quick check: is the drawdown circuit breaker currently active?

    Reads from the state file without recomputing. Scanners and trackers
    call this before opening new positions.

    Returns:
        True if breaker is ACTIVE or CRITICAL (new entries should be paused).
        False if CLEAR or state file missing/unreadable.
    """
    try:
        state = _load_json(STATE_FILE)
        if not state:
            return False
        level = state.get("level", "CLEAR")
        if level in ("CIRCUIT_BREAKER_ACTIVE", "CIRCUIT_BREAKER_CRITICAL"):
            # Check staleness: if state is older than 2 hours, don't trust it
            ts_str = state.get("timestamp", "")
            if ts_str:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
                if age_hours > 2.0:
                    # Stale state -- don't block on old data, recompute needed
                    return False
            return True
    except Exception:
        pass
    return False


def get_drawdown_breaker_state() -> dict:
    """
    Return the full circuit breaker state dict.

    Returns empty dict if state file missing/unreadable.
    """
    return _load_json(STATE_FILE) or {}


if __name__ == "__main__":
    state = check_drawdown_breaker()
    print(json.dumps(state, indent=2, default=str))
