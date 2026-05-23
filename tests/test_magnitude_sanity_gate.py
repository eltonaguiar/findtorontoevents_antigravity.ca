"""M-108: tests for the magnitude-sanity gate."""
from alpha_engine.magnitude_sanity_gate import (
    implied_move_pct, is_magnitude_plausible, max_move_for,
)


def test_implied_move_basic():
    assert implied_move_pct(100.0, 110.0) == 0.10
    assert implied_move_pct(100.0, 90.0) == 0.10
    assert implied_move_pct(100.0, None) is None
    assert implied_move_pct(0, 110.0) is None


def test_per_class_caps():
    assert max_move_for("CRYPTO") == 0.25
    assert max_move_for("FOREX") == 0.06
    assert max_move_for("BOND") == 0.05
    assert max_move_for(None) == 0.20  # default


def test_plausible_crypto_pick_passes():
    # 8% TP on a crypto pick — within the 25% cap
    ok, reason = is_magnitude_plausible({
        "asset_class": "CRYPTO", "entry_price": 100.0,
        "take_profit": 108.0, "stop_loss": 96.0})
    assert ok and reason == ""


def test_fetusdt_style_fantasy_tp_rejected():
    # The real M-108 motivating case: ~40% implied TP on a 1-day crypto pick.
    ok, reason = is_magnitude_plausible({
        "asset_class": "CRYPTO", "entry_price": 1.00,
        "take_profit": 1.40, "stop_loss": 0.95})
    assert ok is False
    assert "TP_MAGNITUDE_IMPLAUSIBLE" in reason


def test_forex_tight_cap():
    # 10% TP is fine for crypto but fantasy for FX (6% cap).
    ok, reason = is_magnitude_plausible({
        "asset_class": "FOREX", "entry_price": 1.10,
        "take_profit": 1.21, "stop_loss": 1.08})
    assert ok is False and "TP_MAGNITUDE_IMPLAUSIBLE" in reason


def test_implausible_stop_loss_rejected():
    ok, reason = is_magnitude_plausible({
        "asset_class": "EQUITY", "entry_price": 100.0,
        "take_profit": 105.0, "stop_loss": 50.0})  # 50% SL
    assert ok is False and "SL_MAGNITUDE_IMPLAUSIBLE" in reason


def test_sub_noise_tp_rejected():
    # TP only 5bp away — below the round-trip-cost floor.
    ok, reason = is_magnitude_plausible({
        "asset_class": "CRYPTO", "entry_price": 100.0,
        "take_profit": 100.05, "stop_loss": 96.0})
    assert ok is False and "TP_SUB_NOISE" in reason


def test_fail_open_on_missing_prices():
    # No entry / no TP-SL -> this gate does not fail it (a different gate
    # owns missing-TP/SL).
    assert is_magnitude_plausible({"asset_class": "CRYPTO"})[0] is True
    assert is_magnitude_plausible(
        {"asset_class": "CRYPTO", "entry_price": 100.0})[0] is True
