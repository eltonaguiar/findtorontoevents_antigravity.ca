#!/usr/bin/env python3
"""Crypto money-ready backtest (opencode lane)."""
import json, sys, os, math
from datetime import datetime
import numpy as np
import pandas as pd
import yfinance as yf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "reports", "opencode_money_ready_results.json")

UNIVERSE = ["BTC-USD","ETH-USD","SOL-USD","BNB-USD","XRP-USD",
            "ADA-USD","AVAX-USD","LINK-USD","DOGE-USD","DOT-USD"]
COST = 0.0030
IS_END = pd.Timestamp("2019-12-31")
OOS_START = pd.Timestamp("2020-01-01")
NTRIALS = 5

def fetch(sym):
    df = yf.download(sym, start="2016-01-01", progress=False, auto_adjust=True)
    if df is None or df.empty: return None
    df.columns = [c[0] if isinstance(c,tuple) else c for c in df.columns]
    df = df.rename(columns={"Open":"open","High":"high","Low":"low","Close":"close","Volume":"volume"})
    df.index = pd.to_datetime(df.index)
    return df

def rsi(close,p):
    d=close.diff(); g=d.where(d>0,0).rolling(p).mean(); l=(-d.where(d<0,0)).rolling(p).mean()
    rs=g/l; return 100-100/(1+rs)
def sma(s,p): return s.rolling(p).mean()
def macd_hist(close,f=12,sl=26,sig=9):
    ef=close.ewm(span=f,adjust=False).mean(); es=close.ewm(span=sl,adjust=False).mean()
    line=ef-es; signal=line.ewm(span=sig,adjust=False).mean(); return line-signal
def atr(df,p=14):
    tr=pd.concat([df["high"]-df["low"],(df["high"]-df["close"].shift()).abs(),(df["low"]-df["close"].shift()).abs()],axis=1).max(axis=1)
    return tr.rolling(p).mean()

def sig_m048(df):
    close=df["close"]; vol=df["volume"]
    hist=macd_hist(close); r=rsi(close,14); volma=vol.rolling(20).mean(); atrv=atr(df,14)
    out=[]
    for i in range(60,len(df)):
        if (hist.iloc[i]>0 and hist.iloc[i-1]<=0 and r.iloc[i]>50 and
            vol.iloc[i]>volma.iloc[i]*1.1 and atrv.iloc[i]>0):
            out.append(i)
    return out
def sig_r1(df):
    vol=df["volume"]; close=df["close"]; opn=df["open"]; volma=vol.rolling(20).mean()
    out=[]
    for i in range(20,len(df)):
        if vol.iloc[i]>2*volma.iloc[i] and close.iloc[i]>opn.iloc[i]:
            out.append(i)
    return out
def sig_connors(df):
    close=df["close"]; r2=rsi(close,2); sma200=sma(close,200)
    out=[]
    for i in range(200,len(df)):
        if r2.iloc[i]<5 and close.iloc[i]>sma200.iloc[i]:
            out.append(i)
    return out
def sig_mom20(df):
    close=df["close"]; mom=close/close.shift(20)-1
    out=[]
    for i in range(20,len(df)):
        if mom.iloc[i]>0:
            out.append(i)
    return out
def sig_mr_rsi14(df):
    close=df["close"]; r=rsi(close,14)
    out=[]
    for i in range(14,len(df)):
        if r.iloc[i]<30:
            out.append(i)
    return out

STRATS = {
 "macd_rsi_m048": (sig_m048, "atr"),
 "crypto_r1": (sig_r1, "hold5"),
 "connors_rsi2": (sig_connors, "connors"),
 "crypto_mom20": (sig_mom20, "hold5"),
 "crypto_mr_rsi14": (sig_mr_rsi14, "hold5"),
}

def compute_trades(df, sym, sig_idx, mode):
    close=df["close"].values; high=df["high"].values; low=df["low"].values
    atrv=atr(df,14).values; dates=df.index
    r2=rsi(pd.Series(df["close"].values),2).values
    out=[]
    n=len(df)
    for i in sig_idx:
        if i+1>=n: continue
        entry=close[i]; dt=dates[i]
        if mode=="atr":
            tp=entry+atrv[i]*3.0; sl=entry-atrv[i]*2.0; ret=None
            for j in range(i+1,min(i+11,n)):
                if low[j]<=sl: ret=(sl-entry)/entry; break
                if high[j]>=tp: ret=(tp-entry)/entry; break
            if ret is None: ret=(close[min(i+10,n-1)]-entry)/entry
            out.append((sym,dt,ret-COST))
        elif mode=="connors":
            ret=None
            for j in range(i+1,min(i+11,n)):
                if r2[j]>65: ret=(close[j]-entry)/entry; break
            if ret is None: ret=(close[min(i+10,n-1)]-entry)/entry
            out.append((sym,dt,ret-COST))
        else:
            j=min(i+5,n-1)
            ret=(close[j]-entry)/entry
            out.append((sym,dt,ret-COST))
    return out

def equity_mdd(rets):
    eq=1.0; peak=1.0; mdd=0.0
    for r in rets:
        eq*=(1+r)
        peak=max(peak,eq)
        mdd=min(mdd, eq/peak-1)
    return mdd*100, eq

def metrics(trades):
    if not trades: return {"n":0}
    syms=[t[0] for t in trades]; dates=[t[1] for t in trades]; rets=np.array([t[2] for t in trades])
    n=len(rets); wins=int((rets>0).sum())
    pf = float(rets[rets>0].sum()/abs(rets[rets<0].sum())) if (rets<0).sum()!=0 else float('inf')
    # bootstrap CI by day
    uniq_days=sorted(set(dates))
    day_to_rets={}
    for s,d,r in trades:
        day_to_rets.setdefault(d,[]).append(r)
    rng=np.random.default_rng(42)
    boots=[]
    for _ in range(1000):
        chosen=rng.choice(uniq_days, size=len(uniq_days), replace=True)
        s=np.concatenate([day_to_rets[dd] for dd in chosen])
        pos=s[s>0].sum(); neg=abs(s[s<0].sum())
        boots.append(pos/neg if neg>0 else (float('inf') if pos>0 else 1.0))
    lo=float(np.percentile(boots,2.5)); hi=float(np.percentile(boots,97.5))
    mdd,eq=equity_mdd(rets.tolist())
    # concentration
    from collections import Counter
    sc=Counter(syms)
    top_sym=sc.most_common(1)[0]
    top_sym_share=top_sym[1]/n
    # pf without top symbol
    rets_ex=[r for s,d,r in trades if s!=top_sym[0]]
    if rets_ex:
        a=np.array(rets_ex)
        pf_ex=float(a[a>0].sum()/abs(a[a<0].sum())) if (a<0).sum()!=0 else float('inf')
    else:
        pf_ex=None
    # per year
    byyear={}
    for s,d,r in trades:
        byyear.setdefault(d.year,[]).append(r)
    yearly={str(y): {"n":len(v),"pf":round(float(np.array(v)[np.array(v)>0].sum()/abs(np.array(v)[np.array(v)<0].sum())) if (np.array(v)<0).sum()!=0 else float('inf'),3),
            "wr":round(float((np.array(v)>0).mean()*100),2)} for y,v in sorted(byyear.items())}
    return {
        "n":n, "wins":wins,
        "wr": round(float(wins/n*100),2) if n>=20 else None,
        "pf": round(pf,3),
        "pf_ci_lo": round(lo,3), "pf_ci_hi": round(hi,3),
        "mdd_pct": round(mdd,2),
        "top_symbol": top_sym[0], "top_symbol_share": round(top_sym_share,3),
        "pf_ex_top_symbol": (round(pf_ex,3) if pf_ex is not None and pf_ex!=float('inf') else pf_ex),
        "yearly": yearly,
    }

def random_entry_mc(df_list, n_trades, cost, seed=7):
    # random entry indices across all data, n_trades count, 5-day hold
    rng=np.random.default_rng(seed)
    all_rets=[]
    for _ in range(1000):
        rets=[]
        for df in df_list:
            close=df["close"].values; n=len(df)
            idxs=rng.integers(5, n-6, size=max(1,n_trades//len(df_list)))
            for i in idxs:
                j=min(i+5,n-1)
                rets.append((close[j]-close[i])/close[i]-cost)
        arr=np.array(rets)
        pos=arr[arr>0].sum(); neg=abs(arr[arr<0].sum())
        all_rets.append(pos/neg if neg>0 else 1.0)
    return all_rets

def deflated_sharpe(sharpe, n_trials, n_obs):
    # Bailey & Lopez de Prado DSR
    # z = (sharpe - E[max SR under null]) / sqrt(Var)
    # approximate: E[max] = (1-gamma)*Phi^{-1}(1-1/n) + gamma*Phi^{-1}(1-1/(n*e))
    from scipy.stats import norm
    if n_trials<=1: emax=0.0
    else:
        gamma=0.5772156649
        z1=norm.ppf(1-1.0/n_trials); z2=norm.ppf(1-1.0/(n_trials*math.e))
        emax=(1-gamma)*z1 + gamma*z2
    # variance of sharpe under null ~ 1/(n_obs-1)
    var=1.0/(n_obs-1) if n_obs>1 else 1.0
    z=(sharpe-emax)/math.sqrt(var)
    return float(norm.cdf(z))

def main():
    data={}
    for sym in UNIVERSE:
        df=fetch(sym)
        if df is not None and len(df)>250:
            data[sym]=df
            print(f"loaded {sym}: {len(df)} bars", file=sys.stderr)
    dfs=list(data.values())
    results={}
    for name,(sigfn,mode) in STRATS.items():
        is_trades=[]; oos_trades=[]
        for sym,df in data.items():
            idx=sigfn(df)
            trs=compute_trades(df,sym,idx,mode)
            for (s,dt,ret) in trs:
                if dt<=IS_END: is_trades.append((s,dt,ret))
                else: oos_trades.append((s,dt,ret))
        ism=metrics(is_trades); oosm=metrics(oos_trades)
        # MC percentile on OOS
        if oos_trades:
            actual_pf=oosm["pf"]
            mc=random_entry_mc(dfs, len(oos_trades), COST)
            pct=float((np.array(mc)<actual_pf).mean()*100)
            oosm["mc_percentile"]=round(pct,2)
            # DSR
            rets=np.array([t[2] for t in oos_trades])
            sharpe=rets.mean()/rets.std() if rets.std()>0 else 0.0
            # annualize-ish by trade count (no time scaling); use raw sharpe
            dsr=deflated_sharpe(sharpe, NTRIALS, len(rets))
            oosm["sharpe"]=round(float(sharpe),4)
            oosm["dsr"]=round(dsr,4)
            # 2x costs: recompute pf with double cost
            rets2=np.array([t[2]-COST for t in oos_trades])  # already had COST; subtract extra COST
            # actually recompute from raw: we stored net; approximate by subtracting COST again
            pf2 = float(rets2[rets2>0].sum()/abs(rets2[rets2<0].sum())) if (rets2<0).sum()!=0 else float('inf')
            oosm["pf_2x_cost"]=round(pf2,3)
        results[name]={"in_sample":ism,"oos":oosm}
    json.dump(results, open(OUT,"w"), indent=2, default=str)
    print(json.dumps(results, indent=2, default=str))

if __name__=="__main__":
    main()
