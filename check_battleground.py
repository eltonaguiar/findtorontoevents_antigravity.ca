#!/usr/bin/env python3
import json

with open('battleground/data/baby_strats_dashboard.json', 'r') as f:
    data = json.load(f)

print('='*70)
print('BATTLEGROUND DASHBOARD - BUNDLE STATUS')
print('='*70)
print(f"Total Bundles: {data.get('total_bundles', 'N/A')}")
print(f"Last Updated: {data.get('last_updated', 'N/A')}")

if 'sections' in data:
    print('\n--- Sections ---')
    for i, section in enumerate(data['sections']):
        section_name = section.get('section', section.get('title', f'section_{i}'))
        print(f"\n[{i}] {section_name}")
        if section_name == 'BUNDLE_BABIES_TOP':
            print(f"   Description: {section.get('description', 'N/A')}")
            bundles = section.get('bundles', [])
            print(f"   Bundles: {len(bundles)}")
            for b in bundles[:3]:
                print(f"\n   - {b.get('name', 'Unknown')}")
                print(f"     ID: {b.get('bundle_id', 'N/A')}")
                
                # Handle nested classification
                classification = b.get('classification', {})
                if classification:
                    print(f"     Classification: {classification.get('symbol_scope', 'N/A')} | {classification.get('timeframe_scope', 'N/A')} | {classification.get('direction_bias', 'N/A')}")
                
                # Handle nested backtest
                backtest = b.get('backtest', {})
                if backtest:
                    print(f"     Backtest Sharpe: {backtest.get('sharpe', 'N/A')}")
                    print(f"     Backtest Win Rate: {backtest.get('win_rate', 'N/A')}%")
                    print(f"     Backtest Max DD: {backtest.get('max_dd', 'N/A')}%")
                
                # Handle nested forward
                forward = b.get('forward', {})
                if forward:
                    print(f"     Forward Trades: {forward.get('trades', 'N/A')}")
                    print(f"     Forward Status: {forward.get('status', 'N/A')}")
                    print(f"     Forward Realized PnL: {forward.get('realized_pnl', 'N/A')}%")
                
                strategies = b.get('strategies', [])
                if strategies:
                    print(f"     Strategies ({len(strategies)}): {', '.join(strategies[:3])}")
