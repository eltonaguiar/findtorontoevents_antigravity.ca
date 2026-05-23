"""
STRATEGY 2: THETA OPTIONS STRATEGY (u/heyredditaddict)
Based on: OTM Put/Call Selling on SPY with 31.7% returns, 3.87% max drawdown

Key Principles:
- Sell OTM puts and calls on SPY (90% of trades)
- Occasional far OTM IV crush plays
- Beat SPY benchmark (19.4%) with lower drawdown (3.87% vs 16.68%)
- Sharpe 2.93 vs 0.89 SPY
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import yfinance as yf


@dataclass
class OptionTrade:
    entry_date: pd.Timestamp
    option_type: str  # 'put' or 'call'
    strike: float
    premium: float
    dte: int  # days to expiration
    delta: float
    iv: float
    exit_date: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    status: str = 'open'
    assigned: bool = False


class ThetaStrategy:
    """
    Theta-based Options Selling Strategy on SPY
    
    Parameters:
    -----------
    delta_target : float
        Target delta for option selection (default 0.15-0.20)
    dte_target : int
        Target days to expiration (default 30-45)
    profit_target : float
        Percentage of max profit to take (default 50%)
    max_loss_multiplier : float
        Stop loss as multiple of premium received
    iv_rank_threshold : float
        Minimum IV rank to sell (default 30)
    """
    
    def __init__(
        self,
        delta_target: float = 0.16,
        dte_target: int = 30,
        profit_target: float = 0.50,
        max_loss_multiplier: float = 2.0,
        iv_rank_threshold: float = 30,
        allocation_per_trade: float = 0.10  # 10% of account per trade
    ):
        self.delta_target = delta_target
        self.dte_target = dte_target
        self.profit_target = profit_target
        self.max_loss_multiplier = max_loss_multiplier
        self.iv_rank_threshold = iv_rank_threshold
        self.allocation_per_trade = allocation_per_trade
        self.trades: List[OptionTrade] = []
        
    def calculate_iv_rank(self, df: pd.DataFrame, lookback: int = 252) -> pd.Series:
        """
        Calculate IV Rank (current IV relative to 1-year range)
        Using realized volatility as proxy for IV
        """
        # Calculate realized volatility
        returns = df['Close'].pct_change()
        realized_vol = returns.rolling(20).std() * np.sqrt(252) * 100
        
        # Calculate rank
        vol_low = realized_vol.rolling(lookback).min()
        vol_high = realized_vol.rolling(lookback).max()
        
        iv_rank = 100 * (realized_vol - vol_low) / (vol_high - vol_low)
        return iv_rank.fillna(50)  # Default to middle if insufficient data
    
    def calculate_historical_volatility(
        self, 
        df: pd.DataFrame, 
        window: int = 20
    ) -> pd.Series:
        """Calculate annualized historical volatility"""
        returns = df['Close'].pct_change()
        hv = returns.rolling(window).std() * np.sqrt(252)
        return hv
    
    def estimate_option_price(
        self,
        underlying_price: float,
        strike: float,
        dte: int,
        iv: float,
        option_type: str
    ) -> float:
        """
        Simplified Black-Scholes for option pricing
        """
        from scipy.stats import norm
        
        S = underlying_price
        K = strike
        T = dte / 365.0
        r = 0.05  # risk-free rate
        sigma = iv
        
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        if option_type == 'call':
            price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        else:
            price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        
        return max(price, 0.01)
    
    def select_strike(
        self,
        underlying_price: float,
        iv: float,
        option_type: str,
        delta_target: float = 0.16
    ) -> float:
        """
        Select strike based on delta target
        Approximation: delta ~ N(d1) for calls, N(d1) - 1 for puts
        """
        # Simplified: strike selection based on standard deviations
        # 0.16 delta roughly corresponds to 1 standard deviation OTM
        
        distance = iv * np.sqrt(self.dte_target / 365)
        
        if option_type == 'put':
            strike = underlying_price * (1 - distance)
        else:
            strike = underlying_price * (1 + distance)
        
        # Round to nearest option strike (SPY strikes every $1)
        return round(strike)
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate option selling signals
        """
        df = df.copy()
        
        # Calculate indicators
        df['HV'] = self.calculate_historical_volatility(df)
        df['IV_Rank'] = self.calculate_iv_rank(df)
        
        # Moving averages for trend
        df['SMA_50'] = df['Close'].rolling(50).mean()
        df['SMA_200'] = df['Close'].rolling(200).mean()
        
        # Trend determination
        df['Trend'] = np.where(
            df['SMA_50'] > df['SMA_200'], 'bullish',
            np.where(df['SMA_50'] < df['SMA_200'], 'bearish', 'neutral')
        )
        
        # Signal generation
        # Sell puts in bullish/neutral, sell calls in bearish/neutral
        # Only when IV rank is elevated
        df['Sell_Put_Signal'] = (
            (df['Trend'].isin(['bullish', 'neutral'])) &
            (df['IV_Rank'] > self.iv_rank_threshold)
        )
        
        df['Sell_Call_Signal'] = (
            (df['Trend'].isin(['bearish', 'neutral'])) &
            (df['IV_Rank'] > self.iv_rank_threshold)
        )
        
        return df
    
    def backtest(
        self,
        df: pd.DataFrame,
        initial_balance: float = 100000,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Backtest the theta strategy
        
        Note: This is a simplified simulation. Real options backtesting
        requires historical options chain data.
        """
        df = self.generate_signals(df)
        
        if start_date:
            df = df[df.index >= start_date]
        if end_date:
            df = df[df.index <= end_date]
        
        balance = initial_balance
        equity_curve = []
        open_trades: List[OptionTrade] = []
        
        # Rebalance frequency (weekly)
        last_trade_date = None
        
        for i, (date, row) in enumerate(df.iterrows()):
            # Check for expirations and manage open trades
            trades_to_close = []
            
            for trade in open_trades:
                days_held = (date - trade.entry_date).days
                
                # Simulate theta decay (simplified)
                # Premium decays over time
                if days_held >= trade.dte:
                    # Expiration
                    if trade.option_type == 'put':
                        assigned = row['Close'] < trade.strike
                    else:
                        assigned = row['Close'] > trade.strike
                    
                    trade.exit_date = date
                    trade.status = 'closed'
                    trade.assigned = assigned
                    
                    if assigned:
                        # Assignment - loss equal to intrinsic value
                        if trade.option_type == 'put':
                            intrinsic = max(0, trade.strike - row['Close'])
                        else:
                            intrinsic = max(0, row['Close'] - trade.strike)
                        trade.pnl = trade.premium - intrinsic
                    else:
                        # Full profit
                        trade.pnl = trade.premium
                    
                    balance += trade.pnl
                    trades_to_close.append(trade)
                else:
                    # Check for early profit taking (50% of max profit)
                    theta_decay = days_held / trade.dte
                    current_value = trade.premium * (1 - theta_decay * 0.7)  # Accelerated decay
                    unrealized_pnl = trade.premium - current_value
                    
                    if unrealized_pnl >= trade.premium * self.profit_target:
                        trade.exit_date = date
                        trade.exit_price = current_value
                        trade.pnl = unrealized_pnl
                        trade.status = 'closed'
                        balance += trade.pnl
                        trades_to_close.append(trade)
            
            # Remove closed trades
            for trade in trades_to_close:
                if trade in open_trades:
                    open_trades.remove(trade)
                    self.trades.append(trade)
            
            # Open new trades (weekly, max 2 positions)
            if (last_trade_date is None or 
                (date - last_trade_date).days >= 7) and len(open_trades) < 2:
                
                position_size = balance * self.allocation_per_trade
                
                if row['Sell_Put_Signal'] and len(open_trades) < 2:
                    strike = self.select_strike(
                        row['Close'], row['HV'], 'put', self.delta_target
                    )
                    
                    # Estimate premium (simplified)
                    premium = self.estimate_option_price(
                        row['Close'], strike, self.dte_target, row['HV'], 'put'
                    )
                    
                    trade = OptionTrade(
                        entry_date=date,
                        option_type='put',
                        strike=strike,
                        premium=premium,
                        dte=self.dte_target,
                        delta=self.delta_target,
                        iv=row['HV']
                    )
                    open_trades.append(trade)
                    last_trade_date = date
                    
                elif row['Sell_Call_Signal'] and len(open_trades) < 2:
                    strike = self.select_strike(
                        row['Close'], row['HV'], 'call', self.delta_target
                    )
                    
                    premium = self.estimate_option_price(
                        row['Close'], strike, self.dte_target, row['HV'], 'call'
                    )
                    
                    trade = OptionTrade(
                        entry_date=date,
                        option_type='call',
                        strike=strike,
                        premium=premium,
                        dte=self.dte_target,
                        delta=self.delta_target,
                        iv=row['HV']
                    )
                    open_trades.append(trade)
                    last_trade_date = date
            
            # Calculate unrealized P&L
            unrealized = sum(
                t.premium * 0.5 for t in open_trades if t.status == 'open'
            )
            
            equity_curve.append({
                'Date': date,
                'Balance': balance,
                'Equity': balance + unrealized,
                'Open_Trades': len(open_trades),
                'IV_Rank': row['IV_Rank']
            })
        
        return pd.DataFrame(equity_curve).set_index('Date')
    
    def get_performance_metrics(self, equity_df: pd.DataFrame) -> Dict:
        """Calculate performance metrics"""
        equity = equity_df['Equity']
        returns = equity.pct_change().dropna()
        
        # Total return
        total_return = (equity.iloc[-1] / equity.iloc[0]) - 1
        
        # Annualized return
        years = len(equity) / 252
        cagr = (1 + total_return) ** (1/years) - 1 if years > 0 else 0
        
        # Volatility
        volatility = returns.std() * np.sqrt(252)
        
        # Sharpe ratio (assuming 5% risk-free)
        sharpe = (cagr - 0.05) / volatility if volatility > 0 else 0
        
        # Max drawdown
        peak = equity.expanding().max()
        drawdown = (equity - peak) / peak
        max_drawdown = drawdown.min()
        
        # Trade metrics
        closed_trades = [t for t in self.trades if t.status == 'closed']
        winning_trades = [t for t in closed_trades if t.pnl > 0]
        
        return {
            'Total_Return': total_return,
            'CAGR': cagr,
            'Volatility': volatility,
            'Sharpe_Ratio': sharpe,
            'Max_Drawdown': max_drawdown,
            'Total_Trades': len(closed_trades),
            'Win_Rate': len(winning_trades) / len(closed_trades) if closed_trades else 0,
            'Avg_Premium': np.mean([t.premium for t in closed_trades]) if closed_trades else 0,
        }


def fetch_spy_data(period: str = "5y") -> pd.DataFrame:
    """Fetch SPY data"""
    spy = yf.download('SPY', period=period, interval='1d')
    
    # Flatten multi-index if present
    if isinstance(spy.columns, pd.MultiIndex):
        spy.columns = spy.columns.get_level_values(0)
    
    return spy


if __name__ == "__main__":
    print("=" * 60)
    print("THETA OPTIONS STRATEGY - SPY")
    print("=" * 60)
    
    strategy = ThetaStrategy(
        delta_target=0.16,
        dte_target=30,
        profit_target=0.50,
        allocation_per_trade=0.10
    )
    
    print("\nStrategy Parameters:")
    print(f"  Delta Target: {strategy.delta_target}")
    print(f"  DTE Target: {strategy.dte_target}")
    print(f"  Profit Target: {strategy.profit_target:.0%}")
    print(f"  Allocation per Trade: {strategy.allocation_per_trade:.0%}")
    
    print("\nFetching SPY data...")
    try:
        data = fetch_spy_data(period='3y')
        print(f"Data shape: {data.shape}")
        
        print("\nRunning backtest...")
        equity = strategy.backtest(data, initial_balance=100000)
        
        metrics = strategy.get_performance_metrics(equity)
        
        print("\n" + "=" * 60)
        print("BACKTEST RESULTS")
        print("=" * 60)
        print(f"  Total Return: {metrics['Total_Return']:.2%}")
        print(f"  CAGR: {metrics['CAGR']:.2%}")
        print(f"  Volatility: {metrics['Volatility']:.2%}")
        print(f"  Sharpe Ratio: {metrics['Sharpe_Ratio']:.2f}")
        print(f"  Max Drawdown: {metrics['Max_Drawdown']:.2%}")
        print(f"  Total Trades: {metrics['Total_Trades']}")
        print(f"  Win Rate: {metrics['Win_Rate']:.2%}")
        print(f"  Avg Premium: ${metrics['Avg_Premium']:.2f}")
        
        print(f"\nFinal Equity: ${equity['Equity'].iloc[-1]:,.2f}")
        
        # Compare to buy and hold
        spy_return = (data['Close'].iloc[-1] / data['Close'].iloc[0]) - 1
        print(f"\nSPY Buy & Hold Return: {spy_return:.2%}")
        print(f"Strategy Outperformance: {metrics['Total_Return'] - spy_return:.2%}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
