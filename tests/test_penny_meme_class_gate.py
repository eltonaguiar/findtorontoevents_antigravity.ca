"""Tests for the class-wide PENNY_STOCK / MEMECOIN quality gate (2026-05-15).

The repo previously had only strategy-PAIR blocks for MEMECOIN and zero
gating for PENNY_STOCK. `passes_penny_meme_class_gate` blocks both classes
outright, kill-switchable via PENNY_MEME_CLASS_GATE_ENABLED=0.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audit_trail.quality_gates import passes_penny_meme_class_gate


def _pick(asset_class: str) -> dict:
    return {"symbol": "FOO", "strategy": "s", "asset_class": asset_class}


def test_blocks_memecoin(monkeypatch):
    monkeypatch.delenv("PENNY_MEME_CLASS_GATE_ENABLED", raising=False)
    assert passes_penny_meme_class_gate(_pick("MEMECOIN")) is False


def test_blocks_penny_stock(monkeypatch):
    monkeypatch.delenv("PENNY_MEME_CLASS_GATE_ENABLED", raising=False)
    assert passes_penny_meme_class_gate(_pick("PENNY_STOCK")) is False


def test_passes_crypto(monkeypatch):
    monkeypatch.delenv("PENNY_MEME_CLASS_GATE_ENABLED", raising=False)
    assert passes_penny_meme_class_gate(_pick("CRYPTO")) is True


def test_passes_equity(monkeypatch):
    monkeypatch.delenv("PENNY_MEME_CLASS_GATE_ENABLED", raising=False)
    assert passes_penny_meme_class_gate(_pick("EQUITY")) is True


def test_kill_switch_disables_gate(monkeypatch):
    monkeypatch.setenv("PENNY_MEME_CLASS_GATE_ENABLED", "0")
    assert passes_penny_meme_class_gate(_pick("MEMECOIN")) is True
    assert passes_penny_meme_class_gate(_pick("PENNY_STOCK")) is True


def test_case_insensitive(monkeypatch):
    monkeypatch.delenv("PENNY_MEME_CLASS_GATE_ENABLED", raising=False)
    for ac in ("memecoin", " MemeCoin ", "penny_stock", "Penny_Stock"):
        assert passes_penny_meme_class_gate(_pick(ac)) is False, ac


def test_missing_asset_class_passes(monkeypatch):
    monkeypatch.delenv("PENNY_MEME_CLASS_GATE_ENABLED", raising=False)
    assert passes_penny_meme_class_gate({"symbol": "FOO"}) is True
