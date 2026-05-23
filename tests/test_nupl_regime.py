"""Tests for tools/research/nupl_regime.py — M-038 NUPL euphoria gate."""
import importlib
import os

import pytest


def _reload_module():
    """Reload nupl_regime so module-level constants pick up env changes."""
    import tools.research.nupl_regime as m
    importlib.reload(m)
    return m


def test_nupl_unavailable_passes(monkeypatch):
    """When NUPL_OVERRIDE not set and API unavailable, gate should pass (fail-open)."""
    monkeypatch.delenv("NUPL_OVERRIDE", raising=False)
    monkeypatch.delenv("NUPL_GATE_ENFORCE", raising=False)

    # Patch the Coin Metrics fetch to simulate API unavailability
    import tools.research.nupl_regime as m
    monkeypatch.setattr(m, "get_current_nupl", lambda: None)

    blocked, reason = m.is_crypto_long_blocked_by_nupl()
    assert not blocked
    assert "unavailable" in reason


def test_nupl_below_threshold_passes(monkeypatch):
    """NUPL below euphoria threshold should pass."""
    monkeypatch.setenv("NUPL_OVERRIDE", "0.65")
    monkeypatch.delenv("NUPL_GATE_ENFORCE", raising=False)

    import tools.research.nupl_regime as m
    blocked, reason = m.is_crypto_long_blocked_by_nupl()
    assert not blocked
    assert "nupl_ok" in reason


def test_nupl_above_threshold_enforced(monkeypatch):
    """NUPL above threshold with NUPL_GATE_ENFORCE=1 should block."""
    monkeypatch.setenv("NUPL_OVERRIDE", "0.80")
    monkeypatch.setenv("NUPL_GATE_ENFORCE", "1")

    import tools.research.nupl_regime as m
    blocked, reason = m.is_crypto_long_blocked_by_nupl()
    assert blocked
    assert "M-038" in reason
    assert "nupl_euphoria" in reason


def test_nupl_above_threshold_shadow_passes(monkeypatch):
    """Shadow mode (NUPL_GATE_ENFORCE=0): euphoric NUPL should NOT block."""
    monkeypatch.setenv("NUPL_OVERRIDE", "0.80")
    monkeypatch.setenv("NUPL_GATE_ENFORCE", "0")

    import tools.research.nupl_regime as m
    blocked, reason = m.is_crypto_long_blocked_by_nupl()
    assert not blocked
    # Reason should still mention the euphoria condition even in shadow mode
    assert "nupl_euphoria" in reason or "M-038" in reason or "nupl_ok" not in reason


def test_nupl_exactly_at_threshold_passes(monkeypatch):
    """NUPL exactly at threshold should NOT block (strictly greater than required)."""
    monkeypatch.setenv("NUPL_OVERRIDE", "0.75")
    monkeypatch.setenv("NUPL_GATE_ENFORCE", "1")

    import tools.research.nupl_regime as m
    blocked, reason = m.is_crypto_long_blocked_by_nupl()
    assert not blocked
    assert "nupl_ok" in reason


def test_nupl_gate_fails_open_on_exception(monkeypatch):
    """Any exception inside the gate must result in fail-open (not blocked)."""
    monkeypatch.delenv("NUPL_OVERRIDE", raising=False)
    monkeypatch.setenv("NUPL_GATE_ENFORCE", "1")

    import tools.research.nupl_regime as m

    def _boom():
        raise RuntimeError("simulated API crash")

    monkeypatch.setattr(m, "get_current_nupl", _boom)

    blocked, reason = m.is_crypto_long_blocked_by_nupl()
    assert not blocked
    assert "error" in reason or "pass" in reason


def test_exchange_spread_divergence_compute():
    """compute_exchange_spread_divergence returns correct ratio."""
    from coinglass_strategies.data_fetcher import compute_exchange_spread_divergence

    prices = {"binance": 100.0, "bybit": 101.0, "okx": 99.0}
    ratio = compute_exchange_spread_divergence(prices)
    # max=101, min=99, avg=100 → ratio = 2/100 = 0.02
    assert abs(ratio - 0.02) < 1e-9


def test_exchange_spread_divergence_single_exchange():
    """Single exchange returns 0.0 (no divergence possible)."""
    from coinglass_strategies.data_fetcher import compute_exchange_spread_divergence

    assert compute_exchange_spread_divergence({"binance": 50000.0}) == 0.0


def test_exchange_spread_divergence_empty():
    """Empty dict returns 0.0."""
    from coinglass_strategies.data_fetcher import compute_exchange_spread_divergence

    assert compute_exchange_spread_divergence({}) == 0.0


def test_is_exchange_divergence_high_stub():
    """Stub always returns False — gate is default OFF (shadow mode)."""
    from coinglass_strategies.data_fetcher import is_exchange_divergence_high

    assert is_exchange_divergence_high("BTCUSDT") is False
    assert is_exchange_divergence_high("ETHUSDT") is False
