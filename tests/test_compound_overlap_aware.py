"""Tests for overlap-aware compounding (Sub-project 1, Task 3).

The old model compounds trades sequentially as if each used 100% of capital.
These tests lock in the corrected behaviour: concurrent positions share capital.
"""
from __future__ import annotations

import pytest


def test_two_overlapping_trades_share_capital():
    """Two trades open at the same time must each get 50% of capital, not 100%."""
    from audit_trail.compound_overlap_aware import compound_overlap_aware

    picks = [
        {"entry_time": "2026-01-01T10:00:00Z", "closed_at": "2026-01-01T12:00:00Z", "pnl_pct": 10.0},
        {"entry_time": "2026-01-01T10:00:00Z", "closed_at": "2026-01-01T12:00:00Z", "pnl_pct": 10.0},
    ]
    pct, diag = compound_overlap_aware(picks, max_pnl_pct=100.0)
    # Each gets 50% of capital: equity = 1.0 * (1 + 0.5*0.10) * (1 + 0.5*0.10) = 1.1025
    assert pct == pytest.approx(10.25, abs=0.05), f"got {pct}"
    assert diag["max_concurrency"] == 2
    assert diag["n_timed"] == 2
    assert diag["n_untimed"] == 0


def test_sequential_trades_match_old_model_when_no_overlap():
    """With zero overlap, the new model must reproduce the old sequential number."""
    from audit_trail.compound_overlap_aware import compound_overlap_aware

    picks = [
        {"entry_time": "2026-01-01T10:00:00Z", "closed_at": "2026-01-01T11:00:00Z", "pnl_pct": 3.0},
        {"entry_time": "2026-01-01T11:00:00Z", "closed_at": "2026-01-01T12:00:00Z", "pnl_pct": -2.0},
    ]
    pct, diag = compound_overlap_aware(picks, max_pnl_pct=100.0)
    # Sequential: (1.03 * 0.98) - 1 = 0.94%
    assert pct == pytest.approx(0.94, abs=0.02), f"got {pct}"
    assert diag["max_concurrency"] == 1
    assert diag["distortion_pp"] == pytest.approx(0.0, abs=0.02)


def test_same_instant_batch_is_concurrent_not_sequential():
    """A resolver batch close (identical timestamps) must register as concurrency."""
    from audit_trail.compound_overlap_aware import compound_overlap_aware

    picks = [
        {"entry_time": "2026-01-01T00:00:00Z", "closed_at": "2026-01-05T00:00:00Z", "pnl_pct": 5.0}
        for _ in range(10)
    ]
    pct, diag = compound_overlap_aware(picks, max_pnl_pct=100.0)
    assert diag["max_concurrency"] == 10, "batch close must be detected as 10 concurrent"
    # Each is 1/10 of capital: equity = (1 + 0.05/10)^10 = 1.005^10
    assert pct == pytest.approx(5.114, abs=0.1), f"got {pct}"
    # The sequential model would have said 62.9% -- distortion must be large
    assert diag["distortion_pp"] > 50.0


def test_max_pnl_cap_is_applied():
    """Per-trade PnL must be clipped to +/- max_pnl_pct."""
    from audit_trail.compound_overlap_aware import compound_overlap_aware

    picks = [{"entry_time": "2026-01-01T00:00:00Z", "closed_at": "2026-01-01T01:00:00Z", "pnl_pct": 999.0}]
    pct, _diag = compound_overlap_aware(picks, max_pnl_pct=10.0)
    assert pct == pytest.approx(10.0, abs=0.05), f"got {pct}"


def test_untimed_rows_do_not_crash_and_are_counted():
    """Rows with no usable timestamps must not break the function."""
    from audit_trail.compound_overlap_aware import compound_overlap_aware

    picks = [
        {"entry_time": "2026-01-01T00:00:00Z", "closed_at": "2026-01-01T01:00:00Z", "pnl_pct": 2.0},
        {"pnl_pct": 1.0},  # no timestamps at all
        {"entry_time": "not-a-date", "closed_at": "", "pnl_pct": 0.5},
    ]
    pct, diag = compound_overlap_aware(picks, max_pnl_pct=100.0)
    assert isinstance(pct, float)
    assert diag["n_untimed"] == 2
    assert diag["n_timed"] == 1


def test_net_of_cost_field_preferred_over_gross():
    """When net_of_cost_pnl_pct is present, the model must use it, not gross pnl_pct."""
    from audit_trail.compound_overlap_aware import compound_overlap_aware

    picks = [
        {
            "entry_time": "2026-01-01T00:00:00Z",
            "closed_at": "2026-01-01T01:00:00Z",
            "pnl_pct": 10.0,
            "net_of_cost_pnl_pct": 4.0,
        }
    ]
    pct, _diag = compound_overlap_aware(picks, max_pnl_pct=100.0)
    assert pct == pytest.approx(4.0, abs=0.05), f"got {pct}"


def test_empty_input_returns_zero():
    from audit_trail.compound_overlap_aware import compound_overlap_aware
    pct, diag = compound_overlap_aware([], max_pnl_pct=10.0)
    assert pct == 0.0
    assert diag["n_trades"] == 0
