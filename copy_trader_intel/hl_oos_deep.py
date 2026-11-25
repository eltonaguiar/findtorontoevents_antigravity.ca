#!/usr/bin/env python3
"""
hl_oos_deep.py — is the week-to-week rank-IC of +0.138 real, or the same carried-over artifact?

WHY THIS EXISTS
The carried-over audit showed 92.8% of future-window realised PnL came from positions opened
BEFORE the window. That was measured on a 30d-vs-7d construction. The out-of-sample test then
used realised `closedPnl` bucketed by week, and produced a weaker but still positive median
rho of +0.138.

But `closedPnl` is recognised AT CLOSE. A position opened in week 3 and closed in week 5 books its
PnL in week 5. So a weekly realised series is still a mix of "decisions made this week" and
"decisions made earlier and resolved now". If the +0.138 is the latter, the out-of-sample result is
the SAME frozen-position artifact as the headline, just with a different lag.

THE TEST
Two weekly series over 14 non-overlapping weeks, from the same fills:
  ALL      = every closedPnl, bucketed by the close date        (what the OOS used)
  IN-WEEK  = only closedPnl whose position was BOTH opened and closed inside that same week
             (a genuinely new decision, resolved inside the window)

Rank-IC per adjacent week pair is computed on each. If IN-WEEK collapses toward zero while ALL
stays positive, then week-to-week "persistence" is long-hold drift and the OOS result is void.

Inference: per-pair rho has SE ~ 1/sqrt(n-3). Because adjacent pairs share a week, the honest unit
is the PAIR, so the mean is bootstrapped over the 13 pairs rather than pretending they are
independent observations.
"""
from __future__ import annotations

import glob
import json
import random
import sys
import time
import urllib.request

import numpy as np

API = "https://api.hyperliquid.xyz/info"
DAY = 86_400_000
WEEK = 7 * DAY
LOOKBACK_DAYS = 98
MIN_ACCT = 10_000.0
RNG = np.random.default_rng(20261125)


def post(payload, tries=3):
    for i in range(tries):
        req = urllib.request.Request(API, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            return json.loads(urllib.request.urlopen(req, timeout=25).read())
        except Exception:
            if i == tries - 1:
                return None
            time.sleep(0.5)


def rankdata(x):
    x = np.asarray(x, float)
    n = x.size
    s = np.argsort(x, kind="mergesort")
    inv = np.empty(n, dtype=np.int64)
    inv[s] = np.arange(n)
    xs = x[s]
    obs = np.r_[True, xs[1:] != xs[:-1]]
    dense = obs.cumsum()[inv]
    cnt = np.r_[np.nonzero(obs)[0], n]
    return 0.5 * (cnt[dense] + cnt[dense - 1] + 1)


def pcor(a, b):
    a = a - a.mean(); b = b - b.mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d > 0 else float("nan")


def spearman(x, y):
    return pcor(rankdata(x), rankdata(y)) if len(x) >= 3 else float("nan")


def at_or_before(series, ts):
    best = None
    for t, v in series:
        if t <= ts:
            best = float(v)
        else:
            break
    return best


def load(addr, now):
    nb = LOOKBACK_DAYS // 7
    base = now - nb * WEEK
    port = post({"type": "portfolio", "user": addr})
    if not isinstance(port, list):
        return None, "no portfolio"
    ph = ah = None
    for w, body in port:
        if w == "month":
            ph, ah = body.get("pnlHistory") or [], body.get("accountValueHistory") or []
            break
    if not ph or not ah:
        return None, "no month history"
    eq7 = at_or_before(ah, now - WEEK)
    p7, p30 = at_or_before(ph, now - WEEK), at_or_before(ph, now - 30 * DAY)
    if not eq7 or eq7 < MIN_ACCT or p7 is None or p30 is None:
        return None, "below equity floor / no pnl"

    fills = post({"type": "userFillsByTime", "user": addr,
                  "startTime": now - LOOKBACK_DAYS * DAY, "endTime": now})
    if not isinstance(fills, list) or not fills:
        return None, "no fills"

    weekly_all = np.zeros(nb + 1)
    weekly_rt = np.zeros(nb + 1)
    open_at = {}
    for f in sorted(fills, key=lambda x: int(x.get("time", 0))):
        try:
            t = int(f["time"]); coin = f["coin"]
            sz = float(f["sz"]); start = float(f.get("startPosition", 0.0))
            side = f.get("side"); closed = float(f.get("closedPnl") or 0.0)
        except (KeyError, TypeError, ValueError):
            continue
        b = int((t - base) // WEEK)
        if not (0 <= b < len(weekly_all)):
            continue
        weekly_all[b] += closed
        started = open_at.get(coin)
        if closed != 0.0 and started is not None:
            sb = int((started - base) // WEEK)
            if sb == b:                      # opened AND closed inside this week
                weekly_rt[b] += closed
        if abs(start) < 1e-12:
            open_at[coin] = t
        after = start + (sz if side == "B" else -sz)
        if abs(after) < 1e-12:
            open_at.pop(coin, None)

    return dict(eq7=eq7, prior=p7 - p30, all=weekly_all, rt=weekly_rt), None


def pair_rhos(recs, key, nb):
    out = []
    for w in range(nb - 1):
        a = np.array([r[key][w] for r in recs])
        b = np.array([r[key][w + 1] for r in recs])
        m = (a != 0) | (b != 0)
        if m.sum() < 60:
            continue
        out.append((w + 1, int(m.sum()), spearman(a[m], b[m])))
    return out


def boot_mean(vals, n=5000):
    v = np.asarray(vals, float)
    idx = RNG.integers(0, v.size, (n, v.size))
    means = v[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def main():
    n_target = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    print("=" * 78)
    print(f"H-260 deep: is the OOS rank-IC new decisions or long-hold drift?  (n={n_target})")
    print("=" * 78)

    snap = json.load(open(sorted(glob.glob("reports/hl_leaderboard_snapshot_*.json"))[-1]))
    elig = [r for r in snap["rows"] if r["acct"] >= MIN_ACCT and r["wk_vlm"] > 0]
    random.seed(1234)                      # SAME seed/n as the committed OOS run -> same wallets
    samp = random.sample(elig, min(n_target, len(elig)))
    now = int(time.time() * 1000)

    recs, why, t0 = [], {}, time.time()
    for i, r in enumerate(samp, 1):
        rec, reason = load(r["addr"], now)
        if rec is None:
            why[reason] = why.get(reason, 0) + 1
        else:
            recs.append(rec)
        if i % 50 == 0:
            print(f"  ..{i}/{len(samp)} ok={len(recs)} {time.time()-t0:.0f}s")
        time.sleep(0.05)
    print(f"\nusable {len(recs)}/{len(samp)}")
    print("  failure taxonomy:", dict(sorted(why.items(), key=lambda kv: -kv[1])))
    if len(recs) < 100:
        print("BROKEN"); return 2

    nb = LOOKBACK_DAYS // 7
    all_pairs = pair_rhos(recs, "all", nb)
    rt_pairs = pair_rhos(recs, "rt", nb)

    for label, pairs in (("ALL closedPnl (what the OOS used)", all_pairs),
                         ("IN-WEEK round trips (new decisions only)", rt_pairs)):
        r = [p[2] for p in pairs]
        if len(r) < 4:
            print(f"\n{label}: too few pairs"); continue
        lo, hi = boot_mean(r)
        print(f"\n{label}")
        print(f"  pairs={len(r)}  median={np.median(r):+.4f}  mean={r and np.mean(r):+.4f}  "
              f"bootstrap 95% CI of mean [{lo:+.4f}, {hi:+.4f}]")
        print(f"  min={min(r):+.4f} max={max(r):+.4f} positive {sum(1 for v in r if v>0)}/{len(r)}")
        print(f"  {' '.join(f'{v:+.3f}' for v in r)}")

    out = {"n": len(recs), "failures": why,
           "all": {"rhos": [round(p[2], 4) for p in all_pairs]},
           "in_week": {"rhos": [round(p[2], 4) for p in rt_pairs]},
           "run_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if all_pairs and rt_pairs:
        out["all"]["mean"] = float(np.mean([p[2] for p in all_pairs]))
        out["in_week"]["mean"] = float(np.mean([p[2] for p in rt_pairs]))
        gap = out["all"]["mean"] - out["in_week"]["mean"]
        print(f"\n  GAP (ALL minus IN-WEEK) = {gap:+.4f}")
        if abs(out["in_week"]["mean"]) < 0.05 and out["all"]["mean"] > 0.08:
            print("  => the OOS +0.14 is LONG-HOLD DRIFT, not new decisions. The OOS result is void"
                  " as evidence of tradable week-to-week skill.")
        elif out["in_week"]["mean"] > 0.08:
            print("  => in-week round trips carry it too: week-to-week skill is not merely drift.")
        else:
            print("  => inconclusive: in-week signal is positive but small.")
        out["gap"] = float(gap)

    json.dump(out, open("reports/hl_oos_deep.json", "w"), indent=1)
    print("\nwrote reports/hl_oos_deep.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
