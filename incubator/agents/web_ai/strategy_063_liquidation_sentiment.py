"""
Baby Strategy 063: Liquidation Sentiment Extreme

Contrarian strategy based on long/short liquidation ratio extremes.
When one side gets completely wiped out, the move is often overextended.

Category: Liquidation Strategies
Best for: Sentiment extremes and contrarian entries
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class Strategy063LiquidationSentiment:
    """
    Contrarian entries based on liquidation sentiment extremes.
    
    Logic:
    - Monitors ratio of long liquidations to short liquidations
    - When ratio hits extreme (one side dominated), expect reversal
    - Combines with price momentum exhaustion for confirmation
    """
    
    def __init__(self, params: Optional[dict] = None):
        self.p = params or {}
        self.extreme_ratio = self.p.get('extreme_ratio', 5.0)  # 5:1 liquidation ratio
        self.exhaustion_lookback = self.p.get('exhaustion_lookback', 5)
        self.tp_atr = self.p.get('tp_atr', 2.0)
        self.sl_atr = self.p.get('sl_atr', 1.5)
        self.lookback = self.p.get('lookback', 20)
        
    def generate_signals(self, data: pd.DataFrame, 
                        long_liq_data: Optional[pd.Series] = None,
                        short_liq_data: Optional[pd.Series] = None,
                        symbol: str = "BTCUSDT") -> List[Signal]:
        """
        Generate signals based on liquidation ratio extremes.
        
        Args:
            data: OHLCV price data
            long_liq_data: Series of long liquidation amounts
            short_liq_data: Series of short liquidation amounts
            symbol: Trading symbol
        """
        if len(data) < self.lookback + 10:
            return []
        
        # If no liquidation data provided, simulate from price action
        if long_liq_data is None or short_liq_data is None:
            long_liq_data, short_liq_data = self._estimate_liquidations(data)
        
        # Calculate liquidation ratio
        # Ratio > 1 means more long liquidations (price going down)
        # Ratio < 1 means more short liquidations (price going up)
        liq_ratio = long_liq_data / (short_liq_data + 1e-10)
        
        # ATR for position sizing
        atr = self._atr(data, self.lookback)
        current_atr = atr.iloc[-1]
        current_price = data['close'].iloc[-1]
        
        # Price momentum for exhaustion check
        price_change = data['close'].pct_change(self.exhaustion_lookback)
        
        signals = []
        
        # Extreme long liquidations (ratio very high) = potential bottom
        if liq_ratio.iloc[-1] > self.extreme_ratio:
            # Check for momentum exhaustion (price stopped falling)
            recent_low = data['low'].iloc[-self.exhaustion_lookback:].min()
            price_bounce = (current_price - recent_low) / recent_low
            
            # Need some bounce confirmation + RSI not oversold anymore
            if price_bounce > 0.005:  # At least 0.5% bounce
                confidence = min(0.5 + (liq_ratio.iloc[-1] / self.extreme_ratio - 1) * 0.1, 0.85)
                signals.append(Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 2),
                    entry_price=round(current_price, 2),
                    take_profit=round(current_price + current_atr * self.tp_atr, 2),
                    stop_loss=round(current_price - current_atr * self.sl_atr, 2),
                    reason=f"Long liq extreme {liq_ratio.iloc[-1]:.1f}:1, bounce {price_bounce*100:.1f}%"
                ))
        
        # Extreme short liquidations (ratio very low) = potential top
        elif liq_ratio.iloc[-1] < 1 / self.extreme_ratio:
            # Check for momentum exhaustion (price stopped rising)
            recent_high = data['high'].iloc[-self.exhaustion_lookback:].max()
            price_pullback = (recent_high - current_price) / recent_high
            
            if price_pullback > 0.005:
                confidence = min(0.5 + ((1 / liq_ratio.iloc[-1]) / self.extreme_ratio - 1) * 0.1, 0.85)
                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 2),
                    entry_price=round(current_price, 2),
                    take_profit=round(current_price - current_atr * self.tp_atr, 2),
                    stop_loss=round(current_price + current_atr * self.sl_atr, 2),
                    reason=f"Short liq extreme {1/liq_ratio.iloc[-1]:.1f}:1, pullback {price_pullback*100:.1f}%"
                ))
        
        return signals
    
    def _estimate_liquidations(self, data: pd.DataFrame) -> tuple:
        """Estimate liquidations from price action when real data unavailable."""
        # Down moves estimate long liquidations
        # Up moves estimate short liquidations
        returns = data['close'].pct_change()
        
        long_liq = pd.Series(0.0, index=data.index)
        short_liq = pd.Series(0.0, index=data.index)
        
        # Negative returns = long liquidations
        long_liq = returns.clip(upper=0).abs() * data.get('volume', pd.Series(1, index=data.index))
        # Positive returns = short liquidations  
        short_liq = returns.clip(lower=0) * data.get('volume', pd.Series(1, index=data.index))
        
        # Smooth slightly
        long_liq = long_liq.rolling(3).mean().fillna(0)
        short_liq = short_liq.rolling(3).mean().fillna(0)
        
        return long_liq, short_liq
    
    def _atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        high, low, close = data['high'], data['low'], data['close']
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(period).mean()


if __name__ == "__main__":
    # Test with synthetic liquidation data
    np.random.seed(42)
    n = 100
    base = 50000
    
    # Create price data with a drop
    returns = np.random.randn(n) * 0.005
    returns[40:45] = [-0.02, -0.03, -0.025, -0.015, -0.01]  # Drop
    returns[45:50] = [0.005, 0.008, 0.01, 0.008, 0.005]  # Bounce
    
    closes = base * (1 + np.cumsum(returns))
    opens = np.roll(closes, 1)
    opens[0] = base
    
    data = pd.DataFrame({
        'open': opens,
        'high': np.maximum(opens, closes) * 1.002,
        'low': np.minimum(opens, closes) * 0.998,
        'close': closes,
        'volume': np.random.randint(1000, 2000, n),
    })
    
    # Create extreme liquidation ratio during the drop
    long_liq = pd.Series(100.0, index=data.index)
    short_liq = pd.Series(100.0, index=data.index)
    long_liq.iloc[44] = 800  # Extreme long liquidations
    short_liq.iloc[44] = 50
    
    strategy = LiquidationSentimentExtremeStrategy()
    signals = strategy.generate_signals(data, long_liq, short_liq)
    print(f"Signals generated: {len(signals)}")
    for sig in signals:
        print(f"{sig.direction} {sig.symbol} @ {sig.entry_price} (conf: {sig.confidence}) - {sig.reason}")
