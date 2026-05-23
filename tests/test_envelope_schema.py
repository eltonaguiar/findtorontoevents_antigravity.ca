import pytest
from strategy_registry.envelope_schema import validate_envelope

def test_valid_envelope_passes():
    envelope = {
        "strategy_id": "opp_20260304_btc_001",
        "name": "Opposite Theory BTC",
        "type": "opposite",
        "source_system": "alpha_engine",
        "parameters": {"lookback": 24},
        "backtest_results": {
            "tier_1": {"passed": True, "sharpe_ratio": 1.5, "win_rate": 62, "max_drawdown": -10, "trades": 50, "total_return": 30, "pair": "BTC/USDT", "direction": "SHORT"},
        },
        "tags": {"symbol_scope": "single_symbol", "direction_bias": "short_only", "theory": "opposite"},
        "generated_at": "2026-03-04T12:00:00Z",
    }
    ok, errors = validate_envelope(envelope)
    assert ok is True
    assert errors == []

def test_missing_fields_fails():
    envelope = {"name": "Broken"}
    ok, errors = validate_envelope(envelope)
    assert ok is False
    assert "strategy_id" in str(errors)

def test_bad_type_fails():
    envelope = {
        "strategy_id": "x", "name": "x", "type": 123,
        "source_system": "alpha_engine",
        "backtest_results": {}, "tags": {}, "generated_at": "2026-03-04T12:00:00Z",
    }
    ok, errors = validate_envelope(envelope)
    assert ok is False
