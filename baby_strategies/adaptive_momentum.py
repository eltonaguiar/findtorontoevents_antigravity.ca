"""
AdaptiveMomentumStrategy - Baby Strat
=====================================

Created by: AI Assistant
Date: 2026-02-27

Strategy Logic:
- Entry when: Price momentum in trend direction, adaptive to volatility regime
- Exit when: Momentum fades or counter-momentum signal
- Risk management: Dynamic position sizing based on volatility

Unique Value Proposition:
Uses Perry Kaufman's Efficiency Ratio to adapt momentum speed to market conditions.
In trending markets: faster momentum. In choppy markets: requires stronger confirmation.
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


class AdaptiveMomentumStrategy:
    """
    Adaptive Momentum Strategy using Kaufman's Efficiency Ratio
    
    Efficiency Ratio (ER) = |Price Change| / Sum of absolute price changes
    - ER close to 1 = strong trend (use fast momentum)
    - ER close to 0 = choppy (require stronger confirmation)
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.er_period = self.params.get('er_period', 10)
        self.fast_ema = self.params.get('fast_ema', 12)
        self.slow_ema = self.params.get('slow_ema', 26)
        self.momentum_period = self.params.get('momentum_period', 14)
        self.er_threshold_trend = self.params.get('er_threshold_trend', 0.6)
        self.er_threshold_chop = self.params.get('er_threshold_chop', 0.3)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 3.0)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.5)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < max(self.er_period, self.slow_ema, self.momentum_period) + 10:
            return []

        # Calculate Efficiency Ratio
        er = self._calculate_efficiency_ratio(data['close'], self.er_period)
        
        # Calculate momentum
        momentum = data['close'].diff(self.momentum_period)
        momentum_ma = momentum.rolling(window=5).mean()
        
        # Calculate adaptive EMA based on ER
        adaptive_ema = self._calculate_adaptive_ema(data['close'], er, self.fast_ema, self.slow_ema)
        
        # Calculate ATR
        atr = self._calculate_atr(data, self.atr_period)
        
        current_price = data['close'].iloc[-1]
        prev_price = data['close'].iloc[-2]
        current_er = er.iloc[-1]
        current_momentum = momentum.iloc[-1]
        current_momentum_ma = momentum_ma.iloc[-1]
        current_adaptive_ema = adaptive_ema.iloc[-1]
        current_atr = atr.iloc[-1]
        
        signals = []
        
        # Determine if we're in trend or chop
        is_trending = current_er > self.er_threshold_trend
        is_choppy = current_er < self.er_threshold_chop
        
        # Bullish momentum signal
        # In trends: price above adaptive EMA + positive momentum
        # In chop: requires stronger momentum confirmation
        if (current_price > current_adaptive_ema and 
            current_momentum > 0 and
            current_momentum_ma > 0 and
            (is_trending or (not is_choppy and current_momentum > current_momentum_ma))):
            
            # Scale confidence by ER (stronger trend = higher confidence)
            base_confidence = 0.5
            trend_boost = current_er * 0.3
            momentum_boost = min(abs(current_momentum) / (current_atr * 2), 0.2)
            confidence = min(base_confidence + trend_boost + momentum_boost, 0.95)
            
            # Dynamic TP based on ER (trending markets get wider targets)
            tp_mult = self.tp_atr_mult * (1 + current_er)
            
            tp = current_price + (current_atr * tp_mult)
            sl = current_adaptive_ema - (current_atr * 0.5)
            
            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"Adaptive momentum (ER: {current_er:.2f}, trend: {is_trending})"
            ))
        
        # Bearish momentum signal
        elif (current_price < current_adaptive_ema and 
              current_momentum < 0 and
              current_momentum_ma < 0 and
              (is_trending or (not is_choppy and current_momentum < current_momentum_ma))):
            
            base_confidence = 0.5
            trend_boost = current_er * 0.3
            momentum_boost = min(abs(current_momentum) / (current_atr * 2), 0.2)
            confidence = min(base_confidence + trend_boost + momentum_boost, 0.95)
            
            tp_mult = self.tp_atr_mult * (1 + current_er)
            
            tp = current_price - (current_atr * tp_mult)
            sl = current_adaptive_ema + (current_atr * 0.5)
            
            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"Adaptive momentum (ER: {current_er:.2f}, trend: {is_trending})"
            ))
        
        return signals

    def _calculate_efficiency_ratio(self, prices: pd.Series, period: int) -> pd.Series:
        """
        Calculate Kaufman's Efficiency Ratio
        ER = |Price[n] - Price[0]| / Sum(|Price[i] - Price[i-1]|)
        """
        price_change = prices.diff(period).abs()
        volatility = prices.diff().abs().rolling(window=period).sum()
        er = price_change / volatility
        er = er.replace([np.inf, -np.inf], 0).fillna(0)
        return er

    def _calculate_adaptive_ema(self, prices: pd.Series, er: pd.Series, 
                                fast_period: int, slow_period: int) -> pd.Series:
        """
        Calculate adaptive EMA based on Efficiency Ratio
        Higher ER = faster EMA (more responsive)
        Lower ER = slower EMA (smoother)
        """
        # Scale factor: ER=1 uses fast constant, ER=0 uses slow constant
        fast_sc = 2 / (fast_period + 1)
        slow_sc = 2 / (slow_period + 1)
        
        # Smoothing constant scales with ER
        sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2
        
        # Calculate adaptive EMA
        adaptive_ema = pd.Series(index=prices.index, dtype=float)
        adaptive_ema.iloc[0] = prices.iloc[0]
        
        for i in range(1, len(prices)):
            adaptive_ema.iloc[i] = adaptive_ema.iloc[i-1] + sc.iloc[i] * (prices.iloc[i] - adaptive_ema.iloc[i-1])
        
        return adaptive_ema

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
    
    strategy = AdaptiveMomentumStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")
    
    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
