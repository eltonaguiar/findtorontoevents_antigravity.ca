"""
Base Strategy Class for Professional-Grade Trading Strategies
Includes institutional risk controls, transaction cost modeling, and validation framework.
"""

import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import logging
import json
import os
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class SignalType(Enum):
    LONG = 1
    SHORT = -1
    NEUTRAL = 0

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

@dataclass
class Trade:
    """Represents a single trade"""
    entry_time: datetime
    exit_time: Optional[datetime]
    symbol: str
    signal: SignalType
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    pnl: float
    pnl_pct: float
    commission: float
    slippage: float
    strategy_name: str
    trade_id: str
    metadata: Dict[str, Any]

@dataclass
class Position:
    """Represents a current position"""
    symbol: str
    signal: SignalType
    entry_price: float
    quantity: float
    entry_time: datetime
    stop_loss: Optional[float]
    take_profit: Optional[float]
    unrealized_pnl: float
    unrealized_pnl_pct: float
    strategy_name: str

@dataclass
class StrategyConfig:
    """Configuration for strategy parameters"""
    # Risk management
    max_position_size: float = 0.05  # Max 5% of portfolio per position
    max_daily_loss: float = 0.02     # Max 2% daily loss
    max_drawdown_limit: float = 0.20 # Max 20% drawdown
    max_correlation: float = 0.7     # Max correlation between positions
    
    # Transaction costs
    commission_per_trade: float = 0.001  # 0.1% per trade
    slippage_model: str = "linear"       # slippage model
    min_slippage: float = 0.0001         # 1 bps minimum slippage
    
    # Strategy-specific parameters (to be overridden)
    lookback_period: int = 252           # Default 1 year lookback
    rebalance_freq: str = "daily"        # Rebalancing frequency
    
    # Validation
    min_trades_for_significance: int = 30
    required_confidence_level: float = 0.95

class BaseStrategy(ABC):
    """
    Abstract base class for all professional trading strategies.
    Provides common functionality for risk management, transaction costs,
    and performance tracking.
    """
    
    def __init__(self, name: str, config: StrategyConfig = None):
        self.name = name
        self.config = config or StrategyConfig()
        self.trades: List[Trade] = []
        self.positions: Dict[str, Position] = {}  # symbol -> Position
        self.portfolio_value: float = 100000.0  # Starting portfolio value
        self.daily_pnl: float = 0.0
        self.max_portfolio_value: float = self.portfolio_value
        self.current_drawdown: float = 0.0
        
        # Performance tracking
        self.equity_curve: List[Tuple[datetime, float]] = []
        self.returns: List[float] = []
        
        # Setup logging
        self.logger = logging.getLogger(f"{__name__}.{name}")
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate strategy configuration"""
        if self.config.max_position_size <= 0 or self.config.max_position_size > 1:
            raise ValueError("max_position_size must be between 0 and 1")
        if self.config.max_daily_loss <= 0 or self.config.max_daily_loss > 1:
            raise ValueError("max_daily_loss must be between 0 and 1")
        if self.config.max_drawdown_limit <= 0 or self.config.max_drawdown_limit > 1:
            raise ValueError("max_drawdown_limit must be between 0 and 1")
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame, timestamp: datetime) -> Dict[str, SignalType]:
        """
        Generate trading signals for given data at timestamp.
        Must be implemented by subclasses.
        
        Args:
            data: DataFrame with market data (OHLCV, indicators, etc.)
            timestamp: Current timestamp for signal generation
            
        Returns:
            Dictionary mapping symbol to SignalType
        """
        pass
    
    @abstractmethod
    def calculate_position_size(self, symbol: str, signal: SignalType, 
                              data: pd.DataFrame, timestamp: datetime) -> float:
        """
        Calculate position size for a given signal.
        Must be implemented by subclasses.
        
        Args:
            symbol: Trading symbol
            signal: Signal type (LONG/SHORT)
            data: Market data
            timestamp: Current timestamp
            
        Returns:
            Position size as fraction of portfolio (0.0 to 1.0)
        """
        pass
    
    def update_portfolio(self, market_data: pd.DataFrame, timestamp: datetime):
        """
        Update portfolio values based on current market data.
        Should be called before generating new signals.
        
        Args:
            market_data: Current market data for all symbols
            timestamp: Current timestamp
        """
        # Update unrealized PnL for existing positions
        total_unrealized = 0.0
        
        for symbol, position in self.positions.items():
            if symbol in market_data.index:
                current_price = market_data.loc[symbol, 'close']
                
                if position.signal == SignalType.LONG:
                    price_change = (current_price - position.entry_price) / position.entry_price
                else:  # SHORT
                    price_change = (position.entry_price - current_price) / position.entry_price
                
                position.unrealized_pnl = price_change * position.quantity * position.entry_price
                position.unrealized_pnl_pct = price_change
                total_unrealized += position.unrealized_pnl
        
        # Update portfolio value
        self.portfolio_value += total_unrealized
        
        # Update equity curve
        self.equity_curve.append((timestamp, self.portfolio_value))
        
        # Update drawdown
        if self.portfolio_value > self.max_portfolio_value:
            self.max_portfolio_value = self.portfolio_value
        
        self.current_drawdown = (self.max_portfolio_value - self.portfolio_value) / self.max_portfolio_value
        
        # Reset daily PnL at day start (simplified)
        if len(self.equity_curve) > 1:
            prev_date = self.equity_curve[-2][0].date()
            curr_date = timestamp.date()
            if prev_date != curr_date:
                self.daily_pnl = 0.0
    
    def check_risk_limits(self) -> Tuple[bool, List[str]]:
        """
        Check if current portfolio violates any risk limits.
        
        Returns:
            Tuple of (is_ok, list_of_violations)
        """
        violations = []
        
        # Check drawdown limit
        if self.current_drawdown > self.config.max_drawdown_limit:
            violations.append(f"Drawdown {self.current_drawdown:.2%} exceeds limit {self.config.max_drawdown_limit:.2%}")
        
        # Check daily loss limit (simplified)
        if self.daily_pnl < -self.config.max_daily_loss * self.portfolio_value:
            violations.append(f"Daily loss {self.daily_pnl:.2f} exceeds limit {-self.config.max_daily_loss * self.portfolio_value:.2f}")
        
        # Check position sizes
        total_exposure = sum(abs(pos.quantity * pos.entry_price) for pos in self.positions.values())
        if total_exposure > self.portfolio_value:
            violations.append(f"Total exposure {total_exposure:.2f} exceeds portfolio value {self.portfolio_value:.2f}")
        
        return len(violations) == 0, violations
    
    def calculate_transaction_costs(self, symbol: str, quantity: float, 
                                  price: float, is_buy: bool) -> Tuple[float, float]:
        """
        Calculate commission and slippage for a trade.
        
        Args:
            symbol: Trading symbol
            quantity: Trade quantity
            price: Trade price
            is_buy: True for buy, False for sell
            
        Returns:
            Tuple of (commission, slippage)
        """
        trade_value = abs(quantity * price)
        commission = trade_value * self.config.commission_per_trade
        
        # Simple slippage model (can be enhanced)
        if self.config.slippage_model == "linear":
            # Base slippage + size-dependent component
            size_factor = min(quantity / 1000, 0.01)  # Cap at 1%
            slippage = trade_value * (self.config.min_slippage + size_factor)
        else:
            slippage = trade_value * self.config.min_slippage
            
        return commission, slippage
    
    def execute_trade(self, symbol: str, signal: SignalType, quantity: float,
                     price: float, timestamp: datetime, 
                     metadata: Dict[str, Any] = None) -> Optional[Trade]:
        """
        Execute a trade and record it.
        
        Args:
            symbol: Trading symbol
            signal: Signal type
            quantity: Quantity to trade (positive for long, negative for short)
            price: Execution price
            timestamp: Trade timestamp
            metadata: Additional trade metadata
            
        Returns:
            Executed Trade object or None if rejected
        """
        # Check risk limits before trading
        is_ok, violations = self.check_risk_limits()
        if not is_ok:
            self.logger.warning(f"Trade rejected due to risk violations: {violations}")
            return None
        
        # Calculate transaction costs
        is_buy = (signal == SignalType.LONG and quantity > 0) or (signal == SignalType.SHORT and quantity < 0)
        commission, slippage = self.calculate_transaction_costs(symbol, quantity, price, is_buy)
        
        # Adjust price for slippage
        if is_buy:
            execution_price = price * (1 + slippage / (abs(quantity * price)))
        else:
            execution_price = price * (1 - slippage / (abs(quantity * price)))
        
        # Create trade record
        trade = Trade(
            entry_time=timestamp,
            exit_time=None,
            symbol=symbol,
            signal=signal,
            entry_price=execution_price,
            exit_price=None,
            quantity=quantity,
            pnl=0.0,
            pnl_pct=0.0,
            commission=commission,
            slippage=slippage,
            strategy_name=self.name,
            trade_id=f"{self.name}_{symbol}_{timestamp.strftime('%Y%m%d_%H%M%S')}",
            metadata=metadata or {}
        )
        
        # Update positions
        if symbol in self.positions:
            # Adding to existing position
            existing = self.positions[symbol]
            if existing.signal == signal:
                # Same direction - average prices
                total_quantity = existing.quantity + quantity
                if total_quantity != 0:
                    avg_price = (existing.entry_price * existing.quantity + 
                               execution_price * quantity) / total_quantity
                    existing.entry_price = avg_price
                    existing.quantity = total_quantity
                else:
                    # Position closed out
                    del self.positions[symbol]
                    return None  # Actually this would be a closing trade
            else:
                # Opposite direction - reduce or reverse
                if abs(quantity) >= abs(existing.quantity):
                    # Reverse or close and open new
                    remaining_qty = quantity + existing.quantity  # Existing quantity is opposite sign
                    # Close existing position at execution price
                    close_trade = self._close_position(symbol, execution_price, timestamp, 
                                                     f"Reverse {signal.name}")
                    if remaining_qty != 0:
                        # Open new position with remaining quantity
                        new_signal = signal if remaining_qty > 0 else SignalType.SHORT if remaining_qty < 0 else SignalType.NEUTRAL
                        if new_signal != SignalType.NEUTRAL:
                            self.execute_trade(symbol, new_signal, abs(remaining_qty), 
                                             execution_price, timestamp, metadata)
                    return close_trade
                else:
                    # Partial closure
                    remaining_qty = existing.quantity + quantity
                    close_trade = self._close_position(symbol, execution_price, timestamp, 
                                                     f"Partial close {signal.name}")
                    existing.quantity = remaining_qty
                    return close_trade
        else:
            # New position
            self.positions[symbol] = Position(
                symbol=symbol,
                signal=signal,
                entry_price=execution_price,
                quantity=quantity,
                entry_time=timestamp,
                stop_loss=None,  # To be set by strategy
                take_profit=None,  # To be set by strategy
                unrealized_pnl=0.0,
                unrealized_pnl_pct=0.0,
                strategy_name=self.name
            )
        
        self.logger.info(f"Executed {signal.name} {quantity:.4f} {symbol} @ {execution_price:.4f}")
        return trade
    
    def _close_position(self, symbol: str, price: float, timestamp: datetime, 
                       reason: str) -> Trade:
        """Close an existing position and record the trade."""
        if symbol not in self.positions:
            raise ValueError(f"No position found for {symbol}")
        
        position = self.positions[symbol]
        
        # Calculate PnL
        if position.signal == SignalType.LONG:
            price_change = (price - position.entry_price) / position.entry_price
        else:  # SHORT
            price_change = (position.entry_price - price) / position.entry_price
        
        pnl = price_change * abs(position.quantity) * position.entry_price
        pnl_pct = price_change
        
        # Calculate transaction costs for closing
        commission, slippage = self.calculate_transaction_costs(
            symbol, abs(position.quantity), price, 
            is_buy=(position.signal == SignalType.SHORT)  # To close short, we buy
        )
        
        # Adjust for slippage on close
        if position.signal == SignalType.LONG:
            execution_price = price * (1 - slippage / (abs(position.quantity * price)))
        else:  # SHORT
            execution_price = price * (1 + slippage / (abs(position.quantity * price)))
        
        # Recalculate PnL with execution price
        if position.signal == SignalType.LONG:
            price_change = (execution_price - position.entry_price) / position.entry_price
        else:
            price_change = (position.entry_price - execution_price) / position.entry_price
        
        pnl = price_change * abs(position.quantity) * position.entry_price
        pnl_pct = price_change
        
        # Create closing trade
        trade = Trade(
            entry_time=position.entry_time,
            exit_time=timestamp,
            symbol=symbol,
            signal=position.signal,
            entry_price=position.entry_price,
            exit_price=execution_price,
            quantity=position.quantity,
            pnl=pnl - commission - slippage,  # Net of costs
            pnl_pct=pnl_pct - (commission + slippage) / (abs(position.quantity) * position.entry_price),
            commission=commission,
            slippage=slippage,
            strategy_name=self.name,
            trade_id=f"{self.name}_{symbol}_close_{timestamp.strftime('%Y%m%d_%H%M%S')}",
            metadata={"close_reason": reason}
        )
        
        # Remove position
        del self.positions[symbol]
        
        self.logger.info(f"Closed position {symbol} @ {execution_price:.4f}, PnL: {trade.pnl:.2f} ({reason})")
        return trade
    
    def close_all_positions(self, market_data: pd.DataFrame, timestamp: datetime, 
                           reason: str = "Strategy end"):
        """Close all open positions."""
        symbols = list(self.positions.keys())
        for symbol in symbols:
            if symbol in market_data.index:
                price = market_data.loc[symbol, 'close']
                self._close_position(symbol, price, timestamp, reason)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Calculate and return performance metrics.
        
        Returns:
            Dictionary with performance statistics
        """
        if not self.trades:
            return {"error": "No trades executed"}
        
        # Calculate returns from completed trades
        completed_trades = [t for t in self.trades if t.exit_time is not None]
        if not completed_trades:
            return {"error": "No completed trades"}
        
        returns = [t.pnl_pct for t in completed_trades]
        
        # Basic statistics
        total_return = sum(returns)
        avg_return = np.mean(returns)
        std_return = np.std(returns) if len(returns) > 1 else 0.0
        sharpe_ratio = avg_return / std_return * np.sqrt(252) if std_return > 0 else 0.0  # Annualized
        
        # Win rate
        wins = [r for r in returns if r > 0]
        win_rate = len(wins) / len(returns) if returns else 0.0
        
        # Profit factor
        gross_profit = sum([r for r in returns if r > 0])
        gross_loss = abs(sum([r for r in returns if r < 0]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Maximum drawdown from equity curve
        if self.equity_curve:
            equity_values = [eq[1] for eq in self.equity_curve]
            running_max = np.maximum.accumulate(equity_values)
            drawdown = (running_max - equity_values) / running_max
            max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0.0
        else:
            max_drawdown = 0.0
        
        # Calmar ratio
        calmar_ratio = (total_return / 252) / max_drawdown if max_drawdown > 0 else 0.0  # Approximate annualized
        
        return {
            "total_trades": len(self.trades),
            "completed_trades": len(completed_trades),
            "win_rate": win_rate,
            "total_return": total_return,
            "avg_return_per_trade": avg_return,
            "return_std": std_return,
            "sharpe_ratio": sharpe_ratio,
            "profit_factor": profit_factor,
            "max_drawdown": max_drawdown,
            "calmar_ratio": calmar_ratio,
            "current_portfolio_value": self.portfolio_value,
            "current_drawdown": self.current_drawdown
        }
    
    def save_state(self, filepath: str):
        """Save strategy state to file."""
        state = {
            "name": self.name,
            "config": asdict(self.config),
            "trades": [asdict(t) for t in self.trades],
            "portfolio_value": self.portfolio_value,
            "equity_curve": [(ts.isoformat(), val) for ts, val in self.equity_curve],
            "timestamp": datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
        
        self.logger.info(f"Strategy state saved to {filepath}")
    
    def load_state(self, filepath: str):
        """Load strategy state from file."""
        with open(filepath, 'r') as f:
            state = json.load(f)
        
        self.name = state["name"]
        # Note: Config loading would need special handling for enum/etc.
        self.portfolio_value = state["portfolio_value"]
        self.equity_curve = [(datetime.fromisoformat(ts), val) for ts, val in state["equity_curve"]]
        
        self.logger.info(f"Strategy state loaded from {filepath}")

# Example concrete strategy implementation
class ExampleMeanReversionStrategy(BaseStrategy):
    """Example mean reversion strategy for demonstration."""
    
    def __init__(self, name: str = "ExampleMeanReversion", config: StrategyConfig = None):
        super().__init__(name, config)
        self.lookback_period = config.lookback_period if config else 20
        self.entry_threshold = 2.0  # Z-score threshold for entry
        self.exit_threshold = 0.5   # Z-score threshold for exit
    
    def generate_signals(self, data: pd.DataFrame, timestamp: datetime) -> Dict[str, SignalType]:
        """Generate mean reversion signals based on z-score."""
        signals = {}
        
        # Ensure we have enough data
        if len(data) < self.lookback_period:
            return signals
        
        # Calculate z-score for each symbol (simplified example)
        for symbol in data.index:
            if 'close' in data.columns:
                # Get historical prices for this symbol
                # In practice, you'd need time series data for each symbol
                # This is a simplified placeholder
                historical_prices = data.loc[symbol, 'close'] if isinstance(data.loc[symbol, 'close'], pd.Series) else [data.loc[symbol, 'close']]
                
                if len(historical_prices) >= self.lookback_period:
                    recent_prices = historical_prices[-self.lookback_period:]
                    mean_price = np.mean(recent_prices)
                    std_price = np.std(recent_prices)
                    
                    if std_price > 0:
                        current_price = recent_prices[-1]
                        z_score = (current_price - mean_price) / std_price
                        
                        if z_score < -self.entry_threshold:
                            signals[symbol] = SignalType.LONG
                        elif z_score > self.entry_threshold:
                            signals[symbol] = SignalType.SHORT
                        elif abs(z_score) < self.exit_threshold:
                            # Exit signal would be handled separately
                            pass
        
        return signals
    
    def calculate_position_size(self, symbol: str, signal: SignalType, 
                              data: pd.DataFrame, timestamp: datetime) -> float:
        """Calculate position size based on volatility."""
        # Simple volatility-based sizing
        if 'close' in data.columns and symbol in data.index:
            # Get recent volatility (simplified)
            if len(data) >= 20:
                # This would need proper time series data
                volatility = 0.02  # Placeholder 2% daily volatility
                # Inverse volatility scaling
                vol_scalar = 1.0 / (volatility * np.sqrt(252)) if volatility > 0 else 1.0
                # Scale by max position size
                position_size = min(self.config.max_position_size * vol_scalar, self.config.max_position_size)
                return position_size
        
        return self.config.max_position_size * 0.5  # Default half position

# Utility functions for strategy evaluation
def calculate_statistical_significance(returns: List[float]) -> Dict[str, float]:
    """
    Calculate statistical significance of returns.
    
    Args:
        returns: List of trade returns (as decimals)
        
    Returns:
        Dictionary with statistical test results
    """
    if len(returns) < 2:
        return {"error": "Insufficient data for significance testing"}
    
    returns_array = np.array(returns)
    mean_return = np.mean(returns_array)
    std_return = np.std(returns_array, ddof=1)  # Sample standard deviation
    
    # t-test for mean return significantly different from zero
    if std_return > 0:
        t_stat = mean_return / (std_return / np.sqrt(len(returns)))
        # Degrees of freedom
        df = len(returns) - 1
        # Two-tailed p-value (simplified approximation)
        from scipy import stats
        p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df))
    else:
        t_stat = 0.0
        p_value = 1.0
    
    return {
        "mean_return": mean_return,
        "std_return": std_return,
        "t_statistic": t_stat,
        "p_value": p_value,
        "significant_at_95pct": p_value < 0.05,
        "significant_at_99pct": p_value < 0.01
    }

def walk_forward_analysis(strategy_class, data: pd.DataFrame, 
                         in_sample_period: int = 252,
                         out_sample_period: int = 63,
                         min_periods: int = 50) -> Dict[str, Any]:
    """
    Perform walk-forward analysis on a strategy.
    
    Args:
        strategy_class: Strategy class to test
        data: Historical market data
        in_sample_period: Number of periods for in-sample optimization
        out_sample_period: Number of periods for out-sample testing
        min_periods: Minimum periods required to start
        
    Returns:
        Dictionary with walk-forward results
    """
    # This is a simplified placeholder - full implementation would be more complex
    results = {
        "total_periods": 0,
        "periods_analyzed": 0,
        "average_is_return": 0.0,
        "average_oos_return": 0.0,
        "return_consistency": 0.0,
        "parameter_stability": {}
    }
    
    return results

if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Create strategy
    config = StrategyConfig(
        max_position_size=0.03,
        max_daily_loss=0.01,
        max_drawdown_limit=0.15
    )
    
    strategy = ExampleMeanReversionStrategy("TestMR", config)
    print(f"Created strategy: {strategy.name}")
    print(f"Config: {asdict(strategy.config)}")