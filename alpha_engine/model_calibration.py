#!/usr/bin/env python3
"""
ALPHA_ENGINE -- Model Calibration & Uncertainty Quantification
================================================================
Pure-Python implementation (no sklearn) of:

1. Probability Calibration (Platt Scaling + Isotonic Regression)
   - Calibrates raw ml_score -> true P(win) using closed_picks.json
   - Computes Expected Calibration Error (ECE) in 10 bins
   - Flags miscalibration when ECE > 0.10
   - Saves calibration_report.json

2. Prediction Uncertainty via Ensemble Disagreement
   - Measures spread across XGBoost / RF / CatBoost predictions
   - Adds prediction_uncertainty field to each pick
   - Uncertainty > 0.15  -> -3 elite_score penalty
   - Uncertainty < 0.05  -> +3 elite_score bonus (high agreement)

3. Confidence-Weighted Position Sizing
   - get_calibrated_confidence(pick) returns:
       calibrated_probability, uncertainty, confidence_adjusted_size

4. Model Drift Detection
   - Rolling 50-prediction ECE vs baseline
   - Flags retraining when ECE increases 50%+
   - Saves model_drift.json

Usage:
  from model_calibration import (
      calibrate_model,               # run full calibration from closed picks
      get_prediction_uncertainty,     # ensemble disagreement for a pick
      get_calibrated_confidence,      # calibrated prob + uncertainty + sizing
      check_model_drift,             # rolling drift detection
      get_uncertainty_elite_adjustment,  # bonus/penalty for elite_scorer
      apply_calibration_to_picks,    # batch: enrich all picks
  )
"""

from __future__ import annotations

import json
import math
import os
import time
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).resolve().parent / "data"
_CLOSED_PICKS_PATH = _DATA_DIR / "closed_picks.json"
_CALIBRATION_REPORT_PATH = _DATA_DIR / "calibration_report.json"
_MODEL_DRIFT_PATH = _DATA_DIR / "model_drift.json"

# ---------------------------------------------------------------------------
# In-memory calibration cache (loaded once per process)
# ---------------------------------------------------------------------------
_calibration_cache: dict = {}
_calibration_cache_time: float = 0.0
_CACHE_TTL = 3600  # 1 hour


# =========================================================================
# 1. PROBABILITY CALIBRATION (Platt Scaling + Isotonic Regression)
# =========================================================================

def _load_closed_picks(data_dir: Optional[Path] = None) -> list[dict]:
    """Load closed_picks.json safely."""
    path = (data_dir or _DATA_DIR) / "closed_picks.json"
    if not path.exists():
        return []
    try:
        with open(path) as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _platt_scaling(scores: list[float], labels: list[int]) -> tuple[float, float]:
    """Fit Platt scaling parameters A, B via gradient descent.

    Platt scaling: P(y=1|s) = 1 / (1 + exp(A*s + B))
    We find A, B that minimize cross-entropy loss.

    Pure Python -- no sklearn dependency.

    Returns (A, B) parameters.
    """
    if not scores or not labels:
        return 0.0, 0.0

    n = len(scores)
    # Target smoothing (Platt's recipe): avoid 0/1 targets
    n_pos = sum(labels)
    n_neg = n - n_pos
    if n_pos == 0 or n_neg == 0:
        return 0.0, 0.0

    t_pos = (n_pos + 1) / (n_pos + 2)
    t_neg = 1 / (n_neg + 2)
    targets = [t_pos if y == 1 else t_neg for y in labels]

    # Initialize A, B
    A = 0.0
    B = 0.0
    lr = 0.01
    max_iter = 200

    for _ in range(max_iter):
        grad_A = 0.0
        grad_B = 0.0
        for i in range(n):
            z = A * scores[i] + B
            # Numerically stable sigmoid
            if z >= 0:
                p = 1.0 / (1.0 + math.exp(-z))
            else:
                ez = math.exp(z)
                p = ez / (1.0 + ez)
            p = max(1e-7, min(1 - 1e-7, p))
            err = p - targets[i]
            grad_A += err * scores[i]
            grad_B += err
        grad_A /= n
        grad_B /= n
        A -= lr * grad_A
        B -= lr * grad_B

    return A, B


def _platt_predict(score: float, A: float, B: float) -> float:
    """Apply Platt scaling to get calibrated probability."""
    z = A * score + B
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    else:
        ez = math.exp(z)
        return ez / (1.0 + ez)


def _isotonic_regression(scores: list[float], labels: list[int],
                         n_bins: int = 20) -> list[tuple[float, float, float]]:
    """Pure-Python isotonic regression via pool-adjacent-violators (PAV).

    Bins scores into n_bins buckets, computes mean outcome per bin,
    then applies PAV to enforce monotonicity.

    Returns list of (bin_lower, bin_upper, calibrated_prob) tuples.
    """
    if not scores or not labels:
        return []

    # Sort by score
    paired = sorted(zip(scores, labels), key=lambda x: x[0])
    n = len(paired)

    # Bin boundaries
    min_s = paired[0][0]
    max_s = paired[-1][0]
    if max_s <= min_s:
        avg = sum(labels) / len(labels)
        return [(0.0, 1.0, avg)]

    bin_width = (max_s - min_s) / n_bins
    bins: list[list[int]] = [[] for _ in range(n_bins)]

    for s, y in paired:
        idx = min(int((s - min_s) / bin_width), n_bins - 1)
        bins[idx].append(y)

    # Mean per bin (PAV input)
    means: list[float] = []
    weights: list[int] = []
    bin_edges: list[tuple[float, float]] = []
    for i in range(n_bins):
        lo = min_s + i * bin_width
        hi = lo + bin_width
        bin_edges.append((lo, hi))
        if bins[i]:
            means.append(sum(bins[i]) / len(bins[i]))
            weights.append(len(bins[i]))
        else:
            means.append(0.0)
            weights.append(0)

    # Pool Adjacent Violators (PAV) -- enforce monotonicity
    n_m = len(means)
    result = list(means)
    w = list(weights)

    i = 0
    while i < n_m - 1:
        if result[i] > result[i + 1]:
            # Pool: weighted average
            total_w = w[i] + w[i + 1]
            if total_w > 0:
                pooled = (result[i] * w[i] + result[i + 1] * w[i + 1]) / total_w
            else:
                pooled = (result[i] + result[i + 1]) / 2
            result[i] = pooled
            result[i + 1] = pooled
            w[i] = total_w
            w[i + 1] = total_w
            # Go back to check previous
            if i > 0:
                i -= 1
            else:
                i += 1
        else:
            i += 1

    isotonic_map = []
    for i in range(n_bins):
        lo, hi = bin_edges[i]
        isotonic_map.append((lo, hi, max(0.0, min(1.0, result[i]))))

    return isotonic_map


def _isotonic_predict(score: float, isotonic_map: list[tuple[float, float, float]]) -> float:
    """Look up calibrated probability from isotonic map."""
    if not isotonic_map:
        return score  # pass-through

    # Find matching bin
    for lo, hi, prob in isotonic_map:
        if lo <= score <= hi:
            return prob

    # Outside range: clamp to nearest
    if score < isotonic_map[0][0]:
        return isotonic_map[0][2]
    return isotonic_map[-1][2]


def _compute_ece(scores: list[float], labels: list[int], n_bins: int = 10) -> float:
    """Compute Expected Calibration Error.

    ECE = sum over bins: (bin_weight) * |avg_predicted - avg_actual|

    Lower is better. ECE > 0.10 = miscalibrated.
    """
    if not scores or not labels:
        return 0.0

    n = len(scores)
    bin_sums_pred: list[float] = [0.0] * n_bins
    bin_sums_true: list[float] = [0.0] * n_bins
    bin_counts: list[int] = [0] * n_bins

    for s, y in zip(scores, labels):
        idx = min(int(s * n_bins), n_bins - 1)
        idx = max(0, idx)
        bin_sums_pred[idx] += s
        bin_sums_true[idx] += y
        bin_counts[idx] += 1

    ece = 0.0
    for i in range(n_bins):
        if bin_counts[i] > 0:
            avg_pred = bin_sums_pred[i] / bin_counts[i]
            avg_true = bin_sums_true[i] / bin_counts[i]
            weight = bin_counts[i] / n
            ece += weight * abs(avg_pred - avg_true)

    return round(ece, 6)


def _compute_bin_details(scores: list[float], labels: list[int],
                         n_bins: int = 10) -> list[dict]:
    """Compute per-bin calibration details for the report."""
    if not scores or not labels:
        return []

    n = len(scores)
    bins_pred: list[list[float]] = [[] for _ in range(n_bins)]
    bins_true: list[list[int]] = [[] for _ in range(n_bins)]

    for s, y in zip(scores, labels):
        idx = min(int(s * n_bins), n_bins - 1)
        idx = max(0, idx)
        bins_pred[idx].append(s)
        bins_true[idx].append(y)

    details = []
    for i in range(n_bins):
        lo = i / n_bins
        hi = (i + 1) / n_bins
        count = len(bins_pred[i])
        if count > 0:
            avg_pred = sum(bins_pred[i]) / count
            avg_true = sum(bins_true[i]) / count
            gap = abs(avg_pred - avg_true)
        else:
            avg_pred = 0.0
            avg_true = 0.0
            gap = 0.0
        details.append({
            "bin_range": f"{lo:.1f}-{hi:.1f}",
            "count": count,
            "avg_predicted": round(avg_pred, 4),
            "avg_actual": round(avg_true, 4),
            "gap": round(gap, 4),
        })

    return details


def calibrate_model(data_dir: Optional[Path] = None) -> dict:
    """Run full model calibration from closed_picks.json.

    Steps:
      1. Load closed picks, extract (ml_score, outcome) pairs
      2. Fit Platt scaling (A, B)
      3. Fit isotonic regression map
      4. Compute ECE on calibrated predictions
      5. Save calibration_report.json

    Returns calibration report dict.
    """
    global _calibration_cache, _calibration_cache_time

    d = data_dir or _DATA_DIR
    closed = _load_closed_picks(d)

    if not closed:
        report = {
            "status": "no_data",
            "message": "No closed picks available for calibration",
            "ece_raw": None,
            "ece_calibrated": None,
            "platt_A": 0.0,
            "platt_B": 0.0,
            "isotonic_map": [],
            "n_picks": 0,
            "calibrated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        _save_report(report, d)
        _calibration_cache = report
        _calibration_cache_time = time.time()
        return report

    # Extract ml_score and binary outcome
    scores = []
    labels = []
    for pick in closed:
        ml = pick.get("ml_score")
        if ml is None:
            ml = pick.get("confidence", 0.5)
        if ml is None or not isinstance(ml, (int, float)):
            continue
        ml = float(ml)
        # Clamp to [0, 1]
        ml = max(0.0, min(1.0, ml))

        status = str(pick.get("status", "")).upper()
        if status == "WON":
            labels.append(1)
            scores.append(ml)
        elif status in ("LOST", "STOPPED"):
            labels.append(0)
            scores.append(ml)
        # Skip OPEN / EXPIRED / unknown

    if len(scores) < 10:
        report = {
            "status": "insufficient_data",
            "message": f"Only {len(scores)} scored closed picks (need 10+)",
            "ece_raw": None,
            "ece_calibrated": None,
            "platt_A": 0.0,
            "platt_B": 0.0,
            "isotonic_map": [],
            "n_picks": len(scores),
            "calibrated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        _save_report(report, d)
        _calibration_cache = report
        _calibration_cache_time = time.time()
        return report

    # Raw ECE
    ece_raw = _compute_ece(scores, labels, n_bins=10)

    # Fit Platt scaling
    platt_A, platt_B = _platt_scaling(scores, labels)
    platt_calibrated = [_platt_predict(s, platt_A, platt_B) for s in scores]
    ece_platt = _compute_ece(platt_calibrated, labels, n_bins=10)

    # Fit isotonic regression
    isotonic_map = _isotonic_regression(scores, labels, n_bins=20)
    iso_calibrated = [_isotonic_predict(s, isotonic_map) for s in scores]
    ece_isotonic = _compute_ece(iso_calibrated, labels, n_bins=10)

    # Choose the method with lower ECE
    if ece_platt <= ece_isotonic:
        method = "platt"
        ece_calibrated = ece_platt
    else:
        method = "isotonic"
        ece_calibrated = ece_isotonic

    # Miscalibration flag
    miscalibrated = ece_calibrated > 0.10

    # Bin details for raw scores
    bin_details = _compute_bin_details(scores, labels, n_bins=10)

    # Win rate at different score thresholds
    thresholds = {}
    for t in [0.5, 0.6, 0.7, 0.8]:
        above = [(s, y) for s, y in zip(scores, labels) if s >= t]
        if above:
            wr = sum(y for _, y in above) / len(above)
            thresholds[str(t)] = {"count": len(above), "win_rate": round(wr, 4)}

    # Serialize isotonic map
    iso_serializable = [
        {"lo": round(lo, 4), "hi": round(hi, 4), "prob": round(p, 4)}
        for lo, hi, p in isotonic_map
    ]

    report = {
        "status": "calibrated",
        "method": method,
        "miscalibrated": miscalibrated,
        "ece_raw": round(ece_raw, 6),
        "ece_platt": round(ece_platt, 6),
        "ece_isotonic": round(ece_isotonic, 6),
        "ece_calibrated": round(ece_calibrated, 6),
        "platt_A": round(platt_A, 6),
        "platt_B": round(platt_B, 6),
        "isotonic_map": iso_serializable,
        "n_picks": len(scores),
        "overall_win_rate": round(sum(labels) / len(labels), 4),
        "threshold_analysis": thresholds,
        "bin_details": bin_details,
        "calibrated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    _save_report(report, d)
    _calibration_cache = report
    _calibration_cache_time = time.time()

    return report


def _save_report(report: dict, data_dir: Optional[Path] = None) -> None:
    """Persist calibration report to JSON."""
    d = data_dir or _DATA_DIR
    d.mkdir(parents=True, exist_ok=True)
    path = d / "calibration_report.json"
    try:
        with open(path, "w") as f:
            json.dump(report, f, indent=2)
    except OSError:
        pass


def _load_calibration(data_dir: Optional[Path] = None) -> dict:
    """Load calibration report with 1-hour cache."""
    global _calibration_cache, _calibration_cache_time

    now = time.time()
    if _calibration_cache and (now - _calibration_cache_time) < _CACHE_TTL:
        return _calibration_cache

    d = data_dir or _DATA_DIR
    path = d / "calibration_report.json"
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            _calibration_cache = json.load(f)
        _calibration_cache_time = now
        return _calibration_cache
    except (json.JSONDecodeError, OSError):
        return {}


def get_calibrated_probability(raw_score: float,
                               data_dir: Optional[Path] = None) -> float:
    """Apply calibration to a raw ml_score -> calibrated P(win).

    Falls back to raw_score if no calibration data is available.
    """
    cal = _load_calibration(data_dir)
    if not cal or cal.get("status") not in ("calibrated",):
        return raw_score

    method = cal.get("method", "platt")
    if method == "platt":
        A = cal.get("platt_A", 0.0)
        B = cal.get("platt_B", 0.0)
        if A == 0.0 and B == 0.0:
            return raw_score
        return _platt_predict(raw_score, A, B)
    else:
        # Isotonic
        iso_raw = cal.get("isotonic_map", [])
        if not iso_raw:
            return raw_score
        iso_map = [(d["lo"], d["hi"], d["prob"]) for d in iso_raw]
        return _isotonic_predict(raw_score, iso_map)


# =========================================================================
# 2. PREDICTION UNCERTAINTY VIA ENSEMBLE DISAGREEMENT
# =========================================================================

def get_prediction_uncertainty(pick: dict) -> dict:
    """Compute ensemble prediction uncertainty for a pick.

    Looks for ensemble_scores in pick metadata. If not present,
    synthesizes from available score fields (ml_score, confidence, etc.).

    Returns dict with:
      - ensemble_mean: float
      - ensemble_std: float (the "uncertainty")
      - ensemble_count: int
      - uncertainty_level: "LOW" / "MEDIUM" / "HIGH"
    """
    # Check for explicit ensemble predictions
    ensemble_preds = pick.get("ensemble_scores", [])

    if not ensemble_preds:
        # Synthesize from available score fields
        preds = []
        for key in ("ml_score", "confidence", "meta_label_prob",
                     "xgb_score", "rf_score", "catboost_score",
                     "pattern_score", "momentum_score"):
            val = pick.get(key)
            if val is not None and isinstance(val, (int, float)):
                v = float(val)
                if 0.0 <= v <= 1.0:
                    preds.append(v)
        # Also check nested extra_json
        extra = pick.get("extra", {})
        if isinstance(extra, str):
            try:
                extra = json.loads(extra)
            except (json.JSONDecodeError, TypeError):
                extra = {}
        if isinstance(extra, dict):
            for key in ("xgb_score", "rf_score", "catboost_score",
                         "ml_score", "pattern_prob"):
                val = extra.get(key)
                if val is not None and isinstance(val, (int, float)):
                    v = float(val)
                    if 0.0 <= v <= 1.0:
                        preds.append(v)

        ensemble_preds = preds

    if len(ensemble_preds) < 2:
        # Can't compute disagreement with < 2 predictions
        mean_val = ensemble_preds[0] if ensemble_preds else 0.5
        return {
            "ensemble_mean": round(mean_val, 4),
            "ensemble_std": 0.0,
            "ensemble_count": len(ensemble_preds),
            "uncertainty_level": "UNKNOWN",
        }

    # Compute mean and standard deviation
    n = len(ensemble_preds)
    mean_val = sum(ensemble_preds) / n
    variance = sum((x - mean_val) ** 2 for x in ensemble_preds) / n
    std_val = math.sqrt(variance)

    # Classify uncertainty level
    if std_val < 0.05:
        level = "LOW"
    elif std_val < 0.15:
        level = "MEDIUM"
    else:
        level = "HIGH"

    return {
        "ensemble_mean": round(mean_val, 4),
        "ensemble_std": round(std_val, 4),
        "ensemble_count": n,
        "uncertainty_level": level,
    }


def get_uncertainty_elite_adjustment(pick: dict) -> int:
    """Get elite_score adjustment based on prediction uncertainty.

    Returns:
      +3 if uncertainty < 0.05 (high agreement bonus)
      -3 if uncertainty > 0.15 (high disagreement penalty)
       0 otherwise
    """
    unc = get_prediction_uncertainty(pick)
    std = unc.get("ensemble_std", 0.0)
    level = unc.get("uncertainty_level", "UNKNOWN")

    if level == "UNKNOWN":
        return 0

    if std < 0.05:
        return 3   # High agreement bonus
    elif std > 0.15:
        return -3  # High disagreement penalty
    return 0


# =========================================================================
# 3. CONFIDENCE-WEIGHTED POSITION SIZING
# =========================================================================

def get_calibrated_confidence(pick: dict,
                              data_dir: Optional[Path] = None) -> dict:
    """Get full calibrated confidence for position sizing.

    Returns dict with:
      - calibrated_probability: Platt/isotonic-scaled P(win)
      - uncertainty: ensemble std
      - uncertainty_level: LOW/MEDIUM/HIGH/UNKNOWN
      - confidence_adjusted_size: kelly_size * (1 - uncertainty)
      - raw_ml_score: original ml_score
    """
    raw_ml = float(pick.get("ml_score", pick.get("confidence", 0.5)) or 0.5)
    raw_ml = max(0.0, min(1.0, raw_ml))

    # Calibrate probability
    calibrated_prob = get_calibrated_probability(raw_ml, data_dir)

    # Get uncertainty
    unc = get_prediction_uncertainty(pick)
    uncertainty = unc.get("ensemble_std", 0.0)
    unc_level = unc.get("uncertainty_level", "UNKNOWN")

    # Adjusted sizing factor: (1 - uncertainty)
    # If uncertainty is 0.15, size is reduced to 85% of Kelly
    # If uncertainty is 0.0, full Kelly
    sizing_multiplier = max(0.1, 1.0 - uncertainty)

    # Kelly fraction from pick (if already computed)
    kelly_frac = pick.get("kelly_fraction", 0.02)
    adjusted_size = kelly_frac * sizing_multiplier

    return {
        "calibrated_probability": round(calibrated_prob, 4),
        "uncertainty": round(uncertainty, 4),
        "uncertainty_level": unc_level,
        "confidence_adjusted_size": round(adjusted_size, 6),
        "sizing_multiplier": round(sizing_multiplier, 4),
        "raw_ml_score": round(raw_ml, 4),
    }


# =========================================================================
# 4. MODEL DRIFT DETECTION
# =========================================================================

def check_model_drift(data_dir: Optional[Path] = None) -> dict:
    """Track rolling 50-prediction ECE and detect model drift.

    Compares recent ECE to baseline ECE from calibration.
    If ECE increases by 50%+, flags for retraining.

    Saves model_drift.json.
    Returns drift report dict.
    """
    d = data_dir or _DATA_DIR
    closed = _load_closed_picks(d)

    if len(closed) < 50:
        drift_report = {
            "status": "insufficient_data",
            "message": f"Need 50+ closed picks, have {len(closed)}",
            "needs_retraining": False,
            "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        _save_drift(drift_report, d)
        return drift_report

    # Load calibration report for baseline ECE
    cal = _load_calibration(d)
    baseline_ece = cal.get("ece_calibrated") or cal.get("ece_raw") or 0.10

    # Get the most recent 50 closed picks (sorted by exit_date desc)
    sorted_closed = sorted(
        closed,
        key=lambda p: p.get("exit_date", p.get("entry_date", "1970-01-01")),
        reverse=True,
    )
    recent_50 = sorted_closed[:50]

    # Compute ECE on recent 50
    recent_scores = []
    recent_labels = []
    for pick in recent_50:
        ml = pick.get("ml_score", pick.get("confidence"))
        if ml is None or not isinstance(ml, (int, float)):
            continue
        ml = float(ml)
        ml = max(0.0, min(1.0, ml))

        status = str(pick.get("status", "")).upper()
        if status == "WON":
            recent_labels.append(1)
            recent_scores.append(ml)
        elif status in ("LOST", "STOPPED"):
            recent_labels.append(0)
            recent_scores.append(ml)

    if len(recent_scores) < 20:
        drift_report = {
            "status": "insufficient_recent",
            "message": f"Only {len(recent_scores)} scored in recent 50",
            "needs_retraining": False,
            "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        _save_drift(drift_report, d)
        return drift_report

    recent_ece = _compute_ece(recent_scores, recent_labels, n_bins=10)

    # Drift detection: 50% increase over baseline
    if baseline_ece > 0:
        ece_increase_pct = (recent_ece - baseline_ece) / baseline_ece
    else:
        ece_increase_pct = 0.0 if recent_ece == 0 else 1.0

    needs_retraining = ece_increase_pct >= 0.50
    recent_wr = sum(recent_labels) / len(recent_labels) if recent_labels else 0.0

    # Load prior drift history
    drift_path = d / "model_drift.json"
    prior_history = []
    if drift_path.exists():
        try:
            with open(drift_path) as f:
                prior = json.load(f)
            prior_history = prior.get("history", [])
        except (json.JSONDecodeError, OSError):
            pass

    # Add current measurement to rolling history (keep last 20)
    prior_history.append({
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rolling_ece": round(recent_ece, 6),
        "baseline_ece": round(baseline_ece, 6),
        "increase_pct": round(ece_increase_pct, 4),
        "recent_wr": round(recent_wr, 4),
        "n_samples": len(recent_scores),
    })
    prior_history = prior_history[-20:]  # keep last 20

    drift_report = {
        "status": "drift_detected" if needs_retraining else "stable",
        "needs_retraining": needs_retraining,
        "baseline_ece": round(baseline_ece, 6),
        "rolling_ece": round(recent_ece, 6),
        "ece_increase_pct": round(ece_increase_pct, 4),
        "recent_win_rate": round(recent_wr, 4),
        "n_recent_scored": len(recent_scores),
        "history": prior_history,
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    _save_drift(drift_report, d)
    return drift_report


def _save_drift(report: dict, data_dir: Optional[Path] = None) -> None:
    """Persist model drift report to JSON."""
    d = data_dir or _DATA_DIR
    d.mkdir(parents=True, exist_ok=True)
    path = d / "model_drift.json"
    try:
        with open(path, "w") as f:
            json.dump(report, f, indent=2)
    except OSError:
        pass


# =========================================================================
# 5. BATCH ENRICHMENT -- apply_calibration_to_picks
# =========================================================================

def apply_calibration_to_picks(picks: list[dict],
                               data_dir: Optional[Path] = None) -> list[dict]:
    """Enrich all picks with calibration and uncertainty fields.

    Adds to each pick:
      - calibrated_probability
      - prediction_uncertainty
      - uncertainty_level
      - confidence_adjusted_size
      - sizing_multiplier

    Modifies picks in-place and returns them.
    """
    if not picks:
        return picks

    d = data_dir or _DATA_DIR

    enriched = 0
    for pick in picks:
        try:
            # Calibrated confidence
            cal_info = get_calibrated_confidence(pick, d)
            pick["calibrated_probability"] = cal_info["calibrated_probability"]
            pick["prediction_uncertainty"] = cal_info["uncertainty"]
            pick["uncertainty_level"] = cal_info["uncertainty_level"]
            pick["confidence_adjusted_size"] = cal_info["confidence_adjusted_size"]
            pick["sizing_multiplier"] = cal_info["sizing_multiplier"]
            enriched += 1
        except Exception:
            # Non-fatal: leave pick as-is
            pass

    if enriched:
        print(f"  [CALIBRATION] Enriched {enriched}/{len(picks)} picks with "
              f"calibrated probability + uncertainty")

    return picks


# =========================================================================
# 6. STARTUP DIAGNOSTICS (called from production_scanner.py)
# =========================================================================

def run_calibration_diagnostics(data_dir: Optional[Path] = None) -> None:
    """Run calibration + drift check at scanner startup.

    Prints status summary. Non-fatal on any error.
    """
    d = data_dir or _DATA_DIR

    try:
        # Run calibration (or load cached)
        cal = _load_calibration(d)
        if not cal or cal.get("status") not in ("calibrated",):
            cal = calibrate_model(d)

        status = cal.get("status", "unknown")
        if status == "calibrated":
            ece = cal.get("ece_calibrated", 0)
            method = cal.get("method", "?")
            n = cal.get("n_picks", 0)
            misc = cal.get("miscalibrated", False)
            flag = " ** MISCALIBRATED **" if misc else ""
            print(f"  [CALIBRATION] {method} on {n} picks: ECE={ece:.4f}{flag}")
        elif status in ("no_data", "insufficient_data"):
            print(f"  [CALIBRATION] {cal.get('message', 'No data')}")
        else:
            print(f"  [CALIBRATION] Status: {status}")

        # Drift detection
        drift = check_model_drift(d)
        drift_status = drift.get("status", "unknown")
        if drift_status == "drift_detected":
            increase = drift.get("ece_increase_pct", 0)
            print(f"  [DRIFT] ** MODEL DRIFT DETECTED ** ECE increased "
                  f"{increase:.0%} -- consider retraining")
        elif drift_status == "stable":
            rolling_ece = drift.get("rolling_ece", 0)
            print(f"  [DRIFT] Stable (rolling ECE={rolling_ece:.4f})")
        else:
            print(f"  [DRIFT] {drift.get('message', 'Skipped')}")

    except Exception as e:
        print(f"  [CALIBRATION] Diagnostics failed (non-fatal): {e}")


# =========================================================================
# Module self-test
# =========================================================================
if __name__ == "__main__":
    print("=== Model Calibration Self-Test ===\n")

    # Test Platt scaling with synthetic data
    test_scores = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.35, 0.55, 0.75,
                   0.2, 0.45, 0.65, 0.85, 0.25, 0.55, 0.72, 0.81, 0.33, 0.67]
    test_labels = [0, 0, 0, 1, 1, 1, 1, 0, 1, 1,
                   0, 0, 1, 1, 0, 0, 1, 1, 0, 1]

    print(f"Test data: {len(test_scores)} samples, WR={sum(test_labels)/len(test_labels):.0%}")

    # ECE
    ece = _compute_ece(test_scores, test_labels)
    print(f"Raw ECE: {ece:.4f}")

    # Platt
    A, B = _platt_scaling(test_scores, test_labels)
    print(f"Platt params: A={A:.4f}, B={B:.4f}")
    platt_cal = [_platt_predict(s, A, B) for s in test_scores]
    ece_platt = _compute_ece(platt_cal, test_labels)
    print(f"Platt ECE: {ece_platt:.4f}")

    # Isotonic
    iso_map = _isotonic_regression(test_scores, test_labels)
    iso_cal = [_isotonic_predict(s, iso_map) for s in test_scores]
    ece_iso = _compute_ece(iso_cal, test_labels)
    print(f"Isotonic ECE: {ece_iso:.4f}")

    # Uncertainty test
    print("\n--- Uncertainty Test ---")
    high_agree = {"ml_score": 0.7, "confidence": 0.71, "meta_label_prob": 0.69}
    high_disagree = {"ml_score": 0.7, "confidence": 0.5, "meta_label_prob": 0.8}

    u1 = get_prediction_uncertainty(high_agree)
    print(f"High agreement: std={u1['ensemble_std']:.4f}, level={u1['uncertainty_level']}")

    u2 = get_prediction_uncertainty(high_disagree)
    print(f"High disagree:  std={u2['ensemble_std']:.4f}, level={u2['uncertainty_level']}")

    adj1 = get_uncertainty_elite_adjustment(high_agree)
    adj2 = get_uncertainty_elite_adjustment(high_disagree)
    print(f"Elite adj (agree): {adj1:+d}, Elite adj (disagree): {adj2:+d}")

    # Full calibration from real data
    print("\n--- Full Calibration (real data) ---")
    report = calibrate_model()
    print(f"Status: {report.get('status')}")
    if report.get("status") == "calibrated":
        print(f"Method: {report.get('method')}")
        print(f"ECE raw: {report.get('ece_raw'):.4f}")
        print(f"ECE calibrated: {report.get('ece_calibrated'):.4f}")
        print(f"Miscalibrated: {report.get('miscalibrated')}")
        print(f"N picks: {report.get('n_picks')}")

    # Drift check
    print("\n--- Drift Check ---")
    drift = check_model_drift()
    print(f"Status: {drift.get('status')}")
    print(f"Needs retraining: {drift.get('needs_retraining')}")

    print("\n=== Self-test complete ===")
