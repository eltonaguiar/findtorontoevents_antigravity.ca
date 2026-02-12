"""
Momentum Factor Implementation for Stock Algorithms

This script implements a robust momentum factor based on academic research (Jegadeesh & Titman, 1993).
It calculates momentum scores for stocks and can be integrated into existing algorithms like Technical Momentum.

Features:
- Calculates momentum over multiple lookback periods (e.g., 1-12 months)
- Uses cumulative returns to avoid short-term noise
- Includes risk adjustments (volatility normalization)
- Outputs scores for ranking and selection

Usage:
- Run with a list of tickers to get momentum scores
- Integrate into backtesting frameworks like Backtrader or QuantConnect

Dependencies: pandas, yfinance, numpy
"""

import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta

class MomentumFactor:
    def __init__(self, lookback_periods=[1, 3, 6, 12], risk_adjusted=True):
        """
        Initialize momentum factor calculator.

        Args:
            lookback_periods: List of months to calculate momentum over
            risk_adjusted: Whether to normalize by volatility
        """
        self.lookback_periods = lookback_periods
        self.risk_adjusted = risk_adjusted

    def calculate_momentum(self, prices, period_months):
        """
        Calculate momentum score for a given lookback period.

        Args:
            prices: DataFrame of daily prices (columns = tickers, index = dates)
            period_months: Lookback period in months

        Returns:
            Series of momentum scores
        """
        # Calculate cumulative returns over the period
        lookback_days = period_months * 21  # Approximate trading days per month
        returns = prices.pct_change(lookback_days).iloc[-1]  # Latest period return

        if self.risk_adjusted:
            # Normalize by volatility (standard deviation of returns)
            vol = prices.pct_change().rolling(lookback_days).std().iloc[-1]
            returns = returns / vol.replace(0, np.inf)  # Avoid division by zero

        return returns

    def get_momentum_scores(self, tickers, start_date=None, end_date=None):
        """
        Calculate momentum scores for a list of tickers.

        Args:
            tickers: List of stock tickers
            start_date: Start date for data (default: 2 years ago)
            end_date: End date for data (default: today)

        Returns:
            DataFrame with momentum scores for each period
        """
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=730)  # 2 years

        # Download historical data
        data = yf.download(tickers, start=start_date, end=end_date, progress=False)

        if 'Adj Close' in data.columns:
            prices = data['Adj Close']
        else:
            prices = data['Close']

        # Calculate momentum for each period
        scores = {}
        for period in self.lookback_periods:
            scores[f'momentum_{period}m'] = self.calculate_momentum(prices, period)

        return pd.DataFrame(scores)

    def rank_stocks(self, scores_df, top_n=10):
        """
        Rank stocks based on momentum scores.

        Args:
            scores_df: DataFrame from get_momentum_scores
            top_n: Number of top stocks to return

        Returns:
            Series of top-ranked tickers
        """
        # Average momentum across periods for composite score
        composite_score = scores_df.mean(axis=1)
        ranked = composite_score.sort_values(ascending=False)
        return ranked.head(top_n)

# Example usage
if __name__ == "__main__":
    # Sample tickers (can be expanded)
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX']

    # Initialize momentum calculator
    momentum = MomentumFactor(lookback_periods=[1, 3, 6, 12], risk_adjusted=True)

    # Get scores
    scores = momentum.get_momentum_scores(tickers)
    print("Momentum Scores:")
    print(scores)

    # Rank top stocks
    top_stocks = momentum.rank_stocks(scores, top_n=5)
    print("\nTop 5 Momentum Stocks:")
    print(top_stocks)