"""Tests for M-020: BOND walk-forward output path mirrors PR #940 COMMODITY pattern.

Verifies that walk_forward_by_class():
1. Filters BOND picks to BOND_ALLOWED_SYMBOLS (TLT, HYG)
2. Surfaces symbols_allowed and symbols_filtered_out on BOND result
3. BOND picks outside the allowlist are excluded from OOS-Sharpe calc
4. COMMODITY filtering is unaffected
"""
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest
from alpha_engine.walkforward_validator import (
    walk_forward_by_class,
    BOND_ALLOWED_SYMBOLS,
    COMMODITY_ALLOWED_SYMBOLS,
)


def _pick(asset_class, symbol, pnl_pct=1.0):
    return {
        "asset_class": asset_class,
        "symbol": symbol,
        "pnl_pct": pnl_pct,
        "timestamp": "2026-01-01T00:00:00Z",
        "_outcome": "TP_HIT",
    }


def _payload(picks):
    return {"picks": {"recent_closed": picks}}


def _bond_picks(n, sym="TLT", pnl=1.0):
    return [_pick("BOND", sym, pnl) for _ in range(n)]


def test_bond_allowed_symbols_defined():
    """BOND_ALLOWED_SYMBOLS must include all common bond instruments."""
    for sym in ("TLT", "HYG", "IEF", "SHY", "ZN=F", "ZB=F"):
        assert sym in BOND_ALLOWED_SYMBOLS, f"{sym} must be in BOND_ALLOWED_SYMBOLS"


def test_bond_result_has_symbols_allowed():
    """BOND result must include symbols_allowed when n >= min_trades."""
    picks = _bond_picks(10)
    payload = _payload(picks)
    # Use min_trades=5 for BOND, with small window config
    out = walk_forward_by_class(
        payload,
        class_config={"BOND": {"min_trades": 5, "train_size": 3, "test_size": 2, "step": 1}},
    )
    assert "BOND" in out, "BOND must appear in by_class output"
    assert "symbols_allowed" in out["BOND"], "BOND result must have symbols_allowed"
    assert "TLT" in out["BOND"]["symbols_allowed"]


def test_bond_result_has_symbols_filtered_out():
    """BOND result must surface symbols_filtered_out for non-allowlist picks."""
    allowed = _bond_picks(10, sym="TLT")
    blocked = _bond_picks(5, sym="BNDX")  # BNDX not in BOND_ALLOWED_SYMBOLS
    payload = _payload(allowed + blocked)
    out = walk_forward_by_class(
        payload,
        class_config={"BOND": {"min_trades": 5, "train_size": 3, "test_size": 2, "step": 1}},
    )
    assert "BOND" in out
    assert "BNDX" in out["BOND"].get("symbols_filtered_out", [])


def test_bond_non_allowlist_excluded_from_oos():
    """Non-allowlist BOND symbols must not contribute to the trade list."""
    only_blocked = _bond_picks(20, sym="BNDX")  # BNDX not in BOND_ALLOWED_SYMBOLS
    payload = _payload(only_blocked)
    out = walk_forward_by_class(
        payload,
        class_config={"BOND": {"min_trades": 5, "train_size": 3, "test_size": 2, "step": 1}},
    )
    # All BOND picks filtered out → should NOT appear in output (n=0 < min_trades=5)
    assert "BOND" not in out, "BOND with only blocked symbols must be absent (n below min_trades)"


def test_commodity_unaffected_by_m020():
    """COMMODITY filtering must remain unchanged after M-020."""
    assert "HG=F" in COMMODITY_ALLOWED_SYMBOLS
    assert "PL=F" in COMMODITY_ALLOWED_SYMBOLS


def test_bond_window_config_embedded():
    """BOND result must embed window_config provenance."""
    picks = _bond_picks(10)
    payload = _payload(picks)
    out = walk_forward_by_class(
        payload,
        class_config={"BOND": {"min_trades": 5, "train_size": 3, "test_size": 2, "step": 1}},
    )
    if "BOND" in out and isinstance(out["BOND"], dict):
        assert "window_config" in out["BOND"], "BOND result must have window_config"
        assert out["BOND"]["window_config"]["n_trades"] == 10
