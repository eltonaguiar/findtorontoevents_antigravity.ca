"""
KIMI_FEB172026 - Signal Tracker
Tracks all generated signals and validates outcomes against live market data
Records: Entry → TP Hit / SL Hit / Time Exit / Manual Close
"""

import json
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import pandas as pd
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KIMI_TRACKER")

@dataclass
class TrackedSignal:
    """Complete signal tracking record"""
    signal_id: str
    timestamp: datetime
    symbol: str
    asset_class: str  # crypto, forex, stock, meme
    algorithm: str
    direction: str  # LONG or SHORT
    entry_price: float
    take_profit: float
    stop_loss: float
    confidence: float
    win_probability: float
    metadata: Dict
    
    # Outcome tracking
    status: str = "OPEN"  # OPEN, TP_HIT, SL_HIT, TIME_EXIT, EXPIRED
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    exit_reason: Optional[str] = None
    pnl_pct: float = 0.0
    pnl_dollar: float = 0.0
    time_to_exit_minutes: Optional[float] = None
    
    # Validation
    prediction_correct: bool = False
    max_favorable_excursion: float = 0.0  # Max profit % reached
    max_adverse_excursion: float = 0.0    # Max loss % reached
    

class SignalTracker:
    """
    Tracks signal lifecycle from generation to outcome
    Validates against live market data
    """
    
    def __init__(self, data_dir: str = "KIMI_FEB172026/data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.tracking_file = self.data_dir / "signal_tracking.json"
        self.active_signals: Dict[str, TrackedSignal] = {}
        self.completed_signals: List[TrackedSignal] = []
        
        # Binance API for price checking
        self.binance_base = "https://api.binance.com"
        self.binance_futures = "https://fapi.binance.com"
        
        self.load_tracking_data()
    
    def load_tracking_data(self):
        """Load existing tracking data"""
        if self.tracking_file.exists():
            with open(self.tracking_file, 'r') as f:
                data = json.load(f)
                
            for sig_data in data.get("completed", []):
                signal = self._dict_to_signal(sig_data)
                self.completed_signals.append(signal)
            
            for sig_id, sig_data in data.get("active", {}).items():
                signal = self._dict_to_signal(sig_data)
                self.active_signals[sig_id] = signal
            
            logger.info(f"Loaded {len(self.completed_signals)} completed, {len(self.active_signals)} active signals")
    
    def save_tracking_data(self):
        """Save tracking data to file"""
        data = {
            "active": {sid: self._signal_to_dict(s) for sid, s in self.active_signals.items()},
            "completed": [self._signal_to_dict(s) for s in self.completed_signals],
            "last_updated": datetime.now().isoformat()
        }
        
        with open(self.tracking_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def _signal_to_dict(self, signal: TrackedSignal) -> Dict:
        """Convert signal to dictionary"""
        d = asdict(signal)
        # Convert datetime to string
        d['timestamp'] = signal.timestamp.isoformat()
        if signal.exit_time:
            d['exit_time'] = signal.exit_time.isoformat()
        return d
    
    def _dict_to_signal(self, data: Dict) -> TrackedSignal:
        """Convert dictionary to signal"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        if data.get('exit_time'):
            data['exit_time'] = datetime.fromisoformat(data['exit_time'])
        return TrackedSignal(**data)
    
    def track_signal(self, signal_data: Dict) -> str:
        """
        Start tracking a new signal
        """
        signal_id = f"{signal_data['symbol']}_{signal_data['algorithm']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        signal = TrackedSignal(
            signal_id=signal_id,
            timestamp=datetime.now(),
            symbol=signal_data['symbol'],
            asset_class=signal_data.get('asset_class', 'crypto'),
            algorithm=signal_data['algorithm'],
            direction=signal_data['direction'],
            entry_price=signal_data['entry_price'],
            take_profit=signal_data['take_profit'],
            stop_loss=signal_data['stop_loss'],
            confidence=signal_data.get('confidence', 0.5),
            win_probability=signal_data.get('win_probability', 0.5),
            metadata=signal_data.get('metadata', {})
        )
        
        self.active_signals[signal_id] = signal
        self.save_tracking_data()
        
        logger.info(f"Tracking new signal: {signal_id} - {signal.symbol} {signal.direction}")
        return signal_id
    
    async def check_all_outcomes(self):
        """
        Check all active signals against live market data
        Updates status if TP/SL hit or time expired
        """
        if not self.active_signals:
            return
        
        logger.info(f"Checking outcomes for {len(self.active_signals)} active signals...")
        
        for signal_id in list(self.active_signals.keys()):
            signal = self.active_signals[signal_id]
            
            try:
                # Get current price
                current_price = await self._get_current_price(signal.symbol)
                
                if not current_price:
                    continue
                
                # Check exit conditions
                exit_result = self._check_exit_conditions(signal, current_price)
                
                if exit_result['exited']:
                    # Signal has exited
                    self._complete_signal(signal_id, exit_result)
                    
            except Exception as e:
                logger.error(f"Error checking {signal_id}: {e}")
    
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price from Binance"""
        try:
            # Normalize symbol for Binance
            binance_symbol = symbol.replace('-USD', 'USDT').replace('/', '')
            
            url = f"{self.binance_base}/api/v3/ticker/price"
            params = {"symbol": binance_symbol}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return float(data.get('price', 0))
                    
            # Try futures if spot fails
            url = f"{self.binance_futures}/fapi/v1/ticker/price"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return float(data.get('price', 0))
                        
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
        
        return None
    
    def _check_exit_conditions(self, signal: TrackedSignal, current_price: float) -> Dict:
        """
        Check if signal has hit TP, SL, or time exit
        Returns exit information
        """
        entry = signal.entry_price
        tp = signal.take_profit
        sl = signal.stop_loss
        direction = signal.direction
        
        result = {
            'exited': False,
            'exit_price': None,
            'exit_reason': None,
            'pnl_pct': 0.0
        }
        
        # Calculate current P&L
        if direction == "LONG":
            pnl_pct = (current_price - entry) / entry * 100
            
            # Check TP
            if current_price >= tp:
                result['exited'] = True
                result['exit_price'] = tp
                result['exit_reason'] = "TP_HIT"
                result['pnl_pct'] = (tp - entry) / entry * 100
            
            # Check SL
            elif current_price <= sl:
                result['exited'] = True
                result['exit_price'] = sl
                result['exit_reason'] = "SL_HIT"
                result['pnl_pct'] = (sl - entry) / entry * 100
                
        else:  # SHORT
            pnl_pct = (entry - current_price) / entry * 100
            
            # Check TP (price went down for short)
            if current_price <= tp:
                result['exited'] = True
                result['exit_price'] = tp
                result['exit_reason'] = "TP_HIT"
                result['pnl_pct'] = (entry - tp) / entry * 100
            
            # Check SL (price went up for short)
            elif current_price >= sl:
                result['exited'] = True
                result['exit_price'] = sl
                result['exit_reason'] = "SL_HIT"
                result['pnl_pct'] = (entry - sl) / entry * 100
        
        # Check time exit (24 hour default)
        time_elapsed = (datetime.now() - signal.timestamp).total_seconds() / 3600
        if time_elapsed >= 24 and not result['exited']:
            result['exited'] = True
            result['exit_price'] = current_price
            result['exit_reason'] = "TIME_EXIT"
            result['pnl_pct'] = pnl_pct
        
        return result
    
    def _complete_signal(self, signal_id: str, exit_result: Dict):
        """Move signal from active to completed"""
        signal = self.active_signals.pop(signal_id)
        
        # Update signal with outcome
        signal.status = exit_result['exit_reason']
        signal.exit_price = exit_result['exit_price']
        signal.exit_time = datetime.now()
        signal.exit_reason = exit_result['exit_reason']
        signal.pnl_pct = exit_result['pnl_pct']
        signal.time_to_exit_minutes = (signal.exit_time - signal.timestamp).total_seconds() / 60
        
        # Prediction was correct if P&L > 0
        signal.prediction_correct = signal.pnl_pct > 0
        
        # Add to completed
        self.completed_signals.append(signal)
        self.save_tracking_data()
        
        logger.info(f"Signal completed: {signal_id} - {signal.exit_reason} - P&L: {signal.pnl_pct:+.2f}%")
    
    def update_max_excursions(self, signal_id: str, current_price: float):
        """Update max favorable/adverse excursion for a signal"""
        if signal_id not in self.active_signals:
            return
        
        signal = self.active_signals[signal_id]
        entry = signal.entry_price
        
        if signal.direction == "LONG":
            current_pnl = (current_price - entry) / entry * 100
        else:
            current_pnl = (entry - current_price) / entry * 100
        
        # Update excursions
        signal.max_favorable_excursion = max(signal.max_favorable_excursion, current_pnl)
        signal.max_adverse_excursion = min(signal.max_adverse_excursion, current_pnl)
        
        self.save_tracking_data()
    
    def get_performance_stats(self, days: int = 7, algorithm: Optional[str] = None,
                             asset_class: Optional[str] = None) -> Dict:
        """
        Get performance statistics for completed signals
        """
        # Filter signals
        cutoff = datetime.now() - timedelta(days=days)
        signals = [s for s in self.completed_signals if s.exit_time and s.exit_time >= cutoff]
        
        if algorithm:
            signals = [s for s in signals if s.algorithm == algorithm]
        
        if asset_class:
            signals = [s for s in signals if s.asset_class == asset_class]
        
        if not signals:
            return {"error": "No completed signals in period"}
        
        # Calculate stats
        wins = [s for s in signals if s.pnl_pct > 0]
        losses = [s for s in signals if s.pnl_pct <= 0]
        
        win_rate = len(wins) / len(signals) if signals else 0
        
        pnls = [s.pnl_pct for s in signals]
        total_pnl = sum(pnls)
        avg_pnl = np.mean(pnls)
        
        # Sharpe (simplified)
        sharpe = 0
        if len(pnls) > 1 and np.std(pnls) > 0:
            sharpe = (np.mean(pnls) / np.std(pnls)) * np.sqrt(365 / days)
        
        # Profit factor
        gross_profit = sum(s.pnl_pct for s in wins)
        gross_loss = abs(sum(s.pnl_pct for s in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # By exit reason
        tp_hits = len([s for s in signals if s.exit_reason == "TP_HIT"])
        sl_hits = len([s for s in signals if s.exit_reason == "SL_HIT"])
        time_exits = len([s for s in signals if s.exit_reason == "TIME_EXIT"])
        
        # Average time to exit
        avg_time = np.mean([s.time_to_exit_minutes for s in signals if s.time_to_exit_minutes])
        
        return {
            "period_days": days,
            "total_signals": len(signals),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(win_rate, 4),
            "total_pnl_pct": round(total_pnl, 4),
            "avg_pnl_pct": round(avg_pnl, 4),
            "sharpe_ratio": round(sharpe, 4),
            "profit_factor": round(profit_factor, 4),
            "tp_hits": tp_hits,
            "sl_hits": sl_hits,
            "time_exits": time_exits,
            "avg_time_to_exit_min": round(avg_time, 2) if avg_time else None,
            "best_trade": round(max(pnls), 4),
            "worst_trade": round(min(pnls), 4),
            "algorithm": algorithm,
            "asset_class": asset_class
        }
    
    def get_algorithm_performance(self) -> List[Dict]:
        """Get performance breakdown by algorithm"""
        if not self.completed_signals:
            return []
        
        algo_stats = {}
        
        for signal in self.completed_signals:
            algo = signal.algorithm
            if algo not in algo_stats:
                algo_stats[algo] = {
                    "signals": [],
                    "wins": 0,
                    "losses": 0,
                    "total_pnl": 0
                }
            
            algo_stats[algo]["signals"].append(signal)
            algo_stats[algo]["total_pnl"] += signal.pnl_pct
            
            if signal.pnl_pct > 0:
                algo_stats[algo]["wins"] += 1
            else:
                algo_stats[algo]["losses"] += 1
        
        # Create summary
        results = []
        for algo, stats in algo_stats.items():
            total = len(stats["signals"])
            results.append({
                "algorithm": algo,
                "total_signals": total,
                "wins": stats["wins"],
                "losses": stats["losses"],
                "win_rate": round(stats["wins"] / total, 4) if total > 0 else 0,
                "total_pnl_pct": round(stats["total_pnl"], 4),
                "avg_pnl_pct": round(stats["total_pnl"] / total, 4) if total > 0 else 0
            })
        
        # Sort by win rate
        results.sort(key=lambda x: x["win_rate"], reverse=True)
        return results
    
    def export_for_analysis(self, filepath: str):
        """Export all completed signals to CSV for analysis"""
        if not self.completed_signals:
            logger.warning("No completed signals to export")
            return
        
        data = []
        for signal in self.completed_signals:
            data.append({
                "signal_id": signal.signal_id,
                "timestamp": signal.timestamp,
                "symbol": signal.symbol,
                "asset_class": signal.asset_class,
                "algorithm": signal.algorithm,
                "direction": signal.direction,
                "entry_price": signal.entry_price,
                "take_profit": signal.take_profit,
                "stop_loss": signal.stop_loss,
                "confidence": signal.confidence,
                "win_probability": signal.win_probability,
                "status": signal.status,
                "exit_price": signal.exit_price,
                "exit_reason": signal.exit_reason,
                "pnl_pct": signal.pnl_pct,
                "time_to_exit_min": signal.time_to_exit_minutes,
                "prediction_correct": signal.prediction_correct
            })
        
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
        logger.info(f"Exported {len(data)} signals to {filepath}")


# =============================================================================
# Entry point for testing
# =============================================================================
async def main():
    """Test the signal tracker"""
    tracker = SignalTracker()
    
    print("=" * 80)
    print("KIMI_FEB172026 - Signal Tracker Test")
    print("=" * 80)
    
    # Test tracking a signal
    test_signal = {
        "symbol": "BTC-USD",
        "asset_class": "crypto",
        "algorithm": "pump-detector-scout",
        "direction": "LONG",
        "entry_price": 96500.0,
        "take_profit": 98500.0,
        "stop_loss": 95500.0,
        "confidence": 0.85,
        "win_probability": 0.72,
        "metadata": {"volume_ratio": 5.5}
    }
    
    signal_id = tracker.track_signal(test_signal)
    print(f"\nTracked signal: {signal_id}")
    print(f"Active signals: {len(tracker.active_signals)}")
    
    # Check outcomes
    print("\nChecking outcomes...")
    await tracker.check_all_outcomes()
    
    # Get stats
    print("\nPerformance Stats (7 days):")
    stats = tracker.get_performance_stats(days=7)
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\nAlgorithm Performance:")
    algo_perf = tracker.get_algorithm_performance()
    for algo in algo_perf[:5]:
        print(f"  {algo['algorithm']}: WR={algo['win_rate']:.1%}, PnL={algo['total_pnl_pct']:+.2f}%")


if __name__ == "__main__":
    asyncio.run(main())
