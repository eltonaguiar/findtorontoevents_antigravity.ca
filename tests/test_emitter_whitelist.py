"""Tests for alpha_engine.emitter_whitelist (T2-01 / T2-02)."""
import os

import pytest

from alpha_engine.emitter_whitelist import (
    HARDCODED_TOXIC_PAIRS,
    INVERSE_ML_SLEEVE_STRATEGIES,
    evaluate_emitter_registry_gate,
    is_toxic_pair,
    passes_emitter_registry_gate,
    passes_inverse_ml_sleeve_gate,
)


def test_hardcoded_toxic_pairs():
    # Test only the HARDCODED set — the registry may dynamically add pairs
    # at runtime (e.g. COMMODITY/multi_asset_copytrader if pf < 1.2 and n >= 20),
    # so is_toxic_pair() is not stable for non-hardcoded pairs.
    assert ("CRYPTO", "quan_engine") in HARDCODED_TOXIC_PAIRS
    assert ("COMMODITY", "cta_replicator") in HARDCODED_TOXIC_PAIRS
    assert ("FOREX", "multi_asset_copytrader") in HARDCODED_TOXIC_PAIRS
    assert ("COMMODITY", "multi_asset_copytrader") not in HARDCODED_TOXIC_PAIRS


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


def test_inverse_ml_sleeve_off_is_noop(monkeypatch):
    monkeypatch.delenv("INVERSE_ML_BTC_15M_ENABLED", raising=False)
    pick = {"asset_class": "CRYPTO", "strategy": "quan_engine", "symbol": "BTCUSDT"}
    assert passes_inverse_ml_sleeve_gate(pick) is True


def test_inverse_ml_sleeve_blocks_non_sleeve_crypto(monkeypatch):
    monkeypatch.setenv("INVERSE_ML_BTC_15M_ENABLED", "1")
    pick = {"asset_class": "CRYPTO", "strategy": "quan_engine", "symbol": "BTCUSDT"}
    assert passes_inverse_ml_sleeve_gate(pick) is False
    assert "inverse_ml_sleeve_block" in (pick.get("_hf_quality_gate_reason") or "")


@pytest.mark.parametrize("strategy", sorted(INVERSE_ML_SLEEVE_STRATEGIES))
def test_inverse_ml_sleeve_allows_btc_ada(monkeypatch, strategy):
    monkeypatch.setenv("INVERSE_ML_BTC_15M_ENABLED", "1")
    pick = {"asset_class": "CRYPTO", "strategy": strategy, "symbol": "BTCUSDT"}
    assert passes_inverse_ml_sleeve_gate(pick) is True


def test_inverse_ml_sleeve_allows_non_crypto(monkeypatch):
    monkeypatch.setenv("INVERSE_ML_BTC_15M_ENABLED", "1")
    pick = {"asset_class": "EQUITY", "strategy": "quan_engine", "symbol": "AAPL"}
    assert passes_inverse_ml_sleeve_gate(pick) is True
