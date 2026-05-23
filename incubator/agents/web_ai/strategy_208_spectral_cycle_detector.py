"""
Strategy 208: Spectral Cycle Detector
Google Antigravity Strategy #8
Uses FFT cycle detection to trade at cycle trough/peak
"""
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class SpectralCycleDetectorStrategy:
    """
    Uses Fast Fourier Transform to detect dominant cycles in price.
    Trade at expected cycle troughs (long) and peaks (short).
    """
    
    def __init__(
        self,
        fft_window: int = 64,
        min_cycle_period: int = 5,
        max_cycle_period: int = 50,
        phase_threshold: float = 0.3
    ):
        self.fft_window = fft_window
        self.min_period = min_cycle_period
        self.max_period = max_cycle_period
        self.phase_thresh = phase_threshold
    
    def _detrend(self, prices: List[float]) -> List[float]:
        """Remove linear trend."""
        x = np.arange(len(prices))
        slope, intercept = np.polyfit(x, prices, 1)
        trend = [slope * i + intercept for i in x]
        return [p - t for p, t in zip(prices, trend)]
    
    def _fft_analysis(self, prices: List[float]) -> Tuple[int, float, float]:
        """
        Perform FFT analysis to find dominant cycle.
        Returns: (period, amplitude, phase)
        """
        if len(prices) < self.fft_window:
            return 20, 0, 0  # Default
        
        # Use detrended prices
        detrended = self._detrend(prices[-self.fft_window:])
        
        # Apply Hanning window
        window = np.hanning(len(detrended))
        windowed = [d * w for d, w in zip(detrended, window)]
        
        # FFT
        fft_result = np.fft.fft(windowed)
        freqs = np.fft.fftfreq(len(windowed))
        
        # Find dominant frequency (excluding DC component)
        magnitudes = np.abs(fft_result)
        positive_freqs = freqs[:len(freqs)//2]
        positive_mags = magnitudes[:len(magnitudes)//2]
        
        # Filter by period range
        valid_idx = []
        for i, f in enumerate(positive_freqs):
            if f > 0:
                period = 1/f
                if self.min_period <= period <= self.max_period:
                    valid_idx.append(i)
        
        if not valid_idx:
            return 20, 0, 0
        
        # Find peak
        peak_idx = valid_idx[np.argmax([positive_mags[i] for i in valid_idx])]
        dominant_freq = positive_freqs[peak_idx]
        dominant_period = 1 / dominant_freq
        amplitude = positive_mags[peak_idx]
        
        # Phase at end of window
        phase = np.angle(fft_result[peak_idx])
        
        return dominant_period, amplitude, phase
    
    def _predict_cycle_position(self, period: float, phase: float) -> float:
        """
        Predict position in cycle (0 = trough, pi = peak).
        Returns normalized position in [0, 1].
        """
        # Phase tells us where we are in the cycle
        # Normalize to [0, 2*pi]
        normalized_phase = (phase + 2 * np.pi) % (2 * np.pi)
        
        # Position: 0 = start (trough for sine), 0.5 = peak
        position = normalized_phase / (2 * np.pi)
        
        return position
    
    def analyze(self, prices: List[float], volumes: List[float]) -> Signal:
        """Generate signal based on cycle position."""
        if len(prices) < self.fft_window + 10:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # FFT analysis
        period, amplitude, phase = self._fft_analysis(prices)
        
        # Cycle position
        cycle_pos = self._predict_cycle_position(period, phase)
        
        # Calculate current momentum
        returns = np.diff(prices) / prices[:-1]
        mom = np.mean(returns[-5:]) if len(returns) >= 5 else 0
        
        # Volume trend
        vol_ma = np.mean(volumes[-10:]) if len(volumes) >= 10 else 0
        vol_prev = np.mean(volumes[-20:-10]) if len(volumes) >= 20 else 1
        vol_confirm = vol_ma > vol_prev * 0.9
        
        # Signal generation based on cycle position
        # 0.0-0.25: Trough region (buy)
        # 0.75-1.0: Peak region (sell)
        
        if 0.0 <= cycle_pos <= 0.25 and mom > -0.05 and vol_confirm:
            # Near cycle trough - expect bounce
            confidence = min((0.25 - cycle_pos) * 4 + amplitude * 0.01, 0.9)
            return Signal("buy", confidence, {
                "period": period,
                "amplitude": amplitude,
                "cycle_pos": cycle_pos,
                "reason": "cycle_trough_long"
            })
        
        elif 0.75 <= cycle_pos <= 1.0 and mom < 0.05 and vol_confirm:
            # Near cycle peak - expect pullback
            confidence = min((cycle_pos - 0.75) * 4 + amplitude * 0.01, 0.9)
            return Signal("sell", confidence, {
                "period": period,
                "amplitude": amplitude,
                "cycle_pos": cycle_pos,
                "reason": "cycle_peak_short"
            })
        
        return Signal("hold", 0.0, {
            "period": period,
            "amplitude": amplitude,
            "cycle_pos": cycle_pos
        })
