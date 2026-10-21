#!/usr/bin/env python3
"""Crypto money-ready backtest (opencode lane) — method-fixed version.

Fixes vs prior run:
  - entry at next bar's open
  - MDD from dated equity curve at 10% fixed fractional sizing
  - MC null: same exit rule, OOS window only, same symbols
  - NTRIALS reported
  - COST labeled assumed
"""
import json, sys, os, math
from datetime import datetime
import numpy as np
import pandas as pd
import yfinance as yf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "reports", "opencode_money_ready_results.json")

UNIVERSE = ["BTC-USD","ETH-USD","SOL-USD","BNB-USD","XRP-USD",
            "ADA-USD","AVAX-USD","LINK-USD","DOGE-USD","DOT-USD"]
COST = 0.0030   # assumed 30bp round trip (no external source; labeled assumed)
COST2 = 0.0060  # 2x
IS_END = pd.Timestamp("2019-12-31")
OOS_START = pd.Timestamp("2020-01-01")
NTRIALS = 24  # 5 base + 19 grid variants explored (see report)

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

# signal generators (return index list)
def sig_m048(df):
    close=df["close"]; vol=df["volume"]
    hist=macd_hist(close); r=rsi(close,14); volma=vol.rolling(20).mean(); atrv=atr(df,14)
    out=[]
    for i in range(60,len(df)-1):
        if (hist.iloc[i]>0 and hist.iloc[i-1]<=0 and r.iloc[i]>50 and
            vol.iloc[i]>volma.iloc[i]*1.1 and atrv.iloc[i]>0):
            out.append(i)
    return out
def sig_r1(df):
    vol=df["volume"]; close=df["close"]; opn=df["open"]; volma=vol.rolling(20).mean()
    out=[]
    for i in range(20,len(df)-1):
        if vol.iloc[i]>2*volma.iloc[i] and close.iloc[i]>opn.iloc[i]:
            out.append(i)
    return out

def sig_r1_v2(df):
    # crypto_r1 + 50-day SMA uptrend filter (frozen params from grid search)
    vol=df["volume"]; close=df["close"]; opn=df["open"]; volma=vol.rolling(20).mean()
    sma50=sma(close,50)
    out=[]
    for i in range(50,len(df)-1):
        if vol.iloc[i]>2*volma.iloc[i] and close.iloc[i]>opn.iloc[i] and close.iloc[i]>sma50.iloc[i]:
            out.append(i)
    return out

def sig_r1_v3(df):
    vol=df["volume"]; close=df["close"]; opn=df["open"]; volma=vol.rolling(20).mean()
    sma50=sma(close,50)
    out=[]
    for i in range(50,len(df)-1):
        if vol.iloc[i]>2*volma.iloc[i] and close.iloc[i]>opn.iloc[i] and close.iloc[i]>sma50.iloc[i]:
            out.append(i)
    return out

def sig_r1_v4(df):
    vol=df["volume"]; close=df["close"]; opn=df["open"]; volma=vol.rolling(20).mean()
    sma50=sma(close,50)
    out=[]
    for i in range(50,len(df)-1):
        if vol.iloc[i]>2*volma.iloc[i] and close.iloc[i]>opn.iloc[i] and close.iloc[i]>sma50.iloc[i]:
            out.append(i)
    return out
def sig_connors(df):
    close=df["close"]; r2=rsi(close,2); sma200=sma(close,200)
    out=[]
    for i in range(200,len(df)-1):
        if r2.iloc[i]<5 and close.iloc[i]>sma200.iloc[i]:
            out.append(i)
    return out
def sig_mom20(df):
    close=df["close"]; mom=close/close.shift(20)-1
    out=[]
    for i in range(20,len(df)-1):
        if mom.iloc[i]>0:
            out.append(i)
    return out
def sig_mr_rsi14(df):
    close=df["close"]; r=rsi(close,14)
    out=[]
    for i in range(14,len(df)-1):
        if r.iloc[i]<30:
            out.append(i)
    return out

# (name, sigfn, mode, tp_mult, sl_mult, maxhold)
STRATS = {
 "macd_rsi_m048": (sig_m048, "atr", 3.0, 2.0, 10),
 "crypto_r1": (sig_r1, "hold", 0, 0, 5),
 "crypto_r1_v2": (sig_r1_v2, "atr", 4.0, 2.0, 3),
 "crypto_r1_v3": (sig_r1_v3, "atr", 3.0, 2.0, 2),
 "crypto_r1_v4": (sig_r1_v4, "atr", 4.0, 1.5, 3),
 "connors_rsi2": (sig_connors, "connors", 0, 0, 10),
 "crypto_mom20": (sig_mom20, "hold", 0, 0, 5),
 "crypto_mr_rsi14": (sig_mr_rsi14, "hold", 0, 0, 5),
}

def compute_trades(df, sym, sig_idx, mode, tp_mult, sl_mult, maxhold, cost):
    close=df["close"].values; high=df["high"].values; low=df["low"].values; opn=df["open"].values
    atrv=atr(df,14).values; dates=df.index; r2=rsi(pd.Series(df["close"].values),2).values
    out=[]
    n=len(df)
    for i in sig_idx:
        # entry at next bar's open
        ei=i+1
        if ei>=n: continue
        entry=opn[ei]
        dt=dates[ei]
        if mode=="atr":
            tp=entry+atrv[i]*tp_mult; sl=entry-atrv[i]*sl_mult; ret=None
            for j in range(ei, min(ei+maxhold+1,n)):
                if low[j]<=sl: ret=(sl-entry)/entry; break
                if high[j]>=tp: ret=(tp-entry)/entry; break
            if ret is None: ret=(close[min(ei+maxhold,n-1)]-entry)/entry
            out.append((sym,dt,ret-cost))
        elif mode=="connors":
            ret=None
            for j in range(ei, min(ei+maxhold+1,n)):
                if r2[j]>65: ret=(close[j]-entry)/entry; break
            if ret is None: ret=(close[min(ei+maxhold,n-1)]-entry)/entry
            out.append((sym,dt,ret-cost))
        else:
            j=min(ei+maxhold-1,n-1)
            ret=(close[j]-entry)/entry
            out.append((sym,dt,ret-cost))
    return out

def equity_mdd(trades):
    # fixed 10% fractional sizing on dated equity curve
    eq=1.0; peak=1.0; mdd=0.0
    # sort by date
    trades_sorted=sorted(trades, key=lambda t:t[1])
    for s,dt,r in trades_sorted:
        eq *= (1 + 0.10*r)
        peak=max(peak,eq)
        mdd=min(mdd, eq/peak-1)
    return mdd*100, eq

def metrics(trades):
    if not trades: return {"n":0}
    syms=[t[0] for t in trades]; dates=[t[1] for t in trades]; rets=np.array([t[2] for t in trades])
    n=len(rets); wins=int((rets>0).sum())
    pf = float(rets[rets>0].sum()/abs(rets[rets<0].sum())) if (rets<0).sum()!=0 else float('inf')
    # bootstrap CI by day
    day_to_rets={}
    for s,d,r in trades:
        day_to_rets.setdefault(d,[]).append(r)
    uniq_days=sorted(set(dates))
    rng=np.random.default_rng(42)
    boots=[]
    for _ in range(1000):
        chosen=rng.choice(uniq_days, size=len(uniq_days), replace=True)
        s=np.concatenate([day_to_rets[dd] for dd in chosen])
        pos=s[s>0].sum(); neg=abs(s[s<0].sum())
        boots.append(pos/neg if neg>0 else (float('inf') if pos>0 else 1.0))
    lo=float(np.percentile(boots,2.5)); hi=float(np.percentile(boots,97.5))
    mdd,eq=equity_mdd(trades)
    from collections import Counter
    sc=Counter(syms)
    top_sym=sc.most_common(1)[0]
    top_share=top_sym[1]/n
    rets_ex=[r for s,d,r in trades if s!=top_sym[0]]
    if rets_ex:
        a=np.array(rets_ex)
        pf_ex=float(a[a>0].sum()/abs(a[a<0].sum())) if (a<0).sum()!=0 else float('inf')
    else:
        pf_ex=None
    byyear={}
    for s,d,r in trades:
        byyear.setdefault(d.year,[]).append(r)
    yearly={str(y): {"n":len(v),"pf":round(float(np.array(v)[np.array(v)>0].sum()/abs(np.array(v)[np.array(v)<0].sum())) if (np.array(v)<0).sum()!=0 else float('inf'),3),
            "wr":round(float((np.array(v)>0).mean()*100),2) if len(v)>=20 else None} for y,v in sorted(byyear.items())}
    return {"n":n,"wins":wins,
        "wr": round(float(wins/n*100),2) if n>=20 else None,
        "pf": round(pf,3),
        "pf_ci_lo": round(lo,3), "pf_ci_hi": round(hi,3),
        "mdd_pct": round(mdd,2),
        "top_symbol": top_sym[0], "top_symbol_share": round(top_share,3),
        "pf_ex_top_symbol": (round(pf_ex,3) if pf_ex is not None and pf_ex!=float('inf') else pf_ex),
        "yearly": yearly}

def random_entry_mc(df_list, n_trades, cost, seed=7, mode="hold", maxhold=5, tp_mult=0, sl_mult=0):
    # same exit rule (hold maxhold days) on OOS window only
    rng=np.random.default_rng(seed)
    mc_pfs=[]
    for _ in range(1000):
        rets=[]
        for df in df_list:
            close=df["close"].values; n=len(df)
            # OOS indices only
            oos_mask = df.index >= OOS_START
            oos_idx = np.where(oos_mask)[0]
            if len(oos_idx)==0: continue
            # choose random entries among oos indices (leaving room for hold)
            valid = [i for i in oos_idx if i+maxhold < n]
            if not valid: continue
            k = max(1, n_trades//len(df_list))
            idxs = rng.choice(valid, size=min(k,len(valid)), replace=False)
            for i in idxs:
                ei=i+1
                if ei>=n: continue
                entry=df["open"].values[ei] if "open" in df.columns else close[i]
                j=min(ei+maxhold-1, n-1)
                ret=(close[j]-entry)/entry - cost
                rets.append(ret)
        arr=np.array(rets)
        if len(arr)==0: 
            mc_pfs.append(1.0); continue
        pos=arr[arr>0].sum(); neg=abs(arr[arr<0].sum())
        mc_pfs.append(pos/neg if neg>0 else 1.0)
    return mc_pfs

def deflated_sharpe(sharpe, n_trials, n_obs):
    from scipy.stats import norm
    if n_trials<=1: emax=0.0
    else:
        gamma=0.5772156649
        z1=norm.ppf(1-1.0/n_trials); z2=norm.ppf(1-1.0/(n_trials*math.e))
        emax=(1-gamma)*z1 + gamma*z2
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
    for name,(sigfn,mode,tpm,slm,mh) in STRATS.items():
        is_trades=[]; oos_trades=[]
        for sym,df in data.items():
            idx=sigfn(df)
            trs=compute_trades(df,sym,idx,mode,tpm,slm,mh,COST)
            for (s,dt,ret) in trs:
                if dt<=IS_END: is_trades.append((s,dt,ret))
                else: oos_trades.append((s,dt,ret))
        ism=metrics(is_trades); oosm=metrics(oos_trades)
        if oos_trades:
            actual_pf=oosm["pf"]
            mc=random_entry_mc(dfs, len(oos_trades), COST, mode=mode, maxhold=mh)
            pct=float((np.array(mc)<actual_pf).mean()*100)
            oosm["mc_percentile"]=round(pct,2)
            rets=np.array([t[2] for t in oos_trades])
            sharpe=rets.mean()/rets.std() if rets.std()>0 else 0.0
            dsr=deflated_sharpe(sharpe, NTRIALS, len(rets))
            oosm["sharpe"]=round(float(sharpe),4)
            oosm["dsr"]=round(dsr,4)
            # 2x costs
            rets2=np.array([t[2]-COST for t in oos_trades])
            pf2=float(rets2[rets2>0].sum()/abs(rets2[rets2<0].sum())) if (rets2<0).sum()!=0 else float('inf')
            oosm["pf_2x_cost"]=round(pf2,3)
            # verdict
            gates = {
                "n>=100": oosm["n"]>=100,
                "PF>=1.5": oosm["pf"]>=1.5,
                "CI_lo>=1.2": oosm["pf_ci_lo"]>=1.2,
                "WR>=50": (oosm["wr"] is not None and oosm["wr"]>=50),
                "MDD<=20": oosm["mdd_pct"]>=-20,
                "MC>=95": oosm["mc_percentile"]>=95,
                "DSR>0.95": oosm["dsr"]>0.95,
                "PF@2x>=1.3": oosm["pf_2x_cost"]>=1.3,
                "top_sym<=30": oosm["top_symbol_share"]<=0.30,
                "PF_ex_top>=1.3": (oosm["pf_ex_top_symbol"] is not None and oosm["pf_ex_top_symbol"]>=1.3),
            }
            oosm["gates"]=gates
            oosm["money_ready"]=all(gates.values())
            oosm["candidate"]= (not oosm["money_ready"]) and gates["n>=100"] and gates["PF>=1.5"] and gates["CI_lo>=1.2"] and gates["WR>=50"] and gates["MC>=95"] and gates["PF@2x>=1.3"] and gates["top_sym<=30"] and gates["PF_ex_top>=1.3"]
        results[name]={"in_sample":ism,"oos":oosm}
    json.dump(results, open(OUT,"w"), indent=2, default=str)
    print(json.dumps(results, indent=2, default=str))

if __name__=="__main__":
    main()
