#!/usr/bin/env python3
"""fund_deep_dive.py — index fund / ETF / mutual fund comparison, CORRECTED per subq review.

Fixes vs v1:
  * Sharpe/Sortino now EXCESS OF CASH (SGOV daily return = risk-free), not (ret-fee)/vol.
  * SGOV relabelled: excess-of-cash Sharpe is ~undefined/0 by construction (it IS cash).
  * True rebalancing every 21 trading days for multi-fund portfolios (sleeve-value drift +
    reset keyed to BAR COUNT, not calendar month start -- labelled accordingly),
    plus the old daily-rebalanced number for contrast.
  * Block-bootstrap (21-day blocks, 2000 draws) 5-95% CI on CAGR.
  * Split sample: first ~3y vs last ~2y.
  * FXAIX vs SPY arithmetic stated honestly: the fee gap UNDER-predicts (7.95bp/yr of fees vs
    +16.7bp/yr observed), and the excess is unattributed. Magnitude stays within noise.
Source: 2026-11-15_AM_profitability-plan/copilot-financial-review/market_prices.csv
"""
import csv, json, math, random, statistics as st
from pathlib import Path

SRC = "2026-11-15_AM_profitability-plan/copilot-financial-review/market_prices.csv"
MER = {"FZROX_adj":0.0000,"FXAIX_adj":0.00015,"VTSAX_adj":0.0004,"SPY_adj":0.000945,
       "VTI_adj":0.0003,"BND_adj":0.0003,"SGOV_adj":0.0009}
LABEL = {"FZROX_adj":"Fidelity ZERO Total Market (index MF, 0.00%)","FXAIX_adj":"Fidelity 500 Index (index MF, 0.015%)",
         "VTSAX_adj":"Vanguard Total Stock (index MF, 0.04%)","SPY_adj":"SPDR S&P 500 ETF (0.0945%)",
         "VTI_adj":"Vanguard Total Market ETF (0.03%)","BND_adj":"Vanguard Total Bond ETF (0.03%)",
         "SGOV_adj":"iShares 0-3mo T-bill ETF (0.09%)"}
ANN=252

def load():
    rows=list(csv.DictReader(open(SRC))); cols=[c for c in rows[0] if c.endswith("_adj")]
    dates=[]; ser={c:[] for c in cols}
    for r in rows:
        try: vals={c:float(r[c]) for c in cols}
        except: continue
        dates.append(r["date"])
        for c in cols: ser[c].append(vals[c])
    ret={c:[ser[c][i]/ser[c][i-1]-1 for i in range(1,len(ser[c]))] for c in cols}
    return dates[1:], ret

def maxdd(r):
    eq=1; peak=1; mdd=0
    for x in r: eq*=(1+x); peak=max(peak,eq); mdd=min(mdd,eq/peak-1)
    return mdd

def cagr(r):
    n=len(r); return (math.prod(1+x for x in r))**(ANN/n)-1 if n else 0.0

def excess_metrics(r, rf, mer):
    n=min(len(r),len(rf)); ex=[r[i]-rf[i] for i in range(n)]  # daily excess-of-cash
    mu=st.mean(ex); sd=st.pstdev(ex)
    sharpe=mu/sd*math.sqrt(ANN) if sd else None
    # Downside deviation divides by n, not by the count of negative days. Dividing by
    # len(neg) inflates dsd by 1/sqrt(share of negatives) and understates Sortino by ~30%
    # (0.501 vs 0.722 for FXAIX on the 2021-2026 sample).
    neg=[x for x in ex if x<0]; dsd=math.sqrt(sum(x*x for x in neg)/len(ex)) if neg else 0
    sortino=mu/dsd*math.sqrt(ANN) if dsd else None
    return {"sharpe_excess":round(sharpe,3) if sharpe is not None else None,
            "sortino_excess":round(sortino,3) if sortino is not None else None}

def bootstrap_cagr_ci(r, blocks=21, draws=2000, seed=7):
    n=len(r)
    if n < blocks*3: return None
    rng=random.Random(seed)
    nb=(n+blocks-1)//blocks
    out=[]
    for _ in range(draws):
        seq=[]
        for _ in range(nb):
            s=rng.randrange(0, n-blocks+1)
            seq.extend(r[s:s+blocks])
        seq=seq[:n]
        out.append(cagr(seq))
    out.sort()
    return [round(out[int(0.05*draws)]*100,2), round(out[int(0.95*draws)-1]*100,2)]

def monthly_rebalance(ret, weights, dates):
    """True monthly-rebalance: sleeve values drift, reset to target at month start."""
    n=min(len(ret[c]) for c in weights)
    sleeve={c:weights[c] for c in weights}
    prev_total=1.0; out=[]
    for i in range(n):
        for c in weights: sleeve[c]*=(1+ret[c][i])
        total=sum(sleeve.values())
        out.append(total/prev_total-1); prev_total=total
        # reset every 21 trading days (bar-count cadence; not calendar month start)
        if (i+1)%21==0:
            for c in weights: sleeve[c]=weights[c]*total
    return out

def daily_rebalance(ret, weights):
    n=min(len(ret[c]) for c in weights)
    return [sum(w*ret[c][i] for c,w in weights.items()) for i in range(n)]

def block_metrics(r, rf, mer, dates=None):
    m={"cagr_pct":round(cagr(r)*100,2),"net_cagr_pct":round((cagr(r)-mer)*100,2),
       "vol_pct":round(st.pstdev(r)*math.sqrt(ANN)*100,2),"max_dd_pct":round(maxdd(r)*100,2),
       "n":len(r)}
    m.update(excess_metrics(r, rf if rf is not None else [mer/ANN]*len(r), mer))
    if rf is None: m["sharpe_excess"]=None; m["sortino_excess"]=None
    m["cagr_ci95"]=bootstrap_cagr_ci(r)
    return m

def main():
    dates, ret = load()
    rf = ret["SGOV_adj"]; rf_full = rf
    n=len(ret["SPY_adj"])
    out={"generated_at":__import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
         "period":[dates[0],dates[-1]],"n_days":n,"rnf":None,
         "note":"Sharpe/Sortino are EXCESS OF CASH (SGOV daily). Block-bootstrap 21d/2000 on CAGR.","funds":{},"portfolios":{}}
    print(f"{'fund':32s}{'netCAGR':>8s}{'CI95':>16s}{'vol':>7s}{'Sh(rf)':>8s}{'Sort(rf)':>9s}{'MaxDD':>8s}")
    for c in ret:
        use_rf = None if c=="SGOV_adj" else rf_full[:len(ret[c])]
        m=block_metrics(ret[c], use_rf, MER[c]); out["funds"][c]=m
        ci=m["cagr_ci95"]; cis=f"[{ci[0]},{ci[1]}]" if ci else "n/a"
        sh="n/a" if c=="SGOV_adj" else str(m["sharpe_excess"])
        so="n/a" if c=="SGOV_adj" else str(m["sortino_excess"])
        print(f"{LABEL[c][:31]:32s}{m['net_cagr_pct']:8.2f}{cis:>16s}{m['vol_pct']:7.2f}{sh:>8s}{so:>9s}{m['max_dd_pct']:8.2f}")
    # split sample on SPY length
    third=3*ANN
    out["split"]={}
    for c in ("FXAIX_adj","SPY_adj","VTSAX_adj","VTI_adj"):
        r=ret[c]; rf2=rf_full[:len(r)]
        first=r[:third]; last=r[third:]
        out["split"][c]={"first3y_net_cagr_pct":round((cagr(first)-MER[c])*100,2),
                         "last2y_net_cagr_pct":round((cagr(last)-MER[c])*100,2)}
        print(f"  split {c:10s} first3y {out['split'][c]['first3y_net_cagr_pct']:+.2f}%  last2y {out['split'][c]['last2y_net_cagr_pct']:+.2f}%")
    # portfolios: true monthly rebalance vs daily
    ports={"100% SPY":({"SPY_adj":1.0},MER["SPY_adj"]),
           "80/20 SPY/BND":({"SPY_adj":0.8,"BND_adj":0.2},0.8*MER["SPY_adj"]+0.2*MER["BND_adj"]),
           "60/40 SPY/BND":({"SPY_adj":0.6,"BND_adj":0.4},0.6*MER["SPY_adj"]+0.4*MER["BND_adj"])}
    print("\nPortfolios (monthly vs daily rebalance, excess-of-cash Sharpe):")
    for name,(w,mer) in ports.items():
        mr=monthly_rebalance(ret,w,dates); dr=daily_rebalance(ret,w)
        rf2=rf_full[:len(mr)]
        mm=block_metrics(mr,rf2,mer); dm=block_metrics(dr,rf2,mer)
        out["portfolios"][name]={"monthly":{k:mm[k] for k in ("net_cagr_pct","vol_pct","max_dd_pct","sharpe_excess")},
                                  "daily":{k:dm[k] for k in ("net_cagr_pct","vol_pct","max_dd_pct","sharpe_excess")},
                                  "rebalance_effect_pp":round(mm["net_cagr_pct"]-dm["net_cagr_pct"],3)}
        print(f"  {name:16s} monthly netCAGR {mm['net_cagr_pct']:.2f}% DD {mm['max_dd_pct']:.2f}%  | daily {dm['net_cagr_pct']:.2f}%  | effect {out['portfolios'][name]['rebalance_effect_pp']:+.2f}pp")
    Path("reports/fund_deep_dive.json").write_text(json.dumps(out,indent=2)+"\n")
    print("\nwrote reports/fund_deep_dive.json")

if __name__=="__main__": main()
