"""
Monte Carlo Validator per TESTING_PROTOCOL.MD §5
1000-sample bootstrap simulator computing:
- PPR (Probability of Ruin): P(peak-to-valley DD > capital)
- POR (Probability of Outperformance): P(return > threshold)
- P5/P50/P95: quantiles for PF, WR, Sharpe, MDD
Returns: PASS / PROBATION / FAIL classification + detailed metrics
"""
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple


@dataclass
class MonteCarloResult:
    status: str  # "PASS", "PROBATION", "FAIL"
    ppr: float  # Probability of Ruin
    por: float  # Probability of Outperformance
    metrics: Dict
    quantiles: Dict


def compute_drawdown(pnls: np.ndarray) -> np.ndarray:
    """Compute running maximum and drawdown from PnL series."""
    cum_pnl = np.cumsum(pnls)
    running_max = np.maximum.accumulate(cum_pnl)
    drawdown = (running_max - cum_pnl) / (np.abs(running_max) + 1e-9)
    return drawdown


def bootstrap_sample_trades(pnls: List[float], n_sims: int = 1000, horizon: int = 30) -> List[np.ndarray]:
    """
    Generate bootstrap samples of future trade sequences.
    Each sample = horizon trades randomly drawn from historical pnls (with replacement).
    """
    pnls = np.array(pnls)
    samples = []
    for _ in range(n_sims):
        sample = np.random.choice(pnls, size=horizon, replace=True)
        samples.append(sample)
    return samples


def compute_sample_metrics(sample: np.ndarray) -> Dict:
    """Compute metrics for a single bootstrap sample."""
    pnls = sample
    trades_positive = np.sum(pnls > 0)
    win_rate = trades_positive / len(pnls) if len(pnls) > 0 else 0
    
    gross_profit = np.sum(pnls[pnls > 0]) if np.any(pnls > 0) else 0
    gross_loss = np.abs(np.sum(pnls[pnls < 0])) if np.any(pnls < 0) else 0
    profit_factor = gross_profit / (gross_loss + 1e-9)
    
    total_return = np.sum(pnls)
    volatility = np.std(pnls) if len(pnls) > 1 else 0
    sharpe = (total_return / len(pnls)) / (volatility + 1e-9) if volatility > 0 else 0
    
    drawdown = compute_drawdown(pnls)
    max_dd = np.max(drawdown) if len(drawdown) > 0 else 0
    
    return {
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "total_return": total_return,
    }


def monte_carlo_validate(
    pnls: List[float],
    trade_count: int,
    win_rate: float,
    profit_factor: float,
    n_sims: int = 1000,
    horizon: int = 30,
    ppr_threshold: float = 0.05,
    por_threshold: float = 0.70,
    min_trades: int = 10,
    min_wr: float = 0.45,
    min_pf: float = 1.20,
) -> MonteCarloResult:
    """
    Full Monte Carlo validation pipeline.
    
    Args:
        pnls: list of historical trade P&Ls
        trade_count: number of trades in backtest
        win_rate: historical win rate (0-1)
        profit_factor: historical profit factor
        n_sims: number of bootstrap simulations
        horizon: number of future trades to simulate
        ppr_threshold: max acceptable probability of ruin
        por_threshold: min acceptable probability of outperformance
        min_trades: minimum trade count threshold
        min_wr: minimum win rate threshold
        min_pf: minimum profit factor threshold
    
    Returns:
        MonteCarloResult with status + detailed metrics
    """
    pnls = np.array(pnls)
    
    # Quick validation gates
    if trade_count < min_trades:
        return MonteCarloResult(
            status="FAIL",
            ppr=1.0,
            por=0.0,
            metrics={"reason": f"Trade count {trade_count} < minimum {min_trades}"},
            quantiles={},
        )
    
    if win_rate < min_wr:
        return MonteCarloResult(
            status="FAIL",
            ppr=1.0,
            por=0.0,
            metrics={"reason": f"Win rate {win_rate:.2%} < minimum {min_wr:.2%}"},
            quantiles={},
        )
    
    if profit_factor < min_pf:
        return MonteCarloResult(
            status="FAIL",
            ppr=1.0,
            por=0.0,
            metrics={"reason": f"Profit factor {profit_factor:.2f} < minimum {min_pf:.2f}"},
            quantiles={},
        )
    
    # Run bootstrap simulations
    samples = bootstrap_sample_trades(pnls, n_sims=n_sims, horizon=horizon)
    results = [compute_sample_metrics(sample) for sample in samples]
    
    # Extract metric arrays for quantile calculation
    win_rates = np.array([r["win_rate"] for r in results])
    profit_factors = np.array([r["profit_factor"] for r in results])
    sharpes = np.array([r["sharpe"] for r in results])
    drawdowns = np.array([r["max_drawdown"] for r in results])
    total_returns = np.array([r["total_return"] for r in results])
    
    # Probability metrics
    ppr = np.mean(drawdowns > 0.50)  # P(drawdown > 50%)
    por = np.mean(total_returns > 0)  # P(positive return)
    
    # Quantile distributions
    quantiles = {
        "pf": {
            "p5": np.percentile(profit_factors, 5),
            "p50": np.percentile(profit_factors, 50),
            "p95": np.percentile(profit_factors, 95),
        },
        "wr": {
            "p5": np.percentile(win_rates, 5),
            "p50": np.percentile(win_rates, 50),
            "p95": np.percentile(win_rates, 95),
        },
        "sharpe": {
            "p5": np.percentile(sharpes, 5),
            "p50": np.percentile(sharpes, 50),
            "p95": np.percentile(sharpes, 95),
        },
        "mdd": {
            "p5": np.percentile(drawdowns, 5),
            "p50": np.percentile(drawdowns, 50),
            "p95": np.percentile(drawdowns, 95),
        },
    }
    
    # Classification logic
    if ppr > ppr_threshold:
        status = "FAIL"
    elif por < por_threshold:
        status = "PROBATION"
    elif quantiles["pf"]["p5"] < min_pf:
        status = "PROBATION"
    elif quantiles["wr"]["p5"] < min_wr:
        status = "PROBATION"
    else:
        status = "PASS"
    
    metrics = {
        "trade_count": trade_count,
        "historical_wr": win_rate,
        "historical_pf": profit_factor,
        "simulated_por": por,
        "simulated_ppr": ppr,
    }
    
    return MonteCarloResult(
        status=status,
        ppr=ppr,
        por=por,
        metrics=metrics,
        quantiles=quantiles,
    )


def validate_strategy_batch(
    strategies: List[Dict],
    n_sims: int = 1000,
    horizon: int = 30,
) -> Dict[str, MonteCarloResult]:
    """
    Validate a batch of strategies.
    Each strategy dict should contain: name, pnls, trade_count, win_rate, profit_factor
    """
    results = {}
    for strat in strategies:
        result = monte_carlo_validate(
            pnls=strat["pnls"],
            trade_count=strat["trade_count"],
            win_rate=strat["win_rate"],
            profit_factor=strat["profit_factor"],
            n_sims=n_sims,
            horizon=horizon,
        )
        results[strat["name"]] = result
    return results


if __name__ == "__main__":
    # Example usage
    example_pnls = [0.01, 0.015, -0.005, 0.02, 0.008, -0.003, 0.012, 0.015, -0.002, 0.018]
    result = monte_carlo_validate(
        pnls=example_pnls,
        trade_count=10,
        win_rate=0.70,
        profit_factor=2.5,
        n_sims=1000,
        horizon=30,
    )
    print(f"Status: {result.status}")
    print(f"PPR: {result.ppr:.2%}")
    print(f"POR: {result.por:.2%}")
    print(f"Quantiles: {result.quantiles}")
