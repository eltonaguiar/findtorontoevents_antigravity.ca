#!/usr/bin/env python3
"""
Integration Module - Connects new implementations with existing infrastructure
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SignalAggregatorIntegrations:
    """
    Integrates new components with existing signal aggregator infrastructure.
    """
    
    def __init__(self):
        self.forward_testing = None
        self.adaptive_tpsl = None
        self.position_sizer = None
        self.circuit_breakers = None
        
    def initialize_forward_testing(self):
        """Initialize forward testing integration."""
        try:
            from forward_testing.adaptive_tpsl import AdaptiveTPSL, MarketRegime
            from forward_testing.forward_database import ForwardTestDatabase
            
            self.adaptive_tpsl = AdaptiveTPSL()
            self.forward_db = ForwardTestDatabase()
            logger.info("Forward testing integration initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize forward testing: {e}")
            return False
    
    def initialize_risk_management(self):
        """Initialize risk management integration."""
        try:
            from risk_management.position_sizer import PositionSizer
            from circuit_breaker_system import CircuitBreakerSystem
            
            self.position_sizer = PositionSizer()
            self.circuit_breakers = CircuitBreakerSystem()
            logger.info("Risk management integration initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize risk management: {e}")
            return False
    
    def enhance_signal_with_adaptive_tpsl(
        self,
        signal: Dict,
        price_data: 'pd.DataFrame',
        regime: Optional[str] = None
    ) -> Dict:
        """
        Enhance signal with adaptive TP/SL levels.
        
        Args:
            signal: Original signal dict
            price_data: Price DataFrame for ATR calculation
            regime: Market regime (BULL, BEAR, SIDEWAYS, HIGH_VOL)
            
        Returns:
            Enhanced signal with adaptive TP/SL
        """
        if self.adaptive_tpsl is None:
            self.initialize_forward_testing()
        
        try:
            from forward_testing.adaptive_tpsl import MarketRegime
            
            # Map regime string to enum
            regime_map = {
                'bull': MarketRegime.BULL,
                'bear': MarketRegime.BEAR,
                'sideways': MarketRegime.SIDEWAYS,
                'high_vol': MarketRegime.HIGH_VOL
            }
            regime_enum = regime_map.get(regime.lower(), MarketRegime.SIDEWAYS) if regime else None
            
            # Calculate adaptive TP/SL
            tpsl_config = self.adaptive_tpsl.calculate_tpsl(
                entry_price=signal['entry_price'],
                direction=signal['direction'],
                df=price_data,
                regime=regime_enum
            )
            
            # Enhance signal
            enhanced = signal.copy()
            enhanced['tp_price'] = tpsl_config['tp_price']
            enhanced['sl_price'] = tpsl_config['sl_price']
            enhanced['atr'] = tpsl_config['atr']
            enhanced['partial_tp_levels'] = tpsl_config['partial_tp_levels']
            enhanced['partial_tp_percentages'] = tpsl_config['partial_tp_percentages']
            enhanced['trailing_activation'] = tpsl_config['trailing_activation']
            enhanced['max_holding_bars'] = tpsl_config['max_holding_bars']
            enhanced['risk_reward_ratio'] = tpsl_config['risk_reward_ratio']
            enhanced['regime'] = tpsl_config['regime']
            
            logger.info(f"Enhanced {signal['symbol']} with adaptive TP/SL (R:R {tpsl_config['risk_reward_ratio']:.2f})")
            return enhanced
            
        except Exception as e:
            logger.error(f"Failed to enhance signal with TP/SL: {e}")
            return signal
    
    def calculate_position_size_with_risk_controls(
        self,
        signal: Dict,
        portfolio_value: float,
        win_rate: float = 0.55,
        avg_win: float = 0.03,
        avg_loss: float = 0.02,
        current_volatility: float = 0.25
    ) -> Dict:
        """
        Calculate position size with Kelly criterion and volatility adjustment.
        
        Args:
            signal: Signal dict with entry_price and stop_loss
            portfolio_value: Total portfolio value
            win_rate: Historical win rate
            avg_win: Average win percentage
            avg_loss: Average loss percentage
            current_volatility: Current market volatility
            
        Returns:
            Position sizing recommendation
        """
        if self.position_sizer is None:
            self.initialize_risk_management()
        
        try:
            sizing = self.position_sizer.calculate_position_size(
                portfolio_value=portfolio_value,
                entry_price=signal['entry_price'],
                stop_loss=signal['sl_price'],
                win_rate=win_rate,
                avg_win=avg_win,
                avg_loss=avg_loss,
                current_volatility=current_volatility
            )
            
            # Check circuit breakers
            portfolio_state = {
                'equity': portfolio_value,
                'daily_pnl_pct': 0,  # Would be calculated from actual P&L
                'consecutive_losses': 0,  # Would be tracked
                'current_atr': signal.get('atr', 0),
                'avg_atr': signal.get('atr', 0),
                'correlations': []
            }
            
            breaker_result = self.circuit_breakers.check_all(portfolio_state)
            
            # Apply circuit breaker constraints
            if breaker_result['position_size_multiplier'] < 1.0:
                original_pct = sizing['position_pct']
                sizing['position_pct'] *= breaker_result['position_size_multiplier']
                sizing['quantity'] *= breaker_result['position_size_multiplier']
                sizing['position_value'] *= breaker_result['position_size_multiplier']
                sizing['circuit_breaker_applied'] = True
                sizing['original_position_pct'] = original_pct
                logger.warning(f"Circuit breaker reduced position from {original_pct:.2%} to {sizing['position_pct']:.2%}")
            
            sizing['circuit_breakers'] = breaker_result
            sizing['trading_enabled'] = breaker_result['trading_enabled']
            
            return sizing
            
        except Exception as e:
            logger.error(f"Failed to calculate position size: {e}")
            return {'error': str(e)}
    
    def record_forward_test_signal(self, signal: Dict, system: str) -> bool:
        """
        Record signal in forward testing database.
        
        Args:
            signal: Signal to record
            system: Source system name
            
        Returns:
            True if recorded successfully
        """
        if self.forward_db is None:
            self.initialize_forward_testing()
        
        try:
            self.forward_db.add_position({
                'id': signal.get('id', f"{signal['symbol']}_{signal.get('timestamp', '')}"),
                'system': system,
                'symbol': signal['symbol'],
                'direction': signal['direction'],
                'entry_price': signal['entry_price'],
                'tp_price': signal.get('tp_price'),
                'sl_price': signal.get('sl_price'),
                'regime': signal.get('regime', 'UNKNOWN'),
                'atr': signal.get('atr', 0)
            })
            return True
        except Exception as e:
            logger.error(f"Failed to record forward test signal: {e}")
            return False


class EnhancedSignalAggregator:
    """
    Enhanced signal aggregator that integrates with existing infrastructure.
    """
    
    def __init__(self):
        # Import existing aggregator
        from signal_aggregator.aggregator import SignalAggregator
        from signal_aggregator.confidence_calculator import BayesianConfidenceCalculator
        from signal_aggregator.system_registry import SystemRegistry
        
        self.base_aggregator = SignalAggregator()
        self.confidence_calc = BayesianConfidenceCalculator()
        self.system_registry = SystemRegistry()
        self.integrations = SignalAggregatorIntegrations()
        
        # Initialize integrations
        self.integrations.initialize_forward_testing()
        self.integrations.initialize_risk_management()
    
    async def aggregate_with_enhancements(
        self,
        price_data: Optional['pd.DataFrame'] = None,
        regime: Optional[str] = None,
        portfolio_value: float = 100000
    ) -> Dict:
        """
        Run aggregation with all enhancements.
        
        Args:
            price_data: Price data for ATR calculations
            regime: Current market regime
            portfolio_value: Current portfolio value
            
        Returns:
            Enhanced consensus signals with TP/SL and position sizing
        """
        import asyncio
        
        # Run base aggregation
        consensus = await self.base_aggregator.aggregate_all_signals()
        
        enhanced_signals = {}
        
        for symbol, consensus_signal in consensus.items():
            try:
                # Get best signal from agreeing systems
                best_signal = max(
                    consensus_signal.signals,
                    key=lambda s: s.confidence
                )
                
                signal_dict = {
                    'symbol': best_signal.symbol,
                    'direction': best_signal.direction.value,
                    'entry_price': best_signal.entry_price,
                    'confidence': best_signal.confidence,
                    'system': best_signal.system
                }
                
                # Enhance with adaptive TP/SL if price data available
                if price_data is not None:
                    signal_dict = self.integrations.enhance_signal_with_adaptive_tpsl(
                        signal_dict, price_data, regime
                    )
                
                # Calculate position size
                sizing = self.integrations.calculate_position_size_with_risk_controls(
                    signal_dict, portfolio_value
                )
                
                signal_dict['position_sizing'] = sizing
                
                # Record for forward testing
                self.integrations.record_forward_test_signal(signal_dict, 'aggregated')
                
                # Update system registry
                self.system_registry.update_system_status(
                    signal_dict['system'],
                    'active',
                    signal_count=1
                )
                
                enhanced_signals[symbol] = signal_dict
                
            except Exception as e:
                logger.error(f"Error enhancing signal for {symbol}: {e}")
                continue
        
        return enhanced_signals


def integrate_with_existing_hub():
    """
    Integration helper to connect with existing hub dashboard.
    """
    try:
        from signal_aggregator.system_registry import SystemRegistry
        
        registry = SystemRegistry()
        dashboard_data = registry.generate_dashboard_data()
        
        # Add forward testing metrics
        try:
            from forward_testing.forward_database import ForwardTestDatabase
            forward_db = ForwardTestDatabase()
            forward_stats = forward_db.get_performance_summary(days=30)
            dashboard_data['forward_testing'] = forward_stats
        except Exception as e:
            logger.warning(f"Could not add forward testing metrics: {e}")
        
        # Save to hub data directory
        import json
        from pathlib import Path
        
        hub_data_dir = Path('hub/data')
        hub_data_dir.mkdir(exist_ok=True)
        
        with open(hub_data_dir / 'integrated_dashboard.json', 'w') as f:
            json.dump(dashboard_data, f, indent=2, default=str)
        
        logger.info("Integrated dashboard data saved to hub")
        return True
        
    except Exception as e:
        logger.error(f"Integration with hub failed: {e}")
        return False


if __name__ == "__main__":
    print("Signal Aggregator Integrations")
    print("=" * 60)
    
    # Test integration initialization
    integrations = SignalAggregatorIntegrations()
    
    forward_ok = integrations.initialize_forward_testing()
    risk_ok = integrations.initialize_risk_management()
    
    print(f"\nForward Testing: {'✓ Ready' if forward_ok else '✗ Failed'}")
    print(f"Risk Management: {'✓ Ready' if risk_ok else '✗ Failed'}")
    
    # Test hub integration
    hub_ok = integrate_with_existing_hub()
    print(f"Hub Integration: {'✓ Ready' if hub_ok else '✗ Failed'}")
