#!/usr/bin/env python3
"""per_class_bootstrap_edge.py — Operator-grade statistical edge per asset class.

2000-iteration bootstrap on tournament_picks pnl, post 7 audit cleanup rounds.
Requires WR 95% CI lower bound >= 50% for "CONFIRMED" status.

Usage: python3 tools/per_class_bootstrap_edge.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pymysql, numpy as np
from collections import defaultdict

def bootstrap_wr_ci(pnls, n_boot=2000, alpha=0.05, seed=42):
    if not pnls: return 0,0,0
    rng=np.random.default_rng(seed)
    pnls=np.array(pnls); n=len(pnls)
    wrs=[(pnls[rng.integers(0,n,n)]>0).sum()/n for _ in range(n_boot)]
    return float((pnls>0).mean()), float(np.quantile(wrs,alpha/2)), float(np.quantile(wrs,1-alpha/2))

def main():
    from tools.db_env import get_stocks_creds
    c=pymysql.connect(**get_stocks_creds(), connect_timeout=15)
    with c.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute("""SELECT asset_class, model_id, persona_id, symbol, direction, pnl_pct, exit_reason
                       FROM tournament_picks WHERE status IN ('WIN','LOSS') AND pnl_pct IS NOT NULL""")
        rows=cur.fetchall()
    c.close()
    by_class=defaultdict(list)
    for r in rows: by_class[r['asset_class']].append(r)
    def bucket(rows, keys, min_n=10):
        g=defaultdict(list)
        for r in rows:
            k=tuple(r[x] for x in keys)
            if all(v is not None for v in k): g[k].append((r['pnl_pct'], 'REPLAY' in (r['exit_reason'] or '')))
        out=[]
        for k,vs in g.items():
            pnls=[p for p,_ in vs]
            if len(pnls)<min_n: continue
            wr,lo,hi=bootstrap_wr_ci(pnls)
            if lo<0.50: continue
            wins=[p for p in pnls if p>0]; losses=[p for p in pnls if p<=0]
            pf=(sum(wins) if wins else 0)/(abs(sum(losses)) if losses else 0.0001)
            replay=sum(1 for _,r in vs if r)/len(vs)
            out.append((k,wr,lo,hi,pf,sum(pnls)/len(pnls),len(pnls),replay))
        return sorted(out, key=lambda x:-x[2])
    for cls in ('COMMODITY','ETF','CRYPTO','BOND','EQUITY','FUTURES','FOREX','PENNY'):
        crs=by_class.get(cls,[])
        if not crs: continue
        print(f'\n=== {cls} ({len(crs)} closed) ===')
        for label, keys in (('SYM+DIR',['symbol','direction']),('PERSONA',['persona_id']),('MODEL',['model_id'])):
            for k,wr,lo,hi,pf,avg,n,rep in bucket(crs,keys)[:3]:
                flag='[REPLAY]' if rep>0.25 else ''
                kstr='/'.join(str(x) for x in k)
                print(f'  {label:8} {kstr:30} n={n:>3} WR={wr*100:>4.1f}% CI[{lo*100:.0f}-{hi*100:.0f}] PF={pf:.2f} avg={avg:+.2f}%{flag}')

if __name__=='__main__': main()
