"""Tests for alpha_engine.risk.vol_target — vol-targeted position sizing sidecar.

Per 5-stream consensus 2026-04-29 + CLAUDE.md Wire-Up Rule:
- Default-off (CRYPTO_VOL_TARGET_ENABLED unset or "0")
- CRYPTO-only scope
- Scale clamped [0.25, 1.0] (no leverage)
- Default vol target 30.0% annualized, env-overridable
"""
from __future__ import annotations

import os

import pytest

from alpha_engine.risk import vol_target as vt


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    """Ensure each test starts with vol-target env flags unset."""
    monkeypatch.delenv("CRYPTO_VOL_TARGET_ENABLED", raising=False)
    monkeypatch.delenv("CRYPTO_VOL_TARGET_PCT", raising=False)
    yield


# ---------------------------------------------------------------------------
# Flag default
# ---------------------------------------------------------------------------

def test_default_flag_off():
    """By default, the vol-target sidecar must be DISABLED (safety)."""
    assert vt.crypto_vol_target_enabled() is False


def test_flag_on_when_env_set(monkeypatch):
    monkeypatch.setenv("CRYPTO_VOL_TARGET_ENABLED", "1")
    assert vt.crypto_vol_target_enabled() is True


def test_flag_off_when_env_zero(monkeypatch):
    monkeypatch.setenv("CRYPTO_VOL_TARGET_ENABLED", "0")
    assert vt.crypto_vol_target_enabled() is False


def test_flag_off_when_env_truthy_but_not_one(monkeypatch):
    """Strict '1' check — 'true', 'yes', etc. should NOT activate (avoid ambiguity)."""
    monkeypatch.setenv("CRYPTO_VOL_TARGET_ENABLED", "true")
    assert vt.crypto_vol_target_enabled() is False


# ---------------------------------------------------------------------------
# compute_size_scale edge cases
# ---------------------------------------------------------------------------

def test_compute_size_scale_none_returns_one():
    assert vt.compute_size_scale(None) == 1.0


def test_compute_size_scale_zero_returns_one():
    assert vt.compute_size_scale(0) == 1.0


def test_compute_size_scale_negative_returns_one():
    assert vt.compute_size_scale(-5.0) == 1.0


def test_compute_size_scale_at_target_equals_one():
    """vol == target => scale 1.0 (no adjustment)."""
    assert vt.compute_size_scale(vt.DEFAULT_VOL_TARGET_PCT) == pytest.approx(1.0)


def test_compute_size_scale_double_target_halves():
    """vol == 2x target => raw scale 0.5, within clamp [0.25, 1.0]."""
    rv = vt.DEFAULT_VOL_TARGET_PCT * 2  # 60%
    assert vt.compute_size_scale(rv) == pytest.approx(0.5)


def test_compute_size_scale_very_high_vol_clamped_to_min():
    """vol >> target => clamped to MIN_SCALE (0.25)."""
    rv = vt.DEFAULT_VOL_TARGET_PCT * 100  # absurd vol
    assert vt.compute_size_scale(rv) == 0.25


def test_compute_size_scale_very_low_vol_clamped_to_max():
    """vol << target => raw scale > 1.0 but clamped to MAX_SCALE (1.0)."""
    rv = vt.DEFAULT_VOL_TARGET_PCT / 10  # 3%
    assert vt.compute_size_scale(rv) == 1.0


def test_compute_size_scale_half_target_clamped_to_max():
    """vol == 0.5x target => raw scale 2.0 but clamped to 1.0 (no leverage)."""
    rv = vt.DEFAULT_VOL_TARGET_PCT * 0.5
    assert vt.compute_size_scale(rv) == 1.0


# ---------------------------------------------------------------------------
# Env var overrides for vol target
# ---------------------------------------------------------------------------

def test_env_var_vol_target_override(monkeypatch):
    monkeypatch.setenv("CRYPTO_VOL_TARGET_PCT", "15.0")
    assert vt.get_vol_target_pct() == 15.0
    # At 15% realized, scale should be exactly 1.0
    assert vt.compute_size_scale(15.0) == pytest.approx(1.0)
    # At 30% realized, scale should be 15/30 = 0.5
    assert vt.compute_size_scale(30.0) == pytest.approx(0.5)


def test_env_var_bad_value_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("CRYPTO_VOL_TARGET_PCT", "not-a-number")
    assert vt.get_vol_target_pct() == vt.DEFAULT_VOL_TARGET_PCT


def test_env_var_empty_string_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("CRYPTO_VOL_TARGET_PCT", "")
    assert vt.get_vol_target_pct() == vt.DEFAULT_VOL_TARGET_PCT


# ---------------------------------------------------------------------------
# apply_to_pick behavior
# ---------------------------------------------------------------------------

def test_apply_to_pick_noop_when_flag_off():
    """Flag default-off => apply_to_pick must return the pick unchanged."""
    pick = {"asset_class": "CRYPTO", "position_size_pct": 2.0, "realized_vol_pct": 60.0}
    result = vt.apply_to_pick(pick)
    assert result["position_size_pct"] == 2.0
    assert "_vol_target_scale" not in result


def test_apply_to_pick_noop_when_not_crypto_equity(monkeypatch):
    monkeypatch.setenv("CRYPTO_VOL_TARGET_ENABLED", "1")
    pick = {"asset_class": "EQUITY", "position_size_pct": 2.0, "realized_vol_pct": 60.0}
    result = vt.apply_to_pick(pick)
    assert result["position_size_pct"] == 2.0
    assert "_vol_target_scale" not in result


def test_apply_to_pick_noop_when_not_crypto_forex(monkeypatch):
    monkeypatch.setenv("CRYPTO_VOL_TARGET_ENABLED", "1")
    pick = {"asset_class": "FOREX", "position_size_pct": 2.0, "realized_vol_pct": 60.0}
    result = vt.apply_to_pick(pick)
    assert result["position_size_pct"] == 2.0
    assert "_vol_target_scale" not in result


def test_apply_to_pick_scales_position_size_when_crypto_and_enabled(monkeypatch):
    monkeypatch.setenv("CRYPTO_VOL_TARGET_ENABLED", "1")
    pick = {"asset_class": "CRYPTO", "position_size_pct": 2.0, "realized_vol_pct": 60.0}
    result = vt.apply_to_pick(pick)
    # 60% realized vs 30% target => scale 0.5 => 2.0 * 0.5 = 1.0
    assert result["position_size_pct"] == pytest.approx(1.0)
    assert result["_vol_target_scale"] == pytest.approx(0.5)


def test_apply_to_pick_writes_vol_target_scale_field(monkeypatch):
    monkeypatch.setenv("CRYPTO_VOL_TARGET_ENABLED", "1")
    pick = {"asset_class": "CRYPTO", "position_size_pct": 1.5, "realized_vol_pct": 30.0}
    result = vt.apply_to_pick(pick)
    assert "_vol_target_scale" in result
    assert result["_vol_target_scale"] == pytest.approx(1.0)


def test_apply_to_pick_handles_missing_realized_vol(monkeypatch):
    """When realized_vol_pct is missing, scale=1.0 (preserves behavior, no-op math)."""
    monkeypatch.setenv("CRYPTO_VOL_TARGET_ENABLED", "1")
    pick = {"asset_class": "CRYPTO", "position_size_pct": 2.0}
    result = vt.apply_to_pick(pick)
    assert result["_vol_target_scale"] == 1.0
    assert result["position_size_pct"] == pytest.approx(2.0)


def test_apply_to_pick_uses_atr_pct_annualized_fallback(monkeypatch):
    monkeypatch.setenv("CRYPTO_VOL_TARGET_ENABLED", "1")
    pick = {"asset_class": "CRYPTO", "position_size_pct": 2.0, "atr_pct_annualized": 60.0}
    result = vt.apply_to_pick(pick)
    assert result["_vol_target_scale"] == pytest.approx(0.5)
    assert result["position_size_pct"] == pytest.approx(1.0)


def test_apply_to_pick_override_param_takes_precedence(monkeypatch):
    """Explicit realized_vol_pct argument wins over pick fields."""
    monkeypatch.setenv("CRYPTO_VOL_TARGET_ENABLED", "1")
    pick = {"asset_class": "CRYPTO", "position_size_pct": 2.0, "realized_vol_pct": 30.0}
    result = vt.apply_to_pick(pick, realized_vol_pct=60.0)
    assert result["_vol_target_scale"] == pytest.approx(0.5)
    assert result["position_size_pct"] == pytest.approx(1.0)


def test_apply_to_pick_lowercase_asset_class_handled(monkeypatch):
    """`asset_class='crypto'` (lowercase) must still be recognized."""
    monkeypatch.setenv("CRYPTO_VOL_TARGET_ENABLED", "1")
    pick = {"asset_class": "crypto", "position_size_pct": 2.0, "realized_vol_pct": 60.0}
    result = vt.apply_to_pick(pick)
    assert result["_vol_target_scale"] == pytest.approx(0.5)


def test_apply_to_pick_no_position_size_field_no_crash(monkeypatch):
    """Pick without position_size_pct should still get _vol_target_scale, no KeyError."""
    monkeypatch.setenv("CRYPTO_VOL_TARGET_ENABLED", "1")
    pick = {"asset_class": "CRYPTO", "realized_vol_pct": 60.0}
    result = vt.apply_to_pick(pick)
    assert result["_vol_target_scale"] == pytest.approx(0.5)
    assert "position_size_pct" not in result


def test_apply_to_pick_extreme_high_vol_uses_min_scale(monkeypatch):
    """Extreme vol => scale clamped at 0.25, position reduced 4x."""
    monkeypatch.setenv("CRYPTO_VOL_TARGET_ENABLED", "1")
    pick = {"asset_class": "CRYPTO", "position_size_pct": 4.0, "realized_vol_pct": 1000.0}
    result = vt.apply_to_pick(pick)
    assert result["_vol_target_scale"] == 0.25
    assert result["position_size_pct"] == pytest.approx(1.0)
