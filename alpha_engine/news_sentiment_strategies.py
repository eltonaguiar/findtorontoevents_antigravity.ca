# News Sentiment & Regulatory Event Strategy
# Uses sentiment scores to bias long/short positions.
# Auto-fetches data using the unified data provider.

import logging
from data_providers.crypto_data import build_context

logger = logging.getLogger(__name__)


class NewsSentimentStrategy:
    """Generate signals based on news sentiment for each crypto symbol.

    Automatically builds its own context from the data provider.
    External context values can override defaults.
    """
    def __init__(self, context=None):
        try:
            generated = build_context()
        except Exception as e:
            logger.warning("Failed to build context: %s", e)
            generated = {}
        self.context = generated
        if context:
            self.context.update(context)

    def generate_signals(self):
        signals = []
        scores = self.context.get('sentiment_scores', {})
        spot_prices = self.context.get('spot_price', {})
        for symbol, score in scores.items():
            if abs(score) < 0.2:
                continue
            price = spot_prices.get(symbol)
            if price is None:
                continue
            direction = "LONG" if score > 0 else "SHORT"
            tp = price * (1.05 if direction == "LONG" else 0.95)
            sl = price * (0.95 if direction == "LONG" else 1.05)
            signals.append({
                "symbol": symbol,
                "direction": direction,
                "entry": price,
                "tp": tp,
                "sl": sl,
                "size": 0.01,
                "confidence": min(0.50 + abs(score), 0.80),
                "strategy": "news_sentiment",
                "reason": f"News sentiment {score:.2f} for {symbol}"
            })
        return signals
