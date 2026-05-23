"""Tests for M-023: sector_dual_momentum_12_1 ETF opt-in sidecar.

Verifies core logic of tools/research/sector_dual_momentum.py without
hitting yfinance (uses synthetic data to test Antonacci GEM logic).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tools.research.sector_dual_momentum import build_decision

SECTORS = {"XLE", "XLF", "XLK", "XLV", "XLI"}


def _row(ticker, mom):
    return {"ticker": ticker, "mom_12_1_pct": mom}


def _make_rows(spy_mom, sector_moms):
    rows = [_row("SPY", spy_mom)]
    for t, m in sector_moms.items():
        rows.append(_row(t, m))
    return rows


def test_risk_on_returns_top_sectors():
    """SPY mom > 0 must produce risk_on with top-3 sector basket."""
    rows = _make_rows(
        spy_mom=8.0,
        sector_moms={"XLK": 15.0, "XLE": 12.0, "XLV": 10.0, "XLI": 3.0, "XLF": 2.0},
    )
    result = build_decision(rows, sectors=SECTORS, top_n=3)
    assert result["regime"] == "risk_on"
    assert "XLK" in result["basket"]
    assert "XLE" in result["basket"]
    assert "XLV" in result["basket"]


def test_risk_off_routes_to_agg():
    """SPY mom <= 0 must produce risk_off with basket = [AGG]."""
    rows = _make_rows(
        spy_mom=-3.0,
        sector_moms={"XLK": 5.0, "XLE": 3.0, "XLV": 1.0},
    )
    result = build_decision(rows, sectors=SECTORS, top_n=3)
    assert result["regime"] == "risk_off"
    assert result["basket"] == ["AGG"]


def test_missing_spy_returns_error():
    """Rows without SPY must return error dict."""
    rows = [_row("XLK", 10.0), _row("XLE", 5.0)]
    result = build_decision(rows, sectors=SECTORS)
    assert "error" in result


def test_result_contains_required_keys():
    """build_decision must return all required structural keys."""
    rows = _make_rows(spy_mom=5.0, sector_moms={"XLK": 10.0, "XLE": 8.0})
    result = build_decision(rows, sectors=SECTORS, top_n=2)
    for key in ("regime", "basket", "sector_ranking", "expected_signal_strength"):
        assert key in result, f"Missing key: {key}"


def test_sector_ranking_sorted_descending():
    """sector_ranking must be sorted by mom_12_1_pct descending."""
    rows = _make_rows(
        spy_mom=3.0,
        sector_moms={"XLK": 5.0, "XLE": 15.0, "XLV": 8.0},
    )
    result = build_decision(rows, sectors=SECTORS, top_n=2)
    ranking = result["sector_ranking"]
    moms = [r["mom_12_1_pct"] for r in ranking]
    assert moms == sorted(moms, reverse=True)
