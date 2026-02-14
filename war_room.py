#!/usr/bin/env python3
"""
================================================================================
CRYPTOALPHA PRO - WAR ROOM 🚨
================================================================================
Real-time combat system for live market validation.

Features:
- Real-time price monitoring
- Live signal generation
- Auto-position tracking
- P&L calculation
- Alert system

Usage:
    python war_room.py --mode live --assets BTC,ETH,BNB,AVAX
================================================================================
"""

import argparse
import json
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import sys
import requests

sys.path.insert(0, str(Path(__file__).parent))
from high_conviction_signals import HighConvictionSystem, ConvictionLevel, SignalAudit


@dataclass
class LivePosition:
    """Track a live position"""
    asset: str
    entry_price: float
    position_size: float
    stop_loss: float
    tp1: float
    tp2: float
    tp3: float
    entry_time: datetime
    signal_audit: dict
    
    # Live tracking
    current_price: float = 0
    unrealized_pnl: float = 0
    unrealized_pct: float = 0
    status: str = "OPEN"  # OPEN, TP1_HIT, TP2_HIT, TP3_HIT, STOPPED
    highest_price: float = 0
    
    def update(self, current_price: float):
        """Update position with current price"""
        self.current_price = current_price
        self.unrealized_pct = (current_price - self.entry_price) / self.entry_price
        self.unrealized_pnl = self.unrealized_pct * self.position_size
        
        if current_price > self.highest_price:
            self.highest_price = current_price
        
        # Check exits
        if current_price <= self.stop_loss:
            self.status = "STOPPED"
            return "STOP_LOSS"
        elif self.tp1 and current_price >= self.tp1 and self.status == "OPEN":
            self.status = "TP1_HIT"
            return "TAKE_PROFIT_1"
        elif self.tp2 and current_price >= self.tp2 and self.status == "TP1_HIT":
            self.status = "TP2_HIT"
            return "TAKE_PROFIT_2"
        elif self.tp3 and current_price >= self.tp3 and self.status == "TP2_HIT":
            self.status = "TP3_HIT"
            return "TAKE_PROFIT_3"
        
        return None


class RealTimeDataFeed:
    """Fetch real-time crypto data from CoinGecko"""
    
    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.coin_ids = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'BNB': 'binancecoin',
            'AVAX': 'avalanche-2'
        }
        self.price_history = {asset: [] for asset in self.coin_ids.keys()}
        
    def fetch_current_prices(self) -> Dict[str, float]:
        """Fetch current prices for all tracked assets"""
        ids = ','.join(self.coin_ids.values())
        url = f"{self.base_url}/simple/price"
        params = {
            'ids': ids,
            'vs_currencies': 'usd',
            'include_24hr_change': 'true',
            'include_24hr_vol': 'true'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            prices = {}
            for asset, coin_id in self.coin_ids.items():
                if coin_id in data:
                    prices[asset] = {
                        'price': data[coin_id]['usd'],
                        'change_24h': data[coin_id].get('usd_24h_change', 0),
                        'volume_24h': data[coin_id].get('usd_24h_vol', 0)
                    }
            
            return prices
        except Exception as e:
            print(f"❌ Error fetching prices: {e}")
            return {}
    
    def fetch_ohlc(self, asset: str, days: int = 30) -> pd.DataFrame:
        """Fetch OHLC data for backtesting signals"""
        coin_id = self.coin_ids.get(asset)
        if not coin_id:
            return pd.DataFrame()
        
        url = f"{self.base_url}/coins/{coin_id}/ohlc"
        params = {
            'vs_currency': 'usd',
            'days': days
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            # CoinGecko returns: [timestamp, open, high, low, close]
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df['volume'] = 0  # OHLC endpoint doesn't include volume
            
            return df
        except Exception as e:
            print(f"❌ Error fetching OHLC for {asset}: {e}")
            return pd.DataFrame()


class WarRoom:
    """
    Real-time combat system for live trading validation
    """
    
    def __init__(self, assets: List[str], capital: float = 10000.0):
        self.assets = assets
        self.capital = capital
        self.data_feed = RealTimeDataFeed()
        self.signal_system = HighConvictionSystem()
        
        # Position tracking
        self.positions: Dict[str, LivePosition] = {}
        self.closed_positions: List[LivePosition] = []
        self.signals_generated: List[dict] = []
        
        # Performance tracking
        self.start_time = datetime.now()
        self.initial_capital = capital
        self.current_equity = capital
        
        # War room stats
        self.battles_fought = 0
        self.battles_won = 0
        self.battles_lost = 0
        
    def scan_for_signals(self) -> List[SignalAudit]:
        """Scan all assets for EXTREME signals"""
        signals = []
        
        print("\n🔍 SCANNING FOR EXTREME SIGNALS...")
        print("=" * 70)
        
        for asset in self.assets:
            # Skip if already in position
            if asset in self.positions:
                print(f"⏸️  {asset}: Already in position, skipping...")
                continue
            
            # Fetch data
            ohlc = self.data_feed.fetch_ohlc(asset, days=60)
            if ohlc.empty or len(ohlc) < 30:
                print(f"⚠️  {asset}: Insufficient data")
                continue
            
            # Prepare data for signal system
            data = ohlc.copy()
            data['price'] = data['close']
            data['volume'] = 1000000  # Placeholder
            
            # Generate signal
            signal = self.signal_system.analyze(asset, data)
            
            if signal and signal.conviction == ConvictionLevel.EXTREME:
                print(f"🚨 {asset}: EXTREME SIGNAL DETECTED (Score: {signal.composite_score:.1f})")
                signals.append(signal)
                self.signals_generated.append(asdict(signal))
            else:
                conviction = signal.conviction.name if signal else "NONE"
                score = signal.composite_score if signal else 0
                print(f"❌ {asset}: {conviction} (Score: {score:.1f}) - No trade")
        
        return signals
    
    def enter_position(self, signal: SignalAudit):
        """Enter a new position based on signal"""
        asset = signal.asset
        
        # Calculate position size
        position_value = self.capital * signal.position_size
        
        position = LivePosition(
            asset=asset,
            entry_price=signal.entry_price,
            position_size=position_value,
            stop_loss=signal.stop_loss,
            tp1=signal.take_profit_1,
            tp2=signal.take_profit_2,
            tp3=signal.take_profit_3,
            entry_time=datetime.now(),
            signal_audit=signal.to_audit_log(),
            current_price=signal.entry_price,
            highest_price=signal.entry_price
        )
        
        self.positions[asset] = position
        self.battles_fought += 1
        
        print(f"\n⚔️  ENTERING BATTLE: {asset}")
        print(f"   Entry: ${signal.entry_price:,.2f}")
        print(f"   Stop:  ${signal.stop_loss:,.2f} ({(signal.stop_loss/signal.entry_price-1)*100:.2f}%)")
        print(f"   TP1:   ${signal.take_profit_1:,.2f} ({(signal.take_profit_1/signal.entry_price-1)*100:.1f}%)")
        print(f"   TP2:   ${signal.take_profit_2:,.2f} ({(signal.take_profit_2/signal.entry_price-1)*100:.1f}%)")
        print(f"   TP3:   ${signal.take_profit_3:,.2f} ({(signal.take_profit_3/signal.entry_price-1)*100:.1f}%) 🌙")
        print(f"   Size:  ${position_value:,.2f} ({signal.position_size*100:.1f}% of portfolio)")
        print(f"   Conviction: {signal.conviction.name} ({signal.composite_score:.1f}/100)")
        
        # Send alert
        self.send_alert(f"🚨 EXTREME SIGNAL: {asset}\nEntry: ${signal.entry_price:,.2f}\nTP3: ${signal.take_profit_3:,.2f} ({(signal.take_profit_3/signal.entry_price-1)*100:.1f}%)")
    
    def update_positions(self, current_prices: Dict):
        """Update all open positions"""
        if not self.positions:
            return
        
        print("\n📊 POSITION UPDATE")
        print("-" * 70)
        
        for asset, position in list(self.positions.items()):
            if asset not in current_prices:
                continue
            
            current = current_prices[asset]['price']
            result = position.update(current)
            
            # Display status
            emoji = "🟢" if position.unrealized_pct > 0 else "🔴"
            print(f"{emoji} {asset}: ${current:,.2f} | P&L: {position.unrealized_pct*100:+.2f}% | Status: {position.status}")
            
            # Handle exits
            if result:
                self.close_position(asset, current, result)
    
    def close_position(self, asset: str, exit_price: float, reason: str):
        """Close a position and record results"""
        position = self.positions.pop(asset)
        
        # Calculate final P&L
        if reason == "STOP_LOSS":
            pnl_pct = (position.stop_loss - position.entry_price) / position.entry_price
        elif reason == "TAKE_PROFIT_1":
            # 40% closed at TP1, 60% still open
            pnl_pct = ((position.tp1 - position.entry_price) / position.entry_price) * 0.4
        elif reason == "TAKE_PROFIT_2":
            # Another 40% closed at TP2
            tp1_pnl = ((position.tp1 - position.entry_price) / position.entry_price) * 0.4
            tp2_pnl = ((position.tp2 - position.entry_price) / position.entry_price) * 0.4
            pnl_pct = tp1_pnl + tp2_pnl
        elif reason == "TAKE_PROFIT_3":
            # Full position closed
            tp1_pnl = ((position.tp1 - position.entry_price) / position.entry_price) * 0.4
            tp2_pnl = ((position.tp2 - position.entry_price) / position.entry_price) * 0.4
            tp3_pnl = ((position.tp3 - position.entry_price) / position.entry_price) * 0.2
            pnl_pct = tp1_pnl + tp2_pnl + tp3_pnl
        else:
            pnl_pct = position.unrealized_pct
        
        pnl_amount = pnl_pct * position.position_size
        self.current_equity += pnl_amount
        
        # Track win/loss
        if pnl_pct > 0:
            self.battles_won += 1
            emoji = "✅ VICTORY"
        else:
            self.battles_lost += 1
            emoji = "❌ DEFEAT"
        
        position.status = reason
        self.closed_positions.append(position)
        
        print(f"\n{emoji}: {asset} POSITION CLOSED")
        print(f"   Reason: {reason}")
        print(f"   Entry: ${position.entry_price:,.2f}")
        print(f"   Exit:  ${exit_price:,.2f}")
        print(f"   P&L:   {pnl_pct*100:+.2f}% (${pnl_amount:,.2f})")
        print(f"   Hold:  {(datetime.now() - position.entry_time).days} days")
        
        # Send alert
        self.send_alert(f"{emoji}: {asset}\nReason: {reason}\nP&L: {pnl_pct*100:+.2f}%")
    
    def send_alert(self, message: str):
        """Send alert to Discord/Telegram"""
        # Placeholder - implement with actual webhooks
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"\n📢 ALERT [{timestamp}]:")
        print(message)
    
    def print_war_room_status(self):
        """Print current war room status"""
        elapsed = datetime.now() - self.start_time
        
        print("\n" + "=" * 70)
        print("🚨 WAR ROOM STATUS 🚨")
        print("=" * 70)
        print(f"⏱️  Time in Combat: {elapsed.days}d {elapsed.seconds//3600}h {(elapsed.seconds//60)%60}m")
        print(f"💰 Starting Capital: ${self.initial_capital:,.2f}")
        print(f"💰 Current Equity:   ${self.current_equity:,.2f}")
        print(f"📈 Total Return:     {(self.current_equity/self.initial_capital-1)*100:+.2f}%")
        print(f"⚔️  Battles Fought:  {self.battles_fought}")
        print(f"✅ Victories:        {self.battles_won} ({self.battles_won/self.battles_fought*100:.1f}% win rate)" if self.battles_fought > 0 else "✅ Victories:        0")
        print(f"❌ Defeats:          {self.battles_lost}")
        print(f"🎯 Open Positions:   {len(self.positions)}")
        
        if self.positions:
            print("\n📊 OPEN POSITIONS:")
            for asset, pos in self.positions.items():
                print(f"   {asset}: ${pos.current_price:,.2f} ({pos.unrealized_pct*100:+.2f}%)")
        
        print("=" * 70)
    
    def save_battle_report(self):
        """Save battle report to file"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'initial_capital': self.initial_capital,
            'current_equity': self.current_equity,
            'total_return_pct': (self.current_equity/self.initial_capital-1)*100,
            'battles_fought': self.battles_fought,
            'battles_won': self.battles_won,
            'battles_lost': self.battles_lost,
            'win_rate': self.battles_won / self.battles_fought if self.battles_fought > 0 else 0,
            'open_positions': {k: asdict(v) for k, v in self.positions.items()},
            'closed_positions': [asdict(p) for p in self.closed_positions],
            'signals_generated': self.signals_generated
        }
        
        filename = f"war_room_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📝 Battle report saved: {filename}")
    
    def run(self, scan_interval: int = 300):
        """Main war room loop"""
        print("\n" + "=" * 70)
        print("🚨 CRYPTOALPHA PRO - WAR ROOM ACTIVATED 🚨")
        print("=" * 70)
        print(f"Assets: {', '.join(self.assets)}")
        print(f"Capital: ${self.capital:,.2f}")
        print(f"Scan Interval: {scan_interval}s")
        print("=" * 70)
        
        try:
            while True:
                # Fetch current prices
                prices = self.data_feed.fetch_current_prices()
                
                if prices:
                    print(f"\n💹 Market Update - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    for asset, data in prices.items():
                        emoji = "🟢" if data['change_24h'] > 0 else "🔴"
                        print(f"{emoji} {asset}: ${data['price']:,.2f} ({data['change_24h']:+.2f}%)")
                
                # Update positions
                self.update_positions(prices)
                
                # Scan for new signals
                signals = self.scan_for_signals()
                for signal in signals:
                    self.enter_position(signal)
                
                # Print status
                self.print_war_room_status()
                
                # Save report
                self.save_battle_report()
                
                # Wait for next scan
                print(f"\n😴 Sleeping for {scan_interval}s...")
                time.sleep(scan_interval)
                
        except KeyboardInterrupt:
            print("\n\n🛑 WAR ROOM SHUTTING DOWN...")
            self.print_war_room_status()
            self.save_battle_report()
            print("✅ Final report saved. Goodbye, commander.")


def main():
    parser = argparse.ArgumentParser(description='CryptoAlpha Pro War Room')
    parser.add_argument('--assets', default='BTC,ETH,BNB,AVAX', help='Assets to track')
    parser.add_argument('--capital', type=float, default=10000.0, help='Starting capital')
    parser.add_argument('--interval', type=int, default=300, help='Scan interval in seconds')
    
    args = parser.parse_args()
    
    assets = [a.strip() for a in args.assets.split(',')]
    
    war_room = WarRoom(assets=assets, capital=args.capital)
    war_room.run(scan_interval=args.interval)


if __name__ == '__main__':
    main()
