#!/usr/bin/env python3
"""
LIVE SPIKE TRADER - Autonomous Crypto & Forex Trading
Fetches live data, predicts spikes, executes trades, monitors results
"""

import os
import json
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

# Import our spike predictor
from spike_predictor import SpikePredictor, SpikeSignal, LiveSpikeMonitor

# Failover helpers — tries all Binance mirrors + circuit breaker + Bybit fallback
from shared.binance_api import binance_get, binance_futures_get

class LiveDataFeed:
    """Fetches live market data from exchanges (with endpoint failover)."""
    
    def __init__(self):
        self.price_cache = {}
        self.last_update = {}
    
    async def get_binance_price(self, symbol: str) -> Optional[Dict]:
        """Get current price from Binance (with endpoint failover)"""
        try:
            data = await asyncio.to_thread(
                binance_get, "/api/v3/ticker/24hr", params={"symbol": symbol},
            )
            if data:
                return {
                    'price': float(data['lastPrice']),
                    'volume': float(data['volume']),
                    'price_change': float(data['priceChangePercent']),
                    'high': float(data['highPrice']),
                    'low': float(data['lowPrice']),
                    'timestamp': datetime.utcnow()
                }
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
        return None
    
    async def get_binance_klines(self, symbol: str, interval: str = "1m", limit: int = 100) -> Optional[pd.DataFrame]:
        """Get OHLCV data from Binance (with endpoint failover)"""
        try:
            data = await asyncio.to_thread(
                binance_get, "/api/v3/klines",
                params={"symbol": symbol, "interval": interval, "limit": str(limit)},
            )
            if data:
                df = pd.DataFrame(data, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'taker_buy',
                    'taker_buy_quote', 'ignore'
                ])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
                df.set_index('timestamp', inplace=True)
                return df
        except Exception as e:
            print(f"Error fetching klines for {symbol}: {e}")
        return None
    
    async def get_funding_rate(self, symbol: str) -> Optional[float]:
        """Get current funding rate for perpetual futures (with endpoint failover)"""
        try:
            data = await asyncio.to_thread(
                binance_futures_get, "/fapi/v1/fundingRate",
                params={"symbol": symbol, "limit": "1"},
            )
            if data and isinstance(data, list) and data:
                return float(data[0]['fundingRate'])
        except Exception as e:
            print(f"Error fetching funding rate: {e}")
        return None

class AutonomousSpikeTrader:
    """
    Autonomous trading system that:
    1. Fetches live data
    2. Predicts spikes
    3. Logs signals
    4. Tracks performance
    5. Adapts to market conditions
    """
    
    def __init__(self, capital: float = 10000.0):
        self.capital = capital
        self.predictor = SpikePredictor()
        self.data_feed = LiveDataFeed()
        self.active_signals: List[Dict] = []
        self.signal_history: List[Dict] = []
        self.running = False
        
        # Assets to monitor
        self.crypto_assets = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT']
        self.forex_pairs = []  # Would need forex data feed
        
        # Performance tracking
        self.daily_pnl = []
        self.total_trades = 0
        self.winning_trades = 0
    
    async def initialize(self):
        """Initialize the trader"""
        # LiveDataFeed now uses shared.binance_api (no session init needed)
        print("✅ Autonomous Spike Trader initialized")
        print(f"💰 Capital: ${self.capital:,.2f}")
        print(f"📊 Monitoring: {', '.join(self.crypto_assets)}")
    
    async def run(self, check_interval: int = 60):
        """Main trading loop"""
        self.running = True
        print("\n🔴 AUTONOMOUS TRADING STARTED")
        print("=" * 70)
        
        while self.running:
            try:
                await self.scan_all_assets()
                await self.check_signal_exits()
                self.print_status()
                
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                print(f"❌ Error in main loop: {e}")
                await asyncio.sleep(10)
    
    async def scan_all_assets(self):
        """Scan all assets for spike opportunities"""
        for asset in self.crypto_assets:
            await self.analyze_asset(asset)
    
    async def analyze_asset(self, symbol: str):
        """Analyze a single asset for spike prediction"""
        # Fetch data
        price_data = await self.data_feed.get_binance_klines(symbol, "1m", 100)
        current_price = await self.data_feed.get_binance_price(symbol)
        funding_rate = await self.data_feed.get_funding_rate(symbol)
        
        if price_data is None or current_price is None:
            return
        
        # Get funding history for anomaly detection
        funding_history = None
        if funding_rate is not None:
            try:
                data = await asyncio.to_thread(
                    binance_futures_get, "/fapi/v1/fundingRate",
                    params={"symbol": symbol, "limit": "30"},
                )
                if data and isinstance(data, list):
                    funding_history = pd.Series([float(d['fundingRate']) for d in data])
            except Exception:
                pass
        
        # Predict spike
        signal = self.predictor.predict_spike(
            asset=symbol,
            price_data=price_data,
            funding_rate=funding_rate,
            funding_history=funding_history
        )
        
        if signal:
            await self.process_signal(signal, current_price)
    
    async def process_signal(self, signal: SpikeSignal, current_price: Dict):
        """Process a new trading signal"""
        # Check if we already have a signal for this asset
        existing = [s for s in self.active_signals if s['asset'] == signal.asset]
        if existing:
            return
        
        # Calculate position size (2% risk per trade)
        risk_amount = self.capital * 0.02
        price_risk = abs(signal.entry_price - signal.stop_loss)
        position_size = risk_amount / price_risk if price_risk > 0 else 0
        
        trade = {
            'signal_id': len(self.signal_history),
            'asset': signal.asset,
            'direction': signal.direction,
            'entry_price': signal.entry_price,
            'current_price': current_price['price'],
            'stop_loss': signal.stop_loss,
            'take_profit': signal.take_profit,
            'confidence': signal.confidence,
            'rationale': signal.rationale,
            'entry_time': datetime.utcnow(),
            'position_size': position_size,
            'status': 'ACTIVE'
        }
        
        self.active_signals.append(trade)
        self.signal_history.append(trade)
        
        print(f"\n🎯 NEW SPIKE SIGNAL")
        print(f"Asset: {signal.asset}")
        print(f"Direction: {signal.direction}")
        print(f"Confidence: {signal.confidence:.1f}%")
        print(f"Entry: ${signal.entry_price:,.2f}")
        print(f"Stop: ${signal.stop_loss:,.2f}")
        print(f"Target: ${signal.take_profit:,.2f}")
        print(f"Rationale: {signal.rationale}")
        print("-" * 50)
    
    async def check_signal_exits(self):
        """Check if any active signals hit stop or target"""
        for signal in self.active_signals[:]:
            current = await self.data_feed.get_binance_price(signal['asset'])
            if not current:
                continue
            
            current_price = current['price']
            exit_triggered = False
            exit_price = current_price
            exit_reason = ""
            pnl = 0
            
            if signal['direction'] == 'LONG':
                if current_price <= signal['stop_loss']:
                    exit_triggered = True
                    exit_reason = "STOP_LOSS"
                    pnl = (signal['stop_loss'] - signal['entry_price']) / signal['entry_price']
                elif current_price >= signal['take_profit']:
                    exit_triggered = True
                    exit_reason = "TAKE_PROFIT"
                    pnl = (signal['take_profit'] - signal['entry_price']) / signal['entry_price']
            else:  # SHORT
                if current_price >= signal['stop_loss']:
                    exit_triggered = True
                    exit_reason = "STOP_LOSS"
                    pnl = (signal['entry_price'] - signal['stop_loss']) / signal['entry_price']
                elif current_price <= signal['take_profit']:
                    exit_triggered = True
                    exit_reason = "TAKE_PROFIT"
                    pnl = (signal['entry_price'] - signal['take_profit']) / signal['entry_price']
            
            # Time-based exit (30 minutes max)
            elapsed = (datetime.utcnow() - signal['entry_time']).total_seconds() / 60
            if elapsed > 30 and not exit_triggered:
                exit_triggered = True
                exit_reason = "TIME_EXIT"
                if signal['direction'] == 'LONG':
                    pnl = (current_price - signal['entry_price']) / signal['entry_price']
                else:
                    pnl = (signal['entry_price'] - current_price) / signal['entry_price']
            
            if exit_triggered:
                self.close_signal(signal, exit_price, exit_reason, pnl)
    
    def close_signal(self, signal: Dict, exit_price: float, reason: str, pnl: float):
        """Close a signal and update performance"""
        signal['status'] = 'CLOSED'
        signal['exit_price'] = exit_price
        signal['exit_time'] = datetime.utcnow()
        signal['exit_reason'] = reason
        signal['pnl'] = pnl
        
        self.active_signals.remove(signal)
        self.total_trades += 1
        if pnl > 0:
            self.winning_trades += 1
        
        emoji = "✅" if pnl > 0 else "❌"
        print(f"\n{emoji} SIGNAL CLOSED")
        print(f"Asset: {signal['asset']}")
        print(f"Reason: {reason}")
        print(f"P&L: {pnl:.2%}")
        print(f"Win Rate: {self.winning_trades}/{self.total_trades} ({self.winning_trades/self.total_trades:.1%})")
    
    def print_status(self):
        """Print current status"""
        print(f"\n[{datetime.utcnow().strftime('%H:%M:%S')} UTC]")
        print(f"Active Signals: {len(self.active_signals)}")
        print(f"Total Trades: {self.total_trades}")
        if self.total_trades > 0:
            print(f"Win Rate: {self.winning_trades/self.total_trades:.1%}")
        
        if self.active_signals:
            print("\nActive Signals:")
            for s in self.active_signals:
                elapsed = (datetime.utcnow() - s['entry_time']).total_seconds() / 60
                print(f"  {s['asset']} {s['direction']} | Conf: {s['confidence']:.0f}% | Age: {elapsed:.0f}m")
    
    def save_results(self, filename: str = "spike_trading_results.json"):
        """Save trading results to file"""
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'capital': self.capital,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'win_rate': self.winning_trades / self.total_trades if self.total_trades > 0 else 0,
            'signal_history': self.signal_history,
            'active_signals': self.active_signals
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to {filename}")
    
    async def shutdown(self):
        """Shutdown the trader"""
        self.running = False
        self.save_results()
        # LiveDataFeed no longer uses aiohttp session (no close needed)
        print("\n🛑 Autonomous trader shutdown complete")

# Main execution
async def main():
    """Main entry point"""
    trader = AutonomousSpikeTrader(capital=10000.0)
    
    try:
        await trader.initialize()
        await trader.run(check_interval=60)  # Check every minute
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    finally:
        await trader.shutdown()

if __name__ == "__main__":
    print("🚀 LIVE SPIKE TRADER")
    print("=" * 70)
    print("This will start live monitoring of crypto markets")
    print("Press Ctrl+C to stop")
    print("=" * 70)
    
    # Run the async main
    asyncio.run(main())
