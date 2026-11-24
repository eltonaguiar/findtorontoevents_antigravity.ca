#!/usr/bin/env python3
"""Generic daily-cell measurer for the 1000-cell backlog (crypto daily klines).

Usage: python tools/measure_cell_daily.py SYMBOL STRATEGY
Strategies: trend_pullback, rsi2_pullback, breakout. Horizon fixed at 1d. Hold=5 daily bars,
net of 26bp round-turn. Writes results/cells/<SYM>_<strategy>_1d.json and prints a JSON line.
"""
import csv, json, glob, sys, random, statistics as st, subprocess
from datetime import datetime, timezone
from pathlib import Path

COST=26.0; N_TRIALS=1000; HOLD=5
FILES=["Kimi_Agent_Winning Algo_ Signals & Communities_Feb 14 2026/crypto_daily_klines.csv",
       "Kimi_Agent_Crypto Pick Strategy Challenge Winners/crypto_daily_klines.csv"]

def load(sym):
    best=None
    for f in FILES:
        try: rows=[r for r in csv.DictReader(open(f)) if r['symbol']==sym]
        except: continue
        if rows and (best is None or len(rows)>len(best)): best=rows
    if not best: return None
    best.sort(key=lambda r:r['open_time'])
    return [float(r['close']) for r in best]

def ema(v,s):
    k=2/(s+1); o=[v[0]]
    for x in v[1:]: o.append(x*k+o[-1]*(1-k))
    return o

def rsi(v,p=14):
    o=[None]*len(v); g=l=0.0; ag=al=None
    for i in range(1,len(v)):
        ch=v[i]-v[i-1]; gg=max(ch,0); ll=max(-ch,0)
        if i<=p:
            g+=gg; l+=ll
            if i==p: ag,al=g/p,l/p; o[i]=100 if al==0 else 100-100/(1+ag/al)
        else:
            ag=(ag*(p-1)+gg)/p; al=(al*(p-1)+ll)/p; o[i]=100 if al==0 else 100-100/(1+ag/al)
    return o

def signals(closes, strat):
    """return list of entry indices."""
    idx=[]
    if strat=="trend_pullback":
        e50,e200,r=ema(closes,50),ema(closes,200),rsi(closes,14)
        i=200
        while i<len(closes)-HOLD:
            if e50[i]>e200[i] and r[i] is not None and r[i-1] is not None and r[i]<40<=r[i-1]:
                idx.append(i); i+=HOLD+1; continue
            i+=1
    elif strat=="rsi2_pullback":
        r2=rsi(closes,2)
        i=3
        while i<len(closes)-HOLD:
            if r2[i] is not None and r2[i]<10:
                idx.append(i); i+=HOLD+1; continue
            i+=1
    elif strat=="breakout":
        i=20
        while i<len(closes)-HOLD:
            if closes[i]>max(closes[i-20:i]):
                idx.append(i); i+=HOLD+1; continue
            i+=1
    else:
        raise SystemExit("unknown strategy "+strat)
    return idx

def measure(sym,strat):
    closes=load(sym)
    res={"cell":f"{sym}/{strat}/1d","horizon":"1d","strategy":strat}
    if not closes:
        res.update({"verdict":"BLOCKED_NO_DATA","bars":0,"reason":"no daily bars for symbol"}); return res
    res["bars"]=len(closes)
    idx=signals(closes,strat)
    trades=[]
    for i in idx:
        xi=min(i+HOLD,len(closes)-1)
        trades.append((closes[xi]/closes[i]-1)*1e4-COST)
    n=len(trades); res["n"]=n; res["cost_round_turn_bp"]=COST
    if n==0:
        res.update({"verdict":"KILLED","reason":"n=0"}); return res
    mean=st.mean(trades); rng=random.Random(7)
    bm=sorted(sum(trades[rng.randrange(n)] for _ in range(n))/n for _ in range(4000))
    ci=[round(bm[100],3),round(bm[3899],3)]
    obs=abs(mean); cnt=0
    for _ in range(4000):
        if abs(sum(trades[j]*(1 if rng.random()<.5 else -1) for j in range(n))/n)>=obs: cnt+=1
    p=(cnt+1)/4001
    dsr=None
    try:
        import sys; sys.path.insert(0,".")
        from alpha_engine.audit3_tribunal import deflated_sharpe
        d=deflated_sharpe([t/1e4 for t in trades],N_TRIALS); dsr=round(d["dsr"],4) if d else None
    except Exception: pass
    kill=(n<30) or (ci[0]<=0<=ci[1]) or (p>0.05)
    res.update({"net_mean_bp":round(mean,3),"ci95_bp":ci,"permutation_p":round(p,4),"dsr":dsr,
                "dsr_n_trials":N_TRIALS,"verdict":"KILLED" if kill else "DONE"})
    return res

def main():
    sym,strat=sys.argv[1],sys.argv[2]
    r=measure(sym,strat)
    r["git_sha"]=subprocess.run(["git","rev-parse","HEAD"],capture_output=True,text=True).stdout.strip()
    r["generated_at"]=datetime.now(timezone.utc).isoformat()
    p=Path(f"results/cells/{sym}_{strat}_1d.json"); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(r,indent=2)+"\n")
    print(json.dumps({k:r.get(k) for k in ("cell","bars","n","net_mean_bp","ci95_bp","permutation_p","dsr","verdict")}))

if __name__=="__main__": main()
