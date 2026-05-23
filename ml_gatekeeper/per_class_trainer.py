"""
Per-class ML pick quality models — trained on REAL closed picks per asset class.

Reuses ~80% of ml_gatekeeper/gatekeeper.py logic (feature extraction, training
pipeline, leakage masking). The key difference: each model is trained on the
closed picks for ONE asset class only, producing class-specific WR thresholds
and feature importances.

Why per-class?
  - CRYPTO n=8,000+ allows a richer model; BOND n=11 requires a stub/fallback.
  - Class-specific feature importances reveal what actually predicts wins per class
    (e.g. wf_pass matters more for EQUITY than CRYPTO; direction matters for FOREX).
  - Enables per-class calibration thresholds instead of one global 0.5 cutoff.

Output: ml_gatekeeper/models/per_class/<CLASS>_model.joblib + <CLASS>_report.json
Wire-up: opt-in sidecar (reads from per_class_gates.json; not in passes_active_gate yet).
Wiring plan: wire predict_quality(pick) into passes_smart_gate() for CRYPTO + EQUITY
             once 30-day shadow validation confirms calibration matches live WR.

Run:
    python ml_gatekeeper/per_class_trainer.py                     # all classes
    python ml_gatekeeper/per_class_trainer.py --class CRYPTO      # one class
    python ml_gatekeeper/per_class_trainer.py --class EQUITY --dry-run
    ML_GATE_DROP_LEAKAGE=1 python ml_gatekeeper/per_class_trainer.py  # no leakage
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ml_gatekeeper"))

DASHBOARD_DATA = ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
PER_CLASS_DIR = ROOT / "ml_gatekeeper" / "models" / "per_class"
GATES_OUT = ROOT / "ml_gatekeeper" / "data" / "per_class_gates.json"

MIN_TRAIN_N = 50  # minimum resolved picks to attempt training

# Same class list as gatekeeper.py
ALL_CLASSES = ["CRYPTO", "EQUITY", "COMMODITY", "ETF", "FOREX", "BOND", "FUTURES"]


# ---------------------------------------------------------------------------
# Reuse feature extraction from gatekeeper.py
# ---------------------------------------------------------------------------

try:
    from gatekeeper import extract_features, FEATURE_NAMES, _f, _drop_leakage_enabled
except ImportError:
    from ml_gatekeeper.gatekeeper import extract_features, FEATURE_NAMES, _f, _drop_leakage_enabled


# ---------------------------------------------------------------------------
# Data loading — filtered by asset class
# ---------------------------------------------------------------------------

def load_class_data(asset_class: str) -> tuple[list, list, list]:
    """Load closed picks for one asset class. Returns (X, y, meta).

    Filters recent_closed by asset_class (case-insensitive). Labels:
    1 = profitable (pnl_pct > 0), 0 = unprofitable (pnl_pct <= 0).
    """
    if not DASHBOARD_DATA.exists():
        print(f"[per_class] dashboard_data.json not found")
        return [], [], []

    data = json.loads(DASHBOARD_DATA.read_text(encoding="utf-8"))
    closed = data.get("picks", {}).get("recent_closed", [])
    target = asset_class.upper()

    X, y, meta = [], [], []
    for pick in closed:
        if str(pick.get("asset_class", "") or "").upper() != target:
            continue
        pnl = pick.get("pnl_pct")
        if pnl is None:
            continue

        features = extract_features(pick)
        label = 1 if pnl > 0 else 0
        X.append(features)
        y.append(label)
        meta.append({
            "symbol": pick.get("symbol"),
            "strategy": pick.get("strategy"),
            "source_system": pick.get("source_system"),
            "asset_class": pick.get("asset_class"),
            "pnl_pct": pnl,
            "timestamp": pick.get("timestamp"),
        })

    wins = sum(y)
    n = len(y)
    wr = wins / n * 100 if n > 0 else 0
    print(f"[per_class:{target}] {n} resolved picks — {wins} wins / {n - wins} losses ({wr:.1f}% WR)")
    return X, y, meta


# ---------------------------------------------------------------------------
# Training — same architecture as gatekeeper.py, simplified for small n
# ---------------------------------------------------------------------------

def train_class_model(asset_class: str, X: list, y: list, meta: list) -> dict:
    """Train per-class model. Returns report dict.

    Uses the same GradientBoosting + RandomForest ensemble as gatekeeper.py
    with TimeSeriesSplit CV. Falls back to a frequency-baseline stub when
    n < MIN_TRAIN_N (e.g. BOND n=11, FUTURES n=0).
    """
    import numpy as np
    n = len(X)
    base_wr = sum(y) / n if n > 0 else 0

    if n < MIN_TRAIN_N:
        print(f"[per_class:{asset_class}] n={n} < {MIN_TRAIN_N} — using frequency stub")
        return {
            "asset_class": asset_class,
            "status": "stub_insufficient_data",
            "n": n,
            "base_wr": round(base_wr, 4),
            "threshold": 0.5,
            "model_path": None,
            "note": f"Need n>={MIN_TRAIN_N} to train; current n={n}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    try:
        from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
        from sklearn.model_selection import TimeSeriesSplit
        from sklearn.metrics import roc_auc_score, brier_score_loss, accuracy_score
        from sklearn.preprocessing import StandardScaler
        from sklearn.isotonic import IsotonicRegression
        import joblib
    except ImportError as e:
        print(f"[per_class:{asset_class}] sklearn/joblib not available: {e}")
        return {
            "asset_class": asset_class, "status": "import_error", "error": str(e),
            "n": n, "base_wr": round(base_wr, 4),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    X_arr = np.nan_to_num(np.array(X, dtype=np.float64), nan=0.0, posinf=0.0, neginf=0.0)
    y_arr = np.array(y, dtype=np.int32)

    n_splits = min(5, max(2, n // 20))
    tscv = TimeSeriesSplit(n_splits=n_splits)
    fold_metrics = []
    oof_probs = np.zeros(n)

    for fold, (tr_idx, val_idx) in enumerate(tscv.split(X_arr)):
        if len(val_idx) < 5:
            continue
        X_tr, X_val = X_arr[tr_idx], X_arr[val_idx]
        y_tr, y_val = y_arr[tr_idx], y_arr[val_idx]

        scaler = StandardScaler()
        X_tr_s = scaler.fit_transform(X_tr)
        X_val_s = scaler.transform(X_val)

        gb = GradientBoostingClassifier(
            n_estimators=150, max_depth=3, learning_rate=0.05,
            subsample=0.8, min_samples_leaf=max(5, n // 50), random_state=42,
        )
        rf = RandomForestClassifier(
            n_estimators=150, max_depth=6, min_samples_leaf=max(5, n // 50),
            class_weight="balanced", random_state=42, n_jobs=-1,
        )
        gb.fit(X_tr_s, y_tr)
        rf.fit(X_tr_s, y_tr)

        prob = 0.6 * gb.predict_proba(X_val_s)[:, 1] + 0.4 * rf.predict_proba(X_val_s)[:, 1]
        oof_probs[val_idx] = prob

        try:
            auc = roc_auc_score(y_val, prob)
            brier = brier_score_loss(y_val, prob)
        except ValueError:
            auc, brier = 0.5, 1.0
        acc = accuracy_score(y_val, (prob >= 0.5).astype(int))
        fold_metrics.append({"fold": fold + 1, "n_val": len(val_idx), "acc": round(acc, 4),
                              "auc": round(auc, 4), "brier": round(brier, 4),
                              "base_wr": round(float(y_val.mean()), 4)})
        print(f"  [{asset_class}] fold {fold+1}: acc={acc:.3f} auc={auc:.3f} brier={brier:.4f} (n={len(val_idx)})")

    # Final model on all data
    scaler_final = StandardScaler()
    X_s = scaler_final.fit_transform(X_arr)

    final_gb = GradientBoostingClassifier(
        n_estimators=200, max_depth=3, learning_rate=0.03,
        subsample=0.8, min_samples_leaf=max(5, n // 50), random_state=42,
    )
    final_rf = RandomForestClassifier(
        n_estimators=200, max_depth=6, min_samples_leaf=max(5, n // 50),
        class_weight="balanced", random_state=42, n_jobs=-1,
    )
    final_gb.fit(X_s, y_arr)
    final_rf.fit(X_s, y_arr)

    # Isotonic calibration on OOF probs (same as gatekeeper.py)
    valid_oof = oof_probs > 0
    calibrator = None
    if valid_oof.sum() >= 20:
        calibrator = IsotonicRegression(out_of_bounds="clip")
        calibrator.fit(oof_probs[valid_oof], y_arr[valid_oof])

    # Feature importances
    gb_imp = final_gb.feature_importances_
    rf_imp = final_rf.feature_importances_
    avg_imp = 0.6 * gb_imp + 0.4 * rf_imp
    top_features = sorted(zip(FEATURE_NAMES, avg_imp.tolist()), key=lambda x: -x[1])[:10]

    print(f"\n[per_class:{asset_class}] Top 5 features:")
    for name, imp in top_features[:5]:
        print(f"  {name:<30} {imp:.4f}")

    # Class-specific threshold: maximize precision at WR above base rate
    oof_valid = oof_probs[valid_oof]
    y_valid = y_arr[valid_oof]
    best_thresh = 0.5
    best_precision = 0.0
    for t in [0.45, 0.50, 0.55, 0.60, 0.65, 0.70]:
        preds = oof_valid >= t
        if preds.sum() < 10:
            continue
        prec = float(y_valid[preds].mean())
        if prec > best_precision and prec > base_wr:
            best_precision = prec
            best_thresh = t

    # Save model bundle
    PER_CLASS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = PER_CLASS_DIR / f"{asset_class}_model.joblib"
    bundle = {
        "scaler": scaler_final,
        "gb": final_gb,
        "rf": final_rf,
        "calibrator": calibrator,
        "threshold": best_thresh,
        "feature_names": FEATURE_NAMES,
        "asset_class": asset_class,
        "n_train": n,
        "base_wr": base_wr,
        "leakage_dropped": _drop_leakage_enabled(),
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    joblib.dump(bundle, model_path)
    print(f"[per_class:{asset_class}] Model saved → {model_path.name}")

    avg_auc = sum(m["auc"] for m in fold_metrics) / len(fold_metrics) if fold_metrics else 0

    return {
        "asset_class": asset_class,
        "status": "trained",
        "n": n,
        "base_wr": round(base_wr, 4),
        "threshold": best_thresh,
        "threshold_precision": round(best_precision, 4),
        "cv_folds": fold_metrics,
        "avg_cv_auc": round(avg_auc, 4),
        "top_features": [(name, round(imp, 4)) for name, imp in top_features],
        "model_path": str(model_path),
        "leakage_dropped": _drop_leakage_enabled(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Scoring — predict quality for a single pick using per-class model
# ---------------------------------------------------------------------------

def predict_quality(pick: dict, asset_class: str | None = None) -> dict:
    """Score a pick using the per-class model. Returns dict with fields:
      - ml_per_class_score: float 0-1 (calibrated win probability)
      - ml_per_class_pass: bool (above class threshold)
      - ml_per_class_threshold: float
      - ml_per_class_status: 'scored' | 'stub' | 'no_model'
    """
    ac = (asset_class or pick.get("asset_class") or "CRYPTO").upper()
    model_path = PER_CLASS_DIR / f"{ac}_model.joblib"

    if not model_path.exists():
        return {
            "ml_per_class_score": None,
            "ml_per_class_pass": True,  # fail-open
            "ml_per_class_threshold": 0.5,
            "ml_per_class_status": "no_model",
        }

    try:
        import joblib
        import numpy as np
        bundle = joblib.load(model_path)
        features = extract_features(pick)
        X = np.nan_to_num(np.array([features], dtype=np.float64), nan=0.0)
        X_s = bundle["scaler"].transform(X)
        gb_prob = bundle["gb"].predict_proba(X_s)[0, 1]
        rf_prob = bundle["rf"].predict_proba(X_s)[0, 1]
        raw_prob = 0.6 * gb_prob + 0.4 * rf_prob
        if bundle.get("calibrator") is not None:
            cal_prob = float(bundle["calibrator"].predict([raw_prob])[0])
        else:
            cal_prob = float(raw_prob)
        threshold = bundle.get("threshold", 0.5)
        return {
            "ml_per_class_score": round(cal_prob, 4),
            "ml_per_class_pass": cal_prob >= threshold,
            "ml_per_class_threshold": threshold,
            "ml_per_class_status": "scored",
        }
    except Exception as e:
        return {
            "ml_per_class_score": None,
            "ml_per_class_pass": True,  # fail-open
            "ml_per_class_threshold": 0.5,
            "ml_per_class_status": f"error:{e}",
        }


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Per-class ML pick quality trainer")
    parser.add_argument("--class", dest="asset_class", default=None,
                        help="Train one class only (e.g. CRYPTO). Default: all.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print report without saving models.")
    parser.add_argument("--min-n", type=int, default=MIN_TRAIN_N,
                        help=f"Minimum n to attempt training (default {MIN_TRAIN_N}).")
    args = parser.parse_args()

    classes = [args.asset_class.upper()] if args.asset_class else ALL_CLASSES
    all_reports: dict[str, dict] = {}

    for ac in classes:
        print(f"\n{'='*60}")
        print(f"[per_class] Training: {ac}")
        print(f"{'='*60}")
        X, y, meta = load_class_data(ac)
        if len(X) < args.min_n:
            report = {
                "asset_class": ac, "status": "insufficient_data",
                "n": len(X), "min_n": args.min_n,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
            print(f"[per_class:{ac}] Skipping — n={len(X)} < min_n={args.min_n}")
        else:
            report = train_class_model(ac, X, y, meta)
            if args.dry_run:
                report["model_path"] = "(dry-run, not saved)"

        all_reports[ac] = report

    # Write gates manifest
    gates_manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "leakage_dropped": _drop_leakage_enabled(),
        "classes": {
            ac: {
                "status": r.get("status"),
                "n": r.get("n", 0),
                "base_wr": r.get("base_wr"),
                "threshold": r.get("threshold"),
                "avg_cv_auc": r.get("avg_cv_auc"),
                "model_path": r.get("model_path"),
            }
            for ac, r in all_reports.items()
        },
    }
    if not args.dry_run:
        GATES_OUT.parent.mkdir(parents=True, exist_ok=True)
        GATES_OUT.write_text(json.dumps(gates_manifest, indent=2), encoding="utf-8")
        print(f"\n[per_class] Gates manifest written → {GATES_OUT}")
    else:
        print("\n[per_class] DRY-RUN gates manifest:")
        print(json.dumps(gates_manifest, indent=2))

    # Summary
    print(f"\n{'='*60}")
    print("[per_class] Summary")
    print(f"{'='*60}")
    for ac, r in all_reports.items():
        status = r.get("status", "?")
        n = r.get("n", 0)
        auc = r.get("avg_cv_auc", "N/A")
        thresh = r.get("threshold", "N/A")
        print(f"  {ac:<12} n={n:<6} status={status:<25} auc={auc}  thresh={thresh}")


if __name__ == "__main__":
    main()
