"""Tests for M-024: ust_tsmom_level BOND TSMOM sidecar.

Verifies core logic of tools/research/ust_tsmom.py without hitting yfinance.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tools.research.ust_tsmom import vol_target_basket


def _row(ticker, mom_12mo_pct, vol_90d_pct, signal):
    return {
        "ticker": ticker,
        "mom_12mo_pct": mom_12mo_pct,
        "vol_90d_annualized_pct": vol_90d_pct,
        "signal": signal,
    }


def test_vol_target_basket_returns_required_keys():
    """vol_target_basket must return longs, shorts, cash, signal_strength."""
    rows = [
        _row("TLT", mom_12mo_pct=5.0, vol_90d_pct=12.0, signal="long"),
        _row("SHY", mom_12mo_pct=-1.0, vol_90d_pct=4.0, signal="short"),
    ]
    result = vol_target_basket(rows)
    for key in ("longs", "shorts", "cash", "expected_signal_strength", "n_valid"):
        assert key in result


def test_positive_mom_goes_long():
    """Ticker with positive 12mo return (signal=long) must appear in longs."""
    rows = [_row("TLT", mom_12mo_pct=8.0, vol_90d_pct=10.0, signal="long")]
    result = vol_target_basket(rows)
    assert "TLT" in result["longs"]
    assert "TLT" not in result["shorts"]


def test_negative_mom_goes_short():
    """Ticker with negative 12mo return (signal=short) must appear in shorts."""
    rows = [_row("HYG", mom_12mo_pct=-5.0, vol_90d_pct=8.0, signal="short")]
    result = vol_target_basket(rows)
    assert "HYG" in result["shorts"]
    assert "HYG" not in result["longs"]


def test_vol_target_position_size_capped_at_100():
    """Position size must be capped at 100% (1x notional per leg)."""
    rows = [_row("TLT", mom_12mo_pct=3.0, vol_90d_pct=1.0, signal="long")]
    result = vol_target_basket(rows, vol_target_pct=10.0)
    # vol=1% → raw size = 10/1 = 1000%, should be capped at 100%
    tlt_size = rows[0].get("vol_target_position_size_pct", 0)
    assert tlt_size <= 100.0


def test_zero_vol_goes_to_cash():
    """Ticker with zero vol (signal=short) must go to cash (0 size)."""
    rows = [_row("SHY", mom_12mo_pct=-1.0, vol_90d_pct=0.0, signal="short")]
    result = vol_target_basket(rows)
    assert "SHY" in result["cash"]


def test_no_valid_rows_returns_error():
    """Empty rows must return error dict."""
    result = vol_target_basket([{"error": "fetch failed"}])
    assert "error" in result


def test_strong_signal_when_both_long_and_short():
    """STRONG signal requires at least one long AND one short."""
    rows = [
        _row("TLT", mom_12mo_pct=5.0, vol_90d_pct=10.0, signal="long"),
        _row("HYG", mom_12mo_pct=-3.0, vol_90d_pct=12.0, signal="short"),
    ]
    result = vol_target_basket(rows)
    assert result["expected_signal_strength"] == "STRONG"
