#!/usr/bin/env python3
"""
================================================================================
MULTI-TIMEFRAME FORWARD TESTING SYSTEM
================================================================================

Paper trading system to validate multi-timeframe confluence strategies.
Tracks signals, P&L, and performance metrics in real-time.

================================================================================
"""

import json
import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import os


class TradeStatus(Enum):
    OPEN = "open"
    CLOSED_TP1 = "closed_tp1"
    CLOSED_TP2 = "closed_tp2"
    CLOSED_TP3 = "closed_tp3"
    STOPPED = "stopped"
    EXPIRED = "expired"


@dataclass
class MTTrade:
    """Multi-timeframe trade record"""
    trade_id: str
    asset: str
    entry_time: datetime
    entry_price: float
    direction: str  # 'buy' or 'sell'
    confluence_score: float
    confluence_timeframes: List[str]
    
    # Position sizing
    size: float
    tp1_price: float
    tp2_price: float
    tp3_price: float
    sl_price: float
    
    # Tracking
    status: TradeStatus = TradeStatus.OPEN
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    exit_reason: Optional[str] = None
    pnl_pct: float = 0.0
    pnl_usd: float = 0.0
    highest_profit: float = 0.0
    lowest_profit: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            'trade_id': self.trade_id,
            'asset': self.asset,
            'direction': self.direction,
            'entry': {
                'time': self.entry_time.isoformat(),
                'price': self.entry_price
            },
            'exit': {
                'time': self.exit_time.isoformat() if self.exit_time else None,
                'price': self.exit_price,
                'reason': self.exit_reason
            },
            'confluence': {
                'score': self.confluence_score,
                'timeframes': self.confluence_timeframes
            },
            'targets': {
                'tp1': self.tp1_price,
                'tp2': self.tp2_price,
                'tp3': self.tp3_price,
                'sl': self.sl_price
            },
            'status': self.status.value,
            'pnl_pct': round(self.pnl_pct, 2),
            'pnl_usd': round(self.pnl_usd, 2)
        }


class ForwardTestTracker:
    """
    Tracks forward testing performance for multi-timeframe strategies
    """
    
    def __init__(self, strategy_name: str, initial_capital: float = 10000.0):
        self.strategy_name = strategy_name
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        
        self.trades: List[MTTrade] = []
        self.active_trades: Dict[str, MTTrade] = {}
        
        self.start_date = datetime.now()
        self.metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'profit_factor': 0.0,
            'max_drawdown': 0.0,
            'current_drawdown': 0.0,
            'peak_capital': initial_capital
        }
        
        self.data_file = f"forward_test_{strategy_name.lower().replace(' ', '_')}.json"
        self.load_history()
    
    def load_history(self):
        """Load existing trade history"""
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                self.current_capital = data.get('current_capital', self.initial_capital)
                print(f"[Loaded {len(data.get('trades', []))} historical trades]")
    
    def save_state(self):
        """Save current state to file"""
        data = {
            'strategy': self.strategy_name,
            'start_date': self.start_date.isoformat(),
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'metrics': self.metrics,
            'trades': [t.to_dict() for t in self.trades]
        }
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def enter_trade(self, trade: MTTrade) -> bool:
        """Record new trade entry"""
        self.active_trades[trade.trade_id] = trade
        self.trades.append(trade)
        self.metrics['total_trades'] += 1
        
        # Reserve capital
        self.current_capital -= trade.size
        
        print(f"\n🎯 NEW TRADE: {trade.asset} {trade.direction.upper()}")
        print(f"   Entry: ${trade.entry_price:,.2f}")
        print(f"   Confluence Score: {trade.confluence_score:.1f}/100")
        print(f"   Timeframes: {', '.join(trade.confluence_timeframes)}")
        print(f"   TP1: ${trade.tp1_price:,.2f} | TP2: ${trade.tp2_price:,.2f} | TP3: ${trade.tp3_price:,.2f}")
        print(f"   Stop: ${trade.sl_price:,.2f}")
        
        self.save_state()
        return True
    
    def update_prices(self, prices: Dict[str, float]):
        """Update all active trades with current prices"""
        for trade_id, trade in list(self.active_trades.items()):
            if trade.asset not in prices:
                continue
            
            current_price = prices[trade.asset]
            
            # Calculate P&L
            if trade.direction == 'buy':
                pnl_pct = ((current_price - trade.entry_price) / trade.entry_price) * 100
                hit_tp1 = current_price >= trade.tp1_price
                hit_tp2 = current_price >= trade.tp2_price
                hit_tp3 = current_price >= trade.tp3_price
                hit_sl = current_price <= trade.sl_price
            else:  # sell
                pnl_pct = ((trade.entry_price - current_price) / trade.entry_price) * 100
                hit_tp1 = current_price <= trade.tp1_price
                hit_tp2 = current_price <= trade.tp2_price
                hit_tp3 = current_price <= trade.tp3_price
                hit_sl = current_price >= trade.sl_price
            
            # Track extremes
            if pnl_pct > trade.highest_profit:
                trade.highest_profit = pnl_pct
            if pnl_pct < trade.lowest_profit:
                trade.lowest_profit = pnl_pct
            
            # Check targets
            if hit_tp3 and trade.status == TradeStatus.OPEN:
                self.close_trade(trade_id, current_price, 'TP3', pnl_pct)
            elif hit_tp2 and trade.status in [TradeStatus.OPEN, TradeStatus.CLOSED_TP1]:
                trade.status = TradeStatus.CLOSED_TP2
            elif hit_tp1 and trade.status == TradeStatus.OPEN:
                trade.status = TradeStatus.CLOSED_TP1
            elif hit_sl:
                self.close_trade(trade_id, current_price, 'STOP', pnl_pct)
    
    def close_trade(self, trade_id: str, exit_price: float, reason: str, pnl_pct: float):
        """Close a trade"""
        if trade_id not in self.active_trades:
            return
        
        trade = self.active_trades[trade_id]
        trade.exit_price = exit_price
        trade.exit_time = datetime.now()
        trade.exit_reason = reason
        trade.pnl_pct = pnl_pct
        trade.pnl_usd = (trade.size * pnl_pct / 100)
        
        # Update capital
        self.current_capital += trade.size + trade.pnl_usd
        
        # Update metrics
        if trade.pnl_usd > 0:
            self.metrics['winning_trades'] += 1
        else:
            self.metrics['losing_trades'] += 1
        
        # Calculate drawdown
        if self.current_capital > self.metrics['peak_capital']:
            self.metrics['peak_capital'] = self.current_capital
        else:
            dd = ((self.metrics['peak_capital'] - self.current_capital) / self.metrics['peak_capital']) * 100
            self.metrics['current_drawdown'] = dd
            if dd > self.metrics['max_drawdown']:
                self.metrics['max_drawdown'] = dd
        
        # Remove from active
        del self.active_trades[trade_id]
        
        print(f"\n[{'WIN' if pnl_pct > 0 else 'LOSS'}] TRADE CLOSED: {trade.asset}")
        print(f"   Exit: ${exit_price:,.2f} | Reason: {reason}")
        print(f"   P&L: {pnl_pct:+.2f}% (${trade.pnl_usd:+.2f})")
        
        self.recalculate_metrics()
        self.save_state()
    
    def recalculate_metrics(self):
        """Recalculate all performance metrics"""
        closed = [t for t in self.trades if t.exit_price is not None]
        
        if not closed:
            return
        
        wins = [t.pnl_pct for t in closed if t.pnl_pct > 0]
        losses = [t.pnl_pct for t in closed if t.pnl_pct <= 0]
        
        self.metrics['win_rate'] = (len(wins) / len(closed)) * 100 if closed else 0
        self.metrics['avg_win'] = sum(wins) / len(wins) if wins else 0
        self.metrics['avg_loss'] = sum(losses) / len(losses) if losses else 0
        
        # Profit factor
        gross_profit = sum(t.pnl_usd for t in closed if t.pnl_usd > 0)
        gross_loss = abs(sum(t.pnl_usd for t in closed if t.pnl_usd < 0))
        self.metrics['profit_factor'] = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    def get_status_report(self) -> Dict:
        """Generate current status report"""
        return {
            'timestamp': datetime.now().isoformat(),
            'strategy': self.strategy_name,
            'capital': {
                'initial': self.initial_capital,
                'current': self.current_capital,
                'change_pct': ((self.current_capital - self.initial_capital) / self.initial_capital) * 100
            },
            'performance': self.metrics,
            'active_trades': len(self.active_trades),
            'closed_trades': len([t for t in self.trades if t.exit_price is not None])
        }
    
    def print_dashboard(self):
        """Print live dashboard"""
        report = self.get_status_report()
        
        print("\n" + "=" * 70)
        print(f"MULTI-TIMEFRAME FORWARD TEST - {self.strategy_name}")
        print("=" * 70)
        print(f"Capital: ${report['capital']['current']:,.2f} "
              f"({report['capital']['change_pct']:+.2f}%)")
        print(f"Trades: {report['performance']['total_trades']} total, "
              f"{report['active_trades']} active")
        
        if report['performance']['total_trades'] > 0:
            print(f"\nPerformance:")
            print(f"  Win Rate: {report['performance']['win_rate']:.1f}%")
            print(f"  Avg Win: +{report['performance']['avg_win']:.2f}%")
            print(f"  Avg Loss: {report['performance']['avg_loss']:.2f}%")
            print(f"  Profit Factor: {report['performance']['profit_factor']:.2f}")
            print(f"  Max Drawdown: {report['performance']['max_drawdown']:.2f}%")
        
        # Active trades
        if self.active_trades:
            print(f"\n[Active Trades]")
            for tid, trade in self.active_trades.items():
                print(f"  {trade.asset} {trade.direction.upper()} @ ${trade.entry_price:,.2f} "
                      f"[{trade.status.value}]")
        
        print("=" * 70)


def simulate_forward_test():
    """Simulate forward testing with sample trades"""
    tracker = ForwardTestTracker("H2_Higher_Trend_Filter", 10000.0)
    
    print("\n[SIMULATING MULTI-TIMEFRAME FORWARD TEST]")
    print("=" * 70)
    
    # Simulate entering a trade
    trade1 = MTTrade(
        trade_id="BTC_MT_001",
        asset="BTC",
        entry_time=datetime.now(),
        entry_price=69890,
        direction="buy",
        confluence_score=82.5,
        confluence_timeframes=["15m", "1h", "4h", "1d"],
        size=2000,
        tp1_price=71500,
        tp2_price=73500,
        tp3_price=76500,
        sl_price=67800
    )
    
    tracker.enter_trade(trade1)
    
    # Simulate price updates
    prices = {'BTC': 70200}
    tracker.update_prices(prices)
    tracker.print_dashboard()
    
    # Simulate closing
    tracker.close_trade("BTC_MT_001", 71500, 'TP1', 2.30)
    tracker.print_dashboard()
    
    return tracker


if __name__ == '__main__':
    tracker = simulate_forward_test()
