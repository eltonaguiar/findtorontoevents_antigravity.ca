#!/usr/bin/env python3
"""
================================================================================
CRYPTOALPHA PRO - WAR ROOM v2 🚨
================================================================================
CLEAR P&L tracking with buy/sell timestamps

Features:
- Real-time price monitoring
- Live signal generation  
- Clear position tracking with entry/exit times
- SEPARATE realized vs unrealized P&L
- Battle history with full trade details

Usage:
    python war_room_v2.py --mode live --assets BTC,ETH,BNB,AVAX
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
class Trade:
    """Complete trade record with full audit trail"""
    # Identification
    trade_id: str
    asset: str
    
    # ENTRY details
    entry_time: datetime
    entry_price: float
    position_size_usd: float
    conviction_score: float
    signal_audit: dict
    
    # EXIT details (populated when closed)
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None  # TP1, TP2, TP3, STOP, MANUAL
    
    # Targets (set at entry)
    stop_loss: float = 0
    tp1_price: float = 0
    tp2_price: float = 0
    tp3_price: float = 0
    
    # P&L tracking
    realized_pnl_usd: float = 0
    realized_pnl_pct: float = 0
    
    # Status
    status: str = "OPEN"  # OPEN, CLOSED
    
    def close(self, exit_price: float, exit_time: datetime, reason: str):
        """Close the trade and calculate realized P&L"""
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.exit_reason = reason
        self.status = "CLOSED"
        
        # Calculate realized P&L
        self.realized_pnl_pct = (exit_price - self.entry_price) / self.entry_price
        self.realized_pnl_usd = self.realized_pnl_pct * self.position_size_usd
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'trade_id': self.trade_id,
            'asset': self.asset,
            'entry_time': self.entry_time.isoformat(),
            'entry_price': self.entry_price,
            'position_size_usd': self.position_size_usd,
            'conviction_score': self.conviction_score,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'exit_price': self.exit_price,
            'exit_reason': self.exit_reason,
            'stop_loss': self.stop_loss,
            'tp1_price': self.tp1_price,
            'tp2_price': self.tp2_price,
            'tp3_price': self.tp3_price,
            'realized_pnl_usd': self.realized_pnl_usd,
            'realized_pnl_pct': self.realized_pnl_pct,
            'status': self.status
        }


class WarRoomV2:
    """
    Real-time combat system with CLEAR P&L tracking
    """
    
    def __init__(self, assets: List[str], capital: float = 10000.0):
        self.assets = assets
        self.initial_capital = capital
        self.current_capital = capital
        
        # Position tracking - CLEAR separation
        self.open_trades: Dict[str, Trade] = {}  # Currently holding
        self.closed_trades: List[Trade] = []      # Completed trades
        
        # For quick lookup
        self.data_feed = self.MockDataFeed()
        self.signal_system = HighConvictionSystem()
        
        # Stats
        self.start_time = datetime.now()
        self.trade_counter = 0
        
    class MockDataFeed:
        """Mock data feed for demo"""
        def __init__(self):
            self.prices = {
                'BTC': 69852,
                'ETH': 2085,
                'BNB': 634,
                'AVAX': 9.46
            }
        
        def get_prices(self):
            # Simulate small price movements
            for asset in self.prices:
                self.prices[asset] *= (1 + np.random.normal(0, 0.001))
            return self.prices.copy()
    
    def generate_mock_ohlc(self, asset: str) -> pd.DataFrame:
        """Generate mock OHLC data for signal generation"""
        dates = pd.date_range(end=datetime.now(), periods=100, freq='h')
        base_price = self.data_feed.prices[asset]
        
        prices = base_price * np.exp(np.cumsum(np.random.normal(0.0001, 0.01, 100)))
        
        df = pd.DataFrame({
            'price': prices,
            'volume': np.random.lognormal(10, 1, 100),
        }, index=dates)
        
        return df
    
    def scan_for_signals(self) -> List[SignalAudit]:
        """Scan for EXTREME signals"""
        signals = []
        
        for asset in self.assets:
            if asset in self.open_trades:
                continue  # Already in position
            
            # Generate mock signal occasionally
            if np.random.random() < 0.1:  # 10% chance per scan
                # Create a mock EXTREME signal
                current_price = self.data_feed.prices[asset]
                
                # Simulate signal audit
                signal = self._create_mock_signal(asset, current_price)
                signals.append(signal)
        
        return signals
    
    def _create_mock_signal(self, asset: str, price: float) -> SignalAudit:
        """Create a mock signal for demo purposes"""
        # Calculate targets
        volatility = 0.015
        stop = price * (1 - 1.5 * volatility)
        tp1 = price * (1 + 3 * volatility)
        tp2 = price * (1 + 5 * volatility)
        tp3 = price * (1 + 10 * volatility)
        
        return SignalAudit(
            timestamp=datetime.now(),
            asset=asset,
            model_votes={'m1': 'LONG', 'm2': 'LONG', 'm3': 'LONG', 
                        'm4': 'LONG', 'm5': 'LONG', 'm6': 'LONG'},
            model_agreement_score=1.0,
            detected_regime="BULL_TREND",
            regime_alignment_score=0.95,
            volatility_percentile=0.35,
            exchange_flow_24h=-500,
            network_growth=0.04,
            funding_rate=0.008,
            on_chain_score=0.90,
            technical_checks={'check1': True, 'check2': True},
            technical_score=1.0,
            entry_price=price,
            stop_loss=stop,
            take_profit_1=tp1,
            take_profit_2=tp2,
            take_profit_3=tp3,
            risk_reward=3.0,
            position_size=0.12,
            conviction=ConvictionLevel.EXTREME,
            composite_score=92.5,
            reasoning=f"{asset} EXTREME setup - all systems go"
        )
    
    def enter_trade(self, signal: SignalAudit):
        """Enter a new trade based on signal"""
        self.trade_counter += 1
        trade_id = f"TRADE-{self.trade_counter:04d}"
        
        position_size = self.current_capital * signal.position_size
        
        trade = Trade(
            trade_id=trade_id,
            asset=signal.asset,
            entry_time=datetime.now(),
            entry_price=signal.entry_price,
            position_size_usd=position_size,
            conviction_score=signal.composite_score,
            signal_audit=signal.to_audit_log(),
            stop_loss=signal.stop_loss,
            tp1_price=signal.take_profit_1,
            tp2_price=signal.take_profit_2,
            tp3_price=signal.take_profit_3
        )
        
        self.open_trades[signal.asset] = trade
        
        print(f"\n[ENTRY] {trade_id}: {signal.asset}")
        print(f"  Time:  {trade.entry_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Price: ${trade.entry_price:,.2f}")
        print(f"  Size:  ${position_size:,.2f}")
        print(f"  Conviction: {signal.composite_score:.1f}/100")
    
    def update_positions(self, current_prices: Dict[str, float]):
        """Update open positions and check for exits"""
        for asset, trade in list(self.open_trades.items()):
            if asset not in current_prices:
                continue
            
            current_price = current_prices[asset]
            
            # Check stop loss
            if current_price <= trade.stop_loss:
                self.close_trade(asset, current_price, "STOP_LOSS")
            
            # Check take profits (simplified - just TP3 for demo)
            elif current_price >= trade.tp3_price:
                self.close_trade(asset, current_price, "TP3_HIT")
    
    def close_trade(self, asset: str, exit_price: float, reason: str):
        """Close a trade"""
        trade = self.open_trades.pop(asset)
        trade.close(exit_price, datetime.now(), reason)
        
        # Update capital with REALIZED P&L
        self.current_capital += trade.realized_pnl_usd
        
        self.closed_trades.append(trade)
        
        # Display
        pnl_color = "GREEN" if trade.realized_pnl_pct > 0 else "RED"
        emoji = "✅" if trade.realized_pnl_pct > 0 else "❌"
        
        print(f"\n[EXIT] {trade.trade_id}: {asset} {emoji}")
        print(f"  Entry:  {trade.entry_time.strftime('%Y-%m-%d %H:%M:%S')} @ ${trade.entry_price:,.2f}")
        print(f"  Exit:   {trade.exit_time.strftime('%Y-%m-%d %H:%M:%S')} @ ${exit_price:,.2f}")
        print(f"  Reason: {reason}")
        print(f"  P&L:    {trade.realized_pnl_pct*100:+.2f}% ({pnl_color})")
        print(f"  $ P&L:  ${trade.realized_pnl_usd:+,.2f}")
    
    def calculate_metrics(self) -> dict:
        """Calculate all metrics with CLEAR breakdown"""
        
        # REALIZED P&L (closed trades)
        total_realized_pnl = sum(t.realized_pnl_usd for t in self.closed_trades)
        
        # UNREALIZED P&L (open positions)
        current_prices = self.data_feed.get_prices()
        total_unrealized_pnl = 0
        for asset, trade in self.open_trades.items():
            if asset in current_prices:
                unrealized_pct = (current_prices[asset] - trade.entry_price) / trade.entry_price
                total_unrealized_pnl += unrealized_pct * trade.position_size_usd
        
        # TOTAL P&L
        total_pnl = total_realized_pnl + total_unrealized_pnl
        total_return_pct = (self.current_capital + total_unrealized_pnl - self.initial_capital) / self.initial_capital * 100
        
        # Trade statistics
        total_trades = len(self.closed_trades)
        winning_trades = [t for t in self.closed_trades if t.realized_pnl_usd > 0]
        losing_trades = [t for t in self.closed_trades if t.realized_pnl_usd <= 0]
        
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        
        avg_win = np.mean([t.realized_pnl_pct for t in winning_trades]) * 100 if winning_trades else 0
        avg_loss = np.mean([t.realized_pnl_pct for t in losing_trades]) * 100 if losing_trades else 0
        
        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'unrealized_pnl': total_unrealized_pnl,
            'realized_pnl': total_realized_pnl,
            'total_pnl': total_pnl,
            'total_return_pct': total_return_pct,
            'open_positions': len(self.open_trades),
            'closed_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'avg_win_pct': avg_win,
            'avg_loss_pct': avg_loss
        }
    
    def display_status(self):
        """Display CLEAR status with P&L breakdown"""
        metrics = self.calculate_metrics()
        current_prices = self.data_feed.get_prices()
        
        print("\n" + "=" * 80)
        print("CRYPTOALPHA PRO - WAR ROOM v2".center(80))
        print("=" * 80)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Session: {(datetime.now() - self.start_time).seconds // 60} minutes")
        print()
        
        # CAPITAL & P&L - CRYSTAL CLEAR
        print("💰 CAPITAL & P&L BREAKDOWN")
        print("-" * 80)
        print(f"  Initial Capital:     ${self.initial_capital:>12,.2f}")
        print(f"  Realized P&L:        ${metrics['realized_pnl']:>+12,.2f}  (closed trades)")
        print(f"  Unrealized P&L:      ${metrics['unrealized_pnl']:>+12,.2f}  (open positions)")
        print(f"  ─────────────────────────────────────────")
        print(f"  TOTAL P&L:           ${metrics['total_pnl']:>+12,.2f}")
        print(f"  TOTAL RETURN:        {metrics['total_return_pct']:>+11.2f}%")
        print()
        
        # TRADE STATISTICS
        print("📊 TRADE STATISTICS")
        print("-" * 80)
        print(f"  Open Positions:      {metrics['open_positions']}")
        print(f"  Closed Trades:       {metrics['closed_trades']}")
        print(f"  Win Rate:            {metrics['win_rate']:.1f}%")
        print(f"  Avg Win:             {metrics['avg_win_pct']:+.2f}%")
        print(f"  Avg Loss:            {metrics['avg_loss_pct']:+.2f}%")
        print()
        
        # OPEN POSITIONS - with entry details
        if self.open_trades:
            print("🎯 OPEN POSITIONS (UNREALIZED)")
            print("-" * 80)
            print(f"  {'Trade ID':<12} {'Asset':<6} {'Entry Time':<20} {'Entry $':<12} {'Current $':<12} {'P&L %':<10}")
            print(f"  {'-'*11:<12} {'-'*5:<6} {'-'*19:<20} {'-'*11:<12} {'-'*11:<12} {'-'*9:<10}")
            
            for asset, trade in self.open_trades.items():
                current = current_prices.get(asset, trade.entry_price)
                pnl_pct = (current - trade.entry_price) / trade.entry_price * 100
                print(f"  {trade.trade_id:<12} {asset:<6} {trade.entry_time.strftime('%Y-%m-%d %H:%M'):<20} "
                      f"${trade.entry_price:<11,.2f} ${current:<11,.2f} {pnl_pct:+.2f}%")
            print()
        
        # CLOSED TRADES - full history
        if self.closed_trades:
            print("⚔️  BATTLE HISTORY - CLOSED TRADES (REALIZED)")
            print("-" * 80)
            print(f"  {'Trade ID':<12} {'Asset':<6} {'Bought':<20} {'Sold':<20} {'P&L':<12} {'Result':<10}")
            print(f"  {'-'*11:<12} {'-'*5:<6} {'-'*19:<20} {'-'*19:<20} {'-'*11:<12} {'-'*9:<10}")
            
            for trade in reversed(self.closed_trades[-5:]):  # Last 5
                entry_time = trade.entry_time.strftime('%m/%d %H:%M')
                exit_time = trade.exit_time.strftime('%m/%d %H:%M')
                pnl_str = f"${trade.realized_pnl_usd:+,.2f}"
                result = "WIN" if trade.realized_pnl_usd > 0 else "LOSS"
                
                print(f"  {trade.trade_id:<12} {trade.asset:<6} {entry_time:<20} {exit_time:<20} "
                      f"{pnl_str:<12} {result:<10}")
            print()
        
        print("=" * 80)
    
    def save_report(self):
        """Save detailed report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'metrics': self.calculate_metrics(),
            'open_trades': [t.to_dict() for t in self.open_trades.values()],
            'closed_trades': [t.to_dict() for t in self.closed_trades]
        }
        
        filename = f"war_room_v2_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Report saved: {filename}")
    
    def run(self, interval: int = 10):
        """Main loop"""
        print("\n" + "=" * 80)
        print("WAR ROOM v2 - CLEAR P&L TRACKING")
        print("=" * 80)
        print(f"Starting Capital: ${self.initial_capital:,.2f}")
        print(f"Assets: {', '.join(self.assets)}")
        print()
        
        try:
            while True:
                # Get prices
                prices = self.data_feed.get_prices()
                
                # Update positions
                self.update_positions(prices)
                
                # Scan for new signals
                signals = self.scan_for_signals()
                for signal in signals:
                    self.enter_trade(signal)
                
                # Display status
                self.display_status()
                
                # Save report
                self.save_report()
                
                print(f"\n⏱️  Next update in {interval}s...")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n🛑 SHUTTING DOWN...")
            self.display_status()
            self.save_report()
            print("\n✅ Final report saved.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--assets', default='BTC,ETH,BNB,AVAX')
    parser.add_argument('--capital', type=float, default=10000.0)
    parser.add_argument('--interval', type=int, default=10)
    args = parser.parse_args()
    
    assets = [a.strip() for a in args.assets.split(',')]
    war_room = WarRoomV2(assets=assets, capital=args.capital)
    war_room.run(interval=args.interval)


if __name__ == '__main__':
    main()
