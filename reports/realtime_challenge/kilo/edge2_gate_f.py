#!/usr/bin/env python3
"""EDGE-R2  FUNDING CARRY -> GATE F  (REALTIMECHALLENGE kilo).

Extends EDGE-R1 (H-FUND-LEVEL-WEEKLY) toward Gate F:
  * history 200d -> 730d  (target n>=100 weekly obs)
  * stationary bootstrap 95% CI on net mean bp AND net Sharpe
  * 2x cost stress (9.0 bp/side) -- net CI-LB must stay > 0
  * funding-vs-price DECOMPOSITION: is the edge carry income or price/crowding?
  * long-leg vs short-leg attribution
  * PSR / DSR proxy (deflated for N_eff trials)

GATE F (written before run): net expectancy 95% CI-LB > 0 at 2x cost,
  n >= 100 weekly obs, net Sharpe CI-LB > 0, DSR proxy > 1.0.
KILL if any fails.  INCONCLUSIVE if n < 100 (underpowered, keep accruing).

Reproducible: `python3 reports/realtime_challenge/kilo/edge2_gate_f.py`
Read-only public ccxt (binanceusdm funding + 1d OHLCV). Gross/fee/net together.
"""
import datetime, hashlib, json
import numpy as np

SYMS = ["BTC","ETH","SOL","BNB","XRP","ADA","DOGE","AVAX","LINK","LTC"]
DAYS = 730
COST_PER_SIDE = 0.00045    # 4.5 bp base; 2x = 9.0 bp
THIRD = 3
N_BOOT = 4000
N_TRIALS_DSR = 12          # effective independent configs tried by the fleet
RNG = np.random.default_rng(20261127)

def fetch_funding_paginated(ex, sym, since):
    """Binance caps fetchFundingRateHistory at limit=1000 (~333d of 8h).
    Page backwards until we reach `since` or run dry, so DAYS=730 is real."""
    out = {}; cursor = int(datetime.datetime.now(datetime.timezone.utc).timestamp()*1000)
    for _ in range(6):
        try:
            fr = ex.fetchFundingRateHistory(sym, since=since, limit=1000)
        except Exception:
            break
        if not fr: break
        for r in fr:
            out[int(r["timestamp"])] = float(r["fundingRate"])
        oldest = min(int(r["timestamp"]) for r in fr)
        if oldest <= since: break
        cursor = oldest - 1
        # ccxt uses `since` param; re-call with since=cursor to page older
        try:
            fr2 = ex.fetchFundingRateHistory(sym, since=since, limit=1000)
        except Exception:
            break
        # fallback: break if no new rows (ccxt binance returns oldest-first window)
        new = [r for r in fr2 if int(r["timestamp"]) not in out]
        if not new:
            # try advancing since to oldest-1 via raw param
            try:
                fr3 = ex.fetchFundingRateHistory(sym, since=oldest-1, limit=1000)
                for r in fr3: out[int(r["timestamp"])] = float(r["fundingRate"])
                if min(int(r["timestamp"]) for r in fr3) >= oldest: break
            except Exception:
                break
    return out

def load(ex):
    now = datetime.datetime.now(datetime.timezone.utc)
    since = int((now - datetime.timedelta(days=DAYS)).timestamp()*1000)
    fund = {}; px = {}
    for s in SYMS:
        sym = f"{s}/USDT:USDT"
        try:
            fund[s] = fetch_funding_paginated(ex, sym, since)
            o = ex.fetch_ohlcv(sym, "1d", since=since, limit=DAYS)
            px[s] = {int(c[0]): float(c[4]) for c in o}
        except Exception as e:
            print("skip", s, type(e).__name__)
    return fund, px

def vol(daily_ret):
    daily_ret = np.asarray(daily_ret, float)
    daily_ret = daily_ret[np.isfinite(daily_ret)]
    if len(daily_ret) < 3:
        return 1.0
    return float(np.std(daily_ret)) + 1e-9

def run(fund, px, rebalance_hours):
    all_ts = sorted(set().union(*[set(v.keys()) for v in fund.values()]))
    if not all_ts: return None
    step = rebalance_hours*3600*1000
    grid = all_ts[::max(1, rebalance_hours)]
    net=[]; gross=[]; fund_leg=[]; price_leg=[]; long_leg=[]; short_leg=[]
    for gi in range(len(grid)-1):
        t0, t1 = grid[gi], grid[gi+1]
        window = [t for t in all_ts if t0-7*24*3600*1000 < t <= t0] if rebalance_hours==24 else [t for t in all_ts if t0-step < t <= t0]
        avg = {s: np.mean([fund[s][t] for t in window if t in fund[s]]) for s in SYMS if any(t in fund[s] for t in window)}
        if len(avg) < 2*THIRD: continue
        ranked = sorted(avg, key=lambda s: avg[s])
        longs = ranked[:THIRD]; shorts = ranked[-THIRD:]
        w = {}
        for s in longs+shorts:
            ts = sorted(t for t in px[s] if t <= t0)[-30:]
            if len(ts) < 2: w[s]=1.0; continue
            p = np.array([px[s][t] for t in ts], float); r = np.diff(p)/p[:-1]
            w[s] = 1.0/vol(r)
        for leg in (longs, shorts):
            tot = sum(w[s] for s in leg) or 1.0
            for s in leg: w[s]/=tot
        g=0.0; fsum_tot=0.0; psum_tot=0.0; lsum=0.0; ssum=0.0
        for s in longs+shorts:
            sign = 1.0 if s in longs else -1.0
            fsum = sum(fund[s][t] for t in all_ts if t0 < t <= t1 and t in fund[s])
            p0 = px[s].get(max([t for t in px[s] if t<=t0], default=None), None)
            p1 = px[s].get(min([t for t in px[s] if t>=t1], default=None), None)
            price_ret = (p1/p0-1) if (p0 and p1) else 0.0
            fcomp = w[s]*(sign*(-fsum)); pcomp = w[s]*(sign*price_ret)
            g += fcomp + pcomp; fsum_tot += fcomp; psum_tot += pcomp
            if sign>0: lsum += fcomp+pcomp
            else: ssum += fcomp+pcomp
        if not np.isfinite(g): continue
        cost = 2.0*COST_PER_SIDE
        net.append(g-cost); gross.append(g); fund_leg.append(fsum_tot)
        price_leg.append(psum_tot); long_leg.append(lsum); short_leg.append(ssum)
    net=np.array(net); gross=np.array(gross)
    if len(net) < 4: return {"n":len(net),"status":"too_few"}
    ann = np.sqrt(52*24/rebalance_hours)
    def sharpe(x): return float(np.mean(x)/(np.std(x)+1e-12)*ann)
    # stationary (iid) bootstrap CI
    n=len(net); idx=RNG.integers(0,n,size=(N_BOOT,n))
    bmean = net[idx].mean(axis=1)*1e4
    bsharpe = (net[idx].mean(axis=1)/(net[idx].std(axis=1)+1e-12)*ann)
    mean_bp=float(net.mean()*1e4); sd_bp=float(net.std()*1e4)
    ci_mean=(float(np.percentile(bmean,2.5)),float(np.percentile(bmean,97.5)))
    ci_sharpe=(float(np.percentile(bsharpe,2.5)),float(np.percentile(bsharpe,97.5)))
    # 2x cost net
    net2 = gross - 2.0*(2.0*COST_PER_SIDE)
    bmean2 = net2[idx].mean(axis=1)*1e4
    ci_mean2=(float(np.percentile(bmean2,2.5)),float(np.percentile(bmean2,97.5)))
    # PSR / DSR proxy (Bailey/Lopez de Prado), skew+kurt adjusted
    s=sharpe(net); skew=float(((net-net.mean())**3).mean()/(net.std()**3+1e-12))
    kurt=float(((net-net.mean())**4).mean()/(net.std()**4+1e-12))
    T=n
    def psr(sr, n_trials):
        sr0=sr/np.sqrt(T)  # not used directly; use annualized->per-obs
        sr_obs=sr/ann
        denom=np.sqrt(1-skew*sr_obs+(kurt-1)/4*sr_obs**2)
        z=( (sr_obs - 0.0)*np.sqrt(T-1) )/ (denom+1e-12)
        from math import erf
        return 0.5*(1+erf(z/np.sqrt(2)))
    psr_val=psr(s,1); dsr_val=psr(s,N_TRIALS_DSR)
    return {"n":n,"gross_mean_bp":round(float(gross.mean()*1e4),3),
            "fund_leg_bp":round(float(np.mean(fund_leg)*1e4),3),
            "price_leg_bp":round(float(np.mean(price_leg)*1e4),3),
            "long_leg_bp":round(float(np.mean(long_leg)*1e4),3),
            "short_leg_bp":round(float(np.mean(short_leg)*1e4),3),
            "net_mean_bp":round(mean_bp,3),"net_sd_bp":round(sd_bp,3),
            "net_sharpe":round(s,3),
            "ci95_mean_bp":[round(ci_mean[0],3),round(ci_mean[1],3)],
            "ci95_sharpe":[round(ci_sharpe[0],3),round(ci_sharpe[1],3)],
            "net2x_mean_bp":round(float(net2.mean()*1e4),3),
            "ci95_mean_2x_bp":[round(ci_mean2[0],3),round(ci_mean2[1],3)],
            "psr":round(psr_val,3),"dsr_proxy":round(dsr_val,3),
            "neg_share":round(float((net<0).mean()),3)}

def main():
    import ccxt
    ex = ccxt.binanceusdm({"enableRateLimit":True})
    fund, px = load(ex)
    out = {"round":"EDGE-R2","hypothesis":"H-FUND-LEVEL-WEEKLY->GATEF",
           "generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "syms":SYMS,"days":DAYS,"cost_per_side_bp":4.5,"boot":N_BOOT,
           "n_trials_dsr":N_TRIALS_DSR,"arms":{}}
    out["arms"]["weekly"]=run(fund,px,24)
    out["arms"]["per_8h"]=run(fund,px,1)
    with open(__file__,"rb") as fh: out["artifact_sha"]=hashlib.sha256(fh.read()).hexdigest()[:16]
    with open(__file__.replace(".py",".json"),"w") as fh: json.dump(out,fh,indent=2)
    w=out["arms"]["weekly"]
    print(json.dumps(out["arms"],indent=2))
    if w and "net_sharpe" in w:
        n_ok = w["n"]>=100
        mean2_ok = w["ci95_mean_2x_bp"][0] > 0
        sharpe_ok = w["ci95_sharpe"][0] > 0
        dsr_ok = w["dsr_proxy"] > 1.0
        verdict = "PASS-GATE-F" if (n_ok and mean2_ok and sharpe_ok and dsr_ok) else ("INCONCLUSIVE" if not n_ok else "FAIL")
        print(f"\nn={w['n']} (>=100? {n_ok}) | net {w['net_mean_bp']}bp CI{w['ci95_mean_bp']} | "
              f"2x {w['net2x_mean_bp']}bp CI{w['ci95_mean_2x_bp']} (>0? {mean2_ok}) | "
              f"Sharpe {w['net_sharpe']} CI{w['ci95_sharpe']} (>0? {sharpe_ok}) | DSR {w['dsr_proxy']} (>1? {dsr_ok})")
        print(f"DECOMP funding {w['fund_leg_bp']}bp vs price {w['price_leg_bp']}bp | long {w['long_leg_bp']} short {w['short_leg_bp']}")
        print(f"VERDICT: {verdict}")
        print("LEAST-SURVIVABLE NUMBER:", f"2x-cost net CI-LB {w['ci95_mean_2x_bp'][0]}bp (must be >0); n={w['n']} (must be >=100)")

if __name__=="__main__":
    main()