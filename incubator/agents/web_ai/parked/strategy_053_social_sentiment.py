"""
Strategy 053: Social Sentiment NLP
Social media sentiment strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class SocialSentimentStrategy:
    """
    Analyzes social media sentiment for contrarian signals.
    Extreme sentiment often marks turning points.
    """
    
    def __init__(
        self,
        extreme_positive: float = 0.8,
        extreme_negative: float = 0.2,
        sentiment_ma_period: int = 7,
        volume_threshold: float = 1000
    ):
        self.extreme_pos = extreme_positive
        self.extreme_neg = extreme_negative
        self.ma_period = sentiment_ma_period
        self.volume_threshold = volume_threshold
    
    def analyze(
        self,
        sentiment_scores: List[float],  # 0-1 scale
        mention_volumes: List[float],
        prices: List[float]
    ) -> Signal:
        if len(sentiment_scores) < self.ma_period:
            return Signal("hold", 0.0, {"error": "Insufficient sentiment data"})
        
        current_sentiment = sentiment_scores[-1]
        sentiment_ma = np.mean(sentiment_scores[-self.ma_period:])
        
        # Sentiment trend
        sentiment_change = current_sentiment - sentiment_scores[-self.ma_period]
        
        # Volume of mentions
        current_mentions = mention_volumes[-1]
        mention_ma = np.mean(mention_volumes[-self.ma_period:])
        mention_surge = current_mentions / mention_ma if mention_ma > 0 else 1
        
        # Price trend
        price_change = (prices[-1] - prices[-5]) / prices[-5] if len(prices) >= 5 else 0
        
        # Sentiment-price divergence
        divergence = sentiment_change - price_change
        
        metadata = {
            "current_sentiment": current_sentiment,
            "sentiment_ma": sentiment_ma,
            "sentiment_change": sentiment_change,
            "mention_surge": mention_surge,
            "price_change": price_change,
            "divergence": divergence
        }
        
        # Extreme positive sentiment - contrarian sell
        if current_sentiment > self.extreme_pos and mention_surge > 1.5:
            if sentiment_change > 0.1:
                confidence = min(0.8, 0.5 + (current_sentiment - self.extreme_pos) * 0.5)
                return Signal("sell", confidence, {**metadata, "reason": "Extreme positive sentiment"})
        
        # Extreme negative sentiment - contrarian buy
        if current_sentiment < self.extreme_neg and mention_surge > 1.5:
            if sentiment_change < -0.1:
                confidence = min(0.8, 0.5 + (self.extreme_neg - current_sentiment) * 0.5)
                return Signal("buy", confidence, {**metadata, "reason": "Extreme negative sentiment"})
        
        # Sentiment improving from extreme
        if sentiment_ma < self.extreme_neg and current_sentiment > sentiment_ma + 0.05:
            return Signal("buy", 0.65, {**metadata, "reason": "Sentiment recovering from fear"})
        
        # Sentiment declining from extreme
        if sentiment_ma > self.extreme_pos and current_sentiment < sentiment_ma - 0.05:
            return Signal("sell", 0.65, {**metadata, "reason": "Sentiment declining from greed"})
        
        # High volume with neutral sentiment = accumulation
        if mention_surge > 2 and 0.4 < current_sentiment < 0.6:
            if price_change > 0:
                return Signal("buy", 0.6, {**metadata, "reason": "High activity, neutral sentiment"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 20
    # Sentiment going to extreme positive
    sentiment = [0.5 + i * 0.02 + np.random.randn() * 0.05 for i in range(n)]
    sentiment[-1] = 0.9  # Extreme
    
    mentions = [1000 + np.random.randn() * 100 for _ in range(n-1)]
    mentions.append(3000)  # Volume surge
    
    prices = [40000 + i * 100 for i in range(n)]
    
    strategy = SocialSentimentStrategy()
    signal = strategy.analyze(sentiment, mentions, prices)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
