"""Unit tests for tools/clean_ingest_v2.py"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools.clean_ingest_v2 import validate_pick_row, entry_drift_pct


def test_accepts_clean_crypto_short():
    dec = validate_pick_row({
        "symbol": "BTCUSDT",
        "asset_class": "CRYPTO",
        "direction": "SHORT",
        "entry_price": 100.0,
    }, spot_price=100.5)
    assert dec.ok, dec.reasons


def test_rejects_entry_drift():
    dec = validate_pick_row({
        "symbol": "SPY",
        "asset_class": "ETF",
        "entry_price": 100.0,
    }, spot_price=120.0)
    assert not dec.ok
    assert any("entry_drift" in r for r in dec.reasons)


def test_rejects_tp_hit_replay():
    dec = validate_pick_row({
        "symbol": "ETHUSDT",
        "asset_class": "CRYPTO",
        "entry_price": 3000.0,
        "tp_fill_method": "TP_HIT_REPLAY",
    })
    assert not dec.ok
    assert "tp_hit_replay_inflates_wr" in dec.reasons


def test_entry_drift_pct():
    assert entry_drift_pct(110, 100) == 10.0