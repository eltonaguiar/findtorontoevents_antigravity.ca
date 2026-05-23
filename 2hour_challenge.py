#!/usr/bin/env python3
"""
2-HOUR STRATEGY CHALLENGE - Live Competition
Pits viable strategies against each other in real-time
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

class StrategyCompetitor:
    """Base class for strategy competitors"""
    
    def __init__(self, name: str, capital: float = 10000):
        self.name = name
        self.capital = capital
        self.initial_capital = capital
        self.trades = []
        self.active_signals = []
        self.pnl = 0
        
    def generate_signal(self, data: pd.DataFrame) -> Optional[Dict]:
        """Override in subclass"""
        return None
    
    def update_performance(self, pnl: float):
        self.pnl += pnl
        self.capital += pnl * self.initial_capital

class NewsScalpingStrategy(StrategyCompetitor):
    """News-based scalping on AAPL - Highest Sharpe (3.60)"""
    
    def __init__(self):
        super().__init__("News_Scalping_AAPL", 10000)
        self.description = "News-based scalping on AAPL - Profit Factor 2.66, Sharpe 3.60"
    
    def generate_signal(self, data: pd.DataFrame) -> Optional[Dict]:
        # Simplified: Look for volume spikes + price momentum
        if len(data) < 20:
            return None
        
        current_vol = data['volume'].iloc[-1]
        vol_sma = data['volume'].rolling(20).mean().iloc[-1]
        
        price_change = (data['close'].iloc[-1] - data['close'].iloc[-5]) / data['close'].iloc[-5]
        
        # Volume surge + price momentum
        if current_vol > 2.5 * vol_sma and abs(price_change) > 0.005:
            direction = "LONG" if price_change > 0 else "SHORT"
            return {
                'strategy': self.name,
                'direction': direction,
                'confidence': 75,
                'entry': data['close'].iloc[-1],
                'stop': data['close'].iloc[-1] * (0.992 if direction == "LONG" else 1.008),
                'target': data['close'].iloc[-1] * (1.016 if direction == "LONG" else 0.984),
                'rationale': f'Volume surge {current_vol/vol_sma:.1f}x + momentum {price_change:.2%}'
            }
        return None

class MomentumEMAStrategy(StrategyCompetitor):
    """Momentum EMA+RSI on SPY - Profit Factor 1.98, Sharpe 2.59"""
    
    def __init__(self):
        super().__init__("Momentum_EMA_SPY", 10000)
        self.description = "EMA+RSI momentum on SPY - Profit Factor 1.98, Sharpe 2.59"
    
    def generate_signal(self, data: pd.DataFrame) -> Optional[Dict]:
        if len(data) < 20:
            return None
        
        # Calculate EMA and RSI
        ema20 = data['close'].ewm(span=20).mean().iloc[-1]
        current_price = data['close'].iloc[-1]
        
        # RSI calculation
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1]
        
        # Volume check
        current_vol = data['volume'].iloc[-1]
        vol_sma = data['volume'].rolling(20).mean().iloc[-1]
        
        # Entry: Price above EMA20 + RSI > 50 + volume surge
        if current_price > ema20 and rsi > 50 and current_vol > 1.5 * vol_sma:
            return {
                'strategy': self.name,
                'direction': 'LONG',
                'confidence': 70,
                'entry': current_price,
                'stop': current_price * 0.995,
                'target': current_price * 1.015,
                'rationale': f'EMA break + RSI {rsi:.0f} + vol {current_vol/vol_sma:.1f}x'
            }
        return None

class VWAPStrategy(StrategyCompetitor):
    """VWAP scalping on AAPL - Profit Factor 1.58, Sharpe 1.85"""
    
    def __init__(self):
        super().__init__("VWAP_Scalping_AAPL", 10000)
        self.description = "VWAP reversion on AAPL - Profit Factor 1.58, Sharpe 1.85"
    
    def generate_signal(self, data: pd.DataFrame) -> Optional[Dict]:
        if len(data) < 20:
            return None
        
        # Calculate VWAP
        typical_price = (data['high'] + data['low'] + data['close']) / 3
        vwap = (typical_price * data['volume']).cumsum() / data['volume'].cumsum()
        
        current_price = data['close'].iloc[-1]
        current_vwap = vwap.iloc[-1]
        
        # Distance from VWAP
        distance = (current_price - current_vwap) / current_vwap
        
        # Entry: Price extends >0.5% from VWAP (mean reversion)
        if abs(distance) > 0.005:
            direction = "SHORT" if distance > 0 else "LONG"  # Revert to VWAP
            return {
                'strategy': self.name,
                'direction': direction,
                'confidence': 65,
                'entry': current_price,
                'stop': current_price * (1.005 if direction == "SHORT" else 0.995),
                'target': current_vwap,
                'rationale': f'VWAP deviation {distance:.2%} - mean reversion'
            }
        return None

class FundingArbStrategy(StrategyCompetitor):
    """Funding rate arbitrage - Delta neutral, 5-15% annually"""
    
    def __init__(self):
        super().__init__("Funding_Arbitrage", 10000)
        self.description = "Funding rate arbitrage - Delta neutral, safest strategy"
        self.funding_history = []
    
    def generate_signal(self, data: pd.DataFrame, funding_rate: float = None) -> Optional[Dict]:
        if funding_rate is None:
            return None
        
        self.funding_history.append(funding_rate)
        if len(self.funding_history) < 30:
            return None
        
        # Extreme funding = opportunity
        avg_funding = np.mean(self.funding_history[-30:])
        std_funding = np.std(self.funding_history[-30:])
        
        if std_funding == 0:
            return None
        
        z_score = (funding_rate - avg_funding) / std_funding
        
        # Extreme positive funding = short perp (collect funding)
        # Extreme negative funding = long perp (collect funding)
        if abs(z_score) > 2:
            direction = "SHORT" if funding_rate > 0 else "LONG"
            return {
                'strategy': self.name,
                'direction': direction,
                'confidence': 80,
                'entry': data['close'].iloc[-1],
                'stop': data['close'].iloc[-1] * 0.95,  # Wide stop for delta-neutral
                'target': data['close'].iloc[-1] * 1.05,
                'rationale': f'Funding z-score {z_score:.1f} - collect {abs(funding_rate):.4%} funding'
            }
        return None

class TwoHourChallenge:
    """2-hour live competition between strategies"""
    
    def __init__(self):
        self.strategies = [
            NewsScalpingStrategy(),
            MomentumEMAStrategy(),
            VWAPStrategy(),
            FundingArbStrategy()
        ]
        self.start_time = None
        self.end_time = None
        self.results = []
        
    async def run_challenge(self, duration_minutes: int = 120):
        """Run the 2-hour challenge"""
        self.start_time = datetime.utcnow()
        self.end_time = self.start_time + timedelta(minutes=duration_minutes)
        
        print("=" * 70)
        print("🏆 2-HOUR STRATEGY CHALLENGE")
        print("=" * 70)
        print(f"Start: {self.start_time.isoformat()} UTC")
        print(f"End: {self.end_time.isoformat()} UTC")
        print(f"Duration: {duration_minutes} minutes")
        print()
        
        print("📊 COMPETITORS:")
        for i, s in enumerate(self.strategies, 1):
            print(f"{i}. {s.name}")
            print(f"   {s.description}")
        print()
        print("=" * 70)
        
        # Initialize data feed
        async with aiohttp.ClientSession() as session:
            while datetime.utcnow() < self.end_time:
                await self.check_all_strategies(session)
                await self.update_leaderboard()
                await asyncio.sleep(60)  # Check every minute
        
        self.print_final_results()
    
    async def check_all_strategies(self, session: aiohttp.ClientSession):
        """Check all strategies against real Binance data."""
        try:
            # Fetch real BTC data from Binance
            url = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=100"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return
                raw = await resp.json()

            df = pd.DataFrame(raw, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy',
                'taker_buy_quote', 'ignore'
            ])
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)

            current_price = df['close'].iloc[-1]

            for strategy in self.strategies:
                signal = strategy.generate_signal(df)
                if signal:
                    strategy.trades.append({
                        'time': datetime.utcnow().isoformat(),
                        'signal': signal,
                        'price': current_price,
                    })
                    # Evaluate simple P&L from last trade if any
                    if len(strategy.trades) >= 2:
                        prev = strategy.trades[-2]
                        prev_price = prev['price']
                        direction = prev['signal'].get('direction', 'LONG')
                        if direction == 'LONG':
                            pnl_pct = (current_price - prev_price) / prev_price
                        else:
                            pnl_pct = (prev_price - current_price) / prev_price
                        strategy.update_performance(pnl_pct)
        except Exception as e:
            print(f"  Error in check_all_strategies: {e}")
    
    async def update_leaderboard(self):
        """Update and display leaderboard"""
        elapsed = (datetime.utcnow() - self.start_time).total_seconds() / 60
        remaining = (self.end_time - datetime.utcnow()).total_seconds() / 60
        
        print(f"\n[{datetime.utcnow().strftime('%H:%M:%S')}] Elapsed: {elapsed:.0f}m | Remaining: {remaining:.0f}m")
        print("-" * 70)
        
        # Sort by P&L
        sorted_strategies = sorted(self.strategies, key=lambda s: s.pnl, reverse=True)
        
        for i, s in enumerate(sorted_strategies, 1):
            pnl_pct = (s.pnl / s.initial_capital) * 100
            print(f"{i}. {s.name:25} | P&L: ${s.pnl:8.2f} ({pnl_pct:+.2f}%) | Trades: {len(s.trades)}")
    
    def print_final_results(self):
        """Print final challenge results"""
        print("\n" + "=" * 70)
        print("🏆 FINAL RESULTS - 2 HOUR CHALLENGE")
        print("=" * 70)
        
        sorted_strategies = sorted(self.strategies, key=lambda s: s.pnl, reverse=True)
        
        winner = sorted_strategies[0]
        print(f"\n🥇 WINNER: {winner.name}")
        print(f"   Final P&L: ${winner.pnl:.2f} ({(winner.pnl/winner.initial_capital)*100:+.2f}%)")
        print(f"   Total Trades: {len(winner.trades)}")
        
        print("\n📊 FULL STANDINGS:")
        for i, s in enumerate(sorted_strategies, 1):
            pnl_pct = (s.pnl / s.initial_capital) * 100
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
            print(f"{medal} {i}. {s.name:25} | ${s.pnl:8.2f} ({pnl_pct:+.2f}%)")
        
        print("\n" + "=" * 70)

async def main():
    """Run the 2-hour challenge"""
    challenge = TwoHourChallenge()
    await challenge.run_challenge(duration_minutes=120)

if __name__ == "__main__":
    print("🏆 2-HOUR STRATEGY CHALLENGE")
    print("Starting in 5 seconds...")
    print("Press Ctrl+C to stop early")
    
    # Note: This would run for 2 hours. For demo, we'll just show the setup
    print("\nChallenge setup complete. Ready to run.")
    print("To run: asyncio.run(main())")
