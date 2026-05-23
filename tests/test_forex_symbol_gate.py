"""Tests for the FOREX symbol gate — autopsy-killed pair blocking (2026-05-17)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audit_trail.quality_gates import (
    BLOCKED_SYMBOLS_BY_CLASS,
    passes_forex_symbol_gate,
)


def _pick(symbol: str, asset_class: str = "FOREX") -> dict:
    return {"symbol": symbol, "asset_class": asset_class, "strategy": "s"}


def test_blocked_forex_pairs_present():
    blk = BLOCKED_SYMBOLS_BY_CLASS["FOREX"]
    for s in ("NZDUSD=X", "EURJPY=X", "USDCHF=X"):
        assert s in blk, s


def test_blocks_killed_pairs(monkeypatch):
    monkeypatch.delenv("FOREX_SYMBOL_GATE_ENABLED", raising=False)
    for s in ("NZDUSD=X", "EURJPY=X", "USDCHF=X"):
        assert passes_forex_symbol_gate(_pick(s)) is False, s


def test_passes_good_forex_pairs(monkeypatch):
    monkeypatch.delenv("FOREX_SYMBOL_GATE_ENABLED", raising=False)
    # AUDUSD=X removed: blocked 2026-05-17 (cta_replicator n=8, WR=0%)
    for s in ("AUDJPY=X", "EURUSD=X", "GBPUSD=X"):
        assert passes_forex_symbol_gate(_pick(s)) is True, s


def test_case_insensitive(monkeypatch):
    monkeypatch.delenv("FOREX_SYMBOL_GATE_ENABLED", raising=False)
    assert passes_forex_symbol_gate(_pick("nzdusd=x")) is False
    assert passes_forex_symbol_gate(_pick(" EurJpy=X ")) is False


def test_kill_switch_disables(monkeypatch):
    monkeypatch.setenv("FOREX_SYMBOL_GATE_ENABLED", "0")
    assert passes_forex_symbol_gate(_pick("NZDUSD=X")) is True


def test_other_classes_unaffected(monkeypatch):
    monkeypatch.delenv("FOREX_SYMBOL_GATE_ENABLED", raising=False)
    # a CRYPTO pick with a coincidentally-matching symbol must still pass
    assert passes_forex_symbol_gate(_pick("NZDUSD=X", asset_class="CRYPTO")) is True
    assert passes_forex_symbol_gate(_pick("BTCUSDT", asset_class="CRYPTO")) is True


def test_missing_symbol_passes(monkeypatch):
    monkeypatch.delenv("FOREX_SYMBOL_GATE_ENABLED", raising=False)
    assert passes_forex_symbol_gate({"asset_class": "FOREX"}) is True
