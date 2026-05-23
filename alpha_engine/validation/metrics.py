"""
Performance Metrics

Comprehensive metrics suite for strategy evaluation.
Reports everything needed for the TACO checklist:
T - Transaction costs included
A - Avoided leakage
C - Consistent across regimes
O - Out-of-sample beats benchmark
"""
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class StrategyMetrics:
    """Complete metrics for a strategy."""
    # Return metrics
    total_return: float = 0
    annual_return: float = 0
    benchmark_return: float = 0
    alpha: float = 0
    information_ratio: float = 0

    # Risk metrics
    sharpe_ratio: float = 0
    sortino_ratio: float = 0
    calmar_ratio: float = 0
    max_drawdown: float = 0
    max_drawdown_duration: int = 0
    ulcer_index: float = 0

    # Trade metrics
    win_rate: float = 0
    profit_factor: float = 0
    expectancy: float = 0
    avg_win: float = 0
    avg_loss: float = 0
    payoff_ratio: float = 0

    # Tail risk
    var_95: float = 0
    cvar_95: float = 0
    skewness: float = 0
    kurtosis: float = 0
    tail_ratio: float = 0

    # Stability
    stability_of_returns: float = 0  # R-squared of equity curve
    consistency_score: float = 0     # % of positive rolling windows
    omega_ratio: float = 0

    # Capacity
    avg_turnover: float = 0
    avg_positions: float = 0
    min_dollar_volume_traded: float = 0

    # Regime performance
    regime_sharpes: Dict[str, float] = None


class PerformanceMetrics:
    """Compute comprehensive performance metrics."""

    @staticmethod
    def compute_all(
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
        risk_free_rate: float = 0.05,
    ) -> StrategyMetrics:
        """Compute all metrics from a returns series."""
        metrics = StrategyMetrics()
        returns = returns.dropna()

        if len(returns) < 10:
            return metrics

        n_years = len(returns) / 252

        # ── Return Metrics ────────────────────────────────────────────────
        total = (1 + returns).prod() - 1
        metrics.total_return = total
        metrics.annual_return = (1 + total) ** (1 / max(n_years, 0.01)) - 1

        if benchmark_returns is not None:
            bench = benchmark_returns.reindex(returns.index).fillna(0)
            bench_total = (1 + bench).prod() - 1
            metrics.benchmark_return = bench_total
            metrics.alpha = metrics.annual_return - ((1 + bench_total) ** (1 / max(n_years, 0.01)) - 1)

            # Information Ratio
            active = returns - bench
            if active.std() > 0:
                metrics.information_ratio = active.mean() / active.std() * np.sqrt(252)

        # ── Risk Metrics ──────────────────────────────────────────────────
        daily_rf = risk_free_rate / 252
        excess = returns - daily_rf

        if returns.std() > 0:
            metrics.sharpe_ratio = excess.mean() / returns.std() * np.sqrt(252)

        downside = returns[returns < 0]
        if len(downside) > 0 and downside.std() > 0:
            metrics.sortino_ratio = excess.mean() / downside.std() * np.sqrt(252)

        # Drawdown
        equity = (1 + returns).cumprod()
        peak = equity.cummax()
        drawdown = (equity - peak) / peak
        metrics.max_drawdown = abs(drawdown.min())

        if metrics.max_drawdown > 0:
            metrics.calmar_ratio = metrics.annual_return / metrics.max_drawdown

        # Max drawdown duration
        underwater = drawdown < 0
        if underwater.any():
            groups = (~underwater).cumsum()
            durations = underwater.groupby(groups).sum()
            metrics.max_drawdown_duration = int(durations.max()) if len(durations) > 0 else 0

        # Ulcer Index
        dd_sq = drawdown ** 2
        metrics.ulcer_index = np.sqrt(dd_sq.mean())

        # ── Tail Risk ─────────────────────────────────────────────────────
        metrics.var_95 = np.percentile(returns, 5)
        tail = returns[returns <= metrics.var_95]
        metrics.cvar_95 = tail.mean() if len(tail) > 0 else metrics.var_95
        metrics.skewness = float(returns.skew())
        metrics.kurtosis = float(returns.kurtosis())

        # Tail ratio: right tail / left tail
        p95 = np.percentile(returns, 95)
        p5 = abs(np.percentile(returns, 5))
        metrics.tail_ratio = p95 / p5 if p5 > 0 else 0

        # ── Stability ─────────────────────────────────────────────────────
        # R-squared of equity curve vs linear trend
        equity_log = np.log(equity)
        x = np.arange(len(equity_log))
        if len(x) > 2:
            try:
                slope, intercept = np.polyfit(x, equity_log, 1)
                predicted = slope * x + intercept
                ss_res = np.sum((equity_log - predicted) ** 2)
                ss_tot = np.sum((equity_log - equity_log.mean()) ** 2)
                metrics.stability_of_returns = 1 - ss_res / ss_tot if ss_tot > 0 else 0
            except Exception:
                metrics.stability_of_returns = 0

        # Consistency: % of rolling 63-day windows with positive returns
        rolling_ret = returns.rolling(63).sum()
        metrics.consistency_score = (rolling_ret > 0).mean() if len(rolling_ret.dropna()) > 0 else 0

        # Omega ratio: sum of gains above threshold / sum of losses below
        threshold = 0
        gains = returns[returns > threshold].sum()
        losses = abs(returns[returns <= threshold].sum())
        metrics.omega_ratio = gains / losses if losses > 0 else float("inf")

        return metrics

    @staticmethod
    def compute_regime_metrics(
        returns: pd.Series,
        regimes: pd.Series,
    ) -> Dict[str, float]:
        """Compute Sharpe ratio for each regime."""
        result = {}
        for regime in regimes.unique():
            if pd.isna(regime):
                continue
            mask = regimes == regime
            regime_returns = returns[mask].dropna()
            if len(regime_returns) > 10 and regime_returns.std() > 0:
                sharpe = regime_returns.mean() / regime_returns.std() * np.sqrt(252)
                result[str(regime)] = round(sharpe, 3)
        return result

    @staticmethod
    def compute_deflated_sharpe(
        sharpe: float,
        n_trials: int,
        n_observations: int,
        skewness: float = 0,
        kurtosis: float = 3,
    ) -> float:
        """
        Deflated Sharpe Ratio (Bailey & Lopez de Prado).
        
        Adjusts Sharpe for multiple testing / data snooping.
        If DSR < 0.5, the strategy likely has no real edge.
        """
        from scipy import stats

        if n_trials <= 1 or n_observations < 10:
            return sharpe

        # Expected max Sharpe from N random trials
        e_max_sharpe = np.sqrt(2 * np.log(n_trials))

        # Standard error of Sharpe
        se_sharpe = np.sqrt(
            (1 + 0.25 * sharpe ** 2 * (kurtosis - 1) - sharpe * skewness)
            / (n_observations - 1)
        )

        if se_sharpe <= 0:
            return 0

        # Deflated Sharpe = probability that true Sharpe > 0
        test_stat = (sharpe - e_max_sharpe) / se_sharpe
        dsr = stats.norm.cdf(test_stat)

        return dsr

    @staticmethod
    def format_report(metrics: StrategyMetrics, name: str = "") -> str:
        """Format metrics into a readable report."""
        lines = [
            f"{'=' * 60}",
            f"  Strategy: {name}",
            f"{'=' * 60}",
            f"",
            f"  RETURNS",
            f"    Total Return:     {metrics.total_return * 100:>8.2f}%",
            f"    Annual Return:    {metrics.annual_return * 100:>8.2f}%",
            f"    Benchmark Return: {metrics.benchmark_return * 100:>8.2f}%",
            f"    Alpha:            {metrics.alpha * 100:>8.2f}%",
            f"",
            f"  RISK",
            f"    Sharpe Ratio:     {metrics.sharpe_ratio:>8.3f}",
            f"    Sortino Ratio:    {metrics.sortino_ratio:>8.3f}",
            f"    Calmar Ratio:     {metrics.calmar_ratio:>8.3f}",
            f"    Max Drawdown:     {metrics.max_drawdown * 100:>8.2f}%",
            f"    DD Duration:      {metrics.max_drawdown_duration:>8d} days",
            f"",
            f"  TAIL RISK",
            f"    VaR 95%:          {metrics.var_95 * 100:>8.3f}%",
            f"    CVaR 95%:         {metrics.cvar_95 * 100:>8.3f}%",
            f"    Skewness:         {metrics.skewness:>8.3f}",
            f"    Kurtosis:         {metrics.kurtosis:>8.3f}",
            f"    Tail Ratio:       {metrics.tail_ratio:>8.3f}",
            f"",
            f"  STABILITY",
            f"    R² of Equity:     {metrics.stability_of_returns:>8.3f}",
            f"    Consistency:      {metrics.consistency_score * 100:>8.1f}%",
            f"    Omega Ratio:      {metrics.omega_ratio:>8.3f}",
            f"    Info Ratio:       {metrics.information_ratio:>8.3f}",
            f"{'=' * 60}",
        ]
        return "\n".join(lines)
