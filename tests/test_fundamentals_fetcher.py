"""Tests for alpha_engine.fundamentals_fetcher."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from alpha_engine.fundamentals_fetcher import (
    EdgarAdapter,
    FundamentalsFetcher,
    FundamentalsRecord,
    ParquetCache,
    compute_ratios,
)

SAMPLE_EDGAR_TICKERS_JSON = json.dumps({
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corp"},
})


def _edgar_companyfacts_for_aapl() -> str:
    payload = {
        "cik": 320193, "entityName": "Apple Inc.",
        "facts": {"us-gaap": {
            "Revenues": {"units": {"USD": [
                {"val": 365817000000, "fy": 2024, "fp": "FY", "end": "2024-09-28"},
                {"val": 383285000000, "fy": 2025, "fp": "FY", "end": "2025-09-27"},
            ]}},
            "NetIncomeLoss": {"units": {"USD": [
                {"val": 96995000000, "fy": 2024, "fp": "FY", "end": "2024-09-28"},
                {"val": 99803000000, "fy": 2025, "fp": "FY", "end": "2025-09-27"},
            ]}},
            "OperatingIncomeLoss": {"units": {"USD": [
                {"val": 114301000000, "fy": 2025, "fp": "FY", "end": "2025-09-27"},
            ]}},
            "Assets": {"units": {"USD": [
                {"val": 364840000000, "fy": 2025, "fp": "FY", "end": "2025-09-27"},
            ]}},
            "Liabilities": {"units": {"USD": [
                {"val": 290437000000, "fy": 2025, "fp": "FY", "end": "2025-09-27"},
            ]}},
            "StockholdersEquity": {"units": {"USD": [
                {"val": 74403000000, "fy": 2025, "fp": "FY", "end": "2025-09-27"},
            ]}},
            "AssetsCurrent": {"units": {"USD": [
                {"val": 152987000000, "fy": 2025, "fp": "FY", "end": "2025-09-27"},
            ]}},
            "LiabilitiesCurrent": {"units": {"USD": [
                {"val": 176392000000, "fy": 2025, "fp": "FY", "end": "2025-09-27"},
            ]}},
            "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": [
                {"val": 110543000000, "fy": 2025, "fp": "FY", "end": "2025-09-27"},
            ]}},
        }},
    }
    return json.dumps(payload)


def _make_adapter_with_fixtures(http_responses: dict[str, str]) -> EdgarAdapter:
    adapter = EdgarAdapter(user_agent="test-agent", request_delay_s=0.0)

    def fake_get(url, ua):
        for key, body in http_responses.items():
            if key in url:
                return body
        raise FileNotFoundError(f"no fixture for {url}")

    adapter._http_get = fake_get
    return adapter


def test_edgar_parses_companyfacts_into_record():
    adapter = _make_adapter_with_fixtures({
        "company_tickers.json": SAMPLE_EDGAR_TICKERS_JSON,
        "CIK0000320193.json": _edgar_companyfacts_for_aapl(),
    })
    record = adapter.fetch("AAPL")
    assert record is not None
    assert record.ticker == "AAPL"
    assert record.cik == "320193"
    assert record.source == "edgar"
    assert record.period == "2025-Q3"
    assert record.income_statement["revenue"] == 383285000000
    assert record.income_statement["net_income"] == 99803000000
    assert record.income_statement["operating_income"] == 114301000000
    assert record.balance_sheet["total_assets"] == 364840000000
    assert record.balance_sheet["stockholders_equity"] == 74403000000
    assert record.cash_flow["operating_cash_flow"] == 110543000000


def test_edgar_returns_none_for_unknown_ticker():
    adapter = _make_adapter_with_fixtures({
        "company_tickers.json": SAMPLE_EDGAR_TICKERS_JSON,
    })
    assert adapter.fetch("UNKNOWN_TICKER_ZZZ") is None


def test_edgar_handles_http_failure_gracefully():
    adapter = EdgarAdapter(user_agent="test", request_delay_s=0.0)

    def failing_get(url, ua):
        raise OSError("network down")

    adapter._http_get = failing_get
    assert adapter.fetch("AAPL") is None


def test_edgar_prefers_fy_filings_over_interim():
    payload = {
        "facts": {"us-gaap": {"Revenues": {"units": {"USD": [
            {"val": 100, "fy": 2025, "fp": "Q3", "end": "2025-09-30"},
            {"val": 400, "fy": 2025, "fp": "FY", "end": "2025-12-31"},
        ]}}}}
    }
    adapter = EdgarAdapter(user_agent="t", request_delay_s=0.0)
    record = adapter._parse_companyfacts("TST", "1", payload)
    assert record.income_statement["revenue"] == 400


def test_edgar_period_label_handles_quarters_correctly():
    adapter = EdgarAdapter()
    assert adapter._period_label("2024-12-31") == "2024-Q4"
    assert adapter._period_label("2025-03-15") == "2025-Q1"
    assert adapter._period_label("2025-06-30") == "2025-Q2"
    assert adapter._period_label("2025-09-27") == "2025-Q3"
    assert adapter._period_label("") == ""
    assert adapter._period_label("not-a-date") == ""


def test_cache_round_trip_within_ttl(tmp_path):
    cache = ParquetCache(cache_dir=tmp_path, ttl_hours=24)
    record = FundamentalsRecord(
        ticker="AAPL", cik="320193", period="2025-Q3",
        fetched_at=datetime.now(timezone.utc).isoformat(),
        source="edgar", income_statement={"revenue": 100.0},
    )
    cache.put(record)
    got = cache.get("AAPL")
    assert got is not None
    assert got.ticker == "AAPL"
    assert got.income_statement["revenue"] == 100.0
    assert got.cache_hit is True


def test_cache_returns_none_when_stale(tmp_path):
    cache = ParquetCache(cache_dir=tmp_path, ttl_hours=1)
    old_ts = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    record = FundamentalsRecord(
        ticker="AAPL", cik="320193", period="2025-Q3",
        fetched_at=old_ts, source="edgar",
    )
    cache.put(record)
    assert cache.get("AAPL") is None


def test_cache_returns_none_for_unknown_ticker(tmp_path):
    cache = ParquetCache(cache_dir=tmp_path)
    assert cache.get("NEVER_CACHED") is None


def test_fetcher_uses_cache_first(tmp_path):
    fetcher = FundamentalsFetcher(cache_dir=tmp_path)
    cached = FundamentalsRecord(
        ticker="AAPL", cik="320193", period="2025-Q3",
        fetched_at=datetime.now(timezone.utc).isoformat(),
        source="edgar",
        income_statement={"revenue": 999.0, "net_income": 100.0},
        balance_sheet={"total_assets": 1000.0, "stockholders_equity": 500.0},
    )
    fetcher.cache.put(cached)
    got = fetcher.fetch("AAPL")
    assert got.income_statement["revenue"] == 999.0
    assert got.cache_hit is True


def test_fetcher_falls_back_to_yfinance_when_edgar_returns_none(tmp_path):
    fetcher = FundamentalsFetcher(cache_dir=tmp_path)
    fetcher.edgar.fetch = lambda ticker: None
    yf_record = FundamentalsRecord(
        ticker="ZZZ.TO", period="2025-Q3",
        fetched_at=datetime.now(timezone.utc).isoformat(),
        source="yfinance",
        income_statement={"revenue": 5e9, "net_income": 1e9},
        balance_sheet={"total_assets": 2e10, "stockholders_equity": 8e9},
    )
    fetcher.yfinance.fetch = lambda ticker: yf_record
    got = fetcher.fetch("ZZZ.TO")
    assert got is not None
    assert got.source == "yfinance"
    assert got.income_statement["revenue"] == 5e9


def test_fetcher_returns_missing_stub_when_all_sources_fail(tmp_path):
    fetcher = FundamentalsFetcher(cache_dir=tmp_path)
    fetcher.edgar.fetch = lambda t: None
    fetcher.yfinance.fetch = lambda t: None
    got = fetcher.fetch("FAKE_TICKER")
    assert got.source == "missing"
    assert got.is_complete() is False


def test_compute_ratios_pe_pb_basic():
    record = FundamentalsRecord(
        ticker="AAPL",
        income_statement={
            "revenue": 400e9, "net_income": 100e9,
            "operating_income": 120e9, "ebit": 120e9,
            "ebitda_proxy_da": 12e9, "interest_expense": 4e9,
        },
        balance_sheet={
            "total_assets": 365e9, "total_liabilities": 290e9,
            "stockholders_equity": 75e9,
            "current_assets": 153e9, "current_liabilities": 176e9,
            "long_term_debt": 100e9, "cash_and_equivalents": 30e9,
            "shares_outstanding": 15e9,
        },
        cash_flow={"operating_cash_flow": 110e9, "capex": 10e9},
    )
    ratios = compute_ratios(record, market_cap=3.2e12)
    assert ratios["pe"] == pytest.approx(32.0, rel=0.01)
    assert ratios["pb"] == pytest.approx(42.667, rel=0.01)
    assert ratios["roe"] == pytest.approx(1.333, rel=0.01)
    assert ratios["debt_to_equity"] == pytest.approx(3.867, rel=0.01)
    assert ratios["interest_coverage"] == pytest.approx(30.0, rel=0.01)


def test_compute_ratios_acquirers_multiple():
    record = FundamentalsRecord(
        ticker="X",
        income_statement={"operating_income": 100e9, "ebit": 100e9},
        balance_sheet={
            "long_term_debt": 50e9, "current_liabilities": 30e9,
            "cash_and_equivalents": 20e9, "stockholders_equity": 100e9,
            "total_assets": 200e9, "total_liabilities": 100e9,
            "current_assets": 80e9,
        },
        cash_flow={},
    )
    ratios = compute_ratios(record, market_cap=600e9)
    assert ratios["acquirers_multiple"] == pytest.approx(6.6, rel=0.01)
    assert ratios["earnings_yield"] == pytest.approx(0.1515, rel=0.01)


def test_compute_ratios_returns_none_for_missing_inputs():
    record = FundamentalsRecord(ticker="X")
    ratios = compute_ratios(record, market_cap=None)
    assert ratios["pe"] is None
    assert ratios["pb"] is None
    assert ratios["acquirers_multiple"] is None
    assert ratios["altman_z_double_prime"] is None


def test_altman_z_double_prime_distress_signal():
    record = FundamentalsRecord(
        ticker="DISTRESSED",
        income_statement={"ebit": -10e9, "operating_income": -10e9},
        balance_sheet={
            "total_assets": 100e9, "total_liabilities": 110e9,
            "stockholders_equity": -10e9,
            "current_assets": 30e9, "current_liabilities": 60e9,
            "long_term_debt": 50e9, "cash_and_equivalents": 5e9,
        },
        cash_flow={},
    )
    ratios = compute_ratios(record, market_cap=10e9)
    z = ratios["altman_z_double_prime"]
    assert z is not None
    assert z < 1.10

    record_safe = FundamentalsRecord(
        ticker="SAFE",
        income_statement={"ebit": 50e9, "operating_income": 50e9},
        balance_sheet={
            "total_assets": 200e9, "total_liabilities": 50e9,
            "stockholders_equity": 150e9,
            "current_assets": 80e9, "current_liabilities": 30e9,
            "long_term_debt": 20e9, "cash_and_equivalents": 30e9,
        },
        cash_flow={},
    )
    ratios_safe = compute_ratios(record_safe, market_cap=500e9)
    assert ratios_safe["altman_z_double_prime"] is not None
    assert ratios_safe["altman_z_double_prime"] > 2.60


def test_record_is_complete_when_required_fields_present():
    record = FundamentalsRecord(
        ticker="X",
        income_statement={"revenue": 100, "net_income": 10},
        balance_sheet={"total_assets": 1000, "stockholders_equity": 500},
    )
    assert record.is_complete() is True


def test_record_is_incomplete_when_revenue_missing():
    record = FundamentalsRecord(
        ticker="X",
        income_statement={"net_income": 10},
        balance_sheet={"total_assets": 1000, "stockholders_equity": 500},
    )
    assert record.is_complete() is False
