#!/usr/bin/env python3
"""
test_won_pnl_contradiction.py — Tests for WON/PnL sign coherence.

Validates that:
1. PnL for LONG positions is (exit - entry) / entry
2. PnL for SHORT positions is (entry - exit) / entry
3. WON status always implies positive PnL
4. classify_outcome edge cases are handled correctly
5. _resolve_claude_gainer_ml_pick uses direction-aware PnL

Usage:
    python tools/test_won_pnl_contradiction.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from alpha_engine.outcome_resolver import compute_pnl, classify_outcome


def test_long_pnl_positive_when_exit_above_entry():
    """LONG: exit > entry => positive PnL."""
    entry = 100.0
    exit_price = 105.0
    pnl = compute_pnl(entry, exit_price, "LONG")
    assert pnl == 0.05, f"Expected 0.05, got {pnl}"
    print("  PASS: LONG PnL positive when exit > entry")


def test_long_pnl_negative_when_exit_below_entry():
    """LONG: exit < entry => negative PnL."""
    entry = 100.0
    exit_price = 95.0
    pnl = compute_pnl(entry, exit_price, "LONG")
    assert pnl == -0.05, f"Expected -0.05, got {pnl}"
    print("  PASS: LONG PnL negative when exit < entry")


def test_short_pnl_positive_when_exit_below_entry():
    """SHORT: exit < entry => positive PnL (price fell, short profits)."""
    entry = 100.0
    exit_price = 95.0
    pnl = compute_pnl(entry, exit_price, "SHORT")
    assert pnl == 0.05, f"Expected 0.05, got {pnl}"
    print("  PASS: SHORT PnL positive when exit < entry")


def test_short_pnl_negative_when_exit_above_entry():
    """SHORT: exit > entry => negative PnL (price rose, short loses)."""
    entry = 100.0
    exit_price = 105.0
    pnl = compute_pnl(entry, exit_price, "SHORT")
    assert pnl == -0.05, f"Expected -0.05, got {pnl}"
    print("  PASS: SHORT PnL negative when exit > entry")


def test_short_pnl_at_tp_is_positive():
    """SHORT hitting TP (below entry) must yield positive PnL."""
    entry = 1.0
    tp = 0.97  # 3% below entry
    pnl = compute_pnl(entry, tp, "SHORT")
    assert pnl > 0, f"SHORT at TP should have positive PnL, got {pnl}"
    assert abs(pnl - 0.03) < 1e-6, f"Expected ~0.03, got {pnl}"
    print("  PASS: SHORT at TP yields positive PnL")


def test_short_pnl_at_sl_is_negative():
    """SHORT hitting SL (above entry) must yield negative PnL."""
    entry = 1.0
    sl = 1.02  # 2% above entry
    pnl = compute_pnl(entry, sl, "SHORT")
    assert pnl < 0, f"SHORT at SL should have negative PnL, got {pnl}"
    assert abs(pnl - (-0.02)) < 1e-6, f"Expected ~-0.02, got {pnl}"
    print("  PASS: SHORT at SL yields negative PnL")


def test_won_status_always_implies_positive_pnl():
    """classify_outcome should return WON only for positive PnL above threshold."""
    # Positive PnL above threshold => WON
    assert classify_outcome(0.01) == "WON"
    assert classify_outcome(0.001) == "WON"
    assert classify_outcome(5.0) == "WON"

    # Negative PnL => LOST
    assert classify_outcome(-0.01) == "LOST"
    assert classify_outcome(-5.0) == "LOST"

    # Zero PnL => FLAT
    assert classify_outcome(0.0) == "FLAT"

    # Very small PnL (below threshold) => FLAT
    assert classify_outcome(0.000005) == "FLAT"
    assert classify_outcome(-0.000005) == "FLAT"

    print("  PASS: WON status always implies positive PnL")


def test_classify_outcome_non_crypto_threshold():
    """Non-crypto assets use 5bp threshold instead of 0.1bp."""
    # 3bp should be FLAT for non-crypto (below 5bp threshold)
    assert classify_outcome(0.0003, "FOREX") == "FLAT"
    assert classify_outcome(-0.0003, "FOREX") == "FLAT"

    # 6bp should be WON for non-crypto
    assert classify_outcome(0.0006, "FOREX") == "WON"
    assert classify_outcome(-0.0006, "FOREX") == "LOST"

    # Same 3bp is WON for crypto (above 0.1bp threshold)
    assert classify_outcome(0.0003, "CRYPTO") == "WON"

    print("  PASS: Non-crypto threshold (5bp) applied correctly")


def test_compute_pnl_direction_variants():
    """compute_pnl should handle various direction strings."""
    entry = 100.0
    exit_price = 110.0

    # LONG variants
    assert compute_pnl(entry, exit_price, "LONG") == 0.10
    assert compute_pnl(entry, exit_price, "BUY") == 0.10
    assert compute_pnl(entry, exit_price, "long") == 0.10

    # SHORT variants
    assert compute_pnl(entry, exit_price, "SHORT") == -0.10
    assert compute_pnl(entry, exit_price, "SELL") == -0.10
    assert compute_pnl(entry, exit_price, "short") == -0.10

    print("  PASS: Direction string variants handled correctly")


def test_compute_pnl_zero_entry():
    """compute_pnl should return 0 for zero/invalid entry."""
    assert compute_pnl(0, 100, "LONG") == 0.0
    assert compute_pnl(-1, 100, "LONG") == 0.0
    print("  PASS: Zero/negative entry returns 0 PnL")


def test_resolve_claude_gainer_ml_pnl_direction():
    """Verify _resolve_claude_gainer_ml_pick uses direction-aware PnL."""
    from alpha_engine.outcome_resolver import _resolve_claude_gainer_ml_pick

    # LONG pick: entry=100, live_price=103 (at TP=103) => TP hit => positive PnL
    pick_long = {
        "entry_price": 100.0,
        "take_profit": 103.0,
        "stop_loss": 97.0,
        "direction": "LONG",
        "status": "ACTIVE",
    }
    # The function writes pnl_pct into _original_pick, which defaults to {}
    # We need to provide a real dict for _original_pick to capture the result
    result_long = {}
    pick_long["_original_pick"] = result_long
    _resolve_claude_gainer_ml_pick(pick_long, live_price=103.0)
    assert result_long.get("pnl_pct") is not None, f"LONG pick was not resolved: {result_long}"
    assert result_long["pnl_pct"] > 0, f"LONG at TP should have positive PnL, got {result_long['pnl_pct']}"
    print(f"  PASS: LONG pick resolved with PnL={result_long['pnl_pct']}%")

    # SHORT pick: entry=100, live_price=97 (at TP=97) => TP hit => positive PnL
    pick_short = {
        "entry_price": 100.0,
        "take_profit": 97.0,
        "stop_loss": 103.0,
        "direction": "SHORT",
        "status": "ACTIVE",
    }
    result_short = {}
    pick_short["_original_pick"] = result_short
    _resolve_claude_gainer_ml_pick(pick_short, live_price=97.0)
    assert result_short.get("pnl_pct") is not None, f"SHORT pick was not resolved: {result_short}"
    assert result_short["pnl_pct"] > 0, f"SHORT at TP should have positive PnL, got {result_short['pnl_pct']}"
    print(f"  PASS: SHORT pick resolved with PnL={result_short['pnl_pct']}%")

    # SHORT pick hitting SL: entry=100, live_price=103 (at SL=103) => negative PnL
    pick_short_sl = {
        "entry_price": 100.0,
        "take_profit": 97.0,
        "stop_loss": 103.0,
        "direction": "SHORT",
        "status": "ACTIVE",
    }
    result_short_sl = {}
    pick_short_sl["_original_pick"] = result_short_sl
    _resolve_claude_gainer_ml_pick(pick_short_sl, live_price=103.0)
    assert result_short_sl.get("pnl_pct") is not None, f"SHORT SL pick was not resolved: {result_short_sl}"
    assert result_short_sl["pnl_pct"] < 0, f"SHORT at SL should have negative PnL, got {result_short_sl['pnl_pct']}"
    print(f"  PASS: SHORT SL hit resolved with PnL={result_short_sl['pnl_pct']}%")


def test_won_contradiction_invariant():
    """
    End-to-end invariant: if classify_outcome(pnl) == 'WON', then pnl must be > 0.
    This catches any future regression where the threshold logic could produce
    WON for negative PnL.
    """
    import random
    for _ in range(1000):
        pnl = random.uniform(-1.0, 1.0)
        for asset_class in ["CRYPTO", "FOREX", "EQUITY", "COMMODITY", None]:
            outcome = classify_outcome(pnl, asset_class)
            if outcome == "WON":
                assert pnl > 0, f"classify_outcome returned WON for negative PnL={pnl}, class={asset_class}"
            elif outcome == "LOST":
                assert pnl < 0, f"classify_outcome returned LOST for positive PnL={pnl}, class={asset_class}"
    print("  PASS: WON/LOST invariant holds across 5000 randomized cases")


def main():
    print("=" * 60)
    print("WON PnL Contradiction Tests")
    print("=" * 60)

    tests = [
        ("PnL formula — LONG positive", test_long_pnl_positive_when_exit_above_entry),
        ("PnL formula — LONG negative", test_long_pnl_negative_when_exit_below_entry),
        ("PnL formula — SHORT positive", test_short_pnl_positive_when_exit_below_entry),
        ("PnL formula — SHORT negative", test_short_pnl_negative_when_exit_above_entry),
        ("PnL formula — SHORT at TP", test_short_pnl_at_tp_is_positive),
        ("PnL formula — SHORT at SL", test_short_pnl_at_sl_is_negative),
        ("WON status invariant", test_won_status_always_implies_positive_pnl),
        ("Non-crypto threshold", test_classify_outcome_non_crypto_threshold),
        ("Direction string variants", test_compute_pnl_direction_variants),
        ("Zero entry edge case", test_compute_pnl_zero_entry),
        ("_resolve_claude_gainer_ml_pick direction-aware PnL", test_resolve_claude_gainer_ml_pnl_direction),
        ("WON contradiction invariant (fuzz)", test_won_contradiction_invariant),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"  FAIL: {name}: {e}")

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
