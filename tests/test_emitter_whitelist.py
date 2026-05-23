"""Tests for alpha_engine.emitter_whitelist (T2-01 / T2-02)."""
import os

import pytest

from alpha_engine.emitter_whitelist import (
    HARDCODED_TOXIC_PAIRS,
    evaluate_emitter_registry_gate,
    is_toxic_pair,
    passes_emitter_registry_gate,
)


def test_hardcoded_toxic_pairs():
    assert is_toxic_pair("CRYPTO", "quan_engine")
    assert is_toxic_pair("COMMODITY", "cta_replicator")
    assert is_toxic_pair("FOREX", "multi_asset_copytrader")
    assert not is_toxic_pair("COMMODITY", "multi_asset_copytrader")


def test_toxic_pick_rejected(monkeypatch):
    monkeypatch.setenv("EMITTER_REGISTRY_GATE", "1")
    pick = {
        "asset_class": "CRYPTO",
        "strategy": "quan_engine",
        "symbol": "BTCUSDT",
        "source_system": "quan_engine",
    }
    assert passes_emitter_registry_gate(pick) is False
    assert "toxic" in (pick.get("_hf_quality_gate_reason") or "")


def test_whitelist_shadow_by_default(monkeypatch):
    monkeypatch.setenv("EMITTER_REGISTRY_GATE", "1")
    monkeypatch.delenv("EMITTER_WHITELIST_ENFORCE", raising=False)
    pick = {
        "asset_class": "EQUITY",
        "strategy": "totally_unknown_strategy_xyz",
        "symbol": "AAPL",
    }
    assert passes_emitter_registry_gate(pick) is True
    verdict = pick.get("_emitter_registry_gate") or {}
    assert verdict.get("would_block") is True


def test_whitelist_enforce_blocks_unknown(monkeypatch):
    monkeypatch.setenv("EMITTER_REGISTRY_GATE", "1")
    monkeypatch.setenv("EMITTER_WHITELIST_ENFORCE", "1")
    pick = {
        "asset_class": "EQUITY",
        "strategy": "totally_unknown_strategy_xyz",
        "symbol": "AAPL",
    }
    assert passes_emitter_registry_gate(pick) is False


def test_manual_allowlist_seed(monkeypatch):
    monkeypatch.setenv("EMITTER_REGISTRY_GATE", "1")
    monkeypatch.setenv("EMITTER_WHITELIST_ENFORCE", "1")
    pick = {
        "asset_class": "FOREX",
        "strategy": "cta_replicator",
        "symbol": "EURUSD=X",
    }
    assert passes_emitter_registry_gate(pick) is True
