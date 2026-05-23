import json
from isolated_signal_integrator import integrate_isolated_signals
try:
    from elite_scorer import enrich_picks_with_elite_score
except Exception:
    pass
try:
    from forward_validator import load_active_picks, save_active_picks
except Exception as e:
    def load_active_picks():
        with open('data/active_picks.json') as f: return json.load(f)
    def save_active_picks(p):
        with open('data/active_picks.json', 'w') as f: json.dump(p, f, indent=2)

def main():
    active = load_active_picks()
    iso_new = integrate_isolated_signals(active)
    if iso_new:
        print(f'Adding {len(iso_new)} new picks')
        active.extend(iso_new)
        
    print('Scoring picks...')
    active = enrich_picks_with_elite_score(active)
    
    quan = [p for p in active if 'quan_engine' in p.get('source_system', '')]
    print(f'Total QUAN picks in memory: {len(quan)}')
    for q in quan:
        print(f' - {q.get("symbol")} {q.get("strategy")} (Score: {q.get("elite_score", "None")})')
        print(f'   Breakdown: {q.get("elite_breakdown", {})}')
        
    save_active_picks(active)
    print('Saved to active_picks.json')

if __name__ == '__main__':
    main()
