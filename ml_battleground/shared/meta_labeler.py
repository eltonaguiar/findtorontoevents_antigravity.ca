"""
Shared Meta-Labeler for ML Battleground Systems (A, B, C)
=========================================================
Lopez de Prado M2 pattern: predicts whether M1's signal will be profitable.
Filters 50-80% of false positives by learning from closed trade outcomes.

Modes:
  1. Heuristic mode (<50 closed trades): simple rule-based filtering
  2. ML mode (>=50 closed trades): RandomForest trained on closed picks

Features used (available in all battleground systems):
  - ml_score / confidence
  - fear_greed (0-100)
  - risk_reward ratio
  - market_health encoded
  - timeframe encoded
  - strategy encoded
  - funding_rate
  - hour of day
  - signal_type (BUY/SELL)

Usage:
  from shared.meta_labeler import should_take_trade

  # Returns (should_trade: bool, meta_confidence: float, reason: str)
  result = should_take_trade(signal_dict, closed_picks, system_name)
"""

import os
import json
import logging
import numpy as np
from datetime import datetime
from typing import Tuple, List, Dict, Optional

logger = logging.getLogger(__name__)

# Model cache (avoid retraining every scan cycle)
_model_cache: Dict[str, dict] = {}
_MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ensemble_data")

# Minimum closed trades to switch from heuristic to ML mode
MIN_TRADES_FOR_ML = 50

# Meta-labeler threshold: signals below this are filtered
META_THRESHOLD = 0.55


# ---------------------------------------------------------------------------
# Feature Engineering (from signal dict)
# ---------------------------------------------------------------------------

HEALTH_MAP = {"safe": 0, "caution": 1, "warning": 2, "panic": 3}
TIMEFRAME_MAP = {"15m": 0, "30m": 1, "1h": 2, "4h": 3, "1d": 4}

# Strategy name -> integer encoding (deterministic hash fallback)
_STRATEGY_CODES: Dict[str, int] = {}
_STRATEGY_COUNTER = [0]


def _encode_strategy(name: str) -> int:
    """Encode strategy name to integer."""
    if name not in _STRATEGY_CODES:
        _STRATEGY_CODES[name] = _STRATEGY_COUNTER[0]
        _STRATEGY_COUNTER[0] += 1
    return _STRATEGY_CODES[name]


def _extract_features(signal: dict) -> np.ndarray:
    """
    Extract a fixed-length feature vector from a signal/pick dict.
    Returns numpy array of shape (10,).
    """
    # Confidence / ML score
    confidence = float(signal.get("confidence", signal.get("ml_score", 0.5)))

    # Fear & Greed (0-100, normalized to 0-1)
    fg = float(signal.get("fear_greed", 50)) / 100.0

    # Risk-reward ratio
    rr = float(signal.get("risk_reward", 1.5))

    # Market health encoded
    health_str = str(signal.get("market_health", "safe")).lower()
    health = HEALTH_MAP.get(health_str, 0)

    # Timeframe encoded
    tf_str = str(signal.get("timeframe", "4h")).lower()
    timeframe = TIMEFRAME_MAP.get(tf_str, 3)

    # Strategy encoded (hash-based)
    strategy = _encode_strategy(str(signal.get("strategy", "unknown")))

    # Funding rate
    funding = float(signal.get("funding_rate", 0.0))

    # Hour of day (from timestamp)
    hour = 12.0
    ts = signal.get("timestamp", "")
    if ts:
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            hour = dt.hour
        except Exception:
            pass
    hour_normalized = hour / 24.0

    # Signal type (BUY=1, SELL=0)
    sig_type = 1.0 if signal.get("signal_type", "BUY") == "BUY" else 0.0

    # ATR value normalized (use ratio to entry price if available)
    atr_val = float(signal.get("atr_value", 0.0))
    entry = float(signal.get("entry_price", 1.0))
    atr_pct = (atr_val / entry) if entry > 0 else 0.02

    return np.array([
        confidence,       # 0
        fg,               # 1
        rr,               # 2
        health,           # 3
        timeframe,        # 4
        strategy,         # 5
        funding,          # 6
        hour_normalized,  # 7
        sig_type,         # 8
        atr_pct,          # 9
    ], dtype=np.float64)


def _extract_target(pick: dict) -> Optional[int]:
    """
    Extract binary target from a closed pick.
    1 = profitable (TP hit or positive PnL), 0 = loss.
    """
    exit_reason = pick.get("exit_reason", "")
    if exit_reason == "take_profit":
        return 1
    if exit_reason == "stop_loss":
        return 0

    # Fallback: use net PnL
    pnl = pick.get("net_pnl_pct", None)
    if pnl is not None:
        return 1 if float(pnl) > 0 else 0

    return None


# ---------------------------------------------------------------------------
# Heuristic Mode (< 50 trades)
# ---------------------------------------------------------------------------

def _heuristic_filter(signal: dict, closed_picks: list) -> Tuple[bool, float, str]:
    """
    Simple rule-based filtering when insufficient data for ML.

    Rules:
    1. Confidence must be >= threshold (0.52 cold-start, 0.60 normal)
    2. R:R must be >= 1.3
    3. If market_health is panic, only SELL signals pass
    4. If strategy has >5 closed trades and WR < 30%, block it

    Cold-start mode (< 10 closed picks): relax confidence to 0.52 so systems
    can accumulate enough data for the heuristic/ML to become meaningful.
    """
    confidence = float(signal.get("confidence", signal.get("ml_score", 0.5)))
    rr = float(signal.get("risk_reward", 1.5))
    health = str(signal.get("market_health", "safe")).lower()
    sig_type = signal.get("signal_type", "BUY")
    strategy = signal.get("strategy", "unknown")

    # Cold-start mode: relax confidence threshold when system has few/no closed picks
    n_closed = len(closed_picks) if closed_picks else 0
    min_confidence = 0.52 if n_closed < 10 else 0.60

    # Rule 1: Minimum confidence (adaptive for cold start)
    if confidence < min_confidence:
        return False, confidence, f"heuristic: confidence {confidence:.2f} < {min_confidence:.2f} (n_closed={n_closed})"

    # Rule 2: Minimum R:R
    if rr < 1.3:
        return False, confidence * 0.8, f"heuristic: R:R {rr:.1f} < 1.3"

    # Rule 3: Panic — reduce BUY confidence but don't hard-block
    # Hard-blocking all BUYs was too aggressive — missed F&G contrarian bounces
    if health == "panic" and sig_type == "BUY":
        if confidence < 0.55:
            return False, confidence * 0.5, "heuristic: low-conf BUY blocked in panic market"
        return True, confidence * 0.85, "heuristic: BUY penalized in panic (not blocked)"

    # Rule 4: Strategy recent WR check
    if closed_picks:
        strat_trades = [p for p in closed_picks if p.get("strategy") == strategy]
        if len(strat_trades) >= 5:
            wins = sum(1 for p in strat_trades if (p.get("net_pnl_pct", 0) or 0) > 0)
            wr = wins / len(strat_trades)
            if wr < 0.30:
                return False, confidence * 0.4, f"heuristic: {strategy} WR={wr:.0%} < 30% (n={len(strat_trades)})"

    # Passed all rules
    # Compute a pseudo meta-confidence from rules
    meta_conf = confidence * min(rr / 2.0, 1.0)
    return True, meta_conf, "heuristic: passed"


# ---------------------------------------------------------------------------
# ML Mode (>= 50 trades)
# ---------------------------------------------------------------------------

def _train_meta_model(closed_picks: list, system_name: str) -> Optional[dict]:
    """
    Train a RandomForest meta-labeler on closed picks.
    Returns dict with 'model', 'threshold', 'metrics' or None.
    """
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.calibration import CalibratedClassifierCV
        from sklearn.model_selection import TimeSeriesSplit
        from sklearn.metrics import precision_score, recall_score
    except ImportError:
        logger.warning("scikit-learn not available for meta-labeler training")
        return None

    # Build feature matrix and target
    X_list = []
    y_list = []

    for pick in closed_picks:
        target = _extract_target(pick)
        if target is None:
            continue
        features = _extract_features(pick)
        X_list.append(features)
        y_list.append(target)

    if len(X_list) < MIN_TRADES_FOR_ML:
        return None

    X = np.array(X_list)
    y = np.array(y_list)

    # Time-series split (don't shuffle — respect temporal order)
    n_splits = min(3, len(X) // 20)
    if n_splits < 2:
        return None

    tscv = TimeSeriesSplit(n_splits=n_splits)
    precisions = []
    recalls = []

    for train_idx, test_idx in tscv.split(X):
        # Purge gap: remove last 5% of training to avoid leakage
        purge = max(1, len(train_idx) // 20)
        train_idx = train_idx[:-purge]

        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        if len(np.unique(y_train)) < 2:
            continue

        rf = RandomForestClassifier(
            n_estimators=100,
            max_depth=4,
            min_samples_leaf=5,
            class_weight="balanced",
            random_state=42,
        )
        rf.fit(X_train, y_train)

        preds = rf.predict(X_test)
        precisions.append(precision_score(y_test, preds, zero_division=0))
        recalls.append(recall_score(y_test, preds, zero_division=0))

    if not precisions:
        return None

    avg_precision = float(np.mean(precisions))
    avg_recall = float(np.mean(recalls))

    # Train final model on all data
    if len(np.unique(y)) < 2:
        return None

    final_rf = RandomForestClassifier(
        n_estimators=100,
        max_depth=4,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=42,
    )
    final_rf.fit(X, y)

    # Calibrate probabilities
    try:
        cal_rf = CalibratedClassifierCV(final_rf, method="isotonic", cv=3, ensemble=True)
        cal_rf.fit(X, y)
        model = cal_rf
    except Exception:
        model = final_rf

    metrics = {
        "avg_precision": round(avg_precision, 4),
        "avg_recall": round(avg_recall, 4),
        "training_samples": len(X),
        "positive_rate": round(float(y.mean()), 4),
        "trained_at": datetime.utcnow().isoformat(),
        "system": system_name,
    }

    logger.info(
        "Meta-labeler trained: precision=%.1f%%, recall=%.1f%%, samples=%d, pos_rate=%.1f%%",
        avg_precision * 100, avg_recall * 100, len(X), y.mean() * 100,
    )

    return {"model": model, "threshold": META_THRESHOLD, "metrics": metrics}


def _get_or_train_model(closed_picks: list, system_name: str) -> Optional[dict]:
    """Get cached model or train a new one. Retrain every 20 new trades."""
    cache_key = system_name
    cached = _model_cache.get(cache_key)

    n_closed = len(closed_picks)

    # Check if we need to retrain (every 20 new trades or first time)
    if cached is not None:
        trained_on = cached.get("metrics", {}).get("training_samples", 0)
        if n_closed - trained_on < 20:
            return cached

    if n_closed < MIN_TRADES_FOR_ML:
        return None

    result = _train_meta_model(closed_picks, system_name)
    if result is not None:
        _model_cache[cache_key] = result
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def should_take_trade(
    signal: dict,
    closed_picks: list,
    system_name: str = "unknown",
) -> Tuple[bool, float, str]:
    """
    Decide whether to take a trade based on meta-labeling.

    Args:
        signal: The candidate signal/pick dict
        closed_picks: List of all closed picks for this system
        system_name: System identifier for model caching

    Returns:
        (should_trade: bool, meta_confidence: float, reason: str)
        Gracefully degrades: if anything fails, returns (True, original_confidence, "passthrough")
    """
    try:
        n_closed = len(closed_picks) if closed_picks else 0

        # Mode selection: heuristic vs ML
        if n_closed < MIN_TRADES_FOR_ML:
            return _heuristic_filter(signal, closed_picks)

        # Try ML mode
        model_info = _get_or_train_model(closed_picks, system_name)

        if model_info is None:
            # ML training failed — fall back to heuristic
            return _heuristic_filter(signal, closed_picks)

        model = model_info["model"]
        threshold = model_info["threshold"]

        # Extract features and predict
        features = _extract_features(signal).reshape(1, -1)
        meta_proba = float(model.predict_proba(features)[:, 1][0])

        should_trade = meta_proba >= threshold

        if should_trade:
            reason = f"meta-ML: passed (confidence={meta_proba:.3f} >= {threshold})"
        else:
            reason = f"meta-ML: blocked (confidence={meta_proba:.3f} < {threshold})"

        return should_trade, meta_proba, reason

    except Exception as e:
        # Graceful degradation: never block trading due to meta-labeler errors
        logger.warning("Meta-labeler error: %s — passing signal through", e)
        confidence = float(signal.get("confidence", signal.get("ml_score", 0.5)))
        return True, confidence, f"passthrough (error: {e})"


def filter_signals_batch(
    signals: list,
    closed_picks: list,
    system_name: str = "unknown",
) -> list:
    """
    Filter a batch of signals through the meta-labeler.
    Returns only signals that pass the meta-labeling gate.
    Adds 'meta_confidence' and 'meta_reason' to each passing signal.
    """
    passed = []
    filtered_count = 0

    for sig in signals:
        should_trade, meta_conf, reason = should_take_trade(sig, closed_picks, system_name)

        if should_trade:
            sig["meta_confidence"] = round(meta_conf, 4)
            sig["meta_reason"] = reason
            passed.append(sig)
        else:
            filtered_count += 1
            symbol = sig.get("symbol", "?")
            strategy = sig.get("strategy", "?")
            print(f"    [META] {symbol} {strategy} filtered: {reason}")

    if filtered_count > 0:
        total = len(signals)
        print(f"  [META-LABELER] {len(passed)}/{total} signals passed ({filtered_count} filtered)")

    return passed
