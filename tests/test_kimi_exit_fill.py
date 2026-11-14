#!/usr/bin/env python3
"""Tests for the kimi stop-fill fix (exit_fill_for_stop / price_reached).

The defect being pinned: the KIMI live scanner fired its ATR stop when the
* polled * price had already fallen past the stop, then booked P&L at that polled
price. No resting stop order fills there. 0 of 815 kimi SL rows in the
2026-11-14 ledger were booked at the stop they exited against.
"""
from __future__ import annotations

import pytest

from audit_trail.stop_fill import BASIS_GAP, BASIS_STOP, exit_fill_for_stop, price_reached


# ---------------------------------------------------------------------------
# exit_fill_for_stop
# ---------------------------------------------------------------------------
def test_no_stop_returns_none():
    assert exit_fill_for_stop("LONG", 0, 100.0) is None
    assert exit_fill_for_stop("LONG", None, 100.0) is None
    assert exit_fill_for_stop("LONG", -5, 100.0) is None


def test_fills_at_stop_when_bar_spans_it_without_gap():
    bars = [{"open": 105.0, "high": 106.0, "low": 99.0}]
    hit = exit_fill_for_stop("LONG", 100.0, polled_price=95.0, bars=bars)
    assert hit["price"] == 100.0
    assert hit["basis"] == BASIS_STOP


def test_gap_down_fills_at_the_open_not_the_stop():
    """A bar that OPENS below the stop fills at the open — the honest direction."""
    bars = [{"open": 96.0, "high": 97.0, "low": 90.0}]
    hit = exit_fill_for_stop("LONG", 100.0, polled_price=90.5, bars=bars)
    assert hit["price"] == 96.0
    assert hit["basis"] == BASIS_GAP


def test_short_gap_up_fills_at_the_open():
    bars = [{"open": 104.0, "high": 108.0, "low": 103.0}]
    hit = exit_fill_for_stop("SHORT", 100.0, polled_price=107.0, bars=bars)
    assert hit["price"] == 104.0
    assert hit["basis"] == BASIS_GAP


def test_polled_price_is_never_used_as_the_fill():
    """The whole point: a deep poll must not leak into the booked price.

    The bar opens ABOVE the stop (100.2 > 100.0), so there is no gap and the
    fill is the stop itself — a 50.0 poll must not appear anywhere.
    """
    bars = [{"open": 100.2, "high": 100.5, "low": 99.0}]
    hit = exit_fill_for_stop("LONG", 100.0, polled_price=50.0, bars=bars)
    assert hit["price"] == 100.0
    assert hit["basis"] == BASIS_STOP


def test_without_bars_falls_back_to_the_stop_resting_order_model():
    hit = exit_fill_for_stop("LONG", 100.0, polled_price=88.0, bars=None)
    assert hit["price"] == 100.0
    assert hit["basis"] == BASIS_STOP


def test_bars_that_never_breach_still_return_the_stop():
    """The caller only asks after a poll shows a breach; a quiet bar must not
    silently blank the exit out."""
    bars = [{"open": 101.0, "high": 102.0, "low": 100.5}]
    hit = exit_fill_for_stop("LONG", 100.0, polled_price=99.0, bars=bars)
    assert hit["price"] == 100.0


def test_string_numbers_are_accepted():
    bars = [{"open": "104.0", "high": "105.0", "low": "103.0"}]
    hit = exit_fill_for_stop("LONG", "100.0", polled_price="101", bars=bars)
    assert hit["price"] == 100.0


# ---------------------------------------------------------------------------
# price_reached — B4 (mislabelled exit vs fictional exit)
# ---------------------------------------------------------------------------
def test_price_reached_long_true():
    assert price_reached("LONG", 98.0, [{"high": 101.0, "low": 97.5}]) is True


def test_price_reached_long_false():
    assert price_reached("LONG", 90.0, [{"high": 101.0, "low": 97.5}]) is False


def test_price_reached_short_uses_high():
    assert price_reached("SHORT", 103.0, [{"high": 104.0, "low": 99.0}]) is True
    assert price_reached("SHORT", 103.0, [{"high": 101.0, "low": 99.0}]) is False


def test_price_reached_unusable_level_is_none():
    assert price_reached("LONG", 0, [{"high": 1.0, "low": 1.0}]) is None
    assert price_reached("LONG", None, [{"high": 1.0, "low": 1.0}]) is None


def test_price_reached_skips_malformed_bars():
    bars = [{"high": None, "low": None}, {"high": 100.0, "low": 95.0}]
    assert price_reached("LONG", 96.0, bars) is True


def test_price_reached_empty_bars_is_false():
    assert price_reached("LONG", 96.0, []) is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
