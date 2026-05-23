#!/usr/bin/env python3
"""
Hedge Fund Risk Management Module
==================================
Institutional-grade risk controls:
- 4-tier kill switch system (5/10/15/20% drawdown levels)
- CVaR (Conditional Value at Risk) calculation
- Rolling correlation monitoring
- Dynamic position sizing based on Kelly criterion and CVaR
- Scenario analysis framework
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class KillSwitchLevel(Enum):
    """4-tier kill switch system."""
    WARNING = (0.05, "yellow", "5% DD - Warning, reduce size 25%")
    CAUTION = (0.10, "orange", "10% DD - Caution, reduce size 50%")
    ALERT = (0.15, "red", "15% DD - Alert, reduce size 75%")
    KILL = (0.20, "black", "20% DD - KILL SWITCH, halt all trading")
    
    def __init__(self, threshold: float, color: str, description: str):
        self.threshold = threshold
        self.color = color
        self.description = description


@dataclass
class RiskSnapshot:
    """Complete risk snapshot for a portfolio."""
    timestamp: str
    portfolio_value: float
    peak_value: float
    current_drawdown: float
    var_95: float
    cvar_95: float
    var_99: float
    cvar_99: float
    max_drawdown: float
    kill_switch_level: Optional[KillSwitchLevel]
    position_sizes: Dict[str, float]
    correlation_matrix: Optional[pd.DataFrame]


class KillSwitchManager:
    """
    4-tier kill switch system for institutional risk management.
    
    Unlike single-threshold systems, this provides graduated response:
    - 5% DD: Warning (reduce size 25%)
    - 10% DD: Caution (reduce size 50%)
    - 15% DD: Alert (reduce size 75%)
    - 20% DD: Kill (halt trading)
    """
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.peak_value = initial_capital
        self.current_level = None
        self.history = []
        
    def update(self, portfolio_value: float, timestamp: str = None) -> Dict:
        """
        Update kill switch status with new portfolio value.
        
        Returns:
            Dict with current status, action required, and size multiplier.
        """
        from datetime import datetime
        
        if timestamp is None:
            timestamp = datetime.now().isoformat()
            
        # Update peak
        if portfolio_value > self.peak_value:
            self.peak_value = portfolio_value
            
        # Calculate drawdown
        drawdown = (self.peak_value - portfolio_value) / self.peak_value
        
        # Determine level
        level = None
        size_multiplier = 1.0
        action = "NORMAL"
        
        if drawdown >= KillSwitchLevel.KILL.threshold:
            level = KillSwitchLevel.KILL
            size_multiplier = 0.0
            action = "HALT_ALL_TRADING"
        elif drawdown >= KillSwitchLevel.ALERT.threshold:
            level = KillSwitchLevel.ALERT
            size_multiplier = 0.25
            action = "REDUCE_SIZE_75_PERCENT"
        elif drawdown >= KillSwitchLevel.CAUTION.threshold:
            level = KillSwitchLevel.CAUTION
            size_multiplier = 0.50
            action = "REDUCE_SIZE_50_PERCENT"
        elif drawdown >= KillSwitchLevel.WARNING.threshold:
            level = KillSwitchLevel.WARNING
            size_multiplier = 0.75
            action = "REDUCE_SIZE_25_PERCENT"
            
        self.current_level = level
        
        result = {
            'timestamp': timestamp,
            'portfolio_value': portfolio_value,
            'peak_value': self.peak_value,
            'drawdown': drawdown,
            'level': level.name if level else None,
            'color': level.color if level else 'green',
            'size_multiplier': size_multiplier,
            'action': action,
            'description': level.description if level else 'Normal operation'
        }
        
        self.history.append(result)
        return result
    
    def reset(self, new_peak: Optional[float] = None):
        """Reset kill switch after recovery or manual override."""
        self.current_level = None
        if new_peak:
            self.peak_value = new_peak


class CVaRMonitor:
    """
    Conditional Value at Risk (CVaR) monitoring.
    
    CVaR (also called Expected Shortfall) measures the average loss
    in the tail beyond the VaR threshold. More informative than VaR
    alone for tail risk management.
    """
    
    def __init__(self, confidence_levels: List[float] = [0.95, 0.99]):
        self.confidence_levels = confidence_levels
        
    def calculate(self, returns: pd.Series, 
                  position_sizes: Optional[Dict[str, float]] = None) -> Dict:
        """
        Calculate VaR and CVaR for return series.
        
        Args:
            returns: Series of strategy returns
            position_sizes: Optional dict of symbol -> position size for weighted calc
            
        Returns:
            Dict with VaR and CVaR at each confidence level
        """
        results = {}
        
        # Historical simulation method
        sorted_returns = returns.sort_values()
        n = len(sorted_returns)
        
        for conf in self.confidence_levels:
            # VaR: the return at the confidence quantile
            var_idx = int((1 - conf) * n)
            var = sorted_returns.iloc[var_idx]
            
            # CVaR: average of returns beyond VaR (in the tail)
            cvar = sorted_returns.iloc[:var_idx].mean()
            
            results[f'var_{int(conf*100)}'] = var
            results[f'cvar_{int(conf*100)}'] = cvar
            
        return results
    
    def check_breach(self, returns: pd.Series, var_threshold: float = -0.05) -> Dict:
        """
        Check if recent returns breached VaR threshold.
        
        Returns breach statistics for backtesting.
        """
        breaches = returns < var_threshold
        n_breaches = breaches.sum()
        
        return {
            'n_breaches': n_breaches,
            'breach_rate': n_breaches / len(returns),
            'avg_breach_magnitude': returns[breaches].mean() if n_breaches > 0 else 0,
            'consecutive_breaches': self._max_consecutive(breaches)
        }
    
    def _max_consecutive(self, series: pd.Series) -> int:
        """Find maximum consecutive True values in boolean series."""
        max_count = count = 0
        for val in series:
            if val:
                count += 1
                max_count = max(max_count, count)
            else:
                count = 0
        return max_count


class CorrelationMonitor:
    """
    Rolling correlation monitoring for portfolio construction.
    
    Detects correlation breakdowns and crowded trades.
    """
    
    def __init__(self, lookback_windows: List[int] = [30, 90]):
        self.windows = lookback_windows
        
    def compute_matrix(self, returns_df: pd.DataFrame, 
                       window: int = 30) -> pd.DataFrame:
        """Compute rolling correlation matrix."""
        if len(returns_df) < window:
            return returns_df.corr()
        return returns_df.iloc[-window:].corr()
    
    def check_correlation_spike(self, returns_df: pd.DataFrame,
                                threshold: float = 0.7) -> Dict:
        """
        Check for concerning correlation levels.
        
        Returns pairs with correlation above threshold.
        """
        matrix = self.compute_matrix(returns_df)
        
        spikes = []
        for i in range(len(matrix.columns)):
            for j in range(i + 1, len(matrix.columns)):
                corr = matrix.iloc[i, j]
                if abs(corr) > threshold:
                    spikes.append({
                        'pair': (matrix.columns[i], matrix.columns[j]),
                        'correlation': corr,
                        'is_highly_correlated': corr > threshold,
                        'is_negatively_correlated': corr < -threshold
                    })
                    
        return {
            'n_spikes': len(spikes),
            'spikes': spikes,
            'avg_correlation': matrix.values[np.triu_indices_from(matrix.values, k=1)].mean(),
            'max_correlation': matrix.values[np.triu_indices_from(matrix.values, k=1)].max()
        }
    
    def estimate_portfolio_var(self, weights: pd.Series, 
                               returns_df: pd.DataFrame,
                               confidence: float = 0.95) -> float:
        """
        Estimate portfolio VaR using correlation matrix.
        
        VaR_p = z * sqrt(w' * Σ * w)
        where Σ is the covariance matrix
        """
        cov_matrix = returns_df.cov()
        portfolio_var = np.sqrt(weights.T @ cov_matrix @ weights)
        z_score = abs(np.percentile(np.random.standard_normal(10000), (1-confidence)*100))
        return z_score * portfolio_var


class DynamicPositionSizer:
    """
    Dynamic position sizing combining Kelly Criterion with CVaR targeting.
    
    Position size = Kelly_fraction * (target_CVaR / current_CVaR)
    """
    
    def __init__(self, kelly_fraction: float = 0.25, target_cvar: float = 0.02):
        """
        Args:
            kelly_fraction: Conservative Kelly (typically 0.25-0.5)
            target_cvar: Target CVaR at 95% confidence (e.g., 0.02 = 2%)
        """
        self.kelly_fraction = kelly_fraction
        self.target_cvar = target_cvar
        
    def kelly_criterion(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        Kelly Criterion: f* = (p*b - q) / b
        where p = win rate, b = win/loss ratio, q = 1-p
        """
        if avg_loss == 0:
            return 0
        b = avg_win / avg_loss
        q = 1 - win_rate
        kelly = (win_rate * b - q) / b
        return max(0, min(kelly, 1))  # Bound between 0 and 1
    
    def calculate_position_size(self, strategy_returns: pd.Series,
                                current_cvar: float,
                                win_rate: Optional[float] = None,
                                avg_win: Optional[float] = None,
                                avg_loss: Optional[float] = None) -> Dict:
        """
        Calculate dynamic position size.
        
        Returns dict with Kelly size, CVaR-adjusted size, and final recommendation.
        """
        # Kelly size
        if win_rate is not None and avg_win is not None and avg_loss is not None:
            kelly_size = self.kelly_criterion(win_rate, avg_win, avg_loss)
        else:
            # Estimate from returns
            wins = strategy_returns[strategy_returns > 0]
            losses = strategy_returns[strategy_returns < 0]
            if len(losses) > 0 and len(wins) > 0:
                kelly_size = self.kelly_criterion(
                    len(wins) / len(strategy_returns),
                    wins.mean(),
                    abs(losses.mean())
                )
            else:
                kelly_size = 0
                
        # Conservative Kelly
        conservative_kelly = kelly_size * self.kelly_fraction
        
        # CVaR adjustment
        if current_cvar > 0:
            cvar_multiplier = self.target_cvar / current_cvar
        else:
            cvar_multiplier = 1.0
            
        # Final position size
        final_size = conservative_kelly * cvar_multiplier
        
        return {
            'kelly_raw': kelly_size,
            'kelly_conservative': conservative_kelly,
            'cvar_multiplier': cvar_multiplier,
            'target_cvar': self.target_cvar,
            'current_cvar': current_cvar,
            'recommended_position_size': min(final_size, 0.25),  # Max 25% per strategy
            'max_position_cap': 0.25
        }


class ScenarioAnalyzer:
    """
    Scenario analysis framework for stress testing.
    
    Tests portfolio performance under historical and hypothetical scenarios.
    """
    
    SCENARIOS = {
        'btc_crash_50': {
            'description': 'BTC crashes 50% in 24 hours',
            'crypto_correlation': 0.9,
            'btc_return': -0.50,
            'alt_impact_factor': 0.8  # Alts drop 80% of BTC drop
        },
        'exchange_outage': {
            'description': 'Major exchange outage for 4 hours',
            'liquidity_factor': 0.3,  # Only 30% liquidity available
            'slippage_multiplier': 3.0,
            'unwind_time_hours': 8
        },
        'regulatory_ban': {
            'description': 'Major market bans crypto derivatives',
            'volume_reduction': 0.6,  # 60% volume gone
            'spread_widening': 2.5,
            'correlation_spike': 0.95
        },
        'stablecoin_depeg': {
            'description': 'USDT depegs to $0.90',
            'usdt_value': 0.90,
            'flight_to_quality': True,
            'btc_safe_haven_demand': 0.05  # BTC up 5%
        }
    }
    
    def __init__(self, portfolio: Dict[str, float]):
        """
        Args:
            portfolio: Dict of symbol -> position size (as % of portfolio)
        """
        self.portfolio = portfolio
        
    def run_scenario(self, scenario_name: str, 
                     returns_history: pd.DataFrame) -> Dict:
        """
        Run portfolio through a stress scenario.
        
        Returns estimated P&L and risk metrics under scenario.
        """
        if scenario_name not in self.SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario_name}")
            
        scenario = self.SCENARIOS[scenario_name]
        
        # Calculate portfolio impact
        if scenario_name == 'btc_crash_50':
            return self._btc_crash_impact(scenario)
        elif scenario_name == 'exchange_outage':
            return self._outage_impact(scenario)
        elif scenario_name == 'regulatory_ban':
            return self._regulatory_impact(scenario)
        elif scenario_name == 'stablecoin_depeg':
            return self._depeg_impact(scenario)
            
    def _btc_crash_impact(self, scenario: Dict) -> Dict:
        """Calculate impact of BTC crash scenario."""
        btc_exposure = self.portfolio.get('BTCUSDT', 0)
        alt_exposure = sum(v for k, v in self.portfolio.items() if k != 'BTCUSDT')
        
        btc_loss = btc_exposure * scenario['btc_return']
        alt_loss = alt_exposure * scenario['btc_return'] * scenario['alt_impact_factor']
        
        return {
            'scenario': 'BTC Crash 50%',
            'estimated_pnl': btc_loss + alt_loss,
            'btc_component': btc_loss,
            'alt_component': alt_loss,
            'portfolio_impact_pct': (btc_loss + alt_loss) / sum(self.portfolio.values())
        }
    
    def _outage_impact(self, scenario: Dict) -> Dict:
        """Calculate impact of exchange outage."""
        # Estimate cost of closing positions with reduced liquidity
        current_cost = sum(self.portfolio.values()) * 0.001  # 0.1% base cost
        stressed_cost = current_cost * scenario['slippage_multiplier']
        
        # Cost of delayed unwinding
        time_cost = scenario['unwind_time_hours'] * 0.001  # 0.1% per hour exposure
        
        return {
            'scenario': 'Exchange Outage',
            'liquidity_cost': stressed_cost - current_cost,
            'time_exposure_cost': time_cost,
            'total_cost': stressed_cost + time_cost
        }
    
    def _regulatory_impact(self, scenario: Dict) -> Dict:
        """Calculate impact of regulatory ban."""
        # Volume reduction leads to higher slippage
        # Spread widening increases costs
        
        base_spread = 0.001  # 0.1%
        new_spread = base_spread * scenario['spread_widening']
        
        # Estimate P&L impact from wider spreads
        total_position = sum(abs(v) for v in self.portfolio.values())
        spread_cost = total_position * (new_spread - base_spread)
        
        return {
            'scenario': 'Regulatory Ban',
            'spread_cost': spread_cost,
            'liquidity_premium': total_position * 0.02,  # 2% to exit
            'total_cost': spread_cost + total_position * 0.02
        }
    
    def _depeg_impact(self, scenario: Dict) -> Dict:
        """Calculate impact of stablecoin depeg."""
        # Any USDT-denominated positions lose value
        usdt_positions = sum(self.portfolio.values())
        usdt_loss = usdt_positions * (1 - scenario['usdt_value'])
        
        # BTC safe haven gain
        btc_gain = self.portfolio.get('BTCUSDT', 0) * scenario['btc_safe_haven_demand']
        
        return {
            'scenario': 'Stablecoin Depeg',
            'usdt_loss': usdt_loss,
            'btc_safe_haven_gain': btc_gain,
            'net_impact': usdt_loss - btc_gain
        }


class HFRiskDashboard:
    """
    Combined hedge fund risk dashboard.
    
    Integrates all risk modules into a single snapshot.
    """
    
    def __init__(self, initial_capital: float = 100000):
        self.kill_switch = KillSwitchManager(initial_capital)
        self.cvar_monitor = CVaRMonitor()
        self.correlation_monitor = CorrelationMonitor()
        self.position_sizer = DynamicPositionSizer()
        
    def generate_snapshot(self, portfolio_value: float,
                         returns: pd.Series,
                         returns_df: pd.DataFrame,
                         position_sizes: Dict[str, float]) -> RiskSnapshot:
        """Generate complete risk snapshot."""
        from datetime import datetime
        
        # Kill switch status
        kill_status = self.kill_switch.update(portfolio_value)
        
        # CVaR
        cvar_results = self.cvar_monitor.calculate(returns)
        
        # Correlation
        corr_check = self.correlation_monitor.check_correlation_spike(returns_df)
        
        # Max drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_dd = drawdown.min()
        
        return RiskSnapshot(
            timestamp=datetime.now().isoformat(),
            portfolio_value=portfolio_value,
            peak_value=self.kill_switch.peak_value,
            current_drawdown=kill_status['drawdown'],
            var_95=cvar_results.get('var_95', 0),
            cvar_95=cvar_results.get('cvar_95', 0),
            var_99=cvar_results.get('var_99', 0),
            cvar_99=cvar_results.get('cvar_99', 0),
            max_drawdown=max_dd,
            kill_switch_level=self.kill_switch.current_level,
            position_sizes=position_sizes,
            correlation_matrix=self.correlation_monitor.compute_matrix(returns_df) if len(returns_df) > 30 else None
        )


if __name__ == "__main__":
    # Example usage
    print("Hedge Fund Risk Management Module")
    print("=" * 50)
    
    # Kill switch example
    killswitch = KillSwitchManager(100000)
    
    # Simulate drawdown progression
    values = [100000, 98000, 95000, 90000, 88000, 85000, 82000, 80000, 81000]
    for val in values:
        status = killswitch.update(val)
        print(f"Value: ${val:,} | DD: {status['drawdown']:.1%} | "
              f"Level: {status['level'] or 'OK'} | Action: {status['action']}")
    
    print("\nCVaR Example:")
    np.random.seed(42)
    returns = pd.Series(np.random.normal(0.001, 0.02, 252))
    cvar_monitor = CVaRMonitor()
    cvar_results = cvar_monitor.calculate(returns)
    print(f"VaR 95%: {cvar_results['var_95']:.2%}")
    print(f"CVaR 95%: {cvar_results['cvar_95']:.2%}")
    print(f"VaR 99%: {cvar_results['var_99']:.2%}")
    print(f"CVaR 99%: {cvar_results['cvar_99']:.2%}")
