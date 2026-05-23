"""Tests for alpha_engine.value_screener_runner.

Exercises the production wire-up: runner orchestrates fetcher → screener →
write to active_picks.json + run report. All HTTP injectable; no live network.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from alpha_engine.fundamentals_fetcher import FundamentalsRecord
from alpha_engine.long_term_pick_contract import is_long_term_value, validate_long_term_pick
from alpha_engine.value_screener_runner import (
    DEFAULT_UNIVERSE,
    build_screener_inputs,
    load_active_picks,
    remove_existing_long_term_value_picks,
    run,
    save_active_picks,
    write_run_report,
)


def _stub_record(ticker: str, *, healthy: bool = True) -> FundamentalsRecord:
    if healthy:
        return FundamentalsRecord(
            ticker=ticker, period="2025-Q3",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            source="edgar",
            income_statement={
                "revenue": 100e9, "net_income": 15e9,
                "operating_income": 20e9, "ebit": 20e9,
                "ebitda_proxy_da": 5e9, "interest_expense": 1e9,
            },
            balance_sheet={
                "total_assets": 200e9, "total_liabilities": 80e9,
                "stockholders_equity": 120e9,
                "current_assets": 60e9, "current_liabilities": 40e9,
                "long_term_debt": 30e9, "cash_and_equivalents": 20e9,
                "shares_outstanding": 5e9,
            },
            cash_flow={"operating_cash_flow": 25e9, "capex": 5e9},
        )
    # distressed: high liabilities, negative equity → fails SafetyGate (Altman < 1.10)
    return FundamentalsRecord(
        ticker=ticker, period="2025-Q3",
        fetched_at=datetime.now(timezone.utc).isoformat(),
        source="edgar",
        income_statement={"revenue": 50e9, "net_income": -5e9,
                          "operating_income": -3e9, "ebit": -3e9,
                          "ebitda_proxy_da": 2e9, "interest_expense": 4e9},
        balance_sheet={"total_assets": 50e9, "total_liabilities": 60e9,
                       "stockholders_equity": -10e9,
                       "current_assets": 15e9, "current_liabilities": 30e9,
                       "long_term_debt": 25e9, "cash_and_equivalents": 2e9,
                       "shares_outstanding": 2e9},
        cash_flow={"operating_cash_flow": -1e9, "capex": 3e9},
    )


class _StubFundamentalsFetcher:
    def __init__(self, healthy_tickers: set[str] | None = None):
        self.healthy_tickers = healthy_tickers if healthy_tickers is not None else set()

    def fetch(self, ticker: str, *, force_refresh: bool = False) -> FundamentalsRecord:
        return _stub_record(ticker, healthy=ticker in self.healthy_tickers)

    def fetch_prior(self, ticker: str, *, force_refresh: bool = False) -> FundamentalsRecord | None:
        return None

    def fetch_batch_prior(
        self, tickers: list[str], *, force_refresh: bool = False
    ) -> dict[str, FundamentalsRecord]:
        return {}


def test_default_universe_is_nonempty():
    assert len(DEFAULT_UNIVERSE) >= 50
    assert all(isinstance(t, str) and t.isupper() for t in DEFAULT_UNIVERSE)


def test_run_emits_picks_for_healthy_universe(tmp_path):
    healthy = {"AAPL", "MSFT", "GOOGL"}
    fetcher = _StubFundamentalsFetcher(healthy_tickers=healthy)

    summary = run(
        universe=list(healthy),
        fundamentals_fetcher=fetcher,
        earnings_fetcher=None,
        dividends_fetcher=None,
        price_provider=lambda t: 150.0,
        market_cap_provider=lambda ts: {t: 1.5e12 for t in ts},
        active_picks_path=tmp_path / "active_picks.json",
    )
    assert summary["n_universe"] == 3
    assert summary["n_filtered_universe"] == 3
    assert summary["n_long_emitted"] == 3
    # All 3 healthy companies pass SafetyGate → 0 short triggers
    assert summary["n_short_emitted"] == 0


def test_run_filters_micro_caps(tmp_path):
    healthy = {"AAPL"}
    fetcher = _StubFundamentalsFetcher(healthy_tickers=healthy)

    summary = run(
        universe=["AAPL"],
        fundamentals_fetcher=fetcher,
        earnings_fetcher=None,
        dividends_fetcher=None,
        price_provider=lambda t: 150.0,
        # 200M < 300M floor — should be filtered out
        market_cap_provider=lambda ts: {t: 200_000_000 for t in ts},
        active_picks_path=tmp_path / "active_picks.json",
    )
    assert summary["n_filtered_universe"] == 0
    assert summary["n_long_emitted"] == 0


def test_run_filters_missing_price(tmp_path):
    fetcher = _StubFundamentalsFetcher(healthy_tickers={"AAPL"})

    summary = run(
        universe=["AAPL"],
        fundamentals_fetcher=fetcher,
        earnings_fetcher=None,
        dividends_fetcher=None,
        price_provider=lambda t: None,  # no price
        market_cap_provider=lambda ts: {t: 1.5e12 for t in ts},
        active_picks_path=tmp_path / "active_picks.json",
    )
    assert summary["n_filtered_universe"] == 0


def test_emitted_picks_pass_long_term_validator(tmp_path):
    fetcher = _StubFundamentalsFetcher(healthy_tickers={"AAPL"})
    picks_path = tmp_path / "active_picks.json"

    run(
        universe=["AAPL"],
        fundamentals_fetcher=fetcher,
        earnings_fetcher=None,
        dividends_fetcher=None,
        price_provider=lambda t: 150.0,
        market_cap_provider=lambda ts: {t: 1.5e12 for t in ts},
        active_picks_path=picks_path,
    )
    picks, _ = load_active_picks(picks_path)
    long_picks = [p for p in picks if is_long_term_value(p)]
    assert len(long_picks) > 0
    for p in long_picks:
        errors = validate_long_term_pick(p)
        assert errors == [], f"pick failed validation: {errors} on {p}"


def test_run_writes_to_active_picks_json(tmp_path):
    fetcher = _StubFundamentalsFetcher(healthy_tickers={"AAPL", "MSFT"})
    picks_path = tmp_path / "active_picks.json"

    run(
        universe=["AAPL", "MSFT"],
        fundamentals_fetcher=fetcher,
        earnings_fetcher=None,
        dividends_fetcher=None,
        price_provider=lambda t: 150.0,
        market_cap_provider=lambda ts: {t: 1.5e12 for t in ts},
        active_picks_path=picks_path,
    )
    assert picks_path.exists()
    data = json.loads(picks_path.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    symbols = {p["symbol"] for p in data if p.get("pick_type") == "long_term_value"}
    assert symbols == {"AAPL", "MSFT"}


def test_dry_run_does_not_write(tmp_path):
    fetcher = _StubFundamentalsFetcher(healthy_tickers={"AAPL"})
    picks_path = tmp_path / "active_picks.json"

    run(
        universe=["AAPL"],
        fundamentals_fetcher=fetcher,
        earnings_fetcher=None,
        dividends_fetcher=None,
        price_provider=lambda t: 150.0,
        market_cap_provider=lambda ts: {t: 1.5e12 for t in ts},
        active_picks_path=picks_path,
        dry_run=True,
    )
    assert not picks_path.exists()


def test_remove_existing_long_term_value_picks_preserves_others():
    existing = [
        {"symbol": "AAPL", "pick_type": "long_term_value"},
        {"symbol": "MSFT", "pick_type": "long_term_value"},
        {"symbol": "DOTUSDT", "pick_type": "swing"},
        {"symbol": "BTCUSDT"},  # no pick_type
    ]
    cleaned = remove_existing_long_term_value_picks(existing, {"AAPL"})
    symbols = {p["symbol"] for p in cleaned}
    assert "AAPL" not in symbols  # removed
    assert "MSFT" in symbols  # not in re-emit set; preserved
    assert "DOTUSDT" in symbols
    assert "BTCUSDT" in symbols


def test_save_and_load_round_trip_with_wrapper_dict(tmp_path):
    picks = [{"symbol": "AAPL", "pick_type": "long_term_value"}]
    full = {"picks": [], "version": 1, "generated_at": "old-ts"}
    p = tmp_path / "active.json"
    save_active_picks(picks, full, p)
    got, full_back = load_active_picks(p)
    assert got == picks
    assert full_back is not None
    assert full_back["version"] == 1


def test_save_and_load_round_trip_with_list(tmp_path):
    picks = [{"symbol": "AAPL", "pick_type": "long_term_value"}]
    p = tmp_path / "active.json"
    save_active_picks(picks, None, p)
    got, full_back = load_active_picks(p)
    assert got == picks
    assert full_back is None


def test_run_appends_without_clobbering_existing_swing_picks(tmp_path):
    picks_path = tmp_path / "active_picks.json"
    existing = [
        {"symbol": "BTCUSDT", "pick_type": "swing", "direction": "LONG"},
        {"symbol": "ETHUSDT", "pick_type": "scalp", "direction": "SHORT"},
    ]
    save_active_picks(existing, None, picks_path)

    fetcher = _StubFundamentalsFetcher(healthy_tickers={"AAPL"})
    run(
        universe=["AAPL"],
        fundamentals_fetcher=fetcher,
        earnings_fetcher=None,
        dividends_fetcher=None,
        price_provider=lambda t: 150.0,
        market_cap_provider=lambda ts: {t: 1.5e12 for t in ts},
        active_picks_path=picks_path,
    )
    picks, _ = load_active_picks(picks_path)
    types = {p.get("pick_type") for p in picks}
    assert "swing" in types
    assert "scalp" in types
    assert "long_term_value" in types


def test_write_run_report_creates_md_file(tmp_path):
    fetcher = _StubFundamentalsFetcher(healthy_tickers={"AAPL"})
    inputs = build_screener_inputs(
        ["AAPL"], fetcher, None, None,
        lambda t: 150.0, {"AAPL": 1.5e12},
    )
    report_dir = tmp_path / "value_screener_runs"
    path = write_run_report(inputs, [], [], report_dir=report_dir)
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "# Value Screener Run" in text
    assert "n=" in text
    assert "Methodology" in text


def test_run_returns_summary_dict(tmp_path):
    fetcher = _StubFundamentalsFetcher(healthy_tickers={"AAPL"})
    summary = run(
        universe=["AAPL"],
        fundamentals_fetcher=fetcher,
        earnings_fetcher=None,
        dividends_fetcher=None,
        price_provider=lambda t: 150.0,
        market_cap_provider=lambda ts: {t: 1.5e12 for t in ts},
        active_picks_path=tmp_path / "active.json",
    )
    assert "n_universe" in summary
    assert "n_filtered_universe" in summary
    assert "n_long_emitted" in summary
    assert "n_short_emitted" in summary


def test_run_with_distressed_universe_emits_short_picks(tmp_path):
    fetcher = _StubFundamentalsFetcher(healthy_tickers=set())
    summary = run(
        universe=["XYZ"],
        fundamentals_fetcher=fetcher,
        earnings_fetcher=None,
        dividends_fetcher=None,
        price_provider=lambda t: 50.0,
        market_cap_provider=lambda ts: {t: 5e9 for t in ts},
        active_picks_path=tmp_path / "active.json",
    )
    # Distressed company → SafetyGate fails → no LONG; should be picked as SHORT
    assert summary["n_long_emitted"] == 0
