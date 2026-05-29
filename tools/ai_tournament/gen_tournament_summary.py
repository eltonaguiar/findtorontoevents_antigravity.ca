"""Generate summary data from tournament_picks for the summary page."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on path for db_env import
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.db_env import get_stocks_creds  # noqa: E402
import pymysql  # noqa: E402

creds = get_stocks_creds()
conn = pymysql.connect(**creds, cursorclass=pymysql.cursors.DictCursor)
cur = conn.cursor()

# Per-asset-class performance (matching fields the summary page expects)
cur.execute("""
    SELECT asset_class, COUNT(*) as total,
           SUM(CASE WHEN status='WIN' THEN 1 ELSE 0 END) as wins,
           SUM(CASE WHEN status='LOSS' THEN 1 ELSE 0 END) as losses,
           ROUND(AVG(CASE WHEN status IN ('WIN','LOSS') THEN pnl_pct ELSE NULL END), 2) as avg_pnl,
           ROUND(AVG(confidence+0), 4) as avg_conf,
           SUM(CASE WHEN pnl_pct > 0 THEN pnl_pct ELSE 0 END) as sum_win_pnl,
           SUM(CASE WHEN pnl_pct < 0 THEN pnl_pct ELSE 0 END) as sum_loss_pnl
    FROM tournament_picks GROUP BY asset_class ORDER BY total DESC
""")

systems = []
for r in cur.fetchall():
    ac = r['asset_class']
    total = int(r['total'] or 0)
    wins = int(r['wins'] or 0)
    losses = int(r['losses'] or 0)
    resolved = wins + losses
    # When resolved=0, wr and win_rate are null (not 0.0 — 0 resolved ≠ 0% WR)
    wr = round(wins / resolved * 100, 1) if resolved > 0 else None
    avg_pnl = float(r['avg_pnl']) if r['avg_pnl'] is not None else None
    avg_conf = float(r['avg_conf']) if r['avg_conf'] is not None else None
    # Profit Factor = sum(+pnl) / |sum(-pnl)| — NOT wins/losses ratio
    sum_win_pnl = float(r['sum_win_pnl'] or 0)
    sum_loss_pnl = float(r['sum_loss_pnl'] or 0)
    if sum_loss_pnl != 0:
        pf = round(sum_win_pnl / abs(sum_loss_pnl), 2)
    elif sum_win_pnl > 0:
        pf = float('inf')  # no losers, all positive
    elif resolved > 0:
        pf = 0.0  # all losers
    else:
        pf = None  # no data
    
    systems.append({
        'asset_class': ac,
        'display_name': ac.title(),
        'total_picks': total,
        'active_picks': total - resolved,
        'closed_picks': resolved,
        'wins': wins,
        'losses': losses,
        'win_rate_pct': wr,
        'win_rate': round(wins / resolved, 4) if resolved > 0 else None,
        'avg_pnl_pct': avg_pnl,
        'avg_confidence': avg_conf,
        'profit_factor': pf,
    })

# Readiness gates
cur.execute("""
    SELECT asset_class, 
           COUNT(*) >= 100 as passed_n,
           SUM(CASE WHEN status IN ('WIN','LOSS') THEN 1 ELSE 0 END) >= 30 as passed_resolved,
           ROUND(AVG(CASE WHEN status IN ('WIN','LOSS') THEN pnl_pct ELSE NULL END), 4) > 0 as passed_profitable
    FROM tournament_picks GROUP BY asset_class
""")
gates = {}
for r in cur.fetchall():
    ac = r['asset_class']
    gates[ac] = {
        'n_gate': bool(r['passed_n']),
        'resolved_gate': bool(r['passed_resolved']),
        'profitable_gate': bool(r['passed_profitable']),
        'all_passed': bool(r['passed_n']) and bool(r['passed_resolved']) and bool(r['passed_profitable'])
    }

summary = {
    'generated_at': datetime.now(timezone.utc).isoformat(),
    'total_picks': sum(s['total_picks'] for s in systems),
    'active_picks': sum(s['active_picks'] for s in systems),
    'closed_picks': sum(s['closed_picks'] for s in systems),
    'total_wins': sum(s['wins'] for s in systems),
    'total_losses': sum(s['losses'] for s in systems),
    'overall_win_rate': round(sum(s['wins'] for s in systems) / max(sum(s['closed_picks'] for s in systems), 1) * 100, 1),
    'system_count': len(systems),
    'readiness_gates': gates,
    'systems': systems,
    'data_source': 'tournament_picks (AI Tournament Pipeline)',
    'note': 'Picks from AI Prediction Tournament. Active = OPEN picks. Closed = WIN + LOSS resolved picks.'
}

out = REPO / 'audit_dashboard' / 'data' / 'summary_tournament_data.json'
out.parent.mkdir(parents=True, exist_ok=True)
with out.open('w') as f:
    json.dump(summary, f, indent=2, default=str)

print(f'Generated tournament summary: {summary["total_picks"]} picks, {summary["system_count"]} asset classes')
print(f'Active: {summary["active_picks"]}, Closed: {summary["closed_picks"]}, WR: {summary["overall_win_rate"]}%')
print(f'\nReadiness gates:')
for ac, g in gates.items():
    status = '✅ ALL PASS' if g['all_passed'] else '⏳ BUILDING'
    print(f'  {ac:15s} {status}  n={g["n_gate"]} resolved={g["resolved_gate"]} profitable={g["profitable_gate"]}')

conn.close()
