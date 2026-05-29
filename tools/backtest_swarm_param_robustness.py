#!/usr/bin/env python3
"""
backtest_swarm_param_robustness.py — overfit check for the swarm CRYPTO momentum spec.

A real edge survives small parameter perturbations; an overfit one exists only at a
single lucky param combo. We sweep the spec's params over a neighborhood of its
defaults and report how the edge holds up. If only a few combos are profitable, or
the default is an isolated peak far above the median, the "edge" is a fragile artifact.

Reuses indicators + fetch + metrics from tools/backtest_swarm_strategies.py.
Run: python3 tools/backtest_swarm_param_robustness.py
"""
import importlib.util, itertools, pathlib, statistics, sys

_MOD = pathlib.Path(__file__).resolve().parent / "backtest_swarm_strategies.py"
_spec = importlib.util.spec_from_file_location("bss", _MOD)
bss = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(bss)

SYMBOLS = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT"]
FEE = bss.FEE_SLIP
DEFAULT = dict(sma=20, bb=2.0, vol=1.5, trail=2.0, tp=3.0)
GRID = dict(sma=[15,20,25], bb=[1.5,2.0,2.5], vol=[1.2,1.5,2.0], trail=[2.0,3.0], tp=[3.0])

def momentum(bars, sma_p, bb_std, vol_mult, trail, tp_mult, adx_min=25, atr_p=14, adx_p=14):
    o=[b[0] for b in bars]; h=[b[1] for b in bars]; l=[b[2] for b in bars]; c=[b[3] for b in bars]; v=[b[4] for b in bars]
    n=len(c); atr=bss.atr_series(h,l,c,atr_p); adx=bss.adx_series(h,l,c,adx_p)
    warm=max(sma_p,atr_p,adx_p)+1; R=[]; pos=False; entry=hi=tp=0.0
    for t in range(warm, n-1):
        if pos:
            hi=max(hi,c[t]); ae=atr[t] or 0; stop=hi-trail*ae; px=None
            if l[t]<=stop: px=stop
            elif h[t]>=tp: px=tp
            if px is not None: R.append(px/entry-1-2*FEE); pos=False
            continue
        m=bss.sma(c,sma_p,t); sd=bss.std(c,sma_p,t,m) if m else None; vm=bss.sma(v,sma_p,t)
        if None in (m,sd,vm) or atr[t] is None or adx[t] is None: continue
        if (c[t]>m and c[t]>m+bb_std*sd and v[t]>vol_mult*vm
                and (bss.sma(c,sma_p,t) or 0)>(bss.sma(c,sma_p,t-1) or 1e9) and adx[t]>adx_min):
            entry=o[t+1]; hi=c[t]; tp=entry+tp_mult*atr[t]; pos=True
    return R

def main():
    print("=== ParallelSwarm — CRYPTO momentum parameter-robustness sweep (real Binance data) ===")
    data = {s: bss.fetch_crypto(s) for s in SYMBOLS}
    data = {s: b for s, b in data.items() if b and len(b) > 60}
    print(f"symbols with data: {list(data)}")
    combos = list(itertools.product(*[GRID[k] for k in ("sma","bb","vol","trail","tp")]))
    rows = []
    for sma_p,bb,vol,trail,tp in combos:
        allR=[]
        for b in data.values():
            allR += momentum(b, sma_p, bb, vol, trail, tp)
        m = bss.metrics(allR)
        rows.append((dict(sma=sma_p,bb=bb,vol=vol,trail=trail,tp=tp), m))
    pfs = [m["pf"] for _, m in rows if m["n"] >= 10 and m["pf"] != float("inf")]
    prof = [r for r in rows if r[1]["n"] >= 10 and r[1]["pf"] > 1.0]
    default_m = next((m for p, m in rows if all(p[k]==DEFAULT[k] for k in DEFAULT)), None)
    n_eval = len([1 for _, m in rows if m["n"] >= 10])
    print(f"\ncombos: {len(rows)} total, {n_eval} with n>=10 trades")
    print(f"profitable (PF>1, n>=10): {len(prof)}/{n_eval} = {100*len(prof)/max(n_eval,1):.0f}%")
    if pfs:
        print(f"PF across combos: median={statistics.median(pfs):.2f} min={min(pfs):.2f} max={max(pfs):.2f}")
    if default_m:
        print(f"DEFAULT (20/2.0/1.5/2.0/3.0): n={default_m['n']} WR={default_m['wr']*100:.0f}% PF={default_m['pf']:.2f}")
    # robustness verdict
    frac = len(prof)/max(n_eval,1)
    med = statistics.median(pfs) if pfs else 0
    spike = default_m and pfs and default_m["pf"] >= 1.5 and default_m["pf"] > 1.8*med
    print("\n=== VERDICT ===")
    if frac >= 0.60 and med >= 1.1 and not spike:
        v = "ROBUST — edge persists across the parameter neighborhood"
    elif spike:
        v = "OVERFIT SPIKE — default looks good but is an isolated peak vs the neighborhood median"
    elif frac < 0.40:
        v = "FRAGILE — most parameter combos are unprofitable; edge is not robust"
    else:
        v = "WEAK/MIXED — neither clearly robust nor a clean spike; treat as promising-not-valid"
    print(f"  {v}")
    print(f"  (frac_profitable={frac:.0%}, median_PF={med:.2f}, default_PF={default_m['pf'] if default_m else 'NA'})")
    print("  No fabrication — every PF computed from the fetched OHLCV across the sweep.")

if __name__ == "__main__":
    main()
