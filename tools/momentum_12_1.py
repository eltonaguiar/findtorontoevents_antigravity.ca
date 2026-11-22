"""Item 18: 12-1 momentum (formation t-12 .. t-1, skipping the most recent month).

Standard academic form (Jegadeesh-Titman / Fama-French). Distinct from the
N1 12-month rule because it skips month t-1 to avoid short-term reversal.

Universe: the 79-symbol panel at data/cache/asset_class_review/*_5y.csv.
Ranking is done WITHIN the cross-section each month, over symbols that have a
full 12-month formation window. Long the top quintile, short the bottom
quintile, equal weight, hold one month. A long-only variant is also reported
because the panel mixes crypto/forex/futures where shorting assumptions differ.
"""
import csv
import glob
import json
import math
import os
import statistics as st
from datetime import datetime

import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(BASE, "data", "cache", "asset_class_review")
SEED = 20261122
N_BOOT = 10000
N_NULL = 500
Q = 0.2
COST_BP_SIDE = {"base": 5.0, "stress": 15.0}


def load_panel():
    out = {}
    for p in sorted(glob.glob(os.path.join(PANEL, "*_5y.csv"))):
        sym = os.path.basename(p)[:-7]
        rows = list(csv.DictReader(open(p)))
        ser = {}
        for r in rows:
            try:
                ser[r["Date"]] = float(r["Close"])
            except (KeyError, ValueError):
                pass
        if len(ser) > 250:
            out[sym] = ser
    return out


def month_keys(d):
    ym = d[:7]
    return ym


def month_end_series(ser):
    """last close in each month -> {ym: (date, price)}"""
    out = {}
    for d in sorted(ser):
        out[d[:7]] = (d, ser[d])
    return out


def maxdd(eq):
    peak, dd = -1e9, 0.0
    for v in eq:
        peak = max(peak, v)
        dd = min(dd, v / peak - 1)
    return dd


def skew(x):
    a = np.asarray(x, float)
    s = a.std(ddof=0)
    return float(((a - a.mean()) ** 3).mean() / s ** 3) if s > 0 else 0.0


def ann_stats(monthly, rf):
    m = np.asarray(monthly, float)
    eq = np.cumprod(1 + m)
    yrs = len(m) / 12
    cagr = eq[-1] ** (1 / yrs) - 1
    vol = m.std(ddof=1) * math.sqrt(12)
    return {"cagr": float(cagr), "vol": float(vol), "sharpe_vs_rf": float((cagr - rf) / vol),
            "maxdd": float(maxdd(np.concatenate([[1.0], eq]))), "skew": skew(m),
            "worst_month": float(m.min()), "pct_pos": float((m > 0).mean())}


def run(panel, variant="ls", cost_side=5.0, exclude_crypto=False):
    me = {s: month_end_series(v) for s, v in panel.items()}
    months = sorted(set.intersection(*[set(v) for v in me.values()]))
    returns, held, prev_pos = [], [], {}
    for i in range(12, len(months) - 1, 1):
        m_now, m_next = months[i], months[i + 1]
        # 12-1: formation spans months i-12 .. i-2, skipping the most recent
        # month (i-1) so short-term reversal does not contaminate the signal
        form = months[i - 12:i - 1]
        scores = {}
        for s, mm in me.items():
            if exclude_crypto and s.endswith("-USD"):
                continue
            if all(k in mm for k in form) and m_now in mm and m_next in mm:
                p0 = mm[form[0]][1]
                p1 = mm[form[-1]][1]
                if p0 > 0:
                    scores[s] = p1 / p0 - 1
        if len(scores) < 10:
            continue
        order = sorted(scores, key=scores.get)
        n = max(1, int(round(len(order) * Q)))
        shorts, longs = order[:n], order[-n:]
        rets = {s: me[s][m_next][1] / me[s][m_now][1] - 1 for s in order}
        if variant == "ls":
            gross = np.mean([rets[s] for s in longs]) - np.mean([rets[s] for s in shorts])
            pos = {s: 1 for s in longs}
            pos.update({s: -1 for s in shorts})
        else:
            gross = np.mean([rets[s] for s in longs])
            pos = {s: 1 for s in longs}
        # turnover cost: fraction of book changed x cost per side
        if prev_pos:
            traded = sum(abs(pos[s] - prev_pos.get(s, 0)) for s in pos) / len(pos)
        else:
            traded = 1.0
        net = gross - traded * cost_side * 1e-4
        returns.append(net)
        held.append({"month": m_next, "gross": float(gross), "net": float(net),
                     "traded": traded, "n_universe": len(order), "longs": longs, "shorts": shorts,
                     "rets": rets})
        prev_pos = pos
    return returns, held, months


def null_percentile(held, variant, seed, n_shuffles):
    """Item 48: random-rank null. Each rebalance the ranks are shuffled, so a
    random set of the same size is held long and short; the mean monthly return
    of that null distribution is compared against the observed mean."""
    obs = float(np.mean([h["gross"] for h in held]))
    null = []
    for k in range(n_shuffles):
        rg = np.random.default_rng(seed + k)
        rs = []
        for h in held:
            names = list(h["rets"])
            rg.shuffle(names)
            n = len(h["longs"])
            L, S = names[-n:], names[:n]
            if variant == "ls":
                rs.append(np.mean([h["rets"][s] for s in L]) - np.mean([h["rets"][s] for s in S]))
            else:
                rs.append(np.mean([h["rets"][s] for s in L]))
        null.append(float(np.mean(rs)))
    null = np.asarray(null)
    return float((null < obs).mean() * 100), float(null.mean()), float(np.percentile(null, 5)), float(np.percentile(null, 95))


def main():
    panel = load_panel()
    print(f"panel symbols loaded: {len(panel)}")
    rf = 0.0432
    spy = {}
    for r in csv.DictReader(open(os.path.join(PANEL, "SPY_5y.csv"))):
        spy[r["Date"]] = float(r["Close"])
    out = {"item": 18, "strategy": "momentum_12_1", "generated_utc": datetime.utcnow().isoformat() + "Z",
           "panel_symbols": len(panel), "quantile_frac": Q,
           "variants": {}}
    for name, kw in [("long_short_base", dict(variant="ls", cost_side=5.0)),
                     ("long_short_stress", dict(variant="ls", cost_side=15.0)),
                     ("long_only_base", dict(variant="lo", cost_side=5.0)),
                     ("long_only_stress", dict(variant="lo", cost_side=15.0)),
                     ("long_short_ex_crypto", dict(variant="ls", cost_side=5.0, exclude_crypto=True))]:
        r, held, months = run(panel, **kw)
        stt = ann_stats(r, rf)
        # SPY over the same months
        d0 = held[0]["month"] + "-01"
        d1 = held[-1]["month"] + "-31"
        sd = sorted(spy)
        s0 = min([d for d in sd if d >= d0]); s1 = max([d for d in sd if d <= d1])
        yrs = len(r) / 12
        spy_cagr = (spy[s1] / spy[s0]) ** (1 / yrs) - 1
        # item 19 bootstrap on excess CAGR (monthly resample)
        rng = np.random.default_rng(SEED)
        a = np.asarray(r)
        boots = []
        for _ in range(N_BOOT):
            sm = a[rng.integers(0, len(a), len(a))]
            boots.append(float(np.prod(1 + sm)) ** (12 / len(a)) - 1 - spy_cagr)
        lo, hi = np.percentile(boots, [2.5, 97.5])
        # item 48 random-rank null (same selection sizes, ranks shuffled)
        pct, null_mean, null_p5, null_p95 = null_percentile(held, kw["variant"], SEED, N_NULL)
        out["variants"][name] = {**stt, "n_rebalances": len(r), "window": [held[0]["month"], held[-1]["month"]],
                                "mean_universe": float(np.mean([h["n_universe"] for h in held])),
                                "spy_cagr_same_window": float(spy_cagr),
                                "excess_cagr": float(stt["cagr"] - spy_cagr),
                                "item19_ci95": [float(lo), float(hi)],
                                "item48_null": {"percentile": pct, "n_shuffles": N_NULL,
                                                "null_mean_month": null_mean,
                                                "null_p5": null_p5, "null_p95": null_p95},
                                "cost_bp_side": kw["cost_side"]}
        print(f"{name:22s} rebal={len(r):3d} cagr={stt['cagr']:.3%} vol={stt['vol']:.3%} "
              f"sharpe={stt['sharpe_vs_rf']:.3f} maxDD={stt['maxdd']:.3%} skew={stt['skew']:.2f} "
              f"excess_vs_SPY={stt['cagr']-spy_cagr:.3%} CI[{lo:.3%},{hi:.3%}] nullpct={pct:.0f}")
    os.makedirs(os.path.join(BASE, "reports"), exist_ok=True)
    json.dump(out, open(os.path.join(BASE, "reports", "momentum_12_1_20261122.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
