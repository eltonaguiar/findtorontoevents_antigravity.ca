"""Tests for alpha_engine.growth_stock_screener.

Opt-in sidecar (per CLAUDE.md Wire-Up Rule). DEFAULT-OFF gated on
GROWTH_STOCK_SCREENER_ENABLED=1. All tests use synthetic data / stubs — no
live yfinance calls.
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from alpha_engine.growth_stock_screener import (
    MIN_REVENUE_GROWTH_PCT,
    RS_RATING_MIN,
    STRATEGY_NAME,
    TAKE_PROFIT_PCT,
    STOP_LOSS_PCT,
    _confidence_from_rs,
    compute_rs_rating,
    generate_picks,
    revenue_growth_pct,
    stage_2_uptrend,
)


# ---------------------------------------------------------------------------
# RS rating math
# ---------------------------------------------------------------------------
def test_rs_rating_top_symbol_gets_100_percentile():
    # 5 symbols, each with 260 daily closes. WINNER is the strongest uptrend.
    prices = {}
    for i, sym in enumerate(["A", "B", "C", "D", "WINNER"]):
        slope = 0.1 + 0.5 * i  # WINNER has steepest slope
        prices[sym] = [100.0 + slope * t for t in range(260)]
    rs = compute_rs_rating(prices)
    assert rs["WINNER"] == pytest.approx(100.0)
    assert rs["A"] == pytest.approx(0.0)
    # Monotonic: better slope -> higher percentile
    assert rs["A"] < rs["B"] < rs["C"] < rs["D"] < rs["WINNER"]


def test_rs_rating_excludes_short_history():
    prices = {
        "SHORT": [100.0] * 100,                    # < 252 -> excluded
        "OK_A": [100.0 + 0.1 * t for t in range(260)],
        "OK_B": [100.0 + 0.5 * t for t in range(260)],
    }
    rs = compute_rs_rating(prices)
    assert "SHORT" not in rs
    assert "OK_A" in rs and "OK_B" in rs


# ---------------------------------------------------------------------------
# Stage-2 uptrend
# ---------------------------------------------------------------------------
def test_stage_2_uptrend_passes_for_steady_uptrend():
    closes = [100.0 + 0.5 * i for i in range(260)]
    assert stage_2_uptrend(closes) is True


def test_stage_2_uptrend_rejects_downtrend():
    closes = [300.0 - 0.5 * i for i in range(260)]
    assert stage_2_uptrend(closes) is False


def test_stage_2_uptrend_rejects_far_from_52w_high():
    # Rise then collapse >50% from peak
    closes = [100.0 + 0.5 * i for i in range(252)] + [50.0] * 10
    assert stage_2_uptrend(closes) is False


def test_stage_2_uptrend_rejects_short_history():
    assert stage_2_uptrend([100.0] * 50) is False


# ---------------------------------------------------------------------------
# Revenue growth extraction
# ---------------------------------------------------------------------------
class _FakeRow:
    def __init__(self, values):
        self._values = values
    def tolist(self):
        return list(self._values)


class _FakeQF:
    def __init__(self, rows):
        # rows: dict[label] -> list[float] (newest-first)
        self._rows = rows
        self.index = list(rows.keys())
    @property
    def loc(self):
        return self
    def __getitem__(self, key):
        return _FakeRow(self._rows[key])


class _FakeTicker:
    def __init__(self, qf):
        self.quarterly_financials = qf


def test_revenue_growth_pct_30pct_yoy():
    qf = _FakeQF({"Total Revenue": [130.0, 125.0, 120.0, 100.0]})
    tk = _FakeTicker(qf)
    g = revenue_growth_pct(tk)
    assert g == pytest.approx(30.0, abs=1e-6)


def test_revenue_growth_pct_none_when_insufficient_quarters():
    qf = _FakeQF({"Total Revenue": [130.0, 125.0]})
    tk = _FakeTicker(qf)
    assert revenue_growth_pct(tk) is None


def test_revenue_growth_pct_none_when_missing_row():
    qf = _FakeQF({"Operating Income": [10.0, 9.0, 8.0, 7.0]})
    tk = _FakeTicker(qf)
    assert revenue_growth_pct(tk) is None


def test_revenue_growth_threshold_default_matches_user_config():
    # Default = 15.0 (user 2026-05-12 screenshot); upstream verbatim = 25.0.
    # Override via env GSS_MIN_REV_GROWTH_PCT.
    assert MIN_REVENUE_GROWTH_PCT == 15.0
    assert RS_RATING_MIN == 90


# ---------------------------------------------------------------------------
# Pick generation (default-off + shape)
# ---------------------------------------------------------------------------
def test_generate_picks_default_off_returns_empty(monkeypatch):
    monkeypatch.delenv("GROWTH_STOCK_SCREENER_ENABLED", raising=False)
    assert generate_picks(["AAPL", "MSFT"]) == []


def test_generate_picks_off_even_with_universe(monkeypatch):
    monkeypatch.setenv("GROWTH_STOCK_SCREENER_ENABLED", "0")
    assert generate_picks(["AAPL"]) == []


def test_confidence_from_rs_mapping():
    assert _confidence_from_rs(90) == pytest.approx(0.60)
    assert _confidence_from_rs(100) == pytest.approx(0.75)
    mid = _confidence_from_rs(95)
    assert 0.60 < mid < 0.75


def test_pick_shape_required_fields_via_stubbed_pipeline(monkeypatch):
    """Bypass yfinance entirely; force one symbol through every gate."""
    monkeypatch.setenv("GROWTH_STOCK_SCREENER_ENABLED", "1")

    # Strong 260-bar uptrend with healthy volume
    closes = [100.0 + 0.5 * i for i in range(260)]
    volumes = [500_000] * 260

    class _FakeHist:
        def __init__(self):
            self._closes = closes
            self._volumes = volumes
        def __getitem__(self, key):
            if key == "Close":
                return _FakeRow(self._closes)
            if key == "Volume":
                return _FakeRow(self._volumes)
            raise KeyError(key)
        def __len__(self):
            return len(self._closes)

    fake_hist = _FakeHist()

    class _FakeInfoTicker:
        info = {"marketCap": 50_000_000_000}
        quarterly_financials = _FakeQF({"Total Revenue": [200.0, 180.0, 160.0, 100.0]})
        institutional_holders = None

    with patch("alpha_engine.growth_stock_screener._fetch_history",
               return_value=fake_hist), \
         patch("alpha_engine.growth_stock_screener._fetch_ticker",
               return_value=_FakeInfoTicker()):
        picks = generate_picks(["WINNER"], max_picks=5)

    assert len(picks) == 1
    p = picks[0]
    for field in ("symbol", "direction", "entry_price", "take_profit",
                  "stop_loss", "confidence", "strategy", "asset_class",
                  "source_system", "signal_strength"):
        assert field in p, f"missing required field: {field}"
    assert p["symbol"] == "WINNER"
    assert p["direction"] == "LONG"
    assert p["strategy"] == STRATEGY_NAME
    assert p["asset_class"] == "EQUITY"
    assert p["take_profit"] == pytest.approx(p["entry_price"] * (1 + TAKE_PROFIT_PCT))
    assert p["stop_loss"] == pytest.approx(p["entry_price"] * (1 - STOP_LOSS_PCT))
    assert 0.60 <= p["confidence"] <= 0.75
