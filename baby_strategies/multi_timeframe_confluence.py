"""
MultiTimeframeConfluenceStrategy - Baby Strat
=============================================

Created by: AI Assistant
Date: 2026-02-27

Strategy Logic:
- Entry when: Multiple timeframes align (trend + entry signal)
- Exit when: Higher timeframe trend changes or SL/TP hit
- Risk management: Aligned with higher timeframe structure

Unique Value Proposition:
Simulates multi-timeframe analysis on single timeframe data by using
multiple lookback periods to represent HTF and LTF signals.
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


class MultiTimeframeConfluenceStrategy:
    """
    Multi-Timeframe Confluence Strategy
    
    Uses multiple lookback periods to simulate HTF trend and LTF entry:
    - HTF (Higher Timeframe): 4x lookback for trend direction
    - MTF (Medium Timeframe): 2x lookback for momentum
    - LTF (Lower Timeframe): 1x lookback for entry timing
    
    All timeframes must align for entry.
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.htf_ema = self.params.get('htf_ema', 50)  # Higher TF
        self.mtf_ema = self.params.get('mtf_ema', 21)  # Medium TF
        self.ltf_ema = self.params.get('ltf_ema', 8)   # Lower TF
        self.rsi_period = self.params.get('rsi_period', 14)
        self.rsi_long = self.params.get('rsi_long', 50)
        self.rsi_short = self.params.get('rsi_short', 50)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.5)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.5)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < max(self.htf_ema, self.mtf_ema, self.ltf_ema, self.rsi_period) + 20:
            return []

        # Calculate EMAs for different "timeframes"
        htf_ema = data['close'].ewm(span=self.htf_ema, min_periods=self.htf_ema).mean()
        mtf_ema = data['close'].ewm(span=self.mtf_ema, min_periods=self.mtf_ema).mean()
        ltf_ema = data['close'].ewm(span=self.ltf_ema, min_periods=self.ltf_ema).mean()
        
        # Calculate RSI
        rsi = self._calculate_rsi(data['close'], self.rsi_period)
        
        # Calculate ATR
        atr = self._calculate_atr(data, self.atr_period)
        
        current_price = data['close'].iloc[-1]
        prev_price = data['close'].iloc[-2]
        
        htf_val = htf_ema.iloc[-1]
        mtf_val = mtf_ema.iloc[-1]
        ltf_val = ltf_ema.iloc[-1]
        
        current_rsi = rsi.iloc[-1]
        current_atr = atr.iloc[-1]
        
        signals = []
        
        # HTF Trend: Price above HTF EMA = bullish, below = bearish
        htf_bullish = current_price > htf_val
        htf_bearish = current_price < htf_val
        
        # MTF Momentum: MTF EMA direction
        mtf_bullish = mtf_val > htf_val  # MTF above HTF
        mtf_bearish = mtf_val < htf_val
        
        # LTF Entry: Price crosses LTF EMA with RSI confirmation
        ltf_cross_up = (prev_price <= ltf_ema.iloc[-2] and current_price > ltf_val)
        ltf_cross_down = (prev_price >= ltf_ema.iloc[-2] and current_price < ltf_val)
        
        # Bullish confluence: HTF trend up + MTF aligned + LTF entry
        if htf_bullish and mtf_bullish and ltf_cross_up and current_rsi > self.rsi_long:
            # Calculate confluence score
            htf_score = min((current_price - htf_val) / htf_val / 0.05, 0.3)
            mtf_score = min((mtf_val - htf_val) / htf_val / 0.03, 0.2)
            rsi_score = (current_rsi - 50) / 50 * 0.3
            confidence = min(0.4 + htf_score + mtf_score + rsi_score, 0.95)
            
            tp = current_price + (current_atr * self.tp_atr_mult)
            sl = ltf_val - (current_atr * self.sl_atr_mult * 0.5)
            
            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"HTF+MTF+LTF confluence (RSI: {current_rsi:.1f})"
            ))
        
        # Bearish confluence
        elif htf_bearish and mtf_bearish and ltf_cross_down and current_rsi < self.rsi_short:
            htf_score = min((htf_val - current_price) / htf_val / 0.05, 0.3)
            mtf_score = min((htf_val - mtf_val) / htf_val / 0.03, 0.2)
            rsi_score = (50 - current_rsi) / 50 * 0.3
            confidence = min(0.4 + htf_score + mtf_score + rsi_score, 0.95)
            
            tp = current_price - (current_atr * self.tp_atr_mult)
            sl = ltf_val + (current_atr * self.sl_atr_mult * 0.5)
            
            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"HTF+MTF+LTF confluence (RSI: {current_rsi:.1f})"
            ))
        
        return signals

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        delta = prices.diff()
        gains = delta.where(delta > 0, 0)
        losses = (-delta.where(delta < 0, 0))
        avg_gains = gains.ewm(span=period, min_periods=1).mean()
        avg_losses = losses.ewm(span=period, min_periods=1).mean()
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        return rsi

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
    
    strategy = MultiTimeframeConfluenceStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")
    
    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
