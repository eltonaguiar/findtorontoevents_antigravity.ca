import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpha_engine.intrabar_resolver import first_touch, stamp_pick  # noqa: E402


def bar(hi, lo, op=None, close=None, ts="t"):
    return {"high": hi, "low": lo, "open": op, "close": close, "timestamp": ts}


def test_stop_wins_when_both_touch_same_bar():
    r = first_touch([bar(110, 90)], direction="LONG", entry_price=100,
                    stop_loss=95, take_profit=105)
    assert r["outcome"] == "STOP"
    assert r["same_bar_both"] is True


def test_take_profit_when_only_target_touched():
    r = first_touch([bar(106, 99)], direction="LONG", entry_price=100,
                    stop_loss=95, take_profit=105)
    assert r["outcome"] == "TP"
    assert r["price"] == 105


def test_gap_through_stop_fills_at_open_not_stop():
    r = first_touch([bar(101, 90, op=92)], direction="LONG", entry_price=100,
                    stop_loss=95, take_profit=105)
    assert r["outcome"] == "STOP"
    assert r["gapped"] is True
    assert r["price"] == 92


def test_time_exit_uses_last_close():
    r = first_touch([bar(101, 99, close=100.5), bar(102, 100, close=101.0)],
                    direction="LONG", entry_price=100, stop_loss=95,
                    take_profit=110)
    assert r["outcome"] == "TIME"
    assert r["price"] == 101.0


def test_short_direction_mirrors():
    r = first_touch([bar(105, 95)], direction="SHORT", entry_price=100,
                    stop_loss=104, take_profit=96)
    assert r["outcome"] == "STOP"
    assert r["gapped"] is False


def test_no_bars_is_unresolved_not_fake():
    assert first_touch([], direction="LONG", entry_price=100, stop_loss=95) is None
    out = stamp_pick({"direction": "LONG", "entry_price": 100, "stop_loss": 95}, [])
    assert out["intrabar_first_touch"] is False
    assert "resolved_outcome" not in out


def test_stamp_pick_marks_intrabar_true():
    out = stamp_pick({"direction": "LONG", "entry_price": 100, "stop_loss": 95,
                      "take_profit": 105}, [bar(106, 99, ts="2026-11-19T00:00Z")])
    assert out["intrabar_first_touch"] is True
    assert out["resolved_outcome"] == "TP"
    assert out["resolver_version"] == "intrabar.v1"


def test_bad_direction_raises():
    with pytest.raises(ValueError):
        first_touch([bar(1, 1)], direction="SIDEWAYS", entry_price=1, stop_loss=0.5)
