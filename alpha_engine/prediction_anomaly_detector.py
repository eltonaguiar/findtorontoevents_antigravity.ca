"""
ALPHA_ENGINE -- Prediction Anomaly Detector
=============================================
Automated anomaly detection on model predictions and trading metrics.

Five detection modules:
  1. Statistical Process Control (SPC) on win rate (rolling 20-trade window)
  2. Prediction Distribution Monitoring (drift, flat, noisy, PSI)
  3. Isolation Forest via z-score outlier detection (out-of-distribution picks)
  4. Consecutive Pattern Detection (loss streaks, herding)
  5. Unified Alert System with severity-based portfolio sizing

Data files written:
  - data/spc_win_rate.json
  - data/prediction_alerts.json

All functions wrapped in try/except for backwards compatibility.
This module never raises -- it returns safe defaults on error.
"""

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_ENGINE_DIR = Path(__file__).resolve().parent
_DATA_DIR = _ENGINE_DIR / "data"

SPC_PATH = _DATA_DIR / "spc_win_rate.json"
ALERTS_PATH = _DATA_DIR / "prediction_alerts.json"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SPC_WINDOW = 20          # Rolling trade window for SPC
PRED_WINDOW = 100        # Rolling prediction window for distribution monitoring
MEAN_SHIFT_THRESHOLD = 0.1
VARIANCE_FLAT_THRESHOLD = 0.01
VARIANCE_NOISY_THRESHOLD = 0.3
PSI_SIGNIFICANT = 0.20
OOD_ZSCORE_THRESHOLD = 3.0
OOD_CONFIDENCE_PENALTY = 0.05
CONSEC_LOSS_ALARM = 5
HERDING_THRESHOLD = 10
CRITICAL_SIZING_REDUCTION = 0.50


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _load_json(path: Path) -> dict | list:
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_json(path: Path, data) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        print(f"  [ANOMALY] Could not write {path.name}: {e}")


def _safe_float(val, default=0.0) -> float:
    """Safely convert a value to float."""
    if val is None:
        return default
    try:
        v = float(val)
        return default if (math.isnan(v) or math.isinf(v)) else v
    except (ValueError, TypeError):
        return default


# ===================================================================
# 1. STATISTICAL PROCESS CONTROL (SPC) ON WIN RATE
# ===================================================================

def compute_spc_win_rate(closed_picks: list[dict]) -> dict:
    """
    Maintain a rolling 20-trade SPC chart on win rate.

    Returns:
        dict with center_line, ucl, lcl, rolling_wr, alarm status
    """
    try:
        if not closed_picks:
            return {"status": "INSUFFICIENT_DATA", "sample_size": 0}

        # Sort by exit date (most recent last)
        sorted_picks = sorted(
            closed_picks,
            key=lambda p: p.get("exit_date", p.get("closed_at", "")),
        )

        # Compute historical (baseline) win rate from ALL closed picks
        outcomes = [1 if _safe_float(p.get("pnl_pct")) > 0 else 0 for p in sorted_picks]
        total_n = len(outcomes)

        if total_n < SPC_WINDOW:
            return {"status": "INSUFFICIENT_DATA", "sample_size": total_n}

        historical_wr = sum(outcomes) / total_n

        # Rolling window: last SPC_WINDOW trades
        window = outcomes[-SPC_WINDOW:]
        rolling_wr = sum(window) / SPC_WINDOW

        # Control limits: p-chart for proportions
        # sigma = sqrt(p * (1 - p) / n)
        p = max(0.001, min(0.999, historical_wr))  # clamp to avoid div-by-zero
        sigma = math.sqrt(p * (1 - p) / SPC_WINDOW)

        ucl = min(1.0, p + 3 * sigma)
        lcl = max(0.0, p - 3 * sigma)

        # Determine alarm status
        alarm = "NORMAL"
        alarm_detail = ""
        if rolling_wr < lcl:
            alarm = "DEGRADATION"
            alarm_detail = (f"Rolling WR {rolling_wr:.3f} below LCL {lcl:.3f} -- "
                            f"model performance degrading")
        elif rolling_wr > ucl:
            alarm = "INVESTIGATE"
            alarm_detail = (f"Rolling WR {rolling_wr:.3f} above UCL {ucl:.3f} -- "
                            f"possible data leakage or survivorship bias")

        # Build chart data: rolling WR for each window position
        chart_points = []
        for i in range(SPC_WINDOW, total_n + 1):
            w = outcomes[i - SPC_WINDOW:i]
            wr = sum(w) / SPC_WINDOW
            chart_points.append(round(wr, 4))

        spc_data = {
            "status": alarm,
            "detail": alarm_detail,
            "center_line": round(historical_wr, 4),
            "ucl": round(ucl, 4),
            "lcl": round(lcl, 4),
            "rolling_wr": round(rolling_wr, 4),
            "window_size": SPC_WINDOW,
            "total_trades": total_n,
            "chart_points": chart_points[-50:],  # last 50 for chart
            "updated_at": _now_utc().isoformat(),
        }

        _save_json(SPC_PATH, spc_data)
        return spc_data

    except Exception as e:
        print(f"  [SPC] Computation failed (safe fallback): {e}")
        return {"status": "ERROR", "error": str(e)}


# ===================================================================
# 2. PREDICTION DISTRIBUTION MONITORING
# ===================================================================

def monitor_prediction_distribution(active_picks: list[dict],
                                     closed_picks: list[dict]) -> dict:
    """
    Track distribution of ml_scores over time.
    Detect: drift, flat model, noisy model, PSI shift.
    """
    try:
        # Collect ml_scores from all picks
        all_picks = list(closed_picks) + list(active_picks)
        all_picks.sort(key=lambda p: p.get("generated_at", p.get("entry_date", "")))

        scores = []
        for p in all_picks:
            s = p.get("ml_score") or p.get("meta_label_score") or p.get("confidence")
            if s is not None:
                v = _safe_float(s, None)
                if v is not None and 0 <= v <= 1:
                    scores.append(v)

        if len(scores) < PRED_WINDOW:
            return {"status": "INSUFFICIENT_DATA", "sample_size": len(scores)}

        # Baseline: first half of scores
        mid = len(scores) // 2
        baseline = scores[:mid]
        current = scores[-PRED_WINDOW:]

        # Baseline stats
        bl_mean = sum(baseline) / len(baseline)
        bl_var = sum((x - bl_mean) ** 2 for x in baseline) / len(baseline)

        # Current stats
        cur_mean = sum(current) / len(current)
        cur_var = sum((x - cur_mean) ** 2 for x in current) / len(current)

        # Detect anomalies
        alerts = []
        mean_shift = abs(cur_mean - bl_mean)

        if mean_shift > MEAN_SHIFT_THRESHOLD:
            alerts.append({
                "type": "PREDICTION_DRIFT",
                "severity": "WARNING",
                "message": (f"Mean ml_score shifted by {mean_shift:.3f} "
                            f"(baseline={bl_mean:.3f}, current={cur_mean:.3f})"),
            })

        if cur_var < VARIANCE_FLAT_THRESHOLD:
            alerts.append({
                "type": "MODEL_FLAT",
                "severity": "WARNING",
                "message": (f"Prediction variance {cur_var:.4f} < {VARIANCE_FLAT_THRESHOLD} -- "
                            f"model not discriminating between good and bad picks"),
            })

        if cur_var > VARIANCE_NOISY_THRESHOLD:
            alerts.append({
                "type": "MODEL_NOISY",
                "severity": "INFO",
                "message": (f"Prediction variance {cur_var:.4f} > {VARIANCE_NOISY_THRESHOLD} -- "
                            f"model producing highly variable scores"),
            })

        # PSI (Population Stability Index)
        psi = _compute_psi(baseline, current, bins=10)
        if psi > PSI_SIGNIFICANT:
            alerts.append({
                "type": "PSI_SHIFT",
                "severity": "CRITICAL" if psi > 0.40 else "WARNING",
                "message": (f"PSI = {psi:.3f} (threshold {PSI_SIGNIFICANT}) -- "
                            f"prediction distribution has shifted significantly, retrain needed"),
            })

        return {
            "baseline_mean": round(bl_mean, 4),
            "baseline_var": round(bl_var, 4),
            "current_mean": round(cur_mean, 4),
            "current_var": round(cur_var, 4),
            "mean_shift": round(mean_shift, 4),
            "psi": round(psi, 4),
            "sample_size": len(scores),
            "alerts": alerts,
            "updated_at": _now_utc().isoformat(),
        }

    except Exception as e:
        print(f"  [PRED DIST] Monitoring failed (safe fallback): {e}")
        return {"status": "ERROR", "error": str(e)}


def _compute_psi(baseline: list[float], current: list[float], bins: int = 10) -> float:
    """
    Population Stability Index between two distributions.
    PSI = sum( (actual% - expected%) * ln(actual% / expected%) )

    Uses equal-width bins from 0 to 1.
    """
    try:
        epsilon = 1e-6
        bin_edges = [i / bins for i in range(bins + 1)]

        def _histogram(values):
            counts = [0] * bins
            for v in values:
                idx = min(int(v * bins), bins - 1)
                counts[idx] += 1
            total = len(values)
            return [(c / total) + epsilon for c in counts]

        bl_pcts = _histogram(baseline)
        cur_pcts = _histogram(current)

        psi = 0.0
        for actual, expected in zip(cur_pcts, bl_pcts):
            psi += (actual - expected) * math.log(actual / expected)

        return max(0.0, psi)

    except Exception:
        return 0.0


# ===================================================================
# 3. ISOLATION FOREST VIA Z-SCORE (OUT-OF-DISTRIBUTION DETECTION)
# ===================================================================

def check_out_of_distribution(pick: dict, closed_picks: list[dict]) -> dict:
    """
    Pure-Python OOD detection using z-scores on feature vectors.

    For each new pick, compute its feature vector and compare against
    the training distribution. If many features exceed 3 sigma, flag
    as OUT_OF_DISTRIBUTION.

    Returns:
        dict with is_ood, ood_features, confidence_penalty
    """
    try:
        # Extract features from the pick
        pick_features = _extract_features(pick)
        if not pick_features:
            return {"is_ood": False, "reason": "no_features"}

        # Build training distribution from closed picks
        training_features = {}
        for cp in closed_picks:
            feats = _extract_features(cp)
            for k, v in feats.items():
                training_features.setdefault(k, []).append(v)

        if not training_features:
            return {"is_ood": False, "reason": "no_training_data"}

        # Compute z-scores for each feature
        ood_features = []
        checked = 0
        for feat_name, feat_val in pick_features.items():
            train_vals = training_features.get(feat_name, [])
            if len(train_vals) < 5:
                continue  # Need minimum sample

            mean = sum(train_vals) / len(train_vals)
            variance = sum((x - mean) ** 2 for x in train_vals) / len(train_vals)
            std = math.sqrt(variance) if variance > 0 else 0

            if std < 1e-10:
                continue  # Skip constant features

            z = abs(feat_val - mean) / std
            checked += 1

            if z > OOD_ZSCORE_THRESHOLD:
                ood_features.append({
                    "feature": feat_name,
                    "value": round(feat_val, 4),
                    "z_score": round(z, 2),
                    "train_mean": round(mean, 4),
                    "train_std": round(std, 4),
                })

        if checked == 0:
            return {"is_ood": False, "reason": "no_comparable_features"}

        # OOD if more than 30% of features are outliers (or at least 2)
        ood_ratio = len(ood_features) / max(checked, 1)
        is_ood = len(ood_features) >= 2 and ood_ratio > 0.3

        return {
            "is_ood": is_ood,
            "ood_features": ood_features[:10],  # cap detail
            "ood_ratio": round(ood_ratio, 3),
            "features_checked": checked,
            "confidence_penalty": OOD_CONFIDENCE_PENALTY if is_ood else 0.0,
        }

    except Exception as e:
        print(f"  [OOD] Check failed (safe fallback): {e}")
        return {"is_ood": False, "error": str(e)}


def apply_ood_penalties(active_picks: list[dict],
                         closed_picks: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Scan all active picks for OOD and apply confidence reduction.

    Returns:
        (modified_picks, ood_alerts)
    """
    try:
        ood_alerts = []
        for pick in active_picks:
            result = check_out_of_distribution(pick, closed_picks)
            if result.get("is_ood"):
                # Apply confidence penalty
                conf = _safe_float(pick.get("confidence"), 0.5)
                pick["confidence"] = round(max(0.0, conf - OOD_CONFIDENCE_PENALTY), 4)
                pick["ood_flagged"] = True
                pick["ood_details"] = result.get("ood_features", [])

                ood_alerts.append({
                    "type": "OUT_OF_DISTRIBUTION",
                    "severity": "WARNING",
                    "message": (f"{pick.get('symbol', '?')} ({pick.get('strategy', '?')}) "
                                f"is OOD -- {len(result.get('ood_features', []))} features "
                                f"beyond {OOD_ZSCORE_THRESHOLD} sigma, "
                                f"confidence reduced by {OOD_CONFIDENCE_PENALTY}"),
                    "symbol": pick.get("symbol"),
                    "strategy": pick.get("strategy"),
                    "timestamp": _now_utc().isoformat(),
                })

        return active_picks, ood_alerts

    except Exception as e:
        print(f"  [OOD] Penalty application failed (safe fallback): {e}")
        return active_picks, []


def _extract_features(pick: dict) -> dict[str, float]:
    """Extract numeric features from a pick for OOD comparison."""
    features = {}

    # Try ml_features_at_entry first
    ml_feat = pick.get("ml_features_at_entry", {})
    if isinstance(ml_feat, dict):
        for k, v in ml_feat.items():
            fv = _safe_float(v, None)
            if fv is not None:
                features[k] = fv

    # Also extract standard numeric fields
    _NUMERIC_FIELDS = [
        "confidence", "ml_score", "risk_reward", "atr_at_entry",
        "volume_ratio", "rsi_at_entry", "score",
    ]
    for field in _NUMERIC_FIELDS:
        if field not in features:
            v = _safe_float(pick.get(field), None)
            if v is not None:
                features[field] = v

    return features


# ===================================================================
# 4. CONSECUTIVE PATTERN DETECTION
# ===================================================================

def detect_consecutive_patterns(active_picks: list[dict],
                                 closed_picks: list[dict]) -> list[dict]:
    """
    Detect concerning consecutive patterns:
      - 5+ consecutive losses on any strategy (verify risk_controls integration)
      - 10+ consecutive same-direction trades system-wide (herding)

    Returns list of alerts.
    """
    alerts = []
    try:
        if not closed_picks:
            return alerts

        # --- Per-strategy consecutive losses ---
        strat_picks: dict[str, list] = {}
        for p in closed_picks:
            strat = p.get("strategy", "unknown")
            strat_picks.setdefault(strat, []).append(p)

        for strat, picks in strat_picks.items():
            sorted_p = sorted(
                picks,
                key=lambda x: x.get("exit_date", x.get("closed_at", "")),
                reverse=True,
            )
            streak = 0
            for p in sorted_p:
                pnl = _safe_float(p.get("pnl_pct"))
                if pnl < 0:
                    streak += 1
                else:
                    break

            if streak >= CONSEC_LOSS_ALARM:
                alerts.append({
                    "type": "CONSECUTIVE_LOSSES",
                    "severity": "CRITICAL" if streak >= 8 else "WARNING",
                    "message": (f"Strategy '{strat}' has {streak} consecutive losses -- "
                                f"should be auto-paused for 24h (verify risk_controls.py)"),
                    "strategy": strat,
                    "streak": streak,
                    "timestamp": _now_utc().isoformat(),
                })

        # --- System-wide herding detection ---
        # Look at the most recent trades for same-direction clustering
        all_recent = sorted(
            closed_picks + active_picks,
            key=lambda p: p.get("generated_at", p.get("entry_date", "")),
            reverse=True,
        )[:HERDING_THRESHOLD + 5]  # look at last N+5 trades

        if len(all_recent) >= HERDING_THRESHOLD:
            directions = []
            for p in all_recent:
                d = str(p.get("signal_type", p.get("direction", ""))).upper()
                if d in ("LONG", "BUY"):
                    directions.append("LONG")
                elif d in ("SHORT", "SELL"):
                    directions.append("SHORT")

            # Count max consecutive same direction
            if directions:
                max_same = 1
                current_run = 1
                for i in range(1, len(directions)):
                    if directions[i] == directions[i - 1]:
                        current_run += 1
                        max_same = max(max_same, current_run)
                    else:
                        current_run = 1

                if max_same >= HERDING_THRESHOLD:
                    alerts.append({
                        "type": "HERDING_BEHAVIOR",
                        "severity": "WARNING",
                        "message": (f"{max_same} consecutive {directions[0]} trades system-wide -- "
                                    f"possible herding / directional bias"),
                        "direction": directions[0] if directions else "?",
                        "streak": max_same,
                        "timestamp": _now_utc().isoformat(),
                    })

        # --- Consecutive wins detection (sanity check) ---
        all_closed_sorted = sorted(
            closed_picks,
            key=lambda p: p.get("exit_date", p.get("closed_at", "")),
            reverse=True,
        )
        win_streak = 0
        for p in all_closed_sorted:
            if _safe_float(p.get("pnl_pct")) > 0:
                win_streak += 1
            else:
                break
        if win_streak >= 10:
            alerts.append({
                "type": "CONSECUTIVE_WINS",
                "severity": "INFO",
                "message": (f"{win_streak} consecutive wins -- unusual, "
                            f"verify no survivorship bias in data"),
                "streak": win_streak,
                "timestamp": _now_utc().isoformat(),
            })

    except Exception as e:
        print(f"  [PATTERN] Detection failed (safe fallback): {e}")

    return alerts


# ===================================================================
# 5. UNIFIED ALERT SYSTEM
# ===================================================================

def check_all_anomalies(active_picks: list[dict] | None = None,
                         closed_picks: list[dict] | None = None) -> list[dict]:
    """
    Run all anomaly detection modules and return a consolidated alert list.

    Each alert:
        type: str       -- DEGRADATION, PREDICTION_DRIFT, OUT_OF_DISTRIBUTION, etc.
        severity: str   -- INFO, WARNING, CRITICAL
        message: str    -- human-readable description
        timestamp: str  -- ISO-8601 UTC

    CRITICAL alerts imply portfolio sizing should be reduced by 50%.
    """
    all_alerts = []

    try:
        # Load picks from disk if not provided
        if active_picks is None:
            raw = _load_json(_DATA_DIR / "active_picks.json")
            active_picks = raw if isinstance(raw, list) else []
        if closed_picks is None:
            raw = _load_json(_DATA_DIR / "closed_picks.json")
            closed_picks = raw if isinstance(raw, list) else []

        now_str = _now_utc().isoformat()

        # 1. SPC on win rate
        spc = compute_spc_win_rate(closed_picks)
        if spc.get("status") == "DEGRADATION":
            all_alerts.append({
                "type": "SPC_DEGRADATION",
                "severity": "CRITICAL",
                "message": spc.get("detail", "Win rate below lower control limit"),
                "timestamp": now_str,
            })
        elif spc.get("status") == "INVESTIGATE":
            all_alerts.append({
                "type": "SPC_INVESTIGATE",
                "severity": "WARNING",
                "message": spc.get("detail", "Win rate above upper control limit"),
                "timestamp": now_str,
            })

        # 2. Prediction distribution
        pred_dist = monitor_prediction_distribution(active_picks, closed_picks)
        for alert in pred_dist.get("alerts", []):
            alert["timestamp"] = now_str
            all_alerts.append(alert)

        # 3. OOD detection (apply penalties in-place)
        active_picks, ood_alerts = apply_ood_penalties(active_picks, closed_picks)
        all_alerts.extend(ood_alerts)

        # 4. Consecutive pattern detection
        pattern_alerts = detect_consecutive_patterns(active_picks, closed_picks)
        all_alerts.extend(pattern_alerts)

        # Compute summary
        critical_count = sum(1 for a in all_alerts if a.get("severity") == "CRITICAL")
        warning_count = sum(1 for a in all_alerts if a.get("severity") == "WARNING")

        sizing_multiplier = 1.0
        if critical_count > 0:
            sizing_multiplier = CRITICAL_SIZING_REDUCTION
            print(f"  [ANOMALY] {critical_count} CRITICAL alert(s) -- "
                  f"portfolio sizing reduced to {CRITICAL_SIZING_REDUCTION * 100:.0f}%")

        result = {
            "alerts": all_alerts,
            "summary": {
                "total_alerts": len(all_alerts),
                "critical": critical_count,
                "warning": warning_count,
                "info": len(all_alerts) - critical_count - warning_count,
                "sizing_multiplier": sizing_multiplier,
            },
            "spc": {
                "status": spc.get("status", "N/A"),
                "rolling_wr": spc.get("rolling_wr"),
                "center_line": spc.get("center_line"),
            },
            "prediction_dist": {
                "psi": pred_dist.get("psi"),
                "mean_shift": pred_dist.get("mean_shift"),
                "current_var": pred_dist.get("current_var"),
            },
            "updated_at": now_str,
        }

        # Save alerts to disk
        _save_json(ALERTS_PATH, result)

        if all_alerts:
            print(f"  [ANOMALY] {len(all_alerts)} alert(s): "
                  f"{critical_count} CRITICAL, {warning_count} WARNING, "
                  f"{len(all_alerts) - critical_count - warning_count} INFO")
        else:
            print("  [ANOMALY] No anomalies detected")

        return all_alerts

    except Exception as e:
        print(f"  [ANOMALY] check_all_anomalies failed (safe fallback): {e}")
        return []


def get_sizing_multiplier() -> float:
    """
    Read the last saved alerts and return the sizing multiplier.
    1.0 = normal, 0.5 = CRITICAL alert active.

    Safe to call from any module (never raises).
    """
    try:
        data = _load_json(ALERTS_PATH)
        if isinstance(data, dict):
            return data.get("summary", {}).get("sizing_multiplier", 1.0)
    except Exception:
        pass
    return 1.0


def get_active_alerts() -> list[dict]:
    """
    Return the list of currently active alerts from the last check.
    Safe to call from any module (never raises).
    """
    try:
        data = _load_json(ALERTS_PATH)
        if isinstance(data, dict):
            return data.get("alerts", [])
    except Exception:
        pass
    return []
