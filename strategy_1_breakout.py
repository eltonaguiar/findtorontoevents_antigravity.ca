"""
STRATEGY 1: BREAKOUT STRATEGY (u/No-Instruction-1234)
Based on: XAUUSD and USDJPY breakout strategy with 2:1 Risk-Reward

Key Principles:
- Trade only XAUUSD and USDJPY
- Breakout entries with 2:1 RR
- Let volatility work in favor
- Position for big moves
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional, List, Tuple
import yfinance as yf


@dataclass
class Trade:
    entry_date: pd.Timestamp
    entry_price: float
    stop_loss: float
    take_profit: float
    direction: str  # 'long' or 'short'
    exit_date: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    status: str = 'open'


class BreakoutStrategy:
    """
    Breakout Strategy for XAUUSD and USDJPY
    
    Parameters:
    -----------
    lookback_period : int
        Period for identifying consolidation/breakout levels
    breakout_threshold : float
        Minimum percentage move to qualify as breakout
    risk_per_trade : float
        Risk per trade as percentage of account
    risk_reward_ratio : float
        Target RR ratio (default 2:1)
    atr_period : int
        Period for ATR calculation (volatility measure)
    """
    
    def __init__(
        self,
        lookback_period: int = 20,
        breakout_threshold: float = 0.005,  # 0.5%
        risk_per_trade: float = 0.01,  # 1%
        risk_reward_ratio: float = 2.0,  # 2:1
        atr_period: int = 14
    ):
        self.lookback_period = lookback_period
        self.breakout_threshold = breakout_threshold
        self.risk_per_trade = risk_per_trade
        self.risk_reward_ratio = risk_reward_ratio
        self.atr_period = atr_period
        self.trades: List[Trade] = []
        
    def calculate_atr(self, df: pd.DataFrame) -> pd.Series:
        """Calculate Average True Range"""
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(self.atr_period).mean()
        return atr
    
    def identify_consolidation(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Identify consolidation periods and breakout levels
        """
        df = df.copy()
        
        # Calculate rolling high/low for lookback period
        df['Resistance'] = df['High'].rolling(self.lookback_period).max()
        df['Support'] = df['Low'].rolling(self.lookback_period).min()
        
        # Calculate consolidation range
        df['Range'] = df['Resistance'] - df['Support']
        df['Range_Pct'] = df['Range'] / df['Close']
        
        # ATR for volatility context
        df['ATR'] = self.calculate_atr(df)
        df['ATR_Pct'] = df['ATR'] / df['Close']
        
        return df
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate breakout signals
        """
        df = self.identify_consolidation(df)
        
        # Long breakout: Close above resistance
        df['Long_Signal'] = (
            (df['Close'] > df['Resistance'].shift(1)) &
            (df['Range_Pct'].shift(1) < self.breakout_threshold * 2)  # Was consolidating
        )
        
        # Short breakout: Close below support
        df['Short_Signal'] = (
            (df['Close'] < df['Support'].shift(1)) &
            (df['Range_Pct'].shift(1) < self.breakout_threshold * 2)
        )
        
        return df
    
    def calculate_position_size(
        self, 
        account_balance: float, 
        entry_price: float, 
        stop_price: float
    ) -> int:
        """
        Calculate position size based on risk
        """
        risk_amount = account_balance * self.risk_per_trade
        risk_per_unit = abs(entry_price - stop_price)
        
        if risk_per_unit == 0:
            return 0
            
        position_size = int(risk_amount / risk_per_unit)
        return position_size
    
    def backtest(
        self, 
        df: pd.DataFrame, 
        initial_balance: float = 10000
    ) -> pd.DataFrame:
        """
        Backtest the breakout strategy
        """
        df = self.generate_signals(df)
        
        balance = initial_balance
        equity_curve = []
        open_trade = None
        
        for i in range(1, len(df)):
            current = df.iloc[i]
            prev = df.iloc[i-1]
            
            # Check if we need to close open trade
            if open_trade:
                # Check take profit
                if open_trade.direction == 'long':
                    if current['High'] >= open_trade.take_profit:
                        open_trade.exit_price = open_trade.take_profit
                        open_trade.pnl = (open_trade.take_profit - open_trade.entry_price) * position_size
                        open_trade.exit_date = current.name
                        open_trade.status = 'closed'
                        balance += open_trade.pnl
                        self.trades.append(open_trade)
                        open_trade = None
                    elif current['Low'] <= open_trade.stop_loss:
                        open_trade.exit_price = open_trade.stop_loss
                        open_trade.pnl = (open_trade.stop_loss - open_trade.entry_price) * position_size
                        open_trade.exit_date = current.name
                        open_trade.status = 'closed'
                        balance += open_trade.pnl
                        self.trades.append(open_trade)
                        open_trade = None
                else:  # short
                    if current['Low'] <= open_trade.take_profit:
                        open_trade.exit_price = open_trade.take_profit
                        open_trade.pnl = (open_trade.entry_price - open_trade.take_profit) * position_size
                        open_trade.exit_date = current.name
                        open_trade.status = 'closed'
                        balance += open_trade.pnl
                        self.trades.append(open_trade)
                        open_trade = None
                    elif current['High'] >= open_trade.stop_loss:
                        open_trade.exit_price = open_trade.stop_loss
                        open_trade.pnl = (open_trade.entry_price - open_trade.stop_loss) * position_size
                        open_trade.exit_date = current.name
                        open_trade.status = 'closed'
                        balance += open_trade.pnl
                        self.trades.append(open_trade)
                        open_trade = None
            
            # Check for new entry if no open trade
            if open_trade is None:
                if current['Long_Signal']:
                    entry_price = current['Close']
                    stop_loss = prev['Support']  # Stop below previous support
                    risk = entry_price - stop_loss
                    take_profit = entry_price + (risk * self.risk_reward_ratio)
                    
                    position_size = self.calculate_position_size(
                        balance, entry_price, stop_loss
                    )
                    
                    if position_size > 0:
                        open_trade = Trade(
                            entry_date=current.name,
                            entry_price=entry_price,
                            stop_loss=stop_loss,
                            take_profit=take_profit,
                            direction='long'
                        )
                        
                elif current['Short_Signal']:
                    entry_price = current['Close']
                    stop_loss = prev['Resistance']  # Stop above previous resistance
                    risk = stop_loss - entry_price
                    take_profit = entry_price - (risk * self.risk_reward_ratio)
                    
                    position_size = self.calculate_position_size(
                        balance, entry_price, stop_loss
                    )
                    
                    if position_size > 0:
                        open_trade = Trade(
                            entry_date=current.name,
                            entry_price=entry_price,
                            stop_loss=stop_loss,
                            take_profit=take_profit,
                            direction='short'
                        )
            
            equity_curve.append({
                'Date': current.name,
                'Balance': balance,
                'Open_Trade': open_trade is not None
            })
        
        return pd.DataFrame(equity_curve).set_index('Date')
    
    def get_performance_metrics(self) -> dict:
        """Calculate performance metrics"""
        if not self.trades:
            return {}
        
        closed_trades = [t for t in self.trades if t.status == 'closed']
        if not closed_trades:
            return {}
        
        pnls = [t.pnl for t in closed_trades]
        winning_trades = [p for p in pnls if p > 0]
        losing_trades = [p for p in pnls if p < 0]
        
        return {
            'Total_Trades': len(closed_trades),
            'Winning_Trades': len(winning_trades),
            'Losing_Trades': len(losing_trades),
            'Win_Rate': len(winning_trades) / len(closed_trades) if closed_trades else 0,
            'Total_PnL': sum(pnls),
            'Avg_Win': np.mean(winning_trades) if winning_trades else 0,
            'Avg_Loss': np.mean(losing_trades) if losing_trades else 0,
            'Profit_Factor': abs(sum(winning_trades) / sum(losing_trades)) if losing_trades and sum(losing_trades) != 0 else float('inf'),
            'Max_Drawdown': self._calculate_max_drawdown(),
        }
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown from trade history"""
        # Simplified calculation
        return 0.0


def fetch_forex_data(symbol: str, period: str = "1y", interval: str = "1h") -> pd.DataFrame:
    """
    Fetch forex data using yfinance
    For XAUUSD use "GC=F" (Gold Futures)
    For USDJPY use "JPY=X"
    """
    ticker_map = {
        'XAUUSD': 'GC=F',  # Gold Futures
        'USDJPY': 'JPY=X',  # USD/JPY
    }
    
    yf_symbol = ticker_map.get(symbol, symbol)
    data = yf.download(yf_symbol, period=period, interval=interval)
    
    # Flatten multi-index if present
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    return data


if __name__ == "__main__":
    # Example usage
    print("=" * 60)
    print("BREAKOUT STRATEGY - XAUUSD/USDJPY")
    print("=" * 60)
    
    # Initialize strategy
    strategy = BreakoutStrategy(
        lookback_period=20,
        breakout_threshold=0.005,
        risk_per_trade=0.01,
        risk_reward_ratio=2.0
    )
    
    print("\nStrategy Parameters:")
    print(f"  Lookback Period: {strategy.lookback_period}")
    print(f"  Breakout Threshold: {strategy.breakout_threshold:.2%}")
    print(f"  Risk per Trade: {strategy.risk_per_trade:.2%}")
    print(f"  Risk-Reward Ratio: {strategy.risk_reward_ratio}:1")
    
    # Fetch data
    print("\nFetching XAUUSD (Gold) data...")
    try:
        data = fetch_forex_data('XAUUSD', period='1y', interval='1h')
        print(f"Data shape: {data.shape}")
        print(f"Date range: {data.index[0]} to {data.index[-1]}")
        
        # Run backtest
        print("\nRunning backtest...")
        equity = strategy.backtest(data, initial_balance=10000)
        
        # Get metrics
        metrics = strategy.get_performance_metrics()
        
        print("\n" + "=" * 60)
        print("BACKTEST RESULTS")
        print("=" * 60)
        for key, value in metrics.items():
            if isinstance(value, float):
                if 'Rate' in key or 'Drawdown' in key:
                    print(f"  {key}: {value:.2%}")
                else:
                    print(f"  {key}: ${value:,.2f}")
            else:
                print(f"  {key}: {value}")
        
        print(f"\nFinal Balance: ${equity['Balance'].iloc[-1]:,.2f}")
        print(f"Total Return: {(equity['Balance'].iloc[-1] / 10000 - 1):.2%}")
        
    except Exception as e:
        print(f"Error: {e}")
        print("Note: This requires yfinance and internet connection")
