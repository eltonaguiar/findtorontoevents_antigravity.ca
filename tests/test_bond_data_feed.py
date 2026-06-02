"""BONDS#7 bond data-feed scaffold — network-free smoke tests (data_fetcher mocked)."""
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verified_strategies"))
import bond_data_feed as bdf  # noqa: E402


def _fake_df(last=100.0, n=300):
    return pd.DataFrame({"close": [last] * n})


def test_universe_constants_present():
    assert "TLT" in bdf.BOND_ETFS and "AGG" in bdf.BOND_ETFS
    assert bdf.YIELD_SERIES["UST10Y"] == "DGS10"
    assert bdf.YIELD_SERIES["T10Y2Y"] == "T10Y2Y"


def test_fetch_bond_etfs_handles_ok_and_failure(monkeypatch):
    def fake_fetch(sym, period_days=1260):
        return (_fake_df(99.5), "yfinance") if sym == "TLT" else (None, "none")
    monkeypatch.setattr(bdf.data_fetcher, "fetch_ohlcv", fake_fetch)
    out = bdf.fetch_bond_etfs()
    assert out["TLT"]["ok"] is True and out["TLT"]["last_close"] == 99.5
    assert out["AGG"]["ok"] is False and out["AGG"]["rows"] == 0


def test_fetch_bond_etfs_degrades_on_exception(monkeypatch):
    def boom(sym, period_days=1260):
        raise RuntimeError("network down")
    monkeypatch.setattr(bdf.data_fetcher, "fetch_ohlcv", boom)
    out = bdf.fetch_bond_etfs()
    assert all(v["ok"] is False for v in out.values())  # no crash, all degraded


def test_yield_curve_and_inversion(monkeypatch):
    def fake_fred(series_id, days_back=2000):
        vals = {"DGS3MO": 5.3, "DGS2": 4.8, "DGS10": 4.2, "T10Y2Y": -0.6}
        return pd.Series([vals[series_id]])
    monkeypatch.setattr(bdf.data_fetcher, "fetch_fred_series", fake_fred)
    yc = bdf.fetch_yield_curve()
    assert yc["UST10Y"]["ok"] and yc["UST10Y"]["latest"] == 4.2
    assert bdf.curve_is_inverted(yc) is True   # 10y-2y = -0.6 < 0


def test_inversion_none_when_missing(monkeypatch):
    monkeypatch.setattr(bdf.data_fetcher, "fetch_fred_series",
                        lambda *a, **k: None)
    assert bdf.curve_is_inverted(bdf.fetch_yield_curve()) is None
