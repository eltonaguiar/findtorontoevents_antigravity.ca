"""
Kelly Position Sizing Strategy
==============================

Created by: cursor_ai
Date: 2026-02-27

Strategy Logic:
- Base strategy: RSI mean reversion (oversold < 30 buy, overbought > 70 sell)
- Position sizing: Kelly Criterion based on recent win rate and payoff ratio
- Kelly fraction = (win_rate * (1 + risk_reward)) - (1 - win_rate)
- Position size = account_balance * Kelly_fraction * max_capital_pct

Unique Value Proposition:
Dynamically adjusts position size based on recent performance using Kelly Criterion. When win rate is high and risk/reward is favorable, it increases exposure. When performance degrades, it reduces size automatically. This provides an adaptive, mathematical approach to position sizing that static ATR-based methods lack.
"""

import numpy as np
import pandas as pd
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str
    position_size_multiplier: float = 1.0  # Kelly-adjusted sizing

class KellyPositionSizingStrategy:
    """
    RSI mean reversion with Kelly Criterion position sizing.
    Kelly fraction calculated from recent trade performance.
    """
    
    def __init__(self, params: Optional[dict] = None):
        self.p = params or {}
        self.rsi_period = self.p.get('rsi_period', 14)
        self.rsi_oversold = self.p.get('rsi_oversold', 30)
        self.rsi_overbought = self.p.get('rsi_overbought', 70)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr_mult = self.p.get('tp_atr_mult', 2.0)
        self.sl_atr_mult = self.p.get('sl_atr_mult', 1.5)
        
        # Kelly parameters
        self.kelly_lookback = self.p.get('kelly_lookback', 50)  # trades to consider
        self.max_capital_pct = self.p.get('max_capital_pct', 0.1)  # max 10% per trade
        self.kelly_fraction_cap = self.p.get('kelly_fraction_cap', 0.5)  # cap Kelly at 50%
        
        # Performance tracking
        self._trade_history = []  # List of dicts: {'win': bool, 'risk_reward': float}
    
    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT",
        account_balance: float = 10000.0
    ) -> List[Signal]:
        if len(data) < self.rsi_period + 10:
            return []
        
        # Calculate indicators
        rsi = self._calculate_rsi(data['close'])
        atr = self._calculate_atr(data)
        
        current_price = data['close'].iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_atr = atr.iloc[-1]
        
        # Calculate Kelly fraction based on recent performance
        kelly_fraction = self._calculate_kelly_fraction()
        position_size_mult = min(kelly_fraction, self.kelly_fraction_cap)
        
        signals = []
        
        # Long entry: RSI oversold
        if current_rsi < self.rsi_oversold:
            direction = "BUY"
            base_confidence = (self.rsi_oversold - current_rsi) / self.rsi_oversold
            confidence = min(base_confidence * 1.2, 0.9)  # boost from Kelly sizing
            
            tp = current_price + (current_atr * self.tp_atr_mult)
            sl = current_price - (current_atr * self.sl_atr_mult)
            risk_reward = self.tp_atr_mult / self.sl_atr_mult
            
            # Position size based on Kelly
            dollar_risk = account_balance * self.max_capital_pct * position_size_mult
            
            signals.append(Signal(
                symbol=symbol,
                direction=direction,
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"RSI oversold ({current_rsi:.1f}) | Kelly fraction: {kelly_fraction:.3f}",
                position_size_multiplier=round(position_size_mult, 3)
            ))
        
        # Short entry: RSI overbought
        elif current_rsi > self.rsi_overbought:
            direction = "SELL"
            base_confidence = (current_rsi - self.rsi_overbought) / (100 - self.rsi_overbought)
            confidence = min(base_confidence * 1.2, 0.9)
            
            tp = current_price - (current_atr * self.tp_atr_mult)
            sl = current_price + (current_atr * self.sl_atr_mult)
            risk_reward = self.tp_atr_mult / self.sl_atr_mult
            
            kelly_fraction = self._calculate_kelly_fraction()
            position_size_mult = min(kelly_fraction, self.kelly_fraction_cap)
            
            signals.append(Signal(
                symbol=symbol,
                direction=direction,
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"RSI overbought ({current_rsi:.1f}) | Kelly fraction: {kelly_fraction:.3f}",
                position_size_multiplier=round(position_size_mult, 3)
            ))
        
        return signals
    
    def _calculate_kelly_fraction(self) -> float:
        """
        Calculate Kelly Criterion fraction based on recent trade history.
        Kelly = (win_rate * (1 + risk_reward_avg) - (1 - win_rate)) / risk_reward_avg
        
        If insufficient history, return default 0.05 (5% risk).
        """
        if len(self._trade_history) < 5:
            return 0.05  # default 5% when insufficient data
        
        recent_trades = self._trade_history[-self.kelly_lookback:]
        wins = [t for t in recent_trades if t['win']]
        win_rate = len(wins) / len(recent_trades) if recent_trades else 0.5
        
        if win_rate == 0:
            return 0.0
        
        avg_risk_reward = np.mean([t['risk_reward'] for t in recent_trades])
        if avg_risk_reward == 0:
            return 0.0
        
        kelly = (win_rate * (1 + avg_risk_reward) - (1 - win_rate)) / avg_risk_reward
        return max(0.0, min(kelly, 1.0))
    
    def update_trade_result(self, win: bool, risk_reward: float):
        """Call this after a trade closes to update Kelly calculation."""
        self._trade_history.append({
            'win': win,
            'risk_reward': risk_reward,
            'timestamp': datetime.now()
        })
        # Keep only recent history
        if len(self._trade_history) > self.kelly_lookback * 2:
            self._trade_history = self._trade_history[-self.kelly_lookback * 2:]
    
    def _calculate_rsi(self, prices: pd.Series, period: int = None) -> pd.Series:
        if period is None:
            period = self.rsi_period
        delta = prices.diff()
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        avg_gains = gains.rolling(window=period, min_periods=1).mean()
        avg_losses = losses.rolling(window=period, min_periods=1).mean()
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
    
    strategy = KellyPositionSizingStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT", account_balance=10000)
    
    # Simulate some trade results to see Kelly in action
    for i in range(10):
        strategy.update_trade_result(win=np.random.random() > 0.4, risk_reward=1.5)
    
    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    print(f"Current Kelly fraction: {strategy._calculate_kelly_fraction():.3f}")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Position size multiplier: {sig.position_size_multiplier:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")