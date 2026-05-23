"""
Sentinel Fund Integrator
========================
The central orchestrator that ties together all Sentinel components:
- Signal routing (existing)
- Transaction cost modeling (TCM)
- Walk-forward validation (WFV)
- Regime-aware gating
- Risk budgeting
- Performance attribution

This creates a complete institutional-grade trading system that:
1. Validates strategies before they go live (WFV)
2. Models real costs (TCM)
3. Prevents wrong-regime trading (RegimeGate)
4. Manages risk (RiskBudget)
5. Tracks performance (Attribution)

Usage:
    from sentinel_integrator import SentinelIntegrator
    
    sentinel = SentinelIntegrator()
    
    # Process a batch of signals
    result = sentinel.process_signal_batch(signals, price_data)
    
    # Get approved signals with position sizes
    for signal in result['approved']:
        execute_trade(signal)
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

# Import our components
from sentinel_fund_strategy import SentinelFund, Signal, SignalStatus
from transaction_cost_model import TransactionCostModel
from walk_forward_validator import WalkForwardValidator
from regime_aware_gate import RegimeAwareGate, MarketRegime
from sentinel_config import RISK, GATES, PERFORMANCE, REGIME

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('SentinelIntegrator')


@dataclass
class ProcessedSignal:
    """Signal with full processing metadata"""
    # Original signal
    strategy_id: str
    symbol: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: float
    timestamp: datetime
    rr: float
    
    # Processing results
    status: str = "pending"
    book: str = "unknown"  # core, incubator, rejected
    position_size: float = 0.0
    
    # Gate results
    regime_check: Tuple[bool, str] = field(default_factory=lambda: (False, ""))
    cost_check: Tuple[bool, float] = field(default_factory=lambda: (False, 0.0))
    consensus_check: Tuple[bool, str] = field(default_factory=lambda: (False, ""))
    
    # Metadata
    net_expectancy: float = 0.0
    confidence_score: float = 0.0
    processing_notes: List[str] = field(default_factory=list)


class SentinelIntegrator:
    """
    Central orchestrator for the Sentinel Fund System
    
    Implements the complete institutional workflow:
    1. Regime Detection → Filter by market condition
    2. Walk-Forward Validation → Ensure strategy robustness
    3. Transaction Cost Model → Calculate true edge
    4. Signal Gating → RR, consensus, freshness
    5. Risk Budgeting → Position sizing
    6. Core/Incubator Routing → Capital allocation
    """
    
    def __init__(self):
        logger.info("Initializing Sentinel Integrator...")
        
        # Core components
        self.sentinel = SentinelFund()
        self.tcm = TransactionCostModel()
        self.wfv = WalkForwardValidator()
        self.regime_gate = RegimeAwareGate()
        
        # State
        self.current_regime: MarketRegime = MarketRegime.UNKNOWN
        self.last_regime_update: Optional[datetime] = None
        
        # Performance tracking
        self.daily_stats = {
            'signals_received': 0,
            'signals_approved': 0,
            'signals_incubator': 0,
            'signals_rejected': 0,
            'avg_cost_estimate': 0.0
        }
        
        logger.info("Sentinel Integrator initialized")
    
    def update_market_regime(self, prices: List[float], hurst: Optional[float] = None):
        """Update current market regime detection"""
        self.current_regime = self.regime_gate.get_current_regime(prices, hurst)
        self.last_regime_update = datetime.now()
        logger.info(f"Market regime updated: {self.current_regime.value}")
    
    def validate_strategy_robustness(
        self,
        strategy_id: str,
        trades: List[Dict]
    ) -> Dict[str, Any]:
        """
        Run walk-forward validation on a strategy
        
        Returns validation results and recommendation
        """
        results = self.wfv.validate_strategy(strategy_id, trades)
        
        return {
            'strategy_id': strategy_id,
            'is_robust': results.is_robust,
            'robustness_score': results.robustness_score,
            'recommendation': results.recommendation,
            'pass_rate': results.passed_windows / max(results.total_windows, 1),
            'avg_test_expectancy': results.avg_test_expectancy,
            'windows_evaluated': results.total_windows
        }
    
    def calculate_true_edge(
        self,
        signal: Signal,
        strategy_expectancy: float
    ) -> Tuple[float, float, bool]:
        """
        Calculate net expectancy after all costs
        
        Returns: (net_expectancy, total_cost, is_viable)
        """
        # Estimate trade size (would come from portfolio sizing in production)
        trade_size = 10000  # $10k default
        
        # Get cost estimate
        cost_estimate = self.tcm.estimate_cost(
            symbol=signal.symbol,
            trade_size_usd=trade_size,
            exchange="binance",
            order_type="taker"
        )
        
        # Calculate net expectancy
        # Assume round-trip (entry + exit)
        total_cost = cost_estimate.total_cost_percent * 2
        
        # Add funding cost estimate (1 day hold)
        funding_cost = 0.03  # 0.03% per day
        total_cost += funding_cost
        
        net_expectancy = strategy_expectancy - total_cost
        
        # Viability check
        is_viable = net_expectancy > 0.1  # Need at least 0.1% edge after costs
        
        return net_expectancy, total_cost, is_viable
    
    def process_signal(
        self,
        signal: Signal,
        strategy_expectancy: float = 0.5,
        skip_regime_check: bool = False
    ) -> ProcessedSignal:
        """
        Process a single signal through the complete pipeline
        """
        processed = ProcessedSignal(
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            direction=signal.direction,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            timestamp=signal.timestamp,
            rr=signal.rr
        )
        
        self.daily_stats['signals_received'] += 1
        
        # Step 1: Regime Check
        if not skip_regime_check:
            regime_ok, regime_reason = self.regime_gate.check_signal(
                signal.strategy_id,
                self.current_regime
            )
            processed.regime_check = (regime_ok, regime_reason)
            
            if not regime_ok:
                processed.status = "rejected"
                processed.book = "rejected"
                processed.processing_notes.append(f"Regime block: {regime_reason}")
                self.daily_stats['signals_rejected'] += 1
                return processed
        
        # Step 2: Calculate True Edge (TCM)
        net_exp, total_cost, is_viable = self.calculate_true_edge(signal, strategy_expectancy)
        processed.net_expectancy = net_exp
        processed.cost_check = (is_viable, total_cost)
        
        if not is_viable:
            processed.status = "rejected"
            processed.book = "rejected"
            processed.processing_notes.append(
                f"Cost block: Edge ({strategy_expectancy:.2f}%) consumed by costs ({total_cost:.2f}%)"
            )
            self.daily_stats['signals_rejected'] += 1
            return processed
        
        # Step 3: Run through Sentinel Fund (gates + sizing)
        status, position_size, reason = self.sentinel.process_signal(signal)
        
        processed.status = status.value
        processed.position_size = position_size
        processed.processing_notes.append(reason)
        
        # Determine book assignment
        if status == SignalStatus.APPROVED:
            processed.book = "core"
            self.daily_stats['signals_approved'] += 1
        elif status == SignalStatus.INCUBATOR:
            processed.book = "incubator"
            self.daily_stats['signals_incubator'] += 1
        else:
            processed.book = "rejected"
            self.daily_stats['signals_rejected'] += 1
        
        # Calculate confidence score
        processed.confidence_score = self._calculate_confidence(processed, signal)
        
        return processed
    
    def _calculate_confidence(
        self,
        processed: ProcessedSignal,
        signal: Signal
    ) -> float:
        """Calculate overall confidence score for a signal"""
        score = 0.0
        
        # RR contribution (0-30%)
        if signal.rr >= 2.0:
            score += 0.30
        elif signal.rr >= 1.5:
            score += 0.20
        elif signal.rr >= 1.0:
            score += 0.10
        
        # Consensus contribution (0-25%)
        consensus_count = len(signal.supporting_systems)
        score += min(consensus_count / 4, 0.25)
        
        # Cost-adjusted edge (0-25%)
        if processed.net_expectancy > 1.0:
            score += 0.25
        elif processed.net_expectancy > 0.5:
            score += 0.15
        elif processed.net_expectancy > 0.1:
            score += 0.05
        
        # Regime alignment (0-20%)
        if processed.regime_check[0]:
            score += 0.20
        
        return min(score, 1.0)
    
    def process_signal_batch(
        self,
        signals: List[Signal],
        price_data: Optional[List[float]] = None,
        strategy_expectancies: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Process a batch of signals
        
        Returns structured results with approved, incubator, and rejected signals
        """
        # Update regime if price data provided
        if price_data:
            self.update_market_regime(price_data)
        
        expectancies = strategy_expectancies or {}
        
        processed_signals = []
        
        for signal in signals:
            exp = expectancies.get(signal.strategy_id, 0.5)
            processed = self.process_signal(signal, exp)
            processed_signals.append(processed)
        
        # Categorize
        approved = [p for p in processed_signals if p.book == "core"]
        incubator = [p for p in processed_signals if p.book == "incubator"]
        rejected = [p for p in processed_signals if p.book == "rejected"]
        
        # Sort by confidence
        approved.sort(key=lambda x: x.confidence_score, reverse=True)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'market_regime': self.current_regime.value,
            'summary': {
                'total_signals': len(signals),
                'approved_core': len(approved),
                'incubator': len(incubator),
                'rejected': len(rejected),
                'approval_rate': len(approved) / len(signals) if signals else 0
            },
            'approved_signals': [self._signal_to_dict(s) for s in approved],
            'incubator_signals': [self._signal_to_dict(s) for s in incubator],
            'rejected_signals': [self._signal_to_dict(s) for s in rejected],
            'daily_stats': self.daily_stats.copy()
        }
    
    def _signal_to_dict(self, processed: ProcessedSignal) -> Dict[str, Any]:
        """Convert processed signal to dictionary"""
        return {
            'strategy_id': processed.strategy_id,
            'symbol': processed.symbol,
            'direction': processed.direction,
            'entry_price': processed.entry_price,
            'stop_loss': processed.stop_loss,
            'take_profit': processed.take_profit,
            'rr': processed.rr,
            'status': processed.status,
            'book': processed.book,
            'position_size': round(processed.position_size, 4),
            'net_expectancy': round(processed.net_expectancy, 4),
            'confidence_score': round(processed.confidence_score, 2),
            'regime_check': processed.regime_check[1],
            'cost_estimate': round(processed.cost_check[1], 4),
            'notes': processed.processing_notes
        }
    
    def generate_system_report(self) -> Dict[str, Any]:
        """Generate comprehensive system health report"""
        
        # Get portfolio summary
        portfolio = self.sentinel.get_portfolio_summary()
        
        # Get regime report
        regime_report = self.regime_gate.generate_regime_report()
        
        # TCM summary
        tcm_summary = {
            'exchanges_modeled': len(self.tcm.exchanges),
            'avg_cost_at_10k': self.tcm.estimate_cost("BTC-USDT", 10000).total_cost_percent
        }
        
        return {
            'report_time': datetime.now().isoformat(),
            'current_regime': self.current_regime.value,
            'portfolio_summary': portfolio,
            'regime_profiles': regime_report,
            'cost_model': tcm_summary,
            'daily_stats': self.daily_stats,
            'system_health': 'operational'
        }
    
    def run_strategy_audit(
        self,
        strategy_id: str,
        trade_history: List[Dict]
    ) -> Dict[str, Any]:
        """
        Complete audit of a strategy including:
        1. Walk-forward validation
        2. Transaction cost analysis
        3. Regime performance breakdown
        """
        # Walk-forward validation
        wfv_results = self.validate_strategy_robustness(strategy_id, trade_history)
        
        # TCM audit
        gross_exp = sum(t.get('pnl_percent', 0) for t in trade_history) / max(len(trade_history), 1)
        tcm_audit = self.tcm.audit_strategy_viability(
            strategy_id,
            gross_exp,
            len([t for t in trade_history if t.get('pnl_percent', 0) > 0]) / max(len(trade_history), 1),
            sample_size=len(trade_history)
        )
        
        # Regime analysis
        regime_profile = self.regime_gate.analyze_strategy_regimes(strategy_id, trade_history)
        
        # Final recommendation
        if not wfv_results['is_robust']:
            final_rec = "REJECT - Failed walk-forward validation"
        elif tcm_audit['recommendation'] in ['KILL', 'INCUBATOR_ONLY']:
            final_rec = f"REJECT - {tcm_audit['recommendation']}"
        elif len(regime_profile.avoided_regimes) > len(regime_profile.preferred_regimes):
            final_rec = "INCUBATOR - Poor regime adaptability"
        else:
            final_rec = "APPROVED - Passes all audits"
        
        return {
            'strategy_id': strategy_id,
            'walk_forward': wfv_results,
            'cost_analysis': tcm_audit,
            'regime_analysis': {
                'preferred_regimes': [r.value for r in regime_profile.preferred_regimes],
                'avoided_regimes': [r.value for r in regime_profile.avoided_regimes],
                'performance_by_regime': {
                    r.value: {
                        'trades': p.total_trades,
                        'win_rate': p.win_rate,
                        'expectancy': p.expectancy
                    }
                    for r, p in regime_profile.regime_performance.items()
                }
            },
            'final_recommendation': final_rec
        }


# Example usage
if __name__ == "__main__":
    print("=" * 100)
    print("SENTINEL INTEGRATOR - Complete System Demo")
    print("=" * 100)
    
    sentinel = SentinelIntegrator()
    
    # Set market regime
    import random
    prices = [50000 + random.gauss(0, 500) for _ in range(100)]
    sentinel.update_market_regime(prices)
    
    # Create test signals
    test_signals = [
        Signal(
            strategy_id="funding_carry",
            symbol="BTC-USDT",
            direction="short",
            entry_price=65000,
            stop_loss=66500,
            take_profit=62000,
            timestamp=datetime.now(),
            supporting_systems=["funding_carry", "volume_profile_value_area"],
            confidence=0.75
        ),
        Signal(
            strategy_id="hurst_regime_adaptive",
            symbol="ETH-USDT",
            direction="long",
            entry_price=3500,
            stop_loss=3400,
            take_profit=3700,
            timestamp=datetime.now(),
            supporting_systems=["hurst_regime_adaptive", "adaptive_vr_confluence"],
            confidence=0.70
        ),
        Signal(
            strategy_id="autocorrelation_exploiter",
            symbol="SOL-USDT",
            direction="long",
            entry_price=150,
            stop_loss=145,
            take_profit=160,
            timestamp=datetime.now(),
            supporting_systems=["autocorrelation_exploiter"],
            confidence=0.55
        ),
        Signal(
            strategy_id="ema_crossover",
            symbol="ADA-USDT",
            direction="long",
            entry_price=0.50,
            stop_loss=0.48,
            take_profit=0.55,
            timestamp=datetime.now(),
            supporting_systems=["ema_crossover"],
            confidence=0.40
        ),
    ]
    
    # Strategy expectancies
    expectancies = {
        'funding_carry': 1.61,
        'hurst_regime_adaptive': 0.95,
        'autocorrelation_exploiter': 1.20,
        'ema_crossover': -0.05
    }
    
    # Process batch
    print("\n[CHART] Processing Signal Batch...")
    print("-" * 100)
    
    result = sentinel.process_signal_batch(test_signals, prices, expectancies)
    
    print(f"\nMarket Regime: {result['market_regime'].upper()}")
    print(f"\nSummary:")
    print(f"  Total Signals: {result['summary']['total_signals']}")
    print(f"  Approved (Core): {result['summary']['approved_core']}")
    print(f"  Incubator: {result['summary']['incubator']}")
    print(f"  Rejected: {result['summary']['rejected']}")
    print(f"  Approval Rate: {result['summary']['approval_rate']:.1%}")
    
    print(f"\n[OK] APPROVED SIGNALS ({len(result['approved_signals'])}):")
    print("-" * 100)
    for sig in result['approved_signals']:
        print(f"\n{sig['strategy_id']} {sig['direction']} {sig['symbol']}")
        print(f"  Position Size: {sig['position_size']:.2%}")
        print(f"  Net Expectancy: {sig['net_expectancy']:.2f}%")
        print(f"  Confidence: {sig['confidence_score']:.0%}")
        print(f"  Notes: {', '.join(sig['notes'])}")
    
    print(f"\n[!] INCUBATOR SIGNALS ({len(result['incubator_signals'])}):")
    print("-" * 100)
    for sig in result['incubator_signals']:
        print(f"  {sig['strategy_id']} - {', '.join(sig['notes'])}")
    
    print(f"\n[NO] REJECTED SIGNALS ({len(result['rejected_signals'])}):")
    print("-" * 100)
    for sig in result['rejected_signals']:
        print(f"  {sig['strategy_id']} - {', '.join(sig['notes'])}")
    
    print("\n" + "=" * 100)
