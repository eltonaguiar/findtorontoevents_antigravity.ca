from strategy_registry.adapters.dna_adapter import dna_pick_to_envelope
from strategy_registry.envelope_schema import validate_envelope

def test_dna_pick_converts():
    pick = {
        "symbol": "ETHUSDT",
        "direction": "LONG",
        "entry_price": 3000,
        "take_profit": 3300,
        "stop_loss": 2800,
        "strategy": "RSI2_FearGreed_Confluence",
        "confidence": 0.72,
        "dna_hash": "abc123",
    }
    envelope = dna_pick_to_envelope(pick)
    assert envelope["type"] == "dna"
    assert envelope["source_system"] == "genome"
    assert "dna_hash" in envelope["parameters"]

def test_dna_envelope_validates():
    pick = {
        "symbol": "SOLUSDT",
        "direction": "SHORT",
        "confidence": 0.65,
        "dna_hash": "xyz789",
    }
    envelope = dna_pick_to_envelope(pick)
    ok, errors = validate_envelope(envelope)
    assert ok is True, f"Validation errors: {errors}"
