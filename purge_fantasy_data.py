#!/usr/bin/env python3
"""
PURGE FANTASY PnL DATA
Removes all entries with |PnL| > 100% as they are calculation errors
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

BACKUP_DIR = Path("backups") / datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

def purge_file(filepath, max_pnl=100):
    """Remove entries with |PnL| > max_pnl"""
    filepath = Path(filepath)
    if not filepath.exists():
        print(f"[SKIP] {filepath} not found")
        return 0
    
    # Backup first
    backup_path = BACKUP_DIR / filepath.name
    shutil.copy(filepath, backup_path)
    print(f"[BACKUP] {filepath} -> {backup_path}")
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        print(f"[SKIP] {filepath} is not a list")
        return 0
    
    original_count = len(data)
    filtered = []
    removed = []
    
    for entry in data:
        pnl = entry.get('total_pnl_pct', 0)
        if abs(pnl) > max_pnl:
            removed.append({
                'strategy': entry.get('strategy', 'unknown'),
                'pnl': pnl,
                'trades': entry.get('total_trades', 0)
            })
        else:
            filtered.append(entry)
    
    # Write filtered data
    with open(filepath, 'w') as f:
        json.dump(filtered, f, indent=2)
    
    print(f"[PURGED] {filepath}: {original_count} -> {len(filtered)} entries")
    for r in removed:
        print(f"         - {r['strategy']}: {r['pnl']:+.2f}% ({r['trades']} trades)")
    
    return len(removed)

print("=" * 60)
print("FANTASY DATA PURGE - Removing |PnL| > 100% entries")
print("=" * 60)

total_removed = 0
total_removed += purge_file('alpha_engine/data/prove_winners_results.json')

print("\n" + "=" * 60)
print(f"TOTAL REMOVED: {total_removed} fantasy entries")
print(f"BACKUPS: {BACKUP_DIR}")
print("=" * 60)
