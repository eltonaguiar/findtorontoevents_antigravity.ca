"""Smoke tests for the vol_target sidecar wire-up into smart_picks_engine.

Backlog item #1 from `reports/INTEGRATION_PLAN_OPEN_PRS_2026_04_30.md`
Stream #10 — Step 2 of PR #527 (vol_target sidecar).

These tests exercise the import + the apply_to_pick call directly. They
do NOT exercise the full smart_picks_engine.score_pick pipeline (which
requires extensive fixture setup); the contract verified here is that:

1. The import resolves at smart_picks_engine load time.
2. With the flag OFF, apply_to_pick is a no-op (no '_vol_target_scale').
3. With the flag ON + CRYPTO pick, apply_to_pick stamps
   '_vol_target_scale' AND scales position_size_pct.
4. With the flag ON + non-CRYPTO pick, apply_to_pick is still a no-op.
5. With the flag ON + CRYPTO pick + no realized_vol, scale is 1.0.

The downstream wire-up (score_pick result -> _vol_target_apply -> append)
is exercised in production via the audit-dashboard cron once the flag is
set; pinning the integration via a full pipeline test is out of scope
for this surgical wire-up PR.
"""
from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _clear_vol_target_env(monkeypatch):
    """Each test starts with the env flag cleared."""
    monkeypatch.delenv("CRYPTO_VOL_TARGET_ENABLED", raising=False)
    monkeypatch.delenv("CRYPTO_VOL_TARGET_PCT", raising=False)
    yield


def test_import_resolves_at_smart_picks_engine_load():
    """The import added in smart_picks_engine.py top-of-file must resolve."""
    # If the wire-up import fails, this will raise ImportError.
    import alpha_engine.smart_picks_engine as spe
    assert hasattr(spe, "_vol_target_apply"), \
        "Expected _vol_target_apply alias bound at module top"


def test_apply_to_pick_is_noop_when_flag_off():
    """Default-off: no scaling, no _vol_target_scale stamp."""
    from alpha_engine.smart_picks_engine import _vol_target_apply
    pick = {
        "asset_class": "CRYPTO",
        "symbol": "BTCUSDT",
        "position_size_pct": 5.0,
        "realized_vol_pct": 60.0,
    }
    out = _vol_target_apply(pick)
    assert out is pick
    assert "_vol_target_scale" not in out
    assert out["position_size_pct"] == 5.0


def test_apply_to_pick_scales_when_flag_on_and_crypto(monkeypatch):
    """Flag on + CRYPTO pick + high realized vol -> position scaled DOWN."""
    monkeypatch.setenv("CRYPTO_VOL_TARGET_ENABLED", "1")
    from alpha_engine.smart_picks_engine import _vol_target_apply
    pick = {
        "asset_class": "CRYPTO",
        "symbol": "BTCUSDT",
        "position_size_pct": 5.0,
        "realized_vol_pct": 60.0,  # 2x the 30% target -> scale = 0.5
    }
    out = _vol_target_apply(pick)
    assert "_vol_target_scale" in out
    assert out["_vol_target_scale"] == pytest.approx(0.5, rel=1e-3)
    assert out["position_size_pct"] == pytest.approx(2.5, rel=1e-3)


def test_apply_to_pick_noop_on_non_crypto_even_when_flag_on(monkeypatch):
    """Flag on but non-CRYPTO pick -> no-op (preserves single-class scope)."""
    monkeypatch.setenv("CRYPTO_VOL_TARGET_ENABLED", "1")
    from alpha_engine.smart_picks_engine import _vol_target_apply
    pick = {
        "asset_class": "EQUITY",
        "symbol": "AAPL",
        "position_size_pct": 5.0,
        "realized_vol_pct": 60.0,
    }
    out = _vol_target_apply(pick)
    assert "_vol_target_scale" not in out
    assert out["position_size_pct"] == 5.0


def test_apply_to_pick_returns_scale_1_when_no_realized_vol(monkeypatch):
    """Flag on + CRYPTO + missing realized vol -> scale = 1.0 (no scaling)."""
    monkeypatch.setenv("CRYPTO_VOL_TARGET_ENABLED", "1")
    from alpha_engine.smart_picks_engine import _vol_target_apply
    pick = {
        "asset_class": "CRYPTO",
        "symbol": "BTCUSDT",
        "position_size_pct": 5.0,
        # no realized_vol_pct, no atr_pct_annualized
    }
    out = _vol_target_apply(pick)
    assert "_vol_target_scale" in out
    assert out["_vol_target_scale"] == pytest.approx(1.0, rel=1e-3)
    assert out["position_size_pct"] == pytest.approx(5.0, rel=1e-3)


def test_apply_to_pick_clamp_max_at_1(monkeypatch):
    """Realized vol below target should NOT lever up — clamp at 1.0."""
    monkeypatch.setenv("CRYPTO_VOL_TARGET_ENABLED", "1")
    from alpha_engine.smart_picks_engine import _vol_target_apply
    pick = {
        "asset_class": "CRYPTO",
        "symbol": "BTCUSDT",
        "position_size_pct": 5.0,
        "realized_vol_pct": 10.0,  # below 30% target -> raw scale 3.0, clamp to 1.0
    }
    out = _vol_target_apply(pick)
    assert out["_vol_target_scale"] == pytest.approx(1.0, rel=1e-3)
    assert out["position_size_pct"] == pytest.approx(5.0, rel=1e-3)
