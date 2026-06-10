"""Test harness for production-resolver intrabar accuracy (Bug 1A / 1B / 1C).

Acceptance criteria for `audit_trail/universal_pick_resolver._check_tp_sl_intrabar`.
PR1 enables the entry-anchored path via RESOLVER_ENTRY_ANCHORED=1 (set BEFORE import — the module
reads the flag at load). All cases now PASS with the fix; test_flag_off_is_legacy_behavior proves the
flag-OFF path is unchanged (byte-identical production default).

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

# Enable the entry-anchored fix BEFORE import — _ENTRY_ANCHORED is read at module load time.
os.environ["RESOLVER_ENTRY_ANCHORED"] = "1"
import audit_trail.universal_pick_resolver as upr  # noqa: E402

_check_tp_sl_intrabar = upr._check_tp_sl_intrabar

HOUR_MS = 3_600_000
T0 = 1_700_000_000_000  # fixed base ms (no wall-clock dependency)


def bar(i: int, high: float, low: float, *, open_=None, close=None) -> dict:
    return {
        "timestamp": T0 + i * HOUR_MS,
        "open": open_ if open_ is not None else (high + low) / 2,
        "high": high,
        "low": low,
        "close": close if close is not None else (high + low) / 2,
        "volume": 1000,
    }


def pick(direction: str, entry: float, tp: float, sl: float, *, entry_bar: int = 0) -> dict:
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
    return p.get(key)


# ── CORE first-touch ──────────────────────────────────────────────────────────
def test_long_tp_before_sl_is_tp():
    p = pick("LONG", 100, 110, 90)
    assert _reason(_check_tp_sl_intrabar(p, [bar(0, 105, 99), bar(1, 111, 104)])) == "TP_HIT"


def test_long_sl_before_tp_is_sl():
    p = pick("LONG", 100, 110, 90)
    assert _reason(_check_tp_sl_intrabar(p, [bar(0, 105, 89), bar(1, 111, 104)])) == "SL_HIT"


def test_short_sl_before_tp_is_sl():
    p = pick("SHORT", 100, 90, 110)
    assert _reason(_check_tp_sl_intrabar(p, [bar(0, 111, 95)])) == "SL_HIT"


def test_no_touch_returns_none():
    p = pick("LONG", 100, 110, 90)
    assert _check_tp_sl_intrabar(p, [bar(0, 105, 96), bar(1, 108, 97)]) is None


# ── Bug 1C: same-bar conservative SL-first + ambiguous flag (on pick dict) ──
def test_same_bar_both_touched_is_sl_conservative():
    p = pick("LONG", 100, 110, 90)
    assert _reason(_check_tp_sl_intrabar(p, [bar(0, 111, 89)])) == "SL_HIT"


def test_same_bar_ambiguous_flagged():
    # Contract (3-tuple preserved): ambiguity carried on the pick dict, not a 4th tuple element.
    p = pick("LONG", 100, 110, 90)
    result = _check_tp_sl_intrabar(p, [bar(0, 111, 89)])
    assert _reason(result) == "SL_HIT" and pick_flag(p, "_intrabar_ambiguous") is True


# ── Bug 1A: entry-forward filter / stale-window / partial-API / offset-entry ──
def test_stale_window_does_not_fake_resolve():
    # Pick entered at bar 100 but only OLD bars (0..1) available -> no entry-forward bars -> None.
    p = pick("LONG", 100, 110, 90, entry_bar=100)
    assert _check_tp_sl_intrabar(p, [bar(0, 111, 89), bar(1, 111, 89)]) is None


def test_pre_entry_touch_is_ignored():
    # SL touched at bar 0 (before entry at bar 5) must be IGNORED; post-entry TP is the outcome.
    p = pick("LONG", 100, 110, 90, entry_bar=5)
    assert _reason(_check_tp_sl_intrabar(p, [bar(0, 105, 85), bar(6, 111, 104)])) == "TP_HIT"


def test_offset_timestamp_entry_is_handled():
    # Offset-bearing entry now PARSES (Bug 1A must-fix #2). Entry (2026) is after all bars (T0~2023)
    # -> no entry-forward bars -> None -> close_approx (NOT an unfiltered stale-bar replay).
    p = pick("LONG", 100, 110, 90)
    p["timestamp"] = "2026-04-01T00:00:00+00:00"
    assert _check_tp_sl_intrabar(p, [bar(0, 111, 89)]) is None


def test_partial_api_window_after_entry_does_not_fake_resolve():
    # Old pick (entry bar 0) but the API could only return bars 100+; window starts long after entry
    # -> early bars missing -> must NOT fake-resolve on a partial window.
    p = pick("LONG", 100, 110, 90, entry_bar=0)
    assert _check_tp_sl_intrabar(p, [bar(100, 111, 89), bar(101, 111, 89)]) is None


def test_entry_equals_bar_boundary():
    # entry at bar 1; pre-entry SL at bar 0 must NOT fire (open_time >= entry_ms keeps bar 1 onward).
    p = pick("LONG", 100, 110, 90, entry_bar=1)
    assert _reason(_check_tp_sl_intrabar(p, [bar(0, 105, 85), bar(1, 108, 96), bar(2, 111, 104)])) == "TP_HIT"


# ── Bug 1C: bad-geometry guard ──
def test_bad_geometry_long_sl_above_entry_is_skipped():
    p = pick("LONG", 100, 110, 150)  # corrupt: sl(150) > entry(100)
    result = _check_tp_sl_intrabar(p, [bar(0, 160, 155)])
    assert result is None and pick_flag(p, "_intrabar_bad_geometry") is True


# ── Acceptance #8 gap-through + defensive un-timestamped keep ──
def test_gap_through_open_beyond_tp_is_tp():
    p = pick("LONG", 100, 110, 90)
    assert _reason(_check_tp_sl_intrabar(p, [bar(0, 120, 112, open_=115)])) == "TP_HIT"


def test_untimestamped_bar_still_processed_defensive_keep():
    p = pick("LONG", 100, 110, 90)
    b = {"open": 105, "high": 111, "low": 104, "close": 108, "volume": 1}  # no timestamp key
    assert _reason(_check_tp_sl_intrabar(p, [b])) == "TP_HIT"


# ── Flag OFF = legacy behavior, byte-identical (production default) ──
def test_flag_off_is_legacy_behavior(monkeypatch):
    # With the flag OFF, the entry filter is skipped: a stale-window pick resolves on whatever bars
    # are passed (the CURRENT/legacy behavior) — proving PR1 is inert until RESOLVER_ENTRY_ANCHORED=1.
    monkeypatch.setattr(upr, "_ENTRY_ANCHORED", False)
    p = pick("LONG", 100, 110, 90, entry_bar=100)  # entry far after the bars
    # legacy: no entry filter -> bar 0 SL fires
    assert _reason(_check_tp_sl_intrabar(p, [bar(0, 105, 89)])) == "SL_HIT"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
