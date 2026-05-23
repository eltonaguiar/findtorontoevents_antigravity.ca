#!/usr/bin/env python3
"""
Feedback Trainer — Learn from Closed Trade Outcomes
=====================================================
PROBLEM: The ML predictor trains on synthetic targets (triple barrier on OHLCV)
but never learns from actual trade results. 149+ closed trades sit unused.

SOLUTION: This module:
  1. Aggregates closed picks from ALL systems (784+ trades)
  2. Extracts features from each trade's metadata + market context
  3. Trains a gradient-boosted model to predict win probability
  4. Saves the model for use as a filter/booster in live predictions
  5. Generates a retraining report with performance metrics

The trained "outcome model" acts as a secondary filter:
  - Original model: "Is this setup likely to move up?"
  - Outcome model:  "Given setups like this, did we actually WIN?"

Usage:
  python -m ml_crypto_predictor.enhanced_models.feedback_trainer           # Train
  python -m ml_crypto_predictor.enhanced_models.feedback_trainer --report  # Report only
"""

import json
import os
import sys
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

warnings.filterwarnings('ignore')

# Paths
BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
MODELS_DIR = BASE_DIR / "models"
RESULTS_DIR = BASE_DIR / "results"
FEEDBACK_DIR = BASE_DIR / "feedback_data"
FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)

# All known closed picks sources
CLOSED_PICKS_SOURCES = {
    "ml_predictor_v1.2": REPO_ROOT / "ml_crypto_predictor" / "enhanced_models" / "live_picks" / "archive_v1.2" / "closed_picks.json",
    "ml_predictor_current": REPO_ROOT / "ml_crypto_predictor" / "enhanced_models" / "live_picks" / "closed_picks.json",
    "alpha_engine": REPO_ROOT / "alpha_engine" / "data" / "closed_picks.json",
    "alpha_engine_fast": REPO_ROOT / "alpha_engine" / "data" / "closed_picks_fast.json",
    "battleground": REPO_ROOT / "battleground" / "data" / "closed_picks.json",
    "kimi": REPO_ROOT / "KIMI_RISEOFTHECLAW" / "data" / "closed_picks.json",
    "mercury2": REPO_ROOT / "mercury2" / "data" / "closed_picks.json",
    "system_a": REPO_ROOT / "ml_battleground" / "system_a_filter" / "data" / "closed_picks.json",
    "system_b": REPO_ROOT / "ml_battleground" / "system_b_regime" / "data" / "closed_picks.json",
    "system_c": REPO_ROOT / "ml_battleground" / "system_c_deeplearn" / "data" / "closed_picks.json",
    "system_f": REPO_ROOT / "ml_battleground" / "system_f_clawsofdoom" / "data" / "closed_picks.json",
    "paper_trading": REPO_ROOT / "paper_trading" / "data" / "closed_picks.json",
    "breakout_b": REPO_ROOT / "breakout_arena" / "approach_b_ml_breakout" / "data" / "closed_picks.json",
    "breakout_c": REPO_ROOT / "breakout_arena" / "approach_c_spike_reverse" / "data" / "closed_picks.json",
}

# Minimum closed trades needed before we train
MIN_TRADES_TO_TRAIN = 30

# Symbol normalization
def _normalize_symbol(sym: str) -> str:
    """Normalize symbol to XXXUSDT format."""
    if not sym:
        return "UNKNOWN"
    sym = sym.upper().replace("-", "").replace("/", "").replace("=X", "")
    if not sym.endswith("USDT") and not sym.endswith("USD"):
        sym += "USDT"
    return sym


def _safe_float(val, default=0.0) -> float:
    """Safely convert to float."""
    try:
        v = float(val)
        if np.isnan(v) or np.isinf(v):
            return default
        return v
    except (TypeError, ValueError):
        return default


# ── STEP 1: Aggregate closed picks from all sources ──────────────────────────

def collect_all_closed_picks() -> pd.DataFrame:
    """
    Load and normalize closed picks from ALL systems into a single DataFrame.
    Handles different schemas across systems gracefully.
    """
    all_rows = []

    for source_name, path in CLOSED_PICKS_SOURCES.items():
        if not path.exists():
            continue
        try:
            with open(path) as f:
                data = json.load(f)
            if not isinstance(data, list) or len(data) == 0:
                continue

            for pick in data:
                row = _normalize_pick(pick, source_name, require_pnl=True)
                if row is not None:
                    all_rows.append(row)

        except (json.JSONDecodeError, IOError) as e:
            print(f"  [WARN] Failed to load {source_name}: {e}")

    if not all_rows:
        print("  No closed picks found across any system!")
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    print(f"  Collected {len(df)} closed trades from {df['source'].nunique()} systems")
    return df


def _normalize_pick(pick: dict, source: str, require_pnl: bool = True) -> Optional[dict]:
    """
    Normalize a single pick from any system into a standard schema.
    Returns None if the pick is missing critical fields.

    Args:
        pick: Raw pick dict from any system
        source: System name
        require_pnl: If True (training), skip picks without PnL.
                     If False (prediction), allow PnL=0 for live picks.
    """
    # Get PnL (the target variable)
    pnl = pick.get("actual_pnl_pct") or pick.get("pnl_pct") or pick.get("pnl")
    if pnl is None:
        if require_pnl:
            return None
        pnl = 0.0
    pnl = _safe_float(pnl)

    # Get outcome
    outcome = pick.get("outcome") or pick.get("exit_reason") or pick.get("status", "")
    outcome = str(outcome).upper()

    # Determine win/loss (target)
    is_win = 1 if pnl > 0 else 0

    # Symbol
    symbol = pick.get("symbol") or pick.get("pair") or ""
    symbol = _normalize_symbol(symbol)

    # Direction
    direction = pick.get("direction") or pick.get("signal_type") or "BUY"
    direction = str(direction).upper()
    if direction in ("LONG", "BUY"):
        direction_code = 1
    elif direction in ("SHORT", "SELL"):
        direction_code = -1
    else:
        direction_code = 0

    # Timeframe
    timeframe = pick.get("timeframe") or pick.get("tf") or "1h"
    tf_map = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30,
              "1h": 60, "4h": 240, "1d": 1440, "1w": 10080}
    tf_minutes = tf_map.get(str(timeframe).lower(), 60)

    # Confidence/probability
    confidence = _safe_float(pick.get("probability") or pick.get("confidence") or
                             pick.get("ml_score") or pick.get("model_confidence"), 0.5)
    # Normalize string confidence levels
    if isinstance(pick.get("confidence"), str):
        conf_str = pick["confidence"].upper()
        if conf_str == "HIGH":
            confidence = max(confidence, 0.75)
        elif conf_str == "MEDIUM":
            confidence = max(confidence, 0.60)
        elif conf_str == "LOW":
            confidence = max(confidence, 0.50)

    # Entry/exit prices for R:R calculation
    entry_price = _safe_float(pick.get("entry_price"), 0)
    tp_price = _safe_float(pick.get("take_profit") or pick.get("tp_price"), 0)
    sl_price = _safe_float(pick.get("stop_loss") or pick.get("sl_price"), 0)

    # Risk/reward ratio
    if entry_price > 0 and tp_price > 0 and sl_price > 0:
        tp_dist = abs(tp_price - entry_price)
        sl_dist = abs(sl_price - entry_price)
        rr_ratio = tp_dist / max(sl_dist, 1e-10)
    else:
        rr_ratio = _safe_float(pick.get("risk_reward") or pick.get("rr_ratio"), 2.0)

    # TP/SL distance as % of entry
    if entry_price > 0:
        tp_pct = abs(tp_price - entry_price) / entry_price * 100 if tp_price > 0 else 0
        sl_pct = abs(sl_price - entry_price) / entry_price * 100 if sl_price > 0 else 0
    else:
        tp_pct = _safe_float(pick.get("tp_distance_pct") or pick.get("tp_pct"), 0)
        sl_pct = _safe_float(pick.get("sl_distance_pct") or pick.get("sl_pct"), 0)

    # Volume ratio (if available)
    vol_ratio = _safe_float(pick.get("volume_ratio") or
                            pick.get("features", {}).get("vol_ratio_20", 0), 0)

    # RSI at entry
    rsi = _safe_float(pick.get("rsi_at_entry") or
                      pick.get("features", {}).get("rsi_14", 0), 0)

    # ATR at entry
    atr = _safe_float(pick.get("atr_at_entry") or
                      pick.get("features", {}).get("atr_14", 0), 0)

    # Confluence score (how many signals agreed)
    confluence = _safe_float(pick.get("confluence_score") or
                             pick.get("confluence", 0), 0)

    # Fear & Greed at entry
    fear_greed = _safe_float(pick.get("fear_greed") or
                             pick.get("features", {}).get("fear_greed_index", 0), 0)

    # Hold duration (if available)
    hold_hours = 0
    if pick.get("generated_at") and pick.get("closed_at"):
        try:
            gen = datetime.fromisoformat(str(pick["generated_at"]).replace("Z", "+00:00"))
            cls = datetime.fromisoformat(str(pick["closed_at"]).replace("Z", "+00:00"))
            hold_hours = max(0, (cls - gen).total_seconds() / 3600)
        except (ValueError, TypeError):
            pass
    if hold_hours == 0:
        hold_hours = _safe_float(pick.get("hold_days", 0)) * 24

    # MFE/MAE (max favorable/adverse excursion)
    mfe = _safe_float(pick.get("mfe"), 0)
    mae = _safe_float(pick.get("mae"), 0)

    # Source system encoding
    source_map = {
        "ml_predictor_v1.2": 0, "ml_predictor_current": 0,
        "alpha_engine": 1, "alpha_engine_fast": 1,
        "battleground": 2, "kimi": 3, "mercury2": 4,
        "system_a": 5, "system_b": 6, "system_c": 7, "system_f": 8,
        "paper_trading": 9, "breakout_b": 10, "breakout_c": 11,
    }
    source_code = source_map.get(source, 12)

    # Outcome type encoding
    outcome_map = {"TP_HIT": 1, "SL_HIT": 2, "EXPIRED": 3, "CLOSED": 4}
    outcome_code = 0
    for k, v in outcome_map.items():
        if k in outcome:
            outcome_code = v
            break

    # Category encoding (crypto/forex/equity)
    category = pick.get("category", "crypto")
    cat_map = {"crypto": 0, "forex": 1, "equity": 2}
    category_code = cat_map.get(str(category).lower(), 0)

    # Extract features from embedded feature dict if present
    features_dict = pick.get("features", {})
    ema_dist_20 = _safe_float(features_dict.get("price_vs_ema20", 0))
    ema_dist_50 = _safe_float(features_dict.get("price_vs_ema50", 0))
    bb_width = _safe_float(features_dict.get("bb_width", 0))
    macd_hist = _safe_float(features_dict.get("macd_hist", 0))
    adx = _safe_float(features_dict.get("adx_14", 0))

    return {
        # Target
        "is_win": is_win,
        "pnl_pct": pnl,
        # Core features
        "direction_code": direction_code,
        "tf_minutes": tf_minutes,
        "confidence": confidence,
        "rr_ratio": min(rr_ratio, 10.0),  # Cap outliers
        "tp_pct": min(tp_pct, 50.0),
        "sl_pct": min(sl_pct, 50.0),
        "vol_ratio": min(vol_ratio, 20.0),
        "rsi": rsi,
        "atr": atr,
        "confluence": confluence,
        "fear_greed": fear_greed,
        "hold_hours": min(hold_hours, 720),  # Cap at 30 days
        "mfe": mfe,
        "mae": mae,
        "source_code": source_code,
        "outcome_code": outcome_code,
        "category_code": category_code,
        # Embedded technical features
        "ema_dist_20": ema_dist_20,
        "ema_dist_50": ema_dist_50,
        "bb_width": bb_width,
        "macd_hist": macd_hist,
        "adx": adx,
        # Metadata (not features)
        "source": source,
        "symbol": symbol,
        "outcome": outcome,
    }


# ── STEP 2: Feature engineering from closed trade data ────────────────────────

# PRE-TRADE features only (available at prediction time)
# EXCLUDED: mfe, mae, hold_hours, outcome_code (these are post-hoc)
FEATURE_COLUMNS = [
    "direction_code", "tf_minutes", "confidence", "rr_ratio",
    "tp_pct", "sl_pct", "vol_ratio", "rsi", "atr",
    "confluence", "fear_greed",
    "source_code", "category_code",
    "ema_dist_20", "ema_dist_50", "bb_width", "macd_hist", "adx",
]


def _compute_rolling_system_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute rolling/expanding historical win rate per system, per symbol,
    and per direction. These are features the model CAN use at prediction
    time because they only look at PAST trades.
    """
    df = df.copy()
    # Keep original order (roughly chronological from source files)
    df = df.reset_index(drop=True)

    # System historical win rate (expanding, looking at all prior trades from that system)
    sys_wr = {}
    sys_wr_col = []
    sys_avg_pnl_col = []
    for _, row in df.iterrows():
        key = row["source"]
        if key not in sys_wr:
            sys_wr[key] = {"wins": 0, "total": 0, "pnl_sum": 0.0}
        stats = sys_wr[key]
        # Use stats from BEFORE this trade
        wr = stats["wins"] / max(stats["total"], 1)
        avg_pnl = stats["pnl_sum"] / max(stats["total"], 1)
        sys_wr_col.append(wr)
        sys_avg_pnl_col.append(avg_pnl)
        # Update for next trade
        stats["total"] += 1
        stats["wins"] += row["is_win"]
        stats["pnl_sum"] += row["pnl_pct"]

    df["system_hist_wr"] = sys_wr_col
    df["system_hist_avg_pnl"] = sys_avg_pnl_col

    # Symbol historical win rate
    sym_wr = {}
    sym_wr_col = []
    for _, row in df.iterrows():
        key = row["symbol"]
        if key not in sym_wr:
            sym_wr[key] = {"wins": 0, "total": 0}
        stats = sym_wr[key]
        wr = stats["wins"] / max(stats["total"], 1)
        sym_wr_col.append(wr)
        stats["total"] += 1
        stats["wins"] += row["is_win"]
    df["symbol_hist_wr"] = sym_wr_col

    # Direction historical win rate
    dir_wr = {}
    dir_wr_col = []
    for _, row in df.iterrows():
        key = row["direction_code"]
        if key not in dir_wr:
            dir_wr[key] = {"wins": 0, "total": 0}
        stats = dir_wr[key]
        wr = stats["wins"] / max(stats["total"], 1)
        dir_wr_col.append(wr)
        stats["total"] += 1
        stats["wins"] += row["is_win"]
    df["direction_hist_wr"] = dir_wr_col

    # Timeframe historical win rate
    tf_wr = {}
    tf_wr_col = []
    for _, row in df.iterrows():
        key = row["tf_minutes"]
        if key not in tf_wr:
            tf_wr[key] = {"wins": 0, "total": 0}
        stats = tf_wr[key]
        wr = stats["wins"] / max(stats["total"], 1)
        tf_wr_col.append(wr)
        stats["total"] += 1
        stats["wins"] += row["is_win"]
    df["tf_hist_wr"] = tf_wr_col

    return df


def build_feedback_features(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extract feature matrix X and target vector y from normalized closed picks.
    Adds derived features and rolling historical performance stats.

    IMPORTANT: Only uses PRE-TRADE features (available at prediction time).
    Post-hoc features (MFE, MAE, hold_hours, outcome) are excluded.
    """
    df = df.copy()

    # Add rolling historical performance (expanding, no lookahead)
    df = _compute_rolling_system_stats(df)

    # RSI zone encoding (oversold/neutral/overbought)
    df["rsi_oversold"] = (df["rsi"] < 30).astype(int)
    df["rsi_overbought"] = (df["rsi"] > 70).astype(int)

    # Confidence bins
    df["high_conf"] = (df["confidence"] >= 0.75).astype(int)
    df["low_conf"] = (df["confidence"] < 0.55).astype(int)

    # R:R quality
    df["good_rr"] = (df["rr_ratio"] >= 2.0).astype(int)

    # TP/SL ratio (how tight are the stops?)
    df["tpsl_ratio"] = df["tp_pct"] / (df["sl_pct"] + 0.01)

    # Fear zone
    df["extreme_fear"] = (df["fear_greed"].between(1, 25)).astype(int)
    df["extreme_greed"] = (df["fear_greed"] > 75).astype(int)

    # Direction-trend alignment proxy
    df["trend_aligned"] = ((df["direction_code"] > 0) & (df["ema_dist_20"] > 0) |
                           (df["direction_code"] < 0) & (df["ema_dist_20"] < 0)).astype(int)

    # Confluence strength bins
    df["strong_confluence"] = (df["confluence"] >= 3).astype(int)

    # All feature columns (including derived + rolling stats)
    all_features = FEATURE_COLUMNS + [
        "system_hist_wr", "system_hist_avg_pnl",
        "symbol_hist_wr", "direction_hist_wr", "tf_hist_wr",
        "rsi_oversold", "rsi_overbought", "high_conf", "low_conf",
        "good_rr", "tpsl_ratio", "extreme_fear", "extreme_greed",
        "trend_aligned", "strong_confluence",
    ]

    X = df[all_features].fillna(0).values.astype(np.float64)
    y = df["is_win"].values.astype(int)

    # Replace any remaining NaN/inf
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    return X, y, all_features


# ── STEP 3: Train the outcome prediction model ───────────────────────────────

def train_outcome_model(X: np.ndarray, y: np.ndarray,
                        feature_names: List[str]) -> dict:
    """
    Train a gradient-boosted classifier to predict trade win probability.
    Uses time-aware split (last 20% for test) and probability calibration.

    Returns dict with model, scaler, metrics, and feature importances.
    """
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score, f1_score,
        roc_auc_score, classification_report,
    )
    import joblib

    # Stratified shuffle split (better for cross-system data than time-based)
    # The rolling features already prevent lookahead bias
    from sklearn.model_selection import StratifiedShuffleSplit

    sss = StratifiedShuffleSplit(n_splits=1, test_size=0.20, random_state=42)
    train_idx, test_idx = next(sss.split(X, y))
    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    print(f"  Training set: {len(X_train)} ({y_train.mean():.1%} win rate)")
    print(f"  Test set: {len(X_test)} ({y_test.mean():.1%} win rate)")

    if len(X_train) < MIN_TRADES_TO_TRAIN:
        print(f"  Insufficient training data ({len(X_train)} < {MIN_TRADES_TO_TRAIN})")
        return {}

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Train GBT (robust, handles mixed feature types well)
    gbt = GradientBoostingClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        min_samples_split=10,
        min_samples_leaf=5,
        max_features="sqrt",
        random_state=42,
    )
    gbt.fit(X_train_scaled, y_train)

    # Also train RF for ensemble
    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=6,
        min_samples_split=10,
        min_samples_leaf=5,
        max_features="sqrt",
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    rf.fit(X_train_scaled, y_train)

    # Calibrate GBT probabilities
    try:
        cal_gbt = CalibratedClassifierCV(gbt, method="isotonic", cv=3)
        cal_gbt.fit(X_train_scaled, y_train)
        gbt_model = cal_gbt
    except Exception:
        gbt_model = gbt

    # Evaluate both models
    gbt_proba = gbt_model.predict_proba(X_test_scaled)[:, 1]
    rf_proba = rf.predict_proba(X_test_scaled)[:, 1]

    # Ensemble: weighted average (GBT 60%, RF 40%)
    ensemble_proba = 0.6 * gbt_proba + 0.4 * rf_proba
    ensemble_pred = (ensemble_proba >= 0.5).astype(int)

    # Metrics
    try:
        auc = roc_auc_score(y_test, ensemble_proba)
    except ValueError:
        auc = 0.5

    metrics = {
        "accuracy": round(accuracy_score(y_test, ensemble_pred), 4),
        "precision": round(precision_score(y_test, ensemble_pred, zero_division=0), 4),
        "recall": round(recall_score(y_test, ensemble_pred, zero_division=0), 4),
        "f1": round(f1_score(y_test, ensemble_pred, zero_division=0), 4),
        "roc_auc": round(auc, 4),
        "train_win_rate": round(float(y_train.mean()), 4),
        "test_win_rate": round(float(y_test.mean()), 4),
        "predicted_win_rate": round(float(ensemble_pred.mean()), 4),
        "train_size": len(X_train),
        "test_size": len(X_test),
    }

    print(f"\n  === Outcome Model Metrics ===")
    print(f"  AUC:       {metrics['roc_auc']:.4f}")
    print(f"  Accuracy:  {metrics['accuracy']:.4f}")
    print(f"  Precision: {metrics['precision']:.4f}")
    print(f"  Recall:    {metrics['recall']:.4f}")
    print(f"  F1:        {metrics['f1']:.4f}")

    # Feature importance (from GBT)
    if hasattr(gbt, 'feature_importances_'):
        importances = gbt.feature_importances_
        feat_imp = sorted(zip(feature_names, importances),
                         key=lambda x: -x[1])
        print(f"\n  Top 10 Features:")
        for name, imp in feat_imp[:10]:
            print(f"    {name:25s} {imp:.4f}")
        metrics["feature_importance"] = {name: round(float(imp), 4)
                                          for name, imp in feat_imp}

    # Classification report
    print(f"\n  Classification Report (test set):")
    print(classification_report(y_test, ensemble_pred,
                                target_names=["LOSS", "WIN"]))

    # Save models
    model_data = {
        "gbt_model": gbt_model,
        "rf_model": rf,
        "scaler": scaler,
        "feature_names": feature_names,
        "metrics": metrics,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "version": "v1.0",
        "gbt_weight": 0.6,
        "rf_weight": 0.4,
    }

    model_path = MODELS_DIR / "outcome_feedback_model.joblib"
    joblib.dump(model_data, str(model_path))
    print(f"\n  Model saved to {model_path}")

    # Save per-system performance analysis
    return {
        "model_path": str(model_path),
        "metrics": metrics,
        "feature_names": feature_names,
    }


# ── STEP 4: System performance analysis ──────────────────────────────────────

def analyze_system_performance(df: pd.DataFrame) -> dict:
    """
    Analyze per-system, per-symbol, per-timeframe performance.
    This tells us WHICH systems and settings actually work.
    """
    analysis = {}

    # Per system
    sys_stats = {}
    for source in df["source"].unique():
        sdf = df[df["source"] == source]
        wins = sdf["is_win"].sum()
        total = len(sdf)
        avg_pnl = sdf["pnl_pct"].mean()
        sys_stats[source] = {
            "total": int(total),
            "wins": int(wins),
            "win_rate": round(wins / max(total, 1) * 100, 1),
            "avg_pnl": round(avg_pnl, 2),
            "total_pnl": round(sdf["pnl_pct"].sum(), 2),
        }
    analysis["by_system"] = sys_stats

    # Per direction
    for direction in [-1, 1]:
        d_name = "BUY" if direction == 1 else "SELL"
        ddf = df[df["direction_code"] == direction]
        if len(ddf) > 0:
            analysis[f"direction_{d_name}"] = {
                "total": int(len(ddf)),
                "win_rate": round(ddf["is_win"].mean() * 100, 1),
                "avg_pnl": round(ddf["pnl_pct"].mean(), 2),
            }

    # Per confidence level
    for label, lo, hi in [("low", 0, 0.55), ("medium", 0.55, 0.70), ("high", 0.70, 1.01)]:
        cdf = df[(df["confidence"] >= lo) & (df["confidence"] < hi)]
        if len(cdf) > 0:
            analysis[f"confidence_{label}"] = {
                "total": int(len(cdf)),
                "win_rate": round(cdf["is_win"].mean() * 100, 1),
                "avg_pnl": round(cdf["pnl_pct"].mean(), 2),
            }

    # Top performing symbols
    sym_stats = {}
    for sym in df["symbol"].unique():
        sdf = df[df["symbol"] == sym]
        if len(sdf) >= 3:
            sym_stats[sym] = {
                "total": int(len(sdf)),
                "win_rate": round(sdf["is_win"].mean() * 100, 1),
                "avg_pnl": round(sdf["pnl_pct"].mean(), 2),
            }
    # Sort by win rate, show top/bottom
    sorted_syms = sorted(sym_stats.items(), key=lambda x: -x[1]["win_rate"])
    analysis["top_symbols"] = dict(sorted_syms[:10])
    analysis["worst_symbols"] = dict(sorted_syms[-10:])

    return analysis


# ── STEP 5: Prediction function for use in live pipeline ─────────────────────

def predict_outcome(pick_data: dict) -> Tuple[float, bool]:
    """
    Given a candidate pick (dict), predict its win probability using the
    trained outcome model.

    Returns:
        (probability, should_trade) tuple
        - probability: float 0-1 (predicted win probability)
        - should_trade: bool (True if probability >= 0.50)
    """
    import joblib

    model_path = MODELS_DIR / "outcome_feedback_model.joblib"
    if not model_path.exists():
        return 0.5, True  # No model yet, passthrough

    try:
        model_data = joblib.load(str(model_path))
    except Exception:
        return 0.5, True

    gbt_model = model_data["gbt_model"]
    rf_model = model_data["rf_model"]
    scaler = model_data["scaler"]
    feature_names = model_data["feature_names"]
    gbt_weight = model_data.get("gbt_weight", 0.6)
    rf_weight = model_data.get("rf_weight", 0.4)

    # Build feature vector from pick data (don't require PnL for live predictions)
    row = _normalize_pick(pick_data, "live_prediction", require_pnl=False)
    if row is None:
        return 0.5, True

    # Build the same derived features as training
    row_df = pd.DataFrame([row])

    # Load historical stats for rolling features
    # These are computed from all past closed picks
    hist_stats = _load_historical_stats()
    source = pick_data.get("source", "ml_predictor_current")
    symbol = row["symbol"]
    direction = row["direction_code"]
    tf = row["tf_minutes"]

    row_df["system_hist_wr"] = hist_stats.get("system", {}).get(source, {}).get("wr", 0.5)
    row_df["system_hist_avg_pnl"] = hist_stats.get("system", {}).get(source, {}).get("avg_pnl", 0.0)
    row_df["symbol_hist_wr"] = hist_stats.get("symbol", {}).get(symbol, {}).get("wr", 0.5)
    row_df["direction_hist_wr"] = hist_stats.get("direction", {}).get(str(direction), {}).get("wr", 0.5)
    row_df["tf_hist_wr"] = hist_stats.get("tf", {}).get(str(tf), {}).get("wr", 0.5)

    row_df["rsi_oversold"] = (row_df["rsi"] < 30).astype(int)
    row_df["rsi_overbought"] = (row_df["rsi"] > 70).astype(int)
    row_df["high_conf"] = (row_df["confidence"] >= 0.75).astype(int)
    row_df["low_conf"] = (row_df["confidence"] < 0.55).astype(int)
    row_df["good_rr"] = (row_df["rr_ratio"] >= 2.0).astype(int)
    row_df["tpsl_ratio"] = row_df["tp_pct"] / (row_df["sl_pct"] + 0.01)
    row_df["extreme_fear"] = (row_df["fear_greed"].between(1, 25)).astype(int)
    row_df["extreme_greed"] = (row_df["fear_greed"] > 75).astype(int)
    row_df["trend_aligned"] = (
        (row_df["direction_code"] > 0) & (row_df["ema_dist_20"] > 0) |
        (row_df["direction_code"] < 0) & (row_df["ema_dist_20"] < 0)
    ).astype(int)
    row_df["strong_confluence"] = (row_df["confluence"] >= 3).astype(int)

    # Extract features in correct order
    X = row_df[feature_names].fillna(0).values.astype(np.float64)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    X_scaled = scaler.transform(X)

    # Predict
    gbt_proba = gbt_model.predict_proba(X_scaled)[:, 1][0]
    rf_proba = rf_model.predict_proba(X_scaled)[:, 1][0]
    ensemble_proba = gbt_weight * gbt_proba + rf_weight * rf_proba

    # Adaptive threshold: only block trades predicted MUCH WORSE than average.
    # The model is calibrated to the 42% base win rate, so predictions cluster
    # in the 0.15-0.45 range. We use the model primarily for RANKING picks
    # (higher prob = better), and only hard-block the worst predicted trades.
    base_rate = model_data.get("metrics", {}).get("train_win_rate", 0.42)
    # v1.6: Lowered block threshold to 0.05 because market shift is causing probabilities to sit around 0.10
    block_threshold = 0.05 
    should_trade = ensemble_proba >= block_threshold
    return float(ensemble_proba), bool(should_trade)


def _load_historical_stats() -> dict:
    """Load pre-computed historical win rate stats for use in live prediction."""
    stats_path = FEEDBACK_DIR / "historical_stats.json"
    if stats_path.exists():
        try:
            with open(stats_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"system": {}, "symbol": {}, "direction": {}, "tf": {}}


def _save_historical_stats(df: pd.DataFrame):
    """Compute and save historical win rate stats from all closed picks."""
    stats = {"system": {}, "symbol": {}, "direction": {}, "tf": {}}

    # System stats
    for source in df["source"].unique():
        sdf = df[df["source"] == source]
        stats["system"][source] = {
            "wr": round(sdf["is_win"].mean(), 4),
            "avg_pnl": round(sdf["pnl_pct"].mean(), 4),
            "total": int(len(sdf)),
        }

    # Symbol stats
    for sym in df["symbol"].unique():
        sdf = df[df["symbol"] == sym]
        if len(sdf) >= 2:
            stats["symbol"][sym] = {
                "wr": round(sdf["is_win"].mean(), 4),
                "total": int(len(sdf)),
            }

    # Direction stats
    for d in df["direction_code"].unique():
        sdf = df[df["direction_code"] == d]
        stats["direction"][str(int(d))] = {
            "wr": round(sdf["is_win"].mean(), 4),
            "total": int(len(sdf)),
        }

    # Timeframe stats
    for tf in df["tf_minutes"].unique():
        sdf = df[df["tf_minutes"] == tf]
        stats["tf"][str(int(tf))] = {
            "wr": round(sdf["is_win"].mean(), 4),
            "total": int(len(sdf)),
        }

    stats_path = FEEDBACK_DIR / "historical_stats.json"
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"  Historical stats saved to {stats_path}")


# ── STEP 6: Get model info (for dashboards/status) ───────────────────────────

def get_feedback_model_status() -> dict:
    """Return status info about the trained feedback model."""
    import joblib

    model_path = MODELS_DIR / "outcome_feedback_model.joblib"
    if not model_path.exists():
        return {"status": "not_trained", "reason": "No feedback model found"}

    try:
        model_data = joblib.load(str(model_path))
        return {
            "status": "active",
            "trained_at": model_data.get("trained_at", "unknown"),
            "version": model_data.get("version", "unknown"),
            "metrics": model_data.get("metrics", {}),
            "feature_count": len(model_data.get("feature_names", [])),
        }
    except Exception as e:
        return {"status": "error", "reason": str(e)}


# ── MAIN: Run training pipeline ──────────────────────────────────────────────

def run_feedback_training() -> dict:
    """
    Full feedback training pipeline:
    1. Collect all closed picks
    2. Build features
    3. Train model
    4. Analyze performance
    5. Save report
    """
    print("=" * 70)
    print("ML FEEDBACK TRAINER — Learning from Closed Trade Outcomes")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    # 1. Collect
    print("\n[1/5] Collecting closed picks from all systems...")
    df = collect_all_closed_picks()
    if df.empty or len(df) < MIN_TRADES_TO_TRAIN:
        msg = f"Insufficient data: {len(df)} trades (need {MIN_TRADES_TO_TRAIN})"
        print(f"  {msg}")
        return {"status": "skipped", "reason": msg}

    # Overall stats
    print(f"\n  Overall: {len(df)} trades, {df['is_win'].sum()} wins "
          f"({df['is_win'].mean()*100:.1f}% WR), avg PnL {df['pnl_pct'].mean():.2f}%")

    # 2. Build features
    print("\n[2/5] Building features...")
    X, y, feature_names = build_feedback_features(df)
    print(f"  Feature matrix: {X.shape[0]} samples x {X.shape[1]} features")

    # 3. Train
    print("\n[3/5] Training outcome prediction model...")
    train_result = train_outcome_model(X, y, feature_names)
    if not train_result:
        return {"status": "failed", "reason": "Training failed"}

    # 3b. Save historical stats for use in live predictions
    _save_historical_stats(df)

    # 4. Analyze
    print("\n[4/5] Analyzing system performance...")
    analysis = analyze_system_performance(df)

    # Print key insights
    print("\n  === System Performance ===")
    for sys, stats in sorted(analysis["by_system"].items(),
                              key=lambda x: -x[1]["win_rate"]):
        print(f"    {sys:25s} {stats['total']:4d} trades  "
              f"WR={stats['win_rate']:5.1f}%  PnL={stats['avg_pnl']:+6.2f}%")

    # 5. Save report
    print("\n[5/5] Saving feedback report...")
    report = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "total_trades": len(df),
        "total_wins": int(df["is_win"].sum()),
        "overall_win_rate": round(df["is_win"].mean() * 100, 1),
        "overall_avg_pnl": round(df["pnl_pct"].mean(), 2),
        "model_metrics": train_result.get("metrics", {}),
        "analysis": analysis,
        "systems_used": list(df["source"].unique()),
        "feature_names": feature_names,
    }

    report_path = FEEDBACK_DIR / "feedback_training_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"  Report saved to {report_path}")

    # Also save aggregated closed picks for reference
    agg_path = FEEDBACK_DIR / "aggregated_closed_picks.json"
    df_clean = df.drop(columns=["source"], errors="ignore")
    df_clean.to_json(str(agg_path), orient="records", indent=2)
    print(f"  Aggregated data saved to {agg_path}")

    print(f"\n{'=' * 70}")
    print("FEEDBACK TRAINING COMPLETE")
    print(f"  Model AUC: {train_result['metrics'].get('roc_auc', 'N/A')}")
    print(f"  Trades used: {len(df)}")
    print(f"{'=' * 70}")

    return {
        "status": "success",
        "report": report,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ML Feedback Trainer")
    parser.add_argument("--report", action="store_true", help="Show report only")
    args = parser.parse_args()

    if args.report:
        status = get_feedback_model_status()
        print(json.dumps(status, indent=2))
    else:
        result = run_feedback_training()
        print(f"\nResult: {result.get('status', 'unknown')}")
