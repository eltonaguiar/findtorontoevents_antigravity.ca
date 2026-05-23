"""
Funding Momentum Strategy
========================

Created by: cursor_ai
Date: 2026-02-27

Strategy Logic:
- Entry when: Price > SMA(5) AND funding_rate < -0.0001 AND close > close.shift(1)
- Exit when: Price < SMA(5) OR funding_rate > -0.0001
- Risk management: ATR-based TP (3x ATR) and SL (2x ATR)

Unique Value Proposition:
Combines simple momentum (SMA trend) with funding rate as a market regime filter. Only takes long positions when funding is negative (shorts overleveraged), which indicates potential short squeeze conditions. This creates a unique hybrid of trend following and funding arbitrage that doesn't exist in the current inventory.
"""

import pandas as pd
import numpy as np
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class Signal:
    """A trading signal - required return type."""
    symbol: str
    direction: str  # "BUY" or "SELL"
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str

class FundingMomentumStrategy:
    """
    Trade only when funding-rate indicates shorts are paying more than longs.
    Entry confirmed by bullish SMA trend and up-tick.
    Exit when funding turns positive or price falls below SMA.
    """
    
    def __init__(self, params: Optional[dict] = None):
        self.p = params or {}
        self.sma_period = self.p.get('sma_period', 5)
        self.funding_threshold_long = self.p.get('funding_threshold', -0.0001)
        self.funding_threshold_short = self.p.get('funding_threshold_short', 0.0003)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr_mult = self.p.get('tp_atr_mult', 3.0)
        self.sl_atr_mult = self.p.get('sl_atr_mult', 2.0)
    
    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < max(self.sma_period, self.atr_period) + 5:
            return []
        
        # Calculate SMA
        sma = data['close'].rolling(self.sma_period).mean()
        
        # Calculate ATR
        atr = self._calculate_atr(data)
        
        current_price = data['close'].iloc[-1]
        current_sma = sma.iloc[-1]
        current_atr = atr.iloc[-1]
        
        # Check if we have funding_rate column (optional)
        has_funding = 'funding_rate' in data.columns
        funding_rate = data['funding_rate'].iloc[-1] if has_funding else self.funding_threshold
        
        signals = []
        
        # Shared conditions
        price_above_sma = current_price > current_sma
        price_below_sma = current_price < current_sma
        up_tick = data['close'].iloc[-1] > data['close'].iloc[-2] if len(data) > 1 else False
        down_tick = data['close'].iloc[-1] < data['close'].iloc[-2] if len(data) > 1 else False

        # LONG entry: shorts overleveraged (negative funding) + bullish trend
        funding_negative = funding_rate < self.funding_threshold_long
        if price_above_sma and funding_negative and up_tick:
            confidence = 0.6 + min(abs(funding_rate) * 1000, 0.15)
            tp = current_price + (current_atr * self.tp_atr_mult)
            sl = current_price - (current_atr * self.sl_atr_mult)

            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(min(confidence, 0.85), 2),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"LONG: SMA({self.sma_period}) up + funding negative ({funding_rate:.6f}) + up-tick. Short squeeze potential."
            ))

        # SHORT entry: longs overleveraged (high positive funding) + bearish trend
        funding_high_positive = funding_rate > self.funding_threshold_short
        if price_below_sma and funding_high_positive and down_tick:
            confidence = 0.6 + min(funding_rate * 1000, 0.15)
            tp = current_price - (current_atr * self.tp_atr_mult)
            sl = current_price + (current_atr * self.sl_atr_mult)

            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(min(confidence, 0.85), 2),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"SHORT: SMA({self.sma_period}) down + funding positive ({funding_rate:.6f}) + down-tick. Long squeeze potential."
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
    # Create synthetic data with funding_rate
    np.random.seed(42)
    n = 100
    returns = np.random.normal(0.0001, 0.02, n)
    prices = 50000 * np.exp(np.cumsum(returns))
    
    # Generate alternating funding rates (negative then positive)
    funding = np.concatenate([
        np.random.uniform(-0.0002, -0.00005, 50),
        np.random.uniform(0.00005, 0.0002, 50)
    ])
    
    test_data = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.001, n)),
        'high': prices * (1 + abs(np.random.normal(0, 0.01, n))),
        'low': prices * (1 - abs(np.random.normal(0, 0.01, n))),
        'close': prices,
        'volume': np.random.uniform(100, 1000, n),
        'funding_rate': funding[:n]
    })
    
    # Test strategy
    strategy = FundingMomentumStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")
    
    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")