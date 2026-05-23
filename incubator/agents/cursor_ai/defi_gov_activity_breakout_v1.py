"""
DeFi Governance Activity Breakout Strategy
==========================================

Created by: cursor_ai
Date: 2026-02-27

Strategy Logic:
- Entry when: Governance proposal activity spikes > 3x 30-day average AND token price > 20-day SMA AND social mentions > 2x average
- Exit when: Proposal activity returns to normal OR price drops below 20-day SMA
- Risk management: 2.5x ATR take profit, 1.8x ATR stop loss

Unique Value Proposition:
Monitors on-chain governance activity (Snapshot, Tally, etc.) as a leading indicator for DeFi token price movements. Surges in governance proposals often precede price appreciation as community engagement increases. This combines on-chain governance metrics with price action for a unique DeFi-specific strategy.
"""

import numpy as np
import pandas as pd
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str

class DefiGovActivityBreakoutStrategy:
    """Governance activity breakout for DeFi tokens."""
    
    def __init__(self, params: Optional[dict] = None):
        self.p = params or {}
        self.gov_period = self.p.get('gov_period', 30)
        self.gov_spike_multiplier = self.p.get('gov_spike_multiplier', 3.0)
        self.sma_period = self.p.get('sma_period', 20)
        self.social_period = self.p.get('social_period', 20)
        self.social_spike_multiplier = self.p.get('social_spike_multiplier', 2.0)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr_mult = self.p.get('tp_atr_mult', 2.5)
        self.sl_atr_mult = self.p.get('sl_atr_mult', 1.8)
    
    def generate_signals(
        self,
        data: pd.DataFrame,
        gov_data: Optional[pd.Series] = None,
        social_data: Optional[pd.Series] = None,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < 30:
            return []
        
        # Price indicators
        sma = data['close'].rolling(self.sma_period).mean()
        atr = self._calculate_atr(data)
        current_atr = atr.iloc[-1]
        current_price = data['close'].iloc[-1]
        current_sma = sma.iloc[-1]
        
        # Governance activity (mock - replace with on-chain API)
        gov_activity = self._get_gov_activity(gov_data)
        gov_avg = gov_activity.rolling(self.gov_period).mean().iloc[-1] if len(gov_activity) > 0 else 1
        gov_spike = gov_activity.iloc[-1] > (gov_avg * self.gov_spike_multiplier)
        
        # Social activity (mock)
        social_mentions = self._get_social_mentions(social_data)
        social_avg = social_mentions.rolling(self.social_period).mean().iloc[-1] if len(social_mentions) > 0 else 1
        social_spike = social_mentions.iloc[-1] > (social_avg * self.social_spike_multiplier)
        
        signals = []
        
        # Entry: Governance spike + social spike + price above SMA
        if (gov_spike and 
            social_spike and 
            current_price > current_sma):
            
            confidence = 0.5
            if gov_activity.iloc[-1] / gov_avg > 5:
                confidence += 0.2
            if social_mentions.iloc[-1] / social_avg > 3:
                confidence += 0.2
            confidence = min(confidence, 0.85)
            
            tp = current_price + (current_atr * self.tp_atr_mult)
            sl = current_price - (current_atr * self.sl_atr_mult)
            
            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"Gov activity {gov_activity.iloc[-1]:.0f} > {gov_avg*self.gov_spike_multiplier:.0f} + social {social_mentions.iloc[-1]:.0f} > avg + price > SMA({self.sma_period})"
            ))
        
        # Exit: Activity normalizes or price below SMA
        elif (not gov_spike or current_price < current_sma):
            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=0.5,
                entry_price=round(current_price, 2),
                take_profit=round(current_price - (current_atr * self.tp_atr_mult), 2),
                stop_loss=round(current_price + (current_atr * self.sl_atr_mult), 2),
                reason=f"Gov activity normalized or price below SMA"
            ))
        
        return signals
    
    def _calculate_atr(self, data: pd.DataFrame) -> pd.Series:
        high = data['high']
        low = data['low']
        close = data['close']
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=self.atr_period).mean()
    
    def _get_gov_activity(self, gov_data: Optional[pd.Series]) -> pd.Series:
        """Mock governance activity - replace with Snapshot/Tally API"""
        if gov_data is not None:
            return gov_data
        # Deterministic mock
        np.random.seed(42)
        return pd.Series(np.random.randint(1, 100, 100))
    
    def _get_social_mentions(self, social_data: Optional[pd.Series]) -> pd.Series:
        """Mock social mentions - replace with Twitter/Reddit API"""
        if social_data is not None:
            return social_data
        np.random.seed(43)
        return pd.Series(np.random.randint(100, 1000, 100))

if __name__ == "__main__":
    np.random.seed(42)
    n = 200
    prices = 50000 * np.exp(np.cumsum(np.random.normal(0.0001, 0.02, n)))
    
    data = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.001, n)),
        'high': prices * (1 + abs(np.random.normal(0, 0.01, n))),
        'low': prices * (1 - abs(np.random.normal(0, 0.01, n))),
        'close': prices,
        'volume': np.random.uniform(100, 1000, n)
    })
    
    strategy = DefiGovActivityBreakoutStrategy()
    signals = strategy.generate_signals(data, symbol="UNI")
    
    print(f"Generated {len(signals)} signals")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")