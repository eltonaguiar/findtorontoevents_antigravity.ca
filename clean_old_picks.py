#!/usr/bin/env python3
# Clean old picks from all active_picks.json files. Close >48h to closed_picks.json.

import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path('.')
MAX_AGE_HOURS = 48

def clean_system(system_dir):
    active_path = REPO_ROOT / system_dir / 'data' / 'active_picks.json'
    closed_path = REPO_ROOT / system_dir / 'data' / 'closed_picks.json'
    if not active_path.exists():
        return 0
    with open(active_path) as f:
        picks = json.load(f)
    now = datetime.now(timezone.utc)
    old = []
    active_new = []
    for p in picks:
        if not isinstance(p, dict):
            active_new.append(p)
            continue
        ts = p.get('timestamp')
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                age_h = (now - dt).total_seconds() / 3600
                if age_h > MAX_AGE_HOURS:
                    p['status'] = 'EXPIRED'
                    p['exit_reason'] = f'MAX_HOLD_{MAX_AGE_HOURS}h'
                    old.append(p)
                else:
                    active_new.append(p)
            except:
                active_new.append(p)
        else:
            active_new.append(p)
    # Write back
    with open(active_path, 'w') as f:
        json.dump(active_new, f, indent=2)
    if old:
        closed = []
        closed_path.parent.mkdir(exist_ok=True)
        if closed_path.exists():
            with open(closed_path) as f:
                closed = json.load(f)
        closed.extend(old)
        with open(closed_path, 'w') as f:
            json.dump(closed, f, indent=2)
    return len(old)

total_closed = 0
for sys in ['alpha_engine', 'mercury2', 'KIMI_RISEOFTHECLAW', 'battleground', 'crypto_ml_edge', 'rapid_fire_data', 'genome']:
    closed = clean_system(sys)
    total_closed += closed
    print(f'{sys}: closed {closed} old picks')

print(f'Total old picks closed: {total_closed}')
