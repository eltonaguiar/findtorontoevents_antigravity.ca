"""Tests for vol_adjusted_size min_scale parameter (PR fix for clamp).

Per reports/audit_vol_targeting_clamp_2026_04_28.md, the previous hard-coded
min_scale of 0.25 prevented effective MDD reduction on high-vol crypto.
This test pins the new env-controlled behavior with a safer default of 0.05.
"""
from __future__ import annotations

import math
import os

from alpha_engine.kelly_position_sizer import vol_adjusted_size


def test_default_min_scale_allows_aggressive_downscale_on_high_vol():
    """Per audit doc: 162% realized vol crypto needs ~0.092x for 15% target.
    With old 0.25 clamp, scale capped at 0.25. With new 0.05 default, allows 0.092."""
    # ATR ~8.5% daily → realized vol = 8.5 * sqrt(365) = ~162%
    atr_high_vol = 0.085
    base = 1000.0
    sized = vol_adjusted_size(base, atr_high_vol, target_vol=0.15)
    realized_vol = atr_high_vol * math.sqrt(365)
    expected_scale = 0.15 / realized_vol  # ~0.092
    # Old behavior would clamp at 250.0 (0.25 * base). New default lets ~92.
    assert sized < 250.0, "Old 0.25 clamp would force >= 250; got {}".format(sized)
    assert sized >= base * 0.05, "Below safety floor 0.05 of base"
    # Tolerance because of clamp interaction
    assert abs(sized - base * expected_scale) < 5.0


def test_explicit_min_scale_overrides_default():
    """Caller can override min_scale parameter directly."""
    sized = vol_adjusted_size(1000.0, 0.085, target_vol=0.15, min_scale=0.30)
    assert sized == 300.0, "min_scale=0.30 forces clamp at 300"


def test_env_override_restores_old_025_behavior():
    """Rollback path: KELLY_VOL_MIN_SCALE=0.25 restores pre-fix clamp."""
    os.environ["KELLY_VOL_MIN_SCALE"] = "0.25"
    try:
        sized = vol_adjusted_size(1000.0, 0.085, target_vol=0.15)
        assert sized == 250.0, "env=0.25 should restore old 0.25x floor"
    finally:
        del os.environ["KELLY_VOL_MIN_SCALE"]


def test_safety_bounds_on_min_scale():
    """min_scale itself clamped to [0.01, 1.0] to prevent degenerate cases.

    Floor only fires when vol_scale < min_scale_safety_clamp.
    """
    # extreme high vol → vol_scale << 0.01 → safety floor 0.01 fires
    # realized = 1.0 * sqrt(365) ≈ 19.1, scale = 0.05/19.1 ≈ 0.0026 < 0.01
    sized_zero = vol_adjusted_size(1000.0, 1.0, target_vol=0.05, min_scale=0.0)
    assert sized_zero == 10.0, f"min_scale=0 → safety bump 0.01 floor → 10.0; got {sized_zero}"
    # min_scale=2.0 → safety cap at 1.0; vol_scale=0.092 < 1.0 → clamp at 1.0 → 1000
    sized_huge = vol_adjusted_size(1000.0, 0.085, target_vol=0.15, min_scale=2.0)
    assert sized_huge == 1000.0, f"min_scale=2.0 → safety cap 1.0 → 1000.0; got {sized_huge}"


def test_low_vol_asset_uses_target_directly():
    """Low-vol asset (10% realized) gets full target_vol/realized_vol scale."""
    # ATR = 0.005, realized_vol = 0.005 * 19.1 = 0.095 (~10%)
    # vol_scale = 0.15 / 0.095 = 1.58
    sized = vol_adjusted_size(1000.0, 0.005, target_vol=0.15)
    realized_vol = 0.005 * math.sqrt(365)
    expected = 1000.0 * (0.15 / realized_vol)
    assert abs(sized - expected) < 1.0


def test_zero_vol_returns_base():
    """Edge case: zero realized vol returns base (no scaling)."""
    sized = vol_adjusted_size(1000.0, 0.0, target_vol=0.15)
    assert sized == 1000.0


def test_invalid_env_falls_back_to_default():
    """Invalid env value (non-numeric) falls back to 0.05 default."""
    os.environ["KELLY_VOL_MIN_SCALE"] = "garbage"
    try:
        sized = vol_adjusted_size(1000.0, 0.085, target_vol=0.15)
        # 0.05 default → 50.0 floor
        assert sized < 100.0, "Should use 0.05 default, not crash"
        assert sized >= 50.0
    finally:
        del os.environ["KELLY_VOL_MIN_SCALE"]
