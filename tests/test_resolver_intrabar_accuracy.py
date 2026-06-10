"""Test harness for production-resolver intrabar accuracy (Bug 1A / 1B / 1C).

Encodes the ACCEPTANCE CRITERIA for `audit_trail/universal_pick_resolver._check_tp_sl_intrabar`.
TDD contract: the entry-window / stale-window / ambiguous / bad-geometry tests are RED on the
current code (they prove the harness catches Bug 1A/1C) and turn GREEN once the entry-anchored
fix lands. The core first-touch tests (SL-first, TP-before-SL, SHORT) test the already-correct
logic and should pass now.

Run: python3 -m pytest tests/test_resolver_intrabar_accuracy.py -v
Plan: reports/plan_bug1a_entry_anchored_resolver_2026-06-10.md
"""
from __future__ import annotations

import os
import sys
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from audit_trail.universal_pick_resolver import _check_tp_sl_intrabar  # noqa: E402

HOUR_MS = 3_600_000
T0 = 1_700_000_000_000  # arbitrary fixed base ms (no wall-clock dependency)


def bar(i: int, high: float, low: float, *, open_=None, close=None) -> dict:
    """1h bar i hours after T0, carrying a timestamp (the field the fix relies on)."""
    return {
        "timestamp": T0 + i * HOUR_MS,
        "open": open_ if open_ is not None else (high + low) / 2,
        "high": high,
        "low": low,
        "close": close if close is not None else (high + low) / 2,
        "volume": 1000,
    }


def pick(direction: str, entry: float, tp: float, sl: float, *, entry_bar: int = 0) -> dict:
    """A pick whose entry timestamp is at bar `entry_bar`."""
    import datetime as dt
    entry_ms = T0 + entry_bar * HOUR_MS
    ts = dt.datetime.utcfromtimestamp(entry_ms / 1000).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "symbol": "TESTUSDT", "direction": direction, "entry_price": entry,
        "take_profit": tp, "stop_loss": sl, "timestamp": ts, "_entry_ms": entry_ms,
    }


def _reason(result):
    return result[0] if result else None


# ── CORE first-touch (already-correct logic — should PASS now) ──────────────────
def test_long_tp_before_sl_is_tp():
    p = pick("LONG", 100, 110, 90)
    bars = [bar(0, 105, 99), bar(1, 111, 104)]  # bar1 high 111 >= tp 110, no sl touch
    assert _reason(_check_tp_sl_intrabar(p, bars)) == "TP_HIT"


def test_long_sl_before_tp_is_sl():
    p = pick("LONG", 100, 110, 90)
    bars = [bar(0, 105, 89), bar(1, 111, 104)]  # bar0 low 89 <= sl 90 FIRST
    assert _reason(_check_tp_sl_intrabar(p, bars)) == "SL_HIT"


def test_short_sl_before_tp_is_sl():
    p = pick("SHORT", 100, 90, 110)
    bars = [bar(0, 111, 95)]  # SHORT sl=110: high 111 >= sl -> SL_HIT
    assert _reason(_check_tp_sl_intrabar(p, bars)) == "SL_HIT"


def test_no_touch_returns_none():
    p = pick("LONG", 100, 110, 90)
    bars = [bar(0, 105, 96), bar(1, 108, 97)]  # never hits tp or sl
    assert _check_tp_sl_intrabar(p, bars) is None


# ── Bug 1C: same-bar conservative SL-first (passes now) + ambiguous flag (RED until fix) ──
def test_same_bar_both_touched_is_sl_conservative():
    p = pick("LONG", 100, 110, 90)
    bars = [bar(0, 111, 89)]  # one bar touches BOTH tp(110) and sl(90)
    assert _reason(_check_tp_sl_intrabar(p, bars)) == "SL_HIT"  # SL-first conservative


@pytest.mark.xfail(reason="Bug 1C: production resolver lacks an ambiguous flag (port from reresolve tools)", strict=False)
def test_same_bar_ambiguous_flagged():
    p = pick("LONG", 100, 110, 90)
    bars = [bar(0, 111, 89)]
    result = _check_tp_sl_intrabar(p, bars)
    # contract: 4th element (or a dict field) marks ambiguity
    assert result is not None and len(result) >= 4 and result[3] is True


# ── Bug 1A: entry-forward filter / stale-window (RED until the entry-anchored fix) ──
@pytest.mark.xfail(reason="Bug 1A: resolver ignores bar timestamps, replays stale bars vs old picks", strict=False)
def test_stale_window_does_not_fake_resolve():
    # Pick entered at bar 100, but only OLD bars (0..2) are available (the most-recent-window bug
    # in reverse: here the cache is older than entry). An entry-anchored resolver must NOT resolve.
    p = pick("LONG", 100, 110, 90, entry_bar=100)
    bars = [bar(0, 111, 89), bar(1, 111, 89)]  # both pre-entry, would fire if not filtered
    assert _check_tp_sl_intrabar(p, bars) is None  # no entry-forward bars -> None -> close_approx


@pytest.mark.xfail(reason="Bug 1A: pre-entry bars are not filtered out", strict=False)
def test_pre_entry_touch_is_ignored():
    # SL is touched at bar 0 (BEFORE entry at bar 5); a correct resolver ignores pre-entry bars.
    p = pick("LONG", 100, 110, 90, entry_bar=5)
    bars = [bar(0, 105, 85),  # pre-entry SL touch — must be IGNORED
            bar(6, 111, 104)]  # post-entry TP touch — the real outcome
    assert _reason(_check_tp_sl_intrabar(p, bars)) == "TP_HIT"


# ── Bug 1C: bad-geometry guard (RED until ported) ──
@pytest.mark.xfail(reason="Bug 1C: production resolver has no valid_geometry guard", strict=False)
def test_bad_geometry_long_sl_above_entry_is_skipped():
    # Corrupt LONG: sl(150) > entry(100) — a real resolver must skip (BAD_GEOMETRY), not fire SL_HIT.
    p = pick("LONG", 100, 110, 150)
    bars = [bar(0, 160, 155)]
    result = _check_tp_sl_intrabar(p, bars)
    assert result is None or _reason(result) in ("BAD_GEOMETRY", None)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
