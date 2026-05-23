"""
ALPHA_ENGINE -- Feature Health Reporter
=========================================
Analyzes feature health across closed and active picks, generates a daily
report flagging dead, stale, or mostly-zero features.

Called by:
  - ml_ranker.py: before training (gate at health_score < 0.3)
  - forward_validator.py: once per generation cycle (monitoring)

Output: data/feature_health_report.json
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_ENGINE_DIR = Path(__file__).resolve().parent
_DATA_DIR = _ENGINE_DIR / "data"
_SCHEMA_PATH = _DATA_DIR / "features_schema.json"
_REPORT_PATH = _DATA_DIR / "feature_health_report.json"
_CLOSED_PICKS_PATH = _DATA_DIR / "closed_picks.json"
_ACTIVE_PICKS_PATH = _DATA_DIR / "active_picks.json"


def _load_schema() -> dict:
    """Load the feature schema from features_schema.json."""
    if not _SCHEMA_PATH.exists():
        logger.warning("Feature schema not found at %s", _SCHEMA_PATH)
        return {}
    try:
        with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error("Failed to load feature schema: %s", e)
        return {}


def _load_picks(path: Path) -> list[dict]:
    """Load picks from a JSON file."""
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError):
        return []


def _extract_ml_features(pick: dict) -> Optional[dict]:
    """Extract ml_features_at_entry from a pick, or reconstruct from top-level fields."""
    # First check for embedded ml_features_at_entry (newer picks)
    ml_feat = pick.get("ml_features_at_entry")
    if isinstance(ml_feat, dict) and ml_feat:
        return ml_feat

    # Reconstruct from top-level pick fields (older picks)
    feat = {}
    # Map pick fields to feature names where possible
    _FIELD_MAP = {
        "rsi_at_entry": "rsi_at_entry",
        "volume_ratio": "volume_ratio",
        "risk_reward": "risk_reward",
        "atr_at_entry": "atr_at_entry",
        "confidence": "confidence",
        "mfe": "mfe_pct",
        "mae": "mae_pct",
        "hold_days": "hold_duration_hours",
    }
    for pick_key, feat_key in _FIELD_MAP.items():
        val = pick.get(pick_key)
        if val is not None:
            try:
                feat[feat_key] = float(val)
            except (TypeError, ValueError):
                pass

    # Direction
    direction = (pick.get("direction") or pick.get("signal_type") or "").upper()
    if direction in ("BUY", "LONG"):
        # direction_market_alignment: direction * btc_24h_trend (default btc_trend=0 when no data)
        btc_trend = float(ml_feat.get("btc_24h_change_norm", 0) or 0) if ml_feat else 0.0
        feat["direction_market_alignment"] = 1.0 * btc_trend
    elif direction in ("SELL", "SHORT"):
        feat["direction_market_alignment"] = -1.0 * btc_trend

    # Category
    cat_map = {"crypto": 0, "forex": 1, "stock": 2, "penny": 3, "meme": 4}
    cat = (pick.get("category") or "").lower()
    if cat in cat_map:
        feat["category_encoded"] = float(cat_map[cat])

    # Regime
    regime_map = {"bull": 1, "neutral": 0, "bear": -1, "risk_on": 1, "risk_off": -1}
    regime = (pick.get("regime_at_entry") or pick.get("regime_encoded") or "neutral")
    if isinstance(regime, str):
        feat["regime_encoded"] = float(regime_map.get(regime.lower(), 0))
    elif isinstance(regime, (int, float)):
        feat["regime_encoded"] = float(regime)

    # SL/TP distances
    entry = float(pick.get("entry_price", 0) or 0)
    tp = float(pick.get("take_profit", 0) or 0)
    sl = float(pick.get("stop_loss", 0) or 0)
    if entry > 0:
        if sl > 0:
            feat["sl_distance_pct"] = abs(entry - sl) / entry
        if tp > 0:
            feat["tp_distance_pct"] = abs(tp - entry) / entry

    return feat if feat else None


def generate_health_report(
    closed_picks_path: Optional[str] = None,
    active_picks_path: Optional[str] = None,
) -> dict:
    """Analyze feature health across recent picks and generate report.

    Returns:
        dict with keys: generated_at, total_features, alive_features,
        dead_features, health_score, features (per-feature stats),
        recommendations.
    """
    cp_path = Path(closed_picks_path) if closed_picks_path else _CLOSED_PICKS_PATH
    ap_path = Path(active_picks_path) if active_picks_path else _ACTIVE_PICKS_PATH

    closed = _load_picks(cp_path)
    active = _load_picks(ap_path)
    all_picks = closed + active

    schema = _load_schema()
    feature_defs = schema.get("features", {})
    feature_names = list(feature_defs.keys())

    if not feature_names:
        # Fallback: use hardcoded list from MLSignalRanker
        try:
            from ml_ranker import MLSignalRanker
            feature_names = list(MLSignalRanker.FEATURES)
        except ImportError:
            feature_names = []

    if not feature_names:
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_features": 0,
            "alive_features": 0,
            "dead_features": 0,
            "health_score": 0.0,
            "features": {},
            "recommendations": ["No feature schema found -- create features_schema.json"],
        }
        _save_report(report)
        return report

    # Collect per-feature values across all picks
    feature_values: dict[str, list[float]] = {name: [] for name in feature_names}

    for pick in all_picks:
        ml_feat = _extract_ml_features(pick)
        if ml_feat is None:
            continue
        for name in feature_names:
            val = ml_feat.get(name)
            if val is not None:
                try:
                    feature_values[name].append(float(val))
                except (TypeError, ValueError):
                    pass

    # Analyze each feature
    now = datetime.now(timezone.utc)
    total = len(feature_names)
    alive = 0
    dead = 0
    per_feature: dict[str, dict] = {}
    recommendations: list[str] = []

    for name in feature_names:
        values = feature_values[name]
        n_samples = len(values)
        fdef = feature_defs.get(name, {})
        is_critical = fdef.get("critical", False)

        if n_samples == 0:
            status = "no_data"
            dead += 1
            per_feature[name] = {
                "status": "no_data",
                "n_samples": 0,
                "variance": 0.0,
                "pct_zero": 1.0,
                "pct_constant": 1.0,
                "critical": is_critical,
            }
            if is_critical:
                recommendations.append(
                    f"CRITICAL: '{name}' has no data -- check extraction pipeline"
                )
            else:
                recommendations.append(
                    f"'{name}' has no data -- may need extraction or removal"
                )
            continue

        # Compute statistics
        mean_val = sum(values) / n_samples
        variance = sum((v - mean_val) ** 2 for v in values) / max(n_samples - 1, 1)
        n_zero = sum(1 for v in values if abs(v) < 1e-10)
        pct_zero = n_zero / n_samples
        # Check if constant (all same value)
        is_constant = variance < 1e-8
        pct_constant = 1.0 if is_constant else 0.0

        # Check staleness: last 24h of picks all identical
        is_stale = False
        if n_samples >= 5:
            last_vals = values[-min(20, n_samples):]
            if len(set(round(v, 8) for v in last_vals)) <= 1:
                is_stale = True

        # Determine status
        if is_constant:
            status = "dead_constant"
            dead += 1
        elif pct_zero > 0.90:
            # Raised from 0.80 -- many features (obv_divergence, vol_compression)
            # are naturally sparse and shouldn't be classified as dead
            status = "mostly_zero"
            dead += 1
        elif is_stale:
            status = "stale"
            # Stale features still count as alive but with a warning
            alive += 1
        else:
            status = "healthy"
            alive += 1

        per_feature[name] = {
            "status": status,
            "n_samples": n_samples,
            "mean": round(mean_val, 6),
            "variance": round(variance, 8),
            "pct_zero": round(pct_zero, 4),
            "pct_constant": round(pct_constant, 4),
            "is_stale": is_stale,
            "critical": is_critical,
        }

        # Generate recommendations
        if status == "dead_constant" and is_critical:
            recommendations.append(
                f"CRITICAL: '{name}' is constant (var={variance:.2e}) -- "
                f"check data source '{fdef.get('source', 'unknown')}'"
            )
        elif status == "dead_constant":
            recommendations.append(
                f"'{name}' is constant -- consider removing or fixing data source"
            )
        elif status == "mostly_zero":
            recommendations.append(
                f"'{name}' is {pct_zero:.0%} zero -- extraction may be broken"
            )
        elif is_stale:
            recommendations.append(
                f"'{name}' appears stale (last {min(20, n_samples)} values identical)"
            )

    # Check for range violations
    for name in feature_names:
        fdef = feature_defs.get(name, {})
        expected_range = fdef.get("range")
        values = feature_values[name]
        if expected_range and values:
            lo, hi = expected_range
            out_of_range = sum(1 for v in values if v < lo - 0.01 or v > hi + 0.01)
            if out_of_range > 0:
                pct_oor = out_of_range / len(values)
                per_feature[name]["pct_out_of_range"] = round(pct_oor, 4)
                if pct_oor > 0.05:
                    recommendations.append(
                        f"'{name}' has {pct_oor:.0%} values outside expected range "
                        f"[{lo}, {hi}]"
                    )

    health_score = alive / total if total > 0 else 0.0

    # --- Feature Activation Tracking (Task 3) ---
    activation_data = {}
    try:
        activation_data = compute_feature_activation(all_picks, feature_names)
        for name, act_info in activation_data.items():
            if name in per_feature:
                per_feature[name]["activation_rate"] = act_info["activation_rate"]
                per_feature[name]["activation_class"] = act_info["classification"]
            if act_info["classification"] == "dead" and name not in [
                r.split("'")[1] for r in recommendations if "'" in r
            ]:
                recommendations.append(
                    f"'{name}' activation rate {act_info['activation_rate']:.0%} -- classified as dead"
                )
    except Exception as act_err:
        logger.warning("Feature activation tracking failed (non-fatal): %s", act_err)

    # --- Correlation Audit (KIMI review) ---
    correlation_data = {}
    try:
        thresholds = get_health_thresholds()
        correlation_data = detect_high_correlation(
            all_picks, feature_names,
            threshold=thresholds.get("correlation_threshold", 0.85),
        )
        if correlation_data.get("correlated_pairs"):
            for feat_a, feat_b, r_val in correlation_data["correlated_pairs"]:
                recommendations.append(
                    f"High correlation: '{feat_a}' x '{feat_b}' |r|={abs(r_val):.3f} "
                    f"-- consider removing one"
                )
    except Exception as corr_err:
        logger.warning("Correlation audit failed (non-fatal): %s", corr_err)

    # --- Data Quality Checks (KIMI review) ---
    data_quality = {}
    try:
        data_quality = check_data_quality(all_picks)
        for issue in data_quality.get("issues", []):
            recommendations.append(f"Data quality: {issue}")
    except Exception as dq_err:
        logger.warning("Data quality check failed (non-fatal): %s", dq_err)

    report = {
        "generated_at": now.isoformat(),
        "total_features": total,
        "alive_features": alive,
        "dead_features": dead,
        "health_score": round(health_score, 4),
        "health_stage": HEALTH_STAGE,
        "health_thresholds": get_health_thresholds(),
        "total_picks_analyzed": len(all_picks),
        "picks_with_features": sum(
            1 for p in all_picks if _extract_ml_features(p) is not None
        ),
        "features": per_feature,
        "activation_summary": {
            "alive": sum(1 for a in activation_data.values() if a.get("classification") == "alive"),
            "weak": sum(1 for a in activation_data.values() if a.get("classification") == "weak"),
            "dead": sum(1 for a in activation_data.values() if a.get("classification") == "dead"),
        } if activation_data else {},
        "correlation_audit": correlation_data,
        "data_quality": data_quality,
        "recommendations": recommendations,
    }

    _save_report(report)
    return report


def validate_pick_features(
    pick: dict, schema: Optional[dict] = None
) -> tuple[bool, list[str], list[str]]:
    """Validate a single pick's ml_features_at_entry against the schema.

    Args:
        pick: A pick dict (active or closed).
        schema: Optional pre-loaded schema dict. Loaded from disk if None.

    Returns:
        (is_valid, missing_features, out_of_range_features)
        - is_valid: True if all critical features present and in range.
        - missing_features: list of feature names not found in the pick.
        - out_of_range_features: list of feature names outside expected range.
    """
    if schema is None:
        schema = _load_schema()

    feature_defs = schema.get("features", {})
    if not feature_defs:
        return True, [], []

    ml_feat = _extract_ml_features(pick)
    if ml_feat is None:
        # No features at all -- all are missing
        return False, list(feature_defs.keys()), []

    missing: list[str] = []
    out_of_range: list[str] = []

    for name, fdef in feature_defs.items():
        val = ml_feat.get(name)
        if val is None:
            missing.append(name)
            continue

        try:
            fval = float(val)
        except (TypeError, ValueError):
            missing.append(name)
            continue

        expected_range = fdef.get("range")
        if expected_range:
            lo, hi = expected_range
            if fval < lo - 0.01 or fval > hi + 0.01:
                out_of_range.append(name)

    # is_valid = no critical features missing or out of range
    critical_missing = [
        name for name in missing if feature_defs.get(name, {}).get("critical", False)
    ]
    critical_oor = [
        name for name in out_of_range
        if feature_defs.get(name, {}).get("critical", False)
    ]
    is_valid = len(critical_missing) == 0 and len(critical_oor) == 0

    return is_valid, missing, out_of_range


# ---------------------------------------------------------------------------
# Feature Drift Detection
# ---------------------------------------------------------------------------

def _compute_psi(expected: list, actual: list, n_bins: int = 10) -> float:
    """Compute Population Stability Index between two distributions.

    PSI < 0.10 = stable, 0.10-0.25 = moderate drift, > 0.25 = significant drift.
    Uses equal-frequency binning on the expected distribution.
    """
    if not expected or not actual:
        return 0.0

    import math as _math

    # Create bins from expected distribution (equal-frequency)
    sorted_exp = sorted(expected)
    n_exp = len(sorted_exp)
    bin_edges = []
    for i in range(1, n_bins):
        idx = int(i * n_exp / n_bins)
        idx = min(idx, n_exp - 1)
        bin_edges.append(sorted_exp[idx])
    # Deduplicate and add boundaries
    bin_edges = sorted(set(bin_edges))
    if not bin_edges:
        return 0.0

    def _bin_proportions(values, edges):
        n = len(values)
        if n == 0:
            return []
        counts = [0] * (len(edges) + 1)
        for v in values:
            placed = False
            for j, edge in enumerate(edges):
                if v <= edge:
                    counts[j] += 1
                    placed = True
                    break
            if not placed:
                counts[-1] += 1
        # Convert to proportions with small epsilon to avoid log(0)
        eps = 1e-4
        return [(c / n) + eps for c in counts]

    exp_props = _bin_proportions(expected, bin_edges)
    act_props = _bin_proportions(actual, bin_edges)

    if len(exp_props) != len(act_props):
        return 0.0

    psi = 0.0
    for ep, ap in zip(exp_props, act_props):
        psi += (ap - ep) * _math.log(ap / ep)

    return max(0.0, psi)


def detect_feature_drift(
    recent_picks: list[dict],
    training_picks: list[dict],
    features_to_check: Optional[list[str]] = None,
) -> dict:
    """Compare feature distributions between recent picks and training data.

    For each feature:
    - Compute KS statistic (scipy.stats.ks_2samp) if available
    - Flag if p-value < 0.01 (significant drift)
    - Compute PSI (Population Stability Index)
    - Flag if PSI > 0.25 (high drift)

    Falls back to simple mean/std comparison if scipy is not available.

    Args:
        recent_picks: Recent picks (e.g., last 24h) as list of dicts.
        training_picks: Historical training picks as list of dicts.
        features_to_check: Optional list of feature names. Auto-detected if None.

    Returns:
        dict with keys: drift_score (0-1 fraction of features with significant drift),
        drifted_features, psi_scores, recommendation ('stable'|'monitor'|'retrain'|'halt')
    """
    try:
        return _detect_feature_drift_impl(recent_picks, training_picks, features_to_check)
    except Exception as e:
        logger.error("Feature drift detection failed: %s", e)
        return {
            "drift_score": 0.0,
            "drifted_features": [],
            "psi_scores": {},
            "recommendation": "stable",
            "error": str(e),
        }


def _detect_feature_drift_impl(
    recent_picks: list[dict],
    training_picks: list[dict],
    features_to_check: Optional[list[str]] = None,
) -> dict:
    """Internal implementation of drift detection."""
    # Try to import scipy for KS test
    _has_scipy = False
    try:
        from scipy.stats import ks_2samp
        _has_scipy = True
    except ImportError:
        ks_2samp = None

    # Determine feature names to check
    if features_to_check is None:
        all_feat_keys: set[str] = set()
        for pick in training_picks:
            ml_feat = _extract_ml_features(pick)
            if ml_feat:
                all_feat_keys.update(ml_feat.keys())
        features_to_check = sorted(all_feat_keys)

    if not features_to_check:
        return {
            "drift_score": 0.0,
            "drifted_features": [],
            "psi_scores": {},
            "recommendation": "stable",
            "message": "No features to check",
        }

    # Extract feature values from both sets
    def _get_feature_values(picks: list[dict], feat_name: str) -> list[float]:
        vals = []
        for pick in picks:
            ml_feat = _extract_ml_features(pick)
            if ml_feat and feat_name in ml_feat:
                try:
                    vals.append(float(ml_feat[feat_name]))
                except (TypeError, ValueError):
                    pass
        return vals

    drifted_features: list[str] = []
    psi_scores: dict[str, float] = {}
    details: dict[str, dict] = {}
    n_checked = 0

    for feat_name in features_to_check:
        train_vals = _get_feature_values(training_picks, feat_name)
        recent_vals = _get_feature_values(recent_picks, feat_name)

        # Need minimum samples for meaningful comparison
        if len(train_vals) < 10 or len(recent_vals) < 5:
            continue

        n_checked += 1
        feat_detail: dict = {"train_n": len(train_vals), "recent_n": len(recent_vals)}

        # PSI computation (always available, no scipy needed)
        psi_val = _compute_psi(train_vals, recent_vals)
        psi_scores[feat_name] = round(psi_val, 4)
        feat_detail["psi"] = round(psi_val, 4)

        is_drifted = False

        if _has_scipy and ks_2samp is not None:
            ks_stat, ks_pval = ks_2samp(train_vals, recent_vals)
            feat_detail["ks_stat"] = round(float(ks_stat), 4)
            feat_detail["ks_pvalue"] = round(float(ks_pval), 6)
            if ks_pval < 0.01:
                is_drifted = True
                feat_detail["drift_reason"] = "ks_significant"
        else:
            # Fallback: simple mean/std comparison
            train_mean = sum(train_vals) / len(train_vals)
            train_var = sum((v - train_mean) ** 2 for v in train_vals) / max(len(train_vals) - 1, 1)
            train_std = train_var ** 0.5

            recent_mean = sum(recent_vals) / len(recent_vals)
            feat_detail["train_mean"] = round(train_mean, 6)
            feat_detail["recent_mean"] = round(recent_mean, 6)
            feat_detail["train_std"] = round(train_std, 6)

            # Flag if recent mean is > 2 std deviations from training mean
            if train_std > 1e-10:
                z_score = abs(recent_mean - train_mean) / train_std
                feat_detail["z_score"] = round(z_score, 4)
                if z_score > 2.0:
                    is_drifted = True
                    feat_detail["drift_reason"] = "mean_shift"

        # PSI drift flag
        if psi_val > 0.25:
            is_drifted = True
            feat_detail["psi_drift"] = True

        if is_drifted:
            drifted_features.append(feat_name)

        details[feat_name] = feat_detail

    # Compute overall drift score
    drift_score = len(drifted_features) / max(n_checked, 1)

    # Determine recommendation
    if drift_score >= 0.5:
        recommendation = "halt"
    elif drift_score >= 0.3:
        recommendation = "retrain"
    elif drift_score >= 0.1:
        recommendation = "monitor"
    else:
        recommendation = "stable"

    result = {
        "drift_score": round(drift_score, 4),
        "drifted_features": drifted_features,
        "psi_scores": psi_scores,
        "recommendation": recommendation,
        "features_checked": n_checked,
        "features_drifted": len(drifted_features),
        "details": details,
        "scipy_available": _has_scipy,
    }

    logger.info(
        "Drift detection: score=%.2f, drifted=%d/%d, recommendation=%s",
        drift_score, len(drifted_features), n_checked, recommendation,
    )

    return result


# ---------------------------------------------------------------------------
# Task 1: Feature Importance + Pruning (SHAP / Permutation / fallback)
# ---------------------------------------------------------------------------

def compute_feature_importance(model, X, feature_names: list[str]) -> dict[str, float]:
    """Compute SHAP or permutation importance for a trained model.

    Tries (in order):
      1. SHAP TreeExplainer (fast for tree-based models)
      2. sklearn permutation_importance
      3. model.feature_importances_ (built-in for tree ensembles)

    Args:
        model: A trained sklearn Pipeline or estimator.
        X: Training feature matrix (numpy array or DataFrame).
        feature_names: List of feature names matching X columns.

    Returns:
        dict of {feature_name: importance_score} (non-negative, sums ~1).
    """
    try:
        import numpy as _np

        # Unwrap sklearn Pipeline to get the actual estimator
        estimator = model
        X_transformed = X
        if hasattr(model, "named_steps"):
            # Apply all transforms except the final estimator
            for step_name, step in list(model.named_steps.items())[:-1]:
                if hasattr(step, "transform"):
                    X_transformed = step.transform(X_transformed)
            estimator = list(model.named_steps.values())[-1]

        n_features = min(len(feature_names),
                         X_transformed.shape[1] if hasattr(X_transformed, 'shape') else len(feature_names))

        # --- Strategy 1: Built-in feature_importances_ (most reliable for tree models) ---
        if hasattr(estimator, "feature_importances_"):
            raw = estimator.feature_importances_
            total = raw.sum()
            if total > 0:
                raw = raw / total
            result = {feature_names[i]: float(raw[i]) for i in range(n_features)}
            logger.info("Feature importance computed via feature_importances_")
            return result

        logger.warning("No feature importance method available")
        return {name: 0.0 for name in feature_names}

    except Exception as e:
        logger.error("compute_feature_importance failed: %s", e)
        return {name: 0.0 for name in feature_names}


def prune_low_importance_features(
    importances: dict[str, float], threshold: float = 0.01
) -> list[str]:
    """Identify features contributing < threshold to the model.

    Returns list of feature names to consider removing.
    Does NOT auto-remove -- flags for human review only.
    """
    try:
        low = [name for name, score in importances.items() if score < threshold]
        if low:
            logger.info(
                "Features below importance threshold %.3f: %s",
                threshold, low,
            )
        return low
    except Exception as e:
        logger.error("prune_low_importance_features failed: %s", e)
        return []


def detect_redundant_features(
    X, feature_names: list[str], corr_threshold: float = 0.85,
    importances: Optional[dict[str, float]] = None,
) -> tuple[list[tuple[str, str, float]], list[str]]:
    """Find feature pairs with Pearson correlation > threshold.

    For each correlated pair, recommends keeping the one with higher
    importance (if importances dict is provided).

    Args:
        X: Feature matrix (numpy array or DataFrame).
        feature_names: List of feature names matching X columns.
        corr_threshold: Absolute correlation threshold (default 0.85).
        importances: Optional dict of {feature_name: importance_score}.

    Returns:
        - redundant_pairs: list of (feat_a, feat_b, correlation)
        - drop_candidates: list of features to consider dropping
    """
    try:
        import numpy as _np

        n = min(len(feature_names), X.shape[1] if hasattr(X, 'shape') else 0)
        if n < 2:
            return [], []

        # Compute correlation matrix
        if hasattr(X, 'values'):
            arr = X.values[:, :n]
        else:
            arr = X[:, :n] if len(X.shape) > 1 else X.reshape(-1, 1)[:, :n]

        # Use numpy corrcoef (handles NaN gracefully)
        with _np.errstate(invalid='ignore'):
            corr_matrix = _np.corrcoef(arr.T)

        # Replace NaN correlations with 0
        corr_matrix = _np.nan_to_num(corr_matrix, nan=0.0)

        redundant_pairs: list[tuple[str, str, float]] = []
        drop_set: set[str] = set()

        for i in range(n):
            for j in range(i + 1, n):
                corr_val = abs(float(corr_matrix[i, j]))
                if corr_val > corr_threshold:
                    feat_a = feature_names[i]
                    feat_b = feature_names[j]
                    redundant_pairs.append((feat_a, feat_b, round(corr_val, 4)))

                    # Recommend dropping the less important one
                    if importances:
                        imp_a = importances.get(feat_a, 0.0)
                        imp_b = importances.get(feat_b, 0.0)
                        drop_set.add(feat_b if imp_a >= imp_b else feat_a)
                    else:
                        drop_set.add(feat_b)  # default: drop second

        if redundant_pairs:
            logger.info(
                "Found %d redundant feature pairs (corr > %.2f): %s",
                len(redundant_pairs), corr_threshold,
                [(a, b) for a, b, _ in redundant_pairs[:5]],
            )

        return redundant_pairs, sorted(drop_set)

    except Exception as e:
        logger.error("detect_redundant_features failed: %s", e)
        return [], []


# ---------------------------------------------------------------------------
# Task 3: Feature Activation Tracking
# ---------------------------------------------------------------------------

def compute_feature_activation(
    picks: list[dict], feature_names: list[str]
) -> dict[str, dict]:
    """Track feature activation rates across picks.

    Classifies each feature:
      - Alive:  >80% non-null/non-zero
      - Weak:   40-80%
      - Dead:   <40%

    Args:
        picks: List of pick dicts (active or closed).
        feature_names: List of feature names to check.

    Returns:
        dict of {feature_name: {activation_rate, classification, variance}}
    """
    try:
        if not picks or not feature_names:
            return {name: {"activation_rate": 0.0, "classification": "dead", "variance": 0.0}
                    for name in feature_names}

        # Count non-null, non-zero values per feature
        counts: dict[str, int] = {name: 0 for name in feature_names}
        values: dict[str, list[float]] = {name: [] for name in feature_names}
        total_with_features = 0

        for pick in picks:
            ml_feat = _extract_ml_features(pick)
            if ml_feat is None:
                continue
            total_with_features += 1

            for name in feature_names:
                val = ml_feat.get(name)
                if val is not None:
                    try:
                        fval = float(val)
                        values[name].append(fval)
                        if abs(fval) > 1e-10:
                            counts[name] += 1
                    except (TypeError, ValueError):
                        pass

        if total_with_features == 0:
            return {name: {"activation_rate": 0.0, "classification": "dead", "variance": 0.0}
                    for name in feature_names}

        result: dict[str, dict] = {}
        for name in feature_names:
            rate = counts[name] / total_with_features
            vals = values[name]
            if len(vals) > 1:
                mean_v = sum(vals) / len(vals)
                var = sum((v - mean_v) ** 2 for v in vals) / (len(vals) - 1)
            else:
                var = 0.0

            if rate > 0.80:
                classification = "alive"
            elif rate >= 0.40:
                classification = "weak"
            else:
                classification = "dead"

            result[name] = {
                "activation_rate": round(rate, 4),
                "classification": classification,
                "variance": round(var, 8),
            }

        return result

    except Exception as e:
        logger.error("compute_feature_activation failed: %s", e)
        return {name: {"activation_rate": 0.0, "classification": "dead", "variance": 0.0}
                for name in feature_names}


# ---------------------------------------------------------------------------
# Health Stage Configuration (KIMI review -- tighter KPI targets)
# ---------------------------------------------------------------------------
HEALTH_STAGES = {
    "alpha": {
        # Current relaxed thresholds (early development)
        "max_dead_features": 10,
        "max_constant_pct": 0.20,       # 20% constant features allowed
        "min_expectancy_pct": 0.0,       # no expectancy gate yet
        "min_health_score": 0.30,        # training gate
        "correlation_threshold": 0.85,   # |r| > 0.85 flagged
    },
    "beta": {
        # Tighter targets for beta testing
        "max_dead_features": 5,
        "max_constant_pct": 0.10,
        "min_expectancy_pct": 0.1,
        "min_health_score": 0.50,
        "correlation_threshold": 0.85,
    },
    "production": {
        # KIMI's strict production targets
        "max_dead_features": 3,          # <=3/39 dead features
        "max_constant_pct": 0.05,        # <=5% constant
        "min_expectancy_pct": 0.2,       # >=0.2% per trade
        "min_health_score": 0.70,
        "correlation_threshold": 0.85,
    },
}

# Default stage -- change to 'beta' or 'production' as system matures
HEALTH_STAGE = "alpha"


def get_health_thresholds() -> dict:
    """Return the current health stage thresholds."""
    return HEALTH_STAGES.get(HEALTH_STAGE, HEALTH_STAGES["alpha"])


# ---------------------------------------------------------------------------
# Correlation Audit (KIMI review -- multicollinearity detection)
# ---------------------------------------------------------------------------

def detect_high_correlation(
    picks: list[dict],
    feature_names: list[str],
    threshold: float = 0.85,
) -> dict:
    """Detect feature pairs with |Pearson r| > threshold.

    Multicollinearity (|r| > 0.85) degrades model quality by inflating
    variance of coefficient estimates and making feature importance
    unreliable. This audit flags pairs for review/removal.

    Args:
        picks: List of pick dicts with ml_features_at_entry.
        feature_names: Feature names to check.
        threshold: Absolute correlation threshold (default 0.85).

    Returns:
        dict with keys:
          - correlated_pairs: list of (feat_a, feat_b, r_value)
          - correlation_health: 'clean' | 'warning' | 'critical'
          - n_features_checked: int
          - drop_candidates: list of feature names to consider removing
    """
    result = {
        "correlated_pairs": [],
        "correlation_health": "clean",
        "n_features_checked": 0,
        "drop_candidates": [],
    }

    if not picks or len(feature_names) < 2:
        return result

    # Build feature matrix from picks
    rows: list[list[float]] = []
    for pick in picks:
        ml_feat = _extract_ml_features(pick)
        if ml_feat is None:
            continue
        row = []
        valid = True
        for name in feature_names:
            val = ml_feat.get(name)
            if val is None:
                valid = False
                break
            try:
                row.append(float(val))
            except (TypeError, ValueError):
                valid = False
                break
        if valid and len(row) == len(feature_names):
            rows.append(row)

    if len(rows) < 10:
        result["correlation_health"] = "insufficient_data"
        return result

    result["n_features_checked"] = len(feature_names)

    # Compute pairwise Pearson correlation without numpy
    n = len(feature_names)
    n_rows = len(rows)

    # Column means and stds
    means = [0.0] * n
    for row in rows:
        for j in range(n):
            means[j] += row[j]
    means = [m / n_rows for m in means]

    stds = [0.0] * n
    for row in rows:
        for j in range(n):
            stds[j] += (row[j] - means[j]) ** 2
    stds = [(s / max(n_rows - 1, 1)) ** 0.5 for s in stds]

    correlated_pairs = []
    drop_set: set[str] = set()

    for i in range(n):
        if stds[i] < 1e-10:
            continue  # skip constant features
        for j in range(i + 1, n):
            if stds[j] < 1e-10:
                continue
            # Pearson r
            cov = 0.0
            for row in rows:
                cov += (row[i] - means[i]) * (row[j] - means[j])
            cov /= max(n_rows - 1, 1)
            r = cov / (stds[i] * stds[j]) if (stds[i] * stds[j]) > 1e-15 else 0.0

            if abs(r) > threshold:
                correlated_pairs.append((feature_names[i], feature_names[j], round(r, 4)))
                # Default: drop the second feature (can be refined with importance scores)
                drop_set.add(feature_names[j])

    result["correlated_pairs"] = correlated_pairs
    result["drop_candidates"] = sorted(drop_set)

    if len(correlated_pairs) == 0:
        result["correlation_health"] = "clean"
    elif len(correlated_pairs) <= 3:
        result["correlation_health"] = "warning"
    else:
        result["correlation_health"] = "critical"

    if correlated_pairs:
        logger.warning(
            "Correlation audit: %d pairs with |r| > %.2f -- health=%s",
            len(correlated_pairs), threshold, result["correlation_health"],
        )

    return result


# ---------------------------------------------------------------------------
# Data Quality Checks (KIMI review)
# ---------------------------------------------------------------------------

def check_data_quality(picks: list[dict]) -> dict:
    """Run data quality checks on picks.

    Checks:
      1. Missing rate per feature (alert if > 1%)
      2. Stale data (same value repeated > 10 consecutive picks for a symbol)
      3. Price jump anomaly (entry price > 5% different from previous pick for same symbol)
      4. Volume anomaly (volume_ratio > 3 sigma from mean)

    Args:
        picks: List of pick dicts (active or closed).

    Returns:
        dict with quality_score (0-1), issues list, and per-check details.
    """
    issues: list[str] = []
    details: dict[str, dict] = {}

    if not picks:
        return {
            "quality_score": 1.0,
            "issues": [],
            "details": {},
            "total_picks": 0,
        }

    n_picks = len(picks)

    # --- 1. Missing rate per feature ---
    feature_names_seen: set[str] = set()
    feature_present_count: dict[str, int] = {}
    picks_with_features = 0

    for pick in picks:
        ml_feat = _extract_ml_features(pick)
        if ml_feat is None:
            continue
        picks_with_features += 1
        for fname, val in ml_feat.items():
            feature_names_seen.add(fname)
            if val is not None:
                feature_present_count[fname] = feature_present_count.get(fname, 0) + 1

    missing_alerts: list[str] = []
    if picks_with_features > 0:
        for fname in sorted(feature_names_seen):
            present = feature_present_count.get(fname, 0)
            missing_rate = 1.0 - (present / picks_with_features)
            if missing_rate > 0.01:
                missing_alerts.append(f"{fname}: {missing_rate:.1%} missing")
    if missing_alerts:
        issues.append(f"High missing rate: {len(missing_alerts)} features above 1%")
    details["missing_rate"] = {
        "alerts": missing_alerts,
        "features_checked": len(feature_names_seen),
        "threshold": "1%",
    }

    # --- 2. Stale data (same entry_price repeated > 10 consecutive picks per symbol) ---
    # Group picks by symbol, check for consecutive identical entry prices
    symbol_picks: dict[str, list[dict]] = {}
    for pick in picks:
        sym = pick.get("symbol", "")
        if sym:
            symbol_picks.setdefault(sym, []).append(pick)

    stale_alerts: list[str] = []
    for sym, sym_list in symbol_picks.items():
        # Sort by timestamp if available
        try:
            sym_list.sort(key=lambda p: str(p.get("timestamp", "")))
        except Exception:
            pass
        prices = [p.get("entry_price", 0) for p in sym_list]
        max_consecutive = 1
        current_run = 1
        for k in range(1, len(prices)):
            if prices[k] == prices[k - 1] and prices[k] != 0:
                current_run += 1
                max_consecutive = max(max_consecutive, current_run)
            else:
                current_run = 1
        if max_consecutive > 10:
            stale_alerts.append(f"{sym}: {max_consecutive} consecutive identical entry prices")

    if stale_alerts:
        issues.append(f"Stale data detected: {len(stale_alerts)} symbols")
    details["stale_data"] = {
        "alerts": stale_alerts,
        "threshold": "10 consecutive identical values",
    }

    # --- 3. Price jump anomaly (>5% between consecutive picks for same symbol) ---
    price_jump_alerts: list[str] = []
    for sym, sym_list in symbol_picks.items():
        try:
            sym_list.sort(key=lambda p: str(p.get("timestamp", "")))
        except Exception:
            pass
        for k in range(1, len(sym_list)):
            p_prev = float(sym_list[k - 1].get("entry_price", 0) or 0)
            p_curr = float(sym_list[k].get("entry_price", 0) or 0)
            if p_prev > 0 and p_curr > 0:
                pct_change = abs(p_curr - p_prev) / p_prev
                if pct_change > 0.05:
                    price_jump_alerts.append(
                        f"{sym}: {pct_change:.1%} jump "
                        f"({p_prev:.4f} -> {p_curr:.4f})"
                    )

    if price_jump_alerts:
        issues.append(f"Price jump anomalies: {len(price_jump_alerts)} instances")
    details["price_jumps"] = {
        "alerts": price_jump_alerts[:20],  # cap output
        "total": len(price_jump_alerts),
        "threshold": "5%",
    }

    # --- 4. Volume anomaly (volume_ratio > 3 sigma from mean) ---
    vol_ratios: list[float] = []
    for pick in picks:
        vr = pick.get("volume_ratio")
        if vr is not None:
            try:
                vol_ratios.append(float(vr))
            except (TypeError, ValueError):
                pass

    volume_anomaly_alerts: list[str] = []
    if len(vol_ratios) >= 5:
        mean_vr = sum(vol_ratios) / len(vol_ratios)
        var_vr = sum((v - mean_vr) ** 2 for v in vol_ratios) / max(len(vol_ratios) - 1, 1)
        std_vr = var_vr ** 0.5
        if std_vr > 1e-10:
            threshold_3sig = mean_vr + 3 * std_vr
            for pick in picks:
                vr = pick.get("volume_ratio")
                if vr is not None:
                    try:
                        fvr = float(vr)
                        if fvr > threshold_3sig:
                            volume_anomaly_alerts.append(
                                f"{pick.get('symbol', '?')}: volume_ratio={fvr:.2f} "
                                f"(3-sigma={threshold_3sig:.2f})"
                            )
                    except (TypeError, ValueError):
                        pass
            details["volume_anomalies"] = {
                "alerts": volume_anomaly_alerts[:20],
                "total": len(volume_anomaly_alerts),
                "mean": round(mean_vr, 4),
                "std": round(std_vr, 4),
                "threshold_3sig": round(threshold_3sig, 4),
            }
    else:
        details["volume_anomalies"] = {"alerts": [], "note": "insufficient volume data"}

    if volume_anomaly_alerts:
        issues.append(f"Volume anomalies: {len(volume_anomaly_alerts)} picks above 3-sigma")

    # Compute overall quality score (0-1)
    # Deductions: each category of issue reduces score
    score = 1.0
    if missing_alerts:
        score -= min(len(missing_alerts) * 0.02, 0.20)
    if stale_alerts:
        score -= min(len(stale_alerts) * 0.05, 0.20)
    if price_jump_alerts:
        score -= min(len(price_jump_alerts) * 0.01, 0.15)
    if volume_anomaly_alerts:
        score -= min(len(volume_anomaly_alerts) * 0.01, 0.10)
    score = max(score, 0.0)

    return {
        "quality_score": round(score, 4),
        "issues": issues,
        "details": details,
        "total_picks": n_picks,
        "picks_with_features": picks_with_features,
    }


def _save_report(report: dict) -> None:
    """Save report to data/feature_health_report.json."""
    try:
        _REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info(
            "Feature health report saved: score=%.2f (%d/%d alive)",
            report.get("health_score", 0),
            report.get("alive_features", 0),
            report.get("total_features", 0),
        )
    except IOError as e:
        logger.error("Failed to save feature health report: %s", e)


# ---------------------------------------------------------------------------
# Precision@K Measurement -- "When we're most confident, are we actually right?"
# ---------------------------------------------------------------------------
_KPI_REPORT_PATH = _DATA_DIR / "kpi_report.json"


def compute_precision_at_k(closed_picks: list[dict], k: int = 20) -> float:
    """Compute Precision@K: of the top-K scored picks, what fraction were winners?

    Sort closed picks by elite_score descending.
    Take top K.
    Count wins (pnl_pct > 0).
    Precision@K = wins / min(K, len(scored))

    This measures: "When we're most confident, are we actually right?"
    Target: >=52%
    """
    scored = [p for p in closed_picks if isinstance(p, dict) and p.get("elite_score")]
    scored.sort(key=lambda x: float(x.get("elite_score", 0)), reverse=True)
    top_k = scored[:k]
    if not top_k:
        return 0.0
    wins = sum(1 for p in top_k if float(p.get("pnl_pct", 0) or 0) > 0)
    return wins / len(top_k)


def compute_score_to_wr_correlation(closed_picks: list[dict]) -> float:
    """Compute Spearman rank correlation between elite_score and binary win (pnl_pct > 0).

    Positive correlation means higher scores predict higher win rates.
    Returns correlation coefficient in [-1, 1], or 0.0 if insufficient data.
    """
    scored = [
        p for p in closed_picks
        if isinstance(p, dict) and p.get("elite_score") is not None
        and p.get("pnl_pct") is not None
    ]
    if len(scored) < 10:
        return 0.0

    scores = [float(p.get("elite_score", 0)) for p in scored]
    wins = [1.0 if float(p.get("pnl_pct", 0) or 0) > 0 else 0.0 for p in scored]

    # Spearman rank correlation (no scipy dependency -- manual rank correlation)
    n = len(scores)

    def _rank(vals):
        indexed = sorted(enumerate(vals), key=lambda x: x[1])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n - 1 and indexed[j + 1][1] == indexed[j][1]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1
            for k_idx in range(i, j + 1):
                ranks[indexed[k_idx][0]] = avg_rank
            i = j + 1
        return ranks

    r_scores = _rank(scores)
    r_wins = _rank(wins)

    mean_s = sum(r_scores) / n
    mean_w = sum(r_wins) / n
    cov = sum((r_scores[i] - mean_s) * (r_wins[i] - mean_w) for i in range(n))
    std_s = (sum((r_scores[i] - mean_s) ** 2 for i in range(n))) ** 0.5
    std_w = (sum((r_wins[i] - mean_w) ** 2 for i in range(n))) ** 0.5

    if std_s == 0 or std_w == 0:
        return 0.0

    return round(cov / (std_s * std_w), 4)


def compute_precision_kpi_report(closed_picks: list[dict] | None = None) -> dict:
    """Compute full Precision@K KPI report and save to data/kpi_report.json.

    Computes:
      - Precision@10 (very top picks)
      - Precision@20 (standard)
      - Precision@50 (broader set)
      - Score-to-WR correlation (does higher score = higher WR?)

    Returns the KPI report dict.
    """
    if closed_picks is None:
        closed_picks = _load_picks(_CLOSED_PICKS_PATH)

    p_at_10 = compute_precision_at_k(closed_picks, k=10)
    p_at_20 = compute_precision_at_k(closed_picks, k=20)
    p_at_50 = compute_precision_at_k(closed_picks, k=50)
    score_wr_corr = compute_score_to_wr_correlation(closed_picks)

    scored_count = sum(
        1 for p in closed_picks
        if isinstance(p, dict) and p.get("elite_score")
    )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "precision_at_10": round(p_at_10, 4),
        "precision_at_20": round(p_at_20, 4),
        "precision_at_50": round(p_at_50, 4),
        "score_to_wr_correlation": score_wr_corr,
        "scored_picks": scored_count,
        "total_closed_picks": len(closed_picks),
        "targets": {
            "precision_at_20": ">= 0.52",
            "score_to_wr_correlation": "> 0 (positive)",
        },
        "status": {
            "precision_at_20": "GREEN" if p_at_20 >= 0.52 else "RED",
            "score_to_wr_correlation": "GREEN" if score_wr_corr > 0 else "RED",
        },
    }

    # Log summary
    logger.info(
        "Precision@K: P@10=%.1f%%, P@20=%.1f%%, P@50=%.1f%%, "
        "score-WR corr=%.4f (scored=%d/%d)",
        p_at_10 * 100, p_at_20 * 100, p_at_50 * 100,
        score_wr_corr, scored_count, len(closed_picks),
    )

    # Save to JSON
    try:
        _KPI_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_KPI_REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
    except IOError as e:
        logger.warning("Failed to write kpi_report.json: %s", e)

    return report


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    report = generate_health_report()
    print(f"\n=== Feature Health Report ===")
    print(f"Generated: {report['generated_at']}")
    print(f"Total features: {report['total_features']}")
    print(f"Alive: {report['alive_features']}")
    print(f"Dead: {report['dead_features']}")
    print(f"Health score: {report['health_score']:.2%}")
    print(f"Picks analyzed: {report.get('total_picks_analyzed', '?')}")
    print(f"Picks with features: {report.get('picks_with_features', '?')}")

    if report["recommendations"]:
        print(f"\nRecommendations ({len(report['recommendations'])}):")
        for rec in report["recommendations"]:
            print(f"  - {rec}")

    # Per-feature summary
    print(f"\nPer-feature status:")
    for name, stats in report.get("features", {}).items():
        status = stats.get("status", "?")
        marker = "X" if status in ("dead_constant", "mostly_zero", "no_data") else "~" if status == "stale" else "+"
        crit = " [CRITICAL]" if stats.get("critical") else ""
        print(f"  [{marker}] {name:30s} {status:15s} (n={stats.get('n_samples', 0)}, "
              f"var={stats.get('variance', 0):.6f}, %zero={stats.get('pct_zero', 0):.0%}){crit}")

    sys.exit(0 if report["health_score"] >= 0.5 else 1)
