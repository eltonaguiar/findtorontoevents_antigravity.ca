from __future__ import annotations

from datetime import datetime, timezone

from audit_trail import universal_pick_resolver


def _ms(iso: str) -> int:
    """ISO-8601 -> epoch milliseconds (UTC)."""
    s = iso[:-1] + "+00:00" if iso.endswith("Z") else iso
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.astimezone(timezone.utc).timestamp() * 1000)


def _pick(ts: str, direction: str = "LONG") -> dict:
    return {
        "symbol": "BTCUSDT",
        "direction": direction,
        "entry_price": 65000.0,
        "take_profit": 67000.0,
        "stop_loss": 63000.0,
        "timestamp": ts,
        "strategy": "test",
        "source_system": "test",
    }


def _bars(specs) -> list[dict]:
    return [{"timestamp": ts_ms, "close": close} for ts_ms, close in specs]


def test_per_pick_price_uses_own_window_bar_not_global_snapshot() -> None:
    """Frozen-exit regression: a pick resolved via intrabar must use the close of
    a bar at/after its entry — NOT the single run-wide snapshot price that was
    previously stamped onto every pick of the symbol."""
    bars = _bars([(_ms("2026-10-22T12:00:00Z"), 65500.0),
                  (_ms("2026-10-22T13:00:00Z"), 66000.0)])
    snapshot = 65000.0  # the shared, frozen run-wide snapshot

    pick = _pick("2026-10-22T12:05:00Z")   # entry after the 12:00 bar
    price = universal_pick_resolver._per_pick_price(pick, "BTCUSDT", {"BTCUSDT": bars}, snapshot)

    assert price == 66000.0          # the 13:00 post-entry bar close
    assert price != snapshot         # NOT the frozen snapshot


def test_per_pick_price_uses_newest_post_entry_bar_for_later_pick() -> None:
    """A pick with a later entry resolves against its own (later) post-entry bar,
    proving per-pick resolution rather than one shared price."""
    bars = _bars([(_ms("2026-10-22T12:00:00Z"), 65500.0),
                  (_ms("2026-10-22T13:00:00Z"), 66000.0),
                  (_ms("2026-10-22T15:00:00Z"), 67000.0)])
    snapshot = 65000.0

    early = _pick("2026-10-22T12:05:00Z")
    late = _pick("2026-10-22T14:05:00Z")
    # Each pick is priced as of its own horizon (e.g. TIME_EXIT expiry); without
    # as_of_ms the LATEST post-entry bar is used (the first bar == entry price -> 0% exits).
    price_early = universal_pick_resolver._per_pick_price(
        early, "BTCUSDT", {"BTCUSDT": bars}, snapshot, as_of_ms=_ms("2026-10-22T14:00:00Z"))
    price_late = universal_pick_resolver._per_pick_price(late, "BTCUSDT", {"BTCUSDT": bars}, snapshot)

    assert price_early == 66000.0
    assert price_late == 67000.0
    assert price_early != price_late


def test_per_pick_price_falls_back_to_snapshot_without_bars() -> None:
    """When no intrabar bars exist, behavior must remain byte-identical to the
    legacy path (return the live snapshot)."""
    pick = _pick("2026-10-22T12:05:00Z")
    price = universal_pick_resolver._per_pick_price(
        pick, "BTCUSDT", {"BTCUSDT": []}, 65000.0
    )
    assert price == 65000.0


def test_per_pick_price_ignores_bars_before_entry() -> None:
    """Bars strictly BEFORE the pick's entry must NOT be used (no stale-window
    look-ahead) — only bars at/after entry count."""
    bars = _bars([(_ms("2026-10-22T11:00:00Z"), 60000.0),
                  (_ms("2026-10-22T12:00:00Z"), 65500.0)])
    pick = _pick("2026-10-22T12:30:00Z")
    price = universal_pick_resolver._per_pick_price(
        pick, "BTCUSDT", {"BTCUSDT": bars}, 65000.0
    )
    assert price == 65000.0  # both bars are pre-entry -> honest fallback, no 1-ahead


def test_per_pick_price_handles_unparseable_timestamp() -> None:
    """If the pick timestamp can't be parsed, fall back to the snapshot
    (never crash, never fake a window)."""
    pick = _pick("not-a-timestamp")
    bars = _bars([(_ms("2026-10-22T12:00:00Z"), 65500.0)])
    price = universal_pick_resolver._per_pick_price(
        pick, "BTCUSDT", {"BTCUSDT": bars}, 64700.0
    )
    assert price == 64700.0
