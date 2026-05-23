"""
Strategy 031: Funding Rate Arbitrage
Perpetual funding rate strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class FundingArbitrageStrategy:
    """
    Exploits funding rate differentials between exchanges.
    Also trades extreme funding rates as contrarian signals.
    """
    
    def __init__(
        self,
        extreme_positive: float = 0.01,
        extreme_negative: float = -0.01,
        arb_threshold: float = 0.005,
        lookback: int = 30
    ):
        self.extreme_pos = extreme_positive
        self.extreme_neg = extreme_negative
        self.arb_threshold = arb_threshold
        self.lookback = lookback
    
    def analyze(
        self,
        funding_rates: dict,  # {exchange: [rates], ...}
        prices: List[float],
        predicted_funding: float = None
    ) -> Signal:
        if not funding_rates:
            return Signal("hold", 0.0, {"error": "No funding data"})
        
        # Get latest funding rates
        latest_rates = {}
        for exchange, rates in funding_rates.items():
            if rates:
                latest_rates[exchange] = rates[-1]
        
        if not latest_rates:
            return Signal("hold", 0.0, {"error": "No latest funding rates"})
        
        # Average funding rate
        avg_funding = np.mean(list(latest_rates.values()))
        
        # Funding rate spread (arb opportunity)
        max_rate = max(latest_rates.values())
        min_rate = min(latest_rates.values())
        funding_spread = max_rate - min_rate
        
        # Historical context
        all_rates = []
        for rates in funding_rates.values():
            all_rates.extend(rates[-self.lookback:])
        
        funding_std = np.std(all_rates) if all_rates else 0.001
        funding_zscore = (avg_funding - np.mean(all_rates)) / (funding_std + 1e-8) if all_rates else 0
        
        metadata = {
            "avg_funding": avg_funding,
            "funding_spread": funding_spread,
            "max_rate": max_rate,
            "min_rate": min_rate,
            "funding_zscore": funding_zscore,
            "extreme_positive": avg_funding > self.extreme_pos,
            "extreme_negative": avg_funding < self.extreme_neg
        }
        
        # Extreme positive funding - shorts getting paid heavily, potential top
        if avg_funding > self.extreme_pos and funding_zscore > 2:
            confidence = min(0.8, 0.5 + (avg_funding - self.extreme_pos) * 20)
            return Signal("sell", confidence, {**metadata, "reason": "Extreme positive funding"})
        
        # Extreme negative funding - longs getting paid heavily, potential bottom
        if avg_funding < self.extreme_neg and funding_zscore < -2:
            confidence = min(0.8, 0.5 + abs(avg_funding - self.extreme_neg) * 20)
            return Signal("buy", confidence, {**metadata, "reason": "Extreme negative funding"})
        
        # Funding arbitrage opportunity
        if funding_spread > self.arb_threshold:
            return Signal("hold", 0.4, {**metadata, "reason": "Funding arb opportunity", "arb_exchanges": (min_rate, max_rate)})
        
        # Predicted funding divergence
        if predicted_funding is not None:
            prediction_diff = predicted_funding - avg_funding
            if abs(prediction_diff) > 0.002:
                if prediction_diff > 0:
                    return Signal("sell", 0.55, {**metadata, "reason": "Funding predicted to increase"})
                else:
                    return Signal("buy", 0.55, {**metadata, "reason": "Funding predicted to decrease"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    # Funding rates across exchanges
    funding_rates = {
        "binance": [0.008, 0.009, 0.012, 0.015],
        "bybit": [0.007, 0.010, 0.013, 0.016],
        "okx": [0.009, 0.008, 0.011, 0.014]
    }
    
    prices = [40000 + i * 100 for i in range(10)]
    
    strategy = FundingArbitrageStrategy()
    signal = strategy.analyze(funding_rates, prices)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
