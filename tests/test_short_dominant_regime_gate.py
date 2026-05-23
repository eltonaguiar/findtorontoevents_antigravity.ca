"""
Regression test for the BULL-regime gate added to
alpha_engine/short_dominant_engine.py 2026-05-09.

Reference: reports/portfolio_lessons_2026-05-08.md — engine emitted 485
SHORTs in 14d (100% short bias) while ENA/JUP/RENDER/ADA/TON pumped.
TONUSDT pumped 40% while we held 7 open SHORTs.
"""
from __future__ import annotations

import os

import pytest

from alpha_engine.short_dominant_engine import _filter_picks_by_regime


def _short(symbol="ENAUSDT", confidence=0.65):
    return {
        "symbol": symbol, "direction": "SHORT", "confidence": confidence,
        "entry_price": 0.125, "take_profit": 0.121, "stop_loss": 0.127,
    }


def _long(symbol="BTCUSDT", confidence=0.85):
    return {
        "symbol": symbol, "direction": "LONG", "confidence": confidence,
        "entry_price": 80000, "take_profit": 84000, "stop_loss": 78000,
    }


def test_strong_bull_drops_all_shorts():
    picks = [_short("ENAUSDT"), _short("JUPUSDT"), _long("BTCUSDT")]
    kept, suppressed = _filter_picks_by_regime(picks, "STRONG_BULL")
    assert suppressed == 2
    assert len(kept) == 1
    assert kept[0]["direction"] == "LONG"


def test_bull_keeps_high_conviction_shorts_only():
    picks = [
        _short("ENAUSDT", confidence=0.65),  # below threshold
        _short("JUPUSDT", confidence=0.90),  # above threshold — kept
        _short("RENDERUSDT", confidence=0.85),  # at threshold — kept
        _long("BTCUSDT", confidence=0.80),
    ]
    kept, suppressed = _filter_picks_by_regime(picks, "BULL")
    assert suppressed == 1  # only the 0.65-conf one
    kept_syms = {p["symbol"] for p in kept}
    assert "ENAUSDT" not in kept_syms
    assert "JUPUSDT" in kept_syms
    assert "RENDERUSDT" in kept_syms
    assert "BTCUSDT" in kept_syms


def test_choppy_passes_all_through():
    picks = [_short("ENAUSDT"), _short("JUPUSDT"), _long("BTCUSDT")]
    kept, suppressed = _filter_picks_by_regime(picks, "CHOPPY")
    assert suppressed == 0
    assert len(kept) == 3


def test_bear_passes_all_through():
    picks = [_short("ENAUSDT"), _short("JUPUSDT")]
    kept, suppressed = _filter_picks_by_regime(picks, "BEAR")
    assert suppressed == 0
    assert len(kept) == 2


def test_strong_bear_passes_all_through():
    picks = [_short("ENAUSDT"), _short("JUPUSDT")]
    kept, suppressed = _filter_picks_by_regime(picks, "STRONG_BEAR")
    assert suppressed == 0
    assert len(kept) == 2


def test_unknown_regime_fails_open():
    """When regime detector unavailable, gate must NOT block picks (legacy
    behavior preserved)."""
    picks = [_short("ENAUSDT"), _short("JUPUSDT"), _long("BTCUSDT")]
    kept, suppressed = _filter_picks_by_regime(picks, "UNKNOWN")
    assert suppressed == 0
    assert len(kept) == 3


def test_env_override_disables_gate(monkeypatch):
    """SHORT_DOMINANT_REGIME_GATE_DISABLE=1 disables the gate even in BULL."""
    monkeypatch.setenv("SHORT_DOMINANT_REGIME_GATE_DISABLE", "1")
    picks = [_short("ENAUSDT"), _short("JUPUSDT")]
    kept, suppressed = _filter_picks_by_regime(picks, "STRONG_BULL")
    assert suppressed == 0
    assert len(kept) == 2


def test_long_picks_never_suppressed_regardless_of_regime():
    picks = [_long("BTCUSDT", confidence=0.55)]  # low-conf LONG
    for regime in ("STRONG_BULL", "BULL", "CHOPPY", "BEAR", "STRONG_BEAR", "UNKNOWN"):
        kept, suppressed = _filter_picks_by_regime(picks, regime)
        assert suppressed == 0, f"LONG suppressed in {regime}"
        assert len(kept) == 1


def test_empty_pick_list_handled():
    kept, suppressed = _filter_picks_by_regime([], "STRONG_BULL")
    assert kept == []
    assert suppressed == 0
