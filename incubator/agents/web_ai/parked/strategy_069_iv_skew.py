"""
Strategy 069: IV Skew Trading
Implied volatility skew strategy
"""
from dataclasses import dataclass
from typing import List, Dict
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class IVSkewStrategy:
    """
    Trades implied volatility skew.
    High put skew = fear (potential buy)
    High call skew = greed (potential sell)
    """
    
    def __init__(
        self,
        skew_threshold: float = 0.1,
        lookback: int = 20
    ):
        self.skew_threshold = skew_threshold
        self.lookback = lookback
    
    def analyze(
        self,
        iv_by_strike: Dict[float, float],
        atm_iv: float,
        prices: List[float]
    ) -> Signal:
        if not iv_by_strike or atm_iv == 0:
            return Signal("hold", 0.0, {"error": "No IV data"})
        
        current_price = prices[-1]
        
        # Calculate skew
        puts = {k: v for k, v in iv_by_strike.items() if k < current_price}
        calls = {k: v for k, v in iv_by_strike.items() if k > current_price}
        
        avg_put_iv = np.mean(list(puts.values())) if puts else atm_iv
        avg_call_iv = np.mean(list(calls.values())) if calls else atm_iv
        
        # Put skew (25 delta put - ATM)
        put_skew = (avg_put_iv - atm_iv) / atm_iv if atm_iv > 0 else 0
        
        # Call skew (25 delta call - ATM)
        call_skew = (avg_call_iv - atm_iv) / atm_iv if atm_iv > 0 else 0
        
        # Overall skew
        skew_ratio = put_skew / (call_skew + 1e-8)
        
        metadata = {
            "atm_iv": atm_iv,
            "put_skew": put_skew,
            "call_skew": call_skew,
            "skew_ratio": skew_ratio
        }
        
        # Extreme put skew - fear, potential buy
        if put_skew > self.skew_threshold and skew_ratio > 2:
            confidence = min(0.8, 0.5 + put_skew)
            return Signal("buy", confidence, {**metadata, "reason": "High put skew - fear"})
        
        # Extreme call skew - greed, potential sell
        if call_skew > self.skew_threshold and skew_ratio < 0.5:
            confidence = min(0.8, 0.5 + call_skew)
            return Signal("sell", confidence, {**metadata, "reason": "High call skew - greed"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    current_price = 40000
    atm_iv = 0.6
    
    iv_by_strike = {
        35000: 0.75,  # High put IV
        36000: 0.70,
        38000: 0.65,
        40000: 0.60,  # ATM
        42000: 0.55,
        44000: 0.52,
        45000: 0.50
    }
    
    prices = [40000 + np.random.randn() * 100 for _ in range(20)]
    
    strategy = IVSkewStrategy()
    signal = strategy.analyze(iv_by_strike, atm_iv, prices)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
