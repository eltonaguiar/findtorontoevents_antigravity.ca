"""Performance report generator — wired into tournament pipeline."""
import pymysql, json, os
from datetime import datetime, timezone

conn = pymysql.connect(host='mysql.50webs.com', user='ejaguiar1_stocks', password=os.environ.get('DB_PASS_STOCKS','') or os.environ.get('MYSQL_PASSWORD',''), database='ejaguiar1_stocks', port=3306, connect_timeout=15)
cur = conn.cursor()

report = {
    'generated_at': datetime.now(timezone.utc).isoformat(),
    'period': 'all_time',
    'models': []
}

cur.execute("""
    SELECT model_id, COUNT(*),
           SUM(CASE WHEN status='WIN' THEN 1 ELSE 0 END),
           SUM(CASE WHEN status='LOSS' THEN 1 ELSE 0 END),
           ROUND(AVG(CASE WHEN status IN ('WIN','LOSS') THEN pnl_pct ELSE NULL END), 2),
           ROUND(STD(CASE WHEN status IN ('WIN','LOSS') THEN pnl_pct ELSE NULL END), 4),
           MAX(submitted_at),
           COUNT(DISTINCT persona_id), COUNT(DISTINCT asset_class)
    FROM tournament_picks GROUP BY model_id ORDER BY COUNT(*) DESC
""")
for r in cur.fetchall():
    total = int(r[1]); wins = int(r[2] or 0); losses = int(r[3] or 0)
    resolved = wins + losses; wr = round(wins/resolved*100,1) if resolved > 0 else 0
    avg_pnl = float(r[4]) if r[4] is not None else 0
    std_pnl = float(r[5]) if r[5] is not None else 0
    sharpe = round(avg_pnl / std_pnl, 3) if std_pnl > 0 else 0
    report['models'].append({
        'model_id': r[0], 'picks': total, 'resolved': resolved,
        'wins': wins, 'losses': losses, 'win_rate': wr,
        'avg_pnl_pct': avg_pnl, 'std_pnl_pct': std_pnl,
        'sharpe': sharpe, 'last_pick': str(r[6] or '')[:16],
        'personas': int(r[7]), 'classes': int(r[8])
    })

total_wins = sum(m['wins'] for m in report['models'])
total_resolved = sum(m['resolved'] for m in report['models'])
report['summary'] = {
    'total_picks': sum(m['picks'] for m in report['models']),
    'total_resolved': total_resolved,
    'total_wins': total_wins,
    'total_losses': sum(m['losses'] for m in report['models']),
    'overall_wr': round(total_wins / max(total_resolved, 1) * 100, 1),
    'n_models': len(report['models']),
    'avg_sharpe': round(sum(m['sharpe'] for m in report['models'] if m['resolved'] > 0) / max(sum(1 for m in report['models'] if m['resolved'] > 0), 1), 3)
}

# Top 5 models by Sharpe
report['top_5_sharpe'] = sorted([m for m in report['models'] if m['resolved'] >= 10], key=lambda x: -x['sharpe'])[:5]

out = r'c:\findtorontoevents_antigravity.ca\audit_dashboard\data\research\performance_report.json'
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, 'w') as f:
    json.dump(report, f, indent=2)

print(f'Report: {report["summary"]["total_picks"]} picks, {report["summary"]["n_models"]} models, WR={report["summary"]["overall_wr"]}%, Avg Sharpe={report["summary"]["avg_sharpe"]}')
print(f'Top models:')
for m in report['top_5_sharpe']:
    print(f'  {m["model_id"]:25s} Sharpe={m["sharpe"]} WR={m["win_rate"]}% PnL={m["avg_pnl_pct"]}%')

conn.close()
