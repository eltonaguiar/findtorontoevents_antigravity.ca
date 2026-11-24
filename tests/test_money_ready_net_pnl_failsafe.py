"""Regression tests for money_ready_verdict._net_pnl fail-safe behavior.

2026-11-16 audit: the slippage deduction must never silently fall back to a
gross-only verdict when the charter_slippage model is unavailable.
"""
import pytest

from alpha_engine import money_ready_verdict as mrv


def test_net_pnl_deducts_charter_round_trip():
    # CRYPTO one-way 4bp -> 8bp round-trip = 0.0008
    net = mrv._net_pnl({"pnl_pct": 0.03, "asset_class": "CRYPTO"})
    assert net == pytest.approx(0.03 - 0.0008)


def test_net_pnl_unknown_class_uses_conservative_bps():
    # unknown class -> 8bp one-way -> 16bp round-trip = 0.0016
    net = mrv._net_pnl({"pnl_pct": 0.03, "asset_class": "ALIEN"})
    assert net == pytest.approx(0.03 - 0.0016)


def test_net_pnl_fails_safe_when_model_unavailable(monkeypatch):
    import alpha_engine.charter_slippage as cs

    def _boom(*a, **k):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(cs, "deduct_slippage", _boom)
    net = mrv._net_pnl({"pnl_pct": 0.03, "asset_class": "CRYPTO"})
    # Widest charter round-trip (COMMODITY 12bp) applied, not gross.
    assert net == pytest.approx(0.03 - 0.0012)
    assert net < 0.03
