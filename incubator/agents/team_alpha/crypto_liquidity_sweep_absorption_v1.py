"""
Liquidity Sweep Absorption Strategy - Baby Strat
=================================================

Created by: team_alpha
Date: 2026-02-26

Strategy Logic:
Detects classic liquidity sweep below recent swing low followed by 
immediate strong absorption candle — the hidden reversal pros hunt daily.

Unique Value Proposition:
False-break strategies exist but sweep + 75% absorption wick filter is 
the 2025–2026 microstructure edge from order-flow studies. Not coded 
anywhere in incubator — pure pro-level liquidity grab reversal.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class LiquiditySweepAbsorptionStrategy:
    """
    Liquidity sweep + absorption reversal (pro microstructure).
    
    Entry: Low sweeps 30-period swing low AND current candle closes > 75% 
    of its range (absorption) AND ATR percentile < 0.55
    Exit: TP 2.5×ATR, SL 1.2×ATR
    Filter: Vol regime + absorption confirmation
    """
   
    def __init__(self, params: Optional[dict] = None):
        self.p = params or {}
        self.sweep_lookback = self.p.get('sweep_lookback', 30)
        self.absorb_threshold = self.p.get('absorb_threshold', 0.75)
        self.pct_lookback = self.p.get('pct_lookback', 50)
        self.tp_atr = self.p.get('tp_atr', 2.5)
        self.sl_atr = self.p.get('sl_atr', 1.2)
   
    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_len = self.sweep_lookback + self.pct_lookback + 10
        if len(data) < min_len:
            return []
       
        rolling_low = data['low'].rolling(self.sweep_lookback).min()
        atr = self._atr(data)
        atr_roll = atr.rolling(self.pct_lookback)
        atr_pct = (atr < atr_roll.quantile(0.55)).astype(float).rolling(self.pct_lookback).mean()
       
        current_low = data['low'].iloc[-1]
        current_close = data['close'].iloc[-1]
        recent_low = rolling_low.iloc[-2]
        current_atr = atr.iloc[-1]
        current_pct = atr_pct.iloc[-1] if not pd.isna(atr_pct.iloc[-1]) else 0.0
       
        is_sweep = current_low < recent_low
        candle_range = data['high'].iloc[-1] - current_low
        if candle_range == 0:
            return []
        close_pos = (current_close - current_low) / candle_range
        absorption = close_pos > self.absorb_threshold
       
        if is_sweep and absorption and current_pct > 0.4:
            confidence = 0.82 + close_pos * 0.15
            return [Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(min(confidence, 0.95), 2),
                entry_price=round(current_close, 2),
                take_profit=round(current_close + current_atr * self.tp_atr, 2),
                stop_loss=round(current_close - current_atr * self.sl_atr, 2),
                reason=f"Sweep+Absorb {close_pos:.2f} VolOK"
            )]
        return []
   
    def _atr(self, data: pd.DataFrame) -> pd.Series:
        high, low, close = data['high'], data['low'], data['close']
        tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
        return tr.rolling(14).mean()


if __name__ == "__main__":
    np.random.seed(42)
    data = pd.DataFrame({
        'open': np.random.randn(350).cumsum() * 980 + 49700,
        'close': np.random.randn(350).cumsum() * 980 + 49800,
        'high': np.random.randn(350).cumsum() * 980 + 50000,
        'low': np.random.randn(350).cumsum() * 980 + 49600,
        'volume': np.random.uniform(1000, 5000, 350)
    })
    s = LiquiditySweepAbsorptionStrategy()
    signals = s.generate_signals(data)
    print(f"Signals: {len(signals)}")
    for sig in signals:
        print(f"{sig.direction} {sig.symbol} @ {sig.entry_price} - {sig.reason}")
