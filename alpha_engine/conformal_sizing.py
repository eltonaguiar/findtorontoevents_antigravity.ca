"""Conformal Prediction for calibrated position sizing.

Wraps existing XGBoost predictions to produce uncertainty intervals.
Position size scales inversely with interval width.
No retraining needed -- just collect recent prediction residuals.

Reference: ICLR 2024. Tested on 4000+ crypto assets.
"""
import json
import os

import numpy as np
from pathlib import Path


class ConformalSizer:
    """Split conformal prediction for position sizing.

    Maintains a rolling calibration set of |actual - predicted| residuals.
    The conformal quantile defines an interval width; narrower intervals
    mean higher confidence, which maps to a larger position multiplier.
    """

    def __init__(self, coverage=0.90, min_calibration=50):
        """
        Args:
            coverage: Target coverage probability (0.90 = 90% of outcomes
                      should fall within the predicted interval).
            min_calibration: Minimum residuals needed before producing
                             calibrated intervals.  Returns max-uncertainty
                             (width=1.0) when below this threshold.
        """
        self.coverage = coverage
        self.min_calibration = min_calibration
        self.residuals: list[float] = []
        self._state_file = Path(__file__).parent / "data" / "conformal_state.json"
        self._load_state()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_state(self) -> None:
        """Load calibration residuals from disk."""
        if self._state_file.exists():
            try:
                with open(self._state_file, encoding="utf-8") as f:
                    state = json.load(f)
                    self.residuals = state.get("residuals", [])
            except (json.JSONDecodeError, OSError):
                self.residuals = []

    def _save_state(self) -> None:
        """Persist calibration residuals (rolling window of 500)."""
        os.makedirs(self._state_file.parent, exist_ok=True)
        with open(self._state_file, "w", encoding="utf-8") as f:
            json.dump({"residuals": self.residuals[-500:]}, f)

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------

    def update(self, predicted_prob: float, actual_outcome: float) -> None:
        """Add a new calibration point.  Call when a pick closes.

        Args:
            predicted_prob: ML score at entry time (0-1).
            actual_outcome: 1.0 if the trade was a win, 0.0 if a loss.
        """
        residual = abs(actual_outcome - predicted_prob)
        self.residuals.append(residual)
        if len(self.residuals) > 500:
            self.residuals = self.residuals[-500:]
        self._save_state()

    @property
    def calibrated(self) -> bool:
        """True when enough residuals have been collected."""
        return len(self.residuals) >= self.min_calibration

    # ------------------------------------------------------------------
    # Interval & sizing
    # ------------------------------------------------------------------

    def get_interval_width(self, predicted_prob: float) -> float:
        """Get prediction interval width for a given prediction.

        Narrower = more confident = should size up.

        Returns:
            Width in [0, 2].  Returns 1.0 (max uncertainty) when
            the calibration set is too small.
        """
        if not self.calibrated:
            return 1.0  # max uncertainty when uncalibrated

        sorted_res = sorted(self.residuals)
        quantile_idx = int(np.ceil(self.coverage * len(sorted_res))) - 1
        quantile_idx = min(quantile_idx, len(sorted_res) - 1)
        return sorted_res[quantile_idx] * 2  # symmetric interval

    def size_multiplier(self, predicted_prob: float) -> float:
        """Position size multiplier based on conformal interval.

        Returns:
            Multiplier in [0.5, 2.0].
            - Width ~0.2 (very confident) -> 2.0x
            - Width ~1.0 (very uncertain) -> 0.5x
        """
        width = self.get_interval_width(predicted_prob)
        if width <= 0:
            return 1.0
        # Narrow interval -> bigger position, wide -> smaller
        multiplier = max(0.5, min(2.0, 0.4 / max(width, 0.2)))
        return round(multiplier, 3)

    def get_diagnostics(self, predicted_prob: float) -> dict:
        """Return a diagnostic dict suitable for logging / signal enrichment."""
        width = self.get_interval_width(predicted_prob)
        mult = self.size_multiplier(predicted_prob)
        return {
            "conformal_width": round(width, 4),
            "conformal_multiplier": mult,
            "conformal_calibrated": self.calibrated,
            "conformal_residuals_n": len(self.residuals),
            "conformal_coverage": self.coverage,
        }
