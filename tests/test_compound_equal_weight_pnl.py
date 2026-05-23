"""Headline sum vs equal-weight compounded capped PnL% (audit dashboard)."""

from audit_trail.dashboard_generator import _compound_equal_weight_capped_sequence


def test_compound_two_positive_trades_order_invariant_for_equal_returns():
    a = [{"timestamp": "2026-01-01T00:00:00", "symbol": "A", "pnl_pct": 10.0}]
    b = [{"timestamp": "2026-01-02T00:00:00", "symbol": "B", "pnl_pct": 10.0}]
    trades = a + b
    assert _compound_equal_weight_capped_sequence(trades, 500.0) == 21.0


def test_compound_applies_500_cap():
    trades = [
        {"timestamp": "2026-01-01T00:00:00", "symbol": "X", "pnl_pct": 800.0},
    ]
    assert _compound_equal_weight_capped_sequence(trades, 500.0) == 500.0


def test_compound_empty_is_zero():
    assert _compound_equal_weight_capped_sequence([], 500.0) == 0.0
