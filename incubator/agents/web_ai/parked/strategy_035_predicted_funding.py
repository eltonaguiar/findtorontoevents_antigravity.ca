"""
Strategy 035: Predicted Funding Strategy
Predicted funding rate front-running
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class PredictedFundingStrategy:
    """
    Trades based on predicted funding rates before they apply.
    Front-run funding payments by entering/exiting positions.
    """
    
    def __init__(
        self,
        current_threshold: float = 0.005,
        predicted_threshold: float = 0.008,
        time_to_funding_hours: float = 8
    ):
        self.current_threshold = current_threshold
        self.predicted_threshold = predicted_threshold
        self.time_to_funding = time_to_funding_hours
    
    def analyze(
        self,
        current_funding: float,
        predicted_funding: float,
        mark_price: float,
        index_price: float,
        hours_to_funding: float
    ) -> Signal:
        
        # Funding differential
        funding_diff = predicted_funding - current_funding
        funding_accel = funding_diff / (hours_to_funding + 1e-8)
        
        # Premium at mark
        premium = (mark_price - index_price) / index_price
        
        # Estimated funding based on premium
        estimated_funding = premium * 3  # Rough estimate: 8hr funding = 3x 1hr premium
        
        # Time urgency
        urgency = 1 - (hours_to_funding / 8)  # Higher as funding approaches
        
        metadata = {
            "current_funding": current_funding,
            "predicted_funding": predicted_funding,
            "funding_diff": funding_diff,
            "funding_accel": funding_accel,
            "premium": premium,
            "estimated_funding": estimated_funding,
            "urgency": urgency,
            "hours_to_funding": hours_to_funding
        }
        
        # Predicted funding much higher than current - shorts will pay more
        if predicted_funding > self.predicted_threshold and funding_diff > 0.003:
            # If we're before funding, short to collect the high funding
            if hours_to_funding > 1:
                confidence = min(0.8, 0.5 + predicted_funding * 30 + urgency * 0.2)
                return Signal("sell", confidence, {**metadata, "reason": "High predicted funding - short to collect"})
        
        # Predicted funding much lower (negative) - longs will pay more
        if predicted_funding < -self.predicted_threshold and funding_diff < -0.003:
            if hours_to_funding > 1:
                confidence = min(0.8, 0.5 + abs(predicted_funding) * 30 + urgency * 0.2)
                return Signal("buy", confidence, {**metadata, "reason": "Very negative predicted funding - long to collect"})
        
        # Funding flipping from positive to negative
        if current_funding > 0 and predicted_funding < -0.002:
            confidence = min(0.75, 0.55 + urgency * 0.2)
            return Signal("buy", confidence, {**metadata, "reason": "Funding flipping negative"})
        
        # Funding flipping from negative to positive
        if current_funding < 0 and predicted_funding > 0.002:
            confidence = min(0.75, 0.55 + urgency * 0.2)
            return Signal("sell", confidence, {**metadata, "reason": "Funding flipping positive"})
        
        # Avoid funding payment
        if hours_to_funding < 0.5 and abs(predicted_funding) > 0.01:
            if predicted_funding > 0:
                return Signal("sell", 0.6, {**metadata, "reason": "Close long before funding"})
            else:
                return Signal("buy", 0.6, {**metadata, "reason": "Close short before funding"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    # Current funding low, predicted very high
    current_funding = 0.001
    predicted_funding = 0.015
    mark_price = 40200
    index_price = 40000
    hours_to_funding = 4
    
    strategy = PredictedFundingStrategy()
    signal = strategy.analyze(current_funding, predicted_funding, 
                               mark_price, index_price, hours_to_funding)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
