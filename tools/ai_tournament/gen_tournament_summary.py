"""Generate summary data from tournament_picks for the summary page."""
import pymysql, json, os
from datetime import datetime, timezone

conn = pymysql.connect(host='mysql.50webs.com', user='ejaguiar1_stocks', password='stocks1234560', database='ejaguiar1_stocks', port=3306, connect_timeout=15)
cur = conn.cursor()

# Per-asset-class performance (matching fields the summary page expects)
cur.execute("""
    SELECT asset_class, COUNT(*),
           SUM(CASE WHEN status='WIN' THEN 1 ELSE 0 END) as wins,
           SUM(CASE WHEN status='LOSS' THEN 1 ELSE 0 END) as losses,
           ROUND(AVG(CASE WHEN status IN ('WIN','LOSS') THEN pnl_pct ELSE NULL END), 2) as avg_pnl,
           ROUND(AVG(confidence+0), 4) as avg_conf
    FROM tournament_picks GROUP BY asset_class ORDER BY COUNT(*) DESC
""")

systems = []
for r in cur.fetchall():
    ac = r[0]
    total = int(r[1])
    wins = int(r[2] or 0)
    losses = int(r[3] or 0)
    resolved = wins + losses
    wr = round(wins / resolved * 100, 1) if resolved > 0 else 0
    avg_pnl = float(r[4]) if r[4] is not None else 0
    avg_conf = float(r[5]) if r[5] is not None else 0
    
    systems.append({
        'asset_class': ac,
        'display_name': ac.title(),
        'total_picks': total,
        'active_picks': total - resolved,
        'closed_picks': resolved,
        'wins': wins,
        'losses': losses,
        'win_rate_pct': wr,
        'win_rate': round(wins / resolved, 4) if resolved > 0 else 0,
        'avg_pnl_pct': avg_pnl,
        'avg_confidence': avg_conf,
        'profit_factor': round(wins / max(losses, 1), 2) if losses > 0 else wins,
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
    gates[r[0]] = {
        'n_gate': bool(r[1]),
        'resolved_gate': bool(r[2]),
        'profitable_gate': bool(r[3]),
        'all_passed': bool(r[1]) and bool(r[2]) and bool(r[3])
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

out = r'c:\findtorontoevents_antigravity.ca\audit_dashboard\data\summary_tournament_data.json'
with open(out, 'w') as f:
    json.dump(summary, f, indent=2)

print(f'Generated tournament summary: {summary["total_picks"]} picks, {summary["system_count"]} asset classes')
print(f'Active: {summary["active_picks"]}, Closed: {summary["closed_picks"]}, WR: {summary["overall_win_rate"]}%')
print(f'\nReadiness gates:')
for ac, g in gates.items():
    status = '✅ ALL PASS' if g['all_passed'] else '⏳ BUILDING'
    print(f'  {ac:15s} {status}  n={g["n_gate"]} resolved={g["resolved_gate"]} profitable={g["profitable_gate"]}')

conn.close()
