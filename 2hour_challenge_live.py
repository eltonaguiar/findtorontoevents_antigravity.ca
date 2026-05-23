#!/usr/bin/env python3
"""
2-HOUR CHALLENGE - LIVE with Real Market Data (EST)
Pits viable strategies against each other using actual price feeds
"""

import requests
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

class EST2HourChallenge:
    """
    2-hour live trading challenge with real market data
    All timestamps in EST
    """
    
    def __init__(self):
        self.est_tz = timezone(timedelta(hours=-5))
        self.start_time = None
        self.end_time = None
        self.running = False
        
        # Strategies with their performance
        self.strategies = {
            'News_Scalping': {'pnl': 0, 'trades': 0, 'wins': 0, 'capital': 10000},
            'Momentum_EMA': {'pnl': 0, 'trades': 0, 'wins': 0, 'capital': 10000},
            'VWAP_MeanReversion': {'pnl': 0, 'trades': 0, 'wins': 0, 'capital': 10000},
            'Funding_Arbitrage': {'pnl': 0, 'trades': 0, 'wins': 0, 'capital': 10000}
        }
        
        self.active_signals: List[Dict] = []
        self.completed_trades: List[Dict] = []
        
    def get_est_time(self) -> datetime:
        """Get current time in EST"""
        return datetime.now(self.est_tz)
    
    def format_est(self, dt: datetime = None) -> str:
        """Format timestamp in EST"""
        if dt is None:
            dt = self.get_est_time()
        return dt.strftime('%Y-%m-%d %H:%M:%S EST')
    
    def fetch_prices(self) -> Dict:
        """Fetch live crypto prices from Binance"""
        prices = {}
        symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT']
        
        for symbol in symbols:
            try:
                url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    prices[symbol] = {
                        'price': float(data['lastPrice']),
                        'change': float(data['priceChangePercent']),
                        'volume': float(data['volume']),
                        'high': float(data['highPrice']),
                        'low': float(data['lowPrice']),
                        'timestamp': self.format_est()
                    }
            except Exception as e:
                print(f"Error fetching {symbol}: {e}")
        
        return prices
    
    def check_strategy_signals(self, prices: Dict) -> List[Dict]:
        """Check all strategies for signals based on real prices"""
        signals = []
        est_time = self.get_est_time()
        
        # 1. News Scalping - Look for volume + momentum
        for symbol, data in prices.items():
            # Simulate volume surge detection
            if abs(data['change']) > 1.5:  # >1.5% move = news/volume
                direction = "LONG" if data['change'] > 0 else "SHORT"
                signals.append({
                    'strategy': 'News_Scalping',
                    'symbol': symbol,
                    'direction': direction,
                    'entry_price': data['price'],
                    'stop': data['price'] * (0.985 if direction == "LONG" else 1.015),
                    'target': data['price'] * (1.03 if direction == "LONG" else 0.97),
                    'confidence': min(abs(data['change']) * 20, 90),
                    'timestamp_est': self.format_est(est_time),
                    'rationale': f"Price move {data['change']:+.2f}% indicates volume surge"
                })
        
        # 2. Momentum EMA - Trend following
        btc = prices.get('BTCUSDT')
        if btc and abs(btc['change']) > 0.5:
            direction = "LONG" if btc['change'] > 0 else "SHORT"
            signals.append({
                'strategy': 'Momentum_EMA',
                'symbol': 'BTCUSDT',
                'direction': direction,
                'entry_price': btc['price'],
                'stop': btc['price'] * (0.99 if direction == "LONG" else 1.01),
                'target': btc['price'] * (1.02 if direction == "LONG" else 0.98),
                'confidence': 65,
                'timestamp_est': self.format_est(est_time),
                'rationale': f"BTC momentum {btc['change']:+.2f}%"
            })
        
        # 3. VWAP Mean Reversion - Price far from VWAP
        for symbol, data in prices.items():
            # Simulate VWAP deviation
            mid_range = (data['high'] + data['low']) / 2
            deviation = (data['price'] - mid_range) / mid_range
            
            if abs(deviation) > 0.01:  # >1% from mid
                direction = "SHORT" if deviation > 0 else "LONG"  # Revert
                signals.append({
                    'strategy': 'VWAP_MeanReversion',
                    'symbol': symbol,
                    'direction': direction,
                    'entry_price': data['price'],
                    'stop': data['price'] * (1.015 if direction == "SHORT" else 0.985),
                    'target': mid_range,
                    'confidence': 60,
                    'timestamp_est': self.format_est(est_time),
                    'rationale': f"VWAP deviation {deviation:.2%}"
                })
        
        return signals
    
    def execute_signal(self, signal: Dict):
        """Execute a trading signal"""
        # Check if we already have a signal for this strategy+symbol
        existing = [s for s in self.active_signals 
                   if s['strategy'] == signal['strategy'] and s['symbol'] == signal['symbol']]
        
        if existing:
            return
        
        signal['signal_id'] = len(self.active_signals)
        signal['status'] = 'ACTIVE'
        self.active_signals.append(signal)
        
        print(f"\n🎯 NEW SIGNAL [{signal['timestamp_est']}]")
        print(f"   {signal['strategy']} | {signal['symbol']} {signal['direction']}")
        print(f"   Entry: ${signal['entry_price']:,.2f}")
        print(f"   Stop: ${signal['stop']:,.2f} | Target: ${signal['target']:,.2f}")
        print(f"   Confidence: {signal['confidence']}%")
    
    def check_exits(self, prices: Dict):
        """Check if any active signals hit stop or target"""
        for signal in self.active_signals[:]:
            symbol = signal['symbol']
            if symbol not in prices:
                continue
            
            current_price = prices[symbol]['price']
            exit_triggered = False
            exit_price = current_price
            exit_reason = ""
            pnl = 0
            
            if signal['direction'] == 'LONG':
                if current_price <= signal['stop']:
                    exit_triggered = True
                    exit_reason = "STOP_LOSS"
                    exit_price = signal['stop']
                elif current_price >= signal['target']:
                    exit_triggered = True
                    exit_reason = "TAKE_PROFIT"
                    exit_price = signal['target']
            else:  # SHORT
                if current_price >= signal['stop']:
                    exit_triggered = True
                    exit_reason = "STOP_LOSS"
                    exit_price = signal['stop']
                elif current_price <= signal['target']:
                    exit_triggered = True
                    exit_reason = "TAKE_PROFIT"
                    exit_price = signal['target']
            
            # Time-based exit (30 min max)
            entry_time = datetime.strptime(signal['timestamp_est'], '%Y-%m-%d %H:%M:%S EST')
            elapsed = (self.get_est_time() - entry_time.replace(tzinfo=self.est_tz)).total_seconds() / 60
            
            if elapsed > 30 and not exit_triggered:
                exit_triggered = True
                exit_reason = "TIME_EXIT"
                exit_price = current_price
            
            if exit_triggered:
                # Calculate P&L
                if signal['direction'] == 'LONG':
                    pnl = (exit_price - signal['entry_price']) / signal['entry_price']
                else:
                    pnl = (signal['entry_price'] - exit_price) / signal['entry_price']
                
                self.close_trade(signal, exit_price, exit_reason, pnl)
    
    def close_trade(self, signal: Dict, exit_price: float, reason: str, pnl: float):
        """Close a trade and update performance"""
        est_time = self.get_est_time()
        
        trade = {
            'signal_id': signal['signal_id'],
            'strategy': signal['strategy'],
            'symbol': signal['symbol'],
            'direction': signal['direction'],
            'entry': signal['entry_price'],
            'exit': exit_price,
            'pnl': pnl,
            'exit_reason': reason,
            'entry_time': signal['timestamp_est'],
            'exit_time': self.format_est(est_time)
        }
        
        self.completed_trades.append(trade)
        self.active_signals.remove(signal)
        
        # Update strategy performance
        strategy = signal['strategy']
        self.strategies[strategy]['trades'] += 1
        self.strategies[strategy]['pnl'] += pnl
        if pnl > 0:
            self.strategies[strategy]['wins'] += 1
        
        emoji = "✅" if pnl > 0 else "❌"
        print(f"\n{emoji} TRADE CLOSED [{trade['exit_time']}]")
        print(f"   {trade['strategy']} | {trade['symbol']} | P&L: {pnl:+.2f}%")
        print(f"   Reason: {reason}")
    
    def print_leaderboard(self):
        """Print current standings"""
        print("\n" + "=" * 70)
        print("🏆 2-HOUR CHALLENGE LEADERBOARD")
        print("=" * 70)
        print(f"Time: {self.format_est()}")
        print(f"Active Signals: {len(self.active_signals)}")
        print("-" * 70)
        
        # Sort by P&L
        sorted_strategies = sorted(
            self.strategies.items(),
            key=lambda x: x[1]['pnl'],
            reverse=True
        )
        
        for i, (name, stats) in enumerate(sorted_strategies, 1):
            pnl_pct = stats['pnl'] * 100
            win_rate = stats['wins'] / stats['trades'] if stats['trades'] > 0 else 0
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
            
            print(f"{medal} {i}. {name:20} | P&L: {pnl_pct:+6.2f}% | Trades: {stats['trades']} | WR: {win_rate:.0%}")
        
        print("=" * 70)
    
    def run_challenge(self, duration_minutes: int = 120):
        """Run the 2-hour challenge"""
        self.start_time = self.get_est_time()
        self.end_time = self.start_time + timedelta(minutes=duration_minutes)
        self.running = True
        
        print("\n" + "=" * 70)
        print("🔴 2-HOUR STRATEGY CHALLENGE - LIVE")
        print("=" * 70)
        print(f"Start: {self.format_est(self.start_time)}")
        print(f"End:   {self.format_est(self.end_time)}")
        print(f"All timestamps in EST (UTC-5)")
        print("=" * 70)
        
        iteration = 0
        while self.running and self.get_est_time() < self.end_time:
            iteration += 1
            
            # Fetch live prices
            prices = self.fetch_prices()
            
            if prices:
                # Check for new signals
                signals = self.check_strategy_signals(prices)
                for signal in signals:
                    self.execute_signal(signal)
                
                # Check for exits
                self.check_exits(prices)
            
            # Print leaderboard every 5 minutes
            if iteration % 5 == 0:
                self.print_leaderboard()
            
            # Check if time's up
            if self.get_est_time() >= self.end_time:
                self.running = False
            else:
                time.sleep(60)  # Wait 1 minute
        
        self.print_final_results()
    
    def print_final_results(self):
        """Print final challenge results"""
        print("\n" + "=" * 70)
        print("🏆 FINAL RESULTS - 2 HOUR CHALLENGE")
        print("=" * 70)
        print(f"Completed: {self.format_est()}")
        print()
        
        # Sort by P&L
        sorted_strategies = sorted(
            self.strategies.items(),
            key=lambda x: x[1]['pnl'],
            reverse=True
        )
        
        winner_name, winner_stats = sorted_strategies[0]
        winner_pnl = winner_stats['pnl'] * 100
        
        print(f"🥇 WINNER: {winner_name}")
        print(f"   Final P&L: {winner_pnl:+.2f}%")
        print(f"   Total Trades: {winner_stats['trades']}")
        print(f"   Win Rate: {winner_stats['wins']/winner_stats['trades']:.1%}" if winner_stats['trades'] > 0 else "   Win Rate: N/A")
        print()
        
        print("📊 FULL STANDINGS:")
        print("-" * 70)
        for i, (name, stats) in enumerate(sorted_strategies, 1):
            pnl_pct = stats['pnl'] * 100
            win_rate = stats['wins'] / stats['trades'] if stats['trades'] > 0 else 0
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
            print(f"{medal} {i}. {name:20} | {pnl_pct:+6.2f}% | {stats['trades']} trades | {win_rate:.0%} WR")
        
        print("=" * 70)
        
        # Save results
        results = {
            'completed_at_est': self.format_est(),
            'winner': winner_name,
            'final_standings': {name: {
                'pnl_pct': stats['pnl'] * 100,
                'trades': stats['trades'],
                'wins': stats['wins']
            } for name, stats in sorted_strategies},
            'all_trades': self.completed_trades
        }
        
        with open('2HOUR_CHALLENGE_RESULTS.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print("\n💾 Results saved to 2HOUR_CHALLENGE_RESULTS.json")

def main():
    """Run the 2-hour challenge"""
    challenge = EST2HourChallenge()
    
    try:
        challenge.run_challenge(duration_minutes=120)
    except KeyboardInterrupt:
        print("\n\n⚠️ Challenge interrupted by user")
        challenge.print_final_results()

if __name__ == "__main__":
    print("🏆 2-HOUR STRATEGY CHALLENGE")
    print("Using REAL market data from Binance")
    print("All timestamps in EST (UTC-5)")
    print("\nPress Ctrl+C to stop early\n")
    
    main()
