"""
Sentinel Hardened Integrator - Consistency-Focused Trading System
=================================================================
Ultra-conservative trading system based on ChatGPT/Perplexity feedback:
- Strip to 1-2 proven sleeves
- Meta-confidence scoring
- Consistency tracking
- WTF debugging
- Circuit breaker protection

This is the "production hardened" version that prioritizes consistency
over frequency.

Usage:
    from sentinel_hardened_integrator import HardenedSentinel
    
    sentinel = HardenedSentinel(mode='minimal_core')
    
    # Only processes 1-2 highest confidence signals per day
    result = sentinel.process_signals(signals, price_data)
    
    if result['circuit_breaker_active']:
        logger.error("Trading halted - check status")
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

# Import all Sentinel components
from sentinel_fund_strategy import SentinelFund, Signal
from transaction_cost_model import TransactionCostModel
from regime_aware_gate import RegimeAwareGate, MarketRegime
from consistency_tracker import ConsistencyTracker
from wtf_dashboard import WTFDashboard
from portfolio_circuit_breaker import PortfolioCircuitBreaker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('HardenedSentinel')


@dataclass
class HardenedConfig:
    """Configuration for hardened mode"""
    mode: str = "minimal_core"  # minimal_core, standard, aggressive
    
    # Ultra-conservative settings
    min_confidence_score: float = 0.85
    min_rr: float = 2.0
    min_consensus_systems: int = 2
    max_signals_per_day: int = 999  # TESTING SPRINT: was 2, uncapped to evaluate signal quality
    
    # Consistency requirements
    min_sharpe_30d: float = 1.0
    max_cv_expectancy: float = 0.4
    
    # Circuit breaker
    max_portfolio_dd: float = 6.0
    auto_flatten: bool = True


class HardenedSentinel:
    """
    Hardened Sentinel - Consistency-First Trading System
    
    Implements the "Starve the System" experiment:
    - Only top 30% confidence signals
    - RR >= 2.0
    - 2+ systems consensus
    - Consistency tracking
    - Global circuit breaker
    """
    
    def __init__(self, config: Optional[HardenedConfig] = None):
        self.config = config or HardenedConfig()
        
        logger.info(f"Initializing Hardened Sentinel (mode: {self.config.mode})")
        
        # Core components
        self.sentinel = SentinelFund()
        self.tcm = TransactionCostModel()
        self.regime_gate = RegimeAwareGate()
        self.consistency = ConsistencyTracker()
        self.wtf = WTFDashboard()
        self.circuit_breaker = PortfolioCircuitBreaker()
        
        # Daily tracking
        self.signals_today = 0
        self.last_reset = datetime.now().date()
        
        # Load minimal core config
        self._load_minimal_config()
    
    def _load_minimal_config(self):
        """Load minimal core configuration"""
        try:
            with open('minimal_core_config.json', 'r') as f:
                self.minimal_config = json.load(f)
                logger.info("Loaded minimal core configuration")
        except FileNotFoundError:
            self.minimal_config = None
            logger.warning("No minimal_core_config.json found")
    
    def _check_daily_reset(self):
        """Reset daily counters"""
        today = datetime.now().date()
        if today != self.last_reset:
            self.signals_today = 0
            self.last_reset = today
            logger.info("[Hardened] Daily counter reset")
    
    def calculate_meta_confidence(
        self,
        signal: Signal,
        net_expectancy: float,
        regime_ok: bool,
        consistency_score: float
    ) -> float:
        """
        Calculate meta-confidence score
        
        Combines multiple factors into unified confidence metric
        """
        score = 0.0
        
        # RR contribution (0-25%)
        if signal.rr >= 3.0:
            score += 0.25
        elif signal.rr >= 2.5:
            score += 0.20
        elif signal.rr >= 2.0:
            score += 0.15
        elif signal.rr >= 1.5:
            score += 0.10
        
        # Consensus contribution (0-20%)
        consensus_count = len(signal.supporting_systems)
        if consensus_count >= 4:
            score += 0.20
        elif consensus_count >= 3:
            score += 0.15
        elif consensus_count >= 2:
            score += 0.10
        
        # Net expectancy contribution (0-25%)
        if net_expectancy > 2.0:
            score += 0.25
        elif net_expectancy > 1.0:
            score += 0.20
        elif net_expectancy > 0.5:
            score += 0.10
        
        # Regime alignment (0-15%)
        if regime_ok:
            score += 0.15
        
        # Consistency contribution (0-15%)
        score += consistency_score * 0.15
        
        return min(score, 1.0)
    
    def process_signal(self, signal: Signal, price_data: List[float]) -> Optional[Dict]:
        """
        Process a single signal through hardened filters
        
        Returns processed signal or None if rejected
        """
        self._check_daily_reset()
        
        # Check circuit breaker
        can_trade, reason = self.circuit_breaker.can_trade()
        if not can_trade:
            self.wtf.log_rejection(
                signal.strategy_id,
                f"Circuit breaker: {reason}",
                {'signal': str(signal)},
                'circuit_breaker'
            )
            return None
        
        # Check daily limit
        if self.signals_today >= self.config.max_signals_per_day:
            self.wtf.log_rejection(
                signal.strategy_id,
                f"Daily limit reached ({self.config.max_signals_per_day})",
                {'signal': str(signal)},
                'daily_limit'
            )
            return None
        
        # Get strategy consistency metrics
        consistency = self.consistency.get_consistency_metrics(signal.strategy_id)
        
        # Step 1: Regime Check
        current_regime = self.regime_gate.get_current_regime(price_data)
        regime_ok, regime_reason = self.regime_gate.check_signal(
            signal.strategy_id, current_regime
        )
        
        if not regime_ok:
            self.wtf.log_rejection(
                signal.strategy_id,
                regime_reason,
                {'regime': current_regime.value},
                'regime'
            )
            return None
        
        # Step 2: RR Gate (hardened)
        if signal.rr < self.config.min_rr:
            self.wtf.log_rejection(
                signal.strategy_id,
                f"RR {signal.rr:.2f} < {self.config.min_rr}",
                {'rr': signal.rr},
                'rr_gate'
            )
            return None
        
        # Step 3: Consensus Gate
        if len(signal.supporting_systems) < self.config.min_consensus_systems:
            self.wtf.log_rejection(
                signal.strategy_id,
                f"Consensus {len(signal.supporting_systems)} < {self.config.min_consensus_systems}",
                {'systems': signal.supporting_systems},
                'consensus'
            )
            return None
        
        # Step 4: Consistency Check
        if consistency.sharpe_30d < self.config.min_sharpe_30d:
            self.wtf.log_rejection(
                signal.strategy_id,
                f"Sharpe {consistency.sharpe_30d:.2f} < {self.config.min_sharpe_30d}",
                {'sharpe': consistency.sharpe_30d},
                'consistency'
            )
            return None
        
        if consistency.cv_expectancy > self.config.max_cv_expectancy:
            self.wtf.log_rejection(
                signal.strategy_id,
                f"CV {consistency.cv_expectancy:.2f} > {self.config.max_cv_expectancy}",
                {'cv': consistency.cv_expectancy},
                'consistency'
            )
            return None
        
        # Step 5: Transaction Cost Model
        gross_exp = 0.5  # Default estimate
        net_exp, total_cost, viable = self.calculate_true_edge(signal, gross_exp)
        
        if not viable:
            self.wtf.log_rejection(
                signal.strategy_id,
                f"Edge consumed by costs: {net_exp:.2f}%",
                {'cost': total_cost},
                'cost'
            )
            return None
        
        # Step 6: Meta-Confidence Score
        confidence = self.calculate_meta_confidence(
            signal, net_exp, regime_ok, consistency.consistency_score
        )
        
        if confidence < self.config.min_confidence_score:
            self.wtf.log_rejection(
                signal.strategy_id,
                f"Confidence {confidence:.2f} < {self.config.min_confidence_score}",
                {'confidence': confidence},
                'confidence'
            )
            return None
        
        # PASSED ALL GATES
        self.signals_today += 1
        
        # Calculate position size with circuit breaker multiplier
        base_size = 0.02  # 2% base
        cb_multiplier = self.circuit_breaker.get_position_size_multiplier()
        position_size = base_size * cb_multiplier
        
        result = {
            'strategy_id': signal.strategy_id,
            'symbol': signal.symbol,
            'direction': signal.direction,
            'entry_price': signal.entry_price,
            'stop_loss': signal.stop_loss,
            'take_profit': signal.take_profit,
            'rr': signal.rr,
            'position_size': position_size,
            'confidence_score': confidence,
            'net_expectancy': net_exp,
            'regime': current_regime.value,
            'consistency_score': consistency.consistency_score,
            'sharpe_30d': consistency.sharpe_30d,
            'supporting_systems': signal.supporting_systems,
            'signals_today': self.signals_today
        }
        
        logger.info(
            f"[Hardened] APPROVED {signal.strategy_id} {signal.symbol} | "
            f"Confidence: {confidence:.0%} | Size: {position_size:.2%}"
        )
        
        return result
    
    def calculate_true_edge(
        self,
        signal: Signal,
        gross_expectancy: float
    ) -> Tuple[float, float, bool]:
        """Calculate net expectancy after costs"""
        trade_size = 10000
        
        cost_estimate = self.tcm.estimate_cost(
            symbol=signal.symbol,
            trade_size_usd=trade_size,
            exchange="binance",
            order_type="taker"
        )
        
        total_cost = cost_estimate.total_cost_percent * 2 + 0.03  # Round trip + funding
        net_expectancy = gross_expectancy - total_cost
        
        is_viable = net_expectancy > 0.5  # Need at least 0.5% edge
        
        return net_expectancy, total_cost, is_viable
    
    def process_signals(
        self,
        signals: List[Signal],
        price_data: List[float]
    ) -> Dict[str, Any]:
        """Process multiple signals and return approved ones"""
        
        # Update circuit breaker with current equity (placeholder)
        # In production, this would come from portfolio tracker
        
        approved = []
        rejected_count = 0
        
        for signal in signals:
            result = self.process_signal(signal, price_data)
            if result:
                approved.append(result)
            else:
                rejected_count += 1
        
        # Sort by confidence, take top N
        approved.sort(key=lambda x: x['confidence_score'], reverse=True)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'circuit_breaker_active': not self.circuit_breaker.can_trade()[0],
            'signals_processed': len(signals),
            'signals_approved': len(approved),
            'signals_rejected': rejected_count,
            'daily_quota_remaining': self.config.max_signals_per_day - self.signals_today,
            'approved_signals': approved[:self.config.max_signals_per_day]
        }
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health report"""
        return {
            'timestamp': datetime.now().isoformat(),
            'mode': self.config.mode,
            'circuit_breaker': self.circuit_breaker.get_status(),
            'consistency': self.consistency.get_all_strategies_report(),
            'wtf_summary': self.wtf.get_rejection_breakdown(days=1),
            'daily_stats': {
                'signals_today': self.signals_today,
                'max_allowed': self.config.max_signals_per_day
            }
        }


# Example usage
if __name__ == "__main__":
    import random
    
    print("=" * 80)
    print("HARDENED SENTINEL - Consistency-First System")
    print("=" * 80)
    
    sentinel = HardenedSentinel()
    
    # Generate test signals
    test_signals = [
        Signal(
            strategy_id="funding_carry_elite",
            symbol="BTC-USDT",
            direction="short",
            entry_price=65000,
            stop_loss=66500,
            take_profit=62000,
            timestamp=datetime.now(),
            supporting_systems=["funding_carry", "volume_profile", "hurst_regime"],
            confidence=0.9
        ),
        Signal(
            strategy_id="hurst_regime_adaptive",
            symbol="ETH-USDT",
            direction="short",
            entry_price=3500,
            stop_loss=3600,
            take_profit=3300,
            timestamp=datetime.now(),
            supporting_systems=["hurst_regime"],
            confidence=0.7
        ),
        Signal(
            strategy_id="funding_carry_elite",
            symbol="SOL-USDT",
            direction="short",
            entry_price=150,
            stop_loss=155,
            take_profit=140,
            timestamp=datetime.now(),
            supporting_systems=["funding_carry", "adaptive_vr", "volume_profile"],
            confidence=0.85
        )
    ]
    
    # Generate price data
    prices = [50000 + random.gauss(0, 500) for _ in range(100)]
    
    print(f"\nProcessing {len(test_signals)} signals...")
    print(f"Config: RR >= {sentinel.config.min_rr}, Confidence >= {sentinel.config.min_confidence_score}")
    print("-" * 80)
    
    result = sentinel.process_signals(test_signals, prices)
    
    print(f"\nResults:")
    print(f"  Circuit Breaker: {'ACTIVE' if result['circuit_breaker_active'] else 'OK'}")
    print(f"  Processed: {result['signals_processed']}")
    print(f"  Approved: {result['signals_approved']}")
    print(f"  Rejected: {result['signals_rejected']}")
    print(f"  Daily Quota Remaining: {result['daily_quota_remaining']}")
    
    if result['approved_signals']:
        print(f"\n[OK] Approved Signals:")
        for sig in result['approved_signals']:
            print(f"  {sig['strategy_id']} {sig['symbol']}")
            print(f"    Confidence: {sig['confidence_score']:.0%}")
            print(f"    Net Expectancy: {sig['net_expectancy']:.2f}%")
            print(f"    Position Size: {sig['position_size']:.2%}")
    
    # Print WTF report
    print("\n" + "=" * 80)
    wtf_report = sentinel.wtf.generate_daily_report()
    sentinel.wtf.print_console_report(wtf_report)
