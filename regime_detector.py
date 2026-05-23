#!/usr/bin/env python3
"""
Market Regime Detector

Determines current market regime to activate appropriate strategy ensemble.
Uses multiple features to classify:
- Volatility regime (low/medium/high/extreme)
- Trend regime (strong up/weak up/sideways/weak down/strong down)
- Sentiment regime (greed/fear/extreme fear)
- Liquidity regime (high/low)

Output: Regime classification + recommended ensemble
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json

DB_PATH = Path("crypto_data.db")
REGIME_FILE = Path("battleground/data/current_regime.json")


@dataclass
class MarketRegime:
    """Current market regime classification"""
    timestamp: str
    
    # Volatility
    volatility_regime: str  # low, medium, high, extreme
    atr_14: float
    atr_percentile: float
    
    # Trend
    trend_regime: str  # strong_up, weak_up, sideways, weak_down, strong_down
    ema_20_slope: float
    ema_50_slope: float
    adx: float
    
    # Sentiment (proxy indicators)
    sentiment_regime: str  # extreme_greed, greed, neutral, fear, extreme_fear
    funding_rate: float
    funding_percentile: float
    
    # Liquidity
    liquidity_regime: str  # high, medium, low
    volume_percentile: float
    spread_proxy: float
    
    # Composite
    overall_regime: str
    confidence: float
    recommended_ensemble: str
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'volatility': {
                'regime': self.volatility_regime,
                'atr_14': round(self.atr_14, 2),
                'percentile': round(self.atr_percentile, 1)
            },
            'trend': {
                'regime': self.trend_regime,
                'ema_20_slope': round(self.ema_20_slope, 4),
                'ema_50_slope': round(self.ema_50_slope, 4),
                'adx': round(self.adx, 1)
            },
            'sentiment': {
                'regime': self.sentiment_regime,
                'funding_rate': round(self.funding_rate, 4),
                'funding_percentile': round(self.funding_percentile, 1)
            },
            'liquidity': {
                'regime': self.liquidity_regime,
                'volume_percentile': round(self.volume_percentile, 1)
            },
            'recommendation': {
                'overall_regime': self.overall_regime,
                'confidence': round(self.confidence, 2),
                'ensemble': self.recommended_ensemble
            }
        }


class RegimeDetector:
    """Detects current market regime from price and on-chain data"""
    
    def __init__(self, db_path: str = "crypto_data.db"):
        self.db_path = Path(db_path)
        
    def load_data(self, pair: str = "BTC/USDT", lookback: int = 100) -> pd.DataFrame:
        """Load recent price data"""
        try:
            conn = sqlite3.connect(self.db_path)
            query = f"""
                SELECT timestamp, open, high, low, close, volume, funding_rate
                FROM klines 
                WHERE pair = '{pair}' 
                ORDER BY timestamp DESC 
                LIMIT {lookback}
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if df.empty:
                return None
                
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            return df
        except Exception as e:
            print(f"Error loading data: {e}")
            return None
    
    def calculate_volatility_regime(self, df: pd.DataFrame) -> Tuple[str, float, float]:
        """
        Calculate volatility regime based on ATR
        Returns: (regime, atr_14, percentile)
        """
        # Calculate ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr_14 = true_range.rolling(14).mean().iloc[-1]
        
        # ATR as % of price
        current_price = df['close'].iloc[-1]
        atr_pct = (atr_14 / current_price) * 100
        
        # Calculate percentile over lookback period
        atr_history = (true_range / df['close']) * 100
        percentile = (atr_history <= atr_pct).mean() * 100
        
        # Classify regime
        if percentile > 90:
            regime = "extreme"
        elif percentile > 75:
            regime = "high"
        elif percentile > 25:
            regime = "medium"
        else:
            regime = "low"
            
        return regime, atr_pct, percentile
    
    def calculate_trend_regime(self, df: pd.DataFrame) -> Tuple[str, float, float, float]:
        """
        Calculate trend regime
        Returns: (regime, ema20_slope, ema50_slope, adx)
        """
        # Calculate EMAs
        ema_20 = df['close'].ewm(span=20).mean()
        ema_50 = df['close'].ewm(span=50).mean()
        
        # Calculate slopes (normalized)
        ema_20_slope = (ema_20.iloc[-1] - ema_20.iloc[-5]) / ema_20.iloc[-5]
        ema_50_slope = (ema_50.iloc[-1] - ema_50.iloc[-10]) / ema_50.iloc[-10]
        
        # Calculate ADX (simplified)
        plus_dm = df['high'].diff()
        minus_dm = df['low'].diff(-1).abs()
        
        tr = pd.concat([
            df['high'] - df['low'],
            (df['high'] - df['close'].shift()).abs(),
            (df['low'] - df['close'].shift()).abs()
        ], axis=1).max(axis=1)
        
        atr = tr.rolling(14).mean()
        
        # Simplified ADX approximation
        dx = ((ema_20 - ema_50).abs() / ((ema_20 + ema_50) / 2)) * 100
        adx = dx.rolling(14).mean().iloc[-1]
        
        # Classify trend
        if adx > 25:  # Strong trend
            if ema_20_slope > 0.02 and ema_50_slope > 0.01:
                regime = "strong_up"
            elif ema_20_slope < -0.02 and ema_50_slope < -0.01:
                regime = "strong_down"
            elif ema_20_slope > 0:
                regime = "weak_up"
            else:
                regime = "weak_down"
        else:  # Weak/no trend
            if abs(ema_20_slope) < 0.005 and abs(ema_50_slope) < 0.005:
                regime = "sideways"
            elif ema_20_slope > 0:
                regime = "weak_up"
            else:
                regime = "weak_down"
                
        return regime, ema_20_slope, ema_50_slope, adx
    
    def calculate_sentiment_regime(self, df: pd.DataFrame) -> Tuple[str, float, float]:
        """
        Calculate sentiment regime from funding rate
        Returns: (regime, funding_rate, percentile)
        """
        funding = df['funding_rate'].dropna()
        
        if len(funding) < 10:
            return "neutral", 0, 50
        
        current_funding = funding.iloc[-1]
        
        # Calculate percentile
        percentile = (funding <= current_funding).mean() * 100
        
        # Classify sentiment
        if percentile > 90:
            regime = "extreme_greed"
        elif percentile > 70:
            regime = "greed"
        elif percentile > 30:
            regime = "neutral"
        elif percentile > 10:
            regime = "fear"
        else:
            regime = "extreme_fear"
            
        return regime, current_funding, percentile
    
    def calculate_liquidity_regime(self, df: pd.DataFrame) -> Tuple[str, float]:
        """
        Calculate liquidity regime from volume
        Returns: (regime, volume_percentile)
        """
        volume = df['volume']
        current_vol = volume.iloc[-1]
        
        # Volume percentile
        percentile = (volume <= current_vol).mean() * 100
        
        if percentile > 80:
            regime = "high"
        elif percentile > 40:
            regime = "medium"
        else:
            regime = "low"
            
        return regime, percentile
    
    def determine_overall_regime(self, 
                                  vol_regime: str, 
                                  trend_regime: str, 
                                  sentiment_regime: str,
                                  liquidity_regime: str) -> Tuple[str, float, str]:
        """
        Determine overall regime and recommended ensemble
        Returns: (overall_regime, confidence, recommended_ensemble)
        """
        # Ensemble mapping
        ensemble_map = {
            # Volatility regimes
            ("extreme", "*", "*", "*"): ("volatility_crisis", 0.9, "volatility_ensemble"),
            ("high", "strong_down", "*", "*"): ("crash_recovery", 0.85, "volatility_ensemble"),
            ("high", "*", "extreme_fear", "*"): ("capitulation", 0.8, "volatility_ensemble"),
            
            # Trending regimes
            ("medium", "strong_up", "*", "high"): ("strong_trend", 0.8, "trend_ensemble"),
            ("low", "strong_up", "greed", "*"): ("mature_trend", 0.75, "trend_ensemble"),
            ("medium", "strong_down", "*", "*"): ("downtrend", 0.75, "trend_ensemble_short"),
            
            # Ranging regimes
            ("low", "sideways", "neutral", "*"): ("low_vol_chop", 0.7, "arbitrage_ensemble"),
            ("medium", "sideways", "*", "medium"): ("mean_reversion", 0.7, "mean_reversion_ensemble"),
            
            # Default
        }
        
        # Check for exact matches first
        for pattern, result in ensemble_map.items():
            v_match = pattern[0] == "*" or pattern[0] == vol_regime
            t_match = pattern[1] == "*" or pattern[1] == trend_regime
            s_match = pattern[2] == "*" or pattern[2] == sentiment_regime
            l_match = pattern[3] == "*" or pattern[3] == liquidity_regime
            
            if v_match and t_match and s_match and l_match:
                return result
        
        # Default regime
        return ("mixed", 0.5, "conservative_ensemble")
    
    def detect(self, pair: str = "BTC/USDT") -> MarketRegime:
        """Detect current market regime"""
        df = self.load_data(pair)
        if df is None or len(df) < 50:
            raise ValueError(f"Insufficient data for {pair}")
        
        # Calculate all regimes
        vol_regime, atr_14, atr_pct = self.calculate_volatility_regime(df)
        trend_regime, ema20_slope, ema50_slope, adx = self.calculate_trend_regime(df)
        sentiment_regime, funding, funding_pct = self.calculate_sentiment_regime(df)
        liquidity_regime, vol_pct = self.calculate_liquidity_regime(df)
        
        # Overall regime
        overall, confidence, ensemble = self.determine_overall_regime(
            vol_regime, trend_regime, sentiment_regime, liquidity_regime
        )
        
        return MarketRegime(
            timestamp=datetime.now(timezone.utc).isoformat(),
            volatility_regime=vol_regime,
            atr_14=atr_14,
            atr_percentile=atr_pct,
            trend_regime=trend_regime,
            ema_20_slope=ema20_slope,
            ema_50_slope=ema50_slope,
            adx=adx,
            sentiment_regime=sentiment_regime,
            funding_rate=funding,
            funding_percentile=funding_pct,
            liquidity_regime=liquidity_regime,
            volume_percentile=vol_pct,
            spread_proxy=0,  # Would need order book data
            overall_regime=overall,
            confidence=confidence,
            recommended_ensemble=ensemble
        )
    
    def save_regime(self, regime: MarketRegime):
        """Save regime to file"""
        REGIME_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(REGIME_FILE, 'w') as f:
            json.dump(regime.to_dict(), f, indent=2)
        print(f"Regime saved to {REGIME_FILE}")
    
    def print_regime(self, regime: MarketRegime):
        """Print regime in readable format"""
        print("="*60)
        print("MARKET REGIME DETECTION")
        print(f"Time: {regime.timestamp[:19]} UTC")
        print("="*60)
        print(f"\nVolatility: {regime.volatility_regime.upper()}")
        print(f"  ATR: {regime.atr_14:.2f}% (percentile: {regime.atr_percentile:.0f})")
        
        print(f"\nTrend: {regime.trend_regime.upper()}")
        print(f"  EMA20 slope: {regime.ema_20_slope:.4f}")
        print(f"  EMA50 slope: {regime.ema_50_slope:.4f}")
        print(f"  ADX: {regime.adx:.1f}")
        
        print(f"\nSentiment: {regime.sentiment_regime.upper()}")
        print(f"  Funding: {regime.funding_rate:.4f} ({regime.funding_percentile:.0f}th percentile)")
        
        print(f"\nLiquidity: {regime.liquidity_regime.upper()}")
        print(f"  Volume: {regime.volume_percentile:.0f}th percentile")
        
        print("\n" + "="*60)
        print(f"OVERALL REGIME: {regime.overall_regime.upper()}")
        print(f"Confidence: {regime.confidence:.0%}")
        print(f"Recommended Ensemble: {regime.recommended_ensemble}")
        print("="*60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Market Regime Detector')
    parser.add_argument('--pair', default='BTC/USDT', help='Trading pair')
    parser.add_argument('--save', action='store_true', help='Save to file')
    parser.add_argument('--watch', action='store_true', help='Watch mode (update every 5 min)')
    
    args = parser.parse_args()
    
    detector = RegimeDetector()
    
    if args.watch:
        import time
        print("Watch mode - updating every 5 minutes (Ctrl+C to exit)")
        while True:
            try:
                regime = detector.detect(args.pair)
                detector.print_regime(regime)
                if args.save:
                    detector.save_regime(regime)
                print("\nWaiting 5 minutes...\n")
                time.sleep(300)
            except KeyboardInterrupt:
                break
    else:
        regime = detector.detect(args.pair)
        detector.print_regime(regime)
        if args.save:
            detector.save_regime(regime)
