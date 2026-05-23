#!/usr/bin/env python3
"""
ChatGPT Meta-Model Trainer — Includes multiplier parsing + decision tree.
Complementary to Perplexity's logistic-only approach.
"""
import re
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.metrics import roc_auc_score, precision_score
import sys, json, os

CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else "antigravity_closed_picks_2026-03-16.csv"

COL_SCORE_BREAKDOWN = "Score Breakdown (English)"
COL_PNL = "PnL%"
COL_SCORE = "Score"
COL_GRADE = "Grade"
COL_TRUST = "Trust Tier"
COL_FORWARD_WR = "Forward WR"
COL_FORWARD_TRADES = "Forward Trades"
COL_CONFLUENCE = "Confluence Count"
COL_DIRECTION = "Direction"
COL_TIMEFRAME = "Timeframe"
COL_ENTRY_TIME = "Entry Time"

COMPONENT_KEYS = ["Strategy", "Signal", "Freshness", "Forward", "Consensus", "NoConflict", "LivePnL", "Timeframe"]
MULT_KEYS = ["Trust mult", "Dir penalty", "Time decay", "Entry drift", "Insight mult", "Consensus mult"]


def parse_score_breakdown(text):
    res = {}
    for key in COMPONENT_KEYS:
        base = key.lower().replace(" ", "_")
        res[f"comp_{base}"] = np.nan
        res[f"w_{base}"] = np.nan
    for key in MULT_KEYS:
        base = key.lower().replace(" ", "_")
        res[f"mult_{base}"] = np.nan

    if not isinstance(text, str) or not text:
        return res

    parts = [p.strip() for p in text.split("|")]
    comp_pattern = re.compile(r"([^:]+):\s*(\d+)\s*/\s*(\d+)\s*\((\d+)%\)", re.IGNORECASE)
    mult_pattern = re.compile(r"([^:]+):\s*([0-9]+(?:\.[0-9]+)?)%", re.IGNORECASE)

    for p in parts:
        m = comp_pattern.search(p)
        if m:
            raw_name = m.group(1).strip()
            score = float(m.group(2))
            weight = float(m.group(4))
            key_norm = raw_name.lower().replace(" ", "").replace("_", "")
            for ck in COMPONENT_KEYS:
                if ck.lower().replace(" ", "").replace("_", "") == key_norm:
                    base = ck.lower().replace(" ", "_")
                    res[f"comp_{base}"] = score
                    res[f"w_{base}"] = weight
                    break

        m2 = mult_pattern.search(p)
        if m2:
            raw_name = m2.group(1).strip()
            val = float(m2.group(2))
            key_norm = raw_name.lower().replace(" ", "").replace("_", "")
            for mk in MULT_KEYS:
                if mk.lower().replace(" ", "").replace("_", "") == key_norm:
                    base = mk.lower().replace(" ", "_")
                    res[f"mult_{base}"] = val / 100.0
                    break
    return res


df = pd.read_csv(CSV_PATH)
for col in [COL_PNL, COL_SCORE, COL_FORWARD_WR, COL_FORWARD_TRADES, COL_CONFLUENCE]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df[COL_ENTRY_TIME] = pd.to_datetime(df[COL_ENTRY_TIME], errors="coerce")
df = df.sort_values(COL_ENTRY_TIME).reset_index(drop=True)
df = df.dropna(subset=[COL_PNL, COL_SCORE])

parsed = df[COL_SCORE_BREAKDOWN].apply(parse_score_breakdown)
parsed_df = pd.DataFrame(list(parsed))
df = pd.concat([df, parsed_df], axis=1)

df["target_win"] = (df[COL_PNL] > 0).astype(int)
df["is_long"] = (df[COL_DIRECTION].astype(str).str.upper() == "LONG").astype(int)

tf_dummies = pd.get_dummies(df[COL_TIMEFRAME].astype(str).str.upper(), prefix="tf")
df = pd.concat([df, tf_dummies], axis=1)

trust_map = {"DEMOTED": -2, "SANDBOX": -1, "PROBATION": 0, "WATCH": 1, "RELIABLE": 2, "PROVEN": 3}
df["trust_code"] = df[COL_TRUST].astype(str).str.upper().map(trust_map).fillna(0)
grade_map = {"F": 0, "D": 1, "C": 2, "B": 3, "A": 4}
df["grade_code"] = df[COL_GRADE].astype(str).str.upper().map(grade_map).fillna(0)

feature_cols = [COL_SCORE, "grade_code"]
for key in COMPONENT_KEYS:
    base = key.lower().replace(" ", "_")
    for prefix in ["comp_", "w_"]:
        col = f"{prefix}{base}"
        if col in df.columns:
            feature_cols.append(col)
for key in MULT_KEYS:
    base = key.lower().replace(" ", "_")
    mcol = f"mult_{base}"
    if mcol in df.columns:
        feature_cols.append(mcol)

feature_cols.extend([COL_FORWARD_WR, COL_FORWARD_TRADES, COL_CONFLUENCE, "is_long", "trust_code"])
feature_cols.extend(tf_dummies.columns.tolist())

X = df[feature_cols].fillna(0.0)
y = df["target_win"]

N = len(df)
split_idx = int(0.8 * N)
X_train, X_test = X.iloc[:split_idx].values, X.iloc[split_idx:].values
y_train, y_test = y.iloc[:split_idx].values, y.iloc[split_idx:].values
df_test = df.iloc[split_idx:].copy()

# Logistic (with multipliers)
log_reg = LogisticRegression(C=1.0, solver="lbfgs", max_iter=2000)
log_reg.fit(X_train, y_train)
log_proba = log_reg.predict_proba(X_test)[:, 1]
auc_log = roc_auc_score(y_test, log_proba)

print(f"=== CHATGPT META-MODEL (with multipliers) ===")
print(f"Features: {len(feature_cols)}")
print(f"Logistic AUC: {auc_log:.4f}")

# Quintile analysis
def quintile_wr(probs, labels, q=5):
    dfq = pd.DataFrame({"p": probs, "y": labels}).sort_values("p").reset_index(drop=True)
    n = len(dfq)
    for i in range(q):
        lo, hi = int(i * n / q), int((i + 1) * n / q)
        chunk = dfq.iloc[lo:hi]
        print(f"  Q{i+1}: {len(chunk)} trades, WR {chunk['y'].mean()*100:.1f}%")

print("\nLogistic quintile WR:")
quintile_wr(log_proba, y_test)

# Decision tree
tree = DecisionTreeClassifier(max_depth=4, min_samples_leaf=50, random_state=42)
tree.fit(X_train, y_train)
tree_proba = tree.predict_proba(X_test)[:, 1]
auc_tree = roc_auc_score(y_test, tree_proba)
print(f"\nDecision Tree AUC: {auc_tree:.4f}")
print("\nDecision tree rules:")
print(export_text(tree, feature_names=feature_cols))

# Feature importance comparison
coef = log_reg.coef_[0]
print("\nLogistic coefficients (top 15 by |coef|):")
feat_coef = sorted(zip(feature_cols, coef), key=lambda t: abs(t[1]), reverse=True)
for name, c in feat_coef[:15]:
    print(f"  {name:25s} coef={c:+.4f}")

print(f"\nIntercept: {log_reg.intercept_[0]:.6f}")

tree_imp = sorted(zip(feature_cols, tree.feature_importances_), key=lambda t: t[1], reverse=True)
print("\nTree feature importance (top 10):")
for name, imp in tree_imp[:10]:
    print(f"  {name:25s} {imp:.4f}")

# JS function
print("\n--- JS metaScore function ---\n")
intercept = float(log_reg.intercept_[0])
print("function metaScore(f) {")
print(f"  let z = {intercept:.8f};")
for name, c in feat_coef:
    if abs(c) < 1e-6:
        continue
    print(f"  z += {c:+.8f} * (f['{name}'] || 0);")
print("  return 1.0 / (1.0 + Math.exp(-z));")
print("}")
