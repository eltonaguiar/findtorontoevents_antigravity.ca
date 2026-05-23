"""Tests for Phase 15 short-side screener.

Covers:
  - Pure-function trigger detectors (Beneish / Altman / Sloan)
  - ShortSideScreener.score_one trigger-count logic
  - ShortSideScreener.screen_universe pick emission + factory contract
"""
from __future__ import annotations

import pytest

from alpha_engine.fundamentals_fetcher import FundamentalsRecord
from alpha_engine.long_term_pick_contract import validate_long_term_pick
from alpha_engine.short_side_screener import (
    ShortSideScore,
    ShortSideScreener,
    compute_sloan_accruals,
    is_altman_distressed,
    is_beneish_top_decile,
    is_sloan_top_decile,
)


# =============================================================================
# Fixtures
# =============================================================================
def _make_record(
    *,
    revenue: float | None = 1_000.0,
    net_income: float | None = 100.0,
    operating_cash_flow: float | None = 110.0,
    total_assets: float | None = 1_000.0,
    total_liabilities: float | None = 400.0,
    stockholders_equity: float | None = 600.0,
    current_assets: float | None = 300.0,
    current_liabilities: float | None = 150.0,
    long_term_debt: float | None = 200.0,
    ebit: float | None = 150.0,
    da: float | None = 30.0,
    interest_expense: float | None = 10.0,
    cash: float | None = 80.0,
    shares: float | None = 1_000.0,
) -> FundamentalsRecord:
    rec = FundamentalsRecord(ticker="TEST", source="test", period="2025-Q4")
    rec.income_statement = {
        "revenue": revenue,
        "net_income": net_income,
        "operating_income": ebit,
        "ebit": ebit,
        "ebitda_proxy_da": da,
        "interest_expense": interest_expense,
        "income_tax_expense": 20.0,
    }
    rec.balance_sheet = {
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "stockholders_equity": stockholders_equity,
        "current_assets": current_assets,
        "current_liabilities": current_liabilities,
        "long_term_debt": long_term_debt,
        "cash_and_equivalents": cash,
        "shares_outstanding": shares,
    }
    rec.cash_flow = {
        "operating_cash_flow": operating_cash_flow,
        "capex": -50.0,
        "dividends_paid": -20.0,
    }
    return rec


def _healthy_record() -> FundamentalsRecord:
    """Healthy company: high Z'', cash > NI, low accruals."""
    return _make_record(
        revenue=1_000.0,
        net_income=100.0,
        operating_cash_flow=140.0,  # OCF > NI: low accruals
        total_assets=1_000.0,
        total_liabilities=200.0,    # low leverage -> high Z''
        stockholders_equity=800.0,
        current_assets=500.0,
        current_liabilities=100.0,
        long_term_debt=100.0,
        ebit=180.0,
        da=30.0,
    )


def _altman_distressed_record() -> FundamentalsRecord:
    """Distressed: low equity, high liabilities, low EBIT -> Z'' < 1.10."""
    return _make_record(
        revenue=1_000.0,
        net_income=20.0,
        operating_cash_flow=25.0,
        total_assets=1_000.0,
        total_liabilities=950.0,
        stockholders_equity=50.0,
        current_assets=120.0,
        current_liabilities=400.0,
        long_term_debt=550.0,
        ebit=10.0,
        da=10.0,
    )


def _sloan_high_accruals_record() -> FundamentalsRecord:
    """High Sloan accruals: NI=200, CFO=20, TA=1000 -> 0.18 (>0.10)."""
    return _make_record(
        net_income=200.0,
        operating_cash_flow=20.0,
        total_assets=1_000.0,
    )


# =============================================================================
# 1-3. Beneish top-decile detector
# =============================================================================
def test_is_beneish_top_decile_true_above_threshold():
    assert is_beneish_top_decile(-1.5) is True


def test_is_beneish_top_decile_false_safe_value():
    assert is_beneish_top_decile(-2.5) is False


def test_is_beneish_top_decile_handles_none():
    assert is_beneish_top_decile(None) is False


# =============================================================================
# 4-5. Altman distress detector
# =============================================================================
def test_is_altman_distressed_true_below_threshold():
    assert is_altman_distressed(1.0) is True


def test_is_altman_distressed_false_at_safe_value():
    assert is_altman_distressed(3.0) is False


def test_is_altman_distressed_handles_none():
    assert is_altman_distressed(None) is False


# =============================================================================
# 6-7. Sloan accruals computation
# =============================================================================
def test_compute_sloan_accruals_basic():
    rec = _make_record(
        net_income=10.0,
        operating_cash_flow=5.0,
        total_assets=100.0,
    )
    result = compute_sloan_accruals(rec)
    assert result is not None
    assert result == pytest.approx(0.05, abs=1e-9)


def test_compute_sloan_accruals_returns_none_for_missing_inputs():
    rec_no_ni = _make_record(net_income=None)
    rec_no_cfo = _make_record(operating_cash_flow=None)
    rec_no_ta = _make_record(total_assets=None)
    rec_zero_ta = _make_record(total_assets=0.0)

    assert compute_sloan_accruals(rec_no_ni) is None
    assert compute_sloan_accruals(rec_no_cfo) is None
    assert compute_sloan_accruals(rec_no_ta) is None
    assert compute_sloan_accruals(rec_zero_ta) is None


def test_is_sloan_top_decile_true_at_threshold():
    assert is_sloan_top_decile(0.18) is True
    assert is_sloan_top_decile(0.10) is True


def test_is_sloan_top_decile_false_below():
    assert is_sloan_top_decile(0.05) is False
    assert is_sloan_top_decile(None) is False


# =============================================================================
# 8-11. score_one trigger-count logic
# =============================================================================
def test_score_one_clean_company_no_triggers():
    screener = ShortSideScreener()
    rec = _healthy_record()
    score = screener.score_one("CLEAN", rec, prior_record=None)
    assert isinstance(score, ShortSideScore)
    assert score.signal_quality == "clean"
    assert score.total_triggers == 0
    assert score.beneish_top_decile is False
    assert score.altman_distressed is False
    assert score.sloan_top_decile is False


def test_score_one_one_trigger_blocks_long_only():
    """Distressed Altman only; healthy Sloan; Beneish None (no prior) -> 1 trigger."""
    screener = ShortSideScreener()
    rec = _altman_distressed_record()
    # Override CFO so accruals stay below 0.10 (NI=20, CFO=25 -> -0.005).
    score = screener.score_one("ONETRIG", rec, prior_record=None)
    assert score.altman_distressed is True
    assert score.beneish_top_decile is False  # None -> False
    assert score.sloan_top_decile is False
    assert score.total_triggers == 1
    assert score.signal_quality == "long_block_only"
    assert score.rejection_reason == "insufficient_short_triggers_block_long_only"


def test_score_one_two_triggers_short_candidate():
    """Altman distressed + Sloan high -> 2 triggers."""
    screener = ShortSideScreener()
    # Distressed Altman fundamentals AND high accruals (NI=100, CFO=-50, TA=1000 -> 0.15).
    rec = _make_record(
        revenue=1_000.0,
        net_income=100.0,
        operating_cash_flow=-50.0,
        total_assets=1_000.0,
        total_liabilities=950.0,
        stockholders_equity=50.0,
        current_assets=120.0,
        current_liabilities=400.0,
        long_term_debt=550.0,
        ebit=10.0,
        da=10.0,
    )
    score = screener.score_one("TWOTRIG", rec, prior_record=None)
    assert score.altman_distressed is True
    assert score.sloan_top_decile is True
    assert score.total_triggers >= 2
    assert score.signal_quality == "short_candidate"
    assert score.rejection_reason is None


def test_score_one_three_triggers_short_candidate():
    """Distressed + high Sloan + high Beneish (with prior) -> 3 triggers."""
    screener = ShortSideScreener()
    # Configure cur and prior so Beneish M ends up >= -1.78.
    # Beneish is dominated by SGI (sales growth) and TATA ((NI-OCF)/TA).
    # SGI=2.0 (revenue doubled), TATA=0.15 (NI=100, OCF=-50, TA=1000) push M up.
    cur = _make_record(
        revenue=2_000.0,
        net_income=100.0,
        operating_cash_flow=-50.0,
        total_assets=1_000.0,
        total_liabilities=950.0,
        stockholders_equity=50.0,
        current_assets=120.0,
        current_liabilities=400.0,
        long_term_debt=550.0,
        ebit=10.0,
        da=10.0,
    )
    prior = _make_record(
        revenue=1_000.0,
        net_income=80.0,
        operating_cash_flow=70.0,
        total_assets=900.0,
        total_liabilities=600.0,
        stockholders_equity=300.0,
        current_assets=200.0,
        current_liabilities=200.0,
        long_term_debt=400.0,
        ebit=80.0,
        da=15.0,
    )
    score = screener.score_one("THREETRIG", cur, prior_record=prior)
    assert score.altman_distressed is True
    assert score.sloan_top_decile is True
    assert score.beneish_top_decile is True
    assert score.total_triggers == 3
    assert score.signal_quality == "short_candidate"


# =============================================================================
# 12-14. screen_universe + pick emission + factory contract
# =============================================================================
def _two_trigger_record() -> FundamentalsRecord:
    return _make_record(
        revenue=1_000.0,
        net_income=100.0,
        operating_cash_flow=-50.0,
        total_assets=1_000.0,
        total_liabilities=950.0,
        stockholders_equity=50.0,
        current_assets=120.0,
        current_liabilities=400.0,
        long_term_debt=550.0,
        ebit=10.0,
        da=10.0,
    )


def test_screen_universe_emits_short_picks_with_correct_direction():
    """5 inputs: 2 short candidates, 1 long-block, 2 clean -> 2 SHORT picks."""
    screener = ShortSideScreener()
    universe: list[
        tuple[str, FundamentalsRecord, FundamentalsRecord | None]
    ] = [
        ("SHORT1", _two_trigger_record(), None),
        ("SHORT2", _two_trigger_record(), None),
        ("BLOCK1", _altman_distressed_record(), None),  # 1 trigger
        ("CLEAN1", _healthy_record(), None),
        ("CLEAN2", _healthy_record(), None),
    ]
    prices = {"SHORT1": 50.0, "SHORT2": 100.0, "BLOCK1": 25.0,
              "CLEAN1": 40.0, "CLEAN2": 60.0}
    picks = screener.screen_universe(universe, top_n=20, current_prices=prices)

    assert len(picks) == 2
    assert all(p["direction"] == "SHORT" for p in picks)
    emitted_symbols = {p["symbol"] for p in picks}
    assert emitted_symbols == {"SHORT1", "SHORT2"}


def test_short_pick_thesis_explains_triggers():
    """Thesis must mention which triggers fired by name."""
    screener = ShortSideScreener()
    universe = [("SHORT1", _two_trigger_record(), None)]
    picks = screener.screen_universe(universe, top_n=5,
                                     current_prices={"SHORT1": 50.0})
    assert len(picks) == 1
    thesis = picks[0]["thesis"]
    assert isinstance(thesis, str) and thesis.strip()
    assert thesis.startswith("SHORT:")
    # At least one of the trigger-name keywords must appear.
    assert (
        "Beneish" in thesis
        or "Altman" in thesis
        or "Sloan" in thesis
    ), f"thesis missing trigger names: {thesis}"


def test_short_pick_passes_validate_long_term_pick():
    """Emitted SHORT picks must satisfy the long-term-value contract validator."""
    screener = ShortSideScreener()
    universe = [
        ("SHORT1", _two_trigger_record(), None),
        ("SHORT2", _two_trigger_record(), None),
    ]
    picks = screener.screen_universe(
        universe, top_n=5,
        current_prices={"SHORT1": 50.0, "SHORT2": 100.0},
    )
    assert len(picks) == 2
    for p in picks:
        errors = validate_long_term_pick(p)
        assert errors == [], (
            f"SHORT pick {p.get('symbol')} failed validation: {errors}"
        )
        # Spot-check inverted-semantic invariants.
        assert p["pick_type"] == "long_term_value"
        assert p["exit_mode"] == "thesis"
        assert p["holding_horizon"] == "1y"
        assert p["safety_gate_passed"] is True  # inverted meaning, factory enforces True
        assert p["intrinsic_value"] > 0
        assert p["intrinsic_value"] < p["entry_price"]  # SHORT targets a loss
        assert p["source_system"] == "short_side_screener"
        # Thesis-break rules: at least 3 (Beneish reverse, Altman recover, restatement).
        assert len(p["thesis_break_rules"]) >= 3
