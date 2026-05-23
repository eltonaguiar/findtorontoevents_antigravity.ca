"""
EdgeTrainer — Model Training Orchestrator
==========================================
Trains one LightGBM model per pair/timeframe combination using a rigorous
walk-forward protocol.

Requirements satisfied:
  MODL-01: LightGBM primary model; Optuna hyperparameter tuning inside
           training folds only (never touches test data). Fallback to a
           5-candidate grid when optuna is not installed.
  MODL-02: All preprocessing (StandardScaler) lives inside an sklearn
           Pipeline — the scaler is fit on the training fold and applied
           to the test fold; it is NEVER fit on the full dataset before
           splitting.
  MODL-03: SHAP-based feature importance computed via TreeExplainer;
           features below the importance threshold are dropped and the
           model is retrained on the reduced set.
  MODL-04: Runtime bounded for GitHub Actions CPU runners: Optuna
           n_trials=20, inner CV 3-fold, early stopping on LightGBM.

Academic anchors:
  - Lopez de Prado 2018: walk-forward CV, purge + embargo
  - Bailey & Lopez de Prado 2014: DSR gate (via validation.py)
  - Lundberg & Lee 2017: SHAP TreeExplainer for feature selection
"""

from __future__ import annotations

import json
import logging
import time
import warnings
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# Try optional imports — all are needed at runtime but gracefully flagged
import warnings as _warnings

try:
    from lightgbm import LGBMClassifier
    _LGBM_AVAILABLE = True
except ImportError:
    _LGBM_AVAILABLE = False
    LGBMClassifier = None  # type: ignore[assignment,misc]
    _warnings.warn(
        "LightGBM not available — falling back to RandomForest. "
        "Install with: pip install lightgbm",
        UserWarning,
        stacklevel=1,
    )

try:
    import shap
    _SHAP_AVAILABLE = True
except ImportError:
    _SHAP_AVAILABLE = False
    _warnings.warn(
        "SHAP not available — feature importance explanations disabled. "
        "Install with: pip install shap",
        UserWarning,
        stacklevel=1,
    )

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    _OPTUNA_AVAILABLE = True
except ImportError:
    _OPTUNA_AVAILABLE = False
    _warnings.warn(
        "Optuna not available — hyperparameter tuning disabled. "
        "Install with: pip install optuna",
        UserWarning,
        stacklevel=1,
    )

try:
    import joblib as _joblib
    _JOBLIB_AVAILABLE = True
except ImportError:
    _JOBLIB_AVAILABLE = False
    _warnings.warn(
        "joblib not available — model persistence disabled. "
        "Install with: pip install joblib",
        UserWarning,
        stacklevel=1,
    )

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score

try:
    from sklearn.isotonic import IsotonicRegression
    _CALIBRATION_AVAILABLE = True
except ImportError:
    _CALIBRATION_AVAILABLE = False

from crypto_ml_edge.config import (
    MODELS_DIR,
    TPSL_CONFIG,
    WALK_FORWARD_FOLDS,
    PURGE_GAP_BARS,
)
from crypto_ml_edge.features.engine import build_features, FEATURE_NAMES, WARMUP_BARS
from crypto_ml_edge.labeler import build_labels
from crypto_ml_edge.validation import WalkForwardSplit, validate_model

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

# SHAP importance: drop features whose mean |SHAP| is below this fraction of
# the mean importance across all features. e.g. 0.1 = drop anything below
# 10% of the average importance.
SHAP_DROP_THRESHOLD = 0.10

# Minimum class probability to take a trade.  A 3-class model often assigns
# With binary labels (29% class 1, 71% class 0), the model assigns
# >0.5 to class 0 on most bars.  Break-even precision for 3:2 TP/SL
# ratio is 40%, requiring high confidence before entering.
ENTRY_THRESHOLD = 0.70

# Optuna budget (MODL-04): keep total tuning fast for CI runners.
OPTUNA_N_TRIALS = 20

# Inner-fold CV folds for Optuna objective.
INNER_CV_FOLDS = 3

# LightGBM early stopping (reduces wasted compute).
EARLY_STOPPING_ROUNDS = 30

# Fallback grid when optuna is not installed (5 candidates as specified).
# Each dict is a complete set of LightGBM hyperparameters to try.
_FALLBACK_PARAM_GRID = [
    # Candidate 1: conservative / low complexity
    {
        "n_estimators": 200, "max_depth": 4, "num_leaves": 15,
        "learning_rate": 0.05, "min_child_samples": 30,
        "subsample": 0.8, "colsample_bytree": 0.8, "reg_lambda": 1.0,
    },
    # Candidate 2: moderate depth
    {
        "n_estimators": 300, "max_depth": 6, "num_leaves": 31,
        "learning_rate": 0.05, "min_child_samples": 20,
        "subsample": 0.8, "colsample_bytree": 0.8, "reg_lambda": 0.5,
    },
    # Candidate 3: shallow + high regularisation (good for noisy financial data)
    {
        "n_estimators": 500, "max_depth": 3, "num_leaves": 7,
        "learning_rate": 0.02, "min_child_samples": 50,
        "subsample": 0.7, "colsample_bytree": 0.7, "reg_lambda": 5.0,
    },
    # Candidate 4: faster / fewer estimators
    {
        "n_estimators": 150, "max_depth": 5, "num_leaves": 20,
        "learning_rate": 0.1, "min_child_samples": 25,
        "subsample": 0.9, "colsample_bytree": 0.9, "reg_lambda": 0.1,
    },
    # Candidate 5: deeper with more regularisation
    {
        "n_estimators": 400, "max_depth": 7, "num_leaves": 50,
        "learning_rate": 0.03, "min_child_samples": 40,
        "subsample": 0.75, "colsample_bytree": 0.75, "reg_lambda": 2.0,
    },
]

# Default LightGBM parameters that are always fixed (not tuned).
_LGBM_FIXED_PARAMS = {
    "objective": "binary",          # binary long-only: {0=no-trade, 1=long}
    "metric": "binary_logloss",
    "verbose": -1,
    "n_jobs": -1,
    "random_state": 42,
    "is_unbalance": True,           # counteract label imbalance (LABL-03 note)
}


# ─── Label remapping helpers ──────────────────────────────────────────────────
# Binary long-only: labeler produces {0, 1}. No remapping needed.

def _remap_labels(y: pd.Series) -> np.ndarray:
    """Binary labels {0, 1} — identity (no remapping needed)."""
    return y.astype(int).values


def _unmap_labels(y_pred: np.ndarray) -> np.ndarray:
    """Binary predictions {0, 1} — identity."""
    return y_pred.astype(int)


# ─── Calibration wrapper ─────────────────────────────────────────────────────

class _CalibratedWrapper:
    """Wraps a fitted classifier with an isotonic calibration mapping."""

    def __init__(self, base_clf, isotonic_reg):
        self.base_clf = base_clf
        self.isotonic_reg = isotonic_reg
        # Forward sklearn-required attributes
        self.classes_ = base_clf.classes_

    def predict_proba(self, X):
        raw = self.base_clf.predict_proba(X)
        cal_pos = self.isotonic_reg.transform(raw[:, 1])
        cal_neg = 1.0 - cal_pos
        return np.column_stack([cal_neg, cal_pos])

    def predict(self, X):
        proba = self.predict_proba(X)
        return self.classes_[np.argmax(proba, axis=1)]


# ─── Main trainer class ───────────────────────────────────────────────────────

class EdgeTrainer:
    """
    Trains one LightGBM model for one pair/timeframe combination.

    Usage:
        trainer = EdgeTrainer(pair="BTCUSDT", timeframe="1h")
        results = trainer.train(ohlcv_df, funding_df=funding_df)
        # results["verdict"] is "PASS" or "FAIL"
    """

    def __init__(self, pair: str, timeframe: str):
        if timeframe not in TPSL_CONFIG:
            raise ValueError(
                f"timeframe '{timeframe}' not in TPSL_CONFIG. "
                f"Valid: {list(TPSL_CONFIG.keys())}"
            )
        if not _LGBM_AVAILABLE:
            raise ImportError(
                "LightGBM is required: pip install lightgbm"
            )

        self.pair = pair
        self.timeframe = timeframe
        self._bars_per_year = (
            8760 if timeframe == "1h" else 2190
        )

        # Will be populated after training
        self.feature_names_: list[str] = list(FEATURE_NAMES)
        self.fold_metrics_: list[dict] = []

    # ── Public API ────────────────────────────────────────────────────────

    def train(
        self,
        ohlcv: pd.DataFrame,
        funding: Optional[pd.DataFrame] = None,
    ) -> dict:
        """
        Full training pipeline.

        Parameters
        ----------
        ohlcv:
            DataFrame with columns [open, high, low, close, volume] and a
            tz-aware DatetimeIndex.  Must have at least WARMUP_BARS + 500
            rows for meaningful training.
        funding:
            Optional funding-rate DataFrame aligned to the same index.

        Returns
        -------
        dict with keys:
            verdict:           "PASS" | "FAIL"
            pair:              Trading pair symbol
            timeframe:         Timeframe string
            feature_names:     Features used after SHAP pruning
            fold_metrics:      Per-fold OOS metrics list
            validation:        Full validate_model() output dict
            shap_importance:   Feature → mean |SHAP| (after pruning)
            model_path:        Absolute path of saved .joblib file
            sidecar_path:      Absolute path of saved _meta.json file
            n_trials_used:     Number of hyperparameter sets evaluated
            training_seconds:  Wall time for the full train() call
            n_folds:           Number of completed walk-forward folds
        """
        t0 = time.time()
        logger.info("EdgeTrainer.train: %s %s — start", self.pair, self.timeframe)

        # ── Step 1: Build features ──────────────────────────────────────
        features_df = build_features(ohlcv, funding_df=funding, timeframe=self.timeframe)

        # ── Step 2: Build labels ────────────────────────────────────────
        # ATR for the labeler: un-normalise from the percentage form stored
        # in features to an absolute ATR value.
        # atr_14 column = ATR / close (see engine.py).  Multiply back by close
        # to get absolute ATR needed by build_labels.
        atr_abs = features_df["atr_14"] * ohlcv["close"]

        labels = build_labels(
            close=ohlcv["close"],
            high=ohlcv["high"],
            low=ohlcv["low"],
            atr=atr_abs,
            timeframe=self.timeframe,
            pair=self.pair,
        )

        # Align: drop warmup rows and any rows where either X or y is NaN
        X_full, y_full = self._align_xy(features_df, labels)

        if len(X_full) < 600:
            return self._fail_result(
                "Insufficient samples after alignment: "
                f"{len(X_full)} (need >= 600)",
                t0,
            )

        # ── Step 3: Walk-forward split ──────────────────────────────────
        try:
            splitter = WalkForwardSplit(
                n_samples=len(X_full),
                timestamps=X_full.index,
            )
            logger.info(splitter.summary())
        except ValueError as e:
            return self._fail_result(str(e), t0)

        # ── Step 4: Per-fold training ───────────────────────────────────
        oos_returns: list[float] = []
        trades_count: int = 0
        all_shap_importance: list[pd.Series] = []
        best_params: Optional[dict] = None
        n_trials_used: int = 0

        for fold in splitter.folds:
            X_train = X_full.iloc[fold.train_start:fold.train_end]
            y_train = y_full.iloc[fold.train_start:fold.train_end]
            X_test  = X_full.iloc[fold.test_start:fold.test_end]
            y_test  = y_full.iloc[fold.test_start:fold.test_end]

            # Drop NaN labels from training (embargoed rows)
            mask_train = y_train.notna()
            X_train = X_train[mask_train]
            y_train = y_train[mask_train]

            if len(X_train) < 200 or len(X_test) < 50:
                logger.warning(
                    "Fold %d: skipping (train=%d, test=%d)",
                    fold.fold_id, len(X_train), len(X_test),
                )
                continue

            y_train_int = y_train.astype(int)
            y_test_int  = y_test.dropna().astype(int)
            X_test_clean = X_test.loc[y_test.dropna().index]

            # ── 4a: Optuna tuning (inside train fold only) ────────────
            params, n_trials = self._tune_hyperparameters(X_train, y_train_int)
            n_trials_used = max(n_trials_used, n_trials)
            if best_params is None:
                best_params = params

            # ── 4b: Build sklearn Pipeline — scaler INSIDE fold ───────
            pipeline = self._create_pipeline(params)
            pipeline.fit(X_train, _remap_labels(y_train_int))

            # ── 4c: OOS predictions ───────────────────────────────────
            proba = pipeline.predict_proba(X_test_clean)
            # Binary: class 0 = no-trade, class 1 = long
            long_prob  = proba[:, 1]
            short_prob = np.zeros_like(long_prob)  # no shorts in binary model

            # Take positions only when confidence exceeds ENTRY_THRESHOLD.
            fold_returns, fold_trades = self._compute_fold_returns(
                X_test_clean, y_test_int, long_prob, short_prob
            )
            oos_returns.extend(fold_returns)
            trades_count += fold_trades

            # ── 4d: SHAP importance ───────────────────────────────────
            shap_imp = self._compute_shap_importance(
                pipeline, X_train, fold.fold_id
            )
            if shap_imp is not None:
                all_shap_importance.append(shap_imp)

            # Per-fold metrics
            acc = float(np.mean(
                _unmap_labels(pipeline.predict(X_test_clean)) == y_test_int.values
            ))
            self.fold_metrics_.append({
                "fold_id": fold.fold_id,
                "n_train": len(X_train),
                "n_test": len(X_test_clean),
                "accuracy": round(acc, 4),
                "n_oos_bars": len(fold_returns),
            })

        if len(oos_returns) < 50:
            return self._fail_result(
                f"Too few OOS observations: {len(oos_returns)} (need >= 50)",
                t0,
            )

        # ── Step 5: SHAP feature pruning + retrain ──────────────────────
        selected_features = self._prune_features(all_shap_importance)
        shap_importance_final: dict = {}

        if selected_features and selected_features != list(X_full.columns):
            logger.info(
                "SHAP pruning: %d → %d features",
                len(X_full.columns), len(selected_features),
            )
            X_pruned = X_full[selected_features]
            self.feature_names_ = selected_features

            # Quick retrain on final selected features for the sidecar model
            best_params_final = best_params or _FALLBACK_PARAM_GRID[1]
            final_pipeline = self._create_pipeline(best_params_final)
            # Use last 70% of data as a full final train set
            cutoff = int(0.3 * len(X_pruned))
            final_pipeline.fit(
                X_pruned.iloc[cutoff:],
                _remap_labels(y_full.iloc[cutoff:].dropna().astype(int)),
            )

            # Calibrate probabilities using held-out early data
            cal_size = max(50, int(0.1 * cutoff))
            if cutoff >= 30:
                X_cal = X_pruned.iloc[:cal_size]
                y_cal = y_full.iloc[:cal_size].dropna().astype(int)
                if len(y_cal) >= 30:
                    final_pipeline = self._calibrate_model(
                        final_pipeline, X_cal, y_cal
                    )

            # Recompute SHAP on the pruned final model
            imp = self._compute_shap_importance(
                final_pipeline,
                X_pruned.iloc[cutoff:],
                fold_id=-1,
            )
            if imp is not None:
                shap_importance_final = imp.to_dict()
        else:
            self.feature_names_ = list(X_full.columns)
            # Build a final model on the last 70% for saving
            best_params_final = best_params or _FALLBACK_PARAM_GRID[1]
            final_pipeline = self._create_pipeline(best_params_final)
            cutoff = int(0.3 * len(X_full))
            final_pipeline.fit(
                X_full.iloc[cutoff:],
                _remap_labels(y_full.iloc[cutoff:].dropna().astype(int)),
            )

            # Calibrate probabilities using held-out early data
            cal_size = max(50, int(0.1 * cutoff))
            if cutoff >= 30:
                X_cal = X_full.iloc[:cal_size]
                y_cal = y_full.iloc[:cal_size].dropna().astype(int)
                if len(y_cal) >= 30:
                    final_pipeline = self._calibrate_model(
                        final_pipeline, X_cal, y_cal
                    )

        # ── Step 6: DSR gate ────────────────────────────────────────────
        oos_array = np.asarray(oos_returns, dtype=float)
        trades_per_year = (
            trades_count / (len(oos_array) / self._bars_per_year)
            if len(oos_array) > 0
            else 0.0
        )
        validation_result = validate_model(
            returns=oos_array,
            n_trials=n_trials_used,
            pair=self.pair,
            trades_per_year=trades_per_year,
            bars_per_year=self._bars_per_year,
        )

        # ── Step 7: Save artifacts ──────────────────────────────────────
        model_path, sidecar_path = self._save_artifacts(
            pipeline=final_pipeline,
            validation=validation_result,
            shap_importance=shap_importance_final,
            n_trials_used=n_trials_used,
        )

        elapsed = round(time.time() - t0, 1)
        logger.info(
            "EdgeTrainer.train: %s %s — %s in %.1fs (DSR=%.3f)",
            self.pair,
            self.timeframe,
            validation_result["verdict"],
            elapsed,
            validation_result["dsr_probability"],
        )

        return {
            "verdict": validation_result["verdict"],
            "pair": self.pair,
            "timeframe": self.timeframe,
            "feature_names": self.feature_names_,
            "fold_metrics": self.fold_metrics_,
            "validation": validation_result,
            "shap_importance": shap_importance_final,
            "model_path": str(model_path),
            "sidecar_path": str(sidecar_path),
            "n_trials_used": n_trials_used,
            "training_seconds": elapsed,
            "n_folds": len(self.fold_metrics_),
        }

    # ── Pipeline factory (MODL-02) ────────────────────────────────────────

    def _create_pipeline(self, params: dict) -> Pipeline:
        """
        Build a fresh sklearn Pipeline: StandardScaler → LGBMClassifier.

        The scaler is NOT pre-fit.  It will be fit by pipeline.fit() on the
        training fold's data only.  This ensures MODL-02: no preprocessing
        applied before the train/test split.

        Parameters
        ----------
        params:
            LightGBM hyperparameters (the tunable ones, not the fixed ones).
            Merged with _LGBM_FIXED_PARAMS before constructing the estimator.

        Returns
        -------
        Unfitted sklearn Pipeline.
        """
        merged = {**_LGBM_FIXED_PARAMS, **params}
        # Remove keys that are not valid LGBMClassifier constructor arguments
        # (n_estimators is valid but some grid entries use it directly).
        clf = LGBMClassifier(**merged)
        return Pipeline([
            ("scaler", StandardScaler()),
            ("clf", clf),
        ])

    # ── Probability calibration ─────────────────────────────────────────

    @staticmethod
    def _calibrate_model(pipeline: Pipeline, X_cal: pd.DataFrame, y_cal: pd.Series) -> Pipeline:
        """
        Apply isotonic probability calibration to the fitted pipeline.

        Gets raw probabilities from the fitted model, fits an IsotonicRegression
        mapping, and wraps the classifier so predict_proba() returns calibrated
        probabilities.
        """
        if not _CALIBRATION_AVAILABLE:
            logger.debug("Calibration unavailable (sklearn import failed)")
            return pipeline

        try:
            clf = pipeline.named_steps["clf"]
            scaler = pipeline.named_steps["scaler"]

            # Get raw probabilities on calibration set
            X_cal_scaled = scaler.transform(X_cal)
            raw_proba = clf.predict_proba(X_cal_scaled)[:, 1]

            # Fit isotonic regression: raw_prob → calibrated_prob
            ir = IsotonicRegression(out_of_bounds="clip")
            ir.fit(raw_proba, y_cal.values.astype(float))

            # Wrap the classifier to apply calibration at inference
            calibrated_clf = _CalibratedWrapper(clf, ir)

            # Rebuild pipeline with calibrated classifier
            cal_pipeline = Pipeline([
                ("scaler", scaler),
                ("clf", calibrated_clf),
            ])
            logger.info("Probability calibration applied (isotonic)")
            return cal_pipeline

        except Exception as exc:
            logger.warning("Calibration failed: %s — using uncalibrated model", exc)
            return pipeline

    # ── Hyperparameter tuning (MODL-01) ──────────────────────────────────

    def _optuna_objective(
        self,
        trial: "optuna.Trial",
        X_train: pd.DataFrame,
        y_train: pd.Series,
    ) -> float:
        """
        Optuna objective: inner 3-fold time-series CV on training data only.

        All CV is performed using only training-fold data — the outer test fold
        is never seen here.  This implements the inner loop of nested CV as
        described in Lopez de Prado 2018, ch. 12.

        Returns the mean log-loss (lower = better); Optuna minimises by default.
        """
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 100, 600),
            "max_depth": trial.suggest_int("max_depth", 3, 8),
            "num_leaves": trial.suggest_int("num_leaves", 8, 64),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.15, log=True),
            "min_child_samples": trial.suggest_int("min_child_samples", 10, 60),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "reg_lambda": trial.suggest_float("reg_lambda", 0.01, 10.0, log=True),
        }
        pipeline = self._create_pipeline(params)

        y_remapped = _remap_labels(y_train)

        # TimeSeriesSplit for the inner CV (preserves temporal order).
        from sklearn.model_selection import TimeSeriesSplit
        tscv = TimeSeriesSplit(n_splits=INNER_CV_FOLDS)

        scores = cross_val_score(
            pipeline, X_train, y_remapped,
            cv=tscv,
            scoring="neg_log_loss",
            n_jobs=1,  # Keep single-threaded inside Optuna workers
        )
        return float(-scores.mean())  # Return positive loss (minimise)

    def _tune_hyperparameters(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
    ) -> tuple[dict, int]:
        """
        Tune hyperparameters using Optuna if available, otherwise grid search.

        Parameters
        ----------
        X_train, y_train: Training fold data (already sliced, no test leakage).

        Returns
        -------
        (best_params, n_trials_evaluated)
        """
        if _OPTUNA_AVAILABLE:
            study = optuna.create_study(
                direction="minimize",
                sampler=optuna.samplers.TPESampler(seed=42),
            )
            study.optimize(
                lambda trial: self._optuna_objective(trial, X_train, y_train),
                n_trials=OPTUNA_N_TRIALS,
                show_progress_bar=False,
            )
            return study.best_params, len(study.trials)

        # ── Fallback: 5-candidate grid ────────────────────────────────
        from sklearn.model_selection import TimeSeriesSplit
        tscv = TimeSeriesSplit(n_splits=INNER_CV_FOLDS)
        y_remapped = _remap_labels(y_train)

        best_params = _FALLBACK_PARAM_GRID[0]
        best_score = float("inf")

        for candidate in _FALLBACK_PARAM_GRID:
            pipeline = self._create_pipeline(candidate)
            scores = cross_val_score(
                pipeline, X_train, y_remapped,
                cv=tscv,
                scoring="neg_log_loss",
                n_jobs=1,
            )
            loss = float(-scores.mean())
            if loss < best_score:
                best_score = loss
                best_params = candidate

        return best_params, len(_FALLBACK_PARAM_GRID)

    # ── SHAP feature importance (MODL-03) ────────────────────────────────

    def _compute_shap_importance(
        self,
        pipeline: Pipeline,
        X: pd.DataFrame,
        fold_id: int,
    ) -> Optional[pd.Series]:
        """
        Compute SHAP feature importance using TreeExplainer.

        Uses the LightGBM model extracted from the Pipeline's 'clf' step.
        The scaler is NOT applied to X here — TreeExplainer works on the
        raw (unscaled) feature space to produce interpretable importances.
        However, since the model was trained on scaled data, we must pass
        the scaled X.  We transform via the pipeline's scaler step to get
        the same representation the model saw during training.

        Returns
        -------
        pd.Series with feature names as index and mean |SHAP| as values,
        or None if SHAP is unavailable or an error occurs.
        """
        if not _SHAP_AVAILABLE:
            logger.debug("SHAP not available; skipping importance for fold %d", fold_id)
            return None

        try:
            clf = pipeline.named_steps["clf"]

            # Use RAW (unscaled) features for SHAP on tree-based models.
            # Trees are invariant to monotonic scaling, so SHAP values are
            # mathematically identical whether computed on scaled or raw data.
            # Using raw features keeps SHAP magnitudes interpretable
            # (e.g., "RSI shifted prediction by +0.03" vs opaque scaled units).
            X_raw = X.values if hasattr(X, 'values') else X

            # Sub-sample for speed on large folds (max 2000 rows for SHAP).
            if len(X_raw) > 2000:
                idx = np.random.RandomState(42).choice(
                    len(X_raw), size=2000, replace=False
                )
                X_raw_sample = X_raw[idx]
            else:
                X_raw_sample = X_raw

            explainer = shap.TreeExplainer(clf)
            shap_values = explainer.shap_values(X_raw_sample)

            # Handle both SHAP API formats:
            #   Old (<0.50): list of 2D arrays, one per class
            #   New (>=0.50): single 3D ndarray (samples, features, classes)
            if isinstance(shap_values, list):
                # Old format: list of (n_samples, n_features) arrays
                mean_abs_shap = np.mean(
                    [np.abs(sv).mean(axis=0) for sv in shap_values],
                    axis=0,
                )
            elif shap_values.ndim == 3:
                # New format: (n_samples, n_features, n_classes) ndarray
                # Average absolute SHAP across samples, then across classes
                mean_abs_shap = np.abs(shap_values).mean(axis=0).mean(axis=1)
            else:
                # 2D format (binary or single-output)
                mean_abs_shap = np.abs(shap_values).mean(axis=0)

            feature_names = X.columns.tolist()
            return pd.Series(mean_abs_shap, index=feature_names, name=f"fold_{fold_id}")

        except Exception as exc:
            logger.warning("SHAP computation failed for fold %d: %s", fold_id, exc)
            return None

    # ── Feature pruning ───────────────────────────────────────────────────

    def _prune_features(
        self,
        importance_list: list[pd.Series],
    ) -> list[str]:
        """
        Aggregate per-fold SHAP importances and drop low-importance features.

        Features with mean |SHAP| below SHAP_DROP_THRESHOLD * mean(all features)
        are dropped.  Minimum 4 features are always retained.

        Parameters
        ----------
        importance_list: List of per-fold SHAP Series (may be empty).

        Returns
        -------
        List of selected feature names (subset of self.feature_names_).
        If importance_list is empty, returns the full feature list unchanged.
        """
        if not importance_list:
            return list(self.feature_names_)

        # Aggregate: align on feature names, fill missing with 0, mean.
        combined = pd.concat(importance_list, axis=1).fillna(0.0)
        avg_importance = combined.mean(axis=1).sort_values(ascending=False)

        threshold = avg_importance.mean() * SHAP_DROP_THRESHOLD
        selected = avg_importance[avg_importance >= threshold].index.tolist()

        # Always keep at least 4 features to avoid degenerate models.
        if len(selected) < 4:
            selected = avg_importance.nlargest(4).index.tolist()

        return selected

    # ── OOS return computation ─────────────────────────────────────────────

    def _compute_fold_returns(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        long_prob: np.ndarray,
        short_prob: np.ndarray,
        entry_threshold: float = ENTRY_THRESHOLD,
    ) -> tuple[np.ndarray, int]:
        """
        Compute simplified per-bar OOS returns for DSR calculation.

        A position is taken when:
          - long_prob > entry_threshold → +1 (long signal)
          - short_prob > entry_threshold → -1 (short signal)
          - otherwise → 0 (no trade)

        The "return" for a bar is: signal * actual_label.
        This is a simplified proxy — the labeler's triple-barrier labels
        already encode whether the trade would have been profitable (+1/-1/0).

        Trade counting: only counts NEW entries (signal changes from 0 → ±1
        or from +1 → -1), not every bar spent in a position.  This gives a
        realistic trades_per_year estimate for the cost model.

        Parameters
        ----------
        X_test:          Test-fold features (not used directly; needed for length).
        y_test:          Actual labels {-1, 0, 1}.
        long_prob:       Model probability for class +1 (long).
        short_prob:      Model probability for class -1 (short).
        entry_threshold: Probability above which a signal is taken.

        Returns
        -------
        (returns_array, n_new_trades)
            returns_array: per-bar returns (decimal; 0 for no-trade bars)
            n_new_trades:  count of new trade entries (position changes)
        """
        # Binary long-only: only take long positions when confidence exceeds threshold
        signals = np.zeros(len(long_prob))
        signals[long_prob > entry_threshold] = 1.0

        # Count NEW entries only: when signal changes from 0→1.
        signal_diff = np.diff(signals, prepend=0.0)
        n_new_trades = int(np.sum(signal_diff > 0))  # only 0→1 transitions
        n_new_trades = max(n_new_trades, 0)

        y_arr = y_test.values.astype(float)
        # Return proxy using actual TP/SL ratio from config.
        # TP hit (label=1): gain tp_mult * ATR → proxy +tp_mult * 0.01
        # SL/timeout (label=0): lose sl_mult * ATR → proxy -sl_mult * 0.01
        # This correctly reflects the asymmetric payoff (e.g. 3:2 for 1h).
        tp_mult = TPSL_CONFIG[self.timeframe]["tp_atr_mult"]
        sl_mult = TPSL_CONFIG[self.timeframe]["sl_atr_mult"]
        returns = np.where(
            signals > 0,
            np.where(y_arr == 1, tp_mult * 0.01, -sl_mult * 0.01),
            0.0,
        )
        return returns, n_new_trades

    # ── Alignment helper ───────────────────────────────────────────────────

    @staticmethod
    def _align_xy(
        features_df: pd.DataFrame,
        labels: pd.Series,
    ) -> tuple[pd.DataFrame, pd.Series]:
        """
        Align features and labels, dropping warmup rows and NaN features.

        The warmup slice (WARMUP_BARS) is removed from the front.  Any rows
        where ALL feature values are NaN are also dropped.  Labels retain
        NaN (embargoed rows) — the training loop handles them.

        Returns
        -------
        (X, y) with matching indices.
        """
        X = features_df.iloc[WARMUP_BARS:].copy()
        y = labels.iloc[WARMUP_BARS:].copy()

        # Align on the common index
        common_idx = X.index.intersection(y.index)
        X = X.loc[common_idx]
        y = y.loc[common_idx]

        # Drop rows where ALL features are NaN (data gaps)
        valid_rows = X.notna().any(axis=1)
        X = X[valid_rows]
        y = y[valid_rows]

        # Forward-fill remaining NaNs in features (rare; avoids sklearn errors)
        X = X.ffill().fillna(0.0)

        return X, y

    # ── Artifact persistence ───────────────────────────────────────────────

    def _save_artifacts(
        self,
        pipeline: Pipeline,
        validation: dict,
        shap_importance: dict,
        n_trials_used: int,
    ) -> tuple[Path, Path]:
        """
        Persist the final pipeline and a JSON sidecar to MODELS_DIR.

        File naming convention:
            {pair}_{timeframe}_edge.joblib
            {pair}_{timeframe}_edge_meta.json

        The sidecar contains all metadata needed to reproduce or audit the
        model: feature names, validation metrics, SHAP importances, and
        training configuration.

        Returns
        -------
        (model_path, sidecar_path)
        """
        slug = f"{self.pair}_{self.timeframe}_edge"
        model_path   = MODELS_DIR / f"{slug}.joblib"
        sidecar_path = MODELS_DIR / f"{slug}_meta.json"

        # Save pipeline
        if _JOBLIB_AVAILABLE:
            import joblib
            joblib.dump(pipeline, model_path)
        else:
            import pickle
            with open(model_path, "wb") as f:
                pickle.dump(pipeline, f)

        # Save JSON sidecar
        sidecar = {
            "pair": self.pair,
            "timeframe": self.timeframe,
            "feature_names": self.feature_names_,
            "n_features": len(self.feature_names_),
            "n_trials_used": n_trials_used,
            "optuna_available": _OPTUNA_AVAILABLE,
            "shap_available": _SHAP_AVAILABLE,
            "validation": validation,
            "shap_importance": shap_importance,
            "fold_metrics": self.fold_metrics_,
        }
        with open(sidecar_path, "w") as f:
            json.dump(sidecar, f, indent=2, default=str)

        logger.info("Saved model: %s", model_path)
        logger.info("Saved sidecar: %s", sidecar_path)

        return model_path, sidecar_path

    # ── Failure helper ────────────────────────────────────────────────────

    def _fail_result(self, reason: str, t0: float) -> dict:
        """Return a standardised FAIL result dict with a single reason."""
        logger.warning("EdgeTrainer FAIL: %s %s — %s", self.pair, self.timeframe, reason)
        return {
            "verdict": "FAIL",
            "pair": self.pair,
            "timeframe": self.timeframe,
            "feature_names": self.feature_names_,
            "fold_metrics": self.fold_metrics_,
            "validation": {
                "verdict": "FAIL",
                "fail_reasons": [reason],
                "dsr_probability": 0.0,
                "gross_sharpe": 0.0,
                "net_sharpe": 0.0,
            },
            "shap_importance": {},
            "model_path": "",
            "sidecar_path": "",
            "n_trials_used": 0,
            "training_seconds": round(time.time() - t0, 1),
            "n_folds": 0,
        }
