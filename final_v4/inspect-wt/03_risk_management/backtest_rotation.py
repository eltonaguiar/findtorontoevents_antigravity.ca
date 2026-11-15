#!/usr/bin/env python3
"""MF/ETF rotation-sleeve backtest — regenerates backtest_results.json.

PRE-REGISTERED SPEC (fixed before this run; do not edit after seeing results):
- data:     yahoo_monthly.json — monthly closes, 11 symbols. Repeated YYYY-MM rows are
            de-duplicated keeping the first occurrence.
- universe: rotation = SPY EFA EEM TLT IEF GLD VNQ DBC QQQ IWM (AGG only in the 60/40 bench).
- momentum: 12-1 trailing total return (close[t-13] -> close[t-1]); no lookahead.
- filter:   absolute (dual) momentum — hold asset only if its 12-1 return > rf_12 = 2.5%/yr;
            else that slot earns cash (rf monthly).
- weights:  inverse trailing 12-month vol of monthly returns (window ending t-1), normalized
            across selected assets, 50% position cap, remainder in cash at rf.
- cost:     0.05% one-way on traded notional: cost_t = sum(|dw|) * 0.0005, subtracted.
- rf:       2.5%/yr => rf_m = (1.025)^(1/12) - 1, used for the filter, Sharpe and Sortino.
- v1:            base sleeve (above).
- v1_mf_feecost: v1 * (1 - 0.0015)^(1/12) monthly expense drag (0.15%/yr MF share class).
- v2:            v1 with 12% annual vol target: r = rf_m + s*(v1gross - rf_m) - s*cost,
                 s = min(1, 0.12 / realized_annual_vol of v1, 12m window ending t-1).
- v3:            v1 + portfolio drawdown stop: when equity drawdown from peak >= 15%, hold
                 cash for 3 months (cooldown), then resume. (Tested to be reported, incl. if bad.)
- v4_top3_sens:  top-3 selection + 12% vol target (2nd trial — sensitivity only, disclosed).
- benchmarks:    SPY buy & hold (price-only closes, NO dividends — understates B&H, conservative);
                 60/40 SPY/AGG monthly rebalanced.
- metrics:   CAGR; vol = std(returns)*sqrt(12);
             Sharpe = sqrt(12) * mean(r - rf_m) / std(r - rf_m)   <-- TRUE excess Sharpe;
             Sortino = sqrt(12) * mean(r - rf_m) / downside_dev(r vs rf_m);
             MDD on equity curve; Calmar = CAGR/|MDD|; Win% = share of months with r>0;
             best/worst calendar year; VaR95/99 and ES95 = historical, monthly horizon.
- window:    first month with a full 12-1 history -> last valid month.

Run: python backtest_rotation.py   (writes backtest_results.json next to this file)
"""
import io
import json
import math
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
RF_ANN = 0.025
RF_M = (1 + RF_ANN) ** (1 / 12) - 1
RF_12 = RF_ANN
COST_ONEWAY = 0.0005
MF_DRAG_M = (1 - 0.0015) ** (1 / 12)
UNIVERSE = ["SPY", "EFA", "EEM", "TLT", "IEF", "GLD", "VNQ", "DBC", "QQQ", "IWM"]


def load_prices():
    raw = json.load(io.open(os.path.join(HERE, "yahoo_monthly.json"), encoding="utf-8"))
    # rows are [unix_ts_seconds, close]; label by UTC month, keep first occurrence of a month
    # (drops the duplicate partial 2026-11 bar), and exclude the trailing partial month
    # because the data was fetched on 2026-11-14 (last full month = 2026-10).
    months = sorted({time.strftime("%Y-%m", time.gmtime(r[0]))
                     for s in raw.values() for r in s})
    months = [m for m in months if m <= "2026-10"]
    px = {}
    for sym, series in raw.items():
        col = {}
        for row in series:
            m = time.strftime("%Y-%m", time.gmtime(row[0]))
            if m <= "2026-10" and m not in col:
                col[m] = row[1]
        px[sym] = [col.get(m) for m in months]
    return months, px


def std(xs):
    if len(xs) < 2:
        return float("nan")
    mu = sum(xs) / len(xs)
    return math.sqrt(sum((x - mu) ** 2 for x in xs) / (len(xs) - 1))


def backtest():
    months, px = load_prices()
    # monthly simple returns per symbol
    rets = {}
    for s, col in px.items():
        rets[s] = [None] + [(col[i] / col[i - 1] - 1) if col[i] and col[i - 1] else None
                            for i in range(1, len(col))]
    # first index with full 12-1 momentum history: need close[t-13] => i-13 >= 0
    start = next(i for i in range(len(months)) if i - 13 >= 0)
    # trim end: drop trailing months where ANY universe symbol has no close
    end = len(months)
    while end > start and any(px[s][end - 1] is None for s in UNIVERSE):
        end -= 1

    def mom(s, i):        # 12-1 momentum using closes up to i-1
        c1, c0 = px[s][i - 1], px[s][i - 13]
        return (c1 / c0 - 1) if c1 and c0 else None

    def vol12(s, i):      # trailing 12m vol of monthly returns ending at i-1
        w = [rets[s][j] for j in range(i - 12, i)]
        w = [x for x in w if x is not None]
        return std(w) if len(w) >= 12 else None

    out_curve = {k: [] for k in ["v1", "v2", "v3", "v4", "spy", "b6040"]}
    out_ret = {k: [] for k in out_curve}
    labels = []
    eq = {"v1": 1.0, "v2": 1.0, "v3": 1.0, "v4": 1.0, "spy": 1.0, "b6040": 1.0}
    peak_v3, cd_v3 = 1.0, 0
    prev_w = {k: {} for k in ["v1", "v3", "v4"]}   # for turnover cost

    for i in range(start, end):
        labels.append(months[i])
        # ---- select & weight (decision uses data through i-1) ----
        cands = []
        for s in UNIVERSE:
            m, v = mom(s, i), vol12(s, i)
            if m is None or v is None or v <= 0:
                continue
            if m > RF_12:                     # absolute-momentum filter
                cands.append((s, m, v))
        cands.sort(key=lambda t: -t[1])

        def build(topn, vol_target=None):
            sel = cands[:topn]
            if not sel:
                return {}, 0.0
            iv = {s: 1.0 / v for s, _, v in sel}
            tot = sum(iv.values())
            w = {s: min(0.5, iv[s] / tot) for s in iv}
            over = sum(w.values())
            if over > 1.0:                    # rescale down to fit cap-sum<=1
                w = {s: x / over for s, x in w.items()}
            cost_mult = 1.0
            if vol_target is not None:        # v2/v4: scale exposure to vol target
                pv = std([r for r in (out_ret["v1"][-12:] if out_ret["v1"] else [])]) * math.sqrt(12) \
                    if out_ret["v1"] else None
                if pv and pv > 0:
                    sc = min(1.0, vol_target / pv)
                    w = {s: x * sc for s, x in w.items()}
                    cost_mult = sc
            return w, cost_mult

        def apply_variant(key, w, cost_mult, gross_extra=None):
            dw = 0.0
            for s in UNIVERSE:
                dw += abs(w.get(s, 0.0) - prev_w[key].get(s, 0.0))
            cost = dw * COST_ONEWAY * (cost_mult if key in ("v1", "v3") else 1.0)
            prev_w[key] = dict(w)
            r = RF_M + sum(w.get(s, 0.0) * (rets[s][i] - RF_M) for s in UNIVERSE if rets[s][i] is not None)
            r -= cost
            if gross_extra is not None:
                r = gross_extra
            return r

        w1, _ = build(2)
        r1 = apply_variant("v1", w1, 1.0)
        out_ret["v1"].append(r1)

        # v2: vol-targeted version of v1 (uses trailing v1 vol, applied to gross excess)
        pv = std(out_ret["v1"][-12:]) * math.sqrt(12) if len(out_ret["v1"]) >= 12 else None
        sc = min(1.0, 0.12 / pv) if pv and pv > 0 else 1.0
        r2 = RF_M + sc * (r1 - RF_M)   # scales both excess and the already-included cost
        out_ret["v2"].append(r2)

        # v3: DD stop with 3-month cooldown (return choice only; equity rule runs after
        # the shared curve-update below so the equity is not double-counted)
        r3 = RF_M if cd_v3 > 0 else r1
        if cd_v3 > 0:
            cd_v3 -= 1
        out_ret["v3"].append(r3)

        # v4 sensitivity: top-3 + vol target
        w4, cm4 = build(3, vol_target=0.12)
        dw4 = sum(abs(w4.get(s, 0.0) - prev_w["v4"].get(s, 0.0)) for s in UNIVERSE)
        prev_w["v4"] = dict(w4)
        r4 = RF_M + sum(w4.get(s, 0.0) * (rets[s][i] - RF_M) for s in UNIVERSE if rets[s][i] is not None) \
            - dw4 * COST_ONEWAY * cm4
        out_ret["v4"].append(r4)

        # benchmarks
        out_ret["spy"].append(rets["SPY"][i] if rets["SPY"][i] is not None else 0.0)
        w60 = {"SPY": 0.6, "AGG": 0.4}
        r60 = sum(w * (rets[s][i] if rets[s][i] is not None else 0.0) for s, w in w60.items())
        out_ret["b6040"].append(r60)

        for k in out_curve:
            eq[k] *= (1 + out_ret[k][-1])
            out_curve[k].append(eq[k])

        # v3 drawdown rule on the post-month equity (sets cooldown for NEXT month)
        peak_v3 = max(peak_v3, eq["v3"])
        if eq["v3"] / peak_v3 - 1 <= -0.15 and cd_v3 == 0:
            cd_v3 = 3

    return labels, out_ret, out_curve


def stats(r, curve, months):
    n = len(r)
    if n == 0:
        return {}
    eq = curve
    years = {}
    for i, m in enumerate(months):
        years.setdefault(m[:4], []).append(r[i])
    ann = {}
    for y, rs in years.items():
        acc = 1.0
        for x in rs:
            acc *= (1 + x)
        ann[y] = round((acc - 1) * 100, 1)
    cagr = (eq[-1] ** (12.0 / n) - 1) * 100
    vol = std(r) * math.sqrt(12) * 100
    ex = [x - RF_M for x in r]
    sharpe = (math.sqrt(12) * (sum(ex) / n) / std(ex)) if std(ex) > 0 else None
    downside = [min(0, x) for x in ex]
    dd = std(downside) * math.sqrt(12)
    sortino = (math.sqrt(12) * (sum(ex) / n) / dd) if dd > 0 else None
    peak, mdd = 1.0, 0.0
    for x in eq:
        peak = max(peak, x)
        mdd = min(mdd, (x / peak - 1) * 100)
    sr_sorted = sorted(r)
    q = lambda p: sr_sorted[min(n - 1, int(p * n))]
    var95 = q(0.05) * 100
    var99 = q(0.01) * 100
    es95 = (sum(x for x in sr_sorted if x <= q(0.05)) / max(1, sum(1 for x in sr_sorted if x <= q(0.05)))) * 100
    pos = sum(1 for x in r if x > 0) / n * 100
    calmar = (cagr / abs(mdd)) if mdd < 0 else None
    return dict(final=round(eq[-1], 3), cagr=round(cagr, 1), vol=round(vol, 1),
                sharpe=round(sharpe, 2) if sharpe is not None else None,
                sortino=round(sortino, 2) if sortino is not None else None,
                mdd=round(mdd, 1), calmar=round(calmar, 2) if calmar is not None else None,
                wr=round(pos, 1), best=max(ann.values()), worst=min(ann.values()),
                var95=round(var95, 2), var99=round(var99, 2), es95=round(es95, 2)), ann


def main():
    labels, rets, curve = backtest()
    res = {}
    anns = {}
    for key, rowname in [("spy", "bench_spy"), ("b6040", "bench_6040"), ("v1", "v1"),
                         ("v2", "v2"), ("v3", "v3"), ("v4", "v4_top3_sens")]:
        s, ann = stats(rets[key], curve[key], labels)
        s["label"] = rowname
        res[rowname] = s
        anns[key] = ann
    # v1 + MF expense drag: pure rescale of v1 returns
    fee = [(1 + x) * MF_DRAG_M - 1 for x in rets["v1"]]
    feecurve, acc = [], 1.0
    for x in fee:
        acc *= (1 + x)
        feecurve.append(acc)
    s, _ = stats(fee, feecurve, labels)
    s["label"] = "v1_mf_feecost"
    res["v1_mf_feecost"] = s

    def window_ret(key, a, b):
        acc = 1.0
        for m, x in zip(labels, rets[key]):
            if a <= m <= b:
                acc *= (1 + x)
        return round((acc - 1) * 100, 1)

    stress = {}
    for k, short in [("v1", "v1"), ("v3", "v3"), ("spy", "spy")]:
        stress[short + "_2022"] = window_ret(k, "2022-01", "2022-12")
        stress[short + "_covid"] = window_ret(k, "2020-02", "2020-03")
        stress[short + "_2018q4"] = window_ret(k, "2018-10", "2018-12")
        stress[short + "_2025_26"] = window_ret(k, "2025-01", "2026-12")

    out = dict(res)
    out["v1_annual"] = anns["v1"]
    out["v3_annual"] = anns["v3"]
    out["spy_annual"] = anns["spy"]
    out["stress"] = stress
    out["avg_exposure"] = {k: "n/a (see design)" for k in ["v1", "v2", "v3", "v4"]}
    out["curves"] = dict(months=labels, v1=curve["v1"], v2=curve["v2"], v3=curve["v3"],
                         spy=curve["spy"], b6040=curve["b6040"])
    out["spec"] = dict(sharpe="true excess Sharpe: sqrt(12)*mean(r-rf_m)/std(r-rf_m), rf=2.5%/yr",
                       window="%s..%s (%d months)" % (labels[0], labels[-1], len(labels)),
                       script="backtest_rotation.py", rf_pct=2.5, cost_one_way_pct=0.05)
    with io.open(os.path.join(HERE, "backtest_results.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print("window:", labels[0], "->", labels[-1], len(labels), "months")
    for k in ["bench_spy", "bench_6040", "v1", "v1_mf_feecost", "v2", "v3", "v4_top3_sens"]:
        s = out[k]
        print("%-15s CAGR %6s  vol %5s  Sharpe %5s  MDD %7s  WR %4s" %
              (k, s["cagr"], s["vol"], s["sharpe"], s["mdd"], s["wr"]))


if __name__ == "__main__":
    main()
