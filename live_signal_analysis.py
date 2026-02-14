#!/usr/bin/env python3
"""
================================================================================
LIVE SIGNAL ANALYSIS - With Real-Time API Data
================================================================================

Uses live CoinGecko API to generate fresh signals with real prices.

Usage:
    python live_signal_analysis.py
================================================================================
"""

import json
import numpy as np
from datetime import datetime
from pathlib import Path

from live_data_connector import LiveDataConnector
from high_conviction_signals import HighConvictionSystem, ConvictionLevel


def analyze_with_live_data():
    """Run complete signal analysis with live data"""
    print("=" * 80)
    print("🚀 LIVE SIGNAL ANALYSIS - REAL-TIME DATA")
    print("=" * 80)
    print(f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("✅ Using LIVE CoinGecko API data")
    print("=" * 80)
    
    # Initialize connector
    connector = LiveDataConnector()
    
    # Fetch live prices
    print("\n📡 Fetching live market data...")
    live_prices = connector.get_live_prices()
    
    if not live_prices:
        print("❌ Failed to fetch live data")
        return
    
    print("✅ Live data received!")
    
    # Display current prices
    print("\n💹 CURRENT MARKET SNAPSHOT:")
    print("-" * 80)
    for asset, data in live_prices.items():
        emoji = "🟢" if data['change_24h'] > 0 else "🔴"
        print(f"{emoji} {asset:5}: ${data['price']:>12,.2f} "
              f"({data['change_24h']:>+6.2f}%) "
              f"| Vol: ${data['volume_24h']/1e9:>5.1f}B")
    print()
    
    # Fetch OHLC data for technical analysis
    print("📊 Fetching OHLC data for technical analysis...")
    
    signal_system = HighConvictionSystem()
    assets = ['BTC', 'ETH', 'BNB', 'AVAX']
    
    analysis_results = {}
    
    for asset in assets:
        print(f"\n🔍 Analyzing {asset}...")
        
        # Get OHLC data
        ohlc = connector.get_ohlc_data(asset, days=60)
        
        if ohlc.empty:
            print(f"   ⚠️  No OHLC data available")
            continue
        
        # Prepare data for signal system
        data = ohlc.copy()
        data['price'] = data['close']
        data['volume'] = data.get('volume', 1000000)
        
        # Generate signal
        signal = signal_system.analyze(asset, data)
        
        # Get live price for comparison
        live_price = live_prices.get(asset, {}).get('price', 0)
        live_change = live_prices.get(asset, {}).get('change_24h', 0)
        
        if signal:
            # Compare signal price to live price
            price_diff = abs(live_price - signal.entry_price) / signal.entry_price * 100
            
            analysis_results[asset] = {
                'signal_generated': True,
                'conviction': signal.conviction.name,
                'score': signal.composite_score,
                'entry_price': signal.entry_price,
                'live_price': live_price,
                'price_diff_pct': price_diff,
                'stop_loss': signal.stop_loss,
                'tp1': signal.take_profit_1,
                'tp2': signal.take_profit_2,
                'tp3': signal.take_profit_3,
                'position_size': signal.position_size,
                '24h_change': live_change,
                'model_agreement': signal.model_agreement_score
            }
            
            print(f"   Conviction: {signal.conviction.name}")
            print(f"   Score: {signal.composite_score:.1f}/100")
            print(f"   Signal Entry: ${signal.entry_price:,.2f}")
            print(f"   Live Price:   ${live_price:,.2f}")
            print(f"   Price Drift:  {price_diff:.2f}%")
            
            if signal.conviction == ConvictionLevel.EXTREME:
                print(f"   🚨 EXTREME SIGNAL!")
        else:
            analysis_results[asset] = {
                'signal_generated': False,
                'live_price': live_price,
                '24h_change': live_change
            }
            print(f"   No signal generated (criteria not met)")
    
    # Generate recommendations
    print("\n" + "=" * 80)
    print("🎯 SIGNAL RECOMMENDATIONS")
    print("=" * 80)
    
    # Filter for actionable signals
    actionable = []
    for asset, data in analysis_results.items():
        if data.get('signal_generated') and data.get('conviction') in ['EXTREME', 'HIGH']:
            actionable.append((asset, data))
    
    # Sort by score
    actionable.sort(key=lambda x: x[1]['score'], reverse=True)
    
    if not actionable:
        print("\n⚠️  NO EXTREME SIGNALS GENERATED")
        print("\nPossible reasons:")
        print("   • Market conditions don't meet 6-model consensus")
        print("   • Risk/reward ratio below 3:1 threshold")
        print("   • Technical indicators not aligned")
        print("\nRecommendation: WAIT for better setup")
        
        # Show what we have
        print("\n📊 Current Status by Asset:")
        for asset, data in analysis_results.items():
            if data.get('signal_generated'):
                print(f"   {asset}: {data['conviction']} ({data['score']:.1f}/100)")
            else:
                print(f"   {asset}: No signal")
    
    else:
        # Display top signals
        for rank, (asset, data) in enumerate(actionable[:3], 1):
            print(f"\n{'='*60}")
            print(f"🎯 RANK #{rank}: {asset} {data['conviction']}")
            print(f"{'='*60}")
            
            # Check if price has drifted significantly
            price_drift = data.get('price_diff_pct', 0)
            if price_drift > 2:
                print(f"⚠️  WARNING: Price drifted {price_drift:.1f}% from signal")
                print(f"   Consider waiting for pullback or adjusting entry")
            
            print(f"\n📊 TRADE SETUP:")
            print(f"   Live Price:    ${data['live_price']:,.2f}")
            print(f"   Signal Entry:  ${data['entry_price']:,.2f}")
            print(f"   Stop Loss:     ${data['stop_loss']:,.2f} ({(data['stop_loss']/data['entry_price']-1)*100:.2f}%)")
            print(f"   TP1 (3:1):     ${data['tp1']:,.2f} ({(data['tp1']/data['entry_price']-1)*100:.1f}%)")
            print(f"   TP2 (5:1):     ${data['tp2']:,.2f} ({(data['tp2']/data['entry_price']-1)*100:.1f}%)")
            print(f"   TP3 (8:1):     ${data['tp3']:,.2f} ({(data['tp3']/data['entry_price']-1)*100:.1f}%)")
            print(f"   Position:      {data['position_size']*100:.1f}% of portfolio")
            print(f"   Score:         {data['score']:.1f}/100")
            print(f"   Model Agree:   {data['model_agreement']*100:.0f}%")
            
            print(f"\n📈 MARKET CONTEXT:")
            print(f"   24h Change:    {data['24h_change']:+.2f}%")
            print(f"   Price Drift:   {price_drift:.2f}%")
    
    # Save report
    report = {
        'timestamp': datetime.now().isoformat(),
        'data_source': 'CoinGecko Live API',
        'prices': {k: v for k, v in live_prices.items()},
        'analysis': analysis_results,
        'actionable_signals': [{'asset': a, **d} for a, d in actionable[:3]]
    }
    
    filename = f"live_signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n📄 Full report saved: {filename}")
    
    # Final summary
    print("\n" + "=" * 80)
    print("📋 SUMMARY")
    print("=" * 80)
    print(f"Assets Analyzed: {len(assets)}")
    print(f"Signals Generated: {sum(1 for d in analysis_results.values() if d.get('signal_generated'))}")
    print(f"Actionable Signals: {len(actionable)}")
    print(f"Data Freshness: LIVE (CoinGecko API)")
    print(f"Last Update: {datetime.now().strftime('%H:%M:%S')} UTC")
    
    if actionable:
        print(f"\n✅ Top Signal: {actionable[0][0]} ({actionable[0][1]['conviction']})")
    else:
        print("\n⏸️  No actionable signals - waiting for better setup")
    
    print("=" * 80)


if __name__ == '__main__':
    analyze_with_live_data()
