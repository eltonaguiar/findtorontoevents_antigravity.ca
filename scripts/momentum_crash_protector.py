"""
Momentum Crash Protection System
Prevents momentum strategy failures during high volatility periods
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class MomentumCrashProtector:
    def __init__(self, vix_threshold=30, momentum_threshold=0.8):
        """
        Initialize momentum crash protector
        
        Args:
            vix_threshold: VIX level above which momentum is disabled
            momentum_threshold: Minimum momentum variance ratio required
        """
        self.vix_threshold = vix_threshold
        self.momentum_threshold = momentum_threshold
        
    def get_vix_level(self):
        """Get current VIX level from Yahoo Finance"""
        try:
            vix = yf.Ticker("^VIX")
            hist = vix.history(period="1d")
            if len(hist) > 0:
                return hist['Close'].iloc[-1]
        except Exception as e:
            print(f"Error fetching VIX: {e}")
            return 15.0  # Default safe level
        return 15.0
    
    def calculate_momentum_variance_ratio(self, symbol, lookback_days=252):
        """
        Calculate momentum variance ratio (MVR)
        Higher values indicate stronger, more consistent momentum
        """
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period=f"{lookback_days}d")
            
            if len(hist) < 50:
                return 0.0
            
            # Calculate momentum (price change over 20 days)
            hist['momentum'] = hist['Close'].pct_change(20)
            hist['momentum_std'] = hist['momentum'].rolling(20).std()
            
            # Variance ratio: mean momentum / momentum volatility
            recent_momentum = hist['momentum'].tail(20)
            momentum_mean = recent_momentum.mean()
            momentum_std = recent_momentum.std()
            
            if momentum_std == 0:
                return 0.0
                
            variance_ratio = abs(momentum_mean) / momentum_std
            return variance_ratio
            
        except Exception as e:
            print(f"Error calculating MVR for {symbol}: {e}")
            return 0.0
    
    def is_momentum_safe(self, symbol):
        """
        Determine if momentum trading is safe for given symbol
        Returns True if conditions are favorable
        """
        vix_level = self.get_vix_level()
        mvr = self.calculate_momentum_variance_ratio(symbol)
        
        print(f"VIX Level: {vix_level:.2f}")
        print(f"Momentum Variance Ratio: {mvr:.3f}")
        
        # Check VIX condition
        if vix_level > self.vix_threshold:
            print("❌ Momentum disabled: VIX too high")
            return False
        
        # Check momentum quality
        if mvr < self.momentum_threshold:
            print("❌ Momentum disabled: Weak momentum signal")
            return False
        
        print("✅ Momentum conditions favorable")
        return True
    
    def get_momentum_regime(self, symbol):
        """
        Get detailed momentum regime analysis
        Returns dict with regime classification and metrics
        """
        vix_level = self.get_vix_level()
        mvr = self.calculate_momentum_variance_ratio(symbol)
        
        regime = {
            'vix_level': vix_level,
            'momentum_variance_ratio': mvr,
            'volatility_regime': 'high' if vix_level > self.vix_threshold else 'normal',
            'momentum_quality': 'strong' if mvr > self.momentum_threshold else 'weak',
            'trading_allowed': vix_level <= self.vix_threshold and mvr >= self.momentum_threshold
        }
        
        return regime
    
    def protect_portfolio(self, portfolio_symbols):
        """
        Apply momentum protection to entire portfolio
        Returns list of symbols safe for momentum trading
        """
        safe_symbols = []
        
        for symbol in portfolio_symbols:
            if self.is_momentum_safe(symbol):
                safe_symbols.append(symbol)
        
        print(f"\nSafe for momentum trading: {len(safe_symbols)}/{len(portfolio_symbols)} symbols")
        return safe_symbols

# Example usage
if __name__ == "__main__":
    protector = MomentumCrashProtector()
    
    # Test with sample portfolio
    test_portfolio = ["AAPL", "MSFT", "GOOGL", "TSLA", "SPY"]
    
    print("=== Momentum Crash Protection Analysis ===")
    safe_symbols = protector.protect_portfolio(test_portfolio)
    
    print("\n=== Individual Symbol Analysis ===")
    for symbol in test_portfolio:
        regime = protector.get_momentum_regime(symbol)
        print(f"{symbol}: VIX={regime['vix_level']:.1f}, MVR={regime['momentum_variance_ratio']:.3f}, "
              f"Volatility={regime['volatility_regime']}, Momentum={regime['momentum_quality']}")