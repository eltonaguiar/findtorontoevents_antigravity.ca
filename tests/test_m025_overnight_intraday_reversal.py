"""Tests for M-025: overnight_intraday_reversal EQUITY sidecar.

Verifies core logic of tools/research/overnight_intraday_reversal.py
without hitting yfinance.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tools.research.overnight_intraday_reversal import rank_and_basket


def _row(ticker, intraday_pct):
    return {"ticker": ticker, "intraday_return_pct": intraday_pct}


def _make_rows(n=14):
    """Generate n rows with varied intraday returns for testing."""
    return [_row(f"SYM{i:02d}", intraday_pct=(i - n // 2) * 0.5) for i in range(n)]


def test_longs_are_worst_intraday_losers():
    """Bottom-quintile intraday losers must appear in longs (overnight bounce)."""
    rows = [
        _row("LOSER1", -3.0),
        _row("LOSER2", -2.5),
        _row("MID1", 0.0),
        _row("MID2", 0.5),
        _row("MID3", 1.0),
        _row("WINNER1", 2.5),
        _row("WINNER2", 3.0),
        _row("MID4", -0.5),
        _row("MID5", -1.0),
        _row("MID6", 1.5),
        _row("MID7", -1.5),
        _row("WINNER3", 2.0),
    ]
    result = rank_and_basket(rows, quintile=3)
    assert "LOSER1" in result["longs"]
    assert "LOSER2" in result["longs"]


def test_shorts_are_best_intraday_winners():
    """Top-quintile intraday winners must appear in shorts (overnight reversal)."""
    rows = _make_rows(14)
    result = rank_and_basket(rows, quintile=3)
    # The best intraday performer should be in shorts
    best = max(rows, key=lambda r: r["intraday_return_pct"])
    assert best["ticker"] in result["shorts"]


def test_insufficient_rows_returns_error():
    """Fewer rows than quintile*2 must return error."""
    rows = [_row("A", 0.5), _row("B", -0.5)]
    result = rank_and_basket(rows, quintile=3)
    assert "error" in result


def test_result_required_keys():
    """rank_and_basket must return all required structural keys."""
    rows = _make_rows(14)
    result = rank_and_basket(rows, quintile=3)
    for key in ("longs", "shorts", "neutrals", "n_valid", "expected_signal_strength"):
        assert key in result


def test_longs_plus_shorts_plus_neutrals_equals_n_valid():
    """longs + shorts + neutrals must account for all valid rows."""
    rows = _make_rows(14)
    result = rank_and_basket(rows, quintile=3)
    total = len(result["longs"]) + len(result["shorts"]) + len(result["neutrals"])
    assert total == result["n_valid"]


def test_strong_signal_on_big_loser():
    """STRONG signal fires when worst intraday return magnitude > 1.0%."""
    rows = [
        _row("BIG_LOSER", -3.5),
        _row("MED_LOSER", -1.5),
        _row("FLAT", 0.0),
        _row("MED_WIN", 1.5),
        _row("BIG_WIN", 3.0),
        _row("A", -0.5), _row("B", 0.5), _row("C", -1.0),
        _row("D", 1.0), _row("E", -0.2), _row("F", 0.2), _row("G", -0.1),
    ]
    result = rank_and_basket(rows, quintile=3)
    assert result["expected_signal_strength"] == "STRONG"
