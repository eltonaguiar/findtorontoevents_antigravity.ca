"""Tests for data fetching + monthly-return computation."""
import pandas as pd
import pytest

from combined_book import fetch


def _daily_series(dates, prices):
    s = pd.Series(prices, index=pd.to_datetime(dates))
    s.index.name = "date"
    return s


def test_monthly_returns_resamples_to_last_price():
    s = _daily_series(
        ["2026-01-05", "2026-01-20", "2026-02-10", "2026-02-25", "2026-03-15"],
        [100.0, 110.0, 115.0, 120.0, 130.0],
    )
    r = fetch.monthly_returns(s)
    # Jan last=110, Feb last=120, Mar last=130
    assert list(r.index.strftime("%Y-%m")) == ["2026-01", "2026-02", "2026-03"]
    assert abs(r.iloc[0] - 0.10) < 1e-9  # (110-100)/100
    assert abs(r.iloc[1] - (120 - 110) / 110) < 1e-9
    assert abs(r.iloc[2] - (130 - 120) / 120) < 1e-9


def test_get_daily_closes_caches_to_disk(tmp_path):
    data = {"SPY": _daily_series(["2026-01-05"], [100.0])}
    fetch._write_cache(data, tmp_path)  # helper to seed cache
    out = fetch.get_daily_closes(["SPY"], cache_dir=tmp_path)
    assert "SPY" in out
    assert (tmp_path / "SPY.csv").exists()


def test_universe_contains_core_symbols():
    assert "SPY" in fetch.UNIVERSE
    assert "XYLD" in fetch.UNIVERSE
    assert "PUT" in fetch.UNIVERSE
    assert "QUAL" in fetch.UNIVERSE
