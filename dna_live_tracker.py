"""
DNA Live Tracker - Pick Performance Monitoring
==============================================
Tracks DNA picks from generation to close.

Features:
- Real-time PnL tracking
- Performance attribution
- Auto status updates
- Integration with consistency tracker

Usage:
    from dna_live_tracker import DNALiveTracker
    
    tracker = DNALiveTracker()
    
    # Update pick with market price
    tracker.update_pick_price('DNA-20260303-BTC-1234', 66000)
    
    # Get performance report
    report = tracker.get_performance_report()
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('DNATracker')


@dataclass
class PickPerformance:
    """Performance tracking for a single pick"""
    tracking_id: str
    symbol: str
    direction: str
    entry_price: float
    current_price: float
    stop_loss: float
    take_profit: float
    
    # PnL tracking
    pnl_percent: float = 0.0
    pnl_usd: float = 0.0
    max_profit: float = 0.0
    max_drawdown: float = 0.0
    
    # Status
    status: str = "active"  # active, tp_hit, sl_hit, closed, expired
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    exit_time: Optional[datetime] = None
    
    # Metadata
    open_time: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)
    hours_open: float = 0.0
    
    def update_price(self, price: float):
        """Update with current market price"""
        self.current_price = price
        
        # Calculate PnL
        if self.direction == 'long':
            self.pnl_percent = (price - self.entry_price) / self.entry_price * 100
        else:
            self.pnl_percent = (self.entry_price - price) / self.entry_price * 100
        
        # Track max profit/drawdown
        if self.pnl_percent > self.max_profit:
            self.max_profit = self.pnl_percent
        if self.pnl_percent < self.max_drawdown:
            self.max_drawdown = self.pnl_percent
        
        # Check exit conditions
        self._check_exits()
        
        self.last_update = datetime.now()
        self.hours_open = (self.last_update - self.open_time).total_seconds() / 3600
    
    def _check_exits(self):
        """Check if stop or target hit"""
        if self.status != 'active':
            return
        
        if self.direction == 'long':
            if self.current_price <= self.stop_loss:
                self._close('sl_hit', self.stop_loss)
            elif self.current_price >= self.take_profit:
                self._close('tp_hit', self.take_profit)
        else:
            if self.current_price >= self.stop_loss:
                self._close('sl_hit', self.stop_loss)
            elif self.current_price <= self.take_profit:
                self._close('tp_hit', self.take_profit)
        
        # Time-based exit (after 24h)
        if self.hours_open > 24:
            self._close('time_exit', self.current_price)
    
    def _close(self, reason: str, price: float):
        """Close the pick"""
        self.status = 'closed'
        self.exit_reason = reason
        self.exit_price = price
        self.exit_time = datetime.now()
        
        # Final PnL calc
        if self.direction == 'long':
            self.pnl_percent = (price - self.entry_price) / self.entry_price * 100
        else:
            self.pnl_percent = (self.entry_price - price) / self.entry_price * 100
        
        logger.info(f"[DNA] {self.tracking_id} closed: {reason} @ {price:.4f} ({self.pnl_percent:+.2f}%)")


class DNALiveTracker:
    """
    Live tracker for DNA picks
    
    Monitors all active picks and updates performance.
    """
    
    def __init__(self):
        self.active_picks: Dict[str, PickPerformance] = {}
        self.closed_picks: List[PickPerformance] = []
        self._load_state()
    
    def _load_state(self):
        """Load tracker state"""
        try:
            with open('dna_tracker_state.json', 'r') as f:
                data = json.load(f)
                
                # Load active picks
                for p in data.get('active', []):
                    perf = PickPerformance(
                        tracking_id=p['tracking_id'],
                        symbol=p['symbol'],
                        direction=p['direction'],
                        entry_price=p['entry_price'],
                        current_price=p['current_price'],
                        stop_loss=p['stop_loss'],
                        take_profit=p['take_profit'],
                        pnl_percent=p.get('pnl_percent', 0),
                        max_profit=p.get('max_profit', 0),
                        max_drawdown=p.get('max_drawdown', 0),
                        status=p.get('status', 'active'),
                        open_time=datetime.fromisoformat(p['open_time']),
                        last_update=datetime.fromisoformat(p['last_update'])
                    )
                    self.active_picks[perf.tracking_id] = perf
                
                logger.info(f"[Tracker] Loaded {len(self.active_picks)} active picks")
        except FileNotFoundError:
            pass
    
    def _save_state(self):
        """Save tracker state"""
        data = {
            'last_update': datetime.now().isoformat(),
            'active': [
                {
                    'tracking_id': p.tracking_id,
                    'symbol': p.symbol,
                    'direction': p.direction,
                    'entry_price': p.entry_price,
                    'current_price': p.current_price,
                    'stop_loss': p.stop_loss,
                    'take_profit': p.take_profit,
                    'pnl_percent': p.pnl_percent,
                    'max_profit': p.max_profit,
                    'max_drawdown': p.max_drawdown,
                    'status': p.status,
                    'open_time': p.open_time.isoformat(),
                    'last_update': p.last_update.isoformat()
                }
                for p in self.active_picks.values()
            ],
            'closed': [
                {
                    'tracking_id': p.tracking_id,
                    'symbol': p.symbol,
                    'direction': p.direction,
                    'pnl_percent': p.pnl_percent,
                    'exit_reason': p.exit_reason,
                    'exit_time': p.exit_time.isoformat() if p.exit_time else None,
                    'hours_open': p.hours_open
                }
                for p in self.closed_picks[-100:]  # Keep last 100
            ]
        }
        
        with open('dna_tracker_state.json', 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def add_pick(self, pick):
        """Add new pick to tracking"""
        perf = PickPerformance(
            tracking_id=pick.tracking_id,
            symbol=pick.symbol,
            direction=pick.direction,
            entry_price=pick.entry_price,
            current_price=pick.entry_price,
            stop_loss=pick.stop_loss,
            take_profit=pick.take_profit,
            open_time=pick.timestamp
        )
        
        self.active_picks[pick.tracking_id] = perf
        self._save_state()
        
        logger.info(f"[Tracker] Added {pick.tracking_id} to tracking")
    
    def update_pick_price(self, tracking_id: str, current_price: float):
        """Update pick with current market price"""
        if tracking_id not in self.active_picks:
            logger.warning(f"[Tracker] Pick {tracking_id} not found")
            return
        
        pick = self.active_picks[tracking_id]
        pick.update_price(current_price)
        
        # If closed, move to closed list
        if pick.status == 'closed':
            self.closed_picks.append(pick)
            del self.active_picks[tracking_id]
        
        self._save_state()
    
    def update_all_prices(self, prices: Dict[str, float]):
        """Update all picks with current prices"""
        for tracking_id, pick in list(self.active_picks.items()):
            symbol = pick.symbol
            if symbol in prices:
                self.update_pick_price(tracking_id, prices[symbol])
    
    def get_active_summary(self) -> Dict[str, Any]:
        """Get summary of active picks"""
        if not self.active_picks:
            return {'message': 'No active picks'}
        
        total_pnl = sum(p.pnl_percent for p in self.active_picks.values())
        avg_pnl = total_pnl / len(self.active_picks)
        
        best = max(self.active_picks.values(), key=lambda x: x.pnl_percent)
        worst = min(self.active_picks.values(), key=lambda x: x.pnl_percent)
        
        return {
            'active_count': len(self.active_picks),
            'total_pnl_percent': round(total_pnl, 2),
            'avg_pnl_percent': round(avg_pnl, 2),
            'best_pick': {
                'id': best.tracking_id,
                'pnl': round(best.pnl_percent, 2)
            },
            'worst_pick': {
                'id': worst.tracking_id,
                'pnl': round(worst.pnl_percent, 2)
            },
            'picks': [
                {
                    'id': p.tracking_id,
                    'symbol': p.symbol,
                    'direction': p.direction,
                    'pnl': round(p.pnl_percent, 2),
                    'hours': round(p.hours_open, 1)
                }
                for p in self.active_picks.values()
            ]
        }
    
    def get_performance_report(self, days: int = 30) -> Dict[str, Any]:
        """Get performance report"""
        # Get closed picks from last N days
        cutoff = datetime.now() - timedelta(days=days)
        recent_closed = [p for p in self.closed_picks if p.exit_time and p.exit_time > cutoff]
        
        if not recent_closed:
            return {'message': f'No closed picks in last {days} days'}
        
        # Calculate metrics
        total_pnl = sum(p.pnl_percent for p in recent_closed)
        avg_pnl = total_pnl / len(recent_closed)
        
        wins = [p for p in recent_closed if p.pnl_percent > 0]
        losses = [p for p in recent_closed if p.pnl_percent <= 0]
        
        win_rate = len(wins) / len(recent_closed)
        
        avg_win = sum(p.pnl_percent for p in wins) / len(wins) if wins else 0
        avg_loss = sum(p.pnl_percent for p in losses) / len(losses) if losses else 0
        
        expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
        
        # By exit reason
        by_reason = {}
        for p in recent_closed:
            reason = p.exit_reason or 'unknown'
            if reason not in by_reason:
                by_reason[reason] = {'count': 0, 'total_pnl': 0}
            by_reason[reason]['count'] += 1
            by_reason[reason]['total_pnl'] += p.pnl_percent
        
        return {
            'period_days': days,
            'total_picks': len(recent_closed),
            'win_rate': round(win_rate, 2),
            'expectancy': round(expectancy, 4),
            'avg_pnl': round(avg_pnl, 4),
            'total_pnl': round(total_pnl, 2),
            'avg_win': round(avg_win, 4),
            'avg_loss': round(avg_loss, 4),
            'by_exit_reason': by_reason
        }
    
    def close_pick_manual(self, tracking_id: str, price: float, reason: str = 'manual'):
        """Manually close a pick"""
        if tracking_id in self.active_picks:
            pick = self.active_picks[tracking_id]
            pick._close(reason, price)
            self.closed_picks.append(pick)
            del self.active_picks[tracking_id]
            self._save_state()


# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("DNA LIVE TRACKER - Demo")
    print("=" * 80)
    
    tracker = DNALiveTracker()
    
    # Create a sample pick
    from freshpicks_dna_strategy import DNAPick, DNAPickGenerator
    
    generator = DNAPickGenerator()
    picks = generator.generate_picks()
    
    if picks:
        pick = picks[0]
        print(f"\nAdding pick: {pick.tracking_id}")
        tracker.add_pick(pick)
        
        # Simulate price updates
        print("\nSimulating price movement...")
        prices = [pick.entry_price * (1 + i * 0.005) for i in range(10)]
        
        for i, price in enumerate(prices):
            tracker.update_pick_price(pick.tracking_id, price)
            active = tracker.get_active_summary()
            if 'picks' in active:
                pnl = active['picks'][0]['pnl']
                print(f"  Price {i+1}: {price:.2f} -> PnL: {pnl:+.2f}%")
        
        print("\n[Active Summary]")
        print(json.dumps(tracker.get_active_summary(), indent=2))
        
        print("\n[Performance Report]")
        print(json.dumps(tracker.get_performance_report(days=30), indent=2))
