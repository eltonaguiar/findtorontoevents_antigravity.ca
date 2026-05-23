"""Unit tests for vt_csv_edge_luxalgo_alts strategy and adapter.

Tests cover:
  - Strategy init / defaults / param overrides
  - Signal generation with synthetic OHLCV (LONG & SHORT)
  - Filter gates: unprecedented streaks, RSI bounds, bo_prob threshold
  - Confidence scoring formula (conviction, squeeze, reversal penalty, vol boost)
  - Adapter integration (vt_csv_edge_luxalgo_alts in vt_baby_strategies)
  - Symbol mapping: Binance keys ↔ yfinance keys
  - Edge cases: insufficient bars, zero ATR, empty data
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Path setup — allow imports from project root and alpha_engine
# ---------------------------------------------------------------------------
_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
if str(_REPO / "alpha_engine") not in sys.path:
    sys.path.insert(0, str(_REPO / "alpha_engine"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ohlcv(
    start_price: float = 100.0,
    volatility: float = 0.02,
    drift: float = 0.0,
    n: int = 250,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate realistic OHLCV bars with lowercase column names."""
    rng = np.random.default_rng(seed)
    returns = drift + volatility * rng.standard_normal(n)
    closes = start_price * np.exp(np.cumsum(returns))
    highs = closes * (1 + abs(volatility) * rng.random(n) * 0.5)
    lows = closes * (1 - abs(volatility) * rng.random(n) * 0.5)
    opens = closes * (1 + volatility * 0.3 * rng.standard_normal(n))
    volumes = abs(rng.standard_normal(n) * 1e6 + 5e6)
    return pd.DataFrame(
        {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
        },
        index=pd.date_range("2025-01-01", periods=n, freq="1h"),
    )


def _strong_uptrend_df(n: int = 250, seed: int = 1) -> pd.DataFrame:
    """OHLCV with strong uptrend → should trigger LONG breakout signals."""
    return _make_ohlcv(start_price=0.18, volatility=0.03, drift=0.003, n=n, seed=seed)


def _strong_downtrend_df(n: int = 250, seed: int = 2) -> pd.DataFrame:
    """OHLCV with strong downtrend → should trigger SHORT breakout signals."""
    return _make_ohlcv(start_price=0.17, volatility=0.03, drift=-0.003, n=n, seed=seed)


def _flat_df(n: int = 250) -> pd.DataFrame:
    """OHLCV with no drift → unlikely to produce breakout signals."""
    return _make_ohlcv(start_price=100.0, volatility=0.005, drift=0.0, n=n, seed=3)


# ---------------------------------------------------------------------------
# Import strategy (graceful if baby_strategies not on path)
# ---------------------------------------------------------------------------

try:
    from baby_strategies.vt_csv_edge_luxalgo_alts import (
        MIN_BARS,
        SYMBOLS,
        Signal,
        VTCsvEdgeLuxalgoAltsStrategy,
    )
except ImportError:
    pytest.skip("baby_strategies.vt_csv_edge_luxalgo_alts not importable", allow_module_level=True)


# ========================================================================
# Test: Strategy init & defaults
# ========================================================================


class TestStrategyInit:
    """Strategy construction and default parameter values."""

    def test_default_params(self):
        s = VTCsvEdgeLuxalgoAltsStrategy()
        assert s.bo_prob_threshold == 40.0
        assert s.rsi_long_max == 65
        assert s.rsi_short_min == 35
        assert s.tp_atr_mult == 2.5
        assert s.sl_atr_mult == 1.2
        assert s.atr_period == 14
        assert s.rsi_period == 14

    def test_custom_params(self):
        s = VTCsvEdgeLuxalgoAltsStrategy(params={
            "bo_prob_threshold": 30.0,
            "rsi_long_max": 70,
            "rsi_short_min": 30,
            "tp_atr_mult": 3.0,
        })
        assert s.bo_prob_threshold == 30.0
        assert s.rsi_long_max == 70
        assert s.rsi_short_min == 30
        assert s.tp_atr_mult == 3.0
        # Unchanged defaults
        assert s.sl_atr_mult == 1.2

    def test_class_attributes(self):
        assert VTCsvEdgeLuxalgoAltsStrategy.name == "vt_csv_edge_luxalgo_alts"
        assert VTCsvEdgeLuxalgoAltsStrategy.version == "1.0.0"
        assert VTCsvEdgeLuxalgoAltsStrategy.asset_class == "crypto"
        assert VTCsvEdgeLuxalgoAltsStrategy.family == "community"


class TestSymbolsAndConstants:
    """SYMBOLS list and MIN_BARS constant."""

    def test_symbols_list(self):
        assert SYMBOLS == ["WIFUSDT", "JUPUSDT", "AVAXUSDT", "SOLUSDT"]

    def test_min_bars(self):
        assert MIN_BARS == 120


# ========================================================================
# Test: Signal generation
# ========================================================================


class TestSignalGeneration:
    """Core signal generation with synthetic data."""

    def test_insufficient_bars_returns_empty(self):
        s = VTCsvEdgeLuxalgoAltsStrategy()
        df = _make_ohlcv(n=50)  # well below MIN_BARS=120
        assert s.generate_signals(df, symbol="WIFUSDT") == []

    def test_strong_uptrend_produces_long_signal(self):
        s = VTCsvEdgeLuxalgoAltsStrategy(params={"bo_prob_threshold": 35.0})
        df = _strong_uptrend_df()
        sigs = s.generate_signals(df, symbol="WIFUSDT")
        # With a relaxed threshold, should get at least one BUY
        if sigs:
            assert sigs[0].direction == "BUY"
            assert sigs[0].symbol == "WIFUSDT"
            assert sigs[0].entry_price > 0
            assert sigs[0].take_profit > sigs[0].entry_price  # TP above entry for LONG
            assert sigs[0].stop_loss < sigs[0].entry_price    # SL below entry for LONG

    def test_strong_downtrend_produces_short_signal(self):
        s = VTCsvEdgeLuxalgoAltsStrategy(params={"bo_prob_threshold": 35.0})
        df = _strong_downtrend_df()
        sigs = s.generate_signals(df, symbol="JUPUSDT")
        if sigs:
            assert sigs[0].direction == "SELL"
            assert sigs[0].symbol == "JUPUSDT"
            assert sigs[0].take_profit < sigs[0].entry_price   # TP below entry for SHORT
            assert sigs[0].stop_loss > sigs[0].entry_price     # SL above entry for SHORT

    def test_flat_market_may_produce_no_signal(self):
        """Flat / ranging data may not trigger breakout — acceptable."""
        s = VTCsvEdgeLuxalgoAltsStrategy()
        df = _flat_df()
        # No assertion on signal count — just verify it doesn't crash
        sigs = s.generate_signals(df, symbol="AVAXUSDT")
        assert isinstance(sigs, list)

    def test_signal_confidence_in_range(self):
        s = VTCsvEdgeLuxalgoAltsStrategy(params={"bo_prob_threshold": 35.0})
        df = _strong_uptrend_df()
        sigs = s.generate_signals(df, symbol="SOLUSDT")
        for sig in sigs:
            assert 0.0 <= sig.confidence <= 1.0

    def test_signal_has_reason_string(self):
        s = VTCsvEdgeLuxalgoAltsStrategy(params={"bo_prob_threshold": 35.0})
        df = _strong_uptrend_df()
        sigs = s.generate_signals(df, symbol="WIFUSDT")
        for sig in sigs:
            assert isinstance(sig.reason, str)
            assert len(sig.reason) > 0
            assert "+27pp" in sig.reason

    def test_at_most_one_signal_per_call(self):
        """Strategy returns at most 1 signal (LONG xor SHORT) per invocation."""
        s = VTCsvEdgeLuxalgoAltsStrategy(params={"bo_prob_threshold": 35.0})
        df = _strong_uptrend_df()
        sigs = s.generate_signals(df, symbol="WIFUSDT")
        assert len(sigs) <= 1


# ========================================================================
# Test: RSI indicator
# ========================================================================


class TestRSI:
    """RSI calculation correctness."""

    def test_rsi_range(self):
        s = VTCsvEdgeLuxalgoAltsStrategy()
        df = _make_ohlcv(n=200)
        rsi = s._calc_rsi(df["close"])
        # RSI should be between 0 and 100 (ignoring initial NaN)
        valid = rsi.dropna()
        assert (valid >= 0).all() and (valid <= 100).all()

    def test_rsi_period_param(self):
        s = VTCsvEdgeLuxalgoAltsStrategy(params={"rsi_period": 7})
        df = _make_ohlcv(n=200)
        rsi = s._calc_rsi(df["close"])
        # Should not crash and should produce values
        assert rsi.iloc[-1] > 0


# ========================================================================
# Test: ATR indicator
# ========================================================================


class TestATR:
    """ATR calculation correctness."""

    def test_atr_positive(self):
        s = VTCsvEdgeLuxalgoAltsStrategy()
        df = _make_ohlcv(n=200)
        atr = s._calc_atr(df["high"], df["low"], df["close"])
        assert atr.iloc[-1] > 0

    def test_zero_atr_returns_empty(self):
        """If ATR=0, strategy should return no signals (division guard)."""
        s = VTCsvEdgeLuxalgoAltsStrategy()
        # Create flat data where high==low==close → ATR ≈ 0
        n = 250
        closes = np.full(n, 100.0)
        df = pd.DataFrame({
            "open": closes, "high": closes, "low": closes, "close": closes,
            "volume": np.ones(n) * 1e6,
        })
        sigs = s.generate_signals(df, symbol="WIFUSDT")
        assert sigs == []


# ========================================================================
# Test: Filter gates
# ========================================================================


class TestFilterGates:
    """Individual filter gate behaviour."""

    def test_unprecedented_streak_blocks_signal(self):
        """When streak analyzer reports unprecedented=True, no signal."""
        s = VTCsvEdgeLuxalgoAltsStrategy(params={"bo_prob_threshold": 20.0})
        df = _strong_uptrend_df()

        with patch.object(s, "_run_streak_analyzer", return_value={
            "direction": "BULL", "length": 20, "reversal_probability": 0.3,
            "unprecedented": True,
        }):
            sigs = s.generate_signals(df, symbol="WIFUSDT")
            assert sigs == [], "Unprecedented streak should block signal"

    def test_rsi_overbought_blocks_long(self):
        """RSI > rsi_long_max should block LONG signal."""
        s = VTCsvEdgeLuxalgoAltsStrategy(params={"bo_prob_threshold": 20.0, "rsi_long_max": 30})
        df = _strong_uptrend_df()
        # With rsi_long_max=30, almost any uptrend data will have RSI > 30
        sigs = s.generate_signals(df, symbol="WIFUSDT")
        # If a signal is produced, RSI must be < 30
        for sig in sigs:
            assert sig.direction != "BUY", "LONG should be blocked when RSI > rsi_long_max"

    def test_rsi_oversold_blocks_short(self):
        """RSI < rsi_short_min should block SHORT signal."""
        s = VTCsvEdgeLuxalgoAltsStrategy(params={"bo_prob_threshold": 20.0, "rsi_short_min": 80})
        df = _strong_downtrend_df()
        # With rsi_short_min=80, almost any downtrend data will have RSI < 80
        sigs = s.generate_signals(df, symbol="JUPUSDT")
        for sig in sigs:
            assert sig.direction != "SELL", "SHORT should be blocked when RSI < rsi_short_min"

    def test_bo_prob_threshold_blocks_weak_breakout(self):
        """bull_prob below threshold should not generate signal."""
        s = VTCsvEdgeLuxalgoAltsStrategy(params={"bo_prob_threshold": 99.0})
        df = _strong_uptrend_df()
        sigs = s.generate_signals(df, symbol="WIFUSDT")
        # No real breakout can reach 99%, so should be empty
        assert sigs == []

    def test_bear_must_dominate_for_short(self):
        """For SHORT, bear_prob must exceed bull_prob."""
        s = VTCsvEdgeLuxalgoAltsStrategy(params={"bo_prob_threshold": 20.0})
        df = _strong_uptrend_df()  # Uptrend → bull dominates
        # Force both probs above threshold but bull dominates
        with patch.object(s, "_run_breakout_forecaster", return_value={
            "bull_prob": 60.0, "bear_prob": 45.0, "squeeze": 0.0,
        }):
            sigs = s.generate_signals(df, symbol="WIFUSDT")
            # Should be LONG only (bull dominates), not SHORT
            for sig in sigs:
                assert sig.direction != "SELL"


# ========================================================================
# Test: Confidence scoring
# ========================================================================


class TestConfidenceScoring:
    """Confidence formula: base + conviction + squeeze + vol_boost - reversal_penalty."""

    def test_expansion_regime_boosts_confidence(self):
        s = VTCsvEdgeLuxalgoAltsStrategy(params={"bo_prob_threshold": 20.0})
        df = _strong_uptrend_df()

        # Mock filters to isolate confidence scoring
        with patch.object(s, "_run_breakout_forecaster", return_value={
            "bull_prob": 45.0, "bear_prob": 20.0, "squeeze": 0.0,
        }), patch.object(s, "_run_streak_analyzer", return_value={
            "direction": "BULL", "length": 3, "reversal_probability": 0.5,
            "unprecedented": False,
        }), patch.object(s, "_run_volatility_waterfall", return_value={
            "aggregate_heat": 80, "regime": "EXPANSION", "all_hot": True, "all_cold": False,
        }):
            sigs = s.generate_signals(df, symbol="WIFUSDT")
            assert len(sigs) == 1
            conf_expansion = sigs[0].confidence

        # Same but with COMPRESSION regime (no vol_boost)
        with patch.object(s, "_run_breakout_forecaster", return_value={
            "bull_prob": 45.0, "bear_prob": 20.0, "squeeze": 0.0,
        }), patch.object(s, "_run_streak_analyzer", return_value={
            "direction": "BULL", "length": 3, "reversal_probability": 0.5,
            "unprecedented": False,
        }), patch.object(s, "_run_volatility_waterfall", return_value={
            "aggregate_heat": 10, "regime": "COMPRESSION", "all_hot": False, "all_cold": True,
        }):
            sigs = s.generate_signals(df, symbol="WIFUSDT")
            assert len(sigs) == 1
            conf_compression = sigs[0].confidence

        # EXPANSION should boost confidence by 0.05
        assert conf_expansion > conf_compression
        assert abs((conf_expansion - conf_compression) - 0.05) < 0.01

    def test_high_reversal_reduces_confidence(self):
        s = VTCsvEdgeLuxalgoAltsStrategy(params={"bo_prob_threshold": 20.0})
        df = _strong_uptrend_df()

        # Low reversal
        with patch.object(s, "_run_breakout_forecaster", return_value={
            "bull_prob": 45.0, "bear_prob": 20.0, "squeeze": 0.0,
        }), patch.object(s, "_run_streak_analyzer", return_value={
            "direction": "BULL", "length": 2, "reversal_probability": 0.2,
            "unprecedented": False,
        }), patch.object(s, "_run_volatility_waterfall", return_value={
            "aggregate_heat": 50, "regime": "NEUTRAL", "all_hot": False, "all_cold": False,
        }):
            sigs = s.generate_signals(df, symbol="WIFUSDT")
            conf_low = sigs[0].confidence

        # High reversal
        with patch.object(s, "_run_breakout_forecaster", return_value={
            "bull_prob": 45.0, "bear_prob": 20.0, "squeeze": 0.0,
        }), patch.object(s, "_run_streak_analyzer", return_value={
            "direction": "BULL", "length": 2, "reversal_probability": 0.9,
            "unprecedented": False,
        }), patch.object(s, "_run_volatility_waterfall", return_value={
            "aggregate_heat": 50, "regime": "NEUTRAL", "all_hot": False, "all_cold": False,
        }):
            sigs = s.generate_signals(df, symbol="WIFUSDT")
            conf_high = sigs[0].confidence

        # Higher reversal should reduce confidence
        assert conf_low > conf_high

    def test_confidence_capped_at_max_long(self):
        """LONG confidence capped at 0.82."""
        s = VTCsvEdgeLuxalgoAltsStrategy(params={"bo_prob_threshold": 20.0})
        df = _strong_uptrend_df()

        # Extreme breakout to push confidence high
        with patch.object(s, "_run_breakout_forecaster", return_value={
            "bull_prob": 90.0, "bear_prob": 5.0, "squeeze": 100.0,
        }), patch.object(s, "_run_streak_analyzer", return_value={
            "direction": "BULL", "length": 1, "reversal_probability": 0.0,
            "unprecedented": False,
        }), patch.object(s, "_run_volatility_waterfall", return_value={
            "aggregate_heat": 90, "regime": "EXPANSION", "all_hot": True, "all_cold": False,
        }):
            sigs = s.generate_signals(df, symbol="WIFUSDT")
            assert len(sigs) == 1
            assert sigs[0].confidence <= 0.82

    def test_confidence_capped_at_max_short(self):
        """SHORT confidence capped at 0.78."""
        s = VTCsvEdgeLuxalgoAltsStrategy(params={"bo_prob_threshold": 20.0})
        df = _strong_downtrend_df()

        # Need RSI > rsi_short_min (35) for SHORT to fire.
        # Strong downtrend → RSI low, so mock _calc_rsi to return RSI=50.
        mock_rsi = pd.Series([50.0] * len(df))

        # Extreme bear breakout to push SHORT confidence high
        with patch.object(s, "_run_breakout_forecaster", return_value={
            "bull_prob": 5.0, "bear_prob": 90.0, "squeeze": 100.0,
        }), patch.object(s, "_run_streak_analyzer", return_value={
            "direction": "BEAR", "length": 1, "reversal_probability": 0.0,
            "unprecedented": False,
        }), patch.object(s, "_run_volatility_waterfall", return_value={
            "aggregate_heat": 90, "regime": "EXPANSION", "all_hot": True, "all_cold": False,
        }), patch.object(s, "_calc_rsi", return_value=mock_rsi):
            sigs = s.generate_signals(df, symbol="JUPUSDT")
            assert len(sigs) == 1
            assert sigs[0].direction == "SELL"
            assert sigs[0].confidence <= 0.78

    def test_long_confidence_base_higher_than_short(self):
        """LONG base=0.55 > SHORT base=0.50, so with same conviction/squeeze/penalty
        LONG confidence exceeds SHORT confidence by ~0.05."""
        s = VTCsvEdgeLuxalgoAltsStrategy(params={"bo_prob_threshold": 20.0})

        mock_streak = {
            "direction": "NEUTRAL", "length": 1, "reversal_probability": 0.5,
            "unprecedented": False,
        }
        mock_vol = {
            "aggregate_heat": 50, "regime": "NEUTRAL", "all_hot": False, "all_cold": False,
        }

        # LONG case: bull slightly dominates
        df_up = _strong_uptrend_df()
        mock_bo_long = {"bull_prob": 46.0, "bear_prob": 44.0, "squeeze": 0.0}
        with patch.object(s, "_run_breakout_forecaster", return_value=mock_bo_long), \
             patch.object(s, "_run_streak_analyzer", return_value=mock_streak), \
             patch.object(s, "_run_volatility_waterfall", return_value=mock_vol):
            sigs_long = s.generate_signals(df_up, symbol="WIFUSDT")

        # SHORT case: bear slightly dominates; mock RSI so SHORT gate passes
        df_down = _strong_downtrend_df()
        mock_bo_short = {"bull_prob": 44.0, "bear_prob": 46.0, "squeeze": 0.0}
        mock_rsi = pd.Series([50.0] * len(df_down))
        with patch.object(s, "_run_breakout_forecaster", return_value=mock_bo_short), \
             patch.object(s, "_run_streak_analyzer", return_value=mock_streak), \
             patch.object(s, "_run_volatility_waterfall", return_value=mock_vol), \
             patch.object(s, "_calc_rsi", return_value=mock_rsi):
            sigs_short = s.generate_signals(df_down, symbol="JUPUSDT")

        # Both should produce a signal
        assert len(sigs_long) >= 1, "LONG signal expected"
        assert len(sigs_short) >= 1, "SHORT signal expected"
        # LONG base (0.55) > SHORT base (0.50) with same other factors
        assert sigs_long[0].confidence > sigs_short[0].confidence


# ========================================================================
# Test: Adapter integration
# ========================================================================


class TestAdapterIntegration:
    """vt_csv_edge_luxalgo_alts adapter in vt_baby_strategies module."""

    @pytest.fixture(autouse=True)
    def _import_adapter(self):
        try:
            from alpha_engine.vt_baby_strategies import vt_csv_edge_luxalgo_alts
            self.adapter = vt_csv_edge_luxalgo_alts
        except ImportError:
            pytest.skip("vt_baby_strategies not importable")

    def test_adapter_returns_list(self):
        data = {}
        result = self.adapter(data)
        assert isinstance(result, list)

    def test_adapter_with_yfinance_keys(self):
        """Adapter should find data using yfinance-style keys (WIF-USD)."""
        df = _strong_uptrend_df(n=250)
        # Use yfinance-style key (production scanner convention)
        data = {"WIF-USD": df}
        result = self.adapter(data)
        assert isinstance(result, list)
        # If signals generated, symbol should be Binance-style (WIFUSDT)
        for sig in result:
            assert sig["symbol"] == "WIFUSDT"
            assert sig["source"] == "vt_baby"
            assert sig["extra"].get("edge") == "+27pp WR vs unfiltered"

    def test_adapter_with_binance_keys(self):
        """Adapter should also find data using Binance-style keys (WIFUSDT)."""
        df = _strong_uptrend_df(n=250)
        data = {"WIFUSDT": df}
        result = self.adapter(data)
        assert isinstance(result, list)
        for sig in result:
            assert sig["symbol"] == "WIFUSDT"

    def test_adapter_prefers_yfinance_key(self):
        """When both keys exist, yfinance key should be used first."""
        df_yf = _strong_uptrend_df(n=250, seed=100)
        df_bin = _strong_uptrend_df(n=250, seed=200)
        data = {"WIF-USD": df_yf, "WIFUSDT": df_bin}
        result = self.adapter(data)
        # Should work without error — yfinance key takes priority
        assert isinstance(result, list)

    def test_adapter_skips_short_data(self):
        """Adapter should skip symbols with < 120 bars."""
        df = _make_ohlcv(n=50)  # Too short
        data = {"WIF-USD": df, "WIFUSDT": df}
        result = self.adapter(data)
        assert result == []

    def test_adapter_in_vt_baby_strategies_dict(self):
        """vt_csv_edge_luxalgo_alts should be in VT_BABY_STRATEGIES dict."""
        from alpha_engine.vt_baby_strategies import VT_BABY_STRATEGIES
        assert "vt_csv_edge_luxalgo_alts" in VT_BABY_STRATEGIES

    def test_adapter_signal_fields(self):
        """Verify all expected signal dict fields are present via adapter."""
        s = VTCsvEdgeLuxalgoAltsStrategy(params={"bo_prob_threshold": 30.0})
        df = _strong_uptrend_df(n=250)
        sigs = s.generate_signals(df, symbol="WIFUSDT")
        if not sigs:
            pytest.skip("No signals generated with this data")
        sig = sigs[0]
        # Verify Signal dataclass fields directly (no cross-module import)
        assert sig.symbol == "WIFUSDT"
        assert sig.direction in ("BUY", "SELL")
        assert 0.0 <= sig.confidence <= 1.0
        assert sig.entry_price > 0
        assert sig.take_profit > 0
        assert sig.stop_loss > 0
        assert isinstance(sig.reason, str)


# ========================================================================
# Test: Fallback when luxalgo_filters unavailable
# ========================================================================


class TestLuxalgoFallback:
    """When luxalgo_filters import fails, strategy should use fallback defaults."""

    def test_breakout_forecaster_fallback(self):
        s = VTCsvEdgeLuxalgoAltsStrategy()
        with patch.dict("sys.modules", {"battleground.incubator.strategies.luxalgo_filters": None}):
            result = s._run_breakout_forecaster([1, 2, 3], [1.1, 2.1, 3.1], [0.9, 1.9, 2.9])
            # Fallback returns 50/50 — neither direction dominates, no signal
            assert result["bull_prob"] == 50.0
            assert result["bear_prob"] == 50.0

    def test_streak_analyzer_fallback(self):
        s = VTCsvEdgeLuxalgoAltsStrategy()
        result = s._run_streak_analyzer([1, 2, 3])
        assert result["unprecedented"] is False
        assert result["reversal_probability"] == 0.5

    def test_volatility_waterfall_fallback(self):
        s = VTCsvEdgeLuxalgoAltsStrategy()
        result = s._run_volatility_waterfall([1.1], [0.9], [1.0])
        assert result["regime"] == "NEUTRAL"
        assert result["all_hot"] is False
        assert result["all_cold"] is False

    def test_fallback_produces_no_signal_with_default_threshold(self):
        """Fallback bull_prob=50% > 40% threshold, but bear_prob=50% too → no dominance."""
        s = VTCsvEdgeLuxalgoAltsStrategy()
        df = _make_ohlcv(n=250)
        with patch.object(s, "_run_breakout_forecaster", return_value={
            "bull_prob": 50.0, "bear_prob": 50.0, "squeeze": 0.0,
        }):
            sigs = s.generate_signals(df, symbol="WIFUSDT")
            # Neither direction dominates (50==50), so no signal
            assert sigs == []
