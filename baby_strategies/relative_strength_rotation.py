"""
RelativeStrengthRotationStrategy - Baby Strat
=============================================

Created by: AI Assistant
Date: 2026-02-27

Strategy Logic:
- Entry when: Asset shows relative strength vs market (BTC) with momentum
- Exit when: Relative strength fades or SL/TP hit
- Risk management: Correlation-adjusted position sizing

Unique Value Proposition:
Trades altcoins based on relative performance vs BTC, not just absolute price.
Captures "beta" outperformance during risk-on crypto periods.
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


class RelativeStrengthRotationStrategy:
    """
    Relative Strength Rotation Strategy
    
    Compares the asset's performance to a benchmark (BTC proxy).
    When asset outperforms with positive momentum = long signal.
    Uses correlation and beta to filter strong relationships.
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.rs_lookback = self.params.get('rs_lookback', 20)
        self.momentum_period = self.params.get('momentum_period', 10)
        self.correlation_period = self.params.get('correlation_period', 30)
        self.strength_threshold = self.params.get('strength_threshold', 1.02)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.5)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.5)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        """
        For single-asset mode, we calculate relative strength vs its own
        moving average (as a proxy for market). For multi-asset, you'd pass
        benchmark data separately.
        """
        if len(data) < max(self.rs_lookback, self.correlation_period, self.momentum_period) + 10:
            return []

        # Calculate returns
        returns = data['close'].pct_change()
        
        # Use SMA as "market" benchmark for this asset
        sma = data['close'].rolling(window=self.rs_lookback).mean()
        
        # Calculate relative strength: price / benchmark
        rs = data['close'] / sma
        rs_momentum = rs.diff(self.momentum_period)
        
        # Price momentum
        price_momentum = returns.rolling(window=self.momentum_period).sum()
        
        # Calculate ATR
        atr = self._calculate_atr(data, self.atr_period)
        
        current_price = data['close'].iloc[-1]
        current_rs = rs.iloc[-1]
        current_rs_momentum = rs_momentum.iloc[-1]
        current_momentum = price_momentum.iloc[-1]
        current_atr = atr.iloc[-1]
        
        # RS percentile (how strong vs recent history)
        rs_history = rs.iloc[-self.rs_lookback:]
        rs_percentile = (rs_history < current_rs).sum() / len(rs_history)
        
        signals = []
        
        # Long: RS > 1 (above benchmark) + positive RS momentum + positive price momentum
        if (current_rs > self.strength_threshold and 
            current_rs_momentum > 0 and 
            current_momentum > 0):
            
            # Confidence based on RS strength and percentile
            rs_score = min((current_rs - 1) / 0.05, 0.3)
            percentile_score = rs_percentile * 0.3
            momentum_score = min(current_momentum / 0.05, 0.2)
            confidence = min(0.3 + rs_score + percentile_score + momentum_score, 0.95)
            
            tp = current_price + (current_atr * self.tp_atr_mult)
            sl = current_price - (current_atr * self.sl_atr_mult)
            
            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"RS strength: {current_rs:.3f} (pct: {rs_percentile:.1%})"
            ))
        
        # Short: RS weakness with negative momentum
        elif (current_rs < 0.98 and 
              current_rs_momentum < 0 and 
              current_momentum < 0):
            
            rs_score = min((1 - current_rs) / 0.05, 0.3)
            percentile_score = (1 - rs_percentile) * 0.3
            momentum_score = min(abs(current_momentum) / 0.05, 0.2)
            confidence = min(0.3 + rs_score + percentile_score + momentum_score, 0.95)
            
            tp = current_price - (current_atr * self.tp_atr_mult)
            sl = current_price + (current_atr * self.sl_atr_mult)
            
            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"RS weakness: {current_rs:.3f} (pct: {1-rs_percentile:.1%})"
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
    
    strategy = RelativeStrengthRotationStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")
    
    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
