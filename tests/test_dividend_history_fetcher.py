"""Tests for alpha_engine.dividend_history_fetcher."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from alpha_engine.dividend_history_fetcher import (
    DividendCache,
    DividendHistoryFetcher,
    DividendRecord,
    Edgar8KDividendsAdapter,
    YfinanceDividendsAdapter,
    compute_annual_yield,
    compute_consecutive_growth_years,
    compute_payout_ratio,
)
from alpha_engine.long_term_pick_contract import DividendEvent, DividendRecord as DividendRecordTD


# --------------------------------------------------------------------------- #
# helpers                                                                     #
# --------------------------------------------------------------------------- #

def _quarterly_events(years_back: int, base_amount: float, growth_per_year: float = 0.0):
    """Build quarterly DividendEvents for years_back complete years ending last year."""
    events: list[DividendEvent] = []
    current_year = datetime.now(timezone.utc).year
    last_complete_year = current_year - 1
    for i in range(years_back):
        year = last_complete_year - i
        amt = base_amount + growth_per_year * (years_back - 1 - i)
        for q_month in (3, 6, 9, 12):
            events.append({
                "ex_date": f"{year}-{q_month:02d}-15",
                "amount": amt,
            })
    return events


# --------------------------------------------------------------------------- #
# 1. compute_consecutive_growth_years correctly identifies aristocrats        #
# --------------------------------------------------------------------------- #

def test_growth_years_5y_aristocrat():
    history = _quarterly_events(years_back=5, base_amount=0.50, growth_per_year=0.05)
    streak = compute_consecutive_growth_years(history)
    assert streak == 5


def test_growth_years_10y_achiever():
    history = _quarterly_events(years_back=10, base_amount=0.40, growth_per_year=0.04)
    streak = compute_consecutive_growth_years(history)
    assert streak == 10


def test_growth_years_25y_aristocrat_threshold():
    history = _quarterly_events(years_back=25, base_amount=0.20, growth_per_year=0.02)
    streak = compute_consecutive_growth_years(history)
    assert streak == 25


# --------------------------------------------------------------------------- #
# 2. compute_consecutive_growth_years returns 0 for non-payers / inconsistent #
# --------------------------------------------------------------------------- #

def test_growth_years_zero_for_non_payer():
    assert compute_consecutive_growth_years([]) == 0


def test_growth_years_breaks_on_dividend_cut():
    """Build 5y of growth, then a cut in the middle — streak should equal 1
    (just the most-recent year, walking back stops at the cut)."""
    current_year = datetime.now(timezone.utc).year
    last_complete = current_year - 1
    history: list[DividendEvent] = []
    # Most-recent year: 1.00 / quarter (highest)
    for q in (3, 6, 9, 12):
        history.append({"ex_date": f"{last_complete}-{q:02d}-15", "amount": 1.00})
    # Year before: 1.20 / quarter (HIGHER — so walking back, streak breaks immediately)
    for q in (3, 6, 9, 12):
        history.append({"ex_date": f"{last_complete - 1}-{q:02d}-15", "amount": 1.20})
    streak = compute_consecutive_growth_years(history)
    assert streak == 1


def test_growth_years_zero_for_zero_amounts():
    history: list[DividendEvent] = [
        {"ex_date": "2024-03-15", "amount": 0.0},
        {"ex_date": "2023-03-15", "amount": 0.0},
    ]
    assert compute_consecutive_growth_years(history) == 0


# --------------------------------------------------------------------------- #
# 3. compute_annual_yield sums last 12 months                                 #
# --------------------------------------------------------------------------- #

def test_annual_yield_sums_last_12_months():
    today = datetime.now(timezone.utc).date()
    history: list[DividendEvent] = [
        {"ex_date": (today - timedelta(days=30)).isoformat(), "amount": 0.50},
        {"ex_date": (today - timedelta(days=120)).isoformat(), "amount": 0.50},
        {"ex_date": (today - timedelta(days=210)).isoformat(), "amount": 0.50},
        {"ex_date": (today - timedelta(days=300)).isoformat(), "amount": 0.50},
        # >365d ago — must be excluded
        {"ex_date": (today - timedelta(days=400)).isoformat(), "amount": 0.50},
    ]
    yield_pct = compute_annual_yield(history, current_price=100.0)
    assert yield_pct == pytest.approx(0.02, rel=1e-6)  # $2.00 / $100 = 2 %


def test_annual_yield_no_dividends_returns_zero():
    assert compute_annual_yield([], current_price=100.0) == 0.0


def test_annual_yield_invalid_price_returns_none():
    assert compute_annual_yield(_quarterly_events(1, 0.5), current_price=0.0) is None
    assert compute_annual_yield(_quarterly_events(1, 0.5), current_price=None) is None  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# 4. compute_payout_ratio returns None for negative EPS                       #
# --------------------------------------------------------------------------- #

def test_payout_ratio_returns_none_for_negative_eps():
    assert compute_payout_ratio(annual_div_per_share=2.0, eps=-1.5) is None


def test_payout_ratio_returns_none_for_zero_eps():
    assert compute_payout_ratio(annual_div_per_share=2.0, eps=0.0) is None


def test_payout_ratio_normal():
    assert compute_payout_ratio(annual_div_per_share=2.0, eps=5.0) == pytest.approx(0.40)


def test_payout_ratio_none_inputs():
    assert compute_payout_ratio(None, 5.0) is None
    assert compute_payout_ratio(2.0, None) is None


# --------------------------------------------------------------------------- #
# 5. Cache TTL respected (168h)                                               #
# --------------------------------------------------------------------------- #

def test_cache_ttl_168h(tmp_path):
    cache = DividendCache(cache_dir=tmp_path, ttl_hours=168)
    record = DividendRecord(
        ticker="JNJ",
        annual_yield=0.027,
        payout_ratio=0.45,
        consecutive_growth_years=60,
        history_5y=[{"ex_date": "2025-09-15", "amount": 1.19}],
        fetched_at=datetime.now(timezone.utc).isoformat(),
        source="yfinance",
    )
    cache.put(record)
    got = cache.get("JNJ")
    assert got is not None
    assert got.cache_hit is True
    assert got.consecutive_growth_years == 60

    # Age it out beyond 168h.
    stale_path = tmp_path / "JNJ" / "latest.json"
    stale_data = json.loads(stale_path.read_text(encoding="utf-8"))
    stale_data["fetched_at"] = (datetime.now(timezone.utc) - timedelta(hours=169)).isoformat()
    stale_path.write_text(json.dumps(stale_data), encoding="utf-8")
    assert cache.get("JNJ") is None


# --------------------------------------------------------------------------- #
# 6. Failover yfinance None -> EDGAR None -> missing stub (not cached)        #
# --------------------------------------------------------------------------- #

def test_failover_to_missing_when_all_adapters_none(tmp_path):
    fetcher = DividendHistoryFetcher(cache_dir=tmp_path)
    fetcher.yfinance.fetch = lambda ticker: None  # type: ignore[method-assign]
    fetcher.edgar_8k.fetch = lambda ticker: None  # type: ignore[method-assign]

    record = fetcher.fetch("ZZZZ")
    assert record.source == "missing"
    assert record.consecutive_growth_years == 0
    assert record.history_5y == []
    # Missing stub must NOT be cached.
    assert not (tmp_path / "ZZZZ" / "latest.json").exists()


# --------------------------------------------------------------------------- #
# 7. DividendRecord shape matches TypedDict                                   #
# --------------------------------------------------------------------------- #

def test_dividend_record_shape_matches_typeddict():
    """The DividendRecord dataclass must contain every key from the TypedDict
    in long_term_pick_contract (plus housekeeping fields)."""
    record = DividendRecord(
        ticker="KO",
        annual_yield=0.031,
        payout_ratio=0.65,
        consecutive_growth_years=62,
        next_ex_div_date="2026-06-15",
        history_5y=[{"ex_date": "2025-12-15", "amount": 0.485}],
        fetched_at=datetime.now(timezone.utc).isoformat(),
        source="yfinance",
    )
    contract_keys = set(DividendRecordTD.__annotations__.keys())
    record_fields = set(record.__dataclass_fields__.keys())
    assert contract_keys.issubset(record_fields), (
        f"Missing TypedDict fields: {contract_keys - record_fields}"
    )

    # And history_5y entries must match DividendEvent.
    event_keys = set(DividendEvent.__annotations__.keys())
    assert event_keys == {"ex_date", "amount"}
    assert set(record.history_5y[0].keys()) == event_keys


# --------------------------------------------------------------------------- #
# 8. Failover yfinance success skips EDGAR                                    #
# --------------------------------------------------------------------------- #

def test_failover_yfinance_success_skips_edgar(tmp_path):
    fetcher = DividendHistoryFetcher(cache_dir=tmp_path)
    fake_record = DividendRecord(
        ticker="MSFT",
        annual_yield=0.0085,
        payout_ratio=0.27,
        consecutive_growth_years=20,
        history_5y=[{"ex_date": "2025-11-15", "amount": 0.83}],
        fetched_at=datetime.now(timezone.utc).isoformat(),
        source="yfinance",
    )
    fetcher.yfinance.fetch = lambda ticker: fake_record  # type: ignore[method-assign]

    edgar_called = {"flag": False}

    def edgar_spy(ticker):
        edgar_called["flag"] = True
        return None

    fetcher.edgar_8k.fetch = edgar_spy  # type: ignore[method-assign]
    record = fetcher.fetch("MSFT")
    assert record.source == "yfinance"
    assert edgar_called["flag"] is False


# --------------------------------------------------------------------------- #
# 9. EDGAR 8-K stub returns None                                              #
# --------------------------------------------------------------------------- #

def test_edgar_8k_stub_returns_none():
    adapter = Edgar8KDividendsAdapter()
    assert adapter.fetch("AAPL") is None


# --------------------------------------------------------------------------- #
# 10. fetch_batch returns one entry per ticker                                #
# --------------------------------------------------------------------------- #

def test_fetch_batch_returns_one_entry_per_ticker(tmp_path):
    fetcher = DividendHistoryFetcher(cache_dir=tmp_path)

    def fake_yf(ticker):
        return DividendRecord(
            ticker=ticker,
            annual_yield=0.02,
            payout_ratio=0.50,
            consecutive_growth_years=5,
            history_5y=[{"ex_date": "2025-09-15", "amount": 0.50}],
            fetched_at=datetime.now(timezone.utc).isoformat(),
            source="yfinance",
        )

    fetcher.yfinance.fetch = fake_yf  # type: ignore[method-assign]
    out = fetcher.fetch_batch(["JNJ", "KO", "PG"])
    assert set(out.keys()) == {"JNJ", "KO", "PG"}
    for sym, rec in out.items():
        assert rec.ticker == sym
        assert rec.source == "yfinance"


# --------------------------------------------------------------------------- #
# 11. Cache round-trip preserves data shape                                   #
# --------------------------------------------------------------------------- #

def test_cache_roundtrip(tmp_path):
    cache = DividendCache(cache_dir=tmp_path, ttl_hours=168)
    record = DividendRecord(
        ticker="PG",
        annual_yield=0.024,
        payout_ratio=0.60,
        consecutive_growth_years=68,
        next_ex_div_date="2026-04-25",
        history_5y=[
            {"ex_date": "2025-12-15", "amount": 1.0065},
            {"ex_date": "2025-09-15", "amount": 1.0065},
        ],
        fetched_at=datetime.now(timezone.utc).isoformat(),
        source="yfinance",
    )
    cache.put(record)
    got = cache.get("PG")
    assert got is not None
    assert got.ticker == "PG"
    assert got.annual_yield == pytest.approx(0.024)
    assert got.consecutive_growth_years == 68
    assert len(got.history_5y) == 2
    assert got.history_5y[0]["amount"] == pytest.approx(1.0065)
    assert got.cache_hit is True
