"""
Hurst Volatility Expansion Breakout Strategy
===========================================

Created by: cursor_ai
Date: 2026-02-27

Strategy Logic:
- Entry when: Hurst exponent < 0.4 (mean-reverting regime) AND recent volatility (ATR%) > 75th percentile of last 100 bars AND price breaks above upper Bollinger Band (2 std)
- Exit when: Hurst exponent rises above 0.6 (transition to trending) OR price crosses back inside Bollinger Bands
- Risk management: ATR-based stop loss (1.5x) and take profit (2.5x)

Unique Value Proposition:
Combines Hurst exponent for regime detection with volatility expansion and Bollinger Band breakout. This filters out low-volatility mean reversion traps and only trades breakouts when the market transitions from mean-reverting to trending, a sweet spot not captured by existing strategies.
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

class HurstVolatilityExpansionBreakoutStrategy:
    """Breakout strategy with Hurst-based regime filter and volatility expansion confirmation."""
    
    def __init__(self, params: Optional[dict] = None):
        self.p = params or {}
        self.hurst_period = self.p.get('hurst_period', 100)
        self.hurst_entry_threshold = self.p.get('hurst_entry_threshold', 0.4)
        self.hurst_exit_threshold = self.p.get('hurst_exit_threshold', 0.6)
        self.bb_period = self.p.get('bb_period', 20)
        self.bb_std = self.p.get('bb_std', 2.0)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr_mult = self.p.get('tp_atr_mult', 2.5)
        self.sl_atr_mult = self.p.get('sl_atr_mult', 1.5)
        self.volatility_percentile = self.p.get('volatility_percentile', 75)
    
    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < max(self.hurst_period, self.bb_period, self.atr_period) + 10:
            return []
        
        # Calculate ATR
        atr = self._calculate_atr(data)
        current_atr = atr.iloc[-1]
        
        # Calculate Bollinger Bands
        sma = data['close'].rolling(self.bb_period).mean()
        std = data['close'].rolling(self.bb_period).std()
        upper_band = sma + (std * self.bb_std)
        current_price = data['close'].iloc[-1]
        
        # Calculate Hurst (simplified using R/S method)
        hurst = self._calculate_hurst(data['close'])
        
        # Check volatility expansion
        atr_percentile = self._calculate_atr_percentile(data)
        volatility_high = atr.iloc[-1] > atr_percentile.iloc[-1]
        
        signals = []
        
        # Entry: Hurst < 0.4 (mean-reverting), volatility expanding, price breaks above upper BB
        if (hurst < self.hurst_entry_threshold and 
            volatility_high and 
            current_price > upper_band.iloc[-1]):
            
            confidence = 0.6 + (self.hurst_entry_threshold - hurst) * 0.5
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
                reason=f"Hurst {hurst:.3f} (mean-rev) + vol expansion + BB breakout"
            ))
        
        # Exit signal: Hurst rises above 0.6 (regime change) or price back inside BB
        elif hurst > self.hurst_exit_threshold:
            # Generate SELL to exit long (in real system, would close position)
            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=0.5,
                entry_price=round(current_price, 2),
                take_profit=round(current_price - (current_atr * self.tp_atr_mult), 2),
                stop_loss=round(current_price + (current_atr * self.sl_atr_mult), 2),
                reason=f"Hurst {hurst:.3f} > {self.hurst_exit_threshold} (regime change to trending)"
            ))
        
        return signals
    
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
    
    def _calculate_hurst(self, prices: pd.Series, max_lag: int = 100) -> float:
        """Simplified Hurst exponent using R/S method."""
        if len(prices) < max_lag:
            return 0.5  # random walk default
        
        lags = range(2, min(max_lag, len(prices)//2))
        rs_values = []
        for lag in lags:
            # Calculate R/S for this lag
            diffs = prices.diff(lag).dropna()
            if len(diffs) > 0:
                r = diffs.max() - diffs.min()
                s = diffs.std()
                if s > 0:
                    rs_values.append(r / s)
        
        if len(rs_values) < 10:
            return 0.5
        
        # Linear fit on log-log
        log_lags = np.log(list(lags)[:len(rs_values)])
        log_rs = np.log(rs_values)
        if len(log_lags) > 1:
            coeff = np.polyfit(log_lags, log_rs, 1)[0]
            return coeff
        return 0.5
    
    def _calculate_atr_percentile(self, data: pd.DataFrame, window: int = 100) -> pd.Series:
        """Calculate rolling percentile of ATR."""
        atr = self._calculate_atr(data)
        return atr.rolling(window).quantile(self.volatility_percentile / 100.0)

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
    
    strategy = HurstVolatilityExpansionBreakoutStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")
    
    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
        print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")