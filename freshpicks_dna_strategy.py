"""
FreshPicks DNA Strategy - Live Signal Generator
================================================
A focused, trackable strategy for real Discord picks.

Based on Mercury analysis: funding_carry has 95% WR, +1.61% expectancy.
This strategy combines funding rate arbitrage with momentum confirmation.

Strategy DNA:
- Primary: Funding rate carry (8h funding rate differential)
- Confirm: 4h trend alignment (avoid counter-trend)
- Filter: Volume > 20-period average
- Entry: Market orders on signal
- RR: Minimum 1.5, target 2.0+

Usage:
    from freshpicks_dna_strategy import DNAPickGenerator
    
    dna = DNAPickGenerator()
    picks = dna.generate_picks()
    
    for pick in picks:
        send_to_discord(pick)
        track_pick(pick['tracking_id'])
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import random
import math

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('FreshPicksDNA')


@dataclass
class DNAPick:
    """A FreshPicks DNA pick with full tracking"""
    # Identification
    tracking_id: str
    timestamp: datetime
    symbol: str
    
    # Signal details
    direction: str  # 'long' or 'short'
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float  # % of portfolio
    
    # DNA components
    funding_rate: float
    funding_annualized: float
    trend_4h: str
    volume_ratio: float
    
    # Risk metrics
    rr: float
    confidence_score: float
    
    # Optional with defaults
    version: str = "1.0.0"
    exchange: str = "binance"
    expected_hold_hours: int = 8
    status: str = "active"  # active, filled, closed, expired
    discord_sent: bool = False
    discord_message_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'tracking_id': self.tracking_id,
            'timestamp': self.timestamp.isoformat(),
            'version': self.version,
            'symbol': self.symbol,
            'exchange': self.exchange,
            'direction': self.direction,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'position_size': self.position_size,
            'funding_rate': self.funding_rate,
            'funding_annualized': self.funding_annualized,
            'trend_4h': self.trend_4h,
            'volume_ratio': self.volume_ratio,
            'rr': self.rr,
            'confidence_score': self.confidence_score,
            'expected_hold_hours': self.expected_hold_hours,
            'status': self.status,
            'discord_sent': self.discord_sent,
            'discord_message_id': self.discord_message_id
        }


@dataclass
class MarketData:
    """Simulated market data structure"""
    symbol: str
    price: float
    funding_rate: float  # 8h funding rate
    volume_24h: float
    volume_avg_20d: float
    ema_20: float
    ema_50: float
    atr_14: float


class DNAPickGenerator:
    """
    FreshPicks DNA Strategy Generator
    
    Generates high-confidence picks based on funding rate + momentum.
    """
    
    def __init__(self):
        self.version = "1.0.0"
        self.symbols = ["BTC-USDT", "ETH-USDT", "SOL-USDT", "ADA-USDT"]
        self.exchange = "binance"
        
        # Strategy parameters
        self.min_funding_annualized = 0.10  # 10% annualized
        self.min_volume_ratio = 1.0  # Above average
        self.min_rr = 1.5
        self.target_rr = 2.0
        self.position_size = 0.02  # 2% per pick
        
        # Tracking
        self.pick_history: List[DNAPick] = []
        self._load_history()
    
    def _load_history(self):
        """Load pick history"""
        try:
            with open('dna_pick_history.json', 'r') as f:
                data = json.load(f)
                for p in data.get('picks', []):
                    pick = DNAPick(
                        tracking_id=p['tracking_id'],
                        timestamp=datetime.fromisoformat(p['timestamp']),
                        symbol=p['symbol'],
                        direction=p['direction'],
                        entry_price=p['entry_price'],
                        stop_loss=p['stop_loss'],
                        take_profit=p['take_profit'],
                        position_size=p['position_size'],
                        funding_rate=p['funding_rate'],
                        funding_annualized=p['funding_annualized'],
                        trend_4h=p['trend_4h'],
                        volume_ratio=p['volume_ratio'],
                        rr=p['rr'],
                        confidence_score=p['confidence_score'],
                        version=p.get('version', '1.0.0'),
                        exchange=p.get('exchange', 'binance'),
                        expected_hold_hours=p.get('expected_hold_hours', 8),
                        status=p.get('status', 'active'),
                        discord_sent=p.get('discord_sent', False),
                        discord_message_id=p.get('discord_message_id')
                    )
                    self.pick_history.append(pick)
        except FileNotFoundError:
            pass
    
    def _save_history(self):
        """Save pick history"""
        data = {
            'last_update': datetime.now().isoformat(),
            'total_picks': len(self.pick_history),
            'picks': [p.to_dict() for p in self.pick_history[-500:]]  # Keep last 500
        }
        with open('dna_pick_history.json', 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def fetch_market_data(self, symbol: str) -> Optional[MarketData]:
        """
        Fetch market data for symbol
        
        In production, this would call exchange API.
        For now, simulates realistic data.
        """
        try:
            # In production:
            # return self._fetch_from_exchange(symbol)
            
            # Simulation for testing:
            base_prices = {
                "BTC-USDT": 65000,
                "ETH-USDT": 3500,
                "SOL-USDT": 150,
                "ADA-USDT": 0.50
            }
            
            base_price = base_prices.get(symbol, 100)
            
            # Random variation
            price = base_price * (1 + random.gauss(0, 0.02))
            
            # Funding rate (-0.1% to +0.1% for 8h = -10.95% to +10.95% annualized)
            funding = random.uniform(-0.001, 0.001)
            
            # Volume (0.8x to 2.0x average)
            vol_ratio = random.uniform(0.8, 2.0)
            
            # EMAs
            ema20 = price * (1 + random.gauss(0, 0.05))
            ema50 = price * (1 + random.gauss(0, 0.10))
            
            # ATR (~2% of price)
            atr = price * 0.02
            
            return MarketData(
                symbol=symbol,
                price=price,
                funding_rate=funding,
                volume_24h=1000000 * vol_ratio,
                volume_avg_20d=1000000,
                ema_20=ema20,
                ema_50=ema50,
                atr_14=atr
            )
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None
    
    def calculate_signal(self, data: MarketData) -> Optional[Dict[str, Any]]:
        """
        Calculate DNA signal for market data
        
        Returns signal dict or None if no valid signal
        """
        # Funding rate signal
        funding_annual = data.funding_rate * 3 * 365  # 8h * 3 = daily, * 365 = annual
        
        # Only trade if funding rate is significant (>10% annualized)
        if abs(funding_annual) < self.min_funding_annualized:
            return None
        
        # Direction: short if positive funding (you pay), long if negative (you get paid)
        direction = "short" if data.funding_rate > 0 else "long"
        
        # Trend confirmation (don't fight the trend)
        trend = "up" if data.ema_20 > data.ema_50 else "down"
        
        # Only take shorts in downtrend, longs in uptrend
        if direction == "short" and trend != "down":
            return None
        if direction == "long" and trend != "up":
            return None
        
        # Volume check
        volume_ratio = data.volume_24h / data.volume_avg_20d
        if volume_ratio < self.min_volume_ratio:
            return None
        
        # Calculate levels
        entry = data.price
        
        # Stop loss: 1.5x ATR for shorts, 1.5x ATR below for longs
        if direction == "short":
            stop = entry + (data.atr_14 * 1.5)
            target = entry - (data.atr_14 * 3)  # 2:1 RR
        else:
            stop = entry - (data.atr_14 * 1.5)
            target = entry + (data.atr_14 * 3)
        
        # Calculate RR
        risk = abs(entry - stop)
        reward = abs(target - entry)
        rr = reward / risk if risk > 0 else 0
        
        if rr < self.min_rr:
            return None
        
        # Confidence score
        confidence = 0.5
        
        # Higher confidence for larger funding rates
        if abs(funding_annual) > 0.20:  # >20% annualized
            confidence += 0.25
        elif abs(funding_annual) > 0.15:
            confidence += 0.15
        
        # Higher confidence for strong trend alignment
        ema_diff = abs(data.ema_20 - data.ema_50) / data.price
        if ema_diff > 0.05:  # Strong trend
            confidence += 0.15
        
        # Higher confidence for high volume
        if volume_ratio > 1.5:
            confidence += 0.10
        
        return {
            'direction': direction,
            'entry': entry,
            'stop': stop,
            'target': target,
            'rr': rr,
            'confidence': min(confidence, 1.0),
            'funding_rate': data.funding_rate,
            'funding_annualized': funding_annual,
            'trend': trend,
            'volume_ratio': volume_ratio
        }
    
    def generate_picks(self) -> List[DNAPick]:
        """
        Generate DNA picks for all symbols
        
        Returns list of valid picks ready for Discord
        """
        picks = []
        
        logger.info(f"[DNA] Generating picks for {len(self.symbols)} symbols...")
        
        for symbol in self.symbols:
            # Fetch market data
            data = self.fetch_market_data(symbol)
            if not data:
                continue
            
            # Calculate signal
            signal = self.calculate_signal(data)
            if not signal:
                continue
            
            # Generate tracking ID
            tracking_id = f"DNA-{datetime.now().strftime('%Y%m%d')}-{symbol.replace('-', '')}-{random.randint(1000, 9999)}"
            
            # Create pick
            pick = DNAPick(
                tracking_id=tracking_id,
                timestamp=datetime.now(),
                symbol=symbol,
                direction=signal['direction'],
                entry_price=round(signal['entry'], 8),
                stop_loss=round(signal['stop'], 8),
                take_profit=round(signal['target'], 8),
                position_size=self.position_size,
                funding_rate=round(signal['funding_rate'], 6),
                funding_annualized=round(signal['funding_annualized'], 4),
                trend_4h=signal['trend'],
                volume_ratio=round(signal['volume_ratio'], 2),
                rr=round(signal['rr'], 2),
                confidence_score=round(signal['confidence'], 2)
            )
            
            picks.append(pick)
            logger.info(f"[DNA] Generated pick: {tracking_id} {symbol} {signal['direction']} "
                       f"RR:{signal['rr']:.2f} Conf:{signal['confidence']:.0%}")
        
        # Save to history
        self.pick_history.extend(picks)
        self._save_history()
        
        # Sort by confidence
        picks.sort(key=lambda x: x.confidence_score, reverse=True)
        
        logger.info(f"[DNA] Generated {len(picks)} picks")
        return picks
    
    def get_pick_by_id(self, tracking_id: str) -> Optional[DNAPick]:
        """Get pick by tracking ID"""
        for pick in self.pick_history:
            if pick.tracking_id == tracking_id:
                return pick
        return None
    
    def update_pick_status(self, tracking_id: str, status: str, **kwargs):
        """Update pick status"""
        pick = self.get_pick_by_id(tracking_id)
        if pick:
            pick.status = status
            for key, value in kwargs.items():
                if hasattr(pick, key):
                    setattr(pick, key, value)
            self._save_history()
            logger.info(f"[DNA] Updated {tracking_id} -> {status}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get DNA strategy statistics"""
        total = len(self.pick_history)
        
        if total == 0:
            return {'message': 'No picks yet'}
        
        # Recent picks (last 30 days)
        cutoff = datetime.now() - timedelta(days=30)
        recent = [p for p in self.pick_history if p.timestamp > cutoff]
        
        # By direction
        longs = sum(1 for p in recent if p.direction == 'long')
        shorts = sum(1 for p in recent if p.direction == 'short')
        
        # By status
        active = sum(1 for p in recent if p.status == 'active')
        closed = sum(1 for p in recent if p.status == 'closed')
        
        # Avg confidence
        avg_conf = sum(p.confidence_score for p in recent) / len(recent) if recent else 0
        
        return {
            'total_picks_all_time': total,
            'picks_last_30d': len(recent),
            'breakdown': {
                'longs': longs,
                'shorts': shorts,
                'active': active,
                'closed': closed
            },
            'avg_confidence': round(avg_conf, 2),
            'last_pick': recent[-1].timestamp.isoformat() if recent else None
        }


# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("FRESHPICKS DNA STRATEGY - Live Pick Generator")
    print("=" * 80)
    
    dna = DNAPickGenerator()
    
    # Generate picks
    picks = dna.generate_picks()
    
    print(f"\nGenerated {len(picks)} picks:\n")
    
    for pick in picks:
        print(f"Tracking ID: {pick.tracking_id}")
        print(f"Symbol: {pick.symbol}")
        print(f"Direction: {pick.direction.upper()}")
        print(f"Entry: {pick.entry_price}")
        print(f"Stop: {pick.stop_loss}")
        print(f"Target: {pick.take_profit}")
        print(f"RR: {pick.rr}")
        print(f"Confidence: {pick.confidence_score:.0%}")
        print(f"Funding: {pick.funding_annualized:.2%} annualized")
        print(f"Trend: {pick.trend_4h}")
        print("-" * 80)
    
    # Stats
    print("\n[STATS]")
    print(json.dumps(dna.get_stats(), indent=2))
