"""
On-Chain Exchange Flow Momentum Strategy
=========================================

Created by: cursor_ai
Date: 2026-02-27

Strategy Logic:
- Entry when: Net exchange flow (inflows - outflows) is negative (more withdrawals = bullish) AND RSI > 55 AND volume increasing
- Exit when: Net exchange flow turns positive (more inflows = bearish) OR RSI < 45
- Risk management: 2x ATR stop, 3x ATR target

Unique Value Proposition:
Uses on-chain exchange flow data (BTC moving on/off exchanges) as a smart money indicator. Net outflows suggest accumulation (bullish), while inflows suggest distribution (bearish). Combined with momentum, this creates a unique on-chain + technical hybrid strategy.
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

class OnChainExchangeFlowMomentumStrategy:
    """Momentum strategy enhanced with exchange flow signals."""
    
    def __init__(self, params: Optional[dict] = None):
        self.p = params or {}
        self.rsi_period = self.p.get('rsi_period', 14)
        self.rsi_entry_threshold = self.p.get('rsi_entry_threshold', 55)
        self.rsi_exit_threshold = self.p.get('rsi_exit_threshold', 45)
        self.flow_period = self.p.get('flow_period', 24)  # hours
        self.volume_period = self.p.get('volume_period', 20)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr_mult = self.p.get('tp_atr_mult', 3.0)
        self.sl_atr_mult = self.p.get('sl_atr_mult', 2.0)
    
    def generate_signals(
        self,
        data: pd.DataFrame,
        flow_data: Optional[pd.Series] = None,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < 30:
            return []
        
        # RSI
        rsi = self._calculate_rsi(data['close'])
        current_rsi = rsi.iloc[-1]
        
        # ATR
        atr = self._calculate_atr(data)
        current_atr = atr.iloc[-1]
        current_price = data['close'].iloc[-1]
        
        # Exchange flow (mock - replace with Glassnode/ blockchain API)
        net_flow = self._get_exchange_flow(flow_data)
        net_flow_recent = net_flow.iloc[-1] if len(net_flow) > 0 else 0
        
        # Volume trend
        volume_avg = data['volume'].rolling(self.volume_period).mean().iloc[-1]
        volume_increasing = data['volume'].iloc[-1] > volume_avg
        
        signals = []
        
        # Long: Negative net flow (outflows > inflows = accumulation) + RSI bullish + volume up
        if (net_flow_recent < 0 and 
            current_rsi > self.rsi_entry_threshold and
            volume_increasing):
            
            confidence = 0.5 + (abs(net_flow_recent) / 1000) * 0.3  # flow magnitude matters
            confidence = min(confidence, 0.85)
            
            tp = current_price + (current_atr * self.tp_atr_mult)
            sl = current_price - (current_atr * self.sl_atr_mult)
            
            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"Net exchange outflow {net_flow_recent:.1f} BTC + RSI {current_rsi:.1f} + volume up"
            ))
        
        # Exit: Flow turns positive or RSI drops
        elif (net_flow_recent > 0 or current_rsi < self.rsi_exit_threshold):
            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=0.5,
                entry_price=round(current_price, 2),
                take_profit=round(current_price - (current_atr * self.tp_atr_mult), 2),
                stop_loss=round(current_price + (current_atr * self.sl_atr_mult), 2),
                reason=f"Exchange flow {'inflow' if net_flow_recent > 0 else 'RSI exit'}"
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
    
    def _get_exchange_flow(self, flow_data: Optional[pd.Series]) -> pd.Series:
        """Mock exchange flow - replace with Glassnode API"""
        if flow_data is not None:
            return flow_data
        np.random.seed(44)
        return pd.Series(np.random.uniform(-500, 500, 100))  # BTC net flow

if __name__ == "__main__":
    np.random.seed(42)
    n = 200
    prices = 50000 * np.exp(np.cumsum(np.random.normal(0.0001, 0.02, n)))
    
    data = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.001, n)),
        'high': prices * (1 + abs(np.random.normal(0, 0.01, n))),
        'low': prices * (1 - abs(np.random.normal(0, 0.01, n))),
        'close': prices,
        'volume': np.random.uniform(100, 1000, n)
    })
    
    strategy = OnChainExchangeFlowMomentumStrategy()
    signals = strategy.generate_signals(data, symbol="BTCUSDT")
    
    print(f"Generated {len(signals)} signals")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")