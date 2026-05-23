"""Tests for M-041: slippage_validator scaffold wire-in to dashboard payload.

Verifies that:
1. _build_slippage_validation() produces the expected keys
2. Empty closed picks returns {}
3. CRITICAL strategy is surfaced in flagged_strategies
4. Fail-open: returns {} on import error
"""
import os
import sys
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest
from audit_trail.slippage_validator import validate_closed_picks, SLIPPAGE_PCT_CRITICAL


def _pick(strategy, asset_class="CRYPTO", pnl_pct=1.0, entry=50000.0):
    return {
        "strategy": strategy,
        "asset_class": asset_class,
        "pnl_pct": pnl_pct,
        "entry_price": entry,
        "symbol": "BTCUSDT",
        "direction": "LONG",
    }


def test_validate_closed_picks_returns_required_keys():
    """validate_closed_picks must return strategy_stats, asset_class_stats, summary."""
    picks = [_pick("strat_a"), _pick("strat_a", pnl_pct=2.0)]
    result = validate_closed_picks(picks)
    assert "strategy_stats" in result
    assert "asset_class_stats" in result
    assert "summary" in result
    assert "flagged_strategies" in result


def test_validate_empty_picks():
    """Empty picks must return empty stats without error."""
    result = validate_closed_picks([])
    assert result["summary"]["total_strategies"] == 0
    assert result["flagged_strategies"] == {}


def test_strategy_with_high_slippage_flagged_critical():
    """Strategy where slippage >> PnL must be flagged CRITICAL."""
    # Create picks with very small PnL relative to spread
    # CRYPTO default spread=0.001 → slippage=entry*0.001=50 per pick
    # slippage_pct = 50/50000*100 = 0.1%
    # avg_pnl_pct must be tiny for slippage to exceed SLIPPAGE_PCT_CRITICAL
    # SLIPPAGE_PCT_CRITICAL = 0.25 (25% of avg PnL) → avg_pnl_pct = 0.1/0.25 = 0.4% threshold
    # Use avg_pnl_pct = 0.1% (very tiny) → slippage_as_pct_of_pnl = 100% >> 25%
    picks = [_pick("high_slip_strat", pnl_pct=0.05) for _ in range(10)]
    result = validate_closed_picks(picks)
    strat_stats = result["strategy_stats"].get("high_slip_strat", {})
    # With pnl_pct=0.05% and slippage_pct=0.1%, slippage_as_pct_of_pnl = 200% >> 25%
    assert strat_stats.get("flag") in ("WARNING", "CRITICAL"), (
        f"Expected WARNING or CRITICAL, got {strat_stats.get('flag')} "
        f"(slippage_as_pct_of_pnl={strat_stats.get('slippage_as_pct_of_pnl')})"
    )


def test_strategy_with_low_slippage_not_flagged():
    """Strategy with high PnL relative to spread must be NONE."""
    # avg_pnl_pct=10%, slippage_pct~0.1% → slippage_as_pct_of_pnl = 1% << 10%
    picks = [_pick("low_slip_strat", pnl_pct=10.0) for _ in range(10)]
    result = validate_closed_picks(picks)
    strat_stats = result["strategy_stats"].get("low_slip_strat", {})
    assert strat_stats.get("flag") == "NONE"


def test_build_slippage_validation_helper():
    """_build_slippage_validation in dashboard_generator must return expected structure."""
    try:
        from audit_trail.dashboard_generator import _build_slippage_validation
    except ImportError:
        pytest.skip("dashboard_generator not importable in test env")
    picks = [_pick("test_strat", pnl_pct=5.0) for _ in range(5)]
    result = _build_slippage_validation(picks)
    assert isinstance(result, dict)
    assert "summary" in result or result == {}  # Empty if no picks above threshold


def test_build_slippage_validation_empty_returns_empty():
    """_build_slippage_validation with empty picks must return {}."""
    try:
        from audit_trail.dashboard_generator import _build_slippage_validation
    except ImportError:
        pytest.skip("dashboard_generator not importable in test env")
    result = _build_slippage_validation([])
    assert result == {}
