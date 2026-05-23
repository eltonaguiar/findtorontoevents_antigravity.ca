"""
Sentinel Fund Strategy - Institutional-Grade Crypto Trading System
=================================================================
A hedge fund-style meta-strategy that manages risk, enforces consensus,
and dynamically allocates capital based on proven edge.

Based on Mercury AI feedback and institutional best practices:
- Core/Incubator book split
- Risk budgeting with Kelly criterion sizing
- Multi-system consensus gates
- Direction filtering for asymmetric strategies
- Real-time performance attribution

Author: Sentinel Fund System
Version: 1.0.0
"""

import json
import logging
import math
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import copy

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('SentinelFund')


class SignalStatus(Enum):
    """Signal validation status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    INCUBATOR = "incubator"
    EXPIRED = "expired"


class MarketRegime(Enum):
    """Market regime classifications"""
    TRENDING = "trending"
    MEAN_REVERTING = "mean_reverting"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    UNKNOWN = "unknown"


@dataclass
class Signal:
    """Trading signal with metadata"""
    strategy_id: str
    symbol: str
    direction: str  # 'long' or 'short'
    entry_price: float
    stop_loss: float
    take_profit: float
    timestamp: datetime
    rr: float = 0.0
    confidence: float = 0.5
    supporting_systems: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.rr == 0.0 and self.stop_loss != 0:
            risk = abs(self.entry_price - self.stop_loss)
            reward = abs(self.take_profit - self.entry_price)
            self.rr = reward / risk if risk > 0 else 0


@dataclass
class StrategyPerformance:
    """Rolling performance metrics for a strategy"""
    strategy_id: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl_percent: float = 0.0
    current_drawdown_percent: float = 0.0
    peak_equity: float = 100.0
    current_equity: float = 100.0
    expectancy: float = 0.0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    last_trade_time: Optional[datetime] = None
    last_update: Optional[datetime] = None
    
    def update_from_trade(self, pnl_percent: float, timestamp: datetime):
        """Update metrics with new trade result"""
        self.total_trades += 1
        self.total_pnl_percent += pnl_percent
        
        if pnl_percent > 0:
            self.winning_trades += 1
            self.avg_win = ((self.avg_win * (self.winning_trades - 1)) + pnl_percent) / self.winning_trades
        else:
            self.losing_trades += 1
            self.avg_loss = ((self.avg_loss * (self.losing_trades - 1)) + pnl_percent) / self.losing_trades
        
        # Update equity curve
        self.current_equity *= (1 + pnl_percent / 100)
        if self.current_equity > self.peak_equity:
            self.peak_equity = self.current_equity
        
        # Calculate drawdown
        self.current_drawdown_percent = (self.peak_equity - self.current_equity) / self.peak_equity * 100
        
        # Update derived metrics
        if self.total_trades > 0:
            self.win_rate = self.winning_trades / self.total_trades
            self.expectancy = (self.win_rate * self.avg_win) + ((1 - self.win_rate) * self.avg_loss)
        
        if abs(self.avg_loss) > 0:
            self.profit_factor = (self.winning_trades * self.avg_win) / (self.losing_trades * abs(self.avg_loss))
        
        self.last_trade_time = timestamp
        self.last_update = timestamp


class RiskBudgetAllocator:
    """
    Implements risk budgeting with fractional Kelly criterion sizing
    """
    
    def __init__(
        self,
        kelly_fraction: float = 0.25,
        max_position_core: float = 0.02,
        max_position_incubator: float = 0.005
    ):
        self.kelly_fraction = kelly_fraction
        self.max_position_core = max_position_core
        self.max_position_incubator = max_position_incubator
    
    def calculate_kelly_size(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        is_core: bool = True
    ) -> float:
        """
        Calculate position size using fractional Kelly criterion
        f* = (p*b - q) / b
        where p = win rate, q = loss rate, b = avg win / avg loss
        """
        if win_rate <= 0 or avg_loss == 0:
            return 0
        
        loss_rate = 1 - win_rate
        b = abs(avg_win / avg_loss) if avg_loss != 0 else 1
        
        if b == 0:
            return 0
        
        # Full Kelly
        kelly = (win_rate * b - loss_rate) / b
        
        # Fractional Kelly for safety
        fractional_kelly = kelly * self.kelly_fraction
        
        # Apply caps
        max_pos = self.max_position_core if is_core else self.max_position_incubator
        
        return max(0, min(fractional_kelly, max_pos))
    
    def calculate_position_size(
        self,
        signal: Signal,
        strategy_perf: StrategyPerformance,
        is_core: bool = True,
        confidence_boost: float = 1.0
    ) -> float:
        """Calculate final position size with all adjustments"""
        
        # Base Kelly size
        base_size = self.calculate_kelly_size(
            strategy_perf.win_rate,
            strategy_perf.avg_win,
            strategy_perf.avg_loss,
            is_core
        )
        
        # RR boost (higher RR = larger size)
        rr_multiplier = min(signal.rr / 1.5, 2.0) if signal.rr > 0 else 0.5
        
        # Consensus boost
        consensus_multiplier = min(len(signal.supporting_systems) / 2, 1.5)
        
        # Drawdown penalty
        dd_penalty = max(0, 1 - (strategy_perf.current_drawdown_percent / 5))
        
        # Freshness decay
        age_minutes = (datetime.now() - signal.timestamp).total_seconds() / 60
        freshness_multiplier = max(0.5, 1 - (age_minutes / 30))
        
        final_size = (
            base_size * 
            rr_multiplier * 
            consensus_multiplier * 
            dd_penalty * 
            freshness_multiplier *
            confidence_boost
        )
        
        max_pos = self.max_position_core if is_core else self.max_position_incubator
        return min(final_size, max_pos)


class SignalGate:
    """
    Enforces signal safety gates per institutional best practices
    """
    
    def __init__(
        self,
        min_rr: float = 1.5,
        min_rr_mercury: float = 1.4,
        min_consensus: int = 2,
        max_freshness_minutes: int = 15,
        alpha_short_only: bool = True
    ):
        self.min_rr = min_rr
        self.min_rr_mercury = min_rr_mercury
        self.min_consensus = min_consensus
        self.max_freshness_minutes = max_freshness_minutes
        self.alpha_short_only = alpha_short_only
        
        # Load kill list
        self.kill_list = self._load_kill_list()
        self.core_whitelist = self._load_core_whitelist()
    
    def _load_kill_list(self) -> List[str]:
        """Load strategies on kill list"""
        try:
            with open('kill_list.json', 'r') as f:
                data = json.load(f)
                return [s['id'] for s in data.get('killed_strategies', [])]
        except FileNotFoundError:
            return []
    
    def _load_core_whitelist(self) -> List[str]:
        """Load core whitelisted strategies"""
        try:
            with open('core_whitelist.json', 'r') as f:
                data = json.load(f)
                return [s['id'] for s in data.get('core_strategies', [])]
        except FileNotFoundError:
            return []
    
    def validate_signal(
        self,
        signal: Signal,
        strategy_perf: StrategyPerformance
    ) -> Tuple[SignalStatus, str]:
        """
        Validate a signal through all gates
        Returns: (status, reason)
        """
        
        # Gate 1: Kill list check
        if signal.strategy_id in self.kill_list:
            return SignalStatus.REJECTED, f"Strategy {signal.strategy_id} is on kill list"
        
        # Gate 2: Direction check for Alpha strategies
        if self.alpha_short_only and 'alpha' in signal.strategy_id.lower():
            if signal.direction == 'long':
                return SignalStatus.REJECTED, "Alpha long signals blocked due to negative expectancy"
        
        # Gate 3: Risk/Reward check
        min_rr = self.min_rr_mercury if 'mercury' in signal.strategy_id.lower() else self.min_rr
        if signal.rr < min_rr:
            return SignalStatus.REJECTED, f"RR {signal.rr:.2f} below minimum {min_rr}"
        
        # Gate 4: Freshness check
        age_minutes = (datetime.now() - signal.timestamp).total_seconds() / 60
        if age_minutes > self.max_freshness_minutes:
            return SignalStatus.EXPIRED, f"Signal expired ({age_minutes:.1f} min old)"
        
        # Gate 5: Consensus check for core book
        if signal.strategy_id in self.core_whitelist:
            if len(signal.supporting_systems) < self.min_consensus:
                return SignalStatus.INCUBATOR, f"Insufficient consensus ({len(signal.supporting_systems)}/{self.min_consensus})"
        
        # Gate 6: Performance check
        if strategy_perf.total_trades >= 10:
            if strategy_perf.expectancy < 0:
                return SignalStatus.INCUBATOR, f"Negative expectancy ({strategy_perf.expectancy:.2f}%)"
            if strategy_perf.win_rate < 0.30:
                return SignalStatus.INCUBATOR, f"Low win rate ({strategy_perf.win_rate:.1%})"
            if strategy_perf.current_drawdown_percent > 5:
                return SignalStatus.INCUBATOR, f"In drawdown ({strategy_perf.current_drawdown_percent:.1f}%)"
        
        return SignalStatus.APPROVED, "All gates passed"


class RegimeDetector:
    """
    Detects market regimes for strategy filtering
    """
    
    def __init__(
        self,
        hurst_threshold_trending: float = 0.6,
        hurst_threshold_mean_revert: float = 0.4
    ):
        self.hurst_threshold_trending = hurst_threshold_trending
        self.hurst_threshold_mean_revert = hurst_threshold_mean_revert
        self.current_regime = MarketRegime.UNKNOWN
    
    def detect_regime(self, price_data: List[float], hurst_exponent: Optional[float] = None) -> MarketRegime:
        """
        Detect current market regime
        """
        if not price_data or len(price_data) < 20:
            return MarketRegime.UNKNOWN
        
        # Calculate returns
        returns = [(price_data[i] - price_data[i-1]) / price_data[i-1] 
                   for i in range(1, len(price_data))]
        
        # Volatility regime
        volatility = math.sqrt(sum(r**2 for r in returns) / len(returns))
        
        # Use provided Hurst or estimate
        h = hurst_exponent if hurst_exponent else self._estimate_hurst(price_data)
        
        # Determine regime
        if h > self.hurst_threshold_trending:
            self.current_regime = MarketRegime.TRENDING
        elif h < self.hurst_threshold_mean_revert:
            self.current_regime = MarketRegime.MEAN_REVERTING
        else:
            self.current_regime = MarketRegime.RANGING
        
        # Volatility overlay
        if volatility > 0.05:  # 5% volatility threshold
            self.current_regime = MarketRegime.HIGH_VOLATILITY
        elif volatility < 0.01:
            self.current_regime = MarketRegime.LOW_VOLATILITY
        
        return self.current_regime
    
    def _estimate_hurst(self, price_data: List[float]) -> float:
        """
        Simple R/S Hurst exponent estimation
        """
        if len(price_data) < 20:
            return 0.5
        
        returns = [(price_data[i] - price_data[i-1]) / price_data[i-1] 
                   for i in range(1, len(price_data))]
        
        n = len(returns)
        mean_return = sum(returns) / n
        
        # Cumulative deviation
        cumdev = [sum(returns[:i+1]) - (i+1) * mean_return for i in range(n)]
        
        # Range
        R = max(cumdev) - min(cumdev)
        
        # Standard deviation
        S = math.sqrt(sum((r - mean_return)**2 for r in returns) / n)
        
        if S == 0:
            return 0.5
        
        # Hurst estimate
        return math.log(R / S) / math.log(n / 2)


class SentinelFund:
    """
    Main hedge fund orchestrator
    """
    
    def __init__(self):
        self.performance_tracker: Dict[str, StrategyPerformance] = {}
        self.risk_allocator = RiskBudgetAllocator()
        self.signal_gate = SignalGate()
        self.regime_detector = RegimeDetector()
        self.approved_signals: List[Signal] = []
        self.rejected_signals: List[Tuple[Signal, str]] = []
        self.incubator_signals: List[Signal] = []
        
        self._load_performance_data()
    
    def _load_performance_data(self):
        """Load existing performance data"""
        try:
            with open('sentinel_performance_tracker.json', 'r') as f:
                data = json.load(f)
                for strat_id, perf_data in data.items():
                    self.performance_tracker[strat_id] = StrategyPerformance(
                        strategy_id=strat_id,
                        **{k: v for k, v in perf_data.items() 
                           if k in StrategyPerformance.__dataclass_fields__}
                    )
        except FileNotFoundError:
            logger.info("No existing performance data found")
    
    def _save_performance_data(self):
        """Save performance data to disk"""
        data = {
            strat_id: {
                k: (v.isoformat() if isinstance(v, datetime) else v)
                for k, v in asdict(perf).items()
            }
            for strat_id, perf in self.performance_tracker.items()
        }
        with open('sentinel_performance_tracker.json', 'w') as f:
            json.dump(data, f, indent=2)
    
    def process_signal(self, signal: Signal) -> Tuple[SignalStatus, float, str]:
        """
        Process a signal through the full pipeline
        Returns: (status, position_size, reason)
        """
        # Get or create strategy performance tracker
        if signal.strategy_id not in self.performance_tracker:
            self.performance_tracker[signal.strategy_id] = StrategyPerformance(
                strategy_id=signal.strategy_id
            )
        
        strategy_perf = self.performance_tracker[signal.strategy_id]
        
        # Run through signal gates
        status, reason = self.signal_gate.validate_signal(signal, strategy_perf)
        
        if status == SignalStatus.REJECTED:
            self.rejected_signals.append((signal, reason))
            return status, 0.0, reason
        
        if status == SignalStatus.EXPIRED:
            self.rejected_signals.append((signal, reason))
            return status, 0.0, reason
        
        # Calculate position size
        is_core = signal.strategy_id in self.signal_gate.core_whitelist
        position_size = self.risk_allocator.calculate_position_size(
            signal, strategy_perf, is_core
        )
        
        if status == SignalStatus.INCUBATOR:
            self.incubator_signals.append(signal)
            # Reduce size for incubator
            position_size *= 0.25
            return status, position_size, reason
        
        # Approved for core book
        self.approved_signals.append(signal)
        
        # Log the approval
        logger.info(
            f"APPROVED: {signal.strategy_id} {signal.direction} {signal.symbol} "
            f"| RR: {signal.rr:.2f} | Size: {position_size:.2%} | "
            f"Consensus: {len(signal.supporting_systems)} systems"
        )
        
        return status, position_size, reason
    
    def update_trade_result(
        self,
        strategy_id: str,
        pnl_percent: float,
        timestamp: Optional[datetime] = None
    ):
        """Update performance with trade result"""
        if strategy_id not in self.performance_tracker:
            self.performance_tracker[strategy_id] = StrategyPerformance(
                strategy_id=strategy_id
            )
        
        self.performance_tracker[strategy_id].update_from_trade(
            pnl_percent,
            timestamp or datetime.now()
        )
        
        self._save_performance_data()
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get current portfolio summary"""
        core_strategies = []
        incubator_strategies = []
        
        for strat_id, perf in self.performance_tracker.items():
            summary = {
                'strategy_id': strat_id,
                'total_trades': perf.total_trades,
                'win_rate': perf.win_rate,
                'expectancy': perf.expectancy,
                'current_drawdown': perf.current_drawdown_percent,
                'profit_factor': perf.profit_factor,
                'current_equity': perf.current_equity
            }
            
            if strat_id in self.signal_gate.core_whitelist:
                core_strategies.append(summary)
            else:
                incubator_strategies.append(summary)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'core_strategies': core_strategies,
            'incubator_strategies': incubator_strategies,
            'approved_signals_count': len(self.approved_signals),
            'incubator_signals_count': len(self.incubator_signals),
            'rejected_signals_count': len(self.rejected_signals),
            'portfolio_equity': sum(s.current_equity for s in self.performance_tracker.values())
        }
    
    def generate_weekly_report(self) -> Dict[str, Any]:
        """Generate PM-style weekly report"""
        report = {
            'report_date': datetime.now().isoformat(),
            'report_type': 'weekly_pm_dashboard',
            'components': []
        }
        
        for strat_id, perf in self.performance_tracker.items():
            if perf.total_trades < 5:
                continue
            
            # Determine action based on performance
            action = 'hold'
            if perf.expectancy < 0:
                action = 'demote_to_incubator'
            elif perf.win_rate < 0.30:
                action = 'review'
            elif perf.current_drawdown_percent > 5:
                action = 'pause'
            elif perf.expectancy > 0.5 and perf.win_rate > 0.55:
                action = 'promote_to_core'
            
            report['components'].append({
                'strategy_id': strat_id,
                'total_trades': perf.total_trades,
                'win_rate_percent': round(perf.win_rate * 100, 2),
                'expectancy_percent': round(perf.expectancy, 4),
                'max_drawdown_percent': round(perf.current_drawdown_percent, 2),
                'profit_factor': round(perf.profit_factor, 2),
                'current_equity': round(perf.current_equity, 2),
                'recommendation': action
            })
        
        # Sort by expectancy
        report['components'].sort(key=lambda x: x['expectancy_percent'], reverse=True)
        
        return report


# Example usage and demonstration
if __name__ == "__main__":
    # Initialize the fund
    fund = SentinelFund()
    
    # Example signals
    test_signals = [
        Signal(
            strategy_id="funding_carry",
            symbol="BTC-USDT",
            direction="long",
            entry_price=65000,
            stop_loss=64000,
            take_profit=67000,
            timestamp=datetime.now(),
            supporting_systems=["funding_carry", "volume_profile_value_area"],
            confidence=0.75
        ),
        Signal(
            strategy_id="alpha_engine_long",
            symbol="ETH-USDT",
            direction="long",
            entry_price=3500,
            stop_loss=3400,
            take_profit=3700,
            timestamp=datetime.now(),
            supporting_systems=["alpha_engine"],
            confidence=0.60
        ),
        Signal(
            strategy_id="smart_money_fvg",
            symbol="SOL-USDT",
            direction="short",
            entry_price=150,
            stop_loss=155,
            take_profit=140,
            timestamp=datetime.now(),
            supporting_systems=["smart_money_fvg"],
            confidence=0.50
        ),
        Signal(
            strategy_id="hurst_regime_adaptive",
            symbol="BTC-USDT",
            direction="short",
            entry_price=65500,
            stop_loss=66500,
            take_profit=63500,
            timestamp=datetime.now(),
            supporting_systems=["hurst_regime_adaptive", "adaptive_vr_confluence", "claws_of_doom"],
            confidence=0.80
        )
    ]
    
    print("=" * 80)
    print("SENTINEL FUND - Signal Processing Demo")
    print("=" * 80)
    
    for signal in test_signals:
        status, size, reason = fund.process_signal(signal)
        print(f"\nSignal: {signal.strategy_id} {signal.direction} {signal.symbol}")
        print(f"  RR: {signal.rr:.2f} | Consensus: {len(signal.supporting_systems)} systems")
        print(f"  Status: {status.value}")
        print(f"  Position Size: {size:.2%}")
        print(f"  Reason: {reason}")
    
    print("\n" + "=" * 80)
    print("PORTFOLIO SUMMARY")
    print("=" * 80)
    summary = fund.get_portfolio_summary()
    print(f"Approved Signals: {summary['approved_signals_count']}")
    print(f"Incubator Signals: {summary['incubator_signals_count']}")
    print(f"Rejected Signals: {summary['rejected_signals_count']}")
    
    print("\n" + "=" * 80)
    print("WEEKLY PM REPORT (Template)")
    print("=" * 80)
    report = fund.generate_weekly_report()
    for comp in report['components']:
        print(f"\n{comp['strategy_id']}:")
        print(f"  Trades: {comp['total_trades']} | WR: {comp['win_rate_percent']}%")
        print(f"  Expectancy: {comp['expectancy_percent']}% | DD: {comp['max_drawdown_percent']}%")
        print(f"  Action: {comp['recommendation']}")
