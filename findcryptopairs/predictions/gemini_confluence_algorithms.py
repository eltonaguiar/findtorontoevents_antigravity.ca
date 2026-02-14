#!/usr/bin/env python3
"""
Gemini Deep Research Confluence Algorithms
Based on: "Quantitative Reverse-Engineering of Historical Entry Signals: 
A Multi-Asset Analysis of BTC, ETH, BNB, AVAX (2020-2021)"

Three Confluence Zones Framework:
- Zone 1: Macro-Bottom (Extreme Exhaustion)
- Zone 2: Ecosystem Breakout (Structural Change)  
- Zone 3: Momentum Continuation (Trend Support)

Author: Google Gemini 2.5 Pro Analysis
Implementation: KIMI/Cursor Hybrid
"""

import json
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

class SignalZone(Enum):
    MACRO_BOTTOM = "macro_bottom"          # Zone 1
    ECOSYSTEM_BREAKOUT = "ecosystem"        # Zone 2
    MOMENTUM_CONTINUATION = "momentum"      # Zone 3
    DISTRIBUTION = "distribution"           # Warning

class SignalStrength(Enum):
    WEAK = 1
    MODERATE = 2
    STRONG = 3
    CONFLUENCE = 4

@dataclass
class Signal:
    zone: SignalZone
    strength: SignalStrength
    confidence: float  # 0-100
    indicators: Dict[str, any]
    entry_price: float
    target_price: float
    stop_loss: float
    timeframe: str
    rationale: str

class ConfluenceEngine:
    """
    Multi-factor signal engine implementing Gemini research findings.
    Combines technical, on-chain, and sentiment indicators.
    """
    
    def __init__(self):
        self.weights = {
            'mvrv_z_score': 0.20,
            'rsi': 0.15,
            'ema_structure': 0.15,
            'volume_profile': 0.15,
            'funding_rates': 0.10,
            'bollinger_bands': 0.10,
            'macd': 0.10,
            'sentiment': 0.05
        }
        
    def calculate_zone_1_signal(self, 
                                price: float,
                                mvrv_z: float,
                                rsi_weekly: float,
                                price_vs_200w_ma: float,
                                funding_rate: float) -> Optional[Signal]:
        """
        Zone 1: Macro-Bottom Detection
        MVRV Z-Score green zone, RSI <30, 200-week MA touch
        March 2020 style capitulation identification
        """
        score = 0
        indicators = {}
        
        # MVRV Z-Score analysis
        if mvrv_z < 0:
            score += 25
            indicators['mvrv'] = f"Green zone ({mvrv_z:.2f})"
        elif mvrv_z < 1:
            score += 15
            indicators['mvrv'] = f"Accumulation ({mvrv_z:.2f})"
        else:
            indicators['mvrv'] = f"Neutral/Overvalued ({mvrv_z:.2f})"
            
        # Weekly RSI
        if rsi_weekly < 30:
            score += 25
            indicators['rsi'] = f"Oversold ({rsi_weekly:.1f})"
        elif rsi_weekly < 40:
            score += 15
            indicators['rsi'] = f"Weak ({rsi_weekly:.1f})"
        else:
            indicators['rsi'] = f"Neutral ({rsi_weekly:.1f})"
            
        # 200-week MA position
        if price_vs_200w_ma < 0.95:  # Below 200W MA
            score += 20
            indicators['200w_ma'] = f"Below support ({price_vs_200w_ma:.2%})"
        elif price_vs_200w_ma < 1.05:
            score += 10
            indicators['200w_ma'] = f"At support ({price_vs_200w_ma:.2%})"
        else:
            indicators['200w_ma'] = f"Above support ({price_vs_200w_ma:.2%})"
            
        # Funding rate (negative = good for longs)
        if funding_rate < -0.01:
            score += 15
            indicators['funding'] = f"Negative ({funding_rate:.3%})"
        elif funding_rate < 0.01:
            score += 10
            indicators['funding'] = f"Neutral ({funding_rate:.3%})"
        else:
            indicators['funding'] = f"Elevated ({funding_rate:.3%})"
            
        if score >= 60:
            return Signal(
                zone=SignalZone.MACRO_BOTTOM,
                strength=SignalStrength.CONFLUENCE if score >= 75 else SignalStrength.STRONG,
                confidence=score,
                indicators=indicators,
                entry_price=price,
                target_price=price * 1.5,  # 50% target per research
                stop_loss=price * 0.92,     # 8% stop
                timeframe="1-6 months",
                rationale="MVRV Z-Score green zone + RSI oversold + 200W MA touch - March 2020 style bottom"
            )
        return None
        
    def calculate_zone_2_signal(self,
                                price: float,
                                volume_24h: float,
                                volume_avg_30d: float,
                                price_vs_range_high: float,
                                ecosystem_tvl_change: float,
                                daily_active_addresses_change: float,
                                narrative_catalyst: str = None) -> Optional[Signal]:
        """
        Zone 2: Ecosystem Breakout Detection
        Volume spike >200%, horizontal range break, TVL/DAA surge
        BSC launch / Avalanche Rush style catalysts
        """
        score = 0
        indicators = {}
        
        # Volume analysis (200%+ spike is key signal)
        volume_ratio = volume_24h / volume_avg_30d if volume_avg_30d > 0 else 0
        if volume_ratio > 3.0:
            score += 25
            indicators['volume'] = f"Extreme spike ({volume_ratio:.1f}x)"
        elif volume_ratio > 2.0:
            score += 20
            indicators['volume'] = f"Breakout confirmed ({volume_ratio:.1f}x)"
        elif volume_ratio > 1.5:
            score += 10
            indicators['volume'] = f"Elevated ({volume_ratio:.1f}x)"
        else:
            indicators['volume'] = f"Normal ({volume_ratio:.1f}x)"
            
        # Range breakout
        if price_vs_range_high > 1.05:  # 5% above range high
            score += 25
            indicators['breakout'] = f"Confirmed ({price_vs_range_high:.2%})"
        elif price_vs_range_high > 1.02:
            score += 15
            indicators['breakout'] = f"Breaking ({price_vs_range_high:.2%})"
        else:
            indicators['breakout'] = f"Below ({price_vs_range_high:.2%})"
            
        # Ecosystem growth (TVL)
        if ecosystem_tvl_change > 1.0:  # 100%+ growth
            score += 20
            indicators['tvl'] = f"Explosive ({ecosystem_tvl_change:.0%})"
        elif ecosystem_tvl_change > 0.5:
            score += 15
            indicators['tvl'] = f"Strong ({ecosystem_tvl_change:.0%})"
        elif ecosystem_tvl_change > 0.2:
            score += 10
            indicators['tvl'] = f"Growing ({ecosystem_tvl_change:.0%})"
        else:
            indicators['tvl'] = f"Flat ({ecosystem_tvl_change:.0%})"
            
        # Daily Active Addresses
        if daily_active_addresses_change > 1.0:
            score += 15
            indicators['daa'] = f"Viral ({daily_active_addresses_change:.0%})"
        elif daily_active_addresses_change > 0.5:
            score += 10
            indicators['daa'] = f"Strong ({daily_active_addresses_change:.0%})"
        else:
            indicators['daa'] = f"Normal ({daily_active_addresses_change:.0%})"
            
        # Narrative catalyst bonus
        if narrative_catalyst:
            score += 15
            indicators['catalyst'] = narrative_catalyst
            
        if score >= 60:
            return Signal(
                zone=SignalZone.ECOSYSTEM_BREAKOUT,
                strength=SignalStrength.CONFLUENCE if score >= 75 else SignalStrength.STRONG,
                confidence=score,
                indicators=indicators,
                entry_price=price,
                target_price=price * 1.5,  # 50% target
                stop_loss=price * 0.90,     # 10% stop (wider for breakouts)
                timeframe="1-3 months",
                rationale=f"Volume breakout ({volume_ratio:.1f}x) + Ecosystem growth (TVL {ecosystem_tvl_change:.0%})"
            )
        return None
        
    def calculate_zone_3_signal(self,
                                price: float,
                                ema_50: float,
                                ema_200: float,
                                bb_middle: float,
                                bb_lower: float,
                                rsi_daily: float,
                                trend_direction: str) -> Optional[Signal]:
        """
        Zone 3: Momentum Continuation
        50-day EMA retest, mid-Bollinger Band bounce
        Trend continuation entries
        """
        score = 0
        indicators = {}
        
        # Must be in established uptrend
        if trend_direction != "uptrend":
            return None
            
        # 50-day EMA retest
        ema_distance = (price - ema_50) / ema_50
        if -0.03 <= ema_distance <= 0.02:  # At or slightly below 50 EMA
            score += 30
            indicators['50ema'] = f"Retest ({ema_distance:.2%})"
        elif ema_distance > 0.02:
            score += 10
            indicators['50ema'] = f"Above ({ema_distance:.2%})"
        else:
            indicators['50ema'] = f"Below ({ema_distance:.2%})"
            
        # Golden Cross status
        if ema_50 > ema_200:
            score += 20
            indicators['golden_cross'] = "Active"
        else:
            indicators['golden_cross'] = "Inactive"
            
        # Bollinger Band position
        bb_position = (price - bb_lower) / (bb_middle - bb_lower) if bb_middle != bb_lower else 0.5
        if 0.4 <= bb_position <= 0.6:  # Around middle band
            score += 25
            indicators['bb_position'] = f"Mid-band ({bb_position:.2f})"
        elif bb_position < 0.4:
            score += 15
            indicators['bb_position'] = f"Lower half ({bb_position:.2f})"
        else:
            indicators['bb_position'] = f"Upper half ({bb_position:.2f})"
            
        # RSI in healthy range
        if 45 <= rsi_daily <= 65:
            score += 20
            indicators['rsi'] = f"Healthy ({rsi_daily:.1f})"
        elif 40 <= rsi_daily < 45:
            score += 15
            indicators['rsi'] = f"Cooling ({rsi_daily:.1f})"
        elif rsi_daily > 70:
            score -= 10  # Overbought penalty
            indicators['rsi'] = f"Overbought ({rsi_daily:.1f})"
        else:
            indicators['rsi'] = f"Weak ({rsi_daily:.1f})"
            
        if score >= 60:
            return Signal(
                zone=SignalZone.MOMENTUM_CONTINUATION,
                strength=SignalStrength.STRONG if score >= 70 else SignalStrength.MODERATE,
                confidence=score,
                indicators=indicators,
                entry_price=price,
                target_price=price * 1.25,  # 25% target for continuation
                stop_loss=ema_50 * 0.95,     # Stop below 50 EMA
                timeframe="2-6 weeks",
                rationale="Trend continuation - 50 EMA retest with Golden Cross active"
            )
        return None
        
    def detect_distribution_warning(self,
                                    mvrv_z: float,
                                    funding_rate: float,
                                    rsi_daily: float,
                                    social_sentiment: float) -> Optional[Signal]:
        """
        Distribution Warning: Late-stage cycle detection
        FOMO peak signals - time to reduce exposure
        """
        warnings = []
        
        if mvrv_z > 7:
            warnings.append(f"MVRV Red Zone ({mvrv_z:.1f})")
        if funding_rate > 0.10:
            warnings.append(f"Extreme funding ({funding_rate:.2%})")
        if rsi_daily > 80:
            warnings.append(f"Overextended RSI ({rsi_daily:.1f})")
        if social_sentiment > 90:
            warnings.append(f"Euphoria sentiment ({social_sentiment:.0f})")
            
        if len(warnings) >= 2:
            return Signal(
                zone=SignalZone.DISTRIBUTION,
                strength=SignalStrength.STRONG,
                confidence=70 + len(warnings) * 10,
                indicators={'warnings': warnings},
                entry_price=0,
                target_price=0,
                stop_loss=0,
                timeframe="Immediate",
                rationale="Late-stage mania signals detected - consider taking profits"
            )
        return None


class WaterfallRotationDetector:
    """
    Detects the "waterfall effect" of capital rotation:
    BTC → ETH → High-utility ecosystem tokens
    """
    
    def __init__(self):
        self.rotation_stages = ['btc_lead', 'eth_follow', 'alt_season']
        
    def detect_rotation(self,
                       btc_price_change_7d: float,
                       eth_price_change_7d: float,
                       alt_index_change_7d: float,
                       btc_dominance_change: float) -> Dict:
        """
        Identifies which stage of capital rotation we're in
        """
        signals = {
            'stage': 'unknown',
            'rotation_signal': None,
            'confidence': 0
        }
        
        # BTC leading
        if btc_price_change_7d > 10 and eth_price_change_7d < btc_price_change_7d * 0.7:
            signals['stage'] = 'btc_lead'
            signals['confidence'] = 75
            
        # ETH catching up (rotation signal)
        if (btc_price_change_7d > 5 and 
            eth_price_change_7d > btc_price_change_7d * 1.2 and
            btc_dominance_change < -1):
            signals['stage'] = 'eth_rotation'
            signals['rotation_signal'] = 'ETH likely to outperform - consider rotation'
            signals['confidence'] = 80
            
        # Altcoin season
        if (alt_index_change_7d > eth_price_change_7d * 1.3 and
            btc_dominance_change < -2):
            signals['stage'] = 'alt_season'
            signals['rotation_signal'] = 'Full altcoin season - high beta plays active'
            signals['confidence'] = 85
            
        return signals


class GeminiConfluenceStrategy:
    """
    Master strategy combining all three zones + rotation detection
    """
    
    def __init__(self):
        self.engine = ConfluenceEngine()
        self.rotation = WaterfallRotationDetector()
        self.signals_history = []
        
    def generate_signal(self, market_data: Dict) -> Dict:
        """
        Main entry point - analyze market and return trading signal
        """
        signals = []
        
        # Zone 1: Macro bottom
        z1 = self.engine.calculate_zone_1_signal(
            price=market_data.get('price', 0),
            mvrv_z=market_data.get('mvrv_z_score', 0),
            rsi_weekly=market_data.get('rsi_weekly', 50),
            price_vs_200w_ma=market_data.get('price_vs_200w_ma', 1.0),
            funding_rate=market_data.get('funding_rate', 0)
        )
        if z1:
            signals.append(z1)
            
        # Zone 2: Ecosystem breakout
        z2 = self.engine.calculate_zone_2_signal(
            price=market_data.get('price', 0),
            volume_24h=market_data.get('volume_24h', 0),
            volume_avg_30d=market_data.get('volume_avg_30d', 1),
            price_vs_range_high=market_data.get('price_vs_range_high', 0.9),
            ecosystem_tvl_change=market_data.get('ecosystem_tvl_change', 0),
            daily_active_addresses_change=market_data.get('daa_change', 0),
            narrative_catalyst=market_data.get('catalyst')
        )
        if z2:
            signals.append(z2)
            
        # Zone 3: Momentum continuation
        z3 = self.engine.calculate_zone_3_signal(
            price=market_data.get('price', 0),
            ema_50=market_data.get('ema_50', 0),
            ema_200=market_data.get('ema_200', 0),
            bb_middle=market_data.get('bb_middle', 0),
            bb_lower=market_data.get('bb_lower', 0),
            rsi_daily=market_data.get('rsi_daily', 50),
            trend_direction=market_data.get('trend', 'sideways')
        )
        if z3:
            signals.append(z3)
            
        # Distribution warning
        warn = self.engine.detect_distribution_warning(
            mvrv_z=market_data.get('mvrv_z_score', 0),
            funding_rate=market_data.get('funding_rate', 0),
            rsi_daily=market_data.get('rsi_daily', 50),
            social_sentiment=market_data.get('social_sentiment', 50)
        )
        if warn:
            signals.append(warn)
            
        # Sort by confidence
        signals.sort(key=lambda x: x.confidence, reverse=True)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'asset': market_data.get('symbol', 'UNKNOWN'),
            'signals': [
                {
                    'zone': s.zone.value,
                    'strength': s.strength.name,
                    'confidence': s.confidence,
                    'entry': s.entry_price,
                    'target': s.target_price,
                    'stop': s.stop_loss,
                    'timeframe': s.timeframe,
                    'rationale': s.rationale,
                    'indicators': s.indicators
                } for s in signals
            ],
            'primary_recommendation': signals[0].zone.value if signals else 'HOLD',
            'highest_confidence': signals[0].confidence if signals else 0
        }


# ==================== BACKTEST SIMULATOR ====================

class BacktestSimulator:
    """
    Simulates Gemini Confluence strategy on historical data
    """
    
    def __init__(self, initial_capital: float = 1000.0):
        self.capital = initial_capital
        self.positions = []
        self.trades = []
        
    def run_backtest(self, historical_data: List[Dict]) -> Dict:
        """
        Run strategy on historical price data
        """
        strategy = GeminiConfluenceStrategy()
        
        for i, data_point in enumerate(historical_data):
            # Generate signal
            signal_data = strategy.generate_signal(data_point)
            
            if signal_data['signals']:
                top_signal = signal_data['signals'][0]
                
                # Check for exits
                self._check_exits(data_point)
                
                # Enter new position if strong signal
                if top_signal['confidence'] >= 70 and top_signal['zone'] != 'distribution':
                    self._enter_position(top_signal, data_point)
                    
        return self._calculate_metrics()
        
    def _enter_position(self, signal: Dict, data: Dict):
        """Record position entry"""
        position = {
            'entry_price': signal['entry'],
            'target': signal['target'],
            'stop': signal['stop'],
            'size': self.capital * 0.1,  # 10% position
            'entry_time': data['timestamp'],
            'zone': signal['zone']
        }
        self.positions.append(position)
        
    def _check_exits(self, data: Dict):
        """Check for stop/target hits"""
        price = data['price']
        for pos in self.positions[:]:
            if price >= pos['target']:
                pnl = (pos['target'] - pos['entry_price']) / pos['entry_price']
                self._close_position(pos, pnl, 'target', data['timestamp'])
            elif price <= pos['stop']:
                pnl = (pos['stop'] - pos['entry_price']) / pos['entry_price']
                self._close_position(pos, pnl, 'stop', data['timestamp'])
                
    def _close_position(self, position: Dict, pnl: float, reason: str, timestamp: str):
        """Record closed trade"""
        self.positions.remove(position)
        self.trades.append({
            'pnl': pnl,
            'reason': reason,
            'zone': position['zone'],
            'entry': position['entry_time'],
            'exit': timestamp
        })
        self.capital *= (1 + pnl)
        
    def _calculate_metrics(self) -> Dict:
        """Calculate performance metrics"""
        if not self.trades:
            return {'error': 'No trades executed'}
            
        pnls = [t['pnl'] for t in self.trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        
        return {
            'total_return': (self.capital / 1000 - 1) * 100,
            'num_trades': len(self.trades),
            'win_rate': len(wins) / len(pnls) * 100 if pnls else 0,
            'avg_win': np.mean(wins) * 100 if wins else 0,
            'avg_loss': np.mean(losses) * 100 if losses else 0,
            'profit_factor': abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else float('inf'),
            'max_drawdown': min(pnls) * 100 if pnls else 0,
            'sharpe': np.mean(pnls) / np.std(pnls) if len(pnls) > 1 and np.std(pnls) > 0 else 0,
            'trades': self.trades
        }


# ==================== LIVE SIGNAL GENERATOR ====================

def generate_live_signals(price_data: Dict) -> Dict:
    """
    Generate live trading signals from current market data
    Usage: Called every 15 minutes by GitHub Actions
    """
    strategy = GeminiConfluenceStrategy()
    
    # Enrich with calculated fields if needed
    if 'ema_50' not in price_data and 'prices' in price_data:
        prices = price_data['prices']
        price_data['ema_50'] = pd.Series(prices).ewm(span=50).mean().iloc[-1]
        price_data['ema_200'] = pd.Series(prices).ewm(span=200).mean().iloc[-1]
        
    return strategy.generate_signal(price_data)


if __name__ == '__main__':
    # Example usage
    print("=" * 60)
    print("GEMINI CONFLUENCE ALGORITHMS v1.0")
    print("Based on: Quantitative Reverse-Engineering Research")
    print("=" * 60)
    
    # Demo signal
    demo_data = {
        'symbol': 'BTCUSD',
        'price': 45000,
        'mvrv_z_score': -0.5,  # Green zone
        'rsi_weekly': 28,       # Oversold
        'price_vs_200w_ma': 0.92,  # Below 200W
        'funding_rate': -0.02,   # Negative = good for longs
        'volume_24h': 50000000,
        'volume_avg_30d': 20000000,
        'ema_50': 47000,
        'ema_200': 42000,
        'bb_middle': 46000,
        'bb_lower': 43000,
        'rsi_daily': 35,
        'trend': 'downtrend'
    }
    
    strategy = GeminiConfluenceStrategy()
    result = strategy.generate_signal(demo_data)
    
    print(f"\nDemo Signal for {result['asset']}:")
    print(f"Primary Recommendation: {result['primary_recommendation'].upper()}")
    print(f"Confidence: {result['highest_confidence']}%")
    print(f"\nAll Signals Detected:")
    for sig in result['signals']:
        print(f"  - {sig['zone']}: {sig['confidence']}% confidence")
        print(f"    Entry: ${sig['entry']:.2f} | Target: ${sig['target']:.2f} | Stop: ${sig['stop']:.2f}")
        print(f"    Rationale: {sig['rationale'][:80]}...")
