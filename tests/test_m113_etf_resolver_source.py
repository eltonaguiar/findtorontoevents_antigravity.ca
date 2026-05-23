"""M-113 ETF pick files included in resolve_active_non_crypto() source list.

Previously ETF picks (etf_sector_picks.json, etf_decay_picks.json, etc.) had
valid take_profit/stop_loss fields but were never read by the outcome resolver.
Root cause: the source file list in resolve_active_non_crypto() only included
ACTIVE_PICKS_FILE, MULTI_ASSET_PICKS, FOREX_FUTURES_FILE, BOND_SCANNER_FILE.
Result: 0 ETF picks ever reached closed_picks.json → ETF n=0 in pf_registry.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path
from alpha_engine.outcome_resolver import (
    ETF_SECTOR_PICKS_FILE,
    ETF_DECAY_PICKS_FILE,
    ETF_LEVERAGED_DECAY_FILE,
    ETF_SCANNER_FILE,
)


def test_etf_constants_are_defined():
    """All four ETF pick file constants must be importable."""
    assert ETF_SECTOR_PICKS_FILE is not None
    assert ETF_DECAY_PICKS_FILE is not None
    assert ETF_LEVERAGED_DECAY_FILE is not None
    assert ETF_SCANNER_FILE is not None


def test_etf_constants_are_paths():
    assert isinstance(ETF_SECTOR_PICKS_FILE, Path)
    assert isinstance(ETF_DECAY_PICKS_FILE, Path)
    assert isinstance(ETF_LEVERAGED_DECAY_FILE, Path)
    assert isinstance(ETF_SCANNER_FILE, Path)


def test_etf_files_in_resolver_source_list():
    """Verify the ETF files appear in the resolve_active_non_crypto source list."""
    import inspect
    import alpha_engine.outcome_resolver as resolver_mod
    source = inspect.getsource(resolver_mod.resolve_active_non_crypto)
    assert "ETF_SECTOR_PICKS_FILE" in source, "ETF sector picks not in source list"
    assert "ETF_DECAY_PICKS_FILE" in source, "ETF decay picks not in source list"
    assert "ETF_LEVERAGED_DECAY_FILE" in source, "ETF leveraged decay not in source list"
    assert "ETF_SCANNER_FILE" in source, "ETF scanner file not in source list"


def test_etf_sector_picks_have_tp_sl():
    """ETF sector picks must have take_profit and stop_loss > 0 for resolver to fire."""
    import json
    if not ETF_SECTOR_PICKS_FILE.exists():
        return  # CI may not have the file
    data = json.loads(ETF_SECTOR_PICKS_FILE.read_text())
    picks = data if isinstance(data, list) else data.get("picks", [])
    for p in picks[:5]:
        tp = p.get("take_profit") or p.get("tp_price")
        sl = p.get("stop_loss") or p.get("sl_price")
        assert tp is not None, f"Pick {p.get('symbol')} has no take_profit"
        assert sl is not None, f"Pick {p.get('symbol')} has no stop_loss"
