"""
Momentum Variance Ratio Calculator
Measures the consistency and quality of momentum signals
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class MomentumVarianceRatio:
    def __init__(self, lookback_days=252, momentum_period=20):
        """
        Initialize momentum variance ratio calculator
        
        Args:
            lookback_days: Number of days for historical analysis
            momentum_period: Period for momentum calculation (default 20 days)
        """
        self.lookback_days = lookback_days
        self.momentum_period = momentum_period
    
    def calculate_mvr(self, symbol):
        """
        Calculate Momentum Variance Ratio (MVR)
        
        MVR = |mean momentum| / momentum volatility
        Higher MVR indicates stronger, more consistent momentum
        """
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period=f"{self.lookback_days}d")
            
            if len(hist) < self.momentum_period * 2:
                return {'mvr': 0.0, 'momentum_mean': 0.0, 'momentum_std': 0.0, 'error': 'Insufficient data'}
            
            # Calculate momentum (price change over momentum period)
            hist['momentum'] = hist['Close'].pct_change(self.momentum_period)
            hist['momentum_std'] = hist['momentum'].rolling(self.momentum_period).std()
            
            # Use recent momentum data
            recent_momentum = hist['momentum'].tail(self.momentum_period)
            momentum_mean = recent_momentum.mean()
            momentum_std = recent_momentum.std()
            
            if momentum_std == 0:
                mvr = 0.0
            else:
                mvr = abs(momentum_mean) / momentum_std
            
            return {
                'mvr': mvr,
                'momentum_mean': momentum_mean,
                'momentum_std': momentum_std,
                'momentum_direction': 'up' if momentum_mean > 0 else 'down',
                'signal_strength': self.classify_strength(mvr),
                'data_points': len(recent_momentum)
            }
            
        except Exception as e:
            return {'mvr': 0.0, 'momentum_mean': 0.0, 'momentum_std': 0.0, 'error': str(e)}
    
    def classify_strength(self, mvr):
        """Classify momentum strength based on MVR value"""
        if mvr > 1.5:
            return 'very_strong'
        elif mvr > 1.0:
            return 'strong'
        elif mvr > 0.5:
            return 'moderate'
        elif mvr > 0.2:
            return 'weak'
        else:
            return 'very_weak'
    
    def analyze_momentum_quality(self, symbol):
        """
        Comprehensive momentum quality analysis
        Returns detailed metrics about momentum characteristics
        """
        mvr_result = self.calculate_mvr(symbol)
        
        if 'error' in mvr_result:
            return mvr_result
        
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period=f"{self.lookback_days}d")
            
            # Additional momentum metrics
            hist['returns'] = hist['Close'].pct_change()
            
            # Momentum consistency (how often momentum persists)
            hist['momentum_sign'] = np.sign(hist['momentum'])
            hist['momentum_persistence'] = hist['momentum_sign'].rolling(5).apply(
                lambda x: len(set(x)) == 1, raw=False
            )
            momentum_consistency = hist['momentum_persistence'].mean()
            
            # Volatility-adjusted momentum
            volatility = hist['returns'].std() * np.sqrt(252)  # Annualized
            volatility_adjusted_momentum = mvr_result['momentum_mean'] / volatility if volatility > 0 else 0
            
            analysis = {
                'symbol': symbol,
                'mvr': mvr_result['mvr'],
                'momentum_mean': mvr_result['momentum_mean'],
                'momentum_std': mvr_result['momentum_std'],
                'direction': mvr_result['momentum_direction'],
                'strength': mvr_result['signal_strength'],
                'momentum_consistency': momentum_consistency,
                'volatility_adjusted_momentum': volatility_adjusted_momentum,
                'annual_volatility': volatility,
                'recommendation': self.get_recommendation(mvr_result['mvr'], momentum_consistency),
                'lookback_period': self.lookback_days
            }
            
            return analysis
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_recommendation(self, mvr, consistency):
        """Generate trading recommendation based on momentum quality"""
        if mvr > 1.0 and consistency > 0.7:
            return 'high_confidence'
        elif mvr > 0.5 and consistency > 0.6:
            return 'medium_confidence'
        elif mvr > 0.2:
            return 'low_confidence'
        else:
            return 'avoid'
    
    def compare_momentum_signals(self, symbols):
        """
        Compare momentum quality across multiple symbols
        Returns ranked list by momentum quality
        """
        results = []
        
        for symbol in symbols:
            analysis = self.analyze_momentum_quality(symbol)
            if 'error' not in analysis:
                results.append(analysis)
        
        # Sort by MVR (highest first)
        results.sort(key=lambda x: x['mvr'], reverse=True)
        
        return results

# Example usage
if __name__ == "__main__":
    mvr_calc = MomentumVarianceRatio()
    
    # Test with sample symbols
    test_symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "SPY", "QQQ"]
    
    print("=== Momentum Variance Ratio Analysis ===")
    
    for symbol in test_symbols:
        analysis = mvr_calc.analyze_momentum_quality(symbol)
        
        if 'error' in analysis:
            print(f"{symbol}: Error - {analysis['error']}")
        else:
            print(f"{symbol}: MVR={analysis['mvr']:.3f} ({analysis['strength']}), "
                  f"Direction={analysis['direction']}, Consistency={analysis['momentum_consistency']:.2f}, "
                  f"Recommendation={analysis['recommendation']}")
    
    print("\n=== Ranked Momentum Signals ===")
    ranked_signals = mvr_calc.compare_momentum_signals(test_symbols)
    
    for i, signal in enumerate(ranked_signals, 1):
        print(f"{i}. {signal['symbol']}: MVR={signal['mvr']:.3f} ({signal['strength']}) - {signal['recommendation']}")