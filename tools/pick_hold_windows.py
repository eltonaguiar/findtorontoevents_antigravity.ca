"""Shared max-hold windows for live trading_picks (OPEN + ACTIVE).

Used by resolve_stale_open_picks.py and check_resolver_health.py so MySQL
hygiene and health metrics agree on what counts as past max hold.
"""
from __future__ import annotations

from datetime import datetime, timezone

# Statuses treated as live / unresolved in trading_picks
LIVE_PICK_STATUSES: tuple[str, ...] = ("OPEN", "ACTIVE")

HOLD_HOURS_BY_CATEGORY: dict[str, int] = {
    "crypto": 48,
    "meme": 48,
    "equity": 96,
    "equities": 96,
    "stock": 96,
    "stocks": 96,
    "penny": 72,
    "pennystock": 72,
    "etf": 96,
    "commodity": 96,
    "commodities": 96,
    "futures": 96,
    "forex": 72,
    "bond": 120,
    "bonds": 120,
    "index": 96,
}
DEFAULT_HOLD_HOURS = 48


def hold_hours_for(category: str | None) -> int:
    c = (category or "").strip().lower()
    return HOLD_HOURS_BY_CATEGORY.get(c, DEFAULT_HOLD_HOURS)


def pick_age_hours(pick: dict, *, now: datetime | None = None) -> float | None:
    ts = pick.get("submitted_at") or pick.get("created_at") or pick.get("recorded_at")
    if ts is None:
        return None
    ref = now or datetime.now(timezone.utc)
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return (ref - ts).total_seconds() / 3600.0
    if isinstance(ts, str):
        s = ts.strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return (ref - dt).total_seconds() / 3600.0
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                dt = datetime.strptime(ts[:19], fmt).replace(tzinfo=timezone.utc)
                return (ref - dt).total_seconds() / 3600.0
            except ValueError:
                continue
    return None


def is_past_max_hold(pick: dict, *, now: datetime | None = None) -> bool:
    age = pick_age_hours(pick, now=now)
    if age is None:
        return False
    return age > hold_hours_for(pick.get("category"))
