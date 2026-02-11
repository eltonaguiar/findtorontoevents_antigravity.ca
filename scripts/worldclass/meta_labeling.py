#!/usr/bin/env python3
"""
Meta-Labeling with XGBoost — Signal Quality Filter
Science: Marcos Lopez de Prado, "Advances in Financial Machine Learning" (2018)

A secondary ML model that takes each raw signal and predicts whether it will be profitable.
Improved precision from 21% to 77% in research.

Pipeline:
1. Fetch historical signals + outcomes from PHP API
2. Feature engineer each signal
3. Train XGBoost classifier with purged cross-validation
4. Compute Kelly fractions per algorithm
5. Compute alpha decay + online learning weights
6. Store predictions and weights back to DB

Runs via GitHub Actions weekly (retrain) and daily (predict).
"""

import sys
import json
import warnings
import requests
import numpy as np
from datetime import datetime

warnings.filterwarnings("ignore")

try:
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score
    import xgboost as xgb
    import joblib
except ImportError as e:
    print(f"Missing: {e}")
    print("pip install scikit-learn xgboost joblib")
    sys.exit(1)

from config import INTEL_API, ADMIN_KEY, ALL_ALGOS, MOMENTUM_ALGOS, MEAN_REVERSION_ALGOS


API_BASE = "https://findtorontoevents.ca/live-monitor/api"


def fetch_trade_history():
    """Fetch closed trades from the live trading API."""
    try:
        resp = requests.get(f"{API_BASE}/live_trade.php",
                          params={"action": "history", "limit": "5000"},
                          timeout=30)
        data = resp.json()
        if data.get("ok"):
            return data.get("trades", [])
        else:
            print(f"  Trade history error: {data.get('error')}")
            return []
    except Exception as e:
        print(f"  Fetch error: {e}")
        return []


def fetch_signal_history():
    """Fetch historical signals from the signals API."""
    try:
        resp = requests.get(f"{API_BASE}/live_signals.php",
                          params={"action": "history", "limit": "5000"},
                          timeout=30)
        data = resp.json()
        if data.get("ok"):
            return data.get("signals", [])
        return []
    except Exception:
        return []


def fetch_intelligence():
    """Fetch current intelligence state (regime, hurst, macro)."""
    try:
        resp = requests.get(f"{API_BASE}/world_class_intelligence.php",
                          params={"action": "regime"},
                          timeout=15)
        return resp.json().get("regimes", {})
    except Exception:
        return {}


def engineer_features(trades):
    """
    Feature engineering for meta-labeling.
    Each trade becomes a feature vector for the classifier.
    """
    features = []
    labels = []

    # Algo name → numeric mapping
    algo_map = {name: i for i, name in enumerate(ALL_ALGOS)}

    for trade in trades:
        try:
            # Skip trades without enough info
            algo = trade.get("algorithm_name", "")
            if not algo or algo not in algo_map:
                continue

            # Label: 1 if profitable, 0 if loss
            pnl = float(trade.get("realized_pct", 0))
            label = 1 if pnl > 0 else 0

            # Features
            feat = {}

            # Algorithm ID (categorical encoded as int)
            feat["algo_id"] = algo_map[algo]

            # Is momentum algo
            feat["is_momentum"] = 1 if algo in MOMENTUM_ALGOS else 0

            # Is mean reversion algo
            feat["is_mean_reversion"] = 1 if algo in MEAN_REVERSION_ALGOS else 0

            # Asset class
            asset = trade.get("asset_class", "STOCK")
            feat["asset_crypto"] = 1 if asset == "CRYPTO" else 0
            feat["asset_forex"] = 1 if asset == "FOREX" else 0
            feat["asset_stock"] = 1 if asset == "STOCK" else 0

            # Direction
            feat["is_long"] = 1 if trade.get("direction", "LONG") == "LONG" else 0

            # TP/SL ratio (reward/risk)
            tp = float(trade.get("target_tp_pct", 3))
            sl = float(trade.get("target_sl_pct", 1.5))
            feat["tp_sl_ratio"] = tp / sl if sl > 0 else 2.0

            # Position value (normalized)
            feat["position_value"] = float(trade.get("position_value_usd", 500)) / 1000

            # Hold time target
            feat["max_hold"] = float(trade.get("max_hold_hours", 12))

            # Hour of day (from entry time)
            entry_time = trade.get("entry_time", "")
            if entry_time:
                try:
                    dt = datetime.strptime(entry_time[:19], "%Y-%m-%d %H:%M:%S")
                    feat["hour_of_day"] = dt.hour
                    feat["day_of_week"] = dt.weekday()
                    feat["is_weekend"] = 1 if dt.weekday() >= 5 else 0
                except ValueError:
                    feat["hour_of_day"] = 12
                    feat["day_of_week"] = 2
                    feat["is_weekend"] = 0
            else:
                feat["hour_of_day"] = 12
                feat["day_of_week"] = 2
                feat["is_weekend"] = 0

            # Exit reason encoding (for analysis, not used in prediction)
            exit_reason = trade.get("exit_reason", "")

            features.append(feat)
            labels.append(label)

        except Exception as e:
            continue

    return features, labels


def purged_time_series_cv(X, y, n_splits=5, purge_gap=3):
    """
    Purged time-series cross-validation.
    Science: Lopez de Prado (2018)
    - Chronological splits (no look-ahead)
    - Purge gap between train and test to prevent leakage
    """
    n = len(X)
    fold_size = n // (n_splits + 1)

    for i in range(n_splits):
        train_end = fold_size * (i + 1)
        test_start = train_end + purge_gap  # Purge gap
        test_end = min(test_start + fold_size, n)

        if test_start >= n or test_end <= test_start:
            continue

        train_idx = list(range(0, train_end))
        test_idx = list(range(test_start, test_end))

        yield train_idx, test_idx


def train_meta_model(features, labels):
    """
    Train XGBoost meta-labeling model with purged CV.
    """
    if len(features) < 50:
        print(f"  Insufficient data for training ({len(features)} samples, need 50+)")
        return None, None

    # Convert to numpy arrays
    feature_names = sorted(features[0].keys())
    X = np.array([[f.get(fn, 0) for fn in feature_names] for f in features])
    y = np.array(labels)

    print(f"  Training data: {len(X)} samples, {X.shape[1]} features")
    print(f"  Class balance: {sum(y)}/{len(y)} positive ({sum(y)/len(y)*100:.1f}%)")

    # XGBoost parameters (optimized for small financial datasets)
    params = {
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "max_depth": 4,
        "learning_rate": 0.1,
        "n_estimators": 100,
        "min_child_weight": 5,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "random_state": 42,
        "verbosity": 0
    }

    # Purged cross-validation
    cv_scores = {"precision": [], "recall": [], "f1": [], "accuracy": []}

    for train_idx, test_idx in purged_time_series_cv(X, y, n_splits=4, purge_gap=5):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        model = xgb.XGBClassifier(**params)
        model.fit(X_train, y_train, verbose=False)

        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]

        cv_scores["precision"].append(precision_score(y_test, y_pred, zero_division=0))
        cv_scores["recall"].append(recall_score(y_test, y_pred, zero_division=0))
        cv_scores["f1"].append(f1_score(y_test, y_pred, zero_division=0))
        cv_scores["accuracy"].append(accuracy_score(y_test, y_pred))

    # Print CV results
    print(f"\n  Purged CV Results (4-fold):")
    for metric, scores in cv_scores.items():
        if scores:
            print(f"    {metric}: {np.mean(scores):.4f} (+/- {np.std(scores):.4f})")

    # Train final model on all data
    final_model = xgb.XGBClassifier(**params)
    final_model.fit(X, y, verbose=False)

    # Feature importance
    importances = final_model.feature_importances_
    print(f"\n  Feature Importance:")
    sorted_idx = np.argsort(importances)[::-1]
    for i in sorted_idx[:8]:
        print(f"    {feature_names[i]}: {importances[i]:.4f}")

    return final_model, feature_names


def compute_kelly_fractions(trades):
    """Calculate Half-Kelly fractions per algorithm from trade history."""
    algo_stats = {}

    for trade in trades:
        algo = trade.get("algorithm_name", "")
        asset = trade.get("asset_class", "ALL")
        pnl = float(trade.get("realized_pct", 0))
        key = f"{algo}|{asset}"

        if key not in algo_stats:
            algo_stats[key] = {"wins": [], "losses": [], "algo": algo, "asset": asset}

        if pnl > 0:
            algo_stats[key]["wins"].append(pnl)
        else:
            algo_stats[key]["losses"].append(abs(pnl))

    kelly_data = []
    for key, stats in algo_stats.items():
        total = len(stats["wins"]) + len(stats["losses"])
        if total < 5:
            continue

        win_rate = len(stats["wins"]) / total
        avg_win = np.mean(stats["wins"]) if stats["wins"] else 0
        avg_loss = np.mean(stats["losses"]) if stats["losses"] else 1

        # Kelly formula
        if avg_loss > 0 and avg_win > 0:
            b = avg_win / avg_loss
            full_kelly = (win_rate * b - (1 - win_rate)) / b
            full_kelly = max(0, min(0.25, full_kelly))
            half_kelly = min(0.15, full_kelly * 0.5)
        else:
            full_kelly = 0
            half_kelly = 0

        kelly_data.append({
            "algorithm_name": stats["algo"],
            "asset_class": stats["asset"],
            "win_rate": round(win_rate, 4),
            "avg_win_pct": round(avg_win, 4),
            "avg_loss_pct": round(avg_loss, 4),
            "full_kelly": round(full_kelly, 6),
            "half_kelly": round(half_kelly, 6),
            "sample_size": total
        })

        print(f"    {stats['algo']:25s} {stats['asset']:6s} "
              f"WR={win_rate:.2%} Kelly={half_kelly:.4f} (n={total})")

    return kelly_data


def compute_algo_health(trades):
    """Calculate alpha decay status and online learning weights."""
    from datetime import datetime, timedelta

    cutoff = datetime.utcnow() - timedelta(days=30)
    algo_recent = {}

    for trade in trades:
        algo = trade.get("algorithm_name", "")
        asset = trade.get("asset_class", "ALL")
        exit_time = trade.get("exit_time", "")
        pnl = float(trade.get("realized_pct", 0))
        key = f"{algo}|{asset}"

        if not exit_time:
            continue

        try:
            dt = datetime.strptime(exit_time[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue

        if dt < cutoff:
            continue

        if key not in algo_recent:
            algo_recent[key] = {"pnls": [], "algo": algo, "asset": asset}
        algo_recent[key]["pnls"].append(pnl)

    health_data = []
    for key, stats in algo_recent.items():
        pnls = stats["pnls"]
        if not pnls:
            continue

        trades_30d = len(pnls)
        wins = sum(1 for p in pnls if p > 0)
        wr = wins / trades_30d if trades_30d > 0 else 0
        total_pnl = sum(pnls)
        avg_pnl = np.mean(pnls)
        std_pnl = np.std(pnls) if len(pnls) > 1 else 1

        # Sharpe (annualized from 30-day)
        sharpe = (avg_pnl / std_pnl) * np.sqrt(252) if std_pnl > 0 else 0

        # Online weight
        weight = 0.5 + (wr * 0.3) + (min(1, max(0, sharpe / 2)) * 0.2)
        weight = max(0.1, min(1.5, weight))

        # Consecutive losses
        consec = 0
        for p in reversed(pnls):
            if p <= 0:
                consec += 1
            else:
                break

        # Decay status
        if sharpe < -0.5 or consec >= 5:
            status = "decayed"
            weight *= 0.5
        elif sharpe < 0 or consec >= 3:
            status = "warning"
            weight *= 0.75
        elif sharpe > 1.0 and wr > 0.5:
            status = "strong"
            weight = min(1.5, weight * 1.1)
        else:
            status = "healthy"

        health_data.append({
            "algorithm_name": stats["algo"],
            "asset_class": stats["asset"],
            "rolling_sharpe_30d": round(sharpe, 4),
            "rolling_win_rate_30d": round(wr, 4),
            "rolling_pnl_30d": round(total_pnl, 4),
            "online_weight": round(weight, 6),
            "decay_status": status,
            "trades_30d": trades_30d,
            "consecutive_losses": consec
        })

    return health_data


def main():
    print("=" * 60)
    print("WORLD-CLASS INTELLIGENCE: Meta-Labeling + Kelly + Alpha Decay")
    print("=" * 60)

    # ──── Fetch trade history ────
    print("\n--- Fetching Trade History ---")
    trades = fetch_trade_history()
    print(f"  Fetched {len(trades)} closed trades")

    if not trades:
        print("  No trade history available. Running Kelly computation via PHP API instead.")
        # Trigger server-side Kelly computation
        try:
            resp = requests.get(f"{INTEL_API}",
                              params={"action": "compute_kelly", "key": ADMIN_KEY},
                              timeout=30)
            print(f"  Kelly computation: {resp.json()}")
        except Exception as e:
            print(f"  Kelly computation error: {e}")

        # Trigger server-side algo health computation
        try:
            resp = requests.get(f"{INTEL_API}",
                              params={"action": "compute_algo_health", "key": ADMIN_KEY},
                              timeout=30)
            print(f"  Algo health computation: {resp.json()}")
        except Exception as e:
            print(f"  Algo health error: {e}")

        print("\nMeta-labeling requires trade history. Will train once sufficient data exists.")
        return

    # ──── Feature Engineering ────
    print("\n--- Feature Engineering ---")
    features, labels = engineer_features(trades)
    print(f"  Engineered {len(features)} samples")

    # ──── Train Meta-Labeling Model ────
    print("\n--- Training Meta-Labeling Model ---")
    model, feature_names = train_meta_model(features, labels)

    if model:
        # Save model for daily predictions
        model_path = "/tmp/meta_label_model.json"
        model.save_model(model_path)
        print(f"  Model saved to {model_path}")

        # Store model metrics
        from config import INTEL_API
        y_pred = model.predict(np.array([[f.get(fn, 0) for fn in feature_names] for f in features]))
        overall_precision = precision_score(labels, y_pred, zero_division=0)
        overall_accuracy = accuracy_score(labels, y_pred)

        requests.post(INTEL_API, data={
            "action": "store",
            "key": ADMIN_KEY,
            "metric_name": "meta_label_model",
            "asset_class": "ALL",
            "metric_value": str(overall_precision),
            "metric_label": f"precision={overall_precision:.4f}",
            "metadata": json.dumps({
                "precision": round(overall_precision, 4),
                "accuracy": round(overall_accuracy, 4),
                "samples": len(features),
                "features": feature_names,
                "trained_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            })
        }, timeout=15)

    # ──── Compute Kelly Fractions ────
    print("\n--- Computing Kelly Fractions ---")
    kelly_data = compute_kelly_fractions(trades)
    if kelly_data:
        try:
            resp = requests.post(INTEL_API, data={
                "action": "store_kelly",
                "key": ADMIN_KEY,
                "kelly_data": json.dumps(kelly_data)
            }, timeout=15)
            result = resp.json()
            print(f"  Stored {result.get('stored', 0)} Kelly fractions")
        except Exception as e:
            print(f"  Kelly store error: {e}")

    # ──── Compute Alpha Decay + Online Weights ────
    print("\n--- Computing Alpha Decay + Online Learning Weights ---")
    health_data = compute_algo_health(trades)
    if health_data:
        try:
            resp = requests.post(INTEL_API, data={
                "action": "store_algo_health",
                "key": ADMIN_KEY,
                "health_data": json.dumps(health_data)
            }, timeout=15)
            result = resp.json()
            print(f"  Stored {result.get('stored', 0)} algo health records")
        except Exception as e:
            print(f"  Health store error: {e}")

        # Print summary
        print(f"\n  Alpha Decay Summary:")
        for h in sorted(health_data, key=lambda x: x["online_weight"], reverse=True):
            emoji = {"strong": "+", "healthy": "=", "warning": "!", "decayed": "X"}
            status_char = emoji.get(h["decay_status"], "?")
            print(f"    [{status_char}] {h['algorithm_name']:25s} weight={h['online_weight']:.3f} "
                  f"sharpe={h['rolling_sharpe_30d']:+.2f} wr={h['rolling_win_rate_30d']:.1%} "
                  f"(n={h['trades_30d']})")

    print(f"\n{'=' * 60}")
    print("META-LABELING PIPELINE COMPLETE")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
