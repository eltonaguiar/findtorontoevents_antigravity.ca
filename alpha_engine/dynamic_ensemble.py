"""
ALPHA_ENGINE -- Dynamic Ensemble Weighting
===========================================================================
Replaces fixed 50/25/25 ensemble blending with performance-adaptive weights.

Key features:
  1. Per-model accuracy tracking over a rolling 50-trade window
  2. Softmax weighting: w_i = exp(acc_i * T) / sum(exp(acc_j * T)), T=5.0
  3. Regime-conditional weights (BULL / BEAR / CHOPPY separate weight sets)
  4. Minimum weight floor of 10% (prevents complete model exclusion)
  5. Persistence to data/ensemble_weights.json
  6. Weekly rebalancing entry point for retrain workflows

Usage from ml_ranker.py:
    from dynamic_ensemble import DynamicEnsemble
    ensemble = DynamicEnsemble()
    weights = ensemble.get_weights(regime="bull")
    # weights = {"primary": 0.45, "rf": 0.30, "catboost": 0.25}
"""

from __future__ import annotations

import json
import math
import os
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_DEFAULT_TEMPERATURE = 5.0
_ROLLING_WINDOW = 50
_MIN_WEIGHT = 0.10          # 10% floor per model
_MODEL_NAMES = ("primary", "rf", "catboost")
_REGIMES = ("BULL", "BEAR", "CHOPPY")

# Resolve data directory relative to this file (same as config.DATA_DIR)
_THIS_DIR = Path(__file__).resolve().parent
_DATA_DIR = _THIS_DIR / "data"
_WEIGHTS_PATH = _DATA_DIR / "ensemble_weights.json"

# Default fixed weights (backwards-compatible fallback)
_FIXED_WEIGHTS = {"primary": 0.50, "rf": 0.25, "catboost": 0.25}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _softmax_weights(
    accuracies: dict[str, float],
    temperature: float = _DEFAULT_TEMPERATURE,
    min_weight: float = _MIN_WEIGHT,
) -> dict[str, float]:
    """
    Convert per-model accuracies to weights via softmax with temperature
    scaling and a minimum weight floor.

    Parameters
    ----------
    accuracies : dict  e.g. {"primary": 0.62, "rf": 0.58, "catboost": 0.55}
    temperature : float  Higher = sharper differentiation (default 5.0)
    min_weight : float  Minimum weight per model (default 0.10)

    Returns
    -------
    dict  Weights summing to 1.0, each >= min_weight
    """
    models = list(accuracies.keys())
    if not models:
        return dict(_FIXED_WEIGHTS)

    n = len(models)
    floor_total = min_weight * n
    if floor_total >= 1.0:
        # Too many models for the floor -- equal weights
        return {m: 1.0 / n for m in models}

    # Compute raw softmax (subtract max for numerical stability)
    vals = [accuracies[m] * temperature for m in models]
    max_val = max(vals)
    exps = [math.exp(v - max_val) for v in vals]
    exp_sum = sum(exps)

    # Distribute the remaining weight (1 - floor_total) proportionally
    remaining = 1.0 - floor_total
    raw_weights = {m: (exps[i] / exp_sum) for i, m in enumerate(models)}
    weights = {m: min_weight + remaining * raw_weights[m] for m in models}

    # Normalize to exactly 1.0 (handles floating point drift)
    w_sum = sum(weights.values())
    return {m: w / w_sum for m, w in weights.items()}


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class DynamicEnsemble:
    """
    Tracks per-model prediction accuracy over a rolling window and
    computes softmax-based ensemble weights, optionally per-regime.
    """

    def __init__(
        self,
        weights_path: Optional[Path] = None,
        temperature: float = _DEFAULT_TEMPERATURE,
        window_size: int = _ROLLING_WINDOW,
        min_weight: float = _MIN_WEIGHT,
    ):
        self.weights_path = weights_path or _WEIGHTS_PATH
        self.temperature = temperature
        self.window_size = window_size
        self.min_weight = min_weight

        # Per-regime rolling accuracy records
        # Structure: {regime: {model: deque of (predicted_win, actual_win)}}
        self._records: dict[str, dict[str, deque]] = {}
        for regime in _REGIMES:
            self._records[regime] = {m: deque(maxlen=window_size) for m in _MODEL_NAMES}

        # Cached weights per regime
        self._weights: dict[str, dict[str, float]] = {}
        for regime in _REGIMES:
            self._weights[regime] = dict(_FIXED_WEIGHTS)

        # Global (non-regime) weights for when regime is unknown
        self._weights["GLOBAL"] = dict(_FIXED_WEIGHTS)
        self._records["GLOBAL"] = {m: deque(maxlen=window_size) for m in _MODEL_NAMES}

        # Metadata
        self._last_rebalanced: Optional[str] = None
        self._total_records = 0

        # Load persisted state
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load weights and records from disk."""
        try:
            if self.weights_path.exists():
                with open(self.weights_path, "r") as f:
                    data = json.load(f)

                # Restore weights
                for regime in list(_REGIMES) + ["GLOBAL"]:
                    if regime in data.get("weights", {}):
                        saved = data["weights"][regime]
                        # Only use saved weights for models we know
                        w = {}
                        for m in _MODEL_NAMES:
                            w[m] = float(saved.get(m, _FIXED_WEIGHTS.get(m, 1.0 / len(_MODEL_NAMES))))
                        # Renormalize
                        w_sum = sum(w.values())
                        self._weights[regime] = {m: v / w_sum for m, v in w.items()}

                # Restore records
                for regime in list(_REGIMES) + ["GLOBAL"]:
                    if regime in data.get("records", {}):
                        for m in _MODEL_NAMES:
                            entries = data["records"][regime].get(m, [])
                            self._records[regime][m] = deque(
                                [(e[0], e[1]) for e in entries[-self.window_size:]],
                                maxlen=self.window_size,
                            )

                self._last_rebalanced = data.get("last_rebalanced")
                self._total_records = data.get("total_records", 0)
        except Exception as e:
            print(f"  [DynEnsemble] Failed to load weights: {e}, using defaults")

    def save(self) -> None:
        """Persist weights and records to disk."""
        try:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            data = {
                "weights": {},
                "records": {},
                "last_rebalanced": self._last_rebalanced,
                "total_records": self._total_records,
                "temperature": self.temperature,
                "window_size": self.window_size,
                "min_weight": self.min_weight,
                "saved_at": datetime.now(timezone.utc).isoformat(),
            }
            for regime in list(_REGIMES) + ["GLOBAL"]:
                data["weights"][regime] = self._weights.get(regime, dict(_FIXED_WEIGHTS))
                data["records"][regime] = {
                    m: list(self._records[regime][m])
                    for m in _MODEL_NAMES
                }

            with open(self.weights_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"  [DynEnsemble] Failed to save weights: {e}")

    # ------------------------------------------------------------------
    # Record outcomes
    # ------------------------------------------------------------------

    def _normalize_regime(self, regime: Optional[str]) -> str:
        """Map regime string to one of BULL/BEAR/CHOPPY."""
        if not regime:
            return "GLOBAL"
        r = regime.upper().strip()
        if r in ("BULL", "BULLISH", "TRENDING", "MARKUP", "UPTREND", "RISK_ON"):
            return "BULL"
        elif r in ("BEAR", "BEARISH", "MARKDOWN", "DOWNTREND", "RISK_OFF"):
            return "BEAR"
        elif r in ("CHOPPY", "SIDEWAYS", "RANGING", "ACCUMULATION", "NEUTRAL", "TRANSITIONAL", "HIGH_VOL"):
            return "CHOPPY"
        return "GLOBAL"

    def record_outcome(
        self,
        model_predictions: dict[str, float],
        actual_win: bool,
        regime: Optional[str] = None,
    ) -> None:
        """
        Record how each model performed on a closed trade.

        Parameters
        ----------
        model_predictions : dict
            e.g. {"primary": 0.72, "rf": 0.61, "catboost": 0.68}
            Win probability each model assigned to this signal.
        actual_win : bool
            Whether the trade actually won (TP hit).
        regime : str or None
            Market regime at entry time.
        """
        regime_key = self._normalize_regime(regime)
        actual_val = 1 if actual_win else 0

        for model_name, prob in model_predictions.items():
            if model_name not in _MODEL_NAMES:
                continue
            predicted_win = 1 if prob >= 0.5 else 0
            correct = 1 if predicted_win == actual_val else 0

            # Record in regime-specific and global
            self._records[regime_key][model_name].append((correct, 1))
            if regime_key != "GLOBAL":
                self._records["GLOBAL"][model_name].append((correct, 1))

        self._total_records += 1

        # Auto-rebalance every 10 new records
        if self._total_records % 10 == 0:
            self.rebalance()

    # ------------------------------------------------------------------
    # Compute weights
    # ------------------------------------------------------------------

    def _compute_accuracy(self, regime_key: str) -> dict[str, float]:
        """Compute rolling accuracy per model for a given regime."""
        accuracies = {}
        for m in _MODEL_NAMES:
            records = self._records[regime_key][m]
            if len(records) < 5:
                # Not enough data -- use default 0.5
                accuracies[m] = 0.5
            else:
                correct = sum(r[0] for r in records)
                total = len(records)
                accuracies[m] = correct / total
        return accuracies

    def rebalance(self, save: bool = True) -> dict[str, dict[str, float]]:
        """
        Recompute weights for all regimes based on recent accuracy.
        Called automatically every 10 records, or manually for weekly rebalancing.

        Returns
        -------
        dict  {regime: {model: weight}} for all regimes
        """
        for regime_key in list(_REGIMES) + ["GLOBAL"]:
            accuracies = self._compute_accuracy(regime_key)
            self._weights[regime_key] = _softmax_weights(
                accuracies,
                temperature=self.temperature,
                min_weight=self.min_weight,
            )

        self._last_rebalanced = datetime.now(timezone.utc).isoformat()

        if save:
            self.save()

        return dict(self._weights)

    def get_weights(
        self,
        regime: Optional[str] = None,
        available_models: Optional[list[str]] = None,
    ) -> dict[str, float]:
        """
        Get current ensemble weights, optionally filtered to available models.

        Parameters
        ----------
        regime : str or None
            Current market regime (mapped to BULL/BEAR/CHOPPY).
        available_models : list or None
            Subset of model names actually available (e.g. ["primary", "rf"]
            when CatBoost is not installed). Weights are renormalized.

        Returns
        -------
        dict  {model_name: weight} summing to 1.0
        """
        regime_key = self._normalize_regime(regime)
        weights = dict(self._weights.get(regime_key, self._weights["GLOBAL"]))

        # Filter to available models
        if available_models is not None:
            weights = {m: w for m, w in weights.items() if m in available_models}

        if not weights:
            return dict(_FIXED_WEIGHTS)

        # Renormalize
        w_sum = sum(weights.values())
        if w_sum <= 0:
            return {m: 1.0 / len(weights) for m in weights}
        return {m: w / w_sum for m, w in weights.items()}

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def get_diagnostics(self) -> dict:
        """Return diagnostic info for dashboard/logging."""
        diag = {
            "total_records": self._total_records,
            "last_rebalanced": self._last_rebalanced,
            "temperature": self.temperature,
            "window_size": self.window_size,
            "regimes": {},
        }
        for regime_key in list(_REGIMES) + ["GLOBAL"]:
            acc = self._compute_accuracy(regime_key)
            sample_counts = {m: len(self._records[regime_key][m]) for m in _MODEL_NAMES}
            diag["regimes"][regime_key] = {
                "accuracies": acc,
                "weights": self._weights.get(regime_key, dict(_FIXED_WEIGHTS)),
                "sample_counts": sample_counts,
            }
        return diag


# ---------------------------------------------------------------------------
# Weekly rebalancing entry point (called from retrain workflow)
# ---------------------------------------------------------------------------

def weekly_rebalance(weights_path: Optional[str] = None) -> dict:
    """
    Entry point for weekly rebalancing, callable from retrain workflow.

    Usage:
        python -c "from alpha_engine.dynamic_ensemble import weekly_rebalance; weekly_rebalance()"

    Or from the retrain script:
        from dynamic_ensemble import weekly_rebalance
        result = weekly_rebalance()

    Returns
    -------
    dict  Updated weights per regime
    """
    path = Path(weights_path) if weights_path else None
    ensemble = DynamicEnsemble(weights_path=path)

    print("[DynEnsemble] Weekly rebalance triggered")
    print(f"  Total records: {ensemble._total_records}")

    result = ensemble.rebalance(save=True)

    for regime_key in list(_REGIMES) + ["GLOBAL"]:
        acc = ensemble._compute_accuracy(regime_key)
        w = result.get(regime_key, {})
        counts = {m: len(ensemble._records[regime_key][m]) for m in _MODEL_NAMES}
        print(f"  {regime_key:8s} | acc={acc} | weights={w} | n={counts}")

    print(f"  Saved to {ensemble.weights_path}")
    return result


# ---------------------------------------------------------------------------
# Convenience: backfill from closed picks
# ---------------------------------------------------------------------------

def backfill_from_closed_picks(
    closed_picks_path: Optional[str] = None,
    weights_path: Optional[str] = None,
) -> int:
    """
    Backfill model accuracy records from closed_picks.json.

    For each closed pick that has model probability predictions stored,
    record the outcome for the dynamic ensemble. This is useful when
    first deploying dynamic weighting with existing historical data.

    Returns number of records processed.
    """
    picks_path = Path(closed_picks_path) if closed_picks_path else _DATA_DIR / "closed_picks.json"
    if not picks_path.exists():
        print(f"  [DynEnsemble] No closed picks at {picks_path}")
        return 0

    try:
        with open(picks_path, "r") as f:
            picks = json.load(f)
    except Exception as e:
        print(f"  [DynEnsemble] Failed to load closed picks: {e}")
        return 0

    if not isinstance(picks, list):
        picks = picks.get("picks", picks.get("closed", []))

    w_path = Path(weights_path) if weights_path else None
    ensemble = DynamicEnsemble(weights_path=w_path)
    count = 0

    for pick in picks:
        # Determine outcome
        outcome = pick.get("outcome", "").upper()
        if outcome in ("WON", "TP_HIT", "WIN", "TP"):
            actual_win = True
        elif outcome in ("LOST", "SL_HIT", "LOSS", "SL"):
            actual_win = False
        else:
            continue  # Skip expired/uncertain

        # Get model predictions if stored
        model_preds = pick.get("model_predictions", {})
        if not model_preds:
            # Fallback: use ml_score as primary prediction
            ml_score = pick.get("ml_score") or pick.get("score")
            if ml_score is not None:
                model_preds = {"primary": float(ml_score)}
            else:
                continue

        regime = (
            pick.get("regime_at_entry")
            or pick.get("market_regime")
            or pick.get("regime")
        )

        ensemble.record_outcome(model_preds, actual_win, regime)
        count += 1

    if count > 0:
        ensemble.rebalance(save=True)
        print(f"  [DynEnsemble] Backfilled {count} records from {picks_path.name}")

    return count


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "backfill":
        n = backfill_from_closed_picks()
        print(f"Backfilled {n} records")
    else:
        result = weekly_rebalance()
        print(f"\nFinal weights: {json.dumps(result, indent=2)}")
