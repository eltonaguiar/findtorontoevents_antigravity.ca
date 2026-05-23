"""Tests for audit_trail.pick_sanity."""

import pytest

from audit_trail.pick_sanity import pick_financial_sanity_issues, passes_pick_sanity


def test_long_valid_geometry():
    p = {
        "direction": "LONG",
        "entry_price": 100.0,
        "take_profit": 110.0,
        "stop_loss": 95.0,
        "confidence": 0.7,
    }
    assert passes_pick_sanity(p)


def test_short_valid_geometry():
    p = {
        "direction": "SHORT",
        "entry_price": 100.0,
        "take_profit": 90.0,
        "stop_loss": 105.0,
    }
    assert passes_pick_sanity(p)


def test_long_inverted_tp_sl():
    p = {
        "direction": "LONG",
        "entry_price": 100.0,
        "take_profit": 90.0,
        "stop_loss": 105.0,
    }
    assert "long_tp_sl_geometry" in pick_financial_sanity_issues(p)


def test_negative_entry():
    p = {"entry_price": -1.0, "direction": "LONG"}
    assert "entry_price_non_positive" in pick_financial_sanity_issues(p)


def test_rr_out_of_range():
    p = {
        "direction": "LONG",
        "entry_price": 100,
        "take_profit": 100.01,
        "stop_loss": 0.01,
        "risk_reward": 50.0,
    }
    assert "risk_reward_out_of_range" in pick_financial_sanity_issues(p)
