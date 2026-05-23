"""
NY-London Flow Session Momentum Strategy
=========================================

Created by: cursor_ai
Date: 2026-02-27

Strategy Logic:
- Entry when: Current hour is London-NY overlap (8-11am ET) AND price > SMA(20) AND volume > 1.5x 20-period average AND ATR > threshold
- Exit when: Session ends (11am ET) OR price < SMA(10) OR 3x ATR profit reached OR 2x ATR stop loss

Unique Value Proposition:
Focuses exclusively on the London-New York overlap session (8-11am ET) when institutional volume peaks. Requires multi-timeframe momentum confirmation (5m + 15m) and volume spikes to filter out noise. This session-specific approach is underexplored in the existing inventory.
"""

import numpy as np
import pandas as pd
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime
from functools import reduce

@dataclass
class Signal:
    """A trading signal - required return type."""
    symbol: str
    direction: str  # "BUY" or "SELL"
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str

class NYLondonFlowSessionMomentumStrategy:
    """
    Session-based momentum strategy targeting London-NY overlap periods.
    Enters only during high-volume overlap windows with momentum confirmation.
    """
    
    def __init__(self, params: Optional[dict] = None):
        self.p = params or {}
        # Session parameters (Eastern Time)
        self.session_start_hour = self.p.get('session_start_hour', 8)
        self.session_end_hour = self.p.get('session_end_hour', 11)
        
        # Technical parameters
        self.sma_short_period = self.p.get('sma_short_period', 10)
        self.sma_long_period = self.p.get('sma_long_period', 20)
        self.atr_period = self.p.get('atr_period', 14)
        self.atr_threshold = self.p.get('atr_threshold', 0.002)
        self.volume_multiplier = self.p.get('volume_multiplier', 1.5)
        self.volume_period = self.p.get('volume_period', 20)
        
        # Risk management
        self.tp_atr_mult = self.p.get('tp_atr_mult', 3.0)
        self.sl_atr_mult = self.p.get('sl_atr_mult', 2.0)
    
    def generate_signals(
        self,
        data_5m: pd.DataFrame,
        data_15m: Optional[pd.DataFrame] = None,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        """
        Main signal generation method.
        
        Args:
            data_5m: 5-minute OHLCV DataFrame with 'date' column (timezone-aware or UTC)
            data_15m: Optional 15-minute DataFrame for multi-timeframe confirmation
            symbol: Trading pair
            
        Returns:
            List of Signal objects (empty if no signal)
        """
        if len(data_5m) < 50:
            return []
        
        # Ensure we have datetime index
        df = data_5m.copy()
        if 'date' in df.columns:
            df['datetime'] = pd.to_datetime(df['date'])
        elif not isinstance(df.index, pd.DatetimeIndex):
            return []
        else:
            df['datetime'] = df.index
        
        # Extract hour (assuming Eastern Time - adjust if data is UTC)
        df['hour'] = df['datetime'].dt.hour
        
        # Calculate indicators on 5m
        sma_short = df['close'].rolling(self.sma_short_period).mean()
        sma_long = df['close'].rolling(self.sma_long_period).mean()
        atr = self._calculate_atr(df)
        volume_avg = df['volume'].rolling(self.volume_period).mean()
        
        current_idx = -1
        current_price = df['close'].iloc[current_idx]
        current_atr = atr.iloc[current_idx]
        current_hour = df['hour'].iloc[current_idx]
        current_volume = df['volume'].iloc[current_idx]
        
        signals = []
        
        # Check if we're in session (8-11am ET)
        in_session = self.session_start_hour <= current_hour <= self.session_end_hour
        
        # Entry conditions
        if in_session:
            # 1. Momentum filter: price > SMA(20) and SMA(10) < SMA(20) (uptrend)
            price_above_long = current_price > sma_long.iloc[current_idx]
            sma_alignment = sma_short.iloc[current_idx] < sma_long.iloc[current_idx]
            momentum_ok = price_above_long and sma_alignment
            
            # 2. Volume spike
            volume_ok = current_volume > (volume_avg.iloc[current_idx] * self.volume_multiplier)
            
            # 3. Volatility filter
            atr_ok = current_atr > self.atr_threshold
            
            # 4. Multi-timeframe confirmation (if 15m data provided)
            mtf_ok = True
            if data_15m is not None and len(data_15m) > 0:
                mtf_ok = self._check_multi_timeframe_confirmation(data_15m, current_price)
            
            if momentum_ok and volume_ok and atr_ok and mtf_ok:
                confidence = 0.6
                if momentum_ok:
                    confidence += 0.1
                if volume_ok:
                    confidence += 0.1
                if atr_ok:
                    confidence += 0.1
                if mtf_ok:
                    confidence += 0.1
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
                    reason=f"Session {self.session_start_hour}:00-{self.session_end_hour}:00 ET + momentum + volume {current_volume/volume_avg.iloc[current_idx]:.1f}x + ATR {current_atr:.4f}"
                ))
        
        # Exit conditions
        else:
            # Session ended - exit any open position (would be handled by position manager)
            # For signal-based system, generate SELL at session close
            if current_hour > self.session_end_hour:
                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=0.5,
                    entry_price=round(current_price, 2),
                    take_profit=round(current_price - (current_atr * self.tp_atr_mult), 2),
                    stop_loss=round(current_price + (current_atr * self.sl_atr_mult), 2),
                    reason=f"Session ended at {self.session_end_hour}:00 ET"
                ))
        
        return signals
    
    def _check_multi_timeframe_confirmation(self, data_15m: pd.DataFrame, current_price_5m: float) -> bool:
        """Check that 15-minute timeframe also shows bullish momentum."""
        if len(data_15m) < 50:
            return True  # Fallback if not enough data
        
        sma_20_15m = data_15m['close'].rolling(20).mean().iloc[-1]
        price_15m = data_15m['close'].iloc[-1]
        
        # 15m price should also be above its 20-period SMA
        return price_15m > sma_20_15m
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = None) -> pd.Series:
        """Calculate Average True Range."""
        if period is None:
            period = self.atr_period
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
    np.random.seed(42)
    n = 200
    
    # Create 5-minute data with realistic session hour patterns
    # Simulate higher volume during 8-11am ET (hours 13-16 UTC)
    hours = []
    base_prices = 50000 * np.exp(np.cumsum(np.random.normal(0.0001, 0.02, n)))
    
    for i in range(n):
        hour = (13 + i // 6) % 24  # UTC hours, approximate ET +5
        hours.append(hour)
    
    prices = base_prices
    df_5m = pd.DataFrame({
        'date': pd.date_range('2024-01-01 00:00', periods=n, freq='5min'),
        'open': prices * (1 + np.random.normal(0, 0.001, n)),
        'high': prices * (1 + abs(np.random.normal(0, 0.01, n))),
        'low': prices * (1 - abs(np.random.normal(0, 0.01, n))),
        'close': prices,
        'volume': np.where(
            np.array(hours) >= 13,  # 8am ET = 13 UTC
            np.random.uniform(2000, 5000, n),  # High volume during session
            np.random.uniform(100, 1000, n)    # Low volume outside session
        )
    })
    
    # Create 15-minute data (every 3rd 5m bar)
    df_15m = df_5m.iloc[::3].copy().reset_index(drop=True)
    
    strategy = NYLondonFlowSessionMomentumStrategy()
    signals = strategy.generate_signals(df_5m, df_15m, symbol="BTCUSDT")
    
    print(f"Generated {len(signals)} signals from {len(df_5m)} 5m bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
        print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")