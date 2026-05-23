#!/usr/bin/env python3
"""
HyroTrader ML Pick Optimizer — Adaptive Edge Discovery Engine
==============================================================
Learns from validated signal outcomes + backtest results to find
strategy×symbol×regime combos with real, durable edge.

Data Sources:
  1. hyro_pick_performance.json   — validated TP/SL outcomes (from validator)
  2. hyro_backtest_results.json   — 6-month backtest stats per strategy×symbol
  3. hyro_quan_bridge.json        — current regime + ensemble consensus
  4. hyrotrader_enhanced_picks.json — live technical indicator snapshots
  5. hyro_signal_history.json     — historical signal entries with context

ML Pipeline:
  1. Feature engineering from all sources (backtest stats, regime, technicals)
  2. XGBoost/RF classifier: predict P(WIN) for each strategy×symbol combo
  3. Drift detection: retrain when rolling accuracy < 45%
  4. Edge scoring: rank combos by predicted edge × confidence
  5. Output: ml_pick_rankings.json consumed by hyrotrader_enhanced_scoring.py

Usage:
  python tools/hyro_ml_pick_optimizer.py --save
  python tools/hyro_ml_pick_optimizer.py --retrain --save
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import pickle
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

REPO = Path(__file__).resolve().parent.parent
DATA_DIR = REPO / "audit_dashboard" / "data"
ALPHA_DIR = REPO / "alpha_engine" / "data"

# Input files
PERF_PATH = DATA_DIR / "hyro_pick_performance.json"
BACKTEST_PATH = DATA_DIR / "hyro_backtest_results.json"
QUAN_BRIDGE_PATH = DATA_DIR / "hyro_quan_bridge.json"
ENHANCED_PATH = DATA_DIR / "hyrotrader_enhanced_picks.json"
SIGNAL_HIST_PATH = DATA_DIR / "hyro_signal_history.json"

# Output files
OUTPUT_PATH = DATA_DIR / "hyro_ml_pick_rankings.json"
MODEL_PATH = ALPHA_DIR / "hyro_ml_optimizer_model.pkl"
TRAIN_HISTORY_PATH = ALPHA_DIR / "hyro_ml_train_history.json"

BINANCE_MIRRORS = [
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
]

# All strategy×symbol combos we track
STRATEGIES = [
    "cci_divergence", "adx_vol_breakout", "cmf_cross", "bb_squeeze",
    "multi_ema_stack", "macd_ema50", "triple_ema_trend", "adx_slope_momentum",
    "rsi_pullback", "vwap_trend", "bollinger_mr", "sr_bounce",
    "quan_ensemble",
    # Backtest strategy short names (mapped from hyro_backtest_results.json)
    "rsi2", "volume", "sr",
]
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "XRPUSDT",
    "BNBUSDT", "DOGEUSDT", "LINKUSDT", "ADAUSDT", "DOTUSDT",
    "NEARUSDT", "SUIUSDT", "ARBUSDT", "APTUSDT", "PEPEUSDT",
]

# Minimum samples needed before ML kicks in (otherwise heuristic)
MIN_SAMPLES_FOR_ML = 10
# Drift detection threshold
DRIFT_ACCURACY_THRESHOLD = 0.45
DRIFT_WINDOW = 30

# Feature names (must be stable across train/predict)
FEATURE_NAMES = [
    # Backtest features (static, from 6-month backtest)
    "bt_win_rate", "bt_profit_factor", "bt_max_drawdown_pct",
    "bt_total_trades", "bt_passed", "bt_total_pnl_pct",
    # Validated performance features (rolling, from pick_performance)
    "vp_win_rate", "vp_edge_ratio", "vp_avg_mfe", "vp_avg_mae",
    "vp_profit_factor", "vp_total_signals",
    # Regime features (current market state)
    "regime_trending", "regime_mean_revert", "regime_random",
    "hurst", "fear_greed_norm",
    # Ensemble features
    "ensemble_consensus", "ensemble_confidence",
    # Strategy tier encoding
    "tier_proven", "tier_promising", "tier_demoted",
    # Symbol volatility features (live)
    "atr_pct", "volume_ratio",
    # Cross-strategy features
    "strategy_rank_in_symbol", "symbol_rank_in_strategy",
]


def _safe_load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _fetch_current_price_atr(symbol: str) -> tuple[float, float, float]:
    """Fetch current price, ATR%, and volume ratio for a symbol."""
    for base in BINANCE_MIRRORS:
        url = f"{base}/api/v3/klines?symbol={symbol}&interval=1h&limit=30"
        try:
            req = Request(url, headers={"User-Agent": "HyroMLOpt/1.0"})
            with urlopen(req, timeout=8) as resp:
                klines = json.loads(resp.read())
            if not klines or len(klines) < 15:
                continue

            closes = [float(k[4]) for k in klines]
            highs = [float(k[2]) for k in klines]
            lows = [float(k[3]) for k in klines]
            volumes = [float(k[5]) for k in klines]

            # ATR (14-period)
            trs = []
            for i in range(1, len(closes)):
                tr = max(highs[i] - lows[i],
                         abs(highs[i] - closes[i-1]),
                         abs(lows[i] - closes[i-1]))
                trs.append(tr)
            atr = sum(trs[-14:]) / min(14, len(trs)) if trs else 0
            atr_pct = (atr / closes[-1] * 100) if closes[-1] > 0 else 0

            # Volume ratio
            avg_vol = sum(volumes[-20:]) / min(20, len(volumes)) if volumes else 1
            vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 1.0

            return closes[-1], round(atr_pct, 3), round(vol_ratio, 2)
        except (URLError, OSError, json.JSONDecodeError, IndexError):
            continue
    return 0.0, 2.0, 1.0  # defaults


def build_feature_vectors(
    backtest_data: dict | None,
    perf_data: dict | None,
    quan_bridge: dict | None,
    live_prices: dict[str, tuple] | None,
    strategy_tiers: dict[str, str] | None,
) -> list[dict]:
    """
    Build feature vectors for every strategy×symbol combo.
    Returns list of {strategy, symbol, features: [float], label: int|None}
    """
    bt_lookup = {}
    if backtest_data and "results" in backtest_data:
        for r in backtest_data["results"]:
            key = (r.get("strategy", ""), r.get("symbol", ""))
            bt_lookup[key] = r

    perf_strats = {}
    perf_syms = {}
    if perf_data:
        perf_strats = perf_data.get("strategy_scores", {})
        perf_syms = perf_data.get("symbol_scores", {})

    qb_symbols = {}
    fear_greed = 50
    if quan_bridge:
        qb_symbols = quan_bridge.get("symbols", {})
        fear_greed = quan_bridge.get("fear_greed", 50)

    tiers = strategy_tiers or {}
    prices = live_prices or {}

    # Compute cross-rankings: best strategies per symbol, best symbols per strategy
    strat_rank_by_sym = {}  # {symbol: {strategy: rank}}
    sym_rank_by_strat = {}  # {strategy: {symbol: rank}}

    # Use backtest PnL for ranking
    for sym in SYMBOLS:
        strats_for_sym = []
        for strat in STRATEGIES:
            bt = bt_lookup.get((strat, sym))
            pnl = bt["total_pnl"] if bt and bt.get("total_pnl") is not None else -9999
            strats_for_sym.append((strat, pnl))
        strats_for_sym.sort(key=lambda x: x[1], reverse=True)
        strat_rank_by_sym[sym] = {s: i / max(1, len(strats_for_sym) - 1)
                                   for i, (s, _) in enumerate(strats_for_sym)}

    for strat in STRATEGIES:
        syms_for_strat = []
        for sym in SYMBOLS:
            bt = bt_lookup.get((strat, sym))
            pnl = bt["total_pnl"] if bt and bt.get("total_pnl") is not None else -9999
            syms_for_strat.append((sym, pnl))
        syms_for_strat.sort(key=lambda x: x[1], reverse=True)
        sym_rank_by_strat[strat] = {s: i / max(1, len(syms_for_strat) - 1)
                                     for i, (s, _) in enumerate(syms_for_strat)}

    vectors = []
    for strat in STRATEGIES:
        for sym in SYMBOLS:
            bt = bt_lookup.get((strat, sym), {})
            ps = perf_strats.get(strat, {})
            qb = qb_symbols.get(sym, {})
            price_data = prices.get(sym, (0, 2.0, 1.0))

            # Backtest features
            bt_wr = bt.get("win_rate", 0) / 100.0
            bt_tt = bt.get("total_trades", 0)
            bt_pnl = bt.get("total_pnl", 0)
            bt_pnl_pct = bt_pnl / 5000.0 if bt_pnl else 0  # normalize to account size
            bt_dd = bt.get("max_drawdown", 0) / 5000.0
            bt_passed = 1.0 if bt.get("passed") else 0.0
            # Crude profit factor from backtest
            bt_pf = 0.0
            if bt_tt > 0 and bt.get("wins", 0) > 0:
                avg_win = bt_pnl / bt["wins"] if bt_pnl > 0 and bt["wins"] > 0 else 0
                losses_count = bt_tt - bt.get("wins", 0)
                avg_loss = abs(bt_pnl) / losses_count if bt_pnl < 0 and losses_count > 0 else 1
                bt_pf = avg_win / max(avg_loss, 0.01) if bt_pnl > 0 else 0

            # Validated performance features
            vp_wr = ps.get("win_rate", 0)
            vp_er = ps.get("edge_ratio", 1.0)
            vp_mfe = ps.get("avg_mfe_pct", 0)
            vp_mae = ps.get("avg_mae_pct", 0)
            vp_pf = ps.get("profit_factor", 0)
            vp_n = ps.get("total_signals", 0)

            # Regime features
            regime = qb.get("regime", "RANDOM")
            r_trending = 1.0 if regime == "TRENDING" else 0.0
            r_mr = 1.0 if regime == "MEAN_REVERSION" else 0.0
            r_random = 1.0 if regime == "RANDOM" else 0.0
            hurst = qb.get("hurst", 0.5)
            fg_norm = min(1.0, max(0.0, (fear_greed or 50) / 100.0))

            # Ensemble features
            ens = qb.get("ensemble") or {}
            ens_cons = ens.get("consensus_pct", 0)
            ens_conf = ens.get("avg_confidence", 0)

            # Tier encoding
            tier = tiers.get(strat, "unknown")
            t_proven = 1.0 if tier == "proven" else 0.0
            t_promising = 1.0 if tier == "promising" else 0.0
            t_demoted = 1.0 if tier == "demoted" else 0.0

            # Live price features
            _, atr_pct, vol_ratio = price_data

            # Cross-rankings
            s_rank = strat_rank_by_sym.get(sym, {}).get(strat, 0.5)
            sym_rank = sym_rank_by_strat.get(strat, {}).get(sym, 0.5)

            features = [
                bt_wr, bt_pf, bt_dd, bt_tt, bt_passed, bt_pnl_pct,
                vp_wr, vp_er, vp_mfe, vp_mae, vp_pf, vp_n,
                r_trending, r_mr, r_random, hurst, fg_norm,
                ens_cons, ens_conf,
                t_proven, t_promising, t_demoted,
                atr_pct, vol_ratio,
                s_rank, sym_rank,
            ]

            vectors.append({
                "strategy": strat,
                "symbol": sym,
                "features": features,
                "label": None,  # populated during training
            })

    return vectors


def _load_training_labels(
    perf_data: dict | None,
    backtest_data: dict | None = None,
) -> dict[tuple[str, str], int]:
    """Extract WIN/LOSS labels from validated signals + backtest results.
    
    Priority: real validated outcomes > backtest-derived pseudo-labels.
    Backtest pseudo-labels: passed + WR>=50% → WIN, failed + WR<40% → LOSS.
    """
    labels = {}

    # 1) Backtest-derived pseudo-labels (lower priority, loaded first so real
    #    validated labels can override)
    if backtest_data and "results" in backtest_data:
        for r in backtest_data["results"]:
            strat = r.get("strategy", "")
            sym = r.get("symbol", "")
            if not strat or not sym:
                continue
            wr = r.get("win_rate", 0)
            tt = r.get("total_trades", 0)
            passed = r.get("passed", False)
            failed = r.get("failed", False)
            pnl = r.get("total_pnl", 0)

            # Need at least 5 trades to be meaningful
            if tt < 5:
                continue
            # Clear winners: passed backtest with decent WR and positive PnL
            if passed and wr >= 50 and pnl > 0:
                labels[(strat, sym)] = 1
            # Clear losers: failed or very poor performance
            elif (failed and wr < 40) or (wr < 35 and tt >= 10):
                labels[(strat, sym)] = 0
            # Marginal cases: WR 40-50 with positive PnL → cautious win
            elif wr >= 48 and pnl > 0 and tt >= 10:
                labels[(strat, sym)] = 1
            elif wr < 42 and pnl < 0 and tt >= 8:
                labels[(strat, sym)] = 0

    # 2) Real validated signal outcomes (higher priority, override pseudo-labels)
    if perf_data and "validated_signals" in perf_data:
        for sig in perf_data["validated_signals"]:
            outcome = sig.get("outcome", {})
            result = outcome.get("result", "")
            if result == "WIN":
                label = 1
            elif result == "LOSS":
                label = 0
            else:
                continue  # skip EXPIRED/NO_DATA
            key = (sig.get("strategy", ""), sig.get("symbol", ""))
            labels[key] = label  # override any pseudo-label

    return labels


def train_model(vectors: list[dict], labels: dict, force_retrain: bool = False) -> dict | None:
    """
    Train XGBoost/RF model on labeled strategy×symbol combos.
    Returns model info dict or None if insufficient data.
    """
    try:
        import numpy as np
    except ImportError:
        log.warning("numpy not available — skipping ML training")
        return None

    # Build X, y from labeled vectors
    X_rows = []
    y_rows = []
    for v in vectors:
        key = (v["strategy"], v["symbol"])
        if key in labels:
            X_rows.append(v["features"])
            y_rows.append(labels[key])

    if len(X_rows) < MIN_SAMPLES_FOR_ML:
        log.info(f"Only {len(X_rows)} labeled samples (need {MIN_SAMPLES_FOR_ML}) — using heuristic scoring")
        return None

    X = np.array(X_rows, dtype=np.float64)
    y = np.array(y_rows, dtype=np.int32)
    np.nan_to_num(X, copy=False, nan=0.0, posinf=1.0, neginf=-1.0)

    n_pos = int(y.sum())
    n_neg = len(y) - n_pos
    log.info(f"Training on {len(y)} samples ({n_pos} wins, {n_neg} losses)")

    # Try XGBoost first, fall back to RandomForest
    model = None
    model_type = "unknown"

    try:
        from sklearn.ensemble import GradientBoostingClassifier
        model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            subsample=0.8,
            min_samples_leaf=2,
            random_state=42,
        )
        model.fit(X, y)
        model_type = "GradientBoosting"
        log.info("Trained GradientBoosting model")
    except ImportError:
        pass

    if model is None:
        try:
            from sklearn.ensemble import RandomForestClassifier
            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=5,
                min_samples_leaf=2,
                random_state=42,
            )
            model.fit(X, y)
            model_type = "RandomForest"
            log.info("Trained RandomForest model")
        except ImportError:
            log.warning("sklearn not available — cannot train ML model")
            return None

    # Feature importances
    importances = model.feature_importances_
    top_features = sorted(
        zip(FEATURE_NAMES, importances),
        key=lambda x: x[1], reverse=True
    )[:10]

    # Cross-val accuracy estimate
    try:
        from sklearn.model_selection import cross_val_score
        cv_scores = cross_val_score(model, X, y, cv=min(3, len(y)), scoring="accuracy")
        cv_acc = float(cv_scores.mean())
    except Exception:
        cv_acc = 0.0

    # Save model
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

    # Save training history
    history = _safe_load_json(TRAIN_HISTORY_PATH) or []
    history.append({
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "model_type": model_type,
        "samples": len(y),
        "n_wins": n_pos,
        "n_losses": n_neg,
        "cv_accuracy": round(cv_acc, 3),
        "top_features": [(f, round(float(imp), 4)) for f, imp in top_features[:5]],
    })
    # Keep last 50 entries
    history = history[-50:]
    with open(TRAIN_HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    return {
        "model": model,
        "model_type": model_type,
        "cv_accuracy": cv_acc,
        "top_features": top_features,
        "samples": len(y),
    }


def _check_drift(train_history: list) -> bool:
    """Check if model has drifted — accuracy dropping below threshold."""
    if not train_history or len(train_history) < 2:
        return False
    recent = train_history[-3:]
    avg_acc = sum(h.get("cv_accuracy", 0.5) for h in recent) / len(recent)
    if avg_acc < DRIFT_ACCURACY_THRESHOLD:
        log.warning(f"Drift detected: avg CV accuracy {avg_acc:.3f} < {DRIFT_ACCURACY_THRESHOLD}")
        return True
    return False


def heuristic_score(v: dict) -> float:
    """
    Simple heuristic scoring when ML model unavailable.
    Combines backtest performance + validated performance + regime alignment.
    """
    f = v["features"]
    # f indices match FEATURE_NAMES order
    bt_wr = f[0]
    bt_pf = f[1]
    bt_dd = f[2]
    bt_passed = f[4]
    bt_pnl = f[5]
    vp_wr = f[6]
    vp_er = f[7]
    vp_pf = f[10]
    vp_n = f[11]
    ens_cons = f[17]
    ens_conf = f[18]
    t_proven = f[19]
    t_demoted = f[21]

    score = 30.0  # base

    # Backtest contribution (30 points max)
    score += bt_wr * 15  # up to 15
    score += min(bt_pf * 3, 10)  # up to 10
    score += bt_passed * 5  # 5 if passed

    # Validated performance contribution (30 points max)
    if vp_n >= 3:
        score += vp_wr * 15
        score += min(vp_er * 3, 10)
        score += min(vp_pf * 2, 5)

    # Regime / ensemble bonus (10 points)
    score += ens_cons * 5
    score += ens_conf * 5

    # Tier bonus/penalty
    score += t_proven * 5
    score -= t_demoted * 15

    # DD penalty
    score -= bt_dd * 20

    return max(0, min(100, round(score, 1)))


def score_all_combos(
    vectors: list[dict],
    model_info: dict | None,
) -> list[dict]:
    """Score every strategy×symbol combo using ML model or heuristic fallback."""
    import numpy as np

    scored = []
    for v in vectors:
        if model_info and model_info.get("model"):
            X = np.array([v["features"]], dtype=np.float64)
            np.nan_to_num(X, copy=False, nan=0.0, posinf=1.0, neginf=-1.0)
            try:
                proba = model_info["model"].predict_proba(X)[0]
                # proba[1] = P(WIN)
                p_win = float(proba[1]) if len(proba) > 1 else float(proba[0])
                ml_score = round(p_win * 100, 1)
                scoring_method = "ml"
            except Exception:
                ml_score = heuristic_score(v)
                scoring_method = "heuristic_fallback"
        else:
            ml_score = heuristic_score(v)
            scoring_method = "heuristic"

        scored.append({
            "strategy": v["strategy"],
            "symbol": v["symbol"],
            "ml_edge_score": ml_score,
            "scoring_method": scoring_method,
            "features": {name: round(val, 4) for name, val in zip(FEATURE_NAMES, v["features"])},
        })

    # Sort by score descending
    scored.sort(key=lambda x: x["ml_edge_score"], reverse=True)

    # Assign ranks and grades
    for i, s in enumerate(scored):
        s["rank"] = i + 1
        score = s["ml_edge_score"]
        if score >= 75:
            s["grade"] = "A+"
        elif score >= 65:
            s["grade"] = "A"
        elif score >= 55:
            s["grade"] = "B"
        elif score >= 45:
            s["grade"] = "C"
        elif score >= 35:
            s["grade"] = "D"
        else:
            s["grade"] = "F"

    return scored


def _load_strategy_tiers() -> dict[str, str]:
    """Load strategy tier assignments from hyro_live_strategies.json."""
    path = DATA_DIR / "hyro_live_strategies.json"
    data = _safe_load_json(path)
    if not data or "strategies" not in data:
        return {}
    tiers = {}
    for s in data["strategies"]:
        sid = s.get("id") or s.get("strategy", "")
        tier = s.get("tier", "unknown")
        tiers[sid] = tier
    return tiers


def run(save: bool = False, force_retrain: bool = False) -> dict:
    """Main optimizer pipeline."""
    log.info("=== HyroTrader ML Pick Optimizer ===")

    # Load all data sources
    perf_data = _safe_load_json(PERF_PATH)
    backtest_data = _safe_load_json(BACKTEST_PATH)
    quan_bridge = _safe_load_json(QUAN_BRIDGE_PATH)
    strategy_tiers = _load_strategy_tiers()

    log.info(f"Data sources: perf={'yes' if perf_data else 'no'} "
             f"backtest={'yes' if backtest_data else 'no'} "
             f"quan={'yes' if quan_bridge else 'no'} "
             f"tiers={len(strategy_tiers)}")

    # Fetch live price/vol data for each symbol
    log.info("Fetching live price data...")
    live_prices = {}
    for sym in SYMBOLS:
        live_prices[sym] = _fetch_current_price_atr(sym)
        time.sleep(0.1)

    # Build feature vectors
    log.info("Building feature vectors...")
    vectors = build_feature_vectors(
        backtest_data, perf_data, quan_bridge, live_prices, strategy_tiers
    )
    log.info(f"Built {len(vectors)} strategy×symbol combos")

    # Load training labels from validated signals + backtest results
    labels = _load_training_labels(perf_data, backtest_data)
    log.info(f"Training labels available: {len(labels)} ({sum(labels.values())} wins, {len(labels) - sum(labels.values())} losses)")

    # Check for drift
    train_history = _safe_load_json(TRAIN_HISTORY_PATH) or []
    drift = _check_drift(train_history)

    # Train or load model
    model_info = None
    if len(labels) >= MIN_SAMPLES_FOR_ML:
        if force_retrain or drift or not MODEL_PATH.exists():
            reason = "forced" if force_retrain else ("drift" if drift else "no model")
            log.info(f"Training ML model (reason: {reason})...")
            model_info = train_model(vectors, labels, force_retrain)
        else:
            # Load existing model
            try:
                with open(MODEL_PATH, "rb") as f:
                    model = pickle.load(f)
                model_info = {"model": model, "model_type": "loaded", "cv_accuracy": 0, "top_features": [], "samples": 0}
                log.info("Loaded existing ML model")
            except Exception as e:
                log.warning(f"Failed to load model: {e} — retraining")
                model_info = train_model(vectors, labels, True)
    else:
        log.info(f"Using heuristic scoring ({len(labels)} labels < {MIN_SAMPLES_FOR_ML} min)")

    # Score all combos
    log.info("Scoring all combos...")
    import numpy as np  # ensure available for scoring
    scored = score_all_combos(vectors, model_info)

    # Top picks per symbol (best strategy for each)
    top_per_symbol = {}
    for s in scored:
        sym = s["symbol"]
        if sym not in top_per_symbol:
            top_per_symbol[sym] = s

    # Top picks per strategy (best symbol for each)
    top_per_strategy = {}
    for s in scored:
        strat = s["strategy"]
        if strat not in top_per_strategy:
            top_per_strategy[strat] = s

    # Executive summary
    top_10 = scored[:10]
    bottom_5 = scored[-5:]
    a_grade = [s for s in scored if s["grade"].startswith("A")]
    f_grade = [s for s in scored if s["grade"] == "F"]

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scoring_method": model_info["model_type"] if model_info else "heuristic",
        "total_combos": len(scored),
        "model_info": {
            "type": model_info["model_type"] if model_info else "heuristic",
            "cv_accuracy": round(model_info["cv_accuracy"], 3) if model_info and model_info.get("cv_accuracy") else None,
            "training_samples": model_info["samples"] if model_info else 0,
            "top_features": [(f, round(float(imp), 4)) for f, imp in (model_info.get("top_features", []) if model_info else [])[:5]],
            "drift_detected": drift,
            "labels_available": len(labels),
        },
        "summary": {
            "a_grade_combos": len(a_grade),
            "f_grade_combos": len(f_grade),
            "avg_score": round(sum(s["ml_edge_score"] for s in scored) / len(scored), 1) if scored else 0,
            "best_combo": f"{top_10[0]['strategy']}×{top_10[0]['symbol']}" if top_10 else "none",
            "best_score": top_10[0]["ml_edge_score"] if top_10 else 0,
        },
        "top_10": [
            {
                "rank": s["rank"],
                "strategy": s["strategy"],
                "symbol": s["symbol"],
                "score": s["ml_edge_score"],
                "grade": s["grade"],
                "method": s["scoring_method"],
            }
            for s in top_10
        ],
        "bottom_5": [
            {
                "rank": s["rank"],
                "strategy": s["strategy"],
                "symbol": s["symbol"],
                "score": s["ml_edge_score"],
                "grade": s["grade"],
            }
            for s in bottom_5
        ],
        "best_per_symbol": {
            sym: {
                "strategy": d["strategy"],
                "score": d["ml_edge_score"],
                "grade": d["grade"],
            }
            for sym, d in top_per_symbol.items()
        },
        "best_per_strategy": {
            strat: {
                "symbol": d["symbol"],
                "score": d["ml_edge_score"],
                "grade": d["grade"],
            }
            for strat, d in top_per_strategy.items()
        },
        "all_rankings": [
            {
                "strategy": s["strategy"],
                "symbol": s["symbol"],
                "score": s["ml_edge_score"],
                "grade": s["grade"],
                "method": s["scoring_method"],
            }
            for s in scored
        ],
    }

    if save:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        log.info(f"Saved rankings to {OUTPUT_PATH}")

    # Log summary
    log.info(f"\n{'='*60}")
    log.info(f"ML Pick Optimizer Results ({result['scoring_method']})")
    log.info(f"{'='*60}")
    log.info(f"Total combos scored: {len(scored)}")
    log.info(f"A-grade: {len(a_grade)} | F-grade: {len(f_grade)}")
    log.info(f"Labels: {len(labels)} | Drift: {drift}")
    log.info(f"\nTop 10 combos:")
    for s in top_10:
        log.info(f"  #{s['rank']:3d}  {s['grade']:2s}  {s['ml_edge_score']:5.1f}  {s['strategy']:20s} × {s['symbol']}")
    log.info(f"\nBottom 5 (avoid):")
    for s in bottom_5:
        log.info(f"  #{s['rank']:3d}  {s['grade']:2s}  {s['ml_edge_score']:5.1f}  {s['strategy']:20s} × {s['symbol']}")

    return result


def main():
    parser = argparse.ArgumentParser(description="HyroTrader ML Pick Optimizer")
    parser.add_argument("--save", action="store_true", help="Save results to JSON")
    parser.add_argument("--retrain", action="store_true", help="Force model retrain")
    args = parser.parse_args()

    result = run(save=args.save, force_retrain=args.retrain)

    if not args.save:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
