#!/usr/bin/env python3
"""
WAR ROOM - Simplified Version (Windows Compatible)
"""

import time
import random
from datetime import datetime, timedelta


def clear():
    print("\n" * 50)


def main():
    print("=" * 80)
    print("CRYPTOALPHA PRO - WAR ROOM".center(80))
    print("=" * 80)
    print()
    
    # Mock data
    capital = 10000.0
    positions = [
        {
            'asset': 'BTC',
            'entry': 68400,
            'current': 69852,
            'pnl': 2.1,
            'status': 'HOLDING'
        }
    ]
    
    history = [
        {'time': '12:15', 'asset': 'ETH', 'pnl': 8.5},
        {'time': '11:42', 'asset': 'AVAX', 'pnl': -2.2},
        {'time': '10:30', 'asset': 'BTC', 'pnl': 12.3},
    ]
    
    frame = 0
    
    try:
        while True:
            clear()
            
            print("=" * 80)
            print("CRYPTOALPHA PRO - WAR ROOM".center(80))
            print("=" * 80)
            print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Frame: {frame}")
            print()
            
            # Portfolio
            pnl = capital - 10000
            print("PORTFOLIO STATUS")
            print("-" * 80)
            print(f"  Starting Capital: $10,000.00")
            print(f"  Current Equity:   ${capital:,.2f}")
            print(f"  Total P&L:        ${pnl:+,.2f} ({pnl/100:.2f}%)")
            print()
            
            # Market Data
            print("LIVE MARKET DATA")
            print("-" * 80)
            print(f"  BTC:  $69,852.00 (+1.27%)")
            print(f"  ETH:  $2,085.74  (+1.34%)")
            print(f"  BNB:  $633.95    (+2.89%)")
            print(f"  AVAX: $9.46      (+3.06%)")
            print()
            
            # Open Positions
            print("ACTIVE COMBAT - OPEN POSITIONS")
            print("-" * 80)
            print(f"  {'Asset':<8} {'Entry':<12} {'Current':<12} {'P&L':<12} {'Status':<20}")
            for pos in positions:
                current = pos['current'] + random.uniform(-100, 100)
                pnl = (current - pos['entry']) / pos['entry'] * 100
                print(f"  {pos['asset']:<8} ${pos['entry']:<11,.2f} ${current:<11,.2f} {pnl:+.2f}%       {pos['status']:<20}")
            print()
            
            # History
            print("BATTLE HISTORY (Last 5)")
            print("-" * 80)
            print(f"  {'Time':<10} {'Asset':<8} {'Result':<10} {'P&L':<15}")
            for trade in history:
                result = "WIN" if trade['pnl'] > 0 else "LOSS"
                print(f"  {trade['time']:<10} {trade['asset']:<8} {result:<10} {trade['pnl']:+.2f}%")
            print()
            
            # Activity
            if frame % 3 == 0:
                print("RECENT ACTIVITY")
                print("-" * 80)
                activities = [
                    "Scanning BTC... Model agreement: 4/6",
                    "Scanning ETH... On-chain score: 75%",
                    "Checking AVAX... Volatility: 89th percentile",
                    "BNB analysis... Regime: SIDEWAYS"
                ]
                print(f"  {random.choice(activities)}")
                print()
            
            print("=" * 80)
            print("Press Ctrl+C to exit".center(80))
            print("=" * 80)
            
            frame += 1
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\nWAR ROOM SHUTDOWN")
        print(f"Final Equity: ${capital:,.2f}")
        print("Goodbye, commander.")


if __name__ == '__main__':
    main()
