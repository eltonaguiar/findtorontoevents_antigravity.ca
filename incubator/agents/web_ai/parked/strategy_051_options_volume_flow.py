"""
Strategy 051: Options Volume Flow
Options market flow analysis
"""
from dataclasses import dataclass
from typing import List, Dict
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class OptionsVolumeFlowStrategy:
    """
    Analyzes options volume for directional signals.
    Unusual call volume = bullish sentiment
    Unusual put volume = bearish sentiment
    """
    
    def __init__(
        self,
        volume_threshold: float = 1.5,
        lookback: int = 20,
        oi_change_threshold: float = 0.1
    ):
        self.volume_threshold = volume_threshold
        self.lookback = lookback
        self.oi_threshold = oi_change_threshold
    
    def analyze(
        self,
        call_volume: List[float],
        put_volume: List[float],
        call_oi: List[float],
        put_oi: List[float],
        prices: List[float]
    ) -> Signal:
        if len(call_volume) < self.lookback:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Volume metrics
        total_volume = call_volume[-1] + put_volume[-1]
        if total_volume == 0:
            return Signal("hold", 0.0, {"error": "Zero volume"})
        
        call_ratio = call_volume[-1] / total_volume
        put_ratio = put_volume[-1] / total_volume
        
        # Historical averages
        avg_call_vol = np.mean(call_volume[-self.lookback:])
        avg_put_vol = np.mean(put_volume[-self.lookback:])
        
        # Volume surges
        call_surge = call_volume[-1] / avg_call_vol if avg_call_vol > 0 else 1
        put_surge = put_volume[-1] / avg_put_vol if avg_put_vol > 0 else 1
        
        # Put/Call ratio
        pc_ratio = put_volume[-1] / (call_volume[-1] + 1e-8)
        pc_ratio_ma = np.mean([put_volume[i] / (call_volume[i] + 1e-8) 
                               for i in range(-self.lookback, 0)])
        
        # OI changes
        call_oi_change = (call_oi[-1] - call_oi[-2]) / call_oi[-2] if len(call_oi) > 1 and call_oi[-2] > 0 else 0
        put_oi_change = (put_oi[-1] - put_oi[-2]) / put_oi[-2] if len(put_oi) > 1 and put_oi[-2] > 0 else 0
        
        metadata = {
            "call_ratio": call_ratio,
            "put_ratio": put_ratio,
            "pc_ratio": pc_ratio,
            "pc_ratio_ma": pc_ratio_ma,
            "call_surge": call_surge,
            "put_surge": put_surge,
            "call_oi_change": call_oi_change,
            "put_oi_change": put_oi_change
        }
        
        # Extreme call buying
        if call_surge > self.volume_threshold and call_oi_change > self.oi_threshold:
            if pc_ratio < 0.7:
                confidence = min(0.8, 0.5 + (call_surge - 1) * 0.3)
                return Signal("buy", confidence, {**metadata, "reason": "Unusual call volume"})
        
        # Extreme put buying
        if put_surge > self.volume_threshold and put_oi_change > self.oi_threshold:
            if pc_ratio > 1.3:
                confidence = min(0.8, 0.5 + (put_surge - 1) * 0.3)
                return Signal("sell", confidence, {**metadata, "reason": "Unusual put volume"})
        
        # P/C ratio extreme
        if pc_ratio < 0.5 and pc_ratio < pc_ratio_ma * 0.7:
            return Signal("buy", 0.65, {**metadata, "reason": "P/C ratio extremely low"})
        
        if pc_ratio > 1.5 and pc_ratio > pc_ratio_ma * 1.3:
            return Signal("sell", 0.65, {**metadata, "reason": "P/C ratio extremely high"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 25
    call_vol = [1000 + np.random.randn() * 100 for _ in range(n-1)]
    call_vol.append(2500)  # Surge
    
    put_vol = [800 + np.random.randn() * 80 for _ in range(n)]
    
    call_oi = [50000 + i * 1000 for i in range(n)]
    put_oi = [40000 + i * 500 for i in range(n)]
    
    prices = [40000 + i * 50 for i in range(n)]
    
    strategy = OptionsVolumeFlowStrategy()
    signal = strategy.analyze(call_vol, put_vol, call_oi, put_oi, prices)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
