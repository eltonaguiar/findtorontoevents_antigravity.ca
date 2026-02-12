"""
NLP Sentiment Analysis for Stock Algorithms

This script implements sentiment analysis on news articles and financial filings using open-source NLP models.
Based on academic research (Tetlock, 2007; Loughran & McDonald, 2011), it can enhance factor models by incorporating textual data.

Features:
- Uses pre-trained transformer models for sentiment scoring
- Processes news headlines or article snippets
- Integrates with stock tickers for sentiment aggregation
- Outputs sentiment scores for use in trading signals

Usage:
- Provide text data (e.g., news headlines) and get sentiment scores
- Combine with momentum or other factors for composite signals

Dependencies: transformers, torch, pandas
"""

from transformers import pipeline
import pandas as pd
import torch
import numpy as np

class SentimentAnalyzer:
    def __init__(self, model_name="cardiffnlp/twitter-roberta-base-sentiment-latest"):
        """
        Initialize sentiment analyzer with a pre-trained model.

        Args:
            model_name: HuggingFace model for sentiment analysis
        """
        self.sentiment_pipeline = pipeline("sentiment-analysis", model=model_name, tokenizer=model_name)

    def analyze_text(self, text):
        """
        Analyze sentiment of a single text.

        Args:
            text: String of text to analyze

        Returns:
            Dict with label (POSITIVE/NEGATIVE/NEUTRAL) and score
        """
        result = self.sentiment_pipeline(text)[0]
        return {
            'label': result['label'],
            'score': result['score']
        }

    def analyze_batch(self, texts):
        """
        Analyze sentiment for a batch of texts.

        Args:
            texts: List of strings

        Returns:
            List of sentiment dicts
        """
        results = self.sentiment_pipeline(texts)
        return [{'label': r['label'], 'score': r['score']} for r in results]

    def aggregate_sentiment(self, ticker_sentiments):
        """
        Aggregate sentiment scores for tickers.

        Args:
            ticker_sentiments: Dict of {ticker: list of sentiment dicts}

        Returns:
            DataFrame with average sentiment scores per ticker
        """
        aggregated = {}
        for ticker, sentiments in ticker_sentiments.items():
            positive_scores = [s['score'] for s in sentiments if s['label'] == 'positive']
            negative_scores = [s['score'] for s in sentiments if s['label'] == 'negative']
            neutral_scores = [s['score'] for s in sentiments if s['label'] == 'neutral']

            avg_positive = np.mean(positive_scores) if positive_scores else 0
            avg_negative = np.mean(negative_scores) if negative_scores else 0
            avg_neutral = np.mean(neutral_scores) if neutral_scores else 0

            # Net sentiment: positive - negative
            net_sentiment = avg_positive - avg_negative

            aggregated[ticker] = {
                'avg_positive': avg_positive,
                'avg_negative': avg_negative,
                'avg_neutral': avg_neutral,
                'net_sentiment': net_sentiment
            }

        return pd.DataFrame.from_dict(aggregated, orient='index')

# Example usage
if __name__ == "__main__":
    # Sample news headlines (in practice, fetch from APIs like NewsAPI or Alpha Vantage)
    sample_headlines = {
        'AAPL': [
            "Apple announces record iPhone sales, stock surges!",
            "Apple faces supply chain issues amid chip shortage."
        ],
        'TSLA': [
            "Tesla beats earnings expectations, EV demand soars.",
            "Tesla recalls vehicles due to autopilot concerns."
        ],
        'GOOGL': [
            "Google AI breakthrough boosts Alphabet shares.",
            "Alphabet fined for antitrust violations."
        ]
    }

    # Initialize analyzer
    analyzer = SentimentAnalyzer()

    # Analyze sentiments
    ticker_sentiments = {}
    for ticker, headlines in sample_headlines.items():
        sentiments = analyzer.analyze_batch(headlines)
        ticker_sentiments[ticker] = sentiments

    # Aggregate
    sentiment_df = analyzer.aggregate_sentiment(ticker_sentiments)
    print("Aggregated Sentiment Scores:")
    print(sentiment_df)