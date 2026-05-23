#!/usr/bin/env python3
"""
Price Change Regression Model
=============================
Predicts HOW MUCH a crypto will move (not just direction).

Model 1: PnL% Regression  -- GradientBoosting with decision stumps (numpy-only)
Model 2: Optimal TP/SL    -- best TP/SL per symbol+strategy combo

Training data:
  - mega_training_data.json  (308K trades, ~50K with pnl_pct)
  - closed_picks.json        (500 trades with rich features)

Zero external ML dependencies -- uses numpy-only gradient boosting.

Usage:
  python price_regression.py              # Train + save model
  python price_regression.py --predict    # Demo predictions on recent picks

Author: Alpha Engine
"""

import sys
import os
import io
import json
import math
import hashlib
import pickle
import warnings
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

warnings.filterwarnings('ignore')

import numpy as np

# ---------------------------------------------------------------------------
# Numpy-only Gradient Boosting Regressor
# ---------------------------------------------------------------------------

class DecisionStump:
    """Single-split decision tree (depth=1 weak learner)."""
    __slots__ = ('feature_idx', 'threshold', 'left_val', 'right_val')

    def __init__(self):
        self.feature_idx = 0
        self.threshold = 0.0
        self.left_val = 0.0
        self.right_val = 0.0

    def predict(self, X: np.ndarray) -> np.ndarray:
        mask = X[:, self.feature_idx] <= self.threshold
        out = np.empty(X.shape[0], dtype=np.float64)
        out[mask] = self.left_val
        out[~mask] = self.right_val
        return out


class DecisionTreeRegressor:
    """
    Minimal depth-limited decision tree for gradient boosting.
    Splits greedily by variance reduction on a random subset of features.
    """

    def __init__(self, max_depth: int = 4, min_samples_leaf: int = 20,
                 max_features_frac: float = 0.8):
        self.max_depth = max_depth
        self.min_samples_leaf = min_samples_leaf
        self.max_features_frac = max_features_frac
        self._tree = None

    def fit(self, X: np.ndarray, y: np.ndarray):
        n_features = X.shape[1]
        n_try = max(1, int(n_features * self.max_features_frac))
        self._tree = self._build(X, y, depth=0, feature_subset_size=n_try)
        return self

    def _build(self, X, y, depth, feature_subset_size):
        n = len(y)
        node_val = float(np.mean(y))

        if depth >= self.max_depth or n < 2 * self.min_samples_leaf:
            return ('leaf', node_val)

        best_score = np.var(y) * n  # total variance * n = SSE
        best_split = None

        # Random feature subset
        all_feats = np.arange(X.shape[1])
        if feature_subset_size < X.shape[1]:
            feat_idx = np.random.choice(all_feats, size=feature_subset_size, replace=False)
        else:
            feat_idx = all_feats

        for fi in feat_idx:
            col = X[:, fi]
            # Try up to 20 quantile-based thresholds for speed
            unique_vals = np.unique(col)
            if len(unique_vals) <= 1:
                continue
            if len(unique_vals) > 20:
                percentiles = np.linspace(5, 95, 20)
                thresholds = np.percentile(col, percentiles)
                thresholds = np.unique(thresholds)
            else:
                thresholds = (unique_vals[:-1] + unique_vals[1:]) / 2.0

            for thr in thresholds:
                left_mask = col <= thr
                n_left = np.sum(left_mask)
                n_right = n - n_left

                if n_left < self.min_samples_leaf or n_right < self.min_samples_leaf:
                    continue

                y_left = y[left_mask]
                y_right = y[~left_mask]
                sse = np.var(y_left) * n_left + np.var(y_right) * n_right

                if sse < best_score:
                    best_score = sse
                    best_split = (fi, thr, left_mask)

        if best_split is None:
            return ('leaf', node_val)

        fi, thr, left_mask = best_split
        left_tree = self._build(X[left_mask], y[left_mask], depth + 1, feature_subset_size)
        right_tree = self._build(X[~left_mask], y[~left_mask], depth + 1, feature_subset_size)
        return ('split', fi, thr, left_tree, right_tree)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.array([self._predict_one(x, self._tree) for x in X], dtype=np.float64)

    def _predict_one(self, x, node):
        if node[0] == 'leaf':
            return node[1]
        _, fi, thr, left, right = node
        if x[fi] <= thr:
            return self._predict_one(x, left)
        else:
            return self._predict_one(x, right)


class GradientBoostingRegressorNP:
    """
    Gradient Boosting Regressor using numpy only.
    Uses Huber loss for robustness to outliers.
    """

    def __init__(self, n_estimators: int = 200, learning_rate: float = 0.05,
                 max_depth: int = 4, min_samples_leaf: int = 20,
                 subsample: float = 0.8, huber_delta: float = 5.0,
                 random_state: int = 42):
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.min_samples_leaf = min_samples_leaf
        self.subsample = subsample
        self.huber_delta = huber_delta
        self.random_state = random_state

        self.init_prediction_ = 0.0
        self.trees_ = []
        self.feature_importances_ = None

    def _huber_negative_gradient(self, y, pred, delta):
        """Pseudo-residuals for Huber loss."""
        diff = y - pred
        mask = np.abs(diff) <= delta
        grad = np.where(mask, diff, delta * np.sign(diff))
        return grad

    def fit(self, X: np.ndarray, y: np.ndarray):
        np.random.seed(self.random_state)
        n, n_features = X.shape

        # Initialize with median (robust)
        self.init_prediction_ = float(np.median(y))
        pred = np.full(n, self.init_prediction_, dtype=np.float64)
        self.trees_ = []

        # Feature importance accumulator
        feat_importance = np.zeros(n_features, dtype=np.float64)
        subsample_size = max(1, int(n * self.subsample))

        for i in range(self.n_estimators):
            # Compute pseudo-residuals (Huber)
            residuals = self._huber_negative_gradient(y, pred, self.huber_delta)

            # Subsample
            if self.subsample < 1.0:
                idx = np.random.choice(n, size=subsample_size, replace=False)
                X_sub, r_sub = X[idx], residuals[idx]
            else:
                X_sub, r_sub = X, residuals

            # Fit tree to residuals
            tree = DecisionTreeRegressor(
                max_depth=self.max_depth,
                min_samples_leaf=self.min_samples_leaf,
                max_features_frac=0.8,
            )
            tree.fit(X_sub, r_sub)

            # Update predictions
            update = tree.predict(X) * self.learning_rate
            pred += update
            self.trees_.append(tree)

            # Accumulate feature importance (approximate via split features)
            self._accumulate_importance(tree._tree, feat_importance)

            if (i + 1) % 50 == 0 or i == 0:
                mae = np.mean(np.abs(y - pred))
                print(f"    Iter {i+1:4d}/{self.n_estimators}: MAE={mae:.4f}%")

        # Normalize feature importances
        total = feat_importance.sum()
        if total > 0:
            self.feature_importances_ = feat_importance / total
        else:
            self.feature_importances_ = np.ones(n_features) / n_features

        return self

    def _accumulate_importance(self, node, importance):
        """Walk tree and count how many times each feature is used for splitting."""
        if node[0] == 'leaf':
            return
        _, fi, thr, left, right = node
        importance[fi] += 1.0
        self._accumulate_importance(left, importance)
        self._accumulate_importance(right, importance)

    def predict(self, X: np.ndarray) -> np.ndarray:
        pred = np.full(X.shape[0], self.init_prediction_, dtype=np.float64)
        for tree in self.trees_:
            pred += tree.predict(X) * self.learning_rate
        return pred


# ---------------------------------------------------------------------------
# Time Series Split (numpy-only)
# ---------------------------------------------------------------------------

def time_series_split(n: int, n_splits: int = 5):
    """Generate TimeSeriesSplit indices."""
    min_train = n // (n_splits + 1)
    fold_size = n // (n_splits + 1)
    for i in range(n_splits):
        train_end = min_train + fold_size * i + fold_size
        test_end = min(train_end + fold_size, n)
        if test_end <= train_end:
            continue
        train_idx = np.arange(0, train_end)
        test_idx = np.arange(train_end, test_end)
        yield train_idx, test_idx


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def mae(y_true, y_pred):
    return float(np.mean(np.abs(y_true - y_pred)))

def rmse(y_true, y_pred):
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

def r2_score(y_true, y_pred):
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    if ss_tot == 0:
        return 0.0
    return float(1.0 - ss_res / ss_tot)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
MEGA_DATA_PATH = DATA_DIR / "mega_training_data.json"
CLOSED_PICKS_PATH = DATA_DIR / "closed_picks.json"
MODEL_PATH = DATA_DIR / "price_regression_model.pkl"

# ---------------------------------------------------------------------------
# Feature engineering helpers
# ---------------------------------------------------------------------------

ASSET_CLASS_MAP = {'crypto': 0, 'stock': 1, 'forex': 2}
DIRECTION_MAP = {'LONG': 1, 'SHORT': 0, 'BUY': 1, 'SELL': 0}


def stable_hash(s: str, mod: int = 10000) -> int:
    """Hash a string to a stable integer for categorical encoding."""
    return int(hashlib.md5(s.encode('utf-8', errors='replace')).hexdigest()[:8], 16) % mod


def extract_features_mega(trade: dict) -> dict | None:
    """Extract features from a mega_training_data trade."""
    pnl = trade.get('pnl_pct')
    if pnl is None:
        return None

    pnl = max(-100.0, min(100.0, float(pnl)))

    entry_date = trade.get('entry_date', '')
    hour_utc = 12
    day_of_week = 3
    if entry_date:
        try:
            dt = datetime.fromisoformat(entry_date.replace('Z', '+00:00'))
            hour_utc = dt.hour
            day_of_week = dt.weekday()
        except Exception:
            pass

    strategy = trade.get('strategy', 'unknown')
    symbol = trade.get('symbol', 'unknown')
    direction_str = trade.get('direction', 'LONG')
    asset_class_str = trade.get('asset_class', 'crypto')
    source = trade.get('source', 'unknown')

    features = {
        'strategy_hash': stable_hash(strategy),
        'symbol_hash': stable_hash(symbol),
        'direction': DIRECTION_MAP.get(direction_str.upper(), 1),
        'entry_hour_utc': hour_utc,
        'day_of_week': day_of_week,
        'asset_class': ASSET_CLASS_MAP.get(asset_class_str, 0),
        'source_weight': float(trade.get('source_weight', 0.7)),
        'source_hash': stable_hash(source),
        'confidence_num': _parse_confidence(trade.get('confidence', 0.5)),
        'rsi_at_entry': 50.0,
        'atr_at_entry': 0.0,
        'volume_ratio': 1.0,
        'tp_distance_pct': 0.0,
        'sl_distance_pct': 0.0,
        'hold_days': 0.0,
        'strategies_agreeing': float(trade.get('strategies_agreeing', 0)),
        'avg_backtest_winrate': float(trade.get('avg_backtest_winrate', 0)),
    }

    return {'features': features, 'target': pnl}


def extract_features_closed(pick: dict) -> dict | None:
    """Extract features from a closed_picks trade (richer data)."""
    pnl = pick.get('pnl_pct')
    if pnl is None:
        return None

    pnl = max(-100.0, min(100.0, float(pnl)))

    entry_date = pick.get('entry_date', '')
    hour_utc = 12
    day_of_week = 3
    if entry_date:
        try:
            dt = datetime.fromisoformat(entry_date.replace('Z', '+00:00'))
            hour_utc = dt.hour
            day_of_week = dt.weekday()
        except Exception:
            pass

    strategy = pick.get('strategy', 'unknown')
    symbol = pick.get('symbol', 'unknown')
    direction_str = pick.get('signal_type', pick.get('direction', 'LONG'))
    asset_class_str = pick.get('category', 'crypto')

    entry_price = float(pick.get('entry_price', 0) or 0)
    tp = float(pick.get('take_profit', 0) or 0)
    sl = float(pick.get('stop_loss', 0) or 0)

    tp_dist = abs(tp - entry_price) / entry_price * 100 if entry_price and tp else 0.0
    sl_dist = abs(sl - entry_price) / entry_price * 100 if entry_price and sl else 0.0

    features = {
        'strategy_hash': stable_hash(strategy),
        'symbol_hash': stable_hash(symbol),
        'direction': DIRECTION_MAP.get(direction_str.upper(), 1),
        'entry_hour_utc': hour_utc,
        'day_of_week': day_of_week,
        'asset_class': ASSET_CLASS_MAP.get(asset_class_str, 0),
        'source_weight': float(pick.get('source_weight', 1.0) or 1.0),
        'source_hash': stable_hash(pick.get('source', pick.get('source_system', 'closed'))),
        'confidence_num': _parse_confidence(pick.get('confidence', 0.5)),
        'rsi_at_entry': float(pick.get('rsi_at_entry', pick.get('rsi', 50.0)) or 50.0),
        'atr_at_entry': float(pick.get('atr_at_entry', pick.get('atr', 0.0)) or 0.0),
        'volume_ratio': float(pick.get('volume_ratio', 1.0) or 1.0),
        'tp_distance_pct': tp_dist,
        'sl_distance_pct': sl_dist,
        'hold_days': float(pick.get('hold_days', 0) or 0),
        'strategies_agreeing': float(pick.get('consensus_count', pick.get('signal_count', 0)) or 0),
        'avg_backtest_winrate': float(pick.get('pattern_predicted_wr', pick.get('trader_win_rate', 0)) or 0),
    }

    return {'features': features, 'target': pnl}


def _parse_confidence(val) -> float:
    """Parse confidence which can be float, string ('HIGH'/'MED'/'LOW'), or None."""
    if val is None:
        return 0.5
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).upper()
    conf_map = {'HIGH': 0.85, 'MEDIUM': 0.6, 'MED': 0.6, 'LOW': 0.3}
    return conf_map.get(val_str, 0.5)


FEATURE_COLUMNS = [
    'strategy_hash', 'symbol_hash', 'direction', 'entry_hour_utc',
    'day_of_week', 'asset_class', 'source_weight', 'source_hash',
    'confidence_num', 'rsi_at_entry', 'atr_at_entry', 'volume_ratio',
    'tp_distance_pct', 'sl_distance_pct', 'hold_days',
    'strategies_agreeing', 'avg_backtest_winrate',
]


def features_to_array(features: dict) -> list:
    """Convert feature dict to ordered list matching FEATURE_COLUMNS."""
    return [features.get(col, 0.0) for col in FEATURE_COLUMNS]


# ---------------------------------------------------------------------------
# Model 2: Optimal TP/SL lookup table
# ---------------------------------------------------------------------------

def build_tp_sl_model(trades: list[dict]) -> dict:
    """
    Build a lookup table of recommended TP/SL per symbol and strategy.
    """
    groups = defaultdict(lambda: {'wins': [], 'losses': [], 'all_pnl': []})

    for trade in trades:
        sym = trade.get('symbol', 'unknown')
        strat = trade.get('strategy', 'unknown')
        key = (stable_hash(sym), stable_hash(strat))

        pnl = trade.get('pnl_pct')
        if pnl is None:
            continue
        pnl = float(pnl)

        entry = float(trade.get('entry_price', 0) or 0)
        tp_val = trade.get('take_profit', 0)

        groups[key]['all_pnl'].append(pnl)

        if pnl > 0:
            groups[key]['wins'].append(pnl)
            if tp_val and entry:
                tp_dist = abs(float(tp_val) - entry) / entry * 100
                groups[key]['wins'].append(tp_dist)
        else:
            groups[key]['losses'].append(abs(pnl))

    recommendations = {}
    for key, data in groups.items():
        wins = data['wins']
        losses = data['losses']
        all_pnl = data['all_pnl']

        if len(all_pnl) < 3:
            continue

        if wins:
            recommended_tp = float(np.median(wins))
            recommended_tp = max(0.5, min(15.0, recommended_tp))
        else:
            recommended_tp = 3.0

        if losses:
            recommended_sl = float(np.median(losses))
            recommended_sl = max(0.3, min(10.0, recommended_sl))
        else:
            recommended_sl = 2.0

        avg_pnl = float(np.mean(all_pnl))
        win_rate = len(wins) / len(all_pnl) if all_pnl else 0.5

        recommendations[key] = {
            'recommended_tp_pct': round(recommended_tp, 2),
            'recommended_sl_pct': round(recommended_sl, 2),
            'avg_pnl': round(avg_pnl, 4),
            'sample_size': len(all_pnl),
            'win_rate': round(win_rate, 4),
        }

    # Global fallback
    all_pnls = [pnl for g in groups.values() for pnl in g['all_pnl']]
    all_wins = [p for p in all_pnls if p > 0]
    all_losses = [abs(p) for p in all_pnls if p < 0]

    recommendations[('__global__', '__global__')] = {
        'recommended_tp_pct': round(float(np.median(all_wins)) if all_wins else 3.0, 2),
        'recommended_sl_pct': round(float(np.median(all_losses)) if all_losses else 2.0, 2),
        'avg_pnl': round(float(np.mean(all_pnls)) if all_pnls else 0.0, 4),
        'sample_size': len(all_pnls),
        'win_rate': round(len(all_wins) / len(all_pnls) if all_pnls else 0.5, 4),
    }

    return recommendations


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def load_training_data() -> tuple[list[list[float]], list[float], list[dict]]:
    """Load and featurize all training data, sorted by date."""
    records = []

    # 1. Load mega_training_data.json
    print(f"Loading {MEGA_DATA_PATH} ...")
    try:
        with open(MEGA_DATA_PATH, 'r', encoding='utf-8') as f:
            mega = json.load(f)
        trades = mega.get('trades', [])
        print(f"  Raw trades: {len(trades)}")

        count = 0
        for trade in trades:
            result = extract_features_mega(trade)
            if result:
                date_str = trade.get('entry_date', '2020-01-01')
                records.append((date_str, features_to_array(result['features']),
                                result['target'], trade))
                count += 1
        print(f"  Usable trades (with pnl_pct): {count}")
    except FileNotFoundError:
        print(f"  WARNING: {MEGA_DATA_PATH} not found, skipping")
    except Exception as e:
        print(f"  ERROR loading mega data: {e}")

    # 2. Load closed_picks.json
    print(f"Loading {CLOSED_PICKS_PATH} ...")
    try:
        with open(CLOSED_PICKS_PATH, 'r', encoding='utf-8') as f:
            closed = json.load(f)
        print(f"  Raw picks: {len(closed)}")

        count = 0
        for pick in closed:
            result = extract_features_closed(pick)
            if result:
                date_str = pick.get('entry_date', '2020-01-01')
                records.append((date_str, features_to_array(result['features']),
                                result['target'], pick))
                count += 1
        print(f"  Usable picks (with pnl_pct): {count}")
    except FileNotFoundError:
        print(f"  WARNING: {CLOSED_PICKS_PATH} not found, skipping")
    except Exception as e:
        print(f"  ERROR loading closed picks: {e}")

    if not records:
        print("ERROR: No training data loaded!")
        sys.exit(1)

    records.sort(key=lambda r: r[0] or '2020-01-01')

    X = [r[1] for r in records]
    y = [r[2] for r in records]
    raw = [r[3] for r in records]

    return X, y, raw


def train_model():
    """Train the price regression model and save it."""
    print("=" * 70)
    print("PRICE REGRESSION MODEL -- Training (numpy-only GBR)")
    print("=" * 70)

    X_list, y_list, raw_trades = load_training_data()
    X = np.array(X_list, dtype=np.float64)
    y = np.array(y_list, dtype=np.float64)

    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    y = np.nan_to_num(y, nan=0.0, posinf=100.0, neginf=-100.0)

    print(f"\nTotal samples: {len(y)}")
    print(f"Target (pnl_pct) stats:")
    print(f"  Mean:   {np.mean(y):.4f}%")
    print(f"  Median: {np.median(y):.4f}%")
    print(f"  Std:    {np.std(y):.4f}%")
    print(f"  Min:    {np.min(y):.2f}%  Max: {np.max(y):.2f}%")
    print(f"  >0:     {np.sum(y > 0)} ({np.sum(y > 0)/len(y)*100:.1f}%)")
    print(f"  <0:     {np.sum(y < 0)} ({np.sum(y < 0)/len(y)*100:.1f}%)")

    # --- Time-series cross-validation ---
    print(f"\n{'=' * 70}")
    print("Cross-validation (TimeSeriesSplit, 5 folds)")
    print(f"{'=' * 70}")

    fold_metrics = []

    for fold_i, (train_idx, test_idx) in enumerate(time_series_split(len(y), n_splits=5)):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        print(f"\n  --- Fold {fold_i+1} (train={len(train_idx)}, test={len(test_idx)}) ---")

        model = GradientBoostingRegressorNP(
            n_estimators=150,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            min_samples_leaf=20,
            huber_delta=5.0,
            random_state=42 + fold_i,
        )
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        fold_mae = mae(y_test, y_pred)
        fold_rmse = rmse(y_test, y_pred)
        fold_r2 = r2_score(y_test, y_pred)

        direction_correct = np.sum(np.sign(y_pred) == np.sign(y_test))
        direction_acc = direction_correct / len(y_test) * 100

        fold_metrics.append({'mae': fold_mae, 'rmse': fold_rmse, 'r2': fold_r2, 'dir_acc': direction_acc})
        print(f"  Fold {fold_i+1} result: MAE={fold_mae:.4f}%  RMSE={fold_rmse:.4f}%  R2={fold_r2:.4f}  DirAcc={direction_acc:.1f}%")

    avg_mae = np.mean([m['mae'] for m in fold_metrics])
    avg_rmse = np.mean([m['rmse'] for m in fold_metrics])
    avg_r2 = np.mean([m['r2'] for m in fold_metrics])
    avg_dir = np.mean([m['dir_acc'] for m in fold_metrics])
    print(f"\n  AVG:    MAE={avg_mae:.4f}%  RMSE={avg_rmse:.4f}%  R2={avg_r2:.4f}  DirAcc={avg_dir:.1f}%")

    # --- Train final model on ALL data ---
    print(f"\n{'=' * 70}")
    print("Training final model on all data...")
    print(f"{'=' * 70}")

    final_model = GradientBoostingRegressorNP(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        min_samples_leaf=20,
        huber_delta=5.0,
        random_state=42,
    )
    final_model.fit(X, y)

    # Feature importances
    importances = final_model.feature_importances_
    importance_pairs = sorted(zip(FEATURE_COLUMNS, importances), key=lambda x: -x[1])
    print("\nFeature Importances:")
    for name, imp in importance_pairs:
        bar = '#' * int(imp * 100)
        print(f"  {name:25s} {imp:.4f}  {bar}")

    # --- Build TP/SL model ---
    print(f"\n{'=' * 70}")
    print("Building Optimal TP/SL lookup model...")
    print(f"{'=' * 70}")

    tp_sl_model = build_tp_sl_model(raw_trades)
    global_rec = tp_sl_model.get(('__global__', '__global__'), {})
    print(f"  Symbol+Strategy combos: {len(tp_sl_model) - 1}")
    print(f"  Global defaults -- TP: {global_rec.get('recommended_tp_pct', '?')}%  SL: {global_rec.get('recommended_sl_pct', '?')}%")

    # --- Calibration ---
    y_pred_all = final_model.predict(X)
    residuals = y - y_pred_all
    residual_std = float(np.std(residuals))
    print(f"\n  Residual std (calibration): {residual_std:.4f}%")

    # --- Save ---
    model_bundle = {
        'version': '1.0.0',
        'trained_at': datetime.utcnow().isoformat(),
        'pnl_model': final_model,
        'tp_sl_model': tp_sl_model,
        'feature_columns': FEATURE_COLUMNS,
        'feature_importances': {name: float(imp) for name, imp in importance_pairs},
        'calibration': {
            'residual_std': residual_std,
            'train_mean_pnl': float(np.mean(y)),
            'train_samples': len(y),
        },
        'cv_metrics': {
            'avg_mae': float(avg_mae),
            'avg_rmse': float(avg_rmse),
            'avg_r2': float(avg_r2),
            'avg_direction_accuracy': float(avg_dir),
        },
    }

    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model_bundle, f)
    print(f"\nModel saved to: {MODEL_PATH}")
    print(f"File size: {MODEL_PATH.stat().st_size / 1024:.1f} KB")

    return model_bundle


# ---------------------------------------------------------------------------
# Prediction API
# ---------------------------------------------------------------------------

_cached_model = None


def _load_model():
    global _cached_model
    if _cached_model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model not found at {MODEL_PATH}. Run `python price_regression.py` to train first."
            )
        with open(MODEL_PATH, 'rb') as f:
            _cached_model = pickle.load(f)
    return _cached_model


def predict_pnl(pick: dict) -> dict:
    """
    Predict PnL% and recommend TP/SL for a new pick.

    Args:
        pick: dict with keys like symbol, strategy, direction/signal_type,
              entry_price, take_profit, stop_loss, confidence, etc.

    Returns:
        {
            'predicted_pnl_pct': float,
            'predicted_direction_confidence': float,  # 0-1
            'recommended_tp_pct': float,
            'recommended_sl_pct': float,
            'predicted_hold_hours': float,
            'position_size_multiplier': float,  # 1.0 = normal, >1 = bigger
            'prediction_quality': str,           # 'high'/'medium'/'low'
        }
    """
    bundle = _load_model()
    model = bundle['pnl_model']
    tp_sl_model = bundle['tp_sl_model']
    calibration = bundle['calibration']
    residual_std = calibration['residual_std']

    result = extract_features_closed(pick)
    if result is None:
        pick_copy = dict(pick)
        pick_copy['pnl_pct'] = 0.0
        result = extract_features_closed(pick_copy)

    feat_array = np.array([features_to_array(result['features'])], dtype=np.float64)
    feat_array = np.nan_to_num(feat_array, nan=0.0, posinf=0.0, neginf=0.0)

    predicted_pnl = float(model.predict(feat_array)[0])
    predicted_pnl = max(-50.0, min(50.0, predicted_pnl))

    # Direction confidence
    if residual_std > 0:
        z_score = abs(predicted_pnl) / residual_std
        direction_confidence = min(1.0, z_score / 3.0)
    else:
        direction_confidence = 0.5

    # TP/SL lookup
    sym_hash = stable_hash(pick.get('symbol', 'unknown'))
    strat_hash = stable_hash(pick.get('strategy', 'unknown'))
    tp_sl = tp_sl_model.get(
        (sym_hash, strat_hash),
        tp_sl_model.get(('__global__', '__global__'), {})
    )

    recommended_tp = tp_sl.get('recommended_tp_pct', 3.0)
    recommended_sl = tp_sl.get('recommended_sl_pct', 2.0)

    # Adjust TP/SL based on predicted magnitude
    if abs(predicted_pnl) > 1.0:
        magnitude_ratio = min(3.0, abs(predicted_pnl) / recommended_tp) if recommended_tp > 0 else 1.0
        recommended_tp = round(recommended_tp * max(0.5, min(2.0, magnitude_ratio)), 2)

    # Predicted hold time heuristic
    hold_hours = max(1.0, abs(predicted_pnl) * 4.0)
    hold_hours = min(168.0, hold_hours)

    # Position size multiplier
    if direction_confidence > 0.6 and abs(predicted_pnl) > 2.0:
        size_mult = min(2.0, 1.0 + direction_confidence)
    elif direction_confidence < 0.3 or abs(predicted_pnl) < 0.3:
        size_mult = max(0.25, direction_confidence)
    else:
        size_mult = 1.0

    # Quality assessment
    sample_size = tp_sl.get('sample_size', 0)
    if sample_size >= 20 and direction_confidence > 0.5:
        quality = 'high'
    elif sample_size >= 5 or direction_confidence > 0.3:
        quality = 'medium'
    else:
        quality = 'low'

    return {
        'predicted_pnl_pct': round(predicted_pnl, 4),
        'predicted_direction_confidence': round(direction_confidence, 4),
        'recommended_tp_pct': round(recommended_tp, 2),
        'recommended_sl_pct': round(recommended_sl, 2),
        'predicted_hold_hours': round(hold_hours, 1),
        'position_size_multiplier': round(size_mult, 2),
        'prediction_quality': quality,
    }


def predict_batch(picks: list[dict]) -> list[dict]:
    """Predict PnL% for a batch of picks. Loads model once."""
    _load_model()
    return [predict_pnl(p) for p in picks]


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo_predictions():
    """Run predictions on closed_picks and show comparison."""
    print("\n" + "=" * 70)
    print("DEMO: Predictions vs Actual on closed_picks.json")
    print("=" * 70)

    if not MODEL_PATH.exists():
        print("Model not found. Training first...")
        train_model()

    try:
        with open(CLOSED_PICKS_PATH, 'r', encoding='utf-8') as f:
            picks = json.load(f)
    except FileNotFoundError:
        print(f"  {CLOSED_PICKS_PATH} not found.")
        return

    print(f"\n{'Symbol':<12} {'Strategy':<28} {'Actual':>8} {'Predicted':>10} {'Dir?':>5} {'TP%':>6} {'SL%':>6} {'Size':>5} {'Quality':<7}")
    print("-" * 100)

    correct_dir = 0
    total = 0
    abs_errors = []

    for pick in picks[:50]:
        actual = pick.get('pnl_pct')
        if actual is None:
            continue

        pred = predict_pnl(pick)
        predicted = pred['predicted_pnl_pct']
        actual = float(actual)

        dir_match = '  Y' if (predicted >= 0) == (actual >= 0) else '  N'
        if (predicted >= 0) == (actual >= 0):
            correct_dir += 1
        total += 1
        abs_errors.append(abs(predicted - actual))

        sym = pick.get('symbol', '?')[:11]
        strat = pick.get('strategy', '?')[:27]
        print(f"{sym:<12} {strat:<28} {actual:>7.3f}% {predicted:>9.4f}% {dir_match:>5} {pred['recommended_tp_pct']:>5.2f}% {pred['recommended_sl_pct']:>5.2f}% {pred['position_size_multiplier']:>5.2f} {pred['prediction_quality']:<7}")

    if total > 0:
        print(f"\n  Direction accuracy (sample): {correct_dir}/{total} = {correct_dir/total*100:.1f}%")
        print(f"  Mean absolute error (sample): {np.mean(abs_errors):.4f}%")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    if '--predict' in sys.argv:
        demo_predictions()
    else:
        bundle = train_model()
        demo_predictions()
        print("\n" + "=" * 70)
        print("DONE. Model ready for integration.")
        print(f"  Import: from alpha_engine.price_regression import predict_pnl")
        print(f"  Usage:  result = predict_pnl({{'symbol': 'BTCUSDT', 'strategy': 'ema_crossover', ...}})")
        print("=" * 70)
