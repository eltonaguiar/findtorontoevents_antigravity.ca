"""
VolumeProfileDeviationStrategy - Baby Strat
===========================================

Created by: AI Assistant
Date: 2026-02-27

Strategy Logic:
- Entry when: Price deviates from Volume Weighted Distribution level
- Exit when: Returns to VWAP/POC or SL hit
- Risk management: VAH/VAL as dynamic levels

Unique Value Proposition:
Uses volume profile statistics (POC, VAH, VAL) instead of just VWAP.
Trades deviations from value areas with mean reversion.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass


SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "DOTUSDT",
    "LINKUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "SUIUSDT",
    "INJUSDT", "NEARUSDT", "HBARUSDT", "ARBUSDT", "OPUSDT",
    "FETUSDT", "TIAUSDT", "SEIUSDT", "AAVEUSDT", "ETCUSDT",
]

@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class VolumeProfileDeviationStrategy:
    """
    Volume Profile Deviation Strategy
    
    Calculates Volume Profile metrics:
    - POC (Point of Control): Price level with highest volume
    - VAH (Value Area High): Upper bound of 70% volume
    - VAL (Value Area Low): Lower bound of 70% volume
    
    Trades deviations outside value area with mean reversion.
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.profile_lookback = self.params.get('profile_lookback', 50)
        self.value_area_pct = self.params.get('value_area_pct', 0.70)
        self.num_bins = self.params.get('num_bins', 20)
        self.deviation_threshold = self.params.get('deviation_threshold', 1.5)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_ratio = self.params.get('tp_ratio', 1.5)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < max(self.profile_lookback, self.atr_period) + 10:
            return []

        # Calculate volume profile metrics
        profile_data = data.iloc[-self.profile_lookback:]
        poc, vah, val = self._calculate_volume_profile(profile_data)
        
        # Calculate ATR
        atr = self._calculate_atr(data, self.atr_period)
        
        current_price = data['close'].iloc[-1]
        current_atr = atr.iloc[-1]
        
        # Calculate deviation from value area
        value_area_mid = (vah + val) / 2
        
        signals = []
        
        # Long signal: Price below VAL (undervalued)
        if current_price < val:
            deviation = (val - current_price) / current_atr
            
            if deviation > self.deviation_threshold * 0.5:
                confidence = min(deviation / (self.deviation_threshold * 2), 0.95)
                
                tp = val  # Target: return to value area
                sl = current_price - (current_atr * self.tp_ratio * 0.5)
                
                signals.append(Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2),
                    stop_loss=round(sl, 2),
                    reason=f"Below VAL ({val:.2f}), deviation: {deviation:.2f}ATR"
                ))
        
        # Short signal: Price above VAH (overvalued)
        elif current_price > vah:
            deviation = (current_price - vah) / current_atr
            
            if deviation > self.deviation_threshold * 0.5:
                confidence = min(deviation / (self.deviation_threshold * 2), 0.95)
                
                tp = vah  # Target: return to value area
                sl = current_price + (current_atr * self.tp_ratio * 0.5)
                
                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2),
                    stop_loss=round(sl, 2),
                    reason=f"Above VAH ({vah:.2f}), deviation: {deviation:.2f}ATR"
                ))
        
        return signals

    def _calculate_volume_profile(self, data: pd.DataFrame) -> tuple:
        """
        Calculate Volume Profile: POC, VAH, VAL
        
        Returns:
            (poc_price, vah_price, val_price)
        """
        prices = data['close'].values
        volumes = data['volume'].values
        
        # Create price bins
        price_min = data['low'].min()
        price_max = data['high'].max()
        bins = np.linspace(price_min, price_max, self.num_bins)
        
        # Calculate volume for each bin
        volume_profile = np.zeros(len(bins) - 1)
        for i in range(len(bins) - 1):
            mask = (prices >= bins[i]) & (prices < bins[i+1])
            volume_profile[i] = volumes[mask].sum()
        
        # Find POC (price level with highest volume)
        poc_idx = np.argmax(volume_profile)
        poc = (bins[poc_idx] + bins[poc_idx + 1]) / 2
        
        # Calculate Value Area (70% of volume centered on POC)
        total_volume = volume_profile.sum()
        target_volume = total_volume * self.value_area_pct
        
        # Start at POC and expand until we capture target volume
        current_volume = volume_profile[poc_idx]
        lower_idx = poc_idx
        upper_idx = poc_idx
        
        while current_volume < target_volume and (lower_idx > 0 or upper_idx < len(volume_profile) - 1):
            # Add the larger adjacent bin
            lower_vol = volume_profile[lower_idx - 1] if lower_idx > 0 else 0
            upper_vol = volume_profile[upper_idx + 1] if upper_idx < len(volume_profile) - 1 else 0
            
            if lower_vol >= upper_vol and lower_idx > 0:
                lower_idx -= 1
                current_volume += lower_vol
            elif upper_idx < len(volume_profile) - 1:
                upper_idx += 1
                current_volume += upper_vol
            else:
                break
        
        val = bins[lower_idx]
        vah = bins[upper_idx + 1]
        
        return poc, vah, val

    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        high = data['high']
        low = data['low']
        close = data['close']
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period, min_periods=1).mean()
        return atr


# ==============================================================================
# TESTING
# ==============================================================================

if __name__ == "__main__":
    """Quick test with synthetic data."""
    
    np.random.seed(42)
    n = 200
    returns = np.random.normal(0.0001, 0.02, n)
    prices = 50000 * np.exp(np.cumsum(returns))
    
    test_data = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.001, n)),
        'high': prices * (1 + abs(np.random.normal(0, 0.01, n))),
        'low': prices * (1 - abs(np.random.normal(0, 0.01, n))),
        'close': prices,
        'volume': np.random.uniform(100, 1000, n)
    })
    
    strategy = VolumeProfileDeviationStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")
    
    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
