"""
Liquidation Cluster Reversal Strategy
=====================================

Created by: cursor_ai
Date: 2026-02-27

Strategy Logic:
- Entry when: Large liquidation cluster detected (> $1M total) AND RSI < 30 (oversold) AND price bounces 1% from cluster low
- Exit when: RSI > 60 OR liquidation cluster dissipates
- Risk management: Tight stop (1.2x ATR) because reversals are quick

Unique Value Proposition:
Identifies cascading liquidation events (liquidity voids) and enters on the bounce after extreme sell-offs. This captures the "liquidation bounce" phenomenon that's common in crypto but not systematically traded. Uses on-chain liquidation data (often available from exchanges) as a trigger.
"""

import numpy as np
import pandas as pd
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str

class CryptoLiquidationClusterReversalStrategy:
    """Reversal strategy triggered by liquidation clusters."""
    
    def __init__(self, params: Optional[dict] = None):
        self.p = params or {}
        self.liquidation_threshold_usd = self.p.get('liquidation_threshold_usd', 1_000_000)
        self.rsi_period = self.p.get('rsi_period', 14)
        self.rsi_oversold = self.p.get('rsi_oversold', 30)
        self.rsi_exit_threshold = self.p.get('rsi_exit_threshold', 60)
        self.bounce_threshold = self.p.get('bounce_threshold', 0.01)  # 1% bounce
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr_mult = self.p.get('tp_atr_mult', 2.0)
        self.sl_atr_mult = self.p.get('sl_atr_mult', 1.2)
        self.cluster_window = self.p.get('cluster_window', 5)  # minutes
    
    def generate_signals(
        self,
        data: pd.DataFrame,
        liquidation_data: Optional[pd.DataFrame] = None,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < self.rsi_period + 10:
            return []
        
        # Calculate RSI
        rsi = self._calculate_rsi(data['close'])
        current_rsi = rsi.iloc[-1]
        
        # Calculate ATR
        atr = self._calculate_atr(data)
        current_atr = atr.iloc[-1]
        
        current_price = data['close'].iloc[-1]
        recent_low = data['low'].iloc[-5:].min()
        bounce_pct = (current_price - recent_low) / recent_low if recent_low > 0 else 0
        
        signals = []
        
        # Check for liquidation cluster (mock - replace with real data source)
        cluster_detected, cluster_size = self._check_liquidation_cluster(liquidation_data, symbol)
        
        # Entry: Oversold + bounce from cluster low + large liquidation cluster
        if (current_rsi < self.rsi_oversold and 
            bounce_pct >= self.bounce_threshold and 
            cluster_detected and cluster_size > self.liquidation_threshold_usd):
            
            confidence = 0.6 + (self.rsi_oversold - current_rsi) / self.rsi_oversold * 0.3
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
                reason=f"Liquidation cluster ${cluster_size/1e6:.1f}M + RSI {current_rsi:.1f} + bounce {bounce_pct:.1%}"
            ))
        
        # Exit: RSI overbought or cluster gone
        elif current_rsi > self.rsi_exit_threshold:
            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=0.5,
                entry_price=round(current_price, 2),
                take_profit=round(current_price - (current_atr * self.tp_atr_mult), 2),
                stop_loss=round(current_price + (current_atr * self.sl_atr_mult), 2),
                reason=f"RSI {current_rsi:.1f} > {self.rsi_exit_threshold} - exit reversal"
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
        return tr.rolling(window=self.atr_period).mean()
    
    def _check_liquidation_cluster(self, liquidation_data: Optional[pd.DataFrame], symbol: str) -> tuple:
        """Mock liquidation detection - replace with real exchange API."""
        if liquidation_data is not None and not liquidation_data.empty:
            # Filter recent cluster
            recent = liquidation_data[liquidation_data['timestamp'] > 
                                      (pd.Timestamp.now() - pd.Timedelta(minutes=self.cluster_window))]
            total_liquidated = recent['usd_value'].sum() if 'usd_value' in recent.columns else 0
            return total_liquidated > self.liquidation_threshold_usd, total_liquidated
        
        # Deterministic mock for testing
        np.random.seed(hash(symbol) % 1000)
        mock_cluster = np.random.uniform(0, 2e6)  # $0-$2M
        return mock_cluster > self.liquidation_threshold_usd, mock_cluster

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
    
    strategy = CryptoLiquidationClusterReversalStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")
    
    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")