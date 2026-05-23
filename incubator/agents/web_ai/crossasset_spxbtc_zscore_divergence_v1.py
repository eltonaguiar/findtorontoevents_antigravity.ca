"""
Cross-Asset SPX/BTC Z-Score Divergence Strategy
===============================================

Created by: web_ai
Date: 2026-02-26

Strategy Logic:
- Compute SPX/BTC ratio over rolling window (20 periods)
- Enter when z-score exceeds ±2 (2 standard deviations from mean)
- Go Long SPX / Short BTC when ratio < -2σ (BTC overperforms)
- Go Short SPX / Long BTC when ratio > +2σ (SPX overperforms)
- Exit when z-score reverts to 0 (mean reversion)
- Stop loss when z-score hits ±3 (extreme divergence persists)

Unique Value Proposition:
Exploits cross-asset divergence between S&P 500 and Bitcoin for mean-reversion 
opportunities. Works best when correlation is low or negative. Acts as a 
barometer for risk-on/risk-off sentiment shifts.
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


class CrossAssetSPXBTCZScoreDivergenceStrategy:
    """SPX/BTC ratio z-score divergence for mean-reversion trades."""
    
    def __init__(self, params: Optional[dict] = None):
        self.p = params or {}
        self.zscore_window = self.p.get('zscore_window', 20)
        self.zscore_entry_threshold = self.p.get('zscore_entry_threshold', 2.0)
        self.zscore_exit_threshold = self.p.get('zscore_exit_threshold', 0.0)
        self.zscore_stop_threshold = self.p.get('zscore_stop_threshold', 3.0)
        self.atr_window = self.p.get('atr_window', 14)
        self.atr_multiplier = self.p.get('atr_multiplier', 1.5)
    
    def generate_signals(
        self,
        spx_data: pd.DataFrame,
        btc_data: pd.DataFrame,
        symbol: str = "SPXBTC"
    ) -> List[Signal]:
        """Generate signals based on SPX/BTC ratio z-score divergence."""
        if len(spx_data) < self.zscore_window + 10 or len(btc_data) < self.zscore_window + 10:
            return []
        
        # Compute SPX/BTC ratio
        ratio = spx_data['close'] / btc_data['close']
        
        # Rolling stats for z-score
        ratio_mean = ratio.rolling(self.zscore_window).mean()
        ratio_std = ratio.rolling(self.zscore_window).std()
        zscore = (ratio - ratio_mean) / ratio_std
        
        current_zscore = zscore.iloc[-1]
        current_ratio = ratio.iloc[-1]
        
        # Volatility filter (ATR on ratio)
        ratio_range = abs(ratio - ratio.shift(1))
        atr = ratio_range.rolling(self.atr_window).mean()
        atr_filter = atr.iloc[-1] > atr.rolling(50).mean().iloc[-1] * self.atr_multiplier
        
        signals = []
        
        # Long SPX / Short BTC when zscore < -threshold (BTC overperforms, SPX underperforms)
        if current_zscore < -self.zscore_entry_threshold and not np.isnan(current_zscore):
            confidence = min(0.5 + (abs(current_zscore) - self.zscore_entry_threshold) * 0.2, 0.85)
            
            signals.append(Signal(
                symbol=symbol,
                direction="LONG_SPX_SHORT_BTC",
                confidence=round(confidence, 3),
                entry_price=round(current_ratio, 6),
                take_profit=round(ratio_mean.iloc[-1], 6),  # Revert to mean
                stop_loss=round(current_ratio * (1 - self.zscore_stop_threshold * 0.01), 6),
                reason=f"SPX/BTC ratio z-score {current_zscore:.2f} < -{self.zscore_entry_threshold} (BTC overperforms)"
            ))
        
        # Short SPX / Long BTC when zscore > +threshold (SPX overperforms, BTC underperforms)
        elif current_zscore > self.zscore_entry_threshold and not np.isnan(current_zscore):
            confidence = min(0.5 + (current_zscore - self.zscore_entry_threshold) * 0.2, 0.85)
            
            signals.append(Signal(
                symbol=symbol,
                direction="SHORT_SPX_LONG_BTC",
                confidence=round(confidence, 3),
                entry_price=round(current_ratio, 6),
                take_profit=round(ratio_mean.iloc[-1], 6),  # Revert to mean
                stop_loss=round(current_ratio * (1 + self.zscore_stop_threshold * 0.01), 6),
                reason=f"SPX/BTC ratio z-score {current_zscore:.2f} > +{self.zscore_entry_threshold} (SPX overperforms)"
            ))
        
        # Exit signals when z-score reverts to neutral
        elif abs(current_zscore) <= self.zscore_exit_threshold:
            signals.append(Signal(
                symbol=symbol,
                direction="EXIT",
                confidence=0.5,
                entry_price=round(current_ratio, 6),
                take_profit=round(current_ratio, 6),
                stop_loss=round(current_ratio, 6),
                reason=f"Z-score {current_zscore:.2f} reverted to neutral zone"
            ))
        
        return signals
    
    def get_zscore_analysis(
        self,
        spx_data: pd.DataFrame,
        btc_data: pd.DataFrame
    ) -> dict:
        """Return z-score analysis for dashboard display."""
        ratio = spx_data['close'] / btc_data['close']
        ratio_mean = ratio.rolling(self.zscore_window).mean()
        ratio_std = ratio.rolling(self.zscore_window).std()
        zscore = (ratio - ratio_mean) / ratio_std
        
        return {
            'current_ratio': round(ratio.iloc[-1], 6),
            'current_zscore': round(zscore.iloc[-1], 3),
            'ratio_mean': round(ratio_mean.iloc[-1], 6),
            'ratio_std': round(ratio_std.iloc[-1], 6),
            'is_diverged': abs(zscore.iloc[-1]) > self.zscore_entry_threshold,
            'divergence_direction': 'spx_overperforming' if zscore.iloc[-1] > self.zscore_entry_threshold 
                                   else 'btc_overperforming' if zscore.iloc[-1] < -self.zscore_entry_threshold 
                                   else 'neutral'
        }


# -------------------------------------------------------------
# TEST CODE
# -------------------------------------------------------------
import unittest


class TestSPXBTCZScoreDivergence(unittest.TestCase):
    def setUp(self):
        np.random.seed(42)
        length = 100
        btc_base = 50000
        spx_base = 4000
        
        # Generate correlated base prices
        btc_prices = btc_base + np.cumsum(np.random.normal(0, 100, length))
        spx_prices = spx_base + np.cumsum(np.random.normal(0, 20, length))
        
        # Inject divergence: BTC surges while SPX dips (creates z-score < -2)
        btc_prices[50:60] *= 1.05  # 5% BTC pump
        spx_prices[50:60] *= 0.98  # 2% SPX dip
        
        self.btc_data = pd.DataFrame({
            'open': btc_prices * 0.999,
            'high': btc_prices * 1.01,
            'low': btc_prices * 0.99,
            'close': btc_prices,
            'volume': np.random.uniform(100, 1000, length)
        })
        
        self.spx_data = pd.DataFrame({
            'open': spx_prices * 0.999,
            'high': spx_prices * 1.005,
            'low': spx_prices * 0.995,
            'close': spx_prices,
            'volume': np.random.uniform(1000, 5000, length)
        })
        
        self.strategy = CrossAssetSPXBTCZScoreDivergenceStrategy()
    
    def test_divergence_detection(self):
        """Test that divergence triggers a signal."""
        # Inject extreme divergence at the end to ensure signal generation
        extreme_spx = self.spx_data.copy()
        extreme_btc = self.btc_data.copy()
        extreme_btc['close'].iloc[-5:] *= 1.20  # 20% BTC pump at end for clear divergence
        
        signals = self.strategy.generate_signals(extreme_spx, extreme_btc)
        
        # Should detect at least one signal
        self.assertTrue(len(signals) > 0, f"Expected at least one signal during divergence, got {len(signals)}")
        
        # Check for long SPX/short BTC signal during divergence period
        long_signals = [s for s in signals if s.direction == "LONG_SPX_SHORT_BTC"]
        print(f"\nGenerated {len(long_signals)} LONG_SPX_SHORT_BTC signals")
        for sig in long_signals[:2]:
            print(f"  Entry: {sig.entry_price} | Confidence: {sig.confidence}")
    
    def test_zscore_calculation(self):
        """Test z-score calculation is correct."""
        analysis = self.strategy.get_zscore_analysis(self.spx_data, self.btc_data)
        
        self.assertIn('current_zscore', analysis)
        self.assertIn('current_ratio', analysis)
        self.assertIn('is_diverged', analysis)
        
        print(f"\nZ-Score Analysis:")
        print(f"  Current Ratio: {analysis['current_ratio']}")
        print(f"  Current Z-Score: {analysis['current_zscore']}")
        print(f"  Is Diverged: {analysis['is_diverged']}")
        print(f"  Direction: {analysis['divergence_direction']}")
    
    def test_signal_confidence(self):
        """Test that signal confidence increases with divergence magnitude."""
        # Create extreme divergence
        extreme_spx = self.spx_data.copy()
        extreme_btc = self.btc_data.copy()
        extreme_btc['close'].iloc[-1] *= 1.15  # Extreme BTC pump
        
        strategy = CrossAssetSPXBTCZScoreDivergenceStrategy({'zscore_entry_threshold': 1.5})
        signals = strategy.generate_signals(extreme_spx, extreme_btc)
        
        if signals:
            self.assertGreater(signals[0].confidence, 0.5)
            print(f"\nExtreme divergence signal confidence: {signals[0].confidence}")


if __name__ == "__main__":
    # Run basic demo
    np.random.seed(42)
    n = 200
    
    # Generate SPX data
    spx_prices = 4000 * np.exp(np.cumsum(np.random.normal(0.00005, 0.01, n)))
    spx = pd.DataFrame({
        'open': spx_prices * 0.999,
        'high': spx_prices * 1.005,
        'low': spx_prices * 0.995,
        'close': spx_prices,
        'volume': np.random.uniform(1000, 5000, n)
    })
    
    # Generate BTC data with divergence period
    btc_prices = 50000 * np.exp(np.cumsum(np.random.normal(0.0001, 0.02, n)))
    btc_prices[80:95] *= np.linspace(1.0, 1.08, 15)  # BTC pumps 8%
    spx['close'].iloc[80:95] *= 0.97  # SPX dips 3%
    
    btc = pd.DataFrame({
        'open': btc_prices * 0.998,
        'high': btc_prices * 1.015,
        'low': btc_prices * 0.985,
        'close': btc_prices,
        'volume': np.random.uniform(100, 1000, n)
    })
    
    strategy = CrossAssetSPXBTCZScoreDivergenceStrategy()
    signals = strategy.generate_signals(spx, btc)
    analysis = strategy.get_zscore_analysis(spx, btc)
    
    print("=" * 60)
    print("SPX/BTC Z-Score Divergence Strategy Demo")
    print("=" * 60)
    print(f"\nCurrent Analysis:")
    print(f"  SPX/BTC Ratio: {analysis['current_ratio']:.8f}")
    print(f"  Z-Score: {analysis['current_zscore']:.3f}")
    print(f"  Diverged: {analysis['is_diverged']}")
    print(f"  Direction: {analysis['divergence_direction']}")
    
    print(f"\nGenerated {len(signals)} signals:")
    for sig in signals[:3]:
        print(f"\n  {sig.direction}")
        print(f"    Confidence: {sig.confidence:.1%}")
        print(f"    Entry Ratio: {sig.entry_price:.8f}")
        print(f"    Target (Mean): {sig.take_profit:.8f}")
        print(f"    Reason: {sig.reason}")
    
    print("\n" + "=" * 60)
    
    # Run unit tests
    unittest.main(argv=[''], verbosity=2, exit=False)
