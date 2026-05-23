"""
Strategy 219: Entropy-Weighted Momentum
Google Antigravity Strategy #19
Shannon entropy weighting - low entropy = high conviction
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class EntropyWeightedMomentumStrategy:
    """
    Uses Shannon entropy of price distribution to weight momentum signals.
    Low entropy = more predictable/structured = higher conviction.
    """
    
    def __init__(
        self,
        lookback: int = 30,
        bins: int = 10,
        entropy_threshold_low: float = 2.0,
        entropy_threshold_high: float = 3.0
    ):
        self.lookback = lookback
        self.bins = bins
        self.entropy_low = entropy_threshold_low
        self.entropy_high = entropy_threshold_high
    
    def _calculate_entropy(self, prices: List[float]) -> float:
        """
        Calculate Shannon entropy of price distribution.
        Lower entropy = more predictable structure.
        """
        if len(prices) < self.bins:
            return 3.0  # Default (high entropy/uncertainty)
        
        # Create price bins
        min_p, max_p = min(prices), max(prices)
        if min_p == max_p:
            return 0  # All same price = zero entropy
        
        bin_edges = np.linspace(min_p, max_p, self.bins + 1)
        
        # Count observations in each bin
        hist = [0] * self.bins
        for p in prices:
            for i in range(self.bins):
                if bin_edges[i] <= p <= bin_edges[i + 1]:
                    hist[i] += 1
                    break
        
        # Calculate probabilities
        total = sum(hist)
        probs = [h / total for h in hist if h > 0]
        
        # Shannon entropy: -sum(p * log(p))
        entropy = -sum(p * np.log(p) for p in probs)
        
        return entropy
    
    def _normalize_entropy(self, entropy: float, max_entropy: float = None) -> float:
        """Normalize entropy to [0, 1] where 0 = predictable, 1 = random."""
        if max_entropy is None:
            max_entropy = np.log(self.bins)  # Max entropy for uniform distribution
        
        return min(entropy / max_entropy, 1.0) if max_entropy > 0 else 0.5
    
    def _calculate_momentum(self, prices: List[float]) -> float:
        """Calculate multi-timeframe momentum."""
        if len(prices) < 10:
            return 0
        
        mom_short = (prices[-1] - prices[-5]) / prices[-5] if len(prices) >= 5 else 0
        mom_medium = (prices[-1] - prices[-10]) / prices[-10] if len(prices) >= 10 else 0
        
        # Weighted combination
        return 0.6 * mom_short + 0.4 * mom_medium
    
    def analyze(self, prices: List[float], volumes: List[float]) -> Signal:
        """Generate entropy-weighted momentum signal."""
        if len(prices) < self.lookback + 5:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate entropy
        entropy = self._calculate_entropy(prices[-self.lookback:])
        norm_entropy = self._normalize_entropy(entropy)
        
        # Predictability score (inverse of normalized entropy)
        predictability = 1 - norm_entropy
        
        # Calculate momentum
        momentum = self._calculate_momentum(prices)
        
        # Volume confirmation
        vol_ma = np.mean(volumes[-10:]) if len(volumes) >= 10 else 1
        vol_recent = np.mean(volumes[-3:]) if len(volumes) >= 3 else 0
        vol_confirm = vol_recent > vol_ma * 0.9
        
        # Entropy-weighted confidence
        if entropy < self.entropy_low:
            # Low entropy = structured/predictable = high conviction
            if abs(momentum) > 0.015 and vol_confirm:
                base_confidence = predictability
                if momentum > 0:
                    return Signal("buy", min(base_confidence * 1.2 + abs(momentum) * 5, 0.95), {
                        "entropy": entropy,
                        "predictability": predictability,
                        "momentum": momentum,
                        "regime": "low_entropy",
                        "reason": "high_conviction_long"
                    })
                else:
                    return Signal("sell", min(base_confidence * 1.2 + abs(momentum) * 5, 0.95), {
                        "entropy": entropy,
                        "predictability": predictability,
                        "momentum": momentum,
                        "regime": "low_entropy",
                        "reason": "high_conviction_short"
                    })
        
        elif entropy > self.entropy_high:
            # High entropy = noisy/random = low conviction, fade extreme moves
            if abs(momentum) > 0.04:  # Only fade extreme moves in high entropy
                fade_confidence = norm_entropy * 0.3  # Low confidence fade
                if momentum > 0:
                    return Signal("sell", fade_confidence, {
                        "entropy": entropy,
                        "predictability": predictability,
                        "momentum": momentum,
                        "regime": "high_entropy",
                        "reason": "high_entropy_fade_short"
                    })
                else:
                    return Signal("buy", fade_confidence, {
                        "entropy": entropy,
                        "predictability": predictability,
                        "momentum": momentum,
                        "regime": "high_entropy",
                        "reason": "high_entropy_fade_long"
                    })
        
        else:
            # Medium entropy = normal conditions
            if abs(momentum) > 0.02 and vol_confirm:
                medium_confidence = predictability * 0.7 + abs(momentum) * 10
                if momentum > 0:
                    return Signal("buy", min(medium_confidence, 0.75), {
                        "entropy": entropy,
                        "predictability": predictability,
                        "momentum": momentum,
                        "regime": "medium_entropy",
                        "reason": "medium_conviction_long"
                    })
                else:
                    return Signal("sell", min(medium_confidence, 0.75), {
                        "entropy": entropy,
                        "predictability": predictability,
                        "momentum": momentum,
                        "regime": "medium_entropy",
                        "reason": "medium_conviction_short"
                    })
        
        return Signal("hold", 0.0, {
            "entropy": entropy,
            "predictability": predictability,
            "momentum": momentum
        })
