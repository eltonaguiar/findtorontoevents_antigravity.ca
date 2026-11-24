"""H-236: does H-201's momentum survive a 44-name PIT universe? Pre-registered."""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from per_class_edge_harness import fetch, xsmom, block_bootstrap, UNIVERSES, BENCH_SYMBOL

LOOK, TOPK, COST, REBAL = 126, 3, 10, 21

def stats(x, b):
    lo, hi = block_bootstrap(x)
    d = x - b
    dlo, _ = block_bootstrap(d)
    return {"n": int(len(x)), "mean_bps": round(1e4*float(x.mean()),3),
            "ci_lb_bps": round(1e4*float(lo),3), "ci_ub_bps": round(1e4*float(hi),3),
            "excess_bps": round(1e4*float(d.mean()),3), "excess_ci_lb_bps": round(1e4*float(dlo),3),
            "pass": bool(x.mean()>0 and lo>0 and d.mean()>0)}

def book(names):
    out={}
    for s in names:
        df=fetch(s)
        if df is not None and len(df)>200: out[s]=df
    if not out: return None
    return pd.concat({s:d["close"] for s,d in out.items()},axis=1).dropna(how="all"), sorted(out)

def main():
    pit=json.load(open('reports/pit_equity_universe_20261122.json'))
    names=pit['universe']; w=pit['window']
    s0,e0=pd.Timestamp(w['start']),pd.Timestamp(w['end'])
    bdf=fetch(BENCH_SYMBOL["EQUITY"]); bench=bdf["close"].pct_change().fillna(0.0)
    res={"hypothesis":"H-236","prereg":"plans/2026-11-23-prereg-H-236-h201-pit-universe.md",
         "window":w,"universe_declared":len(names),"books":{}}
    for label,uni in (("PIT_44",names),("MEGA_10",UNIVERSES["EQUITY"])):
        built=book(uni)
        if not built: continue
        closes,have=built
        net,_=xsmom(closes,LOOK,TOPK,COST,REBAL)
        m=(net.index>=s0)&(net.index<=e0)
        x=net[m].to_numpy(dtype=float); b=bench.reindex(net.index[m]).fillna(0.0).to_numpy(dtype=float)
        if len(x)<100: res["books"][label]={"error":"insufficient","n":int(len(x))}; continue
        st=stats(x,b); st["symbols_loaded"]=len(have)
        res["books"][label]=st
        print(f"{label:<8} nn={st['n']:4d} symbols={len(have):2d} mean {st['mean_bps']:>8.3f}bp "
              f"CI[{st['ci_lb_bps']:>8.3f},{st['ci_ub_bps']:>8.3f}] excess {st['excess_bps']:>7.3f} pass={st['pass']}")
    p=res["books"].get("PIT_44",{})
    verdict="REPLICATED" if p.get("pass") else "REFUTED"
    res["verdict"]={"label":verdict,"pit_44_passes":p.get("pass"),
                    "mega10_same_window_mean_bps":res["books"].get("MEGA_10",{}).get("mean_bps"),
                    "note":"5-year window; failure here bounds universe dependence, it does not overturn H-234"}
    print("VERDICT:",verdict)
    Path('reports/h236_h201_pit_universe_2026-11-23.json').write_text(json.dumps(res,indent=2)+"\n")
    print("wrote reports/h236_h201_pit_universe_2026-11-23.json")

if __name__=="__main__": main()
