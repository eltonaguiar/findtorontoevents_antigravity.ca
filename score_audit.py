import json
from alpha_engine.elite_scorer import compute_elite_score
data = json.load(open('alpha_engine/data/active_predictions.json'))
n_zero = 0
for p in data:
    ml = float(p.get('ml_score', p.get('confidence', 0)))
    if p.get('elite_score', 0) == 0 and ml > 0.7:
        n_zero += 1
        res = compute_elite_score(p)
        new_score = res.get('elite_score', 0)
        print(f"[{p.get('source_system', '??')}] {p['symbol']} - Old: 0, New: {new_score}, ML: {ml}")
print(f"Total zero-scores with ML>0.7 found: {n_zero}")
def scan_dashboard():
    dashboard = json.load(open('audit_dashboard/data/dashboard_data.json'))
    active = dashboard.get('active_picks', [])
    n=0
    for p in active:
        ml = float(p.get('ml_score', p.get('confidence', 0)))
        if p.get('elite_score', 0) == 0 and ml > 0.7:
            n += 1
            res = compute_elite_score(p)
            print(f"[{p.get('source_system', '??')}] DASHBOARD: {p['symbol']} - Old: 0, New: {res.get('elite_score', 0)}, ML: {ml}")
    print(f"Total zero-scores with ML>0.7 in dashboard: {n}")
scan_dashboard()
