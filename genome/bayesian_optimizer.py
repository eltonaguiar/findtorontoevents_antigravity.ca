"""
Bayesian Strategy Optimizer
============================
Replaces random mutation with intelligent hyperparameter search.
Uses Tree-Parzen Estimator (TPE) inspired approach for efficiency
without requiring heavy dependencies like optuna.

Research basis:
- Parameter stability > parameter optimality (avoid overfitting)
- Walk-forward validation mandatory
- Optimize Sharpe, not win rate (Zarattini et al., 2025)
"""

import json
import logging
import math
import random
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Callable
from pathlib import Path

logger = logging.getLogger("BayesianOptimizer")

@dataclass
class ParameterSpace:
    """Defines the search space for a strategy parameter."""
    name: str
    low: float
    high: float
    param_type: str = "float"  # float, int, choice
    choices: List = field(default_factory=list)
    log_scale: bool = False  # Search in log space

@dataclass
class TrialResult:
    """Result of a single optimization trial."""
    params: Dict
    sharpe: float
    win_rate: float
    profit_factor: float
    max_drawdown: float
    total_trades: int
    score: float  # Combined objective

class BayesianOptimizer:
    """TPE-inspired Bayesian optimizer for strategy parameters."""

    def __init__(self, param_space: List[ParameterSpace], seed: int = 42):
        self.param_space = param_space
        self.trials: List[TrialResult] = []
        self.rng = random.Random(seed)
        self.np_rng = np.random.RandomState(seed)

    def _sample_random(self) -> Dict:
        """Sample random point from parameter space (exploration)."""
        params = {}
        for p in self.param_space:
            if p.param_type == "choice":
                params[p.name] = self.rng.choice(p.choices)
            elif p.param_type == "int":
                params[p.name] = self.rng.randint(int(p.low), int(p.high))
            elif p.log_scale:
                log_val = self.rng.uniform(math.log(p.low), math.log(p.high))
                params[p.name] = math.exp(log_val)
            else:
                params[p.name] = self.rng.uniform(p.low, p.high)
        return params

    def _sample_tpe(self, gamma: float = 0.25) -> Dict:
        """Sample using TPE (Tree-Parzen Estimator) approach.
        Split trials into good/bad, sample from good distribution."""
        if len(self.trials) < 10:
            return self._sample_random()

        # Sort by score, split into good (top gamma%) and bad
        sorted_trials = sorted(self.trials, key=lambda t: t.score, reverse=True)
        n_good = max(1, int(len(sorted_trials) * gamma))
        good_trials = sorted_trials[:n_good]

        params = {}
        for p in self.param_space:
            good_values = [t.params[p.name] for t in good_trials if p.name in t.params]

            if not good_values or p.param_type == "choice":
                params[p.name] = self.rng.choice(p.choices) if p.param_type == "choice" else self._sample_random()[p.name]
                continue

            # Sample from KDE of good values with noise
            base = self.rng.choice(good_values)
            spread = (p.high - p.low) * 0.1  # 10% of range as bandwidth
            sampled = base + self.np_rng.normal(0, spread)
            sampled = max(p.low, min(p.high, sampled))

            if p.param_type == "int":
                sampled = int(round(sampled))

            params[p.name] = sampled

        return params

    def suggest(self) -> Dict:
        """Suggest next parameter set to evaluate."""
        if len(self.trials) < 5:
            return self._sample_random()
        return self._sample_tpe()

    def tell(self, params: Dict, sharpe: float, win_rate: float,
             profit_factor: float, max_drawdown: float, total_trades: int):
        """Record trial result."""
        # Combined objective: weighted score
        # Heavily penalize low trade count (unreliable)
        trade_penalty = min(1.0, total_trades / 20)
        # Penalize extreme drawdown
        dd_penalty = max(0, 1.0 - max_drawdown / 30)
        # Score = Sharpe * trade_reliability * drawdown_safety
        score = sharpe * trade_penalty * dd_penalty

        trial = TrialResult(
            params=params, sharpe=sharpe, win_rate=win_rate,
            profit_factor=profit_factor, max_drawdown=max_drawdown,
            total_trades=total_trades, score=score
        )
        self.trials.append(trial)
        logger.info(f"Trial {len(self.trials)}: score={score:.4f} sharpe={sharpe:.2f} "
                     f"WR={win_rate:.1%} trades={total_trades}")

    def best(self, n: int = 5) -> List[TrialResult]:
        """Return top N trials by score."""
        return sorted(self.trials, key=lambda t: t.score, reverse=True)[:n]

    def optimize(self, objective_fn: Callable, n_trials: int = 50,
                 early_stop_patience: int = 15) -> List[TrialResult]:
        """Run full optimization loop.

        Args:
            objective_fn: Function(params) -> dict with keys:
                sharpe, win_rate, profit_factor, max_drawdown, total_trades
            n_trials: Number of trials to run
            early_stop_patience: Stop if no improvement for N trials
        """
        best_score = -float('inf')
        patience_counter = 0

        for i in range(n_trials):
            params = self.suggest()
            try:
                result = objective_fn(params)
                self.tell(
                    params,
                    sharpe=result.get("sharpe", 0),
                    win_rate=result.get("win_rate", 0),
                    profit_factor=result.get("profit_factor", 0),
                    max_drawdown=result.get("max_drawdown", 0),
                    total_trades=result.get("total_trades", 0),
                )

                if self.trials[-1].score > best_score:
                    best_score = self.trials[-1].score
                    patience_counter = 0
                else:
                    patience_counter += 1

                if patience_counter >= early_stop_patience:
                    logger.info(f"Early stopping at trial {i+1} (no improvement for {early_stop_patience} trials)")
                    break

            except Exception as e:
                logger.warning(f"Trial {i+1} failed: {e}")
                continue

        return self.best()

    def to_dna_genes(self, params: Dict) -> Dict:
        """Convert optimized params back to StrategyDNA gene format."""
        genes = {}
        for p in self.param_space:
            if p.name in params:
                genes[p.name] = params[p.name]
        return genes

    def save_results(self, path: str):
        """Save optimization results to JSON."""
        results = {
            "total_trials": len(self.trials),
            "best_score": self.trials[0].score if self.trials else 0,
            "top_5": [
                {"params": t.params, "sharpe": t.sharpe, "win_rate": t.win_rate,
                 "profit_factor": t.profit_factor, "max_drawdown": t.max_drawdown,
                 "total_trades": t.total_trades, "score": t.score}
                for t in self.best(5)
            ],
            "all_trials": [
                {"score": t.score, "sharpe": t.sharpe, "win_rate": t.win_rate}
                for t in self.trials
            ]
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(results, f, indent=2)


# === PREDEFINED PARAMETER SPACES FOR COMMON STRATEGIES ===

def rsi_mean_reversion_space() -> List[ParameterSpace]:
    """Parameter space for RSI mean reversion strategies."""
    return [
        ParameterSpace("rsi_period", 2, 21, "int"),
        ParameterSpace("rsi_oversold", 5, 35, "int"),
        ParameterSpace("rsi_overbought", 65, 95, "int"),
        ParameterSpace("lookback_window", 10, 200, "int"),
        ParameterSpace("atr_period", 7, 21, "int"),
        ParameterSpace("stop_atr_mult", 1.0, 4.0, "float"),
        ParameterSpace("tp_atr_mult", 1.5, 6.0, "float"),
        ParameterSpace("risk_per_trade", 0.005, 0.03, "float"),
    ]

def trend_following_space() -> List[ParameterSpace]:
    """Parameter space for trend following strategies."""
    return [
        ParameterSpace("fast_ma", 5, 50, "int"),
        ParameterSpace("slow_ma", 20, 200, "int"),
        ParameterSpace("atr_period", 7, 21, "int"),
        ParameterSpace("breakout_period", 10, 55, "int"),
        ParameterSpace("vol_lookback", 10, 60, "int"),
        ParameterSpace("stop_atr_mult", 1.5, 5.0, "float"),
        ParameterSpace("tp_atr_mult", 2.0, 8.0, "float"),
        ParameterSpace("risk_per_trade", 0.005, 0.02, "float"),
        ParameterSpace("vol_scale_factor", 0.5, 2.0, "float"),
    ]

def funding_rate_space() -> List[ParameterSpace]:
    """Parameter space for funding rate carry strategies."""
    return [
        ParameterSpace("funding_threshold", 0.0001, 0.001, "float", log_scale=True),
        ParameterSpace("exit_threshold", 0.00005, 0.0005, "float", log_scale=True),
        ParameterSpace("max_hold_hours", 4, 72, "int"),
        ParameterSpace("min_volume_usd", 1e6, 1e8, "float", log_scale=True),
        ParameterSpace("risk_per_trade", 0.005, 0.02, "float"),
    ]

def volatility_breakout_space() -> List[ParameterSpace]:
    """Parameter space for volatility breakout (Keltner/Bollinger squeeze)."""
    return [
        ParameterSpace("squeeze_lookback", 10, 30, "int"),
        ParameterSpace("bb_period", 15, 30, "int"),
        ParameterSpace("bb_std", 1.5, 3.0, "float"),
        ParameterSpace("keltner_period", 15, 30, "int"),
        ParameterSpace("keltner_atr_mult", 1.0, 2.5, "float"),
        ParameterSpace("breakout_confirmation_bars", 1, 5, "int"),
        ParameterSpace("stop_atr_mult", 1.5, 4.0, "float"),
        ParameterSpace("tp_atr_mult", 2.0, 6.0, "float"),
        ParameterSpace("risk_per_trade", 0.005, 0.02, "float"),
    ]


# === CLI ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Demo: optimize RSI mean reversion
    space = rsi_mean_reversion_space()
    optimizer = BayesianOptimizer(space, seed=42)

    # Simulated objective (replace with real backtester)
    def mock_objective(params):
        rsi_p = params["rsi_period"]
        risk = params["risk_per_trade"]
        # Simulate: short RSI periods + moderate risk = better Sharpe
        sharpe = 2.0 * (1.0 / (rsi_p / 5)) * (1 - abs(risk - 0.015) * 50)
        sharpe += random.gauss(0, 0.3)
        wr = 0.55 + 0.1 * (1.0 / (rsi_p / 5)) + random.gauss(0, 0.05)
        return {
            "sharpe": max(0, sharpe),
            "win_rate": max(0.3, min(0.8, wr)),
            "profit_factor": max(0.5, sharpe * 0.8),
            "max_drawdown": max(2, 15 - sharpe * 2 + random.gauss(0, 3)),
            "total_trades": random.randint(15, 50),
        }

    results = optimizer.optimize(mock_objective, n_trials=30)

    print(f"\nTop 5 configurations:")
    for i, r in enumerate(results):
        print(f"  {i+1}. score={r.score:.4f} sharpe={r.sharpe:.2f} WR={r.win_rate:.1%} "
              f"DD={r.max_drawdown:.1f}% trades={r.total_trades}")
        print(f"     params: rsi_period={r.params['rsi_period']} "
              f"risk={r.params['risk_per_trade']:.3f} "
              f"stop={r.params['stop_atr_mult']:.1f}x "
              f"tp={r.params['tp_atr_mult']:.1f}x")

    optimizer.save_results("genome/results/bayesian_optimization_demo.json")
    print(f"\nSaved to genome/results/bayesian_optimization_demo.json")
