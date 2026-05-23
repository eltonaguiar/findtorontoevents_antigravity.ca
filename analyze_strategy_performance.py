import json
import os
from collections import defaultdict

DASHBOARD_DATA_PATH = r'e:\findtorontoevents_antigravity.ca\audit_dashboard\data\dashboard_data.json'
MANIFEST_PATH = r'e:\findtorontoevents_antigravity.ca\hub\data\systems_manifest.json'

def analyze():
    with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    systems_map = {sys['id']: sys for sys in manifest['systems']}
    
    with open(DASHBOARD_DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Data keys: {list(data.keys())}")
    
    active_picks = []
    closed_picks = []
    
    # Traverse data to find picks
    def find_picks(obj, parent_key=None):
        nonlocal active_picks, closed_picks
        if isinstance(obj, dict):
            # Check for 'active' or 'closed' lists
            if 'active' in obj and isinstance(obj['active'], list):
                for p in obj['active']:
                    if isinstance(p, dict):
                        if 'strategy' not in p: p['strategy'] = parent_key or 'unknown'
                        active_picks.append(p)
            if 'closed' in obj and isinstance(obj['closed'], list):
                for p in obj['closed']:
                    if isinstance(p, dict):
                        if 'strategy' not in p: p['strategy'] = parent_key or 'unknown'
                        closed_picks.append(p)
            if 'active_picks' in obj and isinstance(obj['active_picks'], list):
                for p in obj['active_picks']:
                    if isinstance(p, dict):
                        if 'strategy' not in p: p['strategy'] = parent_key or 'unknown'
                        active_picks.append(p)
            if 'closed_picks' in obj and isinstance(obj['closed_picks'], list):
                for p in obj['closed_picks']:
                    if isinstance(p, dict):
                        if 'strategy' not in p: p['strategy'] = parent_key or 'unknown'
                        closed_picks.append(p)
            
            # Recurse into dicts
            for k, v in obj.items():
                if k not in ['active', 'closed', 'active_picks', 'closed_picks']:
                    find_picks(v, k)
        elif isinstance(obj, list):
            # If it's a list, check if it's a list of picks (heuristically)
            for item in obj:
                if isinstance(item, dict) and ('symbol' in item or 'ticker' in item):
                    # We might be in a generic list of picks
                    # But without knowing if it's active or closed, we might duplicate
                    pass # Skip generic lists for now unless they are named 'active' or 'closed'

    find_picks(data)
    
    if not active_picks and 'activePicks' in data:
        active_picks = data['activePicks']
    if not closed_picks and 'closedPicks' in data:
        closed_picks = data['closedPicks']

    print(f"Total active: {len(active_picks)} | Total closed: {len(closed_picks)}")
    
    # Analysis
    strategy_perf = defaultdict(lambda: {'closed_count': 0, 'wins': 0, 'losses': 0, 'total_pnl': 0.0})
    active_perf = defaultdict(lambda: {'active_count': 0, 'unrealized_pnl': 0.0})
    
    for p in closed_picks:
        s = p.get('strategy') or p.get('strat_id') or 'unknown'
        if ':' in s: s = s.split(':')[0]
        perf = strategy_perf[s]
        perf['closed_count'] += 1
        pnl = float(p.get('pnl_pct') or p.get('pnl') or 0)
        perf['total_pnl'] += pnl
        if pnl > 0: perf['wins'] += 1
        elif pnl < 0: perf['losses'] += 1

    for p in active_picks:
        s = p.get('strategy') or p.get('strat_id') or 'unknown'
        if ':' in s: s = s.split(':')[0]
        perf = active_perf[s]
        perf['active_count'] += 1
        pnl = float(p.get('pnl_pct') or p.get('unrealized_pnl') or p.get('pnl') or 0)
        perf['unrealized_pnl'] += pnl

    all_strats = set(strategy_perf.keys()) | set(active_perf.keys())
    results = []
    for s in all_strats:
        c = strategy_perf[s]
        a = active_perf[s]
        wr = (c['wins']/c['closed_count']*100) if c['closed_count'] > 0 else 0
        sys_info = systems_map.get(s, {'name': s, 'methodology': 'N/A'})
        results.append({
            'id': s, 'name': sys_info['name'], 'methodology': sys_info.get('methodology', 'N/A'),
            'closed': c['closed_count'], 'wr': wr, 'pnl': c['total_pnl'],
            'active': a['active_count'], 'unrealized': a['unrealized_pnl']
        })
    
    results.sort(key=lambda x: x['pnl'] + x['unrealized'], reverse=True)
    
    print("\n=== TOP STRATEGIES ===")
    for r in results[:20]:
        print(f"[{r['id']}] {r['name']} | P/L: {r['pnl']:.2f}% | WR: {r['wr']:.1f}% | Active: {r['active']} (UPNL: {r['unrealized']:.2f}%)")
        print(f"  Methodology: {str(r['methodology'])[:120]}...")

if __name__ == "__main__":
    analyze()
