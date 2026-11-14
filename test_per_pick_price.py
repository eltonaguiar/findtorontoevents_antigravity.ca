"""_per_pick_price must price TIME_EXIT at the LATEST bar in window, not the first (Grok quick-fix #3).

Main returns the FIRST bar >= entry, so a pick that rode a 100->147 uptrend exits at ~100
(0.00% "flat"). The fix takes the latest bar at/before as_of_ms (the TIME_EXIT expiry).
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


def _bars(specs):
    return [{"timestamp": ts, "close": cl} for ts, cl in specs]


def _pick(ts: str) -> dict:
    return {"symbol": "BTCUSDT", "direction": "LONG", "entry_price": 65000.0,
            "take_profit": 67000.0, "stop_loss": 63000.0, "timestamp": ts,
            "strategy": "test", "source_system": "test"}


def test_prices_at_latest_bar_not_first() -> None:
    """A rising 100->147 book must exit near the top, not at the entry bar (100)."""
    # 48 hourly bars rising 100 -> 147, entry anchored at the first bar.
    start = _ms("2026-10-22T00:00:00Z")
    bars = _bars([(start + i * 3600_000, 100.0 + i) for i in range(48)])
    pick = _pick("2026-10-22T00:05:00Z")
    price = universal_pick_resolver._per_pick_price(
        pick, "BTCUSDT", {"BTCUSDT": bars}, 100.0)
    assert price == 147.0, f"expected latest bar (147.0), got {price}"


def test_as_of_ms_caps_at_expiry() -> None:
    """With as_of_ms = +24h, price is the expiry bar, not a later stale/later bar."""
    start = _ms("2026-10-22T00:00:00Z")
    bars = _bars([(start + i * 3600_000, 100.0 + i) for i in range(48)])
    pick = _pick("2026-10-22T00:05:00Z")
    expiry = start + 24 * 3600_000  # +24h -> bar index 24 -> price 124.0
    price = universal_pick_resolver._per_pick_price(
        pick, "BTCUSDT", {"BTCUSDT": bars}, 100.0, as_of_ms=expiry)
    assert price == 124.0, f"expected expiry-capped price 124.0, got {price}"


def test_as_of_ms_accepts_keyword() -> None:
    """The as_of_ms parameter must exist (main lacks it -> TypeError)."""
    import inspect
    sig = inspect.signature(universal_pick_resolver._per_pick_price)
    assert "as_of_ms" in sig.parameters, "_per_pick_price must accept as_of_ms"
