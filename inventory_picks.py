#!/usr/bin/env python3
"""Quick inventory of closed picks across all systems for health dashboard."""

import json
from pathlib import Path

systems = [
    ('System A (Filter)', 'ml_battleground/system_a_filter/data/closed_picks.json'),
    ('System B (Regime)', 'ml_battleground/system_b_regime/data/closed_picks.json'),
    ('System C (Neural)', 'ml_battleground/system_c_deeplearn/data/closed_picks.json'),
    ('Alpha Engine', 'alpha_engine/data/closed_picks.json'),
    ('KIMI Rise of Claw', 'KIMI_RISEOFTHECLAW/data/closed_picks.json'),
]

print("=== Closed Picks Inventory ===\n")
total = 0
for name, path_str in systems:
    p = Path(path_str)
    if p.exists():
        try:
            data = json.loads(p.read_text())
            count = len(data) if isinstance(data, list) else 0
            total += count
            print(f"{name:25} {count:6d} closed picks")
        except Exception as e:
            print(f"{name:25} ERROR - {e}")
    else:
        print(f"{name:25} FILE NOT FOUND")

print(f"\nTotal closed picks across systems: {total}")

# Check active picks for Crypto ML Edge
active_picks_path = Path('crypto_ml_edge/data/active_picks.json')
if active_picks_path.exists():
    try:
        act = json.loads(active_picks_path.read_text())
        print(f"\nCrypto ML Edge active picks: {len(act.get('picks', []))}")
    except:
        pass
