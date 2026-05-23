"""
Regime-Aware Strategy Gating
============================
Prevents strategies from firing in market conditions where they historically fail.

This addresses the MEDIUM-HIGH IMPACT issue: "We have regime detection but it's 
not wired as a gate. Strategies fire regardless of regime."

Usage:
    from regime_aware_gate import RegimeAwareGate
    
    gate = RegimeAwareGate()
    
    # Check if strategy should fire
    can_trade = gate.check_signal(
        strategy_id="hurst_regime_adaptive",
        signal_direction="long",
        current_regime=MarketRegime.TRENDING
    )
    
    if not can_trade:
        # Block signal - wrong regime for this strategy
        continue
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('RegimeGate')


class MarketRegime(Enum):
    """Market regime classifications"""
    TRENDING = "trending"
    MEAN_REVERTING = "mean_reverting"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    UNKNOWN = "unknown"


class StrategyType(Enum):
    """Strategy classifications"""
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    BREAKOUT = "breakout"
    FUNDING_ARB = "funding_arbitrage"
    VOLATILITY = "volatility"
    GENERIC = "generic"


@dataclass
class RegimePerformance:
    """Performance in a specific regime"""
    regime: MarketRegime
    total_trades: int = 0
    win_rate: float = 0.0
    expectancy: float = 0.0
    avg_pnl: float = 0.0
    sharpe: float = 0.0
    is_viable: bool = False


@dataclass
class StrategyRegimeProfile:
    """Complete regime profile for a strategy"""
    strategy_id: str
    strategy_type: StrategyType
    
    # Performance by regime
    regime_performance: Dict[MarketRegime, RegimePerformance] = field(default_factory=dict)
    
    # Optimal regimes
    preferred_regimes: List[MarketRegime] = field(default_factory=list)
    avoided_regimes: List[MarketRegime] = field(default_factory=list)
    
    # Gates
    min_trades_per_regime: int = 5
    min_win_rate: float = 0.40
    min_expectancy: float = 0.0
    
    def is_regime_suitable(self, regime: MarketRegime) -> Tuple[bool, str]:
        """Check if strategy should trade in given regime"""
        if regime in self.avoided_regimes:
            return False, f"Regime {regime.value} in avoid list"
        
        if self.preferred_regimes and regime not in self.preferred_regimes:
            return False, f"Regime {regime.value} not in preferred list"
        
        perf = self.regime_performance.get(regime)
        if not perf:
            return True, "No data for this regime (allowing)"
        
        if perf.total_trades < self.min_trades_per_regime:
            return True, f"Insufficient data ({perf.total_trades} trades)"
        
        if perf.win_rate < self.min_win_rate:
            return False, f"Low win rate ({perf.win_rate:.1%}) in {regime.value}"
        
        if perf.expectancy < self.min_expectancy:
            return False, f"Negative expectancy ({perf.expectancy:.2f}%) in {regime.value}"
        
        return True, f"Viable in {regime.value} (WR: {perf.win_rate:.1%}, E: {perf.expectancy:.2f}%)"


class RegimeDetector:
    """
    Detect current market regime using multiple indicators
    """
    
    def __init__(
        self,
        hurst_trending_threshold: float = 0.6,
        hurst_mean_revert_threshold: float = 0.4,
        high_vol_threshold: float = 0.05,  # 5% daily vol
        low_vol_threshold: float = 0.01    # 1% daily vol
    ):
        self.hurst_trending = hurst_trending_threshold
        self.hurst_mean_revert = hurst_mean_revert_threshold
        self.high_vol = high_vol_threshold
        self.low_vol = low_vol_threshold
    
    def calculate_hurst_exponent(self, prices: List[float]) -> float:
        """Calculate Hurst exponent for mean-reversion/trend detection"""
        if len(prices) < 20:
            return 0.5
        
        # Calculate returns
        returns = [(prices[i] - prices[i-1]) / prices[i-1] 
                   for i in range(1, len(prices))]
        
        if not returns or len(returns) < 10:
            return 0.5
        
        # R/S analysis
        n = len(returns)
        mean_return = sum(returns) / n
        
        # Cumulative deviation
        cumdev = []
        cumsum = 0
        for r in returns:
            cumsum += (r - mean_return)
            cumdev.append(cumsum)
        
        if not cumdev:
            return 0.5
        
        R = max(cumdev) - min(cumdev)
        
        # Standard deviation
        variance = sum((r - mean_return) ** 2 for r in returns) / n
        S = variance ** 0.5
        
        if S == 0:
            return 0.5
        
        # Hurst estimate
        RS = R / S
        hurst = 0.5 * (1 + (RS / (n ** 0.5)))
        
        # Clamp to reasonable range
        return max(0.0, min(1.0, hurst))
    
    def calculate_volatility(self, prices: List[float], lookback: int = 20) -> float:
        """Calculate annualized volatility"""
        if len(prices) < lookback + 1:
            return 0.03  # Default 3%
        
        recent_prices = prices[-lookback:]
        returns = [(recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1] 
                   for i in range(1, len(recent_prices))]
        
        if not returns:
            return 0.03
        
        mean_ret = sum(returns) / len(returns)
        variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
        daily_vol = variance ** 0.5
        
        # Annualize
        return daily_vol * (365 ** 0.5)
    
    def detect_regime(
        self,
        prices: List[float],
        hurst: Optional[float] = None
    ) -> MarketRegime:
        """
        Detect current market regime
        """
        if len(prices) < 20:
            return MarketRegime.UNKNOWN
        
        # Calculate or use provided Hurst
        h = hurst if hurst is not None else self.calculate_hurst_exponent(prices)
        
        # Calculate volatility
        vol = self.calculate_volatility(prices)
        
        # Determine regime
        # Priority: volatility > Hurst
        if vol > self.high_vol:
            return MarketRegime.HIGH_VOLATILITY
        elif vol < self.low_vol:
            return MarketRegime.LOW_VOLATILITY
        elif h > self.hurst_trending:
            return MarketRegime.TRENDING
        elif h < self.hurst_mean_revert:
            return MarketRegime.MEAN_REVERTING
        else:
            return MarketRegime.RANGING


class RegimeAwareGate:
    """
    Main regime-aware gating system
    """
    
    def __init__(self):
        self.detector = RegimeDetector()
        self.profiles: Dict[str, StrategyRegimeProfile] = {}
        self._load_default_profiles()
    
    def _load_default_profiles(self):
        """Load default regime profiles for known strategies"""
        defaults = {
            # Trend-following strategies
            'hurst_regime_adaptive': StrategyRegimeProfile(
                strategy_id='hurst_regime_adaptive',
                strategy_type=StrategyType.TREND_FOLLOWING,
                preferred_regimes=[MarketRegime.TRENDING],
                avoided_regimes=[MarketRegime.MEAN_REVERTING]
            ),
            'adaptive_vr_confluence': StrategyRegimeProfile(
                strategy_id='adaptive_vr_confluence',
                strategy_type=StrategyType.TREND_FOLLOWING,
                preferred_regimes=[MarketRegime.TRENDING, MarketRegime.HIGH_VOLATILITY],
                avoided_regimes=[MarketRegime.RANGING]
            ),
            
            # Mean-reversion strategies
            'autocorrelation_exploiter': StrategyRegimeProfile(
                strategy_id='autocorrelation_exploiter',
                strategy_type=StrategyType.MEAN_REVERSION,
                preferred_regimes=[MarketRegime.MEAN_REVERTING, MarketRegime.RANGING],
                avoided_regimes=[MarketRegime.TRENDING]
            ),
            'volume_profile_value_area': StrategyRegimeProfile(
                strategy_id='volume_profile_value_area',
                strategy_type=StrategyType.MEAN_REVERSION,
                preferred_regimes=[MarketRegime.RANGING, MarketRegime.MEAN_REVERTING],
                avoided_regimes=[MarketRegime.HIGH_VOLATILITY]
            ),
            'multi_sigma_reversal': StrategyRegimeProfile(
                strategy_id='multi_sigma_reversal',
                strategy_type=StrategyType.MEAN_REVERSION,
                preferred_regimes=[MarketRegime.MEAN_REVERTING],
                avoided_regimes=[MarketRegime.TRENDING]
            ),
            
            # Funding arb (works in all regimes but best in high vol)
            'funding_carry': StrategyRegimeProfile(
                strategy_id='funding_carry',
                strategy_type=StrategyType.FUNDING_ARB,
                preferred_regimes=[],  # Works in all
                avoided_regimes=[]
            ),
            'funding_carry_elite': StrategyRegimeProfile(
                strategy_id='funding_carry_elite',
                strategy_type=StrategyType.FUNDING_ARB,
                preferred_regimes=[MarketRegime.HIGH_VOLATILITY],
                avoided_regimes=[]
            ),
            
            # Baby strategies
            'baby_battleground': StrategyRegimeProfile(
                strategy_id='baby_battleground',
                strategy_type=StrategyType.MOMENTUM,
                preferred_regimes=[MarketRegime.TRENDING, MarketRegime.RANGING],
                avoided_regimes=[MarketRegime.HIGH_VOLATILITY]
            ),
            'claws_of_doom': StrategyRegimeProfile(
                strategy_id='claws_of_doom',
                strategy_type=StrategyType.BREAKOUT,
                preferred_regimes=[MarketRegime.TRENDING, MarketRegime.HIGH_VOLATILITY],
                avoided_regimes=[MarketRegime.RANGING]
            ),
        }
        
        self.profiles = defaults
    
    def analyze_strategy_regimes(
        self,
        strategy_id: str,
        trades: List[Dict],
        price_history: Optional[List[float]] = None
    ) -> StrategyRegimeProfile:
        """
        Analyze historical performance by regime to build profile
        """
        if strategy_id not in self.profiles:
            self.profiles[strategy_id] = StrategyRegimeProfile(
                strategy_id=strategy_id,
                strategy_type=StrategyType.GENERIC
            )
        
        profile = self.profiles[strategy_id]
        
        # Group trades by regime
        regime_trades: Dict[MarketRegime, List[Dict]] = {r: [] for r in MarketRegime}
        
        for trade in trades:
            # Determine regime at trade time
            # In real implementation, look up from historical regime data
            regime = self._infer_trade_regime(trade, price_history)
            regime_trades[regime].append(trade)
        
        # Calculate performance per regime
        for regime, trades_list in regime_trades.items():
            if len(trades_list) < 3:
                continue
            
            pnls = [t.get('pnl_percent', 0) for t in trades_list]
            wins = sum(1 for p in pnls if p > 0)
            
            perf = RegimePerformance(
                regime=regime,
                total_trades=len(trades_list),
                win_rate=wins / len(trades_list),
                expectancy=sum(pnls) / len(pnls),
                avg_pnl=sum(pnls) / len(pnls),
                is_viable=(wins / len(trades_list) > 0.4 and sum(pnls) / len(pnls) > 0)
            )
            
            profile.regime_performance[regime] = perf
        
        # Auto-determine preferred/avoided regimes
        viable_regimes = [
            r for r, p in profile.regime_performance.items() 
            if p.is_viable
        ]
        
        poor_regimes = [
            r for r, p in profile.regime_performance.items() 
            if not p.is_viable and p.total_trades >= profile.min_trades_per_regime
        ]
        
        profile.preferred_regimes = viable_regimes
        profile.avoided_regimes = poor_regimes
        
        return profile
    
    def _infer_trade_regime(
        self,
        trade: Dict,
        price_history: Optional[List[float]]
    ) -> MarketRegime:
        """Infer market regime at time of trade"""
        # In production, look up from regime_state.json
        # For now, use a heuristic
        
        if price_history and len(price_history) >= 20:
            return self.detector.detect_regime(price_history)
        
        return MarketRegime.UNKNOWN
    
    def check_signal(
        self,
        strategy_id: str,
        current_regime: MarketRegime,
        signal_direction: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Check if strategy should be allowed to trade
        
        Returns: (allowed, reason)
        """
        if strategy_id not in self.profiles:
            logger.warning(f"No regime profile for {strategy_id}, allowing signal")
            return True, "No profile (allowing by default)"
        
        profile = self.profiles[strategy_id]
        allowed, reason = profile.is_regime_suitable(current_regime)
        
        if not allowed:
            logger.info(f"BLOCKED: {strategy_id} in {current_regime.value} - {reason}")
        
        return allowed, reason
    
    def get_current_regime(
        self,
        prices: List[float],
        hurst: Optional[float] = None
    ) -> MarketRegime:
        """Get current market regime"""
        return self.detector.detect_regime(prices, hurst)
    
    def filter_signals(
        self,
        signals: List[Dict],
        current_regime: MarketRegime
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Filter a batch of signals by regime suitability
        
        Returns: (allowed_signals, blocked_signals)
        """
        allowed = []
        blocked = []
        
        for signal in signals:
            strategy_id = signal.get('strategy_id', signal.get('strategy', 'unknown'))
            can_trade, reason = self.check_signal(strategy_id, current_regime)
            
            if can_trade:
                allowed.append(signal)
            else:
                signal['block_reason'] = reason
                blocked.append(signal)
        
        return allowed, blocked
    
    def generate_regime_report(self) -> Dict:
        """Generate report on regime profiles"""
        report = {
            'generated_at': datetime.now().isoformat(),
            'strategies': []
        }
        
        for strat_id, profile in self.profiles.items():
            strat_report = {
                'strategy_id': strat_id,
                'type': profile.strategy_type.value,
                'preferred_regimes': [r.value for r in profile.preferred_regimes],
                'avoided_regimes': [r.value for r in profile.avoided_regimes],
                'regime_performance': {}
            }
            
            for regime, perf in profile.regime_performance.items():
                strat_report['regime_performance'][regime.value] = {
                    'trades': perf.total_trades,
                    'win_rate': round(perf.win_rate, 2),
                    'expectancy': round(perf.expectancy, 4),
                    'viable': perf.is_viable
                }
            
            report['strategies'].append(strat_report)
        
        return report


# Example usage
if __name__ == "__main__":
    import random
    
    print("=" * 80)
    print("REGIME-AWARE GATE - Demo")
    print("=" * 80)
    
    gate = RegimeAwareGate()
    
    # Simulate different market regimes
    test_regimes = [
        MarketRegime.TRENDING,
        MarketRegime.MEAN_REVERTING,
        MarketRegime.RANGING,
        MarketRegime.HIGH_VOLATILITY
    ]
    
    strategies = [
        'hurst_regime_adaptive',
        'autocorrelation_exploiter',
        'funding_carry',
        'baby_battleground',
        'claws_of_doom'
    ]
    
    print("\n📊 Regime Suitability Matrix")
    print("-" * 80)
    print(f"{'Strategy':<30} {'Trending':<12} {'MeanRev':<12} {'Ranging':<12} {'HighVol':<12}")
    print("-" * 80)
    
    for strat in strategies:
        row = [strat[:28]]
        for regime in test_regimes:
            allowed, reason = gate.check_signal(strat, regime)
            status = "✓ YES" if allowed else "✗ NO"
            row.append(status)
        print(f"{row[0]:<30} {row[1]:<12} {row[2]:<12} {row[3]:<12} {row[4]:<12}")
    
    print("\n" + "-" * 80)
    print("\n📋 Signal Filtering Example")
    print("-" * 80)
    
    # Simulate incoming signals
    signals = [
        {'strategy_id': 'hurst_regime_adaptive', 'symbol': 'BTC', 'direction': 'long'},
        {'strategy_id': 'autocorrelation_exploiter', 'symbol': 'ETH', 'direction': 'short'},
        {'strategy_id': 'funding_carry', 'symbol': 'BTC', 'direction': 'short'},
        {'strategy_id': 'hurst_regime_adaptive', 'symbol': 'SOL', 'direction': 'long'},
        {'strategy_id': 'claws_of_doom', 'symbol': 'ADA', 'direction': 'long'},
    ]
    
    current_regime = MarketRegime.TRENDING
    print(f"Current Regime: {current_regime.value.upper()}")
    print()
    
    allowed, blocked = gate.filter_signals(signals, current_regime)
    
    print(f"ALLOWED ({len(allowed)} signals):")
    for s in allowed:
        print(f"  ✓ {s['strategy_id']} {s['direction']} {s['symbol']}")
    
    print(f"\nBLOCKED ({len(blocked)} signals):")
    for s in blocked:
        print(f"  ✗ {s['strategy_id']} {s['direction']} {s['symbol']} - {s.get('block_reason', '')}")
    
    print("\n" + "=" * 80)
