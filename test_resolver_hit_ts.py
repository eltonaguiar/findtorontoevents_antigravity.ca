"""Intrabar hits must stamp the HIT BAR's timestamp, not the resolver run time (Grok quick-fix #1).

Main stamped resolved_at = now (the resolver run time) on every hit, producing batch-close
clusters (e.g. 21/29 closes all at the same second). The fix records the bar open_time where
SL/TP was actually touched (pick["_hit_bar_ts"]) and stamps that, falling back to now when
missing or in the future. Also pp_price must be bound up front so an intrabar hit does not
NameError or reuse the previous pick's price.
"""
from __future__ import annotations

from datetime import datetime, timezone

from audit_trail import universal_pick_resolver


def _ms(iso: str) -> int:
    s = iso[:-1] + "+00:00" if iso.endswith("Z") else iso
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.astimezone(timezone.utc).timestamp() * 1000)


def test_hit_ts_iso_exists_and_uses_hit_bar() -> None:
    """_hit_ts_iso must exist and format the hit-bar ms as ISO-Z."""
    fn = getattr(universal_pick_resolver, "_hit_ts_iso", None)
    assert fn is not None, "_hit_ts_iso helper missing (fix1)"
    now = datetime(2026, 10, 22, 12, 0, 0, tzinfo=timezone.utc)
    hit_ms = _ms("2026-10-22T06:18:00Z")
    assert fn(hit_ms, now) == "2026-10-22T06:18:00Z"


def test_hit_ts_iso_falls_back_for_future() -> None:
    """A future hit bar (bad clock) falls back to the run time."""
    fn = universal_pick_resolver._hit_ts_iso
    now = datetime(2026, 10, 22, 12, 0, 0, tzinfo=timezone.utc)
    future_ms = _ms("2026-10-23T00:00:00Z")
    assert fn(future_ms, now) == now.strftime("%Y-%m-%dT%H:%M:%SZ")


def test_hit_ts_iso_falls_back_for_none() -> None:
    fn = universal_pick_resolver._hit_ts_iso
    now = datetime(2026, 10, 22, 12, 0, 0, tzinfo=timezone.utc)
    assert fn(None, now) == now.strftime("%Y-%m-%dT%H:%M:%SZ")


def test_intrabar_hit_records_hit_bar_ts() -> None:
    """On a LONG entry, an up-bar that crosses TP must stamp _hit_bar_ts on the pick."""
    entry_ms = _ms("2026-10-22T00:00:00Z")
    hit_ms = _ms("2026-10-22T00:05:00Z")  # the bar that touches TP
    pick = {
        "symbol": "BTCUSDT", "direction": "LONG", "entry_price": 100.0,
        "take_profit": 105.0, "stop_loss": 95.0,
        "timestamp": "2026-10-22T00:00:00Z",
        "strategy": "test", "source_system": "test",
    }
    bars = [
        {"timestamp": entry_ms, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5},
        {"timestamp": hit_ms, "open": 100.5, "high": 106.0, "low": 100.0, "close": 105.5},
    ]
    result = universal_pick_resolver._check_tp_sl_intrabar(pick, bars)
    assert result is not None, "expected an intrabar hit on the second bar"
    reason = result[0] if isinstance(result, tuple) else result
    assert "TP" in str(reason).upper(), f"expected TP hit, got {result}"
    assert pick.get("_hit_bar_ts") == hit_ms, (
        f"pick must record the HIT bar ts ({hit_ms}), got {pick.get('_hit_bar_ts')}")
