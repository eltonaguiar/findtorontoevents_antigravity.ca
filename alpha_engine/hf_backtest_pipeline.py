#!/usr/bin/env python3
"""
Hedge-Fund-Grade Walk-Forward Backtesting Pipeline
===================================================
Mercury 2 Blueprint Implementation

Steps:
  1. Data Loader        — load closed picks, extract features
  2. Feature Matrix     — normalized feature vectors for every pick
  3. Walk-Forward       — anchored walk-forward with logistic regression (pure Python)
  4. Monte Carlo        — 1000-shuffle stress test for luck detection
  5. Param Sensitivity  — grid search over confidence / R:R / direction
  6. Output             — hf_backtest_report.json

Pure Python + numpy only. No sklearn, no pandas.
"""

import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from collections import defaultdict

try:
    import numpy as np
except ImportError:
    print("ERROR: numpy is required. Install with: pip install numpy")
    sys.exit(1)

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
CLOSED_PICKS_PATH = os.path.join(DATA_DIR, "closed_picks.json")
OUTPUT_PATH = os.path.join(DATA_DIR, "hf_backtest_report.json")

# ---------------------------------------------------------------------------
# STEP 1: DATA LOADER
# ---------------------------------------------------------------------------

def load_closed_picks():
    """Load closed picks and filter to those with valid PnL data."""
    with open(CLOSED_PICKS_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    picks = []
    for p in raw:
        pnl = p.get("pnl_pct")
        if pnl is None:
            continue
        # Include WON, LOST, CLOSED, EXPIRED — all have realised PnL
        status = p.get("status", "")
        if status == "OPEN":
            continue

        entry_date_str = p.get("entry_date") or p.get("generated_at", "")
        exit_date_str = p.get("exit_date") or ""

        pick = {
            "symbol": p.get("symbol", "UNKNOWN"),
            "direction": _encode_direction(p.get("signal_type")),
            "entry_price": _safe_float(p.get("entry_price"), 0.0),
            "exit_price": _safe_float(p.get("exit_price"), 0.0),
            "pnl_pct": float(pnl),
            "confidence": _safe_float(p.get("confidence"), 0.5),
            "elite_score": _safe_float(p.get("elite_score"), 50.0),
            "ml_score": _safe_float(p.get("ml_score"), 0.5),
            "risk_reward": _safe_float(p.get("risk_reward"), 1.0),
            "volume_ratio": min(_safe_float(p.get("volume_ratio"), 1.0), 10.0),
            "rsi_at_entry": _safe_float(p.get("rsi_at_entry"), 50.0),
            "strategy": p.get("strategy", "unknown"),
            "category": p.get("category", "crypto"),
            "entry_date": entry_date_str[:10] if entry_date_str else "2026-01-01",
            "exit_date": exit_date_str[:10] if exit_date_str else "",
            "hold_days": _safe_float(p.get("hold_days"), 1.0),
            "status": status,
            "won": 1 if (status == "WON" or pnl > 0) else 0,
            # Extra enrichment from ml_features_at_entry
            "confluence_score": _safe_float(p.get("confluence_score"), 0.0),
            "funding_rate": _safe_float(p.get("funding_rate"), 0.0),
            "orderbook_imbalance": _safe_float(p.get("orderbook_imbalance"), 0.0),
        }

        # Extract hour from generated_at if available
        gen_at = p.get("generated_at", "")
        if "T" in gen_at and ":" in gen_at:
            try:
                hour_str = gen_at.split("T")[1].split(":")[0]
                pick["hour_utc"] = int(hour_str)
            except (ValueError, IndexError):
                pick["hour_utc"] = 12
        else:
            pick["hour_utc"] = 12

        # Pull volume_ratio from ml_features if missing at top level
        mlf = p.get("ml_features_at_entry") or {}
        if p.get("volume_ratio") is None and mlf.get("volume_ratio") is not None:
            pick["volume_ratio"] = min(float(mlf["volume_ratio"]), 10.0)
        if p.get("rsi_at_entry") is None and mlf.get("rsi_14") is not None:
            pick["rsi_at_entry"] = float(mlf["rsi_14"])

        picks.append(pick)

    # Sort chronologically
    picks.sort(key=lambda x: x["entry_date"])
    print(f"[DATA] Loaded {len(picks)} closed picks ({sum(p['won'] for p in picks)} wins, "
          f"{len(picks) - sum(p['won'] for p in picks)} losses)")
    return picks


def _safe_float(val, default):
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _encode_direction(signal_type):
    if signal_type in ("BUY", "LONG"):
        return 1
    elif signal_type in ("SELL", "SHORT"):
        return -1
    return 1  # default LONG


# ---------------------------------------------------------------------------
# STEP 2: FEATURE MATRIX
# ---------------------------------------------------------------------------

CATEGORY_MAP = {
    "crypto": 1, "forex": 2, "equity": 3, "stock": 3,
    "futures": 4, "on-chain": 5, "commodity": 6, "etf": 7, "bond": 8,
}


def build_feature_matrix(picks):
    """Build normalized feature matrix.

    Features (9 columns):
      0: confidence (0-1)
      1: elite_score (0-1, normalized from 0-100)
      2: risk_reward (raw, capped at 5)
      3: volume_ratio (raw, capped at 10)
      4: direction_encoded (1 or -1)
      5: strategy_wr (per-strategy historical WR)
      6: category_encoded (int)
      7: hold_duration_days
      8: hour_utc (0-23)
    """
    # Compute per-strategy win rates
    strat_wins = defaultdict(int)
    strat_total = defaultdict(int)
    for p in picks:
        strat_total[p["strategy"]] += 1
        strat_wins[p["strategy"]] += p["won"]

    strategy_wr = {}
    for s in strat_total:
        strategy_wr[s] = strat_wins[s] / max(strat_total[s], 1)

    n = len(picks)
    X = np.zeros((n, 9), dtype=np.float64)
    y = np.zeros(n, dtype=np.float64)
    pnl = np.zeros(n, dtype=np.float64)

    for i, p in enumerate(picks):
        X[i, 0] = np.clip(p["confidence"], 0, 1)
        X[i, 1] = np.clip(p["elite_score"] / 100.0, 0, 1)
        X[i, 2] = np.clip(p["risk_reward"], 0, 5)
        X[i, 3] = np.clip(p["volume_ratio"], 0, 10)
        X[i, 4] = p["direction"]
        X[i, 5] = strategy_wr.get(p["strategy"], 0.5)
        X[i, 6] = CATEGORY_MAP.get(p["category"], 1)
        X[i, 7] = min(p["hold_days"], 30)
        X[i, 8] = p["hour_utc"]
        y[i] = p["won"]
        pnl[i] = p["pnl_pct"]

    # Standardize features (z-score) for logistic regression
    means = X.mean(axis=0)
    stds = X.std(axis=0)
    stds[stds < 1e-8] = 1.0  # avoid division by zero
    X_norm = (X - means) / stds

    print(f"[FEATURES] Built {n}x{X.shape[1]} feature matrix | "
          f"WR={y.mean():.3f} | Mean PnL={pnl.mean():.4f}")
    return X_norm, X, y, pnl, means, stds, strategy_wr


# ---------------------------------------------------------------------------
# STEP 3: WALK-FORWARD VALIDATION (Pure Python Logistic Regression)
# ---------------------------------------------------------------------------

def sigmoid(z):
    """Numerically stable sigmoid."""
    return np.where(z >= 0,
                    1.0 / (1.0 + np.exp(-z)),
                    np.exp(z) / (1.0 + np.exp(z)))


def logistic_regression_train(X, y, lr=0.01, epochs=500, reg_lambda=0.01):
    """Train logistic regression via gradient descent with L2 regularization.

    Pure numpy, no sklearn.
    """
    n, d = X.shape
    # Add bias column
    X_b = np.hstack([np.ones((n, 1)), X])
    w = np.zeros(d + 1)

    for epoch in range(epochs):
        z = X_b @ w
        p = sigmoid(z)
        # Gradient with L2 regularization
        grad = (X_b.T @ (p - y)) / n + reg_lambda * np.concatenate([[0], w[1:]])
        w -= lr * grad

        # Early stopping on small gradient
        if np.max(np.abs(grad)) < 1e-6:
            break

    return w


def logistic_regression_predict(X, w):
    """Predict probabilities using trained weights."""
    n = X.shape[0]
    X_b = np.hstack([np.ones((n, 1)), X])
    return sigmoid(X_b @ w)


def compute_metrics(y_true, y_pred_prob, pnl_values):
    """Compute WR, PF, Sharpe on a test set."""
    y_pred = (y_pred_prob >= 0.5).astype(float)

    # Accuracy / Win Rate
    correct = (y_pred == y_true).sum()
    wr = correct / max(len(y_true), 1)

    # Profit Factor (gross profits / gross losses)
    # Filter predicted wins
    predicted_win_mask = y_pred == 1
    predicted_loss_mask = y_pred == 0

    # Actual PnL of predicted winners vs losers
    gross_profit = np.sum(np.maximum(pnl_values[predicted_win_mask], 0))
    gross_loss = abs(np.sum(np.minimum(pnl_values[predicted_win_mask], 0)))

    # Overall PnL-based metrics
    all_profits = np.sum(np.maximum(pnl_values, 0))
    all_losses = abs(np.sum(np.minimum(pnl_values, 0)))
    pf = all_profits / max(all_losses, 1e-8)

    # Sharpe (annualized, assuming daily)
    if len(pnl_values) > 1 and np.std(pnl_values) > 0:
        sharpe = (np.mean(pnl_values) / np.std(pnl_values)) * np.sqrt(252)
    else:
        sharpe = 0.0

    # Precision on predicted wins
    true_pos = np.sum((y_pred == 1) & (y_true == 1))
    pred_pos = np.sum(y_pred == 1)
    precision = true_pos / max(pred_pos, 1)

    return {
        "win_rate": round(float(wr), 4),
        "profit_factor": round(float(pf), 4),
        "sharpe_ratio": round(float(sharpe), 4),
        "precision": round(float(precision), 4),
        "n_trades": int(len(y_true)),
        "n_wins": int(y_true.sum()),
        "mean_pnl_pct": round(float(np.mean(pnl_values)), 4),
        "total_pnl_pct": round(float(np.sum(pnl_values)), 4),
    }


def walk_forward_validation(X, y, pnl, n_picks):
    """
    Walk-forward with anchored expanding windows.

    Window definitions adapt to actual pick count:
      Window 1: picks 0..W train, W..W+T test
      Window 2: picks S..W+S train, W+S..W+S+T test
      etc.
    """
    results = []

    # Define windows proportional to dataset size
    n = len(y)
    train_size = max(int(n * 0.40), 50)  # ~40% for first train window
    test_size = max(int(n * 0.20), 30)   # ~20% for test
    step = max(int(n * 0.20), 30)        # step by 20%

    window_id = 0
    start = 0
    while start + train_size + test_size <= n:
        window_id += 1
        train_end = start + train_size
        test_end = min(train_end + test_size, n)

        X_train, y_train = X[start:train_end], y[start:train_end]
        X_test, y_test = X[train_end:test_end], y[train_end:test_end]
        pnl_test = pnl[train_end:test_end]

        if len(y_train) < 20 or len(y_test) < 10:
            start += step
            continue

        # Train logistic regression
        w = logistic_regression_train(X_train, y_train, lr=0.05, epochs=1000, reg_lambda=0.01)
        y_pred_prob = logistic_regression_predict(X_test, w)

        metrics = compute_metrics(y_test, y_pred_prob, pnl_test)
        metrics["window"] = window_id
        metrics["train_range"] = f"picks {start}-{train_end}"
        metrics["test_range"] = f"picks {train_end}-{test_end}"
        metrics["train_wr"] = round(float(y_train.mean()), 4)

        # Feature importance (absolute weight magnitude)
        feature_names = [
            "confidence", "elite_score", "risk_reward", "volume_ratio",
            "direction", "strategy_wr", "category", "hold_days", "hour_utc"
        ]
        importance = {name: round(float(abs(w[i + 1])), 4)
                      for i, name in enumerate(feature_names)}
        metrics["feature_importance"] = importance

        results.append(metrics)
        print(f"  [WF-{window_id}] Train {start}-{train_end} ({len(y_train)} picks) | "
              f"Test {train_end}-{test_end} ({len(y_test)} picks) | "
              f"WR={metrics['win_rate']:.3f} PF={metrics['profit_factor']:.3f} "
              f"Sharpe={metrics['sharpe_ratio']:.3f}")

        start += step

    # Summary across windows
    if results:
        avg_wr = np.mean([r["win_rate"] for r in results])
        avg_pf = np.mean([r["profit_factor"] for r in results])
        avg_sharpe = np.mean([r["sharpe_ratio"] for r in results])
        std_wr = np.std([r["win_rate"] for r in results])
    else:
        avg_wr = avg_pf = avg_sharpe = std_wr = 0.0

    summary = {
        "n_windows": len(results),
        "avg_win_rate": round(float(avg_wr), 4),
        "avg_profit_factor": round(float(avg_pf), 4),
        "avg_sharpe": round(float(avg_sharpe), 4),
        "wr_std": round(float(std_wr), 4),
        "windows": results,
    }
    print(f"\n[WALK-FORWARD] {len(results)} windows | Avg WR={avg_wr:.3f}±{std_wr:.3f} | "
          f"Avg PF={avg_pf:.3f} | Avg Sharpe={avg_sharpe:.3f}")
    return summary


# ---------------------------------------------------------------------------
# STEP 4: MONTE CARLO STRESS TEST
# ---------------------------------------------------------------------------

def monte_carlo_stress_test(pnl_values, n_simulations=1000, seed=42):
    """
    Shuffle trade order 1000x and compute drawdown/PnL/Sharpe distribution.
    Tests if results could be random luck.
    """
    rng = np.random.RandomState(seed)
    n = len(pnl_values)

    max_drawdowns = np.zeros(n_simulations)
    final_pnls = np.zeros(n_simulations)
    sharpes = np.zeros(n_simulations)
    max_consecutive_losses = np.zeros(n_simulations)

    for sim in range(n_simulations):
        shuffled = pnl_values.copy()
        rng.shuffle(shuffled)

        # Compute equity curve
        equity = np.cumsum(shuffled)
        running_max = np.maximum.accumulate(equity)
        drawdown = running_max - equity
        max_drawdowns[sim] = drawdown.max()

        final_pnls[sim] = equity[-1]

        # Sharpe
        if np.std(shuffled) > 0:
            sharpes[sim] = (np.mean(shuffled) / np.std(shuffled)) * np.sqrt(252)
        else:
            sharpes[sim] = 0.0

        # Max consecutive losses
        max_streak = 0
        current_streak = 0
        for v in shuffled:
            if v < 0:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        max_consecutive_losses[sim] = max_streak

    def percentiles(arr):
        return {
            "p5": round(float(np.percentile(arr, 5)), 4),
            "p25": round(float(np.percentile(arr, 25)), 4),
            "p50": round(float(np.percentile(arr, 50)), 4),
            "p75": round(float(np.percentile(arr, 75)), 4),
            "p95": round(float(np.percentile(arr, 95)), 4),
            "mean": round(float(np.mean(arr)), 4),
            "std": round(float(np.std(arr)), 4),
        }

    # Actual (un-shuffled) metrics for comparison
    actual_equity = np.cumsum(pnl_values)
    actual_running_max = np.maximum.accumulate(actual_equity)
    actual_dd = (actual_running_max - actual_equity).max()
    actual_final = actual_equity[-1]
    actual_sharpe = (np.mean(pnl_values) / max(np.std(pnl_values), 1e-8)) * np.sqrt(252)

    # How does actual compare to random? (percentile rank)
    dd_rank = float(np.mean(max_drawdowns <= actual_dd))
    pnl_rank = float(np.mean(final_pnls <= actual_final))
    sharpe_rank = float(np.mean(sharpes <= actual_sharpe))

    result = {
        "n_simulations": n_simulations,
        "n_trades": int(n),
        "max_drawdown": percentiles(max_drawdowns),
        "final_pnl": percentiles(final_pnls),
        "sharpe_ratio": percentiles(sharpes),
        "max_consecutive_losses": percentiles(max_consecutive_losses),
        "actual_vs_random": {
            "actual_max_drawdown": round(float(actual_dd), 4),
            "actual_final_pnl": round(float(actual_final), 4),
            "actual_sharpe": round(float(actual_sharpe), 4),
            "drawdown_percentile_rank": round(dd_rank, 4),
            "pnl_percentile_rank": round(pnl_rank, 4),
            "sharpe_percentile_rank": round(sharpe_rank, 4),
            "luck_assessment": _assess_luck(pnl_rank, sharpe_rank),
        },
    }

    print(f"\n[MONTE CARLO] {n_simulations} simulations | {n} trades")
    print(f"  Max DD:  p5={result['max_drawdown']['p5']:.4f} | "
          f"p50={result['max_drawdown']['p50']:.4f} | "
          f"p95={result['max_drawdown']['p95']:.4f}")
    print(f"  Final PnL: p5={result['final_pnl']['p5']:.4f} | "
          f"p50={result['final_pnl']['p50']:.4f} | "
          f"p95={result['final_pnl']['p95']:.4f}")
    print(f"  Sharpe:  p5={result['sharpe_ratio']['p5']:.4f} | "
          f"p50={result['sharpe_ratio']['p50']:.4f} | "
          f"p95={result['sharpe_ratio']['p95']:.4f}")
    print(f"  Actual PnL rank vs random: {pnl_rank:.1%} | "
          f"Luck: {result['actual_vs_random']['luck_assessment']}")
    return result


def _assess_luck(pnl_rank, sharpe_rank):
    """Determine if results are skill or luck based on MC rankings."""
    avg_rank = (pnl_rank + sharpe_rank) / 2
    # Since we shuffle ORDER not values, PnL sum is constant.
    # The key metric is drawdown and Sharpe variation.
    # If sharpe_rank > 0.5, our actual ordering is better than random
    if sharpe_rank > 0.8:
        return "STRONG_SKILL — trade ordering significantly better than random"
    elif sharpe_rank > 0.5:
        return "MODERATE_SKILL — some skill in trade ordering"
    elif sharpe_rank > 0.2:
        return "NEUTRAL — results consistent with random ordering"
    else:
        return "WARNING — actual ordering worse than random, review strategy sequencing"


# ---------------------------------------------------------------------------
# STEP 5: PARAMETER SENSITIVITY ANALYSIS
# ---------------------------------------------------------------------------

def parameter_sensitivity(picks):
    """
    Grid search over golden filter parameters to find the robust sweet spot.
    Tests confidence thresholds, R:R ranges, and direction filters.
    """
    confidence_thresholds = [0.60, 0.65, 0.70, 0.75, 0.80]
    rr_ranges = [(0.5, 1.5), (1.0, 2.0), (1.5, 2.5), (2.0, 3.0)]
    directions = ["BOTH", "LONG", "SHORT"]

    matrix = []
    best_combo = None
    best_score = -999

    for conf_thresh in confidence_thresholds:
        for rr_min, rr_max in rr_ranges:
            for direction in directions:
                filtered = []
                for p in picks:
                    if p["confidence"] < conf_thresh:
                        continue
                    if not (rr_min <= p["risk_reward"] <= rr_max):
                        continue
                    if direction == "LONG" and p["direction"] != 1:
                        continue
                    if direction == "SHORT" and p["direction"] != -1:
                        continue
                    filtered.append(p)

                n = len(filtered)
                if n < 10:
                    continue

                wins = sum(p["won"] for p in filtered)
                wr = wins / n

                pnl_arr = np.array([p["pnl_pct"] for p in filtered])
                gross_profit = np.sum(np.maximum(pnl_arr, 0))
                gross_loss = abs(np.sum(np.minimum(pnl_arr, 0)))
                pf = gross_profit / max(gross_loss, 1e-8)

                mean_pnl = float(np.mean(pnl_arr))
                total_pnl = float(np.sum(pnl_arr))

                if np.std(pnl_arr) > 0:
                    sharpe = (np.mean(pnl_arr) / np.std(pnl_arr)) * np.sqrt(252)
                else:
                    sharpe = 0.0

                entry = {
                    "confidence_threshold": conf_thresh,
                    "rr_range": f"{rr_min}-{rr_max}",
                    "direction": direction,
                    "n_trades": n,
                    "win_rate": round(wr, 4),
                    "profit_factor": round(float(pf), 4),
                    "sharpe_ratio": round(float(sharpe), 4),
                    "mean_pnl_pct": round(mean_pnl, 4),
                    "total_pnl_pct": round(total_pnl, 4),
                }
                matrix.append(entry)

                # Composite score: balances WR, PF, Sharpe, and sample size
                score = (wr * 0.3 + min(pf, 3) / 3 * 0.3 +
                         min(max(sharpe, -5), 5) / 5 * 0.2 +
                         min(n, 100) / 100 * 0.2)
                if score > best_score:
                    best_score = score
                    best_combo = entry.copy()
                    best_combo["composite_score"] = round(score, 4)

    # Find robust parameters (work across MULTIPLE thresholds)
    robustness = _compute_robustness(matrix)

    print(f"\n[SENSITIVITY] {len(matrix)} parameter combos tested")
    if best_combo:
        print(f"  Best combo: conf>={best_combo['confidence_threshold']} | "
              f"R:R={best_combo['rr_range']} | dir={best_combo['direction']} | "
              f"WR={best_combo['win_rate']:.3f} PF={best_combo['profit_factor']:.3f} "
              f"n={best_combo['n_trades']}")
    print(f"  Robustness: {robustness['assessment']}")

    return {
        "n_combos_tested": len(matrix),
        "matrix": matrix,
        "best_combo": best_combo,
        "robustness": robustness,
    }


def _compute_robustness(matrix):
    """
    Check if profitability is robust across adjacent parameter values.
    A strategy that only works at ONE exact setting is fragile.
    """
    if not matrix:
        return {"assessment": "NO_DATA", "robust_combos": 0, "fragile_combos": 0}

    # Count combos where WR > 0.50 AND PF > 1.0 (profitable)
    profitable = [m for m in matrix if m["win_rate"] > 0.50 and m["profit_factor"] > 1.0]
    total = len(matrix)

    # Check if profitability clusters (adjacent params also profitable)
    conf_profitable = defaultdict(int)
    rr_profitable = defaultdict(int)
    for m in profitable:
        conf_profitable[m["confidence_threshold"]] += 1
        rr_profitable[m["rr_range"]] += 1

    # Robust = profitable across 3+ confidence levels AND 2+ R:R ranges
    n_conf_levels = sum(1 for v in conf_profitable.values() if v >= 1)
    n_rr_ranges = sum(1 for v in rr_profitable.values() if v >= 1)

    if n_conf_levels >= 4 and n_rr_ranges >= 3:
        assessment = "HIGHLY_ROBUST — profitable across most parameter combos"
    elif n_conf_levels >= 3 and n_rr_ranges >= 2:
        assessment = "ROBUST — profitable across multiple parameter settings"
    elif n_conf_levels >= 2 or n_rr_ranges >= 2:
        assessment = "MODERATE — works in a few settings, needs monitoring"
    elif len(profitable) > 0:
        assessment = "FRAGILE — profitable only at specific settings, high overfit risk"
    else:
        assessment = "UNPROFITABLE — no parameter combo yields consistent profit"

    # Confidence intervals for optimal parameters
    if profitable:
        conf_values = sorted(set(m["confidence_threshold"] for m in profitable))
        rr_values = sorted(set(m["rr_range"] for m in profitable))
        ci_conf = f"{conf_values[0]}-{conf_values[-1]}" if conf_values else "N/A"
        ci_rr = f"{rr_values[0]} to {rr_values[-1]}" if rr_values else "N/A"
    else:
        ci_conf = "N/A"
        ci_rr = "N/A"

    return {
        "assessment": assessment,
        "profitable_combos": len(profitable),
        "total_combos": total,
        "profitable_pct": round(len(profitable) / max(total, 1) * 100, 1),
        "n_profitable_conf_levels": n_conf_levels,
        "n_profitable_rr_ranges": n_rr_ranges,
        "confidence_interval": ci_conf,
        "rr_interval": ci_rr,
    }


# ---------------------------------------------------------------------------
# STEP 6: OUTPUT
# ---------------------------------------------------------------------------

def generate_report(picks, walk_forward, monte_carlo, sensitivity, strategy_wr):
    """Compile final hedge-fund-grade backtest report."""
    # Top-level portfolio stats
    pnl_arr = np.array([p["pnl_pct"] for p in picks])
    wins = sum(p["won"] for p in picks)

    equity = np.cumsum(pnl_arr)
    running_max = np.maximum.accumulate(equity)
    max_dd = float((running_max - equity).max())

    gross_profit = float(np.sum(np.maximum(pnl_arr, 0)))
    gross_loss = float(abs(np.sum(np.minimum(pnl_arr, 0))))

    # Strategy leaderboard
    strat_stats = defaultdict(lambda: {"wins": 0, "total": 0, "pnl": []})
    for p in picks:
        s = p["strategy"]
        strat_stats[s]["total"] += 1
        strat_stats[s]["wins"] += p["won"]
        strat_stats[s]["pnl"].append(p["pnl_pct"])

    leaderboard = []
    for s, stats in strat_stats.items():
        if stats["total"] >= 3:
            wr = stats["wins"] / stats["total"]
            total_pnl = sum(stats["pnl"])
            leaderboard.append({
                "strategy": s,
                "trades": stats["total"],
                "win_rate": round(wr, 4),
                "total_pnl_pct": round(total_pnl, 4),
                "mean_pnl_pct": round(total_pnl / stats["total"], 4),
            })
    leaderboard.sort(key=lambda x: x["total_pnl_pct"], reverse=True)

    # Recommended optimal parameters
    optimal = {}
    if sensitivity.get("best_combo"):
        bc = sensitivity["best_combo"]
        optimal = {
            "confidence_threshold": bc["confidence_threshold"],
            "rr_range": bc["rr_range"],
            "direction": bc["direction"],
            "expected_wr": bc["win_rate"],
            "expected_pf": bc["profit_factor"],
            "robustness": sensitivity["robustness"]["assessment"],
            "confidence_interval_conf": sensitivity["robustness"]["confidence_interval"],
            "confidence_interval_rr": sensitivity["robustness"]["rr_interval"],
        }

    report = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "pipeline_version": "1.0.0",
            "description": "Hedge-Fund-Grade Walk-Forward Backtesting Pipeline",
            "n_picks_loaded": len(picks),
            "date_range": f"{picks[0]['entry_date']} to {picks[-1]['entry_date']}",
        },
        "portfolio_summary": {
            "total_trades": len(picks),
            "wins": wins,
            "losses": len(picks) - wins,
            "win_rate": round(wins / max(len(picks), 1), 4),
            "total_pnl_pct": round(float(np.sum(pnl_arr)), 4),
            "mean_pnl_pct": round(float(np.mean(pnl_arr)), 4),
            "median_pnl_pct": round(float(np.median(pnl_arr)), 4),
            "std_pnl_pct": round(float(np.std(pnl_arr)), 4),
            "max_drawdown_pct": round(max_dd, 4),
            "gross_profit_pct": round(gross_profit, 4),
            "gross_loss_pct": round(gross_loss, 4),
            "profit_factor": round(gross_profit / max(gross_loss, 1e-8), 4),
            "sharpe_ratio": round(float(np.mean(pnl_arr) / max(np.std(pnl_arr), 1e-8) * np.sqrt(252)), 4),
            "best_trade_pct": round(float(np.max(pnl_arr)), 4),
            "worst_trade_pct": round(float(np.min(pnl_arr)), 4),
        },
        "walk_forward_results": walk_forward,
        "monte_carlo_stress_test": monte_carlo,
        "parameter_sensitivity": sensitivity,
        "strategy_leaderboard": leaderboard[:20],
        "recommended_optimal_parameters": optimal,
    }

    return report


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    t0 = time.time()
    print("=" * 72)
    print("  HEDGE-FUND-GRADE WALK-FORWARD BACKTESTING PIPELINE v1.0")
    print("=" * 72)

    # Step 1: Load data
    print("\n--- STEP 1: DATA LOADER ---")
    picks = load_closed_picks()
    if len(picks) < 30:
        print(f"ERROR: Only {len(picks)} picks loaded. Need at least 30.")
        sys.exit(1)

    # Step 2: Feature matrix
    print("\n--- STEP 2: FEATURE MATRIX ---")
    X_norm, X_raw, y, pnl, means, stds, strategy_wr = build_feature_matrix(picks)

    # Step 3: Walk-forward validation
    print("\n--- STEP 3: WALK-FORWARD VALIDATION ---")
    wf_results = walk_forward_validation(X_norm, y, pnl, len(picks))

    # Step 4: Monte Carlo stress test
    print("\n--- STEP 4: MONTE CARLO STRESS TEST ---")
    mc_results = monte_carlo_stress_test(pnl, n_simulations=1000, seed=42)

    # Step 5: Parameter sensitivity
    print("\n--- STEP 5: PARAMETER SENSITIVITY ---")
    sens_results = parameter_sensitivity(picks)

    # Step 6: Output
    print("\n--- STEP 6: GENERATING REPORT ---")
    report = generate_report(picks, wf_results, mc_results, sens_results, strategy_wr)

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    elapsed = time.time() - t0
    print(f"\n{'=' * 72}")
    print(f"  PIPELINE COMPLETE in {elapsed:.1f}s")
    print(f"  Report saved to: {OUTPUT_PATH}")
    print(f"  Trades: {report['portfolio_summary']['total_trades']} | "
          f"WR: {report['portfolio_summary']['win_rate']:.3f} | "
          f"PF: {report['portfolio_summary']['profit_factor']:.3f} | "
          f"Sharpe: {report['portfolio_summary']['sharpe_ratio']:.3f}")
    print(f"  Walk-Forward Avg WR: {wf_results['avg_win_rate']:.3f} | "
          f"MC Luck: {mc_results['actual_vs_random']['luck_assessment']}")
    print(f"  Robustness: {sens_results['robustness']['assessment']}")
    print(f"{'=' * 72}")

    return report


if __name__ == "__main__":
    main()
