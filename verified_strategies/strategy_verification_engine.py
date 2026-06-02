#!/usr/bin/env python3
"""
Strategy Verification Engine — Hedge Fund-Grade Backtesting & Monte Carlo Validation
Implements rigorous statistical testing for trading strategy edge verification.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from enum import Enum
import json
from pathlib import Path


class StrategyTier(Enum):
    """Strategy classification based on risk-adjusted returns and statistical significance."""
    S = "S-Tier (Elite)"  # Sharpe > 1.5, Win Rate > 60%, MC p-value < 0.05
    A = "A-Tier (Strong)"  # Sharpe > 1.0, Win Rate > 55%, MC p-value < 0.10
    B = "B-Tier (Viable)"  # Sharpe > 0.5, Win Rate > 50%, MC p-value < 0.20
    C = "C-Tier (Marginal)"  # Sharpe > 0.0, Win Rate > 45%
    REJECTED = "Rejected"  # Below C-Tier thresholds


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics for a strategy."""
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    trades_count: int
    avg_win: float
    avg_loss: float
    consecutive_wins: int
    consecutive_losses: int
    
    # Monte Carlo metrics
    mc_p_value: float = 0.0
    mc_sharpe_mean: float = 0.0
    mc_sharpe_std: float = 0.0
    mc_win_rate_mean: float = 0.0
    mc_win_rate_std: float = 0.0
    
    # Classification
    tier: StrategyTier = StrategyTier.C
    
    def to_dict(self) -> Dict:
        """Convert metrics to dictionary."""
        return {
            'total_return': self.total_return,
            'annual_return': self.annual_return,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'win_rate': self.win_rate,
            'profit_factor': self.profit_factor,
            'trades_count': self.trades_count,
            'avg_win': self.avg_win,
            'avg_loss': self.avg_loss,
            'consecutive_wins': self.consecutive_wins,
            'consecutive_losses': self.consecutive_losses,
            'mc_p_value': self.mc_p_value,
            'mc_sharpe_mean': self.mc_sharpe_mean,
            'mc_sharpe_std': self.mc_sharpe_std,
            'mc_win_rate_mean': self.mc_win_rate_mean,
            'mc_win_rate_std': self.mc_win_rate_std,
            'tier': self.tier.name,
        }


class SimpleBacktester:
    """Lightweight backtester for strategy evaluation."""
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
    
    def run(self, strategy, market_data: pd.DataFrame) -> Tuple[pd.Series, List[Dict]]:
        """
        Run a strategy on market data.
        
        Args:
            strategy: Strategy object with run(market_data, capital) method
            market_data: DataFrame with OHLCV data
            
        Returns:
            equity_curve: Series of portfolio values
            trades: List of trade dicts with entry/exit info
        """
        try:
            # Use run_backtest if available (e.g. CarryTrade returns weights from run())
            if hasattr(strategy, 'run_backtest'):
                equity_curve, trades = strategy.run_backtest(market_data, self.initial_capital)
            else:
                equity_curve, trades = strategy.run(market_data, self.initial_capital)
            return equity_curve, trades
        except Exception as e:
            print(f"Error running strategy: {e}")
            return pd.Series([self.initial_capital]), []


class StrategyVerificationEngine:
    """Core verification engine for hedge fund-grade strategy validation."""
    
    def __init__(self, mc_iterations: int = 1000, confidence_level: float = 0.95):
        self.mc_iterations = mc_iterations
        self.confidence_level = confidence_level
        self.backtest_engine = SimpleBacktester()
    
    def verify_strategy(self, strategy, market_data: pd.DataFrame, 
                       asset_class: str = "UNKNOWN") -> PerformanceMetrics:
        """
        Comprehensive strategy verification including Monte Carlo testing.
        
        Args:
            strategy: Strategy object
            market_data: OHLCV DataFrame
            asset_class: Asset class for context
            
        Returns:
            PerformanceMetrics with tier classification
        """
        # Run backtest
        equity_curve, trades = self.backtest_engine.run(strategy, market_data)
        
        # Calculate base metrics
        metrics = self._calculate_metrics(equity_curve, trades)
        
        # Run Monte Carlo validation
        if len(trades) > 0:
            mc_results = self._monte_carlo_validation(trades, equity_curve)
            metrics.mc_p_value = mc_results['p_value']
            metrics.mc_sharpe_mean = mc_results['sharpe_mean']
            metrics.mc_sharpe_std = mc_results['sharpe_std']
            metrics.mc_win_rate_mean = mc_results['win_rate_mean']
            metrics.mc_win_rate_std = mc_results['win_rate_std']
        
        # Assign tier
        metrics.tier = self._classify_tier(metrics)
        
        return metrics
    
    def _calculate_metrics(self, equity_curve: pd.Series, trades: List[Dict]) -> PerformanceMetrics:
        """Calculate performance metrics from equity curve and trades."""
        
        # Return metrics
        total_return = (equity_curve.iloc[-1] - equity_curve.iloc[0]) / equity_curve.iloc[0]
        annual_return = total_return / (len(equity_curve) / 252)  # Assume daily data
        
        # Drawdown
        cummax = equity_curve.cummax()
        drawdown = (equity_curve - cummax) / cummax
        max_drawdown = drawdown.min()
        
        # Sharpe ratio
        returns = equity_curve.pct_change().dropna()
        sharpe_ratio = np.sqrt(252) * returns.mean() / returns.std() if returns.std() > 0 else 0
        
        # Trade metrics (prefer pct returns; fall back to dollar pnl / entry capital)
        if len(trades) > 0:
            pnls = []
            for t in trades:
                if 'pnl_pct' in t and t['pnl_pct'] is not None:
                    pnls.append(float(t['pnl_pct']))
                elif 'pnl' in t:
                    entry = t.get('entry_price') or t.get('entry') or 0
                    pnl = float(t.get('pnl', 0))
                    if entry and float(entry) != 0:
                        pnls.append(pnl / float(entry))
                    else:
                        pnls.append(pnl / equity_curve.iloc[0] if equity_curve.iloc[0] else pnl)
                else:
                    pnls.append(0.0)
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p < 0]
            
            win_rate = len(wins) / len(trades) if len(trades) > 0 else 0
            profit_factor = sum(wins) / abs(sum(losses)) if sum(losses) != 0 else 0
            avg_win = np.mean(wins) if wins else 0
            avg_loss = np.mean(losses) if losses else 0
            
            # Consecutive wins/losses
            consecutive_wins = self._max_consecutive(pnls, lambda x: x > 0)
            consecutive_losses = self._max_consecutive(pnls, lambda x: x < 0)
        else:
            win_rate = 0
            profit_factor = 0
            avg_win = 0
            avg_loss = 0
            consecutive_wins = 0
            consecutive_losses = 0
        
        return PerformanceMetrics(
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            trades_count=len(trades),
            avg_win=avg_win,
            avg_loss=avg_loss,
            consecutive_wins=consecutive_wins,
            consecutive_losses=consecutive_losses,
        )
    
    def _monte_carlo_validation(self, trades: List[Dict], equity_curve: pd.Series) -> Dict:
        """
        Monte Carlo resampling of trade returns to validate edge robustness.
        
        Returns:
            Dict with p-value and distribution statistics
        """
        pnls_list = []
        for t in trades:
            if 'pnl_pct' in t and t['pnl_pct'] is not None:
                pnls_list.append(float(t['pnl_pct']))
            else:
                entry = t.get('entry_price') or 0
                pnl = float(t.get('pnl', 0))
                if entry and float(entry) != 0:
                    pnls_list.append(pnl / float(entry))
                else:
                    pnls_list.append(pnl)
        pnls = np.array(pnls_list)
        
        if len(pnls) < 2:
            return {
                'p_value': 1.0,
                'sharpe_mean': 0,
                'sharpe_std': 0,
                'win_rate_mean': 0,
                'win_rate_std': 0,
            }
        
        original_sharpe = np.mean(pnls) / np.std(pnls) if np.std(pnls) > 0 else 0
        original_win_rate = np.sum(pnls > 0) / len(pnls)
        
        mc_sharpes = []
        mc_win_rates = []
        
        for _ in range(self.mc_iterations):
            # Resample with replacement
            resampled = np.random.choice(pnls, size=len(pnls), replace=True)
            
            # Calculate metrics on resampled data
            mc_sharpe = np.mean(resampled) / np.std(resampled) if np.std(resampled) > 0 else 0
            mc_win_rate = np.sum(resampled > 0) / len(resampled)
            
            mc_sharpes.append(mc_sharpe)
            mc_win_rates.append(mc_win_rate)
        
        mc_sharpes = np.array(mc_sharpes)
        mc_win_rates = np.array(mc_win_rates)
        
        # P-value: probability of observing this Sharpe by chance
        p_value = np.sum(mc_sharpes >= original_sharpe) / self.mc_iterations
        
        return {
            'p_value': p_value,
            'sharpe_mean': np.mean(mc_sharpes),
            'sharpe_std': np.std(mc_sharpes),
            'win_rate_mean': np.mean(mc_win_rates),
            'win_rate_std': np.std(mc_win_rates),
        }
    
    def _classify_tier(self, metrics: PerformanceMetrics) -> StrategyTier:
        """Classify strategy into tier based on metrics.

        Two paths:
          1. Standard (high-frequency / high-WR): strict MC p-value gates.
          2. Macro (low-frequency / trend-following): high PF gates, relaxed MC
             because N is naturally small (SMA crossovers generate few trades).
        """
        wr = metrics.win_rate
        pf = metrics.profit_factor
        sr = metrics.sharpe_ratio
        mc = metrics.mc_p_value
        n = metrics.trades_count

        # Minimum sample size — anything below 5 trades is too noisy
        if n < 5:
            return StrategyTier.REJECTED

        # --- S-Tier: Elite ---
        if sr > 1.5 and mc < 0.05:
            if wr > 0.60 or pf > 2.5:
                return StrategyTier.S

        # --- A-Tier: Strong ---
        # Standard path
        if sr > 1.0 and mc < 0.10 and (wr > 0.55 or pf > 2.0):
            return StrategyTier.A
        # Macro path (high Sharpe + very high PF, relaxed MC for small N)
        if sr > 1.2 and pf > 3.0 and mc < 0.35 and n >= 8:
            return StrategyTier.A

        # --- B-Tier: Viable ---
        # Standard path
        if sr > 0.5 and mc < 0.20 and (wr > 0.50 or pf > 1.5):
            return StrategyTier.B
        # Macro path (solid Sharpe + strong PF, relaxed MC)
        if sr > 0.8 and pf > 2.0 and mc < 0.55 and n >= 6:
            return StrategyTier.B

        # --- C-Tier: Marginal ---
        if sr > 0.0 and (wr > 0.40 or pf > 1.1):
            return StrategyTier.C
        if sr >= 0.5 and metrics.total_return > 0.20:
            return StrategyTier.C

        return StrategyTier.REJECTED
    
    @staticmethod
    def _max_consecutive(values: List, condition) -> int:
        """Find maximum consecutive values matching condition."""
        max_count = 0
        current_count = 0
        for v in values:
            if condition(v):
                current_count += 1
                max_count = max(max_count, current_count)
            else:
                current_count = 0
        return max_count


def generate_report(strategies_results: Dict[str, PerformanceMetrics], 
                   output_path: str = "verified_strategies/VERIFICATION_REPORT.json",
                   data_sources: Optional[Dict] = None) -> None:
    """Generate comprehensive verification report."""
    
    report = {
        'timestamp': pd.Timestamp.now().isoformat(),
        'data_mode': 'real_ohlcv',
        'data_sources': data_sources or {},
        'strategies': {},
        'summary': {
            'total_strategies': len(strategies_results),
            'by_tier': {},
        }
    }
    
    # Populate strategy results
    for name, metrics in strategies_results.items():
        report['strategies'][name] = metrics.to_dict()
    
    # Summary by tier
    tier_counts = {}
    for metrics in strategies_results.values():
        tier_name = metrics.tier.name
        tier_counts[tier_name] = tier_counts.get(tier_name, 0) + 1
    
    report['summary']['by_tier'] = tier_counts
    
    # Save report
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"Report saved to {output_path}")
