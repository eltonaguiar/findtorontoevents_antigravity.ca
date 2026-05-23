"""Tests for alpha_engine.long_term_pick_contract."""
from __future__ import annotations

import pytest

from alpha_engine.long_term_pick_contract import (
    evaluate_thesis_break,
    is_long_term_value,
    is_swing,
    make_long_term_value_pick,
    make_swing_pick,
    validate_long_term_pick,
)

SAMPLE_FUNDAMENTAL_SNAPSHOT = {
    "pe": 12.4, "pb": 1.2, "ev_ebitda": 7.8, "roic": 0.18, "roe": 0.21,
    "fcf_yield": 0.085, "debt_to_equity": 0.42, "interest_coverage": 8.3,
    "piotroski_f": 8, "magic_formula_rank": 17, "acquirers_multiple": 6.4,
    "altman_z_double_prime": 3.2, "beneish_m": -2.45, "sloan_accruals_decile": 3,
}

SAMPLE_THESIS_BREAK_RULES = [
    {"metric": "ROIC", "op": "<", "threshold": 0.126, "source": "edgartools"},
    {"metric": "DebtToEquity", "op": ">", "threshold": 0.63, "source": "edgartools"},
    {"metric": "ConsecutiveEarningsMisses", "op": ">=", "threshold": 2, "source": "finnhub"},
]

SAMPLE_EARNINGS_HISTORY = [
    {"date": "2025-Q4", "eps_actual": 2.10, "eps_estimate": 2.05, "surprise_pct": 2.4},
    {"date": "2025-Q3", "eps_actual": 1.95, "eps_estimate": 1.90, "surprise_pct": 2.6},
]

SAMPLE_DIVIDEND_RECORD = {
    "annual_yield": 0.024, "payout_ratio": 0.35, "consecutive_growth_years": 12,
    "next_ex_div_date": "2026-05-15",
    "history_5y": [
        {"ex_date": "2026-02-15", "amount": 0.42},
        {"ex_date": "2025-11-15", "amount": 0.41},
    ],
}


def test_make_long_term_value_pick_has_required_fields():
    pick = make_long_term_value_pick(
        symbol="AAPL", direction="LONG", entry_price=180.50, intrinsic_value=215.00,
        thesis="Trades at 17x earnings vs sector 22x. ROIC 18% above sector median.",
        thesis_break_rules=SAMPLE_THESIS_BREAK_RULES,
        fundamental_snapshot=SAMPLE_FUNDAMENTAL_SNAPSHOT,
        earnings_history=SAMPLE_EARNINGS_HISTORY,
        next_earnings_date="2026-08-01",
        dividend_record=SAMPLE_DIVIDEND_RECORD,
        catalyst_dates=["2026-08-01"],
    )
    assert pick["pick_type"] == "long_term_value"
    assert pick["exit_mode"] == "thesis"
    assert pick["holding_horizon"] == "3y+"
    assert pick["intrinsic_value"] == 215.00
    assert pick["safety_gate_passed"] is True
    assert pick["universe_gate_passed"] is True
    assert is_long_term_value(pick) is True
    assert is_swing(pick) is False


def test_make_swing_pick_has_required_fields():
    pick = make_swing_pick(
        symbol="MSFT", direction="LONG", entry_price=410.00,
        take_profit=440.00, stop_loss=395.00,
        next_earnings_date="2026-07-25", catalyst_dates=["2026-07-25"],
    )
    assert pick["pick_type"] == "swing"
    assert pick["exit_mode"] == "tp_sl"
    assert pick["holding_horizon"] == "1m"
    assert pick["take_profit"] == 440.00
    assert pick["stop_loss"] == 395.00
    assert is_swing(pick) is True
    assert is_long_term_value(pick) is False


def test_long_term_value_rejects_empty_thesis():
    with pytest.raises(ValueError, match="non-empty thesis"):
        make_long_term_value_pick(
            symbol="AAPL", direction="LONG", entry_price=180.0, intrinsic_value=200.0,
            thesis="   ", thesis_break_rules=SAMPLE_THESIS_BREAK_RULES,
            fundamental_snapshot=SAMPLE_FUNDAMENTAL_SNAPSHOT,
            earnings_history=[], next_earnings_date=None,
            dividend_record={}, catalyst_dates=[],
        )


def test_long_term_value_rejects_empty_break_rules():
    with pytest.raises(ValueError, match="thesis_break_rule"):
        make_long_term_value_pick(
            symbol="AAPL", direction="LONG", entry_price=180.0, intrinsic_value=200.0,
            thesis="solid value", thesis_break_rules=[],
            fundamental_snapshot=SAMPLE_FUNDAMENTAL_SNAPSHOT,
            earnings_history=[], next_earnings_date=None,
            dividend_record={}, catalyst_dates=[],
        )


def test_long_term_value_rejects_zero_intrinsic_value():
    with pytest.raises(ValueError, match="intrinsic_value"):
        make_long_term_value_pick(
            symbol="AAPL", direction="LONG", entry_price=180.0, intrinsic_value=0.0,
            thesis="solid", thesis_break_rules=SAMPLE_THESIS_BREAK_RULES,
            fundamental_snapshot=SAMPLE_FUNDAMENTAL_SNAPSHOT,
            earnings_history=[], next_earnings_date=None,
            dividend_record={}, catalyst_dates=[],
        )


def test_long_term_value_rejects_failed_safety_gate():
    with pytest.raises(ValueError, match="safety_gate_passed"):
        make_long_term_value_pick(
            symbol="AAPL", direction="LONG", entry_price=180.0, intrinsic_value=200.0,
            thesis="solid", thesis_break_rules=SAMPLE_THESIS_BREAK_RULES,
            fundamental_snapshot=SAMPLE_FUNDAMENTAL_SNAPSHOT,
            earnings_history=[], next_earnings_date=None,
            dividend_record={}, catalyst_dates=[], safety_gate_passed=False,
        )


def test_validate_long_term_pick_returns_no_errors_for_valid_pick():
    pick = make_long_term_value_pick(
        symbol="AAPL", direction="LONG", entry_price=180.0, intrinsic_value=215.0,
        thesis="value thesis", thesis_break_rules=SAMPLE_THESIS_BREAK_RULES,
        fundamental_snapshot=SAMPLE_FUNDAMENTAL_SNAPSHOT,
        earnings_history=[], next_earnings_date=None,
        dividend_record={}, catalyst_dates=[],
    )
    assert validate_long_term_pick(pick) == []


def test_validate_long_term_pick_catches_wrong_pick_type():
    pick = make_swing_pick(
        symbol="MSFT", direction="LONG", entry_price=410.0,
        take_profit=440.0, stop_loss=395.0,
    )
    errors = validate_long_term_pick(pick)
    assert any("pick_type" in e for e in errors)


def test_validate_long_term_pick_catches_missing_snapshot():
    pick = {
        "pick_type": "long_term_value", "exit_mode": "thesis",
        "thesis": "solid", "thesis_break_rules": SAMPLE_THESIS_BREAK_RULES,
        "intrinsic_value": 200.0, "safety_gate_passed": True,
    }
    errors = validate_long_term_pick(pick)
    assert any("fundamental_snapshot" in e for e in errors)


def test_evaluate_thesis_break_no_trigger_when_metrics_healthy():
    pick = make_long_term_value_pick(
        symbol="AAPL", direction="LONG", entry_price=180.0, intrinsic_value=215.0,
        thesis="value thesis", thesis_break_rules=SAMPLE_THESIS_BREAK_RULES,
        fundamental_snapshot=SAMPLE_FUNDAMENTAL_SNAPSHOT,
        earnings_history=[], next_earnings_date=None,
        dividend_record={}, catalyst_dates=[],
    )
    current = {"ROIC": 0.17, "DebtToEquity": 0.45, "ConsecutiveEarningsMisses": 0}
    broken, triggered = evaluate_thesis_break(pick, current)
    assert broken is False
    assert triggered == []


def test_evaluate_thesis_break_triggers_on_roic_collapse():
    pick = make_long_term_value_pick(
        symbol="AAPL", direction="LONG", entry_price=180.0, intrinsic_value=215.0,
        thesis="value thesis", thesis_break_rules=SAMPLE_THESIS_BREAK_RULES,
        fundamental_snapshot=SAMPLE_FUNDAMENTAL_SNAPSHOT,
        earnings_history=[], next_earnings_date=None,
        dividend_record={}, catalyst_dates=[],
    )
    current = {"ROIC": 0.10, "DebtToEquity": 0.45, "ConsecutiveEarningsMisses": 0}
    broken, triggered = evaluate_thesis_break(pick, current)
    assert broken is True
    assert len(triggered) == 1
    assert "ROIC" in triggered[0]


def test_evaluate_thesis_break_returns_false_for_swing_pick():
    pick = make_swing_pick(
        symbol="MSFT", direction="LONG", entry_price=410.0,
        take_profit=440.0, stop_loss=395.0,
    )
    broken, triggered = evaluate_thesis_break(pick, {"ROIC": 0.0})
    assert broken is False
    assert triggered == []


def test_evaluate_thesis_break_skips_unknown_metrics_quietly():
    pick = make_long_term_value_pick(
        symbol="AAPL", direction="LONG", entry_price=180.0, intrinsic_value=215.0,
        thesis="value thesis", thesis_break_rules=SAMPLE_THESIS_BREAK_RULES,
        fundamental_snapshot=SAMPLE_FUNDAMENTAL_SNAPSHOT,
        earnings_history=[], next_earnings_date=None,
        dividend_record={}, catalyst_dates=[],
    )
    broken, triggered = evaluate_thesis_break(pick, {})
    assert broken is False
    assert triggered == []


def test_old_picks_unchanged_no_pick_type_field():
    old_pick = {
        "symbol": "DOTUSDT", "direction": "SHORT", "entry_price": 1.2587,
        "take_profit": 1.2452, "stop_loss": 1.2699,
        "asset_class": "CRYPTO", "source_system": "genome",
        "strategy": "mega_mutation", "status": "ACTIVE",
    }
    assert is_long_term_value(old_pick) is False
    assert is_swing(old_pick) is False
    errors = validate_long_term_pick(old_pick)
    assert len(errors) > 0
    broken, _ = evaluate_thesis_break(old_pick, {})
    assert broken is False
