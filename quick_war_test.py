#!/usr/bin/env python3
"""
================================================================================
QUICK WAR TEST - Immediate Real-Time Validation
================================================================================

Quick test of the system with live market data. No positions, just signals.

Usage:
    python quick_war_test.py
================================================================================
"""

import json
import time
import numpy as np
import pandas as pd
from datetime import datetime
import requests

from high_conviction_signals import HighConvictionSystem, ConvictionLevel


class QuickDataFeed:
    """Quick data fetcher from CoinGecko"""
    
    def __init__(self):
        self.coins = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'BNB': 'binancecoin',
            'AVAX': 'avalanche-2'
        }
    
    def get_prices(self):
        """Get current prices"""
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': ','.join(self.coins.values()),
            'vs_currencies': 'usd',
            'include_24hr_change': 'true',
            'include_market_cap': 'true'
        }
        
        try:
            r = requests.get(url, params=params, timeout=10)
            data = r.json()
            
            result = {}
            for asset, coin_id in self.coins.items():
                if coin_id in data:
                    result[asset] = {
                        'price': data[coin_id]['usd'],
                        'change_24h': data[coin_id].get('usd_24h_change', 0),
                        'mkt_cap': data[coin_id].get('usd_market_cap', 0)
                    }
            return result
        except Exception as e:
            print(f"Error: {e}")
            return {}
    
    def get_ohlc(self, asset, days=30):
        """Get OHLC data"""
        coin_id = self.coins.get(asset)
        if not coin_id:
            return None
        
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
        params = {'vs_currency': 'usd', 'days': days}
        
        try:
            r = requests.get(url, params=params, timeout=10)
            data = r.json()
            
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df['price'] = df['close']
            df['volume'] = 1000000  # Placeholder
            return df
        except:
            return None


def main():
    print("=" * 80)
    print("🚨 QUICK WAR TEST - REAL-TIME SIGNAL VALIDATION 🚨")
    print("=" * 80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Initialize
    feed = QuickDataFeed()
    system = HighConvictionSystem()
    
    # Get current market snapshot
    print("📊 FETCHING MARKET DATA...")
    prices = feed.get_prices()
    
    if not prices:
        print("❌ Failed to fetch prices. Check internet connection.")
        return
    
    print("\n💹 CURRENT MARKET SNAPSHOT:")
    print("-" * 80)
    for asset, data in prices.items():
        emoji = "🟢" if data['change_24h'] > 0 else "🔴"
        print(f"{emoji} {asset:5}: ${data['price']:>12,.2f} ({data['change_24h']:>+6.2f}%) | MCap: ${data['mkt_cap']/1e9:.1f}B")
    print()
    
    # Analyze each asset
    print("🔍 ANALYZING FOR EXTREME SIGNALS...")
    print("=" * 80)
    
    signals_found = []
    
    for asset in ['BTC', 'ETH', 'BNB', 'AVAX']:
        print(f"\n⚔️  Scanning {asset}...")
        
        # Get historical data
        ohlc = feed.get_ohlc(asset, days=60)
        if ohlc is None or len(ohlc) < 30:
            print(f"   ⚠️  Insufficient data")
            continue
        
        # Generate signal
        signal = system.analyze(asset, ohlc)
        
        if signal is None:
            print(f"   ❌ No signal generated (insufficient criteria)")
            continue
        
        # Display results
        print(f"   Conviction: {signal.conviction.name} (Score: {signal.composite_score:.1f}/100)")
        print(f"   Model Agreement: {signal.model_agreement_score*100:.0f}%")
        print(f"   Regime: {signal.detected_regime}")
        print(f"   On-Chain Score: {signal.on_chain_score*100:.0f}%")
        print(f"   Technical Score: {signal.technical_score*100:.0f}%")
        
        if signal.conviction == ConvictionLevel.EXTREME:
            signals_found.append(signal)
            print(f"   🚨 EXTREME SIGNAL DETECTED!")
            print(f"   Entry: ${signal.entry_price:,.2f}")
            print(f"   Stop:  ${signal.stop_loss:,.2f} ({(signal.stop_loss/signal.entry_price-1)*100:.2f}%)")
            print(f"   TP1:   ${signal.take_profit_1:,.2f} ({(signal.take_profit_1/signal.entry_price-1)*100:.1f}%)")
            print(f"   TP2:   ${signal.take_profit_2:,.2f} ({(signal.take_profit_2/signal.entry_price-1)*100:.1f}%)")
            print(f"   TP3:   ${signal.take_profit_3:,.2f} ({(signal.take_profit_3/signal.entry_price-1)*100:.1f}%) 🌙")
            print(f"   Position Size: {signal.position_size*100:.1f}%")
        else:
            print(f"   ⏸️  Signal below EXTREME threshold - No trade")
    
    # Summary
    print("\n" + "=" * 80)
    print("📋 BATTLE SUMMARY")
    print("=" * 80)
    print(f"Assets Scanned: 4")
    print(f"EXTREME Signals: {len(signals_found)}")
    
    if signals_found:
        print(f"\n🚨 READY TO DEPLOY:")
        for sig in signals_found:
            print(f"   • {sig.asset}: ${sig.entry_price:,.2f} → ${sig.take_profit_3:,.2f} ({(sig.take_profit_3/sig.entry_price-1)*100:.1f}%)")
    else:
        print(f"\n⏸️  NO EXTREME SIGNALS")
        print("   The market doesn't meet our criteria right now.")
        print("   Waiting for the stars to align...")
    
    # Comparison to swarm expectations
    print("\n📊 COMPARISON TO SWARM RESEARCH:")
    print("-" * 80)
    print("Our system requires:")
    print("  • 6/6 models agree (100% consensus)")
    print("  • Composite score ≥ 85/100")
    print("  • Risk/Reward ≥ 3:1")
    print("  • On-chain score ≥ 90%")
    print("  • 6/6 technical checks pass")
    print()
    print("Swarm research expected: 5-10 signals/month")
    print("Our system: 1-3 EXTREME signals/month (higher quality)")
    print()
    print("Swarm expected Sharpe: 1.0-1.5")
    print("Our target Sharpe: 3.24 (82.9% win rate)")
    
    print("\n" + "=" * 80)
    print("✅ QUICK WAR TEST COMPLETE")
    print("=" * 80)
    print()
    print("Next steps:")
    print("  1. Run full war room: python war_room.py")
    print("  2. Open dashboard: python live_dashboard.py")
    print("  3. Check GitHub Actions for backtest validation")
    print()
    
    # Save report
    report = {
        'timestamp': datetime.now().isoformat(),
        'market_snapshot': prices,
        'signals_found': [
            {
                'asset': s.asset,
                'conviction': s.conviction.name,
                'score': s.composite_score,
                'entry': s.entry_price,
                'tp3': s.take_profit_3,
                'rr': s.risk_reward
            } for s in signals_found
        ],
        'total_signals': len(signals_found)
    }
    
    filename = f"quick_war_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"📝 Report saved: {filename}")


if __name__ == '__main__':
    main()
