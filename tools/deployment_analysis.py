#!/usr/bin/env python3
"""deployment_analysis.py — practical questions for a real investor, on real data.

R1 DCA vs lump sum; R2 sequence-of-returns (worst/best 12-mo windows); R3 drawdown recovery;
R15 fee compounding over 30y; R23 drawdown frequency. Source: market_prices.csv (2021-11-15..2026-11-13).
Buying analysis (beta), not an edge claim.
"""
import csv, json, math, statistics as st
from pathlib import Path

SRC="2026-11-15_AM_profitability-plan/copilot-financial-review/market_prices.csv"
MER={"SPY_adj":0.000945,"BND_adj":0.0003,"SGOV_adj":0.0009,"VTI_adj":0.0003}
ANN=252

def load():
    rows=list(csv.DictReader(open(SRC))); cols=[c for c in rows[0] if c.endswith("_adj")]
    ser={c:[] for c in cols}
    for r in rows:
        try: vals={c:float(r[c]) for c in cols}
        except: continue
        for c in cols: ser[c].append(vals[c])
    ret={c:[ser[c][i]/ser[c][i-1]-1 for i in range(1,len(ser[c]))] for c in cols}
    return ret

def monthly_rebalance(ret,w):
    n=min(len(ret[c]) for c in w); sleeve={c:w[c] for c in w}; prev=1.0; out=[]
    for i in range(n):
        for c in w: sleeve[c]*=(1+ret[c][i])
        tot=sum(sleeve.values()); out.append(tot/prev-1); prev=tot
        if (i+1)%21==0:
            for c in w: sleeve[c]=w[c]*tot
    return out

def grow(ret, fee_ann=0.0):
    v=1.0
    for x in ret: v*=(1+x-fee_ann/ANN)
    return v

def main():
    ret=load()
    spy=ret["SPY_adj"]; p6040=monthly_rebalance(ret,{"SPY_adj":0.6,"BND_adj":0.4})
    out={"generated_at":__import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
         "note":"buying/beta analysis; past 5y; not advice","R1_dca_vs_lumpsum":{},"R2_sequence":{},"R3_recovery":{},"R15_fees":{},"R23_dd_freq":{}}
    # R1: DCA (12 equal monthly tranches then hold) vs lump sum, for SPY and 60/40
    for name,r,mer in (("SPY",spy,MER["SPY_adj"]),("60/40",p6040,0.6*MER["SPY_adj"]+0.4*MER["BND_adj"])):
        lump=10000*grow(r,mer)                          # invest 10k at start
        # DCA: 10000/12 each ~21 trading days for 12 months, rest held
        months=252; tranche=10000/12; dca=0.0
        for k in range(12):
            start=k*21
            sub=r[start:]
            dca+=tranche*grow(sub,mer)
        out["R1_dca_vs_lumpsum"][name]={"lump_final":round(lump,2),"dca_final":round(dca,2),
            "lump_more_pct":round((lump/dca-1)*100,2)}
        print(f"R1 {name}: lump ${lump:,.0f} vs DCA ${dca:,.0f} -> lump {(lump/dca-1)*100:+.1f}% vs DCA")
    # R2: worst/best rolling 252-day returns for SPY
    roll=[grow(spy[i:i+252],MER["SPY_adj"])-1 for i in range(0,len(spy)-252)]
    out["R2_sequence"]={"n_windows":len(roll),"worst_12mo_pct":round(min(roll)*100,2),
        "best_12mo_pct":round(max(roll)*100,2),"median_12mo_pct":round(st.median(roll)*100,2)}
    print(f"R2 SPY rolling 12mo: worst {min(roll)*100:.1f}%, best {max(roll)*100:.1f}%, median {st.median(roll)*100:.1f}%")
    # R3: drawdown recovery on SPY price level (clean)
    import csv as _csv
    _rows=list(_csv.DictReader(open(SRC))); _px=[float(r['SPY_adj']) for r in _rows]; _dt=[r['date'] for r in _rows]
    peak=_px[0]; peak_i=0; mdd=0; trough_i=0; peak_at_trough=0
    for i,p in enumerate(_px):
        if p>peak: peak=p; peak_i=i
        if p/peak-1<mdd: mdd=p/peak-1; trough_i=i; peak_at_trough=peak_i
    rec=None
    for i in range(trough_i,len(_px)):
        if _px[i]>=_px[peak_at_trough]: rec=i; break
    out["R3_recovery"]={"max_dd_pct":round(mdd*100,2),"peak_date":_dt[peak_at_trough],"trough_date":_dt[trough_i],
        "recovered_date":_dt[rec] if rec else None,
        "td_trough_to_recovery":(rec-trough_i) if rec else None,"td_peak_to_recovery":(rec-peak_at_trough) if rec else None}
    print(f"R3 SPY maxDD {mdd*100:.1f}% {out['R3_recovery']['peak_date']}->{out['R3_recovery']['trough_date']}, recovered {out['R3_recovery']['recovered_date']} ({out['R3_recovery']['td_trough_to_recovery']} td after trough)")
    # R15: fee compounding 30y, 7% gross, per $100k
    for fee in (0.0003,0.005,0.018):
        v=100000*(1+0.07-fee)**30
        out["R15_fees"][f"{fee*100:.2f}%"]=round(v,0)
        print(f"R15 fee {fee*100:.2f}%: 30y -> ${v:,.0f} per $100k")
    # R23: how often rolling 12m drawdown > 20%
    ddcount=sum(1 for i in range(len(spy)-252) if (grow(spy[i:i+252],0)-1) < -0.2)
    out["R23_dd_freq"]={"rolling_12mo_windows_below_-20pct":ddcount,"of":len(roll)}
    print(f"R23 rolling 12mo windows < -20%: {ddcount}/{len(roll)}")
    Path("reports/deployment_analysis.json").write_text(json.dumps(out,indent=2)+"\n")
    print("wrote reports/deployment_analysis.json")

if __name__=="__main__": main()
