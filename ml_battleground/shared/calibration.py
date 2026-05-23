"""
Probability calibration for ML Battleground confidence scores.

Problem: ML models (especially neural nets) output overconfident probabilities.
A model saying "85% confident" on a trade that only wins 45% of the time
causes position sizing to be dangerously large.

Solution: Isotonic regression learns the actual P(win) for each confidence bucket
from historical closed trades. Falls back to temperature scaling when insufficient data.

References:
  - Platt (1999) "Probabilistic Outputs for SVMs" -- sigmoid calibration
  - Niculescu-Mizil & Caruana (2005) -- isotonic regression outperforms Platt
  - R021 (Dubois) -- recommended isotonic calibration for crypto_ml_edge pipeline
"""
import os
import json
import numpy as np
from typing import Optional


CALIBRATION_DIR = os.path.join(os.path.dirname(__file__), "..", "shared_data")
CALIBRATION_FILE = os.path.join(CALIBRATION_DIR, "calibration_map.json")
MIN_SAMPLES_FOR_ISOTONIC = 30  # need at least 30 closed trades to calibrate


def build_calibration_map(closed_trades: list[dict]) -> dict:
    """
    Build a calibration map from historical closed trades.

    Groups trades into confidence buckets, computes actual win rate per bucket,
    then creates a monotonic (isotonic) mapping.

    Args:
        closed_trades: list of closed trade dicts with 'confidence' and 'net_pnl_pct' keys

    Returns:
        dict with 'buckets' (list of {raw_conf, actual_wr, count}) and 'method' str
    """
    # Extract confidence and outcome pairs
    pairs = []
    for trade in closed_trades:
        conf = trade.get("confidence") or trade.get("ml_score")
        pnl = trade.get("net_pnl_pct", 0)
        if conf is not None:
            pairs.append((float(conf), 1.0 if pnl > 0 else 0.0))

    if len(pairs) < MIN_SAMPLES_FOR_ISOTONIC:
        return {"buckets": [], "method": "insufficient_data", "n_samples": len(pairs)}

    # Sort by confidence
    pairs.sort(key=lambda x: x[0])

    # Create buckets (10 equal-frequency bins)
    n = len(pairs)
    bucket_size = max(n // 10, 3)
    buckets = []

    for i in range(0, n, bucket_size):
        chunk = pairs[i:i + bucket_size]
        if len(chunk) < 2:
            continue
        raw_conf = float(np.mean([c for c, _ in chunk]))
        actual_wr = float(np.mean([w for _, w in chunk]))
        buckets.append({
            "raw_conf": round(raw_conf, 4),
            "actual_wr": round(actual_wr, 4),
            "count": len(chunk),
        })

    # Enforce monotonicity (isotonic regression via pool adjacent violators)
    if len(buckets) >= 2:
        wrs = [b["actual_wr"] for b in buckets]
        wrs = _pool_adjacent_violators(wrs)
        for i, b in enumerate(buckets):
            b["actual_wr"] = round(wrs[i], 4)

    return {"buckets": buckets, "method": "isotonic", "n_samples": len(pairs)}


def _pool_adjacent_violators(values: list[float]) -> list[float]:
    """
    Pool Adjacent Violators Algorithm (PAVA) for isotonic regression.
    Enforces monotonically non-decreasing sequence.
    """
    n = len(values)
    result = list(values)

    # Forward pass: merge violating pairs
    i = 0
    while i < n - 1:
        if result[i] > result[i + 1]:
            # Pool: average the violating pair
            avg = (result[i] + result[i + 1]) / 2
            result[i] = avg
            result[i + 1] = avg
            # Check backward for new violations
            if i > 0:
                i -= 1
            else:
                i += 1
        else:
            i += 1

    return result


def calibrate_confidence(
    raw_confidence: float,
    calibration_map: Optional[dict] = None,
    temperature: float = 2.0,
) -> float:
    """
    Calibrate a raw model confidence score to actual win probability.

    Priority:
    1. Isotonic calibration if map has sufficient data
    2. Temperature scaling as fallback
    3. Raw confidence with hard cap at 0.85

    Args:
        raw_confidence: model's raw output probability (0-1)
        calibration_map: output of build_calibration_map()
        temperature: temperature for Platt-style scaling (fallback)

    Returns:
        calibrated confidence (0-1)
    """
    raw_confidence = max(0.001, min(0.999, raw_confidence))

    # Try isotonic calibration first
    if calibration_map and calibration_map.get("method") == "isotonic":
        buckets = calibration_map.get("buckets", [])
        if len(buckets) >= 2:
            # Linear interpolation between nearest buckets
            raw_vals = [b["raw_conf"] for b in buckets]
            cal_vals = [b["actual_wr"] for b in buckets]

            # Clamp to range
            if raw_confidence <= raw_vals[0]:
                return max(cal_vals[0], 0.05)
            if raw_confidence >= raw_vals[-1]:
                return min(cal_vals[-1], 0.85)

            # Interpolate
            for i in range(len(raw_vals) - 1):
                if raw_vals[i] <= raw_confidence <= raw_vals[i + 1]:
                    frac = (raw_confidence - raw_vals[i]) / (raw_vals[i + 1] - raw_vals[i] + 1e-10)
                    calibrated = cal_vals[i] + frac * (cal_vals[i + 1] - cal_vals[i])
                    return round(max(0.05, min(0.85, calibrated)), 4)

    # Fallback: temperature scaling
    import math
    logit = math.log(raw_confidence / (1.0 - raw_confidence))
    scaled_logit = logit / temperature
    calibrated = 1.0 / (1.0 + math.exp(-scaled_logit))
    return round(min(calibrated, 0.85), 4)


def save_calibration_map(cal_map: dict):
    """Save calibration map to shared JSON file."""
    os.makedirs(CALIBRATION_DIR, exist_ok=True)
    with open(CALIBRATION_FILE, "w") as f:
        json.dump(cal_map, f, indent=2)


def load_calibration_map() -> Optional[dict]:
    """Load calibration map from shared JSON file."""
    if os.path.exists(CALIBRATION_FILE):
        try:
            with open(CALIBRATION_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return None
