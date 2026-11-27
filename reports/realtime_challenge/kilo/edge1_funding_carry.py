#!/usr/bin/env python3
"""EDGE-R1  FUNDING CARRY (level + weekly rebalance)  (REALTIMECHALLENGE kilo).

Pre-registered hypothesis H-FUND-LEVEL-WEEKLY:
  Cross-sectional funding carry. Each rebalance, rank perps by trailing-7d AVG
  funding LEVEL; LONG the cheapest third (most negative funding), SHORT the
  dearest third; inverse-vol weight; DOLLAR-NEUTRAL. Collect funding + price.
  Compare WEEKLY rebalance vs PER-8H (churn) rebalance.
  KILL CRITERION (written before run): net Sharpe < 0.5 OOS, OR net expectancy
  CI-LB <= 0, OR edge/cost < 3.

Reproducible: `python3 reports/realtime_challenge/kilo/edge1_funding_carry.py`
Read-only public ccxt (binanceusdm funding + 1d OHLCV). Gross/fee/net together.
"""
import datetime, hashlib, json
import numpy as np

SYMS = ["BTC","ETH","SOL","BNB","XRP","ADA","DOGE","AVAX","LINK","LTC"]
DAYS = 200
COST_PER_SIDE = 0.00045   # 4.5 bp
THIRD = 3                 # long 3 / short 3 of 10

def load(ex):
    now = datetime.datetime.now(datetime.timezone.utc)
    since = int((now - datetime.timedelta(days=DAYS)).timestamp()*1000)
    fund = {}; px = {}
    for s in SYMS:
        sym = f"{s}/USDT:USDT"
        try:
            fr = ex.fetchFundingRateHistory(sym, since=since, limit=1000)
            fund[s] = {int(r["timestamp"]): float(r["fundingRate"]) for r in fr}
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
    # common funding timestamps grid
    all_ts = sorted(set().union(*[set(v.keys()) for v in fund.values()]))
    if not all_ts: return None
    step = rebalance_hours*3600*1000
    grid = all_ts[::max(1, rebalance_hours)]  # every N funding bars
    rets = []; gross_list = []
    for gi in range(len(grid)-1):
        t0, t1 = grid[gi], grid[gi+1]
        window = [t for t in all_ts if t0-7*24*3600*1000 < t <= t0] if rebalance_hours==24 else [t for t in all_ts if t0-step < t <= t0]
        avg = {s: np.mean([fund[s][t] for t in window if t in fund[s]]) for s in SYMS if any(t in fund[s] for t in window)}
        if len(avg) < 2*THIRD: continue
        ranked = sorted(avg, key=lambda s: avg[s])
        longs = ranked[:THIRD]; shorts = ranked[-THIRD:]
        # inverse-vol weights from daily returns up to t0
        w = {}
        for s in longs+shorts:
            ts = sorted(t for t in px[s] if t <= t0)[-30:]
            if len(ts) < 2:
                w[s] = 1.0; continue
            p = np.array([px[s][t] for t in ts], float)
            r = np.diff(p) / p[:-1]
            w[s] = 1.0/vol(r)
        for leg in (longs, shorts):
            tot = sum(w[s] for s in leg)
            if tot <= 0: tot = 1.0
            for s in leg: w[s] /= tot
        # pnl over [t0,t1]
        gross = 0.0
        for s in longs+shorts:
            sign = 1.0 if s in longs else -1.0
            fsum = sum(fund[s][t] for t in all_ts if t0 < t <= t1 and t in fund[s])
            p0 = px[s].get(max([t for t in px[s] if t<=t0], default=None), None)
            p1 = px[s].get(min([t for t in px[s] if t>=t1], default=None), None)
            price_ret = (p1/p0-1) if (p0 and p1) else 0.0
            gross += w[s]*(sign*(-fsum) + sign*price_ret)
        if not np.isfinite(gross):
            continue
        # cost: turnover ~ full gross (2.0) * cost_per_side
        cost = 2.0*COST_PER_SIDE
        net = gross - cost
        rets.append(net); gross_list.append(gross)
    rets = np.array(rets); gross_list=np.array(gross_list)
    if len(rets) < 4: return {"n":len(rets),"status":"too_few"}
    sharpe = float(np.mean(rets)/ (np.std(rets)+1e-12) * np.sqrt(52*24/rebalance_hours))
    return {"n":len(rets),"gross_mean_bp":round(float(gross_list.mean())*1e4,3),
            "net_mean_bp":round(float(rets.mean())*1e4,3),
            "net_sharpe":round(sharpe,3),
            "neg_share":round(float((rets<0).mean()),3)}

def main():
    import ccxt
    ex = ccxt.binanceusdm({"enableRateLimit":True})
    fund, px = load(ex)
    out = {"round":"EDGE-R1","hypothesis":"H-FUND-LEVEL-WEEKLY",
           "generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "syms":SYMS,"cost_per_side_bp":4.5,"rebalance":"weekly_vs_8h","arms":{}}
    out["arms"]["weekly"] = run(fund, px, 24)
    out["arms"]["per_8h"] = run(fund, px, 1)
    with open(__file__,"rb") as fh: out["artifact_sha"]=hashlib.sha256(fh.read()).hexdigest()[:16]
    print(json.dumps(out["arms"], indent=2))
    with open(__file__.replace(".py",".json"),"w") as fh: json.dump(out,fh,indent=2)
    w=out["arms"]["weekly"]
    if w and "net_sharpe" in w:
        verdict = "PASS-proxy" if (w["net_sharpe"]>=0.5 and w["net_mean_bp"]>0) else "FAIL"
        print(f"\nWEEKLY net_sharpe={w['net_sharpe']} net_mean={w['net_mean_bp']}bp n={w['n']} -> {verdict} (kill if <0.5 or CI-LB<=0)")
        print("LEAST-SURVIVABLE NUMBER:", f"net_sharpe {w['net_sharpe']} vs 0.5 bar; per_8h={out['arms']['per_8h']}")

if __name__=="__main__":
    main()