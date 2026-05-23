"""
Backtest Framework for Trading Strategies
=========================================
A production-ready backtest engine supporting multiple data sources,
performance metrics, and strategy evaluation.

Author: AI Assistant
Date: 2025
"""

import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Union, Tuple
from datetime import datetime, timedelta
from enum import Enum
import warnings
from pathlib import Path
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class Signal(Enum):
    """Trading signals"""
    BUY = 1
    SELL = -1
    HOLD = 0


class OrderType(Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class PositionSide(Enum):
    """Position side"""
    LONG = 1
    SHORT = -1
    FLAT = 0


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Trade:
    """Represents a completed trade"""
    entry_date: datetime
    exit_date: datetime
    symbol: str
    side: PositionSide
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    pnl_pct: float
    commission: float = 0.0
    slippage: float = 0.0
    
    @property
    def duration(self) -> timedelta:
        """Trade duration"""
        return self.exit_date - self.entry_date
    
    @property
    def is_win(self) -> bool:
        """Whether trade was profitable"""
        return self.pnl > 0


@dataclass
class Position:
    """Current position state"""
    symbol: str
    side: PositionSide
    quantity: float = 0.0
    avg_entry_price: float = 0.0
    entry_date: Optional[datetime] = None
    unrealized_pnl: float = 0.0
    
    def update_unrealized_pnl(self, current_price: float):
        """Update unrealized PnL based on current price"""
        if self.side == PositionSide.LONG:
            self.unrealized_pnl = (current_price - self.avg_entry_price) * self.quantity
        elif self.side == PositionSide.SHORT:
            self.unrealized_pnl = (self.avg_entry_price - current_price) * self.quantity
        else:
            self.unrealized_pnl = 0.0


@dataclass
class BacktestConfig:
    """Configuration for backtest"""
    initial_capital: float = 100000.0
    commission_rate: float = 0.001  # 0.1%
    slippage: float = 0.0005  # 0.05%
    max_position_pct: float = 1.0  # Max position as % of capital
    allow_short: bool = False
    position_sizing: str = "fixed"  # fixed, percent_risk, kelly
    risk_per_trade: float = 0.02  # For percent_risk sizing
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None


@dataclass
class BacktestResult:
    """Complete backtest results"""
    # Performance metrics
    total_return: float = 0.0
    annualized_return: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    calmar_ratio: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    num_trades: int = 0
    avg_trade_return: float = 0.0
    avg_trade_duration: timedelta = field(default_factory=lambda: timedelta(0))
    
    # Data
    equity_curve: pd.Series = field(default_factory=pd.Series)
    trades: List[Trade] = field(default_factory=list)
    returns: pd.Series = field(default_factory=pd.Series)
    drawdown_series: pd.Series = field(default_factory=pd.Series)
    
    # Additional metrics
    volatility: float = 0.0
    downside_deviation: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'total_return': self.total_return,
            'annualized_return': self.annualized_return,
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'max_drawdown': self.max_drawdown,
            'calmar_ratio': self.calmar_ratio,
            'win_rate': self.win_rate,
            'profit_factor': self.profit_factor,
            'num_trades': self.num_trades,
            'avg_trade_return': self.avg_trade_return,
            'volatility': self.volatility,
            'avg_win': self.avg_win,
            'avg_loss': self.avg_loss,
            'largest_win': self.largest_win,
            'largest_loss': self.largest_loss,
            'consecutive_wins': self.consecutive_wins,
            'consecutive_losses': self.consecutive_losses,
        }
    
    def to_json(self, path: str):
        """Save results to JSON"""
        data = self.to_dict()
        # Convert non-serializable types
        data['avg_trade_duration_days'] = self.avg_trade_duration.days if self.avg_trade_duration else 0
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def __str__(self) -> str:
        """String representation"""
        return f"""
Backtest Results
================
Total Return:        {self.total_return:.2%}
Annualized Return:   {self.annualized_return:.2%}
Sharpe Ratio:        {self.sharpe_ratio:.2f}
Sortino Ratio:       {self.sortino_ratio:.2f}
Max Drawdown:        {self.max_drawdown:.2%}
Calmar Ratio:        {self.calmar_ratio:.2f}
Win Rate:            {self.win_rate:.2%}
Profit Factor:       {self.profit_factor:.2f}
Number of Trades:    {self.num_trades}
Avg Trade Return:    {self.avg_trade_return:.2%}
Volatility:          {self.volatility:.2%}
Avg Win:             {self.avg_win:.2%}
Avg Loss:            {self.avg_loss:.2%}
"""


# =============================================================================
# DATA LOADING
# =============================================================================

class DataLoader:
    """Load historical price data from various sources"""
    
    @staticmethod
    def from_yahoo(
        symbol: str,
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Load data from Yahoo Finance using yfinance.
        
        Args:
            symbol: Ticker symbol (e.g., 'AAPL', 'BTC-USD')
            start_date: Start date
            end_date: End date
            interval: Data interval ('1d', '1h', '15m', etc.)
        
        Returns:
            DataFrame with OHLCV data
        """
        try:
            import yfinance as yf
        except ImportError:
            raise ImportError("yfinance required. Install: pip install yfinance")
        
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date)
        if isinstance(end_date, str):
            end_date = pd.to_datetime(end_date)
        
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date, interval=interval)
        
        if df.empty:
            raise ValueError(f"No data found for {symbol}")
        
        # Standardize column names
        df.columns = [c.lower().replace(' ', '_') for c in df.columns]
        df.index.name = 'date'
        
        # Add symbol column
        df['symbol'] = symbol
        
        logger.info(f"Loaded {len(df)} rows for {symbol} from Yahoo Finance")
        return df
    
    @staticmethod
    def from_kraken(
        symbol: str,
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        interval: int = 1440  # 1440 minutes = 1 day
    ) -> pd.DataFrame:
        """
        Load data from Kraken cryptocurrency exchange.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSD', 'ETHUSD')
            start_date: Start date
            end_date: End date
            interval: Candle interval in minutes (1, 5, 15, 30, 60, 240, 1440, 10080, 21600)
        
        Returns:
            DataFrame with OHLCV data
        """
        try:
            import requests
        except ImportError:
            raise ImportError("requests required. Install: pip install requests")
        
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date)
        if isinstance(end_date, str):
            end_date = pd.to_datetime(end_date)
        
        # Convert to Unix timestamps
        since = int(start_date.timestamp())
        
        url = f"https://api.kraken.com/0/public/OHLC"
        params = {
            'pair': symbol,
            'interval': interval,
            'since': since
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if 'error' in data and data['error']:
            raise ValueError(f"Kraken API error: {data['error']}")
        
        # Extract OHLC data
        pair_key = list(data['result'].keys())[0]
        ohlc_data = data['result'][pair_key]
        
        # Create DataFrame
        df = pd.DataFrame(
            ohlc_data,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count']
        )
        
        # Convert types
        df['date'] = pd.to_datetime(df['timestamp'], unit='s')
        for col in ['open', 'high', 'low', 'close', 'vwap', 'volume']:
            df[col] = df[col].astype(float)
        
        df = df.set_index('date')
        df = df[(df.index >= start_date) & (df.index <= end_date)]
        df['symbol'] = symbol
        
        logger.info(f"Loaded {len(df)} rows for {symbol} from Kraken")
        return df
    
    @staticmethod
    def from_csv(
        path: str,
        date_col: str = 'date',
        symbol: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Load data from CSV file.
        
        Args:
            path: Path to CSV file
            date_col: Name of date column
            symbol: Symbol name (optional)
        
        Returns:
            DataFrame with OHLCV data
        """
        df = pd.read_csv(path, parse_dates=[date_col])
        df = df.set_index(date_col)
        df.index.name = 'date'
        
        # Standardize column names to lowercase
        df.columns = [c.lower() for c in df.columns]
        
        if symbol:
            df['symbol'] = symbol
        
        logger.info(f"Loaded {len(df)} rows from {path}")
        return df
    
    @staticmethod
    def from_dataframe(
        df: pd.DataFrame,
        date_col: Optional[str] = None,
        symbol: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Use existing DataFrame.
        
        Args:
            df: Input DataFrame
            date_col: Name of date column (if not index)
            symbol: Symbol name (optional)
        
        Returns:
            DataFrame with standardized format
        """
        df = df.copy()
        
        if date_col and date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col])
            df = df.set_index(date_col)
        
        df.index.name = 'date'
        df.columns = [c.lower() for c in df.columns]
        
        if symbol and 'symbol' not in df.columns:
            df['symbol'] = symbol
        
        return df


# =============================================================================
# STRATEGY BASE CLASS
# =============================================================================

class Strategy(ABC):
    """
    Abstract base class for trading strategies.
    
    Subclasses must implement:
    - on_bar(): Called on each new bar
    - generate_signals(): Generate trading signals
    """
    
    def __init__(self, name: str = "Unnamed Strategy"):
        self.name = name
        self.data: Optional[pd.DataFrame] = None
        self.current_idx: int = 0
        self.current_bar: Optional[pd.Series] = None
        self.indicators: Dict[str, pd.Series] = {}
    
    def initialize(self, data: pd.DataFrame):
        """Initialize strategy with data"""
        self.data = data
        self._calculate_indicators()
    
    @abstractmethod
    def _calculate_indicators(self):
        """Calculate technical indicators. Override in subclass."""
        pass
    
    @abstractmethod
    def on_bar(self, idx: int, bar: pd.Series) -> Optional[Signal]:
        """
        Called on each bar. Override in subclass.
        
        Args:
            idx: Current index
            bar: Current bar data
        
        Returns:
            Signal or None
        """
        pass
    
    def get_indicator(self, name: str, idx: Optional[int] = None) -> float:
        """Get indicator value at index"""
        if name not in self.indicators:
            raise KeyError(f"Indicator '{name}' not found")
        
        if idx is None:
            idx = self.current_idx
        
        return self.indicators[name].iloc[idx]
    
    def get_price_history(self, periods: int, column: str = 'close') -> pd.Series:
        """Get recent price history"""
        start_idx = max(0, self.current_idx - periods + 1)
        return self.data[column].iloc[start_idx:self.current_idx + 1]


# =============================================================================
# BACKTEST ENGINE
# =============================================================================

class BacktestEngine:
    """
    Production-ready backtest engine for trading strategies.
    """
    
    def __init__(self, config: Optional[BacktestConfig] = None):
        self.config = config or BacktestConfig()
        self.data: Optional[pd.DataFrame] = None
        self.strategy: Optional[Strategy] = None
        
        # State
        self.cash: float = self.config.initial_capital
        self.equity: float = self.config.initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.equity_curve: List[Tuple[datetime, float]] = []
        
        # Tracking
        self.current_date: Optional[datetime] = None
        self.pending_orders: List[Dict] = []
    
    def set_data(self, data: pd.DataFrame):
        """Set historical data"""
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing = [c for c in required_cols if c not in data.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        
        self.data = data.sort_index()
        logger.info(f"Data set: {len(data)} rows from {data.index[0]} to {data.index[-1]}")
    
    def set_strategy(self, strategy: Strategy):
        """Set trading strategy"""
        self.strategy = strategy
        logger.info(f"Strategy set: {strategy.name}")
    
    def run(self) -> BacktestResult:
        """
        Run the backtest.
        
        Returns:
            BacktestResult with all metrics
        """
        if self.data is None:
            raise ValueError("No data set. Call set_data() first.")
        if self.strategy is None:
            raise ValueError("No strategy set. Call set_strategy() first.")
        
        # Initialize
        self.cash = self.config.initial_capital
        self.equity = self.config.initial_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        
        # Initialize strategy
        self.strategy.initialize(self.data)
        
        logger.info("Starting backtest...")
        
        # Iterate through bars
        for idx in range(len(self.data)):
            bar = self.data.iloc[idx]
            self.current_date = self.data.index[idx]
            self.strategy.current_idx = idx
            self.strategy.current_bar = bar
            
            # Update positions with current prices
            self._update_positions(bar)
            
            # Get signal from strategy
            signal = self.strategy.on_bar(idx, bar)
            
            # Execute signal
            if signal:
                self._execute_signal(signal, bar)
            
            # Record equity
            self._update_equity()
        
        # Close any open positions at the end
        self._close_all_positions(self.data.iloc[-1])
        
        logger.info("Backtest complete. Calculating metrics...")
        
        # Calculate and return results
        return self._calculate_metrics()
    
    def _update_positions(self, bar: pd.Series):
        """Update position PnL with current prices"""
        symbol = bar.get('symbol', 'UNKNOWN')
        
        if symbol in self.positions:
            position = self.positions[symbol]
            position.update_unrealized_pnl(bar['close'])
    
    def _execute_signal(self, signal: Signal, bar: pd.Series):
        """Execute trading signal"""
        symbol = bar.get('symbol', 'UNKNOWN')
        price = bar['close']
        
        # Apply slippage
        if signal == Signal.BUY:
            fill_price = price * (1 + self.config.slippage)
        elif signal == Signal.SELL:
            fill_price = price * (1 - self.config.slippage)
        else:
            return
        
        current_position = self.positions.get(symbol)
        
        # Determine action based on signal and current position
        if signal == Signal.BUY:
            if current_position is None or current_position.side == PositionSide.FLAT:
                # Open long position
                self._open_position(symbol, PositionSide.LONG, fill_price, bar)
            elif current_position.side == PositionSide.SHORT and self.config.allow_short:
                # Close short and open long
                self._close_position(symbol, fill_price, bar)
                self._open_position(symbol, PositionSide.LONG, fill_price, bar)
        
        elif signal == Signal.SELL:
            if current_position is None or current_position.side == PositionSide.FLAT:
                if self.config.allow_short:
                    # Open short position
                    self._open_position(symbol, PositionSide.SHORT, fill_price, bar)
            elif current_position.side == PositionSide.LONG:
                # Close long position
                self._close_position(symbol, fill_price, bar)
    
    def _calculate_position_size(self, price: float, side: PositionSide) -> float:
        """Calculate position size based on config"""
        if self.config.position_sizing == "fixed":
            # Fixed dollar amount
            position_value = self.equity * self.config.max_position_pct
            quantity = position_value / price
        
        elif self.config.position_sizing == "percent_risk":
            # Risk-based sizing
            risk_amount = self.equity * self.config.risk_per_trade
            if self.config.stop_loss_pct:
                stop_distance = price * self.config.stop_loss_pct
                quantity = risk_amount / stop_distance
            else:
                quantity = (self.equity * self.config.max_position_pct) / price
        
        else:
            # Default to fixed
            position_value = self.equity * self.config.max_position_pct
            quantity = position_value / price
        
        return quantity
    
    def _open_position(self, symbol: str, side: PositionSide, price: float, bar: pd.Series):
        """Open a new position"""
        quantity = self._calculate_position_size(price, side)
        
        if quantity <= 0:
            return
        
        # Calculate commission
        position_value = quantity * price
        commission = position_value * self.config.commission_rate
        
        # Check if we have enough cash
        if position_value + commission > self.cash:
            quantity = (self.cash - commission) / price
            position_value = quantity * price
            commission = position_value * self.config.commission_rate
        
        # Update cash
        self.cash -= position_value + commission
        
        # Create position
        self.positions[symbol] = Position(
            symbol=symbol,
            side=side,
            quantity=quantity,
            avg_entry_price=price,
            entry_date=self.current_date
        )
    
    def _close_position(self, symbol: str, price: float, bar: pd.Series):
        """Close an existing position"""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        
        if position.side == PositionSide.FLAT:
            return
        
        # Calculate PnL
        if position.side == PositionSide.LONG:
            pnl = (price - position.avg_entry_price) * position.quantity
        else:  # SHORT
            pnl = (position.avg_entry_price - price) * position.quantity
        
        # Calculate commission
        position_value = position.quantity * price
        commission = position_value * self.config.commission_rate
        
        # Update cash
        self.cash += position_value - commission
        
        # Calculate PnL percentage
        invested = position.avg_entry_price * position.quantity
        pnl_pct = pnl / invested if invested > 0 else 0
        
        # Record trade
        trade = Trade(
            entry_date=position.entry_date,
            exit_date=self.current_date,
            symbol=symbol,
            side=position.side,
            entry_price=position.avg_entry_price,
            exit_price=price,
            quantity=position.quantity,
            pnl=pnl,
            pnl_pct=pnl_pct,
            commission=commission,
            slippage=self.config.slippage
        )
        self.trades.append(trade)
        
        # Clear position
        self.positions[symbol] = Position(symbol=symbol, side=PositionSide.FLAT)
    
    def _close_all_positions(self, bar: pd.Series):
        """Close all open positions at end of backtest"""
        for symbol, position in list(self.positions.items()):
            if position.side != PositionSide.FLAT:
                self._close_position(symbol, bar['close'], bar)
    
    def _update_equity(self):
        """Update total equity"""
        position_value = sum(
            pos.quantity * self.strategy.current_bar['close']
            for pos in self.positions.values()
            if pos.side != PositionSide.FLAT
        )
        self.equity = self.cash + position_value
        self.equity_curve.append((self.current_date, self.equity))
    
    def _calculate_metrics(self) -> BacktestResult:
        """Calculate all performance metrics"""
        result = BacktestResult()
        
        # Equity curve
        equity_df = pd.DataFrame(self.equity_curve, columns=['date', 'equity'])
        equity_df = equity_df.set_index('date')
        result.equity_curve = equity_df['equity']
        
        # Returns
        result.returns = result.equity_curve.pct_change().dropna()
        
        # Total return
        result.total_return = (result.equity_curve.iloc[-1] / self.config.initial_capital) - 1
        
        # Annualized return
        years = (result.equity_curve.index[-1] - result.equity_curve.index[0]).days / 365.25
        if years > 0:
            result.annualized_return = (1 + result.total_return) ** (1 / years) - 1
        
        # Volatility (annualized)
        if len(result.returns) > 1:
            result.volatility = result.returns.std() * np.sqrt(252)
        
        # Sharpe Ratio (assuming risk-free rate of 0 for simplicity)
        if result.volatility > 0:
            result.sharpe_ratio = (result.returns.mean() * 252) / (result.returns.std() * np.sqrt(252))
        
        # Sortino Ratio
        downside_returns = result.returns[result.returns < 0]
        if len(downside_returns) > 0:
            result.downside_deviation = downside_returns.std() * np.sqrt(252)
            if result.downside_deviation > 0:
                result.sortino_ratio = (result.returns.mean() * 252) / result.downside_deviation
        
        # Max Drawdown
        rolling_max = result.equity_curve.expanding().max()
        drawdown = (result.equity_curve - rolling_max) / rolling_max
        result.max_drawdown = drawdown.min()
        result.drawdown_series = drawdown
        
        # Calmar Ratio
        if abs(result.max_drawdown) > 0:
            result.calmar_ratio = result.annualized_return / abs(result.max_drawdown)
        
        # Trade metrics
        result.trades = self.trades
        result.num_trades = len(self.trades)
        
        if self.trades:
            # Win rate
            wins = [t for t in self.trades if t.is_win]
            result.win_rate = len(wins) / len(self.trades)
            
            # Profit factor
            gross_profit = sum(t.pnl for t in wins)
            gross_loss = abs(sum(t.pnl for t in self.trades if not t.is_win))
            if gross_loss > 0:
                result.profit_factor = gross_profit / gross_loss
            
            # Average trade return
            result.avg_trade_return = np.mean([t.pnl_pct for t in self.trades])
            
            # Average trade duration
            durations = [t.duration for t in self.trades]
            if durations:
                result.avg_trade_duration = sum(durations, timedelta(0)) / len(durations)
            
            # Win/Loss metrics
            if wins:
                result.avg_win = np.mean([t.pnl_pct for t in wins])
                result.largest_win = max([t.pnl_pct for t in wins])
            
            losses = [t for t in self.trades if not t.is_win]
            if losses:
                result.avg_loss = np.mean([t.pnl_pct for t in losses])
                result.largest_loss = min([t.pnl_pct for t in losses])
            
            # Consecutive wins/losses
            max_consecutive_wins = 0
            max_consecutive_losses = 0
            current_wins = 0
            current_losses = 0
            
            for trade in self.trades:
                if trade.is_win:
                    current_wins += 1
                    current_losses = 0
                    max_consecutive_wins = max(max_consecutive_wins, current_wins)
                else:
                    current_losses += 1
                    current_wins = 0
                    max_consecutive_losses = max(max_consecutive_losses, current_losses)
            
            result.consecutive_wins = max_consecutive_wins
            result.consecutive_losses = max_consecutive_losses
        
        return result


# =============================================================================
# EXAMPLE STRATEGIES
# =============================================================================

class MovingAverageCrossover(Strategy):
    """
    Simple Moving Average Crossover Strategy.
    Buys when fast MA crosses above slow MA.
    Sells when fast MA crosses below slow MA.
    """
    
    def __init__(
        self,
        fast_period: int = 20,
        slow_period: int = 50,
        name: str = "MA Crossover"
    ):
        super().__init__(name)
        self.fast_period = fast_period
        self.slow_period = slow_period
    
    def _calculate_indicators(self):
        """Calculate moving averages"""
        self.indicators['fast_ma'] = self.data['close'].rolling(self.fast_period).mean()
        self.indicators['slow_ma'] = self.data['close'].rolling(self.slow_period).mean()
    
    def on_bar(self, idx: int, bar: pd.Series) -> Optional[Signal]:
        """Generate signals based on MA crossover"""
        if idx < self.slow_period:
            return None
        
        fast_ma = self.get_indicator('fast_ma', idx)
        slow_ma = self.get_indicator('slow_ma', idx)
        prev_fast = self.get_indicator('fast_ma', idx - 1)
        prev_slow = self.get_indicator('slow_ma', idx - 1)
        
        # Golden cross (buy)
        if prev_fast <= prev_slow and fast_ma > slow_ma:
            return Signal.BUY
        
        # Death cross (sell)
        if prev_fast >= prev_slow and fast_ma < slow_ma:
            return Signal.SELL
        
        return Signal.HOLD


class RSIStrategy(Strategy):
    """
    RSI Mean Reversion Strategy.
    Buys when RSI is oversold (< 30).
    Sells when RSI is overbought (> 70).
    """
    
    def __init__(
        self,
        period: int = 14,
        oversold: float = 30,
        overbought: float = 70,
        name: str = "RSI Strategy"
    ):
        super().__init__(name)
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
    
    def _calculate_indicators(self):
        """Calculate RSI"""
        delta = self.data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
        rs = gain / loss
        self.indicators['rsi'] = 100 - (100 / (1 + rs))
    
    def on_bar(self, idx: int, bar: pd.Series) -> Optional[Signal]:
        """Generate signals based on RSI"""
        if idx < self.period:
            return None
        
        rsi = self.get_indicator('rsi', idx)
        
        if rsi < self.oversold:
            return Signal.BUY
        elif rsi > self.overbought:
            return Signal.SELL
        
        return Signal.HOLD


class BollingerBandsStrategy(Strategy):
    """
    Bollinger Bands Mean Reversion Strategy.
    Buys when price touches lower band.
    Sells when price touches upper band.
    """
    
    def __init__(
        self,
        period: int = 20,
        std_dev: float = 2.0,
        name: str = "Bollinger Bands"
    ):
        super().__init__(name)
        self.period = period
        self.std_dev = std_dev
    
    def _calculate_indicators(self):
        """Calculate Bollinger Bands"""
        sma = self.data['close'].rolling(self.period).mean()
        std = self.data['close'].rolling(self.period).std()
        self.indicators['middle'] = sma
        self.indicators['upper'] = sma + (std * self.std_dev)
        self.indicators['lower'] = sma - (std * self.std_dev)
    
    def on_bar(self, idx: int, bar: pd.Series) -> Optional[Signal]:
        """Generate signals based on Bollinger Bands"""
        if idx < self.period:
            return None
        
        close = bar['close']
        upper = self.get_indicator('upper', idx)
        lower = self.get_indicator('lower', idx)
        
        if close <= lower:
            return Signal.BUY
        elif close >= upper:
            return Signal.SELL
        
        return Signal.HOLD


# =============================================================================
# BATCH BACKTESTING
# =============================================================================

class BatchBacktester:
    """
    Run multiple strategies and parameters in batch.
    Useful for strategy optimization and comparison.
    """
    
    def __init__(self, data: pd.DataFrame, config: Optional[BacktestConfig] = None):
        self.data = data
        self.config = config or BacktestConfig()
        self.results: List[Tuple[Strategy, BacktestResult]] = []
    
    def run_strategy(
        self,
        strategy: Strategy,
        name: Optional[str] = None
    ) -> BacktestResult:
        """Run a single strategy"""
        engine = BacktestEngine(self.config)
        engine.set_data(self.data)
        engine.set_strategy(strategy)
        
        result = engine.run()
        
        if name:
            strategy.name = name
        
        self.results.append((strategy, result))
        return result
    
    def run_param_grid(
        self,
        strategy_class: type,
        param_grid: Dict[str, List],
        base_name: str = "Strategy"
    ) -> pd.DataFrame:
        """
        Run strategy with parameter grid search.
        
        Args:
            strategy_class: Strategy class to instantiate
            param_grid: Dictionary of parameter names to lists of values
            base_name: Base name for strategies
        
        Returns:
            DataFrame with results for each parameter combination
        """
        from itertools import product
        
        # Generate all parameter combinations
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        combinations = list(product(*values))
        
        results_list = []
        
        for i, combo in enumerate(combinations):
            params = dict(zip(keys, combo))
            name = f"{base_name}_{i+1}"
            
            try:
                strategy = strategy_class(**params)
                result = self.run_strategy(strategy, name)
                
                row = {
                    'name': name,
                    **params,
                    **result.to_dict()
                }
                results_list.append(row)
                
            except Exception as e:
                logger.error(f"Error running {name}: {e}")
        
        return pd.DataFrame(results_list)
    
    def get_best_strategy(
        self,
        metric: str = 'sharpe_ratio'
    ) -> Tuple[Strategy, BacktestResult]:
        """Get best performing strategy by metric"""
        if not self.results:
            raise ValueError("No results available")
        
        return max(self.results, key=lambda x: getattr(x[1], metric, float('-inf')))
    
    def compare_strategies(self) -> pd.DataFrame:
        """Compare all strategies in a DataFrame"""
        data = []
        for strategy, result in self.results:
            row = {
                'strategy': strategy.name,
                **result.to_dict()
            }
            data.append(row)
        
        return pd.DataFrame(data)
    
    def save_results(self, path: str):
        """Save all results to directory"""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        
        # Save comparison
        comparison = self.compare_strategies()
        comparison.to_csv(path / 'comparison.csv', index=False)
        
        # Save individual results
        for strategy, result in self.results:
            result.to_json(path / f"{strategy.name.replace(' ', '_')}.json")
        
        logger.info(f"Results saved to {path}")


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

def example_usage():
    """
    Example of how to use the backtest framework.
    """
    print("=" * 60)
    print("BACKTEST FRAMEWORK EXAMPLE")
    print("=" * 60)
    
    # Create sample data (in real usage, load from Yahoo/Kraken)
    print("\n1. Creating sample data...")
    dates = pd.date_range(start='2020-01-01', end='2025-01-01', freq='D')
    np.random.seed(42)
    
    # Generate random walk price data
    returns = np.random.normal(0.0005, 0.02, len(dates))
    prices = 100 * np.exp(np.cumsum(returns))
    
    data = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.001, len(dates))),
        'high': prices * (1 + abs(np.random.normal(0, 0.01, len(dates)))),
        'low': prices * (1 - abs(np.random.normal(0, 0.01, len(dates)))),
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, len(dates)),
        'symbol': 'SAMPLE'
    }, index=dates)
    
    print(f"   Data: {len(data)} rows from {data.index[0].date()} to {data.index[-1].date()}")
    
    # Configure backtest
    print("\n2. Configuring backtest...")
    config = BacktestConfig(
        initial_capital=100000.0,
        commission_rate=0.001,
        slippage=0.0005,
        max_position_pct=1.0,
        position_sizing="fixed"
    )
    
    # Run single strategy
    print("\n3. Running Moving Average Crossover Strategy...")
    ma_strategy = MovingAverageCrossover(fast_period=20, slow_period=50)
    
    engine = BacktestEngine(config)
    engine.set_data(data)
    engine.set_strategy(ma_strategy)
    
    result = engine.run()
    print(result)
    
    # Run RSI Strategy
    print("\n4. Running RSI Strategy...")
    rsi_strategy = RSIStrategy(period=14, oversold=30, overbought=70)
    
    engine2 = BacktestEngine(config)
    engine2.set_data(data)
    engine2.set_strategy(rsi_strategy)
    
    result2 = engine2.run()
    print(result2)
    
    # Batch testing with parameter optimization
    print("\n5. Running parameter optimization...")
    batch = BatchBacktester(data, config)
    
    param_grid = {
        'fast_period': [10, 20, 30],
        'slow_period': [50, 100]
    }
    
    results_df = batch.run_param_grid(
        MovingAverageCrossover,
        param_grid,
        base_name="MA_Optimization"
    )
    
    print("\n   Parameter Optimization Results:")
    print(results_df[['name', 'fast_period', 'slow_period', 'total_return', 
                      'sharpe_ratio', 'max_drawdown', 'num_trades']].to_string())
    
    # Get best strategy
    best_strategy, best_result = batch.get_best_strategy('sharpe_ratio')
    print(f"\n   Best Strategy: {best_strategy.name}")
    print(f"   Sharpe Ratio: {best_result.sharpe_ratio:.2f}")
    
    print("\n" + "=" * 60)
    print("EXAMPLE COMPLETE")
    print("=" * 60)
    
    return result, result2, batch


def example_with_real_data():
    """
    Example using real data from Yahoo Finance.
    Requires yfinance: pip install yfinance
    """
    print("=" * 60)
    print("REAL DATA EXAMPLE (Yahoo Finance)")
    print("=" * 60)
    
    try:
        # Load real data
        print("\n1. Loading data from Yahoo Finance...")
        data = DataLoader.from_yahoo(
            symbol="SPY",
            start_date="2020-01-01",
            end_date="2025-01-01",
            interval="1d"
        )
        print(f"   Loaded {len(data)} rows")
        
        # Configure and run
        config = BacktestConfig(
            initial_capital=100000.0,
            commission_rate=0.001,
            slippage=0.0005
        )
        
        # Test multiple strategies
        strategies = [
            MovingAverageCrossover(20, 50, "MA_20_50"),
            MovingAverageCrossover(50, 200, "MA_50_200"),
            RSIStrategy(14, 30, 70, "RSI_14"),
            BollingerBandsStrategy(20, 2.0, "BB_20_2")
        ]
        
        batch = BatchBacktester(data, config)
        
        for strategy in strategies:
            print(f"\n   Running {strategy.name}...")
            result = batch.run_strategy(strategy)
            print(f"   Return: {result.total_return:.2%}, Sharpe: {result.sharpe_ratio:.2f}")
        
        # Compare all
        print("\n2. Strategy Comparison:")
        comparison = batch.compare_strategies()
        print(comparison[['strategy', 'total_return', 'sharpe_ratio', 
                         'max_drawdown', 'win_rate', 'num_trades']].to_string())
        
        # Save results
        batch.save_results("./backtest_results")
        
    except ImportError as e:
        print(f"   Skipping: {e}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n" + "=" * 60)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    # Run example with synthetic data
    example_usage()
    
    # Run example with real data (if yfinance available)
    print("\n")
    example_with_real_data()
