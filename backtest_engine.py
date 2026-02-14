"""
================================================================================
INSTITUTIONAL BACKTESTING ENGINE
================================================================================
Comprehensive backtesting framework for crypto prediction models

FEATURES:
- Walk-forward validation
- Multiple market regime testing
- Statistical significance testing
- Performance attribution
- Risk metrics calculation
================================================================================
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from scipy import stats


@dataclass
class BacktestConfig:
    """Configuration for backtesting"""
    # Time periods
    train_window: int = 1680  # 4 months of 4h bars
    test_step: int = 4  # Rebalance every 4 bars (16 hours)
    
    # Trading costs
    commission_rate: float = 0.0006  # 6 bps (Binance tier 1)
    slippage_rate: float = 0.0003  # 3 bps estimated slippage
    
    # Risk-free rate for Sharpe (annualized)
    risk_free_rate: float = 0.05


class PerformanceMetrics:
    """Calculate institutional-grade performance metrics"""
    
    @staticmethod
    def calculate_returns_metrics(returns: List[float], 
                                  risk_free_rate: float = 0.05,
                                  periods_per_year: int = 2190) -> Dict:
        """
        Calculate comprehensive return metrics
        
        Parameters:
        -----------
        returns : List[float]
            Strategy returns (not percentages)
        risk_free_rate : float
            Annual risk-free rate
        periods_per_year : int
            Number of periods in a year (2190 for 4h bars)
        """
        returns = np.array(returns)
        returns = returns[~np.isnan(returns)]
        
        if len(returns) == 0:
            return {}
        
        # Basic metrics
        total_return = np.prod(1 + returns) - 1
        n_periods = len(returns)
        years = n_periods / periods_per_year
        
        # Annualized metrics
        if years > 0:
            cagr = (1 + total_return) ** (1 / years) - 1
        else:
            cagr = 0
        
        # Volatility
        volatility = np.std(returns) * np.sqrt(periods_per_year)
        
        # Sharpe ratio
        excess_returns = returns - risk_free_rate / periods_per_year
        if np.std(excess_returns) > 0:
            sharpe = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(periods_per_year)
        else:
            sharpe = 0
        
        # Sortino ratio (downside deviation)
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0 and np.std(downside_returns) > 0:
            sortino = np.mean(excess_returns) / np.std(downside_returns) * np.sqrt(periods_per_year)
        else:
            sortino = sharpe  # Fallback if no downside
        
        # Drawdown calculation
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (cumulative - running_max) / running_max
        max_drawdown = np.min(drawdowns)
        
        # Calmar ratio
        if abs(max_drawdown) > 0:
            calmar = cagr / abs(max_drawdown)
        else:
            calmar = 0
        
        # Win rate
        win_rate = np.mean(returns > 0)
        
        # Profit factor
        gross_profits = np.sum(returns[returns > 0])
        gross_losses = abs(np.sum(returns[returns < 0]))
        profit_factor = gross_profits / gross_losses if gross_losses > 0 else 0
        
        # Skewness and kurtosis
        return_skew = stats.skew(returns) if len(returns) > 2 else 0
        return_kurt = stats.kurtosis(returns) if len(returns) > 3 else 0
        
        # VaR and CVaR
        var_95 = np.percentile(returns, 5)
        var_99 = np.percentile(returns, 1)
        cvar_95 = np.mean(returns[returns <= var_95]) if len(returns[returns <= var_95]) > 0 else var_95
        
        # Information ratio (vs buy and hold)
        # Simplified: assume buy and hold has different return pattern
        
        return {
            'total_return': f"{total_return * 100:.2f}%",
            'cagr': f"{cagr * 100:.2f}%",
            'volatility_annual': f"{volatility * 100:.2f}%",
            'sharpe_ratio': f"{sharpe:.3f}",
            'sortino_ratio': f"{sortino:.3f}",
            'max_drawdown': f"{max_drawdown * 100:.2f}%",
            'calmar_ratio': f"{calmar:.3f}",
            'win_rate': f"{win_rate * 100:.2f}%",
            'profit_factor': f"{profit_factor:.3f}",
            'skewness': f"{return_skew:.3f}",
            'kurtosis': f"{return_kurt:.3f}",
            'var_95': f"{var_95 * 100:.2f}%",
            'var_99': f"{var_99 * 100:.2f}%",
            'cvar_95': f"{cvar_95 * 100:.2f}%",
            'n_trades': len(returns)
        }
    
    @staticmethod
    def calculate_monthly_breakdown(returns: List[float], 
                                   timestamps: List,
                                   periods_per_month: int = 180) -> Dict:
        """Calculate monthly return breakdown"""
        returns = np.array(returns)
        
        # Group returns by month (approximate with rolling windows)
        monthly_returns = []
        for i in range(0, len(returns), periods_per_month):
            month_rets = returns[i:i+periods_per_month]
            if len(month_rets) > 0:
                monthly_return = np.prod(1 + month_rets) - 1
                monthly_returns.append(monthly_return)
        
        if not monthly_returns:
            return {}
        
        monthly_returns = np.array(monthly_returns)
        
        return {
            'avg_monthly_return': f"{np.mean(monthly_returns) * 100:.2f}%",
            'monthly_volatility': f"{np.std(monthly_returns) * 100:.2f}%",
            'best_month': f"{np.max(monthly_returns) * 100:.2f}%",
            'worst_month': f"{np.min(monthly_returns) * 100:.2f}%",
            'positive_months': f"{np.mean(monthly_returns > 0) * 100:.2f}%",
            'monthly_sharpe': f"{np.mean(monthly_returns) / np.std(monthly_returns) * np.sqrt(12):.3f}" if np.std(monthly_returns) > 0 else "0.000"
        }
    
    @staticmethod
    def statistical_significance_test(model_returns: List[float],
                                       benchmark_returns: List[float] = None) -> Dict:
        """
        Test statistical significance of returns
        
        Returns t-statistic and p-value for hypothesis that mean return > 0
        """
        returns = np.array(model_returns)
        returns = returns[~np.isnan(returns)]
        
        if len(returns) < 30:
            return {'note': 'Insufficient data for statistical test (need >30 samples)'}
        
        # T-test for mean return > 0
        t_stat, p_value = stats.ttest_1samp(returns, 0)
        
        # One-sided test
        if t_stat > 0:
            p_value_one_sided = p_value / 2
        else:
            p_value_one_sided = 1 - p_value / 2
        
        # Confidence interval for mean return
        confidence_level = 0.95
        dof = len(returns) - 1
        t_critical = stats.t.ppf((1 + confidence_level) / 2, dof)
        margin_error = t_critical * stats.sem(returns)
        ci_lower = np.mean(returns) - margin_error
        ci_upper = np.mean(returns) + margin_error
        
        results = {
            't_statistic': f"{t_stat:.4f}",
            'p_value_two_sided': f"{p_value:.6f}",
            'p_value_one_sided': f"{p_value_one_sided:.6f}",
            'significant_at_5pct': p_value_one_sided < 0.05,
            'significant_at_1pct': p_value_one_sided < 0.01,
            'mean_return_ci_95': f"[{ci_lower * 100:.4f}%, {ci_upper * 100:.4f}%]"
        }
        
        # If benchmark provided, test difference
        if benchmark_returns is not None:
            bench = np.array(benchmark_returns)
            bench = bench[~np.isnan(bench)]
            
            if len(bench) == len(returns):
                diff = returns - bench
                t_stat_diff, p_val_diff = stats.ttest_1samp(diff, 0)
                results['benchmark_comparison_t_stat'] = f"{t_stat_diff:.4f}"
                results['benchmark_comparison_p_value'] = f"{p_val_diff:.6f}"
                results['outperforms_benchmark_5pct'] = p_val_diff / 2 < 0.05 and t_stat_diff > 0
        
        return results


class MarketRegimeAnalyzer:
    """Analyze performance across different market regimes"""
    
    @staticmethod
    def classify_regime(prices: pd.Series, lookback: int = 42) -> str:
        """Classify current market regime"""
        if len(prices) < lookback:
            return 'UNKNOWN'
        
        recent_prices = prices.iloc[-lookback:]
        returns = recent_prices.pct_change().dropna()
        
        if len(returns) < 10:
            return 'UNKNOWN'
        
        # Calculate metrics
        total_return = (recent_prices.iloc[-1] / recent_prices.iloc[0]) - 1
        volatility = returns.std() * np.sqrt(2190)  # Annualized
        
        # Trend strength
        sma_short = recent_prices.rolling(6).mean().iloc[-1]
        sma_long = recent_prices.rolling(24).mean().iloc[-1]
        trend_strength = abs(sma_short / sma_long - 1)
        
        # Classify
        if total_return > 0.3 and volatility < 0.5:
            return 'BULL_TREND'
        elif total_return < -0.3 and volatility < 0.5:
            return 'BEAR_TREND'
        elif volatility > 0.8:
            return 'HIGH_VOLATILITY'
        elif volatility < 0.3 and abs(total_return) < 0.1:
            return 'LOW_VOLATILITY'
        elif trend_strength > 0.05 and total_return > 0.1:
            return 'BREAKOUT_UP'
        elif trend_strength > 0.05 and total_return < -0.1:
            return 'BREAKOUT_DOWN'
        else:
            return 'SIDEWAYS'
    
    @staticmethod
    def analyze_performance_by_regime(returns: List[float],
                                       prices: pd.Series,
                                       timestamps: List) -> Dict:
        """Analyze strategy performance by market regime"""
        regime_returns = {
            'BULL_TREND': [],
            'BEAR_TREND': [],
            'SIDEWAYS': [],
            'HIGH_VOLATILITY': [],
            'LOW_VOLATILITY': [],
            'BREAKOUT_UP': [],
            'BREAKOUT_DOWN': [],
            'UNKNOWN': []
        }
        
        for i in range(len(returns)):
            if i < 42:
                regime = 'UNKNOWN'
            else:
                regime = MarketRegimeAnalyzer.classify_regime(prices.iloc[:i])
            
            regime_returns[regime].append(returns[i])
        
        # Calculate metrics for each regime
        results = {}
        for regime, rets in regime_returns.items():
            if len(rets) > 10:
                metrics = PerformanceMetrics.calculate_returns_metrics(rets)
                results[regime] = {
                    'count': len(rets),
                    'metrics': metrics
                }
        
        return results


def run_comprehensive_backtest(model, df: pd.DataFrame, asset: str,
                                config: BacktestConfig = None) -> Dict:
    """
    Run comprehensive backtest with full metrics
    """
    config = config or BacktestConfig()
    
    # Run backtest
    results = model.backtest(df, asset, 
                             train_size=config.train_window,
                             step_size=config.test_step)
    
    # Calculate metrics
    returns = results['returns']
    timestamps = results['timestamps']
    
    metrics = PerformanceMetrics.calculate_returns_metrics(
        returns, config.risk_free_rate
    )
    
    monthly_metrics = PerformanceMetrics.calculate_monthly_breakdown(
        returns, timestamps
    )
    
    stats_tests = PerformanceMetrics.statistical_significance_test(returns)
    
    regime_analysis = MarketRegimeAnalyzer.analyze_performance_by_regime(
        returns, df['price'], timestamps
    )
    
    return {
        'asset': asset,
        'metrics': metrics,
        'monthly_metrics': monthly_metrics,
        'statistical_tests': stats_tests,
        'regime_analysis': regime_analysis,
        'equity_curve': [1 + sum(returns[:i+1]) for i in range(len(returns))],
        'drawdown_curve': _calculate_drawdown_curve(returns),
        'timestamps': [str(t) for t in timestamps]
    }


def _calculate_drawdown_curve(returns: List[float]) -> List[float]:
    """Calculate drawdown curve for visualization"""
    cumulative = np.cumprod(1 + np.array(returns))
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = (cumulative - running_max) / running_max
    return drawdowns.tolist()


def compare_models(custom_results: Dict, generic_results: Dict) -> Dict:
    """
    Compare customized vs generic model performance
    """
    comparison = {
        'sharpe_difference': {
            'custom': custom_results['metrics'].get('sharpe_ratio', '0.000'),
            'generic': generic_results['metrics'].get('sharpe_ratio', '0.000'),
            'difference': f"{float(custom_results['metrics'].get('sharpe_ratio', 0)) - float(generic_results['metrics'].get('sharpe_ratio', 0)):.3f}"
        },
        'return_difference': {
            'custom': custom_results['metrics'].get('cagr', '0.00%'),
            'generic': generic_results['metrics'].get('cagr', '0.00%'),
        },
        'drawdown_comparison': {
            'custom': custom_results['metrics'].get('max_drawdown', '0.00%'),
            'generic': generic_results['metrics'].get('max_drawdown', '0.00%'),
        },
        'win_rate_comparison': {
            'custom': custom_results['metrics'].get('win_rate', '0.00%'),
            'generic': generic_results['metrics'].get('win_rate', '0.00%'),
        }
    }
    
    return comparison


if __name__ == "__main__":
    print("=" * 80)
    print("INSTITUTIONAL BACKTESTING ENGINE")
    print("=" * 80)
    print("\nThis module provides:")
    print("  - PerformanceMetrics: Calculate institutional-grade metrics")
    print("  - MarketRegimeAnalyzer: Analyze performance by regime")
    print("  - run_comprehensive_backtest: Full backtest pipeline")
    print("  - compare_models: Head-to-head model comparison")
    print("=" * 80)
