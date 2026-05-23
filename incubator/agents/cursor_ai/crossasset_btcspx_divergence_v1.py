"""
Cross-Asset BTC-SPX Divergence Strategy
=======================================

Created by: cursor_ai
Date: 2026-02-27

Strategy Logic:
- Entry when: BTC price shows divergence from SPX (correlation breaks) AND VIX > 25 (fear regime) AND BTC > 200-day SMA
- Exit when: Correlation re-establishes (30-day rolling correlation returns to normal) OR VIX drops below 20
- Risk management: 2x ATR stop, 3x ATR target

Unique Value Proposition:
Captures periods where BTC decouples from traditional market risk sentiment (SPX). During fear regimes (high VIX), this divergence often precedes crypto rallies as institutional money rotates into BTC as a hedge. This cross-asset strategy is underexplored in the current inventory.
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

class CrossAssetBTCSPXDivergenceStrategy:
    """BTC-SPX divergence with VIX regime filter."""
    
    def __init__(self, params: Optional[dict] = None):
        self.p = params or {}
        self.correlation_period = self.p.get('correlation_period', 30)
        self.correlation_threshold = self.p.get('correlation_threshold', 0.3)  # below this = divergence
        self.vix_high_threshold = self.p.get('vix_high_threshold', 25)
        self.vix_low_threshold = self.p.get('vix_low_threshold', 20)
        self.ma_period = self.p.get('ma_period', 200)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr_mult = self.p.get('tp_atr_mult', 3.0)
        self.sl_atr_mult = self.p.get('sl_atr_mult', 2.0)
    
    def generate_signals(
        self,
        btc_data: pd.DataFrame,
        spx_data: pd.DataFrame,
        vix_data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(btc_data) < self.correlation_period + 10:
            return []
        
        # Calculate rolling correlation
        btc_returns = btc_data['close'].pct_change()
        spx_returns = spx_data['close'].pct_change()
        correlation = btc_returns.rolling(self.correlation_period).corr(spx_returns)
        current_corr = correlation.iloc[-1]
        
        # VIX regime
        current_vix = vix_data['close'].iloc[-1]
        vix_fear = current_vix > self.vix_high_threshold
        vix_calm = current_vix < self.vix_low_threshold
        
        # BTC trend filter
        btc_ma = btc_data['close'].rolling(self.ma_period).mean()
        current_price = btc_data['close'].iloc[-1]
        above_ma = current_price > btc_ma.iloc[-1]
        
        # ATR for risk
        atr = self._calculate_atr(btc_data)
        current_atr = atr.iloc[-1]
        
        signals = []
        
        # Entry: Low/negative correlation + high VIX + BTC above long MA
        if (abs(current_corr) < self.correlation_threshold and 
            vix_fear and 
            above_ma):
            
            confidence = 0.6 + (self.correlation_threshold - abs(current_corr)) * 2
            confidence = min(confidence, 0.85)
            
            tp = current_price + (current_atr * self.tp_atr_mult)
            sl = current_price - (current_atr * self.sl_atr_mult)
            
            direction = "BUY"  # Typically BTC decoupling in fear regime = bullish
            signals.append(Signal(
                symbol=symbol,
                direction=direction,
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"BTC-SPX correlation {current_corr:.2f} (decoupled) + VIX {current_vix:.1f} > {self.vix_high_threshold}"
            ))
        
        # Exit: Correlation returns OR VIX calms
        elif (abs(current_corr) >= self.correlation_threshold or vix_calm):
            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=0.5,
                entry_price=round(current_price, 2),
                take_profit=round(current_price - (current_atr * self.tp_atr_mult), 2),
                stop_loss=round(current_price + (current_atr * self.sl_atr_mult), 2),
                reason=f"Correlation {current_corr:.2f} restored or VIX {current_vix:.1f} < {self.vix_low_threshold}"
            ))
        
        return signals
    
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
    n = 200
    # BTC data
    btc_prices = 50000 * np.exp(np.cumsum(np.random.normal(0.0001, 0.02, n)))
    btc = pd.DataFrame({
        'open': btc_prices * (1 + np.random.normal(0, 0.001, n)),
        'high': btc_prices * (1 + abs(np.random.normal(0, 0.01, n))),
        'low': btc_prices * (1 - abs(np.random.normal(0, 0.01, n))),
        'close': btc_prices,
        'volume': np.random.uniform(100, 1000, n)
    })
    
    # SPX data (less volatile, trending)
    spx_prices = 4000 * np.exp(np.cumsum(np.random.normal(0.00005, 0.01, n)))
    spx = pd.DataFrame({
        'close': spx_prices,
        'high': spx_prices * 1.005,
        'low': spx_prices * 0.995,
        'volume': np.random.uniform(1000, 5000, n)
    })
    
    # VIX data (mean-reverting around 20)
    vix = pd.DataFrame({
        'close': 20 + np.random.randn(n).cumsum() * 0.5 + 10
    })
    
    strategy = CrossAssetBTCSPXDivergenceStrategy()
    signals = strategy.generate_signals(btc, spx, vix, "BTCUSDT")
    
    print(f"Generated {len(signals)} signals")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")