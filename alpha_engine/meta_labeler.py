"""
Meta-Labeling Filter for Alpha Engine Consensus Picks
=====================================================

Meta-labeling approach per Marcos Lopez de Prado (Advances in Financial
Machine Learning, 2018), recommended by Grok audit 2026-03-16.

Instead of predicting direction (already handled by strategy signals), the
meta-label answers: "Should we ACT on this signal?"  A secondary ML model
scores each consensus pick with P(profitable) and only lets through picks
above a configurable threshold.

Pipeline:
    consensus picks --> meta_labeler.score_pick() --> filtered output

Data sources for training:
    - alpha_engine/data/closed_picks.json
    - battleground/data/closed_picks.json
    - data/consensus_outcomes.json (optional)

Fallback: heuristic gate when < 100 closed picks or ML training fails.
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [META-LABEL] %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("meta_labeler")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
ALPHA_DIR = ROOT / "alpha_engine" / "data"
BATTLE_DIR = ROOT / "battleground" / "data"
CONSENSUS_PATH = ROOT / "data" / "consensus_outcomes.json"
ACTIVE_PICKS_PATH = ALPHA_DIR / "active_picks.json"
OUTPUT_PATH = ALPHA_DIR / "meta_filtered_picks.json"
MODEL_PATH = ALPHA_DIR / "meta_labeler_model.pkl"
METRICS_PATH = ALPHA_DIR / "meta_labeler_metrics.json"

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
MIN_PICKS_FOR_ML = 100
PREDICTION_THRESHOLD = 0.60
HEURISTIC_MIN_CONFLUENCE = 3
HEURISTIC_MIN_CONFIDENCE = 0.65
MIN_VALIDATION_AUC = 0.55
TRAIN_RATIO = 0.80
EMBARGO_RATIO = 0.01  # purged-walk-forward gap between train and val slices

# ---------------------------------------------------------------------------
# Known strategy historical win-rates (lookup table)
# ---------------------------------------------------------------------------
STRATEGY_WR: Dict[str, float] = {
    "rsi_macd_confluence": 0.65,
    "multi_timeframe_ema_stack": 0.68,
    "whale_accumulation_detector": 0.62,
    "atr_volatility_breakout": 0.58,
    "cross_sectional_momentum": 0.60,
    "liquidation_cascade_bottom": 0.62,
    "oi_funding_squeeze": 0.58,
    "funding_rate_carry": 0.60,
    "break_of_structure": 0.60,
    "swing_failure_pattern": 0.61,
    "fear_greed_extreme_dca": 0.70,
    "hash_ribbon_buy": 0.78,
    "mvrv_sma_proxy": 0.65,
    "sopr_dip_buy_proxy": 0.62,
    "pentoshi_htf_structure": 0.64,
    "funding_rate_arbitrage": 0.72,
    "hurst_regime_adaptive": 0.58,
    "hurst_mean_reversion": 0.62,
    "multi_sigma_reversal": 0.55,
    "connors_rsi2": 0.68,
    "drawdown_recovery_rsi": 0.56,
    "adaptive_vr_confluence": 0.60,
}
DEFAULT_WR = 0.50


# ===================================================================
# Data Loading
# ===================================================================

def _load_json(path: Path) -> List[Dict[str, Any]]:
    """Safely load a JSON file, returning [] on any error."""
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            log.warning("Expected list in %s, got %s", path, type(data).__name__)
    except Exception as exc:
        log.warning("Failed to load %s: %s", path, exc)
    return []


def load_all_closed_picks() -> List[Dict[str, Any]]:
    """Aggregate closed picks from all known sources."""
    sources = [
        ("alpha_engine", ALPHA_DIR / "closed_picks.json"),
        ("alpha_engine_fast", ALPHA_DIR / "closed_picks_fast.json"),
        ("battleground", BATTLE_DIR / "closed_picks.json"),
        ("consensus", CONSENSUS_PATH),
    ]
    all_picks: List[Dict[str, Any]] = []
    for label, path in sources:
        picks = _load_json(path)
        for p in picks:
            p.setdefault("_source", label)
        log.info("Loaded %d closed picks from %s", len(picks), label)
        all_picks.extend(picks)
    log.info("Total closed picks: %d", len(all_picks))
    return all_picks


# ===================================================================
# Feature Engineering
# ===================================================================

def _symbol_encode(symbol: str, vocab: Dict[str, int]) -> int:
    """Simple label-encoding for symbols."""
    if symbol not in vocab:
        vocab[symbol] = len(vocab)
    return vocab[symbol]


def _hour_sin_cos(dt_str: Optional[str]) -> Tuple[float, float]:
    """Cyclical encoding of hour-of-day."""
    if not dt_str:
        return (0.0, 0.0)
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        h = dt.hour + dt.minute / 60.0
        return (math.sin(2 * math.pi * h / 24), math.cos(2 * math.pi * h / 24))
    except Exception:
        return (0.0, 0.0)


def _day_of_week(dt_str: Optional[str]) -> int:
    """0=Monday ... 6=Sunday; returns 3 (Wed) as neutral default."""
    if not dt_str:
        return 3
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.weekday()
    except Exception:
        return 3


# Trained-model feature-vector dimensionality (kept in sync with extract_features).
NUM_FEATURES = 9


def _pick_epoch(pick: Dict[str, Any]) -> float:
    """Best-effort entry-time epoch for chronological sorting.

    P1 fix 2026-05-16: the walk-forward train/val split in MetaLabeler.train()
    only yields a genuine past->future split if build_dataset emits picks in
    chronological order. Picks aggregated from multiple JSON sources are NOT
    time-ordered, so sort by this key first. Picks with no parseable timestamp
    sort to the end (epoch inf) so they never leak into the train slice.
    """
    ts = pick.get("timestamp") or pick.get("entry_time") or pick.get("created_at")
    if not ts:
        return float("inf")
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
    except Exception:
        return float("inf")


def extract_features(pick: Dict[str, Any], symbol_vocab: Dict[str, int]) -> np.ndarray:
    """
    Build feature vector from a single pick dict.

    Features (9-dim):
        0: num_agreeing_systems  (confluence_strategies length or confluence_score)
        1: average_confidence    (confidence field)
        2: strategy_historical_wr  (STATIC lookup table — not live-computed)
        3: symbol_encoded
        4: hour_sin
        5: hour_cos
        6: day_of_week
        7: risk_reward ratio
        8: ml_score (if available)

    P1 leak fix 2026-05-16 (DAILY_IDEAS_LLMARENA_May162026.MD): the former
    feature 9 `forward_wr` was REMOVED from the trained-model feature vector.
    `forward_wr` is a forward/realized win-rate aggregate; on a CLOSED pick used
    for training it can include outcomes dated after the pick's own entry =
    look-ahead leakage. `heuristic_score()` still reads `forward_wr` separately
    for LIVE scoring, where the strategy's WR-to-date is legitimately known.
    """
    # Num agreeing systems
    confluence_strats = pick.get("confluence_strategies", [])
    if isinstance(confluence_strats, list) and len(confluence_strats) > 0:
        num_agreeing = len(confluence_strats) + 1  # +1 for the primary strategy
    else:
        # Fall back to confluence_score as a proxy
        num_agreeing = max(1, int(pick.get("confluence_score", 1.0)))

    confidence = float(pick.get("confidence", 0.5))
    strategy = pick.get("strategy", "")
    strat_wr = STRATEGY_WR.get(strategy, DEFAULT_WR)
    sym_enc = _symbol_encode(pick.get("symbol", "UNKNOWN"), symbol_vocab)

    ts = pick.get("timestamp") or pick.get("entry_time") or pick.get("created_at", "")
    h_sin, h_cos = _hour_sin_cos(ts)
    dow = _day_of_week(ts)

    rr = float(pick.get("risk_reward", 1.0))
    ml_score = float(pick.get("ml_score", 0.5))

    return np.array([
        num_agreeing,
        confidence,
        strat_wr,
        sym_enc,
        h_sin,
        h_cos,
        dow,
        rr,
        ml_score,
    ], dtype=np.float64)


def build_dataset(
    picks: List[Dict[str, Any]],
) -> Tuple[np.ndarray, np.ndarray, Dict[str, int]]:
    """
    Build (X, y) arrays from closed picks.

    Label: 1 if pnl_pct > 0, else 0.
    """
    symbol_vocab: Dict[str, int] = {}
    rows_X = []
    rows_y = []
    # P1 fix: sort chronologically so the caller's [:split] walk-forward split
    # is a genuine past->future split (picks arrive un-ordered from N sources).
    picks = sorted(picks, key=_pick_epoch)
    for p in picks:
        pnl = p.get("pnl_pct")
        if pnl is None:
            # Some sources use status WIN/LOSS instead
            status = p.get("status", "").upper()
            if status == "WIN":
                pnl = 1.0
            elif status in ("LOST", "LOSS"):
                pnl = -1.0
            else:
                continue  # skip picks without outcome
        label = 1 if float(pnl) > 0 else 0
        feat = extract_features(p, symbol_vocab)
        rows_X.append(feat)
        rows_y.append(label)

    if len(rows_X) == 0:
        return np.empty((0, NUM_FEATURES)), np.empty((0,)), symbol_vocab
    return np.array(rows_X), np.array(rows_y), symbol_vocab


# ===================================================================
# Heuristic Mode
# ===================================================================

def heuristic_score(pick: Dict[str, Any]) -> float:
    """
    Simple rule-based probability estimate when ML is unavailable.

    Returns a pseudo-probability in [0, 1].
    """
    score = 0.50

    # Confluence boost
    confluence_strats = pick.get("confluence_strategies", [])
    n_agreeing = len(confluence_strats) + 1 if confluence_strats else int(pick.get("confluence_score", 1))
    if n_agreeing >= 3:
        score += 0.15
    elif n_agreeing >= 2:
        score += 0.08

    # Confidence boost
    conf = float(pick.get("confidence", 0.5))
    if conf >= 0.85:
        score += 0.12
    elif conf >= 0.70:
        score += 0.06

    # Risk-reward boost
    rr = float(pick.get("risk_reward", 1.0))
    if rr >= 3.0:
        score += 0.08
    elif rr >= 2.0:
        score += 0.04

    # ML score boost
    ml = float(pick.get("ml_score", 0.5))
    if ml >= 0.80:
        score += 0.06

    # Forward WR boost
    fwd_wr = float(pick.get("forward_wr", 0.0))
    fwd_trades = int(pick.get("forward_trades", 0))
    if fwd_trades >= 15 and fwd_wr >= 0.60:
        score += 0.10
    elif fwd_trades >= 10 and fwd_wr >= 0.55:
        score += 0.05

    # Strategy WR boost
    strat = pick.get("strategy", "")
    strat_wr = STRATEGY_WR.get(strat, DEFAULT_WR)
    if strat_wr >= 0.65:
        score += 0.05

    return min(score, 0.99)


# ===================================================================
# ML Model
# ===================================================================

class MetaLabeler:
    """
    Meta-labeling model wrapper.

    Tries XGBoost first, falls back to sklearn RandomForest,
    falls back to heuristic mode.
    """

    def __init__(self) -> None:
        self.model: Any = None
        self.model_type: str = "heuristic"
        self.symbol_vocab: Dict[str, int] = {}
        self.validation_auc: float = 0.0
        self.train_size: int = 0
        self.val_size: int = 0
        self.feature_names = [
            "num_agreeing", "confidence", "strategy_wr", "symbol_enc",
            "hour_sin", "hour_cos", "day_of_week", "risk_reward",
            "ml_score",
        ]

    def train(self, picks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Train or fall back to heuristic.

        Returns metrics dict.
        """
        X, y, self.symbol_vocab = build_dataset(picks)
        total = len(y)

        if total < MIN_PICKS_FOR_ML:
            log.info(
                "Only %d picks (need %d) -- using heuristic mode",
                total, MIN_PICKS_FOR_ML,
            )
            self.model_type = "heuristic"
            return self._heuristic_metrics(total, y)

        # Purged walk-forward split (P1 fix 2026-05-16): build_dataset now emits
        # picks in chronological order, so [:split] is genuinely past->future.
        # An EMBARGO gap drops the train picks immediately adjacent to the val
        # boundary so overlapping outcome windows cannot leak train -> val.
        split_idx = int(total * TRAIN_RATIO)
        embargo = max(1, int(total * EMBARGO_RATIO))
        train_end = max(1, split_idx - embargo)
        X_train, X_val = X[:train_end], X[split_idx:]
        y_train, y_val = y[:train_end], y[split_idx:]
        self.train_size = len(y_train)
        self.val_size = len(y_val)

        if len(np.unique(y_train)) < 2:
            log.warning("Training set has only one class -- falling back to heuristic")
            self.model_type = "heuristic"
            return self._heuristic_metrics(total, y)

        # Try XGBoost, then RandomForest
        try:
            self._train_xgb(X_train, y_train, X_val, y_val)
        except ImportError:
            log.info("xgboost not available, trying sklearn RandomForest")
            try:
                self._train_rf(X_train, y_train, X_val, y_val)
            except ImportError:
                log.warning("sklearn not available -- heuristic mode")
                self.model_type = "heuristic"
                return self._heuristic_metrics(total, y)
        except Exception as exc:
            log.error("ML training failed: %s -- falling back to heuristic", exc)
            self.model_type = "heuristic"
            return self._heuristic_metrics(total, y)

        # Check AUC gate
        if self.validation_auc < MIN_VALIDATION_AUC:
            log.warning(
                "Validation AUC %.3f < %.3f -- falling back to heuristic",
                self.validation_auc, MIN_VALIDATION_AUC,
            )
            self.model_type = "heuristic"
            self.model = None
            return self._heuristic_metrics(total, y)

        log.info(
            "ML model ready (%s): AUC=%.4f, train=%d, val=%d",
            self.model_type, self.validation_auc, self.train_size, self.val_size,
        )
        return self._ml_metrics()

    def _train_xgb(
        self, X_train: np.ndarray, y_train: np.ndarray,
        X_val: np.ndarray, y_val: np.ndarray,
    ) -> None:
        from xgboost import XGBClassifier
        from sklearn.metrics import roc_auc_score

        clf = XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            use_label_encoder=False,
            eval_metric="logloss",
            random_state=42,
            verbosity=0,
        )
        clf.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )
        y_prob = clf.predict_proba(X_val)[:, 1]
        self.validation_auc = float(roc_auc_score(y_val, y_prob))
        self.model = clf
        self.model_type = "xgboost"

    def _train_rf(
        self, X_train: np.ndarray, y_train: np.ndarray,
        X_val: np.ndarray, y_val: np.ndarray,
    ) -> None:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import roc_auc_score

        clf = RandomForestClassifier(
            n_estimators=200,
            max_depth=6,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1,
        )
        clf.fit(X_train, y_train)
        y_prob = clf.predict_proba(X_val)[:, 1]
        self.validation_auc = float(roc_auc_score(y_val, y_prob))
        self.model = clf
        self.model_type = "random_forest"

    def _heuristic_metrics(self, total: int, y: np.ndarray) -> Dict[str, Any]:
        wr = float(y.mean()) if len(y) > 0 else 0.0
        return {
            "model_type": "heuristic",
            "total_picks": total,
            "overall_wr": round(wr, 4),
            "validation_auc": None,
            "reason": f"<{MIN_PICKS_FOR_ML} picks or ML failed",
        }

    def _ml_metrics(self) -> Dict[str, Any]:
        metrics: Dict[str, Any] = {
            "model_type": self.model_type,
            "validation_auc": round(self.validation_auc, 4),
            "train_size": self.train_size,
            "val_size": self.val_size,
        }
        # Feature importances
        if hasattr(self.model, "feature_importances_"):
            imp = self.model.feature_importances_
            metrics["feature_importance"] = {
                name: round(float(v), 4)
                for name, v in zip(self.feature_names, imp)
            }
        return metrics

    def score_pick(self, pick: Dict[str, Any]) -> float:
        """
        Score a single pick.

        Returns P(profitable) in [0, 1].
        Uses ML model if trained and validated, otherwise heuristic.
        """
        if self.model is not None and self.model_type != "heuristic":
            try:
                feat = extract_features(pick, self.symbol_vocab).reshape(1, -1)
                prob = float(self.model.predict_proba(feat)[0, 1])
                return prob
            except Exception as exc:
                log.warning("ML scoring failed: %s -- using heuristic", exc)

        return heuristic_score(pick)

    def save(self) -> None:
        """Persist trained model to disk."""
        if self.model is None:
            return
        try:
            import pickle
            with open(MODEL_PATH, "wb") as f:
                pickle.dump({
                    "model": self.model,
                    "model_type": self.model_type,
                    "symbol_vocab": self.symbol_vocab,
                    "validation_auc": self.validation_auc,
                }, f)
            log.info("Model saved to %s", MODEL_PATH)
        except Exception as exc:
            log.warning("Failed to save model: %s", exc)

    def load(self) -> bool:
        """Load a previously trained model. Returns True on success."""
        try:
            import pickle
            if not MODEL_PATH.exists():
                return False
            with open(MODEL_PATH, "rb") as f:
                state = pickle.load(f)
            self.model = state["model"]
            self.model_type = state["model_type"]
            self.symbol_vocab = state["symbol_vocab"]
            self.validation_auc = state["validation_auc"]
            log.info(
                "Loaded %s model (AUC=%.4f) from %s",
                self.model_type, self.validation_auc, MODEL_PATH,
            )
            return True
        except Exception as exc:
            log.warning("Failed to load model: %s", exc)
            return False


# ===================================================================
# Main Pipeline
# ===================================================================

def run_meta_filter(
    threshold: float = PREDICTION_THRESHOLD,
    retrain: bool = True,
) -> Dict[str, Any]:
    """
    Full meta-labeling pipeline:
      1. Load closed picks, train model
      2. Load active picks
      3. Score each, filter by threshold
      4. Write filtered output
      5. Return summary

    Returns:
        dict with keys: total, passed, killed, kill_rate, model_metrics, picks
    """
    labeler = MetaLabeler()

    # ---- Train or load ----
    if retrain:
        closed = load_all_closed_picks()
        metrics = labeler.train(closed)
        labeler.save()
    else:
        if not labeler.load():
            log.info("No saved model found, training from scratch")
            closed = load_all_closed_picks()
            metrics = labeler.train(closed)
            labeler.save()
        else:
            metrics = {
                "model_type": labeler.model_type,
                "validation_auc": labeler.validation_auc,
                "loaded_from_disk": True,
            }

    # ---- Load active picks ----
    active = _load_json(ACTIVE_PICKS_PATH)
    log.info("Active picks loaded: %d", len(active))

    # ---- Score and filter ----
    passed: List[Dict[str, Any]] = []
    killed: List[Dict[str, Any]] = []

    for pick in active:
        prob = labeler.score_pick(pick)
        pick["meta_score"] = round(prob, 4)
        pick["meta_model"] = labeler.model_type

        if prob >= threshold:
            pick["meta_action"] = "PASS"
            passed.append(pick)
        else:
            pick["meta_action"] = "KILL"
            killed.append(pick)

    total = len(active)
    kill_count = len(killed)
    kill_rate = kill_count / total if total > 0 else 0.0

    log.info(
        "Meta-filter results: %d total, %d passed, %d killed (%.1f%% kill rate)",
        total, len(passed), kill_count, kill_rate * 100,
    )

    # ---- Write output ----
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_type": labeler.model_type,
        "validation_auc": labeler.validation_auc if labeler.model_type != "heuristic" else None,
        "threshold": threshold,
        "total_picks": total,
        "passed_count": len(passed),
        "killed_count": kill_count,
        "kill_rate": round(kill_rate, 4),
        "picks": passed,
        "killed_picks": [
            {
                "id": p.get("id"),
                "symbol": p.get("symbol"),
                "strategy": p.get("strategy"),
                "meta_score": p.get("meta_score"),
            }
            for p in killed
        ],
    }

    try:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, default=str)
        log.info("Filtered picks written to %s", OUTPUT_PATH)
    except Exception as exc:
        log.error("Failed to write output: %s", exc)

    # ---- Write metrics ----
    try:
        metrics_out = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "model_metrics": metrics,
            "filter_stats": {
                "total": total,
                "passed": len(passed),
                "killed": kill_count,
                "kill_rate": round(kill_rate, 4),
                "threshold": threshold,
            },
        }
        with open(METRICS_PATH, "w", encoding="utf-8") as f:
            json.dump(metrics_out, f, indent=2, default=str)
    except Exception:
        pass

    return {
        "total": total,
        "passed": len(passed),
        "killed": kill_count,
        "kill_rate": round(kill_rate, 4),
        "model_metrics": metrics,
        "picks": passed,
    }


# ===================================================================
# CLI Entry Point
# ===================================================================

def main() -> None:
    """Run meta-labeling filter from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Meta-labeling filter for Alpha Engine")
    parser.add_argument(
        "--threshold", type=float, default=PREDICTION_THRESHOLD,
        help=f"Minimum meta-score to pass (default: {PREDICTION_THRESHOLD})",
    )
    parser.add_argument(
        "--no-retrain", action="store_true",
        help="Load saved model instead of retraining",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Score picks but don't write output file",
    )
    args = parser.parse_args()

    result = run_meta_filter(
        threshold=args.threshold,
        retrain=not args.no_retrain,
    )

    print(f"\n{'='*60}")
    print(f"META-LABELER RESULTS")
    print(f"{'='*60}")
    print(f"Model type:      {result['model_metrics'].get('model_type', 'unknown')}")
    auc = result['model_metrics'].get('validation_auc')
    print(f"Validation AUC:  {auc if auc else 'N/A (heuristic)'}")
    print(f"Total picks:     {result['total']}")
    print(f"Passed:          {result['passed']}")
    print(f"Killed:          {result['killed']}")
    print(f"Kill rate:       {result['kill_rate']*100:.1f}%")
    print(f"Output:          {OUTPUT_PATH}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
