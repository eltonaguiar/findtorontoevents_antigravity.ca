#!/usr/bin/env python3
"""
Volume Anomaly Detector
Identifies accumulation before price moves
The #1 predictor of 100x gems
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class VolumeSignal:
    symbol: str
    timestamp: datetime
    volume_spike: float  # Multiple of average
    price_change: float  # % change
    accumulation_score: int  # 0-100
    signal_type: str  # 'accumulation', 'distribution', 'breakout'
    confidence: str  # 'high', 'medium', 'low'


class VolumeAnomalyDetector:
    """
    Detects volume patterns that precede major moves
    Based on 100x gem research:
    - 3x+ volume without price = accumulation
    - Volume precedes price by 1-7 days
    """
    
    def __init__(self):
        self.baseline_period = 7  # days
        self.volume_threshold = 3.0  # 3x average
        
    def calculate_baseline(self, df: pd.DataFrame) -> Dict:
        """Calculate baseline volume and price metrics"""
        if len(df) < self.baseline_period:
            return None
        
        baseline_vol = df['volume'].tail(self.baseline_period).mean()
        baseline_price = df['close'].tail(self.baseline_period).mean()
        
        return {
            'avg_volume': baseline_vol,
            'avg_price': baseline_price,
            'vol_std': df['volume'].tail(self.baseline_period).std(),
            'price_std': df['close'].tail(self.baseline_period).std()
        }
    
    def detect_accumulation(self, df: pd.DataFrame, symbol: str) -> VolumeSignal:
        """
        Detect accumulation pattern:
        - Volume increasing
        - Price consolidating (not moving much)
        - Smart money building positions
        """
        if len(df) < 10:
            return None
        
        baseline = self.calculate_baseline(df)
        if not baseline:
            return None
        
        # Current metrics
        current_vol = df['volume'].iloc[-1]
        current_price = df['close'].iloc[-1]
        
        # Volume spike calculation
        vol_spike = current_vol / baseline['avg_volume'] if baseline['avg_volume'] > 0 else 0
        
        # Price change over period
        price_start = df['close'].iloc[-self.baseline_period]
        price_change = ((current_price - price_start) / price_start) * 100
        
        # Accumulation score
        score = 0
        
        # Volume component (0-50 points)
        if vol_spike >= 5.0:
            score += 50
        elif vol_spike >= 3.0:
            score += 40
        elif vol_spike >= 2.0:
            score += 25
        elif vol_spike >= 1.5:
            score += 15
        
        # Price suppression component (0-50 points)
        # High volume + low price change = accumulation
        if abs(price_change) < 10 and vol_spike >= 3.0:
            score += 50  # Perfect accumulation
        elif abs(price_change) < 20 and vol_spike >= 2.0:
            score += 35
        elif abs(price_change) < 30 and vol_spike >= 1.5:
            score += 20
        
        # Determine signal type
        if vol_spike >= 3.0 and abs(price_change) < 20:
            signal_type = 'accumulation'
        elif vol_spike >= 3.0 and price_change > 30:
            signal_type = 'breakout'
        elif vol_spike >= 2.0 and price_change < -20:
            signal_type = 'distribution'
        else:
            signal_type = 'neutral'
        
        # Confidence level
        if score >= 80:
            confidence = 'high'
        elif score >= 60:
            confidence = 'medium'
        else:
            confidence = 'low'
        
        return VolumeSignal(
            symbol=symbol,
            timestamp=datetime.now(),
            volume_spike=vol_spike,
            price_change=price_change,
            accumulation_score=score,
            signal_type=signal_type,
            confidence=confidence
        )
    
    def detect_sustained_volume(self, df: pd.DataFrame, days: int = 3) -> bool:
        """
        Detect if volume has been elevated for multiple days
        Sustained volume = real interest, not just a one-day pump
        """
        if len(df) < days + self.baseline_period:
            return False
        
        baseline_vol = df['volume'].tail(days + self.baseline_period).head(self.baseline_period).mean()
        
        recent_days = df['volume'].tail(days)
        elevated_days = sum(1 for vol in recent_days if vol > baseline_vol * 2)
        
        # 2+ days of elevated volume
        return elevated_days >= 2
    
    def detect_volume_climax(self, df: pd.DataFrame) -> bool:
        """
        Detect volume climax (potential top)
        5x+ volume with large price move = distribution
        """
        if len(df) < 2:
            return False
        
        current_vol = df['volume'].iloc[-1]
        prev_vol = df['volume'].iloc[-2]
        
        # Sudden massive volume spike
        if current_vol > prev_vol * 5:
            price_change = ((df['close'].iloc[-1] - df['open'].iloc[-1]) / df['open'].iloc[-1]) * 100
            
            # Large price move with massive volume = climax
            if abs(price_change) > 20:
                return True
        
        return False
    
    def score_opportunity(self, df: pd.DataFrame, symbol: str) -> Dict:
        """
        Score a token for 100x potential based on volume patterns
        """
        signal = self.detect_accumulation(df, symbol)
        
        if not signal:
            return None
        
        analysis = {
            'symbol': symbol,
            'timestamp': signal.timestamp.isoformat(),
            'volume_spike': f"{signal.volume_spike:.1f}x",
            'price_change_7d': f"{signal.price_change:.1f}%",
            'accumulation_score': signal.accumulation_score,
            'signal_type': signal.signal_type,
            'confidence': signal.confidence,
            'is_sustained': self.detect_sustained_volume(df),
            'climax_warning': self.detect_volume_climax(df)
        }
        
        # Recommendation
        if signal.accumulation_score >= 80 and signal.signal_type == 'accumulation':
            analysis['recommendation'] = '🚀 STRONG BUY - High accumulation detected'
            analysis['urgency'] = 'immediate'
        elif signal.accumulation_score >= 60 and signal.signal_type == 'accumulation':
            analysis['recommendation'] = '👀 WATCH - Early accumulation'
            analysis['urgency'] = '24-48h'
        elif signal.signal_type == 'breakout':
            analysis['recommendation'] = '⚡ BREAKOUT - May have missed entry'
            analysis['urgency'] = 'caution'
        elif signal.signal_type == 'distribution':
            analysis['recommendation'] = '❌ AVOID - Distribution phase'
            analysis['urgency'] = 'avoid'
        else:
            analysis['recommendation'] = '⏸️  HOLD - No clear signal'
            analysis['urgency'] = 'monitor'
        
        return analysis
    
    def scan_for_accumulation(self, tokens_data: Dict[str, pd.DataFrame]) -> List[Dict]:
        """
        Scan multiple tokens for accumulation patterns
        """
        opportunities = []
        
        for symbol, df in tokens_data.items():
            try:
                analysis = self.score_opportunity(df, symbol)
                
                if analysis and analysis['accumulation_score'] >= 60:
                    opportunities.append(analysis)
                    
            except Exception as e:
                print(f"Error analyzing {symbol}: {e}")
                continue
        
        # Sort by accumulation score
        opportunities.sort(key=lambda x: x['accumulation_score'], reverse=True)
        
        return opportunities


# Pattern recognition for 100x gems
class PatternRecognizer:
    """
    Recognize specific patterns from documented 100x gainers
    """
    
    @staticmethod
    def is_pre_pump_signature(df: pd.DataFrame) -> Dict:
        """
        Check if price action matches pre-pump signature:
        - 7 days of volume building
        - Price consolidating in range
        - Sudden volume spike on day 7-8
        """
        if len(df) < 10:
            return {'match': False}
        
        # Volume trend
        vol_week1 = df['volume'].tail(10).head(7).mean()
        vol_recent = df['volume'].tail(3).mean()
        
        vol_increasing = vol_recent > vol_week1 * 2
        
        # Price range (consolidation)
        week1_high = df['high'].tail(10).head(7).max()
        week1_low = df['low'].tail(10).head(7).min()
        price_range = (week1_high - week1_low) / week1_low
        
        consolidating = price_range < 0.30  # 30% range or less
        
        # Recent breakout attempt
        recent_high = df['high'].tail(3).max()
        breakout_attempt = recent_high > week1_high * 1.05
        
        # Match score
        score = 0
        if vol_increasing:
            score += 40
        if consolidating:
            score += 30
        if breakout_attempt:
            score += 30
        
        return {
            'match': score >= 70,
            'score': score,
            'vol_increasing': vol_increasing,
            'consolidating': consolidating,
            'breakout_attempt': breakout_attempt,
            'pattern': 'pre_pump_accumulation' if score >= 70 else 'none'
        }
    
    @staticmethod
    def is_viral_breakout(df: pd.DataFrame) -> Dict:
        """
        Detect viral breakout pattern:
        - Massive volume spike (5x+)
        - Large green candle (>20%)
        - Continuation likely if volume sustains
        """
        if len(df) < 3:
            return {'match': False}
        
        recent = df.tail(3)
        
        # Volume spike
        avg_vol = df['volume'].tail(10).head(7).mean()
        max_vol = recent['volume'].max()
        vol_spike = max_vol / avg_vol if avg_vol > 0 else 0
        
        # Price move
        price_start = recent['open'].iloc[0]
        price_end = recent['close'].iloc[-1]
        price_move = (price_end - price_start) / price_start
        
        match = vol_spike >= 5.0 and price_move >= 0.20
        
        return {
            'match': match,
            'vol_spike': vol_spike,
            'price_move': price_move * 100,
            'pattern': 'viral_breakout' if match else 'none'
        }


# Example usage
if __name__ == "__main__":
    import numpy as np
    
    detector = VolumeAnomalyDetector()
    
    # Create sample data with accumulation pattern
    np.random.seed(42)
    sample_data = pd.DataFrame({
        'open': 100 + np.random.randn(20).cumsum(),
        'high': 105 + np.random.randn(20).cumsum(),
        'low': 95 + np.random.randn(20).cumsum(),
        'close': 100 + np.random.randn(20).cumsum(),
        'volume': [1000, 1200, 1100, 1300, 1500, 1800, 2200, 3500, 4000, 4500,
                   1000, 1100, 1050, 1150, 1200, 1300, 1400, 1600, 1800, 2100]
    })
    
    # Ensure realistic price bounds
    sample_data['high'] = sample_data[['open', 'close']].max(axis=1) + abs(np.random.randn(20)) * 2
    sample_data['low'] = sample_data[['open', 'close']].min(axis=1) - abs(np.random.randn(20)) * 2
    
    # Analyze
    result = detector.score_opportunity(sample_data, "TEST_TOKEN")
    
    if result:
        print("📊 Volume Anomaly Analysis")
        print("=" * 50)
        print(f"Token: {result['symbol']}")
        print(f"Volume Spike: {result['volume_spike']}")
        print(f"Price Change (7d): {result['price_change_7d']}")
        print(f"Accumulation Score: {result['accumulation_score']}/100")
        print(f"Signal Type: {result['signal_type']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Sustained: {result['is_sustained']}")
        print(f"\n🎯 Recommendation: {result['recommendation']}")
        
        # Pattern check
        pattern = PatternRecognizer.is_pre_pump_signature(sample_data)
        if pattern['match']:
            print(f"\n💎 PATTERN MATCH: {pattern['pattern']} ({pattern['score']}/100)")
    else:
        print("No clear volume signal detected.")
