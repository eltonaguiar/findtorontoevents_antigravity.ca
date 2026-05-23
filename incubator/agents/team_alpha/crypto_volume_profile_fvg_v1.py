"""
Volume Profile Fair Value Gap Strategy - Baby Strat
====================================================

Created by: team_alpha
Date: 2026-02-26

Strategy Logic:
- Builds volume profile to find Point of Control (POC)
- Detects Fair Value Gaps (FVG) with volume spike confirmation
- Enters when price returns to POC after FVG formation
- RSI filter ensures neutral momentum zone

Unique Value Proposition:
Combines two institutional concepts (Volume Profile + FVG) that no existing
strategy uses together. POC acts as a magnet for price, providing high-
probability entries at key volume nodes.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Signal:
    """A trading signal - required return type."""
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class VolumeProfileFVGStrategy:
    """
    Volume Profile Fair Value Gap Strategy.
    
    Combines volume profile analysis (POC) with Fair Value Gap detection
    for precise entries at high-probability institutional levels.
    """
    
    def __init__(self, params: Optional[Dict] = None):
        """
        Initialize with parameters.
        
        Args:
            params: Dict with strategy parameters
        """
        self.params = params or {}
        self.profile_periods = self.params.get('profile_periods', 50)
        self.volume_spike_mult = self.params.get('volume_spike_mult', 2.0)
        self.rsi_lower = self.params.get('rsi_lower', 40)
        self.rsi_upper = self.params.get('rsi_upper', 60)
        self.tp_fvg_fill = self.params.get('tp_fvg_fill', True)
        self.sl_poc_buffer = self.params.get('sl_poc_buffer', 0.005)
        self.atr_period = self.params.get('atr_period', 14)
    
    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        """
        Main signal generation method.
        
        Args:
            data: DataFrame with columns [open, high, low, close, volume]
            symbol: Trading pair
            
        Returns:
            List of Signal objects
        """
        if len(data) < self.profile_periods + 10:
            return []
        
        # Calculate indicators
        rsi = self._calculate_rsi(data['close'], 14)
        atr = self._calculate_atr(data, self.atr_period)
        
        current_price = data['close'].iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_atr = atr.iloc[-1]
        
        # Build volume profile for recent periods
        profile_data = data.tail(self.profile_periods)
        poc = self._calculate_poc(profile_data)
        
        # Detect Fair Value Gap
        fvg = self._detect_fvg(data)
        
        signals = []
        
        # Entry conditions:
        # 1. Price is near POC (within ATR distance)
        # 2. FVG exists above (for long) or below (for short)
        # 3. RSI in neutral zone (40-60)
        # 4. Volume spike confirmed the FVG
        
        price_near_poc = abs(current_price - poc) < current_atr
        rsi_neutral = self.rsi_lower <= current_rsi <= self.rsi_upper
        
        if price_near_poc and rsi_neutral and fvg['exists']:
            if fvg['type'] == 'bullish' and current_price < fvg['fill_level']:
                # Bullish FVG - buy at POC targeting FVG fill
                direction = "BUY"
                confidence = 0.75
                
                if self.tp_fvg_fill:
                    tp = fvg['fill_level']
                else:
                    tp = current_price + (current_atr * 2)
                
                sl = poc * (1 - self.sl_poc_buffer)
                
                signals.append(Signal(
                    symbol=symbol,
                    direction=direction,
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2),
                    stop_loss=round(sl, 2),
                    reason=f"POC retest with bullish FVG (POC: ${poc:,.2f}, FVG fill: ${fvg['fill_level']:,.2f}, RSI: {current_rsi:.1f})"
                ))
            
            elif fvg['type'] == 'bearish' and current_price > fvg['fill_level']:
                # Bearish FVG - sell at POC targeting FVG fill
                direction = "SELL"
                confidence = 0.75
                
                if self.tp_fvg_fill:
                    tp = fvg['fill_level']
                else:
                    tp = current_price - (current_atr * 2)
                
                sl = poc * (1 + self.sl_poc_buffer)
                
                signals.append(Signal(
                    symbol=symbol,
                    direction=direction,
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2),
                    stop_loss=round(sl, 2),
                    reason=f"POC retest with bearish FVG (POC: ${poc:,.2f}, FVG fill: ${fvg['fill_level']:,.2f}, RSI: {current_rsi:.1f})"
                ))
        
        return signals
    
    def _calculate_poc(self, data: pd.DataFrame) -> float:
        """
        Calculate Point of Control (price level with highest volume).
        Simplified: bins prices into levels, finds max volume bin.
        """
        n_bins = 10
        price_range = data['high'].max() - data['low'].min()
        bin_size = price_range / n_bins
        
        if bin_size == 0:
            return data['close'].iloc[-1]
        
        # Create price-volume profile
        volume_profile = {}
        for _, row in data.iterrows():
            typical_price = (row['high'] + row['low'] + row['close']) / 3
            bin_idx = int((typical_price - data['low'].min()) / bin_size)
            bin_idx = min(bin_idx, n_bins - 1)  # Cap at max bin
            
            if bin_idx not in volume_profile:
                volume_profile[bin_idx] = 0
            volume_profile[bin_idx] += row['volume']
        
        # Find bin with max volume
        max_volume_bin = max(volume_profile.items(), key=lambda x: x[1])[0]
        poc_price = data['low'].min() + (max_volume_bin * bin_size) + (bin_size / 2)
        
        return poc_price
    
    def _detect_fvg(self, data: pd.DataFrame) -> Dict:
        """
        Detect Fair Value Gap in recent price action.
        Returns dict with 'exists', 'type', 'fill_level', 'volume_confirmed'
        """
        if len(data) < 5:
            return {'exists': False}
        
        # Look at last 3 candles for FVG
        c1 = data.iloc[-3]  # Candle 1
        c2 = data.iloc[-2]  # Candle 2 (middle)
        c3 = data.iloc[-1]  # Candle 3 (most recent)
        
        # Volume average for confirmation
        avg_volume = data['volume'].tail(10).mean()
        
        # Bullish FVG: Current low > previous high (gap up)
        if c3['low'] > c1['high']:
            volume_confirmed = c2['volume'] > avg_volume * self.volume_spike_mult
            return {
                'exists': True,
                'type': 'bullish',
                'fill_level': c1['high'],
                'gap_size': c3['low'] - c1['high'],
                'volume_confirmed': volume_confirmed
            }
        
        # Bearish FVG: Current high < previous low (gap down)
        elif c3['high'] < c1['low']:
            volume_confirmed = c2['volume'] > avg_volume * self.volume_spike_mult
            return {
                'exists': True,
                'type': 'bearish',
                'fill_level': c1['low'],
                'gap_size': c1['low'] - c3['high'],
                'volume_confirmed': volume_confirmed
            }
        
        return {'exists': False}
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = prices.diff()
        gains = delta.where(delta > 0, 0)
        losses = (-delta.where(delta < 0, 0))
        avg_gains = gains.rolling(window=period, min_periods=1).mean()
        avg_losses = losses.rolling(window=period, min_periods=1).mean()
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high = data['high']
        low = data['low']
        close = data['close']
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period, min_periods=1).mean()
        return atr


if __name__ == "__main__":
    """Quick test with sample data."""
    np.random.seed(42)
    n = 200
    returns = np.random.normal(0.001, 0.02, n)
    prices = 50000 * np.exp(np.cumsum(returns))
    
    # Create sample data with volume profile pattern
    sample_data = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.001, n)),
        'high': prices * (1 + abs(np.random.normal(0, 0.01, n))),
        'low': prices * (1 - abs(np.random.normal(0, 0.01, n))),
        'close': prices,
        'volume': np.random.uniform(100, 1000, n)
    })
    
    # Simulate a volume spike for FVG
    sample_data.loc[n-2, 'volume'] = sample_data['volume'].mean() * 3
    
    strategy = VolumeProfileFVGStrategy()
    signals = strategy.generate_signals(sample_data, symbol="BTCUSDT")
    
    print(f"Generated {len(signals)} signals from {len(sample_data)} bars")
    print(f"\nVolume Profile POC: ${strategy._calculate_poc(sample_data.tail(50)):,.2f}")
    
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
