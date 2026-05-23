"""Smoke tests for adaptive stops, regime scoring, forward-test gates."""

from audit_trail.adaptive_stops import (
    calculate_adaptive_stop,
    get_vol_tier_percentages,
)
from audit_trail.forward_test_gates import forward_pick_passes_gates
from audit_trail.regime_scoring import get_market_weather, weather_adjusted_score


def test_crypto_vs_equity_vol_percentages_differ():
    c = get_vol_tier_percentages("BTCUSDT", "CRYPTO", crypto_tier="LOW")
    e = get_vol_tier_percentages("AAPL", "EQUITY", crypto_tier="LOW")
    assert c[1] < e[1]  # equity SL % wider than crypto LOW tier


def test_adaptive_stop_long_rr():
    # CLEAR_BULL tightens SL / widens TP vs UNKNOWN so net_rr clears 1.2 after equity commission
    tp, sl, rr = calculate_adaptive_stop(100.0, 2.0, "EQUITY", "CLEAR_BULL", vix=18.0)
    assert tp is not None and sl is not None
    assert tp > 100 and sl < 100
    assert rr >= 1.2


def test_forward_gate_rr():
    ok, _ = forward_pick_passes_gates(
        {
            "entry_price": 100,
            "tp_price": 103,
            "sl_price": 99,
            "direction": "LONG",
        }
    )
    assert ok


def test_forward_gate_rr_fail():
    ok, reason = forward_pick_passes_gates(
        {
            "entry_price": 100,
            "tp_price": 100.5,
            "sl_price": 99,
            "direction": "LONG",
        }
    )
    assert not ok
    assert "rr" in reason


def test_weather_and_adjust():
    w = get_market_weather(14.0, 2.0, 65.0)
    assert w == "CLEAR_BULL"
    adj = weather_adjusted_score(80.0, w, "momentum_breakout", active_position_count=0)
    assert 0 <= adj <= 100
