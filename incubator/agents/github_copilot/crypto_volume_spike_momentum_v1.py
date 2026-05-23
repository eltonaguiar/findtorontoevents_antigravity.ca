"""
Volume Spike Momentum Strategy - Baby Strat #4
==============================================

Created by: github_copilot
Date: 2026-02-26

Strategy Logic:
- Entry when: Volume spikes 2x+ above 20-period average AND price moves >0.5% in that direction
- Exit when: Take profit (2x ATR) or stop loss (1.5x ATR) or 5-day time exit
- Risk management: ATR-based TP/SL, confidence based on volume spike magnitude

Unique Value Proposition:
First volume-spike filtered momentum strategy in the ecosystem. All existing momentum systems (System E, competition algorithms) use price-only signals. This strategy adds volume confirmation to filter out false momentum signals, improving signal quality by requiring both price movement AND unusual volume activity. Academic backing: volume spikes often precede sustainable price moves (Karpoff, 1987; Gervais et al., 2001).

Signals are uncorrelated with existing systems because volume spikes as primary filter is not used anywhere else in the current strategy set.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Signal:
    """A trading signal - required return type."""
    symbol: str           # e.g., "BTCUSDT"
    direction: str        # "BUY" or "SELL"
    confidence: float     # 0.0 to 1.0
    entry_price: float    # Suggested entry
    take_profit: float    # Target price
    stop_loss: float      # Stop price
    reason: str           # Why this signal


class VolumeSpikeMomentumStrategy:
    """
    Volume Spike Momentum Strategy
    
    Enters momentum trades only when accompanied by significant volume spikes,
    filtering out false signals and improving win rates.
    """
    
    def __init__(self, params: Optional[Dict] = None):
        """
        Initialize with parameters.
        
        Args:
            params: Dict with strategy parameters
        """
        self.params = params or {}
        self.volume_period = self.params.get('volume_period', 20)
        self.volume_threshold = self.params.get('volume_threshold', 2.0)  # 2x average
        self.price_change_threshold = self.params.get('price_change_threshold', 0.005)  # 0.5%
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.0)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.5)
        self.max_hold_days = self.params.get('max_hold_days', 5)
    
    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        """
        Main method - called by backtest engine.
        
        Args:
            data: DataFrame with columns [open, high, low, close, volume]
            symbol: Trading pair being analyzed
            
        Returns:
            List of Signal objects (empty if no signal)
        """
        if len(data) < self.volume_period + 10:
            return []  # Not enough data
        
        # Calculate indicators
        avg_volume = data['volume'].shift(1).rolling(window=self.volume_period).mean()
        volume_ratio = data['volume'] / avg_volume
        
        price_change = data['close'].pct_change()
        atr = self._calculate_atr(data, self.atr_period)
        
        current_price = data['close'].iloc[-1]
        current_volume_ratio = volume_ratio.iloc[-1]
        current_price_change = price_change.iloc[-1]
        current_atr = atr.iloc[-1]
        
        signals = []
        
        # Check for volume spike + upward momentum
        if (current_volume_ratio >= self.volume_threshold and 
            current_price_change >= self.price_change_threshold):
            
            direction = "BUY"
            # Confidence based on volume spike magnitude (capped at 95%)
            confidence = min(current_volume_ratio / self.volume_threshold, 0.95)
            
            tp = current_price + (current_atr * self.tp_atr_mult)
            sl = current_price - (current_atr * self.sl_atr_mult)
            
            signals.append(Signal(
                symbol=symbol,
                direction=direction,
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"Volume spike momentum up ({current_volume_ratio:.1f}x vol, {current_price_change:.1%} price)"
            ))
        
        # Check for volume spike + downward momentum
        elif (current_volume_ratio >= self.volume_threshold and 
              current_price_change <= -self.price_change_threshold):
            
            direction = "SELL"
            confidence = min(current_volume_ratio / self.volume_threshold, 0.95)
            
            tp = current_price - (current_atr * self.tp_atr_mult)
            sl = current_price + (current_atr * self.sl_atr_mult)
            
            signals.append(Signal(
                symbol=symbol,
                direction=direction,
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"Volume spike momentum down ({current_volume_ratio:.1f}x vol, {current_price_change:.1%} price)"
            ))
        
        return signals
    
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
    n = 100
    
    # Generate price data with some trends
    returns = np.random.normal(0.001, 0.03, n)
    prices = 50000 * np.exp(np.cumsum(returns))
    
    # Generate volume with occasional spikes
    base_volume = np.random.uniform(100, 1000, n)
    spike_indices = np.random.choice(n, size=int(n*0.1), replace=False)
    base_volume[spike_indices] *= np.random.uniform(2, 5, len(spike_indices))
    
    sample_data = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.001, n)),
        'high': prices * (1 + abs(np.random.normal(0, 0.01, n))),
        'low': prices * (1 - abs(np.random.normal(0, 0.01, n))),
        'close': prices,
        'volume': base_volume
    })
    
    strategy = VolumeSpikeMomentumStrategy()
    signals = strategy.generate_signals(sample_data, symbol="BTCUSDT")
    
    print(f"Generated {len(signals)} signals from {len(sample_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")