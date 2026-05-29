#!/usr/bin/env python3
"""
backtest_swarm_strategies.py — MULTI-CLASS, no-lookahead backtest of the strategies
the ParallelSwarm dry-run generated (one per asset class).

  CRYPTO (deepseek): Momentum Breakout + Volume   -> engine_momentum_breakout
  EQUITY (groq)    : BB Mean-Reversion + RSI<30    -> engine_bb_mean_reversion(use_rsi=True)
  FOREX  (groq)    : BB Mean-Reversion (long+short)-> engine_bb_mean_reversion(allow_short=True)

Data (free, no key): CRYPTO=Binance daily klines; EQUITY/FOREX=yfinance daily ~3y.
Discipline: multi-symbol per class (no single-symbol artifact); signal on bar t ->
enter at t+1 open (no lookahead); intrabar stop/TP via high/low; 20bp round-trip cost.

Run: python3 tools/backtest_swarm_strategies.py
"""
from __future__ import annotations
import json, sys, urllib.request

FEE_SLIP = 0.0010  # per side
UNIVERSE = {
    "CRYPTO": (["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT"], "momentum"),
    "EQUITY": (["SPY","AAPL","MSFT","NVDA","AMZN"], "mr_rsi"),
    "FOREX":  (["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X"], "mr_short"),
}
INCUMBENT = {"CRYPTO": "PF 3.23 / WR 17% / n=30",
             "EQUITY": "none n>=20 (best any-n PF 0.28)",
             "FOREX":  "none n>=20 (best any-n PF 0.50)"}

# ---------- data ----------
def fetch_crypto(sym):
    for host in ("https://api.binance.com","https://api1.binance.com","https://api2.binance.com"):
        try:
            with urllib.request.urlopen(f"{host}/api/v3/klines?symbol={sym}&interval=1d&limit=1000", timeout=20) as r:
                k = json.load(r)
            return [(float(x[1]),float(x[2]),float(x[3]),float(x[4]),float(x[5])) for x in k]
        except Exception: continue
    return None

def fetch_yf(sym):
    try:
        import yfinance as yf
        df = yf.Ticker(sym).history(period="3y", interval="1d", auto_adjust=True)
        if df is None or df.empty: return None
        return [(float(o),float(h),float(l),float(c),float(v or 0))
                for o,h,l,c,v in zip(df["Open"],df["High"],df["Low"],df["Close"],df["Volume"])]
    except Exception as e:
        print(f"    yf err {sym}: {e}", file=sys.stderr); return None

# ---------- indicators ----------
def sma(v,p,i): return sum(v[i-p+1:i+1])/p if i>=p-1 else None
def std(v,p,i,m): return (sum((x-m)**2 for x in v[i-p+1:i+1])/p)**0.5 if i>=p-1 else None
def atr_series(h,l,c,p):
    n=len(c); tr=[0.0]*n
    for i in range(1,n): tr[i]=max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1]))
    a=[None]*n
    if n>p:
        a[p]=sum(tr[1:p+1])/p
        for i in range(p+1,n): a[i]=(a[i-1]*(p-1)+tr[i])/p
    return a
def adx_series(h,l,c,p):
    n=len(c); pdm=[0.0]*n; mdm=[0.0]*n; tr=[0.0]*n
    for i in range(1,n):
        up=h[i]-h[i-1]; dn=l[i-1]-l[i]
        pdm[i]=up if (up>dn and up>0) else 0.0; mdm[i]=dn if (dn>up and dn>0) else 0.0
        tr[i]=max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1]))
    adx=[None]*n
    if n<2*p+1: return adx
    atr=sum(tr[1:p+1]); apdm=sum(pdm[1:p+1]); amdm=sum(mdm[1:p+1]); hist=[]
    for i in range(p+1,n):
        atr=atr-atr/p+tr[i]; apdm=apdm-apdm/p+pdm[i]; amdm=amdm-amdm/p+mdm[i]
        if atr==0: continue
        pdi=100*apdm/atr; mdi=100*amdm/atr
        dx=100*abs(pdi-mdi)/(pdi+mdi) if (pdi+mdi) else 0.0
        hist.append((i,dx))
        if len(hist)==p: adx[i]=sum(d for _,d in hist)/p
        elif len(hist)>p: adx[i]=(adx[hist[-2][0]]*(p-1)+dx)/p
    return adx
def rsi_series(c,p):
    n=len(c); r=[None]*n
    if n<=p: return r
    g=l=0.0
    for i in range(1,p+1):
        d=c[i]-c[i-1]; g+=max(d,0); l+=max(-d,0)
    ag=g/p; al=l/p
    r[p]=100-100/(1+(ag/al if al else 1e9))
    for i in range(p+1,n):
        d=c[i]-c[i-1]; ag=(ag*(p-1)+max(d,0))/p; al=(al*(p-1)+max(-d,0))/p
        r[i]=100-100/(1+(ag/al if al else 1e9))
    return r

# ---------- engines (long-only unless allow_short) ----------
def engine_momentum_breakout(bars):
    o=[b[0] for b in bars]; h=[b[1] for b in bars]; l=[b[2] for b in bars]; c=[b[3] for b in bars]; v=[b[4] for b in bars]
    n=len(c); atr=atr_series(h,l,c,14); adx=adx_series(h,l,c,14); R=[]
    pos=False; entry=hi=tp=0.0
    for t in range(21,n-1):
        if pos:
            hi=max(hi,c[t]); ae=atr[t] or 0; stop=hi-2*ae; px=None
            if l[t]<=stop: px=stop
            elif h[t]>=tp: px=tp
            if px is not None: R.append(px/entry-1-2*FEE_SLIP); pos=False
            continue
        m=sma(c,20,t); sd=std(c,20,t,m) if m else None; vm=sma(v,20,t)
        if None in (m,sd,vm) or atr[t] is None or adx[t] is None: continue
        if c[t]>m and c[t]>m+2*sd and v[t]>1.5*vm and (sma(c,20,t) or 0)>(sma(c,20,t-1) or 1e9) and adx[t]>25:
            entry=o[t+1]; hi=c[t]; tp=entry+3*atr[t]; pos=True
    return R

def engine_bb_mean_reversion(bars, use_rsi=False, allow_short=False):
    o=[b[0] for b in bars]; h=[b[1] for b in bars]; l=[b[2] for b in bars]; c=[b[3] for b in bars]
    n=len(c); atr=atr_series(h,l,c,14); rsi=rsi_series(c,14) if use_rsi else [50]*n; R=[]
    pos=0; entry=0.0  # pos: 0 flat, 1 long, -1 short
    for t in range(21,n-1):
        m=sma(c,20,t); sd=std(c,20,t,m) if m else None; ae=atr[t] or 0
        if None in (m,sd) or ae==0: continue
        lower=m-2*sd; upper=m+2*sd
        if pos==1:
            stop=entry-2*ae; px=None
            if l[t]<=stop: px=stop
            elif c[t]>=m: px=c[t]      # revert to mean
            if px is not None: R.append(px/entry-1-2*FEE_SLIP); pos=0
            continue
        if pos==-1:
            stop=entry+2*ae; px=None
            if h[t]>=stop: px=stop
            elif c[t]<=m: px=c[t]
            if px is not None: R.append(entry/px-1-2*FEE_SLIP); pos=0
            continue
        long_ok = c[t]<=lower and (rsi[t] is not None and rsi[t]<30 if use_rsi else True)
        short_ok = allow_short and c[t]>=upper and (rsi[t] is not None and rsi[t]>70 if use_rsi else True)
        if long_ok: entry=o[t+1]; pos=1
        elif short_ok: entry=o[t+1]; pos=-1
    return R

def metrics(R):
    n=len(R)
    if not n: return dict(n=0,wr=0,pf=0,avg=0,mdd=0,cum=0)
    w=[r for r in R if r>0]; ls=[r for r in R if r<=0]
    gp=sum(w); gl=abs(sum(ls)); pf=gp/gl if gl else float('inf')
    eq=1.0; pk=1.0; mdd=0.0
    for r in R: eq*=1+r; pk=max(pk,eq); mdd=max(mdd,(pk-eq)/pk)
    return dict(n=n,wr=len(w)/n,pf=pf,avg=sum(R)/n,mdd=mdd,cum=eq-1)

def run_class(cls, syms, engine):
    fetch = fetch_crypto if cls=="CRYPTO" else fetch_yf
    allR=[]; ok=0
    for s in syms:
        bars=fetch(s)
        if not bars or len(bars)<60: print(f"    {s}: no data", file=sys.stderr); continue
        ok+=1
        if engine=="momentum": R=engine_momentum_breakout(bars)
        elif engine=="mr_rsi": R=engine_bb_mean_reversion(bars,use_rsi=True)
        else: R=engine_bb_mean_reversion(bars,allow_short=True)
        m=metrics(R)
        print(f"    {s:10} n={m['n']:3} WR={m['wr']*100:5.1f}% PF={m['pf']:6.2f} avg={m['avg']*100:+5.2f}% MDD={m['mdd']*100:4.1f}%")
        allR+=R
    return metrics(allR), ok

def main():
    print("=== ParallelSwarm Dry Run 2 — multi-class backtest (real data, no-lookahead, 20bp round-trip) ===")
    summary={}
    for cls,(syms,engine) in UNIVERSE.items():
        print(f"\n[{cls}]  engine={engine}  incumbent={INCUMBENT[cls]}")
        m,ok = run_class(cls,syms,engine)
        summary[cls]=m
        t2 = "PASS" if (m['pf']>=1.5 and m['wr']>=0.50 and m['n']>=100) else "FAIL"
        print(f"  POOLED({ok} syms): n={m['n']} WR={m['wr']*100:.1f}% PF={m['pf']:.2f} "
              f"avg={m['avg']*100:+.2f}% MDD={m['mdd']*100:.1f}% cum={m['cum']*100:+.1f}%  Tier-2:{t2}")
    print("\n=== VERDICT ===")
    for cls,m in summary.items():
        print(f"  {cls:8} PF={m['pf']:.2f} WR={m['wr']*100:.0f}% n={m['n']}  "
              f"{'clears Tier-2' if (m['pf']>=1.5 and m['wr']>=0.5 and m['n']>=100) else 'below Tier-2 (paper-only / promising-not-valid)'}")
    print("  (no fabrication — every figure computed from the fetched OHLCV above)")

if __name__ == "__main__":
    main()
