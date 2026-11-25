#!/usr/bin/env python3
"""
hl_persistence_v2.py — H-260: trader-skill persistence with a VALID denominator.

Why v1 (H-258) was invalidated:
  The leaderboard field `accountValue` is NOT account equity. Measured on a
  random sample of the eligible universe:
    - median(live perp equity / leaderboard accountValue) = 0.098   (~10x overstated)
    - 52% of wallets have zero perp equity while the leaderboard reports >=$10k
    - only 10% reconcile within +-15%
  So ROI = window_pnl / accountValue divided by a number that is ~10x wrong for
  most of the universe and undefined for half of it. Any ROI-based verdict from
  v1 is a measurement of that field, not of trader skill.

Fix:
  POST /info {"type":"portfolio","user":<addr>} returns, per window, an
  accountValueHistory AND pnlHistory time series. From those:
     prior_pnl  = pnl(t-7d)  - pnl(t-30d)      [days 8-30]
     future_pnl = pnl(t)     - pnl(t-7d)       [days 1-7]
     equity     = accountValue at the prior boundary (the risk actually carried)
  Windows are disjoint and the denominator is measured, not inferred.

Usage:  python3 hl_persistence_v2.py [N_SAMPLE] [SNAPSHOT_PATH]
"""
import glob
import json
import sys
import time
import random

import numpy as np
import urllib.request

API = "https://api.hyperliquid.xyz/info"
DAY = 86_400_000
N_BOOT, N_PERM = 2_000, 5_000
RNG = np.random.default_rng(20261124)


def post(payload, tries=3):
    for i in range(tries):
        req = urllib.request.Request(API, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            return json.loads(urllib.request.urlopen(req, timeout=25).read())
        except Exception:
            if i == tries - 1:
                return None
            time.sleep(0.6)


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


def pearson(a, b):
    a = a - a.mean(); b = b - b.mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d > 0 else float("nan")


def spearman(x, y):
    return pearson(rankdata(x), rankdata(y))


def at_or_before(series, ts):
    """value of the last point at or before ts (series = [[ts, val_str], ...])"""
    best = None
    for t, v in series:
        if t <= ts:
            best = float(v)
        else:
            break
    return best


def window_series(port, name):
    for w, body in port:
        if w == name:
            return body.get("pnlHistory") or [], body.get("accountValueHistory") or []
    return [], []


def positive_control():
    n, frac, edge, vol = 20_000, 0.10, 0.03, 0.10
    skilled = RNG.random(n) < frac
    prior = RNG.normal(0, vol, n)
    future = prior * 0.30 + RNG.normal(0, vol, n) + np.where(skilled, edge, 0.0)
    rho = spearman(prior, future)
    ok = rho > 0.05
    print(f"POSITIVE CONTROL  rho={rho:.4f} -> {'PASS' if ok else 'FAIL'}")
    return ok


def main():
    n_target = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    snap_path = sys.argv[2] if len(sys.argv) > 2 else sorted(glob.glob(
        "reports/hl_leaderboard_snapshot_*.json"))[-1]
    print("=" * 74)
    print(f"H-260  persistence with measured equity denominator  (sample={n_target})")
    print("=" * 74)
    if not positive_control():
        print("HARNESS_BROKEN"); return 2

    snap = json.load(open(snap_path))
    print(f"snapshot: {snap_path.split('/')[-1]}  sha256={snap['sha256'][:16]}...")
    elig = [r for r in snap["rows"] if r["acct"] >= 10000 and r["wk_vlm"] > 0]
    random.seed(4242)
    samp = random.sample(elig, min(n_target, len(elig)))
    print(f"universe={len(elig):,}  sampling={len(samp):,}")

    recs, fail = [], 0
    t0 = time.time()
    for i, r in enumerate(samp):
        port = post({"type": "portfolio", "user": r["addr"]})
        if not isinstance(port, list):
            fail += 1; continue
        ph, ah = window_series(port, "month")
        if len(ph) < 10:
            fail += 1; continue
        now = ph[-1][0]
        t7, t30 = now - 7 * DAY, now - 30 * DAY
        p_now, p7, p30 = at_or_before(ph, now), at_or_before(ph, t7), at_or_before(ph, t30)
        eq = at_or_before(ah, t30) or at_or_before(ah, t7)
        if None in (p_now, p7, p30) or not eq or eq <= 0:
            fail += 1; continue
        recs.append(dict(addr=r["addr"], equity=eq,
                         prior=p7 - p30, future=p_now - p7))
        if (i + 1) % 50 == 0:
            print(f"  ..{i+1}/{len(samp)} ok={len(recs)} fail={fail} {time.time()-t0:.0f}s")
        time.sleep(0.08)

    print(f"\nusable wallets: {len(recs):,}  (failed/empty: {fail:,})  {time.time()-t0:.0f}s")
    if len(recs) < 100:
        print("BROKEN: usable n < 100 — do not issue a verdict."); return 2

    prior = np.array([x["prior"] for x in recs])
    future = np.array([x["future"] for x in recs])
    eq = np.array([x["equity"] for x in recs])
    pr, fr = prior / eq, future / eq

    rho = spearman(pr, fr)
    rx, ry = rankdata(pr), rankdata(fr)
    bs = np.array([pearson(rx[i], ry[i]) for i in
                   (RNG.integers(0, len(rx), len(rx)) for _ in range(N_BOOT))])
    lo, hi = np.percentile(bs, [2.5, 97.5])
    obs = pearson(rx, ry)
    ge = sum(1 for _ in range(N_PERM) if pearson(rx, RNG.permutation(ry)) >= obs)
    p = (ge + 1) / (N_PERM + 1)

    print(f"\n--- PRIMARY (measured-equity ROI) ---")
    print(f"  rho = {rho:+.5f}   CI [{lo:+.5f}, {hi:+.5f}]   perm p = {p:.4f}   n = {len(recs):,}")
    print(f"  raw-PnL rho = {spearman(prior, future):+.5f}")

    order = np.argsort(-pr); k = max(1, len(order) // 10)
    top = fr[order[:k]]
    print(f"\n--- top decile (n={k:,}) ---")
    print(f"  mean {top.mean():+.4%}  median {np.median(top):+.4%}  "
          f"hit {np.mean(top>0):.1%}  blowups<-50% {np.mean(top<-0.5):.1%}")

    if lo > 0 and rho >= 0.05:
        v = "PERSISTENT on a valid denominator (beta confound still open)"
    elif hi < 0:
        v = "REFUTED (negative persistence)"
    else:
        v = "INCONCLUSIVE (CI spans 0) — no skill evidence"
    print(f"\nVERDICT: {v}")
    json.dump({"n": len(recs), "rho": rho, "ci": [lo, hi], "perm_p": p,
               "run_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
              open(f"reports/hl_persistence_v2_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.json", "w"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
