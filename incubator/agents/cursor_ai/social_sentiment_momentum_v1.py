"""
Social Sentiment Momentum Strategy
==================================

Created by: cursor_ai
Date: 2026-02-27

Strategy Logic:
- Entry when: RSI > 50 AND social_sentiment_score > 0.6 AND volume > 1.5x 20-bar average
- Exit when: RSI crosses below 40 OR social_sentiment_score drops below 0.4 OR 2.5x ATR profit reached
- Risk management: ATR-based stop loss (1.5x) and take profit (2.5x)

Unique Value Proposition:
Combines technical momentum (RSI) with social sentiment analysis from Twitter/Reddit/Discord to confirm trend strength. This hybrid approach filters out purely technical moves that lack social consensus, improving signal quality. Social sentiment is an underexplored data source in the existing inventory.
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

class SocialSentimentMomentumStrategy:
    """Momentum strategy enhanced with social sentiment scoring."""
    
    def __init__(self, params: Optional[dict] = None):
        self.p = params or {}
        self.rsi_period = self.p.get('rsi_period', 14)
        self.rsi_entry_threshold = self.p.get('rsi_entry_threshold', 50)
        self.rsi_exit_threshold = self.p.get('rsi_exit_threshold', 40)
        self.sentiment_threshold_entry = self.p.get('sentiment_threshold_entry', 0.6)
        self.sentiment_threshold_exit = self.p.get('sentiment_threshold_exit', 0.4)
        self.volume_multiplier = self.p.get('volume_multiplier', 1.5)
        self.volume_period = self.p.get('volume_period', 20)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr_mult = self.p.get('tp_atr_mult', 2.5)
        self.sl_atr_mult = self.p.get('sl_atr_mult', 1.5)
    
    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < max(self.rsi_period, self.volume_period, self.atr_period) + 10:
            return []
        
        # Calculate RSI
        rsi = self._calculate_rsi(data['close'])
        current_rsi = rsi.iloc[-1]
        
        # Calculate ATR
        atr = self._calculate_atr(data)
        current_atr = atr.iloc[-1]
        
        # Volume check
        avg_volume = data['volume'].rolling(self.volume_period).mean().iloc[-1]
        current_volume = data['volume'].iloc[-1]
        volume_ok = current_volume > (avg_volume * self.volume_multiplier)
        
        # Get social sentiment (mock implementation - replace with real Twitter/Reddit/Discord NLP API)
        sentiment = self._get_social_sentiment(symbol)
        
        current_price = data['close'].iloc[-1]
        
        signals = []
        
        # Long entry: RSI > 50, sentiment > 0.6, volume spike
        if (current_rsi > self.rsi_entry_threshold and 
            sentiment >= self.sentiment_threshold_entry and
            volume_ok):
            
            confidence = 0.5 + ((current_rsi - 50) / 50) * 0.2 + (sentiment - 0.6) * 0.3
            confidence = min(confidence, 0.9)
            
            tp = current_price + (current_atr * self.tp_atr_mult)
            sl = current_price - (current_atr * self.sl_atr_mult)
            
            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"RSI {current_rsi:.1f} > 50 + Sentiment {sentiment:.2f} + Volume {current_volume/avg_volume:.1f}x"
            ))
        
        # Exit long: RSI drops below 40 or sentiment weakens
        elif (current_rsi < self.rsi_exit_threshold or sentiment < self.sentiment_threshold_exit):
            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=0.5,
                entry_price=round(current_price, 2),
                take_profit=round(current_price - (current_atr * self.tp_atr_mult), 2),
                stop_loss=round(current_price + (current_atr * self.sl_atr_mult), 2),
                reason=f"Exit: RSI {current_rsi:.1f} < 40 or Sentiment {sentiment:.2f} < 0.4"
            ))
        
        return signals
    
    def _calculate_rsi(self, prices: pd.Series) -> pd.Series:
        delta = prices.diff()
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        avg_gains = gains.rolling(window=self.rsi_period, min_periods=1).mean()
        avg_losses = losses.rolling(window=self.rsi_period, min_periods=1).mean()
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
        return tr.rolling(window=self.atr_period, min_periods=1).mean()
    
    def _get_social_sentiment(self, symbol: str) -> float:
        """Mock social sentiment - replace with real Twitter/Reddit/Discord NLP API"""
        # Deterministic mock based on symbol hash for consistency
        np.random.seed(hash(symbol) % 1000)
        base = 0.5  # neutral baseline
        noise = np.random.uniform(-0.2, 0.3)  # slight bullish bias
        return max(0.0, min(1.0, base + noise))

if __name__ == "__main__":
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
    
    strategy = SocialSentimentMomentumStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")
    
    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")