"""Wire-up tests for transaction_cost_model -> dashboard_generator._normalize_pick.

Validates the env-flag-gated net-of-cost overlay added in PR-A.
Per CLAUDE.md: default-OFF, opt-in via HF_NET_PF_ENABLED=1, must not change
existing pick fields when flag is OFF.

The overlay was added per the empirical finding from PR #626's backtest:
"transaction-cost overlay flips every class except CRYPTO from gross-positive
to net-negative at literature-prior slippage."
"""
from __future__ import annotations

import importlib
import os

import pytest


@pytest.fixture(autouse=True)
def _restore_env(monkeypatch):
    """Always restore HF_NET_PF_ENABLED to its un-set state between tests."""
    monkeypatch.delenv("HF_NET_PF_ENABLED", raising=False)
    yield


def _reload_dg():
    import audit_trail.dashboard_generator as dg
    importlib.reload(dg)
    return dg


def _pick(**overrides):
    """Build a pick that flows cleanly through _normalize_pick."""
    base = {
        "symbol": "BTC-USD",
        "asset_class": "CRYPTO",
        "direction": "LONG",
        "entry_price": 50000.0,
        "take_profit": 51000.0,
        "stop_loss": 49000.0,
        "pnl_pct": 1.5,
        "score": 60,
        "confidence": 0.75,
        "trust_score": 4,
        "timestamp": "2026-05-02T00:00:00Z",
    }
    base.update(overrides)
    return base


# ─────────────────────────────────────────────────────────────────
# Default-OFF safety: no new fields added unless flag is set
# ─────────────────────────────────────────────────────────────────

def test_flag_off_does_not_add_net_of_cost_field():
    """Without HF_NET_PF_ENABLED, the overlay must not run."""
    dg = _reload_dg()
    out = dg._normalize_pick(_pick(), "test_source")
    assert "net_of_cost_pnl_pct" not in out, \
        "Flag-OFF must not add net_of_cost_pnl_pct (preserves existing schema)"


def test_flag_explicit_zero_does_not_add_net_of_cost(monkeypatch):
    """HF_NET_PF_ENABLED=0 is explicitly OFF, same as unset."""
    monkeypatch.setenv("HF_NET_PF_ENABLED", "0")
    dg = _reload_dg()
    out = dg._normalize_pick(_pick(), "test_source")
    assert "net_of_cost_pnl_pct" not in out


def test_flag_garbage_value_treated_as_off(monkeypatch):
    """Anything other than literal "1" should be treated as OFF (defensive)."""
    monkeypatch.setenv("HF_NET_PF_ENABLED", "true")
    dg = _reload_dg()
    out = dg._normalize_pick(_pick(), "test_source")
    assert "net_of_cost_pnl_pct" not in out, \
        "Only literal '1' enables the flag; 'true' must be treated as OFF"


# ─────────────────────────────────────────────────────────────────
# Flag-ON behavior: overlay runs, original pnl_pct preserved
# ─────────────────────────────────────────────────────────────────

def test_flag_on_adds_net_of_cost_pnl_pct(monkeypatch):
    monkeypatch.setenv("HF_NET_PF_ENABLED", "1")
    dg = _reload_dg()
    out = dg._normalize_pick(_pick(pnl_pct=1.5), "test_source")
    assert "net_of_cost_pnl_pct" in out, \
        "Flag-ON must add net_of_cost_pnl_pct"
    # CRYPTO_SPOT total cost = 0.20 + 0.10 + 0.06 = 0.36% RT
    # 1.5 - 0.36 = 1.14
    assert abs(out["net_of_cost_pnl_pct"] - 1.14) < 0.01, \
        f"Expected ~1.14 net for 1.5 gross CRYPTO; got {out['net_of_cost_pnl_pct']}"


def test_flag_on_preserves_original_pnl_pct(monkeypatch):
    """Critical: gross pnl_pct must NOT be overwritten (downstream consumers depend on it)."""
    monkeypatch.setenv("HF_NET_PF_ENABLED", "1")
    dg = _reload_dg()
    out = dg._normalize_pick(_pick(pnl_pct=1.5), "test_source")
    assert out.get("pnl_pct") == 1.5, \
        f"Original pnl_pct must be preserved; got {out.get('pnl_pct')}"


def test_flag_on_meme_flips_thin_alpha_negative(monkeypatch):
    """Empirical finding from PR #626 backtest: thin meme alpha flips negative
    after costs. Overlay must reflect this on a normalized pick.
    """
    monkeypatch.setenv("HF_NET_PF_ENABLED", "1")
    dg = _reload_dg()
    out = dg._normalize_pick(
        _pick(symbol="DOGEUSDT", pnl_pct=0.40, entry_price=0.10),
        "test_source",
    )
    assert out.get("net_of_cost_pnl_pct", 0) < 0, \
        f"Thin meme alpha 0.40% should flip net-negative; got {out.get('net_of_cost_pnl_pct')}"


def test_flag_on_negative_pick_more_negative_after_costs(monkeypatch):
    """Losing picks get MORE negative after costs (we pay both ways)."""
    monkeypatch.setenv("HF_NET_PF_ENABLED", "1")
    dg = _reload_dg()
    out = dg._normalize_pick(_pick(pnl_pct=-0.50), "test_source")
    net = out.get("net_of_cost_pnl_pct")
    assert net is not None
    assert net < -0.50, f"Net loss must exceed gross loss; got net={net} gross=-0.50"


# ─────────────────────────────────────────────────────────────────
# Defensive: overlay error must not break pick normalization
# ─────────────────────────────────────────────────────────────────

def test_overlay_error_swallowed_does_not_break_pick(monkeypatch):
    """If apply_costs_to_pick raises, _normalize_pick must still return a valid pick.
    Demonstrates the try/except guard around the import + call.
    """
    monkeypatch.setenv("HF_NET_PF_ENABLED", "1")
    dg = _reload_dg()

    # Patch apply_costs_to_pick on the imported module to raise
    import audit_trail.transaction_cost_model as tcm
    original = tcm.apply_costs_to_pick
    try:
        def boom(pick):
            raise RuntimeError("simulated overlay failure")
        tcm.apply_costs_to_pick = boom
        out = dg._normalize_pick(_pick(), "test_source")
        # Must still return a valid pick (pnl_pct preserved, no net field)
        assert out.get("pnl_pct") == 1.5
        assert "net_of_cost_pnl_pct" not in out
    finally:
        tcm.apply_costs_to_pick = original


def test_malformed_pick_short_circuits_before_overlay():
    """Non-dict raw input returns the early-return skip dict; overlay never runs."""
    dg = _reload_dg()
    out = dg._normalize_pick("not a dict", "test_source")
    assert out.get("skip") is True
