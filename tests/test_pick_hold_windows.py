"""Tests for tools/pick_hold_windows.py"""
from datetime import datetime, timezone

from tools.pick_hold_windows import (
    LIVE_PICK_STATUSES,
    hold_hours_for,
    is_past_max_hold,
    pick_age_hours,
)


def test_live_statuses_include_active():
    assert "OPEN" in LIVE_PICK_STATUSES
    assert "ACTIVE" in LIVE_PICK_STATUSES


def test_forex_hold_72h():
    assert hold_hours_for("forex") == 72


def test_is_past_max_hold_crypto():
    old = datetime.now(timezone.utc).replace(year=2020)
    pick = {"category": "crypto", "created_at": old}
    assert is_past_max_hold(pick) is True


def test_is_not_past_max_hold_recent():
    recent = datetime.now(timezone.utc)
    pick = {"category": "crypto", "created_at": recent}
    assert is_past_max_hold(pick) is False


def test_pick_age_hours_from_string():
    pick = {"created_at": "2020-01-01T00:00:00Z"}
    age = pick_age_hours(pick)
    assert age is not None and age > 1000
