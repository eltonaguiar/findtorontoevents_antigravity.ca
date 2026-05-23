"""
LiquiditySweepReversalStrategy - Baby Strat
===========================================

Created by: AI Assistant
Date: 2026-02-27

Strategy Logic:
- Entry when: Price sweeps liquidity (takes out recent highs/lows) then reverses
- Exit when: TP/SL hit or next structure level
- Risk management: Stop beyond sweep wick, TP at opposing liquidity

Unique Value Proposition:
Detects "stop hunts" and liquidity grabs - when price briefly breaks a key level
to trigger stops, then immediately reverses. Classic Smart Money reversal pattern.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
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


class LiquiditySweepReversalStrategy:
    """
    Liquidity Sweep Reversal Strategy
    
    Identifies stop hunts where price:
    1. Takes out a recent swing high/low (liquidity)
    2. Has a long wick (rejection)
    3. Closes back within range (failure to hold)
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.lookback = self.params.get('lookback', 10)
        self.wick_threshold = self.params.get('wick_threshold', 0.6)
        self.close_rejection = self.params.get('close_rejection', 0.3)
        self.volume_confirm = self.params.get('volume_confirm', True)
        self.volume_threshold = self.params.get('volume_threshold', 1.3)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_ratio = self.params.get('tp_ratio', 2.0)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < max(self.lookback, self.atr_period) + 5:
            return []

        # Calculate indicators
        atr = self._calculate_atr(data, self.atr_period)
        
        # Get recent bars
        recent_highs = data['high'].iloc[-self.lookback-1:-1]
        recent_lows = data['low'].iloc[-self.lookback-1:-1]
        
        current_bar = {
            'open': data['open'].iloc[-1],
            'high': data['high'].iloc[-1],
            'low': data['low'].iloc[-1],
            'close': data['close'].iloc[-1],
            'volume': data['volume'].iloc[-1]
        }
        
        prev_bar_close = data['close'].iloc[-2]
        current_atr = atr.iloc[-1]
        
        # Volume check
        volume_ma = data['volume'].rolling(window=20).mean().iloc[-1]
        volume_ok = current_bar['volume'] > volume_ma * self.volume_threshold
        
        signals = []
        
        # Check for bearish liquidity sweep (takes highs, reverses down)
        recent_high = recent_highs.max()
        
        upper_wick = current_bar['high'] - max(current_bar['open'], current_bar['close'])
        lower_wick = min(current_bar['open'], current_bar['close']) - current_bar['low']
        body = abs(current_bar['close'] - current_bar['open'])
        total_range = current_bar['high'] - current_bar['low']
        
        if total_range > 0:
            upper_wick_pct = upper_wick / total_range
            lower_wick_pct = lower_wick / total_range
            body_pct = body / total_range
        else:
            upper_wick_pct = lower_wick_pct = body_pct = 0
        
        # Bearish sweep: Takes out recent high with long upper wick, closes lower
        if (current_bar['high'] > recent_high and
            upper_wick_pct > self.wick_threshold and
            current_bar['close'] < current_bar['open'] and  # Red candle
            body_pct < self.close_rejection and  # Small body = rejection
            (not self.volume_confirm or volume_ok)):
            
            confidence = upper_wick_pct * 0.5 + (1 - body_pct) * 0.5
            confidence = min(confidence, 0.95)
            
            entry = current_bar['close']
            sl = current_bar['high'] + (current_atr * 0.5)  # Above sweep high
            tp = entry - (abs(entry - sl) * self.tp_ratio)
            
            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 3),
                entry_price=round(entry, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"Bearish liquidity sweep above {recent_high:.2f} ({upper_wick_pct:.1%} wick)"
            ))
        
        # Bullish sweep: Takes out recent low with long lower wick, closes higher
        recent_low = recent_lows.min()
        
        if (current_bar['low'] < recent_low and
            lower_wick_pct > self.wick_threshold and
            current_bar['close'] > current_bar['open'] and  # Green candle
            body_pct < self.close_rejection and
            (not self.volume_confirm or volume_ok)):
            
            confidence = lower_wick_pct * 0.5 + (1 - body_pct) * 0.5
            confidence = min(confidence, 0.95)
            
            entry = current_bar['close']
            sl = current_bar['low'] - (current_atr * 0.5)  # Below sweep low
            tp = entry + (abs(entry - sl) * self.tp_ratio)
            
            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(entry, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"Bullish liquidity sweep below {recent_low:.2f} ({lower_wick_pct:.1%} wick)"
            ))
        
        return signals

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
    
    strategy = LiquiditySweepReversalStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")
    
    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
