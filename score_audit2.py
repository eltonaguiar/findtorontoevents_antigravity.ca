import json
from alpha_engine.elite_scorer import compute_elite_score
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
try:
    scan_dashboard()
except Exception as e:
    print(e)
