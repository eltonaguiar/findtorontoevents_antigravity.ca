"""
Strategy 049: Kalman Filter Pairs
Kalman filter-based pairs trading
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class KalmanPairsStrategy:
    """
    Uses Kalman filter to dynamically estimate hedge ratio.
    Adapts to changing market conditions.
    """
    
    def __init__(
        self,
        delta: float = 0.0001,
        entry_threshold: float = 1.5,
        exit_threshold: float = 0.3
    ):
        self.delta = delta
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold
        self.wt = 1.0  # Initial hedge ratio
        self.vt = 0.0  # Initial intercept
        self.cov = np.zeros((2, 2))
        self.cov[0, 0] = 1.0
        self.cov[1, 1] = 1.0
    
    def _update_kalman(self, x: float, y: float):
        """Update Kalman filter with new observation"""
        # Prediction
        F = np.array([[1, 0], [0, 1]])
        Q = self.delta / (1 - self.delta) * np.eye(2)
        
        # Observation matrix
        H = np.array([x, 1])
        
        # Prediction error
        y_pred = self.wt * x + self.vt
        e = y - y_pred
        
        # Kalman gain
        R = 1.0
        S = H @ self.cov @ H.T + R
        K = self.cov @ H.T / S
        
        # Update state
        state = np.array([self.wt, self.vt])
        state = state + K * e
        self.wt, self.vt = state[0], state[1]
        
        # Update covariance
        self.cov = (np.eye(2) - np.outer(K, H)) @ self.cov + Q
        
        return e
    
    def analyze(
        self,
        asset1_prices: List[float],
        asset2_prices: List[float]
    ) -> Signal:
        if len(asset1_prices) < 20:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Run Kalman filter
        errors = []
        for i in range(len(asset1_prices)):
            e = self._update_kalman(asset2_prices[i], asset1_prices[i])
            errors.append(e)
        
        # Current spread (error)
        current_error = errors[-1]
        
        # Z-score of errors
        error_mean = np.mean(errors[-20:])
        error_std = np.std(errors[-20:])
        zscore = (current_error - error_mean) / (error_std + 1e-8)
        
        metadata = {
            "hedge_ratio": self.wt,
            "intercept": self.vt,
            "current_error": current_error,
            "zscore": zscore,
            "error_std": error_std
        }
        
        # Entry signals
        if zscore > self.entry_threshold:
            confidence = min(0.8, 0.5 + (zscore - self.entry_threshold) * 0.2)
            return Signal("sell", confidence, {**metadata, "reason": "Kalman spread high"})
        
        if zscore < -self.entry_threshold:
            confidence = min(0.8, 0.5 + (abs(zscore) - self.entry_threshold) * 0.2)
            return Signal("buy", confidence, {**metadata, "reason": "Kalman spread low"})
        
        # Exit signal
        if abs(zscore) < self.exit_threshold:
            return Signal("hold", 0.3, {**metadata, "reason": "Kalman spread normalized"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 50
    asset2 = [2000 + i * 10 + np.random.randn() * 30 for i in range(n)]
    asset1 = [4000 + i * 20 + 2 * (a - 2000) + np.random.randn() * 50 for a in asset2]
    
    # Divergence
    asset1[-10:] = [a + 400 for a in asset1[-10:]]
    
    strategy = KalmanPairsStrategy()
    signal = strategy.analyze(asset1, asset2)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
