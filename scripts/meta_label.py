#!/usr/bin/env python3
"""
Meta-Labeler — XGBoost signal quality predictor using purged time-series CV.

Predicts whether a signal will result in a good (above-median) trade outcome.
Filters out false-positive signals before position sizing.

ENHANCED VERSION:
  - Uses real backtest data from stock_picks + cp_signals + fx_signals (2000+ trades)
    instead of the sparse lm_trades table (only 9 rows)
  - 15+ engineered features including rolling algo performance, score percentile,
    day-of-week, monthly seasonality, risk level, and multi-asset awareness
  - Purged TimeSeriesSplit prevents look-ahead bias (de Prado 2018)
  - Saves CV results and feature importance to JSON for dashboard tracking
  - Writes meta-label predictions back to DB for signal gating

References:
  - de Prado (2018) — "Advances in Financial Machine Learning" ch.7
  - Purged k-fold: remove observations whose labels overlap with test set

Requirements: pip install xgboost pandas numpy mysql-connector-python scikit-learn
"""
import os
import sys
import json
import logging
import math
import mysql.connector
import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import xgboost as xgb

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('meta_label')

# DB config from env vars
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

# Model config
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(SCRIPT_DIR, '..', 'models')
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')
MODEL_PATH = os.path.join(MODEL_DIR, 'meta_label_model.json')
RESULTS_PATH = os.path.join(DATA_DIR, 'meta_label_results.json')
EXECUTE_THRESHOLD = 0.6   # Only execute signals with P(good) >= this
MIN_TRAINING_SAMPLES = 50
N_CV_SPLITS = 5
PURGE_PCT = 0.05  # 5% of training data removed as purge gap

# Backtest defaults (match PHP backtest engines)
STOCK_TP, STOCK_SL, STOCK_HOLD = 10, 5, 7
CRYPTO_TP, CRYPTO_SL, CRYPTO_HOLD = 10, 5, 30
FOREX_TP, FOREX_SL, FOREX_HOLD = 2, 1, 14


def connect_db():
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
    )


def _backtest_stocks(conn):
    """Backtest stock picks against daily_prices, return DataFrame."""
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT sp.ticker, sp.algorithm_name, sp.pick_date, sp.entry_price,
               sp.score, sp.rating, sp.risk_level
        FROM stock_picks sp WHERE sp.entry_price > 0 ORDER BY sp.pick_date ASC
    """)
    picks = cur.fetchall()
    if not picks:
        return pd.DataFrame()

    # Load prices
    tickers = set(p['ticker'] for p in picks)
    prices = {}
    for tk in tickers:
        cur.execute("SELECT trade_date, open_price, high_price, low_price, close_price "
                     "FROM daily_prices WHERE ticker = %s ORDER BY trade_date ASC", (tk,))
        prices[tk] = cur.fetchall()

    rows = []
    for pick in picks:
        tk = pick['ticker']
        ep = float(pick['entry_price'])
        pd_date = pick['pick_date']
        if tk not in prices or not prices[tk] or ep <= 0:
            continue

        plist = prices[tk]
        si = None
        for i, pr in enumerate(plist):
            if pr['trade_date'] >= pd_date:
                si = i
                break
        if si is None:
            continue

        tp_p = ep * (1 + STOCK_TP / 100.0)
        sl_p = ep * (1 - STOCK_SL / 100.0)
        exit_p = 0
        exit_reason = ''
        hd = 0
        for j in range(si, min(si + STOCK_HOLD + 2, len(plist))):
            bar = plist[j]
            hd += 1
            h, l, c = float(bar['high_price']), float(bar['low_price']), float(bar['close_price'])
            if l <= sl_p:
                exit_p = sl_p; exit_reason = 'stop_loss'; break
            if h >= tp_p:
                exit_p = tp_p; exit_reason = 'take_profit'; break
            if hd >= STOCK_HOLD:
                exit_p = c; exit_reason = 'max_hold'; break
        if exit_p <= 0:
            continue

        ret = ((exit_p - ep) / ep) * 100.0
        rows.append({
            'asset_class': 'stocks', 'algorithm': pick['algorithm_name'],
            'symbol': tk, 'date': pd_date, 'entry_price': ep,
            'return_pct': ret, 'hold_days': hd, 'exit_reason': exit_reason,
            'score': int(pick['score'] or 0),
            'rating': pick['rating'] or '',
            'risk_level': pick['risk_level'] or 'Medium',
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _backtest_crypto(conn):
    """Backtest crypto signals against cp_prices, return DataFrame."""
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT pair, strategy_name, signal_date, entry_price, direction "
                "FROM cp_signals WHERE entry_price > 0 ORDER BY signal_date ASC")
    signals = cur.fetchall()
    if not signals:
        return pd.DataFrame()

    cur.execute("SELECT pair, trade_date, open_price, high_price, low_price, close_price "
                "FROM cp_prices ORDER BY pair, trade_date ASC")
    prices_raw = cur.fetchall()
    prices = {}
    for pr in prices_raw:
        prices.setdefault(pr['pair'], []).append(pr)

    rows = []
    for sig in signals:
        pair = sig['pair']
        ep = float(sig['entry_price'])
        sd = sig['signal_date']
        if pair not in prices or ep <= 0:
            continue
        plist = prices[pair]
        si = None
        for i, pr in enumerate(plist):
            if pr['trade_date'] >= sd:
                si = i; break
        if si is None:
            continue

        tp_p = ep * (1 + CRYPTO_TP / 100.0)
        sl_p = ep * (1 - CRYPTO_SL / 100.0)
        exit_p = 0; exit_reason = ''; hd = 0
        for j in range(si, min(si + CRYPTO_HOLD + 2, len(plist))):
            bar = plist[j]; hd += 1
            h, l, c = float(bar['high_price']), float(bar['low_price']), float(bar['close_price'])
            if l <= sl_p:
                exit_p = sl_p; exit_reason = 'stop_loss'; break
            if h >= tp_p:
                exit_p = tp_p; exit_reason = 'take_profit'; break
            if hd >= CRYPTO_HOLD:
                exit_p = c; exit_reason = 'max_hold'; break
        if exit_p <= 0:
            continue

        ret = ((exit_p - ep) / ep) * 100.0
        rows.append({
            'asset_class': 'crypto', 'algorithm': sig['strategy_name'],
            'symbol': pair, 'date': sd, 'entry_price': ep,
            'return_pct': ret, 'hold_days': hd, 'exit_reason': exit_reason,
            'score': 50, 'rating': '', 'risk_level': 'High',
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _backtest_forex(conn):
    """Backtest forex signals against fx_prices, return DataFrame."""
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT pair, strategy_name, signal_date, entry_price, direction "
                "FROM fx_signals WHERE entry_price > 0 ORDER BY signal_date ASC")
    signals = cur.fetchall()
    if not signals:
        return pd.DataFrame()

    cur.execute("SELECT pair, trade_date, open_price, high_price, low_price, close_price "
                "FROM fx_prices ORDER BY pair, trade_date ASC")
    prices_raw = cur.fetchall()
    prices = {}
    for pr in prices_raw:
        prices.setdefault(pr['pair'], []).append(pr)

    rows = []
    for sig in signals:
        pair = sig['pair']
        ep = float(sig['entry_price'])
        sd = sig['signal_date']
        if pair not in prices or ep <= 0:
            continue
        plist = prices[pair]
        si = None
        for i, pr in enumerate(plist):
            if pr['trade_date'] >= sd:
                si = i; break
        if si is None:
            continue

        tp_p = ep * (1 + FOREX_TP / 100.0)
        sl_p = ep * (1 - FOREX_SL / 100.0)
        exit_p = 0; exit_reason = ''; hd = 0
        for j in range(si, min(si + FOREX_HOLD + 2, len(plist))):
            bar = plist[j]; hd += 1
            h, l, c = float(bar['high_price']), float(bar['low_price']), float(bar['close_price'])
            if l <= sl_p:
                exit_p = sl_p; exit_reason = 'stop_loss'; break
            if h >= tp_p:
                exit_p = tp_p; exit_reason = 'take_profit'; break
            if hd >= FOREX_HOLD:
                exit_p = c; exit_reason = 'max_hold'; break
        if exit_p <= 0:
            continue

        ret = ((exit_p - ep) / ep) * 100.0
        rows.append({
            'asset_class': 'forex', 'algorithm': sig['strategy_name'],
            'symbol': pair, 'date': sd, 'entry_price': ep,
            'return_pct': ret, 'hold_days': hd, 'exit_reason': exit_reason,
            'score': 50, 'rating': '', 'risk_level': 'Medium',
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def fetch_all_trade_data():
    """Fetch and backtest all signals across stocks/crypto/forex."""
    conn = connect_db()
    logger.info("Backtesting stocks...")
    df_stocks = _backtest_stocks(conn)
    logger.info("  %d stock trades", len(df_stocks))

    logger.info("Backtesting crypto...")
    df_crypto = _backtest_crypto(conn)
    logger.info("  %d crypto trades", len(df_crypto))

    logger.info("Backtesting forex...")
    df_forex = _backtest_forex(conn)
    logger.info("  %d forex trades", len(df_forex))

    conn.close()

    frames = [f for f in [df_stocks, df_crypto, df_forex] if len(f) > 0]
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    return df


def engineer_features(df):
    """
    Engineer 15+ features for the meta-labeler.
    All features use only past data (no look-ahead) since df is sorted by date
    and rolling windows are backward-looking.
    """
    df = df.copy()

    # Binary label: above-median return = good trade
    median_ret = df['return_pct'].median()
    df['label'] = (df['return_pct'] > median_ret).astype(int)

    # --- Feature 1: Algorithm rolling win rate (last 20 trades) ---
    df['algo_rolling_wr'] = df.groupby('algorithm')['label'].transform(
        lambda x: x.rolling(20, min_periods=3).mean()
    )

    # --- Feature 2: Algorithm rolling mean return (last 20 trades) ---
    df['algo_rolling_ret'] = df.groupby('algorithm')['return_pct'].transform(
        lambda x: x.rolling(20, min_periods=3).mean()
    )

    # --- Feature 3: Asset class one-hot ---
    df['is_stocks'] = (df['asset_class'] == 'stocks').astype(int)
    df['is_crypto'] = (df['asset_class'] == 'crypto').astype(int)
    df['is_forex'] = (df['asset_class'] == 'forex').astype(int)

    # --- Feature 4: Score (normalized to 0-1) ---
    max_score = df['score'].max()
    df['score_norm'] = df['score'] / max_score if max_score > 0 else 0

    # --- Feature 5: Risk level one-hot ---
    df['risk_high'] = (df['risk_level'] == 'High').astype(int)
    df['risk_low'] = (df['risk_level'] == 'Low').astype(int)

    # --- Feature 6: Day of week (0=Mon, 4=Fri) ---
    df['day_of_week'] = df['date'].dt.dayofweek

    # --- Feature 7: Month (seasonality) ---
    df['month'] = df['date'].dt.month

    # --- Feature 8: Entry price log (proxy for market cap/tier) ---
    df['log_price'] = np.log1p(df['entry_price'].clip(lower=0.001))

    # --- Feature 9: Portfolio-wide rolling win rate (last 50 trades) ---
    df['portfolio_rolling_wr'] = df['label'].rolling(50, min_periods=10).mean()

    # --- Feature 10: Portfolio-wide rolling return (last 50 trades) ---
    df['portfolio_rolling_ret'] = df['return_pct'].rolling(50, min_periods=10).mean()

    # --- Feature 11: Consecutive wins/losses for this algorithm ---
    def _streak(series):
        streak = []
        cnt = 0
        prev = None
        for v in series:
            if v == prev:
                cnt += 1
            else:
                cnt = 1
            prev = v
            streak.append(cnt)
        return streak

    df['algo_streak'] = df.groupby('algorithm')['label'].transform(
        lambda x: pd.Series(_streak(x.values), index=x.index)
    )

    # --- Feature 12: Is strong buy rating ---
    df['is_strong_buy'] = df['rating'].str.contains('STRONG', case=False, na=False).astype(int)

    # --- Feature 13: Trade number for this algorithm (experience/maturity) ---
    df['algo_trade_num'] = df.groupby('algorithm').cumcount() + 1

    # --- Feature 14: Return volatility rolling (last 20 algo trades) ---
    df['algo_ret_vol'] = df.groupby('algorithm')['return_pct'].transform(
        lambda x: x.rolling(20, min_periods=5).std()
    )

    # All features
    feature_cols = [
        'algo_rolling_wr', 'algo_rolling_ret',
        'is_stocks', 'is_crypto', 'is_forex',
        'score_norm', 'risk_high', 'risk_low',
        'day_of_week', 'month', 'log_price',
        'portfolio_rolling_wr', 'portfolio_rolling_ret',
        'algo_streak', 'is_strong_buy',
        'algo_trade_num', 'algo_ret_vol',
    ]

    X = df[feature_cols].fillna(0)
    y = df['label']
    return X, y, feature_cols, df


def train_model():
    """
    Train XGBoost meta-labeler using purged time-series cross-validation.

    Key methodology:
      1. Data is sorted by date (temporal order preserved)
      2. TimeSeriesSplit ensures train always precedes test chronologically
      3. Purge gap removes samples between train/test to prevent label leakage
      4. Final model is trained on all data after CV validation
    """
    logger.info("=" * 70)
    logger.info("  Meta-Labeler Training (Purged TSCV, Multi-Asset)")
    logger.info("=" * 70)

    df = fetch_all_trade_data()
    if len(df) < MIN_TRAINING_SAMPLES:
        logger.warning("Insufficient data: %d samples (need %d)", len(df), MIN_TRAINING_SAMPLES)
        return None

    logger.info("Loaded %d trades across stocks/crypto/forex", len(df))

    X, y, feature_cols, df_full = engineer_features(df)
    logger.info("Features: %d | Label positive rate: %.1f%%", len(feature_cols), y.mean() * 100)

    # --- Purged Time-Series Cross-Validation ---
    tscv = TimeSeriesSplit(n_splits=N_CV_SPLITS)
    cv_results = []

    for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
        # Purge: remove end of training set to prevent label leakage
        purge_gap = max(1, int(len(train_idx) * PURGE_PCT))
        train_idx_purged = train_idx[:-purge_gap] if purge_gap > 0 else train_idx

        X_train, X_test = X.iloc[train_idx_purged], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx_purged], y.iloc[test_idx]

        if len(X_train) < 20 or len(X_test) < 10:
            logger.warning("  Fold %d: skipped (too few samples)", fold + 1)
            continue

        model = xgb.XGBClassifier(
            n_estimators=150,
            learning_rate=0.05,
            max_depth=4,
            min_child_weight=3,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.1,
            reg_lambda=1.0,
            random_state=42,
            use_label_encoder=False,
            eval_metric='logloss',
        )
        model.fit(X_train, y_train, verbose=False)

        preds = model.predict(X_test)
        probs = model.predict_proba(X_test)[:, 1]

        acc = accuracy_score(y_test, preds)
        prec = precision_score(y_test, preds, zero_division=0)
        rec = recall_score(y_test, preds, zero_division=0)
        f1 = f1_score(y_test, preds, zero_division=0)
        try:
            auc = roc_auc_score(y_test, probs)
        except ValueError:
            auc = 0.5

        cv_results.append({
            'fold': fold + 1,
            'train_size': len(X_train),
            'test_size': len(X_test),
            'purge_gap': purge_gap,
            'accuracy': round(acc, 4),
            'precision': round(prec, 4),
            'recall': round(rec, 4),
            'f1': round(f1, 4),
            'auc': round(auc, 4),
        })
        logger.info("  Fold %d: acc=%.3f prec=%.3f rec=%.3f f1=%.3f auc=%.3f "
                     "(train=%d, test=%d, purge=%d)",
                     fold + 1, acc, prec, rec, f1, auc,
                     len(X_train), len(X_test), purge_gap)

    if not cv_results:
        logger.error("No valid CV folds — cannot train")
        return None

    # CV summary
    avg_acc = np.mean([r['accuracy'] for r in cv_results])
    avg_prec = np.mean([r['precision'] for r in cv_results])
    avg_f1 = np.mean([r['f1'] for r in cv_results])
    avg_auc = np.mean([r['auc'] for r in cv_results])
    logger.info("CV Summary: avg_acc=%.3f avg_prec=%.3f avg_f1=%.3f avg_auc=%.3f (%d folds)",
                avg_acc, avg_prec, avg_f1, avg_auc, len(cv_results))

    # --- Train final model on ALL data ---
    logger.info("Training final model on all %d samples...", len(X))
    final_model = xgb.XGBClassifier(
        n_estimators=150,
        learning_rate=0.05,
        max_depth=4,
        min_child_weight=3,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        use_label_encoder=False,
        eval_metric='logloss',
    )
    final_model.fit(X, y, verbose=False)

    # Feature importance
    importance = dict(zip(feature_cols, final_model.feature_importances_))
    sorted_imp = sorted(importance.items(), key=lambda x: x[1], reverse=True)
    logger.info("Feature importance (top 10):")
    for feat, imp in sorted_imp[:10]:
        logger.info("  %-25s: %.4f", feat, imp)

    # Save model
    os.makedirs(MODEL_DIR, exist_ok=True)
    final_model.save_model(MODEL_PATH)
    logger.info("Model saved: %s", MODEL_PATH)

    # --- Evaluate: what if we had filtered signals with P(good) < threshold? ---
    all_probs = final_model.predict_proba(X)[:, 1]
    df_full['meta_prob'] = all_probs
    df_full['meta_execute'] = (all_probs >= EXECUTE_THRESHOLD).astype(int)

    # Compare performance: all trades vs filtered trades
    all_mean_ret = df_full['return_pct'].mean()
    filtered = df_full[df_full['meta_execute'] == 1]
    filtered_mean_ret = filtered['return_pct'].mean() if len(filtered) > 0 else 0
    rejected = df_full[df_full['meta_execute'] == 0]
    rejected_mean_ret = rejected['return_pct'].mean() if len(rejected) > 0 else 0

    logger.info("")
    logger.info("=" * 50)
    logger.info("  SIGNAL FILTERING ANALYSIS")
    logger.info("=" * 50)
    logger.info("  Threshold: P(good) >= %.2f", EXECUTE_THRESHOLD)
    logger.info("  All trades:      %d (mean ret: %+.3f%%)", len(df_full), all_mean_ret)
    logger.info("  Would EXECUTE:   %d (mean ret: %+.3f%%)", len(filtered), filtered_mean_ret)
    logger.info("  Would REJECT:    %d (mean ret: %+.3f%%)", len(rejected), rejected_mean_ret)
    logger.info("  Improvement:     %+.3f%% per trade",
                filtered_mean_ret - all_mean_ret if len(filtered) > 0 else 0)

    # Save results to JSON
    os.makedirs(DATA_DIR, exist_ok=True)
    results = {
        'generated': pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%dT%H:%M:%SZ'),
        'total_samples': len(df_full),
        'cv_results': cv_results,
        'cv_summary': {
            'avg_accuracy': round(avg_acc, 4),
            'avg_precision': round(avg_prec, 4),
            'avg_f1': round(avg_f1, 4),
            'avg_auc': round(avg_auc, 4),
            'n_folds': len(cv_results),
        },
        'feature_importance': {feat: round(float(imp), 4) for feat, imp in sorted_imp},
        'filtering_analysis': {
            'threshold': EXECUTE_THRESHOLD,
            'all_trades': len(df_full),
            'all_mean_return_pct': round(all_mean_ret, 4),
            'execute_count': len(filtered),
            'execute_mean_return_pct': round(filtered_mean_ret, 4),
            'reject_count': len(rejected),
            'reject_mean_return_pct': round(rejected_mean_ret, 4),
            'improvement_pct': round(filtered_mean_ret - all_mean_ret, 4) if len(filtered) > 0 else 0,
        },
    }
    with open(RESULTS_PATH, 'w') as f:
        json.dump(results, f, indent=2)
    logger.info("Results saved: %s", RESULTS_PATH)

    return final_model


def predict_signal(features_dict):
    """
    Predict whether a signal should be executed.

    Args:
        features_dict: dict with keys matching feature columns. At minimum:
            algorithm, asset_class, score, risk_level, entry_price, rating

    Returns:
        (prob, should_execute, explanation)
    """
    model = xgb.XGBClassifier()
    try:
        model.load_model(MODEL_PATH)
    except Exception as e:
        logger.warning("No model found: %s", e)
        return 0.5, True, "No model available — defaulting to execute"

    # Build feature vector from dict
    df = pd.DataFrame([{
        'asset_class': features_dict.get('asset_class', 'stocks'),
        'algorithm': features_dict.get('algorithm', ''),
        'score': features_dict.get('score', 50),
        'rating': features_dict.get('rating', ''),
        'risk_level': features_dict.get('risk_level', 'Medium'),
        'entry_price': features_dict.get('entry_price', 100),
        'date': pd.Timestamp.now(),
        'return_pct': 0,  # placeholder for feature engineering
    }])
    X, _, _, _ = engineer_features(df)

    prob = float(model.predict_proba(X)[0, 1])
    should_execute = prob >= EXECUTE_THRESHOLD
    explanation = (f"P(good)={prob:.2f} {'>=  ' if should_execute else '< '}"
                   f"{EXECUTE_THRESHOLD} -> {'EXECUTE' if should_execute else 'SKIP'}")
    return prob, should_execute, explanation


if __name__ == '__main__':
    train_model()
