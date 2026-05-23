#!/usr/bin/env python3
"""
REAL 2-HOUR CHALLENGE - Live Market Data
Uses actual Binance API for real competition
"""

import json

# Failover helper — tries all Binance mirrors + circuit breaker + Bybit fallback
from shared.binance_api import binance_get, binance_futures_get
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

class RealTimeChallenge:
    """2-hour challenge with REAL market data from Binance"""
    
    def __init__(self):
        self.strategies = {
            'news_scalping': {'name': 'News_Scalping_AAPL', 'pnl': 0, 'trades': 0, 'capital': 10000},
            'momentum_ema': {'name': 'Momentum_EMA_SPY', 'pnl': 0, 'trades': 0, 'capital': 10000},
            'vwap': {'name': 'VWAP_Scalping_AAPL', 'pnl': 0, 'trades': 0, 'capital': 10000},
            'funding_arb': {'name': 'Funding_Arbitrage', 'pnl': 0, 'trades': 0, 'capital': 10000}
        }
        self.active_signals = {}
        self.start_time = None
        
    def get_binance_data(self, symbol: str, interval: str = '1m', limit: int = 100):
        """Fetch real data from Binance (with endpoint failover)"""
        try:
            data = binance_get(
                "/api/v3/klines",
                params={"symbol": symbol, "interval": interval, "limit": str(limit)},
            )
            if data:
                df = pd.DataFrame(data, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'taker_buy',
                    'taker_buy_quote', 'ignore'
                ])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = df[col].astype(float)
                return df
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
        return None
    
    def get_funding_rate(self, symbol: str):
        """Get funding rate for perpetual futures (with endpoint failover)"""
        try:
            data = binance_futures_get(
                "/fapi/v1/fundingRate",
                params={"symbol": symbol, "limit": "1"},
            )
            if data and isinstance(data, list) and data:
                return float(data[0]['fundingRate'])
        except Exception as e:
            print(f"Error fetching funding: {e}")
        return None
    
    def check_news_scalping(self, df: pd.DataFrame) -> dict:
        """
        News scalping strategy: Volume surge + momentum
        High win rate when volume spikes with price momentum
        """
        if len(df) < 20:
            return None
        
        current_vol = df['volume'].iloc[-1]
        vol_sma = df['volume'].rolling(20).mean().iloc[-1]
        price_change = (df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5]
        
        # Volume surge + momentum = news event
        if current_vol > 2.5 * vol_sma and abs(price_change) > 0.003:
            direction = "LONG" if price_change > 0 else "SHORT"
            return {
                'direction': direction,
                'confidence': min(75 + abs(price_change)*1000, 95),
                'entry': df['close'].iloc[-1],
                'stop': df['close'].iloc[-1] * (0.992 if direction == "LONG" else 1.008),
                'target': df['close'].iloc[-1] * (1.016 if direction == "LONG" else 0.984),
                'rationale': f'Volume {current_vol/vol_sma:.1f}x + momentum {price_change:.2%}'
            }
        return None
    
    def check_momentum_ema(self, df: pd.DataFrame) -> dict:
        """
        Momentum EMA strategy: EMA20 break + RSI + volume
        Trend following with confirmation
        """
        if len(df) < 20:
            return None
        
        ema20 = df['close'].ewm(span=20).mean().iloc[-1]
        current_price = df['close'].iloc[-1]
        
        # RSI calculation
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1]
        
        # Volume
        current_vol = df['volume'].iloc[-1]
        vol_sma = df['volume'].rolling(20).mean().iloc[-1]
        
        # Entry: Price above EMA20 + RSI > 50 + volume surge
        if current_price > ema20 and rsi > 50 and current_vol > 1.5 * vol_sma:
            return {
                'direction': 'LONG',
                'confidence': min(65 + (rsi-50)*0.5, 90),
                'entry': current_price,
                'stop': current_price * 0.995,
                'target': current_price * 1.015,
                'rationale': f'EMA break + RSI {rsi:.0f} + vol {current_vol/vol_sma:.1f}x'
            }
        return None
    
    def check_vwap(self, df: pd.DataFrame) -> dict:
        """
        VWAP strategy: Mean reversion to volume-weighted price
        Works well for liquid stocks/crypto
        """
        if len(df) < 20:
            return None
        
        # Calculate VWAP
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        
        current_price = df['close'].iloc[-1]
        current_vwap = vwap.iloc[-1]
        
        # Distance from VWAP
        distance = (current_price - current_vwap) / current_vwap
        
        # Entry: Price extends >0.5% from VWAP (mean reversion)
        if abs(distance) > 0.005:
            direction = "SHORT" if distance > 0 else "LONG"
            return {
                'direction': direction,
                'confidence': min(60 + abs(distance)*2000, 85),
                'entry': current_price,
                'stop': current_price * (1.005 if direction == "SHORT" else 0.995),
                'target': current_vwap,
                'rationale': f'VWAP deviation {distance:.2%}'
            }
        return None
    
    def check_funding_arb(self, symbol: str, funding_rate: float, df: pd.DataFrame) -> dict:
        """
        Funding arbitrage: Collect funding when rate is extreme
        Delta-neutral strategy
        """
        if funding_rate is None:
            return None
        
        # Extreme funding rate = opportunity
        if abs(funding_rate) > 0.0001:  # >0.01%
            direction = "SHORT" if funding_rate > 0 else "LONG"
            return {
                'direction': direction,
                'confidence': min(80 + abs(funding_rate)*10000, 95),
                'entry': df['close'].iloc[-1],
                'stop': df['close'].iloc[-1] * 0.95,  # Wide stop for delta-neutral
                'target': df['close'].iloc[-1] * 1.05,
                'rationale': f'Funding rate {funding_rate:.4%}'
            }
        return None
    
    def update_signals(self, strategy: str, signal: dict, current_price: float):
        """Update active signals and check exits"""
        if strategy not in self.active_signals:
            self.active_signals[strategy] = []
        
        # Check existing signals for exits
        for sig in self.active_signals[strategy][:]:
            pnl = 0
            exit_triggered = False
            
            if sig['direction'] == 'LONG':
                if current_price <= sig['stop']:
                    pnl = (sig['stop'] - sig['entry']) / sig['entry']
                    exit_triggered = True
                elif current_price >= sig['target']:
                    pnl = (sig['target'] - sig['entry']) / sig['entry']
                    exit_triggered = True
            else:  # SHORT
                if current_price >= sig['stop']:
                    pnl = (sig['entry'] - sig['stop']) / sig['entry']
                    exit_triggered = True
                elif current_price <= sig['target']:
                    pnl = (sig['entry'] - sig['target']) / sig['entry']
                    exit_triggered = True
            
            if exit_triggered:
                self.strategies[strategy]['pnl'] += pnl * self.strategies[strategy]['capital']
                self.strategies[strategy]['capital'] += pnl * self.strategies[strategy]['capital']
                self.strategies[strategy]['trades'] += 1
                self.active_signals[strategy].remove(sig)
                
                emoji = "🟢" if pnl > 0 else "🔴"
                print(f"  {emoji} {strategy}: Closed {sig['direction']} | P&L: {pnl:.2%}")
        
        # Add new signal
        if signal and len(self.active_signals[strategy]) < 2:  # Max 2 concurrent
            self.active_signals[strategy].append({
                'direction': signal['direction'],
                'entry': signal['entry'],
                'stop': signal['stop'],
                'target': signal['target'],
                'time': datetime.utcnow()
            })
            print(f"  🎯 {strategy}: New {signal['direction']} signal | Conf: {signal['confidence']:.0f}%")
    
    def run_challenge(self, duration_minutes: int = 120):
        """Run the 2-hour challenge with REAL data"""
        self.start_time = datetime.utcnow()
        end_time = self.start_time + timedelta(minutes=duration_minutes)
        
        print("=" * 70)
        print("🏆 2-HOUR STRATEGY CHALLENGE - LIVE WITH REAL DATA")
        print("=" * 70)
        print(f"Start: {self.start_time.isoformat()} UTC")
        print(f"End: {end_time.isoformat()} UTC")
        print(f"Assets: BTC, ETH, SOL (real Binance data)")
        print("=" * 70)
        print()
        
        iteration = 0
        while datetime.utcnow() < end_time:
            iteration += 1
            elapsed = (datetime.utcnow() - self.start_time).total_seconds() / 60
            remaining = duration_minutes - elapsed
            
            print(f"\n[{datetime.utcnow().strftime('%H:%M:%S')}] Iteration {iteration} | Elapsed: {elapsed:.0f}m | Remaining: {remaining:.0f}m")
            print("-" * 70)
            
            # Fetch real data
            btc_data = self.get_binance_data('BTCUSDT', '1m', 100)
            eth_data = self.get_binance_data('ETHUSDT', '1m', 100)
            sol_data = self.get_binance_data('SOLUSDT', '1m', 100)
            
            btc_funding = self.get_funding_rate('BTCUSDT')
            eth_funding = self.get_funding_rate('ETHUSDT')
            
            # Check each strategy
            if btc_data is not None:
                # News scalping on BTC
                signal = self.check_news_scalping(btc_data)
                self.update_signals('news_scalping', signal, btc_data['close'].iloc[-1])
                
                # Momentum EMA on BTC
                signal = self.check_momentum_ema(btc_data)
                self.update_signals('momentum_ema', signal, btc_data['close'].iloc[-1])
                
                # VWAP on BTC
                signal = self.check_vwap(btc_data)
                self.update_signals('vwap', signal, btc_data['close'].iloc[-1])
                
                # Funding arb on BTC
                signal = self.check_funding_arb('BTCUSDT', btc_funding, btc_data)
                self.update_signals('funding_arb', signal, btc_data['close'].iloc[-1])
            
            # Print leaderboard every 5 minutes
            if iteration % 5 == 0:
                self.print_leaderboard()
            
            # Save results
            self.save_results()
            
            # Wait 1 minute
            time.sleep(60)
        
        self.print_final_results()
    
    def print_leaderboard(self):
        """Print current standings"""
        print("\n📊 LEADERBOARD:")
        print("-" * 70)
        
        sorted_strategies = sorted(self.strategies.items(), 
                                   key=lambda x: x[1]['pnl'], reverse=True)
        
        for i, (key, data) in enumerate(sorted_strategies, 1):
            pnl_pct = (data['pnl'] / 10000) * 100
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
            active = len(self.active_signals.get(key, []))
            print(f"{medal} {i}. {data['name']:25} | ${data['pnl']:8.2f} ({pnl_pct:+.2f}%) | Trades: {data['trades']} | Active: {active}")
    
    def print_final_results(self):
        """Print final results"""
        print("\n" + "=" * 70)
        print("🏆 FINAL RESULTS - 2 HOUR CHALLENGE")
        print("=" * 70)
        
        sorted_strategies = sorted(self.strategies.items(), 
                                   key=lambda x: x[1]['pnl'], reverse=True)
        
        winner_key, winner_data = sorted_strategies[0]
        winner_pnl_pct = (winner_data['pnl'] / 10000) * 100
        
        print(f"\n🥇 WINNER: {winner_data['name']}")
        print(f"   Final P&L: ${winner_data['pnl']:.2f} ({winner_pnl_pct:+.2f}%)")
        print(f"   Total Trades: {winner_data['trades']}")
        print(f"   Final Capital: ${winner_data['capital'] + winner_data['pnl']:.2f}")
        
        print("\n📊 FULL STANDINGS:")
        print("-" * 70)
        for i, (key, data) in enumerate(sorted_strategies, 1):
            pnl_pct = (data['pnl'] / 10000) * 100
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
            print(f"{medal} {i}. {data['name']:25} | ${data['pnl']:8.2f} ({pnl_pct:+.2f}%) | {data['trades']} trades")
        
        self.save_results(final=True)
    
    def save_results(self, final: bool = False):
        """Save results to file"""
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'strategies': self.strategies,
            'active_signals': {k: len(v) for k, v in self.active_signals.items()}
        }
        
        filename = 'REAL_CHALLENGE_RESULTS.json'
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        if final:
            # Create markdown report
            sorted_strategies = sorted(self.strategies.items(), 
                                       key=lambda x: x[1]['pnl'], reverse=True)
            winner = sorted_strategies[0][1]
            
            with open('REAL_CHALLENGE_FINAL.md', 'w') as f:
                f.write("# 🏆 2-HOUR STRATEGY CHALLENGE - FINAL RESULTS\n\n")
                f.write(f"**Completed:** {datetime.utcnow().isoformat()} UTC\n\n")
                f.write(f"## 🥇 WINNER: {winner['name']}\n\n")
                f.write(f"- **Final P&L:** ${winner['pnl']:.2f}\n")
                f.write(f"- **Return:** {(winner['pnl']/10000)*100:+.2f}%\n")
                f.write(f"- **Total Trades:** {winner['trades']}\n\n")
                f.write("## 📊 Full Standings\n\n")
                f.write("| Rank | Strategy | P&L | Return % | Trades |\n")
                f.write("|------|----------|-----|----------|--------|\n")
                for i, (key, data) in enumerate(sorted_strategies, 1):
                    pnl_pct = (data['pnl'] / 10000) * 100
                    f.write(f"| {i} | {data['name']} | ${data['pnl']:.2f} | {pnl_pct:+.2f}% | {data['trades']} |\n")
            
            print("\n✅ Results saved to REAL_CHALLENGE_RESULTS.json and REAL_CHALLENGE_FINAL.md")

if __name__ == "__main__":
    print("🚀 REAL 2-HOUR CHALLENGE")
    print("Using live Binance data")
    print("Press Ctrl+C to stop early")
    print()
    
    challenge = RealTimeChallenge()
    
    try:
        challenge.run_challenge(duration_minutes=120)
    except KeyboardInterrupt:
        print("\n\n⚠️ Stopped by user")
        challenge.print_final_results()
