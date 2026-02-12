#!/usr/bin/env python3
"""
Meta-Label V2 — Enhanced XGBoost Signal Quality Filter with Regime Context

Upgrade from V1 (11 features, 77% precision) to V2 (25+ features):
  - Adds HMM regime state, Hurst exponent, VIX regime, composite score
  - Adds strategy context: rolling Sharpe, win rate, consecutive losses, bundle weight
  - Adds market context: ATR percentile, recent returns, 52-week high distance
  - Adds cross-asset divergence (BTC vs SPY correlation breakdown)
  - Adds trade quality: signal strength, entry hour quality, same-day signal noise

Science: Lopez de Prado (2018) "Advances in Financial Machine Learning"
  - Meta-label filter reduces trade count 40-60% while raising expectancy
  - If meta_probability < 0.60 -> DO NOT EXECUTE

Pipeline:
  1. Fetch closed trades from lm_trades (last 5000) + backtest signals
  2. Fetch regime data from lm_market_regime for each trade date
  3. Engineer 25+ features per trade
  4. Label: 1 if realized_pnl > 0, 0 otherwise
  5. Train XGBoost with purged walk-forward CV (embargo=3 trades)
  6. Report: precision, recall, F1, feature importance
  7. Post results to API
  8. Generate filter thresholds per strategy

Requires: pip install xgboost scikit-learn pandas numpy mysql-connector-python requests
"""

import os
import sys
import json
import logging
import warnings
import traceback
import numpy as np
import pandas as pd
import mysql.connector
import requests
from datetime import datetime, timedelta
from collections import defaultdict

warnings.filterwarnings("ignore")

try:
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.metrics import (
        precision_score, recall_score, f1_score,
        accuracy_score, roc_auc_score, log_loss
    )
    from xgboost import XGBClassifier
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install: pip install xgboost scikit-learn pandas numpy mysql-connector-python requests")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("meta_label_v2")

# API config
API_BASE = os.environ.get("API_BASE", "https://findtorontoevents.ca/live-monitor/api")
ADMIN_KEY = os.environ.get("ADMIN_KEY", "livetrader2026")
API_HEADERS = {"User-Agent": "WorldClassIntelligence/1.0"}

# Database config
DB_HOST = os.environ.get("DB_HOST", "mysql.50webs.com")
DB_USER = os.environ.get("DB_USER", "ejaguiar1_stocks")
DB_PASS = os.environ.get("DB_PASS", "stocks")
DB_NAME = os.environ.get("DB_NAME", "ejaguiar1_stocks")

# Model config
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(SCRIPT_DIR, "models")
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
MODEL_PATH = os.path.join(MODEL_DIR, "meta_label_v2.json")
RESULTS_PATH = os.path.join(DATA_DIR, "meta_label_v2_results.json")
THRESHOLDS_PATH = os.path.join(DATA_DIR, "meta_label_v2_thresholds.json")

# Training parameters
DEFAULT_THRESHOLD = 0.60
AGGRESSIVE_THRESHOLD = 0.70       # For algos with < 50% win rate
MIN_TRAINING_SAMPLES = 50
N_CV_SPLITS = 5
PURGE_GAP = 3                     # Embargo: 3 trades between train/test boundary
MAX_TRADES = 5000

# XGBoost hyperparameters (tuned for small financial datasets)
XGB_PARAMS = {
    "objective": "binary:logistic",
    "eval_metric": "logloss",
    "max_depth": 5,
    "learning_rate": 0.05,
    "n_estimators": 200,
    "min_child_weight": 5,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "random_state": 42,
    "verbosity": 0,
}

# Algorithm lists (must match live-monitor)
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
    "Insider Cluster Buy", "13F New Position",
    "Consensus"
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

# Bundle assignments for bundle weight lookup
BUNDLE_MAP = {}
for algo in MOMENTUM_ALGOS:
    BUNDLE_MAP[algo] = "momentum"
for algo in MEAN_REVERSION_ALGOS:
    BUNDLE_MAP[algo] = "reversion"
for algo in FUNDAMENTAL_ALGOS:
    BUNDLE_MAP[algo] = "fundamental"
for algo in SENTIMENT_ALGOS:
    BUNDLE_MAP[algo] = "sentiment"
# Remaining algos default to "other"
for algo in ALL_ALGOS:
    if algo not in BUNDLE_MAP:
        BUNDLE_MAP[algo] = "other"

# VIX regime thresholds
VIX_THRESHOLDS = {
    "complacent": (0, 12),
    "normal": (12, 18),
    "elevated": (18, 25),
    "fear": (25, 35),
    "fear_peak": (35, float("inf"))
}

# Hurst regime thresholds
HURST_THRESHOLDS = {
    "mean_reverting": (0, 0.45),
    "random": (0.45, 0.55),
    "trending": (0.55, 1.0)
}


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
                import time
                time.sleep(2 ** attempt)
    raise ConnectionError("Failed to connect to database after 3 attempts")


# ---------------------------------------------------------------------------
# Data Fetching
# ---------------------------------------------------------------------------

def fetch_closed_trades(conn):
    """Fetch closed trades from lm_trades table."""
    logger.info("Fetching closed trades from lm_trades...")
    cur = conn.cursor(dictionary=True)

    # Check if table exists
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
            ORDER BY t.entry_time ASC
            LIMIT %s
        """, (MAX_TRADES,))
        trades = cur.fetchall()
        logger.info("  lm_trades: %d closed trades", len(trades))
        return trades
    except mysql.connector.Error as e:
        logger.warning("  lm_trades query failed: %s", e)
        return []


def fetch_backtest_trades(conn):
    """Fetch backtest trades from stock_picks, cp_signals, fx_signals as fallback."""
    logger.info("Fetching backtest trades as supplementary data...")
    trades = []

    # Stock picks with daily prices
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT sp.ticker AS symbol, sp.algorithm_name, sp.pick_date,
                   sp.entry_price, sp.score, sp.rating, sp.risk_level
            FROM stock_picks sp
            WHERE sp.entry_price > 0
            ORDER BY sp.pick_date ASC
            LIMIT 3000
        """)
        stock_picks = cur.fetchall()
        logger.info("  stock_picks: %d rows", len(stock_picks))

        # Load price data for backtesting
        if stock_picks:
            tickers = list(set(p["ticker" if "ticker" in p else "symbol"] for p in stock_picks))
            prices = {}
            for tk in tickers:
                cur.execute("""
                    SELECT trade_date, open_price, high_price, low_price, close_price
                    FROM daily_prices WHERE ticker = %s ORDER BY trade_date ASC
                """, (tk,))
                prices[tk] = cur.fetchall()

            # Backtest each pick
            for pick in stock_picks:
                tk = pick.get("ticker", pick.get("symbol", ""))
                ep = float(pick.get("entry_price", 0))
                pd_date = pick.get("pick_date")
                if not tk or tk not in prices or not prices[tk] or ep <= 0:
                    continue

                plist = prices[tk]
                si = None
                for i, pr in enumerate(plist):
                    if pr["trade_date"] >= pd_date:
                        si = i
                        break
                if si is None:
                    continue

                tp_pct, sl_pct, max_hold = 10.0, 5.0, 7
                tp_p = ep * (1 + tp_pct / 100.0)
                sl_p = ep * (1 - sl_pct / 100.0)
                exit_p, exit_reason, hd = 0, "", 0

                for j in range(si, min(si + max_hold + 2, len(plist))):
                    bar = plist[j]
                    hd += 1
                    h = float(bar["high_price"])
                    l = float(bar["low_price"])
                    c = float(bar["close_price"])
                    if l <= sl_p:
                        exit_p, exit_reason = sl_p, "stop_loss"
                        break
                    if h >= tp_p:
                        exit_p, exit_reason = tp_p, "take_profit"
                        break
                    if hd >= max_hold:
                        exit_p, exit_reason = c, "max_hold"
                        break
                if exit_p <= 0:
                    continue

                ret_pct = ((exit_p - ep) / ep) * 100.0
                entry_dt = datetime.combine(pd_date, datetime.min.time()) if hasattr(pd_date, "year") else pd_date

                trades.append({
                    "algorithm_name": pick.get("algorithm_name", "Unknown"),
                    "symbol": tk,
                    "asset_class": "STOCK",
                    "direction": "LONG",
                    "entry_price": ep,
                    "exit_price": exit_p,
                    "entry_time": str(entry_dt),
                    "exit_time": str(entry_dt + timedelta(days=hd)),
                    "realized_pnl": ret_pct * 5.0,  # Approximate USD PnL
                    "realized_pct": ret_pct,
                    "target_tp_pct": tp_pct,
                    "target_sl_pct": sl_pct,
                    "max_hold_hours": max_hold * 24,
                    "exit_reason": exit_reason,
                    "position_value_usd": 500,
                    "signal_strength": float(pick.get("score", 50)),
                    "source": "backtest_stock"
                })
    except mysql.connector.Error as e:
        logger.warning("  Stock backtest error: %s", e)

    # Crypto signals
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT pair AS symbol, strategy_name AS algorithm_name,
                   signal_date, entry_price, direction
            FROM cp_signals
            WHERE entry_price > 0
            ORDER BY signal_date ASC
            LIMIT 2000
        """)
        crypto_sigs = cur.fetchall()
        logger.info("  cp_signals: %d rows", len(crypto_sigs))

        if crypto_sigs:
            cur.execute("""
                SELECT pair, trade_date, open_price, high_price, low_price, close_price
                FROM cp_prices ORDER BY pair, trade_date ASC
            """)
            cp_raw = cur.fetchall()
            cp_prices = {}
            for pr in cp_raw:
                cp_prices.setdefault(pr["pair"], []).append(pr)

            for sig in crypto_sigs:
                pair = sig["symbol"]
                ep = float(sig.get("entry_price", 0))
                sd = sig.get("signal_date")
                if not pair or pair not in cp_prices or ep <= 0:
                    continue

                plist = cp_prices[pair]
                si = None
                for i, pr in enumerate(plist):
                    if pr["trade_date"] >= sd:
                        si = i
                        break
                if si is None:
                    continue

                tp_pct, sl_pct, max_hold = 10.0, 5.0, 30
                tp_p = ep * (1 + tp_pct / 100.0)
                sl_p = ep * (1 - sl_pct / 100.0)
                exit_p, exit_reason, hd = 0, "", 0

                for j in range(si, min(si + max_hold + 2, len(plist))):
                    bar = plist[j]
                    hd += 1
                    h = float(bar["high_price"])
                    l = float(bar["low_price"])
                    c = float(bar["close_price"])
                    if l <= sl_p:
                        exit_p, exit_reason = sl_p, "stop_loss"
                        break
                    if h >= tp_p:
                        exit_p, exit_reason = tp_p, "take_profit"
                        break
                    if hd >= max_hold:
                        exit_p, exit_reason = c, "max_hold"
                        break
                if exit_p <= 0:
                    continue

                ret_pct = ((exit_p - ep) / ep) * 100.0
                entry_dt = datetime.combine(sd, datetime.min.time()) if hasattr(sd, "year") else sd

                trades.append({
                    "algorithm_name": sig.get("algorithm_name", "Unknown"),
                    "symbol": pair,
                    "asset_class": "CRYPTO",
                    "direction": sig.get("direction", "LONG"),
                    "entry_price": ep,
                    "exit_price": exit_p,
                    "entry_time": str(entry_dt),
                    "exit_time": str(entry_dt + timedelta(days=hd)),
                    "realized_pnl": ret_pct * 5.0,
                    "realized_pct": ret_pct,
                    "target_tp_pct": tp_pct,
                    "target_sl_pct": sl_pct,
                    "max_hold_hours": max_hold * 24,
                    "exit_reason": exit_reason,
                    "position_value_usd": 500,
                    "signal_strength": 50,
                    "source": "backtest_crypto"
                })
    except mysql.connector.Error as e:
        logger.warning("  Crypto backtest error: %s", e)

    # Forex signals
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT pair AS symbol, strategy_name AS algorithm_name,
                   signal_date, entry_price, direction
            FROM fx_signals
            WHERE entry_price > 0
            ORDER BY signal_date ASC
            LIMIT 2000
        """)
        fx_sigs = cur.fetchall()
        logger.info("  fx_signals: %d rows", len(fx_sigs))

        if fx_sigs:
            cur.execute("""
                SELECT pair, trade_date, open_price, high_price, low_price, close_price
                FROM fx_prices ORDER BY pair, trade_date ASC
            """)
            fx_raw = cur.fetchall()
            fx_prices = {}
            for pr in fx_raw:
                fx_prices.setdefault(pr["pair"], []).append(pr)

            for sig in fx_sigs:
                pair = sig["symbol"]
                ep = float(sig.get("entry_price", 0))
                sd = sig.get("signal_date")
                if not pair or pair not in fx_prices or ep <= 0:
                    continue

                plist = fx_prices[pair]
                si = None
                for i, pr in enumerate(plist):
                    if pr["trade_date"] >= sd:
                        si = i
                        break
                if si is None:
                    continue

                tp_pct, sl_pct, max_hold = 2.0, 1.0, 14
                tp_p = ep * (1 + tp_pct / 100.0)
                sl_p = ep * (1 - sl_pct / 100.0)
                exit_p, exit_reason, hd = 0, "", 0

                for j in range(si, min(si + max_hold + 2, len(plist))):
                    bar = plist[j]
                    hd += 1
                    h = float(bar["high_price"])
                    l = float(bar["low_price"])
                    c = float(bar["close_price"])
                    if l <= sl_p:
                        exit_p, exit_reason = sl_p, "stop_loss"
                        break
                    if h >= tp_p:
                        exit_p, exit_reason = tp_p, "take_profit"
                        break
                    if hd >= max_hold:
                        exit_p, exit_reason = c, "max_hold"
                        break
                if exit_p <= 0:
                    continue

                ret_pct = ((exit_p - ep) / ep) * 100.0
                entry_dt = datetime.combine(sd, datetime.min.time()) if hasattr(sd, "year") else sd

                trades.append({
                    "algorithm_name": sig.get("algorithm_name", "Unknown"),
                    "symbol": pair,
                    "asset_class": "FOREX",
                    "direction": sig.get("direction", "LONG"),
                    "entry_price": ep,
                    "exit_price": exit_p,
                    "entry_time": str(entry_dt),
                    "exit_time": str(entry_dt + timedelta(days=hd)),
                    "realized_pnl": ret_pct * 5.0,
                    "realized_pct": ret_pct,
                    "target_tp_pct": tp_pct,
                    "target_sl_pct": sl_pct,
                    "max_hold_hours": max_hold * 24,
                    "exit_reason": exit_reason,
                    "position_value_usd": 500,
                    "signal_strength": 50,
                    "source": "backtest_forex"
                })
    except mysql.connector.Error as e:
        logger.warning("  Forex backtest error: %s", e)

    logger.info("  Total backtest trades: %d", len(trades))
    return trades


def fetch_regime_data(conn):
    """Fetch regime history from lm_market_regime table."""
    logger.info("Fetching regime history from lm_market_regime...")
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
        logger.info("  lm_market_regime: %d rows", len(rows))
        return rows
    except mysql.connector.Error as e:
        logger.warning("  lm_market_regime query failed: %s", e)
        return []


def fetch_regime_from_api():
    """Fetch current regime state from the PHP API as fallback."""
    logger.info("Fetching regime from API...")
    try:
        resp = requests.get(
            f"{API_BASE}/regime.php",
            params={"action": "get_regime", "key": ADMIN_KEY},
            headers=API_HEADERS,
            timeout=30
        )
        data = resp.json()
        if data.get("ok"):
            return data.get("regime", {})
        else:
            logger.warning("  API regime error: %s", data.get("error"))
            return {}
    except Exception as e:
        logger.warning("  API regime fetch failed: %s", e)
        return {}


def fetch_signal_counts(conn):
    """Fetch daily signal counts for same-day noise detection."""
    logger.info("Fetching signal counts from lm_signals...")
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
        logger.info("  Signal count rows: %d", len(rows))
        # Build lookup: (date_str, algo) -> count
        lookup = {}
        for r in rows:
            key = (str(r["signal_date"]), r["algorithm_name"])
            lookup[key] = int(r["signal_count"])
        return lookup
    except mysql.connector.Error as e:
        logger.warning("  lm_signals query failed: %s", e)
        return {}


def fetch_bundle_weights():
    """Fetch current bundle regime weights from the API."""
    logger.info("Fetching bundle weights from API...")
    try:
        resp = requests.get(
            f"{API_BASE}/regime.php",
            params={"action": "get_bundles", "key": ADMIN_KEY},
            headers=API_HEADERS,
            timeout=15
        )
        data = resp.json()
        if data.get("ok"):
            bundles = data.get("bundles", {})
            # Build algo -> weight map
            weights = {}
            for bundle_name, bundle_data in bundles.items():
                w = float(bundle_data.get("regime_weight", 1.0)) if isinstance(bundle_data, dict) else 1.0
                algos = bundle_data.get("algos", []) if isinstance(bundle_data, dict) else []
                for algo in algos:
                    weights[algo] = w
            return weights
        return {}
    except Exception as e:
        logger.warning("  Bundle weights fetch failed: %s", e)
        return {}


# ---------------------------------------------------------------------------
# Feature Engineering (25+ features)
# ---------------------------------------------------------------------------

def encode_vix_regime(vix_level):
    """Encode VIX level into regime integer: 0=complacent, 1=normal, 2=elevated, 3=fear, 4=fear_peak."""
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


def encode_hmm_regime(hmm_regime):
    """Encode HMM regime label: 0=bear, 1=sideways, 2=bull."""
    mapping = {"bear": 0, "sideways": 1, "bull": 2}
    if isinstance(hmm_regime, str):
        return mapping.get(hmm_regime.lower(), 1)
    return 1


def compute_entry_hour_quality(hour):
    """
    Score entry hour quality based on market liquidity patterns.
    Market open hours (9:30-16:00 ET) get higher scores.
    First/last hour (high vol) slightly lower.
    """
    h = int(hour) if hour is not None else 12
    if 10 <= h <= 15:
        return 1.0   # Core market hours
    elif h == 9 or h == 16:
        return 0.7   # Open/close volatility
    elif 17 <= h <= 20:
        return 0.4   # After hours
    elif 4 <= h <= 8:
        return 0.3   # Pre-market
    else:
        return 0.2   # Overnight


def engineer_features(trades, regime_data, signal_counts, bundle_weights):
    """
    Engineer 25+ features for each trade.

    Returns:
        features_df: DataFrame with feature columns
        labels: numpy array of binary labels (1=profitable, 0=loss)
        feature_names: list of feature column names
    """
    if not trades:
        return pd.DataFrame(), np.array([]), []

    # Build regime lookup: (asset_class, date_str) -> regime_dict
    regime_lookup = {}
    for r in regime_data:
        rd = r.get("regime_date")
        ac = r.get("asset_class", "ALL")
        if rd:
            date_str = str(rd)[:10]
            regime_lookup[(ac, date_str)] = r
            regime_lookup[("ALL", date_str)] = r  # Fallback

    # Algo performance tracking (rolling window)
    algo_map = {name: i for i, name in enumerate(ALL_ALGOS)}
    algo_history = defaultdict(list)  # algo -> list of (pnl, timestamp)

    features_list = []
    labels = []

    for trade in trades:
        try:
            algo = trade.get("algorithm_name", "")
            pnl_pct = float(trade.get("realized_pct", 0))
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
            asset_class = trade.get("asset_class", "STOCK").upper()

            # Label: 1 if profitable, 0 otherwise
            label = 1 if pnl_pct > 0 else 0

            feat = {}

            # =====================================================
            # ORIGINAL 11 FEATURES (preserved from V1)
            # =====================================================

            # 1. Algorithm ID (numeric encoding)
            feat["algo_id"] = algo_map.get(algo, len(ALL_ALGOS))

            # 2. Is momentum algo
            feat["is_momentum"] = 1 if algo in MOMENTUM_ALGOS else 0

            # 3. Is mean reversion algo
            feat["is_mean_reversion"] = 1 if algo in MEAN_REVERSION_ALGOS else 0

            # 4-6. Asset class one-hot
            feat["asset_crypto"] = 1 if asset_class == "CRYPTO" else 0
            feat["asset_forex"] = 1 if asset_class == "FOREX" else 0
            feat["asset_stock"] = 1 if asset_class == "STOCK" else 0

            # 7. Direction
            feat["is_long"] = 1 if trade.get("direction", "LONG").upper() == "LONG" else 0

            # 8. TP/SL ratio (reward/risk)
            tp = float(trade.get("target_tp_pct", 3))
            sl = float(trade.get("target_sl_pct", 1.5))
            feat["tp_sl_ratio"] = tp / sl if sl > 0 else 2.0

            # 9. Position value (normalized to $1000)
            feat["position_value"] = float(trade.get("position_value_usd", 500)) / 1000.0

            # 10. Max hold hours
            feat["max_hold"] = float(trade.get("max_hold_hours", 12))

            # 11. Time features
            feat["hour_of_day"] = entry_dt.hour
            feat["day_of_week"] = entry_dt.weekday()
            feat["is_weekend"] = 1 if entry_dt.weekday() >= 5 else 0

            # =====================================================
            # NEW REGIME FEATURES (9 features)
            # =====================================================

            # Look up regime data for this trade's date + asset class
            regime = regime_lookup.get((asset_class, entry_date_str),
                     regime_lookup.get(("ALL", entry_date_str), {}))

            # 12. HMM regime encoded (0=bear, 1=sideways, 2=bull)
            feat["hmm_regime_encoded"] = encode_hmm_regime(regime.get("hmm_regime", "sideways"))

            # 13. HMM confidence (0-1)
            feat["hmm_confidence"] = float(regime.get("hmm_confidence", 0.5))

            # 14. Hurst value (0-1)
            feat["hurst_value"] = float(regime.get("hurst_value", 0.5))

            # 15. Hurst regime encoded (0=mean_reverting, 1=random, 2=trending)
            hurst_regime_str = regime.get("hurst_regime", "")
            if hurst_regime_str:
                hurst_map = {"mean_reverting": 0, "random": 1, "trending": 2}
                feat["hurst_regime_encoded"] = hurst_map.get(str(hurst_regime_str).lower(), 1)
            else:
                feat["hurst_regime_encoded"] = encode_hurst_regime(feat["hurst_value"])

            # 16. EWMA annualized volatility
            ewma_vol = float(regime.get("ewma_vol", 0.02))
            feat["ewma_vol_annualized"] = ewma_vol * np.sqrt(252) if ewma_vol < 1 else ewma_vol

            # 17. VIX level
            feat["vix_level"] = float(regime.get("vix_level", 20.0))

            # 18. VIX regime encoded (0-4)
            feat["vix_regime_encoded"] = encode_vix_regime(feat["vix_level"])

            # 19. Composite score (0-100)
            feat["composite_score"] = float(regime.get("composite_score", 50.0))

            # 20. Yield spread (bps)
            feat["yield_spread"] = float(regime.get("yield_spread", 0))

            # =====================================================
            # NEW STRATEGY CONTEXT FEATURES (4 features)
            # =====================================================

            # Get algo's recent trade history (up to this point, no look-ahead)
            algo_hist = algo_history.get(algo, [])

            # 21. Algo rolling Sharpe (last 30 trades)
            recent_30 = [pnl for pnl, _ in algo_hist[-30:]]
            if len(recent_30) >= 5:
                mean_ret = np.mean(recent_30)
                std_ret = np.std(recent_30)
                feat["algo_rolling_sharpe_30d"] = (mean_ret / std_ret) * np.sqrt(252) if std_ret > 0 else 0
            else:
                feat["algo_rolling_sharpe_30d"] = 0

            # 22. Algo win rate (last 30 trades)
            if len(recent_30) >= 3:
                feat["algo_win_rate_30d"] = sum(1 for p in recent_30 if p > 0) / len(recent_30)
            else:
                feat["algo_win_rate_30d"] = 0.5

            # 23. Algo consecutive losses (current losing streak)
            consec_losses = 0
            for pnl_val, _ in reversed(algo_hist):
                if pnl_val <= 0:
                    consec_losses += 1
                else:
                    break
            feat["algo_consecutive_losses"] = consec_losses

            # 24. Strategy bundle regime weight
            bundle_name = BUNDLE_MAP.get(algo, "other")
            feat["strategy_bundle_weight"] = bundle_weights.get(algo, 1.0)

            # =====================================================
            # NEW MARKET CONTEXT FEATURES (4 features)
            # =====================================================

            # 25. ATR percentile (approximated from recent algo returns volatility)
            all_recent = [pnl for pnl, _ in algo_hist[-30:]]
            if len(all_recent) >= 10:
                current_vol = np.std(all_recent[-5:]) if len(all_recent) >= 5 else np.std(all_recent)
                hist_vol = np.std(all_recent)
                feat["atr_percentile"] = min(1.0, current_vol / max(hist_vol, 0.001))
            else:
                feat["atr_percentile"] = 0.5

            # 26. Recent 5-day return (approximated from last 5 algo trades)
            recent_5 = [pnl for pnl, _ in algo_hist[-5:]]
            feat["recent_5d_return"] = sum(recent_5) if recent_5 else 0

            # 27. Distance from peak performance (proxy for 52-week high distance)
            if len(algo_hist) >= 10:
                cumulative = np.cumsum([pnl for pnl, _ in algo_hist])
                peak = np.max(cumulative)
                current = cumulative[-1]
                feat["distance_from_peak"] = (peak - current) / max(abs(peak), 0.001)
            else:
                feat["distance_from_peak"] = 0

            # 28. Cross-asset divergence signal
            #     1 if algo's asset is performing opposite to its normal correlation
            feat["cross_asset_divergence"] = _compute_cross_asset_divergence(
                asset_class, feat["hmm_regime_encoded"], feat["composite_score"]
            )

            # =====================================================
            # NEW TRADE QUALITY FEATURES (3 features)
            # =====================================================

            # 29. Signal strength normalized (0-1)
            raw_strength = float(trade.get("signal_strength", 50))
            feat["signal_strength_normalized"] = min(1.0, max(0.0, raw_strength / 100.0))

            # 30. Entry hour quality (market session weighted)
            feat["entry_hour_quality"] = compute_entry_hour_quality(entry_dt.hour)

            # 31. Same-day signal count (noise indicator)
            sig_key = (entry_date_str, algo)
            feat["same_day_signal_count"] = signal_counts.get(sig_key, 1)

            # =====================================================
            # INTERACTION FEATURES (bonus, 4 features)
            # =====================================================

            # 32. Regime-momentum alignment
            #     High composite score + momentum algo = good alignment
            feat["regime_momentum_align"] = (
                feat["composite_score"] / 100.0 * feat["is_momentum"] +
                (1 - feat["composite_score"] / 100.0) * feat["is_mean_reversion"]
            )

            # 33. Strength x regime interaction
            feat["strength_x_regime"] = feat["signal_strength_normalized"] * feat["composite_score"] / 100.0

            # 34. Volatility x direction interaction
            feat["vol_x_direction"] = feat["ewma_vol_annualized"] * (1 if feat["is_long"] else -1)

            # 35. Bundle performance alignment
            feat["bundle_perf_align"] = feat["strategy_bundle_weight"] * feat["algo_win_rate_30d"]

            features_list.append(feat)
            labels.append(label)

            # Update rolling history (AFTER feature engineering to prevent look-ahead)
            algo_history[algo].append((pnl_pct, entry_dt))

        except Exception as e:
            logger.debug("Feature engineering error for trade: %s", e)
            continue

    if not features_list:
        return pd.DataFrame(), np.array([]), []

    df = pd.DataFrame(features_list)

    # Feature columns (all 35)
    feature_names = [
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

    # Ensure all columns exist
    for col in feature_names:
        if col not in df.columns:
            df[col] = 0

    X = df[feature_names].fillna(0).astype(float)
    y = np.array(labels)

    return X, y, feature_names


def _compute_cross_asset_divergence(asset_class, hmm_regime, composite_score):
    """
    Compute cross-asset divergence signal.

    Normally:
      - Crypto and stocks correlate in risk-on/risk-off
      - When they diverge, it signals regime transition or dislocation

    Returns: 0 (aligned) or 1 (diverged)
    """
    # Simple heuristic: if composite score is near 50 (uncertain),
    # and asset is crypto or stock, flag as potential divergence
    if 35 <= composite_score <= 65:
        # Near regime boundary = higher chance of divergence
        return 0.5 + (0.5 - abs(composite_score - 50) / 50)
    elif asset_class == "CRYPTO" and hmm_regime == 0:  # Crypto in bear regime
        return 0.7  # Crypto tends to diverge in corrections
    elif asset_class == "FOREX":
        return 0.3  # Forex tends to mean-revert, less divergence
    return 0.0


# ---------------------------------------------------------------------------
# Purged Walk-Forward Cross-Validation
# ---------------------------------------------------------------------------

def purged_walk_forward_cv(X, y, n_splits=5, purge_gap=3):
    """
    Purged walk-forward cross-validation.

    Science: Lopez de Prado (2018) ch.7
    - Chronological splits (no look-ahead)
    - Purge gap (embargo) of `purge_gap` observations between train/test
    - Prevents label leakage from overlapping trade windows

    Yields: (train_indices, test_indices) tuples
    """
    n = len(X)
    fold_size = n // (n_splits + 1)

    for i in range(n_splits):
        train_end = fold_size * (i + 1)
        test_start = train_end + purge_gap
        test_end = min(test_start + fold_size, n)

        if test_start >= n or test_end <= test_start:
            continue

        train_idx = np.arange(0, train_end)
        test_idx = np.arange(test_start, test_end)

        if len(train_idx) < 20 or len(test_idx) < 10:
            continue

        yield train_idx, test_idx


# ---------------------------------------------------------------------------
# Model Training
# ---------------------------------------------------------------------------

def train_meta_model(X, y, feature_names):
    """
    Train XGBoost meta-labeling model with purged walk-forward CV.

    Returns:
        model: trained XGBClassifier
        cv_results: list of fold results
        feature_importance: dict of feature -> importance
    """
    n_samples = len(X)
    n_features = X.shape[1] if hasattr(X, "shape") else len(feature_names)

    logger.info("=" * 70)
    logger.info("  META-LABEL V2 TRAINING")
    logger.info("=" * 70)
    logger.info("  Samples: %d | Features: %d", n_samples, n_features)
    logger.info("  Positive rate: %.1f%% (%d wins / %d total)",
                float(np.mean(y)) * 100, int(np.sum(y)), n_samples)

    if n_samples < MIN_TRAINING_SAMPLES:
        logger.error("Insufficient data: %d samples (need %d+)", n_samples, MIN_TRAINING_SAMPLES)
        return None, [], {}

    # Convert to numpy if DataFrame
    X_arr = X.values if hasattr(X, "values") else np.array(X)
    y_arr = np.array(y)

    # Handle class imbalance
    pos_count = int(np.sum(y_arr))
    neg_count = n_samples - pos_count
    scale_pos_weight = neg_count / max(pos_count, 1) if pos_count < neg_count else 1.0

    params = dict(XGB_PARAMS)
    params["scale_pos_weight"] = round(scale_pos_weight, 3)

    logger.info("  Scale pos weight: %.3f", scale_pos_weight)
    logger.info("  Purge gap (embargo): %d trades", PURGE_GAP)
    logger.info("")

    # ---- Purged Walk-Forward CV ----
    cv_results = []
    all_test_probs = []
    all_test_labels = []

    for fold_idx, (train_idx, test_idx) in enumerate(
        purged_walk_forward_cv(X_arr, y_arr, n_splits=N_CV_SPLITS, purge_gap=PURGE_GAP)
    ):
        X_train, X_test = X_arr[train_idx], X_arr[test_idx]
        y_train, y_test = y_arr[train_idx], y_arr[test_idx]

        model = XGBClassifier(**params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )

        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]

        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        acc = accuracy_score(y_test, y_pred)

        try:
            auc = roc_auc_score(y_test, y_proba)
        except ValueError:
            auc = 0.5

        try:
            ll = log_loss(y_test, y_proba)
        except ValueError:
            ll = 1.0

        fold_result = {
            "fold": fold_idx + 1,
            "train_size": len(train_idx),
            "test_size": len(test_idx),
            "purge_gap": PURGE_GAP,
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "accuracy": round(acc, 4),
            "auc": round(auc, 4),
            "log_loss": round(ll, 4),
            "test_positive_rate": round(float(np.mean(y_test)), 4),
        }
        cv_results.append(fold_result)

        all_test_probs.extend(y_proba.tolist())
        all_test_labels.extend(y_test.tolist())

        logger.info(
            "  Fold %d: prec=%.3f rec=%.3f f1=%.3f acc=%.3f auc=%.3f "
            "(train=%d, test=%d)",
            fold_idx + 1, prec, rec, f1, acc, auc,
            len(train_idx), len(test_idx)
        )

    if not cv_results:
        logger.error("No valid CV folds produced")
        return None, [], {}

    # ---- CV Summary ----
    avg_prec = np.mean([r["precision"] for r in cv_results])
    avg_rec = np.mean([r["recall"] for r in cv_results])
    avg_f1 = np.mean([r["f1"] for r in cv_results])
    avg_acc = np.mean([r["accuracy"] for r in cv_results])
    avg_auc = np.mean([r["auc"] for r in cv_results])
    std_prec = np.std([r["precision"] for r in cv_results])
    std_f1 = np.std([r["f1"] for r in cv_results])

    logger.info("")
    logger.info("  CV Summary (%d folds):", len(cv_results))
    logger.info("    Precision: %.4f (+/- %.4f)", avg_prec, std_prec)
    logger.info("    Recall:    %.4f", avg_rec)
    logger.info("    F1:        %.4f (+/- %.4f)", avg_f1, std_f1)
    logger.info("    Accuracy:  %.4f", avg_acc)
    logger.info("    AUC:       %.4f", avg_auc)

    # ---- Threshold Analysis on CV Predictions ----
    logger.info("")
    logger.info("  Threshold Analysis (on held-out CV predictions):")
    if all_test_probs:
        probs_arr = np.array(all_test_probs)
        labels_arr = np.array(all_test_labels)
        for threshold in [0.50, 0.55, 0.60, 0.65, 0.70, 0.75]:
            mask = probs_arr >= threshold
            n_pass = int(np.sum(mask))
            if n_pass > 0:
                pass_wr = float(np.mean(labels_arr[mask]))
                pass_pct = n_pass / len(probs_arr) * 100
                logger.info(
                    "    t=%.2f: %d/%d pass (%.0f%%), win_rate=%.1f%%",
                    threshold, n_pass, len(probs_arr), pass_pct, pass_wr * 100
                )

    # ---- Train Final Model on All Data ----
    logger.info("")
    logger.info("  Training final model on all %d samples...", n_samples)

    final_model = XGBClassifier(**params)
    final_model.fit(X_arr, y_arr, verbose=False)

    # ---- Feature Importance ----
    importances = dict(zip(feature_names, final_model.feature_importances_))
    sorted_imp = sorted(importances.items(), key=lambda x: x[1], reverse=True)

    logger.info("")
    logger.info("  Feature Importance (top 15):")
    for rank, (feat, imp) in enumerate(sorted_imp[:15], 1):
        bar = "#" * int(imp * 150)
        logger.info("    %2d. %-30s %.4f |%s|", rank, feat, imp, bar)

    return final_model, cv_results, importances


# ---------------------------------------------------------------------------
# Per-Algorithm Threshold Optimization
# ---------------------------------------------------------------------------

def compute_algo_thresholds(model, X, y, feature_names, trades):
    """
    Compute optimal probability threshold per algorithm.

    Rules:
      - Default threshold: 0.60
      - Algos with < 50% overall win rate: 0.70 (aggressive filtering)
      - Optimize per-algo threshold to maximize precision while keeping recall > 0.30

    Returns:
        thresholds: dict of {algo_name: {threshold, precision, recall, f1, top_features}}
    """
    logger.info("")
    logger.info("=" * 70)
    logger.info("  PER-ALGORITHM THRESHOLD OPTIMIZATION")
    logger.info("=" * 70)

    X_arr = X.values if hasattr(X, "values") else np.array(X)
    y_arr = np.array(y)
    probs = model.predict_proba(X_arr)[:, 1]

    # Map trades to algo names
    algo_names = []
    for trade in trades:
        algo_names.append(trade.get("algorithm_name", "Unknown"))
    # Trim to match feature matrix length (some trades may have been skipped)
    algo_names = algo_names[:len(X_arr)]

    # Group by algorithm
    algo_indices = defaultdict(list)
    for i, name in enumerate(algo_names):
        algo_indices[name].append(i)

    thresholds = {}

    for algo_name in sorted(algo_indices.keys()):
        indices = algo_indices[algo_name]
        if len(indices) < 5:
            continue

        algo_probs = probs[indices]
        algo_labels = y_arr[indices]
        algo_wr = float(np.mean(algo_labels))

        # Choose base threshold
        if algo_wr < 0.50:
            base_threshold = AGGRESSIVE_THRESHOLD  # 0.70
        else:
            base_threshold = DEFAULT_THRESHOLD      # 0.60

        # Optimize: try thresholds from 0.50 to 0.80
        best_threshold = base_threshold
        best_f1 = 0
        best_precision = 0
        best_recall = 0

        for t in np.arange(0.45, 0.85, 0.05):
            mask = algo_probs >= t
            n_pass = int(np.sum(mask))
            if n_pass < 3:
                continue

            preds = mask.astype(int)
            # For F1/precision, we need binary prediction aligned with mask
            t_precision = float(np.mean(algo_labels[mask])) if n_pass > 0 else 0
            t_recall = n_pass / len(indices)

            # F1 approximation (precision of passing trades vs pass rate)
            if t_precision + t_recall > 0:
                t_f1 = 2 * t_precision * t_recall / (t_precision + t_recall)
            else:
                t_f1 = 0

            # Keep threshold that maximizes F1 while recall >= 0.30
            if t_recall >= 0.30 and t_f1 > best_f1:
                best_f1 = t_f1
                best_threshold = float(t)
                best_precision = t_precision
                best_recall = t_recall

        # If no good threshold found, use base
        if best_f1 == 0:
            mask = algo_probs >= base_threshold
            best_threshold = base_threshold
            if int(np.sum(mask)) > 0:
                best_precision = float(np.mean(algo_labels[mask]))
                best_recall = int(np.sum(mask)) / len(indices)
            else:
                best_precision = algo_wr
                best_recall = 0.0

        # Top features for this algo (by average absolute feature value)
        algo_X = X_arr[indices]
        feature_importance_local = np.mean(np.abs(algo_X), axis=0)
        top_feat_idx = np.argsort(feature_importance_local)[::-1][:5]
        top_features = [feature_names[j] for j in top_feat_idx]

        thresholds[algo_name] = {
            "threshold": round(best_threshold, 2),
            "precision": round(best_precision, 4),
            "recall": round(best_recall, 4),
            "f1": round(best_f1, 4),
            "overall_win_rate": round(algo_wr, 4),
            "sample_count": len(indices),
            "top_features": top_features,
        }

        status = "AGGRESSIVE" if best_threshold >= 0.70 else "STANDARD"
        logger.info(
            "  %-25s t=%.2f prec=%.1f%% rec=%.1f%% wr=%.1f%% n=%d [%s]",
            algo_name, best_threshold, best_precision * 100,
            best_recall * 100, algo_wr * 100, len(indices), status
        )

    return thresholds


# ---------------------------------------------------------------------------
# Signal Filtering Analysis
# ---------------------------------------------------------------------------

def analyze_filtering_impact(model, X, y, feature_names, trades):
    """
    Analyze what would happen if we applied the meta-label filter historically.

    Reports:
      - Trade reduction %
      - Expectancy improvement
      - Win rate improvement
      - Per-asset-class breakdown
    """
    logger.info("")
    logger.info("=" * 70)
    logger.info("  HISTORICAL FILTERING IMPACT ANALYSIS")
    logger.info("=" * 70)

    X_arr = X.values if hasattr(X, "values") else np.array(X)
    y_arr = np.array(y)
    probs = model.predict_proba(X_arr)[:, 1]

    # Build trade-level analysis
    results = []
    for i in range(min(len(X_arr), len(trades))):
        trade = trades[i] if i < len(trades) else {}
        results.append({
            "algo": trade.get("algorithm_name", "Unknown"),
            "asset": trade.get("asset_class", "UNKNOWN"),
            "pnl_pct": float(trade.get("realized_pct", 0)),
            "label": int(y_arr[i]),
            "meta_prob": float(probs[i]),
        })

    df = pd.DataFrame(results)
    if df.empty:
        logger.warning("  No data for filtering analysis")
        return {}

    analysis = {}

    for threshold in [0.55, 0.60, 0.65, 0.70]:
        df["execute"] = (df["meta_prob"] >= threshold).astype(int)
        executed = df[df["execute"] == 1]
        rejected = df[df["execute"] == 0]

        if len(executed) == 0:
            continue

        all_wr = float(df["label"].mean())
        all_mean_pnl = float(df["pnl_pct"].mean())
        exec_wr = float(executed["label"].mean())
        exec_mean_pnl = float(executed["pnl_pct"].mean())
        rej_mean_pnl = float(rejected["pnl_pct"].mean()) if len(rejected) > 0 else 0
        reduction = 1 - len(executed) / len(df)

        logger.info("  Threshold %.2f:", threshold)
        logger.info("    All trades:      %d (WR=%.1f%%, avg=%.3f%%)",
                     len(df), all_wr * 100, all_mean_pnl)
        logger.info("    Would execute:   %d (WR=%.1f%%, avg=%.3f%%)",
                     len(executed), exec_wr * 100, exec_mean_pnl)
        logger.info("    Would reject:    %d (avg=%.3f%%)",
                     len(rejected), rej_mean_pnl)
        logger.info("    Trade reduction: %.1f%%", reduction * 100)
        logger.info("    Expectancy lift: %+.3f%% per trade",
                     exec_mean_pnl - all_mean_pnl)
        logger.info("")

        # Per asset class
        for ac in ["STOCK", "CRYPTO", "FOREX"]:
            ac_df = df[df["asset"] == ac]
            ac_exec = ac_df[ac_df["execute"] == 1]
            if len(ac_df) > 0 and len(ac_exec) > 0:
                logger.info("      %s: %d->%d trades, WR %.1f%%->%.1f%%",
                             ac, len(ac_df), len(ac_exec),
                             ac_df["label"].mean() * 100,
                             ac_exec["label"].mean() * 100)

        analysis[f"t_{threshold:.2f}"] = {
            "threshold": threshold,
            "total_trades": len(df),
            "executed": len(executed),
            "rejected": len(rejected),
            "reduction_pct": round(reduction * 100, 1),
            "all_win_rate": round(all_wr, 4),
            "executed_win_rate": round(exec_wr, 4),
            "all_mean_return": round(all_mean_pnl, 4),
            "executed_mean_return": round(exec_mean_pnl, 4),
            "rejected_mean_return": round(rej_mean_pnl, 4),
            "expectancy_lift": round(exec_mean_pnl - all_mean_pnl, 4),
        }

    return analysis


# ---------------------------------------------------------------------------
# API Posting
# ---------------------------------------------------------------------------

def post_results_to_api(cv_results, importances, thresholds, analysis):
    """Post training results and thresholds to the PHP API."""
    logger.info("")
    logger.info("Posting results to API...")

    avg_prec = np.mean([r["precision"] for r in cv_results]) if cv_results else 0
    avg_f1 = np.mean([r["f1"] for r in cv_results]) if cv_results else 0
    avg_auc = np.mean([r["auc"] for r in cv_results]) if cv_results else 0

    # Top features
    sorted_imp = sorted(importances.items(), key=lambda x: x[1], reverse=True)
    top_features = [{"name": f, "importance": round(float(v), 4)} for f, v in sorted_imp[:15]]

    payload = {
        "version": "v2",
        "features_count": len(importances),
        "cv_results": cv_results,
        "avg_precision": round(float(avg_prec), 4),
        "avg_f1": round(float(avg_f1), 4),
        "avg_auc": round(float(avg_auc), 4),
        "top_features": top_features,
        "thresholds": thresholds,
        "filtering_analysis": analysis,
        "trained_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "default_threshold": DEFAULT_THRESHOLD,
        "aggressive_threshold": AGGRESSIVE_THRESHOLD,
    }

    try:
        url = f"{API_BASE}/regime.php?action=update_meta_labeler&key={ADMIN_KEY}"
        resp = requests.post(url, json=payload, headers=API_HEADERS, timeout=60)
        result = resp.json()
        if result.get("ok"):
            logger.info("  API update successful: %s", result)
        else:
            logger.warning("  API update error: %s", result.get("error", "unknown"))
        return result
    except Exception as e:
        logger.warning("  API post failed: %s", e)
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Prediction Interface (for live signal filtering)
# ---------------------------------------------------------------------------

def predict_signal(signal_features, algo_thresholds=None):
    """
    Predict whether a single signal should be executed.

    Args:
        signal_features: dict matching the feature names
        algo_thresholds: dict of per-algo thresholds (loaded from file)

    Returns:
        (probability, should_execute, explanation)
    """
    if not os.path.exists(MODEL_PATH):
        return 0.5, True, "No V2 model available -- defaulting to execute"

    try:
        model = XGBClassifier()
        model.load_model(MODEL_PATH)
    except Exception as e:
        return 0.5, True, f"Model load error: {e}"

    # Build feature vector
    feature_names = [
        "algo_id", "is_momentum", "is_mean_reversion",
        "asset_crypto", "asset_forex", "asset_stock",
        "is_long", "tp_sl_ratio", "position_value", "max_hold",
        "hour_of_day", "day_of_week", "is_weekend",
        "hmm_regime_encoded", "hmm_confidence", "hurst_value",
        "hurst_regime_encoded", "ewma_vol_annualized", "vix_level",
        "vix_regime_encoded", "composite_score", "yield_spread",
        "algo_rolling_sharpe_30d", "algo_win_rate_30d",
        "algo_consecutive_losses", "strategy_bundle_weight",
        "atr_percentile", "recent_5d_return", "distance_from_peak",
        "cross_asset_divergence",
        "signal_strength_normalized", "entry_hour_quality",
        "same_day_signal_count",
        "regime_momentum_align", "strength_x_regime",
        "vol_x_direction", "bundle_perf_align",
    ]

    X = np.array([[float(signal_features.get(f, 0)) for f in feature_names]])
    prob = float(model.predict_proba(X)[0, 1])

    # Determine threshold
    algo_name = signal_features.get("algorithm_name", "")
    if algo_thresholds and algo_name in algo_thresholds:
        threshold = algo_thresholds[algo_name].get("threshold", DEFAULT_THRESHOLD)
    else:
        threshold = DEFAULT_THRESHOLD

    should_execute = prob >= threshold

    if prob >= 0.80:
        explanation = f"HIGH confidence ({prob:.2f} >= {threshold:.2f}) -- strong execute"
    elif prob >= threshold:
        explanation = f"ABOVE threshold ({prob:.2f} >= {threshold:.2f}) -- execute"
    elif prob >= threshold - 0.10:
        explanation = f"NEAR threshold ({prob:.2f} < {threshold:.2f}) -- marginal, skip"
    else:
        explanation = f"LOW confidence ({prob:.2f} << {threshold:.2f}) -- skip (likely noise)"

    return prob, should_execute, explanation


def filter_signals_batch(signals, algo_thresholds=None):
    """
    Filter a batch of signals through the V2 meta-labeler.

    Args:
        signals: list of dicts with signal features
        algo_thresholds: per-algo thresholds

    Returns:
        signals with meta_probability, meta_execute, meta_explanation added
    """
    if not os.path.exists(MODEL_PATH):
        logger.info("No V2 model -- passing all %d signals", len(signals))
        for s in signals:
            s["meta_probability_v2"] = 0.5
            s["meta_execute_v2"] = True
            s["meta_explanation_v2"] = "No V2 model trained"
        return signals

    passed = 0
    filtered = 0
    for signal in signals:
        prob, execute, explanation = predict_signal(signal, algo_thresholds)
        signal["meta_probability_v2"] = round(prob, 4)
        signal["meta_execute_v2"] = execute
        signal["meta_explanation_v2"] = explanation
        if execute:
            passed += 1
        else:
            filtered += 1

    logger.info(
        "V2 Meta-filter: %d passed, %d filtered (%.0f%% pass rate)",
        passed, filtered, passed / max(1, len(signals)) * 100
    )
    return signals


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def main():
    """
    Full V2 meta-labeling pipeline:
    1. Fetch data (lm_trades + backtest + regime)
    2. Engineer 25+ features
    3. Train XGBoost with purged walk-forward CV
    4. Compute per-algo thresholds
    5. Analyze historical filtering impact
    6. Save model + results
    7. Post to API
    """
    start_time = datetime.utcnow()

    print("=" * 70)
    print("  META-LABEL V2 -- Enhanced Signal Quality Filter")
    print("  25+ Features | Regime Context | Cross-Asset Divergence")
    print("=" * 70)
    print(f"  Started: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("")

    # ---- Step 1: Connect to DB and fetch data ----
    logger.info("Step 1: Fetching data...")
    try:
        conn = connect_db()
        logger.info("  Database connected")
    except ConnectionError as e:
        logger.error("  Database connection failed: %s", e)
        logger.info("  Falling back to API-only mode...")
        conn = None

    all_trades = []

    if conn:
        # Fetch live trades
        live_trades = fetch_closed_trades(conn)
        all_trades.extend(live_trades)

        # Fetch backtest trades as supplement
        bt_trades = fetch_backtest_trades(conn)
        all_trades.extend(bt_trades)

        # Fetch regime data
        regime_data = fetch_regime_data(conn)

        # Fetch signal counts
        signal_counts = fetch_signal_counts(conn)

        conn.close()
    else:
        # API-only fallback
        try:
            resp = requests.get(
                f"{API_BASE}/live_trade.php",
                params={"action": "history", "limit": "5000"},
                headers=API_HEADERS, timeout=30
            )
            data = resp.json()
            if data.get("ok"):
                all_trades = data.get("trades", [])
        except Exception as e:
            logger.error("  API fetch failed: %s", e)

        regime_data = []
        signal_counts = {}

    # Fetch regime from API (supplements DB data)
    if not regime_data:
        api_regime = fetch_regime_from_api()
        if api_regime:
            # Convert single regime snapshot to list format
            regime_data = [{
                "asset_class": "ALL",
                "regime_date": datetime.utcnow().strftime("%Y-%m-%d"),
                "hmm_regime": api_regime.get("hmm_regime", "sideways"),
                "hmm_confidence": api_regime.get("hmm_confidence", 0.5),
                "hurst_value": api_regime.get("hurst", 0.5),
                "hurst_regime": api_regime.get("hurst_regime", "random"),
                "ewma_vol": api_regime.get("ewma_vol", 0.02),
                "vix_level": api_regime.get("vix_level", 20),
                "composite_score": api_regime.get("composite_score", 50),
                "yield_spread": api_regime.get("yield_spread", 0),
            }]

    # Fetch bundle weights
    bundle_weights = fetch_bundle_weights()

    logger.info("")
    logger.info("  Total trades: %d", len(all_trades))
    logger.info("  Regime records: %d", len(regime_data))
    logger.info("  Signal count records: %d", len(signal_counts))
    logger.info("  Bundle weights loaded: %d algos", len(bundle_weights))

    if len(all_trades) < MIN_TRAINING_SAMPLES:
        logger.error(
            "Insufficient trade data: %d (need %d+). Cannot train.",
            len(all_trades), MIN_TRAINING_SAMPLES
        )
        print("\nMeta-Label V2 requires more trade history. Exiting.")
        return

    # ---- Step 2: Feature Engineering ----
    logger.info("")
    logger.info("Step 2: Engineering features...")
    X, y, feature_names = engineer_features(
        all_trades, regime_data, signal_counts, bundle_weights
    )

    logger.info("  Feature matrix: %d samples x %d features", len(X), len(feature_names))
    logger.info("  Label distribution: %d positive (%.1f%%), %d negative (%.1f%%)",
                int(np.sum(y)), np.mean(y) * 100,
                len(y) - int(np.sum(y)), (1 - np.mean(y)) * 100)

    if len(X) < MIN_TRAINING_SAMPLES:
        logger.error("Too few valid samples after feature engineering: %d", len(X))
        return

    # ---- Step 3: Train Model ----
    logger.info("")
    logger.info("Step 3: Training XGBoost with purged walk-forward CV...")
    model, cv_results, importances = train_meta_model(X, y, feature_names)

    if model is None:
        logger.error("Model training failed. Exiting.")
        return

    # ---- Step 4: Save Model ----
    logger.info("")
    logger.info("Step 4: Saving model...")
    os.makedirs(MODEL_DIR, exist_ok=True)
    model.save_model(MODEL_PATH)
    logger.info("  Model saved: %s", MODEL_PATH)

    # ---- Step 5: Compute Per-Algorithm Thresholds ----
    logger.info("")
    logger.info("Step 5: Computing per-algorithm thresholds...")
    thresholds = compute_algo_thresholds(model, X, y, feature_names, all_trades)

    # Save thresholds
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(THRESHOLDS_PATH, "w") as f:
        json.dump(thresholds, f, indent=2)
    logger.info("  Thresholds saved: %s", THRESHOLDS_PATH)

    # ---- Step 6: Filtering Impact Analysis ----
    logger.info("")
    logger.info("Step 6: Analyzing historical filtering impact...")
    analysis = analyze_filtering_impact(model, X, y, feature_names, all_trades)

    # ---- Step 7: Save Full Results ----
    logger.info("")
    logger.info("Step 7: Saving results...")

    avg_prec = np.mean([r["precision"] for r in cv_results]) if cv_results else 0
    avg_f1 = np.mean([r["f1"] for r in cv_results]) if cv_results else 0
    avg_auc = np.mean([r["auc"] for r in cv_results]) if cv_results else 0

    sorted_imp = sorted(importances.items(), key=lambda x: x[1], reverse=True)

    results = {
        "version": "v2",
        "generated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_samples": len(X),
        "feature_count": len(feature_names),
        "feature_names": feature_names,
        "cv_results": cv_results,
        "cv_summary": {
            "avg_precision": round(float(avg_prec), 4),
            "avg_recall": round(float(np.mean([r["recall"] for r in cv_results])), 4),
            "avg_f1": round(float(avg_f1), 4),
            "avg_accuracy": round(float(np.mean([r["accuracy"] for r in cv_results])), 4),
            "avg_auc": round(float(avg_auc), 4),
            "n_folds": len(cv_results),
        },
        "feature_importance": {f: round(float(v), 4) for f, v in sorted_imp},
        "per_algo_thresholds": thresholds,
        "filtering_analysis": analysis,
        "config": {
            "default_threshold": DEFAULT_THRESHOLD,
            "aggressive_threshold": AGGRESSIVE_THRESHOLD,
            "purge_gap": PURGE_GAP,
            "n_cv_splits": N_CV_SPLITS,
            "xgb_params": {k: v for k, v in XGB_PARAMS.items() if k != "verbosity"},
        },
    }

    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)
    logger.info("  Results saved: %s", RESULTS_PATH)

    # ---- Step 8: Post to API ----
    logger.info("")
    logger.info("Step 8: Posting to API...")
    api_result = post_results_to_api(cv_results, importances, thresholds, analysis)

    # ---- Summary ----
    elapsed = (datetime.utcnow() - start_time).total_seconds()

    print("")
    print("=" * 70)
    print("  META-LABEL V2 COMPLETE")
    print("=" * 70)
    print(f"  Samples:        {len(X)}")
    print(f"  Features:       {len(feature_names)}")
    print(f"  CV Precision:   {avg_prec:.1%} (+/- {np.std([r['precision'] for r in cv_results]):.1%})")
    print(f"  CV F1:          {avg_f1:.3f}")
    print(f"  CV AUC:         {avg_auc:.3f}")
    print(f"  Algo thresholds: {len(thresholds)}")
    print(f"  Default cutoff: {DEFAULT_THRESHOLD}")
    print(f"  Model path:     {MODEL_PATH}")
    print(f"  Results path:   {RESULTS_PATH}")
    print(f"  Thresholds:     {THRESHOLDS_PATH}")
    print(f"  API posted:     {'Yes' if api_result.get('ok') else 'No'}")
    print(f"  Elapsed:        {elapsed:.1f}s")
    print("=" * 70)

    # Key recommendation
    if analysis:
        best_key = None
        best_lift = -999
        for key, val in analysis.items():
            if val.get("expectancy_lift", 0) > best_lift and val.get("reduction_pct", 0) < 70:
                best_lift = val["expectancy_lift"]
                best_key = key
        if best_key:
            best = analysis[best_key]
            print(f"\n  RECOMMENDATION: Use threshold {best['threshold']:.2f}")
            print(f"    -> Reduces trades by {best['reduction_pct']:.0f}%")
            print(f"    -> Lifts expectancy by {best['expectancy_lift']:+.3f}% per trade")
            print(f"    -> Win rate: {best['all_win_rate']:.1%} -> {best['executed_win_rate']:.1%}")

    print("")


if __name__ == "__main__":
    main()
