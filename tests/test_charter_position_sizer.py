"""Tests for Charter §7 position sizer (P0.5-1).

Independent of the regime-adaptive sizer at alpha_engine/position_sizer.py.
"""
import math

import pytest

from alpha_engine.charter_position_sizer import (
    compute_position_size,
    daily_loss_kill_switch,
    validate_concentration,
)


EQUITY = 100_000.0


def _pick(**overrides):
    base = {
        "symbol": "BTCUSDT",
        "asset_class": "CRYPTO",
        "confidence": 1.0,
        "category": "swing",
        "sector": "crypto_majors",
    }
    base.update(overrides)
    return base


def test_explicit_extreme_vol_differentiates():
    # In normal vol regimes the per-class risk cap binds first (target 0.75% /
    # vol < per-class cap) — see test_per_class_risk_cap_clips_very_low_vol.
    # Vol-targeting math only differentiates when target/vol < per-class cap.
    # Force this with extreme vol where the cap no longer binds.
    high_vol = compute_position_size(
        _pick(category="long_term"), EQUITY, daily_vol_estimate=1.0)
    extreme_vol = compute_position_size(
        _pick(category="long_term"), EQUITY, daily_vol_estimate=2.0)
    assert extreme_vol < high_vol
    assert high_vol > 0


def test_default_vol_used_when_none():
    none_size = compute_position_size(_pick(), EQUITY, None)
    eq_size = compute_position_size(_pick(), EQUITY, 0.04)
    assert math.isclose(none_size, eq_size, rel_tol=1e-9)


def test_swing_notional_cap_caps_low_vol_bond():
    size = compute_position_size(
        _pick(asset_class="BOND", symbol="TLT", category="swing"),
        EQUITY,
        daily_vol_estimate=0.001,
    )
    assert size <= 0.01 * EQUITY + 1e-6


def test_long_term_allows_larger_position():
    swing = compute_position_size(
        _pick(category="swing", asset_class="EQUITY"), EQUITY, 0.005)
    longt = compute_position_size(
        _pick(category="long_term", asset_class="EQUITY"), EQUITY, 0.005)
    assert longt >= swing
    assert longt <= 0.05 * EQUITY + 1e-6


def test_confidence_scales_linearly_in_safe_range():
    # long_term so the swing cap doesn't clip both into the same notional.
    full = compute_position_size(
        _pick(category="long_term", confidence=1.0), EQUITY, 0.05)
    half = compute_position_size(
        _pick(category="long_term", confidence=0.0), EQUITY, 0.05)
    assert math.isclose(half, 0.5 * full, rel_tol=1e-9)


def test_per_class_risk_cap_clips_very_low_vol():
    crypto = compute_position_size(
        _pick(asset_class="CRYPTO", category="long_term"),
        EQUITY,
        daily_vol_estimate=1e-6,
    )
    assert crypto == pytest.approx(2_000.0, abs=1.0)


def test_zero_equity_returns_zero():
    assert compute_position_size(_pick(), 0.0, 0.02) == 0.0


def test_duplicate_symbol_rejected():
    ok, reason = validate_concentration(
        _pick(symbol="AAPL"),
        [{"symbol": "AAPL", "sector": "tech", "notional_pct": 0.01,
          "category": "swing"}],
    )
    assert not ok
    assert "duplicate_symbol" in reason


def test_sector_cap_swing_blocks_at_20pct():
    positions = [
        {"symbol": f"T{i}", "sector": "tech", "notional_pct": 0.01,
         "category": "swing"}
        for i in range(20)
    ]
    ok, reason = validate_concentration(
        _pick(symbol="NVDA", sector="tech", category="swing",
              notional_pct=0.01),
        positions,
    )
    assert not ok
    assert "sector_cap" in reason


def test_sector_cap_long_term_independent_of_swing():
    positions = [
        {"symbol": f"S{i}", "sector": "tech", "notional_pct": 0.01,
         "category": "swing"}
        for i in range(15)
    ]
    ok, _ = validate_concentration(
        _pick(symbol="MSFT", sector="tech", category="long_term",
              notional_pct=0.05),
        positions,
    )
    assert ok


def test_validate_no_sector_passes():
    ok, reason = validate_concentration(
        _pick(symbol="XYZ", sector=None), [])
    assert ok
    assert reason == "ok"


def test_kill_switch_triggers_at_minus_3pct():
    fired, _ = daily_loss_kill_switch(100_000, 96_999)
    assert fired


def test_kill_switch_quiet_at_minus_2pct():
    fired, _ = daily_loss_kill_switch(100_000, 98_000)
    assert not fired
