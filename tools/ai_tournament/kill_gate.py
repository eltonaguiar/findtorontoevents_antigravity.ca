"""Statistical Kill Gates — auto-prune failing strategies from tournament pipeline.

Stages:
  WATCH     — n < 20, not enough data to judge
  MONITOR   — n >= 20, WR >= 45%, passing
  WARN      — n >= 20, WR < 45% OR negative PnL, one more cycle to improve
  KILLED    — n >= 20, WR < 40% AND negative PnL, blocked from allocation
"""
import pymysql, json, os
from datetime import datetime, timezone

conn = pymysql.connect(host='mysql.50webs.com', user='ejaguiar1_stocks', password=os.environ.get('DB_PASS_STOCKS','') or os.environ.get('MYSQL_PASSWORD',''), database='ejaguiar1_stocks', port=3306, connect_timeout=15)
cur = conn.cursor()

cur.execute("""
    SELECT persona_id, asset_class, COUNT(*) as n,
           ROUND(AVG(CASE WHEN status='WIN' THEN 1.0 ELSE 0.0 END), 4) as wr,
           ROUND(AVG(pnl_pct), 4) as avg_pnl
    FROM tournament_picks
    WHERE status IN ('WIN','LOSS') AND persona_id != ''
    GROUP BY persona_id, asset_class
    HAVING n >= 5
    ORDER BY n DESC
""")

kills = []
for r in cur.fetchall():
    persona = r[0]; asset_class = r[1]; n = int(r[2])
    wr = float(r[3] or 0); avg_pnl = float(r[4] or 0)
    
    if n < 20:
        stage = "WATCH"
    elif wr >= 0.45 and avg_pnl >= 0:
        stage = "MONITOR"
    elif wr >= 0.40 and (avg_pnl >= 0 or wr >= 0.45):
        stage = "WARN"
    else:
        stage = "KILLED"
    
    kills.append({
        "persona_id": persona,
        "asset_class": asset_class,
        "n_resolved": n,
        "win_rate": round(wr * 100, 1),
        "avg_pnl_pct": round(avg_pnl, 2),
        "stage": stage,
        "recommendation": (
            "Insufficient data — collect until n>=20" if stage == "WATCH"
            else "Active — within performance thresholds" if stage == "MONITOR"
            else "Underperforming — one cycle to improve or auto-kill" if stage == "WARN"
            else "KILLED — negative expectancy with significant sample. Block allocation."
        )
    })

# Sort: KILLED first, then by severity
kills.sort(key=lambda x: ({"KILLED": 0, "WARN": 1, "WATCH": 2, "MONITOR": 3}[x["stage"]], -x["n_resolved"]))

report = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "total_pairs": len(kills),
    "killed": sum(1 for k in kills if k["stage"] == "KILLED"),
    "warn": sum(1 for k in kills if k["stage"] == "WARN"),
    "watch": sum(1 for k in kills if k["stage"] == "WATCH"),
    "monitor": sum(1 for k in kills if k["stage"] == "MONITOR"),
    "blocked_personas": [k["persona_id"] for k in kills if k["stage"] == "KILLED"],
    "warned_personas": [k["persona_id"] for k in kills if k["stage"] == "WARN"],
    "blocked_asset_classes": [],
    "warned_asset_classes": [],
    "pairs": kills,
}

# Check whole asset classes for negative expectancy
cur.execute("""
    SELECT asset_class, COUNT(*) as n,
           ROUND(AVG(pnl_pct), 4) as avg_pnl,
           ROUND(AVG(CASE WHEN status='WIN' THEN 1.0 ELSE 0.0 END), 4) as wr
    FROM tournament_picks
    WHERE status IN ('WIN','LOSS') AND asset_class != ''
    GROUP BY asset_class HAVING n >= 50
""")
for r in cur.fetchall():
    ac = r[0]; n = int(r[1]); pnl = float(r[2] or 0); wr = float(r[3] or 0)
    if n >= 100 and pnl < -0.20:
        report["blocked_asset_classes"].append(ac)
        print(f"  ASSET CLASS KILLED: {ac} (n={n}, WR={wr*100:.1f}%, PnL={pnl:+.2f}%)")
    elif n >= 50 and pnl < 0:
        report["warned_asset_classes"].append(ac)
        print(f"  ASSET CLASS WARN: {ac} (n={n}, WR={wr*100:.1f}%, PnL={pnl:+.2f}%)")

out = r'c:\findtorontoevents_antigravity.ca\audit_dashboard\data\research\kill_gate_report.json'
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, 'w') as f:
    json.dump(report, f, indent=2)

print(f"Kill gate: {len(kills)} pairs tested")
print(f"  KILLED: {report['killed']} | WARN: {report['warn']} | WATCH: {report['watch']} | MONITOR: {report['monitor']}")
for k in kills[:10]:
    icon = {"KILLED":"🔴","WARN":"🟡","WATCH":"⏳","MONITOR":"🟢"}[k["stage"]]
    print(f"  {icon} {k['persona_id']:25s} {k['asset_class']:12s} n={k['n_resolved']:3d} WR={k['win_rate']:5.1f}% PnL={k['avg_pnl_pct']:>+6.2f}% → {k['stage']}")

conn.close()
