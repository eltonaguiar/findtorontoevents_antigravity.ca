"""Tests for alpha_engine/equity_earnings_loader.py."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from alpha_engine.equity_earnings_loader import load_pead_events_from_earnings_cache


def test_load_pead_events_from_earnings_cache_returns_list():
    events = load_pead_events_from_earnings_cache()
    assert isinstance(events, list)
    for ev in events:
        assert ev.get("symbol")
        assert ev.get("earnings_date")
        assert ev.get("asset_class") == "EQUITY"
        assert float(ev.get("surprise_pct", 0)) >= 5.0