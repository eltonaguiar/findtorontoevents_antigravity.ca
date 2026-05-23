#!/usr/bin/env python3
"""
SPIKE PREDICTION ALGORITHM - Live Crypto & Forex
Predicts volatility spikes before they happen
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import time

@dataclass
class SpikeSignal:
    """A spike prediction signal"""
    asset: str
    direction: str  # 'LONG' or 'SHORT'
    confidence: float  # 0-100
    predicted_spike_time: datetime
    entry_price: float
    stop_loss: float
    take_profit: float
    rationale: str
    timestamp: datetime

class SpikePredictor:
    """
    Predicts volatility spikes using multi-factor analysis:
    1. Order book imbalance (buy/sell pressure)
    2. Funding rate anomalies
    3. Volume surge detection
    4. Correlation breakdown
    5. Time-of-day patterns
    """
    
    def __init__(self):
        self.signals: List[SpikeSignal] = []
        self.performance_log: List[Dict] = []
        
    def calculate_order_book_imbalance(self, bids: List[Tuple], asks: List[Tuple]) -> float:
        """
        Calculate order book imbalance
        Returns: -1 (all sell pressure) to +1 (all buy pressure)
        """
        bid_volume = sum(b[1] for b in bids[:10])  # Top 10 bids
        ask_volume = sum(a[1] for a in asks[:10])  # Top 10 asks
        
        if bid_volume + ask_volume == 0:
            return 0
        
        imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume)
        return imbalance
    
    def detect_volume_surge(self, current_volume: float, 
                           volume_sma_20: float,
                           volume_sma_50: float) -> Tuple[bool, float]:
        """
        Detect if volume is surging (potential spike precursor)
        Returns: (is_surging, surge_ratio)
        """
        if volume_sma_20 == 0:
            return False, 0
        
        surge_ratio = current_volume / volume_sma_20
        
        # Volume surge if > 2x 20-period average AND > 1.5x 50-period
        is_surging = surge_ratio > 2.0 and (current_volume / volume_sma_50) > 1.5
        
        return is_surging, surge_ratio
    
    def detect_funding_anomaly(self, funding_rate: float, 
                               funding_sma_30: float,
                               percentile_90: float) -> Tuple[bool, str]:
        """
        Detect funding rate anomalies (predicts reversals)
        Returns: (is_anomaly, direction_hint)
        """
        # Extreme positive funding = shorts paying longs = potential short squeeze
        # Extreme negative funding = longs paying shorts = potential long squeeze
        
        deviation = abs(funding_rate - funding_sma_30)
        
        if funding_rate > percentile_90:
            return True, "SHORT_SQUEEZE_RISK"  # Price may spike UP
        elif funding_rate < -percentile_90:
            return True, "LONG_SQUEEZE_RISK"  # Price may spike DOWN
        
        return False, "NORMAL"
    
    def calculate_volatility_regime(self, returns: pd.Series) -> Tuple[str, float]:
        """
        Determine current volatility regime
        Returns: (regime, current_vol)
        """
        current_vol = returns.std() * np.sqrt(252)  # Annualized
        historical_vol = returns.rolling(252).std().mean() * np.sqrt(252)
        
        vol_ratio = current_vol / historical_vol if historical_vol > 0 else 1
        
        if vol_ratio > 1.5:
            return "HIGH_VOL", current_vol
        elif vol_ratio < 0.7:
            return "LOW_VOL", current_vol
        else:
            return "NORMAL_VOL", current_vol
    
    def time_of_day_bias(self, hour_utc: int, asset: str) -> Tuple[str, float]:
        """
        Returns time-of-day bias for spike probability
        """
        if "USD" in asset or "EUR" in asset or "GBP" in asset:  # Forex
            # London open (8-9 UTC) and NY open (13-14 UTC)
            if hour_utc in [8, 9, 13, 14]:
                return "HIGH_ACTIVITY", 0.8
            # Asian session (lower volatility)
            elif hour_utc in [0, 1, 2, 3, 4, 5]:
                return "LOW_ACTIVITY", 0.3
        
        elif "BTC" in asset or "ETH" in asset:  # Crypto
            # US market hours affect crypto
            if hour_utc in [13, 14, 15, 16, 17, 18, 19, 20]:
                return "HIGH_ACTIVITY", 0.7
            # Weekend lower volume
            elif hour_utc in [0, 1, 2, 3, 4, 5, 6]:
                return "MEDIUM_ACTIVITY", 0.5
        
        return "NORMAL_ACTIVITY", 0.5
    
    def predict_spike(self, 
                     asset: str,
                     price_data: pd.DataFrame,
                     order_book: Dict = None,
                     funding_rate: float = None,
                     funding_history: pd.Series = None) -> Optional[SpikeSignal]:
        """
        Main prediction function
        Returns SpikeSignal if spike predicted, None otherwise
        """
        signals = []
        confidence_weights = []
        
        # 1. Volume surge detection
        if 'volume' in price_data.columns and len(price_data) >= 50:
            current_vol = price_data['volume'].iloc[-1]
            vol_sma_20 = price_data['volume'].rolling(20).mean().iloc[-1]
            vol_sma_50 = price_data['volume'].rolling(50).mean().iloc[-1]
            
            is_surging, surge_ratio = self.detect_volume_surge(
                current_vol, vol_sma_20, vol_sma_50
            )
            
            if is_surging:
                signals.append("VOLUME_SURGE")
                confidence_weights.append(min(surge_ratio / 3, 1.0))  # Cap at 1.0
        
        # 2. Volatility regime
        if len(price_data) >= 20:
            returns = price_data['close'].pct_change().dropna()
            regime, current_vol = self.calculate_volatility_regime(returns)
            
            if regime == "HIGH_VOL":
                signals.append("HIGH_VOLATILITY")
                confidence_weights.append(0.7)
        
        # 3. Funding anomaly (for crypto)
        if funding_rate is not None and funding_history is not None:
            funding_sma = funding_history.mean()
            percentile_90 = funding_history.quantile(0.9)
            
            is_anomaly, direction_hint = self.detect_funding_anomaly(
                funding_rate, funding_sma, percentile_90
            )
            
            if is_anomaly:
                signals.append(f"FUNDING_ANOMALY_{direction_hint}")
                confidence_weights.append(0.8)
        
        # 4. Order book imbalance
        if order_book:
            imbalance = self.calculate_order_book_imbalance(
                order_book.get('bids', []),
                order_book.get('asks', [])
            )
            
            if abs(imbalance) > 0.3:  # Strong imbalance
                signals.append(f"ORDER_BOOK_IMBALANCE_{'BUY' if imbalance > 0 else 'SELL'}")
                confidence_weights.append(abs(imbalance))
        
        # 5. Time of day
        current_hour = datetime.utcnow().hour
        time_bias, time_weight = self.time_of_day_bias(current_hour, asset)
        
        if time_bias == "HIGH_ACTIVITY":
            signals.append("HIGH_ACTIVITY_PERIOD")
            confidence_weights.append(time_weight)
        
        # Generate signal if we have enough evidence
        if len(signals) >= 2 and len(confidence_weights) >= 2:
            avg_confidence = np.mean(confidence_weights) * 100
            
            # Determine direction
            direction = "LONG"
            if any("SELL" in s or "SHORT" in s or "LONG_SQUEEZE" in s for s in signals):
                direction = "SHORT"
            
            # Calculate entry/stop/take profit
            current_price = price_data['close'].iloc[-1]
            atr = self.calculate_atr(price_data, 14)
            
            if direction == "LONG":
                stop_loss = current_price - (2 * atr)
                take_profit = current_price + (4 * atr)  # 2:1 RR
            else:
                stop_loss = current_price + (2 * atr)
                take_profit = current_price - (4 * atr)
            
            signal = SpikeSignal(
                asset=asset,
                direction=direction,
                confidence=min(avg_confidence, 95),  # Cap at 95
                predicted_spike_time=datetime.utcnow() + timedelta(minutes=30),
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                rationale=" | ".join(signals),
                timestamp=datetime.utcnow()
            )
            
            self.signals.append(signal)
            return signal
        
        return None
    
    def calculate_atr(self, data: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range"""
        high = data['high']
        low = data['low']
        close = data['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        
        return atr if not np.isnan(atr) else (high.iloc[-1] - low.iloc[-1]) * 0.5
    
    def update_performance(self, signal: SpikeSignal, exit_price: float, 
                          exit_time: datetime, reason: str):
        """Update performance tracking for a signal"""
        pnl = (exit_price - signal.entry_price) / signal.entry_price
        if signal.direction == "SHORT":
            pnl = -pnl
        
        result = {
            'asset': signal.asset,
            'direction': signal.direction,
            'entry': signal.entry_price,
            'exit': exit_price,
            'pnl': pnl,
            'confidence': signal.confidence,
            'rationale': signal.rationale,
            'exit_reason': reason,
            'duration_minutes': (exit_time - signal.timestamp).total_seconds() / 60
        }
        
        self.performance_log.append(result)
        return result
    
    def get_performance_summary(self) -> Dict:
        """Get performance statistics"""
        if not self.performance_log:
            return {'message': 'No trades yet'}
        
        pnls = [t['pnl'] for t in self.performance_log]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        
        return {
            'total_trades': len(pnls),
            'win_rate': len(wins) / len(pnls) if pnls else 0,
            'avg_win': np.mean(wins) if wins else 0,
            'avg_loss': np.mean(losses) if losses else 0,
            'profit_factor': abs(sum(wins) / sum(losses)) if sum(losses) != 0 else 0,
            'total_pnl': sum(pnls),
            'sharpe': np.mean(pnls) / np.std(pnls) * np.sqrt(252) if np.std(pnls) > 0 else 0
        }

# Live monitoring class
class LiveSpikeMonitor:
    """Monitors live markets and generates spike predictions"""
    
    def __init__(self, predictor: SpikePredictor):
        self.predictor = predictor
        self.active_signals: List[SpikeSignal] = []
        self.monitoring = False
    
    def start_monitoring(self, assets: List[str], interval_seconds: int = 60):
        """Start live monitoring loop"""
        self.monitoring = True
        print(f"🔴 LIVE SPIKE MONITORING STARTED")
        print(f"Assets: {', '.join(assets)}")
        print(f"Check interval: {interval_seconds}s")
        print("=" * 60)
        
        while self.monitoring:
            for asset in assets:
                self.check_asset(asset)
            
            self.check_signal_exits()
            self.print_status()
            
            time.sleep(interval_seconds)
    
    def check_asset(self, asset: str):
        """Check a single asset for spike conditions"""
        # In real implementation, fetch live data here
        # For now, placeholder
        pass
    
    def check_signal_exits(self):
        """Check if any active signals hit stop or target"""
        # In real implementation, check live prices
        pass
    
    def print_status(self):
        """Print current status"""
        summary = self.predictor.get_performance_summary()
        print(f"\n[{datetime.utcnow().isoformat()}]")
        print(f"Active Signals: {len(self.active_signals)}")
        print(f"Total Trades: {summary.get('total_trades', 0)}")
        if 'win_rate' in summary:
            print(f"Win Rate: {summary['win_rate']:.1%}")
            print(f"Total P&L: {summary['total_pnl']:.2%}")

if __name__ == "__main__":
    # Initialize
    predictor = SpikePredictor()
    monitor = LiveSpikeMonitor(predictor)
    
    print("🎯 SPIKE PREDICTION ALGORITHM")
    print("=" * 60)
    print("Ready to predict crypto and forex spikes")
    print("Run with live data feeds for actual predictions")
