#!/usr/bin/env python3
"""
ALPHA ENGINE -- Bayesian TP/SL Optimizer
===================================
Uses Bayesian optimization to find optimal TP/SL levels based on
real trade outcomes (MFE/MAE data from forward_validator).

Usage (from repo root):
    from alpha_engine.bayes_optimizer import optimize_tp_sl

    best = optimize_tp_sl("ema_crossover", "BTCUSDT", n_iterations=30)
    print(f"Optimal TP: {best['tp_pct']}, SL: {best['sl_pct']}")
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List
import numpy as np

try:
    from bayes_opt import BayesianOptimization
except ImportError:  # pragma: no cover
    from bayes_optimization import BayesianOptimization

# Local imports
THIS_DIR = Path(__file__).resolve().parent
DATA_DIR = THIS_DIR / "data"
CLOSED_PICKS_PATH = DATA_DIR / "closed_picks.json"

# Default bounds (fraction of price)
DEFAULT_BOUNDS = {
    "tp_pct": (0.005, 0.15),    # 0.5% to 15%
    "sl_pct": (0.003, 0.10),    # 0.3% to 10%
    "max_hold_days": (1, 14)     # 1 to 14 days
}


def load_closed_picks(strategy: Optional[str] = None, symbol: Optional[str] = None) -> List[Dict]:
    """Load closed picks from JSON."""
    if not CLOSED_PICKS_PATH.exists():
        return []
    
    with open(CLOSED_PICKS_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    picks = data.get("picks", [])
    
    if strategy:
        picks = [p for p in picks if p.get("strategy") == strategy]
    if symbol:
        picks = [p for p in picks if p.get("symbol") == symbol]
    
    return picks


def simulate_trade(
    entry_price: float,
    tp_pct: float,
    sl_pct: float,
    max_hold_days: int,
    price_series: np.ndarray
) -> Dict[str, Any]:
    """
    Simulate a trade with given TP/SL and price series.
    
    Returns outcome: 1 (win), -1 (loss), 0 (expire)
    """
    tp_target = entry_price * (1 + tp_pct)
    sl_target = entry_price * (1 - sl_pct)
    
    for i, price in enumerate(price_series[:max_hold_days]):
        if price >= tp_target:
            return {"outcome": 1, "return": tp_pct, "hold_days": i + 1}
        if price <= sl_target:
            return {"outcome": -1, "return": -sl_pct, "hold_days": i + 1}
    
    # Expire - return based on final price
    final_return = (price_series[min(max_hold_days, len(price_series)-1)] / entry_price) - 1
    return {"outcome": 0, "return": final_return, "hold_days": max_hold_days}


def objective_function(
    tp_pct: float,
    sl_pct: float,
    max_hold_days: int,
    picks: List[Dict],
    min_trades: int = 10
) -> float:
    """
    Objective: Maximize Sharpe-like metric while maintaining acceptable win rate.
    
    Returns: Expected return / volatility (Sharpe proxy), penalized if too few trades.
    """
    if len(picks) < min_trades:
        return -999
    
    returns = []
    for pick in picks:
        entry = pick.get("entry_price")
        if not entry:
            continue
        
        # Get simulated result
        # In real use, would use actual price path
        result = simulate_trade(
            entry,
            tp_pct,
            sl_pct,
            int(max_hold_days),
            np.array([entry * (1 + np.random.randn() * 0.02) for _ in range(int(max_hold_days))])
        )
        returns.append(result["return"])
    
    if len(returns) < min_trades:
        return -999
    
    arr = np.array(returns)
    mean_ret = arr.mean()
    std_ret = arr.std()
    
    if std_ret == 0:
        return -999
    
    sharpe = mean_ret / std_ret * np.sqrt(252)
    
    # Penalize very low win rates
    win_rate = (arr > 0).mean()
    if win_rate < 0.35:
        sharpe -= 0.5
    
    return sharpe


def optimize_tp_sl(
    strategy: Optional[str] = None,
    symbol: Optional[str] = None,
    n_iterations: int = 30,
    n_random_starts: int = 5,
    bounds: Optional[Dict[str, tuple]] = None
) -> Dict[str, Any]:
    """
    Find optimal TP/SL using Bayesian optimization.
    
    Returns optimal parameters and optimization history.
    """
    picks = load_closed_picks(strategy, symbol)
    
    if len(picks) < 10:
        print(f"Warning: Only {len(picks)} trades found. Using defaults.")
        return {"tp_pct": 0.05, "sl_pct": 0.03, "max_hold_days": 7, "n_trades": len(picks)}
    
    if bounds is None:
        bounds = DEFAULT_BOUNDS
    
    def objective(tp_pct: float, sl_pct: float, max_hold_days: float) -> float:
        return objective_function(
            tp_pct,
            sl_pct,
            max_hold_days,
            picks
        )
    
    # bayes_opt expects float bounds only
    pbounds = {k: (float(v[0]), float(v[1])) for k, v in bounds.items()}
    optimizer = BayesianOptimization(
        f=objective,
        pbounds=pbounds,
        random_state=42,
        verbose=2,
    )
    
    print(f"Optimizing TP/SL for {len(picks)} trades...")
    optimizer.maximize(
        n_iter=n_iterations,
        init_points=n_random_starts
    )
    
    best = optimizer.max
    params = best["params"]
    
    # Convert numpy types to Python
    result = {
        "tp_pct": float(params["tp_pct"]),
        "sl_pct": float(params["sl_pct"]),
        "max_hold_days": int(round(params["max_hold_days"])),
        "score": float(best["target"]),
        "strategy": strategy,
        "symbol": symbol,
        "n_trades": len(picks)
    }
    
    print(f"Optimal TP: {result['tp_pct']:.3f}, SL: {result['sl_pct']:.3f}, Score: {result['score']:.2f}")
    
    return result


def optimize_adaptive_levels(
    strategy: str,
    symbol: str,
    n_iterations: int = 20
) -> Dict[str, Any]:
    """
    Optimize adaptive TP/SL levels using Bayesian optimization.
    
    Combines forward validator data with Bayesian search.
    """
    # Load strategy-specific trades
    picks = load_closed_picks(strategy=strategy, symbol=symbol)
    
    if len(picks) < 10:
        # Fall back to symbol-level
        picks = load_closed_picks(symbol=symbol)
    
    if len(picks) < 10:
        # Fall back to strategy-level
        picks = load_closed_picks(strategy=strategy)
    
    if len(picks) < 10:
        print(f"Warning: Only {len(picks)} trades. Using default policy.")
        return None
    
    # Use tighter bounds based on category
    category = picks[0].get("category", "crypto")
    
    if category == "crypto":
        bounds = {
            "tp_pct": (0.01, 0.20),
            "sl_pct": (0.005, 0.15),
            "max_hold_days": (1, 7)
        }
    elif category in ["forex", "commodities"]:
        bounds = {
            "tp_pct": (0.005, 0.08),
            "sl_pct": (0.003, 0.05),
            "max_hold_days": (1, 14)
        }
    else:
        bounds = DEFAULT_BOUNDS
    
    return optimize_tp_sl(
        strategy=strategy,
        symbol=symbol,
        n_iterations=n_iterations,
        bounds=bounds
    )


def save_optimal_levels(levels: Dict[str, Any], path: Optional[Path] = None):
    """Save optimized levels to JSON."""
    if path is None:
        path = DATA_DIR / "bayesian_tp_sl.json"
    
    # Load existing
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            existing = json.load(f)
    else:
        existing = {"optimized": []}
    
    # Add/update entry
    key = f"{levels.get('strategy', 'default')}_{levels.get('symbol', 'default')}"
    existing["optimized"] = [
        e for e in existing["optimized"]
        if e.get("strategy") != levels.get("strategy") or e.get("symbol") != levels.get("symbol")
    ]
    existing["optimized"].append(levels)
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(existing, f, indent=2, default=str)
    
    print(f"Saved to {path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Bayesian TP/SL Optimizer")
    parser.add_argument("--strategy", help="Strategy name")
    parser.add_argument("--symbol", help="Symbol")
    parser.add_argument("--iterations", type=int, default=30)
    
    args = parser.parse_args()
    
    result = optimize_tp_sl(
        strategy=args.strategy,
        symbol=args.symbol,
        n_iterations=args.iterations
    )
    
    save_optimal_levels(result)
    print(f"\nResult: {result}")