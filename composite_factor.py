"""
Composite Factor Model: Momentum + Sentiment

This script combines momentum and sentiment factors into a composite score for stock selection.
Based on academic research, it weights factors and provides a ranked list of stocks.

Features:
- Integrates momentum scores from momentum_factor.py
- Incorporates sentiment scores from sentiment_analyzer.py
- Allows customizable weighting
- Outputs composite rankings for trading signals

Usage:
- Run with tickers to get composite scores
- Use in backtesting or live trading

Dependencies: pandas, numpy, yfinance, transformers, torch
"""

import pandas as pd
import numpy as np
from momentum_factor import MomentumFactor
from sentiment_analyzer import SentimentAnalyzer

class CompositeFactor:
    def __init__(self, momentum_weight=0.7, sentiment_weight=0.3):
        """
        Initialize composite factor model.

        Args:
            momentum_weight: Weight for momentum factor (0-1)
            sentiment_weight: Weight for sentiment factor (0-1)
        """
        self.momentum_weight = momentum_weight
        self.sentiment_weight = sentiment_weight
        self.momentum = MomentumFactor()
        self.sentiment = SentimentAnalyzer()

    def get_composite_scores(self, tickers, news_data=None):
        """
        Calculate composite scores combining momentum and sentiment.

        Args:
            tickers: List of stock tickers
            news_data: Dict of {ticker: list of news headlines} (optional)

        Returns:
            DataFrame with individual and composite scores
        """
        # Get momentum scores
        momentum_scores = self.momentum.get_momentum_scores(tickers)
        momentum_composite = momentum_scores.mean(axis=1)  # Average across periods

        # Get sentiment scores (if news data provided)
        if news_data:
            ticker_sentiments = {}
            for ticker, headlines in news_data.items():
                if ticker in tickers:
                    sentiments = self.sentiment.analyze_batch(headlines)
                    ticker_sentiments[ticker] = sentiments
            sentiment_df = self.sentiment.aggregate_sentiment(ticker_sentiments)
            sentiment_scores = sentiment_df['net_sentiment']
        else:
            # Default neutral sentiment if no data
            sentiment_scores = pd.Series(0, index=tickers)

        # Combine into composite score
        composite = pd.DataFrame({
            'momentum_score': momentum_composite,
            'sentiment_score': sentiment_scores,
        })

        # Normalize scores to 0-1 scale for weighting
        composite['momentum_norm'] = (composite['momentum_score'] - composite['momentum_score'].min()) / (composite['momentum_score'].max() - composite['momentum_score'].min())
        composite['sentiment_norm'] = (composite['sentiment_score'] - composite['sentiment_score'].min()) / (composite['sentiment_score'].max() - composite['sentiment_score'].min())

        # Weighted composite
        composite['composite_score'] = (
            self.momentum_weight * composite['momentum_norm'] +
            self.sentiment_weight * composite['sentiment_norm']
        )

        return composite.sort_values('composite_score', ascending=False)

# Example usage
if __name__ == "__main__":
    # Sample tickers and news
    tickers = ['AAPL', 'TSLA', 'GOOGL', 'NVDA']
    news_data = {
        'AAPL': ["Apple announces record iPhone sales!", "Apple faces minor supply issues."],
        'TSLA': ["Tesla beats earnings, demand soars.", "Tesla autopilot recall."],
        'GOOGL': ["Google AI breakthrough.", "Alphabet antitrust fine."],
        'NVDA': ["NVIDIA chips in high demand.", "GPU shortages continue."]
    }

    # Initialize composite model
    composite = CompositeFactor(momentum_weight=0.7, sentiment_weight=0.3)

    # Get scores
    scores = composite.get_composite_scores(tickers, news_data)
    print("Composite Factor Scores:")
    print(scores[['momentum_score', 'sentiment_score', 'composite_score']])

    # Top picks
    top_picks = scores.head(2)
    print("\nTop 2 Composite Picks:")
    print(top_picks.index.tolist())