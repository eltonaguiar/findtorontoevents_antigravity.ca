"""
Isotonic calibration wrapper for sklearn-compatible classifiers.

Tree ensembles (XGBoost, RF) produce poorly calibrated probabilities —
they tend to push predictions toward 0 and 1 without matching true
frequency. Isotonic regression learns a monotonic mapping from raw
model output to actual P(positive class) using a held-out temporal chunk.

Usage:
    # During training:
    wrapper = CalibratedModelWrapper(base_model)
    wrapper.fit_calibration(X_cal, y_cal)   # last 20% of training data
    wrapper.save(model_path, cal_path)

    # During inference:
    wrapper = CalibratedModelWrapper.load(model_path, cal_path)
    prob = wrapper.predict_proba(X)  # calibrated if cal model exists

References:
    - Niculescu-Mizil & Caruana (2005) — isotonic > Platt for trees
    - R021 Final Synthesis Report — recommends isotonic for XGBoost pipeline
"""
import os
import numpy as np
import joblib
from typing import Optional


class CalibratedModelWrapper:
    """
    Wraps any sklearn-compatible classifier with isotonic calibration.

    The base model's predict_proba output is passed through an isotonic
    regression fitted on held-out temporal data. Falls back to raw
    probabilities if no calibration model is available.
    """

    def __init__(self, base_model=None):
        self.base_model = base_model
        self.calibrator = None  # IsotonicRegression instance or None

    def fit_calibration(self, X_cal: np.ndarray, y_cal: np.ndarray, min_samples: int = 30) -> bool:
        """
        Fit isotonic calibration on a held-out temporal chunk.

        Args:
            X_cal: Feature matrix (already scaled) for calibration set.
            y_cal: Binary labels for calibration set.
            min_samples: Minimum samples required to fit calibration.

        Returns:
            True if calibration was fitted, False if insufficient data.
        """
        if self.base_model is None:
            raise ValueError("base_model must be set before fitting calibration")

        if len(X_cal) < min_samples:
            print(f"  Calibration skipped: {len(X_cal)} samples < {min_samples} minimum")
            self.calibrator = None
            return False

        # Get raw probabilities from the base model on the calibration set
        raw_proba = self.base_model.predict_proba(X_cal)[:, 1]

        # Fit isotonic regression: raw_proba -> actual labels
        from sklearn.isotonic import IsotonicRegression
        self.calibrator = IsotonicRegression(
            y_min=0.01,   # avoid exact 0/1 — keeps log-loss finite
            y_max=0.99,
            out_of_bounds="clip",
        )
        self.calibrator.fit(raw_proba, y_cal)

        # Report calibration effect
        cal_proba = self.calibrator.predict(raw_proba)
        print(f"  Calibration fitted on {len(X_cal)} samples")
        print(f"    Raw proba  — mean={raw_proba.mean():.3f}, std={raw_proba.std():.3f}")
        print(f"    Cal proba  — mean={cal_proba.mean():.3f}, std={cal_proba.std():.3f}")
        print(f"    Actual WR  — {y_cal.mean():.3f}")

        return True

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Predict calibrated probabilities.

        Returns ndarray of shape (n_samples, 2) matching sklearn convention.
        If calibration model exists, probabilities are isotonic-calibrated.
        Otherwise, returns raw model output.
        """
        if self.base_model is None:
            raise ValueError("No base model loaded")

        raw = self.base_model.predict_proba(X)

        if self.calibrator is not None:
            raw_positive = raw[:, 1]
            cal_positive = self.calibrator.predict(raw_positive)
            cal_positive = np.clip(cal_positive, 0.01, 0.99)
            return np.column_stack([1.0 - cal_positive, cal_positive])

        return raw

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict class labels (delegates to base model)."""
        return self.base_model.predict(X)

    @property
    def is_calibrated(self) -> bool:
        return self.calibrator is not None

    def save(self, model_path: str, calibration_path: Optional[str] = None):
        """
        Save base model and calibration model.

        Args:
            model_path: Path for the base model joblib file.
            calibration_path: Path for calibration model. If None,
                derived from model_path by appending '_calibration'.
        """
        if calibration_path is None:
            calibration_path = _default_cal_path(model_path)

        joblib.dump(self.base_model, model_path)

        if self.calibrator is not None:
            joblib.dump(self.calibrator, calibration_path)
        elif os.path.exists(calibration_path):
            # Remove stale calibration file if calibrator was reset
            os.remove(calibration_path)

    @classmethod
    def load(cls, model_path: str, calibration_path: Optional[str] = None) -> "CalibratedModelWrapper":
        """
        Load base model and calibration model (if it exists).

        Falls back gracefully to uncalibrated predictions if calibration
        file is missing or corrupt.
        """
        if calibration_path is None:
            calibration_path = _default_cal_path(model_path)

        wrapper = cls()
        wrapper.base_model = joblib.load(model_path)

        if os.path.exists(calibration_path):
            try:
                wrapper.calibrator = joblib.load(calibration_path)
            except Exception as e:
                print(f"  Warning: calibration model corrupt, using raw proba: {e}")
                wrapper.calibrator = None

        return wrapper


def _default_cal_path(model_path: str) -> str:
    """Derive calibration path from model path: filter_xgb.joblib -> filter_xgb_calibration.joblib"""
    base, ext = os.path.splitext(model_path)
    return f"{base}_calibration{ext}"
