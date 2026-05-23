#!/usr/bin/env python3
"""
Comprehensive audit of ALL prove_winners_results.json files
Flags any entry with |PnL| > 100% as fictional/calculation error
"""

import json
import shutil
from pathlib import Path
from datetime import datetime

# Files to audit (main + backup + any worktree copies)
files_to_audit = [
    Path('alpha_engine/data/prove_winners_results.json'),
    Path('backups/20260228_034618/prove_winners_results.json'),
]

# Also check if there are any other copies
all_files = list(Path('.').rglob('prove_winners_results.json'))
# Filter to only those in project directories (not temp)
files_to_audit = [f for f in all_files if 'Temp' not in str(f) and 'AppData' not in str(f)]

print("=" * 80)
print("FANTASY DATA AUDIT - prove_winners_results.json")
print("Flagging any |PnL| > 100% as calculation error")
print("=" * 80)

fantasy_found = []

for filepath in files_to_audit:
    if not filepath.exists():
        print(f"\n[MISSING] {filepath}")
        continue
    
    print(f"\n[CHECKING] {filepath}")
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    file_fantasy = []
    for entry in data:
        pnl = entry.get('total_pnl_pct', 0)
        strategy = entry.get('strategy', 'unknown')
        
        if abs(pnl) > 100:
            file_fantasy.append({
                'strategy': strategy,
                'pnl': pnl,
                'win_rate': entry.get('win_rate'),
                'trades': entry.get('total_trades'),
                'avg_win': entry.get('avg_win'),
                'avg_loss': entry.get('avg_loss')
            })
    
    if file_fantasy:
        print(f"  [!] FOUND {len(file_fantasy)} FANTASY ENTRIES:")
        for f in file_fantasy:
            print(f"      - {f['strategy']}: {f['pnl']:+.2f}% (WR: {f['win_rate']}%, {f['trades']} trades)")
            print(f"        Avg Win: {f['avg_win']}%, Avg Loss: {f['avg_loss']}%")
        fantasy_found.extend([(filepath, f['strategy']) for f in file_fantasy])
    else:
        print("  [OK] No fantasy entries found")

print("\n" + "=" * 80)
print(f"SUMMARY: {len(fantasy_found)} fantasy entries across {len(files_to_audit)} files")
print("=" * 80)

# Offer to purge
if fantasy_found:
    print("\nTo purge all fantasy entries, run:")
    print("  python purge_fantasy_all.py")
