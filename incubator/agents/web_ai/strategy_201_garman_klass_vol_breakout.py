"""
Strategy 201: Garman-Klass Volatility Breakout
Google Antigravity Strategy #1
Uses Garman-Klass volatility estimator (more efficient than close-close)
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class GarmanKlassVolBreakoutStrategy:
    """
    Garman-Klass volatility breakout with long/short support.
    More efficient volatility estimator using OHLC data.
    """
    
    def __init__(
        self,
        vol_period: int = 20,
        breakout_threshold: float = 2.0,
        trend_filter_period: int = 50
    ):
        self.vol_period = vol_period
        self.breakout_threshold = breakout_threshold
        self.trend_filter_period = trend_filter_period
    
    def _garman_klass_vol(self, highs: List[float], lows: List[float], 
                          opens: List[float], closes: List[float]) -> float:
        """Calculate Garman-Klass volatility estimator."""
        if len(highs) < self.vol_period:
            return 0.0
        
        log_hl = [np.log(h/l)**2 for h, l in zip(highs[-self.vol_period:], lows[-self.vol_period:])]
        log_co = [np.log(c/o)**2 for c, o in zip(closes[-self.vol_period:], opens[-self.vol_period:])]
        
        # Garman-Klass formula: 0.5*ln(H/L)^2 - (2ln2-1)*ln(C/O)^2
        var = 0.5 * np.mean(log_hl) - (2*np.log(2) - 1) * np.mean(log_co)
        return np.sqrt(max(var, 0)) * np.sqrt(365)  # Annualized
    
    def _atr(self, highs: List[float], lows: List[float], closes: List[float]) -> float:
        """Calculate Average True Range."""
        if len(closes) < 2:
            return 0
        tr_list = []
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            tr_list.append(tr)
        return np.mean(tr_list[-self.vol_period:]) if tr_list else 0
    
    def analyze(self, prices: List[float], volumes: List[float],
                highs: List[float] = None, lows: List[float] = None, 
                opens: List[float] = None) -> Signal:
        """Generate signal based on GK volatility breakout."""
        if len(prices) < self.vol_period + 10:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Use prices as fallback for OHLC
        highs = highs or prices
        lows = lows or prices
        opens = opens or prices[:-1] + [prices[-1]]
        
        # Calculate GK volatility
        gk_vol = self._garman_klass_vol(highs, lows, opens, prices)
        
        # Calculate rolling median vol for comparison
        if len(prices) >= self.vol_period * 2:
            historical_vols = []
            for i in range(self.vol_period, min(len(prices) - self.vol_period, self.vol_period * 3)):
                h_slice = highs[i-self.vol_period:i]
                l_slice = lows[i-self.vol_period:i]
                o_slice = opens[i-self.vol_period:i]
                c_slice = prices[i-self.vol_period:i]
                historical_vols.append(self._garman_klass_vol(h_slice, l_slice, o_slice, c_slice))
            median_vol = np.median(historical_vols) if historical_vols else gk_vol
        else:
            median_vol = gk_vol
        
        # Volatility breakout detection
        vol_zscore = (gk_vol - median_vol) / (median_vol + 1e-8) if median_vol > 0 else 0
        
        # Trend filter
        sma_fast = np.mean(prices[-20:])
        sma_slow = np.mean(prices[-self.trend_filter_period:])
        trend = "up" if sma_fast > sma_slow else "down"
        
        # Price momentum
        price_change = (prices[-1] - prices[-5]) / prices[-5] if len(prices) >= 5 else 0
        
        # Generate signal
        if abs(vol_zscore) > self.breakout_threshold:
            if vol_zscore > 0:  # High volatility regime
                if trend == "up" and price_change > 0:
                    return Signal("buy", min(abs(vol_zscore)/3, 0.95), {
                        "gk_vol": gk_vol,
                        "vol_zscore": vol_zscore,
                        "trend": trend,
                        "reason": "vol_breakout_long"
                    })
                elif trend == "down" and price_change < 0:
                    return Signal("sell", min(abs(vol_zscore)/3, 0.95), {
                        "gk_vol": gk_vol,
                        "vol_zscore": vol_zscore,
                        "trend": trend,
                        "reason": "vol_breakout_short"
                    })
            else:  # Low volatility - mean reversion play
                if trend == "down" and price_change > 0:
                    return Signal("buy", min(abs(vol_zscore)/2, 0.7), {
                        "gk_vol": gk_vol,
                        "vol_zscore": vol_zscore,
                        "reason": "vol_compression_long"
                    })
                elif trend == "up" and price_change < 0:
                    return Signal("sell", min(abs(vol_zscore)/2, 0.7), {
                        "gk_vol": gk_vol,
                        "vol_zscore": vol_zscore,
                        "reason": "vol_compression_short"
                    })
        
        return Signal("hold", 0.0, {"gk_vol": gk_vol, "reason": "no_breakout"})
