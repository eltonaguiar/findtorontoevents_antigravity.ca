#!/usr/bin/env python3
"""
Online Meta-Learner — Incremental XGBoost update on newly closed trades.

Instead of full weekly retraining (meta_label_v2.py processes 5000+ trades),
this script fine-tunes the existing meta-label model on each day's batch of
new closed trades (typically 5-20/day).

Benefits:
  - Fast: processes only new trades, not entire history
  - Responsive: new patterns are learned within hours, not a week
  - Efficient: leverages xgb_model parameter for warm-start training
  - Safe: backs up model before each update, rolls back on degradation

Pipeline:
  1. Detect new closed trades since last run (via timestamp file)
  2. Compute same 35 features as meta_label_v2.py (regime, strategy, market context)
  3. Load existing model and incrementally train on new batch
  4. Recalibrate per-algorithm thresholds on last 100 trades
  5. Track performance drift (precision, recall, F1 before vs after)
  6. Update lm_ml_status entry for the meta-label model

Safety Guards:
  - Skip if batch < 3 trades (too noisy)
  - Skip if precision drops below 0.50 on recent data (flag for full retrain)
  - Maximum 1 update per day (deduplicated via timestamp file)
  - Backup of previous model before each update

Usage:
  python scripts/online_meta_learner.py              # normal run
  python scripts/online_meta_learner.py --dry-run    # preview only, no model save
  python scripts/online_meta_learner.py --force      # force update even if few trades

Requires: pip install xgboost scikit-learn pandas numpy mysql-connector-python
"""

import os
import sys
import json
import time
import shutil
import logging
import argparse
import warnings
import traceback
import numpy as np
import pandas as pd
import mysql.connector
from datetime import datetime, timedelta
from collections import defaultdict

warnings.filterwarnings("ignore")

try:
    from sklearn.metrics import (
        precision_score, recall_score, f1_score,
        accuracy_score, roc_auc_score
    )
    from xgboost import XGBClassifier
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install: pip install xgboost scikit-learn pandas numpy mysql-connector-python")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("online_meta_learner")

# Database config
DB_HOST = os.environ.get("DB_HOST", "mysql.50webs.com")
DB_USER = os.environ.get("DB_USER", "ejaguiar1_stocks")
DB_PASS = os.environ.get("DB_PASS", "stocks")
DB_NAME = os.environ.get("DB_NAME", "ejaguiar1_stocks")

# API config
API_BASE = os.environ.get("API_BASE", "https://findtorontoevents.ca/live-monitor/api")
ADMIN_KEY = os.environ.get("ADMIN_KEY", "livetrader2026")
API_HEADERS = {"User-Agent": "WorldClassIntelligence/1.0"}

# File paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(SCRIPT_DIR, "models")
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
MODEL_PATH = os.path.join(MODEL_DIR, "meta_label_v2.json")
BACKUP_PATH = os.path.join(MODEL_DIR, "meta_label_v2_backup.json")
THRESHOLDS_PATH = os.path.join(DATA_DIR, "meta_label_v2_thresholds.json")
LAST_RUN_PATH = os.path.join(DATA_DIR, "online_meta_last_run.json")

# Incremental training parameters
MIN_BATCH_SIZE = 3          # Minimum new trades to trigger update
MAX_UPDATES_PER_DAY = 1     # Deduplicate updates
INCREMENTAL_LR = 0.01       # Low learning rate for stability
INCREMENTAL_ROUNDS = 50     # Boosting rounds per incremental update
PRECISION_FLOOR = 0.50      # If precision drops below this, flag for full retrain
RECALL_FLOOR = 0.30         # Minimum recall to keep threshold
RECENT_WINDOW = 100         # Number of recent trades per algo for threshold recalibration
DEFAULT_THRESHOLD = 0.60
AGGRESSIVE_THRESHOLD = 0.70

# Algorithm lists (must match meta_label_v2.py and live-monitor)
MOMENTUM_ALGOS = [
    "Momentum Burst", "Breakout 24h", "Volatility Breakout",
    "Trend Sniper", "Volume Spike", "VAM",
    "ADX Trend Strength", "Alpha Predator"
]

MEAN_REVERSION_ALGOS = [
    "RSI Reversal", "DCA Dip", "Dip Recovery",
    "Mean Reversion Sniper", "Bollinger Squeeze",
    "StochRSI Crossover", "RSI(2) Scalp"
]

FUNDAMENTAL_ALGOS = [
    "Insider Cluster Buy", "13F New Position", "Consensus"
]

SENTIMENT_ALGOS = [
    "Sentiment Divergence", "Contrarian Fear/Greed"
]

ALL_ALGOS = [
    "Momentum Burst", "RSI Reversal", "Breakout 24h", "DCA Dip",
    "Bollinger Squeeze", "MACD Crossover", "Consensus",
    "Volatility Breakout", "Trend Sniper", "Dip Recovery",
    "Volume Spike", "VAM", "Mean Reversion Sniper",
    "ADX Trend Strength", "StochRSI Crossover", "Awesome Oscillator",
    "RSI(2) Scalp", "Ichimoku Cloud", "Alpha Predator",
    "Insider Cluster Buy", "13F New Position",
    "Sentiment Divergence", "Contrarian Fear/Greed"
]

BUNDLE_MAP = {}
for algo in MOMENTUM_ALGOS:
    BUNDLE_MAP[algo] = "momentum"
for algo in MEAN_REVERSION_ALGOS:
    BUNDLE_MAP[algo] = "reversion"
for algo in FUNDAMENTAL_ALGOS:
    BUNDLE_MAP[algo] = "fundamental"
for algo in SENTIMENT_ALGOS:
    BUNDLE_MAP[algo] = "sentiment"
for algo in ALL_ALGOS:
    if algo not in BUNDLE_MAP:
        BUNDLE_MAP[algo] = "other"

# Feature names — must match meta_label_v2.py exactly (35 features)
FEATURE_NAMES = [
    # Original 11 (+2 time sub-features = 13 columns)
    "algo_id", "is_momentum", "is_mean_reversion",
    "asset_crypto", "asset_forex", "asset_stock",
    "is_long", "tp_sl_ratio", "position_value", "max_hold",
    "hour_of_day", "day_of_week", "is_weekend",
    # Regime (9)
    "hmm_regime_encoded", "hmm_confidence", "hurst_value",
    "hurst_regime_encoded", "ewma_vol_annualized", "vix_level",
    "vix_regime_encoded", "composite_score", "yield_spread",
    # Strategy context (4)
    "algo_rolling_sharpe_30d", "algo_win_rate_30d",
    "algo_consecutive_losses", "strategy_bundle_weight",
    # Market context (4)
    "atr_percentile", "recent_5d_return", "distance_from_peak",
    "cross_asset_divergence",
    # Trade quality (3)
    "signal_strength_normalized", "entry_hour_quality",
    "same_day_signal_count",
    # Interaction (4)
    "regime_momentum_align", "strength_x_regime",
    "vol_x_direction", "bundle_perf_align",
]


# ---------------------------------------------------------------------------
# Database Connection
# ---------------------------------------------------------------------------

def connect_db():
    """Connect to MySQL database with retry."""
    for attempt in range(3):
        try:
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASS,
                database=DB_NAME,
                connect_timeout=30,
                autocommit=True
            )
            return conn
        except mysql.connector.Error as e:
            logger.warning("DB connect attempt %d failed: %s", attempt + 1, e)
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise ConnectionError("Failed to connect to database after 3 attempts")


# ---------------------------------------------------------------------------
# Last Run Tracking
# ---------------------------------------------------------------------------

def load_last_run():
    """Load last run state from JSON file."""
    if os.path.exists(LAST_RUN_PATH):
        try:
            with open(LAST_RUN_PATH, "r") as f:
                data = json.load(f)
            return data
        except (json.JSONDecodeError, IOError):
            logger.warning("Could not read last run file, starting fresh")
    return {}


def save_last_run(data):
    """Save last run state to JSON file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(LAST_RUN_PATH, "w") as f:
        json.dump(data, f, indent=2)


def check_update_allowed(last_run, force=False):
    """
    Check if an update is allowed (max 1 per day).

    Returns:
        (allowed: bool, reason: str)
    """
    if force:
        return True, "Forced update via --force flag"

    last_ts = last_run.get("last_update_timestamp")
    if not last_ts:
        return True, "First run ever"

    try:
        last_dt = datetime.strptime(last_ts, "%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, TypeError):
        return True, "Invalid last timestamp, allowing update"

    now = datetime.utcnow()
    hours_since = (now - last_dt).total_seconds() / 3600

    if hours_since < 20:
        return False, f"Last update was {hours_since:.1f}h ago (need 20h+ gap)"

    return True, f"Last update was {hours_since:.1f}h ago"


# ---------------------------------------------------------------------------
# Data Fetching
# ---------------------------------------------------------------------------

def fetch_new_closed_trades(conn, since_timestamp):
    """
    Fetch trades closed since the given timestamp.

    Args:
        conn: MySQL connection
        since_timestamp: ISO string or None (fetch last 7 days if None)

    Returns:
        list of trade dicts
    """
    cur = conn.cursor(dictionary=True)

    if since_timestamp:
        try:
            since_dt = datetime.strptime(since_timestamp, "%Y-%m-%dT%H:%M:%SZ")
        except (ValueError, TypeError):
            since_dt = datetime.utcnow() - timedelta(days=7)
    else:
        # First run: fetch last 7 days of closed trades
        since_dt = datetime.utcnow() - timedelta(days=7)

    since_str = since_dt.strftime("%Y-%m-%d %H:%M:%S")
    logger.info("Fetching trades closed since %s...", since_str)

    try:
        cur.execute("""
            SELECT t.id, t.algorithm_name, t.symbol, t.asset_class,
                   t.direction, t.entry_price, t.exit_price,
                   t.entry_time, t.exit_time,
                   t.realized_pnl, t.realized_pct,
                   t.target_tp_pct, t.target_sl_pct,
                   t.max_hold_hours, t.exit_reason,
                   t.position_value_usd, t.signal_strength
            FROM lm_trades t
            WHERE t.exit_time IS NOT NULL
              AND t.realized_pnl IS NOT NULL
              AND t.exit_time > %s
            ORDER BY t.exit_time ASC
        """, (since_str,))
        trades = cur.fetchall()
        logger.info("  Found %d new closed trades", len(trades))
        return trades
    except mysql.connector.Error as e:
        logger.error("  Failed to fetch new trades: %s", e)
        return []


def fetch_recent_trades_for_context(conn, limit=200):
    """
    Fetch recent closed trades to build rolling algo history context.
    Needed for features like algo_rolling_wr, consecutive_losses, etc.
    """
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT t.id, t.algorithm_name, t.symbol, t.asset_class,
                   t.direction, t.entry_price, t.exit_price,
                   t.entry_time, t.exit_time,
                   t.realized_pnl, t.realized_pct,
                   t.target_tp_pct, t.target_sl_pct,
                   t.max_hold_hours, t.exit_reason,
                   t.position_value_usd, t.signal_strength
            FROM lm_trades t
            WHERE t.exit_time IS NOT NULL
              AND t.realized_pnl IS NOT NULL
            ORDER BY t.exit_time DESC
            LIMIT %s
        """, (limit,))
        trades = cur.fetchall()
        # Reverse to chronological order
        trades.reverse()
        logger.info("  Context trades loaded: %d", len(trades))
        return trades
    except mysql.connector.Error as e:
        logger.warning("  Context trades fetch failed: %s", e)
        return []


def fetch_regime_data(conn):
    """Fetch regime history from lm_market_regime table."""
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT asset_class, regime_date, hmm_regime, hmm_confidence,
                   hurst_value, hurst_regime, ewma_vol, vix_level,
                   composite_score, yield_spread
            FROM lm_market_regime
            ORDER BY regime_date ASC
        """)
        rows = cur.fetchall()
        logger.info("  Regime records: %d", len(rows))
        return rows
    except mysql.connector.Error as e:
        logger.warning("  Regime query failed: %s", e)
        return []


def fetch_signal_counts(conn):
    """Fetch daily signal counts for same-day noise detection."""
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT DATE(signal_time) AS signal_date,
                   algorithm_name,
                   COUNT(*) AS signal_count
            FROM lm_signals
            GROUP BY DATE(signal_time), algorithm_name
            ORDER BY signal_date ASC
        """)
        rows = cur.fetchall()
        lookup = {}
        for r in rows:
            key = (str(r["signal_date"]), r["algorithm_name"])
            lookup[key] = int(r["signal_count"])
        return lookup
    except mysql.connector.Error as e:
        logger.warning("  Signal count query failed: %s", e)
        return {}


# ---------------------------------------------------------------------------
# Feature Engineering (matches meta_label_v2.py exactly)
# ---------------------------------------------------------------------------

def encode_hmm_regime(hmm_regime):
    """Encode HMM regime label: 0=bear, 1=sideways, 2=bull."""
    mapping = {"bear": 0, "sideways": 1, "bull": 2}
    if isinstance(hmm_regime, str):
        return mapping.get(hmm_regime.lower(), 1)
    return 1


def encode_vix_regime(vix_level):
    """Encode VIX level into regime integer: 0-4."""
    vix = float(vix_level) if vix_level is not None else 20.0
    if vix < 12:
        return 0
    elif vix < 18:
        return 1
    elif vix < 25:
        return 2
    elif vix < 35:
        return 3
    else:
        return 4


def encode_hurst_regime(hurst_value):
    """Encode Hurst exponent: 0=mean_reverting, 1=random, 2=trending."""
    h = float(hurst_value) if hurst_value is not None else 0.5
    if h < 0.45:
        return 0
    elif h < 0.55:
        return 1
    else:
        return 2


def compute_entry_hour_quality(hour):
    """Score entry hour quality based on market liquidity patterns."""
    h = int(hour) if hour is not None else 12
    if 10 <= h <= 15:
        return 1.0
    elif h == 9 or h == 16:
        return 0.7
    elif 17 <= h <= 20:
        return 0.4
    elif 4 <= h <= 8:
        return 0.3
    else:
        return 0.2


def compute_cross_asset_divergence(asset_class, hmm_regime, composite_score):
    """Compute cross-asset divergence signal (matches meta_label_v2.py)."""
    if 35 <= composite_score <= 65:
        return 0.5 + (0.5 - abs(composite_score - 50) / 50)
    elif asset_class == "CRYPTO" and hmm_regime == 0:
        return 0.7
    elif asset_class == "FOREX":
        return 0.3
    return 0.0


def engineer_features_for_trades(trades, regime_data, signal_counts,
                                  context_trades=None):
    """
    Engineer 35 features for a list of trades — identical feature set to meta_label_v2.py.

    Args:
        trades: list of trade dicts (the new batch to featurize)
        regime_data: list of regime rows from lm_market_regime
        signal_counts: dict of (date_str, algo) -> count
        context_trades: prior trades for rolling algo history (optional)

    Returns:
        X: numpy array of features (n_trades x 35)
        y: numpy array of labels (1=win, 0=loss)
        valid_trades: list of trades that produced valid features
    """
    if not trades:
        return np.array([]), np.array([]), []

    # Build regime lookup
    regime_lookup = {}
    for r in regime_data:
        rd = r.get("regime_date")
        ac = r.get("asset_class", "ALL")
        if rd:
            date_str = str(rd)[:10]
            regime_lookup[(ac, date_str)] = r
            regime_lookup[("ALL", date_str)] = r

    # Algo encoding map
    algo_map = {name: i for i, name in enumerate(ALL_ALGOS)}

    # Build rolling algo history from context trades (prior to this batch)
    algo_history = defaultdict(list)
    if context_trades:
        for ct in context_trades:
            algo = ct.get("algorithm_name", "")
            pnl_pct = float(ct.get("realized_pct", 0) or 0)
            entry_str = str(ct.get("entry_time", ""))
            try:
                entry_dt = datetime.strptime(entry_str[:19], "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                try:
                    entry_dt = datetime.strptime(entry_str[:10], "%Y-%m-%d")
                except (ValueError, TypeError):
                    entry_dt = datetime.utcnow()
            algo_history[algo].append((pnl_pct, entry_dt))

    features_list = []
    labels = []
    valid_trades = []

    for trade in trades:
        try:
            algo = trade.get("algorithm_name", "")
            pnl_pct = float(trade.get("realized_pct", 0) or 0)
            entry_time_str = str(trade.get("entry_time", ""))

            # Parse entry time
            try:
                entry_dt = datetime.strptime(entry_time_str[:19], "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                try:
                    entry_dt = datetime.strptime(entry_time_str[:10], "%Y-%m-%d")
                except (ValueError, TypeError):
                    continue

            entry_date_str = entry_dt.strftime("%Y-%m-%d")
            asset_class = (trade.get("asset_class", "STOCK") or "STOCK").upper()

            # Label
            label = 1 if pnl_pct > 0 else 0

            feat = {}

            # ---- Original 13 features ----
            feat["algo_id"] = algo_map.get(algo, len(ALL_ALGOS))
            feat["is_momentum"] = 1 if algo in MOMENTUM_ALGOS else 0
            feat["is_mean_reversion"] = 1 if algo in MEAN_REVERSION_ALGOS else 0
            feat["asset_crypto"] = 1 if asset_class == "CRYPTO" else 0
            feat["asset_forex"] = 1 if asset_class == "FOREX" else 0
            feat["asset_stock"] = 1 if asset_class == "STOCK" else 0
            feat["is_long"] = 1 if (trade.get("direction", "LONG") or "LONG").upper() == "LONG" else 0

            tp = float(trade.get("target_tp_pct", 3) or 3)
            sl = float(trade.get("target_sl_pct", 1.5) or 1.5)
            feat["tp_sl_ratio"] = tp / sl if sl > 0 else 2.0
            feat["position_value"] = float(trade.get("position_value_usd", 500) or 500) / 1000.0
            feat["max_hold"] = float(trade.get("max_hold_hours", 12) or 12)
            feat["hour_of_day"] = entry_dt.hour
            feat["day_of_week"] = entry_dt.weekday()
            feat["is_weekend"] = 1 if entry_dt.weekday() >= 5 else 0

            # ---- Regime features (9) ----
            regime = regime_lookup.get((asset_class, entry_date_str),
                     regime_lookup.get(("ALL", entry_date_str), {}))

            feat["hmm_regime_encoded"] = encode_hmm_regime(regime.get("hmm_regime", "sideways"))
            feat["hmm_confidence"] = float(regime.get("hmm_confidence", 0.5) or 0.5)
            feat["hurst_value"] = float(regime.get("hurst_value", 0.5) or 0.5)

            hurst_regime_str = regime.get("hurst_regime", "")
            if hurst_regime_str:
                hurst_map = {"mean_reverting": 0, "random": 1, "trending": 2}
                feat["hurst_regime_encoded"] = hurst_map.get(str(hurst_regime_str).lower(), 1)
            else:
                feat["hurst_regime_encoded"] = encode_hurst_regime(feat["hurst_value"])

            ewma_vol = float(regime.get("ewma_vol", 0.02) or 0.02)
            feat["ewma_vol_annualized"] = ewma_vol * np.sqrt(252) if ewma_vol < 1 else ewma_vol
            feat["vix_level"] = float(regime.get("vix_level", 20.0) or 20.0)
            feat["vix_regime_encoded"] = encode_vix_regime(feat["vix_level"])
            feat["composite_score"] = float(regime.get("composite_score", 50.0) or 50.0)
            feat["yield_spread"] = float(regime.get("yield_spread", 0) or 0)

            # ---- Strategy context features (4) ----
            algo_hist = algo_history.get(algo, [])

            recent_30 = [pnl for pnl, _ in algo_hist[-30:]]
            if len(recent_30) >= 5:
                mean_ret = np.mean(recent_30)
                std_ret = np.std(recent_30)
                feat["algo_rolling_sharpe_30d"] = (mean_ret / std_ret) * np.sqrt(252) if std_ret > 0 else 0
            else:
                feat["algo_rolling_sharpe_30d"] = 0

            if len(recent_30) >= 3:
                feat["algo_win_rate_30d"] = sum(1 for p in recent_30 if p > 0) / len(recent_30)
            else:
                feat["algo_win_rate_30d"] = 0.5

            consec_losses = 0
            for pnl_val, _ in reversed(algo_hist):
                if pnl_val <= 0:
                    consec_losses += 1
                else:
                    break
            feat["algo_consecutive_losses"] = consec_losses
            feat["strategy_bundle_weight"] = 1.0  # Default; bundle weights not fetched in incremental mode

            # ---- Market context features (4) ----
            all_recent = [pnl for pnl, _ in algo_hist[-30:]]
            if len(all_recent) >= 10:
                current_vol = np.std(all_recent[-5:]) if len(all_recent) >= 5 else np.std(all_recent)
                hist_vol = np.std(all_recent)
                feat["atr_percentile"] = min(1.0, current_vol / max(hist_vol, 0.001))
            else:
                feat["atr_percentile"] = 0.5

            recent_5 = [pnl for pnl, _ in algo_hist[-5:]]
            feat["recent_5d_return"] = sum(recent_5) if recent_5 else 0

            if len(algo_hist) >= 10:
                cumulative = np.cumsum([pnl for pnl, _ in algo_hist])
                peak = np.max(cumulative)
                current = cumulative[-1]
                feat["distance_from_peak"] = (peak - current) / max(abs(peak), 0.001)
            else:
                feat["distance_from_peak"] = 0

            feat["cross_asset_divergence"] = compute_cross_asset_divergence(
                asset_class, feat["hmm_regime_encoded"], feat["composite_score"]
            )

            # ---- Trade quality features (3) ----
            raw_strength = float(trade.get("signal_strength", 50) or 50)
            feat["signal_strength_normalized"] = min(1.0, max(0.0, raw_strength / 100.0))
            feat["entry_hour_quality"] = compute_entry_hour_quality(entry_dt.hour)

            sig_key = (entry_date_str, algo)
            feat["same_day_signal_count"] = signal_counts.get(sig_key, 1)

            # ---- Interaction features (4) ----
            feat["regime_momentum_align"] = (
                feat["composite_score"] / 100.0 * feat["is_momentum"] +
                (1 - feat["composite_score"] / 100.0) * feat["is_mean_reversion"]
            )
            feat["strength_x_regime"] = feat["signal_strength_normalized"] * feat["composite_score"] / 100.0
            feat["vol_x_direction"] = feat["ewma_vol_annualized"] * (1 if feat["is_long"] else -1)
            feat["bundle_perf_align"] = feat["strategy_bundle_weight"] * feat["algo_win_rate_30d"]

            features_list.append(feat)
            labels.append(label)
            valid_trades.append(trade)

            # Update rolling history AFTER feature engineering (no look-ahead)
            algo_history[algo].append((pnl_pct, entry_dt))

        except Exception as e:
            logger.debug("Feature engineering error for trade %s: %s",
                        trade.get("id", "?"), e)
            continue

    if not features_list:
        return np.array([]), np.array([]), []

    df = pd.DataFrame(features_list)
    for col in FEATURE_NAMES:
        if col not in df.columns:
            df[col] = 0

    X = df[FEATURE_NAMES].fillna(0).astype(float).values
    y = np.array(labels)

    return X, y, valid_trades


# ---------------------------------------------------------------------------
# Model Management
# ---------------------------------------------------------------------------

def load_existing_model():
    """Load existing XGBoost model from disk. Returns (model, exists)."""
    if not os.path.exists(MODEL_PATH):
        logger.info("No existing model at %s", MODEL_PATH)
        return None, False

    try:
        model = XGBClassifier()
        model.load_model(MODEL_PATH)
        logger.info("Loaded existing model from %s", MODEL_PATH)
        return model, True
    except Exception as e:
        logger.error("Failed to load model: %s", e)
        return None, False


def backup_model():
    """Create backup of current model before updating."""
    if os.path.exists(MODEL_PATH):
        os.makedirs(MODEL_DIR, exist_ok=True)
        shutil.copy2(MODEL_PATH, BACKUP_PATH)
        logger.info("Model backed up to %s", BACKUP_PATH)
        return True
    return False


def rollback_model():
    """Restore model from backup."""
    if os.path.exists(BACKUP_PATH):
        shutil.copy2(BACKUP_PATH, MODEL_PATH)
        logger.info("Model rolled back from backup")
        return True
    logger.warning("No backup available for rollback")
    return False


def evaluate_model_on_batch(model, X, y):
    """
    Evaluate model performance on a batch of data.

    Returns:
        dict with precision, recall, f1, accuracy, auc, win_rate_predicted
    """
    if len(X) == 0 or len(y) == 0:
        return {}

    try:
        y_pred = model.predict(X)
        y_proba = model.predict_proba(X)[:, 1]

        metrics = {
            "precision": round(float(precision_score(y, y_pred, zero_division=0)), 4),
            "recall": round(float(recall_score(y, y_pred, zero_division=0)), 4),
            "f1": round(float(f1_score(y, y_pred, zero_division=0)), 4),
            "accuracy": round(float(accuracy_score(y, y_pred)), 4),
            "n_samples": len(y),
            "actual_win_rate": round(float(np.mean(y)), 4),
            "predicted_pass_rate": round(float(np.mean(y_pred)), 4),
        }

        try:
            metrics["auc"] = round(float(roc_auc_score(y, y_proba)), 4)
        except ValueError:
            metrics["auc"] = 0.5

        # Win rate of trades predicted to be executed
        mask_execute = y_proba >= DEFAULT_THRESHOLD
        if np.sum(mask_execute) > 0:
            metrics["filtered_win_rate"] = round(float(np.mean(y[mask_execute])), 4)
            metrics["pass_count"] = int(np.sum(mask_execute))
        else:
            metrics["filtered_win_rate"] = 0.0
            metrics["pass_count"] = 0

        return metrics
    except Exception as e:
        logger.error("Evaluation error: %s", e)
        return {}


# ---------------------------------------------------------------------------
# Incremental Training
# ---------------------------------------------------------------------------

def incremental_update(existing_model, X_new, y_new):
    """
    Incrementally update XGBoost model on new batch of trades.

    Uses the xgb_model parameter to warm-start from existing trees,
    then adds INCREMENTAL_ROUNDS new trees at low learning rate.

    Args:
        existing_model: loaded XGBClassifier (or None for cold start)
        X_new: feature matrix for new trades
        y_new: labels for new trades

    Returns:
        updated model (XGBClassifier)
    """
    n_samples = len(X_new)
    pos_count = int(np.sum(y_new))
    neg_count = n_samples - pos_count

    # Handle class imbalance
    scale_pos_weight = neg_count / max(pos_count, 1) if pos_count < neg_count else 1.0

    # Incremental params: low LR, few rounds, warm start from existing model
    params = {
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "max_depth": 4,                     # Slightly shallower for incremental
        "learning_rate": INCREMENTAL_LR,     # 0.01 for stability
        "n_estimators": INCREMENTAL_ROUNDS,  # 50 new trees
        "min_child_weight": 3,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
        "reg_alpha": 0.2,                   # Slightly more regularization
        "reg_lambda": 1.5,
        "scale_pos_weight": round(scale_pos_weight, 3),
        "random_state": 42,
        "verbosity": 0,
    }

    updated_model = XGBClassifier(**params)

    if existing_model is not None:
        # Warm-start: continue training from existing model's trees
        logger.info("  Incremental update: adding %d rounds at LR=%.3f on %d samples",
                    INCREMENTAL_ROUNDS, INCREMENTAL_LR, n_samples)
        updated_model.fit(
            X_new, y_new,
            xgb_model=existing_model.get_booster(),
            verbose=False
        )
    else:
        # Cold start: no existing model, train from scratch
        logger.info("  Cold start: training new model on %d samples", n_samples)
        params["learning_rate"] = 0.05
        params["n_estimators"] = 200
        updated_model = XGBClassifier(**params)
        updated_model.fit(X_new, y_new, verbose=False)

    return updated_model


# ---------------------------------------------------------------------------
# Threshold Recalibration
# ---------------------------------------------------------------------------

def recalibrate_thresholds(model, conn):
    """
    Recalibrate per-algorithm thresholds using last RECENT_WINDOW trades per algo.

    Fetches recent trades, runs predictions, and finds optimal threshold
    that maximizes precision while keeping recall >= RECALL_FLOOR.

    Returns:
        thresholds: dict of {algo_name: {threshold, precision, recall, ...}}
    """
    logger.info("Recalibrating per-algorithm thresholds...")

    # Fetch recent trades for calibration
    context_trades = fetch_recent_trades_for_context(conn, limit=500)
    regime_data = fetch_regime_data(conn)
    signal_counts = fetch_signal_counts(conn)

    X_all, y_all, valid_trades = engineer_features_for_trades(
        context_trades, regime_data, signal_counts
    )

    if len(X_all) == 0:
        logger.warning("  No valid trades for threshold calibration")
        return {}

    # Get predictions
    try:
        probs = model.predict_proba(X_all)[:, 1]
    except Exception as e:
        logger.error("  Prediction failed during calibration: %s", e)
        return {}

    # Map trades to algo names
    algo_names = [t.get("algorithm_name", "Unknown") for t in valid_trades[:len(X_all)]]

    # Group by algorithm
    algo_indices = defaultdict(list)
    for i, name in enumerate(algo_names):
        algo_indices[name].append(i)

    thresholds = {}

    for algo_name in sorted(algo_indices.keys()):
        indices = algo_indices[algo_name]

        # Use last RECENT_WINDOW trades per algo
        if len(indices) > RECENT_WINDOW:
            indices = indices[-RECENT_WINDOW:]

        if len(indices) < 5:
            continue

        algo_probs = probs[indices]
        algo_labels = y_all[indices]
        algo_wr = float(np.mean(algo_labels))

        # Choose base threshold
        base_threshold = AGGRESSIVE_THRESHOLD if algo_wr < 0.50 else DEFAULT_THRESHOLD

        best_threshold = base_threshold
        best_f1 = 0
        best_precision = 0
        best_recall = 0

        for t in np.arange(0.45, 0.85, 0.05):
            mask = algo_probs >= t
            n_pass = int(np.sum(mask))
            if n_pass < 3:
                continue

            t_precision = float(np.mean(algo_labels[mask])) if n_pass > 0 else 0
            t_recall = n_pass / len(indices)

            if t_precision + t_recall > 0:
                t_f1 = 2 * t_precision * t_recall / (t_precision + t_recall)
            else:
                t_f1 = 0

            if t_recall >= RECALL_FLOOR and t_f1 > best_f1:
                best_f1 = t_f1
                best_threshold = float(t)
                best_precision = t_precision
                best_recall = t_recall

        # Fallback if no good threshold found
        if best_f1 == 0:
            mask = algo_probs >= base_threshold
            best_threshold = base_threshold
            if int(np.sum(mask)) > 0:
                best_precision = float(np.mean(algo_labels[mask]))
                best_recall = int(np.sum(mask)) / len(indices)
            else:
                best_precision = algo_wr
                best_recall = 0.0

        thresholds[algo_name] = {
            "threshold": round(best_threshold, 2),
            "precision": round(best_precision, 4),
            "recall": round(best_recall, 4),
            "f1": round(best_f1, 4),
            "overall_win_rate": round(algo_wr, 4),
            "sample_count": len(indices),
        }

        status = "AGGRESSIVE" if best_threshold >= 0.70 else "STANDARD"
        logger.info(
            "  %-25s t=%.2f prec=%.1f%% rec=%.1f%% wr=%.1f%% n=%d [%s]",
            algo_name, best_threshold, best_precision * 100,
            best_recall * 100, algo_wr * 100, len(indices), status
        )

    return thresholds


# ---------------------------------------------------------------------------
# DB Status Update
# ---------------------------------------------------------------------------

def update_ml_status(conn, metrics_before, metrics_after, batch_size, updated):
    """
    Update the lm_ml_status table with meta-label model metrics.

    Uses a dedicated row for the meta-label model:
      algorithm_name='Meta-Label-V2', asset_class='ALL'
    """
    cur = conn.cursor(dictionary=True)
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    prec_after = metrics_after.get("precision", 0) if metrics_after else 0
    f1_after = metrics_after.get("f1", 0) if metrics_after else 0
    wr_after = metrics_after.get("filtered_win_rate", 0) if metrics_after else 0

    status = "active" if updated else "skipped"
    reason_parts = []
    if updated:
        reason_parts.append(f"Incremental update on {batch_size} trades")
        if metrics_before:
            reason_parts.append(f"Before: prec={metrics_before.get('precision', '?')}")
        reason_parts.append(f"After: prec={prec_after:.4f}, f1={f1_after:.4f}")
    else:
        reason_parts.append(f"Skipped update ({batch_size} trades)")

    reason = ". ".join(reason_parts)

    try:
        # Check if row exists
        cur.execute("""
            SELECT id FROM lm_ml_status
            WHERE algorithm_name = 'Meta-Label-V2' AND asset_class = 'ALL'
        """)
        row = cur.fetchone()

        if row:
            cur.execute("""
                UPDATE lm_ml_status
                SET current_win_rate = %s,
                    current_sharpe = %s,
                    status = %s,
                    status_reason = %s,
                    last_optimization = %s,
                    optimization_count = optimization_count + 1,
                    updated_at = %s
                WHERE algorithm_name = 'Meta-Label-V2' AND asset_class = 'ALL'
            """, (
                round(wr_after * 100, 2) if wr_after else None,
                round(f1_after, 4) if f1_after else None,
                status,
                reason[:500],
                now_str,
                now_str
            ))
        else:
            cur.execute("""
                INSERT INTO lm_ml_status
                    (algorithm_name, asset_class, closed_trades, ml_ready,
                     current_win_rate, current_sharpe, status, status_reason,
                     last_optimization, optimization_count, updated_at, created_at)
                VALUES ('Meta-Label-V2', 'ALL', %s, 1, %s, %s, %s, %s, %s, 1, %s, %s)
            """, (
                batch_size,
                round(wr_after * 100, 2) if wr_after else None,
                round(f1_after, 4) if f1_after else None,
                status,
                reason[:500],
                now_str,
                now_str,
                now_str
            ))

        logger.info("  lm_ml_status updated for Meta-Label-V2")
    except mysql.connector.Error as e:
        logger.warning("  Failed to update lm_ml_status: %s", e)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Online Meta-Learner: incremental XGBoost update")
    parser.add_argument("--dry-run", action="store_true",
                       help="Preview only, do not save model or thresholds")
    parser.add_argument("--force", action="store_true",
                       help="Force update even if batch is small or too soon")
    args = parser.parse_args()

    start_time = datetime.utcnow()

    print("=" * 70)
    print("  ONLINE META-LEARNER — Incremental XGBoost Update")
    print("  Fine-tunes meta-label model on new closed trades")
    print("=" * 70)
    print(f"  Started: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  Dry run: {args.dry_run}")
    print(f"  Force:   {args.force}")
    print("")

    # ---- Step 1: Load last run state ----
    logger.info("Step 1: Checking last run state...")
    last_run = load_last_run()
    last_timestamp = last_run.get("last_update_timestamp")
    last_trade_timestamp = last_run.get("last_trade_exit_time")

    logger.info("  Last update: %s", last_timestamp or "never")
    logger.info("  Last trade exit: %s", last_trade_timestamp or "unknown")

    # Check if update is allowed (max 1/day)
    allowed, reason = check_update_allowed(last_run, force=args.force)
    if not allowed:
        logger.info("  Update not allowed: %s", reason)
        print(f"\n  SKIPPED: {reason}")
        print("  Use --force to override.")
        return
    logger.info("  Update allowed: %s", reason)

    # ---- Step 2: Connect to DB and fetch new trades ----
    logger.info("")
    logger.info("Step 2: Fetching new closed trades...")
    try:
        conn = connect_db()
        logger.info("  Database connected")
    except ConnectionError as e:
        logger.error("  Database connection failed: %s", e)
        print("\n  FAILED: Cannot connect to database.")
        return

    # Fetch new trades since last run
    since = last_trade_timestamp or last_timestamp
    new_trades = fetch_new_closed_trades(conn, since)

    if len(new_trades) == 0:
        logger.info("  No new closed trades since last run")
        print("\n  NO NEW TRADES — nothing to update.")
        conn.close()
        return

    # Check minimum batch size
    if len(new_trades) < MIN_BATCH_SIZE and not args.force:
        logger.info("  Only %d new trades (need %d+). Skipping.", len(new_trades), MIN_BATCH_SIZE)
        print(f"\n  TOO FEW TRADES: {len(new_trades)} (need {MIN_BATCH_SIZE}+). Use --force to override.")
        conn.close()
        return

    logger.info("  New trades to process: %d", len(new_trades))

    # Print trade summary
    algo_counts = defaultdict(int)
    win_count = 0
    for t in new_trades:
        algo_counts[t.get("algorithm_name", "?")] += 1
        if float(t.get("realized_pct", 0) or 0) > 0:
            win_count += 1
    logger.info("  Batch win rate: %.1f%% (%d/%d)",
                win_count / len(new_trades) * 100, win_count, len(new_trades))
    for algo, count in sorted(algo_counts.items(), key=lambda x: -x[1])[:10]:
        logger.info("    %-25s %d trades", algo, count)

    # ---- Step 3: Feature engineering ----
    logger.info("")
    logger.info("Step 3: Engineering features for new batch...")

    # Fetch context (recent trades for rolling algo history)
    context_trades = fetch_recent_trades_for_context(conn, limit=200)
    regime_data = fetch_regime_data(conn)
    signal_counts = fetch_signal_counts(conn)

    X_new, y_new, valid_new = engineer_features_for_trades(
        new_trades, regime_data, signal_counts, context_trades
    )

    if len(X_new) == 0:
        logger.error("  Feature engineering produced no valid samples")
        print("\n  FAILED: Could not engineer features for new trades.")
        conn.close()
        return

    logger.info("  Feature matrix: %d samples x %d features", X_new.shape[0], X_new.shape[1])
    logger.info("  Label distribution: %d wins (%.1f%%), %d losses (%.1f%%)",
                int(np.sum(y_new)), np.mean(y_new) * 100,
                len(y_new) - int(np.sum(y_new)), (1 - np.mean(y_new)) * 100)

    # ---- Step 4: Load existing model and evaluate BEFORE update ----
    logger.info("")
    logger.info("Step 4: Loading existing model...")
    existing_model, model_exists = load_existing_model()

    metrics_before = {}
    if model_exists:
        logger.info("  Evaluating existing model on new batch (BEFORE update)...")
        metrics_before = evaluate_model_on_batch(existing_model, X_new, y_new)
        logger.info("  BEFORE: precision=%.4f recall=%.4f f1=%.4f auc=%.4f",
                    metrics_before.get("precision", 0),
                    metrics_before.get("recall", 0),
                    metrics_before.get("f1", 0),
                    metrics_before.get("auc", 0))

    # ---- Step 5: Incremental update ----
    logger.info("")
    logger.info("Step 5: Performing incremental update...")

    # Backup existing model
    if model_exists and not args.dry_run:
        backup_model()

    updated_model = incremental_update(existing_model, X_new, y_new)

    # ---- Step 6: Evaluate AFTER update ----
    logger.info("")
    logger.info("Step 6: Evaluating updated model...")
    metrics_after = evaluate_model_on_batch(updated_model, X_new, y_new)
    logger.info("  AFTER:  precision=%.4f recall=%.4f f1=%.4f auc=%.4f",
                metrics_after.get("precision", 0),
                metrics_after.get("recall", 0),
                metrics_after.get("f1", 0),
                metrics_after.get("auc", 0))

    # Compare before vs after
    if metrics_before and metrics_after:
        prec_delta = metrics_after.get("precision", 0) - metrics_before.get("precision", 0)
        f1_delta = metrics_after.get("f1", 0) - metrics_before.get("f1", 0)
        logger.info("  DELTA:  precision=%+.4f  f1=%+.4f", prec_delta, f1_delta)

    # ---- Step 7: Safety check — precision floor ----
    should_save = True
    if metrics_before and model_exists:
        # Check if model degraded significantly on recent data
        # We also evaluate on the context trades (broader sample) for a fairer check
        logger.info("")
        logger.info("Step 7: Safety validation on broader recent trades...")
        X_ctx, y_ctx, _ = engineer_features_for_trades(
            context_trades[-100:], regime_data, signal_counts
        )
        if len(X_ctx) > 0:
            ctx_metrics = evaluate_model_on_batch(updated_model, X_ctx, y_ctx)
            ctx_precision = ctx_metrics.get("precision", 0)
            logger.info("  Broader validation: precision=%.4f on %d trades",
                        ctx_precision, len(X_ctx))

            if ctx_precision < PRECISION_FLOOR:
                logger.warning(
                    "  DEGRADATION DETECTED: precision=%.4f < floor=%.4f",
                    ctx_precision, PRECISION_FLOOR
                )
                logger.warning("  Model will NOT be saved. Flagging for full retrain.")
                should_save = False
                # Update status to flag the issue
                update_ml_status(conn, metrics_before, metrics_after,
                                len(new_trades), updated=False)
                if not args.dry_run:
                    rollback_model()
        else:
            logger.info("  Not enough context trades for broader validation, proceeding")
    else:
        logger.info("")
        logger.info("Step 7: Safety check — no prior model to compare, proceeding")

    # ---- Step 8: Save model and thresholds ----
    logger.info("")
    if should_save and not args.dry_run:
        logger.info("Step 8: Saving updated model and recalibrating thresholds...")

        os.makedirs(MODEL_DIR, exist_ok=True)
        updated_model.save_model(MODEL_PATH)
        logger.info("  Model saved: %s", MODEL_PATH)

        # Recalibrate thresholds
        thresholds = recalibrate_thresholds(updated_model, conn)
        if thresholds:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(THRESHOLDS_PATH, "w") as f:
                json.dump(thresholds, f, indent=2)
            logger.info("  Thresholds saved: %s (%d algos)", THRESHOLDS_PATH, len(thresholds))

        # Update last run timestamp
        last_exit_times = [str(t.get("exit_time", "")) for t in new_trades if t.get("exit_time")]
        latest_exit = max(last_exit_times) if last_exit_times else None

        save_last_run({
            "last_update_timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "last_trade_exit_time": latest_exit,
            "batch_size": len(new_trades),
            "metrics_before": metrics_before,
            "metrics_after": metrics_after,
            "model_existed": model_exists,
            "update_number": last_run.get("update_number", 0) + 1,
        })
        logger.info("  Last run state saved")

        # Update lm_ml_status
        update_ml_status(conn, metrics_before, metrics_after, len(new_trades), updated=True)

    elif args.dry_run:
        logger.info("Step 8: DRY RUN — model and thresholds NOT saved")
        logger.info("  Would save model to: %s", MODEL_PATH)
        logger.info("  Would recalibrate thresholds in: %s", THRESHOLDS_PATH)
    else:
        logger.info("Step 8: Model NOT saved due to safety check failure")

    # ---- Final Summary ----
    elapsed = (datetime.utcnow() - start_time).total_seconds()

    print("")
    print("=" * 70)
    print("  ONLINE META-LEARNER — COMPLETE")
    print("=" * 70)
    print(f"  New trades processed:  {len(new_trades)}")
    print(f"  Valid feature samples: {len(X_new)}")
    print(f"  Batch win rate:        {np.mean(y_new):.1%}")
    if metrics_before:
        print(f"  BEFORE update:")
        print(f"    Precision: {metrics_before.get('precision', 0):.4f}")
        print(f"    Recall:    {metrics_before.get('recall', 0):.4f}")
        print(f"    F1:        {metrics_before.get('f1', 0):.4f}")
        print(f"    AUC:       {metrics_before.get('auc', 0):.4f}")
    if metrics_after:
        print(f"  AFTER update:")
        print(f"    Precision: {metrics_after.get('precision', 0):.4f}")
        print(f"    Recall:    {metrics_after.get('recall', 0):.4f}")
        print(f"    F1:        {metrics_after.get('f1', 0):.4f}")
        print(f"    AUC:       {metrics_after.get('auc', 0):.4f}")
    if metrics_before and metrics_after:
        prec_delta = metrics_after.get("precision", 0) - metrics_before.get("precision", 0)
        f1_delta = metrics_after.get("f1", 0) - metrics_before.get("f1", 0)
        print(f"  DELTA:")
        print(f"    Precision: {prec_delta:+.4f}")
        print(f"    F1:        {f1_delta:+.4f}")

    saved_str = "NO (dry-run)" if args.dry_run else ("YES" if should_save else "NO (degradation)")
    print(f"  Model saved:           {saved_str}")
    print(f"  Model path:            {MODEL_PATH}")
    print(f"  Elapsed:               {elapsed:.1f}s")
    print("=" * 70)

    if not should_save and not args.dry_run:
        print("")
        print("  WARNING: Model precision dropped below %.0f%%. " % (PRECISION_FLOOR * 100))
        print("  Run a full retrain with meta_label_v2.py instead.")
        print("  The previous model has been restored from backup.")

    print("")
    conn.close()


if __name__ == "__main__":
    main()
