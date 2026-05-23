#!/usr/bin/env python3
"""Verify trade data from bundle_babies.db.
Usage: python verify_trades.py [--db PATH]"""
import argparse
import sqlite3
from pathlib import Path

def _resolve_db(path: str | None) -> str:
    if path:
        return path
    # Auto-detect relative to script location
    default = Path(__file__).resolve().parent.parent / "battleground" / "data" / "bundle_babies.db"
    return str(default)

parser = argparse.ArgumentParser(description="Verify trade data from bundle_babies.db")
parser.add_argument("--db", default=None, help="Path to bundle_babies.db (default: battleground/data/bundle_babies.db)")
args = parser.parse_args()

conn = sqlite3.connect(_resolve_db(args.db))
cursor = conn.cursor()

print("="*70)
print("VERIFYING TRADE DATA")
print("="*70)

print("\n=== BUNDLE SUMMARY ===")
cursor.execute('''SELECT bundle_id, name, forward_trades, forward_realized_pnl, 
                         backtest_total_return, backtest_trades
                  FROM bundle_babies 
                  ORDER BY forward_realized_pnl DESC''')

bundles = cursor.fetchall()
for row in bundles:
    bid, name, fw_trades, fw_pnl, bt_return, bt_trades = row
    print(f"\nBundle: {name}")
    print(f"  Forward: {fw_trades} trades, {fw_pnl or 0:.2f}% PnL")
    print(f"  Backtest: {bt_trades} trades, {bt_return or 0:.2f}% return")

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bundle_trades'")
if cursor.fetchone():
    print("\n" + "="*70)
    print("DETAILED TRADE BREAKDOWN")
    print("="*70)
    
    cursor.execute('SELECT COUNT(*) FROM bundle_trades')
    count = cursor.fetchone()[0]
    print(f"Total trades in bundle_trades table: {count}")
    
    if count > 0:
        cursor.execute('''SELECT trade_id, bundle_id, strategy_name, symbol, side,
                                entry_price, exit_price, realized_pnl_pct, status,
                                exit_reason, entry_time_est
                         FROM bundle_trades 
                         ORDER BY entry_time_utc DESC''')
        
        all_trades = cursor.fetchall()
        total_pnl = 0
        
        for row in all_trades:
            tid, bid, strat, sym, side, entry, exit_p, pnl, status, reason, time = row
            total_pnl += pnl or 0
            exit_str = f"${exit_p:.2f}" if exit_p else "N/A"
            print(f"\n{time}")
            print(f"  {sym} {side} | Strategy: {strat}")
            print(f"  Entry: ${entry:.2f} -> Exit: {exit_str}")
            print(f"  PnL: {pnl:+.2f}% | Status: {status} | Reason: {reason}")
        
        print(f"\n" + "="*70)
        print(f"CALCULATED TOTAL PnL: {total_pnl:.2f}%")
        print(f"FROM {len(all_trades)} TRADES")
        print("="*70)

conn.close()
