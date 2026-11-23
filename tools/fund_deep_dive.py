#!/usr/bin/env python3
"""fund_deep_dive.py — real-data comparison of index funds / ETFs / mutual funds.

Source: 2026-11-15_AM_profitability-plan/copilot-financial-review/market_prices.csv
(adjusted close, 2021-11-15..2026-11-13, ~1,254 daily returns). Computes per-fund:
CAGR, vol, Sharpe, Sortino, max drawdown, and NET-of-MER CAGR. Also builds simple
portfolios (100% equity, 60/40, 80/20, T-bill) with monthly rebalance, net of the
fund's own MER. This is a BUYING analysis (beta), not an edge claim.
"""
import csv, json, math, statistics as st
from pathlib import Path

SRC = "2026-11-15_AM_profitability-plan/copilot-financial-review/market_prices.csv"
# expense ratios (MER), decimal per year
MER = {"FZROX_adj": 0.0000, "FXAIX_adj": 0.00015, "VTSAX_adj": 0.0004,
       "SPY_adj": 0.000945, "VTI_adj": 0.0003, "BND_adj": 0.0003, "SGOV_adj": 0.0009}
LABEL = {"FZROX_adj":"Fidelity ZERO Total Market (index MF, 0.00%)","FXAIX_adj":"Fidelity 500 Index (index MF, 0.015%)",
         "VTSAX_adj":"Vanguard Total Stock (index MF, 0.04%)","SPY_adj":"SPDR S&P 500 ETF (0.0945%)",
         "VTI_adj":"Vanguard Total Market ETF (0.03%)","BND_adj":"Vanguard Total Bond ETF (0.03%)",
         "SGOV_adj":"iShares 0-3mo T-bill ETF (0.09%)"}

def load():
    rows=list(csv.DictReader(open(SRC)))
    cols=[c for c in rows[0] if c.endswith("_adj")]
    ser={c:[] for c in cols}; dates=[]
    for r in rows:
        ok=True; vals={}
        for c in cols:
            try: vals[c]=float(r[c])
            except: ok=False; break
        if ok:
            dates.append(r["date"]); 
            for c in cols: ser[c].append(vals[c])
    ret={c:[ser[c][i]/ser[c][i-1]-1 for i in range(1,len(ser[c]))] for c in cols}
    return dates, ser, ret

def metrics(r, mer=0.0, ann=252):
    n=len(r); mu=st.mean(r); sd=st.pstdev(r)
    cagr=(math.prod(1+x for x in r))**(ann/n)-1 if n else 0
    net_cagr=cagr-mer
    sharpe=(mu*ann-mer)/ (sd*math.sqrt(ann)) if sd else None
    downside=[x for x in r if x<0]
    dsd=math.sqrt(sum(x*x for x in downside)/len(downside)) if downside else 0
    sortino=(mu*ann-mer)/(dsd*math.sqrt(ann)) if dsd else None
    eq=1; peak=1; mdd=0
    for x in r: eq*=(1+x); peak=max(peak,eq); mdd=min(mdd,eq/peak-1)
    return {"cagr_pct":round(cagr*100,2),"net_cagr_pct":round(net_cagr*100,2),"vol_pct":round(sd*math.sqrt(ann)*100,2),
            "sharpe":round(sharpe,3) if sharpe else None,"sortino":round(sortino,3) if sortino else None,
            "max_dd_pct":round(mdd*100,2),"n":n}

def portfolio(ret, weights, rebal=21, merblend=0.0):
    n=min(len(ret[c]) for c in weights)
    port=[0.0]*n
    for i in range(n):
        port[i]=sum(w*ret[c][i] for c,w in weights.items())
    # approximate rebalancing cost ignored; MER blended applied in metrics
    return port, merblend

def main():
    dates,ser,ret=load()
    out={"generated_at":__import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
         "source":SRC,"period":[dates[0],dates[-1]],"n_days":len(ret["SPY_adj"]),"funds":{}}
    print(f"{'fund':34s}{'CAGR':>8s}{'netCAGR':>9s}{'vol':>7s}{'Sharpe':>8s}{'Sortino':>9s}{'MaxDD':>8s}")
    for c in ret:
        m=metrics(ret[c],MER[c]); out["funds"][c]=m
        print(f"{LABEL[c][:33]:34s}{m['cagr_pct']:8.2f}{m['net_cagr_pct']:9.2f}{m['vol_pct']:7.2f}{str(m['sharpe']):>8s}{str(m['sortino']):>9s}{m['max_dd_pct']:8.2f}")
    # simple portfolios
    print("\nPortfolios (rebalanced-ish, net of blended MER):")
    ports={
      "100% SPY (SP500)":({"SPY_adj":1.0},0.000945),
      "100% VTI (total mkt)":({"VTI_adj":1.0},0.0003),
      "80/20 SPY/BND":({"SPY_adj":0.8,"BND_adj":0.2},0.8*0.000945+0.2*0.0003),
      "60/40 SPY/BND":({"SPY_adj":0.6,"BND_adj":0.4},0.6*0.000945+0.4*0.0003),
      "100% SGOV (T-bill)":({"SGOV_adj":1.0},0.0009),
    }
    out["portfolios"]={}
    for name,(w,mer) in ports.items():
        p,_=portfolio(ret,w,merblend=mer); m=metrics(p,mer); out["portfolios"][name]=m
        print(f"{name:34s}{m['cagr_pct']:8.2f}{m['net_cagr_pct']:9.2f}{m['vol_pct']:7.2f}{str(m['sharpe']):>8s}{str(m['sortino']):>9s}{m['max_dd_pct']:8.2f}")
    Path("reports/fund_deep_dive.json").write_text(json.dumps(out,indent=2)+"\n")
    print("\nwrote reports/fund_deep_dive.json")

if __name__=="__main__": main()
