"""Tests for quan_engine_inverse adapter wiring in antigravity_strategies.

SKIPPED: The quan_engine_inverse feature (apply_quan_engine_inverse,
_QUAN_INVERSE_CONF_BAND, etc.) was removed from antigravity_strategies
during a refactoring. These tests are preserved for future re-implementation
but cannot run until the feature is restored.
"""
from __future__ import annotations

import pytest

pytest.skip(
    "quan_engine_inverse feature removed from antigravity_strategies",
    allow_module_level=True,
)

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "alpha_engine"))

from alpha_engine.antigravity_strategies import (
    apply_quan_engine_inverse,
    _QUAN_INVERSE_CONF_BAND,
    _QUAN_INVERSE_EXCLUDE,
    _QUAN_INVERSE_SOURCE_STRATEGIES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_signal(
    strategy="quan_engine_scalp",
    symbol="ETHUSDT",
    direction="BUY",
    confidence=0.65,
    entry_price=3000.0,
    take_profit=3100.0,
    stop_loss=2950.0,
) -> dict:
    return {
        "strategy": strategy,
        "symbol": symbol,
        "direction": direction,
        "signal": direction,
        "confidence": confidence,
        "entry_price": entry_price,
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "category": "crypto",
        "source": "quan_engine",
        "extra": {"reason": "test signal"},
    }


# ---------------------------------------------------------------------------
# Config checks
# ---------------------------------------------------------------------------

class TestConfig:
    def test_confidence_band_matches_meta(self):
        assert _QUAN_INVERSE_CONF_BAND == (0.60, 0.69)

    def test_excluded_symbols_match_meta(self):
        assert "TAOUSDT" in _QUAN_INVERSE_EXCLUDE
        assert "HYPEUSDT" in _QUAN_INVERSE_EXCLUDE
        assert "TRXUSDT" in _QUAN_INVERSE_EXCLUDE

    def test_source_strategies_cover_family(self):
        assert "quan_engine" in _QUAN_INVERSE_SOURCE_STRATEGIES
        assert "quan_engine_scalp" in _QUAN_INVERSE_SOURCE_STRATEGIES
        assert "quan_engine_swing" in _QUAN_INVERSE_SOURCE_STRATEGIES
        assert "quan_engine_position" in _QUAN_INVERSE_SOURCE_STRATEGIES


# ---------------------------------------------------------------------------
# apply_quan_engine_inverse
# ---------------------------------------------------------------------------

class TestApplyQuanEngineInverse:
    def test_inverts_qualifying_signal(self):
        signals = [_make_signal(strategy="quan_engine_scalp", confidence=0.65, direction="BUY")]
        inverted = apply_quan_engine_inverse(signals)
        assert len(inverted) == 1
        assert inverted[0]["direction"] == "SELL"
        assert inverted[0]["strategy"] == "quan_engine_scalp_inverse"

    def test_inverts_sell_to_buy(self):
        signals = [_make_signal(strategy="quan_engine", confidence=0.62, direction="SELL")]
        inverted = apply_quan_engine_inverse(signals)
        assert len(inverted) == 1
        assert inverted[0]["direction"] == "BUY"

    def test_skips_confidence_outside_band(self):
        signals = [_make_signal(confidence=0.55)]  # below 0.60
        inverted = apply_quan_engine_inverse(signals)
        assert len(inverted) == 0

    def test_skips_confidence_above_band(self):
        signals = [_make_signal(confidence=0.75)]  # above 0.69
        inverted = apply_quan_engine_inverse(signals)
        assert len(inverted) == 0

    def test_skips_excluded_symbols(self):
        signals = [_make_signal(symbol="TAOUSDT", confidence=0.65)]
        inverted = apply_quan_engine_inverse(signals)
        assert len(inverted) == 0

    def test_skips_non_quan_strategies(self):
        signals = [_make_signal(strategy="ag_vwap_rsi_institutional", confidence=0.65)]
        inverted = apply_quan_engine_inverse(signals)
        assert len(inverted) == 0

    def test_inverts_all_quan_family_strategies(self):
        signals = [
            _make_signal(strategy="quan_engine", confidence=0.65),
            _make_signal(strategy="quan_engine_scalp", confidence=0.62),
            _make_signal(strategy="quan_engine_swing", confidence=0.68),
            _make_signal(strategy="quan_engine_position", confidence=0.60),
        ]
        inverted = apply_quan_engine_inverse(signals)
        assert len(inverted) == 4
        strat_names = {s["strategy"] for s in inverted}
        assert strat_names == {
            "quan_engine_inverse",
            "quan_engine_scalp_inverse",
            "quan_engine_swing_inverse",
            "quan_engine_position_inverse",
        }

    def test_tp_sl_swapped(self):
        """TP and SL should be mirrored around entry price."""
        signals = [_make_signal(
            entry_price=100.0, take_profit=110.0, stop_loss=95.0,
            direction="BUY", confidence=0.65,
        )]
        inverted = apply_quan_engine_inverse(signals)
        assert len(inverted) == 1
        inv = inverted[0]
        # Original BUY: TP=110 (above), SL=95 (below)
        # Inverted SELL: TP=90 (below by 10), SL=105 (above by 5)
        assert inv["take_profit"] == pytest.approx(90.0)
        assert inv["stop_loss"] == pytest.approx(105.0)

    def test_originals_not_mutated(self):
        original = _make_signal(confidence=0.65, direction="BUY")
        signals = [original]
        apply_quan_engine_inverse(signals)
        assert original["direction"] == "BUY"
        assert original["strategy"] == "quan_engine_scalp"

    def test_audit_trail_in_extra(self):
        signals = [_make_signal(confidence=0.65, direction="BUY")]
        inverted = apply_quan_engine_inverse(signals)
        assert len(inverted) == 1
        assert "inverted_from" in inverted[0]["extra"]
        assert inverted[0]["extra"]["inverted_from"]["original_direction"] == "BUY"

    def test_empty_signals_returns_empty(self):
        assert apply_quan_engine_inverse([]) == []

    def test_mixed_signals_only_inverts_qualifying(self):
        signals = [
            _make_signal(strategy="quan_engine_scalp", confidence=0.65),  # qualifies
            _make_signal(strategy="ag_vwap_rsi_institutional", confidence=0.65),  # wrong strat
            _make_signal(strategy="quan_engine_scalp", confidence=0.55),  # wrong conf
            _make_signal(strategy="quan_engine_scalp", confidence=0.65, symbol="TAOUSDT"),  # excluded
            _make_signal(strategy="quan_engine_swing", confidence=0.69),  # qualifies
        ]
        inverted = apply_quan_engine_inverse(signals)
        assert len(inverted) == 2
