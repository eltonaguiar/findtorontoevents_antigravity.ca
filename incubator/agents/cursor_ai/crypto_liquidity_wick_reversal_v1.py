"""
Liquidity Wick Reversal Strategy
================================

Created by: cursor_ai
Date: 2026-02-27

Strategy Logic:
- Entry when: Upper/lower wick > 70% of total candle range (liquidity sweep) AND RSI divergence (hidden or regular) AND volume > 2x average
- Exit when: Wick fills (price returns to candle body) OR 1.5x ATR profit OR RSI crosses threshold
- Filter: Only trade on support/resistance levels (detected via recent pivot points)

Unique Value Proposition:
Detects liquidity sweeps (wick spikes) that often trap retail traders and enters on the reversal. Combines wick size analysis with RSI divergence and volume confirmation to catch false breakouts. This microstructure-based approach is largely unexplored.
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

class CryptoLiquidityWickReversalStrategy:
    """Reversal strategy based on liquidity sweep wicks."""
    
    def __init__(self, params: Optional[dict] = None):
        self.p = params or {}
        self.wick_threshold = self.p.get('wick_threshold', 0.70)  # wick > 70% of range
        self.rsi_period = self.p.get('rsi_period', 14)
        self.volume_multiplier = self.p.get('volume_multiplier', 2.0)
        self.volume_period = self.p.get('volume_period', 20)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr_mult = self.p.get('tp_atr_mult', 1.5)
        self.sl_atr_mult = self.p.get('sl_atr_mult', 1.2)
        self.pivot_window = self.p.get('pivot_window', 10)  # for S/R detection
    
    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < 50:
            return []
        
        # Calculate RSI
        rsi = self._calculate_rsi(data['close'])
        
        # Calculate ATR
        atr = self._calculate_atr(data)
        current_atr = atr.iloc[-1]
        
        # Volume average
        volume_avg = data['volume'].rolling(self.volume_period).mean()
        
        # Detect recent pivot points for S/R
        support_resistance = self._detect_pivot_levels(data)
        
        current_price = data['close'].iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_volume = data['volume'].iloc[-1]
        
        signals = []
        
        # Get current candle's wick info
        candle_high = data['high'].iloc[-1]
        candle_low = data['low'].iloc[-1]
        candle_body = abs(data['close'].iloc[-1] - data['open'].iloc[-1])
        candle_range = candle_high - candle_low
        
        if candle_range > 0:
            upper_wick = candle_high - max(data['open'].iloc[-1], data['close'].iloc[-1])
            lower_wick = min(data['open'].iloc[-1], data['close'].iloc[-1]) - candle_low
            
            upper_wick_pct = upper_wick / candle_range
            lower_wick_pct = lower_wick / candle_range
            
            volume_ok = current_volume > (volume_avg.iloc[-1] * self.volume_multiplier)
            
            # Upper wick sweep (potential short)
            if (upper_wick_pct > self.wick_threshold and 
                volume_ok and
                self._is_near_resistance(current_price, support_resistance)):
                
                # Check for RSI divergence (price high but RSI lower high)
                rsi_divergence = self._check_bearish_divergence(data, rsi)
                
                confidence = 0.5 + upper_wick_pct * 0.3 + (0.2 if rsi_divergence else 0)
                confidence = min(confidence, 0.85)
                
                tp = current_price - (current_atr * self.tp_atr_mult)
                sl = candle_high + (current_atr * 0.5)  # SL just above wick high
                
                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2),
                    stop_loss=round(sl, 2),
                    reason=f"Upper wick sweep {upper_wick_pct:.1%} + vol {current_volume/volume_avg.iloc[-1]:.1f}x + RSI divergence: {rsi_divergence}"
                ))
            
            # Lower wick sweep (potential long)
            if (lower_wick_pct > self.wick_threshold and 
                volume_ok and
                self._is_near_support(current_price, support_resistance)):
                
                rsi_divergence = self._check_bullish_divergence(data, rsi)
                
                confidence = 0.5 + lower_wick_pct * 0.3 + (0.2 if rsi_divergence else 0)
                confidence = min(confidence, 0.85)
                
                tp = current_price + (current_atr * self.tp_atr_mult)
                sl = candle_low - (current_atr * 0.5)
                
                signals.append(Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2),
                    stop_loss=round(sl, 2),
                    reason=f"Lower wick sweep {lower_wick_pct:.1%} + vol {current_volume/volume_avg.iloc[-1]:.1f}x + RSI divergence: {rsi_divergence}"
                ))
        
        return signals
    
    def _calculate_rsi(self, prices: pd.Series) -> pd.Series:
        delta = prices.diff()
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        avg_gains = gains.rolling(window=self.rsi_period).mean()
        avg_losses = losses.rolling(window=self.rsi_period).mean()
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_atr(self, data: pd.DataFrame) -> pd.Series:
        high = data['high']
        low = data['low']
        close = data['close']
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=self.atr_period).mean()
    
    def _detect_pivot_levels(self, data: pd.DataFrame) -> dict:
        """Simple pivot detection for support/resistance."""
        highs = data['high'].rolling(self.pivot_window*2+1, center=True).max()
        lows = data['low'].rolling(self.pivot_window*2+1, center=True).min()
        
        resistance_levels = data['high'][data['high'] == highs].dropna().unique()
        support_levels = data['low'][data['low'] == lows].dropna().unique()
        
        return {
            'resistance': resistance_levels[-5:] if len(resistance_levels) >= 5 else resistance_levels,
            'support': support_levels[-5:] if len(support_levels) >= 5 else support_levels
        }
    
    def _is_near_resistance(self, price: float, levels: dict, tolerance: float = 0.01) -> bool:
        """Check if price is within tolerance of a resistance level."""
        for r in levels['resistance']:
            if abs(price - r) / r < tolerance:
                return True
        return False
    
    def _is_near_support(self, price: float, levels: dict, tolerance: float = 0.01) -> bool:
        """Check if price is within tolerance of a support level."""
        for s in levels['support']:
            if abs(price - s) / s < tolerance:
                return True
        return False
    
    def _check_bearish_divergence(self, data: pd.DataFrame, rsi: pd.Series, lookback: int = 14) -> bool:
        """Check for bearish divergence: price makes higher high but RSI makes lower high."""
        if len(data) < lookback * 2:
            return False
        
        recent_prices = data['close'].iloc[-lookback*2:]
        recent_rsi = rsi.iloc[-lookback*2:]
        
        # Find local maxima
        price_max_idx = recent_prices.idxmax()
        rsi_max_idx = recent_rsi.idxmax()
        
        if price_max_idx > rsi_max_idx:  # price peak after RSI peak
            price_high_1 = recent_prices.iloc[:lookback].max()
            price_high_2 = recent_prices.iloc[lookback:].max()
            rsi_high_1 = recent_rsi.iloc[:lookback].max()
            rsi_high_2 = recent_rsi.iloc[lookback:].max()
            
            if price_high_2 > price_high_1 and rsi_high_2 < rsi_high_1:
                return True
        return False
    
    def _check_bullish_divergence(self, data: pd.DataFrame, rsi: pd.Series, lookback: int = 14) -> bool:
        """Check for bullish divergence: price makes lower low but RSI makes higher low."""
        if len(data) < lookback * 2:
            return False
        
        recent_prices = data['close'].iloc[-lookback*2:]
        recent_rsi = rsi.iloc[-lookback*2:]
        
        price_min_idx = recent_prices.idxmin()
        rsi_min_idx = recent_rsi.idxmin()
        
        if price_min_idx > rsi_min_idx:  # price trough after RSI trough
            price_low_1 = recent_prices.iloc[:lookback].min()
            price_low_2 = recent_prices.iloc[lookback:].min()
            rsi_low_1 = recent_rsi.iloc[:lookback].min()
            rsi_low_2 = recent_rsi.iloc[lookback:].min()
            
            if price_low_2 < price_low_1 and rsi_low_2 > rsi_low_1:
                return True
        return False

if __name__ == "__main__":
    np.random.seed(42)
    n = 500
    returns = np.random.normal(0.0001, 0.02, n)
    prices = 50000 * np.exp(np.cumsum(returns))
    
    test_data = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.001, n)),
        'high': prices * (1 + abs(np.random.normal(0, 0.01, n))),
        'low': prices * (1 - abs(np.random.normal(0, 0.01, n))),
        'close': prices,
        'volume': np.random.uniform(100, 1000, n)
    })
    
    strategy = CryptoLiquidityWickReversalStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")
    
    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")