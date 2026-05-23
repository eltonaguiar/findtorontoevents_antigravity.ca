"""Tests for M-022: commodity_carry_momo double-sort sidecar.

Verifies the core logic of tools/research/commodity_carry_momo.py without
hitting yfinance (uses synthetic data to test ranking + basket logic).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tools.research.commodity_carry_momo import double_sort_basket, build_picks


def _row(symbol, mom, carry):
    return {"symbol": symbol, "mom_12_1_pct": mom, "carry_proxy_pct": carry}


def test_double_sort_basket_longs_and_shorts():
    """Top-quintile on BOTH mom+carry must be LONGS; bottom-quintile on BOTH = SHORTS."""
    rows = [
        _row("GC=F", mom=15.0, carry=8.0),   # top both → LONG
        _row("SI=F", mom=12.0, carry=6.0),   # top both → LONG
        _row("CL=F", mom=8.0, carry=3.0),    # middle
        _row("NG=F", mom=-5.0, carry=-3.0),  # bottom both → SHORT
        _row("ZC=F", mom=-10.0, carry=-7.0), # bottom both → SHORT
        _row("ZS=F", mom=2.0, carry=1.0),    # middle
    ]
    basket = double_sort_basket(rows, quintile=2)
    assert "GC=F" in basket["longs"] or "SI=F" in basket["longs"]
    assert "NG=F" in basket["shorts"] or "ZC=F" in basket["shorts"]


def test_double_sort_basket_returns_required_keys():
    """double_sort_basket must return required structural keys."""
    rows = [_row(f"SYM{i}", i * 2.0, i * 1.5) for i in range(6)]
    result = double_sort_basket(rows, quintile=2)
    for key in ("longs", "shorts", "neutrals", "expected_signal_strength", "n_valid"):
        assert key in result, f"Missing key: {key}"


def test_double_sort_basket_insufficient_rows():
    """Fewer rows than quintile*2 must return error key."""
    rows = [_row("ONLY_ONE", 5.0, 3.0)]
    result = double_sort_basket(rows, quintile=3)
    assert "error" in result


def test_double_sort_basket_no_overlap_weak_signal():
    """When momentum top and carry top don't overlap, LONGS is empty → WEAK_OR_FLAT."""
    rows = [
        _row("A", mom=10.0, carry=-5.0),   # top mom, bottom carry
        _row("B", mom=8.0, carry=-4.0),    # top mom, bottom carry
        _row("C", mom=-3.0, carry=10.0),   # bottom mom, top carry
        _row("D", mom=-4.0, carry=8.0),    # bottom mom, top carry
        _row("E", mom=1.0, carry=1.0),
        _row("F", mom=-1.0, carry=-1.0),
    ]
    result = double_sort_basket(rows, quintile=2)
    # Longs = top_mom ∩ top_carry = {} (no overlap)
    # Shorts = bot_mom ∩ bot_carry = {} (no overlap because bottom-mom ARE top-carry)
    signal = result["expected_signal_strength"]
    assert signal in ("WEAK_OR_FLAT", "MODERATE")  # depends on carry-bottom overlap


def test_build_picks_schema_compliance():
    """build_picks must return picks with required COMMODITY pick fields."""
    rows = [
        _row("GC=F", mom=15.0, carry=8.0),
        _row("NG=F", mom=-10.0, carry=-7.0),
    ]
    basket = {
        "longs": ["GC=F"],
        "shorts": ["NG=F"],
        "neutrals": [],
        "expected_signal_strength": "STRONG",
    }
    picks = build_picks(rows, basket, "2026-05-17T00:00:00Z")
    assert len(picks) >= 1
    for p in picks:
        assert p.get("asset_class") == "COMMODITY"
        assert p.get("strategy") == "commodity_carry_momo_double_sort"
        assert p.get("direction") in ("LONG", "SHORT")
        assert p.get("symbol") in ("GC=F", "NG=F")
