"""Tests for Charter §7 execution-cost (slippage) model.

Companion to alpha_engine/charter_slippage.py. Pure functions, deterministic.
"""
import math

import pytest

from alpha_engine.charter_slippage import (
    ONE_WAY_BPS_BY_CLASS,
    deduct_slippage,
    one_way_bps,
    round_trip_bps,
    stamp_pick_net_pnl,
)


def test_per_class_one_way_bps_are_known():
    assert one_way_bps("CRYPTO") == 4
    assert one_way_bps("EQUITY") == 3
    assert one_way_bps("ETF") == 2
    assert one_way_bps("COMMODITY") == 6
    assert one_way_bps("FOREX") == 1
    assert one_way_bps("BOND") == 3
    assert one_way_bps("FUTURES") == 4


def test_unknown_class_uses_conservative_default():
    assert one_way_bps("SPORTS") == 8
    assert one_way_bps(None) == 8
    assert one_way_bps("") == 8


def test_case_insensitive():
    assert one_way_bps("crypto") == 4
    assert one_way_bps("Equity") == 3


def test_round_trip_doubles_one_way():
    for cls in ONE_WAY_BPS_BY_CLASS:
        assert round_trip_bps(cls) == 2 * one_way_bps(cls)


def test_deduct_slippage_basic():
    # pnl_pct is a FRACTION (M-069): 0.50 == a +50% gross CRYPTO win.
    # CRYPTO round-trip = 8bp == 0.0008 as a fraction.
    assert math.isclose(
        deduct_slippage(0.50, "CRYPTO"), 0.50 - 0.0008, rel_tol=1e-9
    )


def test_multi_asset_cot_failure_case():
    # The headline finding from multi_asset_cot_slippage_analysis: top
    # winning trade is 7.18bp gross. After a 12bp COMMODITY round-trip it
    # mechanically becomes a -4.82bp net loss. Regression guard for the
    # P0.5-2 motivation — now in correct FRACTION units (M-069):
    # 7.18bp == 0.000718, 12bp round-trip == 0.0012.
    top_win_gross = 0.000718  # 7.18bp as a fraction
    net = deduct_slippage(top_win_gross, "COMMODITY")
    assert net < 0
    assert math.isclose(net, top_win_gross - 0.0012, rel_tol=1e-6)


def test_high_pf_strategy_still_profitable_at_normal_size():
    # A normal "good" win is 1-2% gross (fraction 0.01-0.02). A 100% win
    # (fraction 1.00) trivially survives an 8bp == 0.0008 CRYPTO round-trip.
    net_crypto = deduct_slippage(1.00, "CRYPTO")
    assert net_crypto > 0
    assert math.isclose(net_crypto, 1.00 - 0.0008, rel_tol=1e-9)


def test_stamp_pick_idempotent():
    pick = {"pnl_pct": 0.50, "asset_class": "EQUITY"}
    stamped = stamp_pick_net_pnl(pick)
    assert "_pnl_pct_gross" in stamped
    assert "_pnl_pct_net" in stamped
    assert math.isclose(stamped["_pnl_pct_gross"], 0.50, rel_tol=1e-9)
    # EQUITY round-trip = 6bp == 0.0006 as a fraction (M-069).
    assert math.isclose(stamped["_pnl_pct_net"], 0.50 - 0.0006, rel_tol=1e-9)
    # Re-running uses the already-stamped gross
    pick["pnl_pct"] = 99.99  # corrupted — should be ignored
    stamp_pick_net_pnl(stamped)
    assert math.isclose(stamped["_pnl_pct_gross"], 0.50, rel_tol=1e-9)


def test_stamp_pick_handles_missing_pnl():
    pick = {"asset_class": "CRYPTO"}
    result = stamp_pick_net_pnl(pick)
    assert "_pnl_pct_net" not in result


def test_stamp_pick_handles_invalid_pnl():
    pick = {"pnl_pct": "not-a-number", "asset_class": "CRYPTO"}
    result = stamp_pick_net_pnl(pick)
    assert "_pnl_pct_net" not in result


def test_stamp_pick_unknown_class_uses_default():
    pick = {"pnl_pct": 1.00, "asset_class": "ZZZ"}
    stamped = stamp_pick_net_pnl(pick)
    # Unknown class -> 8bp default one-way -> 16bp round-trip == 0.0016
    # as a fraction (M-069).
    assert math.isclose(stamped["_pnl_pct_net"], 1.00 - 0.0016, rel_tol=1e-9)
