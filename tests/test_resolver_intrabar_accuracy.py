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


def pick_flag(p: dict, key: str):
    """Read a flag the post-fix resolver is contracted to set on the pick dict."""
    return p.get(key)


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
    # CONTRACT (per 2026-06-10 debate): keep the 3-tuple return (the sole caller at
    # universal_pick_resolver.py:1275 strict-unpacks `reason, exit_price, pnl_pct = result` —
    # a 4-tuple would ValueError on the hot path). Ambiguity is carried on the PICK dict, NOT
    # as a 4th tuple element. So the post-fix assertion is on pick["_intrabar_ambiguous"].
    p = pick("LONG", 100, 110, 90)
    bars = [bar(0, 111, 89)]
    result = _check_tp_sl_intrabar(p, bars)
    assert _reason(result) == "SL_HIT" and pick_flag(p, "_intrabar_ambiguous") is True


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


# ── Debate-mandated additions (2026-06-10 swarm review of the Bug 1A plan) ──
# NOTE: the 4 xfail(strict=False) markers above + the ones below stay strict=False ONLY
# until the entry-anchored fix lands; the implementing PR MUST flip them to strict=True (or
# convert to plain asserts) so they provably flip RED->GREEN and a future regression fails CI.

@pytest.mark.xfail(reason="Bug 1A CRITICAL: offset-bearing entry (parse->None) must degrade to close_approx, NOT replay unfiltered bars", strict=False)
def test_offset_timestamp_entry_does_not_fake_resolve():
    # The judge VERIFIED _parse_timestamp returns None for '+00:00'/'-05:00' offsets. The fix must
    # route an unparseable entry to None (-> close_approx), never to an unfiltered stale-bar replay.
    p = pick("LONG", 100, 110, 90)
    p["timestamp"] = "2026-04-01T00:00:00+00:00"
    bars = [bar(0, 111, 89)]  # would fire SL_HIT if entry not honored
    assert _check_tp_sl_intrabar(p, bars) is None


@pytest.mark.xfail(reason="Bug 1A CRITICAL: live-API partial window starting AFTER entry must degrade to close_approx", strict=False)
def test_partial_api_window_after_entry_does_not_fake_resolve():
    # Old pick (entry at bar 0) but the live API could only return recent bars (100+). The window
    # STARTS long after entry -> the early bars where first-touch may have happened are missing ->
    # must NOT fake-resolve on this partial window (oldest bar >> entry + tolerance => None).
    p = pick("LONG", 100, 110, 90, entry_bar=0)
    bars = [bar(100, 111, 89), bar(101, 111, 89)]
    assert _check_tp_sl_intrabar(p, bars) is None


@pytest.mark.xfail(reason="Bug 1A open-Q3: bar exactly at entry + a pre-entry bar — the pre-entry SL must not fire", strict=False)
def test_entry_equals_bar_boundary():
    p = pick("LONG", 100, 110, 90, entry_bar=1)
    bars = [bar(0, 105, 85),   # pre-entry SL touch — must be IGNORED
            bar(1, 108, 96),   # at-entry bar, no touch
            bar(2, 111, 104)]  # post-entry TP — the real outcome
    assert _reason(_check_tp_sl_intrabar(p, bars)) == "TP_HIT"


def test_gap_through_open_beyond_tp_is_tp():
    # Acceptance criterion #8 (was untested): LONG gap-up, bar opens beyond TP, never touches SL -> TP_HIT.
    p = pick("LONG", 100, 110, 90)
    bars = [bar(0, 120, 112, open_=115)]  # high 120>=tp110; low 112 never <=sl 90
    assert _reason(_check_tp_sl_intrabar(p, bars)) == "TP_HIT"


def test_untimestamped_bar_still_processed_defensive_keep():
    # Defensive-keep: a bar lacking 'timestamp' must still be processed so un-stamped sources
    # don't silently start returning None after the fix adds the entry filter.
    p = pick("LONG", 100, 110, 90)
    b = {"open": 105, "high": 111, "low": 104, "close": 108, "volume": 1}  # no timestamp key
    assert _reason(_check_tp_sl_intrabar(p, [b])) == "TP_HIT"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
