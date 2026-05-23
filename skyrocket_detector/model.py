"""
Skyrocket Detector Model
=========================
LightGBM binary classifier with sklearn GradientBoosting fallback.
Handles class imbalance, walk-forward validation, and model persistence.
"""

from __future__ import annotations

import os
import numpy as np
import pandas as pd
from typing import Optional

# Try LightGBM first, fall back to sklearn
_USE_LIGHTGBM = False
try:
    import lightgbm as lgb
    _USE_LIGHTGBM = True
    print("[model] Using LightGBM backend")
except ImportError:
    print("[model] LightGBM not available, using sklearn GradientBoostingClassifier")

from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score


class SkyrocketModel:
    """Binary classifier for skyrocket detection."""

    def __init__(self):
        self.model = None
        self.feature_names: list[str] = []
        self.is_trained = False
        self._use_lgbm = _USE_LIGHTGBM

    def train(self, X: pd.DataFrame, y: pd.Series, verbose: bool = True) -> dict:
        """
        Train the model with class imbalance handling.

        Args:
            X: Feature DataFrame (n_samples, n_features)
            y: Binary labels (0 or 1)
            verbose: Print training progress

        Returns:
            Dict with training metrics (accuracy, class balance info)
        """
        self.feature_names = list(X.columns)

        # Drop rows with NaN in features or labels
        mask = ~(X.isna().any(axis=1) | y.isna())
        X_clean = X[mask].values
        y_clean = y[mask].values.astype(int)

        n_pos = int(y_clean.sum())
        n_neg = int(len(y_clean) - n_pos)

        if n_pos == 0:
            print("[model] ERROR: No positive labels found. Cannot train.")
            return {"error": "no_positive_labels"}

        scale_pos_weight = n_neg / n_pos if n_pos > 0 else 1.0

        if verbose:
            print(f"[model] Training samples: {len(y_clean)} ({n_pos} pos, {n_neg} neg)")
            print(f"[model] Class imbalance ratio: 1:{scale_pos_weight:.1f}")
            print(f"[model] Backend: {'LightGBM' if self._use_lgbm else 'sklearn GBM'}")

        if self._use_lgbm:
            self.model = lgb.LGBMClassifier(
                max_depth=5,
                learning_rate=0.05,
                n_estimators=300,
                num_leaves=31,
                min_child_samples=20,
                subsample=0.8,
                scale_pos_weight=scale_pos_weight,
                random_state=42,
                verbose=-1,
            )
            self.model.fit(X_clean, y_clean)
        else:
            # sklearn fallback with similar hyperparameters
            # GBC uses sample_weight instead of scale_pos_weight
            self.model = GradientBoostingClassifier(
                max_depth=5,
                learning_rate=0.05,
                n_estimators=300,
                max_leaf_nodes=31,
                min_samples_leaf=20,
                subsample=0.8,
                random_state=42,
            )
            # Create sample weights for class imbalance
            sample_weights = np.where(y_clean == 1, scale_pos_weight, 1.0)
            self.model.fit(X_clean, y_clean, sample_weight=sample_weights)

        self.is_trained = True

        # Training accuracy
        train_preds = self.model.predict(X_clean)
        train_proba = self.predict_proba(pd.DataFrame(X_clean, columns=self.feature_names))
        train_acc = np.mean(train_preds == y_clean)
        train_precision = precision_score(y_clean, train_preds, zero_division=0)
        train_recall = recall_score(y_clean, train_preds, zero_division=0)

        metrics = {
            "train_samples": len(y_clean),
            "n_positive": n_pos,
            "n_negative": n_neg,
            "scale_pos_weight": scale_pos_weight,
            "train_accuracy": float(train_acc),
            "train_precision": float(train_precision),
            "train_recall": float(train_recall),
        }

        if verbose:
            print(f"[model] Train accuracy: {train_acc:.3f}")
            print(f"[model] Train precision: {train_precision:.3f}")
            print(f"[model] Train recall: {train_recall:.3f}")

        return metrics

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict probability of skyrocket.

        Args:
            X: Feature DataFrame or numpy array

        Returns:
            Array of probabilities (probability of class 1)
        """
        if not self.is_trained or self.model is None:
            raise RuntimeError("Model not trained. Call train() first.")

        if isinstance(X, pd.DataFrame):
            X_arr = X.values
        else:
            X_arr = np.asarray(X)

        # Handle NaN by replacing with 0
        X_arr = np.nan_to_num(X_arr, nan=0.0)

        probas = self.model.predict_proba(X_arr)
        return probas[:, 1]  # probability of positive class

    def predict(self, X: pd.DataFrame, threshold: float = 0.5) -> np.ndarray:
        """Predict binary class with adjustable threshold."""
        probas = self.predict_proba(X)
        return (probas >= threshold).astype(int)

    def save(self, path: str):
        """Save model to disk using joblib."""
        import joblib

        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        data = {
            "model": self.model,
            "feature_names": self.feature_names,
            "is_trained": self.is_trained,
            "use_lgbm": self._use_lgbm,
        }
        joblib.dump(data, path)
        print(f"[model] Saved to {path}")

    def load(self, path: str):
        """Load model from disk."""
        import joblib

        if not os.path.exists(path):
            raise FileNotFoundError(f"Model file not found: {path}")

        data = joblib.load(path)
        self.model = data["model"]
        self.feature_names = data["feature_names"]
        self.is_trained = data["is_trained"]
        self._use_lgbm = data.get("use_lgbm", False)
        print(f"[model] Loaded from {path} ({'LightGBM' if self._use_lgbm else 'sklearn GBM'})")

    def feature_importance(self) -> dict:
        """
        Return sorted feature importance dict.

        Returns:
            Dict of {feature_name: importance} sorted by importance descending.
        """
        if not self.is_trained or self.model is None:
            return {}

        if self._use_lgbm:
            importances = self.model.feature_importances_
        else:
            importances = self.model.feature_importances_

        imp_dict = {}
        for name, imp in zip(self.feature_names, importances):
            imp_dict[name] = float(imp)

        # Sort by importance descending
        return dict(sorted(imp_dict.items(), key=lambda x: x[1], reverse=True))

    def walk_forward_validate(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        n_splits: int = 5,
        purge_gap: int = 24,
        verbose: bool = True,
    ) -> dict:
        """
        Time-series walk-forward validation.

        Each fold trains on the first N% and tests on the next chunk.
        A purge gap of `purge_gap` bars is placed between train and test
        to prevent label leakage.

        Args:
            X: Feature DataFrame
            y: Binary labels
            n_splits: Number of folds
            purge_gap: Number of bars to skip between train/test
            verbose: Print per-fold metrics

        Returns:
            Dict with per-fold and average metrics:
              precision, recall, f1, auc (per fold + average)
        """
        # Clean data
        mask = ~(X.isna().any(axis=1) | y.isna())
        X_clean = X[mask].reset_index(drop=True)
        y_clean = y[mask].reset_index(drop=True)
        n = len(X_clean)

        if n < 200:
            print(f"[model] WARNING: Only {n} clean samples, walk-forward may be unreliable")

        fold_results = []
        # Each fold uses an expanding training window
        test_size = n // (n_splits + 1)

        if verbose:
            print(f"[model] Walk-forward validation: {n_splits} splits, {n} samples, test_size={test_size}")

        for fold in range(n_splits):
            train_end = test_size * (fold + 1)
            test_start = train_end + purge_gap
            test_end = test_start + test_size

            if test_end > n:
                test_end = n
            if test_start >= n:
                break

            X_train = X_clean.iloc[:train_end]
            y_train = y_clean.iloc[:train_end]
            X_test = X_clean.iloc[test_start:test_end]
            y_test = y_clean.iloc[test_start:test_end]

            if len(y_test) == 0 or y_train.sum() == 0:
                continue

            # Train a fresh model for this fold
            fold_model = SkyrocketModel()
            fold_model.train(X_train, y_train, verbose=False)

            # Predict
            y_pred = fold_model.predict(X_test)
            y_proba = fold_model.predict_proba(X_test)

            # Metrics
            prec = precision_score(y_test, y_pred, zero_division=0)
            rec = recall_score(y_test, y_pred, zero_division=0)
            f1 = f1_score(y_test, y_pred, zero_division=0)

            try:
                auc = roc_auc_score(y_test, y_proba)
            except ValueError:
                auc = 0.0  # only one class in test set

            fold_result = {
                "fold": fold + 1,
                "train_size": len(y_train),
                "test_size": len(y_test),
                "test_pos": int(y_test.sum()),
                "precision": float(prec),
                "recall": float(rec),
                "f1": float(f1),
                "auc": float(auc),
            }
            fold_results.append(fold_result)

            if verbose:
                print(
                    f"[model] Fold {fold + 1}: "
                    f"train={len(y_train)} test={len(y_test)} "
                    f"prec={prec:.3f} rec={rec:.3f} f1={f1:.3f} auc={auc:.3f}"
                )

        if not fold_results:
            return {"error": "no_valid_folds", "folds": []}

        # Compute averages
        avg_metrics = {
            "avg_precision": float(np.mean([f["precision"] for f in fold_results])),
            "avg_recall": float(np.mean([f["recall"] for f in fold_results])),
            "avg_f1": float(np.mean([f["f1"] for f in fold_results])),
            "avg_auc": float(np.mean([f["auc"] for f in fold_results])),
            "n_folds": len(fold_results),
            "folds": fold_results,
        }

        if verbose:
            print(
                f"[model] AVERAGE: "
                f"prec={avg_metrics['avg_precision']:.3f} "
                f"rec={avg_metrics['avg_recall']:.3f} "
                f"f1={avg_metrics['avg_f1']:.3f} "
                f"auc={avg_metrics['avg_auc']:.3f}"
            )

        return avg_metrics
