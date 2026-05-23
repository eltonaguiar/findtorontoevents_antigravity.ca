#!/usr/bin/env python3
"""
Meta-Model Trainer v1.0 — Learns optimal scoring weights from closed trades.

Based on Perplexity AI's design (2026-03-16) with ChatGPT's leak-free scoring fix.
Trains logistic regression on ex-ante features only (no LivePnL leakage).
Exports coefficients as JS-compatible JSON for client-side deployment.

Usage:
    python meta_model_trainer.py <closed_picks_csv> [--output-dir <dir>]
"""

import re
import sys
import json
import os
from datetime import datetime

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score, classification_report, precision_recall_curve

# ─── Column name mapping ────────────────────────────────────────────────────
COL_SCORE = "Score"
COL_GRADE = "Grade"
COL_PNL = "PnL%"
COL_DIRECTION = "Direction"
COL_TRUST = "Trust Tier"
COL_FORWARD_WR = "Forward WR"
COL_FORWARD_TRADES = "Forward Trades"
COL_CONFLUENCE = "Confluence Count"
COL_TIMEFRAME = "Timeframe"
COL_ENTRY_TIME = "Entry Time"
COL_EXIT_TIME = "Exit Time"
COL_EXIT_REASON = "Exit Reason"
COL_SYSTEM = "System"
COL_STRATEGY = "Strategy"
COL_SCORE_BREAKDOWN = "Score Breakdown (English)"
COL_REGIME_WARNINGS = "Regime Warnings"
COL_PICK_ID = "Pick ID"

# ─── Score breakdown parsing ────────────────────────────────────────────────

COMPONENT_NAMES = [
    "Strategy", "Signal", "Freshness", "Forward",
    "Consensus", "NoConflict", "LivePnL", "Timeframe",
]

# Ex-ante components only (no leakage) — per ChatGPT's recommendation
EX_ANTE_COMPONENTS = [
    "Strategy", "Signal", "Forward", "Consensus", "NoConflict", "Timeframe",
]
# Reactive components (excluded from entry_score, kept for management_score)
REACTIVE_COMPONENTS = ["Freshness", "LivePnL"]


def parse_score_breakdown(text):
    """Parse 'Strategy: 45/100 (15%) | Signal: 67/100 (15%) | ...'"""
    res = {}
    for name in COMPONENT_NAMES:
        key = name.lower()
        res[f"comp_{key}"] = np.nan
        res[f"w_{key}"] = np.nan

    if not isinstance(text, str) or not text:
        return res

    pattern = re.compile(r"([^:]+):\s*(\d+)\s*/\s*(\d+)\s*\((\d+)%\)")
    for part in text.split("|"):
        m = pattern.search(part.strip())
        if m:
            raw_name = m.group(1).strip()
            score = int(m.group(2))
            weight = int(m.group(4))
            raw_key = raw_name.lower().replace(" ", "").replace("_", "")
            for cname in COMPONENT_NAMES:
                if cname.lower().replace(" ", "").replace("_", "") == raw_key:
                    base = cname.lower()
                    res[f"comp_{base}"] = score
                    res[f"w_{base}"] = weight
                    break
    return res


def dedup_picks(df):
    """ChatGPT finding: 49.4% duplicate snapshots. Keep last snapshot per pick."""
    if COL_PICK_ID in df.columns:
        before = len(df)
        df = df.sort_values(COL_ENTRY_TIME).drop_duplicates(
            subset=[COL_PICK_ID], keep="last"
        )
        after = len(df)
        if before != after:
            print(f"  Deduped: {before} → {after} rows ({before - after} duplicates removed)")
    return df


def compute_entry_score(row):
    """Leak-free entry score using only ex-ante components."""
    total = 0
    weight_sum = 0
    for name in EX_ANTE_COMPONENTS:
        base = name.lower()
        comp = row.get(f"comp_{base}", 0) or 0
        w = row.get(f"w_{base}", 0) or 0
        total += comp * w
        weight_sum += w
    if weight_sum > 0:
        return total / weight_sum  # Normalize to 0-100 range
    return 0


def main(csv_path, output_dir=None):
    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(__file__))

    print("=" * 70)
    print("META-MODEL TRAINER v1.0")
    print(f"  CSV: {csv_path}")
    print(f"  Output: {output_dir}")
    print("=" * 70)

    # ─── 1. Load & clean ────────────────────────────────────────────────
    df = pd.read_csv(csv_path)
    print(f"\nLoaded {len(df)} rows")

    # Parse score breakdown
    parsed = df[COL_SCORE_BREAKDOWN].apply(parse_score_breakdown)
    parsed_df = pd.DataFrame(list(parsed))
    df = pd.concat([df, parsed_df], axis=1)

    # Numeric conversions
    for col in [COL_SCORE, COL_PNL, COL_FORWARD_WR, COL_FORWARD_TRADES, COL_CONFLUENCE]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df[COL_ENTRY_TIME] = pd.to_datetime(df[COL_ENTRY_TIME], errors="coerce")
    df = df.dropna(subset=[COL_PNL, COL_SCORE])
    df = df.sort_values(COL_ENTRY_TIME).reset_index(drop=True)

    # Dedup (ChatGPT's finding)
    df = dedup_picks(df)
    print(f"  Clean rows: {len(df)}")

    # ─── 2. Target variable ────────────────────────────────────────────
    PNL_THRESH = 0.0  # Binary: win if PnL > 0
    df["target_win"] = (df[COL_PNL] > PNL_THRESH).astype(int)

    # ─── 3. Compute leak-free entry score ───────────────────────────────
    df["entry_score"] = df.apply(compute_entry_score, axis=1)

    # ─── 4. Feature engineering ─────────────────────────────────────────
    # Direction
    df["is_long"] = (df[COL_DIRECTION].str.upper() == "LONG").astype(int)

    # Short-in-bull warning (ChatGPT: mean PnL -1.42%, win 29.9%)
    df["short_in_bull"] = 0
    if COL_REGIME_WARNINGS in df.columns:
        df["short_in_bull"] = df[COL_REGIME_WARNINGS].fillna("").str.contains(
            "SHORT.*BULLISH|BULLISH.*SHORT", case=False, regex=True
        ).astype(int)

    # Timeframe one-hot
    tf_dummies = pd.get_dummies(df[COL_TIMEFRAME].str.upper(), prefix="tf")
    df = pd.concat([df, tf_dummies], axis=1)

    # Trust tier ordinal
    trust_map = {
        "DEMOTED": -2, "SANDBOX": -1, "PROBATION": 0,
        "WATCH": 1, "RELIABLE": 2, "PROVEN": 3,
    }
    df["trust_code"] = df[COL_TRUST].str.upper().map(trust_map).fillna(0)

    # Grade ordinal
    grade_map = {"F": 0, "D": 1, "C": 2, "B": 3, "A": 4}
    df["grade_code"] = df[COL_GRADE].str.upper().map(grade_map).fillna(0)

    # ─── 5. Build feature matrix (EX-ANTE ONLY — no LivePnL, no Freshness) ─
    feature_cols = []

    # Leak-free entry score
    feature_cols.append("entry_score")

    # Ex-ante component scores only
    for name in EX_ANTE_COMPONENTS:
        base = name.lower()
        comp_col = f"comp_{base}"
        if comp_col in df.columns:
            feature_cols.append(comp_col)

    # Forward stats and confluence
    feature_cols.extend([COL_FORWARD_WR, COL_FORWARD_TRADES, COL_CONFLUENCE])

    # Direction & regime
    feature_cols.extend(["is_long", "short_in_bull"])

    # Timeframe dummies
    feature_cols.extend([c for c in tf_dummies.columns if c in df.columns])

    # Trust & grade
    feature_cols.extend(["trust_code", "grade_code"])

    print(f"\nFeatures ({len(feature_cols)}):")
    for f in feature_cols:
        print(f"  - {f}")

    X = df[feature_cols].fillna(0.0)
    y = df["target_win"]

    # ─── 6. Time-based train/test split ─────────────────────────────────
    N = len(df)
    split_idx = int(0.8 * N)
    print(f"\nTrain: {split_idx} rows | Test: {N - split_idx} rows")

    X_train, X_test = X.iloc[:split_idx].values, X.iloc[split_idx:].values
    y_train, y_test = y.iloc[:split_idx].values, y.iloc[split_idx:].values

    # ─── 7. Standardize ────────────────────────────────────────────────
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # ─── 8. Logistic regression (deployable to JS) ─────────────────────
    print("\n" + "=" * 70)
    print("LOGISTIC REGRESSION (leak-free, ex-ante features only)")
    print("=" * 70)

    log_reg = LogisticRegression(penalty="l2", C=1.0, solver="lbfgs", max_iter=1000)
    log_reg.fit(X_train_scaled, y_train)

    y_pred_proba = log_reg.predict_proba(X_test_scaled)[:, 1]
    y_pred = (y_pred_proba >= 0.5).astype(int)

    auc = roc_auc_score(y_test, y_pred_proba)
    print(f"\nROC AUC: {auc:.4f}")
    print(classification_report(y_test, y_pred))

    # Find optimal threshold (maximize F1)
    precisions, recalls, thresholds = precision_recall_curve(y_test, y_pred_proba)
    f1_scores = 2 * precisions * recalls / (precisions + recalls + 1e-8)
    best_idx = np.argmax(f1_scores)
    best_threshold = thresholds[best_idx] if best_idx < len(thresholds) else 0.5
    print(f"Optimal threshold: {best_threshold:.3f} (F1={f1_scores[best_idx]:.3f})")

    # ─── 9. Coefficient table ──────────────────────────────────────────
    coef = log_reg.coef_[0]
    intercept = float(log_reg.intercept_[0])

    coef_table = pd.DataFrame({
        "feature": feature_cols,
        "coef": coef,
        "mean": scaler.mean_,
        "std": scaler.scale_,
        "abs_coef": np.abs(coef),
    }).sort_values("abs_coef", ascending=False)

    print("\nFeature coefficients (sorted by importance):")
    print(coef_table[["feature", "coef", "abs_coef"]].to_string(index=False))
    print(f"\nIntercept (bias): {intercept:.6f}")

    # ─── 10. GBM for feature importance diagnostics ────────────────────
    print("\n" + "=" * 70)
    print("GBM FEATURE IMPORTANCE (diagnostic only — not deployed)")
    print("=" * 70)

    gbm = GradientBoostingClassifier(
        n_estimators=200, learning_rate=0.05, max_depth=3,
        subsample=0.8, random_state=42,
    )
    gbm.fit(X_train, y_train)

    gbm_auc = roc_auc_score(y_test, gbm.predict_proba(X_test)[:, 1])
    print(f"GBM ROC AUC: {gbm_auc:.4f}")

    importances = pd.Series(gbm.feature_importances_, index=feature_cols)
    importances = importances.sort_values(ascending=False)
    print("\nGBM Feature Importances:")
    for feat, imp in importances.items():
        bar = "#" * int(imp * 100)
        print(f"  {feat:25s} {imp:.4f} {bar}")

    # ─── 11. Export for JS deployment ──────────────────────────────────
    js_model = {
        "version": "meta_model_v1.0",
        "trained_at": datetime.utcnow().isoformat() + "Z",
        "training_rows": int(split_idx),
        "test_rows": int(N - split_idx),
        "roc_auc": round(auc, 4),
        "gbm_roc_auc": round(gbm_auc, 4),
        "optimal_threshold": round(best_threshold, 3),
        "intercept": round(intercept, 8),
        "features": [
            {
                "name": feat,
                "coef": round(float(coef_table.loc[coef_table["feature"] == feat, "coef"].values[0]), 8),
                "mean": round(float(coef_table.loc[coef_table["feature"] == feat, "mean"].values[0]), 8),
                "std": round(float(coef_table.loc[coef_table["feature"] == feat, "std"].values[0]), 8),
            }
            for feat in feature_cols
        ],
        "ex_ante_components": EX_ANTE_COMPONENTS,
        "reactive_components_excluded": REACTIVE_COMPONENTS,
        "notes": "Leak-free: excludes LivePnL and Freshness from entry scoring per ChatGPT recommendation",
    }

    # Save outputs
    json_path = os.path.join(output_dir, "meta_model_weights.json")
    with open(json_path, "w") as f:
        json.dump(js_model, f, indent=2)
    print(f"\nJS model weights saved: {json_path}")

    csv_out = os.path.join(output_dir, "meta_model_coefficients.csv")
    coef_table.to_csv(csv_out, index=False)
    print(f"Coefficient table saved: {csv_out}")

    gbm_out = os.path.join(output_dir, "meta_model_gbm_importances.csv")
    importances.to_csv(gbm_out)
    print(f"GBM importances saved: {gbm_out}")

    # ─── 12. Generate JS snippet ───────────────────────────────────────
    js_snippet = generate_js_function(js_model)
    js_path = os.path.join(output_dir, "meta_model_scorer.js")
    with open(js_path, "w") as f:
        f.write(js_snippet)
    print(f"JS scorer function saved: {js_path}")

    # ─── 13. Cohort analysis ──────────────────────────────────────────
    print("\n" + "=" * 70)
    print("COHORT ANALYSIS — Meta-model vs Current Score")
    print("=" * 70)

    df_test = df.iloc[split_idx:].copy()
    df_test["meta_prob"] = y_pred_proba

    for threshold in [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
        subset = df_test[df_test["meta_prob"] >= threshold]
        if len(subset) >= 5:
            wr = subset["target_win"].mean() * 100
            avg_pnl = subset[COL_PNL].mean()
            print(f"  meta_prob >= {threshold:.1f}: {len(subset):4d} trades, WR {wr:.1f}%, avg PnL {avg_pnl:+.2f}%")

    print("\nCurrent score thresholds (for comparison):")
    for threshold in [0, 10, 20, 30, 40, 50]:
        subset = df_test[df_test[COL_SCORE] >= threshold]
        if len(subset) >= 5:
            wr = subset["target_win"].mean() * 100
            avg_pnl = subset[COL_PNL].mean()
            print(f"  score >= {threshold:3d}: {len(subset):4d} trades, WR {wr:.1f}%, avg PnL {avg_pnl:+.2f}%")

    return js_model


def generate_js_function(model):
    """Generate a drop-in JS function from trained model weights."""
    lines = [
        "// META-MODEL SCORER v1.0 — Auto-generated from meta_model_trainer.py",
        f"// Trained: {model['trained_at']}",
        f"// ROC AUC: {model['roc_auc']} (logistic) | {model['gbm_roc_auc']} (GBM diagnostic)",
        f"// Optimal threshold: {model['optimal_threshold']}",
        "// LEAK-FREE: Excludes LivePnL and Freshness from entry scoring",
        "",
        "const META_MODEL = " + json.dumps({
            "intercept": model["intercept"],
            "threshold": model["optimal_threshold"],
            "features": model["features"],
        }, indent=2) + ";",
        "",
        "/**",
        " * Compute meta-model win probability for a pick.",
        " * @param {Object} f - Feature values keyed by feature name",
        " * @returns {number} Win probability 0-1",
        " */",
        "function metaWinProb(f) {",
        "  let z = META_MODEL.intercept;",
        "  for (const feat of META_MODEL.features) {",
        "    const raw = f[feat.name] ?? 0.0;",
        "    const std = feat.std || 1.0;",
        "    const standardized = (raw - feat.mean) / std;",
        "    z += feat.coef * standardized;",
        "  }",
        "  return 1.0 / (1.0 + Math.exp(-z));",
        "}",
        "",
        "/**",
        " * Grade a pick using meta-model probability.",
        " * @param {number} prob - Win probability from metaWinProb()",
        " * @returns {string} Grade A-F",
        " */",
        "function metaGrade(prob) {",
        f"  if (prob >= 0.80) return 'A';",
        f"  if (prob >= 0.65) return 'B';",
        f"  if (prob >= 0.50) return 'C';",
        f"  if (prob >= 0.35) return 'D';",
        "  return 'F';",
        "}",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python meta_model_trainer.py <closed_picks.csv> [--output-dir <dir>]")
        sys.exit(1)

    csv_file = sys.argv[1]
    out_dir = None
    if "--output-dir" in sys.argv:
        idx = sys.argv.index("--output-dir")
        out_dir = sys.argv[idx + 1]

    main(csv_file, out_dir)
