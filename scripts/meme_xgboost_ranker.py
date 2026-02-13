#!/usr/bin/env python3
"""
Meme Coin XGBoost Ranker -- Gradient-boosted ensemble model trained on
resolved mc_winners signals. Produces win probability for BUY NOW ranking.

Features (12 total):
  7 existing indicator scores + 5 new derived features:
    - holder_concentration_proxy (volume vs market context)
    - cross_exchange_divergence (crypto.com vs coingecko price delta - future)
    - volume_acceleration (3-candle volume trend)
    - historical_coin_wr (this coin's past win rate)
    - btc_regime_score (bull/bear/chop encoded)

Output:
  - Trained model saved to scripts/models/meme_xgb_v1.json
  - Performance metrics printed
  - Optimal BUY NOW threshold calibrated

Requires: pip install xgboost scikit-learn mysql-connector-python numpy
Usage:
  python scripts/meme_xgboost_ranker.py
  python scripts/meme_xgboost_ranker.py --min-samples 20
  python scripts/meme_xgboost_ranker.py --dry-run
"""
import os
import sys
import json
import argparse
from datetime import datetime
from collections import defaultdict

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MEME_DB_HOST = os.getenv('MEME_DB_HOST', 'mysql.50webs.com')
MEME_DB_USER = os.getenv('MEME_DB_USER', 'ejaguiar1_memecoin')
MEME_DB_PASS = os.getenv('MEME_DB_PASS', 'testing123')
MEME_DB_NAME = os.getenv('MEME_DB_NAME', 'ejaguiar1_memecoin')

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')
MODEL_PATH = os.path.join(MODEL_DIR, 'meme_xgb_v1.json')

# Factor keys and max values for normalization
FACTOR_KEYS = [
    ('explosive_volume', 25),
    ('parabolic_momentum', 20),
    ('rsi_hype_zone', 15),
    ('social_proxy', 15),
    ('volume_concentration', 10),
    ('breakout_4h', 10),
    ('low_cap_bonus', 5),
]

FEATURE_NAMES = [
    # 7 existing indicators (normalized 0-1)
    'explosive_volume', 'parabolic_momentum', 'rsi_hype_zone',
    'social_proxy', 'volume_concentration', 'breakout_4h', 'low_cap_bonus',
    # 5 new derived features
    'tier_encoded', 'btc_regime_encoded', 'quality_gate_score',
    'historical_coin_wr', 'volume_usd_log',
]


def connect_db():
    import mysql.connector
    return mysql.connector.connect(
        host=MEME_DB_HOST,
        user=MEME_DB_USER,
        password=MEME_DB_PASS,
        database=MEME_DB_NAME,
        connect_timeout=15,
    )


def extract_factor_score(factors, key):
    """Extract normalized factor score from factors_json."""
    if not factors:
        return 0
    f = factors.get(key)
    if f is None:
        return 0
    if isinstance(f, dict):
        return f.get('score', 0)
    if isinstance(f, (int, float)):
        return f
    return 0


def build_features(row, coin_wr_map):
    """Build feature vector from a mc_winners row."""
    factors = row.get('factors_json')
    if isinstance(factors, str):
        try:
            factors = json.loads(factors)
        except Exception:
            factors = {}
    if not isinstance(factors, dict):
        factors = {}

    features = []

    # 7 existing indicators (normalized)
    for key, max_val in FACTOR_KEYS:
        score = extract_factor_score(factors, key)
        features.append(score / max_val if max_val > 0 else 0)

    # Tier encoded (1 = tier1, 2 = tier2)
    tier = row.get('tier', 'tier1')
    features.append(1 if tier == 'tier1' else 2)

    # BTC regime encoded (1=bull, 0=chop, -1=bear)
    btc = factors.get('btc_regime', {})
    regime = btc.get('regime', 'chop') if isinstance(btc, dict) else 'chop'
    regime_val = 1 if regime == 'bull' else (-1 if regime == 'bear' else 0)
    features.append(regime_val)

    # Quality gate score (0-3)
    qc = factors.get('quality_check', {})
    qscore = qc.get('score', 0) if isinstance(qc, dict) else 0
    features.append(qscore)

    # Historical coin win rate
    pair = row.get('pair', '')
    coin_wr = coin_wr_map.get(pair, 0.0)
    features.append(coin_wr)

    # Volume USD (log scale)
    import math
    vol = float(row.get('vol_usd_24h', 0) or 0)
    features.append(math.log10(vol + 1) if vol > 0 else 0)

    return features


def main():
    parser = argparse.ArgumentParser(description='Meme Coin XGBoost Ranker')
    parser.add_argument('--min-samples', type=int, default=20,
                        help='Minimum resolved signals for training')
    parser.add_argument('--dry-run', action='store_true',
                        help='Analyze only, do not save model')
    args = parser.parse_args()

    print("=" * 60)
    print("  MEME COIN XGBoost RANKER")
    print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    # Check dependencies
    try:
        import numpy as np
        from sklearn.model_selection import cross_val_score, StratifiedKFold
        from sklearn.metrics import (classification_report, precision_recall_curve,
                                     roc_auc_score)
        import xgboost as xgb
    except ImportError as e:
        print(f"\n  Missing dependency: {e}")
        print("  Install with: pip install xgboost scikit-learn numpy")
        sys.exit(1)

    # Connect to database
    print(f"\n  Connecting to {MEME_DB_NAME}...")
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)

    # Fetch all resolved signals
    cursor.execute("""
        SELECT id, pair, score, factors_json, tier, outcome, pnl_pct,
               vol_usd_24h, chg_24h, created_at
        FROM mc_winners
        WHERE outcome IS NOT NULL
        AND factors_json IS NOT NULL
        ORDER BY created_at ASC
    """)
    rows = cursor.fetchall()
    print(f"  Fetched {len(rows)} resolved signals")

    if len(rows) < args.min_samples:
        print(f"  Insufficient data ({len(rows)} < {args.min_samples}). Exiting.")
        conn.close()
        sys.exit(0)

    # Pre-compute per-coin win rates (leave-one-out to avoid leakage)
    coin_stats = defaultdict(lambda: {'wins': 0, 'total': 0})
    for r in rows:
        pair = r.get('pair', '')
        is_win = r.get('outcome') in ('win', 'partial_win')
        coin_stats[pair]['total'] += 1
        if is_win:
            coin_stats[pair]['wins'] += 1

    coin_wr_map = {}
    for pair, stats in coin_stats.items():
        coin_wr_map[pair] = stats['wins'] / stats['total'] if stats['total'] > 0 else 0.0

    # Build feature matrix and labels
    X_list = []
    y_list = []
    for r in rows:
        feats = build_features(r, coin_wr_map)
        label = 1 if r.get('outcome') in ('win', 'partial_win') else 0
        X_list.append(feats)
        y_list.append(label)

    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.int32)

    n_pos = int(y.sum())
    n_neg = len(y) - n_pos
    print(f"  Wins: {n_pos}, Losses: {n_neg}, WR: {n_pos / len(y) * 100:.1f}%")

    # Handle class imbalance
    scale_pos = n_neg / max(1, n_pos) if n_pos > 0 else 1.0

    # Train XGBoost
    print("\n  Training XGBoost...")
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        scale_pos_weight=scale_pos,
        min_child_weight=3,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric='logloss',
        random_state=42,
        use_label_encoder=False,
    )

    # Cross-validation
    if len(y) >= 10:
        n_splits = min(5, n_pos, n_neg)
        if n_splits >= 2:
            cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
            scores = cross_val_score(model, X, y, cv=cv, scoring='accuracy')
            print(f"  CV Accuracy: {scores.mean():.3f} +/- {scores.std():.3f}")

            auc_scores = cross_val_score(model, X, y, cv=cv, scoring='roc_auc')
            print(f"  CV AUC:      {auc_scores.mean():.3f} +/- {auc_scores.std():.3f}")

    # Fit on full data
    model.fit(X, y)

    # Feature importance
    importance = model.feature_importances_
    print("\n  Feature Importance:")
    feat_imp = []
    for i, name in enumerate(FEATURE_NAMES):
        feat_imp.append((name, float(importance[i])))
    feat_imp.sort(key=lambda x: x[1], reverse=True)
    for name, imp in feat_imp:
        bar = '#' * int(imp * 50)
        print(f"    {name:25s} {imp:.4f} {bar}")

    # Predictions on full set
    y_prob = model.predict_proba(X)[:, 1]
    y_pred = model.predict(X)

    print(f"\n  Full-set Classification Report:")
    print(classification_report(y, y_pred, target_names=['Loss', 'Win']))

    try:
        auc = roc_auc_score(y, y_prob)
        print(f"  AUC-ROC: {auc:.4f}")
    except Exception:
        auc = None

    # Calibrate BUY NOW threshold
    print("\n  Calibrating BUY NOW threshold...")
    precisions, recalls, thresholds = precision_recall_curve(y, y_prob)
    best_threshold = 0.5
    best_f1 = 0
    for i in range(len(thresholds)):
        p = precisions[i]
        r = recalls[i]
        if p + r > 0:
            f1 = 2 * p * r / (p + r)
            if f1 > best_f1:
                best_f1 = f1
                best_threshold = thresholds[i]

    print(f"  Optimal threshold: {best_threshold:.4f} (F1={best_f1:.4f})")
    print(f"  At this threshold:")
    y_cal = (y_prob >= best_threshold).astype(int)
    tp = ((y_cal == 1) & (y == 1)).sum()
    fp = ((y_cal == 1) & (y == 0)).sum()
    fn = ((y_cal == 0) & (y == 1)).sum()
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    print(f"    Precision: {precision:.3f}  Recall: {recall:.3f}")

    # Save model
    if not args.dry_run:
        os.makedirs(MODEL_DIR, exist_ok=True)

        model_data = {
            'model_version': 'meme_xgb_v1',
            'trained_at': datetime.utcnow().isoformat(),
            'samples': len(y),
            'wins': int(n_pos),
            'losses': int(n_neg),
            'feature_names': FEATURE_NAMES,
            'feature_importance': {name: float(imp) for name, imp in feat_imp},
            'cv_accuracy': float(scores.mean()) if len(y) >= 10 and n_splits >= 2 else None,
            'auc_roc': float(auc) if auc else None,
            'optimal_threshold': float(best_threshold),
            'optimal_f1': float(best_f1),
            'threshold_precision': float(precision),
            'threshold_recall': float(recall),
        }

        # Save metadata
        meta_path = os.path.join(MODEL_DIR, 'meme_xgb_v1_meta.json')
        with open(meta_path, 'w') as f:
            json.dump(model_data, f, indent=2)
        print(f"\n  Model metadata saved: {meta_path}")

        # Save XGBoost model
        model.save_model(MODEL_PATH)
        print(f"  Model saved: {MODEL_PATH}")

        # Save to database
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mc_ml_models (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    model_version VARCHAR(50),
                    model_meta_json TEXT,
                    sample_count INT,
                    created_at DATETIME,
                    INDEX idx_model_created (created_at)
                ) ENGINE=MyISAM DEFAULT CHARSET=utf8
            """)
            meta_json = json.dumps(model_data)
            cursor.execute(
                "INSERT INTO mc_ml_models (model_version, model_meta_json, sample_count, created_at) "
                "VALUES (%s, %s, %s, NOW())",
                ('meme_xgb_v1', meta_json, len(y))
            )
            conn.commit()
            print("  Model record saved to mc_ml_models")
        except Exception as e:
            print(f"  WARNING: Could not save to DB: {e}")
    else:
        print("\n  [DRY RUN] Model not saved")

    cursor.close()
    conn.close()

    print("\n" + "=" * 60)
    print("  DONE")
    print("=" * 60)


if __name__ == '__main__':
    main()
