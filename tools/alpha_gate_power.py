#!/usr/bin/env python3
"""alpha_gate_power.py — is "0/362 pass alpha" a NULL result or a LOW-POWER statement?

Peer critique (hermes-deepseek-flash-psc, Cycle 1): a gate that rejects everything may be
UNDERPOWERED, so "0 pass" says nothing about the market. This computes, analytically and from
the ledger's own mde_pct field, the minimum alpha the gate can actually detect.

Analytic power for a one-sided 95% CI on the mean alpha (alpha ~ N(true, sigma), n trades):
    CI_lo = mean - 1.96*sigma/sqrt(n);  detect iff CI_lo > 0
    power(true) = Phi( true*sqrt(n)/sigma - 1.96 )
    MDE at 80% power = (1.96 + 0.84) * sigma / sqrt(n) = 2.80 * sigma / sqrt(n)
"""
import json, math, argparse
from pathlib import Path

def phi(z): return 0.5*(1+math.erf(z/math.sqrt(2)))
def power(true_alpha, n, sigma): return phi(true_alpha*math.sqrt(n)/sigma - 1.96)
def mde(n, sigma, power_z=0.84): return (1.96+power_z)*sigma/math.sqrt(n)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--out", default="reports/alpha_gate_power.json"); a=ap.parse_args()
    out={"generated_at":__import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
         "question":"Is '0/362 pass alpha' a null result or a low-power statement?",
         "method":"analytic two-sided->one-sided CI power; plus ledger mde_pct","grid":{}}
    for sigma in (0.02,0.05):
        g={}
        for ta in (0.001,0.002,0.005,0.01):
            g[f"alpha={ta*100:.1f}%"]={str(n):round(power(ta,n,sigma),3) for n in (30,100,300,1000)}
        out["grid"][f"sigma={sigma*100:.0f}%"]=g
    out["mde_80pct"]={f"sigma={s*100:.0f}%":{str(n):round(mde(n,s)*100,3) for n in (30,100,300,1000)} for s in (0.02,0.05)}
    # ledger's own mde_pct (minimum detectable effect the gate uses per cell)
    try:
        d=json.load(open("audit_dashboard/data/audit3_ledger.json"))
        mdes=sorted({round(float(c["mde_pct"]),3) for c in d.get("cells",[]) if c.get("mde_pct") is not None})
        out["ledger_mde_pct_distinct"]=mdes[:12]
        aj=[s for s in d["symbols"] if s.get("symbol")=="AUDJPY"]
        if aj: out["audjpy_mde_pct"]=aj[0].get("mde_pct")
    except Exception as e:
        out["ledger_error"]=str(e)
    # verdict
    p02=power(0.002,100,0.02); p05=power(0.005,100,0.02)
    out["verdict"]=(f"At a plausible true alpha of 0.2%/trade, sigma=2%, n=100, power is only {p02:.0%} - the gate would MISS it "
                    f"{1-p02:.0%} of the time. At 0.5% it is {p05:.0%}. So '0 pass' proves 'no alpha ABOVE the gate's MDE', "
                    f"NOT 'zero alpha'. The peer is right: it is (partly) a POWER statement.")
    Path(a.out).write_text(json.dumps(out,indent=2)+"\n")
    print("POWER sigma=2%/trade:")
    for ta,row in out["grid"]["sigma=2%"].items(): print(f"  {ta:12s}",row)
    print("\nMDE (80% power) sigma=2%:",out["mde_80pct"]["sigma=2%"])
    print("ledger distinct mde_pct:",out.get("ledger_mde_pct_distinct"))
    print("AUDJPY mde_pct:",out.get("audjpy_mde_pct"))
    print("\n"+out["verdict"])

if __name__=="__main__": main()
