"""Tests for tools/strategy_crosswalk.py's pair classification.

The crosswalk only earns the right to close the DSR trial bracket if it
distinguishes "the book already counts this under another name" from "this
strategy never entered the book". These tests pin that distinction.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.strategy_crosswalk import classify_audit3_pairs  # noqa: E402


def test_direct_pair_is_counted_once():
    direct, collapsed, absent = classify_audit3_pairs(
        {("EQUITY", "golden-cross-stocks")},
        {("EQUITY", "golden-cross-stocks")},
        {"EQUITY": {"golden-cross-stocks"}},
    )
    assert direct == {("EQUITY", "golden-cross-stocks")}
    assert collapsed == set()
    assert absent == set()


def test_umbrella_filing_is_collapsed_not_drift():
    """The registry keys on source_system, so a strategy can hide under it."""
    direct, collapsed, absent = classify_audit3_pairs(
        {("EQUITY", "adx-trend-scout")},
        {("EQUITY", "alpha_engine")},
        {"EQUITY": {"adx-trend-scout", "rsi-divergence-scout"}},
    )
    assert direct == set()
    assert collapsed == {("EQUITY", "adx-trend-scout")}
    assert absent == set()


def test_strategy_outside_the_book_is_absent():
    direct, collapsed, absent = classify_audit3_pairs(
        {("BOND", "vwap-reclaim-scout")},
        {("BOND", "bond_duration_rotation")},
        {"BOND": {"bond_duration_rotation"}},
    )
    assert absent == {("BOND", "vwap-reclaim-scout")}
    assert direct == set()
    assert collapsed == set()


def test_class_boundaries_are_respected():
    """A strategy in EQUITY must not excuse the same label under ETF."""
    direct, collapsed, absent = classify_audit3_pairs(
        {("ETF", "regime_accumulation")},
        {("EQUITY", "regime_accumulation")},
        {"EQUITY": {"regime_accumulation"}},
    )
    assert collapsed == set()
    assert absent == {("ETF", "regime_accumulation")}


def test_buckets_partition_the_audit3_pairs():
    a3 = {
        ("EQUITY", "golden-cross-stocks"),
        ("EQUITY", "adx-trend-scout"),
        ("BOND", "vwap-reclaim-scout"),
    }
    direct, collapsed, absent = classify_audit3_pairs(
        a3,
        {("EQUITY", "golden-cross-stocks"), ("EQUITY", "alpha_engine")},
        {"EQUITY": {"adx-trend-scout"}},
    )
    assert direct | collapsed | absent == a3
    assert not (direct & collapsed) and not (direct & absent) and not (collapsed & absent)
