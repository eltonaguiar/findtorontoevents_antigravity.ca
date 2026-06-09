#!/usr/bin/env python3
"""One-shot clean-cohort cross-check for cursor's 12 T2-shaped intrabar strategies."""
import json, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
import pymysql
from tools.db_env import get_stocks_creds

d = json.load(open('reports/reresolve_intrabar_latest.json'))
strats = d.get('strategies', [])
candidates = []
for s in strats:
    n = s.get('n', 0); twr = s.get('true_wr', 0); tpf = s.get('true_pf', 0)
    if n >= 30 and twr >= 50 and isinstance(tpf, (int, float)) and 1.5 <= tpf <= 10:
        candidates.append(s)
candidates.sort(key=lambda x: -x.get('true_pf', 0))
print(f'== T2-SHAPED INTRABAR STRATEGIES ({len(candidates)}) ==')
for c in candidates:
    print(f"  {c['strategy']:50s} n={c['n']:4} trueWR={c['true_wr']:5} truePF={c['true_pf']:5}")

conn = pymysql.connect(**get_stocks_creds(), cursorclass=pymysql.cursors.DictCursor)
cur = conn.cursor()
print()
print('== CLEAN-COHORT CROSS-CHECK (no backfill, resolved_at not null, sane-pnl <=95) ==')
print(f"  {'strategy':42} {'ALL_n':>5} {'bf/null':>10} | {'CLEAN_n':>7} {'WR%':>5} {'PF':>5} {'mo':>3}  verdict")
results = []
for c in candidates:
    s = c['strategy']
    cur.execute(
        "SELECT COUNT(*) n, SUM(resolver_version LIKE 'backfill%%') bf, SUM(resolved_at IS NULL) nx"
        " FROM at_pick_outcomes WHERE strategy=%s AND status IN ('WON','LOST','EXPIRED','FLAT')", (s,))
    a = cur.fetchone()
    cur.execute(
        "SELECT COUNT(*) n, SUM(status='WON') w,"
        " ROUND(100*SUM(status='WON')/COUNT(*),1) wr,"
        " ROUND(SUM(CASE WHEN pnl_pct>0 THEN pnl_pct ELSE 0 END)/NULLIF(-SUM(CASE WHEN pnl_pct<0 THEN pnl_pct ELSE 0 END),0),2) pf,"
        " COUNT(DISTINCT YEAR(resolved_at)*100 + MONTH(resolved_at)) months"
        " FROM at_pick_outcomes WHERE strategy=%s AND status IN ('WON','LOST','EXPIRED','FLAT')"
        "   AND (resolver_version IS NULL OR resolver_version NOT LIKE 'backfill%%')"
        "   AND resolved_at IS NOT NULL AND ABS(pnl_pct) <= 95", (s,))
    b = cur.fetchone()
    n = b['n'] or 0; wr = b['wr'] or 0; pf = b['pf']; mo = b['months'] or 0
    if n < 30:
        verdict = 'INSUFFICIENT'
    elif mo < 3:
        verdict = 'INSUFFICIENT (months<3)'
    elif pf is None or pf <= 1.5 or wr <= 50:
        verdict = 'REFUTED'
    else:
        verdict = 'HOLDS'
    print(f"  {s[:42]:42} {a['n'] or 0:5d} {int(a['bf'] or 0):3d}/{int(a['nx'] or 0):3d}  | {n:7d} {wr:5} {str(pf):>5} {mo:3d}  {verdict}")
    results.append((s, n, wr, pf, mo, verdict, a['n'] or 0, int(a['bf'] or 0)))

# Summary
print()
print('== SUMMARY ==')
holds = [r for r in results if r[5] == 'HOLDS']
refuted = [r for r in results if r[5] == 'REFUTED']
insuff = [r for r in results if 'INSUFFICIENT' in r[5]]
print(f'  HOLDS: {len(holds)}/{len(results)}')
for s, n, wr, pf, mo, v, an, ab in holds:
    print(f"    {s}  n={n} wr={wr} pf={pf} mo={mo}")
print(f'  REFUTED: {len(refuted)}/{len(results)}')
for s, n, wr, pf, mo, v, an, ab in refuted:
    print(f"    {s}  n={n} wr={wr} pf={pf} mo={mo} (all_n={an} backfill={ab})")
print(f'  INSUFFICIENT: {len(insuff)}/{len(results)}')
for s, n, wr, pf, mo, v, an, ab in insuff:
    print(f"    {s}  n={n} mo={mo} (all_n={an} backfill={ab})")
conn.close()
