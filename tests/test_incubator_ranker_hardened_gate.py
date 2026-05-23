"""Tests for hardened incubator graduation gate (MASTER_ENHANCEMENT_PLAN P1 2026-05-18).

Verifies:
 - MIN_WIN_RATE raised to 0.50 (from 0.45)
 - MIN_TRADES raised to 20 (from 10)
 - Symbol sign-consistency gate: ≥60% of tested symbols must have Sharpe > 0
   (only applies when ≥4 symbols are tested)
"""
from __future__ import annotations

import pytest

from alpha_engine.incubator.ranker import (
    MIN_DSR_PROB,
    MIN_SYMBOL_SIGN_CONSISTENCY,
    MIN_SYMBOLS_FOR_CONSISTENCY,
    MIN_TRADES,
    MIN_WIN_RATE,
    RankedCandidate,
    _check_paper_ready,
)


def _candidate(**kwargs) -> RankedCandidate:
    defaults = dict(
        perm_id="test-perm",
        archetype="test",
        params={},
        seed_strategy="test_strat",
        combined_sharpe=2.0,
        combined_max_dd=0.05,
        combined_pf=1.8,
        combined_wr=0.55,
        combined_trades=25,
        combined_return=0.20,
    )
    defaults.update(kwargs)
    return RankedCandidate(**defaults)


class TestRaisedThresholds:
    def test_min_win_rate_is_fifty_percent(self):
        assert MIN_WIN_RATE == 0.50

    def test_min_trades_is_twenty(self):
        assert MIN_TRADES == 20

    def test_candidate_below_wr_threshold_rejected(self):
        c = _candidate(combined_wr=0.49)
        _check_paper_ready(c)
        assert not c.ready_for_paper
        assert any("WinRate" in r for r in c.rejection_reasons)

    def test_candidate_at_wr_threshold_not_rejected_for_wr(self):
        c = _candidate(combined_wr=0.50)
        _check_paper_ready(c)
        assert not any("WinRate" in r for r in c.rejection_reasons)

    def test_candidate_below_trades_threshold_rejected(self):
        c = _candidate(combined_trades=15)
        _check_paper_ready(c)
        assert not c.ready_for_paper
        assert any("Trades" in r for r in c.rejection_reasons)

    def test_candidate_at_trades_threshold_not_rejected_for_trades(self):
        c = _candidate(combined_trades=20)
        _check_paper_ready(c)
        assert not any("Trades" in r for r in c.rejection_reasons)


class TestSymbolSignConsistency:
    def test_constants_correct(self):
        assert MIN_SYMBOL_SIGN_CONSISTENCY == 0.60
        assert MIN_SYMBOLS_FOR_CONSISTENCY == 4

    def test_consistency_gate_not_applied_below_min_symbols(self):
        # With only 3 symbols, gate should not apply even if 0/3 are positive
        c = _candidate(per_symbol={
            "SYM1": {"sharpe": -0.5},
            "SYM2": {"sharpe": -0.3},
            "SYM3": {"sharpe": -0.1},
        })
        _check_paper_ready(c)
        assert not any("SymbolConsistency" in r for r in c.rejection_reasons)

    def test_consistency_gate_applied_with_four_symbols(self):
        # 1/4 = 25% positive — below 60% threshold → rejected
        c = _candidate(per_symbol={
            "SYM1": {"sharpe": 1.5},
            "SYM2": {"sharpe": -0.5},
            "SYM3": {"sharpe": -0.3},
            "SYM4": {"sharpe": -0.1},
        })
        _check_paper_ready(c)
        assert not c.ready_for_paper
        assert any("SymbolConsistency" in r for r in c.rejection_reasons)

    def test_consistency_gate_passes_with_three_of_four_positive(self):
        # 3/4 = 75% positive — above 60% threshold → no consistency rejection
        c = _candidate(per_symbol={
            "SYM1": {"sharpe": 1.5},
            "SYM2": {"sharpe": 0.8},
            "SYM3": {"sharpe": 0.3},
            "SYM4": {"sharpe": -0.1},
        })
        _check_paper_ready(c)
        assert not any("SymbolConsistency" in r for r in c.rejection_reasons)

    def test_consistency_gate_passes_with_all_positive(self):
        c = _candidate(per_symbol={
            f"SYM{i}": {"sharpe": 0.5 + i * 0.1} for i in range(6)
        })
        _check_paper_ready(c)
        assert not any("SymbolConsistency" in r for r in c.rejection_reasons)

    def test_candidate_passes_all_gates_when_strong(self):
        c = _candidate(
            combined_wr=0.60,
            combined_trades=30,
            combined_sharpe=2.5,
            combined_max_dd=0.08,
            per_symbol={
                f"SYM{i}": {"sharpe": 1.0 + i * 0.2} for i in range(5)
            },
        )
        _check_paper_ready(c)
        # DSR gate might reject depending on n_trials, but Sharpe/WR/Trades/Consistency should pass
        non_dsr_reasons = [r for r in c.rejection_reasons if "DSR" not in r]
        assert non_dsr_reasons == []
