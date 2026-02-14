#!/usr/bin/env python3
"""
================================================================================
WAR ROOM DEMO - Simulated Real-Time Combat
================================================================================

Shows what the war room looks like with active positions and signals.
This is a simulation for demonstration purposes.

Usage:
    python war_room_demo.py
================================================================================
"""

import time
import random
from datetime import datetime, timedelta
import sys


def clear():
    """Clear screen"""
    print("\033[2J\033[H")


def color(text, color_code):
    """Add ANSI color"""
    colors = {
        'green': '\033[92m',
        'red': '\033[91m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'cyan': '\033[96m',
        'reset': '\033[0m'
    }
    return f"{colors.get(color_code, '')}{text}{colors['reset']}"


def generate_mock_data():
    """Generate realistic mock market data"""
    return {
        'BTC': {'price': 69852 + random.uniform(-500, 500), 'change': 1.27 + random.uniform(-0.1, 0.1)},
        'ETH': {'price': 2085 + random.uniform(-20, 20), 'change': 1.34 + random.uniform(-0.1, 0.1)},
        'BNB': {'price': 634 + random.uniform(-5, 5), 'change': 2.89 + random.uniform(-0.2, 0.2)},
        'AVAX': {'price': 9.46 + random.uniform(-0.1, 0.1), 'change': 3.06 + random.uniform(-0.3, 0.3)}
    }


def render_war_room(frame, positions, history, capital, start_capital):
    """Render the war room display"""
    clear()
    
    # Header
    print("=" * 80)
    title = "🚨 CRYPTOALPHA PRO - WAR ROOM 🚨"
    print(color(title.center(80), 'cyan'))
    print("=" * 80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Frame: {frame}")
    print()
    
    # Portfolio Status
    pnl = capital - start_capital
    pnl_pct = (capital / start_capital - 1) * 100
    pnl_color = 'green' if pnl >= 0 else 'red'
    
    print(color("📊 PORTFOLIO STATUS", 'yellow'))
    print("-" * 80)
    print(f"  Starting Capital: ${start_capital:,.2f}")
    print(f"  Current Equity:   ${capital:,.2f}")
    print(f"  Total P&L:        {color(f'${pnl:+,.2f}', pnl_color)} ({color(f'{pnl_pct:+.2f}%', pnl_color)})")
    print(f"  Open Positions:   {len(positions)}")
    print(f"  Closed Trades:    {len(history)}")
    print()
    
    # Market Data
    data = generate_mock_data()
    print(color("💹 LIVE MARKET DATA", 'yellow'))
    print("-" * 80)
    for asset, d in data.items():
        emoji = "🟢" if d['change'] > 0 else "🔴"
        change_color = 'green' if d['change'] > 0 else 'red'
        print(f"  {emoji} {asset:5}: ${d['price']:>10,.2f} ({color(f'{d['change']:+.2f}%', change_color)})")
    print()
    
    # Open Positions
    if positions:
        print(color("🎯 ACTIVE COMBAT - OPEN POSITIONS", 'yellow'))
        print("-" * 80)
        print(f"  {'Asset':<8} {'Entry':<12} {'Current':<12} {'P&L':<12} {'Status':<20}")
        print(f"  {'-'*7:<8} {'-'*11:<12} {'-'*11:<12} {'-'*11:<12} {'-'*19:<20}")
        
        for pos in positions:
            asset = pos['asset']
            current_price = data[asset]['price']
            entry = pos['entry']
            pnl_pct = (current_price - entry) / entry * 100
            
            # Update position
            pos['current'] = current_price
            pos['pnl_pct'] = pnl_pct
            
            pnl_color = 'green' if pnl_pct > 0 else 'red'
            print(f"  {asset:<8} ${entry:<11,.2f} ${current_price:<11,.2f} {color(f'{pnl_pct:+.2f}%', pnl_color):<12} {pos['status']:<20}")
        
        # Show targets
        print()
        print("  TARGETS:")
        for pos in positions:
            print(f"    {pos['asset']}: Stop ${pos['stop']:,.0f} | TP1 ${pos['tp1']:,.0f} | TP2 ${pos['tp2']:,.0f} | TP3 🌙 ${pos['tp3']:,.0f}")
        print()
    
    # Trade History
    if history:
        print(color("⚔️  BATTLE HISTORY (Last 5)", 'yellow'))
        print("-" * 80)
        print(f"  {'Time':<10} {'Asset':<8} {'Result':<10} {'P&L':<15}")
        print(f"  {'-'*9:<10} {'-'*7:<8} {'-'*9:<10} {'-'*14:<15}")
        
        for trade in history[-5:]:
            result_color = 'green' if trade['pnl'] > 0 else 'red'
            emoji = "✅" if trade['pnl'] > 0 else "❌"
            print(f"  {trade['time']:<10} {trade['asset']:<8} {emoji:<10} {color(f'{trade['pnl']:+.2f}%', result_color):<15}")
        print()
    
    # Recent Activity
    if frame % 3 == 0:
        print(color("📢 RECENT ACTIVITY", 'cyan'))
        print("-" * 80)
        activities = [
            "Scanning BTC... Model agreement: 4/6",
            "Scanning ETH... On-chain score: 75%",
            "Checking AVAX... Volatility: 89th percentile",
            "BNB analysis... Regime: SIDEWAYS",
            "Waiting for EXTREME criteria..."
        ]
        print(f"  {random.choice(activities)}")
        print()
    
    # Footer
    print("=" * 80)
    print(color("Press Ctrl+C to exit War Room".center(80), 'cyan'))
    print("=" * 80)


def simulate_war_room():
    """Simulate the war room experience"""
    clear()
    
    print("=" * 80)
    print("🚨 CRYPTOALPHA PRO - WAR ROOM 🚨".center(80))
    print("=" * 80)
    print()
    print("INITIALIZING COMBAT SYSTEM...")
    print()
    
    # Starting conditions
    start_capital = 10000.0
    capital = start_capital
    positions = []
    history = []
    frame = 0
    
    # Add some mock positions
    positions.append({
        'asset': 'BTC',
        'entry': 68400,
        'current': 69852,
        'stop': 67000,
        'tp1': 72000,
        'tp2': 75000,
        'tp3': 80000,
        'pnl_pct': 2.1,
        'status': 'HOLDING',
        'entry_time': datetime.now() - timedelta(hours=2)
    })
    
    # Add some mock history
    history.extend([
        {'time': '12:15', 'asset': 'ETH', 'pnl': 8.5, 'result': 'TP1_HIT'},
        {'time': '11:42', 'asset': 'AVAX', 'pnl': -2.2, 'result': 'STOP_LOSS'},
        {'time': '10:30', 'asset': 'BTC', 'pnl': 12.3, 'result': 'TP2_HIT'},
        {'time': '09:15', 'asset': 'BNB', 'pnl': 5.7, 'result': 'TP1_HIT'},
        {'time': '08:00', 'asset': 'ETH', 'pnl': -1.8, 'result': 'STOP_LOSS'},
    ])
    
    try:
        while True:
            # Simulate position updates
            if positions and random.random() < 0.1:  # 10% chance of exit per frame
                pos = positions.pop(0)
                pnl = pos['pnl_pct']
                capital += (pnl / 100) * (capital * 0.12)  # 12% position size
                history.append({
                    'time': datetime.now().strftime('%H:%M'),
                    'asset': pos['asset'],
                    'pnl': pnl,
                    'result': 'TP1_HIT' if pnl > 5 else 'STOP_LOSS'
                })
            
            # Simulate new signal
            if random.random() < 0.05 and len(positions) < 3:  # 5% chance of new signal
                assets = ['ETH', 'AVAX', 'BNB']
                new_pos = {
                    'asset': random.choice(assets),
                    'entry': data[random.choice(assets)]['price'] if 'data' in dir() else 2000,
                    'current': 0,
                    'stop': 0,
                    'tp1': 0,
                    'tp2': 0,
                    'tp3': 0,
                    'pnl_pct': 0,
                    'status': 'EXTREME_SIGNAL',
                    'entry_time': datetime.now()
                }
                
                # Set targets based on asset
                if new_pos['asset'] == 'ETH':
                    new_pos['entry'] = 2085
                    new_pos['stop'] = 2000
                    new_pos['tp1'] = 2200
                    new_pos['tp2'] = 2350
                    new_pos['tp3'] = 2600
                elif new_pos['asset'] == 'BNB':
                    new_pos['entry'] = 634
                    new_pos['stop'] = 610
                    new_pos['tp1'] = 670
                    new_pos['tp2'] = 710
                    new_pos['tp3'] = 780
                elif new_pos['asset'] == 'AVAX':
                    new_pos['entry'] = 9.46
                    new_pos['stop'] = 9.0
                    new_pos['tp1'] = 10.2
                    new_pos['tp2'] = 11.0
                    new_pos['tp3'] = 12.5
                
                new_pos['current'] = new_pos['entry']
                positions.append(new_pos)
            
            # Render frame
            render_war_room(frame, positions, history, capital, start_capital)
            
            frame += 1
            time.sleep(2)  # Update every 2 seconds
            
    except KeyboardInterrupt:
        clear()
        print("\n" + "=" * 80)
        print("🛑 WAR ROOM SHUTDOWN".center(80))
        print("=" * 80)
        print()
        print(f"Final Equity: ${capital:,.2f}")
        print(f"Total Return: {(capital/start_capital-1)*100:+.2f}%")
        print(f"Battles Fought: {len(history)}")
        wins = sum(1 for h in history if h['pnl'] > 0)
        print(f"Victories: {wins} ({wins/len(history)*100:.1f}% win rate)")
        print()
        print("Goodbye, commander.")
        print("=" * 80)


if __name__ == '__main__':
    print("=" * 80)
    print("WAR ROOM DEMO - Real-Time Combat Simulation")
    print("=" * 80)
    print()
    print("This demo shows what the live war room looks like with:")
    print("  • Real-time price updates")
    print("  • Live position tracking")
    print("  • P&L calculation")
    print("  • Signal generation")
    print()
    input("Press ENTER to enter the War Room...")
    
    simulate_war_room()
