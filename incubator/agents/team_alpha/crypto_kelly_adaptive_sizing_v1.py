"""
Kelly Criterion Adaptive Sizing Strategy - Baby Strat
======================================================

Created by: team_alpha
Date: 2026-02-26

Strategy Logic:
- Base strategy: RSI mean reversion
- Dynamic position sizing using Kelly Criterion
- Tracks recent performance to adjust size
- Preserves capital during drawdowns, compounds during wins

Unique Value Proposition:
This is a RISK MANAGEMENT overlay that can be applied to ANY base strategy.
Unlike fixed position sizing, it uses Kelly Criterion for mathematically
optimal position sizes based on recent edge and win rate.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from collections import deque


@dataclass
class Signal:
    """A trading signal with Kelly-adjusted sizing."""
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str
    position_size_mult: float = 1.0  # Kelly-adjusted multiplier
    kelly_fraction: float = 0.0  # Raw Kelly percentage


class KellyAdaptiveSizingStrategy:
    """
    Kelly Criterion Adaptive Position Sizing Strategy.
    
    Uses Kelly formula to dynamically adjust position sizes:
    f* = (W * B - (1 - W)) / B
    Where W = win rate, B = avg_win/avg_loss ratio
    
    This is a RISK MANAGEMENT overlay - can wrap any base strategy.
    """
    
    def __init__(self, params: Optional[Dict] = None):
        """
        Initialize with parameters.
        
        Args:
            params: Dict with strategy parameters
        """
        self.params = params or {}
        
        # Base strategy params (RSI mean reversion)
        self.base_rsi_period = self.params.get('base_rsi_period', 14)
        self.base_oversold = self.params.get('base_oversold', 30)
        self.base_overbought = self.params.get('base_overbought', 70)
        self.base_tp_atr_mult = self.params.get('base_tp_atr_mult', 2.0)
        self.base_sl_atr_mult = self.params.get('base_sl_atr_mult', 1.5)
        
        # Kelly params
        self.kelly_lookback = self.params.get('kelly_lookback', 20)
        self.recent_lookback = self.params.get('recent_lookback', 5)
        self.kelly_fraction = self.params.get('kelly_fraction', 0.5)  # Half-Kelly
        self.max_kelly_mult = self.params.get('max_kelly_mult', 2.0)
        self.min_kelly_mult = self.params.get('min_kelly_mult', 0.25)
        
        # Track simulated trade history for Kelly calculation
        self.trade_history = deque(maxlen=self.kelly_lookback)
        self._init_trade_history()
    
    def _init_trade_history(self):
        """Initialize with simulated baseline performance (50% WR, 1:1 R/R)."""
        for _ in range(10):
            self.trade_history.append({'pnl_pct': 0.02, 'win': True})
            self.trade_history.append({'pnl_pct': -0.02, 'win': False})
    
    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        """
        Main signal generation method.
        
        Args:
            data: DataFrame with columns [open, high, low, close, volume]
            symbol: Trading pair
            
        Returns:
            List of Signal objects with Kelly-adjusted sizing
        """
        if len(data) < self.base_rsi_period + 10:
            return []
        
        # Calculate indicators
        rsi = self._calculate_rsi(data['close'], self.base_rsi_period)
        atr = self._calculate_atr(data, 14)
        
        current_price = data['close'].iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_atr = atr.iloc[-1]
        
        # Calculate Kelly-adjusted position size
        position_mult, kelly_pct = self._calculate_kelly_sizing()
        
        signals = []
        
        # RSI Oversold - Buy signal
        if current_rsi < self.base_oversold:
            direction = "BUY"
            confidence = min((self.base_oversold - current_rsi) / self.base_oversold, 0.95)
            
            tp = current_price + (current_atr * self.base_tp_atr_mult)
            sl = current_price - (current_atr * self.base_sl_atr_mult)
            
            signals.append(Signal(
                symbol=symbol,
                direction=direction,
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"RSI oversold ({current_rsi:.1f}) with Kelly sizing: {position_mult:.2f}x (f*={kelly_pct:.1%})",
                position_size_mult=round(position_mult, 3),
                kelly_fraction=round(kelly_pct, 4)
            ))
        
        # RSI Overbought - Sell signal
        elif current_rsi > self.base_overbought:
            direction = "SELL"
            confidence = min((current_rsi - self.base_overbought) / (100 - self.base_overbought), 0.95)
            
            tp = current_price - (current_atr * self.base_tp_atr_mult)
            sl = current_price + (current_atr * self.base_sl_atr_mult)
            
            signals.append(Signal(
                symbol=symbol,
                direction=direction,
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"RSI overbought ({current_rsi:.1f}) with Kelly sizing: {position_mult:.2f}x (f*={kelly_pct:.1%})",
                position_size_mult=round(position_mult, 3),
                kelly_fraction=round(kelly_pct, 4)
            ))
        
        return signals
    
    def _calculate_kelly_sizing(self) -> Tuple[float, float]:
        """
        Calculate Kelly Criterion position sizing multiplier.
        
        Returns:
            Tuple of (position_multiplier, raw_kelly_percentage)
        """
        if len(self.trade_history) < 5:
            return 1.0, 0.0
        
        # Calculate win rate (W)
        wins = sum(1 for t in self.trade_history if t['win'])
        win_rate = wins / len(self.trade_history)
        
        # Calculate edge ratio (B) = avg_win / avg_loss
        winning_trades = [t['pnl_pct'] for t in self.trade_history if t['win'] and t['pnl_pct'] > 0]
        losing_trades = [abs(t['pnl_pct']) for t in self.trade_history if not t['win'] and t['pnl_pct'] < 0]
        
        if not winning_trades or not losing_trades:
            return 1.0, 0.0
        
        avg_win = np.mean(winning_trades)
        avg_loss = np.mean(losing_trades)
        
        if avg_loss == 0:
            return self.max_kelly_mult, 1.0
        
        edge_ratio = avg_win / avg_loss
        
        # Kelly formula: f* = (W * B - (1 - W)) / B
        kelly_pct = (win_rate * edge_ratio - (1 - win_rate)) / edge_ratio
        kelly_pct = max(0, kelly_pct)  # Kelly can't be negative
        
        # Use Half-Kelly for safety (or configured fraction)
        adjusted_kelly = kelly_pct * self.kelly_fraction
        
        # Convert to position multiplier
        # Base position = 1.0, Kelly scales this
        position_mult = 1.0 + (adjusted_kelly * 2)  # Scale to 0.25x - 2x range
        position_mult = max(self.min_kelly_mult, min(self.max_kelly_mult, position_mult))
        
        # Check recent performance for regime adjustment
        recent_trades = list(self.trade_history)[-self.recent_lookback:]
        if recent_trades:
            recent_wins = sum(1 for t in recent_trades if t['win'])
            recent_wr = recent_wins / len(recent_trades)
            
            # Reduce size if recent performance is poor
            if recent_wr < 0.3:
                position_mult *= 0.5  # Quarter-Kelly
            # Allow up to full Kelly if recent performance is strong
            elif recent_wr > 0.7:
                position_mult = min(position_mult * 1.5, self.max_kelly_mult)
        
        return position_mult, kelly_pct
    
    def update_trade_result(self, pnl_pct: float):
        """
        Update trade history with result (call after trade closes).
        This would be used by the backtest engine.
        """
        self.trade_history.append({
            'pnl_pct': pnl_pct,
            'win': pnl_pct > 0,
            'timestamp': datetime.now()
        })
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = prices.diff()
        gains = delta.where(delta > 0, 0)
        losses = (-delta.where(delta < 0, 0))
        avg_gains = gains.rolling(window=period, min_periods=1).mean()
        avg_losses = losses.rolling(window=period, min_periods=1).mean()
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
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
    """Quick test with sample data and Kelly sizing demonstration."""
    np.random.seed(42)
    n = 200
    returns = np.random.normal(0.001, 0.02, n)
    prices = 50000 * np.exp(np.cumsum(returns))
    
    sample_data = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.001, n)),
        'high': prices * (1 + abs(np.random.normal(0, 0.01, n))),
        'low': prices * (1 - abs(np.random.normal(0, 0.01, n))),
        'close': prices,
        'volume': np.random.uniform(100, 1000, n)
    })
    
    strategy = KellyAdaptiveSizingStrategy()
    
    # Simulate different performance regimes
    print("=" * 60)
    print("KELLY ADAPTIVE SIZING STRATEGY - TEST")
    print("=" * 60)
    
    # Scenario 1: Baseline (50% WR, 1:1 R/R)
    print("\n1. BASELINE PERFORMANCE (50% WR, 1:1 R/R)")
    mult, kelly = strategy._calculate_kelly_sizing()
    print(f"   Kelly %: {kelly:.1%} | Position Multiplier: {mult:.2f}x")
    
    # Scenario 2: Strong performance (70% WR, 2:1 R/R)
    print("\n2. STRONG PERFORMANCE (70% WR, 2:1 R/R)")
    strategy.trade_history.clear()
    for _ in range(14):
        strategy.trade_history.append({'pnl_pct': 0.04, 'win': True})
    for _ in range(6):
        strategy.trade_history.append({'pnl_pct': -0.02, 'win': False})
    mult, kelly = strategy._calculate_kelly_sizing()
    print(f"   Kelly %: {kelly:.1%} | Position Multiplier: {mult:.2f}x")
    
    # Scenario 3: Poor performance (30% WR, 1:1 R/R)
    print("\n3. POOR PERFORMANCE (30% WR, 1:1 R/R)")
    strategy.trade_history.clear()
    for _ in range(6):
        strategy.trade_history.append({'pnl_pct': 0.02, 'win': True})
    for _ in range(14):
        strategy.trade_history.append({'pnl_pct': -0.02, 'win': False})
    mult, kelly = strategy._calculate_kelly_sizing()
    print(f"   Kelly %: {kelly:.1%} | Position Multiplier: {mult:.2f}x")
    
    # Generate signals
    print("\n" + "=" * 60)
    print("SIGNAL GENERATION")
    print("=" * 60)
    
    # Reset to strong performance
    strategy.trade_history.clear()
    for _ in range(14):
        strategy.trade_history.append({'pnl_pct': 0.04, 'win': True})
    for _ in range(6):
        strategy.trade_history.append({'pnl_pct': -0.02, 'win': False})
    
    signals = strategy.generate_signals(sample_data, symbol="BTCUSDT")
    
    print(f"\nGenerated {len(signals)} signals from {len(sample_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Position Size: {sig.position_size_mult:.2f}x base")
        print(f"  Kelly Fraction: {sig.kelly_fraction:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
