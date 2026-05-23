"""ML Meta-Learner — trains on combo results to predict winning permutations.

Uses gradient-boosted trees (XGBoost/LightGBM) to learn which combinations
of systems, logic types, and market conditions produce winning trades.

Features:
  - System composition (one-hot encoding)
  - Logic type (majority/unanimous/weighted/inverse)
  - Number of systems in combo
  - Historical win rates per system
  - Market regime indicators
  - Time-of-day / day-of-week patterns

Target: is_winner (binary classification)
"""
import json
import sqlite3
import numpy as np
from pathlib import Path
from datetime import datetime, timezone

from meta_strategy.db import get_db

MODEL_PATH = Path(__file__).parent / "data" / "meta_learner.joblib"
STATS_PATH = Path(__file__).parent / "data" / "meta_learner_stats.json"
WEIGHTS_PATH = Path(__file__).parent / "data" / "combo_weights.json"

# Known systems for feature encoding
KNOWN_SYSTEMS = [
    "alpha_engine", "claws_of_doom", "crypto_ml_edge", "mercury2",
    "regime_terminal", "social_predict", "goldmine", "stocks_comp",
    "ml_bg_a", "ml_bg_b", "ml_bg_c", "ml_bg_d", "ml_bg_e",
    "kimi_rotc", "signal_engine", "breakout_a", "breakout_b",
    "breakout_c", "ensemble", "ml_crypto_pred", "incubator_fwd",
    "quantum_fusion", "crypto_gainer",
]

LOGIC_TYPES = ["majority", "unanimous", "weighted", "inverse",
               "consensus_plus_inverse", "cascade"]


def _encode_systems(systems_json: str) -> list:
    """One-hot encode system membership."""
    try:
        systems = json.loads(systems_json) if isinstance(systems_json, str) else systems_json
    except Exception:
        systems = []
    return [1 if s in systems else 0 for s in KNOWN_SYSTEMS]


def _encode_logic(logic_type: str) -> list:
    """One-hot encode logic type."""
    return [1 if l == logic_type else 0 for l in LOGIC_TYPES]


def build_features(conn) -> tuple:
    """Build feature matrix and target from permutation results."""
    rows = conn.execute("""
        SELECT pr.*, p.systems, p.logic_type, p.min_agreement
        FROM permutation_results pr
        JOIN permutations p ON p.combo_id = pr.combo_id
        WHERE pr.total_trades >= 3
    """).fetchall()

    if not rows:
        return None, None, None

    X = []
    y = []
    combo_ids = []

    for row in rows:
        r = dict(row)
        systems = json.loads(r["systems"]) if isinstance(r["systems"], str) else r["systems"]

        features = []
        # System composition (23 features)
        features.extend(_encode_systems(r["systems"]))
        # Logic type (6 features)
        features.extend(_encode_logic(r["logic_type"]))
        # Numerical features
        features.append(len(systems))                          # combo_size
        features.append(r.get("min_agreement") or 2)           # min_agreement
        features.append(r.get("total_trades") or 0)            # total_trades
        features.append(r.get("win_rate") or 0)                # historical_wr
        features.append(r.get("avg_pnl_pct") or 0)            # avg_pnl
        features.append(r.get("sharpe") or 0)                  # sharpe
        features.append(r.get("max_drawdown_pct") or 0)        # max_dd
        features.append(r.get("profit_factor") or 0)           # profit_factor
        features.append(r.get("p_value") or 1.0)               # p_value

        X.append(features)
        y.append(1 if r.get("is_winner") else 0)
        combo_ids.append(r["combo_id"])

    X_arr = np.array(X, dtype=np.float64)
    # Replace any remaining NaN/inf with 0 (DB NULLs can leak through)
    X_arr = np.nan_to_num(X_arr, nan=0.0, posinf=0.0, neginf=0.0)
    return X_arr, np.array(y), combo_ids


def train_meta_learner() -> dict:
    """Train the meta-learner on permutation results."""
    conn = get_db()
    X, y, combo_ids = build_features(conn)

    if X is None or len(X) < 10:
        print(f"Insufficient data for ML training ({0 if X is None else len(X)} samples, need 10+)")
        conn.close()
        return {"mode": "insufficient_data", "samples": 0 if X is None else len(X)}

    n_wins = int(y.sum())
    n_losses = len(y) - n_wins

    if n_wins < 3 or n_losses < 3:
        print(f"Class imbalance: wins={n_wins}, losses={n_losses}. Using heuristic.")
        _compute_heuristic_weights(conn)
        conn.close()
        return {"mode": "heuristic", "wins": n_wins, "losses": n_losses}

    try:
        from sklearn.ensemble import GradientBoostingClassifier
        from sklearn.model_selection import cross_val_score
        import joblib

        model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=4,
            min_samples_leaf=3,
            learning_rate=0.1,
            random_state=42,
        )

        # Cross-validate
        cv_folds = min(5, n_wins, n_losses)
        if cv_folds < 2:
            cv_folds = 2
        from sklearn.model_selection import TimeSeriesSplit
        tscv = TimeSeriesSplit(n_splits=cv_folds)
        scores = cross_val_score(model, X, y, cv=tscv, scoring="roc_auc")
        avg_auc = float(scores.mean())

        # Train on full data
        model.fit(X, y)

        # Save model
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, MODEL_PATH)

        # Feature importance
        feature_names = (
            [f"sys_{s}" for s in KNOWN_SYSTEMS] +
            [f"logic_{l}" for l in LOGIC_TYPES] +
            ["combo_size", "min_agreement", "total_trades",
             "historical_wr", "avg_pnl", "sharpe", "max_dd",
             "profit_factor", "p_value"]
        )
        importances = dict(zip(feature_names, model.feature_importances_.tolist()))
        top_features = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:10]

        # Predict win probability for all combos
        _compute_ml_weights(conn, model, X, combo_ids)

        stats = {
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "mode": "gradient_boosting",
            "n_samples": len(X),
            "n_wins": n_wins,
            "n_losses": n_losses,
            "cv_auc_mean": round(avg_auc, 4),
            "cv_auc_std": round(float(scores.std()), 4),
            "top_features": {k: round(v, 4) for k, v in top_features},
        }

        STATS_PATH.write_text(json.dumps(stats, indent=2))
        print(f"Meta-learner trained: {len(X)} samples, AUC={avg_auc:.3f}")
        print(f"Top features: {', '.join(k for k, v in top_features[:5])}")

        conn.close()
        return stats

    except ImportError as e:
        print(f"ML libraries not available: {e}. Using heuristic.")
        _compute_heuristic_weights(conn)
        conn.close()
        return {"mode": "heuristic_fallback", "error": str(e)}


def _compute_ml_weights(conn, model, X, combo_ids):
    """Compute per-combo win probabilities from ML model."""
    weights = {}
    probas = model.predict_proba(X)

    for i, combo_id in enumerate(combo_ids):
        prob = float(probas[i][1])
        weights[combo_id] = {
            "win_probability": round(prob, 4),
            "mode": "ml",
        }

    WEIGHTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    WEIGHTS_PATH.write_text(json.dumps({
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "gradient_boosting",
        "combo_weights": weights,
        "total_combos": len(weights),
    }, indent=2))


def _compute_heuristic_weights(conn):
    """Fallback heuristic weights when ML data is insufficient."""
    rows = conn.execute("""
        SELECT pr.combo_id, pr.win_rate, pr.sharpe, pr.total_trades, pr.p_value
        FROM permutation_results pr
        WHERE pr.total_trades >= 3
    """).fetchall()

    weights = {}
    for row in rows:
        r = dict(row)
        wr = r.get("win_rate", 0.5)
        sharpe = min(r.get("sharpe", 0), 5.0) / 5.0
        trades = min(r.get("total_trades", 0), 50) / 50
        p_val = max(0, 1 - r.get("p_value", 1.0))

        score = 0.4 * wr + 0.3 * sharpe + 0.2 * trades + 0.1 * p_val
        weights[r["combo_id"]] = {
            "win_probability": round(min(max(score, 0.05), 0.95), 4),
            "mode": "heuristic",
        }

    WEIGHTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    WEIGHTS_PATH.write_text(json.dumps({
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "heuristic",
        "combo_weights": weights,
        "total_combos": len(weights),
    }, indent=2))


def predict_best_combos(top_n: int = 10) -> list:
    """Return top-N combos by ML win probability."""
    if not WEIGHTS_PATH.exists():
        return []

    data = json.loads(WEIGHTS_PATH.read_text())
    combos = data.get("combo_weights", {})

    sorted_combos = sorted(
        combos.items(),
        key=lambda x: x[1].get("win_probability", 0),
        reverse=True,
    )

    return [{"combo_id": k, **v} for k, v in sorted_combos[:top_n]]


if __name__ == "__main__":
    print("Meta-Learner — Training...")
    stats = train_meta_learner()
    print(f"\nResult: {json.dumps(stats, indent=2)}")

    print("\nTop combos by ML probability:")
    for combo in predict_best_combos(10):
        print(f"  {combo['combo_id']:45s} p(win)={combo['win_probability']:.3f} [{combo['mode']}]")
