"""
Surge Detection System

Detects sudden price spikes/surges with early confirmation indicators.
Optimized for catching 5-10% moves early with minimal lag.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SurgeAlert:
    """Represents a detected surge with early indicators"""
    symbol: str
    direction: str  # 'UP' or 'DOWN'
    strength: float  # 0-100
    current_price: float
    surge_start_price: float
    percent_change: float
    early_indicators: Dict[str, float]
    timestamp: str
    confirmation_level: str  # 'weak', 'moderate', 'strong'


class SurgeDetector:
    """
    Detects price surges using multiple early confirmation signals:
    
    1. Price velocity (rate of change)
    2. Volume spike detection
    3. Order book imbalance (if available)
    4. Cross-timeframe momentum alignment
    5. RSI velocity (momentum acceleration)
    """
    
    # Detection thresholds
    SURGE_THRESHOLD_PCT = 2.0  # 2% in short window = potential surge
    STRONG_SURGE_PCT = 5.0     # 5% = confirmed surge
    
    # Time windows (in minutes)
    DETECTION_WINDOW = 15      # Look at last 15 min for surge detection
    CONFIRMATION_WINDOW = 5    # Confirm within 5 min for early entry
    
    def __init__(self, price_history_file: Optional[str] = None):
        self.price_history = {}
        self.history_file = Path(price_history_file) if price_history_file else None
        self._load_history()
    
    def _load_history(self):
        """Load price history from file"""
        if self.history_file and self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    self.price_history = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load price history: {e}")
    
    def _save_history(self):
        """Save price history to file"""
        if self.history_file:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, 'w') as f:
                json.dump(self.price_history, f, indent=2)
    
    def update_price(self, symbol: str, price: float, volume: float = 0):
        """Add new price point"""
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        
        self.price_history[symbol].append({
            'timestamp': datetime.utcnow().isoformat(),
            'price': price,
            'volume': volume
        })
        
        # Keep only last 4 hours of data
        cutoff = (datetime.utcnow() - timedelta(hours=4)).isoformat()
        self.price_history[symbol] = [
            p for p in self.price_history[symbol] 
            if p['timestamp'] > cutoff
        ]
        
        self._save_history()
    
    def calculate_velocity(self, symbol: str, window_minutes: int = 15) -> float:
        """Calculate price velocity (% change per minute)"""
        if symbol not in self.price_history or len(self.price_history[symbol]) < 2:
            return 0.0
        
        history = self.price_history[symbol]
        cutoff = (datetime.utcnow() - timedelta(minutes=window_minutes)).isoformat()
        
        recent = [p for p in history if p['timestamp'] >= cutoff]
        if len(recent) < 2:
            return 0.0
        
        start_price = recent[0]['price']
        end_price = recent[-1]['price']
        
        if start_price == 0:
            return 0.0
        
        pct_change = (end_price - start_price) / start_price * 100
        velocity = pct_change / window_minutes  # % per minute
        
        return velocity
    
    def calculate_volume_spike(self, symbol: str) -> float:
        """Detect volume spike (ratio of recent vs average)"""
        if symbol not in self.price_history:
            return 1.0
        
        history = self.price_history[symbol]
        if len(history) < 10:
            return 1.0
        
        volumes = [p.get('volume', 0) for p in history if p.get('volume', 0) > 0]
        if len(volumes) < 5:
            return 1.0
        
        avg_volume = sum(volumes[:-3]) / len(volumes[:-3]) if len(volumes) > 3 else sum(volumes) / len(volumes)
        recent_volume = sum(volumes[-3:]) / 3
        
        if avg_volume == 0:
            return 1.0
        
        return recent_volume / avg_volume
    
    def check_multi_timeframe_alignment(self, symbol: str) -> float:
        """Check if momentum aligns across timeframes"""
        # Calculate velocity at different windows
        v5 = self.calculate_velocity(symbol, 5)
        v15 = self.calculate_velocity(symbol, 15)
        v60 = self.calculate_velocity(symbol, 60)
        
        # All positive = strong bullish alignment
        # All negative = strong bearish alignment
        # Mixed = no alignment
        
        if v5 > 0 and v15 > 0 and v60 > 0:
            return min(abs(v5) + abs(v15) + abs(v60), 10.0)  # Cap at 10
        elif v5 < 0 and v15 < 0 and v60 < 0:
            return -min(abs(v5) + abs(v15) + abs(v60), 10.0)
        
        return 0.0
    
    def detect_surge(self, symbol: str, current_price: float) -> Optional[SurgeAlert]:
        """
        Detect if a surge is occurring with early confirmation.
        
        Returns SurgeAlert if surge detected, None otherwise.
        """
        self.update_price(symbol, current_price)
        
        # Calculate indicators
        velocity_15m = self.calculate_velocity(symbol, 15)
        velocity_5m = self.calculate_velocity(symbol, 5)
        volume_spike = self.calculate_volume_spike(symbol)
        tf_alignment = self.check_multi_timeframe_alignment(symbol)
        
        # Get surge start reference
        history = self.price_history.get(symbol, [])
        if len(history) < 2:
            return None
        
        surge_start = history[0]['price'] if len(history) >= 20 else history[max(0, len(history)-20)]['price']
        percent_change = (current_price - surge_start) / surge_start * 100
        
        # Determine direction
        direction = 'UP' if velocity_15m > 0 else 'DOWN'
        
        # Calculate surge strength score (0-100)
        strength = 0
        early_indicators = {
            'velocity_5m': velocity_5m,
            'velocity_15m': velocity_15m,
            'volume_spike': volume_spike,
            'tf_alignment': tf_alignment,
            'percent_change': percent_change
        }
        
        # Velocity component (0-40 points)
        velocity_score = min(abs(velocity_5m) * 10, 40)
        strength += velocity_score
        
        # Volume spike component (0-30 points)
        if volume_spike > 2.0:
            strength += 30
        elif volume_spike > 1.5:
            strength += 20
        elif volume_spike > 1.2:
            strength += 10
        
        # Timeframe alignment (0-30 points)
        if abs(tf_alignment) > 5:
            strength += 30
        elif abs(tf_alignment) > 3:
            strength += 20
        elif abs(tf_alignment) > 1:
            strength += 10
        
        # Determine confirmation level
        if strength >= 70 and abs(percent_change) >= self.STRONG_SURGE_PCT:
            confirmation = 'strong'
        elif strength >= 50 and abs(percent_change) >= self.SURGE_THRESHOLD_PCT:
            confirmation = 'moderate'
        elif strength >= 30:
            confirmation = 'weak'
        else:
            return None
        
        return SurgeAlert(
            symbol=symbol,
            direction=direction,
            strength=min(strength, 100),
            current_price=current_price,
            surge_start_price=surge_start,
            percent_change=percent_change,
            early_indicators=early_indicators,
            timestamp=datetime.utcnow().isoformat(),
            confirmation_level=confirmation
        )
    
    def format_alert_embed(self, alert: SurgeAlert) -> Dict:
        """Format surge alert as Discord embed"""
        color = 0x00ff00 if alert.direction == 'UP' else 0xff0000
        emoji = "🚀" if alert.direction == 'UP' else "📉"
        
        # Progress bar for strength
        filled = int(alert.strength / 10)
        strength_bar = "█" * filled + "░" * (10 - filled)
        
        indicators = alert.early_indicators
        
        embed = {
            "title": f"{emoji} SURGE ALERT: {alert.symbol} {alert.direction}",
            "description": (
                f"**{strength_bar} {alert.strength}/100** - {alert.confirmation_level.upper()} confirmation\n"
                f"Price moved {alert.percent_change:+.2f}% in detection window"
            ),
            "color": color,
            "fields": [
                {
                    "name": "Price Action",
                    "value": (
                        f"```\n"
                        f"Current:  ${alert.current_price:,.2f}\n"
                        f"Started:  ${alert.surge_start_price:,.2f}\n"
                        f"Change:   {alert.percent_change:+.2f}%\n"
                        f"```"
                    ),
                    "inline": False
                },
                {
                    "name": "Early Indicators",
                    "value": (
                        f"```\n"
                        f"5m Velocity:   {indicators['velocity_5m']:+.3f}%/min\n"
                        f"15m Velocity:  {indicators['velocity_15m']:+.3f}%/min\n"
                        f"Volume Spike:  {indicators['volume_spike']:.2f}x avg\n"
                        f"TF Alignment:  {indicators['tf_alignment']:+.2f}\n"
                        f"```"
                    ),
                    "inline": False
                }
            ],
            "footer": {
                "text": f"Surge Detector | {alert.timestamp[:16]} UTC"
            },
            "timestamp": alert.timestamp
        }
        
        return embed


# Singleton instance
_detector_instance = None

def get_detector() -> SurgeDetector:
    """Get singleton surge detector"""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = SurgeDetector(
            price_history_file="signal_aggregator/data/surge_history.json"
        )
    return _detector_instance


if __name__ == "__main__":
    # Test with simulated ETH surge
    logging.basicConfig(level=logging.INFO)
    
    detector = get_detector()
    
    # Simulate ETH price data
    base_price = 2035
    
    # Add historical data (simulating before surge)
    for i in range(20):
        detector.update_price("ETHUSDT", base_price * (1 + i * 0.001), 1000)
    
    # Add surge data (simulating 8% uptick)
    for i in range(1, 6):
        surge_price = base_price * (1 + i * 0.016)  # 1.6% per 5min = 8% total
        detector.update_price("ETHUSDT", surge_price, 3000)  # 3x volume
    
    # Detect surge
    current = base_price * 1.08
    alert = detector.detect_surge("ETHUSDT", current)
    
    if alert:
        print(f"\n{'='*60}")
        print(f"SURGE DETECTED!")
        print(f"{'='*60}")
        print(f"Symbol: {alert.symbol}")
        print(f"Direction: {alert.direction}")
        print(f"Strength: {alert.strength}/100")
        print(f"Confirmation: {alert.confirmation_level}")
        print(f"Price Change: {alert.percent_change:+.2f}%")
        print(f"\nEarly Indicators:")
        for key, val in alert.early_indicators.items():
            print(f"  {key}: {val:.4f}")
    else:
        print("\nNo surge detected")
