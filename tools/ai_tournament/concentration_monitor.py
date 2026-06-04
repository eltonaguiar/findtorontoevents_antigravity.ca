"""Diversification and concentration monitor for tournament picks."""
import pymysql, json
import sys
from datetime import datetime, timezone
from pathlib import Path

# 2026-06-04 INCIDENT #89 scrub: canonical helper instead of hardcoded literal.
_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
from tools.db_env import get_stocks_creds  # noqa: E402

conn = pymysql.connect(**get_stocks_creds(), connect_timeout=15)
cur = conn.cursor()

# Per asset class concentration
cur.execute("""
    SELECT asset_class, COUNT(*),
           COUNT(DISTINCT model_id), COUNT(DISTINCT persona_id), COUNT(DISTINCT symbol)
    FROM tournament_picks
    WHERE status = 'OPEN'
    GROUP BY asset_class
    ORDER BY COUNT(*) DESC
""")
rows = cur.fetchall()
total_open = sum(r[1] for r in rows)

alerts = []
print(f'Total open picks: {total_open}')
for r in rows:
    pct = round(r[1] / total_open * 100, 1) if total_open > 0 else 0
    print(f'  {r[0]:15s} {r[1]:5d} picks ({pct:5.1f}%)  models={r[2]} personas={r[3]} symbols={r[4]}')
    
    # Alert if over-concentrated (>35% in one class)
    if pct > 35:
        alerts.append(f'HIGH CONCENTRATION: {r[0]} at {pct}% of open picks (threshold: 35%)')
    if r[2] < 3 and r[1] > 50:
        alerts.append(f'MODEL CONCENTRATION: {r[0]} has only {r[2]} models for {r[1]} picks')

# Model concentration
cur.execute("""
    SELECT model_id, COUNT(*) as cnt FROM tournament_picks
    WHERE status = 'OPEN' GROUP BY model_id ORDER BY cnt DESC LIMIT 5
""")
top_models = cur.fetchall()
if top_models:
    top_pct = round(top_models[0][1] / total_open * 100, 1) if total_open > 0 else 0
    if top_pct > 25:
        alerts.append(f'MODEL DOMINANCE: {top_models[0][0]} has {top_pct}% of all open picks')

concentration_data = {
    'generated_at': datetime.now(timezone.utc).isoformat(),
    'total_open_picks': total_open,
    'alerts': alerts,
    'asset_classes': [{'class': r[0], 'picks': r[1], 'pct': round(r[1]/total_open*100,1) if total_open > 0 else 0,
                       'models': r[2], 'personas': r[3], 'symbols': r[4]} for r in rows]
}

import os
out = r'c:\findtorontoevents_antigravity.ca\audit_dashboard\data\research\concentration_report.json'
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, 'w') as f:
    json.dump(concentration_data, f, indent=2)

print(f'\nAlerts ({len(alerts)}):')
for a in alerts:
    print(f'  ⚠️  {a}')

conn.close()
