"""Tests for PortfolioCircuitBreaker auto-flatten hook.

2026-11-16 audit: `_flatten_all_positions` was a log-only stub. It now invokes
an injectable `BreakerConfig.flatten_callback`; without one it must not claim
to have closed positions.
"""
from datetime import datetime, timezone

import portfolio_circuit_breaker as pcb


def test_trigger_invokes_flatten_callback():
    calls = []

    def _flatten(breaker):
        calls.append(breaker)
        return 3

    cfg = pcb.BreakerConfig(auto_flatten_on_trigger=True, flatten_callback=_flatten)
    b = pcb.PortfolioCircuitBreaker(config=cfg)
    b._trigger_breaker("unit_test", 12.0, datetime.now(timezone.utc))

    assert len(calls) == 1
    assert calls[0] is b


def test_no_callback_returns_zero_without_error():
    cfg = pcb.BreakerConfig(auto_flatten_on_trigger=True)
    b = pcb.PortfolioCircuitBreaker(config=cfg)
    assert b._flatten_all_positions() == 0


def test_callback_failure_is_contained():
    def _boom(breaker):
        raise RuntimeError("position manager down")

    cfg = pcb.BreakerConfig(auto_flatten_on_trigger=True, flatten_callback=_boom)
    b = pcb.PortfolioCircuitBreaker(config=cfg)
    assert b._flatten_all_positions() == 0

    # Triggering must not propagate the callback exception.
    b._trigger_breaker("unit_test", 12.0, datetime.now(timezone.utc))


def test_auto_flatten_disabled_skips_callback():
    calls = []
    cfg = pcb.BreakerConfig(
        auto_flatten_on_trigger=False,
        flatten_callback=lambda breaker: calls.append(breaker) or 1,
    )
    b = pcb.PortfolioCircuitBreaker(config=cfg)
    b._trigger_breaker("unit_test", 12.0, datetime.now(timezone.utc))
    assert calls == []
