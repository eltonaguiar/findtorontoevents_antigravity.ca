#!/usr/bin/env python3
"""Generic 1000-cell runner: measure a (symbol,strategy,horizon) from repo bars.

Bars: crypto daily klines (BTC/ETH/SOL/XRP/DOGE) for 1d/1w; BTC 1h cache for 1h/4h.
Strategies (long-only, hold H bars, net 26bp). gap_fade needs 'open' -> blocked on daily-close klines.
Prints JSON artifact; writes results/cells/<sym>_<strat>_<hz>.json.
"""
import csv, json, glob, sys, random, statistics as st, subprocess
from datetime import datetime, timezone
from pathlib import Path

COST=26.0; N_TRIALS=1000
DAILY_FILES=["Kimi_Agent_Winning Algo_ Signals & Communities_Feb 14 2026/crypto_daily_klines.csv",
             "Kimi_Agent_Crypto Pick Strategy Challenge Winners/crypto_daily_klines.csv"]
HOLD={"1d":5,"1w":4,"1h":24,"4h":6}

def daily(sym):
    best=None
    for f in DAILY_FILES:
        try: rows=[r for r in csv.DictReader(open(f)) if r['symbol']==sym]
        except: continue
        if rows and (best is None or len(rows)>len(best)): best=rows
    if not best: return None
    best.sort(key=lambda r:r['open_time']); return [float(r['close']) for r in best]

def btc_1h():
    try: rows=list(csv.reader(open('data/cache/BTCUSDT_3mo_1h.csv')))[3:]
    except: return None
    o=[]
    for r in rows:
        try:o.append(float(r[1]))
        except:pass
    return o or None

def bars_for(sym,hz):
    if hz=="1d": return daily(sym)
    if hz=="1w":
        d=daily(sym); return d[::7] if d else None
    if hz=="1h": return btc_1h() if sym=="BTCUSDT" else None
    if hz=="4h":
        d=btc_1h(); return d[::4] if (sym=="BTCUSDT" and d) else None
    return None  # 15m: none in repo

def ema(v,s):
    k=2/(s+1);o=[v[0]]
    for x in v[1:]:o.append(x*k+o[-1]*(1-k))
    return o
def rsi(v,p=14):
    o=[None]*len(v);g=l=0.0;ag=al=None
    for i in range(1,len(v)):
        ch=v[i]-v[i-1];gg=max(ch,0);ll=max(-ch,0)
        if i<=p:
            g+=gg;l+=ll
            if i==p:ag,al=g/p,l/p;o[i]=100 if al==0 else 100-100/(1+ag/al)
        else:
            ag=(ag*(p-1)+gg)/p;al=(al*(p-1)+ll)/p;o[i]=100 if al==0 else 100-100/(1+ag/al)
    return o
def atr(c,hz):
    # proxy ATR from closes (true range needs high/low; use abs diff)
    return [abs(c[i]-c[i-1]) for i in range(1,len(c))]

def signals(c,strat,hz):
    n=len(c); idx=[]; H=HOLD[hz]; i=1
    def push(j): idx.append(j)
    if strat=="trend_pullback":
        e50,e200,r=ema(c,50),ema(c,200),rsi(c,14)
        while i<n-H:
            if e50[i]>e200[i] and r[i] is not None and r[i-1] is not None and r[i]<40<=r[i-1]: push(i); i+=H+1;continue
            i+=1
    elif strat=="rsi2_pullback":
        r2=rsi(c,2)
        while i<n-H:
            if r2[i] is not None and r2[i]<10: push(i); i+=H+1;continue
            i+=1
    elif strat in ("breakout","donchian"):
        i=20
        while i<n-H:
            if c[i]>max(c[i-20:i]): push(i); i+=H+1;continue
            i+=1
    elif strat=="ma_cross":
        e20,e50=ema(c,20),ema(c,50)
        i=50
        while i<n-H:
            if e20[i]>e50[i] and e20[i-1]<=e50[i-1]: push(i); i+=H+1;continue
            i+=1
    elif strat=="bb_meanrev":
        i=20
        while i<n-H:
            seg=c[i-20:i];m=st.mean(seg);sd=st.pstdev(seg)
            if sd>0 and c[i]<m-2*sd: push(i); i+=H+1;continue
            i+=1
    elif strat=="vwap_reversion":
        i=20
        while i<n-H:
            seg=c[i-20:i];m=st.mean(seg);sd=st.pstdev(seg)
            if sd>0 and c[i]<m-1*sd: push(i); i+=H+1;continue
            i+=1
    elif strat=="momentum_12_1":
        i=13
        while i<n-H:
            if c[i-1]>c[i-13] and c[i]<c[i-1]: push(i); i+=H+1;continue
            i+=1
    elif strat=="vol_compression":
        a=atr(c,hz); i=55
        while i<n-H and i-1<len(a):
            win=a[max(0,i-50):i]
            if win and a[i-1]<0.8*st.median(win) and c[i]>ema(c,50)[i]: push(i); i+=H+1;continue
            i+=1
    elif strat=="gap_fade":
        return None  # needs open; daily klines are close-only
    else:
        return None
    return idx

def measure(sym,strat,hz):
    c=bars_for(sym,hz)
    res={"cell":f"{sym}/{strat}/{hz}","symbol":sym,"strategy":strat,"horizon":hz}
    if not c:
        res.update({"verdict":"BLOCKED_NO_DATA","bars":0,"reason":f"no {hz} bars for {sym} in repo"}); return res
    res["bars"]=len(c)
    idx=signals(c,strat,hz)
    if idx is None:
        res.update({"verdict":"BLOCKED_NO_DATA","bars":len(c),"reason":"strategy needs open/high/low not in source"}); return res
    H=HOLD[hz]; trades=[]
    for i in idx:
        xi=min(i+H,len(c)-1); trades.append((c[xi]/c[i]-1)*1e4-COST)
    n=len(trades); res["n"]=n; res["cost_round_turn_bp"]=COST; res["hold_bars"]=H
    if n==0:
        res.update({"verdict":"KILLED","reason":"n=0"}); return res
    mean=st.mean(trades); rng=random.Random(7)
    bm=sorted(sum(trades[rng.randrange(n)] for _ in range(n))/n for _ in range(3000))
    ci=[round(bm[75],3),round(bm[2924],3)]
    obs=abs(mean);cnt=0
    for _ in range(3000):
        if abs(sum(trades[j]*(1 if rng.random()<.5 else -1) for j in range(n))/n)>=obs:cnt+=1
    p=(cnt+1)/3001; dsr=None
    try:
        import sys;sys.path.insert(0,".")
        from alpha_engine.audit3_tribunal import deflated_sharpe
        d=deflated_sharpe([t/1e4 for t in trades],N_TRIALS);dsr=round(d["dsr"],4) if d else None
    except Exception: pass
    kill=(n<30) or (ci[0]<=0<=ci[1]) or (p>0.05)
    res.update({"net_mean_bp":round(mean,3),"ci95_bp":ci,"permutation_p":round(p,4),"dsr":dsr,
                "dsr_n_trials":N_TRIALS,"verdict":"KILLED" if kill else "DONE"})
    return res

def main():
    sym,strat,hz=sys.argv[1:4]
    r=measure(sym,strat,hz)
    r["git_sha"]=subprocess.run(["git","rev-parse","HEAD"],capture_output=True,text=True).stdout.strip()
    r["generated_at"]=datetime.now(timezone.utc).isoformat()
    Path(f"results/cells/{sym}_{strat}_{hz}.json").parent.mkdir(parents=True,exist_ok=True)
    Path(f"results/cells/{sym}_{strat}_{hz}.json").write_text(json.dumps(r,indent=2)+"\n")
    print(json.dumps({k:r.get(k) for k in ("cell","bars","n","net_mean_bp","ci95_bp","permutation_p","dsr","verdict")}))

if __name__=="__main__": main()
