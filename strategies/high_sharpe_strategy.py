"""
High Sharpe Ratio Momentum Strategy - Python Implementation
===========================================================

This module implements the complete High Sharpe Ratio Momentum trading strategy
for S&P 500 stocks with quarterly rebalancing.

Author: Trading Competition Team
Version: 1.0
Date: February 2025
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


class HighSharpeMomentumStrategy:
    """
    High Sharpe Ratio Momentum Strategy implementation.
    
    Strategy Rules:
    - Universe: S&P 500 constituents
    - Entry: Sharpe > 1.0, Price > 50 SMA, Volume > 1M
    - Exit: Sharpe < 0.8, Price < 200 SMA, -15% stop loss
    - Position sizing: Equal weight (10% per position, max 10 positions)
    - Rebalancing: Quarterly (Mar, Jun, Sep, Dec)
    """
    
    def __init__(self, 
                 risk_free_rate: float = 0.045,
                 min_sharpe_entry: float = 1.0,
                 min_sharpe_exit: float = 0.8,
                 max_positions: int = 10,
                 position_size: float = 0.10,
                 stop_loss_pct: float = -0.15,
                 max_sector_pct: float = 0.30,
                 min_volume: int = 1_000_000,
                 lookback_years: int = 3):
        """
        Initialize strategy parameters.
        
        Args:
            risk_free_rate: Annual risk-free rate (default 4.5%)
            min_sharpe_entry: Minimum Sharpe ratio for entry (default 1.0)
            min_sharpe_exit: Sharpe ratio threshold for exit (default 0.8)
            max_positions: Maximum number of positions (default 10)
            position_size: Target position size as % of portfolio (default 10%)
            stop_loss_pct: Stop loss percentage (default -15%)
            max_sector_pct: Maximum sector concentration (default 30%)
            min_volume: Minimum average daily volume (default 1M)
            lookback_years: Years of data for Sharpe calculation (default 3)
        """
        self.risk_free_rate = risk_free_rate
        self.min_sharpe_entry = min_sharpe_entry
        self.min_sharpe_exit = min_sharpe_exit
        self.max_positions = max_positions
        self.position_size = position_size
        self.stop_loss_pct = stop_loss_pct
        self.max_sector_pct = max_sector_pct
        self.min_volume = min_volume
        self.lookback_years = lookback_years
        self.lookback_days = lookback_years * 252
        
        # Cache for data
        self._price_cache = {}
        self._sp500_list = None
        
    def get_sp500_tickers(self) -> List[str]:
        """
        Fetch current S&P 500 constituent list from Wikipedia.
        
        Returns:
            List of S&P 500 ticker symbols
        """
        if self._sp500_list is not None:
            return self._sp500_list
            
        try:
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            tables = pd.read_html(url)
            sp500_df = tables[0]
            tickers = sp500_df['Symbol'].tolist()
            
            # Clean tickers (handle BRK.B, BF.B, etc.)
            tickers = [t.replace('.', '-') for t in tickers]
            
            self._sp500_list = tickers
            return tickers
        except Exception as e:
            print(f"Error fetching S&P 500 list: {e}")
            # Fallback to common S&P 500 tickers
            return self._get_fallback_tickers()
    
    def _get_fallback_tickers(self) -> List[str]:
        """Fallback list of major S&P 500 tickers."""
        return [
            'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'GOOG', 'META', 'TSLA', 'NVDA',
            'BRK-B', 'JPM', 'JNJ', 'V', 'PG', 'UNH', 'HD', 'MA', 'BAC', 'ABBV',
            'PFE', 'KO', 'AVGO', 'PEP', 'TMO', 'COST', 'DIS', 'CSCO', 'VZ',
            'ADBE', 'WMT', 'MRK', 'NKE', 'ABT', 'CMCSA', 'XOM', 'CVX', 'ACN',
            'TXN', 'CRM', 'LLY', 'PM', 'NEE', 'RTX', 'NFLX', 'BMY', 'QCOM',
            'HON', 'ORCL', 'AMGN', 'IBM', 'LOW', 'INTC', 'UPS', 'SBUX'
        ]
    
    def download_data(self, tickers: List[str], period: str = "3y") -> Dict[str, pd.DataFrame]:
        """
        Download historical price data for multiple tickers.
        
        Args:
            tickers: List of ticker symbols
            period: Data period (default "3y")
            
        Returns:
            Dictionary mapping ticker to price DataFrame
        """
        data = {}
        batch_size = 50  # Download in batches to avoid rate limits
        
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i+batch_size]
            try:
                batch_data = yf.download(
                    batch, 
                    period=period, 
                    progress=False,
                    auto_adjust=True
                )
                
                # Handle single vs multiple tickers
                if len(batch) == 1:
                    ticker = batch[0]
                    df = pd.DataFrame({
                        'Open': batch_data['Open'],
                        'High': batch_data['High'],
                        'Low': batch_data['Low'],
                        'Close': batch_data['Close'],
                        'Volume': batch_data['Volume']
                    })
                    data[ticker] = df
                else:
                    for ticker in batch:
                        df = pd.DataFrame({
                            'Open': batch_data['Open'][ticker],
                            'High': batch_data['High'][ticker],
                            'Low': batch_data['Low'][ticker],
                            'Close': batch_data['Close'][ticker],
                            'Volume': batch_data['Volume'][ticker]
                        })
                        data[ticker] = df
                        
            except Exception as e:
                print(f"Error downloading batch {batch}: {e}")
                continue
                
        return data
    
    def calculate_sharpe_ratio(self, prices: pd.Series) -> float:
        """
        Calculate annualized Sharpe ratio from price series.
        
        Args:
            prices: Series of closing prices
            
        Returns:
            Annualized Sharpe ratio
        """
        if len(prices) < 252:  # Need at least 1 year of data
            return -999
        
        # Calculate daily returns
        returns = prices.pct_change().dropna()
        
        if len(returns) < 50 or returns.std() == 0:
            return -999
        
        # Annualized metrics
        annualized_return = returns.mean() * 252
        annualized_volatility = returns.std() * np.sqrt(252)
        
        # Sharpe ratio
        sharpe = (annualized_return - self.risk_free_rate) / annualized_volatility
        
        return sharpe
    
    def get_momentum_signals(self, prices: pd.Series) -> Dict:
        """
        Calculate momentum indicators.
        
        Args:
            prices: Series of closing prices
            
        Returns:
            Dictionary with momentum signals
        """
        current_price = prices.iloc[-1]
        
        # Moving averages
        sma_50 = prices.rolling(50).mean().iloc[-1]
        sma_200 = prices.rolling(200).mean().iloc[-1]
        
        return {
            'current_price': current_price,
            'sma_50': sma_50,
            'sma_200': sma_200,
            'above_50_sma': current_price > sma_50,
            'above_200_sma': current_price > sma_200,
            'price_to_50_sma': current_price / sma_50 - 1,
            'price_to_200_sma': current_price / sma_200 - 1
        }
    
    def screen_stock(self, ticker: str, data: pd.DataFrame) -> Optional[Dict]:
        """
        Screen a single stock against strategy criteria.
        
        Args:
            ticker: Stock ticker symbol
            data: Price DataFrame
            
        Returns:
            Dictionary with stock metrics if qualified, None otherwise
        """
        if data is None or len(data) < self.lookback_days * 0.9:
            return None
        
        try:
            # Calculate metrics
            sharpe = self.calculate_sharpe_ratio(data['Close'])
            momentum = self.get_momentum_signals(data['Close'])
            avg_volume = data['Volume'].mean()
            
            # Check entry criteria
            qualified = (
                sharpe > self.min_sharpe_entry and
                momentum['above_50_sma'] and
                avg_volume >= self.min_volume
            )
            
            return {
                'ticker': ticker,
                'sharpe_ratio': sharpe,
                'current_price': momentum['current_price'],
                'sma_50': momentum['sma_50'],
                'sma_200': momentum['sma_200'],
                'above_50_sma': momentum['above_50_sma'],
                'above_200_sma': momentum['above_200_sma'],
                'avg_volume': avg_volume,
                'qualified': qualified
            }
            
        except Exception as e:
            print(f"Error screening {ticker}: {e}")
            return None
    
    def screen_universe(self, tickers: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Screen entire universe and return qualified stocks.
        
        Args:
            tickers: Optional list of tickers (defaults to S&P 500)
            
        Returns:
            DataFrame with screening results
        """
        if tickers is None:
            tickers = self.get_sp500_tickers()
        
        print(f"Screening {len(tickers)} stocks...")
        
        # Download data
        data = self.download_data(tickers)
        
        # Screen each stock
        results = []
        for ticker in tickers:
            if ticker in data:
                result = self.screen_stock(ticker, data[ticker])
                if result:
                    results.append(result)
        
        # Create DataFrame
        df = pd.DataFrame(results)
        
        if len(df) == 0:
            return pd.DataFrame()
        
        # Sort by Sharpe ratio
        df = df.sort_values('sharpe_ratio', ascending=False)
        
        return df
    
    def get_top_picks(self, df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
        """
        Get top N qualified stocks by Sharpe ratio.
        
        Args:
            df: Screening results DataFrame
            n: Number of stocks to select
            
        Returns:
            DataFrame with top picks
        """
        qualified = df[df['qualified'] == True]
        return qualified.head(n).copy()
    
    def check_exit(self, position: Dict, current_data: pd.DataFrame) -> Tuple[bool, str]:
        """
        Check if a position should be exited.
        
        Args:
            position: Position dictionary with entry info
            current_data: Current price data
            
        Returns:
            Tuple of (should_exit, reason)
        """
        ticker = position['ticker']
        entry_price = position.get('entry_price', 0)
        
        try:
            # Check Sharpe degradation
            current_sharpe = self.calculate_sharpe_ratio(current_data['Close'])
            if current_sharpe < self.min_sharpe_exit:
                return True, f"Sharpe ratio {current_sharpe:.2f} below {self.min_sharpe_exit}"
            
            # Check trend break (200 SMA)
            momentum = self.get_momentum_signals(current_data['Close'])
            if not momentum['above_200_sma']:
                return True, f"Price below 200-day SMA"
            
            # Check stop loss
            current_price = momentum['current_price']
            if entry_price > 0:
                return_pct = (current_price - entry_price) / entry_price
                if return_pct <= self.stop_loss_pct:
                    return True, f"Stop loss triggered at {return_pct:.1%}"
            
            return False, ""
            
        except Exception as e:
            print(f"Error checking exit for {ticker}: {e}")
            return False, ""
    
    def calculate_position_sizes(self, 
                                  portfolio_value: float, 
                                  target_stocks: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate position sizes for target stocks.
        
        Args:
            portfolio_value: Total portfolio value
            target_stocks: DataFrame with target stocks
            
        Returns:
            Dictionary mapping ticker to position value
        """
        positions = {}
        target_value = portfolio_value * self.position_size
        
        for _, stock in target_stocks.iterrows():
            ticker = stock['ticker']
            positions[ticker] = min(target_value, portfolio_value * 0.10)
        
        return positions
    
    def generate_rebalance_orders(self,
                                   current_portfolio: Dict[str, Dict],
                                   target_stocks: pd.DataFrame,
                                   portfolio_value: float) -> Dict:
        """
        Generate buy/sell orders for rebalancing.
        
        Args:
            current_portfolio: Dictionary of current positions
            target_stocks: DataFrame with target stocks
            portfolio_value: Total portfolio value
            
        Returns:
            Dictionary with orders
        """
        target_tickers = set(target_stocks['ticker'].tolist())
        current_tickers = set(current_portfolio.keys())
        
        # Calculate target positions
        target_positions = self.calculate_position_sizes(portfolio_value, target_stocks)
        
        orders = {
            'sell': [],
            'buy': [],
            'hold': []
        }
        
        # Determine sells
        for ticker in current_tickers:
            if ticker not in target_tickers:
                # Check if we need to exit
                position = current_portfolio[ticker]
                current_value = position.get('current_value', 0)
                orders['sell'].append({
                    'ticker': ticker,
                    'value': current_value,
                    'reason': 'Rebalancing - dropped from top 10'
                })
        
        # Determine buys
        for ticker in target_tickers:
            target_value = target_positions.get(ticker, 0)
            
            if ticker in current_portfolio:
                current_value = current_portfolio[ticker].get('current_value', 0)
                delta = target_value - current_value
                
                if abs(delta) > portfolio_value * 0.02:  # 2% threshold
                    if delta > 0:
                        orders['buy'].append({
                            'ticker': ticker,
                            'value': delta,
                            'reason': 'Rebalancing - increase position'
                        })
                    else:
                        orders['sell'].append({
                            'ticker': ticker,
                            'value': abs(delta),
                            'reason': 'Rebalancing - reduce position'
                        })
                else:
                    orders['hold'].append({
                        'ticker': ticker,
                        'value': current_value
                    })
            else:
                orders['buy'].append({
                    'ticker': ticker,
                    'value': target_value,
                    'reason': 'New position'
                })
        
        return orders
    
    def run_screening(self) -> pd.DataFrame:
        """
        Run full screening and return top 10 picks.
        
        Returns:
            DataFrame with top 10 qualified stocks
        """
        results = self.screen_universe()
        top_picks = self.get_top_picks(results, n=self.max_positions)
        
        print(f"\n=== TOP {self.max_positions} HIGH SHARPE MOMENTUM PICKS ===")
        print(top_picks[['ticker', 'sharpe_ratio', 'current_price', 
                         'above_50_sma', 'above_200_sma', 'avg_volume']].to_string(index=False))
        
        return top_picks


class PortfolioTracker:
    """Track portfolio performance and generate reports."""
    
    def __init__(self, strategy: HighSharpeMomentumStrategy):
        self.strategy = strategy
        self.positions = {}
        self.trades = []
        self.daily_values = []
        
    def add_position(self, ticker: str, shares: float, entry_price: float, 
                     entry_date: datetime):
        """Add a new position."""
        self.positions[ticker] = {
            'ticker': ticker,
            'shares': shares,
            'entry_price': entry_price,
            'entry_date': entry_date,
            'current_price': entry_price,
            'current_value': shares * entry_price,
            'unrealized_pnl': 0,
            'unrealized_pnl_pct': 0
        }
    
    def update_prices(self, price_data: Dict[str, float]):
        """Update current prices for all positions."""
        for ticker, price in price_data.items():
            if ticker in self.positions:
                pos = self.positions[ticker]
                pos['current_price'] = price
                pos['current_value'] = pos['shares'] * price
                pos['unrealized_pnl'] = pos['current_value'] - (pos['shares'] * pos['entry_price'])
                pos['unrealized_pnl_pct'] = pos['unrealized_pnl'] / (pos['shares'] * pos['entry_price'])
    
    def get_portfolio_value(self) -> float:
        """Get total portfolio value."""
        return sum(pos['current_value'] for pos in self.positions.values())
    
    def get_position_summary(self) -> pd.DataFrame:
        """Get summary of all positions."""
        return pd.DataFrame(self.positions.values())
    
    def record_trade(self, ticker: str, action: str, shares: float, 
                     price: float, date: datetime, reason: str = ""):
        """Record a trade."""
        self.trades.append({
            'date': date,
            'ticker': ticker,
            'action': action,
            'shares': shares,
            'price': price,
            'value': shares * price,
            'reason': reason
        })
    
    def get_trade_history(self) -> pd.DataFrame:
        """Get trade history."""
        return pd.DataFrame(self.trades)


def run_example():
    """Run example screening."""
    print("=" * 60)
    print("HIGH SHARPE RATIO MOMENTUM STRATEGY")
    print("=" * 60)
    
    # Initialize strategy
    strategy = HighSharpeMomentumStrategy()
    
    # Run screening on a subset for demo (full S&P 500 takes time)
    demo_tickers = [
        'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'NVDA', 'TSLA',
        'JPM', 'JNJ', 'V', 'PG', 'UNH', 'HD', 'MA', 'BAC',
        'ABBV', 'PFE', 'KO', 'AVGO', 'PEP', 'TMO', 'COST'
    ]
    
    print(f"\nRunning demo screening on {len(demo_tickers)} stocks...")
    print("(Full S&P 500 screening would take several minutes)")
    
    results = strategy.screen_universe(demo_tickers)
    top_picks = strategy.get_top_picks(results)
    
    print("\n" + "=" * 60)
    print("TOP HIGH SHARPE MOMENTUM PICKS")
    print("=" * 60)
    
    for idx, row in top_picks.iterrows():
        print(f"\n{row['ticker']}:")
        print(f"  Sharpe Ratio: {row['sharpe_ratio']:.2f}")
        print(f"  Price: ${row['current_price']:.2f}")
        print(f"  Above 50 SMA: {row['above_50_sma']}")
        print(f"  Above 200 SMA: {row['above_200_sma']}")
        print(f"  Avg Volume: {row['avg_volume']:,.0f}")
    
    return strategy, top_picks


if __name__ == "__main__":
    strategy, picks = run_example()
