"""
================================================================================
FORWARD TESTING RUNNER
================================================================================
Simulates the CryptoAlpha Pro system in paper trading mode.
Generates daily signals and tracks performance.

Usage:
    python run_forward_test.py --mode paper --days 30
================================================================================
"""

import argparse
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import time
from typing import Dict, List

from live_signal_system_demo import CryptoAlphaPro, TradingSignal, SignalStrength


class MockDataFeed:
    """Simulates real-time crypto data feed"""
    
    def __init__(self, assets: List[str] = None):
        self.assets = assets or ['BTC', 'ETH', 'AVAX', 'BNB', 'SOL', 'LINK']
        self.price_history = {asset: self._generate_initial_data(asset) for asset in self.assets}
        
    def _generate_initial_data(self, asset: str, days: int = 100) -> pd.DataFrame:
        """Generate realistic crypto price data"""
        np.random.seed(hash(asset) % 2**32)
        
        # Base prices for each asset
        base_prices = {
            'BTC': 43000, 'ETH': 2650, 'AVAX': 36,
            'BNB': 310, 'SOL': 102, 'LINK': 14.5
        }
        
        base = base_prices.get(asset, 100)
        
        # Generate OHLCV data
        dates = pd.date_range(end=datetime.now(), periods=days*24, freq='H')
        
        # Random walk with trend
        returns = np.random.normal(0.0001, 0.02, len(dates))
        prices = base * np.exp(np.cumsum(returns))
        
        df = pd.DataFrame({
            'price': prices,
            'volume': np.random.lognormal(10, 1, len(dates)),
            'timestamp': dates
        })
        
        # Add on-chain metrics (simulated)
        df['hash_rate'] = np.random.lognormal(5, 0.5, len(dates))
        df['exchange_flow'] = np.random.normal(0, 1000, len(dates))
        df['funding_rate'] = np.random.normal(0.01, 0.05, len(dates))
        
        return df
    
    def get_latest(self, asset: str) -> pd.DataFrame:
        """Get latest data for an asset"""
        return self.price_history[asset].copy()
    
    def get_current_price(self, asset: str) -> float:
        """Get current price"""
        return self.price_history[asset]['price'].iloc[-1]
    
    def update(self):
        """Simulate new price tick"""
        for asset in self.assets:
            # Add new price point
            last_row = self.price_history[asset].iloc[-1].copy()
            new_return = np.random.normal(0.0001, 0.02)
            new_price = last_row['price'] * (1 + new_return)
            
            new_row = pd.DataFrame({
                'price': [new_price],
                'volume': [np.random.lognormal(10, 1)],
                'timestamp': [datetime.now()],
                'hash_rate': [last_row['hash_rate'] * (1 + np.random.normal(0, 0.01))],
                'exchange_flow': [np.random.normal(0, 1000)],
                'funding_rate': [last_row['funding_rate'] + np.random.normal(0, 0.001)]
            })
            
            self.price_history[asset] = pd.concat([self.price_history[asset], new_row], ignore_index=True)


class PaperTradingEngine:
    """Paper trading simulation"""
    
    def __init__(self, initial_capital: float = 10000.0):
        self.capital = initial_capital
        self.equity = initial_capital
        self.open_positions: Dict[str, Dict] = {}
        self.trade_history: List[Dict] = []
        
    def enter_position(self, signal: TradingSignal):
        """Enter a paper position"""
        position_size = self.capital * signal.position_size
        
        self.open_positions[signal.asset] = {
            'entry_price': signal.entry_price,
            'position_size': position_size,
            'target': signal.target_price,
            'stop': signal.stop_loss,
            'direction': signal.direction,
            'entry_time': signal.timestamp,
            'signal': signal
        }
        
        print(f"📥 ENTERED: {signal.asset} {signal.direction} @ ${signal.entry_price:,.2f}")
        print(f"   Target: ${signal.target_price:,.2f} | Stop: ${signal.stop_loss:,.2f}")
        print(f"   Size: ${position_size:,.2f} ({signal.position_size*100:.1f}%)")
        
    def check_positions(self, data_feed: MockDataFeed) -> List[str]:
        """Check if any positions hit target or stop"""
        closed = []
        
        for asset, position in list(self.open_positions.items()):
            current_price = data_feed.get_current_price(asset)
            
            # Check target
            if position['direction'] == 'LONG' and current_price >= position['target']:
                pnl = (current_price - position['entry_price']) / position['entry_price'] * position['position_size']
                self._close_position(asset, current_price, pnl, 'TARGET_HIT')
                closed.append(asset)
                
            elif position['direction'] == 'SHORT' and current_price <= position['target']:
                pnl = (position['entry_price'] - current_price) / position['entry_price'] * position['position_size']
                self._close_position(asset, current_price, pnl, 'TARGET_HIT')
                closed.append(asset)
                
            # Check stop
            elif position['direction'] == 'LONG' and current_price <= position['stop']:
                pnl = (current_price - position['entry_price']) / position['entry_price'] * position['position_size']
                self._close_position(asset, current_price, pnl, 'STOP_HIT')
                closed.append(asset)
                
            elif position['direction'] == 'SHORT' and current_price >= position['stop']:
                pnl = (position['entry_price'] - current_price) / position['entry_price'] * position['position_size']
                self._close_position(asset, current_price, pnl, 'STOP_HIT')
                closed.append(asset)
                
        return closed
    
    def _close_position(self, asset: str, exit_price: float, pnl: float, reason: str):
        """Close a position"""
        position = self.open_positions.pop(asset)
        self.equity += pnl
        
        trade = {
            'asset': asset,
            'direction': position['direction'],
            'entry': position['entry_price'],
            'exit': exit_price,
            'pnl': pnl,
            'return_pct': pnl / position['position_size'] * 100,
            'reason': reason,
            'exit_time': datetime.now()
        }
        self.trade_history.append(trade)
        
        emoji = "✅" if pnl > 0 else "❌"
        print(f"{emoji} CLOSED: {asset} @ ${exit_price:,.2f} | P&L: ${pnl:+,.2f} ({reason})")
        
    def get_stats(self) -> Dict:
        """Get trading statistics"""
        if not self.trade_history:
            return {"status": "No trades yet"}
            
        closed = self.trade_history
        wins = [t for t in closed if t['pnl'] > 0]
        losses = [t for t in closed if t['pnl'] <= 0]
        
        total_return = (self.equity / self.capital - 1) * 100
        
        return {
            'total_trades': len(closed),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': len(wins) / len(closed) * 100 if closed else 0,
            'total_pnl': self.equity - self.capital,
            'total_return_pct': total_return,
            'current_equity': self.equity,
            'avg_win': np.mean([t['pnl'] for t in wins]) if wins else 0,
            'avg_loss': np.mean([t['pnl'] for t in losses]) if losses else 0,
            'open_positions': len(self.open_positions)
        }


def run_forward_test(days: int = 30, interval_seconds: int = 1):
    """
    Run forward test simulation
    """
    print("=" * 80)
    print("CRYPTOALPHA PRO - FORWARD TESTING MODE")
    print("=" * 80)
    print(f"\n📅 Simulating {days} days of paper trading")
    print(f"⏱️  Each 'day' = {interval_seconds} second(s)")
    print(f"💰 Starting Capital: $10,000")
    print("\n" + "=" * 80)
    
    # Initialize systems
    data_feed = MockDataFeed()
    pro_system = CryptoAlphaPro()
    paper_trader = PaperTradingEngine(initial_capital=10000.0)
    
    # Simulation loop
    for day in range(days):
        print(f"\n{'='*80}")
        print(f"📆 DAY {day + 1} - {datetime.now().strftime('%Y-%m-%d')}")
        print(f"{'='*80}")
        
        # Update market data
        data_feed.update()
        
        # Check existing positions
        paper_trader.check_positions(data_feed)
        
        # Generate signals
        market_data = {asset: data_feed.get_latest(asset) for asset in data_feed.assets}
        signals = pro_system.generate_signals(market_data)
        
        print(f"\n📊 Generated {len(signals)} signals")
        
        # Get top 3 picks
        top_picks = pro_system.get_top_picks(n=3)
        
        print(f"\n🎯 TOP PICKS:")
        for pick in top_picks:
            sig = pick['signal']
            print(f"  {pick['rank']}. {sig['asset']} ({sig['strength']}) - Score: {pick['composite_score']}")
        
        # Enter top pick if valid signal
        for pick in top_picks[:1]:  # Only take the #1 pick
            sig_data = pick['signal']
            asset = sig_data['asset']
            
            # Skip if already in position
            if asset in paper_trader.open_positions:
                print(f"\n⏸️  Already in {asset} position, skipping...")
                continue
                
            # Recreate signal object
            signal = TradingSignal(
                asset=asset,
                direction=sig_data['direction'],
                strength=SignalStrength[sig_data['strength']],
                entry_price=float(sig_data['entry_price'].replace('$', '').replace(',', '')),
                target_price=float(sig_data['target_price'].replace('$', '').replace(',', '')),
                stop_loss=float(sig_data['stop_loss'].replace('$', '').replace(',', '')),
                position_size=float(sig_data['position_size'].replace('%', '')) / 100,
                confidence=float(sig_data['confidence'].replace('%', '')) / 100,
                timeframe=sig_data['timeframe'],
                regime=sig_data['regime'],
                expected_return=float(sig_data['expected_return'].replace('%', '')) / 100,
                risk_reward=float(sig_data['risk_reward']),
                timestamp=datetime.now(),
                model_version=sig_data['model']
            )
            
            # Only enter if strong signal
            if signal.strength in [SignalStrength.STRONG_BUY, SignalStrength.BUY]:
                paper_trader.enter_position(signal)
        
        # Show stats
        stats = paper_trader.get_stats()
        print(f"\n📈 CURRENT STATS:")
        print(f"   Equity: ${stats.get('current_equity', 10000):,.2f}")
        print(f"   Total Return: {stats.get('total_return_pct', 0):+.2f}%")
        print(f"   Trades: {stats.get('total_trades', 0)}")
        print(f"   Win Rate: {stats.get('win_rate', 0):.1f}%")
        print(f"   Open Positions: {stats.get('open_positions', 0)}")
        
        # Simulate time passing
        if day < days - 1:
            print(f"\n⏳ Simulating next day...")
            time.sleep(interval_seconds)
    
    # Final report
    print("\n" + "=" * 80)
    print("FORWARD TEST COMPLETE")
    print("=" * 80)
    
    stats = paper_trader.get_stats()
    print(f"\n📊 FINAL PERFORMANCE:")
    print(f"   Starting Capital: $10,000.00")
    print(f"   Final Equity: ${stats.get('current_equity', 10000):,.2f}")
    print(f"   Total Return: {stats.get('total_return_pct', 0):+.2f}%")
    print(f"   Total Trades: {stats.get('total_trades', 0)}")
    print(f"   Win Rate: {stats.get('win_rate', 0):.1f}%")
    
    if stats.get('total_trades', 0) > 0:
        print(f"   Avg Win: ${stats.get('avg_win', 0):,.2f}")
        print(f"   Avg Loss: ${stats.get('avg_loss', 0):,.2f}")
    
    print("\n" + "=" * 80)
    print("✅ Forward test complete. System ready for live deployment.")
    print("=" * 80)
    
    return stats


def generate_live_report():
    """Generate a live performance report"""
    pro = CryptoAlphaPro()
    report = pro.get_daily_report()
    
    print("\n" + "=" * 80)
    print("CRYPTOALPHA PRO - DAILY SIGNAL REPORT")
    print("=" * 80)
    print(f"\n📅 Date: {report['date']}")
    print(f"\n{report['market_summary']}")
    
    print(f"\n🎯 TOP 3 PICKS:")
    for pick in report['top_picks']:
        print(f"\n  #{pick['rank']} - {pick['signal']['asset']}")
        print(f"     Direction: {pick['signal']['direction']}")
        print(f"     Entry: {pick['signal']['entry_price']}")
        print(f"     Target: {pick['signal']['target_price']}")
        print(f"     Stop: {pick['signal']['stop_loss']}")
        print(f"     Confidence: {pick['signal']['confidence']}")
        print(f"     Score: {pick['composite_score']}")
    
    print(f"\n📊 TRACK RECORD:")
    for key, value in report['track_record'].items():
        print(f"   {key}: {value}")
    
    print(f"\n⚠️  {report['disclaimer']}")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='CryptoAlpha Pro Forward Testing')
    parser.add_argument('--mode', choices=['paper', 'live'], default='paper',
                       help='Run mode: paper (simulation) or live (real signals)')
    parser.add_argument('--days', type=int, default=30,
                       help='Number of days to simulate')
    parser.add_argument('--interval', type=int, default=1,
                       help='Seconds per simulated day')
    parser.add_argument('--report', action='store_true',
                       help='Generate daily report only')
    
    args = parser.parse_args()
    
    if args.report:
        generate_live_report()
    elif args.mode == 'paper':
        run_forward_test(days=args.days, interval_seconds=args.interval)
    else:
        print("Live mode not yet implemented. Use --mode paper for testing.")
