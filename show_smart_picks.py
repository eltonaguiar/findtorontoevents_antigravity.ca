#!/usr/bin/env python3
"""Display Smart Picks from dashboard payload."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def main():
    payload_path = ROOT / "audit_trail" / "data" / "dashboard_payload.json"
    
    with open(payload_path) as f:
        data = json.load(f)
    
    print("=" * 70)
    print("SMART PICKS - Premium Quality Tier")
    print("=" * 70)
    print(f"Total Active: {len(data['picks']['active'])}")
    print(f"Smart Picks: {len(data['picks'].get('smart_picks', []))}")
    print(f"Percentage: {data['summary'].get('quality_stats', {}).get('smart_picks_percentage', 0)}%")
    print("=" * 70)
    print()
    
    for i, p in enumerate(data['picks'].get('smart_picks', []), 1):
        print(f"{i}. {p['symbol']} {p['direction']}")
        print(f"   Score: {p.get('score', 0)} | Confidence: {p.get('confidence', 0):.2f} | R:R: {p.get('rr_ratio', 'N/A')}")
        print(f"   Entry: ${p.get('entry_price', 0)} | TP: ${p.get('take_profit', 0)} | SL: ${p.get('stop_loss', 0)}")
        print(f"   Strategy: {p.get('strategy', 'Unknown')}")
        print(f"   Source: {p.get('source_system', 'Unknown')}")
        print()

if __name__ == "__main__":
    main()
