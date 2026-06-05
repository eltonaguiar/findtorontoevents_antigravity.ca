"""Tests for EAGLE2 Phase 0 concentration and depromotion gates."""
from audit_trail.quality_gates import (
    BLOCKED_ASSET_SOURCE_PAIRS,
    BLOCKED_ASSET_STRATEGY_PAIRS,
    BLOCKED_SOURCE_SYSTEMS,
    passes_active_gate,
)
from alpha_engine.eagle2_class_source_cap import enforce_class_single_source_cap


def _pick(symbol="BTCUSDT", source="incubator_gainer", ac="CRYPTO", score=50, strategy="test_strat"):
    return {
        "symbol": symbol,
        "source_system": source,
        "asset_class": ac,
        "strategy": strategy,
        "smart_score": score,
        "ml_composite": score,
        "status": "OPEN",
        "direction": "LONG",
        "entry_price": 100.0,
        "take_profit": 110.0,
        "stop_loss": 95.0,
        "score": score,
        "confidence": 0.8,
        "trust_label": "PROVEN",
        "timestamp": "2026-06-02T12:00:00+00:00",
    }


def test_single_source_cap_trims_dominant_low_scored():
    picks = [
        _pick(source="incubator_gainer", score=90),
        _pick(source="incubator_gainer", score=80),
        _pick(source="incubator_gainer", score=70),
        _pick(source="alpha_engine", score=60),
    ]
    out, stats = enforce_class_single_source_cap(picks, max_share=0.60)
    assert len(out) == 3
    assert stats["trimmed"] == 1
    sources = [p["source_system"] for p in out]
    assert sources.count("incubator_gainer") == 2


def test_single_source_cap_no_trim_when_balanced():
    picks = [
        _pick(source="a", score=90),
        _pick(source="b", score=80),
        _pick(source="c", score=70),
    ]
    out, stats = enforce_class_single_source_cap(picks, max_share=0.60)
    assert len(out) == 3
    assert stats["trimmed"] == 0


def test_incubator_gainer_blocked_for_crypto():
    assert ("CRYPTO", "incubator_gainer") in BLOCKED_ASSET_SOURCE_PAIRS
    assert "incubator_gainer" in BLOCKED_SOURCE_SYSTEMS


def test_regime_terminal_blocked_equity_crypto_forex():
    assert ("EQUITY", "regime_terminal") in BLOCKED_ASSET_STRATEGY_PAIRS
    assert ("CRYPTO", "regime_terminal") in BLOCKED_ASSET_SOURCE_PAIRS
    assert ("FOREX", "regime_terminal") in BLOCKED_ASSET_SOURCE_PAIRS


def test_equity_dragger_strategies_blocked_2026_06_05():
    """Edge hunt P0: block copytrader + regime_accumulation on EQUITY emits."""
    assert ("EQUITY", "multi_asset_copytrader") in BLOCKED_ASSET_STRATEGY_PAIRS
    assert ("EQUITY", "regime_accumulation") in BLOCKED_ASSET_STRATEGY_PAIRS
    pick = _pick(ac="EQUITY", strategy="multi_asset_copytrader", source="multi_asset_copytrader")
    assert passes_active_gate(pick) is False


def test_incubator_gainer_rejected_by_active_gate():
    pick = _pick(source="incubator_gainer", ac="CRYPTO", strategy="gainer_scout")
    assert passes_active_gate(pick) is False
