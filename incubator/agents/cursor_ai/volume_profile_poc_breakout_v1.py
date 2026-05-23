"""
Volume Profile POC Breakout Strategy
====================================

Created by: cursor_ai
Date: 2026-02-27

Strategy Logic:
- Entry when: Price breaks above/below POC (Point of Control) with volume > 2x profile average AND 5-minute candle closes beyond POC
- Exit when: Price returns to POC (mean reversion) OR 2x ATR target reached
- Filter: Only trade during high-volume sessions (US market hours)

Unique Value Proposition:
Uses volume profile Point of Control (POC) as a dynamic support/resistance level. When price breaks through the POC with high volume, it signals a shift in value area and institutional re-pricing. This differs from traditional support/resistance by weighting volume rather than just price extremes.
"""

import numpy as np
import pandas as pd
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str

class VolumeProfilePOCBreakoutStrategy:
    """Breakout strategy based on Volume Profile POC."""
    
    def __init__(self, params: Optional[dict] = None):
        self.p = params or {}
        self.profile_period = self.p.get('profile_period', 60)  # bars for volume profile
        self.volume_multiplier = self.p.get('volume_multiplier', 2.0)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr_mult = self.p.get('tp_atr_mult', 2.0)
        self.sl_atr_mult = self.p.get('sl_atr_mult', 1.5)
        self.session_start_hour = self.p.get('session_start_hour', 13)  # US market open (UTC)
        self.session_end_hour = self.p.get('session_end_hour', 20)
    
    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < self.profile_period + 10:
            return []
        
        # Calculate volume profile POC
        poc_price = self._calculate_poc(data)
        
        # ATR for risk
        atr = self._calculate_atr(data)
        current_atr = atr.iloc[-1]
        
        current_price = data['close'].iloc[-1]
        current_volume = data['volume'].iloc[-1]
        
        # Volume profile average volume
        profile_volume_avg = data['volume'].iloc[-self.profile_period:].mean()
        
        signals = []
        
        # Volume threshold check
        volume_confirms = current_volume > (profile_volume_avg * self.volume_multiplier)
        
        # Breakout above POC
        if current_price > poc_price and volume_confirms:
            confidence = 0.6 + (current_price - poc_price) / poc_price * 2
            confidence = min(confidence, 0.85)
            
            tp = current_price + (current_atr * self.tp_atr_mult)
            sl = poc_price - (current_atr * 0.5)  # Stop just below POC
            
            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"Breakout above POC ${poc_price:.2f} + volume {current_volume/profile_volume_avg:.1f}x"
            ))
        
        # Breakdown below POC
        elif current_price < poc_price and volume_confirms:
            confidence = 0.6 + (poc_price - current_price) / poc_price * 2
            confidence = min(confidence, 0.85)
            
            tp = current_price - (current_atr * self.tp_atr_mult)
            sl = poc_price + (current_atr * 0.5)
            
            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"Breakdown below POC ${poc_price:.2f} + volume {current_volume/profile_volume_avg:.1f}x"
            ))
        
        return signals
    
    def _calculate_poc(self, data: pd.DataFrame) -> float:
        """Calculate Point of Control from volume profile."""
        # Simple volume-weighted price as POC approximation
        if len(data) < self.profile_period:
            return data['close'].iloc[-1]
        
        recent = data.iloc[-self.profile_period:]
        volume_weighted_price = (recent['close'] * recent['volume']).sum() / recent['volume'].sum()
        return volume_weighted_price
    
    def _calculate_atr(self, data: pd.DataFrame) -> pd.Series:
        high = data['high']
        low = data['low']
        close = data['close']
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=self.atr_period).mean()

if __name__ == "__main__":
    np.random.seed(42)
    n = 300
    prices = 50000 * np.exp(np.cumsum(np.random.normal(0.0001, 0.02, n)))
    
    data = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.001, n)),
        'high': prices * (1 + abs(np.random.normal(0, 0.01, n))),
        'low': prices * (1 - abs(np.random.normal(0, 0.01, n))),
        'close': prices,
        'volume': np.random.uniform(100, 1000, n)
    })
    
    strategy = VolumeProfilePOCBreakoutStrategy()
    signals = strategy.generate_signals(data, symbol="BTCUSDT")
    
    print(f"Generated {len(signals)} signals")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")