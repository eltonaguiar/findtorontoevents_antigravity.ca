#!/usr/bin/env python3
"""tactical_blend_tracker.py — the v2 POC: 50/50 blend of two regime-complementary TAA
strategies (rotation top5-6m + VAA-G4). Beats BOTH components 2007-2026 (Sharpe 0.89 vs
0.82/0.73, Calmar 0.50, MaxDD -16% vs SPY -51%) with the smoothest regime profile.
See reports/TACTICAL_ROTATION_EDGE_2026-07-04.md. Read-only sidecar; no orders.
    python3 tools/tactical_blend_tracker.py --stdout
"""
from __future__ import annotations
import argparse, json, os, sys
from collections import defaultdict
from datetime import datetime, timezone
sys.path.insert(0, "/home/eaguiar2015/findtorontoevents_antigravity.ca")
from tools.db_env import get_stocks_creds
import pymysql
OUT = os.path.join("/home/eaguiar2015/findtorontoevents_antigravity.ca", "audit_dashboard", "data", "tactical_blend_status.json")
ROT_UNIV = ["SPY","QQQ","IWM","EFA","EEM","TLT","IEF","AGG","GLD","DBC","VNQ","LQD","HYG","TIP"]
OFF = ["SPY","EFA","EEM","AGG"]; DEFN = ["LQD","IEF","SHY"]

def _px():
    keep=("host","user","password","database","port","connect_timeout")
    c=pymysql.connect(**{k:v for k,v in get_stocks_creds().items() if k in keep}); cur=c.cursor()
    syms=set(ROT_UNIV)|set(OFF)|set(DEFN)
    cur.execute("SELECT symbol,trade_date,close FROM etf_daily_ohlcv WHERE close>0 AND symbol IN (%s) ORDER BY trade_date"
                % ",".join(["%s"]*len(syms)), tuple(syms))
    p=defaultdict(dict)
    for s,d,cl in cur.fetchall(): p[s][str(d)]=float(cl)
    c.close(); return p

def compute():
    p=_px()
    def series(s): return sorted(p.get(s,{}))
    def ret_n(s,n):
        ds=series(s)
        return (p[s][ds[-1]]/p[s][ds[-1-n]]-1) if len(ds)>n and p[s][ds[-1-n]]>0 else None
    # rotation: top5 by 6m (~126 trading days)
    rot=sorted([(s, ret_n(s,126)) for s in ROT_UNIV if ret_n(s,126) is not None], key=lambda x:-x[1])[:5]
    # VAA-13612W
    def m13612(s):
        v=0
        for w,n in [(12,21),(4,63),(2,126),(1,252)]:
            rr=ret_n(s,n)
            if rr is None: return None
            v+=w*rr
        return v
    offs={s:m13612(s) for s in OFF if m13612(s) is not None}
    defs={s:m13612(s) for s in DEFN if m13612(s) is not None}
    vaa_pick = (max(offs,key=offs.get) if offs and all(v>0 for v in offs.values()) else (max(defs,key=defs.get) if defs else "AGG"))
    # combine 50% rotation (10% each of top5), 50% VAA single pick
    w=defaultdict(float)
    for s,_ in rot: w[s]+=0.10
    w[vaa_pick]+=0.50
    latest=max((max(p[s]) for s in p if p[s]), default=None)
    return {"strategy":"50/50 rotation(top5-6m)+VAA-G4 blend (v2 POC)","kind":"smart-beta TAA blend — best risk-adjusted of the family (Sharpe 0.89, MaxDD -16% 2007-26)",
            "generated_at":datetime.now(timezone.utc).isoformat(),"as_of":latest,
            "rotation_top5":[s for s,_ in rot],"vaa_pick":vaa_pick,
            "target_weights":{k:round(v,3) for k,v in sorted(w.items(),key=lambda x:-x[1])},
            "note":"rebalance monthly; benchmark vs SPY. Blend beats both components + smoothest regime profile."}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--stdout",action="store_true"); a=ap.parse_args()
    st=compute()
    if a.stdout: print(json.dumps(st,indent=2,default=str)); return 0
    os.makedirs(os.path.dirname(OUT),exist_ok=True); open(OUT,"w").write(json.dumps(st,indent=2,default=str))
    print("wrote",OUT,"weights",st["target_weights"]); return 0
if __name__=="__main__": sys.exit(main())
