"""Merge copy trader picks into tournament picks file."""
import json, os
from datetime import datetime

repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ct_path = os.path.join(repo, 'audit_dashboard', 'data', 'copy_trader_tournament_picks.json')
if not os.path.exists(ct_path):
    print('[merge_ct] No copy trader picks found')
    exit(0)

ct = json.load(open(ct_path))
picks_file = os.path.join(repo, 'data', 'ai_tournament', f'picks_{datetime.utcnow().strftime("%Y%m%d")}.json')
existing = json.load(open(picks_file)) if os.path.exists(picks_file) else []
existing.extend(ct)
json.dump(existing, open(picks_file, 'w'), indent=2)
print(f'[merge_ct] Merged {len(ct)} copy trader picks into {picks_file} ({len(existing)} total)')
