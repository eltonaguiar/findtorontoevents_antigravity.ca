"""
Smart Execution Strategy
Implements institutional-grade execution algorithms
- TWAP, VWAP, and adaptive execution
- Market impact modeling
- Optimal order routing
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import logging


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    IOC = "ioc"  # Immediate or cancel
    FOK = "fok"  # Fill or kill


class ExecutionAlgorithm(Enum):
    TWAP = "twap"
    VWAP = "vwap"
    POV = "pov"  # Percent of volume
    ADAPTIVE = "adaptive"


@dataclass
class Order:
    symbol: str
    side: str  # 'BUY' or 'SELL'
    quantity: float
    order_type: OrderType
    limit_price: Optional[float] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class Fill:
    order_id: str
    symbol: str
    side: str
    filled_quantity: float
    fill_price: float
    timestamp: datetime
    venue: str
    slippage_bps: float


class MarketImpactModel:
    """
    Almgren-Chriss style market impact model
    """
    
    def __init__(self, 
                 permanent_impact_coef: float = 1.0,
                 temporary_impact_coef: float = 0.5,
                 decay_rate: float = 0.1):
        self.permanent_coef = permanent_impact_coef
        self.temporary_coef = temporary_impact_coef
        self.decay_rate = decay_rate
        
    def estimate_impact(self, 
                        order_size: float,
                        daily_volume: float,
                        volatility: float,
                        spread: float,
                        urgency: str = 'medium') -> Dict:
        """
        Estimate market impact in basis points
        
        Args:
            order_size: Number of shares/contracts
            daily_volume: Average daily volume
            volatility: Annualized volatility (decimal)
            spread: Bid-ask spread (decimal)
            urgency: 'low', 'medium', 'high'
        
        Returns:
            Dict with temporary, permanent, and total impact
        """
        # Participation rate
        participation = order_size / daily_volume
        
        # Urgency multiplier
        urgency_mult = {'low': 0.7, 'medium': 1.0, 'high': 1.5}[urgency]
        
        # Temporary impact (trading cost)
        temp_impact = (self.temporary_coef * spread * urgency_mult + 
                      0.5 * volatility * np.sqrt(participation))
        
        # Permanent impact (information leakage)
        perm_impact = self.permanent_coef * volatility * (participation ** 0.6)
        
        return {
            'temporary_bps': temp_impact * 10000,
            'permanent_bps': perm_impact * 10000,
            'total_bps': (temp_impact + perm_impact) * 10000,
            'participation_rate': participation
        }
    
    def optimal_execution_time(self,
                               order_size: float,
                               daily_volume: float,
                               alpha_decay: float = 0.1) -> int:
        """
        Calculate optimal execution time horizon
        
        Balances:
        - Market impact (decreases with longer horizon)
        - Alpha decay (increases with longer horizon)
        """
        # Base time in periods
        base_periods = int((order_size / daily_volume) * 390)  # Trading minutes
        
        # Adjust for alpha decay
        if alpha_decay > 0.2:  # Fast alpha decay
            optimal_periods = max(1, int(base_periods * 0.5))
        elif alpha_decay > 0.1:  # Medium decay
            optimal_periods = base_periods
        else:  # Slow decay
            optimal_periods = min(390, int(base_periods * 2))
        
        return optimal_periods


class LiquidityForecaster:
    """
    Forecast liquidity for execution planning
    """
    
    def __init__(self):
        self.intraday_pattern = self._load_intraday_pattern()
        self.day_of_week_effect = {
            0: 1.05,  # Monday
            1: 1.0,   # Tuesday
            2: 1.0,   # Wednesday
            3: 1.0,   # Thursday
            4: 1.15,  # Friday
            5: 0.3,   # Saturday (crypto)
            6: 0.4    # Sunday (crypto)
        }
    
    def _load_intraday_pattern(self) -> Dict[int, float]:
        """Load typical intraday volume profile"""
        # Hour of day -> % of daily volume
        return {
            0: 0.02, 1: 0.02, 2: 0.02, 3: 0.02, 4: 0.02,  # Night
            5: 0.03, 6: 0.04, 7: 0.06, 8: 0.08,          # Pre-market
            9: 0.12, 10: 0.10, 11: 0.08,                 # Morning
            12: 0.06, 13: 0.08, 14: 0.09, 15: 0.10,     # Afternoon
            16: 0.04, 17: 0.03, 18: 0.02, 19: 0.02,     # After hours
            20: 0.02, 21: 0.02, 22: 0.02, 23: 0.02      # Night
        }
    
    def predict_volume(self, 
                       timestamp: datetime,
                       base_daily_volume: float,
                       recent_volume: Optional[float] = None) -> float:
        """
        Predict volume for a given time period
        """
        hour = timestamp.hour
        dow = timestamp.weekday()
        
        # Base prediction from intraday pattern
        hour_pct = self.intraday_pattern.get(hour, 0.04)
        dow_mult = self.day_of_week_effect.get(dow, 1.0)
        
        predicted = base_daily_volume * hour_pct * dow_mult
        
        # Adjust based on recent realized volume
        if recent_volume is not None:
            expected_so_far = base_daily_volume * sum(
                self.intraday_pattern.get(h, 0.04) 
                for h in range(hour)
            )
            if expected_so_far > 0:
                adjustment = recent_volume / expected_so_far
                predicted *= max(0.8, min(1.2, adjustment))
        
        return predicted
    
    def predict_spread(self,
                       timestamp: datetime,
                       base_spread: float,
                       volatility: float) -> float:
        """
        Predict bid-ask spread
        """
        hour = timestamp.hour
        
        # Time of day effect
        if hour in [9, 16]:  # Open/close
            tod_mult = 1.5
        elif hour in [12, 13]:  # Lunch
            tod_mult = 1.2
        else:
            tod_mult = 1.0
        
        # Volatility component
        vol_component = volatility * 0.5  # Half-spread approximation
        
        return base_spread * tod_mult + vol_component


class TWAPStrategy:
    """
    Time-Weighted Average Price execution
    """
    
    def __init__(self, 
                 symbol: str,
                 total_quantity: float,
                 duration_minutes: int,
                 num_slices: Optional[int] = None,
                 side: str = 'BUY'):
        
        self.symbol = symbol
        self.total_quantity = total_quantity
        self.duration = duration_minutes
        self.side = side
        self.num_slices = num_slices or max(1, duration_minutes // 5)
        
        self.quantity_per_slice = total_quantity / self.num_slices
        self.interval_minutes = duration_minutes / self.num_slices
        
        self.fills: List[Fill] = []
        self.remaining = total_quantity
        
    def generate_schedule(self) -> List[Dict]:
        """Generate execution schedule"""
        schedule = []
        for i in range(self.num_slices):
            schedule.append({
                'slice': i + 1,
                'quantity': self.quantity_per_slice,
                'target_time': i * self.interval_minutes,
                'order_type': OrderType.LIMIT  # Default to limit orders
            })
        return schedule
    
    def execute_slice(self, 
                      slice_info: Dict,
                      market_data: pd.DataFrame,
                      price_tolerance: float = 0.001) -> Optional[Fill]:
        """
        Execute a single slice
        
        In live trading, this would place actual orders
        In backtest, simulates execution
        """
        current_price = market_data['close'].iloc[-1]
        
        # Determine order type based on market conditions
        spread = market_data.get('spread', pd.Series([0.001])).iloc[-1]
        
        if spread < price_tolerance:
            order_type = OrderType.MARKET
            fill_price = current_price
        else:
            order_type = OrderType.LIMIT
            if self.side == 'BUY':
                fill_price = current_price * (1 - spread * 0.5)
            else:
                fill_price = current_price * (1 + spread * 0.5)
        
        # Simulate fill
        fill = Fill(
            order_id=f"twap_{slice_info['slice']}",
            symbol=self.symbol,
            side=self.side,
            filled_quantity=slice_info['quantity'],
            fill_price=fill_price,
            timestamp=datetime.now(),
            venue='simulated',
            slippage_bps=0  # Calculate later
        )
        
        self.fills.append(fill)
        self.remaining -= slice_info['quantity']
        
        return fill
    
    def get_vwap(self) -> float:
        """Calculate executed VWAP"""
        if not self.fills:
            return 0
        
        total_value = sum(f.fill_price * f.filled_quantity for f in self.fills)
        total_qty = sum(f.filled_quantity for f in self.fills)
        
        return total_value / total_qty if total_qty > 0 else 0


class VWAPStrategy:
    """
    Volume-Weighted Average Price execution
    """
    
    def __init__(self,
                 symbol: str,
                 total_quantity: float,
                 duration_minutes: int,
                 side: str = 'BUY',
                 volume_profile: Optional[Dict] = None):
        
        self.symbol = symbol
        self.total_quantity = total_quantity
        self.duration = duration_minutes
        self.side = side
        self.volume_profile = volume_profile or self._default_volume_profile()
        
        self.fills: List[Fill] = []
        self.remaining = total_quantity
        
    def _default_volume_profile(self) -> Dict[int, float]:
        """Default intraday volume profile"""
        return {
            0: 0.02, 1: 0.02, 2: 0.02, 3: 0.02, 4: 0.02,
            5: 0.03, 6: 0.04, 7: 0.06, 8: 0.08,
            9: 0.12, 10: 0.10, 11: 0.08,
            12: 0.06, 13: 0.08, 14: 0.09, 15: 0.10,
            16: 0.04, 17: 0.03, 18: 0.02, 19: 0.02,
            20: 0.02, 21: 0.02, 22: 0.02, 23: 0.02
        }
    
    def generate_schedule(self, current_hour: int = 9) -> List[Dict]:
        """Generate volume-based execution schedule"""
        schedule = []
        remaining_hours = self.duration // 60
        
        # Get volume weights for remaining periods
        total_weight = sum(
            self.volume_profile.get((current_hour + i) % 24, 0.04)
            for i in range(remaining_hours + 1)
        )
        
        for i in range(remaining_hours + 1):
            hour = (current_hour + i) % 24
            weight = self.volume_profile.get(hour, 0.04) / total_weight
            quantity = self.total_quantity * weight
            
            schedule.append({
                'hour': hour,
                'quantity': quantity,
                'weight': weight
            })
        
        return schedule
    
    def get_vwap(self) -> float:
        """Calculate executed VWAP"""
        if not self.fills:
            return 0
        
        total_value = sum(f.fill_price * f.filled_quantity for f in self.fills)
        total_qty = sum(f.filled_quantity for f in self.fills)
        
        return total_value / total_qty if total_qty > 0 else 0


class SmartExecutionStrategy:
    """
    Adaptive execution strategy that selects optimal algorithm
    based on order characteristics and market conditions
    """
    
    def __init__(self,
                 symbol: str,
                 capital: float = 10000,
                 default_algorithm: ExecutionAlgorithm = ExecutionAlgorithm.VWAP):
        
        self.symbol = symbol
        self.capital = capital
        self.default_algorithm = default_algorithm
        
        self.impact_model = MarketImpactModel()
        self.liquidity_forecaster = LiquidityForecaster()
        
        self.execution_history: List[Dict] = []
        
    def select_algorithm(self,
                         order_size: float,
                         daily_volume: float,
                         urgency: str = 'medium',
                         alpha_half_life: Optional[float] = None) -> ExecutionAlgorithm:
        """
        Select best execution algorithm based on order characteristics
        
        Args:
            order_size: Shares/contracts to trade
            daily_volume: Average daily volume
            urgency: 'low', 'medium', 'high'
            alpha_half_life: Time until alpha decays by half (minutes)
        """
        participation = order_size / daily_volume if daily_volume > 0 else 1
        
        # Decision tree for algorithm selection
        if participation < 0.01 and urgency == 'high':
            # Small order, urgent - just execute
            return ExecutionAlgorithm.ADAPTIVE
        
        elif participation < 0.05:
            # Small order - TWAP is fine
            return ExecutionAlgorithm.TWAP
        
        elif participation < 0.15:
            # Medium order - VWAP tracks benchmark
            return ExecutionAlgorithm.VWAP
        
        elif alpha_half_life and alpha_half_life < 30:
            # Large order with fast alpha - execute quickly
            return ExecutionAlgorithm.ADAPTIVE
        
        else:
            # Large order, no urgency - POV to blend in
            return ExecutionAlgorithm.POV
    
    def execute_order(self,
                      order: Order,
                      market_data: pd.DataFrame,
                      urgency: str = 'medium') -> Dict:
        """
        Execute order using optimal strategy
        """
        # Estimate market impact
        daily_volume = market_data['volume'].rolling(20).mean().iloc[-1]
        volatility = market_data['close'].pct_change().rolling(20).std().iloc[-1] * np.sqrt(365)
        spread = (market_data['ask'].iloc[-1] - market_data['bid'].iloc[-1]) / market_data['close'].iloc[-1] if 'bid' in market_data.columns else 0.001
        
        impact_estimate = self.impact_model.estimate_impact(
            order.quantity,
            daily_volume,
            volatility,
            spread,
            urgency
        )
        
        # Select algorithm
        algorithm = self.select_algorithm(
            order.quantity,
            daily_volume,
            urgency
        )
        
        # Execute based on algorithm
        if algorithm == ExecutionAlgorithm.TWAP:
            executor = TWAPStrategy(
                order.symbol,
                order.quantity,
                duration_minutes=60,
                side=order.side
            )
        elif algorithm == ExecutionAlgorithm.VWAP:
            executor = VWAPStrategy(
                order.symbol,
                order.quantity,
                duration_minutes=60,
                side=order.side
            )
        else:
            # Adaptive - use aggressive execution
            executor = TWAPStrategy(
                order.symbol,
                order.quantity,
                duration_minutes=15,  # Faster
                side=order.side
            )
        
        # Record execution
        execution_record = {
            'order': order,
            'algorithm': algorithm.value,
            'impact_estimate': impact_estimate,
            'executor': executor,
            'timestamp': datetime.now()
        }
        
        self.execution_history.append(execution_record)
        
        return execution_record
    
    def analyze_execution_quality(self) -> Dict:
        """
        Analyze historical execution quality
        """
        if not self.execution_history:
            return {}
        
        analysis = {
            'total_orders': len(self.execution_history),
            'algorithm_distribution': {},
            'avg_participation_rate': 0,
            'avg_estimated_impact_bps': 0
        }
        
        algo_counts = {}
        total_participation = 0
        total_impact = 0
        
        for record in self.execution_history:
            algo = record['algorithm']
            algo_counts[algo] = algo_counts.get(algo, 0) + 1
            
            impact = record['impact_estimate']
            total_participation += impact.get('participation_rate', 0)
            total_impact += impact.get('total_bps', 0)
        
        analysis['algorithm_distribution'] = {
            algo: count / len(self.execution_history) 
            for algo, count in algo_counts.items()
        }
        
        analysis['avg_participation_rate'] = total_participation / len(self.execution_history)
        analysis['avg_estimated_impact_bps'] = total_impact / len(self.execution_history)
        
        return analysis


# Convenience function
def create_smart_execution(symbol: str, capital: float = 10000) -> SmartExecutionStrategy:
    """Create configured smart execution strategy"""
    return SmartExecutionStrategy(
        symbol=symbol,
        capital=capital,
        default_algorithm=ExecutionAlgorithm.VWAP
    )


if __name__ == "__main__":
    print("Smart Execution Strategy - Example Usage")
    print("=" * 50)
    
    # Example: Execute large BTC order
    strategy = create_smart_execution("BTC-USD", capital=100000)
    
    # Create order
    order = Order(
        symbol="BTC-USD",
        side="BUY",
        quantity=1.5,  # BTC
        order_type=OrderType.LIMIT
    )
    
    print(f"\nOrder Details:")
    print(f"  Symbol: {order.symbol}")
    print(f"  Side: {order.side}")
    print(f"  Quantity: {order.quantity}")
    
    # Estimate impact
    impact = strategy.impact_model.estimate_impact(
        order_size=order.quantity,
        daily_volume=50000,  # BTC daily volume
        volatility=0.8,      # 80% annualized
        spread=0.0005,       # 5 bps spread
        urgency='medium'
    )
    
    print(f"\nMarket Impact Estimate:")
    print(f"  Participation Rate: {impact['participation_rate']*100:.3f}%")
    print(f"  Temporary Impact: {impact['temporary_bps']:.2f} bps")
    print(f"  Permanent Impact: {impact['permanent_bps']:.2f} bps")
    print(f"  Total Impact: {impact['total_bps']:.2f} bps")
    
    # Select algorithm
    algo = strategy.select_algorithm(
        order.quantity,
        50000,
        urgency='medium'
    )
    print(f"\nRecommended Algorithm: {algo.value.upper()}")
