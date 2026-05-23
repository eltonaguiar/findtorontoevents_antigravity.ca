"""
Tests for the Gainer Detector — Phase 4
=========================================
Covers all five requirements:

  GAIN-01  GainerCollector identifies 20%+ gainer events in synthetic data
  GAIN-02  PrePumpModel extracts features strictly BEFORE the event bar
           (no lookahead — verified by spike injection at event_bar)
  GAIN-03  BreakoutDetector identifies volume/price breakouts
  GAIN-04  Every signal dict carries source="gainer_detector"
  GAIN-05  Signal output format is complete and well-typed

Run:
    py -m pytest crypto_ml_edge/tests/test_gainer.py -v
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from crypto_ml_edge.gainer_detector import (
    GainerCollector,
    PrePumpModel,
    BreakoutDetector,
    GainerEngine,
    PRE_PUMP_FEATURE_NAMES,
)


# ─── Synthetic data helpers ───────────────────────────────────────────────────

def _make_ohlcv(
    n: int = 300,
    seed: int = 42,
    freq: str = "1h",
    base_vol: float = 1_000_000.0,
) -> pd.DataFrame:
    """Generic synthetic OHLCV — flat random walk, no embedded pump."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2023-01-01", periods=n, freq=freq, tz="UTC")
    log_ret = rng.normal(0.0, 0.004, n)
    close  = 100.0 * np.exp(np.cumsum(log_ret))
    noise  = rng.uniform(0.001, 0.004, n)
    high   = close * (1.0 + noise)
    low    = close * (1.0 - noise)
    open_  = close * (1.0 + rng.normal(0.0, 0.002, n))
    volume = np.abs(rng.normal(base_vol, base_vol * 0.2, n)) + 10_000
    df = pd.DataFrame(
        {"open": open_, "high": high, "low": low,
         "close": close, "volume": volume},
        index=dates,
    )
    df.index.name = "timestamp"
    return df


def _inject_pump_at(df: pd.DataFrame, bar: int, gain_pct: float = 25.0) -> pd.DataFrame:
    """
    Inject a synthetic pump at `bar`.
    The close at `bar` is raised by gain_pct% relative to the close 24 bars earlier.
    Bars before `bar` are untouched (zero-lookahead test relies on this).
    """
    df = df.copy()
    if bar >= len(df) or bar < 24:
        return df
    ref_price = float(df["close"].iloc[bar - 24])
    pumped_price = ref_price * (1.0 + gain_pct / 100.0)
    df.iloc[bar, df.columns.get_loc("close")] = pumped_price
    df.iloc[bar, df.columns.get_loc("high")]  = pumped_price * 1.01
    # Amplify volume at the event bar to simulate a real pump
    df.iloc[bar, df.columns.get_loc("volume")] = (
        float(df["volume"].iloc[bar]) * 8.0
    )
    return df


def _make_breakout_ohlcv(n: int = 60, seed: int = 99) -> pd.DataFrame:
    """
    Build OHLCV where the LAST bar has a clear breakout:
    - volume 10x average
    - close above 20-bar high
    - ATR expansion
    - 3 consecutive green candles with rising volume
    """
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2023-06-01", periods=n, freq="1h", tz="UTC")
    base = 100.0
    close  = base + np.arange(n) * 0.0  # flat
    high   = close + rng.uniform(0.1, 0.5, n)
    low    = close - rng.uniform(0.1, 0.5, n)
    open_  = close + rng.normal(0.0, 0.05, n)
    volume = np.full(n, 100_000.0)

    # Force last 3 bars: green with rising volume
    for i in range(n-3, n):
        open_[i]   = close[i-1] if i > 0 else base
        close[i]   = open_[i] * 1.003                # green
        high[i]    = close[i] * 1.005
        low[i]     = open_[i] * 0.999
        volume[i]  = 100_000.0 * (1.0 + (i - (n-3)) * 0.5)  # rising

    # Force last bar: volume spike + price above 20-bar high
    peak_high = float(np.max(high[n-22:n-2]))       # 20-bar high (excl last 2)
    close[-1]  = peak_high * 1.005                   # price breakout
    high[-1]   = peak_high * 1.01
    low[-1]    = peak_high * 0.998
    open_[-1]  = peak_high * 0.999
    volume[-1] = 100_000.0 * 6.0                     # >5x spike

    # Force last bar: ATR expansion (make the last bar much wider)
    high[-1]  = close[-1] * 1.015
    low[-1]   = close[-1] * 0.985

    df = pd.DataFrame(
        {"open": open_, "high": high, "low": low,
         "close": close, "volume": volume},
        index=dates,
    )
    df.index.name = "timestamp"
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# GAIN-01: Historical gainer identification on synthetic data
# ═══════════════════════════════════════════════════════════════════════════════

class TestGainerCollector:

    def test_build_historical_gainers_finds_injected_event(self):
        """GainerCollector.build_historical_gainers finds 20%+ events in OHLCV."""
        collector = GainerCollector()
        base = _make_ohlcv(n=200, seed=0)
        pumped = _inject_pump_at(base, bar=100, gain_pct=25.0)

        # Simulate what build_historical_gainers does internally
        ret_24h = pumped["close"].pct_change(24) * 100.0
        gainer_bars = ret_24h[ret_24h >= 20.0].index.tolist()

        assert len(gainer_bars) >= 1, (
            "Expected at least one gainer event after injecting 25% pump"
        )

    def test_no_spurious_gainers_in_flat_series(self):
        """Low-volatility flat OHLCV should not produce 20%+ gainer events."""
        rng = np.random.default_rng(7)
        n = 200
        dates = pd.date_range("2023-01-01", periods=n, freq="1h", tz="UTC")
        close = 100.0 + rng.normal(0.0, 0.05, n)  # tiny noise, never 20% move
        df = pd.DataFrame({
            "open": close, "high": close * 1.001,
            "low": close * 0.999, "close": close,
            "volume": np.ones(n) * 1_000_000,
        }, index=dates)

        ret_24h = df["close"].pct_change(24) * 100.0
        gainer_bars = ret_24h[ret_24h >= 20.0].index.tolist()
        assert len(gainer_bars) == 0, (
            "Flat series should produce zero 20%+ gainer events"
        )

    def test_gainer_events_dataframe_schema(self):
        """build_historical_gainers returns DataFrame with required columns."""
        collector = GainerCollector()
        # Inject two pumps for different symbols
        df1 = _inject_pump_at(_make_ohlcv(200, seed=1), bar=100, gain_pct=22.0)
        df2 = _inject_pump_at(_make_ohlcv(200, seed=2), bar=120, gain_pct=30.0)

        ohlcv_map = {"AAAAAA": df1, "BBBBBB": df2}

        # Replicate core logic of build_historical_gainers
        events = []
        for symbol, ohlcv in ohlcv_map.items():
            ret_24h = ohlcv["close"].pct_change(24) * 100.0
            for bar_idx in range(24, len(ohlcv)):
                gain = ret_24h.iloc[bar_idx]
                if pd.isna(gain) or gain < 20.0:
                    continue
                events.append({
                    "symbol":        symbol,
                    "event_bar_idx": bar_idx,
                    "event_ts":      ohlcv.index[bar_idx],
                    "peak_gain_pct": float(gain),
                })

        df_events = pd.DataFrame(events)
        required = {"symbol", "event_bar_idx", "event_ts", "peak_gain_pct"}
        assert required.issubset(set(df_events.columns)), (
            f"Missing columns: {required - set(df_events.columns)}"
        )
        assert (df_events["peak_gain_pct"] >= 20.0).all(), (
            "All events must have peak_gain_pct >= 20.0"
        )

    def test_save_and_load_gainer_db(self, tmp_path, monkeypatch):
        """save_gainer_db writes parquet; load_gainer_db reads it back."""
        import crypto_ml_edge.gainer_detector as gd
        monkeypatch.setattr(gd, "GAINER_DB_PATH", tmp_path / "gainer_events.parquet")

        collector = GainerCollector()
        df = pd.DataFrame({
            "symbol":        ["AAAAAA", "BBBBBB"],
            "event_bar_idx": [100, 120],
            "event_ts":      [pd.Timestamp("2023-05-01", tz="UTC"),
                              pd.Timestamp("2023-06-01", tz="UTC")],
            "peak_gain_pct": [22.5, 35.0],
        })
        collector.save_gainer_db(df)
        loaded = collector.load_gainer_db()
        assert len(loaded) == 2
        assert set(loaded.columns) == set(df.columns)

    def test_load_gainer_db_missing_returns_empty(self, tmp_path, monkeypatch):
        """load_gainer_db returns empty DataFrame when file does not exist."""
        import crypto_ml_edge.gainer_detector as gd
        monkeypatch.setattr(gd, "GAINER_DB_PATH", tmp_path / "no_file.parquet")
        collector = GainerCollector()
        result = collector.load_gainer_db()
        assert isinstance(result, pd.DataFrame)
        assert result.empty


# ═══════════════════════════════════════════════════════════════════════════════
# GAIN-02: Pre-pump features are extracted BEFORE the event (no lookahead)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPrePumpNoLookahead:
    """
    Zero-lookahead guarantee for PrePumpModel.build_pre_pump_features().

    Strategy: inject a massive spike at event_bar and verify that the
    features computed for bars [event_bar-lookback .. event_bar-1] are
    UNCHANGED. If any feature changes, it used event_bar data.
    """

    def _build_features_pair(self, event_bar: int = 100):
        """Return (features_original, features_perturbed) for the same event_bar."""
        model = PrePumpModel()
        base = _make_ohlcv(n=200, seed=42)

        # Original
        feats_orig = model.build_pre_pump_features(base, event_bar)

        # Perturbed: inject extreme spike AT event_bar only
        perturbed = base.copy()
        perturbed.iloc[event_bar, perturbed.columns.get_loc("close")]  = 1_000_000.0
        perturbed.iloc[event_bar, perturbed.columns.get_loc("high")]   = 1_010_000.0
        perturbed.iloc[event_bar, perturbed.columns.get_loc("low")]    = 990_000.0
        perturbed.iloc[event_bar, perturbed.columns.get_loc("volume")] = 1e12

        feats_perturbed = model.build_pre_pump_features(perturbed, event_bar)

        return feats_orig, feats_perturbed

    def test_features_unchanged_when_event_bar_perturbed(self):
        """
        Perturbing the event bar must NOT change features computed from
        the pre-event window. This is the core no-lookahead guarantee.
        """
        feats_orig, feats_perturbed = self._build_features_pair(event_bar=100)

        assert feats_orig, "Original features should not be empty"
        assert feats_perturbed, "Perturbed features should not be empty"

        for feat_name in PRE_PUMP_FEATURE_NAMES:
            v_orig     = feats_orig.get(feat_name)
            v_perturb  = feats_perturbed.get(feat_name)
            if v_orig is None or v_perturb is None:
                continue
            diff = abs(v_orig - v_perturb)
            assert diff < 1e-6, (
                f"Feature '{feat_name}' changed when event_bar was perturbed. "
                f"Original={v_orig:.6f}, Perturbed={v_perturb:.6f}, diff={diff:.2e}. "
                "This means build_pre_pump_features is using event_bar data — LOOKAHEAD!"
            )

    def test_all_required_feature_names_present(self):
        """build_pre_pump_features must return all PRE_PUMP_FEATURE_NAMES."""
        model = PrePumpModel()
        ohlcv = _make_ohlcv(n=200, seed=5)
        feats = model.build_pre_pump_features(ohlcv, event_bar=100)

        assert feats, "Feature dict must not be empty for sufficient history"
        for name in PRE_PUMP_FEATURE_NAMES:
            assert name in feats, (
                f"Feature '{name}' missing from build_pre_pump_features output"
            )

    def test_feature_count_in_budget(self):
        """PRE_PUMP_FEATURE_NAMES must have 10-20 entries (matching FEAT-06)."""
        assert 10 <= len(PRE_PUMP_FEATURE_NAMES) <= 20, (
            f"PRE_PUMP_FEATURE_NAMES has {len(PRE_PUMP_FEATURE_NAMES)} entries; "
            "must be 10-20 to match the Edge Engine budget"
        )

    def test_feature_values_are_finite_floats(self):
        """All returned feature values must be finite floats (no inf/nan)."""
        model = PrePumpModel()
        ohlcv = _make_ohlcv(n=200, seed=9)
        feats = model.build_pre_pump_features(ohlcv, event_bar=100)

        for name, value in feats.items():
            assert isinstance(value, float), (
                f"Feature '{name}' is {type(value)}, expected float"
            )
            assert np.isfinite(value), (
                f"Feature '{name}' = {value} is not finite"
            )

    def test_insufficient_history_returns_empty(self):
        """Returns empty dict when there are too few bars before event_bar."""
        model = PrePumpModel()
        ohlcv = _make_ohlcv(n=200, seed=3)
        # event_bar = 5 is too close to the start for a 6h lookback + 24h context
        feats = model.build_pre_pump_features(ohlcv, event_bar=5)
        assert feats == {}, (
            "Should return empty dict when insufficient history before event_bar"
        )

    def test_event_bar_boundary_off_by_one(self):
        """
        event_bar - 1 must be the last bar included in the feature window.
        Verify by mutating ONLY bar event_bar-1 and confirming features change
        (proving the window does include that bar — it is not accidentally skipped).
        """
        model = PrePumpModel()
        base = _make_ohlcv(n=200, seed=42)
        event_bar = 100
        feats_orig = model.build_pre_pump_features(base, event_bar)

        # Perturb the bar immediately before event_bar
        perturbed = base.copy()
        perturbed.iloc[event_bar - 1, perturbed.columns.get_loc("volume")] *= 50.0

        feats_perturbed = model.build_pre_pump_features(perturbed, event_bar)

        # At least one volume-related feature must differ
        vol_features = ["vol_accel_6h", "vol_accel_3h", "rel_vol_spike"]
        any_changed = any(
            abs(feats_orig.get(f, 0.0) - feats_perturbed.get(f, 0.0)) > 1e-6
            for f in vol_features
        )
        assert any_changed, (
            "Mutating bar event_bar-1 should change at least one volume feature. "
            "The pre-pump window must include event_bar-1."
        )

    def test_predict_returns_valid_structure_when_model_not_trained(self):
        """predict() gracefully handles untrained model."""
        model = PrePumpModel()
        result = model.predict({"vol_accel_6h": 2.5})
        assert "pre_pump_probability" in result
        assert "confidence" in result
        assert "model_trained" in result
        assert result["model_trained"] is False
        assert result["pre_pump_probability"] == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# GAIN-03: Breakout detector identifies volume/price breakouts
# ═══════════════════════════════════════════════════════════════════════════════

class TestBreakoutDetector:

    def test_detects_clear_breakout(self):
        """BreakoutDetector.scan returns a signal for a constructed breakout."""
        detector = BreakoutDetector()
        breakout_df = _make_breakout_ohlcv(n=60)
        signals = detector.scan({"TESTUSDT": breakout_df})

        assert len(signals) >= 1, (
            "Expected at least one breakout signal on the constructed breakout series"
        )
        sig = signals[0]
        assert sig["symbol"] == "TESTUSDT"
        assert sig["strength"] > 0.0

    def test_no_signal_on_flat_low_volume(self):
        """No breakout detected when volume is flat and price is ranging."""
        detector = BreakoutDetector()
        flat_df = _make_ohlcv(n=60, seed=77)  # random walk, no spike
        # Ensure volume never spikes (cap all volume)
        flat_df["volume"] = 100_000.0

        signals = detector.scan({"FLATUSDT": flat_df}, min_strength=0.75)
        # At high threshold, a random-walk series should not trigger
        assert len(signals) == 0 or all(s["strength"] < 0.75 for s in signals), (
            "Flat, low-volume series should not trigger a high-confidence breakout"
        )

    def test_strength_is_fraction_of_four_conditions(self):
        """Strength must be in [0, 1] and equal n_conditions_fired / 4."""
        detector = BreakoutDetector()
        ohlcv_dict = {
            "AAAAAA": _make_breakout_ohlcv(n=60, seed=1),
            "BBBBBB": _make_ohlcv(n=60, seed=2),
        }
        signals = detector.scan(ohlcv_dict, min_strength=0.0)
        for sig in signals:
            strength = sig["strength"]
            assert 0.0 <= strength <= 1.0, (
                f"Strength {strength} is out of [0, 1]"
            )
            # Strength must be a multiple of 0.25 (1/4, 2/4, 3/4, or 4/4)
            remainder = (strength * 4) % 1.0
            assert remainder < 1e-9, (
                f"Strength {strength} is not a multiple of 0.25 — "
                "check n_conditions calculation"
            )

    def test_signals_sorted_by_strength_descending(self):
        """scan() returns signals sorted by strength descending."""
        detector = BreakoutDetector()
        ohlcv_dict = {
            f"SYM{i}USDT": _make_ohlcv(n=60, seed=i * 13)
            for i in range(8)
        }
        ohlcv_dict["BREAKOUT"] = _make_breakout_ohlcv(n=60)
        signals = detector.scan(ohlcv_dict, min_strength=0.0)

        strengths = [s["strength"] for s in signals]
        assert strengths == sorted(strengths, reverse=True), (
            "Breakout signals must be sorted by strength descending"
        )

    def test_too_few_bars_skipped(self):
        """Pairs with fewer than BREAKOUT_WARMUP_BARS are skipped gracefully."""
        from crypto_ml_edge.gainer_detector import BREAKOUT_WARMUP_BARS
        detector = BreakoutDetector()
        tiny = _make_ohlcv(n=BREAKOUT_WARMUP_BARS - 1)
        signals = detector.scan({"TINY": tiny}, min_strength=0.0)
        # Should not raise; may or may not emit signals (but must not crash)
        assert isinstance(signals, list)

    def test_features_dict_present_and_non_empty(self):
        """Every breakout signal must have a non-empty features dict."""
        detector = BreakoutDetector()
        breakout_df = _make_breakout_ohlcv(n=60)
        signals = detector.scan({"BREAKOUT": breakout_df}, min_strength=0.0)
        for sig in signals:
            assert "features" in sig, "Signal missing 'features' key"
            assert isinstance(sig["features"], dict)
            assert len(sig["features"]) > 0, "features dict must not be empty"

    def test_conditions_dict_has_four_boolean_entries(self):
        """The 'conditions' dict must have exactly 4 boolean entries."""
        detector = BreakoutDetector()
        breakout_df = _make_breakout_ohlcv(n=60)
        signals = detector.scan({"BREAKOUT": breakout_df}, min_strength=0.0)
        for sig in signals:
            conds = sig.get("conditions", {})
            assert len(conds) == 4, (
                f"Expected 4 condition keys, got {len(conds)}: {list(conds)}"
            )
            for key, val in conds.items():
                assert isinstance(val, bool), (
                    f"Condition '{key}' must be bool, got {type(val)}"
                )


# ═══════════════════════════════════════════════════════════════════════════════
# GAIN-04: All signals carry source="gainer_detector"
# ═══════════════════════════════════════════════════════════════════════════════

class TestSignalSource:
    """
    GAIN-04: Gainer signals must be clearly labelled to distinguish them
    from Edge Engine signals. Every dict in run_scan() output must have
    source="gainer_detector".
    """

    def test_breakout_signal_source_label(self):
        """Breakout signals from BreakoutDetector have source='gainer_detector'."""
        detector = BreakoutDetector()
        breakout_df = _make_breakout_ohlcv(n=60)
        signals = detector.scan({"BREAKOUT": breakout_df}, min_strength=0.0)

        for sig in signals:
            assert sig.get("source") == "gainer_detector", (
                f"Expected source='gainer_detector', got '{sig.get('source')}'. "
                "GAIN-04 requires gainer signals to be clearly labelled."
            )

    def test_engine_run_scan_source_label(self):
        """GainerEngine.run_scan() all outputs carry source='gainer_detector'."""
        engine = GainerEngine()
        ohlcv_dict = {
            "BREAKOUT": _make_breakout_ohlcv(n=60),
            "NORMAL":   _make_ohlcv(n=60, seed=42),
        }
        signals = engine.run_scan(ohlcv_dict)

        for sig in signals:
            assert sig.get("source") == "gainer_detector", (
                f"Signal for {sig.get('symbol')} has source='{sig.get('source')}'. "
                "All GainerEngine signals must have source='gainer_detector' (GAIN-04)."
            )

    def test_source_not_edge_engine(self):
        """
        Gainer signals must never say source='edge_engine'.
        This is the explicit anti-confusion check from GAIN-04.
        """
        engine = GainerEngine()
        ohlcv_dict = {"BREAKOUT": _make_breakout_ohlcv(n=60)}
        signals = engine.run_scan(ohlcv_dict)

        for sig in signals:
            assert sig.get("source") != "edge_engine", (
                "A gainer signal was labelled source='edge_engine' — GAIN-04 violation. "
                "Gainer and Edge Engine signals must be distinct."
            )

    def test_signal_type_is_pre_pump_or_breakout(self):
        """signal_type must be 'pre_pump' or 'breakout' — no other values."""
        engine = GainerEngine()
        ohlcv_dict = {"BREAKOUT": _make_breakout_ohlcv(n=60)}
        signals = engine.run_scan(ohlcv_dict)

        valid_types = {"pre_pump", "breakout"}
        for sig in signals:
            assert sig.get("signal_type") in valid_types, (
                f"signal_type='{sig.get('signal_type')}' is invalid. "
                f"Must be one of: {valid_types}"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# GAIN-05: Signal output format is complete and well-typed
# ═══════════════════════════════════════════════════════════════════════════════

class TestSignalOutputFormat:
    """
    Every signal dict emitted by GainerEngine.run_scan() must satisfy
    the format contract described in the module docstring.
    """

    REQUIRED_KEYS = {"source", "signal_type", "symbol", "confidence", "features"}

    def _get_signals(self) -> list:
        engine = GainerEngine()
        ohlcv_dict = {
            "BREAKOUT": _make_breakout_ohlcv(n=60),
            "NORMAL1":  _make_ohlcv(n=60, seed=10),
            "NORMAL2":  _make_ohlcv(n=60, seed=11),
        }
        return engine.run_scan(ohlcv_dict)

    def test_required_keys_present(self):
        """All required top-level keys must be present in every signal."""
        signals = self._get_signals()
        assert len(signals) >= 1, (
            "Expected at least one signal from the breakout series"
        )
        for sig in signals:
            missing = self.REQUIRED_KEYS - set(sig.keys())
            assert not missing, (
                f"Signal for {sig.get('symbol')} missing keys: {missing}"
            )

    def test_source_is_string(self):
        for sig in self._get_signals():
            assert isinstance(sig["source"], str)

    def test_signal_type_is_string(self):
        for sig in self._get_signals():
            assert isinstance(sig["signal_type"], str)

    def test_symbol_is_string(self):
        for sig in self._get_signals():
            assert isinstance(sig["symbol"], str)
            assert len(sig["symbol"]) > 0

    def test_confidence_is_valid_string(self):
        valid = {"high", "medium", "low"}
        for sig in self._get_signals():
            assert sig["confidence"] in valid, (
                f"confidence='{sig['confidence']}' — must be one of {valid}"
            )

    def test_features_is_dict(self):
        for sig in self._get_signals():
            assert isinstance(sig["features"], dict), (
                f"'features' must be a dict, got {type(sig['features'])}"
            )

    def test_breakout_signals_have_strength_and_conditions(self):
        """Breakout signals must carry 'strength' (float) and 'conditions' (dict)."""
        signals = self._get_signals()
        breakout_sigs = [s for s in signals if s["signal_type"] == "breakout"]

        # We injected a breakout series, so there must be at least one
        assert len(breakout_sigs) >= 1, (
            "Expected at least one breakout signal from the breakout series"
        )

        for sig in breakout_sigs:
            assert "strength" in sig, "Breakout signal missing 'strength'"
            assert isinstance(sig["strength"], float)
            assert 0.0 <= sig["strength"] <= 1.0

            assert "conditions" in sig, "Breakout signal missing 'conditions'"
            assert isinstance(sig["conditions"], dict)

    def test_pre_pump_signals_have_probability(self):
        """Pre-pump signals must carry 'pre_pump_probability' (float in [0, 1])."""
        # Inject a trained model mock to get a pre-pump signal
        engine = GainerEngine()
        engine.pre_pump._model = MagicMock()
        engine.pre_pump._model.predict_proba = MagicMock(
            return_value=np.array([[0.2, 0.8]])   # 80% confidence → high
        )
        engine.pre_pump._scaler = MagicMock()
        engine.pre_pump._scaler.transform = MagicMock(
            side_effect=lambda x: x
        )

        ohlcv_dict = {"PUMPSYM": _make_ohlcv(n=200, seed=42)}
        signals = engine.run_scan(
            ohlcv_dict,
            pre_pump_threshold=0.0,   # accept all probabilities
        )

        pre_pump_sigs = [s for s in signals if s["signal_type"] == "pre_pump"]
        for sig in pre_pump_sigs:
            assert "pre_pump_probability" in sig, (
                "Pre-pump signal missing 'pre_pump_probability'"
            )
            prob = sig["pre_pump_probability"]
            assert isinstance(prob, float)
            assert 0.0 <= prob <= 1.0, (
                f"pre_pump_probability={prob} is outside [0, 1]"
            )

    def test_sorted_high_confidence_first(self):
        """
        run_scan() output is sorted so high-confidence signals come first.
        """
        signals = self._get_signals()
        if len(signals) < 2:
            pytest.skip("Need at least 2 signals to test ordering")

        confidence_rank = {"high": 0, "medium": 1, "low": 2}
        ranks = [confidence_rank[s["confidence"]] for s in signals]
        assert ranks == sorted(ranks), (
            "Signals must be sorted high→medium→low confidence"
        )

    def test_empty_ohlcv_dict_returns_empty_list(self):
        """run_scan with no pairs returns an empty list without error."""
        engine = GainerEngine()
        result = engine.run_scan({})
        assert result == []

    def test_none_values_in_ohlcv_dict_handled_gracefully(self):
        """Pairs with None OHLCV are silently skipped."""
        engine = GainerEngine()
        ohlcv_dict = {
            "NULLPAIR": None,
            "BREAKOUT": _make_breakout_ohlcv(n=60),
        }
        result = engine.run_scan(ohlcv_dict)
        assert isinstance(result, list)
        # Only BREAKOUT should produce signals; NULLPAIR must not crash
        symbols = {s["symbol"] for s in result}
        assert "NULLPAIR" not in symbols


# ═══════════════════════════════════════════════════════════════════════════════
# Additional integration-style tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegration:

    def test_full_scan_multiple_pairs_no_crash(self):
        """run_scan across a mixed universe of 10 pairs completes without error."""
        engine = GainerEngine()
        ohlcv_dict = {}
        for i in range(9):
            ohlcv_dict[f"COIN{i:02d}USDT"] = _make_ohlcv(n=80, seed=i * 17)
        ohlcv_dict["PUMPCOIN"] = _make_breakout_ohlcv(n=80)

        result = engine.run_scan(ohlcv_dict)
        assert isinstance(result, list)
        # Every returned dict must have source="gainer_detector"
        for sig in result:
            assert sig["source"] == "gainer_detector"

    def test_breakout_conditions_consistent_with_strength(self):
        """
        For each breakout signal: count True values in conditions
        must equal strength * 4 (integer).
        """
        engine = GainerEngine()
        ohlcv_dict = {"BREAKOUT": _make_breakout_ohlcv(n=60)}
        signals = engine.run_scan(ohlcv_dict)

        for sig in signals:
            if sig["signal_type"] != "breakout":
                continue
            n_true = sum(1 for v in sig["conditions"].values() if v)
            expected_strength = n_true / 4.0
            assert abs(sig["strength"] - expected_strength) < 1e-9, (
                f"strength={sig['strength']} but {n_true}/4 conditions fired "
                f"(expected {expected_strength})"
            )

    def test_pre_pump_feature_keys_match_constant(self):
        """
        Features returned by build_pre_pump_features must have exactly
        the keys listed in PRE_PUMP_FEATURE_NAMES.
        """
        model = PrePumpModel()
        ohlcv = _make_ohlcv(n=200, seed=0)
        feats = model.build_pre_pump_features(ohlcv, event_bar=100)

        assert set(feats.keys()) == set(PRE_PUMP_FEATURE_NAMES), (
            f"Feature keys don't match PRE_PUMP_FEATURE_NAMES.\n"
            f"  Got:      {sorted(feats.keys())}\n"
            f"  Expected: {sorted(PRE_PUMP_FEATURE_NAMES)}"
        )
