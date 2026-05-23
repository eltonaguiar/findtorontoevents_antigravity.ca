#!/usr/bin/env python3
"""
ALPHA ENGINE -- BTC UTC Hour Death-Zone Filter
================================================
Score adjustment for BTC picks based on UTC hour-of-day.

Empirical edge (per `feedback_clean_data_symbol_wr` + `feedback_quick_guess_horizons`
memory, sourced from `audit_dashboard/data/dashboard_data.json::picks.recent_closed`
filtered to symbol == "BINANCE:BTCUSDT", n>1000 closed picks):

  - 08-09 UTC = 18.2% WR  → death zone (penalty -12)
  - 22 UTC    = 61.2% WR  → sweet spot (bonus +5)
  - All other hours       = neutral (0)

Applied in `score_booster.run_score_booster` via a try/except wire so a missing
module degrades cleanly.

Fail-open: anything unparseable (bad timestamp, missing symbol, etc.) returns 0.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# Hour-of-day (UTC) → score delta. Empirical band from memory citation above.
BTC_HOUR_PENALTIES: dict[int, int] = {
    8: -12,
    9: -12,
    22: 5,
}

_BTC_SYMBOLS = {"BTCUSDT", "BTCUSD"}


def _extract_symbol(pick: dict) -> str:
    """Return the pick's symbol with any exchange prefix (BINANCE:, COINBASE:, etc.) stripped."""
    sym = pick.get("symbol") or ""
    if not isinstance(sym, str):
        return ""
    if ":" in sym:
        sym = sym.split(":", 1)[1]
    return sym.upper().strip()


def _parse_hour_utc(value: Any) -> int | None:
    """Parse an ISO-8601 string or epoch float into UTC hour-of-day. None on failure."""
    if value is None:
        return None
    # Epoch numeric path
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc).hour
        except (OverflowError, OSError, ValueError):
            return None
    # ISO string path
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        # Normalize trailing Z → +00:00 for fromisoformat
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).hour
    return None


def btc_hour_score_adjustment(pick: dict) -> int:
    """Return score delta for a BTC pick whose created_at hour matches the penalty table.

    Returns 0 for non-BTC symbols, neutral hours, or unparseable timestamps (fail-open).
    """
    if not isinstance(pick, dict):
        return 0
    symbol = _extract_symbol(pick)
    if symbol not in _BTC_SYMBOLS:
        return 0
    ts = pick.get("created_at") or pick.get("signal_time")
    hour = _parse_hour_utc(ts)
    if hour is None:
        return 0
    return BTC_HOUR_PENALTIES.get(hour, 0)
