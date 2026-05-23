"""Unit tests for multi-asset non-crypto signal quality gate."""

from multi_asset.scanner import _apply_non_crypto_quality_gate


def _signal(**overrides):
    base = {
        "strategy": "test_strategy",
        "symbol": "CL=F",
        "category": "commodity",
        "direction": "SHORT",
        "entry_price": 100.0,
        "take_profit": 92.0,
        "stop_loss": 104.0,
        "confidence": 0.75,
        "risk_reward": 2.0,
    }
    base.update(overrides)
    return base


def test_quality_gate_rejects_low_confidence_non_crypto_signal():
    signals = [_signal(symbol="HG=F", confidence=0.11)]
    kept, rejected = _apply_non_crypto_quality_gate(signals)
    assert kept == []
    assert rejected.get("low_confidence", 0) == 1


def test_quality_gate_rejects_excessive_tp_sl_distance_non_crypto_signal():
    # Mirrors recent CL=F failure mode in pick_quality_monitor:
    # TP distance 19.7% and SL distance 14.8% exceed commodity limits.
    signals = [_signal(symbol="CL=F", take_profit=80.3, stop_loss=114.8)]
    kept, rejected = _apply_non_crypto_quality_gate(signals)
    assert kept == []
    assert rejected.get("tp_too_far", 0) == 1
    assert rejected.get("sl_too_far", 0) == 1


def test_quality_gate_keeps_valid_non_crypto_signal():
    signals = [_signal(symbol="ZN=F", category="futures", take_profit=95.0, stop_loss=103.0)]
    kept, rejected = _apply_non_crypto_quality_gate(signals)
    assert len(kept) == 1
    assert rejected == {}


def test_quality_gate_skips_crypto_signals():
    signals = [_signal(symbol="BTCUSDT", category="crypto", confidence=0.1, risk_reward=0.2)]
    kept, rejected = _apply_non_crypto_quality_gate(signals)
    assert len(kept) == 1
    assert rejected == {}
