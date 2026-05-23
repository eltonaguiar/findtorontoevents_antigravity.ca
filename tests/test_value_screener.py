"""Tests for alpha_engine.value_screener (Phase 6).

Opt-in sidecar (per CLAUDE.md Wire-Up Rule). No production caller in this commit.
Wiring plan: Phase 14 GHA workflows + Phase 11 dashboard.
"""
from __future__ import annotations

import pytest

from alpha_engine.fundamentals_fetcher import FundamentalsRecord
from alpha_engine.long_term_pick_contract import validate_long_term_pick
from alpha_engine.value_screener import (
    ALTMAN_Z_DOUBLE_PRIME_MIN,
    BENEISH_M_MAX,
    BENEISH_M_PLACEHOLDER,
    ScreenerInput,
    ValueScreener,
    compute_beneish_m_score,
    compute_debt_to_equity_score,
    compute_piotroski_f_score,
    compute_quality_composite,
    compute_safety_gate,
    compute_value_composite,
)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _strong_record(scale: float = 1.0) -> FundamentalsRecord:
    """Healthy company suitable for full F-score = 9 with improving prior."""
    return FundamentalsRecord(
        ticker="GOOD",
        period="2025-Q4",
        income_statement={
            "revenue": 1000.0 * scale,
            "net_income": 200.0 * scale,
            "operating_income": 240.0 * scale,
            "ebit": 240.0 * scale,
            "ebitda_proxy_da": 60.0 * scale,
            "interest_expense": 10.0 * scale,
        },
        balance_sheet={
            "total_assets": 2000.0 * scale,
            "total_liabilities": 600.0 * scale,
            "stockholders_equity": 1400.0 * scale,
            "current_assets": 700.0 * scale,
            "current_liabilities": 200.0 * scale,
            "long_term_debt": 100.0 * scale,
            "cash_and_equivalents": 250.0 * scale,
            "shares_outstanding": 100.0,  # constant -> no dilution
        },
        cash_flow={
            "operating_cash_flow": 280.0 * scale,
            "capex": 50.0 * scale,
            "dividends_paid": 30.0 * scale,
        },
    )


def _prior_weaker_record() -> FundamentalsRecord:
    """Prior year: smaller, weaker — so YoY growth/improvement tests pass."""
    return FundamentalsRecord(
        ticker="GOOD",
        period="2024-Q4",
        income_statement={
            "revenue": 800.0,         # current 1000 -> SGI > 1, asset-turnover up
            "net_income": 120.0,      # current 200 -> NI/Rev up
            "operating_income": 150.0,
            "ebit": 150.0,
            "ebitda_proxy_da": 50.0,
            "interest_expense": 12.0,
        },
        balance_sheet={
            "total_assets": 1900.0,
            "total_liabilities": 700.0,
            "stockholders_equity": 1200.0,
            "current_assets": 600.0,
            "current_liabilities": 250.0,  # current_ratio 600/250=2.4 vs 700/200=3.5 -> up
            "long_term_debt": 200.0,        # leverage 200/1900=0.105 -> 100/2000=0.05 down
            "cash_and_equivalents": 200.0,
            "shares_outstanding": 100.0,
        },
        cash_flow={
            "operating_cash_flow": 180.0,
            "capex": 40.0,
            "dividends_paid": 20.0,
        },
    )


def _weak_record() -> FundamentalsRecord:
    """Distressed company — Altman Z'' will be << 1.10."""
    return FundamentalsRecord(
        ticker="WEAK",
        period="2025-Q4",
        income_statement={
            "revenue": 500.0,
            "net_income": -150.0,
            "operating_income": -100.0,
            "ebit": -100.0,
            "ebitda_proxy_da": 20.0,
            "interest_expense": 80.0,
        },
        balance_sheet={
            "total_assets": 800.0,
            "total_liabilities": 900.0,
            "stockholders_equity": -100.0,   # negative equity
            "current_assets": 100.0,
            "current_liabilities": 400.0,
            "long_term_debt": 500.0,
            "cash_and_equivalents": 5.0,
            "shares_outstanding": 200.0,
        },
        cash_flow={
            "operating_cash_flow": -50.0,
            "capex": 10.0,
        },
    )


def _make_input(
    ticker: str = "GOOD",
    record: FundamentalsRecord | None = None,
    *,
    market_cap: float = 1_000_000_000.0,
    operating_history_years: int = 10,
    is_financial_or_utility: bool = False,
    going_concern_flag: bool = False,
    pink_sheets: bool = False,
    last_10k_filing_age_days: int = 90,
    current_price: float = 100.0,
) -> ScreenerInput:
    return ScreenerInput(
        ticker=ticker,
        current_price=current_price,
        market_cap=market_cap,
        fundamentals=record if record is not None else _strong_record(),
        operating_history_years=operating_history_years,
        is_financial_or_utility=is_financial_or_utility,
        going_concern_flag=going_concern_flag,
        pink_sheets=pink_sheets,
        last_10k_filing_age_days=last_10k_filing_age_days,
    )


# -----------------------------------------------------------------------------
# Pure-function tests
# -----------------------------------------------------------------------------
def test_piotroski_f_score_full_9_with_improving_prior():
    f = compute_piotroski_f_score(_strong_record(), _prior_weaker_record())
    assert f == 9


def test_piotroski_f_score_capped_at_4_without_prior():
    f = compute_piotroski_f_score(_strong_record(), prior_record=None)
    assert f <= 4
    # 4 static tests should all pass for our healthy fixture
    assert f == 4


def test_piotroski_f_score_low_for_weak_company():
    f = compute_piotroski_f_score(_weak_record(), prior_record=None)
    assert f <= 1  # NI<0, ROA<0, OCF<0 — only OCF>NI passes (-50 > -150)


def test_beneish_m_returns_none_without_prior():
    assert compute_beneish_m_score(_strong_record(), None) is None


def test_beneish_m_returns_float_with_prior():
    m = compute_beneish_m_score(_strong_record(), _prior_weaker_record())
    assert m is not None
    assert isinstance(m, float)


def test_debt_to_equity_score_buckets():
    assert compute_debt_to_equity_score(0.3) == 1.0
    assert compute_debt_to_equity_score(2.0) == 0.0
    assert compute_debt_to_equity_score(2.5) == 0.0
    # Linear midpoint: D/E=1.25 -> (1.25-0.5)/1.5 = 0.5 -> score 0.5
    assert compute_debt_to_equity_score(1.25) == pytest.approx(0.5, abs=1e-6)
    assert compute_debt_to_equity_score(None) == 0.0
    assert compute_debt_to_equity_score(-0.1) == 0.0


def test_value_composite_weights():
    # 0.40*0.8 + 0.35*0.6 + 0.25*0.4 = 0.32 + 0.21 + 0.10 = 0.63
    assert compute_value_composite(0.8, 0.6, 0.4) == pytest.approx(0.63, abs=1e-9)


def test_quality_composite_weights():
    # piotroski_f=8 -> 8/9 ≈ 0.8889
    # roic=0.18 -> 0.18/0.20 = 0.9 (capped at 1.0)
    # d_to_e_score=0.9
    # 0.50*(8/9) + 0.30*0.9 + 0.20*0.9 = 0.4444 + 0.27 + 0.18 = 0.8944
    expected = 0.50 * (8 / 9) + 0.30 * 0.9 + 0.20 * 0.9
    assert compute_quality_composite(8, 0.18, 0.9) == pytest.approx(expected, abs=1e-6)


def test_safety_gate_pass():
    assert compute_safety_gate(altman_z=3.0, beneish_m=-2.5) is True


def test_safety_gate_blocks_low_altman_z():
    assert compute_safety_gate(altman_z=0.5, beneish_m=-3.0) is False


def test_safety_gate_blocks_high_beneish_m():
    assert compute_safety_gate(altman_z=5.0, beneish_m=0.0) is False


def test_safety_gate_uses_placeholder_when_beneish_none():
    # Placeholder = -2.5 (safe), so altman pass + None -> True
    assert BENEISH_M_PLACEHOLDER <= BENEISH_M_MAX
    assert compute_safety_gate(altman_z=2.0, beneish_m=None) is True


def test_safety_gate_blocks_when_altman_none():
    assert compute_safety_gate(altman_z=None, beneish_m=-3.0) is False


# -----------------------------------------------------------------------------
# ValueScreener.score_one tests
# -----------------------------------------------------------------------------
def test_score_one_strong_company_passes_all_gates():
    screener = ValueScreener()
    score = screener.score_one(_make_input(record=_strong_record()),
                               prior_fundamentals=_prior_weaker_record())
    assert score.universe_gate_passed is True
    assert score.safety_gate_passed is True
    assert score.rejection_reason is None
    assert score.altman_z_double_prime is not None
    assert score.altman_z_double_prime >= ALTMAN_Z_DOUBLE_PRIME_MIN


def test_safety_gate_failure_sets_rejection_reason():
    screener = ValueScreener()
    score = screener.score_one(_make_input(ticker="WEAK", record=_weak_record()))
    assert score.safety_gate_passed is False
    assert score.rejection_reason == "safety_gate_failed"


def test_universe_gate_blocks_micro_cap():
    screener = ValueScreener()
    score = screener.score_one(_make_input(market_cap=100_000_000))  # below 300M
    assert score.universe_gate_passed is False
    assert score.rejection_reason == "universe_gate_market_cap"


def test_universe_gate_blocks_financial():
    screener = ValueScreener()
    score = screener.score_one(_make_input(is_financial_or_utility=True))
    assert score.universe_gate_passed is False
    assert score.rejection_reason == "universe_gate_financial_or_utility"


def test_universe_gate_blocks_short_history():
    screener = ValueScreener()
    score = screener.score_one(_make_input(operating_history_years=2))
    assert score.universe_gate_passed is False
    assert score.rejection_reason == "universe_gate_operating_history"


def test_universe_gate_blocks_going_concern():
    screener = ValueScreener()
    score = screener.score_one(_make_input(going_concern_flag=True))
    assert score.rejection_reason == "universe_gate_going_concern"


def test_universe_gate_blocks_pink_sheets():
    screener = ValueScreener()
    score = screener.score_one(_make_input(pink_sheets=True))
    assert score.rejection_reason == "universe_gate_pink_sheets"


def test_universe_gate_blocks_stale_10k():
    screener = ValueScreener()
    score = screener.score_one(_make_input(last_10k_filing_age_days=600))
    assert score.rejection_reason == "universe_gate_stale_10k"


# -----------------------------------------------------------------------------
# screen_universe tests
# -----------------------------------------------------------------------------
def test_screen_universe_emits_top_n_picks_via_factory():
    screener = ValueScreener()
    inputs = []
    priors = {}
    for i in range(5):
        ticker = f"GOOD{i}"
        inputs.append(_make_input(ticker=ticker, record=_strong_record(),
                                  current_price=100.0 + i))
        priors[ticker] = _prior_weaker_record()
    picks = screener.screen_universe(inputs, top_n=3, prior_fundamentals_map=priors)
    assert len(picks) == 3
    for pick in picks:
        assert pick["pick_type"] == "long_term_value"
        assert pick["safety_gate_passed"] is True
        assert pick["universe_gate_passed"] is True
        assert pick["intrinsic_value"] > 0
        assert pick["intrinsic_value"] > pick["entry_price"]
        assert len(pick["thesis_break_rules"]) >= 3


def test_screen_universe_excludes_failed_gates():
    screener = ValueScreener()
    inputs = [
        _make_input(ticker="OK", record=_strong_record()),
        _make_input(ticker="WEAK", record=_weak_record()),  # safety fail
        _make_input(ticker="MICRO", market_cap=10_000_000),  # universe fail
        _make_input(ticker="FIN", is_financial_or_utility=True),  # universe fail
    ]
    priors = {"OK": _prior_weaker_record()}
    picks = screener.screen_universe(inputs, top_n=10, prior_fundamentals_map=priors)
    tickers = {p["symbol"] for p in picks}
    assert "OK" in tickers
    assert "WEAK" not in tickers
    assert "MICRO" not in tickers
    assert "FIN" not in tickers


def test_emitted_picks_pass_validate_long_term_pick():
    screener = ValueScreener()
    inputs = [
        _make_input(ticker=f"T{i}", record=_strong_record(), current_price=50.0 + i)
        for i in range(4)
    ]
    priors = {f"T{i}": _prior_weaker_record() for i in range(4)}
    picks = screener.screen_universe(inputs, top_n=4, prior_fundamentals_map=priors)
    assert len(picks) == 4
    for pick in picks:
        errors = validate_long_term_pick(pick)
        assert errors == [], f"Pick {pick['symbol']} validation errors: {errors}"


def test_thesis_string_non_empty_and_includes_metrics():
    screener = ValueScreener()
    inputs = [_make_input(ticker="MMM", record=_strong_record())]
    priors = {"MMM": _prior_weaker_record()}
    picks = screener.screen_universe(inputs, top_n=1, prior_fundamentals_map=priors)
    assert len(picks) == 1
    thesis = picks[0]["thesis"]
    assert isinstance(thesis, str) and thesis.strip()
    assert "F-score" in thesis
    assert "Magic Formula" in thesis
