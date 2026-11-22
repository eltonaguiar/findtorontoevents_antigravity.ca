#!/usr/bin/env python3
"""Pick survival analysis + regime conditioning of the live ledger.

TODOS 36 and 37 in one harness, because both need the same joined timeline and
splitting them across two scripts is how two different date filters start
producing two different answers.

36 SURVIVAL   -- how long do picks actually live, and does holding longer help?
37 REGIME     -- does per-class expectancy depend on the market state the pick
                 was opened into, or is the loss regime-independent?

Evidence discipline
  * Duration is only computable on artifacts that carry `opened_at`. The resolved
    ledger does NOT; reports/forward_observations.jsonl does (430 H-119 rows).
    So survival is measured on H-119 ONLY and must not be generalised to the other
    66 emitters. Stated in the output, not buried in a footnote.
  * Closed-pick durations are RIGHT-CENSORED: picks still open are absent. Every
    duration statistic here is conditional on having closed, and therefore
    under-states the tail. We print the censoring caveat next to the numbers.
  * Regime partitions are a search. n_trials is printed and BH is applied across
    every regime cell tested, not just the flattering ones.

Read-only. No capital. Not investment advice.

Usage:
    python3 tools/pick_survival_regime.py
    python3 tools/pick_survival_regime.py --out reports/survival_regime
"""
from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LEDGER = REPO / "audit_dashboard/data/resolved_closed_picks_net.json"
FWD = REPO / "reports/forward_observations.jsonl"
OUT = REPO / "reports/survival_regime"


# --------------------------------------------------------------- helpers
def pdt(s):
    if not s:
        return None
    s = str(s).strip().replace("Z", "+00:00")
    for suf in (" EST", " EDT", " UTC", " GMT"):
        if s.endswith(suf):
            s = s[: -len(suf)]
            break
    try:
        dt = datetime.fromisoformat(s)
        return dt.replace(tzinfo=None) if dt.tzinfo else dt
    except ValueError:
        return None


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def sd(xs):
    if len(xs) < 2:
        return float("nan")
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def tstat(xs):
    if len(xs) < 3:
        return float("nan")
    s = sd(xs)
    return mean(xs) / (s / math.sqrt(len(xs))) if s and s == s else float("nan")


def q(xs, p):
    if not xs:
        return float("nan")
    xs = sorted(xs)
    i = min(len(xs) - 1, max(0, int(p * (len(xs) - 1))))
    return xs[i]


def profit_factor(xs):
    w = sum(x for x in xs if x > 0)
    l = -sum(x for x in xs if x < 0)
    return (w / l) if l > 0 else (float("inf") if w > 0 else float("nan"))


def cboot(byc, fn, nb, seed=20261122):
    cl = list(byc.values())
    if len(cl) < 5:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    out = []
    for _ in range(nb):
        f = []
        for _ in range(len(cl)):
            f.extend(cl[rng.randrange(len(cl))])
        v = fn(f)
        if v == v and abs(v) != float("inf"):
            out.append(v)
    if not out:
        return (float("nan"), float("nan"))
    out.sort()
    return out[int(0.025 * len(out))], out[int(0.975 * len(out))]


def norm_sf(z):
    return 0.5 * math.erfc(z / math.sqrt(2))


def bh(p):
    n = len(p)
    if not n:
        return []
    idx = sorted(range(n), key=lambda i: p[i])
    out = [1.0] * n
    prev = 1.0
    for r in range(n, 0, -1):
        i = idx[r - 1]
        prev = min(prev, p[i] * n / r)
        out[i] = min(1.0, prev)
    return out


def fmt(x, nd=2):
    if x is None:
        return "UNMEASURED"
    if isinstance(x, float):
        if x != x:
            return "n/a"
        if abs(x) == float("inf"):
            return "inf"
        return f"{x:,.{nd}f}"
    return str(x)


# --------------------------------------------------------------- regime source
def btc_daily():
    """Daily BTC closes. Prefer yfinance; fall back to the local 1h bars.

    Returns (list of (date, close), source_name).
    """
    try:
        import yfinance as yf
        h = yf.download("BTC-USD", start="2025-09-01", progress=False, auto_adjust=True)
        if h is not None and len(h) > 60:
            col = h["Close"]
            if hasattr(col, "columns"):
                col = col.iloc[:, 0]
            ser = [(d.date(), float(v)) for d, v in col.items() if v == v]
            return ser, "yfinance BTC-USD daily"
    except Exception as e:  # noqa: BLE001
        print(f"    yfinance unavailable ({type(e).__name__}); using local bars")
    p = REPO / "paper_trading/live_sim/bars/BTC_USD_1h.csv"
    day_last = {}
    with p.open() as f:
        next(f)
        for line in f:
            parts = line.strip().split(",")
            if len(parts) < 5:
                continue
            d = parts[0][:10]
            try:
                day_last[d] = float(parts[4])
            except ValueError:
                continue
    return sorted(day_last.items()), "local paper_trading 1h bars (6-month span)"


def build_regimes(series):
    """50d SMA trend flag + trailing-20d realised-vol tercile, PIT (shifted 1d)."""
    dates = [d for d, _ in series]
    closes = [c for _, c in series]
    out = {}
    for i in range(len(dates)):
        if i < 51:
            continue
        win = closes[i - 50:i + 1]
        sma = mean(closes[i - 50:i])          # through t-1, no look-ahead
        rets = [math.log(closes[j] / closes[j - 1])
                for j in range(i - 20, i + 1) if closes[j - 1] > 0]
        vol = sd(rets) * math.sqrt(365) if len(rets) > 2 else float("nan")
        out[dates[i]] = {"trend_ok": closes[i] > sma, "vol": vol,
                         "sma": sma, "close": closes[i]}
    vols = [v["vol"] for v in out.values() if v["vol"] == v["vol"]]
    if len(vols) > 30:
        t1, t2 = q(vols, 1 / 3), q(vols, 2 / 3)
        for v in out.values():
            w = v["vol"]
            v["vol_regime"] = ("LOW" if w == w and w <= t1 else
                               "TOP" if w == w and w >= t2 else "MID")
    else:
        for v in out.values():
            v["vol_regime"] = "MID"
    return out


# --------------------------------------------------------------- 36 survival
def section_survival(nb):
    print("\n" + "=" * 78)
    print("SECTION 36 -- PICK SURVIVAL (duration on closed picks)")
    print("=" * 78)
    if not FWD.exists():
        print("BLOCKED: reports/forward_observations.jsonl missing")
        return {}, []
    rows = []
    for line in FWD.open():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        o, c = pdt(r.get("opened_at")), pdt(r.get("closed_at"))
        if not o or not c or c <= o:
            continue
        if r.get("entry_px") in (None, 0) or r.get("exit_px") in (None, 0):
            continue
        hrs = (c - o).total_seconds() / 3600
        ret = (float(r["exit_px"]) / float(r["entry_px"]) - 1) * 10000  # bp
        if (r.get("side") or "").upper() == "SHORT":
            ret = -ret
        rows.append({"hrs": hrs, "ret_bp": ret, "sym": r.get("symbol"),
                     "hyp": r.get("hypothesis_id"),
                     "regime_ok": r.get("regime_ok"),
                     "created": pdt(r.get("created_at")), "closed": c,
                     "fee_bp": float(r.get("fees") or 0) * 1e4,
                     "slip_bp": float(r.get("slippage_bps") or 0)})

    hyps = Counter(r["hyp"] for r in rows)
    print(f"n usable closed picks   {len(rows):,}")
    print(f"hypotheses              {dict(hyps)}")
    print("SCOPE WARNING: only artifacts carrying `opened_at` can be timed. In this")
    print("repo that is forward_observations.jsonl, which is H-119 only. Everything")
    print("below describes H-119 and must NOT be generalised to the other 66 emitters.")
    print("RIGHT-CENSORING: picks still open are absent from this file, so every")
    print("duration statistic is conditional on having closed and under-states the tail.")

    hrs = [r["hrs"] for r in rows]
    print(f"\nduration (hours)")
    print(f"    min {min(hrs):.1f}   p25 {q(hrs,.25):.1f}   median {q(hrs,.5):.1f}   "
          f"p75 {q(hrs,.75):.1f}   p95 {q(hrs,.95):.1f}   max {max(hrs):.1f}")
    for h, lbl in ((24, "24h"), (48, "48h"), (168, "7d"), (720, "30d")):
        print(f"    closed within {lbl:<5} {100*sum(1 for x in hrs if x<=h)/len(hrs):5.1f}%")

    # duration vs return
    print(f"\nduration bucket vs net return (bp)")
    buckets = [(0, 6, "<6h"), (6, 24, "6-24h"), (24, 72, "1-3d"),
               (72, 168, "3-7d"), (168, 720, "7-30d"), (720, 1e9, ">30d")]
    hdr = f"    {'bucket':<9}{'n':>6}{'mean bp':>10}{'WR%':>7}{'PF':>7}{'t':>7}"
    print(hdr)
    bres = {}
    for lo, hi, lbl in buckets:
        v = [r["ret_bp"] for r in rows if lo <= r["hrs"] < hi]
        if not v:
            continue
        wr = 100 * sum(1 for x in v if x > 0) / len(v)
        print(f"    {lbl:<9}{len(v):>6}{mean(v):>10.2f}{wr:>7.2f}"
              f"{fmt(profit_factor(v)):>7}{fmt(tstat(v)):>7}")
        bres[lbl] = {"n": len(v), "mean_bp": mean(v), "wr": wr, "pf": profit_factor(v)}

    # P&L concentration in time
    tot = sum(r["ret_bp"] for r in rows)
    sortd = sorted(rows, key=lambda r: r["hrs"])
    cum, half = 0.0, None
    for i, r in enumerate(sortd):
        cum += r["ret_bp"]
        if half is None and tot != 0 and (cum / tot) >= 0.5:
            half = (i + 1) / len(sortd)
    print(f"\n    total net {tot:,.0f} bp over {len(rows)} picks")
    print(f"    fastest {100*half:.0f}% of picks (by duration) account for 50% of "
          f"cumulative P&L" if half else "    50% cumulative P&L never reached")

    # provenance on this artifact IS measurable
    back = sum(1 for r in rows if r["created"] and r["closed"] and r["created"] > r["closed"])
    print(f"\nprovenance (this artifact DOES carry created_at)")
    print(f"    created_at > closed_at : {back}/{len(rows)} "
          f"({100*back/len(rows):.1f}%)  <- backfilled, cannot be pre-registered")

    # cost pass-through
    print(f"\ncost actually charged")
    print(f"    median fee {q([r['fee_bp'] for r in rows],.5):.2f} bp   "
          f"median slippage {q([r['slip_bp'] for r in rows],.5):.2f} bp")
    return bres, rows


# --------------------------------------------------------------- 37 regime
def section_regime(nb):
    print("\n" + "=" * 78)
    print("SECTION 37 -- REGIME CONDITIONING OF THE LIVE LEDGER")
    print("=" * 78)
    print("DEFECT FOUND IN MY OWN FIRST PASS, FIXED HERE:\n"
          "The first version joined each pick to the BTC regime on its CLOSE date.\n"
          "That is look-ahead: a pick's P&L and the 'BTC above its 50d SMA' flag\n"
          "are both functions of the same price path, so the split mechanically\n"
          "sorts wins into the UP bucket. It reported CRYPTO|UP +15.72bp (PF CI-LB\n"
          "1.03, survives BH) -- an artefact of conditioning on the outcome.\n"
          "The resolved ledger carries no opened_at, so regime-at-ENTRY is\n"
          "UNMEASURED for those 10,968 rows. We therefore (a) keep the close-date\n"
          "variant ONLY to size the bias, (b) measure regime at ENTRY on\n"
          "forward_observations.jsonl where opened_at exists, and (c) benchmark\n"
          "those picks against simply holding BTC over the identical window.\n")
    ser, srcname = btc_daily()
    print(f"regime source: {srcname}  ({len(ser)} daily closes, "
          f"{ser[0][0]} .. {ser[-1][0]})")
    reg = build_regimes(ser)

    d = json.loads(LEDGER.read_text())
    rows = []
    for r in d["rows"]:
        dt = pdt(r.get("closed_at"))
        if not dt:
            continue
        try:
            net = float(r["pnl_net_pct"]) * 100
        except (TypeError, ValueError):
            continue
        day = dt.date()
        # nearest regime observation at or before the close day
        info = reg.get(day)
        if info is None:
            probe = day
            for _ in range(6):
                probe -= timedelta(days=1)
                if probe in reg:
                    info = reg[probe]
                    break
        if info is None:
            continue
        rows.append({"cls": (r.get("asset_class") or "?").upper(),
                     "src": r.get("source_system") or "?",
                     "sym": r.get("symbol") or "?",
                     "net": net, "day": str(day),
                     "cluster": f"{r.get('symbol')}|{day}",
                     "trend_ok": info["trend_ok"],
                     "vol_regime": info["vol_regime"]})

    covered = len(rows)
    total = len(d["rows"])
    print(f"ledger rows joined to a regime   {covered:,}/{total:,} "
          f"({100*covered/total:.1f}%)")
    if covered < total:
        print(f"    {total-covered:,} rows fall outside the regime series and are "
              f"DROPPED, not imputed.")
    rc = Counter((r["trend_ok"], r["vol_regime"]) for r in rows)
    print(f"    regime mix: " + "  ".join(
        f"{'UP' if k[0] else 'DOWN'}/{k[1]}={v:,}" for k, v in rc.most_common()))

    # Per-class x trend regime, with cluster-robust CI, then BH across cells.
    cells = []
    print(f"\n(a) VARIANT A -- regime at CLOSE date. ** INVALID, LOOK-AHEAD **")
    print("    Shown only to size the bias. Do not use any number in this table.")
    hdr = (f"    {'class':<11}{'regime':<7}{'n':>7}{'clust':>7}{'net bp':>10}"
           f"{'WR%':>7}{'PF':>7}{'PF LB':>7}{'t':>7}")
    print(hdr)
    for cls in [c for c, _ in Counter(r["cls"] for r in rows).most_common()]:
        for lbl, want in (("UP", True), ("DOWN", False)):
            sub = [r for r in rows if r["cls"] == cls and r["trend_ok"] is want]
            if len(sub) < 25:
                continue
            v = [r["net"] for r in sub]
            byc = defaultdict(list)
            for r in sub:
                byc[r["cluster"]].append(r["net"])
            lo, hi = cboot(byc, profit_factor, nb)
            t = tstat(v)
            p = norm_sf(t) if t == t else 1.0
            cells.append({"key": f"{cls}|{lbl}", "n": len(v), "net": mean(v),
                          "pf": profit_factor(v), "lo": lo, "t": t, "p": p})
            print(f"    {cls:<11}{lbl:<7}{len(v):>7,}{len(byc):>7,}"
                  f"{mean(v):>10.2f}{100*sum(1 for x in v if x>0)/len(v):>7.2f}"
                  f"{fmt(profit_factor(v)):>7}{fmt(lo):>7}{fmt(t):>7}")

    n_trials = len(cells)
    qv = bh([c["p"] for c in cells])
    for c, qq in zip(cells, qv):
        c["q"] = qq
    print(f"\n    n_trials (regime cells tested) = {n_trials}")
    surv = [c for c in cells if c["q"] < 0.05]
    print(f"    cells surviving BH at q<0.05 : {len(surv)}")
    for c in sorted(surv, key=lambda z: z["net"], reverse=True):
        print(f"      {c['key']:<18} net {c['net']:+.2f}bp  q={c['q']:.4f}  "
              f"n={c['n']:,}")
    expected = 0.05 * n_trials
    print(f"    expected false positives at alpha=.05 : {expected:.1f}")

    # The decision-relevant question: does conditioning BEAT not conditioning?
    allv = [r["net"] for r in rows]
    best = max(cells, key=lambda c: c["net"]) if cells else None
    print(f"\n    unconditional net          {mean(allv):+.2f} bp (n={len(allv):,})")
    if best:
        print(f"    best regime cell           {best['net']:+.2f} bp "
              f"({best['key']}, n={best['n']:,})")
        print(f"    improvement from conditioning  {best['net']-mean(allv):+.2f} bp")
        print(f"    -> conditioning is only worth it if this gap survives n_trials="
              f"{n_trials} AND the CI lower bound clears 0 (best cell PF LB "
              f"{fmt(best['lo'])})")

    # vol regime, aggregate only (avoid another 2x multiplication of trials)
    print(f"\n(a-cont) by BTC vol regime at CLOSE -- also INVALID (same look-ahead)")
    for lbl in ("LOW", "MID", "TOP"):
        sub = [r["net"] for r in rows if r["vol_regime"] == lbl]
        if len(sub) < 25:
            continue
        print(f"    {lbl:<5} n={len(sub):>6,}  net {mean(sub):>+9.2f} bp  "
              f"WR {100*sum(1 for x in sub if x>0)/len(sub):5.2f}%  "
              f"PF {fmt(profit_factor(sub))}  t {fmt(tstat(sub))}")

    # ---------------------------------------------------------------- (b)
    print(f"\n(b) VARIANT B -- regime at ENTRY. The honest measurement.")
    print("    Source: reports/forward_observations.jsonl (carries opened_at).")
    print("    Scope: H-119 only. n is small and this does NOT generalise.")
    ent = []
    if FWD.exists():
        for line in FWD.open():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            o, c = pdt(r.get("opened_at")), pdt(r.get("closed_at"))
            if not o or not c or c <= o:
                continue
            try:
                ep, xp = float(r["entry_px"]), float(r["exit_px"])
            except (TypeError, ValueError, KeyError):
                continue
            if ep <= 0 or xp <= 0:
                continue
            ret = (xp / ep - 1) * 10000
            if (r.get("side") or "").upper() == "SHORT":
                ret = -ret
            info = reg.get(o.date()) or reg.get((o - timedelta(days=1)).date())
            if info is None:
                continue
            ent.append({"o": o, "c": c, "ret": ret, "up": info["trend_ok"],
                        "vol": info["vol_regime"], "sym": r.get("symbol"),
                        "side": (r.get("side") or "?").upper(),
                        "hrs": (c - o).total_seconds() / 3600})
    if len(ent) >= 20:
        print(f"    n usable entry-dated picks  {len(ent)}")
        print(f"    {'regime':<8}{'n':>6}{'net bp':>10}{'WR%':>7}{'PF':>7}{'t':>7}")
        ev = {}
        for lbl, want in (("UP", True), ("DOWN", False)):
            v = [x["ret"] for x in ent if x["up"] is want]
            if len(v) < 10:
                continue
            print(f"    {lbl:<8}{len(v):>6}{mean(v):>10.2f}"
                  f"{100*sum(1 for y in v if y>0)/len(v):>7.2f}"
                  f"{fmt(profit_factor(v)):>7}{fmt(tstat(v)):>7}")
            ev[lbl] = {"n": len(v), "net": mean(v), "pf": profit_factor(v),
                       "t": tstat(v)}
        for lbl in ("LOW", "MID", "TOP"):
            v = [x["ret"] for x in ent if x["vol"] == lbl]
            if len(v) < 10:
                continue
            print(f"    vol {lbl:<4}{len(v):>6}{mean(v):>10.2f}"
                  f"{100*sum(1 for y in v if y>0)/len(v):>7.2f}"
                  f"{fmt(profit_factor(v)):>7}{fmt(tstat(v)):>7}")
    else:
        ev = {}
        print("    BLOCKED: too few entry-dated picks to condition on.")

    # ---------------------------------------------------------------- (c)
    print(f"\n(c) THE DECISIVE TEST -- beta-adjusted alpha, then cost, then side.")
    print("    DEFECT FOUND IN MY OWN FIRST PASS, FIXED HERE:\n"
          "    The first version subtracted BTC's return over the pick's window and\n"
          "    reported '+395.49bp per trade, t=9.33, picks beat BTC'. That is\n"
          "    arithmetic, not edge. H-119 is a BALANCED long/short book (226L/204S)\n"
          "    and over this sample BTC fell 3.66% per holding window; a market-\n"
          "    neutral book beats a falling long-only index by construction. The\n"
          "    correct benchmark for a zero-beta book is CASH, and the correct test\n"
          "    is alpha from a regression on the benchmark, not a naive difference.")
    bench = None
    if len(ent) >= 20:
        closes = dict(ser)

        def btc_ret(a, b):
            """BTC return between dates a and b, nearest available closes."""
            def near(d, fwd=True):
                k = 0
                while k < 10:
                    t = d + timedelta(days=k if fwd else -k)
                    if t in closes:
                        return closes[t]
                    k += 1
                return None
            pa, pb = near(a.date(), True), near(b.date(), True)
            return (pb / pa - 1) * 10000 if pa and pb and pa > 0 else None

        pairs = []
        for x in ent:
            br = btc_ret(x["o"], x["c"])
            if br is not None:
                pairs.append((x["ret"], br, x.get("side", "?")))
        if len(pairs) >= 20:
            xs = [p[0] for p in pairs]
            bs = [p[1] for p in pairs]
            mb, mx = mean(bs), mean(xs)
            cov = sum((b - mb) * (x - mx) for b, x in zip(bs, xs)) / (len(bs) - 1)
            var = sum((b - mb) ** 2 for b in bs) / (len(bs) - 1)
            beta = cov / var
            alpha = mx - beta * mb
            resid = [x - (alpha + beta * b) for b, x in zip(bs, xs)]
            se = math.sqrt(sum(r * r for r in resid) / (len(resid) - 2))
            se_a = se * math.sqrt(1 / len(xs) + mb * mb / (var * (len(xs) - 1)))
            rt_cost = 2 * 16.0
            print(f"    n paired windows            {len(pairs)}")
            print(f"    beta vs BTC                 {beta:+.4f}   (balanced book, as "
                  f"designed)")
            print(f"    alpha (intercept)           {alpha:+.2f} bp / trade")
            print(f"    alpha t-stat                {alpha/se_a:+.2f}"
                  f"   {'SIGNIFICANT' if abs(alpha/se_a) > 1.96 else 'NOT significant'}")
            print(f"    mean BTC over window        {mb:+.2f} bp  <- the naive "
                  f"benchmark mostly measured a falling market")

            # side decomposition -- where does whatever is there actually live?
            print(f"\n    by side (tests the pick against ZERO, which is the correct")
            print(f"    hurdle for a market-neutral book):")
            print(f"      {'side':<6}{'n':>5}{'pick bp':>10}{'t vs 0':>9}")
            for sd in ("LONG", "SHORT"):
                v = [p[0] for p in pairs if p[2] == sd]
                if len(v) < 10:
                    continue
                print(f"      {sd:<6}{len(v):>5}{mean(v):>10.2f}"
                      f"{fmt(tstat(v)):>9}")

            # cost truth
            gross = mx
            net_rt = gross - rt_cost
            print(f"\n    cost truth (median slippage_bps = 16.0 per side)")
            print(f"      gross mean per trade      {gross:+.2f} bp")
            print(f"      round-trip cost assumed   {rt_cost:.1f} bp")
            print(f"      NET per trade             {net_rt:+.2f} bp  <-- the only "
                  f"number that matters")
            hh = mean([r["hrs"] for r in ent])
            print(f"      mean hold                 {hh:.0f} h")
            print(f"      annualised gross          {gross*(8760/hh)/100:+.2f}%/yr")
            print(f"      annualised net            "
                  f"{net_rt*(8760/hh)/100:+.2f}%/yr   vs T-bill 3.5%/yr")
            bench = {"n": len(pairs), "beta": beta, "alpha_bp": alpha,
                     "alpha_t": alpha / se_a, "mean_btc_bp": mb,
                     "gross_bp": gross, "net_bp": net_rt,
                     "naive_diff_bp": mean([p[0] - p[1] for p in pairs])}
            if net_rt < 0:
                print("      -> net of measured cost the strategy LOSES money and "
                      "loses to cash.\n         The naive 'beats BTC' figure was the "
                      "falling market, not selection.")

    return {"n_joined": covered, "n_trials": n_trials,
            "cells_surviving_bh": len(surv),
            "variant_a_invalid_net_bp": mean(allv),
            "variant_a_best_cell": (best["key"] if best else None),
            "variant_a_best_cell_net": (best["net"] if best else None),
            "variant_b_entry_regime": ev, "variant_c_benchmark": bench,
            "uncond_net_bp": mean(allv), "best_cell": best}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()

    bres, durs = section_survival(a.boot)
    rg = section_regime(a.boot)

    print("\n" + "=" * 78)
    print("WHAT THIS SECTION ESTABLISHES")
    print("=" * 78)
    print(f"  * survival is measurable on H-119 only (n={len(durs)}); durations are "
          f"right-censored")
    print(f"  * regime join covers {rg['n_joined']:,} ledger rows; "
          f"n_trials={rg['n_trials']} regime cells; "
          f"{rg['cells_surviving_bh']} survive BH")
    print(f"  * VARIANT A (regime at close) is LOOK-AHEAD and its best cell "
          f"{rg['variant_a_best_cell']} = {rg['variant_a_best_cell_net']:+.2f}bp "
          f"is an artefact -- retained only to size the bias")
    ev = rg.get("variant_b_entry_regime") or {}
    if ev:
        for lbl, v in ev.items():
            print(f"  * VARIANT B regime-at-entry {lbl:<5} n={v['n']:<4} "
                  f"{v['net']:+8.2f}bp  PF {v['pf']:.2f}  t {v['t']:+.2f}")
    else:
        print("  * VARIANT B regime-at-entry: BLOCKED (too few entry-dated picks)")
    b = rg.get("variant_c_benchmark")
    if b:
        print(f"  * VARIANT C beta {b['beta']:+.3f}; alpha {b['alpha_bp']:+.2f}bp "
              f"t {b['alpha_t']:+.2f} ({'SIG' if abs(b['alpha_t'])>1.96 else 'NOT sig'});"
              f" gross {b['gross_bp']:+.2f}bp -> NET {b['net_bp']:+.2f}bp after 32bp RT"
              f"  (naive 'beats BTC' was {b['naive_diff_bp']:+.2f}bp = falling market)")
    else:
        print("  * VARIANT C benchmark: UNMEASURED")

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "survival_regime.json").write_text(json.dumps(
        {"duration_buckets": bres, "regime": rg}, indent=1, default=str))
    print(f"\nwrote {out/'survival_regime.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
