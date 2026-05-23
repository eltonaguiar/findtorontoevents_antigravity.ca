"""Tests for cross_aggregation.performance_alerts degradation/staleness logic."""

from datetime import datetime, timezone, timedelta

from cross_aggregation.performance_alerts import check_all_alerts, _strategy_degradation


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")


def test_degradation_suppressed_small_recent_sample():
    now = datetime.now(timezone.utc)
    closed = []
    for i in range(20):
        d = now - timedelta(days=14 + i * 0.1)
        closed.append({"strategy": "s1", "pnl_pct": 50.0, "closed_at": _iso(d)})
    for j in range(3):
        d = now - timedelta(days=j * 0.1)
        closed.append({"strategy": "s1", "pnl_pct": -5.0, "closed_at": _iso(d)})
    assert _strategy_degradation([], closed, []) == []


def test_degradation_suppressed_relative_drop_under_20pct():
    """Prior 60%, recent 50%: 10pp drop but relative 16.7% — no alert."""
    now = datetime.now(timezone.utc)
    closed = []
    for i in range(25):
        d = now - timedelta(days=21 + i * 0.03)
        closed.append({"strategy": "z", "pnl_pct": 1.0 if i < 15 else -1.0, "closed_at": _iso(d)})
    for j in range(12):
        d = now - timedelta(days=3 + j * 0.02)
        closed.append({"strategy": "z", "pnl_pct": 1.0 if j < 6 else -1.0, "closed_at": _iso(d)})
    assert _strategy_degradation([], closed, []) == []


def test_degradation_fires_large_drop_sufficient_n():
    now = datetime.now(timezone.utc)
    closed = []
    for i in range(25):
        d = now - timedelta(days=20 + i * 0.05)
        closed.append(
            {"strategy": "heavy", "pnl_pct": 5.0 if i < 20 else -2.0, "closed_at": _iso(d)}
        )
    for j in range(12):
        d = now - timedelta(days=2 + j * 0.02)
        closed.append({"strategy": "heavy", "pnl_pct": -3.0, "closed_at": _iso(d)})
    out = _strategy_degradation([], closed, [])
    assert len(out) == 1
    assert out[0]["severity"] == "HIGH"
    assert out[0]["details"]["strategy"] == "heavy"


def test_staleness_medium_requires_longer_gap():
    now = datetime.now(timezone.utc)
    old = now - timedelta(hours=30)
    active = [
        {
            "source_system": "riseoftheclaw",
            "timestamp": _iso(old),
            "pnl_pct": 0,
        }
    ]
    alerts = check_all_alerts(active, [], [])
    stale = [a for a in alerts if a.get("type") == "DATA_STALE"]
    assert stale == []  # 30h < 56h threshold


def test_daily_loss_ignores_realized_pnl_on_terminal_status():
    """Regression: 2026-04-27 phantom HALT bug.

    Caller mistakenly included rows with terminal status (WON/LOST/TP_HIT) but
    no `unrealized_pnl_pct`. Old code fell through to `pnl_pct` (realized) and
    summed those negative realized values into the live-PnL alert, tripping a
    CRITICAL HALT on -60% when actual unrealized was only -7%. This test pins
    the new behavior: realized rows must NOT contribute to the daily-loss sum.
    """
    active = [
        # Real open pick at -2% unrealized
        {"status": "OPEN", "unrealized_pnl_pct": -2.0, "pnl_pct": 0},
        # Terminal-status row that previously contaminated the sum
        {"status": "LOST", "unrealized_pnl_pct": None, "pnl_pct": -25.0},
        {"status": "WON", "unrealized_pnl_pct": None, "pnl_pct": +12.0},
        {"status": "TP_HIT", "unrealized_pnl_pct": None, "pnl_pct": -8.0},
    ]
    alerts = check_all_alerts(active, [], [])
    daily = [a for a in alerts if a.get("type") == "DAILY_LOSS"]
    # Total unrealized = -2.0% (only the OPEN pick); -2 > -3 → no alert at all.
    assert daily == [], f"DAILY_LOSS should not fire; got {daily}"


def test_daily_loss_fires_on_real_unrealized_drawdown():
    active = [
        {"status": "OPEN", "unrealized_pnl_pct": -3.0},
        {"status": "OPEN", "unrealized_pnl_pct": -3.0},
        # Closed/terminal rows must NOT count even if their realized pnl is bad.
        {"status": "LOST", "pnl_pct": -100.0},
    ]
    alerts = check_all_alerts(active, [], [])
    daily = [a for a in alerts if a.get("type") == "DAILY_LOSS"]
    # Total unrealized = -6.0% → CRITICAL HALT (< -5%); n=2 (only OPEN counted).
    assert len(daily) == 1
    assert daily[0]["severity"] == "CRITICAL"
    assert daily[0]["action"] == "HALT"
    assert daily[0]["details"]["pick_count"] == 2
    assert daily[0]["details"]["total_unrealized_pnl_pct"] == -6.0
