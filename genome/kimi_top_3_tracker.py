#!/usr/bin/env python3
"""
KIMI Top 3 Picks — Real-Time Entry Condition Monitor
=====================================================

Automated tracking of entry conditions for top 3 picks:
- Monitors live market data
- Checks if entry conditions are met
- Sends alerts when triggers hit
- Updates tracking log

Author: KIMI | Date: 2026-03-14
"""

import sys
import json
import urllib.request
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from genome.mutation_lab.innovative_mutations import fetch_binance_klines
from genome.kimi_top_picks_automation import williams_r_indicator


@dataclass
class Pick:
    """Tracked pick with entry conditions."""
    rank: int
    symbol: str
    strategy: str
    direction: str  # 'LONG' or 'SHORT' - EXPLICIT
    entry_price: float
    take_profit: float
    stop_loss: float
    confidence: float
    status: str  # 'WAITING', 'READY', 'ENTERED', 'CLOSED'
    
    # Entry conditions
    entry_trigger_type: str  # 'IMMEDIATE', 'WILLIAMS_R_BELOW', 'VWAP_TOUCH', etc.
    entry_trigger_value: Optional[float] = None
    
    # Current market data
    current_price: Optional[float] = None
    current_williams_r: Optional[float] = None
    current_vwap: Optional[float] = None
    
    # Tracking
    entry_time_est: Optional[str] = None
    exit_time_est: Optional[str] = None
    realized_pnl: Optional[float] = None
    
    def check_entry_conditions(self) -> bool:
        """Check if entry conditions are met."""
        if self.status != 'WAITING':
            return False
        
        if self.entry_trigger_type == 'IMMEDIATE':
            return True
        
        elif self.entry_trigger_type == 'WILLIAMS_R_BELOW':
            if self.current_williams_r is not None and self.entry_trigger_value is not None:
                return self.current_williams_r <= self.entry_trigger_value
        
        elif self.entry_trigger_type == 'VWAP_TOUCH':
            if self.current_price is not None and self.entry_trigger_value is not None:
                return self.current_price <= self.entry_trigger_value * 1.005  # Within 0.5%
        
        return False
    
    def check_exit_conditions(self) -> Optional[str]:
        """Check if exit conditions are met. Returns 'TP', 'SL', or None."""
        if self.status != 'ENTERED' or self.current_price is None:
            return None
        
        if self.direction == 'LONG':
            if self.current_price >= self.take_profit:
                return 'TP'
            elif self.current_price <= self.stop_loss:
                return 'SL'
        
        elif self.direction == 'SHORT':
            if self.current_price <= self.take_profit:
                return 'TP'
            elif self.current_price >= self.stop_loss:
                return 'SL'
        
        return None
    
    def to_dict(self) -> dict:
        return asdict(self)


class Top3Tracker:
    """Tracks top 3 picks with automated condition checking."""
    
    def __init__(self):
        self.picks: List[Pick] = []
        self.est_timezone = timezone(timedelta(hours=-4))  # EST
        self.init_default_picks()
    
    def init_default_picks(self):
        """Initialize the top 3 picks."""
        now_utc = datetime.now(timezone.utc)
        now_est = now_utc.astimezone(self.est_timezone)
        time_str = now_est.strftime('%Y-%m-%d %H:%M EST')
        
        self.picks = [
            Pick(
                rank=1,
                symbol='SOLUSDT',
                strategy='Williams %R Mean Reversion',
                direction='LONG',  # EXPLICIT
                entry_price=88.39,
                take_profit=94.50,
                stop_loss=84.20,
                confidence=0.78,
                status='READY',  # Already met conditions
                entry_trigger_type='IMMEDIATE',
                entry_trigger_value=None,
                entry_time_est=time_str,
            ),
            Pick(
                rank=2,
                symbol='BTCUSDT',
                strategy='Williams %R Mean Reversion',
                direction='LONG',  # EXPLICIT
                entry_price=71095.37,
                take_profit=73100.00,
                stop_loss=68800.00,
                confidence=0.72,
                status='WAITING',
                entry_trigger_type='WILLIAMS_R_BELOW',
                entry_trigger_value=-80.0,
                entry_time_est=None,
            ),
            Pick(
                rank=3,
                symbol='ETHUSDT',
                strategy='VWAP Bollinger Squeeze',
                direction='LONG',  # EXPLICIT
                entry_price=2100.69,
                take_profit=2185.00,
                stop_loss=2034.00,
                confidence=0.70,
                status='WAITING',
                entry_trigger_type='VWAP_TOUCH',
                entry_trigger_value=2085.50,
                entry_time_est=None,
            ),
        ]
    
    def update_market_data(self):
        """Fetch current market data for all picks."""
        print("Fetching live market data...")
        
        for pick in self.picks:
            df = fetch_binance_klines(pick.symbol, '1h', limit=50)
            if df.empty:
                continue
            
            close = df['Close']
            pick.current_price = close.iloc[-1]
            
            # Calculate Williams %R for relevant picks
            if 'Williams' in pick.strategy:
                wr = williams_r_indicator(close).iloc[-1]
                pick.current_williams_r = wr
            
            # Calculate VWAP for relevant picks
            if 'VWAP' in pick.strategy:
                typical = (df['High'] + df['Low'] + df['Close']) / 3
                vwap = (typical * df['Volume']).rolling(20).sum() / df['Volume'].rolling(20).sum()
                pick.current_vwap = vwap.iloc[-1]
    
    def check_all_conditions(self) -> List[dict]:
        """Check entry/exit conditions for all picks. Returns alerts."""
        alerts = []
        
        for pick in self.picks:
            # Check entry
            if pick.status == 'WAITING':
                if pick.check_entry_conditions():
                    pick.status = 'READY'
                    now_est = datetime.now(self.est_timezone).strftime('%Y-%m-%d %H:%M EST')
                    pick.entry_time_est = now_est
                    
                    alerts.append({
                        'type': 'ENTRY_TRIGGERED',
                        'priority': 'HIGH',
                        'symbol': pick.symbol,
                        'direction': pick.direction,
                        'message': f"🚨 ENTRY NOW: {pick.symbol} {pick.direction} @ ${pick.current_price:,.2f}",
                        'details': f"Strategy: {pick.strategy} | TP: ${pick.take_profit:,.2f} | SL: ${pick.stop_loss:,.2f}",
                    })
            
            # Check exit
            elif pick.status == 'ENTERED':
                exit_reason = pick.check_exit_conditions()
                if exit_reason:
                    pick.status = 'CLOSED'
                    pick.exit_time_est = datetime.now(self.est_timezone).strftime('%Y-%m-%d %H:%M EST')
                    
                    # Calculate P&L
                    if pick.direction == 'LONG':
                        pnl_pct = (pick.current_price - pick.entry_price) / pick.entry_price
                    else:
                        pnl_pct = (pick.entry_price - pick.current_price) / pick.entry_price
                    
                    pick.realized_pnl = pnl_pct
                    
                    emoji = '✅' if exit_reason == 'TP' else '❌'
                    alerts.append({
                        'type': 'EXIT_TRIGGERED',
                        'priority': 'HIGH',
                        'symbol': pick.symbol,
                        'direction': pick.direction,
                        'message': f"{emoji} EXIT: {pick.symbol} {pick.direction} | Reason: {exit_reason} | P&L: {pnl_pct:+.2%}",
                    })
        
        return alerts
    
    def generate_report(self) -> dict:
        """Generate comprehensive tracking report."""
        now_utc = datetime.now(timezone.utc)
        now_est = now_utc.astimezone(self.est_timezone)
        
        report = {
            'timestamp_utc': now_utc.isoformat(),
            'timestamp_est': now_est.strftime('%Y-%m-%d %H:%M:%S EST'),
            'picks': [],
            'alerts': [],
            'summary': {
                'total_picks': len(self.picks),
                'waiting': sum(1 for p in self.picks if p.status == 'WAITING'),
                'ready': sum(1 for p in self.picks if p.status == 'READY'),
                'entered': sum(1 for p in self.picks if p.status == 'ENTERED'),
                'closed': sum(1 for p in self.picks if p.status == 'CLOSED'),
            }
        }
        
        for pick in self.picks:
            pick_data = pick.to_dict()
            
            # Add distance to trigger
            if pick.status == 'WAITING':
                if pick.entry_trigger_type == 'WILLIAMS_R_BELOW' and pick.current_williams_r:
                    distance = pick.current_williams_r - pick.entry_trigger_value
                    pick_data['distance_to_trigger'] = f"{distance:.1f} points"
                elif pick.entry_trigger_type == 'VWAP_TOUCH' and pick.current_price and pick.entry_trigger_value:
                    distance_pct = (pick.current_price - pick.entry_trigger_value) / pick.entry_trigger_value * 100
                    pick_data['distance_to_trigger'] = f"{distance_pct:.2f}% above VWAP"
            
            # Add P&L tracking
            if pick.status == 'ENTERED' and pick.current_price:
                if pick.direction == 'LONG':
                    unrealized_pct = (pick.current_price - pick.entry_price) / pick.entry_price
                else:
                    unrealized_pct = (pick.entry_price - pick.current_price) / pick.entry_price
                pick_data['unrealized_pnl_pct'] = unrealized_pct
                pick_data['unrealized_pnl_usd'] = unrealized_pct * 10000  # Assuming $10k account
            
            report['picks'].append(pick_data)
        
        return report
    
    def save_to_chatwithit(self):
        """Save formatted report to chatwithit.md."""
        report = self.generate_report()
        
        # Generate markdown
        md = f"""

---

## KIMI TOP 3 PICKS — LIVE TRACKING ({report['timestamp_est']})

### PORTFOLIO STATUS
| Metric | Value |
|--------|-------|
| **Total Picks** | {report['summary']['total_picks']} |
| **Waiting for Entry** | {report['summary']['waiting']} |
| **Ready to Enter** | {report['summary']['ready']} |
| **Active Positions** | {report['summary']['entered']} |
| **Closed Positions** | {report['summary']['closed']} |

---

"""
        
        for pick in report['picks']:
            direction_emoji = '🟢 LONG' if pick['direction'] == 'LONG' else '🔴 SHORT'
            status_emoji = {
                'WAITING': '⏳',
                'READY': '✅',
                'ENTERED': '📊',
                'CLOSED': '🔒',
            }.get(pick['status'], '❓')
            
            md += f"""### PICK #{pick['rank']}: {pick['symbol']} — {direction_emoji}

| Field | Value |
|-------|-------|
| **Status** | {status_emoji} {pick['status']} |
| **Strategy** | {pick['strategy']} |
| **Direction** | **{pick['direction']}** (explicit) |
| **Entry Price** | ${pick['entry_price']:,.2f} |
| **Take Profit** | ${pick['take_profit']:,.2f} |
| **Stop Loss** | ${pick['stop_loss']:,.2f} |
| **Confidence** | {pick['confidence']:.0%} |
| **Entry Time (EST)** | {pick.get('entry_time_est', 'Waiting...')} |

**Current Market Data:**
"""
            
            if pick.get('current_price'):
                md += f"- Current Price: ${pick['current_price']:,.2f}\n"
            if pick.get('current_williams_r'):
                md += f"- Williams %R: {pick['current_williams_r']:.1f} (trigger: below {pick['entry_trigger_value']})\n"
            if pick.get('current_vwap'):
                md += f"- VWAP: ${pick['current_vwap']:,.2f}\n"
            if pick.get('distance_to_trigger'):
                md += f"- **Distance to Entry:** {pick['distance_to_trigger']}\\n"
            if pick.get('unrealized_pnl_pct') is not None:
                pnl_emoji = '🟢' if pick['unrealized_pnl_pct'] >= 0 else '🔴'
                md += f"- **Unrealized P&L:** {pnl_emoji} {pick['unrealized_pnl_pct']:+.2%} (${pick['unrealized_pnl_usd']:,.2f})\n"
            
            md += f"""
**Entry Conditions:**
- Type: {pick['entry_trigger_type']}
"""
            if pick['entry_trigger_value']:
                md += f"- Trigger Value: {pick['entry_trigger_value']}\n"
            
            md += f"""
---

"""
        
        # Append to chatwithit.md
        chatwithit_path = ROOT / 'chatwithit.md'
        with open(chatwithit_path, 'a', encoding='utf-8') as f:
            f.write(md)
        
        print(f"✅ Updated {chatwithit_path}")
    
    def run_monitoring_cycle(self):
        """Complete monitoring cycle."""
        print("="*70)
        print("KIMI TOP 3 PICKS — AUTOMATED ENTRY MONITOR")
        print("="*70)
        
        # Update market data
        self.update_market_data()
        
        # Check conditions
        alerts = self.check_all_conditions()
        
        # Generate report
        report = self.generate_report()
        
        # Display
        print(f"\nTimestamp: {report['timestamp_est']}")
        print(f"\nStatus Summary:")
        print(f"  Waiting: {report['summary']['waiting']}")
        print(f"  Ready: {report['summary']['ready']}")
        print(f"  Entered: {report['summary']['entered']}")
        print(f"  Closed: {report['summary']['closed']}")
        
        print(f"\nCurrent Picks:")
        for pick in report['picks']:
            direction_str = f"[{pick['direction']}]"
            print(f"\n  #{pick['rank']} {pick['symbol']} {direction_str}")
            print(f"     Status: {pick['status']}")
            print(f"     Current: ${pick.get('current_price', 0):,.2f}")
            print(f"     Target: ${pick['entry_price']:,.2f}")
            
            if pick.get('current_williams_r'):
                print(f"     Williams %R: {pick['current_williams_r']:.1f}")
            if pick.get('distance_to_trigger'):
                print(f"     -> {pick['distance_to_trigger']}")
            if pick.get('unrealized_pnl_pct') is not None:
                print(f"     P&L: {pick['unrealized_pnl_pct']:+.2%}")
        
        # Display alerts
        if alerts:
            print(f"\n🚨 ALERTS ({len(alerts)}):")
            for alert in alerts:
                print(f"  [{alert['priority']}] {alert['message']}")
                print(f"     {alert['details']}")
        else:
            print("\n✅ No new alerts")
        
        # Save to chatwithit.md
        self.save_to_chatwithit()
        
        print("\n" + "="*70)
        
        return report, alerts


def main():
    """Run monitoring cycle."""
    tracker = Top3Tracker()
    tracker.run_monitoring_cycle()


if __name__ == '__main__':
    main()
