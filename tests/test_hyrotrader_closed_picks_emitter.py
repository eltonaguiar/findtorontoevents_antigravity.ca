"""Tests for the hyrotrader closed-picks emitter.

The emitter materializes pf_registry-shaped rows from
`hyrotrader_journal.json` (real fills only) joined to `hyrotrader_picks.json`
on pick_id. These tests use synthetic data — never touch the real journal.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_emitter_module():
    """Load tools/hyrotrader_closed_picks_emitter.py without polluting sys.modules."""
    repo_root = Path(__file__).resolve().parent.parent
    src = repo_root / "tools" / "hyrotrader_closed_picks_emitter.py"
    spec = importlib.util.spec_from_file_location("hyrotrader_emitter", src)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["hyrotrader_emitter"] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def test_self_test_passes():
    mod = _load_emitter_module()
    assert mod._self_test() == 0


def test_open_trades_are_skipped():
    mod = _load_emitter_module()
    journal = {"trades": [
        {"pick_id": "X1", "symbol": "BTCUSDT", "direction": "LONG",
         "entry_time": "2026-05-25T10:00:00Z", "entry_price": 95000.0,
         "closed_at": None, "pnl_pct": None},  # open
        {"pick_id": "X2", "symbol": "ETHUSDT", "direction": "LONG",
         "entry_time": "2026-05-25T10:00:00Z", "entry_price": 3500.0,
         "closed_at": "2026-05-26T10:00:00Z", "pnl_pct": 0.02},  # closed
    ]}
    picks = {"picks": [
        {"id": "X1", "strategy": "alpha", "asset_class": "CRYPTO"},
        {"id": "X2", "strategy": "beta", "asset_class": "CRYPTO"},
    ]}
    rows = mod.emit(journal, picks)
    assert len(rows) == 1
    assert rows[0]["pick_id"] == "X2"
    assert rows[0]["status"] == "WIN"


def test_strategy_falls_back_to_journal_then_default():
    mod = _load_emitter_module()
    journal = {"trades": [
        {"pick_id": "missing", "symbol": "BTCUSDT", "direction": "LONG",
         "entry_time": "t", "entry_price": 1.0, "exit_price": 2.0,
         "closed_at": "t2", "pnl_pct": 1.0, "strategy": "journal_strategy",
         "asset_class": "CRYPTO"},
    ]}
    rows = mod.emit(journal, picks=None)
    assert len(rows) == 1
    assert rows[0]["strategy"] == "journal_strategy"  # picks empty → journal field used

    journal2 = {"trades": [
        {"pick_id": "missing", "symbol": "BTCUSDT", "direction": "LONG",
         "entry_time": "t", "closed_at": "t2", "pnl_pct": -0.1},
    ]}
    rows = mod.emit(journal2, picks=None)
    assert rows[0]["strategy"] == "hyrotrader_manual"  # nothing → default
    assert rows[0]["asset_class"] == "UNKNOWN"
    assert rows[0]["status"] == "LOSS"


def test_enhanced_picks_consulted_when_picks_missing():
    mod = _load_emitter_module()
    journal = {"trades": [
        {"pick_id": "E1", "symbol": "BTCUSDT", "direction": "LONG",
         "entry_time": "t", "closed_at": "t2", "pnl_pct": 0.5},
    ]}
    enhanced = {"picks": [
        {"id": "E1", "strategy": "enhanced_only", "asset_class": "ETF"},
    ]}
    rows = mod.emit(journal, picks=None, enhanced=enhanced)
    assert rows[0]["strategy"] == "enhanced_only"
    assert rows[0]["asset_class"] == "ETF"


def test_non_numeric_pnl_is_skipped():
    mod = _load_emitter_module()
    journal = {"trades": [
        {"pick_id": "B1", "symbol": "X", "direction": "LONG",
         "closed_at": "t", "pnl_pct": "not_a_number"},
        {"pick_id": "B2", "symbol": "Y", "direction": "LONG",
         "closed_at": "t", "pnl_pct": 0.01},
    ]}
    rows = mod.emit(journal, picks=None)
    assert len(rows) == 1
    assert rows[0]["pick_id"] == "B2"


def test_empty_journal_emits_zero_rows():
    mod = _load_emitter_module()
    assert mod.emit({"trades": []}, picks=None) == []
    assert mod.emit(None, picks=None) == []
