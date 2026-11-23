#!/usr/bin/env python3
"""top_gainer_backtest.py — can momentum predict the top gainers?

Cross-sectional test on the daily-kline CSVs already in the repo. For each date t:
  signal = trailing return over LOOKBACK days (also test its negative = reversal)
  target = forward return over HORIZON days (1 = daily, 7 = weekly, 30 = monthly)
Metrics: Spearman rank IC (signal vs forward), and hit-rate@topK vs the RANDOM
baseline (K/N). If hit-rate ~= baseline and IC ~= 0, top gainers are not predictable
from price momentum — which is what the Mercury2 LightGBM model already found
(hit_rate@top3 = 0% out-of-sample).

Pure stdlib. No DB, no network. Symbols pooled from the two crypto_daily_klines CSVs.
"""
import argparse, csv, glob, json, math, statistics as st
from collections import defaultdict
from datetime import date

FILES = [
    "Kimi_Agent_Winning Algo_ Signals & Communities_Feb 14 2026/crypto_daily_klines.csv",
    "Kimi_Agent_Crypto Pick Strategy Challenge Winners/crypto_daily_klines.csv",
]


def load_panel():
    px = defaultdict(dict)  # symbol -> {date_str: close}
    for f in FILES:
        try:
            rows = list(csv.DictReader(open(f)))
        except FileNotFoundError:
            continue
        for r in rows:
            try:
                px[r["symbol"]][r["open_time_formatted"]] = float(r["close"])
            except Exception:
                continue
    return px


def spearman(a, b):
    n = len(a)
    if n < 3:
        return None
    def rank(x):
        order = sorted(range(n), key=lambda i: x[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and x[order[j + 1]] == x[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    ra, rb = rank(a), rank(b)
    ma, mb = st.mean(ra), st.mean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    da = math.sqrt(sum((x - ma) ** 2 for x in ra))
    db = math.sqrt(sum((y - mb) ** 2 for y in rb))
    return num / (da * db) if da and db else None


def backtest(px, lookback, horizon, topk, reversal=False):
    # build common date axis across symbols with data
    all_dates = sorted({d for s in px for d in px[s]})
    syms = sorted(px)
    ics, hits, trials, base_hits = [], 0, 0, 0
    for i in range(lookback, len(all_dates) - horizon):
        t = all_dates[i]
        fwd_t = all_dates[i + horizon]
        cur_t = all_dates[i - lookback]
        sig, fwd, have = [], [], []
        for s in syms:
            c0, c1, c2 = px[s].get(cur_t), px[s].get(t), px[s].get(fwd_t)
            if c0 and c1 and c2:
                r_sig = (c1 / c0 - 1.0) * (-1 if reversal else 1)
                r_fwd = c2 / c1 - 1.0
                sig.append(r_sig); fwd.append(r_fwd); have.append(s)
        if len(have) < topk + 1:
            continue
        ic = spearman(sig, fwd)
        if ic is not None:
            ics.append(ic)
        pred_top = {have[j] for j in sorted(range(len(sig)), key=lambda j: -sig[j])[:topk]}
        true_top = {have[j] for j in sorted(range(len(fwd)), key=lambda j: -fwd[j])[:topk]}
        hits += len(pred_top & true_top)
        trials += topk
        base_hits += topk * topk / len(have)  # expected overlap for random topk of N
    if not trials:
        return None
    return {
        "lookback": lookback, "horizon": horizon, "topk": topk, "reversal": reversal,
        "n_days": len(ics), "mean_rank_ic": round(st.mean(ics), 4) if ics else None,
        "hit_rate_topk": round(hits / trials, 4),
        "random_baseline": round(base_hits / trials, 4),
        "edge_vs_random": round(hits / trials - base_hits / trials, 4),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="reports/top_gainer_backtest.json")
    a = ap.parse_args()
    px = load_panel()
    syms = {s: len(v) for s, v in px.items()}
    out = {"generated_at": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
           "symbols": syms, "n_symbols": len(px), "results": []}
    for lb in (7, 30):
        for h in (1, 7, 30):
            for k in (2, 3):
                for rev in (False, True):
                    r = backtest(px, lb, h, k, rev)
                    if r: out["results"].append(r)
    json.dump(out, open(a.out, "w"), indent=2)
    print(f"symbols={len(px)} panel_days~{max(len(v) for v in px.values())}")
    print(f"{'lb':>3}{'h':>4}{'k':>3}{'rev':>6}{'days':>6}{'IC':>8}{'hitK':>8}{'rand':>8}{'edge':>8}")
    for r in out["results"]:
        print(f"{r['lookback']:>3}{r['horizon']:>4}{r['topk']:>3}{str(r['reversal']):>6}{r['n_days']:>6}"
              f"{r['mean_rank_ic'] if r['mean_rank_ic'] is not None else 0:>8.3f}{r['hit_rate_topk']:>8.3f}"
              f"{r['random_baseline']:>8.3f}{r['edge_vs_random']:>+8.3f}")


if __name__ == "__main__":
    main()
