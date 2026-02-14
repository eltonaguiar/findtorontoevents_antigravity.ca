#!/usr/bin/env python3
"""
P&L CLARITY DEMO - Shows exactly how trades are tracked
"""

from datetime import datetime, timedelta


def main():
    print("=" * 80)
    print("P&L TRACKING CLARITY DEMO")
    print("=" * 80)
    print()
    
    # Starting capital
    initial_capital = 10000.00
    current_capital = 10000.00
    
    # Trade history with CLEAR buy/sell times
    trades = [
        {
            'id': 'TRADE-0001',
            'asset': 'ETH',
            'bought_time': '2026-02-14 10:30:00',
            'bought_price': 2085.00,
            'sold_time': '2026-02-14 12:15:00',
            'sold_price': 2262.25,
            'position_size': 1200.00,
            'pnl_pct': 8.5,
            'pnl_usd': 102.00,
            'result': 'WIN'
        },
        {
            'id': 'TRADE-0002',
            'asset': 'AVAX',
            'bought_time': '2026-02-14 11:00:00',
            'bought_price': 9.50,
            'sold_time': '2026-02-14 11:42:00',
            'sold_price': 9.29,
            'position_size': 1200.00,
            'pnl_pct': -2.2,
            'pnl_usd': -26.40,
            'result': 'LOSS'
        },
        {
            'id': 'TRADE-0003',
            'asset': 'BTC',
            'bought_time': '2026-02-14 09:00:00',
            'bought_price': 68400.00,
            'sold_time': '2026-02-14 10:30:00',
            'sold_price': 76813.20,
            'position_size': 1200.00,
            'pnl_pct': 12.3,
            'pnl_usd': 147.60,
            'result': 'WIN'
        }
    ]
    
    # Calculate realized P&L from closed trades
    realized_pnl = sum(t['pnl_usd'] for t in trades)
    current_capital += realized_pnl
    
    # Current open position (not yet closed)
    open_position = {
        'id': 'TRADE-0004',
        'asset': 'BTC',
        'bought_time': '2026-02-14 12:00:00',
        'bought_price': 68400.00,
        'current_price': 69852.00,
        'position_size': 1200.00,
        'unrealized_pnl_pct': 2.12,
        'unrealized_pnl_usd': 25.44
    }
    
    unrealized_pnl = open_position['unrealized_pnl_usd']
    
    print("💰 CAPITAL & P&L BREAKDOWN")
    print("-" * 80)
    print(f"Initial Capital:        ${initial_capital:>12,.2f}")
    print()
    print("REALIZED (Closed Trades):")
    for t in trades:
        emoji = "✅" if t['result'] == 'WIN' else "❌"
        print(f"  {emoji} {t['id']}: {t['asset']} ${t['pnl_usd']:+,.2f} ({t['pnl_pct']:+.2f}%)")
    print(f"  ─────────────────────────────────────────")
    print(f"  TOTAL REALIZED:       ${realized_pnl:>+12,.2f}")
    print()
    print("UNREALIZED (Open Position):")
    print(f"  🎯 {open_position['id']}: {open_position['asset']} "
          f"${open_position['unrealized_pnl_usd']:+,.2f} ({open_position['unrealized_pnl_pct']:+.2f}%)")
    print(f"  ─────────────────────────────────────────")
    print(f"  TOTAL UNREALIZED:     ${unrealized_pnl:>+12,.2f}")
    print()
    print(f"CURRENT CAPITAL:        ${current_capital:>12,.2f}")
    print(f"(Available for trading, excluding unrealized)")
    print()
    print("=" * 80)
    print(f"TOTAL P&L (Realized + Unrealized): ${realized_pnl + unrealized_pnl:+,.2f}")
    print(f"TOTAL RETURN: {(realized_pnl + unrealized_pnl) / initial_capital * 100:+.2f}%")
    print("=" * 80)
    print()
    
    # Detailed trade history
    print("📋 COMPLETE TRADE HISTORY")
    print("-" * 80)
    print(f"{'Trade ID':<12} {'Asset':<6} {'Buy Time':<20} {'Buy $':<12} {'Sell Time':<20} {'Sell $':<12} {'P&L':<12}")
    print("-" * 80)
    
    for t in trades:
        print(f"{t['id']:<12} {t['asset']:<6} {t['bought_time']:<20} ${t['bought_price']:<11,.2f} "
              f"{t['sold_time']:<20} ${t['sold_price']:<11,.2f} ${t['pnl_usd']:+,.2f}")
    
    # Open position
    print(f"{open_position['id']:<12} {open_position['asset']:<6} {open_position['bought_time']:<20} "
          f"${open_position['bought_price']:<11,.2f} {'[OPEN]':<20} "
          f"${open_position['current_price']:<11,.2f} ${open_position['unrealized_pnl_usd']:+,.2f} (Unrealized)")
    
    print()
    print("=" * 80)
    print("KEY POINTS:")
    print("  • Realized P&L: Money actually made/lost from closed trades")
    print("  • Unrealized P&L: Paper gains/losses on open positions")
    print("  • Current Capital: Starting + Realized (available for new trades)")
    print("  • Total P&L: Realized + Unrealized (your actual performance)")
    print("=" * 80)


if __name__ == '__main__':
    main()
