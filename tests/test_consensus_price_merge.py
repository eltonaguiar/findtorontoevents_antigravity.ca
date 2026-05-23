"""Tests for audit_trail.consensus_price_merge."""

from audit_trail.consensus_price_merge import merge_consensus_price_levels
from audit_trail.pick_sanity import passes_pick_sanity


def test_mean_long_valid():
    picks = [
        {"entry_price": 100, "take_profit": 110, "stop_loss": 95, "confidence": 0.8},
        {"entry_price": 102, "take_profit": 112, "stop_loss": 97, "confidence": 0.7},
    ]
    e, tp, sl, method = merge_consensus_price_levels(picks, "LONG", passes_pick_sanity)
    assert method == "mean"
    assert e == 101.0
    assert tp == 111.0
    assert sl == 96.0


def test_mean_breaks_falls_back_to_anchor():
    """Mixed entries can make mean geometry invalid; best standalone pick wins."""
    good = {"entry_price": 100, "take_profit": 110, "stop_loss": 95, "confidence": 0.9}
    bad = {"entry_price": 500, "take_profit": 110, "stop_loss": 95, "confidence": 0.5}
    e, tp, sl, method = merge_consensus_price_levels(
        [bad, good], "LONG", passes_pick_sanity
    )
    assert method == "anchor_highest_confidence"
    assert e == 100.0
    assert tp == 110.0
    assert sl == 95.0


def test_short_consensus_mean():
    picks = [
        {"entry_price": 100.0, "take_profit": 90.0, "stop_loss": 105.0, "confidence": 0.8},
        {"entry_price": 102.0, "take_profit": 88.0, "stop_loss": 106.0, "confidence": 0.7},
    ]
    e, tp, sl, method = merge_consensus_price_levels(picks, "SHORT", passes_pick_sanity)
    assert method == "mean"
    assert e == 101.0
    assert tp == 89.0
    assert sl == 105.5
