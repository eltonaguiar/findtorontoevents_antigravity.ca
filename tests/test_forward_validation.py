"""Tests for audit_trail.forward_validation."""

import pytest

from audit_trail.forward_validation import (
    FV_MIN_N,
    FV_MIN_PF,
    FV_MIN_WR,
    apply_ledger_validation,
    evaluate,
    ledger_stats,
)


def test_thresholds_are_the_documented_bar():
    assert (FV_MIN_N, FV_MIN_WR, FV_MIN_PF) == (20, 45.0, 1.0)


def test_evaluate_accepts_a_positive_forward_sample():
    ok, reason = evaluate(20, 45.0, 1.0)
    assert ok is True
    assert reason.startswith("ok:")


def test_evaluate_rejects_thin_sample_even_with_great_wr():
    ok, reason = evaluate(19, 90.0, 5.0)
    assert ok is False
    assert reason.startswith("insufficient_sample")


def test_evaluate_rejects_losing_strategy():
    ok, reason = evaluate(60, 38.0, 0.7)
    assert ok is False


def test_evaluate_requires_known_pf():
    ok, reason = evaluate(30, 55.0, None)
    assert ok is False
    assert reason.startswith("pf_unknown")


def test_ledger_stats_ignores_flat_and_computes_pf():
    stats = ledger_stats([2.0, -1.0, 0.0, 4.0])
    assert stats["n"] == 3
    assert stats["wr"] == pytest.approx(66.6667, abs=1e-3)
    assert stats["pf"] == pytest.approx(6.0)


def test_promote_emitter_false_when_ledger_qualifies():
    pick = {"forward_validated": False}
    change = apply_ledger_validation(pick, {"n": 40, "wr": 52.0, "pf": 1.4})
    assert change == "promoted"
    assert pick["forward_validated"] is True
    assert pick["forward_validated_basis"] == "strategy_ledger"


def test_no_change_when_already_true_and_valid():
    pick = {"forward_validated": True}
    assert apply_ledger_validation(pick, {"n": 40, "wr": 60.0, "pf": 2.0}) is None


def test_demote_emitter_true_when_ledger_has_enough_rows_and_loses():
    pick = {"forward_validated": True}
    change = apply_ledger_validation(pick, {"n": 55, "wr": 31.0, "pf": 0.4})
    assert change == "demoted"
    assert pick["forward_validated"] is False


def test_do_not_demote_on_a_thin_ledger():
    pick = {"forward_validated": True}
    assert apply_ledger_validation(pick, {"n": 4, "wr": 0.0, "pf": 0.0}) is None
