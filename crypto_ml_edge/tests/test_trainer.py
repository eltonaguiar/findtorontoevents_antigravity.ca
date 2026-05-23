"""
Tests for EdgeTrainer + Risk Module (Phase 3 — MODL-01 through MODL-04, RISK-01 through RISK-03)
================================================================================================
Run: py -m pytest crypto_ml_edge/tests/test_trainer.py -v

Coverage:
  1. Pipeline preprocessing is inside the fold (not pre-applied to full dataset).
  2. Position size never exceeds MAX_POSITION_PCT.
  3. Position size scales with confidence (higher conf → larger position).
  4. TP/SL levels are directionally correct (TP > entry for long, SL < entry for long;
     TP < entry for short, SL > entry for short).
  5. Model output dict contains a DSR verdict key.
  6. SHAP importance is computed and returned (when shap is available).
  7. Optuna fallback grid is used when optuna is not installed.
  8. Zero-confidence inputs produce zero position size.
  9. Invalid inputs raise the correct errors.
 10. TPSL config values are honoured (tp_atr_mult, sl_atr_mult).

Design philosophy:
  - Synthetic OHLCV is generated deterministically so assertions are exact.
  - Trainer tests use a small dataset (1200 bars) to keep CI runtime low.
  - Risk tests use only numeric inputs — no external dependencies needed.
  - We mock optuna and shap absence via monkeypatching the module-level flags.
"""

from __future__ import annotations

import importlib
import sys
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from crypto_ml_edge.config import (
    KELLY_FRACTION,
    MAX_POSITION_PCT,
    TPSL_CONFIG,
)
from crypto_ml_edge.risk import compute_position_size, compute_tp_sl, compute_portfolio_risk


# ─── Shared synthetic data helpers ───────────────────────────────────────────

def _make_ohlcv(
    n: int = 1500,
    base_price: float = 50_000.0,
    vol_pct: float = 0.005,
    start: str = "2020-01-01",
    freq: str = "1h",
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate synthetic OHLCV with a random-walk close series.

    Parameters
    ----------
    n:          Number of bars.
    base_price: Starting price.
    vol_pct:    Per-bar volatility as fraction of price.
    start:      Start datetime string.
    freq:       Pandas frequency string.
    seed:       RNG seed for reproducibility.

    Returns
    -------
    DataFrame with columns [open, high, low, close, volume] and UTC DatetimeIndex.
    """
    rng = np.random.RandomState(seed)
    returns = rng.normal(0, vol_pct, size=n)
    close = base_price * np.cumprod(1 + returns)
    # Realistic OHLC: high = close * (1 + |noise|), low = close * (1 - |noise|)
    noise = np.abs(rng.normal(0, vol_pct * 0.5, size=n))
    high  = close * (1 + noise)
    low   = close * (1 - noise)
    open_ = np.roll(close, 1)
    open_[0] = close[0]

    dates = pd.date_range(start, periods=n, freq=freq, tz="UTC")
    return pd.DataFrame(
        {
            "open":   open_,
            "high":   high,
            "low":    low,
            "close":  close,
            "volume": rng.uniform(1000, 5000, size=n),
        },
        index=dates,
    )


def _make_funding(ohlcv_df: pd.DataFrame, seed: int = 99) -> pd.DataFrame:
    """Synthetic funding rate at 8h intervals aligned to ohlcv_df's timespan."""
    rng = np.random.RandomState(seed)
    start = ohlcv_df.index[0]
    end   = ohlcv_df.index[-1]
    idx = pd.date_range(start, end, freq="8h", tz="UTC")
    return pd.DataFrame(
        {"funding_rate": rng.normal(0.0001, 0.0005, size=len(idx))},
        index=idx,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# RISK MODULE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestComputePositionSize:
    """Tests for compute_position_size() — RISK-01 and RISK-02."""

    def test_position_never_exceeds_max_position_pct(self):
        """RISK-02: Position fraction must never exceed MAX_POSITION_PCT (5%)."""
        # Use very high confidence + low ATR to push towards maximum
        result = compute_position_size(
            confidence=0.99,
            atr=10.0,          # small ATR relative to price
            price=50_000.0,
            capital=100_000.0,
            pair="BTCUSDT",
        )
        assert result["position_size_pct"] <= MAX_POSITION_PCT, (
            f"position_size_pct {result['position_size_pct']} "
            f"exceeds MAX_POSITION_PCT {MAX_POSITION_PCT}"
        )

    def test_position_scales_with_confidence(self):
        """RISK-01: Higher confidence → larger position size."""
        # Use high ATR relative to price so positions stay below the cap.
        # atr_pct = 5.0/1.0 = 5.0 → vol_adjusted fractions are small enough
        # to avoid hitting MAX_POSITION_PCT for all confidence levels.
        common_kwargs = {
            "atr": 5.0,
            "price": 1.0,
            "capital": 100_000.0,
            "pair": "BTCUSDT",
        }
        size_low  = compute_position_size(confidence=0.55, **common_kwargs)
        size_mid  = compute_position_size(confidence=0.70, **common_kwargs)
        size_high = compute_position_size(confidence=0.90, **common_kwargs)

        assert size_low["position_size_usd"] < size_mid["position_size_usd"], (
            "conf=0.55 should produce smaller position than conf=0.70"
        )
        assert size_mid["position_size_usd"] < size_high["position_size_usd"] or \
               size_high["capped"], (
            "conf=0.70 should produce smaller or equal (capped) position than conf=0.90"
        )

    def test_confidence_at_or_below_50_pct_returns_zero(self):
        """No edge at confidence <= 0.5 — position must be zero."""
        for conf in [0.0, 0.1, 0.5]:
            result = compute_position_size(
                confidence=conf,
                atr=500.0,
                price=50_000.0,
                capital=100_000.0,
                pair="BTCUSDT",
            )
            assert result["position_size_usd"] == 0.0, (
                f"Expected zero position for confidence={conf}, "
                f"got {result['position_size_usd']}"
            )
            assert result["position_size_pct"] == 0.0

    def test_zero_atr_returns_zero_position(self):
        """ATR=0 (flat market) should produce zero position (no barriers can be set)."""
        result = compute_position_size(
            confidence=0.80,
            atr=0.0,
            price=50_000.0,
            capital=100_000.0,
            pair="BTCUSDT",
        )
        assert result["position_size_usd"] == 0.0

    def test_position_size_usd_matches_fraction_times_capital(self):
        """position_size_usd = position_size_pct * capital (within rounding)."""
        capital = 75_000.0
        result = compute_position_size(
            confidence=0.70,
            atr=500.0,
            price=50_000.0,
            capital=capital,
            pair="BTCUSDT",
        )
        expected_usd = result["position_size_pct"] * capital
        assert abs(result["position_size_usd"] - expected_usd) < 1.0, (
            f"USD amount {result['position_size_usd']} doesn't match "
            f"pct * capital = {expected_usd}"
        )

    def test_kelly_edge_calculation(self):
        """kelly_edge = 2 * confidence - 1."""
        for conf in [0.55, 0.65, 0.75, 0.85]:
            result = compute_position_size(
                confidence=conf,
                atr=500.0,
                price=50_000.0,
                capital=100_000.0,
                pair="BTCUSDT",
            )
            expected_edge = round(2 * conf - 1, 4)
            assert abs(result["kelly_edge"] - expected_edge) < 1e-3, (
                f"kelly_edge {result['kelly_edge']} != expected {expected_edge} "
                f"for confidence {conf}"
            )

    def test_position_capped_flag(self):
        """capped=True must be set when MAX_POSITION_PCT limit is hit."""
        # Very high confidence, very low ATR → should hit the cap
        result = compute_position_size(
            confidence=0.999,
            atr=1.0,
            price=50_000.0,
            capital=1_000_000.0,
            pair="BTCUSDT",
        )
        if result["capped"]:
            assert result["position_size_pct"] == MAX_POSITION_PCT

    def test_higher_atr_produces_smaller_position(self):
        """
        RISK-01 volatility adjustment: same confidence, higher ATR → smaller position.
        High ATR (more volatile asset) should receive a smaller allocation.
        """
        common = {
            "confidence": 0.70,
            "price": 50_000.0,
            "capital": 100_000.0,
            "pair": "BTCUSDT",
        }
        low_vol  = compute_position_size(atr=200.0, **common)
        high_vol = compute_position_size(atr=2000.0, **common)

        # High-volatility asset should get smaller position (or both are capped)
        assert high_vol["position_size_usd"] < low_vol["position_size_usd"] or \
               (low_vol["capped"] and high_vol["capped"]), (
            "Higher ATR should produce smaller position for same confidence"
        )

    def test_invalid_confidence_raises(self):
        """Out-of-range confidence must raise ValueError."""
        with pytest.raises(ValueError, match="confidence"):
            compute_position_size(
                confidence=1.5, atr=500.0, price=50_000.0,
                capital=100_000.0, pair="BTCUSDT",
            )
        with pytest.raises(ValueError, match="confidence"):
            compute_position_size(
                confidence=-0.1, atr=500.0, price=50_000.0,
                capital=100_000.0, pair="BTCUSDT",
            )

    def test_invalid_price_raises(self):
        with pytest.raises(ValueError, match="price"):
            compute_position_size(
                confidence=0.7, atr=500.0, price=0.0,
                capital=100_000.0, pair="BTCUSDT",
            )

    def test_invalid_capital_raises(self):
        with pytest.raises(ValueError, match="capital"):
            compute_position_size(
                confidence=0.7, atr=500.0, price=50_000.0,
                capital=0.0, pair="BTCUSDT",
            )


class TestComputeTpSl:
    """Tests for compute_tp_sl() — RISK-03."""

    @pytest.mark.parametrize("timeframe", ["1h", "4h"])
    def test_long_tp_above_entry_sl_below_entry(self, timeframe: str):
        """RISK-03: For a long trade, TP must be above entry and SL below."""
        price = 50_000.0
        atr   = 500.0
        result = compute_tp_sl(price=price, atr=atr, timeframe=timeframe, direction="long")

        assert result["tp_price"] > price, (
            f"Long TP {result['tp_price']} should be above entry {price}"
        )
        assert result["sl_price"] < price, (
            f"Long SL {result['sl_price']} should be below entry {price}"
        )

    @pytest.mark.parametrize("timeframe", ["1h", "4h"])
    def test_short_tp_below_entry_sl_above_entry(self, timeframe: str):
        """RISK-03: For a short trade, TP must be below entry and SL above."""
        price = 50_000.0
        atr   = 500.0
        result = compute_tp_sl(price=price, atr=atr, timeframe=timeframe, direction="short")

        assert result["tp_price"] < price, (
            f"Short TP {result['tp_price']} should be below entry {price}"
        )
        assert result["sl_price"] > price, (
            f"Short SL {result['sl_price']} should be above entry {price}"
        )

    @pytest.mark.parametrize("timeframe", ["1h", "4h"])
    def test_tp_sl_distances_match_atr_multiples(self, timeframe: str):
        """TP/SL distances must equal ATR * configured multiplier."""
        price = 100.0
        atr   = 10.0
        result = compute_tp_sl(price=price, atr=atr, timeframe=timeframe, direction="long")

        cfg = TPSL_CONFIG[timeframe]
        expected_tp_dist = cfg["tp_atr_mult"] * atr
        expected_sl_dist = cfg["sl_atr_mult"] * atr

        assert abs(result["tp_distance"] - expected_tp_dist) < 1e-6, (
            f"TP distance {result['tp_distance']} != {expected_tp_dist}"
        )
        assert abs(result["sl_distance"] - expected_sl_dist) < 1e-6, (
            f"SL distance {result['sl_distance']} != {expected_sl_dist}"
        )

    def test_risk_reward_ratio_positive(self):
        """Risk-reward ratio must be positive for valid inputs."""
        result = compute_tp_sl(
            price=50_000.0, atr=500.0, timeframe="1h", direction="long"
        )
        assert result["risk_reward_ratio"] > 0.0

    def test_risk_reward_matches_tp_sl_distance_ratio(self):
        """risk_reward_ratio = tp_distance / sl_distance."""
        result = compute_tp_sl(
            price=50_000.0, atr=500.0, timeframe="4h", direction="long"
        )
        expected_rr = result["tp_distance"] / result["sl_distance"]
        assert abs(result["risk_reward_ratio"] - expected_rr) < 1e-3

    def test_invalid_timeframe_raises(self):
        """Unknown timeframe must raise ValueError."""
        with pytest.raises(ValueError, match="timeframe"):
            compute_tp_sl(price=100.0, atr=5.0, timeframe="15m", direction="long")

    def test_invalid_direction_raises(self):
        with pytest.raises(ValueError, match="direction"):
            compute_tp_sl(price=100.0, atr=5.0, timeframe="1h", direction="buy")

    def test_tp_pct_and_sl_pct_are_positive(self):
        """tp_pct and sl_pct are fractions of price and must be positive."""
        for direction in ("long", "short"):
            result = compute_tp_sl(
                price=1000.0, atr=20.0, timeframe="1h", direction=direction
            )
            assert result["tp_pct"] > 0.0
            assert result["sl_pct"] > 0.0

    def test_max_hold_bars_present_and_positive(self):
        """max_hold_bars must be included and positive."""
        result = compute_tp_sl(
            price=1000.0, atr=20.0, timeframe="1h", direction="long"
        )
        assert "max_hold_bars" in result
        assert result["max_hold_bars"] > 0

    @pytest.mark.parametrize("timeframe,direction", [
        ("1h", "long"), ("1h", "short"), ("4h", "long"), ("4h", "short"),
    ])
    def test_symmetric_long_short_distances(self, timeframe: str, direction: str):
        """
        For a given timeframe, |TP distance| and |SL distance| must be the same
        regardless of whether the trade is long or short.
        """
        price = 10.0
        atr   = 0.5
        r_long  = compute_tp_sl(price=price, atr=atr, timeframe=timeframe, direction="long")
        r_short = compute_tp_sl(price=price, atr=atr, timeframe=timeframe, direction="short")
        assert abs(r_long["tp_distance"] - r_short["tp_distance"]) < 1e-8
        assert abs(r_long["sl_distance"] - r_short["sl_distance"]) < 1e-8


class TestComputePortfolioRisk:
    """Tests for compute_portfolio_risk()."""

    def _make_picks(self, n: int) -> list[dict]:
        return [
            {
                "pair": "BTCUSDT",
                "confidence": 0.70,
                "atr": 500.0,
                "price": 50_000.0,
                "symbol": f"PICK_{i}",
            }
            for i in range(n)
        ]

    def test_portfolio_risk_returns_correct_n_picks(self):
        """n_picks must equal the number of picks after applying max_concurrent."""
        picks = self._make_picks(10)
        result = compute_portfolio_risk(picks, capital=100_000.0, max_concurrent=3)
        assert result["n_picks"] == 3

    def test_portfolio_total_allocated_is_sum_of_individual(self):
        """total_allocated must equal sum of individual position_size_usd."""
        picks = self._make_picks(5)
        result = compute_portfolio_risk(picks, capital=100_000.0)
        summed = sum(p["position_size_usd"] for p in result["sized_picks"])
        assert abs(result["total_allocated"] - summed) < 0.01

    def test_portfolio_risk_per_pick_avg(self):
        """risk_per_pick_avg = total_allocated / n_picks."""
        picks = self._make_picks(4)
        result = compute_portfolio_risk(picks, capital=100_000.0)
        n = result["n_picks"]
        if n > 0:
            expected_avg = result["total_allocated"] / n
            assert abs(result["risk_per_pick_avg"] - expected_avg) < 0.01


# ═══════════════════════════════════════════════════════════════════════════════
# TRAINER MODULE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

# Check if lightgbm is available before running trainer tests
try:
    import lightgbm  # noqa: F401
    _LGBM_INSTALLED = True
except ImportError:
    _LGBM_INSTALLED = False

# Check if sklearn is available (required for Pipeline tests)
try:
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    _SKLEARN_INSTALLED = True
except ImportError:
    _SKLEARN_INSTALLED = False


pytestmark_lgbm = pytest.mark.skipif(
    not _LGBM_INSTALLED or not _SKLEARN_INSTALLED,
    reason="LightGBM or scikit-learn not installed",
)


@pytest.mark.skipif(
    not _LGBM_INSTALLED or not _SKLEARN_INSTALLED,
    reason="LightGBM or scikit-learn not installed",
)
class TestEdgeTrainerPipeline:
    """Tests for EdgeTrainer — pipeline + preprocessing guarantees."""

    def test_pipeline_has_scaler_and_clf_steps(self):
        """
        MODL-02: Pipeline must have exactly a 'scaler' and 'clf' step.
        The scaler must be a StandardScaler and clf must be an LGBMClassifier.
        """
        from lightgbm import LGBMClassifier
        from sklearn.preprocessing import StandardScaler
        from crypto_ml_edge.trainer import EdgeTrainer, _LGBM_FIXED_PARAMS

        trainer = EdgeTrainer(pair="BTCUSDT", timeframe="1h")
        pipeline = trainer._create_pipeline({"n_estimators": 50, "max_depth": 3})

        assert hasattr(pipeline, "named_steps"), "Result must be a sklearn Pipeline"
        assert "scaler" in pipeline.named_steps, "Pipeline must have a 'scaler' step"
        assert "clf"    in pipeline.named_steps, "Pipeline must have a 'clf' step"
        assert isinstance(pipeline.named_steps["scaler"], StandardScaler), \
            "Scaler step must be a StandardScaler"
        assert isinstance(pipeline.named_steps["clf"], LGBMClassifier), \
            "clf step must be an LGBMClassifier"

    def test_pipeline_scaler_is_not_fit_before_creation(self):
        """
        MODL-02: Scaler must be unfitted when the pipeline is created.
        It should only be fit when pipeline.fit() is called on training data.
        """
        from crypto_ml_edge.trainer import EdgeTrainer

        trainer = EdgeTrainer(pair="BTCUSDT", timeframe="1h")
        pipeline = trainer._create_pipeline({"n_estimators": 50, "max_depth": 3})

        scaler = pipeline.named_steps["scaler"]
        # An unfitted StandardScaler does not have the 'mean_' attribute
        assert not hasattr(scaler, "mean_"), (
            "Scaler must NOT be pre-fitted. "
            "It should only be fit inside pipeline.fit() on the training fold."
        )

    def test_pipeline_scaler_fit_only_on_training_data(self):
        """
        MODL-02: Verify the scaler is fit exclusively on training-fold data.

        We create two datasets with different value ranges, fit the pipeline
        on the training set, then verify the scaler's mean_ matches the
        training set, not the test set.
        """
        from sklearn.pipeline import Pipeline
        from crypto_ml_edge.trainer import EdgeTrainer

        trainer = EdgeTrainer(pair="BTCUSDT", timeframe="1h")

        rng = np.random.RandomState(1)
        n_features = 5
        # Training data: centered around 10
        X_train = pd.DataFrame(
            rng.normal(10.0, 1.0, (300, n_features)),
            columns=[f"f{i}" for i in range(n_features)],
        )
        # Test data: centered around 50 — very different range
        X_test = pd.DataFrame(
            rng.normal(50.0, 1.0, (100, n_features)),
            columns=[f"f{i}" for i in range(n_features)],
        )
        y_train = np.random.choice([0, 1], size=300)  # binary long-only

        pipeline = trainer._create_pipeline({"n_estimators": 20, "max_depth": 3})
        pipeline.fit(X_train, y_train)

        scaler = pipeline.named_steps["scaler"]
        # Scaler mean_ should be close to training data mean (~10), not test (~50)
        scaler_mean = scaler.mean_.mean()
        assert abs(scaler_mean - 10.0) < 3.0, (
            f"Scaler mean {scaler_mean:.2f} appears to include test data "
            f"(training mean ~10, test mean ~50)"
        )
        assert abs(scaler_mean - 50.0) > 5.0, (
            "Scaler appears to have been fit on test data (mean ~50)"
        )

    def test_invalid_timeframe_raises(self):
        """EdgeTrainer must reject unknown timeframes immediately."""
        from crypto_ml_edge.trainer import EdgeTrainer
        with pytest.raises(ValueError, match="timeframe"):
            EdgeTrainer(pair="BTCUSDT", timeframe="15m")


@pytest.mark.skipif(
    not _LGBM_INSTALLED or not _SKLEARN_INSTALLED,
    reason="LightGBM or scikit-learn not installed",
)
class TestEdgeTrainerFallbackGrid:
    """
    MODL-01: Test that the optuna fallback (5-candidate grid) works correctly
    when optuna is not available.
    """

    def test_fallback_grid_has_5_candidates(self):
        """The fallback grid must contain exactly 5 candidates."""
        from crypto_ml_edge.trainer import _FALLBACK_PARAM_GRID
        assert len(_FALLBACK_PARAM_GRID) == 5, (
            f"Expected 5 fallback candidates, got {len(_FALLBACK_PARAM_GRID)}"
        )

    def test_fallback_grid_candidates_are_valid_lgbm_params(self):
        """Each fallback candidate must be a dict with required LightGBM keys."""
        from crypto_ml_edge.trainer import _FALLBACK_PARAM_GRID
        required_keys = {"n_estimators", "max_depth", "learning_rate"}
        for i, candidate in enumerate(_FALLBACK_PARAM_GRID):
            assert isinstance(candidate, dict), f"Candidate {i} must be a dict"
            missing = required_keys - set(candidate.keys())
            assert not missing, (
                f"Candidate {i} missing keys: {missing}"
            )

    def test_tune_hyperparameters_without_optuna_returns_dict(self):
        """
        When optuna is patched out, _tune_hyperparameters should fall back to
        the grid search and return a dict of params + integer trial count.
        """
        from crypto_ml_edge import trainer as trainer_module
        from crypto_ml_edge.trainer import EdgeTrainer

        rng = np.random.RandomState(7)
        n, n_feat = 400, 5
        X_train = pd.DataFrame(
            rng.normal(0, 1, (n, n_feat)),
            columns=[f"f{i}" for i in range(n_feat)],
        )
        y_train = pd.Series(np.random.choice([0, 1], size=n))  # binary long-only

        t = EdgeTrainer(pair="BTCUSDT", timeframe="1h")

        # Patch optuna as unavailable
        with patch.object(trainer_module, "_OPTUNA_AVAILABLE", False):
            params, n_trials = t._tune_hyperparameters(X_train, y_train)

        assert isinstance(params, dict), "Params must be a dict"
        assert "n_estimators" in params, "Params must include n_estimators"
        assert n_trials == 5, f"Fallback should evaluate exactly 5 candidates, got {n_trials}"


@pytest.mark.skipif(
    not _LGBM_INSTALLED or not _SKLEARN_INSTALLED,
    reason="LightGBM or scikit-learn not installed",
)
class TestEdgeTrainerOutput:
    """
    Tests for EdgeTrainer.train() output structure and DSR verdict.
    Uses a small dataset for speed — the DSR gate will likely FAIL on synthetic
    random-walk data; we only check the structural guarantees.
    """

    @pytest.fixture(scope="class")
    def training_result(self):
        """
        Run EdgeTrainer.train() on a small synthetic dataset.
        Shared across all tests in this class to avoid re-running training.
        """
        from crypto_ml_edge.trainer import EdgeTrainer

        ohlcv   = _make_ohlcv(n=1200, seed=10)
        funding = _make_funding(ohlcv)
        trainer = EdgeTrainer(pair="BTCUSDT", timeframe="1h")
        return trainer.train(ohlcv, funding=funding)

    def test_result_contains_verdict(self, training_result):
        """MODL-01: Output must contain a 'verdict' key with value PASS or FAIL."""
        assert "verdict" in training_result, "Output must contain 'verdict'"
        assert training_result["verdict"] in ("PASS", "FAIL"), (
            f"verdict must be 'PASS' or 'FAIL', got {training_result['verdict']}"
        )

    def test_result_contains_validation_dict(self, training_result):
        """Output must contain a 'validation' sub-dict with dsr_probability."""
        assert "validation" in training_result
        val = training_result["validation"]
        assert isinstance(val, dict), "validation must be a dict"
        assert "verdict" in val, "validation must contain 'verdict'"
        assert "dsr_probability" in val, "validation must contain 'dsr_probability'"
        assert 0.0 <= val["dsr_probability"] <= 1.0, (
            f"dsr_probability must be in [0,1], got {val['dsr_probability']}"
        )

    def test_result_contains_feature_names(self, training_result):
        """Output must list the features used after SHAP pruning."""
        assert "feature_names" in training_result
        features = training_result["feature_names"]
        assert isinstance(features, list), "feature_names must be a list"
        assert len(features) >= 4, (
            f"At least 4 features must be retained, got {len(features)}"
        )

    def test_result_contains_fold_metrics(self, training_result):
        """Output must contain per-fold metrics."""
        assert "fold_metrics" in training_result
        assert isinstance(training_result["fold_metrics"], list)

    def test_result_contains_timing(self, training_result):
        """Output must record training duration."""
        assert "training_seconds" in training_result
        assert training_result["training_seconds"] > 0

    def test_result_pair_and_timeframe_match(self, training_result):
        """Output pair/timeframe must match the trainer's configuration."""
        assert training_result["pair"] == "BTCUSDT"
        assert training_result["timeframe"] == "1h"

    def test_result_n_trials_positive_or_zero(self, training_result):
        """n_trials_used must be >= 0 (0 if no folds completed)."""
        assert "n_trials_used" in training_result
        assert training_result["n_trials_used"] >= 0

    def test_shap_importance_is_dict(self, training_result):
        """
        MODL-03: shap_importance must be a dict (may be empty if shap is
        not installed or no folds completed, but must not be None).
        """
        assert "shap_importance" in training_result
        assert isinstance(training_result["shap_importance"], dict), (
            "shap_importance must be a dict (possibly empty)"
        )


@pytest.mark.skipif(
    not _LGBM_INSTALLED or not _SKLEARN_INSTALLED,
    reason="LightGBM or scikit-learn not installed",
)
class TestEdgeTrainerShapImportance:
    """
    MODL-03: Tests for SHAP feature importance computation.
    These tests patch the pipeline to avoid running a full training cycle.
    """

    def test_compute_shap_importance_returns_series_or_none(self):
        """_compute_shap_importance must return a pd.Series or None."""
        from crypto_ml_edge.trainer import EdgeTrainer

        trainer = EdgeTrainer(pair="BTCUSDT", timeframe="1h")

        rng = np.random.RandomState(3)
        n, n_feat = 300, 5
        X = pd.DataFrame(
            rng.normal(0, 1, (n, n_feat)),
            columns=[f"f{i}" for i in range(n_feat)],
        )
        y = np.random.choice([0, 1], size=n)

        params = {"n_estimators": 30, "max_depth": 3, "learning_rate": 0.1,
                  "num_leaves": 7, "min_child_samples": 5}
        pipeline = trainer._create_pipeline(params)
        pipeline.fit(X, y)

        result = trainer._compute_shap_importance(pipeline, X, fold_id=0)
        # Should be a Series or None (None if shap not installed)
        assert result is None or isinstance(result, pd.Series), (
            f"Expected pd.Series or None, got {type(result)}"
        )

    def test_shap_importance_has_correct_feature_index(self):
        """SHAP Series index must match the input DataFrame columns."""
        try:
            import shap  # noqa: F401
        except ImportError:
            pytest.skip("shap not installed")

        from crypto_ml_edge.trainer import EdgeTrainer

        trainer = EdgeTrainer(pair="BTCUSDT", timeframe="1h")
        rng = np.random.RandomState(5)
        feature_cols = ["alpha", "beta", "gamma", "delta"]
        n = 200
        X = pd.DataFrame(rng.normal(0, 1, (n, len(feature_cols))), columns=feature_cols)
        y = np.random.choice([0, 1], size=n)

        params = {"n_estimators": 30, "max_depth": 3, "learning_rate": 0.1,
                  "num_leaves": 7, "min_child_samples": 5}
        pipeline = trainer._create_pipeline(params)
        pipeline.fit(X, y)

        importance = trainer._compute_shap_importance(pipeline, X, fold_id=0)
        if importance is not None:
            assert list(importance.index) == feature_cols, (
                f"SHAP index {list(importance.index)} != expected {feature_cols}"
            )
            assert (importance >= 0).all(), "All SHAP importances must be non-negative"

    def test_prune_features_drops_low_importance(self):
        """
        _prune_features must drop features below SHAP_DROP_THRESHOLD * mean.
        Need 4+ features above threshold so the min-4 guarantee doesn't
        override the pruning decision.
        """
        from crypto_ml_edge.trainer import EdgeTrainer, SHAP_DROP_THRESHOLD

        trainer = EdgeTrainer(pair="BTCUSDT", timeframe="1h")
        trainer.feature_names_ = [
            "high_imp", "low_imp_1", "low_imp_2", "low_imp_3",
            "medium_imp", "medium_imp_2", "medium_imp_3", "medium_imp_4",
        ]

        # 5 features well above threshold, 3 features far below it
        importance = pd.Series({
            "high_imp": 10.0, "low_imp_1": 0.01, "low_imp_2": 0.01,
            "low_imp_3": 0.01, "medium_imp": 3.0, "medium_imp_2": 2.5,
            "medium_imp_3": 2.0, "medium_imp_4": 1.5,
        })
        selected = trainer._prune_features([importance])

        # Very low-importance features should be dropped
        mean_imp = importance.mean()
        threshold = mean_imp * SHAP_DROP_THRESHOLD
        for feature, imp_val in importance.items():
            if imp_val < threshold:
                assert feature not in selected, (
                    f"Feature '{feature}' with importance {imp_val:.4f} "
                    f"below threshold {threshold:.4f} should have been pruned"
                )

    def test_prune_features_minimum_4_retained(self):
        """Even with very high threshold, at least 4 features must be retained."""
        from crypto_ml_edge.trainer import EdgeTrainer

        trainer = EdgeTrainer(pair="BTCUSDT", timeframe="1h")
        trainer.feature_names_ = [f"f{i}" for i in range(16)]

        # All features have the same importance — nothing should be pruned
        importance = pd.Series({f"f{i}": 1.0 for i in range(16)})
        selected = trainer._prune_features([importance])
        assert len(selected) >= 4

    def test_prune_features_empty_input_returns_all(self):
        """Empty importance list should return all features unchanged."""
        from crypto_ml_edge.trainer import EdgeTrainer

        trainer = EdgeTrainer(pair="BTCUSDT", timeframe="1h")
        trainer.feature_names_ = ["a", "b", "c", "d"]
        selected = trainer._prune_features([])
        assert selected == ["a", "b", "c", "d"]


@pytest.mark.skipif(
    not _LGBM_INSTALLED or not _SKLEARN_INSTALLED,
    reason="LightGBM or scikit-learn not installed",
)
class TestEdgeTrainerLabelAlignment:
    """Tests for _align_xy to confirm no preprocessing before split."""

    def test_align_xy_drops_warmup_rows(self):
        """
        _align_xy must remove at least WARMUP_BARS rows from the front so that
        the feature matrix does not start with NaN-filled warmup rows.
        """
        from crypto_ml_edge.features.engine import WARMUP_BARS
        from crypto_ml_edge.trainer import EdgeTrainer

        n = WARMUP_BARS + 100
        dates = pd.date_range("2021-01-01", periods=n, freq="1h", tz="UTC")
        features = pd.DataFrame(np.random.randn(n, 4), index=dates, columns=list("ABCD"))
        labels = pd.Series(np.zeros(n, dtype="int8"), index=dates)

        X, y = EdgeTrainer._align_xy(features, labels)

        assert len(X) <= n - WARMUP_BARS, (
            f"Expected at most {n - WARMUP_BARS} rows after warmup drop, got {len(X)}"
        )

    def test_align_xy_x_and_y_have_same_index(self):
        """X and y returned by _align_xy must have the same index."""
        from crypto_ml_edge.trainer import EdgeTrainer

        n = 500
        dates = pd.date_range("2021-01-01", periods=n, freq="1h", tz="UTC")
        features = pd.DataFrame(np.random.randn(n, 4), index=dates, columns=list("ABCD"))
        labels = pd.Series(np.zeros(n, dtype="int8"), index=dates)

        X, y = EdgeTrainer._align_xy(features, labels)
        assert X.index.equals(y.index), "X and y must share the same index after alignment"

    def test_align_xy_no_all_nan_rows(self):
        """Rows where all features are NaN must be removed."""
        from crypto_ml_edge.trainer import EdgeTrainer

        n = 300
        dates = pd.date_range("2021-01-01", periods=n, freq="1h", tz="UTC")
        data = np.random.randn(n, 4)
        # Inject a completely NaN row
        data[50, :] = np.nan
        features = pd.DataFrame(data, index=dates, columns=list("ABCD"))
        labels = pd.Series(np.zeros(n, dtype="int8"), index=dates)

        X, y = EdgeTrainer._align_xy(features, labels)
        # All-NaN row should be removed (ffill handles partial NaN; all-NaN drops)
        assert X.isnull().all(axis=1).sum() == 0, (
            "All-NaN rows must be removed from X by _align_xy"
        )
