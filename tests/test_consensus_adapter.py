from strategy_registry.adapters.consensus_adapter import consensus_pick_to_envelope
from strategy_registry.envelope_schema import validate_envelope

def test_consensus_pick_converts():
    pick = {
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "confidence": 0.85,
        "entry_price": 65000,
        "take_profit": 70000,
        "stop_loss": 62000,
        "strategy": "connors_rsi2",
        "source_systems": ["alpha_engine", "mercury2", "kimi"],
        "agreement_count": 3,
    }
    envelope = consensus_pick_to_envelope(pick)
    assert envelope["strategy_id"].startswith("consensus_")
    assert envelope["type"] == "consensus"
    assert envelope["source_system"] == "cross_aggregation"
    assert "BTCUSDT" in envelope["name"]

def test_consensus_envelope_validates():
    pick = {
        "symbol": "ETHUSDT",
        "direction": "SHORT",
        "confidence": 0.70,
        "agreement_count": 2,
    }
    envelope = consensus_pick_to_envelope(pick)
    ok, errors = validate_envelope(envelope)
    assert ok is True, f"Validation errors: {errors}"
