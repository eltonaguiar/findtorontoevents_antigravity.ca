"""Unit tests for tools/forex_unblock_tracker.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import patch
from forex_unblock_tracker import run_tracker


def _make_pick(strategy, status, pnl_pct):
    return {
        "asset_class": "FOREX",
        "strategy": strategy,
        "status": status,
        "pnl_pct": pnl_pct,
    }


def test_blocked_when_below_threshold(capsys):
    """Should report BLOCKED when no strategy meets n>=30."""
    picks = [
        _make_pick("forex-rsi-ema-scout", "WON", 1.5),
        _make_pick("forex-rsi-ema-scout", "LOST", -1.0),
    ] * 11  # n=22
    dashboard = {"picks": {"recent_closed": picks}}

    with patch("forex_unblock_tracker.load_dashboard", return_value=dashboard):
        run_tracker()

    captured = capsys.readouterr()
    assert "BLOCKED" in captured.out
    assert "need 8 more picks" in captured.out
    assert "forex-rsi-ema-scout" in captured.out


def test_unblock_recommended_when_threshold_met(capsys):
    """Should report UNBLOCK RECOMMENDED when a strategy crosses the line."""
    picks = [
        _make_pick("forex-rsi-ema-scout", "WON", 1.5),
        _make_pick("forex-rsi-ema-scout", "LOST", -1.0),
    ] * 15  # n=30, WR=50%, PF=1.5
    dashboard = {"picks": {"recent_closed": picks}}

    with patch("forex_unblock_tracker.load_dashboard", return_value=dashboard):
        run_tracker()

    captured = capsys.readouterr()
    assert "UNBLOCK RECOMMENDED" in captured.out
    assert "forex-rsi-ema-scout" in captured.out


def test_non_forex_picks_ignored(capsys):
    """Should ignore picks that are not FOREX."""
    picks = [
        {"asset_class": "CRYPTO", "strategy": "st_fear_greed_contrarian", "status": "WON", "pnl_pct": 2.0},
        {"asset_class": "FOREX", "strategy": "forex-rsi-ema-scout", "status": "WON", "pnl_pct": 1.5},
    ] * 30
    dashboard = {"picks": {"recent_closed": picks}}

    with patch("forex_unblock_tracker.load_dashboard", return_value=dashboard):
        run_tracker()

    captured = capsys.readouterr()
    # Only the FOREX picks count, so n=30 for forex-rsi-ema-scout
    assert "UNBLOCK RECOMMENDED" in captured.out
    assert "Total resolved FOREX picks: 30" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
