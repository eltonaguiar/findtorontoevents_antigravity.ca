import json
from collections import defaultdict

DASHBOARD_DATA_PATH = r'e:\findtorontoevents_antigravity.ca\audit_dashboard\data\dashboard_data.json'
CONSOLIDATED_PATH = r'e:\findtorontoevents_antigravity.ca\audit_dashboard\data\consolidated_portfolios.json'
MANIFEST_PATH = r'e:\findtorontoevents_antigravity.ca\hub\data\systems_manifest.json'

def final_audit():
    with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    systems_map = {sys['id']: sys for sys in manifest['systems']}
    
    with open(DASHBOARD_DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    leaderboard = data.get('leaderboard', [])
    active_picks = data.get('picks', {}).get('active', [])
    
    strategy_metrics = {}
    for item in leaderboard:
        strat = item['strategy']
        strategy_metrics[strat] = {
            'wr': item.get('fwd_wr', 0),
            'trades': item.get('fwd_trades', 0),
            'pnl': item.get('fwd_total_pnl', 0),
            'active': item.get('active_picks', 0),
            'system': item.get('system_name', 'Unknown')
        }

    # Calculate UPNL for top active strategies
    upnl_by_strat = defaultdict(float)
    active_count = defaultdict(int)
    for p in active_picks:
        s = p.get('strategy', 'unknown') or 'unknown'
        if ':' in s: s = s.split(':')[0]
        pnl_val = p.get('pnl_pct') or 0
        try:
            pnl = float(pnl_val)
        except (ValueError, TypeError):
            pnl = 0.0
        upnl_by_strat[s] += pnl
        active_count[s] += 1

    # Merge
    for s, upnl in upnl_by_strat.items():
        if s not in strategy_metrics:
            strategy_metrics[s] = {'wr': 0, 'trades': 0, 'pnl': 0, 'active': active_count[s], 'system': 'Unknown', 'upnl': upnl}
        else:
            strategy_metrics[s]['upnl'] = upnl
            strategy_metrics[s]['active'] = active_count[s]

    # Top strategies by Total P/L (Closed + Unrealized)
    top_strats = sorted(strategy_metrics.items(), key=lambda x: (x[1].get('pnl', 0) + x[1].get('upnl', 0)), reverse=True)
    
    print("TOP STRATEGIES BY TOTAL PERFORMANCE")
    for s, m in top_strats[:30]:
        total = m.get('pnl', 0) + m.get('upnl', 0)
        print(f"[{s}] Total: {total:.2f}% | Closed: {m['pnl']:.2f}% ({m['trades']} tr) | Active: {m.get('upnl', 0):.2f}% ({m['active']} tr)")

    # Feed Audit
    present_systems = set()
    for s, m in strategy_metrics.items():
        # Try to find which manifest system this belongs to
        # Sometimes strateg names are system IDs, sometimes they are child IDs
        if s in systems_map:
            present_systems.add(s)
        else:
            # Check if system name matches a manifest name
            for sid, sinfo in systems_map.items():
                if sinfo['name'] == m['system'] or sid in s:
                    present_systems.add(sid)

    manifest_ids = set(systems_map.keys())
    missing = manifest_ids - present_systems
    
    print("\nFEED AUDIT")
    print(f"Manifest Systems: {len(manifest_ids)}")
    print(f"Feeding Systems: {len(present_systems)}")
    print(f"Missing Systems: {', '.join(sorted(missing))}")

if __name__ == "__main__":
    final_audit()
