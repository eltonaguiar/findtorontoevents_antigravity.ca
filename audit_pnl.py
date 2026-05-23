#!/usr/bin/env python3
"""Audit PnL for suspicious values (>100% or <-100%)"""

import json
from pathlib import Path
from collections import defaultdict

def audit_pnl():
    # Load closed picks
    with open('alpha_engine/data/closed_picks.json', 'r') as f:
        picks = json.load(f)

    print("=" * 80)
    print("PnL AUDIT REPORT - Flagging any |PnL| > 100%")
    print("=" * 80)
    
    # Find any suspicious PnL values
    suspicious = []
    for pick in picks:
        pnl = pick.get('pnl_pct') or pick.get('pnl', 0)
        if abs(pnl) > 100:
            suspicious.append({
                'strategy': pick.get('strategy', 'unknown'),
                'symbol': pick.get('symbol', 'N/A'),
                'pnl': pnl,
                'entry': pick.get('entry_price'),
                'exit': pick.get('exit_price')
            })

    if suspicious:
        print(f"\n[!] FOUND {len(suspicious)} TRADES WITH |PnL| > 100%")
        print("-" * 80)
        for s in suspicious:
            print(f"  Strategy: {s['strategy']}")
            print(f"  Symbol:   {s['symbol']}")
            print(f"  PnL:      {s['pnl']:+.2f}%")
            print(f"  Entry:    {s['entry']}")
            print(f"  Exit:     {s['exit']}")
            print("-" * 80)
    else:
        print("\n[OK] No trades with |PnL| > 100% found")
        
    # Show high PnL trades (>20%) for review
    print("\n" + "=" * 80)
    print("High PnL Review (|PnL| > 20%)")
    print("=" * 80)
    high_pnl = [p for p in picks if abs(p.get('pnl_pct', 0) or p.get('pnl', 0)) > 20]
    if high_pnl:
        for pick in sorted(high_pnl, key=lambda x: abs(x.get('pnl_pct', 0) or x.get('pnl', 0)), reverse=True):
            pnl = pick.get('pnl_pct') or pick.get('pnl', 0)
            print(f"  {pick.get('strategy', 'unknown')[:40]:<40} {pick.get('symbol', 'N/A'):<10} {pnl:>+8.2f}%")
    else:
        print("  No trades with |PnL| > 20%")
    
    # Summary stats
    print("\n" + "=" * 80)
    print("PnL Distribution Summary")
    print("=" * 80)
    pnls = [p.get('pnl_pct') or p.get('pnl', 0) for p in picks]
    print(f"  Total trades:    {len(pnls)}")
    print(f"  Max PnL:         {max(pnls):+.2f}%")
    print(f"  Min PnL:         {min(pnls):+.2f}%")
    print(f"  Mean PnL:        {sum(pnls)/len(pnls):+.2f}%")
    print(f"  Median PnL:      {sorted(pnls)[len(pnls)//2]:+.2f}%")
    print("=" * 80)

if __name__ == "__main__":
    audit_pnl()
