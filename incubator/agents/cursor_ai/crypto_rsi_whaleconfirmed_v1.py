"""
Whale-Confirmed RSI Mean Reversion Strategy
==========================================

Created by: cursor_ai
Date: 2026-02-27

Strategy Logic:
- Entry when: RSI < 30 (oversold) AND whale accumulation confirmed
- Exit when: Take profit (2x ATR) or stop loss (1.5x ATR)
- Risk management: Dynamic position sizing with whale confidence weighting

Unique Value Proposition:
Combines classic RSI mean reversion with on-chain whale activity confirmation, providing a unique angle not present in existing strategies. This approach filters out false RSI signals by requiring whale accumulation confirmation, reducing false positives and improving win rate.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

# Mock data_bridge for testing (replace with actual implementation)
class DataBridge:
    @staticmethod
    def get_whale_data(symbol: str) -> Dict:
        """Mock whale data - replace with actual on-chain data source"""
        np.random.seed(hash(symbol) % 1000)
        return {
            'recent_trade_volume': np.random.uniform(0.1, 5.0),  # BTC
            'net_long_position': np.random.uniform(-0.8, 0.8),
            'net_short_position': np.random.uniform(-0.8, 0.8),
            'whale_probability': np.random.uniform(0.3, 0.9)
        }

@dataclass
class Signal:
    """A trading signal - required return type."""
    symbol: str           # e.g., "BTCUSDT"
    direction: str        # "BUY" or "SELL"
    confidence: float     # 0.0 to 1.0
    entry_price: float    # Suggested entry
    take_profit: float    # Target price
    stop_loss: float      # Stop price
    reason: str           # Why this signal

class WhaleConfirmedRSIStrategy:
    """
    Whale-Confirmed RSI Mean Reversion Strategy
    
    Logic:
    - Buy when RSI < 30 (oversold) AND whale accumulation detected
    - Sell when RSI > 70 (overbought) AND whale distribution detected
    - Use ATR for dynamic stop loss placement
    - Whale confidence weights signal strength
    """
    
    def __init__(self, params: Optional[Dict] = None):
        """
        Initialize with parameters.
        
        Args:
            params: Dictionary with keys like 'rsi_period', 'oversold', etc.
        """
        self.params = params or {}
        self.rsi_period = self.params.get('rsi_period', 14)
        self.oversold = self.params.get('oversold', 30)
        self.overbought = self.params.get('overbought', 70)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.0)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.5)
        self.whale_threshold = self.params.get('whale_threshold', 0.5)  # BTC
        self.data_bridge = DataBridge()
    
    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        """
        Main method - called by backtest engine.
        
        Args:
            data: DataFrame with columns [open, high, low, close, volume]
            symbol: Trading pair being analyzed
            
        Returns:
            List of Signal objects (empty if no signal)
        """
        if len(data) < self.rsi_period + 10:
            return []  # Not enough data
        
        # Calculate indicators
        rsi = self._calculate_rsi(data['close'])
        atr = self._calculate_atr(data)
        whale_signals = self._analyze_whale_activity(symbol)
        
        current_price = data['close'].iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_atr = atr.iloc[-1]
        
        signals = []
        
        # Check for oversold (buy signal with whale confirmation)
        if current_rsi < self.oversold and whale_signals['accumulation']:
            direction = "BUY"
            base_confidence = (self.oversold - current_rsi) / self.oversold
            base_confidence = min(base_confidence, 0.95)
            
            # Whale confidence weighting
            confidence = base_confidence + (whale_signals['confidence'] * 0.5)
            confidence = min(confidence, 0.95)
            
            tp = current_price + (current_atr * self.tp_atr_mult)
            sl = current_price - (current_atr * self.sl_atr_mult)
            
            signals.append(Signal(
                symbol=symbol,
                direction=direction,
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"RSI oversold ({current_rsi:.1f} < {self.oversold}) + Whale accumulation ({whale_signals['confidence']:.2f})"
            ))
        
        # Check for overbought (sell signal with whale confirmation)
        elif current_rsi > self.overbought and whale_signals['distribution']:
            direction = "SELL"
            base_confidence = (current_rsi - self.overbought) / (100 - self.overbought)
            base_confidence = min(base_confidence, 0.95)
            
            # Whale confidence weighting
            confidence = base_confidence + (whale_signals['confidence'] * 0.5)
            confidence = min(confidence, 0.95)
            
            tp = current_price - (current_atr * self.tp_atr_mult)
            sl = current_price + (current_atr * self.sl_atr_mult)
            
            signals.append(Signal(
                symbol=symbol,
                direction=direction,
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"RSI overbought ({current_rsi:.1f} > {self.overbought}) + Whale distribution ({whale_signals['confidence']:.2f})"
            ))
        
        return signals
    
    def _calculate_rsi(self, prices: pd.Series) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = prices.diff()
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        avg_gains = gains.rolling(window=self.rsi_period, min_periods=1).mean()
        avg_losses = losses.rolling(window=self.rsi_period, min_periods=1).mean()
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_atr(self, data: pd.DataFrame) -> pd.Series:
        """Calculate Average True Range."""
        high = data['high']
        low = data['low']
        close = data['close']
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=self.atr_period, min_periods=1).mean()
        return atr
    
    def _analyze_whale_activity(self, symbol: str) -> Dict:
        """Analyzes whale activity from on-chain data."""
        whale_data = self.data_bridge.get_whale_data(symbol)
        
        # Determine accumulation vs distribution
        accumulation = whale_data['net_long_position'] > 0.2
        distribution = whale_data['net_short_position'] > 0.2
        
        # Whale confidence based on volume and probability
        whale_confidence = whale_data['whale_probability'] if whale_data['recent_trade_volume'] > self.whale_threshold else 0
        
        return {
            'accumulation': accumulation,
            'distribution': distribution,
            'confidence': whale_confidence
        }

# ==============================================================================
# TESTING - Required: Verify your strategy works
# ==============================================================================

if __name__ == "__main__":
    """Quick test with synthetic data."""
    
    # Create synthetic OHLCV data
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
    
    # Test strategy
    strategy = WhaleConfirmedRSIStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")
    
    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
        print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")