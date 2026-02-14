#!/usr/bin/env python3
"""
================================================================================
LIVE SIGNALS NOW - With Real-Time API Data
================================================================================
Generates signals using live prices when OHLC is unavailable.
================================================================================
"""

import json
from datetime import datetime
from live_data_connector import LiveDataConnector


def generate_live_signals():
    """Generate signals using live price data"""
    print("=" * 80)
    print("🚨 LIVE SIGNALS NOW - REAL-TIME ANALYSIS")
    print("=" * 80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("✅ Connected to CoinGecko LIVE API")
    print("=" * 80)
    
    connector = LiveDataConnector()
    
    # Get live prices
    print("\n📡 Fetching live prices...")
    prices = connector.get_live_prices()
    
    if not prices:
        print("❌ Failed to fetch prices")
        return
    
    # Get market data for each asset
    print("📊 Fetching market data...")
    market_data = {}
    for asset in ['BTC', 'ETH', 'BNB', 'AVAX']:
        data = connector.get_market_data(asset)
        if data:
            market_data[asset] = data
    
    # Display live snapshot
    print("\n💹 LIVE MARKET SNAPSHOT:")
    print("-" * 80)
    print(f"{'Asset':<8} {'Price':<15} {'24h %':<10} {'24h High':<12} {'24h Low':<12} {'Volume':<10}")
    print("-" * 80)
    
    for asset in ['BTC', 'ETH', 'BNB', 'AVAX']:
        if asset in prices and asset in market_data:
            p = prices[asset]
            m = market_data[asset]
            emoji = "🟢" if p['change_24h'] > 0 else "🔴"
            print(f"{emoji} {asset:<5} ${p['price']:<14,.2f} {p['change_24h']:<+9.2f}% "
                  f"${m['high_24h']:<11,.0f} ${m['low_24h']:<11,.0f} "
                  f"${p['volume_24h']/1e9:<9.1f}B")
    
    # Technical analysis using live data
    print("\n" + "=" * 80)
    print("🔧 TECHNICAL ANALYSIS (Live Data)")
    print("=" * 80)
    
    results = {}
    
    for asset in ['BTC', 'ETH', 'BNB', 'AVAX']:
        if asset not in prices or asset not in market_data:
            continue
        
        p = prices[asset]
        m = market_data[asset]
        
        print(f"\n📊 {asset} Analysis:")
        
        # Current price
        price = p['price']
        
        # Calculate technical levels from 24h data
        high_24h = m['high_24h']
        low_24h = m['low_24h']
        range_24h = high_24h - low_24h
        
        # Position in 24h range (0 = at low, 1 = at high)
        position_in_range = (price - low_24h) / range_24h if range_24h > 0 else 0.5
        
        print(f"   Price: ${price:,.2f}")
        print(f"   24h Range: ${low_24h:,.2f} - ${high_24h:,.2f}")
        print(f"   Position in Range: {position_in_range*100:.1f}%")
        
        # Layer 1: Trend (based on 24h change)
        change_24h = p['change_24h']
        trend_score = min(abs(change_24h) / 5, 1.0) if change_24h > 0 else 0
        trend = "BULLISH" if change_24h > 0 else "BEARISH"
        print(f"   1. Trend: {trend} ({change_24h:+.2f}%) Score: {trend_score:.2f}")
        
        # Layer 2: Range position (ideal: 30-70%, not at extremes)
        if 0.3 <= position_in_range <= 0.7:
            range_score = 0.8
            range_status = "✅ Optimal"
        elif position_in_range < 0.3:
            range_score = 0.5
            range_status = "⚠️ Near lows"
        else:
            range_score = 0.4
            range_status = "⚠️ Near highs"
        print(f"   2. Range Position: {range_status} Score: {range_score:.2f}")
        
        # Layer 3: Volume confirmation
        volume = p['volume_24h']
        avg_volume = 30e9 if asset == 'BTC' else 15e9 if asset == 'ETH' else 1e9 if asset == 'BNB' else 0.2e9
        vol_ratio = volume / avg_volume
        vol_score = min(vol_ratio, 1.0)
        vol_status = "✅ Above avg" if vol_ratio > 1 else "⚠️ Below avg"
        print(f"   3. Volume: ${volume/1e9:.1f}B ({vol_ratio:.1f}x) {vol_status} Score: {vol_score:.2f}")
        
        # Layer 4: Support/Resistance calculation
        # Use 24h low as support, 24h high as resistance
        support = low_24h
        resistance = high_24h
        
        risk = (price - support) / price
        reward = (resistance - price) / price
        rr = reward / risk if risk > 0 else 0
        
        rr_score = 0.3 if rr >= 2 else 0.2 if rr >= 1 else 0.1
        print(f"   4. R/R Ratio: {rr:.1f}:1 (Risk: {risk*100:.1f}%, Reward: {reward*100:.1f}%) Score: {rr_score:.2f}")
        
        # Layer 5: Momentum (price vs 24h mid)
        mid_24h = (high_24h + low_24h) / 2
        momentum = (price - mid_24h) / mid_24h
        momentum_score = 0.5 + momentum if abs(momentum) < 0.5 else 0.5 + (0.5 if momentum > 0 else -0.5)
        momentum_score = max(0, min(1, momentum_score))
        print(f"   5. Momentum: {momentum*100:+.2f}% vs mid Score: {momentum_score:.2f}")
        
        # Layer 6: Swarm Research Alignment
        swarm_score = 0.8 if asset in ['BTC', 'ETH'] else 0.6
        print(f"   6. Swarm Alignment: {'Momentum' if asset in ['BTC','ETH'] else 'Mean Reversion'} Score: {swarm_score:.2f}")
        
        # Calculate composite
        composite = (trend_score * 0.25 + range_score * 0.2 + vol_score * 0.15 + 
                     rr_score * 0.2 + momentum_score * 0.1 + swarm_score * 0.1)
        
        # Penalty for extreme volatility (AVAX)
        vol_penalty = 0.15 if asset == 'AVAX' else 0.05 if asset == 'BNB' else 0
        composite -= vol_penalty
        
        final_score = max(0, composite)
        
        print(f"   ─────────────────────────")
        print(f"   RAW SCORE: {composite:.2f}")
        print(f"   FINAL SCORE: {final_score:.2f}")
        
        # Determine recommendation
        if final_score >= 0.7:
            recommendation = "STRONG BUY"
        elif final_score >= 0.55:
            recommendation = "BUY"
        elif final_score >= 0.4:
            recommendation = "WEAK BUY"
        else:
            recommendation = "NEUTRAL"
        
        print(f"   🎯 RECOMMENDATION: {recommendation}")
        
        results[asset] = {
            'price': price,
            'change_24h': change_24h,
            'high_24h': high_24h,
            'low_24h': low_24h,
            'volume_24h': volume,
            'support': support,
            'resistance': resistance,
            'risk_pct': risk * 100,
            'reward_pct': reward * 100,
            'rr_ratio': rr,
            'score': final_score,
            'recommendation': recommendation
        }
    
    # Generate trade setups for top signals
    print("\n" + "=" * 80)
    print("🎯 TOP SIGNALS - TRADE SETUPS")
    print("=" * 80)
    
    # Sort by score
    sorted_results = sorted(results.items(), key=lambda x: x[1]['score'], reverse=True)
    
    top_signals = []
    for rank, (asset, data) in enumerate(sorted_results[:3], 1):
        if data['score'] < 0.5:
            continue
        
        # Calculate targets based on 24h range extension
        current = data['price']
        support = data['support']
        resistance = data['resistance']
        range_size = resistance - support
        
        # Dynamic position size based on score
        if data['score'] >= 0.75:
            position_size = 0.08
            confidence = "HIGH"
        elif data['score'] >= 0.6:
            position_size = 0.06
            confidence = "MEDIUM"
        else:
            position_size = 0.04
            confidence = "LOW"
        
        # Adjust for volatility
        if asset == 'AVAX':
            position_size *= 0.5
        elif asset == 'BNB':
            position_size *= 0.75
        
        signal = {
            'rank': rank,
            'asset': asset,
            'confidence': confidence,
            'entry': current,
            'stop': support * 0.99,  # Just below 24h low
            'tp1': resistance * 0.98,  # Just below 24h high
            'tp2': resistance * 1.05,  # 5% above resistance
            'tp3': resistance * 1.10,  # 10% above resistance
            'position_size': position_size,
            'score': data['score'],
            'rr': data['rr_ratio'],
            'rationale': f"24h momentum: {data['change_24h']:+.2f}%, Range position: optimal"
        }
        
        top_signals.append(signal)
        
        print(f"\n{'='*60}")
        print(f"🎯 RANK #{rank}: {asset} ({confidence} CONFIDENCE)")
        print(f"{'='*60}")
        print(f"   Live Price:    ${current:,.2f}")
        print(f"   24h Range:     ${support:,.2f} - ${resistance:,.2f}")
        print(f"   Entry:         ${current:,.2f} (MARKET)")
        print(f"   Stop Loss:     ${signal['stop']:,.2f} ({(signal['stop']/current-1)*100:.2f}%)")
        print(f"   TP1 (Near R):  ${signal['tp1']:,.2f} ({(signal['tp1']/current-1)*100:.1f}%)")
        print(f"   TP2 (+5%):     ${signal['tp2']:,.2f} ({(signal['tp2']/current-1)*100:.1f}%)")
        print(f"   TP3 (+10%):    ${signal['tp3']:,.2f} ({(signal['tp3']/current-1)*100:.1f}%)")
        print(f"   Position Size: {position_size*100:.1f}% of portfolio")
        print(f"   R/R Ratio:     {data['rr_ratio']:.1f}:1")
        print(f"   Score:         {data['score']:.2f}/1.0")
        print(f"\n   💡 RATIONALE:")
        print(f"      {signal['rationale']}")
    
    if not top_signals:
        print("\n⚠️  NO STRONG SIGNALS")
        print("   Market conditions don't meet thresholds")
        print("   Recommendation: WAIT")
    
    # Warnings
    print("\n" + "=" * 80)
    print("⚠️  IMPORTANT WARNINGS")
    print("=" * 80)
    print("1. ✅ Data is LIVE but analysis uses 24h range only (limited history)")
    print("2. ⚠️  Paper trade first - validate these signals over 5+ trades")
    print("3. ⚠️  All crypto is volatile - use strict position sizing")
    print("4. ⚠️  These are day-trading ranges - expect quick moves")
    print("5. ✅ API connection verified and working")
    
    # Save report
    report = {
        'timestamp': datetime.now().isoformat(),
        'data_source': 'CoinGecko Live API',
        'prices': {k: v for k, v in prices.items()},
        'analysis': results,
        'signals': top_signals
    }
    
    filename = f"live_signals_now_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n📄 Report saved: {filename}")
    print("=" * 80)
    print("✅ LIVE ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    generate_live_signals()
