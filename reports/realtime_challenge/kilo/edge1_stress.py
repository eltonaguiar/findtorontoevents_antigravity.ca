#!/usr/bin/env python3
"""EDGE-1 STRESS TEST — rigorous re-adjudication of the funding-carry lead.

The original edge1_funding_carry.py reported "weekly net Sharpe 0.494, n=24".
Deep read found three defects:
  D1. `grid = all_ts[::rebalance_hours]` steps N *funding bars* (8h each), so
      "rebalance_hours=24" is actually ~8 calendar days, not weekly. Label wrong.
  D2. Sharpe annualised as sqrt(52*24/rebalance_hours)=sqrt(52) (~weekly) but the
      holding period is ~8 days -> wrong factor (should be sqrt(365/hold_days)).
  D3. No significance test at all (no t, no CI, no permutation, no OOS split).

This script re-implements the SAME economic hypothesis with an explicit CALENDAR
rebalance, correct annualisation, and full statistics:
  - t-stat, stationary-block bootstrap 95% CI, sign-permutation p-value
  - OOS split (first half vs second half of periods)
  - parameter sensitivity: k (2/3/4), lookback (3/7/14d), hold (7/8/14d)
  - cost ladder: 0 / 1 / 4.5 / 9 / 20 bp per side
  - leg decomposition: funding-carry vs price-momentum attribution

Read-only public ccxt (binanceusdm). Gross / fee / net reported together.
Kill criterion (pre-registered): OOS net Sharpe < 0.5 OR net bootstrap CI-LB <= 0
OR edge/cost < 3.
"""
import datetime, json, hashlib
import numpy as np

SYMS = ["BTC","ETH","SOL","BNB","XRP","ADA","DOGE","AVAX","LINK","LTC"]
DAYS = 330            # ~330d at 8h funding = 990 records (<1000 ccxt cap)
FUND_MS = 8*3600*1000
RNG = np.random.default_rng(20261127)


def load(ex):
    now = datetime.datetime.now(datetime.timezone.utc)
    since = int((now - datetime.timedelta(days=DAYS)).timestamp()*1000)
    fund, px = {}, {}
    for s in SYMS:
        sym = f"{s}/USDT:USDT"
        try:
            fr = ex.fetchFundingRateHistory(sym, since=since, limit=1000)
            fund[s] = sorted((int(r["timestamp"]), float(r["fundingRate"])) for r in fr)
            o = ex.fetch_ohlcv(sym, "1d", since=since, limit=DAYS)
            px[s] = sorted((int(c[0]), float(c[4])) for c in o)
        except Exception as e:
            print("skip", s, type(e).__name__, e)
    return fund, px


def _asof_avg_funding(series, t_end_ms, lookback_days):
    lo = t_end_ms - lookback_days*24*3600*1000
    vals = [r for t, r in series if lo < t <= t_end_ms]
    return float(np.mean(vals)) if vals else None


def _asof_price(series, t_ms):
    # last close at or before t_ms
    best = None
    for t, p in series:
        if t <= t_ms:
            best = p
        else:
            break
    return best


def _price_on_or_after(series, t_ms):
    for t, p in series:
        if t >= t_ms:
            return p
    return None


def _ann_factor(hold_days):
    return np.sqrt(365.0 / hold_days)


def backtest(fund, px, hold_days, k, lookback_days, cost_bp_per_side):
    """Calendar rebalance every hold_days. Dollar-neutral long-cheap/short-dear."""
    # build calendar of rebalance timestamps from the union funding grid
    all_ts = sorted({t for s in fund for t, _ in fund[s]})
    if not all_ts:
        return None
    start = all_ts[0] + lookback_days*24*3600*1000
    end = all_ts[-1]
    grid = []
    t = start
    while t <= end:
        grid.append(int(t))
        t += hold_days*24*3600*1000
    per = []   # dict per period: {carry, price, gross, net}
    for i in range(len(grid)-1):
        t0, t1 = grid[i], grid[i+1]
        avg = {s: _asof_avg_funding(fund[s], t0, lookback_days) for s in SYMS}
        avg = {s: v for s, v in avg.items() if v is not None}
        if len(avg) < 2*k:
            continue
        ranked = sorted(avg, key=lambda s: avg[s])
        longs, shorts = ranked[:k], ranked[-k:]
        # inverse-vol weights from last 30 daily returns up to t0
        w = {}
        for s in longs+shorts:
            rets = []
            hist = [(t, p) for t, p in px[s] if t <= t0][-31:]
            for (ta, pa), (tb, pb) in zip(hist, hist[1:]):
                if pa:
                    rets.append(pb/pa - 1)
            v = float(np.std(rets)) if len(rets) >= 3 else 0.03
            w[s] = 1.0/(v + 1e-9)
        for leg in (longs, shorts):
            tot = sum(w[s] for s in leg) or 1.0
            for s in leg:
                w[s] /= tot
        carry = price = 0.0
        ok = True
        for s in longs+shorts:
            sign = 1.0 if s in longs else -1.0
            payout = [r for t, r in fund[s] if t0 < t <= t1]
            if not payout:
                ok = False; break
            fsum = float(np.sum(payout))
            p0 = _asof_price(px[s], t0)
            p1 = _price_on_or_after(px[s], t1)
            if not p0 or not p1:
                ok = False; break
            pret = p1/p0 - 1
            carry += w[s] * (sign * (-fsum))
            price += w[s] * (sign * pret)
        if not ok:
            continue
        gross = carry + price
        cost = 2.0 * (cost_bp_per_side/1e4)   # full turnover both legs
        per.append(dict(t0=t0, carry=carry, price=price, gross=gross, net=gross-cost))
    return per


def stats(nets, ann_factor):
    a = np.asarray(nets, float)
    a = a[np.isfinite(a)]
    n = len(a)
    if n < 5:
        return {"n": n, "status": "too_few"}
    mean, sd = float(a.mean()), float(a.std(ddof=1))
    t = mean/(sd/np.sqrt(n)) if sd > 0 else 0.0
    # stationary-block bootstrap 95% CI on the mean
    L = max(2, int(round(n ** (1/3))))
    boots = []
    for _ in range(4000):
        idx = []
        while len(idx) < n:
            start = RNG.integers(0, n)
            idx.extend((start + np.arange(L)) % n)
        idx = np.array(idx[:n])
        boots.append(a[idx].mean())
    lo, hi = np.percentile(boots, [2.5, 97.5])
    # sign-permutation p (two-sided) for mean != 0
    signs = RNG.choice([-1, 1], size=(4000, n))
    perm_means = (signs * a).mean(axis=1)
    p_perm = float(np.mean(np.abs(perm_means) >= abs(mean)))
    sharpe = mean/(sd+1e-12) * ann_factor
    return {"n": n, "mean_bp": round(mean*1e4, 3), "sd_bp": round(sd*1e4, 3),
            "t": round(t, 3), "sharpe_ann": round(sharpe, 3),
            "ci95_lo_bp": round(float(lo)*1e4, 3), "ci95_hi_bp": round(float(hi)*1e4, 3),
            "p_perm": round(p_perm, 4), "win": round(float((a > 0).mean()), 3)}


def main():
    import ccxt
    ex = ccxt.binanceusdm({"enableRateLimit": True})
    fund, px = load(ex)
    cov = {s: len(fund[s]) for s in fund}
    out = {"round": "EDGE-1-STRESS", "hypothesis": "H-FUND-LEVEL-CALENDAR",
           "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "data": {"days": DAYS, "syms": list(fund.keys()), "funding_records": cov,
                    "coverage_ok": all(v > 500 for v in cov.values())}}

    # ---- 1. base config: hold 7d, k=3, lookback 7d, cost 4.5bp/side ----
    base_per = backtest(fund, px, 7, 3, 7, 4.5)
    nets = [p["net"] for p in base_per] if base_per else []
    base = stats(nets, _ann_factor(7)) if nets else {"status": "none"}
    out["base"] = base
    if base_per:
        out["base_decomp"] = {
            "carry_mean_bp": round(float(np.mean([p["carry"] for p in base_per]))*1e4, 3),
            "price_mean_bp": round(float(np.mean([p["price"] for p in base_per]))*1e4, 3),
            "gross_mean_bp": round(float(np.mean([p["gross"] for p in base_per]))*1e4, 3),
            "n_periods": len(base_per),
        }
        # ---- 2. OOS split ----
        h = len(nets)//2
        out["oos"] = {"first_half": stats(nets[:h], _ann_factor(7)),
                      "second_half": stats(nets[h:], _ann_factor(7))}
    # ---- 3. parameter sensitivity ----
    sweep = {}
    for hold in (7, 8, 14):
        for kk in (2, 3, 4):
            for lb in (3, 7, 14):
                if 2*kk > len(SYMS):
                    continue
                per = backtest(fund, px, hold, kk, lb, 4.5)
                if not per:
                    continue
                st = stats([p["net"] for p in per], _ann_factor(hold))
                if "mean_bp" in st:
                    sweep[f"H{hold}_k{kk}_L{lb}"] = {k: st[k] for k in
                        ("n", "mean_bp", "sharpe_ann", "t", "ci95_lo_bp", "p_perm")}
    out["param_sweep"] = sweep
    # ---- 4. cost ladder (base config) ----
    ladder = {}
    for c in (0.0, 1.0, 4.5, 9.0, 20.0):
        per = backtest(fund, px, 7, 3, 7, c)
        if per:
            n = [p["net"] for p in per]
            st = stats(n, _ann_factor(7))
            ladder[f"{c}bp"] = {k: st.get(k) for k in ("n", "mean_bp", "sharpe_ann", "ci95_lo_bp")}
    out["cost_ladder"] = ladder

    with open(__file__, "rb") as fh:
        out["artifact_sha"] = hashlib.sha256(fh.read()).hexdigest()[:16]
    print(json.dumps(out, indent=2))
    with open(__file__.replace(".py", ".json"), "w") as fh:
        json.dump(out, fh, indent=2)


if __name__ == "__main__":
    main()