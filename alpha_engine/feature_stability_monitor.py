"""
ALPHA ENGINE -- Feature Stability Monitor & Automated Feature Discovery
=======================================================================
Tracks feature importance stability across training cycles, detects
redundant feature pairs, discovers candidate features from extra_json,
and recommends dead feature cleanup.

Pure Python (no scipy). Runs weekly via feature-stability-check.yml.

Sections:
  1. Feature Importance Stability (CV analysis across N training cycles)
  2. Feature Correlation Matrix (Pearson, flag |r| > 0.85)
  3. Automated Feature Discovery (Spearman vs pnl_pct from extra_json)
  4. Dead Feature Cleanup (cross-ref health report, recommend removals)
"""

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent / "data"
FEATURE_IMPORTANCE_PATH = DATA_DIR / "feature_importance.json"
FEATURE_IMPORTANCE_HISTORY_PATH = DATA_DIR / "feature_importance_history.json"
FEATURE_HEALTH_REPORT_PATH = DATA_DIR / "feature_health_report.json"
CLOSED_PICKS_PATH = DATA_DIR / "closed_picks.json"

STABILITY_REPORT_PATH = DATA_DIR / "feature_stability_report.json"
CORRELATION_REPORT_PATH = DATA_DIR / "feature_correlation.json"
DISCOVERY_REPORT_PATH = DATA_DIR / "feature_discovery.json"
DEAD_CLEANUP_PATH = DATA_DIR / "feature_dead_cleanup.json"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MIN_CYCLES_FOR_STABILITY = 3
CV_UNSTABLE_THRESHOLD = 1.0
CORRELATION_REDUNDANT_THRESHOLD = 0.85
DISCOVERY_MIN_PICKS = 20
DISCOVERY_MIN_ABS_CORR = 0.10
DISCOVERY_P_THRESHOLD = 0.05
DEAD_CONSECUTIVE_THRESHOLD = 3  # reports where feature is >80% missing

# Extra keys that leak future info (they correlate perfectly with pnl but
# ARE the outcome). Exclude from discovery candidates.
LEAKY_EXTRA_KEYS = {
    "gross_pnl_pct", "net_pnl_pct", "pnl_pct", "pnl_dollar",
    "exit_price", "exit_date", "exit_reason", "closed_at",
    "hold_duration_hours", "mfe_pct", "mae_pct", "entry_vs_optimal",
    "status", "high_water_mark",
}


# ===========================================================================
# Math helpers (pure Python -- no scipy/numpy)
# ===========================================================================

def _mean(values):
    """Arithmetic mean."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def _std(values, mean_val=None):
    """Population standard deviation."""
    if len(values) < 2:
        return 0.0
    m = mean_val if mean_val is not None else _mean(values)
    return math.sqrt(sum((x - m) ** 2 for x in values) / len(values))


def _pearson(xs, ys):
    """Pearson correlation coefficient. Returns 0.0 on degenerate input."""
    n = len(xs)
    if n < 3:
        return 0.0
    mx, my = _mean(xs), _mean(ys)
    sx, sy = _std(xs, mx), _std(ys, my)
    if sx == 0 or sy == 0:
        return 0.0
    cov = sum((xs[i] - mx) * (ys[i] - my) for i in range(n)) / n
    return cov / (sx * sy)


def _rank(values):
    """Assign average ranks (1-based) to values. Handles ties."""
    n = len(values)
    indexed = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j < n - 1 and values[indexed[j + 1]] == values[indexed[j]]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[indexed[k]] = avg_rank
        i = j + 1
    return ranks


def _spearman(xs, ys):
    """Spearman rank correlation. Returns (rho, p_value_approx)."""
    n = len(xs)
    if n < 6:
        return 0.0, 1.0
    rx = _rank(xs)
    ry = _rank(ys)
    rho = _pearson(rx, ry)
    # Approximate p-value via t-distribution approximation (two-tailed)
    if abs(rho) >= 1.0:
        return rho, 0.0
    t_stat = rho * math.sqrt((n - 2) / (1.0 - rho * rho))
    # Use normal approximation for large n (>30) or rough Student-t for small n
    p = _t_to_p(t_stat, n - 2)
    return rho, p


def _t_to_p(t, df):
    """Approximate two-tailed p-value from t-statistic using normal approx."""
    # For df > 30, t ~ N(0,1). For smaller df, this is an approximation.
    # Uses the complementary error function approach.
    x = abs(t)
    if df < 30:
        # Slightly adjust for heavier tails with small df
        x = x * math.sqrt(1 - 1.0 / (4.0 * max(df, 1)))
    # Standard normal survival function approximation (Abramowitz & Stegun 26.2.17)
    p_one_tail = _normal_sf(x)
    return 2.0 * p_one_tail


def _normal_sf(x):
    """Standard normal survival function P(Z > x) approximation."""
    if x < 0:
        return 1.0 - _normal_sf(-x)
    # Abramowitz & Stegun 26.2.17
    b0 = 0.2316419
    b1 = 0.319381530
    b2 = -0.356563782
    b3 = 1.781477937
    b4 = -1.821255978
    b5 = 1.330274429
    t = 1.0 / (1.0 + b0 * x)
    phi = math.exp(-x * x / 2.0) / math.sqrt(2.0 * math.pi)
    return phi * t * (b1 + t * (b2 + t * (b3 + t * (b4 + t * b5))))


def _safe_float(v, default=None):
    """Convert to float, returning default for NaN/None/non-numeric."""
    if v is None:
        return default
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (ValueError, TypeError):
        return default


# ===========================================================================
# Section 1: Feature Importance Stability
# ===========================================================================

def _load_importance_history():
    """Load history of feature importances across training cycles.

    The history file stores a list of snapshots, each with a timestamp
    and a dict of feature->importance. We also append the current
    feature_importance.json if it's newer.
    """
    history = []
    if FEATURE_IMPORTANCE_HISTORY_PATH.exists():
        try:
            history = json.loads(FEATURE_IMPORTANCE_HISTORY_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            history = []

    # Append current snapshot if not already present
    if FEATURE_IMPORTANCE_PATH.exists():
        try:
            current = json.loads(FEATURE_IMPORTANCE_PATH.read_text())
            ts = current.get("generated_at", "")
            importances = current.get("importances", {})
            # Only append if we have real data and it's not already the last entry
            if importances and (not history or history[-1].get("generated_at") != ts):
                clean_imp = {}
                for k, v in importances.items():
                    fv = _safe_float(v)
                    if fv is not None:
                        clean_imp[k] = fv
                if clean_imp:
                    history.append({
                        "generated_at": ts,
                        "importances": clean_imp
                    })
        except (json.JSONDecodeError, OSError):
            pass

    # Persist updated history (keep last 50 cycles)
    history = history[-50:]
    try:
        FEATURE_IMPORTANCE_HISTORY_PATH.write_text(
            json.dumps(history, indent=2), encoding="utf-8"
        )
    except OSError:
        pass

    return history


def analyze_feature_stability():
    """Compute importance stability metrics across training cycles.

    Returns dict with per-feature stats: mean, std, CV, classification.
    """
    history = _load_importance_history()
    n_cycles = len(history)

    # Collect all feature names seen across history
    all_features = set()
    for entry in history:
        all_features.update(entry.get("importances", {}).keys())

    results = {}
    stable_features = []
    unstable_features = []

    for feat in sorted(all_features):
        values = []
        top10_count = 0
        for entry in history:
            imp = entry.get("importances", {})
            fv = _safe_float(imp.get(feat))
            if fv is not None:
                values.append(fv)
            # Check if feature was in top 10 for this cycle
            sorted_imp = sorted(
                ((k, _safe_float(v, 0.0)) for k, v in imp.items()),
                key=lambda x: x[1], reverse=True
            )
            top10_names = {x[0] for x in sorted_imp[:10]}
            if feat in top10_names:
                top10_count += 1

        if not values:
            results[feat] = {
                "mean_importance": 0.0,
                "std_importance": 0.0,
                "cv": None,
                "n_cycles_present": 0,
                "n_cycles_top10": 0,
                "classification": "no_data"
            }
            continue

        mean_imp = _mean(values)
        std_imp = _std(values)
        cv = (std_imp / mean_imp) if mean_imp > 1e-10 else None

        classification = "normal"
        if cv is not None and cv > CV_UNSTABLE_THRESHOLD:
            classification = "UNSTABLE"
            unstable_features.append(feat)
        elif top10_count >= MIN_CYCLES_FOR_STABILITY and top10_count >= min(n_cycles, 3):
            classification = "STABLE_TOP10"
            stable_features.append(feat)

        results[feat] = {
            "mean_importance": round(mean_imp, 6),
            "std_importance": round(std_imp, 6),
            "cv": round(cv, 4) if cv is not None else None,
            "n_cycles_present": len(values),
            "n_cycles_top10": top10_count,
            "classification": classification
        }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_training_cycles": n_cycles,
        "total_features_tracked": len(all_features),
        "stable_top10_features": stable_features,
        "unstable_features": unstable_features,
        "features": results
    }

    try:
        STABILITY_REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    except OSError as e:
        print(f"[feature_stability] WARNING: Could not write stability report: {e}")

    print(f"[feature_stability] Stability: {n_cycles} cycles, "
          f"{len(stable_features)} stable, {len(unstable_features)} unstable")
    return report


# ===========================================================================
# Section 2: Feature Correlation Matrix
# ===========================================================================

def _load_closed_picks_features():
    """Load closed picks and extract numeric feature values.

    Returns (feature_names, feature_vectors) where feature_vectors is
    a dict of feature_name -> list of float values (aligned by pick index).
    Also returns pnl_pct list for discovery.
    """
    if not CLOSED_PICKS_PATH.exists():
        return [], {}, []

    try:
        picks = json.loads(CLOSED_PICKS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return [], {}, []

    if not picks:
        return [], {}, []

    # Identify all numeric fields that appear in picks
    numeric_fields = set()
    # Also track extra_json keys
    extra_keys = {}

    for pick in picks:
        for key, val in pick.items():
            if key in ("id", "strategy", "symbol", "category", "signal_type",
                       "entry_date", "exit_date", "exit_reason", "status",
                       "regime_at_entry", "extra_json"):
                continue
            fv = _safe_float(val)
            if fv is not None:
                numeric_fields.add(key)

        # Parse extra_json
        extra_raw = pick.get("extra_json", "")
        if extra_raw and isinstance(extra_raw, str):
            try:
                extra = json.loads(extra_raw)
                if isinstance(extra, dict):
                    for ek, ev in extra.items():
                        fv = _safe_float(ev)
                        if fv is not None:
                            extra_keys.setdefault(ek, 0)
                            extra_keys[ek] += 1
            except (json.JSONDecodeError, ValueError):
                pass

    # Build aligned vectors for alive features
    feature_names = sorted(numeric_fields)
    feature_vectors = {f: [] for f in feature_names}
    pnl_values = []

    for pick in picks:
        pnl = _safe_float(pick.get("pnl_pct"))
        if pnl is None:
            continue
        pnl_values.append(pnl)
        for f in feature_names:
            fv = _safe_float(pick.get(f))
            feature_vectors[f].append(fv if fv is not None else 0.0)

    return feature_names, feature_vectors, pnl_values, picks, extra_keys


def analyze_feature_correlation():
    """Compute pairwise Pearson correlation between alive features.

    Flags pairs with |r| > 0.85 as REDUNDANT.
    """
    result = _load_closed_picks_features()
    feature_names, feature_vectors = result[0], result[1]

    if len(feature_names) < 2:
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "insufficient_features",
            "n_features": len(feature_names),
            "redundant_pairs": [],
            "correlation_matrix": {}
        }
        try:
            CORRELATION_REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
        except OSError:
            pass
        return report

    # Load feature health to know which are alive
    alive_features = set()
    if FEATURE_HEALTH_REPORT_PATH.exists():
        try:
            health = json.loads(FEATURE_HEALTH_REPORT_PATH.read_text(encoding="utf-8"))
            for fname, fdata in health.get("features", {}).items():
                if fdata.get("activation_class") in ("alive", "weak"):
                    alive_features.add(fname)
        except (json.JSONDecodeError, OSError):
            pass

    # If we couldn't load health, use all features
    if not alive_features:
        alive_features = set(feature_names)

    # Filter to features with enough non-zero variance
    active_features = []
    for f in feature_names:
        if f not in alive_features and f != "pnl_pct":
            continue
        vals = feature_vectors[f]
        if len(vals) < 10:
            continue
        if _std(vals) < 1e-10:
            continue
        active_features.append(f)

    # Compute pairwise correlation
    corr_matrix = {}
    redundant_pairs = []

    # Load importance to know which feature to recommend dropping
    importances = {}
    if FEATURE_IMPORTANCE_PATH.exists():
        try:
            imp_data = json.loads(FEATURE_IMPORTANCE_PATH.read_text(encoding="utf-8"))
            for k, v in imp_data.get("importances", {}).items():
                fv = _safe_float(v)
                if fv is not None:
                    importances[k] = fv
        except (json.JSONDecodeError, OSError):
            pass

    for i, fa in enumerate(active_features):
        row = {}
        for j, fb in enumerate(active_features):
            if i == j:
                row[fb] = 1.0
                continue
            if j < i:
                # Already computed
                row[fb] = corr_matrix.get(fb, {}).get(fa, 0.0)
                continue
            r = _pearson(feature_vectors[fa], feature_vectors[fb])
            row[fb] = round(r, 4)
            if abs(r) > CORRELATION_REDUNDANT_THRESHOLD:
                # Recommend dropping the less important one
                imp_a = importances.get(fa, 0.0)
                imp_b = importances.get(fb, 0.0)
                drop = fb if imp_a >= imp_b else fa
                redundant_pairs.append({
                    "feature_a": fa,
                    "feature_b": fb,
                    "correlation": round(r, 4),
                    "recommend_drop": drop,
                    "reason": f"|r|={abs(r):.3f} > {CORRELATION_REDUNDANT_THRESHOLD}"
                })
        corr_matrix[fa] = row

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_features_analyzed": len(active_features),
        "n_picks_used": len(feature_vectors.get(active_features[0], [])) if active_features else 0,
        "redundant_pairs": redundant_pairs,
        "redundant_count": len(redundant_pairs),
        "correlation_matrix": corr_matrix
    }

    try:
        CORRELATION_REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    except OSError as e:
        print(f"[feature_stability] WARNING: Could not write correlation report: {e}")

    print(f"[feature_stability] Correlation: {len(active_features)} features, "
          f"{len(redundant_pairs)} redundant pairs")
    return report


# ===========================================================================
# Section 3: Automated Feature Discovery
# ===========================================================================

def discover_candidate_features():
    """Scan extra_json fields for candidate ML features.

    For each key appearing in 20+ picks, compute Spearman correlation
    with pnl_pct. Flag as CANDIDATE if |rho| > 0.10 and p < 0.05.
    """
    result = _load_closed_picks_features()
    if len(result) < 5:
        print("[feature_stability] WARNING: Could not load closed picks for discovery")
        return {"generated_at": datetime.now(timezone.utc).isoformat(), "candidates": []}

    _, _, pnl_values, picks, extra_key_counts = result

    # Get current ML feature list for exclusion
    current_features = set()
    try:
        # Import FEATURES from ml_ranker without running the whole module
        ml_ranker_path = Path(__file__).parent / "ml_ranker.py"
        if ml_ranker_path.exists():
            text = ml_ranker_path.read_text(encoding="utf-8")
            # Parse FEATURES list from source
            in_features = False
            bracket_depth = 0
            for line in text.split("\n"):
                stripped = line.strip()
                if "FEATURES = [" in stripped:
                    in_features = True
                    bracket_depth = 1
                    continue
                if in_features:
                    bracket_depth += stripped.count("[") - stripped.count("]")
                    if bracket_depth <= 0:
                        break
                    # Extract quoted feature name
                    if '"' in stripped:
                        name = stripped.split('"')[1]
                        current_features.add(name)
    except OSError:
        pass

    # Build per-extra-key aligned vectors with pnl
    extra_vectors = {}  # key -> [(extra_val, pnl_val), ...]
    for pick in picks:
        pnl = _safe_float(pick.get("pnl_pct"))
        if pnl is None:
            continue
        extra_raw = pick.get("extra_json", "")
        if not extra_raw or not isinstance(extra_raw, str):
            continue
        try:
            extra = json.loads(extra_raw)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(extra, dict):
            continue
        for ek, ev in extra.items():
            fv = _safe_float(ev)
            if fv is not None:
                extra_vectors.setdefault(ek, []).append((fv, pnl))

    candidates = []
    scanned_keys = []

    for key, pairs in sorted(extra_vectors.items()):
        if len(pairs) < DISCOVERY_MIN_PICKS:
            continue
        if key in current_features:
            continue
        if key in LEAKY_EXTRA_KEYS:
            continue

        xs = [p[0] for p in pairs]
        ys = [p[1] for p in pairs]

        rho, p_val = _spearman(xs, ys)
        is_candidate = abs(rho) > DISCOVERY_MIN_ABS_CORR and p_val < DISCOVERY_P_THRESHOLD

        entry = {
            "key": key,
            "n_picks": len(pairs),
            "spearman_rho": round(rho, 4),
            "p_value": round(p_val, 6),
            "is_candidate": is_candidate,
            "already_ml_feature": key in current_features
        }
        scanned_keys.append(entry)
        if is_candidate:
            candidates.append(entry)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_extra_keys_scanned": len(scanned_keys),
        "candidate_count": len(candidates),
        "discovery_thresholds": {
            "min_picks": DISCOVERY_MIN_PICKS,
            "min_abs_spearman": DISCOVERY_MIN_ABS_CORR,
            "max_p_value": DISCOVERY_P_THRESHOLD
        },
        "candidates": sorted(candidates, key=lambda x: abs(x["spearman_rho"]), reverse=True),
        "all_scanned": scanned_keys,
        "note": "These extra_json fields predict outcomes but are not yet ML features"
    }

    try:
        DISCOVERY_REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    except OSError as e:
        print(f"[feature_stability] WARNING: Could not write discovery report: {e}")

    print(f"[feature_stability] Discovery: {len(scanned_keys)} keys scanned, "
          f"{len(candidates)} candidates found")
    return report


# ===========================================================================
# Section 4: Dead Feature Cleanup
# ===========================================================================

def recommend_dead_cleanup():
    """Cross-reference FEATURES list with health reports.

    Features dead (>80% missing) for 3+ consecutive reports get flagged
    for removal. Generates a clean FEATURES list recommendation.
    """
    # Load current FEATURES from ml_ranker
    current_features = []
    try:
        ml_ranker_path = Path(__file__).parent / "ml_ranker.py"
        if ml_ranker_path.exists():
            text = ml_ranker_path.read_text(encoding="utf-8")
            in_features = False
            bracket_depth = 0
            for line in text.split("\n"):
                stripped = line.strip()
                if "FEATURES = [" in stripped:
                    in_features = True
                    bracket_depth = 1
                    continue
                if in_features:
                    bracket_depth += stripped.count("[") - stripped.count("]")
                    if bracket_depth <= 0:
                        break
                    if '"' in stripped:
                        name = stripped.split('"')[1]
                        current_features.append(name)
    except OSError:
        pass

    # Load health report
    health_data = {}
    if FEATURE_HEALTH_REPORT_PATH.exists():
        try:
            health = json.loads(FEATURE_HEALTH_REPORT_PATH.read_text(encoding="utf-8"))
            health_data = health.get("features", {})
        except (json.JSONDecodeError, OSError):
            pass

    # Load dead feature history (track consecutive dead counts)
    dead_history_path = DATA_DIR / "feature_dead_history.json"
    dead_history = {}
    if dead_history_path.exists():
        try:
            dead_history = json.loads(dead_history_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    # Update dead counts
    for feat in current_features:
        fh = health_data.get(feat, {})
        activation = fh.get("activation_class", "unknown")
        activation_rate = fh.get("activation_rate", 0.0)
        is_dead = activation == "dead" or activation_rate < 0.2

        prev = dead_history.get(feat, {"consecutive_dead": 0, "last_status": ""})
        if is_dead:
            prev["consecutive_dead"] = prev.get("consecutive_dead", 0) + 1
        else:
            prev["consecutive_dead"] = 0
        prev["last_status"] = activation
        prev["activation_rate"] = activation_rate
        dead_history[feat] = prev

    # Save updated history
    try:
        dead_history_path.write_text(json.dumps(dead_history, indent=2), encoding="utf-8")
    except OSError:
        pass

    # Find features to recommend removing
    remove_candidates = []
    keep_features = []
    for feat in current_features:
        info = dead_history.get(feat, {})
        consecutive = info.get("consecutive_dead", 0)
        if consecutive >= DEAD_CONSECUTIVE_THRESHOLD:
            remove_candidates.append({
                "feature": feat,
                "consecutive_dead_reports": consecutive,
                "last_activation_rate": info.get("activation_rate", 0.0),
                "recommendation": "REMOVE"
            })
        else:
            keep_features.append(feat)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "current_feature_count": len(current_features),
        "recommended_removals": len(remove_candidates),
        "recommended_feature_count": len(keep_features),
        "remove_candidates": remove_candidates,
        "clean_features_list": keep_features,
        "dead_history": dead_history
    }

    try:
        DEAD_CLEANUP_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    except OSError as e:
        print(f"[feature_stability] WARNING: Could not write cleanup report: {e}")

    print(f"[feature_stability] Cleanup: {len(current_features)} features, "
          f"{len(remove_candidates)} recommended for removal, "
          f"{len(keep_features)} clean")
    return report


# ===========================================================================
# Main entry point
# ===========================================================================

def run_full_analysis():
    """Run all four analyses and print summary."""
    print("=" * 70)
    print("FEATURE STABILITY MONITOR -- Full Analysis")
    print("=" * 70)

    print("\n--- Section 1: Feature Importance Stability ---")
    stability = analyze_feature_stability()

    print("\n--- Section 2: Feature Correlation Matrix ---")
    correlation = analyze_feature_correlation()

    print("\n--- Section 3: Automated Feature Discovery ---")
    discovery = discover_candidate_features()

    print("\n--- Section 4: Dead Feature Cleanup ---")
    cleanup = recommend_dead_cleanup()

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Training cycles analyzed: {stability.get('n_training_cycles', 0)}")
    print(f"  Stable top-10 features:   {len(stability.get('stable_top10_features', []))}")
    print(f"  Unstable features (CV>1):  {len(stability.get('unstable_features', []))}")
    print(f"  Redundant pairs (|r|>0.85):{correlation.get('redundant_count', 0)}")
    print(f"  Candidate new features:    {discovery.get('candidate_count', 0)}")
    print(f"  Dead features to remove:   {cleanup.get('recommended_removals', 0)}")
    print(f"  Clean feature list size:   {cleanup.get('recommended_feature_count', 0)}")

    # Print candidates if any
    if discovery.get("candidates"):
        print("\n  CANDIDATE features from extra_json:")
        for c in discovery["candidates"][:10]:
            print(f"    {c['key']}: rho={c['spearman_rho']}, p={c['p_value']}, n={c['n_picks']}")

    # Print removal recommendations if any
    if cleanup.get("remove_candidates"):
        print("\n  Features recommended for REMOVAL:")
        for r in cleanup["remove_candidates"]:
            print(f"    {r['feature']}: dead for {r['consecutive_dead_reports']} consecutive reports")

    print("\nReports saved to:")
    print(f"  {STABILITY_REPORT_PATH}")
    print(f"  {CORRELATION_REPORT_PATH}")
    print(f"  {DISCOVERY_REPORT_PATH}")
    print(f"  {DEAD_CLEANUP_PATH}")

    return {
        "stability": stability,
        "correlation": correlation,
        "discovery": discovery,
        "cleanup": cleanup
    }


# ===========================================================================
# Section 5: KS-test Feature Distribution Drift (A6.1)
# ===========================================================================

def check_feature_distribution_drift(
    current_features: "pd.DataFrame",
    reference_features: "pd.DataFrame",
    alpha: float = 0.05,
) -> dict:
    """Detect feature distribution drift via the two-sample Kolmogorov–Smirnov test.

    Parameters
    ----------
    current_features:
        pd.DataFrame where each column is a feature and each row is an
        observation from the *current* (recent) window.
    reference_features:
        pd.DataFrame with the same column layout from a *reference* (historical)
        window.
    alpha:
        Significance level for the KS test.  A feature is flagged as drifted
        when p_value < alpha.  Default 0.05.

    Returns
    -------
    dict
        ``{feature_name: {"ks_stat": float, "p_value": float, "drifted": bool}}``
        Only features that appear in *both* DataFrames are included.
        Features with fewer than 5 observations in either window return
        ``ks_stat=None, p_value=None, drifted=False`` with a warning logged.

    Notes
    -----
    - Requires ``scipy`` (already a project dependency — ``data_validator.py``
      imports ``scipy.stats``).
    - This function is **additive only** — it does not modify any existing
      function in this module.
    """
    try:
        from scipy.stats import ks_2samp
    except ImportError as exc:
        raise ImportError(
            "[feature_stability] check_feature_distribution_drift requires scipy. "
            "Install it via: pip install scipy"
        ) from exc

    try:
        import pandas as _pd  # lazy import — keeps module importable without pandas
    except ImportError as exc:
        raise ImportError(
            "[feature_stability] check_feature_distribution_drift requires pandas."
        ) from exc

    if current_features is None or reference_features is None:
        return {}

    common_cols = [
        c for c in current_features.columns if c in reference_features.columns
    ]
    if not common_cols:
        print(
            "[feature_stability] check_feature_distribution_drift: no common columns "
            "between current and reference DataFrames."
        )
        return {}

    results: dict = {}
    for col in common_cols:
        cur_vals = current_features[col].dropna().tolist()
        ref_vals = reference_features[col].dropna().tolist()

        if len(cur_vals) < 5 or len(ref_vals) < 5:
            print(
                f"[feature_stability] WARNING: '{col}' has too few observations "
                f"(current={len(cur_vals)}, reference={len(ref_vals)}) — skipping KS test."
            )
            results[col] = {"ks_stat": None, "p_value": None, "drifted": False}
            continue

        try:
            ks_stat, p_value = ks_2samp(cur_vals, ref_vals)
            drifted = bool(p_value < alpha)
            results[col] = {
                "ks_stat": round(float(ks_stat), 6),
                "p_value": round(float(p_value), 8),
                "drifted": drifted,
            }
        except Exception as exc:  # noqa: BLE001
            print(
                f"[feature_stability] WARNING: KS test failed for '{col}': {exc}"
            )
            results[col] = {"ks_stat": None, "p_value": None, "drifted": False}

    n_drifted = sum(1 for v in results.values() if v.get("drifted"))
    print(
        f"[feature_stability] Distribution drift: {len(results)} features checked, "
        f"{n_drifted} drifted (alpha={alpha})"
    )
    return results


def generate_drift_report(results: dict) -> str:
    """Summarise KS-test drift results as a human-readable string.

    Parameters
    ----------
    results:
        Output of ``check_feature_distribution_drift``.

    Returns
    -------
    str
        Multi-line report listing drifted and stable features with their
        KS statistics and p-values.

    Notes
    -----
    - This function is **additive only**.
    """
    if not results:
        return "[feature_stability] Drift report: no results to display."

    drifted = {
        k: v for k, v in results.items()
        if v.get("drifted") is True
    }
    stable = {
        k: v for k, v in results.items()
        if v.get("drifted") is False
    }
    skipped = {
        k: v for k, v in results.items()
        if v.get("ks_stat") is None
    }

    lines = [
        "=" * 65,
        "FEATURE DISTRIBUTION DRIFT REPORT (KS-test)",
        "=" * 65,
        f"Features checked : {len(results)}",
        f"Drifted          : {len(drifted)}",
        f"Stable           : {len(stable) - len(skipped)}",
        f"Skipped (n<5)    : {len(skipped)}",
        "",
    ]

    if drifted:
        lines.append("DRIFTED FEATURES (p < alpha):")
        for feat, stats in sorted(drifted.items(), key=lambda x: x[1].get("p_value") or 1.0):
            lines.append(
                f"  {feat:<40s}  KS={stats['ks_stat']:.4f}  p={stats['p_value']:.6f}"
            )
        lines.append("")

    if stable:
        non_skipped_stable = {k: v for k, v in stable.items() if v.get("ks_stat") is not None}
        if non_skipped_stable:
            lines.append("STABLE FEATURES:")
            for feat, stats in sorted(non_skipped_stable.items()):
                lines.append(
                    f"  {feat:<40s}  KS={stats['ks_stat']:.4f}  p={stats['p_value']:.6f}"
                )
            lines.append("")

    if skipped:
        lines.append("SKIPPED (insufficient observations):")
        for feat in sorted(skipped):
            lines.append(f"  {feat}")
        lines.append("")

    lines.append("=" * 65)
    return "\n".join(lines)


if __name__ == "__main__":
    run_full_analysis()
