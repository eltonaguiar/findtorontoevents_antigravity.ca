"""Tests for alpha_engine.earnings_calendar_fetcher."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from alpha_engine.earnings_calendar_fetcher import (
    EarningsCache,
    EarningsCalendarFetcher,
    EarningsRecord,
    FinnhubEarningsAdapter,
    YfinanceEarningsAdapter,
    EdgarEightKAdapter,
)
from alpha_engine.long_term_pick_contract import EarningsRow

# ----- fixtures -----

SAMPLE_FINNHUB_HISTORY = json.dumps([
    {"period": "2025-09-30", "actual": 1.85, "estimate": 1.78, "surprisePercent": 3.93},
    {"period": "2025-06-30", "actual": 1.42, "estimate": 1.38, "surprisePercent": 2.90},
    {"period": "2025-03-31", "actual": 1.65, "estimate": 1.60, "surprisePercent": 3.13},
    {"period": "2024-12-31", "actual": 2.18, "estimate": 2.10, "surprisePercent": 3.81},
    {"period": "2024-09-30", "actual": 1.64, "estimate": 1.60, "surprisePercent": 2.50},
    {"period": "2024-06-30", "actual": 1.40, "estimate": 1.35, "surprisePercent": 3.70},
    {"period": "2024-03-31", "actual": 1.53, "estimate": 1.50, "surprisePercent": 2.00},
    {"period": "2023-12-31", "actual": 2.18, "estimate": 2.10, "surprisePercent": 3.81},
    {"period": "2023-09-30", "actual": 1.46, "estimate": 1.39, "surprisePercent": 5.04},  # 9th — should be dropped
])

SAMPLE_FINNHUB_CALENDAR = json.dumps({
    "earningsCalendar": [
        {"date": "2026-05-01", "epsEstimate": 1.95, "symbol": "AAPL"},
        {"date": "2026-08-01", "epsEstimate": 1.50, "symbol": "AAPL"},
    ]
})

EMPTY_FINNHUB_HISTORY = json.dumps([])
EMPTY_FINNHUB_CALENDAR = json.dumps({"earningsCalendar": []})


def _make_finnhub_with_fixtures(http_responses: dict[str, str], api_key: str = "test-key") -> FinnhubEarningsAdapter:
    adapter = FinnhubEarningsAdapter(api_key=api_key)

    def fake_get(url: str, ua: str) -> str:
        for key, body in http_responses.items():
            if key in url:
                return body
        raise FileNotFoundError(f"no fixture for {url}")

    adapter._http_get = fake_get
    return adapter


# ----- 1. Parser produces standardized record from fixture Finnhub JSON -----

def test_finnhub_parser_produces_standardized_record():
    adapter = _make_finnhub_with_fixtures({
        "stock/earnings": SAMPLE_FINNHUB_HISTORY,
        "calendar/earnings": SAMPLE_FINNHUB_CALENDAR,
    })
    record = adapter.fetch("AAPL")
    assert record is not None
    assert record.ticker == "AAPL"
    assert record.source == "finnhub"
    # Capped at 8 quarters.
    assert len(record.history) == 8
    # Newest first.
    assert record.history[0]["date"] == "2025-09-30"
    assert record.history[0]["eps_actual"] == 1.85
    assert record.history[0]["eps_estimate"] == 1.78
    assert record.history[0]["surprise_pct"] == pytest.approx(3.93)
    # Calendar parsed.
    assert record.next_earnings_date == "2026-05-01"
    assert record.next_earnings_estimate == pytest.approx(1.95)


# ----- 2. Failover Finnhub -> EDGAR(stub) -> yfinance when Finnhub returns None -----

def test_failover_finnhub_to_yfinance(tmp_path, monkeypatch):
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    fetcher = EarningsCalendarFetcher(cache_dir=tmp_path)
    # Finnhub adapter has no api key -> returns None.
    assert fetcher.finnhub.fetch("AAPL") is None

    fake_record = EarningsRecord(
        ticker="AAPL",
        next_earnings_date="2026-05-01",
        next_earnings_estimate=1.95,
        history=[{"date": "2025-09-30", "eps_actual": 1.85, "eps_estimate": 1.78, "surprise_pct": 3.93}],
        fetched_at=datetime.now(timezone.utc).isoformat(),
        source="yfinance",
    )

    def fake_yf_fetch(ticker):
        return fake_record

    fetcher.yfinance.fetch = fake_yf_fetch  # type: ignore[method-assign]
    record = fetcher.fetch("AAPL")
    assert record.source == "yfinance"
    assert record.history[0]["eps_actual"] == 1.85


# ----- 3. Cache TTL respected (24h boundary) -----

def test_cache_ttl_respected(tmp_path):
    cache = EarningsCache(cache_dir=tmp_path, ttl_hours=24)
    fresh = EarningsRecord(
        ticker="AAPL",
        history=[{"date": "2025-09-30", "eps_actual": 1.85, "eps_estimate": 1.78, "surprise_pct": 3.93}],
        fetched_at=datetime.now(timezone.utc).isoformat(),
        source="finnhub",
    )
    cache.put(fresh)
    got = cache.get("AAPL")
    assert got is not None
    assert got.cache_hit is True

    stale_path = tmp_path / "AAPL" / "latest.json"
    stale_data = json.loads(stale_path.read_text(encoding="utf-8"))
    stale_data["fetched_at"] = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    stale_path.write_text(json.dumps(stale_data), encoding="utf-8")
    assert cache.get("AAPL") is None


# ----- 4. EarningsRow shape exactly matches TypedDict -----

def test_earnings_row_shape_matches_typeddict():
    adapter = _make_finnhub_with_fixtures({
        "stock/earnings": SAMPLE_FINNHUB_HISTORY,
        "calendar/earnings": SAMPLE_FINNHUB_CALENDAR,
    })
    record = adapter.fetch("AAPL")
    assert record is not None
    row = record.history[0]
    expected_keys = set(EarningsRow.__annotations__.keys())
    assert set(row.keys()) == expected_keys
    assert isinstance(row["date"], str)
    assert isinstance(row["eps_actual"], float)
    assert isinstance(row["eps_estimate"], float)
    assert isinstance(row["surprise_pct"], float)


# ----- 5. Old picks (no earnings_history field) parse cleanly -----

def test_old_picks_without_earnings_history_parse_cleanly():
    """A pick dict without `earnings_history` should still be a valid pick;
    the new EarningsRecord schema is purely additive."""
    pick = {
        "symbol": "AAPL",
        "direction": "LONG",
        "entry_price": 180.0,
        "asset_class": "EQUITY",
        "source_system": "legacy",
    }
    # Constructing EarningsRecord from scratch with no history is also fine.
    rec = EarningsRecord(
        ticker="AAPL",
        fetched_at=datetime.now(timezone.utc).isoformat(),
        source="missing",
    )
    assert rec.history == []
    assert rec.is_complete() is False
    assert pick.get("earnings_history") is None  # No KeyError.


# ----- 6. _http_get is mockable (no live HTTP) -----

def test_http_get_is_injectable():
    adapter = FinnhubEarningsAdapter(api_key="test-key")
    calls = []

    def fake_get(url, ua):
        calls.append(url)
        if "stock/earnings" in url:
            return SAMPLE_FINNHUB_HISTORY
        if "calendar/earnings" in url:
            return SAMPLE_FINNHUB_CALENDAR
        return "[]"

    adapter._http_get = fake_get
    rec = adapter.fetch("AAPL")
    assert rec is not None
    # Both endpoints hit; no live HTTP attempted.
    assert any("stock/earnings" in u for u in calls)
    assert any("calendar/earnings" in u for u in calls)


# ----- 7. Cache miss does NOT cache the missing stub -----

def test_missing_stub_is_not_cached(tmp_path, monkeypatch):
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    fetcher = EarningsCalendarFetcher(cache_dir=tmp_path)
    # Force every adapter to return None.
    fetcher.finnhub.fetch = lambda ticker: None  # type: ignore[method-assign]
    fetcher.edgar_8k.fetch = lambda ticker: None  # type: ignore[method-assign]
    fetcher.yfinance.fetch = lambda ticker: None  # type: ignore[method-assign]

    record = fetcher.fetch("ZZZZ")
    assert record.source == "missing"
    # Cache should NOT have been written.
    cache_path = tmp_path / "ZZZZ" / "latest.json"
    assert not cache_path.exists()


# ----- 8. Batch returns dict with one entry per ticker -----

def test_fetch_batch_returns_one_entry_per_ticker(tmp_path, monkeypatch):
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    fetcher = EarningsCalendarFetcher(cache_dir=tmp_path)

    def fake_yf(ticker):
        return EarningsRecord(
            ticker=ticker,
            history=[{"date": "2025-09-30", "eps_actual": 1.0, "eps_estimate": 0.95, "surprise_pct": 5.26}],
            fetched_at=datetime.now(timezone.utc).isoformat(),
            source="yfinance",
        )

    fetcher.yfinance.fetch = fake_yf  # type: ignore[method-assign]
    out = fetcher.fetch_batch(["AAPL", "MSFT", "GOOG"])
    assert set(out.keys()) == {"AAPL", "MSFT", "GOOG"}
    for sym, rec in out.items():
        assert rec.ticker == sym
        assert rec.source == "yfinance"


# ----- 9. EDGAR 8-K stub returns None -----

def test_edgar_8k_stub_returns_none():
    adapter = EdgarEightKAdapter()
    assert adapter.fetch("AAPL") is None


# ----- 10. Finnhub adapter without API key returns None -----

def test_finnhub_without_api_key_returns_none(monkeypatch):
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    adapter = FinnhubEarningsAdapter()
    assert adapter.api_key is None
    assert adapter.fetch("AAPL") is None


# ----- 11. Empty Finnhub history with no calendar returns None -----

def test_finnhub_empty_responses_returns_none():
    adapter = _make_finnhub_with_fixtures({
        "stock/earnings": EMPTY_FINNHUB_HISTORY,
        "calendar/earnings": EMPTY_FINNHUB_CALENDAR,
    })
    assert adapter.fetch("ZZZZ") is None


# ----- 12. Cache round-trip preserves data shape -----

def test_cache_roundtrip_preserves_shape(tmp_path):
    cache = EarningsCache(cache_dir=tmp_path, ttl_hours=24)
    record = EarningsRecord(
        ticker="MSFT",
        next_earnings_date="2026-04-25",
        next_earnings_estimate=2.78,
        history=[
            {"date": "2025-12-31", "eps_actual": 3.21, "eps_estimate": 3.10, "surprise_pct": 3.55},
        ],
        fetched_at=datetime.now(timezone.utc).isoformat(),
        source="finnhub",
    )
    cache.put(record)
    got = cache.get("MSFT")
    assert got is not None
    assert got.ticker == "MSFT"
    assert got.next_earnings_date == "2026-04-25"
    assert got.next_earnings_estimate == pytest.approx(2.78)
    assert len(got.history) == 1
    assert got.history[0]["eps_actual"] == pytest.approx(3.21)
    assert got.cache_hit is True
